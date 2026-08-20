import json
from pathlib import Path

import pytest

from aiflow.freshness import evaluate_freshness


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
