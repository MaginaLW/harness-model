"""Integration tests for the governed read-only `aiflow list` command."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from aiflow.cli import main
from aiflow.storage import resolve_task_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"


def _run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    return result.stdout.rstrip("\r\n")


def _create_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _run_git(path, "init", "-b", "main")
    ai_root = path / ".ai"
    ai_root.mkdir()
    for folder in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / folder, ai_root / folder)
    (ai_root / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _run_git(path, "add", ".ai", "tracked.txt")
    _run_git(
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


def _snapshot(root: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def _create_merged_task(repository: Path, task_id: str) -> None:
    assert main(["start", "--objective", f"Task {task_id}", "--allow", "tracked.txt"]) == 0
    _run_git(repository, "switch", "-c", "feature/list-merge")
    (repository / "tracked.txt").write_text("feature\n", encoding="utf-8")
    _run_git(repository, "add", "tracked.txt")
    _run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "feature commit",
    )
    feature_head = _run_git(repository, "rev-parse", "HEAD")
    _run_git(repository, "switch", "main")
    _run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "merge",
        "--no-ff",
        "feature/list-merge",
        "-m",
        "merge feature",
    )
    merge_commit = _run_git(repository, "rev-parse", "HEAD")

    task_yaml = resolve_task_path(repository, task_id, "task.yaml")
    events_path = resolve_task_path(repository, task_id, "events.jsonl")
    events = [
        json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line
    ]
    from aiflow.state import create_transition_event
    from aiflow.storage import atomic_write_yaml, read_task_yaml

    task = read_task_yaml(repository, task_id, "task.yaml")
    task["subject_commit"] = feature_head
    transitions = [
        ("CLASSIFIED", "classification_recorded", {"classification_available"}, {}),
        ("READY_TO_IMPLEMENT", "implementation_ready", {"classification_route_selected"}, {}),
        ("IMPLEMENTING", "implementation_started", {"readiness_satisfied"}, {}),
        ("VERIFYING", "verification_started", {"implementation_complete"}, {}),
        ("VERIFIED", "verification_passed", {"verification_passed"}, {}),
        ("APPROVED_FOR_MERGE", "merge_approved_automatically", {"final_review_not_required"}, {}),
        (
            "MERGED",
            "merge_recorded",
            {"merge_commit_verified"},
            {"result": "merged", "merge_commit": merge_commit},
        ),
    ]
    for target_state, event_type, preconditions, payload in transitions:
        event = create_transition_event(
            task,
            target_state=target_state,
            event_type=event_type,
            actor="tester",
            payload=payload,
            sequence=len(events) + 1,
            satisfied_preconditions=preconditions,
        )
        events.append(event)
        task["current_state"] = target_state
        task["updated_at"] = event["occurred_at"]
    atomic_write_yaml(task_yaml, task)
    events_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in events),
        encoding="utf-8",
    )


def test_list_command_zero_writes_filters_subdir_and_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _create_repo(tmp_path / "repo")
    monkeypatch.chdir(repository)

    _create_merged_task(repository, "TASK-0001")
    assert main(["start", "--objective", "Active new task", "--allow", "tracked.txt"]) == 0

    (repository / ".ai" / "tasks" / "TASK-0003").mkdir()
    (repository / ".ai" / "tasks" / "TASK-0003" / "creation_failed.json").write_text(
        json.dumps({"status": "creation_failed", "task_id": "TASK-0003"}),
        encoding="utf-8",
    )
    (repository / ".ai" / "tasks" / "TASK-0165" / "logs").mkdir(parents=True)
    (repository / ".ai" / "tasks" / "TASK-0165" / "logs" / "run.log").write_text(
        "runtime\n", encoding="utf-8"
    )
    _run_git(repository, "add", ".ai/tasks/TASK-0001", ".ai/tasks/TASK-0002")
    _run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "track tasks",
    )
    capsys.readouterr()

    before = _snapshot(repository / ".ai")
    assert main(["list", "--format", "json"]) == 0
    default_payload = json.loads(capsys.readouterr().out)
    assert [item["task_id"] for item in default_payload["tasks"]] == ["TASK-0002"]
    assert default_payload["counts_by_state"] == {"MERGED": 1, "NEW": 1}
    assert default_payload["incomplete_tasks"] == ["TASK-0003"]
    assert default_payload["logs_only_tasks"] == ["TASK-0165"]

    assert main(["list", "--all", "--format", "json"]) == 0
    all_payload = json.loads(capsys.readouterr().out)
    assert [item["task_id"] for item in all_payload["tasks"]] == ["TASK-0001", "TASK-0002"]

    assert main(["list", "--state", "MERGED", "--format", "json"]) == 0
    merged_payload = json.loads(capsys.readouterr().out)
    assert [item["task_id"] for item in merged_payload["tasks"]] == ["TASK-0001"]

    assert main(["list"]) == 0
    assert "TASK-0002 [NEW]" in capsys.readouterr().out

    subdir = repository / "nested" / "dir"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)
    monkeypatch.setattr(os, "chdir", lambda *_args: pytest.fail("CLI must never chdir"))
    assert main(["list", "--all", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == all_payload
    assert Path.cwd() == subdir
    monkeypatch.undo()

    worktree_dir = tmp_path / "wt"
    _run_git(repository, "worktree", "add", "-b", "wt-branch", str(worktree_dir))
    monkeypatch.chdir(worktree_dir)
    assert main(["list", "--all", "--format", "json"]) == 0
    wt_payload = json.loads(capsys.readouterr().out)
    assert wt_payload["tasks"] == all_payload["tasks"]
    assert wt_payload["counts_by_state"] == all_payload["counts_by_state"]
    assert _snapshot(repository / ".ai") == before


def test_list_command_fails_closed_on_corrupt_or_pending_task_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _create_repo(tmp_path / "repo")
    monkeypatch.chdir(repository)
    assert main(["start", "--objective", "Pending task", "--allow", "tracked.txt"]) == 0
    (repository / ".ai" / "tasks" / "TASK-0001" / "task.yaml.next").write_text(
        "pending: true\n", encoding="utf-8"
    )
    capsys.readouterr()

    before = _snapshot(repository / ".ai")
    assert main(["list", "--format", "json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["code"] == "STATE_MATERIALIZATION_MISMATCH"
    assert _snapshot(repository / ".ai") == before


def test_list_command_real_repository_smoke(tmp_path: Path) -> None:
    del tmp_path
    result = subprocess.run(
        [sys.executable, "-m", "aiflow", "list", "--all", "--format", "json"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "aiflow-task-list"
    assert payload["include_merged"] is True
    assert payload["total_tasks"] >= 2
    by_id = {item["task_id"]: item for item in payload["tasks"]}
    assert by_id["TASK-0194"]["current_state"] == "MERGED"
    assert by_id["TASK-0196"]["current_state"] == "MERGED"
