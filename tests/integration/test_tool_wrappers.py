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
def test_pre_command_uses_core_permission_policy(
    action: str, expected_allowed: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    decision = evaluate_action_permission(load_policy_bundle(ROOT), action)
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: SimpleNamespace(task=_pre_command_task()),
    )
    monkeypatch.setattr(pre_command, "apply_observation", lambda *_args, **_kwargs: None)
    passed, reasons = pre_command.check_pre_command(ROOT, action, "example", "TASK-0001")

    assert decision.allowed_automatically is expected_allowed
    assert passed is expected_allowed
    assert ("ACTION_PERMISSION_DENIED" in reasons) is (not expected_allowed)


def _pre_command_task() -> dict[str, object]:
    return {
        "current_state": "IMPLEMENTING",
        "base_commit": "a" * 40,
        "subject_commit": "b" * 40,
    }


def test_pre_command_allowed_action_has_no_task_or_observation_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: pytest.fail("allowed action must not read a task"),
    )
    monkeypatch.setattr(
        pre_command,
        "apply_observation",
        lambda *_args, **_kwargs: pytest.fail("allowed action must not apply an observation"),
    )

    passed, reasons = pre_command.check_pre_command(ROOT, "read", "opaque target", "")

    assert passed is True
    assert reasons == ()


def test_pre_command_rejects_empty_target_before_policy_or_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pre_command,
        "load_policy_bundle",
        lambda *_args: pytest.fail("empty target must not load Policy"),
    )
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: pytest.fail("empty target must not read a task"),
    )

    with pytest.raises(ContractError, match="Action target is required") as error:
        pre_command.check_pre_command(ROOT, "push", "   ")

    assert error.value.code == "HOOK_TARGET_INVALID"


def test_pre_command_delegates_exact_high_risk_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _pre_command_task()
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: SimpleNamespace(task=task),
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

    monkeypatch.setattr(pre_command, "apply_observation", apply)

    passed, reasons = pre_command.check_pre_command(ROOT, "push", "origin/main", "TASK-0001")

    assert passed is False
    assert reasons == ("ACTION_PERMISSION_DENIED",)
    assert observed == {
        "calls": 1,
        "root": ROOT,
        "task_id": "TASK-0001",
        "observation": {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "base_commit": "a" * 40,
            "subject_commit": "b" * 40,
            "policy_sha256": load_policy_bundle(ROOT).sha256,
            "source": "hook_pre_command",
            "kind": "high_risk_command",
            "summary": {"action": "push", "target_ref": "origin/main"},
        },
        "actor": "hook_pre_command",
    }


def test_pre_command_invalid_high_risk_target_fails_before_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _pre_command_task()
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: SimpleNamespace(task=task),
    )
    monkeypatch.setattr(
        pre_command,
        "apply_observation",
        lambda *_args, **_kwargs: pytest.fail("invalid target must not be applied"),
    )

    assert (
        pre_command.main(["--action", "push", "--target", "bad target", "--task", "TASK-0001"]) == 1
    )


def test_pre_command_observation_failure_propagates_to_fail_closed_main(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _pre_command_task()
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: SimpleNamespace(task=task),
    )

    def fail(*_args: object, **_kwargs: object) -> None:
        raise ContractError("observation persistence failed", code="OBSERVATION_AUDIT_FAILED")

    monkeypatch.setattr(pre_command, "apply_observation", fail)
    monkeypatch.chdir(ROOT)

    assert (
        pre_command.main(["--action", "push", "--target", "origin/main", "--task", "TASK-0001"])
        == 1
    )
    assert capsys.readouterr().err == "observation persistence failed\n"


def test_pre_command_task_resolver_requires_unique_active_task(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="Exactly one active task"):
        pre_command._resolve_task_id(tmp_path, None)


def test_pre_command_task_resolver_accepts_one_active_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_root = tmp_path / ".ai" / "tasks"
    (task_root / "TASK-0001").mkdir(parents=True)
    (task_root / "TASK-0002").mkdir()
    states = {"TASK-0001": "MERGED", "TASK-0002": "IMPLEMENTING"}
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda _root, task_id: SimpleNamespace(task={"current_state": states[task_id]}),
    )

    assert pre_command._resolve_task_id(tmp_path, None) == "TASK-0002"


def test_pre_command_task_resolver_rejects_ambiguous_or_empty_explicit_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_root = tmp_path / ".ai" / "tasks"
    (task_root / "TASK-0001").mkdir(parents=True)
    (task_root / "TASK-0002").mkdir()

    def read(_root: Path, task_id: str) -> SimpleNamespace:
        if task_id == "":
            raise ContractError("Task is required", code="STATE_TASK_ID_INVALID")
        return SimpleNamespace(task={"current_state": "IMPLEMENTING"})

    monkeypatch.setattr(pre_command, "read_task_record_strict", read)

    with pytest.raises(ContractError, match="Exactly one active task"):
        pre_command._resolve_task_id(tmp_path, None)
    with pytest.raises(ContractError, match="Task is required"):
        pre_command._resolve_task_id(tmp_path, "")


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
