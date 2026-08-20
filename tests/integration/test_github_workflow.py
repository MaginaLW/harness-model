from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from aiflow.gate import GateFacts, evaluate_gate_facts
from tools.ci.resolve_task import resolve_task_id

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ai-quality-gate.yml"


def _workflow() -> dict[str, object]:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True, timeout=20
    )
    return result.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "checkout"
    root.mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.email", "ci@example.invalid")
    _git(root, "config", "user.name", "CI")
    (root / ".ai").mkdir()
    (root / ".ai" / "repository-id").write_text("repo-stable\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base")
    return root, _git(root, "rev-parse", "HEAD")


def test_workflow_is_read_only_reproducible_and_bounded() -> None:
    workflow = _workflow()
    text = WORKFLOW.read_text(encoding="utf-8")

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["on"]["pull_request"]["types"] == [
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
    ]
    assert "pull_request_target" not in text
    assert "cancel-in-progress: true" in text
    assert "timeout-minutes: 15" in text
    assert "fetch-depth: 0" in text
    assert 'python-version: "3.11"' in text
    assert 'python -m pip install ".[dev]"' in text
    assert "retention-days: 14" in text
    assert "write" not in str(workflow["permissions"])


def test_resolved_task_output_flows_to_verify_and_gate() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "task_id=" in (ROOT / "tools" / "ci" / "resolve_task.py").read_text(encoding="utf-8")
    assert "TASK_ID: ${{ steps.task.outputs.task_id }}" in text
    assert 'verify "$TASK_ID" --ci --ci-run-dir "$run_dir"' in text
    assert 'gate "$TASK_ID" --evidence "$run_dir/evidence.json" --format json' in text
    assert "${{ runner.temp }}/aiflow" in text


@pytest.mark.parametrize("count", [0, 1, 2])
def test_diff_task_resolution_requires_exactly_one(tmp_path: Path, count: int) -> None:
    root, base = _repo(tmp_path)
    for index in range(count):
        task = root / ".ai" / "tasks" / f"TASK-000{index + 1}"
        task.mkdir(parents=True)
        (task / "task.yaml").write_text("task\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--allow-empty", "-m", "head")
    head = _git(root, "rev-parse", "HEAD")

    if count == 1:
        assert resolve_task_id(root, base, head) == "TASK-0001"
    else:
        with pytest.raises(ValueError, match="exactly one"):
            resolve_task_id(root, base, head)


def test_explicit_task_depends_on_repository_identity_not_checkout_path(tmp_path: Path) -> None:
    first, base = _repo(tmp_path / "one")
    second, _ = _repo(tmp_path / "two")
    for root in (first, second):
        (root / ".ai" / "tasks" / "TASK-0001").mkdir(parents=True)

    assert resolve_task_id(first, base, base, "TASK-0001") == "TASK-0001"
    assert resolve_task_id(second, base, base, "TASK-0001") == "TASK-0001"
    assert first.resolve() != second.resolve()


def test_non_governance_tail_is_rejected_by_shared_gate() -> None:
    decision = evaluate_gate_facts(
        GateFacts(
            task_id="TASK-0001",
            current_state="APPROVED_FOR_MERGE",
            route="AUTO",
            verification_level="V0",
            scope_current=False,
        )
    )

    assert decision.passed is False
    assert "GATE_SCOPE_CHANGED" in decision.reason_codes
