"""Read-only, unscored preparation advice from current native AI Flow reads."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import chdir
from pathlib import Path
from typing import cast

if __name__ == "__main__":
    sys.dont_write_bytecode = True

from aiflow.contracts import SCHEMA_FILES  # noqa: E402
from aiflow.gate import evaluate_gate  # noqa: E402
from aiflow.git_context import collect_git_context  # noqa: E402
from aiflow.mutation_manifest import CANONICAL_MANIFEST_PATH  # noqa: E402
from aiflow.policy import POLICY_FILES  # noqa: E402
from aiflow.status_service import MISSING_BY_STATE, summarize_task  # noqa: E402
from aiflow.storage import resolve_task_path, validate_task_id  # noqa: E402

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


def _input_fingerprint(repository: Path, task_id: str) -> str | None:
    """Compare a finite input inventory; matching hashes do not prove atomic reads."""
    try:
        validate_task_id(task_id)
        root = repository.resolve()
        task = Path(".ai/tasks") / task_id
        tasks_directory = root / ".ai/tasks"
        if tasks_directory.exists() and not tasks_directory.is_dir():
            return None
        paths = {Path(".ai/repository-id"), CANONICAL_MANIFEST_PATH}
        paths.update(Path(".ai/policy") / name for name in POLICY_FILES)
        paths.update(Path(".ai/schemas") / name for name in SCHEMA_FILES.values())
        paths.update(
            task / name
            for name in (
                "task.yaml",
                "spec.md",
                "classification.json",
                "approvals.json",
                "evidence.json",
                "events.jsonl",
                "review-package.md",
                "creation_failed.json",
                "approval_pending.json",
            )
        )
        inventories: list[tuple[str, bool, list[str]]] = []
        for relative, pattern in (
            (Path(".ai/policy"), "*"),
            (task / "reviews", "*.json"),
            (task / "review-contexts", "*.json"),
            (task / "verifier-contexts", "*.json"),
        ):
            directory = root / relative
            if relative.is_relative_to(task):
                resolve_task_path(root, task_id, relative.relative_to(task))
            if not directory.resolve().is_relative_to(root):
                return None
            if directory.exists() and not directory.is_dir():
                return None
            entries = (
                sorted(entry for entry in directory.iterdir() if entry.match(pattern))
                if directory.is_dir()
                else []
            )
            inventories.append((relative.as_posix(), directory.is_dir(), [p.name for p in entries]))
            if relative != Path(".ai/policy"):
                paths.update(relative / entry.name for entry in entries)
        contents: list[tuple[str, str | None]] = []
        for relative in sorted(paths):
            path = root / relative
            if relative.is_relative_to(task):
                resolve_task_path(root, task_id, relative.relative_to(task))
            if path.parent.exists() and not path.parent.is_dir():
                return None
            boundary = path.parent.resolve()
            if not boundary.is_relative_to(root) or not path.resolve().is_relative_to(boundary):
                return None
            if path.exists() and not path.is_file():
                return None
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            contents.append((relative.as_posix(), digest))
        context = collect_git_context(root)
        if Path(context.repository_path).resolve() != root:
            return None
        payload = (
            context.repository_id,
            context.branch,
            context.head,
            context.worktree_dirty,
            context.dirty_paths,
            inventories,
            contents,
        )
        return hashlib.sha256(json.dumps(payload, ensure_ascii=True).encode("utf-8")).hexdigest()
    except Exception:
        return None


def _format_text(report: dict[str, object]) -> str:
    """Summarize the safe native projection without turning it into execution advice."""
    lines = ["Current facts:", f"  task={report['task_id'] or 'unknown'}"]
    status = cast(dict[str, object] | None, report["native_status"])
    if status is None:
        lines.append("  native_status=unknown")
    else:
        for field, value in status.items():
            if field != "missing_conditions":
                lines.append(f"  {field}={json.dumps(value, ensure_ascii=True)}")
    gate = cast(dict[str, object], report["native_gate"])
    lines.append(f"  native_gate={json.dumps(gate, ensure_ascii=True, sort_keys=True)}")
    lines.append("Missing / unknown:")
    if status is not None:
        missing = cast(list[str], status["missing_conditions"])
        lines.append(f"  native_missing_conditions={', '.join(missing) or 'none_reported'}")
    for code in cast(list[str], report["unknown"]):
        lines.append(f"  {code}")
    if "error_code" in report:
        lines.append(f"  error_code={report['error_code']}")
    lines.append("Next preparation / authorization checks (not execution):")
    basis = cast(list[dict[str, str]], report["advice_basis"])
    for item in basis:
        source_value = item.get("missing_condition", item.get("state", "unknown"))
        lines.append(f"  {item['advice']}: {item['source']}={source_value}")
    if not basis:
        lines.append("  none_in_native_projection; unknowns_above_remain")
    lines.append("Scope: probability_status=unestimated; execution_allowed=false")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run one synchronous CLI read; this entry is not a concurrent library API."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id", metavar="TASK-ID")
    parser.add_argument("--repository", type=Path, default=DEFAULT_REPOSITORY, metavar="ROOT")
    parser.add_argument("--format", choices=("json", "text"), default="json")
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
        "advice_basis": [],
        "unknown": [],
    }
    unknown = ["AUTHORIZATION_COVERAGE_NOT_EVALUATED", "SOURCE_READ_ATOMICITY_NOT_ESTABLISHED"]
    exit_code = 0
    failure_code = "ADVISORY_INPUT_INVALID"
    try:
        validate_task_id(arguments.task_id)
        report["task_id"] = arguments.task_id
        repository = arguments.repository.resolve()
        previous_locks = os.environ.get("GIT_OPTIONAL_LOCKS")
        with chdir(repository):
            os.environ["GIT_OPTIONAL_LOCKS"] = "0"
            before: str | None = None
            try:
                failure_code = "NATIVE_STATUS_READ_FAILED"
                before = _input_fingerprint(repository, arguments.task_id)
                summary = summarize_task(repository, arguments.task_id)
                status: dict[str, object] = {}
                for field, allowed in STATUS_VALUES.items():
                    value = getattr(summary, field)
                    if isinstance(value, str) and value in allowed:
                        status[field] = value
                    else:
                        status[field] = "unknown"
                        unknown.append("NATIVE_STATUS_FIELD_UNRECOGNIZED")
                for field in ("base_commit", "subject_commit", "observed_head"):
                    value = getattr(summary, field)
                    if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value):
                        status[field] = value
                    else:
                        status[field] = "unknown"
                        if field != "subject_commit" or value is not None:
                            unknown.append("NATIVE_STATUS_FIELD_UNRECOGNIZED")
                status["worktree_dirty"] = (
                    summary.worktree_dirty if isinstance(summary.worktree_dirty, bool) else None
                )
                known_missing: set[str] = set()
                for missing in summary.missing_conditions:
                    if isinstance(missing, str) and (
                        missing in PREPARATION or missing in DECISIONS
                    ):
                        known_missing.add(missing)
                    else:
                        unknown.append("NATIVE_MISSING_CONDITION_UNRECOGNIZED")
                status["missing_conditions"] = sorted(known_missing)
                report["native_status"] = status
                preparation: set[str] = set()
                decisions: set[str] = set()
                advice_basis: list[dict[str, str]] = []
                if summary.current_state != "MERGED":
                    for missing in sorted(known_missing):
                        if missing in PREPARATION:
                            advice = PREPARATION[missing]
                            preparation.add(advice)
                        else:
                            advice = DECISIONS[missing]
                            decisions.add(advice)
                        advice_basis.append(
                            {
                                "advice": advice,
                                "source": "native_status.missing_conditions",
                                "missing_condition": missing,
                            }
                        )
                if summary.current_state in {"FAILED", "BLOCKED", "ESCALATED"}:
                    diagnostic = "CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION"
                    advice_basis = [
                        basis
                        for basis in advice_basis
                        if basis["advice"] not in preparation and basis["advice"] != diagnostic
                    ]
                    preparation.clear()
                    decisions.add(diagnostic)
                    advice_basis.append(
                        {
                            "advice": diagnostic,
                            "source": "native_status.current_state",
                            "state": summary.current_state,
                        }
                    )
                report["mechanical_preparation"] = sorted(preparation)
                report["decision_or_authorization_checks"] = sorted(decisions)
                report["advice_basis"] = advice_basis
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
                try:
                    after = _input_fingerprint(repository, arguments.task_id)
                    if before is None or after is None:
                        unknown.append("SOURCE_INPUT_CHANGE_CHECK_UNAVAILABLE")
                    elif before != after:
                        unknown.append("SOURCE_INPUTS_CHANGED_DURING_READ")
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
    if arguments.format == "text":
        print(_format_text(report))
    else:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
