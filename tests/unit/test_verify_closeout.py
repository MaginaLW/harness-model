"""Exercise closeout CI with the Git snapshots produced by the native close command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from aiflow.cli import main as aiflow
from aiflow.storage import atomic_write_yaml
from aiflow.task_service import close_task
from tests.integration.test_begin_close_commands import (
    close_commit,
    commit_all,
    create_repository,
    make_approved,
    make_failed,
    make_ready,
    run_git,
    start,
)
from tools.ci.verify_closeout import verify_closeout, verify_retained

TASK = "TASK-0001"


@pytest.fixture
def closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, str]:
    root = create_repository(tmp_path / "repo")
    initial = run_git(root, "rev-parse", "HEAD")
    start(root, monkeypatch)
    make_ready(root)
    assert aiflow(["begin", TASK, "--actor", "implementer"]) == 0
    make_approved(root)
    commit_all(root, "approved candidate")
    approved = run_git(root, "rev-parse", "HEAD")
    target = close_commit(root, "target advances", initial)
    merge = close_commit(root, "merge implementation", target, approved)
    run_git(root, "switch", "-c", "closeout", merge)
    close_task(root, TASK, actor="closer", result="merged", merge_commit=merge)
    commit_all(root, "record native close")
    return root, merge, run_git(root, "rev-parse", "HEAD")


def test_native_closeout_uses_pr_snapshots_even_after_target_advances(
    closed: tuple[Path, str, str],
) -> None:
    root, merge, head = closed
    advanced = close_commit(root, "later target change", merge)
    run_git(root, "switch", "--detach", advanced)
    verify_closeout(root, advanced, head, TASK)


def test_closeout_requires_the_recorded_merge_in_target_history(
    closed: tuple[Path, str, str],
) -> None:
    root, merge, head = closed
    approved = run_git(root, "rev-parse", merge + "^2")
    with pytest.raises(ValueError, match="not in the target branch history"):
        verify_closeout(root, approved, head, TASK)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("prior_event", "exactly one appended"),
        ("materialized_task", "native close transition"),
        ("close_payload", "native merge event payload"),
        ("existing_spec", "update only task.yaml and events.jsonl"),
    ],
)
def test_closeout_accepts_only_native_changes(
    closed: tuple[Path, str, str], change: str, reason: str
) -> None:
    root, merge, _ = closed
    directory = root / ".ai" / "tasks" / TASK
    event_path = directory / "events.jsonl"
    if change == "prior_event":
        previous = event_path.read_bytes()
        event_path.write_bytes(b" " + previous)
    elif change == "materialized_task":
        path = directory / "task.yaml"
        task = yaml.safe_load(path.read_bytes())
        task["branch"] = "another-branch"
        atomic_write_yaml(path, task)
    elif change == "close_payload":
        lines = event_path.read_bytes().splitlines(keepends=True)
        last = json.loads(lines[-1])
        last["payload"]["note"] = "additional data"
        event_path.write_bytes(b"".join(lines[:-1]) + json.dumps(last).encode() + b"\n")
    else:
        (directory / "spec.md").write_text("changed after approval\n", encoding="utf-8")
    commit_all(root, f"change {change}")
    with pytest.raises(ValueError, match=reason):
        verify_closeout(root, merge, run_git(root, "rev-parse", "HEAD"), TASK)


@pytest.fixture
def failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, str]:
    root = create_repository(tmp_path / "repo")
    start(root, monkeypatch)
    make_ready(root)
    assert aiflow(["begin", TASK, "--actor", "implementer"]) == 0
    directory = root / ".ai" / "tasks" / TASK
    (directory / "evidence.json").write_bytes(
        (
            Path(__file__).resolve().parents[1] / "fixtures/contracts/valid/evidence.json"
        ).read_bytes()
    )
    commit_all(root, "keep implementation and original evidence")
    before_failure = run_git(root, "rev-parse", "HEAD")
    make_failed(root, {"conclusion": "failed"})
    (directory / "failure-notes.md").write_text(
        "Preserve the failed verification.\n", encoding="utf-8"
    )
    commit_all(root, "retain failed verification")
    return root, before_failure, run_git(root, "rev-parse", "HEAD")


def test_retained_new_ledger_and_existing_task_transition(failed: tuple[Path, str, str]) -> None:
    root, before_failure, head = failed
    verify_retained(root, before_failure + "^", head, TASK)
    verify_retained(root, before_failure, head, TASK)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("replace_evidence", "retained originals"),
        ("delete_classification", "retained originals"),
        ("rewrite_events", "event history was rewritten"),
        ("change_binding", "differs from its event projection"),
        ("unrecorded_approval", "append the recorded approvals"),
    ],
)
def test_retained_existing_ledger_preserves_originals(
    failed: tuple[Path, str, str], change: str, reason: str
) -> None:
    root, base, _ = failed
    directory = root / ".ai" / "tasks" / TASK
    if change == "replace_evidence":
        path = directory / "evidence.json"
        evidence = json.loads(path.read_bytes())
        evidence["subject_commit"] = "a" * 40
        path.write_text(json.dumps(evidence), encoding="utf-8")
    elif change == "delete_classification":
        (directory / "classification.json").unlink()
    elif change == "rewrite_events":
        path = directory / "events.jsonl"
        path.write_bytes(b" " + path.read_bytes())
    elif change == "change_binding":
        path = directory / "task.yaml"
        task = yaml.safe_load(path.read_bytes())
        task["branch"] = "unrecorded-branch"
        atomic_write_yaml(path, task)
    else:
        fixture = Path(__file__).resolve().parents[1] / "fixtures/contracts/valid/approval.json"
        (directory / "approvals.json").write_text(
            json.dumps([json.loads(fixture.read_bytes())]), encoding="utf-8"
        )
    commit_all(root, f"change {change}")
    with pytest.raises(ValueError, match=reason):
        verify_retained(root, base, run_git(root, "rev-parse", "HEAD"), TASK)
