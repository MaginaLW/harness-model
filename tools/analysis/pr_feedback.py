"""Read supplied public PR records and prepare questions without executing them."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

OUTCOMES = {"APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_CHANGES", "REJECT", "BLOCKED", "unknown"}
ROLES = {"non_author_reported", "author_reported", "unknown"}
SEVERITIES = {"critical", "high", "medium", "low", "unknown"}
STATUSES = {"open", "resolved", "unknown"}
RUN_STATUSES = {"queued", "in_progress", "completed", "requested", "waiting", "pending"}
CONCLUSIONS = {
    "success",
    "failure",
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
    "neutral",
    "stale",
    "startup_failure",
}


def _mapping(value: object, fields: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or (fields is not None and set(value) != fields):
        raise ValueError("invalid object fields")
    return cast(dict[str, Any], value)


def _list(value: object) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError("invalid collection")
    return value


def _text(value: object, pattern: str | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid string")
    if pattern is not None and re.fullmatch(pattern, value) is None:
        raise ValueError("invalid identifier")
    return value


def _enum(value: object, choices: set[str]) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ValueError("invalid enum")
    return value


def _sha(value: object, *, nullable: bool = False) -> str | None:
    return None if value is None and nullable else _text(value, r"[0-9a-f]{40}")


def _positive_id(value: object) -> int:
    if type(value) is not int or value < 1:
        raise ValueError("invalid numeric ID")
    return value


def _source(url: str, locator: str) -> dict[str, str]:
    return {"url": url, "locator": locator}


def _reference(value: object, pr_url: str) -> str | None:
    if value is None:
        return None
    ref = _text(value)
    if not ref.startswith(pr_url + "#") or not re.fullmatch(
        r"[A-Za-z0-9_-]+", ref[len(pr_url) + 1 :]
    ):
        raise ValueError("original reference must be a same-PR anchor")
    return ref


def _records(
    body: str, pr_url: str, head_sha: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from benchmark_reference import _reject_constant, _unique_object

    markers = list(re.finditer(r"<!--\s*(/?aiflow-review-feedback:[^>]*?)\s*-->", body))
    if len(re.findall(r"<!--\s*/?aiflow-review-feedback:", body)) != len(markers):
        raise ValueError("incomplete feedback marker")
    if len(markers) % 2:
        raise ValueError("unpaired feedback marker")
    records: list[dict[str, Any]] = []
    followups: list[dict[str, Any]] = []
    seen: set[str] = set()
    for start, end in zip(markers[::2], markers[1::2]):
        marker = start.group(1).strip()
        if (
            marker not in {"aiflow-review-feedback:v1", "aiflow-review-feedback:v2"}
            or end.group(1).strip() != "/" + marker
        ):
            raise ValueError("unsupported or nested feedback marker")
        version = "2.0" if marker.endswith(":v2") else "1.0"
        text = body[start.end() : end.start()].strip()
        if text.startswith("```"):
            fenced = re.fullmatch(r"```json[ \t]*\r?\n(.*?)\r?\n```", text, re.DOTALL)
            if fenced is None:
                raise ValueError("invalid feedback JSON fence")
            text = fenced.group(1)
        fields = {"schema_version", "record_id", "candidate_commit", "category", "reviews"}
        if version == "2.0":
            fields.add("followups")
        record = _mapping(
            json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant),
            fields,
        )
        if record["schema_version"] != version:
            raise ValueError("unsupported feedback version")
        record_id = _text(record["record_id"], r"[A-Za-z0-9_-]{1,64}")
        if record_id in seen:
            raise ValueError("duplicate feedback record")
        seen.add(record_id)
        candidate = _sha(record["candidate_commit"], nullable=True)
        category = _text(record["category"], r"[a-z][a-z0-9_-]{0,63}")
        reviews: list[dict[str, Any]] = []
        review_ids: set[str] = set()
        for item in _list(record["reviews"]):
            review = _mapping(item, {"review_id", "role", "outcome", "original_ref", "findings"})
            review_id = _text(review["review_id"], r"[A-Za-z0-9_-]{1,64}")
            if review_id in review_ids:
                raise ValueError("duplicate review ID")
            review_ids.add(review_id)
            locator = f"body.feedback[{record_id}].reviews[{review_id}]"
            original_ref = _reference(review["original_ref"], pr_url)
            findings: list[dict[str, Any]] = []
            finding_ids: set[str] = set()
            for value in _list(review["findings"]):
                finding = _mapping(value, {"finding_id", "severity", "status", "original_ref"})
                finding_id = _text(finding["finding_id"], r"RF-[0-9]{3,}")
                if finding_id in finding_ids:
                    raise ValueError("duplicate finding ID")
                finding_ids.add(finding_id)
                finding_ref = _reference(finding["original_ref"], pr_url)
                findings.append(
                    {
                        "finding_id": finding_id,
                        "severity": _enum(finding["severity"], SEVERITIES),
                        "status": _enum(finding["status"], STATUSES),
                        "original_ref": finding_ref,
                        "original_reference_status": (
                            "not_provided" if finding_ref is None else "not_fetched"
                        ),
                        "source": _source(pr_url, f"{locator}.findings[{finding_id}]"),
                        "author_disposition": "unknown",
                        "independent_recheck": "unknown",
                        "independent_truth": "unknown",
                    }
                )
            reviews.append(
                {
                    "review_id": review_id,
                    "role": _enum(review["role"], ROLES),
                    "outcome": _enum(review["outcome"], OUTCOMES),
                    "original_ref": original_ref,
                    "original_reference_status": (
                        "not_provided" if original_ref is None else "not_fetched"
                    ),
                    "findings": findings,
                    "source": _source(pr_url, locator),
                    "actual_model_identity": "unknown",
                }
            )
        records.append(
            {
                "schema_version": version,
                "record_id": record_id,
                "candidate_commit": candidate,
                "category": category,
                "reviews": reviews,
                "record_kind": "coordinator_reported",
                "candidate_binding": (
                    "unknown"
                    if candidate is None
                    else "matched_reported"
                    if candidate == head_sha
                    else "mismatched"
                ),
                "source": _source(pr_url, f"body.feedback[{record_id}]"),
            }
        )
        if version == "2.0":
            for index, value in enumerate(_list(record["followups"])):
                followup = _mapping(
                    value, {"finding_ref", "author_disposition", "repair", "recheck_ref"}
                )
                raw_finding_ref = _mapping(
                    followup["finding_ref"], {"record_id", "review_id", "finding_id"}
                )
                projected_ref = {
                    field: _text(
                        raw_finding_ref[field],
                        r"RF-[0-9]{3,}" if field == "finding_id" else r"[A-Za-z0-9_-]{1,64}",
                    )
                    for field in ("record_id", "review_id", "finding_id")
                }
                disposition = _mapping(followup["author_disposition"], {"decision", "original_ref"})
                disposition_ref = _reference(disposition["original_ref"], pr_url)
                repair = _mapping(followup["repair"], {"kind", "candidate_commit", "original_ref"})
                repair_ref = _reference(repair["original_ref"], pr_url)
                recheck_ref = None
                if followup["recheck_ref"] is not None:
                    raw_recheck_ref = _mapping(followup["recheck_ref"], {"record_id", "review_id"})
                    recheck_ref = {
                        field: _text(raw_recheck_ref[field], r"[A-Za-z0-9_-]{1,64}")
                        for field in ("record_id", "review_id")
                    }
                followups.append(
                    {
                        "record_id": record_id,
                        "finding_ref": projected_ref,
                        "author_disposition": {
                            "decision": _enum(
                                disposition["decision"],
                                {"accepted", "rejected", "undecided", "unknown"},
                            ),
                            "original_ref": disposition_ref,
                            "original_reference_status": (
                                "not_provided" if disposition_ref is None else "not_fetched"
                            ),
                        },
                        "repair": {
                            "kind": _enum(
                                repair["kind"],
                                {
                                    "code_change",
                                    "documentation_change",
                                    "same_candidate_retry",
                                    "contract_change",
                                    "unknown",
                                },
                            ),
                            "candidate_commit": _sha(repair["candidate_commit"], nullable=True),
                            "original_ref": repair_ref,
                            "original_reference_status": (
                                "not_provided" if repair_ref is None else "not_fetched"
                            ),
                        },
                        "recheck_ref": recheck_ref,
                        "source": _source(pr_url, f"body.feedback[{record_id}].followups[{index}]"),
                        "record_kind": "coordinator_reported",
                    }
                )
    return records, followups


def _link_followups(
    records: list[dict[str, Any]], followups: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Compare explicit references within this capture, without authenticating claims."""
    reviews = {
        (record["record_id"], review["review_id"]): (record, review)
        for record in records
        for review in record["reviews"]
    }
    findings = {
        (record["record_id"], review["review_id"], finding["finding_id"]): (record, finding)
        for record in records
        for review in record["reviews"]
        for finding in review["findings"]
    }
    questions: list[dict[str, Any]] = []
    for followup in followups:
        finding_ref = followup["finding_ref"]
        original = findings.get(
            (finding_ref["record_id"], finding_ref["review_id"], finding_ref["finding_id"])
        )
        original_candidate = None if original is None else original[0]["candidate_commit"]
        repair_candidate = followup["repair"]["candidate_commit"]
        recheck_ref = followup["recheck_ref"]
        recheck = (
            None
            if recheck_ref is None
            else reviews.get((recheck_ref["record_id"], recheck_ref["review_id"]))
        )
        recheck_candidate = None if recheck is None else recheck[0]["candidate_commit"]
        candidate_binding = (
            "unknown"
            if repair_candidate is None or recheck_candidate is None
            else "matched_reported"
            if repair_candidate == recheck_candidate
            else "mismatched"
        )
        followup.update(
            {
                "finding_linkage": "not_in_capture" if original is None else "matched_reported",
                "finding_source": None if original is None else dict(original[1]["source"]),
                "original_candidate_commit": original_candidate,
                "recheck_linkage": (
                    "not_provided"
                    if recheck_ref is None
                    else "not_in_capture"
                    if recheck is None
                    else "matched_reported"
                ),
                "reported_recheck": None
                if recheck is None
                else {
                    "role": recheck[1]["role"],
                    "outcome": recheck[1]["outcome"],
                    "candidate_commit": recheck_candidate,
                    "source": dict(recheck[1]["source"]),
                    "original_ref": recheck[1]["original_ref"],
                    "original_reference_status": recheck[1]["original_reference_status"],
                },
                "recheck_candidate_binding": candidate_binding,
                "independent_recheck": "unknown",
                "independent_truth": "unknown",
                "actual_model_identity": "unknown",
            }
        )
        codes: list[str] = []
        if original is None:
            codes.append("LOCATE_FOLLOWUP_FINDING")
        if (recheck_ref is not None and recheck is None) or (
            recheck_ref is None
            and followup["author_disposition"]["decision"] == "accepted"
            and repair_candidate is not None
        ):
            codes.append("LOCATE_FOLLOWUP_RECHECK")
        if original_candidate is not None and repair_candidate is not None:
            same_candidate = original_candidate == repair_candidate
            if (followup["repair"]["kind"] == "same_candidate_retry" and not same_candidate) or (
                followup["repair"]["kind"] in {"code_change", "documentation_change"}
                and same_candidate
            ):
                codes.append("CHECK_REPORTED_REPAIR_CANDIDATE")
        if recheck is not None:
            if candidate_binding != "matched_reported":
                codes.append("CHECK_RECHECK_CANDIDATE_REFERENCE")
            if recheck[1]["role"] in {"author_reported", "unknown"}:
                codes.append("CHECK_REPORTED_RECHECK_ROLE")
        if recheck_ref is not None and all(
            recheck_ref[field] == finding_ref[field] for field in ("record_id", "review_id")
        ):
            codes.append("CHECK_REPORTED_RECHECK_REFERENCE")
        questions.extend({"code": code, "source": dict(followup["source"])} for code in codes)
    return questions


def _native_collection(value: object, key: str, field: str, pr_url: str) -> dict[str, Any]:
    if value is None:
        rows = None
    else:
        rows = _list(_mapping(value).get(key))
        for row in rows:
            _mapping(row)
    return {
        "collection_status": "not_captured" if rows is None else "captured",
        "records_in_capture": None if rows is None else len(rows),
        "field_projection": "not_projected",
        "sources": []
        if rows is None
        else [_source(pr_url, f"{field}.{key}[{index}]") for index in range(len(rows))],
    }


def build_pr_feedback(document: object, *, reference_input: object | None = None) -> dict[str, Any]:
    """Project supplied connector captures; neither transport nor claims are authenticated."""
    data = _mapping(
        document,
        {
            "schema_version",
            "repository",
            "retrieved_at",
            "pull_request",
            "native_reviews",
            "native_threads",
            "workflows",
        },
    )
    if data["schema_version"] != "1.0":
        raise ValueError("unsupported input version")
    repository = _text(data["repository"], r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
    if any(part in {".", ".."} for part in repository.split("/")):
        raise ValueError("invalid repository identity")
    retrieved_at = _text(data["retrieved_at"])
    if datetime.fromisoformat(retrieved_at).utcoffset() is None:
        raise ValueError("retrieval timestamp requires a timezone")
    raw_pr = _mapping(data["pull_request"])
    if not {"number", "url", "state", "merged", "head_sha", "merge_commit_sha", "body"}.issubset(
        raw_pr
    ):
        raise ValueError("missing PR facts")
    number = _positive_id(raw_pr.get("number"))
    pr_url = f"https://github.com/{repository}/pull/{number}"
    if raw_pr.get("url") != pr_url or type(raw_pr.get("merged")) is not bool:
        raise ValueError("invalid PR identity")
    head_sha = cast(str, _sha(raw_pr.get("head_sha")))
    pr = {
        "number": number,
        "url": pr_url,
        "state": _enum(raw_pr.get("state"), {"open", "closed"}),
        "merged": raw_pr["merged"],
        "head_sha": head_sha,
        "merge_commit_sha": _sha(raw_pr.get("merge_commit_sha"), nullable=True),
    }
    body = raw_pr.get("body")
    if body is not None and not isinstance(body, str):
        raise ValueError("invalid PR body")
    records, followups = ([], []) if body is None else _records(body, pr_url, head_sha)
    has_followup_version = any(record["schema_version"] == "2.0" for record in records)
    followup_questions = _link_followups(records, followups)
    questions: list[dict[str, Any]] = []
    if not records:
        questions.append({"code": "LOCATE_STRUCTURED_FEEDBACK", "source": _source(pr_url, "body")})
    for record in records:
        if record["candidate_binding"] != "matched_reported":
            questions.append(
                {
                    "code": "CHECK_CANDIDATE_REFERENCE",
                    "record_id": record["record_id"],
                    "source": record["source"],
                }
            )
        for review in record["reviews"]:
            if review["outcome"] in {"REQUEST_CHANGES", "REJECT", "BLOCKED"}:
                questions.append(
                    {
                        "code": "CHECK_REPORTED_REVIEW_CONCLUSION",
                        "record_id": record["record_id"],
                        "review_id": review["review_id"],
                        "source": review["source"],
                    }
                )
            for finding in review["findings"]:
                if finding["status"] == "open":
                    question: dict[str, Any] = {
                        "code": "INSPECT_REPORTED_OPEN_FINDING",
                        "record_id": record["record_id"],
                        "review_id": review["review_id"],
                        "finding_id": finding["finding_id"],
                        "source": finding["source"],
                    }
                    linked = [
                        dict(followup["source"])
                        for followup in followups
                        if followup["finding_linkage"] == "matched_reported"
                        and followup["finding_ref"]
                        == {
                            "record_id": record["record_id"],
                            "review_id": review["review_id"],
                            "finding_id": finding["finding_id"],
                        }
                    ]
                    if linked:
                        question["followup_sources"] = linked
                    questions.append(question)
    questions.extend(followup_questions)
    workflows = data["workflows"]
    observations: list[dict[str, Any]] = []
    if workflows is not None:
        workflow_data = _mapping(workflows)
        requested = _sha(workflow_data.get("requested_commit_sha"))
        rows = _list(_mapping(workflow_data.get("data")).get("workflow_runs"))
        for index, value in enumerate(rows):
            run = _mapping(value)
            if not {"id", "name", "status", "conclusion"}.issubset(run):
                raise ValueError("missing workflow facts")
            run_id = _positive_id(run.get("id"))
            status = _enum(run.get("status"), RUN_STATUSES)
            conclusion = run.get("conclusion")
            if conclusion is not None:
                conclusion = _enum(conclusion, CONCLUSIONS)
            source = _source(
                f"https://github.com/{repository}/actions/runs/{run_id}",
                f"workflows.data.workflow_runs[{index}]",
            )
            observation = {
                "id": run_id,
                "name": _text(run.get("name")),
                "status": status,
                "conclusion": conclusion,
                "requested_commit_sha": requested,
                "candidate_binding": "query_reference" if requested == head_sha else "mismatched",
                "source": source,
            }
            observations.append(observation)
            code = None
            if requested != head_sha:
                code = "CHECK_CHECK_CANDIDATE_REFERENCE"
            elif status != "completed":
                code = "WAIT_FOR_RECORDED_CHECK"
            elif conclusion in {"failure", "timed_out", "startup_failure"}:
                code = "DIAGNOSE_RECORDED_CHECK_FAILURE"
            elif conclusion != "success":
                code = "CHECK_NONPASS_RESULT_SCOPE"
            if code is not None:
                questions.append({"code": code, "source": source})
    if not observations:
        questions.append({"code": "GET_CHECK_SOURCE", "source": _source(pr_url, "workflows")})
    reference = None
    if reference_input is not None:
        from benchmark_reference import build_reference

        reference = build_reference(reference_input)
    report: dict[str, Any] = {
        "schema_version": "2.0" if has_followup_version else "1.0",
        "measurement": "task_free_pr_feedback",
        "repository": repository,
        "retrieved_at": retrieved_at,
        "pull_request": pr,
        "source_assurance": "supplied_github_records",
        "history_completeness": "unknown",
        "source_atomicity": "unknown",
        "task_id": "not_applicable",
        "actual_model_identity": "unknown",
        "model_score_update_status": "not_implemented",
        "probability_status": "unestimated",
        "method_status": "design_pending",
        "execution_allowed": False,
        "permission_effect": "none",
        "ledger_effect": "none",
        "required_checks_status": "unknown",
        "external_reference": reference,
        "native_reviews": _native_collection(
            data["native_reviews"], "reviews", "native_reviews", pr_url
        ),
        "native_threads": _native_collection(
            data["native_threads"], "review_threads", "native_threads", pr_url
        ),
        "workflow_observations": observations,
        "workflow_collection_status": "not_captured"
        if workflows is None
        else "captured_first_page",
        "structured_feedback_status": (
            "not_captured" if body is None else "reported" if records else "absent"
        ),
        "reported_feedback": records,
        "next_review_questions": questions,
        "coverage": {
            "reported_records": len(records),
            "reported_review_records": sum(len(record["reviews"]) for record in records),
            "reported_finding_records": sum(
                len(review["findings"]) for record in records for review in record["reviews"]
            ),
            "workflow_records": len(observations),
        },
        "limitations": [
            "Captures and coordinator reports are supplied claims, not authenticated originals.",
            "A mutable PR body and an input hash do not establish complete or append-only history.",
            "Empty native captures do not establish absence of machine review.",
            "Native item shapes are not projected; "
            "bodies, authors and reported identities are excluded.",
            "Workflow query references and first pages do not establish required-check coverage.",
            "Resolved, approved, merged and successful checks "
            "do not establish defect truth or model ability.",
            "Questions prepare source and scope checks; "
            "they do not trigger review or authorize actions.",
        ],
    }
    if has_followup_version:
        report["reported_followups"] = followups
        report["coverage"]["reported_followup_records"] = len(followups)
    return report


def _format_text(report: dict[str, Any]) -> str:
    """Render only the normalized projection; never render supplied bodies or names."""
    pr = report["pull_request"]
    counts = report["coverage"]
    lines = [
        "Current facts (supplied claims):",
        f"  PR #{pr['number']}: {pr['state']}; merged={str(pr['merged']).lower()}",
        f"  source={pr['url']}; head={pr['head_sha']}",
        f"  records={counts['reported_records']}; reviews={counts['reported_review_records']}; "
        f"findings={counts['reported_finding_records']}; "
        f"followups={counts.get('reported_followup_records', 0)}",
    ]
    for record in report["reported_feedback"]:
        lines.append(
            f"  record {record['record_id']}: candidate={record['candidate_commit'] or 'unknown'}; "
            f"binding={record['candidate_binding']}"
        )
        for review in record["reviews"]:
            lines.append(
                f"    review {review['review_id']}: {review['outcome']}; role={review['role']}; "
                f"original={review['original_reference_status']}"
            )
            for finding in review["findings"]:
                lines.append(
                    f"      {finding['finding_id']}: {finding['severity']}/{finding['status']}; "
                    f"original={finding['original_reference_status']}"
                )
    for followup in report.get("reported_followups", []):
        ref = followup["finding_ref"]
        lines.append(
            f"  followup {followup['record_id']} -> "
            f"{ref['record_id']}/{ref['review_id']}/{ref['finding_id']}: "
            f"disposition={followup['author_disposition']['decision']}; "
            f"repair={followup['repair']['kind']}; finding={followup['finding_linkage']}; "
            f"recheck={followup['recheck_linkage']}; "
            f"candidate_binding={followup['recheck_candidate_binding']}"
        )
    for run in report["workflow_observations"]:
        lines.append(
            f"  workflow {run['id']}: {run['status']}/{run['conclusion'] or 'unknown'}; "
            f"binding={run['candidate_binding']}"
        )
    lines.extend(
        [
            "Missing / unknown:",
            f"  feedback={report['structured_feedback_status']}; "
            f"workflows={report['workflow_collection_status']}",
            "  history_completeness=unknown; source_atomicity=unknown; "
            "required_checks_status=unknown",
            "  actual_model_identity=unknown; independent_truth=unknown; "
            "independent_recheck=unknown",
        ]
    )
    for field in ("native_reviews", "native_threads"):
        collection = report[field]
        count = collection["records_in_capture"]
        lines.append(
            f"  {field}={collection['collection_status']}; "
            f"records_in_capture={count if count is not None else 'unknown'}; "
            "field_projection=not_projected"
        )
    lines.append("Next source checks (not execution):")
    for question in report["next_review_questions"]:
        source = question["source"]
        lines.append(f"  {question['code']}: {source['url']} @ {source['locator']}")
    if not report["next_review_questions"]:
        lines.append("  none_in_supplied_projection; unknowns_above_remain")
    reference = "not_provided" if report["external_reference"] is None else "separate_unscored"
    lines.extend(
        [
            f"Scope: external_reference={reference}; probability_status=unestimated; "
            "method_status=design_pending; model_score_update_status=not_implemented",
            "execution_allowed=false; permission_effect=none; ledger_effect=none",
            "Use --format json for the complete projection and byte hashes.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    sys.dont_write_bytecode = True
    from benchmark_reference import _reject_constant, _unique_object

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-input", type=Path)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    arguments = parser.parse_args(argv)
    try:
        original = sys.stdin.buffer.read()
        document = json.loads(
            original.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        reference = None
        reference_bytes = None
        if arguments.reference_input is not None:
            reference_bytes = arguments.reference_input.read_bytes()
            reference = json.loads(
                reference_bytes.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
            if reference is None:
                raise ValueError("reference input must be an object")
        report = build_pr_feedback(document, reference_input=reference)
        report["input_sha256"] = hashlib.sha256(original).hexdigest()
        report["executed_tool_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if reference_bytes is not None:
            report["external_reference"]["input_sha256"] = hashlib.sha256(
                reference_bytes
            ).hexdigest()
    except (OSError, ValueError, RecursionError):
        print("pr-feedback: supplied records or reference input are invalid", file=sys.stderr)
        return 2
    if arguments.format == "text":
        print(_format_text(report))
    else:
        print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
