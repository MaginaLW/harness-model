"""Counterexamples for the committed, privacy-limited ledger snapshot."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import pytest

TOOL_PATH = Path(__file__).resolve().parents[2] / "tools/analysis/approval_overhead.py"
PREFIX = ".ai/tasks/TASK-0001/"


@pytest.fixture
def snapshot_module() -> Any:
    spec = importlib.util.spec_from_file_location("telemetry_snapshot", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _event(sequence: int, kind: str, state: str, **payload: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "sequence": sequence,
        "event_type": kind,
        "from_state": "VERIFYING",
        "to_state": state,
        "actor": "私人会话中的身份，不应输出",
        "occurred_at": "2026-10-11T00:00:00Z",
        "payload": payload,
    }


def _documents() -> dict[str, Any]:
    return {
        PREFIX + "task.yaml": {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "current_state": "MERGED",
            "base_commit": "a" * 40,
            "subject_commit": "b" * 40,
            "goal": "private-chat-marker",
            "repository_path_at_creation": "C:/Users/private-person/secret-repo",
        },
        PREFIX + "classification.json": {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "effective_route": "REVIEW",
            "effective_verification_level": "V1",
        },
        PREFIX + "events.jsonl": [
            _event(1, "classification_recorded", "BLOCKED", effective_route="BLOCK"),
            _event(2, "verification_started", "VERIFYING"),
            _event(3, "verification_failed", "FAILED", conclusion="failed"),
            _event(4, "verification_started", "VERIFYING"),
            _event(5, "verification_passed", "VERIFIED", conclusion="passed"),
        ],
        PREFIX + "reviews/REV-0001-r0001.json": {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "review_id": "REV-0001",
            "revision": 1,
            "review_stage": "implementation",
            "outcome": "REQUEST_CHANGES",
            "context_sha256": "d" * 64,
            "recorded_at": "2026-10-11T00:00:00Z",
            "reviewer": "claimed-provider-model",
            "findings": [{"title": "credential-secret-marker"}],
        },
        PREFIX + "evidence.json": {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "subject_commit": "b" * 40,
            "conclusion": "passed",
            "checks": [
                {
                    "check_id": "unit_tests",
                    "category": "unit_tests",
                    "status": "passed",
                    "duration_ms": 123,
                    "required": True,
                    "exit_code": 0,
                    "timed_out": False,
                    "command_summary": "credential-secret-marker",
                    "stdout_log_ref": "C:/Users/private-person/private-logs",
                }
            ],
        },
    }


def _git_inputs(
    module: Any, monkeypatch: pytest.MonkeyPatch, documents: dict[str, Any]
) -> list[tuple[str, ...]]:
    """Supply the external Git wire format; reject requests for non-allowlisted blobs."""
    blobs = {}
    for path, value in documents.items():
        if isinstance(value, bytes):
            contents = value
        elif path.endswith(".jsonl"):
            contents = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in value).encode()
        else:
            contents = json.dumps(value, ensure_ascii=False).encode()
        oid = hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\0" + contents).hexdigest()
        blobs[path] = (oid, contents)
    calls: list[tuple[str, ...]] = []

    def git(_repository: Path, *arguments: str, data: bytes | None = None) -> bytes:
        calls.append(arguments)
        if arguments == ("rev-parse", "--verify", "HEAD"):
            return b"c" * 40 + b"\n"
        if arguments[0] == "ls-tree":
            return b"".join(
                f"100644 blob {oid}\t{path}\0".encode() for path, (oid, _) in blobs.items()
            )
        assert arguments == ("cat-file", "--batch")
        assert data is not None
        allowed = {
            oid: contents
            for path, (oid, contents) in blobs.items()
            if "/logs/" not in path and "/private/" not in path
        }
        return b"".join(
            f"{oid} blob {len(allowed[oid])}\n".encode() + allowed[oid] + b"\n"
            for oid in data.decode().splitlines()
        )

    monkeypatch.setattr(module, "_snapshot_git", git)
    return calls


def test_snapshot_preserves_failure_block_and_attempt_dependence(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    later = dict(documents[PREFIX + "reviews/REV-0001-r0001.json"])
    later.update(revision=2, outcome="APPROVE")
    documents[PREFIX + "reviews/REV-0001-r0002.json"] = later
    _git_inputs(snapshot_module, monkeypatch, documents)

    report = snapshot_module.build_snapshot(tmp_path)

    task = report["tasks"][0]
    assert task["task"]["current_state"] == "MERGED"
    assert task["events"][0]["effective_route"] == "BLOCK"
    assert [attempt["original_result"] for attempt in task["verification_attempts"]] == [
        "failed",
        "passed",
    ]
    assert [review["outcome"] for review in task["reviews"]] == ["REQUEST_CHANGES", "APPROVE"]
    assert task["historical_first_result"] == "unknown"
    assert task["evidence_attempt_linkage"] == "unknown"
    assert report["coverage"]["task_records"] == 1
    assert task["dependence_group"] == "TASK-0001"
    assert report["unknown"]["actual_model"] == "unknown"
    assert report["unknown"]["cost"] == "unknown"
    assert "success_probability" not in json.dumps(report)


def test_snapshot_excludes_private_free_text_and_has_no_writes(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    documents[PREFIX + "logs/run-private/evidence.json"] = b"credential-secret-marker"
    documents[PREFIX + "private/task.yaml"] = b"private-chat-marker"
    _git_inputs(snapshot_module, monkeypatch, documents)
    dirty = tmp_path / ".ai/tasks/TASK-0001/task.yaml"
    dirty.parent.mkdir(parents=True)
    dirty.write_text("uncommitted-secret-marker", encoding="utf-8")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    report = snapshot_module.build_snapshot(tmp_path)

    serialized = json.dumps(report)
    assert not any(
        marker in serialized
        for marker in (
            "private-chat-marker",
            "credential-secret-marker",
            "uncommitted-secret-marker",
            "private-person",
            "claimed-provider-model",
            "私人会话",
            "/logs/",
            "/private/",
        )
    )
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_missing_optional_data_is_unknown_and_unclosed_attempt_stays_open(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    for filename in ("classification.json", "evidence.json", "reviews/REV-0001-r0001.json"):
        del documents[PREFIX + filename]
    documents[PREFIX + "events.jsonl"] = [_event(1, "verification_started", "VERIFYING")]
    _git_inputs(snapshot_module, monkeypatch, documents)

    report = snapshot_module.build_snapshot(tmp_path)

    task = report["tasks"][0]
    assert task["classification"] == task["evidence"] == "unknown"
    assert task["verification_attempts"][0]["original_result"] == "unknown"
    assert report["coverage"]["missing_tasks_by_field"] == {
        "classification.json": 1,
        "evidence.json": 1,
        "reviews": 1,
        "verification_attempts": 0,
    }


def test_native_restarted_and_checked_attempt_preserves_provisional_result(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    documents[PREFIX + "events.jsonl"] = [
        _event(1, "verification_restarted", "VERIFYING"),
        _event(2, "verification_checked", "IMPLEMENTING", conclusion="provisional"),
    ]
    _git_inputs(snapshot_module, monkeypatch, documents)
    report = snapshot_module.build_snapshot(tmp_path)
    assert report["tasks"][0]["verification_attempts"] == [
        {
            "stage": "verification",
            "start_sequence": 1,
            "result_sequence": 2,
            "original_result": "provisional",
            "to_state": "IMPLEMENTING",
        }
    ]


@pytest.mark.parametrize(
    "filename,value",
    [
        ("task.yaml", b"current_state: ["),
        ("events.jsonl", b"{not-json-private-secret}\n"),
        ("evidence.json", {"task_id": "TASK-0001", "checks": [], "conclusion": {}}),
        ("reviews/REV-0001-r0001.json", {"task_id": "TASK-0001", "revision": 0}),
    ],
)
def test_malformed_committed_data_fails_without_echoing_content(
    snapshot_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    filename: str,
    value: Any,
) -> None:
    documents = _documents()
    documents[PREFIX + filename] = value
    _git_inputs(snapshot_module, monkeypatch, documents)

    assert snapshot_module.main([str(tmp_path), "--snapshot", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "private-secret" not in captured.err


@pytest.mark.parametrize("filename", ["task.yaml", "events.jsonl"])
def test_missing_required_committed_document_is_rejected(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, filename: str
) -> None:
    documents = _documents()
    del documents[PREFIX + filename]
    _git_inputs(snapshot_module, monkeypatch, documents)

    with pytest.raises(snapshot_module.LedgerDataError, match="committed file is required"):
        snapshot_module.build_snapshot(tmp_path)


def test_git_errors_do_not_disclose_repository_or_stderr(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("C:/Users/private-person/credential-secret-marker")

    monkeypatch.setattr(snapshot_module.subprocess, "run", fail)
    with pytest.raises(snapshot_module.LedgerDataError, match="committed Git inputs") as error:
        snapshot_module._snapshot_git(tmp_path, "rev-parse", "HEAD")
    assert "private-person" not in str(error.value)


@pytest.mark.parametrize(
    "filename,contents",
    [
        ("task.yaml", b"task_id: TASK-0001\ncurrent_state: FAILED\ncurrent_state: MERGED\n"),
        (
            "evidence.json",
            b'{"task_id":"TASK-0001","checks":[],"conclusion":"failed","conclusion":"passed"}',
        ),
    ],
)
def test_duplicate_keys_cannot_overwrite_failure(
    snapshot_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    filename: str,
    contents: bytes,
) -> None:
    documents = _documents()
    documents[PREFIX + filename] = contents
    _git_inputs(snapshot_module, monkeypatch, documents)
    with pytest.raises(snapshot_module.LedgerDataError):
        snapshot_module.build_snapshot(tmp_path)


@pytest.mark.parametrize("issue", ["contradictory_result", "negative_duration"])
def test_contradictory_failure_and_negative_duration_are_rejected(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, issue: str
) -> None:
    documents = _documents()
    if issue == "contradictory_result":
        documents[PREFIX + "events.jsonl"][2]["payload"]["conclusion"] = "passed"
    else:
        documents[PREFIX + "evidence.json"]["checks"][0]["duration_ms"] = -5
    _git_inputs(snapshot_module, monkeypatch, documents)
    with pytest.raises(snapshot_module.LedgerDataError):
        snapshot_module.build_snapshot(tmp_path)


def test_git_environment_cannot_redirect_repository_or_replace_raw_objects(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG_COUNT", "GIT_CONFIG_GLOBAL"):
        monkeypatch.setenv(key, "untrusted-redirection")
    observed: dict[str, Any] = {}

    def run(command: list[str], **options: Any) -> Any:
        observed.update(command=command, **options)
        return snapshot_module.subprocess.CompletedProcess(command, 0, stdout=b"metadata\n")

    monkeypatch.setattr(snapshot_module.subprocess, "run", run)
    assert snapshot_module._snapshot_git(tmp_path, "rev-parse", "HEAD") == b"metadata\n"
    assert "--no-replace-objects" in observed["command"]
    environment = observed["env"]
    assert not any(key in environment for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG_COUNT"))
    assert environment["GIT_CONFIG_GLOBAL"] == environment["GIT_CONFIG_SYSTEM"] == os.devnull
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert environment["GIT_ALLOW_PROTOCOL"] == ""


@pytest.mark.parametrize("issue", ["empty", "sequence", "missing_type", "bad_review_id"])
def test_inconsistent_record_identity_and_event_history_are_rejected(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, issue: str
) -> None:
    documents = _documents()
    if issue == "empty":
        documents[PREFIX + "events.jsonl"] = b""
    elif issue == "sequence":
        documents[PREFIX + "events.jsonl"][1]["sequence"] = 1
    elif issue == "missing_type":
        documents[PREFIX + "events.jsonl"][0]["event_type"] = None
    else:
        documents[PREFIX + "reviews/REV-0001-r0001.json"]["review_id"] = "REV-0002"
    _git_inputs(snapshot_module, monkeypatch, documents)

    with pytest.raises(snapshot_module.LedgerDataError):
        snapshot_module.build_snapshot(tmp_path)


@pytest.mark.parametrize("issue", ["symlink", "header", "length", "trailing"])
def test_git_protocol_failures_and_symlink_inputs_are_rejected(
    snapshot_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, issue: str
) -> None:
    _git_inputs(snapshot_module, monkeypatch, _documents())
    valid_git = snapshot_module._snapshot_git

    def malformed(repository: Path, *arguments: str, data: bytes | None = None) -> bytes:
        response = valid_git(repository, *arguments, data=data)
        if arguments[0] == "ls-tree" and issue == "symlink":
            return response.replace(b"100644", b"120000", 1)
        if arguments[0] == "cat-file":
            if issue == "header":
                return b"private-secret malformed header\n"
            if issue == "length":
                return response[: response.index(b"\n") + 1]
            if issue == "trailing":
                return response + b"private-secret"
        return response

    monkeypatch.setattr(snapshot_module, "_snapshot_git", malformed)
    with pytest.raises(snapshot_module.LedgerDataError) as error:
        snapshot_module.build_snapshot(tmp_path)
    assert "private-secret" not in str(error.value)


@pytest.mark.parametrize("format_name", ["text", "json"])
def test_opt_in_snapshot_formats_are_readable(
    snapshot_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    format_name: str,
) -> None:
    _git_inputs(snapshot_module, monkeypatch, _documents())
    assert snapshot_module.main([str(tmp_path), "--snapshot", "--format", format_name]) == 0
    output = capsys.readouterr().out
    if format_name == "json":
        assert json.loads(output)["measurement"] == "tracked_ledger_snapshot"
    else:
        assert "not reverified" in output
