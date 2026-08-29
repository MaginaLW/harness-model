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
from aiflow.evidence import (
    EvidenceFacts,
    build_evidence,
    finalize_v2_evidence,
    prepare_v2_pre_evidence,
    save_evidence,
    validate_v2_snapshot,
)
from aiflow.freshness import current_classification_input_digest, evaluate_freshness
from aiflow.git_context import (
    VerificationGitAssessment,
    VerificationGitBinding,
    evaluate_verification_git_context,
)
from aiflow.mutation_evidence import (
    TargetedMutationFacts,
    consume_targeted_mutation_evidence,
    record_targeted_mutation_evidence,
)
from aiflow.policy import PolicyBundle, load_policy_bundle
from aiflow.process_runner import ProcessResult, run_execution
from aiflow.review_service import ReviewAssessment, latest_review_assessment
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
    V1_CHECK_IDS,
    V2_EXTRA_CHECK_IDS,
    VerificationCheck,
    VerificationContext,
    VerificationExecution,
    VerificationPlan,
    parse_verification_plan,
)
from aiflow.verifier_service import (
    build_verifier_context,
    current_implementer_actor,
    load_verifier_context,
    save_verifier_context,
    validate_verifier_actor,
    validate_verifier_context_current,
)

VersionProbe = Callable[[VerificationCheck], str]
_V2_CHAPTER11_CHECK_IDS = frozenset({"targeted_mutation"})


@dataclass(frozen=True)
class VerifyResult:
    """One completed verification run and its externally useful outcome."""

    task_id: str
    conclusion: Literal["passed", "failed", "provisional"]
    state: str | None
    evidence_path: Path
    reason_codes: tuple[str, ...]


def _v2_targeted_mutation_artifact(
    repository_root: Path, task_id: str, subject_commit: str
) -> TargetedMutationFacts:
    """Collect once, then replay the exact immutable task-bound artifact.

    The caller is the frozen production seam.  The recorder itself atomically
    consumes and revalidates the separately approved single-use action before
    its fixed runner call, so direct recorder use cannot bypass authorization.
    """
    recorded = record_targeted_mutation_evidence(repository_root, task_id, subject_commit)
    facts = consume_targeted_mutation_evidence(
        repository_root, task_id, {}, recorded_artifact=recorded
    )
    return facts


def _missing_mutation_projection(task_id: str) -> dict[str, object]:
    """Return a schema-shaped sentinel that the public consumer rejects."""
    return {
        "evidence_ref": (
            f".ai/tasks/{task_id}/logs/MUTRUN-19700101T000000Z-0000000000000000/"
            "targeted-mutation/evidence.json"
        ),
        "mutation_evidence_sha256": "0" * 64,
        "manifest_ref": ".ai/mutations/phase-02-critical-manifest.json",
        "results": [
            {"mutation_id": f"MUT-V2-{index:03d}", "outcome": "unverified", "log_ref": None}
            for index in range(1, 6)
        ],
    }


def _targeted_mutation_projection(
    repository_root: Path,
    task_id: str,
    subject_commit: str,
    *,
    collect: bool,
) -> tuple[dict[str, object], TargetedMutationFacts]:
    """Return a schema-valid projection plus loader-backed fail-closed facts."""
    if not collect:
        projection = _missing_mutation_projection(task_id)
        return projection, TargetedMutationFacts(
            False,
            "MUTATION_EVIDENCE_MISSING",
            str(projection["evidence_ref"]),
            str(projection["mutation_evidence_sha256"]),
            str(projection["manifest_ref"]),
            tuple(cast(list[Mapping[str, object]], projection["results"])),
        )
    try:
        facts = _v2_targeted_mutation_artifact(repository_root, task_id, subject_commit)
    except AiflowError as error:
        projection = _missing_mutation_projection(task_id)
        return projection, TargetedMutationFacts(
            False,
            error.code if error.code.startswith("ACTION_") else "MUTATION_EVIDENCE_INVALID",
            str(projection["evidence_ref"]),
            str(projection["mutation_evidence_sha256"]),
            str(projection["manifest_ref"]),
            tuple(cast(list[Mapping[str, object]], projection["results"])),
        )
    if (
        not isinstance(facts.evidence_ref, str)
        or not isinstance(facts.mutation_evidence_sha256, str)
        or not isinstance(facts.manifest_ref, str)
        or len(facts.results) != 5
    ):
        projection = _missing_mutation_projection(task_id)
    else:
        projection = {
            "evidence_ref": facts.evidence_ref,
            "mutation_evidence_sha256": facts.mutation_evidence_sha256,
            "manifest_ref": facts.manifest_ref,
            "results": [dict(item) for item in facts.results],
        }
    return projection, facts


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


def _empty_plan(plan: VerificationPlan) -> VerificationPlan:
    return VerificationPlan(
        plan.level,
        plan.run_dir,
        (),
        (),
        (),
        (),
        plan.comparison_subject,
    )


def _v2_plans(
    plan: VerificationPlan, check_ids: Sequence[str]
) -> tuple[VerificationPlan, tuple[VerificationCheck, ...]]:
    """Execute V1 plus runnable V2 checks, retaining pending mutation evidence."""
    selected_ids = tuple(dict.fromkeys(check_ids))
    known = {check.check_id for check in plan.checks}
    if any(identifier not in known for identifier in selected_ids):
        raise ContractError("Verification check is unknown", code="VERIFY_CHECK_UNKNOWN")
    default_ids = (*V1_CHECK_IDS, "acceptance", "integration")
    runnable_ids = frozenset((*V1_CHECK_IDS, "acceptance", "integration"))
    executable_ids = tuple(
        identifier
        for identifier in (selected_ids or default_ids)
        if identifier in known and identifier in runnable_ids
    )
    execution_plan = _selected_plan(plan, executable_ids) if executable_ids else _empty_plan(plan)
    evidence_ids = set(executable_ids) | set(V2_EXTRA_CHECK_IDS)
    evidence_checks = tuple(check for check in plan.checks if check.check_id in evidence_ids)
    return execution_plan, evidence_checks


def _review_ref(assessment: ReviewAssessment) -> dict[str, str]:
    return {
        "review_id": str(assessment.record["review_id"]),
        "context_sha256": str(assessment.context["context_sha256"]),
    }


def _independent_verifier_result() -> ProcessResult:
    observed_at = _now()
    return ProcessResult(
        "ROLE-CHECK",
        "independent_verifier",
        (
            "task-local implementer and verifier actor labels differ; "
            "external identity is not authenticated"
        ),
        observed_at,
        observed_at,
        0,
        0,
        False,
        "",
        "",
        "passed",
        None,
    )


def _upgrade_v2_pre_evidence(
    evidence: dict[str, object],
    *,
    mutation_projection: Mapping[str, object],
    mutation_facts: TargetedMutationFacts,
    verifier_actor: str,
    verifier_context_sha256: str,
    design_review: ReviewAssessment,
    provisional_check_ids: Sequence[str] = (),
) -> dict[str, object]:
    raw_checks = evidence.get("checks")
    checks = raw_checks if isinstance(raw_checks, list) else []
    for check in checks:
        if not isinstance(check, dict) or check.get("check_id") not in _V2_CHAPTER11_CHECK_IDS:
            continue
        check.update(
            {
                "status": "passed" if mutation_facts.passed else "failed",
                "reason_code": mutation_facts.reason_code,
                "exit_code": 0 if mutation_facts.passed else 1,
                "timed_out": False,
                "duration_ms": 0,
                "stdout_log_ref": None,
                "stderr_log_ref": None,
                "command_summary": "loader-validated targeted mutation evidence",
                "tool_version": "aiflow-mutation-evidence-v1",
            }
        )
    raw_unverified = evidence.get("unverified_scenarios")
    unverified_values = raw_unverified if isinstance(raw_unverified, list) else []
    unverified = {
        str(reason)
        for reason in unverified_values
        if not any(f"check:{identifier}:" in str(reason) for identifier in _V2_CHAPTER11_CHECK_IDS)
    }
    if not mutation_facts.passed:
        unverified.add(
            f"check:targeted_mutation:{mutation_facts.reason_code or 'MUTATION_EVIDENCE_INVALID'}"
        )
    # A selected V2 check is deliberately a partial, non-gating observation.  Its
    # conclusion may be provisional only when every selected check really passed
    # and the independent-verifier role fact is present.  In particular, do not
    # let the pending Chapter 11 mutation (or another unselected real check)
    # conceal a selected check failure.
    by_id = {
        str(check.get("check_id")): check
        for check in checks
        if isinstance(check, dict) and isinstance(check.get("check_id"), str)
    }
    selected_complete = bool(provisional_check_ids) and all(
        isinstance(by_id.get(check_id), dict) and by_id[check_id].get("status") == "passed"
        for check_id in provisional_check_ids
    )
    independent_verifier = by_id.get("independent_verifier")
    role_fact_complete = (
        isinstance(independent_verifier, dict) and independent_verifier.get("status") == "passed"
    )
    required_complete = bool(checks) and all(
        check.get("required") is not True or check.get("status") == "passed"
        for check in checks
        if isinstance(check, dict)
    )
    conclusion = (
        "provisional"
        if (
            provisional_check_ids
            and selected_complete
            and role_fact_complete
            and mutation_facts.passed
        )
        else "passed"
        if not provisional_check_ids and required_complete
        else "failed"
    )
    evidence.update(
        {
            "schema_version": "2.0",
            "verification_level": "V2",
            "unverified_scenarios": sorted(unverified),
            "conclusion": conclusion,
            "verifier_actor": verifier_actor,
            "verifier_context_sha256": verifier_context_sha256,
            "review_refs": {"design": _review_ref(design_review)},
            "targeted_mutation": dict(mutation_projection),
        }
    )
    return prepare_v2_pre_evidence(evidence)


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


def _finalize_v2_task(
    repository_root: Path,
    task_id: str,
    *,
    actor: str | None,
    check_ids: Sequence[str],
    ci: bool,
    ci_run_dir: Path | None,
    output: Path | None,
) -> VerifyResult:
    if ci or check_ids or ci_run_dir is not None or output is not None:
        raise ContractError(
            "V2 finalization cannot run checks or CI verification",
            code="VERIFY_FINALIZE_ARGUMENT_INVALID",
        )
    root = repository_root.resolve()
    record = load_task_record(root, task_id)
    classification = _classification(root, task_id)
    bundle = load_policy_bundle(root)
    spec_sha256 = specification_digest(_read_spec(root, task_id))
    _require_fresh_inputs(root, record, classification, bundle, spec_sha256)
    if classification.get("effective_verification_level") != "V2":
        raise ContractError(
            "Finalization requires V2 verification", code="VERIFY_FINALIZE_LEVEL_INVALID"
        )
    _ci_git_assessment(root, task_id, record)
    implementer = current_implementer_actor(record.events)
    _implementer, verifier = validate_verifier_actor(implementer, actor or "")
    evidence_path = resolve_task_path(root, task_id, "evidence.json")
    if not evidence_path.is_file():
        raise ContractError("V2 pre evidence is missing", code="VERIFY_FINALIZE_EVIDENCE_INVALID")
    evidence = read_task_json(root, task_id, "evidence.json", contract_name="evidence")
    if not isinstance(evidence, dict):
        raise ContractError("V2 pre evidence is invalid", code="VERIFY_FINALIZE_EVIDENCE_INVALID")
    if (
        evidence.get("schema_version") != "2.0"
        or evidence.get("verification_level") != "V2"
        or evidence.get("phase") != "pre_implementation_review"
        or evidence.get("mode") != "local"
    ):
        raise ContractError("V2 pre evidence is invalid", code="VERIFY_FINALIZE_EVIDENCE_INVALID")
    if evidence.get("verifier_actor") != verifier:
        raise ContractError("Verifier actor is stale", code="VERIFY_FINALIZE_ACTOR_STALE")
    validate_v2_snapshot(evidence)
    current = {
        "task_id": task_id,
        "repository_id": record.task.get("repository_id"),
        "branch": record.task.get("branch"),
        "base_commit": record.task.get("base_commit"),
        "subject_commit": record.task.get("subject_commit"),
        "policy_sha256": bundle.sha256,
        "spec_sha256": spec_sha256,
        "classification_input_sha256": classification.get("classification_input_sha256"),
        "verification_level": "V2",
    }
    if evaluate_freshness("evidence", evidence, current).status != "fresh":
        raise ContractError("V2 pre evidence is stale", code="VERIFY_FINALIZE_EVIDENCE_STALE")
    context_digest = evidence.get("verifier_context_sha256")
    if not isinstance(context_digest, str):
        raise ContractError("Verifier context is invalid", code="VERIFY_FINALIZE_CONTEXT_INVALID")
    stored_context = load_verifier_context(root, task_id, context_digest)
    current_context = build_verifier_context(root, task_id)
    validate_verifier_context_current(stored_context, current_context)
    decision_ids = tuple(str(unit["decision_unit_id"]) for unit in record.task["decision_units"])
    design_review = latest_review_assessment(
        root, task_id, "design", decision_unit_ids=decision_ids
    )
    review_refs = evidence.get("review_refs")
    if not isinstance(review_refs, Mapping) or review_refs.get("design") != _review_ref(
        design_review
    ):
        raise ContractError("Design review reference is stale", code="VERIFY_FINALIZE_REVIEW_STALE")
    snapshot = evidence.get("verification_snapshot_sha256")
    if not isinstance(snapshot, str):
        raise ContractError("V2 snapshot is invalid", code="VERIFY_FINALIZE_EVIDENCE_INVALID")
    implementation_review = latest_review_assessment(
        root,
        task_id,
        "implementation",
        decision_unit_ids=decision_ids,
        verification_snapshot_sha256=snapshot,
    )
    final = finalize_v2_evidence(evidence, implementation_review.record)
    save_evidence(evidence_path, final)
    return VerifyResult(
        task_id,
        "passed",
        str(record.task.get("current_state")),
        evidence_path,
        (),
    )


def _load_v2_ci_source_evidence(
    repository_root: Path,
    task_id: str,
    record: TaskRecord,
    classification: Mapping[str, object],
    bundle: PolicyBundle,
    spec_sha256: str,
    actor: str | None,
) -> tuple[
    dict[str, object],
    str,
    str,
    ReviewAssessment,
    dict[str, object],
    TargetedMutationFacts,
]:
    """Load the local-final V2 authority without mutating the task directory.

    CI evidence is an execution attestation, not a second implementation review.
    It can therefore inherit the verifier identity and mutation projection only
    from a current, finalized local evidence artifact.
    """
    evidence_path = resolve_task_path(repository_root, task_id, "evidence.json")
    if not evidence_path.is_file():
        raise ContractError(
            "V2 local-final evidence is missing", code="VERIFY_FINALIZE_EVIDENCE_INVALID"
        )
    evidence = read_task_json(repository_root, task_id, "evidence.json", contract_name="evidence")
    if not isinstance(evidence, dict):
        raise ContractError(
            "V2 local-final evidence is invalid", code="VERIFY_FINALIZE_EVIDENCE_INVALID"
        )
    if (
        evidence.get("schema_version") != "2.0"
        or evidence.get("verification_level") != "V2"
        or evidence.get("phase") != "final"
        or evidence.get("mode") != "local"
        or evidence.get("conclusion") != "passed"
    ):
        raise ContractError(
            "V2 local-final evidence is invalid", code="VERIFY_FINALIZE_EVIDENCE_INVALID"
        )
    validate_v2_snapshot(evidence)
    current = {
        "task_id": task_id,
        "repository_id": record.task.get("repository_id"),
        "branch": record.task.get("branch"),
        "base_commit": record.task.get("base_commit"),
        "subject_commit": record.task.get("subject_commit"),
        "policy_sha256": bundle.sha256,
        "spec_sha256": spec_sha256,
        "classification_input_sha256": classification.get("classification_input_sha256"),
        "verification_level": "V2",
    }
    if evaluate_freshness("evidence", evidence, current).status != "fresh":
        raise ContractError(
            "V2 local-final evidence is stale", code="VERIFY_FINALIZE_EVIDENCE_STALE"
        )

    implementer = current_implementer_actor(record.events)
    source_actor = evidence.get("verifier_actor")
    _implementer, verifier_actor = validate_verifier_actor(implementer, source_actor or "")
    if actor is not None and actor.strip() != verifier_actor:
        raise ContractError("Verifier actor is stale", code="VERIFY_FINALIZE_ACTOR_STALE")

    context_digest = evidence.get("verifier_context_sha256")
    if not isinstance(context_digest, str):
        raise ContractError("Verifier context is invalid", code="VERIFY_FINALIZE_CONTEXT_INVALID")
    stored_context = load_verifier_context(repository_root, task_id, context_digest)
    current_context = build_verifier_context(repository_root, task_id)
    validate_verifier_context_current(stored_context, current_context)

    decision_ids = tuple(str(unit["decision_unit_id"]) for unit in record.task["decision_units"])
    design_review = latest_review_assessment(
        repository_root, task_id, "design", decision_unit_ids=decision_ids
    )
    review_refs = evidence.get("review_refs")
    if not isinstance(review_refs, Mapping) or review_refs.get("design") != _review_ref(
        design_review
    ):
        raise ContractError("Design review reference is stale", code="VERIFY_FINALIZE_REVIEW_STALE")
    snapshot = evidence.get("verification_snapshot_sha256")
    if not isinstance(snapshot, str):
        raise ContractError("V2 snapshot is invalid", code="VERIFY_FINALIZE_EVIDENCE_INVALID")
    implementation_review = latest_review_assessment(
        repository_root,
        task_id,
        "implementation",
        decision_unit_ids=decision_ids,
        verification_snapshot_sha256=snapshot,
    )
    if review_refs.get("implementation") != _review_ref(implementation_review):
        raise ContractError(
            "Implementation review reference is stale", code="VERIFY_FINALIZE_REVIEW_STALE"
        )
    mutation_projection, mutation_facts = _ci_v2_targeted_mutation_projection(
        repository_root, task_id, evidence
    )
    if not mutation_facts.passed:
        raise ContractError(
            "V2 local-final mutation evidence is invalid",
            code=mutation_facts.reason_code or "MUTATION_EVIDENCE_INVALID",
        )
    return (
        evidence,
        verifier_actor,
        context_digest,
        design_review,
        mutation_projection,
        mutation_facts,
    )


def _ci_v2_targeted_mutation_projection(
    repository_root: Path, task_id: str, source_evidence: Mapping[str, object]
) -> tuple[dict[str, object], TargetedMutationFacts]:
    """Replay a finalized source projection through the public read-only consumer."""
    try:
        facts = consume_targeted_mutation_evidence(repository_root, task_id, source_evidence)
    except AiflowError:
        facts = TargetedMutationFacts(False, "MUTATION_EVIDENCE_INVALID", None, None, None, ())
    if (
        not isinstance(facts.evidence_ref, str)
        or not isinstance(facts.mutation_evidence_sha256, str)
        or not isinstance(facts.manifest_ref, str)
        or len(facts.results) != 5
    ):
        return _missing_mutation_projection(task_id), facts
    return (
        {
            "evidence_ref": facts.evidence_ref,
            "mutation_evidence_sha256": facts.mutation_evidence_sha256,
            "manifest_ref": facts.manifest_ref,
            "results": [dict(item) for item in facts.results],
        },
        facts,
    )


def verify_task(
    repository_root: Path,
    task_id: str,
    *,
    actor: str | None = None,
    check_ids: Sequence[str] = (),
    provisional: bool = False,
    run_id: str | None = None,
    ci: bool = False,
    ci_run_dir: Path | None = None,
    output: Path | None = None,
    finalize: bool = False,
    version_probe: VersionProbe = _default_version_probe,
) -> VerifyResult:
    """Execute one governed local verification or read-only CI attestation."""
    root = repository_root.resolve()
    if finalize:
        return _finalize_v2_task(
            root,
            task_id,
            actor=actor,
            check_ids=check_ids,
            ci=ci,
            ci_run_dir=ci_run_dir,
            output=output,
        )
    record = read_task_record_strict(root, task_id) if ci else load_task_record(root, task_id)
    state = str(record.task.get("current_state"))
    if ci:
        if state not in {"VERIFIED", "WAITING_FOR_FINAL_REVIEW", "APPROVED_FOR_MERGE"}:
            raise ContractError(
                "Task is not ready for CI verification", code="VERIFY_STATE_INVALID"
            )
        run_directory, evidence_path = _ci_paths(ci_run_dir, output)
    else:
        run_directory = Path()
        evidence_path = resolve_task_path(root, task_id, "evidence.json")

    classification = _classification(root, task_id)
    bundle = load_policy_bundle(root)
    spec_sha256 = specification_digest(_read_spec(root, task_id))
    _require_fresh_inputs(root, record, classification, bundle, spec_sha256)
    level = classification.get("effective_verification_level")
    if level not in {"V0", "V1", "V2"}:
        raise ContractError("Verification level is invalid", code="VERIFY_LEVEL_INVALID")
    if ci and level == "V2" and (check_ids or provisional):
        raise ContractError(
            "V2 CI requires a complete verification run", code="VERIFY_CI_V2_PARTIAL_INVALID"
        )
    verifier_actor: str | None = None
    ci_v2_source_evidence: dict[str, object] | None = None
    ci_v2_design_review: ReviewAssessment | None = None
    ci_v2_context_sha256: str | None = None
    ci_v2_mutation_projection: dict[str, object] | None = None
    ci_v2_mutation_facts: TargetedMutationFacts | None = None
    if level == "V2":
        if ci:
            (
                ci_v2_source_evidence,
                verifier_actor,
                ci_v2_context_sha256,
                ci_v2_design_review,
                ci_v2_mutation_projection,
                ci_v2_mutation_facts,
            ) = _load_v2_ci_source_evidence(
                root,
                task_id,
                record,
                classification,
                bundle,
                spec_sha256,
                actor,
            )
        else:
            implementer = current_implementer_actor(record.events)
            _implementer, verifier_actor = validate_verifier_actor(implementer, actor or "")
    elif not ci and (actor is None or not actor.strip()):
        raise ContractError("Verification actor is required", code="VERIFY_ACTOR_REQUIRED")
    effective_actor = verifier_actor if level == "V2" else actor

    if ci:
        assessment = _ci_git_assessment(root, task_id, record)
        identifier = run_directory.name
        subject_commit = assessment.subject_commit
    else:
        assessment = evaluate_and_sync_verification_subject(
            root,
            task_id,
            mode="provisional" if check_ids or provisional else "final",
            actor=cast(str, effective_actor),
        )
        if not check_ids and not assessment.gate_eligible:
            raise ContractError("Git verification context is stale", code="VERIFY_GIT_STALE")
        record = load_task_record(root, task_id)
        _require_fresh_inputs(root, record, classification, bundle, spec_sha256)
        identifier = run_id or _run_id()
        subject_commit = assessment.subject_commit

    context = VerificationContext(
        root,
        task_id,
        str(record.task["base_commit"]),
        subject_commit,
        sys.executable,
        identifier,
        run_directory if ci else None,
    )
    full_plan = parse_verification_plan(
        bundle, context, level=cast(Literal["V0", "V1", "V2"], level)
    )
    design_review: ReviewAssessment | None = None
    verifier_context_sha256: str | None = None
    if level == "V2":
        if ci:
            assert ci_v2_context_sha256 is not None
            assert ci_v2_design_review is not None
            verifier_context_sha256 = ci_v2_context_sha256
            design_review = ci_v2_design_review
        else:
            verifier_context = build_verifier_context(root, task_id)
            verifier_context_sha256 = str(verifier_context["context_sha256"])
            save_verifier_context(root, task_id, verifier_context)
            decision_ids = tuple(
                str(unit["decision_unit_id"]) for unit in record.task["decision_units"]
            )
            design_review = latest_review_assessment(
                root, task_id, "design", decision_unit_ids=decision_ids
            )
        execution_plan, planned_evidence_checks = _v2_plans(full_plan, check_ids)
    else:
        execution_plan = _selected_plan(full_plan, check_ids)
        planned_evidence_checks = execution_plan.checks
    if not ci:
        _start_local_verification(root, task_id, record, cast(str, effective_actor))
    results = _execute_plan(root, execution_plan)
    if level == "V2":
        results.append(_independent_verifier_result())
        if ci:
            assert ci_v2_source_evidence is not None
            assert ci_v2_mutation_projection is not None
            assert ci_v2_mutation_facts is not None
            mutation_projection = ci_v2_mutation_projection
            mutation_facts = ci_v2_mutation_facts
        else:
            mutation_projection, mutation_facts = _targeted_mutation_projection(
                root,
                task_id,
                subject_commit,
                collect=not check_ids or "targeted_mutation" in check_ids,
            )
    else:
        mutation_projection = None
        mutation_facts = None
    versions = {
        check.check_id: (
            "aiflow-mutation-evidence-v1"
            if check.check_id in _V2_CHAPTER11_CHECK_IDS
            else "aiflow-local"
            if check.check_id == "independent_verifier"
            else version_probe(check)
        )
        for check in planned_evidence_checks
    }
    provisional = bool(check_ids) or provisional
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
            *(("--actor", cast(str, verifier_actor)) if level == "V2" else ()),
        )
        if ci
        else (
            "python",
            "-m",
            "aiflow",
            "verify",
            task_id,
            "--actor",
            cast(str, effective_actor),
            *(argument for check_id in check_ids for argument in ("--check", check_id)),
        )
    )
    facts_level = "V1" if level == "V2" else level
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
        cast(Literal["V0", "V1"], facts_level),
        "ci" if ci else "local",
        identifier,
        full_plan.run_dir,
        _now(),
        reproduce_command,
        assessment.attestation_head if ci else None,
        (assessment.attestation_scope.passed and assessment.worktree_scope.passed) if ci else None,
    )
    evidence = build_evidence(
        facts,
        planned_evidence_checks,
        results,
        tool_versions=versions,
        unverified_scenarios=(
            *execution_plan.unverified_check_ids,
            *execution_plan.blocking_reasons,
        ),
        provisional=provisional,
    )
    if level == "V2":
        assert verifier_actor is not None
        assert verifier_context_sha256 is not None
        assert design_review is not None
        assert mutation_projection is not None
        assert mutation_facts is not None
        evidence = _upgrade_v2_pre_evidence(
            evidence,
            mutation_projection=mutation_projection,
            mutation_facts=mutation_facts,
            verifier_actor=verifier_actor,
            verifier_context_sha256=verifier_context_sha256,
            design_review=design_review,
            provisional_check_ids=check_ids if check_ids else (),
        )
    try:
        save_evidence(
            evidence_path,
            evidence,
            archive_path=full_plan.run_dir / "evidence.json" if not ci else None,
        )
    except AiflowError:
        if not ci:
            transition_task_record(
                root,
                task_id,
                target_state="FAILED",
                event_type="verification_failed",
                actor=cast(str, effective_actor),
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
            actor=cast(str, effective_actor),
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
