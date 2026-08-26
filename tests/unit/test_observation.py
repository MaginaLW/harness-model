"""Focused tests for the pure immutable observation type layer."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from aiflow.contracts import ContractValidationError, validate_contract
from aiflow.observation import (
    CommandSummary,
    EvidenceArtifact,
    EvidenceReason,
    EvidenceSummary,
    HighRiskAction,
    ObservationKind,
    ObservationSource,
    PathsSummary,
    parse_observation,
    serialize_observation,
)


def _payload(kind: str, summary: dict[str, object], source: str = "cli") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "base_commit": "1" * 40,
        "subject_commit": "2" * 40,
        "policy_sha256": "a" * 64,
        "source": source,
        "kind": kind,
        "summary": summary,
    }


@pytest.mark.parametrize(
    ("kind", "summary", "summary_type"),
    [
        ("scope_out_of_bounds", {"paths": ["src/a.py"]}, PathsSummary),
        ("policy_changed", {"paths": [".ai/policy/routing.yaml"]}, PathsSummary),
        ("controlled_file_changed", {"paths": [".github/workflows/gate.yml"]}, PathsSummary),
        ("high_risk_command", {"action": "push", "target_ref": "origin/main"}, CommandSummary),
        ("evidence_missing", {"artifact": "evidence", "reason_code": "stale"}, EvidenceSummary),
    ],
)
def test_parse_serialize_round_trip_for_each_kind(
    kind: str, summary: dict[str, object], summary_type: type[object]
) -> None:
    payload = _payload(kind, summary)
    parsed = parse_observation(payload)
    assert isinstance(parsed.summary, summary_type)
    assert serialize_observation(parsed) == payload
    assert parse_observation(serialize_observation(parsed)) == parsed


@pytest.mark.parametrize("source", [source.value for source in ObservationSource])
def test_parse_accepts_each_declared_source(source: str) -> None:
    parsed = parse_observation(_payload("scope_out_of_bounds", {"paths": ["src/a.py"]}, source))
    assert parsed.source.value == source


def test_parser_returns_frozen_tuple_backed_values_without_mutating_input() -> None:
    payload = _payload("scope_out_of_bounds", {"paths": ["src/a.py"]})
    original = deepcopy(payload)
    parsed = parse_observation(payload)
    assert isinstance(parsed.summary, PathsSummary)
    assert parsed.summary.paths == ("src/a.py",)
    with pytest.raises(FrozenInstanceError):
        parsed.task_id = "TASK-0002"  # type: ignore[misc]
    assert payload == original


def test_enums_are_exposed_by_the_immutable_model() -> None:
    command = parse_observation(
        _payload("high_risk_command", {"action": "merge", "target_ref": "main"})
    )
    evidence = parse_observation(
        _payload("evidence_missing", {"artifact": "code_approval", "reason_code": "not_passed"})
    )
    assert command.kind is ObservationKind.HIGH_RISK_COMMAND
    assert command.summary == CommandSummary(HighRiskAction.MERGE, "main")
    assert evidence.summary == EvidenceSummary(
        EvidenceArtifact.CODE_APPROVAL, EvidenceReason.NOT_PASSED
    )


@pytest.mark.parametrize(
    ("kind", "summary"),
    [
        ("scope_out_of_bounds", {"paths": []}),
        ("scope_out_of_bounds", {"paths": ["src/a.py", "src/a.py"]}),
        ("scope_out_of_bounds", {"paths": ["../escape.py"]}),
        ("scope_out_of_bounds", {"paths": ["C:\\\\escape.py"]}),
        ("scope_out_of_bounds", {"paths": ["src\\\\escape.py"]}),
        ("high_risk_command", {"action": "unknown", "target_ref": "main"}),
        ("high_risk_command", {"action": "push", "target_ref": "origin/main;rm"}),
        ("high_risk_command", {"action": "push", "target_ref": "$(whoami)"}),
        ("high_risk_command", {"action": "push", "target_ref": "%USERPROFILE%"}),
        ("evidence_missing", {"artifact": "evidence", "reason_code": "free text"}),
        ("evidence_missing", {"paths": ["src/a.py"]}),
    ],
)
def test_contract_rejects_unsafe_or_kind_mismatched_summaries(
    kind: str, summary: dict[str, object]
) -> None:
    errors = validate_contract("observation", _payload(kind, summary))
    assert errors
    assert all(error.startswith("/") for error in errors)


@pytest.mark.parametrize("field", ["task_id", "base_commit", "subject_commit", "policy_sha256"])
def test_contract_rejects_missing_required_bindings(field: str) -> None:
    payload = _payload("scope_out_of_bounds", {"paths": ["src/a.py"]})
    payload.pop(field)
    assert any(
        error.startswith(f"/{field}:") for error in validate_contract("observation", payload)
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task_id", "task-0001"),
        ("base_commit", "A" * 40),
        ("subject_commit", "a" * 39),
        ("policy_sha256", "A" * 64),
        ("source", "remote"),
        ("kind", "other"),
    ],
)
def test_contract_rejects_invalid_bindings_and_enums(field: str, value: str) -> None:
    payload = _payload("scope_out_of_bounds", {"paths": ["src/a.py"]})
    payload[field] = value
    assert validate_contract("observation", payload)


def test_parser_uses_contract_errors_without_echoing_sensitive_values() -> None:
    payload = _payload(
        "scope_out_of_bounds", {"paths": ["src/a.py"], "stdout": "SUPER_SECRET_VALUE"}
    )
    with pytest.raises(ContractValidationError) as caught:
        parse_observation(payload)
    assert "SUPER_SECRET_VALUE" not in str(caught.value)


def test_serialization_returns_a_fresh_json_value() -> None:
    parsed = parse_observation(_payload("scope_out_of_bounds", {"paths": ["src/a.py"]}))
    serialized = serialize_observation(parsed)
    serialized["task_id"] = "TASK-9999"
    assert parsed.task_id == "TASK-0001"
    assert serialize_observation(parsed)["task_id"] == "TASK-0001"
