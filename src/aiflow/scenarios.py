"""Isolated, replayable scenario execution contracts."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from aiflow.errors import ContractError


@dataclass(frozen=True)
class ScenarioOperation:
    """One declared CLI operation and its observable expectations."""

    argv: tuple[str, ...]
    actor: str | None
    allowed_changes: tuple[str, ...]
    expected_state: str | None
    expected_gate_reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScenarioDefinition:
    """A complete ordered scenario definition."""

    scenario_id: str
    operations: tuple[ScenarioOperation, ...]


@dataclass(frozen=True)
class ScenarioRepository:
    """Fresh repository prepared for one scenario run."""

    root: Path
    initial_commit: str
    scenario_id: str


def _run_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode != 0:
        raise ContractError(
            "Could not prepare isolated scenario repository",
            code="SCENARIO_GIT_FAILED",
            details={"stderr": result.stderr.strip()},
        )
    return result.stdout.strip()


def prepare_scenario_repository(
    source_repository: Path,
    destination: Path,
    scenario_id: str,
) -> ScenarioRepository:
    """Copy governed inputs into a new Git repository without touching source tasks."""
    source = source_repository.resolve()
    target = destination.resolve()
    if target.exists():
        raise ContractError(
            "Scenario destination already exists", code="SCENARIO_DESTINATION_EXISTS"
        )
    scenario = source / "examples" / "scenarios" / scenario_id
    if not scenario.is_dir():
        raise ContractError("Scenario input is missing", code="SCENARIO_INPUT_MISSING")
    target.mkdir(parents=True)
    for name in ("policy", "schemas", "templates"):
        shutil.copytree(source / ".ai" / name, target / ".ai" / name)
    shutil.copy2(source / ".ai" / "repository-id", target / ".ai" / "repository-id")
    shutil.copytree(scenario, target / "scenario")
    _run_git(target, "init")
    _run_git(target, "config", "user.name", "AI Flow Scenario Runner")
    _run_git(target, "config", "user.email", "scenario@example.invalid")
    _run_git(target, "add", ".")
    _run_git(target, "commit", "-m", f"scenario baseline: {scenario_id}")
    return ScenarioRepository(target, _run_git(target, "rev-parse", "HEAD"), scenario_id)
