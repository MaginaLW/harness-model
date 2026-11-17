from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from aiflow.errors import ContractError
from aiflow.task_service import TaskRecord
from tools.ci.verify_closeout import main, verify_closeout

ROOT = Path(__file__).resolve().parents[2]


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


def _setup_repo_and_merged_commits(tmp_path: Path) -> tuple[Path, str, str, str]:
    """Set up repo with base commit, feature commit (subject), and a 2-parent merge commit."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.email", "ci@example.invalid")
    _git(root, "config", "user.name", "CI")
    (root / ".ai").mkdir()
    shutil.copytree(ROOT / ".ai" / "schemas", root / ".ai" / "schemas")

    repo_id = (ROOT / ".ai" / "repository-id").read_text(encoding="utf-8")
    (root / ".ai" / "repository-id").write_text(repo_id, encoding="utf-8")
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base commit")
    base_commit = _git(root, "rev-parse", "HEAD")

    # Feature branch (subject)
    _git(root, "checkout", "-b", "feature", base_commit)
    (root / "feature.txt").write_text("feature content\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "feature subject commit")
    subject_commit = _git(root, "rev-parse", "HEAD")

    # Main branch merges feature with --no-ff
    _git(root, "checkout", "master" if "master" in _git(root, "branch") else "main")
    _git(root, "merge", "--no-ff", "-m", "Merge feature into main", subject_commit)
    merge_commit = _git(root, "rev-parse", "HEAD")

    return root, base_commit, subject_commit, merge_commit


def _create_task_from_template(
    root: Path,
    task_id: str,
    *,
    state: str,
    base_commit: str,
    subject_commit: str,
    merge_commit: str | None = None,
) -> None:
    task_dir = root / ".ai" / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    template_task = yaml.safe_load(
        (ROOT / ".ai" / "tasks" / "TASK-0092" / "task.yaml").read_text(encoding="utf-8")
    )
    template_task["task_id"] = task_id
    template_task["base_commit"] = base_commit
    template_task["subject_commit"] = subject_commit
    template_task["current_state"] = state
    (task_dir / "task.yaml").write_text(yaml.safe_dump(template_task), encoding="utf-8")

    template_events = [
        json.loads(line)
        for line in (ROOT / ".ai" / "tasks" / "TASK-0092" / "events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    for event in template_events:
        event["task_id"] = task_id

    if state == "APPROVED_FOR_MERGE":
        # Drop the last merge_recorded event so replay ends in APPROVED_FOR_MERGE
        events = template_events[:-1]
    else:
        events = template_events
        if merge_commit is not None:
            events[-1]["payload"]["merge_commit"] = merge_commit

    (task_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )


def test_verify_closeout_passes_for_valid_merged_task(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, base, subject, merge = _setup_repo_and_merged_commits(tmp_path)
    _create_task_from_template(
        root,
        "TASK-0001",
        state="MERGED",
        base_commit=base,
        subject_commit=subject,
        merge_commit=merge,
    )

    verify_closeout(root, "TASK-0001")
    captured = capsys.readouterr()
    assert "closeout verified" in captured.out
    assert merge in captured.out


def test_verify_closeout_passes_for_historical_repo_task(
    capsys: pytest.CaptureFixture[str],
) -> None:
    verify_closeout(ROOT, "TASK-0092")
    captured = capsys.readouterr()
    assert "Task TASK-0092 closeout verified" in captured.out


def test_verify_closeout_fails_when_not_merged_state(tmp_path: Path) -> None:
    root, base, subject, merge = _setup_repo_and_merged_commits(tmp_path)
    _create_task_from_template(
        root,
        "TASK-0001",
        state="APPROVED_FOR_MERGE",
        base_commit=base,
        subject_commit=subject,
        merge_commit=merge,
    )

    with pytest.raises(ContractError) as exc_info:
        verify_closeout(root, "TASK-0001")
    assert exc_info.value.code == "CLOSEOUT_NOT_MERGED"


def test_verify_closeout_fails_when_merge_event_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base, subject, merge = _setup_repo_and_merged_commits(tmp_path)
    _create_task_from_template(
        root,
        "TASK-0001",
        state="MERGED",
        base_commit=base,
        subject_commit=subject,
        merge_commit=merge,
    )

    # Mock read_task_record_strict to return no merge_recorded events
    fake_record = TaskRecord(
        task={"current_state": "MERGED", "base_commit": base, "subject_commit": subject},
        events=({"event_type": "task_created", "payload": {}},),
    )
    monkeypatch.setattr("tools.ci.verify_closeout.read_task_record_strict", lambda *_: fake_record)

    with pytest.raises(ContractError) as exc_info:
        verify_closeout(root, "TASK-0001")
    assert exc_info.value.code == "CLOSEOUT_EVENT_MISSING"


def test_verify_closeout_fails_when_commit_is_not_a_merge(tmp_path: Path) -> None:
    root, base, subject, _ = _setup_repo_and_merged_commits(tmp_path)
    # Using the single-parent subject commit as the supposed merge commit
    _create_task_from_template(
        root,
        "TASK-0001",
        state="MERGED",
        base_commit=base,
        subject_commit=subject,
        merge_commit=subject,
    )

    with pytest.raises(ContractError) as exc_info:
        verify_closeout(root, "TASK-0001")
    assert exc_info.value.code == "CLOSE_NOT_MERGE"


def test_verify_closeout_fails_when_merge_commit_not_ancestral(tmp_path: Path) -> None:
    root, base, subject, _ = _setup_repo_and_merged_commits(tmp_path)

    # Create an unrelated branch and merge it into main
    _git(root, "checkout", "-b", "unrelated", base)
    (root / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "unrelated commit")
    unrelated_head = _git(root, "rev-parse", "HEAD")

    _git(root, "checkout", "master" if "master" in _git(root, "branch") else "main")
    _git(root, "merge", "--no-ff", "-m", "Merge unrelated into main", unrelated_head)
    unrelated_merge = _git(root, "rev-parse", "HEAD")

    _create_task_from_template(
        root,
        "TASK-0001",
        state="MERGED",
        base_commit=base,
        subject_commit=subject,
        merge_commit=unrelated_merge,
    )

    with pytest.raises(ContractError) as exc_info:
        verify_closeout(root, "TASK-0001")
    assert exc_info.value.code == "CLOSE_SUBJECT_NOT_MERGED"


def test_verify_closeout_cli_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, base, subject, merge = _setup_repo_and_merged_commits(tmp_path)
    _create_task_from_template(
        root,
        "TASK-0001",
        state="MERGED",
        base_commit=base,
        subject_commit=subject,
        merge_commit=merge,
    )

    monkeypatch.chdir(root)
    assert main(["--task", "TASK-0001"]) == 0
    assert main(["--task", "TASK-NONEXISTENT"]) == 1
