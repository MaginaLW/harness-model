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


def _normalize_status_path(raw_path: str) -> str:
    path = raw_path.rsplit(" -> ", maxsplit=1)[-1]
    if len(path) >= 2 and path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    normalized = path.replace("\\", "/")
    candidate = Path(normalized)
    if not normalized or candidate.is_absolute() or ".." in candidate.parts:
        raise _error("Git status contained an invalid path", "GIT_STATUS_INVALID")
    return normalized


def _dirty_paths(status: str) -> tuple[str, ...]:
    paths: set[str] = set()
    for line in status.splitlines():
        if len(line) < 4 or line[2] != " ":
            raise _error("Git status output is invalid", "GIT_STATUS_INVALID")
        paths.add(_normalize_status_path(line[3:]))
    return tuple(sorted(paths))


def collect_git_context(path: Path) -> GitContext:
    """Collect normalized repository facts without reading business file contents."""
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
    repository_id = _read_repository_id(repository_root)

    head = _run_git(
        repository_root,
        ("rev-parse", "HEAD"),
        failure_code="GIT_HEAD_UNAVAILABLE",
    )
    if HEAD_PATTERN.fullmatch(head) is None:
        raise _error("Git HEAD is not a 40-character commit", "GIT_HEAD_INVALID")

    branch = _read_branch(repository_root)
    status = _run_git(
        repository_root,
        ("status", "--porcelain=v1", "--untracked-files=all"),
        failure_code="GIT_STATUS_UNAVAILABLE",
    )
    dirty_paths = _dirty_paths(status)
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
