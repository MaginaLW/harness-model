"""Safe, deterministic parsing of Policy-defined V0 and V1 verification plans."""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

from aiflow.errors import ContractError
from aiflow.policy import PolicyBundle

V0_CHECK_IDS = ("contract", "scope", "ruff_check", "ruff_format_check", "smoke")
V1_EXTRA_CHECK_IDS = ("unit_tests", "regression_tests", "mypy", "coverage_xml", "diff_coverage")
V1_CHECK_IDS = V0_CHECK_IDS + V1_EXTRA_CHECK_IDS
ALLOWED_VARIABLES = frozenset(
    {"python", "repository_root", "base_commit", "subject_commit", "task_id", "run_dir"}
)
ALLOWED_PARSERS = frozenset({"exit_zero", "pytest", "coverage_xml", "diff_cover"})
_VARIABLE_PATTERN = re.compile(r"\{([^{}]+)\}")
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class VerificationContext:
    """All concrete values allowed to fill a Policy command once."""

    repository_root: Path
    task_id: str
    base_commit: str
    subject_commit: str
    python: str
    run_id: str
    ci_run_dir: Path | None = None


@dataclass(frozen=True)
class VerificationCheck:
    """One shell-free executable check in a stable category."""

    check_id: str
    level: str
    argv: tuple[str, ...]
    environment: Mapping[str, str]
    cwd: Path
    timeout_seconds: int
    required: bool
    result_parser: str
    threshold: int | None = None
    log_sensitivity: Literal["standard", "sensitive"] = "standard"


@dataclass(frozen=True)
class VerificationExecution:
    """One deduplicated process candidate retaining every evidence category."""

    execution_id: str
    argv: tuple[str, ...]
    environment: Mapping[str, str]
    cwd: Path
    timeout_seconds: int
    check_ids: tuple[str, ...]


@dataclass(frozen=True)
class VerificationPlan:
    """A parsed plan, including parse-time capability findings."""

    level: str
    run_dir: Path
    checks: tuple[VerificationCheck, ...]
    executions: tuple[VerificationExecution, ...]
    blocking_reasons: tuple[str, ...]
    unverified_check_ids: tuple[str, ...]
    comparison_subject: str

    @property
    def valid(self) -> bool:
        return not self.blocking_reasons


@dataclass(frozen=True)
class ParsedCheckResult:
    """Pure parser conclusion for a process result or threshold report."""

    conclusion: Literal["passed", "failed", "unverified"]
    reason_code: str | None = None


def _within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _strictly_within(path: Path, parent: Path) -> bool:
    return path != parent and _within(path, parent)


def _run_directory(context: VerificationContext) -> Path:
    root = context.repository_root.resolve()
    if not root.is_dir():
        raise ContractError(
            "Verification repository root is invalid", code="VERIFICATION_CWD_INVALID"
        )
    if not _RUN_ID_PATTERN.fullmatch(context.run_id):
        raise ContractError("Verification run ID is invalid", code="VERIFICATION_RUN_ID_INVALID")
    if context.ci_run_dir is None:
        run_dir = (root / ".ai" / "tasks" / context.task_id / "logs" / context.run_id).resolve()
        logs_root = (root / ".ai" / "tasks" / context.task_id / "logs").resolve()
        if not _within(logs_root, root) or not _strictly_within(run_dir, logs_root):
            raise ContractError(
                "Verification run directory escapes task logs", code="VERIFICATION_RUN_DIR_INVALID"
            )
        return run_dir
    ci_root = context.ci_run_dir.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not ci_root.is_dir() or not _strictly_within(ci_root, temp_root):
        raise ContractError(
            "CI run directory is not an operating-system temporary directory",
            code="CI_RUN_DIR_INVALID",
        )
    return ci_root


def _levels(bundle: PolicyBundle) -> Mapping[str, Mapping[str, object]]:
    document = bundle.documents.get("verification-levels.yaml")
    if not isinstance(document, Mapping) or not isinstance(document.get("levels"), list):
        raise ContractError("Verification Policy is invalid", code="VERIFICATION_POLICY_INVALID")
    raw_levels = [level for level in document["levels"] if isinstance(level, Mapping)]
    levels = {
        str(level.get("id")): level for level in raw_levels if isinstance(level.get("id"), str)
    }
    if set(levels) != {"V0", "V1"} or len(raw_levels) != 2:
        raise ContractError(
            "Verification Policy levels are invalid", code="VERIFICATION_POLICY_INVALID"
        )
    return levels


def _commands_for(level: Mapping[str, object]) -> Mapping[str, Mapping[str, object]]:
    checks = level.get("checks")
    if not isinstance(checks, list):
        return {}
    result: dict[str, Mapping[str, object]] = {}
    for check in checks:
        if isinstance(check, Mapping) and isinstance(check.get("id"), str):
            if str(check["id"]) in result:
                raise ContractError(
                    "Verification check IDs must be unique",
                    code="VERIFICATION_CATEGORY_DUPLICATE",
                )
            result[str(check["id"])] = check
    return result


def _required_ids(level: str) -> tuple[str, ...]:
    return V0_CHECK_IDS if level == "V0" else V1_CHECK_IDS


def _variables(context: VerificationContext, run_dir: Path) -> Mapping[str, str]:
    return {
        "python": context.python,
        "repository_root": context.repository_root.resolve().as_posix(),
        "base_commit": context.base_commit,
        "subject_commit": context.subject_commit,
        "task_id": context.task_id,
        "run_dir": run_dir.as_posix(),
    }


def _expand_once(value: str, variables: Mapping[str, str]) -> str:
    unknown = [name for name in _VARIABLE_PATTERN.findall(value) if name not in ALLOWED_VARIABLES]
    if unknown:
        raise ContractError(
            "Verification command has an unknown placeholder",
            code="VERIFICATION_PLACEHOLDER_INVALID",
        )
    expanded = _VARIABLE_PATTERN.sub(lambda match: variables[match.group(1)], value)
    if (
        _VARIABLE_PATTERN.search(expanded)
        or "{" in expanded
        or "}" in expanded
        or "$" in expanded
        or "`" in expanded
        or re.search(r"%[A-Za-z_][A-Za-z0-9_]*%", expanded)
    ):
        raise ContractError(
            "Verification placeholder expansion is nested or shell-like",
            code="VERIFICATION_PLACEHOLDER_INVALID",
        )
    return expanded


def _tool_available(argv: tuple[str, ...]) -> bool:
    program = argv[0]
    if len(argv) >= 3 and argv[1] == "-m":
        try:
            return find_spec(argv[2]) is not None
        except (ImportError, ValueError):
            return False
    if "/" in program or "\\" in program:
        return Path(program).is_file()
    adjacent = Path(sys.executable).resolve().parent / program
    return (
        shutil.which(program) is not None
        or adjacent.is_file()
        or adjacent.with_suffix(".exe").is_file()
    )


def _require_output_semantics(
    check: VerificationCheck, context: VerificationContext, run_dir: Path
) -> None:
    if check.check_id == "smoke" and check.argv[1:] != ("-m", "aiflow", "--help"):
        raise ContractError("Smoke command is invalid", code="VERIFICATION_COMMAND_INVALID")
    if check.check_id == "coverage_xml":
        expected_coverage = (run_dir / ".coverage").as_posix()
        expected_xml = (run_dir / "coverage.xml").as_posix()
        reports = [
            arg.removeprefix("--cov-report=xml:")
            for arg in check.argv
            if arg.startswith("--cov-report=xml:")
        ]
        if (
            check.argv[1:3] != ("-m", "pytest")
            or check.argv.count("--cov=aiflow") != 1
            or check.argv.count("--cov-branch") != 1
            or check.environment != {"COVERAGE_FILE": expected_coverage}
            or reports != [expected_xml]
        ):
            raise ContractError(
                "Coverage outputs must be bound to the run directory",
                code="VERIFICATION_COVERAGE_CONFIG_INVALID",
            )
    if check.check_id == "diff_coverage":
        expected_xml = (run_dir / "coverage.xml").as_posix()
        if (
            check.argv[0] != "diff-cover"
            or check.argv.count(expected_xml) != 1
            or check.argv.count("--compare-branch") != 1
            or check.argv.count("--fail-under") != 1
        ):
            raise ContractError(
                "Diff coverage configuration is invalid",
                code="VERIFICATION_DIFF_COVERAGE_CONFIG_INVALID",
            )
        try:
            compare = check.argv[check.argv.index("--compare-branch") + 1]
            threshold = check.argv[check.argv.index("--fail-under") + 1]
        except (ValueError, IndexError) as error:
            raise ContractError(
                "Diff coverage configuration is invalid",
                code="VERIFICATION_DIFF_COVERAGE_CONFIG_INVALID",
            ) from error
        if (
            expected_xml not in check.argv
            or compare != context.base_commit
            or threshold != "90"
            or check.threshold != 90
        ):
            raise ContractError(
                "Diff coverage configuration is invalid",
                code="VERIFICATION_DIFF_COVERAGE_CONFIG_INVALID",
            )


def _parse_check(
    raw: Mapping[str, object],
    *,
    level: str,
    context: VerificationContext,
    run_dir: Path,
    allowed_commands: set[str],
    allowed_environment: set[str],
) -> VerificationCheck:
    identifier = raw.get("id")
    command = raw.get("command")
    timeout = raw.get("timeout_seconds")
    parser = raw.get("result_parser")
    required = raw.get("required")
    threshold = raw.get("threshold")
    if not isinstance(identifier, str) or not isinstance(command, list) or not command:
        raise ContractError(
            "Verification check command is invalid", code="VERIFICATION_COMMAND_INVALID"
        )
    if not all(isinstance(argument, str) and argument for argument in command):
        raise ContractError(
            "Verification command must be an argument array", code="VERIFICATION_COMMAND_INVALID"
        )
    if command[0] not in allowed_commands:
        raise ContractError(
            "Verification command is not allowed", code="VERIFICATION_COMMAND_DENIED"
        )
    if not isinstance(timeout, int) or timeout <= 0:
        raise ContractError("Verification timeout is invalid", code="VERIFICATION_TIMEOUT_INVALID")
    if not isinstance(required, bool) or parser not in ALLOWED_PARSERS:
        raise ContractError(
            "Verification check metadata is invalid", code="VERIFICATION_CHECK_INVALID"
        )
    if threshold is not None and (not isinstance(threshold, int) or isinstance(threshold, bool)):
        raise ContractError("Verification threshold is invalid", code="VERIFICATION_CHECK_INVALID")
    variables = _variables(context, run_dir)
    argv = tuple(_expand_once(argument, variables) for argument in command)
    environment = raw.get("environment", {})
    if not isinstance(environment, Mapping) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in environment.items()
    ):
        raise ContractError("Verification environment is invalid", code="VERIFICATION_ENV_INVALID")
    if set(environment) - allowed_environment:
        raise ContractError(
            "Verification environment is not allowed", code="VERIFICATION_ENV_INVALID"
        )
    expanded_environment = {
        key: _expand_once(value, variables) for key, value in environment.items()
    }
    for value in expanded_environment.values():
        candidate = Path(value)
        if not candidate.is_absolute() or not _strictly_within(candidate.resolve(), run_dir):
            raise ContractError(
                "Verification environment escapes run directory", code="VERIFICATION_ENV_INVALID"
            )
    check = VerificationCheck(
        check_id=identifier,
        level=level,
        argv=argv,
        environment=expanded_environment,
        cwd=context.repository_root.resolve(),
        timeout_seconds=timeout,
        required=required,
        result_parser=str(parser),
        threshold=threshold,
    )
    _require_output_semantics(check, context, run_dir)
    return check


def parse_verification_plan(
    bundle: PolicyBundle,
    context: VerificationContext,
    *,
    level: Literal["V0", "V1"],
    tool_available: Callable[[tuple[str, ...]], bool] = _tool_available,
) -> VerificationPlan:
    """Parse exactly the selected V0/V1 Policy checks, without starting processes."""
    document = bundle.documents["verification-levels.yaml"]
    expected_placeholders = {f"{{{name}}}" for name in ALLOWED_VARIABLES}
    if (
        not isinstance(document, Mapping)
        or set(document.get("allowed_placeholders", [])) != expected_placeholders
    ):
        raise ContractError(
            "Verification placeholder allow-list is invalid",
            code="VERIFICATION_PLACEHOLDER_INVALID",
        )
    allowed_commands = (
        set(document.get("allowed_commands", [])) if isinstance(document, Mapping) else set()
    )
    allowed_environment = (
        set(document.get("allowed_environment", [])) if isinstance(document, Mapping) else set()
    )
    if allowed_commands != {"{python}", "diff-cover"} or allowed_environment != {"COVERAGE_FILE"}:
        raise ContractError(
            "Verification command or environment allow-list is invalid",
            code="VERIFICATION_POLICY_INVALID",
        )
    run_dir = _run_directory(context)
    levels = _levels(bundle)
    by_id = _commands_for(levels[level])
    required_ids = _required_ids(level)
    if set(by_id) != set(required_ids):
        raise ContractError(
            "Verification Policy check categories are incomplete or unknown",
            code="VERIFICATION_CATEGORY_MISSING",
        )
    if level == "V1":
        v0 = _commands_for(levels["V0"])
        if any(dict(by_id[check_id]) != dict(v0[check_id]) for check_id in V0_CHECK_IDS):
            raise ContractError(
                "V1 must contain the complete V0 checks",
                code="VERIFICATION_V1_PREFIX_INVALID",
            )
    checks = tuple(
        _parse_check(
            by_id[check_id],
            level=level,
            context=context,
            run_dir=run_dir,
            allowed_commands=allowed_commands,
            allowed_environment=allowed_environment,
        )
        for check_id in required_ids
    )
    grouped: dict[tuple[object, ...], list[str]] = {}
    execution_checks: dict[tuple[object, ...], VerificationCheck] = {}
    for check in checks:
        identity = (
            check.argv,
            tuple(sorted(check.environment.items())),
            check.cwd,
            check.log_sensitivity,
        )
        grouped.setdefault(identity, []).append(check.check_id)
        execution_checks.setdefault(identity, check)
    executions = tuple(
        VerificationExecution(
            execution_id=f"EXEC-{index:03d}",
            argv=execution_checks[identity].argv,
            environment=execution_checks[identity].environment,
            cwd=execution_checks[identity].cwd,
            timeout_seconds=max(
                check.timeout_seconds for check in checks if check.check_id in grouped[identity]
            ),
            check_ids=tuple(grouped[identity]),
        )
        for index, identity in enumerate(grouped, start=1)
    )
    blocking: list[str] = []
    unverified: list[str] = []
    for check in checks:
        if tool_available(check.argv):
            continue
        if check.required:
            blocking.append(f"VERIFICATION_TOOL_MISSING:{check.check_id}")
        else:
            unverified.append(check.check_id)
    return VerificationPlan(
        level,
        run_dir,
        checks,
        executions,
        tuple(sorted(blocking)),
        tuple(sorted(unverified)),
        context.subject_commit,
    )


def parse_check_result(
    check: VerificationCheck,
    *,
    returncode: int | None,
    output: str = "",
    coverage_xml_exists: bool = True,
) -> ParsedCheckResult:
    """Interpret runner facts deterministically, including the diff-cover 90% threshold."""
    if returncode is None:
        return ParsedCheckResult("unverified", "VERIFICATION_NO_RESULT")
    if returncode != 0:
        return ParsedCheckResult("failed", "VERIFICATION_COMMAND_FAILED")
    if check.result_parser == "coverage_xml" and not coverage_xml_exists:
        return ParsedCheckResult("failed", "VERIFICATION_COVERAGE_XML_MISSING")
    if check.result_parser == "diff_cover":
        if "No lines with coverage information in this diff." in output:
            return ParsedCheckResult("passed")
        match = re.search(r"(?:TOTAL|coverage)[^0-9]*([0-9]+(?:\.[0-9]+)?)%", output, re.I)
        if match is None:
            return ParsedCheckResult("failed", "VERIFICATION_DIFF_COVERAGE_UNPARSEABLE")
        try:
            threshold = float(check.threshold or check.argv[check.argv.index("--fail-under") + 1])
        except (ValueError, IndexError):
            return ParsedCheckResult("failed", "VERIFICATION_DIFF_COVERAGE_UNPARSEABLE")
        if float(match.group(1)) < threshold:
            return ParsedCheckResult("failed", "VERIFICATION_DIFF_COVERAGE_BELOW_THRESHOLD")
    return ParsedCheckResult("passed")
