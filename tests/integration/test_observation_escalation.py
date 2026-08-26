from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.errors import ContractError
from aiflow.escalation import escalate_task
from aiflow.observation import parse_observation
from aiflow.observation_decision import DecisionRoute, VerificationLevel
from aiflow.observation_service import apply_observation
from aiflow.policy import load_policy_bundle
from aiflow.task_service import TaskRecord, TransitionResult, load_task_record
from tests.integration.test_begin_close_commands import create_repository, make_ready, start


def _bound_observation(repository: Path, kind: str):
    task = load_task_record(repository, "TASK-0001").task
    summary: dict[str, object] = (
        {"artifact": "evidence", "reason_code": "stale"}
        if kind == "evidence_missing"
        else {"paths": ["src/outside_scope.py"]}
    )
    return parse_observation(
        {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "base_commit": task["base_commit"],
            "subject_commit": task["subject_commit"],
            "policy_sha256": load_policy_bundle(repository).sha256,
            "source": "cli",
            "kind": kind,
            "summary": summary,
        }
    )


def _repository_at_route(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, route: str) -> Path:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route=route)
    return repository


@pytest.mark.parametrize(
    ("route", "kind", "event_type"),
    [
        ("BLOCK", "scope_out_of_bounds", "observation_recorded"),
        ("REVIEW", "evidence_missing", "observation_refused"),
    ],
)
def test_real_ledger_record_and_refuse_are_idempotent_non_state_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    kind: str,
    event_type: str,
) -> None:
    repository = _repository_at_route(tmp_path, monkeypatch, route=route)
    if route == "BLOCK":
        escalate_task(
            repository,
            "TASK-0001",
            target_route="BLOCK",
            reason_code="policy_changed",
            impact="test version invalidation",
            next_step="retain the blocked state",
            actor="setup",
        )
    before = load_task_record(repository, "TASK-0001")
    observation = _bound_observation(repository, kind)

    first = apply_observation(repository, "TASK-0001", observation, actor="observer")
    second = apply_observation(repository, "TASK-0001", observation, actor="observer")

    after = load_task_record(repository, "TASK-0001")
    matching = [event for event in after.events if event["event_type"] == event_type]
    assert after.task["current_state"] == before.task["current_state"]
    assert len(matching) == 1
    assert first.audit_event == second.audit_event == matching[0]
    assert first.escalation_event is second.escalation_event is None


def test_real_escalation_appends_one_audit_then_uses_existing_escalation_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_route(tmp_path, monkeypatch, route="AUTO")
    observation = _bound_observation(repository, "scope_out_of_bounds")

    first = apply_observation(repository, "TASK-0001", observation, actor="observer")
    replay = apply_observation(repository, "TASK-0001", observation, actor="observer")

    record = load_task_record(repository, "TASK-0001")
    event_types = [event["event_type"] for event in record.events]
    assert record.task["current_state"] == "ESCALATED"
    assert event_types.count("observation_recorded") == 1
    assert event_types.count("task_escalated") == 1
    assert first.escalation_event is not None
    assert first.escalation_event["payload"]["new_route"] == "REVIEW"
    assert replay.audit_event == first.audit_event
    assert replay.escalation_event is None


def test_real_escalation_recovers_after_delegation_failure_without_duplicate_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_route(tmp_path, monkeypatch, route="AUTO")
    observation = _bound_observation(repository, "scope_out_of_bounds")
    from aiflow import observation_service

    actual_escalate = observation_service.escalate_task
    monkeypatch.setattr(
        observation_service,
        "escalate_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ContractError("interrupted", code="ESCALATION_INTERRUPTED")
        ),
    )
    with pytest.raises(ContractError) as error:
        apply_observation(repository, "TASK-0001", observation, actor="observer")
    assert error.value.code == "ESCALATION_INTERRUPTED"
    interrupted = load_task_record(repository, "TASK-0001")
    assert interrupted.task["current_state"] == "READY_TO_IMPLEMENT"
    assert [event["event_type"] for event in interrupted.events].count("observation_recorded") == 1

    monkeypatch.setattr(observation_service, "escalate_task", actual_escalate)
    recovered = apply_observation(repository, "TASK-0001", observation, actor="observer")

    final = load_task_record(repository, "TASK-0001")
    assert final.task["current_state"] == "ESCALATED"
    assert [event["event_type"] for event in final.events].count("observation_recorded") == 1
    assert [event["event_type"] for event in final.events].count("task_escalated") == 1
    assert recovered.escalation_event is not None


def test_observation_escalation_never_performs_the_observed_action(monkeypatch) -> None:
    base = "a" * 40
    subject = "b" * 40
    observation = parse_observation(
        {
            "schema_version": "1.0",
            "task_id": "TASK-0018",
            "base_commit": base,
            "subject_commit": subject,
            "policy_sha256": "c" * 64,
            "source": "cli",
            "kind": "scope_out_of_bounds",
            "summary": {"paths": ["src/outside_scope.py"]},
        }
    )
    task = {
        "task_id": "TASK-0018",
        "base_commit": base,
        "subject_commit": subject,
        "current_state": "IMPLEMENTING",
    }
    monkeypatch.setattr(
        "aiflow.observation_service._current_facts",
        lambda *_args: (task, {}, DecisionRoute.ASK, VerificationLevel.V1),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record", lambda *_args: TaskRecord(task, ())
    )
    monkeypatch.setattr(
        "aiflow.observation_service.record_task_event",
        lambda *_args, **_kwargs: TransitionResult(task, {"event_type": "observation_recorded"}),
    )
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **kwargs: (
            calls.append(dict(kwargs)) or TransitionResult(task, {"event_type": "task_escalated"})
        ),
    )

    result = apply_observation(Path("."), "TASK-0018", observation, actor="verifier")

    assert result.decision.execution_allowed is False
    assert calls[0]["target_route"] == "REVIEW"
    assert "src/outside_scope.py" not in str(calls[0])
