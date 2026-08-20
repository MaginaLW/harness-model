"""Integration coverage for independent spec, code, and action approvals."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_answer_command import specification
from test_begin_close_commands import classification as base_classification
from test_begin_close_commands import create_repository, run_git, start

from aiflow import approval as approval_service
from aiflow.classification_service import _stable_input
from aiflow.cli import main
from aiflow.decision_units import parse_decision_units
from aiflow.errors import StorageError
from aiflow.policy import load_policy_bundle
from aiflow.storage import atomic_write_json, read_task_json, read_task_yaml, resolve_task_path
from aiflow.task_service import freeze_task, load_task_record, transition_task_record


def review_package() -> str:
    return """# Review Package

## 审核目标

决定是否接受当前实现。

## 背景

任务实现了一个确定性本地流程。

## 代码地图

- `src/aiflow/module.py`：入口。

## 语义变更

新增版本绑定批准。

## 风险

版本变化时旧批准必须失效。

## 证据

- 已验证：定向测试通过。
- 未验证：真实外部动作未执行。

## 审核问题

- 当前实现是否满足冻结规格？

## 推荐结论

APPROVE
"""


def _classification(repository: Path) -> dict[str, object]:
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    policy = load_policy_bundle(repository)
    document = base_classification("REVIEW")
    document.update(
        {
            "classification_input_sha256": _stable_input(task, parse_decision_units(task)),
            "policy_version": policy.policy_version,
            "policy_sha256": policy.sha256,
            "base_commit": task["base_commit"],
            "subject_commit": task["subject_commit"],
            "effective_route": "REVIEW",
            "effective_verification_level": "V1",
        }
    )
    entry = document["classifications"][0]
    entry["policy_version"] = policy.policy_version
    entry["policy_sha256"] = policy.sha256
    return document


def _to_classified(repository: Path) -> None:
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"),
        _classification(repository),
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="CLASSIFIED",
        event_type="classification_recorded",
        actor="classifier",
        payload={},
        satisfied_preconditions={"classification_available"},
    )


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    state: str,
) -> Path:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    (repository / ".ai" / "task-sequence").unlink(missing_ok=True)
    resolve_task_path(repository, "TASK-0001", "spec.md").write_text(
        specification(), encoding="utf-8"
    )
    freeze_task(repository, "TASK-0001", actor="specifier")
    _to_classified(repository)
    if state == "WAITING_FOR_SPEC_REVIEW":
        transition_task_record(
            repository,
            "TASK-0001",
            target_state=state,
            event_type="spec_review_required",
            actor="classifier",
            payload={},
            satisfied_preconditions={"classification_route_selected"},
        )
    elif state == "WAITING_FOR_FINAL_REVIEW":
        transition_task_record(
            repository,
            "TASK-0001",
            target_state="READY_TO_IMPLEMENT",
            event_type="implementation_ready",
            actor="classifier",
            payload={},
            satisfied_preconditions={"classification_route_selected"},
        )
        transition_task_record(
            repository,
            "TASK-0001",
            target_state="IMPLEMENTING",
            event_type="implementation_started",
            actor="implementer",
            payload={},
            satisfied_preconditions={"readiness_satisfied"},
        )
        transition_task_record(
            repository,
            "TASK-0001",
            target_state="VERIFYING",
            event_type="verification_started",
            actor="verifier",
            payload={},
            satisfied_preconditions={"implementation_complete"},
        )
        transition_task_record(
            repository,
            "TASK-0001",
            target_state="VERIFIED",
            event_type="verification_passed",
            actor="verifier",
            payload={},
            satisfied_preconditions={"verification_passed"},
        )
        transition_task_record(
            repository,
            "TASK-0001",
            target_state=state,
            event_type="final_review_required",
            actor="verifier",
            payload={},
            satisfied_preconditions={"final_review_required"},
        )
    elif state != "CLASSIFIED":
        raise AssertionError(f"unsupported test state: {state}")
    return repository


def _evidence(repository: Path, *, conclusion: str = "passed") -> dict[str, object]:
    task = load_task_record(repository, "TASK-0001").task
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "decision_unit_ids": ["DU-001"],
        "repository_id": task["repository_id"],
        "branch": task["branch"],
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "spec_sha256": task["frozen_spec_sha256"],
        "policy_sha256": classification["policy_sha256"],
        "classification_input_sha256": classification["classification_input_sha256"],
        "verification_level": "V1",
        "mode": "local",
        "checks": [
            {
                "check_id": "pytest",
                "category": "pytest",
                "status": conclusion,
                "reason_code": None,
                "required": True,
                "exit_code": 0,
                "timed_out": False,
                "duration_ms": 1,
                "stdout_log_ref": "logs/run/pytest.stdout.log",
                "stderr_log_ref": "logs/run/pytest.stderr.log",
                "command_summary": "python -m pytest",
                "tool_version": "test",
            }
        ],
        "unverified_scenarios": [],
        "conclusion": conclusion,
        "generated_at": "2026-08-21T01:00:00Z",
        "reproduce_command": ["python", "-m", "pytest"],
    }


def test_spec_approval_persists_all_review_units_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    arguments = [
        "approve",
        "TASK-0001",
        "--type",
        "spec",
        "--actor",
        "reviewer",
        "--reason",
        "direction approved",
    ]

    assert main(arguments) == 0
    first = load_task_record(repository, "TASK-0001")
    approvals = read_task_json(repository, "TASK-0001", "approvals.json")
    assert first.task["current_state"] == "READY_TO_IMPLEMENT"
    assert isinstance(approvals, list) and len(approvals) == 1
    assert approvals[0]["approval_type"] == "spec"
    assert first.events[-1]["event_type"] == "spec_approved"

    assert main(arguments) == 0
    second = load_task_record(repository, "TASK-0001")
    assert second.events == first.events
    assert read_task_json(repository, "TASK-0001", "approvals.json") == approvals


def test_code_approval_requires_package_and_current_passing_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_FINAL_REVIEW")
    arguments = [
        "approve",
        "TASK-0001",
        "--type",
        "code",
        "--actor",
        "reviewer",
        "--reason",
        "implementation approved",
    ]
    assert main(arguments) == 1

    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    assert main(arguments) == 1
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "evidence.json"), _evidence(repository)
    )

    assert main(arguments) == 0
    record = load_task_record(repository, "TASK-0001")
    approvals = read_task_json(repository, "TASK-0001", "approvals.json")
    assert record.task["current_state"] == "APPROVED_FOR_MERGE"
    assert record.events[-1]["event_type"] == "code_approved"
    assert isinstance(approvals, list) and approvals[-1]["approval_type"] == "code"
    assert "evidence_sha256" in approvals[-1]


def test_code_approval_rejects_business_worktree_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_FINAL_REVIEW")
    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "evidence.json"), _evidence(repository)
    )
    (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")

    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "code",
                "--actor",
                "reviewer",
                "--reason",
                "implementation approved",
            ]
        )
        == 1
    )
    assert load_task_record(repository, "TASK-0001").task["current_state"] == (
        "WAITING_FOR_FINAL_REVIEW"
    )


def test_action_approval_records_exact_single_use_action_without_state_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="CLASSIFIED")
    task = load_task_record(repository, "TASK-0001").task
    action_path = tmp_path / "action.json"
    action = {
        "decision_unit_id": "DU-001",
        "action_type": "notify",
        "target": "issue-123",
        "parameter_summary": "one bounded notification",
        "subject_commit": task["subject_commit"],
        "conditions": ["spec remains frozen"],
        "expires_at": "2099-01-01T00:00:00Z",
        "single_use": True,
    }
    action_path.write_text(json.dumps(action), encoding="utf-8")
    arguments = [
        "approve",
        "TASK-0001",
        "--type",
        "action",
        "--actor",
        "reviewer",
        "--reason",
        "one action approved",
        "--action-file",
        str(action_path),
    ]

    assert main(arguments) == 0
    first = load_task_record(repository, "TASK-0001")
    approvals = read_task_json(repository, "TASK-0001", "approvals.json")
    assert first.task["current_state"] == "CLASSIFIED"
    assert first.events[-1]["event_type"] == "approval_recorded"
    assert isinstance(approvals, list) and approvals[-1]["approval_type"] == "action"
    assert approvals[-1]["single_use"] is True and "action_sha256" in approvals[-1]

    assert main(arguments) == 0
    assert load_task_record(repository, "TASK-0001").events == first.events


def test_action_approval_rejects_expired_or_non_single_use_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="CLASSIFIED")
    task = load_task_record(repository, "TASK-0001").task
    action_path = tmp_path / "action.json"
    action_path.write_text(
        json.dumps(
            {
                "decision_unit_id": "DU-001",
                "action_type": "notify",
                "target": "issue-123",
                "parameter_summary": "one notification",
                "subject_commit": task["subject_commit"],
                "conditions": [],
                "expires_at": "2020-01-01T00:00:00Z",
                "single_use": False,
            }
        ),
        encoding="utf-8",
    )
    before = load_task_record(repository, "TASK-0001")
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "action",
                "--actor",
                "reviewer",
                "--reason",
                "action approved",
                "--action-file",
                str(action_path),
            ]
        )
        == 1
    )
    after = load_task_record(repository, "TASK-0001")
    assert after.task == before.task and after.events == before.events


def test_spec_approval_rejects_tampered_spec_and_wrong_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    spec_path = resolve_task_path(repository, "TASK-0001", "spec.md")
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    before = load_task_record(repository, "TASK-0001")
    arguments = [
        "approve",
        "TASK-0001",
        "--type",
        "spec",
        "--actor",
        "reviewer",
        "--reason",
        "direction approved",
    ]
    assert main(arguments) == 1
    assert load_task_record(repository, "TASK-0001").events == before.events

    other_root = tmp_path / "other"
    other_root.mkdir()
    other = _prepare(other_root, monkeypatch, state="CLASSIFIED")
    monkeypatch.chdir(other)
    assert main(arguments) == 1
    assert load_task_record(other, "TASK-0001").task["current_state"] == "CLASSIFIED"


def test_spec_approval_recovers_pending_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    original = approval_service._persist_event_and_task

    def fail_once(*args: object, **kwargs: object) -> None:
        raise StorageError("injected", code="STORAGE_WRITE_FAILED")

    monkeypatch.setattr(approval_service, "_persist_event_and_task", fail_once)
    arguments = [
        "approve",
        "TASK-0001",
        "--type",
        "spec",
        "--actor",
        "reviewer",
        "--reason",
        "direction approved",
    ]
    assert main(arguments) == 1
    assert load_task_record(repository, "TASK-0001").task["current_state"] == (
        "WAITING_FOR_SPEC_REVIEW"
    )
    assert resolve_task_path(repository, "TASK-0001", "approval_pending.json").is_file()

    monkeypatch.setattr(approval_service, "_persist_event_and_task", original)
    assert main(arguments) == 0
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "READY_TO_IMPLEMENT"
    assert [event["event_type"] for event in record.events].count("spec_approved") == 1
    assert not resolve_task_path(repository, "TASK-0001", "approval_pending.json").exists()


def test_code_approval_rejects_committed_business_change_after_subject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_FINAL_REVIEW")
    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "evidence.json"), _evidence(repository)
    )
    (repository / "tracked.txt").write_text("committed change\n", encoding="utf-8")
    run_git(repository, "add", "tracked.txt")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "business change",
    )

    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "code",
                "--actor",
                "reviewer",
                "--reason",
                "implementation approved",
            ]
        )
        == 1
    )
    assert load_task_record(repository, "TASK-0001").task["current_state"] == (
        "WAITING_FOR_FINAL_REVIEW"
    )
