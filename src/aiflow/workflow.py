"""Reusable, deterministic workflow precondition evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConditionStatus = Literal["pass", "fail", "not_applicable"]

_SAFETY_PRIORITY = {
    "ACTION_PERMISSION_DENIED": 10,
    "SCOPE_EXPANDED": 20,
    "GIT_CONTEXT_INVALID": 30,
    "POLICY_SUMMARY_MISMATCH": 40,
    "CLASSIFICATION_STALE": 50,
    "SPECIFICATION_TAMPERED": 60,
    "SPECIFICATION_INCOMPLETE": 70,
    "SPECIFICATION_NOT_FROZEN": 80,
    "REQUIRED_APPROVAL_MISSING": 90,
    "STATE_NOT_ALLOWED": 100,
}


@dataclass(frozen=True)
class WorkflowFacts:
    """Facts supplied by a command before it makes a stateful workflow change."""

    current_state: str
    allowed_states: frozenset[str]
    classification_fresh: bool = True
    policy_summary_matches: bool = True
    specification_complete: bool = True
    specification_frozen: bool = False
    specification_summary_matches: bool = True
    require_specification_frozen: bool = False
    approvals_required: bool = False
    approvals_present: bool = False
    git_context_valid: bool = True
    scope_unchanged: bool = True
    action_allowed: bool = True


@dataclass(frozen=True)
class PreconditionResult:
    """One independently evaluated prerequisite with a stable machine reason."""

    name: str
    status: ConditionStatus
    reason_code: str | None = None


@dataclass(frozen=True)
class WorkflowEvaluation:
    """Complete outcome, ordered for deterministic and safety-first reporting."""

    results: tuple[PreconditionResult, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def failures(self) -> tuple[PreconditionResult, ...]:
        return tuple(result for result in self.results if result.status == "fail")

    @property
    def failure_codes(self) -> tuple[str, ...]:
        return tuple(
            result.reason_code for result in self.failures if result.reason_code is not None
        )


def _result(name: str, passed: bool, code: str) -> PreconditionResult:
    return PreconditionResult(name, "pass" if passed else "fail", None if passed else code)


def _sort_results(results: list[PreconditionResult]) -> tuple[PreconditionResult, ...]:
    return tuple(
        sorted(
            results,
            key=lambda result: (
                0 if result.status == "fail" else 1,
                _SAFETY_PRIORITY.get(result.reason_code or "", 1000),
                result.name,
            ),
        )
    )


def evaluate_preconditions(facts: WorkflowFacts) -> WorkflowEvaluation:
    """Evaluate shared command prerequisites without inspecting or changing storage."""
    results = [
        _result("action_allowed", facts.action_allowed, "ACTION_PERMISSION_DENIED"),
        _result("scope_unchanged", facts.scope_unchanged, "SCOPE_EXPANDED"),
        _result("git_context_valid", facts.git_context_valid, "GIT_CONTEXT_INVALID"),
        _result("policy_summary_matches", facts.policy_summary_matches, "POLICY_SUMMARY_MISMATCH"),
        _result("classification_fresh", facts.classification_fresh, "CLASSIFICATION_STALE"),
        _result(
            "specification_complete",
            facts.specification_complete,
            "SPECIFICATION_INCOMPLETE",
        ),
        _result(
            "state_allowed",
            facts.current_state in facts.allowed_states,
            "STATE_NOT_ALLOWED",
        ),
    ]
    if facts.approvals_required:
        results.append(
            _result("approvals_present", facts.approvals_present, "REQUIRED_APPROVAL_MISSING")
        )
    else:
        results.append(PreconditionResult("approvals_present", "not_applicable"))
    if facts.require_specification_frozen:
        results.append(
            _result(
                "specification_frozen",
                facts.specification_frozen,
                "SPECIFICATION_NOT_FROZEN",
            )
        )
    else:
        results.append(PreconditionResult("specification_frozen", "not_applicable"))
    if facts.specification_frozen:
        results.append(
            _result(
                "specification_summary_matches",
                facts.specification_summary_matches,
                "SPECIFICATION_TAMPERED",
            )
        )
    else:
        results.append(PreconditionResult("specification_summary_matches", "not_applicable"))
    return WorkflowEvaluation(_sort_results(results))


def check_preconditions(facts: WorkflowFacts) -> WorkflowEvaluation:
    """Compatibility spelling for callers that use check-style service APIs."""
    return evaluate_preconditions(facts)
