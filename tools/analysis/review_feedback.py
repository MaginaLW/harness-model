"""Read committed review feedback and display external references separately."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from copy import deepcopy
from itertools import pairwise
from pathlib import Path
from typing import Any, Sequence


def _source(snapshot: dict[str, Any], path: str, locator: str) -> dict[str, str]:
    blobs = {source["ref"]: source["git_blob"] for source in snapshot["sources"]}
    return {
        "source_commit": snapshot["source_commit"],
        "path": path,
        "git_blob": blobs.get(path, "unknown"),
        "locator": locator,
    }


def _histories(
    reviews: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for review in reviews:
        groups[review["review_id"]].append(review)
    histories: list[dict[str, Any]] = []
    review_histories: list[dict[str, Any]] = []
    for review_id, records in sorted(groups.items()):
        records = sorted(records, key=lambda record: record["revision"])
        revisions = [record["revision"] for record in records]
        group_issues: list[str] = []
        if revisions[0] != 1 or any(after != before + 1 for before, after in pairwise(revisions)):
            group_issues.append("REVISION_GAP")
        if len({record["context_sha256"] for record in records}) > 1:
            group_issues.append("CONTEXT_CHANGED")
        if len({record["review_stage"] for record in records}) > 1:
            group_issues.append("STAGE_CHANGED")
        review_histories.append(
            {
                "review_id": review_id,
                "observed_revisions": revisions,
                "history_issues": group_issues,
                "history_completeness": "unknown",
            }
        )
        findings: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            for finding in record["findings"]:
                findings[finding["finding_id"]].append(
                    {
                        "revision": record["revision"],
                        "outcome": record["outcome"],
                        "context_sha256": record["context_sha256"],
                        "severity": finding["severity"],
                        "status": finding["status"],
                        "resolved_at": finding["resolved_at"],
                        "source": {
                            **record["source"],
                            "locator": (
                                f"review_id={review_id},revision={record['revision']},"
                                f"finding_id={finding['finding_id']}"
                            ),
                        },
                    }
                )
        for finding_id, observations in sorted(findings.items()):
            issues = list(group_issues)
            if len({item["severity"] for item in observations}) > 1:
                issues.append("SEVERITY_CHANGED")
            statuses = [item["status"] for item in observations]
            if "resolved" in statuses and "open" in statuses[statuses.index("resolved") + 1 :]:
                issues.append("STATUS_REOPENED")
            if len(observations) != len(records):
                issues.append("FINDING_NOT_IN_EACH_REVISION")
            histories.append(
                {
                    "review_id": review_id,
                    "finding_id": finding_id,
                    "observations": observations,
                    "observed_first_revision": observations[0]["revision"],
                    "observed_latest_revision": observations[-1]["revision"],
                    "history_issues": issues,
                    "history_completeness": "unknown",
                    "author_disposition": "unknown",
                    "independent_recheck": "unknown",
                    "independent_truth": "not_projected",
                }
            )
    return review_histories, histories


def build_feedback(
    snapshot: dict[str, Any],
    *,
    reference_input: object | None = None,
    task_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Summarize a trusted native feedback snapshot, preserving observations and gaps.

    The CLI constructs this snapshot from Git; it never accepts feedback snapshots
    from input files. Finding histories group records, not independent defects.
    """
    from approval_overhead import LedgerDataError

    if snapshot.get("feedback_projection") is not True:
        raise LedgerDataError("feedback: explicit finding projection is required")
    selected = None
    if task_ids is not None:
        if not task_ids or any(
            not isinstance(item, str) or not re.fullmatch(r"TASK-[0-9]{4,}", item)
            for item in task_ids
        ):
            raise LedgerDataError("feedback: task selection must contain unique valid IDs")
        selected = set(task_ids)
        if len(selected) != len(task_ids):
            raise LedgerDataError("feedback: task selection must contain unique valid IDs")
    known_ids = {task["task_id"] for task in snapshot["tasks"]}
    if selected is not None and not selected.issubset(known_ids):
        raise LedgerDataError("feedback: selected task is absent from the committed snapshot")
    reference = None
    if reference_input is not None:
        from benchmark_reference import build_reference

        reference = build_reference(reference_input)
    rows: list[dict[str, Any]] = []
    for task in snapshot["tasks"]:
        if selected is not None and task["task_id"] not in selected:
            continue
        reviews = deepcopy(task["reviews"])
        for review in reviews:
            if "findings" not in review:
                raise LedgerDataError("feedback: finding projection is missing")
            review["source"] = _source(
                snapshot,
                review["source_ref"],
                f"review_id={review['review_id']},revision={review['revision']}",
            )
            context = review["context"]
            if isinstance(context, dict):
                context["source"] = _source(
                    snapshot,
                    context["source_ref"],
                    f"context_sha256={review['context_sha256']}",
                )
            for link in review["event_links"]:
                link["source"] = _source(
                    snapshot,
                    f".ai/tasks/{task['task_id']}/events.jsonl",
                    f"task_id={task['task_id']},sequence={link['sequence']}",
                )
        review_histories, finding_histories = _histories(reviews)
        rows.append(
            {
                "task_id": task["task_id"],
                "current_state": task["task"]["current_state"],
                "bindings": {
                    field: task["task"].get(field, "unknown")
                    for field in (
                        "repository_id",
                        "base_commit",
                        "subject_commit",
                        "frozen_spec_sha256",
                    )
                },
                "reviews": reviews,
                "review_histories": review_histories,
                "finding_histories": finding_histories,
                "events": deepcopy(task["events"]),
                "verification_attempts": deepcopy(task["verification_attempts"]),
                "evidence": deepcopy(task["evidence"]),
                **{
                    field: task.get(field, "unknown")
                    for field in (
                        "history_completeness",
                        "historical_first_result",
                        "evidence_attempt_linkage",
                    )
                },
            }
        )
    return {
        "schema_version": "1.0",
        "measurement": "review_feedback_readback",
        "source_commit": snapshot["source_commit"],
        "executed_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "snapshot_tool_sha256": snapshot["executed_tool_sha256"],
        "sources": deepcopy(snapshot["sources"]),
        "probability_status": "unestimated",
        "method_status": "design_pending",
        "execution_allowed": False,
        "permission_effect": "none",
        "ledger_effect": "none",
        "task_free_feedback_status": "not_projected",
        "actual_model_identity": "unknown",
        "model_score_update_status": "not_implemented",
        "external_reference": reference,
        "tasks": rows,
        "coverage": {
            "task_records": len(rows),
            "review_records": sum(len(task["reviews"]) for task in rows),
            "finding_revision_records": sum(
                len(review["findings"]) for task in rows for review in task["reviews"]
            ),
            "finding_keys": sum(len(task["finding_histories"]) for task in rows),
        },
        "limitations": [
            *snapshot["limitations"],
            "Finding keys identify task/review/finding records, not independent defects.",
            "First/latest refer only to observed revisions; complete history is unknown.",
            "Resolved records do not establish acceptance, repair, correctness or recheck.",
            "Current task bindings never replace the candidate bindings in review contexts.",
            "Task selection filters output only; the snapshot reads the full Git allowlist.",
            "Task-free PR feedback is not projected by this report; use pr_feedback.py separately.",
            "Actual runtime identity and score updates are not implemented.",
            "External references are displayed separately; no model matching or score mixing.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    sys.dont_write_bytecode = True
    from approval_overhead import LedgerDataError, build_snapshot
    from benchmark_reference import _reject_constant, _unique_object

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--task", action="append", help="Filter output to this committed task ID")
    parser.add_argument("--reference-input", type=Path, help="Optional public benchmark input JSON")
    arguments = parser.parse_args(argv)
    try:
        original = None
        reference_input = None
        if arguments.reference_input is not None:
            original = arguments.reference_input.read_bytes()
            reference_input = json.loads(
                original.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
            if reference_input is None:
                raise ValueError("reference input must be an object")
        try:
            repository = arguments.repository.resolve()
        except RuntimeError as error:
            raise ValueError("repository root could not be resolved") from error
        snapshot = build_snapshot(repository, include_feedback=True)
        report = build_feedback(snapshot, reference_input=reference_input, task_ids=arguments.task)
        if original is not None:
            report["external_reference"]["input_sha256"] = hashlib.sha256(original).hexdigest()
    except (LedgerDataError, OSError, ValueError, RecursionError):
        print("review-feedback: committed source or reference input is invalid", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
