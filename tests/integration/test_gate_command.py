"""Integration tests for deterministic, read-only local and CI Gate decisions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_approve_command import review_package
from test_begin_close_commands import create_repository, make_ready, run_git, start
from test_governance_paths import _auto_unit
from test_verify_command import _plan

from aiflow import gate as gate_service
from aiflow import verification_service
from aiflow.cli import main
from aiflow.storage import (
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record


def _prepare_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    review: bool = False,
    implementation_path: str | None = None,
) -> Path:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    unit = _auto_unit("TASK-0001")
    if review:
        unit["impact"] = {"level": "medium"}
        characteristics = unit["change_characteristics"]
        assert isinstance(characteristics, dict)
        characteristics.update(
            {"mechanical": False, "behavior_changed": True, "code_modified": True}
        )
    task["decision_units"] = [unit]
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    route = "REVIEW" if review else "AUTO"
    make_ready(repository, route=route, valid_approval=review)
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    if not review:
        classification["effective_verification_level"] = "V0"
        classification["classifications"][0]["verification_level"] = "V0"
        atomic_write_json(
            resolve_task_path(repository, "TASK-0001", "classification.json"), classification
        )
    else:
        approvals = read_task_json(repository, "TASK-0001", "approvals.json")
        assert isinstance(approvals, list)
        approvals[0]["base_commit"] = task["base_commit"]
        atomic_write_json(resolve_task_path(repository, "TASK-0001", "approvals.json"), approvals)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    if implementation_path is not None:
        implementation = repository / implementation_path
        implementation.parent.mkdir(parents=True, exist_ok=True)
        implementation.write_text("implemented\n", encoding="utf-8")
        run_git(repository, "add", implementation_path)
        run_git(
            repository,
            "-c",
            "user.name=AI Flow Tests",
            "-c",
            "user.email=aiflow@example.invalid",
            "commit",
            "-m",
            "implementation",
        )
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan())
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    return repository


def test_auto_gate_passes_repeatably_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    capsys.readouterr()
    paths = [
        resolve_task_path(repository, "TASK-0001", name)
        for name in ("task.yaml", "events.jsonl", "approvals.json", "evidence.json")
    ]
    before = {path: path.read_bytes() for path in paths}

    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    first = capsys.readouterr().out
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    second = capsys.readouterr().out

    assert first == second
    assert json.loads(first)["passed"] is True
    assert before == {path: path.read_bytes() for path in paths}


def test_gate_rejects_governance_tail_outside_current_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    capsys.readouterr()
    (repository / "tracked.txt").write_text("new tail\n", encoding="utf-8")
    run_git(repository, "add", "tracked.txt")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "outside tail",
    )

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert "GATE_SCOPE_CHANGED" in json.loads(capsys.readouterr().out)["reason_codes"]


def test_auto_gate_rejects_subject_change_outside_decision_unit_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_gate(
        tmp_path,
        monkeypatch,
        implementation_path="src/outside-decision-unit.py",
    )
    capsys.readouterr()

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert "GATE_SCOPE_CHANGED" in json.loads(capsys.readouterr().out)["reason_codes"]


def test_gate_rejects_non_ancestral_commit_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_gate(tmp_path, monkeypatch)
    capsys.readouterr()
    monkeypatch.setattr(gate_service, "commits_are_ancestral", lambda *args, **kwargs: False)

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert "GATE_REPOSITORY_CHANGED" in json.loads(capsys.readouterr().out)["reason_codes"]


def test_review_gate_requires_code_approval_and_then_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    capsys.readouterr()
    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    rejected = json.loads(capsys.readouterr().out)
    assert "GATE_CODE_APPROVAL_STALE" in rejected["reason_codes"]
    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )

    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "code",
                "--actor",
                "reviewer",
                "--reason",
                "current implementation approved",
            ]
        )
        == 0
    )
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["passed"] is True


def test_ci_gate_uses_external_attested_evidence_but_local_code_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_gate(tmp_path, monkeypatch)
    ci_run_dir = tmp_path / "gate-ci"
    ci_run_dir.mkdir()
    external = ci_run_dir / "evidence.json"
    assert (
        main(
            [
                "verify",
                "TASK-0001",
                "--ci",
                "--ci-run-dir",
                str(ci_run_dir),
                "--output",
                str(external),
            ]
        )
        == 0
    )

    assert (
        main(
            [
                "gate",
                "TASK-0001",
                "--evidence",
                str(external),
                "--format",
                "json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["passed"] is True


def test_action_approval_does_not_replace_review_code_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    task = load_task_record(repository, "TASK-0001").task
    action_path = tmp_path / "action.json"
    action_path.write_text(
        json.dumps(
            {
                "decision_unit_id": "DU-001",
                "action_type": "notify",
                "target": "issue-1",
                "parameter_summary": "one notification",
                "subject_commit": task["subject_commit"],
                "conditions": ["reviewed"],
                "expires_at": "2099-01-01T00:00:00Z",
                "single_use": True,
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "action",
                "--action-file",
                str(action_path),
                "--actor",
                "reviewer",
                "--reason",
                "notification only",
            ]
        )
        == 0
    )

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert (
        "GATE_CODE_APPROVAL_STALE"
        in json.loads(capsys.readouterr().out.splitlines()[-1])["reason_codes"]
    )


def test_gate_distinguishes_invalid_external_input_from_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_gate(tmp_path, monkeypatch)
    broken = tmp_path / "broken.json"
    broken.write_text("{broken", encoding="utf-8")
    assert main(["gate", "TASK-0001", "--evidence", str(broken)]) == 1


def test_gate_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["gate", "--help"])
    assert caught.value.code == 0
    output = capsys.readouterr().out
    assert "--evidence" in output and "--format" in output
