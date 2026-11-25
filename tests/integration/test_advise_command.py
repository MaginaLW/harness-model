"""Integration tests for the read-only non-scoring `aiflow advise` command."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from aiflow import verification_service
from aiflow.cli import main
from aiflow.storage import atomic_write_json, atomic_write_yaml, read_task_yaml, resolve_task_path
from aiflow.verification import (
    VerificationCheck,
    VerificationContext,
    VerificationExecution,
    VerificationPlan,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"


def _run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    return result.stdout.rstrip("\r\n")


def _create_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _run_git(path, "init", "-b", "main")
    ai_root = path / ".ai"
    ai_root.mkdir()
    for folder in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / folder, ai_root / folder)
    (ai_root / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _run_git(path, "add", ".ai", "tracked.txt")
    _run_git(
        path,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "initial",
    )
    return path


def _snapshot(root: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def _assert_advise_zero_writes(
    repository: Path,
    capsys: pytest.CaptureFixture[str],
    *,
    task_id: str = "TASK-0001",
    expected_state: str,
) -> dict[str, Any]:
    before = _snapshot(repository / ".ai")
    assert main(["advise", task_id, "--format", "json"]) == 0
    json_out = capsys.readouterr().out
    assert main(["advise", task_id]) == 0
    text_out = capsys.readouterr().out
    after = _snapshot(repository / ".ai")
    assert after == before

    payload = json.loads(json_out)
    assert payload["schema_version"] == "1.0"
    assert payload["design_version"] == "advisory-status-explanation-v0"
    assert payload["mode"] == "offline_advisory"
    assert payload["purpose"] == "offline_status_explanation"
    assert payload["probability_status"] == "unestimated"
    assert payload["execution_allowed"] is False
    assert payload["permission_effect"] == "none"
    assert payload["ledger_effect"] == "none"
    assert payload["lifecycle_state"] == expected_state
    assert f"State: {expected_state}" in text_out
    assert "execution_allowed=false" in text_out
    return payload


def _write_facts(tmp_path: Path, *, impact_level: str, route_flags: dict[str, Any]) -> Path:
    facts_file = tmp_path / f"facts-{impact_level}.json"
    facts = {
        "impact_categories": [],
        "controlled_actions": [],
        "external_side_effects": [],
        "impact": {"level": impact_level},
        "reversibility": "reversible",
        "scope": {"clear": True},
        "verification": {"automatic": True, "tools_missing": False},
        "change_characteristics": {
            "behavior_changed": route_flags["behavior_changed"],
            "code_modified": route_flags["code_modified"],
            "regression_risk": route_flags["regression_risk"],
            "interaction_scope": "local",
            "error_detectability": "high",
            "mechanical": route_flags["mechanical"],
        },
        "verification_requirements": {
            "integration_required": False,
            "acceptance_required": False,
            "independent_verifier_required": False,
            "targeted_mutation_required": False,
        },
    }
    facts_file.write_text(json.dumps(facts), encoding="utf-8")
    return facts_file


def _write_complete_spec(repository: Path, task_id: str) -> None:
    spec_path = resolve_task_path(repository, task_id, "spec.md")
    spec_path.write_text(
        "\n".join(
            [
                "# Task Specification",
                "",
                "## 目标",
                "Bounded change in tracked.txt",
                "",
                "## 范围",
                "- tracked.txt",
                "",
                "## 非目标",
                "- No policy edits",
                "",
                "## 验收条件",
                "- Automated verification check passes",
                "",
                "## 禁止动作",
                "- No push or delete",
                "",
                "## 错误行为",
                "- Fail closed on contract errors",
                "",
                "## 回滚",
                "- Revert tracked.txt commit",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _record_stage_review(
    repository: Path, tmp_path: Path, *, task_id: str, stage: str, review_id: str
) -> None:
    context_path = tmp_path / f"{stage}-context.json"
    assert (
        main(["review", "context", task_id, "--stage", stage, "--output", str(context_path)]) == 0
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    review_path = tmp_path / f"{stage}-review.json"
    review_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "review_id": review_id,
                "revision": 1,
                "task_id": task_id,
                "review_stage": stage,
                "reviewer": "independent-reviewer",
                "recorded_at": "2026-10-08T00:00:00Z",
                "context_sha256": context["context_sha256"],
                "outcome": "APPROVE",
                "summary": f"{stage} approved",
                "findings": [],
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "review",
                "record",
                task_id,
                "--input",
                str(review_path),
                "--actor",
                "independent-reviewer",
            ]
        )
        == 0
    )


def _pass_or_fail_plan(passed: bool) -> Any:
    def builder(_bundle: Any, context: VerificationContext, *, level: str) -> VerificationPlan:
        run_dir = (
            context.ci_run_dir.resolve()
            if context.ci_run_dir is not None
            else (
                context.repository_root
                / ".ai"
                / "tasks"
                / context.task_id
                / "logs"
                / context.run_id
            ).resolve()
        )
        argv = (
            sys.executable,
            "-c",
            "print('ok')" if passed else "import sys; sys.exit(1)",
        )
        check = VerificationCheck(
            "smoke",
            level,
            argv,
            {},
            context.repository_root.resolve(),
            10,
            True,
            "exit_zero",
        )
        execution = VerificationExecution("EXEC-001", argv, {}, check.cwd, 10, ("smoke",))
        return VerificationPlan(
            level,
            run_dir,
            (check,),
            (execution,),
            (),
            (),
            context.subject_commit,
        )

    return builder


def test_advise_across_review_lifecycle_and_deep_subdirectory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _create_repo(tmp_path / "repo")
    deep_dir = repository / "nested" / "sub"
    deep_dir.mkdir(parents=True)
    monkeypatch.chdir(repository)

    # 1. NEW
    assert main(["start", "--objective", "bounded review lifecycle", "--allow", "tracked.txt"]) == 0
    capsys.readouterr()
    new_rep = _assert_advise_zero_writes(repository, capsys, expected_state="NEW")
    assert [i["category"] for i in new_rep["advice_items"]] == ["continue_mechanical"]
    assert new_rep["bindings"]["policy_sha256"] is None

    # Verify deep-subdirectory invocation matches root output with zero chdir & zero writes
    root_json = json.dumps(new_rep, sort_keys=True)
    before = _snapshot(repository / ".ai")
    with monkeypatch.context() as mp:
        mp.chdir(deep_dir)
        mp.setattr(os, "chdir", lambda *_args: pytest.fail("CLI must never chdir"))
        assert main(["advise", "TASK-0001", "--format", "json"]) == 0
        deep_out = capsys.readouterr().out
        assert json.loads(deep_out) == json.loads(root_json)
        assert _snapshot(repository / ".ai") == before
        assert Path.cwd() == deep_dir

    # 2. Classify -> WAITING_FOR_SPEC_REVIEW
    _write_complete_spec(repository, "TASK-0001")
    facts = _write_facts(
        tmp_path,
        impact_level="medium",
        route_flags={
            "behavior_changed": True,
            "code_modified": True,
            "regression_risk": True,
            "mechanical": False,
        },
    )
    assert (
        main(
            [
                "facts",
                "TASK-0001",
                "--decision-unit",
                "DU-001",
                "--input",
                str(facts),
                "--actor",
                "planner",
            ]
        )
        == 0
    )
    assert main(["classify", "TASK-0001", "--actor", "planner"]) == 0
    assert main(["freeze", "TASK-0001", "--actor", "planner"]) == 0
    capsys.readouterr()

    spec_rev_rep = _assert_advise_zero_writes(
        repository, capsys, expected_state="WAITING_FOR_SPEC_REVIEW"
    )
    assert [(i["category"], i["condition"]) for i in spec_rev_rep["advice_items"]] == [
        ("continue_mechanical", "design_review"),
        ("residual_human_decision", "spec_approval"),
    ]
    assert spec_rev_rep["bindings"]["policy_sha256"] is not None
    assert spec_rev_rep["bindings"]["frozen_spec_sha256"] is not None

    # Record design review + spec approval -> READY_TO_IMPLEMENT
    _record_stage_review(
        repository, tmp_path, task_id="TASK-0001", stage="design", review_id="REV-0001"
    )
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "spec",
                "--actor",
                "project-owner",
                "--reason",
                "spec approved",
            ]
        )
        == 0
    )
    capsys.readouterr()
    ready_rep = _assert_advise_zero_writes(repository, capsys, expected_state="READY_TO_IMPLEMENT")
    assert [i["category"] for i in ready_rep["advice_items"]] == ["continue_mechanical"]

    # 3. IMPLEMENTING
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    capsys.readouterr()
    impl_rep = _assert_advise_zero_writes(repository, capsys, expected_state="IMPLEMENTING")
    assert [i["category"] for i in impl_rep["advice_items"]] == ["continue_mechanical"]

    # Out-of-scope dirty file -> stop_out_of_scope
    (repository / "unlisted.txt").write_text("oops\n", encoding="utf-8")
    oos_rep = _assert_advise_zero_writes(repository, capsys, expected_state="IMPLEMENTING")
    assert any(i["category"] == "stop_out_of_scope" for i in oos_rep["advice_items"])
    (repository / "unlisted.txt").unlink()

    # Make in-scope commit and sync
    (repository / "tracked.txt").write_text("updated\n", encoding="utf-8")
    _run_git(repository, "add", "tracked.txt")
    _run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "implement tracked change",
    )
    assert main(["sync", "TASK-0001", "--actor", "implementer"]) == 0
    capsys.readouterr()

    # 4. FAILED -> repair_in_scope
    monkeypatch.setattr(verification_service, "parse_verification_plan", _pass_or_fail_plan(False))
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    capsys.readouterr()
    failed_rep = _assert_advise_zero_writes(repository, capsys, expected_state="FAILED")
    assert failed_rep["advice_items"][0]["category"] == "repair_in_scope"

    # Retry & pass verify -> WAITING_FOR_FINAL_REVIEW
    assert (
        main(["begin", "TASK-0001", "--actor", "implementer", "--reason", "retry after fix"]) == 0
    )
    monkeypatch.setattr(verification_service, "parse_verification_plan", _pass_or_fail_plan(True))
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    capsys.readouterr()
    wait_final = _assert_advise_zero_writes(
        repository, capsys, expected_state="WAITING_FOR_FINAL_REVIEW"
    )
    assert [(i["category"], i["condition"]) for i in wait_final["advice_items"]] == [
        ("continue_mechanical", "implementation_review"),
        ("residual_human_decision", "code_approval"),
    ]

    # 5. APPROVED_FOR_MERGE (fresh) -> external_merge continue_mechanical
    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        "\n".join(
            [
                "# Review Package",
                "",
                "## 审核目标",
                "Approve bounded tracked.txt update.",
                "",
                "## 背景",
                "Integration verification of review lifecycle.",
                "",
                "## 代码地图",
                "- tracked.txt",
                "",
                "## 语义变更",
                "Updates tracked.txt within allowed_scope.",
                "",
                "## 风险",
                "Low risk; bounded to tracked.txt.",
                "",
                "## 证据",
                "已验证：Automated check passed；未验证：None.",
                "",
                "## 审核问题",
                "- Is tracked.txt within scope?",
                "",
                "## 推荐结论",
                "APPROVE",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _record_stage_review(
        repository, tmp_path, task_id="TASK-0001", stage="implementation", review_id="REV-0002"
    )
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "code",
                "--actor",
                "project-owner",
                "--reason",
                "code approved",
            ]
        )
        == 0
    )
    capsys.readouterr()
    approved_fresh = _assert_advise_zero_writes(
        repository, capsys, expected_state="APPROVED_FOR_MERGE"
    )
    assert approved_fresh["native_constraints"]["gate_passed"] is True
    assert approved_fresh["advice_items"][0]["category"] == "continue_mechanical"
    assert approved_fresh["advice_items"][0]["condition"] == "external_merge"

    # 6. APPROVED_FOR_MERGE (stale approvals) -> residual_human_decision + reverification
    approvals_path = resolve_task_path(repository, "TASK-0001", "approvals.json")
    original_approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
    stale_approvals = deepcopy(original_approvals)
    stale_approvals[-1]["subject_commit"] = "0" * 40
    atomic_write_json(approvals_path, stale_approvals)
    approved_stale = _assert_advise_zero_writes(
        repository, capsys, expected_state="APPROVED_FOR_MERGE"
    )
    assert approved_stale["native_constraints"]["gate_passed"] is False
    assert any(i["category"] == "residual_human_decision" for i in approved_stale["advice_items"])
    atomic_write_json(approvals_path, original_approvals)

    # 7. MERGED
    base_commit = approved_fresh["bindings"]["base_commit"]
    subject_commit = approved_fresh["bindings"]["subject_commit"]
    assert isinstance(base_commit, str) and isinstance(subject_commit, str)
    _run_git(repository, "checkout", "-b", "merge-target", base_commit)
    _run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "merge",
        "--no-ff",
        subject_commit,
        "-m",
        "merge task",
    )
    merge_commit = _run_git(repository, "rev-parse", "HEAD")
    _run_git(repository, "checkout", "main")
    assert (
        main(
            [
                "close",
                "TASK-0001",
                "--result",
                "merged",
                "--merge-commit",
                merge_commit,
                "--actor",
                "integrator",
            ]
        )
        == 0
    )
    capsys.readouterr()
    merged_rep = _assert_advise_zero_writes(repository, capsys, expected_state="MERGED")
    assert [(i["category"], i["condition"]) for i in merged_rep["advice_items"]] == [
        ("continue_mechanical", "merged")
    ]


def test_advise_waiting_for_ask_and_blocked_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _create_repo(tmp_path / "repo")
    monkeypatch.chdir(repository)

    # Create task with ASK route by modifying unit inputs after start -> WAITING_FOR_ASK
    assert main(["start", "--objective", "ask and block checks", "--allow", "tracked.txt"]) == 0
    _write_complete_spec(repository, "TASK-0001")
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"][0].update(
        {
            "impact_categories": [],
            "controlled_actions": [],
            "external_side_effects": [],
            "business_direction_count": 2,
            "impact": {"level": "low"},
            "reversibility": "reversible",
            "scope": {"clear": True},
            "verification": {"automatic": True, "tools_missing": False},
            "change_characteristics": {
                "behavior_changed": False,
                "code_modified": False,
                "regression_risk": False,
                "interaction_scope": "local",
                "error_detectability": "high",
                "mechanical": True,
            },
            "verification_requirements": {
                "integration_required": False,
                "acceptance_required": False,
                "independent_verifier_required": False,
                "targeted_mutation_required": False,
            },
        }
    )
    atomic_write_yaml(task_path, task)
    assert main(["classify", "TASK-0001", "--actor", "planner"]) == 0
    capsys.readouterr()

    ask_rep = _assert_advise_zero_writes(repository, capsys, expected_state="WAITING_FOR_ASK")
    assert [
        (i["category"], i["condition"], i["requires_human"]) for i in ask_rep["advice_items"]
    ] == [
        ("residual_human_decision", "ask_answer", True),
        ("continue_mechanical", "spec_frozen", False),
    ]

    # Escalate to BLOCK -> BLOCKED
    assert (
        main(
            [
                "escalate",
                "TASK-0001",
                "--to",
                "BLOCK",
                "--reason-code",
                "verification_unavailable",
                "--impact",
                "test runner offline",
                "--next-step",
                "restore runner",
                "--actor",
                "planner",
            ]
        )
        == 0
    )
    capsys.readouterr()
    blocked_rep = _assert_advise_zero_writes(repository, capsys, expected_state="BLOCKED")
    assert blocked_rep["advice_items"][0]["category"] == "repair_in_scope"
    assert blocked_rep["advice_items"][0]["condition"] == "block_resolution"


def test_advise_invalid_task_fails_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _create_repo(tmp_path / "repo")
    monkeypatch.chdir(repository)

    assert main(["advise", "TASK-9999", "--format", "json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    error_payload = json.loads(captured.err)
    assert "code" in error_payload
    assert "message" in error_payload
    assert not (repository / ".ai" / "tasks").exists()
