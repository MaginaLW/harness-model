"""Offline acceptance contract for the current Chapter 13.2 REVIEW/V2 trial."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.errors import ContractError
from aiflow.policy import load_policy_bundle
from aiflow.specification import specification_digest
from aiflow.storage import read_task_json
from aiflow.task_service import load_task_record
from aiflow.verification import V2_CHECK_IDS, VerificationContext, parse_verification_plan
from aiflow.verifier_service import (
    build_verifier_context,
    context_sha256,
    load_verifier_context,
    validate_verifier_actor,
    validate_verifier_context_current,
)

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "TASK-0025"
HISTORICAL_POLICY_SHA256 = "f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf"
HISTORICAL_CONTEXT_SHA256 = "760023540a0560e312e9136945bb7171560a4b776a0c626eb106e933d45b7c03"


def test_historical_review_v2_binding_is_frozen_and_active_policy_has_all_checks() -> None:
    """The frozen trial remains historical while active V2 keeps all required checks."""
    record = load_task_record(ROOT, TASK_ID)
    task = record.task
    classification = read_task_json(
        ROOT, TASK_ID, "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    bundle = load_policy_bundle(ROOT)

    assert task["frozen_spec_sha256"] == specification_digest(
        (ROOT / ".ai" / "tasks" / TASK_ID / "spec.md").read_text(encoding="utf-8")
    )
    assert classification["task_id"] == TASK_ID
    assert classification["base_commit"] == task["base_commit"]
    assert classification["policy_sha256"] == HISTORICAL_POLICY_SHA256
    assert classification["policy_sha256"] != bundle.sha256
    assert classification["effective_route"] == "REVIEW"
    assert classification["effective_verification_level"] == "V2"

    plan = parse_verification_plan(
        bundle,
        VerificationContext(
            ROOT,
            TASK_ID,
            str(task["base_commit"]),
            str(task["subject_commit"]),
            "python",
            "phase-02-acceptance",
        ),
        level="V2",
        tool_available=lambda _argv: True,
    )
    assert tuple(check.check_id for check in plan.checks) == V2_CHECK_IDS
    assert all(check.required for check in plan.checks)
    requirements = task["decision_units"][0]["verification_requirements"]
    assert requirements == {
        "acceptance_required": True,
        "integration_required": True,
        "targeted_mutation_required": True,
        "independent_verifier_required": True,
    }


def test_verifier_context_and_roles_fail_closed_for_reused_or_non_independent_facts() -> None:
    """Historical classification and context reuse fail closed; roles remain independent."""
    with pytest.raises(ContractError) as stale_classification:
        build_verifier_context(ROOT, TASK_ID)
    assert stale_classification.value.code == "VERIFIER_CONTEXT_CLASSIFICATION_STALE"

    historical = load_verifier_context(ROOT, TASK_ID, HISTORICAL_CONTEXT_SHA256)
    assert historical["policy_sha256"] == HISTORICAL_POLICY_SHA256
    reused = dict(historical)
    reused["task_id"] = "TASK-0024"
    reused["context_sha256"] = context_sha256(reused)

    with pytest.raises(ContractError, match="stale") as stale:
        validate_verifier_context_current(reused, historical)
    assert stale.value.code == "VERIFIER_CONTEXT_STALE"
    with pytest.raises(ContractError) as same_actor:
        validate_verifier_actor("implementer", "implementer")
    assert same_actor.value.code == "VERIFIER_ACTOR_NOT_INDEPENDENT"
    with pytest.raises(ContractError) as empty_actor:
        validate_verifier_actor("implementer", " ")
    assert empty_actor.value.code == "VERIFIER_ACTOR_REQUIRED"
