"""Require core branch and diff coverage from one full-suite database."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from coverage import Coverage

DOMAINS: tuple[tuple[str, str], ...] = (("core", "src/aiflow"),)


def check_coverage(repository: Path, run_dir: Path, base: str) -> int:
    """Report all domain files, then check each domain's changed lines."""
    repo_src = str(Path(__file__).resolve().parents[2] / "src")
    if repo_src not in sys.path:
        sys.path.insert(0, repo_src)
    from aiflow.coverage_check import check_coverage as _check_coverage

    return _check_coverage(
        repository,
        run_dir,
        base,
        domains=DOMAINS,
        coverage_factory=Coverage,
        run_subprocess=subprocess.run,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--base", required=True)
    arguments = parser.parse_args(argv)
    try:
        return check_coverage(Path.cwd().resolve(), arguments.run_dir, arguments.base)
    except Exception as error:
        print(f"Coverage check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
