from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_begin_close_commands import commit_all, create_repository, make_ready, run_git, start

from aiflow.cli import main as cli_main
from aiflow.decision_units import classification_input_digest, parse_decision_units
from aiflow.errors import ContractError
from aiflow.observation import serialize_observation
from aiflow.policy import evaluate_action_permission, load_policy_bundle
from aiflow.storage import atomic_write_json, atomic_write_yaml, read_task_json
from aiflow.task_service import load_task_record
from tools.hooks import pre_command, pre_commit

ROOT = Path(__file__).resolve().parents[2]


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
        ("notify", False),
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


def test_pre_command_unknown_action_rejects_without_task_or_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pre_command,
        "resolve_hook_task_id",
        lambda *_args: pytest.fail("unknown action must not resolve a task"),
    )
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: pytest.fail("unknown action must not read a task"),
    )
    monkeypatch.setattr(
        pre_command,
        "apply_observation",
        lambda *_args, **_kwargs: pytest.fail("unknown action must not apply an observation"),
    )

    passed, reasons = pre_command.check_pre_command(ROOT, " Notify ", "opaque target", "TASK-0001")

    assert passed is False
    assert reasons == ("ACTION_PERMISSION_DENIED",)


def test_pre_command_unknown_action_main_uses_refusal_exit_without_task_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pre_command,
        "resolve_hook_task_id",
        lambda *_args: pytest.fail("unknown action must not resolve a task"),
    )
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: pytest.fail("unknown action must not read a task"),
    )
    monkeypatch.setattr(
        pre_command,
        "apply_observation",
        lambda *_args, **_kwargs: pytest.fail("unknown action must not apply an observation"),
    )
    monkeypatch.chdir(ROOT)

    assert pre_command.main(["--action", "notify", "--target", "opaque target"]) == 2


def test_pre_command_empty_action_is_policy_error_before_task_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pre_command,
        "resolve_hook_task_id",
        lambda *_args: pytest.fail("empty action must not resolve a task"),
    )
    monkeypatch.setattr(
        pre_command,
        "read_task_record_strict",
        lambda *_args: pytest.fail("empty action must not read a task"),
    )
    monkeypatch.setattr(
        pre_command,
        "apply_observation",
        lambda *_args, **_kwargs: pytest.fail("empty action must not apply an observation"),
    )
    monkeypatch.chdir(ROOT)

    assert pre_command.main(["--action", "   ", "--target", "opaque target"]) == 1


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


def test_hook_resolver_uses_branch_and_worktree_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    start(repository, monkeypatch)
    commit_all(repository, "start two tasks on main")
    run_git(repository, "switch", "-c", "feature")
    with pytest.raises(ContractError, match="Exactly one active task"):
        pre_command.resolve_hook_task_id(repository, None)

    tasks = repository / ".ai/tasks"
    (tasks / "TASK-0002/spec.md").write_text("branch candidate", encoding="utf-8")
    commit_all(repository, "update task 2")
    assert pre_commit.resolve_hook_task_id(repository, None) == "TASK-0002"
    (tasks / "TASK-0001/spec.md").write_text("another candidate", encoding="utf-8")
    with pytest.raises(ContractError, match="Exactly one active task"):
        pre_command.resolve_hook_task_id(repository, None)
    (tasks / "TASK-0001/task.yaml").write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="Invalid task contract"):
        pre_commit.resolve_hook_task_id(repository, None)
    assert pre_command.main(["--action", "push", "--target", "origin/main", "--task", ""]) == 1


@pytest.mark.parametrize("hook", ["pre_commit", "pre_command"])
def test_nested_hook_with_legacy_subject_records_base_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route="AUTO")
    assert cli_main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    directory = repository / ".ai/tasks/TASK-0001"
    task = load_task_record(repository, "TASK-0001").task
    task["subject_commit"] = None
    atomic_write_yaml(directory / "task.yaml", task)
    classification = read_task_json(repository, "TASK-0001", "classification.json")
    classification["classification_input_sha256"] = classification_input_digest(
        task, parse_decision_units(task)
    )
    atomic_write_json(directory / "classification.json", classification)
    nested = repository / "outside"
    nested.mkdir()
    (nested / "change.txt").write_text("out of scope", encoding="utf-8")
    with monkeypatch.context() as local:
        local.chdir(nested)
        if hook == "pre_commit":
            assert pre_commit.main([]) == 2
        else:
            assert pre_command.main(["--action", "push", "--target", "origin/main"]) == 2
    events = load_task_record(repository, "TASK-0001").events
    observed = [
        event["payload"]["observation"] for event in events if "observation" in event["payload"]
    ]
    assert observed[-1]["source"] == "hook_" + hook
    assert observed[-1]["subject_commit"] == task["base_commit"]


def _pre_commit_task() -> dict[str, object]:
    return {
        "current_state": "IMPLEMENTING",
        "base_commit": "a" * 40,
        "subject_commit": "b" * 40,
        "allowed_scope": ["src/**"],
    }


def _install_pre_commit_facts(monkeypatch: pytest.MonkeyPatch, *, scope: object) -> None:
    task = _pre_commit_task()
    monkeypatch.setattr(pre_commit, "resolve_hook_task_id", lambda root, task_id: "TASK-0001")
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
    repository = create_repository(tmp_path / "repository")
    with pytest.raises(ContractError, match="Exactly one active task"):
        pre_commit.resolve_hook_task_id(repository, None)


@pytest.mark.parametrize(
    "script",
    ("tools/hooks/pre_commit.py", "tools/hooks/pre_command.py"),
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
