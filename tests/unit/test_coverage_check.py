"""Unit tests for reusable portable Python branch and diff coverage checks."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from coverage import Coverage, CoverageData

from aiflow import coverage_check

BASE = "a" * 40


def _setup_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, source_rel: str = "src/sample_pkg"
) -> tuple[Path, Path, Mock, Mock, Mock]:
    repository = tmp_path / "repository"
    path = repository / source_rel / "module.py"
    path.parent.mkdir(parents=True)
    path.write_text("value = 1\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / ".coverage").write_bytes(b"fixture")
    coverage = Mock()
    coverage.get_data.return_value.measured_files.return_value = {str(path.resolve())}
    coverage.get_data.return_value.has_arcs.return_value = True
    coverage.report.side_effect = [100.0]
    factory = Mock(return_value=coverage)
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.chdir(repository)
    return repository, run_dir, coverage, factory, run


@pytest.mark.parametrize(
    "valid_source",
    [
        "src/aiflow",
        "src/sample_pkg",
        "pkg",
        "packages/sub_pkg/src",
        ".hidden_src",
    ],
)
def test_validate_source_domain_accepts_clean_relative_posix_paths(valid_source: str) -> None:
    assert coverage_check._validate_source_domain(valid_source) == valid_source


@pytest.mark.parametrize(
    "invalid_source",
    [
        "",
        "/",
        "/src/aiflow",
        "src/aiflow/",
        ".",
        "..",
        "./src",
        "../src",
        "src/./pkg",
        "src/../pkg",
        "src//pkg",
        r"src\pkg",
        "C:/src/pkg",
        "C:src/pkg",
        "src pkg",
        "src\tpkg",
        "src\npkg",
        "src\x00pkg",
        "src\x7fpkg",
    ],
)
def test_validate_source_domain_rejects_unsafe_paths(invalid_source: str) -> None:
    with pytest.raises(ValueError):
        coverage_check._validate_source_domain(invalid_source)


def test_importing_coverage_check_does_not_require_coverage_package() -> None:
    code = (
        "import sys; sys.modules['coverage'] = None; "
        "import aiflow.coverage_check as m; "
        "assert 'coverage' in sys.modules and sys.modules['coverage'] is None; "
        "assert m._validate_source_domain('src/pkg') == 'src/pkg'"
    )
    src_root = str(Path(__file__).resolve().parents[2] / "src")
    env = dict(os.environ)
    env["PYTHONPATH"] = src_root
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_check_coverage_passes_for_custom_domain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, run_dir, coverage, factory, run = _setup_repo(tmp_path, monkeypatch)
    assert (
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("target", "src/sample_pkg"),),
            coverage_factory=factory,
            run_subprocess=run,
        )
        == 0
    )
    factory.assert_called_once_with(data_file=str(run_dir / ".coverage"), config_file=False)
    coverage.load.assert_called_once_with()
    assert coverage.report.call_count == 1
    assert coverage.xml_report.call_args_list[0].kwargs["outfile"] == str(
        run_dir.resolve() / "coverage-target.xml"
    )
    assert run.call_args_list[0].args == (
        [
            sys.executable,
            "-m",
            "diff_cover.diff_cover_tool",
            str(run_dir.resolve() / "coverage-target.xml"),
            "--compare-branch",
            BASE,
            "--fail-under=90",
        ],
    )


@pytest.mark.parametrize(
    ("total", "diff_rc", "expected"),
    [
        (85.0, 0, 0),
        (84.99, 0, 1),
        (float("nan"), 0, 1),
        (float("inf"), 0, 1),
        (95.0, 1, 1),
        (95.0, 2, 1),
    ],
)
def test_check_coverage_enforces_hard_thresholds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, total: float, diff_rc: int, expected: int
) -> None:
    repository, run_dir, coverage, factory, run = _setup_repo(tmp_path, monkeypatch)
    coverage.report.side_effect = [total]
    run.side_effect = [subprocess.CompletedProcess([], diff_rc)]
    assert (
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("target", "src/sample_pkg"),),
            coverage_factory=factory,
            run_subprocess=run,
        )
        == expected
    )


@pytest.mark.parametrize("base", ["main", "a" * 39, "A" * 40, "g" * 40, ""])
def test_check_coverage_rejects_invalid_base_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, base: str
) -> None:
    repository, run_dir, _, factory, run = _setup_repo(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="complete lowercase Git commit SHA"):
        coverage_check.check_coverage(
            repository, run_dir, base, coverage_factory=factory, run_subprocess=run
        )
    factory.assert_not_called()
    run.assert_not_called()


def test_check_coverage_rejects_wrong_cwd_and_missing_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, run_dir, _, factory, run = _setup_repo(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="repository root"):
        coverage_check.check_coverage(
            repository, run_dir, BASE, coverage_factory=factory, run_subprocess=run
        )

    monkeypatch.chdir(repository)
    (run_dir / ".coverage").unlink()
    with pytest.raises(ValueError, match="database is missing"):
        coverage_check.check_coverage(
            repository, run_dir, BASE, coverage_factory=factory, run_subprocess=run
        )
    run_dir.rmdir()
    with pytest.raises(ValueError, match="database is missing"):
        coverage_check.check_coverage(
            repository, run_dir, BASE, coverage_factory=factory, run_subprocess=run
        )


def test_check_coverage_rejects_domain_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, run_dir, coverage, factory, run = _setup_repo(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="at least one"):
        coverage_check.check_coverage(
            repository, run_dir, BASE, domains=(), coverage_factory=factory, run_subprocess=run
        )
    with pytest.raises(ValueError, match="domain name is invalid"):
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("../escape", "src/sample_pkg"),),
            coverage_factory=factory,
            run_subprocess=run,
        )
    with pytest.raises(ValueError, match="duplicate coverage domain"):
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("target", "src/sample_pkg"), ("target", "src/other")),
            coverage_factory=factory,
            run_subprocess=run,
        )
    coverage.get_data.return_value.has_arcs.return_value = False
    with pytest.raises(ValueError, match="branch coverage"):
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("target", "src/sample_pkg"),),
            coverage_factory=factory,
            run_subprocess=run,
        )
    coverage.get_data.return_value.has_arcs.return_value = True
    coverage.get_data.return_value.measured_files.return_value = set()
    with pytest.raises(ValueError, match="branch coverage"):
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("target", "src/sample_pkg"),),
            coverage_factory=factory,
            run_subprocess=run,
        )
    coverage.get_data.return_value.measured_files.return_value = {
        str((repository / "tests/test_other.py").resolve())
    }
    with pytest.raises(ValueError, match="no measured source files"):
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("target", "src/sample_pkg"),),
            coverage_factory=factory,
            run_subprocess=run,
        )
    (repository / "src/sample_pkg/module.py").unlink()
    with pytest.raises(ValueError, match="inventory is empty"):
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("target", "src/sample_pkg"),),
            coverage_factory=factory,
            run_subprocess=run,
        )


def test_check_coverage_rejects_symlink_domain_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, run_dir, coverage, factory, run = _setup_repo(tmp_path, monkeypatch)
    outside = tmp_path / "outside_pkg"
    outside.mkdir()
    outside_file = outside / "secret.py"
    outside_file.write_text("secret = 1\n", encoding="utf-8")
    escape_link = repository / "src/escaped"
    try:
        escape_link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    coverage.get_data.return_value.measured_files.return_value = {str(outside_file.resolve())}
    with pytest.raises(ValueError, match="escapes repository"):
        coverage_check.check_coverage(
            repository,
            run_dir,
            BASE,
            domains=(("target", "src/escaped"),),
            coverage_factory=factory,
            run_subprocess=run,
        )


def test_check_coverage_real_non_branch_database_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, run_dir, _, _, _ = _setup_repo(tmp_path, monkeypatch, source_rel="src/aiflow")
    data_file = run_dir / ".coverage"
    data_file.unlink()
    data = CoverageData(basename=str(data_file))
    data.add_lines({str(repository / "src/aiflow/module.py"): {1}})
    data.write()
    assert coverage_check.main(["--run-dir", str(run_dir), "--base", BASE]) == 1
    assert "Coverage check failed:" in capsys.readouterr().err


def test_check_coverage_real_branch_database_and_cli_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    pkg_a = repository / "src/pkg_a"
    pkg_b = repository / "src/pkg_b"
    pkg_a.mkdir(parents=True)
    pkg_b.mkdir(parents=True)
    mod_a = pkg_a / "__init__.py"
    mod_b = pkg_b / "__init__.py"
    mod_a.write_text("def f(x: bool) -> int:\n    return 1 if x else 0\n", encoding="utf-8")
    mod_b.write_text("def g(x: bool) -> int:\n    return 2 if x else 3\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    cov = Coverage(data_file=str(run_dir / ".coverage"), config_file=False, branch=True)
    cov.start()
    mod_a_ns: dict[str, object] = {}
    mod_b_ns: dict[str, object] = {}
    exec(compile(mod_a.read_text(encoding="utf-8"), str(mod_a), "exec"), mod_a_ns)
    exec(compile(mod_b.read_text(encoding="utf-8"), str(mod_b), "exec"), mod_b_ns)
    mod_a_ns["f"](True)  # type: ignore[operator]
    mod_a_ns["f"](False)  # type: ignore[operator]
    mod_b_ns["g"](True)  # type: ignore[operator]
    mod_b_ns["g"](False)  # type: ignore[operator]
    cov.stop()
    cov.save()

    monkeypatch.chdir(repository)
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(subprocess, "run", run)

    assert (
        coverage_check.main(
            [
                "--run-dir",
                str(run_dir),
                "--base",
                BASE,
                "--source",
                "src/pkg_a",
                "--source",
                "src/pkg_b",
                "--source",
                "src/pkg_a",
            ]
        )
        == 0
    )
    assert (run_dir / "coverage-target-1.xml").is_file()
    assert (run_dir / "coverage-target-2.xml").is_file()
    assert run.call_count == 2

    assert (
        coverage_check.main(
            [
                "--run-dir",
                str(run_dir),
                "--base",
                BASE,
                "--source",
                "src/pkg_a",
            ]
        )
        == 0
    )
    assert (run_dir / "coverage-target.xml").is_file()
    assert run.call_count == 3


def test_cli_rejects_threshold_override_and_invalid_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, run_dir, _, _, _ = _setup_repo(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as error:
        coverage_check.main(["--run-dir", str(run_dir), "--base", BASE, "--fail-under", "0"])
    assert error.value.code == 2

    assert (
        coverage_check.main(["--run-dir", str(run_dir), "--base", BASE, "--source", "../outside"])
        == 1
    )
    assert "Coverage check failed:" in capsys.readouterr().err
    assert Path.cwd().resolve() == repository.resolve()
