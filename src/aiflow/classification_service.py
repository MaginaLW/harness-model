"""Classification orchestration: facts in, durable routing evidence out."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import ContractError, StateTransitionError
from aiflow.git_context import collect_git_context
from aiflow.policy import load_policy_bundle
from aiflow.routing import ROUTE_ORDER, route_task
from aiflow.storage import atomic_write_json, read_task_json, resolve_task_path
from aiflow.task_service import TaskRecord, read_task_record_strict, transition_task_record
from aiflow.verification_level import verification_for_task


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _stable_input(task: Mapping[str, object], units: tuple[dict[str, Any], ...]) -> str:
    """Digest only durable decision facts, never state/timestamps/worktree paths."""
    value = {
        "task_id": task.get("task_id"),
        "goal": task.get("goal"),
        "allowed_scope": task.get("allowed_scope"),
        "forbidden_actions": task.get("forbidden_actions"),
        "base_commit": task.get("base_commit"),
        "subject_commit": task.get("subject_commit"),
        "decision_units": units,
    }
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _scope_allowed(impact: object, allowed: object) -> bool:
    if not isinstance(impact, list) or not isinstance(allowed, list):
        return False
    patterns = [item.replace("\\", "/") for item in allowed if isinstance(item, str)]
    if len(patterns) != len(allowed):
        return False
    for item in impact:
        if not isinstance(item, str) or not item.strip():
            return False
        path = item.replace("\\", "/")
        if (
            path.startswith("/")
            or (len(path) >= 3 and path[1:3] == ":/")
            or ".." in PurePosixPath(path).parts
        ):
            return False
        # pathlib's ** semantics vary at the directory boundary, hence prefix too.
        if not any(
            PurePosixPath(path).match(pattern)
            or (pattern.endswith("/**") and path.startswith(pattern[:-3].rstrip("/") + "/"))
            for pattern in patterns
        ):
            return False
    return True


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


def _resolution_allowed(
    record: TaskRecord,
    *,
    authorization_required: bool,
    previous: Mapping[str, object] | None,
    input_sha256: str,
    policy_sha256: str,
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
    if authorization_required and (
        payload.get("manual_authorization") is not True
        or not isinstance(payload.get("authorized_by"), str)
        or not payload["authorized_by"].strip()
        or payload.get("authorized_classification_input_sha256") != input_sha256
        or payload.get("authorized_policy_sha256") != policy_sha256
    ):
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
        authorization_required=downgrade,
        previous=previous,
        input_sha256=stable_hash,
        policy_sha256=bundle.sha256,
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
    # This is deliberately first: a failed durable classification cannot mutate state.
    atomic_write_json(
        resolve_task_path(repository_root, task_id, "classification.json"), classification
    )
    evidence = {
        "classification_input_sha256": stable_hash,
        "policy_sha256": bundle.sha256,
        "effective_route": route,
        "effective_verification_level": verification.level,
        "change_reason": _change_reason(previous, entries, route=route, level=verification.level),
    }
    if state in {"BLOCKED", "ESCALATED"}:
        event_type = "block_resolved" if state == "BLOCKED" else "escalation_resolved"
        transition_task_record(
            repository_root,
            task_id,
            target_state="CLASSIFIED",
            event_type=event_type,
            actor=actor,
            payload={**evidence, "resolution_event_sequence": record.events[-1]["sequence"]},
            satisfied_preconditions={"resolution_recorded"},
        )
    elif state == "NEW":
        transition_task_record(
            repository_root,
            task_id,
            target_state="CLASSIFIED",
            event_type="classification_recorded",
            actor=actor,
            payload=evidence,
            satisfied_preconditions={"classification_available"},
        )
    target_state, event_type, preconditions = _target(route, blocked, entries)
    transition_task_record(
        repository_root,
        task_id,
        target_state=target_state,
        event_type=event_type,
        actor=actor,
        payload={
            **evidence,
            "blocking_reasons": list(verification.blocking_reasons),
            "previous_classification_input_sha256": previous.get("classification_input_sha256")
            if previous
            else None,
            "downgrade": downgrade,
        },
        satisfied_preconditions=preconditions,
    )
    return classification
