from __future__ import annotations

from pathlib import Path

import pytest
from scenario_support import TASK_ID, classification, prepare_task, state

from aiflow.cli import main
from aiflow.storage import atomic_write_yaml, read_task_yaml, resolve_task_path
from aiflow.task_service import load_task_record


def test_block_scenario_requires_backup_and_dry_run_before_reclassification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _unit, expected = prepare_task(tmp_path, monkeypatch, "block-no-backup")
    assert main(["classify", TASK_ID, "--actor", "classifier"]) == 0
    assert classification(repository)["effective_route"] == expected["route"] == "BLOCK"
    assert state(repository) == "BLOCKED"
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 1
    assert main(["verify", TASK_ID, "--actor", "verifier"]) == 1
    assert main(["gate", TASK_ID, "--format", "json"]) == 2

    task = read_task_yaml(repository, TASK_ID, "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    unit = task["decision_units"][0]
    unit.update(
        {
            "planned_actions": ["dry_run_overwrite"],
            "impact_scope": ["data/live/batch/sample.json"],
            "reversibility": "reversible",
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
    )
    atomic_write_yaml(resolve_task_path(repository, TASK_ID, "task.yaml"), task)
    resolution = resolve_task_path(repository, TASK_ID, "resolution.md")
    resolution.write_text(
        "Verified backup restore check passed; operation is dry-run only.\n", encoding="utf-8"
    )
    assert (
        main(
            [
                "resolve",
                TASK_ID,
                "--condition",
                "backup_and_dry_run",
                "--evidence-ref",
                "resolution.md",
                "--reason",
                "backup verified and operation narrowed to dry-run",
                "--actor",
                "reviewer",
                "--authorize-downgrade",
            ]
        )
        == 0
    )
    assert main(["classify", TASK_ID, "--actor", "classifier"]) == 0
    assert classification(repository)["effective_route"] == "AUTO"
    events = load_task_record(repository, TASK_ID).events
    assert any(event["event_type"] == "classification_blocked" for event in events)
    assert any(event["event_type"] == "resolution_recorded" for event in events)
    assert any(event["event_type"] == "block_resolved" for event in events)
    assert state(repository) == "READY_TO_IMPLEMENT"
