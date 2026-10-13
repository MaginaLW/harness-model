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

from aiflow.contracts import SCHEMA_FILES
from aiflow.gate import GateDecision
from aiflow.git_context import GitContext, collect_git_context
from aiflow.mutation_manifest import CANONICAL_MANIFEST_PATH
from aiflow.policy import POLICY_FILES
from aiflow.status_service import StatusSummary
from aiflow.task_service import start_task

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def advisory_module() -> Any:
    path = PROJECT_ROOT / "tools" / "analysis" / "review_advisory.py"
    spec = importlib.util.spec_from_file_location("review_advisory", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def advisory(advisory_module: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(advisory_module, "_input_fingerprint", lambda *_args: "stable")
    return advisory_module


@pytest.fixture
def input_repository(tmp_path: Path, advisory_module: Any, monkeypatch: pytest.MonkeyPatch) -> Path:
    repository = tmp_path / "repository"
    (repository / ".ai" / "tasks" / "TASK-0001").mkdir(parents=True)
    (repository / ".ai" / "policy").mkdir()
    (repository / ".ai" / "schemas").mkdir()
    (repository / ".ai" / "repository-id").write_text("PRIVATE identity", encoding="utf-8")
    context = GitContext(
        "123e4567-e89b-42d3-a456-426614174000",
        repository.resolve().as_posix(),
        "main",
        "a" * 40,
        False,
        (),
    )
    monkeypatch.setattr(advisory_module, "collect_git_context", lambda *_args: context)
    return repository


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


def _link_directory(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as error:
        if os.name != "nt":
            pytest.skip(f"symlink creation unavailable: {error}")
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        if created.returncode != 0:
            pytest.skip(f"junction creation unavailable: {created.stderr}")


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
    reads: list[str] = []

    def fingerprint(root: Path, task_id: str) -> str:
        assert root == tmp_path and task_id == "TASK-0001" and Path.cwd() == tmp_path
        assert os.environ["GIT_OPTIONAL_LOCKS"] == "0"
        assert os.environ["GIT_INDEX_FILE"] == "unchanged-input"
        reads.append("fingerprint")
        return "stable"

    def status(root: Path, _task_id: str) -> StatusSummary:
        assert root == tmp_path and Path.cwd() == tmp_path
        assert os.environ["GIT_OPTIONAL_LOCKS"] == "0"
        assert os.environ["GIT_INDEX_FILE"] == "unchanged-input"
        reads.append("status")
        if failure_stage == "status":
            raise RuntimeError("SENSITIVE failure /private/path")
        return _summary(current_state="APPROVED_FOR_MERGE", missing_conditions=("external_merge",))

    def gate(root: Path, _task_id: str) -> GateDecision:
        assert root == tmp_path and os.environ["GIT_OPTIONAL_LOCKS"] == "0"
        reads.append("gate")
        if failure_stage == "gate":
            raise RuntimeError("SENSITIVE gate /private/path")
        return GateDecision("TASK-0001", True, "REVIEW", "V1", (), ())

    monkeypatch.setattr(advisory, "summarize_task", status)
    monkeypatch.setattr(advisory, "evaluate_gate", gate)
    monkeypatch.setattr(advisory, "_input_fingerprint", fingerprint)

    result, report = _run(advisory, tmp_path, capsys)

    assert result == (1 if failure_stage else 0)
    if failure_stage:
        assert report["error_code"] == f"NATIVE_{failure_stage.upper()}_READ_FAILED"
    assert reads == (
        ["fingerprint", "status", "fingerprint"]
        if failure_stage == "status"
        else ["fingerprint", "status", "gate", "fingerprint"]
    )
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
    monkeypatch.setattr(
        advisory, "_input_fingerprint", lambda *_args: pytest.fail("invalid ID check")
    )
    assert advisory.main(["SENSITIVE-invalid", "--repository", str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["error_code"] == "ADVISORY_INPUT_INVALID"
    assert report["task_id"] is None


@pytest.fixture
def native_repository(tmp_path: Path) -> Path:
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
    return repository


def test_real_native_status_leaves_all_repository_files_and_git_index_unchanged(
    tmp_path: Path,
    native_repository: Path,
    capsys: pytest.CaptureFixture[str],
    advisory_module: Any,
) -> None:
    repository = native_repository
    tracked = repository / "tracked.txt"
    tool = repository / "tools" / "analysis" / "review_advisory.py"
    stat = tracked.stat()
    os.utime(tracked, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    before = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }

    result, report = _run(advisory_module, repository, capsys)

    assert result == 0
    assert report["native_status"]["current_state"] == "NEW"
    assert report["mechanical_preparation"] == ["PREPARE_CLASSIFICATION_FACTS"]
    assert "SOURCE_INPUTS_CHANGED_DURING_READ" not in report["unknown"]
    assert "SOURCE_INPUT_CHANGE_CHECK_UNAVAILABLE" not in report["unknown"]
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
    monkeypatch.setattr(
        advisory, "_input_fingerprint", lambda *_args: pytest.fail("help input check")
    )
    with pytest.raises(SystemExit) as caught:
        advisory.main(["--help"])
    assert caught.value.code == 0
    assert sys.dont_write_bytecode is previous_bytecode


@pytest.mark.parametrize("passed", [True, False])
@pytest.mark.parametrize(
    ("fingerprints", "diagnostic"),
    [
        (("stable", "stable"), None),
        (("PRIVATE before", "PRIVATE after"), "SOURCE_INPUTS_CHANGED_DURING_READ"),
        ((None, "stable"), "SOURCE_INPUT_CHANGE_CHECK_UNAVAILABLE"),
        (("stable", None), "SOURCE_INPUT_CHANGE_CHECK_UNAVAILABLE"),
        ((None, None), "SOURCE_INPUT_CHANGE_CHECK_UNAVAILABLE"),
    ],
)
def test_input_diagnostic_only_adds_unknown_without_repeating_native_reads(
    fingerprints: tuple[str | None, str | None],
    diagnostic: str | None,
    passed: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    advisory: Any,
) -> None:
    calls: list[str] = []

    def status(*_args: object) -> StatusSummary:
        calls.append("status")
        return _summary(current_state="APPROVED_FOR_MERGE", missing_conditions=("external_merge",))

    def gate(*_args: object) -> GateDecision:
        calls.append("gate")
        return GateDecision("TASK-0001", passed, "REVIEW", "V1", (), ())

    monkeypatch.setattr(advisory, "summarize_task", status)
    monkeypatch.setattr(advisory, "evaluate_gate", gate)
    _, expected = _run(advisory, tmp_path, capsys)
    calls.clear()
    values = iter(fingerprints)

    def fingerprint(root: Path, task_id: str) -> str | None:
        assert root == tmp_path and task_id == "TASK-0001" and Path.cwd() == tmp_path
        assert os.environ["GIT_OPTIONAL_LOCKS"] == "0"
        calls.append("fingerprint")
        return next(values)

    monkeypatch.setattr(advisory, "_input_fingerprint", fingerprint)
    result, report = _run(advisory, tmp_path, capsys)

    assert result == 0
    assert calls == ["fingerprint", "status", "gate", "fingerprint"]
    if diagnostic is not None:
        expected["unknown"] = sorted([*expected["unknown"], diagnostic])
    assert report == expected


@pytest.mark.parametrize(
    "relative_path",
    [
        *(
            f".ai/tasks/TASK-0001/{name}"
            for name in (
                "task.yaml",
                "spec.md",
                "classification.json",
                "approvals.json",
                "evidence.json",
                "events.jsonl",
                "review-package.md",
                "creation_failed.json",
                "approval_pending.json",
            )
        ),
        ".ai/repository-id",
        CANONICAL_MANIFEST_PATH.as_posix(),
        *(f".ai/policy/{name}" for name in POLICY_FILES),
        *(f".ai/schemas/{name}" for name in SCHEMA_FILES.values()),
    ],
)
def test_fixed_input_bytes_and_presence_are_checked_with_unchanged_git_context(
    relative_path: str, input_repository: Path, advisory_module: Any
) -> None:
    target = input_repository / relative_path
    existed = target.exists()
    before = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"PRIVATE A")
    created = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    metadata = target.stat()
    target.write_bytes(b"PRIVATE B")
    os.utime(target, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    changed = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    target.unlink()
    removed = advisory_module._input_fingerprint(input_repository, "TASK-0001")

    assert None not in (before, created, changed, removed)
    assert before != created != changed != removed
    if not existed:
        assert removed == before


@pytest.mark.parametrize("directory", ["reviews", "review-contexts", "verifier-contexts"])
def test_review_input_collections_check_directory_and_json_membership(
    directory: str, input_repository: Path, advisory_module: Any
) -> None:
    root = input_repository / ".ai" / "tasks" / "TASK-0001" / directory
    missing = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    root.mkdir()
    empty = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    target = root / "PRIVATE-record.json"
    target.write_bytes(b"PRIVATE A")
    added = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    target.write_bytes(b"PRIVATE B")
    changed = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    target.unlink()
    removed = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    root.rmdir()
    absent = advisory_module._input_fingerprint(input_repository, "TASK-0001")

    assert None not in (missing, empty, added, changed)
    assert len({missing, empty, added, changed}) == 4
    assert removed == empty and absent == missing


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository_id", "123e4567-e89b-42d3-a456-426614174001"),
        ("branch", "other"),
        ("head", "b" * 40),
        ("worktree_dirty", True),
        ("dirty_paths", ("PRIVATE-path.txt",)),
    ],
)
def test_each_git_context_input_change_is_detected(
    field: str,
    value: object,
    input_repository: Path,
    advisory_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = advisory_module.collect_git_context(input_repository)
    before = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    monkeypatch.setattr(
        advisory_module, "collect_git_context", lambda *_args: replace(context, **{field: value})
    )
    after = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    assert before is not None and after is not None and before != after


def test_extra_policy_names_are_checked_without_reading_their_contents(
    input_repository: Path, advisory_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    extra = input_repository / ".ai" / "policy" / "PRIVATE-extra.yaml"
    extra.write_bytes(b"PRIVATE A")
    original_read = Path.read_bytes

    def safe_read(path: Path) -> bytes:
        assert path != extra
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", safe_read)
    added = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    extra.write_bytes(b"PRIVATE B")
    changed = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    assert before is not None and added is not None and before != added
    assert changed == added


def test_logs_and_other_tasks_are_never_read_or_content_fingerprinted(
    input_repository: Path, advisory_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    ignored = [
        input_repository / ".ai" / "tasks" / "TASK-0001" / "logs" / "PRIVATE-log.txt",
        input_repository / ".ai" / "tasks" / "TASK-0002" / "task.yaml",
    ]
    for target in ignored:
        target.parent.mkdir(parents=True)
        target.write_bytes(b"PRIVATE A")
    original_read = Path.read_bytes

    def safe_read(path: Path) -> bytes:
        assert path not in ignored
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", safe_read)
    before = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    for target in ignored:
        target.write_bytes(b"PRIVATE B")
    after = advisory_module._input_fingerprint(input_repository, "TASK-0001")
    assert before is not None and before == after


@pytest.mark.parametrize("failure", ["bytes", "git", "repository_identity", "path_escape"])
def test_input_check_failures_are_unavailable_without_reading_unsafe_paths(
    failure: str,
    input_repository: Path,
    advisory_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = input_repository / ".ai" / "repository-id"
    outside = input_repository.parent / "PRIVATE-outside.txt"
    original_read = Path.read_bytes
    reads: list[Path] = []

    def safe_read(path: Path) -> bytes:
        reads.append(path)
        if failure == "bytes" and path == target:
            raise PermissionError("PRIVATE failure")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", safe_read)
    if failure == "git":

        def fail_git(*_args: object) -> None:
            raise RuntimeError("PRIVATE git failure")

        monkeypatch.setattr(advisory_module, "collect_git_context", fail_git)
    elif failure == "repository_identity":
        context = advisory_module.collect_git_context(input_repository)
        monkeypatch.setattr(
            advisory_module,
            "collect_git_context",
            lambda *_args: replace(context, repository_path=outside.as_posix()),
        )
    elif failure == "path_escape":
        original_resolve = Path.resolve

        def resolve(path: Path, strict: bool = False) -> Path:
            return outside if path == target else original_resolve(path, strict=strict)

        monkeypatch.setattr(Path, "resolve", resolve)

    assert advisory_module._input_fingerprint(input_repository, "TASK-0001") is None
    assert outside not in reads


@pytest.mark.parametrize(
    "relative_path",
    [
        ".ai/tasks/TASK-0001/spec.md",
        ".ai/tasks/TASK-0001/reviews/PRIVATE-record.json",
        ".ai/policy/routing.yaml",
        ".ai/schemas/task.schema.json",
    ],
)
def test_non_file_input_is_unavailable(
    relative_path: str, input_repository: Path, advisory_module: Any
) -> None:
    (input_repository / relative_path).mkdir(parents=True)
    assert advisory_module._input_fingerprint(input_repository, "TASK-0001") is None


@pytest.mark.parametrize(
    "relative_path",
    [
        ".ai/policy",
        ".ai/schemas",
        ".ai/tasks",
        ".ai/tasks/TASK-0001",
        ".ai/tasks/TASK-0001/reviews",
    ],
)
def test_non_directory_input_group_is_unavailable(
    relative_path: str, input_repository: Path, advisory_module: Any
) -> None:
    target = input_repository / relative_path
    if relative_path == ".ai/tasks":
        (target / "TASK-0001").rmdir()
    if target.is_dir():
        target.rmdir()
    target.write_bytes(b"PRIVATE content")
    assert advisory_module._input_fingerprint(input_repository, "TASK-0001") is None


@pytest.mark.parametrize(
    "relative_path",
    [
        ".ai/policy/routing.yaml",
        ".ai/schemas/task.schema.json",
        ".ai/tasks/TASK-0001/spec.md",
        ".ai/tasks/TASK-0001/reviews/PRIVATE-record.json",
    ],
)
def test_input_file_cannot_resolve_outside_its_declared_parent_inside_the_repository(
    relative_path: str,
    input_repository: Path,
    advisory_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = input_repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"PRIVATE local content")
    outside_parent = input_repository / "PRIVATE-other-location.txt"
    original_resolve = Path.resolve
    original_read = Path.read_bytes
    reads: list[Path] = []

    def resolve(path: Path, strict: bool = False) -> Path:
        return outside_parent if path == target else original_resolve(path, strict=strict)

    def safe_read(path: Path) -> bytes:
        reads.append(path)
        return original_read(path)

    monkeypatch.setattr(Path, "resolve", resolve)
    monkeypatch.setattr(Path, "read_bytes", safe_read)
    assert advisory_module._input_fingerprint(input_repository, "TASK-0001") is None
    assert target not in reads and outside_parent not in reads


@pytest.mark.parametrize(
    "relative_path", [".ai/policy", ".ai/schemas", ".ai/tasks/TASK-0001/reviews"]
)
def test_input_directory_link_escape_is_rejected_before_reading_external_contents(
    relative_path: str,
    input_repository: Path,
    advisory_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = input_repository.parent / "PRIVATE-outside"
    outside.mkdir()
    (outside / "PRIVATE-record.json").write_bytes(b"PRIVATE external content")
    link = input_repository / relative_path
    if link.is_dir():
        link.rmdir()
    _link_directory(link, outside)
    original_read = Path.read_bytes
    reads: list[Path] = []

    def safe_read(path: Path) -> bytes:
        reads.append(path.resolve())
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", safe_read)
    assert advisory_module._input_fingerprint(input_repository, "TASK-0001") is None
    assert not any(path.is_relative_to(outside) for path in reads)


@pytest.mark.parametrize("directory", ["reviews", "review-contexts", "verifier-contexts"])
def test_task_collection_cannot_link_to_another_task_within_the_repository(
    directory: str,
    input_repository: Path,
    advisory_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_task = input_repository / ".ai" / "tasks" / "TASK-0002" / directory
    other_task.mkdir(parents=True)
    (other_task / "PRIVATE-record.json").write_bytes(b"PRIVATE other task content")
    link = input_repository / ".ai" / "tasks" / "TASK-0001" / directory
    _link_directory(link, other_task)
    original_read = Path.read_bytes
    reads: list[Path] = []

    def safe_read(path: Path) -> bytes:
        reads.append(path.resolve())
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", safe_read)
    assert advisory_module._input_fingerprint(input_repository, "TASK-0001") is None
    assert not any(path.is_relative_to(other_task) for path in reads)


def test_unreadable_input_inventory_is_unavailable(
    input_repository: Path, advisory_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_scandir = os.scandir
    original_listdir = os.listdir
    policy_directory = input_repository / ".ai" / "policy"

    def scandir(path: Any) -> Any:
        if Path(path) == policy_directory:
            raise PermissionError("PRIVATE unreadable inventory")
        return original_scandir(path)

    def listdir(path: Any) -> Any:
        if Path(path) == policy_directory:
            raise PermissionError("PRIVATE unreadable inventory")
        return original_listdir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    monkeypatch.setattr(os, "listdir", listdir)
    assert advisory_module._input_fingerprint(input_repository, "TASK-0001") is None


def test_direct_input_check_rejects_invalid_task_id_before_git_reads(
    input_repository: Path, advisory_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        advisory_module, "collect_git_context", lambda *_args: pytest.fail("invalid task Git read")
    )
    assert advisory_module._input_fingerprint(input_repository, "PRIVATE-invalid") is None


@pytest.mark.parametrize(
    ("fingerprints", "diagnostic"),
    [
        (("PRIVATE before", "PRIVATE after"), "SOURCE_INPUTS_CHANGED_DURING_READ"),
        ((None, "PRIVATE after"), "SOURCE_INPUT_CHANGE_CHECK_UNAVAILABLE"),
    ],
)
def test_text_output_keeps_input_diagnostics_without_fingerprint_details(
    fingerprints: tuple[str | None, str | None],
    diagnostic: str,
    tmp_path: Path,
    advisory: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    values = iter(fingerprints)
    monkeypatch.setattr(advisory, "_input_fingerprint", lambda *_args: next(values))
    monkeypatch.setattr(advisory, "summarize_task", lambda *_args: _summary())
    assert advisory.main(["TASK-0001", "--repository", str(tmp_path), "--format", "text"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert diagnostic in captured.out
    assert "SOURCE_READ_ATOMICITY_NOT_ESTABLISHED" in captured.out
    assert "execution_allowed=false" in captured.out
    assert "PRIVATE" not in captured.out and str(tmp_path) not in captured.out


@pytest.mark.parametrize(
    "relative_path",
    [".ai/tasks/TASK-0001/task.yaml", ".ai/policy/routing.yaml", ".ai/schemas/task.schema.json"],
)
def test_real_content_drift_is_visible_with_same_head_and_dirty_paths(
    relative_path: str,
    native_repository: Path,
    advisory_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = native_repository / relative_path
    target.write_bytes(target.read_bytes() + b"\n")
    _, expected = _run(advisory_module, native_repository, capsys)
    native_status = advisory_module.summarize_task
    before_fingerprint = advisory_module._input_fingerprint(native_repository, "TASK-0001")
    context = collect_git_context(native_repository)

    def status(root: Path, task_id: str) -> StatusSummary:
        summary = native_status(root, task_id)
        target.write_bytes(target.read_bytes() + b"\nPRIVATE input content\n")
        assert collect_git_context(root) == context
        return summary

    monkeypatch.setattr(advisory_module, "summarize_task", status)
    result, report = _run(advisory_module, native_repository, capsys)
    after_fingerprint = advisory_module._input_fingerprint(native_repository, "TASK-0001")

    assert result == 0
    expected["unknown"] = sorted([*expected["unknown"], "SOURCE_INPUTS_CHANGED_DURING_READ"])
    assert report == expected
    output = json.dumps(report)
    assert target.name not in output
    assert before_fingerprint not in output and after_fingerprint not in output


def test_real_head_drift_is_diagnosed_without_replacing_the_native_observed_head(
    native_repository: Path,
    advisory_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    native_status = advisory_module.summarize_task
    previous_head = collect_git_context(native_repository).head

    def status(root: Path, task_id: str) -> StatusSummary:
        summary = native_status(root, task_id)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=AI Flow Tests",
                "-c",
                "user.email=aiflow@example.invalid",
                "commit",
                "--allow-empty",
                "-m",
                "drift",
            ],
            cwd=root,
            check=True,
            capture_output=True,
            timeout=10,
        )
        return summary

    monkeypatch.setattr(advisory_module, "summarize_task", status)
    result, report = _run(advisory_module, native_repository, capsys)

    assert result == 0
    assert report["native_status"]["observed_head"] == previous_head
    assert collect_git_context(native_repository).head != previous_head
    assert "SOURCE_INPUTS_CHANGED_DURING_READ" in report["unknown"]
