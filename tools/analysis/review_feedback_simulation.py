"""Rehearse synthetic score updates, calibration and feedback without execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from bisect import bisect_right
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

_ASSUMPTIONS = ("assumed", "unknown", "violated")
_CALIBRATION_ASSUMPTIONS = (
    "predictions_fixed_before_outcomes",
    "bins_and_split_predeclared",
    "complete_independent_groups",
    "same_target_and_predictor",
    "no_material_drift",
)
_ROUTING_ASSUMPTIONS = (
    "baseline_continuation",
    "authorization_boundary_preserved",
    "no_material_drift",
)
_THRESHOLDS = ("trigger_below_lower_bound", "max_interval_width", "max_heldout_brier")
_DEPENDENCIES = (
    "benchmark_reference.py",
    "review_detection.py",
    "review_detection_input.py",
    "review_detection_analysis.py",
)


def _envelope(document: object, fields: set[str]) -> dict[str, Any]:
    from review_detection_input import _object

    data = _object(document, fields | {"schema_version", "record_origin"})
    if data["schema_version"] != "1.0" or data["record_origin"] != "synthetic":
        raise ValueError("unsupported schema version or record origin")
    return data


def _scope(value: object) -> dict[str, Any]:
    from review_detection_input import _ID, _object, _pattern

    scope = _object(value, {"profile_id", "profile_revision", "condition_id"})
    for field in scope.values():
        if field is not None:
            _pattern(field, _ID)
    return deepcopy(scope)


def _probability(value: object) -> None:
    if value is None:
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 1
        or not math.isfinite(value)
    ):
        raise ValueError("invalid probability")


def _assumption(value: object) -> None:
    if value not in _ASSUMPTIONS:
        raise ValueError("invalid assumption")


def _block(blockers: list[dict[str, str]], code: str, status: str, locator: str) -> None:
    item = {"code": code, "status": status, "locator": locator}
    if item not in blockers:
        blockers.append(item)


def _unknown_scope(scope: dict[str, Any], blockers: list[dict[str, str]], prefix: str) -> None:
    for field, value in scope.items():
        if value is None:
            _block(blockers, "SCOPE_UNKNOWN", "unknown", f"{prefix}.{field}")


def _base(measurement: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "record_origin": "synthetic",
        "measurement": measurement,
        "target": "review_detection",
        "source_authenticity": "unknown",
        "profile_applicability": "unknown",
        "actual_model_identity": "unknown",
        "statistical_independence": "unknown",
        "observation_admission": "unknown",
        "method_status": "design_pending",
        "probability_status": "unestimated",
        "model_score_update_status": "not_implemented",
        "execution_allowed": False,
        "permission_effect": "none",
        "ledger_effect": "none",
    }


def _snapshot_content(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Ignore only the snapshot label and whole-candidate-array ordering."""
    content = deepcopy(snapshot)
    content.pop("snapshot_id")
    declarations = content["analysis"]["declarations"]
    declarations["candidates"] = {
        candidate["candidate_id"]: candidate for candidate in declarations["candidates"]
    }
    return content


def build_score_update(document: object) -> dict[str, Any]:
    """Recompute a complete synthetic snapshot, retaining prior history and failures."""
    from review_detection_analysis import build_detection_analysis
    from review_detection_input import _ID, _object, _pattern

    data = _envelope(document, {"profile_assignment", "previous", "current"})
    _assumption(data["profile_assignment"])
    reports: dict[str, Any] = {"previous": None}
    snapshots: dict[str, dict[str, Any]] = {}
    blockers: list[dict[str, str]] = []
    if data["profile_assignment"] != "assumed":
        _block(
            blockers,
            "PROFILE_ASSIGNMENT",
            "unknown" if data["profile_assignment"] == "unknown" else "conflict",
            "$.profile_assignment",
        )
    for name in ("previous", "current"):
        if name == "previous" and data[name] is None:
            continue
        snapshot = _object(data[name], {"snapshot_id", "scope", "analysis"})
        _pattern(snapshot["snapshot_id"], _ID)
        scope = _scope(snapshot["scope"])
        _unknown_scope(scope, blockers, f"$.{name}.scope")
        report = build_detection_analysis(snapshot["analysis"])
        snapshots[name] = snapshot
        reports[name] = report
        if report["analysis_status"] == "blocked":
            _block(
                blockers,
                "UPSTREAM_BLOCKED",
                "conflict"
                if any(item["status"] == "conflict" for item in report["blockers"])
                else "unknown",
                f"$.{name}.analysis",
            )

    current = snapshots["current"]
    previous = snapshots.get("previous")
    unchanged = False
    if previous is not None:
        if previous["scope"] != current["scope"]:
            _block(blockers, "SCOPE_MISMATCH", "conflict", "$.current.scope")
        before = previous["analysis"]
        after = current["analysis"]
        for field in ("repository", "admission_package", "window"):
            if before["declarations"][field] != after["declarations"][field]:
                _block(
                    blockers,
                    "COHORT_MISMATCH",
                    "conflict",
                    f"$.current.analysis.declarations.{field}",
                )
        if before["scenario_assumptions"] != after["scenario_assumptions"]:
            _block(
                blockers, "COHORT_MISMATCH", "conflict", "$.current.analysis.scenario_assumptions"
            )
        current_candidates = {
            candidate["candidate_id"]: candidate
            for candidate in after["declarations"]["candidates"]
        }
        for candidate in before["declarations"]["candidates"]:
            if current_candidates.get(candidate["candidate_id"]) != candidate:
                _block(
                    blockers,
                    "HISTORY_CHANGED",
                    "conflict",
                    "$.current.analysis.declarations.candidates",
                )
        selections = {
            selection["related_group"]: selection
            for selection in reports["current"]["declaration_readback"]["group_selections"]
        }
        for selection in reports["previous"]["declaration_readback"]["group_selections"]:
            if selections.get(selection["related_group"]) != selection:
                _block(
                    blockers,
                    "SELECTION_CHANGED",
                    "conflict",
                    "$.current.analysis.declarations.candidates",
                )
        unchanged = _snapshot_content(previous) == _snapshot_content(current)
        if previous["snapshot_id"] == current["snapshot_id"] and not unchanged:
            _block(blockers, "SNAPSHOT_ID_REUSED", "conflict", "$.current.snapshot_id")

    calculation = reports["current"]["synthetic_calculation"]
    status = (
        "blocked"
        if blockers
        else "initial_snapshot"
        if previous is None
        else "unchanged_snapshot"
        if unchanged
        else "append_only_recomputed"
    )
    return {
        **_base("synthetic_score_update"),
        "synthetic_score_update_status": status,
        "scope": deepcopy(current["scope"]),
        "snapshot_id": current["snapshot_id"],
        "previous_analysis": reports["previous"],
        "current_analysis": reports["current"],
        "synthetic_score": None
        if blockers or calculation is None
        else deepcopy(calculation["conditional_result"]),
        "blockers": blockers,
    }


def _bin(prediction: float, edges: list[float]) -> int:
    return min(bisect_right(edges, prediction) - 1, len(edges) - 2)


def _diagnostics(
    predictions: list[float], outcomes: list[int], edges: list[float]
) -> dict[str, Any]:
    buckets: list[list[tuple[float, int]]] = [[] for _ in edges[:-1]]
    for prediction, outcome in zip(predictions, outcomes, strict=True):
        buckets[_bin(prediction, edges)].append((prediction, outcome))
    return {
        "count": len(predictions),
        "brier": math.fsum(
            (prediction - outcome) ** 2
            for prediction, outcome in zip(predictions, outcomes, strict=True)
        )
        / len(predictions),
        "reliability": [
            {
                "count": len(bucket),
                "mean_prediction": math.fsum(prediction for prediction, _ in bucket) / len(bucket)
                if bucket
                else None,
                "event_rate": sum(outcome for _, outcome in bucket) / len(bucket)
                if bucket
                else None,
            }
            for bucket in buckets
        ],
    }


def build_calibration(document: object) -> dict[str, Any]:
    """Fit predeclared synthetic bins and diagnose a separate complete heldout set."""
    from review_detection_input import _ID, _object, _pattern, _time

    data = _envelope(
        document,
        {
            "scope",
            "predictor_revision",
            "fit_fixed_at",
            "bin_edges",
            "scenario_assumptions",
            "fit",
            "heldout",
        },
    )
    scope = _scope(data["scope"])
    revision = data["predictor_revision"]
    if revision is not None:
        _pattern(revision, _ID)
    fixed = _time(data["fit_fixed_at"])
    edges = data["bin_edges"]
    if not isinstance(edges, list) or len(edges) < 2:
        raise ValueError("invalid bin edges")
    for edge in edges:
        _probability(edge)
        if edge is None:
            raise ValueError("invalid bin edge")
    if (
        edges[0] != 0
        or edges[-1] != 1
        or any(left >= right for left, right in zip(edges, edges[1:]))
    ):
        raise ValueError("invalid bin edges")
    assumptions = _object(data["scenario_assumptions"], set(_CALIBRATION_ASSUMPTIONS))
    for value in assumptions.values():
        _assumption(value)
    blockers: list[dict[str, str]] = []
    _unknown_scope(scope, blockers, "$.scope")
    if revision is None:
        _block(blockers, "PREDICTOR_UNKNOWN", "unknown", "$.predictor_revision")
    if fixed is None:
        _block(blockers, "REQUIRED_VALUE", "unknown", "$.fit_fixed_at")
    for field, value in assumptions.items():
        if value != "assumed":
            _block(
                blockers,
                "CALIBRATION_ASSUMPTION",
                "unknown" if value == "unknown" else "conflict",
                f"$.scenario_assumptions.{field}",
            )
    units: set[str] = set()
    groups: set[str] = set()
    for partition in ("fit", "heldout"):
        rows = data[partition]
        if not isinstance(rows, list):
            raise ValueError("invalid calibration rows")
        for i, item in enumerate(rows):
            row = _object(
                item,
                {"unit_id", "related_group", "prediction", "outcome", "predicted_at", "outcome_at"},
            )
            locator = f"$.{partition}[{i}]"
            unit = _pattern(row["unit_id"], _ID)
            if unit in units:
                _block(blockers, "DUPLICATE_UNIT", "conflict", locator + ".unit_id")
            units.add(unit)
            group = row["related_group"]
            if group is not None:
                _pattern(group, _ID)
                if group in groups:
                    _block(blockers, "GROUP_OVERLAP", "conflict", locator + ".related_group")
                groups.add(group)
            _probability(row["prediction"])
            outcome = row["outcome"]
            if outcome is not None and (type(outcome) is not int or outcome not in (0, 1)):
                raise ValueError("invalid outcome")
            predicted, observed = _time(row["predicted_at"]), _time(row["outcome_at"])
            for field in ("related_group", "prediction", "outcome", "predicted_at", "outcome_at"):
                if row[field] is None:
                    _block(blockers, "REQUIRED_VALUE", "unknown", locator + "." + field)
            if predicted is not None and observed is not None and predicted >= observed:
                _block(blockers, "EVENT_ORDER", "conflict", locator + ".outcome_at")
            if fixed is not None:
                if partition == "fit" and observed is not None and observed > fixed:
                    _block(blockers, "EVENT_ORDER", "conflict", locator + ".outcome_at")
                if partition == "heldout" and predicted is not None and predicted <= fixed:
                    _block(blockers, "EVENT_ORDER", "conflict", locator + ".predicted_at")
    if not data["fit"]:
        _block(blockers, "EMPTY_FIT", "unknown", "$.fit")
    if not data["heldout"]:
        _block(blockers, "EMPTY_HELDOUT", "unknown", "$.heldout")
    fit_bins = None
    mapped_predictions = None
    raw_diagnostics = None
    mapped_diagnostics = None
    status = "blocked"
    if all(blocker["code"] == "EMPTY_HELDOUT" for blocker in blockers):
        bins: list[list[int]] = [[] for _ in edges[:-1]]
        for row in data["fit"]:
            bins[_bin(row["prediction"], edges)].append(row["outcome"])
        fit_bins = [
            {
                "lower": lower,
                "upper": upper,
                "count": len(outcomes),
                "positives": sum(outcomes),
                "mapped_probability": sum(outcomes) / len(outcomes) if outcomes else None,
            }
            for lower, upper, outcomes in zip(edges, edges[1:], bins)
        ]
        mapped_predictions = []
        for i, row in enumerate(data["heldout"]):
            prediction = fit_bins[_bin(row["prediction"], edges)]["mapped_probability"]
            mapped_predictions.append({"unit_id": row["unit_id"], "prediction": prediction})
            if prediction is None:
                _block(blockers, "UNSEEN_FIT_BIN", "unknown", f"$.heldout[{i}].prediction")
        if not data["heldout"]:
            _block(blockers, "EMPTY_HELDOUT", "unknown", "$.heldout")
            status = "fit_only"
        else:
            outcomes = [row["outcome"] for row in data["heldout"]]
            raw_diagnostics = _diagnostics(
                [row["prediction"] for row in data["heldout"]], outcomes, edges
            )
            status = "incomplete_mapping" if blockers else "evaluated"
            if not blockers:
                mapped_diagnostics = _diagnostics(
                    [cast(float, row["prediction"]) for row in mapped_predictions], outcomes, edges
                )
    return {
        **_base("synthetic_calibration"),
        "synthetic_calibration_status": status,
        "scope": scope,
        "predictor_revision": revision,
        "fit_fixed_at": data["fit_fixed_at"],
        "bin_edges": deepcopy(edges),
        "scenario_assumptions": deepcopy(assumptions),
        "fit": deepcopy(data["fit"]),
        "heldout": deepcopy(data["heldout"]),
        "fit_bins": fit_bins,
        "mapped_predictions": mapped_predictions,
        "raw_diagnostics": raw_diagnostics,
        "mapped_diagnostics": mapped_diagnostics,
        "blockers": blockers,
    }


def build_feedback_simulation(document: object) -> dict[str, Any]:
    """Return a non-executing recommendation from independently recomputed subpackages."""
    from review_detection_input import _object, _time

    data = _envelope(document, {"score_update", "calibration", "routing_scenario"})
    score = build_score_update(data["score_update"])
    calibration = build_calibration(data["calibration"])
    routing = _object(
        data["routing_scenario"], {"baseline_route", *_ROUTING_ASSUMPTIONS, *_THRESHOLDS}
    )
    if routing["baseline_route"] not in ("AUTO", "ASK", "REVIEW", "BLOCK", "unknown"):
        raise ValueError("invalid baseline route")
    for field in _ROUTING_ASSUMPTIONS:
        _assumption(routing[field])
    for field in _THRESHOLDS:
        _probability(routing[field])
    blockers: list[dict[str, str]] = []
    for name, report in (("score_update", score), ("calibration", calibration)):
        for blocker in report["blockers"]:
            _block(
                blockers, blocker["code"], blocker["status"], f"$.{name}" + blocker["locator"][1:]
            )
    if score["scope"] != calibration["scope"]:
        _block(blockers, "SCOPE_MISMATCH", "conflict", "$.calibration.scope")
    if calibration["predictor_revision"] != score["snapshot_id"]:
        _block(blockers, "PREDICTOR_MISMATCH", "conflict", "$.calibration.predictor_revision")
    estimation_groups: set[str] = set()
    for name in ("previous", "current"):
        snapshot = data["score_update"][name]
        if snapshot is not None:
            estimation_groups.update(
                candidate["related_group"]
                for candidate in snapshot["analysis"]["declarations"]["candidates"]
                if candidate["related_group"] is not None
            )
    for partition in ("fit", "heldout"):
        for i, row in enumerate(data["calibration"][partition]):
            if row["related_group"] is not None and row["related_group"] in estimation_groups:
                _block(
                    blockers,
                    "SPLIT_GROUP_OVERLAP",
                    "conflict",
                    f"$.calibration.{partition}[{i}].related_group",
                )
    end = _time(data["score_update"]["current"]["analysis"]["declarations"]["window"]["t1"])
    for i, row in enumerate(data["calibration"]["fit"]):
        predicted = _time(row["predicted_at"])
        if end is None or predicted is None or end >= predicted:
            _block(
                blockers,
                "ESTIMATION_TIME_OVERLAP",
                "unknown" if end is None or predicted is None else "conflict",
                f"$.calibration.fit[{i}].predicted_at",
            )
    for field in _ROUTING_ASSUMPTIONS:
        if routing[field] != "assumed":
            _block(
                blockers,
                "ROUTING_ASSUMPTION",
                "unknown" if routing[field] == "unknown" else "conflict",
                f"$.routing_scenario.{field}",
            )
    for field in _THRESHOLDS:
        if routing[field] is None:
            _block(blockers, "ROUTING_THRESHOLD_UNKNOWN", "unknown", f"$.routing_scenario.{field}")
    if routing["baseline_route"] == "unknown":
        _block(blockers, "BASELINE_UNKNOWN", "unknown", "$.routing_scenario.baseline_route")
    result = score["synthetic_score"]
    if result is None or result["n"] == 0:
        _block(blockers, "NO_SCORE", "unknown", "$.score_update.current.analysis")
    if calibration["synthetic_calibration_status"] != "evaluated":
        _block(blockers, "CALIBRATION_INCOMPLETE", "unknown", "$.calibration")
    recommendation = "INSUFFICIENT_EVIDENCE"
    if not blockers:
        raw = calibration["raw_diagnostics"]["brier"]
        mapped = calibration["mapped_diagnostics"]["brier"]
        if result["width"] > routing["max_interval_width"]:
            _block(
                blockers, "INTERVAL_TOO_WIDE", "conflict", "$.routing_scenario.max_interval_width"
            )
        if mapped > routing["max_heldout_brier"]:
            _block(
                blockers,
                "HELDOUT_LOSS_TOO_HIGH",
                "conflict",
                "$.routing_scenario.max_heldout_brier",
            )
        if mapped > raw:
            _block(blockers, "HELDOUT_LOSS_WORSENED", "conflict", "$.calibration.heldout")
        if not blockers:
            recommendation = (
                "PREPARE_ADDITIONAL_REVIEW"
                if routing["baseline_route"] not in ("ASK", "BLOCK")
                and result["lower"] < routing["trigger_below_lower_bound"]
                else "KEEP_CURRENT_PROCESS"
            )
    return {
        **_base("synthetic_feedback_simulation"),
        "score_update": score,
        "calibration": calibration,
        "routing_scenario": deepcopy(routing),
        "recommendation": recommendation,
        "blockers": blockers,
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
        report = build_feedback_simulation(document)
        report["input_sha256"] = hashlib.sha256(original).hexdigest()
        script = Path(__file__)
        report["executed_tool_sha256"] = hashlib.sha256(script.read_bytes()).hexdigest()
        report["dependency_sha256"] = {
            name: hashlib.sha256(script.with_name(name).read_bytes()).hexdigest()
            for name in _DEPENDENCIES
        }
    except (OSError, ValueError, RecursionError):
        print("review-feedback-simulation: supplied synthetic scenario is invalid", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
