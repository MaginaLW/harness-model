"""Report recorded AI Flow approval overhead without changing the ledger.

This tool deliberately reads ledger documents directly.  It does not evaluate
Policy, determine whether an approval is current, or infer whether a recorded
approval required a human interruption.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml

APPROVAL_TYPES = frozenset({"spec", "code", "action"})
ROUTES = frozenset({"AUTO", "ASK", "REVIEW", "BLOCK"})
REQUIRED_APPROVAL_FIELDS = frozenset(
    {
        "schema_version",
        "task_id",
        "decision_unit_id",
        "approval_type",
        "actor",
        "reason",
        "spec_sha256",
        "policy_sha256",
        "subject_commit",
        "approved_at",
    }
)
REQUIRED_EVENT_FIELDS = frozenset(
    {
        "schema_version",
        "task_id",
        "sequence",
        "from_state",
        "to_state",
        "event_type",
        "actor",
        "occurred_at",
        "payload",
    }
)


class LedgerDataError(ValueError):
    """A ledger document is missing or does not have the expected shape."""


def _error(task_id: str, filename: str, message: str) -> LedgerDataError:
    return LedgerDataError(f"{task_id}/{filename}: {message}")


def _read_json(path: Path, task_id: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise _error(task_id, path.name, "file is required") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _error(task_id, path.name, "invalid JSON") from error


def _read_yaml(path: Path, task_id: str) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise _error(task_id, path.name, "file is required") from error
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise _error(task_id, path.name, "invalid YAML") from error


def _require_mapping(value: Any, task_id: str, filename: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(task_id, filename, "must contain an object")
    return value


def _require_string(value: Any, task_id: str, filename: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise _error(task_id, filename, f"{field} must be a non-empty string")
    return value


def _binding(approval: dict[str, Any]) -> str:
    """Serialize the approval-type bindings used for record comparison only.

    The selected fields mirror the freshness bindings: spec approvals intentionally
    omit ``subject_commit``; code approvals add subject and evidence; action
    approvals add subject, exact action, expiry, and single-use data.
    """
    approval_type = approval["approval_type"]
    fields = ["task_id", "decision_unit_id", "base_commit", "policy_sha256", "spec_sha256"]
    if approval_type == "code":
        fields.extend(("subject_commit", "evidence_sha256"))
    elif approval_type == "action":
        fields.extend(("subject_commit", "action_sha256", "expires_at", "single_use"))
    return json.dumps(
        {key: approval.get(key) for key in fields},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _read_events(path: Path, task_id: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise _error(task_id, path.name, "file is required") from error
    except (OSError, UnicodeError) as error:
        raise _error(task_id, path.name, "cannot be read") from error
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise _error(task_id, path.name, f"blank line at {line_number}")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise _error(task_id, path.name, f"invalid JSON at line {line_number}") from error
        event = _require_mapping(event, task_id, path.name)
        if not REQUIRED_EVENT_FIELDS.issubset(event):
            raise _error(task_id, path.name, f"missing required fields at line {line_number}")
        if event["task_id"] != task_id or not isinstance(event["event_type"], str):
            raise _error(task_id, path.name, f"invalid task_id or event_type at line {line_number}")
        events.append(event)
    return events


def _task_directories(repository: Path) -> Iterable[Path]:
    root = repository / ".ai" / "tasks"
    if not root.is_dir():
        raise LedgerDataError(".ai/tasks: directory is required")
    directories = sorted(
        path for path in root.iterdir() if path.is_dir() and path.name.startswith("TASK-")
    )
    if not directories:
        raise LedgerDataError(".ai/tasks: no task directories found")
    return directories


def build_report(repository: Path) -> dict[str, Any]:
    """Build the report from ledger records, making no filesystem mutations."""
    states: Counter[str] = Counter()
    routes: Counter[str] = Counter()
    approval_types: Counter[str] = Counter()
    event_types: Counter[str] = Counter()
    approval_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    approval_total = 0
    event_total = 0
    escalations = 0
    failures = 0

    for directory in _task_directories(repository):
        task_id = directory.name
        task = _require_mapping(_read_yaml(directory / "task.yaml", task_id), task_id, "task.yaml")
        if _require_string(task.get("task_id"), task_id, "task.yaml", "task_id") != task_id:
            raise _error(task_id, "task.yaml", "task_id does not match directory")
        states[
            _require_string(task.get("current_state"), task_id, "task.yaml", "current_state")
        ] += 1

        classification_path = directory / "classification.json"
        if not classification_path.exists():
            route = "not_available"
        else:
            classification = _require_mapping(
                _read_json(classification_path, task_id), task_id, "classification.json"
            )
            if classification.get("task_id") != task_id:
                raise _error(task_id, "classification.json", "task_id does not match directory")
            route = classification.get("effective_route")
            if not isinstance(route, str) or route not in ROUTES:
                raise _error(task_id, "classification.json", "effective_route is invalid")
        routes[route] += 1

        approvals = _read_json(directory / "approvals.json", task_id)
        if not isinstance(approvals, list):
            raise _error(task_id, "approvals.json", "must contain an array")
        for index, approval in enumerate(approvals):
            approval = _require_mapping(approval, task_id, "approvals.json")
            if not REQUIRED_APPROVAL_FIELDS.issubset(approval):
                raise _error(task_id, "approvals.json", f"missing required fields at index {index}")
            approval_type = approval.get("approval_type")
            if not isinstance(approval_type, str) or approval_type not in APPROVAL_TYPES:
                raise _error(
                    task_id, "approvals.json", f"approval_type is invalid at index {index}"
                )
            if approval.get("task_id") != task_id:
                raise _error(
                    task_id, "approvals.json", f"task_id does not match directory at index {index}"
                )
            decision_unit_id = _require_string(
                approval.get("decision_unit_id"), task_id, "approvals.json", "decision_unit_id"
            )
            if approval_type == "action" and not {
                "action_sha256",
                "expires_at",
                "single_use",
            }.issubset(approval):
                raise _error(
                    task_id, "approvals.json", f"action approval is incomplete at index {index}"
                )
            approval_groups[(task_id, decision_unit_id, approval_type)].append(approval)
            approval_types[approval_type] += 1
            approval_total += 1

        events = _read_events(directory / "events.jsonl", task_id)
        event_total += len(events)
        for event in events:
            event_types[event["event_type"]] += 1
            escalations += int(event["event_type"] in {"task_escalated", "verification_escalated"})
            failures += int(event["event_type"] == "verification_failed")

    group_rows: list[dict[str, Any]] = []
    same_binding_by_type: Counter[str] = Counter()
    for (task_id, decision_unit_id, approval_type), records in sorted(approval_groups.items()):
        seen_bindings: set[str] = set()
        same_binding_subsequent = 0
        for record in records:
            binding = _binding(record)
            if binding in seen_bindings:
                same_binding_subsequent += 1
            seen_bindings.add(binding)
        same_binding_by_type[approval_type] += same_binding_subsequent
        group_rows.append(
            {
                "task_id": task_id,
                "decision_unit_id": decision_unit_id,
                "approval_type": approval_type,
                "record_count": len(records),
                "first_records": int(bool(records)),
                "subsequent_records": max(0, len(records) - 1),
                "same_binding_subsequent_records": same_binding_subsequent,
            }
        )

    return {
        "schema_version": "1.0",
        "measurement": "ledger_record_proxy",
        "limitations": [
            "Counts are ledger records, not verified human interruptions or review time.",
            "The ledger does not provide defect-escape rates.",
            "Same-binding subsequent records are repeated records; they do not prove redundant "
            "authorization.",
            "The tool does not re-evaluate Policy, authorization validity, or approval freshness.",
        ],
        "tasks": {
            "total": sum(states.values()),
            "by_state": dict(sorted(states.items())),
            "by_route": dict(sorted(routes.items())),
        },
        "approvals": {
            "total": approval_total,
            "first_records": len(approval_groups),
            "subsequent_records": approval_total - len(approval_groups),
            "by_type": dict(sorted(approval_types.items())),
            "by_task_decision_unit_type": group_rows,
            "same_binding_subsequent_records_by_type": dict(sorted(same_binding_by_type.items())),
        },
        "events": {
            "total": event_total,
            "by_type": dict(sorted(event_types.items())),
            "escalation_events": escalations,
            "verification_failed_events": failures,
        },
        "unavailable": {
            "human_interruptions": "unavailable",
            "human_review_time": "unavailable",
            "defect_escape_rate": "unavailable",
        },
    }


def _text(report: dict[str, Any]) -> str:
    tasks = report["tasks"]
    approvals = report["approvals"]
    events = report["events"]
    lines = [
        "Approval overhead report (ledger-record proxy; read-only)",
        f"Tasks: {tasks['total']} | state: {tasks['by_state']} | route: {tasks['by_route']}",
        "Approvals: "
        f"{approvals['total']} | first: {approvals['first_records']} | "
        f"subsequent: {approvals['subsequent_records']} | by type: {approvals['by_type']}",
        "Same-binding subsequent records by type: "
        f"{approvals['same_binding_subsequent_records_by_type']}",
        "Events: "
        f"{events['total']} | escalated: {events['escalation_events']} | "
        f"verification_failed: {events['verification_failed_events']}",
        "Limit: repeated records do not prove redundant authorization; human interruption/time "
        "and defect escape are unavailable.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only AI Flow approval-overhead ledger report"
    )
    parser.add_argument("repository", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("text", "json"), default="text")
    arguments = parser.parse_args(argv)
    try:
        report = build_report(arguments.repository.resolve())
    except LedgerDataError as error:
        print(f"approval-overhead: {error}", file=sys.stderr)
        return 2
    if arguments.format == "json":
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
