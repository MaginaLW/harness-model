from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.ci.route_pr import classify_pr, main


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.email", "ci@example.invalid")
    _git(root, "config", "user.name", "CI")
    (root / ".ai").mkdir()
    (root / ".ai" / "repository-id").write_text("repo-stable\n", encoding="utf-8")
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "initial base")
    base = _git(root, "rev-parse", "HEAD")
    return root, base


def test_classify_pr_task_free_when_no_checklist_files_modified(tmp_path: Path) -> None:
    root, base = _init_repo(tmp_path)
    _git(root, "checkout", "-b", "feature")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("documentation\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_example.py").write_text("def test_foo(): pass\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "docs and test additions")
    head = _git(root, "rev-parse", "HEAD")

    category, task_id, bootstrap_active = classify_pr(root, base, head)
    assert category == "task_free"
    assert task_id is None
    assert bootstrap_active is False


def test_classify_pr_task_closeout_when_only_merged_task_modified(tmp_path: Path) -> None:
    root, base = _init_repo(tmp_path)
    _git(root, "checkout", "-b", "closeout")
    task_dir = root / ".ai" / "tasks" / "TASK-0042"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text("current_state: MERGED\n", encoding="utf-8")
    (task_dir / "events.jsonl").write_text('{"event_type": "merge_recorded"}\n', encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "log.md").write_text("updated log\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "record closeout")
    head = _git(root, "rev-parse", "HEAD")

    category, task_id, bootstrap_active = classify_pr(root, base, head)
    assert category == "task_closeout"
    assert task_id == "TASK-0042"
    assert bootstrap_active is False


def test_classify_pr_formal_governed_when_task_not_merged(tmp_path: Path) -> None:
    root, base = _init_repo(tmp_path)
    _git(root, "checkout", "-b", "in-progress")
    task_dir = root / ".ai" / "tasks" / "TASK-0042"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text("current_state: READY_TO_IMPLEMENT\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "task in progress")
    head = _git(root, "rev-parse", "HEAD")

    category, task_id, bootstrap_active = classify_pr(root, base, head)
    assert category == "formal_governed"
    assert task_id == "TASK-0042"
    assert bootstrap_active is False


@pytest.mark.parametrize(
    "modified_file",
    [
        "src/aiflow/core.py",
        ".github/workflows/ci.yml",
        "tools/ci/check.py",
        "AGENTS.md",
        "CLAUDE.md",
        "pyproject.toml",
        "uv.lock",
        ".gitignore",
        ".gitattributes",
        ".ai/policy/hard-rules.yaml",
    ],
)
def test_classify_pr_formal_governed_on_checklist_modifications(
    tmp_path: Path, modified_file: str
) -> None:
    root, base = _init_repo(tmp_path)
    _git(root, "checkout", "-b", "code-change")
    target = root / modified_file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("change\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "modify checklist file")
    head = _git(root, "rev-parse", "HEAD")

    category, task_id, _ = classify_pr(root, base, head)
    assert category == "formal_governed"


def test_classify_pr_detects_bootstrap_mode(tmp_path: Path) -> None:
    root, _ = _init_repo(tmp_path)
    (root / ".ai" / "bootstrap-mode.yaml").write_text(
        "mode: bootstrap_auto\nstatus: active\n", encoding="utf-8"
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "activate bootstrap")
    active_base = _git(root, "rev-parse", "HEAD")

    _git(root, "checkout", "-b", "task-free-branch")
    (root / "docs").mkdir()
    (root / "docs" / "doc.md").write_text("doc\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "doc update")
    head = _git(root, "rev-parse", "HEAD")

    category, task_id, bootstrap_active = classify_pr(root, active_base, head)
    assert category == "task_free"
    assert bootstrap_active is True


def test_route_pr_cli_main_with_output_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base = _init_repo(tmp_path)
    _git(root, "checkout", "-b", "closeout-cli")
    task_dir = root / ".ai" / "tasks" / "TASK-0099"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text("current_state: MERGED\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "closeout")
    head = _git(root, "rev-parse", "HEAD")

    monkeypatch.chdir(root)
    output_file = tmp_path / "github_output.txt"
    exit_code = main(["--base", base, "--head", head, "--output", str(output_file)])
    assert exit_code == 0
    lines = output_file.read_text(encoding="utf-8").splitlines()
    assert "category=task_closeout" in lines
    assert "bootstrap_active=false" in lines
    assert "task_id=TASK-0099" in lines
