"""Integration coverage for the read-only repository adoption inventory."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tools.analysis import repository_readiness

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "analysis" / "repository_readiness.py"


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


def create_repository(path: Path, *, commit: bool = True) -> Path:
    path.mkdir()
    run_git(path, "init", "-b", "main")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    if commit:
        run_git(path, "add", "tracked.txt")
        run_git(
            path,
            "-c",
            "user.name=Inventory Tests",
            "-c",
            "user.email=inventory@example.invalid",
            "commit",
            "-m",
            "initial",
        )
    return path


def run_inventory(
    repository: Path, *, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repository), "--format", "json"],
        capture_output=True,
        check=False,
        encoding="utf-8",
        env=environment,
        timeout=20,
    )


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def test_inventory_is_read_only_and_consistent_from_a_subdirectory(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    (repository / "AGENTS.md").write_text("keep these instructions\n", encoding="utf-8")
    (repository / "AGENTS.override.md").write_text("keep override\n", encoding="utf-8")
    (repository / ".githooks").mkdir()
    (repository / ".githooks" / "preserve").write_text("keep\n", encoding="utf-8")
    (repository / ".github" / "workflows").mkdir(parents=True)
    (repository / ".github" / "workflows" / "quality.yml").write_text("name: quality\n")
    (repository / "pyproject.toml").write_text("[project]\nname = 'target'\n", encoding="utf-8")
    (repository / ".codex").mkdir()
    (repository / ".codex" / "config.toml").write_text("keep = true\n", encoding="utf-8")
    run_git(
        repository,
        "add",
        "AGENTS.md",
        "AGENTS.override.md",
        ".githooks",
        ".github",
        "pyproject.toml",
        ".codex",
    )
    run_git(
        repository,
        "-c",
        "user.name=Inventory Tests",
        "-c",
        "user.email=inventory@example.invalid",
        "commit",
        "-m",
        "add target conventions",
    )
    (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
    before = tree_bytes(repository)

    root_result = run_inventory(repository)
    subdirectory = repository / "nested"
    subdirectory.mkdir()
    sub_result = run_inventory(subdirectory)

    assert root_result.returncode == sub_result.returncode == 0
    root_report = json.loads(root_result.stdout)
    sub_report = json.loads(sub_result.stdout)
    direct_report = repository_readiness.build_inventory(repository)
    assert root_report["repository"] == sub_report["repository"]
    assert direct_report["repository"] == root_report["repository"]
    assert root_report["repository"]["dirty"]["is_dirty"] is True
    assert root_report["repository"]["dirty"]["path_count"] >= 1
    paths = root_report["fixed_path_inventory"]
    assert paths["instructions"]["AGENTS.md"] == "present"
    assert paths["instructions"]["AGENTS.override.md"] == "present"
    assert paths["hook_conventions"][".githooks"] == "present"
    assert paths["ci_entrypoints"][".github/workflows"] == "present"
    assert paths["quality_configuration"]["pyproject.toml"] == "present"
    assert paths["agent_configuration"][".codex/config.toml"] == "present"
    assert "not readiness" in root_report["conclusion"]
    assert tree_bytes(repository) == before
    assert (repository / "AGENTS.md").read_text(encoding="utf-8") == "keep these instructions\n"


def test_inventory_reports_dirty_count_without_paths_and_ignores_inherited_git_environment(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path / "repository")
    (repository / "tracked.txt").write_text("pending\n", encoding="utf-8")
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_DIR": str(tmp_path / "wrong-git-dir"),
            "GIT_WORK_TREE": str(tmp_path / "wrong-worktree"),
            "GIT_CONFIG_GLOBAL": str(tmp_path / "wrong-config"),
        }
    )

    result = run_inventory(repository, environment=environment)

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert repository_readiness.build_inventory(repository)["repository"] == report["repository"]
    assert report["repository"]["dirty"] == {"is_dirty": True, "path_count": 1}
    assert "tracked.txt" not in result.stdout


def test_inventory_disables_fsmonitor(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    sentinel = tmp_path / "fsmonitor-called"
    command = tmp_path / "fsmonitor"
    if os.name == "nt":
        command = command.with_suffix(".cmd")
        command.write_text(f'@echo off\necho called > "{sentinel}"\n', encoding="utf-8")
    else:
        command.write_text(f"#!/bin/sh\nprintf called > '{sentinel}'\n", encoding="utf-8")
        command.chmod(command.stat().st_mode | stat.S_IXUSR)
    run_git(repository, "config", "core.fsmonitor", str(command))

    result = run_inventory(repository)

    assert result.returncode == 0
    repository_readiness.build_inventory(repository)
    assert not sentinel.exists()


@pytest.mark.parametrize("config_location", ("local", "include", "worktree"))
@pytest.mark.parametrize("filter_type", ("clean", "process"))
def test_inventory_does_not_run_target_clean_filters(
    tmp_path: Path, config_location: str, filter_type: str, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = create_repository(tmp_path / "repository")
    sentinel = tmp_path / "filter-called"
    command = tmp_path / "clean-filter"
    if os.name == "nt":
        command = command.with_suffix(".cmd")
        command.write_text(f'@echo off\necho called > "{sentinel}"\ntype\n', encoding="utf-8")
    else:
        command.write_text(f"#!/bin/sh\nprintf called > '{sentinel}'\ncat\n", encoding="utf-8")
        command.chmod(command.stat().st_mode | stat.S_IXUSR)
    (repository / ".gitattributes").write_text("tracked.txt filter=sentinel\n", encoding="utf-8")
    run_git(repository, "add", ".gitattributes")
    run_git(
        repository,
        "-c",
        "user.name=Inventory Tests",
        "-c",
        "user.email=inventory@example.invalid",
        "commit",
        "-m",
        "add target filter",
    )
    key = f"filter.sentinel.{filter_type}"
    if config_location == "include":
        include = repository / ".git" / "included-filter.config"
        run_git(repository, "config", "--file", str(include), key, str(command))
        run_git(repository, "config", "include.path", str(include))
    elif config_location == "worktree":
        run_git(repository, "config", "extensions.worktreeConfig", "true")
        run_git(repository, "config", "--worktree", key, str(command))
    else:
        run_git(repository, "config", key, str(command))
    (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
    before = tree_bytes(repository)

    result = run_inventory(repository)

    assert result.returncode == 0
    report = repository_readiness.build_inventory(repository)
    assert report["repository"]["dirty"] == {
        "is_dirty": None,
        "path_count": None,
        "reason": "unknown_target_clean_or_process_filter",
    }
    assert repository_readiness.main(["--repo", str(repository)]) == 0
    assert (
        "Dirty paths: unknown (unknown_target_clean_or_process_filter)" in capsys.readouterr().out
    )
    assert not sentinel.exists()
    assert tree_bytes(repository) == before


@pytest.mark.parametrize(
    ("kind", "expected_code"),
    (
        ("missing", "TARGET_NOT_FOUND"),
        ("non_git", "GIT_NOT_REPOSITORY"),
        ("no_head", "GIT_HEAD_UNAVAILABLE"),
        ("bare", "GIT_BARE_REPOSITORY"),
    ),
)
def test_inventory_rejects_unusable_targets_without_git_stderr(
    tmp_path: Path, kind: str, expected_code: str
) -> None:
    target = tmp_path / kind
    if kind == "non_git":
        target.mkdir()
    elif kind == "no_head":
        create_repository(target, commit=False)
    elif kind == "bare":
        subprocess.run(["git", "init", "--bare", str(target)], check=True, capture_output=True)

    result = run_inventory(target)

    assert result.returncode == 2
    with pytest.raises(repository_readiness.InventoryError) as error:
        repository_readiness.build_inventory(target)
    assert error.value.code == expected_code
    error = json.loads(result.stdout)["error"]
    assert error["code"] == expected_code
    assert "fatal:" not in error["message"]


def test_inventory_does_not_follow_target_or_fixed_path_links(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "repository")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "instructions").write_text("do not read\n", encoding="utf-8")
    try:
        (repository / "AGENTS.md").symlink_to(outside / "instructions")
        target_link = tmp_path / "repository-link"
        target_link.symlink_to(repository, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink capability unavailable: {error}")

    report_result = run_inventory(repository)
    link_result = run_inventory(target_link)

    assert report_result.returncode == 0
    direct_report = repository_readiness.build_inventory(repository)
    report = json.loads(report_result.stdout)
    assert direct_report["fixed_path_inventory"] == report["fixed_path_inventory"]
    assert report["fixed_path_inventory"]["instructions"]["AGENTS.md"] == "link_or_reparse"
    assert link_result.returncode == 2
    assert json.loads(link_result.stdout)["error"]["code"] == "PATH_LINK_BOUNDARY"


def test_inventory_text_main_and_detached_branch_are_descriptive(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = create_repository(tmp_path / "repository")
    commit = run_git(repository, "rev-parse", "HEAD")
    run_git(repository, "checkout", "--detach", commit)

    assert repository_readiness.main(["--repo", str(repository)]) == 0

    output = capsys.readouterr().out
    assert "Read-only adoption inventory" in output
    assert "Branch: DETACHED" in output
    assert "Manual mapping still required:" in output


def test_inventory_main_uses_structured_errors_and_never_leaks_git_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing"

    assert repository_readiness.main(["--repo", str(missing), "--format", "json"]) == 2

    error = json.loads(capsys.readouterr().out)["error"]
    assert error == {"code": "TARGET_NOT_FOUND", "message": "Target directory does not exist"}


def test_inventory_helpers_reject_file_paths_and_invalid_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("x\n", encoding="utf-8")
    with pytest.raises(repository_readiness.InventoryError, match="Target must be a directory"):
        repository_readiness.build_inventory(file_path)
    with pytest.raises(repository_readiness.InventoryError, match="status is invalid"):
        repository_readiness._dirty_count("unexpected output")

    def unavailable(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("not exposed")

    monkeypatch.setattr(repository_readiness.subprocess, "run", unavailable)
    with pytest.raises(repository_readiness.InventoryError) as error:
        repository_readiness._run_git(tmp_path, ("status",))
    assert error.value.code == "GIT_UNAVAILABLE"


def test_inventory_rejects_parent_traversal_before_any_git_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_git(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("parent traversal must fail before Git is called")

    monkeypatch.setattr(repository_readiness, "_run_git", no_git)
    paths = [Path("ordinary") / ".." / "target"]
    link = tmp_path / "link"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pass
    else:
        paths.append(link / ".." / "target")
    for path in paths:
        with pytest.raises(repository_readiness.InventoryError) as error:
            repository_readiness.build_inventory(path)
        assert error.value.code == "PATH_PARENT_TRAVERSAL"


def test_inventory_git_environment_removes_all_inherited_git_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "do-not-use")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    environment = repository_readiness._git_environment()

    assert not any(
        key.startswith("GIT_")
        for key in environment
        if key
        not in {
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_SYSTEM",
            "GIT_CONFIG_NOSYSTEM",
            "GIT_OPTIONAL_LOCKS",
            "GIT_TERMINAL_PROMPT",
            "GIT_NO_LAZY_FETCH",
            "GIT_ALLOW_PROTOCOL",
            "GIT_PAGER",
        }
    )
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert environment["GIT_ALLOW_PROTOCOL"] == ""
