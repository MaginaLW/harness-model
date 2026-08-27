"""Offline Chapter 13.2 self-hosting contract scenarios.

These scenarios deliberately assemble evidence and use public validation helpers only.
They never create a mutation action, invoke the mutation runner, or perform a network
or repository write outside pytest's temporary state.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError
from aiflow.evidence import (
    decide_evidence_conclusion,
    finalize_v2_evidence,
    prepare_v2_pre_evidence,
    validate_v2_snapshot,
)
from aiflow.freshness import evaluate_freshness
from aiflow.gate import GateFacts, evaluate_gate_facts
from aiflow.review_service import validate_review_context, validate_review_record
from aiflow.scope import assess_scope
from aiflow.verification import V1_CHECK_IDS, V2_EXTRA_CHECK_IDS
from aiflow.verifier_service import (
    context_sha256,
    validate_verifier_actor,
    validate_verifier_context_current,
)

ROOT = Path(__file__).resolve().parents[2]
DESIGN_CONTEXT_SHA256 = "1833cc40e1f5a4bdd5e7ce59e2233965325dce8b30ecf1c94ddfa45586b790e7"


def _v2_evidence() -> dict[str, object]:
    """Build a contract-valid, offline V2 candidate with all fourteen checks."""
    fixture = ROOT / "tests" / "fixtures" / "contracts" / "valid" / "evidence-v2.json"
    value = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    template = value["checks"][0]
    assert isinstance(template, dict)
    value["checks"] = [
        {
            **template,
            "check_id": check_id,
            "category": check_id,
            "command_summary": "offline self-hosting contract",
        }
        for check_id in (*V1_CHECK_IDS, *V2_EXTRA_CHECK_IDS)
    ]
    return value


def test_offline_self_hosting_positive_contract_preserves_v2_snapshot() -> None:
    evidence = _v2_evidence()
    pre = prepare_v2_pre_evidence(evidence)
    final = finalize_v2_evidence(pre, {"review_id": "REV-0004", "context_sha256": "f" * 64})

    assert tuple(check["check_id"] for check in final["checks"]) == (
        *V1_CHECK_IDS,
        *V2_EXTRA_CHECK_IDS,
    )
    assert final["phase"] == "final"
    assert final["unverified_scenarios"] == []
    assert final["verification_snapshot_sha256"] == pre["verification_snapshot_sha256"]
    assert evaluate_gate_facts(
        GateFacts(
            task_id="TASK-SELF",
            current_state="APPROVED_FOR_MERGE",
            route="REVIEW",
            verification_level="V2",
            review_required=True,
        )
    ).passed


@pytest.mark.parametrize(
    ("implementer", "verifier", "reason_code"),
    [
        ("implementer", "implementer", "VERIFIER_ACTOR_NOT_INDEPENDENT"),
        ("implementer", "", "VERIFIER_ACTOR_REQUIRED"),
        ("", "verifier", "VERIFIER_IMPLEMENTER_MISSING"),
    ],
)
def test_same_or_empty_actor_is_rejected_before_runner(
    implementer: str, verifier: str, reason_code: str
) -> None:
    with pytest.raises(ContractError) as error:
        validate_verifier_actor(implementer, verifier)
    assert error.value.code == reason_code


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        ("survived", "failed"),
        ("missing", "unverified"),
        ("unexecuted", "unverified"),
        ("unknown", "unverified"),
    ],
)
def test_non_killed_or_missing_mutant_fails_evidence_and_gate(outcome: str, status: str) -> None:
    evidence = _v2_evidence()
    checks = evidence["checks"]
    assert isinstance(checks, list)
    targeted = next(check for check in checks if check["check_id"] == "targeted_mutation")
    targeted["status"] = status
    targeted["reason_code"] = f"MUTATION_{outcome.upper()}"

    assert decide_evidence_conclusion(checks, provisional=True, version_complete=True) == "failed"
    decision = evaluate_gate_facts(
        GateFacts(
            task_id="TASK-SELF",
            current_state="APPROVED_FOR_MERGE",
            route="REVIEW",
            verification_level="V2",
            review_required=True,
            v2_mutation_killed=False,
        )
    )
    assert decision.reason_codes == ("GATE_V2_MUTATION_NOT_KILLED",)


def test_missing_mutant_scope_overrun_and_tampered_snapshot_fail_closed() -> None:
    scope = assess_scope(
        ("tests/e2e/test_phase_02_self_hosting_scenario.py", "src/aiflow/forbidden.py"),
        ("tests/e2e/test_phase_02_self_hosting_scenario.py",),
        task_id="TASK-SELF",
    )
    assert scope.passed is False
    assert scope.out_of_scope == ("src/aiflow/forbidden.py",)

    pre = prepare_v2_pre_evidence(_v2_evidence())
    tampered = deepcopy(pre)
    tampered["subject_commit"] = "3" * 40
    with pytest.raises(ContractError, match="snapshot"):
        validate_v2_snapshot(tampered)


@pytest.mark.parametrize("stage", ["design", "implementation"])
def test_stale_or_tampered_review_fails_closed(stage: str) -> None:
    context = json.loads(
        (
            ROOT
            / ".ai"
            / "tasks"
            / "TASK-0025"
            / "review-contexts"
            / f"{DESIGN_CONTEXT_SHA256}.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(context, dict)
    if stage == "implementation":
        context["schema_version"] = "2.0"
        context["review_stage"] = "implementation"
        context["subject_commit"] = "b" * 40
        context["verification_snapshot_sha256"] = "f" * 64
        context["content"] = {
            **context["content"],
            "diff_summary": {"paths": []},
            "verification_summary": {"conclusion": "passed"},
        }
        context["context_sha256"] = context_sha256(context)

    record = {
        "schema_version": "1.0",
        "review_id": "REV-9001",
        "revision": 1,
        "task_id": "TASK-0025",
        "review_stage": stage,
        "reviewer": "independent-reviewer",
        "recorded_at": "2026-08-27T00:00:00Z",
        "context_sha256": context["context_sha256"],
        "outcome": "APPROVE",
        "summary": "offline binding",
        "findings": [],
    }
    validate_review_record(record, context)

    stale_context = deepcopy(context)
    stale_context["content"]["goal"] = "tampered current facts"
    with pytest.raises(ContractError) as stale_error:
        validate_review_context(stale_context)
    assert stale_error.value.code == "REVIEW_CONTEXT_HASH_INVALID"

    tampered_record = deepcopy(record)
    tampered_record["context_sha256"] = "0" * 64
    with pytest.raises(ContractError) as record_error:
        validate_review_record(tampered_record, context)
    assert record_error.value.code == "REVIEW_CONTEXT_MISMATCH"


def test_stale_evidence_and_missing_or_tampered_ci_attestation_fail_closed() -> None:
    evidence = _v2_evidence()
    binding_fields = (
        "task_id",
        "repository_id",
        "branch",
        "base_commit",
        "subject_commit",
        "policy_sha256",
        "spec_sha256",
        "classification_input_sha256",
    )
    current = {field: evidence[field] for field in binding_fields}
    current.update(
        verification_level="V2",
        governance_only=True,
        attestation_governance_only=True,
    )

    stale_subject = {**current, "subject_commit": "3" * 40}
    stale = evaluate_freshness("evidence", evidence, stale_subject)
    assert stale.status == "stale"
    assert stale.reason_codes == ("FRESHNESS_SUBJECT_CHANGED",)

    ci_evidence = deepcopy(evidence)
    ci_evidence["mode"] = "ci"
    ci_evidence["attestation_head"] = "4" * 40
    ci_evidence["attestation_governance_only"] = True
    changed_attestation = {**current, "attestation_head": "5" * 40}
    attestation = evaluate_freshness("evidence", ci_evidence, changed_attestation)
    assert attestation.status == "stale"
    assert attestation.reason_codes == ("FRESHNESS_ATTESTATION_CHANGED",)

    missing_attestation = deepcopy(ci_evidence)
    missing_attestation.pop("attestation_head")
    with pytest.raises(ContractError):
        require_valid_contract("evidence", missing_attestation)


def test_stale_review_context_binding_is_rejected() -> None:
    fixture = ROOT / "tests" / "fixtures" / "contracts" / "valid" / "verifier-context.json"
    stored = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(stored, dict)
    stored["context_sha256"] = context_sha256(stored)
    current = deepcopy(stored)
    content = current["content"]
    assert isinstance(content, dict)
    content["goal"] = "a different current subject contract"
    current["context_sha256"] = context_sha256(current)

    with pytest.raises(ContractError, match="stale"):
        validate_verifier_context_current(stored, current)
