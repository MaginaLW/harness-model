"""Bounded risk-facts persistence failures and exact recovery contracts."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_git_context import create_repository

from aiflow import task_service
from aiflow.cli import main
from aiflow.errors import AiflowError, StorageError
from aiflow.facts_service import record_risk_facts
from aiflow.state import create_record_event
from aiflow.storage import atomic_write_yaml, resolve_task_path
from aiflow.task_service import load_task_record, read_task_record_strict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DECLARATION = {"scope": {"clear": True}, "impact_categories": [], "controlled_actions": []}


@pytest.fixture
def draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> tuple[Path, Path]:
    repository = create_repository(tmp_path / "repository")
    for name in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / name, repository / ".ai" / name)
    monkeypatch.chdir(repository)
    assert main(["start", "--objective", "bounded facts", "--allow", "src/**"]) == 0
    path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = yaml.safe_load(path.read_text(encoding="utf-8"))
    second = deepcopy(task["decision_units"][0])
    second["decision_unit_id"] = "DU-002"
    task["decision_units"].append(second)
    atomic_write_yaml(path, task)
    source = repository / "facts.json"
    source.write_text(json.dumps(DECLARATION), encoding="utf-8")
    capsys.readouterr()
    return repository, source


def _apply(
    draft: tuple[Path, Path],
    *,
    actor: str = "declarer",
    unit: str = "DU-001",
    preview: bool = False,
) -> dict[str, Any]:
    repository, source = draft
    return record_risk_facts(
        repository,
        "TASK-0001",
        decision_unit_id=unit,
        input_path=source,
        actor=actor,
        dry_run=preview,
    )


def _artifacts(repository: Path) -> dict[str, bytes]:
    directory = resolve_task_path(repository, "TASK-0001")
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def _interrupt_replacement(draft: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    original = task_service._replace_materialized_task

    def fail(_staged: Path, _target: Path) -> None:
        raise OSError("simulated interrupted replacement")

    monkeypatch.setattr(task_service, "_replace_materialized_task", fail)
    with pytest.raises(StorageError):
        _apply(draft)
    monkeypatch.setattr(task_service, "_replace_materialized_task", original)


@pytest.mark.parametrize("equivalent_input", [None, "format", "unchanged_field"])
def test_exact_recovery_preserves_original_event_actor_and_timestamp(
    draft: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, equivalent_input: str | None
) -> None:
    repository, source = draft
    before = _artifacts(repository)
    _interrupt_replacement(draft, monkeypatch)
    interrupted = _artifacts(repository)
    assert interrupted["task.yaml"] == before["task.yaml"]
    assert "task.yaml.next" in interrupted
    events = [json.loads(line) for line in interrupted["events.jsonl"].splitlines()]
    assert len(events) == 2 and events[-1]["event_type"] == "risk_facts_recorded"
    if equivalent_input == "format":
        source.write_text(json.dumps(DECLARATION, indent=2, sort_keys=True), encoding="utf-8")
    elif equivalent_input == "unchanged_field":
        source.write_text(
            json.dumps({**DECLARATION, "reversibility": "reversible"}), encoding="utf-8"
        )
    replacements = []
    original = task_service._replace_materialized_task

    def replace(staged: Path, target: Path) -> None:
        replacements.append((staged, target))
        original(staged, target)

    monkeypatch.setattr(task_service, "_replace_materialized_task", replace)
    result = _apply(draft)
    assert result["changed"] is result["applied"] is result["recovered"] is True
    recovered = _artifacts(repository)
    assert len(replacements) == 1
    assert "task.yaml.next" not in recovered
    assert recovered["events.jsonl"] == interrupted["events.jsonl"]
    assert recovered["task.yaml"] == interrupted["task.yaml.next"]
    record = read_task_record_strict(repository, "TASK-0001")
    assert record.task["updated_at"] == events[-1]["occurred_at"]
    assert record.events[-1]["actor"] == "declarer"
    no_op = _apply(draft)
    assert no_op["changed"] is no_op["applied"] is no_op["recovered"] is False
    assert _artifacts(repository) == recovered


@pytest.mark.parametrize("failure", ["before", "partial", "after_complete"])
def test_uncertain_append_failures_preserve_staged_material_and_only_complete_event_recovers(
    draft: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    repository, _ = draft
    before = _artifacts(repository)
    original = task_service._append_event

    def fail(path: Path, event: dict[str, Any]) -> None:
        if failure == "partial":
            with path.open("ab") as stream:
                stream.write(b'{"incomplete":')
        elif failure == "after_complete":
            original(path, event)
        raise StorageError("uncertain append result", code="STATE_EVENT_APPEND_FAILED")

    monkeypatch.setattr(task_service, "_append_event", fail)
    with pytest.raises(StorageError):
        _apply(draft)
    monkeypatch.setattr(task_service, "_append_event", original)
    interrupted = _artifacts(repository)
    assert interrupted["task.yaml"] == before["task.yaml"]
    assert "task.yaml.next" in interrupted
    assert interrupted["events.jsonl"].startswith(before["events.jsonl"])
    if failure == "before":
        assert interrupted["events.jsonl"] == before["events.jsonl"]
    elif failure == "partial":
        assert interrupted["events.jsonl"].endswith(b'{"incomplete":')
    if failure == "after_complete":
        result = _apply(draft)
        assert result["recovered"] is True
        assert _artifacts(repository)["events.jsonl"] == interrupted["events.jsonl"]
    else:
        with pytest.raises(AiflowError):
            _apply(draft)
        assert _artifacts(repository) == interrupted


@pytest.mark.parametrize("reader", ["strict", "repairing", "classify", "preview"])
def test_pending_facts_are_not_repaired_or_classified_by_other_readers(
    draft: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    reader: str,
) -> None:
    repository, _ = draft
    _interrupt_replacement(draft, monkeypatch)
    before = _artifacts(repository)
    if reader == "classify":
        assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
        assert not capsys.readouterr().out
    else:
        with pytest.raises(AiflowError):
            if reader == "strict":
                read_task_record_strict(repository, "TASK-0001")
            elif reader == "repairing":
                load_task_record(repository, "TASK-0001")
            else:
                _apply(draft, preview=True)
    assert _artifacts(repository) == before


@pytest.mark.parametrize("reader", ["strict", "repairing", "classify", "facts"])
def test_recorded_but_unapplied_facts_without_next_block_stale_readers(
    draft: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    reader: str,
) -> None:
    repository, _ = draft
    _interrupt_replacement(draft, monkeypatch)
    resolve_task_path(repository, "TASK-0001", "task.yaml.next").unlink()
    before = _artifacts(repository)
    if reader == "classify":
        assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
        assert not capsys.readouterr().out
    else:
        with pytest.raises(AiflowError):
            if reader == "strict":
                read_task_record_strict(repository, "TASK-0001")
            elif reader == "repairing":
                load_task_record(repository, "TASK-0001")
            else:
                _apply(draft)
    assert _artifacts(repository) == before


@pytest.mark.parametrize(
    "mismatch",
    [
        "input",
        "actor",
        "unit",
        "staged_goal",
        "other_unit",
        "timestamp",
        "raw_goal",
        "invalid_staged",
        "event_actor",
        "event_before",
        "event_after",
        "event_task",
    ],
)
def test_recovery_refuses_mismatched_request_events_or_staged_metadata(
    draft: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    repository, source = draft
    _interrupt_replacement(draft, monkeypatch)
    directory = resolve_task_path(repository, "TASK-0001")
    if mismatch == "input":
        source.write_text('{"scope":{"clear":false}}', encoding="utf-8")
    elif mismatch in {"staged_goal", "other_unit", "timestamp", "raw_goal", "invalid_staged"}:
        path = directory / ("task.yaml" if mismatch == "raw_goal" else "task.yaml.next")
        task = yaml.safe_load(path.read_text(encoding="utf-8"))
        if mismatch in {"staged_goal", "raw_goal"}:
            task["goal"] = "unexpected metadata change"
        elif mismatch == "other_unit":
            task["decision_units"][1]["goal"] = "unexpected other unit change"
        elif mismatch == "timestamp":
            task["updated_at"] = "2026-01-01T00:00:00Z"
        else:
            task["unknown"] = True
        atomic_write_yaml(path, task)
    elif mismatch.startswith("event_"):
        path = directory / "events.jsonl"
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if mismatch == "event_actor":
            events[-1]["actor"] = "other"
        elif mismatch == "event_before":
            events[-1]["payload"]["before"]["reversibility"] = "irreversible"
        elif mismatch == "event_after":
            events[-1]["payload"]["after"]["scope"]["clear"] = False
        else:
            events[-1]["task_id"] = "TASK-0002"
        path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    before = _artifacts(repository)
    with pytest.raises(AiflowError):
        _apply(
            draft,
            actor="other" if mismatch == "actor" else "declarer",
            unit="DU-002" if mismatch == "unit" else "DU-001",
        )
    assert _artifacts(repository) == before


def test_recovery_replacement_failure_stays_retryable_without_new_events(
    draft: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _ = draft
    _interrupt_replacement(draft, monkeypatch)
    before = _artifacts(repository)
    original = task_service._replace_materialized_task

    def fail(_staged: Path, _target: Path) -> None:
        raise OSError("second replacement interruption")

    monkeypatch.setattr(task_service, "_replace_materialized_task", fail)
    with pytest.raises(StorageError):
        _apply(draft)
    assert _artifacts(repository) == before
    monkeypatch.setattr(task_service, "_replace_materialized_task", original)
    assert _apply(draft)["recovered"] is True
    assert _artifacts(repository)["events.jsonl"] == before["events.jsonl"]


def test_latest_declaration_for_each_unit_must_be_materialized_before_first_classification(
    draft: tuple[Path, Path],
) -> None:
    repository, _ = draft
    _apply(draft)
    _apply(draft, unit="DU-002")
    path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = yaml.safe_load(path.read_text(encoding="utf-8"))
    task["decision_units"][0]["scope"]["clear"] = False
    atomic_write_yaml(path, task)
    before = _artifacts(repository)
    for reader in (read_task_record_strict, load_task_record):
        with pytest.raises(AiflowError):
            reader(repository, "TASK-0001")
    assert _artifacts(repository) == before


def test_tasks_without_risk_fact_events_remain_compatible(draft: tuple[Path, Path]) -> None:
    repository, _ = draft
    before = _artifacts(repository)
    strict = read_task_record_strict(repository, "TASK-0001")
    assert strict == load_task_record(repository, "TASK-0001")
    assert len(strict.events) == 1 and strict.task["current_state"] == "NEW"
    assert _artifacts(repository) == before


def test_exact_subject_sync_staged_recovery_cannot_hide_unmaterialized_risk_facts(
    draft: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _ = draft
    _apply(draft)
    directory = resolve_task_path(repository, "TASK-0001")
    path = directory / "task.yaml"
    task = yaml.safe_load(path.read_text(encoding="utf-8"))
    task["decision_units"][0]["scope"]["clear"] = False
    atomic_write_yaml(path, task)
    event = create_record_event(
        task,
        event_type="subject_commit_synchronized",
        actor="sync",
        payload={
            "old_subject_commit": task["subject_commit"],
            "new_subject_commit": "2" * 40,
            "base_commit": task["base_commit"],
            "repository_id": task["repository_id"],
            "branch": task["branch"],
        },
        sequence=3,
    )
    staged = {**task, "subject_commit": "2" * 40, "updated_at": event["occurred_at"]}
    atomic_write_yaml(directory / "task.yaml.next", staged)
    task_service._append_event(directory / "events.jsonl", event)
    before = _artifacts(repository)
    replacements = []
    monkeypatch.setattr(
        task_service, "_replace_materialized_task", lambda *args: replacements.append(args)
    )
    with pytest.raises(AiflowError):
        load_task_record(repository, "TASK-0001")
    assert replacements == []
    assert _artifacts(repository) == before
