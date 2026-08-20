"""Integration coverage for explicit specification freezing."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_begin_close_commands import create_repository, start

from aiflow.cli import main
from aiflow.storage import resolve_task_path
from aiflow.task_service import (
    load_task_record,
    specification_is_current,
    transition_task_record,
)

VALID_SPEC = """# Task Specification

## 目标

交付一个可执行且有测试覆盖的规格冻结命令。

## 范围

仅修改当前任务允许的本地文件。

## 非目标

不执行外部动作。

## 验收条件

- 运行定向测试并得到通过结果。

## 禁止动作

不得推送、合并或部署。

## 错误行为

无效状态或不完整规格必须拒绝且不写事件。

## 回滚

恢复任务文件到冻结前版本并重新运行命令。
"""


def _move_from_new(repository: Path, target: str) -> None:
    if target == "NEW":
        return
    transition_task_record(
        repository,
        "TASK-0001",
        target_state="CLASSIFIED",
        event_type="classification_recorded",
        actor="classifier",
        payload={},
        satisfied_preconditions={"classification_available"},
    )
    if target == "CLASSIFIED":
        return
    event_type = {
        "WAITING_FOR_ASK": "ask_required",
        "WAITING_FOR_SPEC_REVIEW": "spec_review_required",
        "READY_TO_IMPLEMENT": "implementation_ready",
    }[target]
    transition_task_record(
        repository,
        "TASK-0001",
        target_state=target,
        event_type=event_type,
        actor="classifier",
        payload={},
        satisfied_preconditions={"classification_route_selected"},
    )


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    state: str = "NEW",
) -> Path:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    spec_path = resolve_task_path(repository, "TASK-0001", "spec.md")
    spec_path.write_bytes(VALID_SPEC.replace("\n", "\r\n").encode("utf-8"))
    _move_from_new(repository, state)
    return repository


@pytest.mark.parametrize(
    "state",
    ["NEW", "CLASSIFIED", "WAITING_FOR_SPEC_REVIEW", "READY_TO_IMPLEMENT"],
)
def test_freeze_records_digest_without_changing_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state=state)
    before = load_task_record(repository, "TASK-0001")

    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 0

    after = load_task_record(repository, "TASK-0001")
    assert after.task["current_state"] == state
    assert after.task["frozen_spec_sha256"] == after.events[-1]["payload"]["spec_sha256"]
    assert after.task["spec_frozen_at"] == after.events[-1]["occurred_at"]
    assert after.events[-1]["event_type"] == "spec_frozen"
    assert after.events[-1]["actor"] == "specifier"
    assert after.events[-1]["payload"]["normalized"] is True
    assert len(after.events) == len(before.events) + 1
    assert specification_is_current(repository, "TASK-0001") is True
    assert b"\r\n" not in resolve_task_path(repository, "TASK-0001", "spec.md").read_bytes()


def test_freeze_rejects_waiting_for_ask_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare(tmp_path, monkeypatch, state="WAITING_FOR_ASK")
    before = load_task_record(repository, "TASK-0001")

    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 1

    assert "current state" in capsys.readouterr().err.lower()
    after = load_task_record(repository, "TASK-0001")
    assert after.task == before.task
    assert after.events == before.events


def test_tamper_requires_explicit_refreeze(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 0
    first = load_task_record(repository, "TASK-0001")
    first_digest = first.task["frozen_spec_sha256"]

    spec_path = resolve_task_path(repository, "TASK-0001", "spec.md")
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace("本地文件", "仓库文件"),
        encoding="utf-8",
    )
    assert specification_is_current(repository, "TASK-0001") is False

    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 0
    second = load_task_record(repository, "TASK-0001")
    assert second.task["frozen_spec_sha256"] != first_digest
    assert second.events[-1]["payload"]["previous_spec_sha256"] == first_digest
    assert len(second.events) == len(first.events) + 1
    assert specification_is_current(repository, "TASK-0001") is True


def test_invalid_specification_does_not_append_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    spec_path = resolve_task_path(repository, "TASK-0001", "spec.md")
    spec_path.write_text(
        VALID_SPEC.replace("运行定向测试并得到通过结果。", "TODO"), encoding="utf-8"
    )
    before = load_task_record(repository, "TASK-0001")

    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 1

    assert "incomplete" in capsys.readouterr().err.lower()
    after = load_task_record(repository, "TASK-0001")
    assert after.task == before.task
    assert after.events == before.events
