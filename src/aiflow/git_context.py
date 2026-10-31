"""Read-only Git context collection for AI Flow tasks."""

from __future__ import annotations

import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from aiflow.errors import AiflowError
from aiflow.scope import (
    ScopeAssessment,
    assess_governance_only_scope,
    assess_scope,
    collect_verification_changed_paths,
)
from aiflow.storage import TASK_ID_PATTERN

GIT_TIMEOUT_SECONDS = 10
HEAD_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class GitContext:
    """Normalized identity and version facts for one checkout."""

    repository_id: str
    repository_path: str
    branch: str
    head: str
    worktree_dirty: bool
    dirty_paths: tuple[str, ...]


@dataclass(frozen=True)
class VerificationGitBinding:
    """Immutable task version facts that a verification run must preserve."""

    repository_id: str
    branch: str
    base_commit: str
    subject_commit: str


@dataclass(frozen=True)
class VerificationGitAssessment:
    """Replayable Git boundary decision for one provisional or final verification."""

    mode: Literal["provisional", "final"]
    gate_eligible: bool
    reason_codes: tuple[str, ...]
    subject_commit: str
    attestation_head: str
    committed_scope: ScopeAssessment
    attestation_scope: ScopeAssessment
    worktree_scope: ScopeAssessment
    subject_sync_event: dict[str, object] | None


def _error(message: str, code: str, **details: object) -> AiflowError:
    return AiflowError(message, code=code, details=details)


def _run_git(cwd: Path, arguments: tuple[str, ...], *, failure_code: str) -> str:
    command = ["git", *arguments]
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise _error(
            "Git command timed out",
            "GIT_COMMAND_TIMEOUT",
            command=arguments,
            timeout_seconds=GIT_TIMEOUT_SECONDS,
        ) from error
    except OSError as error:
        raise _error("Could not run Git command", failure_code, command=arguments) from error

    if result.returncode != 0:
        raise _error(
            "Git command did not complete successfully",
            failure_code,
            command=arguments,
            returncode=result.returncode,
        )
    try:
        return result.stdout.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError as error:
        raise _error(
            "Git output is not valid UTF-8",
            "GIT_OUTPUT_INVALID",
            command=arguments,
        ) from error


def _read_repository_id(repository_root: Path) -> str:
    path = repository_root / ".ai" / "repository-id"
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise _error(
            "Repository ID is missing or unreadable",
            "GIT_REPOSITORY_ID_INVALID",
        ) from error

    lines = content.splitlines()
    if len(lines) != 1 or lines[0] != lines[0].strip():
        raise _error("Repository ID must be one canonical UUID line", "GIT_REPOSITORY_ID_INVALID")
    try:
        parsed = uuid.UUID(lines[0])
    except ValueError as error:
        raise _error("Repository ID is not a valid UUID", "GIT_REPOSITORY_ID_INVALID") from error
    if str(parsed) != lines[0] or parsed.version != 4:
        raise _error("Repository ID is not a canonical UUIDv4", "GIT_REPOSITORY_ID_INVALID")
    return lines[0]


def _read_branch(repository_root: Path) -> str:
    arguments = ("symbolic-ref", "--short", "-q", "HEAD")
    command = ["git", *arguments]
    try:
        result = subprocess.run(
            command,
            cwd=repository_root,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise _error(
            "Git command timed out",
            "GIT_COMMAND_TIMEOUT",
            command=arguments,
            timeout_seconds=GIT_TIMEOUT_SECONDS,
        ) from error
    except OSError as error:
        raise _error("Could not inspect Git branch", "GIT_BRANCH_UNAVAILABLE") from error

    if result.returncode == 1:
        return "DETACHED"
    if result.returncode != 0:
        raise _error(
            "Could not inspect Git branch",
            "GIT_BRANCH_UNAVAILABLE",
            returncode=result.returncode,
        )
    try:
        branch = result.stdout.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError as error:
        raise _error("Git branch is not valid UTF-8", "GIT_OUTPUT_INVALID") from error
    if not branch:
        raise _error("Git branch is empty", "GIT_BRANCH_UNAVAILABLE")
    return branch


def _valid_branch(branch: str) -> bool:
    return (
        bool(branch)
        and not branch.endswith(".")
        and not any(ord(char) <= 32 or ord(char) == 127 or char in "~^:?*[\\" for char in branch)
        and ".." not in branch
        and "@{" not in branch
        and all(
            part and not part.startswith(".") and not part.endswith(".lock")
            for part in branch.split("/")
        )
    )


def _normalize_status_path(path: str) -> str:
    # Porcelain -z paths are literal: quotes and " -> " are part of the filename.
    if (
        not path
        or "\\" in path
        or ":" in path
        or any(ord(char) < 32 or ord(char) == 127 for char in path)
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise _error("Git status contained an invalid path", "GIT_STATUS_INVALID")
    return path


def _parse_status(status: str) -> tuple[str, str, tuple[str, ...], bool]:
    """Validate the fixed porcelain-v2 protocol, including every changed path."""
    if not status.endswith("\0"):
        raise _error("Git status records are incomplete", "GIT_STATUS_INVALID")
    records = iter(status[:-1].split("\0"))
    headers: dict[str, str] = {}
    paths: set[str] = set()
    in_paths = False
    for record in records:
        if record.startswith("# "):
            name, separator, value = record[2:].partition(" ")
            if (
                in_paths
                or not separator
                or name not in {"branch.oid", "branch.head", "branch.upstream", "branch.ab"}
                or name in headers
            ):
                raise _error("Git status headers are invalid", "GIT_STATUS_INVALID")
            headers[name] = value
            continue
        in_paths = True
        kind = record[:1]
        if kind == "?" and record.startswith("? "):
            path = record[2:]
        elif kind in {"1", "2", "u"}:
            count = {"1": 8, "2": 9, "u": 10}[kind]
            fields = record.split(" ", maxsplit=count)
            if len(fields) != count + 1 or fields[0] != kind:
                raise _error("Git status entry is incomplete", "GIT_STATUS_INVALID")
            xy, submodule = fields[1:3]
            if (
                len(xy) != 2
                or xy == ".."
                or (
                    xy not in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
                    if kind == "u"
                    else any(char not in (".MTADRC" if kind == "2" else ".MTAD") for char in xy)
                )
                or re.fullmatch(r"N\.\.\.|S[.C][.M][.U]", submodule) is None
            ):
                raise _error("Git status flags are invalid", "GIT_STATUS_INVALID")
            modes = fields[3:7] if kind == "u" else fields[3:6]
            hashes = fields[7:10] if kind == "u" else fields[6:8]
            if any(
                mode not in {"000000", "100644", "100755", "120000", "160000"} for mode in modes
            ):
                raise _error("Git status modes are invalid", "GIT_STATUS_INVALID")
            if any(HEAD_PATTERN.fullmatch(commit) is None for commit in hashes):
                raise _error("Git status object IDs are invalid", "GIT_STATUS_INVALID")
            if kind == "2":
                score = fields[8]
                if re.fullmatch(r"[RC](?:100|[1-9]?[0-9])", score) is None or score[0] not in xy:
                    raise _error("Git status rename score is invalid", "GIT_STATUS_INVALID")
                original = next(records, "")
                _normalize_status_path(original)
            path = fields[-1]
        else:
            raise _error("Git status record is unknown", "GIT_STATUS_INVALID")
        path = _normalize_status_path(path)
        if path in paths:
            raise _error("Git status path is duplicated", "GIT_STATUS_INVALID")
        paths.add(path)

    head = headers.get("branch.oid")
    if head is None or head == "(initial)":
        raise _error("Git HEAD is unavailable", "GIT_HEAD_UNAVAILABLE")
    if HEAD_PATTERN.fullmatch(head) is None:
        raise _error("Git HEAD is not a 40-character commit", "GIT_HEAD_INVALID")
    branch = headers.get("branch.head", "")
    if branch != "(detached)" and not _valid_branch(branch):
        raise _error("Git branch is unavailable or invalid", "GIT_BRANCH_UNAVAILABLE")
    upstream = headers.get("branch.upstream")
    ahead_behind = headers.get("branch.ab")
    if (
        (upstream is not None and not _valid_branch(upstream))
        or (ahead_behind is not None and upstream is None)
        or (ahead_behind is not None and re.fullmatch(r"\+[0-9]+ -[0-9]+", ahead_behind) is None)
    ):
        raise _error("Git status tracking headers are invalid", "GIT_STATUS_INVALID")
    return head, branch, tuple(sorted(paths)), upstream is not None


def task_numbers_in_refs(repository_root: Path) -> frozenset[int]:
    """Return TASK numbers under ``.ai/tasks`` in every local and remote-tracking branch."""
    code = "GIT_TASK_REFS_UNAVAILABLE"
    refs = _run_git(
        repository_root,
        ("for-each-ref", "--format=%(objectname)", "refs/heads", "refs/remotes"),
        failure_code=code,
    )
    numbers: set[int] = set()
    for commit in sorted(set(refs.split())):
        listing = _run_git(
            repository_root,
            ("ls-tree", "--full-tree", "--name-only", commit, ".ai/tasks/"),
            failure_code=code,
        )
        for line in listing.splitlines():
            match = TASK_ID_PATTERN.fullmatch(line.rsplit("/", 1)[-1])
            if match is not None:
                numbers.add(int(match.group("number")))
    return frozenset(numbers)


def resolve_repository_root(path: Path) -> Path:
    """Locate the enclosing Git worktree without crossing a nested Git boundary."""
    requested_path = path.resolve()
    root_output = _run_git(
        requested_path,
        ("rev-parse", "--show-toplevel"),
        failure_code="GIT_NOT_REPOSITORY",
    )
    if not root_output:
        raise _error("Git repository root is empty", "GIT_NOT_REPOSITORY")
    root_path = Path(root_output)
    if not root_path.is_absolute():
        raise _error("Git repository root is not absolute", "GIT_NOT_REPOSITORY")
    repository_root = root_path.resolve()
    if not requested_path.is_relative_to(repository_root):
        raise _error("Git repository root is not an ancestor of the directory", "GIT_ROOT_INVALID")
    directory = requested_path
    while directory != repository_root:
        marker = directory / ".git"
        if marker.is_file() or marker.is_dir():
            raise _error("Git repository root crosses a nested Git boundary", "GIT_ROOT_INVALID")
        directory = directory.parent
    return repository_root


def collect_git_context(path: Path) -> GitContext:
    """Collect normalized repository facts without reading business file contents."""
    repository_root = resolve_repository_root(path)
    repository_id = _read_repository_id(repository_root)

    status = _run_git(
        repository_root,
        ("status", "--porcelain=v2", "--branch", "--no-show-stash", "-z", "--untracked-files=all"),
        failure_code="GIT_STATUS_UNAVAILABLE",
    )
    head, status_branch, dirty_paths, has_upstream = _parse_status(status)
    # Git's --short spelling may include heads/ or refs/heads/ when tags collide.
    # Keep that existing fact instead of implementing Git's abbreviation algorithm.
    branch = _read_branch(repository_root)
    expected_branches = {status_branch, f"heads/{status_branch}", f"refs/heads/{status_branch}"}
    if status_branch == "(detached)":
        # A real branch may be named "(detached)"; symbolic-ref disambiguates it.
        expected_branches.add("DETACHED")
        if branch == "DETACHED" and has_upstream:
            raise _error("Detached HEAD cannot have an upstream", "GIT_STATUS_INVALID")
    if branch not in expected_branches:
        raise _error("Git branch observations do not agree", "GIT_BRANCH_UNAVAILABLE")
    return GitContext(
        repository_id=repository_id,
        repository_path=repository_root.as_posix(),
        branch=branch,
        head=head,
        worktree_dirty=bool(dirty_paths),
        dirty_paths=dirty_paths,
    )


def _is_ancestor(repository_root: Path, ancestor: str, descendant: str) -> bool:
    if HEAD_PATTERN.fullmatch(ancestor) is None or HEAD_PATTERN.fullmatch(descendant) is None:
        return False
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repository_root,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def commits_are_ancestral(
    repository_root: Path, *, base_commit: str, subject_commit: str, head_commit: str
) -> bool:
    """Require the fixed verification chain base -> subject -> observed HEAD."""
    return _is_ancestor(repository_root, base_commit, subject_commit) and _is_ancestor(
        repository_root, subject_commit, head_commit
    )


def evaluate_verification_git_context(
    repository_root: Path,
    *,
    task_id: str,
    allowed_scope: tuple[str, ...],
    binding: VerificationGitBinding,
    mode: Literal["provisional", "final"],
) -> VerificationGitAssessment:
    """Assess a verification snapshot without mutating task state or Git history."""
    if mode not in {"provisional", "final"}:
        raise _error("Verification mode is invalid", "VERIFY_MODE_INVALID")
    context = collect_git_context(repository_root)
    reasons: list[str] = []
    if context.repository_id != binding.repository_id:
        reasons.append("VERIFY_REPOSITORY_CHANGED")
    if context.branch != binding.branch:
        reasons.append("VERIFY_BRANCH_CHANGED")
    if not _is_ancestor(Path(context.repository_path), binding.base_commit, context.head):
        reasons.append("VERIFY_BASE_UNREACHABLE")

    initial_changes = collect_verification_changed_paths(
        Path(context.repository_path),
        base_commit=binding.base_commit,
        subject_commit=binding.subject_commit,
        head_commit=context.head,
    )
    committed_scope = assess_scope(
        initial_changes.committed,
        allowed_scope,
        task_id=task_id,
        repository_root=Path(context.repository_path),
        cache_patterns=(),
    )
    attestation_scope = assess_governance_only_scope(
        initial_changes.attestation,
        task_id=task_id,
        repository_root=Path(context.repository_path),
    )
    worktree_scope = assess_governance_only_scope(
        initial_changes.worktree,
        task_id=task_id,
        repository_root=Path(context.repository_path),
    )
    subject = binding.subject_commit
    sync_candidate = False
    if mode == "final" and not attestation_scope.passed:
        sync_candidate = any(
            not path.startswith(".ai/tasks/") for path in attestation_scope.out_of_scope
        )
        if sync_candidate:
            subject = context.head
            candidate_changes = collect_verification_changed_paths(
                Path(context.repository_path),
                base_commit=binding.base_commit,
                subject_commit=subject,
                head_commit=context.head,
            )
            committed_scope = assess_scope(
                candidate_changes.committed,
                allowed_scope,
                task_id=task_id,
                repository_root=Path(context.repository_path),
                cache_patterns=(),
            )
    if mode == "provisional":
        reasons.append("VERIFY_PROVISIONAL_NOT_GATE")
    else:
        if not committed_scope.passed or (not sync_candidate and not attestation_scope.passed):
            reasons.append("VERIFY_SCOPE_EXCEEDED")
        if not worktree_scope.passed:
            reasons.append("VERIFY_WORKTREE_DIRTY")

    ordered = tuple(sorted(set(reasons)))
    synchronized = mode == "final" and sync_candidate and not ordered and subject == context.head
    event: dict[str, object] | None = (
        {
            "event_type": "subject_commit_synchronized",
            "old_subject_commit": binding.subject_commit,
            "new_subject_commit": context.head,
            "base_commit": binding.base_commit,
            "repository_id": context.repository_id,
            "branch": context.branch,
            "observed_head": context.head,
            "mode": mode,
        }
        if synchronized
        else None
    )
    return VerificationGitAssessment(
        mode=mode,
        gate_eligible=mode == "final" and not ordered,
        reason_codes=ordered,
        subject_commit=subject,
        attestation_head=context.head,
        committed_scope=committed_scope,
        attestation_scope=attestation_scope,
        worktree_scope=worktree_scope,
        subject_sync_event=event,
    )
