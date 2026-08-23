"""Focused V2 scheduling tests without launching the repository's V2 verifier recursively."""

from __future__ import annotations

import sys
from pathlib import Path

from aiflow.verification import (
    V1_CHECK_IDS,
    VerificationCheck,
    VerificationExecution,
    VerificationPlan,
)
from aiflow.verification_service import _v2_plans


def _check(identifier: str) -> VerificationCheck:
    return VerificationCheck(
        identifier, "V2", (sys.executable, "-c", "print('ok')"), {}, Path.cwd(), 10, True, "pytest"
    )


def _plan() -> VerificationPlan:
    checks = tuple(
        _check(identifier)
        for identifier in (
            *V1_CHECK_IDS,
            "acceptance",
            "integration",
            "targeted_mutation",
            "independent_verifier",
        )
    )
    executions = tuple(
        VerificationExecution(f"EXEC-{index:03d}", check.argv, {}, check.cwd, 10, (check.check_id,))
        for index, check in enumerate(checks, start=1)
    )
    return VerificationPlan("V2", Path.cwd() / "run", checks, executions, (), (), "b" * 40)


def test_default_v2_schedules_v1_prefix_acceptance_and_integration_but_not_mutation() -> None:
    execution, evidence_checks = _v2_plans(_plan(), ())

    assert {check.check_id for check in execution.checks} == {
        *V1_CHECK_IDS,
        "acceptance",
        "integration",
    }
    assert "targeted_mutation" not in {
        item for run in execution.executions for item in run.check_ids
    }
    assert {check.check_id for check in evidence_checks} == {
        *V1_CHECK_IDS,
        "acceptance",
        "integration",
        "targeted_mutation",
        "independent_verifier",
    }


def test_selected_integration_only_schedules_that_real_check() -> None:
    execution, evidence_checks = _v2_plans(_plan(), ("integration",))

    assert tuple(check.check_id for check in execution.checks) == ("integration",)
    assert {check.check_id for check in evidence_checks} == {
        "acceptance",
        "integration",
        "targeted_mutation",
        "independent_verifier",
    }
