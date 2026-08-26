from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from aiflow.errors import ContractError
from aiflow.git_context import GitContext
from aiflow.observation import Observation, parse_observation
from aiflow.observation_decision import (
    DecisionRoute,
    VerificationLevel,
    decide_observation,
    observation_digest,
)
from aiflow.observation_service import _audit_payload, _current_facts, apply_observation
from aiflow.policy import PolicyBundle
from aiflow.task_service import TaskRecord, TransitionResult

ROOT = Path(".")
BASE = "a" * 40
SUBJECT = "b" * 40
POLICY = "c" * 64


def _observation(kind: str, *, source: str = "cli") -> Observation:
    return parse_observation(
        {
            "schema_version": "1.0",
            "task_id": "TASK-0018",
            "base_commit": BASE,
            "subject_commit": SUBJECT,
            "policy_sha256": POLICY,
            "source": source,
            "kind": kind,
            "summary": {"paths": ["src/new.py"]}
            if kind != "evidence_missing"
            else {"artifact": "evidence", "reason_code": "stale"},
        }
    )


def _record(
    *, state: str = "IMPLEMENTING", events: tuple[dict[str, object], ...] = ()
) -> TaskRecord:
    return TaskRecord(
        task={
            "task_id": "TASK-0018",
            "base_commit": BASE,
            "subject_commit": SUBJECT,
            "current_state": state,
        },
        events=events,
    )


def _facts(monkeypatch: pytest.MonkeyPatch, *, route: DecisionRoute) -> None:
    monkeypatch.setattr(
        "aiflow.observation_service._current_facts",
        lambda _root, _task_id, _observation: (_record().task, {}, route, VerificationLevel.V1),
    )


def test_ci_observation_is_rejected_before_any_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record",
        lambda *_args: calls.append("load"),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.record_task_event",
        lambda *_args, **_kwargs: calls.append("record"),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **_kwargs: calls.append("escalate"),
    )

    with pytest.raises(ContractError) as error:
        apply_observation(
            ROOT, "TASK-0018", _observation("scope_out_of_bounds", source="ci"), actor="tester"
        )

    assert error.value.code == "OBSERVATION_CI_PERSISTENCE_FORBIDDEN"
    assert calls == []


def _install_real_facts(
    monkeypatch: pytest.MonkeyPatch,
    *,
    task_changes: dict[str, object] | None = None,
    classification_changes: dict[str, object] | None = None,
    observation_changes: dict[str, object] | None = None,
    context_changes: dict[str, object] | None = None,
    ancestral: bool = True,
) -> tuple[Observation, list[str]]:
    task: dict[str, object] = {
        **_record().task,
        "repository_id": "repo-1",
        "branch": "main",
    }
    task.update(task_changes or {})
    classification: dict[str, object] = {
        "task_id": "TASK-0018",
        "base_commit": BASE,
        "subject_commit": SUBJECT,
        "policy_sha256": POLICY,
        "classification_input_sha256": "d" * 64,
        "effective_route": "AUTO",
        "effective_verification_level": "V1",
    }
    classification.update(classification_changes or {})
    context = {
        "repository_id": "repo-1",
        "repository_path": "D:/Repos/harness-model",
        "branch": "main",
        "head": SUBJECT,
        "worktree_dirty": False,
        "dirty_paths": (),
    }
    context.update(context_changes or {})
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record",
        lambda *_args: TaskRecord(task, ()),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.collect_git_context",
        lambda *_args: GitContext(**context),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.commits_are_ancestral", lambda *_args, **_kwargs: ancestral
    )
    monkeypatch.setattr(
        "aiflow.observation_service.load_policy_bundle",
        lambda *_args: PolicyBundle(documents={}, policy_version="1.0", sha256=POLICY),
    )
    monkeypatch.setattr("aiflow.observation_service._classification", lambda *_args: classification)
    monkeypatch.setattr("aiflow.observation_service.parse_decision_units", lambda *_args: ())
    monkeypatch.setattr(
        "aiflow.observation_service.current_classification_input_digest",
        lambda *_args: ("d" * 64, False),
    )
    writes: list[str] = []
    monkeypatch.setattr(
        "aiflow.observation_service.record_task_event",
        lambda *_args, **_kwargs: writes.append("record"),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **_kwargs: writes.append("escalate"),
    )
    return replace(_observation("scope_out_of_bounds"), **(observation_changes or {})), writes


@pytest.mark.parametrize(
    "task_changes,classification_changes,observation_changes,context_changes,ancestral,code",
    [
        ({"task_id": "TASK-9999"}, {}, {}, {}, True, "OBSERVATION_BINDING_STALE"),
        ({}, {}, {"task_id": "TASK-9999"}, {}, True, "OBSERVATION_BINDING_STALE"),
        ({}, {}, {"base_commit": "e" * 40}, {}, True, "OBSERVATION_BINDING_STALE"),
        ({}, {}, {"subject_commit": "e" * 40}, {}, True, "OBSERVATION_BINDING_STALE"),
        ({}, {}, {"policy_sha256": "e" * 64}, {}, True, "OBSERVATION_POLICY_STALE"),
        ({}, {"task_id": "TASK-9999"}, {}, {}, True, "OBSERVATION_CLASSIFICATION_STALE"),
        ({}, {"base_commit": "e" * 40}, {}, {}, True, "OBSERVATION_CLASSIFICATION_STALE"),
        ({}, {"subject_commit": "e" * 40}, {}, {}, True, "OBSERVATION_CLASSIFICATION_STALE"),
        ({}, {"policy_sha256": "e" * 64}, {}, {}, True, "OBSERVATION_CLASSIFICATION_STALE"),
        (
            {},
            {"classification_input_sha256": "e" * 64},
            {},
            {},
            True,
            "OBSERVATION_CLASSIFICATION_STALE",
        ),
        ({}, {}, {}, {"repository_id": "repo-2"}, True, "OBSERVATION_GIT_BINDING_STALE"),
        ({}, {}, {}, {"branch": "other"}, True, "OBSERVATION_GIT_BINDING_STALE"),
        ({}, {}, {}, {"head": "e" * 40}, True, "OBSERVATION_GIT_BINDING_STALE"),
        ({}, {}, {}, {}, False, "OBSERVATION_GIT_BINDING_STALE"),
        ({"current_state": "NEW"}, {}, {}, {}, True, "OBSERVATION_STATE_INVALID"),
        (
            {},
            {"effective_route": "INVALID"},
            {},
            {},
            True,
            "OBSERVATION_CLASSIFICATION_INVALID",
        ),
        (
            {},
            {"effective_verification_level": "INVALID"},
            {},
            {},
            True,
            "OBSERVATION_CLASSIFICATION_INVALID",
        ),
    ],
)
def test_current_facts_rejects_stale_or_invalid_inputs_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
    task_changes: dict[str, object],
    classification_changes: dict[str, object],
    observation_changes: dict[str, object],
    context_changes: dict[str, object],
    ancestral: bool,
    code: str,
) -> None:
    observation, writes = _install_real_facts(
        monkeypatch,
        task_changes=task_changes,
        classification_changes=classification_changes,
        observation_changes=observation_changes,
        context_changes=context_changes,
        ancestral=ancestral,
    )

    with pytest.raises(ContractError) as error:
        apply_observation(ROOT, "TASK-0018", observation, actor="tester")

    assert error.value.code == code
    assert writes == []


def test_current_facts_accepts_an_audited_subject_synchronization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observation, writes = _install_real_facts(
        monkeypatch,
        classification_changes={"subject_commit": "e" * 40},
    )
    monkeypatch.setattr(
        "aiflow.observation_service.current_classification_input_digest",
        lambda *_args: ("d" * 64, True),
    )

    _task, classification, route, level = _current_facts(ROOT, "TASK-0018", observation)

    assert classification["subject_commit"] == "e" * 40
    assert route is DecisionRoute.AUTO
    assert level is VerificationLevel.V1
    assert writes == []


def test_missing_task_fails_before_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    writes: list[str] = []
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record",
        lambda *_args: (_ for _ in ()).throw(ContractError("missing", code="TASK_NOT_FOUND")),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.record_task_event",
        lambda *_args, **_kwargs: writes.append("record"),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **_kwargs: writes.append("escalate"),
    )

    with pytest.raises(ContractError) as error:
        apply_observation(ROOT, "TASK-0018", _observation("scope_out_of_bounds"), actor="tester")

    assert error.value.code == "TASK_NOT_FOUND"
    assert writes == []


@pytest.mark.parametrize(
    ("kind", "route", "event_type"),
    [
        ("scope_out_of_bounds", DecisionRoute.BLOCK, "observation_recorded"),
        ("evidence_missing", DecisionRoute.REVIEW, "observation_refused"),
    ],
)
def test_record_and_refuse_only_append_a_non_state_audit_event(
    monkeypatch: pytest.MonkeyPatch, kind: str, route: DecisionRoute, event_type: str
) -> None:
    _facts(monkeypatch, route=route)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("aiflow.observation_service.load_task_record", lambda *_args: _record())

    def record_event(*_args: object, **kwargs: object) -> TransitionResult:
        calls.append(dict(kwargs))
        return TransitionResult(task=_record().task, event={"event_type": kwargs["event_type"]})

    monkeypatch.setattr("aiflow.observation_service.record_task_event", record_event)
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **_kwargs: pytest.fail("must not escalate"),
    )

    result = apply_observation(ROOT, "TASK-0018", _observation(kind), actor="tester")

    assert result.escalation_event is None
    assert result.audit_event == {"event_type": event_type}
    assert [call["event_type"] for call in calls] == [event_type]
    assert calls[0]["payload"]["decision"]["execution_allowed"] is False  # type: ignore[index]


def test_escalation_persists_once_then_delegates_and_retries_without_duplicate_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _facts(monkeypatch, route=DecisionRoute.AUTO)
    audit = {"event_type": "observation_recorded", "payload": {}}
    records = [_record(), _record(), _record(events=(audit,)), _record(events=(audit,))]
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record", lambda *_args: records.pop(0)
    )
    events: list[str] = []

    def record_event(*_args: object, **kwargs: object) -> TransitionResult:
        events.append(str(kwargs["event_type"]))
        payload = kwargs["payload"]
        assert isinstance(payload, dict)
        audit["payload"] = payload
        return TransitionResult(task=_record().task, event=audit)

    escalation_calls: list[dict[str, object]] = []
    monkeypatch.setattr("aiflow.observation_service.record_task_event", record_event)
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **kwargs: (
            escalation_calls.append(dict(kwargs))
            or TransitionResult(
                task=_record(state="ESCALATED").task, event={"event_type": "task_escalated"}
            )
        ),
    )

    first = apply_observation(
        ROOT, "TASK-0018", _observation("scope_out_of_bounds"), actor="tester"
    )
    second = apply_observation(
        ROOT, "TASK-0018", _observation("scope_out_of_bounds"), actor="tester"
    )

    assert first.escalation_event == {"event_type": "task_escalated"}
    assert second.escalation_event == {"event_type": "task_escalated"}
    assert events == ["observation_recorded"]
    assert len(escalation_calls) == 2
    assert escalation_calls[0]["target_route"] == "REVIEW"
    assert escalation_calls[0]["reason_code"] == "scope_expanded"


def test_escalation_failure_keeps_its_audit_record_for_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _facts(monkeypatch, route=DecisionRoute.AUTO)
    monkeypatch.setattr("aiflow.observation_service.load_task_record", lambda *_args: _record())
    events: list[str] = []
    monkeypatch.setattr(
        "aiflow.observation_service.record_task_event",
        lambda *_args, **kwargs: (
            events.append(str(kwargs["event_type"]))
            or TransitionResult(task=_record().task, event={"event_type": "observation_recorded"})
        ),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ContractError("failed", code="ESCALATION_FAILED")
        ),
    )

    with pytest.raises(ContractError) as error:
        apply_observation(ROOT, "TASK-0018", _observation("scope_out_of_bounds"), actor="tester")

    assert error.value.code == "ESCALATION_FAILED"
    assert events == ["observation_recorded"]


def test_blocked_record_appends_audit_without_changing_the_blocked_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _facts(monkeypatch, route=DecisionRoute.BLOCK)
    blocked = _record(state="BLOCKED")
    monkeypatch.setattr("aiflow.observation_service.load_task_record", lambda *_args: blocked)
    calls: list[str] = []
    monkeypatch.setattr(
        "aiflow.observation_service.record_task_event",
        lambda *_args, **kwargs: (
            calls.append(str(kwargs["event_type"]))
            or TransitionResult(task=blocked.task, event={"event_type": "observation_recorded"})
        ),
    )
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **_kwargs: pytest.fail("must not escalate"),
    )

    result = apply_observation(
        ROOT, "TASK-0018", _observation("scope_out_of_bounds"), actor="tester"
    )

    assert result.audit_event == {"event_type": "observation_recorded"}
    assert result.escalation_event is None
    assert calls == ["observation_recorded"]


@pytest.mark.parametrize(
    ("kind", "route", "event_type"),
    [
        ("scope_out_of_bounds", DecisionRoute.BLOCK, "observation_recorded"),
        ("evidence_missing", DecisionRoute.REVIEW, "observation_refused"),
    ],
)
def test_record_and_refuse_exact_replay_reuses_the_existing_audit(
    monkeypatch: pytest.MonkeyPatch, kind: str, route: DecisionRoute, event_type: str
) -> None:
    _facts(monkeypatch, route=route)
    audit: dict[str, object] = {"event_type": event_type, "payload": {}}
    records = [_record(), _record(events=(audit,))]
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record", lambda *_args: records.pop(0)
    )
    writes: list[str] = []

    def record_event(*_args: object, **kwargs: object) -> TransitionResult:
        writes.append(str(kwargs["event_type"]))
        audit["payload"] = kwargs["payload"]
        return TransitionResult(task=_record().task, event=audit)

    monkeypatch.setattr("aiflow.observation_service.record_task_event", record_event)

    first = apply_observation(ROOT, "TASK-0018", _observation(kind), actor="tester")
    second = apply_observation(ROOT, "TASK-0018", _observation(kind), actor="tester")

    assert first.audit_event == second.audit_event == audit
    assert writes == [event_type]


def test_escalated_exact_replay_does_not_append_or_escalate_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _facts(monkeypatch, route=DecisionRoute.AUTO)
    audit: dict[str, object] = {"event_type": "observation_recorded", "payload": {}}
    records = [
        _record(),
        _record(),
        _record(state="ESCALATED", events=(audit,)),
        _record(state="ESCALATED", events=(audit,)),
    ]
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record", lambda *_args: records.pop(0)
    )
    writes: list[str] = []

    def record_event(*_args: object, **kwargs: object) -> TransitionResult:
        writes.append(str(kwargs["event_type"]))
        audit["payload"] = kwargs["payload"]
        return TransitionResult(task=_record().task, event=audit)

    escalations: list[object] = []
    monkeypatch.setattr("aiflow.observation_service.record_task_event", record_event)
    monkeypatch.setattr(
        "aiflow.observation_service.escalate_task",
        lambda *_args, **_kwargs: (
            escalations.append(1)
            or TransitionResult(
                task=_record(state="ESCALATED").task, event={"event_type": "task_escalated"}
            )
        ),
    )

    apply_observation(ROOT, "TASK-0018", _observation("scope_out_of_bounds"), actor="tester")
    replay = apply_observation(
        ROOT, "TASK-0018", _observation("scope_out_of_bounds"), actor="tester"
    )

    assert replay.escalation_event is None
    assert writes == ["observation_recorded"]
    assert escalations == [1]


@pytest.mark.parametrize(
    "tampered_payload",
    [
        {"observation_sha256": "same", "decision_sha256": "0" * 64},
        {
            "observation_sha256": "same",
            "decision_sha256": "0" * 64,
            "observation": {"tampered": True},
        },
        {
            "observation_sha256": "same",
            "decision_sha256": "0" * 64,
            "decision": {"execution_allowed": True},
        },
    ],
)
def test_tampered_audit_is_rejected_before_any_new_write(
    monkeypatch: pytest.MonkeyPatch, tampered_payload: dict[str, object]
) -> None:
    _facts(monkeypatch, route=DecisionRoute.BLOCK)
    observation = _observation("scope_out_of_bounds")
    tampered_payload["observation_sha256"] = observation_digest(observation)
    conflicting = {
        "event_type": "observation_refused",
        "payload": tampered_payload,
    }
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record",
        lambda *_args: _record(events=(conflicting,)),
    )
    writes: list[object] = []
    monkeypatch.setattr(
        "aiflow.observation_service.record_task_event",
        lambda *_args, **_kwargs: writes.append(1),
    )

    with pytest.raises(ContractError) as error:
        apply_observation(ROOT, "TASK-0018", observation, actor="tester")

    assert error.value.code == "OBSERVATION_AUDIT_CONFLICT"
    assert writes == []


@pytest.mark.parametrize(
    "tamper",
    ["observation_digest", "decision_digest", "observation_payload", "event_type"],
)
def test_canonical_audit_identity_tampering_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    _facts(monkeypatch, route=DecisionRoute.BLOCK)
    observation = _observation("scope_out_of_bounds")
    decision = decide_observation(observation, DecisionRoute.BLOCK, VerificationLevel.V1)
    payload = _audit_payload(observation, decision)
    event_type = "observation_recorded"
    if tamper == "observation_digest":
        payload["observation_sha256"] = "0" * 64
    elif tamper == "decision_digest":
        payload["decision_sha256"] = "0" * 64
    elif tamper == "observation_payload":
        changed = deepcopy(payload["observation"])
        assert isinstance(changed, dict)
        changed["summary"] = {"paths": ["src/tampered.py"]}
        payload["observation"] = changed
    else:
        event_type = "review_recorded"
    conflicting = {"event_type": event_type, "payload": payload}
    monkeypatch.setattr(
        "aiflow.observation_service.load_task_record",
        lambda *_args: _record(events=(conflicting,)),
    )
    writes: list[object] = []
    monkeypatch.setattr(
        "aiflow.observation_service.record_task_event",
        lambda *_args, **_kwargs: writes.append(1),
    )

    with pytest.raises(ContractError) as error:
        apply_observation(ROOT, "TASK-0018", observation, actor="tester")

    assert error.value.code == "OBSERVATION_AUDIT_CONFLICT"
    assert writes == []
