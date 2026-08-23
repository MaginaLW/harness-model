"""Offline acceptance contract for the Chapter 11.1 V2 verification plan.

This suite intentionally only parses Policy and exercises pure planning helpers: invoking
``aiflow verify`` here would recursively run the acceptance suite itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

from aiflow.policy import load_policy_bundle
from aiflow.verification import (
    V1_CHECK_IDS,
    V2_EXTRA_CHECK_IDS,
    VerificationContext,
    parse_verification_plan,
)
from aiflow.verification_service import _v2_plans

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


def test_selected_acceptance_is_provisional_and_never_schedules_mutation(tmp_path: Path) -> None:
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
