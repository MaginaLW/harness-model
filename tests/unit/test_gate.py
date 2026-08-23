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


def test_v2_gate_requires_final_evidence_and_all_final_bindings() -> None:
    facts = GateFacts(**{**BASELINE, "verification_level": "V2"})  # type: ignore[arg-type]
    assert evaluate_gate_facts(facts).passed is True

    decision = evaluate_gate_facts(
        GateFacts(
            **{
                **BASELINE,
                "verification_level": "V2",
                "v2_final_evidence": False,
                "v2_snapshot_current": False,
                "v2_verifier_independent": False,
                "v2_context_current": False,
                "v2_reviews_current": False,
                "v2_checks_current": False,
                "v2_mutation_killed": False,
            }
        )  # type: ignore[arg-type]
    )

    assert decision.reason_codes == (
        "GATE_V2_EVIDENCE_NOT_FINAL",
        "GATE_V2_SNAPSHOT_STALE",
        "GATE_V2_VERIFIER_NOT_INDEPENDENT",
        "GATE_V2_CONTEXT_STALE",
        "GATE_V2_REVIEW_STALE",
        "GATE_V2_CHECKS_INCOMPLETE",
        "GATE_V2_MUTATION_NOT_KILLED",
    )


def test_v2_final_predicates_do_not_change_v1_gate_parity() -> None:
    decision = evaluate_gate_facts(
        GateFacts(
            **{
                **BASELINE,
                "v2_final_evidence": False,
                "v2_snapshot_current": False,
                "v2_verifier_independent": False,
                "v2_context_current": False,
                "v2_reviews_current": False,
                "v2_checks_current": False,
                "v2_mutation_killed": False,
            }
        )  # type: ignore[arg-type]
    )
    assert decision.passed is True
