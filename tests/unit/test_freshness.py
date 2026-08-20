import json
from pathlib import Path

import pytest

from aiflow.decision_units import classification_input_digest
from aiflow.freshness import current_classification_input_digest, evaluate_freshness


@pytest.mark.parametrize(
    "row",
    json.loads(
        (Path(__file__).parents[1] / "fixtures" / "freshness" / "decision-table.json").read_text()
    ),
)
def test_decision_table(row: dict[str, object]) -> None:
    result = evaluate_freshness(  # type: ignore[arg-type]
        row["artifact_type"],
        row["artifact"],
        row["current"],
        invalid=bool(row.get("invalid", False)),
    )
    assert result.status == row["status"]
    assert result.reason_codes == tuple(row["reasons"])
    if result.status != "not_applicable":
        assert result.reproduce_argv[0] == "aiflow"
        current = row.get("current", {})
        task_id = current.get("task_id", "TASK-0000") if isinstance(current, dict) else "TASK-0000"
        assert str(task_id) in result.reproduce_argv


def test_reason_order_and_ci_attestation() -> None:
    result = evaluate_freshness(
        "evidence",
        {
            "mode": "ci",
            "subject_commit": "old",
            "attestation_head": "old",
            "conclusion": "passed",
        },
        {"subject_commit": "new", "attestation_head": "new", "governance_only": True},
    )
    assert result.reason_codes == ("FRESHNESS_SUBJECT_CHANGED", "FRESHNESS_ATTESTATION_CHANGED")


def test_classification_digest_accepts_ordered_subject_sync_chain() -> None:
    unit = {"decision_unit_id": "DU-001"}
    task = {
        "task_id": "TASK-0001",
        "goal": "bounded",
        "allowed_scope": ["src/**"],
        "forbidden_actions": [],
        "base_commit": "0" * 40,
        "subject_commit": "c" * 40,
    }
    classification = {"subject_commit": "a" * 40}
    events = [
        {
            "event_type": "subject_commit_synchronized",
            "payload": {"old_subject_commit": "a" * 40, "new_subject_commit": "b" * 40},
        },
        {
            "event_type": "subject_commit_synchronized",
            "payload": {"old_subject_commit": "b" * 40, "new_subject_commit": "c" * 40},
        },
    ]

    digest, synchronized = current_classification_input_digest(
        task, (unit,), classification, events
    )

    assert synchronized is True
    assert digest == classification_input_digest({**task, "subject_commit": "a" * 40}, (unit,))
