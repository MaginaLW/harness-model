"""Clean-checkout installation and operations-document verification."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from importlib.machinery import PathFinder
from pathlib import Path

import pytest
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


def _isolated_environment(root: Path) -> dict[str, str]:
    git = shutil.which("git")
    assert git is not None, "Git is required for the clean-checkout test"
    root.mkdir()
    for name in ("home", "config", "cache", "temp", "hooks", "template"):
        (root / name).mkdir()
    paths = [str(Path(git).resolve().parent)]
    env: dict[str, str] = {}
    if os.name == "nt":
        system_root = Path(os.environ["SYSTEMROOT"])
        assert system_root.is_absolute() and system_root.is_dir()
        env["SYSTEMROOT"] = str(system_root)
        paths.extend((str(system_root / "System32"), str(system_root)))
    else:
        paths.extend(os.defpath.split(os.pathsep))
    env.update(
        {
            "PATH": os.pathsep.join(paths),
            "HOME": str(root / "home"),
            "USERPROFILE": str(root / "home"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "APPDATA": str(root / "config"),
            "LOCALAPPDATA": str(root / "cache"),
            "NETRC": str(root / "home" / ".netrc"),
            "TMPDIR": str(root / "temp"),
            "TEMP": str(root / "temp"),
            "TMP": str(root / "temp"),
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_ALLOW_PROTOCOL": "file",
            "GIT_TEMPLATE_DIR": str(root / "template"),
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "core.hooksPath",
            "GIT_CONFIG_VALUE_1": str(root / "hooks"),
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_KEYRING_PROVIDER": "disabled",
            "PIP_NO_INPUT": "1",
            "PIP_NO_INDEX": "1",
            "PIP_NO_CACHE_DIR": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    return env


def _installed_environment(target: Path, environment: dict[str, str]) -> dict[str, str]:
    return environment | {"PYTHONPATH": str(target)}


def _clone_at_head(source: Path, clone: Path, env: dict[str, str]) -> str:
    source_head = _run(["git", "rev-parse", "HEAD"], cwd=source, env=env).stdout.strip()
    _run(
        [
            "git",
            "clone",
            "--no-local",
            "--single-branch",
            "--no-tags",
            "--no-checkout",
            str(source),
            str(clone),
        ],
        cwd=clone.parent,
        env=env,
    )
    assert _run(["git", "rev-parse", "HEAD"], cwd=clone, env=env).stdout.strip() == source_head
    _run(["git", "checkout", "-B", "clean-checkout", source_head], cwd=clone, env=env)
    return source_head


def _install_clean_clone(clone: Path, installed: Path, install_env: dict[str, str]) -> None:
    if PathFinder.find_spec("pip") is not None:
        interpreter = sys.executable
    else:
        base_executable = getattr(sys, "_base_executable", None)
        assert base_executable is not None, "the active Python has no pip or base interpreter"
        base_interpreter = Path(base_executable)
        assert base_interpreter.is_file(), (
            "the active Python has no pip and its base interpreter is unavailable"
        )
        interpreter = str(base_interpreter)
    wheelhouse = installed.parent / "wheelhouse"
    _run(
        [
            sys.executable,
            "-I",
            "-B",
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(wheelhouse),
            str(clone),
        ],
        cwd=installed.parent,
        env=install_env,
    )
    wheels = list(wheelhouse.glob("*.whl"))
    assert len(wheels) == 1, "the clean clone must produce exactly one wheel"
    _run(
        [
            interpreter,
            "-I",
            "-B",
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-index",
            "--no-deps",
            "--no-cache-dir",
            "--target",
            str(installed),
            str(wheels[0]),
        ],
        cwd=installed.parent,
        env=install_env,
    )


def test_clean_clone_uses_base_interpreter_when_active_has_no_pip(
    monkeypatch, tmp_path: Path
) -> None:
    base_interpreter = Path(sys.executable)
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if "build" in argv:
            wheelhouse = Path(argv[argv.index("--outdir") + 1])
            wheelhouse.mkdir()
            (wheelhouse / "aiflow-test.whl").touch()
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(PathFinder, "find_spec", lambda name: None)
    monkeypatch.setattr(sys, "_base_executable", str(base_interpreter), raising=False)
    monkeypatch.setitem(globals(), "_run", fake_run)

    clone = tmp_path / "checkout"
    installed = tmp_path / "installed"
    _install_clean_clone(clone, installed, {})

    assert len(calls) == 2
    assert calls[0][:5] == [sys.executable, "-I", "-B", "-m", "build"]
    assert calls[1] == [
        str(base_interpreter),
        "-I",
        "-B",
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-index",
        "--no-deps",
        "--no-cache-dir",
        "--target",
        str(installed),
        str(tmp_path / "wheelhouse" / "aiflow-test.whl"),
    ]


def test_clean_clone_pip_probe_does_not_query_meta_path(monkeypatch, tmp_path: Path) -> None:
    class RejectPipMetaFinder:
        def find_spec(self, fullname: str, path=None, target=None):
            if fullname == "pip":
                raise AssertionError(
                    "pip availability probing must not invoke global meta-path hooks"
                )
            return None

    calls: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if "build" in argv:
            wheelhouse = Path(argv[argv.index("--outdir") + 1])
            wheelhouse.mkdir()
            (wheelhouse / "aiflow-test.whl").touch()
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(sys, "meta_path", [RejectPipMetaFinder(), *sys.meta_path])
    monkeypatch.setitem(globals(), "_run", fake_run)

    _install_clean_clone(tmp_path / "checkout", tmp_path / "installed", {})

    assert len(calls) == 2
    assert calls[1][3:6] == ["-m", "pip", "install"]


@pytest.mark.parametrize("detached", [False, True])
def test_transport_clone_excludes_unrelated_private_refs_and_objects(
    tmp_path: Path, detached: bool
) -> None:
    env = _isolated_environment(tmp_path / "environment")
    source = tmp_path / "source"
    source.mkdir()
    _run(["git", "init", "-b", "public"], cwd=source, env=env)
    _run(["git", "config", "user.name", "synthetic"], cwd=source, env=env)
    _run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=source, env=env)
    (source / "public.txt").write_text("public\n", encoding="utf-8")
    _run(["git", "add", "."], cwd=source, env=env)
    _run(["git", "commit", "-qm", "public"], cwd=source, env=env)
    public_head = _run(["git", "rev-parse", "HEAD"], cwd=source, env=env).stdout.strip()
    _run(["git", "checkout", "-b", "private"], cwd=source, env=env)
    (source / "private.txt").write_text("synthetic private material\n", encoding="utf-8")
    _run(["git", "add", "."], cwd=source, env=env)
    _run(["git", "commit", "-qm", "private"], cwd=source, env=env)
    private_head = _run(["git", "rev-parse", "HEAD"], cwd=source, env=env).stdout.strip()
    private_blob = _run(
        ["git", "rev-parse", "HEAD:private.txt"], cwd=source, env=env
    ).stdout.strip()
    _run(["git", "tag", "private-tag"], cwd=source, env=env)
    checkout = (
        ["git", "checkout", "--detach", public_head] if detached else ["git", "checkout", "public"]
    )
    _run(checkout, cwd=source, env=env)

    clone = tmp_path / "clone"
    assert _clone_at_head(source, clone, env) == public_head
    assert (clone / "public.txt").read_text("utf-8") == "public\n"
    refs = _run(["git", "for-each-ref", "--format=%(refname)"], cwd=clone, env=env).stdout
    assert "private" not in refs
    for private_object in (private_head, private_blob):
        _run(["git", "cat-file", "-t", private_object], cwd=clone, env=env, expected=128)
    assert not (clone / ".git/objects/info/alternates").exists()


def test_clean_environment_ignores_inherited_configuration_and_controls_temp(
    monkeypatch, tmp_path: Path
) -> None:
    private = tmp_path / "private"
    private.mkdir()
    marker = private / "python-started"
    (private / "sitecustomize.py").write_text(
        f"from pathlib import Path; Path({str(marker)!r}).touch()\n", encoding="utf-8"
    )
    for name in (
        "PYTHONHOME",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "HTTPS_PROXY",
        "AWS_SECRET_ACCESS_KEY",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_ASKPASS",
    ):
        monkeypatch.setenv(name, "synthetic-private-value")
    monkeypatch.setenv("PYTHONPATH", str(private))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "synthetic-private-value")
    env = _isolated_environment(tmp_path / "environment")
    result = _run(
        [
            sys.executable,
            "-c",
            "import json, os, tempfile; "
            "print(json.dumps({'env': dict(os.environ), 'temp': tempfile.mkdtemp()}))",
        ],
        cwd=tmp_path,
        env=env,
    )
    facts = json.loads(result.stdout)
    assert "synthetic-private-value" not in facts["env"].values()
    assert "PYTHONPATH" not in facts["env"]
    assert Path(facts["temp"]).parent == Path(env["TEMP"])
    assert not marker.exists()

    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init"], cwd=repo, env=env)
    hook = repo / ".git/hooks/pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook_marker = tmp_path / "hook-executed"
    hook.write_text(
        f"#!/bin/sh\nprintf fired > {shlex.quote(hook_marker.as_posix())}\n", encoding="utf-8"
    )
    hook.chmod(0o700)
    _run(
        [
            "git",
            "-c",
            "user.name=synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "synthetic",
        ],
        cwd=repo,
        env=env,
    )
    assert not hook_marker.exists()
    _run(["git", "config", "core.fsmonitor", str(hook)], cwd=repo, env=env)
    _run(["git", "status", "--porcelain"], cwd=repo, env=env)
    assert not hook_marker.exists()
    _run(
        ["git", "-c", f"core.hooksPath={hook.parent}", "hook", "run", "pre-commit"],
        cwd=repo,
        env=env,
    )
    assert hook_marker.is_file(), "the synthetic hook must be executable for this regression"


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
    checkout_env = _isolated_environment(tmp_path / "environment")
    _clone_at_head(ROOT, clone, checkout_env)
    assert (
        _run(["git", "symbolic-ref", "--short", "HEAD"], cwd=clone, env=checkout_env).stdout.strip()
        == "clean-checkout"
    )
    assert _run(["git", "status", "--porcelain"], cwd=clone, env=checkout_env).stdout == ""
    source_tracked = _run(["git", "ls-files"], cwd=ROOT, env=checkout_env).stdout.splitlines()
    clone_tracked = _run(["git", "ls-files"], cwd=clone, env=checkout_env).stdout.splitlines()
    assert clone_tracked == source_tracked
    assert (
        _run(
            ["git", "ls-files", "--others", "--exclude-standard"], cwd=clone, env=checkout_env
        ).stdout
        == ""
    )

    _install_clean_clone(clone, installed, checkout_env)
    env = _installed_environment(installed, checkout_env)
    imported = _run(
        [sys.executable, "-c", "import aiflow; print(aiflow.__file__)"], cwd=clone, env=env
    )
    assert Path(imported.stdout.strip()).resolve().is_relative_to(installed.resolve())

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
            "controlled_actions": [],
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
    assert _run(["git", "status", "--porcelain"], cwd=clone, env=env).stdout.startswith(
        "?? .ai/tasks/"
    )
