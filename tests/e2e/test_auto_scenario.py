from __future__ import annotations

from pathlib import Path

import pytest
from scenario_support import (
    TASK_ID,
    approvals,
    classification,
    commit_implementation,
    evidence,
    install_compact_verification,
    prepare_task,
    state,
)

from aiflow.cli import main


def test_auto_document_scenario_reaches_closed_without_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _unit, expected = prepare_task(tmp_path, monkeypatch, "auto-doc-edit")
    assert main(["classify", TASK_ID, "--actor", "classifier"]) == 0
    assert classification(repository)["effective_route"] == expected["route"] == "AUTO"
    assert main(["freeze", TASK_ID, "--actor", "specifier"]) == 0
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 0
    head = commit_implementation(
        repository,
        {"docs/guide.md": "# Guide\n\nClearer bounded wording.\n"},
        "docs: improve guide wording",
    )
    install_compact_verification(monkeypatch)
    assert main(["verify", TASK_ID, "--actor", "verifier"]) == 0
    result = evidence(repository)
    assert result["conclusion"] == "passed"
    assert result["verification_level"] == expected["verification_level"] == "V0"
    assert all(check["status"] == "passed" for check in result["checks"])
    assert approvals(repository) == []
    assert main(["gate", TASK_ID, "--format", "json"]) == 0
    assert (
        main(
            [
                "close",
                TASK_ID,
                "--result",
                "merged",
                "--merge-commit",
                head,
                "--actor",
                "integrator",
            ]
        )
        == 0
    )
    assert state(repository) == "MERGED"
