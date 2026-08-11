"""Regression tests for the root aiflow command."""

from __future__ import annotations

import subprocess
from collections.abc import Callable


def test_module_help_succeeds(
    run_aiflow: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    result = run_aiflow("--help")

    assert result.returncode == 0
    assert "Auditable AI code collaboration CLI" in result.stdout
    assert result.stderr == ""


def test_module_version_is_stable(
    run_aiflow: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    result = run_aiflow("--version")

    assert result.returncode == 0
    assert result.stdout == "aiflow 0.1.0.dev0\n"
    assert result.stderr == ""


def test_unknown_argument_uses_argparse_error_contract(
    run_aiflow: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    result = run_aiflow("--definitely-unknown")

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert "error:" in result.stderr
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr
