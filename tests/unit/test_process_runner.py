"""Controlled process runner tests using short local Python commands only."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import SimpleNamespace

import pytest

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
    assert set(received["env"]) <= {"PATH", "SystemRoot"}
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
    assert set(environment) <= {"PATH", "SystemRoot", "COVERAGE_FILE"}
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
