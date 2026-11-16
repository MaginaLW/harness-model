"""Independent coverage gates, fixed commands, and fail-closed inputs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from coverage import Coverage, CoverageData

from tools.ci import check_coverage as checker

BASE = "a" * 40


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repository = tmp_path / "repository"
    path = repository / "src/aiflow/example.py"
    path.parent.mkdir(parents=True)
    path.write_text("value = 1\n", encoding="utf-8")
    files = [path.resolve()]
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / ".coverage").write_bytes(b"fixture")
    coverage = Mock()
    coverage.get_data.return_value.measured_files.return_value = {str(item) for item in files}
    coverage.get_data.return_value.has_arcs.return_value = True
    coverage.report.side_effect = [100.0]
    factory = Mock(return_value=coverage)
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(checker, "Coverage", factory)
    monkeypatch.setattr(checker.subprocess, "run", run)
    monkeypatch.chdir(repository)
    return repository, run_dir, coverage, factory, run


def test_fixed_domain_includes_unmeasured_nested_files_and_writes_core_report(setup) -> None:
    repository, run_dir, coverage, factory, run = setup
    unmeasured = repository / "src/aiflow/nested/unimported.py"
    unmeasured.parent.mkdir()
    unmeasured.write_text("not_executed = 1\n", encoding="utf-8")

    assert checker.check_coverage(repository, run_dir, BASE) == 0

    factory.assert_called_once_with(data_file=str(run_dir / ".coverage"), config_file=False)
    coverage.load.assert_called_once_with()
    assert len(checker.DOMAINS) == 1
    name, relative = checker.DOMAINS[0]
    assert (name, relative) == ("core", "src/aiflow")
    expected = sorted(str(path.resolve()) for path in (repository / relative).rglob("*.py"))
    assert coverage.report.call_args_list[0].kwargs == {
        "morfs": expected,
        "include": [],
        "omit": [],
        "ignore_errors": False,
    }
    xml = run_dir / f"coverage-{name}.xml"
    assert coverage.xml_report.call_args_list[0].kwargs == {
        "morfs": expected,
        "outfile": str(xml),
        "include": [],
        "omit": [],
        "ignore_errors": False,
    }
    assert run.call_args_list[0].args == (
        [
            sys.executable,
            "-m",
            "diff_cover.diff_cover_tool",
            str(xml),
            "--compare-branch",
            BASE,
            "--fail-under=90",
        ],
    )
    assert run.call_args_list[0].kwargs == {
        "cwd": repository.resolve(),
        "shell": False,
        "check": False,
        "timeout": 45,
    }


@pytest.mark.parametrize(
    ("totals", "expected"),
    [
        ([85.0], 0),
        ([84.9999999], 1),
        ([float("nan")], 1),
        ([float("inf")], 1),
    ],
)
def test_raw_total_thresholds_cannot_round_up(setup, totals, expected) -> None:
    repository, run_dir, coverage, _, run = setup
    coverage.report.side_effect = totals
    assert checker.check_coverage(repository, run_dir, BASE) == expected
    assert coverage.report.call_count == run.call_count == 1


@pytest.mark.parametrize("code", [1, 2])
def test_diff_failure_fails_closed(setup, code) -> None:
    repository, run_dir, _, _, run = setup
    run.side_effect = [subprocess.CompletedProcess([], code)]
    assert checker.check_coverage(repository, run_dir, BASE) == 1
    assert run.call_count == 1


@pytest.mark.parametrize("base", ["main", "a" * 39, "A" * 40, "g" * 40, "--help", ""])
def test_non_commit_base_is_rejected_before_reading_data(setup, base: str) -> None:
    repository, run_dir, _, factory, run = setup
    with pytest.raises(ValueError, match="complete lowercase Git commit SHA"):
        checker.check_coverage(repository, run_dir, base)
    factory.assert_not_called()
    run.assert_not_called()


@pytest.mark.parametrize("missing", ["directory", "database"])
def test_missing_database_fails(setup, missing: str) -> None:
    repository, run_dir, _, factory, run = setup
    (run_dir / ".coverage").unlink()
    if missing == "directory":
        run_dir.rmdir()
    with pytest.raises(ValueError, match="database is missing"):
        checker.check_coverage(repository, run_dir, BASE)
    factory.assert_not_called()
    run.assert_not_called()


@pytest.mark.parametrize("invalid", ["empty", "statement_only", "unmeasured_core"])
def test_missing_measurements_and_non_branch_data_fail(setup, invalid: str) -> None:
    repository, run_dir, coverage, _, run = setup
    data = coverage.get_data.return_value
    if invalid == "empty":
        data.measured_files.return_value = set()
    elif invalid == "statement_only":
        data.has_arcs.return_value = False
    else:
        data.measured_files.return_value = {str(repository / "tests/example_test.py")}
    with pytest.raises(ValueError, match="branch coverage|no measured source"):
        checker.check_coverage(repository, run_dir, BASE)
    coverage.report.assert_not_called()
    run.assert_not_called()


def test_missing_domain_inventory_fails(setup) -> None:
    repository, run_dir, coverage, _, run = setup
    (repository / "src/aiflow/example.py").unlink()
    with pytest.raises(ValueError, match="inventory is empty"):
        checker.check_coverage(repository, run_dir, BASE)
    coverage.report.assert_not_called()
    run.assert_not_called()


@pytest.mark.parametrize("failure", ["load", "report", "xml", "tool", "timeout", "unexpected"])
def test_cli_fails_closed_for_database_report_and_subprocess_errors(setup, capsys, failure) -> None:
    _, run_dir, coverage, _, run = setup
    if failure == "load":
        coverage.load.side_effect = ValueError("invalid database")
    elif failure == "report":
        coverage.report.side_effect = OSError("unreadable source")
    elif failure == "xml":
        coverage.xml_report.side_effect = OSError("report unavailable")
    elif failure == "tool":
        run.side_effect = FileNotFoundError("tool unavailable")
    elif failure == "timeout":
        run.side_effect = subprocess.TimeoutExpired("diff-cover", 45)
    else:
        coverage.report.side_effect = RuntimeError("unexpected report failure")

    assert checker.main(["--run-dir", str(run_dir), "--base", BASE]) == 1
    assert "Coverage check failed:" in capsys.readouterr().err


def test_relative_measurements_are_resolved_against_repository(setup) -> None:
    repository, run_dir, coverage, _, _ = setup
    coverage.get_data.return_value.measured_files.return_value = {"src/aiflow/example.py"}
    assert checker.check_coverage(repository, run_dir, BASE) == 0


def test_direct_api_rejects_a_different_working_directory(setup, monkeypatch) -> None:
    repository, run_dir, _, factory, _ = setup
    monkeypatch.chdir(repository.parent)
    with pytest.raises(ValueError, match="repository root"):
        checker.check_coverage(repository, run_dir, BASE)
    factory.assert_not_called()


@pytest.mark.parametrize("kind", ["invalid", "statement_only"])
def test_real_database_rejection_preserves_input(setup, monkeypatch, capsys, kind) -> None:
    repository, run_dir, _, _, run = setup
    data_file = run_dir / ".coverage"
    if kind == "statement_only":
        data_file.unlink()
        data = CoverageData(basename=str(data_file))
        data.add_lines({str(repository / "src/aiflow/example.py"): {1}})
        data.write()
    original = data_file.read_bytes()
    monkeypatch.setattr(checker, "Coverage", Coverage)

    assert checker.main(["--run-dir", str(run_dir), "--base", BASE]) == 1

    assert "Coverage check failed:" in capsys.readouterr().err
    assert data_file.read_bytes() == original
    assert not list(run_dir.glob("*.xml"))
    run.assert_not_called()


def test_cli_rejects_threshold_overrides(setup) -> None:
    _, run_dir, _, factory, _ = setup
    with pytest.raises(SystemExit) as error:
        checker.main(["--run-dir", str(run_dir), "--base", BASE, "--fail-under", "0"])
    assert error.value.code == 2
    factory.assert_not_called()
