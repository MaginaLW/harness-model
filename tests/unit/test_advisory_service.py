"""Unit tests for the read-only non-scoring advisory service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aiflow import advisory_service
from aiflow.advisory_service import (
    ADVICE_CATEGORIES,
    advise_task,
    format_advisory_text,
)
from aiflow.errors import StorageError
from aiflow.gate import GateDecision
from aiflow.status_service import StatusSummary
from aiflow.task_service import TaskRecord

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
HASH_SPEC = "c" * 64
HASH_POLICY = "d" * 64
REPO_ID = "123e4567-e89b-42d3-a456-426614174000"


def _summary(**overrides: Any) -> StatusSummary:
    base: dict[str, Any] = {
        "task_id": "TASK-0001",
        "goal": "Bounded advisory test",
        "repository_id": REPO_ID,
        "current_state": "IMPLEMENTING",
        "merge_readiness": "not_applicable",
        "route": "REVIEW",
        "verification_level": "V1",
        "next_events": ("verification_started",),
        "missing_conditions": ("implementation_result",),
        "base_commit": COMMIT_A,
        "subject_commit": COMMIT_A,
        "observed_head": COMMIT_A,
        "worktree_dirty": False,
        "dirty_paths": (),
        "classification": "fresh",
        "approvals": "current",
        "evidence": "not_available",
    }
    base.update(overrides)
    return StatusSummary(**base)


def _record(
    *,
    allowed_scope: list[str] | None = None,
    frozen_spec_sha256: str | None = HASH_SPEC,
    events: tuple[dict[str, Any], ...] | None = None,
) -> TaskRecord:
    task: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "allowed_scope": ["src/aiflow/**"] if allowed_scope is None else allowed_scope,
    }
    if frozen_spec_sha256 is not None:
        task["frozen_spec_sha256"] = frozen_spec_sha256
    default_events = (
        {
            "sequence": 1,
            "event_type": "task_created",
            "payload": {"objective": "Bounded advisory test"},
        },
        {
            "sequence": 2,
            "event_type": "classification_recorded",
            "payload": {"policy_sha256": HASH_POLICY},
        },
    )
    return TaskRecord(task=task, events=default_events if events is None else events)


def _gate(
    *,
    passed: bool = False,
    route: str = "REVIEW",
    verification_level: str = "V1",
    reason_codes: tuple[str, ...] = ("GATE_STATE_INVALID",),
) -> GateDecision:
    return GateDecision(
        task_id="TASK-0001",
        passed=passed,
        route=route,
        verification_level=verification_level,
        reason_codes=reason_codes,
        recovery_argv=(),
    )


def _patch_native(
    monkeypatch: pytest.MonkeyPatch,
    *,
    summary: StatusSummary,
    record: TaskRecord | None = None,
    reviews: tuple[dict[str, Any], ...] = (),
    gate: GateDecision | Exception | None = None,
) -> None:
    monkeypatch.setattr(advisory_service, "summarize_task", lambda _r, _t: summary)
    monkeypatch.setattr(
        advisory_service,
        "load_task_record",
        lambda _r, _t: record if record is not None else _record(),
    )
    monkeypatch.setattr(advisory_service, "list_review_records", lambda _r, _t: reviews)

    def fake_gate(_r: Path, _t: str) -> GateDecision:
        if isinstance(gate, Exception):
            raise gate
        return gate if gate is not None else _gate()

    monkeypatch.setattr(advisory_service, "evaluate_gate", fake_gate)


def _assert_non_authorizing_invariants(report: dict[str, Any]) -> None:
    assert report["schema_version"] == "1.0"
    assert report["design_version"] == "advisory-status-explanation-v0"
    assert report["mode"] == "offline_advisory"
    assert report["purpose"] == "offline_status_explanation"
    assert report["probability_status"] == "unestimated"
    assert report["execution_allowed"] is False
    assert report["permission_effect"] == "none"
    assert report["ledger_effect"] == "none"
    for item in report["advice_items"]:
        assert item["category"] in ADVICE_CATEGORIES
        assert isinstance(item["requires_human"], bool)


def test_mechanical_states_and_bindings_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # NEW state with unavailable Gate and absent bindings
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="NEW",
            route="not_available",
            verification_level="not_available",
            missing_conditions=("classification",),
            base_commit="",
            subject_commit=None,
            classification="not_available",
            approvals="not_available",
            evidence="not_available",
        ),
        record=_record(
            frozen_spec_sha256=None, events=({"sequence": 1, "event_type": "task_created"},)
        ),
        gate=StorageError("missing classification", code="STORAGE_READ_FAILED"),
    )
    new_report = advise_task(tmp_path, "TASK-0001")
    _assert_non_authorizing_invariants(new_report)
    assert new_report["bindings"] == {
        "base_commit": None,
        "subject_commit": None,
        "frozen_spec_sha256": None,
        "policy_sha256": None,
        "worktree_dirty": False,
    }
    assert new_report["native_constraints"]["gate_passed"] is None
    assert [i["category"] for i in new_report["advice_items"]] == ["continue_mechanical"]
    assert new_report["advice_items"][0]["requires_human"] is False

    # CLASSIFIED, READY_TO_IMPLEMENT, IMPLEMENTING (with subject_sync), VERIFYING, VERIFIED, MERGED
    for state, missing, extra_summary in [
        ("CLASSIFIED", ("route_resolution",), {}),
        ("READY_TO_IMPLEMENT", ("begin",), {}),
        (
            "IMPLEMENTING",
            ("implementation_result",),
            {"observed_head": COMMIT_B, "worktree_dirty": False},
        ),
        ("VERIFYING", ("verification_result",), {}),
        ("VERIFIED", ("final_route",), {"route": "AUTO", "approvals": "not_applicable"}),
        ("VERIFIED", ("final_route",), {"route": "REVIEW", "approvals": "not_applicable"}),
        ("MERGED", (), {"approvals": "current", "evidence": "passed"}),
    ]:
        _patch_native(
            monkeypatch,
            summary=_summary(current_state=state, missing_conditions=missing, **extra_summary),
            gate=_gate(
                passed=False,
                route=extra_summary.get("route", "REVIEW"),
                reason_codes=("GATE_STATE_INVALID",),
            ),
        )
        rep = advise_task(tmp_path, "TASK-0001")
        _assert_non_authorizing_invariants(rep)
        assert all(item["category"] == "continue_mechanical" for item in rep["advice_items"])
        assert all(item["requires_human"] is False for item in rep["advice_items"])
        if state == "IMPLEMENTING":
            assert [i["condition"] for i in rep["advice_items"]] == [
                "subject_sync",
                "implementation_result",
            ]

    # APPROVED_FOR_MERGE with Gate PASS -> continue_mechanical & execution_allowed remains False
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="APPROVED_FOR_MERGE",
            merge_readiness="gate_required",
            missing_conditions=("external_merge",),
            evidence="passed",
        ),
        gate=_gate(passed=True, reason_codes=()),
    )
    approved_report = advise_task(tmp_path, "TASK-0001")
    _assert_non_authorizing_invariants(approved_report)
    assert approved_report["native_constraints"]["gate_passed"] is True
    assert approved_report["advice_items"][0]["category"] == "continue_mechanical"
    assert approved_report["advice_items"][0]["condition"] == "external_merge"


def test_human_decisions_and_review_postures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # WAITING_FOR_ASK before answer
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="WAITING_FOR_ASK",
            route="ASK",
            missing_conditions=("ask_answer", "spec_frozen"),
        ),
        gate=_gate(route="ASK"),
    )
    ask_report = advise_task(tmp_path, "TASK-0001")
    assert [
        (i["category"], i["condition"], i["requires_human"]) for i in ask_report["advice_items"]
    ] == [
        ("residual_human_decision", "ask_answer", True),
        ("continue_mechanical", "spec_frozen", False),
    ]

    # WAITING_FOR_ASK after ask_answered (spec_frozen only remaining)
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="WAITING_FOR_ASK",
            route="ASK",
            missing_conditions=("spec_frozen",),
        ),
        record=_record(
            events=(
                {
                    "sequence": 1,
                    "event_type": "ask_answered",
                    "payload": {"policy_sha256": HASH_POLICY},
                },
            )
        ),
        gate=_gate(route="ASK"),
    )
    ask_frozen = advise_task(tmp_path, "TASK-0001")
    assert "aiflow freeze" in ask_frozen["advice_items"][0]["suggested_next_step"]

    # WAITING_FOR_SPEC_REVIEW: missing design review -> continue_mechanical + human decision
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="WAITING_FOR_SPEC_REVIEW",
            missing_conditions=("spec_approval",),
            approvals="not_available",
        ),
        reviews=(),
    )
    spec_missing_rev = advise_task(tmp_path, "TASK-0001")
    assert [(i["category"], i["condition"]) for i in spec_missing_rev["advice_items"]] == [
        ("continue_mechanical", "design_review"),
        ("residual_human_decision", "spec_approval"),
    ]
    assert "standing_delegation" in spec_missing_rev["advice_items"][1]["suggested_next_step"]

    # WAITING_FOR_SPEC_REVIEW with open critical finding -> repair_in_scope + human decision
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="WAITING_FOR_SPEC_REVIEW",
            missing_conditions=("spec_approval",),
            approvals="not_available",
        ),
        reviews=(
            {
                "review_id": "REV-0001",
                "revision": 1,
                "review_stage": "design",
                "outcome": "APPROVE_WITH_CONDITIONS",
                "findings": [{"status": "open", "severity": "critical"}],
            },
        ),
    )
    spec_finding = advise_task(tmp_path, "TASK-0001")
    assert [(i["category"], i["condition"]) for i in spec_finding["advice_items"]] == [
        ("repair_in_scope", "design_review"),
        ("residual_human_decision", "spec_approval"),
    ]

    # WAITING_FOR_SPEC_REVIEW with APPROVE -> only residual_human_decision
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="WAITING_FOR_SPEC_REVIEW",
            missing_conditions=("spec_approval",),
            approvals="not_available",
        ),
        reviews=(
            {
                "review_id": "REV-0001",
                "revision": 1,
                "review_stage": "design",
                "outcome": "APPROVE",
                "findings": [],
            },
        ),
    )
    spec_ready = advise_task(tmp_path, "TASK-0001")
    assert [
        (i["category"], i["condition"], i["requires_human"]) for i in spec_ready["advice_items"]
    ] == [("residual_human_decision", "spec_approval", True)]

    # WAITING_FOR_FINAL_REVIEW with stale evidence and non-approvable review outcome
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="WAITING_FOR_FINAL_REVIEW",
            missing_conditions=("code_approval",),
            evidence="stale",
            approvals="not_available",
        ),
        reviews=(
            {
                "review_id": "REV-0002",
                "revision": 1,
                "review_stage": "implementation",
                "outcome": "COMMENT_ONLY",
                "findings": [],
            },
        ),
    )
    final_rev = advise_task(tmp_path, "TASK-0001")
    assert [(i["category"], i["condition"]) for i in final_rev["advice_items"]] == [
        ("complete_machine_evidence", "verification_evidence"),
        ("continue_mechanical", "implementation_review"),
        ("residual_human_decision", "code_approval"),
    ]

    # WAITING_FOR_FINAL_REVIEW with V2 awaiting finalization + READY_TO_IMPLEMENT stale approval
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="WAITING_FOR_FINAL_REVIEW",
            missing_conditions=("code_approval",),
            evidence="awaiting_implementation_review_or_finalization",
            approvals="not_available",
        ),
        reviews=(
            {
                "review_id": "REV-0002",
                "revision": 1,
                "review_stage": "implementation",
                "outcome": "APPROVE",
                "findings": [],
            },
        ),
    )
    v2_final = advise_task(tmp_path, "TASK-0001")
    assert v2_final["advice_items"][0]["condition"] == "verification_finalization"
    assert v2_final["advice_items"][1]["condition"] == "code_approval"

    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="READY_TO_IMPLEMENT",
            missing_conditions=("begin",),
            approvals="stale",
        ),
    )
    stale_ready = advise_task(tmp_path, "TASK-0001")
    assert stale_ready["advice_items"][0]["category"] == "residual_human_decision"


def test_failed_blocked_escalated_repair_and_unknown_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # FAILED with preserved evidence -> repair_in_scope
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="FAILED",
            missing_conditions=("retry_reason_or_escalation",),
            evidence="stale",
        ),
        record=_record(
            events=(
                {
                    "sequence": 1,
                    "event_type": "verification_failed",
                    "payload": {"conclusion": "failed"},
                },
            )
        ),
    )
    failed_actionable = advise_task(tmp_path, "TASK-0001")
    assert [(i["category"], i["condition"]) for i in failed_actionable["advice_items"]] == [
        ("repair_in_scope", "retry_reason_or_escalation")
    ]

    # FAILED without evidence or failure detail -> retain_unknown
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="FAILED",
            missing_conditions=("retry_reason_or_escalation",),
            evidence="not_available",
        ),
        record=_record(
            events=({"sequence": 1, "event_type": "verification_failed", "payload": {}},)
        ),
    )
    failed_unknown = advise_task(tmp_path, "TASK-0001")
    assert [(i["category"], i["condition"]) for i in failed_unknown["advice_items"]] == [
        ("retain_unknown", "retry_reason_or_escalation")
    ]

    # BLOCKED with reason_code -> repair_in_scope
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="BLOCKED",
            route="BLOCK",
            missing_conditions=("block_resolution",),
        ),
        record=_record(
            events=(
                {
                    "sequence": 3,
                    "event_type": "task_blocked",
                    "payload": {
                        "reason_code": "verification_unavailable",
                        "next_step": "restore test runner",
                    },
                },
            )
        ),
        gate=_gate(route="BLOCK", reason_codes=("GATE_BLOCKED", "GATE_STATE_INVALID")),
    )
    blocked_repair = advise_task(tmp_path, "TASK-0001")
    assert blocked_repair["advice_items"][0]["category"] == "repair_in_scope"

    # BLOCKED after resolution_recorded -> continue_mechanical
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="BLOCKED",
            route="BLOCK",
            missing_conditions=("block_resolution",),
        ),
        record=_record(
            events=(
                {
                    "sequence": 3,
                    "event_type": "task_blocked",
                    "payload": {"reason_code": "backup_invalid"},
                },
                {
                    "sequence": 4,
                    "event_type": "resolution_recorded",
                    "payload": {"reason": "fixed"},
                },
            )
        ),
        gate=_gate(route="BLOCK", reason_codes=("GATE_BLOCKED", "GATE_STATE_INVALID")),
    )
    blocked_resolved = advise_task(tmp_path, "TASK-0001")
    assert blocked_resolved["advice_items"][0]["category"] == "continue_mechanical"

    # BLOCKED with no cause -> retain_unknown
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="BLOCKED",
            route="BLOCK",
            missing_conditions=("block_resolution",),
        ),
        record=_record(events=()),
        gate=_gate(route="BLOCK", reason_codes=("GATE_BLOCKED", "GATE_STATE_INVALID")),
    )
    blocked_unknown = advise_task(tmp_path, "TASK-0001")
    assert blocked_unknown["advice_items"][0]["category"] == "retain_unknown"

    # ESCALATED with human reason -> residual_human_decision
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="ESCALATED",
            missing_conditions=("escalation_resolution",),
        ),
        record=_record(
            events=(
                {
                    "sequence": 3,
                    "event_type": "task_escalated",
                    "payload": {"reason_code": "directional_discovery"},
                },
            )
        ),
    )
    escalated_human = advise_task(tmp_path, "TASK-0001")
    assert escalated_human["advice_items"][0]["category"] == "residual_human_decision"
    assert escalated_human["advice_items"][0]["requires_human"] is True


def test_status_gate_mismatch_stale_reverification_and_misc_conditions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Status says gate_required, Gate says REJECT with V2/spec code -> preserve both outputs
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="APPROVED_FOR_MERGE",
            merge_readiness="gate_required",
            missing_conditions=("external_merge",),
            evidence="passed",
        ),
        gate=_gate(passed=False, reason_codes=("GATE_V2_MUTATION_NOT_KILLED",)),
    )
    mismatch = advise_task(tmp_path, "TASK-0001")
    categories = {item["condition"]: item["category"] for item in mismatch["advice_items"]}
    assert categories["status_gate_mismatch"] == "complete_machine_evidence"
    assert categories["external_merge"] == "complete_machine_evidence"
    assert mismatch["merge_readiness"] == "gate_required"
    assert mismatch["native_constraints"]["gate_passed"] is False
    assert mismatch["native_constraints"]["gate_reason_codes"] == ["GATE_V2_MUTATION_NOT_KILLED"]

    # Non-NEW task where Gate fails with StorageError -> gate_evaluation_unavailable
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="APPROVED_FOR_MERGE",
            merge_readiness="gate_required",
            missing_conditions=("external_merge",),
        ),
        gate=StorageError("missing spec", code="GATE_INPUT_INVALID"),
    )
    gate_err = advise_task(tmp_path, "TASK-0001")
    assert gate_err["advice_items"][0]["condition"] == "gate_evaluation_unavailable"
    assert gate_err["advice_items"][0]["category"] == "complete_machine_evidence"

    # Reverification with stale classification, moved HEAD, stale evidence, stale approvals
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="APPROVED_FOR_MERGE",
            merge_readiness="reverification_required",
            missing_conditions=("reverification",),
            observed_head=COMMIT_B,
            classification="stale",
            approvals="stale",
            evidence="stale",
        ),
        gate=_gate(
            passed=False,
            reason_codes=(
                "GATE_CLASSIFICATION_STALE",
                "GATE_EVIDENCE_STALE",
                "GATE_CODE_APPROVAL_STALE",
            ),
        ),
    )
    reverify = advise_task(tmp_path, "TASK-0001")
    assert [(i["category"], i["condition"]) for i in reverify["advice_items"]] == [
        ("complete_machine_evidence", "classification_stale"),
        ("continue_mechanical", "subject_sync"),
        ("continue_mechanical", "reverification"),
        ("residual_human_decision", "approval_revalidation"),
    ]

    # Reverification fallback, stale classification outside reverification, GATE_SPEC_STALE,
    # implementation_review, finalization, and unknown missing condition
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="READY_TO_IMPLEMENT",
            classification="stale",
            missing_conditions=("begin", "implementation_review", "finalization", "mystery_gap"),
        ),
        gate=_gate(passed=False, reason_codes=("GATE_STATE_INVALID", "GATE_SPEC_STALE")),
    )
    misc = advise_task(tmp_path, "TASK-0001")
    cond_to_cat = {i["condition"]: i["category"] for i in misc["advice_items"]}
    assert cond_to_cat["classification_stale"] == "complete_machine_evidence"
    assert cond_to_cat["GATE_SPEC_STALE"] == "complete_machine_evidence"
    assert cond_to_cat["classification_freshness"] == "complete_machine_evidence"
    assert cond_to_cat["implementation_review"] == "continue_mechanical"
    assert cond_to_cat["finalization"] == "continue_mechanical"
    assert cond_to_cat["mystery_gap"] == "retain_unknown"

    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="APPROVED_FOR_MERGE",
            merge_readiness="reverification_required",
            missing_conditions=("reverification",),
            classification="fresh",
            approvals="current",
            evidence="passed",
        ),
        gate=_gate(passed=False, reason_codes=("GATE_STATE_INVALID",)),
    )
    reverify_fallback = advise_task(tmp_path, "TASK-0001")
    assert reverify_fallback["advice_items"][0]["condition"] == "reverification"
    assert reverify_fallback["advice_items"][0]["category"] == "complete_machine_evidence"


def test_out_of_scope_dirty_paths_gate_codes_and_in_scope_implementing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Out-of-scope dirty worktree (>5 paths) -> stop_out_of_scope
    dirty = tuple(f"outside/file_{idx}.py" for idx in range(6))
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="READY_TO_IMPLEMENT",
            missing_conditions=("begin",),
            worktree_dirty=True,
            dirty_paths=dirty,
        ),
        gate=_gate(
            passed=False, reason_codes=("GATE_SCOPE_OUT_OF_BOUNDS", "GATE_REPOSITORY_CHANGED")
        ),
    )
    oos = advise_task(tmp_path, "TASK-0001")
    assert [i["category"] for i in oos["advice_items"]] == [
        "stop_out_of_scope",
        "stop_out_of_scope",
        "stop_out_of_scope",
    ]
    assert "(+1 more)" in oos["advice_items"][0]["reason"]

    # Dirty worktree with empty dirty_paths -> retain_unknown
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="IMPLEMENTING",
            missing_conditions=("implementation_result",),
            worktree_dirty=True,
            dirty_paths=(),
        ),
        gate=_gate(passed=False, reason_codes=("GATE_STATE_INVALID",)),
    )
    unknown_dirty = advise_task(tmp_path, "TASK-0001")
    assert unknown_dirty["advice_items"][0]["category"] == "retain_unknown"

    # Invalid allowed_scope with dirty_paths triggers conservative stop_out_of_scope
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="FAILED",
            missing_conditions=("retry_reason_or_escalation",),
            worktree_dirty=True,
            dirty_paths=("src/aiflow/cli.py",),
        ),
        record=_record(allowed_scope=[]),
        gate=_gate(passed=False, reason_codes=("GATE_SCOPE_CHANGED",)),
    )
    bad_scope = advise_task(tmp_path, "TASK-0001")
    assert bad_scope["advice_items"] == [
        {
            **bad_scope["advice_items"][0],
            "category": "stop_out_of_scope",
            "condition": "worktree_dirty_out_of_scope",
        }
    ]

    # In-scope dirty path during IMPLEMENTING must NOT emit stop_out_of_scope on GATE_SCOPE_CHANGED
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="IMPLEMENTING",
            missing_conditions=("implementation_result",),
            worktree_dirty=True,
            dirty_paths=("src/aiflow/cli.py",),
        ),
        gate=_gate(passed=False, reason_codes=("GATE_STATE_INVALID", "GATE_SCOPE_CHANGED")),
    )
    in_scope = advise_task(tmp_path, "TASK-0001")
    assert [i["category"] for i in in_scope["advice_items"]] == ["continue_mechanical"]

    # Clean worktree with GATE_SCOPE_CHANGED in APPROVED_FOR_MERGE -> stop_out_of_scope
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="APPROVED_FOR_MERGE",
            merge_readiness="reverification_required",
            missing_conditions=("reverification",),
            worktree_dirty=False,
        ),
        gate=_gate(passed=False, reason_codes=("GATE_SCOPE_CHANGED",)),
    )
    committed_oos = advise_task(tmp_path, "TASK-0001")
    assert committed_oos["advice_items"][0]["category"] == "stop_out_of_scope"
    assert committed_oos["advice_items"][0]["condition"] == "GATE_SCOPE_CHANGED"

    # IMPLEMENTING with out-of-scope dirty path skips implementation_result mechanical advice
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="IMPLEMENTING",
            missing_conditions=("implementation_result",),
            worktree_dirty=True,
            dirty_paths=("outside/file.py",),
        ),
        gate=_gate(passed=False, reason_codes=("GATE_STATE_INVALID", "GATE_SCOPE_CHANGED")),
    )
    impl_oos = advise_task(tmp_path, "TASK-0001")
    assert [i["category"] for i in impl_oos["advice_items"]] == ["stop_out_of_scope"]

    # WAITING_FOR_FINAL_REVIEW with passed evidence and APPROVE review -> code_approval only
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="WAITING_FOR_FINAL_REVIEW",
            missing_conditions=("code_approval",),
            evidence="passed",
            approvals="not_available",
        ),
        reviews=(
            {
                "review_id": "REV-0002",
                "revision": 1,
                "review_stage": "implementation",
                "outcome": "APPROVE",
                "findings": [],
            },
        ),
    )
    final_passed = advise_task(tmp_path, "TASK-0001")
    assert [(i["category"], i["condition"]) for i in final_passed["advice_items"]] == [
        ("residual_human_decision", "code_approval")
    ]

    # assess_scope raising AiflowError on malformed allowed_scope pattern falls back to dirty paths
    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="READY_TO_IMPLEMENT",
            missing_conditions=("begin",),
            worktree_dirty=True,
            dirty_paths=("src/aiflow/cli.py",),
        ),
        record=_record(allowed_scope=["/absolute/invalid"]),
        gate=_gate(passed=False, reason_codes=("GATE_STATE_INVALID",)),
    )
    err_scope = advise_task(tmp_path, "TASK-0001")
    assert err_scope["advice_items"][0]["category"] == "stop_out_of_scope"


def test_format_advisory_text_and_error_propagation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty_text = format_advisory_text(
        {
            "task_id": "TASK-0001",
            "mode": "offline_advisory",
            "purpose": "offline_status_explanation",
            "lifecycle_state": "NEW",
            "merge_readiness": "not_applicable",
            "effective_route": "not_available",
            "effective_verification_level": "not_available",
            "execution_allowed": False,
            "permission_effect": "none",
            "ledger_effect": "none",
            "probability_status": "unestimated",
            "bindings": {},
            "native_constraints": {"gate_passed": None},
            "advice_items": [],
        }
    )
    assert "Gate: NOT_EVALUATED" in empty_text
    assert "Advice items (0): none" in empty_text
    assert "execution_allowed=false" in empty_text

    _patch_native(
        monkeypatch,
        summary=_summary(
            current_state="APPROVED_FOR_MERGE",
            merge_readiness="gate_required",
            missing_conditions=("external_merge",),
            evidence="passed",
        ),
        gate=_gate(passed=True, reason_codes=()),
    )
    report = advise_task(tmp_path, "TASK-0001")
    rendered = format_advisory_text(report)
    assert "Gate: PASS" in rendered
    assert "[ADV-001] continue_mechanical (external_merge)" in rendered

    # Invalid category guard
    builder = advisory_service._AdviceBuilder()
    with pytest.raises(ValueError, match="Unsupported advice category"):
        builder.add(
            category="invalid",
            condition="x",
            reason="x",
            suggested_next_step="x",
            evidence_refs=[],
        )

    # Deduplication guard
    builder.add(
        category="continue_mechanical",
        condition="dup",
        reason="first",
        suggested_next_step="next",
        evidence_refs=["ref1", "ref1"],
    )
    builder.add(
        category="continue_mechanical",
        condition="dup",
        reason="second",
        suggested_next_step="next",
        evidence_refs=["ref2"],
    )
    assert len(builder.items) == 1
    assert builder.items[0]["evidence_refs"] == ["ref1"]

    # Invalid task error propagates from native status service
    monkeypatch.setattr(
        advisory_service,
        "summarize_task",
        lambda _r, _t: (_ for _ in ()).throw(
            StorageError("Missing task", code="STORAGE_READ_FAILED")
        ),
    )
    with pytest.raises(StorageError, match="Missing task"):
        advise_task(tmp_path, "TASK-9999")
