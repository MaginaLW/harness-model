"""Pure escalation and resolution preparation for governed task routing."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping, Sequence

from aiflow.decision_units import classification_input_digest, parse_decision_units
from aiflow.errors import ContractError
from aiflow.policy import load_policy_bundle
from aiflow.routing import ROUTE_ORDER
from aiflow.storage import read_task_json, resolve_task_path
from aiflow.task_service import (
    TaskRecord,
    TransitionResult,
    load_task_record,
    record_task_event,
    transition_task_record,
)

Route = Literal["AUTO", "ASK", "REVIEW", "BLOCK"]
ESCALATION_REASON_CODES = frozenset(
    {
        "scope_expanded",
        "repeated_verification_failures",
        "new_dependencies",
        "new_permissions",
        "network_required",
        "credentials_required",
        "directional_discovery",
        "verification_unavailable",
        "backup_invalid",
        "task_description_changed",
        "policy_changed",
        "spec_changed",
    }
)
SAME_ROUTE_INVALIDATION_CODES = frozenset({"policy_changed", "spec_changed"})
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class EscalationPreparation:
    """The target state and immutable escalation facts for one event payload."""

    target_state: str
    payload: Mapping[str, object]


def _invalid(message: str, code: str) -> ContractError:
    return ContractError(message, code=code)


def _nonempty(value: str, code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise _invalid("Escalation input is required", code)
    return normalized


def prepare_escalation(
    *,
    current_route: Route,
    target_route: Route,
    reason_code: str,
    impact: str,
    next_step: str,
    existing_work_disposition: str = "preserve_and_reassess",
) -> EscalationPreparation:
    """Validate a non-decreasing route change and produce its stable event payload."""
    if current_route not in ROUTE_ORDER or target_route not in ROUTE_ORDER:
        raise _invalid("Escalation route is invalid", "ESCALATION_ROUTE_INVALID")
    if target_route == "AUTO":
        raise _invalid("Escalation cannot target AUTO", "ESCALATION_ROUTE_INVALID")
    if reason_code not in ESCALATION_REASON_CODES:
        raise _invalid("Escalation reason code is invalid", "ESCALATION_REASON_INVALID")
    current_index = ROUTE_ORDER.index(current_route)
    target_index = ROUTE_ORDER.index(target_route)
    if target_index < current_index:
        raise _invalid("Escalation cannot lower the route", "ESCALATION_ROUTE_DOWNGRADE")
    if target_index == current_index and reason_code not in SAME_ROUTE_INVALIDATION_CODES:
        raise _invalid(
            "Same-route escalation requires a version invalidation", "ESCALATION_SAME_ROUTE_INVALID"
        )
    normalized_impact = _nonempty(impact, "ESCALATION_IMPACT_REQUIRED")
    normalized_next_step = _nonempty(next_step, "ESCALATION_NEXT_STEP_REQUIRED")
    disposition = _nonempty(existing_work_disposition, "ESCALATION_WORK_DISPOSITION_REQUIRED")
    target_state = "BLOCKED" if target_route == "BLOCK" else "ESCALATED"
    return EscalationPreparation(
        target_state=target_state,
        payload=MappingProxyType(
            {
                "old_route": current_route,
                "new_route": target_route,
                "reason_code": reason_code,
                "trigger_signal": reason_code,
                "impact": normalized_impact,
                "next_step": normalized_next_step,
                "existing_work_disposition": disposition,
            }
        ),
    )


def prepare_resolution(
    *,
    reason: str,
    evidence_refs: Sequence[str],
    previous_classification_input_sha256: str,
    previous_policy_sha256: str,
    manual_authorization: bool = False,
    authorized_by: str | None = None,
    authorized_classification_input_sha256: str | None = None,
    authorized_policy_sha256: str | None = None,
) -> Mapping[str, object]:
    """Build a version-bound resolution payload consumable by classification recovery."""
    normalized_reason = _nonempty(reason, "RESOLUTION_REASON_REQUIRED")
    references = tuple(
        sorted({_nonempty(item, "RESOLUTION_EVIDENCE_REQUIRED") for item in evidence_refs})
    )
    if not references:
        raise _invalid("Resolution evidence is required", "RESOLUTION_EVIDENCE_REQUIRED")
    if not _HASH_PATTERN.fullmatch(
        previous_classification_input_sha256
    ) or not _HASH_PATTERN.fullmatch(previous_policy_sha256):
        raise _invalid("Resolution version binding is invalid", "RESOLUTION_VERSION_INVALID")
    payload: dict[str, object] = {
        "reason": normalized_reason,
        "evidence_refs": list(references),
        "previous_classification_input_sha256": previous_classification_input_sha256,
        "previous_policy_sha256": previous_policy_sha256,
    }
    if manual_authorization:
        if (
            authorized_by is None
            or authorized_classification_input_sha256 is None
            or authorized_policy_sha256 is None
        ):
            raise _invalid(
                "Resolution authorization is incomplete", "RESOLUTION_AUTHORIZATION_REQUIRED"
            )
        actor = _nonempty(authorized_by, "RESOLUTION_AUTHORIZATION_REQUIRED")
        if not _HASH_PATTERN.fullmatch(
            authorized_classification_input_sha256
        ) or not _HASH_PATTERN.fullmatch(authorized_policy_sha256):
            raise _invalid(
                "Resolution authorization is invalid", "RESOLUTION_AUTHORIZATION_REQUIRED"
            )
        payload.update(
            {
                "manual_authorization": True,
                "authorized_by": actor,
                "authorized_classification_input_sha256": authorized_classification_input_sha256,
                "authorized_policy_sha256": authorized_policy_sha256,
            }
        )
    return MappingProxyType(payload)


def _classification(repository_root: Path, task_id: str) -> dict[str, Any]:
    value = read_task_json(
        repository_root, task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(value, dict) or value.get("effective_route") not in ROUTE_ORDER:
        raise _invalid("Current classification is invalid", "ESCALATION_CLASSIFICATION_INVALID")
    return value


def _transition_event(state: object, target_state: str) -> tuple[str, set[str]]:
    if state == "VERIFYING":
        if target_state == "BLOCKED":
            return "verification_blocked", {"blocking_condition_recorded"}
        return "verification_escalated", {"escalation_recorded"}
    if target_state == "BLOCKED":
        return "task_blocked", {"blocking_condition_recorded"}
    return "task_escalated", {"escalation_recorded"}


def escalate_task(
    repository_root: Path,
    task_id: str,
    *,
    target_route: Route,
    reason_code: str,
    impact: str,
    next_step: str,
    actor: str,
    existing_work_disposition: str = "preserve_and_reassess",
) -> TransitionResult:
    """Persist one structured escalation without changing Policy classifications."""
    if not actor.strip():
        raise _invalid("Escalation actor is required", "ESCALATION_ACTOR_REQUIRED")
    record = load_task_record(repository_root, task_id)
    classification = _classification(repository_root, task_id)
    current_route = classification["effective_route"]
    prepared = prepare_escalation(
        current_route=current_route,
        target_route=target_route,
        reason_code=reason_code,
        impact=impact,
        next_step=next_step,
        existing_work_disposition=existing_work_disposition,
    )
    entries = classification.get("classifications")
    payload = {
        **prepared.payload,
        "required_conditions": [reason_code],
        "previous_classification_input_sha256": classification.get("classification_input_sha256"),
        "previous_policy_sha256": classification.get("policy_sha256"),
        "previous_spec_sha256": record.task.get("frozen_spec_sha256"),
        "subject_commit": record.task.get("subject_commit"),
        "classification_summary": [
            {
                "decision_unit_id": entry.get("decision_unit_id"),
                "route": entry.get("route"),
                "verification_level": entry.get("verification_level"),
                "rule_id": entry.get("rule_id"),
            }
            for entry in entries
            if isinstance(entry, Mapping)
        ]
        if isinstance(entries, list)
        else [],
    }
    last = record.events[-1]
    if (
        record.task.get("current_state") == prepared.target_state
        and last.get("event_type")
        in {"task_escalated", "verification_escalated", "task_blocked", "verification_blocked"}
        and last.get("actor") == actor.strip()
        and last.get("payload") == payload
    ):
        return TransitionResult(task=record.task, event=dict(last))
    allowed_states = {
        "WAITING_FOR_ASK",
        "WAITING_FOR_SPEC_REVIEW",
        "READY_TO_IMPLEMENT",
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "FAILED",
        "WAITING_FOR_FINAL_REVIEW",
    }
    if record.task.get("current_state") not in allowed_states:
        raise _invalid("Task cannot escalate from its current state", "ESCALATION_STATE_INVALID")
    event_type, preconditions = _transition_event(
        record.task.get("current_state"), prepared.target_state
    )
    return transition_task_record(
        repository_root,
        task_id,
        target_state=prepared.target_state,
        event_type=event_type,
        actor=actor,
        payload=payload,
        satisfied_preconditions=preconditions,
    )


def _escalation_event(record: TaskRecord) -> Mapping[str, object]:
    for event in reversed(record.events):
        if event.get("event_type") in {
            "task_escalated",
            "verification_escalated",
            "task_blocked",
            "verification_blocked",
            "classification_blocked",
        }:
            return event
    raise _invalid("Resolution has no escalation to resolve", "RESOLUTION_ESCALATION_MISSING")


def record_resolution(
    repository_root: Path,
    task_id: str,
    *,
    condition: str,
    evidence_refs: Sequence[str],
    actor: str,
    reason: str,
    authorize_downgrade: bool = False,
) -> TransitionResult:
    """Record one evidence-backed resolution condition for later reclassification."""
    if not actor.strip():
        raise _invalid("Resolution actor is required", "RESOLUTION_ACTOR_REQUIRED")
    record = load_task_record(repository_root, task_id)
    if record.task.get("current_state") not in {"BLOCKED", "ESCALATED"}:
        raise _invalid("Task is not waiting for resolution", "RESOLUTION_STATE_INVALID")
    classification = _classification(repository_root, task_id)
    escalation = _escalation_event(record)
    escalation_payload = escalation.get("payload")
    if not isinstance(escalation_payload, Mapping):
        raise _invalid("Escalation payload is invalid", "RESOLUTION_ESCALATION_INVALID")
    required = escalation_payload.get("required_conditions")
    if isinstance(required, list) and required and condition not in required:
        raise _invalid("Resolution condition was not requested", "RESOLUTION_CONDITION_INVALID")
    normalized_refs = sorted(
        {_nonempty(ref, "RESOLUTION_EVIDENCE_REQUIRED") for ref in evidence_refs}
    )
    evidence: list[dict[str, str]] = []
    for reference in normalized_refs:
        path = resolve_task_path(repository_root, task_id, reference)
        try:
            content = path.read_bytes()
        except OSError as error:
            raise _invalid(
                "Resolution evidence cannot be read", "RESOLUTION_EVIDENCE_INVALID"
            ) from error
        evidence.append(
            {"ref": reference.replace("\\", "/"), "sha256": hashlib.sha256(content).hexdigest()}
        )
    bundle = load_policy_bundle(repository_root)
    anticipated_input = classification_input_digest(record.task, parse_decision_units(record.task))
    payload = dict(
        prepare_resolution(
            reason=reason,
            evidence_refs=normalized_refs,
            previous_classification_input_sha256=str(
                escalation_payload.get(
                    "previous_classification_input_sha256",
                    classification.get("classification_input_sha256"),
                )
            ),
            previous_policy_sha256=str(
                escalation_payload.get(
                    "previous_policy_sha256", classification.get("policy_sha256")
                )
            ),
            manual_authorization=authorize_downgrade,
            authorized_by=actor if authorize_downgrade else None,
            authorized_classification_input_sha256=anticipated_input
            if authorize_downgrade
            else None,
            authorized_policy_sha256=bundle.sha256 if authorize_downgrade else None,
        )
    )
    payload.update(
        {
            "condition": _nonempty(condition, "RESOLUTION_CONDITION_REQUIRED"),
            "evidence": evidence,
            "required_conditions": list(required) if isinstance(required, list) else [condition],
            "escalation_event_sequence": escalation.get("sequence"),
            "previous_spec_sha256": escalation_payload.get("previous_spec_sha256"),
            "subject_commit": escalation_payload.get("subject_commit"),
        }
    )
    last = record.events[-1]
    if last.get("event_type") == "resolution_recorded" and last.get("payload") == payload:
        return TransitionResult(task=record.task, event=dict(last))
    return record_task_event(
        repository_root,
        task_id,
        event_type="resolution_recorded",
        actor=actor,
        payload=payload,
    )
