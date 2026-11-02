"""Finite synthetic provider/ZIP transcripts, never evidence of actual GitHub CI."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
import time
import zipfile
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from aiflow import node_ci, process_runner
from aiflow.errors import AiflowError, ContractError
from aiflow.process_runner import NodeProcessResult

REPOSITORY = "example/synthetic-target"
ENDPOINT = f"repos/{REPOSITORY}/actions/runs/42/attempts/2/jobs"
SHA = "a" * 64
HEAD = "1" * 40
BASE = "2" * 40
MERGE = "3" * 40
WORKFLOW = ".github/workflows/aiflow-node-ci.yml"
WORKFLOW_BYTES = b"name: synthetic-only\non: pull_request\njobs: {}\n"
TRANSPORT_ROLES = (
    "source",
    "artifact",
    "engine",
    "runtime",
    "dependencies",
    "host",
    "preflight",
    "control",
    "node",
)


def _zip_bytes(members: list[tuple[str | zipfile.ZipInfo, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in members:
            if isinstance(name, str):
                # Preserve hostile raw names; ZipInfo normally rewrites Windows separators.
                raw_name = name
                name = zipfile.ZipInfo(name)
                name.filename = raw_name
                name.orig_filename = raw_name
            archive.writestr(name, data)
    return output.getvalue()


def test_archive_inventory_reads_exact_bytes_without_extracting(tmp_path: Path) -> None:
    payload = _zip_bytes([("control/", b""), ("control/source.json", b"{}")])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        files = node_ci._zip_files(archive, entries=2, total=2)
        assert set(files) == {"control/source.json"}
        assert node_ci._zip_read(archive, files["control/source.json"], limit=2) == b"{}"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "name", ["../outside", "/absolute", "C:/outside", "a\\b", "a/./b", "a/../b", "a//b"]
)
def test_archive_rejects_unsafe_member_paths(name: str, tmp_path: Path) -> None:
    payload = _zip_bytes([(name, b"x")])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive, pytest.raises(ContractError):
        node_ci._zip_files(archive, entries=1, total=1)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "members",
    [
        [("raw/A", b"x"), ("raw/a", b"x")],
        [("raw", b"x"), ("raw/file", b"x")],
        [("raw/", b""), ("RAW", b"x")],
    ],
)
def test_archive_rejects_case_aliases_and_file_directory_collisions(
    members: list[tuple[str, bytes]],
) -> None:
    payload = _zip_bytes(members)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive, pytest.raises(ContractError):
        node_ci._zip_files(archive, entries=2, total=2)


@pytest.mark.parametrize("kind", [stat.S_IFLNK, stat.S_IFCHR, stat.S_IFSOCK])
def test_archive_rejects_link_and_special_unix_members(kind: int) -> None:
    entry = zipfile.ZipInfo("raw/member")
    entry.create_system = 3
    entry.external_attr = (kind | 0o777) << 16
    payload = _zip_bytes([(entry, b"target")])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive, pytest.raises(ContractError):
        node_ci._zip_files(archive, entries=1, total=6)


def test_archive_rejects_windows_reparse_member() -> None:
    entry = zipfile.ZipInfo("raw/member")
    entry.create_system = 0
    entry.external_attr = (stat.S_IFREG | 0o644) << 16 | 0x400
    payload = _zip_bytes([(entry, b"target")])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive, pytest.raises(ContractError):
        node_ci._zip_files(archive, entries=1, total=6)


@pytest.mark.parametrize("limit", ["entries", "expanded", "member"])
def test_archive_limits_reject_before_any_extraction(limit: str, tmp_path: Path) -> None:
    payload = _zip_bytes([("raw/member", b"1234")])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        with pytest.raises(ContractError) as caught:
            if limit == "member":
                node_ci._zip_read(archive, archive.getinfo("raw/member"), limit=3)
            else:
                node_ci._zip_files(
                    archive,
                    entries=0 if limit == "entries" else 1,
                    total=3 if limit == "expanded" else 4,
                )
    assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"
    assert list(tmp_path.iterdir()) == []


def test_archive_rejects_unapproved_codec() -> None:
    entry = zipfile.ZipInfo("raw/member")
    entry.compress_type = zipfile.ZIP_BZIP2
    payload = _zip_bytes([(entry, b"x")])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive, pytest.raises(ContractError):
        node_ci._zip_files(archive, entries=1, total=1)


def _source_selection() -> dict[str, object]:
    return {
        "origin": "direct",
        "source_repository_id": 1319293089,
        "source_full_name": "MaginaLW/harness-model",
        "workflow_id": 10,
        "workflow_path": ".github/workflows/node-engine-artifacts.yml",
        "workflow_ref": "refs/pull/7/merge",
        "workflow_sha256": SHA,
        "source_head": HEAD,
        "run_id": 42,
        "run_attempt": 2,
        "job_id": 43,
        "artifact_id": 46,
        "artifact_name": "aiflow-node-engine-42-2",
        "artifact_digest": "sha256:" + SHA,
        "wheel": {"member": "direct/aiflow-0.2.0-py3-none-any.whl", "size": 1, "sha256": SHA},
        "sdist": {"member": "sdist/aiflow-0.2.0.tar.gz", "size": 1, "sha256": SHA},
        "build_manifest": {"member": "build-manifest.json", "size": 1, "sha256": SHA},
    }


def test_source_archive_provider_digest_rejects_before_unpacking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "artifact.zip"
    archive.write_bytes(_zip_bytes([("unknown", b"synthetic")]))
    inspect = Mock(side_effect=AssertionError("digest mismatch reached ZIP traversal"))
    monkeypatch.setattr(node_ci, "_zip_files", inspect)
    with pytest.raises(ContractError):
        node_ci.validate_engine_artifact_archive(archive, _source_selection())
    inspect.assert_not_called()
    assert list(tmp_path.iterdir()) == [archive]


@pytest.mark.parametrize("change", ["missing", "extra", "foreign"])
def test_source_artifact_cannot_expand_public_member_set(change: str, tmp_path: Path) -> None:
    members = [
        ("direct/aiflow-0.2.0-py3-none-any.whl", b"not-a-wheel"),
        ("sdist/aiflow-0.2.0.tar.gz", b"not-an-sdist"),
        ("sdist-rebuilt/aiflow-0.2.0-py3-none-any.whl", b"not-a-wheel"),
        ("build-manifest.json", b"{}"),
    ]
    if change == "missing":
        members.pop()
    elif change == "extra":
        members.append(("private.txt", b"not-authorized"))
    else:
        members[0] = ("direct/foreign.whl", b"not-a-wheel")
    archive = tmp_path / "artifact.zip"
    archive.write_bytes(_zip_bytes(members))
    with pytest.raises(ContractError, match="exact four-member"):
        node_ci.validate_engine_artifact_archive(archive)
    assert list(tmp_path.iterdir()) == [archive]


def test_paginated_exact_attempt_reads_all_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [
        {"total_count": 101, "jobs": [{"id": number} for number in range(1, 101)]},
        {"total_count": 101, "jobs": [{"id": 101}]},
    ]
    request = Mock(side_effect=pages)
    monkeypatch.setattr(node_ci, "_gh_json", request)
    assert node_ci.github_get(ENDPOINT, paginate=True) == [
        {"id": number} for number in range(1, 102)
    ]
    assert [call.args[0] for call in request.call_args_list] == [
        ENDPOINT + "?per_page=100&page=1",
        ENDPOINT + "?per_page=100&page=2",
    ]


@pytest.mark.parametrize(
    "change", ["incomplete", "changed_total", "duplicate", "missing_id", "mixed", "bool_id"]
)
def test_paginated_provider_collection_rejects_incomplete_or_mixed_observations(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    first = {"total_count": 101, "jobs": [{"id": number} for number in range(1, 101)]}
    second = {"total_count": 101, "jobs": [{"id": 101}]}
    if change == "incomplete":
        pages = [{"total_count": 2, "jobs": [{"id": 1}]}]
    elif change == "missing_id":
        pages = [{"total_count": 1, "jobs": [{"name": "no-id"}]}]
    elif change == "bool_id":
        pages = [{"total_count": 1, "jobs": [{"id": True}]}]
    else:
        if change == "changed_total":
            second["total_count"] = 102
        elif change == "duplicate":
            second["jobs"] = [{"id": 1}]
        else:
            second = {"total_count": 101, "artifacts": [{"id": 101}]}
        pages = [first, second]
    request = Mock(side_effect=pages)
    monkeypatch.setattr(node_ci, "_gh_json", request)
    with pytest.raises(ContractError):
        node_ci.github_get(ENDPOINT, paginate=True)
    assert request.call_count <= 2


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://api.github.com/user",
        "user",
        "repos/example/synthetic-target/../user",
        "repos/example/synthetic-target/actions/%2e%2e/%2e%2e/user",
        ENDPOINT + "?page=2",
        ENDPOINT + "?per_page=1",
    ],
)
def test_invalid_endpoint_or_caller_pagination_never_reaches_client(
    monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    request = Mock(side_effect=AssertionError("invalid selector reached client"))
    monkeypatch.setattr(node_ci, "_gh_json", request)
    with pytest.raises(ContractError):
        node_ci.github_get(endpoint, paginate=True)
    request.assert_not_called()


@pytest.mark.parametrize("bound", ["bytes", "entries"])
def test_provider_pagination_enforces_finite_aggregate_bounds(
    monkeypatch: pytest.MonkeyPatch, bound: str
) -> None:
    monkeypatch.setattr(node_ci, "MAX_JSON_BYTES" if bound == "bytes" else "MAX_ENTRIES", 2)
    request = Mock(return_value=[{"id": 1}, {"id": 2}, {"id": 3}])
    monkeypatch.setattr(node_ci, "_gh_json", request)
    with pytest.raises(ContractError) as caught:
        node_ci.github_get(ENDPOINT, paginate=True)
    assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"
    request.assert_called_once()


def _process_result() -> NodeProcessResult:
    return NodeProcessResult(0, False, b'{"id":42}', b"", False, False, "confirmed", False)


def test_official_client_get_has_fixed_host_method_timeout_and_isolated_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "tools/gh.exe"
    monkeypatch.setattr(node_ci, "_gh_executable", lambda: executable)
    monkeypatch.setenv("GH_TOKEN", "synthetic-test-token")
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-second-token")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-private-unrelated")
    monkeypatch.setenv("GH_HOST", "attacker.invalid")
    monkeypatch.setenv("GH_DEBUG", "api")
    runner = Mock(return_value=_process_result())
    monkeypatch.setattr(process_runner, "run_node_process", runner)
    assert node_ci._gh_json(ENDPOINT) == {"id": 42}
    arguments, options = runner.call_args
    assert arguments[0] == (
        str(executable),
        "api",
        "--hostname",
        "github.com",
        "--method",
        "GET",
        "--header",
        "Accept: application/vnd.github+json",
        ENDPOINT,
    )
    assert options["timeout_seconds"] == 60
    assert options["cwd"] == Path.cwd().absolute()
    environment = options["environment"]
    assert environment["GH_TOKEN"] == "synthetic-test-token"
    assert environment["GH_HOST"] == "github.com"
    assert environment["GH_PROMPT_DISABLED"] == "1"
    assert "GH_DEBUG" not in environment
    assert "OPENAI_API_KEY" not in environment
    assert "synthetic-test-token" not in " ".join(arguments[0])
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "fault",
    [
        {"returncode": 1},
        {"timed_out": True},
        {"stdout_overflow": True},
        {"stderr_overflow": True},
        {"cleanup": "unknown"},
        {"execution_error": True},
    ],
)
def test_unsafe_client_outcome_rejects_without_disclosing_streams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: dict[str, object]
) -> None:
    monkeypatch.setattr(node_ci, "_gh_executable", lambda: tmp_path / "gh.exe")
    result = replace(
        _process_result(),
        stdout=b"synthetic-sensitive-output",
        stderr=b"synthetic-sensitive-error",
        **fault,
    )
    monkeypatch.setattr(process_runner, "run_node_process", Mock(return_value=result))
    with pytest.raises(ContractError) as caught:
        node_ci._gh_json(ENDPOINT)
    assert caught.value.code == "NODE_CI_PLATFORM_UNVERIFIED"
    assert "synthetic-sensitive" not in str(caught.value)


@pytest.mark.parametrize("data", [b'{"id":1,"id":2}', b"{", b"NaN"])
def test_client_rejects_duplicate_or_malformed_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data: bytes
) -> None:
    monkeypatch.setattr(node_ci, "_gh_executable", lambda: tmp_path / "gh.exe")
    monkeypatch.setattr(
        process_runner,
        "run_node_process",
        Mock(return_value=replace(_process_result(), stdout=data)),
    )
    with pytest.raises(ContractError):
        node_ci._gh_json(ENDPOINT)


def test_untrusted_client_bytes_reject_before_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "gh.exe"
    executable.write_bytes(b"synthetic-not-the-pinned-official-client")
    monkeypatch.setenv("AIFLOW_GH_EXE", str(executable))
    runner = Mock(side_effect=AssertionError("untrusted executable was launched"))
    monkeypatch.setattr(process_runner, "run_node_process", runner)
    with pytest.raises(ContractError) as caught:
        node_ci.github_get(ENDPOINT)
    assert caught.value.code == "NODE_CI_PLATFORM_UNVERIFIED"
    runner.assert_not_called()


def _blob(data: bytes) -> dict[str, object]:
    return {
        "type": "file",
        "encoding": "base64",
        "size": len(data),
        "sha": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
        "content": base64.b64encode(data).decode("ascii"),
    }


def _endpoints(*, source: bool = False) -> dict[str, str]:
    full_name = "MaginaLW/harness-model" if source else REPOSITORY
    workflow = ".github/workflows/node-engine-artifacts.yml" if source else WORKFLOW
    filename = "node-engine-artifacts.yml" if source else "aiflow-node-ci.yml"
    root = f"repos/{full_name}"
    return {
        "repository": root,
        "workflow": root + "/actions/workflows/" + filename,
        "run": root + "/actions/runs/42/attempts/2",
        "pr": root + "/pulls/7",
        "merge_ref": root + "/git/ref/pull/7/merge",
        "merge_commit": root + "/git/commits/" + MERGE,
        "merge_workflow": root + f"/contents/{workflow}?ref={MERGE}",
        "head_workflow": root + f"/contents/{workflow}?ref={HEAD}",
        "jobs": root + "/actions/runs/42/attempts/2/jobs",
        "check": root + "/check-runs/44",
    }


def _workflow_transcript(*, completed: bool, source: bool = False) -> dict[str, object]:
    """Finite server-shaped bytes behind the client seam, not real authentication."""
    full_name = "MaginaLW/harness-model" if source else REPOSITORY
    workflow = ".github/workflows/node-engine-artifacts.yml" if source else WORKFLOW
    job_key = "node-engine-artifacts" if source else "aiflow-node-ci"
    repository = {"id": 1319293089 if source else 42, "full_name": full_name, "private": not source}
    head = {"sha": HEAD, "ref": "codex/synthetic", "repo": deepcopy(repository)}
    base = {"sha": BASE, "ref": "main", "repo": deepcopy(repository)}
    status = {
        "status": "completed" if completed else "in_progress",
        "conclusion": "success" if completed else None,
    }
    records = {
        "repository": deepcopy(repository),
        "workflow": {"id": 10, "path": workflow, "state": "active"},
        "run": {
            "id": 42,
            "run_attempt": 2,
            "workflow_id": 10,
            "event": "pull_request",
            "repository": deepcopy(repository),
            "head_repository": deepcopy(repository),
            "head_sha": HEAD,
            "head_branch": "codex/synthetic",
            "path": workflow,
            "pull_requests": [{"number": 7, "head": deepcopy(head), "base": deepcopy(base)}],
            "referenced_workflows": [],
            "check_suite_id": 45,
            **status,
        },
        "pr": {
            "number": 7,
            "state": "open",
            "head": deepcopy(head),
            "base": deepcopy(base),
            "merge_commit_sha": MERGE,
        },
        "merge_ref": {"ref": "refs/pull/7/merge", "object": {"type": "commit", "sha": MERGE}},
        "merge_commit": {"sha": MERGE, "parents": [{"sha": BASE}, {"sha": HEAD}]},
        "merge_workflow": _blob(WORKFLOW_BYTES),
        "head_workflow": _blob(WORKFLOW_BYTES),
        "jobs": [
            {
                "id": 43,
                "run_id": 42,
                "run_attempt": 2,
                "head_sha": HEAD,
                "name": job_key,
                "check_run_url": f"https://api.github.com/repos/{full_name}/check-runs/44",
                **status,
            }
        ],
        "check": {
            "id": 44,
            "name": job_key,
            "head_sha": HEAD,
            "app": {"id": 15368},
            "check_suite": {"id": 45},
            **status,
        },
    }
    endpoints = _endpoints(source=source)
    return {endpoints[name]: value for name, value in records.items()}


def _install_transcript(monkeypatch: pytest.MonkeyPatch, transcript: dict[str, object]) -> Mock:
    def get(endpoint: str, *, paginate: bool = False) -> object:
        assert endpoint in transcript, f"unplanned synthetic provider read: {endpoint}"
        assert paginate is (
            endpoint in {ENDPOINT, "repos/MaginaLW/harness-model/actions/runs/42/attempts/2/jobs"}
        )
        return deepcopy(transcript[endpoint])

    request = Mock(side_effect=get)
    monkeypatch.setattr(node_ci, "github_get", request)
    return request


@pytest.mark.parametrize("completed", [False, True])
def test_workflow_transcript_binds_actual_pr_merge_workflow_attempt_job_and_check(
    monkeypatch: pytest.MonkeyPatch, completed: bool, tmp_path: Path
) -> None:
    transcript = _workflow_transcript(completed=completed)
    request = _install_transcript(monkeypatch, transcript)
    observed = node_ci.authenticate_workflow(
        42, REPOSITORY, WORKFLOW, "aiflow-node-ci", run_id=42, attempt=2, completed=completed
    )
    assert observed["repository_id"] == 42
    assert observed["full_name"] == REPOSITORY
    assert observed["head_sha"] == HEAD
    assert observed["workflow_sha256"] == hashlib.sha256(WORKFLOW_BYTES).hexdigest()
    assert observed["workflow_ref"] == "refs/pull/7/merge"
    assert observed["run_id"] == 42
    assert observed["run_attempt"] == 2
    assert observed["job_id"] == 43
    assert observed["check_run_id"] == 44
    assert observed["app_id"] == 15368
    assert set(call.args[0] for call in request.call_args_list) == set(transcript)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "record,path,value",
    [
        ("repository", ("id",), 99),
        ("workflow", ("path",), ".github/workflows/foreign.yml"),
        ("run", ("run_attempt",), 1),
        ("run", ("workflow_id",), 99),
        ("run", ("event",), "workflow_dispatch"),
        ("run", ("repository", "id"), 99),
        ("run", ("pull_requests",), []),
        ("run", ("pull_requests",), [{"number": 7}, {"number": 8}]),
        ("pr", ("head", "repo", "id"), 99),
        ("pr", ("base", "repo", "id"), 99),
        ("pr", ("head", "sha"), BASE),
        ("pr", ("base", "sha"), HEAD),
        ("pr", ("merge_commit_sha",), HEAD),
        ("merge_ref", ("object", "sha"), HEAD),
        ("merge_commit", ("parents",), [{"sha": BASE}]),
        ("jobs", (0, "run_attempt"), 1),
        ("jobs", (0, "run_id"), 99),
        ("jobs", (0, "head_sha"), BASE),
        ("jobs", (0, "check_run_url"), "https://attacker.invalid/check-runs/44"),
        ("check", ("id",), 99),
        ("check", ("name",), "foreign-check"),
        ("check", ("app", "id"), 1),
        ("check", ("head_sha",), BASE),
        ("check", ("check_suite", "id"), 99),
    ],
)
def test_workflow_transcript_rejects_foreign_or_incomplete_associations(
    monkeypatch: pytest.MonkeyPatch, record: str, path: tuple[str | int, ...], value: object
) -> None:
    transcript = _workflow_transcript(completed=True)
    target = transcript[_endpoints()[record]]
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    _install_transcript(monkeypatch, transcript)
    with pytest.raises(ContractError):
        node_ci.authenticate_workflow(
            42, REPOSITORY, WORKFLOW, "aiflow-node-ci", run_id=42, attempt=2, completed=True
        )


@pytest.mark.parametrize("record", ["run", "jobs", "check"])
@pytest.mark.parametrize("completed", [False, True])
def test_producer_and_completed_consumer_cannot_borrow_each_others_status(
    monkeypatch: pytest.MonkeyPatch, record: str, completed: bool
) -> None:
    transcript = _workflow_transcript(completed=completed)
    observation = transcript[_endpoints()[record]]
    if record == "jobs":
        observation = observation[0]
    observation.update(
        status="in_progress" if completed else "completed",
        conclusion=None if completed else "success",
    )
    _install_transcript(monkeypatch, transcript)
    with pytest.raises(ContractError):
        node_ci.authenticate_workflow(
            42, REPOSITORY, WORKFLOW, "aiflow-node-ci", run_id=42, attempt=2, completed=completed
        )


def test_workflow_blobs_must_match_each_other_not_just_individually_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcript = _workflow_transcript(completed=True)
    transcript[_endpoints()["merge_workflow"]] = _blob(WORKFLOW_BYTES + b"# changed at merge\n")
    _install_transcript(monkeypatch, transcript)
    with pytest.raises(ContractError):
        node_ci.authenticate_workflow(
            42, REPOSITORY, WORKFLOW, "aiflow-node-ci", run_id=42, attempt=2, completed=True
        )


def test_caller_environment_cannot_fill_missing_pr_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcript = _workflow_transcript(completed=False)
    transcript[_endpoints()["run"]]["pull_requests"] = []
    for name, value in {
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_RUN_ID": "42",
        "GITHUB_RUN_ATTEMPT": "2",
        "GITHUB_SHA": HEAD,
        "GITHUB_REF": "refs/pull/7/merge",
        "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/{WORKFLOW}@refs/pull/7/merge",
    }.items():
        monkeypatch.setenv(name, value)
    _install_transcript(monkeypatch, transcript)
    with pytest.raises(ContractError):
        node_ci.authenticate_workflow(
            42, REPOSITORY, WORKFLOW, "aiflow-node-ci", run_id=42, attempt=2, completed=False
        )


@pytest.mark.parametrize(
    "change", ["size", "bool_size", "digest", "encoding", "type", "base64", "content_type"]
)
def test_workflow_blob_identity_uses_actual_decoded_bytes(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    document = _blob(b"x")
    if change == "size":
        document["size"] = 2
    elif change == "bool_size":
        document["size"] = True
    elif change == "digest":
        document["sha"] = HEAD
    elif change == "encoding":
        document["encoding"] = "none"
    elif change == "type":
        document["type"] = "symlink"
    elif change == "base64":
        document["content"] = "!not-base64!"
    else:
        document["content"] = 1
    request = Mock(return_value=document)
    monkeypatch.setattr(node_ci, "github_get", request)
    with pytest.raises(ContractError):
        node_ci._github_file(REPOSITORY, WORKFLOW, HEAD)
    request.assert_called_once_with(
        f"repos/{REPOSITORY}/contents/{WORKFLOW}?ref={HEAD}", paginate=False
    )


@pytest.mark.parametrize("change", ["missing_jobs", "duplicate_job", "missing_check_suite"])
def test_workflow_requires_unique_registered_job_and_real_check_suite(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    transcript = _workflow_transcript(completed=True)
    endpoints = _endpoints()
    if change == "missing_jobs":
        transcript[endpoints["jobs"]] = []
    elif change == "duplicate_job":
        transcript[endpoints["jobs"]] *= 2
    else:
        del transcript[endpoints["run"]]["check_suite_id"]
        del transcript[endpoints["check"]]["check_suite"]["id"]
    _install_transcript(monkeypatch, transcript)
    with pytest.raises(ContractError):
        node_ci.authenticate_workflow(
            42, REPOSITORY, WORKFLOW, "aiflow-node-ci", run_id=42, attempt=2, completed=True
        )


def _platform_observation() -> dict[str, object]:
    return {
        "provider": "github",
        "repository_id": 42,
        "full_name": REPOSITORY,
        "workflow_id": 10,
        "workflow_path": WORKFLOW,
        "workflow_ref": "refs/pull/7/merge",
        "workflow_sha256": hashlib.sha256(WORKFLOW_BYTES).hexdigest(),
        "event": "pull_request",
        "head_sha": HEAD,
        "run_id": 42,
        "run_attempt": 2,
        "job_id": 43,
        "job_key": "aiflow-node-ci",
        "check_run_id": 44,
        "check_name": "aiflow-node-ci",
        "app_id": 15368,
    }


def _artifact_transcript() -> dict[str, object]:
    job = _workflow_transcript(completed=True)[ENDPOINT][0]
    job.update(started_at="2026-01-01T00:00:00Z", completed_at="2026-01-01T00:01:00Z")
    artifact = {
        "id": 46,
        "name": "aiflow-node-ci-42-2",
        "size_in_bytes": 123,
        "digest": "sha256:" + SHA,
        "expired": False,
        "created_at": "2026-01-01T00:00:30Z",
        "expires_at": "2099-01-01T00:00:30Z",
        "workflow_run": {"id": 42, "repository_id": 42, "head_repository_id": 42, "head_sha": HEAD},
    }
    return {
        f"repos/{REPOSITORY}/actions/jobs/43": job,
        f"repos/{REPOSITORY}/actions/runs/42/artifacts": [artifact],
    }


def _install_artifact_transcript(
    monkeypatch: pytest.MonkeyPatch, transcript: dict[str, object]
) -> Mock:
    def get(endpoint: str, *, paginate: bool = False) -> object:
        assert endpoint in transcript, f"unplanned synthetic artifact read: {endpoint}"
        assert paginate is endpoint.endswith("/artifacts")
        return deepcopy(transcript[endpoint])

    request = Mock(side_effect=get)
    monkeypatch.setattr(node_ci, "github_get", request)
    return request


def test_artifact_transcript_uses_exact_job_window_and_all_run_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcript = _artifact_transcript()
    request = _install_artifact_transcript(monkeypatch, transcript)
    metadata = node_ci._select_artifact(_platform_observation(), name="aiflow-node-ci-42-2")
    assert metadata["id"] == 46
    assert metadata["name"] == "aiflow-node-ci-42-2"
    assert metadata["digest"] == "sha256:" + SHA
    assert set(call.args[0] for call in request.call_args_list) == set(transcript)


@pytest.mark.parametrize(
    "path,value",
    [
        (("expired",), True),
        (("expired",), None),
        (("expires_at",), "2020-01-01T00:00:00Z"),
        (("id",), True),
        (("size_in_bytes",), -1),
        (("digest",), None),
        (("digest",), "sha512:" + SHA),
        (("created_at",), "2025-12-31T23:59:59Z"),
        (("created_at",), "2026-01-01T00:01:01Z"),
        (("created_at",), True),
        (("workflow_run", "id"), 99),
        (("workflow_run", "repository_id"), 99),
        (("workflow_run", "head_repository_id"), 99),
        (("workflow_run", "head_sha"), BASE),
    ],
)
def test_artifact_transcript_rejects_expiry_bad_digest_or_cross_attempt_origin(
    monkeypatch: pytest.MonkeyPatch, path: tuple[str, ...], value: object
) -> None:
    transcript = _artifact_transcript()
    target = transcript[f"repos/{REPOSITORY}/actions/runs/42/artifacts"][0]
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    _install_artifact_transcript(monkeypatch, transcript)
    with pytest.raises(ContractError):
        node_ci._select_artifact(_platform_observation(), name="aiflow-node-ci-42-2")


@pytest.mark.parametrize("change", ["missing", "duplicate", "job_attempt", "job_window"])
def test_artifact_selection_rejects_absent_ambiguous_or_unbound_window(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    transcript = _artifact_transcript()
    artifacts = f"repos/{REPOSITORY}/actions/runs/42/artifacts"
    if change == "missing":
        transcript[artifacts] = []
    elif change == "duplicate":
        transcript[artifacts] *= 2
    elif change == "job_attempt":
        transcript[f"repos/{REPOSITORY}/actions/jobs/43"]["run_attempt"] = 1
    else:
        transcript[f"repos/{REPOSITORY}/actions/jobs/43"]["completed_at"] = None
    _install_artifact_transcript(monkeypatch, transcript)
    with pytest.raises(ContractError):
        node_ci._select_artifact(_platform_observation(), name="aiflow-node-ci-42-2")


@pytest.fixture
def finite_transport_caps(monkeypatch: pytest.MonkeyPatch) -> dict[str, tuple[int, ...]]:
    """Finite unit-test transport bounds; never register production capacity."""
    table = {level: (256, 8192, 65536, 16384, 262144) for level in ("V0", "V1", "V2")}
    monkeypatch.setattr(node_ci, "CI_CAPS_REGISTERED", True)
    monkeypatch.setattr(node_ci, "CI_CAPS", table)
    return table


def _canonical_test(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def _reference(path: str, data: bytes) -> dict[str, object]:
    return {"ref": path, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _transport_identity(*, size: int | None = None) -> dict[str, int]:
    return {
        "device": 0,
        "inode": 1,
        "nlink": 1,
        "size": size or 0,
        "mtime_ns": 1790000000000000000,
        "ctime_ns": 1790000000000000001,
        "mode": (stat.S_IFDIR | 0o755) if size is None else (stat.S_IFREG | 0o644),
        "attributes": 16 if size is None else 0,
    }


def _transport_source() -> dict[str, Any]:
    placeholder = _reference("control/placeholder.json", b"{}")
    return {
        "kind": "aiflow-node-ci-attested-source",
        "schema_version": "1.0",
        "binding": {
            "repository_id": "00000000-0000-4000-8000-000000000042",
            "task_id": "TASK-0001",
            "branch": "refs/heads/codex/synthetic",
            "base_commit": BASE,
            "subject_commit": HEAD,
            "subject_tree": MERGE,
            "policy_sha256": SHA,
            "spec_sha256": SHA,
            "classification_input_sha256": SHA,
            "decision_unit_ids": ["DU-001"],
            "verification_level": "V0",
        },
        "attestation_head": HEAD,
        "static_declaration": deepcopy(placeholder),
        "engine_artifact": _source_selection(),
        "source_evidence": {"original": deepcopy(placeholder), "canonical_sha256": SHA},
        **{
            name: deepcopy(placeholder)
            for name in ("task", "events", "classification", "spec", "approvals")
        },
        "policy_members": [deepcopy(placeholder) for _ in range(4)],
        "applicable_spec_approvals": [],
        "applicable_code_approvals": [],
        "v2": None,
    }


def _transport_fixture() -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Actual bounded ZIP members and empty dirs, deliberately no valid Node proof."""
    source = _transport_source()
    descriptor = {
        "kind": "aiflow-node-ci-descriptor",
        "schema_version": "1.0",
        "source_tuple_sha256": hashlib.sha256(_canonical_test(source)).hexdigest(),
        "static_declaration_sha256": source["static_declaration"]["sha256"],
        "engine_artifact_sha256": hashlib.sha256(
            _canonical_test(source["engine_artifact"])
        ).hexdigest(),
        "execution_contract_sha256": SHA,
        "verification_level": "V0",
        "attestation_head": HEAD,
    }
    control = {
        "source-tuple.json": _canonical_test(source),
        "descriptor.json": _canonical_test(descriptor),
        # No fabricated passed report. Content replay must reject this placeholder.
        "evidence.json": b"{}",
    }
    response = b'{"id":42}'
    receipt = _canonical_test(_job_receipt())
    api_index = {
        "kind": "aiflow-node-ci-api-observations",
        "schema_version": "1.0",
        "observations": [
            {
                "sequence": 1,
                "method": "GET",
                "endpoint": f"repos/{REPOSITORY}",
                "response": _reference("control/api-observations/000001.response.raw", response),
                "response_canonical_sha256": hashlib.sha256(response).hexdigest(),
                "receipt": _reference("control/api-observations/000001.receipt.json", receipt),
            }
        ],
    }
    control.update(
        {
            "api-observations.json": _canonical_test(api_index),
            "api-observations/000001.response.raw": response,
            "api-observations/000001.receipt.json": receipt,
        }
    )
    files: dict[str, bytes] = {}
    manifests: dict[str, Any] = {}
    for role in TRANSPORT_ROLES:
        payloads = {"payload.bin": role.encode()}
        if role == "control":
            payloads.update(control)
        entries = [
            {"path": path, "kind": "directory", "identity": _transport_identity()}
            for path in ("empty", "empty/nested")
        ]
        if role == "control":
            entries.append(
                {"path": "api-observations", "kind": "directory", "identity": _transport_identity()}
            )
        entries.extend(
            {
                "path": path,
                "kind": "file",
                "identity": _transport_identity(size=len(data)),
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for path, data in payloads.items()
        )
        entries.sort(key=lambda entry: entry["path"].encode())
        root = (
            "C:/synthetic/project/source"
            if role == "source"
            else f"C:/synthetic/project/.tmp/node-ci/42-2/{role}"
        )
        manifests[role] = {
            "id": role,
            "root": root,
            "identity": _transport_identity(),
            "entries": entries,
            "total_bytes": sum(len(data) for data in payloads.values()),
        }
        files.update({f"originals/{role}/{path}": data for path, data in payloads.items()})
        files[f"manifests/{role}.json"] = _canonical_test(manifests[role])
    index = {
        "kind": "aiflow-node-ci-originals",
        "schema_version": "1.0",
        **{
            name: _reference(f"control/{filename}", control[filename])
            for name, filename in (
                ("evidence", "evidence.json"),
                ("descriptor", "descriptor.json"),
                ("source_tuple", "source-tuple.json"),
            )
        },
        "roles": [
            {
                "id": role,
                "manifest": _reference(f"manifests/{role}.json", files[f"manifests/{role}.json"]),
            }
            for role in TRANSPORT_ROLES
        ],
    }
    files["index.json"] = _canonical_test(index)
    return files, index, manifests, descriptor


def _rebind_test_manifest(
    files: dict[str, bytes], index: dict[str, Any], role: str, data: bytes
) -> None:
    files[f"manifests/{role}.json"] = data
    for row in index["roles"]:
        if row["id"] == role:
            row["manifest"] = _reference(f"manifests/{role}.json", data)
    files["index.json"] = _canonical_test(index)


def test_actions_file_only_zip_recreates_only_validated_manifest_directories(
    tmp_path: Path, finite_transport_caps: dict[str, tuple[int, ...]]
) -> None:
    files, index, manifests, _descriptor = _transport_fixture()
    archive = tmp_path / "files.zip"
    archive.write_bytes(_zip_bytes(list(files.items())))
    with zipfile.ZipFile(archive) as zipped:
        assert all(not entry.is_dir() for entry in zipped.infolist())
    package = node_ci._extract_package(archive, tmp_path / "package", level="V0")
    assert node_ci._package_manifests(package, level="V0") == (index, manifests)
    assert {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file()
    } == files
    for role in TRANSPORT_ROLES:
        assert (package / "originals" / role / "empty/nested").is_dir()
        assert list((package / "originals" / role / "empty/nested").iterdir()) == []


@pytest.mark.parametrize(
    "change",
    [
        "missing_file",
        "extra_file",
        "case_alias",
        "unknown_directory",
        "bad_file_hash",
        "bad_manifest_hash",
        "duplicate_json",
        "noncanonical_index",
        "noncanonical_manifest",
        "unknown_manifest",
        "link_identity",
        "reparse_identity",
    ],
)
def test_transport_rejects_invalid_package_before_destination_write(
    tmp_path: Path, finite_transport_caps: dict[str, tuple[int, ...]], change: str
) -> None:
    files, index, manifests, _descriptor = _transport_fixture()
    if change == "missing_file":
        del files["originals/node/payload.bin"]
    elif change == "extra_file":
        files["originals/node/unknown.bin"] = b"x"
    elif change == "case_alias":
        files["ORIGINALS/node/payload.bin"] = b"node"
    elif change == "unknown_directory":
        files["originals/node/unknown/"] = b""
    elif change == "bad_file_hash":
        files["originals/node/payload.bin"] = b"changed"
    elif change == "bad_manifest_hash":
        files["manifests/node.json"] += b" "
    elif change == "duplicate_json":
        files["index.json"] = files["index.json"][:-1] + b',"kind":"aiflow-node-ci-originals"}'
    elif change == "noncanonical_index":
        files["index.json"] = json.dumps(index, indent=2).encode()
    else:
        manifest = manifests["node"]
        if change == "unknown_manifest":
            manifest["unknown"] = True
        elif change == "link_identity":
            manifest["entries"][-1]["identity"]["mode"] = stat.S_IFLNK | 0o777
        elif change == "reparse_identity":
            manifest["identity"]["attributes"] |= 0x400
        data = (
            json.dumps(manifest, indent=2).encode()
            if change == "noncanonical_manifest"
            else _canonical_test(manifest)
        )
        _rebind_test_manifest(files, index, "node", data)
    archive = tmp_path / "invalid.zip"
    original = _zip_bytes(list(files.items()))
    archive.write_bytes(original)
    destination = tmp_path / "package"
    with pytest.raises(ContractError):
        node_ci._extract_package(archive, destination, level="V0")
    assert not destination.exists()
    assert archive.read_bytes() == original


@pytest.mark.parametrize("slot", ["entries", "original", "manifests", "index", "archive"])
def test_transport_enforces_each_registered_aggregate_cap_before_extraction(
    tmp_path: Path, finite_transport_caps: dict[str, tuple[int, ...]], slot: str
) -> None:
    files, _index, manifests, _descriptor = _transport_fixture()
    payload = _zip_bytes(list(files.items()))
    limits = [
        4 + 2 * len(TRANSPORT_ROLES) + sum(len(value["entries"]) for value in manifests.values()),
        sum(value["total_bytes"] for value in manifests.values()),
        sum(len(_canonical_test(value)) for value in manifests.values()),
        len(files["index.json"]),
        len(payload),
    ]
    position = ("entries", "original", "manifests", "index", "archive").index(slot)
    row = list(finite_transport_caps["V0"])
    row[position] = limits[position] - 1
    finite_transport_caps["V0"] = tuple(row)
    archive = tmp_path / "over-cap.zip"
    archive.write_bytes(payload)
    destination = tmp_path / "package"
    with pytest.raises(ContractError) as caught:
        node_ci._extract_package(archive, destination, level="V0")
    assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"
    assert not destination.exists()


def test_extraction_write_failure_retains_partial_and_refuses_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    finite_transport_caps: dict[str, tuple[int, ...]],
) -> None:
    files, _index, _manifests, _descriptor = _transport_fixture()
    archive = tmp_path / "files.zip"
    archive.write_bytes(_zip_bytes(list(files.items())))
    destination = tmp_path / "package"
    original_write = node_ci._write_new
    writes = 0

    def fail_second_write(path: Path, data: bytes) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("synthetic extraction failure")
        original_write(path, data)

    monkeypatch.setattr(node_ci, "_write_new", fail_second_write)
    with pytest.raises(ContractError):
        node_ci._extract_package(archive, destination, level="V0")
    assert (destination / "index.json").read_bytes() == files["index.json"]
    before = {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in destination.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ContractError):
        node_ci._extract_package(archive, destination, level="V0")
    assert writes == 2
    assert {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in destination.rglob("*")
        if path.is_file()
    } == before


@pytest.mark.parametrize(
    "change", ["modified", "missing", "extra_directory", "missing_directory", "hardlink"]
)
def test_package_reader_rechecks_physical_members_without_repair(
    tmp_path: Path, finite_transport_caps: dict[str, tuple[int, ...]], change: str
) -> None:
    files, _index, _manifests, _descriptor = _transport_fixture()
    archive = tmp_path / "files.zip"
    archive.write_bytes(_zip_bytes(list(files.items())))
    package = node_ci._extract_package(archive, tmp_path / "package", level="V0")
    target = package / "originals/node/payload.bin"
    if change == "modified":
        target.write_bytes(b"changed")
    elif change == "missing":
        target.unlink()
    elif change == "extra_directory":
        (package / "originals/node/undeclared").mkdir()
    elif change == "missing_directory":
        (package / "originals/node/empty/nested").rmdir()
    else:
        os.link(target, tmp_path / "retained-link")
    before = {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ContractError):
        node_ci._package_manifests(package, level="V0")
    assert {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file()
    } == before


def test_minimal_transport_is_rejected_as_node_original_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    finite_transport_caps: dict[str, tuple[int, ...]],
) -> None:
    files, _index, _manifests, descriptor = _transport_fixture()
    archive = tmp_path / "files.zip"
    archive.write_bytes(_zip_bytes(list(files.items())))
    package = node_ci._extract_package(archive, tmp_path / "package", level="V0")
    forbidden = Mock(side_effect=AssertionError("transport replay attempted a process"))
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    with pytest.raises(ContractError):
        node_ci.validate_ci_originals(package, descriptor, _transport_source())
    forbidden.assert_not_called()


@pytest.fixture
def gate_composition_seams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    finite_transport_caps: dict[str, tuple[int, ...]],
) -> dict[str, Any]:
    """Isolate composition decisions; mocked observations certify no real CI/LOCAL proof."""
    from aiflow import gate as local_gate

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "sentinel").write_bytes(b"protected source unchanged")
    source = _transport_source()
    platform = _platform_observation()
    declaration = {
        "repository": {"provider_repository_id": 42, "full_name": REPOSITORY},
        "workflow": {"sha256": platform["workflow_sha256"]},
        "tier_contracts": {
            "V0": hashlib.sha256(
                _canonical_test(node_ci.node_ci_execution_contract("V0"))
            ).hexdigest()
        },
    }
    blobs = {"control/task.yaml": b"synthetic committed metadata"}
    package = tmp_path / "boundary-package"
    control = package / "originals/control"
    control.mkdir(parents=True)
    (control / "task.yaml").write_bytes(blobs["control/task.yaml"])
    inputs = b"{}"
    (control / "input-materials.json").write_bytes(inputs)
    facts = {
        "passed": True,
        "reason_codes": [],
        "evidence": {"platform": deepcopy(platform)},
        "admission": {
            "engine_content_sha256": SHA,
            "input_materials_sha256": hashlib.sha256(inputs).hexdigest(),
        },
    }
    local = Mock(
        side_effect=[
            SimpleNamespace(passed=True, reason_codes=()),
            SimpleNamespace(passed=True, reason_codes=()),
        ]
    )
    authority = Mock(
        side_effect=[(deepcopy(source), deepcopy(declaration), deepcopy(blobs)) for _ in range(3)]
    )
    platform_reader = Mock(side_effect=[deepcopy(platform), deepcopy(platform)])
    content_reader = Mock(return_value=facts)
    download = Mock()
    extract = Mock(return_value=package)
    wheel = Mock(return_value=SHA)
    real_wheel_binding = node_ci._installed_wheel_binding
    real_local_binding = node_ci._local_wheel_binding
    assumed_engine = {"synthetic_composition_observation": "no installation proof"}
    current_engine = Mock(return_value=assumed_engine)
    local_binding = Mock(
        return_value={
            "engine_sha256": hashlib.sha256(_canonical_test(assumed_engine)).hexdigest(),
            "engine_content_sha256": SHA,
        }
    )
    monkeypatch.setattr(local_gate, "evaluate_gate", local)
    monkeypatch.setattr(node_ci, "_build_source_authority", authority)
    monkeypatch.setattr(node_ci, "authenticate_workflow", platform_reader)
    monkeypatch.setattr(node_ci, "validate_ci_originals", content_reader)
    monkeypatch.setattr(node_ci, "_download_artifact", download)
    monkeypatch.setattr(node_ci, "_extract_package", extract)
    monkeypatch.setattr(node_ci, "_authenticate_engine", Mock())
    monkeypatch.setattr(node_ci, "_installed_wheel_binding", wheel)
    monkeypatch.setattr(node_ci, "_current_local_engine", current_engine)
    monkeypatch.setattr(node_ci, "_local_wheel_binding", local_binding)
    return {
        "root": source_root,
        "download_dir": tmp_path / "download",
        "package": package,
        "local": local,
        "authority": authority,
        "platform_reader": platform_reader,
        "facts": facts,
        "source": source,
        "declaration": declaration,
        "blobs": blobs,
        "download": download,
        "extract": extract,
        "wheel": wheel,
        "content_reader": content_reader,
        "current_engine": current_engine,
        "local_binding": local_binding,
        "real_wheel_binding": real_wheel_binding,
        "real_local_binding": real_local_binding,
    }


def _compose_gate(seams: dict[str, Any], **selectors: object) -> dict[str, Any]:
    return node_ci.evaluate_node_ci_gate(
        seams["root"],
        "TASK-0001",
        run_id=selectors.get("run_id", 42),
        attempt=selectors.get("attempt", 2),
        download_dir=selectors.get("download_dir", seams["download_dir"]),
    )


def test_combined_gate_requires_both_live_local_boundaries_under_mocked_ci_observations(
    gate_composition_seams: dict[str, Any],
) -> None:
    seams = gate_composition_seams
    decision = _compose_gate(seams)
    assert decision["passed"] is True
    assert all(
        decision[key] is True
        for key in (
            "local_current",
            "source_tuple_matches",
            "fresh_ci_originals_passed",
            "platform_authenticated",
        )
    )
    assert seams["local"].call_count == 2
    assert seams["authority"].call_count == 3
    assert seams["platform_reader"].call_count == 2
    capture = seams["download"].call_args.kwargs["_capture"]
    seams["download"].assert_called_once_with(
        _platform_observation(),
        name="aiflow-node-ci-42-2",
        destination=seams["download_dir"] / "originals.zip",
        level="V0",
        _capture=capture,
    )
    assert capture["prefix"] == "api-observations"
    assert capture["sealed"] is True
    assert seams["platform_reader"].call_args_list[0].kwargs["_capture"] is capture
    assert (seams["download_dir"] / "api-observations.json").is_file()
    assert seams["wheel"].call_args.args[1] == seams["source"]["engine_artifact"]
    assert (seams["root"] / "sentinel").read_bytes() == b"protected source unchanged"
    assert list(seams["root"].iterdir()) == [seams["root"] / "sentinel"]


def test_later_local_tamper_rejects_even_with_mocked_green_platform_and_content(
    gate_composition_seams: dict[str, Any],
) -> None:
    seams = gate_composition_seams
    seams["local"].side_effect = [
        SimpleNamespace(passed=True, reason_codes=()),
        SimpleNamespace(passed=False, reason_codes=("NODE_EVIDENCE_STALE",)),
    ]
    decision = _compose_gate(seams)
    assert decision["passed"] is False
    assert decision["local_current"] is False
    assert decision["fresh_ci_originals_passed"] is True
    assert decision["platform_authenticated"] is True
    assert "NODE_EVIDENCE_STALE" in decision["reason_codes"]
    assert seams["local"].call_count == 2


def test_failed_initial_local_gate_blocks_provider_and_download(
    gate_composition_seams: dict[str, Any],
) -> None:
    seams = gate_composition_seams
    seams["local"].side_effect = [
        SimpleNamespace(passed=False, reason_codes=("NODE_EVIDENCE_STALE",))
    ]
    decision = _compose_gate(seams)
    assert decision["passed"] is False
    assert "NODE_EVIDENCE_STALE" in decision["reason_codes"]
    assert seams["local"].call_count == 1
    seams["authority"].assert_not_called()
    seams["platform_reader"].assert_not_called()
    seams["download"].assert_not_called()
    assert not seams["download_dir"].exists()


@pytest.mark.parametrize(
    "selector,value",
    [("run_id", True), ("run_id", 0), ("run_id", "42"), ("attempt", False), ("attempt", 0)],
)
def test_bad_combined_gate_selectors_reject_before_local_or_remote_work(
    gate_composition_seams: dict[str, Any], selector: str, value: object
) -> None:
    seams = gate_composition_seams
    assert _compose_gate(seams, **{selector: value})["passed"] is False
    seams["local"].assert_not_called()
    seams["platform_reader"].assert_not_called()
    seams["download"].assert_not_called()
    assert not seams["download_dir"].exists()


@pytest.mark.parametrize(
    "change",
    ["ci_platform", "platform_drift", "source_drift", "wheel", "materials", "content_failed"],
)
def test_combined_gate_cannot_mix_authenticated_attempt_source_or_selected_wheel(
    gate_composition_seams: dict[str, Any], change: str
) -> None:
    seams = gate_composition_seams
    if change == "ci_platform":
        seams["facts"]["evidence"]["platform"]["run_attempt"] = 1
    elif change == "platform_drift":
        later = _platform_observation()
        later["job_id"] = 99
        seams["platform_reader"].side_effect = [_platform_observation(), later]
    elif change == "source_drift":
        later = deepcopy(seams["source"])
        later["binding"]["subject_commit"] = BASE
        seams["authority"].side_effect = [
            (deepcopy(seams["source"]), deepcopy(seams["declaration"]), deepcopy(seams["blobs"])),
            (deepcopy(seams["source"]), deepcopy(seams["declaration"]), deepcopy(seams["blobs"])),
            (later, deepcopy(seams["declaration"]), deepcopy(seams["blobs"])),
        ]
    elif change == "wheel":
        seams["wheel"].return_value = "b" * 64
    elif change == "materials":
        seams["facts"]["admission"]["input_materials_sha256"] = "b" * 64
    else:
        seams["facts"]["passed"] = False
        seams["facts"]["reason_codes"] = ["NODE_EVIDENCE_INVALID"]
    decision = _compose_gate(seams)
    assert decision["passed"] is False
    assert seams["local"].call_count == 2
    if change == "source_drift":
        assert decision["source_tuple_matches"] is False


@pytest.mark.parametrize("placement", ["source", "inside", "ancestor"])
def test_combined_gate_download_cannot_overlap_protected_source(
    gate_composition_seams: dict[str, Any], placement: str
) -> None:
    seams = gate_composition_seams
    target = (
        seams["root"]
        if placement == "source"
        else seams["root"] / "download"
        if placement == "inside"
        else seams["root"].parent
    )
    decision = _compose_gate(seams, download_dir=target)
    assert decision["passed"] is False
    seams["download"].assert_not_called()
    assert seams["local"].call_count == 2
    assert (seams["root"] / "sentinel").read_bytes() == b"protected source unchanged"


@pytest.fixture
def download_stream_seams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    finite_transport_caps: dict[str, tuple[int, ...]],
) -> dict[str, Any]:
    """Exercise the real file sink/hash around a fake runner, never launch gh."""
    payload = b"synthetic binary artifact\x00\xff"
    metadata = {
        "id": 46,
        "size_in_bytes": len(payload),
        "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
    }
    select = Mock(return_value=metadata)
    executable = tmp_path / "tools/gh.exe"
    monkeypatch.setattr(node_ci, "_select_artifact", select)
    monkeypatch.setattr(node_ci, "_gh_executable", lambda: executable)
    monkeypatch.setenv("GH_TOKEN", "synthetic-download-token")
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-other-download-token")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-unrelated-secret")
    observation = {"payload": payload, "result": replace(_process_result(), stdout=b"")}

    def stream(argv: tuple[str, ...], **options: Any) -> NodeProcessResult:
        assert options["stdout_limit"] == finite_transport_caps["V0"][4]
        options["stdout_sink"].write(observation["payload"])
        return observation["result"]

    runner = Mock(side_effect=stream)
    monkeypatch.setattr(process_runner, "run_node_process", runner)
    return {
        "destination": tmp_path / "originals.zip",
        "metadata": metadata,
        "executable": executable,
        "select": select,
        "runner": runner,
        "observation": observation,
        "payload": payload,
    }


def test_download_stream_binds_get_sink_budget_and_actual_binary_digest(
    download_stream_seams: dict[str, Any], finite_transport_caps: dict[str, tuple[int, ...]]
) -> None:
    seams = download_stream_seams
    assert (
        node_ci._download_artifact(
            _platform_observation(),
            name="aiflow-node-ci-42-2",
            destination=seams["destination"],
            level="V0",
        )
        == seams["metadata"]
    )
    assert seams["destination"].read_bytes() == seams["payload"]
    (argv,) = seams["runner"].call_args.args
    assert argv == (
        str(seams["executable"]),
        "api",
        "--hostname",
        "github.com",
        "--method",
        "GET",
        "--header",
        "Accept: application/vnd.github+json",
        f"repos/{REPOSITORY}/actions/artifacts/46/zip",
    )
    options = seams["runner"].call_args.kwargs
    assert options["stdout_limit"] == finite_transport_caps["V0"][4]
    assert options["timeout_seconds"] == 300
    assert options["cwd"] == seams["destination"].parent
    assert options["stdout_sink"].closed
    assert options["environment"]["GH_TOKEN"] == "synthetic-download-token"
    assert "OPENAI_API_KEY" not in options["environment"]
    assert "synthetic-download-token" not in " ".join(argv)
    # Stderr retains the existing bounded process-runner contract, no binary stderr sink.
    assert "stderr_sink" not in options


@pytest.mark.parametrize(
    "fault",
    [
        "timeout",
        "stdout_overflow",
        "stderr_overflow",
        "cleanup",
        "returncode",
        "digest",
        "actual_size",
    ],
)
def test_failed_download_retains_partial_bytes_and_never_reuses_destination(
    download_stream_seams: dict[str, Any],
    finite_transport_caps: dict[str, tuple[int, ...]],
    fault: str,
) -> None:
    seams = download_stream_seams
    if fault == "digest":
        seams["metadata"]["digest"] = "sha256:" + "b" * 64
    elif fault == "actual_size":
        seams["observation"]["payload"] = b"x" * (finite_transport_caps["V0"][4] + 1)
    else:
        changes = {
            "timeout": {"timed_out": True},
            "stdout_overflow": {"stdout_overflow": True},
            "stderr_overflow": {"stderr_overflow": True},
            "cleanup": {"cleanup": "unknown"},
            "returncode": {"returncode": 1},
        }
        seams["observation"]["result"] = replace(_process_result(), stdout=b"", **changes[fault])
    with pytest.raises(ContractError):
        node_ci._download_artifact(
            _platform_observation(),
            name="aiflow-node-ci-42-2",
            destination=seams["destination"],
            level="V0",
        )
    retained = seams["destination"].read_bytes()
    assert retained == seams["observation"]["payload"]
    with pytest.raises((ContractError, OSError)):
        node_ci._download_artifact(
            _platform_observation(),
            name="aiflow-node-ci-42-2",
            destination=seams["destination"],
            level="V0",
        )
    assert seams["destination"].read_bytes() == retained
    assert seams["runner"].call_count == 1


def test_provider_declared_oversize_download_rejects_before_sink_or_process(
    download_stream_seams: dict[str, Any], finite_transport_caps: dict[str, tuple[int, ...]]
) -> None:
    seams = download_stream_seams
    seams["metadata"]["size_in_bytes"] = finite_transport_caps["V0"][4] + 1
    with pytest.raises(ContractError) as caught:
        node_ci._download_artifact(
            _platform_observation(),
            name="aiflow-node-ci-42-2",
            destination=seams["destination"],
            level="V0",
        )
    assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"
    assert not seams["destination"].exists()
    seams["runner"].assert_not_called()


def test_unregistered_download_rejects_before_authentication_or_output(
    download_stream_seams: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    seams = download_stream_seams
    monkeypatch.setattr(node_ci, "CI_CAPS_REGISTERED", False)
    with pytest.raises(ContractError) as caught:
        node_ci._download_artifact(
            _platform_observation(),
            name="aiflow-node-ci-42-2",
            destination=seams["destination"],
            level="V0",
        )
    assert caught.value.code == "NODE_CI_UNAVAILABLE"
    seams["select"].assert_not_called()
    seams["runner"].assert_not_called()
    assert not seams["destination"].exists()


def test_archive_writer_keeps_every_file_and_declared_empty_directory(
    tmp_path: Path, finite_transport_caps: dict[str, tuple[int, ...]]
) -> None:
    files, _index, _manifests, _descriptor = _transport_fixture()
    wrapper = tmp_path / "files.zip"
    wrapper.write_bytes(_zip_bytes(list(files.items())))
    package = node_ci._extract_package(wrapper, tmp_path / "package", level="V0")
    output = tmp_path / "complete.zip"
    measured = node_ci.write_ci_archive(package, output, level="V0")
    payload = output.read_bytes()
    assert measured["size"] == len(payload)
    assert measured["sha256"] == hashlib.sha256(payload).hexdigest()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert measured["entries"] == len(archive.infolist())
        assert {entry.filename for entry in archive.infolist() if entry.is_dir()} == {
            path.relative_to(package).as_posix() + "/"
            for path in package.rglob("*")
            if path.is_dir()
        }
        assert {
            entry.filename: archive.read(entry)
            for entry in archive.infolist()
            if not entry.is_dir()
        } == files
    roundtrip = node_ci._extract_package(output, tmp_path / "roundtrip", level="V0")
    assert node_ci._package_manifests(roundtrip, level="V0") == node_ci._package_manifests(
        package, level="V0"
    )


def test_archive_writer_rejects_insufficient_compressed_reserve_before_opening_output(
    tmp_path: Path, finite_transport_caps: dict[str, tuple[int, ...]]
) -> None:
    files, _index, _manifests, _descriptor = _transport_fixture()
    wrapper = tmp_path / "files.zip"
    wrapper.write_bytes(_zip_bytes(list(files.items())))
    package = node_ci._extract_package(wrapper, tmp_path / "package", level="V0")
    row = list(finite_transport_caps["V0"])
    row[4] = 1024
    finite_transport_caps["V0"] = tuple(row)
    output = tmp_path / "too-small.zip"
    with pytest.raises(ContractError) as caught:
        node_ci.write_ci_archive(package, output, level="V0")
    assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"
    assert not output.exists()


def _job_receipt() -> dict[str, object]:
    return {
        "process_id": 123,
        "creation_time_filetime": 133000000000000001,
        **{
            name: True
            for name in (
                "created_suspended",
                "assigned",
                "initial_membership",
                "resumed",
                "job_empty",
                "stdout_eof",
                "stderr_eof",
                "closed",
            )
        },
        "terminate_requested": False,
    }


def _install_raw_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, documents: dict[str, bytes]
) -> Mock:
    def execute(argv: tuple[str, ...], **_options: object) -> NodeProcessResult:
        endpoint = argv[-1]
        assert endpoint in documents, f"unplanned raw transcript request: {endpoint}"
        return replace(
            _process_result(),
            stdout=documents[endpoint],
            receipt=_job_receipt(),
            stderr=b"synthetic-private-stderr",
        )

    monkeypatch.setattr(node_ci, "_gh_executable", lambda: tmp_path / "gh.exe")
    monkeypatch.setenv("GH_TOKEN", "synthetic-capture-token")
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-capture-second-token")
    runner = Mock(side_effect=execute)
    monkeypatch.setattr(process_runner, "run_node_process", runner)
    return runner


def test_api_capture_preserves_raw_bytes_receipts_and_one_exclusive_final_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = f"repos/{REPOSITORY}"
    second = f"repos/{REPOSITORY}/actions/jobs/43"
    raw = b'{ "id" : 42 }\n'
    _install_raw_transcript(tmp_path, monkeypatch, {first: raw, second: b'{"id":43}'})
    capture = node_ci._new_api_capture()
    assert node_ci.github_get(first, _capture=capture) == {"id": 42}
    node_ci._write_api_observations(tmp_path, capture, seal=False)
    response = tmp_path / "control/api-observations/000001.response.raw"
    assert response.read_bytes() == raw
    assert not (tmp_path / "control/api-observations.json").exists()
    before = response.stat()
    node_ci.github_get(second, _capture=capture)
    node_ci._write_api_observations(tmp_path, capture)
    index_path = tmp_path / "control/api-observations.json"
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)
    assert index_bytes == _canonical_test(index)
    assert capture["sealed"] is True
    assert capture["written"] == 2
    assert capture["total_bytes"] == len(index_bytes) + sum(
        len(item["response"]) + len(item["receipt"]) for item in capture["observations"]
    )
    entry = index["observations"][0]
    assert entry["sequence"] == 1
    assert entry["method"] == "GET"
    assert entry["endpoint"] == first
    assert entry["response"] == _reference("control/api-observations/000001.response.raw", raw)
    assert (
        entry["response_canonical_sha256"]
        == hashlib.sha256(_canonical_test({"id": 42})).hexdigest()
    )
    assert json.loads((tmp_path / entry["receipt"]["ref"]).read_bytes()) == _job_receipt()
    assert response.stat().st_mtime_ns == before.st_mtime_ns
    node_ci._validate_api_observations(tmp_path)
    retained = b"".join(path.read_bytes() for path in tmp_path.rglob("*") if path.is_file())
    assert b"synthetic-capture-token" not in retained
    assert b"synthetic-private-stderr" not in retained
    with pytest.raises(ContractError):
        node_ci._write_api_observations(tmp_path, capture)
    assert index_path.read_bytes() == index_bytes


def test_capture_records_each_exact_attempt_page_as_its_own_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    documents = {
        ENDPOINT + "?per_page=100&page=1": _canonical_test(
            {"total_count": 101, "jobs": [{"id": i} for i in range(1, 101)]}
        ),
        ENDPOINT + "?per_page=100&page=2": b'{"total_count":101,"jobs":[{"id":101}]}',
    }
    runner = _install_raw_transcript(tmp_path, monkeypatch, documents)
    capture = node_ci._new_api_capture()
    assert len(node_ci.github_get(ENDPOINT, paginate=True, _capture=capture)) == 101
    assert runner.call_count == 2
    node_ci._write_api_observations(tmp_path, capture)
    index = json.loads((tmp_path / "control/api-observations.json").read_bytes())
    assert [row["endpoint"] for row in index["observations"]] == list(documents)
    assert [row["sequence"] for row in index["observations"]] == [1, 2]
    for row in index["observations"]:
        assert (tmp_path / row["response"]["ref"]).read_bytes() == documents[row["endpoint"]]
    node_ci._validate_api_observations(tmp_path)


def test_capture_propagates_through_actual_workflow_graph_and_artifact_selectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transcript = _workflow_transcript(completed=True)
    transcript.update(_artifact_transcript())
    documents = {}
    for endpoint, value in transcript.items():
        if endpoint == ENDPOINT or endpoint.endswith("/artifacts"):
            key = "jobs" if endpoint == ENDPOINT else "artifacts"
            documents[endpoint + "?per_page=100&page=1"] = _canonical_test(
                {"total_count": len(value), key: value}
            )
        else:
            documents[endpoint] = _canonical_test(value)
    runner = _install_raw_transcript(tmp_path, monkeypatch, documents)
    capture = node_ci._new_api_capture()
    platform = node_ci.authenticate_workflow(
        42,
        REPOSITORY,
        WORKFLOW,
        "aiflow-node-ci",
        run_id=42,
        attempt=2,
        completed=True,
        _capture=capture,
    )
    assert (
        node_ci._select_artifact(platform, name="aiflow-node-ci-42-2", _capture=capture)["id"] == 46
    )
    assert runner.call_count == len(documents)
    assert {item["entry"]["endpoint"] for item in capture["observations"]} == set(documents)
    node_ci._write_api_observations(tmp_path, capture)
    node_ci._validate_api_observations(tmp_path)


@pytest.mark.parametrize(
    "change", ["missing", "bool_pid", "missing_eof", "terminated", "environment"]
)
def test_capture_requires_closed_successful_job_receipt_without_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    receipt = _job_receipt()
    if change == "bool_pid":
        receipt["process_id"] = True
    elif change == "missing_eof":
        receipt["stdout_eof"] = False
    elif change == "terminated":
        receipt["terminate_requested"] = True
    elif change == "environment":
        receipt["environment"] = {"GH_TOKEN": "synthetic-leak"}
    result = replace(_process_result(), receipt=None if change == "missing" else receipt)
    monkeypatch.setattr(node_ci, "_gh_executable", lambda: tmp_path / "gh.exe")
    monkeypatch.setattr(process_runner, "run_node_process", Mock(return_value=result))
    capture = node_ci._new_api_capture()
    with pytest.raises(ContractError):
        node_ci.github_get(ENDPOINT, _capture=capture)
    assert capture["observations"] == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("bound", ["count", "aggregate", "response"])
def test_capture_enforces_response_count_and_actual_aggregate_bounds_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: str
) -> None:
    raw = b'{"id":42}'
    if bound == "response":
        raw = _canonical_test({"padding": "x" * (1024 * 1024)})
    _install_raw_transcript(tmp_path, monkeypatch, {ENDPOINT: raw})
    capture = node_ci._new_api_capture()
    if bound != "response":
        node_ci.github_get(ENDPOINT, _capture=capture)
        if bound == "count":
            monkeypatch.setattr(node_ci, "MAX_ENTRIES", 1)
        else:
            monkeypatch.setattr(node_ci, "MAX_JSON_BYTES", capture["total_bytes"])
    original_count = len(capture["observations"])
    original_total = capture["total_bytes"]
    with pytest.raises(ContractError):
        node_ci.github_get(ENDPOINT, _capture=capture)
    assert len(capture["observations"]) == original_count
    assert capture["total_bytes"] == original_total
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("prefix", ["../outside", "control/other", "api-observations/other"])
def test_api_capture_only_uses_fixed_owned_prefixes(prefix: str) -> None:
    with pytest.raises(ContractError):
        node_ci._new_api_capture(prefix)


@pytest.mark.parametrize(
    "change",
    [
        "raw",
        "missing_receipt",
        "extra_file",
        "sequence_bool",
        "canonical_digest",
        "index_noncanonical",
    ],
)
def test_capture_reader_rejects_changed_or_missing_originals_without_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    _install_raw_transcript(tmp_path, monkeypatch, {ENDPOINT: b'{"id":42}'})
    capture = node_ci._new_api_capture()
    node_ci.github_get(ENDPOINT, _capture=capture)
    node_ci._write_api_observations(tmp_path, capture)
    index_path = tmp_path / "control/api-observations.json"
    index = json.loads(index_path.read_bytes())
    if change == "raw":
        (tmp_path / index["observations"][0]["response"]["ref"]).write_bytes(b'{"id":43}')
    elif change == "missing_receipt":
        (tmp_path / index["observations"][0]["receipt"]["ref"]).unlink()
    elif change == "extra_file":
        (tmp_path / "control/api-observations/unknown.raw").write_bytes(b"x")
    else:
        if change == "sequence_bool":
            index["observations"][0]["sequence"] = True
        elif change == "canonical_digest":
            index["observations"][0]["response_canonical_sha256"] = "b" * 64
        index_path.write_bytes(
            json.dumps(index, indent=2).encode()
            if change == "index_noncanonical"
            else _canonical_test(index)
        )
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    with pytest.raises((ContractError, OSError)):
        node_ci._validate_api_observations(tmp_path)
    assert {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    } == before


def test_empty_capture_index_does_not_stand_in_for_actual_api_originals(tmp_path: Path) -> None:
    node_ci._write_api_observations(tmp_path, node_ci._new_api_capture())
    with pytest.raises(ContractError):
        node_ci._validate_api_observations(tmp_path)


def test_capture_write_failure_still_runs_final_local_gate_and_rejects(
    gate_composition_seams: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    seams = gate_composition_seams
    monkeypatch.setattr(
        node_ci,
        "_write_api_observations",
        Mock(
            side_effect=ContractError(
                "synthetic capture failure", code="NODE_CI_API_ORIGINALS_INVALID"
            )
        ),
    )
    decision = _compose_gate(seams)
    assert decision["passed"] is False
    assert decision["platform_authenticated"] is False
    assert "NODE_CI_API_ORIGINALS_INVALID" in decision["reason_codes"]
    assert seams["local"].call_count == 2


@pytest.mark.parametrize("completed", [False, True])
def test_source_workflow_requires_actual_public_source_repository_observation(
    monkeypatch: pytest.MonkeyPatch, completed: bool
) -> None:
    transcript = _workflow_transcript(completed=completed, source=True)
    request = _install_transcript(monkeypatch, transcript)
    observation = node_ci.authenticate_workflow(
        1319293089,
        "MaginaLW/harness-model",
        ".github/workflows/node-engine-artifacts.yml",
        "node-engine-artifacts",
        run_id=42,
        attempt=2,
        completed=completed,
    )
    assert observation["repository_id"] == 1319293089
    assert observation["full_name"] == "MaginaLW/harness-model"
    assert observation["workflow_path"] == ".github/workflows/node-engine-artifacts.yml"
    assert observation["job_key"] == "node-engine-artifacts"
    assert observation["workflow_ref"] == "refs/pull/7/merge"
    assert request.call_args_list[0].args == ("repos/MaginaLW/harness-model",)
    assert set(call.args[0] for call in request.call_args_list) == set(transcript)


@pytest.mark.parametrize("source", [False, True])
@pytest.mark.parametrize("change", ["opposite", "missing", "integer", "string"])
def test_repository_visibility_cannot_be_inferred_or_coerced_from_other_claims(
    monkeypatch: pytest.MonkeyPatch, source: bool, change: str
) -> None:
    transcript = _workflow_transcript(completed=True, source=source)
    endpoint = _endpoints(source=source)["repository"]
    repository = transcript[endpoint]
    if change == "opposite":
        repository["private"] = source
    elif change == "missing":
        del repository["private"]
    elif change == "integer":
        repository["private"] = 0 if source else 1
    else:
        repository["private"] = "false" if source else "true"
    # Correct-looking nested run/PR facts and caller environment cannot fill the actual GET.
    monkeypatch.setenv("GITHUB_REPOSITORY_VISIBILITY", "public" if source else "private")
    request = _install_transcript(monkeypatch, transcript)
    with pytest.raises(ContractError):
        node_ci.authenticate_workflow(
            1319293089 if source else 42,
            "MaginaLW/harness-model" if source else REPOSITORY,
            ".github/workflows/node-engine-artifacts.yml" if source else WORKFLOW,
            "node-engine-artifacts" if source else "aiflow-node-ci",
            run_id=42,
            attempt=2,
            completed=True,
        )
    request.assert_called_once_with(endpoint, paginate=False)


@pytest.mark.parametrize("failure", ["aiflow", "os"])
def test_final_authority_exception_rejects_despite_green_components_and_final_local_gate(
    gate_composition_seams: dict[str, Any], failure: str
) -> None:
    seams = gate_composition_seams
    valid = (deepcopy(seams["source"]), deepcopy(seams["declaration"]), deepcopy(seams["blobs"]))
    error = (
        AiflowError("synthetic final authority unavailable", code="NODE_CI_SOURCE_UNAVAILABLE")
        if failure == "aiflow"
        else OSError("synthetic final authority unavailable")
    )
    # The exception is at the last source recheck, after all CI component flags were set.
    # A subsequently healthy provider/local observation must not repair this failed decision.
    seams["authority"].side_effect = [deepcopy(valid), deepcopy(valid), error, deepcopy(valid)]
    decision = _compose_gate(seams)
    assert decision["passed"] is False
    assert decision["local_current"] is True
    assert seams["local"].call_count == 2
    assert seams["authority"].call_count == 3
    assert seams["platform_reader"].call_count == 2
    assert (seams["download_dir"] / "api-observations.json").is_file()
    assert ("NODE_CI_SOURCE_UNAVAILABLE" if failure == "aiflow" else "NODE_CI_INVALID") in decision[
        "reason_codes"
    ]


def _wheel_record(payload: dict[str, bytes]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name, data in sorted(payload.items()):
        if name.endswith(".dist-info/RECORD"):
            writer.writerow((name, "", ""))
        else:
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
            writer.writerow((name, "sha256=" + digest, str(len(data))))
    return output.getvalue().encode()


def _same_payload_wheels() -> tuple[bytes, bytes, dict[str, bytes], dict[str, bytes]]:
    """Complete synthetic aiflow wheel/resources; not a real installed-runtime proof."""
    from aiflow.resource_bundle import build_bundle

    manifest, resources = build_bundle(Path(__file__).resolve().parents[2])
    payload = {
        "aiflow/__init__.py": b'__version__ = "0.2.0"\n',
        "aiflow/_bundled_resources/manifest.json": _canonical_test(manifest),
        "aiflow-0.2.0.dist-info/METADATA": b"Metadata-Version: 2.4\nName: aiflow\nVersion: 0.2.0\n",
        "aiflow-0.2.0.dist-info/WHEEL": (
            b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ),
        **{"aiflow/_bundled_resources/" + name: data for name, data in resources.items()},
        "aiflow-0.2.0.dist-info/RECORD": b"",
    }
    payload["aiflow-0.2.0.dist-info/RECORD"] = _wheel_record(payload)
    variants = []
    for comment in (b"selected-A", b"repacked-B"):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as wheel:
            for name, data in sorted(payload.items()):
                wheel.writestr(zipfile.ZipInfo(name), data)
            wheel.comment = comment
        variants.append(output.getvalue())
    return variants[0], variants[1], payload, resources


def _source_archive_for_wheel(
    wheel: bytes, payload: dict[str, bytes], resources: dict[str, bytes]
) -> tuple[bytes, dict[str, Any]]:
    source = io.BytesIO()
    source_members = {
        "LICENSE": b"synthetic test license\n",
        "pyproject.toml": b"# synthetic test source\n",
        "setup.py": b"# synthetic test source\n",
        "MANIFEST.in": b"# synthetic test source\n",
        "PKG-INFO": b"Name: aiflow\nVersion: 0.2.0\n",
        "src/aiflow/__init__.py": payload["aiflow/__init__.py"],
        **{".ai/" + name: data for name, data in resources.items()},
    }
    with tarfile.open(fileobj=source, mode="w:gz") as archive:
        for name, data in sorted(source_members.items()):
            info = tarfile.TarInfo("aiflow-0.2.0/" + name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    members = {
        "direct/aiflow-0.2.0-py3-none-any.whl": wheel,
        "sdist/aiflow-0.2.0.tar.gz": source.getvalue(),
        "sdist-rebuilt/aiflow-0.2.0-py3-none-any.whl": wheel,
    }
    manifest = {
        "kind": "aiflow-node-engine-build",
        "schema_version": "1.0",
        "repository_id": 1319293089,
        "source_head": HEAD,
        "workflow_path": ".github/workflows/node-engine-artifacts.yml",
        "workflow_blob_sha256": SHA,
        "job_key": "node-engine-artifacts",
        "run_id": 42,
        "run_attempt": 2,
        "python_version": [3, 11, 9],
        "setuptools_version": "82.0.1",
        "members": [
            {
                "path": name,
                "origin": origin,
                "size": len(members[name]),
                "sha256": hashlib.sha256(members[name]).hexdigest(),
            }
            for name, origin in zip(members, ("direct", "source", "sdist_rebuilt"), strict=True)
        ],
        "package_payload_sha256": hashlib.sha256(
            _canonical_test(
                [
                    {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    for name, data in sorted(payload.items())
                ]
            )
        ).hexdigest(),
        "resource_manifest_sha256": hashlib.sha256(
            payload["aiflow/_bundled_resources/manifest.json"]
        ).hexdigest(),
    }
    members["build-manifest.json"] = _canonical_test(manifest)
    archive = _zip_bytes(list(members.items()))
    selection = _source_selection()
    selection["artifact_digest"] = "sha256:" + hashlib.sha256(archive).hexdigest()
    for field, member in (
        ("wheel", "direct/aiflow-0.2.0-py3-none-any.whl"),
        ("sdist", "sdist/aiflow-0.2.0.tar.gz"),
        ("build_manifest", "build-manifest.json"),
    ):
        selection[field] = {
            "member": member,
            "size": len(members[member]),
            "sha256": hashlib.sha256(members[member]).hexdigest(),
        }
    return archive, selection


def _install_fixture_payload(
    site: Path, payload: dict[str, bytes], wheel_path: Path, wheel: bytes
) -> None:
    files = dict(payload)
    files["aiflow-0.2.0.dist-info/direct_url.json"] = _canonical_test(
        {
            "url": wheel_path.as_uri(),
            "archive_info": {"hashes": {"sha256": hashlib.sha256(wheel).hexdigest()}},
        }
    )
    files["aiflow-0.2.0.dist-info/RECORD"] = _wheel_record(files)
    for name, data in files.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _collect_fixture_engine(
    site: Path, metadata_prefix: Path, metadata_site: Path
) -> dict[str, Any]:
    """Narrow collector seam, recomputing real current receipt/RECORD/resource bytes."""
    rows = []
    for path in sorted(site.rglob("*")):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        info = path.stat()
        rows.append(
            {
                "path": str(metadata_site / path.relative_to(site)),
                "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "identity": {
                    "device": info.st_dev,
                    "inode": info.st_ino,
                    "nlink": info.st_nlink,
                    "size": info.st_size,
                    "mtime_ns": info.st_mtime_ns,
                    "ctime_ns": info.st_ctime_ns,
                    "mode": info.st_mode,
                    "attributes": getattr(info, "st_file_attributes", 0),
                },
            }
        )
    return {
        "python": str(metadata_prefix / "Scripts/python.exe"),
        "distributions": [{"name": "aiflow", "version": "0.2.0", "files": rows}],
        "startup": {
            "python_environment": {
                "prefix": str(metadata_prefix),
                "active_site_roots": [str(metadata_site)],
            }
        },
    }


def _real_local_and_ci_wheels(
    seams: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    repacked_local: bool = False,
) -> dict[str, Any]:
    selected, repacked, payload, resources = _same_payload_wheels()
    assert selected != repacked
    with (
        zipfile.ZipFile(io.BytesIO(selected)) as left,
        zipfile.ZipFile(io.BytesIO(repacked)) as right,
    ):
        assert {name: left.read(name) for name in left.namelist()} == {
            name: right.read(name) for name in right.namelist()
        }
    archive_bytes, selection = _source_archive_for_wheel(selected, payload, resources)
    artifact = seams["package"] / "originals/artifact/engine-source.zip"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(archive_bytes)
    chosen = artifact.parent / selection["wheel"]["member"]
    chosen.parent.mkdir(parents=True)
    chosen.write_bytes(selected)
    local_wheel = tmp_path / "local-B.whl" if repacked_local else tmp_path / "local-A.whl"
    local_wheel.write_bytes(repacked if repacked_local else selected)
    local_prefix = tmp_path / "l"
    local_site = local_prefix / "site-packages"
    _install_fixture_payload(local_site, payload, local_wheel, local_wheel.read_bytes())
    ci_prefix = Path("C:/synthetic/producer/engine")
    ci_metadata_site = ci_prefix / "Lib/site-packages"
    ci_site = seams["package"] / "originals/engine/Lib/site-packages"
    _install_fixture_payload(ci_site, payload, chosen, selected)
    inputs = {"engine": _collect_fixture_engine(ci_site, ci_prefix, ci_metadata_site)}
    inputs_raw = _canonical_test(inputs)
    (seams["package"] / "originals/control/input-materials.json").write_bytes(inputs_raw)
    seams["source"]["engine_artifact"] = selection
    seams["authority"].side_effect = [
        (deepcopy(seams["source"]), deepcopy(seams["declaration"]), deepcopy(seams["blobs"]))
        for _ in range(3)
    ]
    contract_sha = seams["declaration"]["tier_contracts"]["V0"]
    monkeypatch.setattr(node_ci, "_installed_wheel_binding", seams["real_wheel_binding"])
    monkeypatch.setattr(node_ci, "_local_wheel_binding", seams["real_local_binding"])
    collector = Mock(
        side_effect=lambda: _collect_fixture_engine(local_site, local_prefix, local_site)
    )
    monkeypatch.setattr(node_ci, "_current_local_engine", collector)
    content = node_ci._installed_wheel_binding(
        artifact, selection, inputs, contract_sha, package_root=seams["package"]
    )
    seams["facts"]["admission"]["engine_content_sha256"] = content
    seams["facts"]["admission"]["input_materials_sha256"] = hashlib.sha256(inputs_raw).hexdigest()
    return {
        "artifact": artifact,
        "chosen": chosen,
        "local_wheel": local_wheel,
        "local_site": local_site,
        "selection": selection,
        "contract_sha": contract_sha,
        "collector": collector,
        "content": content,
        "selected": selected,
        "repacked": repacked,
    }


def test_combined_gate_rejects_local_repacked_wheel_even_when_ci_uses_selected_raw_bytes(
    gate_composition_seams: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seams = gate_composition_seams
    fixture = _real_local_and_ci_wheels(seams, tmp_path, monkeypatch, repacked_local=True)
    # B has the same payload, version, RECORD and bundled resources as A, but its real
    # local direct_url receipt names B's distinct container SHA. The current collector
    # reads actual files; neither binding verifier is mocked to return a rejection.
    with pytest.raises(ContractError):
        node_ci._local_wheel_binding(
            fixture["artifact"], fixture["selection"], fixture["contract_sha"]
        )
    decision = _compose_gate(seams)
    assert decision["passed"] is False
    assert seams["local"].call_count == 2
    assert (seams["download_dir"] / "api-observations.json").is_file()


def test_same_selected_raw_reference_binds_current_local_and_retained_ci_roles_separately(
    gate_composition_seams: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seams = gate_composition_seams
    fixture = _real_local_and_ci_wheels(seams, tmp_path, monkeypatch)
    observed = node_ci._local_wheel_binding(
        fixture["artifact"], fixture["selection"], fixture["contract_sha"]
    )
    assert observed["engine_content_sha256"] == fixture["content"]
    assert (
        observed["engine_sha256"]
        == hashlib.sha256(_canonical_test(fixture["collector"]())).hexdigest()
    )
    collected_before_gate = fixture["collector"].call_count
    assert _compose_gate(seams)["passed"] is True
    assert fixture["collector"].call_count - collected_before_gate >= 3
    assert seams["local"].call_count == 2


@pytest.mark.parametrize(
    "change", ["receipt", "record", "module", "resources", "archive", "selected_member"]
)
def test_final_local_installation_or_selected_raw_drift_rejects_after_green_ci_checks(
    gate_composition_seams: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    seams = gate_composition_seams
    fixture = _real_local_and_ci_wheels(seams, tmp_path, monkeypatch)
    calls = 0

    def authority(
        *_args: object, **_kwargs: object
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes]]:
        nonlocal calls
        calls += 1
        if calls == 3:
            if change == "receipt":
                target = fixture["local_site"] / "aiflow-0.2.0.dist-info/direct_url.json"
                direct = json.loads(target.read_bytes())
                direct["archive_info"]["hashes"]["sha256"] = hashlib.sha256(
                    fixture["repacked"]
                ).hexdigest()
                target.write_bytes(_canonical_test(direct))
            else:
                target = {
                    "record": fixture["local_site"] / "aiflow-0.2.0.dist-info/RECORD",
                    "module": fixture["local_site"] / "aiflow/__init__.py",
                    "resources": fixture["local_site"] / "aiflow/_bundled_resources/manifest.json",
                    "archive": fixture["artifact"],
                    "selected_member": fixture["chosen"],
                }[change]
                target.write_bytes(target.read_bytes() + b"\n")
        return deepcopy(seams["source"]), deepcopy(seams["declaration"]), deepcopy(seams["blobs"])

    seams["authority"].side_effect = authority
    decision = _compose_gate(seams)
    assert calls == 3
    assert decision["passed"] is False
    assert seams["local"].call_count == 2
    assert (seams["download_dir"] / "api-observations.json").is_file()
    # No historical direct_url URL is followed, and no enduring URL path convention
    # is imposed. This covers only current receipt/RECORD/resources/member bytes and
    # the selected raw reference actually read; real dual-host installation is separate.


@pytest.fixture(scope="module")
def ordinary_container_examples() -> dict[str, Any]:
    """Reuse complete ordinary-format container bytes, without building or contacting Actions."""
    selected, repacked, payload, resources = _same_payload_wheels()
    archive, selection = _source_archive_for_wheel(selected, payload, resources)
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        members = {name: source.read(name) for name in source.namelist()}
    return {
        "selected": selected,
        "repacked": repacked,
        "payload": payload,
        "archive": archive,
        "selection": selection,
        "members": members,
    }


def test_public_wheel_inspector_binds_actual_payload_record_and_resources_without_extraction(
    tmp_path: Path, ordinary_container_examples: dict[str, Any]
) -> None:
    examples = ordinary_container_examples
    expected = {
        "package_payload_sha256": hashlib.sha256(
            _canonical_test(
                [
                    {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    for name, data in sorted(examples["payload"].items())
                ]
            )
        ).hexdigest(),
        "resource_manifest_sha256": hashlib.sha256(
            examples["payload"]["aiflow/_bundled_resources/manifest.json"]
        ).hexdigest(),
    }
    for label in ("selected", "repacked"):
        wheel = tmp_path / (label + ".whl")
        wheel.write_bytes(examples[label])
        before = wheel.stat()
        assert node_ci.inspect_engine_wheel(wheel) == expected
        assert wheel.read_bytes() == examples[label]
        assert wheel.stat().st_mtime_ns == before.st_mtime_ns
    assert {path.name for path in tmp_path.iterdir()} == {"selected.whl", "repacked.whl"}


@pytest.mark.parametrize(
    "change",
    [
        "outside_package",
        "missing_init",
        "record_inventory",
        "record_self_hash",
        "payload_digest",
        "invalid_zip",
    ],
)
def test_public_wheel_inspector_rejects_existing_closed_container_guards(
    tmp_path: Path, ordinary_container_examples: dict[str, Any], change: str
) -> None:
    payload = dict(ordinary_container_examples["payload"])
    record = "aiflow-0.2.0.dist-info/RECORD"
    if change == "outside_package":
        payload["private.txt"] = b"not a package member"
        payload[record] = _wheel_record(payload)
    elif change == "missing_init":
        del payload["aiflow/__init__.py"]
        payload[record] = _wheel_record(payload)
    elif change == "record_inventory":
        payload[record] = b"\n".join(payload[record].splitlines()[1:]) + b"\n"
    elif change == "record_self_hash":
        rows = list(csv.reader(io.StringIO(payload[record].decode())))
        for row in rows:
            if row[0] == record:
                row[1] = "sha256=" + SHA
        output = io.StringIO(newline="")
        csv.writer(output, lineterminator="\n").writerows(rows)
        payload[record] = output.getvalue().encode()
    elif change == "payload_digest":
        payload["aiflow/__init__.py"] += b"# changed without updating RECORD\n"
    raw = b"not a ZIP" if change == "invalid_zip" else _zip_bytes(sorted(payload.items()))
    wheel = tmp_path / "rejected.whl"
    wheel.write_bytes(raw)
    with pytest.raises(ContractError):
        node_ci.inspect_engine_wheel(wheel)
    assert wheel.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [wheel]


@pytest.mark.parametrize(
    "change", ["member_digest", "rebuilt_payload", "selected_ref", "producer_binding"]
)
def test_complete_source_archive_rejects_existing_payload_and_producer_binding_guards(
    tmp_path: Path, ordinary_container_examples: dict[str, Any], change: str
) -> None:
    examples = ordinary_container_examples
    members = dict(examples["members"])
    manifest = json.loads(members["build-manifest.json"])
    selection = deepcopy(examples["selection"])
    if change == "member_digest":
        manifest["members"][0]["sha256"] = "b" * 64
    elif change == "rebuilt_payload":
        rebuilt = dict(examples["payload"])
        rebuilt["aiflow/__init__.py"] += b"# distinct rebuilt payload\n"
        rebuilt["aiflow-0.2.0.dist-info/RECORD"] = _wheel_record(rebuilt)
        raw_rebuilt = _zip_bytes(sorted(rebuilt.items()))
        name = "sdist-rebuilt/aiflow-0.2.0-py3-none-any.whl"
        members[name] = raw_rebuilt
        manifest["members"][2]["size"] = len(raw_rebuilt)
        manifest["members"][2]["sha256"] = hashlib.sha256(raw_rebuilt).hexdigest()
    elif change == "producer_binding":
        manifest["source_head"] = BASE
    members["build-manifest.json"] = _canonical_test(manifest)
    raw = _zip_bytes(list(members.items()))
    selection["artifact_digest"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    selection["build_manifest"] = {
        "member": "build-manifest.json",
        "size": len(members["build-manifest.json"]),
        "sha256": hashlib.sha256(members["build-manifest.json"]).hexdigest(),
    }
    if change == "selected_ref":
        selection["wheel"]["size"] += 1
    archive = tmp_path / "rejected-source.zip"
    archive.write_bytes(raw)
    with pytest.raises(ContractError):
        node_ci.validate_engine_artifact_archive(archive, selection)
    assert archive.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [archive]


@pytest.fixture
def source_helper_real_child(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Substitute only public argv; both old subprocess and new Job run real children."""
    if os.name != "nt":
        pytest.skip("real Windows Job originals require a Windows host")
    helper_path = Path(__file__).resolve().parents[2] / "tools/ci/build_node_engine.py"
    spec = importlib.util.spec_from_file_location("synthetic_source_build_job", helper_path)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    script = tmp_path / "public_child.py"
    script.write_text(
        "import os, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "mode, output, marker = sys.argv[1:]\n"
        "if mode != 'git-output':\n"
        "    (Path(output) / 'aiflow-0.2.0-py3-none-any.whl').write_bytes(b'public placeholder')\n"
        "if mode in ('git-output', 'build-stdout'):\n"
        "    for _ in range(272): os.write(1, b'x' * 65536)\n"
        "elif mode == 'build-stderr':\n"
        "    for _ in range(17): os.write(2, b'e' * 65536)\n"
        "elif mode in ('build-timeout', 'build-failed'):\n"
        "    os.write(1, b'public-partial-stdout'); os.write(2, b'public-partial-stderr')\n"
        "    if mode == 'build-failed': sys.exit(7)\n"
        "    time.sleep(4); Path(marker).write_text('late-parent')\n"
        "elif mode == 'build-descendant':\n"
        "    code = 'import time; from pathlib import Path; time.sleep(1); Path('"
        " + repr(marker) + ').write_text(\"descendant-finished\")'\n"
        "    subprocess.Popen([sys.executable, '-I', '-B', '-c', code])\n",
        encoding="utf-8",
    )
    source, work = tmp_path / "s", tmp_path / "w"
    source.mkdir()
    work.mkdir()
    output, marker = work / "ordinary", work / "descendant.txt"
    real_subprocess_run = subprocess.run
    real_run_job = getattr(helper, "_run_job", None)
    observed: dict[str, Any] = {"mode": "", "job_calls": 0, "legacy_calls": []}

    def public_argv(original: object) -> tuple[str, ...]:
        arguments = tuple(original)
        if observed["mode"] == "git-output":
            assert arguments[1:] == (
                "--no-optional-locks",
                "-c",
                "core.fsmonitor=false",
                "synthetic-read-only",
            )
        else:
            assert arguments[1:] == (
                "-I",
                "-B",
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--outdir",
                str(output),
                str(source),
            )
        return (sys.executable, "-I", "-B", str(script), observed["mode"], str(output), str(marker))

    def legacy_adapter(argv: object, **options: Any) -> subprocess.CompletedProcess[bytes]:
        command = public_argv(argv)
        observed["legacy_calls"].append({"capture_output": options.get("capture_output", False)})
        if observed["mode"] == "build-timeout":
            assert options["timeout"] == 180
            options["timeout"] = 1  # Fixture-only deadline; production remains 180 seconds.
        result = real_subprocess_run(command, **options)
        observed["legacy_calls"][-1]["stdout_bytes"] = len(result.stdout or b"")
        return result

    def job_adapter(argv: tuple[str, ...], **options: Any) -> NodeProcessResult:
        command = public_argv(argv)
        observed["job_calls"] += 1
        assert real_run_job is not None
        if observed["mode"] == "build-timeout":
            assert options["timeout_seconds"] == 180
            options["timeout_seconds"] = 1
        return real_run_job(command, **options)

    monkeypatch.setattr(helper.subprocess, "run", legacy_adapter)
    monkeypatch.setattr(helper, "_run_job", job_adapter, raising=False)
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "TMPDIR"}
    }
    return {
        "helper": helper,
        "source": source,
        "work": work,
        "output": output,
        "marker": marker,
        "environment": environment,
        "observed": observed,
    }


def _source_build_receipt(case: dict[str, Any]) -> dict[str, Any]:
    receipt = json.loads((case["work"] / "ordinary.receipt.json").read_bytes())
    assert receipt["cleanup"] == "confirmed"
    job = receipt["receipt"]
    assert all(
        job[name] is True
        for name in (
            "created_suspended",
            "assigned",
            "initial_membership",
            "resumed",
            "job_empty",
            "stdout_eof",
            "stderr_eof",
            "closed",
        )
    )
    for stream, limit in (("stdout", 16 * 1024 * 1024), ("stderr", 1024 * 1024)):
        reference = receipt[stream]
        assert reference["path"] == "ordinary." + stream + ".raw"
        raw = (case["work"] / reference["path"]).read_bytes()
        assert len(raw) <= limit
        assert reference["size"] == len(raw)
        assert reference["sha256"] == hashlib.sha256(raw).hexdigest()
    assert case["observed"]["job_calls"] == 1
    assert case["observed"]["legacy_calls"] == []
    return receipt


def test_source_git_output_is_bounded_during_real_job_capture(
    source_helper_real_child: dict[str, Any],
) -> None:
    case = source_helper_real_child
    case["observed"]["mode"] = "git-output"
    with pytest.raises(ValueError) as caught:
        case["helper"]._git(case["source"], "synthetic-read-only")
    result = getattr(caught.value, "result", None)
    assert result is not None
    assert result.stdout_overflow is True
    assert result.cleanup == "confirmed"
    assert result.receipt["job_empty"] is True
    assert result.receipt["stdout_eof"] is True
    assert result.receipt["stderr_eof"] is True
    assert result.receipt["closed"] is True
    assert len(caught.value.stdout) <= 16 * 1024 * 1024
    assert len(caught.value.stderr) <= 1024 * 1024
    assert case["observed"]["job_calls"] == 1
    assert case["observed"]["legacy_calls"] == []


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_source_build_stream_overflow_rejects_with_real_bounded_partial_originals(
    source_helper_real_child: dict[str, Any], stream: str
) -> None:
    case = source_helper_real_child
    case["observed"]["mode"] = "build-" + stream
    with pytest.raises(ValueError):
        case["helper"]._build(
            case["source"], case["output"], "wheel", case["work"], case["environment"]
        )
    receipt = _source_build_receipt(case)
    assert receipt[stream + "_overflow"] is True
    assert receipt["timed_out"] is False


def test_source_build_timeout_retains_real_partial_eof_and_job_cleanup(
    source_helper_real_child: dict[str, Any],
) -> None:
    case = source_helper_real_child
    case["observed"]["mode"] = "build-timeout"
    with pytest.raises(ValueError):
        case["helper"]._build(
            case["source"], case["output"], "wheel", case["work"], case["environment"]
        )
    receipt = _source_build_receipt(case)
    assert receipt["timed_out"] is True
    assert receipt["receipt"]["terminate_requested"] is True
    assert (case["work"] / "ordinary.stdout.raw").read_bytes() == b"public-partial-stdout"
    assert (case["work"] / "ordinary.stderr.raw").read_bytes() == b"public-partial-stderr"
    assert not case["marker"].exists()


def test_source_build_success_waits_for_owned_descendant_and_both_pipe_eofs(
    source_helper_real_child: dict[str, Any],
) -> None:
    case = source_helper_real_child
    case["observed"]["mode"] = "build-descendant"
    completed_before_return = False
    try:
        case["helper"]._build(
            case["source"], case["output"], "wheel", case["work"], case["environment"]
        )
        completed_before_return = case["marker"].exists()
    finally:
        # The pre-fix public child is finite. Wait out that exact owned child even on RED.
        deadline = time.monotonic() + 5
        while not case["marker"].exists() and time.monotonic() < deadline:
            time.sleep(0.02)
    assert completed_before_return is True
    receipt = _source_build_receipt(case)
    assert receipt["returncode"] == 0
    assert receipt["timed_out"] is False


def test_source_build_failed_exit_keeps_real_bounded_raw_and_job_receipt(
    source_helper_real_child: dict[str, Any],
) -> None:
    case = source_helper_real_child
    case["observed"]["mode"] = "build-failed"
    with pytest.raises(ValueError):
        case["helper"]._build(
            case["source"], case["output"], "wheel", case["work"], case["environment"]
        )
    receipt = _source_build_receipt(case)
    assert receipt["returncode"] == 7
    assert receipt["timed_out"] is False
    assert (case["work"] / "ordinary.stdout.raw").read_bytes() == b"public-partial-stdout"
    assert (case["work"] / "ordinary.stderr.raw").read_bytes() == b"public-partial-stderr"
