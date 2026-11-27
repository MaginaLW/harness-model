"""Unit tests for strictly read-only task listing and CLI error contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiflow import cli, status_service
from aiflow.errors import ContractError, StateTransitionError, StorageError
from aiflow.state import ALL_STATES
from aiflow.status_service import TaskListEntry, TaskListReport, list_tasks
from aiflow.task_service import TaskRecord

REPO_ID = "123e4567-e89b-42d3-a456-426614174000"


def _init_ai(root: Path) -> Path:
    ai_dir = root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)
    return ai_dir


def _make_task(
    task_id: str,
    *,
    state: str = "NEW",
    goal: str = "Bounded task",
    branch: str = "codex/sample",
) -> TaskRecord:
    return TaskRecord(
        task={
            "schema_version": "1.0",
            "task_id": task_id,
            "current_state": state,
            "goal": goal,
            "branch": branch,
            "created_at": "2026-11-27T10:00:00Z",
            "updated_at": "2026-11-27T10:05:00Z",
        },
        events=(),
    )


def _patch_repo(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    records: dict[str, TaskRecord] | None = None,
) -> None:
    monkeypatch.setattr(
        status_service,
        "collect_git_context",
        lambda _path: SimpleNamespace(repository_id=REPO_ID),
    )
    if records is not None:

        def _fake_strict(_repo: Path, task_id: str) -> TaskRecord:
            return records[task_id]

        monkeypatch.setattr(status_service, "read_task_record_strict", _fake_strict)


def test_list_tasks_when_tasks_directory_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_ai(tmp_path)
    _patch_repo(monkeypatch, tmp_path)

    report = list_tasks(tmp_path)

    assert report == TaskListReport(
        repository_id=REPO_ID,
        include_merged=False,
        states=(),
        counts_by_state={},
        tasks=(),
        incomplete_tasks=(),
        logs_only_tasks=(),
    )
    payload = json.loads(report.to_json())
    assert payload == {
        "schema_version": "1.0",
        "kind": "aiflow-task-list",
        "repository_id": REPO_ID,
        "include_merged": False,
        "states": [],
        "total_tasks": 0,
        "matched_tasks": 0,
        "counts_by_state": {},
        "tasks": [],
        "incomplete_tasks": [],
        "logs_only_tasks": [],
    }
    text = report.to_text()
    assert f"Repository: {REPO_ID}" in text
    assert "Tasks: 0 shown (0 total)" in text
    assert "Counts by state: none" in text
    assert "No matching tasks." in text


def test_list_tasks_filters_states_and_handles_special_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = _init_ai(tmp_path) / "tasks"
    tasks_root.mkdir()
    (tasks_root / "README.md").write_text("ignored\n", encoding="utf-8")
    (tasks_root / "notes").mkdir()

    records: dict[str, TaskRecord] = {}
    for task_id, state in (
        ("TASK-0001", "MERGED"),
        ("TASK-0002", "NEW"),
        ("TASK-0003", "BLOCKED"),
        ("TASK-0004", "IMPLEMENTING"),
    ):
        task_dir = tasks_root / task_id
        task_dir.mkdir()
        (task_dir / "task.yaml").write_text("placeholder\n", encoding="utf-8")
        records[task_id] = _make_task(task_id, state=state, goal=f"Goal {task_id}")

    failed_dir = tasks_root / "TASK-0005"
    failed_dir.mkdir()
    (failed_dir / "creation_failed.json").write_text(
        json.dumps({"status": "creation_failed", "task_id": "TASK-0005"}),
        encoding="utf-8",
    )

    empty_dir = tasks_root / "TASK-0006"
    empty_dir.mkdir()

    logs_dir = tasks_root / "TASK-0165" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "run-1.log").write_text("log\n", encoding="utf-8")

    _patch_repo(monkeypatch, tmp_path, records)

    default_report = list_tasks(tmp_path)
    assert [entry.task_id for entry in default_report.tasks] == [
        "TASK-0002",
        "TASK-0003",
        "TASK-0004",
    ]
    assert default_report.counts_by_state == {
        "BLOCKED": 1,
        "IMPLEMENTING": 1,
        "MERGED": 1,
        "NEW": 1,
    }
    assert default_report.incomplete_tasks == ("TASK-0005",)
    assert default_report.logs_only_tasks == ("TASK-0006", "TASK-0165")

    all_report = list_tasks(tmp_path, include_merged=True)
    assert [entry.task_id for entry in all_report.tasks] == [
        "TASK-0001",
        "TASK-0002",
        "TASK-0003",
        "TASK-0004",
    ]

    filtered_report = list_tasks(tmp_path, states=["MERGED", "NEW", "MERGED"])
    assert filtered_report.states == ("MERGED", "NEW")
    assert [entry.task_id for entry in filtered_report.tasks] == ["TASK-0001", "TASK-0002"]
    assert filtered_report.counts_by_state == default_report.counts_by_state

    empty_filter_report = list_tasks(tmp_path, states=[])
    assert [entry.task_id for entry in empty_filter_report.tasks] == [
        "TASK-0002",
        "TASK-0003",
        "TASK-0004",
    ]

    text = all_report.to_text()
    assert "Tasks: 4 shown (4 total)" in text
    assert "- TASK-0001 [MERGED] (codex/sample) Goal TASK-0001" in text
    assert "Incomplete tasks: TASK-0005" in text
    assert "Logs-only tasks: TASK-0006, TASK-0165" in text


@pytest.mark.parametrize("state", sorted(ALL_STATES))
def test_list_tasks_accepts_every_canonical_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    tasks_root = _init_ai(tmp_path) / "tasks"
    task_dir = tasks_root / "TASK-0010"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text("placeholder\n", encoding="utf-8")
    _patch_repo(monkeypatch, tmp_path, {"TASK-0010": _make_task("TASK-0010", state=state)})

    report = list_tasks(tmp_path, states=[state])

    assert report.tasks == (
        TaskListEntry(
            task_id="TASK-0010",
            current_state=state,
            goal="Bounded task",
            branch="codex/sample",
            created_at="2026-11-27T10:00:00Z",
            updated_at="2026-11-27T10:05:00Z",
        ),
    )


@pytest.mark.parametrize(
    ("states", "include_merged"),
    [
        (["UNKNOWN"], False),
        ("NEW", False),
        (["NEW"], True),
    ],
)
def test_list_tasks_rejects_invalid_filter_combinations(
    tmp_path: Path, states: object, include_merged: bool
) -> None:
    with pytest.raises(ContractError) as caught:
        list_tasks(tmp_path, states=states, include_merged=include_merged)  # type: ignore[arg-type]
    assert caught.value.code == "TASK_LIST_FILTER_INVALID"


def test_list_tasks_fails_closed_on_unexpected_files_and_bad_creation_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = _init_ai(tmp_path) / "tasks"
    _patch_repo(monkeypatch, tmp_path)

    unexpected = tasks_root / "TASK-0020"
    unexpected.mkdir(parents=True)
    (unexpected / "stray.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(StorageError) as caught:
        list_tasks(tmp_path)
    assert caught.value.code == "STORAGE_READ_FAILED"

    unexpected.joinpath("stray.txt").unlink()
    unexpected.joinpath("logs").write_text("not a directory\n", encoding="utf-8")
    with pytest.raises(StorageError) as caught_logs:
        list_tasks(tmp_path)
    assert caught_logs.value.code == "STORAGE_READ_FAILED"

    unexpected.joinpath("logs").unlink()
    unexpected.joinpath("creation_failed.json").write_text("[]", encoding="utf-8")
    with pytest.raises(StorageError) as caught_marker:
        list_tasks(tmp_path)
    assert caught_marker.value.code == "STORAGE_PARSE_FAILED"


def test_list_tasks_rejects_non_dir_tasks_root_and_task_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ai_dir = _init_ai(tmp_path)
    _patch_repo(monkeypatch, tmp_path)
    (ai_dir / "tasks").write_text("not a dir\n", encoding="utf-8")
    with pytest.raises(StorageError) as caught_root:
        list_tasks(tmp_path)
    assert caught_root.value.code == "STORAGE_READ_FAILED"

    (ai_dir / "tasks").unlink()
    (ai_dir / "tasks").mkdir()
    (ai_dir / "tasks" / "TASK-0030").write_text("not a dir\n", encoding="utf-8")
    with pytest.raises(StorageError) as caught_entry:
        list_tasks(tmp_path)
    assert caught_entry.value.code == "STORAGE_READ_FAILED"


def test_list_tasks_rejects_reparse_points_and_os_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = _init_ai(tmp_path) / "tasks"
    task_dir = tasks_root / "TASK-0040"
    task_dir.mkdir(parents=True)
    marker = task_dir / "creation_failed.json"
    marker.write_text("{}", encoding="utf-8")
    _patch_repo(monkeypatch, tmp_path)

    original_lstat = Path.lstat

    def _reparse_lstat(self: Path) -> os.stat_result:
        result = original_lstat(self)
        if self == marker:
            return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)  # type: ignore[return-value]
        return result

    monkeypatch.setattr(Path, "lstat", _reparse_lstat)
    with pytest.raises(StorageError) as caught:
        list_tasks(tmp_path)
    assert caught.value.code == "STORAGE_READ_FAILED"

    monkeypatch.undo()
    _patch_repo(monkeypatch, tmp_path)

    monkeypatch.setattr(Path, "iterdir", lambda self: (_ for _ in ()).throw(OSError("denied")))
    with pytest.raises(StorageError) as caught_iter:
        list_tasks(tmp_path)
    assert caught_iter.value.code == "STORAGE_READ_FAILED"


def test_list_tasks_propagates_strict_task_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = _init_ai(tmp_path) / "tasks"
    task_dir = tasks_root / "TASK-0050"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml.next").write_text("pending\n", encoding="utf-8")
    _patch_repo(monkeypatch, tmp_path)

    def _fail_strict(_repo: Path, _task_id: str) -> TaskRecord:
        raise StateTransitionError(
            "Task has a pending materialized replacement",
            code="STATE_MATERIALIZATION_MISMATCH",
        )

    monkeypatch.setattr(status_service, "read_task_record_strict", _fail_strict)
    with pytest.raises(StateTransitionError) as caught:
        list_tasks(tmp_path)
    assert caught.value.code == "STATE_MATERIALIZATION_MISMATCH"


def test_list_cli_dispatch_help_and_json_error_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = TaskListReport(
        repository_id=REPO_ID,
        include_merged=True,
        states=(),
        counts_by_state={"NEW": 1},
        tasks=(
            TaskListEntry(
                task_id="TASK-0001",
                current_state="NEW",
                goal="Sample 中文 🎯",
                branch="main",
                created_at="2026-11-27T10:00:00Z",
                updated_at="2026-11-27T10:00:00Z",
            ),
        ),
        incomplete_tasks=(),
        logs_only_tasks=(),
    )
    assert report.to_json().isascii()
    assert json.loads(report.to_json())["tasks"][0]["goal"] == "Sample 中文 🎯"
    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)
    monkeypatch.setattr(cli, "list_tasks", lambda *_args, **_kwargs: report)

    assert cli.main(["list", "--all", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == report.to_dict()
    assert captured.err == ""

    assert cli.main(["list"]) == 0
    text_out = capsys.readouterr()
    assert text_out.out == report.to_text() + "\n"
    assert text_out.err == ""

    with pytest.raises(SystemExit) as help_exit:
        cli.main(["list", "--help"])
    assert help_exit.value.code == 0
    assert "--all" in capsys.readouterr().out

    for bad_args in (["list", "--all", "--state", "NEW"], ["list", "--state", "BOGUS"]):
        with pytest.raises(SystemExit) as bad_exit:
            cli.main(bad_args)
        assert bad_exit.value.code == 2
        bad_captured = capsys.readouterr()
        assert bad_captured.out == ""
        assert "usage:" in bad_captured.err

    def _fail_list(*_args: object, **_kwargs: object) -> TaskListReport:
        raise StorageError(
            "Task directory is incomplete or contains unexpected entries",
            code="STORAGE_READ_FAILED",
            details={"secret": "private-marker"},
        )

    monkeypatch.setattr(cli, "list_tasks", _fail_list)
    assert cli.main(["list", "--format", "json"]) == 1
    err_captured = capsys.readouterr()
    assert err_captured.out == ""
    assert json.loads(err_captured.err) == {
        "code": "STORAGE_READ_FAILED",
        "message": "Task directory is incomplete or contains unexpected entries",
    }
    assert "private-marker" not in err_captured.err
    assert "Traceback" not in err_captured.err
