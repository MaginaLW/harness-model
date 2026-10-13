"""Require independent core and analysis coverage from one full-suite database."""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from coverage import Coverage

DOMAINS = (("core", "src/aiflow"), ("analysis", "tools/analysis"))


def check_coverage(repository: Path, run_dir: Path, base: str) -> int:
    """Report all domain files, then check each domain's changed lines."""
    if re.fullmatch(r"[0-9a-f]{40}", base) is None:
        raise ValueError("base must be a complete lowercase Git commit SHA")
    repository = repository.resolve()
    if Path.cwd().resolve() != repository:
        raise ValueError("coverage checks must run from the repository root")
    run_dir = run_dir.resolve()
    data_file = run_dir / ".coverage"
    if not run_dir.is_dir() or not data_file.is_file():
        raise ValueError("coverage database is missing")
    coverage = Coverage(data_file=str(data_file), config_file=False)
    coverage.load()
    data = coverage.get_data()
    measured = {(repository / filename).resolve() for filename in data.measured_files()}
    if not measured or not data.has_arcs():
        raise ValueError("nonempty branch coverage data is required")

    inventories: dict[str, list[str]] = {}
    for name, relative in DOMAINS:
        domain = repository / relative
        files = sorted(path.resolve() for path in domain.rglob("*.py") if path.is_file())
        if not files or any(not path.is_relative_to(domain) for path in files):
            raise ValueError(f"{name}: source inventory is empty or escapes its domain")
        if not measured.intersection(files):
            raise ValueError(f"{name}: no measured source files")
        inventories[name] = [str(path) for path in files]

    failed = False
    for name, _ in DOMAINS:
        print(f"Coverage domain: {name}", flush=True)
        total = coverage.report(morfs=inventories[name], include=[], omit=[], ignore_errors=False)
        if not math.isfinite(total) or total < 85:
            print(f"{name}: total coverage is below 85 percent", file=sys.stderr)
            failed = True
        xml_file = run_dir / f"coverage-{name}.xml"
        if xml_file.resolve().parent != run_dir:
            raise ValueError("coverage report path escapes the run directory")
        coverage.xml_report(
            morfs=inventories[name],
            outfile=str(xml_file),
            include=[],
            omit=[],
            ignore_errors=False,
        )
        # The domain XML is the filter, including hidden Python files.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "diff_cover.diff_cover_tool",
                str(xml_file),
                "--compare-branch",
                base,
                "--fail-under=90",
            ],
            cwd=repository,
            shell=False,
            check=False,
            timeout=45,
        )
        failed = result.returncode != 0 or failed
    return int(failed)


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
