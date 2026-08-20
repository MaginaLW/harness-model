"""V0/V1 Policy plan parsing tests without executing project verification commands."""

from __future__ import annotations

import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest

from aiflow.errors import ContractError
from aiflow.policy import PolicyBundle, load_policy_bundle
from aiflow.verification import (
    VerificationContext,
    parse_check_result,
    parse_verification_plan,
)

ROOT = Path(__file__).resolve().parents[2]


def context(tmp_path: Path, **changes: object) -> VerificationContext:
    values: dict[str, object] = {
        "repository_root": ROOT,
        "task_id": "TASK-0001",
        "base_commit": "a" * 40,
        "subject_commit": "b" * 40,
        "python": sys.executable,
        "run_id": "run-001",
        "ci_run_dir": None,
    }
    values.update(changes)
    return VerificationContext(**values)  # type: ignore[arg-type]


def plan(level: str, tmp_path: Path):
    return parse_verification_plan(
        load_policy_bundle(ROOT),
        context(tmp_path),
        level=level,
        tool_available=lambda _tool: True,  # type: ignore[arg-type]
    )


def bundle_copy() -> PolicyBundle:
    bundle = load_policy_bundle(ROOT)
    return PolicyBundle(deepcopy(bundle.documents), bundle.policy_version, bundle.sha256)


def checks(bundle: PolicyBundle, level: str) -> list[dict[str, object]]:
    document = bundle.documents["verification-levels.yaml"]
    selected = next(item for item in document["levels"] if item["id"] == level)
    return selected["checks"]


@pytest.mark.parametrize("level", ["V0", "V1"])
def test_plan_has_fixture_order_and_task_local_run_directory(level: str, tmp_path: Path) -> None:
    expected = json.loads(
        (
            ROOT / "tests" / "fixtures" / "verification" / "plans" / f"{level.lower()}.json"
        ).read_text()
    )
    parsed = plan(level, tmp_path)
    assert [check.check_id for check in parsed.checks] == expected["check_ids"]
    assert parsed.run_dir.is_relative_to(ROOT / ".ai" / "tasks" / "TASK-0001" / "logs")


def test_v1_contains_v0_categories_and_coverage_environment(tmp_path: Path) -> None:
    v0 = plan("V0", tmp_path)
    v1 = plan("V1", tmp_path)
    assert [check.check_id for check in v1.checks][: len(v0.checks)] == [
        check.check_id for check in v0.checks
    ]
    coverage = next(check for check in v1.checks if check.check_id == "coverage_xml")
    assert coverage.environment["COVERAGE_FILE"] == (v1.run_dir / ".coverage").as_posix()
    assert v1.comparison_subject == "b" * 40


def test_repeated_argv_keeps_distinct_category_mapping(tmp_path: Path) -> None:
    bundle = bundle_copy()
    unit = next(item for item in checks(bundle, "V1") if item["id"] == "unit_tests")
    regression = next(item for item in checks(bundle, "V1") if item["id"] == "regression_tests")
    regression["command"] = deepcopy(unit["command"])
    parsed = parse_verification_plan(
        bundle, context(tmp_path), level="V1", tool_available=lambda _argv: True
    )
    assert len(parsed.checks) == len({check.check_id for check in parsed.checks})
    by_id = {check.check_id: check for check in parsed.checks}
    assert by_id["unit_tests"].argv == by_id["regression_tests"].argv
    grouped = next(
        execution for execution in parsed.executions if "unit_tests" in execution.check_ids
    )
    assert grouped.check_ids == ("unit_tests", "regression_tests")
    assert len(parsed.executions) == len(parsed.checks) - 1


def test_missing_tool_blocks_required_check(tmp_path: Path) -> None:
    parsed = parse_verification_plan(
        load_policy_bundle(ROOT), context(tmp_path), level="V0", tool_available=lambda _tool: False
    )
    assert parsed.valid is False
    assert parsed.blocking_reasons[0].startswith("VERIFICATION_TOOL_MISSING:")


def test_missing_optional_tool_is_unverified_not_passed(tmp_path: Path) -> None:
    bundle = bundle_copy()
    checks(bundle, "V0")[0]["required"] = False
    parsed = parse_verification_plan(
        bundle, context(tmp_path), level="V0", tool_available=lambda _argv: False
    )
    assert "contract" in parsed.unverified_check_ids
    assert "VERIFICATION_TOOL_MISSING:contract" not in parsed.blocking_reasons


def test_ci_requires_existing_os_temporary_directory(tmp_path: Path) -> None:
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            load_policy_bundle(ROOT),
            context(tmp_path, ci_run_dir=ROOT),
            level="V0",
            tool_available=lambda _tool: True,
        )
    assert caught.value.code == "CI_RUN_DIR_INVALID"


def test_ci_accepts_strict_existing_temporary_descendant(tmp_path: Path) -> None:
    run_dir = tmp_path / "ci-run"
    run_dir.mkdir()
    parsed = parse_verification_plan(
        load_policy_bundle(ROOT),
        context(tmp_path, ci_run_dir=run_dir),
        level="V0",
        tool_available=lambda _argv: True,
    )
    assert parsed.run_dir == run_dir.resolve()


def test_ci_rejects_temp_root_and_missing_repository(tmp_path: Path) -> None:
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            load_policy_bundle(ROOT),
            context(tmp_path, ci_run_dir=Path(tempfile.gettempdir())),
            level="V0",
            tool_available=lambda _argv: True,
        )
    assert caught.value.code == "CI_RUN_DIR_INVALID"
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            load_policy_bundle(ROOT),
            context(tmp_path, repository_root=tmp_path / "missing"),
            level="V0",
            tool_available=lambda _argv: True,
        )
    assert caught.value.code == "VERIFICATION_CWD_INVALID"


def test_local_logs_symlink_cannot_escape_repository(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    logs_parent = repository / ".ai" / "tasks" / "TASK-0001"
    logs_parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (logs_parent / "logs").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            load_policy_bundle(ROOT),
            context(tmp_path, repository_root=repository),
            level="V0",
            tool_available=lambda _argv: True,
        )
    assert caught.value.code == "VERIFICATION_RUN_DIR_INVALID"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda item: item.update(command="python -m aiflow --help"),
            "VERIFICATION_COMMAND_INVALID",
        ),
        (lambda item: item.update(timeout_seconds=0), "VERIFICATION_TIMEOUT_INVALID"),
        (lambda item: item.update(result_parser="unknown"), "VERIFICATION_CHECK_INVALID"),
        (
            lambda item: item.update(command=["{python}", "{unknown}"]),
            "VERIFICATION_PLACEHOLDER_INVALID",
        ),
        (lambda item: item.update(environment={"PATH": "value"}), "VERIFICATION_ENV_INVALID"),
    ],
)
def test_invalid_check_shape_is_rejected(tmp_path: Path, mutation, code: str) -> None:
    bundle = bundle_copy()
    mutation(checks(bundle, "V0")[0])
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            bundle, context(tmp_path), level="V0", tool_available=lambda _argv: True
        )
    assert caught.value.code == code


def test_duplicate_missing_extra_categories_and_v1_prefix_are_rejected(tmp_path: Path) -> None:
    duplicate = bundle_copy()
    checks(duplicate, "V0").append(deepcopy(checks(duplicate, "V0")[0]))
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            duplicate, context(tmp_path), level="V0", tool_available=lambda _argv: True
        )
    assert caught.value.code == "VERIFICATION_CATEGORY_DUPLICATE"

    missing = bundle_copy()
    checks(missing, "V0").pop()
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            missing, context(tmp_path), level="V0", tool_available=lambda _argv: True
        )
    assert caught.value.code == "VERIFICATION_CATEGORY_MISSING"

    extra = bundle_copy()
    checks(extra, "V0").append(deepcopy(checks(extra, "V1")[-1]))
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            extra, context(tmp_path), level="V0", tool_available=lambda _argv: True
        )
    assert caught.value.code == "VERIFICATION_CATEGORY_MISSING"

    prefix = bundle_copy()
    checks(prefix, "V1")[0]["timeout_seconds"] += 1
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            prefix, context(tmp_path), level="V1", tool_available=lambda _argv: True
        )
    assert caught.value.code == "VERIFICATION_V1_PREFIX_INVALID"


def test_nested_expansion_and_placeholder_allow_list_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            load_policy_bundle(ROOT),
            context(tmp_path, python="{run_dir}"),
            level="V0",
            tool_available=lambda _argv: True,
        )
    assert caught.value.code == "VERIFICATION_PLACEHOLDER_INVALID"
    bundle = bundle_copy()
    bundle.documents["verification-levels.yaml"]["allowed_placeholders"].pop()
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            bundle, context(tmp_path), level="V0", tool_available=lambda _argv: True
        )
    assert caught.value.code == "VERIFICATION_PLACEHOLDER_INVALID"


def test_coverage_and_diff_cover_must_share_run_dir_base_and_threshold(tmp_path: Path) -> None:
    coverage = bundle_copy()
    coverage_check = next(item for item in checks(coverage, "V1") if item["id"] == "coverage_xml")
    coverage_check["environment"]["COVERAGE_FILE"] = "C:/.coverage"
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            coverage, context(tmp_path), level="V1", tool_available=lambda _argv: True
        )
    assert caught.value.code in {"VERIFICATION_ENV_INVALID", "VERIFICATION_COVERAGE_CONFIG_INVALID"}

    xml = bundle_copy()
    xml_check = next(item for item in checks(xml, "V1") if item["id"] == "coverage_xml")
    report_index = next(
        index
        for index, argument in enumerate(xml_check["command"])
        if argument.startswith("--cov-report=xml:")
    )
    xml_check["command"][report_index] = "--cov-report=xml:C:/coverage.xml"
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            xml, context(tmp_path), level="V1", tool_available=lambda _argv: True
        )
    assert caught.value.code == "VERIFICATION_COVERAGE_CONFIG_INVALID"

    for required_argument in ("--cov=aiflow", "--cov-branch"):
        bundle = bundle_copy()
        coverage_check = next(item for item in checks(bundle, "V1") if item["id"] == "coverage_xml")
        coverage_check["command"].remove(required_argument)
        with pytest.raises(ContractError) as caught:
            parse_verification_plan(
                bundle, context(tmp_path), level="V1", tool_available=lambda _argv: True
            )
        assert caught.value.code == "VERIFICATION_COVERAGE_CONFIG_INVALID"

    for token, replacement in (("{base_commit}", "c" * 40), ("90", "89")):
        bundle = bundle_copy()
        diff = next(item for item in checks(bundle, "V1") if item["id"] == "diff_coverage")
        diff["command"][diff["command"].index(token)] = replacement
        with pytest.raises(ContractError) as caught:
            parse_verification_plan(
                bundle, context(tmp_path), level="V1", tool_available=lambda _argv: True
            )
        assert caught.value.code == "VERIFICATION_DIFF_COVERAGE_CONFIG_INVALID"

    threshold_field = bundle_copy()
    diff = next(item for item in checks(threshold_field, "V1") if item["id"] == "diff_coverage")
    diff["threshold"] = 89
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            threshold_field,
            context(tmp_path),
            level="V1",
            tool_available=lambda _argv: True,
        )
    assert caught.value.code == "VERIFICATION_DIFF_COVERAGE_CONFIG_INVALID"

    for flag, value in (("--compare-branch", "c" * 40), ("--fail-under", "1")):
        duplicate_flag = bundle_copy()
        diff = next(item for item in checks(duplicate_flag, "V1") if item["id"] == "diff_coverage")
        diff["command"].extend([flag, value])
        with pytest.raises(ContractError) as caught:
            parse_verification_plan(
                duplicate_flag,
                context(tmp_path),
                level="V1",
                tool_available=lambda _argv: True,
            )
        assert caught.value.code == "VERIFICATION_DIFF_COVERAGE_CONFIG_INVALID"


def test_invalid_policy_allow_lists_are_rejected(tmp_path: Path) -> None:
    bundle = bundle_copy()
    bundle.documents["verification-levels.yaml"]["allowed_commands"].append("unsafe")
    with pytest.raises(ContractError) as caught:
        parse_verification_plan(
            bundle, context(tmp_path), level="V0", tool_available=lambda _argv: True
        )
    assert caught.value.code == "VERIFICATION_POLICY_INVALID"


def test_parse_does_not_create_coverage_files_in_repository_root(tmp_path: Path) -> None:
    coverage = ROOT / ".coverage"
    xml = ROOT / "coverage.xml"
    before = (coverage.exists(), xml.exists())
    plan("V1", tmp_path)
    assert (coverage.exists(), xml.exists()) == before


def test_diff_coverage_threshold_and_missing_xml_are_deterministic(tmp_path: Path) -> None:
    check = next(
        check for check in plan("V1", tmp_path).checks if check.check_id == "diff_coverage"
    )
    assert (
        parse_check_result(
            check, returncode=0, output="TOTAL 89%", coverage_xml_exists=True
        ).conclusion
        == "failed"
    )
    assert (
        parse_check_result(
            check, returncode=0, output="TOTAL 90%", coverage_xml_exists=True
        ).conclusion
        == "passed"
    )
    coverage = next(
        check for check in plan("V1", tmp_path).checks if check.check_id == "coverage_xml"
    )
    assert (
        parse_check_result(coverage, returncode=0, coverage_xml_exists=False).reason_code
        == "VERIFICATION_COVERAGE_XML_MISSING"
    )
