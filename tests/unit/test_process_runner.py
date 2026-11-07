"""Controlled process runner tests using short local Python commands only."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import SimpleNamespace
from typing import BinaryIO

import pytest
from test_node_process import FakeKernel
from test_node_process import execute as execute_node

from aiflow import process_runner
from aiflow.errors import ContractError
from aiflow.process_runner import run_execution
from aiflow.verification import VerificationCheck, VerificationExecution


def check(
    argv: tuple[str, ...], *, timeout: int = 2, environment: dict[str, str] | None = None
) -> VerificationCheck:
    return VerificationCheck(
        "check", "V0", argv, environment or {}, Path.cwd(), timeout, True, "exit_zero"
    )


def execution(item: VerificationCheck) -> VerificationExecution:
    return VerificationExecution(
        "EXEC-001", item.argv, item.environment, item.cwd, item.timeout_seconds, ("check",)
    )


def test_runner_captures_success_failure_and_redacts_logs(tmp_path: Path) -> None:
    item = check((sys.executable, "-c", "import sys; print('TOKEN=secret-value'); sys.exit(0)"))
    results = run_execution(
        execution(item),
        {"check": item},
        run_dir=tmp_path / "logs" / "run",
        allowed_run_root=tmp_path / "logs",
        repository_root=Path.cwd(),
        sequence=1,
        sensitive_values=["secret-value"],
    )
    assert results[0].conclusion == "passed"
    assert not results[0].stdout_log_ref.startswith("/")
    assert "secret-value" not in (tmp_path / "logs" / "run" / results[0].stdout_log_ref).read_text()


def test_runner_returns_structured_failure_for_nonzero_timeout_and_missing_program(
    tmp_path: Path,
) -> None:
    failing = check((sys.executable, "-c", "import sys; sys.exit(3)"))
    assert (
        run_execution(
            execution(failing),
            {"check": failing},
            run_dir=tmp_path / "logs" / "one",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
        )[0].conclusion
        == "failed"
    )
    slow = check((sys.executable, "-c", "import time; time.sleep(2)"), timeout=1)
    assert (
        run_execution(
            execution(slow),
            {"check": slow},
            run_dir=tmp_path / "logs" / "two",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=2,
        )[0].timed_out
        is True
    )
    missing = check(("not-a-real-program",), timeout=1)
    assert (
        run_execution(
            execution(missing),
            {"check": missing},
            run_dir=tmp_path / "logs" / "three",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=3,
        )[0].conclusion
        == "failed"
    )


def test_runner_rejects_run_dir_escape_and_coverage_escape(tmp_path: Path) -> None:
    item = check((sys.executable, "-c", "print('ok')"))
    with pytest.raises(ContractError):
        run_execution(
            execution(item),
            {"check": item},
            run_dir=tmp_path / "outside",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
        )


def test_runner_rejects_cwd_outside_explicit_root(tmp_path: Path) -> None:
    item = check((sys.executable, "-c", "print('ok')"))
    with pytest.raises(ContractError):
        run_execution(
            execution(item),
            {"check": item},
            run_dir=tmp_path / "logs" / "run",
            allowed_run_root=tmp_path / "logs",
            repository_root=tmp_path,
            sequence=1,
        )
    coverage = check(
        (sys.executable, "-c", "print('ok')"),
        environment={"COVERAGE_FILE": str(tmp_path / "outside.coverage")},
    )
    with pytest.raises(ContractError):
        run_execution(
            execution(coverage),
            {"check": coverage},
            run_dir=tmp_path / "logs" / "run",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
        )


def test_runner_rejects_replaced_execution_data(tmp_path: Path) -> None:
    item = check(
        (sys.executable, "-c", "print('ok')"),
        environment={"COVERAGE_FILE": str(tmp_path / "logs" / "coverage")},
    )
    replaced = replace(execution(item), environment={})
    with pytest.raises(ContractError) as error:
        run_execution(
            replaced,
            {"check": item},
            run_dir=tmp_path / "logs" / "run",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
        )
    assert error.value.code == "RUNNER_EXECUTION_INVALID"

    replaced_timeout = replace(execution(item), timeout_seconds=item.timeout_seconds + 1)
    with pytest.raises(ContractError) as error:
        run_execution(
            replaced_timeout,
            {"check": item},
            run_dir=tmp_path / "logs" / "run-timeout",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=2,
        )
    assert error.value.code == "RUNNER_EXECUTION_INVALID"

    duplicate = replace(execution(item), check_ids=("check", "check"))
    with pytest.raises(ContractError) as error:
        run_execution(
            duplicate,
            {"check": item},
            run_dir=tmp_path / "logs" / "run-duplicate",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=3,
        )
    assert error.value.code == "RUNNER_EXECUTION_INVALID"

    unknown = replace(execution(item), check_ids=("unknown",))
    with pytest.raises(ContractError) as error:
        run_execution(
            unknown,
            {"check": item},
            run_dir=tmp_path / "logs" / "run-two",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=4,
        )
    assert error.value.code == "RUNNER_EXECUTION_INVALID"


def test_timeout_kills_child_process_tree(tmp_path: Path) -> None:
    sentinel = tmp_path / "child-survived.txt"
    child = (
        f"import pathlib, time; time.sleep(2); pathlib.Path({str(sentinel)!r}).write_text('alive')"
    )
    parent = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(10)"
    )
    item = check((sys.executable, "-c", parent), timeout=1)

    result = run_execution(
        execution(item),
        {"check": item},
        run_dir=tmp_path / "logs" / "run",
        allowed_run_root=tmp_path / "logs",
        repository_root=Path.cwd(),
        sequence=1,
    )[0]

    assert result.timed_out is True
    time.sleep(3)
    assert not sentinel.exists()


def test_runner_preserves_actual_argv_and_minimal_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = check((sys.executable, "-c", "print('ordinary-check')"))
    selected = execution(item)
    received: dict[str, object] = {}

    class SuccessfulProcess:
        returncode = 0

        def communicate(self, *, timeout: int) -> tuple[str, str]:
            assert timeout == item.timeout_seconds
            return "1 passed in 0.01s\n", ""

    def launch(argv: list[str], **kwargs: object) -> SuccessfulProcess:
        received.update(kwargs)
        received["argv"] = argv
        return SuccessfulProcess()

    monkeypatch.setattr(process_runner.subprocess, "Popen", launch)
    result = run_execution(
        selected,
        {item.check_id: item},
        run_dir=tmp_path / "logs" / "run",
        allowed_run_root=tmp_path / "logs",
        repository_root=Path.cwd(),
        sequence=1,
    )[0]
    assert received["argv"] == list(selected.argv)
    assert received["shell"] is False
    assert set(received["env"]) <= {"PATH", "SystemRoot", "TEMP", "TMP", "TMPDIR"}
    assert result.conclusion == "passed"
    assert "ordinary-check" in result.command_summary


def test_execution_keeps_default_command_summary(tmp_path: Path) -> None:
    item = check((sys.executable, "-c", "print('ordinary-check')"))
    result = run_execution(
        execution(item),
        {item.check_id: item},
        run_dir=tmp_path / "logs" / "run",
        allowed_run_root=tmp_path / "logs",
        repository_root=Path.cwd(),
        sequence=1,
    )[0]
    assert result.returncode == 0
    assert result.conclusion == "passed"
    assert "ordinary-check" in result.command_summary


def test_runner_hides_known_paths_in_summary_without_changing_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    run_dir = tmp_path / "logs" / "run"
    item = replace(
        check(
            (
                sys.executable,
                "-c",
                "print('ordinary-check')",
                f"--root={repository / 'config.toml'}",
                f"--cov-report=xml:{run_dir / 'coverage.xml'}",
                "--run-dir",
                str(run_dir),
                "--token=top-secret",
            ),
            environment={"COVERAGE_FILE": str(run_dir / ".coverage")},
        ),
        cwd=repository,
    )
    selected = execution(item)
    received: dict[str, object] = {}

    class SuccessfulProcess:
        returncode = 0

        def communicate(self, *, timeout: int) -> tuple[str, str]:
            assert timeout == item.timeout_seconds
            return "ordinary-check\n", ""

    def launch(argv: list[str], **kwargs: object) -> SuccessfulProcess:
        received.update(kwargs)
        received["argv"] = argv
        return SuccessfulProcess()

    monkeypatch.setattr(process_runner.subprocess, "Popen", launch)
    result = run_execution(
        selected,
        {item.check_id: item},
        run_dir=run_dir,
        allowed_run_root=tmp_path / "logs",
        repository_root=repository,
        sequence=1,
        sensitive_values=["top-secret"],
    )[0]

    assert received["argv"] == list(selected.argv)
    assert received["shell"] is False
    environment = received["env"]
    assert isinstance(environment, dict)
    assert set(environment) <= {"PATH", "SystemRoot", "COVERAGE_FILE", "TEMP", "TMP", "TMPDIR"}
    assert "PATH" in environment
    assert {entry for entry in os.defpath.split(os.pathsep) if entry} <= set(
        environment["PATH"].split(os.pathsep)
    )
    if os.name == "nt" and os.environ.get("SystemRoot"):
        assert environment["SystemRoot"] == os.environ["SystemRoot"]
    else:
        assert "SystemRoot" not in environment
    assert environment["COVERAGE_FILE"] == str(run_dir / ".coverage")
    assert result.conclusion == "passed"
    assert sys.executable not in result.command_summary
    assert f"--root={repository / 'config.toml'}" not in result.command_summary
    assert str(run_dir) not in result.command_summary
    assert "${PYTHON}" in result.command_summary
    assert "--root=${REPO_ROOT}" in result.command_summary
    assert "--cov-report=xml:${RUN_DIR}" in result.command_summary
    assert "--run-dir ${RUN_DIR}" in result.command_summary
    assert "config.toml" in result.command_summary and "coverage.xml" in result.command_summary
    assert "-c" in result.command_summary and "ordinary-check" in result.command_summary
    assert "top-secret" not in result.command_summary


@pytest.mark.parametrize("selected", ["TMPDIR", "TEMP", "TMP", "default"])
def test_runner_gives_each_child_a_private_temp_in_selected_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: str
) -> None:
    roots = {key: tmp_path / key.lower() for key in ("TMPDIR", "TEMP", "TMP", "default")}
    for root in roots.values():
        root.mkdir()
    order = ["TMPDIR", "TEMP", "TMP"]
    for index, key in enumerate(order):
        if selected == "default" or index < order.index(selected):
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, str(roots[key]))
    if selected == "default":
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(roots["default"]))
    blocked = ("PYTHONPATH", "PYTHONOPTIMIZE", "PYTEST_ADDOPTS", "NODE_OPTIONS", "API_TOKEN")
    for key in blocked:
        monkeypatch.setenv(key, "must-not-be-inherited")
    before = dict(os.environ)
    # Check the fixed roles before calling tempfile: on the unfixed runner this
    # fails without tempfile probing or writing any operating-system temp path.
    script = """
import json, os, sys
from pathlib import Path
root = Path(sys.argv[1])
roles = [os.environ.get(key) for key in ('TEMP', 'TMP', 'TMPDIR')]
assert all(roles) and len(set(roles)) == 1, 'missing private temp roles'
private = Path(roles[0])
assert private.parent == root and private.name.startswith('aiflow-check-')
assert not any(key in os.environ for key in
    ('PYTHONPATH', 'PYTHONOPTIMIZE', 'PYTEST_ADDOPTS', 'NODE_OPTIONS', 'API_TOKEN'))
import tempfile
assert Path(tempfile.gettempdir()) == private
descriptor, filename = tempfile.mkstemp()
os.close(descriptor)
assert Path(filename).parent == private
print(json.dumps({'private': str(private), 'file': filename}))
"""
    item = check((sys.executable, "-B", "-c", script, str(roots[selected])), timeout=10)
    observed = []
    for sequence in (1, 2):
        run_dir = tmp_path / "logs" / f"run-{sequence}"
        result = run_execution(
            execution(item),
            {item.check_id: item},
            run_dir=run_dir,
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=sequence,
        )[0]
        stderr = (run_dir / result.stderr_log_ref).read_text(encoding="utf8")
        assert result.conclusion == "passed", stderr
        report = json.loads((run_dir / result.stdout_log_ref).read_text(encoding="utf8"))
        private, created = Path(report["private"]), Path(report["file"])
        assert private.parent == roots[selected]
        assert not private.is_relative_to(run_dir)
        assert private.is_dir() and created.is_file()
        observed.append(private)
    assert observed[0] != observed[1]
    assert dict(os.environ) == before


def test_runner_rejects_private_temp_creation_failure_without_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "selected-temp"
    root.mkdir()
    marker = root / "existing.txt"
    marker.write_bytes(b"preserved owned material")
    identity = root.stat()
    monkeypatch.setenv("TMPDIR", str(root))
    before = dict(os.environ)
    failure = OSError("synthetic temporary storage unavailable")
    attempts = []

    def unavailable(*, prefix: str, dir: Path) -> str:
        assert prefix == "aiflow-check-"
        attempts.append(Path(dir))
        raise failure

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("temporary creation failure reached process launch")

    monkeypatch.setattr(process_runner.tempfile, "mkdtemp", unavailable)
    monkeypatch.setattr(process_runner.subprocess, "Popen", forbidden)
    item = check((sys.executable, "-c", "print('must not execute')"))
    with pytest.raises(ContractError) as caught:
        run_execution(
            execution(item),
            {item.check_id: item},
            run_dir=tmp_path / "logs" / "run",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
        )
    assert caught.value.code == "RUNNER_TEMP_ROOT_INVALID"
    assert caught.value.__cause__ is failure
    assert attempts == [root]
    assert dict(os.environ) == before
    assert root.is_dir() and list(root.iterdir()) == [marker]
    assert (root.stat().st_dev, root.stat().st_ino) == (identity.st_dev, identity.st_ino)
    assert marker.read_bytes() == b"preserved owned material"


@pytest.mark.parametrize("key", ["TEMP", "TMP", "TMPDIR", "PYTHONPATH"])
def test_runner_never_accepts_temp_or_injection_from_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("untrusted Policy environment reached a process")

    monkeypatch.setattr(process_runner.subprocess, "Popen", forbidden)
    item = check((sys.executable, "-c", "pass"), environment={key: str(tmp_path)})
    with pytest.raises(ContractError, match="environment"):
        run_execution(
            execution(item),
            {item.check_id: item},
            run_dir=tmp_path / "logs" / "run",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
        )


@pytest.mark.parametrize("kind", ["relative", "missing", "file", "link", "linked-parent"])
@pytest.mark.parametrize("selected", ["TMPDIR", "TEMP", "TMP"])
def test_runner_rejects_invalid_explicit_temp_before_any_probe_mkdir_or_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, selected: str
) -> None:
    if kind == "relative":
        root = Path("relative-temp-root")
    elif kind == "missing":
        root = tmp_path / "missing"
    elif kind == "file":
        root = tmp_path / "file"
        root.write_text("not a directory", encoding="utf8")
    else:
        actual = tmp_path / "actual"
        actual.mkdir()
        (actual / "child").mkdir()
        linked = tmp_path / "linked"
        try:
            linked.symlink_to(actual, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory symlinks unavailable: {error}")
        root = linked / "child" if kind == "linked-parent" else linked
    # Lower-priority valid roots must not turn an explicit invalid root into a
    # successful fallback or permit logs to be created before validation.
    order = ["TMPDIR", "TEMP", "TMP"]
    for index, key in enumerate(order):
        if index < order.index(selected):
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, str(root if key == selected else tmp_path))
    calls = []

    def forbidden(*args: object, **kwargs: object) -> None:
        calls.append(args)
        pytest.fail("invalid explicit temp reached a probe, mkdir or process")

    monkeypatch.setattr(process_runner.subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "mkdir", forbidden)
    monkeypatch.setattr(tempfile, "gettempdir", forbidden)
    monkeypatch.setattr(tempfile, "mkdtemp", forbidden)
    item = check((sys.executable, "-c", "pass"))
    with pytest.raises(ContractError):
        run_execution(
            execution(item),
            {item.check_id: item},
            run_dir=tmp_path / "logs" / "run",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
        )
    assert calls == []


@pytest.mark.parametrize(
    ("platform", "repo", "run", "argument", "expected"),
    [
        (
            "nt",
            r"C:\Work\Repo",
            r"C:\Work\Repo\logs\run",
            "--root=(c:/WORK/REPO)",
            "--root=(${REPO_ROOT})",
        ),
        (
            "nt",
            r"C:\Work\Repo",
            r"C:\Work\Repo\logs\run",
            r"--root=C:\Work\Repo-other\config",
            r"--root=C:\Work\Repo-other\config",
        ),
        (
            "nt",
            r"C:\Work\Repo",
            r"C:\Work\Repo\logs\run",
            r"--cov-report=xml:c:/WORK\REPO/logs\run/coverage.xml",
            "--cov-report=xml:${RUN_DIR}/coverage.xml",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "--root=[/srv/Work/repo]",
            "--root=[${REPO_ROOT}]",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "--root=/srv/work/repo",
            "--root=/srv/work/repo",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "--cov-report=xml:/srv/Work/repo/logs/run/coverage.xml",
            "--cov-report=xml:${RUN_DIR}/coverage.xml",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "--root='/srv/Work/repo',",
            "--root='${REPO_ROOT}',",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            '--root="/srv/Work/repo",',
            '--root="${REPO_ROOT}",',
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "/srv/Work/repo,next",
            "${REPO_ROOT},next",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "/srv/Work/repo;next",
            "${REPO_ROOT};next",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "/srv/Work/repo:next",
            "${REPO_ROOT}:next",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "x/srv/Work/repo",
            "x/srv/Work/repo",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "1/srv/Work/repo",
            "1/srv/Work/repo",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "--root=/srv/Work/repo+other/config",
            "--root=/srv/Work/repo+other/config",
        ),
        (
            "posix",
            "/srv/Work/repo",
            "/srv/Work/repo/logs/run",
            "--root=/srv/Work/repo~other/config",
            "--root=/srv/Work/repo~other/config",
        ),
    ],
)
def test_summary_path_boundaries_and_longest_match(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    repo: str,
    run: str,
    argument: str,
    expected: str,
) -> None:
    monkeypatch.setattr(process_runner, "os", SimpleNamespace(name=platform))
    pure_path = PureWindowsPath if platform == "nt" else PurePosixPath
    assert (
        process_runner._summary_paths(
            argument, repository_root=pure_path(repo), run_dir=pure_path(run)
        )
        == expected
    )


@pytest.fixture
def streaming_kernel(monkeypatch: pytest.MonkeyPatch) -> FakeKernel:
    """Use the existing synthetic Win32 API with the actual runner state machine."""
    fake = FakeKernel()
    monkeypatch.setattr(process_runner, "_node_kernel", lambda: (fake, lambda: fake.error))
    monkeypatch.setattr(process_runner, "monotonic", lambda: fake.clock)
    monkeypatch.setattr(process_runner, "sleep", fake.sleep)
    return fake


class StreamingSink:
    """A caller-owned real file, recording bounded writes without storing their payload."""

    def __init__(
        self, raw: BinaryIO, kernel: FakeKernel, *, fault: str | None = None, fault_call: int = 2
    ) -> None:
        self.raw = raw
        self.kernel = kernel
        self.fault = fault
        self.fault_call = fault_call
        self.chunks: list[int] = []
        self.remaining_at_write: list[int] = []
        self.closed_by_runner = False

    def write(self, data: bytes) -> int | None:
        assert type(data) is bytes and 0 < len(data) <= 16 * 1024
        self.chunks.append(len(data))
        self.remaining_at_write.append(len(self.kernel.output[0]))
        if self.fault is not None and len(self.chunks) >= self.fault_call:
            assert len(self.chunks) == self.fault_call, "teardown wrote to a failed sink again"
            if self.fault in {"short", "none", "exception"}:
                count = self.raw.write(data[:7])
                if self.fault == "exception":
                    raise OSError("synthetic private sink error; must not enter the receipt")
                return count if self.fault == "short" else None
            if self.fault in {"true", "false"}:
                self.raw.write(data)
                return self.fault == "true"
            if self.fault == "negative":
                return -1
            if self.fault == "large":
                return len(data) + 1
            raise AssertionError("unknown test sink fault")
        return self.raw.write(data)

    def close(self) -> None:
        self.closed_by_runner = True
        self.raw.close()


def assert_stream_receipt(result: process_runner.NodeProcessResult) -> None:
    """Streaming never adds fields to the existing closed process receipt."""
    assert result.receipt is not None
    assert set(result.receipt) == {
        "process_id",
        "creation_time_filetime",
        "created_suspended",
        "assigned",
        "initial_membership",
        "resumed",
        "job_empty",
        "stdout_eof",
        "stderr_eof",
        "terminate_requested",
        "closed",
    }
    assert result.receipt["process_id"] == 300
    assert result.receipt["creation_time_filetime"] == 132537600000000001
    assert result.receipt["created_suspended"] is True
    assert result.receipt["assigned"] is True
    assert result.receipt["initial_membership"] is True
    assert result.receipt["resumed"] is True


@pytest.mark.parametrize("size", [1, 16384, 16385, 1024 * 1024 + 32771])
def test_streaming_node_exact_limit_uses_bounded_incremental_caller_owned_writes(
    streaming_kernel: FakeKernel, tmp_path: Path, size: int
) -> None:
    fake = streaming_kernel
    fake.output = [bytearray(b"s" * size), bytearray(b"stderr")]
    destination = tmp_path / "stdout.bin"
    with destination.open("wb", buffering=0) as raw:
        sink = StreamingSink(raw, fake)
        result = execute_node(tmp_path, stdout_sink=sink, stdout_limit=size, timeout_seconds=1200)
        assert not raw.closed and not sink.closed_by_runner
        assert sum(sink.chunks) == size and max(sink.chunks) <= 16384
        if size > 16384:
            assert sink.remaining_at_write[0] > 0, (
                "stdout was buffered until the entire pipe drained"
            )
            assert len(sink.chunks) > 1
        assert destination.read_bytes() == b"s" * size
    assert result.stdout == b"" and result.stderr == b"stderr"
    assert result.returncode == 0 and not result.timed_out and not result.execution_error
    assert not result.stdout_overflow and not result.stderr_overflow
    assert result.cleanup == "confirmed"
    assert_stream_receipt(result)
    assert result.receipt["stdout_eof"] is True and result.receipt["stderr_eof"] is True
    assert result.receipt["job_empty"] is True and result.receipt["closed"] is True
    assert result.receipt["terminate_requested"] is False
    assert not fake.terminated and not fake.handles


def test_streaming_node_over_limit_stops_before_writing_an_overflowing_chunk(
    streaming_kernel: FakeKernel, tmp_path: Path
) -> None:
    fake = streaming_kernel
    limit = 32768
    fake.output = [bytearray(b"s" * (limit + 16384)), bytearray(b"stderr")]
    destination = tmp_path / "overflow.bin"
    with destination.open("wb", buffering=0) as raw:
        sink = StreamingSink(raw, fake)
        result = execute_node(tmp_path, stdout_sink=sink, stdout_limit=limit, timeout_seconds=1200)
        assert not raw.closed and not sink.closed_by_runner
        assert sink.chunks == [16384, 16384]
        assert destination.read_bytes() == b"s" * limit
    assert result.stdout == b"" and result.stdout_overflow
    assert not result.stderr_overflow and not result.timed_out
    assert result.cleanup == "confirmed" and fake.terminated and not fake.handles
    assert_stream_receipt(result)
    assert result.receipt["terminate_requested"] is True
    assert result.receipt["stdout_eof"] is True and result.receipt["stderr_eof"] is True
    assert result.receipt["closed"] is True


@pytest.mark.parametrize("fault", ["short", "none", "exception", "negative", "large"])
def test_streaming_node_sink_failure_preserves_partial_then_discards_during_real_teardown(
    streaming_kernel: FakeKernel, tmp_path: Path, fault: str
) -> None:
    fake = streaming_kernel
    fake.output = [bytearray(b"s" * 65536), bytearray(b"stderr")]
    destination = tmp_path / "partial.bin"
    with destination.open("wb", buffering=0) as raw:
        sink = StreamingSink(raw, fake, fault=fault)
        result = execute_node(tmp_path, stdout_sink=sink, stdout_limit=65536, timeout_seconds=1200)
        assert not raw.closed and not sink.closed_by_runner
        assert sink.chunks == [16384, 16384]
        expected = 16384 + (7 if fault in {"short", "none", "exception"} else 0)
        assert destination.read_bytes() == b"s" * expected
    assert result.stdout == b"" and result.execution_error and not result.stdout_overflow
    assert result.cleanup == "confirmed" and fake.terminated and not fake.handles
    assert_stream_receipt(result)
    assert result.receipt["job_empty"] is True
    assert result.receipt["stdout_eof"] is True and result.receipt["stderr_eof"] is True
    assert result.receipt["closed"] is True and result.receipt["terminate_requested"] is True
    assert "private" not in str(result.receipt)


@pytest.mark.parametrize("fault", ["true", "false"])
def test_streaming_node_boolean_write_count_is_not_an_integer_count(
    streaming_kernel: FakeKernel, tmp_path: Path, fault: str
) -> None:
    fake = streaming_kernel
    fake.output = [bytearray(b"s"), bytearray()]
    destination = tmp_path / "boolean.bin"
    with destination.open("wb", buffering=0) as raw:
        sink = StreamingSink(raw, fake, fault=fault, fault_call=1)
        result = execute_node(tmp_path, stdout_sink=sink, stdout_limit=1)
        assert sink.chunks == [1]
        assert not raw.closed and not sink.closed_by_runner
        assert destination.read_bytes() == b"s"
    assert result.stdout == b"" and result.execution_error
    assert result.cleanup == "confirmed" and fake.terminated and not fake.handles
    assert_stream_receipt(result)
    assert result.receipt["terminate_requested"] is True


def test_streaming_node_sink_error_cannot_replace_unobserved_eof_with_confirmed_cleanup(
    streaming_kernel: FakeKernel, tmp_path: Path
) -> None:
    fake = streaming_kernel
    fake.output = [bytearray(b"s" * 65536), bytearray(b"stderr")]
    fake.pipe_held = True
    destination = tmp_path / "held-partial.bin"
    with destination.open("wb", buffering=0) as raw:
        sink = StreamingSink(raw, fake, fault="exception")
        result = execute_node(tmp_path, stdout_sink=sink, stdout_limit=65536, timeout_seconds=1200)
        assert not raw.closed and not sink.closed_by_runner
        assert sink.chunks == [16384, 16384]
        assert destination.read_bytes() == b"s" * (16384 + 7)
    assert result.stdout == b"" and result.execution_error and not result.timed_out
    assert result.cleanup == "unknown" and fake.terminated and not fake.handles
    assert_stream_receipt(result)
    assert result.receipt["job_empty"] is True and result.receipt["terminate_requested"] is True
    assert result.receipt["stdout_eof"] is False and result.receipt["stderr_eof"] is False
    assert result.receipt["closed"] is True


@pytest.mark.parametrize("limit", [None, True, False, 1.0, "1", 0, -1])
@pytest.mark.parametrize("with_sink", [False, True])
def test_streaming_node_invalid_limit_rejects_before_any_kernel_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, limit: object, with_sink: bool
) -> None:
    def forbidden():
        pytest.fail("invalid streaming inputs reached the Win32 kernel")

    monkeypatch.setattr(process_runner, "_node_kernel", forbidden)
    with (tmp_path / "unused.bin").open("wb", buffering=0) as raw:
        result = execute_node(tmp_path, stdout_sink=raw if with_sink else None, stdout_limit=limit)
        assert not raw.closed
    assert result == process_runner.NodeProcessResult(
        None, False, b"", b"", False, False, "not_started", True, None
    )


@pytest.mark.parametrize("sink", [object(), False, 0, SimpleNamespace(write=None)])
def test_streaming_node_invalid_sink_rejects_before_any_kernel_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sink: object
) -> None:
    def forbidden():
        pytest.fail("invalid sink reached the Win32 kernel")

    monkeypatch.setattr(process_runner, "_node_kernel", forbidden)
    result = execute_node(tmp_path, stdout_sink=sink)
    assert result == process_runner.NodeProcessResult(
        None, False, b"", b"", False, False, "not_started", True, None
    )


@pytest.mark.parametrize("limit", [1, 1048575, 1048577, 4 * 1048576])
def test_streaming_node_nondefault_limit_cannot_raise_or_change_the_no_sink_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, limit: int
) -> None:
    def forbidden():
        pytest.fail("a caller limit without a sink reached the kernel")

    monkeypatch.setattr(process_runner, "_node_kernel", forbidden)
    result = execute_node(tmp_path, stdout_limit=limit)
    assert result == process_runner.NodeProcessResult(
        None, False, b"", b"", False, False, "not_started", True, None
    )


@pytest.mark.parametrize("extra", [0, 1])
@pytest.mark.parametrize("explicit_default", [False, True])
def test_streaming_node_no_sink_preserves_the_original_in_memory_one_mib_contract(
    streaming_kernel: FakeKernel, tmp_path: Path, extra: int, explicit_default: bool
) -> None:
    fake = streaming_kernel
    fake.output = [bytearray(b"s" * (1048576 + extra)), bytearray(b"stderr")]
    kwargs = {"stdout_limit": 1048576} if explicit_default else {}
    result = execute_node(tmp_path, timeout_seconds=1200, **kwargs)
    assert result.stdout == b"s" * 1048576 and result.stderr == b"stderr"
    assert result.stdout_overflow is bool(extra) and not result.stderr_overflow
    assert result.cleanup == "confirmed" and not result.timed_out and not result.execution_error
    assert fake.terminated is bool(extra) and not fake.handles
    assert_stream_receipt(result)


def test_streaming_node_stderr_retains_its_fixed_one_mib_limit(
    streaming_kernel: FakeKernel, tmp_path: Path
) -> None:
    fake = streaming_kernel
    fake.output = [bytearray(b"s"), bytearray(b"e" * 1048577)]
    destination = tmp_path / "stdout.bin"
    with destination.open("wb", buffering=0) as raw:
        sink = StreamingSink(raw, fake)
        result = execute_node(
            tmp_path, stdout_sink=sink, stdout_limit=4 * 1048576, timeout_seconds=1200
        )
        assert not raw.closed and not sink.closed_by_runner
        assert destination.read_bytes() == b"s"
    assert result.stdout == b"" and result.stderr == b"e" * 1048576
    assert result.stderr_overflow and not result.stdout_overflow
    assert result.cleanup == "confirmed" and fake.terminated and not fake.handles
    assert_stream_receipt(result)


@pytest.mark.parametrize("mode", ["alive", "children", "pipe"])
def test_streaming_node_timeout_still_requires_actual_job_empty_and_both_pipe_eofs(
    streaming_kernel: FakeKernel, tmp_path: Path, mode: str
) -> None:
    fake = streaming_kernel
    fake.alive, fake.children, fake.pipe_held = mode == "alive", mode == "children", mode == "pipe"
    destination = tmp_path / "partial.bin"
    with destination.open("wb", buffering=0) as raw:
        sink = StreamingSink(raw, fake)
        result = execute_node(tmp_path, stdout_sink=sink)
        assert not raw.closed and not sink.closed_by_runner
        assert destination.read_bytes() == b"stdout"
    assert result.stdout == b"" and result.timed_out and fake.terminated and not fake.handles
    assert result.cleanup == ("unknown" if mode == "pipe" else "confirmed")
    assert result.execution_error is (mode == "pipe")
    assert_stream_receipt(result)
    assert result.receipt["job_empty"] is True and result.receipt["terminate_requested"] is True
    assert result.receipt["closed"] is True
    assert result.receipt["stdout_eof"] is (mode != "pipe")
    assert result.receipt["stderr_eof"] is (mode != "pipe")


@pytest.mark.parametrize("persistent", [False, True])
def test_streaming_node_failed_handle_release_never_claims_confirmed_cleanup(
    streaming_kernel: FakeKernel, tmp_path: Path, persistent: bool
) -> None:
    fake = streaming_kernel
    if persistent:
        original = fake.call

        def failed_close(name, arguments):
            if name == "CloseHandle" and fake.handle(arguments[0]) == 10:
                return 0
            return original(name, arguments)

        fake.call = failed_close
    else:
        fake.fail = "CloseHandle", 3
    destination = tmp_path / "stdout.bin"
    with destination.open("wb", buffering=0) as raw:
        sink = StreamingSink(raw, fake)
        result = execute_node(tmp_path, stdout_sink=sink)
        assert not raw.closed and not sink.closed_by_runner
        assert destination.read_bytes() == b"stdout"
    assert result.stdout == b"" and result.execution_error and result.cleanup == "unknown"
    assert_stream_receipt(result)
    assert result.receipt["closed"] is not persistent
    assert fake.handles == ({10} if persistent else set())
