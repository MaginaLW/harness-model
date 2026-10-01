"""Integration tests for begin, failed retry, and close commands."""

from __future__ import annotations

import hashlib
import os
import shutil
import signal
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from aiflow.cli import main
from aiflow.decision_units import classification_input_digest, parse_decision_units
from aiflow.policy import load_policy_bundle
from aiflow.status_service import summarize_task
from aiflow.storage import atomic_write_json, atomic_write_yaml, read_task_json, resolve_task_path
from aiflow.task_service import (
    freeze_task,
    load_task_record,
    transition_task_record,
)
from tests.integration import repository_fixture
from tests.integration.repository_fixture import populate_or_copy

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"


def _cleanup_fixture_process(process: subprocess.Popen[str]) -> tuple[str, str] | None:
    """Bound every owned cleanup wait without replacing the triggering exception."""
    if os.name == "nt":
        try:
            if process.poll() is None:
                taskkill = Path(os.environ["SystemRoot"]) / "System32" / "taskkill.exe"
                helper = subprocess.Popen(
                    [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                try:
                    helper.wait(timeout=5)
                except BaseException:
                    try:
                        helper.kill()
                    except BaseException:
                        pass
                    try:
                        helper.wait(timeout=1)
                    except BaseException:
                        pass
        except BaseException:
            pass
    else:
        try:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
        except BaseException:
            pass
    try:
        process.kill()
    except BaseException:
        pass
    try:
        process.wait(timeout=5)
    except BaseException:
        pass
    try:
        return process.communicate(timeout=5)
    except BaseException:
        return None


def _run_fixture_command(
    repository: Path, argv: list[str], *, env: dict[str, str] | None = None
) -> str:
    """Retain the fixture deadline and clean up every successfully spawned command."""
    process: subprocess.Popen[str] | None = None
    drained = False
    streams_closed = False
    options: dict[str, Any] = {} if env is None else {"env": env}
    try:
        process = subprocess.Popen(
            argv,
            cwd=repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            **options,
        )
        stdout, stderr = process.communicate(timeout=10)
        drained = True
        assert process.stdout is not None and process.stderr is not None
        process.stdout.close()
        process.stderr.close()
        streams_closed = True
        if process.returncode:
            raise subprocess.CalledProcessError(
                process.returncode, argv, output=stdout, stderr=stderr
            )
        return stdout.rstrip("\r\n")
    except BaseException as original:
        if process is not None and not drained:
            try:
                captured = _cleanup_fixture_process(process)
                if captured is not None:
                    drained = True
                    if isinstance(original, subprocess.TimeoutExpired):
                        original.output, original.stderr = captured
            except BaseException:
                pass
        try:
            if drained and not streams_closed and process is not None:
                # A reader which did not drain may retain the stream's read lock.
                # Only close completed streams, without masking the original failure.
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        try:
                            stream.close()
                        except BaseException:
                            pass
        except BaseException:
            pass
        raise


def run_git(repository: Path, *arguments: str) -> str:
    return _run_fixture_command(
        repository, ["git", *arguments], env=repository_fixture.git_child_environment(repository)
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows timeout cleanup with inherited child pipes")
def test_fixture_command_timeout_terminates_real_pipe_holding_child(tmp_path: Path) -> None:
    import ctypes
    import time
    from ctypes import wintypes

    pid_file = tmp_path / "owned-child.pid"
    child = (
        "import os, pathlib, sys, time; "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    )
    parent = (
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]], "
        "stdout=sys.stdout, stderr=sys.stderr); time.sleep(60)"
    )
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        _run_fixture_command(tmp_path, [sys.executable, "-c", parent, child, str(pid_file)])
    assert caught.value.timeout == 10
    assert time.monotonic() - started < 30
    child_pid = int(pid_file.read_text())
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, child_pid)
    if handle:
        try:
            exit_code = wintypes.DWORD()
            assert kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            assert exit_code.value != 259  # STILL_ACTIVE
        finally:
            assert kernel.CloseHandle(handle)
    else:
        assert ctypes.get_last_error() == 87  # PID no longer exists


def commit_all(repository: Path, message: str) -> None:
    run_git(repository, "add", ".")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        message,
    )


def _populate_repository(path: Path) -> Path:
    run_git(path, "init", "-b", "main")
    ai_root = path / ".ai"
    ai_root.mkdir()
    for directory in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / directory, ai_root / directory)
    (ai_root / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    run_git(path, "add", ".ai", "tracked.txt")
    run_git(
        path,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "initial",
    )
    return path


_STANDARD_RUN_GIT = run_git
_STANDARD_COMMAND = _run_fixture_command
_STANDARD_POPULATE = _populate_repository


def create_repository(path: Path) -> Path:
    path.mkdir()
    return populate_or_copy(
        path,
        project_root=PROJECT_ROOT,
        repository_id=REPOSITORY_ID,
        populate=_populate_repository,
        run_git=run_git,
        standard_helpers=(
            run_git is _STANDARD_RUN_GIT
            and _run_fixture_command is _STANDARD_COMMAND
            and _populate_repository is _STANDARD_POPULATE
        ),
    )


def start(repository: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repository)
    assert main(["start", "--objective", "bounded", "--allow", "src/**"]) == 0


def classification(route: str, policy_sha: str = "b" * 64) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "classification_input_sha256": "a" * 64,
        "policy_version": "1.0.0",
        "policy_sha256": policy_sha,
        "base_commit": "1" * 40,
        "subject_commit": "1" * 40,
        "classified_at": "2026-08-20T14:00:00Z",
        "effective_route": route,
        "effective_verification_level": "V1",
        "change_reason": "unchanged",
        "classifications": [
            {
                "decision_unit_id": "DU-001",
                "route": route,
                "verification_level": "V1",
                "rule_id": "TEST-RULE",
                "explanation": "test classification",
                "matched_rules": [
                    {
                        "rule_id": "TEST-RULE",
                        "priority": 1,
                        "route": route,
                        "explanation": "test classification",
                        "predicate_explanations": [],
                    }
                ],
                "explanations": ["test classification"],
                "verification_rule_ids": ["TEST-VERIFICATION"],
                "verification_explanations": ["test verification"],
                "verification_blocking_reasons": [],
                "policy_version": "1.0.0",
                "policy_sha256": policy_sha,
                "classified_at": "2026-08-20T14:00:00Z",
            }
        ],
    }


def make_ready(
    repository: Path,
    *,
    route: str = "AUTO",
    freeze_spec: bool = True,
    valid_approval: bool = False,
) -> None:
    task_directory = repository / ".ai" / "tasks" / "TASK-0001"
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="CLASSIFIED",
        event_type="classification_recorded",
        actor="tester",
        payload={},
        satisfied_preconditions={"classification_available"},
    )
    if freeze_spec:
        freeze_task(repository, "TASK-0001", actor="tester")
    policy_sha = load_policy_bundle(repository).sha256
    task = load_task_record(repository, "TASK-0001").task
    classification_record = classification(route, policy_sha)
    classification_record["base_commit"] = task["base_commit"]
    classification_record["subject_commit"] = task["subject_commit"]
    classification_record["classification_input_sha256"] = classification_input_digest(
        task, parse_decision_units(task)
    )
    atomic_write_json(task_directory / "classification.json", classification_record)
    approvals: list[dict[str, Any]] = []
    if valid_approval:
        spec_sha = hashlib.sha256((task_directory / "spec.md").read_bytes()).hexdigest()
        approvals.append(
            {
                "schema_version": "1.0",
                "task_id": "TASK-0001",
                "decision_unit_id": "DU-001",
                "approval_type": "spec",
                "actor": "reviewer",
                "reason": "spec is complete",
                "spec_sha256": spec_sha,
                "policy_sha256": policy_sha,
                "base_commit": task["base_commit"],
                "subject_commit": task["subject_commit"],
                "approved_at": "2026-08-20T14:00:00Z",
            }
        )
    atomic_write_json(task_directory / "approvals.json", approvals)
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="READY_TO_IMPLEMENT",
        event_type="implementation_ready",
        actor="tester",
        payload={},
        satisfied_preconditions={"classification_route_selected", "spec_frozen"},
    )


def make_failed(repository: Path, payload: dict[str, object]) -> None:
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="VERIFYING",
        event_type="verification_started",
        actor="tester",
        payload={},
        satisfied_preconditions={"implementation_complete"},
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="FAILED",
        event_type="verification_failed",
        actor="tester",
        payload=payload,
        satisfied_preconditions={"verification_failed"},
    )


def make_approved(repository: Path) -> None:
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="VERIFYING",
        event_type="verification_started",
        actor="tester",
        payload={},
        satisfied_preconditions={"implementation_complete"},
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="VERIFIED",
        event_type="verification_passed",
        actor="tester",
        payload={},
        satisfied_preconditions={"verification_passed"},
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="APPROVED_FOR_MERGE",
        event_type="merge_approved_automatically",
        actor="tester",
        payload={},
        satisfied_preconditions={"final_review_not_required"},
    )


@pytest.mark.parametrize(
    ("route", "with_approval"),
    [("AUTO", False), ("REVIEW", True)],
)
def test_begin_ready_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    with_approval: bool,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route=route, valid_approval=with_approval)

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "IMPLEMENTING"
    assert record.events[-1]["event_type"] == "implementation_started"


def test_begin_and_status_accept_spec_approval_after_subject_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW", valid_approval=True)
    commit_all(repository, "record approved specification")
    task = load_task_record(repository, "TASK-0001").task
    task["subject_commit"] = run_git(repository, "rev-parse", "HEAD")
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    current_classification = read_task_json(repository, "TASK-0001", "classification.json")
    current_classification["subject_commit"] = task["subject_commit"]
    current_classification["classification_input_sha256"] = classification_input_digest(
        task, parse_decision_units(task)
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"),
        current_classification,
    )
    approvals_path = resolve_task_path(repository, "TASK-0001", "approvals.json")
    approvals_before = approvals_path.read_bytes()

    summary = summarize_task(repository, "TASK-0001")
    assert summary.classification == "fresh"
    assert summary.approvals == "current"
    assert summary.missing_conditions == ("begin",)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "IMPLEMENTING"
    assert approvals_path.read_bytes() == approvals_before


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("base_commit", "0" * 40),
        ("policy_sha256", "0" * 64),
        ("spec_sha256", "0" * 64),
        ("base_commit", None),
        ("policy_sha256", None),
        ("spec_sha256", None),
        ("approval_type", "code"),
        ("decision_unit_id", "DU-999"),
    ],
)
def test_begin_rejects_invalid_spec_approval_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    field: str,
    replacement: str | None,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW", valid_approval=True)
    approvals = read_task_json(repository, "TASK-0001", "approvals.json")
    if replacement is None:
        approvals[0].pop(field)
    else:
        approvals[0][field] = replacement
    atomic_write_json(resolve_task_path(repository, "TASK-0001", "approvals.json"), approvals)
    task_directory = repository / ".ai" / "tasks" / "TASK-0001"
    before = {path: path.read_bytes() for path in task_directory.rglob("*") if path.is_file()}

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    error = capsys.readouterr().err
    if replacement is None and field in {"policy_sha256", "spec_sha256"}:
        assert field in error
    else:
        assert "Required specification approval is missing or stale" in error
    after = {path: path.read_bytes() for path in task_directory.rglob("*") if path.is_file()}
    assert after == before


@pytest.mark.parametrize("valid_first", [False, True])
def test_begin_accepts_current_approval_among_stale_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    valid_first: bool,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW", valid_approval=True)
    valid = read_task_json(repository, "TASK-0001", "approvals.json")[0]
    stale = dict(valid, base_commit="0" * 40)
    approvals = [valid, stale] if valid_first else [stale, valid]
    path = resolve_task_path(repository, "TASK-0001", "approvals.json")
    atomic_write_json(path, approvals)
    before = path.read_bytes()

    assert summarize_task(repository, "TASK-0001").approvals == "current"
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("approve_second", [False, True])
def test_begin_requires_approval_for_each_review_unit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    approve_second: bool,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    task = load_task_record(repository, "TASK-0001").task
    second = deepcopy(task["decision_units"][0])
    second["decision_unit_id"] = "DU-002"
    task["decision_units"].append(second)
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    make_ready(repository, route="REVIEW", valid_approval=True)
    current_classification = read_task_json(repository, "TASK-0001", "classification.json")
    second_classification = deepcopy(current_classification["classifications"][0])
    second_classification["decision_unit_id"] = "DU-002"
    current_classification["classifications"].append(second_classification)
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"),
        current_classification,
    )
    if approve_second:
        approvals = read_task_json(repository, "TASK-0001", "approvals.json")
        approvals.append(dict(approvals[0], decision_unit_id="DU-002"))
        atomic_write_json(resolve_task_path(repository, "TASK-0001", "approvals.json"), approvals)
    before = load_task_record(repository, "TASK-0001")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == (0 if approve_second else 1)
    after = load_task_record(repository, "TASK-0001")
    if approve_second:
        assert after.task["current_state"] == "IMPLEMENTING"
        assert after.events[-1]["event_type"] == "implementation_started"
    else:
        assert "Required specification approval is missing or stale" in capsys.readouterr().err
        assert after == before


def test_begin_rejects_missing_frozen_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, freeze_spec=False)

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "frozen" in capsys.readouterr().err.lower()


def test_begin_rejects_missing_review_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "approval" in capsys.readouterr().err.lower()


def test_begin_rejects_business_worktree_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    (repository / "tracked.txt").write_text("changed after start\n", encoding="utf-8")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "git context" in capsys.readouterr().err.lower()


def test_begin_accepts_current_task_governance_only_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW", valid_approval=True)
    commit_all(repository, "record current task governance")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0

    record = load_task_record(repository, "TASK-0001")
    assert record.task["subject_commit"] != run_git(repository, "rev-parse", "HEAD")
    assert record.task["current_state"] == "IMPLEMENTING"


@pytest.mark.parametrize("drift", ["business", "other-task-governance"])
def test_begin_rejects_non_current_task_commits_after_subject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    drift: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="REVIEW", valid_approval=True)
    if drift == "business":
        (repository / "tracked.txt").write_text("committed business drift\n", encoding="utf-8")
    else:
        other = repository / ".ai" / "tasks" / "TASK-9999"
        other.mkdir(parents=True)
        (other / "note.txt").write_text("other task\n", encoding="utf-8")
    commit_all(repository, "commit non-governance drift")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "git context" in capsys.readouterr().err.lower()


def test_failed_retry_requires_reason_and_records_normal_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    make_failed(repository, {"summary": "tests failed"})

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "reason" in capsys.readouterr().err.lower()
    assert (
        main(
            [
                "begin",
                "TASK-0001",
                "--actor",
                "implementer",
                "--reason",
                "Fix the failing test",
            ]
        )
        == 0
    )

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "IMPLEMENTING"
    assert record.events[-1]["event_type"] == "implementation_retried"
    assert record.events[-1]["payload"]["reason"] == "Fix the failing test"


@pytest.mark.parametrize(
    "marker",
    [
        "scope_expanded",
        "new_dependencies",
        "new_permissions",
        "unverifiable",
        "high_risk_side_effects",
    ],
)
def test_risky_failure_requires_escalation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    marker: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    make_failed(repository, {marker: True})

    assert main(["begin", "TASK-0001", "--actor", "implementer", "--reason", "retry"]) == 1
    assert "escalat" in capsys.readouterr().err.lower()


def test_close_rejects_early_state_and_unknown_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)

    close = [
        "close",
        "TASK-0001",
        "--result",
        "merged",
        "--merge-commit",
        "0" * 40,
        "--actor",
        "closer",
    ]
    assert main(close) == 1
    capsys.readouterr()

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    make_approved(repository)
    assert main(close) == 1
    assert "commit" in capsys.readouterr().err.lower()


def test_close_records_existing_merge_without_running_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    make_approved(repository)
    head = run_git(repository, "rev-parse", "HEAD")
    branch_before = run_git(repository, "branch", "--show-current")

    assert (
        main(
            [
                "close",
                "TASK-0001",
                "--result",
                "merged",
                "--merge-commit",
                head,
                "--actor",
                "closer",
            ]
        )
        == 0
    )

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "MERGED"
    assert record.events[-1]["payload"] == {"merge_commit": head, "result": "merged"}
    assert run_git(repository, "rev-parse", "HEAD") == head
    assert run_git(repository, "branch", "--show-current") == branch_before


def test_classify_records_durable_evidence_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    task = load_task_record(repository, "TASK-0001").task
    task["decision_units"][0].update(impact_categories=[], controlled_actions=[])
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    first = load_task_record(repository, "TASK-0001")
    assert first.task["current_state"] == "BLOCKED"
    assert (repository / ".ai" / "tasks" / "TASK-0001" / "classification.json").is_file()
    event_count = len(first.events)

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert len(load_task_record(repository, "TASK-0001").events) == event_count


@pytest.mark.parametrize("command", ["begin", "close", "classify"])
def test_command_help_is_available(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main([command, "--help"])

    assert caught.value.code == 0
    assert "--actor" in capsys.readouterr().out


@pytest.mark.parametrize("failure_kind", ["os_error", "interrupt", "timeout"])
def test_fixture_command_preserves_spawned_failure_and_bounded_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_kind: str
) -> None:
    from types import SimpleNamespace

    argv = ["fixture-command", "literal argument"]
    original = {
        "os_error": OSError("synthetic fixture failure"),
        "interrupt": KeyboardInterrupt("synthetic fixture interruption"),
        "timeout": subprocess.TimeoutExpired(argv, 10),
    }[failure_kind]
    original_args = original.args
    events: list[object] = []
    spawns: list[tuple[list[str], dict[str, object]]] = []

    class Process:
        pid = 123
        returncode: int | None = None

        def __init__(self, helper: bool) -> None:
            self.helper = helper
            self.stdout = SimpleNamespace(close=lambda: events.append("close_stdout"))
            self.stderr = SimpleNamespace(close=lambda: events.append("close_stderr"))

        def poll(self) -> int | None:
            return self.returncode

        def kill(self) -> None:
            events.append("helper_kill" if self.helper else "direct_kill")
            self.returncode = -9

        def wait(self, *, timeout: int) -> int:
            events.append(("helper_wait" if self.helper else "direct_wait", timeout))
            self.returncode = 0 if self.helper else -9
            return self.returncode

        def communicate(self, *, timeout: int) -> tuple[str, str]:
            events.append(("communicate", timeout))
            if timeout == 10:
                raise original
            return "stdout-π\r\n", "stderr-ß"

    direct, helper = Process(False), Process(True)

    def spawn(command: list[str], **options: object) -> Process:
        spawns.append((command, options))
        return direct if len(spawns) == 1 else helper

    def forbidden_run(*args: object, **options: object) -> None:
        raise AssertionError("Cleanup must retain its Popen directly")

    with monkeypatch.context() as scoped:
        scoped.setattr(
            sys.modules[__name__],
            "os",
            SimpleNamespace(name="nt", environ={"SystemRoot": "C:/Windows"}),
        )
        scoped.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
        scoped.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
        scoped.setattr(subprocess, "Popen", spawn)
        scoped.setattr(subprocess, "run", forbidden_run)
        with pytest.raises(type(original)) as caught:
            _run_fixture_command(tmp_path, argv)
    assert caught.value is original and caught.value.args == original_args
    if isinstance(original, subprocess.TimeoutExpired):
        assert original.output == "stdout-π\r\n" and original.stderr == "stderr-ß"
    assert spawns[0] == (
        argv,
        {
            "cwd": tmp_path,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "encoding": "utf-8",
            "start_new_session": False,
            "creationflags": 512,
        },
    )
    assert spawns[1][0][1:] == ["/PID", "123", "/T", "/F"]
    assert spawns[1][1] == {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "creationflags": 0x08000000,
    }
    assert events == [
        ("communicate", 10),
        ("helper_wait", 5),
        "direct_kill",
        ("direct_wait", 5),
        ("communicate", 5),
        "close_stdout",
        "close_stderr",
    ]


@pytest.mark.parametrize("helper_failure", ["spawn", "wait"])
def test_fixture_command_secondary_cleanup_failures_preserve_first_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, helper_failure: str
) -> None:
    from types import SimpleNamespace

    original = OSError("first synthetic exception")
    original_args = original.args
    events: list[object] = []
    spawns = 0

    class Process:
        pid = 456
        returncode = None

        def __init__(self, helper: bool) -> None:
            self.helper = helper
            self.stdout = SimpleNamespace(close=lambda: events.append("forbidden_close"))
            self.stderr = SimpleNamespace(close=lambda: events.append("forbidden_close"))

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            events.append("helper_kill" if self.helper else "direct_kill")
            raise RuntimeError("secondary kill exception")

        def wait(self, *, timeout: int) -> int:
            events.append(("helper_wait" if self.helper else "direct_wait", timeout))
            raise KeyboardInterrupt("secondary wait exception")

        def communicate(self, *, timeout: int) -> tuple[str, str]:
            events.append(("communicate", timeout))
            if timeout == 10:
                raise original
            raise subprocess.TimeoutExpired("secondary drain", timeout)

    direct, helper = Process(False), Process(True)

    def spawn(command: list[str], **options: object) -> Process:
        nonlocal spawns
        spawns += 1
        if spawns == 1:
            return direct
        events.append("helper_spawn")
        if helper_failure == "spawn":
            raise OSError("secondary helper spawn exception")
        return helper

    with monkeypatch.context() as scoped:
        scoped.setattr(
            sys.modules[__name__],
            "os",
            SimpleNamespace(name="nt", environ={"SystemRoot": "C:/Windows"}),
        )
        scoped.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
        scoped.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
        scoped.setattr(subprocess, "Popen", spawn)
        with pytest.raises(OSError) as caught:
            _run_fixture_command(tmp_path, ["fixture-command"])
    assert caught.value is original and caught.value.args == original_args
    expected: list[object] = [("communicate", 10), "helper_spawn"]
    if helper_failure == "wait":
        expected += [("helper_wait", 5), "helper_kill", ("helper_wait", 1)]
    assert events == expected + ["direct_kill", ("direct_wait", 5), ("communicate", 5)]


def test_fixture_command_completed_nonzero_does_not_run_process_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    argv = ["fixture-command", "literal argument"]
    events: list[object] = []

    def communicate(*, timeout: int) -> tuple[str, str]:
        events.append(("communicate", timeout))
        return "stdout-π\r\n", "stderr-ß"

    def forbidden(*args: object, **options: object) -> None:
        raise AssertionError("Completed command must not be killed or drained again")

    process = SimpleNamespace(
        returncode=7,
        communicate=communicate,
        stdout=SimpleNamespace(close=lambda: events.append("close_stdout")),
        stderr=SimpleNamespace(close=lambda: events.append("close_stderr")),
        kill=forbidden,
        wait=forbidden,
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(sys.modules[__name__], "os", SimpleNamespace(name="posix", killpg=forbidden))
        scoped.setattr(sys.modules[__name__], "_cleanup_fixture_process", forbidden)
        scoped.setattr(subprocess, "Popen", lambda *args, **options: process)
        with pytest.raises(subprocess.CalledProcessError) as caught:
            _run_fixture_command(tmp_path, argv)
    assert caught.value.returncode == 7 and caught.value.cmd == argv
    assert caught.value.output == "stdout-π\r\n" and caught.value.stderr == "stderr-ß"
    assert caught.value.args == (7, argv)
    assert events == [("communicate", 10), "close_stdout", "close_stderr"]


def test_fixture_command_interrupt_reaps_real_retained_direct_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    original = KeyboardInterrupt("synthetic after-spawn interrupt")
    original_args = original.args
    ready, stop = tmp_path / "ready.pid", tmp_path / "stop"
    script = (
        "import os, pathlib, sys, time; "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); "
        "stop = pathlib.Path(sys.argv[2]); "
        "exec('while not stop.exists():\\n time.sleep(0.01)')"
    )
    # A Windows venv executable can launch a different engine PID.
    base_executable = getattr(sys, "_base_executable", None)
    assert isinstance(base_executable, str) and Path(base_executable).is_file(), (
        "The actual CPython base executable is required for retained child identity"
    )
    argv = [base_executable, "-c", script, str(ready), str(stop)]
    real_popen = subprocess.Popen
    owned: list[subprocess.Popen[str]] = []
    real_communicate: list[Any] = []
    before_identity: list[tuple[int, int | None]] = []
    communicate_timeouts: list[int] = []

    def identity(process: subprocess.Popen[str]) -> tuple[int, int | None]:
        if os.name != "nt":
            return process.pid, None  # Native creation time is not claimed on POSIX.
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetProcessId.argtypes = [wintypes.HANDLE]
        kernel.GetProcessId.restype = wintypes.DWORD
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
            ctypes.POINTER(wintypes.FILETIME)
        ] * 4
        kernel.GetProcessTimes.restype = wintypes.BOOL
        handle = wintypes.HANDLE(int(process._handle))
        created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        assert kernel.GetProcessId(handle) == process.pid
        assert kernel.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        )
        return process.pid, (created.dwHighDateTime << 32) | created.dwLowDateTime

    def spawn(command: list[str], **options: Any) -> subprocess.Popen[str]:
        process = real_popen(command, **options)
        if command == argv:
            owned.append(process)  # Test finally retains ownership before any identity assertion.
            real_communicate.append(process.communicate)
            before_identity.append(identity(process))

            def communicate(*, timeout: int) -> tuple[str, str]:
                communicate_timeouts.append(timeout)
                if timeout == 10:
                    deadline = time.monotonic() + 5
                    while not ready.exists() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    assert ready.exists()
                    raise original
                return real_communicate[0](timeout=timeout)

            monkeypatch.setattr(process, "communicate", communicate)
        return process

    try:
        monkeypatch.setattr(subprocess, "Popen", spawn)
        with pytest.raises(KeyboardInterrupt) as caught:
            _run_fixture_command(tmp_path, argv)
        assert caught.value is original and caught.value.args == original_args
        assert len(owned) == len(before_identity) == 1
        process = owned[0]
        assert int(ready.read_text()) == process.pid
        assert identity(process) == before_identity[0]
        # These terminal assertions precede the test's fallback cleanup.
        assert process.poll() is not None
        assert process.wait(timeout=0) == process.returncode
        assert communicate_timeouts == [10, 5]
    finally:
        stop.write_text("stop")
        for index, process in enumerate(owned):
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            if any(
                stream is not None and not stream.closed
                for stream in (process.stdout, process.stderr)
            ):
                real_communicate[index](timeout=5)


def test_fixture_command_reaped_decode_failure_does_not_signal_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    original = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
    original_args = original.args
    group_signals: list[tuple[int, int]] = []
    communicate_timeouts: list[int] = []
    wait_timeouts: list[int] = []

    def communicate(*, timeout: int) -> tuple[str, str]:
        communicate_timeouts.append(timeout)
        # POSIX communicate waits/reaps before its final UTF-8 decoding step.
        raise original

    def wait(*, timeout: int) -> int:
        wait_timeouts.append(timeout)
        return 0

    process = SimpleNamespace(
        pid=789,
        returncode=0,
        poll=lambda: 0,
        kill=lambda: None,  # A retained Popen with a known returncode sends no new signal.
        wait=wait,
        communicate=communicate,
        stdout=None,
        stderr=None,
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            sys.modules[__name__],
            "os",
            SimpleNamespace(name="posix", killpg=lambda pid, sig: group_signals.append((pid, sig))),
        )
        scoped.setattr(subprocess, "Popen", lambda *args, **options: process)
        with pytest.raises(UnicodeDecodeError) as caught:
            _run_fixture_command(tmp_path, ["fixture-command"])
    assert caught.value is original and caught.value.args == original_args
    assert group_signals == []
    assert communicate_timeouts == [10, 5] and wait_timeouts == [5]
