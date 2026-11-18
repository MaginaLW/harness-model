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
from aiflow.freshness import (
    V2_CODE_APPROVAL_FACTS,
    current_classification_input_digest,
    evaluate_freshness,
)
from aiflow.gate import classification_matches_policy, policy_v2_checks, v2_gate_facts
from aiflow.git_context import GitContext, collect_git_context, commits_are_ancestral
from aiflow.policy import is_node_policy, is_node_policy_candidate, load_policy_bundle
from aiflow.routing import ROUTE_ORDER
from aiflow.scope import (
    assess_governance_only_scope,
    assess_scope,
    collect_verification_changed_paths,
)
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
    merge_readiness: str
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
                f"Merge readiness: {self.merge_readiness}",
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
    if route not in ROUTE_ORDER or verification not in {"V0", "V1", "V2"}:
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
    context: GitContext | None = None,
    evidence: dict[str, Any] | None = None,
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
    facts["node_policy"] = True
    try:
        bundle = load_policy_bundle(repository_root)
        facts["policy_sha256"] = bundle.sha256
        candidate = is_node_policy_candidate(bundle.documents)
        facts["node_policy"] = candidate
        if candidate and not is_node_policy(bundle):
            facts["policy_sha256"] = "unavailable"
        else:
            if classification is not None:
                try:
                    facts["classification_policy_current"] = classification_matches_policy(
                        task, classification, bundle
                    )
                except AiflowError:
                    facts["classification_policy_current"] = False
            if (
                not candidate
                and classification is not None
                and classification.get("effective_verification_level") == "V2"
            ):
                facts.update(dict.fromkeys(V2_CODE_APPROVAL_FACTS, False))
                if evidence is not None:
                    decision_unit_ids = sorted(
                        str(unit["decision_unit_id"])
                        for unit in task.get("decision_units", [])
                        if isinstance(unit, dict) and "decision_unit_id" in unit
                    )
                    facts.update(
                        v2_gate_facts(
                            repository_root,
                            task_id,
                            evidence,
                            events=events,
                            policy_checks=policy_v2_checks(bundle),
                            decision_unit_ids=decision_unit_ids,
                        )
                    )
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
    merge_scope_current = False
    if isinstance(subject, str) and isinstance(base, str):
        try:
            paths = collect_verification_changed_paths(
                repository_root,
                base_commit=base,
                subject_commit=subject,
                head_commit=observed_head,
                worktree_paths=getattr(context, "worktree_scope_paths", None),
            )
            governance_only = assess_governance_only_scope(
                (*paths.attestation, *paths.worktree),
                task_id=task_id,
                repository_root=repository_root,
            ).passed
            allowed_scope = task.get("allowed_scope")
            committed_scope_ok = (
                isinstance(allowed_scope, list)
                and all(isinstance(item, str) for item in allowed_scope)
                and assess_scope(
                    paths.committed,
                    tuple(allowed_scope),
                    task_id=task_id,
                    repository_root=repository_root,
                    cache_patterns=(),
                ).passed
            )
            merge_scope_current = committed_scope_ok and governance_only
        except AiflowError:
            governance_only = False
            merge_scope_current = False
    if context is not None and (
        getattr(context, "repository_id", None) is not None
        and getattr(context, "branch", None) is not None
    ):
        if isinstance(subject, str) and isinstance(base, str):
            try:
                facts["merge_repository_current"] = (
                    context.repository_id == task.get("repository_id")
                    and context.branch == task.get("branch")
                    and commits_are_ancestral(
                        repository_root,
                        base_commit=base,
                        subject_commit=subject,
                        head_commit=observed_head,
                    )
                )
            except AiflowError:
                facts["merge_repository_current"] = False
        else:
            facts["merge_repository_current"] = False
    facts["governance_only"] = governance_only
    facts["attestation_governance_only"] = governance_only
    facts["merge_scope_current"] = merge_scope_current
    return facts


def _artifact_digest(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _approval_status(
    repository_root: Path,
    task_id: str,
    current: dict[str, object],
    evidence: dict[str, Any] | None,
    *,
    classification: dict[str, Any] | None,
    state: str,
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
        approval_facts["evidence_sha256"] = _artifact_digest(evidence)
        approval_facts["evidence_current"] = _evidence_status(evidence, current) == "passed"
    else:
        approval_facts["evidence_current"] = False
    relevant = [item for item in value if item.get("approval_type") != "action"]
    if not relevant:
        return "not_applicable"
    if classification is None:
        return "stale"
    review_ids = {
        entry["decision_unit_id"]
        for entry in classification["classifications"]
        if entry["route"] == "REVIEW"
    }
    if not review_ids:
        return "not_applicable"
    required_types = {"spec"}
    if state in {"WAITING_FOR_FINAL_REVIEW", "APPROVED_FOR_MERGE", "MERGED"}:
        required_types.add("code")
    current_approvals: dict[str, set[str]] = {kind: set() for kind in required_types}
    for item in relevant:
        kind = item["approval_type"]
        if kind not in required_types:
            continue
        report = evaluate_freshness(
            "spec_approval" if item.get("approval_type") == "spec" else "code_approval",
            item,
            approval_facts,
        )
        if report.status == "fresh":
            current_approvals[kind].add(item["decision_unit_id"])
    # History is append-only. Like Gate, require fresh coverage per unit/type,
    # not freshness of records superseded by a later valid approval.
    return (
        "current"
        if all(review_ids.issubset(covered) for covered in current_approvals.values())
        else "stale"
    )


def _evidence_status(value: dict[str, Any] | None, current: dict[str, object]) -> str:
    if value is None:
        return "not_available"
    report = evaluate_freshness("evidence", value, current)
    if report.status != "fresh":
        return "stale"
    if (
        value.get("schema_version") in {"2.0", "3.2"}
        and value.get("verification_level") == "V2"
        and value.get("phase") == "pre_implementation_review"
    ):
        return "awaiting_implementation_review_or_finalization"
    if current.get("verification_level") == "V2" and any(
        current.get(key) is False for key in V2_CODE_APPROVAL_FACTS
    ):
        return "stale"
    return "passed"


def _merge_readiness(
    *,
    state: str,
    route: str,
    classification: str,
    approvals: str,
    evidence: str,
    policy_ready: bool = True,
    repository_ready: bool = True,
    scope_ready: bool = True,
) -> str:
    """Project an approved state's current merge posture without rewriting its history."""
    if state != "APPROVED_FOR_MERGE":
        return "not_applicable"
    if evidence == "awaiting_implementation_review_or_finalization":
        return "not_ready"
    current = (
        classification == "fresh"
        and evidence == "passed"
        and policy_ready
        and repository_ready
        and scope_ready
    )
    if route == "REVIEW":
        current = current and approvals == "current"
    return "gate_required" if current else "reverification_required"


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
    evidence_value, evidence_invalid = _read_evidence(repository_root, task_id)
    current = _current_facts(
        repository_root,
        task_id,
        task,
        observed_head=context.head,
        classification=classification,
        events=record.events,
        context=context,
        evidence=evidence_value,
    )
    classification_report = evaluate_freshness(
        "classification", classification, current, invalid=classification_invalid
    )
    classification_status = classification_report.status
    is_v2 = verification == "V2"
    node_v2 = current.get("node_policy") is True and is_v2
    if node_v2:
        current.update(dict.fromkeys(V2_CODE_APPROVAL_FACTS, False))
    elif is_v2:
        for key in V2_CODE_APPROVAL_FACTS:
            current.setdefault(key, False)
    if current.get("node_policy") is True and evidence_value is not None:
        from aiflow.node_execution import recheck_node_evidence

        node_facts = recheck_node_evidence(repository_root, task_id, evidence_value)
        current.update(
            node_evidence_current=node_facts.current,
            node_evidence_passed=node_facts.passed,
            node_evidence_sha256=node_facts.evidence_sha256,
            node_materials_sha256=node_facts.materials_sha256,
        )
        if node_v2 and node_facts.current and node_facts.passed:
            try:
                bundle = load_policy_bundle(repository_root)
                if is_node_policy(bundle) and bundle.policy_version == "3.2.0":
                    current.update(
                        v2_gate_facts(
                            repository_root,
                            task_id,
                            evidence_value,
                            events=record.events,
                            policy_checks=policy_v2_checks(bundle),
                            decision_unit_ids=sorted(
                                str(unit["decision_unit_id"]) for unit in task["decision_units"]
                            ),
                            node_facts=node_facts,
                        )
                    )
            except AiflowError:
                pass
    evidence_status = "stale" if evidence_invalid else _evidence_status(evidence_value, current)
    approval_status = _approval_status(
        repository_root,
        task_id,
        current,
        evidence_value,
        classification=classification,
        state=state,
    )
    merge_readiness = _merge_readiness(
        state=state,
        route=route,
        classification=classification_status,
        approvals=approval_status,
        evidence=evidence_status,
        policy_ready=current.get("classification_policy_current") is not False,
        repository_ready=current.get("merge_repository_current") is not False,
        scope_ready=current.get("merge_scope_current") is not False,
    )
    next_events = tuple(
        sorted(
            rule.event_type
            for (source, _target), rule in TRANSITIONS.items()
            if source == state
            and (
                rule.event_type != "code_approved"
                or not is_v2
                or all(current.get(key) is True for key in V2_CODE_APPROVAL_FACTS)
            )
        )
    )
    missing_conditions = MISSING_BY_STATE[state]
    if (
        evidence_status == "awaiting_implementation_review_or_finalization"
        and evidence_value is not None
    ):
        from aiflow.review_service import latest_review_assessment

        missing_conditions = ("implementation_review", "finalization")
        try:
            latest_review_assessment(
                repository_root,
                task_id,
                "implementation",
                decision_unit_ids=sorted(
                    str(unit["decision_unit_id"]) for unit in task["decision_units"]
                ),
                verification_snapshot_sha256=evidence_value["verification_snapshot_sha256"],
            )
        except ContractError:
            pass
        else:
            missing_conditions = ("finalization",)
    elif merge_readiness == "reverification_required":
        missing_conditions = ("reverification",)
    return StatusSummary(
        task_id=task_id,
        goal=str(task["goal"]),
        repository_id=str(task["repository_id"]),
        current_state=state,
        merge_readiness=merge_readiness,
        route=route,
        verification_level=verification,
        next_events=next_events,
        missing_conditions=missing_conditions,
        base_commit=str(task["base_commit"]),
        subject_commit=str(task["subject_commit"]) if task.get("subject_commit") else None,
        observed_head=context.head,
        worktree_dirty=context.worktree_dirty,
        dirty_paths=context.dirty_paths,
        classification=classification_status,
        approvals=approval_status,
        evidence=evidence_status,
    )
