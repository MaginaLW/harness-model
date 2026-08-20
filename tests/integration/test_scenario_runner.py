from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aiflow.errors import ContractError
from aiflow.scenarios import (
    ScenarioDefinition,
    ScenarioOperation,
    prepare_scenario_repository,
    run_scenario,
)

ROOT = Path(__file__).resolve().parents[2]


def _status(root: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain=v1", "-uall"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    ).stdout


def test_scenario_repository_isolated_from_source_checkout(tmp_path: Path) -> None:
    before = _status(ROOT)

    first = prepare_scenario_repository(ROOT, tmp_path / "first", "auto-doc-edit")
    second = prepare_scenario_repository(ROOT, tmp_path / "second", "auto-doc-edit")

    for prepared in (first, second):
        assert len(prepared.initial_commit) == 40
        assert (prepared.root / "scenario" / "input.yaml").is_file()
        assert (prepared.root / ".ai" / "policy" / "routing.yaml").is_file()
        assert (prepared.root / ".ai" / "templates" / "task.yaml").is_file()
        assert not (prepared.root / ".ai" / "tasks").exists()
        assert _status(prepared.root) == ""
    assert _status(ROOT) == before


def test_scenario_repository_rejects_missing_input_or_existing_target(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="input is missing"):
        prepare_scenario_repository(ROOT, tmp_path / "missing", "not-a-scenario")
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ContractError, match="already exists"):
        prepare_scenario_repository(ROOT, existing, "auto-doc-edit")


def _start_definition() -> ScenarioDefinition:
    return ScenarioDefinition(
        "auto-doc-edit",
        (
            ScenarioOperation(
                (
                    "start",
                    "--objective",
                    "Run isolated scenario",
                    "--allow",
                    "docs/example.md",
                ),
                None,
                (),
                "NEW",
            ),
            ScenarioOperation(
                ("status", "{task_id}", "--format", "json"),
                None,
                (),
                "NEW",
            ),
        ),
    )


def test_operations_capture_artifacts_and_replay_deterministically(tmp_path: Path) -> None:
    first = run_scenario(
        prepare_scenario_repository(ROOT, tmp_path / "first-run", "auto-doc-edit"),
        _start_definition(),
    )
    second = run_scenario(
        prepare_scenario_repository(ROOT, tmp_path / "second-run", "auto-doc-edit"),
        _start_definition(),
    )

    assert first.materialized_state == first.replayed_state == "NEW"
    assert first.event_states == ("NEW",)
    assert [command.exit_code for command in first.commands] == [0, 0]
    assert first.classification is None
    assert first.approvals == ()
    assert first.evidence is None
    assert first.semantic_view() == second.semantic_view()


def test_operation_rejects_undeclared_changes(tmp_path: Path) -> None:
    prepared = prepare_scenario_repository(ROOT, tmp_path / "scope-run", "auto-doc-edit")
    (prepared.root / "outside.txt").write_text("unexpected\n", encoding="utf-8")

    with pytest.raises(ContractError, match="must start clean"):
        run_scenario(prepared, _start_definition())
