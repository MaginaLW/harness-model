"""Application service for creating recoverable AI Flow tasks."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from aiflow.contracts import require_valid_contract
from aiflow.errors import AiflowError, ContractError, PolicyError, StorageError
from aiflow.git_context import GitContext, collect_git_context
from aiflow.storage import (
    atomic_write_json,
    atomic_write_text,
    atomic_write_yaml,
    read_task_json,
    reserve_task_id,
    resolve_task_path,
)

CREATION_MARKER = "creation_failed.json"


@dataclass(frozen=True)
class StartResult:
    """Identity and location printed after task creation or recovery."""

    task_id: str
    task_directory: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _unique_nonempty(values: Sequence[str], *, field_name: str) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            raise ContractError(
                f"{field_name} entries cannot be empty",
                code="START_INPUT_INVALID",
                details={"field": field_name},
            )
        if normalized not in result:
            result.append(normalized)
    return result


def _validate_start_input(
    objective: str | None, allowed_scope: Sequence[str]
) -> tuple[str, list[str]]:
    normalized_objective = (objective or "").strip()
    if not normalized_objective:
        raise ContractError(
            "Start objective cannot be empty",
            code="START_INPUT_INVALID",
            details={"field": "objective"},
        )
    normalized_scope = _unique_nonempty(allowed_scope, field_name="allow")
    if not normalized_scope:
        raise ContractError(
            "Start requires at least one allowed scope",
            code="START_INPUT_INVALID",
            details={"field": "allow"},
        )
    if "**" in normalized_scope:
        raise ContractError(
            "Start does not accept '**' as an unbounded scope",
            code="START_SCOPE_UNBOUNDED",
            details={"field": "allow"},
        )
    return normalized_objective, normalized_scope


def _load_default_forbidden_actions(repository_root: Path) -> list[str]:
    path = repository_root / ".ai" / "policy" / "permissions.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise PolicyError(
            "Could not load permissions Policy",
            code="POLICY_LOAD_FAILED",
            details={"policy": "permissions"},
        ) from error
    if not isinstance(value, Mapping):
        raise PolicyError("Permissions Policy must be an object", code="POLICY_INVALID")
    actions = value.get("forbidden_automatic_actions")
    if not isinstance(actions, list) or not all(isinstance(action, str) for action in actions):
        raise PolicyError("Permissions Policy forbidden actions are invalid", code="POLICY_INVALID")
    return _unique_nonempty(actions, field_name="forbidden_automatic_actions")


def _load_spec_template(repository_root: Path) -> str:
    path = repository_root / ".ai" / "templates" / "spec.md"
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise StorageError(
            "Could not read task specification template",
            code="STORAGE_TEMPLATE_READ_FAILED",
            details={"template": "spec.md"},
        ) from error


def _build_task(
    task_id: str,
    objective: str,
    allowed_scope: list[str],
    forbidden_actions: list[str],
    context: GitContext,
    occurred_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "goal": objective,
        "repository_id": context.repository_id,
        "branch": context.branch,
        "base_commit": context.head,
        "subject_commit": context.head,
        "worktree_dirty": context.worktree_dirty,
        "worktree_dirty_paths": list(context.dirty_paths),
        "allowed_scope": allowed_scope,
        "forbidden_actions": forbidden_actions,
        "current_state": "NEW",
        "created_at": occurred_at,
        "updated_at": occurred_at,
        "decision_units": [
            {
                "schema_version": "1.0",
                "task_id": task_id,
                "decision_unit_id": "DU-001",
                "goal": objective,
                "inputs": [],
                "planned_actions": ["Implement the bounded task objective"],
                "impact_scope": allowed_scope,
                "reversibility": "reversible",
                "verification_methods": ["Define and run executable verification"],
                "external_side_effects": [],
                "permission_requirements": [],
            }
        ],
        "repository_path_at_creation": context.repository_path,
    }


def _build_event(task_id: str, objective: str, occurred_at: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "sequence": 1,
        "from_state": "NEW",
        "to_state": "NEW",
        "event_type": "task_created",
        "actor": "aiflow",
        "occurred_at": occurred_at,
        "payload": {"objective": objective},
    }


def _validate_bundle(bundle: Mapping[str, object], task_id: str) -> None:
    task = bundle.get("task")
    event = bundle.get("event")
    spec = bundle.get("spec")
    approvals = bundle.get("approvals")
    if not isinstance(task, dict) or task.get("task_id") != task_id:
        raise StorageError(
            "Creation marker contains an invalid task", code="START_RECOVERY_INVALID"
        )
    if not isinstance(event, dict) or event.get("task_id") != task_id:
        raise StorageError(
            "Creation marker contains an invalid event", code="START_RECOVERY_INVALID"
        )
    if not isinstance(spec, str) or not isinstance(approvals, list):
        raise StorageError("Creation marker is incomplete", code="START_RECOVERY_INVALID")
    require_valid_contract("task", task)
    require_valid_contract("event", event)
    for approval in approvals:
        require_valid_contract("approval", approval)


def _write_required_documents(task_directory: Path, bundle: Mapping[str, object]) -> None:
    task = bundle["task"]
    event = bundle["event"]
    spec = bundle["spec"]
    approvals = bundle["approvals"]
    atomic_write_yaml(task_directory / "task.yaml", task)
    atomic_write_text(
        task_directory / "events.jsonl",
        json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n",
    )
    if not isinstance(spec, str):
        raise StorageError("Creation specification is invalid", code="START_RECOVERY_INVALID")
    atomic_write_text(task_directory / "spec.md", spec)
    atomic_write_json(task_directory / "approvals.json", approvals)


def _remove_marker(marker: Path) -> None:
    try:
        marker.unlink()
    except OSError as error:
        raise StorageError(
            "Task files were written but the creation marker could not be removed",
            code="START_MARKER_REMOVE_FAILED",
            details={"task_id": marker.parent.name},
        ) from error


def _complete_bundle(task_id: str, task_directory: Path, bundle: dict[str, Any]) -> StartResult:
    _validate_bundle(bundle, task_id)
    marker = task_directory / CREATION_MARKER
    atomic_write_json(marker, bundle)
    try:
        _write_required_documents(task_directory, bundle)
        _remove_marker(marker)
    except AiflowError as error:
        failed_bundle = {**bundle, "status": "creation_failed", "failure_code": error.code}
        try:
            atomic_write_json(marker, failed_bundle)
        except AiflowError:
            pass
        raise StorageError(
            f"Task creation failed; run 'aiflow start --recover {task_id}'",
            code="START_CREATION_FAILED",
            details={"task_id": task_id, "cause": error.code},
        ) from error
    return StartResult(task_id=task_id, task_directory=task_directory)


def start_task(
    repository_root: Path,
    *,
    objective: str | None,
    allowed_scope: Sequence[str],
    forbidden_actions: Sequence[str],
    allow_detached: bool = False,
) -> StartResult:
    """Create a complete initial task or leave an explicit recovery marker."""
    objective_value, scope = _validate_start_input(objective, allowed_scope)
    context = collect_git_context(repository_root)
    if context.branch == "DETACHED" and not allow_detached:
        raise ContractError(
            "Start rejects detached HEAD unless --allow-detached is provided",
            code="START_DETACHED_HEAD",
            details={},
        )
    defaults = _load_default_forbidden_actions(Path(context.repository_path))
    requested_forbidden = _unique_nonempty(forbidden_actions, field_name="forbid-action")
    combined_forbidden = list(dict.fromkeys([*defaults, *requested_forbidden]))
    spec = _load_spec_template(Path(context.repository_path))

    task_id = reserve_task_id(Path(context.repository_path))
    task_directory = resolve_task_path(Path(context.repository_path), task_id)
    occurred_at = _utc_now()
    bundle: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "creating",
        "task_id": task_id,
        "task": _build_task(
            task_id,
            objective_value,
            scope,
            combined_forbidden,
            context,
            occurred_at,
        ),
        "event": _build_event(task_id, objective_value, occurred_at),
        "spec": spec,
        "approvals": [],
    }
    return _complete_bundle(task_id, task_directory, bundle)


def recover_task(repository_root: Path, task_id: str) -> StartResult:
    """Complete a previously interrupted task creation from its marker."""
    context = collect_git_context(repository_root)
    try:
        raw_bundle = read_task_json(
            Path(context.repository_path),
            task_id,
            CREATION_MARKER,
        )
    except AiflowError as error:
        raise StorageError(
            f"Task {task_id} is not recoverable",
            code="START_NOT_RECOVERABLE",
            details={"task_id": task_id},
        ) from error
    if not isinstance(raw_bundle, dict):
        raise StorageError(
            f"Task {task_id} is not recoverable",
            code="START_RECOVERY_INVALID",
            details={"task_id": task_id},
        )
    task = raw_bundle.get("task")
    if not isinstance(task, dict) or task.get("repository_id") != context.repository_id:
        raise StorageError(
            "Recovery marker belongs to a different repository",
            code="START_RECOVERY_REPOSITORY_MISMATCH",
            details={"task_id": task_id},
        )
    task_directory = resolve_task_path(Path(context.repository_path), task_id)
    return _complete_bundle(task_id, task_directory, raw_bundle)
