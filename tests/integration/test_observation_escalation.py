from __future__ import annotations

from pathlib import Path

import pytest
from test_begin_close_commands import commit_all, create_repository, make_ready, start

from aiflow.cli import main as cli_main
from aiflow.errors import ContractError
from aiflow.escalation import escalate_task
from aiflow.observation import parse_observation
from aiflow.observation_decision import DecisionRoute, VerificationLevel
from aiflow.observation_service import apply_observation
from aiflow.policy import load_policy_bundle
from aiflow.task_service import TaskRecord, TransitionResult, load_task_record
from tools.hooks import pre_commit


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


def _hook_repository_at_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, route: str
) -> Path:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route=route, valid_approval=route == "REVIEW")
    assert cli_main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    return repository


def _assert_hook_observation(
    repository: Path,
    *,
    event_type: str,
    paths: list[str],
) -> dict[str, object]:
    record = load_task_record(repository, "TASK-0001")
    matching = [event for event in record.events if event["event_type"] == event_type]
    assert len(matching) == 1
    event = matching[0]
    payload = event["payload"]
    assert event["actor"] == "hook_pre_commit"
    assert payload["observation"]["task_id"] == "TASK-0001"
    assert payload["observation"]["base_commit"] == record.task["base_commit"]
    assert payload["observation"]["subject_commit"] == record.task["subject_commit"]
    assert payload["observation"]["policy_sha256"] == load_policy_bundle(repository).sha256
    assert payload["observation"]["source"] == "hook_pre_commit"
    assert payload["observation"]["kind"] == "scope_out_of_bounds"
    assert payload["observation"]["summary"] == {"paths": paths}
    return event


def _add_out_of_scope_paths(repository: Path) -> list[str]:
    paths = ["outside/a.py", "outside/z.py"]
    for path in paths:
        target = repository / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("outside\n", encoding="utf-8")
    return paths


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


def test_real_pre_commit_review_refuses_once_and_keeps_implementing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _hook_repository_at_route(tmp_path, monkeypatch, route="REVIEW")
    paths = _add_out_of_scope_paths(repository)

    first = pre_commit.check_pre_commit(repository, "TASK-0001")
    second = pre_commit.check_pre_commit(repository, "TASK-0001")

    record = load_task_record(repository, "TASK-0001")
    event = _assert_hook_observation(repository, event_type="observation_refused", paths=paths)
    assert first == second == (False, ("SCOPE_EXPANDED",))
    assert record.task["current_state"] == "IMPLEMENTING"
    assert event["payload"]["decision"]["disposition"] == "refuse"


@pytest.mark.parametrize("route", ("AUTO", "ASK"))
def test_real_pre_commit_auto_and_ask_escalate_only_through_existing_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    repository = _hook_repository_at_route(tmp_path, monkeypatch, route=route)
    paths = _add_out_of_scope_paths(repository)

    passed, reasons = pre_commit.check_pre_commit(repository, "TASK-0001")

    record = load_task_record(repository, "TASK-0001")
    event = _assert_hook_observation(repository, event_type="observation_recorded", paths=paths)
    assert passed is False
    assert reasons == ("SCOPE_EXPANDED",)
    assert record.task["current_state"] == "ESCALATED"
    assert event["payload"]["decision"]["disposition"] == "escalate"
    assert event["payload"]["decision"]["target_route"] == "REVIEW"
    assert [item["event_type"] for item in record.events].count("task_escalated") == 1


def test_real_pre_commit_block_records_but_still_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository_at_route(tmp_path, monkeypatch, route="BLOCK")
    escalate_task(
        repository,
        "TASK-0001",
        target_route="BLOCK",
        reason_code="policy_changed",
        impact="test blocked hook disposition",
        next_step="retain blocked state",
        actor="setup",
    )
    paths = _add_out_of_scope_paths(repository)

    passed, reasons = pre_commit.check_pre_commit(repository, "TASK-0001")

    record = load_task_record(repository, "TASK-0001")
    event = _assert_hook_observation(repository, event_type="observation_recorded", paths=paths)
    assert passed is False
    assert reasons == ("SCOPE_EXPANDED", "STATE_NOT_ALLOWED")
    assert record.task["current_state"] == "BLOCKED"
    assert event["payload"]["decision"]["disposition"] == "record"


@pytest.mark.parametrize("failure", ("service", "audit", "binding"))
def test_real_pre_commit_observation_failures_never_allow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    repository = _hook_repository_at_route(tmp_path, monkeypatch, route="REVIEW")
    paths = _add_out_of_scope_paths(repository)
    if failure == "service":
        monkeypatch.setattr(
            pre_commit,
            "apply_observation",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ContractError("service unavailable", code="OBSERVATION_SERVICE_FAILED")
            ),
        )
    elif failure == "audit":
        from aiflow import observation_service

        monkeypatch.setattr(
            observation_service,
            "record_task_event",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ContractError("audit unavailable", code="OBSERVATION_AUDIT_FAILED")
            ),
        )
    else:
        commit_all(repository, "introduce stale hook binding")

    assert pre_commit.main(["--task", "TASK-0001"]) == 1
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "IMPLEMENTING"
    assert not [
        event
        for event in record.events
        if event["event_type"] in {"observation_recorded", "observation_refused"}
    ]
    assert all((repository / path).is_file() for path in paths)


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
