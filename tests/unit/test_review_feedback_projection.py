"""Feedback fields remain opt-in, bounded and tied to the exact review revision."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

TOOL_PATH = Path(__file__).resolve().parents[2] / "tools/analysis/approval_overhead.py"
PREFIX = ".ai/tasks/TASK-0001/"
REVIEW_PATH = PREFIX + "reviews/REV-0001-r0001.json"


@pytest.fixture
def projection_module() -> Any:
    spec = importlib.util.spec_from_file_location("feedback_projection", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _finding(identifier: str = "RF-001", status: str = "open") -> dict[str, Any]:
    finding: dict[str, Any] = {
        "finding_id": identifier,
        "severity": "high",
        "status": status,
        "title": "private-finding-title-marker",
        "evidence_refs": ["private-evidence-path-marker"],
        "location": {"path": "private-location-marker", "line": 1},
    }
    if status == "resolved":
        finding["resolution"] = {
            "resolved_at": "2026-10-11T07:55:30Z",
            "actor": "private-resolution-actor-marker",
            "reason": "private-resolution-reason-marker",
        }
    return finding


def _event(sequence: int, kind: str = "review_finding_resolved", **payload: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "sequence": sequence,
        "event_type": kind,
        "from_state": "BLOCKED",
        "to_state": "BLOCKED",
        "actor": "private-event-actor-marker",
        "occurred_at": "2026-10-11T07:55:30Z",
        "payload": payload,
    }


def _documents() -> dict[str, Any]:
    return {
        PREFIX + "task.yaml": {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "current_state": "BLOCKED",
            "goal": "private-task-goal-marker",
        },
        PREFIX + "events.jsonl": [
            _event(1, "verification_started"),
            _event(2, "verification_failed", conclusion="failed"),
        ],
        REVIEW_PATH: {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "review_id": "REV-0001",
            "revision": 1,
            "review_stage": "design",
            "outcome": "REQUEST_CHANGES",
            "context_sha256": "d" * 64,
            "recorded_at": "2026-10-11T07:46:09.489Z",
            "reviewer": "private-reviewer-marker",
            "findings": [_finding()],
        },
        PREFIX + "logs/private-output.txt": b"private-log-marker",
    }


def _git_inputs(
    module: Any, monkeypatch: pytest.MonkeyPatch, documents: dict[str, Any]
) -> list[tuple[str, ...]]:
    blobs = {}
    for path, value in documents.items():
        if isinstance(value, bytes):
            contents = value
        elif path.endswith(".jsonl"):
            contents = "".join(json.dumps(row) + "\n" for row in value).encode()
        else:
            contents = json.dumps(value).encode()
        oid = hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\0" + contents).hexdigest()
        blobs[path] = (oid, contents)
    calls: list[tuple[str, ...]] = []

    def git(_repository: Path, *arguments: str, data: bytes | None = None) -> bytes:
        calls.append(arguments)
        if arguments == ("rev-parse", "--verify", "HEAD"):
            return b"c" * 40 + b"\n"
        if arguments[0] == "ls-tree":
            return b"".join(
                f"100644 blob {oid}\t{path}\0".encode() for path, (oid, _) in blobs.items()
            )
        assert arguments == ("cat-file", "--batch")
        assert data is not None
        allowed = {oid: contents for path, (oid, contents) in blobs.items() if "/logs/" not in path}
        return b"".join(
            f"{oid} blob {len(allowed[oid])}\n".encode() + allowed[oid] + b"\n"
            for oid in data.decode().splitlines()
        )

    monkeypatch.setattr(module, "_snapshot_git", git)
    return calls


def test_projection_keeps_original_outcome_failures_and_default_shape(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    documents[PREFIX + "reviews/REV-0001-r0002.json"] = dict(
        documents[REVIEW_PATH], revision=2, findings=[_finding(status="resolved")]
    )
    documents[PREFIX + "events.jsonl"].append(
        _event(3, review_id="REV-0001", revision=2, finding_id="RF-001")
    )
    before = copy.deepcopy(documents)
    calls = _git_inputs(projection_module, monkeypatch, documents)
    default = projection_module.build_snapshot(tmp_path)
    original_calls = calls.copy()
    calls.clear()
    report = projection_module.build_snapshot(tmp_path, include_feedback=True)

    assert calls == original_calls
    assert documents == before
    assert report["feedback_projection"] is True
    task = report["tasks"][0]
    first, second = task["reviews"]
    assert [review["outcome"] for review in task["reviews"]] == [
        "REQUEST_CHANGES",
        "REQUEST_CHANGES",
    ]
    assert task["task"]["current_state"] == "BLOCKED"
    assert task["verification_attempts"][0]["original_result"] == "failed"
    assert first["findings"] == [
        {
            "finding_id": "RF-001",
            "severity": "high",
            "status": "open",
            "resolved_at": "not_applicable",
        }
    ]
    assert second["findings"] == [
        {
            "finding_id": "RF-001",
            "severity": "high",
            "status": "resolved",
            "resolved_at": "2026-10-11T07:55:30Z",
        }
    ]
    assert second["event_links"] == [
        {
            "sequence": 3,
            "event_type": "review_finding_resolved",
            "binding": "finding_revision_reference",
            "finding_id": "RF-001",
        }
    ]
    assert report["coverage"] == default["coverage"]
    assert report["sources"] == default["sources"]
    assert "private-" not in json.dumps(report)
    del report["feedback_projection"]
    for review in task["reviews"]:
        del review["findings"]
    del task["events"][-1]["finding_id"]
    del second["event_links"][0]["finding_id"]
    second["event_links"][0]["binding"] = "revision_reference"
    assert report == default


def test_findings_strict_validation_is_not_applied_to_default_snapshot_or_availability(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    documents[REVIEW_PATH]["findings"] = [{"title": "private-only-invalid-finding"}]
    documents[PREFIX + "events.jsonl"].append(
        _event(3, review_id="REV-0001", revision=1, finding_id="F-001")
    )
    _git_inputs(projection_module, monkeypatch, documents)
    implicit = projection_module.build_snapshot(tmp_path)
    explicit = projection_module.build_snapshot(tmp_path, include_feedback=False)
    availability = projection_module.build_availability(tmp_path)

    assert implicit == explicit
    assert "feedback_projection" not in implicit
    assert "finding_id" not in json.dumps(implicit)
    assert "private-" not in json.dumps(availability)
    assert implicit["tasks"][0]["reviews"][0]["event_links"][0]["binding"] == "revision_reference"


@pytest.mark.parametrize("stage,version", [("design", "1.0"), ("implementation", "2.0")])
def test_feedback_keeps_context_hash_binding_and_stage_mismatch(
    projection_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stage: str,
    version: str,
) -> None:
    documents = _documents()
    context = {
        "schema_version": version,
        "task_id": "TASK-0001",
        "review_stage": stage,
        "base_commit": "a" * 40,
        "spec_sha256": "b" * 64,
        "policy_sha256": "c" * 64,
        "classification_input_sha256": "d" * 64,
        "content": {"goal": "private-context-goal-marker"},
    }
    if stage == "implementation":
        context.update(subject_commit="e" * 40, verification_snapshot_sha256="f" * 64)
    digest = hashlib.sha256(
        json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    context["context_sha256"] = digest
    documents[PREFIX + f"review-contexts/{digest}.json"] = context
    documents[REVIEW_PATH]["context_sha256"] = digest
    _git_inputs(projection_module, monkeypatch, documents)

    default = projection_module.build_snapshot(tmp_path)
    feedback = projection_module.build_snapshot(tmp_path, include_feedback=True)
    original_review = default["tasks"][0]["reviews"][0]
    projected_review = feedback["tasks"][0]["reviews"][0]
    assert projected_review["context"] == original_review["context"]
    assert projected_review["context"]["context_sha256"] == digest
    assert projected_review["context_linkage"] == ("matched" if stage == "design" else "mismatched")
    assert "private-" not in json.dumps(feedback)


@pytest.mark.parametrize("severity", ["critical", "high", "medium", "low"])
def test_every_allowed_severity_and_empty_findings(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, severity: str
) -> None:
    documents = _documents()
    documents[REVIEW_PATH]["findings"][0]["severity"] = severity
    documents[PREFIX + "reviews/REV-0002-r0001.json"] = dict(
        documents[REVIEW_PATH], review_id="REV-0002", findings=[]
    )
    _git_inputs(projection_module, monkeypatch, documents)
    reviews = projection_module.build_snapshot(tmp_path, include_feedback=True)["tasks"][0][
        "reviews"
    ]
    assert reviews[0]["findings"][0]["severity"] == severity
    assert reviews[1]["findings"] == []


@pytest.mark.parametrize(
    "findings",
    [
        None,
        {},
        "private-malformed-findings-marker",
        [None],
        ["private-malformed-entry-marker"],
        [[]],
        [{}],
        [{"finding_id": "RF-001", "status": "open"}],
        [{"finding_id": "RF-001", "severity": "high"}],
        [dict(_finding(), finding_id=True)],
        [dict(_finding(), finding_id="F-001")],
        [dict(_finding(), finding_id="RF-01")],
        [dict(_finding(), finding_id="RF-001\nprivate-id-marker")],
        [dict(_finding(), severity="HIGH")],
        [dict(_finding(), severity="private-severity-marker")],
        [dict(_finding(), status="closed")],
        [dict(_finding(), status=None)],
        [_finding(), _finding()],
        [dict(_finding(), resolution=None)],
        [dict(_finding(), resolution={"resolved_at": "2026-10-11T00:00:00Z"})],
        [dict(_finding(status="resolved"), resolution=None)],
        [dict(_finding(status="resolved"), resolution={})],
    ],
)
def test_invalid_findings_are_rejected_without_echoing_private_values(
    projection_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    findings: Any,
) -> None:
    documents = _documents()
    documents[REVIEW_PATH]["findings"] = findings
    _git_inputs(projection_module, monkeypatch, documents)

    with pytest.raises(projection_module.LedgerDataError) as error:
        projection_module.build_snapshot(tmp_path, include_feedback=True)
    assert "private-" not in str(error.value)


def test_missing_findings_or_resolution_is_rejected(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    del documents[REVIEW_PATH]["findings"]
    _git_inputs(projection_module, monkeypatch, documents)
    with pytest.raises(projection_module.LedgerDataError):
        projection_module.build_snapshot(tmp_path, include_feedback=True)

    documents[REVIEW_PATH]["findings"] = [_finding(status="resolved")]
    del documents[REVIEW_PATH]["findings"][0]["resolution"]
    _git_inputs(projection_module, monkeypatch, documents)
    with pytest.raises(projection_module.LedgerDataError):
        projection_module.build_snapshot(tmp_path, include_feedback=True)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-10-11T07:55:30Z",
        "2026-10-12T01:55:30+08:00",
        "2024-02-29T00:00:00.123456789-05:30",
    ],
)
def test_valid_timezone_datetime_is_preserved_exactly(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, timestamp: str
) -> None:
    documents = _documents()
    documents[REVIEW_PATH]["findings"] = [_finding(status="resolved")]
    documents[REVIEW_PATH]["findings"][0]["resolution"]["resolved_at"] = timestamp
    _git_inputs(projection_module, monkeypatch, documents)
    report = projection_module.build_snapshot(tmp_path, include_feedback=True)
    assert report["tasks"][0]["reviews"][0]["findings"][0]["resolved_at"] == timestamp


@pytest.mark.parametrize(
    "timestamp",
    [
        None,
        True,
        {},
        "private-timestamp-marker",
        "2026-10-11",
        "2026-10-11T07:55:30",
        "2026-10-11 07:55:30Z",
        "2023-02-29T00:00:00Z",
        "2026-13-11T07:55:30Z",
        "2026-10-32T07:55:30Z",
        "2026-10-11T25:00:00Z",
        "2026-10-11T07:99:30Z",
        "2026-10-11T07:55:30+24:00",
        "2026-10-11T07:55:30+00:99",
        "2026-10-11T07:55:30Z\nprivate-timestamp-marker",
    ],
)
def test_invalid_resolution_time_is_rejected_without_echoing_content(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, timestamp: Any
) -> None:
    documents = _documents()
    documents[REVIEW_PATH]["findings"] = [_finding(status="resolved")]
    documents[REVIEW_PATH]["findings"][0]["resolution"]["resolved_at"] = timestamp
    _git_inputs(projection_module, monkeypatch, documents)

    with pytest.raises(projection_module.LedgerDataError) as error:
        projection_module.build_snapshot(tmp_path, include_feedback=True)
    assert "resolved_at" in str(error.value)
    assert "private-" not in str(error.value)


def test_resolution_links_require_same_finding_and_revision_and_keep_orphan_events(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    documents[REVIEW_PATH]["findings"].append(_finding("RF-002", "resolved"))
    documents[PREFIX + "reviews/REV-0002-r0001.json"] = dict(
        documents[REVIEW_PATH], review_id="REV-0002", findings=[_finding("RF-001", "resolved")]
    )
    events = documents[PREFIX + "events.jsonl"]
    for sequence, identifier in enumerate(["RF-001", "RF-002", "RF-002", "RF-999"], 3):
        events.append(_event(sequence, review_id="REV-0001", revision=1, finding_id=identifier))
    events.append(_event(7, review_id="REV-0001", revision=99, finding_id="RF-002"))
    events.append(
        _event(
            8,
            "review_recorded",
            review_id="REV-0001",
            revision=1,
            review_stage="design",
            context_sha256="d" * 64,
            finding_id="private-ignored-recorded-marker",
        )
    )
    _git_inputs(projection_module, monkeypatch, documents)

    task = projection_module.build_snapshot(tmp_path, include_feedback=True)["tasks"][0]
    links = task["reviews"][0]["event_links"]
    assert [link["binding"] for link in links] == [
        "mismatched",
        "finding_revision_reference",
        "finding_revision_reference",
        "mismatched",
        "matched",
    ]
    assert [link.get("finding_id") for link in links] == [
        "RF-001",
        "RF-002",
        "RF-002",
        "RF-999",
        None,
    ]
    assert task["reviews"][1]["event_links"] == []
    assert task["events"][-2]["revision"] == 99
    assert task["events"][-2]["finding_id"] == "RF-002"
    assert "finding_id" not in task["events"][-1]
    assert "private-" not in json.dumps(task)


@pytest.mark.parametrize("identifier", [None, True, "F-001", "RF-01", "private-event-id-marker"])
def test_resolution_event_finding_id_is_required_and_bounded(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, identifier: Any
) -> None:
    documents = _documents()
    documents[PREFIX + "events.jsonl"].append(
        _event(3, review_id="REV-0001", revision=1, finding_id=identifier)
    )
    _git_inputs(projection_module, monkeypatch, documents)
    with pytest.raises(projection_module.LedgerDataError) as error:
        projection_module.build_snapshot(tmp_path, include_feedback=True)
    assert "private-" not in str(error.value)


def test_same_finding_id_in_other_tasks_or_reviews_remains_a_separate_record(
    projection_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    documents[PREFIX + "reviews/REV-0002-r0001.json"] = dict(
        documents[REVIEW_PATH], review_id="REV-0002"
    )
    extra = copy.deepcopy(documents)
    for path, value in extra.items():
        if isinstance(value, dict):
            value["task_id"] = "TASK-0002"
        elif isinstance(value, list):
            for event in value:
                event["task_id"] = "TASK-0002"
        documents[path.replace("TASK-0001", "TASK-0002")] = value
    _git_inputs(projection_module, monkeypatch, documents)

    tasks = projection_module.build_snapshot(tmp_path, include_feedback=True)["tasks"]
    assert [task["task_id"] for task in tasks] == ["TASK-0001", "TASK-0002"]
    assert all(
        review["findings"][0]["finding_id"] == "RF-001"
        for task in tasks
        for review in task["reviews"]
    )
