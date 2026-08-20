"""Parsing and validation for independently classifiable decision units."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Mapping, Sequence
from copy import deepcopy
from typing import Any

from aiflow.contracts import validate_contract
from aiflow.errors import PolicyError

KNOWN_REVERSIBILITY = frozenset({"reversible", "conditionally_reversible", "irreversible"})
# Requirement tokens name gates; approval records use the related spec/code/action types.
DECLARED_PERMISSION_REQUIREMENTS = frozenset({"spec_approval", "code_approval", "action_approval"})


def _error(message: str, code: str, **details: object) -> PolicyError:
    return PolicyError(message, code=code, details=details)


def parse_decision_units(
    task: Mapping[str, object],
    *,
    declared_permissions: Collection[str] = DECLARED_PERMISSION_REQUIREMENTS,
) -> tuple[dict[str, Any], ...]:
    """Return task decision units in stable ID order after strict validation.

    ``declared_permissions`` is explicit so callers can use a narrower approved
    vocabulary without weakening the repository-wide default.
    """
    units = task.get("decision_units")
    if not isinstance(units, Sequence) or isinstance(units, (str, bytes)):
        raise _error("Task decision units must be a list", "DECISION_UNITS_INVALID")

    parsed: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    task_id = task.get("task_id")
    for index, raw_unit in enumerate(units):
        if not isinstance(raw_unit, Mapping):
            raise _error("Decision unit must be an object", "DECISION_UNIT_INVALID", index=index)
        unit = dict(raw_unit)
        errors = validate_contract("decision-unit", unit)
        if errors:
            raise _error(
                "Decision unit does not satisfy its Schema",
                "DECISION_UNIT_SCHEMA_INVALID",
                index=index,
                errors=errors,
            )
        identifier = unit["decision_unit_id"]
        if not isinstance(identifier, str):  # Schema checked, retained for type narrowing.
            raise _error("Decision unit ID must be a string", "DECISION_UNIT_INVALID", index=index)
        if identifier in identifiers:
            raise _error(
                "Decision unit IDs must be unique", "DECISION_UNIT_ID_DUPLICATE", id=identifier
            )
        identifiers.add(identifier)
        if unit.get("task_id") != task_id:
            raise _error(
                "Decision unit task ID must match its task",
                "DECISION_UNIT_TASK_MISMATCH",
                id=identifier,
            )
        impact_scope = unit.get("impact_scope")
        if not isinstance(impact_scope, list) or not any(
            isinstance(item, str) and item.strip() for item in impact_scope
        ):
            raise _error(
                "Decision unit impact scope must not be empty",
                "DECISION_UNIT_IMPACT_EMPTY",
                id=identifier,
            )
        reversibility = unit.get("reversibility")
        if reversibility not in KNOWN_REVERSIBILITY:
            raise _error(
                "Decision unit reversibility is not recognized",
                "DECISION_UNIT_REVERSIBILITY_UNKNOWN",
                id=identifier,
            )
        requirements = unit.get("permission_requirements")
        if not isinstance(requirements, list):
            raise _error(
                "Decision unit permissions must be a list", "DECISION_UNIT_INVALID", id=identifier
            )
        unknown_permissions = sorted(
            requirement
            for requirement in requirements
            if not isinstance(requirement, str) or requirement not in declared_permissions
        )
        if unknown_permissions:
            raise _error(
                "Decision unit references an undeclared permission",
                "DECISION_UNIT_PERMISSION_UNDECLARED",
                id=identifier,
                permissions=unknown_permissions,
            )
        parsed.append(deepcopy(unit))

    return tuple(sorted(parsed, key=lambda unit: str(unit["decision_unit_id"])))


def classification_input_digest(
    task: Mapping[str, object], units: Sequence[Mapping[str, object]]
) -> str:
    """Hash only stable task and decision facts used to classify a task."""
    value = {
        "task_id": task.get("task_id"),
        "goal": task.get("goal"),
        "allowed_scope": task.get("allowed_scope"),
        "forbidden_actions": task.get("forbidden_actions"),
        "base_commit": task.get("base_commit"),
        "subject_commit": task.get("subject_commit"),
        "decision_units": units,
    }
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
