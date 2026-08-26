from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from aiflow.cli import main as cli_main
from aiflow.errors import ContractError
from aiflow.observation import Observation, parse_observation
from aiflow.observation_adapter import (
    ObservationAdapterResult,
    ObservationMode,
    load_observation_file,
    parse_observation_mode,
    run_observation,
    serialize_observation_result,
)
from aiflow.observation_decision import DecisionRoute, VerificationLevel, decide_observation
from aiflow.observation_service import ObservationApplication

ROOT = Path(".")
TASK_ID = "TASK-0022"
BASE = "a" * 40
SUBJECT = "b" * 40
POLICY = "c" * 64


def _observation(*, source: str = "cli", path: str = "src/outside.py") -> Observation:
    return parse_observation(
        {
            "schema_version": "1.0",
            "task_id": TASK_ID,
            "base_commit": BASE,
            "subject_commit": SUBJECT,
            "policy_sha256": POLICY,
            "source": source,
            "kind": "scope_out_of_bounds",
            "summary": {"paths": [path]},
        }
    )


def _decision(observation: Observation):
    return decide_observation(observation, DecisionRoute.REVIEW, VerificationLevel.V1)


def _application(observation: Observation) -> ObservationApplication:
    return ObservationApplication(
        decision=_decision(observation),
        audit_event={"event_type": "observation_refused", "sequence": 7, "payload": {}},
        escalation_event=None,
    )


def test_load_observation_file_accepts_one_utf8_object(tmp_path: Path) -> None:
    path = tmp_path / "observation.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "task_id": TASK_ID,
                "base_commit": BASE,
                "subject_commit": SUBJECT,
                "policy_sha256": POLICY,
                "source": "cli",
                "kind": "scope_out_of_bounds",
                "summary": {"paths": ["src/outside.py"]},
            }
        ),
        encoding="utf-8",
    )

    assert load_observation_file(path) == _observation()


@pytest.mark.parametrize(
    "content",
    [
        "not-json SECRET_VALUE",
        "[]",
        '{"schema_version":"1.0","schema_version":"1.0","secret":"SECRET_VALUE"}',
        json.dumps(
            {
                "schema_version": "1.0",
                "task_id": TASK_ID,
                "base_commit": BASE,
                "subject_commit": SUBJECT,
                "policy_sha256": POLICY,
                "source": "cli",
                "kind": "scope_out_of_bounds",
                "summary": {"paths": ["../SECRET_VALUE"]},
            }
        ),
        json.dumps(
            {
                "schema_version": "1.0",
                "task_id": TASK_ID,
                "base_commit": BASE,
                "subject_commit": SUBJECT,
                "policy_sha256": POLICY,
                "source": "cli",
                "kind": "scope_out_of_bounds",
                "summary": {"paths": ["src/outside.py"]},
                "unknown": "SECRET_VALUE",
            }
        ),
    ],
)
def test_load_observation_file_rejects_malformed_closed_or_escaping_input_without_echo(
    tmp_path: Path,
    content: str,
) -> None:
    path = tmp_path / "observation.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ContractError) as caught:
        load_observation_file(path)

    assert "SECRET_VALUE" not in str(caught.value)


def test_load_observation_file_rejects_unreadable_input_without_echo(tmp_path: Path) -> None:
    path = tmp_path / "SECRET_VALUE.json"

    with pytest.raises(ContractError) as caught:
        load_observation_file(path)

    assert caught.value.code == "OBSERVATION_INPUT_INVALID"
    assert "SECRET_VALUE" not in str(caught.value)


@pytest.mark.parametrize(
    ("mode", "source", "actor", "ledger_effect", "service"),
    [
        (ObservationMode.APPLY, "cli", "reviewer", "task_local", "apply"),
        (ObservationMode.DRY_RUN, "cli", None, "none", "evaluate"),
        (ObservationMode.CI, "ci", None, "none", "evaluate"),
    ],
)
def test_closed_modes_delegate_to_exactly_one_expected_service(
    monkeypatch: pytest.MonkeyPatch,
    mode: ObservationMode,
    source: str,
    actor: str | None,
    ledger_effect: str,
    service: str,
) -> None:
    observation = _observation(source=source)
    calls: list[tuple[str, object]] = []

    def apply(*_args: object, **kwargs: object) -> ObservationApplication:
        calls.append(("apply", kwargs["actor"]))
        return _application(observation)

    def evaluate(*_args: object, **_kwargs: object):
        calls.append(("evaluate", None))
        return _decision(observation)

    monkeypatch.setattr("aiflow.observation_adapter.apply_observation", apply)
    monkeypatch.setattr("aiflow.observation_adapter.evaluate_observation", evaluate)

    result = run_observation(ROOT, TASK_ID, observation, mode=mode, actor=actor)
    serialized = serialize_observation_result(result)

    assert calls == [(service, actor if service == "apply" else None)]
    assert result.ledger_effect == ledger_effect
    assert serialized["mode"] == mode.value
    assert serialized["ledger_effect"] == ledger_effect
    assert serialized["decision"]["execution_allowed"] is False
    assert "observation" not in serialized
    assert "summary" not in json.dumps(serialized)
    if mode is ObservationMode.APPLY:
        assert serialized["audit_event"] == {
            "event_type": "observation_refused",
            "sequence": 7,
        }
    else:
        assert serialized["audit_event"] is None
    assert serialized["escalation_event"] is None


@pytest.mark.parametrize(
    ("mode", "source", "actor", "task_id", "code"),
    [
        (ObservationMode.APPLY, "ci", "reviewer", TASK_ID, "OBSERVATION_SOURCE_MODE_MISMATCH"),
        (ObservationMode.APPLY, "cli", None, TASK_ID, "OBSERVATION_ACTOR_REQUIRED"),
        (ObservationMode.APPLY, "cli", "   ", TASK_ID, "OBSERVATION_ACTOR_REQUIRED"),
        (ObservationMode.DRY_RUN, "ci", None, TASK_ID, "OBSERVATION_SOURCE_MODE_MISMATCH"),
        (ObservationMode.DRY_RUN, "cli", "reviewer", TASK_ID, "OBSERVATION_ACTOR_FORBIDDEN"),
        (ObservationMode.CI, "cli", None, TASK_ID, "OBSERVATION_SOURCE_MODE_MISMATCH"),
        (ObservationMode.CI, "ci", "reviewer", TASK_ID, "OBSERVATION_ACTOR_FORBIDDEN"),
        (ObservationMode.CI, "ci", None, "TASK-9999", "OBSERVATION_TASK_MISMATCH"),
    ],
)
def test_invalid_mode_source_actor_or_task_combinations_fail_before_services(
    monkeypatch: pytest.MonkeyPatch,
    mode: ObservationMode,
    source: str,
    actor: str | None,
    task_id: str,
    code: str,
) -> None:
    monkeypatch.setattr(
        "aiflow.observation_adapter.apply_observation",
        lambda *_args, **_kwargs: pytest.fail("invalid input must not apply"),
    )
    monkeypatch.setattr(
        "aiflow.observation_adapter.evaluate_observation",
        lambda *_args, **_kwargs: pytest.fail("invalid input must not evaluate"),
    )

    with pytest.raises(ContractError) as caught:
        run_observation(
            ROOT,
            task_id,
            _observation(source=source),
            mode=mode,
            actor=actor,
        )

    assert caught.value.code == code


def test_invalid_mode_parser_is_non_reflective() -> None:
    with pytest.raises(ContractError) as caught:
        parse_observation_mode("SECRET_VALUE")
    assert caught.value.code == "OBSERVATION_MODE_INVALID"
    assert "SECRET_VALUE" not in str(caught.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"ledger_effect": "none"},
        {"audit_event": {"event_type": "observation_refused", "sequence": True}},
    ],
)
def test_serializer_rejects_inconsistent_apply_result(changes: dict[str, object]) -> None:
    observation = _observation()
    result = ObservationAdapterResult(
        task_id=TASK_ID,
        mode=ObservationMode.APPLY,
        ledger_effect="task_local",
        decision=_decision(observation),
        audit_event={"event_type": "observation_refused", "sequence": 7},
    )

    with pytest.raises(ContractError) as caught:
        serialize_observation_result(replace(result, **changes))

    assert caught.value.code == "OBSERVATION_RESULT_INVALID"


@pytest.mark.parametrize(
    "mode", [ObservationMode.APPLY, ObservationMode.DRY_RUN, ObservationMode.CI]
)
def test_cli_emits_one_canonical_json_result_and_returns_denial_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: ObservationMode,
) -> None:
    source = "ci" if mode is ObservationMode.CI else "cli"
    observation = _observation(source=source)
    expected = ObservationAdapterResult(
        task_id=TASK_ID,
        mode=mode,
        ledger_effect="task_local" if mode is ObservationMode.APPLY else "none",
        decision=_decision(observation),
        audit_event=(
            {"event_type": "observation_refused", "sequence": 7}
            if mode is ObservationMode.APPLY
            else None
        ),
    )
    monkeypatch.setattr("aiflow.cli.run_observation_file", lambda *_args, **_kwargs: expected)
    input_path = tmp_path / "observation.json"
    argv = ["observe", TASK_ID, "--input", str(input_path), "--mode", mode.value]
    if mode is ObservationMode.APPLY:
        argv.extend(["--actor", "reviewer"])

    assert cli_main(argv) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == serialize_observation_result(expected)
    assert (
        captured.out
        == json.dumps(
            serialize_observation_result(expected),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["observe"],
        ["observe", TASK_ID],
        ["observe", TASK_ID, "--input", "x.json"],
        ["observe", TASK_ID, "--input", "x.json", "--mode", "SECRET_VALUE"],
    ],
)
def test_cli_observe_invalid_input_returns_one_without_reflection(
    capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    assert cli_main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "SECRET_VALUE" not in captured.err


def test_cli_observe_help_declares_the_closed_protocol(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        cli_main(["observe", "--help"])

    assert caught.value.code == 0
    output = capsys.readouterr().out
    normalized = " ".join(output.split())
    assert (
        "usage: aiflow observe TASK-ID --input FILE --mode {apply,dry-run,ci} "
        "[--actor ACTOR]" in normalized
    )
    assert "TASK-ID required explicit task ID" in normalized
    assert "--input FILE required local UTF-8 observation JSON file" in normalized
    assert "--mode {apply,dry-run,ci} required; apply writes task audit" in normalized
    assert "--actor ACTOR required for apply; forbidden for dry-run and ci" in normalized
