"""Strictly read-only task status summaries."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import AiflowError, ContractError, StorageError
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
from aiflow.state import ALL_STATES, TRANSITIONS
from aiflow.storage import TASK_ID_PATTERN, read_task_json, resolve_task_path, task_root
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


@dataclass(frozen=True)
class TaskListEntry:
    """Summary of one materialized AI Flow task in ``aiflow list``."""

    task_id: str
    current_state: str
    goal: str
    branch: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of one task entry."""
        return asdict(self)


@dataclass(frozen=True)
class TaskListReport:
    """Strictly read-only listing of local AI Flow tasks and directory anomalies."""

    repository_id: str
    include_merged: bool
    states: tuple[str, ...]
    counts_by_state: dict[str, int]
    tasks: tuple[TaskListEntry, ...]
    incomplete_tasks: tuple[str, ...]
    logs_only_tasks: tuple[str, ...]
    schema_version: str = "1.0"
    kind: str = "aiflow-task-list"

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic dictionary representation of the task listing."""
        ordered_counts = dict(sorted(self.counts_by_state.items()))
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "repository_id": self.repository_id,
            "include_merged": self.include_merged,
            "states": list(self.states),
            "total_tasks": sum(ordered_counts.values()),
            "matched_tasks": len(self.tasks),
            "counts_by_state": ordered_counts,
            "tasks": [entry.to_dict() for entry in self.tasks],
            "incomplete_tasks": list(self.incomplete_tasks),
            "logs_only_tasks": list(self.logs_only_tasks),
        }

    def to_json(self) -> str:
        """Serialize the task listing report to canonical ASCII-escaped JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=True, sort_keys=True)

    def to_text(self) -> str:
        """Format a human-readable summary of listed tasks."""
        ordered_counts = dict(sorted(self.counts_by_state.items()))
        counts_text = (
            ", ".join(f"{state}={count}" for state, count in ordered_counts.items()) or "none"
        )
        lines = [
            f"Repository: {self.repository_id}",
            f"Tasks: {len(self.tasks)} shown ({sum(ordered_counts.values())} total)",
            f"Counts by state: {counts_text}",
        ]
        if self.tasks:
            for entry in self.tasks:
                lines.append(
                    f"- {entry.task_id} [{entry.current_state}] ({entry.branch}) {entry.goal}"
                )
        else:
            lines.append("No matching tasks.")
        if self.incomplete_tasks:
            lines.append(f"Incomplete tasks: {', '.join(self.incomplete_tasks)}")
        if self.logs_only_tasks:
            lines.append(f"Logs-only tasks: {', '.join(self.logs_only_tasks)}")
        return "\n".join(lines)


def _is_reparse_or_symlink(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _require_plain_dir(path: Path, *, message: str, task_id: str | None = None) -> None:
    try:
        info = path.lstat()
    except OSError as error:
        raise StorageError(
            message,
            code="STORAGE_READ_FAILED",
            details={"task_id": task_id} if task_id is not None else {},
        ) from error
    if _is_reparse_or_symlink(info) or not stat.S_ISDIR(info.st_mode):
        raise StorageError(
            message,
            code="STORAGE_READ_FAILED",
            details={"task_id": task_id} if task_id is not None else {},
        )


def _validate_list_filters(
    states: Sequence[str] | None, *, include_merged: bool
) -> tuple[str, ...]:
    if isinstance(states, str):
        raise ContractError(
            "Task state filter must be a sequence of state names",
            code="TASK_LIST_FILTER_INVALID",
            details={"states": states},
        )
    normalized = tuple(dict.fromkeys(states or ()))
    unknown = [state for state in normalized if state not in ALL_STATES]
    if unknown:
        raise ContractError(
            "Task list filter contains an unknown state",
            code="TASK_LIST_FILTER_INVALID",
            details={"states": unknown},
        )
    if include_merged and normalized:
        raise ContractError(
            "Cannot combine include_merged with explicit state filters",
            code="TASK_LIST_FILTER_INVALID",
            details={"states": list(normalized)},
        )
    return normalized


def list_tasks(
    repository_root: Path,
    *,
    states: Sequence[str] | None = None,
    include_merged: bool = False,
) -> TaskListReport:
    """Scan ``.ai/tasks/`` strictly read-only and summarize governed tasks."""
    normalized_states = _validate_list_filters(states, include_merged=include_merged)
    repository_id = collect_git_context(repository_root).repository_id

    lexical_tasks_root = repository_root / ".ai" / "tasks"
    try:
        root_info = lexical_tasks_root.lstat()
    except FileNotFoundError:
        task_root(repository_root)
        return TaskListReport(
            repository_id=repository_id,
            include_merged=include_merged,
            states=normalized_states,
            counts_by_state={},
            tasks=(),
            incomplete_tasks=(),
            logs_only_tasks=(),
        )
    except OSError as error:
        raise StorageError("Could not inspect task root", code="STORAGE_READ_FAILED") from error

    if _is_reparse_or_symlink(root_info) or not stat.S_ISDIR(root_info.st_mode):
        raise StorageError("Task root must be a plain directory", code="STORAGE_READ_FAILED")
    tasks_dir = task_root(repository_root)

    try:
        entries = sorted(tasks_dir.iterdir(), key=lambda item: item.name)
    except OSError as error:
        raise StorageError("Could not list task root", code="STORAGE_READ_FAILED") from error

    counts_by_state: dict[str, int] = {}
    matched_entries: list[TaskListEntry] = []
    incomplete_tasks: list[str] = []
    logs_only_tasks: list[str] = []
    state_filter = set(normalized_states)

    for entry in entries:
        if TASK_ID_PATTERN.fullmatch(entry.name) is None:
            continue
        task_id = entry.name
        _require_plain_dir(entry, message="Task entry must be a plain directory", task_id=task_id)
        try:
            children = sorted(entry.iterdir(), key=lambda item: item.name)
        except OSError as error:
            raise StorageError(
                "Could not read task directory",
                code="STORAGE_READ_FAILED",
                details={"task_id": task_id},
            ) from error
        child_names = {child.name: child for child in children}

        if any(name in child_names for name in ("task.yaml", "events.jsonl", "task.yaml.next")):
            record = read_task_record_strict(repository_root, task_id)
            task = record.task
            state = str(task["current_state"])
            counts_by_state[state] = counts_by_state.get(state, 0) + 1
            include = (
                state in state_filter if state_filter else (include_merged or state != "MERGED")
            )
            if include:
                matched_entries.append(
                    TaskListEntry(
                        task_id=task_id,
                        current_state=state,
                        goal=str(task["goal"]),
                        branch=str(task["branch"]),
                        created_at=str(task["created_at"]),
                        updated_at=str(task["updated_at"]),
                    )
                )
        elif "creation_failed.json" in child_names:
            marker_path = child_names["creation_failed.json"]
            try:
                marker_info = marker_path.lstat()
            except OSError as error:
                raise StorageError(
                    "Could not inspect creation marker",
                    code="STORAGE_READ_FAILED",
                    details={"task_id": task_id},
                ) from error
            if _is_reparse_or_symlink(marker_info) or not stat.S_ISREG(marker_info.st_mode):
                raise StorageError(
                    "Creation marker must be a plain file",
                    code="STORAGE_READ_FAILED",
                    details={"task_id": task_id},
                )
            marker = read_task_json(repository_root, task_id, "creation_failed.json")
            if not isinstance(marker, dict):
                raise StorageError(
                    "Creation marker must be a JSON object",
                    code="STORAGE_PARSE_FAILED",
                    details={"task_id": task_id},
                )
            incomplete_tasks.append(task_id)
        elif not children or (len(children) == 1 and children[0].name == "logs"):
            if children:
                _require_plain_dir(
                    children[0],
                    message="Task logs entry must be a plain directory",
                    task_id=task_id,
                )
            logs_only_tasks.append(task_id)
        else:
            raise StorageError(
                "Task directory is incomplete or contains unexpected entries",
                code="STORAGE_READ_FAILED",
                details={"task_id": task_id},
            )

    return TaskListReport(
        repository_id=repository_id,
        include_merged=include_merged,
        states=normalized_states,
        counts_by_state=dict(sorted(counts_by_state.items())),
        tasks=tuple(matched_entries),
        incomplete_tasks=tuple(incomplete_tasks),
        logs_only_tasks=tuple(logs_only_tasks),
    )
