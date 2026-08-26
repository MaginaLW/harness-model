from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiflow.errors import ContractError
from aiflow.observation import serialize_observation
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


def _pre_commit_task() -> dict[str, object]:
    return {
        "current_state": "IMPLEMENTING",
        "base_commit": "a" * 40,
        "subject_commit": "b" * 40,
        "allowed_scope": ["src/**"],
    }


def _install_pre_commit_facts(monkeypatch: pytest.MonkeyPatch, *, scope: object) -> None:
    task = _pre_commit_task()
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
    monkeypatch.setattr(pre_commit, "assess_scope", lambda *args, **kwargs: scope)


def test_pre_commit_in_scope_has_no_observation_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_pre_commit_facts(monkeypatch, scope=SimpleNamespace(passed=True, out_of_scope=()))
    monkeypatch.setattr(
        pre_commit,
        "load_policy_bundle",
        lambda *_args: pytest.fail("in-scope check must not load Policy"),
    )
    monkeypatch.setattr(
        pre_commit,
        "apply_observation",
        lambda *_args, **_kwargs: pytest.fail("in-scope check must not apply an observation"),
    )

    passed, reasons = pre_commit.check_pre_commit(ROOT, "TASK-0001")

    assert passed is True
    assert reasons == ()


def test_pre_commit_delegates_exact_out_of_scope_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_pre_commit_facts(
        monkeypatch,
        scope=SimpleNamespace(passed=False, out_of_scope=("docs/out.md", "src/out.py")),
    )
    monkeypatch.setattr(
        pre_commit, "load_policy_bundle", lambda *_args: SimpleNamespace(sha256="d" * 64)
    )
    observed: dict[str, object] = {}

    def apply(root: Path, task_id: str, observation: object, *, actor: str) -> None:
        observed["calls"] = int(observed.get("calls", 0)) + 1
        observed.update(
            root=root,
            task_id=task_id,
            observation=serialize_observation(observation),
            actor=actor,
        )

    monkeypatch.setattr(pre_commit, "apply_observation", apply)

    passed, reasons = pre_commit.check_pre_commit(ROOT, "TASK-0001")

    assert passed is False
    assert "SCOPE_EXPANDED" in reasons
    assert observed == {
        "calls": 1,
        "root": ROOT,
        "task_id": "TASK-0001",
        "observation": {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "base_commit": "a" * 40,
            "subject_commit": "b" * 40,
            "policy_sha256": "d" * 64,
            "source": "hook_pre_commit",
            "kind": "scope_out_of_bounds",
            "summary": {"paths": ["docs/out.md", "src/out.py"]},
        },
        "actor": "hook_pre_commit",
    }


def test_pre_commit_observation_failure_propagates_to_fail_closed_main(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_pre_commit_facts(
        monkeypatch, scope=SimpleNamespace(passed=False, out_of_scope=("src/out.py",))
    )
    monkeypatch.setattr(
        pre_commit, "load_policy_bundle", lambda *_args: SimpleNamespace(sha256="d" * 64)
    )

    def fail(*_args: object, **_kwargs: object) -> None:
        raise ContractError("observation persistence failed", code="OBSERVATION_AUDIT_FAILED")

    monkeypatch.setattr(pre_commit, "apply_observation", fail)
    monkeypatch.chdir(ROOT)

    assert pre_commit.main(["--task", "TASK-0001"]) == 1
    assert capsys.readouterr().err == "observation persistence failed\n"


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
