import json
from pathlib import Path

import pytest

from aiflow.gate import GateFacts, evaluate_gate_facts

BASELINE = {
    "task_id": "TASK-0001",
    "current_state": "APPROVED_FOR_MERGE",
    "route": "AUTO",
    "verification_level": "V1",
}


@pytest.mark.parametrize(
    "row",
    json.loads(
        (Path(__file__).parents[1] / "fixtures" / "gate" / "decision-table.json").read_text(
            encoding="utf-8"
        )
    ),
    ids=lambda row: row["name"],
)
def test_gate_decision_table(row: dict[str, object]) -> None:
    changes = row["changes"]
    assert isinstance(changes, dict)
    decision = evaluate_gate_facts(GateFacts(**{**BASELINE, **changes}))  # type: ignore[arg-type]
    assert decision.passed is row["passed"]
    assert decision.reason_codes == tuple(row["reasons"])
    assert decision.task_id == "TASK-0001"
    if decision.passed:
        assert decision.recovery_argv == ()
    else:
        assert all(
            "TASK-0001" in command or command[0] == "git" for command in decision.recovery_argv
        )


def test_gate_json_is_stable_and_has_no_dynamic_time() -> None:
    decision = evaluate_gate_facts(GateFacts(**BASELINE))  # type: ignore[arg-type]
    assert decision.to_json() == decision.to_json()
    assert "time" not in decision.to_json().lower()
