"""Read-only, non-scoring advisory explanations over native AI Flow outputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from aiflow.errors import AiflowError
from aiflow.gate import GateDecision, evaluate_gate
from aiflow.review_service import list_review_records
from aiflow.scope import assess_scope
from aiflow.status_service import StatusSummary, summarize_task
from aiflow.task_service import load_task_record

ADVISORY_SCHEMA_VERSION = "1.0"
ADVISORY_DESIGN_VERSION = "advisory-status-explanation-v0"
ADVISORY_MODE = "offline_advisory"
ADVISORY_PURPOSE = "offline_status_explanation"
ADVISORY_PROBABILITY_STATUS = "unestimated"

ADVICE_CATEGORIES = frozenset(
    {
        "continue_mechanical",
        "complete_machine_evidence",
        "repair_in_scope",
        "residual_human_decision",
        "retain_unknown",
        "stop_out_of_scope",
    }
)

_APPROVABLE_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS"})
_BLOCKING_SEVERITIES = frozenset({"critical", "high"})
_BLOCK_ESCALATION_EVENTS = frozenset(
    {
        "task_blocked",
        "verification_blocked",
        "classification_blocked",
        "task_escalated",
        "verification_escalated",
    }
)
_HUMAN_ESCALATION_REASONS = frozenset(
    {
        "directional_discovery",
        "new_permissions",
        "credentials_required",
        "task_description_changed",
        "policy_changed",
        "spec_changed",
    }
)


class _AdviceBuilder:
    """Collect ordered, deterministic advice items with sequential identifiers."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []
        self._seen: set[tuple[str, str]] = set()

    def add(
        self,
        *,
        category: str,
        condition: str,
        reason: str,
        suggested_next_step: str,
        evidence_refs: Sequence[str],
        requires_human: bool = False,
    ) -> None:
        if category not in ADVICE_CATEGORIES:
            raise ValueError(f"Unsupported advice category: {category}")
        dedupe_key = (category, condition)
        if dedupe_key in self._seen:
            return
        self._seen.add(dedupe_key)
        item_id = f"ADV-{len(self._items) + 1:03d}"
        self._items.append(
            {
                "item_id": item_id,
                "category": category,
                "condition": condition,
                "reason": reason,
                "suggested_next_step": suggested_next_step,
                "evidence_refs": list(dict.fromkeys(evidence_refs)),
                "requires_human": bool(requires_human),
            }
        )

    @property
    def items(self) -> list[dict[str, Any]]:
        return list(self._items)


def _latest_policy_sha256(events: Sequence[Mapping[str, Any]]) -> str | None:
    for event in reversed(events):
        payload = event.get("payload")
        if isinstance(payload, Mapping):
            digest = payload.get("policy_sha256")
            if isinstance(digest, str) and digest:
                return digest
    return None


def _latest_event(
    events: Sequence[Mapping[str, Any]], event_types: frozenset[str]
) -> Mapping[str, Any] | None:
    for event in reversed(events):
        if event.get("event_type") in event_types:
            return event
    return None


def _has_event_after(
    events: Sequence[Mapping[str, Any]], event_type: str, after_sequence: int
) -> bool:
    for event in events:
        sequence = event.get("sequence")
        if (
            event.get("event_type") == event_type
            and isinstance(sequence, int)
            and sequence > after_sequence
        ):
            return True
    return False


def _dirty_out_of_scope_paths(summary: StatusSummary, task: Mapping[str, Any]) -> tuple[str, ...]:
    if not summary.worktree_dirty or not summary.dirty_paths:
        return ()
    allowed_scope = task.get("allowed_scope")
    if (
        not isinstance(allowed_scope, list)
        or not allowed_scope
        or not all(isinstance(item, str) and item.strip() for item in allowed_scope)
    ):
        return tuple(summary.dirty_paths)
    try:
        assessment = assess_scope(summary.dirty_paths, allowed_scope, task_id=summary.task_id)
    except AiflowError:
        return tuple(summary.dirty_paths)
    return assessment.out_of_scope


def _stage_review_posture(
    reviews: Sequence[Mapping[str, Any]], stage: str
) -> tuple[str, list[str]]:
    stage_reviews = [item for item in reviews if item.get("review_stage") == stage]
    if not stage_reviews:
        return "missing", []
    refs = [
        f"reviews:{item.get('review_id')}-r{int(item.get('revision', 0)):04d}"
        for item in stage_reviews
    ]
    for item in stage_reviews:
        findings = item.get("findings")
        has_blocking_finding = isinstance(findings, list) and any(
            isinstance(finding, Mapping)
            and finding.get("status") == "open"
            and finding.get("severity") in _BLOCKING_SEVERITIES
            for finding in findings
        )
        if item.get("outcome") == "REQUEST_CHANGES" or has_blocking_finding:
            return "changes_requested", refs
    for item in stage_reviews:
        if item.get("outcome") in _APPROVABLE_OUTCOMES:
            return "approvable", refs
    return "not_approvable", refs


def _add_scope_and_boundary_advice(
    builder: _AdviceBuilder,
    summary: StatusSummary,
    dirty_oos: tuple[str, ...],
    gate_reason_codes: Sequence[str],
) -> None:
    if dirty_oos:
        preview = ", ".join(dirty_oos[:5])
        suffix = f" (+{len(dirty_oos) - 5} more)" if len(dirty_oos) > 5 else ""
        builder.add(
            category="stop_out_of_scope",
            condition="worktree_dirty_out_of_scope",
            reason=f"Dirty worktree paths lie outside allowed_scope: {preview}{suffix}.",
            suggested_next_step=(
                "Revert or relocate out-of-scope worktree changes, or escalate for an explicit "
                "scope change before proceeding."
            ),
            evidence_refs=["status:worktree_dirty", "task:allowed_scope"],
        )
    elif summary.worktree_dirty and not summary.dirty_paths:
        builder.add(
            category="retain_unknown",
            condition="worktree_dirty_paths_unknown",
            reason="Worktree is marked dirty but no dirty_paths list was provided to check scope.",
            suggested_next_step="Inspect git status to verify dirty files against allowed_scope.",
            evidence_refs=["status:worktree_dirty"],
        )

    if "GATE_SCOPE_OUT_OF_BOUNDS" in gate_reason_codes:
        builder.add(
            category="stop_out_of_scope",
            condition="GATE_SCOPE_OUT_OF_BOUNDS",
            reason="Native Gate reported out-of-bounds scope changes.",
            suggested_next_step=(
                "Stop progression on out-of-bounds paths and verify changes against allowed_scope."
            ),
            evidence_refs=["gate:GATE_SCOPE_OUT_OF_BOUNDS", "task:allowed_scope"],
        )
    elif "GATE_SCOPE_CHANGED" in gate_reason_codes and (
        not dirty_oos
        and (not summary.worktree_dirty or summary.current_state not in {"IMPLEMENTING", "FAILED"})
    ):
        builder.add(
            category="stop_out_of_scope",
            condition="GATE_SCOPE_CHANGED",
            reason=(
                "Native Gate rejected scope (GATE_SCOPE_CHANGED) against committed or "
                "governance-only boundaries."
            ),
            suggested_next_step=(
                "Inspect committed and worktree paths against allowed_scope and clean or "
                "re-scope before continuing."
            ),
            evidence_refs=["gate:GATE_SCOPE_CHANGED", "task:allowed_scope"],
        )

    if "GATE_REPOSITORY_CHANGED" in gate_reason_codes:
        builder.add(
            category="stop_out_of_scope",
            condition="GATE_REPOSITORY_CHANGED",
            reason=(
                "Current repository, branch, or HEAD ancestry diverges from the task's "
                "recorded Git binding."
            ),
            suggested_next_step=(
                "Switch back to the task's recorded branch and verify commit ancestry before "
                "taking any task action."
            ),
            evidence_refs=["gate:GATE_REPOSITORY_CHANGED", "status:observed_head"],
        )


def _add_status_gate_consistency_advice(
    builder: _AdviceBuilder,
    summary: StatusSummary,
    gate_decision: GateDecision | None,
    gate_error: AiflowError | None,
    *,
    frozen_spec_sha256: str | None,
) -> None:
    if gate_error is not None:
        if summary.current_state != "NEW":
            builder.add(
                category="complete_machine_evidence",
                condition="gate_evaluation_unavailable",
                reason=(
                    f"Status is {summary.current_state} ({summary.merge_readiness}), while native "
                    f"Gate could not evaluate ({gate_error.code}: {gate_error.message})."
                ),
                suggested_next_step=(
                    "Restore or regenerate missing/unreadable task artifacts required by Gate "
                    "without overriding native validation."
                ),
                evidence_refs=[f"status:{summary.current_state}", f"gate:{gate_error.code}"],
            )
        return

    assert gate_decision is not None
    codes = gate_decision.reason_codes
    readiness_mismatch = summary.current_state == "APPROVED_FOR_MERGE" and (
        (summary.merge_readiness == "gate_required" and not gate_decision.passed)
        or (
            summary.merge_readiness in {"not_ready", "reverification_required"}
            and gate_decision.passed
        )
    )
    non_merge_pass = summary.current_state != "APPROVED_FOR_MERGE" and gate_decision.passed
    route_mismatch = summary.route not in {"not_available", "stale"} and (
        summary.route != gate_decision.route
        or summary.verification_level != gate_decision.verification_level
    )
    code_approval_applicable = summary.current_state in {
        "WAITING_FOR_FINAL_REVIEW",
        "APPROVED_FOR_MERGE",
        "MERGED",
    }
    freshness_mismatch = (
        (summary.classification == "fresh" and "GATE_CLASSIFICATION_STALE" in codes)
        or (
            summary.evidence == "passed"
            and ("GATE_EVIDENCE_STALE" in codes or "GATE_EVIDENCE_NOT_PASSED" in codes)
        )
        or (
            summary.approvals == "current"
            and (
                "GATE_SPEC_APPROVAL_STALE" in codes
                or (code_approval_applicable and "GATE_CODE_APPROVAL_STALE" in codes)
            )
        )
    )
    unexpected_approved_reject = (
        summary.current_state == "APPROVED_FOR_MERGE"
        and not gate_decision.passed
        and any(
            code.startswith("GATE_V2_")
            or code in {"GATE_SPEC_STALE", "GATE_ASK_UNANSWERED", "GATE_ROUTE_INVALID"}
            for code in codes
        )
    )
    if (
        readiness_mismatch
        or non_merge_pass
        or route_mismatch
        or freshness_mismatch
        or unexpected_approved_reject
    ):
        reason_list = ", ".join(codes) or "none"
        builder.add(
            category="complete_machine_evidence",
            condition="status_gate_mismatch",
            reason=(
                f"Native status ({summary.current_state}, "
                f"merge_readiness={summary.merge_readiness}, "
                f"route={summary.route}/{summary.verification_level}, "
                f"freshness={summary.classification}/{summary.approvals}/{summary.evidence}) "
                f"differs from Gate (passed={gate_decision.passed}, "
                f"route={gate_decision.route}/{gate_decision.verification_level}, "
                f"reasons={reason_list})."
            ),
            suggested_next_step=(
                "Preserve both native outputs without overriding Gate; inspect and regenerate "
                "the discrepant machine bindings or evidence before proceeding."
            ),
            evidence_refs=["status:summary", "gate:decision"],
        )

    if (
        summary.classification == "stale"
        and summary.current_state not in {"NEW", "MERGED"}
        and "reverification" not in summary.missing_conditions
    ):
        builder.add(
            category="complete_machine_evidence",
            condition="classification_stale",
            reason="Persisted classification is stale relative to current task or Policy bindings.",
            suggested_next_step=(
                f"Re-evaluate classification with `aiflow classify {summary.task_id} "
                "--actor <ACTOR>`."
            ),
            evidence_refs=["status:classification", "task:classification.json"],
        )

    if (
        "GATE_SPEC_STALE" in codes
        and frozen_spec_sha256 is not None
        and "reverification" not in summary.missing_conditions
    ):
        builder.add(
            category="complete_machine_evidence",
            condition="GATE_SPEC_STALE",
            reason="Specification digest does not match task frozen_spec_sha256.",
            suggested_next_step=(
                f"Review spec changes and re-freeze with `aiflow freeze {summary.task_id} "
                "--actor <ACTOR>`."
            ),
            evidence_refs=["gate:GATE_SPEC_STALE", "task:spec.md"],
        )


def _add_review_advice(
    builder: _AdviceBuilder,
    task_id: str,
    reviews: Sequence[Mapping[str, Any]],
    stage: str,
) -> None:
    posture, refs = _stage_review_posture(reviews, stage)
    condition = f"{stage}_review"
    if posture == "changes_requested":
        builder.add(
            category="repair_in_scope",
            condition=condition,
            reason=f"Latest {stage} review requested changes or has open critical/high findings.",
            suggested_next_step=(
                f"Address open {stage} review findings in scope, resolve findings with "
                f"`aiflow review resolve {task_id} ...`, and record an updated {stage} review."
            ),
            evidence_refs=refs,
        )
    elif posture in {"missing", "not_approvable"}:
        builder.add(
            category="continue_mechanical",
            condition=condition,
            reason=f"No approvable {stage} review record is present yet.",
            suggested_next_step=(
                f"Build context via `aiflow review context {task_id} --stage {stage}` and "
                f"record an independent {stage} review via `aiflow review record {task_id} "
                "--input <FILE> --actor <ACTOR>`."
            ),
            evidence_refs=refs or [f"reviews:{stage}"],
        )


def _add_failed_advice(
    builder: _AdviceBuilder,
    summary: StatusSummary,
    record_events: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    dirty_oos: tuple[str, ...],
) -> None:
    task_id = summary.task_id
    failed_event = _latest_event(record_events, frozenset({"verification_failed"}))
    payload = failed_event.get("payload") if failed_event is not None else None
    has_event_detail = isinstance(payload, Mapping) and any(
        bool(payload.get(key))
        for key in ("reason", "failure_reason", "error", "failed_checks", "abandoned")
    )
    has_review_changes = any(item.get("outcome") == "REQUEST_CHANGES" for item in reviews)
    has_evidence = summary.evidence != "not_available" or has_event_detail or has_review_changes
    refs = ["status:FAILED", f"evidence:{summary.evidence}"]
    if failed_event is not None:
        refs.append(f"events:seq-{failed_event.get('sequence')}")

    if dirty_oos:
        return
    if has_evidence:
        builder.add(
            category="repair_in_scope",
            condition="retry_reason_or_escalation",
            reason=(
                "Task is FAILED with preserved verification/failure evidence "
                f"(evidence={summary.evidence})."
            ),
            suggested_next_step=(
                "Repair the verified failure within allowed_scope without erasing failure "
                f"records, then retry via `aiflow begin {task_id} --actor <ACTOR> --reason "
                "<REASON>` and re-verify, or escalate if scope/direction changed."
            ),
            evidence_refs=refs,
        )
    else:
        builder.add(
            category="retain_unknown",
            condition="retry_reason_or_escalation",
            reason=(
                "Task is FAILED but evidence.json and event failure details are absent, so the "
                "root cause remains unknown."
            ),
            suggested_next_step=(
                "Inspect or collect diagnostic verification evidence before retrying via "
                f"`aiflow begin {task_id} --actor <ACTOR> --reason <REASON>` or escalating."
            ),
            evidence_refs=refs,
        )


def _add_blocked_or_escalated_advice(
    builder: _AdviceBuilder,
    summary: StatusSummary,
    record_events: Sequence[Mapping[str, Any]],
    condition: str,
) -> None:
    task_id = summary.task_id
    block_event = _latest_event(record_events, _BLOCK_ESCALATION_EVENTS)
    if block_event is not None:
        sequence = block_event.get("sequence")
        if isinstance(sequence, int) and _has_event_after(
            record_events, "resolution_recorded", sequence
        ):
            builder.add(
                category="continue_mechanical",
                condition=condition,
                reason="A resolution_recorded event follows the latest block/escalation event.",
                suggested_next_step=(
                    f"Complete reclassification via `aiflow classify {task_id} --actor <ACTOR>`."
                ),
                evidence_refs=[f"events:seq-{sequence}", "events:resolution_recorded"],
            )
            return

    payload = block_event.get("payload") if block_event is not None else None
    reason_code = payload.get("reason_code") if isinstance(payload, Mapping) else None
    blocking_reasons = payload.get("blocking_reasons") if isinstance(payload, Mapping) else None
    next_step = payload.get("next_step") if isinstance(payload, Mapping) else None
    has_cause = (
        (isinstance(reason_code, str) and bool(reason_code.strip()))
        or (isinstance(blocking_reasons, list) and bool(blocking_reasons))
        or (isinstance(next_step, str) and bool(next_step.strip()))
    )
    refs = [f"status:{summary.current_state}"]
    if block_event is not None:
        refs.append(f"events:seq-{block_event.get('sequence')}")

    if not has_cause:
        builder.add(
            category="retain_unknown",
            condition=condition,
            reason=(
                f"Task is {summary.current_state} without a recorded reason_code or "
                "blocking_reasons in event history."
            ),
            suggested_next_step=(
                "Inspect task history to identify the missing block/escalation cause before "
                "recording a resolution."
            ),
            evidence_refs=refs,
        )
        return

    cause_label = (
        str(reason_code)
        if isinstance(reason_code, str) and reason_code.strip()
        else ", ".join(str(item) for item in blocking_reasons or [])
    )
    if (
        condition == "escalation_resolution"
        and isinstance(reason_code, str)
        and reason_code in _HUMAN_ESCALATION_REASONS
    ):
        builder.add(
            category="residual_human_decision",
            condition=condition,
            reason=(
                f"Task is ESCALATED for '{cause_label}', requiring an explicit human decision "
                "or authorization before resolution."
            ),
            suggested_next_step=(
                "Obtain the required decision and record it with "
                f"`aiflow resolve {task_id} --condition {cause_label} "
                "--evidence-ref <REF> --reason <REASON> --actor <ACTOR>`."
            ),
            evidence_refs=refs,
            requires_human=True,
        )
        return

    guidance = f" ({next_step})" if isinstance(next_step, str) and next_step.strip() else ""
    builder.add(
        category="repair_in_scope",
        condition=condition,
        reason=(
            f"Task is {summary.current_state} due to '{cause_label}'{guidance}; "
            "original block/escalation record remains preserved."
        ),
        suggested_next_step=(
            "Perform in-scope remediation and record evidence via "
            f"`aiflow resolve {task_id} --condition {cause_label or '<CONDITION>'} "
            "--evidence-ref <REF> --reason <REASON> --actor <ACTOR>`, then reclassify."
        ),
        evidence_refs=refs,
    )


def _add_reverification_advice(
    builder: _AdviceBuilder,
    summary: StatusSummary,
    gate_reason_codes: Sequence[str],
    dirty_oos: tuple[str, ...],
) -> None:
    task_id = summary.task_id
    added = False
    if summary.classification == "stale" or "GATE_CLASSIFICATION_STALE" in gate_reason_codes:
        builder.add(
            category="complete_machine_evidence",
            condition="classification_stale",
            reason="Classification is stale relative to current task or Policy bindings.",
            suggested_next_step=(
                f"Re-classify via `aiflow classify {task_id} --actor <ACTOR>` before reverifying."
            ),
            evidence_refs=["status:classification", "task:classification.json"],
        )
        added = True
    if (
        summary.subject_commit is not None
        and summary.observed_head != summary.subject_commit
        and not dirty_oos
        and "GATE_REPOSITORY_CHANGED" not in gate_reason_codes
    ):
        builder.add(
            category="continue_mechanical",
            condition="subject_sync",
            reason=(
                f"Observed HEAD ({summary.observed_head}) differs from recorded subject_commit "
                f"({summary.subject_commit})."
            ),
            suggested_next_step=(
                f"Synchronize the task subject via `aiflow sync {task_id} --actor <ACTOR>`."
            ),
            evidence_refs=["status:subject_commit", "status:observed_head"],
        )
        added = True
    if (
        summary.evidence != "passed"
        or "GATE_EVIDENCE_STALE" in gate_reason_codes
        or "GATE_EVIDENCE_NOT_PASSED" in gate_reason_codes
    ):
        builder.add(
            category="continue_mechanical",
            condition="reverification",
            reason=(
                f"Verification evidence requires refresh (evidence={summary.evidence}) for "
                "current bindings."
            ),
            suggested_next_step=(
                f"Run bounded verification via `aiflow verify {task_id} --actor <ACTOR>`."
            ),
            evidence_refs=["status:evidence", "task:evidence.json"],
        )
        added = True
    if (
        summary.approvals == "stale"
        or "GATE_SPEC_APPROVAL_STALE" in gate_reason_codes
        or "GATE_CODE_APPROVAL_STALE" in gate_reason_codes
    ):
        builder.add(
            category="residual_human_decision",
            condition="approval_revalidation",
            reason=(
                f"Approval coverage is stale ({summary.approvals}) and requires fresh "
                "version-bound approval once evidence is current."
            ),
            suggested_next_step=(
                f"After verification passes, record updated approval via `aiflow approve {task_id} "
                "--type <spec|code> --actor <ACTOR> --reason <REASON>` (standing_delegation "
                "applies only if eligible under Policy; advisory mode grants no authority)."
            ),
            evidence_refs=["status:approvals", "task:approvals.json"],
            requires_human=True,
        )
        added = True
    if not added:
        builder.add(
            category="complete_machine_evidence",
            condition="reverification",
            reason=(
                f"Merge readiness is {summary.merge_readiness}; native bindings require "
                "reverification before Gate evaluation."
            ),
            suggested_next_step=(
                f"Inspect stale bindings and run `aiflow verify {task_id} --actor <ACTOR>`."
            ),
            evidence_refs=["status:merge_readiness"],
        )


def _add_condition_advice(
    builder: _AdviceBuilder,
    summary: StatusSummary,
    record_events: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    gate_decision: GateDecision | None,
    gate_reason_codes: Sequence[str],
    dirty_oos: tuple[str, ...],
) -> None:
    task_id = summary.task_id
    if summary.current_state == "MERGED" and not summary.missing_conditions:
        builder.add(
            category="continue_mechanical",
            condition="merged",
            reason="Task is already in terminal state MERGED; no ledger transitions remain.",
            suggested_next_step="No further task ledger steps required (execution_allowed=false).",
            evidence_refs=["status:MERGED"],
        )
        return

    for condition in summary.missing_conditions:
        if condition in {"classification", "route_resolution"}:
            builder.add(
                category="continue_mechanical",
                condition=condition,
                reason=f"Task state {summary.current_state} requires native classification.",
                suggested_next_step=(
                    f"Record risk facts if needed (`aiflow facts {task_id} ...`) and run "
                    f"`aiflow classify {task_id} --actor <ACTOR>`."
                ),
                evidence_refs=[f"status:{condition}"],
            )
        elif condition == "ask_answer":
            builder.add(
                category="residual_human_decision",
                condition="ask_answer",
                reason="Task is WAITING_FOR_ASK and requires an explicit ASK option selection.",
                suggested_next_step=(
                    f"Provide the decision via `aiflow answer {task_id} --options-file <FILE> "
                    "--select <OPTION> --actor <ACTOR> --reason <REASON>`."
                ),
                evidence_refs=["status:ask_answer", "status:WAITING_FOR_ASK"],
                requires_human=True,
            )
        elif condition == "spec_frozen":
            has_ask = any(event.get("event_type") == "ask_answered" for event in record_events)
            builder.add(
                category="continue_mechanical",
                condition="spec_frozen",
                reason="Specification is not yet frozen with frozen_spec_sha256.",
                suggested_next_step=(
                    f"Run `aiflow freeze {task_id} --actor <ACTOR>`."
                    if has_ask
                    else f"Spec freezes automatically when `aiflow answer {task_id}` completes, "
                    f"or via `aiflow freeze {task_id} --actor <ACTOR>`."
                ),
                evidence_refs=["status:spec_frozen", "task:spec.md"],
            )
        elif condition == "spec_approval":
            _add_review_advice(builder, task_id, reviews, "design")
            builder.add(
                category="residual_human_decision",
                condition="spec_approval",
                reason=(
                    f"Route {summary.route} requires a valid version-bound spec approval "
                    f"(approvals={summary.approvals})."
                ),
                suggested_next_step=(
                    f"After design review APPROVE, record approval via `aiflow approve {task_id} "
                    "--type spec --actor <ACTOR> --reason <REASON>` (read-only note: "
                    "standing_delegation may be used only where Policy permits; advisory output "
                    "grants no permission)."
                ),
                evidence_refs=["status:spec_approval", "task:approvals.json"],
                requires_human=True,
            )
        elif condition == "begin":
            if summary.classification != "fresh":
                builder.add(
                    category="complete_machine_evidence",
                    condition="classification_freshness",
                    reason=(
                        f"Task is READY_TO_IMPLEMENT but classification is "
                        f"{summary.classification}."
                    ),
                    suggested_next_step=(
                        f"Refresh classification via `aiflow classify {task_id} --actor <ACTOR>` "
                        "before beginning."
                    ),
                    evidence_refs=["status:classification"],
                )
            elif summary.route == "REVIEW" and summary.approvals != "current":
                builder.add(
                    category="residual_human_decision",
                    condition="spec_approval",
                    reason=(
                        f"Task is READY_TO_IMPLEMENT under REVIEW route, but approval status is "
                        f"{summary.approvals}."
                    ),
                    suggested_next_step=(
                        f"Record fresh spec approval via `aiflow approve {task_id} --type spec "
                        "--actor <ACTOR> --reason <REASON>` before beginning."
                    ),
                    evidence_refs=["status:approvals", "task:approvals.json"],
                    requires_human=True,
                )
            elif not dirty_oos:
                builder.add(
                    category="continue_mechanical",
                    condition="begin",
                    reason=(
                        "Prerequisites for READY_TO_IMPLEMENT are satisfied; only mechanical "
                        "begin transition remains."
                    ),
                    suggested_next_step=(
                        f"Start implementation via `aiflow begin {task_id} --actor <ACTOR>`."
                    ),
                    evidence_refs=["status:READY_TO_IMPLEMENT", "status:begin"],
                )
        elif condition == "implementation_result":
            if dirty_oos:
                continue
            if summary.subject_commit is None or (
                summary.observed_head != summary.subject_commit and not summary.worktree_dirty
            ):
                builder.add(
                    category="continue_mechanical",
                    condition="subject_sync",
                    reason=(
                        "Committed HEAD differs from recorded subject_commit and should be "
                        "synchronized before final verification."
                    ),
                    suggested_next_step=(
                        f"Run `aiflow sync {task_id} --actor <ACTOR>` once in-scope commits "
                        "are ready."
                    ),
                    evidence_refs=["status:subject_commit", "status:observed_head"],
                )
            builder.add(
                category="continue_mechanical",
                condition="implementation_result",
                reason="Task is IMPLEMENTING within allowed_scope and awaits verification.",
                suggested_next_step=(
                    f"Complete in-scope edits, commit, synchronize if needed, and run "
                    f"`aiflow verify {task_id} --actor <ACTOR>`."
                ),
                evidence_refs=["status:IMPLEMENTING", "status:implementation_result"],
            )
        elif condition == "verification_result":
            builder.add(
                category="continue_mechanical",
                condition="verification_result",
                reason="Task is VERIFYING and awaits verification completion or finalization.",
                suggested_next_step=(
                    f"Complete or finalize verification via `aiflow verify {task_id} --finalize "
                    "--actor <ACTOR>` (or inspect interrupted run)."
                ),
                evidence_refs=["status:VERIFYING", "status:verification_result"],
            )
        elif condition == "final_route":
            if summary.route == "REVIEW":
                _add_review_advice(builder, task_id, reviews, "implementation")
            builder.add(
                category="continue_mechanical",
                condition="final_route",
                reason="Task is VERIFIED and awaits final routing transition.",
                suggested_next_step=(
                    f"Complete final verification routing via `aiflow verify {task_id} "
                    "--finalize --actor <ACTOR>`."
                ),
                evidence_refs=["status:VERIFIED", "status:final_route"],
            )
        elif condition == "implementation_review":
            _add_review_advice(builder, task_id, reviews, "implementation")
        elif condition == "finalization":
            builder.add(
                category="continue_mechanical",
                condition="finalization",
                reason="Implementation review is recorded; V2 verification finalization remains.",
                suggested_next_step=(
                    f"Finalize verification via `aiflow verify {task_id} --finalize "
                    "--actor <ACTOR>`."
                ),
                evidence_refs=["status:finalization", "task:evidence.json"],
            )
        elif condition == "code_approval":
            if summary.evidence == "awaiting_implementation_review_or_finalization":
                builder.add(
                    category="continue_mechanical",
                    condition="verification_finalization",
                    reason="V2 evidence is awaiting implementation review or finalization.",
                    suggested_next_step=(
                        f"Finalize V2 verification via `aiflow verify {task_id} --finalize "
                        "--actor <ACTOR>` before code approval."
                    ),
                    evidence_refs=["status:evidence", "task:evidence.json"],
                )
            elif summary.evidence != "passed":
                builder.add(
                    category="complete_machine_evidence",
                    condition="verification_evidence",
                    reason=(
                        f"Verification evidence is {summary.evidence}; passed evidence is "
                        "required before code approval."
                    ),
                    suggested_next_step=(
                        f"Run `aiflow verify {task_id} --actor <ACTOR>` to produce fresh "
                        "passed evidence."
                    ),
                    evidence_refs=["status:evidence", "task:evidence.json"],
                )
            _add_review_advice(builder, task_id, reviews, "implementation")
            builder.add(
                category="residual_human_decision",
                condition="code_approval",
                reason=(
                    f"Task is WAITING_FOR_FINAL_REVIEW under {summary.route} route and requires "
                    f"version-bound code approval (approvals={summary.approvals})."
                ),
                suggested_next_step=(
                    f"After verification and implementation review APPROVE, record approval via "
                    f"`aiflow approve {task_id} --type code --actor <ACTOR> --reason <REASON>` "
                    "(read-only note: standing_delegation applies only if Policy permits; "
                    "advisory output grants no permission)."
                ),
                evidence_refs=["status:code_approval", "task:approvals.json"],
                requires_human=True,
            )
        elif condition == "external_merge":
            if gate_decision is not None and gate_decision.passed:
                builder.add(
                    category="continue_mechanical",
                    condition="external_merge",
                    reason=(
                        "Merge readiness is satisfied under native Gate (gate_passed=true); "
                        "advisory mode keeps execution_allowed=false."
                    ),
                    suggested_next_step=(
                        "Complete the governed external merge (for example, PR merge commit) and "
                        f"then record closure via `aiflow close {task_id} --result merged "
                        "--merge-commit <SHA> --actor <ACTOR>`."
                    ),
                    evidence_refs=["status:APPROVED_FOR_MERGE", "gate:PASS"],
                )
            else:
                builder.add(
                    category="complete_machine_evidence",
                    condition="external_merge",
                    reason=("Status shows external_merge pending, but native Gate has not passed."),
                    suggested_next_step=(
                        "Resolve native Gate reason codes before performing any external merge."
                    ),
                    evidence_refs=["status:external_merge", "gate:REJECT"],
                )
        elif condition == "reverification":
            _add_reverification_advice(builder, summary, gate_reason_codes, dirty_oos)
        elif condition == "retry_reason_or_escalation":
            _add_failed_advice(builder, summary, record_events, reviews, dirty_oos)
        elif condition in {"block_resolution", "escalation_resolution"}:
            _add_blocked_or_escalated_advice(builder, summary, record_events, condition)
        else:
            builder.add(
                category="retain_unknown",
                condition=condition,
                reason=f"Unclassified native missing condition '{condition}'.",
                suggested_next_step=(
                    f"Inspect `aiflow status {task_id}` and `aiflow gate {task_id}` before taking "
                    "further action."
                ),
                evidence_refs=[f"status:{condition}"],
            )


def advise_task(repository_root: Path, task_id: str) -> dict[str, Any]:
    """Compose a strictly read-only, non-scoring advisory report from native services."""
    summary = summarize_task(repository_root, task_id)
    record = load_task_record(repository_root, task_id)
    reviews = list_review_records(repository_root, task_id)

    gate_decision: GateDecision | None = None
    gate_error: AiflowError | None = None
    try:
        gate_decision = evaluate_gate(repository_root, task_id)
    except AiflowError as error:
        gate_error = error

    frozen_spec_raw = record.task.get("frozen_spec_sha256")
    frozen_spec = frozen_spec_raw if isinstance(frozen_spec_raw, str) else None
    bindings = {
        "base_commit": summary.base_commit or None,
        "subject_commit": summary.subject_commit,
        "frozen_spec_sha256": frozen_spec,
        "policy_sha256": _latest_policy_sha256(record.events),
        "worktree_dirty": bool(summary.worktree_dirty),
    }

    gate_reason_codes = list(gate_decision.reason_codes) if gate_decision is not None else []
    native_constraints = {
        "missing_conditions": list(summary.missing_conditions),
        "gate_passed": gate_decision.passed if gate_decision is not None else None,
        "gate_reason_codes": gate_reason_codes,
        "classification_freshness": summary.classification,
        "approval_freshness": summary.approvals,
        "evidence_freshness": summary.evidence,
    }

    dirty_oos = _dirty_out_of_scope_paths(summary, record.task)
    builder = _AdviceBuilder()
    _add_scope_and_boundary_advice(builder, summary, dirty_oos, gate_reason_codes)
    _add_status_gate_consistency_advice(
        builder,
        summary,
        gate_decision,
        gate_error,
        frozen_spec_sha256=frozen_spec,
    )
    _add_condition_advice(
        builder,
        summary,
        record.events,
        reviews,
        gate_decision,
        gate_reason_codes,
        dirty_oos,
    )

    return {
        "schema_version": ADVISORY_SCHEMA_VERSION,
        "design_version": ADVISORY_DESIGN_VERSION,
        "mode": ADVISORY_MODE,
        "purpose": ADVISORY_PURPOSE,
        "probability_status": ADVISORY_PROBABILITY_STATUS,
        "execution_allowed": False,
        "permission_effect": "none",
        "ledger_effect": "none",
        "task_id": summary.task_id,
        "repository_id": summary.repository_id,
        "lifecycle_state": summary.current_state,
        "merge_readiness": summary.merge_readiness,
        "effective_route": summary.route,
        "effective_verification_level": summary.verification_level,
        "bindings": bindings,
        "native_constraints": native_constraints,
        "advice_items": builder.items,
    }


def format_advisory_text(report: Mapping[str, Any]) -> str:
    """Render an advisory report dict into concise, non-authorizing human-readable text."""
    constraints = report.get("native_constraints", {})
    bindings = report.get("bindings", {})
    gate_passed = constraints.get("gate_passed")
    gate_label = "NOT_EVALUATED" if gate_passed is None else ("PASS" if gate_passed else "REJECT")
    gate_reasons = ", ".join(constraints.get("gate_reason_codes", ())) or "none"
    missing = ", ".join(constraints.get("missing_conditions", ())) or "none"
    items = report.get("advice_items", ())

    lines = [
        f"Advisory: {report.get('task_id')} ({report.get('mode')} / {report.get('purpose')})",
        (
            f"State: {report.get('lifecycle_state')} | "
            f"Merge readiness: {report.get('merge_readiness')}"
        ),
        (
            f"Route / verification: {report.get('effective_route')} / "
            f"{report.get('effective_verification_level')}"
        ),
        (
            "Non-authorizing: "
            f"execution_allowed={str(bool(report.get('execution_allowed'))).lower()} | "
            f"permission_effect={report.get('permission_effect')} | "
            f"ledger_effect={report.get('ledger_effect')} | "
            f"probability_status={report.get('probability_status')}"
        ),
        f"Gate: {gate_label} (reasons: {gate_reasons})",
        f"Missing: {missing}",
        (
            "Freshness: "
            f"classification={constraints.get('classification_freshness')}, "
            f"approvals={constraints.get('approval_freshness')}, "
            f"evidence={constraints.get('evidence_freshness')}"
        ),
        (
            "Bindings: "
            f"base={bindings.get('base_commit')}, "
            f"subject={bindings.get('subject_commit')}, "
            f"spec={bindings.get('frozen_spec_sha256')}, "
            f"policy={bindings.get('policy_sha256')}, "
            f"worktree_dirty={str(bool(bindings.get('worktree_dirty'))).lower()}"
        ),
    ]
    if not items:
        lines.append("Advice items (0): none")
        return "\n".join(lines)
    lines.append(f"Advice items ({len(items)}):")
    for item in items:
        human_flag = str(bool(item.get("requires_human"))).lower()
        refs = ", ".join(item.get("evidence_refs", ())) or "none"
        lines.append(
            f"- [{item.get('item_id')}] {item.get('category')} ({item.get('condition')}) "
            f"[requires_human={human_flag}]: {item.get('reason')}"
        )
        lines.append(f"  Next: {item.get('suggested_next_step')}")
        lines.append(f"  Refs: {refs}")
    return "\n".join(lines)
