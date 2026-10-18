"""Exercise the byte and lifetime limits of the local Git body reader."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/analysis/approval_overhead.py"
LIMIT = 1024 * 1024
ERROR = "snapshot: committed Git inputs could not be read"
LIMIT_ERROR = "snapshot: committed Git output exceeds read limit"
ARGUMENT_ERROR = "snapshot: bounded Git reads require a nonnegative limit and no stdin"
PRIVATE = "PRIVATE_CHILD_FAILURE_DO_NOT_ECHO"


@pytest.fixture
def bounded_git() -> Any:
    spec = importlib.util.spec_from_file_location("bounded_snapshot_git", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repository: Path, *arguments: str, data: bytes | None = None) -> bytes:
    environment = {
        key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")
    }
    environment.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
    )
    return subprocess.run(
        ["git", "--no-pager", "-C", str(repository), *arguments],
        input=data,
        capture_output=True,
        check=True,
        timeout=10,
        env=environment,
    ).stdout


def _blob(repository: Path, data: bytes) -> str:
    _git(repository, "init", "--quiet")
    return _git(repository, "hash-object", "-w", "--stdin", data=data).decode().strip()


@pytest.fixture
def observe_processes(bounded_git: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    native_popen = subprocess.Popen

    def install(
        *,
        short_read: int | None = None,
        read_error: bool = False,
        pipe_eof: bool = False,
        child_script: str | None = None,
    ) -> list[dict[str, Any]]:
        observed: list[dict[str, Any]] = []

        def launch(command: list[str], **options: Any) -> Any:
            if child_script is not None:
                command = [sys.executable, "-c", child_script]
            process = native_popen(command, **options)
            assert process.stdout is not None
            raw = process.stdout
            record: dict[str, Any] = {
                "process": process,
                "command": command,
                "options": options,
                "reads": [],
                "chunks": [],
                "kills": 0,
                "waits": 0,
                "wait_started": threading.Event(),
            }

            class ObservedPipe:
                def read(self, size: int) -> bytes:
                    record["reads"].append(size)
                    if read_error:
                        raise OSError(PRIVATE)
                    contents = (
                        b"" if pipe_eof else raw.read(min(size, short_read) if short_read else size)
                    )
                    record["chunks"].append(len(contents))
                    return contents

                def __getattr__(self, name: str) -> Any:
                    return getattr(raw, name)

            native_kill, native_wait = process.kill, process.wait

            def kill() -> None:
                record["kills"] += 1
                native_kill()

            def wait(*arguments: Any, **keywords: Any) -> int:
                record["waits"] += 1
                record["wait_started"].set()
                return native_wait(*arguments, **keywords)

            process.stdout = ObservedPipe()  # type: ignore[assignment]
            process.kill = kill  # type: ignore[method-assign]
            process.wait = wait  # type: ignore[method-assign]
            observed.append(record)
            return process

        monkeypatch.setattr(bounded_git.subprocess, "Popen", launch)
        return observed

    return install


def _assert_reaped(record: dict[str, Any]) -> None:
    assert record["process"].poll() is not None
    assert record["waits"] >= 1
    assert record["process"].stdout.closed


def _assert_read_budget(record: dict[str, Any], limit: int) -> None:
    consumed = 0
    for requested, received in zip(record["reads"], record["chunks"], strict=True):
        assert 0 < requested <= limit + 1 - consumed
        consumed += received
    assert consumed <= limit + 1


@pytest.mark.parametrize("size", [0, 19, LIMIT])
def test_real_git_accepts_empty_small_and_exact_limit_bodies(
    bounded_git: Any, observe_processes: Any, tmp_path: Path, size: int
) -> None:
    contents = b"x" * size
    oid = _blob(tmp_path, contents)
    observed = observe_processes()

    assert bounded_git._snapshot_git(tmp_path, "cat-file", "blob", oid, output_limit=LIMIT) == (
        contents
    )
    assert len(observed) == 1
    _assert_read_budget(observed[0], LIMIT)
    _assert_reaped(observed[0])


def test_real_git_oversize_stops_after_one_probe_byte_and_reaps_child(
    bounded_git: Any, observe_processes: Any, tmp_path: Path
) -> None:
    oid = _blob(tmp_path, b"x" * (2 * LIMIT))
    observed = observe_processes()

    with pytest.raises(bounded_git.LedgerDataError) as error:
        bounded_git._snapshot_git(tmp_path, "cat-file", "blob", oid, output_limit=LIMIT)

    assert str(error.value) == LIMIT_ERROR
    assert sum(observed[0]["chunks"]) == LIMIT + 1
    assert observed[0]["kills"] >= 1
    _assert_read_budget(observed[0], LIMIT)
    _assert_reaped(observed[0])


def test_short_pipe_reads_do_not_truncate_body_or_reset_remaining_budget(
    bounded_git: Any, observe_processes: Any, tmp_path: Path
) -> None:
    contents = b"a short body with a precise limit"
    oid = _blob(tmp_path, contents)
    observed = observe_processes(short_read=3)

    assert (
        bounded_git._snapshot_git(tmp_path, "cat-file", "blob", oid, output_limit=len(contents))
        == contents
    )
    assert len(observed[0]["reads"]) > 2
    assert observed[0]["reads"][-1] == 1
    _assert_read_budget(observed[0], len(contents))
    _assert_reaped(observed[0])


@pytest.mark.parametrize("read_error", [False, True])
def test_failed_child_or_pipe_read_returns_safe_error_and_reaps_child(
    bounded_git: Any, observe_processes: Any, tmp_path: Path, read_error: bool
) -> None:
    oid = _blob(tmp_path, b"small body")
    observed = observe_processes(read_error=read_error)

    with pytest.raises(bounded_git.LedgerDataError) as error:
        bounded_git._snapshot_git(
            tmp_path, "cat-file", "blob", oid if read_error else PRIVATE, output_limit=LIMIT
        )

    assert str(error.value) == ERROR
    _assert_reaped(observed[0])


def test_spawn_failure_does_not_expose_exception_details(
    bounded_git: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(*_arguments: Any, **_options: Any) -> None:
        raise OSError(PRIVATE)

    monkeypatch.setattr(bounded_git.subprocess, "Popen", fail)
    with pytest.raises(bounded_git.LedgerDataError) as error:
        bounded_git._snapshot_git(tmp_path, "cat-file", "blob", "0" * 40, output_limit=LIMIT)
    assert str(error.value) == ERROR


def test_watchdog_start_failure_is_safe_and_reaps_child_without_joining_unstarted_thread(
    bounded_git: Any,
    observe_processes: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class UnstartableTimer(threading.Timer):
        def start(self) -> None:
            raise RuntimeError(PRIVATE)

        def join(self, timeout: float | None = None) -> None:
            raise AssertionError("an unstarted watchdog must not be joined")

    monkeypatch.setattr(bounded_git, "Timer", UnstartableTimer)
    observed = observe_processes(child_script="import time; time.sleep(60)")

    try:
        with pytest.raises(bounded_git.LedgerDataError) as error:
            bounded_git._snapshot_git(tmp_path, "cat-file", "blob", "0" * 40, output_limit=LIMIT)
        assert str(error.value) == ERROR
    finally:
        assert len(observed) == 1
        assert observed[0]["kills"] >= 1
        _assert_reaped(observed[0])


@pytest.mark.parametrize("pipe_eof", [False, True])
def test_deadline_kills_and_reaps_child_during_read_or_after_stdout_eof(
    bounded_git: Any,
    observe_processes: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    pipe_eof: bool,
) -> None:
    native_timer = threading.Timer
    timers: list[Any] = []

    class ShortTimer(native_timer):
        def __init__(self, interval: float, function: Any) -> None:
            assert interval == 30
            self.cancel_called = False
            self.waits_at_deadline = 0

            def expire() -> None:
                if pipe_eof:
                    observed[0]["wait_started"].wait(2)
                self.waits_at_deadline = observed[0]["waits"]
                function()

            super().__init__(0.1, expire)
            timers.append(self)

        def cancel(self) -> None:
            self.cancel_called = True
            super().cancel()

    monkeypatch.setattr(bounded_git, "Timer", ShortTimer)
    # A simulated EOF avoids platform-specific inherited stdout-handle behavior;
    # the process and its blocking wait remain real in both cases.
    observed = observe_processes(child_script="import time; time.sleep(60)", pipe_eof=pipe_eof)
    started = time.monotonic()

    with pytest.raises(bounded_git.LedgerDataError) as error:
        bounded_git._snapshot_git(tmp_path, "cat-file", "blob", "0" * 40, output_limit=LIMIT)

    assert str(error.value) == ERROR
    assert time.monotonic() - started < 5
    assert len(timers) == 1 and timers[0].cancel_called
    if pipe_eof:
        assert timers[0].waits_at_deadline >= 1
    assert observed[0]["kills"] >= 1
    _assert_read_budget(observed[0], LIMIT)
    _assert_reaped(observed[0])


def test_bounded_reader_keeps_git_isolation_and_discards_child_stdin_and_stderr(
    bounded_git: Any,
    observe_processes: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    oid = _blob(tmp_path, b"local body")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG_COUNT", "GIT_CONFIG_GLOBAL"):
        monkeypatch.setenv(key, PRIVATE)
    observed = observe_processes()

    assert bounded_git._snapshot_git(tmp_path, "cat-file", "blob", oid, output_limit=LIMIT)
    options = observed[0]["options"]
    assert options["stdin"] == options["stderr"] == subprocess.DEVNULL
    assert options["stdout"] == subprocess.PIPE
    assert options["bufsize"] == 0
    assert "--no-replace-objects" in observed[0]["command"]
    environment = options["env"]
    assert not any(key in environment for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG_COUNT"))
    assert environment["GIT_CONFIG_GLOBAL"] == environment["GIT_CONFIG_SYSTEM"] == os.devnull
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert environment["GIT_ALLOW_PROTOCOL"] == ""
    assert environment["GIT_OPTIONAL_LOCKS"] == environment["GIT_TERMINAL_PROMPT"] == "0"
    _assert_reaped(observed[0])


@pytest.mark.parametrize("data", [b"", b"input"])
def test_bounded_reader_rejects_stdin_before_spawning(
    bounded_git: Any, observe_processes: Any, tmp_path: Path, data: bytes
) -> None:
    observed = observe_processes()
    with pytest.raises(bounded_git.LedgerDataError) as error:
        bounded_git._snapshot_git(tmp_path, "cat-file", "--batch", data=data, output_limit=LIMIT)
    assert str(error.value) == ARGUMENT_ERROR
    assert not observed
