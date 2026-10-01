"""Controlled process runner tests using short local Python commands only."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

from aiflow import process_runner
from aiflow.errors import ContractError
from aiflow.process_runner import run_execution
from aiflow.verification import VerificationCheck, VerificationExecution
from aiflow.verification_temporary import (
    PytestTemporaryLayout,
    create_pytest_temporary,
    plan_pytest_temporary,
)


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


def _guarded_pytest_execution(
    tmp_path: Path,
) -> tuple[VerificationCheck, VerificationExecution, PytestTemporaryLayout]:
    parent = tmp_path / "pytest-parent"
    parent.mkdir()
    (parent / "sibling.txt").write_bytes(b"preserve sibling\r\n")
    temporary = create_pytest_temporary(
        plan_pytest_temporary(parent, "TASK-0001", "run-001", ("EXEC-001", "EXEC-002"))
    )
    argv = (
        sys.executable,
        "-m",
        "pytest",
        "tests/unit",
        "-q",
        f"--basetemp={temporary.leaves['EXEC-001'].as_posix()}",
    )
    item = VerificationCheck("unit_tests", "V1", argv, {}, Path.cwd(), 2, True, "pytest")
    selected = VerificationExecution("EXEC-001", argv, {}, item.cwd, 2, (item.check_id,))
    return item, selected, temporary


@pytest.mark.parametrize(
    "tampering", ["parent", "other_leaf", "duplicate", "split", "non_pytest", "missing"]
)
def test_runner_guard_rejects_jointly_tampered_check_and_execution_before_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tampering: str
) -> None:
    item, selected, temporary = _guarded_pytest_execution(tmp_path)
    if tampering == "parent":
        argv = (*selected.argv[:-1], f"--basetemp={temporary.parent.as_posix()}")
    elif tampering == "other_leaf":
        argv = (*selected.argv[:-1], f"--basetemp={temporary.leaves['EXEC-002'].as_posix()}")
    elif tampering == "duplicate":
        argv = (*selected.argv, selected.argv[-1])
    elif tampering == "split":
        argv = (*selected.argv[:-1], "--basetemp", temporary.leaves["EXEC-001"].as_posix())
    elif tampering == "non_pytest":
        argv = (sys.executable, "-c", "raise AssertionError('must not run')", selected.argv[-1])
    else:
        argv = selected.argv[:-1]
    item = replace(item, argv=argv)
    selected = replace(selected, argv=argv)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    directories = {path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_dir()}

    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unsafe temporary argv must not start a process")

    monkeypatch.setattr(process_runner.subprocess, "Popen", unexpected)
    with pytest.raises(ContractError):
        run_execution(
            selected,
            {item.check_id: item},
            run_dir=tmp_path / "logs" / "run",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
            pytest_temporary=temporary,
        )
    assert before == {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert directories == {
        path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_dir()
    }
    assert not (tmp_path / "logs").exists()


@pytest.mark.parametrize("drift", ["existing_leaf", "container_replaced"])
def test_runner_guard_rechecks_directory_identity_and_leaf_before_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    item, selected, temporary = _guarded_pytest_execution(tmp_path)
    if drift == "existing_leaf":
        leaf = temporary.leaves["EXEC-001"]
        leaf.mkdir()
        (leaf / "keep.txt").write_bytes(b"owned by an earlier process\r\n")
    else:
        temporary.container.rename(temporary.parent / "preserved-container")
        temporary.container.mkdir()
        (temporary.container / "keep.txt").write_bytes(b"replacement stays untouched\r\n")
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("directory drift must not start a process")

    monkeypatch.setattr(process_runner.subprocess, "Popen", unexpected)
    with pytest.raises(ContractError):
        run_execution(
            selected,
            {item.check_id: item},
            run_dir=tmp_path / "logs" / "run",
            allowed_run_root=tmp_path / "logs",
            repository_root=Path.cwd(),
            sequence=1,
            pytest_temporary=temporary,
        )
    assert before == {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert not (tmp_path / "logs").exists()


def test_runner_records_guarded_actual_argv_and_preserves_minimal_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item, selected, temporary = _guarded_pytest_execution(tmp_path)
    received: dict[str, object] = {}

    class SuccessfulProcess:
        returncode = 0

        def communicate(self, *, timeout: int) -> tuple[str, str]:
            assert timeout == item.timeout_seconds
            return "1 passed in 0.01s\n", ""

    def launch(argv: list[str], **kwargs: object) -> SuccessfulProcess:
        received.update(kwargs)
        received["argv"] = argv
        assert not temporary.leaves["EXEC-001"].exists()
        return SuccessfulProcess()

    monkeypatch.setattr(process_runner.subprocess, "Popen", launch)
    result = run_execution(
        selected,
        {item.check_id: item},
        run_dir=tmp_path / "logs" / "run",
        allowed_run_root=tmp_path / "logs",
        repository_root=Path.cwd(),
        sequence=1,
        pytest_temporary=temporary,
    )[0]
    assert received["argv"] == list(selected.argv)
    assert received["shell"] is False
    assert set(received["env"]) <= {"PATH", "SystemRoot"}
    assert result.conclusion == "passed"
    assert selected.argv[-1] in result.command_summary


def test_real_pytest_redacted_token_roots_retain_distinct_actual_argv_digests(
    tmp_path: Path,
) -> None:
    program = tmp_path / "program"
    program.mkdir()
    (program / "test_probe.py").write_text(
        "from pathlib import Path\n"
        "def test_owned_fixture(tmp_path, pytestconfig):\n"
        "    base = Path(pytestconfig.getoption('basetemp')).resolve()\n"
        "    assert tmp_path.resolve().is_relative_to(base)\n",
        encoding="utf-8",
    )
    digests: list[str] = []
    for index in (1, 2):
        parent = tmp_path / f"benign-token-cache-{index}"
        parent.mkdir()
        temporary = create_pytest_temporary(
            plan_pytest_temporary(parent, "TASK-0001", "run-001", ("EXEC-001",))
        )
        leaf = temporary.leaves["EXEC-001"]
        argv = (
            sys.executable,
            "-m",
            "pytest",
            "test_probe.py",
            "-q",
            f"--basetemp={leaf.as_posix()}",
        )
        assert Path(argv[0]).is_absolute()
        item = VerificationCheck("unit_tests", "V1", argv, {}, program, 30, True, "pytest")
        selected = VerificationExecution("EXEC-001", argv, {}, program, 30, (item.check_id,))
        result = run_execution(
            selected,
            {item.check_id: item},
            run_dir=tmp_path / "logs" / f"run-{index}",
            allowed_run_root=tmp_path / "logs",
            repository_root=program,
            sequence=index,
            pytest_temporary=temporary,
        )[0]
        expected = hashlib.sha256(
            json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert result.returncode == 0
        assert result.conclusion == "passed"
        assert result.timed_out is False
        assert leaf.is_dir()
        assert list(leaf.glob("test_owned_fixture*"))
        assert "[REDACTED]" in result.command_summary
        assert str(parent) not in result.command_summary
        assert parent.as_posix() not in result.command_summary
        assert argv[-1] not in result.command_summary
        marker = f"[pytest-argv-sha256:{expected}]"
        assert result.command_summary.endswith(marker)
        assert result.command_summary.count("[pytest-argv-sha256:") == 1
        digests.append(expected)
    assert digests[0] != digests[1]


@pytest.mark.parametrize("with_layout", [False, True])
def test_non_pytest_execution_keeps_default_summary_without_argv_digest(
    tmp_path: Path, with_layout: bool
) -> None:
    temporary = None
    if with_layout:
        parent = tmp_path / "pytest-parent"
        parent.mkdir()
        temporary = create_pytest_temporary(
            plan_pytest_temporary(parent, "TASK-0001", "run-001", ("EXEC-001",))
        )
    item = check((sys.executable, "-c", "print('ordinary-check')"))
    result = run_execution(
        execution(item),
        {item.check_id: item},
        run_dir=tmp_path / "logs" / "run",
        allowed_run_root=tmp_path / "logs",
        repository_root=Path.cwd(),
        sequence=1,
        pytest_temporary=temporary,
    )[0]
    assert result.returncode == 0
    assert result.conclusion == "passed"
    assert "ordinary-check" in result.command_summary
    assert "pytest-argv-sha256" not in result.command_summary
    if temporary is not None:
        assert not temporary.leaves["EXEC-001"].exists()
