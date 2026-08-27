"""Offline integration contracts for the Chapter 13.2 REVIEW/V2 self-hosting trial."""

from __future__ import annotations

import json
from pathlib import Path

from aiflow.evidence import finalize_v2_evidence, prepare_v2_pre_evidence, validate_v2_snapshot
from aiflow.gate import GateFacts, evaluate_gate_facts
from aiflow.observation import parse_observation
from aiflow.observation_decision import DecisionRoute, VerificationLevel, decide_observation
from aiflow.storage import read_task_json
from aiflow.task_service import load_task_record
from aiflow.verification import V2_CHECK_IDS

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "TASK-0025"
BASE_COMMIT = "7c0bfd807954df8be934d99c7e0a565e4fa2ddcb"
APPROVED_SUBJECT = "fe30565e669aa047088b0c25c085effeb2b4bdbc"
CLASSIFICATION_INPUT_SHA256 = "2d6cc68d05c4b89d0749700f71ddd98c1c3336cf7d227d59425af802c33e4bd4"
POLICY_SHA256 = "f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf"
SPEC_SHA256 = "04f951e922a1183b750111b101b9e47532c9bd9261225c289e6faa5237262318"
DESIGN_CONTEXT_SHA256 = "cbdf00194a21d792a13f7b14c75298b1cf1bff67a479feabe5a413c1876dc599"


def test_current_task_records_design_review_then_spec_approval_before_implementation() -> None:
    record = load_task_record(ROOT, TASK_ID)
    approvals = read_task_json(ROOT, TASK_ID, "approvals.json")
    classification = read_task_json(
        ROOT, TASK_ID, "classification.json", contract_name="classification"
    )
    review = read_task_json(
        ROOT,
        TASK_ID,
        Path("reviews") / "REV-0046-r0001.json",
        contract_name="review-record",
    )

    assert isinstance(approvals, list)
    assert isinstance(classification, dict)
    assert isinstance(review, dict)
    assert classification["classification_input_sha256"] == CLASSIFICATION_INPUT_SHA256
    assert classification["policy_sha256"] == POLICY_SHA256
    assert classification["effective_route"] == "REVIEW"
    assert classification["effective_verification_level"] == "V2"
    assert review["review_stage"] == "design"
    assert review["outcome"] == "APPROVE"
    assert review["context_sha256"] == DESIGN_CONTEXT_SHA256
    assert all(finding["status"] == "resolved" for finding in review["findings"])

    current_approvals = [
        approval
        for approval in approvals
        if approval["approval_type"] == "spec"
        and approval["spec_sha256"] == SPEC_SHA256
        and approval["policy_sha256"] == POLICY_SHA256
    ]
    assert len(current_approvals) == 1
    current_approval = current_approvals[0]
    assert current_approval["task_id"] == TASK_ID
    assert current_approval["decision_unit_id"] == "DU-001"
    assert current_approval["base_commit"] == BASE_COMMIT
    assert current_approval["subject_commit"] == APPROVED_SUBJECT
    assert CLASSIFICATION_INPUT_SHA256 in current_approval["reason"]

    frozen_event = next(
        event
        for event in record.events
        if event["event_type"] == "spec_frozen" and event["payload"]["spec_sha256"] == SPEC_SHA256
    )
    review_event = next(
        event
        for event in record.events
        if event["event_type"] == "review_recorded" and event["payload"]["review_id"] == "REV-0046"
    )
    approval_event = next(
        event
        for event in record.events
        if event["event_type"] == "spec_approved"
        and event["payload"]["structured_review"]["review_id"] == "REV-0046"
    )
    implementation_event = next(
        event
        for event in reversed(record.events)
        if event["event_type"] == "implementation_started"
        and event["sequence"] > approval_event["sequence"]
    )

    expected_review_binding = {
        "context_sha256": DESIGN_CONTEXT_SHA256,
        "review_id": "REV-0046",
        "review_stage": "design",
        "revision": 1,
    }
    assert review_event["payload"] == expected_review_binding
    assert approval_event["payload"]["structured_review"] == expected_review_binding
    assert approval_event["payload"]["approvals"] == [current_approval]
    assert (
        frozen_event["sequence"]
        < review_event["sequence"]
        < approval_event["sequence"]
        < implementation_event["sequence"]
    )


def test_v2_snapshot_finalization_binds_implementation_review_without_mutating_checks() -> None:
    """Finalize is a pure second review phase; it cannot change verification facts."""
    source = json.loads(
        (ROOT / "tests" / "fixtures" / "contracts" / "valid" / "evidence-v2.json").read_text(
            encoding="utf-8"
        )
    )
    source.pop("phase")
    source.pop("verification_snapshot_sha256")
    by_id = {check["check_id"]: check for check in source["checks"]}
    source["checks"] = [
        dict(
            by_id.get(
                identifier,
                {
                    "check_id": identifier,
                    "category": identifier,
                    "status": "passed",
                    "reason_code": None,
                    "required": True,
                    "exit_code": 0,
                    "timed_out": False,
                    "duration_ms": 0,
                    "stdout_log_ref": None,
                    "stderr_log_ref": None,
                    "command_summary": identifier,
                    "tool_version": "offline-test",
                },
            )
        )
        for identifier in V2_CHECK_IDS
    ]
    pre = prepare_v2_pre_evidence(source)
    finalized = finalize_v2_evidence(pre, {"review_id": "REV-9999", "context_sha256": "f" * 64})

    validate_v2_snapshot(finalized)
    assert finalized["phase"] == "final"
    assert finalized["verification_snapshot_sha256"] == pre["verification_snapshot_sha256"]
    assert finalized["checks"] == pre["checks"]
    assert finalized["review_refs"]["implementation"]["review_id"] == "REV-9999"


def test_v2_gate_requires_all_current_final_review_and_approval_facts() -> None:
    baseline = GateFacts(
        task_id=TASK_ID,
        current_state="APPROVED_FOR_MERGE",
        route="REVIEW",
        verification_level="V2",
        review_required=True,
    )
    assert evaluate_gate_facts(baseline).passed is True

    for field, expected_reason in (
        ("v2_final_evidence", "GATE_V2_EVIDENCE_NOT_FINAL"),
        ("v2_snapshot_current", "GATE_V2_SNAPSHOT_STALE"),
        ("v2_verifier_independent", "GATE_V2_VERIFIER_NOT_INDEPENDENT"),
        ("v2_reviews_current", "GATE_V2_REVIEW_STALE"),
        ("v2_checks_current", "GATE_V2_CHECKS_INCOMPLETE"),
        ("v2_mutation_killed", "GATE_V2_MUTATION_NOT_KILLED"),
        ("code_approval_current", "GATE_CODE_APPROVAL_STALE"),
    ):
        facts = GateFacts(**{**baseline.__dict__, field: False})
        assert expected_reason in evaluate_gate_facts(facts).reason_codes


def test_supported_hook_cli_ci_observations_have_the_same_non_authorizing_decision() -> None:
    decisions = []
    for source in ("hook_pre_commit", "hook_pre_command", "cli", "ci"):
        observation = parse_observation(
            {
                "schema_version": "1.0",
                "task_id": TASK_ID,
                "base_commit": "a" * 40,
                "subject_commit": "b" * 40,
                "policy_sha256": "c" * 64,
                "source": source,
                "kind": "high_risk_command",
                "summary": {"action": "push", "target_ref": "origin/main"},
            }
        )
        result = decide_observation(observation, DecisionRoute.REVIEW, VerificationLevel.V2)
        decisions.append(
            (
                result.disposition.value,
                result.reason_code.value,
                result.execution_allowed,
                tuple(result.required_conditions),
            )
        )

    assert decisions == [decisions[0]] * 4
    assert decisions[0][2] is False
