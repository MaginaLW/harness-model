"""Structured REVIEW context and immutable record validation tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from aiflow import review_service
from aiflow.errors import ContractError
from aiflow.review_service import (
    _committed_diff_summary,
    _stage,
    review_is_approvable,
    validate_review_context,
    validate_review_record,
)

HASH = "a" * 64
COMMIT = "b" * 40


def context(stage: str = "design") -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "review_stage": stage,
        "task_id": "TASK-0001",
        "decision_unit_ids": ["DU-001"],
        "repository_id": "b85e5a53-4935-4436-bdbc-c26a241bfae8",
        "branch": "main",
        "base_commit": COMMIT,
        "spec_sha256": HASH,
        "policy_sha256": HASH,
        "classification_input_sha256": HASH,
        "content": {"goal": "review one bounded change"},
    }
    if stage == "implementation":
        value["subject_commit"] = COMMIT
        value["evidence_sha256"] = HASH
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    value["context_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return value


def record(stage: str = "design", *, outcome: str = "APPROVE") -> dict[str, Any]:
    value = context(stage)
    return {
        "schema_version": "1.0",
        "review_id": "REV-0001",
        "revision": 1,
        "task_id": "TASK-0001",
        "review_stage": stage,
        "reviewer": "reviewer",
        "recorded_at": "2026-08-22T12:00:00Z",
        "context_sha256": value["context_sha256"],
        "outcome": outcome,
        "summary": "bounded review conclusion",
        "findings": [],
    }


def test_context_hash_is_canonical_and_detects_tampering() -> None:
    first = context()
    second = context()
    validate_review_context(first)
    assert first["context_sha256"] == second["context_sha256"]
    tampered = deepcopy(first)
    tampered["content"]["goal"] = "different semantic change"
    with pytest.raises(ContractError) as caught:
        validate_review_context(tampered)
    assert caught.value.code == "REVIEW_CONTEXT_HASH_INVALID"


def test_committed_diff_summary_contains_only_deterministic_numstat(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    def git(*arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    git("init", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")
    (repository / "alpha.txt").write_text("one\ntwo\n", encoding="utf-8")
    git("add", "alpha.txt")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")
    (repository / "alpha.txt").write_text("one\nthree\n", encoding="utf-8")
    (repository / "beta.txt").write_text("new\n", encoding="utf-8")
    git("add", "alpha.txt", "beta.txt")
    git("commit", "-m", "subject")
    subject = git("rev-parse", "HEAD")

    summary = _committed_diff_summary(repository, base, subject)

    assert summary == {
        "changed_paths": ["alpha.txt", "beta.txt"],
        "files": [
            {"path": "alpha.txt", "additions": 1, "deletions": 1, "binary": False},
            {"path": "beta.txt", "additions": 1, "deletions": 0, "binary": False},
        ],
        "totals": {"files": 2, "additions": 2, "deletions": 1},
    }


def test_committed_diff_summary_has_stable_git_and_parse_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(["git"], 10)

    monkeypatch.setattr(review_service.subprocess, "run", timeout)
    with pytest.raises(ContractError) as caught:
        _committed_diff_summary(tmp_path, COMMIT, COMMIT)
    assert caught.value.code == "REVIEW_DIFF_TIMEOUT"

    def unavailable(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise OSError("git unavailable")

    monkeypatch.setattr(review_service.subprocess, "run", unavailable)
    with pytest.raises(ContractError) as caught:
        _committed_diff_summary(tmp_path, COMMIT, COMMIT)
    assert caught.value.code == "REVIEW_DIFF_FAILED"

    for result, code in (
        (subprocess.CompletedProcess(["git"], 1, b"", b"failed"), "REVIEW_DIFF_FAILED"),
        (subprocess.CompletedProcess(["git"], 0, b"\xff", b""), "REVIEW_DIFF_INVALID"),
        (subprocess.CompletedProcess(["git"], 0, b"malformed\n", b""), "REVIEW_DIFF_INVALID"),
        (subprocess.CompletedProcess(["git"], 0, b"x\t1\tbad.txt\n", b""), "REVIEW_DIFF_INVALID"),
    ):
        monkeypatch.setattr(
            review_service.subprocess, "run", lambda *args, _result=result, **kwargs: _result
        )
        with pytest.raises(ContractError) as caught:
            _committed_diff_summary(tmp_path, COMMIT, COMMIT)
        assert caught.value.code == code

    binary = subprocess.CompletedProcess(["git"], 0, b"-\t-\tasset.bin\n", b"")
    monkeypatch.setattr(review_service.subprocess, "run", lambda *args, **kwargs: binary)
    assert _committed_diff_summary(tmp_path, COMMIT, COMMIT)["files"] == [
        {"path": "asset.bin", "additions": None, "deletions": None, "binary": True}
    ]


def test_invalid_review_stage_has_a_stable_error() -> None:
    with pytest.raises(ContractError) as caught:
        _stage("final")
    assert caught.value.code == "REVIEW_STAGE_INVALID"


def test_stages_are_mutually_exclusive() -> None:
    design = context()
    design["subject_commit"] = COMMIT
    design["context_sha256"] = "c" * 64
    assert any("contract constraint failed" in error for error in _errors(design))

    implementation = context("implementation")
    implementation.pop("evidence_sha256")
    implementation["context_sha256"] = "c" * 64
    assert any("required property is missing" in error for error in _errors(implementation))


def _errors(value: dict[str, Any]) -> list[str]:
    from aiflow.contracts import validate_contract

    return validate_contract("review-context", value)


def test_record_rejects_duplicate_findings_and_open_high_findings() -> None:
    current = context()
    duplicate = record()
    duplicate["findings"] = [
        _finding("RF-001", "low"),
        _finding("RF-001", "medium"),
    ]
    with pytest.raises(ContractError) as caught:
        validate_review_record(duplicate, current)
    assert caught.value.code == "REVIEW_FINDING_DUPLICATE"

    blocked = record()
    blocked["findings"] = [_finding("RF-001", "high")]
    with pytest.raises(ContractError) as caught:
        validate_review_record(blocked, current)
    assert caught.value.code == "REVIEW_FINDING_UNRESOLVED"
    assert review_is_approvable(blocked) is False


def test_resolved_high_finding_and_context_binding_are_valid() -> None:
    current = context("implementation")
    reviewed = record("implementation", outcome="APPROVE_WITH_CONDITIONS")
    reviewed["findings"] = [_finding("RF-001", "critical", resolved=True)]
    validate_review_record(reviewed, current)
    assert review_is_approvable(reviewed) is True

    reviewed["context_sha256"] = "c" * 64
    with pytest.raises(ContractError) as caught:
        validate_review_record(reviewed, current)
    assert caught.value.code == "REVIEW_CONTEXT_MISMATCH"

    wrong_task = record("implementation")
    wrong_task["task_id"] = "TASK-0002"
    with pytest.raises(ContractError) as caught:
        validate_review_record(wrong_task, current)
    assert caught.value.code == "REVIEW_CONTEXT_MISMATCH"


def test_non_list_findings_are_ignored_by_the_semantic_helper() -> None:
    review_service._validate_findings({"findings": None})


def test_blank_review_actor_is_rejected_before_storage(tmp_path: Path) -> None:
    with pytest.raises(ContractError) as caught:
        review_service.record_review(tmp_path, "TASK-0001", input_path={}, actor=" ")
    assert caught.value.code == "REVIEW_ACTOR_INVALID"


def test_non_approving_outcomes_cannot_be_approvable() -> None:
    reviewed = record(outcome="REQUEST_CHANGES")
    validate_review_record(reviewed, context())
    assert review_is_approvable(reviewed) is False


def _finding(identifier: str, severity: str, *, resolved: bool = False) -> dict[str, Any]:
    value: dict[str, Any] = {
        "finding_id": identifier,
        "severity": severity,
        "title": "bounded finding",
        "location": {"path": "src/aiflow/review.py", "line": 1},
        "evidence_refs": ["review-context"],
        "status": "resolved" if resolved else "open",
    }
    if resolved:
        value["resolution"] = {
            "reason": "verified fixed",
            "actor": "resolver",
            "resolved_at": "2026-08-22T12:01:00Z",
        }
    return value
