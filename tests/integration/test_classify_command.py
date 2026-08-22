"""End-to-end coverage for durable ``aiflow classify`` decisions."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from test_begin_close_commands import create_repository, start

from aiflow.classification_service import _change_reason, _is_downgrade, _stable_input
from aiflow.cli import main
from aiflow.decision_units import parse_decision_units
from aiflow.errors import StorageError
from aiflow.policy import load_policy_bundle
from aiflow.storage import atomic_write_yaml, read_task_json, read_task_yaml, resolve_task_path
from aiflow.task_service import load_task_record, record_task_event


def _unit(task_id: str, **changes: object) -> dict[str, object]:
    unit: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": task_id,
        "decision_unit_id": "DU-001",
        "goal": "bounded change",
        "inputs": [],
        "planned_actions": ["edit"],
        "impact_scope": ["src/module.py"],
        "reversibility": "reversible",
        "verification_methods": ["pytest"],
        "external_side_effects": [],
        "permission_requirements": [],
        "scope": {"clear": True},
        "impact": {"level": "low"},
        "protections": {"verified_backup": True, "dry_run": True},
        "verification": {"automatic": True, "tools_missing": False},
        "change_characteristics": {
            "mechanical": True,
            "behavior_changed": False,
            "code_modified": False,
            "interaction_scope": "local",
            "regression_risk": False,
            "error_detectability": "high",
        },
    }
    unit.update(changes)
    return unit


def _prepare(repository: Path, monkeypatch: pytest.MonkeyPatch, **changes: object) -> None:
    start(repository, monkeypatch)
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [_unit("TASK-0001", **changes)]
    atomic_write_yaml(task_path, task)


@pytest.mark.parametrize(
    ("changes", "state", "route", "event_type"),
    [
        ({}, "READY_TO_IMPLEMENT", "AUTO", "implementation_ready"),
        ({"business_direction_count": 2}, "WAITING_FOR_ASK", "ASK", "ask_required"),
        (
            {"impact_categories": ["ci"]},
            "WAITING_FOR_SPEC_REVIEW",
            "REVIEW",
            "spec_review_required",
        ),
        (
            {"external_side_effects": ["credential_export"]},
            "BLOCKED",
            "BLOCK",
            "classification_blocked",
        ),
    ],
)
def test_classify_routes_all_four_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, object],
    state: str,
    route: str,
    event_type: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(repository, monkeypatch, **changes)

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    record = load_task_record(repository, "TASK-0001")
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    assert record.task["current_state"] == state
    assert classification["effective_route"] == route
    assert classification["effective_verification_level"] == "V0"
    assert classification["base_commit"] == record.task["base_commit"]
    assert classification["subject_commit"] == record.task["subject_commit"]
    entry = classification["classifications"][0]
    assert entry["route"] == route and entry["verification_level"] == "V0"
    assert entry["matched_rules"] and entry["explanations"]
    assert [event["event_type"] for event in record.events] == [
        "task_created",
        "classification_recorded",
        event_type,
    ]
    assert (
        record.events[-1]["payload"]["classification_input_sha256"]
        == classification["classification_input_sha256"]
    )
    assert record.events[-1]["payload"]["policy_sha256"] == classification["policy_sha256"]


def test_classify_same_identity_does_not_append_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(repository, monkeypatch)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    count = len(load_task_record(repository, "TASK-0001").events)

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert len(load_task_record(repository, "TASK-0001").events) == count


def test_mixed_ask_review_waits_for_answer_before_spec_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    ask = _unit("TASK-0001", business_direction_count=2)
    review = _unit("TASK-0001", impact_categories=["ci"])
    review["decision_unit_id"] = "DU-002"
    task["decision_units"] = [ask, review]
    atomic_write_yaml(task_path, task)

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0

    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    assert classification["effective_route"] == "REVIEW"
    assert {entry["route"] for entry in classification["classifications"]} == {
        "ASK",
        "REVIEW",
    }
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "WAITING_FOR_ASK"
    assert record.events[-1]["event_type"] == "ask_required"


@pytest.mark.parametrize(
    ("route_changes", "expected_route"),
    [({}, "AUTO"), ({"impact_categories": ["ci"]}, "REVIEW")],
)
def test_v2_facts_use_the_v2_contract_independently_of_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    route_changes: dict[str, object],
    expected_route: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(
        repository,
        monkeypatch,
        verification_requirements={
            "acceptance_required": True,
            "integration_required": False,
            "targeted_mutation_required": False,
            "independent_verifier_required": False,
        },
        **route_changes,
    )

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    assert classification["schema_version"] == "2.0"
    assert classification["effective_route"] == expected_route
    assert classification["effective_verification_level"] == "V2"
    assert classification["classifications"][0]["verification_rule_ids"] == [
        "VERIFICATION-V2-ACCEPTANCE-REQUIRED"
    ]

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    assert '"verification_level": "V2"' in capsys.readouterr().out


def test_v2_to_v1_is_a_downgrade_and_v1_to_v2_is_an_upgrade() -> None:
    previous_v2 = {
        "effective_route": "AUTO",
        "effective_verification_level": "V2",
        "classifications": [
            {"decision_unit_id": "DU-001", "route": "AUTO", "verification_level": "V2"}
        ],
    }
    v1_entries = [
        {"decision_unit_id": "DU-001", "route": "AUTO", "verification_level": "V1"}
    ]
    assert _is_downgrade(
        previous_v2,
        v1_entries,
        effective_route="AUTO",
        effective_level="V1",
    )
    assert (
        _change_reason(previous_v2, v1_entries, route="AUTO", level="V1")
        == "downgraded"
    )

    previous_v1 = {
        "effective_route": "AUTO",
        "effective_verification_level": "V1",
        "classifications": v1_entries,
    }
    v2_entries = [
        {"decision_unit_id": "DU-001", "route": "AUTO", "verification_level": "V2"}
    ]
    assert (
        _change_reason(previous_v1, v2_entries, route="AUTO", level="V2")
        == "upgraded"
    )


def test_blocked_reclassification_binds_old_and_new_identity_and_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(repository, monkeypatch, external_side_effects=["credential_export"])
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    before = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(before, dict)

    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [_unit("TASK-0001")]
    atomic_write_yaml(task_path, task)
    # A harmless Policy wording change proves the new identity includes Policy semantics.
    routing = repository / ".ai" / "policy" / "routing.yaml"
    routing.write_text(
        routing.read_text(encoding="utf-8").replace("user choice.", "a user choice."),
        encoding="utf-8",
    )
    new_input = _stable_input(task, parse_decision_units(task))
    new_policy = load_policy_bundle(repository).sha256
    resolution = {
        "reason": "removed external transfer",
        "evidence_refs": ["evidence-001"],
        "previous_classification_input_sha256": before["classification_input_sha256"],
        "previous_policy_sha256": before["policy_sha256"],
    }
    record_task_event(
        repository,
        "TASK-0001",
        event_type="resolution_recorded",
        actor="reviewer",
        payload=resolution,
    )
    event_count = len(load_task_record(repository, "TASK-0001").events)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    assert "authorized" in capsys.readouterr().err.lower()
    assert len(load_task_record(repository, "TASK-0001").events) == event_count

    resolution.update(
        {
            "manual_authorization": True,
            "authorized_by": "reviewer",
            "authorized_classification_input_sha256": new_input,
            "authorized_policy_sha256": new_policy,
        }
    )
    # The rejection leaves the valid resolution in place; record the bound authorization separately.
    record_task_event(
        repository,
        "TASK-0001",
        event_type="resolution_recorded",
        actor="reviewer",
        payload=resolution,
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    after = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(after, dict)
    assert after["classification_input_sha256"] == new_input
    assert after["policy_sha256"] == new_policy
    final_event = load_task_record(repository, "TASK-0001").events[-1]
    assert final_event["payload"]["change_reason"] == "downgraded"


def test_verification_only_block_can_upgrade_to_review_without_manual_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(
        repository,
        monkeypatch,
        verification={"automatic": True, "tools_missing": True},
    )
    # Keep the verification tool failure in the verification gate, not in a hard route rule.
    hard_path = repository / ".ai" / "policy" / "hard-rules.yaml"
    hard = yaml.safe_load(hard_path.read_text(encoding="utf-8"))
    assert isinstance(hard, dict)
    rule = next(
        item for item in hard["rules"] if item["id"] == "HARD-BLOCK-VERIFICATION-TOOL-MISSING"
    )
    rule["conditions"][0]["value"] = "not-a-boolean"
    hard_path.write_text(yaml.safe_dump(hard, sort_keys=False), encoding="utf-8")

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    old = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(old, dict)
    assert old["effective_route"] == "BLOCK"
    assert old["classifications"][0]["route"] == "AUTO"

    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [
        _unit(
            "TASK-0001",
            verification={"automatic": True, "tools_missing": False},
            impact_categories=["ci"],
        )
    ]
    atomic_write_yaml(task_path, task)
    record_task_event(
        repository,
        "TASK-0001",
        event_type="resolution_recorded",
        actor="reviewer",
        payload={
            "reason": "restored verification tools",
            "evidence_refs": ["evidence-002"],
            "previous_classification_input_sha256": old["classification_input_sha256"],
            "previous_policy_sha256": old["policy_sha256"],
        },
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    new = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(new, dict)
    assert new["effective_route"] == "REVIEW" and new["change_reason"] == "upgraded"
    assert (
        load_task_record(repository, "TASK-0001").events[-1]["payload"]["change_reason"]
        == "upgraded"
    )


@pytest.mark.parametrize(
    ("impact_scope", "allowed_scope"),
    [(["src/nested/module.py"], ["src/*"]), (["srcevil/module.py"], ["src/**"])],
)
def test_classify_rejects_paths_outside_segment_aware_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    impact_scope: list[str],
    allowed_scope: list[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(repository, monkeypatch, impact_scope=impact_scope)
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["allowed_scope"] = allowed_scope
    atomic_write_yaml(task_path, task)

    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    assert "scope" in capsys.readouterr().err.lower()


def test_classify_rejects_repository_identity_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(repository, monkeypatch)
    (repository / ".ai" / "repository-id").write_text(
        "123e4567-e89b-42d3-a456-426614174001\n", encoding="utf-8"
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    assert "baseline" in capsys.readouterr().err.lower()


def test_classification_write_failure_does_not_change_state_or_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(repository, monkeypatch)
    from aiflow import classification_service

    def fail_write(_path: Path, _value: object) -> None:
        raise StorageError("simulated", code="STORAGE_WRITE_FAILED")

    monkeypatch.setattr(classification_service, "atomic_write_json", fail_write)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "NEW" and len(record.events) == 1


def test_invalid_policy_does_not_write_classification_or_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(repository, monkeypatch)
    (repository / ".ai" / "policy" / "routing.yaml").write_text("invalid: [", encoding="utf-8")
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "NEW" and len(record.events) == 1
    assert not resolve_task_path(repository, "TASK-0001", "classification.json").exists()


def test_second_transition_failure_recovers_from_classified_on_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    _prepare(repository, monkeypatch)
    from aiflow import classification_service

    original = classification_service.transition_task_record
    calls = 0

    def fail_second(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise StorageError("simulated", code="STATE_EVENT_APPEND_FAILED")
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(classification_service, "transition_task_record", fail_second)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "CLASSIFIED"
    monkeypatch.setattr(classification_service, "transition_task_record", original)

    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    original_units = task["decision_units"]
    task["decision_units"] = [_unit("TASK-0001", goal="changed during recovery")]
    atomic_write_yaml(task_path, task)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "CLASSIFIED"

    task["decision_units"] = original_units
    atomic_write_yaml(task_path, task)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "READY_TO_IMPLEMENT"


def test_classify_help_is_available(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["classify", "--help"])
    assert caught.value.code == 0
    assert "--actor" in capsys.readouterr().out
