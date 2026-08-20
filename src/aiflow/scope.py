"""Read-only scope guards and AUTO preflight facts."""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Sequence

from aiflow.errors import ContractError, StorageError

DEFAULT_CACHE_PATTERNS = frozenset(
    {
        ".pytest_cache/**",
        ".mypy_cache/**",
        ".ruff_cache/**",
        "**/__pycache__/**",
        "**/*.pyc",
        ".coverage",
    }
)
_PREFLIGHT_PRIORITY = {
    "AUTO_FORBIDDEN_ACTION": 10,
    "AUTO_SCOPE_EXCEEDED": 20,
    "AUTO_ROUTE_REQUIRED": 30,
    "AUTO_SPEC_NOT_FROZEN": 40,
    "AUTO_APPROVAL_REQUIRED": 50,
    "AUTO_VERIFICATION_INCOMPLETE": 60,
}


@dataclass(frozen=True)
class ScopeAssessment:
    """A deterministic split of changed paths by scope and explicit cache exclusions."""

    allowed: tuple[str, ...]
    out_of_scope: tuple[str, ...]
    ignored: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.out_of_scope


@dataclass(frozen=True)
class ChangedPaths:
    """Normalized paths observed in committed and worktree change sources."""

    paths: tuple[str, ...]


@dataclass(frozen=True)
class AutoPreflightFacts:
    """Facts a caller collects before allowing an AUTO command to proceed."""

    unfinished_routes: tuple[str, ...]
    specification_frozen: bool
    required_approvals_present: bool
    forbidden_actions_present: bool
    scope: ScopeAssessment
    verification_complete: bool


@dataclass(frozen=True)
class AutoPreflightResult:
    """Safety-sorted AUTO gate result."""

    passed: bool
    failure_codes: tuple[str, ...]


def normalize_repository_path(path: str) -> str:
    """Return one relative POSIX path or reject traversal and absolute inputs."""
    if not isinstance(path, str) or not path.strip():
        raise ContractError("Repository path is invalid", code="SCOPE_PATH_INVALID")
    raw = path.replace("\\", "/")
    if raw.startswith("/") or PureWindowsPath(path).is_absolute():
        raise ContractError("Repository path must be relative", code="SCOPE_PATH_ABSOLUTE")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ContractError("Repository path is invalid", code="SCOPE_PATH_INVALID")
    return "/".join(parts)


def resolve_repository_path(repository_root: Path, path: str) -> Path:
    """Resolve a relative path and reject a symlink that escapes the repository."""
    normalized = normalize_repository_path(path)
    root = repository_root.resolve()
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ContractError(
            "Repository path escapes through a symlink", code="SCOPE_PATH_ESCAPE"
        ) from error
    return candidate


def _matches_parts(pattern: tuple[str, ...], path: tuple[str, ...]) -> bool:
    if not pattern:
        return not path
    head, *tail = pattern
    remainder = tuple(tail)
    if head == "**":
        return any(_matches_parts(remainder, path[index:]) for index in range(len(path) + 1))
    return bool(path) and fnmatch.fnmatchcase(path[0], head) and _matches_parts(remainder, path[1:])


def matches_scope(path: str, pattern: str) -> bool:
    """Match explicit POSIX glob segments; '*' never crosses a directory boundary."""
    normalized_path = normalize_repository_path(path)
    normalized_pattern = normalize_repository_path(pattern)
    return _matches_parts(tuple(normalized_pattern.split("/")), tuple(normalized_path.split("/")))


def is_task_governance_path(path: str, task_id: str) -> bool:
    """Permit only the current task's governance records as a system exception."""
    return matches_scope(path, f".ai/tasks/{task_id}/**")


def assess_scope(
    paths: Sequence[str],
    allowed_scope: Sequence[str],
    *,
    task_id: str,
    repository_root: Path | None = None,
    cache_patterns: Sequence[str] = tuple(DEFAULT_CACHE_PATTERNS),
) -> ScopeAssessment:
    """Classify paths against allowed scope, current-task governance, and known caches."""
    allowed: set[str] = set()
    out_of_scope: set[str] = set()
    ignored: set[str] = set()
    normalized_patterns = tuple(normalize_repository_path(pattern) for pattern in allowed_scope)
    if not normalized_patterns:
        raise ContractError("Allowed scope is required", code="SCOPE_ALLOWED_EMPTY")
    normalized_caches = tuple(normalize_repository_path(pattern) for pattern in cache_patterns)
    for raw_path in paths:
        try:
            path = normalize_repository_path(raw_path)
            if repository_root is not None:
                candidate = repository_root / path
                if candidate.exists() or candidate.is_symlink():
                    resolve_repository_path(repository_root, path)
        except ContractError:
            out_of_scope.add(str(raw_path).replace("\\", "/"))
            continue
        if any(matches_scope(path, pattern) for pattern in normalized_caches):
            ignored.add(path)
        elif is_task_governance_path(path, task_id) or any(
            matches_scope(path, pattern) for pattern in normalized_patterns
        ):
            allowed.add(path)
        else:
            out_of_scope.add(path)
    return ScopeAssessment(
        tuple(sorted(allowed)), tuple(sorted(out_of_scope)), tuple(sorted(ignored))
    )


def assess_auto_scope(
    paths: Sequence[str],
    task_scope: Sequence[str],
    unit_scopes: Sequence[Sequence[str]],
    *,
    task_id: str,
    repository_root: Path | None = None,
) -> ScopeAssessment:
    """Require every business path to match task scope and at least one AUTO unit scope."""
    task = assess_scope(
        paths,
        task_scope,
        task_id=task_id,
        repository_root=repository_root,
    )
    unit = assess_scope(
        paths,
        tuple(pattern for patterns in unit_scopes for pattern in patterns),
        task_id=task_id,
        repository_root=repository_root,
    )
    return ScopeAssessment(
        allowed=tuple(sorted(set(task.allowed) & set(unit.allowed))),
        out_of_scope=tuple(sorted(set(task.out_of_scope) | set(unit.out_of_scope))),
        ignored=tuple(sorted(set(task.ignored) | set(unit.ignored))),
    )


def _run_git(root: Path, arguments: Sequence[str]) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=root, capture_output=True, check=False, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise StorageError(
            "Could not collect Git scope changes", code="SCOPE_GIT_UNAVAILABLE"
        ) from error
    if result.returncode != 0:
        raise StorageError("Could not collect Git scope changes", code="SCOPE_GIT_UNAVAILABLE")
    return result.stdout


def _nul_paths(output: bytes) -> set[str]:
    try:
        values = output.decode("utf-8").split("\0")
    except UnicodeDecodeError as error:
        raise StorageError(
            "Git scope output is invalid", code="SCOPE_GIT_OUTPUT_INVALID"
        ) from error
    return {normalize_repository_path(value) for value in values if value}


def _diff_paths(output: bytes) -> set[str]:
    """Parse ``git diff --name-status -z``, preserving both rename/copy paths."""
    try:
        records = output.decode("utf-8").split("\0")
    except UnicodeDecodeError as error:
        raise StorageError(
            "Git scope output is invalid", code="SCOPE_GIT_OUTPUT_INVALID"
        ) from error
    paths: set[str] = set()
    index = 0
    while index < len(records):
        status = records[index]
        index += 1
        if not status:
            continue
        if status[0] not in "ACDMRTUXB" or index >= len(records) or not records[index]:
            raise StorageError("Git scope output is invalid", code="SCOPE_GIT_OUTPUT_INVALID")
        paths.add(normalize_repository_path(records[index]))
        index += 1
        if status[0] in {"R", "C"}:
            if index >= len(records) or not records[index]:
                raise StorageError("Git scope output is invalid", code="SCOPE_GIT_OUTPUT_INVALID")
            paths.add(normalize_repository_path(records[index]))
            index += 1
    return paths


def _status_paths(output: bytes) -> set[str]:
    try:
        records = output.decode("utf-8").split("\0")
    except UnicodeDecodeError as error:
        raise StorageError(
            "Git scope output is invalid", code="SCOPE_GIT_OUTPUT_INVALID"
        ) from error
    paths: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise StorageError("Git scope output is invalid", code="SCOPE_GIT_OUTPUT_INVALID")
        status, path = record[:2], record[3:]
        paths.add(normalize_repository_path(path))
        if "R" in status or "C" in status:
            if index >= len(records) or not records[index]:
                raise StorageError("Git scope output is invalid", code="SCOPE_GIT_OUTPUT_INVALID")
            paths.add(normalize_repository_path(records[index]))
            index += 1
    return paths


def collect_changed_paths(
    repository_root: Path,
    *,
    base_commit: str,
    subject_commit: str,
    head_commit: str | None = None,
) -> ChangedPaths:
    """Collect committed, attestation, tracked, untracked, deleted, and renamed paths."""
    root = repository_root.resolve()
    committed = _diff_paths(
        _run_git(
            root,
            ("diff", "--name-status", "-z", "--find-renames", base_commit, subject_commit),
        )
    )
    if head_commit is not None and head_commit != subject_commit:
        committed.update(
            _diff_paths(
                _run_git(
                    root,
                    (
                        "diff",
                        "--name-status",
                        "-z",
                        "--find-renames",
                        subject_commit,
                        head_commit,
                    ),
                )
            )
        )
    worktree = _status_paths(
        _run_git(root, ("status", "--porcelain=v1", "-z", "--untracked-files=all"))
    )
    return ChangedPaths(tuple(sorted(committed | worktree)))


def evaluate_auto_preflight(facts: AutoPreflightFacts) -> AutoPreflightResult:
    """Reject AUTO work unless every routing, spec, scope, permission, and V check passes."""
    failures: list[str] = []
    if facts.forbidden_actions_present:
        failures.append("AUTO_FORBIDDEN_ACTION")
    if not facts.scope.passed:
        failures.append("AUTO_SCOPE_EXCEEDED")
    if not facts.unfinished_routes or any(route != "AUTO" for route in facts.unfinished_routes):
        failures.append("AUTO_ROUTE_REQUIRED")
    if not facts.specification_frozen:
        failures.append("AUTO_SPEC_NOT_FROZEN")
    if facts.required_approvals_present:
        failures.append("AUTO_APPROVAL_REQUIRED")
    if not facts.verification_complete:
        failures.append("AUTO_VERIFICATION_INCOMPLETE")
    ordered = tuple(sorted(set(failures), key=lambda code: (_PREFLIGHT_PRIORITY[code], code)))
    return AutoPreflightResult(passed=not ordered, failure_codes=ordered)
