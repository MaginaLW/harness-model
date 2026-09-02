"""Repository-level regression coverage for narrowly scoped hygiene rules."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = ROOT / ".gitignore"
RECOVERY = ROOT / "docs" / "operations" / "recovery.md"


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", "--", path],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode in (0, 1), result.stderr
    return result.returncode == 0


def test_generated_artifacts_are_ignored_only_at_repository_root() -> None:
    for root_path in (
        "build/output.txt",
        "dist/package.whl",
        "htmlcov/index.html",
        ".coverage.unit",
    ):
        assert _is_ignored(root_path), root_path

    for nested_path in (
        "package/build/output.txt",
        "package/dist/package.whl",
        "package/htmlcov/index.html",
        "package/.coverage.unit",
    ):
        assert not _is_ignored(nested_path), nested_path


def test_task_local_logs_keep_a_single_dedicated_ignore_rule() -> None:
    lines = GITIGNORE.read_text(encoding="utf-8").splitlines()
    log_rules = [line for line in lines if "logs" in line and not line.lstrip().startswith("#")]

    assert log_rules == ["/.ai/tasks/*/logs/"]
    assert _is_ignored(".ai/tasks/TASK-0032/logs/run-1/pytest.stdout.log")


def test_generic_logs_and_xml_reports_remain_visible_to_git() -> None:
    assert not _is_ignored("notes/run.log")
    assert not _is_ignored("reports/result.xml")
    assert "*.log" not in GITIGNORE.read_text(encoding="utf-8")
    assert "*.xml" not in GITIGNORE.read_text(encoding="utf-8")


def test_task_audit_evidence_is_never_ignored() -> None:
    """The ledger must stay visible whatever ignore rules the repository grows."""
    for audit_path in (
        ".ai/tasks/TASK-0000/task.yaml",
        ".ai/tasks/TASK-0000/events.jsonl",
        ".ai/tasks/TASK-0000/spec.md",
        ".ai/tasks/TASK-0000/evidence.json",
        ".ai/tasks/TASK-0000/approvals.json",
        ".ai/tasks/TASK-0000/classification.json",
        ".ai/tasks/TASK-0000/reviews/REV-0000-r0001.json",
        ".ai/tasks/TASK-0000/review-contexts/context.json",
        ".ai/tasks/TASK-0000/verifier-contexts/context.json",
    ):
        assert not _is_ignored(audit_path), audit_path


def test_ledger_extensions_are_never_ignored_globally() -> None:
    """A broad extension rule would hide the ledger without tripping any path check."""
    text = GITIGNORE.read_text(encoding="utf-8")

    for pattern in ("*.json", "*.jsonl", "*.yaml", "*.yml", "*.md"):
        assert pattern not in text, pattern


def test_recovery_document_sets_evidence_and_path_boundaries() -> None:
    text = RECOVERY.read_text(encoding="utf-8")

    assert "运行时证据、精确清理与路径边界" in text
    assert "唯一的 task-local 忽略规则" in text
    assert "精确 task、run 和文件" in text
    assert "不作跨 clone 或新 worktree 的持久性承诺" in text
    assert "OS 临时运行目录" in text
    assert "不得用宽泛的 `*.log`、`*.xml`" in text
    assert "不改写它们" in text
    assert "当前 CLI 生成的 task、evidence、action 或 snapshot" in text
    assert "事后替换这些记录中的路径" in text
    assert "${REPO_ROOT}" in text
    assert "${TEMP_ROOT}" in text
