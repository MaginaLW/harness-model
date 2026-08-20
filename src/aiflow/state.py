"""Deterministic AI Flow task state transitions and event replay."""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.errors import StateTransitionError

ALL_STATES = frozenset(
    {
        "NEW",
        "CLASSIFIED",
        "WAITING_FOR_ASK",
        "WAITING_FOR_SPEC_REVIEW",
        "READY_TO_IMPLEMENT",
        "BLOCKED",
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "FAILED",
        "ESCALATED",
        "WAITING_FOR_FINAL_REVIEW",
        "APPROVED_FOR_MERGE",
        "MERGED",
    }
)


@dataclass(frozen=True)
class TransitionRule:
    """One allowed edge and the prerequisite categories checked before it."""

    event_type: str
    preconditions: frozenset[str]


def _rule(event_type: str, *preconditions: str) -> TransitionRule:
    return TransitionRule(event_type, frozenset(preconditions))


TRANSITIONS: Mapping[tuple[str, str], TransitionRule] = MappingProxyType(
    {
        ("NEW", "CLASSIFIED"): _rule("classification_recorded", "classification_available"),
        ("CLASSIFIED", "WAITING_FOR_ASK"): _rule("ask_required", "classification_route_selected"),
        ("CLASSIFIED", "WAITING_FOR_SPEC_REVIEW"): _rule(
            "spec_review_required", "classification_route_selected"
        ),
        ("CLASSIFIED", "READY_TO_IMPLEMENT"): _rule(
            "implementation_ready", "classification_route_selected"
        ),
        ("CLASSIFIED", "BLOCKED"): _rule("classification_blocked", "blocking_condition_recorded"),
        ("WAITING_FOR_ASK", "READY_TO_IMPLEMENT"): _rule(
            "ask_answered", "answer_recorded", "spec_frozen"
        ),
        ("WAITING_FOR_ASK", "WAITING_FOR_SPEC_REVIEW"): _rule(
            "ask_answered", "answer_recorded", "spec_frozen"
        ),
        ("WAITING_FOR_ASK", "ESCALATED"): _rule("task_escalated", "escalation_recorded"),
        ("WAITING_FOR_ASK", "BLOCKED"): _rule("task_blocked", "blocking_condition_recorded"),
        ("WAITING_FOR_SPEC_REVIEW", "READY_TO_IMPLEMENT"): _rule(
            "spec_approved", "spec_frozen", "spec_approval_valid"
        ),
        ("WAITING_FOR_SPEC_REVIEW", "ESCALATED"): _rule("task_escalated", "escalation_recorded"),
        ("WAITING_FOR_SPEC_REVIEW", "BLOCKED"): _rule(
            "task_blocked", "blocking_condition_recorded"
        ),
        ("READY_TO_IMPLEMENT", "IMPLEMENTING"): _rule(
            "implementation_started", "readiness_satisfied"
        ),
        ("READY_TO_IMPLEMENT", "ESCALATED"): _rule("task_escalated", "escalation_recorded"),
        ("READY_TO_IMPLEMENT", "BLOCKED"): _rule("task_blocked", "blocking_condition_recorded"),
        ("FAILED", "IMPLEMENTING"): _rule("implementation_retried", "retry_reason_recorded"),
        ("FAILED", "ESCALATED"): _rule("task_escalated", "escalation_recorded"),
        ("FAILED", "BLOCKED"): _rule("task_blocked", "blocking_condition_recorded"),
        ("IMPLEMENTING", "VERIFYING"): _rule("verification_started", "implementation_complete"),
        ("IMPLEMENTING", "ESCALATED"): _rule("task_escalated", "escalation_recorded"),
        ("IMPLEMENTING", "BLOCKED"): _rule("task_blocked", "blocking_condition_recorded"),
        ("VERIFYING", "VERIFIED"): _rule("verification_passed", "verification_passed"),
        ("VERIFYING", "FAILED"): _rule("verification_failed", "verification_failed"),
        ("VERIFYING", "IMPLEMENTING"): _rule("verification_checked", "provisional_complete"),
        ("VERIFYING", "ESCALATED"): _rule("verification_escalated", "escalation_recorded"),
        ("VERIFYING", "BLOCKED"): _rule("verification_blocked", "blocking_condition_recorded"),
        ("VERIFIED", "APPROVED_FOR_MERGE"): _rule(
            "merge_approved_automatically", "final_review_not_required"
        ),
        ("VERIFIED", "VERIFYING"): _rule("verification_restarted", "reverification_requested"),
        ("VERIFIED", "WAITING_FOR_FINAL_REVIEW"): _rule(
            "final_review_required", "final_review_required"
        ),
        ("VERIFIED", "ESCALATED"): _rule("task_escalated", "escalation_recorded"),
        ("VERIFIED", "BLOCKED"): _rule("task_blocked", "blocking_condition_recorded"),
        ("WAITING_FOR_FINAL_REVIEW", "ESCALATED"): _rule("task_escalated", "escalation_recorded"),
        ("WAITING_FOR_FINAL_REVIEW", "BLOCKED"): _rule(
            "task_blocked", "blocking_condition_recorded"
        ),
        ("WAITING_FOR_FINAL_REVIEW", "VERIFYING"): _rule(
            "verification_restarted", "reverification_requested"
        ),
        ("WAITING_FOR_FINAL_REVIEW", "APPROVED_FOR_MERGE"): _rule(
            "code_approved", "code_approval_valid"
        ),
        ("APPROVED_FOR_MERGE", "VERIFYING"): _rule(
            "verification_restarted", "reverification_requested"
        ),
        ("APPROVED_FOR_MERGE", "ESCALATED"): _rule("task_escalated", "escalation_recorded"),
        ("APPROVED_FOR_MERGE", "BLOCKED"): _rule("task_blocked", "blocking_condition_recorded"),
        ("APPROVED_FOR_MERGE", "MERGED"): _rule("merge_recorded", "merge_commit_verified"),
        ("ESCALATED", "CLASSIFIED"): _rule("escalation_resolved", "resolution_recorded"),
        ("BLOCKED", "CLASSIFIED"): _rule("block_resolved", "resolution_recorded"),
    }
)

NON_STATE_EVENTS = frozenset(
    {
        "task_created",
        "spec_frozen",
        "ask_answer_recorded",
        "approval_recorded",
        "evidence_generated",
        "subject_commit_synchronized",
        "state_recovered",
        "resolution_recorded",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _task_fields(task: Mapping[str, object]) -> tuple[str, str]:
    task_id = task.get("task_id")
    state = task.get("current_state")
    if not isinstance(task_id, str) or not isinstance(state, str) or state not in ALL_STATES:
        raise StateTransitionError(
            "Task identity or current state is invalid",
            code="STATE_TASK_INVALID",
            details={},
        )
    return task_id, state


def _event(
    *,
    task_id: str,
    sequence: int,
    from_state: str,
    to_state: str,
    event_type: str,
    actor: str,
    payload: Mapping[str, object],
    occurred_at: str | None,
) -> dict[str, Any]:
    if sequence < 1 or not actor.strip():
        raise StateTransitionError(
            "Event sequence and actor must be valid",
            code="STATE_EVENT_INVALID",
            details={},
        )
    event = {
        "schema_version": "1.0",
        "task_id": task_id,
        "sequence": sequence,
        "from_state": from_state,
        "to_state": to_state,
        "event_type": event_type,
        "actor": actor.strip(),
        "occurred_at": occurred_at or _utc_now(),
        "payload": dict(payload),
    }
    require_valid_contract("event", event)
    return event


def create_transition_event(
    task: Mapping[str, object],
    *,
    target_state: str,
    event_type: str,
    actor: str,
    payload: Mapping[str, object],
    sequence: int,
    satisfied_preconditions: Set[str],
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """Create an event for one allowed state-changing edge."""
    task_id, current_state = _task_fields(task)
    rule = TRANSITIONS.get((current_state, target_state))
    if target_state == current_state or rule is None or rule.event_type != event_type:
        raise StateTransitionError(
            "Requested state transition is not allowed",
            code="STATE_TRANSITION_NOT_ALLOWED",
            details={"from_state": current_state, "to_state": target_state},
        )
    missing = sorted(rule.preconditions - set(satisfied_preconditions))
    if missing:
        raise StateTransitionError(
            "State transition prerequisites are not satisfied",
            code="STATE_PRECONDITION_MISSING",
            details={"missing": missing},
        )
    return _event(
        task_id=task_id,
        sequence=sequence,
        from_state=current_state,
        to_state=target_state,
        event_type=event_type,
        actor=actor,
        payload=payload,
        occurred_at=occurred_at,
    )


def create_record_event(
    task: Mapping[str, object],
    *,
    event_type: str,
    actor: str,
    payload: Mapping[str, object],
    sequence: int,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """Create a closed, explicitly non-state event."""
    task_id, current_state = _task_fields(task)
    if event_type not in NON_STATE_EVENTS:
        raise StateTransitionError(
            "Requested non-state event is not allowed",
            code="STATE_EVENT_NOT_ALLOWED",
            details={"event_type": event_type},
        )
    return _event(
        task_id=task_id,
        sequence=sequence,
        from_state=current_state,
        to_state=current_state,
        event_type=event_type,
        actor=actor,
        payload=payload,
        occurred_at=occurred_at,
    )


def _validate_replayed_event(event: Mapping[str, object]) -> None:
    from_state = event.get("from_state")
    to_state = event.get("to_state")
    event_type = event.get("event_type")
    if not all(isinstance(value, str) for value in (from_state, to_state, event_type)):
        raise StateTransitionError(
            "Event state fields are invalid", code="STATE_EVENT_INVALID", details={}
        )
    if from_state == to_state:
        if event_type not in NON_STATE_EVENTS:
            raise StateTransitionError(
                "Event contains an unknown self-loop",
                code="STATE_EVENT_NOT_ALLOWED",
                details={"event_type": event_type},
            )
        return
    rule = TRANSITIONS.get((str(from_state), str(to_state)))
    if rule is None or rule.event_type != event_type:
        raise StateTransitionError(
            "Event contains an unknown state transition",
            code="STATE_TRANSITION_NOT_ALLOWED",
            details={"from_state": from_state, "to_state": to_state},
        )


def replay_events(events: Sequence[Mapping[str, object]], *, task_id: str | None = None) -> str:
    """Validate and replay an append-only event sequence to its terminal state."""
    if not events:
        raise StateTransitionError(
            "Task event log is empty", code="STATE_EVENT_SEQUENCE_INVALID", details={}
        )
    previous_state: str | None = None
    expected_task_id = task_id
    for expected_sequence, event in enumerate(events, start=1):
        require_valid_contract("event", event)
        event_task_id = event.get("task_id")
        if expected_task_id is None and isinstance(event_task_id, str):
            expected_task_id = event_task_id
        if event_task_id != expected_task_id:
            raise StateTransitionError(
                "Event belongs to a different task",
                code="STATE_EVENT_TASK_MISMATCH",
                details={"sequence": expected_sequence},
            )
        if event.get("sequence") != expected_sequence:
            raise StateTransitionError(
                "Event sequence is missing or duplicated",
                code="STATE_EVENT_SEQUENCE_INVALID",
                details={"expected": expected_sequence},
            )
        from_state = event.get("from_state")
        to_state = event.get("to_state")
        if expected_sequence == 1 and event.get("event_type") != "task_created":
            raise StateTransitionError(
                "First event must create the task",
                code="STATE_EVENT_SEQUENCE_INVALID",
                details={},
            )
        if previous_state is not None and from_state != previous_state:
            raise StateTransitionError(
                "Event from_state does not match the previous to_state",
                code="STATE_EVENT_CHAIN_INVALID",
                details={"sequence": expected_sequence},
            )
        _validate_replayed_event(event)
        if not isinstance(to_state, str):
            raise StateTransitionError(
                "Event to_state is invalid", code="STATE_EVENT_INVALID", details={}
            )
        previous_state = to_state
    if previous_state is None:
        raise StateTransitionError(
            "Task event log has no terminal state",
            code="STATE_EVENT_SEQUENCE_INVALID",
            details={},
        )
    return previous_state


def assert_task_matches_events(
    task: Mapping[str, object], events: Sequence[Mapping[str, object]]
) -> None:
    """Reject a materialized task whose state differs from replay."""
    task_id, current_state = _task_fields(task)
    terminal_state = replay_events(events, task_id=task_id)
    if current_state != terminal_state:
        raise StateTransitionError(
            "Materialized task state does not match event replay",
            code="STATE_MATERIALIZATION_MISMATCH",
            details={"materialized": current_state, "replayed": terminal_state},
        )
