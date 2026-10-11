"""Counterexamples for evidence availability without statistical or execution claims."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

TOOL_PATH = Path(__file__).resolve().parents[2] / "tools/analysis/approval_overhead.py"
SOURCE_COMMIT = "a" * 40


@pytest.fixture
def availability_module() -> Any:
    spec = importlib.util.spec_from_file_location("confidence_availability", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _event(task_id: str, sequence: int, kind: str, state: str, **payload: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "sequence": sequence,
        "event_type": kind,
        "from_state": "IMPLEMENTING",
        "to_state": state,
        "actor": "synthetic-private-actor-marker",
        "occurred_at": "2026-10-11T00:00:00Z",
        "payload": payload,
    }


def _context(task_id: str) -> dict[str, Any]:
    value = {
        "schema_version": "1.0",
        "task_id": task_id,
        "review_stage": "implementation",
        "base_commit": "b" * 40,
        "subject_commit": "c" * 40,
        "spec_sha256": "d" * 64,
        "policy_sha256": "e" * 64,
        "classification_input_sha256": "f" * 64,
        "evidence_sha256": "b" * 64,
        "content": {"goal": "synthetic-private-context-marker"},
    }
    value["context_sha256"] = hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return value


def _review(
    task_id: str, context: dict[str, Any], identifier: str, revision: int, outcome: str
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "review_id": identifier,
        "revision": revision,
        "review_stage": "implementation",
        "context_sha256": context["context_sha256"],
        "recorded_at": "2026-10-11T00:00:00Z",
        "outcome": outcome,
        "reviewer": "synthetic-claimed-model-marker",
        "findings": [{"finding_id": "F-001", "summary": "synthetic-private-finding-marker"}],
    }


def _documents() -> dict[str, Any]:
    task_id = "TASK-0001"
    prefix = f".ai/tasks/{task_id}/"
    context = _context(task_id)
    binding = {
        "review_id": "REV-0001",
        "revision": 1,
        "review_stage": "implementation",
        "context_sha256": context["context_sha256"],
    }
    documents: dict[str, Any] = {
        prefix + "task.yaml": {
            "schema_version": "1.0",
            "task_id": task_id,
            "current_state": "MERGED",
            "base_commit": "b" * 40,
            "subject_commit": "c" * 40,
            "goal": "synthetic-private-task-marker",
        },
        prefix + "classification.json": {
            "schema_version": "1.0",
            "task_id": task_id,
            "effective_route": "BLOCK",
            "effective_verification_level": "V1",
        },
        prefix + "events.jsonl": [
            _event(task_id, 1, "classification_recorded", "BLOCKED", effective_route="BLOCK"),
            _event(task_id, 2, "verification_started", "VERIFYING"),
            _event(task_id, 3, "verification_failed", "FAILED", conclusion="failed"),
            _event(task_id, 4, "verification_restarted", "VERIFYING"),
            _event(task_id, 5, "verification_passed", "VERIFIED", conclusion="passed"),
            _event(task_id, 6, "review_recorded", "VERIFIED", **binding),
            _event(
                task_id,
                7,
                "review_finding_resolved",
                "VERIFIED",
                review_id="REV-0001",
                revision=2,
                finding_id="F-001",
            ),
            _event(
                task_id, 8, "review_recorded", "VERIFIED", **dict(binding, review_id="REV-0002")
            ),
        ],
        prefix + f"review-contexts/{context['context_sha256']}.json": context,
        prefix + "reviews/REV-0001-r0001.json": _review(
            task_id, context, "REV-0001", 1, "REQUEST_CHANGES"
        ),
        prefix + "reviews/REV-0001-r0002.json": _review(
            task_id, context, "REV-0001", 2, "REQUEST_CHANGES"
        ),
        prefix + "reviews/REV-0002-r0001.json": _review(task_id, context, "REV-0002", 1, "APPROVE"),
        prefix + "evidence.json": {
            "schema_version": "1.0",
            "task_id": task_id,
            "conclusion": "failed",
            "subject_commit": "c" * 40,
            "checks": [
                {
                    "check_id": status,
                    "category": "unit_tests",
                    "status": status,
                    "required": True,
                    "exit_code": 7 if status == "failed" else None,
                    "timed_out": status == "cancelled",
                    "duration_ms": 17,
                    "command_summary": "synthetic-private-command-marker",
                }
                for status in ("failed", "partial", "skipped", "cancelled")
            ],
        },
        prefix + "logs/private-run.txt": b"synthetic-private-log-marker",
        prefix + "approvals.json": b"synthetic-private-approval-marker",
    }
    for identifier, state in (("TASK-0002", "VERIFYING"), ("TASK-0003", "IMPLEMENTING")):
        other = f".ai/tasks/{identifier}/"
        documents[other + "task.yaml"] = {"task_id": identifier, "current_state": state}
        documents[other + "events.jsonl"] = [
            _event(
                identifier,
                1,
                "verification_started" if state == "VERIFYING" else "implementation_started",
                state,
            )
        ]
    return documents


def _git_wire(
    module: Any, monkeypatch: pytest.MonkeyPatch, documents: dict[str, Any]
) -> list[tuple[str, ...]]:
    blobs: dict[str, tuple[str, bytes]] = {}
    for path, value in documents.items():
        if isinstance(value, bytes):
            contents = value
        elif path.endswith(".jsonl"):
            contents = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in value).encode()
        else:
            contents = json.dumps(value, ensure_ascii=False).encode()
        oid = hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\0" + contents).hexdigest()
        blobs[path] = oid, contents
    allowed = {
        oid: contents
        for path, (oid, contents) in blobs.items()
        if module.SNAPSHOT_PATH.fullmatch(path)
    }
    calls: list[tuple[str, ...]] = []

    def git(_repository: Path, *arguments: str, data: bytes | None = None) -> bytes:
        calls.append(arguments)
        if arguments == ("rev-parse", "--verify", "HEAD"):
            return (SOURCE_COMMIT + "\n").encode()
        if arguments == ("ls-tree", "-r", "-z", SOURCE_COMMIT, "--", ".ai/tasks"):
            return b"".join(
                f"100644 blob {oid}\t{path}\0".encode() for path, (oid, _) in blobs.items()
            )
        assert arguments == ("cat-file", "--batch") and data is not None
        return b"".join(
            f"{oid} blob {len(allowed[oid])}\n".encode() + allowed[oid] + b"\n"
            for oid in data.decode().splitlines()
        )

    monkeypatch.setattr(module, "_snapshot_git", git)
    return calls


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(child) for child in value))
    return set()


def test_availability_reuses_one_fixed_snapshot_without_estimation_or_permission(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    calls = _git_wire(availability_module, monkeypatch, documents)
    snapshot = availability_module.build_snapshot(tmp_path)
    calls.clear()
    native_snapshot = availability_module.build_snapshot
    snapshots: list[dict[str, Any]] = []
    original_snapshots: list[str] = []

    def observed_snapshot(repository: Path) -> dict[str, Any]:
        report = native_snapshot(repository)
        snapshots.append(report)
        original_snapshots.append(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return report

    monkeypatch.setattr(availability_module, "build_snapshot", observed_snapshot)
    report = availability_module.build_availability(tmp_path)

    assert len(snapshots) == 1
    assert report["schema_version"] == "1.0"
    assert report["measurement"] == "confidence_evidence_availability"
    assert report["method_status"] == "design_pending"
    assert report["probability_status"] == "unestimated"
    assert report["execution_allowed"] is False
    for field in ("source_commit", "executed_tool_sha256", "sources"):
        assert report[field] == snapshot[field]
    assert calls == [
        ("rev-parse", "--verify", "HEAD"),
        ("ls-tree", "-r", "-z", SOURCE_COMMIT, "--", ".ai/tasks"),
        ("cat-file", "--batch"),
    ]
    assert [task["observations"] for task in report["tasks"]] == snapshot["tasks"]
    assert json.dumps(snapshots[0], ensure_ascii=False, sort_keys=True) == original_snapshots[0]
    assert report["unknown"] == snapshot["unknown"]
    assert report["unknown"]["defect_escape_rate"] == "unknown"
    assert set(report["unknown"].values()) == {"unknown"}
    forbidden = {
        "independent_samples",
        "independent_sample_count",
        "eligible",
        "eligible_tasks",
        "sample_count",
        "sample_size",
        "estimable",
        "score",
        "success_probability",
        "approval_probability",
        "review_policy_probability",
        "success_rate",
        "first_pass_rate",
        "repair_success_rate",
        "detection_rate",
        "false_positive_rate",
        "actual_denominator",
        "denominator",
        "n",
        "rate",
    }
    assert not _all_keys(report) & forbidden
    measured_report = {key: value for key, value in report.items() if key != "unknown"}
    assert not {key for key in _all_keys(measured_report) if key.endswith("_rate")}
    serialized = json.dumps(report)
    for marker in ("synthetic-private", "synthetic-claimed-model", "/logs/", "approvals.json"):
        assert marker not in serialized


def test_target_definitions_are_static_candidates_without_actual_denominators(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    _git_wire(availability_module, monkeypatch, documents)
    report = availability_module.build_availability(tmp_path)
    assert set(report["targets"]) == {
        "author_first_acceptance",
        "author_after_repair_acceptance",
        "review_detection",
        "review_false_positive",
    }
    fact_ids = set(report["tasks"][0]["facts"])
    for target in report["targets"].values():
        assert set(target) == {"denominator_definition", "required_facts"}
        assert (
            isinstance(target["denominator_definition"], str) and target["denominator_definition"]
        )
        assert isinstance(target["required_facts"], list) and target["required_facts"]
        assert set(target["required_facts"]) <= fact_ids
    single_task = {path: value for path, value in documents.items() if "/TASK-0001/" in path}
    _git_wire(availability_module, monkeypatch, single_task)
    smaller = availability_module.build_availability(tmp_path)
    assert smaller["targets"] == report["targets"]
    assert smaller["method_status"] == report["method_status"] == "design_pending"
    assert smaller["probability_status"] == report["probability_status"] == "unestimated"


def test_dynamic_facts_count_task_statuses_not_reviewers_findings_or_retries(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _git_wire(availability_module, monkeypatch, _documents())
    report = availability_module.build_availability(tmp_path)
    assert report["coverage"]["task_records"] == 3
    first, open_attempt, no_attempt = report["tasks"]
    assert [task["task_id"] for task in report["tasks"]] == ["TASK-0001", "TASK-0002", "TASK-0003"]
    assert [task["dependence_group"] for task in report["tasks"]] == [
        "TASK-0001",
        "TASK-0002",
        "TASK-0003",
    ]
    projected = {
        "candidate_version_bindings",
        "verification_evidence",
        "recorded_verification_results",
        "review_results",
        "review_context_bindings",
        "review_event_references",
    }
    for fact_id in projected:
        assert first["facts"][fact_id]["availability"] == "projected"
    for task in (open_attempt, no_attempt):
        for fact_id in ("verification_evidence", "review_results", "review_context_bindings"):
            assert task["facts"][fact_id]["availability"] == "source_missing"
        for fact_id in (
            "candidate_version_bindings",
            "recorded_verification_results",
            "review_event_references",
        ):
            assert task["facts"][fact_id]["availability"] == "linkage_unknown"
    for fact_id, counts in report["coverage"]["by_fact"].items():
        assert set(counts) == {"projected", "source_missing", "not_projected", "linkage_unknown"}
        assert sum(counts.values()) == 3
        if fact_id in projected:
            assert counts["projected"] == 1
    assert first["observations"]["task"]["current_state"] == "MERGED"
    assert first["observations"]["events"][0]["effective_route"] == "BLOCK"
    assert [
        attempt["original_result"] for attempt in first["observations"]["verification_attempts"]
    ] == ["failed", "passed"]
    assert [review["outcome"] for review in first["observations"]["reviews"]] == [
        "REQUEST_CHANGES",
        "REQUEST_CHANGES",
        "APPROVE",
    ]
    assert first["observations"]["reviews"][1]["event_links"] == [
        {"sequence": 7, "event_type": "review_finding_resolved", "binding": "revision_reference"}
    ]
    assert open_attempt["observations"]["verification_attempts"][0]["original_result"] == "unknown"
    assert no_attempt["observations"]["verification_attempts"] == []


def test_unprojected_facts_do_not_claim_source_absence_or_invent_identity_truth_or_budget(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _git_wire(availability_module, monkeypatch, _documents())
    report = availability_module.build_availability(tmp_path)
    unprojected = {
        "actual_model_identity",
        "task_conditions",
        "acceptance_protocol",
        "dependency_independence",
        "repair_strategy_and_budget",
        "independent_positive_truth",
        "independent_negative_truth_and_opportunities",
        "defect_report_matching",
        "review_information_and_budget",
    }
    for task in report["tasks"]:
        for fact_id in unprojected:
            assert task["facts"][fact_id] == {"availability": "not_projected", "source_refs": []}
        for fact_id in (
            "first_candidate_lineage",
            "repair_candidate_lineage",
            "evidence_attempt_linkage",
        ):
            assert task["facts"][fact_id]["availability"] == "linkage_unknown"
        for field in (
            "history_completeness",
            "historical_first_result",
            "evidence_attempt_linkage",
        ):
            assert task["observations"][field] == "unknown"
    for fact_id in unprojected:
        assert report["coverage"]["by_fact"][fact_id] == {
            "projected": 0,
            "source_missing": 0,
            "not_projected": 3,
            "linkage_unknown": 0,
        }


def test_checks_keep_partial_skipped_cancelled_timeout_and_original_failure(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _git_wire(availability_module, monkeypatch, _documents())
    first = availability_module.build_availability(tmp_path)["tasks"][0]
    evidence = first["observations"]["evidence"]
    assert first["facts"]["verification_evidence"]["availability"] == "projected"
    assert evidence["conclusion"] == "failed"
    assert [check["status"] for check in evidence["checks"]] == [
        "failed",
        "partial",
        "skipped",
        "cancelled",
    ]
    assert evidence["checks"][0]["exit_code"] == 7
    assert evidence["checks"][-1]["timed_out"] is True
    assert all(
        check["required"] is True and check["duration_ms"] == 17 for check in evidence["checks"]
    )


@pytest.mark.parametrize("missing", ["base_commit", "subject_commit"])
def test_one_missing_candidate_version_binding_cannot_be_filled_from_merged_state(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing: str
) -> None:
    documents = _documents()
    del documents[".ai/tasks/TASK-0001/task.yaml"][missing]
    _git_wire(availability_module, monkeypatch, documents)

    first = availability_module.build_availability(tmp_path)["tasks"][0]
    assert first["observations"]["task"]["current_state"] == "MERGED"
    assert first["observations"]["task"][missing] == "unknown"
    assert first["facts"]["candidate_version_bindings"] == {
        "availability": "linkage_unknown",
        "source_refs": [".ai/tasks/TASK-0001/task.yaml"],
    }


def test_orphan_result_is_projected_without_claiming_a_complete_attempt_lineage(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    documents[".ai/tasks/TASK-0002/events.jsonl"] = [
        _event("TASK-0002", 1, "verification_failed", "FAILED", conclusion="failed")
    ]
    _git_wire(availability_module, monkeypatch, documents)

    second = availability_module.build_availability(tmp_path)["tasks"][1]
    assert second["facts"]["recorded_verification_results"]["availability"] == "projected"
    assert second["observations"]["verification_attempts"][0]["start_sequence"] == "unknown"
    assert second["observations"]["verification_attempts"][0]["original_result"] == "failed"
    assert second["facts"]["first_candidate_lineage"]["availability"] == "linkage_unknown"
    assert second["facts"]["repair_candidate_lineage"]["availability"] == "linkage_unknown"


def test_missing_recorded_conclusion_is_not_inferred_from_event_name_or_later_pass(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    del documents[".ai/tasks/TASK-0001/events.jsonl"][2]["payload"]["conclusion"]
    _git_wire(availability_module, monkeypatch, documents)

    first = availability_module.build_availability(tmp_path)["tasks"][0]
    assert first["facts"]["recorded_verification_results"]["availability"] == "linkage_unknown"
    assert [
        attempt["original_result"] for attempt in first["observations"]["verification_attempts"]
    ] == ["unknown", "passed"]
    assert first["observations"]["events"][2]["event_type"] == "verification_failed"
    assert first["observations"]["events"][2]["to_state"] == "FAILED"


def test_existing_review_without_event_reference_does_not_link_by_shared_context_or_time(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    documents[".ai/tasks/TASK-0001/events.jsonl"] = [
        event for event in documents[".ai/tasks/TASK-0001/events.jsonl"] if event["sequence"] != 6
    ]
    _git_wire(availability_module, monkeypatch, documents)

    first = availability_module.build_availability(tmp_path)["tasks"][0]
    assert first["facts"]["review_results"]["availability"] == "projected"
    assert first["facts"]["review_context_bindings"]["availability"] == "projected"
    assert first["facts"]["review_event_references"]["availability"] == "linkage_unknown"
    assert first["observations"]["reviews"][0]["event_links"] == []
    assert first["observations"]["reviews"][1]["event_links"][0]["binding"] == "revision_reference"


def test_fact_source_refs_stay_within_fixed_allowlist_and_missing_files_are_not_references(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _git_wire(availability_module, monkeypatch, _documents())
    report = availability_module.build_availability(tmp_path)
    sources = {source["ref"] for source in report["sources"]}
    for task in report["tasks"]:
        prefix = f".ai/tasks/{task['task_id']}/"
        for fact in task["facts"].values():
            assert isinstance(fact["source_refs"], list)
            assert set(fact["source_refs"]) <= sources
            assert all(ref.startswith(prefix) for ref in fact["source_refs"])
        if task["task_id"] != "TASK-0001":
            assert task["facts"]["verification_evidence"]["source_refs"] == []
            assert task["facts"]["review_results"]["source_refs"] == []
    first = report["tasks"][0]
    assert first["facts"]["candidate_version_bindings"]["source_refs"] == [
        ".ai/tasks/TASK-0001/task.yaml"
    ]
    assert first["facts"]["recorded_verification_results"]["source_refs"] == [
        ".ai/tasks/TASK-0001/events.jsonl"
    ]


@pytest.mark.parametrize("missing", [False, True])
def test_context_conflicts_and_partial_context_absence_stay_distinct(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing: bool
) -> None:
    documents = _documents()
    prefix = ".ai/tasks/TASK-0001/"
    review = documents[prefix + "reviews/REV-0002-r0001.json"]
    if missing:
        review["context_sha256"] = "a" * 64
    else:
        review["review_stage"] = "design"
    _git_wire(availability_module, monkeypatch, documents)
    task = availability_module.build_availability(tmp_path)["tasks"][0]
    assert task["facts"]["review_context_bindings"]["availability"] == (
        "source_missing" if missing else "linkage_unknown"
    )
    assert task["facts"]["review_event_references"]["availability"] == "linkage_unknown"
    assert task["observations"]["reviews"][-1]["context_linkage"] == (
        "unknown" if missing else "mismatched"
    )
    assert task["observations"]["reviews"][0]["context_linkage"] == "matched"


def test_extra_retry_review_revision_and_findings_do_not_increase_fact_task_counts(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    documents = _documents()
    _git_wire(availability_module, monkeypatch, documents)
    original = availability_module.build_availability(tmp_path)
    prefix = ".ai/tasks/TASK-0001/"
    documents[prefix + "events.jsonl"].extend(
        [
            _event("TASK-0001", 9, "verification_restarted", "VERIFYING"),
            _event("TASK-0001", 10, "verification_failed", "FAILED", conclusion="failed"),
            _event(
                "TASK-0001",
                11,
                "review_finding_resolved",
                "FAILED",
                review_id="REV-0001",
                revision=3,
                finding_id="F-002",
            ),
        ]
    )
    previous = documents[prefix + "reviews/REV-0001-r0002.json"]
    documents[prefix + "reviews/REV-0001-r0003.json"] = dict(
        previous,
        revision=3,
        reviewer="another-synthetic-claimed-model",
        findings=[
            {"finding_id": f"F-{number:03d}", "summary": "private-many-findings-marker"}
            for number in range(20)
        ],
    )
    _git_wire(availability_module, monkeypatch, documents)
    expanded = availability_module.build_availability(tmp_path)
    assert expanded["coverage"] == original["coverage"]
    assert expanded["targets"] == original["targets"]
    observations = expanded["tasks"][0]["observations"]
    assert len(observations["reviews"]) == 4
    assert [attempt["original_result"] for attempt in observations["verification_attempts"]] == [
        "failed",
        "passed",
        "failed",
    ]
    assert "private-many-findings-marker" not in json.dumps(expanded)


@pytest.mark.parametrize("format_name", ["text", "json"])
def test_availability_cli_formats_are_readable_and_keep_non_estimation_boundary(
    availability_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    format_name: str,
) -> None:
    _git_wire(availability_module, monkeypatch, _documents())
    assert availability_module.main([str(tmp_path), "--availability", "--format", format_name]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    if format_name == "json":
        report = json.loads(captured.out)
        assert report["measurement"] == "confidence_evidence_availability"
        assert report["method_status"] == "design_pending"
        assert report["probability_status"] == "unestimated"
        assert report["execution_allowed"] is False
    else:
        assert "availability" in captured.out.lower()
        assert "unestimated" in captured.out
        assert "design_pending" in captured.out
    assert "synthetic-private" not in captured.out


@pytest.mark.parametrize(
    "flags", [["--availability", "--snapshot"], ["--snapshot", "--availability"]]
)
def test_conflicting_cli_modes_are_rejected_before_reading_sources(
    availability_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    flags: list[str],
) -> None:
    def unexpected_read(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Conflicting flags must not read sources")

    monkeypatch.setattr(availability_module, "_snapshot_git", unexpected_read)
    with pytest.raises(SystemExit) as error:
        availability_module.main([str(tmp_path), *flags])
    assert error.value.code == 2
    assert not capsys.readouterr().out


def test_existing_default_and_snapshot_cli_dispatch_do_not_invoke_availability(
    availability_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []

    def default(_repository: Path) -> dict[str, str]:
        calls.append("default")
        return {"original_mode": "default"}

    def snapshot(_repository: Path) -> dict[str, str]:
        calls.append("snapshot")
        return {"measurement": "tracked_ledger_snapshot"}

    def availability(_repository: Path) -> None:
        raise AssertionError("Existing modes must retain their own dispatch")

    monkeypatch.setattr(availability_module, "build_report", default)
    monkeypatch.setattr(availability_module, "build_snapshot", snapshot)
    monkeypatch.setattr(availability_module, "build_availability", availability)
    assert availability_module.main([str(tmp_path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"original_mode": "default"}
    assert availability_module.main([str(tmp_path), "--snapshot", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"measurement": "tracked_ledger_snapshot"}
    assert calls == ["default", "snapshot"]


@pytest.mark.parametrize("issue", ["no_sources", "malformed", "git_read_failure"])
def test_unavailable_or_failed_source_reads_do_not_create_reports_or_echo_private_data(
    availability_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    issue: str,
) -> None:
    if issue == "git_read_failure":

        def failed_run(*_args: Any, **_kwargs: Any) -> None:
            raise OSError("C:/Users/synthetic-private-user/credential-secret-marker")

        monkeypatch.setattr(availability_module.subprocess, "run", failed_run)
    else:
        documents = (
            _documents()
            if issue == "malformed"
            else {".ai/tasks/TASK-0001/logs/private-run.txt": b"credential-secret-marker"}
        )
        if issue == "malformed":
            documents[".ai/tasks/TASK-0001/events.jsonl"] = (
                b'{"credential-secret-marker": invalid}\n'
            )
        _git_wire(availability_module, monkeypatch, documents)
    assert availability_module.main([str(tmp_path), "--availability", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "synthetic-private" not in captured.err
    assert "credential-secret-marker" not in captured.err
    assert "design_pending" not in captured.err


def test_real_git_availability_keeps_index_bytes_and_excludes_dirty_or_untracked_material(
    availability_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_OPTIONAL_LOCKS="0",
    )

    def git(*arguments: str) -> bytes:
        return subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            env=environment,
        ).stdout

    git("init")
    documents = _documents()
    for relative, value in documents.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes):
            path.write_bytes(value)
        elif relative.endswith(".jsonl"):
            path.write_text(
                "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in value),
                encoding="utf-8",
            )
        else:
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    git("add", ".")
    git(
        "-c",
        "user.name=Availability Fixture",
        "-c",
        "user.email=availability@example.invalid",
        "commit",
        "-m",
        "fixed availability fixture",
    )
    committed = git("rev-parse", "HEAD").decode().strip()
    (repository / ".ai/tasks/TASK-0001/task.yaml").write_text(
        "synthetic-dirty-task-marker", encoding="utf-8"
    )
    untracked = repository / ".ai/tasks/TASK-0002/evidence.json"
    untracked.write_text("synthetic-untracked-evidence-marker", encoding="utf-8")
    before = {
        str(path.relative_to(repository)): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    calls: list[tuple[str, ...]] = []
    native_git = availability_module._snapshot_git

    def observed_git(directory: Path, *arguments: str, data: bytes | None = None) -> bytes:
        calls.append(arguments)
        return native_git(directory, *arguments, data=data)

    monkeypatch.setattr(availability_module, "_snapshot_git", observed_git)
    report = availability_module.build_availability(repository)

    assert report["source_commit"] == committed
    assert sum(arguments[0] == "rev-parse" for arguments in calls) == 1
    assert any(arguments[0] == "ls-tree" and committed in arguments for arguments in calls)
    assert report["tasks"][0]["observations"]["task"]["current_state"] == "MERGED"
    assert report["tasks"][1]["facts"]["verification_evidence"] == {
        "availability": "source_missing",
        "source_refs": [],
    }
    assert {
        str(path.relative_to(repository)): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    } == before
    serialized = json.dumps(report)
    for marker in (
        "synthetic-dirty-task-marker",
        "synthetic-untracked-evidence-marker",
        "synthetic-private",
        "synthetic-claimed-model",
    ):
        assert marker not in serialized
