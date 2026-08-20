"""Small deterministic predicate evaluator for Policy conditions."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import cast

from aiflow.errors import PolicyError

SUPPORTED_OPERATORS = frozenset(
    {
        "equals",
        "not_equals",
        "in",
        "contains_any",
        "contains_all",
        "exists",
        "is_empty",
        "greater_than_or_equal",
    }
)
MISSING_STRATEGIES = frozenset({"error", "match", "no_match"})
_PATH = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*$")
_MISSING = object()


@dataclass(frozen=True)
class PredicateResult:
    """The non-sensitive, stable outcome of one Policy condition."""

    matched: bool
    explanation: str


def _policy_error(message: str, code: str, **details: object) -> PolicyError:
    return PolicyError(message, code=code, details=details)


def _field_value(facts: Mapping[str, object], field: str) -> object:
    value: object = facts
    for part in field.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _require_sequence(value: object, *, operator: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise _policy_error(
            "Predicate requires a list value", "PREDICATE_TYPE_INVALID", operator=operator
        )
    return value


def _is_number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _validate_condition(condition: Mapping[str, object]) -> tuple[str, str, object, str]:
    allowed = {"field", "operator", "value", "missing"}
    unknown = sorted(str(key) for key in condition if key not in allowed)
    if unknown:
        raise _policy_error("Predicate has unknown fields", "PREDICATE_INVALID", fields=unknown)
    field = condition.get("field")
    operator = condition.get("operator")
    if not isinstance(field, str) or not _PATH.fullmatch(field):
        raise _policy_error("Predicate field path is invalid", "PREDICATE_PATH_INVALID")
    if not isinstance(operator, str) or operator not in SUPPORTED_OPERATORS:
        raise _policy_error("Predicate operator is not supported", "PREDICATE_OPERATOR_UNKNOWN")
    if operator not in {"exists", "is_empty"} and "value" not in condition:
        raise _policy_error(
            "Predicate value is required", "PREDICATE_VALUE_MISSING", operator=operator
        )
    missing = condition.get("missing", "no_match")
    if not isinstance(missing, str) or missing not in MISSING_STRATEGIES:
        raise _policy_error("Predicate missing strategy is invalid", "PREDICATE_MISSING_INVALID")
    return field, operator, condition.get("value"), missing


def evaluate_predicate(
    condition: Mapping[str, object], facts: Mapping[str, object]
) -> PredicateResult:
    """Evaluate a fixed predicate vocabulary without exposing supplied values.

    A missing ``error`` field is intentionally an error rather than a false
    result.  Routing can then conservatively classify the incomplete input.
    """
    field, operator, expected, missing = _validate_condition(condition)
    actual = _field_value(facts, field)
    if actual is _MISSING:
        if missing == "error":
            raise _policy_error(
                "Required predicate field is missing", "PREDICATE_FIELD_MISSING", field=field
            )
        return PredicateResult(
            matched=missing == "match", explanation=f"{field}: missing ({missing})"
        )

    if operator == "equals":
        matched = actual == expected
    elif operator == "not_equals":
        matched = actual != expected
    elif operator == "in":
        matched = actual in _require_sequence(expected, operator=operator)
    elif operator == "contains_any":
        values = _require_sequence(actual, operator=operator)
        expected_values = _require_sequence(expected, operator=operator)
        matched = any(value in values for value in expected_values)
    elif operator == "contains_all":
        values = _require_sequence(actual, operator=operator)
        expected_values = _require_sequence(expected, operator=operator)
        matched = all(value in values for value in expected_values)
    elif operator == "exists":
        matched = True
    elif operator == "is_empty":
        if not isinstance(actual, (str, bytes, Sequence, Mapping)):
            raise _policy_error(
                "Predicate requires a collection value", "PREDICATE_TYPE_INVALID", operator=operator
            )
        matched = len(actual) == 0
    else:
        if not _is_number(actual) or not _is_number(expected):
            raise _policy_error(
                "Predicate requires numeric values", "PREDICATE_TYPE_INVALID", operator=operator
            )
        matched = cast(Real, actual) >= cast(Real, expected)
    return PredicateResult(
        matched=matched, explanation=f"{field}: {operator} -> {str(matched).lower()}"
    )
