"""Analyze selected synthetic declarations without admitting real observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, cast

_ASSUMPTIONS = (
    "selection_fixed_before_outcomes",
    "history_and_grouping_complete",
    "independent_truth_and_semantic_matching",
    "review_conditions_comparable",
    "group_outcomes_independent",
    "reports_and_budget_endpoints_complete",
    "single_analysis_after_fixed_window",
)
_OUTCOMES = ("positive_detected", "positive_not_detected", "negative", "unresolved")
_DEPENDENCIES = ("benchmark_reference.py", "review_detection_input.py", "review_detection.py")


def _time(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_detection_analysis(document: object) -> dict[str, Any]:
    """Return conditional synthetic analysis for supplied records, without I/O."""
    from review_detection import VERIFIED_N_MAX, build_detection
    from review_detection_input import build_detection_input

    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "record_origin",
        "declarations",
        "scenario_assumptions",
    }:
        raise ValueError("invalid object fields")
    if document["schema_version"] != "1.0" or document["record_origin"] != "synthetic":
        raise ValueError("unsupported schema version or record origin")
    assumptions = document["scenario_assumptions"]
    if (
        not isinstance(assumptions, dict)
        or set(assumptions) != set(_ASSUMPTIONS)
        or any(value not in ("assumed", "unknown", "violated") for value in assumptions.values())
    ):
        raise ValueError("invalid scenario assumptions")
    readback = build_detection_input(document["declarations"])
    candidates = readback["reported_candidates"]
    checks = readback["condition_checks"]
    blockers: list[dict[str, str]] = []

    def block(code: str, status: str, locator: str) -> None:
        item = {"code": code, "status": status, "locator": locator}
        if item not in blockers:
            blockers.append(item)

    def mechanical(check: dict[str, str]) -> None:
        if check["status"] != "consistent_reported":
            block(check["code"], check["status"], "$.declarations" + check["locator"][1:])

    def order(left: str | None, right: str | None, locator: str) -> None:
        before, after = _time(left), _time(right)
        if before is None or after is None:
            block("EVENT_ORDER", "unknown", locator)
        elif before > after:
            block("EVENT_ORDER", "conflict", locator)

    for name in _ASSUMPTIONS:
        if assumptions[name] != "assumed":
            block(
                "SCENARIO_ASSUMPTION",
                "unknown" if assumptions[name] == "unknown" else "conflict",
                f"$.scenario_assumptions.{name}",
            )
    for check in checks:
        if check["code"] == "WINDOW_DURATION":
            mechanical(check)

    selected: list[dict[str, Any]] = []
    counts = dict.fromkeys((*_OUTCOMES, "outside_window_groups", "unresolved_groups"), 0)
    for selection in readback["group_selections"]:
        group = selection["related_group"]
        if selection["status"] == "no_in_window_candidate":
            counts["outside_window_groups"] += 1
            continue
        if selection["status"] == "unknown":
            counts["unresolved_groups"] += 1
            members = [
                i for i, candidate in enumerate(candidates) if candidate["related_group"] == group
            ]
            location = f"$.declarations.candidates[{members[0]}].related_group"
            block("SELECTION_UNRESOLVED", "unknown", location)
            prefixes = tuple(f"$.candidates[{i}]." for i in members)
            for check in checks:
                if check["code"] in ("GROUP_SELECTION", "OPPORTUNITY_SELECTION") and check[
                    "locator"
                ].startswith(prefixes):
                    mechanical(check)
            continue
        i, candidate = next(
            (i, candidate)
            for i, candidate in enumerate(candidates)
            if candidate["candidate_id"] == selection["candidate_id"]
        )
        j, opportunity = next(
            (j, opportunity)
            for j, opportunity in enumerate(candidate["opportunities"])
            if opportunity["opportunity_id"] == selection["opportunity_id"]
        )
        candidate_location = f"$.candidates[{i}]"
        opportunity_location = f"{candidate_location}.opportunities[{j}]"
        truth, match = opportunity["truth"], opportunity["match"]
        outcome = (
            f"positive_{match}"
            if truth == "positive" and match in ("detected", "not_detected")
            else "negative"
            if truth == "negative"
            else "unresolved"
        )
        counts[outcome] += 1
        selected.append(
            {
                "related_group": group,
                "candidate_id": candidate["candidate_id"],
                "opportunity_id": opportunity["opportunity_id"],
                "reported_outcome": outcome,
            }
        )
        if outcome == "unresolved":
            field = "match" if truth == "positive" else "truth"
            block(
                "OUTCOME_UNRESOLVED", "unknown", f"$.declarations{opportunity_location[1:]}.{field}"
            )

        for check in checks:
            locator = check["locator"]
            candidate_check = (
                locator.startswith(candidate_location + ".refs.")
                or locator
                in (
                    candidate_location + ".entered_at",
                    candidate_location + ".report_fixed_at",
                )
                or locator == candidate_location + ".closed_at"
                and check["code"] != "EVENT_ORDER"
            )
            opportunity_check = locator.startswith(opportunity_location + ".")
            if not candidate_check and not opportunity_check:
                continue
            optional_matching_unknown = (
                truth == "negative"
                and check["status"] == "unknown"
                and (
                    check["code"] == "TRUTH_MATCH"
                    or check["code"] == "EVENT_ORDER"
                    and locator == opportunity_location + ".matched_at"
                    and opportunity["matched_at"] is None
                )
            )
            if not optional_matching_unknown:
                mechanical(check)

        candidate_prefix = "$.declarations" + candidate_location[1:]
        opportunity_prefix = "$.declarations" + opportunity_location[1:]
        for field in ("declared_at", "entered_at", "report_fixed_at", "closed_at"):
            if candidate[field] is None:
                block("REQUIRED_TIME", "unknown", f"{candidate_prefix}.{field}")
        if truth in ("positive", "negative") and opportunity["adjudication_fixed_at"] is None:
            block("REQUIRED_TIME", "unknown", opportunity_prefix + ".adjudication_fixed_at")
        if truth == "positive":
            if opportunity["matching_ref"] is None:
                block("REQUIRED_REFERENCE", "unknown", opportunity_prefix + ".matching_ref")
            if opportunity["matched_at"] is None:
                block("REQUIRED_TIME", "unknown", opportunity_prefix + ".matched_at")
        if truth == "negative":
            order(
                opportunity["adjudication_fixed_at"],
                candidate["closed_at"],
                candidate_prefix + ".closed_at",
            )
        if truth == "positive" or opportunity["matched_at"] is not None:
            order(
                opportunity["matched_at"], candidate["closed_at"], candidate_prefix + ".closed_at"
            )

    n = counts["positive_detected"] + counts["positive_not_detected"]
    if n > VERIFIED_N_MAX:
        block("VERIFIED_DOMAIN_EXCEEDED", "conflict", "$.declarations.candidates")
    calculation = None
    if not blockers:
        calculation = build_detection(
            {
                "schema_version": "1.0",
                "record_origin": "synthetic",
                "n": n,
                "k": counts["positive_detected"],
            }
        )
    return {
        "schema_version": "1.0",
        "measurement": "synthetic_review_detection_analysis",
        "record_origin": "synthetic",
        "source_assurance": "synthetic_supplied_declarations",
        "declaration_readback": readback,
        "scenario_assumptions": deepcopy(cast(dict[str, str], assumptions)),
        "selected_units": selected,
        "reported_selection_counts": counts,
        "blockers": blockers,
        "analysis_status": "blocked" if blockers else "conditional_synthetic",
        "synthetic_calculation": calculation,
        "source_authenticity": "unknown",
        "history_completeness": "unknown",
        "observation_admission": "unknown",
        "statistical_independence": "unknown",
        "actual_model_identity": "unknown",
        "method_status": "design_pending",
        "probability_status": "unestimated",
        "model_score_update_status": "not_implemented",
        "execution_allowed": False,
        "permission_effect": "none",
        "ledger_effect": "none",
    }


def main(argv: list[str] | None = None) -> int:
    sys.dont_write_bytecode = True
    from benchmark_reference import _reject_constant, _unique_object

    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        original = sys.stdin.buffer.read()
        document = json.loads(
            original.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        report = build_detection_analysis(document)
        report["input_sha256"] = hashlib.sha256(original).hexdigest()
        script = Path(__file__)
        report["executed_tool_sha256"] = hashlib.sha256(script.read_bytes()).hexdigest()
        report["dependency_sha256"] = {
            name: hashlib.sha256(script.with_name(name).read_bytes()).hexdigest()
            for name in _DEPENDENCIES
        }
    except (OSError, ValueError, RecursionError):
        print("review-detection-analysis: supplied synthetic records are invalid", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
