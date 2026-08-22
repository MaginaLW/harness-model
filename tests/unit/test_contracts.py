"""Contract schema and validation regression tests."""

from __future__ import annotations

import json
import shutil
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema.validators import Draft202012Validator

from aiflow.contracts import (
    ContractValidationError,
    load_schema,
    require_valid_contract,
    validate_contract,
    validate_task_event_consistency,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "contracts"
VALID_ROOT = FIXTURE_ROOT / "valid"
INVALID_ROOT = FIXTURE_ROOT / "invalid"
CONTRACT_NAMES = {
    "approval",
    "ask-options",
    "classification",
    "decision-unit",
    "event",
    "evidence",
    "task",
}
pytestmark = pytest.mark.contract


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object fixture."""
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def valid_fixture(contract_name: str) -> dict[str, Any]:
    """Load the canonical valid fixture for a contract."""
    return load_json(VALID_ROOT / f"{contract_name}.json")


def contract_name_for(path: Path) -> str:
    """Derive a contract name from a fixture file name."""
    return path.name.split(".", maxsplit=1)[0]


def test_fixture_matrix_is_complete() -> None:
    valid_names = {path.stem for path in VALID_ROOT.glob("*.json")}
    assert valid_names == CONTRACT_NAMES

    for contract_name in CONTRACT_NAMES:
        invalid = list(INVALID_ROOT.glob(f"{contract_name}.*.json"))
        assert {path.name.split(".")[1] for path in invalid} == {"extra", "invalid", "missing"}


@pytest.mark.parametrize("path", sorted(VALID_ROOT.glob("*.json")))
def test_valid_fixtures_satisfy_their_contract(path: Path) -> None:
    contract_name = contract_name_for(path)
    schema = load_schema(contract_name)
    Draft202012Validator.check_schema(schema)

    assert validate_contract(contract_name, load_json(path)) == []


@pytest.mark.parametrize("path", sorted(INVALID_ROOT.glob("*.json")))
def test_invalid_fixtures_have_stable_locatable_errors(path: Path) -> None:
    contract_name = contract_name_for(path)
    value = load_json(path)

    first = validate_contract(contract_name, value)
    second = validate_contract(contract_name, value)

    assert first
    assert first == second
    assert first == sorted(first)
    assert all(error.startswith("/") for error in first)


def test_validation_errors_do_not_echo_unknown_sensitive_values() -> None:
    value = load_json(INVALID_ROOT / "task.extra.json")

    errors = validate_contract("task", value)

    assert "SUPER_SECRET_VALUE" not in "\n".join(errors)


def test_invalid_contract_can_raise_a_domain_exception() -> None:
    value = load_json(INVALID_ROOT / "approval.missing.json")

    with pytest.raises(ContractValidationError) as caught:
        require_valid_contract("approval", value)

    assert caught.value.contract_name == "approval"
    assert caught.value.errors == validate_contract("approval", value)


def test_unknown_contract_name_cannot_escape_the_schema_directory() -> None:
    with pytest.raises(KeyError):
        load_schema("../task")


def test_schema_loader_accepts_a_different_checkout_path(tmp_path: Path) -> None:
    copied_schemas = tmp_path / "different-absolute-checkout" / ".ai" / "schemas"
    shutil.copytree(REPOSITORY_ROOT / ".ai" / "schemas", copied_schemas)

    schema = load_schema("task", copied_schemas)

    assert schema["title"] == "AI Flow task"


@pytest.mark.parametrize("contract_name", ["review-context", "review-record"])
def test_structured_review_templates_satisfy_registered_contracts(contract_name: str) -> None:
    template = REPOSITORY_ROOT / ".ai" / "templates" / f"{contract_name}.json"
    value = load_json(template)

    Draft202012Validator.check_schema(load_schema(contract_name))
    assert validate_contract(contract_name, value) == []


def test_code_approval_requires_subject_commit() -> None:
    approval = valid_fixture("approval")
    approval.pop("subject_commit")

    errors = validate_contract("approval", approval)
    assert any(error.startswith("/subject_commit:") for error in errors)


def test_ci_evidence_requires_attestation_head() -> None:
    evidence = valid_fixture("evidence")
    evidence["mode"] = "ci"

    errors = validate_contract("evidence", evidence)
    assert "/attestation_head: required for CI evidence" in errors
    assert (
        "/attestation_governance_only: CI evidence requires governance-only attestation" in errors
    )


def test_passed_evidence_cannot_contain_a_failed_check() -> None:
    evidence = valid_fixture("evidence")
    evidence["checks"][0]["status"] = "failed"

    assert validate_contract("evidence", evidence) == [
        "/conclusion: passed evidence contains an incomplete required check"
    ]


def test_ask_options_allow_at_most_one_recommendation() -> None:
    ask_options = valid_fixture("ask-options")
    ask_options["options"][1]["recommended"] = True

    assert validate_contract("ask-options", ask_options) == [
        "/options: at most one option may be recommended"
    ]


def test_ask_options_require_between_two_and_four_choices() -> None:
    ask_options = valid_fixture("ask-options")
    ask_options["options"] = ask_options["options"][:1]

    assert validate_contract("ask-options", ask_options) == [
        "/options: contract constraint failed (minItems)"
    ]


def test_materialized_task_state_must_match_the_last_event() -> None:
    task = valid_fixture("task")
    event = valid_fixture("event")

    assert validate_task_event_consistency(task, [event]) == [
        "/current_state: does not match the last event to_state"
    ]


def test_repository_id_is_a_single_stable_uuid_v4(tmp_path: Path) -> None:
    source = REPOSITORY_ROOT / ".ai" / "repository-id"
    raw = source.read_bytes()
    value = raw.decode("utf-8").strip()

    parsed = uuid.UUID(value)
    assert parsed.version == 4
    assert raw.splitlines() == [value.encode("utf-8")]

    copied_ai = tmp_path / "different-absolute-checkout" / ".ai"
    shutil.copytree(REPOSITORY_ROOT / ".ai", copied_ai)
    copied = copied_ai / "repository-id"
    assert copied.read_text(encoding="utf-8").strip() == value


def test_validation_does_not_mutate_the_input() -> None:
    value = valid_fixture("evidence")
    original = deepcopy(value)

    validate_contract("evidence", value)

    assert value == original
