"""Explicit risk declarations for one unclassified draft decision unit."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from aiflow import task_service
from aiflow.contracts import require_valid_contract
from aiflow.decision_units import apply_risk_facts
from aiflow.errors import ContractError, StateTransitionError, StorageError
from aiflow.git_context import collect_git_context
from aiflow.state import create_record_event
from aiflow.storage import read_task_yaml, resolve_task_path


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite JSON number")
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON constant")


def _read_input(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
        # JSON escapes can decode to isolated surrogates that UTF-8 event logs cannot store.
        json.dumps(value, ensure_ascii=False).encode("utf-8")
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        raise ContractError(
            "Could not read risk facts as strict UTF-8 JSON", code="FACTS_INPUT_INVALID"
        ) from error
    if not isinstance(value, dict) or not value:
        raise ContractError("Risk facts must be a nonempty JSON object", code="FACTS_INPUT_INVALID")
    return value


def _require_draft(root: Path, task_id: str, task: Mapping[str, object]) -> None:
    if (
        task.get("task_id") != task_id
        or task.get("current_state") != "NEW"
        or "frozen_spec_sha256" in task
        or "spec_frozen_at" in task
        or any(
            resolve_task_path(root, task_id, name).exists()
            for name in ("classification.json", "classification_pending.json")
        )
    ):
        raise ContractError(
            "Risk facts require a NEW, unfrozen and unclassified draft", code="FACTS_DRAFT_REQUIRED"
        )
    context = collect_git_context(root)
    if (
        context.repository_id != task.get("repository_id")
        or context.branch != task.get("branch")
        or context.head != task.get("base_commit")
        or context.head != task.get("subject_commit")
    ):
        raise ContractError("Risk facts Git baseline does not match", code="FACTS_GIT_MISMATCH")


def record_risk_facts(
    repository_root: Path,
    task_id: str,
    *,
    decision_unit_id: str,
    input_path: Path,
    actor: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Preview, record, or precisely finish one explicit draft-facts update."""
    if not actor.strip():
        raise ContractError("Risk facts actor is required", code="FACTS_ACTOR_INVALID")
    actor = actor.strip()
    facts = _read_input(input_path)
    record = task_service._read_task_record(repository_root, task_id)
    _require_draft(repository_root, task_id, record.task)
    updated, before, after = apply_risk_facts(record.task, decision_unit_id, facts)
    changed = before != after
    staged_path = resolve_task_path(repository_root, task_id, "task.yaml.next")
    recovered = staged_path.exists()
    if recovered:
        if dry_run:
            raise StateTransitionError(
                "Preview cannot recover a pending task replacement", code="FACTS_RECOVERY_REQUIRED"
            )
        staged = read_task_yaml(repository_root, task_id, "task.yaml.next", contract_name="task")
        event = record.events[-1]
        payload = {"decision_unit_id": decision_unit_id, "before": before, "after": after}
        updated["updated_at"] = event["occurred_at"]
        if (
            not changed
            or event.get("event_type") != "risk_facts_recorded"
            or event.get("actor") != actor
            or event.get("from_state") != "NEW"
            or event.get("to_state") != "NEW"
            or event.get("payload") != payload
            or staged != updated
        ):
            raise StateTransitionError(
                "Pending replacement does not match this exact facts update",
                code="FACTS_RECOVERY_MISMATCH",
            )
        require_valid_contract("task", updated)
        # Only the final event may be unapplied; earlier fact declarations must already match.
        task_service._require_materialized_risk_facts(
            task_service.TaskRecord(task=record.task, events=record.events[:-1])
        )
        task_service._require_materialized_risk_facts(
            task_service.TaskRecord(task=updated, events=record.events)
        )
        current = task_service._read_task_record(repository_root, task_id)
        _require_draft(repository_root, task_id, current.task)
        if (
            current != record
            or read_task_yaml(repository_root, task_id, "task.yaml.next", contract_name="task")
            != staged
        ):
            raise StateTransitionError(
                "Task changed during facts recovery", code="FACTS_TASK_CHANGED"
            )
        try:
            task_service._replace_materialized_task(
                staged_path, resolve_task_path(repository_root, task_id, "task.yaml")
            )
        except OSError as error:
            raise StorageError(
                "Could not finish the pending risk facts replacement",
                code="STATE_MATERIALIZATION_FAILED",
            ) from error
    else:
        task_service._require_materialized_risk_facts(record)
        if changed and not dry_run:
            current = task_service.read_task_record_strict(repository_root, task_id)
            _require_draft(repository_root, task_id, current.task)
            if current != record:
                raise StateTransitionError(
                    "Task changed during facts apply", code="FACTS_TASK_CHANGED"
                )
            event = create_record_event(
                record.task,
                event_type="risk_facts_recorded",
                actor=actor,
                payload={"decision_unit_id": decision_unit_id, "before": before, "after": after},
                sequence=len(record.events) + 1,
            )
            updated["updated_at"] = event["occurred_at"]
            require_valid_contract("task", updated)
            task_service._persist_event_and_task(
                resolve_task_path(repository_root, task_id),
                updated,
                event,
                preserve_staged_on_append_failure=True,
            )
    return {
        "task_id": task_id,
        "decision_unit_id": decision_unit_id,
        "dry_run": dry_run,
        "changed": changed,
        "applied": changed and not dry_run,
        "recovered": recovered,
        "before": before,
        "after": after,
    }
