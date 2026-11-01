"""CLI regression tests for approval recovery and invalid Policy inputs."""

from __future__ import annotations

# ruff: noqa: E402 -- Source-absence guard must precede candidate-only imports.
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# Baseline-only absence is not a functional pass; malformed or stale imports fail.
ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file() and (parent / "src/aiflow/__init__.py").is_file()
)
NODE_SOURCE = ROOT / "src/aiflow/node_verification.py"
try:
    NODE_SOURCE_INFO = NODE_SOURCE.lstat()
except FileNotFoundError:
    pytest.skip(
        "Node implementation is absent: test-preparation baseline only, not feature PASS",
        allow_module_level=True,
    )
if (
    not stat.S_ISREG(NODE_SOURCE_INFO.st_mode)
    or getattr(NODE_SOURCE_INFO, "st_file_attributes", 0)
    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    or not NODE_SOURCE.resolve().is_relative_to(ROOT.resolve())
):
    raise ImportError("Node source is not a regular checkout module")

import aiflow
import aiflow.node_verification as node_checkout

if (
    aiflow.__file__ is None
    or Path(aiflow.__file__).resolve() != (ROOT / "src/aiflow/__init__.py").resolve()
    or node_checkout.__file__ is None
    or Path(node_checkout.__file__).resolve() != NODE_SOURCE.resolve()
):
    raise ImportError("Node contracts were not imported from this tested checkout")

import test_approve_command as helpers
from test_begin_close_commands import _populate_repository

from aiflow import approval as approval_service
from aiflow.cli import main
from aiflow.contracts import schema_directory_context
from aiflow.errors import AiflowError, StorageError
from aiflow.storage import resolve_task_path
from aiflow.task_service import load_task_record

ARGUMENTS = [
    "approve",
    "TASK-0001",
    "--type",
    "spec",
    "--actor",
    "reviewer",
    "--reason",
    "direction approved",
]
SOURCE = ROOT / "src"


def _isolate_environment(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    git = shutil.which("git")
    if git is None:
        pytest.fail("Git is required for synthetic recovery tests")
    git_directory = Path(git).resolve(strict=True).parent
    root.mkdir()
    home = root / "home"
    hooks = root / "hooks"
    template = root / "template"
    python_probe = root / "python-probe"
    for directory in (home, hooks, template, python_probe):
        directory.mkdir()
    (python_probe / "sitecustomize.py").write_text(
        "import atexit, os, sys\n"
        "def _record_aiflow():\n"
        "    module = sys.modules.get('aiflow')\n"
        "    with open(os.environ['AIFLOW_TEST_MODULE_PATH'], 'x', encoding='utf-8') as output:\n"
        "        output.write(str(getattr(module, '__file__', '')))\n"
        "atexit.register(_record_aiflow)\n",
        encoding="utf-8",
    )
    git_config = home / "gitconfig"
    git_config.write_bytes(b"")
    for name in tuple(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name, raising=False)
    for name in ("PYTHONHOME", "PYTHONUSERBASE"):
        monkeypatch.delenv(name, raising=False)
    path = [str(git_directory)]
    if os.name == "nt":
        system_root = Path(os.environ["SystemRoot"]).resolve(strict=True)
        path.extend((str(system_root / "System32"), str(system_root)))
    else:
        path.extend(("/usr/bin", "/bin"))
    for key, value in {
        "PATH": os.pathsep.join(path),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "XDG_CONFIG_HOME": str(home),
        "GIT_CONFIG_GLOBAL": str(git_config),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_TEMPLATE_DIR": str(template),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": str(hooks),
        "GIT_CONFIG_KEY_1": "core.fsmonitor",
        "GIT_CONFIG_VALUE_1": "false",
        "PYTHONPATH": os.pathsep.join((str(python_probe), str(SOURCE))),
        "AIFLOW_TEST_MODULE_PATH": str(root / "cli-module-path.txt"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.fixture(autouse=True)
def _isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert aiflow.__file__ is not None
    assert Path(aiflow.__file__).resolve() == (SOURCE / "aiflow/__init__.py").resolve()
    _isolate_environment(tmp_path / "git-isolation", monkeypatch)


def test_synthetic_git_ignores_inherited_config_and_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    untrusted = tmp_path / "untrusted"
    untrusted.mkdir()
    template = untrusted / "template"
    (template / "hooks").mkdir(parents=True)
    (template / "hooks/pre-commit").write_text("synthetic hook", encoding="utf-8")
    config = untrusted / "gitconfig"
    config.write_text("[core]\n  fsmonitor = malicious-monitor\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(untrusted))
    monkeypatch.setenv("USERPROFILE", str(untrusted))
    monkeypatch.setenv("GIT_DIR", str(untrusted))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(config))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "malicious-monitor")
    monkeypatch.setenv("GIT_TEMPLATE_DIR", str(template))
    isolated = tmp_path / "rechecked-isolation"
    _isolate_environment(isolated, monkeypatch)
    assert "GIT_DIR" not in os.environ
    assert "GIT_CONFIG_SYSTEM" not in os.environ
    assert os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
    assert Path(os.environ["GIT_CONFIG_GLOBAL"]) == isolated / "home/gitconfig"
    assert Path(os.environ["GIT_TEMPLATE_DIR"]) == isolated / "template"
    assert os.environ["GIT_CONFIG_VALUE_1"] == "false"
    assert all(Path(part).is_absolute() for part in os.environ["PATH"].split(os.pathsep))
    repository = tmp_path / "synthetic-git"
    repository.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repository, check=True, capture_output=True)
    assert not (repository / ".git/hooks/pre-commit").exists()
    result = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert Path(result.stdout.strip()).resolve() == (isolated / "hooks").resolve()


def _prepare_real_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    def create_repository(path: Path) -> Path:
        path.mkdir()
        return _populate_repository(path)

    monkeypatch.setattr(helpers, "create_repository", create_repository)
    repository = helpers._prepare(tmp_path, monkeypatch, state="WAITING_FOR_SPEC_REVIEW")
    helpers._record_review(repository, tmp_path, stage="design", review_id="REV-0004")
    return repository


def _pending_approval(repository: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    def fail_once(*args: object, **kwargs: object) -> None:
        raise StorageError("injected", code="STORAGE_WRITE_FAILED")

    with monkeypatch.context() as patch:
        patch.setattr(approval_service, "_persist_event_and_task", fail_once)
        assert main(ARGUMENTS) == 1
    marker = resolve_task_path(repository, "TASK-0001", "approval_pending.json")
    assert marker.is_file()
    assert resolve_task_path(repository, "TASK-0001", "approvals.json").is_file()
    return marker


def _run_cli(repository: Path) -> subprocess.CompletedProcess[str]:
    probe = Path(os.environ["AIFLOW_TEST_MODULE_PATH"])
    assert not probe.exists()
    result = subprocess.run(
        [sys.executable, "-B", "-m", "aiflow", *ARGUMENTS],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert (
        Path(probe.read_text(encoding="utf-8")).resolve()
        == (SOURCE / "aiflow/__init__.py").resolve()
    )
    return result


def _assert_error_code(repository: Path, code: str) -> None:
    # The approve CLI displays the message, not the structured error code.
    with schema_directory_context(repository / ".ai" / "schemas"):
        with pytest.raises(AiflowError) as caught:
            approval_service.approve_task(
                repository,
                "TASK-0001",
                approval_type="spec",
                actor="reviewer",
                reason="direction approved",
            )
    assert caught.value.code == code


def _snapshot(root: Path) -> dict[str, tuple[str, bytes | str]]:
    result: dict[str, tuple[str, bytes | str]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("symlink", os.readlink(path))
        elif path.is_dir():
            result[relative] = ("directory", "")
        else:
            result[relative] = ("file", path.read_bytes())
    return result


def _state(repository: Path) -> tuple[dict[str, tuple[str, bytes | str]], ...]:
    return (
        _snapshot(repository / ".ai" / "tasks" / "TASK-0001"),
        _snapshot(repository / ".ai" / "policy"),
    )


def test_valid_python_policy_recovers_real_pending_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare_real_repository(tmp_path, monkeypatch)
    marker = _pending_approval(repository, monkeypatch)
    result = _run_cli(repository)
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "READY_TO_IMPLEMENT"
    assert [event["event_type"] for event in record.events].count("spec_approved") == 1


@pytest.mark.parametrize("variant", ["missing", "corrupt", "unsupported", "unshipped30"])
def test_invalid_policy_blocks_pending_recovery_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    repository = _prepare_real_repository(tmp_path, monkeypatch)
    _pending_approval(repository, monkeypatch)
    policy = repository / ".ai" / "policy"
    if variant == "missing":
        (policy / "routing.yaml").unlink()
    elif variant == "corrupt":
        (policy / "routing.yaml").write_bytes(b"[invalid policy\n")
    else:
        for path in sorted(policy.glob("*.yaml")):
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            document["policy_version"] = "3.0.0" if variant == "unshipped30" else "9.0.0"
            path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding="utf-8")
    before = _state(repository)
    expected_code = {
        "missing": "POLICY_FILE_MISSING",
        "corrupt": "POLICY_READ_FAILED",
        "unsupported": "POLICY_LEVEL_INVALID",
        "unshipped30": "POLICY_LEVEL_INVALID",
    }[variant]
    _assert_error_code(repository, expected_code)
    assert _state(repository) == before
    result = _run_cli(repository)
    assert result.returncode == 1, result.stdout
    expected_error = {
        "missing": "Required Policy file is missing",
        "corrupt": "Could not read or parse Policy file",
        "unsupported": "Policy version is unsupported",
        "unshipped30": "Policy version is unsupported",
    }[variant]
    assert expected_error in result.stderr
    assert _state(repository) == before


@pytest.mark.parametrize("kind", ["directory", "dangling_symlink"])
def test_nonregular_marker_is_rejected_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    repository = _prepare_real_repository(tmp_path, monkeypatch)
    marker = resolve_task_path(repository, "TASK-0001") / "approval_pending.json"
    if kind == "directory":
        marker.mkdir()
    else:
        try:
            marker.symlink_to("missing-marker-target")
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"file symlink creation is unavailable: {error}")
        assert marker.is_symlink() and not marker.exists()
    before = _state(repository)
    _assert_error_code(repository, "APPROVAL_RECOVERY_INVALID")
    assert _state(repository) == before
    result = _run_cli(repository)
    assert result.returncode == 1, result.stdout
    assert "Approval recovery marker is not a regular file" in result.stderr
    assert _state(repository) == before
