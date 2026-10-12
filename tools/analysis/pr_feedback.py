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


def _records(body: str, pr_url: str, head_sha: str) -> list[dict[str, Any]]:
    from benchmark_reference import _reject_constant, _unique_object

    markers = list(re.finditer(r"<!--\s*(/?aiflow-review-feedback:[^>]*?)\s*-->", body))
    if len(re.findall(r"<!--\s*/?aiflow-review-feedback:", body)) != len(markers):
        raise ValueError("incomplete feedback marker")
    if len(markers) % 2:
        raise ValueError("unpaired feedback marker")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for start, end in zip(markers[::2], markers[1::2]):
        if (
            start.group(1).strip() != "aiflow-review-feedback:v1"
            or end.group(1).strip() != "/aiflow-review-feedback:v1"
        ):
            raise ValueError("unsupported or nested feedback marker")
        text = body[start.end() : end.start()].strip()
        if text.startswith("```"):
            fenced = re.fullmatch(r"```json[ \t]*\r?\n(.*?)\r?\n```", text, re.DOTALL)
            if fenced is None:
                raise ValueError("invalid feedback JSON fence")
            text = fenced.group(1)
        record = _mapping(
            json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant),
            {"schema_version", "record_id", "candidate_commit", "category", "reviews"},
        )
        if record["schema_version"] != "1.0":
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
                "schema_version": "1.0",
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
    return records


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
    records = [] if body is None else _records(body, pr_url, head_sha)
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
                    questions.append(
                        {
                            "code": "INSPECT_REPORTED_OPEN_FINDING",
                            "record_id": record["record_id"],
                            "review_id": review["review_id"],
                            "finding_id": finding["finding_id"],
                            "source": finding["source"],
                        }
                    )
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
    return {
        "schema_version": "1.0",
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


def main(argv: list[str] | None = None) -> int:
    sys.dont_write_bytecode = True
    from benchmark_reference import _reject_constant, _unique_object

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-input", type=Path)
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
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
