"""Load and validate AI Flow machine contracts."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]
from referencing import Registry, Resource

from aiflow.errors import ContractError

JsonObject = dict[str, Any]

SCHEMA_RELATIVE_DIRECTORY = Path(".ai") / "schemas"
SCHEMA_FILES = {
    "approval": "approval.schema.json",
    "ask-options": "ask-options.schema.json",
    "classification": "classification.schema.json",
    "decision-unit": "decision-unit.schema.json",
    "event": "event.schema.json",
    "evidence": "evidence.schema.json",
    "mutation-evidence": "mutation-evidence.schema.json",
    "mutation-manifest": "mutation-manifest.schema.json",
    "observation": "observation.schema.json",
    "policy": "policy.schema.json",
    "review-context": "review-context.schema.json",
    "review-record": "review-record.schema.json",
    "task": "task.schema.json",
    "verifier-context": "verifier-context.schema.json",
}


class ContractValidationError(ContractError):
    """Raised when a value does not satisfy a named machine contract."""

    def __init__(self, contract_name: str, errors: list[str]) -> None:
        self.contract_name = contract_name
        self.errors = errors
        super().__init__(
            f"Invalid {contract_name} contract: {'; '.join(errors)}",
            code="CONTRACT_VALIDATION_FAILED",
            details={"contract_name": contract_name, "errors": errors},
        )


def load_schema(contract_name: str, schema_directory: Path | None = None) -> JsonObject:
    """Load a known contract schema without accepting arbitrary paths."""
    try:
        filename = SCHEMA_FILES[contract_name]
    except KeyError as error:
        raise KeyError(f"Unknown contract: {contract_name}") from error

    directory = schema_directory if schema_directory is not None else SCHEMA_RELATIVE_DIRECTORY
    value = json.loads((directory / filename).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Schema {contract_name} must contain a JSON object")
    return value


def _schema_registry(schema_directory: Path = SCHEMA_RELATIVE_DIRECTORY) -> Registry[Any]:
    resources: list[tuple[str, Resource[Any]]] = []
    for filename in SCHEMA_FILES.values():
        path = schema_directory / filename
        if not path.is_file():
            continue
        schema = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(schema, dict) and isinstance(schema.get("$id"), str):
            resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _escape_pointer_part(part: object) -> str:
    return str(part).replace("~", "~0").replace("/", "~1")


def _pointer(parts: Sequence[object]) -> str:
    return "/" + "/".join(_escape_pointer_part(part) for part in parts)


def _required_errors(error: ValidationError) -> list[str]:
    if not isinstance(error.instance, Mapping) or not isinstance(error.validator_value, list):
        return [f"{_pointer(list(error.absolute_path))}: required property is missing"]

    missing = sorted(str(name) for name in error.validator_value if str(name) not in error.instance)
    base = list(error.absolute_path)
    return [f"{_pointer([*base, name])}: required property is missing" for name in missing]


def _additional_property_errors(error: ValidationError) -> list[str]:
    if not isinstance(error.instance, Mapping) or not isinstance(error.schema, Mapping):
        return [f"{_pointer(list(error.absolute_path))}: unexpected property"]

    properties = error.schema.get("properties", {})
    known = set(properties) if isinstance(properties, Mapping) else set()
    extras = sorted(str(name) for name in error.instance if name not in known)
    base = list(error.absolute_path)
    return [f"{_pointer([*base, name])}: unexpected property" for name in extras]


def _safe_schema_errors(
    contract_name: str,
    value: object,
    schema_directory: Path = SCHEMA_RELATIVE_DIRECTORY,
) -> list[str]:
    validator = Draft202012Validator(
        load_schema(contract_name, schema_directory),
        format_checker=FormatChecker(),
        registry=_schema_registry(schema_directory),
    )
    errors: list[str] = []
    for error in validator.iter_errors(value):
        if error.validator == "required":
            errors.extend(_required_errors(error))
        elif error.validator == "additionalProperties":
            errors.extend(_additional_property_errors(error))
        else:
            pointer = _pointer(list(error.absolute_path))
            errors.append(f"{pointer}: contract constraint failed ({error.validator})")
    return errors


def _cross_field_errors(contract_name: str, value: object) -> list[str]:
    if not isinstance(value, Mapping):
        return []

    errors: list[str] = []
    if contract_name == "ask-options":
        options = value.get("options")
        if isinstance(options, list):
            recommended = sum(
                1
                for option in options
                if isinstance(option, Mapping) and option.get("recommended") is True
            )
            if recommended > 1:
                errors.append("/options: at most one option may be recommended")

    if contract_name == "evidence":
        if value.get("mode") == "ci" and "attestation_head" not in value:
            errors.append("/attestation_head: required for CI evidence")
        if value.get("mode") == "ci" and value.get("attestation_governance_only") is not True:
            errors.append(
                "/attestation_governance_only: CI evidence requires governance-only attestation"
            )
        if value.get("mode") == "local" and (
            "attestation_head" in value or "attestation_governance_only" in value
        ):
            errors.append("/mode: local evidence cannot claim CI attestation")

        checks = value.get("checks")
        if value.get("conclusion") == "passed" and isinstance(checks, list):
            required = [
                check
                for check in checks
                if isinstance(check, Mapping) and check.get("required") is True
            ]
            if (
                not checks
                or not required
                or any(
                    isinstance(check, Mapping)
                    and check.get("required") is True
                    and check.get("status") != "passed"
                    for check in checks
                )
            ):
                errors.append("/conclusion: passed evidence contains an incomplete required check")

    return errors


def _validate_contract_with_schema_directory(
    contract_name: str,
    value: object,
    schema_directory: Path,
) -> list[str]:
    schema_errors = _safe_schema_errors(contract_name, value, schema_directory)
    cross_field_errors = _cross_field_errors(contract_name, value)
    return sorted(set(schema_errors + cross_field_errors))


def validate_contract(contract_name: str, value: object) -> list[str]:
    """Return stable, JSON Pointer-addressed validation errors."""
    return _validate_contract_with_schema_directory(contract_name, value, SCHEMA_RELATIVE_DIRECTORY)


def _require_valid_contract_with_schema_directory(
    contract_name: str,
    value: object,
    schema_directory: Path,
) -> None:
    errors = _validate_contract_with_schema_directory(contract_name, value, schema_directory)
    if errors:
        raise ContractValidationError(contract_name, errors)


def require_valid_contract(contract_name: str, value: object) -> None:
    """Raise a domain exception when a value violates the fixed local contract."""
    errors = validate_contract(contract_name, value)
    if errors:
        raise ContractValidationError(contract_name, errors)


def validate_task_event_consistency(
    task: Mapping[str, object],
    events: Sequence[Mapping[str, object]],
) -> list[str]:
    """Verify that a materialized task matches the last recorded event."""
    if events and task.get("current_state") != events[-1].get("to_state"):
        return ["/current_state: does not match the last event to_state"]
    return []
