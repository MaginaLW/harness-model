"""Controlled process runner tests using short local Python commands only."""

from __future__ import annotations

import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

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
