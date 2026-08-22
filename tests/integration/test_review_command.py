"""Integration coverage for the Chapter 8 structured-review CLI surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_approve_command import _evidence, _prepare, review_package

from aiflow import review_service
from aiflow.cli import main
from aiflow.errors import StorageError
from aiflow.review_service import list_review_records, validate_review_artifacts
from aiflow.storage import atomic_write_json, resolve_task_path
from aiflow.task_service import load_task_record


def _context(repository: Path, task_id: str, stage: str, output: Path) -> dict[str, object]:
    assert main(["review", "context", task_id, "--stage", stage, "--output", str(output)]) == 0
    value = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _record_input(
    path: Path,
    context: dict[str, object],
    *,
    stage: str,
    review_id: str,
    conclusion: str = "APPROVE",
    findings: list[dict[str, object]] | None = None,
) -> Path:
    """Write the public record input accepted by ``aiflow review record``.

    The CLI owns reviewer identity and persists the immutable record.  The test
    deliberately supplies only the review decision, the generated context hash,
    and structured findings so it verifies the command rather than duplicating
    task/Git/evidence binding logic in a fixture.
    """
    atomic_write_json(
        path,
        {
            "schema_version": "1.0",
            "review_id": review_id,
            "review_stage": stage,
            "recorded_at": "2026-08-22T01:00:00Z",
            "context_sha256": context["context_sha256"],
            "outcome": conclusion,
            "summary": "structured review completed",
            "findings": findings or [],
        },
    )
    return path


def _record(
    repository: Path,
    task_id: str,
    context: dict[str, object],
    tmp_path: Path,
    *,
    stage: str,
    review_id: str,
    conclusion: str = "APPROVE",
    findings: list[dict[str, object]] | None = None,
) -> None:
    source = _record_input(
        tmp_path / f"{review_id}.json",
        context,
        stage=stage,
        review_id=review_id,
        conclusion=conclusion,
        findings=findings,
    )
    assert (
        main(
            [
                "review",
                "record",
                task_id,
                "--input",
                str(source),
                "--actor",
                "reviewer",
            ]
        )
        == 0
    )


def test_review_context_is_stage_specific_and_record_replay_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    design = _context(repository, "TASK-0001", "design", tmp_path / "design-context.json")
    assert design["review_stage"] == "design"
    assert "subject_commit" not in design and "evidence_sha256" not in design

    _record(repository, "TASK-0001", design, tmp_path, stage="design", review_id="REV-0001")
    before = load_task_record(repository, "TASK-0001")
    _record(repository, "TASK-0001", design, tmp_path, stage="design", review_id="REV-0001")
    assert load_task_record(repository, "TASK-0001").events == before.events
    validate_review_artifacts(repository, "TASK-0001")
    assert [value["review_id"] for value in list_review_records(repository, "TASK-0001")] == [
        "REV-0001"
    ]
    assert list_review_records(repository, "TASK-0001", stage="implementation") == ()

    assert main(["review", "show", "TASK-0001", "--stage", "design", "--format", "json"]) == 0


def test_review_record_retry_completes_a_missing_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    design = _context(repository, "TASK-0001", "design", tmp_path / "design-context.json")
    source = _record_input(
        tmp_path / "recovery.json",
        design,
        stage="design",
        review_id="REV-0009",
    )
    original = review_service.record_task_event

    def fail_once(*args: object, **kwargs: object) -> None:
        raise StorageError("injected", code="STORAGE_WRITE_FAILED")

    monkeypatch.setattr(review_service, "record_task_event", fail_once)
    arguments = [
        "review",
        "record",
        "TASK-0001",
        "--input",
        str(source),
        "--actor",
        "reviewer",
    ]
    assert main(arguments) == 1
    monkeypatch.setattr(review_service, "record_task_event", original)
    assert main(arguments) == 0
    events = load_task_record(repository, "TASK-0001").events
    assert [event["event_type"] for event in events].count("review_recorded") == 1


def test_review_command_rejects_phase_swap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    design = _context(repository, "TASK-0001", "design", tmp_path / "design-context.json")
    swapped = _record_input(
        tmp_path / "swapped.json",
        design,
        stage="implementation",
        review_id="REV-0002",
    )
    assert (
        main(["review", "record", "TASK-0001", "--input", str(swapped), "--actor", "reviewer"]) == 1
    )


def test_review_record_rejects_a_context_hash_not_shown_to_the_reviewer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    design = _context(repository, "TASK-0001", "design", tmp_path / "design-context.json")
    source = _record_input(
        tmp_path / "wrong-context.json",
        design,
        stage="design",
        review_id="REV-0003",
    )
    value = json.loads(source.read_text(encoding="utf-8"))
    value["context_sha256"] = "0" * 64
    atomic_write_json(source, value)
    assert (
        main(["review", "record", "TASK-0001", "--input", str(source), "--actor", "reviewer"]) == 1
    )


def test_latest_non_approving_review_cannot_fall_back_to_an_older_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    design = _context(repository, "TASK-0001", "design", tmp_path / "design-context.json")
    _record(repository, "TASK-0001", design, tmp_path, stage="design", review_id="REV-0007")
    _record(
        repository,
        "TASK-0001",
        design,
        tmp_path,
        stage="design",
        review_id="REV-0008",
        conclusion="REQUEST_CHANGES",
    )
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "spec",
                "--actor",
                "reviewer",
                "--reason",
                "must honor latest review",
            ]
        )
        == 1
    )


def test_review_rejects_open_high_finding_for_approving_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    design = _context(repository, "TASK-0001", "design", tmp_path / "design-context.json")
    source = _record_input(
        tmp_path / "open-high.json",
        design,
        stage="design",
        review_id="REV-0004",
        findings=[
            {
                "finding_id": "RF-001",
                "severity": "high",
                "title": "Acceptance boundary is incomplete",
                "location": {"path": "spec.md", "line": 1},
                "evidence_refs": ["spec.md:1"],
                "status": "open",
            }
        ],
    )
    assert (
        main(["review", "record", "TASK-0001", "--input", str(source), "--actor", "reviewer"]) == 1
    )


def test_review_resolution_appends_revision_without_overwriting_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    design = _context(repository, "TASK-0001", "design", tmp_path / "design-context.json")
    _record(
        repository,
        "TASK-0001",
        design,
        tmp_path,
        stage="design",
        review_id="REV-0005",
        conclusion="REQUEST_CHANGES",
        findings=[
            {
                "finding_id": "RF-001",
                "severity": "high",
                "title": "Acceptance boundary is incomplete",
                "location": {"path": "spec.md", "line": 1},
                "evidence_refs": ["spec.md:1"],
                "status": "open",
            }
        ],
    )
    assert (
        main(
            [
                "review",
                "resolve",
                "TASK-0001",
                "--review",
                "REV-0005",
                "--finding",
                "RF-001",
                "--reason",
                "boundary added to specification",
                "--actor",
                "reviewer",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "review",
                "resolve",
                "TASK-0001",
                "--review",
                "REV-0005",
                "--finding",
                "RF-001",
                "--reason",
                "boundary added to specification",
                "--actor",
                "reviewer",
            ]
        )
        == 0
    )
    records_dir = resolve_task_path(repository, "TASK-0001", "reviews")
    assert len(list(records_dir.glob("REV-0005-r*.json"))) == 2


def test_implementation_context_rejects_stale_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_FINAL_REVIEW")
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "evidence.json"), _evidence(repository)
    )
    implementation = _context(
        repository, "TASK-0001", "implementation", tmp_path / "implementation-context.json"
    )
    assert implementation["review_stage"] == "implementation"
    assert "subject_commit" in implementation and "evidence_sha256" in implementation
    assert implementation["content"]["diff_summary"] == {
        "changed_paths": [],
        "files": [],
        "totals": {"files": 0, "additions": 0, "deletions": 0},
    }
    assert implementation["content"]["verification_summary"] == {
        "verification_level": "V1",
        "required_checks": [{"check_id": "pytest", "status": "passed"}],
        "unverified_scenarios": [],
        "reproduce_command": ["python", "-m", "pytest"],
    }
    _record(
        repository,
        "TASK-0001",
        implementation,
        tmp_path,
        stage="implementation",
        review_id="REV-0006",
    )

    evidence = _evidence(repository)
    evidence["generated_at"] = "2026-08-22T01:00:00Z"
    atomic_write_json(resolve_task_path(repository, "TASK-0001", "evidence.json"), evidence)
    refreshed = _context(
        repository, "TASK-0001", "implementation", tmp_path / "refreshed-context.json"
    )
    assert refreshed["context_sha256"] != implementation["context_sha256"]
    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    assert (
        main(["review", "show", "TASK-0001", "--stage", "implementation", "--format", "json"]) == 0
    )
    assert (
        main(["approve", "TASK-0001", "--type", "code", "--actor", "reviewer", "--reason", "stale"])
        == 1
    )
