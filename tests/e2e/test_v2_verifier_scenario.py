"""Real-service replay of the V2 pre-review/final-evidence handshake."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scenario_support import TASK_ID, complete_spec, prepare_task, review_package

from aiflow import verification_service
from aiflow.cli import main
from aiflow.evidence import prepare_v2_pre_evidence
from aiflow.gate import evaluate_gate
from aiflow.policy import load_policy_bundle
from aiflow.storage import (
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record
from aiflow.verifier_service import build_verifier_context, save_verifier_context


def _record_approving_review(
    repository: Path, stage: str, review_id: str, tmp_path: Path
) -> dict[str, object]:
    context_path = tmp_path / f"{review_id}-context.json"
    assert (
        main(["review", "context", TASK_ID, "--stage", stage, "--output", str(context_path)]) == 0
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    assert isinstance(context, dict)
    record_path = tmp_path / f"{review_id}.json"
    atomic_write_json(
        record_path,
        {
            "schema_version": "1.0",
            "review_id": review_id,
            "review_stage": stage,
            "recorded_at": "2026-08-23T05:00:00Z",
            "context_sha256": context["context_sha256"],
            "outcome": "APPROVE",
            "summary": "V2 fixture review is approvable.",
            "findings": [],
        },
    )
    assert (
        main(["review", "record", TASK_ID, "--input", str(record_path), "--actor", "reviewer"]) == 0
    )
    return context


def _passed_v2_pre(repository: Path, design_context: dict[str, object]) -> dict[str, object]:
    task = load_task_record(repository, TASK_ID).task
    classification = read_task_json(
        repository, TASK_ID, "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    bundle = load_policy_bundle(repository)
    levels = bundle.documents["verification-levels.yaml"]["levels"]
    v2 = next(level for level in levels if level["id"] == "V2")
    context = build_verifier_context(repository, TASK_ID)
    save_verifier_context(repository, TASK_ID, context)
    evidence = {
        "schema_version": "2.0",
        "task_id": TASK_ID,
        "decision_unit_ids": ["DU-103"],
        "repository_id": task["repository_id"],
        "branch": task["branch"],
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "spec_sha256": task["frozen_spec_sha256"],
        "policy_sha256": bundle.sha256,
        "classification_input_sha256": classification["classification_input_sha256"],
        "verification_level": "V2",
        "mode": "local",
        "checks": [
            {
                "check_id": check["id"],
                "category": check["id"],
                "status": "passed",
                "reason_code": None,
                "required": True,
                "exit_code": 0,
                "timed_out": False,
                "duration_ms": 0,
                "stdout_log_ref": None,
                "stderr_log_ref": None,
                "command_summary": "deterministic fixture",
                "tool_version": "fixture",
            }
            for check in v2["checks"]
        ],
        "unverified_scenarios": [],
        "conclusion": "passed",
        "generated_at": "2026-08-23T05:00:00Z",
        "reproduce_command": ["python", "-m", "aiflow", "verify", TASK_ID, "--actor", "verifier"],
        "verifier_actor": "verifier",
        "verifier_context_sha256": context["context_sha256"],
        "review_refs": {
            "design": {"review_id": "REV-1001", "context_sha256": design_context["context_sha256"]}
        },
        "targeted_mutation": {
            "manifest_ref": "tests/mutations.json",
            "results": [{"mutation_id": "MUT-001", "outcome": "killed", "log_ref": None}],
        },
    }
    return prepare_v2_pre_evidence(evidence)


def test_v2_pre_review_finalize_replay_is_runner_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, unit, _expected = prepare_task(tmp_path, monkeypatch, "review-workflow-change")
    unit["verification_requirements"] = {
        "acceptance_required": False,
        "integration_required": False,
        "targeted_mutation_required": False,
        "independent_verifier_required": True,
    }
    task_path = resolve_task_path(repository, TASK_ID, "task.yaml")
    task = read_task_yaml(repository, TASK_ID, "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [unit]
    atomic_write_yaml(task_path, task)
    resolve_task_path(repository, TASK_ID, "spec.md").write_text(
        complete_spec(unit), encoding="utf-8"
    )

    assert main(["classify", TASK_ID, "--actor", "classifier"]) == 0
    assert main(["freeze", TASK_ID, "--actor", "specifier"]) == 0
    design_context = _record_approving_review(repository, "design", "REV-1001", tmp_path)
    assert (
        main(["approve", TASK_ID, "--type", "spec", "--actor", "reviewer", "--reason", "approved"])
        == 0
    )
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 0

    pre = _passed_v2_pre(repository, design_context)
    atomic_write_json(resolve_task_path(repository, TASK_ID, "evidence.json"), pre)
    verification_service._start_local_verification(
        repository, TASK_ID, load_task_record(repository, TASK_ID), "verifier"
    )
    assert (
        verification_service._finish_local_verification(
            repository,
            TASK_ID,
            actor="verifier",
            conclusion="passed",
            route="REVIEW",
        )
        == "WAITING_FOR_FINAL_REVIEW"
    )
    _record_approving_review(repository, "implementation", "REV-1002", tmp_path)
    snapshot = pre["verification_snapshot_sha256"]

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("finalize must not parse or execute verification")

    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)
    result = verification_service.verify_task(repository, TASK_ID, actor="verifier", finalize=True)

    final = read_task_json(repository, TASK_ID, "evidence.json", contract_name="evidence")
    assert result.conclusion == "passed"
    assert final["phase"] == "final"
    assert final["verification_snapshot_sha256"] == snapshot
    assert final["review_refs"]["implementation"]["review_id"] == "REV-1002"
    resolve_task_path(repository, TASK_ID, "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    assert (
        main(
            [
                "approve",
                TASK_ID,
                "--type",
                "code",
                "--actor",
                "reviewer",
                "--reason",
                "V2 final evidence approved",
            ]
        )
        == 0
    )
    assert evaluate_gate(repository, TASK_ID).passed is True

    context_path = resolve_task_path(
        repository,
        TASK_ID,
        Path("verifier-contexts") / f"{final['verifier_context_sha256']}.json",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    context["content"]["goal"] = "tampered"
    context_path.write_text(json.dumps(context), encoding="utf-8")
    assert "GATE_V2_CONTEXT_STALE" in evaluate_gate(repository, TASK_ID).reason_codes
