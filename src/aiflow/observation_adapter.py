"""Bounded CLI and CI adapters for immutable runtime observations."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from aiflow.errors import ContractError
from aiflow.observation import Observation, ObservationSource, parse_observation
from aiflow.observation_decision import ObservationDecision, serialize_observation_decision
from aiflow.observation_service import apply_observation, evaluate_observation


class ObservationMode(str, Enum):
    """The three closed observation adapter modes."""

    APPLY = "apply"
    DRY_RUN = "dry-run"
    CI = "ci"


@dataclass(frozen=True)
class ObservationAdapterResult:
    """One safe machine-readable observation adapter result."""

    task_id: str
    mode: ObservationMode
    ledger_effect: str
    decision: ObservationDecision
    audit_event: Mapping[str, object] | None = None
    escalation_event: Mapping[str, object] | None = None


def _invalid(code: str = "OBSERVATION_ADAPTER_INVALID") -> ContractError:
    return ContractError("Observation adapter input is invalid", code=code)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise _invalid("OBSERVATION_INPUT_INVALID")
        value[key] = item
    return value


def load_observation_file(path: Path) -> Observation:
    """Read exactly one UTF-8 JSON object without echoing caller-controlled data."""
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_unique_json_object)
    except ContractError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _invalid("OBSERVATION_INPUT_INVALID") from error
    if not isinstance(value, dict):
        raise _invalid("OBSERVATION_INPUT_INVALID")
    return parse_observation(value)


def parse_observation_mode(value: object) -> ObservationMode:
    """Parse a closed adapter mode with a stable non-reflective error."""
    try:
        return ObservationMode(value)
    except (TypeError, ValueError) as error:
        raise _invalid("OBSERVATION_MODE_INVALID") from error


def _event_reference(event: Mapping[str, object] | None) -> dict[str, object] | None:
    if event is None:
        return None
    event_type = event.get("event_type")
    sequence = event.get("sequence")
    if (
        not isinstance(event_type, str)
        or not isinstance(sequence, int)
        or isinstance(sequence, bool)
    ):
        raise _invalid("OBSERVATION_RESULT_INVALID")
    return {"event_type": event_type, "sequence": sequence}


def run_observation(
    repository_root: Path,
    task_id: str,
    observation: Observation,
    *,
    mode: ObservationMode,
    actor: str | None = None,
) -> ObservationAdapterResult:
    """Apply or read-only evaluate an observation through one closed mode."""
    if not isinstance(mode, ObservationMode):
        raise _invalid("OBSERVATION_MODE_INVALID")
    if not isinstance(observation, Observation):
        raise _invalid("OBSERVATION_INVALID")
    if observation.task_id != task_id:
        raise _invalid("OBSERVATION_TASK_MISMATCH")

    if mode is ObservationMode.APPLY:
        if observation.source is not ObservationSource.CLI:
            raise _invalid("OBSERVATION_SOURCE_MODE_MISMATCH")
        if actor is None or not actor.strip():
            raise _invalid("OBSERVATION_ACTOR_REQUIRED")
        application = apply_observation(
            repository_root,
            task_id,
            observation,
            actor=actor,
        )
        return ObservationAdapterResult(
            task_id=task_id,
            mode=mode,
            ledger_effect="task_local",
            decision=application.decision,
            audit_event=application.audit_event,
            escalation_event=application.escalation_event,
        )

    if actor is not None:
        raise _invalid("OBSERVATION_ACTOR_FORBIDDEN")
    expected_source = (
        ObservationSource.CLI if mode is ObservationMode.DRY_RUN else ObservationSource.CI
    )
    if observation.source is not expected_source:
        raise _invalid("OBSERVATION_SOURCE_MODE_MISMATCH")
    decision = evaluate_observation(repository_root, task_id, observation)
    return ObservationAdapterResult(
        task_id=task_id,
        mode=mode,
        ledger_effect="none",
        decision=decision,
    )


def run_observation_file(
    repository_root: Path,
    task_id: str,
    input_path: Path,
    *,
    mode: ObservationMode,
    actor: str | None = None,
) -> ObservationAdapterResult:
    """Load and run one observation input file."""
    return run_observation(
        repository_root,
        task_id,
        load_observation_file(input_path),
        mode=mode,
        actor=actor,
    )


def serialize_observation_result(result: ObservationAdapterResult) -> dict[str, object]:
    """Return the closed JSON protocol without raw observation summaries."""
    if not isinstance(result, ObservationAdapterResult):
        raise _invalid("OBSERVATION_RESULT_INVALID")
    if result.ledger_effect not in {"none", "task_local"}:
        raise _invalid("OBSERVATION_RESULT_INVALID")
    if (result.mode is ObservationMode.APPLY) is (result.ledger_effect != "task_local"):
        raise _invalid("OBSERVATION_RESULT_INVALID")
    audit = _event_reference(result.audit_event)
    escalation = _event_reference(result.escalation_event)
    if result.mode is not ObservationMode.APPLY and (audit is not None or escalation is not None):
        raise _invalid("OBSERVATION_RESULT_INVALID")
    return {
        "schema_version": "1.0",
        "task_id": result.task_id,
        "mode": result.mode.value,
        "ledger_effect": result.ledger_effect,
        "decision": serialize_observation_decision(result.decision),
        "audit_event": audit,
        "escalation_event": escalation,
    }
