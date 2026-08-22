"""Pure preparation and freshness checks for independent approval types."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import ContractError, StateTransitionError, StorageError
from aiflow.freshness import current_classification_input_digest
from aiflow.git_context import collect_git_context
from aiflow.policy import load_policy_bundle
from aiflow.review import validate_review_package
from aiflow.review_service import ReviewAssessment, latest_review_assessment
from aiflow.specification import specification_digest
from aiflow.state import create_record_event, create_transition_event
from aiflow.storage import atomic_write_json, read_task_json, resolve_task_path
from aiflow.task_service import _persist_event_and_task, load_task_record

ApprovalType = Literal["spec", "code", "action"]
_APPROVAL_STATES: Mapping[ApprovalType, str | None] = {
    "spec": "WAITING_FOR_SPEC_REVIEW",
    "code": "WAITING_FOR_FINAL_REVIEW",
    "action": None,
}
APPROVAL_MARKER = "approval_pending.json"


@dataclass(frozen=True)
class ApprovalContext:
    """Version facts an approval must bind before persistence."""

    task_id: str
    decision_unit_id: str
    task_state: str
    spec_sha256: str
    policy_sha256: str
    base_commit: str
    subject_commit: str
    action_sha256: str | None = None


@dataclass(frozen=True)
class ApprovalPreparation:
    """Schema-valid approval record and optional action metadata for its event."""

    record: Mapping[str, object]
    action: Mapping[str, object] | None


@dataclass(frozen=True)
class ApprovalResult:
    """Persisted current approvals and the optional new audit event."""

    task: Mapping[str, object]
    approvals: tuple[Mapping[str, object], ...]
    event: Mapping[str, object] | None


def _invalid(message: str, code: str) -> ContractError:
    return ContractError(message, code=code)


def _require_nonempty(value: str, code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise _invalid("Approval input is required", code)
    return normalized


def _utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise _invalid("Approval timestamp is invalid", "APPROVAL_TIMESTAMP_INVALID") from error
    if parsed.tzinfo is None:
        raise _invalid("Approval timestamp is invalid", "APPROVAL_TIMESTAMP_INVALID")
    return parsed.astimezone(timezone.utc)


def validate_action_file(
    action_file: Mapping[str, object], *, subject_commit: str, now: str | None = None
) -> Mapping[str, object]:
    """Validate exact, single-use action authorization data without executing it."""
    allowed_keys = {
        "decision_unit_id",
        "action_type",
        "target",
        "parameter_summary",
        "parameters_summary",
        "subject_commit",
        "conditions",
        "expires_at",
        "single_use",
    }
    if set(action_file) - allowed_keys:
        raise _invalid("Action approval file contains unknown fields", "ACTION_FILE_INVALID")
    if (
        "parameter_summary" in action_file
        and "parameters_summary" in action_file
        and action_file["parameter_summary"] != action_file["parameters_summary"]
    ):
        raise _invalid("Action parameter summaries conflict", "ACTION_FILE_INVALID")
    summary = action_file.get("parameter_summary", action_file.get("parameters_summary"))
    value = {
        "action_type": action_file.get("action_type"),
        "target": action_file.get("target"),
        "parameter_summary": summary,
        "subject_commit": action_file.get("subject_commit"),
        "conditions": action_file.get("conditions"),
        "expires_at": action_file.get("expires_at"),
        "single_use": action_file.get("single_use"),
    }
    strings = ("action_type", "target", "parameter_summary", "subject_commit", "expires_at")
    for key in strings:
        field = value[key]
        if not isinstance(field, str) or not field.strip():
            raise _invalid("Action approval file is incomplete", "ACTION_FILE_INVALID")
    if value["subject_commit"] != subject_commit:
        raise _invalid("Action approval targets a different commit", "ACTION_SUBJECT_MISMATCH")
    conditions = value["conditions"]
    if not isinstance(conditions, list) or not all(
        isinstance(condition, str) and condition.strip() for condition in conditions
    ):
        raise _invalid("Action approval conditions are invalid", "ACTION_FILE_INVALID")
    if value["single_use"] is not True:
        raise _invalid("Action approval must be single use", "ACTION_SINGLE_USE_REQUIRED")
    expires_at = _utc(str(value["expires_at"]))
    if now is not None and expires_at <= _utc(now):
        raise _invalid("Action approval has expired", "ACTION_APPROVAL_EXPIRED")
    return {**value, "conditions": list(conditions)}


def prepare_approval(
    *,
    approval_type: ApprovalType,
    context: ApprovalContext,
    actor: str,
    reason: str,
    approved_at: str,
    review_package: str | None = None,
    evidence_current: bool = False,
    worktree_governance_only: bool = False,
    subject_commit_current: bool = True,
    action_file: Mapping[str, object] | None = None,
) -> ApprovalPreparation:
    """Prepare one independent, version-bound approval without writing it."""
    expected_state = _APPROVAL_STATES.get(approval_type)
    if approval_type not in _APPROVAL_STATES:
        raise _invalid("Approval type is unsupported", "APPROVAL_TYPE_INVALID")
    if expected_state is not None and context.task_state != expected_state:
        raise StateTransitionError(
            "Approval is not allowed in the current state", code="APPROVAL_STATE_INVALID"
        )
    normalized_actor = _require_nonempty(actor, "APPROVAL_ACTOR_INVALID")
    normalized_reason = _require_nonempty(reason, "APPROVAL_REASON_REQUIRED")
    _utc(approved_at)
    if approval_type == "code":
        if review_package is None:
            raise _invalid("Code approval requires a review package", "CODE_REVIEW_PACKAGE_MISSING")
        validate_review_package(review_package)
        if not evidence_current:
            raise _invalid("Code approval requires current passing evidence", "CODE_EVIDENCE_STALE")
        if not worktree_governance_only:
            raise _invalid(
                "Code approval requires a governance-only worktree", "CODE_WORKTREE_DIRTY"
            )
        if not subject_commit_current:
            raise _invalid("Code approval subject commit is stale", "CODE_SUBJECT_STALE")
    action = None
    if approval_type == "action":
        if action_file is None:
            raise _invalid("Action approval requires an action file", "ACTION_FILE_REQUIRED")
        action = validate_action_file(
            action_file, subject_commit=context.subject_commit, now=approved_at
        )
    raw_record: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": context.task_id,
        "decision_unit_id": context.decision_unit_id,
        "approval_type": approval_type,
        "actor": normalized_actor,
        "reason": normalized_reason,
        "spec_sha256": context.spec_sha256,
        "policy_sha256": context.policy_sha256,
        "base_commit": context.base_commit,
        "subject_commit": context.subject_commit,
        "approved_at": approved_at,
    }
    if action is not None:
        action_sha256 = hashlib.sha256(
            json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        raw_record.update(
            {
                "action_sha256": action_sha256,
                "expires_at": action["expires_at"],
                "single_use": True,
            }
        )
    require_valid_contract("approval", raw_record)
    return ApprovalPreparation(record=raw_record, action=action)


def approval_is_current(
    approval: Mapping[str, object], context: ApprovalContext, *, now: str | None = None
) -> bool:
    """Check immutable version bindings; approval type remains a caller-specific gate."""
    try:
        require_valid_contract("approval", dict(approval))
    except ContractError:
        return False
    fields = {
        "task_id": context.task_id,
        "decision_unit_id": context.decision_unit_id,
        "spec_sha256": context.spec_sha256,
        "policy_sha256": context.policy_sha256,
        "base_commit": context.base_commit,
    }
    if approval.get("approval_type") != "spec":
        fields["subject_commit"] = context.subject_commit
    current = all(approval.get(field) == expected for field, expected in fields.items())
    if approval.get("approval_type") == "action":
        expires_at = approval.get("expires_at")
        if not isinstance(expires_at, str):
            return False
        try:
            unexpired = _utc(expires_at) > _utc(now or _now())
        except ContractError:
            return False
        return (
            current
            and unexpired
            and context.action_sha256 is not None
            and approval.get("action_sha256") == context.action_sha256
        )
    return current


def matching_approval(
    approvals: Sequence[Mapping[str, object]],
    *,
    approval_type: ApprovalType,
    context: ApprovalContext,
) -> Mapping[str, object] | None:
    """Return the first current approval of the requested independent type."""
    for approval in approvals:
        if approval.get("approval_type") == approval_type and approval_is_current(
            approval, context
        ):
            return approval
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_text(path: Path, *, code: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise StorageError("Could not read approval input", code=code) from error


def _read_external_json(path: Path, *, code: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StorageError("Could not read approval input", code=code) from error
    if not isinstance(value, Mapping):
        raise ContractError("Approval input must be an object", code=code)
    return value


def _governance_only(repository_root: Path, task_id: str, subject_commit: str) -> bool:
    context = collect_git_context(repository_root)
    prefix = f".ai/tasks/{task_id}/"
    if any(
        path != prefix.rstrip("/") and not path.startswith(prefix) for path in context.dirty_paths
    ):
        return False
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "-z", f"{subject_commit}..{context.head}"],
            cwd=repository_root,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ContractError(
            "Could not inspect approval Git context", code="APPROVAL_GIT_INVALID"
        ) from error
    if result.returncode != 0:
        raise ContractError("Could not inspect approval Git context", code="APPROVAL_GIT_INVALID")
    try:
        paths = [path for path in result.stdout.decode("utf-8").split("\0") if path]
    except UnicodeDecodeError as error:
        raise ContractError(
            "Could not inspect approval Git context", code="APPROVAL_GIT_INVALID"
        ) from error
    return all(path.startswith(prefix) for path in paths)


def _evidence(
    repository_root: Path,
    task_id: str,
    *,
    task: Mapping[str, object],
    classification: Mapping[str, object],
    spec_sha256: str,
    policy_sha256: str,
    review_ids: set[str],
) -> tuple[bool, str | None]:
    path = resolve_task_path(repository_root, task_id, "evidence.json")
    if not path.is_file():
        return False, None
    value = read_task_json(repository_root, task_id, "evidence.json", contract_name="evidence")
    if not isinstance(value, Mapping):
        return False, None
    checks = value.get("checks")
    current = (
        value.get("task_id") == task_id
        and value.get("repository_id") == task.get("repository_id")
        and value.get("branch") == task.get("branch")
        and value.get("base_commit") == task.get("base_commit")
        and value.get("subject_commit") == task.get("subject_commit")
        and value.get("spec_sha256") == spec_sha256
        and value.get("policy_sha256") == policy_sha256
        and value.get("classification_input_sha256")
        == classification.get("classification_input_sha256")
        and value.get("verification_level") == classification.get("effective_verification_level")
        and value.get("conclusion") == "passed"
        and isinstance(checks, list)
        and any(isinstance(check, Mapping) and check.get("required") is True for check in checks)
        and all(
            isinstance(check, Mapping)
            and (check.get("required") is not True or check.get("status") == "passed")
            for check in checks
        )
        and isinstance(value.get("decision_unit_ids"), list)
        and review_ids.issubset(set(value["decision_unit_ids"]))
    )
    digest = hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return current, digest


def _load_approvals(repository_root: Path, task_id: str) -> list[dict[str, object]]:
    value = read_task_json(repository_root, task_id, "approvals.json")
    if not isinstance(value, list):
        raise ContractError("Task approvals must be an array", code="APPROVAL_RECORD_INVALID")
    result: list[dict[str, object]] = []
    for approval in value:
        if not isinstance(approval, dict):
            raise ContractError("Task approval is invalid", code="APPROVAL_RECORD_INVALID")
        require_valid_contract("approval", approval)
        result.append(approval)
    return result


def _logical_identity(approval: Mapping[str, object]) -> str:
    stable = {key: value for key, value in approval.items() if key != "approved_at"}
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _remove_marker(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        raise StorageError(
            "Approval completed but recovery marker remains", code="APPROVAL_MARKER_REMOVE_FAILED"
        ) from error


def _complete_marker(repository_root: Path, task_id: str) -> ApprovalResult:
    marker_path = resolve_task_path(repository_root, task_id, APPROVAL_MARKER)
    marker = read_task_json(repository_root, task_id, APPROVAL_MARKER)
    if not isinstance(marker, dict) or marker.get("task_id") != task_id:
        raise StorageError("Approval recovery marker is invalid", code="APPROVAL_RECOVERY_INVALID")
    task = marker.get("task")
    event = marker.get("event")
    approvals = marker.get("approvals")
    if not isinstance(task, dict) or not isinstance(event, dict) or not isinstance(approvals, list):
        raise StorageError(
            "Approval recovery marker is incomplete", code="APPROVAL_RECOVERY_INVALID"
        )
    require_valid_contract("task", task)
    require_valid_contract("event", event)
    for approval in approvals:
        require_valid_contract("approval", approval)
    atomic_write_json(resolve_task_path(repository_root, task_id, "approvals.json"), approvals)
    record = load_task_record(repository_root, task_id)
    recorded = next(
        (item for item in record.events if item.get("sequence") == event.get("sequence")), None
    )
    if recorded is not None:
        if recorded != event or record.task.get("current_state") != task.get("current_state"):
            raise StorageError(
                "Approval recovery conflicts with task history", code="APPROVAL_RECOVERY_CONFLICT"
            )
        _remove_marker(marker_path)
        return ApprovalResult(record.task, tuple(approvals), event)
    if len(record.events) + 1 != event.get("sequence"):
        raise StorageError(
            "Approval recovery conflicts with task history", code="APPROVAL_RECOVERY_CONFLICT"
        )
    _persist_event_and_task(resolve_task_path(repository_root, task_id), task, event)
    _remove_marker(marker_path)
    return ApprovalResult(task, tuple(approvals), event)


def approve_task(
    repository_root: Path,
    task_id: str,
    *,
    approval_type: ApprovalType,
    actor: str,
    reason: str,
    action_file: Path | None = None,
) -> ApprovalResult:
    """Validate and persist one independent approval type without executing actions."""
    if approval_type != "action" and action_file is not None:
        raise ContractError(
            "Only action approvals accept an action file", code="ACTION_FILE_NOT_ALLOWED"
        )
    marker = resolve_task_path(repository_root, task_id, APPROVAL_MARKER)
    if marker.is_file():
        return _complete_marker(repository_root, task_id)
    record = load_task_record(repository_root, task_id)
    spec_sha256 = record.task.get("frozen_spec_sha256")
    if not isinstance(spec_sha256, str):
        raise ContractError(
            "Approval requires a frozen specification", code="APPROVAL_SPEC_NOT_FROZEN"
        )
    spec_path = resolve_task_path(repository_root, task_id, "spec.md")
    try:
        current_spec = specification_digest(spec_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise StorageError(
            "Could not read frozen specification", code="APPROVAL_SPEC_READ_FAILED"
        ) from error
    if current_spec != spec_sha256:
        raise ContractError("Approval specification is stale", code="APPROVAL_SPEC_STALE")
    policy = load_policy_bundle(repository_root)
    classification = read_task_json(
        repository_root, task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(classification, dict):
        raise ContractError(
            "Approval classification is invalid", code="APPROVAL_CLASSIFICATION_INVALID"
        )
    units = parse_decision_units(record.task)
    input_sha256, synchronized = current_classification_input_digest(
        record.task, units, classification, record.events
    )
    if (
        classification.get("classification_input_sha256") != input_sha256
        or classification.get("policy_sha256") != policy.sha256
        or (
            classification.get("subject_commit") != record.task.get("subject_commit")
            and not synchronized
        )
    ):
        raise ContractError(
            "Approval classification is stale", code="APPROVAL_CLASSIFICATION_STALE"
        )
    entries = classification.get("classifications")
    assert isinstance(entries, list)
    review_ids = {
        str(entry["decision_unit_id"])
        for entry in entries
        if isinstance(entry, Mapping) and entry.get("route") == "REVIEW"
    }
    approved_at = _now()
    review_package: str | None = None
    evidence_current = False
    evidence_sha256: str | None = None
    governance_only = True
    action_value: Mapping[str, object] | None = None
    if approval_type == "code":
        review_package = _read_text(
            resolve_task_path(repository_root, task_id, "review-package.md"),
            code="CODE_REVIEW_PACKAGE_MISSING",
        )
        evidence_current, evidence_sha256 = _evidence(
            repository_root,
            task_id,
            task=record.task,
            classification=classification,
            spec_sha256=spec_sha256,
            policy_sha256=policy.sha256,
            review_ids=review_ids,
        )
        governance_only = _governance_only(
            repository_root, task_id, str(record.task.get("subject_commit"))
        )
    structured_review: ReviewAssessment | None = None
    if approval_type == "spec":
        structured_review = latest_review_assessment(
            repository_root,
            task_id,
            "design",
            decision_unit_ids=sorted(review_ids),
        )
    elif approval_type == "code":
        structured_review = latest_review_assessment(
            repository_root,
            task_id,
            "implementation",
            decision_unit_ids=sorted(review_ids),
            evidence_sha256=evidence_sha256,
        )
    action_decision_unit: str | None = None
    if approval_type == "action":
        if action_file is None:
            raise ContractError(
                "Action approval requires an action file", code="ACTION_FILE_REQUIRED"
            )
        action_value = _read_external_json(action_file, code="ACTION_FILE_INVALID")
        raw_decision_unit = action_value.get("decision_unit_id")
        if not isinstance(raw_decision_unit, str) or raw_decision_unit not in {
            unit.get("decision_unit_id")
            for unit in record.task.get("decision_units", [])
            if isinstance(unit, Mapping)
        }:
            raise ContractError(
                "Action decision unit is invalid", code="ACTION_DECISION_UNIT_INVALID"
            )
        action_decision_unit = raw_decision_unit
    target_ids = [action_decision_unit] if action_decision_unit else sorted(review_ids)
    if not target_ids:
        raise ContractError(
            "Approval has no applicable decision unit", code="APPROVAL_UNIT_MISSING"
        )
    candidates: list[dict[str, object]] = []
    actual_state = str(record.task.get("current_state"))
    retry_target = {
        "spec": "READY_TO_IMPLEMENT",
        "code": "APPROVED_FOR_MERGE",
    }.get(approval_type)
    preparation_state = actual_state
    if actual_state == retry_target:
        preparation_state = (
            "WAITING_FOR_SPEC_REVIEW" if approval_type == "spec" else "WAITING_FOR_FINAL_REVIEW"
        )
    for decision_unit_id in target_ids:
        assert decision_unit_id is not None
        prepared = prepare_approval(
            approval_type=approval_type,
            context=ApprovalContext(
                task_id=task_id,
                decision_unit_id=decision_unit_id,
                task_state=preparation_state,
                spec_sha256=spec_sha256,
                policy_sha256=policy.sha256,
                base_commit=str(record.task.get("base_commit")),
                subject_commit=str(record.task.get("subject_commit")),
            ),
            actor=actor,
            reason=reason,
            approved_at=approved_at,
            review_package=review_package,
            evidence_current=evidence_current,
            worktree_governance_only=governance_only,
            subject_commit_current=governance_only,
            action_file=action_value,
        )
        candidate = dict(prepared.record)
        if evidence_sha256 is not None:
            candidate["evidence_sha256"] = evidence_sha256
            require_valid_contract("approval", candidate)
        candidates.append(candidate)
    approvals = _load_approvals(repository_root, task_id)
    existing_identities = {_logical_identity(approval) for approval in approvals}
    additions = [
        candidate
        for candidate in candidates
        if _logical_identity(candidate) not in existing_identities
    ]
    if approval_type in {"spec", "code"} and actual_state == retry_target:
        if not additions:
            return ApprovalResult(record.task, tuple(approvals), None)
        raise StateTransitionError(
            "Approval is not allowed in the current state", code="APPROVAL_STATE_INVALID"
        )
    if not additions and approval_type == "action":
        return ApprovalResult(record.task, tuple(approvals), None)
    final_approvals = [*approvals, *additions]
    if approval_type == "action":
        event = create_record_event(
            record.task,
            event_type="approval_recorded",
            actor=str(candidates[0]["actor"]),
            payload={"approval_type": approval_type, "approvals": additions},
            sequence=len(record.events) + 1,
        )
        task = {**record.task, "updated_at": event["occurred_at"]}
    else:
        target_state = "READY_TO_IMPLEMENT" if approval_type == "spec" else "APPROVED_FOR_MERGE"
        event_type = "spec_approved" if approval_type == "spec" else "code_approved"
        preconditions = (
            {"spec_frozen", "spec_approval_valid"}
            if approval_type == "spec"
            else {"code_approval_valid"}
        )
        review_payload = None
        if structured_review is not None:
            review_payload = {
                "review_id": structured_review.record["review_id"],
                "revision": structured_review.record["revision"],
                "review_stage": structured_review.record["review_stage"],
                "context_sha256": structured_review.record["context_sha256"],
            }
        event = create_transition_event(
            record.task,
            target_state=target_state,
            event_type=event_type,
            actor=str(candidates[0]["actor"]),
            payload={
                "approval_type": approval_type,
                "approvals": additions or candidates,
                "structured_review": review_payload,
            },
            sequence=len(record.events) + 1,
            satisfied_preconditions=preconditions,
        )
        task = {
            **record.task,
            "current_state": target_state,
            "updated_at": event["occurred_at"],
        }
    require_valid_contract("task", task)
    atomic_write_json(
        marker,
        {
            "schema_version": "1.0",
            "task_id": task_id,
            "task": task,
            "event": event,
            "approvals": final_approvals,
        },
    )
    return _complete_marker(repository_root, task_id)
