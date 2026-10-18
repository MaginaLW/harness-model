"""Independent, hand-calculated calibration cases use only invented records."""

from __future__ import annotations

import builtins
import copy
import datetime
import importlib.util
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "tools/analysis/review_feedback_simulation.py"
ASSUMPTIONS = (
    "predictions_fixed_before_outcomes",
    "bins_and_split_predeclared",
    "complete_independent_groups",
    "same_target_and_predictor",
    "no_material_drift",
)


@pytest.fixture
def simulator(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("review_feedback_simulation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(identifier: str, prediction: Any, outcome: Any, *, heldout: bool = False) -> Any:
    return {
        "unit_id": identifier,
        "related_group": f"group-{identifier}",
        "prediction": prediction,
        "outcome": outcome,
        "predicted_at": "2026-02-05T00:00:00Z" if heldout else "2026-02-02T00:00:00Z",
        "outcome_at": "2026-02-06T00:00:00Z" if heldout else "2026-02-03T00:00:00Z",
    }


def _document() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "record_origin": "synthetic",
        "scope": {
            "profile_id": "invented-profile",
            "profile_revision": "profile-1",
            "condition_id": "invented-condition",
        },
        "predictor_revision": "predictor-1",
        "fit_fixed_at": "2026-02-04T00:00:00Z",
        "bin_edges": [0, 0.5, 1],
        "scenario_assumptions": dict.fromkeys(ASSUMPTIONS, "assumed"),
        "fit": [_row("fit-low", 0.1, 0), _row("fit-high", 0.9, 1)],
        "heldout": [
            _row("heldout-low", 0.2, 0, heldout=True),
            _row("heldout-high", 0.8, 1, heldout=True),
        ],
    }


def _codes(report: dict[str, Any]) -> set[str]:
    return {blocker["code"] for blocker in report["blockers"]}


def _assert_no_calculation(report: dict[str, Any]) -> None:
    assert report["synthetic_calibration_status"] == "blocked"
    for field in ("fit_bins", "mapped_predictions", "raw_diagnostics", "mapped_diagnostics"):
        assert report[field] is None


def test_hand_calculated_improvement_retains_real_unknown_states(simulator: Any) -> None:
    report = simulator.build_calibration(_document())
    assert report["synthetic_calibration_status"] == "evaluated"
    assert report["blockers"] == []
    assert report["fit_bins"] == [
        {"lower": 0, "upper": 0.5, "count": 1, "positives": 0, "mapped_probability": 0},
        {"lower": 0.5, "upper": 1, "count": 1, "positives": 1, "mapped_probability": 1},
    ]
    assert report["mapped_predictions"] == [
        {"unit_id": "heldout-low", "prediction": 0},
        {"unit_id": "heldout-high", "prediction": 1},
    ]
    assert report["raw_diagnostics"]["count"] == 2
    assert report["raw_diagnostics"]["brier"] == pytest.approx(0.04)
    assert report["mapped_diagnostics"] == {
        "count": 2,
        "brier": 0,
        "reliability": [
            {"count": 1, "mean_prediction": 0, "event_rate": 0},
            {"count": 1, "mean_prediction": 1, "event_rate": 1},
        ],
    }
    for field in (
        "source_authenticity",
        "profile_applicability",
        "actual_model_identity",
        "statistical_independence",
        "observation_admission",
    ):
        assert report[field] == "unknown"
    assert report["target"] == "review_detection"
    assert report["measurement"] == "synthetic_calibration"
    assert report["schema_version"] == "1.0"
    assert report["record_origin"] == "synthetic"
    assert report["method_status"] == "design_pending"
    assert report["probability_status"] == "unestimated"
    assert report["model_score_update_status"] == "not_implemented"
    assert report["execution_allowed"] is False
    assert report["permission_effect"] == report["ledger_effect"] == "none"


def test_nonmonotone_mapping_is_not_sorted_and_reliability_rebins_mapped_values(
    simulator: Any,
) -> None:
    document = _document()
    document["fit"][0]["outcome"] = 1
    document["fit"][1]["outcome"] = 0
    document["heldout"][0]["outcome"] = 1
    document["heldout"][1]["outcome"] = 0
    report = simulator.build_calibration(document)
    assert report["synthetic_calibration_status"] == "evaluated"
    assert [item["mapped_probability"] for item in report["fit_bins"]] == [1, 0]
    assert [item["prediction"] for item in report["mapped_predictions"]] == [1, 0]
    assert report["raw_diagnostics"]["brier"] == pytest.approx(0.64)
    assert report["raw_diagnostics"]["reliability"] == [
        {"count": 1, "mean_prediction": 0.2, "event_rate": 1},
        {"count": 1, "mean_prediction": 0.8, "event_rate": 0},
    ]
    assert report["mapped_diagnostics"]["reliability"] == [
        {"count": 1, "mean_prediction": 0, "event_rate": 0},
        {"count": 1, "mean_prediction": 1, "event_rate": 1},
    ]


def test_fractional_empirical_mapping_and_full_heldout_brier_are_hand_calculated(
    simulator: Any,
) -> None:
    document = _document()
    document["fit"] = [
        _row("fit-a", 0.1, 1),
        _row("fit-b", 0.2, 0),
        _row("fit-c", 0.3, 1),
        _row("fit-d", 0.7, 0),
        _row("fit-e", 0.9, 1),
    ]
    document["heldout"] = [
        _row("heldout-a", 0.1, 1, heldout=True),
        _row("heldout-b", 0.4, 0, heldout=True),
        _row("heldout-c", 0.9, 1, heldout=True),
    ]
    report = simulator.build_calibration(document)
    assert [item["count"] for item in report["fit_bins"]] == [3, 2]
    assert [item["positives"] for item in report["fit_bins"]] == [2, 1]
    assert [item["mapped_probability"] for item in report["fit_bins"]] == [2 / 3, 0.5]
    assert report["raw_diagnostics"]["count"] == 3
    assert report["raw_diagnostics"]["brier"] == pytest.approx(49 / 150)
    assert report["mapped_diagnostics"]["brier"] == pytest.approx(29 / 108)
    assert report["mapped_diagnostics"]["reliability"][0] == {
        "count": 0,
        "mean_prediction": None,
        "event_rate": None,
    }
    high = report["mapped_diagnostics"]["reliability"][1]
    assert high["count"] == 3
    assert high["mean_prediction"] == pytest.approx(11 / 18)
    assert high["event_rate"] == pytest.approx(2 / 3)


def test_worsened_heldout_brier_is_reported_without_claiming_guaranteed_improvement(
    simulator: Any,
) -> None:
    document = _document()
    document["fit"][0]["outcome"] = 1
    document["fit"][1]["outcome"] = 0
    document["heldout"][0]["prediction"] = 0.1
    document["heldout"][1]["prediction"] = 0.9
    report = simulator.build_calibration(document)
    assert report["synthetic_calibration_status"] == "evaluated"
    assert report["blockers"] == []
    assert report["raw_diagnostics"]["brier"] == pytest.approx(0.01)
    assert report["mapped_diagnostics"]["brier"] == 1


def test_equal_brier_is_valid_and_no_ece_or_acceptance_is_invented(simulator: Any) -> None:
    document = _document()
    document["bin_edges"] = [0, 1]
    for row in document["fit"] + document["heldout"]:
        row["prediction"] = 0.5
    report = simulator.build_calibration(document)
    assert report["synthetic_calibration_status"] == "evaluated"
    assert report["raw_diagnostics"]["brier"] == report["mapped_diagnostics"]["brier"] == 0.25
    assert set(report["raw_diagnostics"]) == {"count", "brier", "reliability"}
    assert set(report["mapped_diagnostics"]) == {"count", "brier", "reliability"}


def test_zero_internal_edges_and_one_use_left_closed_bins_with_final_one_included(
    simulator: Any,
) -> None:
    document = _document()
    document["bin_edges"] = [0, 0.25, 0.5, 0.75, 1]
    points = [(0, 0), (0.25, 1), (0.5, 0), (0.75, 1), (1, 1)]
    document["fit"] = [_row(f"fit-{i}", p, y) for i, (p, y) in enumerate(points)]
    document["heldout"] = [
        _row(f"heldout-{i}", p, y, heldout=True) for i, (p, y) in enumerate(points)
    ]
    report = simulator.build_calibration(document)
    assert [item["count"] for item in report["fit_bins"]] == [1, 1, 1, 2]
    assert [item["mapped_probability"] for item in report["fit_bins"]] == [0, 1, 0, 1]
    assert [item["prediction"] for item in report["mapped_predictions"]] == [0, 1, 0, 1, 1]
    assert report["mapped_diagnostics"]["brier"] == 0


def test_unused_empty_fit_bin_is_preserved_without_fallback_or_blocking(simulator: Any) -> None:
    document = _document()
    document["bin_edges"] = [0, 0.25, 0.75, 1]
    report = simulator.build_calibration(document)
    assert report["synthetic_calibration_status"] == "evaluated"
    assert report["blockers"] == []
    assert report["fit_bins"][1] == {
        "lower": 0.25,
        "upper": 0.75,
        "count": 0,
        "positives": 0,
        "mapped_probability": None,
    }
    assert report["raw_diagnostics"]["reliability"][1] == {
        "count": 0,
        "mean_prediction": None,
        "event_rate": None,
    }


def test_unseen_fit_bin_keeps_complete_raw_heldout_and_null_mapping_without_subset_metric(
    simulator: Any,
) -> None:
    document = _document()
    document["fit"] = [document["fit"][0]]
    report = simulator.build_calibration(document)
    assert report["synthetic_calibration_status"] == "incomplete_mapping"
    assert _codes(report) == {"UNSEEN_FIT_BIN"}
    assert report["mapped_predictions"] == [
        {"unit_id": "heldout-low", "prediction": 0},
        {"unit_id": "heldout-high", "prediction": None},
    ]
    assert report["raw_diagnostics"]["count"] == 2
    assert report["raw_diagnostics"]["brier"] == pytest.approx(0.04)
    assert report["mapped_diagnostics"] is None
    assert report["fit_bins"][1]["mapped_probability"] is None


@pytest.mark.parametrize("empty_heldout", [False, True])
def test_empty_fit_never_produces_empirical_mapping(simulator: Any, empty_heldout: bool) -> None:
    document = _document()
    document["fit"] = []
    if empty_heldout:
        document["heldout"] = []
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert "EMPTY_FIT" in _codes(report)


def test_empty_heldout_retains_fit_only_and_never_scores_fit_as_heldout(simulator: Any) -> None:
    document = _document()
    document["heldout"] = []
    report = simulator.build_calibration(document)
    assert report["synthetic_calibration_status"] == "fit_only"
    assert _codes(report) == {"EMPTY_HELDOUT"}
    assert len(report["fit_bins"]) == 2
    assert report["mapped_predictions"] == []
    assert report["raw_diagnostics"] is None
    assert report["mapped_diagnostics"] is None


@pytest.mark.parametrize("split", ["fit", "heldout"])
@pytest.mark.parametrize(
    "field", ["related_group", "prediction", "outcome", "predicted_at", "outcome_at"]
)
def test_unknown_row_fields_block_all_calculation_and_preserve_every_input_row(
    simulator: Any, split: str, field: str
) -> None:
    document = _document()
    document[split][0][field] = None
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert "REQUIRED_VALUE" in _codes(report)
    assert report["fit"] == document["fit"]
    assert report["heldout"] == document["heldout"]
    assert len(report["fit"]) == len(report["heldout"]) == 2


@pytest.mark.parametrize("field", ["profile_id", "profile_revision", "condition_id"])
def test_unknown_scope_blocks_calibration(simulator: Any, field: str) -> None:
    document = _document()
    document["scope"][field] = None
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert "SCOPE_UNKNOWN" in _codes(report)


def test_unknown_predictor_version_blocks_calibration(simulator: Any) -> None:
    document = _document()
    document["predictor_revision"] = None
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert "PREDICTOR_UNKNOWN" in _codes(report)


def test_unknown_fit_fixed_time_blocks_even_with_otherwise_ordered_rows(simulator: Any) -> None:
    document = _document()
    document["fit_fixed_at"] = None
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert "REQUIRED_VALUE" in _codes(report)


@pytest.mark.parametrize("field", ASSUMPTIONS)
@pytest.mark.parametrize("value,status", [("unknown", "unknown"), ("violated", "conflict")])
def test_each_unestablished_calibration_assumption_blocks_calculation(
    simulator: Any, field: str, value: str, status: str
) -> None:
    document = _document()
    document["scenario_assumptions"][field] = value
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert {
        "code": "CALIBRATION_ASSUMPTION",
        "status": status,
        "locator": f"$.scenario_assumptions.{field}",
    } in report["blockers"]


@pytest.mark.parametrize("split", ["fit", "heldout"])
@pytest.mark.parametrize(
    "field,code", [("unit_id", "DUPLICATE_UNIT"), ("related_group", "GROUP_OVERLAP")]
)
def test_duplicates_within_one_split_are_conflicts_not_collapsed_rows(
    simulator: Any, split: str, field: str, code: str
) -> None:
    document = _document()
    document[split][1][field] = document[split][0][field]
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert code in _codes(report)
    assert report[split] == document[split]
    assert all(item["status"] == "conflict" for item in report["blockers"] if item["code"] == code)


@pytest.mark.parametrize(
    "field,code", [("unit_id", "DUPLICATE_UNIT"), ("related_group", "GROUP_OVERLAP")]
)
def test_fit_and_heldout_cannot_share_units_or_dependency_groups(
    simulator: Any, field: str, code: str
) -> None:
    document = _document()
    document["heldout"][0][field] = document["fit"][0][field]
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert code in _codes(report)


@pytest.mark.parametrize("split", ["fit", "heldout"])
@pytest.mark.parametrize("offset", ["same", "after"])
def test_each_prediction_strictly_precedes_its_outcome(
    simulator: Any, split: str, offset: str
) -> None:
    document = _document()
    row = document[split][0]
    row["predicted_at"] = row["outcome_at"] if offset == "same" else "2026-02-07T00:00:00Z"
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert "EVENT_ORDER" in _codes(report)


def test_fit_outcome_at_map_fixation_is_allowed(simulator: Any) -> None:
    document = _document()
    document["fit"][0]["outcome_at"] = document["fit_fixed_at"]
    assert simulator.build_calibration(document)["synthetic_calibration_status"] == "evaluated"


def test_fit_outcome_after_map_fixation_is_conflict(simulator: Any) -> None:
    document = _document()
    document["fit"][0]["outcome_at"] = "2026-02-04T00:00:01Z"
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert "EVENT_ORDER" in _codes(report)


@pytest.mark.parametrize("time", ["2026-02-03T00:00:00Z", "2026-02-04T00:00:00Z"])
def test_heldout_prediction_must_follow_map_fixation_strictly(simulator: Any, time: str) -> None:
    document = _document()
    document["heldout"][0]["predicted_at"] = time
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert "EVENT_ORDER" in _codes(report)


def test_all_semantic_deficiencies_are_reported_without_failure_overwrite(simulator: Any) -> None:
    document = _document()
    document["scope"]["profile_id"] = None
    document["predictor_revision"] = None
    document["fit"][0]["prediction"] = None
    document["heldout"][0]["related_group"] = document["fit"][0]["related_group"]
    document["scenario_assumptions"]["no_material_drift"] = "violated"
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert {
        "SCOPE_UNKNOWN",
        "PREDICTOR_UNKNOWN",
        "REQUIRED_VALUE",
        "GROUP_OVERLAP",
        "CALIBRATION_ASSUMPTION",
    } <= _codes(report)
    assert report["heldout"] == document["heldout"]


@pytest.mark.parametrize("target", ["top", "scope", "scenario_assumptions", "fit", "heldout"])
@pytest.mark.parametrize("mutation", ["extra", "missing"])
def test_object_shapes_are_exact(simulator: Any, target: str, mutation: str) -> None:
    document = _document()
    if target == "top":
        item = document
    elif target in {"fit", "heldout"}:
        item = document[target][0]
    else:
        item = document[target]
    if mutation == "extra":
        item["unexpected"] = "synthetic-only"
    else:
        item.pop(next(iter(item)))
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize("field", ["schema_version", "record_origin"])
@pytest.mark.parametrize("value", [None, True, 1, "1", "real", "verified"])
def test_version_and_source_are_fixed_synthetic_envelope(
    simulator: Any, field: str, value: Any
) -> None:
    document = _document()
    document[field] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize("value", ["verified", "yes", True, None, 1, []])
def test_assumptions_do_not_accept_verification_or_truthy_values(
    simulator: Any, value: Any
) -> None:
    document = _document()
    document["scenario_assumptions"]["no_material_drift"] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize("split", ["fit", "heldout"])
@pytest.mark.parametrize(
    "value", [True, False, -0.01, 1.01, "0.5", float("nan"), float("inf"), -float("inf"), {}, []]
)
def test_prediction_rejects_boolean_nonfinite_and_out_of_range_values(
    simulator: Any, split: str, value: Any
) -> None:
    document = _document()
    document[split][0]["prediction"] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize("split", ["fit", "heldout"])
@pytest.mark.parametrize("value", [True, False, 0.0, 1.0, -1, 2, "1", [], {}])
def test_outcomes_are_integer_binary_labels_not_negative_truth_or_probabilities(
    simulator: Any, split: str, value: Any
) -> None:
    document = _document()
    document[split][0]["outcome"] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [0],
        [1],
        [0, 0.5, 0.5, 1],
        [0, 1, 0.5],
        [0.1, 1],
        [0, 0.9],
        [0, True, 1],
        [0, "0.5", 1],
        [0, float("nan"), 1],
        [0, float("inf"), 1],
        [0, -0.1, 1],
        [0, 1.1, 1],
        {"0": 0, "1": 1},
    ],
)
def test_bin_edges_are_explicit_strict_finite_unit_partition(simulator: Any, value: Any) -> None:
    document = _document()
    document["bin_edges"] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize(
    "target", ["top", "scope", "scenario_assumptions", "fit", "heldout", "fit-row", "heldout-row"]
)
@pytest.mark.parametrize("value", [None, "synthetic", 1, True])
def test_all_object_and_array_containers_are_typed(simulator: Any, target: str, value: Any) -> None:
    document: Any = _document()
    if target == "top":
        document = value
    elif target.endswith("-row"):
        document[target.removesuffix("-row")][0] = value
    else:
        document[target] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize("field", ["unit_id", "related_group"])
@pytest.mark.parametrize(
    "value", ["", "has space", "../synthetic", "synthetic/record", True, 1, {}]
)
def test_row_identifiers_use_fixed_id_syntax(simulator: Any, field: str, value: Any) -> None:
    document = _document()
    document["fit"][0][field] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize("field", ["profile_id", "profile_revision", "condition_id"])
@pytest.mark.parametrize("value", ["", "has space", "/absolute", True, 1])
def test_scope_identifiers_are_strict(simulator: Any, field: str, value: Any) -> None:
    document = _document()
    document["scope"][field] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize("value", ["", "has space", "../version", True, 1])
def test_predictor_revision_is_a_strict_identifier(simulator: Any, value: Any) -> None:
    document = _document()
    document["predictor_revision"] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


@pytest.mark.parametrize("field", ["fit_fixed_at", "predicted_at", "outcome_at"])
@pytest.mark.parametrize(
    "value", [True, 1, "2026-02-02", "2026-02-02T00:00:00+01:00", "2026-02-30T00:00:00Z"]
)
def test_times_follow_existing_utc_syntax_and_real_calendar(
    simulator: Any, field: str, value: Any
) -> None:
    document = _document()
    if field == "fit_fixed_at":
        document[field] = value
    else:
        document["fit"][0][field] = value
    with pytest.raises(ValueError):
        simulator.build_calibration(document)


def test_existing_utc_zero_offset_and_fractional_seconds_are_accepted(simulator: Any) -> None:
    document = _document()
    document["fit_fixed_at"] = "2026-02-04T00:00:00+00:00"
    document["fit"][0]["outcome_at"] = "2026-02-03T00:00:00.123456+00:00"
    document["heldout"][0]["predicted_at"] = "2026-02-05T00:00:00.123456Z"
    assert simulator.build_calibration(document)["synthetic_calibration_status"] == "evaluated"


def test_mapped_rows_preserve_heldout_order_and_row_order_cannot_change_diagnostics(
    simulator: Any,
) -> None:
    document = _document()
    before = simulator.build_calibration(document)
    document["fit"].reverse()
    document["heldout"].reverse()
    after = simulator.build_calibration(document)
    assert after["mapped_predictions"] == list(reversed(before["mapped_predictions"]))
    for field in ("fit_bins", "raw_diagnostics", "mapped_diagnostics"):
        assert after[field] == before[field]


def test_empty_heldout_does_not_hide_other_semantic_blockers_or_keep_invalid_fit(
    simulator: Any,
) -> None:
    document = _document()
    document["heldout"] = []
    document["fit"][0]["outcome"] = None
    report = simulator.build_calibration(document)
    _assert_no_calculation(report)
    assert {"REQUIRED_VALUE", "EMPTY_HELDOUT"} <= _codes(report)


@pytest.mark.parametrize("field", ["scope", "bin_edges", "scenario_assumptions", "fit", "heldout"])
def test_output_mutation_cannot_change_input_and_output_records_are_independent(
    simulator: Any, field: str
) -> None:
    document = _document()
    original = copy.deepcopy(document)
    report = simulator.build_calibration(document)
    assert document == original
    assert report[field] == document[field]
    assert report[field] is not document[field]
    report[field].clear()
    assert document == original
    assert simulator.build_calibration(document)["synthetic_calibration_status"] == "evaluated"


def test_input_mutation_after_call_cannot_rewrite_report(simulator: Any) -> None:
    document = _document()
    report = simulator.build_calibration(document)
    snapshot = copy.deepcopy(report)
    document["fit"][0]["outcome"] = 1
    document["heldout"][0]["outcome"] = 1
    document["scope"]["profile_id"] = "changed"
    document["bin_edges"].append(2)
    document["scenario_assumptions"]["no_material_drift"] = "violated"
    assert report == snapshot


def test_pure_calibration_performs_no_file_network_process_or_clock_work(
    simulator: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = _document()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("synthetic pure calibration attempted an external effect")

    class NoClock(datetime.datetime):
        now = classmethod(forbidden)
        utcnow = classmethod(forbidden)
        today = classmethod(forbidden)

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(Path, "read_text", forbidden)
        guard.setattr(Path, "read_bytes", forbidden)
        guard.setattr(Path, "write_text", forbidden)
        guard.setattr(Path, "write_bytes", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(time, "time", forbidden)
        guard.setattr(time, "monotonic", forbidden)
        guard.setattr(time, "perf_counter", forbidden)
        guard.setattr("review_detection_input.datetime", NoClock)
        report = simulator.build_calibration(document)
    assert report["synthetic_calibration_status"] == "evaluated"
