"""Text output retains uncertainty and source checks without exposing raw capture text."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
PR_SCRIPT = ROOT / "tools/analysis/pr_feedback.py"
HEAD = "a" * 40
PR_URL = "https://github.com/synthetic/project/pull/17"


@pytest.fixture
def advisory() -> Any:
    spec = importlib.util.spec_from_file_location(
        "review_advisory_text", ROOT / "tools/analysis/review_advisory.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture() -> dict[str, Any]:
    original = {
        "schema_version": "1.0",
        "record_id": "original",
        "candidate_commit": "b" * 40,
        "category": "documentation",
        "reviews": [
            {
                "review_id": "first",
                "role": "non_author_reported",
                "outcome": "REQUEST_CHANGES",
                "original_ref": None,
                "findings": [
                    {
                        "finding_id": "RF-001",
                        "severity": "high",
                        "status": "open",
                        "original_ref": None,
                    }
                ],
            }
        ],
    }
    followup = {
        "schema_version": "2.0",
        "record_id": "later",
        "candidate_commit": HEAD,
        "category": "documentation",
        "reviews": [],
        "followups": [
            {
                "finding_ref": {
                    "record_id": "original",
                    "review_id": "first",
                    "finding_id": "RF-001",
                },
                "author_disposition": {"decision": "accepted", "original_ref": None},
                "repair": {
                    "kind": "documentation_change",
                    "candidate_commit": HEAD,
                    "original_ref": None,
                },
                "recheck_ref": None,
            }
        ],
    }
    body = "PRIVATE_BODY_MARKER\n"
    for version, record in (("v1", original), ("v2", followup)):
        body += (
            f"<!-- aiflow-review-feedback:{version} -->\n{json.dumps(record)}\n"
            f"<!-- /aiflow-review-feedback:{version} -->\n"
        )
    return {
        "schema_version": "1.0",
        "repository": "synthetic/project",
        "retrieved_at": "2026-10-13T00:00:00+00:00",
        "pull_request": {
            "number": 17,
            "url": PR_URL,
            "state": "closed",
            "merged": True,
            "head_sha": HEAD,
            "merge_commit_sha": "c" * 40,
            "body": body,
            "title": "PRIVATE_TITLE_MARKER",
        },
        "native_reviews": {"reviews": [{"body": "PRIVATE_REVIEW_MARKER"}]},
        "native_threads": None,
        "workflows": {
            "requested_commit_sha": HEAD,
            "data": {
                "workflow_runs": [
                    {
                        "id": 8,
                        "name": "PRIVATE_WORKFLOW_NAME_MARKER",
                        "status": "completed",
                        "conclusion": "cancelled",
                    }
                ]
            },
        },
    }


def _pr_cli(document: object, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(PR_SCRIPT), *args],
        input=json.dumps(document),
        encoding="utf-8",
        capture_output=True,
        check=False,
        cwd=ROOT,
    )


def test_pr_default_json_is_identical_to_explicit_json() -> None:
    default = _pr_cli(_capture())
    explicit = _pr_cli(_capture(), "--format", "json")
    assert default.returncode == explicit.returncode == 0
    assert default.stdout == explicit.stdout
    assert default.stderr == explicit.stderr == ""
    assert json.loads(default.stdout)["schema_version"] == "2.0"


def test_pr_text_preserves_failure_followup_uncertainty_and_source_questions() -> None:
    result = _pr_cli(_capture(), "--format", "text")
    assert result.returncode == 0 and result.stderr == ""
    for fact in (
        "REQUEST_CHANGES",
        "RF-001: high/open",
        "binding=mismatched",
        "disposition=accepted",
        "repair=documentation_change",
        "recheck=not_provided",
        "candidate_binding=unknown",
        "workflow 8: completed/cancelled",
        "INSPECT_REPORTED_OPEN_FINDING",
        "LOCATE_FOLLOWUP_RECHECK",
        "CHECK_NONPASS_RESULT_SCOPE",
        PR_URL + " @ body.feedback[original].reviews[first].findings[RF-001]",
        "history_completeness=unknown",
        "required_checks_status=unknown",
        "independent_truth=unknown",
        "independent_recheck=unknown",
        "actual_model_identity=unknown",
        "records_in_capture=unknown",
        "probability_status=unestimated",
        "execution_allowed=false",
        "permission_effect=none",
    ):
        assert fact in result.stdout
    assert "PRIVATE_" not in result.stdout


def test_pr_text_absence_and_capture_failure_do_not_imply_complete_history() -> None:
    capture = _capture()
    capture["pull_request"]["body"] = None
    capture["workflows"] = None
    result = _pr_cli(capture, "--format", "text")
    assert result.returncode == 0
    assert "feedback=not_captured; workflows=not_captured" in result.stdout
    assert "LOCATE_STRUCTURED_FEEDBACK" in result.stdout
    assert "GET_CHECK_SOURCE" in result.stdout
    assert "history_completeness=unknown" in result.stdout


def test_pr_text_no_questions_still_reports_unknown() -> None:
    capture = _capture()
    empty = {
        "schema_version": "1.0",
        "record_id": "empty",
        "candidate_commit": HEAD,
        "category": "documentation",
        "reviews": [],
    }
    capture["pull_request"]["body"] = (
        "<!-- aiflow-review-feedback:v1 -->\n"
        + json.dumps(empty)
        + "\n<!-- /aiflow-review-feedback:v1 -->"
    )
    capture["workflows"]["data"]["workflow_runs"][0]["conclusion"] = "success"
    result = _pr_cli(capture, "--format", "text")
    assert result.returncode == 0
    assert "none_in_supplied_projection; unknowns_above_remain" in result.stdout
    assert "required_checks_status=unknown" in result.stdout


def test_pr_text_invalid_input_keeps_safe_error_contract() -> None:
    result = _pr_cli({"PRIVATE_INVALID_MARKER": "not a capture"}, "--format", "text")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.strip() == "pr-feedback: supplied records or reference input are invalid"


def _summary(state: str = "WAITING_FOR_SPEC_REVIEW", **changes: object) -> SimpleNamespace:
    fields: dict[str, object] = {
        "current_state": state,
        "merge_readiness": "not_applicable",
        "route": "REVIEW",
        "verification_level": "V1",
        "classification": "fresh",
        "approvals": "current",
        "evidence": "not_available",
        "base_commit": "a" * 40,
        "subject_commit": None,
        "observed_head": "b" * 40,
        "worktree_dirty": False,
        "missing_conditions": ("spec_approval",),
        "goal": "PRIVATE_GOAL_MARKER",
    }
    fields.update(changes)
    return SimpleNamespace(**fields)


def test_advisory_default_json_matches_explicit_json(
    advisory: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(advisory, "summarize_task", lambda *_: _summary())
    assert advisory.main(["TASK-0001", "--repository", str(ROOT)]) == 0
    default = capsys.readouterr()
    assert advisory.main(["TASK-0001", "--repository", str(ROOT), "--format", "json"]) == 0
    explicit = capsys.readouterr()
    assert default == explicit


@pytest.mark.parametrize("state", ["WAITING_FOR_SPEC_REVIEW", "MERGED", "BLOCKED"])
def test_advisory_text_keeps_native_state_and_missing_authorization_boundaries(
    state: str,
    advisory: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(advisory, "summarize_task", lambda *_: _summary(state))
    monkeypatch.setattr(advisory, "evaluate_gate", lambda *_: pytest.fail("premature gate"))
    assert advisory.main(["TASK-0001", "--repository", str(ROOT), "--format", "text"]) == 0
    output = capsys.readouterr().out
    assert state in output
    assert 'approvals="current"' in output
    assert 'subject_commit="unknown"' in output
    assert "native_missing_conditions=spec_approval" in output
    assert "AUTHORIZATION_COVERAGE_NOT_EVALUATED" in output
    assert "SOURCE_READ_ATOMICITY_NOT_ESTABLISHED" in output
    assert "execution_allowed=false" in output
    assert "PRIVATE_" not in output and str(ROOT) not in output
    if state == "MERGED":
        assert "none_in_native_projection" in output
        assert "CHECK_EXISTING_APPROVALS" not in output
    elif state == "BLOCKED":
        assert "CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION" in output
    else:
        assert "CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION" in output


def test_advisory_text_failed_read_keeps_error_and_unknown_without_details(
    advisory: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(*_: object) -> None:
        raise ValueError("PRIVATE_ERROR_MARKER")

    monkeypatch.setattr(advisory, "summarize_task", fail)
    assert advisory.main(["TASK-0001", "--repository", str(ROOT), "--format", "text"]) == 1
    output = capsys.readouterr().out
    assert "native_status=unknown" in output
    assert "error_code=NATIVE_STATUS_READ_FAILED" in output
    assert "execution_allowed=false" in output
    assert "PRIVATE_" not in output
