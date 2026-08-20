"""Single deterministic freshness matrix for governed artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from aiflow.decision_units import classification_input_digest

FreshnessStatus = Literal["fresh", "stale", "missing", "not_applicable"]
_ORDER = (
    "FRESHNESS_ARTIFACT_INVALID",
    "FRESHNESS_SUBJECT_CHANGED",
    "FRESHNESS_ATTESTATION_CHANGED",
    "FRESHNESS_GOVERNANCE_CHANGED",
    "FRESHNESS_SPEC_CHANGED",
    "FRESHNESS_POLICY_CHANGED",
    "FRESHNESS_CLASSIFICATION_CHANGED",
    "FRESHNESS_VERIFICATION_CHANGED",
    "FRESHNESS_EVIDENCE_CHANGED",
    "FRESHNESS_EVIDENCE_NOT_PASSED",
    "FRESHNESS_SCOPE_CHANGED",
    "FRESHNESS_ACTION_CHANGED",
    "FRESHNESS_ACTION_EXPIRED",
    "FRESHNESS_ACTION_USED",
)


@dataclass(frozen=True)
class ArtifactFreshness:
    status: FreshnessStatus
    reason_codes: tuple[str, ...]
    reproduce_argv: tuple[str, ...]


def current_classification_input_digest(
    task: Mapping[str, object],
    units: Sequence[Mapping[str, object]],
    classification: Mapping[str, object],
    events: Sequence[Mapping[str, object]],
) -> tuple[str, bool]:
    """Preserve classification facts across an ordered audited subject synchronization chain."""
    current_subject = task.get("subject_commit")
    classified_subject = classification.get("subject_commit")
    cursor = classified_subject
    for event in events:
        payload = event.get("payload")
        if (
            event.get("event_type") == "subject_commit_synchronized"
            and isinstance(payload, Mapping)
            and payload.get("old_subject_commit") == cursor
            and isinstance(payload.get("new_subject_commit"), str)
        ):
            cursor = payload["new_subject_commit"]
    synchronized = current_subject != classified_subject and cursor == current_subject
    digest_task = {**task, "subject_commit": classified_subject} if synchronized else dict(task)
    return classification_input_digest(digest_task, units), synchronized


def evaluate_freshness(
    artifact_type: Literal[
        "classification", "evidence", "spec_approval", "code_approval", "action_approval"
    ],
    artifact: Mapping[str, object] | None,
    current: Mapping[str, object],
    *,
    invalid: bool = False,
) -> ArtifactFreshness:
    """Compare public binding facts without reading or modifying artifact contents."""
    task_id = str(current.get("task_id", "TASK-0000"))
    command = {
        "classification": ("aiflow", "classify", task_id),
        "evidence": ("aiflow", "verify", task_id),
        "spec_approval": ("aiflow", "approve", task_id, "--type", "spec"),
        "code_approval": ("aiflow", "approve", task_id, "--type", "code"),
        "action_approval": ("aiflow", "approve", task_id, "--type", "action"),
    }[artifact_type]
    if artifact is None:
        if current.get("applicable") is False:
            return ArtifactFreshness("not_applicable", (), ())
        return ArtifactFreshness("missing", ("FRESHNESS_ARTIFACT_MISSING",), command)
    reasons: list[str] = ["FRESHNESS_ARTIFACT_INVALID"] if invalid else []
    classification_fields = [
        "base_commit",
        "policy_sha256",
        "classification_input_sha256",
    ]
    if current.get("subject_synchronized") is not True:
        classification_fields.append("subject_commit")
    fields = {
        "classification": (*classification_fields,),
        "evidence": (
            "repository_id",
            "branch",
            "base_commit",
            "subject_commit",
            "policy_sha256",
            "spec_sha256",
            "classification_input_sha256",
        ),
        "spec_approval": ("base_commit", "policy_sha256", "spec_sha256"),
        "code_approval": ("base_commit", "subject_commit", "policy_sha256", "spec_sha256"),
        "action_approval": (
            "base_commit",
            "subject_commit",
            "policy_sha256",
            "spec_sha256",
        ),
    }[artifact_type]
    reason_for_field = {
        "repository_id": "FRESHNESS_SCOPE_CHANGED",
        "branch": "FRESHNESS_SCOPE_CHANGED",
        "base_commit": "FRESHNESS_SCOPE_CHANGED",
        "policy_sha256": "FRESHNESS_POLICY_CHANGED",
        "subject_commit": "FRESHNESS_SUBJECT_CHANGED",
        "spec_sha256": "FRESHNESS_SPEC_CHANGED",
        "classification_input_sha256": "FRESHNESS_CLASSIFICATION_CHANGED",
    }
    for field in fields:
        if current.get(field) is not None and artifact.get(field) != current.get(field):
            reasons.append(reason_for_field[field])
    if (
        artifact_type == "evidence"
        and artifact.get("mode") == "ci"
        and current.get("attestation_head") is not None
        and artifact.get("attestation_head") != current.get("attestation_head")
    ):
        reasons.append("FRESHNESS_ATTESTATION_CHANGED")
    if artifact_type in {"evidence", "code_approval"}:
        if current.get("governance_only") is False:
            reasons.append("FRESHNESS_GOVERNANCE_CHANGED")
        if artifact_type == "evidence":
            if artifact.get("mode") == "ci" and current.get("attestation_governance_only") is False:
                reasons.append("FRESHNESS_GOVERNANCE_CHANGED")
            if artifact.get("conclusion") != "passed":
                reasons.append("FRESHNESS_EVIDENCE_NOT_PASSED")
            if current.get("verification_level") is not None and artifact.get(
                "verification_level"
            ) != current.get("verification_level"):
                reasons.append("FRESHNESS_VERIFICATION_CHANGED")
        else:
            if current.get("evidence_sha256") is not None and artifact.get(
                "evidence_sha256"
            ) != current.get("evidence_sha256"):
                reasons.append("FRESHNESS_EVIDENCE_CHANGED")
            if current.get("evidence_current") is False:
                reasons.append("FRESHNESS_EVIDENCE_NOT_PASSED")
    if artifact_type == "action_approval":
        action_sha256 = current.get("action_sha256")
        if action_sha256 is None:
            reasons.append("FRESHNESS_ACTION_CHANGED")
        elif artifact.get("action_sha256") != action_sha256:
            reasons.append("FRESHNESS_ACTION_CHANGED")
        expires_at = artifact.get("expires_at")
        now = current.get("now")
        if isinstance(expires_at, str) and isinstance(now, str):
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                observed = datetime.fromisoformat(now.replace("Z", "+00:00"))
                if expiry.tzinfo is None or observed.tzinfo is None:
                    raise ValueError
            except ValueError:
                reasons.append("FRESHNESS_ARTIFACT_INVALID")
            else:
                if expiry.astimezone(timezone.utc) <= observed.astimezone(timezone.utc):
                    reasons.append("FRESHNESS_ACTION_EXPIRED")
        elif current.get("action_expired") is True:
            reasons.append("FRESHNESS_ACTION_EXPIRED")
        used = current.get("used_action_sha256s")
        if (
            isinstance(action_sha256, str)
            and isinstance(used, (list, tuple, set, frozenset))
            and action_sha256 in used
        ) or current.get("action_used") is True:
            reasons.append("FRESHNESS_ACTION_USED")
    ordered = tuple(code for code in _ORDER if code in reasons)
    return ArtifactFreshness("stale" if ordered else "fresh", ordered, command)
