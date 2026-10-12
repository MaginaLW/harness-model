"""Report recorded AI Flow approval overhead without changing the ledger.

This tool deliberately reads ledger documents directly.  It does not evaluate
Policy, determine whether an approval is current, or infer whether a recorded
approval required a human interruption.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
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
SNAPSHOT_PATH = re.compile(
    r"\.ai/tasks/(TASK-[0-9]{4,})/(?:task\.yaml|classification\.json|events\.jsonl|"
    r"evidence\.json|reviews/REV-[0-9]{4,}-r[0-9]{4,}\.json|"
    r"review-contexts/[0-9a-f]{64}\.json)"
)
SNAPSHOT_PATTERNS = {
    "schema_version": r"(?:1|2)\.0",
    "repository_id": r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
    "current_state": r"[A-Z][A-Z_]{0,63}",
    "from_state": r"[A-Z][A-Z_]{0,63}",
    "to_state": r"[A-Z][A-Z_]{0,63}",
    "event_type": r"[a-z][a-z_]{0,63}",
    "effective_route": r"AUTO|ASK|REVIEW|BLOCK",
    "effective_verification_level": r"V[012]",
    "review_id": r"REV-[0-9]{4,}",
    "finding_id": r"RF-[0-9]{3,}",
    "severity": r"critical|high|medium|low",
    "finding_status": r"open|resolved",
    "review_stage": r"design|implementation",
    "outcome": r"APPROVE|APPROVE_WITH_CONDITIONS|REQUEST_CHANGES|REJECT|BLOCKED",
    "conclusion": r"passed|failed|provisional",
    "phase": r"pre_implementation_review|final",
    "verification_level": r"V[012]",
    "mode": r"local|ci",
    "status": r"passed|failed|unverified|skipped|cancelled|not_run|partial|unknown",
    "check_id": r"[a-z][a-z0-9_-]{0,63}",
    "category": r"[a-z][a-z0-9_-]{0,63}",
    "generated_at": r"[0-9TZ:.+\-]{20,40}",
    "recorded_at": r"[0-9TZ:.+\-]{20,40}",
    "occurred_at": r"[0-9TZ:.+\-]{20,40}",
    **dict.fromkeys(("base_commit", "subject_commit", "attestation_head"), r"[0-9a-f]{40}"),
    **dict.fromkeys(
        (
            "frozen_spec_sha256",
            "spec_sha256",
            "policy_sha256",
            "classification_input_sha256",
            "context_sha256",
            "evidence_sha256",
            "verification_snapshot_sha256",
        ),
        r"[0-9a-f]{64}",
    ),
}


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


def _snapshot_git(repository: Path, *arguments: str, data: bytes | None = None) -> bytes:
    environment = {
        key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_ALLOW_PROTOCOL": "",
        }
    )
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", "--no-pager", "-C", str(repository), *arguments],
            input=data,
            capture_output=True,
            env=environment,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise LedgerDataError("snapshot: committed Git inputs could not be read") from error
    return result.stdout


def _snapshot_blobs(repository: Path) -> tuple[str, dict[str, tuple[str, bytes]]]:
    commit = _snapshot_git(repository, "rev-parse", "--verify", "HEAD").decode().strip()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise LedgerDataError("snapshot: invalid source commit")
    tree = _snapshot_git(repository, "ls-tree", "-r", "-z", commit, "--", ".ai/tasks")
    selected: dict[str, str] = {}
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        path = name.decode("utf-8", errors="replace")
        if SNAPSHOT_PATH.fullmatch(path) is None:
            continue
        mode, kind, oid = metadata.decode("ascii").split()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise LedgerDataError("snapshot: ledger input must be a regular Git blob")
        selected[path] = oid
    if not selected:
        raise LedgerDataError("snapshot: no committed ledger inputs found")
    selected = dict(sorted(selected.items()))
    batch = _snapshot_git(
        repository,
        "cat-file",
        "--batch",
        data="".join(f"{oid}\n" for oid in selected.values()).encode("ascii"),
    )
    blobs: dict[str, tuple[str, bytes]] = {}
    offset = 0
    for path, oid in selected.items():
        end = batch.find(b"\n", offset)
        header = batch[offset:end].split()
        if end < 0 or len(header) != 3 or header[:2] != [oid.encode(), b"blob"]:
            raise LedgerDataError("snapshot: invalid Git blob response")
        try:
            size = int(header[2])
        except ValueError as error:
            raise LedgerDataError("snapshot: invalid Git blob length") from error
        offset = end + 1
        contents = batch[offset : offset + size]
        offset += size
        if size < 0 or len(contents) != size or batch[offset : offset + 1] != b"\n":
            raise LedgerDataError("snapshot: incomplete Git blob response")
        offset += 1
        blobs[path] = (oid, contents)
    if offset != len(batch):
        raise LedgerDataError("snapshot: unexpected Git blob response")
    return commit, blobs


def _unique_snapshot_mapping(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in mapping:
            raise ValueError("snapshot mapping keys must be unique strings")
        mapping[key] = value
    return mapping


class _SnapshotLoader(yaml.SafeLoader):
    def construct_mapping(self, node: Any, deep: bool = False) -> dict[str, Any]:
        self.flatten_mapping(node)
        return _unique_snapshot_mapping(
            (self.construct_object(key, deep=deep), self.construct_object(value, deep=deep))
            for key, value in node.value
        )


def _snapshot_document(contents: bytes, task_id: str, filename: str) -> dict[str, Any]:
    try:
        value = (
            yaml.load(contents, Loader=_SnapshotLoader)
            if filename == "task.yaml"
            else json.loads(contents, object_pairs_hook=_unique_snapshot_mapping)
        )
    except (UnicodeError, ValueError, yaml.YAMLError) as error:
        raise _error(task_id, filename, "invalid document") from error
    value = _require_mapping(value, task_id, filename)
    if value.get("task_id") != task_id:
        raise _error(task_id, filename, "task_id does not match directory")
    return value


def _snapshot_fields(
    document: dict[str, Any], fields: Iterable[str], task_id: str, filename: str
) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for field in fields:
        value = document.get(field)
        if value is None:
            facts[field] = "unknown"
        elif not isinstance(value, str) or re.fullmatch(SNAPSHOT_PATTERNS[field], value) is None:
            raise _error(task_id, filename, f"{field} is invalid")
        else:
            facts[field] = value
    return facts


def _snapshot_findings(review: dict[str, Any], task_id: str) -> list[dict[str, Any]]:
    findings = review.get("findings")
    if not isinstance(findings, list):
        raise _error(task_id, "review.json", "findings must contain an array")
    projected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for finding in findings:
        finding = _require_mapping(finding, task_id, "review.json")
        if any(finding.get(field) is None for field in ("finding_id", "severity", "status")):
            raise _error(task_id, "review.json", "missing required finding fields")
        facts = _snapshot_fields(
            {**finding, "finding_status": finding["status"]},
            ("finding_id", "severity", "finding_status"),
            task_id,
            "review.json",
        )
        if facts["finding_id"] in seen:
            raise _error(task_id, "review.json", "finding IDs must be unique within a revision")
        seen.add(facts["finding_id"])
        resolved_at = "not_applicable"
        if facts["finding_status"] == "open":
            if "resolution" in finding:
                raise _error(task_id, "review.json", "open finding cannot contain resolution")
        else:
            resolution = _require_mapping(finding.get("resolution"), task_id, "review.json")
            value = resolution.get("resolved_at")
            if (
                not isinstance(value, str)
                or re.fullmatch(
                    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                    r"(?:\.[0-9]+)?(?:Z|[+\-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
                    value,
                )
                is None
            ):
                raise _error(task_id, "review.json", "resolved_at is invalid")
            try:
                datetime.fromisoformat(value)
            except ValueError as error:
                raise _error(task_id, "review.json", "resolved_at is invalid") from error
            resolved_at = value
        projected.append(
            {
                "finding_id": facts["finding_id"],
                "severity": facts["severity"],
                "status": facts["finding_status"],
                "resolved_at": resolved_at,
            }
        )
    return projected


def build_snapshot(repository: Path, *, include_feedback: bool = False) -> dict[str, Any]:
    """Describe committed ledger facts, without reading working files or private logs."""
    commit, blobs = _snapshot_blobs(repository)
    task_ids = sorted({path.split("/")[2] for path in blobs})
    rows: list[dict[str, Any]] = []
    missing: Counter[str] = Counter()
    binding_fields = ("base_commit", "subject_commit", "spec_sha256", "policy_sha256")
    for task_id in task_ids:
        prefix = f".ai/tasks/{task_id}/"
        documents: dict[str, dict[str, Any]] = {}
        for filename in ("task.yaml", "classification.json", "evidence.json"):
            source = blobs.get(prefix + filename)
            if source is None:
                if filename == "task.yaml":
                    raise _error(task_id, filename, "committed file is required")
                missing[filename] += 1
                continue
            documents[filename] = _snapshot_document(source[1], task_id, filename)
        task = documents["task.yaml"]
        _require_string(task.get("current_state"), task_id, "task.yaml", "current_state")
        row: dict[str, Any] = {
            "task_id": task_id,
            "dependence_group": task_id,
            "task": _snapshot_fields(
                task,
                ("schema_version", "repository_id", "current_state", "frozen_spec_sha256")
                + binding_fields[:2],
                task_id,
                "task.yaml",
            ),
            "classification": "unknown",
            "reviews": [],
            "verification_attempts": [],
            "evidence": "unknown",
        }
        if "classification.json" in documents:
            classification = documents["classification.json"]
            _require_string(
                classification.get("effective_route"),
                task_id,
                "classification.json",
                "effective_route",
            )
            row["classification"] = _snapshot_fields(
                classification,
                ("effective_route", "effective_verification_level", "classification_input_sha256")
                + binding_fields,
                task_id,
                "classification.json",
            )
        event_source = blobs.get(prefix + "events.jsonl")
        if event_source is None:
            raise _error(task_id, "events.jsonl", "committed file is required")
        events: list[dict[str, Any]] = []
        active: dict[str, Any] | None = None
        try:
            lines = event_source[1].decode("utf-8").splitlines()
        except UnicodeError as error:
            raise _error(task_id, "events.jsonl", "invalid encoding") from error
        if not lines:
            raise _error(task_id, "events.jsonl", "event records are required")
        previous_sequence = 0
        for line in lines:
            event = _snapshot_document(line.encode(), task_id, "events.jsonl")
            sequence = event.get("sequence")
            if (
                not REQUIRED_EVENT_FIELDS.issubset(event)
                or type(sequence) is not int
                or sequence <= previous_sequence
            ):
                raise _error(task_id, "events.jsonl", "invalid fields or sequence")
            if any(
                event.get(field) is None
                for field in ("event_type", "from_state", "to_state", "occurred_at")
            ):
                raise _error(task_id, "events.jsonl", "missing required event facts")
            previous_sequence = sequence
            facts = {
                "sequence": sequence,
                **_snapshot_fields(
                    event,
                    ("event_type", "from_state", "to_state", "occurred_at"),
                    task_id,
                    "events.jsonl",
                ),
            }
            payload = _require_mapping(event["payload"], task_id, "events.jsonl")
            facts.update(
                _snapshot_fields(
                    payload, ("effective_route", "conclusion"), task_id, "events.jsonl"
                )
            )
            if facts["event_type"] in {"review_recorded", "review_finding_resolved"}:
                facts.update(
                    _snapshot_fields(
                        payload,
                        ("review_id", "review_stage", "context_sha256"),
                        task_id,
                        "events.jsonl",
                    )
                )
                revision = payload.get("revision")
                if revision is not None and (type(revision) is not int or revision < 1):
                    raise _error(task_id, "events.jsonl", "review revision is invalid")
                facts["revision"] = "unknown" if revision is None else revision
                if include_feedback and facts["event_type"] == "review_finding_resolved":
                    if payload.get("finding_id") is None:
                        raise _error(task_id, "events.jsonl", "finding_id is required")
                    facts.update(
                        _snapshot_fields(payload, ("finding_id",), task_id, "events.jsonl")
                    )
            events.append(facts)
            if facts["event_type"] in {"verification_started", "verification_restarted"}:
                active = {
                    "stage": "verification",
                    "start_sequence": sequence,
                    "result_sequence": "unknown",
                    "original_result": "unknown",
                }
                row["verification_attempts"].append(active)
            elif facts["event_type"] in {
                "verification_passed",
                "verification_failed",
                "verification_checked",
            }:
                expected = {
                    "verification_passed": "passed",
                    "verification_failed": "failed",
                    "verification_checked": "provisional",
                }[facts["event_type"]]
                if facts["conclusion"] not in {expected, "unknown"}:
                    raise _error(task_id, "events.jsonl", "event and conclusion conflict")
                if active is None:
                    active = {"stage": "verification", "start_sequence": "unknown"}
                    row["verification_attempts"].append(active)
                active.update(
                    {
                        "result_sequence": sequence,
                        "original_result": facts["conclusion"],
                        "to_state": facts["to_state"],
                    }
                )
                active = None
        row["events"] = events
        row["history_completeness"] = "unknown"
        row["historical_first_result"] = "unknown"
        row["evidence_attempt_linkage"] = "unknown"
        for path, (_, contents) in blobs.items():
            if not path.startswith(prefix + "reviews/"):
                continue
            review = _snapshot_document(contents, task_id, "review.json")
            revision = review.get("revision")
            if type(revision) is not int or revision < 1:
                raise _error(task_id, "review.json", "revision is invalid")
            if not all(
                review.get(field) is not None
                for field in (
                    "review_id",
                    "review_stage",
                    "outcome",
                    "context_sha256",
                    "recorded_at",
                )
            ):
                raise _error(task_id, "review.json", "missing required fields")
            if path.rsplit("/", 1)[1] != f"{review['review_id']}-r{revision:04d}.json":
                raise _error(task_id, "review.json", "identity does not match source filename")
            review_facts = {
                "source_ref": path,
                "revision": revision,
                **_snapshot_fields(
                    review,
                    ("review_id", "review_stage", "outcome", "context_sha256", "recorded_at"),
                    task_id,
                    "review.json",
                ),
                "context": "unknown",
                "context_linkage": "unknown",
                "event_links": [],
            }
            if include_feedback:
                review_facts["findings"] = _snapshot_findings(review, task_id)
            context_path = prefix + f"review-contexts/{review['context_sha256']}.json"
            context_source = blobs.get(context_path)
            if context_source is not None:
                context = _snapshot_document(context_source[1], task_id, "review-context.json")
                stable = {key: value for key, value in context.items() if key != "context_sha256"}
                canonical = json.dumps(
                    stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                if digest != review["context_sha256"] or context.get("context_sha256") != digest:
                    raise _error(
                        task_id, "review-context.json", "context digest does not match source"
                    )
                context_facts = {
                    "source_ref": context_path,
                    **_snapshot_fields(
                        context,
                        (
                            "schema_version",
                            "review_stage",
                            "context_sha256",
                            "base_commit",
                            "spec_sha256",
                            "policy_sha256",
                            "classification_input_sha256",
                            "subject_commit",
                            "evidence_sha256",
                            "verification_snapshot_sha256",
                        ),
                        task_id,
                        "review-context.json",
                    ),
                }
                stage = context_facts["review_stage"]
                version = context_facts["schema_version"]
                if stage not in {"design", "implementation"} or version not in {"1.0", "2.0"}:
                    raise _error(
                        task_id, "review-context.json", "context stage or version is invalid"
                    )
                inapplicable = (
                    ("subject_commit", "evidence_sha256", "verification_snapshot_sha256")
                    if stage == "design"
                    else ("verification_snapshot_sha256",)
                    if version == "1.0"
                    else ("evidence_sha256",)
                )
                if (stage == "design" and version != "1.0") or any(
                    field in context for field in inapplicable
                ):
                    raise _error(task_id, "review-context.json", "inapplicable context binding")
                context_facts.update(dict.fromkeys(inapplicable, "not_applicable"))
                review_facts["context"] = context_facts
                review_facts["context_linkage"] = (
                    "matched" if stage == review_facts["review_stage"] else "mismatched"
                )
            for event in events:
                if (
                    event.get("review_id") != review["review_id"]
                    or event.get("revision") != revision
                ):
                    continue
                binding = "revision_reference"
                if event["event_type"] == "review_recorded":
                    comparisons = [
                        event[field] == review[field]
                        for field in ("review_stage", "context_sha256")
                        if event[field] != "unknown"
                    ]
                    binding = (
                        "mismatched"
                        if not all(comparisons)
                        else "matched"
                        if len(comparisons) == 2
                        else "unknown"
                    )
                link = {
                    "sequence": event["sequence"],
                    "event_type": event["event_type"],
                    "binding": binding,
                }
                if include_feedback and event["event_type"] == "review_finding_resolved":
                    link["finding_id"] = event["finding_id"]
                    link["binding"] = (
                        "finding_revision_reference"
                        if any(
                            finding["finding_id"] == event["finding_id"]
                            and finding["status"] == "resolved"
                            for finding in review_facts["findings"]
                        )
                        else "mismatched"
                    )
                review_facts["event_links"].append(link)
            row["reviews"].append(review_facts)
        missing["reviews"] += int(not row["reviews"])
        missing["verification_attempts"] += int(not row["verification_attempts"])
        if "evidence.json" in documents:
            evidence = documents["evidence.json"]
            checks = evidence.get("checks")
            if not isinstance(checks, list) or evidence.get("conclusion") is None:
                raise _error(task_id, "evidence.json", "checks or conclusion is invalid")
            projected_checks = []
            for check in checks:
                check = _require_mapping(check, task_id, "evidence.json")
                if not all(
                    check.get(field) is not None for field in ("check_id", "category", "status")
                ):
                    raise _error(task_id, "evidence.json", "missing required check fields")
                projected = _snapshot_fields(
                    check, ("check_id", "category", "status"), task_id, "evidence.json"
                )
                for field, expected_type in (
                    ("required", bool),
                    ("exit_code", int),
                    ("timed_out", bool),
                    ("duration_ms", int),
                ):
                    value = check.get(field)
                    if value is not None and type(value) is not expected_type:
                        raise _error(task_id, "evidence.json", f"{field} is invalid")
                    if field == "duration_ms" and isinstance(value, int) and value < 0:
                        raise _error(task_id, "evidence.json", "duration_ms is invalid")
                    projected[field] = "unknown" if value is None else value
                projected_checks.append(projected)
            row["evidence"] = {
                **_snapshot_fields(
                    evidence,
                    (
                        "schema_version",
                        "phase",
                        "verification_level",
                        "mode",
                        "conclusion",
                        "generated_at",
                        "attestation_head",
                        "verification_snapshot_sha256",
                    )
                    + binding_fields,
                    task_id,
                    "evidence.json",
                ),
                "checks": projected_checks,
            }
        rows.append(row)
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "measurement": "tracked_ledger_snapshot",
        "source_commit": commit,
        "executed_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sources": [{"ref": path, "git_blob": oid} for path, (oid, _) in blobs.items()],
        "tasks": rows,
        "coverage": {
            "task_records": len(rows),
            "review_records": sum(len(row["reviews"]) for row in rows),
            "review_records_with_context": sum(
                review["context"] != "unknown" for row in rows for review in row["reviews"]
            ),
            "review_records_with_matching_record_event": sum(
                any(link["binding"] == "matched" for link in review["event_links"])
                for row in rows
                for review in row["reviews"]
            ),
            "missing_tasks_by_field": dict(sorted(missing.items())),
            "actual_model_unknown_tasks": len(rows),
            "human_work_minutes_unknown_tasks": len(rows),
            "cost_unknown_tasks": len(rows),
            "host_events_unknown_tasks": len(rows),
        },
        "unknown": dict.fromkeys(
            (
                "actual_model",
                "human_interruptions",
                "human_work_minutes",
                "cost",
                "host_events",
                "defect_escape_rate",
            ),
            "unknown",
        ),
        "limitations": [
            "Committed ledger statements were not reverified; "
            "this is not acceptance or authorization.",
            "Task groups are conservative dependencies, not a certified independent sample count.",
            "Checks, findings, review revisions and retries are child records, "
            "not independent samples.",
            "Event ordering only locates recorded attempts; "
            "completeness and evidence linkage are unknown.",
            "Review links compare committed references and context content hashes only; "
            "they do not establish freshness, review correctness, identity or authorization.",
            "Logs, free text, actors, identity, working files "
            "and external/private sources are excluded.",
        ],
    }
    if include_feedback:
        report["feedback_projection"] = True
    return report


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


def build_availability(repository: Path) -> dict[str, Any]:
    """Map existing projections to candidate requirements; do not estimate a target."""
    snapshot = build_snapshot(repository)
    common = [
        "candidate_version_bindings",
        "actual_model_identity",
        "task_conditions",
        "acceptance_protocol",
        "dependency_independence",
    ]
    author = [
        *common,
        "verification_evidence",
        "recorded_verification_results",
        "review_results",
        "evidence_attempt_linkage",
    ]
    reviewer = [
        *common,
        "review_results",
        "review_context_bindings",
        "review_event_references",
        "review_information_and_budget",
        "defect_report_matching",
    ]
    targets = {
        "author_first_acceptance": {
            "denominator_definition": "Predeclared first candidates in included attempt chains.",
            "required_facts": [*author, "first_candidate_lineage"],
        },
        "author_after_repair_acceptance": {
            "denominator_definition": (
                "Included chains that actually entered the declared repair strategy."
            ),
            "required_facts": [*author, "repair_candidate_lineage", "repair_strategy_and_budget"],
        },
        "review_detection": {
            "denominator_definition": (
                "Predeclared review units with independently adjudicated actionable defects."
            ),
            "required_facts": [*reviewer, "independent_positive_truth"],
        },
        "review_false_positive": {
            "denominator_definition": (
                "Predeclared review opportunities independently adjudicated without "
                "the corresponding actionable defect."
            ),
            "required_facts": [*reviewer, "independent_negative_truth_and_opportunities"],
        },
    }
    not_projected = (
        "actual_model_identity",
        "task_conditions",
        "acceptance_protocol",
        "dependency_independence",
        "repair_strategy_and_budget",
        "independent_positive_truth",
        "independent_negative_truth_and_opportunities",
        "defect_report_matching",
        "review_information_and_budget",
    )
    rows: list[dict[str, Any]] = []
    counts: dict[str, Counter[str]] = {}
    for task in snapshot["tasks"]:
        prefix = f".ai/tasks/{task['task_id']}/"
        events_ref = prefix + "events.jsonl"
        reviews = task["reviews"]
        review_refs = [review["source_ref"] for review in reviews]
        context_refs = sorted(
            {
                review["context"]["source_ref"]
                for review in reviews
                if review["context"] != "unknown"
            }
        )
        attempts = task["verification_attempts"]
        evidence_present = task["evidence"] != "unknown"
        if not reviews or any(review["context"] == "unknown" for review in reviews):
            context_availability = "source_missing"
        elif all(review["context_linkage"] == "matched" for review in reviews):
            context_availability = "projected"
        else:
            context_availability = "linkage_unknown"
        facts = {
            "candidate_version_bindings": {
                "availability": "projected"
                if all(
                    task["task"][field] != "unknown" for field in ("base_commit", "subject_commit")
                )
                else "linkage_unknown",
                "source_refs": [prefix + "task.yaml"],
            },
            "verification_evidence": {
                "availability": "projected" if evidence_present else "source_missing",
                "source_refs": [prefix + "evidence.json"] if evidence_present else [],
            },
            "recorded_verification_results": {
                "availability": "projected"
                if attempts and all(attempt["original_result"] != "unknown" for attempt in attempts)
                else "linkage_unknown",
                "source_refs": [events_ref],
            },
            "review_results": {
                "availability": "projected" if reviews else "source_missing",
                "source_refs": review_refs,
            },
            "review_context_bindings": {
                "availability": context_availability,
                "source_refs": [*review_refs, *context_refs],
            },
            "review_event_references": {
                "availability": "projected"
                if reviews
                and all(
                    review["event_links"]
                    and all(
                        link["binding"] in {"matched", "revision_reference"}
                        for link in review["event_links"]
                    )
                    for review in reviews
                )
                else "linkage_unknown",
                "source_refs": [events_ref, *review_refs],
            },
        }
        for fact in (
            "first_candidate_lineage",
            "repair_candidate_lineage",
            "evidence_attempt_linkage",
        ):
            facts[fact] = {"availability": "linkage_unknown", "source_refs": [events_ref]}
        for fact in not_projected:
            facts[fact] = {"availability": "not_projected", "source_refs": []}
        for name, fact in facts.items():
            counts.setdefault(name, Counter())[fact["availability"]] += 1
        rows.append(
            {
                "task_id": task["task_id"],
                "dependence_group": task["dependence_group"],
                "facts": facts,
                "observations": task,
            }
        )
    return {
        "schema_version": "1.0",
        "measurement": "confidence_evidence_availability",
        "probability_status": "unestimated",
        "method_status": "design_pending",
        "execution_allowed": False,
        "source_commit": snapshot["source_commit"],
        "executed_tool_sha256": snapshot["executed_tool_sha256"],
        "sources": snapshot["sources"],
        "targets": targets,
        "tasks": rows,
        "coverage": {
            "task_records": len(rows),
            "by_fact": {
                name: {
                    status: count[status]
                    for status in (
                        "projected",
                        "source_missing",
                        "not_projected",
                        "linkage_unknown",
                    )
                }
                for name, count in sorted(counts.items())
            },
        },
        "unknown": snapshot["unknown"],
        "limitations": [
            *snapshot["limitations"],
            "Availability describes projections and references, "
            "not target eligibility or estimability.",
            "Source missing means at least one needed allowlisted source is absent at this commit; "
            "not projected does not establish absence in the original repository.",
            "Task fact counts are not statistical denominators or independent sample counts.",
            "Target definitions are candidates; population, protocol, truth, "
            "precision and use are not frozen.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only AI Flow approval-overhead ledger report"
    )
    parser.add_argument("repository", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("text", "json"), default="text")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--snapshot", action="store_true", help="Describe allowlisted committed HEAD facts"
    )
    modes.add_argument(
        "--availability", action="store_true", help="Map non-scoring target evidence availability"
    )
    arguments = parser.parse_args(argv)
    try:
        repository = arguments.repository.resolve()
        if arguments.availability:
            report = build_availability(repository)
        elif arguments.snapshot:
            report = build_snapshot(repository)
        else:
            report = build_report(repository)
    except LedgerDataError as error:
        print(f"approval-overhead: {error}", file=sys.stderr)
        return 2
    if arguments.format == "json":
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    elif arguments.availability:
        print(
            "Confidence evidence availability (read-only; unestimated): "
            f"{report['source_commit']}\n"
            "Method: design_pending | execution_allowed=false\n"
            f"Task records: {report['coverage']['task_records']}"
        )
        for name, count in report["coverage"]["by_fact"].items():
            print(f"{name}: {count}")
        print("Task fact counts are not statistical denominators or independent sample counts.")
    elif arguments.snapshot:
        print(
            f"Tracked ledger snapshot (read-only; not reverified): {report['source_commit']}\n"
            f"Coverage: {report['coverage']}\n"
            "Actual model, human time, cost and host events: unknown.\n"
            "Checks, review revisions and retries do not increase independent samples."
        )
    else:
        print(_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
