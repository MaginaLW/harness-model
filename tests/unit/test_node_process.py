"""Exercise the actual Win32 runner state machine with a synthetic x64 kernel and Python."""

from __future__ import annotations

import ctypes as c
import os
import subprocess
import sys
from collections import Counter
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from aiflow import process_runner as runner


class FakeFunction:
    def __init__(self, kernel: FakeKernel, name: str):
        self.kernel, self.name = kernel, name

    def __call__(self, *args: Any) -> Any:
        return self.kernel.call(self.name, args)


class FakeKernel:
    """Only the APIs consumed by this private runner; no alternate launch implementation."""

    def __init__(
        self,
        *,
        output: tuple[bytes, bytes] = (b"stdout", b"stderr"),
        fail: tuple[str, int] | None = None,
        alive: bool = False,
        pipe_held: bool = False,
        children: bool = False,
    ):
        self.output = [bytearray(value) for value in output]
        self.fail = fail
        self.alive, self.pipe_held, self.children = alive, pipe_held, children
        self.calls: list[str] = []
        self.counts: Counter[str] = Counter()
        self.handles: set[int] = set()
        self.closed: list[int] = []
        self.inherited: list[int] = []
        self.clock = 0.0
        self.error = 0
        self.resumed = self.terminated = False
        self.flags = 0x2000
        self.member = True
        self.resume_count = 1
        self.wait_code: int | None = None
        self.read_count: int | None = None
        self.exit_code = 0
        self.pid = 300
        self.creation_time = 132537600000000001
        self.create_delay = 0.0
        self.query_active: int | None = None
        self.termination_effective = True
        self.bad_pipe_handles = False
        self.no_attribute_size = False
        self.null_handle: int | None = 20
        self.command = self.environment = ""
        self.functions: dict[str, FakeFunction] = {}

    def __getattr__(self, name: str) -> FakeFunction:
        return self.functions.setdefault(name, FakeFunction(self, name))

    @staticmethod
    def handle(value: Any) -> int:
        return int(value.value if hasattr(value, "value") else value)

    def sleep(self, _seconds: float) -> None:
        self.clock += 0.25

    def call(self, name: str, args: tuple[Any, ...]) -> Any:
        self.calls.append(name)
        self.counts[name] += 1
        if self.fail == (name, self.counts[name]):
            self.error = 5
            return 0xFFFFFFFF if name == "ResumeThread" else 0
        if name == "CreateJobObjectW":
            self.handles.add(1)
            return 1
        if name == "SetInformationJobObject":
            assert c.sizeof(args[2]._obj) == 144
            assert args[2]._obj.basic.flags == 0x2000
        elif name == "QueryInformationJobObject":
            if args[1] == 9:
                args[2]._obj.basic.flags = self.flags
            else:
                active = 0 if self.terminated else 1
                if self.resumed and not self.alive and not self.children:
                    active = 0
                args[2]._obj.active = active if self.query_active is None else self.query_active
        elif name == "CreatePipe":
            index = self.counts[name] - 1
            args[0]._obj.value = None if self.bad_pipe_handles else 10 + index * 2
            args[1]._obj.value = None if self.bad_pipe_handles else 11 + index * 2
            if not self.bad_pipe_handles:
                self.handles.update((10 + index * 2, 11 + index * 2))
            assert args[2]._obj.inherit == 1
            assert c.sizeof(args[2]._obj) == 24
        elif name == "SetHandleInformation":
            assert self.handle(args[0]) in (10, 12)
            assert args[1:] == (1, 0)
        elif name == "CreateFileW":
            assert args[0] == "NUL"
            if self.null_handle and self.null_handle != c.c_void_p(-1).value:
                self.handles.add(self.null_handle)
            return self.null_handle
        elif name == "InitializeProcThreadAttributeList":
            args[3]._obj.value = 0 if self.no_attribute_size else 64
            return int(args[0] is not None)
        elif name == "UpdateProcThreadAttribute":
            assert args[2] == 0x20002
            self.inherited = list(c.cast(args[3], c.POINTER(c.c_void_p * 3)).contents)
            assert self.inherited == [20, 11, 13]
        elif name == "CreateProcessW":
            assert args[4] is True
            assert args[5] == 0x4 | 0x400 | 0x80000 | 0x08000000
            assert args[8]._obj.cb == 112
            assert args[8]._obj.flags == 0x100
            assert (args[8]._obj.stdin, args[8]._obj.stdout, args[8]._obj.stderr) == (20, 11, 13)
            self.command = args[1].value
            self.environment = args[6][:]
            info = args[9]._obj
            assert c.sizeof(info) == 24
            info.process, info.thread = 30, 31
            info.process_id, info.thread_id = self.pid, 310
            self.handles.update((30, 31))
            self.clock += self.create_delay
        elif name == "GetProcessTimes":
            assert c.sizeof(args[1]._obj) == 8
            args[1]._obj.low = self.creation_time & 0xFFFFFFFF
            args[1]._obj.high = self.creation_time >> 32
        elif name == "IsProcessInJob":
            assert args[:2] == (30, 1)
            args[2]._obj.value = int(self.member)
        elif name == "ResumeThread":
            assert "AssignProcessToJobObject" in self.calls
            assert "IsProcessInJob" in self.calls
            assert 11 in self.closed and 13 in self.closed
            self.resumed = True
            return self.resume_count
        elif name == "PeekNamedPipe":
            index = (self.handle(args[0]) - 10) // 2
            if self.output[index]:
                args[4]._obj.value = len(self.output[index])
            elif self.pipe_held or (self.alive and not self.terminated):
                args[4]._obj.value = 0
            else:
                self.error = 109
                return 0
        elif name == "ReadFile":
            index = (self.handle(args[0]) - 10) // 2
            data = bytes(self.output[index][: args[2]])
            del self.output[index][: len(data)]
            c.memmove(args[1], data, len(data))
            args[3]._obj.value = len(data) if self.read_count is None else self.read_count
        elif name == "WaitForSingleObject":
            if self.wait_code is not None:
                return self.wait_code
            return 0x102 if self.alive and not self.terminated else 0
        elif name == "GetExitCodeProcess":
            args[1]._obj.value = 138 if self.terminated else self.exit_code
        elif name in {"TerminateJobObject", "TerminateProcess"}:
            self.terminated = self.termination_effective
        elif name == "CloseHandle":
            handle = self.handle(args[0])
            assert handle in self.handles, f"unexpected or duplicate close: {handle}"
            self.handles.remove(handle)
            self.closed.append(handle)
        elif name == "DeleteProcThreadAttributeList":
            return None
        return 1


@pytest.fixture
def kernel(monkeypatch: pytest.MonkeyPatch) -> FakeKernel:
    fake = FakeKernel()
    monkeypatch.setattr(runner, "_node_kernel", lambda: (fake, lambda: fake.error))
    monkeypatch.setattr(runner, "monotonic", lambda: fake.clock)
    monkeypatch.setattr(runner, "sleep", fake.sleep)
    return fake


def execute(tmp_path: Path, **kwargs: Any) -> runner.NodeProcessResult:
    return runner.run_node_process(
        kwargs.pop("argv", (sys.executable, "-c", "print('ok')")),
        cwd=kwargs.pop("cwd", tmp_path),
        environment=kwargs.pop("environment", {"SystemRoot": "synthetic", "a": "value"}),
        timeout_seconds=kwargs.pop("timeout_seconds", 1),
        **kwargs,
    )


def test_success_is_frozen_bounded_and_contained(kernel: FakeKernel, tmp_path: Path) -> None:
    result = execute(tmp_path)
    assert result == runner.NodeProcessResult(
        0, False, b"stdout", b"stderr", False, False, "confirmed", False, result.receipt
    )
    assert result.receipt == {
        "process_id": 300,
        "creation_time_filetime": 132537600000000001,
        "created_suspended": True,
        "assigned": True,
        "initial_membership": True,
        "resumed": True,
        "job_empty": True,
        "stdout_eof": True,
        "stderr_eof": True,
        "terminate_requested": False,
        "closed": True,
    }
    with pytest.raises(FrozenInstanceError):
        result.cleanup = "unknown"  # type: ignore[misc]
    assert kernel.inherited == [20, 11, 13]
    ordered = [
        "CreateJobObjectW",
        "SetInformationJobObject",
        "CreateProcessW",
        "AssignProcessToJobObject",
        "IsProcessInJob",
        "ResumeThread",
    ]
    assert [kernel.calls.index(name) for name in ordered] == sorted(
        kernel.calls.index(name) for name in ordered
    )
    assert not kernel.handles
    assert kernel.counts["DeleteProcThreadAttributeList"] == 1
    assert not kernel.terminated
    assert kernel.environment.startswith("a=value\0SystemRoot=synthetic\0\0")
    for name in ("ResumeThread", "WaitForSingleObject"):
        assert c.sizeof(kernel.functions[name].restype) == 4


@pytest.mark.parametrize("returncode", [1, 2147483648, 4294967295])
def test_exit_code_does_not_authenticate_success(
    kernel: FakeKernel, tmp_path: Path, returncode: int
) -> None:
    kernel.exit_code = returncode
    result = execute(tmp_path)
    assert result.returncode == returncode
    assert result.cleanup == "confirmed" and not result.execution_error


@pytest.mark.parametrize(
    "kwargs",
    [
        {"argv": ()},
        {"argv": []},
        {"argv": ("relative.exe",)},
        {"argv": (123,)},
        {"argv": (sys.executable, "bad\0arg")},
        {"argv": (sys.executable, "\ud800")},
        {"argv": (sys.executable, "a" * 32767)},
        {"cwd": Path("relative")},
        {"cwd": 1},
        {"cwd": Path(str(Path.cwd()) + "\0bad")},
        {"timeout_seconds": True},
        {"timeout_seconds": 1.5},
        {"timeout_seconds": 0},
        {"timeout_seconds": -1},
        {"timeout_seconds": 10**1000},
        {"environment": []},
        {"environment": {"": "value"}},
        {"environment": {"a=b": "value"}},
        {"environment": {"a": "bad\0value"}},
        {"environment": {1: "value"}},
        {"environment": {"a": 1}},
        {"environment": {"a": "1", "A": "2"}},
        {"environment": {"a": "\ud800"}},
    ],
)
def test_invalid_inputs_never_start(
    kernel: FakeKernel, tmp_path: Path, kwargs: dict[str, Any]
) -> None:
    result = execute(tmp_path, **kwargs)
    assert result.cleanup == "not_started" and result.execution_error
    assert result.stdout == result.stderr == b""
    assert not kernel.calls


def test_quoting_environment_and_utf16_boundary(kernel: FakeKernel, tmp_path: Path) -> None:
    argv = (sys.executable, 'a"b', "space here", "C:\\trailing path\\", "😀")
    assert execute(tmp_path, argv=argv, environment={}).cleanup == "confirmed"
    assert kernel.command == subprocess.list2cmdline(argv)
    assert kernel.environment == "\0\0\0"


@pytest.mark.parametrize(
    ("name", "occurrence"),
    [
        ("CreateJobObjectW", 1),
        ("SetInformationJobObject", 1),
        ("QueryInformationJobObject", 1),
        ("CreatePipe", 1),
        ("CreatePipe", 2),
        ("SetHandleInformation", 1),
        ("SetHandleInformation", 2),
        ("CreateFileW", 1),
        ("InitializeProcThreadAttributeList", 2),
        ("UpdateProcThreadAttribute", 1),
        ("CreateProcessW", 1),
        ("GetProcessTimes", 1),
        ("AssignProcessToJobObject", 1),
        ("IsProcessInJob", 1),
        ("QueryInformationJobObject", 2),
        ("ResumeThread", 1),
        ("PeekNamedPipe", 1),
        ("ReadFile", 1),
        ("GetExitCodeProcess", 1),
        ("CloseHandle", 1),
    ],
)
def test_api_failure_is_compact_and_releases_owned_handles(
    kernel: FakeKernel, tmp_path: Path, name: str, occurrence: int
) -> None:
    kernel.fail = name, occurrence
    result = execute(tmp_path)
    assert result.execution_error
    assert result.cleanup in {"not_started", "confirmed", "unknown"}
    assert not kernel.handles
    if "CreateProcessW" in kernel.calls and name != "CreateProcessW":
        assert kernel.terminated
    if name in {"AssignProcessToJobObject", "IsProcessInJob"}:
        assert "ResumeThread" not in kernel.calls
    if name == "AssignProcessToJobObject":
        assert "TerminateProcess" in kernel.calls
        assert "TerminateJobObject" not in kernel.calls


@pytest.mark.parametrize("flags", [0, 0x2000 | 0x800, 0x2000 | 0x1000])
def test_breakaway_or_missing_kill_flag_rejects_before_create(
    kernel: FakeKernel, tmp_path: Path, flags: int
) -> None:
    kernel.flags = flags
    result = execute(tmp_path)
    assert result.execution_error and result.cleanup == "not_started"
    assert "CreateProcessW" not in kernel.calls and not kernel.handles


@pytest.mark.parametrize("change", ["member", "active", "resume", "pipe", "attrs", "null"])
def test_unverified_setup_never_yields_success(
    kernel: FakeKernel, tmp_path: Path, change: str
) -> None:
    if change == "member":
        kernel.member = False
    elif change == "active":
        kernel.query_active = 2
    elif change == "resume":
        kernel.resume_count = 0
    elif change == "pipe":
        kernel.bad_pipe_handles = True
    elif change == "attrs":
        kernel.no_attribute_size = True
    else:
        kernel.null_handle = c.c_void_p(-1).value
    result = execute(tmp_path)
    assert result.execution_error
    assert not kernel.handles


@pytest.mark.parametrize("stream", [0, 1])
@pytest.mark.parametrize("extra", [0, 1, 65536])
def test_each_stream_has_a_hard_one_mib_storage_limit(
    kernel: FakeKernel, tmp_path: Path, stream: int, extra: int
) -> None:
    kernel.output[stream] = bytearray(b"x" * (1024 * 1024 + extra))
    result = execute(tmp_path, timeout_seconds=1200)
    assert len((result.stdout, result.stderr)[stream]) == 1024 * 1024
    assert (result.stdout_overflow, result.stderr_overflow)[stream] is bool(extra)
    assert result.cleanup == "confirmed" and not result.execution_error
    assert kernel.terminated is bool(extra)
    assert not kernel.handles


@pytest.mark.parametrize("mode", ["alive", "children", "pipe"])
def test_deadline_covers_parent_descendants_and_pipe_eof(
    kernel: FakeKernel, tmp_path: Path, mode: str
) -> None:
    kernel.alive = mode == "alive"
    kernel.children = mode == "children"
    kernel.pipe_held = mode == "pipe"
    result = execute(tmp_path)
    assert result.timed_out and kernel.terminated
    assert result.cleanup == ("unknown" if mode == "pipe" else "confirmed")
    assert not kernel.handles


@pytest.mark.parametrize("mode", ["wait", "read_zero", "read_large", "kill", "kill_ineffective"])
def test_cleanup_errors_remain_unverified(kernel: FakeKernel, tmp_path: Path, mode: str) -> None:
    if mode == "wait":
        kernel.wait_code = 0xFFFFFFFF
    elif mode.startswith("read"):
        kernel.read_count = 0 if mode == "read_zero" else 65536
    else:
        kernel.alive = True
        if mode == "kill":
            kernel.fail = "TerminateJobObject", 1
        else:
            kernel.termination_effective = False
    result = execute(tmp_path)
    assert result.execution_error
    assert not kernel.handles
    assert result.cleanup == "unknown"


def test_close_error_invalidates_confirmed_cleanup(kernel: FakeKernel, tmp_path: Path) -> None:
    kernel.fail = "CloseHandle", 3
    result = execute(tmp_path)
    assert result.execution_error and result.cleanup == "unknown"
    assert not kernel.handles
    assert result.receipt is not None and result.receipt["closed"] is True


def test_delete_attribute_error_is_execution_error(kernel: FakeKernel, tmp_path: Path) -> None:
    original = kernel.call

    def call(name: str, args: tuple[Any, ...]) -> Any:
        if name == "DeleteProcThreadAttributeList":
            raise OSError("private-local-path")
        return original(name, args)

    kernel.call = call  # type: ignore[method-assign]
    result = execute(tmp_path)
    assert result.execution_error and not kernel.handles
    assert b"private-local-path" not in result.stderr


def test_platform_or_loader_unavailable_is_not_started(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def unavailable() -> Any:
        raise OSError("private-loader-detail")

    monkeypatch.setattr(runner, "_node_kernel", unavailable)
    result = execute(tmp_path)
    assert result.cleanup == "not_started" and result.execution_error
    assert result.stderr == b""


def test_default_kernel_requires_windows_x64(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name == "nt":
        monkeypatch.setattr(runner.c, "sizeof", lambda _type: 4)
    with pytest.raises(OSError, match="Windows x64"):
        runner._node_kernel()


@pytest.mark.skipif(os.name != "nt", reason="real Windows Job process verification")
@pytest.mark.parametrize("mode", ["ok", "nonzero", "overflow", "timeout", "child", "child_pipe"])
def test_real_windows_owned_processes(tmp_path: Path, mode: str) -> None:
    scripts = {
        "ok": "import sys; print('out'); print('err', file=sys.stderr)",
        "nonzero": "raise SystemExit(7)",
        "overflow": "import os; os.write(1, b'x' * (1024 * 1024 + 1))",
        "timeout": "import time; time.sleep(30)",
        "child": (
            "import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
            "'import time; time.sleep(30)'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)"
        ),
        "child_pipe": (
            "import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
            "'import time; time.sleep(30)'])"
        ),
    }
    result = execute(
        tmp_path,
        argv=(sys.executable, "-I", "-c", scripts[mode]),
        environment={key: os.environ[key] for key in ("SystemRoot",) if key in os.environ},
        timeout_seconds=1 if mode in {"timeout", "child", "child_pipe"} else 10,
    )
    assert result.cleanup == "confirmed" and not result.execution_error
    assert result.receipt is not None
    assert type(result.receipt["process_id"]) is int and result.receipt["process_id"] > 0
    assert type(result.receipt["creation_time_filetime"]) is int
    assert result.receipt["creation_time_filetime"] > 10**17
    assert all(
        result.receipt[key] is True
        for key in (
            "created_suspended",
            "assigned",
            "initial_membership",
            "resumed",
            "job_empty",
            "stdout_eof",
            "stderr_eof",
            "closed",
        )
    )
    assert result.timed_out is (mode in {"timeout", "child", "child_pipe"})
    assert result.stdout_overflow is (mode == "overflow")
    if mode == "ok":
        assert result.stdout == b"out\r\n" and result.stderr == b"err\r\n"
    if mode in {"ok", "nonzero"}:
        assert result.returncode == (7 if mode == "nonzero" else 0)


@pytest.mark.skipif(os.name != "nt", reason="real Windows CreateProcess failure")
def test_real_windows_missing_program_never_started(tmp_path: Path) -> None:
    result = execute(tmp_path, argv=(str(tmp_path / "missing.exe"),))
    assert result.execution_error and result.cleanup == "not_started"


@pytest.mark.skipif(os.name != "nt", reason="real Windows Job descendant identity")
def test_real_windows_parent_child_and_grandchild_are_all_reaped(tmp_path: Path) -> None:
    grandchild = "import os,time; print(os.getpid(), flush=True); time.sleep(30)"
    child = (
        "import os,subprocess,sys,time; print(os.getpid(), flush=True); "
        f"subprocess.Popen([sys.executable,'-I','-c',{grandchild!r}]); time.sleep(30)"
    )
    parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-I','-c',{child!r}])"
    result = execute(
        tmp_path,
        argv=(sys.executable, "-I", "-c", parent),
        timeout_seconds=2,
        environment={key: os.environ[key] for key in ("SystemRoot",) if key in os.environ},
    )
    assert result.timed_out and result.cleanup == "confirmed" and not result.execution_error
    pids = [int(line) for line in result.stdout.splitlines()]
    assert len(pids) == 2
    kernel = c.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = c.c_void_p
    kernel.OpenProcess.argtypes = [c.c_uint32, c.c_int32, c.c_uint32]
    kernel.WaitForSingleObject.argtypes = [c.c_void_p, c.c_uint32]
    kernel.CloseHandle.argtypes = [c.c_void_p]
    for pid in pids:
        handle = kernel.OpenProcess(0x100000, False, pid)
        if handle:  # A fully released PID is also a confirmed exited owned process.
            try:
                assert kernel.WaitForSingleObject(handle, 0) == 0
            finally:
                assert kernel.CloseHandle(handle)


@pytest.mark.skipif(os.name != "nt", reason="real Windows simultaneous pipe capture")
def test_real_windows_reads_both_streams_and_waits_for_natural_child(tmp_path: Path) -> None:
    child = (
        "import os,threading; "
        "t=threading.Thread(target=lambda:os.write(2,b'e'*1048576)); "
        "t.start(); os.write(1,b'o'*1048576); t.join()"
    )
    parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-I','-c',{child!r}])"
    result = execute(
        tmp_path,
        argv=(sys.executable, "-I", "-c", parent),
        timeout_seconds=10,
        environment={key: os.environ[key] for key in ("SystemRoot",) if key in os.environ},
    )
    assert result.cleanup == "confirmed" and result.returncode == 0
    assert not result.execution_error and not result.timed_out
    assert not result.stdout_overflow and not result.stderr_overflow
    assert result.stdout == b"o" * 1048576 and result.stderr == b"e" * 1048576


@pytest.mark.skipif(os.name != "nt", reason="real Windows held pipe must not certify EOF")
def test_real_windows_external_pipe_holder_remains_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    kernel, last_error = runner._node_kernel()
    duplicate = c.c_void_p()
    kernel.GetCurrentProcess.restype = c.c_void_p
    kernel.DuplicateHandle.argtypes = [
        c.c_void_p,
        c.c_void_p,
        c.c_void_p,
        c.POINTER(c.c_void_p),
        c.c_uint32,
        c.c_int32,
        c.c_uint32,
    ]
    host_process = kernel.GetCurrentProcess()

    class PipeCreator:
        def __call__(self, *args: Any) -> Any:
            ok = kernel.CreatePipe(*args)
            if ok and not duplicate.value:
                assert kernel.DuplicateHandle(
                    host_process,
                    args[1]._obj,
                    host_process,
                    c.byref(duplicate),
                    0,
                    False,
                    2,
                )
            return ok

    class Kernel:
        CreatePipe = PipeCreator()

        def __getattr__(self, name: str) -> Any:
            return getattr(kernel, name)

    # Configure the real function too: the proxy receives the runner signature.
    kernel.CreatePipe.argtypes = [
        c.POINTER(c.c_void_p),
        c.POINTER(c.c_void_p),
        c.c_void_p,
        c.c_uint32,
    ]
    monkeypatch.setattr(runner, "_node_kernel", lambda: (Kernel(), last_error))
    try:
        result = execute(
            tmp_path,
            argv=(sys.executable, "-I", "-c", "print('owned')"),
            environment={key: os.environ[key] for key in ("SystemRoot",) if key in os.environ},
        )
        assert result.stdout == b"owned\r\n"
        assert result.timed_out and result.execution_error and result.cleanup == "unknown"
        assert result.receipt is not None
        assert result.receipt["job_empty"] is True and result.receipt["stdout_eof"] is False
        assert result.receipt["stderr_eof"] is True and result.receipt["closed"] is True
    finally:
        if duplicate.value:
            kernel.CloseHandle.argtypes = [c.c_void_p]
            assert kernel.CloseHandle(duplicate)


@pytest.mark.parametrize("mode", ["pid", "creation", "deadline"])
def test_process_identity_and_preparation_deadline_are_real_observations(
    kernel: FakeKernel,
    tmp_path: Path,
    mode: str,
) -> None:
    if mode == "pid":
        kernel.pid = 0
    elif mode == "creation":
        kernel.creation_time = 0
    else:
        kernel.create_delay = 2
    result = execute(tmp_path)
    assert result.execution_error and result.cleanup == "confirmed"
    assert result.timed_out is (mode == "deadline")
    assert not kernel.resumed and not kernel.handles
    assert result.receipt is not None
    assert result.receipt["resumed"] is False
    assert result.receipt["terminate_requested"] is True
    if mode == "pid":
        assert result.receipt["process_id"] == 0
        assert result.receipt["creation_time_filetime"] is None
    elif mode == "creation":
        assert result.receipt["creation_time_filetime"] is None


def test_persistent_release_failure_is_unknown(kernel: FakeKernel, tmp_path: Path) -> None:
    original = kernel.call

    def call(name: str, args: tuple[Any, ...]) -> Any:
        if name == "CloseHandle" and kernel.handle(args[0]) == 10:
            return 0
        return original(name, args)

    kernel.call = call  # type: ignore[method-assign]
    result = execute(tmp_path)
    assert result.execution_error and result.cleanup == "unknown"
    assert result.receipt is not None and result.receipt["closed"] is False
    assert kernel.handles == {10}


def test_missing_kernel_entry_is_compact_not_started(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class MissingKernel:
        def __getattr__(self, _name: str) -> Any:
            raise OSError("private-entry-error")

    monkeypatch.setattr(runner, "_node_kernel", lambda: (MissingKernel(), lambda: 0))
    result = execute(tmp_path)
    assert result.cleanup == "not_started" and result.execution_error
    assert result.receipt is None and result.stderr == b""
