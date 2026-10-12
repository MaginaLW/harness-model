"""Independent counterexamples for committed review feedback readback."""

from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "tools/analysis/review_feedback.py"
SOURCE_COMMIT = "c" * 40
PREFIX = ".ai/tasks/TASK-0001/"


@pytest.fixture
def feedback(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("review_feedback", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _finding(
    finding_id: str = "RF-0001", status: str = "open", severity: str = "high"
) -> dict[str, str]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "status": status,
        "resolved_at": "2026-10-12T00:00:00Z" if status == "resolved" else "not_applicable",
    }


def _review(
    revision: int = 1,
    *,
    review_id: str = "REV-0001",
    findings: list[dict[str, str]] | None = None,
    task_id: str = "TASK-0001",
    **updates: Any,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "source_ref": f".ai/tasks/{task_id}/reviews/{review_id}-r{revision:04d}.json",
        "review_id": review_id,
        "revision": revision,
        "review_stage": "implementation",
        "outcome": "REQUEST_CHANGES",
        "context_sha256": "d" * 64,
        "recorded_at": "2026-10-11T00:00:00Z",
        "context": {
            "source_ref": f".ai/tasks/{task_id}/review-contexts/{'d' * 64}.json",
            "schema_version": "1.0",
            "review_stage": "implementation",
            "subject_commit": "e" * 40,
            "base_commit": "a" * 40,
            "spec_sha256": "b" * 64,
            "context_sha256": "d" * 64,
            "evidence_sha256": "f" * 64,
            "verification_snapshot_sha256": "not_applicable",
        },
        "context_linkage": "matched",
        "event_links": [
            {"sequence": revision, "event_type": "review_recorded", "binding": "matched"}
        ],
        "findings": [_finding()] if findings is None else findings,
    }
    value.update(updates)
    return value


def _snapshot(*reviews: dict[str, Any]) -> dict[str, Any]:
    tasks = [
        {
            "task_id": "TASK-0001",
            "dependence_group": "TASK-0001",
            "task": {
                "schema_version": "1.0",
                "repository_id": "12345678-1234-1234-1234-123456789abc",
                "current_state": "MERGED",
                "frozen_spec_sha256": "f" * 64,
                "base_commit": "a" * 40,
                "subject_commit": "b" * 40,
            },
            "reviews": list(reviews) if reviews else [_review()],
            "events": [],
            "verification_attempts": [
                {
                    "stage": "verification",
                    "start_sequence": 1,
                    "result_sequence": 2,
                    "original_result": "failed",
                    "to_state": "FAILED",
                },
                {
                    "stage": "verification",
                    "start_sequence": 3,
                    "result_sequence": 4,
                    "original_result": "passed",
                    "to_state": "VERIFIED",
                },
            ],
            "evidence": {
                "conclusion": "passed",
                "subject_commit": "b" * 40,
                "checks": [{"check_id": "unit_tests", "status": "passed"}],
            },
            "history_completeness": "unknown",
            "evidence_attempt_linkage": "unknown",
            "historical_first_result": "unknown",
        }
    ]
    snapshot = {
        "schema_version": "1.0",
        "measurement": "tracked_ledger_snapshot",
        "feedback_projection": True,
        "source_commit": SOURCE_COMMIT,
        "executed_tool_sha256": "1" * 64,
        "sources": [],
        "tasks": tasks,
        "limitations": ["Synthetic native projection fixture; source statements not reverified."],
    }
    _refresh_sources(snapshot)
    return snapshot


def _refresh_sources(snapshot: dict[str, Any]) -> None:
    refs: set[str] = set()
    for task in snapshot["tasks"]:
        prefix = f".ai/tasks/{task['task_id']}/"
        refs.update(
            prefix + filename for filename in ("task.yaml", "events.jsonl", "evidence.json")
        )
        for review in task["reviews"]:
            refs.add(review["source_ref"])
            if review["context"] != "unknown":
                refs.add(review["context"]["source_ref"])
    snapshot["sources"] = [
        {"ref": ref, "git_blob": hashlib.sha1(ref.encode()).hexdigest()} for ref in sorted(refs)
    ]


def _history(report: dict[str, Any], finding_id: str = "RF-0001") -> dict[str, Any]:
    return next(
        history
        for history in report["tasks"][0]["finding_histories"]
        if history["finding_id"] == finding_id
    )


def _reference_input() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_category": "coding",
        "models": ["synthetic-a", "synthetic-b"],
        "sources": [
            {
                "source_id": "synthetic-repair",
                "family": "synthetic-repair",
                "category": "coding",
                "url": "https://example.org/leaderboard",
                "retrieved_at": "2026-10-12T01:00:00+08:00",
                "as_of": "2026-10-08",
                "revision": "synthetic-fixture-v1",
                "metric": "test_pass_percent",
                "direction": "higher",
                "protocol": "Synthetic single-attempt fixture; no real model claim.",
                "observations": [
                    {
                        "model_id": profile,
                        "label": profile,
                        "configuration": "synthetic fixed harness",
                        "score": score,
                    }
                    for profile, score in (("synthetic-a", 9), ("synthetic-b", 1))
                ],
            }
        ],
    }


def test_feedback_preserves_original_failures_without_claiming_truth(feedback: Any) -> None:
    snapshot = _snapshot(_review(), _review(2, findings=[_finding(status="resolved")]))
    report = feedback.build_feedback(snapshot)
    history = _history(report)

    assert report["measurement"] == "review_feedback_readback"
    assert report["schema_version"] == "1.0"
    assert report["source_commit"] == SOURCE_COMMIT
    assert report["sources"] == snapshot["sources"]
    assert report["snapshot_tool_sha256"] == snapshot["executed_tool_sha256"]
    assert report["executed_tool_sha256"] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert report["tasks"][0]["current_state"] == "MERGED"
    assert history["observed_first_revision"] == 1
    assert history["observed_latest_revision"] == 2
    assert [item["status"] for item in history["observations"]] == ["open", "resolved"]
    assert [item["outcome"] for item in history["observations"]] == [
        "REQUEST_CHANGES",
        "REQUEST_CHANGES",
    ]
    assert history["history_issues"] == []
    assert history["independent_truth"] == "not_projected"
    assert history["author_disposition"] == history["independent_recheck"] == "unknown"
    task = report["tasks"][0]
    assert task["verification_attempts"] == snapshot["tasks"][0]["verification_attempts"]
    assert [attempt["original_result"] for attempt in task["verification_attempts"]] == [
        "failed",
        "passed",
    ]
    assert task["evidence"] == snapshot["tasks"][0]["evidence"]
    for key in ("history_completeness", "evidence_attempt_linkage", "historical_first_result"):
        assert task[key] == "unknown"
    assert history["history_completeness"] == "unknown"
    assert report["coverage"] == {
        "task_records": 1,
        "review_records": 2,
        "finding_revision_records": 2,
        "finding_keys": 1,
    }


def test_feedback_is_readback_without_model_scoring_or_permission_effect(feedback: Any) -> None:
    report = feedback.build_feedback(_snapshot())
    assert report["probability_status"] == "unestimated"
    assert report["method_status"] == "design_pending"
    assert report["execution_allowed"] is False
    assert report["permission_effect"] == report["ledger_effect"] == "none"
    assert report["actual_model_identity"] == "unknown"
    assert report["model_score_update_status"] == "not_implemented"
    assert report["task_free_feedback_status"] == "not_projected"
    assert report["external_reference"] is None
    assert "success_probability" not in json.dumps(report)


def test_every_review_and_finding_observation_has_replayable_source(feedback: Any) -> None:
    snapshot = _snapshot(_review(), _review(2, findings=[_finding(status="resolved")]))
    report = feedback.build_feedback(snapshot)
    blobs = {source["ref"]: source["git_blob"] for source in snapshot["sources"]}
    for review, observation in zip(
        report["tasks"][0]["reviews"], _history(report)["observations"], strict=True
    ):
        expected = {
            "source_commit": SOURCE_COMMIT,
            "path": review["source_ref"],
            "git_blob": blobs[review["source_ref"]],
            "locator": f"review_id=REV-0001,revision={review['revision']}",
        }
        assert review["source"] == expected
        assert observation["source"] == {
            **expected,
            "locator": expected["locator"] + ",finding_id=RF-0001",
        }
        context_ref = review["context"]["source_ref"]
        assert review["context"]["source"] == {
            "source_commit": SOURCE_COMMIT,
            "path": context_ref,
            "git_blob": blobs[context_ref],
            "locator": f"context_sha256={review['context_sha256']}",
        }
        assert review["context"]["subject_commit"] == "e" * 40
        assert report["tasks"][0]["bindings"]["subject_commit"] == "b" * 40
        assert review["context_linkage"] == "matched"
        original_links = snapshot["tasks"][0]["reviews"][review["revision"] - 1]["event_links"]
        for link, original_link in zip(review["event_links"], original_links, strict=True):
            assert {key: value for key, value in link.items() if key != "source"} == original_link
            assert link["source"] == {
                "source_commit": SOURCE_COMMIT,
                "path": PREFIX + "events.jsonl",
                "git_blob": blobs[PREFIX + "events.jsonl"],
                "locator": f"task_id=TASK-0001,sequence={link['sequence']}",
            }


@pytest.mark.parametrize("projection", [None, False, "true", 1])
def test_non_feedback_snapshot_cannot_be_silently_accepted(feedback: Any, projection: Any) -> None:
    snapshot = _snapshot()
    if projection is None:
        del snapshot["feedback_projection"]
    else:
        snapshot["feedback_projection"] = projection
    with pytest.raises(ValueError) as error:
        feedback.build_feedback(snapshot)
    assert type(error.value).__name__ == "LedgerDataError"


def test_observed_first_revision_does_not_claim_historical_first(feedback: Any) -> None:
    report = feedback.build_feedback(_snapshot(_review(3)))
    history = _history(report)
    assert history["observed_first_revision"] == history["observed_latest_revision"] == 3
    assert history["history_issues"] == ["REVISION_GAP"]
    assert history["history_completeness"] == "unknown"
    assert report["tasks"][0]["historical_first_result"] == "unknown"


def test_large_native_revision_does_not_allocate_all_unobserved_revisions(feedback: Any) -> None:
    report = feedback.build_feedback(_snapshot(_review(), _review(10**9)))
    history = _history(report)
    assert history["history_issues"] == ["REVISION_GAP"]
    assert [observation["revision"] for observation in history["observations"]] == [1, 10**9]
    assert history["observed_latest_revision"] == 10**9


def test_projection_marker_without_findings_does_not_imply_empty_findings(feedback: Any) -> None:
    snapshot = _snapshot()
    del snapshot["tasks"][0]["reviews"][0]["findings"]
    with pytest.raises(ValueError) as error:
        feedback.build_feedback(snapshot)
    assert type(error.value).__name__ == "LedgerDataError"


@pytest.mark.parametrize(
    "updates,issue",
    [
        ({"revision": 3}, "REVISION_GAP"),
        (
            {"context_sha256": "a" * 64, "context": "unknown", "context_linkage": "unknown"},
            "CONTEXT_CHANGED",
        ),
        (
            {"review_stage": "design", "context": "unknown", "context_linkage": "unknown"},
            "STAGE_CHANGED",
        ),
        ({"findings": [_finding(severity="low")]}, "SEVERITY_CHANGED"),
    ],
)
def test_revision_drift_is_visible_without_discarding_originals(
    feedback: Any, updates: dict[str, Any], issue: str
) -> None:
    revision = updates.get("revision", 2)
    changes = {key: value for key, value in updates.items() if key != "revision"}
    report = feedback.build_feedback(_snapshot(_review(), _review(revision, **changes)))
    history = _history(report)
    assert issue in history["history_issues"]
    assert len(history["observations"]) == 2
    assert history["observations"][0]["severity"] == "high"
    assert history["observations"][0]["context_sha256"] == "d" * 64
    assert history["independent_recheck"] == "unknown"


def test_resolved_then_reopened_finding_keeps_all_three_observations(feedback: Any) -> None:
    report = feedback.build_feedback(
        _snapshot(_review(), _review(2, findings=[_finding(status="resolved")]), _review(3))
    )
    history = _history(report)
    assert "STATUS_REOPENED" in history["history_issues"]
    assert [observation["status"] for observation in history["observations"]] == [
        "open",
        "resolved",
        "open",
    ]


def test_empty_approve_revision_is_not_finding_resolution_or_independent_recheck(
    feedback: Any,
) -> None:
    report = feedback.build_feedback(
        _snapshot(_review(), _review(2, findings=[], outcome="APPROVE"))
    )
    history = _history(report)
    assert len(report["tasks"][0]["reviews"]) == 2
    assert len(history["observations"]) == 1
    assert history["observations"][0]["status"] == "open"
    assert history["observed_latest_revision"] == 1
    assert "FINDING_NOT_IN_EACH_REVISION" in history["history_issues"]
    assert history["author_disposition"] == history["independent_recheck"] == "unknown"
    assert report["coverage"]["finding_revision_records"] == 1


def test_identical_finding_ids_do_not_merge_across_review_or_task(feedback: Any) -> None:
    snapshot = _snapshot(_review(), _review(review_id="REV-0002"))
    another = copy.deepcopy(snapshot["tasks"][0])
    another["task_id"] = another["dependence_group"] = "TASK-0002"
    another["reviews"] = [_review(task_id="TASK-0002")]
    snapshot["tasks"].append(another)
    _refresh_sources(snapshot)
    report = feedback.build_feedback(snapshot)
    histories = [history for task in report["tasks"] for history in task["finding_histories"]]
    assert len(histories) == 3
    assert [(task["task_id"], len(task["finding_histories"])) for task in report["tasks"]] == [
        ("TASK-0001", 2),
        ("TASK-0002", 1),
    ]
    assert {history["review_id"] for history in report["tasks"][0]["finding_histories"]} == {
        "REV-0001",
        "REV-0002",
    }
    assert all(len(history["observations"]) == 1 for history in histories)
    assert report["coverage"]["finding_keys"] == 3


def test_findings_missing_from_an_intermediate_revision_remain_in_history(feedback: Any) -> None:
    snapshot = _snapshot(_review(), _review(2, findings=[]), _review(3))
    history = _history(feedback.build_feedback(snapshot))
    assert [item["revision"] for item in history["observations"]] == [1, 3]
    assert "FINDING_NOT_IN_EACH_REVISION" in history["history_issues"]
    assert "REVISION_GAP" not in history["history_issues"]


def test_empty_finding_revisions_still_expose_review_gaps_and_candidate_drift(
    feedback: Any,
) -> None:
    report = feedback.build_feedback(
        _snapshot(
            _review(2, findings=[], outcome="APPROVE"),
            _review(
                4,
                findings=[],
                outcome="APPROVE",
                context_sha256="a" * 64,
                review_stage="design",
                context="unknown",
                context_linkage="unknown",
            ),
        )
    )
    task = report["tasks"][0]
    assert task["finding_histories"] == []
    assert task["review_histories"] == [
        {
            "review_id": "REV-0001",
            "observed_revisions": [2, 4],
            "history_issues": ["REVISION_GAP", "CONTEXT_CHANGED", "STAGE_CHANGED"],
            "history_completeness": "unknown",
        }
    ]
    assert [review["outcome"] for review in task["reviews"]] == ["APPROVE", "APPROVE"]
    assert report["coverage"]["finding_revision_records"] == 0


def test_summary_and_output_are_independent_copies_of_all_input_records(feedback: Any) -> None:
    snapshot = _snapshot()
    before = copy.deepcopy(snapshot)
    report = feedback.build_feedback(snapshot)
    assert snapshot == before
    report["sources"][0]["git_blob"] = "0" * 40
    task = report["tasks"][0]
    task["reviews"][0]["context"]["subject_commit"] = "0" * 40
    task["reviews"][0]["findings"][0]["severity"] = "low"
    task["finding_histories"][0]["observations"][0]["source"]["git_blob"] = "0" * 40
    task["verification_attempts"][0]["original_result"] = "passed"
    task["evidence"]["checks"][0]["status"] = "failed"
    assert snapshot == before


def test_missing_optional_candidate_and_evidence_facts_stay_unknown(feedback: Any) -> None:
    snapshot = _snapshot()
    snapshot["tasks"][0]["task"] = {"current_state": "IMPLEMENTING"}
    snapshot["tasks"][0]["evidence"] = "unknown"
    snapshot["tasks"][0]["verification_attempts"] = []
    snapshot["tasks"][0]["reviews"][0]["context"] = "unknown"
    snapshot["tasks"][0]["reviews"][0]["context_linkage"] = "unknown"
    task = feedback.build_feedback(snapshot)["tasks"][0]
    assert task["bindings"] == dict.fromkeys(
        ("base_commit", "subject_commit", "frozen_spec_sha256", "repository_id"), "unknown"
    )
    assert task["evidence"] == task["reviews"][0]["context"] == "unknown"
    assert task["verification_attempts"] == []


@pytest.mark.parametrize("reviews", [[], [_review(findings=[])]])
def test_tasks_without_finding_records_are_not_fabricated_samples(
    feedback: Any, reviews: list[dict[str, Any]]
) -> None:
    snapshot = _snapshot()
    snapshot["tasks"][0]["reviews"] = reviews
    report = feedback.build_feedback(snapshot)
    assert report["tasks"][0]["finding_histories"] == []
    assert report["coverage"]["review_records"] == len(reviews)
    assert report["coverage"]["finding_revision_records"] == 0
    assert report["coverage"]["finding_keys"] == 0


def test_no_task_ledger_does_not_claim_task_free_feedback(feedback: Any) -> None:
    snapshot = _snapshot()
    snapshot["tasks"] = []
    snapshot["sources"] = []
    report = feedback.build_feedback(snapshot)
    assert report["tasks"] == []
    assert not any(report["coverage"].values())
    assert report["task_free_feedback_status"] == "not_projected"


def test_task_filter_does_not_conceal_the_snapshot_read_scope(feedback: Any) -> None:
    snapshot = _snapshot()
    another = copy.deepcopy(snapshot["tasks"][0])
    another["task_id"] = another["dependence_group"] = "TASK-12345"
    another["reviews"] = [_review(task_id="TASK-12345")]
    snapshot["tasks"].append(another)
    _refresh_sources(snapshot)
    report = feedback.build_feedback(snapshot, task_ids=["TASK-12345"])
    assert [task["task_id"] for task in report["tasks"]] == ["TASK-12345"]
    assert report["coverage"]["task_records"] == 1
    assert report["sources"] == snapshot["sources"]
    assert any(source["ref"].startswith(PREFIX) for source in report["sources"])


@pytest.mark.parametrize(
    "task_ids",
    [[], ["TASK-0001", "TASK-0001"], ["TASK-1"], ["REV-0001"], ["TASK-9999"], [[]], [None]],
)
def test_duplicate_invalid_and_unknown_task_filters_are_rejected(
    feedback: Any, task_ids: list[Any]
) -> None:
    with pytest.raises(ValueError) as error:
        feedback.build_feedback(_snapshot(), task_ids=task_ids)
    assert type(error.value).__name__ == "LedgerDataError"


def test_external_reference_does_not_change_local_findings_or_match_model_identity(
    feedback: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_network(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Feedback readback must not connect to a provider or service.")

    monkeypatch.setattr(socket, "socket", no_network)
    snapshot = _snapshot()
    document = _reference_input()
    before = copy.deepcopy(document)
    plain = feedback.build_feedback(snapshot)
    report = feedback.build_feedback(snapshot, reference_input=document)
    reference_module = importlib.import_module("benchmark_reference")
    expected = reference_module.build_reference(document)
    assert report["external_reference"] == expected
    assert document == before
    assert report["tasks"] == plain["tasks"]
    assert report["coverage"] == plain["coverage"]
    assert report["actual_model_identity"] == "unknown"
    assert report["model_score_update_status"] == "not_implemented"
    assert report["probability_status"] == "unestimated"
    report["external_reference"]["sources"][0]["observations"][0]["score"] = -100
    assert document == before


def test_invalid_external_reference_cannot_be_attached_as_partial_success(feedback: Any) -> None:
    with pytest.raises(ValueError):
        feedback.build_feedback(_snapshot(), reference_input={"private-marker": "secret"})


def _git(repository: Path, *arguments: str) -> bytes:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        env=environment,
        check=True,
        capture_output=True,
    )
    return result.stdout


def _write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def committed_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "ledger"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    directory = repository / PREFIX
    directory.mkdir(parents=True)
    task = _snapshot()["tasks"][0]["task"]
    _write_json(
        directory / "task.yaml",
        {**task, "task_id": "TASK-0001", "goal": "private-committed-goal"},
    )
    context: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "review_stage": "implementation",
        "base_commit": "a" * 40,
        "subject_commit": "e" * 40,
        "spec_sha256": "b" * 64,
        "evidence_sha256": "f" * 64,
        "content": {"goal": "private-context-goal"},
    }
    digest = hashlib.sha256(
        json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    context["context_sha256"] = digest
    _write_json(directory / f"review-contexts/{digest}.json", context)
    for revision, status in ((1, "open"), (2, "resolved")):
        finding: dict[str, Any] = {
            "finding_id": "RF-0001",
            "severity": "high",
            "status": status,
            "title": "private-finding-text",
        }
        if status == "resolved":
            finding["resolution"] = {
                "resolved_at": "2026-10-12T00:00:00Z",
                "rationale": "private-resolution-text",
                "actor": "unverified-model-claim",
            }
        _write_json(
            directory / f"reviews/REV-0001-r{revision:04d}.json",
            {
                "schema_version": "1.0",
                "task_id": "TASK-0001",
                "review_id": "REV-0001",
                "revision": revision,
                "review_stage": "implementation",
                "outcome": "REQUEST_CHANGES",
                "context_sha256": digest,
                "recorded_at": "2026-10-11T00:00:00Z",
                "reviewer": "unverified-model-claim",
                "findings": [finding],
            },
        )
    rows = []
    for sequence, (kind, state, payload) in enumerate(
        [
            ("verification_started", "VERIFYING", {}),
            ("verification_failed", "FAILED", {"conclusion": "failed"}),
            ("verification_started", "VERIFYING", {}),
            ("verification_passed", "VERIFIED", {"conclusion": "passed"}),
            (
                "review_recorded",
                "REVIEWED",
                {
                    "review_id": "REV-0001",
                    "revision": 1,
                    "review_stage": "implementation",
                    "context_sha256": digest,
                },
            ),
            (
                "review_finding_resolved",
                "IMPLEMENTING",
                {"review_id": "REV-0001", "revision": 2, "finding_id": "RF-0001"},
            ),
        ],
        start=1,
    ):
        rows.append(
            {
                "schema_version": "1.0",
                "task_id": "TASK-0001",
                "sequence": sequence,
                "event_type": kind,
                "from_state": "IMPLEMENTING",
                "to_state": state,
                "actor": "private-event-actor",
                "occurred_at": "2026-10-11T00:00:00Z",
                "payload": payload,
            }
        )
    (directory / "events.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    _write_json(
        directory / "evidence.json",
        {"task_id": "TASK-0001", "conclusion": "passed", "checks": []},
    )
    _write_json(directory / "logs/run/evidence.json", {"secret": "private-log-content"})
    _git(repository, "add", ".")
    _git(
        repository,
        "-c",
        "user.name=Fixture Author",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--quiet",
        "--no-verify",
        "-m",
        "Synthetic feedback fixture",
    )
    (directory / "task.yaml").write_text("private-dirty-task", encoding="utf-8")
    (directory / "reviews/REV-9999-r0001.json").write_text(
        "private-untracked-review", encoding="utf-8"
    )
    return repository


def _fingerprint(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def _cli(script: Path, repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "0"
    return subprocess.run(
        [sys.executable, "-B", str(script), str(repository), *arguments],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def test_cli_reads_committed_feedback_and_does_not_write_or_disclose_private_material(
    tmp_path: Path, committed_repository: Path
) -> None:
    tool_directory = tmp_path / "copied-tools"
    tool_directory.mkdir()
    for filename in ("review_feedback.py", "approval_overhead.py", "benchmark_reference.py"):
        shutil.copyfile(SCRIPT.parent / filename, tool_directory / filename)
    script = tool_directory / SCRIPT.name
    before = _fingerprint(tmp_path)
    expected_commit = _git(committed_repository, "rev-parse", "HEAD").decode().strip()

    result = _cli(script, committed_repository)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.isascii()
    report = json.loads(result.stdout)
    assert report["source_commit"] == expected_commit
    assert report["executed_tool_sha256"] == hashlib.sha256(script.read_bytes()).hexdigest()
    assert (
        report["snapshot_tool_sha256"]
        == hashlib.sha256((tool_directory / "approval_overhead.py").read_bytes()).hexdigest()
    )
    assert report["tasks"][0]["current_state"] == "MERGED"
    assert report["tasks"][0]["reviews"][0]["context"]["subject_commit"] == "e" * 40
    assert [item["status"] for item in _history(report)["observations"]] == ["open", "resolved"]
    link = report["tasks"][0]["reviews"][1]["event_links"][0]
    assert {key: value for key, value in link.items() if key != "source"} == {
        "sequence": 6,
        "event_type": "review_finding_resolved",
        "binding": "finding_revision_reference",
        "finding_id": "RF-0001",
    }
    assert link["source"]["path"] == PREFIX + "events.jsonl"
    assert link["source"]["locator"] == "task_id=TASK-0001,sequence=6"
    assert link["source"]["source_commit"] == expected_commit
    assert "private-" not in result.stdout
    assert "unverified-model-claim" not in result.stdout
    assert all("/logs/" not in source["ref"] for source in report["sources"])
    assert _fingerprint(tmp_path) == before


def test_cli_reference_hash_binds_exact_original_bytes(
    tmp_path: Path, committed_repository: Path
) -> None:
    path = tmp_path / "reference.json"
    original = json.dumps(_reference_input(), ensure_ascii=False, indent=2).encode() + b"\n"
    path.write_bytes(original)
    result = _cli(SCRIPT, committed_repository, "--reference-input", str(path))
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["external_reference"]["input_sha256"] == hashlib.sha256(original).hexdigest()
    assert report["external_reference"]["reference_status"] == "available"
    assert report["actual_model_identity"] == "unknown"
    assert report["model_score_update_status"] == "not_implemented"


@pytest.mark.parametrize("reference_input", [_reference_input(), None])
def test_main_reference_path_preserves_hash_or_fails_without_partial_feedback(
    tmp_path: Path,
    committed_repository: Path,
    feedback: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    reference_input: dict[str, Any] | None,
) -> None:
    reference_path = tmp_path / "reference.json"
    original = json.dumps(reference_input, indent=2).encode() + b"\n"
    reference_path.write_bytes(original)
    monkeypatch.setattr(sys, "dont_write_bytecode", False)

    code = feedback.main([str(committed_repository), "--reference-input", str(reference_path)])

    captured = capsys.readouterr()
    assert sys.dont_write_bytecode is True
    if reference_input is None:
        assert code == 2
        assert captured.out == ""
        assert "invalid" in captured.err
    else:
        assert code == 0
        assert captured.err == ""
        report = json.loads(captured.out)
        assert report["external_reference"]["input_sha256"] == hashlib.sha256(original).hexdigest()
        assert report["tasks"][0]["current_state"] == "MERGED"


@pytest.mark.parametrize(
    "contents",
    [
        b"{private-input-secret}",
        b'{"secret":"private-input-secret","secret":"replacement"}',
        b'{"secret":"private-input-secret","score":NaN}',
        b'{"secret":"private-input-secret","score":Infinity}',
        b'{"secret":"private-input-secret","score":-Infinity}',
        b'{"secret":"private-input-secret","score":1e400}',
        b'{"secret":"private-input-secret"}',
        b"\xffprivate-input-secret",
        b"null",
        b"[" * 2000 + b"]" * 2000,
    ],
)
def test_cli_invalid_reference_has_no_partial_feedback_or_raw_input(
    tmp_path: Path, committed_repository: Path, contents: bytes
) -> None:
    path = tmp_path / "invalid-reference.json"
    path.write_bytes(contents)
    result = _cli(SCRIPT, committed_repository, "--reference-input", str(path))
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "private-input-secret" not in result.stderr


@pytest.mark.parametrize("issue", ["missing", "directory"])
def test_cli_unreadable_reference_is_a_safe_error(
    tmp_path: Path, committed_repository: Path, issue: str
) -> None:
    path = tmp_path / "reference.json"
    if issue == "directory":
        path.mkdir()
    result = _cli(SCRIPT, committed_repository, "--reference-input", str(path))
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        ("--task", "TASK-0001", "--task", "TASK-0001"),
        ("--task", "TASK-1"),
        ("--task", "TASK-9999"),
    ],
)
def test_cli_rejects_duplicate_invalid_and_nonexistent_task_filters(
    committed_repository: Path, arguments: tuple[str, ...]
) -> None:
    result = _cli(SCRIPT, committed_repository, *arguments)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr


def test_cli_filters_existing_task_and_accepts_default_cwd(
    committed_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    feedback: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(committed_repository)
    assert feedback.main(["--task", "TASK-0001"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert [task["task_id"] for task in json.loads(captured.out)["tasks"]] == ["TASK-0001"]


def test_cli_non_git_directory_does_not_disclose_process_failure(tmp_path: Path) -> None:
    result = _cli(SCRIPT, tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
