from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from aiflow.policy import PolicyBundle, load_policy_bundle
from aiflow.routing import route_decision_unit, route_task

ROOT = Path(__file__).parents[2]


def _bundle() -> PolicyBundle:
    return load_policy_bundle(ROOT)


def _unit(identifier: str, facts: dict[str, object], **extra: object) -> dict[str, object]:
    return {"decision_unit_id": identifier, **facts, **extra}


def _facts(*, automatic: bool, clear: bool, impact: str, directions: int) -> dict[str, object]:
    return {
        "external_side_effects": [],
        "reversibility": "reversible",
        "protections": {"verified_backup": True, "dry_run": False},
        "verification": {"tools_missing": False, "automatic": automatic},
        "scope": {"clear": clear},
        "impact": {"level": impact},
        "planned_actions": ["change"],
        "impact_categories": [],
        "business_direction_count": directions,
    }


def _alter(bundle: PolicyBundle, mutate: object) -> PolicyBundle:
    documents = deepcopy(bundle.documents)
    mutate(documents)  # type: ignore[operator]
    return PolicyBundle(documents, bundle.policy_version, bundle.sha256)


def test_decision_table_routes_every_policy_rule() -> None:
    table = json.loads((ROOT / "tests/fixtures/routing/decision-table.json").read_text("utf-8"))
    cases = table["unit_cases"]
    for index, case in enumerate(cases):
        decision = route_decision_unit(_unit(f"DU-{index:03}", case["facts"]), _bundle())
        assert decision.route == case["expected_route"], case["id"]
        assert table["expected_rule_ids"][case["id"]] in decision.matched_rule_ids, case["id"]


def test_all_hits_are_stable_and_effective_route_is_safety_ordered() -> None:
    facts = {
        "external_side_effects": ["credential_export"],
        "reversibility": "reversible",
        "protections": {"verified_backup": True, "dry_run": False},
        "verification": {"tools_missing": False, "automatic": False},
        "scope": {"clear": False},
        "impact": {"level": "medium"},
        "planned_actions": ["deploy"],
        "impact_categories": ["ci"],
        "business_direction_count": 2,
    }
    decision = route_decision_unit(_unit("DU-001", facts), _bundle())
    assert decision.route == "BLOCK"
    assert [hit.priority for hit in decision.matched_rules] == sorted(
        (hit.priority for hit in decision.matched_rules), reverse=True
    )
    assert {
        "HARD-BLOCK-EXTERNAL-SENSITIVE",
        "HARD-REVIEW-DEPLOYMENT",
        "ROUTE-ASK-MULTIPLE-DIRECTIONS",
    } <= set(decision.matched_rule_ids)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda documents: documents["routing.yaml"]["rules"].append(
            {**documents["routing.yaml"]["rules"][0], "id": "ROUTE-CONFLICT", "route": "AUTO"}
        ),
        lambda documents: documents["hard-rules.yaml"]["rules"][0].pop("recovery_conditions"),
        lambda documents: documents["routing.yaml"]["rules"][1]["conditions"].pop(),
    ],
)
def test_configuration_errors_are_explainable_blocks(mutation: object) -> None:
    decision = route_decision_unit(_unit("DU-001", {}), _alter(_bundle(), mutation))
    assert decision.route == "BLOCK"
    assert decision.matched_rule_ids[0].startswith("ROUTING-")


def test_decision_table_covers_each_incompatible_route_pair() -> None:
    table = json.loads((ROOT / "tests/fixtures/routing/decision-table.json").read_text("utf-8"))
    for case in table["configuration_cases"]:

        def conflict(documents: dict[str, dict[str, object]]) -> None:
            rule = deepcopy(documents["routing.yaml"]["rules"][1])
            assert isinstance(rule, dict)
            rule["id"] = f"ROUTE-CONFLICT-{case['id']}"
            rule["priority"] = case["priority"]
            rule["route"] = case["routes"][0]
            if rule["route"] == "BLOCK":
                rule["recovery_conditions"] = ["Recover before retrying."]
            documents["routing.yaml"]["rules"].append(rule)
            rule = deepcopy(rule)
            rule["id"] = f"ROUTE-CONFLICT-SECOND-{case['id']}"
            rule["route"] = case["routes"][1]
            if rule["route"] == "BLOCK":
                rule["recovery_conditions"] = ["Recover before retrying."]
            documents["routing.yaml"]["rules"].append(rule)

        decision = route_decision_unit(_unit("DU-001", {}), _alter(_bundle(), conflict))
        assert decision.route == case["expected_route"]
        assert "ROUTING_PRIORITY_CONFLICT" in decision.matched_rule_ids[0]


def test_predicate_error_is_an_explainable_block() -> None:
    decision = route_decision_unit(_unit("DU-001", {}), _bundle())
    assert decision.route == "BLOCK"
    assert "PREDICATE_FIELD_MISSING" in decision.matched_rule_ids[0]


def test_task_aggregation_ignores_completed_units_without_overwriting_them() -> None:
    table = json.loads((ROOT / "tests/fixtures/routing/decision-table.json").read_text("utf-8"))
    auto = _unit("DU-001", _facts(automatic=True, clear=True, impact="low", directions=1))
    ask = _unit("DU-002", _facts(automatic=False, clear=False, impact="medium", directions=2))
    block_facts = _facts(automatic=True, clear=True, impact="low", directions=1)
    block_facts["external_side_effects"] = ["credential_export"]
    block = _unit("DU-003", block_facts)
    cases = {
        "multi-unit-highest-unfinished": [auto, ask],
        "completed-unit-excluded": [{**block, "completed": True}, ask],
        "all-completed": [{**auto, "status": "COMPLETED"}, {**ask, "completed": True}],
    }
    for case in table["task_cases"]:
        result = route_task({"decision_units": cases[case["id"]]}, _bundle())
        assert result.route == case["expected_route"], case["id"]
        if case["id"] == "completed-unit-excluded":
            assert result.unit_decisions[0].route == "BLOCK"
