from __future__ import annotations

import pytest

from aiflow.errors import PolicyError
from aiflow.predicates import evaluate_predicate

FACTS = {"name": "safe", "number": 2, "items": ["one", "two"], "nested": {"flag": True}}


@pytest.mark.parametrize(
    ("condition", "matched"),
    [
        ({"field": "name", "operator": "equals", "value": "safe"}, True),
        ({"field": "name", "operator": "not_equals", "value": "unsafe"}, True),
        ({"field": "name", "operator": "in", "value": ["safe"]}, True),
        ({"field": "items", "operator": "contains_any", "value": ["two", "other"]}, True),
        ({"field": "items", "operator": "contains_all", "value": ["one", "two"]}, True),
        ({"field": "nested.flag", "operator": "exists"}, True),
        ({"field": "items", "operator": "is_empty", "value": True}, False),
        ({"field": "number", "operator": "greater_than_or_equal", "value": 2}, True),
    ],
)
def test_evaluate_predicate_supported_operators(
    condition: dict[str, object], matched: bool
) -> None:
    result = evaluate_predicate(condition, FACTS)
    assert result.matched is matched
    assert "safe" not in result.explanation


def test_missing_field_strategies_are_deterministic() -> None:
    condition = {"field": "missing", "operator": "exists"}
    assert evaluate_predicate({**condition, "missing": "no_match"}, FACTS).matched is False
    assert evaluate_predicate({**condition, "missing": "match"}, FACTS).matched is True
    with pytest.raises(PolicyError) as raised:
        evaluate_predicate({**condition, "missing": "error"}, FACTS)
    assert raised.value.code == "PREDICATE_FIELD_MISSING"


@pytest.mark.parametrize(
    "condition",
    [
        {"field": "name.__class__", "operator": "equals", "value": "x"},
        {"field": "name; __import__('os')", "operator": "equals", "value": "x"},
        {"field": "name", "operator": "eval", "value": "__import__('os')"},
        {"field": "name", "operator": "equals", "value": "x", "callback": "run"},
    ],
)
def test_evaluate_predicate_rejects_expression_injection(condition: dict[str, object]) -> None:
    with pytest.raises(PolicyError):
        evaluate_predicate(condition, FACTS)


@pytest.mark.parametrize(
    "condition",
    [
        {"field": "items", "operator": "contains_any", "value": "one"},
        {"field": "number", "operator": "greater_than_or_equal", "value": "two"},
    ],
)
def test_evaluate_predicate_rejects_wrong_types(condition: dict[str, object]) -> None:
    with pytest.raises(PolicyError) as raised:
        evaluate_predicate(condition, FACTS)
    assert raised.value.code == "PREDICATE_TYPE_INVALID"
