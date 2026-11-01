"""Synthetic public contracts for the proposed closed Node 3.1 profile.

The line-coverage validator consumes already-bound, normalized originals, including
the independent zero-hit map's complete executable-line set for every source.
These tests establish arithmetic and rejection behavior, never runtime provenance
or a second TypeScript parser.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys

# ruff: noqa: E402 -- Candidate imports follow the source-absence-only guard.
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file() and (parent / "src/aiflow/__init__.py").is_file()
)
NODE_SOURCE = ROOT / "src/aiflow/node_verification.py"
try:
    NODE_SOURCE_INFO = NODE_SOURCE.lstat()
except FileNotFoundError:
    pytest.skip(
        "Node implementation is absent: test-preparation baseline only, not feature PASS",
        allow_module_level=True,
    )
if (
    not stat.S_ISREG(NODE_SOURCE_INFO.st_mode)
    or getattr(NODE_SOURCE_INFO, "st_file_attributes", 0)
    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    or not NODE_SOURCE.resolve().is_relative_to(ROOT.resolve())
):
    raise ImportError("Node source is not a regular checkout module")

import aiflow
import aiflow.node_verification as node
import aiflow.verification_service as verification_service
from aiflow.errors import AiflowError
from aiflow.evidence import validate_node_evidence
from aiflow.node_execution import _engine as _transaction_engine
from aiflow.node_execution import _source as _transaction_source
from aiflow.policy import POLICY_FILES, load_policy_bundle
from aiflow.verification import (
    V0_CHECK_IDS,
    V1_CHECK_IDS,
    V2_CHECK_IDS,
    VerificationContext,
    parse_verification_plan,
)
from aiflow.verification_level import determine_verification_level

if (
    aiflow.__file__ is None
    or Path(aiflow.__file__).resolve() != (ROOT / "src/aiflow/__init__.py").resolve()
    or node.__file__ is None
    or Path(node.__file__).resolve() != NODE_SOURCE.resolve()
):
    raise ImportError("Node contracts were not imported from this tested checkout")

LOW_RISK = {
    "mechanical": True,
    "behavior_changed": False,
    "code_modified": False,
    "interaction_scope": "local",
    "regression_risk": False,
    "error_detectability": "high",
}
V0 = (
    ("contract", 30),
    ("scope", 30),
    ("smoke", 30),
    ("node_build", 300),
    ("node_check", 600),
    ("diff_whitespace", 30),
)
SOURCE = "src/local/example.ts"


@pytest.fixture(scope="module")
def node_policy_seed_bytes() -> tuple[tuple[str, bytes], ...]:
    seeds = []
    checks = [{"id": name, "required": True, "timeout_seconds": timeout} for name, timeout in V0]
    for name in POLICY_FILES:
        document = yaml.safe_load((ROOT / ".ai/policy" / name).read_text(encoding="utf-8"))
        document["policy_version"] = "3.1.0"
        if name == "verification-levels.yaml":
            document = {
                "schema_version": "1.0",
                "policy_version": "3.1.0",
                "policy_kind": "verification_levels",
                "profile": {"id": "agent-bridge-node", "revision": 1},
                "levels": [
                    {"id": "V0", "checks": deepcopy(checks)},
                    {
                        "id": "V1",
                        "checks": [
                            *deepcopy(checks),
                            {"id": "ts_coverage", "required": True, "timeout_seconds": 600},
                            {
                                "id": "ts_total_lines",
                                "required": True,
                                "timeout_seconds": 30,
                                "threshold": 85,
                            },
                            {
                                "id": "ts_diff_lines",
                                "required": True,
                                "timeout_seconds": 30,
                                "threshold": 90,
                            },
                        ],
                    },
                ],
            }
        # Preserve the host newline conversion of the original Path.write_text.
        data = yaml.safe_dump(document, sort_keys=False).replace("\n", os.linesep).encode("utf-8")
        seeds.append((name, data))
    return tuple(seeds)


@pytest.fixture
def node_policy_directory(
    tmp_path: Path, node_policy_seed_bytes: tuple[tuple[str, bytes], ...]
) -> Path:
    directory = tmp_path / ".ai/policy"
    directory.mkdir(parents=True)
    for name, data in node_policy_seed_bytes:
        (directory / name).write_bytes(data)
    return directory


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_closed_profile_preserves_required_level(
    tmp_path: Path, node_policy_directory: Path, level: str
) -> None:
    policy = load_policy_bundle(tmp_path, policy_directory=node_policy_directory)
    unit = {"decision_unit_id": "DU-001", "change_characteristics": deepcopy(LOW_RISK)}
    if level == "V1":
        unit["change_characteristics"].update(code_modified=True, mechanical=False)
    elif level == "V2":
        unit["verification_requirements"] = {"targeted_mutation_required": True}
    decision = determine_verification_level(unit, policy)
    assert decision.level == level
    assert bool(decision.blocking_reasons) is (level == "V2")


@pytest.mark.parametrize(
    "variant",
    [
        "lower_total",
        "lower_diff",
        "wrong_revision",
        "missing_check",
        "extra_command",
        "environment",
    ],
)
def test_closed_profile_rejects_quality_or_execution_drift(
    tmp_path: Path, node_policy_directory: Path, variant: str
) -> None:
    path = node_policy_directory / "verification-levels.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    checks = document["levels"][1]["checks"]
    if variant == "lower_total":
        checks[-2]["threshold"] = 84
    elif variant == "lower_diff":
        checks[-1]["threshold"] = 89
    elif variant == "wrong_revision":
        document["profile"]["revision"] = 2
    elif variant == "missing_check":
        checks.pop()
    elif variant == "extra_command":
        checks[3]["command"] = ["arbitrary-shell"]
    else:
        checks[3]["environment"] = {"NODE_OPTIONS": "--import=unreviewed"}
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(AiflowError):
        load_policy_bundle(tmp_path, policy_directory=node_policy_directory)


def source(lines: int) -> bytes:
    return "".join(f"export const value{index} = {index};\n" for index in range(lines)).encode()


def report(path: str, hits: list[int]) -> dict:
    return {
        "path": path,
        "statementMap": {
            str(index): {
                "start": {"line": index + 1, "column": 0},
                "end": {"line": index + 1, "column": 24},
            }
            for index in range(len(hits))
        },
        "s": {str(index): count for index, count in enumerate(hits)},
        "fnMap": {},
        "f": {},
        "branchMap": {},
        "b": {},
    }


def validate(hits: list[int], changed: list[int]) -> None:
    # Proposed small pure API: production binds these originals before calling it.
    node.validate_node_line_coverage(
        {SOURCE: report(SOURCE, hits)},
        tracked_sources={SOURCE: source(len(hits))},
        expected_executable_lines={SOURCE: list(range(1, len(hits) + 1))},
        changed_lines={SOURCE: changed},
        deleted_sources=(),
    )


def test_exact_total_and_changed_line_boundaries_are_accepted() -> None:
    validate([1] * 85 + [0] * 15, [1, 2, 3, 4, 5, 6, 7, 8, 9, 86])


@pytest.mark.parametrize("covered,total", [(84, 100), (8499, 10000)])
def test_total_coverage_below_85_is_rejected_without_rounding(covered: int, total: int) -> None:
    with pytest.raises(AiflowError):
        validate([1] * covered + [0] * (total - covered), [1])


@pytest.mark.parametrize("covered,total", [(8, 9), (8999, 10000)])
def test_changed_line_coverage_below_90_is_rejected_without_rounding(
    covered: int, total: int
) -> None:
    with pytest.raises(AiflowError):
        validate([1] * covered + [0] * (total - covered), list(range(1, total + 1)))


def test_same_line_uses_maximum_statement_hits_not_statement_percentage() -> None:
    data = report(SOURCE, [0, 1])
    data["statementMap"]["1"]["start"]["line"] = 1
    data["statementMap"]["1"]["end"]["line"] = 1
    data["statementMap"]["1"]["start"]["column"] = 25
    data["statementMap"]["1"]["end"]["column"] = 49
    node.validate_node_line_coverage(
        {SOURCE: data},
        tracked_sources={SOURCE: b"export const value0 = 0; export const value1 = 1;\n"},
        expected_executable_lines={SOURCE: [1]},
        changed_lines={SOURCE: [1]},
        deleted_sources=(),
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_v8_columns_use_utf16_units_and_exclude_line_endings(newline: str) -> None:
    data = report(SOURCE, [0, 1])
    # The astral character occupies UTF-16 columns 21..23. The two statements
    # end at columns 25 and 49, although the complete line has 48 code points.
    data["statementMap"] = {
        "0": {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": 25}},
        "1": {"start": {"line": 1, "column": 26}, "end": {"line": 1, "column": 49}},
    }
    contents = ('export const face = "😀"; export const value = 1;' + newline).encode("utf-8")
    node.validate_node_line_coverage(
        {SOURCE: data},
        tracked_sources={SOURCE: contents},
        expected_executable_lines={SOURCE: [1]},
        changed_lines={SOURCE: [1]},
        deleted_sources=(),
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("variant", ["split_surrogate", "past_content", "utf8_byte_column"])
def test_v8_columns_reject_split_characters_and_newline_or_byte_offsets(
    newline: str, variant: str
) -> None:
    data = report(SOURCE, [1])
    data["statementMap"]["0"]["end"]["column"] = 49
    if variant == "split_surrogate":
        data["statementMap"]["0"]["start"]["column"] = 22
    else:
        data["statementMap"]["0"]["end"]["column"] = 50 if variant == "past_content" else 51
    contents = ('export const face = "😀"; export const value = 1;' + newline).encode("utf-8")
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: data},
            tracked_sources={SOURCE: contents},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={SOURCE: [1]},
            deleted_sources=(),
        )


def test_invalid_utf8_source_is_unknown_mapping_not_zero_executable_lines() -> None:
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: report(SOURCE, [1])},
            tracked_sources={SOURCE: b'export const value = "\xff";\r\n'},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={},
            deleted_sources=(),
        )


def _coverage_with_auxiliary_range(role: str) -> tuple[dict, dict]:
    data = report(SOURCE, [1])
    location = {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": None}}
    if role == "statement":
        data["statementMap"]["0"] = location
    elif role.startswith("fn_"):
        data["fnMap"] = {"0": {role.removeprefix("fn_"): location}}
    elif role == "branch_loc":
        data["branchMap"] = {"0": {"loc": location}}
    else:
        data["branchMap"] = {"0": {"locations": [location]}}
    return data, location


@pytest.mark.parametrize(
    "role", ["statement", "fn_decl", "fn_loc", "branch_loc", "branch_locations"]
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_bound_converter_null_end_uses_original_utf16_line_end_without_mutation(
    role: str, newline: str
) -> None:
    contents = ('export const face = "😀";' + newline).encode()
    data, location = _coverage_with_auxiliary_range(role)
    data["statementMap"]["0"]["end"]["column"] = 25
    location["end"]["column"] = None
    # UTF-16 offset 25 is beyond the line's 24 Python characters. Deriving a
    # character count instead would reverse this valid range ending at line end.
    location["start"]["column"] = 25
    original = deepcopy(data)
    result = node.validate_node_line_coverage(
        {SOURCE: data},
        tracked_sources={SOURCE: contents},
        expected_executable_lines={SOURCE: [1]},
        changed_lines={SOURCE: [1]},
        deleted_sources=(),
    )
    assert result["total"] == {"covered": 1, "executable": 1, "threshold": 85}
    assert result["changed"] == {
        "covered": 1,
        "executable": 1,
        "threshold": 90,
        "applicability": "applicable",
    }
    assert data == original


@pytest.mark.parametrize(
    "role", ["statement", "fn_decl", "fn_loc", "branch_loc", "branch_locations"]
)
@pytest.mark.parametrize(
    "field,value",
    [
        ("start_column", None),
        ("end_line", None),
        ("end_line", True),
        ("end_line", 1.0),
        ("end_line", 0),
        ("end_line", 999),
        ("end_column", False),
        ("end_column", 24.0),
        ("end_column", float("inf")),
        ("end_column", float("nan")),
        ("end_column", "Infinity"),
        ("end_column", -1),
    ],
)
def test_null_end_exception_preserves_strict_coordinate_types_and_bounds(
    role: str, field: str, value: object
) -> None:
    data, location = _coverage_with_auxiliary_range(role)
    position, coordinate = field.split("_")
    location[position][coordinate] = value
    with pytest.raises(AiflowError) as caught:
        node.validate_node_line_coverage(
            {SOURCE: data},
            tracked_sources={SOURCE: source(1)},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={},
            deleted_sources=(),
        )
    assert caught.value.code == "NODE_COVERAGE_INVALID"


@pytest.mark.parametrize("map_name", ["fnMap", "branchMap"])
@pytest.mark.parametrize("nesting", ["direct", "unknown", "list", "shared_object"])
def test_unknown_nested_end_key_never_receives_converter_null_exception(
    map_name: str, nesting: str
) -> None:
    data, location = _coverage_with_auxiliary_range(
        "fn_loc" if map_name == "fnMap" else "branch_loc"
    )
    unknown = deepcopy(location)
    if nesting == "direct":
        data[map_name]["0"] = unknown
    elif nesting == "unknown":
        data[map_name]["0"]["unknown"] = unknown
    elif nesting == "list":
        data[map_name]["0"]["unknown"] = [unknown]
    else:
        # A pure caller sharing objects must not transfer a known path's role.
        data[map_name]["0"]["unknown"] = location
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: data},
            tracked_sources={SOURCE: source(1)},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={},
            deleted_sources=(),
        )


@pytest.mark.parametrize(
    "role", ["statement", "fn_decl", "fn_loc", "branch_loc", "branch_locations"]
)
def test_null_end_does_not_allow_reversed_source_ranges(role: str) -> None:
    data, location = _coverage_with_auxiliary_range(role)
    location["start"]["line"] = 2
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: data},
            tracked_sources={SOURCE: source(2)},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={},
            deleted_sources=(),
        )


@pytest.mark.parametrize("missing_report", [False, True])
def test_unimported_tracked_source_is_not_excluded_from_total(missing_report: bool) -> None:
    unused = "src/local/unimported.ts"
    reports = {SOURCE: report(SOURCE, [1])}
    if not missing_report:
        reports[unused] = report(unused, [0] * 99)
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            reports,
            tracked_sources={SOURCE: source(1), unused: source(99)},
            expected_executable_lines={SOURCE: [1], unused: list(range(1, 100))},
            changed_lines={SOURCE: [1]},
            deleted_sources=(),
        )


@pytest.mark.parametrize(
    "variant",
    ["missing_statement", "out_of_source", "unknown_statement", "negative", "bool", "wrong_path"],
)
def test_unknown_or_inconsistent_source_mapping_never_becomes_empty_diff(variant: str) -> None:
    data = report(SOURCE, [1])
    if variant == "missing_statement":
        data["statementMap"] = {}
    elif variant == "out_of_source":
        data["statementMap"]["0"]["start"]["line"] = 999
    elif variant == "unknown_statement":
        data["s"]["unknown"] = 1
    elif variant == "negative":
        data["s"]["0"] = -1
    elif variant == "bool":
        data["s"]["0"] = True
    else:
        data["path"] = "../outside.ts"
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: data},
            tracked_sources={SOURCE: source(1)},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={},
            deleted_sources=(),
        )


@pytest.mark.parametrize("path", ["scripts/build.mjs", "scripts/native.ps1", "scripts/owner.cs"])
def test_uncovered_production_language_change_is_unverified(path: str) -> None:
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: report(SOURCE, [1])},
            tracked_sources={SOURCE: source(1)},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={path: [1]},
            deleted_sources=(),
        )


def test_known_empty_changed_line_set_is_distinct_from_missing_mapping() -> None:
    node.validate_node_line_coverage(
        {SOURCE: report(SOURCE, [1])},
        tracked_sources={SOURCE: source(1)},
        expected_executable_lines={SOURCE: [1]},
        changed_lines={},
        deleted_sources=("src/local/deleted.ts",),
    )
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {},
            tracked_sources={SOURCE: source(1)},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={},
            deleted_sources=(),
        )


@pytest.mark.parametrize("variant", ["missing_line", "extra_line"])
def test_nonempty_report_must_match_independent_executable_line_set(variant: str) -> None:
    contents = source(3)
    expected = [1, 2, 3]
    hits = [1, 1]
    if variant == "extra_line":
        contents = source(2) + b"export type Example = number;\n"
        expected = [1, 2]
        hits = [1, 1, 1]
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: report(SOURCE, hits)},
            tracked_sources={SOURCE: contents},
            expected_executable_lines={SOURCE: expected},
            changed_lines={},
            deleted_sources=(),
        )


def test_independent_executable_map_cannot_omit_a_tracked_file() -> None:
    other = "src/local/other.ts"
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: report(SOURCE, [1]), other: report(other, [1])},
            tracked_sources={SOURCE: source(1), other: source(1)},
            expected_executable_lines={SOURCE: [1]},
            changed_lines={},
            deleted_sources=(),
        )


def test_independent_executable_map_is_a_required_argument() -> None:
    with pytest.raises(TypeError):
        node.validate_node_line_coverage(
            {SOURCE: report(SOURCE, [1])},
            tracked_sources={SOURCE: source(1)},
            changed_lines={},
            deleted_sources=(),
        )


@pytest.mark.parametrize(
    "lines,hits",
    [
        ([1, 1], [1]),
        ([2, 1], [1, 1]),
        ([True], [1]),
        ([1.0], [1]),
        ([0], [1]),
        ([-1], [1]),
        ([999], [1]),
    ],
)
def test_independent_executable_lines_are_sorted_unique_in_source_integers(
    lines: list, hits: list[int]
) -> None:
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {SOURCE: report(SOURCE, hits)},
            tracked_sources={SOURCE: source(len(hits))},
            expected_executable_lines={SOURCE: lines},
            changed_lines={},
            deleted_sources=(),
        )


def test_type_only_source_requires_explicit_empty_executable_set() -> None:
    # An independently mapped type-only file remains a known 1-file/0-line input.
    # This does not assert a fabricated 100% value for an empty denominator.
    node.validate_node_line_coverage(
        {SOURCE: report(SOURCE, [])},
        tracked_sources={SOURCE: b"export type Example = number;\n"},
        expected_executable_lines={SOURCE: []},
        changed_lines={SOURCE: [1]},
        deleted_sources=(),
    )


@pytest.mark.parametrize("variant", ["missing_map", "missing_report", "claimed_executable"])
def test_type_only_source_cannot_be_assumed_from_missing_or_inconsistent_data(
    variant: str,
) -> None:
    reports = {SOURCE: report(SOURCE, [])}
    expected = {SOURCE: []}
    if variant == "missing_map":
        expected = {}
    elif variant == "missing_report":
        reports = {}
    else:
        expected = {SOURCE: [1]}
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            reports,
            tracked_sources={SOURCE: b"export type Example = number;\n"},
            expected_executable_lines=expected,
            changed_lines={},
            deleted_sources=(),
        )


@pytest.mark.parametrize("partial", [False, True])
def test_forged_passed_evidence_cannot_replace_bound_required_results(partial: bool) -> None:
    forged = {
        "schema_version": "3.1",
        "mode": "local",
        "conclusion": "passed",
        "verification_level": "V1",
        "checks": [{"check_id": "ts_total_lines", "required": True, "status": "passed"}],
        "partial": partial,
    }
    with pytest.raises(AiflowError):
        validate_node_evidence(forged, require_passed=True)


@pytest.mark.parametrize("options", [{}, {"finalize": True}, {"abandon": True}])
def test_node_ci_rejects_before_recovery_or_execution(
    tmp_path: Path, node_policy_directory: Path, monkeypatch: pytest.MonkeyPatch, options: dict
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Unsupported Node CI reached a recovery or execution boundary")

    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(verification_service, "read_task_record_strict", forbidden)
    monkeypatch.setattr(verification_service, "_execute_plan", forbidden)
    with pytest.raises(AiflowError) as caught:
        verification_service.verify_task(tmp_path, "TASK-0001", ci=True, **options)
    assert caught.value.code == "VERIFY_NODE_CI_UNSUPPORTED"


def test_native_python_policy_plans_remain_unchanged() -> None:
    policy = load_policy_bundle(ROOT)
    digest = policy.sha256
    context = VerificationContext(
        ROOT, "TASK-0001", "a" * 40, "b" * 40, sys.executable, "node-test"
    )
    for level, expected in (("V0", V0_CHECK_IDS), ("V1", V1_CHECK_IDS), ("V2", V2_CHECK_IDS)):
        plan = parse_verification_plan(
            policy, context, level=level, tool_available=lambda _argv: True
        )
        assert tuple(check.check_id for check in plan.checks) == expected
        if level != "V0":
            check = next(item for item in plan.checks if item.check_id == "diff_coverage")
            assert check.threshold == 90
            assert any("tools/ci/check_coverage.py" in part for part in check.argv)
    assert load_policy_bundle(ROOT).sha256 == digest


def _evidence_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


@pytest.fixture
def node_public_evidence(tmp_path: Path, node_policy_directory: Path):
    """Synthetic observations from the real fixed plan, never runtime provenance."""
    from aiflow.node_execution import _public_execution, node_execution_contract
    from aiflow.verification import NodePlanBindings

    policy = load_policy_bundle(tmp_path, policy_directory=node_policy_directory)
    owned = tmp_path / "owned"
    context = VerificationContext(
        tmp_path,
        "TASK-0001",
        "a" * 40,
        "b" * 40,
        sys.executable,
        "node-evidence",
        node_bindings=NodePlanBindings(
            str(tmp_path / "roles/node.exe"),
            str(tmp_path / "roles/npm-cli.js"),
            str(tmp_path / "roles/git.exe"),
            owned,
            owned / "user.npmrc",
            owned / "global.npmrc",
            owned / "coverage",
            owned / "expected.json",
            owned / "source.json",
        ),
    )

    def build(level="V1"):
        plan = parse_verification_plan(policy, context, level=level)
        receipt = {
            "returncode": 0,
            "timed_out": False,
            "duration_ms": 1,
            "stdout_size": 0,
            "stderr_size": 0,
            "stdout_sha256": hashlib.sha256(b"").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "stdout_overflow": False,
            "stderr_overflow": False,
            "cleanup": "confirmed",
            "execution_error": False,
        }
        checks = [
            {
                "check_id": check.check_id,
                "required": True,
                "status": "passed",
                "executions": [
                    _public_execution(execution, receipt, context)
                    for execution in plan.executions
                    if check.check_id in execution.check_ids
                ],
            }
            for check in plan.checks
        ]
        binding = {
            "profile": {"id": "agent-bridge-node", "revision": 1},
            "subject_tree": "c" * 40,
            "prepared": {
                "ref": "logs/node-prepared/" + "d" * 64 + "/prepared.json",
                "size": 1,
                "sha256": "d" * 64,
            },
            "run": {"ref": "logs/node-evidence/node/run.json", "size": 1, "sha256": "e" * 64},
            "materials_sha256": "f" * 64,
            "semantic_contract_sha256": "1" * 64,
            "execution_contract_sha256": _evidence_hash(node_execution_contract(plan, context)),
            "environment_sha256": "2" * 64,
            "coverage": None
            if level == "V0"
            else {
                "scope_files": 2,
                "total": {"covered": 85, "executable": 100, "threshold": 85},
                "changed": {
                    "covered": 9,
                    "executable": 10,
                    "threshold": 90,
                    "applicability": "applicable",
                },
                "method": node.COVERAGE_METHOD,
            },
        }
        return {
            "schema_version": "3.1",
            "task_id": "TASK-0001",
            "decision_unit_ids": ["DU-001"],
            "repository_id": "11111111-2222-3333-4444-555555555555",
            "branch": "codex/synthetic",
            "base_commit": "a" * 40,
            "subject_commit": "b" * 40,
            "spec_sha256": "3" * 64,
            "policy_sha256": "4" * 64,
            "classification_input_sha256": "5" * 64,
            "verification_level": level,
            "mode": "local",
            "checks": checks,
            "unverified_scenarios": [],
            "conclusion": "passed",
            "generated_at": "2026-10-31T00:00:00Z",
            "reproduce_command": [
                "python",
                "-m",
                "aiflow",
                "verify",
                "TASK-0001",
                "--actor",
                "synthetic-agent",
                "--node-materials",
                "d" * 64,
            ],
            "node_binding": binding,
            "node_binding_sha256": _evidence_hash(binding),
        }

    return build


@pytest.mark.parametrize("level", ["V0", "V1"])
def test_public_evidence_matches_real_plan_and_closed_schema(node_public_evidence, level) -> None:
    from aiflow.contracts import require_valid_contract

    evidence = node_public_evidence(level)
    before = deepcopy(evidence)
    validate_node_evidence(evidence, require_passed=True)
    require_valid_contract("evidence", evidence)
    assert evidence == before
    assert sum(len(row["executions"]) for row in evidence["checks"]) == (8 if level == "V0" else 10)


def _replace_evidence_value(evidence, path, value):
    target = evidence
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    if path[0] == "node_binding":
        evidence["node_binding_sha256"] = _evidence_hash(evidence["node_binding"])


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), "3.0"),
        (("mode",), "ci"),
        (("verification_level",), "V2"),
        (("conclusion",), "provisional"),
        (("task_id",), "TASK-../1"),
        (("decision_unit_ids",), []),
        (("decision_unit_ids",), ["DU-001", "DU-001"]),
        (("decision_unit_ids",), [1]),
        (("repository_id",), "bad"),
        (("generated_at",), "2026-10-31"),
        (("generated_at",), "2026-10-31T00:00:00"),
        (("generated_at",), "2026-99-99T00:00:00Z"),
        (("branch",), "bad\nbranch"),
        (("branch",), "\ud800"),
        (("base_commit",), "A" * 40),
        (("subject_commit",), 1),
        (("policy_sha256",), "x" * 64),
        (("node_binding_sha256",), "0" * 64),
        (("node_binding", "profile", "revision"), True),
        (("node_binding", "profile", "revision"), 1.0),
        (("node_binding", "profile", "id"), "arbitrary"),
        (("node_binding", "subject_tree"), "x" * 40),
        (("node_binding", "materials_sha256"), "A" * 64),
        (("node_binding", "execution_contract_sha256"), "0" * 64),
        (("node_binding", "prepared", "size"), True),
        (("node_binding", "prepared", "size"), 1.0),
        (("node_binding", "prepared", "size"), 0),
        (("node_binding", "prepared", "size"), 65537),
        (("node_binding", "prepared", "ref"), "https://example.com/prepared.json"),
        (("node_binding", "run", "ref"), "logs/../node/run.json"),
        (("node_binding", "run", "ref"), "logs/CON/node/run.json"),
        (("node_binding", "run", "ref"), "logs/alias./node/run.json"),
        (("node_binding", "run", "size"), 16777217),
        (("node_binding", "run", "sha256"), "not-a-digest"),
        (("reproduce_command",), ["/private/python", "-m", "aiflow"]),
        (("reproduce_command", 6), "../actor"),
        (("reproduce_command", 6), "bad\nactor"),
        (("unverified_scenarios",), ["fabricated"]),
        (("checks", 0, "required"), 1),
        (("checks", 0, "status"), "unknown"),
        (("checks", 0, "check_id"), "smoke"),
        (("checks", 0, "executions"), []),
        (("checks", 0, "executions", 0, "execution_id"), "EXEC-002"),
        (("checks", 0, "executions", 0, "argv_template"), ["arbitrary"]),
        (("checks", 0, "executions", 0, "argv_template"), [True]),
        (("checks", 0, "executions", 0, "cwd_role"), "isolated"),
        (("checks", 0, "executions", 0, "timeout_seconds"), 30.0),
        (("checks", 0, "executions", 0, "timeout_seconds"), True),
        (("checks", 0, "executions", 0, "timeout_seconds"), 31),
        (("checks", 0, "executions", 0, "returncode"), False),
        (("checks", 0, "executions", 0, "returncode"), 0.0),
        (("checks", 0, "executions", 0, "returncode"), -1),
        (("checks", 0, "executions", 0, "returncode"), None),
        (("checks", 0, "executions", 0, "duration_ms"), 0.0),
        (("checks", 0, "executions", 0, "duration_ms"), -1),
        (("checks", 0, "executions", 0, "timed_out"), 0),
        (("checks", 0, "executions", 0, "stdout_overflow"), 0),
        (("checks", 0, "executions", 0, "stderr_overflow"), 0),
        (("checks", 0, "executions", 0, "execution_error"), 0),
        (("checks", 0, "executions", 0, "cleanup"), "maybe"),
        (("checks", 0, "executions", 0, "stdout", "bytes"), True),
        (("checks", 0, "executions", 0, "stdout", "bytes"), 0.0),
        (("checks", 0, "executions", 0, "stdout", "bytes"), 1048577),
        (("checks", 0, "executions", 0, "stdout", "sha256"), "0" * 64),
        (
            ("checks", 0, "executions", 0, "stdout", "raw_ref"),
            "logs/other/node/raw/EXEC-001/stdout.raw",
        ),
        (
            ("checks", 0, "executions", 0, "stderr", "log_ref"),
            "logs/node-evidence/node/raw/EXEC-001/stdout.log",
        ),
        (("node_binding", "coverage", "scope_files"), 0),
        (("node_binding", "coverage", "scope_files"), True),
        (("node_binding", "coverage", "scope_files"), 2.0),
        (("node_binding", "coverage", "method"), "invented"),
        (("node_binding", "coverage", "total", "threshold"), 84),
        (("node_binding", "coverage", "total", "threshold"), 85.0),
        (("node_binding", "coverage", "total", "executable"), 0),
        (("node_binding", "coverage", "total", "covered"), 101),
        (("node_binding", "coverage", "total", "covered"), 84),
        (("node_binding", "coverage", "changed", "covered"), 8),
        (("node_binding", "coverage", "changed", "executable"), 101),
        (("node_binding", "coverage", "changed", "applicability"), "not_applicable"),
        (("node_binding", "coverage"), None),
    ],
)
def test_public_evidence_rejects_independent_contract_mutations(
    node_public_evidence, path, value
) -> None:
    evidence = node_public_evidence()
    _replace_evidence_value(evidence, path, value)
    with pytest.raises(AiflowError):
        validate_node_evidence(evidence)


@pytest.mark.parametrize(
    "path",
    [
        (),
        ("node_binding",),
        ("node_binding", "profile"),
        ("node_binding", "coverage"),
        ("checks", 0),
        ("checks", 0, "executions", 0),
        ("checks", 0, "executions", 0, "stdout"),
    ],
)
def test_public_evidence_objects_are_closed(node_public_evidence, path) -> None:
    evidence = node_public_evidence()
    target = evidence
    for key in path:
        target = target[key]
    target["unknown"] = True
    with pytest.raises(AiflowError):
        validate_node_evidence(evidence)


@pytest.mark.parametrize("prefix", [0, 1, 5, 6, 8, 9, 10])
def test_failed_public_evidence_retains_only_an_observed_execution_prefix(
    node_public_evidence, prefix
) -> None:
    evidence = node_public_evidence()
    remaining = prefix
    for check in evidence["checks"]:
        expected = len(check["executions"])
        check["executions"] = check["executions"][:remaining]
        remaining = max(0, remaining - expected)
        check["status"] = (
            "passed" if expected and len(check["executions"]) == expected else "unverified"
        )
    evidence["node_binding"]["coverage"] = None
    if prefix == 10:
        evidence["checks"][6]["status"] = "failed"
    evidence["unverified_scenarios"] = [
        row["check_id"] for row in evidence["checks"] if row["status"] == "unverified"
    ]
    evidence["conclusion"] = "failed"
    evidence["node_binding_sha256"] = _evidence_hash(evidence["node_binding"])
    validate_node_evidence(evidence)
    with pytest.raises(AiflowError, match="not passed"):
        validate_node_evidence(evidence, require_passed=True)


@pytest.mark.parametrize("mode", ["nonzero", "unknown", "timeout", "overflow", "not_started"])
def test_execution_failure_blocks_following_public_executions(node_public_evidence, mode) -> None:
    evidence = node_public_evidence()
    execution = evidence["checks"][0]["executions"][0]
    if mode == "nonzero":
        execution["returncode"] = 7
    elif mode == "unknown":
        execution["cleanup"] = "unknown"
        execution["execution_error"] = True
    elif mode == "timeout":
        execution["timed_out"] = True
    elif mode == "overflow":
        execution["stdout_overflow"] = True
        execution["stdout"]["bytes"] = 1048576
        execution["stdout"]["sha256"] = "a" * 64
    else:
        execution["cleanup"] = "not_started"
        execution["returncode"] = None
        execution["execution_error"] = True
    evidence["checks"][0]["status"] = "failed"
    for check in evidence["checks"][1:]:
        check["executions"] = []
        check["status"] = "unverified"
    evidence["node_binding"]["coverage"] = None
    evidence["node_binding_sha256"] = _evidence_hash(evidence["node_binding"])
    evidence["unverified_scenarios"] = [row["check_id"] for row in evidence["checks"][1:]]
    evidence["conclusion"] = "failed"
    validate_node_evidence(evidence)
    # A process after the observed failure cannot be smuggled into the same receipt.
    next_execution = node_public_evidence()["checks"][1]["executions"]
    evidence["checks"][1]["executions"] = next_execution
    with pytest.raises(AiflowError):
        validate_node_evidence(evidence)


def test_no_changed_executable_lines_are_explicitly_not_applicable(node_public_evidence) -> None:
    evidence = node_public_evidence()
    evidence["node_binding"]["coverage"]["changed"].update(
        covered=0,
        executable=0,
        applicability="not_applicable",
    )
    evidence["node_binding_sha256"] = _evidence_hash(evidence["node_binding"])
    validate_node_evidence(evidence, require_passed=True)


def test_public_node_validation_does_not_read_write_or_execute(
    node_public_evidence, monkeypatch
) -> None:
    import aiflow.evidence as module

    evidence = node_public_evidence()

    def forbidden(*_args, **_kwargs):
        pytest.fail("Pure public validation attempted an I/O or execution boundary")

    monkeypatch.setattr(module, "require_valid_contract", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(verification_service, "verify_task", forbidden)
    validate_node_evidence(evidence, require_passed=True)


def test_node_save_validates_before_any_write(node_public_evidence, tmp_path, monkeypatch) -> None:
    import aiflow.evidence as module

    evidence = node_public_evidence()
    destination = tmp_path / "node-evidence.json"
    archive = tmp_path / "node-archive.json"
    module.save_evidence(destination, evidence, archive_path=archive)
    assert json.loads(destination.read_text()) == json.loads(archive.read_text()) == evidence

    def forbidden(*_args, **_kwargs):
        pytest.fail("Invalid Node evidence reached a persistence boundary")

    monkeypatch.setattr(module, "atomic_write_json", forbidden)
    _replace_evidence_value(evidence, ("node_binding", "profile", "revision"), 1.0)
    with pytest.raises(AiflowError):
        module.save_evidence(destination, evidence, archive_path=archive)


@pytest.mark.parametrize(
    "variant",
    [
        "extra-top",
        "native-v2",
        "extra-binding",
        "native-check",
        "missing-check",
        "extra-check",
        "V0-coverage",
    ],
)
def test_node_schema_is_separate_and_closed(node_public_evidence, variant) -> None:
    from aiflow.contracts import require_valid_contract

    evidence = node_public_evidence("V0" if variant == "V0-coverage" else "V1")
    if variant == "extra-top":
        evidence["arbitrary"] = True
    elif variant == "native-v2":
        evidence["phase"] = "final"
    elif variant == "extra-binding":
        evidence["node_binding"]["arbitrary"] = True
    elif variant == "native-check":
        evidence["checks"][0]["category"] = "contract"
    elif variant == "missing-check":
        evidence["checks"].pop()
    elif variant == "extra-check":
        evidence["checks"].append(deepcopy(evidence["checks"][0]))
    else:
        evidence["node_binding"]["coverage"] = node_public_evidence()["node_binding"]["coverage"]
    with pytest.raises(AiflowError):
        require_valid_contract("evidence", evidence)


@pytest.fixture
def synthetic_installed_engine(tmp_path, monkeypatch):
    """Controlled metadata over real temporary files, only for rejection-path tests."""
    import aiflow.node_execution as runtime

    site = tmp_path / "site-packages"
    monkeypatch.delitem(sys.modules, "sitecustomize", raising=False)
    monkeypatch.delitem(sys.modules, "usercustomize", raising=False)
    monkeypatch.setattr(
        runtime,
        "_engine_site_facts",
        lambda: {
            "prefix": str(site.parent),
            "base_prefix": str(site.parent),
            "site_roots": [str(site)],
            "active_site_roots": [str(site)],
            "enable_user_site": False,
        },
        raising=False,
    )
    names = {
        "aiflow": "aiflow",
        "PyYAML": "yaml",
        "jsonschema": "jsonschema",
        "attrs": "attrs",
        "referencing": "referencing",
        "jsonschema-specifications": "jsonschema_specifications",
        "rpds-py": "rpds",
        "typing_extensions": "typing_extensions",
    }
    distributions = {}
    modules = {}
    for name, module in names.items():
        relative = Path(module) / "__init__.py"
        path = site / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(b"# controlled unit fixture; never imported\n")
        distributions[name] = SimpleNamespace(
            files=[relative],
            metadata={"Name": name},
            version="1.0",
            locate_file=lambda value, base=site: base / value,
            read_text=lambda _name: None,
        )
        modules[module] = SimpleNamespace(
            __file__=str(path), __spec__=SimpleNamespace(origin=str(path))
        )
    original_distribution = runtime.importlib.metadata.distribution
    original_import = runtime.importlib.import_module

    def distribution(name):
        if name in distributions:
            value = distributions[name]
            if value is None:
                raise runtime.importlib.metadata.PackageNotFoundError(name)
            return value
        return original_distribution(name)

    monkeypatch.setattr(runtime.importlib.metadata, "distribution", distribution)
    monkeypatch.setattr(
        runtime.importlib,
        "import_module",
        lambda name: modules[name] if name in modules else original_import(name),
    )
    monkeypatch.setattr(aiflow, "__file__", str(site / "aiflow/__init__.py"))
    return runtime, site, distributions, modules


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_py",
        "extra_pyc",
        "editable",
        "missing_dependency",
        "missing_inventory",
        "loaded_origin",
        "loaded_spec",
        "engine_origin",
        "entry_budget",
        "byte_budget",
        "optional_missing_then_bad_origin",
    ],
)
def test_ordinary_engine_rejects_incomplete_or_mutated_installation(
    synthetic_installed_engine, mutation
) -> None:
    runtime, site, distributions, modules = synthetic_installed_engine
    budget = None
    if mutation in {"extra_py", "extra_pyc"}:
        path = (
            site
            / "aiflow"
            / ("unexpected.py" if mutation == "extra_py" else "__pycache__/unexpected.pyc")
        )
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"unrecorded installation bytes")
    elif mutation == "editable":
        distributions["aiflow"].read_text = lambda _name: '{"dir_info":{"editable":true}}'
    elif mutation == "missing_dependency":
        distributions["PyYAML"] = None
    elif mutation == "missing_inventory":
        distributions["PyYAML"].files = []
    elif mutation == "loaded_origin":
        modules["yaml"].__file__ = str(site / "outside.py")
    elif mutation == "loaded_spec":
        modules["yaml"].__spec__ = None
    elif mutation in {"engine_origin", "optional_missing_then_bad_origin"}:
        aiflow.__file__ = str(site / "jsonschema/__init__.py")
        if mutation.startswith("optional"):
            distributions["typing_extensions"] = None
    elif mutation == "entry_budget":
        budget = [1, 4096]
    else:
        budget = [4096, 1]
    with pytest.raises(AiflowError) as caught:
        runtime._engine(budget=budget)
    if mutation in {"extra_py", "extra_pyc"}:
        assert "unrecorded file" in str(caught.value)
    elif mutation in {"entry_budget", "byte_budget"}:
        assert "Combined material inventory" in str(caught.value)
    elif mutation in {"engine_origin", "optional_missing_then_bad_origin"}:
        assert "does not belong" in str(caught.value)


def _negative_process_original(runtime, directory, argv, cwd, environment, stdout):
    """Synthetic observations can test rejection, never establish a feature PASS."""
    directory.mkdir(parents=True)
    observed = dict.fromkeys(
        (
            "created_suspended",
            "assigned",
            "initial_membership",
            "resumed",
            "job_empty",
            "stdout_eof",
            "stderr_eof",
            "closed",
        ),
        True,
    )
    observed.update(process_id=123, creation_time_filetime=456, terminate_requested=False)
    receipt = {
        "returncode": 0,
        "timed_out": False,
        "stdout_overflow": False,
        "stderr_overflow": False,
        "cleanup": "confirmed",
        "execution_error": False,
        "receipt": observed,
        "stdout_sha256": runtime._sha(stdout),
        "stderr_sha256": runtime._sha(b""),
        "stdout_size": len(stdout),
        "stderr_size": 0,
        "argv": list(argv),
        "cwd": str(cwd),
        "environment_sha256": runtime._sha(runtime._canonical(environment)),
        "timeout_seconds": 30,
        "duration_ms": 0,
    }
    for name, data in (
        ("stdout.raw", stdout),
        ("stdout.log", stdout),
        ("stderr.raw", b""),
        ("stderr.log", b""),
        ("receipt.json", runtime._canonical(receipt)),
    ):
        (directory / name).write_bytes(data)
    return receipt


@pytest.fixture
def negative_material_originals(tmp_path, monkeypatch):
    """Real file inventories, with upstream Git/host trust seams held constant."""
    import aiflow.node_execution as runtime

    payload = tmp_path / ".ai/tasks/TASK-0001/logs/node-payload/preparation"
    node_root = payload / "node"
    npm_root = node_root / "node_modules/npm"
    (npm_root / "bin").mkdir(parents=True)
    package = {"name": "npm", "version": runtime.VERSIONS["npm"]}
    (npm_root / "package.json").write_bytes(runtime._canonical(package))
    # Non-executable synthetic x64 PE header for negative material-role probes only.
    pe_header = bytearray(128)
    pe_header[:2] = b"MZ"
    pe_header[60:64] = (64).to_bytes(4, "little")
    pe_header[64:68] = b"PE\0\0"
    pe_header[68:70] = (0x8664).to_bytes(2, "little")
    pe_header[88:90] = (0x20B).to_bytes(2, "little")
    (node_root / "node.exe").write_bytes(pe_header)
    for path in (node_root / "npm.cmd", npm_root / "bin/npm.cmd", npm_root / "bin/npm-cli.js"):
        path.write_bytes(b"fixed synthetic fixture bytes")
    deps = payload / "dependencies/node_modules"
    packages = {}
    for name, version in (
        ("vitest", runtime.VERSIONS["vitest"]),
        ("@vitest/coverage-v8", runtime.VERSIONS["vitest"]),
        ("vite", runtime.VERSIONS["vite"]),
    ):
        folder = deps / name
        folder.mkdir(parents=True)
        (folder / "package.json").write_bytes(
            runtime._canonical({"name": name, "version": version})
        )
        packages["node_modules/" + name] = {
            "version": version,
            "resolved": "https://registry.npmjs.org/synthetic/-/synthetic.tgz",
            "integrity": "sha512-synthetic",
        }
    source = {"files": [], "subject": "synthetic"}
    engine = {"distributions": []}
    host = {"git": {"path": str(tmp_path / "Git/cmd/git.exe")}}
    monkeypatch.setattr(runtime, "_source", lambda *_args, **_kwargs: source)
    monkeypatch.setattr(
        runtime, "_source_contract", lambda *_args, **_kwargs: ({}, {"packages": packages})
    )
    monkeypatch.setattr(runtime, "_engine", lambda **_kwargs: engine)
    monkeypatch.setattr(runtime, "_host_tools", lambda **_kwargs: host)
    inventory = runtime._inventory(node_root)
    manifests = {
        "source.json": deepcopy(source),
        "node.json": {"runtime": inventory, "selected": "node.exe"},
        "npm.json": {
            "runtime_sha256": runtime._sha(runtime._canonical(inventory)),
            "entry": "node_modules/npm/bin/npm-cli.js",
            "shim": "npm.cmd",
            "package": package,
        },
        "dependencies.json": runtime._inventory(deps),
        "engine.json": deepcopy(engine),
        "host-tools.json": deepcopy(host),
        "preflight.json": {},
    }
    prepared = {
        "payload": {"path": str(payload)},
        "binding": {"subject_commit": "b" * 40, "profile": runtime.PROFILE},
    }
    preflight_root = payload.parent.parent / "node-preflight-preparation"
    environment = runtime._environment(
        node_root / "node.exe", payload / "dependencies", preflight_root, Path(host["git"]["path"])
    )
    for name, argv, expected in (
        ("node", (str(node_root / "node.exe"), "--version"), "v" + runtime.VERSIONS["node"]),
        (
            "npm",
            (str(node_root / "node.exe"), str(npm_root / "bin/npm-cli.js"), "--version"),
            runtime.VERSIONS["npm"],
        ),
    ):
        directory = preflight_root / name
        receipt = _negative_process_original(
            runtime, directory, argv, payload, environment, expected.encode() + b"\n"
        )
        manifests["preflight.json"][name] = {
            "directory": str(directory),
            "receipt": receipt,
            "expected": expected,
        }
    return runtime, payload, prepared, manifests


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_role",
        "missing_role",
        "dependencies_extra_root",
        "node_selected",
        "node_extra_field",
        "node_outside_root",
        "dependencies_outside_root",
        "npm_extra_field",
        "npm_digest",
        "npm_entry",
        "npm_shim",
        "npm_name",
        "npm_version",
        "npm_package",
        "npm_shim_bytes",
        "runtime_neighbor",
        "missing_node",
        "runtime_drift",
        "dependencies_drift",
        "source_drift",
        "engine_drift",
        "host_drift",
        "preflight_missing",
        "preflight_extra",
        "preflight_directory",
        "preflight_expected",
        "preflight_timeout_bool",
        "preflight_timeout_float",
        "preflight_extra_field",
        "preflight_argv",
        "preflight_cwd",
        "preflight_env",
        "preflight_returncode_bool",
        "preflight_size_float",
        "preflight_size_negative",
        "preflight_duration_negative",
        "preflight_boolean",
        "preflight_eof",
        "preflight_pid",
        "preflight_filetime",
        "preflight_terminated",
        "preflight_missing_raw",
        "preflight_changed_raw",
        "preflight_changed_log",
        "preflight_wrong_version",
    ],
)
def test_material_recheck_rejects_role_and_preflight_rebindings(
    negative_material_originals, mutation
) -> None:
    runtime, payload, prepared, manifests = negative_material_originals
    node_manifest = manifests["node.json"]
    npm = manifests["npm.json"]
    preflights = manifests["preflight.json"]
    node_probe = preflights["node"]
    receipt = node_probe["receipt"]
    probe_dir = Path(node_probe["directory"])
    if mutation == "extra_role":
        (payload / "unowned").mkdir()
    elif mutation == "missing_role":
        prepared["payload"]["path"] = str(payload / "node")
    elif mutation == "dependencies_extra_root":
        (payload / "dependencies/unowned").mkdir()
    elif mutation == "node_selected":
        node_manifest["selected"] = "other.exe"
    elif mutation == "node_extra_field":
        node_manifest["extra"] = True
    elif mutation == "node_outside_root":
        node_manifest["runtime"]["root"] = str(payload)
    elif mutation == "dependencies_outside_root":
        manifests["dependencies.json"]["root"] = str(payload)
    elif mutation == "npm_extra_field":
        npm["extra"] = True
    elif mutation == "npm_digest":
        npm["runtime_sha256"] = "0" * 64
    elif mutation in {"npm_entry", "npm_shim"}:
        npm[mutation.removeprefix("npm_")] = "../outside"
    elif mutation in {"npm_name", "npm_version"}:
        npm["package"][mutation.removeprefix("npm_")] = "wrong"
        (payload / "node/node_modules/npm/package.json").write_bytes(
            runtime._canonical(npm["package"])
        )
    elif mutation == "npm_package":
        npm["package"] = {"name": "other", "version": "0"}
    elif mutation == "npm_shim_bytes":
        (payload / "node/npm.cmd").write_bytes(b"different shim")
    elif mutation == "runtime_neighbor":
        node_manifest["runtime"]["entries"].append({"path": "outside.exe", "kind": "file"})
        npm["runtime_sha256"] = runtime._sha(runtime._canonical(node_manifest["runtime"]))
    elif mutation == "missing_node":
        node_manifest["runtime"]["entries"] = [
            row for row in node_manifest["runtime"]["entries"] if row["path"] != "node.exe"
        ]
        npm["runtime_sha256"] = runtime._sha(runtime._canonical(node_manifest["runtime"]))
    elif mutation == "runtime_drift":
        executable = payload / "node/node.exe"
        changed = bytearray(executable.read_bytes())
        changed[-1] = 1
        executable.write_bytes(changed)
    elif mutation == "dependencies_drift":
        (payload / "dependencies/node_modules/vite/unknown.js").write_bytes(
            b"extra dependency file"
        )
    elif mutation in {"source_drift", "engine_drift", "host_drift"}:
        manifests[
            {
                "source_drift": "source.json",
                "engine_drift": "engine.json",
                "host_drift": "host-tools.json",
            }[mutation]
        ]["extra"] = True
    elif mutation == "preflight_missing":
        del preflights["npm"]
    elif mutation == "preflight_extra":
        preflights["other"] = {}
    elif mutation == "preflight_directory":
        node_probe["directory"] = str(payload)
    elif mutation == "preflight_expected":
        node_probe["expected"] = "0"
    elif mutation == "preflight_timeout_bool":
        receipt["timeout_seconds"] = True
    elif mutation == "preflight_timeout_float":
        receipt["timeout_seconds"] = 30.0
    elif mutation == "preflight_extra_field":
        node_probe["extra"] = True
    elif mutation == "preflight_argv":
        receipt["argv"] = ["unbound.exe"]
    elif mutation == "preflight_cwd":
        receipt["cwd"] = str(payload / "node")
    elif mutation == "preflight_env":
        receipt["environment_sha256"] = "0" * 64
    elif mutation == "preflight_returncode_bool":
        receipt["returncode"] = False
    elif mutation == "preflight_size_float":
        receipt["stdout_size"] = float(receipt["stdout_size"])
    elif mutation == "preflight_size_negative":
        receipt["stdout_size"] = -1
    elif mutation == "preflight_duration_negative":
        receipt["duration_ms"] = -1
    elif mutation == "preflight_boolean":
        receipt["timed_out"] = 0
    elif mutation == "preflight_eof":
        receipt["receipt"]["stdout_eof"] = False
    elif mutation == "preflight_pid":
        receipt["receipt"]["process_id"] = True
    elif mutation == "preflight_filetime":
        receipt["receipt"]["creation_time_filetime"] = 0
    elif mutation == "preflight_terminated":
        receipt["cleanup"] = "unknown"
        receipt["execution_error"] = True
    elif mutation == "preflight_missing_raw":
        (probe_dir / "stdout.raw").unlink()
    elif mutation == "preflight_changed_raw":
        (probe_dir / "stdout.raw").write_bytes(b"replaced")
    elif mutation == "preflight_changed_log":
        (probe_dir / "stdout.log").write_bytes(b"rewritten display")
    elif mutation == "preflight_wrong_version":
        data = b"v0.0.0\n"
        (probe_dir / "stdout.raw").write_bytes(data)
        (probe_dir / "stdout.log").write_bytes(data)
        receipt["stdout_size"], receipt["stdout_sha256"] = len(data), runtime._sha(data)
    (probe_dir / "receipt.json").write_bytes(runtime._canonical(receipt))
    with pytest.raises((AiflowError, FileNotFoundError)) as caught:
        runtime._check_materials(payload.parents[5], prepared, manifests)
    assert isinstance(caught.value, AiflowError)
    if mutation == "preflight_missing_raw":
        assert caught.value.code == "NODE_MATERIALS_INVALID"
        assert "missing or unreadable" in str(caught.value)
    if mutation == "preflight_wrong_version":
        assert "preflight version changed" in str(caught.value)
    elif mutation == "preflight_changed_log":
        assert "display log differs" in str(caught.value)
    elif mutation == "engine_drift":
        assert caught.value.code == "NODE_ENGINE_DRIFT"
    elif mutation in {"source_drift", "runtime_drift", "dependencies_drift", "host_drift"}:
        assert caught.value.code == "NODE_MATERIALS_DRIFT"


@pytest.fixture
def governance_originals(tmp_path):
    import aiflow.node_execution as runtime

    task = tmp_path / ".ai/tasks/TASK-0001"
    (task / "reviews").mkdir(parents=True)
    (task / "review-contexts").mkdir()
    context = {
        "schema_version": "1.0",
        "review_stage": "design",
        "task_id": "TASK-0001",
        "decision_unit_ids": ["DU-001"],
        "repository_id": "11111111-2222-3333-4444-555555555555",
        "branch": "codex/synthetic",
        "base_commit": "a" * 40,
        "spec_sha256": "b" * 64,
        "policy_sha256": "c" * 64,
        "classification_input_sha256": "d" * 64,
        "content": {},
    }
    digest = runtime._sha(runtime._canonical(context))
    context["context_sha256"] = digest
    review = {
        "schema_version": "1.0",
        "review_id": "REV-0001",
        "revision": 1,
        "task_id": "TASK-0001",
        "review_stage": "design",
        "reviewer": "synthetic-reviewer",
        "recorded_at": "2026-10-31T00:00:00Z",
        "context_sha256": digest,
        "outcome": "APPROVE",
        "summary": "Synthetic audit original",
        "findings": [],
    }
    approval = json.loads((ROOT / "tests/fixtures/contracts/valid/approval.json").read_text())
    review_path = task / "reviews/REV-0001-r0001.json"
    context_path = task / f"review-contexts/{digest}.json"
    review_path.write_bytes(runtime._canonical(review))
    context_path.write_bytes(runtime._canonical(context))
    (task / "approvals.json").write_bytes(runtime._canonical([approval]))
    events = [
        {
            "event_type": "review_recorded",
            "payload": {
                "review_id": "REV-0001",
                "revision": 1,
                "review_stage": "design",
                "context_sha256": digest,
            },
        }
    ]
    return runtime, task, events, review, context, review_path, context_path


def test_governance_paths_are_derived_from_validated_exact_audit_originals(
    governance_originals,
) -> None:
    runtime, task, events, _review, _context, review_path, context_path = governance_originals
    (task / "reviews/unrelated.json").write_bytes(b"unknown file must remain protected")
    snapshot = runtime._governance_snapshot(task.parents[2], "TASK-0001", events)
    prefix = ".ai/tasks/TASK-0001/"
    assert set(snapshot["immutable"]) == {
        prefix + "reviews/" + review_path.name,
        prefix + "review-contexts/" + context_path.name,
    }
    assert prefix + "reviews/unrelated.json" not in snapshot["paths"]
    assert all(
        snapshot["immutable"][str(path.relative_to(task.parents[2])).replace("\\", "/")]
        == runtime._sha(path.read_bytes())
        for path in (review_path, context_path)
    )
    assert len(snapshot["approvals"]) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "event_id",
        "event_digest",
        "event_bool_revision",
        "event_float_revision",
        "event_zero_revision",
        "event_missing_stage",
        "event_wrong_stage",
        "review_task",
        "review_id",
        "review_revision",
        "review_digest",
        "context_task",
        "context_content",
        "approval_object",
        "approval_invalid",
        "missing_review",
        "missing_context",
    ],
)
def test_governance_originals_reject_rebinding_or_rewrite(governance_originals, mutation) -> None:
    runtime, task, events, review, context, review_path, context_path = governance_originals
    if mutation == "event_id":
        events[0]["payload"]["review_id"] = "../outside"
    elif mutation == "event_digest":
        events[0]["payload"]["context_sha256"] = "not-a-digest"
    elif mutation == "event_bool_revision":
        events[0]["payload"]["revision"] = True
    elif mutation == "event_float_revision":
        events[0]["payload"]["revision"] = 1.0
    elif mutation == "event_zero_revision":
        events[0]["payload"]["revision"] = 0
    elif mutation == "event_missing_stage":
        events[0]["payload"].pop("review_stage")
    elif mutation == "event_wrong_stage":
        events[0]["payload"]["review_stage"] = "implementation"
    elif mutation.startswith("review_"):
        key = {
            "review_task": "task_id",
            "review_id": "review_id",
            "review_revision": "revision",
            "review_digest": "context_sha256",
        }[mutation]
        review[key] = {
            "task_id": "TASK-0002",
            "review_id": "REV-0002",
            "revision": 2,
            "context_sha256": "0" * 64,
        }[key]
        review_path.write_bytes(runtime._canonical(review))
    elif mutation.startswith("context_"):
        context["task_id" if mutation == "context_task" else "content"] = (
            "TASK-0002" if mutation == "context_task" else {"changed": True}
        )
        context_path.write_bytes(runtime._canonical(context))
    elif mutation == "approval_object":
        (task / "approvals.json").write_bytes(b"{}")
    elif mutation == "approval_invalid":
        (task / "approvals.json").write_bytes(b"[{}]")
    elif mutation == "missing_review":
        review_path.unlink()
    else:
        context_path.unlink()
    with pytest.raises((AiflowError, FileNotFoundError)):
        runtime._governance_snapshot(task.parents[2], "TASK-0001", events)


def _controlled_git(root, *arguments):
    return (
        subprocess.run(("git", *arguments), cwd=root, check=True, capture_output=True, timeout=30)
        .stdout.decode()
        .strip()
    )


@pytest.fixture
def governance_advancement(tmp_path, monkeypatch):
    import aiflow.node_execution as runtime

    _controlled_git(tmp_path, "init", "--quiet")
    _controlled_git(tmp_path, "config", "user.name", "Synthetic Test")
    _controlled_git(tmp_path, "config", "user.email", "synthetic@example.invalid")
    _controlled_git(tmp_path, "config", "core.autocrlf", "false")
    task = tmp_path / ".ai/tasks/TASK-0001"
    task.mkdir(parents=True)
    (task / "approvals.json").write_bytes(b"[]")
    (tmp_path / "protected.txt").write_bytes(b"protected input\n")
    _controlled_git(tmp_path, "add", ".")
    _controlled_git(tmp_path, "commit", "--quiet", "-m", "Synthetic baseline")
    before = {
        "identity": runtime._identity(tmp_path.lstat()),
        "files": [
            {
                "path": "protected.txt",
                "sha256": runtime._sha((tmp_path / "protected.txt").read_bytes()),
            }
        ],
        "task": {"task_id": "TASK-0001"},
        "git": runtime._git_state(tmp_path),
        # This seam exercises governance deltas; real metadata drift uses the
        # independently enumerated filesystem cases in test_node_v0_outputs.
        "metadata": [],
        "git_audit": runtime._git_audit_inputs(tmp_path),
        "events": [{"event_type": "verification_passed", "payload": {}}],
        "governance": {
            "paths": [".ai/tasks/TASK-0001/approvals.json"],
            "immutable": {"review": "a" * 64},
            "approvals": [{"bound": "original"}],
        },
    }
    after = deepcopy(before)
    monkeypatch.setattr(runtime, "_root_snapshot", lambda *_args: after)
    return runtime, tmp_path, task, before, after


def test_legal_governance_append_keeps_old_facts_and_protected_inputs(
    governance_advancement,
) -> None:
    runtime, root, task, before, after = governance_advancement
    (task / "approvals.json").write_bytes(b"[{},{}]")
    _controlled_git(root, "add", ".ai/tasks/TASK-0001/approvals.json")
    _controlled_git(root, "commit", "--quiet", "-m", "Synthetic governance append")
    after["git"] = runtime._git_state(root)
    after["git_audit"] = runtime._git_audit_inputs(root)
    after["events"].extend([{"event_type": "code_approved"}, {"event_type": "review_recorded"}])
    after["governance"]["approvals"].append({"bound": "appended"})
    after["governance"]["immutable"]["new-review"] = "b" * 64
    runtime._check_root(root, "TASK-0001", before)
    assert (root / "protected.txt").read_bytes() == b"protected input\n"


@pytest.mark.parametrize(
    "mutation",
    [
        "identity",
        "files",
        "task",
        "review_rewrite",
        "approval_rewrite",
        "event_rewrite",
        "unapproved_event",
        "committed_protected",
        "staged_protected",
        "divergent_head",
    ],
)
def test_root_advancement_rejects_rewrites_and_non_governance_git_changes(
    governance_advancement, mutation
) -> None:
    runtime, root, _task, before, after = governance_advancement
    if mutation == "identity":
        after["identity"]["inode"] += 1
    elif mutation == "files":
        after["files"][0]["sha256"] = "0" * 64
    elif mutation == "task":
        after["task"]["subject_commit"] = "new-subject"
    elif mutation == "review_rewrite":
        after["governance"]["immutable"]["review"] = "0" * 64
    elif mutation == "approval_rewrite":
        after["governance"]["approvals"][0]["bound"] = "rewritten"
    elif mutation == "event_rewrite":
        after["events"][0]["payload"] = {"rewritten": True}
    elif mutation == "unapproved_event":
        after["events"].append({"event_type": "task_started"})
    else:
        if mutation == "divergent_head":
            _controlled_git(root, "checkout", "--orphan", "synthetic-divergent")
        (root / "protected.txt").write_bytes(b"changed input\n")
        _controlled_git(root, "add", "protected.txt")
        if mutation != "staged_protected":
            _controlled_git(root, "commit", "--quiet", "-m", "Synthetic forbidden advancement")
        after["git"] = runtime._git_state(root)
    with pytest.raises(AiflowError):
        runtime._check_root(root, "TASK-0001", before)


@pytest.mark.parametrize("boundary", ["open", "read", "final", "grew"])
def test_bounded_file_read_detects_identity_changes_at_every_boundary(
    tmp_path, monkeypatch, boundary
) -> None:
    import aiflow.node_execution as runtime

    path = tmp_path / "material.bin"
    path.write_bytes(b"data")
    original_identity = runtime._identity
    count = 0

    def identity(info):
        nonlocal count
        count += 1
        result = original_identity(info)
        if count == {"open": 1, "read": 3, "final": 5}.get(boundary):
            result["inode"] += 1
        return result

    if boundary == "grew":
        original_fstat = runtime.os.fstat

        def fstat(descriptor):
            nonlocal count
            info = original_fstat(descriptor)
            count += 1
            if count == 1:
                with path.open("ab") as stream:
                    stream.write(b"growth beyond initial size")
            return info

        monkeypatch.setattr(runtime.os, "fstat", fstat)
    else:
        monkeypatch.setattr(runtime, "_identity", identity)
    with pytest.raises(AiflowError):
        runtime._read(path, limit=4)


@pytest.mark.parametrize(
    "fault",
    [
        "npm_unknown",
        "npm_version",
        "runtime_drift",
        "json_limit",
        "selector_limit",
        "publish_write",
    ],
)
def test_preparation_late_failure_never_publishes_a_usable_selection(
    negative_material_originals, monkeypatch, fault
) -> None:
    runtime, old_payload, _prepared, _manifests = negative_material_originals
    payload = old_payload.with_name("late-preparation")
    old_payload.rename(payload)
    root = payload.parents[5]
    monkeypatch.setattr(
        runtime,
        "_binding",
        lambda *_args: ({"subject_commit": "b" * 40, "profile": runtime.PROFILE}, None),
    )
    calls = []

    def process(argv, *, cwd, environment, timeout, output):
        calls.append(output.name)
        data = (
            "v" + runtime.VERSIONS["node"] if output.name == "node" else runtime.VERSIONS["npm"]
        ).encode() + b"\n"
        if fault == "npm_version" and output.name == "npm":
            data = b"0.0.0\n"
        receipt = _negative_process_original(runtime, output, argv, cwd, environment, data)
        if fault == "npm_unknown" and output.name == "npm":
            receipt.update(returncode=None, cleanup="unknown", execution_error=True)
            (output / "receipt.json").write_bytes(runtime._canonical(receipt))
        if fault == "runtime_drift" and output.name == "npm":
            executable = payload / "node/node.exe"
            executable.write_bytes(executable.read_bytes() + b"changed after preflight")
        return receipt

    monkeypatch.setattr(runtime, "_process", process)
    if fault == "json_limit":
        monkeypatch.setattr(runtime, "MAX_JSON_BYTES", 1)
    elif fault == "selector_limit":
        monkeypatch.setattr(runtime, "MAX_PREPARED_BYTES", 1)
    elif fault == "publish_write":
        write = runtime._write_new

        def failed_write(path, data):
            if path.name == "prepared.json":
                raise OSError("controlled publication failure")
            write(path, data)

        monkeypatch.setattr(runtime, "_write_new", failed_write)
    with pytest.raises((AiflowError, OSError)):
        runtime.prepare_node_materials(root, "TASK-0001", payload_root=payload)
    assert calls == ["node", "npm"]
    preflight = payload.parent.parent / "node-preflight-late-preparation"
    assert all((preflight / name / "receipt.json").is_file() for name in calls)
    assert not list((payload.parent.parent / "node-prepared").glob("*/prepared.json"))
    assert (payload / "node/node.exe").is_file()
    if fault == "publish_write":
        assert list((payload.parent.parent / "node-prepared").glob("*/source.json"))


@pytest.fixture
def negative_node_transaction(negative_material_originals, node_policy_directory, monkeypatch):
    """Real Git/source/copies/raw files; fake process prefix MUST end in failure.

    The trusted task/material and Windows API seams are controlled unit inputs.
    These fabricated ownership observations never establish an ordinary-wheel PASS.
    """
    import aiflow.node_execution as runtime
    import aiflow.storage as storage
    import aiflow.task_service as task_service
    from aiflow.decision_units import classification_input_digest, parse_decision_units
    from aiflow.evidence import EvidenceFacts
    from aiflow.specification import specification_digest

    _runtime, payload, _prepared, manifests = negative_material_originals
    root = payload.parents[5]
    task_id = "TASK-0001"
    task_dir = root / ".ai/tasks" / task_id
    (task_dir / "approvals.json").write_bytes(b"[]")
    spec_text = "# Controlled negative transaction specification\n"
    (task_dir / "spec.md").write_text(spec_text, encoding="utf-8")
    repository_id = "11111111-2222-3333-4444-555555555555"
    (root / ".ai/repository-id").write_text(repository_id, encoding="utf-8")
    (root / ".gitignore").write_bytes(b"/.ai/tasks/*/logs/\n")
    (root / "src/local").mkdir(parents=True)
    source_file = root / "src/local/example.ts"
    source_file.write_bytes(b"export const value = 0;\n")
    config = {
        "compilerOptions": {
            "outDir": "dist",
            "rootDir": "src/local",
            "sourceMap": True,
            "declaration": True,
            "declarationMap": True,
        }
    }
    (root / "tsconfig.json").write_bytes(runtime._canonical(config))
    _controlled_git(root, "init", "--quiet")
    _controlled_git(root, "checkout", "-b", "codex/synthetic-transaction")
    _controlled_git(root, "config", "user.name", "Synthetic Test")
    _controlled_git(root, "config", "user.email", "synthetic@example.invalid")
    _controlled_git(root, "config", "core.autocrlf", "false")
    _controlled_git(root, "add", ".")
    _controlled_git(root, "commit", "--quiet", "-m", "Synthetic transaction baseline")
    base = _controlled_git(root, "rev-parse", "HEAD")
    source_file.write_bytes(b"export const value = 1;\n")
    _controlled_git(root, "add", "src/local/example.ts")
    _controlled_git(root, "commit", "--quiet", "-m", "Synthetic transaction subject")
    subject = _controlled_git(root, "rev-parse", "HEAD")
    source = _transaction_source(root, subject)
    manifests["source.json"] = source
    manifests["host-tools.json"] = {
        "python": {"path": sys.executable},
        "git": {"path": shutil.which("git")},
    }
    bundle = load_policy_bundle(root, policy_directory=node_policy_directory)
    binding = {
        "repository_id": repository_id,
        "task_id": task_id,
        "branch": "codex/synthetic-transaction",
        "base_commit": base,
        "subject_commit": subject,
        "subject_tree": source["subject_tree"],
        "spec_sha256": specification_digest(spec_text),
        "policy_sha256": bundle.sha256,
        "classification_input_sha256": "b" * 64,
        "profile": runtime.PROFILE,
    }
    unit = json.loads((ROOT / "tests/fixtures/contracts/valid/decision-unit.json").read_text())
    record = SimpleNamespace(
        task={
            **binding,
            "decision_units": [unit],
            "goal": "Controlled failure transaction",
            "allowed_scope": ["src/local/example.ts"],
            "forbidden_actions": [],
            "frozen_spec_sha256": binding["spec_sha256"],
        },
        events=[],
    )
    binding["classification_input_sha256"] = classification_input_digest(
        record.task,
        parse_decision_units(record.task),
    )
    monkeypatch.setattr(task_service, "read_task_record_strict", lambda *_args: record)
    settings = {"level": "V0", "fault": "last_nonzero", "material_checks": 0, "calls": []}
    original_read_task_json = storage.read_task_json

    def classification(root_arg, task_arg, name, **kwargs):
        if name == "classification.json":
            return {
                "effective_verification_level": settings["level"],
                "classifications": [{"verification_level": settings["level"]}],
                "subject_commit": subject,
                "policy_sha256": bundle.sha256,
                "classification_input_sha256": binding["classification_input_sha256"],
            }
        return original_read_task_json(root_arg, task_arg, name, **kwargs)

    monkeypatch.setattr(storage, "read_task_json", classification)

    def material_check(*_args):
        settings["material_checks"] += 1
        if settings["fault"] == "late_materials" and settings["material_checks"] == 2:
            raise runtime._error("Controlled final material drift", "UNIT_MATERIALS_DRIFT")

    monkeypatch.setattr(runtime, "_check_materials", material_check)
    encoded = {name: runtime._canonical(manifests[name]) for name in runtime.MANIFEST_NAMES}
    prepared = {
        "schema_version": "1.0",
        "kind": "aiflow-node-prepared-3.1",
        "binding": binding,
        "payload": {"path": str(payload), "identity": runtime._identity(payload.lstat())},
        "manifests": [
            {"name": name, "size": len(data), "sha256": runtime._sha(data)}
            for name, data in encoded.items()
        ],
        "versions": runtime.VERSIONS,
        "semantic_contract_sha256": runtime.SEMANTIC_CONTRACT_SHA256,
    }
    prepared_data = runtime._canonical(prepared)
    selector = runtime._sha(prepared_data)
    selected = task_dir / "logs/node-prepared" / selector
    selected.mkdir(parents=True)
    for name, data in {**encoded, "prepared.json": prepared_data}.items():
        (selected / name).write_bytes(data)

    def process(argv, *, cwd, environment, timeout, output):
        name = output.name
        settings["calls"].append(name)
        if name.startswith("setup-"):
            completed = subprocess.run(
                argv, cwd=cwd, env=environment, capture_output=True, timeout=30
            )
            assert completed.returncode == 0, completed.stderr.decode(errors="replace")
        if name == "EXEC-004":
            for relative in runtime._dist_paths(cwd, source):
                path = cwd / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic build bytes for a failing transaction\n")
        receipt = _negative_process_original(
            runtime, output, argv, cwd, environment, b"negative transaction process seam\n"
        )
        receipt["timeout_seconds"] = timeout
        if settings["fault"] == "clone_unknown" and name == "setup-clone":
            receipt.update(returncode=None, cleanup="unknown", execution_error=True)
        elif settings["fault"] == "checkout_nonzero" and name == "setup-checkout":
            receipt["returncode"] = 17
        elif settings["fault"].startswith("collision_") and name == "setup-checkout":
            (cwd / settings["fault"].removeprefix("collision_")).mkdir()
        elif settings["fault"] == "checkout_source" and name == "setup-checkout":
            (cwd / "src/local/example.ts").write_bytes(b"changed before source binding\n")
        elif settings["fault"] == "json_limit_final" and name == "EXEC-008":
            monkeypatch.setattr(runtime, "MAX_JSON_BYTES", 1)
        if settings["fault"] == "last_nonzero" and name == "EXEC-008":
            receipt["returncode"] = 17
        elif settings["fault"] == "unknown" and name == "EXEC-004":
            receipt.update(returncode=None, cleanup="unknown", execution_error=True)
        elif settings["fault"] == "helper_unknown" and name == "EXEC-010":
            receipt.update(returncode=None, cleanup="unknown", execution_error=True)
        elif settings["fault"] == "source_drift" and name == "EXEC-005":
            (cwd / "src/local/example.ts").write_bytes(b"changed protected checkout input\n")
        (output / "receipt.json").write_bytes(runtime._canonical(receipt))
        return receipt

    monkeypatch.setattr(runtime, "_process", process)

    def execute(fault="last_nonzero", level="V0"):
        settings.update(level=level, fault=fault, material_checks=0, calls=[])
        run_id = "unit-negative-" + fault.replace("_", "-")
        run = task_dir / "logs" / run_id
        facts = EvidenceFacts(
            task_id,
            ("DU-001",),
            binding["repository_id"],
            binding["branch"],
            base,
            subject,
            binding["spec_sha256"],
            bundle.sha256,
            binding["classification_input_sha256"],
            level,
            "local",
            run_id,
            run,
            "2026-10-31T00:00:00Z",
            (
                "python",
                "-m",
                "aiflow",
                "verify",
                task_id,
                "--actor",
                "synthetic-agent",
                "--node-materials",
                selector,
            ),
        )
        context = VerificationContext(root, task_id, base, subject, sys.executable, run_id)
        evidence = runtime.execute_node_verification(
            root, task_id, material_sha256=selector, context=context, bundle=bundle, facts=facts
        )
        assert evidence["conclusion"] == "failed", (
            "A unit process seam must never create FeaturePASS"
        )
        return evidence, run / "node"

    return runtime, root, settings, execute


@pytest.mark.parametrize(
    ("fault", "level", "prefix"),
    [
        ("last_nonzero", "V0", 8),
        ("unknown", "V0", 4),
        ("helper_unknown", "V1", 10),
        ("source_drift", "V0", 5),
        ("late_materials", "V0", 8),
        ("missing_coverage", "V1", 10),
    ],
)
def test_negative_transaction_preserves_prefix_and_never_runs_after_failure(
    negative_node_transaction, fault, level, prefix
) -> None:
    runtime, _root, settings, execute = negative_node_transaction
    evidence, node_dir = execute(fault, level)
    validate_node_evidence(evidence)
    with pytest.raises(AiflowError):
        validate_node_evidence(evidence, require_passed=True)
    expected_ids = [f"EXEC-{index:03d}" for index in range(1, prefix + 1)]
    assert settings["calls"] == ["setup-clone", "setup-checkout", *expected_ids]
    original = runtime._json(node_dir / "run.json")
    assert [item["execution_id"] for item in original["executions"]] == expected_ids
    assert all((node_dir / "raw" / name / "receipt.json").is_file() for name in expected_ids)
    assert evidence["node_binding"]["coverage"] is None
    if level == "V1":
        assert evidence["checks"][-2]["status"] == evidence["checks"][-1]["status"] == "unverified"
    if fault in {"unknown", "helper_unknown"}:
        assert original["executions"][-1]["receipt"]["cleanup"] == "unknown"


@pytest.fixture
def readonly_negative_node_transaction(negative_node_transaction, monkeypatch):
    """Prepare independent failed originals for consumer tests, never a runtime PASS.

    These synthetic processes do not mutate the original root. Check its actual
    first and final state while recording every intervening guard invocation.
    Execution-time root protection remains covered by the unabridged transaction
    matrix and root tests; consumer rechecks below always use the real guard.
    """
    runtime, root, settings, execute = negative_node_transaction
    check_root = runtime._check_root
    checkout_files = runtime._checkout_files
    captured = []
    checkout_captured = []
    checkout_baseline = []

    def check_baseline(*args, **kwargs):
        arguments = deepcopy((args, kwargs))
        if not captured:
            check_root(*args, **kwargs)
        else:
            assert arguments == captured[0], "Baseline root guard inputs changed"
        captured.append(arguments)

    def checkout_snapshot(*args, **kwargs):
        arguments = deepcopy((args, kwargs))
        if not checkout_captured:
            checkout_baseline.append(deepcopy(checkout_files(*args, **kwargs)))
        else:
            assert arguments == checkout_captured[0], "Baseline checkout inputs changed"
        checkout_captured.append(arguments)
        return deepcopy(checkout_baseline[0])

    with monkeypatch.context() as preparation:
        preparation.setattr(runtime, "_check_root", check_baseline)
        preparation.setattr(runtime, "_checkout_files", checkout_snapshot)
        evidence, node_dir = execute("late_materials", "V0")
        assert settings["level"] == "V0"
        assert settings["fault"] == "late_materials"
        assert len(captured) == 9
        check_root(*captured[0][0], **captured[0][1])
        assert len(checkout_captured) == 9
        assert (
            checkout_files(*checkout_captured[0][0], **checkout_captured[0][1])
            == checkout_baseline[0]
        )
    assert runtime._check_root is check_root
    assert runtime._checkout_files is checkout_files
    assert settings["material_checks"] == 2
    assert settings["calls"] == ["setup-clone", "setup-checkout"] + [
        f"EXEC-{index:03d}" for index in range(1, 9)
    ]
    original = runtime._json(node_dir / "run.json")
    assert len(original["executions"]) == 8
    assert all(runtime._successful(item["receipt"]) for item in original["executions"])
    assert evidence["conclusion"] == "failed"
    settings["fault"] = "read_only_recheck"
    return runtime, root, settings, evidence, node_dir


@pytest.mark.parametrize("fault", ["derived_results", "raw_stream", "dist_output", "run_hash"])
def test_failed_transaction_cannot_be_consumed_after_readonly_original_recheck(
    readonly_negative_node_transaction, monkeypatch, fault
) -> None:
    runtime, root, settings, evidence, node_dir = readonly_negative_node_transaction
    witnessed = []
    original_checks = runtime._checks

    def checks(*args):
        witnessed.append(True)
        return original_checks(*args)

    monkeypatch.setattr(runtime, "_checks", checks)
    if fault == "raw_stream":
        (node_dir / "raw/EXEC-008/stdout.raw").write_bytes(b"tampered original stream")
    elif fault == "dist_output":
        (node_dir / "checkout/dist/example.js").write_bytes(b"tampered declared build output")
    elif fault == "run_hash":
        evidence["node_binding"]["run"]["sha256"] = "0" * 64
        evidence["node_binding_sha256"] = runtime._sha(runtime._canonical(evidence["node_binding"]))
    before_calls = tuple(settings["calls"])
    data = (node_dir / "run.json").read_bytes()
    result = runtime.recheck_node_evidence(root, "TASK-0001", evidence)
    assert result.current is False and result.passed is False and result.reason_codes
    assert tuple(settings["calls"]) == before_calls
    assert (node_dir / "run.json").read_bytes() == data
    assert bool(witnessed) is (fault == "derived_results")


@pytest.mark.parametrize(
    "mutation",
    [
        "git_hooks",
        "git_include",
        "git_diff",
        "attributes_filter",
        "attributes_encoding",
        "attributes_ident",
        "missing_config",
        "nested_npmrc",
        "missing_script",
        "non_string_script",
        "test_script",
        "script_shell",
        "config_root_list",
        "config_root_null",
        "config_root_bool",
        "node_options",
        "lock_bool",
        "lock_float",
        "lock_old",
        "package_root_list",
        "package_root_null",
        "package_root_bool",
        "lock_root_list",
        "lock_root_null",
        "lock_root_bool",
    ],
)
def test_source_contract_rejects_real_git_execution_input_drift(
    tmp_path, monkeypatch, mutation
) -> None:
    import aiflow.node_execution as runtime

    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    _controlled_git(tmp_path, "init", "--quiet")
    _controlled_git(tmp_path, "config", "user.name", "Synthetic Test")
    _controlled_git(tmp_path, "config", "user.email", "synthetic@example.invalid")
    _controlled_git(tmp_path, "config", "core.autocrlf", "false")
    package = {
        "scripts": {
            name: "controlled unit fixture"
            for name in ("build", "check", "typecheck", "docs:check", "clean")
        }
    }
    package["scripts"]["test"] = runtime.SEMANTIC_CONTRACT["test_script"]
    lock = {"lockfileVersion": 3}
    files = {
        "package.json": b"",
        "package-lock.json": b"",
        "tsconfig.json": b"{}",
        "tsconfig.tests.json": b"{}",
        "vitest.config.ts": b"export default {};\n",
        "agent-commands.json": b"{}",
    }
    if mutation.startswith("attributes_"):
        attribute = {
            "attributes_filter": "filter=unit-undeclared",
            "attributes_encoding": "working-tree-encoding=UTF-8",
            "attributes_ident": "ident",
        }[mutation]
        files[".gitattributes"] = ("* " + attribute + "\n").encode()
    elif mutation == "missing_config":
        del files["agent-commands.json"]
    elif mutation == "nested_npmrc":
        files["scripts/.npmrc"] = b"script-shell=unreviewed\n"
    elif mutation == "missing_script":
        del package["scripts"]["clean"]
    elif mutation == "non_string_script":
        package["scripts"]["build"] = True
    elif mutation == "test_script":
        package["scripts"]["test"] = "vitest run --cache"
    elif mutation == "script_shell":
        package["config"] = {"script-shell": "unreviewed"}
    elif mutation.startswith("config_root_"):
        package["config"] = {
            "config_root_list": [],
            "config_root_null": None,
            "config_root_bool": True,
        }[mutation]
    elif mutation == "node_options":
        monkeypatch.setenv("NODE_OPTIONS", "--require=unreviewed")
    elif mutation.startswith("package_root_"):
        package = {"package_root_list": [], "package_root_null": None, "package_root_bool": True}[
            mutation
        ]
    elif mutation.startswith("lock_root_"):
        lock = {"lock_root_list": [], "lock_root_null": None, "lock_root_bool": True}[mutation]
    elif mutation.startswith("lock_"):
        lock["lockfileVersion"] = {"lock_bool": True, "lock_float": 3.0, "lock_old": 2}[mutation]
    files["package.json"] = runtime._canonical(package)
    files["package-lock.json"] = runtime._canonical(lock)
    for name, data in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    _controlled_git(tmp_path, "add", ".")
    _controlled_git(tmp_path, "commit", "--quiet", "-m", "Controlled invalid source contract")
    subject = _controlled_git(tmp_path, "rev-parse", "HEAD")
    source = _transaction_source(tmp_path, subject)
    if mutation.startswith("git_"):
        key = {
            "git_hooks": "core.hooksPath",
            "git_include": "include.path",
            "git_diff": "diff.external",
        }[mutation]
        _controlled_git(tmp_path, "config", key, "unit-undeclared")

    def forbidden_process(*_args, **_kwargs):
        pytest.fail("Invalid source JSON reached a Node process boundary")

    monkeypatch.setattr(runtime, "_process", forbidden_process)
    with pytest.raises(AiflowError):
        runtime._source_contract(tmp_path, source)
    assert not (tmp_path / ".ai/tasks/TASK-0001/logs").exists()


def test_actual_process_wrapper_retains_failed_job_observations_on_all_platforms(
    tmp_path, monkeypatch
) -> None:
    import aiflow.node_execution as runtime
    from aiflow.process_runner import NodeProcessResult

    def failed_job(*_args, **_kwargs):
        return NodeProcessResult(
            None,
            True,
            b"token=unit-secret\n",
            b"failed",
            False,
            False,
            "unknown",
            True,
            {"job_empty": False},
        )

    monkeypatch.setattr(runtime, "run_node_process", failed_job)
    output = tmp_path / "failed-process"
    receipt = runtime._process(
        (sys.executable, "-I", "-c", "never launched"),
        cwd=tmp_path,
        environment={},
        timeout=1,
        output=output,
    )
    assert not runtime._successful(receipt)
    assert receipt["cleanup"] == "unknown" and receipt["timed_out"] is True
    assert receipt["receipt"] == {"job_empty": False}
    assert (output / "stdout.raw").read_bytes() == b"token=unit-secret\n"
    assert b"unit-secret" not in (output / "stdout.log").read_bytes()
    assert runtime._json(output / "receipt.json") == receipt


@pytest.mark.parametrize(
    "hook", ["unit-injected.pth", "sitecustomize.py", "sitecustomize/__init__.py"]
)
def test_unrecorded_site_startup_hooks_invalidate_bound_engine_materials(
    synthetic_installed_engine,
    negative_material_originals,
    monkeypatch,
    hook,
) -> None:
    runtime, site, _distributions, _modules = synthetic_installed_engine
    _runtime, payload, prepared, manifests = negative_material_originals
    # This binds only a temporary metadata inventory; it never claims engine execution.
    manifests["engine.json"] = _transaction_engine()
    monkeypatch.setattr(runtime, "_engine", _transaction_engine)
    path = site / hook
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"# unrecorded startup input, never executed\n")
    with pytest.raises(AiflowError):
        runtime._check_materials(payload.parents[5], prepared, manifests)


@pytest.mark.parametrize(
    ("fault", "calls"),
    [
        ("clone_unknown", ["setup-clone"]),
        ("checkout_nonzero", ["setup-clone", "setup-checkout"]),
        ("collision_node_modules", ["setup-clone", "setup-checkout"]),
        ("collision_dist", ["setup-clone", "setup-checkout"]),
        ("collision_.runtime", ["setup-clone", "setup-checkout"]),
        ("checkout_source", ["setup-clone", "setup-checkout"]),
        (
            "json_limit_final",
            ["setup-clone", "setup-checkout", *[f"EXEC-{i:03d}" for i in range(1, 9)]],
        ),
    ],
)
def test_transaction_setup_and_publication_faults_keep_originals_without_continuation(
    negative_node_transaction, fault, calls
) -> None:
    runtime, root, settings, execute = negative_node_transaction
    with pytest.raises(AiflowError):
        execute(fault)
    assert settings["calls"] == calls
    run = root / ".ai/tasks/TASK-0001/logs" / ("unit-negative-" + fault.replace("_", "-")) / "node"
    assert not (run / "run.json").exists()
    assert all((run / "raw" / name / "receipt.json").is_file() for name in calls)


@pytest.mark.parametrize(
    "fault",
    [
        "decision_units",
        "spec_binding",
        "prepared_size",
        "prepared_selector",
        "run_size",
        "run_extra",
        "run_version",
        "run_kind",
        "run_prepared",
        "run_binding",
        "run_noncanonical",
        "environment",
        "npm_config",
        "input_roles",
        "input_source",
        "input_runtime",
        "dependency_role",
        "dependency_inventory",
        "dependency_bytes",
        "material_digest",
        "semantic_digest",
        "root_roles",
        "checkout_binding",
        "execution_type",
        "execution_extra",
        "execution_order",
        "execution_deadline",
        "execution_missing",
        "output_roles",
        "dist_binding",
        "build_dist_content",
    ],
)
def test_readonly_recheck_rejects_self_rehashed_private_original_faults(
    readonly_negative_node_transaction, monkeypatch, fault
) -> None:
    runtime, root, settings, evidence, node_dir = readonly_negative_node_transaction
    binding = evidence["node_binding"]
    document = runtime._json(node_dir / "run.json")
    touched_document = True
    if fault == "decision_units":
        evidence["decision_unit_ids"] = ["DU-002"]
        touched_document = False
    elif fault == "spec_binding":
        evidence["spec_sha256"] = "0" * 64
        touched_document = False
    elif fault == "prepared_size":
        binding["prepared"]["size"] += 1
        touched_document = False
    elif fault == "prepared_selector":
        binding["prepared"].update(
            sha256="0" * 64, ref="logs/node-prepared/" + "0" * 64 + "/prepared.json"
        )
        evidence["reproduce_command"][-1] = "0" * 64
        touched_document = False
    elif fault == "run_size":
        binding["run"]["size"] += 1
        touched_document = False
    elif fault == "run_extra":
        document["unbound"] = True
    elif fault == "run_version":
        document["schema_version"] = "3.0"
    elif fault == "run_kind":
        document["kind"] = "unbound"
    elif fault == "run_prepared":
        document["prepared_sha256"] = "0" * 64
    elif fault == "run_binding":
        document["binding"]["subject_tree"] = "0" * 40
    elif fault == "environment":
        document["environment"]["PATH"] = "unbound path"
        binding["environment_sha256"] = runtime._sha(runtime._canonical(document["environment"]))
    elif fault == "npm_config":
        (node_dir / "user.npmrc").write_bytes(b"script-shell=unbound\n")
    elif fault == "input_roles":
        document["inputs"]["unbound"] = {}
    elif fault == "input_source":
        document["inputs"]["source"]["files"][0]["sha256"] = "0" * 64
    elif fault == "input_runtime":
        document["inputs"]["runtime"]["root"] = str(root)
    elif fault == "dependency_role":
        document["inputs"]["dependencies"]["root"] = str(root)
    elif fault == "dependency_inventory":
        document["inputs"]["dependencies"]["entries"][-1]["sha256"] = "0" * 64
    elif fault == "dependency_bytes":
        dependencies = Path(document["inputs"]["dependencies"]["root"])
        (dependencies / "vitest/unbound.js").write_bytes(b"new bytes outside prepared inventory")
        document["inputs"]["dependencies"] = runtime._inventory(dependencies)
    elif fault == "material_digest":
        binding["materials_sha256"] = "0" * 64
    elif fault == "semantic_digest":
        binding["semantic_contract_sha256"] = "0" * 64
    elif fault == "root_roles":
        document["roots"]["unbound"] = {}
    elif fault == "checkout_binding":
        document["roots"]["checkout"]["files"][0]["sha256"] = "0" * 64
    elif fault == "execution_type":
        document["executions"] = {}
    elif fault == "execution_extra":
        document["executions"].append(deepcopy(document["executions"][-1]))
    elif fault == "execution_order":
        document["executions"][0]["execution_id"] = "EXEC-002"
    elif fault == "execution_deadline":
        receipt = document["executions"][0]["receipt"]
        receipt["timeout_seconds"] = 31
        (node_dir / "raw/EXEC-001/receipt.json").write_bytes(runtime._canonical(receipt))
    elif fault == "execution_missing":
        document["executions"].pop()
    elif fault == "output_roles":
        del document["outputs"]["fixtures"]
    elif fault == "dist_binding":
        document["outputs"]["dist"]["entries"][0]["sha256"] = "0" * 64
    elif fault == "build_dist_content":
        initial = document["outputs"].setdefault(
            "build_dist", deepcopy(document["outputs"]["dist"])
        )
        assert set(document["outputs"]) == {"build_dist", "dist", "fixtures"}
        row = next(item for item in initial["entries"] if item["kind"] == "file")
        row["sha256"] = "0" * 64
    if touched_document:
        raw = runtime._canonical(document) + (b"\n" if fault == "run_noncanonical" else b"")
        (node_dir / "run.json").write_bytes(raw)
        binding["run"].update(size=len(raw), sha256=runtime._sha(raw))
    evidence["node_binding_sha256"] = runtime._sha(runtime._canonical(binding))
    witnessed = []
    validated_receipts = []
    validate_receipt = runtime._validate_receipt

    def inspect_receipt(directory, *args, **kwargs):
        validated_receipts.append(directory.name)
        return validate_receipt(directory, *args, **kwargs)

    monkeypatch.setattr(runtime, "_validate_receipt", inspect_receipt)
    checks = runtime._checks

    def unexpected_derivation(*args):
        witnessed.append(True)
        return checks(*args)

    monkeypatch.setattr(runtime, "_checks", unexpected_derivation)
    rejected_errors = []
    original_error = runtime._error

    def observe_error(*args, **kwargs):
        error = original_error(*args, **kwargs)
        rejected_errors.append((error.code, error.message))
        return error

    if fault == "build_dist_content":
        monkeypatch.setattr(runtime, "_error", observe_error)
    calls = tuple(settings["calls"])
    original_bytes = (node_dir / "run.json").read_bytes()
    result = runtime.recheck_node_evidence(root, "TASK-0001", evidence)
    assert result.current is False and result.passed is False and result.reason_codes
    assert (node_dir / "run.json").read_bytes() == original_bytes
    if fault == "build_dist_content":
        expected_error = (
            ("NODE_OUTPUT_INVALID", "Initial and final Node output content differs")
            if "dist_rebuild" in runtime.SEMANTIC_CONTRACT
            else ("NODE_MATERIALS_INVALID", "Node run output inventory is incomplete")
        )
        assert rejected_errors == [expected_error]
    assert not witnessed, "Invalid originals must reject before check conclusions are recomputed"
    expected_receipts = {
        "execution_type": 2,
        "execution_extra": 2,
        "execution_order": 2,
        "execution_deadline": 3,
        "execution_missing": 9,
        "output_roles": 10,
        "dist_binding": 10,
        "build_dist_content": 10,
    }.get(fault, 0)
    assert len(validated_receipts) == expected_receipts, (
        "A new guard rejected before the intended fault boundary"
    )
    assert tuple(settings["calls"]) == calls
    assert (node_dir / "run.json").is_file()


@pytest.mark.parametrize("current,passed", [(False, False), (True, False), (False, True)])
def test_approval_reuses_trusted_policy_but_still_rechecks_node_evidence(
    tmp_path, node_policy_directory, node_public_evidence, monkeypatch, current, passed
):
    import aiflow.approval as approval
    import aiflow.node_execution as runtime

    bundle = load_policy_bundle(tmp_path, policy_directory=node_policy_directory)
    evidence = node_public_evidence()
    path = tmp_path / ".ai/tasks/TASK-0001/evidence.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(evidence), encoding="utf8")
    calls = []

    def recheck(root, task_id, value):
        calls.append((root, task_id, value))
        return SimpleNamespace(current=current, passed=passed, evidence_sha256="c" * 64)

    def forbidden(*args, **kwargs):
        pytest.fail("Evidence consumption reloaded an already trusted Policy")

    monkeypatch.setattr(approval, "load_policy_bundle", forbidden)
    monkeypatch.setattr(runtime, "recheck_node_evidence", recheck)
    result = approval._evidence(
        tmp_path,
        "TASK-0001",
        task={},
        classification={},
        spec_sha256="d" * 64,
        policy=bundle,
        review_ids=set(),
        events=[],
        policy_checks=[],
    )
    assert result == (False, "c" * 64, evidence)
    assert calls == [(tmp_path, "TASK-0001", evidence)]


@pytest.fixture
def controlled_setuptools_startup(synthetic_installed_engine):
    """Metadata protocol plus real files for the one allowed startup hook helper."""
    runtime, site, distributions, modules = synthetic_installed_engine
    data = runtime._DISTUTILS_PTH + b"\n"
    hook = site / "distutils-precedence.pth"
    hook.write_bytes(data)
    record = runtime.importlib.metadata.PackagePath(hook.name)
    record.hash = SimpleNamespace(
        mode="sha256",
        value=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("="),
    )
    record.size = len(data)
    files = [record]
    for module in ("setuptools", "_distutils_hack"):
        relative = Path(module) / "__init__.py"
        path = site / relative
        path.parent.mkdir()
        path.write_bytes(b"# controlled startup dependency; never imported\n")
        files.append(relative)
        modules[module] = SimpleNamespace(
            __file__=str(path), __spec__=SimpleNamespace(origin=str(path))
        )
    distribution = SimpleNamespace(
        files=files,
        metadata={"Name": "setuptools"},
        version="1.0",
        locate_file=lambda value: site / value,
        read_text=lambda _name: None,
    )
    distributions["setuptools"] = distribution
    return runtime, site, distribution, modules, record, hook


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_allowed_startup_helper_binds_exact_record_and_complete_dependency_inventory(
    controlled_setuptools_startup, newline
) -> None:
    runtime, site, _distribution, _modules, record, hook = controlled_setuptools_startup
    data = runtime._DISTUTILS_PTH + newline
    hook.write_bytes(data)
    record.hash.value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
    record.size = len(data)
    budget = [1000, 1024 * 1024]
    startup = runtime._engine_startup(site, budget)
    assert startup["setuptools"] is True and len(startup["files"]) == 1
    assert startup["files"][0]["sha256"] == hashlib.sha256(data).hexdigest()
    assert startup["files"][0]["identity"] == runtime._identity(hook.lstat())
    assert budget == [998, 1024 * 1024 - len(data)]
    inventory = runtime._engine()
    assert inventory["startup"]["setuptools"] is True
    assert inventory["distributions"][-1]["name"] == "setuptools"
    assert {Path(row["path"]).parent.name for row in inventory["distributions"][-1]["files"]} >= {
        "setuptools",
        "_distutils_hack",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_payload",
        "extra_payload",
        "unknown_name",
        "missing_record",
        "missing_hash",
        "hash_mode",
        "hash_value",
        "size_bool",
        "size_float",
        "size_mismatch",
        "installation",
        "loaded_sitecustomize",
        "cache_sitecustomize",
        "setuptools_extra_pyc",
        "hack_extra_source",
        "hack_origin",
        "entry_limit",
        "byte_limit",
    ],
)
def test_startup_hook_or_dependency_drift_is_rejected_before_engine_use(
    controlled_setuptools_startup, monkeypatch, mutation
) -> None:
    runtime, site, distribution, modules, record, hook = controlled_setuptools_startup
    budget = None
    if mutation == "unknown_payload":
        hook.write_bytes(hook.read_bytes().replace(b"local", b"wrong"))
    elif mutation == "extra_payload":
        hook.write_bytes(hook.read_bytes() + b"import unbound_startup_code\n")
    elif mutation == "unknown_name":
        hook.rename(hook.with_name("unbound.pth"))
    elif mutation == "missing_record":
        distribution.files = distribution.files[1:]
    elif mutation == "missing_hash":
        record.hash = None
    elif mutation == "hash_mode":
        record.hash.mode = "md5"
    elif mutation == "hash_value":
        record.hash.value = "unbound"
    elif mutation == "size_bool":
        record.size = True
    elif mutation == "size_float":
        record.size = float(record.size)
    elif mutation == "size_mismatch":
        record.size += 1
    elif mutation == "installation":
        distribution.locate_file = lambda value: site.parent / "other-installation" / value
    elif mutation == "loaded_sitecustomize":
        monkeypatch.setitem(sys.modules, "sitecustomize", SimpleNamespace())
    elif mutation == "cache_sitecustomize":
        cache = site / "__pycache__"
        cache.mkdir()
        (cache / "sitecustomize.cpython-311.pyc").write_bytes(b"unbound bytecode, never executed")
    elif mutation == "setuptools_extra_pyc":
        (site / "setuptools/unbound.pyc").write_bytes(b"unrecorded dependency bytecode")
    elif mutation == "hack_extra_source":
        (site / "_distutils_hack/unbound.py").write_bytes(b"unrecorded startup dependency source")
    elif mutation == "hack_origin":
        modules["_distutils_hack"].__file__ = str(site / "unbound.py")
    elif mutation == "entry_limit":
        budget = [0, 1024 * 1024]
    elif mutation == "byte_limit":
        budget = [1000, 1]
    with pytest.raises(AiflowError):
        runtime._engine(budget=budget)


def test_site_facts_collect_current_interpreter_only_as_data() -> None:
    import site

    import aiflow.node_execution as runtime

    facts = runtime._engine_site_facts()
    assert set(facts) == {
        "prefix",
        "base_prefix",
        "site_roots",
        "active_site_roots",
        "enable_user_site",
    }
    assert facts["prefix"] == str(Path(sys.prefix).absolute())
    assert facts["base_prefix"] == str(Path(sys.base_prefix).absolute())
    assert facts["enable_user_site"] is site.ENABLE_USER_SITE
    assert facts["site_roots"] == [str(Path(value).absolute()) for value in site.getsitepackages()]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("prefix", "relative"),
        ("prefix", None),
        ("enable_user_site", True),
        ("enable_user_site", None),
        ("enable_user_site", 0),
        ("site_roots", []),
        ("site_roots", ()),
        ("site_roots", ["relative"]),
        ("site_roots", [1]),
        ("active_site_roots", "unbound"),
        ("active_site_roots", ["relative"]),
    ],
)
def test_startup_facts_with_unknown_sites_or_user_enablement_are_rejected(
    synthetic_installed_engine, monkeypatch, field, value
) -> None:
    runtime, site, _distributions, _modules = synthetic_installed_engine
    facts = runtime._engine_site_facts()
    facts[field] = value
    monkeypatch.setattr(runtime, "_engine_site_facts", lambda: facts)
    with pytest.raises(AiflowError):
        runtime._engine_startup(site, [1000, 1024 * 1024])


@pytest.mark.parametrize(
    "fault",
    [
        "foreign_declared",
        "foreign_active",
        "duplicate_root",
        "loaded_usercustomize",
        "prefix_pth",
        "prefix_sitecustomize",
        "prefix_known_hook",
    ],
)
def test_startup_root_and_loaded_customization_are_exact(
    synthetic_installed_engine, monkeypatch, fault
) -> None:
    runtime, site, _distributions, _modules = synthetic_installed_engine
    facts = runtime._engine_site_facts()
    prefix = site.parent
    if fault == "foreign_declared":
        facts["site_roots"].append(str(prefix / "outside-installation"))
    elif fault == "foreign_active":
        facts["active_site_roots"].append(str(prefix / "outside-installation"))
    elif fault == "duplicate_root":
        facts["site_roots"].append(str(site))
    elif fault == "loaded_usercustomize":
        monkeypatch.setitem(sys.modules, "usercustomize", SimpleNamespace())
    else:
        facts["site_roots"].append(str(prefix))
        path = (
            prefix
            / {
                "prefix_pth": "unbound.pth",
                "prefix_sitecustomize": "sitecustomize.py",
                "prefix_known_hook": "distutils-precedence.pth",
            }[fault]
        )
        path.write_bytes(runtime._DISTUTILS_PTH + b"\n")
    monkeypatch.setattr(runtime, "_engine_site_facts", lambda: facts)
    with pytest.raises(AiflowError):
        runtime._engine_startup(site, [1000, 1024 * 1024])


@pytest.mark.parametrize(
    "data",
    [
        b"include-system-site-packages=true\n",
        b"home=controlled\n",
        b"include-system-site-packages=false\ninclude-system-site-packages=false\n",
        b"\xff",
    ],
)
def test_pyvenv_configuration_must_explicitly_disable_external_sites(
    synthetic_installed_engine, data
) -> None:
    runtime, site, _distributions, _modules = synthetic_installed_engine
    (site.parent / "pyvenv.cfg").write_bytes(data)
    with pytest.raises(AiflowError):
        runtime._engine_startup(site, [1000, 1024 * 1024])


def test_pyvenv_configuration_presence_and_bytes_are_part_of_the_engine_binding(
    synthetic_installed_engine,
) -> None:
    runtime, site, _distributions, _modules = synthetic_installed_engine
    configuration = site.parent / "pyvenv.cfg"
    absent = runtime._engine()
    assert absent["startup"]["pyvenv_configuration"] is None
    first = b"include-system-site-packages=false\nhome=controlled-a\n"
    configuration.write_bytes(first)
    initial = runtime._engine()
    assert initial["startup"]["pyvenv_configuration"]["sha256"] == hashlib.sha256(first).hexdigest()
    configuration.write_bytes(b"include-system-site-packages=false\nhome=controlled-b\n")
    changed = runtime._engine()
    assert runtime._canonical(changed) != runtime._canonical(initial)
    assert runtime._canonical(initial) != runtime._canonical(absent)
    configuration.unlink()
    removed = runtime._engine()
    assert removed["startup"]["pyvenv_configuration"] is None
    assert runtime._canonical(removed) != runtime._canonical(changed)


@pytest.mark.parametrize("target", ["cached_position", "function_range", "branch_range"])
def test_cached_coverage_ranges_honor_the_existing_deadline(monkeypatch, target) -> None:
    monkeypatch.setattr(node, "monotonic", lambda: 2.0)
    cache = {1: {0, 1}}
    source_range = {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": None}}
    with pytest.raises(AiflowError) as caught:
        if target == "cached_position":
            node._position(source_range["end"], ["x"], cache, 1.0, allow_line_end=True)
        else:
            kind, role = ("fnMap", "decl") if target == "function_range" else ("branchMap", "loc")
            node._auxiliary_source_map({"0": {role: source_range}}, kind, ["x"], cache, 1.0)
    assert caught.value.code == "NODE_COVERAGE_TIMEOUT"


def test_auxiliary_walk_stops_when_deadline_expires_between_entries(monkeypatch) -> None:
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(node, "monotonic", lambda: clock.now)

    class TimedEntries(dict):
        def items(self):
            yield "0", {}
            clock.now = 2.0
            yield "1", {}

    with pytest.raises(AiflowError) as caught:
        node._auxiliary_source_map(TimedEntries(), "fnMap", ["x"], {1: {0, 1}}, 1.0)
    assert caught.value.code == "NODE_COVERAGE_TIMEOUT"
