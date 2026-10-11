"""Regression tests for the root aiflow command."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from importlib.metadata import metadata, version

import pytest

import aiflow


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
    assert result.stdout == "aiflow 0.2.0\n"
    assert result.stderr == ""


def test_package_metadata_matches_runtime_version() -> None:
    assert version("aiflow") == aiflow.__version__ == "0.2.0"
    package_metadata = metadata("aiflow")
    assert package_metadata["License-Expression"] == "MIT"
    assert package_metadata.get_all("License-File") == ["LICENSE"]


def test_unknown_argument_uses_argparse_error_contract(
    run_aiflow: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    result = run_aiflow("--definitely-unknown")

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert "error:" in result.stderr
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [("external-review",), ("verify", "TASK-0001", "--pytest-temp-root", "unused")],
)
def test_retired_interfaces_use_argparse_rejection(
    run_aiflow: Callable[..., subprocess.CompletedProcess[str]], arguments: tuple[str, ...]
) -> None:
    result = run_aiflow(*arguments)

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert "error:" in result.stderr
    assert "Traceback" not in result.stdout + result.stderr


def test_help_exposes_only_supported_interfaces(
    run_aiflow: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    root = run_aiflow("--help")
    verify = run_aiflow("verify", "--help")

    assert root.returncode == verify.returncode == 0
    assert "external-review" not in root.stdout
    assert "--pytest-temp-root" not in verify.stdout
    assert "observe" in root.stdout
    assert "--finalize" in verify.stdout
