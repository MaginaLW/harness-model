"""Application service for creating recoverable AI Flow tasks."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from aiflow.contracts import require_valid_contract
from aiflow.errors import (
    AiflowError,
    ContractError,
    PolicyError,
    StateTransitionError,
    StorageError,
)
from aiflow.git_context import GitContext, collect_git_context
from aiflow.specification import specification_digest, validate_specification
from aiflow.state import create_record_event, create_transition_event, replay_events
from aiflow.storage import (
    atomic_write_json,
    atomic_write_text,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    reserve_task_id,
    resolve_task_path,
)

CREATION_MARKER = "creation_failed.json"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ESCALATING_FAILURE_MARKERS = frozenset(
    {
        "scope_expanded",
        "new_dependencies",
        "new_permissions",
        "unverifiable",
        "high_risk_side_effects",
    }
)
FREEZE_ALLOWED_STATES = frozenset(
    {"NEW", "CLASSIFIED", "WAITING_FOR_SPEC_REVIEW", "READY_TO_IMPLEMENT"}
)


@dataclass(frozen=True)
class StartResult:
    """Identity and location printed after task creation or recovery."""

    task_id: str
    task_directory: Path


@dataclass(frozen=True)
class TaskRecord:
    """A validated materialized task and its replayable event history."""

    task: dict[str, Any]
    events: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class TransitionResult:
    """The new task materialization and appended transition event."""

    task: dict[str, Any]
    event: dict[str, Any]


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


def _read_event_log(repository_root: Path, task_id: str) -> list[dict[str, Any]]:
    path = resolve_task_path(repository_root, task_id, "events.jsonl")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise StorageError(
            "Could not read task event log",
            code="STATE_EVENT_LOG_READ_FAILED",
            details={"task_id": task_id},
        ) from error
    events: list[dict[str, Any]] = []
    for sequence, line in enumerate(lines, start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise StorageError(
                "Could not parse task event log",
                code="STATE_EVENT_LOG_PARSE_FAILED",
                details={"sequence": sequence},
            ) from error
        if not isinstance(value, dict):
            raise StorageError(
                "Task event must be a JSON object",
                code="STATE_EVENT_LOG_PARSE_FAILED",
                details={"sequence": sequence},
            )
        events.append(value)
    return events


def _append_event(path: Path, event: Mapping[str, object]) -> None:
    content = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_APPEND | os.O_WRONLY)
        written = os.write(descriptor, content)
        if written != len(content):
            raise OSError("partial event append")
        os.fsync(descriptor)
    except OSError as error:
        raise StorageError(
            "Could not append task event",
            code="STATE_EVENT_APPEND_FAILED",
            details={"task_id": path.parent.name},
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _replace_materialized_task(staged: Path, target: Path) -> None:
    os.replace(staged, target)


def _persist_event_and_task(
    task_directory: Path,
    task: Mapping[str, object],
    event: Mapping[str, object],
) -> None:
    target = task_directory / "task.yaml"
    staged = task_directory / "task.yaml.next"
    atomic_write_yaml(staged, task)
    try:
        _append_event(task_directory / "events.jsonl", event)
    except AiflowError:
        staged.unlink(missing_ok=True)
        raise
    try:
        _replace_materialized_task(staged, target)
    except OSError as error:
        raise StorageError(
            "Event was appended but materialized task replacement failed",
            code="STATE_MATERIALIZATION_FAILED",
            details={"task_id": task_directory.name},
        ) from error


def load_task_record(repository_root: Path, task_id: str) -> TaskRecord:
    """Load and replay a task, repairing event-ahead materialization if necessary."""
    raw_task = read_task_yaml(
        repository_root,
        task_id,
        "task.yaml",
        contract_name="task",
    )
    if not isinstance(raw_task, dict):
        raise StorageError("Task document must be an object", code="STATE_TASK_INVALID")
    task: dict[str, Any] = raw_task
    events = _read_event_log(repository_root, task_id)
    terminal_state = replay_events(events, task_id=task_id)
    if task.get("current_state") == terminal_state:
        return TaskRecord(task=task, events=tuple(events))

    staged_path = resolve_task_path(repository_root, task_id, "task.yaml.next")
    if not staged_path.is_file():
        raise StateTransitionError(
            "Materialized task differs from replay without a staged replacement",
            code="STATE_MATERIALIZATION_MISMATCH",
            details={"materialized": task.get("current_state"), "replayed": terminal_state},
        )
    staged_task = read_task_yaml(
        repository_root,
        task_id,
        "task.yaml.next",
        contract_name="task",
    )
    if not isinstance(staged_task, dict) or staged_task.get("current_state") != terminal_state:
        raise StateTransitionError(
            "Materialized task differs from replay without a valid staged replacement",
            code="STATE_MATERIALIZATION_MISMATCH",
            details={"materialized": task.get("current_state"), "replayed": terminal_state},
        )
    repaired: dict[str, Any] = staged_task
    recovery_event = create_record_event(
        repaired,
        event_type="state_recovered",
        actor="aiflow",
        payload={"materialized_state": task.get("current_state")},
        sequence=len(events) + 1,
    )
    require_valid_contract("task", repaired)
    task_directory = resolve_task_path(repository_root, task_id)
    _persist_event_and_task(task_directory, repaired, recovery_event)
    return TaskRecord(task=repaired, events=tuple([*events, recovery_event]))


def read_task_record_strict(repository_root: Path, task_id: str) -> TaskRecord:
    """Read and replay a task without repairing or mutating any file."""
    raw_task = read_task_yaml(
        repository_root,
        task_id,
        "task.yaml",
        contract_name="task",
    )
    if not isinstance(raw_task, dict):
        raise StorageError("Task document must be an object", code="STATE_TASK_INVALID")
    events = _read_event_log(repository_root, task_id)
    terminal_state = replay_events(events, task_id=task_id)
    if raw_task.get("current_state") != terminal_state:
        raise StateTransitionError(
            "Materialized task state does not match event replay",
            code="STATE_MATERIALIZATION_MISMATCH",
            details={"materialized": raw_task.get("current_state"), "replayed": terminal_state},
        )
    return TaskRecord(task=raw_task, events=tuple(events))


def transition_task_record(
    repository_root: Path,
    task_id: str,
    *,
    target_state: str,
    event_type: str,
    actor: str,
    payload: Mapping[str, object],
    satisfied_preconditions: set[str],
) -> TransitionResult:
    """Validate, append, and materialize one state transition."""
    record = load_task_record(repository_root, task_id)
    event = create_transition_event(
        record.task,
        target_state=target_state,
        event_type=event_type,
        actor=actor,
        payload=payload,
        sequence=len(record.events) + 1,
        satisfied_preconditions=satisfied_preconditions,
    )
    task = {**record.task, "current_state": target_state, "updated_at": event["occurred_at"]}
    require_valid_contract("task", task)
    task_directory = resolve_task_path(repository_root, task_id)
    _persist_event_and_task(task_directory, task, event)
    return TransitionResult(task=task, event=event)


def record_task_event(
    repository_root: Path,
    task_id: str,
    *,
    event_type: str,
    actor: str,
    payload: Mapping[str, object],
) -> TransitionResult:
    """Append one closed non-state event without changing task state."""
    record = load_task_record(repository_root, task_id)
    event = create_record_event(
        record.task,
        event_type=event_type,
        actor=actor,
        payload=payload,
        sequence=len(record.events) + 1,
    )
    task = {**record.task, "updated_at": event["occurred_at"]}
    require_valid_contract("task", task)
    task_directory = resolve_task_path(repository_root, task_id)
    _persist_event_and_task(task_directory, task, event)
    return TransitionResult(task=task, event=event)


def freeze_task(
    repository_root: Path,
    task_id: str,
    *,
    actor: str,
    allow_waiting_for_ask: bool = False,
) -> TransitionResult:
    """Validate and freeze the current specification without changing task state."""
    record = load_task_record(repository_root, task_id)
    allowed_states = set(FREEZE_ALLOWED_STATES)
    if allow_waiting_for_ask:
        allowed_states.add("WAITING_FOR_ASK")
    current_state = record.task.get("current_state")
    if current_state not in allowed_states:
        raise StateTransitionError(
            "Task specification cannot be frozen from its current state",
            code="STATE_TRANSITION_NOT_ALLOWED",
            details={"current_state": current_state},
        )

    spec_path = resolve_task_path(repository_root, task_id, "spec.md")
    try:
        content = spec_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise StorageError(
            "Could not read task specification",
            code="SPECIFICATION_READ_FAILED",
            details={"task_id": task_id},
        ) from error
    assessment = validate_specification(content)

    event = create_record_event(
        record.task,
        event_type="spec_frozen",
        actor=actor,
        payload={
            "spec_sha256": assessment.sha256,
            "previous_spec_sha256": record.task.get("frozen_spec_sha256"),
            "normalized": assessment.normalized != content,
        },
        sequence=len(record.events) + 1,
    )
    task = {
        **record.task,
        "frozen_spec_sha256": assessment.sha256,
        "spec_frozen_at": event["occurred_at"],
        "updated_at": event["occurred_at"],
    }
    require_valid_contract("task", task)
    if assessment.normalized != content:
        atomic_write_text(spec_path, assessment.normalized)
    _persist_event_and_task(resolve_task_path(repository_root, task_id), task, event)
    return TransitionResult(task=task, event=event)


def specification_is_current(repository_root: Path, task_id: str) -> bool:
    """Return whether the current specification matches the recorded frozen digest."""
    record = load_task_record(repository_root, task_id)
    frozen_digest = record.task.get("frozen_spec_sha256")
    if not isinstance(frozen_digest, str):
        return False
    spec_path = resolve_task_path(repository_root, task_id, "spec.md")
    try:
        content = spec_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise StorageError(
            "Could not read task specification",
            code="SPECIFICATION_READ_FAILED",
            details={"task_id": task_id},
        ) from error
    return specification_digest(content) == frozen_digest


def _load_classification(repository_root: Path, task_id: str) -> dict[str, Any]:
    value = read_task_json(
        repository_root,
        task_id,
        "classification.json",
        contract_name="classification",
    )
    if not isinstance(value, dict):
        raise ContractError(
            "Task classification must be an object", code="BEGIN_CLASSIFICATION_INVALID"
        )
    return value


def _load_approvals(repository_root: Path, task_id: str) -> list[dict[str, Any]]:
    value = read_task_json(repository_root, task_id, "approvals.json")
    if not isinstance(value, list):
        raise ContractError("Task approvals must be an array", code="BEGIN_APPROVAL_INVALID")
    approvals: list[dict[str, Any]] = []
    for approval in value:
        if not isinstance(approval, dict):
            raise ContractError("Task approval must be an object", code="BEGIN_APPROVAL_INVALID")
        require_valid_contract("approval", approval)
        approvals.append(approval)
    return approvals


def _require_ready_artifacts(repository_root: Path, task_id: str, record: TaskRecord) -> None:
    if not isinstance(record.task.get("frozen_spec_sha256"), str):
        raise ContractError("Task specification is not frozen", code="BEGIN_SPEC_NOT_FROZEN")
    if not specification_is_current(repository_root, task_id):
        raise ContractError(
            "Task specification changed after it was frozen",
            code="BEGIN_SPEC_CHANGED",
        )
    classification = _load_classification(repository_root, task_id)
    entries = classification.get("classifications")
    if not isinstance(entries, list):
        raise ContractError(
            "Task classification is incomplete", code="BEGIN_CLASSIFICATION_INVALID"
        )
    task_units = record.task.get("decision_units")
    if not isinstance(task_units, list):
        raise ContractError("Task decision units are invalid", code="BEGIN_CLASSIFICATION_INVALID")
    expected_ids = {
        unit.get("decision_unit_id") for unit in task_units if isinstance(unit, Mapping)
    }
    classified_ids = {
        entry.get("decision_unit_id") for entry in entries if isinstance(entry, Mapping)
    }
    if expected_ids != classified_ids or None in expected_ids:
        raise ContractError(
            "Task classification is incomplete", code="BEGIN_CLASSIFICATION_INVALID"
        )
    if any(isinstance(entry, Mapping) and entry.get("route") == "BLOCK" for entry in entries):
        raise ContractError(
            "Blocked classification cannot begin", code="BEGIN_CLASSIFICATION_BLOCKED"
        )

    review_entries = [
        entry for entry in entries if isinstance(entry, Mapping) and entry.get("route") == "REVIEW"
    ]
    if not review_entries:
        return
    approvals = _load_approvals(repository_root, task_id)
    spec_path = resolve_task_path(repository_root, task_id, "spec.md")
    try:
        spec_sha = specification_digest(spec_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise StorageError(
            "Could not read frozen specification", code="BEGIN_SPEC_READ_FAILED"
        ) from error
    subject_commit = record.task.get("subject_commit")
    for entry in review_entries:
        decision_unit_id = entry.get("decision_unit_id")
        policy_sha = entry.get("policy_sha256")
        if not any(
            approval.get("approval_type") == "spec"
            and approval.get("decision_unit_id") == decision_unit_id
            and approval.get("spec_sha256") == spec_sha
            and approval.get("policy_sha256") == policy_sha
            and approval.get("subject_commit") == subject_commit
            for approval in approvals
        ):
            raise ContractError(
                "Required specification approval is missing or stale",
                code="BEGIN_APPROVAL_INVALID",
                details={"decision_unit_id": decision_unit_id},
            )


def _is_governance_path(path: str) -> bool:
    normalized = path.rstrip("/")
    return normalized == ".ai/tasks" or normalized.startswith(".ai/tasks/")


def _require_git_baseline(repository_root: Path, task_id: str, task: Mapping[str, object]) -> None:
    context = collect_git_context(repository_root)
    baseline_paths = task.get("worktree_dirty_paths")
    expected_paths = set(baseline_paths) if isinstance(baseline_paths, list) else set()
    current_business_paths = {path for path in context.dirty_paths if not _is_governance_path(path)}
    if (
        context.repository_id != task.get("repository_id")
        or context.head != task.get("subject_commit")
        or context.branch != task.get("branch")
        or not current_business_paths.issubset(expected_paths)
    ):
        raise ContractError(
            "Current Git context exceeds the task baseline",
            code="BEGIN_GIT_CONTEXT_CHANGED",
            details={"task_id": task_id},
        )


def begin_task(
    repository_root: Path,
    task_id: str,
    *,
    actor: str,
    reason: str | None = None,
) -> TransitionResult:
    """Begin an implementation or a safe retry after validating prerequisites."""
    record = load_task_record(repository_root, task_id)
    state = record.task.get("current_state")
    if state == "READY_TO_IMPLEMENT":
        _require_ready_artifacts(repository_root, task_id, record)
        _require_git_baseline(repository_root, task_id, record.task)
        return transition_task_record(
            repository_root,
            task_id,
            target_state="IMPLEMENTING",
            event_type="implementation_started",
            actor=actor,
            payload={},
            satisfied_preconditions={"readiness_satisfied"},
        )
    if state == "FAILED":
        normalized_reason = (reason or "").strip()
        if not normalized_reason:
            raise ContractError(
                "Failed task retry requires a reason", code="BEGIN_RETRY_REASON_REQUIRED"
            )
        failure = next(
            (
                event
                for event in reversed(record.events)
                if event.get("event_type") == "verification_failed"
            ),
            None,
        )
        payload = failure.get("payload") if failure is not None else None
        markers = sorted(
            marker
            for marker in ESCALATING_FAILURE_MARKERS
            if isinstance(payload, Mapping) and payload.get(marker)
        )
        if markers:
            raise ContractError(
                "Failed task must escalate before retry",
                code="BEGIN_RETRY_REQUIRES_ESCALATION",
                details={"markers": markers},
            )
        _require_git_baseline(repository_root, task_id, record.task)
        return transition_task_record(
            repository_root,
            task_id,
            target_state="IMPLEMENTING",
            event_type="implementation_retried",
            actor=actor,
            payload={"reason": normalized_reason},
            satisfied_preconditions={"retry_reason_recorded"},
        )
    raise StateTransitionError(
        "Task cannot begin from its current state",
        code="STATE_TRANSITION_NOT_ALLOWED",
        details={"current_state": state},
    )


def _require_commit(repository_root: Path, commit: str) -> None:
    if COMMIT_PATTERN.fullmatch(commit) is None:
        raise ContractError("Merge commit is invalid", code="CLOSE_COMMIT_INVALID")
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=repository_root,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ContractError(
            "Could not verify merge commit", code="CLOSE_COMMIT_UNAVAILABLE"
        ) from error
    if result.returncode != 0:
        raise ContractError("Merge commit does not exist", code="CLOSE_COMMIT_UNKNOWN")


def close_task(
    repository_root: Path,
    task_id: str,
    *,
    result: str,
    merge_commit: str,
    actor: str,
) -> TransitionResult:
    """Record an externally completed merge without performing Git writes."""
    record = load_task_record(repository_root, task_id)
    if record.task.get("current_state") != "APPROVED_FOR_MERGE":
        raise StateTransitionError(
            "Task cannot close before merge approval",
            code="STATE_TRANSITION_NOT_ALLOWED",
            details={"current_state": record.task.get("current_state")},
        )
    if result != "merged":
        raise ContractError("Close result must be merged", code="CLOSE_RESULT_INVALID")
    context = collect_git_context(repository_root)
    if context.repository_id != record.task.get("repository_id"):
        raise ContractError(
            "Task belongs to a different repository", code="CLOSE_REPOSITORY_MISMATCH"
        )
    _require_commit(Path(context.repository_path), merge_commit)
    return transition_task_record(
        repository_root,
        task_id,
        target_state="MERGED",
        event_type="merge_recorded",
        actor=actor,
        payload={"result": result, "merge_commit": merge_commit},
        satisfied_preconditions={"merge_commit_verified"},
    )
