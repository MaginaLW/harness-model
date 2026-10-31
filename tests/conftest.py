"""Fixtures shared by aiflow command-line tests."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Keep each test invocation out of another invocation's numbered temp tree."""
    if config.option.basetemp is None:
        try:
            config.option.basetemp = tempfile.mkdtemp(prefix="aiflow-pytest-")
        except OSError as error:
            raise pytest.UsageError("Could not create an isolated test temporary root") from error


@pytest.fixture
def run_aiflow() -> Callable[[str], subprocess.CompletedProcess[str]]:
    """Run the module with only the repository source tree on PYTHONPATH."""

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PYTHONPATH"] = str(SOURCE_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "aiflow", *arguments],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )

    return run
