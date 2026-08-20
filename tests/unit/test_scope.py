"""Segment-aware scope, change collection, and AUTO preflight tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aiflow.errors import ContractError
from aiflow.scope import (
    AutoPreflightFacts,
    ScopeAssessment,
    assess_auto_scope,
    assess_scope,
    collect_changed_paths,
    evaluate_auto_preflight,
    forbidden_action_present,
    matches_scope,
    normalize_repository_path,
    resolve_repository_path,
)


@pytest.mark.parametrize("path", ["/absolute/file", "C:\\absolute\\file", "src/../secret.py"])
def test_normalization_rejects_absolute_and_parent_paths(path: str) -> None:
    with pytest.raises(ContractError):
        normalize_repository_path(path)


def test_segment_aware_globs_do_not_use_prefix_matching() -> None:
    assert matches_scope("src/module.py", "src/*") is True
    assert matches_scope("src/nested/module.py", "src/*") is False
    assert matches_scope("src/nested/module.py", "src/**") is True
    assert matches_scope("srcevil/module.py", "src/**") is False


def test_forbidden_actions_use_normalized_single_source_semantics() -> None:
    assert forbidden_action_present(["Deploy"], [" deploy "]) is True
    assert forbidden_action_present(["Deploy"], ["notify"]) is False


def test_scope_allows_current_governance_but_not_other_task_governance() -> None:
    result = assess_scope(
        ["src/module.py", ".ai/tasks/TASK-0001/events.jsonl", ".ai/tasks/TASK-0002/task.yaml"],
        ["src/**"],
        task_id="TASK-0001",
    )
    assert result.allowed == (".ai/tasks/TASK-0001/events.jsonl", "src/module.py")
    assert result.out_of_scope == (".ai/tasks/TASK-0002/task.yaml",)


def test_scope_excludes_only_explicit_caches() -> None:
    result = assess_scope(
        [".pytest_cache/v/cache/nodeids", "src/module.py", "tmp/cache.txt"],
        ["src/**"],
        task_id="TASK-0001",
    )
    assert result.ignored == (".pytest_cache/v/cache/nodeids",)
    assert result.out_of_scope == ("tmp/cache.txt",)


def test_auto_scope_uses_union_of_units_within_task_scope_and_is_case_sensitive() -> None:
    result = assess_auto_scope(
        ["src/a.py", "docs/a.md", "SRC/wrong.py", "tests/outside.py"],
        ["src/**", "docs/**", "tests/**"],
        [["src/**"], ["docs/**"]],
        task_id="TASK-0001",
    )
    assert result.allowed == ("docs/a.md", "src/a.py")
    assert result.out_of_scope == ("SRC/wrong.py", "tests/outside.py")


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ContractError) as caught:
        resolve_repository_path(root, "link/secret.txt")
    assert caught.value.code == "SCOPE_PATH_ESCAPE"


def test_change_collection_includes_commit_and_worktree_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import scope

    responses = [
        b"M\0src/committed.py\0R100\0src/renamed-old.py\0src/renamed-new.py\0",
        b"M\0.ai/tasks/TASK-0001/approvals.json\0",
        b" M src/tracked.py\0?? src/untracked.py\0R  src/new.py\0src/old.py\0",
    ]

    def fake_run(_root: Path, _arguments: object) -> bytes:
        return responses.pop(0)

    monkeypatch.setattr(scope, "_run_git", fake_run)
    changed = collect_changed_paths(
        tmp_path,
        base_commit="a" * 40,
        subject_commit="b" * 40,
        head_commit="c" * 40,
    )
    assert changed.paths == (
        ".ai/tasks/TASK-0001/approvals.json",
        "src/committed.py",
        "src/new.py",
        "src/old.py",
        "src/renamed-new.py",
        "src/renamed-old.py",
        "src/tracked.py",
        "src/untracked.py",
    )


def test_change_collection_preserves_deleted_and_both_rename_paths(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    def git(*arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            capture_output=True,
            check=True,
            encoding="utf-8",
            timeout=10,
        )
        return result.stdout.strip()

    git("init", "-b", "main")
    (repository / "src").mkdir()
    (repository / "docs").mkdir()
    (repository / "src" / "old.py").write_text("content\n", encoding="utf-8")
    (repository / "docs" / "deleted.md").write_text("delete\n", encoding="utf-8")
    (repository / "src" / "tracked.py").write_text("before\n", encoding="utf-8")
    git("add", ".")
    git(
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "base",
    )
    base = git("rev-parse", "HEAD")
    git("mv", "src/old.py", "src/new.py")
    git("rm", "docs/deleted.md")
    git(
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-am",
        "rename and delete",
    )
    subject = git("rev-parse", "HEAD")
    (repository / "src" / "tracked.py").write_text("after\n", encoding="utf-8")
    (repository / "src" / "untracked.py").write_text("new\n", encoding="utf-8")

    changed = collect_changed_paths(
        repository,
        base_commit=base,
        subject_commit=subject,
        head_commit=subject,
    )
    assert changed.paths == (
        "docs/deleted.md",
        "src/new.py",
        "src/old.py",
        "src/tracked.py",
        "src/untracked.py",
    )


def test_auto_preflight_requires_all_guardrails_in_safety_order() -> None:
    result = evaluate_auto_preflight(
        AutoPreflightFacts(
            unfinished_routes=("AUTO", "REVIEW"),
            specification_frozen=False,
            required_approvals_present=True,
            forbidden_actions_present=True,
            scope=ScopeAssessment((), ("outside.txt",), ()),
            verification_complete=False,
        )
    )
    assert result.failure_codes == (
        "AUTO_FORBIDDEN_ACTION",
        "AUTO_SCOPE_EXCEEDED",
        "AUTO_ROUTE_REQUIRED",
        "AUTO_SPEC_NOT_FROZEN",
        "AUTO_APPROVAL_REQUIRED",
        "AUTO_VERIFICATION_INCOMPLETE",
    )
