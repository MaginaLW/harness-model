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


def _bootstrap_active_at_commit(root: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "show", f"{commit}:.ai/bootstrap-mode.yaml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode != 0:
        return False
    lines = result.stdout.splitlines()
    return "mode: bootstrap_auto" in lines and "status: active" in lines


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
    assert "timeout-minutes: 35" in text
    assert "fetch-depth: 0" in text
    assert 'python-version: "3.11"' in text
    assert "actions/checkout@v7" in text
    assert "actions/setup-python@v7" in text
    assert "astral-sh/setup-uv@v10.0.1" in text
    assert 'version: "0.12.5"' in text
    assert "uv lock --check" in text
    assert "uv sync --locked --all-extras" in text
    assert "uv run --locked python -m pytest" in text
    assert "retention-days: 14" in text
    assert "write" not in str(workflow["permissions"])


def test_resolved_task_output_flows_to_verify_and_gate() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    gate_command = (
        'uv run --locked python -m aiflow gate "$TASK_ID" '
        '--evidence "$run_dir/evidence.json" --format json'
    )

    assert "task_id=" in (ROOT / "tools" / "ci" / "resolve_task.py").read_text(encoding="utf-8")
    assert "TASK_ID: ${{ steps.task.outputs.task_id }}" in text
    assert 'uv run --locked python -m aiflow verify "$TASK_ID" --ci --ci-run-dir "$run_dir"' in text
    assert gate_command in text
    assert "${{ runner.temp }}/aiflow" in text


def test_bootstrap_mode_runs_quality_checks_without_self_governance() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    diff_cover_command = (
        'uv run --locked diff-cover "$RUNNER_TEMP/coverage.xml" '
        '--compare-branch "$BASE_SHA" --fail-under=90'
    )

    assert "mode: bootstrap_auto" in text
    assert "status: active" in text
    assert "BASE_SHA: ${{ github.event.pull_request.base.sha }}" in text
    assert 'git show "${BASE_SHA}:.ai/bootstrap-mode.yaml"' in text
    assert "bootstrap_active=true" in text
    assert "if: steps.governance.outputs.bootstrap_active == 'true'" in text
    assert text.count("if: steps.governance.outputs.bootstrap_active != 'true'") == 3
    assert 'COVERAGE_FILE="$RUNNER_TEMP/.coverage"' in text
    assert "--cov=aiflow --cov-branch --cov-fail-under=85" in text
    assert "--cov-report=term-missing" in text
    assert '--cov-report="xml:$RUNNER_TEMP/coverage.xml"' in text
    assert diff_cover_command in text
    assert 'git diff --check "$BASE_SHA..$HEAD_SHA"' in text
    assert "uv run --locked ruff check ." in text
    assert "uv run --locked ruff format --check ." in text
    assert "uv run --locked mypy" in text
    assert "always() && steps.governance.outputs.bootstrap_active != 'true'" in text


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        (None, False),
        ("mode: bootstrap_auto\nstatus: active\n", True),
        ("mode: bootstrap_auto\nstatus: disabled\n", False),
        ('mode: "bootstrap_auto"\nstatus: "active"\n', False),
    ],
)
def test_bootstrap_detection_is_canonical_and_fail_closed(
    tmp_path: Path, marker: str | None, expected: bool
) -> None:
    root, _ = _repo(tmp_path)
    if marker is not None:
        (root / ".ai" / "bootstrap-mode.yaml").write_text(marker, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "--allow-empty", "-m", "marker state")

    assert _bootstrap_active_at_commit(root, _git(root, "rev-parse", "HEAD")) is expected


def test_base_commit_controls_bootstrap_transition(tmp_path: Path) -> None:
    exiting, _ = _repo(tmp_path / "exit")
    exit_marker = exiting / ".ai" / "bootstrap-mode.yaml"
    exit_marker.write_text("mode: bootstrap_auto\nstatus: active\n", encoding="utf-8")
    _git(exiting, "add", "-A")
    _git(exiting, "commit", "-m", "activate bootstrap")
    active_base = _git(exiting, "rev-parse", "HEAD")
    exit_marker.unlink()
    _git(exiting, "add", "-A")
    _git(exiting, "commit", "-m", "exit bootstrap")
    exit_head = _git(exiting, "rev-parse", "HEAD")

    entering, inactive_base = _repo(tmp_path / "enter")
    (entering / ".ai" / "bootstrap-mode.yaml").write_text(
        "mode: bootstrap_auto\nstatus: active\n", encoding="utf-8"
    )
    _git(entering, "add", "-A")
    _git(entering, "commit", "-m", "attempt bootstrap")
    entering_head = _git(entering, "rev-parse", "HEAD")

    assert _bootstrap_active_at_commit(exiting, active_base) is True
    assert _bootstrap_active_at_commit(exiting, exit_head) is False
    assert _bootstrap_active_at_commit(entering, inactive_base) is False
    assert _bootstrap_active_at_commit(entering, entering_head) is True


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
