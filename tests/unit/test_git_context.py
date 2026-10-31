"""Git context collection tests using isolated repositories."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from aiflow import git_context
from aiflow.contracts import validate_contract
from aiflow.errors import AiflowError
from aiflow.git_context import GIT_TIMEOUT_SECONDS, collect_git_context, task_numbers_in_refs

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


def test_non_git_directory_has_stable_error_without_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
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
    def timeout(*_args: object, **_kwargs: object) -> Any:
        raise subprocess.TimeoutExpired(["git"], GIT_TIMEOUT_SECONDS)

    monkeypatch.setattr(git_context.subprocess, "run", timeout)

    with pytest.raises(AiflowError) as caught:
        collect_git_context(tmp_path)

    assert caught.value.code == "GIT_COMMAND_TIMEOUT"
    assert caught.value.details["timeout_seconds"] == 10


def test_unparseable_head_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = create_repository(tmp_path / "repository")
    original = git_context._run_git

    def malformed_head(cwd: Path, arguments: tuple[str, ...], *, failure_code: str) -> str:
        if arguments[0] == "status":
            return "# branch.oid not-a-commit\0# branch.head main\0"
        return original(cwd, arguments, failure_code=failure_code)

    monkeypatch.setattr(git_context, "_run_git", malformed_head)

    with pytest.raises(AiflowError) as caught:
        collect_git_context(repository)

    assert caught.value.code == "GIT_HEAD_INVALID"


def test_production_git_commands_use_fixed_argument_arrays_and_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    (repository / ".ai").mkdir(parents=True)
    (repository / ".ai" / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    responses = iter(
        [
            (0, f"{repository}\n".encode()),
            (0, b"# branch.oid " + b"1" * 40 + b"\0# branch.head main\0"),
            (0, b"main\n"),
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
        (
            "git",
            "status",
            "--porcelain=v2",
            "--branch",
            "--no-show-stash",
            "-z",
            "--untracked-files=all",
        ),
        ("git", "symbolic-ref", "--short", "-q", "HEAD"),
    ]
    assert all(kwargs["timeout"] == 10 for _arguments, kwargs in calls)
    assert all(kwargs["cwd"] == repository for _arguments, kwargs in calls)
    assert all("env" not in kwargs and "shell" not in kwargs for _arguments, kwargs in calls)


def _commit_all(repository: Path, message: str) -> None:
    run_git(repository, "add", "-A")
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


def test_task_numbers_in_refs_reads_every_branch_tree(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    assert task_numbers_in_refs(repository) == frozenset()

    run_git(repository, "switch", "-c", "other")
    for name in ("TASK-0009", "TASK-nope", "notes"):
        (repository / ".ai" / "tasks" / name).mkdir(parents=True)
        (repository / ".ai" / "tasks" / name / "task.yaml").write_text("{}\n", encoding="utf-8")
    _commit_all(repository, "other branch task")
    run_git(repository, "switch", "main")
    (repository / ".ai" / "tasks" / "TASK-0003").mkdir(parents=True)
    (repository / ".ai" / "tasks" / "TASK-0003" / "task.yaml").write_text("{}\n", encoding="utf-8")

    assert task_numbers_in_refs(repository) == frozenset({9})
    assert task_numbers_in_refs(repository / "folder") == frozenset({9})


def test_task_numbers_in_refs_fails_closed_outside_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    with pytest.raises(AiflowError) as caught:
        task_numbers_in_refs(tmp_path)
    assert caught.value.code == "GIT_TASK_REFS_UNAVAILABLE"


STATUS_HEADERS = "# branch.oid " + "1" * 40 + "\0# branch.head main\0"
ORDINARY = "1 .M N... 100644 100644 100644 " + "2" * 40 + " " + "3" * 40 + " "
RENAME = "2 R. N... 100644 100644 100644 " + "2" * 40 + " " + "3" * 40 + " R100 "
UNMERGED = (
    "u UU N... 100644 100644 100644 100644 " + "2" * 40 + " " + "3" * 40 + " " + "4" * 40 + " "
)


@pytest.mark.parametrize(
    "record,paths",
    [
        ("", ()),
        (ORDINARY + "tracked.txt\0", ("tracked.txt",)),
        (RENAME + "new -> literal.txt\0old.txt\0", ("new -> literal.txt",)),
        (RENAME.replace("R100", "R0") + "renamed.txt\0old.txt\0", ("renamed.txt",)),
        (UNMERGED + "conflict.txt\0", ("conflict.txt",)),
        (ORDINARY.replace("N...", "SCMU") + "module\0", ("module",)),
        (
            '? folder/空 格.txt\0? "quoted" -> literal.txt\0',
            ('"quoted" -> literal.txt', "folder/空 格.txt"),
        ),
    ],
)
def test_porcelain_records_preserve_literal_paths(record: str, paths: tuple[str, ...]) -> None:
    assert git_context._parse_status(STATUS_HEADERS + record) == ("1" * 40, "main", paths, False)


@pytest.mark.parametrize(
    "suffix",
    ["# branch.upstream origin/main\0", "# branch.upstream origin/main\0# branch.ab +12 -0\0"],
)
def test_porcelain_accepts_tracking_headers(suffix: str) -> None:
    assert git_context._parse_status(STATUS_HEADERS + suffix) == ("1" * 40, "main", (), True)


@pytest.mark.parametrize(
    "status,code",
    [
        ("", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS[:-1], "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + "\0", "GIT_STATUS_INVALID"),
        ("# branch.head main\0", "GIT_HEAD_UNAVAILABLE"),
        ("# branch.oid (initial)\0# branch.head main\0", "GIT_HEAD_UNAVAILABLE"),
        ("# branch.oid not-a-sha\0# branch.head main\0", "GIT_HEAD_INVALID"),
        ("# branch.oid " + "1" * 40 + "\0", "GIT_BRANCH_UNAVAILABLE"),
        (STATUS_HEADERS.replace("head main", "head "), "GIT_BRANCH_UNAVAILABLE"),
        (STATUS_HEADERS + "# branch.oid " + "1" * 40 + "\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + "# branch.head main\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + "# unknown value\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + "# branch.ab +0 -0\0", "GIT_STATUS_INVALID"),
        (
            STATUS_HEADERS + "# branch.upstream origin/main\0# branch.ab +? -?\0",
            "GIT_STATUS_INVALID",
        ),
        (STATUS_HEADERS + "# branch.upstream ../main\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + "? file\0# branch.ab +0 -0\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + "! ignored\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + "? file\0? file\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + "1 too-few-fields\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + ORDINARY.replace(".M", "..") + "file\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + ORDINARY.replace(".M", "U.") + "file\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + ORDINARY.replace(".M", "MMM") + "file\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + ORDINARY.replace("N...", "SXYZ") + "file\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + ORDINARY.replace("100644", "777777", 1) + "file\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + ORDINARY.replace("2" * 40, "bad-hash") + "file\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + RENAME.replace("R100", "R101") + "new\0old\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + RENAME.replace("R.", "M.") + "new\0old\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + RENAME + "new\0", "GIT_STATUS_INVALID"),
        (STATUS_HEADERS + UNMERGED.replace("UU", "MM") + "file\0", "GIT_STATUS_INVALID"),
    ],
)
def test_invalid_machine_status_fails_closed(status: str, code: str) -> None:
    with pytest.raises(AiflowError) as caught:
        git_context._parse_status(status)
    assert caught.value.code == code


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute",
        "../escape",
        "folder/../escape",
        "./file",
        "a//b",
        "C:/outside",
        "a\\b",
        "line\nfeed",
        "del\x7f",
    ],
)
@pytest.mark.parametrize("record", ["? {path}\0", ORDINARY + "{path}\0", RENAME + "new\0{path}\0"])
def test_invalid_status_paths_are_rejected(path: str, record: str) -> None:
    with pytest.raises(AiflowError) as caught:
        git_context._parse_status(STATUS_HEADERS + record.format(path=path))
    assert caught.value.code == "GIT_STATUS_INVALID"


@pytest.mark.parametrize(
    "branch",
    [
        "@{bad",
        "tab\tbranch",
        "../escape",
        "/absolute",
        "a//b",
        "a/",
        "a.lock",
        ".hidden",
        "end.",
        "x@{y",
        "has space",
        "a\\b",
        "x~y",
        "x\x7fy",
    ],
)
def test_invalid_status_branch_is_rejected(branch: str) -> None:
    with pytest.raises(AiflowError) as caught:
        git_context._parse_status(STATUS_HEADERS.replace("head main", "head " + branch))
    assert caught.value.code == "GIT_BRANCH_UNAVAILABLE"


@pytest.mark.parametrize(
    "outcome,code",
    [
        (1, "GIT_STATUS_UNAVAILABLE"),
        (b"\xff\0", "GIT_OUTPUT_INVALID"),
        ("spawn", "GIT_STATUS_UNAVAILABLE"),
        ("timeout", "GIT_COMMAND_TIMEOUT"),
    ],
)
def test_aggregate_failure_never_produces_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: object, code: str
) -> None:
    repository = create_repository(tmp_path / "repository")
    original = git_context.subprocess.run

    def failed(arguments: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if arguments[1] != "status":
            return original(arguments, **kwargs)
        if outcome == "spawn":
            raise OSError("synthetic spawn failure")
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(arguments, 10)
        return subprocess.CompletedProcess(
            arguments,
            outcome if type(outcome) is int else 0,
            stdout=outcome if isinstance(outcome, bytes) else b"",
            stderr=b"private failure text",
        )

    monkeypatch.setattr(git_context.subprocess, "run", failed)
    with pytest.raises(AiflowError) as caught:
        collect_git_context(repository)
    assert caught.value.code == code
    assert "private failure text" not in str(caught.value.to_dict())


def test_real_rename_and_untracked_unicode_spaces(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "mv", "tracked.txt", "folder/空 格 literal.txt")
    (repository / "folder/新 文件.txt").write_text("new content\n", encoding="utf-8")
    context = collect_git_context(repository / "folder")
    assert context.dirty_paths == ("folder/新 文件.txt", "folder/空 格 literal.txt")
    assert context.repository_path == repository.resolve().as_posix()
    assert context.worktree_dirty


def test_real_conflict_is_in_dirty_paths(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "switch", "-c", "other")
    (repository / "tracked.txt").write_text("other\n", encoding="utf-8")
    _commit_all(repository, "other")
    run_git(repository, "switch", "main")
    (repository / "tracked.txt").write_text("main\n", encoding="utf-8")
    _commit_all(repository, "main")
    result = subprocess.run(
        ["git", "merge", "other"], cwd=repository, capture_output=True, timeout=10
    )
    assert result.returncode == 1
    assert collect_git_context(repository).dirty_paths == ("tracked.txt",)


def test_real_submodule_content_and_untracked_changes_are_dirty(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    module = create_repository(tmp_path / "module-source")
    run_git(
        repository, "-c", "protocol.file.allow=always", "submodule", "add", str(module), "module"
    )
    _commit_all(repository, "add local submodule")
    assert not collect_git_context(repository).worktree_dirty
    (repository / "module/tracked.txt").write_text("modified\n", encoding="utf-8")
    (repository / "module/untracked.txt").write_text("new\n", encoding="utf-8")
    assert collect_git_context(repository).dirty_paths == ("module",)


def test_each_collection_observes_current_git_facts(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    before = collect_git_context(repository)
    (repository / "tracked.txt").write_text("modified\n", encoding="utf-8")
    assert collect_git_context(repository).dirty_paths == ("tracked.txt",)
    _commit_all(repository, "changed")
    run_git(repository, "switch", "-c", "feature/新分支")
    after = collect_git_context(repository)
    assert not after.worktree_dirty
    assert after.head != before.head
    assert after.branch == "feature/新分支"


def test_collection_preserves_environment_and_optional_lock_behavior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    monkeypatch.setenv("GIT_OPTIONAL_LOCKS", "0")
    index = repository / ".git/index"
    before = (index.read_bytes(), index.stat().st_mtime_ns)
    original = git_context.subprocess.run
    calls = []

    def observe(arguments: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((arguments, kwargs))
        assert "env" not in kwargs
        assert os.environ["GIT_OPTIONAL_LOCKS"] == "0"
        return original(arguments, **kwargs)

    monkeypatch.setattr(git_context.subprocess, "run", observe)
    collect_git_context(repository)
    assert len(calls) == 3
    assert (index.read_bytes(), index.stat().st_mtime_ns) == before
    assert not (repository / ".git/index.lock").exists()


def test_nested_git_boundary_still_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    nested = repository / "nested"
    nested.mkdir()
    (nested / ".git").write_text("gitdir: missing\n", encoding="utf-8")
    monkeypatch.setattr(git_context, "_run_git", lambda *_args, **_kwargs: str(repository))
    with pytest.raises(AiflowError) as caught:
        collect_git_context(nested)
    assert caught.value.code == "GIT_ROOT_INVALID"


@pytest.mark.parametrize("branch", ["DETACHED", "folder./feature"])
def test_valid_branch_names_and_tracking_are_not_misclassified(branch: str) -> None:
    status = STATUS_HEADERS.replace("head main", "head " + branch)
    assert git_context._parse_status(status + "# branch.upstream origin/main\0")[1] == branch


def test_ambiguous_tag_keeps_existing_symbolic_ref_branch_fact(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "tag", "main")
    expected = run_git(repository, "symbolic-ref", "--short", "-q", "HEAD")
    assert expected == "heads/main"
    assert collect_git_context(repository).branch == expected


def test_tracking_and_stash_display_config_do_not_change_context(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "branch", "peer")
    run_git(repository, "branch", "--set-upstream-to=peer", "main")
    run_git(repository, "config", "status.showStash", "true")
    run_git(repository, "config", "status.aheadBehind", "false")
    (repository / "tracked.txt").write_text("stash content\n", encoding="utf-8")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "stash",
        "push",
        "-m",
        "local fixture",
    )
    context = collect_git_context(repository)
    assert context.branch == "main"
    assert context.head == run_git(repository, "rev-parse", "HEAD")
    assert context.dirty_paths == ()


@pytest.mark.parametrize(
    "status_branch,observed",
    [
        ("main", "other"),
        ("main", "DETACHED"),
        ("(detached)", "main"),
        ("(detached)", "heads/DETACHED"),
    ],
)
def test_branch_header_must_match_independent_symbolic_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status_branch: str, observed: str
) -> None:
    repository = create_repository(tmp_path / "repository")
    original = git_context._run_git

    def read(cwd: Path, arguments: tuple[str, ...], *, failure_code: str) -> str:
        if arguments[0] == "status":
            return STATUS_HEADERS.replace("head main", "head " + status_branch)
        return original(cwd, arguments, failure_code=failure_code)

    monkeypatch.setattr(git_context, "_run_git", read)
    monkeypatch.setattr(git_context, "_read_branch", lambda _root: observed)
    with pytest.raises(AiflowError) as caught:
        collect_git_context(repository)
    assert caught.value.code == "GIT_BRANCH_UNAVAILABLE"


def test_ambiguous_branch_named_detached_keeps_symbolic_ref_fact(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "switch", "-c", "DETACHED")
    run_git(repository, "tag", "DETACHED")
    expected = run_git(repository, "symbolic-ref", "--short", "-q", "HEAD")
    assert expected == "heads/DETACHED"
    assert collect_git_context(repository).branch == expected


@pytest.mark.parametrize(
    "branch,upstream,tag_collision",
    [
        ("@", None, False),
        ("@", "main", False),
        ("main", "@", False),
        ("(detached)", None, False),
        ("(detached)", "main", False),
        ("(detached)", "main", True),
        ("(initial)", None, False),
        ("-option", None, False),
        ("main", "-option", False),
    ],
)
def test_git_full_ref_names_preserve_existing_branch_and_upstream_facts(
    tmp_path: Path, branch: str, upstream: str | None, tag_collision: bool
) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "check-ref-format", "refs/heads/" + branch)
    run_git(repository, "update-ref", "refs/heads/" + branch, "HEAD")
    run_git(repository, "symbolic-ref", "HEAD", "refs/heads/" + branch)
    if tag_collision:
        run_git(repository, "tag", branch)
    if upstream is not None:
        run_git(repository, "check-ref-format", "refs/heads/" + upstream)
        run_git(repository, "update-ref", "refs/heads/" + upstream, "HEAD")
        run_git(repository, "config", "branch." + branch + ".remote", ".")
        run_git(repository, "config", "branch." + branch + ".merge", "refs/heads/" + upstream)
    expected = run_git(repository, "symbolic-ref", "--short", "-q", "HEAD")
    context = collect_git_context(repository)
    assert context.branch == expected
    assert context.head == run_git(repository, "rev-parse", "HEAD")
    assert context.dirty_paths == ()


def test_actual_detached_head_cannot_have_forged_tracking_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    run_git(repository, "checkout", "--detach", "HEAD")
    original = git_context._run_git

    def forged(cwd: Path, arguments: tuple[str, ...], *, failure_code: str) -> str:
        value = original(cwd, arguments, failure_code=failure_code)
        if arguments[0] == "status":
            return value + "# branch.upstream origin/main\0"
        return value

    monkeypatch.setattr(git_context, "_run_git", forged)
    with pytest.raises(AiflowError) as caught:
        collect_git_context(repository)
    assert caught.value.code == "GIT_STATUS_INVALID"
