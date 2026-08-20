"""Strictly read-only task status summaries."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import AiflowError, ContractError
from aiflow.freshness import current_classification_input_digest, evaluate_freshness
from aiflow.git_context import collect_git_context
from aiflow.policy import load_policy_bundle
from aiflow.routing import ROUTE_ORDER
from aiflow.scope import assess_governance_only_scope, collect_verification_changed_paths
from aiflow.specification import specification_digest
from aiflow.state import TRANSITIONS
from aiflow.storage import read_task_json, resolve_task_path
from aiflow.task_service import TaskRecord, read_task_record_strict

MISSING_BY_STATE: dict[str, tuple[str, ...]] = {
    "NEW": ("classification",),
    "CLASSIFIED": ("route_resolution",),
    "WAITING_FOR_ASK": ("ask_answer", "spec_frozen"),
    "WAITING_FOR_SPEC_REVIEW": ("spec_approval",),
    "READY_TO_IMPLEMENT": ("begin",),
    "BLOCKED": ("block_resolution",),
    "IMPLEMENTING": ("implementation_result",),
    "VERIFYING": ("verification_result",),
    "VERIFIED": ("final_route",),
    "FAILED": ("retry_reason_or_escalation",),
    "ESCALATED": ("escalation_resolution",),
    "WAITING_FOR_FINAL_REVIEW": ("code_approval",),
    "APPROVED_FOR_MERGE": ("external_merge",),
    "MERGED": (),
}


@dataclass(frozen=True)
class StatusSummary:
    task_id: str
    goal: str
    repository_id: str
    current_state: str
    route: str
    verification_level: str
    next_events: tuple[str, ...]
    missing_conditions: tuple[str, ...]
    base_commit: str
    subject_commit: str | None
    observed_head: str
    worktree_dirty: bool
    dirty_paths: tuple[str, ...]
    classification: str
    approvals: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["next_events"] = list(self.next_events)
        value["missing_conditions"] = list(self.missing_conditions)
        value["dirty_paths"] = list(self.dirty_paths)
        return value

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    def to_text(self) -> str:
        next_events = ", ".join(self.next_events) or "none"
        missing = ", ".join(self.missing_conditions) or "none"
        return "\n".join(
            (
                f"Task: {self.task_id}",
                f"Goal: {self.goal}",
                f"State: {self.current_state}",
                f"Route / verification: {self.route} / {self.verification_level}",
                f"Next events: {next_events}",
                f"Missing: {missing}",
                f"Subject / observed HEAD: {self.subject_commit} / {self.observed_head}",
                f"Worktree dirty: {str(self.worktree_dirty).lower()}",
                f"Classification / approvals / evidence: "
                f"{self.classification} / {self.approvals} / {self.evidence}",
            )
        )


def _classification(
    repository_root: Path, task_id: str
) -> tuple[str, str, dict[str, Any] | None, bool]:
    path = resolve_task_path(repository_root, task_id, "classification.json")
    if not path.is_file():
        return "not_available", "not_available", None, False
    try:
        value = read_task_json(
            repository_root, task_id, "classification.json", contract_name="classification"
        )
    except AiflowError:
        return "stale", "stale", None, True
    if not isinstance(value, dict):
        return "stale", "stale", None, True
    route = value.get("effective_route")
    verification = value.get("effective_verification_level")
    if route not in ROUTE_ORDER or verification not in {"V0", "V1"}:
        return "stale", "stale", value, True
    return str(route), str(verification), value, False


def _current_facts(
    repository_root: Path,
    task_id: str,
    task: dict[str, Any],
    *,
    observed_head: str,
    classification: dict[str, Any] | None,
    events: tuple[dict[str, Any], ...],
) -> dict[str, object]:
    """Collect the current public bindings once for every freshness consumer."""
    facts: dict[str, object] = {
        "task_id": task_id,
        "repository_id": task.get("repository_id"),
        "branch": task.get("branch"),
        "base_commit": task.get("base_commit"),
        "subject_commit": task.get("subject_commit"),
        "attestation_head": observed_head,
        "now": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "used_action_sha256s": (),
    }
    try:
        facts["policy_sha256"] = load_policy_bundle(repository_root).sha256
    except AiflowError:
        facts["policy_sha256"] = "unavailable"
    spec_path = resolve_task_path(repository_root, task_id, "spec.md")
    try:
        facts["spec_sha256"] = specification_digest(spec_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        facts["spec_sha256"] = "unavailable"
    try:
        units = parse_decision_units(task)
        if classification is None:
            raise ContractError("Classification is unavailable")
        digest, synchronized = current_classification_input_digest(
            task, units, classification, events
        )
        facts["classification_input_sha256"] = digest
        facts["subject_synchronized"] = synchronized
    except AiflowError:
        facts["classification_input_sha256"] = "unavailable"
    if classification is not None:
        facts["verification_level"] = classification.get("effective_verification_level")
    subject = task.get("subject_commit")
    base = task.get("base_commit")
    governance_only = False
    if isinstance(subject, str) and isinstance(base, str):
        try:
            paths = collect_verification_changed_paths(
                repository_root,
                base_commit=base,
                subject_commit=subject,
                head_commit=observed_head,
            )
            governance_only = assess_governance_only_scope(
                (*paths.attestation, *paths.worktree),
                task_id=task_id,
                repository_root=repository_root,
            ).passed
        except AiflowError:
            governance_only = False
    facts["governance_only"] = governance_only
    facts["attestation_governance_only"] = governance_only
    return facts


def _artifact_digest(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _approval_status(
    repository_root: Path,
    task_id: str,
    current: dict[str, object],
    evidence: dict[str, Any] | None,
) -> str:
    path = resolve_task_path(repository_root, task_id, "approvals.json")
    if not path.is_file():
        return "not_available"
    try:
        value = read_task_json(repository_root, task_id, "approvals.json")
    except AiflowError:
        return "stale"
    if not isinstance(value, list) or not value:
        return "not_available"
    try:
        for approval in value:
            require_valid_contract("approval", approval)
    except ContractError:
        return "stale"
    approval_facts = dict(current)
    if evidence is not None:
        evidence_report = evaluate_freshness("evidence", evidence, current)
        approval_facts["evidence_sha256"] = _artifact_digest(evidence)
        approval_facts["evidence_current"] = evidence_report.status == "fresh"
    else:
        approval_facts["evidence_current"] = False
    relevant = [item for item in value if item.get("approval_type") != "action"]
    if not relevant:
        return "not_applicable"
    reports = [
        evaluate_freshness(
            "spec_approval" if item.get("approval_type") == "spec" else "code_approval",
            item,
            approval_facts,
        )
        for item in relevant
    ]
    return "current" if all(report.status == "fresh" for report in reports) else "stale"


def _evidence_status(value: dict[str, Any] | None, current: dict[str, object]) -> str:
    if value is None:
        return "not_available"
    report = evaluate_freshness("evidence", value, current)
    if report.status != "fresh":
        return "stale"
    return "passed"


def _read_evidence(repository_root: Path, task_id: str) -> tuple[dict[str, Any] | None, bool]:
    path = resolve_task_path(repository_root, task_id, "evidence.json")
    if not path.is_file():
        return None, False
    try:
        value = read_task_json(repository_root, task_id, "evidence.json", contract_name="evidence")
    except AiflowError:
        return None, True
    if not isinstance(value, dict):
        return None, True
    return value, False


def summarize_task(repository_root: Path, task_id: str) -> StatusSummary:
    """Build a status summary without changing task files or events."""
    record: TaskRecord = read_task_record_strict(repository_root, task_id)
    task = record.task
    context = collect_git_context(repository_root)
    state = str(task["current_state"])
    route, verification, classification, classification_invalid = _classification(
        repository_root, task_id
    )
    current = _current_facts(
        repository_root,
        task_id,
        task,
        observed_head=context.head,
        classification=classification,
        events=record.events,
    )
    classification_report = evaluate_freshness(
        "classification", classification, current, invalid=classification_invalid
    )
    evidence_value, evidence_invalid = _read_evidence(repository_root, task_id)
    evidence_status = "stale" if evidence_invalid else _evidence_status(evidence_value, current)
    next_events = tuple(
        sorted(
            rule.event_type for (source, _target), rule in TRANSITIONS.items() if source == state
        )
    )
    return StatusSummary(
        task_id=task_id,
        goal=str(task["goal"]),
        repository_id=str(task["repository_id"]),
        current_state=state,
        route=route,
        verification_level=verification,
        next_events=next_events,
        missing_conditions=MISSING_BY_STATE[state],
        base_commit=str(task["base_commit"]),
        subject_commit=str(task["subject_commit"]) if task.get("subject_commit") else None,
        observed_head=context.head,
        worktree_dirty=context.worktree_dirty,
        dirty_paths=context.dirty_paths,
        classification=classification_report.status,
        approvals=_approval_status(repository_root, task_id, current, evidence_value),
        evidence=evidence_status,
    )
