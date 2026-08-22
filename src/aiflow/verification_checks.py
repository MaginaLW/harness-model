"""Thin CLI checks used by executable V0/V1 Policy commands."""

from __future__ import annotations

from pathlib import Path

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import ContractError
from aiflow.git_context import VerificationGitBinding, evaluate_verification_git_context
from aiflow.policy import load_policy_bundle
from aiflow.review_service import validate_review_artifacts
from aiflow.specification import validate_specification
from aiflow.storage import read_task_json, resolve_task_path
from aiflow.task_service import read_task_record_strict


def validate_task_artifacts(repository_root: Path, task_id: str) -> None:
    """Validate the strict task record and every governed artifact currently present."""
    root = repository_root.resolve()
    record = read_task_record_strict(root, task_id)
    parse_decision_units(record.task)
    load_policy_bundle(root)
    spec_path = resolve_task_path(root, task_id, "spec.md")
    validate_specification(spec_path.read_text(encoding="utf-8"))
    for filename, contract in (
        ("classification.json", "classification"),
        ("evidence.json", "evidence"),
    ):
        path = resolve_task_path(root, task_id, filename)
        if path.is_file():
            read_task_json(root, task_id, filename, contract_name=contract)
    approvals_path = resolve_task_path(root, task_id, "approvals.json")
    if approvals_path.is_file():
        approvals = read_task_json(root, task_id, "approvals.json")
        if not isinstance(approvals, list):
            raise ContractError("Task approvals are invalid", code="VALIDATE_ARTIFACT_INVALID")
        for approval in approvals:
            require_valid_contract("approval", approval)
    validate_review_artifacts(root, task_id)


def validate_task_scope(repository_root: Path, task_id: str) -> None:
    """Re-use the final verification Git assessment for the Policy scope check."""
    root = repository_root.resolve()
    task = read_task_record_strict(root, task_id).task
    allowed_scope = task.get("allowed_scope")
    fields = ("repository_id", "branch", "base_commit", "subject_commit")
    if (
        not isinstance(allowed_scope, list)
        or not all(isinstance(item, str) for item in allowed_scope)
        or not all(isinstance(task.get(field), str) for field in fields)
    ):
        raise ContractError("Task scope binding is invalid", code="SCOPE_BINDING_INVALID")
    assessment = evaluate_verification_git_context(
        root,
        task_id=task_id,
        allowed_scope=tuple(allowed_scope),
        binding=VerificationGitBinding(
            str(task["repository_id"]),
            str(task["branch"]),
            str(task["base_commit"]),
            str(task["subject_commit"]),
        ),
        mode="final",
    )
    if not assessment.gate_eligible:
        raise ContractError(
            "Task scope is not ready for final verification",
            code="SCOPE_CHECK_FAILED",
            details={"reason_codes": assessment.reason_codes},
        )
