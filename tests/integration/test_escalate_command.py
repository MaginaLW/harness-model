"""Escalation core tests; command persistence is wired by the CLI layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.cli import main
from aiflow.errors import ContractError, StorageError
from aiflow.escalation import (
    ESCALATION_REASON_CODES,
    escalate_task,
    prepare_escalation,
    prepare_resolution,
    record_resolution,
)
from aiflow.storage import resolve_task_path
from aiflow.task_service import load_task_record
from tests.integration.test_begin_close_commands import create_repository, make_ready, start

HASH = "a" * 64


@pytest.mark.parametrize("reason_code", sorted(ESCALATION_REASON_CODES))
def test_every_structured_reason_code_can_raise_auto_to_review(reason_code: str) -> None:
    result = prepare_escalation(
        current_route="AUTO",
        target_route="REVIEW",
        reason_code=reason_code,
        impact="risk changed",
        next_step="reclassify",
    )
    assert result.target_state == "ESCALATED"
    assert result.payload["old_route"] == "AUTO"
    assert result.payload["new_route"] == "REVIEW"
    assert result.payload["trigger_signal"] == reason_code


@pytest.mark.parametrize(
    ("current_route", "target_route"),
    [("AUTO", "ASK"), ("AUTO", "REVIEW"), ("ASK", "REVIEW")],
)
def test_non_block_escalations_enter_escalated(current_route: str, target_route: str) -> None:
    result = prepare_escalation(
        current_route=current_route,  # type: ignore[arg-type]
        target_route=target_route,  # type: ignore[arg-type]
        reason_code="scope_expanded",
        impact="scope changed",
        next_step="reclassify",
    )
    assert result.target_state == "ESCALATED"


def test_block_target_enters_blocked_and_records_work_disposition() -> None:
    result = prepare_escalation(
        current_route="REVIEW",
        target_route="BLOCK",
        reason_code="credentials_required",
        impact="credentials are unavailable",
        next_step="obtain explicit approval",
        existing_work_disposition="preserve_for_review",
    )
    assert result.target_state == "BLOCKED"
    assert result.payload["existing_work_disposition"] == "preserve_for_review"


@pytest.mark.parametrize("reason_code", ["policy_changed", "spec_changed"])
def test_named_version_invalidations_allow_same_route_reassessment(reason_code: str) -> None:
    result = prepare_escalation(
        current_route="REVIEW",
        target_route="REVIEW",
        reason_code=reason_code,
        impact="bound version changed",
        next_step="reclassify and reapprove",
    )
    assert result.target_state == "ESCALATED"


@pytest.mark.parametrize(
    ("current_route", "target_route", "reason_code", "code"),
    [
        ("REVIEW", "ASK", "scope_expanded", "ESCALATION_ROUTE_DOWNGRADE"),
        ("REVIEW", "REVIEW", "scope_expanded", "ESCALATION_SAME_ROUTE_INVALID"),
        ("ASK", "AUTO", "scope_expanded", "ESCALATION_ROUTE_INVALID"),
    ],
)
def test_route_lowering_and_unqualified_same_route_are_rejected(
    current_route: str, target_route: str, reason_code: str, code: str
) -> None:
    with pytest.raises(ContractError) as caught:
        prepare_escalation(
            current_route=current_route,  # type: ignore[arg-type]
            target_route=target_route,  # type: ignore[arg-type]
            reason_code=reason_code,
            impact="impact",
            next_step="next",
        )
    assert caught.value.code == code


@pytest.mark.parametrize(
    ("impact", "next_step", "code"),
    [("", "next", "ESCALATION_IMPACT_REQUIRED"), ("impact", " ", "ESCALATION_NEXT_STEP_REQUIRED")],
)
def test_escalation_requires_impact_and_next_step(impact: str, next_step: str, code: str) -> None:
    with pytest.raises(ContractError) as caught:
        prepare_escalation(
            current_route="AUTO",
            target_route="ASK",
            reason_code="directional_discovery",
            impact=impact,
            next_step=next_step,
        )
    assert caught.value.code == code


def test_resolution_has_evidence_and_version_bindings_for_classification_recovery() -> None:
    payload = prepare_resolution(
        reason="restored required tooling",
        evidence_refs=["evidence-002", "evidence-001"],
        previous_classification_input_sha256=HASH,
        previous_policy_sha256=HASH,
    )
    assert payload["evidence_refs"] == ["evidence-001", "evidence-002"]
    assert payload["previous_policy_sha256"] == HASH


def test_downgrade_resolution_requires_complete_authorization() -> None:
    with pytest.raises(ContractError) as caught:
        prepare_resolution(
            reason="resolved",
            evidence_refs=["evidence-001"],
            previous_classification_input_sha256=HASH,
            previous_policy_sha256=HASH,
            manual_authorization=True,
        )
    assert caught.value.code == "RESOLUTION_AUTHORIZATION_REQUIRED"


@pytest.mark.parametrize(
    ("current_route", "target_route", "expected_state"),
    [("AUTO", "ASK", "ESCALATED"), ("ASK", "REVIEW", "ESCALATED"), ("REVIEW", "BLOCK", "BLOCKED")],
)
def test_escalate_cli_persists_route_raise_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    current_route: str,
    target_route: str,
    expected_state: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route=current_route)
    arguments = [
        "escalate",
        "TASK-0001",
        "--to",
        target_route,
        "--reason-code",
        "scope_expanded",
        "--impact",
        "more files are affected",
        "--next-step",
        "reclassify the task",
        "--actor",
        "agent",
    ]

    assert main(arguments) == 0
    first = load_task_record(repository, "TASK-0001")
    assert first.task["current_state"] == expected_state
    assert first.events[-1]["payload"]["old_route"] == current_route
    assert first.events[-1]["payload"]["new_route"] == target_route
    assert main(arguments) == 0
    assert len(load_task_record(repository, "TASK-0001").events) == len(first.events)


def test_escalate_cli_allows_named_same_route_and_rejects_other_same_route_or_downgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW")
    base = [
        "escalate",
        "TASK-0001",
        "--impact",
        "binding changed",
        "--next-step",
        "reclassify",
        "--actor",
        "agent",
    ]
    assert main([*base, "--to", "ASK", "--reason-code", "scope_expanded"]) == 1
    assert main([*base, "--to", "REVIEW", "--reason-code", "scope_expanded"]) == 1
    assert main([*base, "--to", "REVIEW", "--reason-code", "policy_changed"]) == 0
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "ESCALATED"


def test_block_requires_bound_resolution_evidence_before_reclassification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW")
    assert (
        main(
            [
                "escalate",
                "TASK-0001",
                "--to",
                "BLOCK",
                "--reason-code",
                "credentials_required",
                "--impact",
                "credentials are unavailable",
                "--next-step",
                "record credential approval evidence",
                "--actor",
                "agent",
            ]
        )
        == 0
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    evidence_path = resolve_task_path(repository, "TASK-0001", "resolution.md")
    evidence_path.write_text("credential requirement resolved\n", encoding="utf-8")
    assert (
        main(
            [
                "resolve",
                "TASK-0001",
                "--condition",
                "credentials_required",
                "--evidence-ref",
                "resolution.md",
                "--reason",
                "credential requirement removed",
                "--actor",
                "reviewer",
                "--authorize-downgrade",
            ]
        )
        == 0
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    events = load_task_record(repository, "TASK-0001").events
    assert any(event["event_type"] == "block_resolved" for event in events), [
        event["event_type"] for event in events
    ]
    assert any(event["event_type"] == "resolution_recorded" for event in events)


def test_escalate_and_resolve_help_are_available(capsys: pytest.CaptureFixture[str]) -> None:
    for command in ("escalate", "resolve"):
        with pytest.raises(SystemExit) as caught:
            main([command, "--help"])
        assert caught.value.code == 0
    output = capsys.readouterr().out
    assert "--next-step" in output and "--evidence-ref" in output


def test_resolution_classification_recovers_from_first_transition_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW")
    escalate_task(
        repository,
        "TASK-0001",
        target_route="BLOCK",
        reason_code="credentials_required",
        impact="credential required",
        next_step="record evidence",
        actor="agent",
    )
    resolve_task_path(repository, "TASK-0001", "resolution.md").write_text(
        "resolved\n", encoding="utf-8"
    )
    record_resolution(
        repository,
        "TASK-0001",
        condition="credentials_required",
        evidence_refs=["resolution.md"],
        actor="reviewer",
        reason="resolved",
        authorize_downgrade=True,
    )
    from aiflow import classification_service

    original = classification_service.transition_task_record

    def fail_transition(*_args: object, **_kwargs: object) -> object:
        raise StorageError("simulated", code="STATE_EVENT_APPEND_FAILED")

    monkeypatch.setattr(classification_service, "transition_task_record", fail_transition)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    marker = resolve_task_path(repository, "TASK-0001", "classification_pending.json")
    assert marker.is_file()
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "BLOCKED"

    monkeypatch.setattr(classification_service, "transition_task_record", original)
    evidence_path = resolve_task_path(repository, "TASK-0001", "resolution.md")
    evidence_path.write_text("tampered\n", encoding="utf-8")
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    assert marker.is_file()
    evidence_path.write_text("resolved\n", encoding="utf-8")
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert not marker.exists()
    assert any(
        event["event_type"] == "block_resolved"
        for event in load_task_record(repository, "TASK-0001").events
    )
