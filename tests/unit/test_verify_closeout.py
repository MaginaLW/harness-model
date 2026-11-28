"""Exercise closeout CI with the Git snapshots produced by the native close command."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from aiflow import closeout_check
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
from tools.ci import verify_closeout as verify_closeout_wrapper
from tools.ci.verify_closeout import verify_closeout, verify_retained

TASK = "TASK-0001"


def _seed_tree_sha256(root: Path) -> str:
    """Digest every directory, file byte, and link count inside a shared module seed."""
    hasher = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise AssertionError(f"shared seed contains link: {path}")
        if stat.S_ISDIR(info.st_mode):
            hasher.update(b"D\0" + relative + b"\0")
        elif stat.S_ISREG(info.st_mode):
            assert info.st_nlink == 1, f"shared seed file has hardlink: {path}"
            hasher.update(b"F\0" + relative + b"\0" + path.read_bytes() + b"\0")
        else:
            raise AssertionError(f"unexpected seed entry: {path}")
    return hasher.hexdigest()


@pytest.fixture(scope="module")
def _closed_seed(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Path, str, str]]:
    root = create_repository(tmp_path_factory.mktemp("closeout-closed-seed") / "repo")
    initial = run_git(root, "rev-parse", "HEAD")
    with pytest.MonkeyPatch.context() as mp:
        start(root, mp)
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
    head = run_git(root, "rev-parse", "HEAD")
    expected = _seed_tree_sha256(root)
    yield root, merge, head
    assert _seed_tree_sha256(root) == expected


@pytest.fixture
def closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    _closed_seed: tuple[Path, str, str],
) -> tuple[Path, str, str]:
    seed_root, merge, head = _closed_seed
    root = tmp_path / "repo"
    shutil.copytree(seed_root, root, copy_function=shutil.copyfile)
    monkeypatch.chdir(root)
    return root, merge, head


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


@pytest.fixture(scope="module")
def _failed_seed(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Path, str, str]]:
    root = create_repository(tmp_path_factory.mktemp("closeout-failed-seed") / "repo")
    with pytest.MonkeyPatch.context() as mp:
        start(root, mp)
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
    head = run_git(root, "rev-parse", "HEAD")
    expected = _seed_tree_sha256(root)
    yield root, before_failure, head
    assert _seed_tree_sha256(root) == expected


@pytest.fixture
def failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    _failed_seed: tuple[Path, str, str],
) -> tuple[Path, str, str]:
    seed_root, before_failure, head = _failed_seed
    root = tmp_path / "repo"
    shutil.copytree(seed_root, root, copy_function=shutil.copyfile)
    monkeypatch.chdir(root)
    return root, before_failure, head


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


def test_portable_closeout_check_api_and_subprocess_for_closed(
    closed: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    closed_root, merge, closed_head = closed
    advanced = close_commit(closed_root, "later target change", merge)

    # Run from a directory with no .ai/schemas to verify target root/.ai/schemas is used.
    monkeypatch.chdir(closed_root.parent)
    closeout_check.verify_closeout(closed_root, advanced, closed_head, TASK)

    clean_env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    valid_closeout = subprocess.run(
        [
            sys.executable,
            "-m",
            "aiflow.closeout_check",
            "--base",
            advanced,
            "--head",
            closed_head,
            "--task",
            TASK,
        ],
        cwd=closed_root,
        env=clean_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert valid_closeout.returncode == 0, valid_closeout.stderr
    assert f"Verified closeout for {TASK}" in valid_closeout.stdout

    monkeypatch.chdir(closed_root)
    assert closeout_check.main(["--base", advanced, "--head", closed_head, "--task", TASK]) == 0
    assert f"Verified closeout for {TASK}" in capsys.readouterr().out
    assert (
        verify_closeout_wrapper.main(["--base", advanced, "--head", closed_head, "--task", TASK])
        == 0
    )
    assert f"Verified closeout for {TASK}" in capsys.readouterr().out
    assert (
        verify_closeout_wrapper.main(["--base", advanced, "--head", closed_head, "--task", "BAD"])
        == 1
    )
    assert "Ledger verification failed:" in capsys.readouterr().err

    (closed_root / ".ai" / "tasks" / TASK / "spec.md").write_text(
        "tampered after merge\n", encoding="utf-8"
    )
    commit_all(closed_root, "tamper closeout")
    tampered_head = run_git(closed_root, "rev-parse", "HEAD")

    tampered_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "aiflow.closeout_check",
            "--base",
            merge,
            "--head",
            tampered_head,
            "--task",
            TASK,
        ],
        cwd=closed_root,
        env=clean_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert tampered_run.returncode == 1
    assert "Ledger verification failed:" in tampered_run.stderr

    assert closeout_check.main(["--base", merge, "--head", closed_head, "--task", "INVALID"]) == 1
    assert "invalid task ID" in capsys.readouterr().err
    assert closeout_check.main(["--base", "0" * 40, "--head", closed_head, "--task", TASK]) == 1
    assert "Ledger verification failed:" in capsys.readouterr().err

    run_git(closed_root, "switch", "--detach", advanced)
    (closed_root / ".ai" / "repository-id").write_text(
        "00000000-0000-4000-8000-000000000000\n", encoding="utf-8"
    )
    commit_all(closed_root, "different repository")
    wrong_repo = run_git(closed_root, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="approved and belong to this repository"):
        closeout_check.verify_closeout(closed_root, wrong_repo, closed_head, TASK)

    monkeypatch.chdir(closed_root.parent)
    (closed_root / ".ai" / "schemas" / "task.schema.json").unlink()
    with pytest.raises(FileNotFoundError):
        closeout_check.verify_closeout(closed_root, advanced, closed_head, TASK)


def test_portable_closeout_check_api_and_subprocess_for_retained(
    failed: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    failed_root, before_failure, failed_head = failed

    monkeypatch.chdir(failed_root.parent)
    closeout_check.verify_retained(failed_root, before_failure, failed_head, TASK)

    clean_env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    valid_retained = subprocess.run(
        [
            sys.executable,
            "-m",
            "aiflow.closeout_check",
            "--retained",
            "--base",
            before_failure,
            "--head",
            failed_head,
            "--task",
            TASK,
        ],
        cwd=failed_root,
        env=clean_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert valid_retained.returncode == 0, valid_retained.stderr
    assert f"Verified retained record for {TASK}" in valid_retained.stdout

    monkeypatch.chdir(failed_root)
    assert (
        closeout_check.main(
            ["--retained", "--base", before_failure, "--head", failed_head, "--task", TASK]
        )
        == 0
    )
    assert f"Verified retained record for {TASK}" in capsys.readouterr().out

    (failed_root / ".ai" / "tasks" / TASK / "classification.json").unlink()
    commit_all(failed_root, "tamper retained")
    tampered_head = run_git(failed_root, "rev-parse", "HEAD")

    tampered_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "aiflow.closeout_check",
            "--retained",
            "--base",
            before_failure,
            "--head",
            tampered_head,
            "--task",
            TASK,
        ],
        cwd=failed_root,
        env=clean_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert tampered_run.returncode == 1
    assert "Ledger verification failed:" in tampered_run.stderr


def test_portable_closeout_check_retained_sync_and_frozen_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = create_repository(tmp_path / "repo")
    with monkeypatch.context() as mp:
        start(root, mp)
        commit_all(root, "started")
        fork = run_git(root, "rev-parse", "HEAD")
        make_ready(root)
        assert aiflow(["begin", TASK, "--actor", "implementer"]) == 0
        (root / "src").mkdir(exist_ok=True)
        (root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        commit_all(root, "subject change")
        assert aiflow(["sync", TASK, "--actor", "implementer"]) == 0
        make_failed(root, {"conclusion": "failed"})
        commit_all(root, "retained failed after sync")
    head = run_git(root, "rev-parse", "HEAD")
    monkeypatch.chdir(tmp_path)
    closeout_check.verify_retained(root, fork, head, TASK)

    (root / ".ai" / "repository-id").write_text("00000000-0000-4000-8000-000000000000\n")
    commit_all(root, "different repo")
    different_repo = run_git(root, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="failed or blocked task"):
        closeout_check.verify_retained(root, different_repo, head, TASK)
