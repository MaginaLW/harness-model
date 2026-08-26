"""Pure, immutable types for Chapter 12 runtime observations.

This module deliberately validates and represents facts only.  It does not read a
repository, consult Policy, persist an event, or decide an escalation/refusal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError


class ObservationKind(str, Enum):
    SCOPE_OUT_OF_BOUNDS = "scope_out_of_bounds"
    POLICY_CHANGED = "policy_changed"
    CONTROLLED_FILE_CHANGED = "controlled_file_changed"
    HIGH_RISK_COMMAND = "high_risk_command"
    EVIDENCE_MISSING = "evidence_missing"


class ObservationSource(str, Enum):
    HOOK_PRE_COMMIT = "hook_pre_commit"
    HOOK_PRE_COMMAND = "hook_pre_command"
    CLI = "cli"
    CI = "ci"


class HighRiskAction(str, Enum):
    PUSH = "push"
    MERGE = "merge"
    DEPLOY = "deploy"
    DELETE = "delete"
    SECRET_EXPORT = "secret_export"
    PAID_EXTERNAL_CALL = "paid_external_call"


class EvidenceArtifact(str, Enum):
    CLASSIFICATION = "classification"
    SPECIFICATION = "specification"
    DESIGN_REVIEW = "design_review"
    SPEC_APPROVAL = "spec_approval"
    EVIDENCE = "evidence"
    VERIFICATION_SNAPSHOT = "verification_snapshot"
    TARGETED_MUTATION_EVIDENCE = "targeted_mutation_evidence"
    IMPLEMENTATION_REVIEW = "implementation_review"
    CODE_APPROVAL = "code_approval"
    ACTION_APPROVAL = "action_approval"
    CI_EVIDENCE = "ci_evidence"


class EvidenceReason(str, Enum):
    MISSING = "missing"
    INVALID = "invalid"
    STALE = "stale"
    NOT_PASSED = "not_passed"


@dataclass(frozen=True)
class PathsSummary:
    paths: tuple[str, ...]


@dataclass(frozen=True)
class CommandSummary:
    action: HighRiskAction
    target_ref: str


@dataclass(frozen=True)
class EvidenceSummary:
    artifact: EvidenceArtifact
    reason_code: EvidenceReason


ObservationSummary: TypeAlias = PathsSummary | CommandSummary | EvidenceSummary


@dataclass(frozen=True)
class Observation:
    schema_version: str
    task_id: str
    base_commit: str
    subject_commit: str
    policy_sha256: str
    source: ObservationSource
    kind: ObservationKind
    summary: ObservationSummary


_PATH_KINDS = frozenset(
    {
        ObservationKind.SCOPE_OUT_OF_BOUNDS,
        ObservationKind.POLICY_CHANGED,
        ObservationKind.CONTROLLED_FILE_CHANGED,
    }
)


def _parse_error() -> ContractError:
    """Return a stable error without including any caller-controlled data."""
    return ContractError("Observation payload is invalid", code="OBSERVATION_INVALID")


def parse_observation(value: object) -> Observation:
    """Validate one JSON-compatible observation and return an immutable value."""
    require_valid_contract("observation", value)
    if not isinstance(value, dict):  # schema validation makes this defensive only.
        raise _parse_error()
    try:
        kind = ObservationKind(value["kind"])
        source = ObservationSource(value["source"])
        summary_value = value["summary"]
        if not isinstance(summary_value, dict):
            raise _parse_error()
        if kind in _PATH_KINDS:
            paths = summary_value.get("paths")
            if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
                raise _parse_error()
            summary: ObservationSummary = PathsSummary(tuple(paths))
        elif kind is ObservationKind.HIGH_RISK_COMMAND:
            action = summary_value.get("action")
            target_ref = summary_value.get("target_ref")
            if not isinstance(action, str) or not isinstance(target_ref, str):
                raise _parse_error()
            summary = CommandSummary(HighRiskAction(action), target_ref)
        else:
            artifact = summary_value.get("artifact")
            reason_code = summary_value.get("reason_code")
            if not isinstance(artifact, str) or not isinstance(reason_code, str):
                raise _parse_error()
            summary = EvidenceSummary(EvidenceArtifact(artifact), EvidenceReason(reason_code))
        schema_version = value.get("schema_version")
        task_id = value.get("task_id")
        base_commit = value.get("base_commit")
        subject_commit = value.get("subject_commit")
        policy_sha256 = value.get("policy_sha256")
        if not isinstance(schema_version, str):
            raise _parse_error()
        if not isinstance(task_id, str):
            raise _parse_error()
        if not isinstance(base_commit, str):
            raise _parse_error()
        if not isinstance(subject_commit, str):
            raise _parse_error()
        if not isinstance(policy_sha256, str):
            raise _parse_error()
        return Observation(
            schema_version=schema_version,
            task_id=task_id,
            base_commit=base_commit,
            subject_commit=subject_commit,
            policy_sha256=policy_sha256,
            source=source,
            kind=kind,
            summary=summary,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise _parse_error() from error


def serialize_observation(observation: Observation) -> dict[str, object]:
    """Return a fresh deterministic JSON-compatible representation."""
    if not isinstance(observation, Observation):
        raise _parse_error()
    summary: dict[str, object]
    if isinstance(observation.summary, PathsSummary):
        summary = {"paths": list(observation.summary.paths)}
    elif isinstance(observation.summary, CommandSummary):
        summary = {
            "action": observation.summary.action.value,
            "target_ref": observation.summary.target_ref,
        }
    elif isinstance(observation.summary, EvidenceSummary):
        summary = {
            "artifact": observation.summary.artifact.value,
            "reason_code": observation.summary.reason_code.value,
        }
    else:
        raise _parse_error()
    value: dict[str, object] = {
        "schema_version": observation.schema_version,
        "task_id": observation.task_id,
        "base_commit": observation.base_commit,
        "subject_commit": observation.subject_commit,
        "policy_sha256": observation.policy_sha256,
        "source": observation.source.value,
        "kind": observation.kind.value,
        "summary": summary,
    }
    require_valid_contract("observation", value)
    return value
