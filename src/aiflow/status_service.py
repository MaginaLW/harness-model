"""Strictly read-only task status summaries."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.git_context import collect_git_context
from aiflow.routing import ROUTE_ORDER
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
                f"Approvals / evidence: {self.approvals} / {self.evidence}",
            )
        )


def _classification(repository_root: Path, task_id: str) -> tuple[str, str]:
    path = resolve_task_path(repository_root, task_id, "classification.json")
    if not path.is_file():
        return "not_available", "not_available"
    value = read_task_json(
        repository_root, task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(value, dict):
        return "not_available", "not_available"
    route = value.get("effective_route")
    verification = value.get("effective_verification_level")
    if route not in ROUTE_ORDER or verification not in {"V0", "V1"}:
        return "not_available", "not_available"
    return str(route), str(verification)


def _approval_status(repository_root: Path, task_id: str, task: dict[str, Any]) -> str:
    path = resolve_task_path(repository_root, task_id, "approvals.json")
    if not path.is_file():
        return "not_available"
    value = read_task_json(repository_root, task_id, "approvals.json")
    if not isinstance(value, list) or not value:
        return "not_available"
    for approval in value:
        require_valid_contract("approval", approval)
    return (
        "current"
        if all(approval.get("subject_commit") == task.get("subject_commit") for approval in value)
        else "stale"
    )


def _evidence_status(repository_root: Path, task_id: str, task: dict[str, Any]) -> str:
    path = resolve_task_path(repository_root, task_id, "evidence.json")
    if not path.is_file():
        return "not_available"
    value = read_task_json(repository_root, task_id, "evidence.json", contract_name="evidence")
    if not isinstance(value, dict):
        return "stale"
    if value.get("repository_id") != task.get("repository_id") or value.get(
        "subject_commit"
    ) != task.get("subject_commit"):
        return "stale"
    return "passed" if value.get("conclusion") == "passed" else "failed"


def summarize_task(repository_root: Path, task_id: str) -> StatusSummary:
    """Build a status summary without changing task files or events."""
    record: TaskRecord = read_task_record_strict(repository_root, task_id)
    task = record.task
    context = collect_git_context(repository_root)
    state = str(task["current_state"])
    route, verification = _classification(repository_root, task_id)
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
        approvals=_approval_status(repository_root, task_id, task),
        evidence=_evidence_status(repository_root, task_id, task),
    )
