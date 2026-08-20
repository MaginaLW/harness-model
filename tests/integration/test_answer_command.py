"""ASK answer core integration tests; CLI persistence is intentionally separate."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_begin_close_commands import classification as base_classification
from test_begin_close_commands import create_repository, start

from aiflow import ask_service
from aiflow.ask_service import prepare_answer, target_state_after_answer, validate_ask_options
from aiflow.classification_service import _stable_input
from aiflow.cli import main
from aiflow.decision_units import parse_decision_units
from aiflow.errors import ContractError, StateTransitionError, StorageError
from aiflow.policy import load_policy_bundle
from aiflow.storage import atomic_write_json, atomic_write_yaml, read_task_yaml, resolve_task_path
from aiflow.task_service import load_task_record, specification_is_current, transition_task_record

ANSWERED_AT = "2026-08-21T00:00:00Z"


def specification() -> str:
    return """# Task Specification

## 目标

实现确定性 ASK 回答。

## 范围

只修改任务记录。

## 非目标

不自动批准审核。

## 验收条件

- `pytest` 通过。

## 禁止动作

不得推送远端。

## 错误行为

非法选择必须拒绝。

## 回滚

恢复任务记录。
"""


def options(count: int = 2, **changes: object) -> dict[str, object]:
    document: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "decision_unit_id": "DU-001",
        "generated_at": ANSWERED_AT,
        "options": [
            {
                "option_id": f"OPT-{index:02d}",
                "description": f"option {index}",
                "benefit": "benefit",
                "cost": "cost",
                "risk": "risk",
                "recommended": index == 1,
            }
            for index in range(1, count + 1)
        ],
    }
    document.update(changes)
    return document


def classification(*routes: str) -> dict[str, object]:
    return {
        "task_id": "TASK-0001",
        "classifications": [
            {"decision_unit_id": f"DU-{index:03d}", "route": route}
            for index, route in enumerate(routes, start=1)
        ],
    }


@pytest.mark.parametrize("count", [1, 5])
def test_options_reject_outside_required_count(count: int) -> None:
    with pytest.raises(ContractError) as caught:
        validate_ask_options(options(count), task_id="TASK-0001")
    assert caught.value.code == "ASK_OPTIONS_INVALID"


@pytest.mark.parametrize("count", [2, 4])
def test_options_accept_required_count(count: int) -> None:
    assert len(validate_ask_options(options(count), task_id="TASK-0001")["options"]) == count


def test_options_reject_duplicate_ids_and_multiple_recommendations() -> None:
    duplicate = options()
    duplicate_options = duplicate["options"]
    assert isinstance(duplicate_options, list)
    duplicate_options[1] = {**duplicate_options[1], "option_id": "OPT-01"}
    with pytest.raises(ContractError) as caught:
        validate_ask_options(duplicate, task_id="TASK-0001")
    assert caught.value.code == "ASK_OPTION_IDS_DUPLICATE"

    recommended = options()
    recommended_options = recommended["options"]
    assert isinstance(recommended_options, list)
    recommended_options[1] = {**recommended_options[1], "recommended": True}
    with pytest.raises(ContractError) as caught:
        validate_ask_options(recommended, task_id="TASK-0001")
    assert caught.value.code == "ASK_RECOMMENDATION_MULTIPLE"


def test_answer_records_full_options_and_freezes_specification() -> None:
    result = prepare_answer(
        task_state="WAITING_FOR_ASK",
        classification=classification("ASK"),
        specification=specification(),
        options_document=options(),
        selected_option_id="OPT-02",
        actor="operator",
        reason="bounded rationale",
        answered_at=ANSWERED_AT,
    )
    assert result.target_state == "READY_TO_IMPLEMENT"
    assert result.event_payload["selected_option_id"] == "OPT-02"
    assert len(result.event_payload["options"]["options"]) == 2  # type: ignore[index]
    assert "## 已冻结决策" in result.frozen_specification
    assert "`OPT-02`" in result.decisions_markdown
    assert result.event_payload["semantic_distinctness_verified"] is False


@pytest.mark.parametrize(
    ("selected_option_id", "reason", "state", "code"),
    [
        ("OPT-99", "reason", "WAITING_FOR_ASK", "ASK_SELECTION_INVALID"),
        ("OPT-01", "  ", "WAITING_FOR_ASK", "ASK_REASON_REQUIRED"),
        ("OPT-01", "reason", "READY_TO_IMPLEMENT", "ASK_STATE_INVALID"),
    ],
)
def test_answer_rejects_invalid_selection_reason_or_state(
    selected_option_id: str, reason: str, state: str, code: str
) -> None:
    error_type: type[Exception] = (
        StateTransitionError if code == "ASK_STATE_INVALID" else ContractError
    )
    with pytest.raises(error_type) as caught:
        prepare_answer(
            task_state=state,
            classification=classification("ASK"),
            specification=specification(),
            options_document=options(),
            selected_option_id=selected_option_id,
            actor="operator",
            reason=reason,
            answered_at=ANSWERED_AT,
        )
    assert getattr(caught.value, "code") == code


def test_mixed_ask_review_remains_waiting_for_spec_review() -> None:
    assert target_state_after_answer(classification("ASK", "REVIEW")) == "WAITING_FOR_SPEC_REVIEW"


def test_repeated_answer_replaces_the_prior_frozen_decision_section() -> None:
    first = prepare_answer(
        task_state="WAITING_FOR_ASK",
        classification=classification("ASK"),
        specification=specification(),
        options_document=options(),
        selected_option_id="OPT-01",
        actor="operator",
        reason="first",
        answered_at=ANSWERED_AT,
    )
    repeated = prepare_answer(
        task_state="WAITING_FOR_ASK",
        classification=classification("ASK"),
        specification=first.frozen_specification,
        options_document=options(),
        selected_option_id="OPT-02",
        actor="operator",
        reason="second",
        answered_at=ANSWERED_AT,
    )
    assert repeated.frozen_specification.count("## 已冻结决策") == 1
    assert "理由：second" in repeated.frozen_specification
    assert "理由：first" not in repeated.frozen_specification


def _classification_for(repository: Path, *, mixed: bool) -> dict[str, object]:
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    document = base_classification("ASK")
    policy = load_policy_bundle(repository)
    document.update(
        {
            "classification_input_sha256": _stable_input(task, parse_decision_units(task)),
            "policy_version": policy.policy_version,
            "policy_sha256": policy.sha256,
            "base_commit": task["base_commit"],
            "subject_commit": task["subject_commit"],
        }
    )
    first = document["classifications"][0]
    first["policy_version"] = policy.policy_version
    first["policy_sha256"] = policy.sha256
    if mixed:
        review = copy.deepcopy(first)
        review.update(
            {
                "decision_unit_id": "DU-002",
                "route": "REVIEW",
                "rule_id": "TEST-REVIEW",
                "explanation": "review remains required",
                "explanations": ["review remains required"],
            }
        )
        review["matched_rules"][0].update(
            {
                "rule_id": "TEST-REVIEW",
                "route": "REVIEW",
                "explanation": "review remains required",
            }
        )
        document["classifications"].append(review)
        document["effective_route"] = "REVIEW"
    return document


def _prepare_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, mixed: bool = False
) -> tuple[Path, Path]:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    if mixed:
        second = copy.deepcopy(task["decision_units"][0])
        second["decision_unit_id"] = "DU-002"
        task["decision_units"].append(second)
        atomic_write_yaml(task_path, task)
    resolve_task_path(repository, "TASK-0001", "spec.md").write_text(
        specification(), encoding="utf-8"
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"),
        _classification_for(repository, mixed=mixed),
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="CLASSIFIED",
        event_type="classification_recorded",
        actor="classifier",
        payload={},
        satisfied_preconditions={"classification_available"},
    )
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="WAITING_FOR_ASK",
        event_type="ask_required",
        actor="classifier",
        payload={},
        satisfied_preconditions={"classification_route_selected"},
    )
    options_path = tmp_path / "options.json"
    options_path.write_text(json.dumps(options(), ensure_ascii=False), encoding="utf-8")
    return repository, options_path


@pytest.mark.parametrize(
    ("mixed", "expected_state"),
    [(False, "READY_TO_IMPLEMENT"), (True, "WAITING_FOR_SPEC_REVIEW")],
)
def test_answer_cli_persists_decision_freeze_and_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mixed: bool,
    expected_state: str,
) -> None:
    repository, options_path = _prepare_repository(tmp_path, monkeypatch, mixed=mixed)

    assert (
        main(
            [
                "answer",
                "TASK-0001",
                "--options-file",
                str(options_path),
                "--select",
                "OPT-02",
                "--actor",
                "operator",
                "--reason",
                "bounded choice",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "semantic exclusivity was not proven" in output
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == expected_state
    assert record.events[-1]["event_type"] == "ask_answered"
    assert record.events[-1]["payload"]["selected_option_id"] == "OPT-02"
    assert len(record.events[-1]["payload"]["options"]["options"]) == 2
    assert specification_is_current(repository, "TASK-0001") is True
    assert "OPT-02" in resolve_task_path(repository, "TASK-0001", "decisions.md").read_text(
        encoding="utf-8"
    )
    assert "## 已冻结决策" in resolve_task_path(repository, "TASK-0001", "spec.md").read_text(
        encoding="utf-8"
    )
    assert not resolve_task_path(repository, "TASK-0001", "answer_pending.json").exists()
    if not mixed:
        assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
        assert load_task_record(repository, "TASK-0001").task["current_state"] == "IMPLEMENTING"


def test_answer_cli_invalid_selection_has_no_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, options_path = _prepare_repository(tmp_path, monkeypatch)
    before = load_task_record(repository, "TASK-0001")
    spec_before = resolve_task_path(repository, "TASK-0001", "spec.md").read_text(encoding="utf-8")

    assert (
        main(
            [
                "answer",
                "TASK-0001",
                "--options-file",
                str(options_path),
                "--select",
                "OPT-99",
                "--actor",
                "operator",
                "--reason",
                "bounded choice",
            ]
        )
        == 1
    )
    after = load_task_record(repository, "TASK-0001")
    assert after.task == before.task and after.events == before.events
    assert (
        resolve_task_path(repository, "TASK-0001", "spec.md").read_text(encoding="utf-8")
        == spec_before
    )
    assert not resolve_task_path(repository, "TASK-0001", "decisions.md").exists()


def test_answer_cli_recovers_pending_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, options_path = _prepare_repository(tmp_path, monkeypatch)
    original = ask_service._persist_event_and_task

    def fail_once(*args: object, **kwargs: object) -> None:
        raise StorageError("injected", code="STORAGE_WRITE_FAILED")

    monkeypatch.setattr(ask_service, "_persist_event_and_task", fail_once)
    arguments = [
        "answer",
        "TASK-0001",
        "--options-file",
        str(options_path),
        "--select",
        "OPT-01",
        "--actor",
        "operator",
        "--reason",
        "bounded choice",
    ]
    assert main(arguments) == 1
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "WAITING_FOR_ASK"
    assert resolve_task_path(repository, "TASK-0001", "answer_pending.json").is_file()

    monkeypatch.setattr(ask_service, "_persist_event_and_task", original)
    assert main(arguments) == 0
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "READY_TO_IMPLEMENT"
    assert [event["event_type"] for event in record.events].count("ask_answered") == 1
    assert not resolve_task_path(repository, "TASK-0001", "answer_pending.json").exists()
