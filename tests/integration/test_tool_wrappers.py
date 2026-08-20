from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiflow.errors import ContractError
from aiflow.policy import evaluate_action_permission, load_policy_bundle
from aiflow.verification_service import VerifyResult
from tools import gauntlet
from tools.hooks import pre_command, pre_commit

ROOT = Path(__file__).resolve().parents[2]


def test_gauntlet_delegates_provisional_verification_and_formats_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed: dict[str, object] = {}

    def fake_verify(root: Path, task_id: str, **kwargs: object) -> VerifyResult:
        observed.update(root=root, task_id=task_id, **kwargs)
        return VerifyResult(task_id, "provisional", "IMPLEMENTING", Path("evidence.json"), ())

    monkeypatch.setattr(gauntlet, "verify_task", fake_verify)
    monkeypatch.chdir(ROOT)

    assert gauntlet.main(["--task", "TASK-0001", "--provisional", "--format", "json"]) == 0
    assert observed["task_id"] == "TASK-0001"
    assert observed["actor"] == "gauntlet"
    assert observed["provisional"] is True
    assert json.loads(capsys.readouterr().out)["conclusion"] == "provisional"


def test_gauntlet_uses_cli_error_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*args: object, **kwargs: object) -> VerifyResult:
        raise ContractError("not ready", code="VERIFY_STATE_INVALID")

    monkeypatch.setattr(gauntlet, "verify_task", reject)
    assert gauntlet.main(["--task", "TASK-0001"]) == 1


@pytest.mark.parametrize(
    ("action", "expected_allowed"),
    [
        ("push", False),
        ("merge", False),
        ("deploy", False),
        ("delete", False),
        ("secret_export", False),
        ("paid_external_call", False),
        ("read", True),
    ],
)
def test_pre_command_uses_core_permission_policy(action: str, expected_allowed: bool) -> None:
    decision = evaluate_action_permission(load_policy_bundle(ROOT), action)
    passed, reasons = pre_command.check_pre_command(ROOT, action, "example")

    assert decision.allowed_automatically is expected_allowed
    assert passed is expected_allowed
    assert ("ACTION_PERMISSION_DENIED" in reasons) is (not expected_allowed)


def test_pre_commit_delegates_scope_and_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = {
        "current_state": "IMPLEMENTING",
        "base_commit": "a" * 40,
        "subject_commit": "b" * 40,
        "allowed_scope": ["src/**"],
    }
    monkeypatch.setattr(pre_commit, "_resolve_task_id", lambda root, task_id: "TASK-0001")
    monkeypatch.setattr(
        pre_commit, "read_task_record_strict", lambda root, task_id: SimpleNamespace(task=task)
    )
    monkeypatch.setattr(
        pre_commit,
        "summarize_task",
        lambda root, task_id: SimpleNamespace(current_state="IMPLEMENTING", observed_head="c" * 40),
    )
    monkeypatch.setattr(
        pre_commit, "collect_changed_paths", lambda *args, **kwargs: SimpleNamespace(paths=("x",))
    )
    monkeypatch.setattr(
        pre_commit, "assess_scope", lambda *args, **kwargs: SimpleNamespace(passed=False)
    )

    passed, reasons = pre_commit.check_pre_commit(ROOT, "TASK-0001")

    assert passed is False
    assert "SCOPE_EXPANDED" in reasons


def test_pre_commit_rejects_missing_or_ambiguous_task(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="Exactly one active task"):
        pre_commit._resolve_task_id(tmp_path, None)


@pytest.mark.parametrize(
    "script",
    ("tools/gauntlet.py", "tools/hooks/pre_commit.py", "tools/hooks/pre_command.py"),
)
def test_wrapper_help_is_executable(script: str) -> None:
    result = subprocess.run(
        [sys.executable, script, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout
