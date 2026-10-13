"""Exercise both coverage gates with real Git diffs and branch coverage data."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from coverage import Coverage

CHECKER = Path(__file__).resolve().parents[2] / "tools" / "ci" / "check_coverage.py"
DOMAINS = ("src/aiflow", "tools/analysis")
MODULES = tuple(f"{domain}/{name}" for domain in DOMAINS for name in ("same.py", "nested/same.py"))
COLLECT_SCRIPT = """
import runpy
import sys
from coverage import Coverage

coverage = Coverage(data_file=sys.argv[1], config_file=False, branch=True)
coverage.start()
try:
    for source in sys.argv[2:]:
        runpy.run_path(source)
finally:
    coverage.stop()
    coverage.save()
"""


def _environment() -> dict[str, str]:
    # Neither the outer pytest collector nor a caller's Git context belongs here.
    return {
        key: value
        for key, value in os.environ.items()
        if key != "PYTHONPATH" and not key.startswith(("COVERAGE_", "COV_CORE_", "GIT_"))
    }


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        env=_environment(),
        capture_output=True,
        encoding="utf-8",
        check=True,
        timeout=20,
    )
    return result.stdout.strip()


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", ".")
    _git(
        repository,
        "-c",
        "user.name=Coverage Tests",
        "-c",
        "user.email=coverage@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD")


def _repository(tmp_path: Path) -> tuple[Path, Path, str]:
    repository = tmp_path / "r"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    source = "".join(f"value_{index} = {index}\n" for index in range(40))
    source += "\ndef choose(flag):\n    if flag:\n        return 1\n    return 0\n"
    source += "\nchoose(True)\nchoose(False)\n"
    for relative in MODULES:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    # A repository's display filters must not turn an omitted file into a pass.
    (repository / "pyproject.toml").write_text(
        "[tool.coverage.report]\nomit = ['*']\n", encoding="utf-8"
    )
    base = _commit(repository, "baseline")
    run_dir = tmp_path / "c"
    run_dir.mkdir()
    return repository, run_dir, base


def _collect(repository: Path, run_dir: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            COLLECT_SCRIPT,
            str(run_dir / ".coverage"),
            *(
                str(repository / relative)
                for relative in MODULES
                if (repository / relative).exists()
            ),
        ],
        cwd=repository,
        env=_environment(),
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )


def _total(repository: Path, run_dir: Path, domains: tuple[str, ...]) -> float:
    coverage = Coverage(data_file=str(run_dir / ".coverage"), config_file=False)
    coverage.load()
    files = [str(path) for domain in domains for path in (repository / domain).rglob("*.py")]
    return coverage.report(morfs=files, include=[], omit=[], file=io.StringIO())


def _check(repository: Path, run_dir: Path, base: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(CHECKER), "--run-dir", str(run_dir), "--base", base],
        cwd=repository,
        env=_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=110,
    )


def _reported_files(repository: Path, report: Path) -> set[Path]:
    document = ET.parse(report)
    sources = [element.text or "" for element in document.findall("./sources/source")]
    return {
        (repository / source / element.attrib["filename"]).resolve()
        for source in sources
        for element in document.findall(".//class")
    }


@pytest.mark.parametrize("change", ["documentation", "deletion"])
def test_coverage_gates_accept_no_added_measurable_lines(tmp_path: Path, change: str) -> None:
    repository, run_dir, base = _repository(tmp_path)
    if change == "documentation":
        (repository / "README.md").write_text("Documentation only.\n", encoding="utf-8")
    else:
        for domain in DOMAINS:
            (repository / domain / "nested" / "same.py").unlink()
    _commit(repository, change)
    _collect(repository, run_dir)

    result = _check(repository, run_dir, base)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(repository, "status", "--porcelain") == ""
    for name, domain in zip(("core", "analysis"), DOMAINS, strict=True):
        assert _reported_files(repository, run_dir / f"coverage-{name}.xml") == {
            path.resolve() for path in (repository / domain).rglob("*.py")
        }


def test_coverage_gates_map_changed_top_level_and_nested_same_names(tmp_path: Path) -> None:
    repository, run_dir, base = _repository(tmp_path)
    for relative in MODULES:
        path = repository / relative
        path.write_text(
            path.read_text(encoding="utf-8") + "changed = choose(True)\n", encoding="utf-8"
        )
    _commit(repository, "covered changes in every module")
    _collect(repository, run_dir)

    result = _check(repository, run_dir, base)

    assert result.returncode == 0, result.stdout + result.stderr
    for name, domain in zip(("core", "analysis"), DOMAINS, strict=True):
        assert _reported_files(repository, run_dir / f"coverage-{name}.xml") == {
            (repository / domain / name).resolve() for name in ("same.py", "nested/same.py")
        }


@pytest.mark.parametrize("domain", DOMAINS)
def test_coverage_gates_fail_each_total_with_no_changed_source(tmp_path: Path, domain: str) -> None:
    repository, run_dir, _ = _repository(tmp_path)
    (repository / domain / "unexecuted.py").write_text(
        "".join(f"missed_{index} = {index}\n" for index in range(20)), encoding="utf-8"
    )
    base = _commit(repository, "baseline includes unexecuted source")
    (repository / "README.md").write_text("Documentation change.\n", encoding="utf-8")
    _commit(repository, "documentation only")
    _collect(repository, run_dir)
    other = next(item for item in DOMAINS if item != domain)
    assert _total(repository, run_dir, (domain,)) < 85
    assert _total(repository, run_dir, (other,)) == 100
    assert _total(repository, run_dir, DOMAINS) >= 85

    result = _check(repository, run_dir, base)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "total coverage is below 85 percent" in result.stderr
    assert result.stdout.count("No lines with coverage information in this diff.") == 2


@pytest.mark.parametrize("domain", DOMAINS)
def test_coverage_gates_count_unexecuted_files_in_each_domain(tmp_path: Path, domain: str) -> None:
    repository, run_dir, base = _repository(tmp_path)
    unexecuted = repository / domain / "unexecuted.py"
    unexecuted.write_text(
        "".join(f"missed_{index} = {index}\n" for index in range(20)), encoding="utf-8"
    )
    _commit(repository, "add unexecuted source")
    _collect(repository, run_dir)
    other = next(item for item in DOMAINS if item != domain)
    assert _total(repository, run_dir, (domain,)) < 85
    assert _total(repository, run_dir, (other,)) == 100
    assert _total(repository, run_dir, DOMAINS) >= 85

    result = _check(repository, run_dir, base)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "total coverage is below 85 percent" in result.stderr
    report = run_dir / f"coverage-{'core' if domain == DOMAINS[0] else 'analysis'}.xml"
    assert unexecuted.resolve() in _reported_files(repository, report)
    assert "Coverage: 0%" in result.stdout


@pytest.mark.parametrize("relative", MODULES)
def test_coverage_gates_fail_each_changed_file_with_passing_totals(
    tmp_path: Path, relative: str
) -> None:
    repository, run_dir, base = _repository(tmp_path)
    path = repository / relative
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\ndef not_called(flag):\n    if flag:\n        return 1\n    return 0\n",
        encoding="utf-8",
    )
    other = next(domain for domain in DOMAINS if not relative.startswith(f"{domain}/"))
    covered = repository / other / "same.py"
    covered.write_text(
        covered.read_text(encoding="utf-8")
        + "".join(f"changed_{index} = {index}\n" for index in range(40)),
        encoding="utf-8",
    )
    _commit(repository, "add uncovered function")
    _collect(repository, run_dir)
    for domain in DOMAINS:
        assert _total(repository, run_dir, (domain,)) >= 85

    result = _check(repository, run_dir, base)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "total coverage is below 85 percent" not in result.stderr
    assert relative in result.stdout
    assert "Coverage: 25%" in result.stdout
    assert "Coverage: 100%" in result.stdout


@pytest.mark.parametrize("domain", DOMAINS)
@pytest.mark.parametrize("hidden", [".unexecuted.py", ".hidden/unexecuted.py"])
def test_coverage_gates_reject_uncovered_hidden_changes(
    tmp_path: Path, domain: str, hidden: str
) -> None:
    repository, run_dir, base = _repository(tmp_path)
    relative = f"{domain}/{hidden}"
    unexecuted = repository / relative
    unexecuted.parent.mkdir(parents=True, exist_ok=True)
    unexecuted.write_text(
        "".join(f"missed_{index} = {index}\n" for index in range(4)), encoding="utf-8"
    )
    other = next(item for item in DOMAINS if item != domain)
    covered = repository / other / "same.py"
    covered.write_text(
        covered.read_text(encoding="utf-8")
        + "".join(f"changed_{index} = {index}\n" for index in range(40)),
        encoding="utf-8",
    )
    _commit(repository, "add uncovered hidden source and covered opposite-domain lines")
    _collect(repository, run_dir)
    totals = {item: _total(repository, run_dir, (item,)) for item in DOMAINS}
    assert all(total >= 85 for total in totals.values())

    result = _check(repository, run_dir, base)

    report = run_dir / f"coverage-{'core' if domain == DOMAINS[0] else 'analysis'}.xml"
    assert unexecuted.resolve() in _reported_files(repository, report)
    hidden_class = next(
        element
        for element in ET.parse(report).findall(".//class")
        if element.attrib["filename"].replace("\\", "/").endswith(relative)
    )
    hidden_lines = hidden_class.findall("./lines/line")
    assert len(hidden_lines) == 4
    assert {line.attrib["hits"] for line in hidden_lines} == {"0"}
    assert result.returncode == 1, (
        f"domain totals={totals}; hidden XML has four unexecuted lines\n"
        + result.stdout
        + result.stderr
    )
    assert "total coverage is below 85 percent" not in result.stderr
    assert relative in result.stdout
    assert "Coverage: 0%" in result.stdout
    assert "Coverage: 100%" in result.stdout
