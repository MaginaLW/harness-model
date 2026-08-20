"""Route-independent, conservative verification-level selection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from aiflow.policy import PolicyBundle

V0 = "V0"
V1 = "V1"
_V0_REQUIRED_CHECKS = frozenset({"contract", "scope", "ruff_check", "ruff_format_check", "smoke"})
_CHARACTERISTIC_KEYS = frozenset(
    {
        "mechanical",
        "behavior_changed",
        "code_modified",
        "interaction_scope",
        "regression_risk",
        "error_detectability",
    }
)


@dataclass(frozen=True)
class VerificationDecision:
    """A stable, auditable verification decision for exactly one unit."""

    decision_unit_id: str
    level: str
    rule_ids: tuple[str, ...]
    explanations: tuple[str, ...]
    blocking_reasons: tuple[str, ...] = ()

    @property
    def verification_level(self) -> str:
        return self.level

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_unit_id": self.decision_unit_id,
            "verification_level": self.level,
            "rule_ids": list(self.rule_ids),
            "explanations": list(self.explanations),
            "blocking_reasons": list(self.blocking_reasons),
        }


@dataclass(frozen=True)
class TaskVerificationDecision:
    """Aggregate decision that retains each unit's individual evidence."""

    level: str
    unit_decisions: tuple[VerificationDecision, ...]
    blocking_reasons: tuple[str, ...] = ()

    @property
    def verification_level(self) -> str:
        return self.level

    def to_dict(self) -> dict[str, object]:
        return {
            "verification_level": self.level,
            "unit_decisions": [decision.to_dict() for decision in self.unit_decisions],
            "blocking_reasons": list(self.blocking_reasons),
        }


def _policy_v0_complete(bundle: PolicyBundle) -> bool:
    """Require the baseline V0 gates by ID and mark each as required."""
    document = bundle.documents.get("verification-levels.yaml")
    if not isinstance(document, Mapping):
        return False
    levels = document.get("levels")
    if not isinstance(levels, list):
        return False
    v0_levels = [level for level in levels if isinstance(level, Mapping) and level.get("id") == V0]
    if len(v0_levels) != 1:
        return False
    checks = v0_levels[0].get("checks")
    if not isinstance(checks, list):
        return False
    required = {
        check.get("id")
        for check in checks
        if isinstance(check, Mapping) and check.get("required") is True
    }
    return _V0_REQUIRED_CHECKS.issubset(required)


def _characteristics(unit: Mapping[str, object]) -> tuple[Mapping[str, object] | None, str | None]:
    facts = unit.get("change_characteristics")
    if not isinstance(facts, Mapping) or not _CHARACTERISTIC_KEYS.issubset(facts):
        return None, "VERIFICATION-FACTS-INCOMPLETE"
    mechanical = facts.get("mechanical")
    behavior_changed = facts.get("behavior_changed")
    code_modified = facts.get("code_modified")
    regression_risk = facts.get("regression_risk")
    interaction_scope = facts.get("interaction_scope")
    error_detectability = facts.get("error_detectability")
    if (
        not all(
            isinstance(value, bool)
            for value in (mechanical, behavior_changed, code_modified, regression_risk)
        )
        or interaction_scope not in {"local", "cross_file", "cross_module"}
        or error_detectability not in {"high", "low"}
    ):
        return None, "VERIFICATION-FACTS-INVALID"
    return facts, None


def _is_completed(unit: Mapping[str, object]) -> bool:
    return (
        unit.get("completed") is True
        or str(unit.get("status", unit.get("state", ""))).upper() == "COMPLETED"
    )


def determine_verification_level(
    unit: Mapping[str, object], bundle: PolicyBundle
) -> VerificationDecision:
    """Select V0/V1 strictly from unit facts; routing is intentionally absent."""
    identifier = unit.get("decision_unit_id")
    decision_unit_id = identifier if isinstance(identifier, str) and identifier else "unknown"
    facts, fact_error = _characteristics(unit)
    if fact_error is not None:
        return VerificationDecision(
            decision_unit_id,
            V1,
            (fact_error,),
            ("Explicit low-risk verification facts are unavailable; V1 is required.",),
        )
    assert facts is not None

    v1_reasons: list[tuple[str, str]] = []
    if facts["behavior_changed"] is True:
        v1_reasons.append(("VERIFICATION-BEHAVIOR-CHANGED", "Behavior changes require V1."))
    if facts["code_modified"] is True:
        v1_reasons.append(("VERIFICATION-CODE-MODIFIED", "Code changes require V1."))
    scope = facts["interaction_scope"]
    if scope == "cross_file":
        v1_reasons.append(("VERIFICATION-CROSS-FILE", "Cross-file interaction requires V1."))
    elif scope == "cross_module":
        v1_reasons.append(("VERIFICATION-CROSS-MODULE", "Cross-module interaction requires V1."))
    if facts["regression_risk"] is True:
        v1_reasons.append(("VERIFICATION-REGRESSION-RISK", "Regression risk requires V1."))
    if facts["error_detectability"] == "low":
        v1_reasons.append(
            ("VERIFICATION-LOW-DETECTABILITY", "Low error detectability requires V1.")
        )
    if facts["mechanical"] is not True:
        v1_reasons.append(("VERIFICATION-NON-MECHANICAL", "Non-mechanical work requires V1."))

    if v1_reasons:
        level = V1
        rule_ids = tuple(reason[0] for reason in v1_reasons)
        explanations = tuple(reason[1] for reason in v1_reasons)
    elif not _policy_v0_complete(bundle):
        level = V1
        rule_ids = ("VERIFICATION-V1-POLICY-INCOMPLETE",)
        explanations = ("The V0 Policy checks are incomplete; V1 is required.",)
    else:
        level = V0
        rule_ids = ("VERIFICATION-V0-LOW-RISK",)
        explanations = ("Explicit low-risk facts and complete V0 checks permit V0.",)

    verification = unit.get("verification")
    blocking: tuple[str, ...] = ()
    if not _policy_v0_complete(bundle):
        blocking += ("VERIFICATION-V0-POLICY-INCOMPLETE",)
    if isinstance(verification, Mapping) and verification.get("tools_missing") is True:
        blocking += ("VERIFICATION-TOOLS-MISSING",)
    return VerificationDecision(decision_unit_id, level, rule_ids, explanations, blocking)


def summarize_task_verification(
    units: Sequence[Mapping[str, object]], bundle: PolicyBundle
) -> TaskVerificationDecision:
    """Aggregate unfinished units while preserving completed-unit evidence."""
    decisions = tuple(determine_verification_level(unit, bundle) for unit in units)
    unfinished = [
        decision for unit, decision in zip(units, decisions, strict=True) if not _is_completed(unit)
    ]
    if not unfinished:
        return TaskVerificationDecision("completed", decisions)
    level = V1 if any(decision.level == V1 for decision in unfinished) else V0
    blocking_reasons = tuple(
        dict.fromkeys(reason for decision in unfinished for reason in decision.blocking_reasons)
    )
    return TaskVerificationDecision(level, decisions, blocking_reasons)


def verification_for_task(
    task: Mapping[str, object], bundle: PolicyBundle
) -> TaskVerificationDecision:
    """Determine verification for a task's decision units without route input."""
    units = task.get("decision_units")
    if not isinstance(units, list) or not all(isinstance(unit, Mapping) for unit in units):
        return TaskVerificationDecision(
            V1,
            (
                VerificationDecision(
                    "unknown",
                    V1,
                    ("VERIFICATION-DECISION-UNITS-INVALID",),
                    ("Decision units are unavailable; V1 is required.",),
                    ("VERIFICATION-DECISION-UNITS-INVALID",),
                ),
            ),
            ("VERIFICATION-DECISION-UNITS-INVALID",),
        )
    return summarize_task_verification(units, bundle)


evaluate_verification_level = determine_verification_level
aggregate_verification_levels = summarize_task_verification
