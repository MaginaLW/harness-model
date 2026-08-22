from __future__ import annotations

import json
from pathlib import Path

import pytest
from scenario_support import (
    TASK_ID,
    approvals,
    classification,
    commit_implementation,
    install_compact_verification,
    prepare_task,
    review_package,
    state,
)

from aiflow.cli import main
from aiflow.storage import atomic_write_json, resolve_task_path


def _record_stage_review(task_id: str, stage: str, review_id: str, tmp_path: Path) -> None:
    """Record an approving immutable review based on CLI-generated context."""
    context_path = tmp_path / f"{review_id}-context.json"
    assert (
        main(
            [
                "review",
                "context",
                task_id,
                "--stage",
                stage,
                "--output",
                str(context_path),
            ]
        )
        == 0
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    assert isinstance(context, dict)
    record_path = tmp_path / f"{review_id}.json"
    atomic_write_json(
        record_path,
        {
            "schema_version": "1.0",
            "review_id": review_id,
            "review_stage": stage,
            "recorded_at": "2026-08-22T01:00:00Z",
            "context_sha256": context["context_sha256"],
            "outcome": "APPROVE",
            "summary": "golden scenario review passed",
            "findings": [],
        },
    )
    assert (
        main(
            [
                "review",
                "record",
                task_id,
                "--input",
                str(record_path),
                "--actor",
                f"{stage}-reviewer",
            ]
        )
        == 0
    )


def test_review_scenario_requires_spec_and_code_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _unit, expected = prepare_task(tmp_path, monkeypatch, "review-workflow-change")
    assert main(["classify", TASK_ID, "--actor", "classifier"]) == 0
    assert classification(repository)["effective_route"] == expected["route"] == "REVIEW"
    assert state(repository) == "WAITING_FOR_SPEC_REVIEW"
    assert main(["freeze", TASK_ID, "--actor", "specifier"]) == 0
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 1
    _record_stage_review(TASK_ID, "design", "REV-0001", tmp_path)
    assert (
        main(
            [
                "approve",
                TASK_ID,
                "--type",
                "spec",
                "--actor",
                "spec-reviewer",
                "--reason",
                "workflow behavior is explicit",
            ]
        )
        == 0
    )
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 0
    commit_implementation(
        repository,
        {".github/workflows/ai-quality-gate.yml": "name: AI Quality Gate\non: [push]\njobs: {}\n"},
        "ci: revise quality gate",
    )
    install_compact_verification(monkeypatch)
    assert main(["verify", TASK_ID, "--actor", "verifier"]) == 0
    assert state(repository) == "WAITING_FOR_FINAL_REVIEW"
    assert main(["gate", TASK_ID, "--format", "json"]) == 2
    _record_stage_review(TASK_ID, "implementation", "REV-0002", tmp_path)
    resolve_task_path(repository, TASK_ID, "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    assert (
        main(
            [
                "approve",
                TASK_ID,
                "--type",
                "code",
                "--actor",
                "code-reviewer",
                "--reason",
                "V1 evidence and workflow change approved",
            ]
        )
        == 0
    )
    assert {item["approval_type"] for item in approvals(repository)} == {"spec", "code"}
    assert state(repository) == "APPROVED_FOR_MERGE"
    assert main(["gate", TASK_ID, "--format", "json"]) == 0
