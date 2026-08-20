"""Pure ASK answer validation and deterministic decision-document preparation."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any

from aiflow.classification_service import _stable_input
from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import ContractError, StateTransitionError, StorageError
from aiflow.policy import load_policy_bundle
from aiflow.specification import SpecificationAssessment, validate_specification
from aiflow.state import create_transition_event
from aiflow.storage import atomic_write_json, atomic_write_text, read_task_json, resolve_task_path
from aiflow.task_service import TransitionResult, _persist_event_and_task, load_task_record

FROZEN_DECISIONS_HEADING = "已冻结决策"
ANSWER_MARKER = "answer_pending.json"


@dataclass(frozen=True)
class AskAnswerPreparation:
    """Validated, durable content that a CLI can persist atomically."""

    event_payload: Mapping[str, object]
    decisions_markdown: str
    frozen_specification: str
    specification: SpecificationAssessment
    target_state: str


def _invalid(message: str, code: str, **details: object) -> ContractError:
    return ContractError(message, code=code, details=details)


def validate_ask_options(
    options_document: Mapping[str, object], *, task_id: str
) -> dict[str, object]:
    """Validate the machine contract plus ASK's stable cross-field constraints."""
    value = copy.deepcopy(dict(options_document))
    raw_options = value.get("options")
    if isinstance(raw_options, list) and all(isinstance(item, Mapping) for item in raw_options):
        option_ids = [item.get("option_id") for item in raw_options]
        if all(isinstance(option_id, str) for option_id in option_ids) and len(option_ids) != len(
            set(option_ids)
        ):
            raise _invalid("ASK option IDs must be unique", "ASK_OPTION_IDS_DUPLICATE")
        recommended = sum(1 for item in raw_options if item.get("recommended") is True)
        if recommended > 1:
            raise _invalid(
                "ASK options allow at most one recommendation", "ASK_RECOMMENDATION_MULTIPLE"
            )
    try:
        require_valid_contract("ask-options", value)
    except ContractError as error:
        raise _invalid("ASK options are invalid", "ASK_OPTIONS_INVALID") from error
    if value["task_id"] != task_id:
        raise _invalid("ASK options belong to a different task", "ASK_TASK_MISMATCH")

    options = value["options"]
    assert isinstance(options, list)
    return value


def target_state_after_answer(classification: Mapping[str, object]) -> str:
    """Keep mixed ASK/REVIEW tasks behind the specification-review gate."""
    entries = classification.get("classifications")
    if not isinstance(entries, list):
        raise _invalid("Classification is invalid for an ASK answer", "ASK_CLASSIFICATION_INVALID")
    routes = {
        entry.get("route")
        for entry in entries
        if isinstance(entry, Mapping) and isinstance(entry.get("route"), str)
    }
    if "ASK" not in routes:
        raise _invalid("Classification does not contain an ASK decision", "ASK_ROUTE_MISSING")
    return "WAITING_FOR_SPEC_REVIEW" if "REVIEW" in routes else "READY_TO_IMPLEMENT"


def _require_answer_identity(
    actor: str, reason: str, selected_option_id: str
) -> tuple[str, str, str]:
    normalized_actor = " ".join(actor.split())
    normalized_reason = " ".join(reason.split())
    normalized_selection = selected_option_id.strip()
    if not normalized_actor:
        raise _invalid("ASK answer actor is required", "ASK_ACTOR_INVALID")
    if not normalized_reason:
        raise _invalid("ASK answer reason is required", "ASK_REASON_REQUIRED")
    if not normalized_selection:
        raise _invalid("ASK answer selection is required", "ASK_SELECTION_INVALID")
    return normalized_actor, normalized_reason, normalized_selection


def _option_by_id(options: list[object], selected_option_id: str) -> dict[str, object]:
    matches = [
        dict(option)
        for option in options
        if isinstance(option, Mapping) and option.get("option_id") == selected_option_id
    ]
    if len(matches) != 1:
        raise _invalid("ASK selection is not one of the supplied options", "ASK_SELECTION_INVALID")
    return matches[0]


def render_decisions_markdown(
    *,
    decision_unit_id: str,
    selected_option: Mapping[str, object],
    actor: str,
    reason: str,
    answered_at: str,
) -> str:
    """Render a stable, concise human summary without inferring semantic exclusivity."""
    option_id = selected_option["option_id"]
    return (
        "# Frozen Decisions\n\n"
        f"## {decision_unit_id}\n\n"
        f"- Selected option: `{option_id}`\n"
        f"- Actor: {actor}\n"
        f"- Answered at: {answered_at}\n"
        f"- Reason: {reason}\n"
    )


def _replace_frozen_decisions_section(specification: str, section: str) -> str:
    heading = f"## {FROZEN_DECISIONS_HEADING}"
    start = specification.find(heading)
    if start < 0:
        return specification.rstrip("\n") + "\n\n" + section
    next_heading = specification.find("\n## ", start + len(heading))
    end = len(specification) if next_heading < 0 else next_heading + 1
    return specification[:start] + section + specification[end:]


def render_frozen_decision_section(
    *,
    decision_unit_id: str,
    selected_option: Mapping[str, object],
    actor: str,
    reason: str,
    answered_at: str,
) -> str:
    """Render the deterministic specification section for the selected option."""
    return (
        f"## {FROZEN_DECISIONS_HEADING}\n\n"
        f"### {decision_unit_id}\n\n"
        f"- 已选择：`{selected_option['option_id']}`\n"
        f"- 操作者：{actor}\n"
        f"- 回答时间：{answered_at}\n"
        f"- 理由：{reason}\n"
    )


def prepare_answer(
    *,
    task_state: str,
    classification: Mapping[str, object],
    specification: str,
    options_document: Mapping[str, object],
    selected_option_id: str,
    actor: str,
    reason: str,
    answered_at: str,
) -> AskAnswerPreparation:
    """Validate and prepare an ASK answer, without reading or changing task storage."""
    if task_state != "WAITING_FOR_ASK":
        raise StateTransitionError(
            "ASK answer requires a task waiting for an answer", code="ASK_STATE_INVALID"
        )
    normalized_actor, normalized_reason, selection = _require_answer_identity(
        actor, reason, selected_option_id
    )
    options = validate_ask_options(options_document, task_id=str(classification.get("task_id", "")))
    entries = classification.get("classifications")
    assert isinstance(entries, list)
    ask_entries = [
        entry for entry in entries if isinstance(entry, Mapping) and entry.get("route") == "ASK"
    ]
    if len(ask_entries) != 1:
        raise _invalid(
            "Stage-one answer requires exactly one ASK decision unit",
            "ASK_DECISION_UNIT_COUNT_UNSUPPORTED",
        )
    if ask_entries[0].get("decision_unit_id") != options.get("decision_unit_id"):
        raise _invalid(
            "ASK options do not match the pending decision unit",
            "ASK_DECISION_UNIT_MISMATCH",
        )
    target_state = target_state_after_answer(classification)
    items = options["options"]
    assert isinstance(items, list)
    selected = _option_by_id(items, selection)
    section = render_frozen_decision_section(
        decision_unit_id=str(options["decision_unit_id"]),
        selected_option=selected,
        actor=normalized_actor,
        reason=normalized_reason,
        answered_at=answered_at,
    )
    frozen_specification = _replace_frozen_decisions_section(specification, section)
    assessed = validate_specification(frozen_specification)
    options_sha256 = hashlib.sha256(
        json.dumps(options, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    payload = MappingProxyType(
        {
            "options": options,
            "selected_option_id": selection,
            "actor": normalized_actor,
            "reason": normalized_reason,
            "answered_at": answered_at,
            "specification_sha256": assessed.sha256,
            "options_sha256": options_sha256,
            "classification_input_sha256": classification.get("classification_input_sha256"),
            "policy_sha256": classification.get("policy_sha256"),
            "semantic_distinctness_verified": False,
        }
    )
    return AskAnswerPreparation(
        event_payload=payload,
        decisions_markdown=render_decisions_markdown(
            decision_unit_id=str(options["decision_unit_id"]),
            selected_option=selected,
            actor=normalized_actor,
            reason=normalized_reason,
            answered_at=answered_at,
        ),
        frozen_specification=assessed.normalized,
        specification=assessed,
        target_state=target_state,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_options_file(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StorageError(
            "Could not read ASK options file",
            code="ASK_OPTIONS_READ_FAILED",
            details={"filename": path.name},
        ) from error
    if not isinstance(value, Mapping):
        raise ContractError("ASK options must be an object", code="ASK_OPTIONS_INVALID")
    return value


def _validate_marker(value: object, task_id: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("task_id") != task_id:
        raise StorageError("ASK answer recovery marker is invalid", code="ASK_RECOVERY_INVALID")
    task = value.get("task")
    event = value.get("event")
    specification = value.get("specification")
    decisions = value.get("decisions")
    if (
        not isinstance(task, dict)
        or not isinstance(event, dict)
        or not isinstance(specification, str)
        or not isinstance(decisions, str)
    ):
        raise StorageError("ASK answer recovery marker is incomplete", code="ASK_RECOVERY_INVALID")
    require_valid_contract("task", task)
    require_valid_contract("event", event)
    return value


def _remove_marker(marker: Path) -> None:
    try:
        marker.unlink(missing_ok=True)
    except OSError as error:
        raise StorageError(
            "ASK answer completed but its recovery marker remains",
            code="ASK_MARKER_REMOVE_FAILED",
        ) from error


def _complete_answer_marker(repository_root: Path, task_id: str) -> TransitionResult:
    marker = resolve_task_path(repository_root, task_id, ANSWER_MARKER)
    value = _validate_marker(read_task_json(repository_root, task_id, ANSWER_MARKER), task_id)
    event = value["event"]
    task = value["task"]
    assert isinstance(event, dict) and isinstance(task, dict)
    specification = value["specification"]
    decisions = value["decisions"]
    assert isinstance(specification, str) and isinstance(decisions, str)

    atomic_write_text(resolve_task_path(repository_root, task_id, "spec.md"), specification)
    atomic_write_text(resolve_task_path(repository_root, task_id, "decisions.md"), decisions)
    record = load_task_record(repository_root, task_id)
    recorded = next(
        (item for item in record.events if item.get("sequence") == event.get("sequence")), None
    )
    if recorded is not None:
        if recorded != event or record.task.get("current_state") != task.get("current_state"):
            raise StorageError(
                "ASK answer recovery conflicts with task history", code="ASK_RECOVERY_CONFLICT"
            )
        _remove_marker(marker)
        return TransitionResult(task=record.task, event=event)
    if len(record.events) + 1 != event.get("sequence"):
        raise StorageError(
            "ASK answer recovery conflicts with task history", code="ASK_RECOVERY_CONFLICT"
        )
    _persist_event_and_task(resolve_task_path(repository_root, task_id), task, event)
    _remove_marker(marker)
    return TransitionResult(task=task, event=event)


def answer_task(
    repository_root: Path,
    task_id: str,
    *,
    options_file: Path,
    selected_option_id: str,
    actor: str,
    reason: str,
) -> TransitionResult:
    """Record one ASK answer and atomically bind its decision and frozen specification."""
    marker = resolve_task_path(repository_root, task_id, ANSWER_MARKER)
    if marker.is_file():
        return _complete_answer_marker(repository_root, task_id)

    record = load_task_record(repository_root, task_id)
    classification = read_task_json(
        repository_root, task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(classification, dict) or classification.get("task_id") != task_id:
        raise ContractError("ASK classification is invalid", code="ASK_CLASSIFICATION_INVALID")
    policy = load_policy_bundle(repository_root)
    expected_input = _stable_input(record.task, parse_decision_units(record.task))
    if (
        classification.get("classification_input_sha256") != expected_input
        or classification.get("policy_sha256") != policy.sha256
        or classification.get("base_commit") != record.task.get("base_commit")
        or classification.get("subject_commit") != record.task.get("subject_commit")
    ):
        raise ContractError("ASK classification is stale", code="ASK_CLASSIFICATION_STALE")
    spec_path = resolve_task_path(repository_root, task_id, "spec.md")
    try:
        specification = spec_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise StorageError(
            "Could not read task specification", code="SPECIFICATION_READ_FAILED"
        ) from error
    answered_at = _utc_now()
    prepared = prepare_answer(
        task_state=str(record.task.get("current_state")),
        classification=classification,
        specification=specification,
        options_document=_load_options_file(options_file),
        selected_option_id=selected_option_id,
        actor=actor,
        reason=reason,
        answered_at=answered_at,
    )
    event = create_transition_event(
        record.task,
        target_state=prepared.target_state,
        event_type="ask_answered",
        actor=str(prepared.event_payload["actor"]),
        payload=prepared.event_payload,
        sequence=len(record.events) + 1,
        satisfied_preconditions={"answer_recorded", "spec_frozen"},
        occurred_at=answered_at,
    )
    task = {
        **record.task,
        "current_state": prepared.target_state,
        "frozen_spec_sha256": prepared.specification.sha256,
        "spec_frozen_at": event["occurred_at"],
        "updated_at": event["occurred_at"],
    }
    require_valid_contract("task", task)
    atomic_write_json(
        marker,
        {
            "schema_version": "1.0",
            "task_id": task_id,
            "task": task,
            "event": event,
            "specification": prepared.frozen_specification,
            "decisions": prepared.decisions_markdown,
        },
    )
    return _complete_answer_marker(repository_root, task_id)
