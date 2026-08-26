"""Pure deterministic decisions for immutable runtime observations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError
from aiflow.observation import Observation, ObservationKind, serialize_observation


class DecisionDisposition(str, Enum):
    RECORD = "record"
    ESCALATE = "escalate"
    REFUSE = "refuse"


class DecisionRoute(str, Enum):
    AUTO = "AUTO"
    ASK = "ASK"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class VerificationLevel(str, Enum):
    V0 = "V0"
    V1 = "V1"
    V2 = "V2"


class DecisionReason(str, Enum):
    SCOPE_EXPANDED = "scope_expanded"
    SCOPE_RECLASSIFICATION_REQUIRED = "scope_reclassification_required"
    POLICY_CHANGED = "policy_changed"
    CONTROLLED_FILE_CHANGED = "controlled_file_changed"
    ACTION_APPROVAL_REQUIRED = "action_approval_required"
    EVIDENCE_CURRENT_AND_PASSED_REQUIRED = "evidence_current_and_passed_required"


class RequiredCondition(str, Enum):
    SCOPE_RECLASSIFICATION_AND_SPEC_FREEZE = "scope_reclassification_and_spec_freeze"
    POLICY_RECLASSIFICATION = "policy_reclassification"
    CONTROLLED_FILE_CONFIRMATION_AND_RECLASSIFICATION = (
        "controlled_file_confirmation_and_reclassification"
    )
    CURRENT_VERSION_SINGLE_USE_ACTION_APPROVAL = "current_version_single_use_action_approval"
    ARTIFACT_CURRENT_AND_PASSED = "artifact_current_and_passed"


_ROUTE_ORDER = (DecisionRoute.AUTO, DecisionRoute.ASK, DecisionRoute.REVIEW, DecisionRoute.BLOCK)


@dataclass(frozen=True)
class ObservationDecision:
    schema_version: str
    observation_sha256: str
    disposition: DecisionDisposition
    reason_code: DecisionReason
    current_route: DecisionRoute
    current_verification_level: VerificationLevel
    execution_allowed: bool
    required_conditions: tuple[RequiredCondition, ...]
    target_route: DecisionRoute | None = None


def _invalid() -> ContractError:
    return ContractError("Observation decision is invalid", code="OBSERVATION_DECISION_INVALID")


def observation_digest(observation: Observation) -> str:
    """Hash exactly the canonical serialized observation bytes."""
    if not isinstance(observation, Observation):
        raise _invalid()
    canonical = json.dumps(
        serialize_observation(observation),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _decision(
    observation: Observation,
    *,
    disposition: DecisionDisposition,
    reason_code: DecisionReason,
    current_route: DecisionRoute,
    current_verification_level: VerificationLevel,
    conditions: tuple[RequiredCondition, ...],
    target_route: DecisionRoute | None = None,
) -> ObservationDecision:
    return ObservationDecision(
        schema_version="1.0",
        observation_sha256=observation_digest(observation),
        disposition=disposition,
        reason_code=reason_code,
        current_route=current_route,
        current_verification_level=current_verification_level,
        execution_allowed=False,
        required_conditions=conditions,
        target_route=target_route,
    )


def _matches_matrix(decision: ObservationDecision) -> bool:
    """Keep parser and serializer closed over the fixed Chapter 12.2 matrix."""
    conditions = decision.required_conditions
    route = decision.current_route
    if decision.reason_code is DecisionReason.SCOPE_EXPANDED:
        return (
            decision.disposition is DecisionDisposition.ESCALATE
            and route in {DecisionRoute.AUTO, DecisionRoute.ASK}
            and decision.target_route is DecisionRoute.REVIEW
            and conditions == (RequiredCondition.SCOPE_RECLASSIFICATION_AND_SPEC_FREEZE,)
        )
    if decision.reason_code is DecisionReason.SCOPE_RECLASSIFICATION_REQUIRED:
        return (
            decision.disposition
            is (
                DecisionDisposition.REFUSE
                if route is DecisionRoute.REVIEW
                else DecisionDisposition.RECORD
            )
            and route in {DecisionRoute.REVIEW, DecisionRoute.BLOCK}
            and decision.target_route is None
            and conditions == (RequiredCondition.SCOPE_RECLASSIFICATION_AND_SPEC_FREEZE,)
        )
    if decision.reason_code is DecisionReason.POLICY_CHANGED:
        if route is DecisionRoute.BLOCK:
            return (
                decision.disposition is DecisionDisposition.RECORD
                and decision.target_route is None
                and conditions == (RequiredCondition.POLICY_RECLASSIFICATION,)
            )
        return (
            decision.disposition is DecisionDisposition.ESCALATE
            and route in {DecisionRoute.AUTO, DecisionRoute.ASK, DecisionRoute.REVIEW}
            and decision.target_route is DecisionRoute.REVIEW
            and conditions == (RequiredCondition.POLICY_RECLASSIFICATION,)
        )
    if decision.reason_code is DecisionReason.CONTROLLED_FILE_CHANGED:
        return (
            decision.disposition
            is (
                DecisionDisposition.RECORD
                if route is DecisionRoute.BLOCK
                else DecisionDisposition.REFUSE
            )
            and decision.target_route is None
            and conditions == (RequiredCondition.CONTROLLED_FILE_CONFIRMATION_AND_RECLASSIFICATION,)
        )
    if decision.reason_code is DecisionReason.ACTION_APPROVAL_REQUIRED:
        return (
            decision.disposition is DecisionDisposition.REFUSE
            and decision.target_route is None
            and conditions == (RequiredCondition.CURRENT_VERSION_SINGLE_USE_ACTION_APPROVAL,)
        )
    if decision.reason_code is DecisionReason.EVIDENCE_CURRENT_AND_PASSED_REQUIRED:
        return (
            decision.disposition
            is (
                DecisionDisposition.RECORD
                if route is DecisionRoute.BLOCK
                else DecisionDisposition.REFUSE
            )
            and decision.target_route is None
            and conditions == (RequiredCondition.ARTIFACT_CURRENT_AND_PASSED,)
        )
    return False


def decide_observation(
    observation: Observation,
    current_route: DecisionRoute,
    current_verification_level: VerificationLevel,
) -> ObservationDecision:
    """Map a current observation to a non-authorizing, monotonic disposition."""
    if not isinstance(observation, Observation):
        raise _invalid()
    if not isinstance(current_route, DecisionRoute) or not isinstance(
        current_verification_level, VerificationLevel
    ):
        raise _invalid()
    if observation.kind is ObservationKind.SCOPE_OUT_OF_BOUNDS:
        if current_route in {DecisionRoute.AUTO, DecisionRoute.ASK}:
            return _decision(
                observation,
                disposition=DecisionDisposition.ESCALATE,
                reason_code=DecisionReason.SCOPE_EXPANDED,
                current_route=current_route,
                current_verification_level=current_verification_level,
                conditions=(RequiredCondition.SCOPE_RECLASSIFICATION_AND_SPEC_FREEZE,),
                target_route=DecisionRoute.REVIEW,
            )
        if current_route is DecisionRoute.REVIEW:
            return _decision(
                observation,
                disposition=DecisionDisposition.REFUSE,
                reason_code=DecisionReason.SCOPE_RECLASSIFICATION_REQUIRED,
                current_route=current_route,
                current_verification_level=current_verification_level,
                conditions=(RequiredCondition.SCOPE_RECLASSIFICATION_AND_SPEC_FREEZE,),
            )
        return _decision(
            observation,
            disposition=DecisionDisposition.RECORD,
            reason_code=DecisionReason.SCOPE_RECLASSIFICATION_REQUIRED,
            current_route=current_route,
            current_verification_level=current_verification_level,
            conditions=(RequiredCondition.SCOPE_RECLASSIFICATION_AND_SPEC_FREEZE,),
        )
    if observation.kind is ObservationKind.POLICY_CHANGED:
        if current_route is DecisionRoute.BLOCK:
            return _decision(
                observation,
                disposition=DecisionDisposition.RECORD,
                reason_code=DecisionReason.POLICY_CHANGED,
                current_route=current_route,
                current_verification_level=current_verification_level,
                conditions=(RequiredCondition.POLICY_RECLASSIFICATION,),
            )
        return _decision(
            observation,
            disposition=DecisionDisposition.ESCALATE,
            reason_code=DecisionReason.POLICY_CHANGED,
            current_route=current_route,
            current_verification_level=current_verification_level,
            conditions=(RequiredCondition.POLICY_RECLASSIFICATION,),
            target_route=DecisionRoute.REVIEW,
        )
    if observation.kind is ObservationKind.CONTROLLED_FILE_CHANGED:
        if current_route is DecisionRoute.BLOCK:
            return _decision(
                observation,
                disposition=DecisionDisposition.RECORD,
                reason_code=DecisionReason.CONTROLLED_FILE_CHANGED,
                current_route=current_route,
                current_verification_level=current_verification_level,
                conditions=(RequiredCondition.CONTROLLED_FILE_CONFIRMATION_AND_RECLASSIFICATION,),
            )
        return _decision(
            observation,
            disposition=DecisionDisposition.REFUSE,
            reason_code=DecisionReason.CONTROLLED_FILE_CHANGED,
            current_route=current_route,
            current_verification_level=current_verification_level,
            conditions=(RequiredCondition.CONTROLLED_FILE_CONFIRMATION_AND_RECLASSIFICATION,),
        )
    if observation.kind is ObservationKind.HIGH_RISK_COMMAND:
        return _decision(
            observation,
            disposition=DecisionDisposition.REFUSE,
            reason_code=DecisionReason.ACTION_APPROVAL_REQUIRED,
            current_route=current_route,
            current_verification_level=current_verification_level,
            conditions=(RequiredCondition.CURRENT_VERSION_SINGLE_USE_ACTION_APPROVAL,),
        )
    if observation.kind is ObservationKind.EVIDENCE_MISSING:
        if current_route is DecisionRoute.BLOCK:
            return _decision(
                observation,
                disposition=DecisionDisposition.RECORD,
                reason_code=DecisionReason.EVIDENCE_CURRENT_AND_PASSED_REQUIRED,
                current_route=current_route,
                current_verification_level=current_verification_level,
                conditions=(RequiredCondition.ARTIFACT_CURRENT_AND_PASSED,),
            )
        return _decision(
            observation,
            disposition=DecisionDisposition.REFUSE,
            reason_code=DecisionReason.EVIDENCE_CURRENT_AND_PASSED_REQUIRED,
            current_route=current_route,
            current_verification_level=current_verification_level,
            conditions=(RequiredCondition.ARTIFACT_CURRENT_AND_PASSED,),
        )
    raise _invalid()


def parse_observation_decision(value: object) -> ObservationDecision:
    """Parse one strict contract without accepting a route downgrade."""
    require_valid_contract("observation-decision", value)
    if not isinstance(value, dict):
        raise _invalid()
    try:
        disposition = DecisionDisposition(value["disposition"])
        current_route = DecisionRoute(value["current_route"])
        target_value = value.get("target_route")
        target_route = DecisionRoute(target_value) if isinstance(target_value, str) else None
        if target_route is not None and _ROUTE_ORDER.index(target_route) < _ROUTE_ORDER.index(
            current_route
        ):
            raise _invalid()
        if disposition is DecisionDisposition.ESCALATE and target_route is None:
            raise _invalid()
        if disposition is not DecisionDisposition.ESCALATE and target_route is not None:
            raise _invalid()
        conditions = value["required_conditions"]
        if not isinstance(conditions, list) or not all(
            isinstance(item, str) for item in conditions
        ):
            raise _invalid()
        fields = ("schema_version", "observation_sha256")
        schema_version, observation_sha256 = (value[field] for field in fields)
        execution_allowed = value["execution_allowed"]
        if (
            not isinstance(schema_version, str)
            or not isinstance(observation_sha256, str)
            or execution_allowed is not False
        ):
            raise _invalid()
        decision = ObservationDecision(
            schema_version,
            observation_sha256,
            disposition,
            DecisionReason(value["reason_code"]),
            current_route,
            VerificationLevel(value["current_verification_level"]),
            False,
            tuple(RequiredCondition(item) for item in conditions),
            target_route,
        )
        if not _matches_matrix(decision):
            raise _invalid()
        return decision
    except (KeyError, TypeError, ValueError) as error:
        raise _invalid() from error


def serialize_observation_decision(decision: ObservationDecision) -> dict[str, object]:
    """Return a fresh canonical JSON-compatible decision representation."""
    if not isinstance(decision, ObservationDecision):
        raise _invalid()
    value: dict[str, object] = {
        "schema_version": decision.schema_version,
        "observation_sha256": decision.observation_sha256,
        "disposition": decision.disposition.value,
        "reason_code": decision.reason_code.value,
        "current_route": decision.current_route.value,
        "current_verification_level": decision.current_verification_level.value,
        "execution_allowed": decision.execution_allowed,
        "required_conditions": [condition.value for condition in decision.required_conditions],
    }
    if decision.target_route is not None:
        value["target_route"] = decision.target_route.value
    require_valid_contract("observation-decision", value)
    parsed = parse_observation_decision(value)
    if parsed != decision:
        raise _invalid()
    return value
