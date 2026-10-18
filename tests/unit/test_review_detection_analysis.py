"""Record-level analysis counterexamples use invented synthetic declarations only."""

from __future__ import annotations

import builtins
import copy
import hashlib
import importlib.util
import io
import itertools
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "tools/analysis/review_detection_analysis.py"
DEPENDENCIES = (
    "benchmark_reference.py",
    "review_detection_input.py",
    "review_detection.py",
)
HEAD = "a" * 40
PRIOR = "b" * 40
PR_URL = "https://github.com/synthetic/project/pull/17"
PRIVATE_MARKER = "PRIVATE_SYNTHETIC_RECORD_DO_NOT_ECHO"
ERROR = b"review-detection-analysis: supplied synthetic records are invalid\n"
ASSUMPTIONS = (
    "selection_fixed_before_outcomes",
    "history_and_grouping_complete",
    "independent_truth_and_semantic_matching",
    "review_conditions_comparable",
    "group_outcomes_independent",
    "reports_and_budget_endpoints_complete",
    "single_analysis_after_fixed_window",
)


@pytest.fixture
def analyzer(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    for name in DEPENDENCIES:
        importlib.import_module(Path(name).stem)
    spec = importlib.util.spec_from_file_location("review_detection_analysis", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(path: str = "docs/candidate.md", **changes: Any) -> dict[str, Any]:
    reference = {
        "kind": "git",
        "source_commit": HEAD,
        "path": path,
        "git_blob": "c" * 40,
        "locator": "section-1",
    }
    reference.update(changes)
    return reference


def _pr(locator: str = "synthetic-locator") -> dict[str, Any]:
    return {"kind": "pr", "url": PR_URL, "locator": locator}


def _opportunity(identifier: str = "op-a", **changes: Any) -> dict[str, Any]:
    opportunity = {
        "opportunity_id": identifier,
        "contract_ref": _git("docs/prior.md", source_commit=PRIOR),
        "object_ref": _git(f"docs/{identifier}.md"),
        "instance_ref": _pr(f"instance-{identifier}"),
        "defect_class": "direct_contradiction",
        "truth": "positive",
        "adjudication_ref": _pr(f"adjudication-{identifier}"),
        "adjudication_fixed_at": "2026-01-03T00:00:00Z",
        "match": "detected",
        "matching_ref": _pr(f"matching-{identifier}"),
        "matched_at": "2026-01-04T00:00:00Z",
    }
    opportunity.update(changes)
    return opportunity


def _candidate(identifier: str = "candidate-a", **changes: Any) -> dict[str, Any]:
    candidate = {
        "candidate_id": identifier,
        "related_group": "group-a",
        "candidate_commit": HEAD,
        "declared_at": "2025-12-31T23:50:00Z",
        "entered_at": "2026-01-01T00:00:00Z",
        "report_fixed_at": "2026-01-02T00:00:00Z",
        "closed_at": "2026-01-05T00:00:00Z",
        "refs": {
            "candidate": _git(),
            **{
                role: _pr(role)
                for role in (
                    "declaration",
                    "related_group",
                    "conditions",
                    "roles",
                    "budget",
                    "report",
                    "closure",
                )
            },
        },
        "opportunities": [_opportunity()],
    }
    candidate.update(changes)
    return candidate


def _document(candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "record_origin": "synthetic",
        "declarations": {
            "schema_version": "1.0",
            "repository": "synthetic/project",
            "admission_package": "review-detection-admission-v0.1",
            "window": {"t0": "2026-01-01T00:00:00Z", "t1": "2026-01-31T00:00:00Z"},
            "candidates": [_candidate()] if candidates is None else candidates,
        },
        "scenario_assumptions": dict.fromkeys(ASSUMPTIONS, "assumed"),
    }


def _negative(identifier: str = "op-a", **changes: Any) -> dict[str, Any]:
    opportunity = _opportunity(
        identifier,
        truth="negative",
        match="unknown",
        matching_ref=None,
        matched_at=None,
    )
    opportunity.update(changes)
    return opportunity


def _result(report: dict[str, Any]) -> dict[str, Any]:
    assert report["analysis_status"] == "conditional_synthetic"
    assert report["blockers"] == []
    return report["synthetic_calculation"]["conditional_result"]


def _blockers(report: dict[str, Any], code: str) -> list[dict[str, Any]]:
    assert report["analysis_status"] == "blocked"
    assert report["synthetic_calculation"] is None
    return [item for item in report["blockers"] if item["code"] == code]


def test_multiple_groups_integrate_counts_with_existing_mathematics_without_admission(
    analyzer: Any,
) -> None:
    document = _document(
        [
            _candidate(f"candidate-{index}", related_group=f"group-{index}", opportunities=[op])
            for index, op in enumerate(
                (_opportunity(), _opportunity(match="not_detected"), _opportunity()), 1
            )
        ]
    )
    report = analyzer.build_detection_analysis(document)
    mathematics = importlib.import_module("review_detection")
    reader = importlib.import_module("review_detection_input")

    assert _result(report)["n"] == 3
    assert _result(report)["k"] == 2
    assert report["synthetic_calculation"] == mathematics.build_detection(
        {"schema_version": "1.0", "record_origin": "synthetic", "n": 3, "k": 2}
    )
    assert report["declaration_readback"] == reader.build_detection_input(document["declarations"])
    assert report["reported_selection_counts"] == {
        "positive_detected": 2,
        "positive_not_detected": 1,
        "negative": 0,
        "unresolved": 0,
        "outside_window_groups": 0,
        "unresolved_groups": 0,
    }
    assert report["measurement"] == "synthetic_review_detection_analysis"
    assert report["source_assurance"] == "synthetic_supplied_declarations"
    for field in (
        "source_authenticity",
        "history_completeness",
        "observation_admission",
        "statistical_independence",
        "actual_model_identity",
    ):
        assert report[field] == "unknown"
    assert report["method_status"] == "design_pending"
    assert report["probability_status"] == "unestimated"
    assert report["model_score_update_status"] == "not_implemented"
    assert report["execution_allowed"] is False
    assert report["permission_effect"] == report["ledger_effect"] == "none"
    assert not ({"n", "k", "score", "admitted", "ready"} & report.keys())


@pytest.mark.parametrize("candidates", [[], [_candidate(opportunities=[_negative()])]])
def test_zero_positive_units_keep_empty_interval(analyzer: Any, candidates: list[Any]) -> None:
    report = analyzer.build_detection_analysis(_document(candidates))
    result = _result(report)

    assert report["synthetic_calculation"]["calculation_status"] == "no_positive_units"
    assert result == dict.fromkeys(
        ("proportion", "lower", "upper", "width", "precision_met"), None
    ) | {"n": 0, "k": 0}


@pytest.mark.parametrize("n", [104, 105])
def test_verified_domain_is_not_silently_truncated(analyzer: Any, n: int) -> None:
    candidates = [
        _candidate(f"candidate-{index}", related_group=f"group-{index}") for index in range(n)
    ]
    report = analyzer.build_detection_analysis(_document(candidates))

    assert len(report["selected_units"]) == n
    assert report["reported_selection_counts"]["positive_detected"] == n
    if n == 104:
        assert _result(report)["n"] == _result(report)["k"] == 104
    else:
        assert _blockers(report, "VERIFIED_DOMAIN_EXCEEDED")


@pytest.mark.parametrize("truth", ["negative", "unknown", "disputed"])
@pytest.mark.parametrize("level", ["candidate", "opportunity"])
def test_first_unfavorable_unit_is_not_replaced_by_later_positive(
    analyzer: Any, truth: str, level: str
) -> None:
    first = _opportunity("first", object_ref=_git("docs/a.md"), truth=truth, match="unknown")
    first.update(matching_ref=None, matched_at=None)
    later_opportunity = _opportunity("later", object_ref=_git("docs/z.md"))
    candidate = _candidate(opportunities=[first])
    if level == "candidate":
        later = _candidate(
            "candidate-z",
            declared_at="2026-01-01T01:00:00Z",
            entered_at="2026-01-01T02:00:00Z",
            opportunities=[later_opportunity],
        )
        candidates = [later, candidate]
    else:
        candidate["opportunities"].insert(0, later_opportunity)
        candidates = [candidate]
    report = analyzer.build_detection_analysis(_document(candidates))

    assert report["selected_units"] == [
        {
            "related_group": "group-a",
            "candidate_id": "candidate-a",
            "opportunity_id": "first",
            "reported_outcome": "negative" if truth == "negative" else "unresolved",
        }
    ]
    if truth == "negative":
        assert _result(report)["n"] == 0
    else:
        assert _blockers(report, "OUTCOME_UNRESOLVED")


@pytest.mark.parametrize("assumption", ASSUMPTIONS)
@pytest.mark.parametrize("value,status", [("unknown", "unknown"), ("violated", "conflict")])
def test_each_scenario_assumption_gates_the_entire_batch(
    analyzer: Any, assumption: str, value: str, status: str
) -> None:
    document = _document()
    document["scenario_assumptions"][assumption] = value
    report = analyzer.build_detection_analysis(document)

    assert _blockers(report, "SCENARIO_ASSUMPTION") == [
        {
            "code": "SCENARIO_ASSUMPTION",
            "status": status,
            "locator": f"$.scenario_assumptions.{assumption}",
        }
    ]
    assert report["scenario_assumptions"] == document["scenario_assumptions"]
    assert report["reported_selection_counts"]["positive_detected"] == 1


def test_unknown_selected_group_blocks_otherwise_complete_groups(analyzer: Any) -> None:
    document = _document(
        [_candidate(), _candidate("candidate-b", related_group="group-b", declared_at=None)]
    )
    report = analyzer.build_detection_analysis(document)

    assert _blockers(report, "SELECTION_UNRESOLVED")
    assert report["reported_selection_counts"]["positive_detected"] == 1
    assert report["reported_selection_counts"]["unresolved_groups"] == 1
    assert len(report["selected_units"]) == 1


@pytest.mark.parametrize("field", ["t0", "t1"])
def test_unknown_window_blocks_even_empty_records(analyzer: Any, field: str) -> None:
    document = _document([])
    document["declarations"]["window"][field] = None
    report = analyzer.build_detection_analysis(document)

    assert _blockers(report, "WINDOW_DURATION")


def test_non_thirty_day_window_is_a_conflict(analyzer: Any) -> None:
    document = _document()
    document["declarations"]["window"]["t1"] = "2026-01-30T00:00:00Z"
    report = analyzer.build_detection_analysis(document)

    assert {item["status"] for item in _blockers(report, "WINDOW_DURATION")} == {"conflict"}


@pytest.mark.parametrize(
    "case", ["tie", "missing_sort_ref", "missing_group", "pr_object", "pr_candidate"]
)
def test_unresolved_preselection_or_object_binding_cannot_become_a_positive_unit(
    analyzer: Any, case: str
) -> None:
    document = _document()
    candidates = document["declarations"]["candidates"]
    if case == "tie":
        candidates.append(_candidate("candidate-tied"))
    elif case == "missing_sort_ref":
        candidates[0]["opportunities"][0]["contract_ref"] = None
    elif case == "missing_group":
        candidates[0]["related_group"] = None
    elif case == "pr_object":
        candidates[0]["opportunities"][0]["object_ref"] = _pr()
    else:
        candidates[0]["refs"]["candidate"] = _pr()
    report = analyzer.build_detection_analysis(document)

    assert _blockers(
        report, "CANDIDATE_BINDING" if case.startswith("pr_") else "SELECTION_UNRESOLVED"
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("candidate_ref", "REQUIRED_REFERENCE"),
        ("report_ref", "REQUIRED_REFERENCE"),
        ("adjudication_ref", "REQUIRED_REFERENCE"),
        ("matching_ref", "REQUIRED_REFERENCE"),
        ("candidate_commit", "CANDIDATE_BINDING"),
        ("object_commit", "CANDIDATE_BINDING"),
        ("declared_equal_entry", "EVENT_ORDER"),
        ("report_before_entry", "EVENT_ORDER"),
        ("adjudication_before_report", "EVENT_ORDER"),
        ("match_before_adjudication", "EVENT_ORDER"),
        ("match_after_close", "EVENT_ORDER"),
        ("closure_at_t1", "CLOSURE_WINDOW"),
        ("missing_report_time", "REQUIRED_TIME"),
        ("missing_adjudication_time", "REQUIRED_TIME"),
        ("missing_match_time", "REQUIRED_TIME"),
        ("missing_close_time", "REQUIRED_TIME"),
    ],
)
def test_selected_path_requires_references_bindings_and_complete_time_chain(
    analyzer: Any, case: str, code: str
) -> None:
    document = _document()
    candidate = document["declarations"]["candidates"][0]
    opportunity = candidate["opportunities"][0]
    if case in ("candidate_ref", "report_ref"):
        candidate["refs"][case.removesuffix("_ref")] = None
    elif case in ("adjudication_ref", "matching_ref"):
        opportunity[case] = None
    elif case == "candidate_commit":
        candidate["candidate_commit"] = "d" * 40
    elif case == "object_commit":
        opportunity["object_ref"]["source_commit"] = "d" * 40
    elif case == "declared_equal_entry":
        candidate["declared_at"] = candidate["entered_at"]
        code = "SELECTION_UNRESOLVED"
    elif case == "report_before_entry":
        candidate["report_fixed_at"] = "2025-12-31T23:59:59Z"
    elif case == "adjudication_before_report":
        opportunity["adjudication_fixed_at"] = candidate["entered_at"]
    elif case == "match_before_adjudication":
        opportunity["matched_at"] = candidate["report_fixed_at"]
    elif case == "match_after_close":
        opportunity["matched_at"] = "2026-01-06T00:00:00Z"
    elif case == "closure_at_t1":
        candidate["closed_at"] = document["declarations"]["window"]["t1"]
    else:
        field = case.removeprefix("missing_").removesuffix("_time")
        key = {"report": "report_fixed_at", "close": "closed_at"}.get(field)
        if key is not None:
            candidate[key] = None
        else:
            opportunity[{"adjudication": "adjudication_fixed_at", "match": "matched_at"}[field]] = (
                None
            )
    report = analyzer.build_detection_analysis(document)

    assert _blockers(report, code)
    assert all(item["locator"].startswith("$.declarations.") for item in report["blockers"])


@pytest.mark.parametrize("match", ["unknown", "detected", "not_detected"])
def test_negative_only_exempts_missing_matching_and_retains_known_truth_conflicts(
    analyzer: Any, match: str
) -> None:
    opportunity = _negative() if match == "unknown" else _opportunity(truth="negative", match=match)
    report = analyzer.build_detection_analysis(_document([_candidate(opportunities=[opportunity])]))

    if match == "unknown":
        assert _result(report)["n"] == 0
        checks = report["declaration_readback"]["condition_checks"]
        assert any(item["code"] == "TRUTH_MATCH" and item["status"] == "unknown" for item in checks)
    else:
        assert {item["status"] for item in _blockers(report, "TRUTH_MATCH")} == {"conflict"}


def test_negative_adjudication_after_closure_cannot_hide_behind_absent_match(analyzer: Any) -> None:
    document = _document(
        [_candidate(opportunities=[_negative(adjudication_fixed_at="2026-01-06T00:00:00Z")])]
    )
    report = analyzer.build_detection_analysis(document)

    assert {item["status"] for item in _blockers(report, "EVENT_ORDER")} == {"conflict"}


@pytest.mark.parametrize(
    "role",
    [
        "candidate",
        "declaration",
        "related_group",
        "conditions",
        "roles",
        "budget",
        "report",
        "closure",
    ],
)
def test_every_selected_candidate_reference_remains_required(analyzer: Any, role: str) -> None:
    document = _document()
    document["declarations"]["candidates"][0]["refs"][role] = None
    report = analyzer.build_detection_analysis(document)

    assert {
        "code": "REQUIRED_REFERENCE",
        "status": "unknown",
        "locator": f"$.declarations.candidates[0].refs.{role}",
    } in _blockers(report, "REQUIRED_REFERENCE")


@pytest.mark.parametrize("negative", [False, True])
def test_equal_report_adjudication_match_and_close_times_are_permitted(
    analyzer: Any, negative: bool
) -> None:
    moment = "2026-01-02T00:00:00Z"
    opportunity = _negative() if negative else _opportunity()
    opportunity["adjudication_fixed_at"] = moment
    if not negative:
        opportunity["matched_at"] = moment
    report = analyzer.build_detection_analysis(
        _document(
            [_candidate(report_fixed_at=moment, closed_at=moment, opportunities=[opportunity])]
        )
    )

    assert _result(report)["n"] == (0 if negative else 1)


@pytest.mark.parametrize("matched_at", ["2026-01-02T00:00:00Z", "2026-01-06T00:00:00Z"])
def test_negative_optional_matching_cannot_hide_supplied_time_conflicts(
    analyzer: Any, matched_at: str
) -> None:
    report = analyzer.build_detection_analysis(
        _document([_candidate(opportunities=[_negative(matched_at=matched_at)])])
    )

    assert {item["status"] for item in _blockers(report, "EVENT_ORDER")} == {"conflict"}


def test_positive_unknown_match_blocks_the_whole_batch_without_dropping_unit(analyzer: Any) -> None:
    document = _document(
        [
            _candidate(),
            _candidate(
                "candidate-b",
                related_group="group-b",
                opportunities=[_opportunity(match="unknown", matching_ref=None, matched_at=None)],
            ),
        ]
    )
    report = analyzer.build_detection_analysis(document)

    assert _blockers(report, "OUTCOME_UNRESOLVED")
    assert report["reported_selection_counts"]["positive_detected"] == 1
    assert report["reported_selection_counts"]["unresolved"] == 1


@pytest.mark.parametrize("unselected_time", [None, "2026-01-06T00:00:00Z"])
def test_unselected_opportunity_terminal_checks_with_shared_close_locator_do_not_block(
    analyzer: Any, unselected_time: str | None
) -> None:
    selected = _opportunity("chosen", object_ref=_git("docs/a.md"))
    unselected = _opportunity(
        "unselected", object_ref=_git("docs/z.md"), matched_at=unselected_time
    )
    report = analyzer.build_detection_analysis(
        _document([_candidate(opportunities=[unselected, selected])])
    )

    assert _result(report)["n"] == 1
    checks = report["declaration_readback"]["condition_checks"]
    assert any(
        item["code"] == "EVENT_ORDER"
        and item["locator"] == "$.candidates[0].closed_at"
        and item["status"] != "consistent_reported"
        for item in checks
    )
    assert report["selected_units"][0]["opportunity_id"] == "chosen"


def test_later_candidate_and_outside_window_gaps_remain_visible_without_becoming_blockers(
    analyzer: Any,
) -> None:
    later = _candidate(
        "candidate-later",
        declared_at="2026-01-02T00:00:00Z",
        entered_at="2026-01-03T00:00:00Z",
        report_fixed_at=None,
        closed_at=None,
        opportunities=[_opportunity(adjudication_ref=None, matching_ref=None)],
    )
    later["refs"]["report"] = None
    outside = _candidate(
        "candidate-outside",
        related_group="group-outside",
        declared_at=None,
        entered_at="2026-02-01T00:00:00Z",
        report_fixed_at=None,
        closed_at=None,
        opportunities=[],
    )
    document = _document([later, outside, _candidate()])
    report = analyzer.build_detection_analysis(document)

    assert _result(report)["n"] == 1
    assert report["reported_selection_counts"]["outside_window_groups"] == 1
    assert (
        report["declaration_readback"]["reported_candidates"]
        == document["declarations"]["candidates"]
    )
    assert any(
        item["status"] == "unknown" for item in report["declaration_readback"]["condition_checks"]
    )
    assert report["declaration_readback"]["next_source_checks"]


def test_group_and_reference_order_is_invariant_under_arrays_and_equivalent_utc(
    analyzer: Any,
) -> None:
    candidates = [
        _candidate(
            "candidate-later",
            declared_at="2026-01-01T01:00:00Z",
            entered_at="2026-01-01T02:00:00Z",
        ),
        _candidate(
            opportunities=[
                _opportunity("z-id", object_ref=_git("docs/a.md")),
                _opportunity("a-id", object_ref=_git("docs/z.md"), match="not_detected"),
            ]
        ),
        _candidate("candidate-b", related_group="group-b"),
    ]
    expected = analyzer.build_detection_analysis(_document(candidates))
    for permutation in itertools.permutations(candidates):
        document = _document(copy.deepcopy(list(permutation)))
        for candidate in document["declarations"]["candidates"]:
            for field in ("declared_at", "entered_at", "report_fixed_at", "closed_at"):
                candidate[field] = candidate[field].replace("Z", "+00:00")
            candidate["opportunities"].reverse()
        report = analyzer.build_detection_analysis(document)
        assert report["selected_units"] == expected["selected_units"]
        assert report["reported_selection_counts"] == expected["reported_selection_counts"]
        assert report["synthetic_calculation"] == expected["synthetic_calculation"]
        assert _result(report)["n"] == 2


@pytest.mark.parametrize(
    "case",
    [
        "top_list",
        "top_extra",
        "top_missing",
        "version_bool",
        "real_origin",
        "captured_origin",
        "origin_bool",
        "declarations_report",
        "assumptions_list",
        "assumption_missing",
        "assumption_extra",
        "assumption_verified",
        "assumption_bool",
        "candidate_tuple",
    ],
)
def test_shape_and_real_or_certified_labels_are_rejected(analyzer: Any, case: str) -> None:
    document: Any = _document()
    if case == "top_list":
        document = []
    elif case == "top_extra":
        document["execution_allowed"] = True
    elif case == "top_missing":
        del document["record_origin"]
    elif case == "version_bool":
        document["schema_version"] = True
    elif case in ("real_origin", "captured_origin", "origin_bool"):
        document["record_origin"] = {"real_origin": "real", "captured_origin": "captured"}.get(
            case, True
        )
    elif case == "declarations_report":
        document["declarations"] = importlib.import_module(
            "review_detection_input"
        ).build_detection_input(document["declarations"])
    elif case == "assumptions_list":
        document["scenario_assumptions"] = []
    elif case == "assumption_missing":
        del document["scenario_assumptions"][ASSUMPTIONS[0]]
    elif case == "assumption_extra":
        document["scenario_assumptions"]["independent"] = True
    elif case in ("assumption_verified", "assumption_bool"):
        document["scenario_assumptions"][ASSUMPTIONS[0]] = (
            "verified" if case == "assumption_verified" else True
        )
    else:
        document["declarations"]["candidates"] = tuple(document["declarations"]["candidates"])
    with pytest.raises(ValueError):
        analyzer.build_detection_analysis(document)


def _deny_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Synthetic record analysis attempted an external effect.")

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


def test_pure_function_has_no_io_and_neither_result_nor_input_aliases(analyzer: Any) -> None:
    document = _document()
    original = copy.deepcopy(document)
    with pytest.MonkeyPatch.context() as guard:
        _deny_effects(guard)
        report = analyzer.build_detection_analysis(document)
    assert document == original
    report["scenario_assumptions"][ASSUMPTIONS[0]] = "violated"
    report["declaration_readback"]["reported_candidates"][0]["candidate_id"] = "changed"
    report["declaration_readback"]["window"]["t0"] = None
    report["selected_units"][0]["candidate_id"] = "different"
    assert document == original
    assert analyzer.build_detection_analysis(document)["selected_units"][0]["candidate_id"] == (
        "candidate-a"
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
        timeout=10,
    )


@pytest.mark.parametrize("encoding", ["ascii", "gbk"])
@pytest.mark.parametrize("blocked", [False, True])
def test_standalone_cli_preserves_unicode_and_binds_raw_bytes_and_all_sources(
    analyzer: Any, tmp_path: Path, encoding: str, blocked: bool
) -> None:
    document = _document()
    document["declarations"]["candidates"][0]["refs"]["report"]["locator"] = "合成 😀 输入"
    if blocked:
        document["scenario_assumptions"][ASSUMPTIONS[0]] = "unknown"
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
    assert report == analyzer.build_detection_analysis(document)
    assert report["analysis_status"] == ("blocked" if blocked else "conditional_synthetic")
    assert all(path.read_bytes() == source for path, source in sources.items())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "payload",
    [
        b"\xffPRIVATE_SYNTHETIC_RECORD_DO_NOT_ECHO",
        b"not JSON PRIVATE_SYNTHETIC_RECORD_DO_NOT_ECHO",
        b'{"private":"PRIVATE_SYNTHETIC_RECORD_DO_NOT_ECHO","n":NaN}',
        b'{"n":Infinity}',
        b'{"n":-Infinity}',
        b"null",
        b"[]",
        b"[" * 1100 + b"]" * 1100,
        json.dumps(_document() | {"record_origin": PRIVATE_MARKER}).encode(),
    ],
)
def test_cli_rejects_invalid_bytes_json_and_shape_with_fixed_private_error(payload: bytes) -> None:
    result = _cli(payload)

    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.replace(b"\r\n", b"\n") == ERROR


@pytest.mark.parametrize("field", ["record_origin", "repository", "candidate_id", ASSUMPTIONS[0]])
def test_nested_duplicate_keys_are_rejected_even_when_last_value_is_valid(field: str) -> None:
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
def test_main_reads_only_stdin_and_four_source_files_without_other_effects(
    analyzer: Any, capsys: pytest.CaptureFixture[str], blocked: bool
) -> None:
    document = _document()
    if blocked:
        document["scenario_assumptions"][ASSUMPTIONS[0]] = "violated"
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
        code = analyzer.main([])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    assert sorted(reads) == sorted(sources)
    assert len(reads) == 4
    report = json.loads(captured.out)
    assert report["input_sha256"] == hashlib.sha256(payload).hexdigest()
    assert report["analysis_status"] == ("blocked" if blocked else "conditional_synthetic")


@pytest.mark.parametrize("failure", ["stdin", SCRIPT.name, *DEPENDENCIES])
def test_main_read_failures_do_not_echo_private_exception_text(
    analyzer: Any, capsys: pytest.CaptureFixture[str], failure: str
) -> None:
    class UnreadableBuffer:
        def read(self) -> bytes:
            raise OSError(PRIVATE_MARKER)

    class UnreadableInput:
        buffer = UnreadableBuffer()

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
            else io.TextIOWrapper(io.BytesIO(json.dumps(_document()).encode()), encoding="utf-8"),
        )
        guard.setattr(sys, "dont_write_bytecode", sys.dont_write_bytecode)
        guard.setattr(Path, "read_bytes", source_bytes)
        assert analyzer.main([]) == 2
    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err.encode() == ERROR
