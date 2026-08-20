"""Isolated, replayable scenario execution contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
from contextlib import chdir, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from aiflow.cli import main as cli_main
from aiflow.errors import ContractError
from aiflow.scope import matches_scope, normalize_repository_path
from aiflow.state import replay_events
from aiflow.storage import read_task_json, resolve_task_path
from aiflow.task_service import read_task_record_strict


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


@dataclass(frozen=True)
class ScenarioCommandResult:
    """One captured CLI invocation."""

    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    observed_state: str | None
    gate_reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioResult:
    """Replayable governed artifacts produced by one isolated run."""

    scenario_id: str
    task_id: str
    commands: tuple[ScenarioCommandResult, ...]
    event_states: tuple[str, ...]
    materialized_state: str
    replayed_state: str
    task: dict[str, Any]
    classification: dict[str, Any] | None
    approvals: tuple[dict[str, Any], ...]
    evidence: dict[str, Any] | None
    gate: dict[str, Any] | None

    def semantic_view(self) -> dict[str, Any]:
        """Remove runtime-only values while retaining decisions and ordering."""
        value = _semantic_value(
            {
                "scenario_id": self.scenario_id,
                "task_id": self.task_id,
                "commands": [
                    {
                        "argv": result.argv,
                        "exit_code": result.exit_code,
                        "observed_state": result.observed_state,
                        "gate_reason_codes": result.gate_reason_codes,
                    }
                    for result in self.commands
                ],
                "event_states": self.event_states,
                "materialized_state": self.materialized_state,
                "replayed_state": self.replayed_state,
                "task": self.task,
                "classification": self.classification,
                "approvals": self.approvals,
                "evidence": self.evidence,
                "gate": self.gate,
            }
        )
        if not isinstance(value, dict):
            raise AssertionError("scenario semantic view must be an object")
        return value


_RUNTIME_KEYS = frozenset(
    {
        "attestation_head",
        "base_commit",
        "classified_at",
        "created_at",
        "evidence_path",
        "expires_at",
        "frozen_at",
        "merge_commit",
        "occurred_at",
        "observed_head",
        "repository_path_at_creation",
        "run_id",
        "spec_frozen_at",
        "subject_commit",
        "updated_at",
    }
)


def _semantic_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _semantic_value(item)
            for key, item in sorted(value.items())
            if key not in _RUNTIME_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_semantic_value(item) for item in value]
    if isinstance(value, Path):
        return value.name
    return value


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


def _changed_paths(root: Path) -> frozenset[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if result.returncode != 0:
        raise ContractError("Could not inspect scenario changes", code="SCENARIO_GIT_FAILED")
    records = [item for item in result.stdout.decode("utf-8").split("\0") if item]
    paths: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        status = record[:2]
        paths.add(record[3:])
        if "R" in status or "C" in status:
            index += 1
            if index >= len(records):
                raise ContractError(
                    "Could not inspect scenario changes", code="SCENARIO_GIT_FAILED"
                )
            paths.add(records[index])
        index += 1
    return frozenset(normalize_repository_path(path) for path in paths)


def _expanded_argv(operation: ScenarioOperation, task_id: str | None) -> tuple[str, ...]:
    if not operation.argv:
        raise ContractError("Scenario command is empty", code="SCENARIO_OPERATION_INVALID")
    expanded: list[str] = []
    for value in operation.argv:
        if "{task_id}" in value:
            if task_id is None:
                raise ContractError(
                    "Scenario task ID is not available", code="SCENARIO_TASK_ID_MISSING"
                )
            value = value.replace("{task_id}", task_id)
        expanded.append(value)
    if operation.actor and "--actor" not in expanded:
        expanded.extend(("--actor", operation.actor))
    return tuple(expanded)


def _require_allowed_changes(
    paths: frozenset[str], operation: ScenarioOperation, task_id: str | None
) -> None:
    allowed = operation.allowed_changes
    unexpected = sorted(
        path
        for path in paths
        if not (
            (task_id is not None and matches_scope(path, f".ai/tasks/{task_id}/**"))
            or any(matches_scope(path, pattern) for pattern in allowed)
        )
    )
    if unexpected:
        raise ContractError(
            "Scenario command changed paths outside its declaration",
            code="SCENARIO_SCOPE_EXPANDED",
            details={"paths": unexpected},
        )


def _optional_json(root: Path, task_id: str, filename: str) -> dict[str, Any] | None:
    path = resolve_task_path(root, task_id, filename)
    if not path.is_file():
        return None
    value = read_task_json(root, task_id, filename)
    if not isinstance(value, dict):
        raise ContractError("Scenario artifact is invalid", code="SCENARIO_ARTIFACT_INVALID")
    return value


def run_scenario(repository: ScenarioRepository, definition: ScenarioDefinition) -> ScenarioResult:
    """Execute declared CLI operations and return a strict, replayable result."""
    if definition.scenario_id != repository.scenario_id or not definition.operations:
        raise ContractError("Scenario definition is invalid", code="SCENARIO_DEFINITION_INVALID")
    task_id: str | None = None
    previous_paths = _changed_paths(repository.root)
    if previous_paths:
        raise ContractError(
            "Scenario repository must start clean",
            code="SCENARIO_REPOSITORY_DIRTY",
            details={"paths": sorted(previous_paths)},
        )
    commands: list[ScenarioCommandResult] = []
    gate: dict[str, Any] | None = None
    with chdir(repository.root):
        for operation in definition.operations:
            argv = _expanded_argv(operation, task_id)
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = cli_main(argv)
            output = stdout.getvalue().strip()
            if task_id is None and argv[0] == "start" and exit_code == 0:
                task_id = output.splitlines()[0]
            current_paths = _changed_paths(repository.root)
            _require_allowed_changes(current_paths - previous_paths, operation, task_id)
            previous_paths = current_paths
            observed_state = None
            if task_id is not None:
                observed_state = str(
                    read_task_record_strict(repository.root, task_id).task["current_state"]
                )
            if operation.expected_state is not None and observed_state != operation.expected_state:
                raise ContractError(
                    "Scenario state did not match its declaration",
                    code="SCENARIO_STATE_MISMATCH",
                    details={"expected": operation.expected_state, "observed": observed_state},
                )
            reason_codes: tuple[str, ...] = ()
            if argv[0] == "gate" and output:
                parsed = json.loads(output)
                if not isinstance(parsed, dict):
                    raise ContractError(
                        "Scenario Gate output is invalid", code="SCENARIO_GATE_INVALID"
                    )
                gate = parsed
                reasons = parsed.get("reason_codes", [])
                reason_codes = tuple(str(item) for item in reasons)
            if reason_codes != operation.expected_gate_reason_codes:
                raise ContractError(
                    "Scenario Gate reasons did not match its declaration",
                    code="SCENARIO_GATE_MISMATCH",
                )
            commands.append(
                ScenarioCommandResult(
                    argv,
                    exit_code,
                    output,
                    stderr.getvalue().strip(),
                    observed_state,
                    reason_codes,
                )
            )
    if task_id is None:
        raise ContractError("Scenario did not create a task", code="SCENARIO_TASK_ID_MISSING")
    record = read_task_record_strict(repository.root, task_id)
    replayed_state = replay_events(record.events, task_id=task_id)
    approvals_value = read_task_json(repository.root, task_id, "approvals.json")
    if not isinstance(approvals_value, list) or not all(
        isinstance(item, dict) for item in approvals_value
    ):
        raise ContractError("Scenario approvals are invalid", code="SCENARIO_ARTIFACT_INVALID")
    return ScenarioResult(
        definition.scenario_id,
        task_id,
        tuple(commands),
        tuple(str(event["to_state"]) for event in record.events),
        str(record.task["current_state"]),
        replayed_state,
        dict(record.task),
        _optional_json(repository.root, task_id, "classification.json"),
        tuple(dict(item) for item in approvals_value),
        _optional_json(repository.root, task_id, "evidence.json"),
        gate,
    )
