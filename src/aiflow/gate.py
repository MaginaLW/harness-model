"""Read-only deterministic merge gate decisions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import ContractError
from aiflow.evidence import V2_FINAL, validate_v2_snapshot
from aiflow.freshness import current_classification_input_digest, evaluate_freshness
from aiflow.git_context import collect_git_context, commits_are_ancestral
from aiflow.mutation_evidence import consume_targeted_mutation_evidence
from aiflow.policy import load_policy_bundle
from aiflow.review_service import latest_review_assessment
from aiflow.routing import ROUTE_ORDER, route_task
from aiflow.scope import (
    AutoPreflightFacts,
    assess_auto_scope,
    assess_governance_only_scope,
    assess_scope,
    collect_verification_changed_paths,
    evaluate_auto_preflight,
    forbidden_action_present,
)
from aiflow.specification import specification_digest
from aiflow.storage import read_task_json, resolve_task_path
from aiflow.task_service import read_task_record_strict
from aiflow.verification_level import verification_for_task
from aiflow.verifier_service import (
    build_verifier_context,
    current_implementer_actor,
    load_verifier_context,
    validate_verifier_actor,
    validate_verifier_context_current,
)

_REASON_ORDER = (
    "GATE_BLOCKED",
    "GATE_STATE_INVALID",
    "GATE_REPOSITORY_CHANGED",
    "GATE_SCOPE_CHANGED",
    "GATE_CLASSIFICATION_STALE",
    "GATE_ROUTE_INVALID",
    "GATE_SPEC_STALE",
    "GATE_ASK_UNANSWERED",
    "GATE_SPEC_APPROVAL_STALE",
    "GATE_EVIDENCE_STALE",
    "GATE_EVIDENCE_NOT_PASSED",
    "GATE_V2_EVIDENCE_NOT_FINAL",
    "GATE_V2_SNAPSHOT_STALE",
    "GATE_V2_VERIFIER_NOT_INDEPENDENT",
    "GATE_V2_CONTEXT_STALE",
    "GATE_V2_REVIEW_STALE",
    "GATE_V2_CHECKS_INCOMPLETE",
    "GATE_V2_MUTATION_NOT_KILLED",
    "GATE_CODE_APPROVAL_STALE",
)


@dataclass(frozen=True)
class GateFacts:
    """Closed, content-free facts consumed by the Gate decision table."""

    task_id: str
    current_state: str
    route: str
    verification_level: str
    ask_required: bool = False
    review_required: bool = False
    repository_current: bool = True
    scope_current: bool = True
    classification_current: bool = True
    specification_current: bool = True
    ask_answered: bool = True
    spec_approval_current: bool = True
    evidence_current: bool = True
    evidence_passed: bool = True
    code_approval_current: bool = True
    unresolved_block_or_escalation: bool = False
    v2_final_evidence: bool = True
    v2_snapshot_current: bool = True
    v2_verifier_independent: bool = True
    v2_context_current: bool = True
    v2_reviews_current: bool = True
    v2_checks_current: bool = True
    v2_mutation_killed: bool = True


@dataclass(frozen=True)
class GateDecision:
    """Stable output shared by text, JSON, and CI exit-code handling."""

    task_id: str
    passed: bool
    route: str
    verification_level: str
    reason_codes: tuple[str, ...]
    recovery_argv: tuple[tuple[str, ...], ...]

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["reason_codes"] = list(self.reason_codes)
        value["recovery_argv"] = [list(command) for command in self.recovery_argv]
        return value

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    def to_text(self) -> str:
        outcome = "PASS" if self.passed else "REJECT"
        reasons = ", ".join(self.reason_codes) or "none"
        recovery = "; ".join(" ".join(command) for command in self.recovery_argv) or "none"
        return "\n".join(
            (
                f"Gate: {outcome}",
                f"Task: {self.task_id}",
                f"Route / verification: {self.route} / {self.verification_level}",
                f"Reasons: {reasons}",
                f"Recovery: {recovery}",
            )
        )


def evaluate_gate_facts(facts: GateFacts) -> GateDecision:
    """Apply the sole merge decision table without reading or mutating files."""
    reasons: list[str] = []
    if facts.unresolved_block_or_escalation or facts.route == "BLOCK":
        reasons.append("GATE_BLOCKED")
    if facts.current_state != "APPROVED_FOR_MERGE":
        reasons.append("GATE_STATE_INVALID")
    if not facts.repository_current:
        reasons.append("GATE_REPOSITORY_CHANGED")
    if not facts.scope_current:
        reasons.append("GATE_SCOPE_CHANGED")
    if not facts.classification_current:
        reasons.append("GATE_CLASSIFICATION_STALE")
    if facts.route not in ROUTE_ORDER or facts.verification_level not in {"V0", "V1", "V2"}:
        reasons.append("GATE_ROUTE_INVALID")
    if not facts.specification_current:
        reasons.append("GATE_SPEC_STALE")
    if (facts.route == "ASK" or facts.ask_required) and not facts.ask_answered:
        reasons.append("GATE_ASK_UNANSWERED")
    if (facts.route == "REVIEW" or facts.review_required) and not facts.spec_approval_current:
        reasons.append("GATE_SPEC_APPROVAL_STALE")
    if not facts.evidence_current:
        reasons.append("GATE_EVIDENCE_STALE")
    if not facts.evidence_passed:
        reasons.append("GATE_EVIDENCE_NOT_PASSED")
    if facts.verification_level == "V2":
        if not facts.v2_final_evidence:
            reasons.append("GATE_V2_EVIDENCE_NOT_FINAL")
        if not facts.v2_snapshot_current:
            reasons.append("GATE_V2_SNAPSHOT_STALE")
        if not facts.v2_verifier_independent:
            reasons.append("GATE_V2_VERIFIER_NOT_INDEPENDENT")
        if not facts.v2_context_current:
            reasons.append("GATE_V2_CONTEXT_STALE")
        if not facts.v2_reviews_current:
            reasons.append("GATE_V2_REVIEW_STALE")
        if not facts.v2_checks_current:
            reasons.append("GATE_V2_CHECKS_INCOMPLETE")
        if not facts.v2_mutation_killed:
            reasons.append("GATE_V2_MUTATION_NOT_KILLED")
    if (facts.route == "REVIEW" or facts.review_required) and not facts.code_approval_current:
        reasons.append("GATE_CODE_APPROVAL_STALE")
    ordered = tuple(code for code in _REASON_ORDER if code in reasons)
    recovery_for = {
        "GATE_BLOCKED": ("aiflow", "resolve", facts.task_id),
        "GATE_STATE_INVALID": ("aiflow", "verify", facts.task_id),
        "GATE_REPOSITORY_CHANGED": ("git", "checkout", "<recorded-branch>"),
        "GATE_SCOPE_CHANGED": ("aiflow", "verify", facts.task_id),
        "GATE_CLASSIFICATION_STALE": ("aiflow", "classify", facts.task_id),
        "GATE_ROUTE_INVALID": ("aiflow", "classify", facts.task_id),
        "GATE_SPEC_STALE": ("aiflow", "freeze", facts.task_id),
        "GATE_ASK_UNANSWERED": ("aiflow", "answer", facts.task_id),
        "GATE_SPEC_APPROVAL_STALE": (
            "aiflow",
            "approve",
            facts.task_id,
            "--type",
            "spec",
        ),
        "GATE_EVIDENCE_STALE": ("aiflow", "verify", facts.task_id),
        "GATE_EVIDENCE_NOT_PASSED": ("aiflow", "verify", facts.task_id),
        "GATE_V2_EVIDENCE_NOT_FINAL": ("aiflow", "verify", facts.task_id, "--finalize"),
        "GATE_V2_SNAPSHOT_STALE": ("aiflow", "verify", facts.task_id),
        "GATE_V2_VERIFIER_NOT_INDEPENDENT": ("aiflow", "verify", facts.task_id),
        "GATE_V2_CONTEXT_STALE": ("aiflow", "verify", facts.task_id),
        "GATE_V2_REVIEW_STALE": ("aiflow", "review", facts.task_id),
        "GATE_V2_CHECKS_INCOMPLETE": ("aiflow", "verify", facts.task_id),
        "GATE_V2_MUTATION_NOT_KILLED": ("aiflow", "verify", facts.task_id),
        "GATE_CODE_APPROVAL_STALE": (
            "aiflow",
            "approve",
            facts.task_id,
            "--type",
            "code",
        ),
    }
    commands: list[tuple[str, ...]] = []
    for code in ordered:
        command = recovery_for[code]
        if command not in commands:
            commands.append(command)
    return GateDecision(
        facts.task_id,
        not ordered,
        facts.route,
        facts.verification_level,
        ordered,
        tuple(commands),
    )


def _read_external_evidence(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractError("Gate evidence is unreadable", code="GATE_INPUT_INVALID") from error
    if not isinstance(value, dict):
        raise ContractError("Gate evidence is invalid", code="GATE_INPUT_INVALID")
    require_valid_contract("evidence", value)
    return value


def _digest(value: Mapping[str, object]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read_approvals(repository_root: Path, task_id: str) -> tuple[dict[str, Any], ...]:
    path = resolve_task_path(repository_root, task_id, "approvals.json")
    if not path.is_file():
        return ()
    value = read_task_json(repository_root, task_id, "approvals.json")
    if not isinstance(value, list):
        raise ContractError("Gate approvals are invalid", code="GATE_INPUT_INVALID")
    result: list[dict[str, Any]] = []
    for approval in value:
        if not isinstance(approval, dict):
            raise ContractError("Gate approval is invalid", code="GATE_INPUT_INVALID")
        require_valid_contract("approval", approval)
        result.append(approval)
    return tuple(result)


def _read_local_evidence(repository_root: Path, task_id: str) -> dict[str, Any] | None:
    path = resolve_task_path(repository_root, task_id, "evidence.json")
    if not path.is_file():
        return None
    value = read_task_json(repository_root, task_id, "evidence.json", contract_name="evidence")
    if not isinstance(value, dict):
        raise ContractError("Gate evidence is invalid", code="GATE_INPUT_INVALID")
    return value


def _v2_gate_facts(
    repository_root: Path,
    task_id: str,
    evidence: Mapping[str, object] | None,
    *,
    events: tuple[Mapping[str, object], ...],
    policy_checks: list[Mapping[str, object]],
    decision_unit_ids: list[str],
) -> dict[str, bool]:
    """Derive the extra V2 final-evidence predicates without changing V0/V1 paths."""
    result = {
        "v2_final_evidence": False,
        "v2_snapshot_current": False,
        "v2_verifier_independent": False,
        "v2_context_current": False,
        "v2_reviews_current": False,
        "v2_checks_current": False,
        "v2_mutation_killed": False,
    }
    if not isinstance(evidence, Mapping) or evidence.get("schema_version") != "2.0":
        return result
    result["v2_final_evidence"] = evidence.get("phase") == V2_FINAL
    try:
        validate_v2_snapshot(evidence)
        result["v2_snapshot_current"] = True
        implementer = current_implementer_actor(events)
        verifier = evidence.get("verifier_actor")
        if isinstance(verifier, str):
            validate_verifier_actor(implementer, verifier)
            result["v2_verifier_independent"] = True
        digest = evidence.get("verifier_context_sha256")
        if isinstance(digest, str):
            stored = load_verifier_context(repository_root, task_id, digest)
            validate_verifier_context_current(
                stored, build_verifier_context(repository_root, task_id)
            )
            result["v2_context_current"] = True
        expected_checks = {
            str(check.get("id"))
            for check in policy_checks
            if check.get("required") is True and isinstance(check.get("id"), str)
        }
        checks = evidence.get("checks")
        if isinstance(checks, list):
            by_id = {
                str(check.get("check_id")): check
                for check in checks
                if isinstance(check, Mapping) and isinstance(check.get("check_id"), str)
            }
            result["v2_checks_current"] = (
                len(by_id) == len(checks)
                and expected_checks.issubset(by_id)
                and all(by_id[check_id].get("status") == "passed" for check_id in expected_checks)
            )
        mutation_facts = consume_targeted_mutation_evidence(repository_root, task_id, evidence)
        result["v2_mutation_killed"] = mutation_facts.passed
        refs = evidence.get("review_refs")
        snapshot = evidence.get("verification_snapshot_sha256")
        if isinstance(refs, Mapping) and isinstance(snapshot, str):
            design = latest_review_assessment(
                repository_root, task_id, "design", decision_unit_ids=decision_unit_ids
            )
            implementation = latest_review_assessment(
                repository_root,
                task_id,
                "implementation",
                decision_unit_ids=decision_unit_ids,
                verification_snapshot_sha256=snapshot,
            )
            result["v2_reviews_current"] = all(
                isinstance(ref, Mapping)
                and ref.get("review_id") == assessment.record.get("review_id")
                and ref.get("context_sha256") == assessment.record.get("context_sha256")
                for ref, assessment in (
                    (refs.get("design"), design),
                    (refs.get("implementation"), implementation),
                )
            )
    except ContractError:
        return result
    return result


def evaluate_gate(
    repository_root: Path, task_id: str, *, evidence_path: Path | None = None
) -> GateDecision:
    """Read current immutable facts and return a Gate decision without writes."""
    root = repository_root.resolve()
    record = read_task_record_strict(root, task_id)
    task = record.task
    context = collect_git_context(root)
    classification = read_task_json(
        root, task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(classification, dict):
        raise ContractError("Gate classification is invalid", code="GATE_INPUT_INVALID")
    policy = load_policy_bundle(root)
    spec_path = resolve_task_path(root, task_id, "spec.md")
    try:
        spec_sha256 = specification_digest(spec_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise ContractError(
            "Gate specification is unreadable", code="GATE_INPUT_INVALID"
        ) from error
    units = parse_decision_units(task)
    input_sha256, synchronized = current_classification_input_digest(
        task, units, classification, record.events
    )
    subject = task.get("subject_commit")
    base = task.get("base_commit")
    if not isinstance(subject, str) or not isinstance(base, str):
        raise ContractError("Gate Git binding is invalid", code="GATE_INPUT_INVALID")
    changes = collect_verification_changed_paths(
        root, base_commit=base, subject_commit=subject, head_commit=context.head
    )
    allowed_scope = task.get("allowed_scope")
    if not isinstance(allowed_scope, list) or not all(
        isinstance(item, str) for item in allowed_scope
    ):
        raise ContractError("Gate scope is invalid", code="GATE_INPUT_INVALID")
    committed_scope = assess_scope(
        changes.committed,
        tuple(allowed_scope),
        task_id=task_id,
        repository_root=root,
        cache_patterns=(),
    )
    governance_scope = assess_governance_only_scope(
        (*changes.attestation, *changes.worktree), task_id=task_id, repository_root=root
    )
    current: dict[str, object] = {
        "task_id": task_id,
        "repository_id": task.get("repository_id"),
        "branch": task.get("branch"),
        "base_commit": base,
        "subject_commit": subject,
        "policy_sha256": policy.sha256,
        "spec_sha256": spec_sha256,
        "classification_input_sha256": input_sha256,
        "subject_synchronized": synchronized,
        "verification_level": classification.get("effective_verification_level"),
        "attestation_head": context.head,
        "governance_only": governance_scope.passed,
        "attestation_governance_only": governance_scope.passed,
    }
    classification_current = (
        evaluate_freshness("classification", classification, current).status == "fresh"
    )
    recomputed_routes = route_task(task, policy)
    recomputed_verification = verification_for_task(task, policy)
    route_by_id = {
        decision.decision_unit_id: decision.effective_route
        for decision in recomputed_routes.unit_decisions
    }
    verification_by_id = {
        decision.decision_unit_id: decision.level
        for decision in recomputed_verification.unit_decisions
    }
    entries = classification.get("classifications")
    if not isinstance(entries, list):
        raise ContractError("Gate classification is invalid", code="GATE_INPUT_INVALID")
    entry_ids = {
        str(entry.get("decision_unit_id")) for entry in entries if isinstance(entry, Mapping)
    }
    classification_current = classification_current and (
        recomputed_routes.effective_route == classification.get("effective_route")
        and recomputed_verification.level == classification.get("effective_verification_level")
        and len(entries) == len(entry_ids)
        and entry_ids == set(route_by_id) == set(verification_by_id)
        and all(
            isinstance(entry, Mapping)
            and route_by_id.get(str(entry.get("decision_unit_id"))) == entry.get("route")
            and verification_by_id.get(str(entry.get("decision_unit_id")))
            == entry.get("verification_level")
            for entry in entries
        )
    )
    local_evidence = _read_local_evidence(root, task_id)
    evidence = (
        _read_external_evidence(evidence_path) if evidence_path is not None else local_evidence
    )
    evidence_report = (
        evaluate_freshness("evidence", evidence, current) if evidence is not None else None
    )
    expected_mode = "ci" if evidence_path is not None else "local"
    evidence_ids = evidence.get("decision_unit_ids") if evidence is not None else None
    expected_ids = {str(unit["decision_unit_id"]) for unit in units}
    evidence_units_current = (
        isinstance(evidence_ids, list)
        and len(evidence_ids) == len(expected_ids)
        and expected_ids == {str(identifier) for identifier in evidence_ids}
    )
    v2_facts: dict[str, bool] = {}
    if classification.get("effective_verification_level") == "V2":
        levels = policy.documents["verification-levels.yaml"].get("levels")
        v2_checks: object = (
            next(
                (
                    level.get("checks")
                    for level in levels
                    if isinstance(level, Mapping) and level.get("id") == "V2"
                ),
                [],
            )
            if isinstance(levels, list)
            else []
        )
        v2_facts = _v2_gate_facts(
            root,
            task_id,
            evidence,
            events=record.events,
            policy_checks=[check for check in v2_checks if isinstance(check, Mapping)]
            if isinstance(v2_checks, list)
            else [],
            decision_unit_ids=sorted(expected_ids),
        )
    approvals = _read_approvals(root, task_id)
    approval_current: dict[str, set[str]] = {"spec": set(), "code": set()}
    local_evidence_report = (
        evaluate_freshness("evidence", local_evidence, current)
        if local_evidence is not None
        else None
    )
    approval_facts = {
        **current,
        "evidence_sha256": _digest(local_evidence) if local_evidence is not None else None,
        "evidence_current": local_evidence_report is not None
        and local_evidence_report.status == "fresh",
    }
    for approval in approvals:
        approval_type = approval.get("approval_type")
        if approval_type not in {"spec", "code"}:
            continue
        report = evaluate_freshness(
            "spec_approval" if approval_type == "spec" else "code_approval",
            approval,
            approval_facts,
        )
        if report.status == "fresh":
            approval_current[str(approval_type)].add(str(approval.get("decision_unit_id")))
    ask_ids = {
        str(entry["decision_unit_id"])
        for entry in entries
        if isinstance(entry, Mapping) and entry.get("route") == "ASK"
    }
    review_ids = {
        str(entry["decision_unit_id"])
        for entry in entries
        if isinstance(entry, Mapping) and entry.get("route") == "REVIEW"
    }
    block_present = any(
        isinstance(entry, Mapping) and entry.get("route") == "BLOCK" for entry in entries
    )
    unfinished_units = [unit for unit in units if unit.get("completed") is not True]
    unfinished_routes = tuple(
        route_by_id.get(str(unit["decision_unit_id"]), "BLOCK") for unit in unfinished_units
    )
    auto_unit_scopes = tuple(
        tuple(str(pattern) for pattern in unit.get("impact_scope", []))
        for unit in unfinished_units
        if route_by_id.get(str(unit["decision_unit_id"])) == "AUTO"
    )
    forbidden_present = forbidden_action_present(
        task.get("forbidden_actions", []),
        tuple(action for unit in unfinished_units for action in unit.get("planned_actions", [])),
    )
    approval_requirements = any(
        bool(unit.get("permission_requirements")) for unit in unfinished_units
    )
    auto_preflight_passed = True
    if str(classification.get("effective_route")) == "AUTO":
        auto_scope = assess_auto_scope(
            changes.committed,
            tuple(allowed_scope),
            auto_unit_scopes,
            task_id=task_id,
            repository_root=root,
        )
        auto_preflight_passed = evaluate_auto_preflight(
            AutoPreflightFacts(
                unfinished_routes=unfinished_routes,
                specification_frozen=task.get("frozen_spec_sha256") == spec_sha256,
                required_approvals_present=approval_requirements,
                forbidden_actions_present=forbidden_present,
                scope=auto_scope,
                verification_complete=classification_current,
            )
        ).passed
    answered_ids: set[str] = set()
    for event in record.events:
        payload = event.get("payload")
        if event.get("event_type") != "ask_answered" or not isinstance(payload, Mapping):
            continue
        options = payload.get("options")
        if (
            isinstance(options, Mapping)
            and payload.get("specification_sha256") == spec_sha256
            and payload.get("policy_sha256") == policy.sha256
            and payload.get("classification_input_sha256")
            == classification.get("classification_input_sha256")
        ):
            answered_ids.add(str(options.get("decision_unit_id")))
    repository_current = context.repository_id == task.get(
        "repository_id"
    ) and context.branch == task.get("branch")
    facts = GateFacts(
        task_id=task_id,
        current_state=str(task.get("current_state")),
        route=str(classification.get("effective_route")),
        verification_level=str(classification.get("effective_verification_level")),
        ask_required=bool(ask_ids),
        review_required=bool(review_ids),
        repository_current=repository_current
        and commits_are_ancestral(
            root, base_commit=base, subject_commit=subject, head_commit=context.head
        ),
        scope_current=committed_scope.passed and governance_scope.passed and auto_preflight_passed,
        classification_current=classification_current,
        specification_current=task.get("frozen_spec_sha256") == spec_sha256,
        ask_answered=ask_ids.issubset(answered_ids),
        spec_approval_current=review_ids.issubset(approval_current["spec"]),
        evidence_current=evidence_report is not None
        and evidence_report.status == "fresh"
        and evidence_units_current
        and evidence is not None
        and evidence.get("mode") == expected_mode,
        evidence_passed=evidence is not None and evidence.get("conclusion") == "passed",
        code_approval_current=review_ids.issubset(approval_current["code"]),
        unresolved_block_or_escalation=block_present
        or task.get("current_state") in {"BLOCKED", "ESCALATED"},
        **v2_facts,
    )
    return evaluate_gate_facts(facts)
