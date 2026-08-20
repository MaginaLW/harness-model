"""Compact end-to-end replay coverage for the four Chapter 4 governance paths."""

from __future__ import annotations

import json
from pathlib import Path

from test_answer_command import _prepare_repository
from test_approve_command import _evidence, review_package
from test_approve_command import _prepare as prepare_review
from test_begin_close_commands import create_repository, make_ready, start

from aiflow.cli import main
from aiflow.storage import (
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record, specification_is_current


def _auto_unit(task_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "decision_unit_id": "DU-001",
        "goal": "bounded documentation edit",
        "inputs": [],
        "planned_actions": ["edit"],
        "impact_scope": ["src/module.py"],
        "reversibility": "reversible",
        "verification_methods": ["pytest"],
        "external_side_effects": [],
        "permission_requirements": [],
        "scope": {"clear": True},
        "impact": {"level": "low"},
        "protections": {"verified_backup": True, "dry_run": True},
        "verification": {"automatic": True, "tools_missing": False},
        "change_characteristics": {
            "mechanical": True,
            "behavior_changed": False,
            "code_modified": False,
            "interaction_scope": "local",
            "regression_risk": False,
            "error_detectability": "high",
        },
    }


def test_auto_path_replays_classification_freeze_begin_then_scope_escalation(
    tmp_path: Path, monkeypatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    (repository / "src").mkdir()
    (repository / "src" / "module.py").write_text("changed\n", encoding="utf-8")
    start(repository, monkeypatch)
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [_auto_unit("TASK-0001")]
    atomic_write_yaml(task_path, task)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 0
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "IMPLEMENTING"

    (repository / "outside.txt").write_text("scope expanded\n", encoding="utf-8")
    assert (
        main(
            [
                "escalate",
                "TASK-0001",
                "--to",
                "REVIEW",
                "--reason-code",
                "scope_expanded",
                "--impact",
                "outside path detected",
                "--next-step",
                "reclassify",
                "--actor",
                "implementer",
            ]
        )
        == 0
    )
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "ESCALATED"
    assert record.events[-1]["payload"]["new_route"] == "REVIEW"


def test_ask_path_rejects_missing_answer_then_freezes_selected_decision(
    tmp_path: Path, monkeypatch
) -> None:
    repository, options_path = _prepare_repository(tmp_path, monkeypatch, mixed=False)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1

    assert (
        main(
            [
                "answer",
                "TASK-0001",
                "--options-file",
                str(options_path),
                "--select",
                "OPT-02",
                "--actor",
                "operator",
                "--reason",
                "bounded choice",
            ]
        )
        == 0
    )
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "READY_TO_IMPLEMENT"
    assert record.events[-1]["event_type"] == "ask_answered"
    assert specification_is_current(repository, "TASK-0001") is True
    assert "OPT-02" in resolve_task_path(repository, "TASK-0001", "decisions.md").read_text(
        encoding="utf-8"
    )


def test_mixed_ask_review_requires_answer_then_spec_approval_before_begin(
    tmp_path: Path, monkeypatch
) -> None:
    repository, options_path = _prepare_repository(tmp_path, monkeypatch, mixed=True)
    assert (
        main(
            [
                "answer",
                "TASK-0001",
                "--options-file",
                str(options_path),
                "--select",
                "OPT-01",
                "--actor",
                "operator",
                "--reason",
                "selected option",
            ]
        )
        == 0
    )
    assert (
        load_task_record(repository, "TASK-0001").task["current_state"] == "WAITING_FOR_SPEC_REVIEW"
    )
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "spec",
                "--actor",
                "reviewer",
                "--reason",
                "direction approved",
            ]
        )
        == 0
    )
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "IMPLEMENTING"


def test_review_code_and_action_approvals_remain_independent(tmp_path: Path, monkeypatch) -> None:
    repository = prepare_review(tmp_path, monkeypatch, state="WAITING_FOR_FINAL_REVIEW")
    action_path = tmp_path / "action.json"
    task = load_task_record(repository, "TASK-0001").task
    action_path.write_text(
        json.dumps(
            {
                "action_type": "notify",
                "decision_unit_id": "DU-001",
                "target": "issue-123",
                "parameter_summary": "one notification",
                "subject_commit": task["subject_commit"],
                "conditions": ["review approved"],
                "expires_at": "2026-08-22T01:00:00Z",
                "single_use": True,
            }
        ),
        encoding="utf-8",
    )
    action_arguments = [
        "approve",
        "TASK-0001",
        "--type",
        "action",
        "--action-file",
        str(action_path),
        "--actor",
        "reviewer",
        "--reason",
        "notification approved",
    ]
    assert main(action_arguments) == 0
    assert (
        load_task_record(repository, "TASK-0001").task["current_state"]
        == "WAITING_FOR_FINAL_REVIEW"
    )

    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "evidence.json"), _evidence(repository)
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
        == 0
    )
    approvals = read_task_json(repository, "TASK-0001", "approvals.json")
    assert isinstance(approvals, list)
    assert {item["approval_type"] for item in approvals} == {"action", "code"}
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "APPROVED_FOR_MERGE"


def test_block_path_records_resolution_and_reclassification_history(
    tmp_path: Path, monkeypatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW")
    assert (
        main(
            [
                "escalate",
                "TASK-0001",
                "--to",
                "BLOCK",
                "--reason-code",
                "credentials_required",
                "--impact",
                "credentials unavailable",
                "--next-step",
                "remove credential use",
                "--actor",
                "agent",
            ]
        )
        == 0
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    resolve_task_path(repository, "TASK-0001", "resolution.md").write_text(
        "resolved\n", encoding="utf-8"
    )
    assert (
        main(
            [
                "resolve",
                "TASK-0001",
                "--condition",
                "credentials_required",
                "--evidence-ref",
                "resolution.md",
                "--reason",
                "credential use removed",
                "--actor",
                "reviewer",
                "--authorize-downgrade",
            ]
        )
        == 0
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    events = load_task_record(repository, "TASK-0001").events
    assert any(event["event_type"] == "block_resolved" for event in events)
    assert any(event["event_type"] == "resolution_recorded" for event in events)
