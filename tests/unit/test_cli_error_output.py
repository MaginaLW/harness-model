"""CLI error boundaries keep machine output useful without exposing internal details."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiflow import cli
from aiflow.classification_service import classify_task
from aiflow.contracts import schema_directory_context
from aiflow.errors import AiflowError, StorageError
from aiflow.facts_service import record_risk_facts
from aiflow.gate import GateDecision
from aiflow.review_service import build_review_context, record_review
from aiflow.status_service import StatusSummary
from aiflow.task_service import freeze_task, start_task

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNICODE_PAYLOAD = "中文目标 🎯"

JSON_COMMANDS = [
    ("status", "TASK-0001"),
    ("advise", "TASK-0001"),
    ("gate", "TASK-0001"),
    ("review", "show", "TASK-0001"),
]


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
        (("advise", "TASK-0001"), "task.yaml"),
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
        ["advise", "--format", "json"],
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


def test_stdout_json_commands_escape_non_ascii_and_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)

    status_summary = StatusSummary(
        task_id="TASK-0001",
        goal=UNICODE_PAYLOAD,
        repository_id="123e4567-e89b-42d3-a456-426614174000",
        current_state="NEW",
        merge_readiness="not_applicable",
        route="REVIEW",
        verification_level="V1",
        next_events=(),
        missing_conditions=(),
        base_commit="0" * 40,
        subject_commit="0" * 40,
        observed_head="0" * 40,
        worktree_dirty=False,
        dirty_paths=(),
        classification="fresh",
        approvals="not_available",
        evidence="not_available",
    )
    monkeypatch.setattr(cli, "summarize_task", lambda *_args: status_summary)
    assert cli.main(["status", "TASK-0001", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert captured.out.isascii()
    assert captured.err == ""
    assert json.loads(captured.out)["goal"] == UNICODE_PAYLOAD

    decision = GateDecision("TASK-0001", True, "REVIEW", "V1", (UNICODE_PAYLOAD,), ())
    monkeypatch.setattr(cli, "evaluate_gate", lambda *_args, **_kwargs: decision)
    assert cli.main(["gate", "TASK-0001", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert captured.out.isascii()
    assert captured.err == ""
    assert json.loads(captured.out)["reason_codes"] == [UNICODE_PAYLOAD]

    monkeypatch.setattr(cli, "advise_task", lambda *_args: {"goal": UNICODE_PAYLOAD})
    assert cli.main(["advise", "TASK-0001", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert captured.out.isascii()
    assert captured.err == ""
    assert json.loads(captured.out)["goal"] == UNICODE_PAYLOAD

    monkeypatch.setattr(
        cli,
        "list_review_records",
        lambda *_args, **_kwargs: (
            {
                "review_id": "REV-0001",
                "revision": 1,
                "review_stage": "design",
                "outcome": "APPROVE",
                "summary": UNICODE_PAYLOAD,
            },
        ),
    )
    assert cli.main(["review", "show", "TASK-0001", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert captured.out.isascii()
    assert captured.err == ""
    assert json.loads(captured.out)["reviews"][0]["summary"] == UNICODE_PAYLOAD

    monkeypatch.setattr(
        cli,
        "build_review_context",
        lambda *_args: {"task_id": "TASK-0001", "goal": UNICODE_PAYLOAD},
    )
    assert cli.main(["review", "context", "TASK-0001", "--stage", "design"]) == 0
    captured = capsys.readouterr()
    assert captured.out.isascii()
    assert captured.err == ""
    assert json.loads(captured.out)["goal"] == UNICODE_PAYLOAD


@pytest.fixture(scope="module")
def unicode_task_repository(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("cli-json-ascii-pipes")
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    ai_root = repo / ".ai"
    ai_root.mkdir()
    for folder in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / folder, ai_root / folder)
    (ai_root / "repository-id").write_text(
        "123e4567-e89b-42d3-a456-426614174000\n", encoding="utf-8"
    )
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", ".ai", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=AI Flow Tests",
            "-c",
            "user.email=aiflow@example.invalid",
            "commit",
            "-m",
            "initial",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    facts_file = repo.parent / "unicode-facts.json"
    facts_file.write_text(
        json.dumps(
            {
                "scope": {"clear": True},
                "impact": {"level": "low"},
                "protections": {"verified_backup": True, "dry_run": True},
                "verification": {"automatic": True, "tools_missing": False},
                "impact_categories": ["documentation"],
                "controlled_actions": [],
                "business_direction_count": 1,
                "change_characteristics": {
                    "mechanical": False,
                    "behavior_changed": True,
                    "code_modified": True,
                    "interaction_scope": "cross_module",
                    "regression_risk": True,
                    "error_detectability": "high",
                },
                "verification_requirements": {
                    "acceptance_required": False,
                    "integration_required": False,
                    "targeted_mutation_required": False,
                    "independent_verifier_required": False,
                },
                "reversibility": "reversible",
                "external_side_effects": [],
                "permission_requirements": [],
            }
        ),
        encoding="utf-8",
    )

    with schema_directory_context(ai_root / "schemas"):
        start_result = start_task(
            repo,
            objective=UNICODE_PAYLOAD,
            allowed_scope=("src/aiflow/cli.py",),
            forbidden_actions=(),
        )
        task_id = start_result.task_id
        spec_path = ai_root / "tasks" / task_id / "spec.md"
        spec_path.write_text(
            "\n".join(
                (
                    "# Task Specification",
                    "",
                    "## 目标",
                    UNICODE_PAYLOAD,
                    "",
                    "## 范围",
                    "src/aiflow/cli.py",
                    "",
                    "## 非目标",
                    "无",
                    "",
                    "## 验收条件",
                    "通过测试",
                    "",
                    "## 禁止动作",
                    "无",
                    "",
                    "## 错误行为",
                    "失败退出",
                    "",
                    "## 回滚",
                    "git revert",
                )
            ),
            encoding="utf-8",
        )
        record_risk_facts(
            repo,
            task_id,
            decision_unit_id="DU-001",
            input_path=facts_file,
            actor="author",
        )
        classify_task(repo, task_id, actor="author")
        freeze_task(repo, task_id, actor="author")
        context = build_review_context(repo, task_id, "design")
        review_file = repo.parent / "unicode-review.json"
        review_file.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "review_id": "REV-0001",
                    "review_stage": "design",
                    "recorded_at": "2026-11-28T06:00:00Z",
                    "context_sha256": context["context_sha256"],
                    "outcome": "APPROVE",
                    "summary": UNICODE_PAYLOAD,
                    "findings": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        record_review(repo, task_id, input_path=review_file, actor="reviewer")

    return repo


@pytest.mark.parametrize("encoding", ["cp1252", "gbk"])
def test_cli_json_stdout_survives_non_utf8_pipe_encoding(
    unicode_task_repository: Path, encoding: str
) -> None:
    environment = os.environ.copy()
    environment.pop("PYTHONUTF8", None)
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["PYTHONIOENCODING"] = encoding

    cases: tuple[tuple[tuple[str, ...], int], ...] = (
        (("status", "TASK-0001", "--format", "json"), 0),
        (("advise", "TASK-0001", "--format", "json"), 0),
        (("gate", "TASK-0001", "--format", "json"), 2),
        (("review", "show", "TASK-0001", "--format", "json"), 0),
        (("review", "context", "TASK-0001", "--stage", "design"), 0),
    )

    decoded_payloads: dict[str, dict[str, object]] = {}
    for arguments, expected_code in cases:
        result = subprocess.run(
            [sys.executable, "-m", "aiflow", *arguments],
            cwd=unicode_task_repository,
            env=environment,
            capture_output=True,
            check=False,
            timeout=30,
        )
        assert result.returncode == expected_code, result.stderr.decode(encoding, errors="replace")
        assert result.stderr == b""
        assert b"UnicodeEncodeError" not in result.stderr
        text = result.stdout.decode(encoding)
        assert text.isascii()
        decoded_payloads[arguments[0] if arguments[0] != "review" else f"review_{arguments[1]}"] = (
            json.loads(text)
        )

    assert decoded_payloads["status"]["goal"] == UNICODE_PAYLOAD
    assert decoded_payloads["advise"]["task_id"] == "TASK-0001"
    assert decoded_payloads["gate"]["task_id"] == "TASK-0001"
    reviews = decoded_payloads["review_show"]["reviews"]
    assert isinstance(reviews, list)
    assert reviews[0]["summary"] == UNICODE_PAYLOAD
    content = decoded_payloads["review_context"]["content"]
    assert isinstance(content, dict)
    assert content["goal"] == UNICODE_PAYLOAD
