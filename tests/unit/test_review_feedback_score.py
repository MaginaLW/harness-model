"""Synthetic score and routing checks use invented records, without real admission."""

from __future__ import annotations

import builtins
import copy
import hashlib
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "tools/analysis/review_feedback_simulation.py"
EXAMPLE = PROJECT_ROOT / "docs/operations/examples/review-feedback-simulation/synthetic.json"
DEPENDENCIES = (
    "benchmark_reference.py",
    "review_detection.py",
    "review_detection_input.py",
    "review_detection_analysis.py",
)
PRIVATE_MARKER = "PRIVATE_SYNTHETIC_FEEDBACK_DO_NOT_ECHO"
ERROR = b"review-feedback-simulation: supplied synthetic scenario is invalid\n"


@pytest.fixture
def simulator(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    for name in DEPENDENCIES:
        importlib.import_module(Path(name).stem)
    spec = importlib.util.spec_from_file_location("review_feedback_simulation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _document() -> dict[str, Any]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _candidates(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return snapshot["analysis"]["declarations"]["candidates"]


def _codes(report: dict[str, Any]) -> set[str]:
    for blocker in report["blockers"]:
        assert set(blocker) == {"code", "status", "locator"}
        assert blocker["status"] in ("unknown", "conflict")
        assert blocker["locator"].startswith("$")
    return {blocker["code"] for blocker in report["blockers"]}


def _boundary(report: dict[str, Any], measurement: str) -> None:
    assert report["schema_version"] == "1.0"
    assert report["record_origin"] == "synthetic"
    assert report["target"] == "review_detection"
    assert report["measurement"] == measurement
    for key in (
        "source_authenticity",
        "profile_applicability",
        "actual_model_identity",
        "statistical_independence",
        "observation_admission",
    ):
        assert report[key] == "unknown"
    assert report["method_status"] == "design_pending"
    assert report["probability_status"] == "unestimated"
    assert report["model_score_update_status"] == "not_implemented"
    assert report["execution_allowed"] is False
    assert report["permission_effect"] == report["ledger_effect"] == "none"


def test_score_recomputes_full_current_snapshot_instead_of_accumulating(simulator: Any) -> None:
    score = _document()["score_update"]
    report = simulator.build_score_update(score)

    assert report["synthetic_score_update_status"] == "append_only_recomputed"
    assert report["blockers"] == []
    assert report["previous_analysis"]["synthetic_calculation"]["conditional_result"]["n"] == 2
    assert report["synthetic_score"]["n"] == 3
    assert report["synthetic_score"]["k"] == 1
    assert report["synthetic_score"]["proportion"] == pytest.approx(1 / 3)
    assert (
        report["synthetic_score"]
        == report["current_analysis"]["synthetic_calculation"]["conditional_result"]
    )
    _boundary(report, "synthetic_score_update")


@pytest.mark.parametrize("reorder", [False, True])
@pytest.mark.parametrize("same_identifier", [False, True])
def test_same_content_is_unchanged_with_new_id_or_candidate_array_order(
    simulator: Any, reorder: bool, same_identifier: bool
) -> None:
    score = _document()["score_update"]
    score["previous"] = copy.deepcopy(score["current"])
    if not same_identifier:
        score["current"]["snapshot_id"] = "same-content-new-id"
    if reorder:
        _candidates(score["current"]).reverse()

    report = simulator.build_score_update(score)

    assert report["synthetic_score_update_status"] == "unchanged_snapshot"
    assert report["synthetic_score"]["n"] == 3
    assert report["blockers"] == []
    assert simulator.build_score_update(score) == report


def test_initial_snapshot_reports_no_previous_analysis(simulator: Any) -> None:
    score = _document()["score_update"]
    score["previous"] = None

    report = simulator.build_score_update(score)

    assert report["synthetic_score_update_status"] == "initial_snapshot"
    assert report["previous_analysis"] is None
    assert report["synthetic_score"]["n"] == 3


@pytest.mark.parametrize("change", ["delete_failure", "outcome", "reference", "opportunity_order"])
def test_old_history_cannot_be_deleted_or_rewritten(simulator: Any, change: str) -> None:
    score = _document()["score_update"]
    failed = _candidates(score["current"])[1]
    if change == "delete_failure":
        _candidates(score["current"]).pop(1)
    elif change == "outcome":
        failed["opportunities"][0]["match"] = "detected"
    elif change == "reference":
        failed["refs"]["report"]["locator"] = "replacement-failure-reference"
    else:
        extra = copy.deepcopy(failed["opportunities"][0])
        extra["opportunity_id"] = "another-failed-opportunity"
        extra["object_ref"]["path"] = "docs/synthetic-z.md"
        for snapshot in (score["previous"], score["current"]):
            _candidates(snapshot)[1]["opportunities"].append(copy.deepcopy(extra))
        failed["opportunities"].reverse()

    report = simulator.build_score_update(score)

    assert report["synthetic_score_update_status"] == "blocked"
    assert report["synthetic_score"] is None
    assert "HISTORY_CHANGED" in _codes(report)


def test_snapshot_id_cannot_bind_different_content(simulator: Any) -> None:
    score = _document()["score_update"]
    score["current"]["snapshot_id"] = score["previous"]["snapshot_id"]
    report = simulator.build_score_update(score)

    assert "SNAPSHOT_ID_REUSED" in _codes(report)
    assert report["synthetic_score"] is None


def test_later_related_retry_does_not_add_an_independent_unit(simulator: Any) -> None:
    score = _document()["score_update"]
    retry = copy.deepcopy(_candidates(score["current"])[0])
    retry.update(
        candidate_id="candidate-retry",
        declared_at="2026-01-01T00:30:00Z",
        entered_at="2026-01-01T01:00:00Z",
    )
    retry["opportunities"][0]["opportunity_id"] = "opportunity-retry"
    _candidates(score["current"]).append(retry)
    report = simulator.build_score_update(score)

    assert report["synthetic_score_update_status"] == "append_only_recomputed"
    assert report["synthetic_score"]["n"] == 3
    assert report["synthetic_score"]["k"] == 1
    assert report["blockers"] == []


def test_new_earlier_related_candidate_cannot_replace_old_selection(simulator: Any) -> None:
    score = _document()["score_update"]
    for snapshot in (score["previous"], score["current"]):
        _candidates(snapshot)[0]["entered_at"] = "2026-01-02T00:00:00Z"
    earlier = copy.deepcopy(_candidates(score["current"])[0])
    earlier.update(candidate_id="candidate-earlier", entered_at="2026-01-01T00:00:00Z")
    earlier["opportunities"][0]["opportunity_id"] = "opportunity-earlier"
    _candidates(score["current"]).append(earlier)
    report = simulator.build_score_update(score)

    assert report["synthetic_score"] is None
    assert "SELECTION_CHANGED" in _codes(report)


@pytest.mark.parametrize("state", ["unknown", "violated"])
def test_assignment_blocks_even_an_otherwise_unchanged_snapshot(simulator: Any, state: str) -> None:
    score = _document()["score_update"]
    score["previous"] = copy.deepcopy(score["current"])
    score["profile_assignment"] = state
    report = simulator.build_score_update(score)

    assert report["synthetic_score_update_status"] == "blocked"
    assert report["synthetic_score"] is None
    assert "PROFILE_ASSIGNMENT" in _codes(report)


@pytest.mark.parametrize("field", ["profile_id", "profile_revision", "condition_id"])
def test_unknown_or_different_scope_prevents_update(simulator: Any, field: str) -> None:
    score = _document()["score_update"]
    score["current"]["scope"][field] = None
    report = simulator.build_score_update(score)
    assert {"SCOPE_UNKNOWN", "SCOPE_MISMATCH"} <= _codes(report)
    assert report["synthetic_score"] is None

    score["current"]["scope"][field] = "different-synthetic-scope"
    report = simulator.build_score_update(score)
    assert "SCOPE_MISMATCH" in _codes(report)
    assert report["synthetic_score"] is None


@pytest.mark.parametrize("field", ["repository", "window", "assumptions"])
def test_snapshots_must_share_declared_cohort_and_assumptions(simulator: Any, field: str) -> None:
    score = _document()["score_update"]
    analysis = score["current"]["analysis"]
    if field == "window":
        analysis["declarations"]["window"]["t1"] = "2026-01-30T00:00:00Z"
    elif field == "assumptions":
        analysis["scenario_assumptions"]["review_conditions_comparable"] = "unknown"
    else:
        # Keep every supplied PR reference valid under the changed repository.
        score["current"]["analysis"] = json.loads(
            json.dumps(analysis).replace("synthetic/project", "synthetic/other")
        )
    report = simulator.build_score_update(score)

    assert "COHORT_MISMATCH" in _codes(report)
    assert report["synthetic_score"] is None


@pytest.mark.parametrize("snapshot", ["previous", "current"])
def test_critical_upstream_unknown_is_retained_and_never_uses_old_score(
    simulator: Any, snapshot: str
) -> None:
    score = _document()["score_update"]
    _candidates(score[snapshot])[0]["opportunities"][0]["match"] = "unknown"
    report = simulator.build_score_update(score)

    assert report["synthetic_score_update_status"] == "blocked"
    assert report["synthetic_score"] is None
    assert "UPSTREAM_BLOCKED" in _codes(report)
    assert report[f"{snapshot}_analysis"]["blockers"]


@pytest.mark.parametrize("count", [104, 105])
def test_update_retains_record_analysis_denominator_cap(simulator: Any, count: int) -> None:
    score = _document()["score_update"]
    score["previous"] = None
    base = _candidates(score["current"])[0]
    candidates = []
    for index in range(count):
        candidate = copy.deepcopy(base)
        candidate["candidate_id"] = f"candidate-{index}"
        candidate["related_group"] = f"group-{index}"
        candidate["opportunities"][0]["opportunity_id"] = f"opportunity-{index}"
        candidates.append(candidate)
    score["current"]["analysis"]["declarations"]["candidates"] = candidates
    report = simulator.build_score_update(score)

    if count == 104:
        assert report["synthetic_score"]["n"] == 104
        assert report["synthetic_score"]["k"] == 104
        assert report["blockers"] == []
    else:
        assert report["synthetic_score"] is None
        assert "UPSTREAM_BLOCKED" in _codes(report)


def test_simulation_recomputes_both_packets_and_preserves_real_unknowns(simulator: Any) -> None:
    document = _document()
    report = simulator.build_feedback_simulation(document)

    assert report["score_update"] == simulator.build_score_update(document["score_update"])
    assert report["calibration"] == simulator.build_calibration(document["calibration"])
    assert report["recommendation"] == "PREPARE_ADDITIONAL_REVIEW"
    assert report["routing_scenario"] == document["routing_scenario"]
    assert report["blockers"] == []
    _boundary(report, "synthetic_feedback_simulation")
    _boundary(report["calibration"], "synthetic_calibration")
    for key in ("effective_route", "native_route", "approval", "dispatch", "scheduled_review"):
        assert key not in report


@pytest.mark.parametrize("baseline", ["ASK", "BLOCK", "AUTO", "REVIEW"])
def test_route_never_overrides_ask_or_block(simulator: Any, baseline: str) -> None:
    document = _document()
    document["routing_scenario"]["baseline_route"] = baseline
    report = simulator.build_feedback_simulation(document)

    assert report["recommendation"] == (
        "KEEP_CURRENT_PROCESS" if baseline in ("ASK", "BLOCK") else "PREPARE_ADDITIONAL_REVIEW"
    )
    assert report["routing_scenario"]["baseline_route"] == baseline
    assert report["execution_allowed"] is False


@pytest.mark.parametrize("direction", ["below", "equal", "above"])
def test_lower_bound_trigger_is_strict_and_uses_original_interval(
    simulator: Any, direction: str
) -> None:
    document = _document()
    score = simulator.build_score_update(document["score_update"])["synthetic_score"]
    floor = score["lower"] + {"below": -0.001, "equal": 0, "above": 0.001}[direction]
    document["routing_scenario"]["trigger_below_lower_bound"] = floor
    report = simulator.build_feedback_simulation(document)

    assert report["recommendation"] == (
        "PREPARE_ADDITIONAL_REVIEW" if direction == "above" else "KEEP_CURRENT_PROCESS"
    )
    assert report["score_update"]["synthetic_score"] == score


@pytest.mark.parametrize("case", ["width_equal", "width_less", "loss_equal", "loss_less"])
def test_quality_limits_accept_equality_and_reject_strict_excess(simulator: Any, case: str) -> None:
    document = _document()
    if case.startswith("width"):
        width = simulator.build_score_update(document["score_update"])["synthetic_score"]["width"]
        document["routing_scenario"]["max_interval_width"] = width - (
            0.001 if case.endswith("less") else 0
        )
        expected_code = "INTERVAL_TOO_WIDE"
    else:
        # Fit q=.5 in both bins; heldout p=.5 gives raw=mapped Brier=.25.
        for index, row in enumerate(document["calibration"]["fit"]):
            row["outcome"] = index % 2
        for row in document["calibration"]["heldout"]:
            row["prediction"] = 0.5
        document["routing_scenario"]["max_heldout_brier"] = 0.249 if case.endswith("less") else 0.25
        expected_code = "HELDOUT_LOSS_TOO_HIGH"
    report = simulator.build_feedback_simulation(document)

    if case.endswith("less"):
        assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
        assert expected_code in _codes(report)
    else:
        assert report["recommendation"] == "PREPARE_ADDITIONAL_REVIEW"
        assert expected_code not in _codes(report)


def test_worse_mapping_blocks_even_when_explicit_max_loss_passes(simulator: Any) -> None:
    document = _document()
    for row in document["calibration"]["fit"]:
        row["outcome"] = 1 - row["outcome"]
    document["routing_scenario"]["max_heldout_brier"] = 1
    report = simulator.build_feedback_simulation(document)

    assert report["calibration"]["synthetic_calibration_status"] == "evaluated"
    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert "HELDOUT_LOSS_WORSENED" in _codes(report)


@pytest.mark.parametrize(
    "field", ["baseline_continuation", "authorization_boundary_preserved", "no_material_drift"]
)
@pytest.mark.parametrize("state", ["unknown", "violated"])
def test_route_assumption_gaps_block_without_authorizing_any_action(
    simulator: Any, field: str, state: str
) -> None:
    document = _document()
    document["routing_scenario"][field] = state
    report = simulator.build_feedback_simulation(document)

    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert "ROUTING_ASSUMPTION" in _codes(report)
    assert report["permission_effect"] == "none"


@pytest.mark.parametrize(
    "field", ["trigger_below_lower_bound", "max_interval_width", "max_heldout_brier"]
)
def test_no_default_route_threshold_is_invented(simulator: Any, field: str) -> None:
    document = _document()
    document["routing_scenario"][field] = None
    report = simulator.build_feedback_simulation(document)

    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert "ROUTING_THRESHOLD_UNKNOWN" in _codes(report)


def test_unknown_baseline_does_not_infer_native_route(simulator: Any) -> None:
    document = _document()
    document["routing_scenario"]["baseline_route"] = "unknown"
    report = simulator.build_feedback_simulation(document)
    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert "BASELINE_UNKNOWN" in _codes(report)


@pytest.mark.parametrize(
    "case", ["scope", "predictor", "empty_heldout", "upstream", "no_positives"]
)
def test_incomplete_subpackets_never_route_or_fall_back_to_prior_score(
    simulator: Any, case: str
) -> None:
    document = _document()
    if case == "scope":
        document["calibration"]["scope"]["profile_revision"] = "other-profile-revision"
        code = "SCOPE_MISMATCH"
    elif case == "predictor":
        document["calibration"]["predictor_revision"] = "other-score-revision"
        code = "PREDICTOR_MISMATCH"
    elif case == "empty_heldout":
        document["calibration"]["heldout"] = []
        code = "CALIBRATION_INCOMPLETE"
    elif case == "upstream":
        document["score_update"]["profile_assignment"] = "unknown"
        code = "PROFILE_ASSIGNMENT"
    else:
        document["score_update"]["previous"] = None
        for candidate in _candidates(document["score_update"]["current"]):
            candidate["opportunities"][0].update(
                truth="negative", match="unknown", matching_ref=None, matched_at=None
            )
        code = "NO_SCORE"
    report = simulator.build_feedback_simulation(document)

    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert code in _codes(report)
    if case == "upstream":
        assert any(
            blocker["code"] == code and blocker["locator"].startswith("$.score_update.")
            for blocker in report["blockers"]
        )
    elif case == "no_positives":
        empty_score = report["score_update"]["synthetic_score"]
        assert empty_score["n"] == empty_score["k"] == 0
        assert all(
            empty_score[field] is None
            for field in ("proportion", "lower", "upper", "width", "precision_met")
        )


def test_all_subpacket_and_routing_reasons_are_retained_with_source_locators(
    simulator: Any,
) -> None:
    document = _document()
    document["score_update"]["profile_assignment"] = "violated"
    document["calibration"]["heldout"][0]["prediction"] = None
    document["routing_scenario"]["baseline_route"] = "unknown"
    document["routing_scenario"]["authorization_boundary_preserved"] = "unknown"
    document["routing_scenario"]["max_interval_width"] = None
    report = simulator.build_feedback_simulation(document)

    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert {
        "PROFILE_ASSIGNMENT",
        "REQUIRED_VALUE",
        "BASELINE_UNKNOWN",
        "ROUTING_ASSUMPTION",
        "ROUTING_THRESHOLD_UNKNOWN",
        "NO_SCORE",
        "CALIBRATION_INCOMPLETE",
    } <= _codes(report)
    for name in ("score_update", "calibration"):
        for blocker in report[name]["blockers"]:
            assert blocker | {"locator": f"$.{name}" + blocker["locator"][1:]} in report["blockers"]


@pytest.mark.parametrize("partition", ["fit", "heldout"])
@pytest.mark.parametrize("selection", ["counted", "negative_group", "outside_window"])
def test_all_declared_score_groups_are_isolated_from_calibration(
    simulator: Any, partition: str, selection: str
) -> None:
    document = _document()
    current = document["score_update"]["current"]
    if selection == "counted":
        group = _candidates(current)[0]["related_group"]
    else:
        extra = copy.deepcopy(_candidates(current)[0])
        extra.update(candidate_id="unused-candidate", related_group="unused-score-group")
        extra["opportunities"][0]["opportunity_id"] = "unused-opportunity"
        if selection == "outside_window":
            extra.update(
                declared_at="2026-02-01T00:00:00Z",
                entered_at="2026-02-02T00:00:00Z",
                report_fixed_at=None,
                closed_at=None,
                opportunities=[],
            )
        else:
            # This group is declared but excluded from the positive denominator.
            extra["opportunities"][0].update(
                truth="negative", match="unknown", matching_ref=None, matched_at=None
            )
        _candidates(current).append(extra)
        group = extra["related_group"]
    document["calibration"][partition][0]["related_group"] = group
    report = simulator.build_feedback_simulation(document)

    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert "SPLIT_GROUP_OVERLAP" in _codes(report)


@pytest.mark.parametrize("predicted_at", ["2026-01-31T00:00:00Z", "2026-01-30T23:59:59Z"])
def test_fit_predictions_must_follow_estimation_window_strictly(
    simulator: Any, predicted_at: str
) -> None:
    document = _document()
    document["calibration"]["fit"][0]["predicted_at"] = predicted_at
    report = simulator.build_feedback_simulation(document)

    assert report["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert "ESTIMATION_TIME_OVERLAP" in _codes(report)


@pytest.mark.parametrize("builder", ["build_score_update", "build_feedback_simulation"])
@pytest.mark.parametrize(
    "case", ["list", "extra", "missing", "version", "real", "captured", "bool_origin"]
)
def test_envelope_shapes_and_real_material_labels_are_rejected(
    simulator: Any, builder: str, case: str
) -> None:
    document: Any = _document()
    if builder == "build_score_update":
        document = document["score_update"]
    if case == "list":
        document = []
    elif case == "extra":
        document["execution_allowed"] = True
    elif case == "missing":
        del document["record_origin"]
    elif case == "version":
        document["schema_version"] = 1
    else:
        document["record_origin"] = {"real": "real", "captured": "captured"}.get(case, True)
    with pytest.raises(ValueError):
        getattr(simulator, builder)(document)


@pytest.mark.parametrize(
    "case",
    [
        "missing_snapshot",
        "extra_snapshot",
        "bad_id",
        "bad_scope",
        "scope_extra",
        "profile_verified",
        "profile_bool",
        "upstream_report",
        "unsupported_admission",
    ],
)
def test_score_nested_shapes_are_strict(simulator: Any, case: str) -> None:
    score = _document()["score_update"]
    if case == "missing_snapshot":
        del score["current"]["snapshot_id"]
    elif case == "extra_snapshot":
        score["current"]["score"] = 1
    elif case == "bad_id":
        score["current"]["snapshot_id"] = "not a valid identifier"
    elif case == "bad_scope":
        score["current"]["scope"]["profile_id"] = True
    elif case == "scope_extra":
        score["current"]["scope"]["verified"] = True
    elif case in ("profile_verified", "profile_bool"):
        score["profile_assignment"] = "verified" if case.endswith("verified") else True
    elif case == "upstream_report":
        score["current"]["analysis"] = simulator.build_score_update(score)["current_analysis"]
    else:
        score["current"]["analysis"]["declarations"]["admission_package"] = "unsupported-package"
    with pytest.raises(ValueError):
        simulator.build_score_update(score)


@pytest.mark.parametrize(
    "field", ["trigger_below_lower_bound", "max_interval_width", "max_heldout_brier"]
)
@pytest.mark.parametrize("value", [True, -0.1, 1.1, float("nan"), float("inf"), "0.5", []])
def test_route_numbers_are_finite_probabilities_without_bool_coercion(
    simulator: Any, field: str, value: Any
) -> None:
    document = _document()
    document["routing_scenario"][field] = value
    with pytest.raises(ValueError):
        simulator.build_feedback_simulation(document)


@pytest.mark.parametrize(
    "case", ["missing", "extra", "route", "assumption", "assumption_bool", "report_instead"]
)
def test_route_shape_enums_and_raw_packet_requirement_are_strict(simulator: Any, case: str) -> None:
    document = _document()
    if case == "missing":
        del document["routing_scenario"]["max_interval_width"]
    elif case == "extra":
        document["routing_scenario"]["execution_allowed"] = True
    elif case == "route":
        document["routing_scenario"]["baseline_route"] = "APPROVE"
    elif case == "assumption":
        document["routing_scenario"]["authorization_boundary_preserved"] = "verified"
    elif case == "assumption_bool":
        document["routing_scenario"]["no_material_drift"] = True
    else:
        document["score_update"] = simulator.build_score_update(document["score_update"])
    with pytest.raises(ValueError):
        simulator.build_feedback_simulation(document)


def _deny_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Synthetic feedback attempted an external effect.")

    for module, names in (
        (socket, ("socket", "create_connection", "getaddrinfo")),
        (subprocess, ("Popen", "run", "call", "check_call", "check_output")),
        (os, ("open", "system", "popen", "mkdir", "remove", "unlink", "rename", "replace")),
        (Path, ("open", "read_bytes", "read_text", "write_bytes", "write_text", "mkdir")),
        (builtins, ("open",)),
        (io, ("open",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, denied)


def test_pure_builders_have_no_effects_and_outputs_do_not_alias_inputs_or_each_other(
    simulator: Any,
) -> None:
    document = _document()
    original = copy.deepcopy(document)
    with pytest.MonkeyPatch.context() as guard:
        _deny_effects(guard)
        score = simulator.build_score_update(document["score_update"])
        report = simulator.build_feedback_simulation(document)
    assert document == original
    score["synthetic_score"]["n"] = 999
    assert score["current_analysis"]["synthetic_calculation"]["conditional_result"]["n"] == 3
    report["score_update"]["scope"]["condition_id"] = "changed"
    report["calibration"]["fit"][0]["outcome"] = 1
    report["routing_scenario"]["baseline_route"] = "AUTO"
    report["score_update"]["current_analysis"]["declaration_readback"]["reported_candidates"][0][
        "candidate_id"
    ] = "changed"
    assert document == original
    assert simulator.build_feedback_simulation(document)["recommendation"] == (
        "PREPARE_ADDITIONAL_REVIEW"
    )


def _cli(
    payload: bytes, cwd: Path | None = None, encoding: str = "ascii"
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = encoding
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT)],
        input=payload,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=environment,
        timeout=15,
    )


@pytest.mark.parametrize("encoding", ["ascii", "gbk"])
@pytest.mark.parametrize("blocked", [False, True])
def test_cli_ascii_unicode_and_original_bytes_and_all_sources_are_bound(
    simulator: Any, tmp_path: Path, encoding: str, blocked: bool
) -> None:
    document = _document()
    _candidates(document["score_update"]["current"])[2]["refs"]["report"]["locator"] = (
        "合成 😀 材料"
    )
    if blocked:
        document["routing_scenario"]["no_material_drift"] = "unknown"
    payload = (" \n" + json.dumps(document, ensure_ascii=False) + "\n").encode("utf-8")
    sources = {
        path: path.read_bytes() for path in [SCRIPT, *(SCRIPT.parent / n for n in DEPENDENCIES)]
    }
    result = _cli(payload, tmp_path, encoding)

    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout.isascii()
    report = json.loads(result.stdout)
    assert report.pop("input_sha256") == hashlib.sha256(payload).hexdigest()
    assert report.pop("executed_tool_sha256") == hashlib.sha256(sources[SCRIPT]).hexdigest()
    assert report.pop("dependency_sha256") == {
        name: hashlib.sha256(sources[SCRIPT.parent / name]).hexdigest() for name in DEPENDENCIES
    }
    assert report == simulator.build_feedback_simulation(document)
    assert all(path.read_bytes() == source for path, source in sources.items())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "payload",
    [
        b"\xffPRIVATE_SYNTHETIC_FEEDBACK_DO_NOT_ECHO",
        b"not JSON PRIVATE_SYNTHETIC_FEEDBACK_DO_NOT_ECHO",
        b'{"private":"PRIVATE_SYNTHETIC_FEEDBACK_DO_NOT_ECHO","n":NaN}',
        b'{"n":Infinity}',
        b'{"n":-Infinity}',
        b"null",
        b"[]",
        b"[" * 1100 + b"]" * 1100,
    ],
)
def test_cli_invalid_payloads_have_fixed_private_error(payload: bytes) -> None:
    result = _cli(payload)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.replace(b"\r\n", b"\n") == ERROR


@pytest.mark.parametrize(
    "field", ["record_origin", "snapshot_id", "profile_revision", "baseline_route"]
)
def test_cli_rejects_nested_duplicate_keys_even_when_last_value_is_valid(field: str) -> None:
    document = _document()
    payload = json.dumps(document)
    target = next(part for part in payload.split(", ") if f'"{field}":' in part)
    pair = target[target.index(f'"{field}":') :]
    payload = payload.replace(pair, f'"{field}": "{PRIVATE_MARKER}", ' + pair, 1)
    assert json.loads(payload) == document
    result = _cli(payload.encode())
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.replace(b"\r\n", b"\n") == ERROR


@pytest.mark.parametrize("blocked", [False, True])
def test_main_reads_only_stdin_and_five_sources_without_other_effects(
    simulator: Any, capsys: pytest.CaptureFixture[str], blocked: bool
) -> None:
    document = _document()
    if blocked:
        document["score_update"]["profile_assignment"] = "violated"
    payload = json.dumps(document).encode()
    sources = {
        path: path.read_bytes() for path in [SCRIPT, *(SCRIPT.parent / n for n in DEPENDENCIES)]
    }
    reads: list[Path] = []

    def source_bytes(path: Path) -> bytes:
        assert path in sources
        reads.append(path)
        return sources[path]

    with pytest.MonkeyPatch.context() as guard:
        guard.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
        guard.setattr(sys, "dont_write_bytecode", sys.dont_write_bytecode)
        _deny_effects(guard)
        guard.setattr(Path, "read_bytes", source_bytes)
        code = simulator.main([])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert sorted(reads) == sorted(sources)
    assert len(reads) == 5
    report = json.loads(captured.out)
    assert report["input_sha256"] == hashlib.sha256(payload).hexdigest()
    assert report["recommendation"] == (
        "INSUFFICIENT_EVIDENCE" if blocked else "PREPARE_ADDITIONAL_REVIEW"
    )


@pytest.mark.parametrize("failure", ["stdin", SCRIPT.name, *DEPENDENCIES])
def test_main_read_failures_do_not_echo_private_exception_text(
    simulator: Any, capsys: pytest.CaptureFixture[str], failure: str
) -> None:
    class UnreadableBuffer:
        def read(self) -> bytes:
            raise OSError(PRIVATE_MARKER)

    class UnreadableInput:
        buffer = UnreadableBuffer()

    payload = json.dumps(_document()).encode()
    sources = {
        path: path.read_bytes() for path in [SCRIPT, *(SCRIPT.parent / n for n in DEPENDENCIES)]
    }

    def source_bytes(path: Path) -> bytes:
        if path.name == failure:
            raise OSError(PRIVATE_MARKER)
        return sources[path]

    with pytest.MonkeyPatch.context() as guard:
        guard.setattr(
            sys,
            "stdin",
            UnreadableInput()
            if failure == "stdin"
            else io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"),
        )
        guard.setattr(sys, "dont_write_bytecode", sys.dont_write_bytecode)
        guard.setattr(Path, "read_bytes", source_bytes)
        assert simulator.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.encode() == ERROR


@pytest.mark.parametrize("payload", [b"[]", b"{", b"[" * 1100 + b"]" * 1100])
def test_inprocess_main_rejects_invalid_payload_without_private_details(
    simulator: Any, capsys: pytest.CaptureFixture[str], payload: bytes
) -> None:
    with pytest.MonkeyPatch.context() as guard:
        guard.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
        guard.setattr(sys, "dont_write_bytecode", sys.dont_write_bytecode)
        assert simulator.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.encode() == ERROR
