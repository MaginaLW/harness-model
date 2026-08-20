"""Runtime golden classifications and conservative routing metamorphic checks."""

from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from aiflow.classification_service import _stable_input, classify_task
from aiflow.cli import main
from aiflow.decision_units import parse_decision_units
from aiflow.policy import load_policy_bundle
from aiflow.storage import (
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record, record_task_event

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_ROOT = PROJECT_ROOT / "examples" / "scenarios"
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"
TASK_ID = "TASK-0001"


def _run_git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=10,
    )


def _repository(path: Path) -> Path:
    path.mkdir()
    _run_git(path, "init", "-b", "main")
    ai_root = path / ".ai"
    ai_root.mkdir()
    for directory in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / directory, ai_root / directory)
    (ai_root / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _run_git(path, "add", ".ai", "tracked.txt")
    _run_git(
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


def _scenario_unit(scenario_id: str) -> dict[str, Any]:
    raw = yaml.safe_load((SCENARIO_ROOT / scenario_id / "input.yaml").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    unit = deepcopy(raw)
    unit["task_id"] = TASK_ID
    return unit


def _expected(scenario_id: str) -> dict[str, Any]:
    raw = json.loads((SCENARIO_ROOT / scenario_id / "expected.json").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def _prepare_task(repository: Path, monkeypatch: pytest.MonkeyPatch, unit: dict[str, Any]) -> None:
    monkeypatch.chdir(repository)
    assert (
        main(
            [
                "start",
                "--objective",
                "golden classification",
                "--allow",
                "docs/**",
                "--allow",
                "src/**",
                "--allow",
                ".github/**",
                "--allow",
                "data/**",
            ]
        )
        == 0
    )
    task_path = resolve_task_path(repository, TASK_ID, "task.yaml")
    task = read_task_yaml(repository, TASK_ID, "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [unit]
    atomic_write_yaml(task_path, task)


def _classify_fresh(
    directory: Path, monkeypatch: pytest.MonkeyPatch, unit: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    repository = _repository(directory)
    _prepare_task(repository, monkeypatch, unit)
    classification = classify_task(repository, TASK_ID, actor="golden")
    return classification, str(load_task_record(repository, TASK_ID).task["current_state"])


@pytest.mark.parametrize(
    "scenario_id",
    ("auto-doc-edit", "ask-conflict-strategy", "review-workflow-change", "block-no-backup"),
)
def test_runtime_classification_matches_frozen_golden_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario_id: str
) -> None:
    repository = _repository(tmp_path / scenario_id)
    _prepare_task(repository, monkeypatch, _scenario_unit(scenario_id))

    classification = classify_task(repository, TASK_ID, actor="golden")
    # Run the public command too. Same identity must be an idempotent read of durable evidence.
    assert main(["classify", TASK_ID, "--actor", "golden-cli"]) == 0

    expected = _expected(scenario_id)
    record = load_task_record(repository, TASK_ID)
    assert classification["effective_route"] == expected["route"]
    assert classification["effective_verification_level"] == expected["verification_level"]
    assert record.task["current_state"] == expected["next_allowed_state"]
    assert len(classification["classifications"]) == 1
    unit = classification["classifications"][0]
    assert unit["decision_unit_id"] == _scenario_unit(scenario_id)["decision_unit_id"]
    assert [rule["rule_id"] for rule in unit["matched_rules"]] == expected["rule_ids"]
    assert unit["explanations"] == expected["reasons"]


def test_auto_facts_are_monotonic_under_risk_additions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = _scenario_unit("auto-doc-edit")

    classification, state = _classify_fresh(tmp_path / "baseline", monkeypatch, baseline)
    assert (classification["effective_route"], state) == ("AUTO", "READY_TO_IMPLEMENT")

    ci = deepcopy(baseline)
    ci["impact_categories"] = ["ci"]
    classification, state = _classify_fresh(tmp_path / "ci", monkeypatch, ci)
    assert (classification["effective_route"], state) == ("REVIEW", "WAITING_FOR_SPEC_REVIEW")

    external = deepcopy(baseline)
    external["external_side_effects"] = ["notification"]
    classification, state = _classify_fresh(tmp_path / "external", monkeypatch, external)
    assert classification["effective_route"] in {"REVIEW", "BLOCK"}
    assert state in {"WAITING_FOR_SPEC_REVIEW", "BLOCKED"}

    missing_tools = deepcopy(baseline)
    missing_tools["verification"] = {"automatic": True, "tools_missing": True}
    classification, state = _classify_fresh(tmp_path / "missing-tools", monkeypatch, missing_tools)
    assert (classification["effective_route"], state) == ("BLOCK", "BLOCKED")

    restored = _scenario_unit("auto-doc-edit")
    classification, state = _classify_fresh(tmp_path / "restored", monkeypatch, restored)
    assert (classification["effective_route"], state) == ("AUTO", "READY_TO_IMPLEMENT")


def test_auto_is_restored_after_bound_authorized_block_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path / "authorized-restoration")
    blocked = _scenario_unit("auto-doc-edit")
    blocked["verification"] = {"automatic": True, "tools_missing": True}
    _prepare_task(repository, monkeypatch, blocked)
    initial = classify_task(repository, TASK_ID, actor="golden")
    assert initial["effective_route"] == "BLOCK"

    task_path = resolve_task_path(repository, TASK_ID, "task.yaml")
    task = read_task_yaml(repository, TASK_ID, "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [_scenario_unit("auto-doc-edit")]
    atomic_write_yaml(task_path, task)
    new_input_sha256 = _stable_input(task, parse_decision_units(task))
    policy_sha256 = load_policy_bundle(repository).sha256
    record_task_event(
        repository,
        TASK_ID,
        event_type="resolution_recorded",
        actor="reviewer",
        payload={
            "reason": "verification tools restored",
            "evidence_refs": ["evidence-tools-restored"],
            "previous_classification_input_sha256": initial["classification_input_sha256"],
            "previous_policy_sha256": initial["policy_sha256"],
            "manual_authorization": True,
            "authorized_by": "reviewer",
            "authorized_classification_input_sha256": new_input_sha256,
            "authorized_policy_sha256": policy_sha256,
        },
    )
    restored = classify_task(repository, TASK_ID, actor="golden")
    persisted = read_task_json(
        repository, TASK_ID, "classification.json", contract_name="classification"
    )
    assert isinstance(persisted, dict)
    assert restored["effective_route"] == persisted["effective_route"] == "AUTO"
    assert load_task_record(repository, TASK_ID).task["current_state"] == "READY_TO_IMPLEMENT"
