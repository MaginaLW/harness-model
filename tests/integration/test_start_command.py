"""Integration tests for the ``aiflow start`` command."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from aiflow import task_service
from aiflow.cli import main
from aiflow.contracts import require_valid_contract
from aiflow.errors import StorageError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"
DEFAULT_FORBIDDEN = {
    "push",
    "merge",
    "deploy",
    "delete",
    "secret_export",
    "paid_external_call",
}


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
    shutil.copytree(PROJECT_ROOT / ".ai" / "schemas", ai_root / "schemas")
    shutil.copytree(PROJECT_ROOT / ".ai" / "policy", ai_root / "policy")
    shutil.copytree(PROJECT_ROOT / ".ai" / "templates", ai_root / "templates")
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


def load_task(repository: Path, task_id: str = "TASK-0001") -> dict[str, object]:
    value = yaml.safe_load(
        (repository / ".ai" / "tasks" / task_id / "task.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_start_creates_complete_contract_valid_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    monkeypatch.chdir(repository)
    expected_head = run_git(repository, "rev-parse", "HEAD")

    assert (
        main(
            [
                "start",
                "--objective",
                "  Implement one bounded change  ",
                "--allow",
                "src/**",
                "--allow",
                "tests/**",
                "--forbid-action",
                "publish",
            ]
        )
        == 0
    )

    task_directory = repository / ".ai" / "tasks" / "TASK-0001"
    assert capsys.readouterr().out.splitlines() == ["TASK-0001", str(task_directory.resolve())]
    assert {path.name for path in task_directory.iterdir()} == {
        "task.yaml",
        "events.jsonl",
        "spec.md",
        "approvals.json",
    }

    task = load_task(repository)
    require_valid_contract("task", task)
    assert task["goal"] == "Implement one bounded change"
    assert task["base_commit"] == expected_head
    assert task["subject_commit"] == expected_head
    assert task["allowed_scope"] == ["src/**", "tests/**"]
    assert set(task["forbidden_actions"]) == DEFAULT_FORBIDDEN | {"publish"}
    assert task["current_state"] == "NEW"
    assert task["repository_path_at_creation"] == repository.resolve().as_posix()

    events = (task_directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(events) == 1
    event = json.loads(events[0])
    require_valid_contract("event", event)
    assert event["event_type"] == "task_created"
    assert event["from_state"] == event["to_state"] == "NEW"
    assert json.loads((task_directory / "approvals.json").read_text(encoding="utf-8")) == []
    assert (task_directory / "spec.md").read_text(encoding="utf-8") == (
        repository / ".ai" / "templates" / "spec.md"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "arguments",
    [
        ["start", "--objective", "   ", "--allow", "src/**"],
        ["start", "--objective", "bounded"],
        ["start", "--objective", "unbounded", "--allow", "**"],
    ],
)
def test_start_rejects_invalid_objective_or_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    monkeypatch.chdir(repository)

    assert main(arguments) == 1

    assert "Traceback" not in capsys.readouterr().err
    assert not (repository / ".ai" / "tasks").exists()


def test_start_rejects_non_git_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["start", "--objective", "bounded", "--allow", "src/**"]) == 1

    assert "Traceback" not in capsys.readouterr().err


def test_detached_head_requires_explicit_allow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "checkout", "--detach", "HEAD")
    monkeypatch.chdir(repository)
    arguments = ["start", "--objective", "bounded", "--allow", "src/**"]

    assert main(arguments) == 1
    assert "detached" in capsys.readouterr().err.lower()
    assert main([*arguments, "--allow-detached"]) == 0
    assert load_task(repository)["branch"] == "DETACHED"


def test_start_records_dirty_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
    monkeypatch.chdir(repository)

    assert main(["start", "--objective", "bounded", "--allow", "src/**"]) == 0

    task = load_task(repository)
    assert task["worktree_dirty"] is True
    assert task["worktree_dirty_paths"] == ["tracked.txt"]


def test_interrupted_creation_is_marked_and_recoverable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    monkeypatch.chdir(repository)
    original = task_service.atomic_write_text
    interrupted = False

    def interrupt_spec(target: Path, content: str) -> None:
        nonlocal interrupted
        if target.name == "spec.md" and not interrupted:
            interrupted = True
            raise StorageError("simulated interruption")
        original(target, content)

    monkeypatch.setattr(task_service, "atomic_write_text", interrupt_spec)

    assert main(["start", "--objective", "recover me", "--allow", "src/**"]) == 1
    assert "--recover TASK-0001" in capsys.readouterr().err
    task_directory = repository / ".ai" / "tasks" / "TASK-0001"
    assert (task_directory / "creation_failed.json").is_file()

    monkeypatch.setattr(task_service, "atomic_write_text", original)
    assert main(["start", "--recover", "TASK-0001"]) == 0
    assert not (task_directory / "creation_failed.json").exists()
    require_valid_contract("task", load_task(repository))

    assert main(["start", "--recover", "TASK-0001"]) == 1
    assert "not recoverable" in capsys.readouterr().err.lower()


def test_new_start_never_reuses_failed_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    monkeypatch.chdir(repository)
    original = task_service.atomic_write_text

    def interrupt_spec(target: Path, content: str) -> None:
        if target.name == "spec.md":
            raise StorageError("simulated interruption")
        original(target, content)

    monkeypatch.setattr(task_service, "atomic_write_text", interrupt_spec)
    assert main(["start", "--objective", "first", "--allow", "src/**"]) == 1
    capsys.readouterr()

    monkeypatch.setattr(task_service, "atomic_write_text", original)
    assert main(["start", "--objective", "second", "--allow", "tests/**"]) == 0

    assert capsys.readouterr().out.splitlines()[0] == "TASK-0002"
    assert (repository / ".ai" / "tasks" / "TASK-0001" / "creation_failed.json").is_file()
    assert load_task(repository, "TASK-0002")["goal"] == "second"


def test_start_help_lists_all_creation_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["start", "--help"])

    assert caught.value.code == 0
    output = capsys.readouterr().out
    for option in (
        "--objective",
        "--allow",
        "--forbid-action",
        "--allow-detached",
        "--recover",
    ):
        assert option in output
