from __future__ import annotations

from pathlib import Path

import pytest
from scenario_support import (
    TASK_ID,
    classification,
    commit_implementation,
    evidence,
    install_compact_verification,
    prepare_task,
    state,
    write_options,
)

from aiflow.cli import main
from aiflow.storage import resolve_task_path
from aiflow.task_service import load_task_record


def test_ask_scenario_requires_answer_then_passes_v1_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _unit, expected = prepare_task(tmp_path, monkeypatch, "ask-conflict-strategy")
    assert main(["classify", TASK_ID, "--actor", "classifier"]) == 0
    assert classification(repository)["effective_route"] == expected["route"] == "ASK"
    assert state(repository) == "WAITING_FOR_ASK"
    assert main(["gate", TASK_ID, "--format", "json"]) == 2
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 1

    options = write_options(repository, expected)
    assert (
        main(
            [
                "answer",
                TASK_ID,
                "--options-file",
                str(options),
                "--select",
                "OPT-03",
                "--actor",
                "operator",
                "--reason",
                "serve both human and machine consumers",
            ]
        )
        == 0
    )
    answer = load_task_record(repository, TASK_ID).events[-1]
    assert answer["event_type"] == "ask_answered"
    assert len(answer["payload"]["options"]["options"]) == 3
    assert "OPT-03" in resolve_task_path(repository, TASK_ID, "spec.md").read_text(encoding="utf-8")
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 0
    commit_implementation(
        repository,
        {
            "src/aiflow/conflicts.py": (
                "def render_conflict() -> tuple[str, str]:\n    return ('markdown', 'json')\n"
            ),
            "docs/conflict-reports.md": "# Conflict reports\n\nMarkdown and JSON are emitted.\n",
        },
        "feat: emit two conflict report formats",
    )
    install_compact_verification(monkeypatch)
    assert main(["verify", TASK_ID, "--actor", "verifier"]) == 0
    assert evidence(repository)["verification_level"] == expected["verification_level"] == "V1"
    assert main(["gate", TASK_ID, "--format", "json"]) == 0
