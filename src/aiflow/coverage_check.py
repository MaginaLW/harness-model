"""Reusable branch and diff coverage gate for AI Flow Python verification."""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

DEFAULT_DOMAINS: tuple[tuple[str, str], ...] = (("core", "src/aiflow"),)
_BASE_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_DOMAIN_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def _validate_source_domain(source: str) -> str:
    """Validate a clean repository-relative POSIX directory path."""
    if not isinstance(source, str) or not source or source.startswith("/") or source.endswith("/"):
        raise ValueError("source domain must be a non-empty relative POSIX path")
    if (
        "\\" in source
        or ":" in source
        or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in source)
    ):
        raise ValueError("source domain contains invalid characters")
    segments = source.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("source domain contains invalid path segments")
    return source


def _validate_domains(domains: Sequence[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    if not domains:
        raise ValueError("at least one coverage domain is required")
    seen_names: set[str] = set()
    validated: list[tuple[str, str]] = []
    for name, relative in domains:
        if _DOMAIN_NAME_PATTERN.fullmatch(name) is None:
            raise ValueError(f"{name}: coverage domain name is invalid")
        if name in seen_names:
            raise ValueError(f"{name}: duplicate coverage domain name")
        seen_names.add(name)
        validated.append((name, _validate_source_domain(relative)))
    return tuple(validated)


def check_coverage(
    repository: Path,
    run_dir: Path,
    base: str,
    *,
    domains: Sequence[tuple[str, str]] = DEFAULT_DOMAINS,
    coverage_factory: Callable[..., Any] | None = None,
    run_subprocess: Callable[..., subprocess.CompletedProcess[Any]] | None = None,
) -> int:
    """Report all domain files, then check each domain's changed lines."""
    if _BASE_SHA_PATTERN.fullmatch(base) is None:
        raise ValueError("base must be a complete lowercase Git commit SHA")
    validated_domains = _validate_domains(domains)
    repository = repository.resolve()
    if Path.cwd().resolve() != repository:
        raise ValueError("coverage checks must run from the repository root")
    run_dir = run_dir.resolve()
    data_file = run_dir / ".coverage"
    if not run_dir.is_dir() or not data_file.is_file():
        raise ValueError("coverage database is missing")

    if coverage_factory is None:
        from coverage import Coverage

        coverage_factory = Coverage
    if run_subprocess is None:
        run_subprocess = subprocess.run

    coverage = coverage_factory(data_file=str(data_file), config_file=False)
    coverage.load()
    data = coverage.get_data()
    measured = {(repository / filename).resolve() for filename in data.measured_files()}
    if not measured or not data.has_arcs():
        raise ValueError("nonempty branch coverage data is required")

    inventories: dict[str, list[str]] = {}
    for name, relative in validated_domains:
        domain = (repository / relative).resolve()
        if domain == repository or not domain.is_relative_to(repository):
            raise ValueError(f"{name}: source domain escapes repository")
        files = sorted(path.resolve() for path in domain.rglob("*.py") if path.is_file())
        if not files or any(
            not path.is_relative_to(domain) or not path.is_relative_to(repository) for path in files
        ):
            raise ValueError(f"{name}: source inventory is empty or escapes its domain")
        if not measured.intersection(files):
            raise ValueError(f"{name}: no measured source files")
        inventories[name] = [str(path) for path in files]

    failed = False
    for name, _ in validated_domains:
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
        result = run_subprocess(
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


def _domains_from_sources(sources: Sequence[str] | None) -> tuple[tuple[str, str], ...]:
    if not sources:
        return DEFAULT_DOMAINS
    unique_sources = tuple(dict.fromkeys(_validate_source_domain(source) for source in sources))
    if len(unique_sources) == 1:
        return (("target", unique_sources[0]),)
    return tuple(
        (f"target-{index}", source) for index, source in enumerate(unique_sources, start=1)
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--base", required=True)
    parser.add_argument("--source", action="append", default=[])
    arguments = parser.parse_args(argv)
    try:
        domains = _domains_from_sources(arguments.source)
        return check_coverage(
            Path.cwd().resolve(),
            arguments.run_dir,
            arguments.base,
            domains=domains,
        )
    except Exception as error:
        print(f"Coverage check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
