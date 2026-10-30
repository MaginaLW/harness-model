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
import tempfile
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


def _base_environment(home: Path) -> dict[str, str]:
    env = {"HOME": str(home), "USERPROFILE": str(home), "PATH": "/usr/bin:/bin"}
    if os.name == "nt":
        system_root = Path(os.environ["SYSTEMROOT"])
        system_directory = system_root / "System32"
        if not system_root.is_absolute() or not system_directory.is_dir():
            raise RuntimeError("Windows system directory is unavailable")
        env["SYSTEMROOT"] = str(system_root)
        env["PATH"] = str(system_directory)
    return env


def _checkout_environment(temp_root: Path) -> tuple[str, dict[str, str]]:
    program = shutil.which("git")
    if program is None:
        raise RuntimeError("Git is unavailable")
    git = Path(program).resolve()
    if (
        not git.is_file()
        or git.is_relative_to(ROOT.resolve())
        or (os.name == "nt" and git.suffix.lower() != ".exe")
    ):
        raise RuntimeError("Git executable is unavailable or inside the checkout")
    home = Path(tempfile.mkdtemp(prefix="aiflow-git-", dir=temp_root))
    hooks = home / "empty-hooks"
    hooks.mkdir()
    env = _base_environment(home)
    env["PATH"] = os.pathsep.join((str(git.parent), env["PATH"]))
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "core.hooksPath",
            "GIT_CONFIG_VALUE_1": str(hooks),
        }
    )
    return str(git), env


def _installed_environment(target: Path, checkout_env: dict[str, str]) -> dict[str, str]:
    env = checkout_env.copy()
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_CONFIG_FILE"] = os.devnull
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(target)
    return env


def _install_clean_clone(clone: Path, installed: Path) -> None:
    if importlib.util.find_spec("pip") is not None:
        interpreter = sys.executable
    else:
        base_executable = getattr(sys, "_base_executable", None)
        assert base_executable is not None, "the active Python has no pip or base interpreter"
        base_interpreter = Path(base_executable)
        assert base_interpreter.is_file(), (
            "the active Python has no pip and its base interpreter is unavailable"
        )
        interpreter = str(base_interpreter)
    argv = [
        interpreter,
        "-I",
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-deps",
        "--index-url",
        "https://pypi.org/simple",
        "--target",
        str(installed),
        str(clone),
    ]
    parent = Path(tempfile.gettempdir()).resolve(strict=True)
    pytest_tree = installed.parent.parent.resolve()
    checkout = ROOT.resolve()
    if parent.is_relative_to(pytest_tree) or parent.is_relative_to(checkout):
        raise RuntimeError("pip temporary root is inside the checkout or pytest tree")
    temporary = Path(tempfile.mkdtemp(prefix="aiflow-pip-", dir=parent))
    try:
        root = temporary.resolve(strict=True)
        if (
            root.parent != parent
            or root.is_relative_to(pytest_tree)
            or root.is_relative_to(checkout)
        ):
            raise RuntimeError("pip temporary directory is inside the checkout or pytest tree")
        home = root / "home"
        temp = root / "temp"
        home.mkdir()
        temp.mkdir()
        env = _base_environment(home)
        env.update(
            {
                "NETRC": str(home / ".netrc"),
                "TMP": str(temp),
                "TEMP": str(temp),
                "TMPDIR": str(temp),
                "PIP_CONFIG_FILE": os.devnull,
                "PIP_KEYRING_PROVIDER": "disabled",
                "PIP_NO_INPUT": "1",
                "PIP_INDEX_URL": "https://pypi.org/simple",
                "PIP_NO_CACHE_DIR": "1",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "NO_PROXY": "*",
                "no_proxy": "*",
            }
        )
        if "PIP_NO_INDEX" in os.environ:
            env["PIP_NO_INDEX"] = os.environ["PIP_NO_INDEX"]
        _run(argv, cwd=clone, env=env)
    except BaseException as error:
        error.add_note(f"pip temp candidate; check interpreter temp root: {temporary.name}")
        raise


def test_checkout_git_environment_disables_inherited_fsmonitor_and_hooks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    git = shutil.which("git")
    assert git is not None
    git = str(Path(git).resolve())
    repo = tmp_path / "repo"
    repo.mkdir()
    git_env = {
        "PATH": str(Path(git).parent),
        "HOME": str(tmp_path),
        "USERPROFILE": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    if os.name == "nt":
        git_env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    _run([git, "init", "-q"], cwd=repo, env=git_env)
    (repo / "tracked.txt").write_text("synthetic\n", encoding="utf-8")
    _run([git, "add", "tracked.txt"], cwd=repo, env=git_env)
    marker = tmp_path / "fsmonitor-fired"
    hook = tmp_path / "fsmonitor.sh"
    hook.write_text(
        f"#!/bin/sh\nprintf fired > {shlex.quote(marker.as_posix())}\n", encoding="utf-8"
    )
    hook.chmod(0o700)
    unsafe_env = git_env | {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": shlex.quote(hook.as_posix()),
    }
    _run([git, "status", "--porcelain"], cwd=repo, env=unsafe_env)
    assert marker.is_file(), "the synthetic fsmonitor did not run"
    marker.unlink()
    private_keys = (
        "GIT_ASKPASS",
        "PIP_INDEX_URL",
        "HTTPS_PROXY",
        "AWS_SECRET_ACCESS_KEY",
        "PYTHONPATH",
    )
    for key in private_keys:
        monkeypatch.setenv(key, "synthetic-private-value")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", shlex.quote(hook.as_posix()))
    monkeypatch.setattr(shutil, "which", lambda name: git if name == "git" else None)
    monkeypatch.setenv("PATH", str(tmp_path))
    git_path, clean_env = _checkout_environment(tmp_path)
    assert Path(git_path).is_absolute()
    assert clean_env["GIT_CONFIG_NOSYSTEM"] == "1" and clean_env["GIT_CONFIG_GLOBAL"] == os.devnull
    assert clean_env["GIT_CONFIG_KEY_0"] == "core.fsmonitor"
    assert clean_env["GIT_CONFIG_VALUE_0"] == "false"
    assert clean_env["GIT_CONFIG_KEY_1"] == "core.hooksPath"
    assert Path(clean_env["GIT_CONFIG_VALUE_1"]).is_dir()
    assert all(key not in clean_env for key in private_keys)
    assert str(tmp_path) not in clean_env["PATH"]
    assert _installed_environment(tmp_path / "installed", clean_env)["PYTHONPATH"] == str(
        tmp_path / "installed"
    )
    _run(
        [git_path, "status", "--porcelain"],
        cwd=repo,
        env=_installed_environment(tmp_path, clean_env),
    )
    assert not marker.exists(), "an inherited fsmonitor executed"
    commit_marker = tmp_path / "hook-fired"
    commit_hook = repo / ".git/hooks/pre-commit"
    commit_hook.write_text(
        f"#!/bin/sh\nprintf fired > {shlex.quote(commit_marker.as_posix())}\n", encoding="utf-8"
    )
    commit_hook.chmod(0o700)
    _run(
        [
            git_path,
            "-c",
            "user.name=synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-qm",
            "synthetic",
        ],
        cwd=repo,
        env=_installed_environment(tmp_path, clean_env),
    )
    assert not commit_marker.exists(), "a repository hook executed"


def test_clean_clone_pip_does_not_inherit_private_configuration_or_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    private_home = tmp_path / "private-home"
    private_home.mkdir()
    (private_home / ".netrc").write_text(
        "machine pypi.org login synthetic password synthetic\n", encoding="utf-8"
    )
    if os.name != "nt":
        (private_home / ".netrc").chmod(0o600)
    private_environment = {
        "HOME": str(private_home),
        "USERPROFILE": str(private_home),
        "NETRC": str(private_home / ".netrc"),
        "PIP_INDEX_URL": "https://private.invalid/simple",
        "PIP_EXTRA_INDEX_URL": "https://extra.invalid/simple",
        "PIP_KEYRING_PROVIDER": "subprocess",
        "PIP_CONFIG_FILE": str(private_home / "pip.conf"),
        "UV_INDEX_URL": "https://private.invalid/simple",
        "HTTPS_PROXY": "http://proxy.invalid:1234",
        "http_proxy": "http://proxy.invalid:1234",
        "PYTHONPATH": str(private_home),
        "PATH": str(private_home),
    }
    homes: list[Path] = []

    def fake_run(
        argv: list[str], *, cwd: Path, env: dict[str, str] | None = None, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        assert env is not None
        home = Path(env["HOME"])
        homes.append(home)
        assert home != private_home and home.is_dir() and not list(home.iterdir())
        assert env["USERPROFILE"] == str(home) and env["NETRC"] == str(home / ".netrc")
        assert not Path(env["NETRC"]).exists()
        assert env["PIP_INDEX_URL"] == "https://pypi.org/simple"
        assert "PIP_EXTRA_INDEX_URL" not in env
        assert argv[argv.index("--index-url") + 1] == "https://pypi.org/simple"
        assert env["PIP_CONFIG_FILE"] == os.devnull
        assert env["NO_PROXY"] == env["no_proxy"] == "*"
        assert all(key.upper() not in {"HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"} for key in env)
        assert env["PIP_KEYRING_PROVIDER"] == "disabled" and env["PIP_NO_INPUT"] == "1"
        assert "PYTHONPATH" not in env and not any(key.upper().startswith("UV_") for key in env)
        assert str(private_home) not in env["PATH"]
        assert all(Path(part).is_absolute() for part in env["PATH"].split(os.pathsep))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setitem(globals(), "_run", fake_run)
    for key, value in private_environment.items():
        monkeypatch.setenv(key, value)
    _install_clean_clone(tmp_path / "checkout", tmp_path / "installed")
    assert len(homes) == 1 and homes[0].is_dir()
    assert (private_home / ".netrc").read_text(encoding="utf-8").endswith("synthetic\n")


@pytest.mark.parametrize("no_index", [None, "1", "false"])
def test_clean_clone_pip_preserves_only_explicit_no_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, no_index: str | None
) -> None:
    if no_index is None:
        monkeypatch.delenv("PIP_NO_INDEX", raising=False)
    else:
        monkeypatch.setenv("PIP_NO_INDEX", no_index)
    monkeypatch.setenv("PIP_EXTRA_INDEX_URL", "https://private.invalid/simple")
    monkeypatch.setenv("HTTPS_PROXY", "http://private.invalid:1234")

    def fake_run(
        argv: list[str], *, cwd: Path, env: dict[str, str] | None = None, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        assert env is not None
        assert env.get("PIP_NO_INDEX") == no_index
        assert "PIP_EXTRA_INDEX_URL" not in env and "HTTPS_PROXY" not in env
        assert env["PIP_INDEX_URL"] == "https://pypi.org/simple"
        assert argv[argv.index("--index-url") + 1] == "https://pypi.org/simple"
        # Both commands are read-only config inspection; neither installs or accesses an index.
        child = (
            "import subprocess,sys; r=subprocess.run([sys.executable,'-I','-m','pip',"
            "'config','list'],capture_output=True,text=True,check=True); print(r.stdout)"
        )
        for command in (
            [argv[0], "-I", "-m", "pip", "config", "list"],
            [argv[0], "-I", "-c", child],
        ):
            result = subprocess.run(
                command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30
            )
            assert result.returncode == 0, result.stderr
            assert (":env:.no-index=" in result.stdout) == (no_index is not None)
            if no_index is not None:
                assert f":env:.no-index='{no_index}'" in result.stdout
            assert "private.invalid" not in result.stdout
        # Parse the install options without running the resolver or making a request.
        parse_options = (
            "from pip._internal.commands import create_command; "
            "options,_=create_command('install').parse_args("
            "['--index-url','https://pypi.org/simple']); print(bool(options.no_index))"
        )
        result = subprocess.run(
            [argv[0], "-I", "-c", parse_options],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == str(no_index == "1")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setitem(globals(), "_run", fake_run)
    _install_clean_clone(tmp_path / "checkout", tmp_path / "installed")


def test_clean_clone_pip_ignores_system_proxy_and_synthetic_netrc(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    private_home = tmp_path / "private-home"
    private_home.mkdir()
    netrc = private_home / ".netrc"
    netrc.write_text("machine pypi.org login synthetic password synthetic\n", encoding="utf-8")
    if os.name != "nt":
        netrc.chmod(0o600)
    for key in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(key, str(private_home))

    def fake_run(
        argv: list[str], *, cwd: Path, env: dict[str, str] | None = None, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        code = (
            "import subprocess, sys; import pip._vendor.requests.utils as u; "
            "u.getproxies = lambda: {'https': 'http://system-proxy.invalid:1234'}; "
            "assert u.get_netrc_auth('https://pypi.org/simple') is None; "
            "assert u.get_environ_proxies('https://pypi.org/simple') == {}; "
            "c = subprocess.run([sys.executable, '-I', '-m', 'pip', 'config', 'list'], "
            "capture_output=True, text=True, timeout=30); "
            "assert c.returncode == 0; "
            "assert 'https://pypi.org/simple' in c.stdout; "
            "assert 'keyring-provider' in c.stdout and 'disabled' in c.stdout; "
            "assert 'no-input' in c.stdout and 'no-cache-dir' in c.stdout; "
            "assert 'private.invalid' not in c.stdout"
        )
        result = subprocess.run(
            [argv[0], "-I", "-c", code],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setitem(globals(), "_run", fake_run)
    _install_clean_clone(tmp_path / "checkout", tmp_path / "installed")


@pytest.mark.parametrize("timed_out", [False, True])
def test_clean_clone_pip_failure_propagates_and_preserves_its_temporary_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, timed_out: bool
) -> None:
    homes: list[Path] = []

    def fake_run(
        argv: list[str], *, cwd: Path, env: dict[str, str] | None = None, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        assert env is not None
        homes.append(Path(env["HOME"]))
        if timed_out:
            raise subprocess.TimeoutExpired(argv, 1)
        raise RuntimeError("synthetic pip failure")

    monkeypatch.setitem(globals(), "_run", fake_run)
    expected_error = subprocess.TimeoutExpired if timed_out else RuntimeError
    with pytest.raises(expected_error) as failure:
        _install_clean_clone(tmp_path / "checkout", tmp_path / "installed")
    assert len(homes) == 1 and homes[0].is_dir()
    root = homes[0].parent
    assert (Path(tempfile.gettempdir()) / root.name).resolve() == root
    assert failure.value.__notes__ == [
        f"pip temp candidate; check interpreter temp root: {root.name}"
    ]
    assert str(root) not in failure.value.__notes__[0]


@pytest.mark.parametrize("location", ["checkout", "pytest"])
def test_clean_clone_rejects_forbidden_temporary_parent_before_creating(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, location: str
) -> None:
    forbidden = ROOT if location == "checkout" else tmp_path.parent
    monkeypatch.setattr(tempfile, "tempdir", str(forbidden))
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(forbidden))
    monkeypatch.setattr(
        tempfile, "mkdtemp", lambda *args, **kwargs: pytest.fail("must not create a directory")
    )
    with pytest.raises(RuntimeError, match="temporary root is inside") as failure:
        _install_clean_clone(tmp_path / "checkout", tmp_path / "installed")
    assert not getattr(failure.value, "__notes__", ())


def test_clean_clone_rechecks_temporary_directory_after_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent = tmp_path.parent.parent.resolve()
    changed = tmp_path / "changed-location"
    changed.mkdir()
    marker = changed / "preserve"
    marker.write_bytes(b"unchanged")
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(parent))

    def displaced(*, prefix: str, dir: Path) -> str:
        assert prefix == "aiflow-pip-" and dir == parent
        return str(changed)

    monkeypatch.setattr(tempfile, "mkdtemp", displaced)
    with pytest.raises(RuntimeError, match="temporary directory is inside") as failure:
        _install_clean_clone(tmp_path / "checkout", tmp_path / "installed")
    assert marker.read_bytes() == b"unchanged"
    assert failure.value.__notes__ == [
        "pip temp candidate; check interpreter temp root: changed-location"
    ]


@pytest.mark.skipif(os.name != "nt", reason="Windows system directory check")
@pytest.mark.parametrize("relative", [True, False])
def test_clean_clone_rejects_invalid_windows_system_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, relative: bool
) -> None:
    value = "relative-system-root" if relative else str(tmp_path / "missing-system-root")
    monkeypatch.setenv("SYSTEMROOT", value)

    def fake_run(*args: object, **kwargs: object) -> None:
        pytest.fail("pip must not run with an invalid system directory")

    monkeypatch.setitem(globals(), "_run", fake_run)
    with pytest.raises(RuntimeError, match="Windows system directory is unavailable"):
        _install_clean_clone(tmp_path / "checkout", tmp_path / "installed")


@pytest.mark.parametrize("active_has_pip", [False, True])
def test_clean_clone_selects_pip_interpreter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, active_has_pip: bool
) -> None:
    base_interpreter = Path(getattr(sys, "_base_executable", sys.executable))
    assert base_interpreter.is_file()
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(
        importlib.util, "find_spec", lambda name: object() if active_has_pip else None
    )
    monkeypatch.setattr(sys, "_base_executable", str(base_interpreter), raising=False)
    monkeypatch.setitem(globals(), "_run", fake_run)

    clone = tmp_path / "checkout"
    installed = tmp_path / "installed"
    _install_clean_clone(clone, installed)

    assert calls == [
        [
            sys.executable if active_has_pip else str(base_interpreter),
            "-I",
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--index-url",
            "https://pypi.org/simple",
            "--target",
            str(installed),
            str(clone),
        ]
    ]


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
    git, checkout_env = _checkout_environment(tmp_path)
    _run(
        [git, "clone", "--local", "--no-hardlinks", str(ROOT), str(clone)],
        cwd=tmp_path,
        env=checkout_env,
    )
    source_head = _run([git, "rev-parse", "HEAD"], cwd=ROOT, env=checkout_env).stdout.strip()
    assert (
        _run([git, "rev-parse", "HEAD"], cwd=clone, env=checkout_env).stdout.strip() == source_head
    )
    _run([git, "checkout", "-B", "clean-checkout", source_head], cwd=clone, env=checkout_env)
    assert (
        _run([git, "symbolic-ref", "--short", "HEAD"], cwd=clone, env=checkout_env).stdout.strip()
        == "clean-checkout"
    )
    assert _run([git, "status", "--porcelain"], cwd=clone, env=checkout_env).stdout == ""
    source_tracked = _run([git, "ls-files"], cwd=ROOT, env=checkout_env).stdout.splitlines()
    clone_tracked = _run([git, "ls-files"], cwd=clone, env=checkout_env).stdout.splitlines()
    assert clone_tracked == source_tracked
    assert (
        _run(
            [git, "ls-files", "--others", "--exclude-standard"], cwd=clone, env=checkout_env
        ).stdout
        == ""
    )

    _install_clean_clone(clone, installed)
    env = _installed_environment(installed, checkout_env)

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
    assert _run([git, "status", "--porcelain"], cwd=clone, env=checkout_env).stdout.startswith(
        "?? .ai/tasks/"
    )
