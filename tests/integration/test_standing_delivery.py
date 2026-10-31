"""Regression tests for bounded standing delivery authorization.

The AUTO cases deliberately understate side effects to verify that the independent
Policy action check still rejects those declared plans. They do not authorize an
actual Git operation or verify the identity of a caller.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from test_begin_close_commands import create_repository
from test_governance_paths import _auto_unit
from test_verify_command import _plan

from aiflow import task_service, verification_service
from aiflow.cli import main
from aiflow.contracts import schema_directory_context
from aiflow.errors import PolicyError
from aiflow.policy import evaluate_action_permission, load_policy_bundle
from aiflow.storage import atomic_write_yaml, read_task_json, read_task_yaml, resolve_task_path
from aiflow.task_service import load_task_record, transition_task_record

ROOT = Path(__file__).resolve().parents[2]
ACTIONS = {"push", "merge", "deploy", "delete", "secret_export", "paid_external_call"}
OTHER_ACTIONS = ACTIONS - {"push", "merge"}


def _permissions(repository: Path) -> tuple[Path, dict[str, object]]:
    path = repository / ".ai" / "policy" / "permissions.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return path, value


def _write_permissions(path: Path, value: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _set_approval(value: dict[str, object], action: str, approval: str) -> None:
    rules = value["rules"]
    assert isinstance(rules, list)
    rule = next(rule for rule in rules if rule["action"] == action)
    rule["required_approval"] = approval


def _start(monkeypatch: pytest.MonkeyPatch, repository: Path, *extra: str) -> int:
    monkeypatch.chdir(repository)
    return main(["start", "--objective", "bounded", "--allow", "src/**", *extra])


def test_active_policy_declares_standing_delivery_without_automatic_allowance() -> None:
    with schema_directory_context(ROOT / ".ai" / "schemas"):
        policy = load_policy_bundle(ROOT)
    for action in ACTIONS:
        decision = evaluate_action_permission(policy, action)
        assert not decision.allowed_automatically
        assert decision.required_approval == (
            "standing_or_action" if action in {"push", "merge"} else "action"
        )


@pytest.mark.parametrize("action", ["push", "merge"])
def test_standing_approval_is_schema_valid_only_as_a_deny_rule(tmp_path: Path, action: str) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    _set_approval(permissions, action, "standing_or_action")
    _write_permissions(path, permissions)
    with schema_directory_context(repository / ".ai" / "schemas"):
        policy = load_policy_bundle(repository)
    decision = evaluate_action_permission(policy, action)
    assert decision.required_approval == "standing_or_action"
    assert not decision.allowed_automatically


@pytest.mark.parametrize("action", ["push", "merge"])
def test_standing_approval_cannot_change_policy_effect_to_allow(
    tmp_path: Path, action: str
) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    _set_approval(permissions, action, "standing_or_action")
    rules = permissions["rules"]
    assert isinstance(rules, list)
    rule = next(rule for rule in rules if rule["action"] == action)
    rule["effect"] = "allow_automatic"
    _write_permissions(path, permissions)
    with schema_directory_context(repository / ".ai" / "schemas"):
        with pytest.raises(PolicyError) as caught:
            load_policy_bundle(repository)
    assert caught.value.code == "POLICY_SCHEMA_INVALID"


@pytest.mark.parametrize("action", sorted(OTHER_ACTIONS))
def test_standing_approval_is_schema_rejected_for_other_actions(
    tmp_path: Path, action: str
) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    _set_approval(permissions, action, "standing_or_action")
    _write_permissions(path, permissions)
    with schema_directory_context(repository / ".ai" / "schemas"):
        with pytest.raises(PolicyError) as caught:
            load_policy_bundle(repository)
    assert caught.value.code == "POLICY_SCHEMA_INVALID"


def test_legacy_policy_remains_valid_and_retains_all_default_forbids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    for action in ("push", "merge"):
        _set_approval(permissions, action, "action")
    permissions["policy_version"] = "2.5.0"
    _write_permissions(path, permissions)
    for name in ("hard-rules.yaml", "routing.yaml", "verification-levels.yaml"):
        other = path.parent / name
        document = yaml.safe_load(other.read_text(encoding="utf-8"))
        document["policy_version"] = "2.5.0"
        other.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with schema_directory_context(repository / ".ai" / "schemas"):
        policy = load_policy_bundle(repository)
    assert evaluate_action_permission(policy, "push").required_approval == "action"
    assert _start(monkeypatch, repository) == 0
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    assert set(task["forbidden_actions"]) == ACTIONS


def test_legacy_policy_yaml_merge_override_loads_and_start_preserves_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    permissions["policy_version"] = "2.5.0"
    for action in ("push", "merge"):
        _set_approval(permissions, action, "action")
    text = yaml.safe_dump(permissions, sort_keys=False)
    push = "- id: PERMISSION-DENY-AUTO-PUSH\n"
    merge = (
        "- id: PERMISSION-DENY-AUTO-MERGE\n"
        "  priority: 680\n"
        "  action: merge\n"
        "  effect: deny_automatic\n"
        "  required_approval: action\n"
    )
    assert text.count(push) == text.count(merge) == 1
    text = text.replace(push, "- &push_rule\n  id: PERMISSION-DENY-AUTO-PUSH\n", 1)
    text = text.replace(
        merge,
        "- <<: *push_rule\n  id: PERMISSION-DENY-AUTO-MERGE\n  priority: 680\n  action: merge\n",
        1,
    )
    assert yaml.safe_load(text) == permissions
    path.write_text(text, encoding="utf-8")
    for name in ("hard-rules.yaml", "routing.yaml", "verification-levels.yaml"):
        other = path.parent / name
        document = yaml.safe_load(other.read_text(encoding="utf-8"))
        document["policy_version"] = "2.5.0"
        other.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with schema_directory_context(repository / ".ai" / "schemas"):
        policy = load_policy_bundle(repository)
    assert policy.documents["permissions.yaml"] == permissions
    assert _start(monkeypatch, repository) == 0
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    assert set(task["forbidden_actions"]) == ACTIONS


@pytest.mark.parametrize("explicit", [[], ["push"], ["merge"], ["push", "merge"]])
def test_new_task_preserves_explicit_forbids_and_other_policy_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: list[str]
) -> None:
    repository = create_repository(tmp_path / "repository")
    extra = [item for action in explicit for item in ("--forbid-action", action)]
    assert _start(monkeypatch, repository, *extra) == 0
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    assert set(task["forbidden_actions"]) == OTHER_ACTIONS | set(explicit)


@pytest.mark.parametrize("standing_action", ["push", "merge"])
def test_only_action_with_standing_rule_is_omitted_from_new_task_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, standing_action: str
) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    for action in ("push", "merge"):
        _set_approval(
            permissions, action, "standing_or_action" if action == standing_action else "action"
        )
    _write_permissions(path, permissions)
    assert _start(monkeypatch, repository) == 0
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    assert set(task["forbidden_actions"]) == ACTIONS - {standing_action}


def test_start_does_not_rewrite_an_existing_task_forbidden_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    assert _start(monkeypatch, repository, "--forbid-action", "push") == 0
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["forbidden_actions"] = sorted(ACTIONS)
    atomic_write_yaml(task_path, task)
    before = task_path.read_bytes()
    assert _start(monkeypatch, repository) == 0
    assert task_path.read_bytes() == before


@pytest.mark.parametrize("corruption", ["duplicate_rule", "standing_on_deploy", "unknown_approval"])
def test_invalid_policy_cannot_relax_new_task_defaults_or_create_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    if corruption == "duplicate_rule":
        rules = permissions["rules"]
        assert isinstance(rules, list)
        rules.append(dict(rules[0]))
    elif corruption == "standing_on_deploy":
        _set_approval(permissions, "deploy", "standing_or_action")
    else:
        _set_approval(permissions, "push", "invalid")
    _write_permissions(path, permissions)
    assert _start(monkeypatch, repository) == 1
    assert not (repository / ".ai" / "tasks" / "TASK-0001").exists()


@pytest.mark.parametrize("duplicate", ["push_same", "push_override", "top_level_forbidden"])
def test_duplicate_policy_keys_are_rejected_before_start_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, duplicate: str
) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    text = path.read_text(encoding="utf-8")
    if duplicate.startswith("push_"):
        rules = permissions["rules"]
        assert isinstance(rules, list)
        push = next(rule for rule in rules if rule["action"] == "push")
        current = push["required_approval"]
        assert current in {"action", "standing_or_action"}
        start = text.index("  - id: PERMISSION-DENY-AUTO-PUSH")
        end = text.index("\n  - id:", start + 1)
        block = text[start:end]
        original = f"    required_approval: {current}"
        assert block.count(original) == 1
        if duplicate == "push_same":
            replacement = f"{original}\n{original}"
            expected = current
        else:
            replacement = "    required_approval: action\n    required_approval: standing_or_action"
            expected = "standing_or_action"
        text = text[:start] + block.replace(original, replacement) + text[end:]
        # Prove the permissive parser sees exactly the intended push override.
        parsed = yaml.safe_load(text)
        parsed_push = next(rule for rule in parsed["rules"] if rule["action"] == "push")
        assert parsed_push["required_approval"] == expected
    else:
        text += "\n" + yaml.safe_dump(
            {"forbidden_automatic_actions": permissions["forbidden_automatic_actions"]},
            sort_keys=False,
        )
    path.write_text(text, encoding="utf-8")
    assert _start(monkeypatch, repository) == 1
    assert not (repository / ".ai" / "tasks").exists()


def test_duplicate_key_inside_anchored_rule_is_rejected_before_start_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    path, permissions = _permissions(repository)
    text = path.read_text(encoding="utf-8")
    rules = permissions["rules"]
    assert isinstance(rules, list)
    push = next(rule for rule in rules if rule["action"] == "push")
    current = push["required_approval"]
    start = text.index("  - id: PERMISSION-DENY-AUTO-PUSH")
    end = text.index("\n  - id:", start + 1)
    block = text[start:end]
    original = f"    required_approval: {current}"
    assert block.count(original) == 1
    block = block.replace(
        "  - id: PERMISSION-DENY-AUTO-PUSH",
        "  - &push_rule\n    id: PERMISSION-DENY-AUTO-PUSH",
        1,
    )
    block = block.replace(original, f"{original}\n{original}", 1)
    text = text[:start] + block + text[end:]
    merge = "  - id: PERMISSION-DENY-AUTO-MERGE"
    assert text.count(merge) == 1
    text = text.replace(merge, "  - <<: *push_rule\n    id: PERMISSION-DENY-AUTO-MERGE", 1)
    # The permissive parser sees an unchanged valid Policy despite the duplicate.
    assert yaml.safe_load(text) == permissions
    path.write_text(text, encoding="utf-8")
    assert _start(monkeypatch, repository) == 1
    assert not (repository / ".ai" / "tasks").exists()


def test_start_api_uses_target_repository_schema_across_working_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    (repository / ".ai" / "schemas" / "policy.schema.json").write_text(
        json.dumps({"not": {}}), encoding="utf-8"
    )
    monkeypatch.chdir(ROOT)
    with pytest.raises(PolicyError):
        task_service.start_task(
            repository,
            objective="bounded",
            allowed_scope=["src/**"],
            forbidden_actions=[],
        )
    assert not (repository / ".ai" / "tasks" / "TASK-0001").exists()


def _classified_auto_with_declared_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str, explicit: bool
) -> Path:
    repository = create_repository(tmp_path / "repository")
    assert _start(monkeypatch, repository) == 0
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    # Reproduce the new-task shape even on the pre-change implementation.
    task["forbidden_actions"] = sorted(OTHER_ACTIONS | ({action} if explicit else set()))
    unit = _auto_unit("TASK-0001")
    unit["planned_actions"] = [action]
    task["decision_units"] = [unit]
    atomic_write_yaml(task_path, task)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    classification = read_task_json(repository, "TASK-0001", "classification.json")
    assert isinstance(classification, dict)
    assert classification["effective_route"] == "AUTO"
    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 0
    return repository


@pytest.mark.parametrize(
    ("action", "explicit"),
    [("push", False), ("merge", False), ("push", True), ("merge", True), ("publish", True)],
)
def test_auto_begin_rejects_forbidden_declared_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    action: str,
    explicit: bool,
) -> None:
    repository = _classified_auto_with_declared_action(tmp_path, monkeypatch, action, explicit)
    capsys.readouterr()
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1
    assert "AUTO_FORBIDDEN_ACTION" in capsys.readouterr().err
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "READY_TO_IMPLEMENT"


def test_auto_gate_allows_unforbidden_edit_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _classified_auto_with_declared_action(tmp_path, monkeypatch, "edit", False)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan())
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    capsys.readouterr()
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    decision = json.loads(capsys.readouterr().out)
    assert decision["passed"] is True
    assert decision["reason_codes"] == []


@pytest.mark.parametrize(
    ("action", "explicit"),
    [("push", False), ("merge", False), ("push", True), ("merge", True), ("publish", True)],
)
def test_auto_gate_rejects_forbidden_declared_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    action: str,
    explicit: bool,
) -> None:
    repository = _classified_auto_with_declared_action(tmp_path, monkeypatch, action, explicit)
    # Seed the post-begin state as an independent Gate regression, since begin itself
    # must reject this input once the fix is implemented.
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="IMPLEMENTING",
        event_type="implementation_started",
        actor="fixture",
        payload={},
        satisfied_preconditions={"readiness_satisfied"},
    )
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan())
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    capsys.readouterr()
    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    decision = json.loads(capsys.readouterr().out)
    assert "GATE_SCOPE_CHANGED" in decision["reason_codes"]
