"""Behavioral checks for the unscored, read-only task preparation advisory."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from contextlib import chdir
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from aiflow.gate import GateDecision
from aiflow.status_service import StatusSummary
from aiflow.task_service import start_task

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def advisory() -> Any:
    path = PROJECT_ROOT / "tools" / "analysis" / "review_advisory.py"
    spec = importlib.util.spec_from_file_location("review_advisory", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary(**changes: object) -> StatusSummary:
    summary = StatusSummary(
        task_id="TASK-0001",
        goal="SENSITIVE goal and actor /private/path",
        repository_id="123e4567-e89b-42d3-a456-426614174000",
        current_state="WAITING_FOR_SPEC_REVIEW",
        merge_readiness="not_applicable",
        route="REVIEW",
        verification_level="V1",
        next_events=("spec_approved",),
        missing_conditions=("spec_approval",),
        base_commit="a" * 40,
        subject_commit="b" * 40,
        observed_head="c" * 40,
        worktree_dirty=True,
        dirty_paths=("PRIVATE-file.txt",),
        classification="fresh",
        approvals="current",
        evidence="not_available",
    )
    return replace(summary, **changes)


def _run(advisory: Any, root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict]:
    result = advisory.main(["TASK-0001", "--repository", str(root)])
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "SENSITIVE" not in captured.out and "PRIVATE" not in captured.out
    assert str(root) not in captured.out and "/private/path" not in captured.out
    report = json.loads(captured.out)
    assert report["probability_status"] == "unestimated"
    assert report["execution_allowed"] is False
    assert "SOURCE_READ_ATOMICITY_NOT_ESTABLISHED" in report["unknown"]
    return result, report


def test_current_approval_is_preserved_without_a_new_human_approval_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: _summary())
    monkeypatch.setattr(advisory, "evaluate_gate", lambda *_args: pytest.fail("premature Gate"))

    result, report = _run(advisory, tmp_path, capsys)

    assert result == 0
    assert report["native_status"]["approvals"] == "current"
    assert report["decision_or_authorization_checks"] == [
        "CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION"
    ]
    assert report["mechanical_preparation"] == []
    assert report["native_gate"] == {"status": "not_evaluated"}
    assert report["native_status"]["missing_conditions"] == ["spec_approval"]
    assert report["advice_basis"] == [
        {
            "advice": "CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION",
            "source": "native_status.missing_conditions",
            "missing_condition": "spec_approval",
        }
    ]


@pytest.mark.parametrize("field", ["base_commit", "subject_commit", "observed_head"])
def test_native_commit_changes_remain_visible_without_changing_native_decisions(
    field: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    summary = _summary()
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: summary)
    _, before = _run(advisory, tmp_path, capsys)

    summary = replace(summary, **{field: "d" * 40})
    _, after = _run(advisory, tmp_path, capsys)

    assert before["native_status"][field] == getattr(_summary(), field)
    assert after["native_status"][field] == "d" * 40
    assert before != after
    before["native_status"][field] = "d" * 40
    assert before == after


def test_absent_subject_is_unknown_without_an_unrecognized_field_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: _summary(subject_commit=None))

    result, report = _run(advisory, tmp_path, capsys)

    assert result == 0
    assert report["native_status"]["subject_commit"] == "unknown"
    assert "NATIVE_STATUS_FIELD_UNRECOGNIZED" not in report["unknown"]


@pytest.mark.parametrize("field", ["base_commit", "subject_commit", "observed_head"])
@pytest.mark.parametrize("value", ["SENSITIVE /private/path", "A" * 40, "d" * 39, "d" * 41])
def test_unrecognized_commit_values_are_not_echoed(
    field: str,
    value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: _summary(**{field: value}))

    result, report = _run(advisory, tmp_path, capsys)

    assert result == 0
    assert report["native_status"][field] == "unknown"
    assert value not in json.dumps(report)
    assert "NATIVE_STATUS_FIELD_UNRECOGNIZED" in report["unknown"]


def test_distinct_native_missing_conditions_keep_their_own_advice_basis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    summary = _summary(
        missing_conditions=("spec_approval", "classification", "code_approval", "classification")
    )
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: summary)

    result, report = _run(advisory, tmp_path, capsys)

    assert result == 0
    assert report["native_status"]["missing_conditions"] == [
        "classification",
        "code_approval",
        "spec_approval",
    ]
    assert report["mechanical_preparation"] == ["PREPARE_CLASSIFICATION_FACTS"]
    assert report["decision_or_authorization_checks"] == [
        "CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION"
    ]
    assert report["advice_basis"] == [
        {
            "advice": "PREPARE_CLASSIFICATION_FACTS",
            "source": "native_status.missing_conditions",
            "missing_condition": "classification",
        },
        {
            "advice": "CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION",
            "source": "native_status.missing_conditions",
            "missing_condition": "code_approval",
        },
        {
            "advice": "CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION",
            "source": "native_status.missing_conditions",
            "missing_condition": "spec_approval",
        },
    ]


@pytest.mark.parametrize("state", ["FAILED", "BLOCKED", "ESCALATED"])
def test_failed_or_blocked_work_is_diagnosed_without_retry_advice(
    state: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    summary = _summary(
        current_state=state,
        missing_conditions=("verification_result", "retry_reason_or_escalation"),
        evidence="stale",
    )
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: summary)

    result, report = _run(advisory, tmp_path, capsys)

    assert result == 0
    assert report["native_status"]["current_state"] == state
    assert report["native_status"]["evidence"] == "stale"
    assert report["mechanical_preparation"] == []
    assert report["decision_or_authorization_checks"] == [
        "CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION"
    ]
    assert report["advice_basis"] == [
        {
            "advice": "CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION",
            "source": "native_status.current_state",
            "state": state,
        }
    ]


def test_merged_history_does_not_become_pending_reverification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    summary = _summary(
        current_state="MERGED", missing_conditions=("reverification",), evidence="stale"
    )
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: summary)
    monkeypatch.setattr(advisory, "evaluate_gate", lambda *_args: pytest.fail("historical Gate"))

    result, report = _run(advisory, tmp_path, capsys)

    assert result == 0
    assert report["native_status"]["evidence"] == "stale"
    assert report["mechanical_preparation"] == report["decision_or_authorization_checks"] == []
    assert report["native_status"]["missing_conditions"] == ["reverification"]
    assert report["advice_basis"] == []


def test_ask_is_a_direction_decision_and_unknown_fields_are_not_repeated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    summary = _summary(
        current_state="WAITING_FOR_ASK",
        missing_conditions=("ask_answer", "SENSITIVE-missing"),
        route="SENSITIVE-route",
    )
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: summary)

    _, report = _run(advisory, tmp_path, capsys)

    assert report["native_status"]["route"] == "unknown"
    assert report["native_status"]["missing_conditions"] == ["ask_answer"]
    assert report["decision_or_authorization_checks"] == ["DECIDE_ASK_DIRECTION"]
    assert report["advice_basis"] == [
        {
            "advice": "DECIDE_ASK_DIRECTION",
            "source": "native_status.missing_conditions",
            "missing_condition": "ask_answer",
        }
    ]
    assert "NATIVE_MISSING_CONDITION_UNRECOGNIZED" in report["unknown"]


@pytest.mark.parametrize("passed", [True, False])
def test_only_native_gate_reports_merge_eligibility_and_it_does_not_grant_execution(
    passed: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    summary = _summary(current_state="APPROVED_FOR_MERGE", missing_conditions=("external_merge",))
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: summary)
    reasons = () if passed else ("GATE_EVIDENCE_STALE", "SENSITIVE-reason")
    monkeypatch.setattr(
        advisory,
        "evaluate_gate",
        lambda *_args: GateDecision("TASK-0001", passed, "REVIEW", "V1", reasons, ()),
    )

    result, report = _run(advisory, tmp_path, capsys)

    assert result == 0
    assert report["native_gate"]["passed"] is passed
    assert report["native_gate"]["reason_codes"] == ([] if passed else ["GATE_EVIDENCE_STALE"])
    assert report["decision_or_authorization_checks"] == [
        "CHECK_GATE_AND_EXTERNAL_ACTION_AUTHORIZATION"
    ]


@pytest.mark.parametrize("original_locks", [None, "1"])
@pytest.mark.parametrize("failure_stage", [None, "status", "gate"])
def test_scoped_cwd_and_git_optional_locks_restore_after_success_or_native_failure(
    original_locks: str | None,
    failure_stage: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    original_cwd = Path.cwd()
    if original_locks is None:
        monkeypatch.delenv("GIT_OPTIONAL_LOCKS", raising=False)
    else:
        monkeypatch.setenv("GIT_OPTIONAL_LOCKS", original_locks)
    monkeypatch.setenv("GIT_INDEX_FILE", "unchanged-input")

    def status(root: Path, _task_id: str) -> StatusSummary:
        assert root == tmp_path and Path.cwd() == tmp_path
        assert os.environ["GIT_OPTIONAL_LOCKS"] == "0"
        assert os.environ["GIT_INDEX_FILE"] == "unchanged-input"
        if failure_stage == "status":
            raise RuntimeError("SENSITIVE failure /private/path")
        return _summary(current_state="APPROVED_FOR_MERGE", missing_conditions=("external_merge",))

    def gate(root: Path, _task_id: str) -> GateDecision:
        assert root == tmp_path and os.environ["GIT_OPTIONAL_LOCKS"] == "0"
        if failure_stage == "gate":
            raise RuntimeError("SENSITIVE gate /private/path")
        return GateDecision("TASK-0001", True, "REVIEW", "V1", (), ())

    monkeypatch.setattr(advisory, "summarize_task", status)
    monkeypatch.setattr(advisory, "evaluate_gate", gate)

    result, report = _run(advisory, tmp_path, capsys)

    assert result == (1 if failure_stage else 0)
    if failure_stage:
        assert report["error_code"] == f"NATIVE_{failure_stage.upper()}_READ_FAILED"
    assert Path.cwd() == original_cwd
    assert os.environ.get("GIT_OPTIONAL_LOCKS") == original_locks
    assert os.environ["GIT_INDEX_FILE"] == "unchanged-input"


def test_invalid_id_is_rejected_without_native_reads_or_echoing_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: pytest.fail("invalid ID read"))
    assert advisory.main(["SENSITIVE-invalid", "--repository", str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["error_code"] == "ADVISORY_INPUT_INVALID"
    assert report["task_id"] is None


def test_real_native_status_leaves_all_repository_files_and_git_index_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], advisory: Any
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", *arguments], cwd=repository, check=True, capture_output=True, timeout=10
        )

    git("init", "-b", "main")
    for directory in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / directory, repository / ".ai" / directory)
    (repository / ".ai" / "repository-id").write_text(
        "123e4567-e89b-42d3-a456-426614174000\n", encoding="utf-8"
    )
    tracked = repository / "tracked.txt"
    tracked.write_text("initial\n", encoding="utf-8")
    shutil.copytree(
        PROJECT_ROOT / "src" / "aiflow",
        repository / "src" / "aiflow",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    tool = repository / "tools" / "analysis" / "review_advisory.py"
    tool.parent.mkdir(parents=True)
    shutil.copyfile(PROJECT_ROOT / "tools" / "analysis" / "review_advisory.py", tool)
    git("add", ".")
    git(
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    with chdir(repository):
        start_task(
            repository,
            objective="SENSITIVE goal",
            allowed_scope=["tracked.txt"],
            forbidden_actions=[],
        )
    stat = tracked.stat()
    os.utime(tracked, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    before = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }

    result, report = _run(advisory, repository, capsys)

    assert result == 0
    assert report["native_status"]["current_state"] == "NEW"
    assert report["mechanical_preparation"] == ["PREPARE_CLASSIFICATION_FACTS"]
    after = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    assert before == after
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(repository / "src")
    result_cli = subprocess.run(
        [sys.executable, str(tool), "TASK-0001"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result_cli.returncode == 0 and result_cli.stderr == ""
    assert json.loads(result_cli.stdout)["native_status"]["current_state"] == "NEW"
    assert not list(repository.rglob("__pycache__"))
    assert before == {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }


def test_default_repository_is_the_tools_clone_and_help_needs_no_native_read(
    monkeypatch: pytest.MonkeyPatch, advisory: Any
) -> None:
    assert advisory.DEFAULT_REPOSITORY == PROJECT_ROOT
    previous_bytecode = sys.dont_write_bytecode
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: pytest.fail("help native read"))
    with pytest.raises(SystemExit) as caught:
        advisory.main(["--help"])
    assert caught.value.code == 0
    assert sys.dont_write_bytecode is previous_bytecode
