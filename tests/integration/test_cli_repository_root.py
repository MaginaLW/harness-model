"""Acceptance checks for CLI roots, invocation paths, and Git boundary failures."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_start_command import create_repository, run_git

from aiflow import cli, contracts, git_context
from aiflow.errors import AiflowError


def _deep(repository: Path) -> Path:
    path = repository / "folder" / "nested"
    path.mkdir(parents=True)
    return path


def _resolve(path: Path) -> Path:
    resolver = getattr(git_context, "resolve_repository_root", None)
    assert callable(resolver), "git_context.resolve_repository_root must locate the worktree root"
    return resolver(path)


def _snapshot(root: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


@pytest.mark.parametrize("from_subdirectory", [False, True])
def test_real_start_writes_only_the_discovered_task_root_and_preserves_cwd(
    from_subdirectory: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    invocation = _deep(repository) if from_subdirectory else repository
    monkeypatch.chdir(invocation)

    assert cli.main(["start", "--objective", "bounded root task", "--allow", "tracked.txt"]) == 0

    task = repository / ".ai" / "tasks" / "TASK-0001"
    assert capsys.readouterr().out.splitlines() == ["TASK-0001", str(task.resolve())]
    assert (task / "task.yaml").is_file()
    assert Path.cwd() == invocation
    if from_subdirectory:
        assert not (invocation / ".ai").exists()


def test_real_status_is_identical_at_root_and_deep_directory_without_chdir_or_asset_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    invocation = _deep(repository)
    monkeypatch.chdir(repository)
    assert cli.main(["start", "--objective", "same task", "--allow", "tracked.txt"]) == 0
    capsys.readouterr()
    assert cli.main(["status", "TASK-0001", "--format", "json"]) == 0
    expected = json.loads(capsys.readouterr().out)
    before = _snapshot(repository / ".ai")
    monkeypatch.chdir(invocation)
    monkeypatch.setattr(os, "chdir", lambda *_args: pytest.fail("CLI must never chdir"))

    assert cli.main(["status", "TASK-0001", "--format", "json"]) == 0

    assert json.loads(capsys.readouterr().out) == expected
    assert _snapshot(repository / ".ai") == before
    assert Path.cwd() == invocation


@pytest.mark.parametrize(
    "arguments, expected",
    [
        ([], None),
        (["--help"], 0),
        (["--version"], 0),
        (["status", "--help"], 0),
        (["--unknown"], 2),
        (["status"], 2),
    ],
)
def test_repository_free_entry_points_do_not_run_git_or_business_services(
    arguments: list[str],
    expected: int | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(git_context, "_run_git", lambda *_args, **_kwargs: pytest.fail("entry Git"))
    monkeypatch.setattr(cli, "summarize_task", lambda *_args: pytest.fail("entry service"))
    if expected is None:
        assert cli.main(arguments) == 0
    else:
        with pytest.raises(SystemExit) as caught:
            cli.main(arguments)
        assert caught.value.code == expected
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out + captured.err
    assert Path.cwd() == tmp_path


@pytest.mark.parametrize(
    "command", ["answer", "approve", "review-record", "observe", "gate", "verify", "review-output"]
)
def test_explicit_file_arguments_stay_relative_to_invocation_with_root_named_decoys(
    command: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    invocation = _deep(repository)
    for directory, marker in ((repository, "root-decoy"), (invocation, "invocation")):
        (directory / "request.json").write_text(marker, encoding="utf-8")
        (directory / "result.json").write_text(marker, encoding="utf-8")
        (directory / "runs").mkdir()
        (directory / "runs" / "marker").write_text(marker, encoding="utf-8")
    monkeypatch.chdir(invocation)
    monkeypatch.setattr(os, "chdir", lambda *_args: pytest.fail("file argument chdir"))
    seen: list[Path] = []

    def check_root(root: Path) -> None:
        assert root == repository.resolve()
        assert Path.cwd() == invocation
        assert contracts.load_schema("task")["title"] == "AI Flow task"
        seen.append(root)

    def check_input(path: Path) -> None:
        assert path.resolve() == invocation / "request.json"
        assert path.read_text(encoding="utf-8") == "invocation"

    def transition(root: Path, _task: str, **kwargs: Any) -> SimpleNamespace:
        check_root(root)
        check_input(kwargs["options_file"] if command == "answer" else kwargs["action_file"])
        return SimpleNamespace(task={"current_state": "READY_TO_IMPLEMENT"})

    def review_record(root: Path, _task: str, **kwargs: Any) -> SimpleNamespace:
        check_root(root)
        check_input(kwargs["input_path"])
        return SimpleNamespace(record={"review_id": "REV-0001", "revision": 1})

    def observe(root: Path, _task: str, input_path: Path, **_kwargs: Any) -> SimpleNamespace:
        check_root(root)
        check_input(input_path)
        return SimpleNamespace(decision=SimpleNamespace(execution_allowed=False))

    def gate(root: Path, _task: str, **kwargs: Any) -> SimpleNamespace:
        check_root(root)
        check_input(kwargs["evidence_path"])
        return SimpleNamespace(passed=True, to_text=lambda: "native Gate")

    def verify(root: Path, _task: str, **kwargs: Any) -> SimpleNamespace:
        check_root(root)
        assert kwargs["ci_run_dir"].resolve() == invocation / "runs"
        assert (kwargs["ci_run_dir"] / "marker").read_text(encoding="utf-8") == "invocation"
        assert kwargs["output"].resolve() == invocation / "result.json"
        kwargs["output"].write_text("native-output", encoding="utf-8")
        return SimpleNamespace(task_id="TASK-0001", state=None, conclusion="passed")

    def review_context(root: Path, _task: str, _stage: str) -> dict[str, str]:
        check_root(root)
        return {"resource": "selected-root"}

    arguments = {
        "answer": [
            "answer",
            "TASK-0001",
            "--options-file",
            "request.json",
            "--select",
            "A",
            "--actor",
            "owner",
            "--reason",
            "choice",
        ],
        "approve": [
            "approve",
            "TASK-0001",
            "--type",
            "action",
            "--action-file",
            "request.json",
            "--actor",
            "owner",
            "--reason",
            "action",
        ],
        "review-record": [
            "review",
            "record",
            "TASK-0001",
            "--input",
            "request.json",
            "--actor",
            "reviewer",
        ],
        "observe": ["observe", "TASK-0001", "--input", "request.json", "--mode", "dry-run"],
        "gate": ["gate", "TASK-0001", "--evidence", "request.json"],
        "verify": [
            "verify",
            "TASK-0001",
            "--ci",
            "--ci-run-dir",
            "runs",
            "--output",
            "result.json",
        ],
        "review-output": [
            "review",
            "context",
            "TASK-0001",
            "--stage",
            "design",
            "--output",
            "result.json",
        ],
    }
    for name, replacement in (
        ("answer_task", transition),
        ("approve_task", transition),
        ("record_review", review_record),
        ("run_observation_file", observe),
        ("evaluate_gate", gate),
        ("verify_task", verify),
        ("build_review_context", review_context),
    ):
        monkeypatch.setattr(cli, name, replacement)
    monkeypatch.setattr(cli, "serialize_observation_result", lambda _value: {"native": True})

    assert cli.main(arguments[command]) == (2 if command == "observe" else 0)

    assert seen == [repository.resolve()]
    assert (repository / "result.json").read_text(encoding="utf-8") == "root-decoy"
    if command == "verify":
        assert (invocation / "result.json").read_text(encoding="utf-8") == "native-output"
    elif command == "review-output":
        assert json.loads((invocation / "result.json").read_text(encoding="utf-8")) == {
            "resource": "selected-root"
        }
        assert capsys.readouterr().out.strip() == str((invocation / "result.json").resolve())
    assert Path.cwd() == invocation


def test_cli_success_and_business_failure_restore_prior_schema_between_repositories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = create_repository(tmp_path / "first")
    second = create_repository(tmp_path / "second")
    scope_factory = getattr(contracts, "schema_directory_context", None)
    assert callable(scope_factory), "CLI requires the scoped Schema API"
    for repository in (first, second):
        schema_path = repository / ".ai" / "schemas" / "task.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["title"] = repository.name
        schema_path.write_text(json.dumps(schema), encoding="utf-8")

    def status(root: Path, _task: str) -> SimpleNamespace:
        assert contracts.load_schema("task")["title"] == root.name
        if root == second:
            raise AiflowError("business sentinel", code="TEST_BUSINESS_FAILURE")
        return SimpleNamespace(to_text=lambda: "native summary")

    monkeypatch.setattr(cli, "summarize_task", status)
    with scope_factory(first / ".ai" / "schemas"):
        for repository, result in ((first, 0), (second, 1)):
            invocation = _deep(repository)
            monkeypatch.chdir(invocation)
            assert cli.main(["status", "TASK-0001"]) == result
            assert contracts.load_schema("task")["title"] == "first"
            assert Path.cwd() == invocation


def test_cli_locates_once_before_dispatch_without_collecting_full_git_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    invocation = _deep(repository)
    monkeypatch.chdir(invocation)
    original = git_context._run_git
    seen: list[tuple[str, ...]] = []

    def inspect(cwd: Path, arguments: tuple[str, ...], *, failure_code: str) -> str:
        seen.append(arguments)
        assert arguments == ("rev-parse", "--show-toplevel"), "entry must not precollect GitContext"
        return original(cwd, arguments, failure_code=failure_code)

    def status(root: Path, _task: str) -> SimpleNamespace:
        assert root == repository.resolve()
        assert contracts.load_schema("task")["title"] == "AI Flow task"
        return SimpleNamespace(to_text=lambda: "native summary")

    monkeypatch.setattr(git_context, "_run_git", inspect)
    monkeypatch.setattr(cli, "summarize_task", status)

    assert cli.main(["status", "TASK-0001"]) == 0
    assert seen == [("rev-parse", "--show-toplevel")]
    assert Path.cwd() == invocation


def test_root_locator_handles_real_subdirectories_and_linked_worktree_git_files(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path / "repository")
    assert _resolve(_deep(repository)) == repository.resolve()
    worktree = tmp_path / "linked"
    run_git(repository, "worktree", "add", "--detach", str(worktree), "HEAD")
    assert (worktree / ".git").is_file()
    assert _resolve(_deep(worktree)) == worktree.resolve()
    assert (
        git_context.collect_git_context(worktree).repository_path == worktree.resolve().as_posix()
    )


def test_nearest_nested_repository_without_ai_assets_never_borrows_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = create_repository(tmp_path / "parent")
    nested = parent / "nested"
    nested.mkdir()
    run_git(nested, "init", "-b", "main")
    before = _snapshot(parent / ".ai")
    monkeypatch.chdir(nested)

    assert cli.main(["start", "--objective", "must reject", "--allow", "tracked.txt"]) == 1

    assert not (nested / ".ai").exists()
    assert _snapshot(parent / ".ai") == before
    assert Path.cwd() == nested


@pytest.mark.parametrize("git_marker", ["directory", "file"])
def test_git_environment_redirect_cannot_cross_nested_marker_or_write_parent_assets(
    git_marker: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = create_repository(tmp_path / "parent")
    nested = parent / "nested"
    nested.mkdir()
    if git_marker == "directory":
        run_git(nested, "init", "-b", "main")
    else:
        run_git(parent, "worktree", "add", "--detach", str(nested), "HEAD")
        for entry in (nested / ".ai").rglob("*"):
            if entry.is_file():
                entry.unlink()
    invocation = _deep(nested)
    monkeypatch.setenv("GIT_DIR", str(parent / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(parent))
    monkeypatch.chdir(invocation)
    before = _snapshot(parent / ".ai")
    try:
        result = cli.main(
            ["start", "--objective", "must reject redirect", "--allow", "tracked.txt"]
        )
    finally:
        assert _snapshot(parent / ".ai") == before
    assert result == 1
    with pytest.raises(AiflowError) as caught:
        _resolve(invocation)
    assert caught.value.code == "GIT_ROOT_INVALID"
    assert Path.cwd() == invocation


def test_relative_git_environment_keeps_existing_discovery_and_identity_check_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository(tmp_path / "repository")
    invocation = _deep(repository)
    monkeypatch.setenv("GIT_DIR", "../../.git")
    monkeypatch.setenv("GIT_WORK_TREE", "../..")

    assert _resolve(invocation) == repository.resolve()
    with pytest.raises(AiflowError) as caught:
        git_context.collect_git_context(invocation)
    assert caught.value.code == "GIT_HEAD_UNAVAILABLE"
    assert os.environ["GIT_DIR"] == "../../.git"
    assert os.environ["GIT_WORK_TREE"] == "../.."


@pytest.mark.parametrize("bare", [False, True])
def test_root_locator_rejects_non_worktrees_with_existing_error_contract(
    bare: bool,
    tmp_path: Path,
) -> None:
    if bare:
        run_git(tmp_path, "init", "--bare")
    with pytest.raises(AiflowError) as caught:
        _resolve(tmp_path)
    assert caught.value.code == "GIT_NOT_REPOSITORY"


@pytest.mark.parametrize("kind", ["empty", "relative", "unrelated", "sibling-prefix"])
def test_root_locator_rejects_invalid_root_output_without_asset_fallback(
    kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested = tmp_path / "repository-extra"
    requested.mkdir()
    output = {
        "empty": "",
        "relative": "repository",
        "unrelated": str(tmp_path / "elsewhere"),
        "sibling-prefix": str(tmp_path / "repository"),
    }[kind]
    monkeypatch.setattr(git_context, "_run_git", lambda *_args, **_kwargs: output)
    with pytest.raises(AiflowError):
        _resolve(requested)


def test_root_locator_keeps_fixed_git_timeout_and_invalid_utf8_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*_args: object, **_kwargs: object) -> Any:
        raise subprocess.TimeoutExpired(["git"], git_context.GIT_TIMEOUT_SECONDS)

    monkeypatch.setattr(git_context.subprocess, "run", timeout)
    with pytest.raises(AiflowError) as caught:
        _resolve(tmp_path)
    assert caught.value.code == "GIT_COMMAND_TIMEOUT"
    assert caught.value.details["timeout_seconds"] == 10
    monkeypatch.setattr(
        git_context.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(args, 0, stdout=b"\xff", stderr=b""),
    )
    with pytest.raises(AiflowError) as caught:
        _resolve(tmp_path)
    assert caught.value.code == "GIT_OUTPUT_INVALID"
