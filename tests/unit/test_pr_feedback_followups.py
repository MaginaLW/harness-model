"""Independent counterexamples for reported PR finding followups and rechecks."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/analysis/pr_feedback.py"
PR_URL = "https://github.com/synthetic/project/pull/17"
ORIGINAL = "b" * 40
REPAIRED = "a" * 40
SAFE_ERROR = "pr-feedback: supplied records or reference input are invalid"


@pytest.fixture
def feedback(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("pr_feedback", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _review(
    review_id: str = "initial",
    *,
    role: str = "non_author_reported",
    outcome: str = "REQUEST_CHANGES",
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "review_id": review_id,
        "role": role,
        "outcome": outcome,
        "original_ref": PR_URL + "#pullrequestreview-1",
        "findings": [
            {
                "finding_id": "RF-001",
                "severity": "high",
                "status": "open",
                "original_ref": PR_URL + "#discussion_r1",
            }
        ]
        if findings is None
        else findings,
    }


def _record(
    record_id: str,
    *,
    candidate: str | None = ORIGINAL,
    reviews: list[dict[str, Any]] | None = None,
    followups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "1.0" if followups is None else "2.0",
        "record_id": record_id,
        "candidate_commit": candidate,
        "category": "coding",
        "reviews": [] if reviews is None else reviews,
    }
    if followups is not None:
        record["followups"] = followups
    return record


def _followup(**changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "finding_ref": {"record_id": "origin", "review_id": "initial", "finding_id": "RF-001"},
        "author_disposition": {
            "decision": "accepted",
            "original_ref": PR_URL + "#issuecomment-2",
        },
        "repair": {
            "kind": "code_change",
            "candidate_commit": REPAIRED,
            "original_ref": PR_URL + "#issuecomment-3",
        },
        "recheck_ref": {"record_id": "check", "review_id": "recheck"},
    }
    value.update(changes)
    return value


def _body(*records: dict[str, Any], fenced: bool = False) -> str:
    pieces = []
    for record in records:
        version = "v1" if record["schema_version"] == "1.0" else "v2"
        contents = json.dumps(record)
        if fenced:
            contents = "```json\n" + contents + "\n```"
        pieces.append(
            f"<!-- aiflow-review-feedback:{version} -->\n{contents}\n"
            f"<!-- /aiflow-review-feedback:{version} -->"
        )
    return "私人细节 PRIVATE_BODY_MARKER\n" + "\n".join(pieces)


def _document(*records: dict[str, Any], body: str | None = None) -> dict[str, Any]:
    if not records and body is None:
        records = (
            _record("origin", reviews=[_review()]),
            _record(
                "check",
                candidate=REPAIRED,
                reviews=[_review("recheck", outcome="APPROVE", findings=[])],
            ),
            _record("followup", candidate=REPAIRED, followups=[_followup()]),
        )
    return {
        "schema_version": "1.0",
        "repository": "synthetic/project",
        "retrieved_at": "2026-10-12T01:00:00+08:00",
        "pull_request": {
            "number": 17,
            "url": PR_URL,
            "state": "closed",
            "merged": True,
            "head_sha": REPAIRED,
            "merge_commit_sha": "c" * 40,
            "body": _body(*records) if body is None else body,
            "author": {"login": "PRIVATE_AUTHOR_MARKER"},
        },
        "native_reviews": {"reviews": []},
        "native_threads": {"review_threads": []},
        "workflows": {
            "requested_commit_sha": REPAIRED,
            "data": {
                "workflow_runs": [
                    {"id": 1, "name": "Fixture CI", "status": "completed", "conclusion": "success"}
                ]
            },
        },
    }


def _codes(report: dict[str, Any]) -> list[str]:
    return [question["code"] for question in report["next_review_questions"]]


def _supplied_followup(report: dict[str, Any], index: int = 0) -> dict[str, Any]:
    return report["reported_followups"][index]


def _reference_input() -> object:
    example = ROOT / "docs/operations/examples/benchmark-reference/swebench.json"
    return json.loads(example.read_text(encoding="utf-8"))


def test_v1_only_retains_legacy_shape_and_mixed_markers_add_separate_followups(
    feedback: Any,
) -> None:
    origin = _record("origin", reviews=[_review()])
    legacy = feedback.build_pr_feedback(_document(origin))
    assert legacy["schema_version"] == "1.0"
    assert "reported_followups" not in legacy
    assert "reported_followup_records" not in legacy["coverage"]

    document = _document()
    assert document["schema_version"] == "1.0"
    report = feedback.build_pr_feedback(document)
    assert report["schema_version"] == "2.0"
    assert report["reported_feedback"][0] == legacy["reported_feedback"][0]
    assert [record["schema_version"] for record in report["reported_feedback"]] == [
        "1.0",
        "1.0",
        "2.0",
    ]
    assert all("followups" not in record for record in report["reported_feedback"])
    assert report["coverage"]["reported_followup_records"] == 1


@pytest.mark.parametrize("fenced", [False, True])
def test_matched_reported_links_keep_original_finding_and_precise_sources(
    feedback: Any, fenced: bool
) -> None:
    document = _document()
    records = (
        _record("origin", reviews=[_review()]),
        _record(
            "check",
            candidate=REPAIRED,
            reviews=[_review("recheck", findings=[], outcome="APPROVE")],
        ),
        _record("followup", candidate=REPAIRED, followups=[_followup()]),
    )
    document["pull_request"]["body"] = _body(*records, fenced=fenced)
    report = feedback.build_pr_feedback(document)
    followup = _supplied_followup(report)
    finding = report["reported_feedback"][0]["reviews"][0]["findings"][0]
    recheck = report["reported_feedback"][1]["reviews"][0]

    assert followup["record_kind"] == "coordinator_reported"
    assert followup["record_id"] == "followup"
    assert followup["finding_linkage"] == "matched_reported"
    assert followup["finding_source"] == finding["source"]
    assert followup["original_candidate_commit"] == ORIGINAL
    assert followup["source"] == {"url": PR_URL, "locator": "body.feedback[followup].followups[0]"}
    assert followup["author_disposition"] == {
        "decision": "accepted",
        "original_ref": PR_URL + "#issuecomment-2",
        "original_reference_status": "not_fetched",
    }
    assert followup["repair"] == {
        "kind": "code_change",
        "candidate_commit": REPAIRED,
        "original_ref": PR_URL + "#issuecomment-3",
        "original_reference_status": "not_fetched",
    }
    assert (
        followup["recheck_linkage"] == followup["recheck_candidate_binding"] == "matched_reported"
    )
    assert followup["reported_recheck"] == {
        "role": "non_author_reported",
        "outcome": "APPROVE",
        "candidate_commit": REPAIRED,
        "source": recheck["source"],
        "original_ref": recheck["original_ref"],
        "original_reference_status": "not_fetched",
    }
    assert finding["status"] == "open"
    assert finding["author_disposition"] == "unknown"
    assert finding["independent_recheck"] == finding["independent_truth"] == "unknown"
    assert report["reported_feedback"][0]["reviews"][0]["outcome"] == "REQUEST_CHANGES"
    assert followup["independent_recheck"] == followup["independent_truth"] == "unknown"
    assert followup["actual_model_identity"] == "unknown"


def test_forward_references_are_resolved_across_all_blocks(feedback: Any) -> None:
    report = feedback.build_pr_feedback(
        _document(
            _record("followup", candidate=REPAIRED, followups=[_followup()]),
            _record(
                "check",
                candidate=REPAIRED,
                reviews=[_review("recheck", findings=[], outcome="APPROVE")],
            ),
            _record("origin", reviews=[_review()]),
        )
    )
    followup = _supplied_followup(report)
    assert followup["finding_linkage"] == followup["recheck_linkage"] == "matched_reported"
    assert followup["recheck_candidate_binding"] == "matched_reported"
    assert followup["original_candidate_commit"] == ORIGINAL
    assert "LOCATE_FOLLOWUP_FINDING" not in _codes(report)
    assert "LOCATE_FOLLOWUP_RECHECK" not in _codes(report)


def test_empty_v2_followup_collection_is_not_a_claim_of_disposition_or_recheck(
    feedback: Any,
) -> None:
    report = feedback.build_pr_feedback(_document(_record("empty", followups=[])))
    assert report["schema_version"] == "2.0"
    assert report["reported_followups"] == []
    assert report["coverage"]["reported_followup_records"] == 0
    assert "LOCATE_FOLLOWUP_FINDING" not in _codes(report)
    assert "LOCATE_FOLLOWUP_RECHECK" not in _codes(report)
    assert report["actual_model_identity"] == "unknown"


@pytest.mark.parametrize("missing_field", ["record_id", "review_id", "finding_id"])
def test_matching_finding_id_cannot_fill_any_missing_reference_component(
    feedback: Any, missing_field: str
) -> None:
    followup = _followup()
    followup["finding_ref"][missing_field] = "RF-999" if missing_field == "finding_id" else "absent"
    report = feedback.build_pr_feedback(
        _document(_record("origin", reviews=[_review()]), _record("fup", followups=[followup]))
    )
    supplied = _supplied_followup(report)
    assert supplied["finding_linkage"] == "not_in_capture"
    assert supplied["finding_source"] is None
    assert supplied["original_candidate_commit"] is None
    assert "LOCATE_FOLLOWUP_FINDING" in _codes(report)


def test_same_finding_ids_in_other_blocks_do_not_receive_linked_followup_sources(
    feedback: Any,
) -> None:
    first = _review()
    second = _review()
    second["findings"][0]["severity"] = "low"
    report = feedback.build_pr_feedback(
        _document(
            _record("origin", reviews=[first]),
            _record("other", candidate=REPAIRED, reviews=[second]),
            _record("fup", followups=[_followup(recheck_ref=None)]),
        )
    )
    supplied = _supplied_followup(report)
    assert supplied["original_candidate_commit"] == ORIGINAL
    assert supplied["finding_source"]["locator"].startswith("body.feedback[origin].")
    questions = [
        question
        for question in report["next_review_questions"]
        if question["code"] == "INSPECT_REPORTED_OPEN_FINDING"
    ]
    assert len(questions) == 2
    for question in questions:
        if "followup_sources" in question:
            expected = [supplied["source"]] if question["record_id"] == "origin" else []
            assert question["followup_sources"] == expected


def test_every_followup_round_and_previous_failure_survives_later_reported_approval(
    feedback: Any,
) -> None:
    rejected = _followup(
        author_disposition={"decision": "rejected", "original_ref": None},
        repair={"kind": "unknown", "candidate_commit": None, "original_ref": None},
        recheck_ref=None,
    )
    document = _document(
        _record("origin", reviews=[_review()]),
        _record("fup1", candidate=ORIGINAL, followups=[rejected]),
        _record(
            "check",
            candidate=REPAIRED,
            reviews=[_review("recheck", findings=[], outcome="APPROVE")],
        ),
        _record("fup2", candidate=REPAIRED, followups=[_followup()]),
    )
    document["workflows"]["data"]["workflow_runs"].insert(
        0, {"id": 2, "name": "Earlier CI", "status": "completed", "conclusion": "failure"}
    )
    report = feedback.build_pr_feedback(document)
    assert [item["author_disposition"]["decision"] for item in report["reported_followups"]] == [
        "rejected",
        "accepted",
    ]
    assert [item["record_id"] for item in report["reported_followups"]] == ["fup1", "fup2"]
    assert report["coverage"]["reported_followup_records"] == 2
    assert report["reported_feedback"][0]["candidate_commit"] == ORIGINAL
    assert report["reported_feedback"][0]["reviews"][0]["findings"][0]["status"] == "open"
    assert report["reported_feedback"][0]["reviews"][0]["outcome"] == "REQUEST_CHANGES"
    assert [item["conclusion"] for item in report["workflow_observations"]] == [
        "failure",
        "success",
    ]
    assert "DIAGNOSE_RECORDED_CHECK_FAILURE" in _codes(report)
    assert "INSPECT_REPORTED_OPEN_FINDING" in _codes(report)
    assert "CHECK_REPORTED_REVIEW_CONCLUSION" in _codes(report)


@pytest.mark.parametrize("decision", ["accepted", "rejected", "undecided", "unknown"])
def test_reported_disposition_is_retained_without_becoming_finding_truth(
    feedback: Any, decision: str
) -> None:
    followup = _followup(
        author_disposition={"decision": decision, "original_ref": None}, recheck_ref=None
    )
    report = feedback.build_pr_feedback(
        _document(_record("origin", reviews=[_review()]), _record("fup", followups=[followup]))
    )
    supplied = _supplied_followup(report)
    assert supplied["author_disposition"]["decision"] == decision
    assert supplied["author_disposition"]["original_reference_status"] == "not_provided"
    assert supplied["recheck_linkage"] == "not_provided"
    assert supplied["reported_recheck"] is None
    assert supplied["recheck_candidate_binding"] == "unknown"
    assert ("LOCATE_FOLLOWUP_RECHECK" in _codes(report)) is (decision == "accepted")
    assert report["reported_feedback"][0]["reviews"][0]["findings"][0]["status"] == "open"


def test_accepted_unknown_repair_candidate_does_not_manufacture_recheck_need(feedback: Any) -> None:
    followup = _followup(
        repair={"kind": "unknown", "candidate_commit": None, "original_ref": None}, recheck_ref=None
    )
    report = feedback.build_pr_feedback(
        _document(
            _record("origin", candidate=None, reviews=[_review()]),
            _record("fup", followups=[followup]),
        )
    )
    supplied = _supplied_followup(report)
    assert supplied["original_candidate_commit"] is None
    assert supplied["repair"]["candidate_commit"] is None
    assert supplied["repair"]["original_reference_status"] == "not_provided"
    assert "LOCATE_FOLLOWUP_RECHECK" not in _codes(report)
    assert "CHECK_REPORTED_REPAIR_CANDIDATE" not in _codes(report)


@pytest.mark.parametrize("missing_field", ["record_id", "review_id"])
def test_nonempty_missing_recheck_reference_is_not_guessed_from_a_matching_id(
    feedback: Any, missing_field: str
) -> None:
    followup = _followup()
    followup["recheck_ref"][missing_field] = "absent"
    report = feedback.build_pr_feedback(
        _document(
            _record("origin", reviews=[_review()]),
            _record(
                "check",
                candidate=REPAIRED,
                reviews=[_review("recheck", findings=[], outcome="APPROVE")],
            ),
            _record("fup", followups=[followup]),
        )
    )
    supplied = _supplied_followup(report)
    assert supplied["recheck_linkage"] == "not_in_capture"
    assert supplied["reported_recheck"] is None
    assert supplied["recheck_candidate_binding"] == "unknown"
    assert "LOCATE_FOLLOWUP_RECHECK" in _codes(report)


@pytest.mark.parametrize(
    "repair_candidate,recheck_candidate,binding",
    [
        (REPAIRED, REPAIRED, "matched_reported"),
        (REPAIRED, ORIGINAL, "mismatched"),
        (None, REPAIRED, "unknown"),
        (REPAIRED, None, "unknown"),
        (None, None, "unknown"),
    ],
)
def test_recheck_candidate_is_compared_with_reported_repair_and_never_filled_from_head(
    feedback: Any, repair_candidate: str | None, recheck_candidate: str | None, binding: str
) -> None:
    followup = _followup(
        repair={"kind": "unknown", "candidate_commit": repair_candidate, "original_ref": None}
    )
    report = feedback.build_pr_feedback(
        _document(
            _record("origin", reviews=[_review()]),
            _record(
                "check",
                candidate=recheck_candidate,
                reviews=[_review("recheck", findings=[], outcome="APPROVE")],
            ),
            _record("fup", followups=[followup]),
        )
    )
    supplied = _supplied_followup(report)
    assert supplied["recheck_linkage"] == "matched_reported"
    assert supplied["reported_recheck"]["candidate_commit"] == recheck_candidate
    assert supplied["repair"]["candidate_commit"] == repair_candidate
    assert supplied["recheck_candidate_binding"] == binding
    assert ("CHECK_RECHECK_CANDIDATE_REFERENCE" in _codes(report)) is (
        binding != "matched_reported"
    )


@pytest.mark.parametrize("role", ["non_author_reported", "author_reported", "unknown"])
def test_recheck_role_is_a_claim_and_unclear_roles_generate_source_check(
    feedback: Any, role: str
) -> None:
    report = feedback.build_pr_feedback(
        _document(
            _record("origin", reviews=[_review()]),
            _record(
                "check",
                candidate=REPAIRED,
                reviews=[_review("recheck", role=role, findings=[], outcome="APPROVE")],
            ),
            _record("fup", followups=[_followup()]),
        )
    )
    supplied = _supplied_followup(report)
    assert supplied["reported_recheck"]["role"] == role
    assert supplied["independent_recheck"] == supplied["actual_model_identity"] == "unknown"
    assert ("CHECK_REPORTED_RECHECK_ROLE" in _codes(report)) is (role != "non_author_reported")


def test_recheck_reference_to_original_review_is_flagged_without_erasing_it(feedback: Any) -> None:
    followup = _followup(
        repair={"kind": "same_candidate_retry", "candidate_commit": ORIGINAL, "original_ref": None},
        recheck_ref={"record_id": "origin", "review_id": "initial"},
    )
    report = feedback.build_pr_feedback(
        _document(_record("origin", reviews=[_review()]), _record("fup", followups=[followup]))
    )
    supplied = _supplied_followup(report)
    assert supplied["recheck_linkage"] == "matched_reported"
    assert supplied["reported_recheck"]["outcome"] == "REQUEST_CHANGES"
    assert (
        supplied["reported_recheck"]["source"]["locator"]
        == "body.feedback[origin].reviews[initial]"
    )
    assert "CHECK_REPORTED_RECHECK_REFERENCE" in _codes(report)


@pytest.mark.parametrize(
    "kind,candidate,needs_check",
    [
        ("same_candidate_retry", ORIGINAL, False),
        ("same_candidate_retry", REPAIRED, True),
        ("code_change", ORIGINAL, True),
        ("code_change", REPAIRED, False),
        ("documentation_change", ORIGINAL, True),
        ("documentation_change", REPAIRED, False),
        ("contract_change", ORIGINAL, False),
        ("contract_change", REPAIRED, False),
        ("unknown", ORIGINAL, False),
        ("unknown", REPAIRED, False),
        ("same_candidate_retry", None, False),
        ("code_change", None, False),
    ],
)
def test_reported_repair_kind_and_candidate_conflicts_generate_only_scope_questions(
    feedback: Any, kind: str, candidate: str | None, needs_check: bool
) -> None:
    followup = _followup(
        repair={"kind": kind, "candidate_commit": candidate, "original_ref": None}, recheck_ref=None
    )
    report = feedback.build_pr_feedback(
        _document(_record("origin", reviews=[_review()]), _record("fup", followups=[followup]))
    )
    supplied = _supplied_followup(report)
    assert supplied["repair"]["kind"] == kind
    assert supplied["repair"]["candidate_commit"] == candidate
    assert ("CHECK_REPORTED_REPAIR_CANDIDATE" in _codes(report)) is needs_check
    for question in report["next_review_questions"]:
        if question["code"].startswith(("CHECK_REPORTED_REPAIR", "LOCATE_FOLLOWUP")):
            assert question["source"] == supplied["source"]


def test_separate_reference_and_followups_do_not_create_probability_or_permission_effect(
    feedback: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject_network(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Followup readback must not fetch links or execute provider calls.")

    monkeypatch.setattr(socket, "socket", reject_network)
    document = _document()
    before = copy.deepcopy(document)
    plain = feedback.build_pr_feedback(document)
    report = feedback.build_pr_feedback(document, reference_input=_reference_input())
    assert report["reported_followups"] == plain["reported_followups"]
    assert report["next_review_questions"] == plain["next_review_questions"]
    assert report["external_reference"]["reference_status"] == "available"
    assert report["actual_model_identity"] == "unknown"
    assert report["model_score_update_status"] == "not_implemented"
    assert report["probability_status"] == "unestimated"
    assert report["method_status"] == "design_pending"
    assert report["execution_allowed"] is False
    assert report["permission_effect"] == report["ledger_effect"] == "none"
    assert document == before
    assert "PRIVATE_" not in json.dumps(report)


def test_followup_output_is_not_a_mutable_alias_of_capture_or_original_records(
    feedback: Any,
) -> None:
    document = _document()
    before = copy.deepcopy(document)
    report = feedback.build_pr_feedback(document)
    supplied = _supplied_followup(report)
    supplied["author_disposition"]["decision"] = "unknown"
    supplied["repair"]["candidate_commit"] = None
    supplied["finding_ref"]["finding_id"] = "RF-999"
    supplied["reported_recheck"]["outcome"] = "REJECT"
    supplied["finding_source"]["locator"] = "changed"
    assert document == before
    assert report["reported_feedback"][0]["reviews"][0]["findings"][0]["source"][
        "locator"
    ].endswith(".findings[RF-001]")
    assert report["reported_feedback"][1]["reviews"][0]["outcome"] == "APPROVE"


def _nested_followup(record: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    value = record["followups"][0]
    for key in path:
        value = value[key]
    return value


@pytest.mark.parametrize(
    "path,field",
    [
        ((), "finding_ref"),
        ((), "author_disposition"),
        ((), "repair"),
        ((), "recheck_ref"),
        (("finding_ref",), "record_id"),
        (("finding_ref",), "review_id"),
        (("finding_ref",), "finding_id"),
        (("author_disposition",), "decision"),
        (("author_disposition",), "original_ref"),
        (("repair",), "kind"),
        (("repair",), "candidate_commit"),
        (("repair",), "original_ref"),
        (("recheck_ref",), "record_id"),
        (("recheck_ref",), "review_id"),
    ],
)
def test_each_followup_field_is_required_instead_of_being_defaulted(
    feedback: Any, path: tuple[str, ...], field: str
) -> None:
    record = _record("fup", followups=[_followup()])
    del _nested_followup(record, path)[field]
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(record))


@pytest.mark.parametrize(
    "path", [(), ("finding_ref",), ("author_disposition",), ("repair",), ("recheck_ref",)]
)
def test_followup_names_body_identity_and_unrecognized_fields_are_rejected(
    feedback: Any, path: tuple[str, ...]
) -> None:
    record = _record("fup", followups=[_followup()])
    _nested_followup(record, path)["actual_model_identity"] = "PRIVATE_INPUT"
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(record))


@pytest.mark.parametrize(
    "path,field,value",
    [
        ((), "finding_ref", None),
        ((), "finding_ref", []),
        ((), "author_disposition", "PRIVATE_INPUT"),
        ((), "repair", []),
        ((), "recheck_ref", []),
        (("finding_ref",), "record_id", "../PRIVATE_INPUT"),
        (("finding_ref",), "review_id", False),
        (("finding_ref",), "finding_id", "RF-1"),
        (("author_disposition",), "decision", "approved"),
        (("author_disposition",), "decision", None),
        (("repair",), "kind", "deployment"),
        (("repair",), "candidate_commit", True),
        (("repair",), "candidate_commit", "a" * 39),
        (("repair",), "candidate_commit", "A" * 40),
        (("recheck_ref",), "record_id", ""),
        (("recheck_ref",), "review_id", "PRIVATE INPUT"),
    ],
)
def test_invalid_followup_shape_and_field_values_are_rejected(
    feedback: Any, path: tuple[str, ...], field: str, value: Any
) -> None:
    record = _record("fup", followups=[_followup()])
    _nested_followup(record, path)[field] = value
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(record))


@pytest.mark.parametrize("field", ["author_disposition", "repair"])
@pytest.mark.parametrize(
    "reference",
    [PR_URL.replace("/17", "/18") + "#issuecomment-1", "https://private.invalid/secret", PR_URL],
)
def test_followup_original_links_must_be_explicit_same_pr_anchors_or_null(
    feedback: Any, field: str, reference: str
) -> None:
    record = _record("fup", followups=[_followup()])
    record["followups"][0][field]["original_ref"] = reference
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(record))


@pytest.mark.parametrize("value", [None, {}, "PRIVATE_INPUT", [None]])
def test_v2_followups_must_be_an_explicit_valid_array(feedback: Any, value: Any) -> None:
    record = _record("fup", followups=[])
    record["followups"] = value
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(record))


@pytest.mark.parametrize(
    "marker_version,schema_version", [("v1", "2.0"), ("v2", "1.0"), ("v2", "3.0")]
)
def test_feedback_marker_and_block_schema_must_agree(
    feedback: Any, marker_version: str, schema_version: str
) -> None:
    record = _record("fup", followups=[])
    record["schema_version"] = schema_version
    body = (
        f"<!-- aiflow-review-feedback:{marker_version} -->\n{json.dumps(record)}\n"
        f"<!-- /aiflow-review-feedback:{marker_version} -->"
    )
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(body=body))


def test_missing_v2_followups_is_rejected_and_v1_cannot_accept_the_new_field(feedback: Any) -> None:
    record = _record("fup", followups=[])
    del record["followups"]
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(record))
    record["schema_version"] = "1.0"
    record["followups"] = []
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(record))


@pytest.mark.parametrize(
    "body",
    [
        "<!-- aiflow-review-feedback:v2 -->\n{}\n<!-- /aiflow-review-feedback:v1 -->",
        "<!-- aiflow-review-feedback:v1 -->\n{}\n<!-- /aiflow-review-feedback:v2 -->",
        "<!-- aiflow-review-feedback:v2 -->\n{}",
        "<!-- /aiflow-review-feedback:v2 -->",
        "<!-- aiflow-review-feedback:v2 -->\n<!-- aiflow-review-feedback:v1 -->\n{}\n"
        "<!-- /aiflow-review-feedback:v1 -->\n<!-- /aiflow-review-feedback:v2 -->",
    ],
)
def test_mixed_version_markers_cannot_hide_unpaired_or_nested_blocks(
    feedback: Any, body: str
) -> None:
    with pytest.raises(ValueError):
        feedback.build_pr_feedback(_document(body=body))


def _cli(raw: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT)], input=raw, capture_output=True, check=False, timeout=30
    )


def test_cli_v2_stdin_hash_preserves_exact_bytes_without_raw_body_or_names() -> None:
    document = _document()
    raw = json.dumps(document, indent=2, ensure_ascii=False).encode() + b"\n\n"
    result = _cli(raw)
    assert result.returncode == 0, result.stderr.decode()
    assert result.stderr == b""
    assert result.stdout.isascii()
    report = json.loads(result.stdout)
    assert report["schema_version"] == "2.0"
    assert report["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["executed_tool_sha256"] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert report["coverage"]["reported_followup_records"] == 1
    assert b"PRIVATE_" not in result.stdout
    assert report["actual_model_identity"] == "unknown"


@pytest.mark.parametrize("nested_duplicate", [False, True])
def test_duplicate_v2_json_keys_fail_safely_without_partial_legacy_report(
    nested_duplicate: bool,
) -> None:
    record = _record("fup", followups=[_followup()])
    payload = json.dumps(record)
    if nested_duplicate:
        payload = payload.replace(
            '"decision": "accepted"', '"decision": "accepted", "decision": "PRIVATE_INPUT"'
        )
    else:
        payload = payload[:-1] + ', "followups": []}'
    document = _document(
        body=_body(_record("origin", reviews=[_review()]))
        + "\n"
        + "<!-- aiflow-review-feedback:v2 -->\n"
        + payload
        + "\n<!-- /aiflow-review-feedback:v2 -->"
    )
    result = _cli(json.dumps(document).encode())
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode().strip() == SAFE_ERROR


@pytest.mark.parametrize("failure", ["unknown_field", "invalid_reference", "missing_field"])
def test_invalid_followup_main_has_only_safe_error_and_no_partial_projection(
    feedback: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failure: str
) -> None:
    followup = _followup()
    if failure == "unknown_field":
        followup["body"] = "PRIVATE_INPUT"
    elif failure == "invalid_reference":
        followup["repair"]["original_ref"] = "https://private.invalid/PRIVATE_INPUT"
    else:
        del followup["author_disposition"]
    document = _document(
        _record("origin", reviews=[_review()]), _record("fup", followups=[followup])
    )
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(document).encode())))
    assert feedback.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == SAFE_ERROR


def test_same_finding_can_have_multiple_followup_entries_with_distinct_array_sources(
    feedback: Any,
) -> None:
    report = feedback.build_pr_feedback(
        _document(
            _record("origin", reviews=[_review()]),
            _record("fup", followups=[_followup(), _followup()]),
        )
    )
    assert report["coverage"]["reported_followup_records"] == 2
    assert [item["source"]["locator"] for item in report["reported_followups"]] == [
        "body.feedback[fup].followups[0]",
        "body.feedback[fup].followups[1]",
    ]
    assert all(item["independent_truth"] == "unknown" for item in report["reported_followups"])


@pytest.mark.parametrize("kind", ["same_candidate_retry", "code_change", "documentation_change"])
def test_unknown_original_candidate_cannot_be_filled_from_head_to_assert_repair_conflict(
    feedback: Any, kind: str
) -> None:
    followup = _followup(
        repair={"kind": kind, "candidate_commit": REPAIRED, "original_ref": None}, recheck_ref=None
    )
    report = feedback.build_pr_feedback(
        _document(
            _record("origin", candidate=None, reviews=[_review()]),
            _record("fup", followups=[followup]),
        )
    )
    assert _supplied_followup(report)["original_candidate_commit"] is None
    assert "CHECK_REPORTED_REPAIR_CANDIDATE" not in _codes(report)
    assert "LOCATE_FOLLOWUP_RECHECK" in _codes(report)


def test_supplied_self_recheck_is_visible_even_when_both_references_are_outside_capture(
    feedback: Any,
) -> None:
    followup = _followup(
        finding_ref={"record_id": "absent", "review_id": "initial", "finding_id": "RF-001"},
        recheck_ref={"record_id": "absent", "review_id": "initial"},
    )
    report = feedback.build_pr_feedback(_document(_record("fup", followups=[followup])))
    supplied = _supplied_followup(report)
    assert supplied["finding_linkage"] == supplied["recheck_linkage"] == "not_in_capture"
    assert supplied["finding_source"] is supplied["reported_recheck"] is None
    assert "CHECK_REPORTED_RECHECK_REFERENCE" in _codes(report)
    assert "LOCATE_FOLLOWUP_FINDING" in _codes(report)
    assert "LOCATE_FOLLOWUP_RECHECK" in _codes(report)
    for question in report["next_review_questions"]:
        if question["code"] in {
            "CHECK_REPORTED_RECHECK_REFERENCE",
            "LOCATE_FOLLOWUP_FINDING",
            "LOCATE_FOLLOWUP_RECHECK",
        }:
            assert question["source"] == supplied["source"]
