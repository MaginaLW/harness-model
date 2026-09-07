"""Integration coverage for the standalone read-only approval-overhead report."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = PROJECT_ROOT / "tools" / "analysis" / "approval_overhead.py"


@pytest.fixture(scope="module")
def overhead_module() -> Any:
    spec = importlib.util.spec_from_file_location("approval_overhead", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _approval(
    kind: str, *, actor: str = "owner", approved_at: str = "2026-09-01T00:00:00Z"
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "decision_unit_id": "DU-001",
        "approval_type": kind,
        "actor": actor,
        "reason": "recorded approval",
        "spec_sha256": "a" * 64,
        "policy_sha256": "b" * 64,
        "subject_commit": "c" * 40,
        "approved_at": approved_at,
    }
    if kind == "action":
        value.update(
            {"action_sha256": "d" * 64, "expires_at": "2026-10-01T00:00:00Z", "single_use": True}
        )
    return value


def _event(kind: str, *, sequence: int, state: str = "CLASSIFIED") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "sequence": sequence,
        "from_state": "NEW",
        "to_state": state,
        "event_type": kind,
        "actor": "owner",
        "occurred_at": "2026-09-01T00:00:00Z",
        "payload": {},
    }


def _ledger(root: Path) -> Path:
    directory = root / ".ai" / "tasks" / "TASK-0001"
    directory.mkdir(parents=True)
    (directory / "task.yaml").write_text(
        "task_id: TASK-0001\ncurrent_state: IMPLEMENTING\n", encoding="utf-8"
    )
    (directory / "classification.json").write_text(
        json.dumps({"task_id": "TASK-0001", "effective_route": "REVIEW"}), encoding="utf-8"
    )
    return directory


def test_report_counts_record_proxies_and_leaves_ledger_unchanged(
    tmp_path: Path, overhead_module: Any
) -> None:
    directory = _ledger(tmp_path)
    approvals = [
        _approval("spec"),
        _approval("action"),
        _approval("action", actor="another-owner", approved_at="2026-09-01T01:00:00Z"),
    ]
    (directory / "approvals.json").write_text(json.dumps(approvals), encoding="utf-8")
    events = [
        _event("task_created", sequence=1),
        _event("task_escalated", sequence=2, state="ESCALATED"),
        _event("verification_failed", sequence=3, state="FAILED"),
    ]
    (directory / "events.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    report = overhead_module.build_report(tmp_path)

    assert report["tasks"] == {
        "total": 1,
        "by_state": {"IMPLEMENTING": 1},
        "by_route": {"REVIEW": 1},
    }
    assert report["approvals"]["by_type"] == {"action": 2, "spec": 1}
    assert report["approvals"]["first_records"] == 2
    assert report["approvals"]["subsequent_records"] == 1
    assert report["approvals"]["same_binding_subsequent_records_by_type"] == {
        "action": 1,
        "spec": 0,
    }
    assert (
        report["approvals"]["by_task_decision_unit_type"][0]["same_binding_subsequent_records"] == 1
    )
    assert report["events"] == {
        "total": 3,
        "by_type": {"task_created": 1, "task_escalated": 1, "verification_failed": 1},
        "escalation_events": 1,
        "verification_failed_events": 1,
    }
    assert report["unavailable"] == {
        "human_interruptions": "unavailable",
        "human_review_time": "unavailable",
        "defect_escape_rate": "unavailable",
    }
    assert "do not prove redundant authorization" in report["limitations"][2]
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_report_rejects_corrupt_ledger_data(
    tmp_path: Path, overhead_module: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = _ledger(tmp_path)
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    (directory / "events.jsonl").write_text("not-json\n", encoding="utf-8")

    assert overhead_module.main([str(tmp_path), "--format", "json"]) == 2
    assert "TASK-0001/events.jsonl: invalid JSON at line 1" in capsys.readouterr().err


def test_report_accepts_unclassified_new_task(tmp_path: Path, overhead_module: Any) -> None:
    directory = _ledger(tmp_path)
    (directory / "classification.json").unlink()
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    (directory / "events.jsonl").write_text(
        json.dumps(_event("task_created", sequence=1)) + "\n", encoding="utf-8"
    )

    assert overhead_module.build_report(tmp_path)["tasks"]["by_route"] == {"not_available": 1}


@pytest.mark.parametrize("field", ["effective_route", "approval_type"])
def test_report_rejects_non_string_categories_without_traceback(
    tmp_path: Path,
    overhead_module: Any,
    capsys: pytest.CaptureFixture[str],
    field: str,
) -> None:
    directory = _ledger(tmp_path)
    approval = _approval("spec")
    if field == "effective_route":
        (directory / "classification.json").write_text(
            json.dumps({"task_id": "TASK-0001", "effective_route": []}), encoding="utf-8"
        )
    else:
        approval[field] = {}
    (directory / "approvals.json").write_text(json.dumps([approval]), encoding="utf-8")

    assert overhead_module.main([str(tmp_path)]) == 2
    assert f"{field} is invalid" in capsys.readouterr().err


def test_binding_counts_follow_approval_type_and_keep_action_limits(
    tmp_path: Path, overhead_module: Any
) -> None:
    directory = _ledger(tmp_path)
    spec = _approval("spec")
    code = {**_approval("code"), "evidence_sha256": "e" * 64}
    action = _approval("action")
    approvals = [
        spec,
        {**spec, "subject_commit": "f" * 40},
        code,
        {**code, "evidence_sha256": "f" * 64},
        action,
        {**action, "expires_at": "2026-11-01T00:00:00Z"},
    ]
    (directory / "approvals.json").write_text(json.dumps(approvals), encoding="utf-8")
    (directory / "events.jsonl").write_text(
        json.dumps(_event("task_created", sequence=1)) + "\n", encoding="utf-8"
    )

    assert overhead_module.build_report(tmp_path)["approvals"][
        "same_binding_subsequent_records_by_type"
    ] == {"action": 0, "code": 0, "spec": 1}
