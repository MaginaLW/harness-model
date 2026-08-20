"""End-to-end Git boundary checks for provisional and final verification snapshots."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aiflow.git_context import (
    VerificationGitBinding,
    evaluate_verification_git_context,
)

REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"
TASK_ID = "TASK-0001"


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=True,
        encoding="utf-8",
        timeout=10,
    )
    return result.stdout.rstrip("\r\n")


def commit(repository: Path, message: str) -> str:
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        message,
    )
    return git(repository, "rev-parse", "HEAD")


def repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    git(root, "init", "-b", "main")
    (root / ".ai").mkdir()
    (root / ".ai" / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "module.py").write_text("value = 1\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "outside.md").write_text("outside\n", encoding="utf-8")
    return root, commit(root, "base")


def binding(base: str) -> VerificationGitBinding:
    return VerificationGitBinding(REPOSITORY_ID, "main", base, base)


def evaluate(root: Path, base: str, *, mode: str = "final"):
    return evaluate_verification_git_context(
        root,
        task_id=TASK_ID,
        allowed_scope=("src/**",),
        binding=binding(base),
        mode=mode,  # type: ignore[arg-type]
    )


def test_clean_final_syncs_current_head_and_is_gate_eligible(tmp_path: Path) -> None:
    root, base = repository(tmp_path)
    (root / "src" / "module.py").write_text("value = 2\n", encoding="utf-8")
    subject = commit(root, "scoped change")

    result = evaluate(root, base)

    assert result.gate_eligible is True
    assert result.subject_commit == subject
    assert result.attestation_head == subject
    assert result.subject_sync_event == {
        "event_type": "subject_commit_synchronized",
        "old_subject_commit": base,
        "new_subject_commit": subject,
        "base_commit": base,
        "repository_id": REPOSITORY_ID,
        "branch": "main",
        "observed_head": subject,
        "mode": "final",
    }


def test_governance_attestation_keeps_existing_subject_without_sync(tmp_path: Path) -> None:
    root, base = repository(tmp_path)
    (root / "src" / "module.py").write_text("value = 2\n", encoding="utf-8")
    subject = commit(root, "scoped code")
    (root / ".ai" / "tasks" / TASK_ID).mkdir(parents=True)
    (root / ".ai" / "tasks" / TASK_ID / "evidence.json").write_text("{}\n", encoding="utf-8")
    attestation_head = commit(root, "task evidence")

    result = evaluate_verification_git_context(
        root,
        task_id=TASK_ID,
        allowed_scope=("src/**",),
        binding=VerificationGitBinding(REPOSITORY_ID, "main", base, subject),
        mode="final",
    )

    assert result.gate_eligible is True
    assert result.subject_commit == subject
    assert result.attestation_head == attestation_head
    assert result.attestation_scope.passed is True
    assert result.subject_sync_event is None


def test_provisional_never_gates_while_final_rejects_business_worktree(tmp_path: Path) -> None:
    root, base = repository(tmp_path)
    (root / "src" / "module.py").write_text("dirty\n", encoding="utf-8")

    provisional = evaluate(root, base, mode="provisional")
    final = evaluate(root, base)

    assert provisional.gate_eligible is False
    assert provisional.reason_codes == ("VERIFY_PROVISIONAL_NOT_GATE",)
    assert final.gate_eligible is False
    assert final.reason_codes == ("VERIFY_WORKTREE_DIRTY",)


def test_final_rejects_rename_delete_and_other_task_governance(tmp_path: Path) -> None:
    root, base = repository(tmp_path)
    git(root, "mv", "src/module.py", "docs/module.py")
    commit(root, "rename outside scope")
    renamed = evaluate(root, base)
    assert renamed.gate_eligible is False
    assert "VERIFY_SCOPE_EXCEEDED" in renamed.reason_codes
    assert renamed.committed_scope.out_of_scope == ("docs/module.py",)
    assert renamed.committed_scope.allowed == ("src/module.py",)

    git(root, "rm", "docs/outside.md")
    commit(root, "delete outside scope")
    deleted = evaluate(root, base)
    assert "VERIFY_SCOPE_EXCEEDED" in deleted.reason_codes
    assert deleted.committed_scope.out_of_scope == ("docs/module.py", "docs/outside.md")

    (root / ".ai" / "tasks" / "TASK-0002").mkdir(parents=True)
    (root / ".ai" / "tasks" / "TASK-0002" / "events.jsonl").write_text("{}\n", encoding="utf-8")
    governance = evaluate(root, base)
    assert governance.gate_eligible is False
    assert governance.worktree_scope.out_of_scope == (".ai/tasks/TASK-0002/events.jsonl",)


def test_final_rejects_branch_base_and_symlink_escape(tmp_path: Path) -> None:
    root, base = repository(tmp_path)
    git(root, "switch", "-c", "other")
    branch_changed = evaluate(root, base)
    assert "VERIFY_BRANCH_CHANGED" in branch_changed.reason_codes

    git(root, "checkout", "--orphan", "unrelated")
    git(root, "rm", "-rf", ".")
    (root / ".ai").mkdir(exist_ok=True)
    (root / ".ai" / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "module.py").write_text("unrelated\n", encoding="utf-8")
    commit(root, "unrelated")
    unreachable = evaluate(root, base)
    assert "VERIFY_BASE_UNREACHABLE" in unreachable.reason_codes

    root, base = repository(tmp_path / "symlink")
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / ".ai" / "tasks").mkdir()
        (root / ".ai" / "tasks" / TASK_ID).symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    escaped = evaluate(root, base)
    assert escaped.gate_eligible is False
    assert escaped.worktree_scope.out_of_scope == (f".ai/tasks/{TASK_ID}",)
