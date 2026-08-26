"""Focused tests for deterministic observation decision mapping."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from aiflow.contracts import ContractValidationError, validate_contract
from aiflow.errors import ContractError
from aiflow.observation import parse_observation
from aiflow.observation_decision import (
    DecisionDisposition,
    DecisionRoute,
    ObservationDecision,
    RequiredCondition,
    VerificationLevel,
    decide_observation,
    observation_digest,
    parse_observation_decision,
    serialize_observation_decision,
)


def _observation(kind: str, summary: dict[str, object], source: str = "cli") -> object:
    return parse_observation(
        {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "base_commit": "1" * 40,
            "subject_commit": "2" * 40,
            "policy_sha256": "a" * 64,
            "source": source,
            "kind": kind,
            "summary": summary,
        }
    )


_SUMMARIES = {
    "scope_out_of_bounds": {"paths": ["src/outside.py"]},
    "policy_changed": {"paths": [".ai/policy/routing.yaml"]},
    "controlled_file_changed": {"paths": [".github/workflows/gate.yml"]},
    "high_risk_command": {"action": "push", "target_ref": "origin/main"},
    "evidence_missing": {"artifact": "evidence", "reason_code": "stale"},
}


@pytest.mark.parametrize("kind", sorted(_SUMMARIES))
@pytest.mark.parametrize("route", list(DecisionRoute))
@pytest.mark.parametrize("level", list(VerificationLevel))
@pytest.mark.parametrize("source", ["hook_pre_commit", "hook_pre_command", "cli", "ci"])
def test_matrix_is_source_independent_non_authorizing_and_monotonic(
    kind: str, route: DecisionRoute, level: VerificationLevel, source: str
) -> None:
    decision = decide_observation(_observation(kind, _SUMMARIES[kind], source), route, level)
    assert decision.execution_allowed is False
    assert decision.current_route is route
    assert decision.current_verification_level is level
    assert decision.required_conditions
    if decision.target_route is not None:
        assert list(DecisionRoute).index(decision.target_route) >= list(DecisionRoute).index(route)
        assert decision.disposition is DecisionDisposition.ESCALATE


@pytest.mark.parametrize("kind", sorted(_SUMMARIES))
@pytest.mark.parametrize("route", list(DecisionRoute))
@pytest.mark.parametrize("level", list(VerificationLevel))
def test_all_sources_produce_identical_decision_semantics(
    kind: str, route: DecisionRoute, level: VerificationLevel
) -> None:
    decisions = [
        decide_observation(_observation(kind, _SUMMARIES[kind], source), route, level)
        for source in ("hook_pre_commit", "hook_pre_command", "cli", "ci")
    ]
    semantics = {
        (
            decision.schema_version,
            decision.disposition,
            decision.reason_code,
            decision.current_route,
            decision.current_verification_level,
            decision.execution_allowed,
            decision.required_conditions,
            decision.target_route,
        )
        for decision in decisions
    }
    assert len(semantics) == 1
    assert len({decision.observation_sha256 for decision in decisions}) == 4


def test_policy_change_at_review_is_same_route_version_invalidation() -> None:
    decision = decide_observation(
        _observation("policy_changed", _SUMMARIES["policy_changed"]),
        DecisionRoute.REVIEW,
        VerificationLevel.V2,
    )
    assert decision.disposition is DecisionDisposition.ESCALATE
    assert decision.target_route is DecisionRoute.REVIEW
    assert decision.required_conditions == (RequiredCondition.POLICY_RECLASSIFICATION,)


@pytest.mark.parametrize(
    ("kind", "reason", "condition"),
    [
        (
            "scope_out_of_bounds",
            "scope_reclassification_required",
            "scope_reclassification_and_spec_freeze",
        ),
        ("policy_changed", "policy_changed", "policy_reclassification"),
        (
            "controlled_file_changed",
            "controlled_file_changed",
            "controlled_file_confirmation_and_reclassification",
        ),
        ("evidence_missing", "evidence_current_and_passed_required", "artifact_current_and_passed"),
    ],
)
def test_block_records_preserve_the_observation_reason_and_recovery_condition(
    kind: str, reason: str, condition: str
) -> None:
    decision = decide_observation(
        _observation(kind, _SUMMARIES[kind]), DecisionRoute.BLOCK, VerificationLevel.V1
    )
    assert decision.disposition is DecisionDisposition.RECORD
    assert decision.reason_code.value == reason
    assert tuple(item.value for item in decision.required_conditions) == (condition,)
    assert parse_observation_decision(serialize_observation_decision(decision)) == decision


@pytest.mark.parametrize(
    ("kind", "route", "disposition", "target"),
    [
        (
            "scope_out_of_bounds",
            DecisionRoute.AUTO,
            DecisionDisposition.ESCALATE,
            DecisionRoute.REVIEW,
        ),
        (
            "scope_out_of_bounds",
            DecisionRoute.ASK,
            DecisionDisposition.ESCALATE,
            DecisionRoute.REVIEW,
        ),
        ("scope_out_of_bounds", DecisionRoute.REVIEW, DecisionDisposition.REFUSE, None),
        ("scope_out_of_bounds", DecisionRoute.BLOCK, DecisionDisposition.RECORD, None),
        ("policy_changed", DecisionRoute.AUTO, DecisionDisposition.ESCALATE, DecisionRoute.REVIEW),
        ("policy_changed", DecisionRoute.ASK, DecisionDisposition.ESCALATE, DecisionRoute.REVIEW),
        (
            "policy_changed",
            DecisionRoute.REVIEW,
            DecisionDisposition.ESCALATE,
            DecisionRoute.REVIEW,
        ),
        ("policy_changed", DecisionRoute.BLOCK, DecisionDisposition.RECORD, None),
        ("controlled_file_changed", DecisionRoute.AUTO, DecisionDisposition.REFUSE, None),
        ("controlled_file_changed", DecisionRoute.ASK, DecisionDisposition.REFUSE, None),
        ("controlled_file_changed", DecisionRoute.REVIEW, DecisionDisposition.REFUSE, None),
        ("controlled_file_changed", DecisionRoute.BLOCK, DecisionDisposition.RECORD, None),
        ("high_risk_command", DecisionRoute.AUTO, DecisionDisposition.REFUSE, None),
        ("high_risk_command", DecisionRoute.ASK, DecisionDisposition.REFUSE, None),
        ("high_risk_command", DecisionRoute.REVIEW, DecisionDisposition.REFUSE, None),
        ("high_risk_command", DecisionRoute.BLOCK, DecisionDisposition.REFUSE, None),
        ("evidence_missing", DecisionRoute.AUTO, DecisionDisposition.REFUSE, None),
        ("evidence_missing", DecisionRoute.ASK, DecisionDisposition.REFUSE, None),
        ("evidence_missing", DecisionRoute.REVIEW, DecisionDisposition.REFUSE, None),
        ("evidence_missing", DecisionRoute.BLOCK, DecisionDisposition.RECORD, None),
    ],
)
def test_fixed_kind_route_matrix(
    kind: str,
    route: DecisionRoute,
    disposition: DecisionDisposition,
    target: DecisionRoute | None,
) -> None:
    decision = decide_observation(_observation(kind, _SUMMARIES[kind]), route, VerificationLevel.V0)
    assert (decision.disposition, decision.target_route) == (disposition, target)


def test_high_risk_command_refuses_even_when_route_is_block() -> None:
    decision = decide_observation(
        _observation("high_risk_command", _SUMMARIES["high_risk_command"]),
        DecisionRoute.BLOCK,
        VerificationLevel.V1,
    )
    assert decision.disposition is DecisionDisposition.REFUSE
    assert decision.target_route is None


def test_digest_is_canonical_and_source_sensitive() -> None:
    observation = _observation("scope_out_of_bounds", _SUMMARIES["scope_out_of_bounds"])
    again = _observation("scope_out_of_bounds", _SUMMARIES["scope_out_of_bounds"])
    changed = _observation("scope_out_of_bounds", _SUMMARIES["scope_out_of_bounds"], "ci")
    assert observation_digest(observation) == observation_digest(again)
    assert observation_digest(observation) != observation_digest(changed)
    assert len(observation_digest(observation)) == 64


def test_parse_serialize_round_trip_is_frozen_and_does_not_mutate_input() -> None:
    decision = decide_observation(
        _observation("scope_out_of_bounds", _SUMMARIES["scope_out_of_bounds"]),
        DecisionRoute.AUTO,
        VerificationLevel.V1,
    )
    value = serialize_observation_decision(decision)
    original = deepcopy(value)
    parsed = parse_observation_decision(value)
    assert parsed == decision
    assert serialize_observation_decision(parsed) == value
    with pytest.raises(FrozenInstanceError):
        parsed.execution_allowed = True  # type: ignore[misc]
    assert value == original


@pytest.mark.parametrize(
    ("replacement", "schema_rejects"),
    [
        ({"disposition": "refuse", "target_route": "REVIEW"}, True),
        ({"disposition": "escalate", "target_route": "AUTO"}, True),
        ({"disposition": "escalate", "target_route": "REVIEW", "current_route": "BLOCK"}, False),
    ],
)
def test_parser_rejects_illegal_target_shape_or_downgrade(
    replacement: dict[str, str], schema_rejects: bool
) -> None:
    value = serialize_observation_decision(
        decide_observation(
            _observation("scope_out_of_bounds", _SUMMARIES["scope_out_of_bounds"]),
            DecisionRoute.AUTO,
            VerificationLevel.V1,
        )
    )
    value.update(replacement)
    assert bool(validate_contract("observation-decision", value)) is schema_rejects
    with pytest.raises(ContractError):
        parse_observation_decision(value)


@pytest.mark.parametrize(
    ("replacement", "error_code"),
    [
        ({"reason_code": "policy_changed"}, "OBSERVATION_DECISION_INVALID"),
        ({"required_conditions": ["policy_reclassification"]}, "OBSERVATION_DECISION_INVALID"),
        ({"disposition": "record", "target_route": "REVIEW"}, "CONTRACT_VALIDATION_FAILED"),
        (
            {"current_route": "REVIEW", "disposition": "escalate", "target_route": "BLOCK"},
            "OBSERVATION_DECISION_INVALID",
        ),
    ],
)
def test_parser_rejects_schema_valid_but_matrix_inconsistent_payloads(
    replacement: dict[str, object], error_code: str
) -> None:
    value = serialize_observation_decision(
        decide_observation(
            _observation("scope_out_of_bounds", _SUMMARIES["scope_out_of_bounds"]),
            DecisionRoute.AUTO,
            VerificationLevel.V1,
        )
    )
    value.update(replacement)
    with pytest.raises(ContractError) as caught:
        parse_observation_decision(value)
    assert caught.value.code == error_code


def test_unknown_sensitive_values_are_not_echoed() -> None:
    value = {
        "schema_version": "1.0",
        "observation_sha256": "a" * 64,
        "disposition": "refuse",
        "reason_code": "action_approval_required",
        "current_route": "REVIEW",
        "current_verification_level": "V1",
        "execution_allowed": False,
        "required_conditions": ["current_version_single_use_action_approval"],
        "stdout": "SUPER_SECRET_VALUE",
    }
    with pytest.raises(ContractValidationError) as caught:
        parse_observation_decision(value)
    assert "SUPER_SECRET_VALUE" not in str(caught.value)


def test_serializer_rejects_internally_inconsistent_manual_value() -> None:
    decision = ObservationDecision(
        "1.0",
        "a" * 64,
        DecisionDisposition.REFUSE,
        decide_observation(
            _observation("high_risk_command", _SUMMARIES["high_risk_command"]),
            DecisionRoute.AUTO,
            VerificationLevel.V1,
        ).reason_code,
        DecisionRoute.AUTO,
        VerificationLevel.V1,
        False,
        (RequiredCondition.CURRENT_VERSION_SINGLE_USE_ACTION_APPROVAL,),
        DecisionRoute.REVIEW,
    )
    with pytest.raises(ContractValidationError):
        serialize_observation_decision(decision)
