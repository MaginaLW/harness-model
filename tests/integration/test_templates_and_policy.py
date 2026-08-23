"""Integration checks for the stage-one Policy and artifact templates."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from aiflow.contracts import validate_contract

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
POLICY_ROOT = REPOSITORY_ROOT / ".ai" / "policy"
TEMPLATE_ROOT = REPOSITORY_ROOT / ".ai" / "templates"
POLICY_FILES = (
    "hard-rules.yaml",
    "routing.yaml",
    "verification-levels.yaml",
    "permissions.yaml",
)
EXPECTED_PLACEHOLDERS = {
    "{base_commit}",
    "{python}",
    "{repository_root}",
    "{run_dir}",
    "{subject_commit}",
    "{task_id}",
}
EXPECTED_V0_CHECKS = {
    "contract",
    "scope",
    "ruff_check",
    "ruff_format_check",
    "smoke",
}
EXPECTED_V1_EXTRA_CHECKS = {
    "coverage_xml",
    "diff_coverage",
    "mypy",
    "regression_tests",
    "unit_tests",
}
EXPECTED_V2_EXTRA_CHECKS = {
    "acceptance",
    "integration",
    "targeted_mutation",
    "independent_verifier",
}
EXPECTED_FORBIDDEN_ACTIONS = {
    "delete",
    "deploy",
    "merge",
    "paid_external_call",
    "push",
    "secret_export",
}
PLACEHOLDER_PATTERN = re.compile(r"\{[^{}]+\}")
pytestmark = pytest.mark.contract

PolicyObject = dict[str, Any]
PolicyBundle = dict[str, PolicyObject]


def load_policy_bundle(directory: Path = POLICY_ROOT) -> PolicyBundle:
    """Safely load the four fixed Policy files."""
    bundle: PolicyBundle = {}
    for filename in POLICY_FILES:
        value = yaml.safe_load((directory / filename).read_text(encoding="utf-8"))
        assert isinstance(value, dict)
        bundle[filename] = value
    return bundle


def _policy_entries(bundle: PolicyBundle) -> list[PolicyObject]:
    entries: list[PolicyObject] = []
    entries.extend(bundle["hard-rules.yaml"]["rules"])
    entries.extend(bundle["routing.yaml"]["rules"])
    entries.append(bundle["routing.yaml"]["default_route"])
    entries.extend(bundle["permissions.yaml"]["rules"])
    return entries


def _level(bundle: PolicyBundle, level_id: str) -> PolicyObject:
    levels = bundle["verification-levels.yaml"]["levels"]
    return next(level for level in levels if level["id"] == level_id)


def _check(bundle: PolicyBundle, level_id: str, check_id: str) -> PolicyObject:
    return next(check for check in _level(bundle, level_id)["checks"] if check["id"] == check_id)


def policy_bundle_errors(bundle: PolicyBundle) -> list[str]:
    """Apply Task 1.3 cross-file invariants without implementing the future loader."""
    errors: list[str] = []
    for filename, value in bundle.items():
        errors.extend(f"{filename}{error}" for error in validate_contract("policy", value))

    entries = _policy_entries(bundle)
    identifiers = [entry["id"] for entry in entries if isinstance(entry.get("id"), str)]
    if len(identifiers) != len(set(identifiers)):
        errors.append("policy: rule IDs must be globally unique")

    routing = bundle["routing.yaml"]
    default_route = routing.get("default_route", {})
    if default_route.get("id") != "ROUTE-DEFAULT-REVIEW" or default_route.get("route") != "REVIEW":
        errors.append("routing: explicit default REVIEW is required")

    verification = bundle["verification-levels.yaml"]
    allowed_placeholders = set(verification.get("allowed_placeholders", []))
    if allowed_placeholders != EXPECTED_PLACEHOLDERS:
        errors.append("verification: allowed placeholders differ from the closed set")

    allowed_commands = set(verification.get("allowed_commands", []))
    allowed_environment = set(verification.get("allowed_environment", []))
    for level in verification.get("levels", []):
        for check in level.get("checks", []):
            command = check.get("command")
            if isinstance(command, list) and command:
                if command[0] not in allowed_commands:
                    errors.append(f"verification: unknown command for {check.get('id')}")
                placeholders = set(PLACEHOLDER_PATTERN.findall(" ".join(command)))
                if not placeholders <= allowed_placeholders:
                    errors.append(f"verification: unknown placeholder for {check.get('id')}")

            environment = check.get("environment", {})
            if isinstance(environment, dict):
                if not set(environment) <= allowed_environment:
                    errors.append(f"verification: unknown environment key for {check.get('id')}")
                environment_placeholders = set(
                    PLACEHOLDER_PATTERN.findall(" ".join(map(str, environment.values())))
                )
                if not environment_placeholders <= allowed_placeholders:
                    errors.append(
                        f"verification: unknown environment placeholder for {check.get('id')}"
                    )

    run_directories = verification.get("run_directories", {})
    if run_directories.get("local_root") != "{repository_root}/.ai/tasks/{task_id}/logs":
        errors.append("verification: local run_dir must stay under the current task logs")
    if run_directories.get("ci_root_source") != "runner_temp":
        errors.append("verification: CI run_dir must come from runner temp")
    if run_directories.get("require_descendant") is not True:
        errors.append("verification: run_dir containment must be enforced")

    v0_ids = {check["id"] for check in _level(bundle, "V0")["checks"]}
    v1_ids = {check["id"] for check in _level(bundle, "V1")["checks"]}
    if v0_ids != EXPECTED_V0_CHECKS:
        errors.append("verification: V0 check set is incomplete")
    if not v0_ids <= v1_ids:
        errors.append("verification: V1 must include every V0 check")
    if not EXPECTED_V1_EXTRA_CHECKS <= v1_ids:
        errors.append("verification: V1 check set is incomplete")

    v2_ids = {check["id"] for check in _level(bundle, "V2")["checks"]}
    if v2_ids != v1_ids | EXPECTED_V2_EXTRA_CHECKS:
        errors.append("verification: V2 check set is incomplete")
    for check_id, target in (
        ("acceptance", "tests/acceptance"),
        ("integration", "tests/integration"),
    ):
        check = _check(bundle, "V2", check_id)
        if check.get("command") != ["{python}", "-m", "pytest", target, "-q"]:
            errors.append(f"verification: {check_id} must use its fixed offline pytest target")
        if check.get("required") is not True or check.get("result_parser") != "pytest":
            errors.append(f"verification: {check_id} must be a required pytest check")

    coverage = _check(bundle, "V1", "coverage_xml")
    if coverage.get("environment") != {"COVERAGE_FILE": "{run_dir}/.coverage"}:
        errors.append("verification: coverage environment is not isolated to run_dir")

    diff_coverage = _check(bundle, "V1", "diff_coverage")
    if diff_coverage.get("threshold") != 90:
        errors.append("verification: diff-cover threshold must be 90")

    forbidden = set(bundle["permissions.yaml"].get("forbidden_automatic_actions", []))
    if forbidden != EXPECTED_FORBIDDEN_ACTIONS:
        errors.append("permissions: automatic forbidden action set is incomplete")

    return sorted(set(errors))


def markdown_headings(path: Path) -> list[str]:
    """Return level-two headings from a Markdown template."""
    return [
        line.removeprefix("## ").strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    ]


def test_policy_files_parse_and_satisfy_all_invariants() -> None:
    bundle = load_policy_bundle()

    assert policy_bundle_errors(bundle) == []
    assert all(isinstance(entry["priority"], int) for entry in _policy_entries(bundle))
    assert sorted((entry["priority"], entry["id"]) for entry in _policy_entries(bundle))


def test_unknown_predicate_is_rejected() -> None:
    bundle = load_policy_bundle()
    bundle["hard-rules.yaml"]["rules"][0]["conditions"][0]["operator"] = "eval"

    assert policy_bundle_errors(bundle)


def test_unknown_verification_check_is_rejected() -> None:
    bundle = load_policy_bundle()
    bundle["verification-levels.yaml"]["levels"][0]["checks"][0]["id"] = "shell"

    assert policy_bundle_errors(bundle)


def test_duplicate_rule_id_is_rejected() -> None:
    bundle = load_policy_bundle()
    bundle["routing.yaml"]["rules"][0]["id"] = bundle["hard-rules.yaml"]["rules"][0]["id"]

    assert "policy: rule IDs must be globally unique" in policy_bundle_errors(bundle)


def test_missing_default_review_is_rejected() -> None:
    bundle = load_policy_bundle()
    bundle["routing.yaml"]["default_route"]["route"] = "AUTO"

    assert "routing: explicit default REVIEW is required" in policy_bundle_errors(bundle)


def test_command_must_be_an_array() -> None:
    bundle = load_policy_bundle()
    bundle["verification-levels.yaml"]["levels"][0]["checks"][0]["command"] = "ruff"

    assert policy_bundle_errors(bundle)


def test_unknown_command_and_substitution_variables_are_rejected() -> None:
    bundle = load_policy_bundle()
    check = bundle["verification-levels.yaml"]["levels"][0]["checks"][0]
    check["command"] = ["powershell", "{unknown_root}"]
    check["environment"] = {"TOKEN": "{unknown_secret}"}

    errors = policy_bundle_errors(bundle)
    assert any("unknown command" in error for error in errors)
    assert any("unknown placeholder" in error for error in errors)
    assert any("unknown environment" in error for error in errors)


def test_run_directory_cannot_resolve_outside_the_allowed_roots() -> None:
    bundle = load_policy_bundle()
    bundle["verification-levels.yaml"]["run_directories"]["local_root"] = "C:/temp"

    assert (
        "verification: local run_dir must stay under the current task logs"
        in policy_bundle_errors(bundle)
    )


def test_diff_cover_threshold_is_fixed_at_ninety() -> None:
    bundle = load_policy_bundle()
    _check(bundle, "V1", "diff_coverage")["threshold"] = 89

    assert "verification: diff-cover threshold must be 90" in policy_bundle_errors(bundle)


def test_v1_cannot_omit_a_v0_check() -> None:
    bundle = load_policy_bundle()
    v1 = _level(bundle, "V1")
    v1["checks"] = [check for check in v1["checks"] if check["id"] != "scope"]

    assert "verification: V1 must include every V0 check" in policy_bundle_errors(bundle)


def test_v2_acceptance_and_integration_cannot_be_replaced_with_help_or_wrong_target() -> None:
    bundle = load_policy_bundle()
    _check(bundle, "V2", "acceptance")["command"] = ["{python}", "-m", "aiflow", "--help"]
    _check(bundle, "V2", "integration")["result_parser"] = "exit_zero"

    errors = policy_bundle_errors(bundle)

    assert "verification: acceptance must use its fixed offline pytest target" in errors
    assert "verification: integration must be a required pytest check" in errors


def test_machine_templates_parse_and_satisfy_contracts() -> None:
    task = yaml.safe_load((TEMPLATE_ROOT / "task.yaml").read_text(encoding="utf-8"))
    evidence = json.loads((TEMPLATE_ROOT / "evidence.json").read_text(encoding="utf-8"))

    assert validate_contract("task", task) == []
    assert validate_contract("evidence", evidence) == []


def test_markdown_templates_have_each_required_heading_once() -> None:
    expected = {
        "spec.md": ["目标", "范围", "非目标", "验收条件", "禁止动作", "错误行为", "回滚"],
        "review-package.md": [
            "审核目标",
            "背景",
            "代码地图",
            "语义变更",
            "风险",
            "证据",
            "审核问题",
            "推荐结论",
        ],
    }
    for filename, headings in expected.items():
        actual = markdown_headings(TEMPLATE_ROOT / filename)
        assert actual == headings
        assert all(actual.count(heading) == 1 for heading in headings)


def test_ask_template_defines_two_to_four_options_and_all_fields() -> None:
    text = (TEMPLATE_ROOT / "ask.md").read_text(encoding="utf-8")

    assert "2—4" in text
    for field in ("option_id", "description", "benefit", "cost", "risk", "recommended"):
        assert f"`{field}`" in text


def test_templates_and_policy_have_no_empty_placeholder_markers() -> None:
    paths = [*TEMPLATE_ROOT.rglob("*"), *POLICY_ROOT.rglob("*")]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.is_file())

    assert not re.search(r"TBD|TODO|稍后补充", text, flags=re.IGNORECASE)
