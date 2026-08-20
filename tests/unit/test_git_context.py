"""Git context collection tests using isolated repositories."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from aiflow.contracts import validate_contract
from aiflow.errors import AiflowError
from aiflow.git_context import GIT_TIMEOUT_SECONDS, collect_git_context

REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    (path / ".ai").mkdir()
    (path / ".ai" / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    (path / "folder").mkdir()
    (path / "folder" / "nested.txt").write_text("nested\n", encoding="utf-8")
    run_git(path, "add", ".ai/repository-id", "tracked.txt", "folder/nested.txt")
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


def test_collect_clean_repository_context(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")

    context = collect_git_context(repository)

    assert context.repository_id == REPOSITORY_ID
    assert context.repository_path == repository.resolve().as_posix()
    assert context.branch == "main"
    assert context.head == run_git(repository, "rev-parse", "HEAD")
    assert context.worktree_dirty is False
    assert context.dirty_paths == ()


def test_collect_dirty_paths_are_relative_normalized_and_sorted(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (repository / "folder" / "nested.txt").write_text("changed nested\n", encoding="utf-8")

    context = collect_git_context(repository)

    assert context.worktree_dirty is True
    assert context.dirty_paths == ("folder/nested.txt", "tracked.txt")
    assert all("\\" not in path for path in context.dirty_paths)


def test_collect_branch_and_detached_head(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "switch", "-c", "feature/context")

    assert collect_git_context(repository).branch == "feature/context"

    run_git(repository, "checkout", "--detach", "HEAD")

    assert collect_git_context(repository).branch == "DETACHED"


def test_repository_identity_survives_checkout_copy(tmp_path: Path) -> None:
    source = create_repository(tmp_path / "source")
    copied = tmp_path / "different absolute checkout"
    shutil.copytree(source, copied)

    source_context = collect_git_context(source)
    copied_context = collect_git_context(copied)

    assert copied_context.repository_id == source_context.repository_id
    assert copied_context.head == source_context.head
    assert copied_context.repository_path != source_context.repository_path


def test_task_contract_accepts_normalized_dirty_paths() -> None:
    fixture = json.loads(
        (PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "task.json").read_text(
            encoding="utf-8"
        )
    )
    fixture["worktree_dirty_paths"] = ["folder/new.txt", "tracked.txt"]

    assert validate_contract("task", fixture) == []


@pytest.mark.parametrize("dirty_path", ["/absolute.txt", "../outside.txt", "folder\\file.txt"])
def test_task_contract_rejects_non_normalized_dirty_paths(dirty_path: str) -> None:
    fixture = json.loads(
        (PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "task.json").read_text(
            encoding="utf-8"
        )
    )
    fixture["worktree_dirty_paths"] = [dirty_path]

    assert validate_contract("task", fixture)


def test_non_git_directory_has_stable_error_without_environment(tmp_path: Path) -> None:
    secret = "SHOULD_NOT_APPEAR"

    with pytest.raises(AiflowError) as caught:
        collect_git_context(tmp_path)

    assert caught.value.code == "GIT_NOT_REPOSITORY"
    assert secret not in str(caught.value.to_dict())


def test_empty_repository_reports_unavailable_head(tmp_path: Path) -> None:
    repository = tmp_path / "empty"
    repository.mkdir()
    run_git(repository, "init", "-b", "main")
    (repository / ".ai").mkdir()
    (repository / ".ai" / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")

    with pytest.raises(AiflowError) as caught:
        collect_git_context(repository)

    assert caught.value.code == "GIT_HEAD_UNAVAILABLE"


def test_invalid_repository_id_is_rejected(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    (repository / ".ai" / "repository-id").write_text("not-a-uuid\n", encoding="utf-8")

    with pytest.raises(AiflowError) as caught:
        collect_git_context(repository)

    assert caught.value.code == "GIT_REPOSITORY_ID_INVALID"


def test_git_timeout_has_stable_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aiflow import git_context

    def timeout(*_args: object, **_kwargs: object) -> Any:
        raise subprocess.TimeoutExpired(["git"], GIT_TIMEOUT_SECONDS)

    monkeypatch.setattr(git_context.subprocess, "run", timeout)

    with pytest.raises(AiflowError) as caught:
        collect_git_context(tmp_path)

    assert caught.value.code == "GIT_COMMAND_TIMEOUT"
    assert caught.value.details["timeout_seconds"] == 10


def test_unparseable_head_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aiflow import git_context

    repository = create_repository(tmp_path / "repository")
    original = git_context._run_git

    def malformed_head(cwd: Path, arguments: tuple[str, ...], *, failure_code: str) -> str:
        if arguments == ("rev-parse", "HEAD"):
            return "not-a-commit"
        return original(cwd, arguments, failure_code=failure_code)

    monkeypatch.setattr(git_context, "_run_git", malformed_head)

    with pytest.raises(AiflowError) as caught:
        collect_git_context(repository)

    assert caught.value.code == "GIT_HEAD_INVALID"


def test_production_git_commands_use_fixed_argument_arrays_and_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import git_context

    repository = tmp_path / "repository"
    (repository / ".ai").mkdir(parents=True)
    (repository / ".ai" / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    responses = iter(
        [
            (0, f"{repository}\n".encode()),
            (0, b"1" * 40 + b"\n"),
            (0, b"main\n"),
            (0, b""),
        ]
    )
    calls: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    def fake_run(arguments: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((tuple(arguments), kwargs))
        returncode, stdout = next(responses)
        return subprocess.CompletedProcess(arguments, returncode, stdout=stdout, stderr=b"")

    monkeypatch.setattr(git_context.subprocess, "run", fake_run)

    collect_git_context(repository)

    assert [arguments for arguments, _kwargs in calls] == [
        ("git", "rev-parse", "--show-toplevel"),
        ("git", "rev-parse", "HEAD"),
        ("git", "symbolic-ref", "--short", "-q", "HEAD"),
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
    ]
    assert all(kwargs["timeout"] == 10 for _arguments, kwargs in calls)
    assert all(kwargs["cwd"] == repository for _arguments, kwargs in calls)
    assert all("env" not in kwargs and "shell" not in kwargs for _arguments, kwargs in calls)
