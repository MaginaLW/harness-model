"""Golden contract checks for AUTO, ASK, REVIEW, and BLOCK scenarios."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from aiflow.contracts import validate_contract

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_ROOT = REPOSITORY_ROOT / "examples" / "scenarios"
POLICY_ROOT = REPOSITORY_ROOT / ".ai" / "policy"
SCENARIOS = {
    "auto-doc-edit": ("AUTO", "V0", "READY_TO_IMPLEMENT"),
    "ask-conflict-strategy": ("ASK", "V1", "WAITING_FOR_ASK"),
    "review-workflow-change": ("REVIEW", "V1", "WAITING_FOR_SPEC_REVIEW"),
    "block-no-backup": ("BLOCK", "V1", "BLOCKED"),
}
EXPECTED_KEYS = {
    "schema_version",
    "scenario_id",
    "route",
    "verification_level",
    "rule_ids",
    "reasons",
    "next_allowed_state",
    "required_approvals",
    "recovery_conditions",
    "options",
    "external_actions",
}
ABSOLUTE_PATH = re.compile(r"(?:^[A-Za-z]:[\\/]|^/(?:home|Users|tmp)/)")
DYNAMIC_KEYS = {"classified_at", "generated_at", "repository_path", "timestamp"}
pytestmark = pytest.mark.contract


def load_input(scenario_id: str) -> dict[str, Any]:
    value = yaml.safe_load((SCENARIO_ROOT / scenario_id / "input.yaml").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def load_expected(scenario_id: str) -> dict[str, Any]:
    value = json.loads((SCENARIO_ROOT / scenario_id / "expected.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def policy_rule_ids() -> set[str]:
    identifiers: set[str] = set()
    for filename in ("hard-rules.yaml", "routing.yaml"):
        value = yaml.safe_load((POLICY_ROOT / filename).read_text(encoding="utf-8"))
        identifiers.update(rule["id"] for rule in value["rules"])
        if "default_route" in value:
            identifiers.add(value["default_route"]["id"])
    return identifiers


def walk(value: object) -> list[tuple[str | None, object]]:
    """Flatten keys and scalar values for dynamic-field checks."""
    found: list[tuple[str | None, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.append((str(key), child))
            found.extend(walk(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk(child))
    else:
        found.append((None, value))
    return found


def test_scenario_tree_is_complete() -> None:
    directories = {path.name for path in SCENARIO_ROOT.iterdir() if path.is_dir()}
    assert directories == set(SCENARIOS)
    for scenario_id in SCENARIOS:
        files = {path.name for path in (SCENARIO_ROOT / scenario_id).iterdir()}
        assert files == {"expected.json", "input.yaml"}


def test_inputs_satisfy_the_decision_unit_contract() -> None:
    for scenario_id in SCENARIOS:
        assert validate_contract("decision-unit", load_input(scenario_id)) == []


def test_expected_results_have_a_fixed_comparable_shape() -> None:
    for scenario_id, (route, level, next_state) in SCENARIOS.items():
        expected = load_expected(scenario_id)
        assert set(expected) == EXPECTED_KEYS
        assert expected["schema_version"] == "1.0"
        assert expected["scenario_id"] == scenario_id
        assert expected["route"] == route
        assert expected["verification_level"] == level
        assert expected["next_allowed_state"] == next_state
        assert expected["rule_ids"]
        assert expected["reasons"]


def test_expected_results_only_reference_current_policy_rules() -> None:
    known = policy_rule_ids()
    for scenario_id in SCENARIOS:
        expected = load_expected(scenario_id)
        assert set(expected["rule_ids"]) <= known


def test_golden_comparison_excludes_dynamic_time_and_absolute_paths() -> None:
    for scenario_id in SCENARIOS:
        for key, value in walk(load_expected(scenario_id)):
            assert key not in DYNAMIC_KEYS
            if isinstance(value, str):
                assert not ABSOLUTE_PATH.search(value)


def test_each_route_uses_distinct_reasons() -> None:
    reason_sets = [set(load_expected(scenario_id)["reasons"]) for scenario_id in SCENARIOS]

    for index, reasons in enumerate(reason_sets):
        for other in reason_sets[index + 1 :]:
            assert reasons.isdisjoint(other)


def test_auto_is_a_reversible_docs_only_v0_change() -> None:
    decision_unit = load_input("auto-doc-edit")
    expected = load_expected("auto-doc-edit")

    assert all(path.startswith("docs/") for path in decision_unit["impact_scope"])
    assert decision_unit["reversibility"] == "reversible"
    assert decision_unit["external_side_effects"] == []
    assert expected["route"] == "AUTO"
    assert expected["verification_level"] == "V0"


def test_ask_has_three_complete_options_and_at_most_one_recommendation() -> None:
    expected = load_expected("ask-conflict-strategy")
    options = expected["options"]
    ask_contract = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "decision_unit_id": "DU-002",
        "options": options,
        "generated_at": "2000-01-01T00:00:00Z",
    }

    assert len(options) == 3
    assert validate_contract("ask-options", ask_contract) == []
    assert sum(option["recommended"] is True for option in options) <= 1


def test_review_requires_spec_and_code_approval_without_external_action() -> None:
    decision_unit = load_input("review-workflow-change")
    expected = load_expected("review-workflow-change")

    assert decision_unit["impact_scope"] == [".github/workflows/ai-quality-gate.yml"]
    assert expected["required_approvals"] == ["spec", "code"]
    assert expected["external_actions"] == []


def test_block_names_concrete_recovery_conditions() -> None:
    expected = load_expected("block-no-backup")
    recovery = expected["recovery_conditions"]

    assert len(recovery) == 2
    assert any("verified backup" in condition for condition in recovery)
    assert any("target scope" in condition for condition in recovery)


def test_scenario_readme_states_that_results_are_not_runtime_classification() -> None:
    text = (SCENARIO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "static contracts" in text
    assert "classification engine" in text
