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
from tools.hooks import pre_command, pre_commit


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


def _pre_command_repository_at_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, route: str
) -> Path:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route=route, valid_approval=route == "REVIEW")
    if route != "BLOCK":
        assert cli_main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    else:
        escalate_task(
            repository,
            "TASK-0001",
            target_route="BLOCK",
            reason_code="policy_changed",
            impact="test blocked pre-command disposition",
            next_step="retain blocked state",
            actor="setup",
        )
    return repository


def _pre_command_events(repository: Path) -> list[dict[str, object]]:
    return [
        event
        for event in load_task_record(repository, "TASK-0001").events
        if event["event_type"] in {"observation_recorded", "observation_refused"}
    ]


def _assert_high_risk_refusal(repository: Path, *, action: str, target: str) -> dict[str, object]:
    record = load_task_record(repository, "TASK-0001")
    events = _pre_command_events(repository)
    assert len(events) == 1
    event = events[0]
    payload = event["payload"]
    assert event["event_type"] == "observation_refused"
    assert event["actor"] == "hook_pre_command"
    assert payload["observation"] == {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "base_commit": record.task["base_commit"],
        "subject_commit": record.task["subject_commit"],
        "policy_sha256": load_policy_bundle(repository).sha256,
        "source": "hook_pre_command",
        "kind": "high_risk_command",
        "summary": {"action": action, "target_ref": target},
    }
    assert payload["decision"]["disposition"] == "refuse"
    assert payload["decision"]["execution_allowed"] is False
    return event


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


@pytest.mark.parametrize(
    ("action", "target"),
    [
        ("push", "origin/main"),
        ("merge", "main"),
        ("deploy", "production"),
        ("delete", "release-archive"),
        ("secret_export", "audit-bundle"),
        ("paid_external_call", "provider-request"),
    ],
)
def test_real_pre_command_refuses_each_policy_denied_action_with_exact_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str, target: str
) -> None:
    repository = _pre_command_repository_at_route(tmp_path, monkeypatch, route="REVIEW")

    assert pre_command.main(["--task", "TASK-0001", "--action", action, "--target", target]) == 2

    record = load_task_record(repository, "TASK-0001")
    _assert_high_risk_refusal(repository, action=action, target=target)
    assert record.task["current_state"] == "IMPLEMENTING"
    assert not [event for event in record.events if event["event_type"] == "task_escalated"]


@pytest.mark.parametrize("route", ("AUTO", "ASK", "REVIEW", "BLOCK"))
def test_real_pre_command_always_refuses_without_state_change_or_escalation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    repository = _pre_command_repository_at_route(tmp_path, monkeypatch, route=route)
    before = load_task_record(repository, "TASK-0001")

    assert (
        pre_command.main(["--task", "TASK-0001", "--action", "push", "--target", "origin/main"])
        == 2
    )

    after = load_task_record(repository, "TASK-0001")
    event = _assert_high_risk_refusal(repository, action="push", target="origin/main")
    assert after.task["current_state"] == before.task["current_state"]
    assert event["payload"]["decision"]["disposition"] == "refuse"
    assert not [item for item in after.events if item["event_type"] == "task_escalated"]


def test_real_pre_command_replay_is_idempotent_but_distinct_facts_get_distinct_audits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _pre_command_repository_at_route(tmp_path, monkeypatch, route="REVIEW")
    first = ["--task", "TASK-0001", "--action", "push", "--target", "origin/main"]

    assert pre_command.main(first) == 2
    assert pre_command.main(first) == 2
    assert (
        pre_command.main(["--task", "TASK-0001", "--action", "push", "--target", "origin/release"])
        == 2
    )
    assert (
        pre_command.main(["--task", "TASK-0001", "--action", "merge", "--target", "origin/release"])
        == 2
    )

    events = _pre_command_events(repository)
    assert len(events) == 3
    identities = {event["payload"]["observation_sha256"] for event in events}
    assert len(identities) == 3
    assert all(event["event_type"] == "observation_refused" for event in events)


@pytest.mark.parametrize("failure", ("service", "audit", "stale_head", "binding"))
def test_real_pre_command_failures_are_exit_one_without_a_successful_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    repository = _pre_command_repository_at_route(tmp_path, monkeypatch, route="REVIEW")
    if failure == "service":
        monkeypatch.setattr(
            pre_command,
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
    elif failure == "stale_head":
        commit_all(repository, "introduce stale high-risk binding")
    else:
        task = load_task_record(repository, "TASK-0001").task
        task["subject_commit"] = "f" * 40
        from aiflow.storage import atomic_write_yaml

        atomic_write_yaml(repository / ".ai" / "tasks" / "TASK-0001" / "task.yaml", task)

    assert (
        pre_command.main(["--task", "TASK-0001", "--action", "push", "--target", "origin/main"])
        == 1
    )
    assert not _pre_command_events(repository)


def test_real_pre_command_invalid_high_risk_target_fails_before_service_or_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _pre_command_repository_at_route(tmp_path, monkeypatch, route="REVIEW")
    monkeypatch.setattr(
        pre_command,
        "apply_observation",
        lambda *_args, **_kwargs: pytest.fail(
            "invalid target must not reach the persistence service"
        ),
    )

    assert (
        pre_command.main(["--task", "TASK-0001", "--action", "push", "--target", "$(whoami)"]) == 1
    )
    assert not _pre_command_events(repository)


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
