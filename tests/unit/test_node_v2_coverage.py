"""Portable, synthetic data tests for the fixed Node revision-2 report contracts.

These tests do not establish producer provenance or execute product acceptance.
The ordinary execution service binds those inputs and real process originals.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

import aiflow.node_verification as node
from aiflow.errors import AiflowError

SOURCE = "src/local/run.ts"
METHOD = "vitest-4.1.10-istanbul-vite-8.2.1-oxc-es2024-zero-hit-ts-ast-wire-v2"
ACCEPTANCE_FILE = "tests/local/personal-dot-integration.test.ts"
INTEGRATION_FILE = "tests/local/weixin-shared-integration.test.ts"
ACCEPTANCE_ANCESTOR = "personal dot authenticated MCP + unified WeChat host (offline)"
INTEGRATION_ANCESTOR = "synthetic Weixin, HTTP and shared runtime integration"
SELECTED = (
    (
        "acceptance",
        ACCEPTANCE_FILE,
        ACCEPTANCE_ANCESTOR,
        "persists duplicate input once, publishes one event, executes original text once "
        "and replies to the saved conversation once",
    ),
    (
        "acceptance",
        ACCEPTANCE_FILE,
        ACCEPTANCE_ANCESTOR,
        "rejects unauthenticated event calls, foreign targets and direct submissions "
        "before any dispatch",
    ),
    (
        "integration",
        INTEGRATION_FILE,
        INTEGRATION_ANCESTOR,
        "persists a polled task contract and returns its terminal result through "
        "the same shared host",
    ),
    (
        "integration",
        INTEGRATION_FILE,
        INTEGRATION_ANCESTOR,
        "runs the isolated shared host with durable duplicate and uncertain reply handling",
    ),
    (
        "integration",
        INTEGRATION_FILE,
        INTEGRATION_ANCESTOR,
        "shares route-bound tasks, reads, stop and client lifetime with a second client",
    ),
)


def location(line: int, start: int, end: int | None) -> dict:
    return {"start": {"line": line, "column": start}, "end": {"line": line, "column": end}}


def catalog(files: dict) -> dict:
    return {
        "kind": "independent-istanbul-zero-hit-domain-v1",
        "producer": "@vitest/coverage-istanbul@4.1.10",
        "transform": "vite@8.2.1-oxc-es2024",
        "typescript_parser": "@babel/parser@7.29.12",
        "files": files,
    }


def coverage_fixture() -> tuple[dict, dict, dict]:
    sources = {SOURCE: b"export function run(enabled: boolean) {\n  if (enabled) execute();\n}\n"}
    parent = location(2, 2, 25)
    locations = [location(2, 15, 25), {"start": {}, "end": {}}]
    reports = {
        SOURCE: {
            "path": SOURCE,
            "statementMap": {"0": deepcopy(parent)},
            "fnMap": {
                "0": {
                    "name": "run",
                    "decl": location(1, 16, 19),
                    "loc": {"start": {"line": 1, "column": 0}, "end": {"line": 3, "column": 1}},
                }
            },
            "branchMap": {
                "0": {"loc": deepcopy(parent), "locations": deepcopy(locations), "type": "if"}
            },
            "s": {"0": 1},
            "f": {"0": 1},
            "b": {"0": [1, 0]},
        }
    }
    expected = catalog(
        {
            SOURCE: {
                "sha256": hashlib.sha256(sources[SOURCE]).hexdigest(),
                "lines": [2],
                "implicit_else": [
                    {
                        "parent": deepcopy(parent),
                        "locations": deepcopy(locations),
                        "type": "if",
                        "ast_start": {"line": 2, "column": 2},
                        "ast_end": {"line": 2, "column": 25},
                    }
                ],
            }
        }
    )
    return reports, sources, expected


def calculate(reports: dict, sources: dict, expected: dict, **changes: object) -> dict:
    return node.validate_node_istanbul_line_coverage(
        reports,
        tracked_sources=sources,
        changed_lines=changes.get("changed_lines", {SOURCE: [2]}),
        deleted_sources=changes.get("deleted_sources", ()),
        catalog=expected,
    )


def test_revision2_accepts_proved_implicit_else_and_preserves_input_bytes() -> None:
    reports, sources, expected = coverage_fixture()
    original = deepcopy((reports, sources, expected))
    assert calculate(reports, sources, expected) == {
        "scope_files": 1,
        "total": {"covered": 1, "executable": 1, "threshold": 85},
        "changed": {"covered": 1, "executable": 1, "threshold": 90, "applicability": "applicable"},
        "method": METHOD,
    }
    assert (reports, sources, expected) == original


@pytest.mark.parametrize("null_end", [False, True], ids=["one-trailing-space", "wire-null-end"])
def test_implicit_parent_ends_use_only_fixed_wire_conventions(null_end: bool) -> None:
    reports, sources, expected = coverage_fixture()
    end = None if null_end else 26
    if not null_end:
        sources[SOURCE] = sources[SOURCE].replace(b"execute();\n", b"execute(); \n")
        expected["files"][SOURCE]["sha256"] = hashlib.sha256(sources[SOURCE]).hexdigest()
    reports[SOURCE]["branchMap"]["0"]["loc"]["end"]["column"] = end
    expected["files"][SOURCE]["implicit_else"][0]["parent"]["end"]["column"] = end
    assert calculate(reports, sources, expected)["total"]["covered"] == 1


def test_revision1_still_rejects_empty_else_without_broadening_its_ranges() -> None:
    reports, sources, _expected = coverage_fixture()
    arguments = dict(
        tracked_sources=sources,
        changed_lines={SOURCE: [2]},
        deleted_sources=(),
        expected_executable_lines={SOURCE: [2]},
    )
    ordinary = deepcopy(reports)
    ordinary[SOURCE]["branchMap"]["0"]["locations"][1] = location(2, 15, 25)
    assert node.validate_node_line_coverage(ordinary, **arguments)["total"]["covered"] == 1
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(reports, **arguments)


@pytest.mark.parametrize("counter", ["s", "f", "b"])
@pytest.mark.parametrize("invalid", [-1, True, 0.5, 2**53, None])
def test_every_counter_rejects_negative_noninteger_and_unsafe_hits(
    counter: str, invalid: object
) -> None:
    reports, sources, expected = coverage_fixture()
    reports[SOURCE][counter]["0"] = [1, invalid] if counter == "b" else invalid
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected)


@pytest.mark.parametrize("identity", ["00", "-1", "1.0", "", True])
def test_statement_identifiers_have_canonical_decimal_identity(identity: object) -> None:
    reports, sources, expected = coverage_fixture()
    reports[SOURCE]["statementMap"] = {identity: reports[SOURCE]["statementMap"]["0"]}
    reports[SOURCE]["s"] = {identity: 1}
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected)


def test_remapped_ids_may_be_sparse_without_becoming_new_exemptions() -> None:
    reports, sources, expected = coverage_fixture()
    for map_name, count_name in (("statementMap", "s"), ("fnMap", "f"), ("branchMap", "b")):
        reports[SOURCE][map_name] = {"17": reports[SOURCE][map_name]["0"]}
        reports[SOURCE][count_name] = {"17": reports[SOURCE][count_name]["0"]}
    assert calculate(reports, sources, expected)["total"]["executable"] == 1


def test_all_hit_kinds_accept_the_declared_maximum_safe_integer() -> None:
    reports, sources, expected = coverage_fixture()
    reports[SOURCE]["s"]["0"] = 2**53 - 1
    reports[SOURCE]["f"]["0"] = 2**53 - 1
    reports[SOURCE]["b"]["0"] = [2**53 - 1, 0]
    assert calculate(reports, sources, expected)["total"]["covered"] == 1


@pytest.mark.parametrize(
    "fault",
    [
        "raw_extra",
        "raw_missing",
        "wrong_path",
        "s_ids",
        "f_ids",
        "b_ids",
        "b_arity",
        "fn_extra_line",
        "branch_extra_line",
        "fn_bad_name",
        "fn_bad_decl",
        "branch_bad_type",
        "missing_certificate",
        "duplicate_certificate",
        "unused_certificate",
        "wrong_slot",
        "sentinel_extra_key",
        "sentinel_null",
        "branch_parent_drift",
        "wrong_catalog_type",
        "catalog_unknown",
        "catalog_wrong_producer",
        "catalog_wrong_hash",
        "catalog_extra_row",
        "catalog_duplicate_lines",
        "catalog_outside_line",
        "unknown_source",
        "missing_report",
        "deleted_overlap",
        "reversed_range",
        "unbound_aux_range",
        "null_start",
        "ignore_source",
        "wrong_map_container",
        "wrong_catalog_row",
        "wrong_tuple_container",
        "different_ast_start",
        "empty_with_runtime_maps",
        "different_executable_domain",
    ],
)
def test_coverage_rejects_incomplete_raw_maps_auxiliary_roles_and_unproved_sentinels(
    fault: str,
) -> None:
    reports, sources, expected = coverage_fixture()
    report = reports[SOURCE]
    row = expected["files"][SOURCE]
    kwargs = {}
    if fault == "raw_extra":
        report["all"] = True
    elif fault == "raw_missing":
        del report["f"]
    elif fault == "wrong_path":
        report["path"] = "src/local/other.ts"
    elif fault in {"s_ids", "f_ids", "b_ids"}:
        report[fault[0]] = {}
    elif fault == "b_arity":
        report["b"]["0"] = [1]
    elif fault == "fn_extra_line":
        report["fnMap"]["0"]["line"] = 1
    elif fault == "branch_extra_line":
        report["branchMap"]["0"]["line"] = 2
    elif fault == "fn_bad_name":
        report["fnMap"]["0"]["name"] = True
    elif fault == "fn_bad_decl":
        report["fnMap"]["0"]["decl"]["start"]["column"] = 999
    elif fault == "branch_bad_type":
        report["branchMap"]["0"]["type"] = "caller-defined"
    elif fault == "missing_certificate":
        row["implicit_else"] = []
    elif fault == "duplicate_certificate":
        row["implicit_else"].append(deepcopy(row["implicit_else"][0]))
    elif fault == "unused_certificate":
        report["branchMap"] = {}
        report["b"] = {}
    elif fault == "wrong_slot":
        report["branchMap"]["0"]["locations"].reverse()
        row["implicit_else"][0]["locations"].reverse()
    elif fault == "sentinel_extra_key":
        report["branchMap"]["0"]["locations"][1]["start"]["unknown"] = 1
    elif fault == "sentinel_null":
        report["branchMap"]["0"]["locations"][1]["start"] = None
    elif fault == "branch_parent_drift":
        report["branchMap"]["0"]["loc"]["start"]["column"] = 3
    elif fault == "wrong_catalog_type":
        row["implicit_else"][0]["type"] = "cond-expr"
    elif fault == "catalog_unknown":
        expected["allow_empty"] = True
    elif fault == "catalog_wrong_producer":
        expected["producer"] = "@vitest/coverage-v8@4.1.10"
    elif fault == "catalog_wrong_hash":
        row["sha256"] = "0" * 64
    elif fault == "catalog_extra_row":
        expected["files"]["src/local/foreign.ts"] = deepcopy(row)
    elif fault == "catalog_duplicate_lines":
        row["lines"] = [2, 2]
    elif fault == "catalog_outside_line":
        row["lines"] = [999]
    elif fault == "unknown_source":
        reports["src/local/foreign.ts"] = deepcopy(report)
    elif fault == "missing_report":
        reports.clear()
    elif fault == "deleted_overlap":
        kwargs["deleted_sources"] = [SOURCE]
    elif fault == "reversed_range":
        report["fnMap"]["0"]["loc"]["end"] = {"line": 1, "column": 0}
        report["fnMap"]["0"]["loc"]["start"] = {"line": 3, "column": 1}
    elif fault == "unbound_aux_range":
        report["branchMap"]["0"]["locations"][0]["end"]["line"] = 999
    elif fault == "null_start":
        report["statementMap"]["0"]["start"]["column"] = None
    elif fault == "ignore_source":
        sources[SOURCE] = b"// istanbul ignore next\n" + sources[SOURCE]
        row["sha256"] = hashlib.sha256(sources[SOURCE]).hexdigest()
    elif fault == "wrong_map_container":
        report["s"] = []
    elif fault == "wrong_catalog_row":
        expected["files"][SOURCE] = []
    elif fault == "wrong_tuple_container":
        row["implicit_else"] = {}
    elif fault == "different_ast_start":
        row["implicit_else"][0]["ast_start"]["column"] = 3
    elif fault == "empty_with_runtime_maps":
        row["empty_domain"] = {"kind": "named_source_reexports_only_v1", "statements": 2}
        row["lines"] = []
        row["implicit_else"] = []
    elif fault == "different_executable_domain":
        row["lines"] = [1, 2]
    else:
        raise AssertionError(fault)
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected, **kwargs)


@pytest.mark.parametrize("present", [False, True], ids=["absent-raw", "present-empty-raw"])
def test_only_certified_empty_source_can_lack_an_original_report(present: bool) -> None:
    reports, sources, expected = coverage_fixture()
    empty = "src/local/lease.ts"
    sources[empty] = b'export { value } from "./run.js";\nexport type { Token } from "./run.js";\n'
    expected["files"][empty] = {
        "sha256": hashlib.sha256(sources[empty]).hexdigest(),
        "lines": [],
        "implicit_else": [],
        "empty_domain": {"kind": "named_source_reexports_only_v1", "statements": 2},
    }
    if present:
        reports[empty] = {
            "path": empty,
            "statementMap": {},
            "fnMap": {},
            "branchMap": {},
            "s": {},
            "f": {},
            "b": {},
        }
    result = calculate(reports, sources, expected)
    assert result["scope_files"] == 2 and result["total"]["executable"] == 1


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "wrong_kind",
        "zero_statements",
        "boolean_statements",
        "unknown_field",
        "nonempty_domain",
    ],
)
def test_empty_domain_requires_a_closed_bound_certificate(fault: str) -> None:
    reports, sources, expected = coverage_fixture()
    row = expected["files"][SOURCE]
    reports.clear()
    row["lines"] = []
    row["implicit_else"] = []
    certificate = {"kind": "named_source_reexports_only_v1", "statements": 2}
    row["empty_domain"] = certificate
    if fault == "missing":
        del row["empty_domain"]
    elif fault == "wrong_kind":
        certificate["kind"] = "arbitrary_empty_file"
    elif fault == "zero_statements":
        certificate["statements"] = 0
    elif fault == "boolean_statements":
        certificate["statements"] = True
    elif fault == "unknown_field":
        certificate["allow"] = True
    elif fault == "nonempty_domain":
        row["lines"] = [2]
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected)


def linear_fixture(hits: int) -> tuple[dict, dict, dict]:
    sources = {SOURCE: "".join(f"export const value{i} = {i};\n" for i in range(20)).encode()}
    lines = sources[SOURCE].decode().splitlines()
    report = {
        "path": SOURCE,
        "statementMap": {str(i): location(i + 1, 0, len(line)) for i, line in enumerate(lines)},
        "fnMap": {},
        "branchMap": {},
        "s": {str(i): int(i < hits) for i in range(20)},
        "f": {},
        "b": {},
    }
    expected = catalog(
        {
            SOURCE: {
                "sha256": hashlib.sha256(sources[SOURCE]).hexdigest(),
                "lines": list(range(1, 21)),
                "implicit_else": [],
            }
        }
    )
    return {SOURCE: report}, sources, expected


def test_total_and_changed_thresholds_accept_exact_integer_boundaries() -> None:
    reports, sources, expected = linear_fixture(17)
    result = calculate(reports, sources, expected, changed_lines={SOURCE: [*range(1, 10), 18]})
    assert result["total"] == {"covered": 17, "executable": 20, "threshold": 85}
    assert result["changed"]["covered"] == 9 and result["changed"]["executable"] == 10


@pytest.mark.parametrize(
    "hits,changed,code",
    [(16, [], "NODE_TOTAL_COVERAGE_LOW"), (18, [*range(1, 9), 19, 20], "NODE_DIFF_COVERAGE_LOW")],
)
def test_threshold_failures_remain_distinct(hits: int, changed: list[int], code: str) -> None:
    reports, sources, expected = linear_fixture(hits)
    with pytest.raises(AiflowError) as caught:
        calculate(reports, sources, expected, changed_lines={SOURCE: changed})
    assert caught.value.code == code


def test_changed_nonexecutable_lines_and_deleted_sources_do_not_fabricate_hits() -> None:
    reports, sources, expected = coverage_fixture()
    result = calculate(
        reports,
        sources,
        expected,
        changed_lines={SOURCE: [1], "src/local/removed.ts": [1]},
        deleted_sources=["src/local/removed.ts"],
    )
    assert result["changed"] == {
        "covered": 0,
        "executable": 0,
        "threshold": 90,
        "applicability": "not_applicable",
    }


def test_unverified_changed_execution_inputs_cannot_escape_ts_coverage_scope() -> None:
    reports, sources, expected = coverage_fixture()
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected, changed_lines={"src/local/runtime.js": [1]})


def test_unicode_ranges_cannot_split_a_surrogate_pair() -> None:
    reports, sources, expected = linear_fixture(20)
    sources[SOURCE] = sources[SOURCE].replace(b"value0 = 0", 'value0 = "😀"'.encode())
    expected["files"][SOURCE]["sha256"] = hashlib.sha256(sources[SOURCE]).hexdigest()
    line = sources[SOURCE].decode().splitlines()[0]
    offset = len(line[: line.index("😀")].encode("utf-16-le")) // 2
    reports[SOURCE]["statementMap"]["0"] = location(1, offset + 1, offset + 2)
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected, changed_lines={})


def test_valid_unicode_endpoints_use_utf16_offsets_instead_of_python_character_counts() -> None:
    reports, sources, expected = linear_fixture(20)
    sources[SOURCE] = sources[SOURCE].replace(b"value0 = 0", 'value0 = "😀"'.encode())
    expected["files"][SOURCE]["sha256"] = hashlib.sha256(sources[SOURCE]).hexdigest()
    line = sources[SOURCE].decode().splitlines()[0]
    reports[SOURCE]["statementMap"]["0"] = location(1, 0, len(line.encode("utf-16-le")) // 2)
    assert (
        calculate(reports, sources, expected, changed_lines={SOURCE: [1]})["total"]["covered"] == 20
    )


@pytest.mark.parametrize(
    "kind,source",
    [
        ("if", b"if (enabled) one(); else two();\n"),
        ("binary-expr", b"export const value = enabled && execute();\n"),
        ("cond-expr", b"export const value = enabled ? one() : two();\n"),
        ("default-arg", b"export function run(value = 1) { return value; }\n"),
        ("switch", b"switch (value) { case 1: one(); break; default: two(); }\n"),
    ],
)
def test_fixed_normal_branch_kinds_keep_their_real_nonempty_ranges(
    kind: str, source: bytes
) -> None:
    span = location(1, 0, len(source.rstrip(b"\n")))
    reports = {
        SOURCE: {
            "path": SOURCE,
            "statementMap": {"0": deepcopy(span)},
            "fnMap": {},
            "branchMap": {
                "0": {
                    "loc": deepcopy(span),
                    "locations": [deepcopy(span), deepcopy(span)],
                    "type": kind,
                }
            },
            "s": {"0": 1},
            "f": {},
            "b": {"0": [1, 0]},
        }
    }
    expected = catalog(
        {SOURCE: {"sha256": hashlib.sha256(source).hexdigest(), "lines": [1], "implicit_else": []}}
    )
    assert (
        calculate(reports, {SOURCE: source}, expected, changed_lines={SOURCE: [1]})["total"][
            "covered"
        ]
        == 1
    )


def test_implicit_parent_cannot_use_one_extra_nonspace_character_as_mapping_trivia() -> None:
    reports, sources, expected = coverage_fixture()
    sources[SOURCE] = sources[SOURCE].replace(b"execute();\n", b"execute();x\n")
    expected["files"][SOURCE]["sha256"] = hashlib.sha256(sources[SOURCE]).hexdigest()
    reports[SOURCE]["branchMap"]["0"]["loc"]["end"]["column"] = 26
    expected["files"][SOURCE]["implicit_else"][0]["parent"]["end"]["column"] = 26
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected)


def test_revision2_coverage_cannot_pass_after_its_fixed_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports, sources, expected = coverage_fixture()
    monkeypatch.setattr(node, "monotonic", iter((0.0, 31.0)).__next__)
    with pytest.raises(AiflowError) as caught:
        calculate(reports, sources, expected)
    assert caught.value.code == "NODE_COVERAGE_TIMEOUT"


@pytest.mark.parametrize("changed", [[2, 2], [0], [True], [999], [3, 2]])
def test_diff_line_inventory_cannot_hide_duplicates_or_invalid_source_coordinates(
    changed: list,
) -> None:
    reports, sources, expected = coverage_fixture()
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected, changed_lines={SOURCE: changed})


def test_source_utf8_validation_cannot_be_replaced_by_an_agreeing_hash() -> None:
    reports, sources, expected = coverage_fixture()
    sources[SOURCE] = b"\xff\xfe\n"
    expected["files"][SOURCE]["sha256"] = hashlib.sha256(sources[SOURCE]).hexdigest()
    with pytest.raises(AiflowError):
        calculate(reports, sources, expected)


def assertion(ancestor: str, title: str) -> dict:
    return {
        "ancestorTitles": [ancestor],
        "duration": 0.125,
        "failureMessages": [],
        "fullName": ancestor + " " + title,
        "meta": {},
        "status": "passed",
        "tags": [],
        "title": title,
    }


def product_fixture(tmp_path: Path) -> tuple[dict, dict, dict, Path]:
    root = tmp_path / "checkout"
    tests = {
        ACCEPTANCE_FILE: b"// synthetic acceptance manifest bytes\n",
        INTEGRATION_FILE: b"// synthetic integration manifest bytes\n",
    }
    coverage, _sources, _catalog = coverage_fixture()
    files = []
    for name in tests:
        cases = [
            assertion(ancestor, title)
            for _category, filename, ancestor, title in SELECTED
            if filename == name
        ]
        files.append(
            {
                "assertionResults": cases,
                "endTime": 2.75,
                "message": "",
                "name": str(root / name),
                "startTime": 1.25,
                "status": "passed",
            }
        )
    snapshot = {
        key: 0
        for key in (
            "added",
            "filesAdded",
            "filesRemoved",
            "filesUnmatched",
            "filesUpdated",
            "matched",
            "total",
            "unchecked",
            "unmatched",
            "updated",
        )
    }
    snapshot.update(didUpdate=False, failure=False, filesRemovedList=[], uncheckedKeysByFile=[])
    report = {
        "coverageMap": deepcopy(coverage),
        "numFailedTestSuites": 0,
        "numFailedTests": 0,
        "numPassedTestSuites": 4,
        "numPassedTests": 5,
        "numPendingTestSuites": 0,
        "numPendingTests": 0,
        "numTodoTests": 0,
        "numTotalTestSuites": 4,
        "numTotalTests": 5,
        "snapshot": snapshot,
        "startTime": 0.5,
        "success": True,
        "testResults": files,
    }
    return report, tests, coverage, root


def product(report: dict, tests: dict, coverage: dict, root: Path) -> dict:
    return node.validate_node_product_tests(
        report, execution_root=root, tracked_tests=tests, expected_coverage=coverage
    )


def test_product_report_uses_exact_five_declarations_and_all_bound_test_sources(
    tmp_path: Path,
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    original = deepcopy((report, tests, coverage))
    result = product(report, tests, coverage, root)
    for category in ("acceptance", "integration"):
        assert result[category] == [
            {"file": filename, "full_name": ancestor + " " + title}
            for kind, filename, ancestor, title in SELECTED
            if kind == category
        ]
    assert (
        result["file_count"] == 2 and result["assertion_count"] == 5 and result["suite_count"] == 4
    )
    assert len(result["inventory_sha256"]) == 64
    changed = deepcopy(tests)
    changed[ACCEPTANCE_FILE] += b"// different bound source\n"
    assert (
        product(report, changed, coverage, root)["inventory_sha256"] != result["inventory_sha256"]
    )
    assert (report, tests, coverage) == original


def test_nonselected_parameterized_repetitions_are_all_preserved_and_counted(
    tmp_path: Path,
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    repeated = assertion("synthetic unit tests", "parameterized example")
    report["testResults"][0]["assertionResults"].extend(
        [deepcopy(repeated), deepcopy(repeated), deepcopy(repeated)]
    )
    report["numPassedTests"] = report["numTotalTests"] = 8
    result = product(report, tests, coverage, root)
    assert result["assertion_count"] == 8 and len(result["acceptance"]) == 2


def test_nonselected_long_titles_and_empty_ancestor_strings_retain_the_wire_protocol(
    tmp_path: Path,
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    case = assertion("", "parameter " + "x" * 4096)
    case["ancestorTitles"] = ["", "unit"]
    case["fullName"] = " unit " + case["title"]
    report["testResults"][0]["assertionResults"].append(case)
    report["numTotalTests"] = report["numPassedTests"] = 6
    assert product(report, tests, coverage, root)["assertion_count"] == 6


def test_passing_unchanged_snapshot_counters_do_not_require_zero_total(tmp_path: Path) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    report["snapshot"]["matched"] = report["snapshot"]["total"] = 2
    assert product(report, tests, coverage, root)["assertion_count"] == 5


def test_a_selected_full_name_cannot_be_recreated_by_splitting_its_ancestor(tmp_path: Path) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    case = report["testResults"][0]["assertionResults"][0]
    case["ancestorTitles"] = ACCEPTANCE_ANCESTOR.split(" ", 1)
    assert " ".join([*case["ancestorTitles"], case["title"]]) == case["fullName"]
    with pytest.raises(AiflowError):
        product(report, tests, coverage, root)


@pytest.mark.parametrize("invalid", [1, "true", None])
def test_report_success_is_the_exact_boolean_not_a_truthy_value(
    tmp_path: Path, invalid: object
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    report["success"] = invalid
    with pytest.raises(AiflowError):
        product(report, tests, coverage, root)


@pytest.mark.parametrize(
    "field,invalid",
    [
        ("failure", 0),
        ("didUpdate", 0),
        ("matched", True),
        ("filesRemovedList", {}),
        ("uncheckedKeysByFile", {}),
    ],
)
def test_snapshot_members_retain_their_exact_boolean_integer_and_list_roles(
    tmp_path: Path, field: str, invalid: object
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    report["snapshot"][field] = invalid
    with pytest.raises(AiflowError):
        product(report, tests, coverage, root)


@pytest.mark.parametrize(
    "fault",
    [
        "missing_selected",
        "duplicate_selected",
        "wrong_ancestor",
        "wrong_title",
        "wrong_fullname",
        "wrong_file",
        "missing_file",
        "duplicate_file",
        "extra_file",
        "foreign_path",
        "relative_path",
        "alias_path",
        "file_message",
        "file_status",
        "backward_time",
        "case_unknown",
        "file_unknown",
        "top_unknown",
        "invented_runtime_counter",
        "coverage_typed_difference",
        "meta",
        "tags",
        "failure_messages",
        "empty_title",
        "ancestor_type",
        "nonselected_failure",
        "success_false",
        "passed_count",
        "suite_count",
        "snapshot_unknown",
        "snapshot_unchecked",
        "snapshot_update",
        "snapshot_mismatch",
        "manifest_outside_suite",
        "manifest_not_bytes",
        "empty_files",
        "file_name_type",
        "assertion_container",
    ],
)
def test_product_parser_rejects_report_identity_status_and_shape_failures(
    tmp_path: Path, fault: str
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    file = report["testResults"][0]
    case = file["assertionResults"][0]
    if fault == "missing_selected":
        file["assertionResults"].pop(0)
        report["numPassedTests"] = report["numTotalTests"] = 4
    elif fault == "duplicate_selected":
        file["assertionResults"].append(deepcopy(case))
        report["numPassedTests"] = report["numTotalTests"] = 6
    elif fault == "wrong_ancestor":
        case["ancestorTitles"] = ["unrelated product"]
        case["fullName"] = "unrelated product " + case["title"]
    elif fault == "wrong_title":
        case["title"] += " changed"
        case["fullName"] += " changed"
    elif fault == "wrong_fullname":
        case["fullName"] = case["fullName"].replace(" ", "  ", 1)
    elif fault == "wrong_file":
        renamed = "tests/local/renamed.test.ts"
        tests[renamed] = tests.pop(ACCEPTANCE_FILE)
        file["name"] = str(root / renamed)
    elif fault == "missing_file":
        report["testResults"].pop()
    elif fault == "duplicate_file":
        report["testResults"].append(deepcopy(file))
    elif fault == "extra_file":
        extra = deepcopy(file)
        extra["name"] = str(root / "tests/local/foreign.test.ts")
        report["testResults"].append(extra)
    elif fault == "foreign_path":
        file["name"] = str(root.parent / ACCEPTANCE_FILE)
    elif fault == "relative_path":
        file["name"] = ACCEPTANCE_FILE
    elif fault == "alias_path":
        file["name"] = str(root) + "/tests/local/../local/personal-dot-integration.test.ts"
    elif fault == "file_message":
        file["message"] = "runtime failure"
    elif fault == "file_status":
        file["status"] = "failed"
    elif fault == "backward_time":
        file["endTime"] = 0
    elif fault == "case_unknown":
        case["location"] = {}
    elif fault == "file_unknown":
        file["errors"] = []
    elif fault == "top_unknown":
        report["schema_version"] = "invented"
    elif fault == "invented_runtime_counter":
        report["numRuntimeErrorTestSuites"] = 0
    elif fault == "coverage_typed_difference":
        report["coverageMap"][SOURCE]["s"]["0"] = True
    elif fault == "meta":
        case["meta"] = {"override": True}
    elif fault == "tags":
        case["tags"] = ["skip"]
    elif fault == "failure_messages":
        case["failureMessages"] = ["failed but marked passed"]
    elif fault == "empty_title":
        case["title"] = ""
    elif fault == "ancestor_type":
        case["ancestorTitles"] = "wrong container"
    elif fault == "nonselected_failure":
        bad = assertion("unit", "unselected")
        bad["status"] = "failed"
        file["assertionResults"].append(bad)
        report["numPassedTests"] = report["numTotalTests"] = 6
    elif fault == "success_false":
        report["success"] = False
    elif fault == "passed_count":
        report["numPassedTests"] = 4
    elif fault == "suite_count":
        report["numPassedTestSuites"] = 3
    elif fault == "snapshot_unknown":
        report["snapshot"]["unknown"] = 0
    elif fault == "snapshot_unchecked":
        report["snapshot"]["unchecked"] = 1
    elif fault == "snapshot_update":
        report["snapshot"]["didUpdate"] = True
    elif fault == "snapshot_mismatch":
        report["snapshot"]["total"] = 1
    elif fault == "manifest_outside_suite":
        tests["other/outside.test.ts"] = b"// not in fixed suite\n"
    elif fault == "manifest_not_bytes":
        tests[ACCEPTANCE_FILE] = "not bound bytes"
    elif fault == "empty_files":
        report["testResults"] = []
    elif fault == "file_name_type":
        file["name"] = True
    elif fault == "assertion_container":
        file["assertionResults"] = {}
    with pytest.raises(AiflowError):
        product(report, tests, coverage, root)


@pytest.mark.parametrize("status", ["failed", "pending", "skipped", "todo"])
def test_selected_product_status_must_be_passed_even_with_success_true(
    tmp_path: Path, status: str
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    report["testResults"][0]["assertionResults"][0]["status"] = status
    with pytest.raises(AiflowError):
        product(report, tests, coverage, root)


@pytest.mark.parametrize(
    "field",
    [
        "numFailedTestSuites",
        "numFailedTests",
        "numPendingTestSuites",
        "numPendingTests",
        "numTodoTests",
    ],
)
def test_nonpassing_global_counters_cannot_hide_behind_success_true(
    tmp_path: Path, field: str
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    report[field] = 1
    with pytest.raises(AiflowError):
        product(report, tests, coverage, root)


@pytest.mark.parametrize("invalid", [True, 1.0, -1, 2**53, None])
def test_report_counters_require_bounded_integers(tmp_path: Path, invalid: object) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    report["numTotalTests"] = invalid
    with pytest.raises(AiflowError):
        product(report, tests, coverage, root)


@pytest.mark.parametrize("where", ["startTime", "file_start", "file_end", "duration"])
@pytest.mark.parametrize("invalid", [-1, float("nan"), float("inf"), True, None, 10**400])
def test_report_timings_require_finite_nonnegative_numbers(
    tmp_path: Path, where: str, invalid: object
) -> None:
    report, tests, coverage, root = product_fixture(tmp_path)
    if where == "startTime":
        report["startTime"] = invalid
    elif where == "duration":
        report["testResults"][0]["assertionResults"][0]["duration"] = invalid
    else:
        report["testResults"][0]["startTime" if where == "file_start" else "endTime"] = invalid
    with pytest.raises(AiflowError):
        product(report, tests, coverage, root)
