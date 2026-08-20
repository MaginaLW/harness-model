"""AUTO begin preflight integration tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from aiflow.cli import main
from aiflow.storage import atomic_write_yaml, resolve_task_path
from aiflow.task_service import load_task_record
from tests.integration.test_begin_close_commands import make_ready, start

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=True,
        encoding="utf-8",
        timeout=10,
    )
    return result.stdout.rstrip("\r\n")


def create_repository(path: Path) -> Path:
    path.mkdir()
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


def prepare_auto(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    dirty_path: str | None = None,
) -> None:
    if dirty_path is not None:
        path = repository / dirty_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pending\n", encoding="utf-8")
    start(repository, monkeypatch)
    make_ready(repository)
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "READY_TO_IMPLEMENT"


def test_auto_begin_accepts_changed_path_in_declared_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    prepare_auto(repository, monkeypatch, dirty_path="src/module.py")

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "IMPLEMENTING"


@pytest.mark.parametrize("dirty_path", ["outside.txt", "SRC/module.py"])
def test_auto_begin_rejects_baseline_path_outside_task_or_unit_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    dirty_path: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    prepare_auto(repository, monkeypatch, dirty_path=dirty_path)
    capsys.readouterr()

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "AUTO preflight" in capsys.readouterr().err
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "READY_TO_IMPLEMENT"


def test_auto_begin_rejects_decision_facts_changed_after_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    prepare_auto(repository, monkeypatch)
    task = load_task_record(repository, "TASK-0001").task
    task["decision_units"][0]["planned_actions"] = ["changed after classification"]
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    capsys.readouterr()

    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "CLASSIFICATION_STALE" in capsys.readouterr().err
