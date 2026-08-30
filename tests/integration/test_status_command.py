"""Integration tests for read-only status output."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from aiflow import status_service
from aiflow.cli import main
from aiflow.state import TRANSITIONS, create_record_event, create_transition_event
from aiflow.storage import atomic_write_json, atomic_write_text, atomic_write_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"

PATHS: dict[str, list[str]] = {
    "NEW": [],
    "WAITING_FOR_ASK": ["CLASSIFIED", "WAITING_FOR_ASK"],
    "READY_TO_IMPLEMENT": ["CLASSIFIED", "READY_TO_IMPLEMENT"],
    "IMPLEMENTING": ["CLASSIFIED", "READY_TO_IMPLEMENT", "IMPLEMENTING"],
    "FAILED": ["CLASSIFIED", "READY_TO_IMPLEMENT", "IMPLEMENTING", "VERIFYING", "FAILED"],
    "VERIFIED": ["CLASSIFIED", "READY_TO_IMPLEMENT", "IMPLEMENTING", "VERIFYING", "VERIFIED"],
    "APPROVED_FOR_MERGE": [
        "CLASSIFIED",
        "READY_TO_IMPLEMENT",
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "APPROVED_FOR_MERGE",
    ],
    "MERGED": [
        "CLASSIFIED",
        "READY_TO_IMPLEMENT",
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "APPROVED_FOR_MERGE",
        "MERGED",
    ],
}


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=True,
        encoding="utf-8",
        timeout=10,
    )
    return result.stdout.rstrip("\r\n")


def create_repository(path: Path) -> Path:
    path.mkdir()
    run_git(path, "init", "-b", "main")
    ai_root = path / ".ai"
    ai_root.mkdir()
    shutil.copytree(PROJECT_ROOT / ".ai" / "schemas", ai_root / "schemas")
    (ai_root / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    run_git(path, "add", ".ai", "tracked.txt")
    run_git(
        path,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "initial",
    )
    return path


def create_task(repository: Path, state: str) -> Path:
    head = run_git(repository, "rev-parse", "HEAD")
    task = json.loads(
        (PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "task.json").read_text(
            encoding="utf-8"
        )
    )
    task.update(
        {
            "task_id": "TASK-0001",
            "repository_id": REPOSITORY_ID,
            "branch": "main",
            "base_commit": head,
            "subject_commit": head,
            "worktree_dirty": False,
            "current_state": state,
            "repository_path_at_creation": repository.resolve().as_posix(),
        }
    )
    task["decision_units"][0]["task_id"] = "TASK-0001"
    event_task = {"task_id": "TASK-0001", "current_state": "NEW"}
    events: list[dict[str, Any]] = [
        create_record_event(
            event_task,
            event_type="task_created",
            actor="aiflow",
            payload={},
            sequence=1,
            occurred_at="2026-08-20T14:00:00Z",
        )
    ]
    current = "NEW"
    for target in PATHS[state]:
        rule = TRANSITIONS[(current, target)]
        event_task["current_state"] = current
        events.append(
            create_transition_event(
                event_task,
                target_state=target,
                event_type=rule.event_type,
                actor="tester",
                payload={},
                sequence=len(events) + 1,
                satisfied_preconditions=set(rule.preconditions),
                occurred_at="2026-08-20T14:00:00Z",
            )
        )
        current = target
    directory = repository / ".ai" / "tasks" / "TASK-0001"
    directory.mkdir(parents=True)
    atomic_write_yaml(directory / "task.yaml", task)
    atomic_write_text(
        directory / "events.jsonl",
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
    )
    atomic_write_json(directory / "approvals.json", [])
    return directory


@pytest.mark.parametrize("state", list(PATHS))
def test_json_status_for_main_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    state: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    create_task(repository, state)
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001", "--format", "json"]) == 0

    summary = json.loads(capsys.readouterr().out)
    assert summary["task_id"] == "TASK-0001"
    assert summary["current_state"] == state
    assert summary["merge_readiness"] == (
        "reverification_required" if state == "APPROVED_FOR_MERGE" else "not_applicable"
    )
    assert summary["route"] == "not_available"
    assert summary["verification_level"] == "not_available"
    assert isinstance(summary["next_events"], list)
    assert summary["observed_head"] == run_git(repository, "rev-parse", "HEAD")
    if state == "APPROVED_FOR_MERGE":
        assert summary["missing_conditions"] == ["reverification"]


@pytest.mark.parametrize(
    ("state", "route", "classification", "approvals", "evidence", "expected"),
    [
        (
            "APPROVED_FOR_MERGE",
            "REVIEW",
            "fresh",
            "current",
            "passed",
            "gate_required",
        ),
        (
            "APPROVED_FOR_MERGE",
            "AUTO",
            "fresh",
            "not_available",
            "passed",
            "gate_required",
        ),
        (
            "APPROVED_FOR_MERGE",
            "REVIEW",
            "fresh",
            "stale",
            "passed",
            "reverification_required",
        ),
        (
            "APPROVED_FOR_MERGE",
            "REVIEW",
            "fresh",
            "current",
            "stale",
            "reverification_required",
        ),
        (
            "WAITING_FOR_FINAL_REVIEW",
            "REVIEW",
            "fresh",
            "not_available",
            "passed",
            "not_applicable",
        ),
    ],
)
def test_merge_readiness_projection(
    state: str,
    route: str,
    classification: str,
    approvals: str,
    evidence: str,
    expected: str,
) -> None:
    assert (
        status_service._merge_readiness(
            state=state,
            route=route,
            classification=classification,
            approvals=approvals,
            evidence=evidence,
        )
        == expected
    )


def test_text_status_is_concise_and_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "READY_TO_IMPLEMENT")
    monkeypatch.chdir(repository)
    paths = [directory / "task.yaml", directory / "events.jsonl"]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

    assert main(["status", "TASK-0001"]) == 0

    output = capsys.readouterr().out
    assert "State: READY_TO_IMPLEMENT" in output
    assert "Merge readiness: not_applicable" in output
    assert "Next events: implementation_started" in output
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_status_reports_classification_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "WAITING_FOR_ASK")
    classification = json.loads(
        (
            PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "classification.json"
        ).read_text(encoding="utf-8")
    )
    atomic_write_json(directory / "classification.json", classification)
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["route"] == "REVIEW"
    assert summary["verification_level"] == "V1"


def test_status_does_not_treat_unrequested_action_approval_as_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "READY_TO_IMPLEMENT")
    approval = json.loads(
        (PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "approval.json").read_text(
            encoding="utf-8"
        )
    )
    approval.update(
        {
            "approval_type": "action",
            "action_sha256": "c" * 64,
            "expires_at": "2099-01-01T00:00:00Z",
            "single_use": True,
        }
    )
    atomic_write_json(directory / "approvals.json", [approval])
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["approvals"] == "not_applicable"


def test_status_rejects_corrupt_event_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "NEW")
    (directory / "events.jsonl").write_text("{broken\n", encoding="utf-8")
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001"]) == 1
    assert "parse" in capsys.readouterr().err.lower()


def test_status_rejects_materialized_state_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "NEW")
    task = yaml.safe_load((directory / "task.yaml").read_text(encoding="utf-8"))
    task["current_state"] = "CLASSIFIED"
    atomic_write_yaml(directory / "task.yaml", task)
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001"]) == 1
    assert "match" in capsys.readouterr().err.lower()


def test_status_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["status", "--help"])
    assert caught.value.code == 0
    assert "--format" in capsys.readouterr().out
