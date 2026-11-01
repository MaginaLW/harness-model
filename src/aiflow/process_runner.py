"""Shell-free verification execution with minimal environments and redacted logs."""

from __future__ import annotations

import ctypes as c
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from typing import Any, Literal

from aiflow.errors import ContractError
from aiflow.redaction import redact_command_summary, redact_text
from aiflow.state import utc_timestamp
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


def _within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _summary_paths(summary: str, *, repository_root: Path, run_dir: Path) -> str:
    """Replace known local paths in display text without changing execution arguments."""
    paths = (
        (sys.executable, "${PYTHON}"),
        (str(run_dir), "${RUN_DIR}"),
        (str(repository_root), "${REPO_ROOT}"),
    )
    for path, placeholder in sorted(paths, key=lambda item: len(item[0]), reverse=True):
        if not path:
            continue
        path_pattern = (
            r"[\\/]".join(re.escape(part) for part in re.split(r"[\\/]", path))
            if os.name == "nt"
            else re.escape(path)
        )
        pattern = re.compile(
            r"(?<![\w.\\/~+-])" + path_pattern + r"(?![\w.~+-])",
            re.IGNORECASE if os.name == "nt" else 0,
        )
        summary = pattern.sub(lambda _match: placeholder, summary)
    return summary


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


def _temporary_root() -> Path:
    selected = next(
        (os.environ[key] for key in ("TMPDIR", "TEMP", "TMP") if key in os.environ), None
    )
    root = Path(selected) if selected is not None else Path(tempfile.gettempdir())
    if not root.is_absolute():
        raise ContractError("Temporary root must be absolute", code="RUNNER_TEMP_ROOT_INVALID")
    try:
        for ancestor in (root, *root.parents):
            info = ancestor.lstat()
            if (
                not stat.S_ISDIR(info.st_mode)
                or stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise ContractError(
                    "Temporary root must have ordinary directory ancestors",
                    code="RUNNER_TEMP_ROOT_INVALID",
                )
        return root.resolve(strict=True)
    except OSError as error:
        raise ContractError(
            "Temporary root is unavailable", code="RUNNER_TEMP_ROOT_INVALID"
        ) from error


def _environment(check: VerificationCheck, run_dir: Path, temporary_root: Path) -> dict[str, str]:
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
    try:
        temporary = Path(tempfile.mkdtemp(prefix="aiflow-check-", dir=temporary_root))
    except OSError as error:
        raise ContractError(
            "Could not create an owned temporary directory", code="RUNNER_TEMP_ROOT_INVALID"
        ) from error
    environment.update({key: str(temporary) for key in ("TEMP", "TMP", "TMPDIR")})
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
    temporary_root = _temporary_root()
    directory = _validate_run_dir(run_dir, allowed_run_root)
    environment = _environment(selected[0], directory, temporary_root)
    if any(check.environment != selected[0].environment for check in selected):
        raise ContractError(
            "Deduplicated checks have different environments", code="RUNNER_EXECUTION_INVALID"
        )
    stdout_ref, stderr_ref = _log_refs(selected[0].check_id, sequence)
    started_at = utc_timestamp()
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
            creationflags=(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP") if os.name == "nt" else 0
            ),
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
    finished_at = utc_timestamp()
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
    summary = _summary_paths(summary, repository_root=cwd_root, run_dir=directory)
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


@dataclass(frozen=True)
class NodeProcessResult:
    """Bounded process observations; these do not authenticate execution inputs."""

    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    stdout_overflow: bool
    stderr_overflow: bool
    cleanup: Literal["confirmed", "unknown", "not_started"]
    execution_error: bool
    receipt: Mapping[str, object] | None = None


def _node_kernel() -> tuple[Any, Callable[[], int]]:
    """Private API seam: the same Win32 state machine runs with synthetic kernels in CI."""
    if os.name != "nt" or c.sizeof(c.c_void_p) != 8:
        raise OSError("Windows x64 process support unavailable")
    return getattr(c, "WinDLL")("kernel32", use_last_error=True), getattr(c, "get_last_error")


def run_node_process(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: int,
) -> NodeProcessResult:
    """Run a caller-authenticated command in a new Windows Job with bounded output.

    This contains owned descendants, not hostile tools or OS components. The caller
    authenticates argv, environment, executable and materials before entering here,
    and must block dependent work unless cleanup is confirmed.
    """
    unavailable = NodeProcessResult(None, False, b"", b"", False, False, "not_started", True)
    try:
        if (
            type(argv) is not tuple
            or not argv
            or any(not isinstance(arg, str) or "\0" in arg for arg in argv)
            or not Path(argv[0]).is_absolute()
            or not isinstance(cwd, Path)
            or not cwd.is_absolute()
            or "\0" in str(cwd)
            or type(timeout_seconds) is not int
            or timeout_seconds <= 0
            or not isinstance(environment, Mapping)
            or any(
                not isinstance(key, str)
                or not isinstance(value, str)
                or not key
                or "=" in key
                or "\0" in key + value
                for key, value in environment.items()
            )
            or len({key.casefold() for key in environment}) != len(environment)
        ):
            return unavailable
        command_text = subprocess.list2cmdline(argv)
        if len(command_text.encode("utf-16-le")) > 65532:
            return unavailable
        env_text = "\0".join(
            f"{key}={environment[key]}" for key in sorted(environment, key=str.casefold)
        )
        (env_text + str(cwd)).encode("utf-16-le")
        deadline = monotonic() + timeout_seconds
        kernel, last_error = _node_kernel()
    except (OSError, ValueError, TypeError, OverflowError):
        return unavailable

    class SecurityAttributes(c.Structure):
        _fields_ = [("length", c.c_uint32), ("descriptor", c.c_void_p), ("inherit", c.c_int32)]

    class StartupInfo(c.Structure):
        _fields_ = [
            ("cb", c.c_uint32),
            ("reserved", c.c_wchar_p),
            ("desktop", c.c_wchar_p),
            ("title", c.c_wchar_p),
            ("x", c.c_uint32),
            ("y", c.c_uint32),
            ("xsize", c.c_uint32),
            ("ysize", c.c_uint32),
            ("xcount", c.c_uint32),
            ("ycount", c.c_uint32),
            ("fill", c.c_uint32),
            ("flags", c.c_uint32),
            ("show", c.c_uint16),
            ("reserved_size", c.c_uint16),
            ("reserved_bytes", c.c_void_p),
            ("stdin", c.c_void_p),
            ("stdout", c.c_void_p),
            ("stderr", c.c_void_p),
        ]

    class StartupInfoEx(c.Structure):
        _fields_ = [("startup", StartupInfo), ("attributes", c.c_void_p)]

    class ProcessInformation(c.Structure):
        _fields_ = [
            ("process", c.c_void_p),
            ("thread", c.c_void_p),
            ("process_id", c.c_uint32),
            ("thread_id", c.c_uint32),
        ]

    class FileTime(c.Structure):
        _fields_ = [("low", c.c_uint32), ("high", c.c_uint32)]

    class BasicLimit(c.Structure):
        _fields_ = [
            ("process_time", c.c_longlong),
            ("job_time", c.c_longlong),
            ("flags", c.c_uint32),
            ("min_working_set", c.c_size_t),
            ("max_working_set", c.c_size_t),
            ("active_limit", c.c_uint32),
            ("affinity", c.c_size_t),
            ("priority", c.c_uint32),
            ("scheduling", c.c_uint32),
        ]

    class IoCounters(c.Structure):
        _fields_ = [
            (name, c.c_ulonglong)
            for name in (
                "read_operations",
                "write_operations",
                "other_operations",
                "read_bytes",
                "write_bytes",
                "other_bytes",
            )
        ]

    class ExtendedLimit(c.Structure):
        _fields_ = [
            ("basic", BasicLimit),
            ("io", IoCounters),
            ("process_memory", c.c_size_t),
            ("job_memory", c.c_size_t),
            ("peak_process_memory", c.c_size_t),
            ("peak_job_memory", c.c_size_t),
        ]

    class Accounting(c.Structure):
        _fields_ = [
            ("user", c.c_longlong),
            ("kernel", c.c_longlong),
            ("period_user", c.c_longlong),
            ("period_kernel", c.c_longlong),
            ("faults", c.c_uint32),
            ("total", c.c_uint32),
            ("active", c.c_uint32),
            ("terminated", c.c_uint32),
        ]

    def api(name: str, result: object, args: list[object]) -> Any:
        function = getattr(kernel, name)
        function.restype, function.argtypes = result, args
        return function

    try:
        handle, dword, boolean = c.c_void_p, c.c_uint32, c.c_int32
        create_job = api("CreateJobObjectW", handle, [c.c_void_p, c.c_wchar_p])
        set_job = api("SetInformationJobObject", boolean, [handle, dword, c.c_void_p, dword])
        query_job = api(
            "QueryInformationJobObject",
            boolean,
            [handle, dword, c.c_void_p, dword, c.POINTER(dword)],
        )
        create_pipe = api(
            "CreatePipe",
            boolean,
            [c.POINTER(handle), c.POINTER(handle), c.POINTER(SecurityAttributes), dword],
        )
        set_handle = api("SetHandleInformation", boolean, [handle, dword, dword])
        create_file = api(
            "CreateFileW",
            handle,
            [c.c_wchar_p, dword, dword, c.POINTER(SecurityAttributes), dword, dword, handle],
        )
        init_attrs = api(
            "InitializeProcThreadAttributeList",
            boolean,
            [c.c_void_p, dword, dword, c.POINTER(c.c_size_t)],
        )
        update_attr = api(
            "UpdateProcThreadAttribute",
            boolean,
            [c.c_void_p, dword, c.c_size_t, c.c_void_p, c.c_size_t, c.c_void_p, c.c_void_p],
        )
        delete_attrs = api("DeleteProcThreadAttributeList", None, [c.c_void_p])
        create_process = api(
            "CreateProcessW",
            boolean,
            [
                c.c_wchar_p,
                c.c_wchar_p,
                c.c_void_p,
                c.c_void_p,
                boolean,
                dword,
                c.c_void_p,
                c.c_wchar_p,
                c.POINTER(StartupInfo),
                c.POINTER(ProcessInformation),
            ],
        )
        assign_job = api("AssignProcessToJobObject", boolean, [handle, handle])
        resume = api("ResumeThread", dword, [handle])
        peek = api(
            "PeekNamedPipe",
            boolean,
            [handle, c.c_void_p, dword, c.c_void_p, c.POINTER(dword), c.c_void_p],
        )
        read = api("ReadFile", boolean, [handle, c.c_void_p, dword, c.POINTER(dword), c.c_void_p])
        terminate_job = api("TerminateJobObject", boolean, [handle, c.c_uint32])
        terminate_process = api("TerminateProcess", boolean, [handle, c.c_uint32])
        wait = api("WaitForSingleObject", dword, [handle, dword])
        get_exit = api("GetExitCodeProcess", boolean, [handle, c.POINTER(dword)])
        close = api("CloseHandle", boolean, [handle])

        is_in_job = api("IsProcessInJob", boolean, [handle, handle, c.POINTER(boolean)])
        get_times = api("GetProcessTimes", boolean, [handle, *([c.POINTER(FileTime)] * 4)])
    except Exception:
        return unavailable

    def require(ok: object) -> None:
        if not ok:
            raise OSError("Windows process operation failed")

    def active_count() -> int:
        info = Accounting()
        require(query_job(job, 1, c.byref(info), c.sizeof(info), None))
        receipt["job_empty"] = info.active == 0
        return int(info.active)

    job = null = None
    reads: list[int] = []
    writes: list[int] = []
    attributes = None
    attrs_initialized = False
    process = ProcessInformation()
    assigned = False
    cleanup: Literal["confirmed", "unknown", "not_started"] = "not_started"
    execution_error = timed_out = False
    overflow = [False, False]
    outputs = [bytearray(), bytearray()]
    eof = [False, False]
    returncode = None
    limit = 1024 * 1024
    receipt: dict[str, object] = {
        "process_id": None,
        "creation_time_filetime": None,
        "created_suspended": False,
        "assigned": False,
        "initial_membership": False,
        "resumed": False,
        "job_empty": False,
        "stdout_eof": False,
        "stderr_eof": False,
        "terminate_requested": False,
        "closed": False,
    }

    def drain() -> None:
        # Peek makes each ReadFile nonblocking. Alternate streams rather than waiting
        # for EOF on either; after overflow discard bounded chunks so EOF is observable.
        for index, reader_handle in enumerate(reads):
            if eof[index]:
                continue
            available = dword()
            if not peek(reader_handle, None, 0, None, c.byref(available), None):
                if last_error() == 109:  # ERROR_BROKEN_PIPE: no buffered bytes remain.
                    eof[index] = True
                    continue
                raise OSError("Pipe observation failed")
            if available.value:
                remaining = limit - len(outputs[index])
                count = min(available.value, 16384, remaining + 1 if remaining else 16384)
                buffer = c.create_string_buffer(count)
                got = dword()
                require(read(reader_handle, buffer, count, c.byref(got), None))
                if not 0 < got.value <= count:
                    raise OSError("Pipe read count is invalid")
                outputs[index].extend(buffer.raw[: min(got.value, remaining)])
                overflow[index] |= got.value > remaining

    def completed() -> bool:
        nonlocal returncode
        observed_wait = wait(process.process, 0)
        if observed_wait not in (0, 0x102):
            raise OSError("Process wait failed")
        empty = active_count() == 0 if assigned else True
        if observed_wait == 0 and empty and all(eof):
            exit_code = dword()
            require(get_exit(process.process, c.byref(exit_code)))
            returncode = int(exit_code.value)
            return True
        return False

    def close_writers() -> None:
        while writes:
            require(close(writes[-1]))
            writes.pop()

    try:
        job = create_job(None, None)
        require(job)
        limits = ExtendedLimit()
        limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE; no breakaway flags.
        require(set_job(job, 9, c.byref(limits), c.sizeof(limits)))
        observed = ExtendedLimit()
        require(query_job(job, 9, c.byref(observed), c.sizeof(observed), None))
        if observed.basic.flags != 0x2000:
            raise OSError("Job limits could not be verified")
        security = SecurityAttributes(c.sizeof(SecurityAttributes), None, True)
        for _ in range(2):
            reader, writer = handle(), handle()
            require(create_pipe(c.byref(reader), c.byref(writer), c.byref(security), 0))
            assert reader.value is not None and writer.value is not None
            reads.append(reader.value)
            writes.append(writer.value)
            require(set_handle(reader, 1, 0))
        null = create_file("NUL", 0x80000000, 3, c.byref(security), 3, 0, None)
        require(null and null != c.c_void_p(-1).value)
        size = c.c_size_t()
        init_attrs(None, 1, 0, c.byref(size))
        require(size.value)
        attribute_buffer = c.create_string_buffer(size.value)
        attributes = c.cast(attribute_buffer, c.c_void_p)
        require(init_attrs(attributes, 1, 0, c.byref(size)))
        attrs_initialized = True
        inherited = (handle * 3)(null, *writes)
        require(
            update_attr(
                attributes,
                0,
                0x20002,
                c.cast(inherited, c.c_void_p),
                c.sizeof(inherited),
                None,
                None,
            )
        )
        startup = StartupInfoEx()
        startup.startup.cb = c.sizeof(startup)
        startup.startup.flags = 0x100
        startup.startup.stdin, startup.startup.stdout, startup.startup.stderr = null, *writes
        startup.attributes = attributes
        command = c.create_unicode_buffer(command_text)
        env_block = c.create_unicode_buffer(env_text + "\0\0")
        require(
            create_process(
                argv[0],
                command,
                None,
                None,
                True,
                0x4 | 0x400 | 0x80000 | 0x08000000,
                env_block,
                str(cwd),
                c.byref(startup.startup),
                c.byref(process),
            )
        )
        cleanup = "unknown"
        receipt["created_suspended"] = True
        receipt["process_id"] = int(process.process_id)
        if not process.process_id:
            raise OSError("Process identity is unavailable")
        created, exited, kernel_time, user_time = (FileTime() for _ in range(4))
        require(
            get_times(
                process.process,
                c.byref(created),
                c.byref(exited),
                c.byref(kernel_time),
                c.byref(user_time),
            )
        )
        creation_time = (int(created.high) << 32) | int(created.low)
        if not creation_time:
            raise OSError("Process creation identity is unavailable")
        receipt["creation_time_filetime"] = creation_time
        require(assign_job(job, process.process))
        assigned = True
        receipt["assigned"] = True
        membership = boolean()
        require(is_in_job(process.process, job, c.byref(membership)))
        if not membership.value or active_count() != 1:
            raise OSError("Initial Job membership is unknown")
        receipt["initial_membership"] = True
        close_writers()
        if monotonic() >= deadline:
            timed_out = True
            raise TimeoutError("Process preparation exhausted the deadline")
        if resume(process.thread) != 1:
            raise OSError("Primary thread resume failed")
        receipt["resumed"] = True
        while True:
            drain()
            done = completed()
            if monotonic() >= deadline:
                timed_out = True
            if timed_out or any(overflow):
                break
            if done:
                cleanup = "confirmed"
                break
            sleep(0.005)
    except Exception:
        # Never expose arbitrary Windows error text or local input paths in receipts.
        execution_error = True
    finally:
        if process.process and cleanup != "confirmed":
            try:
                close_writers()
                receipt["terminate_requested"] = True
                terminated = (
                    terminate_job(job, 138) if assigned else terminate_process(process.process, 138)
                )
                if not terminated:
                    execution_error = True
                stop_deadline = monotonic() + 5
                while True:
                    drain()
                    if completed():
                        cleanup = "confirmed"
                        break
                    if monotonic() >= stop_deadline:
                        execution_error = True
                        break
                    sleep(0.005)
            except Exception:
                execution_error = True
        # A failed close is observable even if termination had already been confirmed.
        all_closed = True
        for item in (*writes, *reads, null, process.thread, process.process, job):
            if item and item != c.c_void_p(-1).value:
                try:
                    require(close(item))
                except Exception:
                    execution_error = True
                    if process.process:
                        cleanup = "unknown"
                    # Retry a failed release once; never infer closure from an error.
                    try:
                        require(close(item))
                    except Exception:
                        all_closed = False
        if attrs_initialized:
            try:
                delete_attrs(attributes)
            except Exception:
                execution_error = True
                all_closed = False
        receipt["stdout_eof"], receipt["stderr_eof"] = eof
        receipt["closed"] = all_closed
    return NodeProcessResult(
        returncode,
        timed_out,
        bytes(outputs[0]),
        bytes(outputs[1]),
        overflow[0],
        overflow[1],
        cleanup,
        execution_error,
        receipt,
    )
