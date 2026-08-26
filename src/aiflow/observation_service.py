"""Bounded task-local persistence for deterministic observation decisions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from aiflow.decision_units import parse_decision_units
from aiflow.errors import ContractError
from aiflow.escalation import escalate_task
from aiflow.freshness import current_classification_input_digest
from aiflow.git_context import collect_git_context, commits_are_ancestral
from aiflow.observation import (
    Observation,
    ObservationSource,
    parse_observation,
    serialize_observation,
)
from aiflow.observation_decision import (
    DecisionDisposition,
    DecisionRoute,
    ObservationDecision,
    VerificationLevel,
    decide_observation,
    observation_digest,
    parse_observation_decision,
    serialize_observation_decision,
)
from aiflow.policy import load_policy_bundle
from aiflow.storage import read_task_json
from aiflow.task_service import TransitionResult, load_task_record, record_task_event


@dataclass(frozen=True)
class ObservationApplication:
    """One fail-closed observation application outcome."""

    decision: ObservationDecision
    audit_event: Mapping[str, object] | None
    escalation_event: Mapping[str, object] | None


def _invalid(code: str) -> ContractError:
    return ContractError("Observation application is invalid", code=code)


def _decision_digest(decision: ObservationDecision) -> str:
    canonical = json.dumps(
        serialize_observation_decision(decision),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _classification(repository_root: Path, task_id: str) -> Mapping[str, object]:
    value = read_task_json(
        repository_root, task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(value, Mapping):
        raise _invalid("OBSERVATION_CLASSIFICATION_INVALID")
    return value


def _current_facts(
    repository_root: Path, task_id: str, observation: Observation
) -> tuple[dict[str, object], Mapping[str, object], DecisionRoute, VerificationLevel]:
    if not isinstance(observation, Observation):
        raise _invalid("OBSERVATION_INVALID")
    if observation.source is ObservationSource.CI:
        raise _invalid("OBSERVATION_CI_PERSISTENCE_FORBIDDEN")
    record = load_task_record(repository_root, task_id)
    task = record.task
    if task.get("current_state") not in {
        "WAITING_FOR_ASK",
        "WAITING_FOR_SPEC_REVIEW",
        "READY_TO_IMPLEMENT",
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "FAILED",
        "WAITING_FOR_FINAL_REVIEW",
        "APPROVED_FOR_MERGE",
        "ESCALATED",
        "BLOCKED",
    }:
        raise _invalid("OBSERVATION_STATE_INVALID")
    if (
        task.get("task_id") != task_id
        or observation.task_id != task_id
        or observation.base_commit != task.get("base_commit")
        or observation.subject_commit != task.get("subject_commit")
    ):
        raise _invalid("OBSERVATION_BINDING_STALE")
    context = collect_git_context(repository_root)
    base = task.get("base_commit")
    subject = task.get("subject_commit")
    if (
        context.repository_id != task.get("repository_id")
        or context.branch != task.get("branch")
        or context.head != subject
        or not isinstance(base, str)
        or not isinstance(subject, str)
        or not commits_are_ancestral(
            repository_root, base_commit=base, subject_commit=subject, head_commit=context.head
        )
    ):
        raise _invalid("OBSERVATION_GIT_BINDING_STALE")
    bundle = load_policy_bundle(repository_root)
    if observation.policy_sha256 != bundle.sha256:
        raise _invalid("OBSERVATION_POLICY_STALE")
    classification = _classification(repository_root, task_id)
    units = parse_decision_units(task)
    current_input, subject_synchronized = current_classification_input_digest(
        task, units, classification, record.events
    )
    if (
        classification.get("task_id") != task_id
        or classification.get("base_commit") != base
        or (classification.get("subject_commit") != subject and not subject_synchronized)
        or classification.get("policy_sha256") != bundle.sha256
        or classification.get("classification_input_sha256") != current_input
    ):
        raise _invalid("OBSERVATION_CLASSIFICATION_STALE")
    try:
        route = DecisionRoute(str(classification["effective_route"]))
        level = VerificationLevel(str(classification["effective_verification_level"]))
    except (KeyError, ValueError) as error:
        raise _invalid("OBSERVATION_CLASSIFICATION_INVALID") from error
    return task, classification, route, level


def _audit_payload(observation: Observation, decision: ObservationDecision) -> dict[str, object]:
    return {
        "observation": serialize_observation(observation),
        "observation_sha256": observation_digest(observation),
        "decision": serialize_observation_decision(decision),
        "decision_sha256": _decision_digest(decision),
    }


def _existing_audit(
    record_events: tuple[Mapping[str, object], ...],
    *,
    expected_event_type: str,
    expected_payload: Mapping[str, object],
) -> Mapping[str, object] | None:
    expected_observation_sha = expected_payload["observation_sha256"]
    expected_observation = expected_payload["observation"]
    for event in record_events:
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type not in {"observation_recorded", "observation_refused"}:
            if isinstance(payload, Mapping) and (
                payload.get("observation_sha256") == expected_observation_sha
                or payload.get("observation") == expected_observation
            ):
                raise _invalid("OBSERVATION_AUDIT_CONFLICT")
            continue
        if not isinstance(payload, Mapping):
            raise _invalid("OBSERVATION_AUDIT_CONFLICT")
        try:
            persisted_observation = parse_observation(payload.get("observation"))
            persisted_decision = parse_observation_decision(payload.get("decision"))
        except ContractError as error:
            raise _invalid("OBSERVATION_AUDIT_CONFLICT") from error
        persisted_observation_sha = observation_digest(persisted_observation)
        if (
            payload.get("observation_sha256") != persisted_observation_sha
            or persisted_decision.observation_sha256 != persisted_observation_sha
            or payload.get("decision_sha256") != _decision_digest(persisted_decision)
        ):
            raise _invalid("OBSERVATION_AUDIT_CONFLICT")
        if persisted_observation_sha != expected_observation_sha:
            continue
        if (
            event_type != expected_event_type
            or payload != expected_payload
            or payload.get("decision_sha256") != expected_payload["decision_sha256"]
        ):
            raise _invalid("OBSERVATION_AUDIT_CONFLICT")
        return event
    return None


def apply_observation(
    repository_root: Path, task_id: str, observation: Observation, *, actor: str
) -> ObservationApplication:
    """Validate, decide, audit, and if necessary delegate a monotonic escalation."""
    if not actor.strip():
        raise _invalid("OBSERVATION_ACTOR_INVALID")
    _task, _classification_value, route, level = _current_facts(
        repository_root, task_id, observation
    )
    decision = decide_observation(observation, route, level)
    payload = _audit_payload(observation, decision)
    record = load_task_record(repository_root, task_id)

    if decision.disposition is DecisionDisposition.REFUSE:
        existing = _existing_audit(
            record.events,
            expected_event_type="observation_refused",
            expected_payload=payload,
        )
        if existing is not None:
            return ObservationApplication(decision, existing, None)
        result = record_task_event(
            repository_root,
            task_id,
            event_type="observation_refused",
            actor=actor,
            payload=payload,
        )
        return ObservationApplication(decision, result.event, None)
    if decision.disposition is DecisionDisposition.RECORD:
        existing = _existing_audit(
            record.events,
            expected_event_type="observation_recorded",
            expected_payload=payload,
        )
        if existing is not None:
            return ObservationApplication(decision, existing, None)
        result = record_task_event(
            repository_root,
            task_id,
            event_type="observation_recorded",
            actor=actor,
            payload=payload,
        )
        return ObservationApplication(decision, result.event, None)
    if decision.disposition is not DecisionDisposition.ESCALATE or decision.target_route is None:
        raise _invalid("OBSERVATION_DECISION_INVALID")

    existing = _existing_audit(
        record.events,
        expected_event_type="observation_recorded",
        expected_payload=payload,
    )
    audit_event: Mapping[str, object] | None = existing
    if audit_event is None:
        audit_event = record_task_event(
            repository_root,
            task_id,
            event_type="observation_recorded",
            actor=actor,
            payload=payload,
        ).event
    refreshed = load_task_record(repository_root, task_id)
    if refreshed.task.get("current_state") in {"ESCALATED", "BLOCKED"}:
        return ObservationApplication(decision, audit_event, None)
    escalation: TransitionResult = escalate_task(
        repository_root,
        task_id,
        target_route=decision.target_route.value,
        reason_code=decision.reason_code.value,
        impact="observation:" + observation_digest(observation),
        next_step="recover:"
        + ",".join(condition.value for condition in decision.required_conditions),
        actor=actor,
        existing_work_disposition="preserve_and_reassess",
    )
    return ObservationApplication(decision, audit_event, escalation.event)
