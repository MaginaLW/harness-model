"""Table-driven state transition, replay, and recovery tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import pytest
import yaml

from aiflow.errors import StateTransitionError, StorageError
from aiflow.git_context import VerificationGitAssessment
from aiflow.scope import ScopeAssessment
from aiflow.state import (
    ALL_STATES,
    NON_STATE_EVENTS,
    TRANSITIONS,
    assert_task_matches_events,
    create_record_event,
    create_transition_event,
    replay_events,
)
from aiflow.storage import atomic_write_text, atomic_write_yaml
from aiflow.task_service import (
    evaluate_and_sync_verification_subject,
    load_task_record,
    transition_task_record,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSITION_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "state" / "transitions.json"
OCCURRED_AT = "2026-08-20T14:00:00Z"


def fixture() -> dict[str, Any]:
    value = json.loads(TRANSITION_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def minimal_task(state: str = "NEW") -> dict[str, object]:
    return {"task_id": "TASK-0001", "current_state": state}


def initial_event() -> dict[str, Any]:
    return create_record_event(
        minimal_task(),
        event_type="task_created",
        actor="aiflow",
        payload={},
        sequence=1,
        occurred_at=OCCURRED_AT,
    )


def test_transition_table_matches_independent_fixture() -> None:
    expected = {
        (item["from"], item["to"]): (item["event_type"], frozenset(item["preconditions"]))
        for item in fixture()["transitions"]
    }
    actual = {edge: (rule.event_type, rule.preconditions) for edge, rule in TRANSITIONS.items()}

    assert actual == expected
    assert NON_STATE_EVENTS == frozenset(fixture()["non_state_events"]) | {
        "subject_commit_synchronized",
        "review_recorded",
        "review_finding_resolved",
    }


@pytest.mark.parametrize("transition", fixture()["transitions"])
def test_every_allowed_edge_creates_a_valid_event(transition: dict[str, Any]) -> None:
    event = create_transition_event(
        minimal_task(transition["from"]),
        target_state=transition["to"],
        event_type=transition["event_type"],
        actor="tester",
        payload={"reason": "fixture"},
        sequence=2,
        satisfied_preconditions=set(transition["preconditions"]),
        occurred_at=OCCURRED_AT,
    )

    assert event["from_state"] == transition["from"]
    assert event["to_state"] == transition["to"]
    assert event["event_type"] == transition["event_type"]


@pytest.mark.parametrize("state", sorted(ALL_STATES))
def test_every_state_rejects_an_illegal_target(state: str) -> None:
    allowed_targets = {target for source, target in TRANSITIONS if source == state}
    illegal_target = next(
        candidate
        for candidate in sorted(ALL_STATES)
        if candidate != state and candidate not in allowed_targets
    )

    with pytest.raises(StateTransitionError) as caught:
        create_transition_event(
            minimal_task(state),
            target_state=illegal_target,
            event_type="invented_transition",
            actor="tester",
            payload={},
            sequence=2,
            satisfied_preconditions=set(),
            occurred_at=OCCURRED_AT,
        )

    assert caught.value.code == "STATE_TRANSITION_NOT_ALLOWED"


def test_transition_requires_all_declared_preconditions() -> None:
    with pytest.raises(StateTransitionError) as caught:
        create_transition_event(
            minimal_task("WAITING_FOR_ASK"),
            target_state="READY_TO_IMPLEMENT",
            event_type="ask_answered",
            actor="tester",
            payload={},
            sequence=2,
            satisfied_preconditions={"answer_recorded"},
            occurred_at=OCCURRED_AT,
        )

    assert caught.value.code == "STATE_PRECONDITION_MISSING"
    assert caught.value.details["missing"] == ["spec_frozen"]


def test_non_state_events_use_a_closed_separate_api() -> None:
    with pytest.raises(StateTransitionError):
        create_transition_event(
            minimal_task(),
            target_state="NEW",
            event_type="spec_frozen",
            actor="tester",
            payload={},
            sequence=2,
            satisfied_preconditions=set(),
            occurred_at=OCCURRED_AT,
        )

    event = create_record_event(
        minimal_task(),
        event_type="spec_frozen",
        actor="tester",
        payload={},
        sequence=2,
        occurred_at=OCCURRED_AT,
    )
    assert event["from_state"] == event["to_state"] == "NEW"

    with pytest.raises(StateTransitionError) as caught:
        create_record_event(
            minimal_task(),
            event_type="invented_self_loop",
            actor="tester",
            payload={},
            sequence=2,
            occurred_at=OCCURRED_AT,
        )
    assert caught.value.code == "STATE_EVENT_NOT_ALLOWED"


def classified_events() -> list[dict[str, Any]]:
    events = [initial_event()]
    events.append(
        create_transition_event(
            minimal_task(),
            target_state="CLASSIFIED",
            event_type="classification_recorded",
            actor="tester",
            payload={},
            sequence=2,
            satisfied_preconditions={"classification_available"},
            occurred_at=OCCURRED_AT,
        )
    )
    return events


def test_replay_returns_deterministic_terminal_state() -> None:
    events = classified_events()

    assert replay_events(events, task_id="TASK-0001") == "CLASSIFIED"
    assert_task_matches_events(minimal_task("CLASSIFIED"), events)


@pytest.mark.parametrize("sequences", [(1, 3), (1, 1)])
def test_replay_rejects_missing_or_duplicate_sequence(sequences: tuple[int, int]) -> None:
    events = classified_events()
    events[0]["sequence"], events[1]["sequence"] = sequences

    with pytest.raises(StateTransitionError) as caught:
        replay_events(events, task_id="TASK-0001")

    assert caught.value.code == "STATE_EVENT_SEQUENCE_INVALID"


def test_replay_rejects_tampered_from_state() -> None:
    events = classified_events()
    events[1]["from_state"] = "FAILED"

    with pytest.raises(StateTransitionError) as caught:
        replay_events(events, task_id="TASK-0001")

    assert caught.value.code == "STATE_EVENT_CHAIN_INVALID"


def test_task_state_must_match_replayed_terminal_state() -> None:
    with pytest.raises(StateTransitionError) as caught:
        assert_task_matches_events(minimal_task("NEW"), classified_events())

    assert caught.value.code == "STATE_MATERIALIZATION_MISMATCH"


def persistent_task(repository: Path) -> dict[str, Any]:
    task = json.loads(
        (PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "task.json").read_text(
            encoding="utf-8"
        )
    )
    task["current_state"] = "NEW"
    task["task_id"] = "TASK-0001"
    task["subject_commit"] = "1" * 40
    task["decision_units"][0]["task_id"] = "TASK-0001"
    directory = repository / ".ai" / "tasks" / "TASK-0001"
    directory.mkdir(parents=True)
    atomic_write_yaml(directory / "task.yaml", task)
    atomic_write_text(
        directory / "events.jsonl",
        json.dumps(initial_event(), sort_keys=True) + "\n",
    )
    return task


def test_transition_persists_event_and_materialized_state(tmp_path: Path) -> None:
    persistent_task(tmp_path)

    result = transition_task_record(
        tmp_path,
        "TASK-0001",
        target_state="CLASSIFIED",
        event_type="classification_recorded",
        actor="tester",
        payload={},
        satisfied_preconditions={"classification_available"},
    )

    assert result.task["current_state"] == "CLASSIFIED"
    assert result.event["sequence"] == 2
    loaded = load_task_record(tmp_path, "TASK-0001")
    assert loaded.task["current_state"] == "CLASSIFIED"
    assert len(loaded.events) == 2


def test_direct_materialized_state_tamper_is_not_auto_recovered(tmp_path: Path) -> None:
    task = persistent_task(tmp_path)
    task["current_state"] = "CLASSIFIED"
    atomic_write_yaml(tmp_path / ".ai" / "tasks" / "TASK-0001" / "task.yaml", task)

    with pytest.raises(StateTransitionError) as caught:
        load_task_record(tmp_path, "TASK-0001")

    assert caught.value.code == "STATE_MATERIALIZATION_MISMATCH"


def test_replace_interruption_is_recovered_from_appended_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import task_service

    persistent_task(tmp_path)
    original = task_service._replace_materialized_task

    def interrupt(_staged: Path, _target: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(task_service, "_replace_materialized_task", interrupt)
    with pytest.raises(StorageError) as caught:
        transition_task_record(
            tmp_path,
            "TASK-0001",
            target_state="CLASSIFIED",
            event_type="classification_recorded",
            actor="tester",
            payload={},
            satisfied_preconditions={"classification_available"},
        )
    assert caught.value.code == "STATE_MATERIALIZATION_FAILED"

    raw_task = yaml.safe_load(
        (tmp_path / ".ai" / "tasks" / "TASK-0001" / "task.yaml").read_text(encoding="utf-8")
    )
    assert raw_task["current_state"] == "NEW"
    assert (
        len(
            (tmp_path / ".ai" / "tasks" / "TASK-0001" / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        == 2
    )

    monkeypatch.setattr(task_service, "_replace_materialized_task", original)
    recovered = load_task_record(tmp_path, "TASK-0001")

    assert recovered.task["current_state"] == "CLASSIFIED"
    assert len(recovered.events) == 3
    assert recovered.events[-1]["event_type"] == "state_recovered"
    assert recovered.events[-1]["from_state"] == recovered.events[-1]["to_state"] == "CLASSIFIED"


def sync_assessment(mode: Literal["provisional", "final"] = "final") -> VerificationGitAssessment:
    scope = ScopeAssessment((), (), ())
    return VerificationGitAssessment(
        mode=mode,
        gate_eligible=mode == "final",
        reason_codes=() if mode == "final" else ("VERIFY_PROVISIONAL_NOT_GATE",),
        subject_commit="2" * 40,
        attestation_head="2" * 40,
        committed_scope=scope,
        attestation_scope=scope,
        worktree_scope=scope,
        subject_sync_event={
            "event_type": "subject_commit_synchronized",
            "old_subject_commit": "1" * 40,
            "new_subject_commit": "2" * 40,
            "base_commit": "1" * 40,
            "observed_head": "2" * 40,
            "repository_id": "123e4567-e89b-42d3-a456-426614174000",
            "branch": "main",
            "mode": mode,
        },
    )


def test_verification_subject_sync_is_atomic_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import task_service

    persistent_task(tmp_path)
    monkeypatch.setattr(
        task_service,
        "evaluate_verification_git_context",
        lambda *_args, **_kwargs: sync_assessment(),
    )

    first = evaluate_and_sync_verification_subject(
        tmp_path, "TASK-0001", mode="final", actor="verifier"
    )
    record = load_task_record(tmp_path, "TASK-0001")
    assert first.subject_commit == "2" * 40
    assert record.task["subject_commit"] == "2" * 40
    assert len(record.events) == 2
    assert record.events[-1]["event_type"] == "subject_commit_synchronized"
    assert record.events[-1]["payload"]["observed_head"] == "2" * 40

    evaluate_and_sync_verification_subject(tmp_path, "TASK-0001", mode="final", actor="verifier")
    assert len(load_task_record(tmp_path, "TASK-0001").events) == 2


def test_provisional_does_not_persist_and_sync_recovery_replaces_staged_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import task_service

    persistent_task(tmp_path)
    monkeypatch.setattr(
        task_service,
        "evaluate_verification_git_context",
        lambda *_args, **_kwargs: sync_assessment("provisional"),
    )
    evaluate_and_sync_verification_subject(
        tmp_path, "TASK-0001", mode="provisional", actor="verifier"
    )
    assert len(load_task_record(tmp_path, "TASK-0001").events) == 1

    monkeypatch.setattr(
        task_service,
        "evaluate_verification_git_context",
        lambda *_args, **_kwargs: sync_assessment(),
    )
    original = task_service._replace_materialized_task
    monkeypatch.setattr(
        task_service,
        "_replace_materialized_task",
        lambda *_args: (_ for _ in ()).throw(OSError("replace")),
    )
    with pytest.raises(StorageError) as caught:
        evaluate_and_sync_verification_subject(
            tmp_path, "TASK-0001", mode="final", actor="verifier"
        )
    assert caught.value.code == "STATE_MATERIALIZATION_FAILED"

    monkeypatch.setattr(task_service, "_replace_materialized_task", original)
    evaluate_and_sync_verification_subject(tmp_path, "TASK-0001", mode="final", actor="verifier")
    recovered = load_task_record(tmp_path, "TASK-0001")
    assert recovered.task["subject_commit"] == "2" * 40
    assert len(recovered.events) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [("goal", "tampered"), ("subject_commit", "3" * 40)],
)
def test_subject_sync_recovery_rejects_unbound_staged_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    from aiflow import task_service

    persistent_task(tmp_path)
    monkeypatch.setattr(
        task_service,
        "evaluate_verification_git_context",
        lambda *_args, **_kwargs: sync_assessment(),
    )
    original = task_service._replace_materialized_task
    monkeypatch.setattr(
        task_service,
        "_replace_materialized_task",
        lambda *_args: (_ for _ in ()).throw(OSError("replace")),
    )
    with pytest.raises(StorageError):
        evaluate_and_sync_verification_subject(
            tmp_path, "TASK-0001", mode="final", actor="verifier"
        )
    staged_path = tmp_path / ".ai" / "tasks" / "TASK-0001" / "task.yaml.next"
    staged = yaml.safe_load(staged_path.read_text(encoding="utf-8"))
    assert isinstance(staged, dict)
    staged[field] = value
    atomic_write_yaml(staged_path, staged)

    monkeypatch.setattr(task_service, "_replace_materialized_task", original)
    with pytest.raises(StateTransitionError) as caught:
        load_task_record(tmp_path, "TASK-0001")
    assert caught.value.code == "STATE_MATERIALIZATION_MISMATCH"
