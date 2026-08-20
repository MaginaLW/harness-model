from __future__ import annotations

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
from aiflow.storage import resolve_task_path


def test_review_scenario_requires_spec_and_code_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _unit, expected = prepare_task(tmp_path, monkeypatch, "review-workflow-change")
    assert main(["classify", TASK_ID, "--actor", "classifier"]) == 0
    assert classification(repository)["effective_route"] == expected["route"] == "REVIEW"
    assert state(repository) == "WAITING_FOR_SPEC_REVIEW"
    assert main(["freeze", TASK_ID, "--actor", "specifier"]) == 0
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 1
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
