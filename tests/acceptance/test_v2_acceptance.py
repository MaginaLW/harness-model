"""Offline acceptance contract for the Chapter 11.1 V2 verification plan.

This suite intentionally only parses Policy and exercises pure planning helpers: invoking
``aiflow verify`` here would recursively run the acceptance suite itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from aiflow.mutation_evidence import TargetedMutationFacts
from aiflow.policy import load_policy_bundle
from aiflow.review_service import ReviewAssessment
from aiflow.verification import (
    V1_CHECK_IDS,
    V2_EXTRA_CHECK_IDS,
    VerificationContext,
    parse_verification_plan,
)
from aiflow.verification_service import (
    _missing_mutation_projection,
    _upgrade_v2_pre_evidence,
    _v2_plans,
)

ROOT = Path(__file__).resolve().parents[2]


def _plan(tmp_path: Path):
    return parse_verification_plan(
        load_policy_bundle(ROOT),
        VerificationContext(
            tmp_path,
            "TASK-ACCEPTANCE",
            "a" * 40,
            "b" * 40,
            sys.executable,
            "offline-acceptance",
        ),
        level="V2",
        tool_available=lambda _argv: True,
    )


def test_v2_policy_exposes_real_offline_acceptance_and_integration(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    by_id = {check.check_id: check for check in plan.checks}

    assert tuple(check.check_id for check in plan.checks) == V1_CHECK_IDS + V2_EXTRA_CHECK_IDS
    assert by_id["acceptance"].argv == (sys.executable, "-m", "pytest", "tests/acceptance", "-q")
    assert by_id["integration"].argv == (sys.executable, "-m", "pytest", "tests/integration", "-q")


def test_selected_acceptance_never_schedules_mutation(tmp_path: Path) -> None:
    full = _plan(tmp_path)
    execution, evidence_checks = _v2_plans(full, ("acceptance",))

    assert tuple(check.check_id for check in execution.checks) == ("acceptance",)
    assert tuple(check.check_id for check in evidence_checks) == (
        "acceptance",
        "integration",
        "targeted_mutation",
        "independent_verifier",
    )
    assert "targeted_mutation" not in {
        item for run in execution.executions for item in run.check_ids
    }


def test_v1_never_requires_or_schedules_targeted_mutation(tmp_path: Path) -> None:
    plan = parse_verification_plan(
        load_policy_bundle(ROOT),
        VerificationContext(
            tmp_path,
            "TASK-ACCEPTANCE",
            "a" * 40,
            "b" * 40,
            sys.executable,
            "offline-v1-acceptance",
        ),
        level="V1",
        tool_available=lambda _argv: True,
    )

    assert tuple(check.check_id for check in plan.checks) == V1_CHECK_IDS
    assert "targeted_mutation" not in {
        item for execution in plan.executions for item in execution.check_ids
    }


@pytest.mark.parametrize(
    ("outcome", "passed", "reason"),
    [
        ("killed", True, None),
        ("survived", False, "MUTATION_EVIDENCE_NOT_KILLED"),
        ("unverified", False, "MUTATION_EVIDENCE_NOT_KILLED"),
    ],
)
def test_v2_mutation_projection_cannot_hide_uncovered_results(
    outcome: str, passed: bool, reason: str | None
) -> None:
    fixture = ROOT / "tests" / "fixtures" / "contracts" / "valid" / "evidence-v2.json"
    evidence = json.loads(fixture.read_text(encoding="utf-8"))
    projection = evidence["targeted_mutation"]
    for result in projection["results"]:
        result["outcome"] = outcome
    facts = TargetedMutationFacts(
        passed,
        reason,
        projection["evidence_ref"],
        projection["mutation_evidence_sha256"],
        projection["manifest_ref"],
        tuple(projection["results"]),
    )

    upgraded = _upgrade_v2_pre_evidence(
        evidence,
        mutation_projection=projection,
        mutation_facts=facts,
        verifier_actor="offline-verifier",
        verifier_context_sha256="d" * 64,
        design_review=ReviewAssessment({"context_sha256": "e" * 64}, {"review_id": "REV-0001"}),
    )
    checks = {check["check_id"]: check for check in upgraded["checks"]}
    assert checks["targeted_mutation"]["status"] == ("passed" if passed else "failed")
    assert checks["targeted_mutation"]["reason_code"] == reason
    assert upgraded["conclusion"] == ("passed" if passed else "failed")


def test_missing_mutation_projection_is_explicit_and_manifest_complete() -> None:
    projection = _missing_mutation_projection("TASK-0001")

    assert projection["mutation_evidence_sha256"] == "0" * 64
    assert [item["mutation_id"] for item in projection["results"]] == [
        f"MUT-V2-{index:03d}" for index in range(1, 6)
    ]
    assert {item["outcome"] for item in projection["results"]} == {"unverified"}
