"""Discover fixed tools in operator-selected directories without consulting PATH."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from pathlib import Path, PureWindowsPath
from typing import Any

NAMES = ("python", "git", "pwsh")
WINDOWS = os.name == "nt"
VERSION = re.compile(r"\d+\.\d+\.\d+(?:\.windows\.\d+)?", re.ASCII)
BRIDGE = Path(__file__).with_name("probe_versions.ps1")


def _drive_type(root: str) -> int:
    """Query a drive root's type without opening or enumerating the path."""
    import ctypes

    function = ctypes.WinDLL("kernel32", use_last_error=True).GetDriveTypeW
    function.argtypes = [ctypes.c_wchar_p]
    function.restype = ctypes.c_uint
    return int(function(root))


def _windows_directory_is_local(value: str) -> bool:
    # Parse first: metadata access to UNC/device paths can contact remote hosts.
    path = PureWindowsPath(value)
    if re.fullmatch(r"[A-Za-z]:", path.drive) is None or path.root != "\\":
        return False
    try:
        return _drive_type(path.anchor) in {2, 3, 5, 6}
    except (AttributeError, OSError):
        return False


def _plain_path(path: Path, *, directory: bool) -> bool:
    """Reject links/reparse points at every component, including trusted roots."""
    metadata = path.lstat()
    if directory != stat.S_ISDIR(metadata.st_mode):
        return False
    if not directory and not stat.S_ISREG(metadata.st_mode):
        return False
    for current in (path, *path.parents):
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            return False
    return True


def _directories(values: list[str]) -> list[Path]:
    if not values or len(values) > 16:
        raise ValueError("INVALID_TRUSTED_DIRECTORIES")
    result: list[Path] = []
    for value in values:
        if WINDOWS and not _windows_directory_is_local(value):
            raise ValueError("INVALID_TRUSTED_DIRECTORIES")
        path = Path(value)
        if not path.is_absolute() or ".." in path.parts or not _plain_path(path, directory=True):
            raise ValueError("INVALID_TRUSTED_DIRECTORIES")
        if path in result:
            raise ValueError("DUPLICATE_TRUSTED_DIRECTORY")
        result.append(path)
    return result


def _expectations(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        name, separator, version = value.partition("=")
        if (
            not separator
            or name not in NAMES
            or name in result
            or VERSION.fullmatch(version) is None
        ):
            raise ValueError("INVALID_VERSION_EXPECTATION")
        result[name] = version
    return result


def _probe(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    """Reuse the runner observer's Windows Job Object probe; no custom argv."""
    pwsh = paths["pwsh"]
    environment = {
        "PATH": "",
        "PSModulePath": str(pwsh.parent / "Modules"),
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
    }
    if os.environ.get("SystemRoot"):
        environment["SystemRoot"] = os.environ["SystemRoot"]
    process = subprocess.run(
        [str(pwsh), "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(BRIDGE)],
        input=json.dumps({name: str(path) for name, path in paths.items()}),
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=environment,
        cwd=pwsh.parent,
        timeout=45,
        check=False,
        shell=False,
    )
    if process.returncode or process.stderr or len(process.stdout) > 32768:
        raise ValueError("VERSION_PROBE_FAILED")
    data = json.loads(process.stdout)
    if not isinstance(data, dict) or set(data) != set(paths):
        raise ValueError("VERSION_PROBE_INVALID")
    for value in data.values():
        if (
            not isinstance(value, dict)
            or set(value) != {"status", "version", "cleanup_confirmed"}
            or not isinstance(value["status"], str)
            or value["status"] not in {"observed", "unavailable", "invalid_output"}
            or type(value["cleanup_confirmed"]) is not bool
            or not isinstance(value["version"], str)
            or (
                value["status"] == "observed"
                and (not value["cleanup_confirmed"] or VERSION.fullmatch(value["version"]) is None)
            )
            or (value["status"] != "observed" and value["version"] != "")
        ):
            raise ValueError("VERSION_PROBE_INVALID")
    return data


def discover(
    trusted_directories: list[str],
    expectations: list[str] | None = None,
    *,
    include_private_details: bool = False,
) -> dict[str, Any]:
    """Observe versions, never assert runner readiness or change process PATH."""
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "NOT_READY",
        "exit_code": 1,
        "proof_scope": "tool_discovery_and_versions_only",
        "search_source": "explicit_operator_directories",
        "ambient_path_used": False,
        "runner_ready": False,
        "gate_pass": False,
        "tools": [{"name": name, "status": "not_checked"} for name in NAMES],
        "reason_codes": [],
    }
    try:
        directories = _directories(trusted_directories)
        expected = _expectations(expectations or [])
    except (OSError, ValueError):
        report.update(status="INPUT_INVALID", exit_code=2, reason_codes=["INVALID_INPUT"])
        return report
    found: dict[str, Path] = {}
    for tool in report["tools"]:
        name = tool["name"]
        candidates = []
        unsafe = False
        for directory in directories:
            path = directory / (name + (".exe" if WINDOWS else ""))
            try:
                if _plain_path(path, directory=False):
                    candidates.append(path)
                else:
                    unsafe = True
            except FileNotFoundError:
                continue
            except OSError:
                unsafe = True
        if unsafe:
            tool["status"] = "unsafe_or_unreadable"
        elif len(candidates) > 1:
            tool["status"] = "ambiguous"
        elif not candidates:
            tool["status"] = "missing"
        else:
            tool["status"] = "located"
            found[name] = candidates[0]
            if include_private_details:
                tool["path"] = str(candidates[0])
        if name in expected:
            tool["expected_version"] = expected[name]
    if not WINDOWS:
        report["reason_codes"].append("LIVE_VERSION_PROBE_WINDOWS_ONLY")
    elif "pwsh" not in found:
        report["reason_codes"].append("TRUSTED_PWSH_REQUIRED_FOR_VERSION_PROBE")
    else:
        try:
            observations = _probe(found)
            for tool in report["tools"]:
                if tool["name"] in observations:
                    tool.update(observations[tool["name"]])
                    if (
                        tool["status"] == "observed"
                        and tool["name"] in expected
                        and tool["version"] != expected[tool["name"]]
                    ):
                        tool["status"] = "version_mismatch"
        except (OSError, ValueError, subprocess.TimeoutExpired):
            report["reason_codes"].append("VERSION_PROBE_FAILED")
    for tool in report["tools"]:
        if tool["status"] != "observed":
            report["reason_codes"].append(f"{tool['name'].upper()}_{tool['status'].upper()}")
    if not report["reason_codes"]:
        report.update(status="TOOLS_OBSERVED", exit_code=0)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-directory", action="append", default=[])
    parser.add_argument("--expect", action="append", default=[], metavar="NAME=VERSION")
    parser.add_argument("--include-private-details", action="store_true")
    args = parser.parse_args(argv)
    report = discover(
        args.trusted_directory, args.expect, include_private_details=args.include_private_details
    )
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
