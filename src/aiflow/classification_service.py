"""Classification orchestration: facts in, durable routing evidence out."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import classification_input_digest, parse_decision_units
from aiflow.errors import AiflowError, ContractError, StateTransitionError
from aiflow.git_context import collect_git_context
from aiflow.policy import load_policy_bundle
from aiflow.routing import ROUTE_ORDER, route_task
from aiflow.scope import matches_scope, normalize_repository_path
from aiflow.storage import atomic_write_json, read_task_json, resolve_task_path
from aiflow.task_service import TaskRecord, read_task_record_strict, transition_task_record
from aiflow.verification_level import verification_for_task


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _stable_input(task: Mapping[str, object], units: tuple[dict[str, Any], ...]) -> str:
    """Compatibility wrapper for the shared stable classification digest."""
    return classification_input_digest(task, units)


def _scope_allowed(impact: object, allowed: object) -> bool:
    if not isinstance(impact, list) or not isinstance(allowed, list):
        return False
    if not all(isinstance(item, str) for item in impact + allowed):
        return False
    try:
        paths = [normalize_repository_path(item) for item in impact]
        patterns = [normalize_repository_path(item) for item in allowed]
        return all(any(matches_scope(path, pattern) for pattern in patterns) for path in paths)
    except ContractError:
        return False


def _require_baseline(root: Path, task: Mapping[str, object]) -> None:
    context = collect_git_context(root)
    if (
        context.repository_id != task.get("repository_id")
        or context.branch != task.get("branch")
        or context.head != task.get("base_commit")
        or context.head != task.get("subject_commit")
    ):
        raise ContractError(
            "Classification Git baseline does not match", code="CLASSIFICATION_GIT_MISMATCH"
        )


def _target(
    route: str, blocked: bool, entries: Sequence[Mapping[str, object]]
) -> tuple[str, str, set[str]]:
    if blocked or route == "BLOCK":
        return "BLOCKED", "classification_blocked", {"blocking_condition_recorded"}
    if any(entry.get("route") == "ASK" for entry in entries):
        return "WAITING_FOR_ASK", "ask_required", {"classification_route_selected"}
    if route == "REVIEW":
        return "WAITING_FOR_SPEC_REVIEW", "spec_review_required", {"classification_route_selected"}
    return "READY_TO_IMPLEMENT", "implementation_ready", {"classification_route_selected"}


def _previous_identity(root: Path, task_id: str) -> Mapping[str, object] | None:
    path = resolve_task_path(root, task_id, "classification.json")
    if not path.is_file():
        return None
    value = read_task_json(root, task_id, "classification.json", contract_name="classification")
    return value if isinstance(value, Mapping) else None


def _resume_classification(
    repository_root: Path,
    task_id: str,
    marker: Mapping[str, object],
) -> dict[str, Any]:
    """Resume a version-checked BLOCK/ESCALATED classification transaction."""
    classification = marker.get("classification")
    if not isinstance(classification, dict):
        raise StateTransitionError(
            "Classification recovery marker is invalid", code="CLASSIFICATION_RECOVERY_INVALID"
        )
    require_valid_contract("classification", classification)
    record = read_task_record_strict(repository_root, task_id)
    resolution_sequence = marker.get("resolution_event_sequence")
    resolution_payload = marker.get("resolution_payload")
    if (
        not isinstance(resolution_sequence, int)
        or resolution_sequence < 1
        or resolution_sequence > len(record.events)
        or record.events[resolution_sequence - 1].get("event_type") != "resolution_recorded"
        or record.events[resolution_sequence - 1].get("payload") != resolution_payload
        or not isinstance(resolution_payload, Mapping)
        or resolution_payload.get("previous_classification_input_sha256")
        != marker.get("previous_classification_input_sha256")
        or resolution_payload.get("previous_policy_sha256") != marker.get("previous_policy_sha256")
        or not _resolution_evidence_current(repository_root, task_id, resolution_payload)
    ):
        raise StateTransitionError(
            "Classification recovery resolution is stale",
            code="CLASSIFICATION_RESOLUTION_REQUIRED",
        )
    target_state = marker.get("target_state")
    if (
        record.task.get("current_state") == target_state
        and record.events
        and record.events[-1].get("event_type") == marker.get("target_event_type")
    ):
        resolve_task_path(repository_root, task_id, "classification_pending.json").unlink(
            missing_ok=True
        )
        return dict(classification)
    units = parse_decision_units(record.task)
    bundle = load_policy_bundle(repository_root)
    if _stable_input(record.task, units) != classification.get(
        "classification_input_sha256"
    ) or bundle.sha256 != classification.get("policy_sha256"):
        raise StateTransitionError(
            "Classification recovery identity changed",
            code="CLASSIFICATION_RECOVERY_IDENTITY_MISMATCH",
        )
    atomic_write_json(
        resolve_task_path(repository_root, task_id, "classification.json"), classification
    )
    source_state = marker.get("source_state")
    actor = marker.get("actor")
    evidence = marker.get("evidence")
    if not isinstance(actor, str) or not isinstance(evidence, Mapping):
        raise StateTransitionError(
            "Classification recovery marker is invalid", code="CLASSIFICATION_RECOVERY_INVALID"
        )
    if record.task.get("current_state") == source_state:
        transition_task_record(
            repository_root,
            task_id,
            target_state="CLASSIFIED",
            event_type=str(marker.get("resolution_event_type")),
            actor=actor,
            payload={
                **evidence,
                "resolution_event_sequence": marker.get("resolution_event_sequence"),
            },
            satisfied_preconditions={"resolution_recorded"},
        )
        record = read_task_record_strict(repository_root, task_id)
    if record.task.get("current_state") == "CLASSIFIED":
        preconditions = marker.get("target_preconditions")
        payload = marker.get("target_payload")
        if not isinstance(preconditions, list) or not isinstance(payload, Mapping):
            raise StateTransitionError(
                "Classification recovery marker is invalid",
                code="CLASSIFICATION_RECOVERY_INVALID",
            )
        transition_task_record(
            repository_root,
            task_id,
            target_state=str(target_state),
            event_type=str(marker.get("target_event_type")),
            actor=actor,
            payload=payload,
            satisfied_preconditions=set(preconditions),
        )
        record = read_task_record_strict(repository_root, task_id)
    if record.task.get("current_state") != target_state:
        raise StateTransitionError(
            "Classification recovery state is invalid", code="CLASSIFICATION_RECOVERY_INVALID"
        )
    try:
        resolve_task_path(repository_root, task_id, "classification_pending.json").unlink()
    except OSError as error:
        raise StateTransitionError(
            "Classification recovery marker remains", code="CLASSIFICATION_RECOVERY_INVALID"
        ) from error
    return dict(classification)


def _resolution_allowed(
    record: TaskRecord,
    *,
    repository_root: Path,
    task_id: str,
    authorization_required: bool,
    previous: Mapping[str, object] | None,
    input_sha256: str,
    policy_sha256: str,
    effective_route: str,
) -> bool:
    if record.task.get("current_state") not in {"BLOCKED", "ESCALATED"}:
        return True
    if not record.events or record.events[-1].get("event_type") != "resolution_recorded":
        return False
    payload = record.events[-1].get("payload")
    if not isinstance(payload, Mapping):
        return False
    if not isinstance(payload.get("reason"), str) or not payload["reason"].strip():
        return False
    refs = payload.get("evidence_refs")
    if (
        not isinstance(refs, list)
        or not refs
        or not all(isinstance(item, str) and item for item in refs)
    ):
        return False
    if previous is None or (
        payload.get("previous_classification_input_sha256")
        != previous.get("classification_input_sha256")
        or payload.get("previous_policy_sha256") != previous.get("policy_sha256")
    ):
        return False
    resolution_events = []
    escalation_event: Mapping[str, object] | None = None
    for event in reversed(record.events):
        if event.get("event_type") == "resolution_recorded":
            resolution_events.append(event)
            continue
        escalation_event = event
        break
    escalation_payload = escalation_event.get("payload") if escalation_event else None
    if isinstance(escalation_payload, Mapping):
        requested_route = escalation_payload.get("new_route")
        if (
            isinstance(requested_route, str)
            and requested_route in ROUTE_ORDER
            and ROUTE_ORDER.index(effective_route) < ROUTE_ORDER.index(requested_route)
        ):
            authorization_required = True
        required = escalation_payload.get("required_conditions")
        if isinstance(required, list) and required:
            resolved = {
                item_payload.get("condition")
                for event in resolution_events
                if isinstance((item_payload := event.get("payload")), Mapping)
                and item_payload.get("previous_classification_input_sha256")
                == previous.get("classification_input_sha256")
                and item_payload.get("previous_policy_sha256") == previous.get("policy_sha256")
            }
            if not set(required).issubset(resolved):
                return False
    if not _resolution_evidence_current(repository_root, task_id, payload):
        return False
    if authorization_required and (
        payload.get("manual_authorization") is not True
        or not isinstance(payload.get("authorized_by"), str)
        or not payload["authorized_by"].strip()
        or payload.get("authorized_classification_input_sha256") != input_sha256
        or payload.get("authorized_policy_sha256") != policy_sha256
    ):
        return False
    return True


def _resolution_evidence_current(
    repository_root: Path, task_id: str, payload: Mapping[str, object]
) -> bool:
    """Validate structured resolution evidence when present; retain legacy refs compatibility."""
    evidence = payload.get("evidence")
    if evidence is None:
        return True
    if not isinstance(evidence, list) or not evidence:
        return False
    for item in evidence:
        if not isinstance(item, Mapping):
            return False
        reference, digest = item.get("ref"), item.get("sha256")
        if not isinstance(reference, str) or not isinstance(digest, str):
            return False
        try:
            current = resolve_task_path(repository_root, task_id, reference).read_bytes()
        except (OSError, AiflowError):
            return False
        if hashlib.sha256(current).hexdigest() != digest:
            return False
    return True


def _is_downgrade(
    previous: Mapping[str, object] | None,
    entries: list[dict[str, object]],
    *,
    effective_route: str,
    effective_level: str,
) -> bool:
    if previous is None:
        return False
    old_entries = previous.get("classifications")
    if not isinstance(old_entries, list):
        return True
    old_by_id = {
        item.get("decision_unit_id"): item for item in old_entries if isinstance(item, Mapping)
    }
    new_ids = {entry["decision_unit_id"] for entry in entries}
    if any(identifier not in new_ids for identifier in old_by_id):
        return True
    old_route = previous.get("effective_route")
    old_level = previous.get("effective_verification_level")
    old_raw_routes = {item.get("route") for item in old_entries if isinstance(item, Mapping)}
    top_route_downgrade = (
        isinstance(old_route, str)
        and ROUTE_ORDER.index(effective_route) < ROUTE_ORDER.index(old_route)
        # A verification-only BLOCK preserves the raw route as the comparison subject.
        and not (old_route == "BLOCK" and "BLOCK" not in old_raw_routes)
    )
    if top_route_downgrade or (effective_level == "V0" and old_level == "V1"):
        return True
    for entry in entries:
        old = old_by_id.get(entry["decision_unit_id"])
        if not isinstance(old, Mapping):
            continue
        if (
            ROUTE_ORDER.index(str(entry["route"])) < ROUTE_ORDER.index(str(old.get("route")))
            or entry["verification_level"] == "V0"
            and old.get("verification_level") == "V1"
        ):
            return True
    return False


def _change_reason(
    previous: Mapping[str, object] | None,
    entries: list[dict[str, object]],
    *,
    route: str,
    level: str,
) -> str:
    if previous is None:
        return "unchanged"
    if _is_downgrade(previous, entries, effective_route=route, effective_level=level):
        return "downgraded"
    old_classifications = previous.get("classifications")
    if not isinstance(old_classifications, list):
        return "unchanged"
    old_routes = {
        item.get("decision_unit_id"): item.get("route")
        for item in old_classifications
        if isinstance(item, Mapping)
    }
    old_entries = {
        item.get("decision_unit_id"): item
        for item in old_classifications
        if isinstance(item, Mapping)
    }
    old_effective_route = previous.get("effective_route")
    if (
        isinstance(old_effective_route, str)
        and ROUTE_ORDER.index(route) > ROUTE_ORDER.index(old_effective_route)
    ) or (level == "V1" and previous.get("effective_verification_level") == "V0"):
        return "upgraded"
    if any(
        old_routes.get(entry["decision_unit_id"]) in ROUTE_ORDER
        and ROUTE_ORDER.index(str(entry["route"]))
        > ROUTE_ORDER.index(str(old_routes[entry["decision_unit_id"]]))
        for entry in entries
    ):
        return "upgraded"
    if any(
        entry["verification_level"] == "V1"
        and isinstance(old_entries.get(entry["decision_unit_id"]), Mapping)
        and old_entries[entry["decision_unit_id"]].get("verification_level") == "V0"
        for entry in entries
    ):
        return "upgraded"
    return "unchanged"


def _entries(
    task_routes: object, task_verification: object, *, version: str, digest: str, at: str
) -> list[dict[str, object]]:
    routes = getattr(task_routes, "unit_decisions")
    verifications = {
        item.decision_unit_id: item for item in getattr(task_verification, "unit_decisions")
    }
    result: list[dict[str, object]] = []
    for route in routes:
        verification = verifications[route.decision_unit_id]
        rules = [hit.to_dict() for hit in route.matched_rules]
        result.append(
            {
                "decision_unit_id": route.decision_unit_id,
                "route": route.effective_route,
                "verification_level": verification.level,
                "rule_id": route.matched_rule_ids[0],
                "explanation": route.explanations[0],
                "matched_rules": rules,
                "explanations": list(route.explanations),
                "verification_rule_ids": list(verification.rule_ids),
                "verification_explanations": list(verification.explanations),
                "verification_blocking_reasons": list(verification.blocking_reasons),
                "policy_version": version,
                "policy_sha256": digest,
                "classified_at": at,
            }
        )
    return result


def classify_task(repository_root: Path, task_id: str, *, actor: str) -> dict[str, Any]:
    """Strictly classify a task, writing evidence before any state transition."""
    if not actor.strip():
        raise ContractError("Classification actor is required", code="CLASSIFICATION_ACTOR_INVALID")
    pending_path = resolve_task_path(repository_root, task_id, "classification_pending.json")
    if pending_path.is_file():
        pending = read_task_json(repository_root, task_id, "classification_pending.json")
        if not isinstance(pending, Mapping):
            raise StateTransitionError(
                "Classification recovery marker is invalid",
                code="CLASSIFICATION_RECOVERY_INVALID",
            )
        return _resume_classification(repository_root, task_id, pending)
    record = read_task_record_strict(repository_root, task_id)
    state = record.task.get("current_state")
    _require_baseline(repository_root, record.task)
    units = parse_decision_units(record.task)
    if not _scope_allowed(
        [path for unit in units for path in unit["impact_scope"]], record.task.get("allowed_scope")
    ):
        raise ContractError(
            "Decision-unit impact exceeds allowed scope", code="CLASSIFICATION_SCOPE_EXCEEDED"
        )
    bundle = load_policy_bundle(repository_root)
    stable_hash = _stable_input(record.task, units)
    previous = _previous_identity(repository_root, task_id)
    identity = (
        stable_hash,
        bundle.sha256,
        record.task.get("base_commit"),
        record.task.get("subject_commit"),
    )
    if (
        previous is not None
        and identity
        == (
            previous.get("classification_input_sha256"),
            previous.get("policy_sha256"),
            previous.get("base_commit"),
            previous.get("subject_commit"),
        )
        and state in {"BLOCKED", "WAITING_FOR_ASK", "WAITING_FOR_SPEC_REVIEW", "READY_TO_IMPLEMENT"}
        and not (
            state == "BLOCKED"
            and (
                not record.events or record.events[-1].get("event_type") != "classification_blocked"
            )
        )
    ):
        return dict(previous)
    if state == "CLASSIFIED" and (
        previous is None
        or identity
        != (
            previous.get("classification_input_sha256"),
            previous.get("policy_sha256"),
            previous.get("base_commit"),
            previous.get("subject_commit"),
        )
    ):
        raise StateTransitionError(
            "CLASSIFIED recovery requires the recorded classification identity",
            code="CLASSIFICATION_RECOVERY_IDENTITY_MISMATCH",
        )
    if state not in {"NEW", "BLOCKED", "ESCALATED", "CLASSIFIED"}:
        raise StateTransitionError(
            "Task cannot be classified in its current state", code="CLASSIFICATION_STATE_INVALID"
        )
    routes = route_task({**record.task, "decision_units": list(units)}, bundle)
    verification = verification_for_task({**record.task, "decision_units": list(units)}, bundle)
    blocked = bool(verification.blocking_reasons)
    route = "BLOCK" if blocked else routes.effective_route
    at = _now()
    entries = _entries(
        routes, verification, version=bundle.policy_version, digest=bundle.sha256, at=at
    )
    downgrade = _is_downgrade(
        previous, entries, effective_route=route, effective_level=verification.level
    )
    if state in {"BLOCKED", "ESCALATED"} and not _resolution_allowed(
        record,
        repository_root=repository_root,
        task_id=task_id,
        authorization_required=downgrade,
        previous=previous,
        input_sha256=stable_hash,
        policy_sha256=bundle.sha256,
        effective_route=route,
    ):
        raise StateTransitionError(
            "Blocked task requires a complete authorized resolution record",
            code="CLASSIFICATION_RESOLUTION_REQUIRED",
        )
    classification: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": task_id,
        "classification_input_sha256": stable_hash,
        "policy_version": bundle.policy_version,
        "policy_sha256": bundle.sha256,
        "base_commit": record.task["base_commit"],
        "subject_commit": record.task["subject_commit"],
        "classified_at": at,
        "effective_route": route,
        "effective_verification_level": verification.level,
        "change_reason": _change_reason(previous, entries, route=route, level=verification.level),
        "classifications": entries,
    }
    require_valid_contract("classification", classification)
    evidence = {
        "classification_input_sha256": stable_hash,
        "policy_sha256": bundle.sha256,
        "effective_route": route,
        "effective_verification_level": verification.level,
        "change_reason": _change_reason(previous, entries, route=route, level=verification.level),
    }
    target_state, event_type, preconditions = _target(route, blocked, entries)
    target_payload = {
        **evidence,
        "blocking_reasons": list(verification.blocking_reasons),
        "previous_classification_input_sha256": previous.get("classification_input_sha256")
        if previous
        else None,
        "downgrade": downgrade,
    }
    if state in {"BLOCKED", "ESCALATED"}:
        marker = {
            "schema_version": "1.0",
            "task_id": task_id,
            "source_state": state,
            "actor": actor.strip(),
            "classification": classification,
            "evidence": evidence,
            "resolution_event_type": "block_resolved"
            if state == "BLOCKED"
            else "escalation_resolved",
            "resolution_event_sequence": record.events[-1]["sequence"],
            "resolution_payload": record.events[-1].get("payload"),
            "previous_classification_input_sha256": previous.get("classification_input_sha256")
            if previous
            else None,
            "previous_policy_sha256": previous.get("policy_sha256") if previous else None,
            "target_state": target_state,
            "target_event_type": event_type,
            "target_preconditions": sorted(preconditions),
            "target_payload": target_payload,
        }
        atomic_write_json(pending_path, marker)
        return _resume_classification(repository_root, task_id, marker)
    # Initial classification is durable before its state events; CLASSIFIED retry recovers it.
    atomic_write_json(
        resolve_task_path(repository_root, task_id, "classification.json"), classification
    )
    if state == "NEW":
        transition_task_record(
            repository_root,
            task_id,
            target_state="CLASSIFIED",
            event_type="classification_recorded",
            actor=actor,
            payload=evidence,
            satisfied_preconditions={"classification_available"},
        )
    transition_task_record(
        repository_root,
        task_id,
        target_state=target_state,
        event_type=event_type,
        actor=actor,
        payload=target_payload,
        satisfied_preconditions=preconditions,
    )
    return classification
