"""CLI error boundaries keep machine output useful without exposing internal details."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiflow import cli
from aiflow.errors import AiflowError, StorageError
from aiflow.gate import GateDecision

JSON_COMMANDS = [("status", "TASK-0001"), ("gate", "TASK-0001"), ("review", "show", "TASK-0001")]


@pytest.mark.parametrize("command", JSON_COMMANDS)
@pytest.mark.parametrize("format_arguments", [("--format", "json"), ("--format=json",)])
def test_json_domain_failure_emits_only_code_and_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: tuple[str, ...],
    format_arguments: tuple[str, ...],
) -> None:
    def fail(*_args: object) -> int:
        raise StorageError(
            "Could not read task document",
            code="STORAGE_READ_FAILED",
            details={"private": "private-detail-marker", "unserializable": object()},
        ) from RuntimeError("private-cause-marker")

    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)
    monkeypatch.setattr(cli, "_dispatch", fail)

    assert cli.main([*command, *format_arguments]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "code": "STORAGE_READ_FAILED",
        "message": "Could not read task document",
    }
    assert captured.err.endswith("\n")
    assert "private-" not in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("command", JSON_COMMANDS)
def test_json_repository_failure_uses_parsed_format(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: tuple[str, ...],
) -> None:
    def fail(_cwd: Path) -> Path:
        raise AiflowError(
            "Could not resolve repository root",
            code="GIT_REPOSITORY_ROOT_INVALID",
            details={"path": "private-repository-marker"},
        )

    monkeypatch.setattr(cli, "resolve_repository_root", fail)

    assert cli.main([*command, "--format", "json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "code": "GIT_REPOSITORY_ROOT_INVALID",
        "message": "Could not resolve repository root",
    }


@pytest.mark.parametrize("command", JSON_COMMANDS)
@pytest.mark.parametrize("format_arguments", [(), ("--format", "text")])
def test_text_domain_failure_retains_existing_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: tuple[str, ...],
    format_arguments: tuple[str, ...],
) -> None:
    def fail(*_args: object) -> int:
        raise AiflowError("Readable domain failure", details={"secret": "private-detail-marker"})

    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)
    monkeypatch.setattr(cli, "_dispatch", fail)

    assert cli.main([*command, *format_arguments]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Readable domain failure\n"


@pytest.mark.parametrize(
    ("command", "filename"),
    [
        (("status", "TASK-0001"), "task.yaml"),
        (("gate", "TASK-0001"), "task.yaml"),
        (("review", "show", "TASK-0001"), "reviews/REV-0001-r0001.json"),
    ],
)
@pytest.mark.parametrize("format_name", ["text", "json"])
def test_non_utf8_task_input_reports_safe_failure_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: tuple[str, ...],
    filename: str,
    format_name: str,
) -> None:
    path = tmp_path / ".ai" / "tasks" / "TASK-0001" / filename
    path.parent.mkdir(parents=True)
    content = b"private-document-marker\xff"
    path.write_bytes(content)
    before = {
        item.relative_to(tmp_path): item.read_bytes()
        for item in tmp_path.rglob("*")
        if item.is_file()
    }
    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)

    assert cli.main([*command, "--format", format_name]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    if format_name == "json":
        assert json.loads(captured.err) == {
            "code": "STORAGE_READ_FAILED",
            "message": "Could not read task document",
        }
    else:
        assert captured.err == "Could not read task document\n"
    assert "private-document-marker" not in captured.err
    assert str(tmp_path) not in captured.err
    assert "Traceback" not in captured.err
    assert {
        item.relative_to(tmp_path): item.read_bytes()
        for item in tmp_path.rglob("*")
        if item.is_file()
    } == before


@pytest.mark.parametrize(
    "arguments",
    [
        ["status", "--format", "json"],
        ["review", "show", "--format", "json"],
        ["gate", "TASK-0001", "--format", "invalid"],
        ["start", "--format", "json"],
    ],
)
def test_invalid_arguments_keep_argparse_text_and_exit_two(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> None:
    def unexpected_resolution(_cwd: Path) -> Path:
        pytest.fail("invalid arguments must not reach repository resolution")

    monkeypatch.setattr(cli, "resolve_repository_root", unexpected_resolution)

    with pytest.raises(SystemExit) as caught:
        cli.main(arguments)
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


def test_status_json_success_retains_payload_and_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    serialized = '{"task_id": "TASK-0001", "current_state": "CREATED"}'
    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)
    monkeypatch.setattr(
        cli, "summarize_task", lambda *_args: SimpleNamespace(to_json=lambda: serialized)
    )

    assert cli.main(["status", "TASK-0001", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert captured.out == serialized + "\n"
    assert captured.err == ""


@pytest.mark.parametrize("passed", [False, True])
def test_gate_json_decision_keeps_existing_exit_and_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    passed: bool,
) -> None:
    decision = GateDecision("TASK-0001", passed, "REVIEW", "V1", (), ())
    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)
    monkeypatch.setattr(cli, "evaluate_gate", lambda *_args, **_kwargs: decision)

    assert cli.main(["gate", "TASK-0001", "--format", "json"]) == (0 if passed else 2)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == decision.to_dict()
    assert captured.err == ""


def test_review_json_success_retains_payload_and_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)

    assert cli.main(["review", "show", "TASK-0001", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"task_id": "TASK-0001", "reviews": []}
    assert captured.err == ""


def test_unexpected_programming_error_is_not_misreported_as_domain_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(*_args: object) -> int:
        raise RuntimeError("unexpected implementation fault")

    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)
    monkeypatch.setattr(cli, "_dispatch", fail)

    with pytest.raises(RuntimeError, match="unexpected implementation fault"):
        cli.main(["status", "TASK-0001", "--format", "json"])
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
