"""Fixed trusted-directory discovery, failure diagnostics, and Windows live probes."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.diagnostics import tool_discovery as subject

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "diagnostics" / "tool_discovery.py"


def observations(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    return {
        name: {"status": "observed", "version": "3.11.9", "cleanup_confirmed": True}
        for name in paths
    }


@pytest.fixture
def selected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.setattr(subject, "WINDOWS", True)
    if os.name != "nt":
        monkeypatch.setattr(subject, "_windows_directory_is_local", lambda _: True)
    directory = tmp_path / "trusted"
    directory.mkdir()
    for name in subject.NAMES:
        (directory / f"{name}.exe").write_bytes(b"not executed by synthetic tests")
    monkeypatch.setattr(subject, "_probe", observations)
    return [str(directory)]


def test_explicit_discovery_ignores_hostile_path_and_preserves_environment(
    selected: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hostile = tmp_path / "hostile"
    hostile.mkdir()
    for name in subject.NAMES:
        (hostile / f"{name}.exe").write_bytes(b"never run")
    monkeypatch.setenv("PATH", str(hostile))
    monkeypatch.chdir(hostile)
    before = dict(os.environ)
    report = subject.discover(selected, ["python=3.11.9"])
    assert report["status"] == "TOOLS_OBSERVED"
    assert report["exit_code"] == 0
    assert report["ambient_path_used"] is False
    assert report["runner_ready"] is report["gate_pass"] is False
    assert report["reason_codes"] == []
    assert str(hostile) not in json.dumps(report)
    assert selected[0] not in json.dumps(report)
    assert dict(os.environ) == before


def test_private_output_is_explicit_and_versions_are_exact(selected: list[str]) -> None:
    report = subject.discover(selected, ["git=2.55.0.windows.3"], include_private_details=True)
    assert report["exit_code"] == 1
    assert report["tools"][1]["status"] == "version_mismatch"
    assert "GIT_VERSION_MISMATCH" in report["reason_codes"]
    assert report["tools"][0]["path"] == str(Path(selected[0]) / "python.exe")


@pytest.mark.parametrize("missing", ["python", "git", "pwsh"])
def test_missing_tool_never_searches_ambient_path(
    selected: list[str], monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    (Path(selected[0]) / f"{missing}.exe").unlink()
    called: list[dict[str, Path]] = []

    def probe(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
        called.append(paths)
        return observations(paths)

    monkeypatch.setattr(subject, "_probe", probe)
    report = subject.discover(selected)
    assert report["exit_code"] == 1
    assert f"{missing.upper()}_MISSING" in report["reason_codes"]
    assert len(report["tools"]) == 3
    if missing == "pwsh":
        assert not called
        assert "TRUSTED_PWSH_REQUIRED_FOR_VERSION_PROBE" in report["reason_codes"]
        assert [tool["status"] for tool in report["tools"]] == ["located", "located", "missing"]
    else:
        assert len(called) == 1 and missing not in called[0]


def test_ambiguous_tool_is_not_selected(selected: list[str], tmp_path: Path) -> None:
    other = tmp_path / "second_trusted"
    other.mkdir()
    (other / "git.exe").write_bytes(b"other")
    report = subject.discover([*selected, str(other)])
    assert report["tools"][1]["status"] == "ambiguous"
    assert "GIT_AMBIGUOUS" in report["reason_codes"]


@pytest.mark.parametrize(
    "expectations", [["unknown=3.1.0"], ["python"], ["python=3"], ["git=1.2.3", "git=1.2.3"]]
)
def test_invalid_expectations_fail_before_probe(
    selected: list[str], expectations: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subject, "_probe", lambda _: pytest.fail("invalid input ran probe"))
    report = subject.discover(selected, expectations)
    assert report["exit_code"] == 2
    assert report["reason_codes"] == ["INVALID_INPUT"]


def test_directories_must_be_explicit_absolute_existing_and_unique(
    selected: list[str], tmp_path: Path
) -> None:
    invalid = [
        [],
        ["."],
        [str(tmp_path / "absent")],
        selected * 2,
        selected * 17,
        [str(Path(selected[0]) / "python.exe")],
        [str(tmp_path / "trusted" / ".." / "trusted")],
    ]
    for directories in invalid:
        report = subject.discover(directories)
        assert report["exit_code"] == 2
        assert all(tool["status"] == "not_checked" for tool in report["tools"])


@pytest.mark.parametrize(
    "path",
    [
        r"\\server\share\tools",
        "//server/share/tools",
        r"\\?\C:\tools",
        r"\\?\UNC\server\share\tools",
        r"\\.\C:\tools",
        r"\??\C:\tools",
        r"C:tools",
        r"\tools",
    ],
)
def test_unc_and_device_paths_are_rejected_without_metadata_or_drive_lookup(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr(subject, "WINDOWS", True)
    monkeypatch.setattr(subject, "_drive_type", lambda _: pytest.fail("queried remote drive"))
    monkeypatch.setattr(
        subject, "_plain_path", lambda *a, **kw: pytest.fail("read remote metadata")
    )
    monkeypatch.setattr(subject, "_probe", lambda _: pytest.fail("executed remote tool"))
    assert subject.discover([path])["status"] == "INPUT_INVALID"


@pytest.mark.parametrize("drive_type", [0, 1, 4, 99])
def test_remote_and_unknown_drive_types_are_rejected_before_metadata(
    monkeypatch: pytest.MonkeyPatch, drive_type: int
) -> None:
    queried: list[str] = []

    def lookup(root: str) -> int:
        queried.append(root)
        return drive_type

    monkeypatch.setattr(subject, "WINDOWS", True)
    monkeypatch.setattr(subject, "_drive_type", lookup)
    monkeypatch.setattr(subject, "_plain_path", lambda *a, **kw: pytest.fail("read mapped share"))
    assert subject.discover([r"Z:\trusted"])["status"] == "INPUT_INVALID"
    assert queried == ["Z:\\"]


@pytest.mark.parametrize("drive_type", [2, 3, 5, 6])
def test_local_drive_types_are_explicitly_supported(
    monkeypatch: pytest.MonkeyPatch, drive_type: int
) -> None:
    monkeypatch.setattr(subject, "_drive_type", lambda _: drive_type)
    assert subject._windows_directory_is_local(r"C:\trusted")


def test_failed_drive_type_query_is_not_local(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_: str) -> int:
        raise OSError("private driver detail")

    monkeypatch.setattr(subject, "_drive_type", fail)
    assert not subject._windows_directory_is_local(r"C:\trusted")


def test_directory_candidate_cannot_be_executed(selected: list[str]) -> None:
    path = Path(selected[0]) / "git.exe"
    path.unlink()
    path.mkdir()
    report = subject.discover(selected)
    assert report["tools"][1]["status"] == "unsafe_or_unreadable"


def test_special_file_is_not_an_executable(
    selected: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.lstat

    def special(path: Path) -> Any:
        if path.name != "git.exe":
            return original(path)

        class Fifo:
            st_mode = stat.S_IFIFO

        return Fifo()

    monkeypatch.setattr(Path, "lstat", special)
    assert subject.discover(selected)["tools"][1]["status"] == "unsafe_or_unreadable"


def test_metadata_failure_is_not_missing(
    selected: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = subject._plain_path

    def denied(path: Path, *, directory: bool) -> bool:
        if path.name == "git.exe":
            raise PermissionError("private path and sensitive error")
        return original(path, directory=directory)

    monkeypatch.setattr(subject, "_plain_path", denied)
    report = subject.discover(selected)
    assert report["tools"][1]["status"] == "unsafe_or_unreadable"
    assert "private path" not in json.dumps(report)


@pytest.mark.parametrize("ancestor", [False, True])
def test_symlink_and_reparse_metadata_are_rejected(
    selected: list[str], monkeypatch: pytest.MonkeyPatch, ancestor: bool
) -> None:
    original = Path.lstat
    target = Path(selected[0]).parent if ancestor else Path(selected[0]) / "git.exe"

    def reparse(path: Path) -> Any:
        result = original(path)
        if path != target:
            return result

        class Reparse:
            st_mode = result.st_mode
            st_file_attributes = 0x400

        return Reparse()

    monkeypatch.setattr(Path, "lstat", reparse)
    report = subject.discover(selected)
    if ancestor:
        assert report["exit_code"] == 2
    else:
        assert report["tools"][1]["status"] == "unsafe_or_unreadable"


@pytest.mark.parametrize(
    "error", [OSError("private"), ValueError("private"), subprocess.TimeoutExpired("private", 45)]
)
def test_probe_failure_redacts_errors(
    selected: list[str], monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def fail(_: Any) -> Any:
        raise error

    monkeypatch.setattr(subject, "_probe", fail)
    report = subject.discover(selected)
    assert report["exit_code"] == 1
    assert "VERSION_PROBE_FAILED" in report["reason_codes"]
    assert "private" not in json.dumps(report)


def test_non_windows_has_no_live_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in subject.NAMES:
        (tmp_path / name).write_bytes(b"not a live Linux executable")
    monkeypatch.setattr(subject, "WINDOWS", False)
    monkeypatch.setattr(subject, "_probe", lambda _: pytest.fail("Windows probe on Linux"))
    report = subject.discover([str(tmp_path)])
    assert report["exit_code"] == 1
    assert "LIVE_VERSION_PROBE_WINDOWS_ONLY" in report["reason_codes"]
    assert all(tool["status"] == "located" for tool in report["tools"])


def test_bridge_argv_environment_and_output_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = {name: tmp_path / f"{name}.exe" for name in subject.NAMES}
    expected = observations(paths)
    monkeypatch.setenv("PATH", "untrusted search")
    monkeypatch.setenv("SECRET_TEST_VALUE", "never inherit")

    def run(argv: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv == [
            str(paths["pwsh"]),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(subject.BRIDGE),
        ]
        assert kwargs["shell"] is False
        assert kwargs["env"]["PATH"] == ""
        assert "SECRET_TEST_VALUE" not in kwargs["env"]
        assert kwargs["env"]["PSModulePath"] == str(tmp_path / "Modules")
        assert json.loads(kwargs["input"]) == {name: str(path) for name, path in paths.items()}
        assert kwargs["timeout"] == 45
        return subprocess.CompletedProcess(argv, 0, json.dumps(expected), "")

    monkeypatch.setattr(subject.subprocess, "run", run)
    assert subject._probe(paths) == expected


@pytest.mark.parametrize(
    "output",
    [
        "not JSON",
        "[]",
        "{}",
        json.dumps(
            {"pwsh": {"status": "observed", "version": "7.6.6", "cleanup_confirmed": False}}
        ),
        json.dumps(
            {"pwsh": {"status": "observed", "version": "private", "cleanup_confirmed": True}}
        ),
        json.dumps({"pwsh": {"status": "unknown", "version": "", "cleanup_confirmed": True}}),
        json.dumps({"pwsh": {"status": [], "version": "", "cleanup_confirmed": True}}),
        json.dumps(
            {"pwsh": {"status": "unavailable", "version": "7.6.6", "cleanup_confirmed": True}}
        ),
        pytest.param("x" * 32769, id="output_too_large"),
    ],
)
def test_malformed_bridge_output_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str
) -> None:
    monkeypatch.setattr(
        subject.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, output, "")
    )
    with pytest.raises(ValueError):
        subject._probe({"pwsh": tmp_path / "pwsh.exe"})


@pytest.mark.parametrize(("code", "stderr"), [(1, ""), (0, "private warning")])
def test_bridge_error_is_not_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int, stderr: str
) -> None:
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, code, "{}", stderr),
    )
    with pytest.raises(ValueError, match="VERSION_PROBE_FAILED"):
        subject._probe({"pwsh": tmp_path / "pwsh.exe"})


def test_cli_default_is_json_failure_without_search(capsys: pytest.CaptureFixture[str]) -> None:
    assert subject.main([]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "INPUT_INVALID"


@pytest.mark.skipif(os.name != "nt", reason="Windows native version collector")
def test_live_windows_empty_path_and_missing_pwsh(tmp_path: Path) -> None:
    pwsh = os.environ.get("RUNNER_INSPECTION_PWSH") or shutil.which("pwsh")
    git = shutil.which("git")
    assert pwsh and git, "Live Windows test requires installed Git and PowerShell 7"
    directories = list(
        dict.fromkeys(str(Path(path).parent) for path in [sys.executable, git, pwsh])
    )
    environment = {"PATH": "", "SystemRoot": os.environ["SystemRoot"]}
    base = [sys.executable, str(SCRIPT)]
    complete = [item for directory in directories for item in ["--trusted-directory", directory]]
    result = subprocess.run(
        [*base, *complete],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=55,
        check=False,
    )
    assert not result.stderr, result.stderr
    report = json.loads(result.stdout)
    assert result.returncode == 0, report
    assert all(tool["status"] == "observed" for tool in report["tools"])
    assert all(tool["cleanup_confirmed"] for tool in report["tools"])
    without_pwsh = [
        item
        for directory in directories
        if directory != str(Path(pwsh).parent)
        for item in ["--trusted-directory", directory]
    ]
    missing = subprocess.run(
        [*base, *without_pwsh],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )
    assert missing.returncode == 1
    assert "PWSH_MISSING" in json.loads(missing.stdout)["reason_codes"]
    assert list(tmp_path.iterdir()) == []
