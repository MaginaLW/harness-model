"""Verification orchestration across plan, runner, Git binding, evidence, and state."""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal, cast

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import AiflowError, ContractError
from aiflow.evidence import EvidenceFacts, build_evidence, save_evidence
from aiflow.freshness import current_classification_input_digest, evaluate_freshness
from aiflow.git_context import (
    VerificationGitAssessment,
    VerificationGitBinding,
    evaluate_verification_git_context,
)
from aiflow.policy import PolicyBundle, load_policy_bundle
from aiflow.process_runner import ProcessResult, run_execution
from aiflow.specification import specification_digest
from aiflow.storage import read_task_json, resolve_task_path
from aiflow.task_service import (
    TaskRecord,
    evaluate_and_sync_verification_subject,
    load_task_record,
    read_task_record_strict,
    transition_task_record,
)
from aiflow.verification import (
    VerificationCheck,
    VerificationContext,
    VerificationExecution,
    VerificationPlan,
    parse_verification_plan,
)

VersionProbe = Callable[[VerificationCheck], str]


@dataclass(frozen=True)
class VerifyResult:
    """One completed verification run and its externally useful outcome."""

    task_id: str
    conclusion: Literal["passed", "failed", "provisional"]
    state: str | None
    evidence_path: Path
    reason_codes: tuple[str, ...]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S%fZ")


def _default_version_probe(check: VerificationCheck) -> str:
    package = None
    if len(check.argv) >= 3 and check.argv[1] == "-m":
        package = check.argv[2].split(".", 1)[0]
    elif Path(check.argv[0]).name.startswith("diff-cover"):
        package = "diff-cover"
    if package == "aiflow":
        return "aiflow-local"
    if package is None:
        return f"{Path(check.argv[0]).name}:available"
    try:
        return f"{package}:{version(package)}"
    except PackageNotFoundError:
        return f"{package}:available"


def _read_spec(repository_root: Path, task_id: str) -> str:
    path = resolve_task_path(repository_root, task_id, "spec.md")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ContractError(
            "Frozen specification is unavailable", code="VERIFY_SPEC_STALE"
        ) from error


def _classification(repository_root: Path, task_id: str) -> dict[str, object]:
    value = read_task_json(
        repository_root, task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(value, dict):
        raise ContractError("Classification is unavailable", code="VERIFY_CLASSIFICATION_STALE")
    return value


def _require_fresh_inputs(
    repository_root: Path,
    record: TaskRecord,
    classification: Mapping[str, object],
    bundle: PolicyBundle,
    spec_sha256: str,
) -> None:
    task = record.task
    units = parse_decision_units(task)
    digest, synchronized = current_classification_input_digest(
        task, units, classification, record.events
    )
    current = {
        "task_id": task["task_id"],
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "policy_sha256": bundle.sha256,
        "classification_input_sha256": digest,
        "subject_synchronized": synchronized,
        "spec_sha256": spec_sha256,
    }
    if evaluate_freshness("classification", classification, current).status != "fresh":
        raise ContractError("Classification is stale", code="VERIFY_CLASSIFICATION_STALE")
    if task.get("frozen_spec_sha256") != spec_sha256:
        raise ContractError("Frozen specification is stale", code="VERIFY_SPEC_STALE")
    raw_classifications = classification.get("classifications")
    classifications = raw_classifications if isinstance(raw_classifications, list) else []
    review_ids = {
        str(entry["decision_unit_id"])
        for entry in classifications
        if isinstance(entry, Mapping) and entry.get("route") == "REVIEW"
    }
    if not review_ids:
        return
    approvals_path = resolve_task_path(repository_root, str(task["task_id"]), "approvals.json")
    if not approvals_path.is_file():
        raise ContractError("Specification approval is missing", code="VERIFY_APPROVAL_STALE")
    approvals = read_task_json(repository_root, str(task["task_id"]), "approvals.json")
    if not isinstance(approvals, list):
        raise ContractError("Specification approval is invalid", code="VERIFY_APPROVAL_STALE")
    current_approvals: set[str] = set()
    for approval in approvals:
        if not isinstance(approval, dict):
            continue
        try:
            require_valid_contract("approval", approval)
        except ContractError:
            continue
        if (
            approval.get("approval_type") == "spec"
            and evaluate_freshness("spec_approval", approval, current).status == "fresh"
        ):
            current_approvals.add(str(approval.get("decision_unit_id")))
    if not review_ids.issubset(current_approvals):
        raise ContractError("Specification approval is stale", code="VERIFY_APPROVAL_STALE")


def _ci_paths(ci_run_dir: Path | None, output: Path | None) -> tuple[Path, Path]:
    if ci_run_dir is None or output is None:
        raise ContractError("CI verification paths are required", code="CI_RUN_DIR_INVALID")
    root = ci_run_dir.resolve()
    target = output.resolve()
    if not root.is_dir() or target == root or target.parent != root:
        raise ContractError(
            "CI output must be a file in the run directory", code="CI_OUTPUT_INVALID"
        )
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ContractError("CI output escapes run directory", code="CI_OUTPUT_INVALID") from error
    return root, target


def _ci_git_assessment(
    repository_root: Path, task_id: str, record: TaskRecord
) -> VerificationGitAssessment:
    task = record.task
    allowed_scope = task.get("allowed_scope")
    if not isinstance(allowed_scope, list) or not all(
        isinstance(item, str) for item in allowed_scope
    ):
        raise ContractError("Task verification scope is invalid", code="VERIFY_BINDING_INVALID")
    fields = ("repository_id", "branch", "base_commit", "subject_commit")
    if not all(isinstance(task.get(field), str) for field in fields):
        raise ContractError("Task Git binding is invalid", code="VERIFY_BINDING_INVALID")
    assessment = evaluate_verification_git_context(
        repository_root,
        task_id=task_id,
        allowed_scope=tuple(allowed_scope),
        binding=VerificationGitBinding(
            repository_id=str(task["repository_id"]),
            branch=str(task["branch"]),
            base_commit=str(task["base_commit"]),
            subject_commit=str(task["subject_commit"]),
        ),
        mode="final",
    )
    if not assessment.gate_eligible:
        raise ContractError("CI Git verification context is stale", code="VERIFY_GIT_STALE")
    return assessment


def _selected_plan(plan: VerificationPlan, check_ids: Sequence[str]) -> VerificationPlan:
    selected_ids = tuple(dict.fromkeys(check_ids))
    if not selected_ids:
        return plan
    known = {check.check_id for check in plan.checks}
    if any(identifier not in known for identifier in selected_ids):
        raise ContractError("Verification check is unknown", code="VERIFY_CHECK_UNKNOWN")
    wanted = set(selected_ids)
    checks = tuple(check for check in plan.checks if check.check_id in wanted)
    executions: list[VerificationExecution] = []
    for execution in plan.executions:
        retained = tuple(identifier for identifier in execution.check_ids if identifier in wanted)
        if not retained:
            continue
        selected_checks = [check for check in checks if check.check_id in retained]
        executions.append(
            VerificationExecution(
                execution.execution_id,
                execution.argv,
                execution.environment,
                execution.cwd,
                max(check.timeout_seconds for check in selected_checks),
                retained,
            )
        )
    return VerificationPlan(
        plan.level,
        plan.run_dir,
        checks,
        tuple(executions),
        tuple(reason for reason in plan.blocking_reasons if reason.rsplit(":", 1)[-1] in wanted),
        tuple(identifier for identifier in plan.unverified_check_ids if identifier in wanted),
        plan.comparison_subject,
    )


def _execute_plan(
    repository_root: Path,
    plan: VerificationPlan,
) -> list[ProcessResult]:
    missing_ids = {
        reason.rsplit(":", 1)[-1]
        for reason in plan.blocking_reasons
        if reason.startswith("VERIFICATION_TOOL_MISSING:")
    }
    by_id = {check.check_id: check for check in plan.checks}
    results: list[ProcessResult] = []
    for sequence, execution in enumerate(plan.executions, start=1):
        if any(identifier in missing_ids for identifier in execution.check_ids):
            continue
        results.extend(
            run_execution(
                execution,
                by_id,
                run_dir=plan.run_dir,
                allowed_run_root=plan.run_dir.parent,
                repository_root=repository_root,
                sequence=sequence,
            )
        )
    return results


def _start_local_verification(
    repository_root: Path, task_id: str, record: TaskRecord, actor: str
) -> None:
    state = record.task.get("current_state")
    if state == "IMPLEMENTING":
        event_type = "verification_started"
        preconditions = {"implementation_complete"}
    elif state in {"VERIFIED", "WAITING_FOR_FINAL_REVIEW", "APPROVED_FOR_MERGE"}:
        event_type = "verification_restarted"
        preconditions = {"reverification_requested"}
    else:
        raise ContractError("Task is not ready for verification", code="VERIFY_STATE_INVALID")
    transition_task_record(
        repository_root,
        task_id,
        target_state="VERIFYING",
        event_type=event_type,
        actor=actor,
        payload={},
        satisfied_preconditions=preconditions,
    )


def _finish_local_verification(
    repository_root: Path,
    task_id: str,
    *,
    actor: str,
    conclusion: str,
    route: str,
) -> str:
    if conclusion == "provisional":
        result = transition_task_record(
            repository_root,
            task_id,
            target_state="IMPLEMENTING",
            event_type="verification_checked",
            actor=actor,
            payload={"conclusion": conclusion},
            satisfied_preconditions={"provisional_complete"},
        )
        return str(result.task["current_state"])
    passed = conclusion == "passed"
    first = transition_task_record(
        repository_root,
        task_id,
        target_state="VERIFIED" if passed else "FAILED",
        event_type="verification_passed" if passed else "verification_failed",
        actor=actor,
        payload={"conclusion": conclusion},
        satisfied_preconditions={"verification_passed" if passed else "verification_failed"},
    )
    if not passed:
        return str(first.task["current_state"])
    review = route == "REVIEW"
    result = transition_task_record(
        repository_root,
        task_id,
        target_state="WAITING_FOR_FINAL_REVIEW" if review else "APPROVED_FOR_MERGE",
        event_type="final_review_required" if review else "merge_approved_automatically",
        actor=actor,
        payload={},
        satisfied_preconditions={
            "final_review_required" if review else "final_review_not_required"
        },
    )
    return str(result.task["current_state"])


def verify_task(
    repository_root: Path,
    task_id: str,
    *,
    actor: str | None = None,
    check_ids: Sequence[str] = (),
    run_id: str | None = None,
    ci: bool = False,
    ci_run_dir: Path | None = None,
    output: Path | None = None,
    version_probe: VersionProbe = _default_version_probe,
) -> VerifyResult:
    """Execute one governed local verification or read-only CI attestation."""
    root = repository_root.resolve()
    record = read_task_record_strict(root, task_id) if ci else load_task_record(root, task_id)
    state = str(record.task.get("current_state"))
    if ci:
        if state not in {"VERIFIED", "WAITING_FOR_FINAL_REVIEW", "APPROVED_FOR_MERGE"}:
            raise ContractError(
                "Task is not ready for CI verification", code="VERIFY_STATE_INVALID"
            )
        run_directory, evidence_path = _ci_paths(ci_run_dir, output)
    else:
        if actor is None or not actor.strip():
            raise ContractError("Verification actor is required", code="VERIFY_ACTOR_REQUIRED")
        run_directory = Path()
        evidence_path = resolve_task_path(root, task_id, "evidence.json")

    classification = _classification(root, task_id)
    bundle = load_policy_bundle(root)
    spec_sha256 = specification_digest(_read_spec(root, task_id))
    _require_fresh_inputs(root, record, classification, bundle, spec_sha256)

    if ci:
        assessment = _ci_git_assessment(root, task_id, record)
        identifier = run_directory.name
        subject_commit = assessment.subject_commit
    else:
        assessment = evaluate_and_sync_verification_subject(
            root,
            task_id,
            mode="provisional" if check_ids else "final",
            actor=cast(str, actor),
        )
        if not check_ids and not assessment.gate_eligible:
            raise ContractError("Git verification context is stale", code="VERIFY_GIT_STALE")
        record = load_task_record(root, task_id)
        _require_fresh_inputs(root, record, classification, bundle, spec_sha256)
        identifier = run_id or _run_id()
        subject_commit = assessment.subject_commit

    level = classification.get("effective_verification_level")
    if level not in {"V0", "V1"}:
        raise ContractError("Verification level is invalid", code="VERIFY_LEVEL_INVALID")
    context = VerificationContext(
        root,
        task_id,
        str(record.task["base_commit"]),
        subject_commit,
        sys.executable,
        identifier,
        run_directory if ci else None,
    )
    full_plan = parse_verification_plan(bundle, context, level=cast(Literal["V0", "V1"], level))
    plan = _selected_plan(full_plan, check_ids)
    if not ci:
        _start_local_verification(root, task_id, record, cast(str, actor))
    results = _execute_plan(root, plan)
    versions = {check.check_id: version_probe(check) for check in plan.checks}
    provisional = bool(check_ids)
    reproduce_command = (
        (
            "python",
            "-m",
            "aiflow",
            "verify",
            task_id,
            "--ci",
            "--ci-run-dir",
            str(run_directory),
            "--output",
            str(evidence_path),
        )
        if ci
        else (
            "python",
            "-m",
            "aiflow",
            "verify",
            task_id,
            "--actor",
            cast(str, actor),
            *(argument for check_id in check_ids for argument in ("--check", check_id)),
        )
    )
    facts = EvidenceFacts(
        task_id,
        tuple(str(unit["decision_unit_id"]) for unit in record.task["decision_units"]),
        str(record.task["repository_id"]),
        str(record.task["branch"]),
        str(record.task["base_commit"]),
        subject_commit,
        spec_sha256,
        bundle.sha256,
        str(classification["classification_input_sha256"]),
        cast(Literal["V0", "V1"], level),
        "ci" if ci else "local",
        identifier,
        plan.run_dir,
        _now(),
        reproduce_command,
        assessment.attestation_head if ci else None,
        (assessment.attestation_scope.passed and assessment.worktree_scope.passed) if ci else None,
    )
    evidence = build_evidence(
        facts,
        plan.checks,
        results,
        tool_versions=versions,
        unverified_scenarios=(*plan.unverified_check_ids, *plan.blocking_reasons),
        provisional=provisional,
    )
    try:
        save_evidence(
            evidence_path,
            evidence,
            archive_path=plan.run_dir / "evidence.json" if not ci else None,
        )
    except AiflowError:
        if not ci:
            transition_task_record(
                root,
                task_id,
                target_state="FAILED",
                event_type="verification_failed",
                actor=cast(str, actor),
                payload={"conclusion": "failed", "reason_code": "EVIDENCE_WRITE_FAILED"},
                satisfied_preconditions={"verification_failed"},
            )
        raise
    conclusion = cast(Literal["passed", "failed", "provisional"], evidence["conclusion"])
    final_state = None
    if not ci:
        final_state = _finish_local_verification(
            root,
            task_id,
            actor=cast(str, actor),
            conclusion=conclusion,
            route=str(classification["effective_route"]),
        )
    raw_checks = evidence.get("checks")
    evidence_checks = raw_checks if isinstance(raw_checks, list) else []
    reasons = tuple(
        sorted(
            {
                str(check["reason_code"])
                for check in evidence_checks
                if isinstance(check, Mapping) and check.get("reason_code")
            }
        )
    )
    return VerifyResult(task_id, conclusion, final_state, evidence_path, reasons)
