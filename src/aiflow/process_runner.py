"""Shell-free verification execution with minimal environments and redacted logs."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

from aiflow.errors import ContractError
from aiflow.redaction import redact_command_summary, redact_text
from aiflow.verification import (
    VerificationCheck,
    VerificationExecution,
    parse_check_result,
)

_CHECK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ProcessResult:
    """One structured, replayable process outcome with only relative log references."""

    execution_id: str
    check_id: str
    command_summary: str
    started_at: str
    finished_at: str
    duration_ms: int
    returncode: int | None
    timed_out: bool
    stdout_log_ref: str
    stderr_log_ref: str
    conclusion: str
    reason_code: str | None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_run_dir(run_dir: Path, allowed_run_root: Path) -> Path:
    root = allowed_run_root.resolve()
    candidate = run_dir.resolve()
    if not _within(candidate, root) or candidate == root:
        raise ContractError(
            "Verification logs must stay within the approved run directory",
            code="RUNNER_RUN_DIR_INVALID",
        )
    candidate.mkdir(parents=True, exist_ok=True)
    resolved = candidate.resolve()
    if not _within(resolved, root):
        raise ContractError(
            "Verification logs escape the approved run directory", code="RUNNER_RUN_DIR_INVALID"
        )
    return resolved


def _environment(check: VerificationCheck, run_dir: Path) -> dict[str, str]:
    if set(check.environment) - {"COVERAGE_FILE"}:
        raise ContractError("Verification environment is not allowed", code="RUNNER_ENV_INVALID")
    path_entries = [entry for entry in os.defpath.split(os.pathsep) if entry]
    git_program = shutil.which("git")
    if git_program is not None:
        git_directory = str(Path(git_program).resolve().parent)
        if git_directory not in path_entries:
            path_entries.append(git_directory)
    environment = {"PATH": os.pathsep.join(path_entries)}
    if os.name == "nt" and os.environ.get("SystemRoot"):
        environment["SystemRoot"] = os.environ["SystemRoot"]
    coverage = check.environment.get("COVERAGE_FILE")
    if coverage is not None:
        path = Path(coverage).resolve()
        if not _within(path, run_dir):
            raise ContractError(
                "Coverage output escapes the run directory", code="RUNNER_ENV_INVALID"
            )
        environment["COVERAGE_FILE"] = str(path)
    return environment


def _log_refs(check_id: str, sequence: int) -> tuple[str, str]:
    if not _CHECK_ID_PATTERN.fullmatch(check_id) or sequence < 1:
        raise ContractError(
            "Verification check log identity is invalid", code="RUNNER_LOG_ID_INVALID"
        )
    prefix = f"{check_id}-{sequence:03d}"
    return f"{prefix}.stdout.log", f"{prefix}.stderr.log"


def _write_log(
    path: Path,
    content: str,
    *,
    sensitive_values: Sequence[str],
    extra_redaction_patterns: Sequence[str],
) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(
            redact_text(
                content,
                sensitive_values=sensitive_values,
                extra_patterns=extra_redaction_patterns,
            )
        )


def _resolved_argv(argv: tuple[str, ...]) -> tuple[str, ...]:
    if Path(argv[0]).is_absolute():
        return argv
    program = shutil.which(argv[0])
    if program is None:
        adjacent = Path(sys.executable).resolve().parent / argv[0]
        for candidate in (adjacent, adjacent.with_suffix(".exe")):
            if candidate.is_file():
                program = str(candidate)
                break
    return (program, *argv[1:]) if program is not None else argv


def run_execution(
    execution: VerificationExecution,
    checks: Mapping[str, VerificationCheck],
    *,
    run_dir: Path,
    allowed_run_root: Path,
    repository_root: Path,
    sequence: int,
    sensitive_values: Sequence[str] = (),
    extra_redaction_patterns: Sequence[str] = (),
) -> tuple[ProcessResult, ...]:
    """Execute a deduplicated argv once and return one parsed result per evidence category."""
    if not execution.check_ids or len(set(execution.check_ids)) != len(execution.check_ids):
        raise ContractError(
            "Verification execution check identities are invalid", code="RUNNER_EXECUTION_INVALID"
        )
    try:
        selected = tuple(checks[identifier] for identifier in execution.check_ids)
    except KeyError as error:
        raise ContractError(
            "Verification execution references an unknown check", code="RUNNER_EXECUTION_INVALID"
        ) from error
    if not selected or any(
        check.argv != execution.argv
        or check.cwd != execution.cwd
        or check.environment != execution.environment
        or check.timeout_seconds != execution.timeout_seconds
        for check in selected
    ):
        raise ContractError(
            "Verification execution does not match its checks", code="RUNNER_EXECUTION_INVALID"
        )
    cwd_root = repository_root.resolve()
    real_cwd = execution.cwd.resolve()
    if not cwd_root.is_dir() or not real_cwd.is_dir() or not _within(real_cwd, cwd_root):
        raise ContractError("Verification working directory is invalid", code="RUNNER_CWD_INVALID")
    directory = _validate_run_dir(run_dir, allowed_run_root)
    environment = _environment(selected[0], directory)
    if any(check.environment != selected[0].environment for check in selected):
        raise ContractError(
            "Deduplicated checks have different environments", code="RUNNER_EXECUTION_INVALID"
        )
    stdout_ref, stderr_ref = _log_refs(selected[0].check_id, sequence)
    started_at = _utc_now()
    started = monotonic()
    returncode: int | None = None
    timed_out = False
    execution_error = False
    stdout = ""
    stderr = ""
    argv = _resolved_argv(execution.argv)
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=real_cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        try:
            stdout, stderr = process.communicate(timeout=execution.timeout_seconds)
            returncode = process.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "nt":
                system_root = os.environ.get("SystemRoot", r"C:\\Windows")
                taskkill = Path(system_root) / "System32" / "taskkill.exe"
                try:
                    terminated = subprocess.run(
                        [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        timeout=5,
                        check=False,
                        shell=False,
                    )
                    if terminated.returncode != 0:
                        process.kill()
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
            else:
                kill_group = getattr(os, "killpg", None)
                kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
                if callable(kill_group):
                    kill_group(process.pid, kill_signal)
                else:
                    process.kill()
            stdout, stderr = process.communicate()
    except OSError as error:
        execution_error = True
        stderr = f"process execution unavailable: {error.__class__.__name__}"
    duration_ms = round((monotonic() - started) * 1000)
    finished_at = _utc_now()
    log_error = False
    try:
        _write_log(
            directory / stdout_ref,
            stdout,
            sensitive_values=sensitive_values,
            extra_redaction_patterns=extra_redaction_patterns,
        )
        _write_log(
            directory / stderr_ref,
            stderr,
            sensitive_values=sensitive_values,
            extra_redaction_patterns=extra_redaction_patterns,
        )
    except OSError:
        log_error = True
    result: list[ProcessResult] = []
    summary = redact_command_summary(
        execution.argv, sensitive_values=sensitive_values, extra_patterns=extra_redaction_patterns
    )
    for check in selected:
        parsed = (
            parse_check_result(
                check,
                returncode=returncode,
                output=stdout + "\n" + stderr,
                coverage_xml_exists=(directory / "coverage.xml").is_file(),
            )
            if not timed_out and not execution_error
            else None
        )
        result.append(
            ProcessResult(
                execution.execution_id,
                check.check_id,
                summary,
                started_at,
                finished_at,
                duration_ms,
                returncode,
                timed_out,
                stdout_ref,
                stderr_ref,
                "failed"
                if timed_out or execution_error or log_error
                else (parsed.conclusion if parsed else "failed"),
                "RUNNER_TIMEOUT"
                if timed_out
                else (
                    "RUNNER_EXECUTION_FAILED"
                    if execution_error
                    else (
                        "RUNNER_LOG_WRITE_FAILED"
                        if log_error
                        else (parsed.reason_code if parsed else None)
                    )
                ),
            )
        )
    return tuple(result)
