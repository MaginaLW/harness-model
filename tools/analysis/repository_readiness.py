"""Read-only inventory for considering a repository's AI-workflow adoption.

This is intentionally an inventory, not an admission check.  It never runs
target code, tests, hooks, or the AI Flow CLI, and it does not decide quality,
authorization, or whether a target can adopt the full engine.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

GIT_TIMEOUT_SECONDS = 5
FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
INSTRUCTION_PATHS = (
    "AGENTS.md",
    "AGENTS.override.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
)
HOOK_PATHS = (".pre-commit-config.yaml", ".githooks", ".husky", "lefthook.yml")
AGENT_CONFIGURATION_PATHS = (".codex/config.toml", ".claude/settings.json")
CI_PATHS = (".github/workflows", ".gitlab-ci.yml", "azure-pipelines.yml", ".circleci/config.yml")
QUALITY_PATHS = (
    "pyproject.toml",
    "package.json",
    "pytest.ini",
    "tox.ini",
    "noxfile.py",
    "Makefile",
    "uv.lock",
    "poetry.lock",
    "requirements.txt",
)
AI_FLOW_PATHS = (
    ".ai",
    ".ai/repository-id",
    ".ai/policy",
    ".ai/schemas",
    ".ai/templates",
    ".ai/bootstrap-mode.yaml",
)


class InventoryError(ValueError):
    """An inventory cannot be collected without crossing a safety boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _is_reparse(path: Path) -> bool:
    try:
        attributes = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISLNK(attributes.st_mode) or bool(
        getattr(attributes, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT
    )


def _absolute_without_resolving(path: Path) -> Path:
    """Return a lexical absolute path without following an input link."""
    if ".." in path.parts:
        raise InventoryError("PATH_PARENT_TRAVERSAL", "Target path must not contain '..'")
    return Path(os.path.abspath(os.fspath(path)))


def _assert_no_reparse_boundary(path: Path) -> None:
    """Reject a path whose existing component is a symlink or reparse point."""
    absolute = _absolute_without_resolving(path)
    anchor = Path(absolute.anchor)
    current = anchor
    for part in absolute.parts[1:]:
        current /= part
        if not os.path.lexists(current):
            break
        if _is_reparse(current):
            raise InventoryError("PATH_LINK_BOUNDARY", "Target path crosses a link boundary")


def _safe_target(path: Path) -> Path:
    absolute = _absolute_without_resolving(path)
    _assert_no_reparse_boundary(absolute)
    if not absolute.exists():
        raise InventoryError("TARGET_NOT_FOUND", "Target directory does not exist")
    if not absolute.is_dir():
        raise InventoryError("TARGET_NOT_DIRECTORY", "Target must be a directory")
    return absolute


def _git_environment() -> dict[str, str]:
    """Remove inherited Git redirection/configuration before local inspection."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_ALLOW_PROTOCOL": "",
            "GIT_PAGER": "cat",
            "LC_ALL": "C",
        }
    )
    return environment


def _run_git(repository: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "--no-pager", "-c", "core.fsmonitor=false", "--no-optional-locks", *arguments],
            cwd=repository,
            env=_git_environment(),
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise InventoryError("GIT_UNAVAILABLE", "Git metadata could not be inspected") from error


def _git_stdout(repository: Path, arguments: Sequence[str], code: str, message: str) -> str:
    result = _run_git(repository, arguments)
    if result.returncode != 0:
        raise InventoryError(code, message)
    return result.stdout.rstrip("\r\n")


def _entry_status(root: Path, relative: str) -> str:
    """Report a fixed path without following links in that path's components."""
    current = root
    for part in Path(relative).parts:
        current /= part
        if not os.path.lexists(current):
            return "absent"
        if _is_reparse(current):
            return "link_or_reparse"
    return "present"


def _path_group(root: Path, paths: Sequence[str]) -> dict[str, str]:
    return {relative: _entry_status(root, relative) for relative in paths}


def _dirty_count(status: str) -> int:
    """Count only porcelain records, never filenames or incidental command output."""
    count = 0
    for line in status.splitlines():
        if len(line) < 4 or line[2] != " ":
            raise InventoryError("GIT_STATUS_INVALID", "Git worktree status is invalid")
        count += 1
    return count


def _target_has_clean_or_process_filter(root: Path) -> bool:
    """Include all effective filter keys, including included/worktree config."""
    result = _run_git(
        root,
        ("config", "--includes", "--name-only", "--get-regexp", r"^filter\..*\.(clean|process)$"),
    )
    if result.returncode == 0:
        return bool(result.stdout.strip())
    if result.returncode == 1:
        return False
    raise InventoryError("GIT_CONFIG_UNAVAILABLE", "Git filter metadata is unavailable")


def build_inventory(target: Path) -> dict[str, Any]:
    """Collect fixed, local metadata only; no target files are modified."""
    requested = _safe_target(target)
    bare = _git_stdout(
        requested,
        ("rev-parse", "--is-bare-repository"),
        "GIT_NOT_REPOSITORY",
        "Target is not a Git repository",
    )
    if bare == "true":
        raise InventoryError("GIT_BARE_REPOSITORY", "Bare repositories are not supported")
    root_text = _git_stdout(
        requested,
        ("rev-parse", "--show-toplevel"),
        "GIT_ROOT_UNAVAILABLE",
        "Git worktree root is unavailable",
    )
    root = _safe_target(Path(root_text))
    try:
        requested.relative_to(root)
    except ValueError as error:
        raise InventoryError(
            "GIT_ROOT_UNAVAILABLE", "Git worktree root is outside the target"
        ) from error

    head = _git_stdout(
        root,
        ("rev-parse", "HEAD"),
        "GIT_HEAD_UNAVAILABLE",
        "Git HEAD is unavailable",
    )
    branch_result = _run_git(root, ("symbolic-ref", "--short", "-q", "HEAD"))
    if branch_result.returncode == 0 and branch_result.stdout.strip():
        branch = branch_result.stdout.rstrip("\r\n")
    elif branch_result.returncode == 1:
        branch = "DETACHED"
    else:
        raise InventoryError("GIT_BRANCH_UNAVAILABLE", "Git branch is unavailable")
    if _target_has_clean_or_process_filter(root):
        dirty: dict[str, bool | int | str | None] = {
            "is_dirty": None,
            "path_count": None,
            "reason": "unknown_target_clean_or_process_filter",
        }
    else:
        status = _git_stdout(
            root,
            ("status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=all"),
            "GIT_STATUS_UNAVAILABLE",
            "Git worktree status is unavailable",
        )
        dirty_count = _dirty_count(status)
        dirty = {"is_dirty": bool(dirty_count), "path_count": dirty_count}
    instructions = _path_group(root, INSTRUCTION_PATHS)
    hooks = _path_group(root, HOOK_PATHS)
    ci = _path_group(root, CI_PATHS)

    return {
        "schema_version": "1.0",
        "kind": "read_only_adoption_inventory",
        "conclusion": (
            "Inventory is not readiness, quality confirmation, authorization, or engine adoption."
        ),
        "repository": {
            "root": root.as_posix(),
            "head": head,
            "branch": branch,
            "dirty": dirty,
        },
        "fixed_path_inventory": {
            "instructions": instructions,
            "hook_conventions": hooks,
            "agent_configuration": _path_group(root, AGENT_CONFIGURATION_PATHS),
            "ci_entrypoints": ci,
            "quality_configuration": _path_group(root, QUALITY_PATHS),
            "ai_flow_assets": _path_group(root, AI_FLOW_PATHS),
        },
        "manual_mapping_required": [
            "Preserve existing instruction files and hook conventions; this tool does not install "
            "or replace them.",
            "Map target-specific test, coverage, lint, type-check, CI, and branch-protection rules "
            "before treating any workflow as a quality gate.",
            "Map Policy, templates, repository identity, task storage, and authorized execution "
            "separately before adopting the full AI Flow engine.",
            "Remote protection, hook installation/effectiveness, credentials, and authorization "
            "are not inspected.",
            "Git global/system configuration and submodule dirtiness are excluded; this is not "
            "the user's complete Git status or effective instruction configuration.",
        ],
    }


def _text_report(report: dict[str, Any]) -> str:
    repository = report["repository"]
    paths = report["fixed_path_inventory"]
    assert isinstance(repository, dict)
    assert isinstance(paths, dict)
    dirty = repository["dirty"]
    assert isinstance(dirty, dict)
    lines = [
        "Read-only adoption inventory (not readiness, quality, or authorization)",
        f"Git root: {repository['root']}",
        f"HEAD: {repository['head']}",
        f"Branch: {repository['branch']}",
        (
            f"Dirty paths: unknown ({dirty['reason']})"
            if dirty["is_dirty"] is None
            else f"Dirty paths: {dirty['path_count']}"
        ),
    ]
    for group_name, group in paths.items():
        assert isinstance(group, dict)
        lines.append(f"{group_name}:")
        lines.extend(f"  {path}: {status}" for path, status in group.items())
    lines.append("Manual mapping still required:")
    lines.extend(f"  - {item}" for item in report["manual_mapping_required"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only repository adoption inventory")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        report = build_inventory(arguments.repo)
    except InventoryError as error:
        if arguments.format == "json":
            print(json.dumps({"error": {"code": error.code, "message": error.message}}))
        else:
            print(f"inventory error [{error.code}]: {error.message}", file=sys.stderr)
        return 2
    if arguments.format == "json":
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(_text_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
