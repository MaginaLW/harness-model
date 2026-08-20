from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

import pytest

from aiflow.decision_units import parse_decision_units
from aiflow.errors import PolicyError


def _unit(identifier: str = "DU-001") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "decision_unit_id": identifier,
        "goal": "Bounded change",
        "inputs": ["design"],
        "planned_actions": ["change"],
        "impact_scope": ["src/a.py"],
        "reversibility": "reversible",
        "verification_methods": ["pytest"],
        "external_side_effects": [],
        "permission_requirements": [],
    }


def _task(*units: dict[str, object]) -> dict[str, object]:
    return {"task_id": "TASK-0001", "decision_units": list(units)}


def test_parse_decision_units_sorts_and_copies() -> None:
    first, second = _unit("DU-002"), _unit("DU-001")
    result = parse_decision_units(_task(first, second))
    assert [unit["decision_unit_id"] for unit in result] == ["DU-001", "DU-002"]
    result[0]["goal"] = "changed"
    assert second["goal"] == "Bounded change"


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda unit: unit.update(impact_scope=[]), "DECISION_UNIT_SCHEMA_INVALID"),
        (lambda unit: unit.update(reversibility="eventually"), "DECISION_UNIT_SCHEMA_INVALID"),
        (
            lambda unit: unit.update(permission_requirements=["untrusted"]),
            "DECISION_UNIT_PERMISSION_UNDECLARED",
        ),
    ],
)
def test_parse_decision_units_rejects_invalid_unit(
    mutate: Callable[[dict[str, object]], None], code: str
) -> None:
    unit = _unit()
    mutate(unit)
    with pytest.raises(PolicyError) as raised:
        parse_decision_units(_task(unit))
    assert raised.value.code == code


def test_parse_decision_units_rejects_duplicate_and_task_mismatch() -> None:
    with pytest.raises(PolicyError) as raised:
        parse_decision_units(_task(_unit(), _unit()))
    assert raised.value.code == "DECISION_UNIT_ID_DUPLICATE"
    mismatched = deepcopy(_unit())
    mismatched["task_id"] = "TASK-0002"
    with pytest.raises(PolicyError) as raised:
        parse_decision_units(_task(mismatched))
    assert raised.value.code == "DECISION_UNIT_TASK_MISMATCH"


def test_parse_decision_units_supports_narrowed_permission_vocabulary() -> None:
    unit = _unit()
    unit["permission_requirements"] = ["spec"]
    assert parse_decision_units(_task(unit))[0]["permission_requirements"] == ["spec"]
    with pytest.raises(PolicyError) as raised:
        parse_decision_units(_task(unit), declared_permissions=frozenset())
    assert raised.value.code == "DECISION_UNIT_PERMISSION_UNDECLARED"
