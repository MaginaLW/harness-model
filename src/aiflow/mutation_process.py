"""Bounded capture of native detector reports using the owned Windows Job runner."""

from __future__ import annotations

import hashlib
import sys
import sysconfig
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from aiflow.errors import ContractError
from aiflow.mutation_protocol import EARLY_STOP_EXIT_CODE, PYTEST_VERSION, PYTHON_VERSION
from aiflow.process_runner import NodeProcessResult, run_node_process

_MAX_REPORT_BYTES = 16 * 1024


@dataclass(frozen=True)
class ProcessLifecycle:
    """Whitelist of completed Job and pipe observations bound to one report."""

    created_suspended: bool
    assigned: bool
    initial_membership: bool
    resumed: bool
    job_empty: bool
    stdout_eof: bool
    stderr_eof: bool
    closed: bool
    terminate_requested: bool
    returncode: int
    report_sha256: str

    def completed_naturally(self) -> bool:
        return self.terminate_requested is False and all(
            fact is True
            for fact in (
                self.created_suspended,
                self.assigned,
                self.initial_membership,
                self.resumed,
                self.job_empty,
                self.stdout_eof,
                self.stderr_eof,
                self.closed,
            )
        )

    def matches_observation(self, report: bytes, exit_code: int) -> bool:
        return (
            self.completed_naturally()
            and type(report) is bytes
            and 0 < len(report) <= _MAX_REPORT_BYTES
            and type(exit_code) is int
            and exit_code in (0, 1)
            and type(self.returncode) is int
            and self.returncode == exit_code
            and type(self.report_sha256) is str
            and self.report_sha256 == hashlib.sha256(report).hexdigest()
        )


@dataclass(frozen=True)
class ProcessOutcome:
    """Report bytes are available only following verified process and pipe closure."""

    returncode: int | None
    report: bytes | None
    reason: str | None
    cleanup_unknown: bool
    duration_ms: int
    lifecycle: ProcessLifecycle | None = None


def preflight_mutation_runtime(cwd: Path, environment: Mapping[str, str]) -> None:
    """Run only a fixed interpreter/version check under the detector's Windows Job."""
    if sys.platform != "win32" or sysconfig.get_platform() != "win-amd64":
        raise ContractError(
            "Mutation process containment is unavailable", code="MUTATION_EVIDENCE_INPUT_MISMATCH"
        )
    # Both this check and the reporter load pytest from the selected interpreter,
    # before the reporter opens the reviewed test sources in its isolated checkout.
    script = (
        "import sys, pytest; "
        "sys.stdout.buffer.write("
        "f'{sys.version_info.major}.{sys.version_info.minor} {pytest.__version__}'.encode('ascii'))"
    )
    outcome = run_bounded_process(
        (sys.executable, "-I", "-B", "-c", script),
        cwd=cwd,
        env=environment,
        timeout_seconds=10,
        max_output_bytes=64,
    )
    if (
        outcome.reason is not None
        or outcome.returncode != 0
        or outcome.report != f"{PYTHON_VERSION} {PYTEST_VERSION}".encode("ascii")
    ):
        raise ContractError(
            "The controlled Python and pytest runtime could not be verified",
            code="MUTATION_EVIDENCE_INPUT_MISMATCH",
        )


def _lifecycle(result: NodeProcessResult, exit_code: int) -> ProcessLifecycle:
    observed = result.receipt or {}
    return ProcessLifecycle(
        created_suspended=observed.get("created_suspended") is True,
        assigned=observed.get("assigned") is True,
        initial_membership=observed.get("initial_membership") is True,
        resumed=observed.get("resumed") is True,
        job_empty=observed.get("job_empty") is True,
        stdout_eof=observed.get("stdout_eof") is True,
        stderr_eof=observed.get("stderr_eof") is True,
        closed=observed.get("closed") is True,
        terminate_requested=observed.get("terminate_requested") is not False,
        returncode=exit_code,
        report_sha256=hashlib.sha256(result.stdout).hexdigest(),
    )


def run_bounded_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
    max_output_bytes: int = _MAX_REPORT_BYTES,
) -> ProcessOutcome:
    """Capture one report with the same deadline for process exit, Job and EOF."""
    if (
        not argv
        or type(timeout_seconds) is not int
        or timeout_seconds <= 0
        or type(max_output_bytes) is not int
        or not 0 < max_output_bytes <= _MAX_REPORT_BYTES
    ):
        return ProcessOutcome(None, None, "invalid_input", False, 0)

    started = monotonic()
    result = run_node_process(
        tuple(argv),
        cwd=cwd,
        environment=env,
        timeout_seconds=timeout_seconds,
        max_output_bytes=max_output_bytes,
    )
    duration = round((monotonic() - started) * 1000)
    unknown = result.cleanup == "unknown"
    if result.timed_out:
        return ProcessOutcome(result.returncode, None, "timeout", unknown, duration)
    if result.stdout_overflow or result.stderr_overflow or len(result.stdout) > max_output_bytes:
        return ProcessOutcome(result.returncode, None, "overflow", unknown, duration)
    if result.cleanup != "confirmed" or result.execution_error:
        return ProcessOutcome(result.returncode, None, "execution_error", unknown, duration)
    if result.returncode == EARLY_STOP_EXIT_CODE and not result.stdout and not result.stderr:
        if not _lifecycle(result, result.returncode).completed_naturally():
            return ProcessOutcome(result.returncode, None, "cleanup_unknown", True, duration)
        return ProcessOutcome(result.returncode, None, "pytest_early_stop", False, duration)
    if result.stderr or result.returncode not in (0, 1) or not result.stdout:
        return ProcessOutcome(result.returncode, None, "report_incomplete", False, duration)
    receipt = _lifecycle(result, result.returncode)
    if not receipt.matches_observation(result.stdout, result.returncode):
        return ProcessOutcome(result.returncode, None, "cleanup_unknown", True, duration)
    return ProcessOutcome(result.returncode, result.stdout, None, False, duration, receipt)
