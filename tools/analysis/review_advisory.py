"""Read-only, unscored preparation advice from current native AI Flow reads."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import chdir
from pathlib import Path

if __name__ == "__main__":
    sys.dont_write_bytecode = True

from aiflow.gate import evaluate_gate  # noqa: E402
from aiflow.status_service import MISSING_BY_STATE, summarize_task  # noqa: E402
from aiflow.storage import validate_task_id  # noqa: E402

DEFAULT_REPOSITORY = Path(__file__).resolve().parents[2]
STATUS_VALUES = {
    "current_state": frozenset(MISSING_BY_STATE),
    "merge_readiness": {"not_applicable", "gate_required", "reverification_required"},
    "route": {"AUTO", "ASK", "REVIEW", "BLOCK"},
    "verification_level": {"V0", "V1", "V2"},
    "classification": {"fresh", "stale", "not_available"},
    "approvals": {"current", "stale", "not_available", "not_applicable"},
    "evidence": {"passed", "stale", "not_available"},
}
GATE_CODES = frozenset(
    (
        "GATE_BLOCKED",
        "GATE_STATE_INVALID",
        "GATE_REPOSITORY_CHANGED",
        "GATE_SCOPE_CHANGED",
        "GATE_CLASSIFICATION_STALE",
        "GATE_ROUTE_INVALID",
        "GATE_SPEC_STALE",
        "GATE_ASK_UNANSWERED",
        "GATE_SPEC_APPROVAL_STALE",
        "GATE_EVIDENCE_STALE",
        "GATE_EVIDENCE_NOT_PASSED",
        "GATE_V2_EVIDENCE_NOT_FINAL",
        "GATE_V2_SNAPSHOT_STALE",
        "GATE_V2_VERIFIER_NOT_INDEPENDENT",
        "GATE_V2_CONTEXT_STALE",
        "GATE_V2_REVIEW_STALE",
        "GATE_V2_CHECKS_INCOMPLETE",
        "GATE_V2_MUTATION_NOT_KILLED",
        "GATE_CODE_APPROVAL_STALE",
    )
)
PREPARATION = {
    "classification": "PREPARE_CLASSIFICATION_FACTS",
    "route_resolution": "CHECK_CLASSIFICATION_ROUTE",
    "spec_frozen": "PREPARE_SPEC_FREEZE",
    "begin": "CHECK_IMPLEMENTATION_PREREQUISITES",
    "implementation_result": "PREPARE_IMPLEMENTATION_RESULT",
    "verification_result": "CHECK_VERIFICATION_READINESS",
    "final_route": "CHECK_FINAL_ROUTE",
    "reverification": "CHECK_STALE_BINDINGS_AND_VERIFICATION_READINESS",
}
DECISIONS = {
    "ask_answer": "DECIDE_ASK_DIRECTION",
    "spec_approval": "CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION",
    "code_approval": "CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION",
    "external_merge": "CHECK_GATE_AND_EXTERNAL_ACTION_AUTHORIZATION",
    "retry_reason_or_escalation": "CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION",
    "block_resolution": "CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION",
    "escalation_resolution": "CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION",
}


def main(argv: list[str] | None = None) -> int:
    """Run one synchronous CLI read; this entry is not a concurrent library API."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id", metavar="TASK-ID")
    parser.add_argument("--repository", type=Path, default=DEFAULT_REPOSITORY, metavar="ROOT")
    arguments = parser.parse_args(argv)
    report: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": None,
        "probability_status": "unestimated",
        "execution_allowed": False,
        "native_status": None,
        "native_gate": {"status": "not_evaluated"},
        "mechanical_preparation": [],
        "decision_or_authorization_checks": [],
        "unknown": ["AUTHORIZATION_COVERAGE_NOT_EVALUATED"],
    }
    unknown = ["AUTHORIZATION_COVERAGE_NOT_EVALUATED"]
    exit_code = 0
    failure_code = "ADVISORY_INPUT_INVALID"
    try:
        validate_task_id(arguments.task_id)
        report["task_id"] = arguments.task_id
        repository = arguments.repository.resolve()
        previous_locks = os.environ.get("GIT_OPTIONAL_LOCKS")
        with chdir(repository):
            os.environ["GIT_OPTIONAL_LOCKS"] = "0"
            try:
                failure_code = "NATIVE_STATUS_READ_FAILED"
                summary = summarize_task(repository, arguments.task_id)
                status: dict[str, object] = {}
                for field, allowed in STATUS_VALUES.items():
                    value = getattr(summary, field)
                    if isinstance(value, str) and value in allowed:
                        status[field] = value
                    else:
                        status[field] = "unknown"
                        unknown.append("NATIVE_STATUS_FIELD_UNRECOGNIZED")
                status["worktree_dirty"] = (
                    summary.worktree_dirty if isinstance(summary.worktree_dirty, bool) else None
                )
                report["native_status"] = status
                preparation: set[str] = set()
                decisions: set[str] = set()
                if summary.current_state != "MERGED":
                    for missing in summary.missing_conditions:
                        if missing in PREPARATION:
                            preparation.add(PREPARATION[missing])
                        elif missing in DECISIONS:
                            decisions.add(DECISIONS[missing])
                        else:
                            unknown.append("NATIVE_MISSING_CONDITION_UNRECOGNIZED")
                if summary.current_state in {"FAILED", "BLOCKED", "ESCALATED"}:
                    preparation.clear()
                    decisions.add("CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION")
                report["mechanical_preparation"] = sorted(preparation)
                report["decision_or_authorization_checks"] = sorted(decisions)
                if summary.current_state == "APPROVED_FOR_MERGE":
                    failure_code = "NATIVE_GATE_READ_FAILED"
                    gate = evaluate_gate(repository, arguments.task_id)
                    reasons = [code for code in gate.reason_codes if code in GATE_CODES]
                    if len(reasons) != len(gate.reason_codes):
                        unknown.append("NATIVE_GATE_REASON_UNRECOGNIZED")
                    report["native_gate"] = {
                        "status": "evaluated",
                        "passed": gate.passed,
                        "reason_codes": reasons,
                    }
            finally:
                if previous_locks is None:
                    os.environ.pop("GIT_OPTIONAL_LOCKS", None)
                else:
                    os.environ["GIT_OPTIONAL_LOCKS"] = previous_locks
    except Exception:
        report["error_code"] = failure_code
        unknown.append(failure_code)
        exit_code = 1
    report["unknown"] = sorted(set(unknown))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
