"""Counterexamples for declaration readback; all sources below are synthetic."""

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
SCRIPT = PROJECT_ROOT / "tools/analysis/review_detection_input.py"
HEAD = "a" * 40
PRIOR = "b" * 40
PR_URL = "https://github.com/synthetic/project/pull/17"
PRIVATE_MARKER = "PRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO"


@pytest.fixture
def reader(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("review_detection_input", SCRIPT)
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


def _pr(locator: str = "synthetic-locator", **changes: Any) -> dict[str, Any]:
    reference = {"kind": "pr", "url": PR_URL, "locator": locator}
    reference.update(changes)
    return reference


def _opportunity(identifier: str = "op-a", **changes: Any) -> dict[str, Any]:
    opportunity = {
        "opportunity_id": identifier,
        "contract_ref": _git("docs/superpowers/specs/prior.md", source_commit=PRIOR),
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


def _document(**changes: Any) -> dict[str, Any]:
    document = {
        "schema_version": "1.0",
        "repository": "synthetic/project",
        "admission_package": "review-detection-admission-v0.1",
        "window": {"t0": "2026-01-01T00:00:00Z", "t1": "2026-01-31T00:00:00Z"},
        "candidates": [_candidate()],
    }
    document.update(changes)
    return document


def _later(**changes: Any) -> dict[str, Any]:
    return _candidate(
        "candidate-z",
        declared_at="2026-01-01T01:00:00Z",
        entered_at="2026-01-01T02:00:00Z",
        **changes,
    )


def _statuses(report: dict[str, Any], code: str) -> set[str]:
    return {item["status"] for item in report["condition_checks"] if item["code"] == code}


def _selection(report: dict[str, Any], group: str | None = "group-a") -> dict[str, Any]:
    matching = [item for item in report["group_selections"] if item["related_group"] == group]
    assert len(matching) == 1
    return matching[0]


def _assert_unknown_selection(report: dict[str, Any]) -> None:
    selection = _selection(report)
    assert selection["status"] == "unknown"
    assert selection["candidate_id"] is None
    assert selection["opportunity_id"] is None


def test_complete_consistent_declarations_still_have_no_real_admission_or_sample(
    reader: Any,
) -> None:
    document = _document()
    report = reader.build_detection_input(document)

    assert report["reported_candidates"] == document["candidates"]
    assert report["coverage"] == {
        "reported_candidates": 1,
        "reported_groups": 1,
        "reported_opportunities": 1,
    }
    assert _selection(report) == {
        "related_group": "group-a",
        "status": "selected_reported",
        "candidate_id": "candidate-a",
        "opportunity_id": "op-a",
    }
    assert all(item["status"] == "consistent_reported" for item in report["condition_checks"])
    assert report["observation_admission"] == "unknown"
    assert report["probability_status"] == "unestimated"
    assert report["source_authenticity"] == "unknown"
    assert report["execution_allowed"] is False
    assert not ({"n", "k", "ready", "score", "conditional_result", "precision_met"} & report.keys())
    assert {item["code"] for item in report["next_source_checks"]} == {
        "VERIFY_ORIGINALS",
        "VERIFY_NATURAL_DOCS_SCOPE",
        "VERIFY_PRIOR_DECLARATION",
        "VERIFY_ROLES_AND_INPUTS",
        "VERIFY_TRUTH_AND_MATCH",
        "VERIFY_BUDGET_AND_CLOSURE",
        "VERIFY_GROUP_CONDITIONS",
    }


@pytest.mark.parametrize(
    "window", [{"t0": None, "t1": None}, {"t0": None, "t1": "2026-01-31T00:00:00Z"}]
)
def test_empty_package_does_not_create_observation_start_or_candidate(
    reader: Any, window: dict[str, Any]
) -> None:
    report = reader.build_detection_input(_document(window=window, candidates=[]))

    assert report["window"] == window
    assert report["reported_candidates"] == []
    assert report["group_selections"] == []
    assert set(report["coverage"].values()) == {0}
    assert _statuses(report, "WINDOW_DURATION") == {"unknown"}
    assert [item["code"] for item in report["next_source_checks"]] == ["LOCATE_NATURAL_CANDIDATE"]


@pytest.mark.parametrize("field", ["t0", "t1"])
def test_partial_window_retains_known_endpoint_and_blocks_group_choice(
    reader: Any, field: str
) -> None:
    document = _document()
    document["window"][field] = None
    report = reader.build_detection_input(document)

    assert report["window"] == document["window"]
    assert _statuses(report, "WINDOW_DURATION") == {"unknown"}
    _assert_unknown_selection(report)


@pytest.mark.parametrize("truth", ["negative", "disputed", "unknown"])
@pytest.mark.parametrize("unfavorable", ["truth", "missing_report", "unclosed"])
def test_first_candidate_is_never_replaced_by_later_detected_positive(
    reader: Any, truth: str, unfavorable: str
) -> None:
    first = _candidate(opportunities=[_opportunity(truth=truth, match="unknown")])
    if unfavorable == "missing_report":
        first["refs"]["report"] = None
        first["report_fixed_at"] = None
    if unfavorable == "unclosed":
        first["refs"]["closure"] = None
        first["closed_at"] = None
    document = _document(candidates=[_later(), first])

    report = reader.build_detection_input(document)

    assert _selection(report)["candidate_id"] == "candidate-a"
    assert _selection(report)["opportunity_id"] == "op-a"
    assert report["reported_candidates"] == document["candidates"]


@pytest.mark.parametrize("truth", ["negative", "disputed", "unknown"])
def test_first_opportunity_is_not_replaced_or_sorted_by_outcome(reader: Any, truth: str) -> None:
    first = _opportunity("z-id", object_ref=_git("docs/a.md"), truth=truth, match="unknown")
    later = _opportunity("a-id", object_ref=_git("docs/z.md"))

    report = reader.build_detection_input(
        _document(candidates=[_candidate(opportunities=[later, first])])
    )

    assert _selection(report)["opportunity_id"] == "z-id"


def test_missing_related_group_makes_all_package_selections_unknown(reader: Any) -> None:
    candidates = [
        _candidate(),
        _candidate("candidate-b", related_group="group-b"),
        _later(related_group=None),
    ]
    report = reader.build_detection_input(_document(candidates=candidates))

    assert report["coverage"]["reported_groups"] == 2
    assert {item["related_group"] for item in report["group_selections"]} == {
        "group-a",
        "group-b",
        None,
    }
    assert all(item["status"] == "unknown" for item in report["group_selections"])
    assert all(item["candidate_id"] is None for item in report["group_selections"])
    assert report["reported_candidates"] == candidates


@pytest.mark.parametrize(
    "case",
    [
        "missing_entry",
        "missing_declaration",
        "late_declaration",
        "same_declaration",
        "same_entry",
        "reversed_order",
        "equivalent_instant_tie",
    ],
)
def test_uncertain_or_conflicting_group_order_cannot_select_a_favorable_record(
    reader: Any, case: str
) -> None:
    first, later = _candidate(), _later()
    if case == "missing_entry":
        later["entered_at"] = None
    elif case == "missing_declaration":
        first["declared_at"] = None
    elif case == "late_declaration":
        first["declared_at"] = first["entered_at"]
    elif case == "same_declaration":
        later["declared_at"] = first["declared_at"]
    elif case == "same_entry":
        later["entered_at"] = first["entered_at"]
    elif case == "reversed_order":
        first["declared_at"] = "2025-12-31T23:55:00Z"
        later["declared_at"] = "2025-12-31T23:45:00Z"
    else:
        later["declared_at"] = "2025-12-31T23:50:00.000000+00:00"

    report = reader.build_detection_input(_document(candidates=[first, later]))

    _assert_unknown_selection(report)
    assert report["reported_candidates"] == [first, later]


@pytest.mark.parametrize(
    "case",
    [
        "empty",
        "missing_contract",
        "missing_object",
        "missing_instance",
        "same_sort_key",
        "same_instance",
    ],
)
def test_ambiguous_opportunities_are_not_disambiguated_with_id_or_array_position(
    reader: Any, case: str
) -> None:
    first, later = _opportunity(), _opportunity("op-z")
    opportunities = [later, first]
    if case == "empty":
        opportunities = []
    elif case.startswith("missing_"):
        later[case.removeprefix("missing_") + "_ref"] = None
    elif case == "same_sort_key":
        later["object_ref"] = copy.deepcopy(first["object_ref"])
    else:
        later["instance_ref"] = copy.deepcopy(first["instance_ref"])

    report = reader.build_detection_input(
        _document(candidates=[_candidate(opportunities=opportunities)])
    )

    _assert_unknown_selection(report)
    assert _statuses(report, "OPPORTUNITY_SELECTION") & {"conflict", "unknown"}


def test_candidate_and_opportunity_permutations_preserve_deterministic_selection(
    reader: Any,
) -> None:
    opportunities = [_opportunity("op-z"), _opportunity("op-a"), _opportunity("op-m")]
    for ordering in itertools.permutations(opportunities):
        first = _candidate(opportunities=list(ordering))
        for candidates in ([first, _later()], [_later(), first]):
            report = reader.build_detection_input(_document(candidates=candidates))
            assert _selection(report)["candidate_id"] == "candidate-a"
            assert _selection(report)["opportunity_id"] == "op-a"


def test_reference_order_uses_documented_fields_and_unicode_not_identifiers(reader: Any) -> None:
    first = _opportunity("z", contract_ref=_git("docs/Z.md", source_commit=PRIOR))
    later = _opportunity("a", contract_ref=_git("docs/a.md", source_commit=PRIOR))
    pr = _opportunity("0", contract_ref=_pr("contract"))
    report = reader.build_detection_input(
        _document(candidates=[_candidate(opportunities=[pr, later, first])])
    )

    assert _selection(report)["opportunity_id"] == "z"


@pytest.mark.parametrize(
    "entry,status",
    [
        ("2025-12-31T23:59:59.999999Z", "conflict"),
        ("2026-01-01T00:00:00+00:00", "consistent_reported"),
        ("2026-01-30T23:59:59.999999Z", "consistent_reported"),
        ("2026-01-31T00:00:00Z", "conflict"),
    ],
)
def test_entry_window_is_closed_at_start_and_open_at_end(
    reader: Any, entry: str, status: str
) -> None:
    document = _document(candidates=[_candidate(entered_at=entry)])
    report = reader.build_detection_input(document)

    assert _statuses(report, "ENTRY_WINDOW") == {status}
    assert report["reported_candidates"] == document["candidates"]
    if status == "conflict":
        assert _selection(report)["status"] == "no_in_window_candidate"


@pytest.mark.parametrize(
    "closed,status",
    [
        ("2026-01-30T23:59:59.999999Z", "consistent_reported"),
        ("2026-01-31T00:00:00+00:00", "conflict"),
        (None, "unknown"),
    ],
)
def test_closure_must_be_strictly_before_window_end(
    reader: Any, closed: str | None, status: str
) -> None:
    report = reader.build_detection_input(_document(candidates=[_candidate(closed_at=closed)]))

    assert _statuses(report, "CLOSURE_WINDOW") == {status}
    assert _selection(report)["candidate_id"] == "candidate-a"


@pytest.mark.parametrize(
    "end", ["2026-01-30T23:59:59.999999Z", "2026-01-31T00:00:00.000001Z", "2025-12-31T00:00:00Z"]
)
def test_wrong_duration_keeps_conflict_and_does_not_rewrite_window(reader: Any, end: str) -> None:
    window = {"t0": "2026-01-01T00:00:00Z", "t1": end}
    report = reader.build_detection_input(_document(window=window))

    assert report["window"] == window
    assert _statuses(report, "WINDOW_DURATION") == {"conflict"}
    _assert_unknown_selection(report)


def test_utc_equivalence_and_allowed_event_equalities_are_compared_as_instants(reader: Any) -> None:
    candidate = _candidate(
        declared_at="2025-12-31T23:59:59.999999Z",
        entered_at="2026-01-01T00:00:00.0+00:00",
        report_fixed_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-01T00:00:00.000000+00:00",
        opportunities=[
            _opportunity(
                adjudication_fixed_at="2026-01-01T00:00:00.00Z", matched_at="2026-01-01T00:00:00Z"
            )
        ],
    )
    document = _document(
        window={"t0": "2026-01-01T00:00:00+00:00", "t1": "2026-01-31T00:00:00.000000Z"},
        candidates=[candidate],
    )
    report = reader.build_detection_input(document)

    assert _statuses(report, "WINDOW_DURATION") == {"consistent_reported"}
    assert _statuses(report, "EVENT_ORDER") == {"consistent_reported"}
    assert _selection(report)["status"] == "selected_reported"


@pytest.mark.parametrize(
    "earlier,later",
    [
        ("declared_at", "entered_at"),
        ("entered_at", "report_fixed_at"),
        ("report_fixed_at", "adjudication_fixed_at"),
        ("adjudication_fixed_at", "matched_at"),
        ("matched_at", "closed_at"),
    ],
)
def test_each_adjacent_event_reversal_is_reported_without_repairing_values(
    reader: Any, earlier: str, later: str
) -> None:
    candidate = _candidate()
    opportunity = candidate["opportunities"][0]
    earlier_object = candidate if earlier in candidate else opportunity
    later_object = candidate if later in candidate else opportunity
    earlier_object[earlier], later_object[later] = later_object[later], earlier_object[earlier]
    report = reader.build_detection_input(_document(candidates=[candidate]))

    assert "conflict" in _statuses(report, "EVENT_ORDER")
    assert report["reported_candidates"] == [candidate]


@pytest.mark.parametrize("binding", ["candidate", "object"])
def test_candidate_binding_conflict_preserves_source_and_candidate_shas(
    reader: Any, binding: str
) -> None:
    candidate = _candidate()
    reference = (
        candidate["refs"]["candidate"]
        if binding == "candidate"
        else candidate["opportunities"][0]["object_ref"]
    )
    reference["source_commit"] = "d" * 40
    report = reader.build_detection_input(_document(candidates=[candidate]))

    assert "conflict" in _statuses(report, "CANDIDATE_BINDING")
    assert report["reported_candidates"] == [candidate]


@pytest.mark.parametrize(
    "missing", ["candidate_commit", "candidate_ref", "object_ref", "pr_candidate", "pr_object"]
)
def test_missing_or_pr_binding_is_unknown_without_reading_current_head(
    reader: Any, missing: str
) -> None:
    candidate = _candidate()
    if missing == "candidate_commit":
        candidate["candidate_commit"] = None
    elif missing in {"candidate_ref", "pr_candidate"}:
        candidate["refs"]["candidate"] = _pr() if missing == "pr_candidate" else None
    else:
        candidate["opportunities"][0]["object_ref"] = _pr() if missing == "pr_object" else None
    report = reader.build_detection_input(_document(candidates=[candidate]))

    assert "unknown" in _statuses(report, "CANDIDATE_BINDING")
    assert report["reported_candidates"] == [candidate]


@pytest.mark.parametrize("truth", ["negative", "disputed", "unknown"])
@pytest.mark.parametrize("match", ["detected", "not_detected"])
def test_nonpositive_truth_and_declared_match_remain_conflicting_raw_values(
    reader: Any, truth: str, match: str
) -> None:
    candidate = _candidate(opportunities=[_opportunity(truth=truth, match=match)])
    report = reader.build_detection_input(_document(candidates=[candidate]))

    assert _statuses(report, "TRUTH_MATCH") == {"conflict"}
    assert report["reported_candidates"] == [candidate]


def test_missing_original_references_do_not_become_default_evidence(reader: Any) -> None:
    candidate = _candidate()
    candidate["refs"] = dict.fromkeys(candidate["refs"])
    opportunity = candidate["opportunities"][0]
    opportunity["adjudication_ref"] = opportunity["matching_ref"] = None
    report = reader.build_detection_input(_document(candidates=[candidate]))

    assert "unknown" in _statuses(report, "REQUIRED_REFERENCE")
    assert report["reported_candidates"] == [candidate]
    assert report["observation_admission"] == "unknown"


@pytest.mark.parametrize(
    "level", ["document", "window", "candidate", "refs", "opportunity", "git_ref", "pr_ref"]
)
@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_type"])
def test_each_object_has_strict_required_shape(reader: Any, level: str, mutation: str) -> None:
    document = _document()
    candidate = document["candidates"][0]
    objects = {
        "document": document,
        "window": document["window"],
        "candidate": candidate,
        "refs": candidate["refs"],
        "opportunity": candidate["opportunities"][0],
        "git_ref": candidate["refs"]["candidate"],
        "pr_ref": candidate["refs"]["declaration"],
    }
    target = objects[level]
    if mutation == "missing":
        del target[next(iter(target))]
    elif mutation == "extra":
        target["ready"] = True
    elif level == "document":
        document = []
    elif level == "window":
        document["window"] = []
    elif level == "candidate":
        document["candidates"][0] = []
    elif level == "opportunity":
        candidate["opportunities"][0] = []
    elif level == "refs":
        candidate["refs"] = []
    else:
        candidate["refs"]["candidate" if level == "git_ref" else "declaration"] = []

    with pytest.raises(ValueError):
        reader.build_detection_input(document)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 1),
        ("schema_version", "2.0"),
        ("admission_package", "approved"),
        ("repository", "synthetic/../project"),
        ("repository", "./project"),
        ("repository", "synthetic/.."),
        ("repository", "synthetic/project?token=x"),
        ("candidates", {}),
        ("candidates", None),
        ("window", None),
    ],
)
def test_invalid_top_level_values_are_rejected(reader: Any, field: str, value: Any) -> None:
    with pytest.raises(ValueError):
        reader.build_detection_input(_document(**{field: value}))


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_id", ""),
        ("candidate_id", "_hidden"),
        ("candidate_id", "same/id"),
        ("candidate_id", True),
        ("related_group", ""),
        ("related_group", {}),
        ("candidate_commit", "A" * 40),
        ("candidate_commit", "a" * 39),
        ("candidate_commit", 1),
        ("opportunities", {}),
        ("opportunities", None),
    ],
)
def test_invalid_candidate_values_are_rejected(reader: Any, field: str, value: Any) -> None:
    with pytest.raises(ValueError):
        reader.build_detection_input(_document(candidates=[_candidate(**{field: value})]))


@pytest.mark.parametrize(
    "field,value",
    [
        ("opportunity_id", "_id"),
        ("opportunity_id", None),
        ("defect_class", "general_defect"),
        ("truth", True),
        ("truth", "POSITIVE"),
        ("match", False),
        ("match", "unmatched"),
    ],
)
def test_invalid_opportunity_values_are_rejected(reader: Any, field: str, value: Any) -> None:
    with pytest.raises(ValueError):
        reader.build_detection_input(
            _document(candidates=[_candidate(opportunities=[_opportunity(**{field: value})])])
        )


@pytest.mark.parametrize("duplicate", ["candidate", "opportunity"])
def test_duplicate_ids_are_rejected_not_deduplicated(reader: Any, duplicate: str) -> None:
    candidates = (
        [_candidate(), _candidate()]
        if duplicate == "candidate"
        else [_candidate(opportunities=[_opportunity(), _opportunity()])]
    )
    with pytest.raises(ValueError):
        reader.build_detection_input(_document(candidates=candidates))


@pytest.mark.parametrize(
    "value",
    [
        "2026-01-01T00:00:00",
        "2026-01-01T08:00:00+08:00",
        "2026-01-01",
        "2026-02-30T00:00:00Z",
        "2026-01-01T00:00:60Z",
        "2026-01-01T00:00:00.1234567Z",
        "2026-01-01t00:00:00z",
        "2026-01-01 00:00:00Z",
        "2026-01-01T00:00:00-00:00",
        0,
        True,
        {},
        "",
    ],
)
def test_invalid_utc_times_are_rejected_instead_of_coerced(reader: Any, value: Any) -> None:
    document = _document()
    document["candidates"][0]["opportunities"][0]["adjudication_fixed_at"] = value
    with pytest.raises(ValueError):
        reader.build_detection_input(document)


@pytest.mark.parametrize(
    "path",
    [
        "/absolute.md",
        "C:/absolute.md",
        "../escape.md",
        "docs/../escape.md",
        "docs/./file.md",
        "docs//file.md",
        "docs\\file.md",
        "docs/file.md/",
        "docs/\x00file.md",
        "docs/\nfile.md",
        "",
    ],
)
def test_git_paths_cannot_escape_or_hide_components(reader: Any, path: str) -> None:
    candidate = _candidate()
    candidate["refs"]["candidate"]["path"] = path
    with pytest.raises(ValueError):
        reader.build_detection_input(_document(candidates=[candidate]))


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/synthetic/project/pull/17",
        "https://evil.example/synthetic/project/pull/17",
        "https://github.com/other/project/pull/17",
        "https://user:secret@github.com/synthetic/project/pull/17",
        PR_URL + "?token=secret",
        PR_URL + "/",
        PR_URL + "#bad/anchor",
        "https://github.com/synthetic/project/pull/0",
        "https://github.com/synthetic/project/pull/-1",
        "https://github.com/synthetic/project/pull/017",
        "https://github.com/synthetic/project/pull/17\n",
    ],
)
def test_pr_references_reject_foreign_sources_credentials_and_noncanonical_urls(
    reader: Any, url: str
) -> None:
    candidate = _candidate()
    candidate["refs"]["report"] = _pr(url=url)
    with pytest.raises(ValueError):
        reader.build_detection_input(_document(candidates=[candidate]))


@pytest.mark.parametrize(
    "reference",
    [
        _git(source_commit="A" * 40),
        _git(git_blob="g" * 40),
        _git(locator=""),
        _pr(locator=""),
        _git(kind="file"),
        _pr(url=42),
    ],
)
def test_reference_tags_shas_and_locators_are_strict(reader: Any, reference: Any) -> None:
    candidate = _candidate()
    candidate["refs"]["report"] = reference
    with pytest.raises(ValueError):
        reader.build_detection_input(_document(candidates=[candidate]))


def test_public_pr_anchor_and_unanchored_locator_still_do_not_certify_sources(reader: Any) -> None:
    candidate = _candidate()
    candidate["refs"]["report"] = _pr(url=PR_URL + "#pullrequestreview-123")
    report = reader.build_detection_input(_document(candidates=[candidate]))

    assert report["reported_candidates"] == [candidate]
    assert report["history_completeness"] == "unknown"
    assert report["source_authenticity"] == "unknown"


def _deny_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Declaration readback attempted an external effect.")

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


def test_pure_function_has_no_effects_and_result_does_not_alias_input(reader: Any) -> None:
    document = _document()
    original = copy.deepcopy(document)
    with pytest.MonkeyPatch.context() as guard:
        _deny_effects(guard)
        report = reader.build_detection_input(document)

    assert document == original
    report["reported_candidates"][0]["refs"]["candidate"]["path"] = "changed"
    report["window"]["t0"] = None
    assert document == original


def _cli(payload: bytes, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii"
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT)],
        input=payload,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=environment,
        timeout=10,
    )


def test_standalone_cli_binds_exact_bytes_without_saving_input_or_result(
    reader: Any, tmp_path: Path
) -> None:
    payload = (" \n" + json.dumps(_document(), ensure_ascii=False) + "\n").encode()
    source = SCRIPT.read_bytes()
    result = _cli(payload, tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout.isascii()
    report = json.loads(result.stdout)
    assert report.pop("input_sha256") == hashlib.sha256(payload).hexdigest()
    assert report.pop("executed_tool_sha256") == hashlib.sha256(source).hexdigest()
    assert report == reader.build_detection_input(json.loads(payload))
    assert SCRIPT.read_bytes() == source
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "payload",
    [
        b"\xffPRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO",
        b"not JSON PRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO",
        b'{"private":"PRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO","n":NaN}',
        b'{"n":Infinity}',
        b'{"n":-Infinity}',
        b"null",
        b"[]",
        b"[" * 1100 + b"]" * 1100,
        json.dumps(_document(repository=PRIVATE_MARKER)).encode(),
    ],
)
def test_cli_errors_never_echo_input_or_emit_partial_report(payload: bytes) -> None:
    result = _cli(payload)

    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.strip()
    assert PRIVATE_MARKER.encode() not in result.stderr
    assert b"Traceback" not in result.stderr


@pytest.mark.parametrize("field", ["schema_version", "candidate_id", "opportunity_id", "git_blob"])
def test_nested_duplicate_keys_are_rejected_even_when_last_value_is_valid(field: str) -> None:
    document = _document()
    payload = json.dumps(document)
    target = next(part for part in payload.split(", ") if f'"{field}":' in part)
    key_start = target.index(f'"{field}":')
    pair = target[key_start:]
    payload = payload.replace(pair, f'"{field}": "{PRIVATE_MARKER}", ' + pair, 1)
    assert json.loads(payload) == document
    result = _cli(payload.encode())

    assert result.returncode == 2
    assert result.stdout == b""
    assert PRIVATE_MARKER.encode() not in result.stderr
    assert b"Traceback" not in result.stderr


def test_main_only_reads_its_script_and_stdin_without_other_effects(
    reader: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = json.dumps(_document()).encode()
    source = SCRIPT.read_bytes()
    reads: list[Path] = []

    def own_source(path: Path) -> bytes:
        assert path == SCRIPT
        reads.append(path)
        return source

    with pytest.MonkeyPatch.context() as guard:
        guard.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
        _deny_effects(guard)
        guard.setattr(Path, "read_bytes", own_source)
        code = reader.main([])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert reads == [SCRIPT]
    assert json.loads(captured.out)["input_sha256"] == hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize("failure", ["stdin", "source"])
def test_cli_read_failures_do_not_echo_private_exception_text(
    reader: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failure: str
) -> None:
    class UnreadableBuffer:
        def read(self) -> bytes:
            raise OSError(PRIVATE_MARKER)

    class UnreadableInput:
        buffer = UnreadableBuffer()

    def failed_source(path: Path) -> bytes:
        raise OSError(PRIVATE_MARKER)

    monkeypatch.setattr(
        sys,
        "stdin",
        UnreadableInput()
        if failure == "stdin"
        else io.TextIOWrapper(io.BytesIO(json.dumps(_document()).encode()), encoding="utf-8"),
    )
    if failure == "source":
        monkeypatch.setattr(Path, "read_bytes", failed_source)

    assert reader.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip()
    assert PRIVATE_MARKER not in captured.err
    assert "Traceback" not in captured.err
