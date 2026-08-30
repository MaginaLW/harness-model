"""Clean-checkout installation and operations-document verification."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
QUICKSTART = ROOT / "docs/operations/quickstart.md"
RECOVERY = ROOT / "docs/operations/recovery.md"
VERIFY_COMMAND = re.compile(r"<!-- verify-command: (.+?) -->")
REQUIRED_PATH = re.compile(r"<!-- required-path: (.+?) -->")
TASK_ID = re.compile(r"TASK-[0-9]{4,}")
RECOVERY_IDS = {f"REC-{index:02d}" for index in range(1, 9)}


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert result.returncode == expected, (argv, result.stdout, result.stderr)
    return result


def _installed_environment(target: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_CONFIG_FILE"] = os.devnull
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(target)
    return env


def _install_clean_clone(clone: Path, installed: Path, install_env: dict[str, str]) -> None:
    if importlib.util.find_spec("pip") is not None:
        argv = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--target",
            str(installed),
            str(clone),
        ]
    else:
        uv = shutil.which("uv")
        assert uv is not None, "the active Python has no pip and uv is unavailable"
        argv = [
            uv,
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--target",
            str(installed),
            "--python",
            sys.executable,
            str(clone),
        ]
    _run(argv, cwd=clone, env=install_env)


def test_quickstart_marked_commands_and_paths_are_executable() -> None:
    content = QUICKSTART.read_text(encoding="utf-8")
    commands = VERIFY_COMMAND.findall(content)
    assert commands == [
        "python -m aiflow --help",
        "python -m pytest tests/unit/test_specification.py -q",
    ]
    paths = REQUIRED_PATH.findall(content)
    assert paths and all((ROOT / path).is_file() for path in paths)


def test_recovery_manual_covers_all_required_failures() -> None:
    content = RECOVERY.read_text(encoding="utf-8")
    headings = set(re.findall(r"^## (REC-[0-9]{2}) ", content, re.MULTILINE))
    assert headings == RECOVERY_IDS
    for identifier in sorted(RECOVERY_IDS):
        section = content.split(f"## {identifier} ", 1)[1].split("\n## ", 1)[0]
        assert "- 诊断：" in section
        assert "- 可恢复操作：" in section
        assert "- 禁止操作：" in section


def test_clean_clone_installs_and_runs_documented_safe_subset(tmp_path: Path) -> None:
    clone = tmp_path / "checkout"
    installed = tmp_path / "installed"
    _run(
        ["git", "clone", "--local", "--no-hardlinks", str(ROOT), str(clone)],
        cwd=tmp_path,
    )
    source_head = _run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip()
    assert _run(["git", "rev-parse", "HEAD"], cwd=clone).stdout.strip() == source_head
    _run(["git", "checkout", "-B", "clean-checkout", source_head], cwd=clone)
    assert (
        _run(["git", "symbolic-ref", "--short", "HEAD"], cwd=clone).stdout.strip()
        == "clean-checkout"
    )
    assert _run(["git", "status", "--porcelain"], cwd=clone).stdout == ""
    source_tracked = _run(["git", "ls-files"], cwd=ROOT).stdout.splitlines()
    clone_tracked = _run(["git", "ls-files"], cwd=clone).stdout.splitlines()
    assert clone_tracked == source_tracked
    assert _run(["git", "ls-files", "--others", "--exclude-standard"], cwd=clone).stdout == ""

    install_env = os.environ.copy()
    install_env["PYTHONNOUSERSITE"] = "1"
    install_env["PIP_CONFIG_FILE"] = os.devnull
    _install_clean_clone(clone, installed, install_env)
    env = _installed_environment(installed)

    for command in VERIFY_COMMAND.findall(
        (clone / QUICKSTART.relative_to(ROOT)).read_text("utf-8")
    ):
        argv = shlex.split(command)
        argv[0] = sys.executable
        _run(argv, cwd=clone, env=env)

    started = _run(
        [
            sys.executable,
            "-m",
            "aiflow",
            "start",
            "--objective",
            "safe local quickstart example",
            "--allow",
            "docs/quickstart-demo.md",
            "--forbid-action",
            "push",
            "--forbid-action",
            "merge",
            "--forbid-action",
            "deploy",
            "--forbid-action",
            "delete",
        ],
        cwd=clone,
        env=env,
    )
    task_id = TASK_ID.search(started.stdout)
    assert task_id
    task_path = clone / ".ai/tasks" / task_id.group() / "task.yaml"
    task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
    unit = task["decision_units"][0]
    unit.update(
        {
            "scope": {"clear": True},
            "impact": {"level": "low"},
            "protections": {"verified_backup": True, "dry_run": True},
            "verification": {"automatic": True, "tools_missing": False},
            "impact_categories": ["documentation"],
            "business_direction_count": 1,
            "change_characteristics": {
                "mechanical": False,
                "behavior_changed": False,
                "code_modified": False,
                "interaction_scope": "local",
                "regression_risk": False,
                "error_detectability": "high",
            },
        }
    )
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")

    _run(
        [sys.executable, "-m", "aiflow", "classify", task_id.group(), "--actor", "quickstart"],
        cwd=clone,
        env=env,
    )
    status = _run(
        [sys.executable, "-m", "aiflow", "status", task_id.group(), "--format", "json"],
        cwd=clone,
        env=env,
    )
    assert json.loads(status.stdout)["route"] == "AUTO"
    gate = _run(
        [sys.executable, "-m", "aiflow", "gate", task_id.group(), "--format", "json"],
        cwd=clone,
        env=env,
        expected=2,
    )
    assert json.loads(gate.stdout)["passed"] is False
    assert _run(["git", "status", "--porcelain"], cwd=clone).stdout.startswith("?? .ai/tasks/")
