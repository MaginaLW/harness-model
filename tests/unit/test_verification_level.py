from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from aiflow.policy import PolicyBundle, load_policy_bundle
from aiflow.verification_level import (
    V0,
    V1,
    determine_verification_level,
    summarize_task_verification,
)

ROOT = Path(__file__).parents[2]


def _bundle() -> PolicyBundle:
    return load_policy_bundle(ROOT)


def _unit(
    identifier: str, characteristics: dict[str, object], **extra: object
) -> dict[str, object]:
    return {
        "decision_unit_id": identifier,
        "change_characteristics": characteristics,
        "verification": {"tools_missing": False},
        **extra,
    }


def test_level_table_is_route_independent() -> None:
    table = json.loads((ROOT / "tests/fixtures/verification/level-table.json").read_text("utf-8"))
    for index, case in enumerate(table["unit_cases"]):
        result = determine_verification_level(_unit(f"DU-{index:03}", case["facts"]), _bundle())
        assert result.level == case["expected_level"], case["id"]


@pytest.mark.parametrize(
    ("field", "value", "rule_id"),
    [
        ("mechanical", False, "VERIFICATION-NON-MECHANICAL"),
        ("behavior_changed", True, "VERIFICATION-BEHAVIOR-CHANGED"),
        ("code_modified", True, "VERIFICATION-CODE-MODIFIED"),
        ("interaction_scope", "cross_file", "VERIFICATION-CROSS-FILE"),
        ("interaction_scope", "cross_module", "VERIFICATION-CROSS-MODULE"),
        ("regression_risk", True, "VERIFICATION-REGRESSION-RISK"),
        ("error_detectability", "low", "VERIFICATION-LOW-DETECTABILITY"),
    ],
)
def test_each_v1_characteristic_has_an_auditable_rule(
    field: str, value: object, rule_id: str
) -> None:
    facts: dict[str, object] = {
        "mechanical": True,
        "behavior_changed": False,
        "code_modified": False,
        "interaction_scope": "local",
        "regression_risk": False,
        "error_detectability": "high",
    }
    facts[field] = value
    result = determine_verification_level(_unit("DU-001", facts), _bundle())
    assert result.level == V1
    assert rule_id in result.rule_ids
    assert len(result.rule_ids) == len(result.explanations)


def test_missing_legacy_characteristics_are_conservative_v1() -> None:
    result = determine_verification_level({"decision_unit_id": "DU-001"}, _bundle())
    assert result.level == V1
    assert result.rule_ids == ("VERIFICATION-FACTS-INCOMPLETE",)


@pytest.mark.parametrize("behavior_changed,expected_level", [(False, V0), (True, V1)])
def test_tools_missing_blocks_execution_without_downgrading_level(
    behavior_changed: bool, expected_level: str
) -> None:
    facts = {
        "mechanical": True,
        "behavior_changed": behavior_changed,
        "code_modified": False,
        "interaction_scope": "local",
        "regression_risk": False,
        "error_detectability": "high",
    }
    result = determine_verification_level(
        _unit("DU-001", facts, verification={"tools_missing": True}), _bundle()
    )
    assert result.level == expected_level
    assert result.blocking_reasons == ("VERIFICATION-TOOLS-MISSING",)
    summary = summarize_task_verification(
        [_unit("DU-001", facts, verification={"tools_missing": True})], _bundle()
    )
    assert summary.blocking_reasons == ("VERIFICATION-TOOLS-MISSING",)


def test_incomplete_v0_policy_is_configuration_block() -> None:
    bundle = _bundle()
    documents = deepcopy(bundle.documents)
    checks = documents["verification-levels.yaml"]["levels"][0]["checks"]
    assert isinstance(checks, list)
    checks.pop()
    altered = PolicyBundle(documents, bundle.policy_version, bundle.sha256)
    facts = {
        "mechanical": True,
        "behavior_changed": False,
        "code_modified": False,
        "interaction_scope": "local",
        "regression_risk": False,
        "error_detectability": "high",
    }
    result = determine_verification_level(_unit("DU-001", facts), altered)
    assert result.level == V1
    assert result.rule_ids == ("VERIFICATION-V1-POLICY-INCOMPLETE",)
    assert result.blocking_reasons == ("VERIFICATION-V0-POLICY-INCOMPLETE",)


def test_task_aggregation_excludes_completed_units_but_keeps_evidence() -> None:
    v0 = {
        "mechanical": True,
        "behavior_changed": False,
        "code_modified": False,
        "interaction_scope": "local",
        "regression_risk": False,
        "error_detectability": "high",
    }
    v1 = {**v0, "behavior_changed": True}
    completed = _unit("DU-001", v1, completed=True)
    active = _unit("DU-002", v0)
    result = summarize_task_verification([completed, active], _bundle())
    assert result.level == V0
    assert [decision.level for decision in result.unit_decisions] == [V1, V0]
    all_completed = summarize_task_verification(
        [completed, {**active, "status": "COMPLETED"}], _bundle()
    )
    assert all_completed.level == "completed"
