"""Integration tests for begin, failed retry, and close commands."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from aiflow.cli import main
from aiflow.decision_units import classification_input_digest, parse_decision_units
from aiflow.policy import load_policy_bundle
from aiflow.storage import atomic_write_json
from aiflow.task_service import (
    freeze_task,
    load_task_record,
    transition_task_record,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=True,
        encoding="utf-8",
        timeout=10,
    )
    return result.stdout.rstrip("\r\n")


def commit_all(repository: Path, message: str) -> None:
    run_git(repository, "add", ".")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        message,
    )


def create_repository(path: Path) -> Path:
    path.mkdir()
    run_git(path, "init", "-b", "main")
    ai_root = path / ".ai"
    ai_root.mkdir()
    for directory in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / directory, ai_root / directory)
    (ai_root / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    run_git(path, "add", ".ai", "tracked.txt")
    run_git(
        path,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "initial",
    )
    return path


def start(repository: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repository)
    assert main(["start", "--objective", "bounded", "--allow", "src/**"]) == 0


def classification(route: str, policy_sha: str = "b" * 64) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "classification_input_sha256": "a" * 64,
        "policy_version": "1.0.0",
        "policy_sha256": policy_sha,
        "base_commit": "1" * 40,
        "subject_commit": "1" * 40,
        "classified_at": "2026-08-20T14:00:00Z",
        "effective_route": route,
        "effective_verification_level": "V1",
        "change_reason": "unchanged",
        "classifications": [
            {
                "decision_unit_id": "DU-001",
                "route": route,
                "verification_level": "V1",
                "rule_id": "TEST-RULE",
                "explanation": "test classification",
                "matched_rules": [
                    {
                        "rule_id": "TEST-RULE",
                        "priority": 1,
                        "route": route,
                        "explanation": "test classification",
                        "predicate_explanations": [],
                    }
                ],
                "explanations": ["test classification"],
                "verification_rule_ids": ["TEST-VERIFICATION"],
                "verification_explanations": ["test verification"],
                "verification_blocking_reasons": [],
                "policy_version": "1.0.0",
                "policy_sha256": policy_sha,
                "classified_at": "2026-08-20T14:00:00Z",
            }
        ],
    }


def make_ready(
    repository: Path,
    *,
    route: str = "AUTO",
    freeze_spec: bool = True,
    valid_approval: bool = False,
) -> None:
    task_directory = repository / ".ai" / "tasks" / "TASK-0001"
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="CLASSIFIED",
        event_type="classification_recorded",
        actor="tester",
        payload={},
        satisfied_preconditions={"classification_available"},
    )
    if freeze_spec:
        freeze_task(repository, "TASK-0001", actor="tester")
    policy_sha = load_policy_bundle(repository).sha256
    task = load_task_record(repository, "TASK-0001").task
    classification_record = classification(route, policy_sha)
    classification_record["base_commit"] = task["base_commit"]
    classification_record["subject_commit"] = task["subject_commit"]
    classification_record["classification_input_sha256"] = classification_input_digest(
        task, parse_decision_units(task)
    )
    atomic_write_json(task_directory / "classification.json", classification_record)
    approvals: list[dict[str, Any]] = []
    if valid_approval:
        spec_sha = hashlib.sha256((task_directory / "spec.md").read_bytes()).hexdigest()
        approvals.append(
            {
                "schema_version": "1.0",
                "task_id": "TASK-0001",
                "decision_unit_id": "DU-001",
                "approval_type": "spec",
                "actor": "reviewer",
                "reason": "spec is complete",
                "spec_sha256": spec_sha,
                "policy_sha256": policy_sha,
                "subject_commit": task["subject_commit"],
                "approved_at": "2026-08-20T14:00:00Z",
            }
        )
    atomic_write_json(task_directory / "approvals.json", approvals)
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="READY_TO_IMPLEMENT",
        event_type="implementation_ready",
        actor="tester",
        payload={},
        satisfied_preconditions={"classification_route_selected", "spec_frozen"},
    )


def make_failed(repository: Path, payload: dict[str, object]) -> None:
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="VERIFYING",
        event_type="verification_started",
        actor="tester",
        payload={},
        satisfied_preconditions={"implementation_complete"},
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="FAILED",
        event_type="verification_failed",
        actor="tester",
        payload=payload,
        satisfied_preconditions={"verification_failed"},
    )


def make_approved(repository: Path) -> None:
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="VERIFYING",
        event_type="verification_started",
        actor="tester",
        payload={},
        satisfied_preconditions={"implementation_complete"},
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="VERIFIED",
        event_type="verification_passed",
        actor="tester",
        payload={},
        satisfied_preconditions={"verification_passed"},
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="APPROVED_FOR_MERGE",
        event_type="merge_approved_automatically",
        actor="tester",
        payload={},
        satisfied_preconditions={"final_review_not_required"},
    )


@pytest.mark.parametrize(
    ("route", "with_approval"),
    [("AUTO", False), ("REVIEW", True)],
)
def test_begin_ready_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    with_approval: bool,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route=route, valid_approval=with_approval)

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "IMPLEMENTING"
    assert record.events[-1]["event_type"] == "implementation_started"


def test_begin_rejects_missing_frozen_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, freeze_spec=False)

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "frozen" in capsys.readouterr().err.lower()


def test_begin_rejects_missing_review_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "approval" in capsys.readouterr().err.lower()


def test_begin_rejects_business_worktree_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    (repository / "tracked.txt").write_text("changed after start\n", encoding="utf-8")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "git context" in capsys.readouterr().err.lower()


def test_begin_accepts_current_task_governance_only_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW", valid_approval=True)
    commit_all(repository, "record current task governance")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0

    record = load_task_record(repository, "TASK-0001")
    assert record.task["subject_commit"] != run_git(repository, "rev-parse", "HEAD")
    assert record.task["current_state"] == "IMPLEMENTING"


@pytest.mark.parametrize("drift", ["business", "other-task-governance"])
def test_begin_rejects_non_current_task_commits_after_subject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    drift: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW", valid_approval=True)
    if drift == "business":
        (repository / "tracked.txt").write_text("committed business drift\n", encoding="utf-8")
    else:
        other = repository / ".ai" / "tasks" / "TASK-9999"
        other.mkdir(parents=True)
        (other / "note.txt").write_text("other task\n", encoding="utf-8")
    commit_all(repository, "commit non-governance drift")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "git context" in capsys.readouterr().err.lower()


def test_failed_retry_requires_reason_and_records_normal_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    make_failed(repository, {"summary": "tests failed"})

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "reason" in capsys.readouterr().err.lower()
    assert (
        main(
            [
                "begin",
                "TASK-0001",
                "--actor",
                "implementer",
                "--reason",
                "Fix the failing test",
            ]
        )
        == 0
    )

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "IMPLEMENTING"
    assert record.events[-1]["event_type"] == "implementation_retried"
    assert record.events[-1]["payload"]["reason"] == "Fix the failing test"


@pytest.mark.parametrize(
    "marker",
    [
        "scope_expanded",
        "new_dependencies",
        "new_permissions",
        "unverifiable",
        "high_risk_side_effects",
    ],
)
def test_risky_failure_requires_escalation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    marker: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    make_failed(repository, {marker: True})

    assert main(["begin", "TASK-0001", "--actor", "implementer", "--reason", "retry"]) == 1
    assert "escalat" in capsys.readouterr().err.lower()


def test_close_rejects_early_state_and_unknown_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)

    close = [
        "close",
        "TASK-0001",
        "--result",
        "merged",
        "--merge-commit",
        "0" * 40,
        "--actor",
        "closer",
    ]
    assert main(close) == 1
    capsys.readouterr()

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    make_approved(repository)
    assert main(close) == 1
    assert "commit" in capsys.readouterr().err.lower()


def test_close_records_existing_merge_without_running_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    make_approved(repository)
    head = run_git(repository, "rev-parse", "HEAD")
    branch_before = run_git(repository, "branch", "--show-current")

    assert (
        main(
            [
                "close",
                "TASK-0001",
                "--result",
                "merged",
                "--merge-commit",
                head,
                "--actor",
                "closer",
            ]
        )
        == 0
    )

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "MERGED"
    assert record.events[-1]["payload"] == {"merge_commit": head, "result": "merged"}
    assert run_git(repository, "rev-parse", "HEAD") == head
    assert run_git(repository, "branch", "--show-current") == branch_before


def test_classify_records_durable_evidence_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    first = load_task_record(repository, "TASK-0001")
    assert first.task["current_state"] == "BLOCKED"
    assert (repository / ".ai" / "tasks" / "TASK-0001" / "classification.json").is_file()
    event_count = len(first.events)

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert len(load_task_record(repository, "TASK-0001").events) == event_count


@pytest.mark.parametrize("command", ["begin", "close", "classify"])
def test_command_help_is_available(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main([command, "--help"])

    assert caught.value.code == 0
    assert "--actor" in capsys.readouterr().out
