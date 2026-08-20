"""Deterministic Policy routing for decision units and whole tasks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from aiflow.errors import PolicyError
from aiflow.policy import PolicyBundle
from aiflow.predicates import evaluate_predicate

ROUTE_ORDER = ("AUTO", "ASK", "REVIEW", "BLOCK")
_ROUTES = frozenset(ROUTE_ORDER)
_AUTO_GUARDS = frozenset(
    {
        ("scope.clear", "equals", True, "error"),
        ("impact.level", "equals", "low", "error"),
        ("reversibility", "in", ("conditionally_reversible", "reversible"), "error"),
        ("verification.automatic", "equals", True, "error"),
        ("external_side_effects", "is_empty", None, "error"),
    }
)


@dataclass(frozen=True)
class RuleHit:
    """An auditable match which deliberately excludes input values."""

    rule_id: str
    priority: int
    route: str
    explanation: str
    predicate_explanations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "priority": self.priority,
            "route": self.route,
            "explanation": self.explanation,
            "predicate_explanations": list(self.predicate_explanations),
        }


@dataclass(frozen=True)
class RouteDecision:
    """The complete deterministic route decision for one decision unit."""

    decision_unit_id: str
    effective_route: str
    matched_rules: tuple[RuleHit, ...]
    explanations: tuple[str, ...]

    @property
    def route(self) -> str:
        """Compatibility-friendly short name for the effective route."""
        return self.effective_route

    @property
    def matched_rule_ids(self) -> tuple[str, ...]:
        return tuple(hit.rule_id for hit in self.matched_rules)

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_unit_id": self.decision_unit_id,
            "route": self.effective_route,
            "matched_rules": [hit.to_dict() for hit in self.matched_rules],
            "explanations": list(self.explanations),
        }


@dataclass(frozen=True)
class TaskRouteDecision:
    """A task summary that never rewrites individual unit decisions."""

    effective_route: str
    unit_decisions: tuple[RouteDecision, ...]

    @property
    def route(self) -> str:
        return self.effective_route

    def to_dict(self) -> dict[str, object]:
        return {
            "effective_route": self.effective_route,
            "unit_decisions": [decision.to_dict() for decision in self.unit_decisions],
        }


def _block(decision_unit_id: str, rule_id: str, explanation: str) -> RouteDecision:
    hit = RuleHit(
        rule_id=rule_id,
        priority=-1,
        route="BLOCK",
        explanation=explanation,
        predicate_explanations=(),
    )
    return RouteDecision(decision_unit_id, "BLOCK", (hit,), (explanation,))


def _as_rules(document: Mapping[str, object], name: str) -> list[Mapping[str, object]]:
    rules = document.get("rules")
    if not isinstance(rules, list) or not all(isinstance(rule, Mapping) for rule in rules):
        raise PolicyError("Routing rules are invalid", code="ROUTING_CONFIGURATION_INVALID")
    return list(rules)


def _guard_key(condition: Mapping[str, object]) -> tuple[str, str, object, object]:
    field, operator = condition.get("field"), condition.get("operator")
    value = condition.get("value")
    if operator == "in" and isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        value = tuple(sorted(str(item) for item in value))
    if operator == "is_empty":
        value = None
    if not isinstance(field, str) or not isinstance(operator, str):
        raise PolicyError("Routing rule is malformed", code="ROUTING_CONFIGURATION_INVALID")
    return field, operator, value, condition.get("missing")


def _validate_configuration(
    bundle: PolicyBundle,
) -> tuple[list[Mapping[str, object]], Mapping[str, object]]:
    try:
        hard = bundle.documents["hard-rules.yaml"]
        routing = bundle.documents["routing.yaml"]
    except KeyError as error:
        raise PolicyError(
            "Required routing Policy is missing", code="ROUTING_CONFIGURATION_INVALID"
        ) from error
    rules = _as_rules(hard, "hard-rules.yaml") + _as_rules(routing, "routing.yaml")
    priorities: dict[int, set[str]] = defaultdict(set)
    for rule in rules:
        identifier, route, priority = rule.get("id"), rule.get("route"), rule.get("priority")
        explanation, match = rule.get("explanation"), rule.get("match")
        conditions = rule.get("conditions")
        if (
            not isinstance(identifier, str)
            or not identifier
            or not isinstance(route, str)
            or route not in _ROUTES
            or not isinstance(priority, int)
            or isinstance(priority, bool)
            or not isinstance(conditions, list)
            or not all(isinstance(condition, Mapping) for condition in conditions)
            or not isinstance(explanation, str)
            or not explanation.strip()
            or match not in {"all", "any"}
        ):
            raise PolicyError("Routing rule is malformed", code="ROUTING_CONFIGURATION_INVALID")
        priorities[priority].add(route)
        if route == "BLOCK":
            recovery = rule.get("recovery_conditions")
            if (
                not isinstance(recovery, list)
                or not recovery
                or not all(isinstance(item, str) and item.strip() for item in recovery)
            ):
                raise PolicyError(
                    "BLOCK rules require recovery conditions", code="ROUTING_BLOCK_RECOVERY_MISSING"
                )
        if route == "AUTO":
            guard_keys = {_guard_key(condition) for condition in conditions}
            if not _AUTO_GUARDS.issubset(guard_keys):
                raise PolicyError(
                    "AUTO rule lacks complete guards", code="ROUTING_AUTO_GUARDS_INCOMPLETE"
                )
    if any(len(routes) > 1 for routes in priorities.values()):
        raise PolicyError("Same-priority routes conflict", code="ROUTING_PRIORITY_CONFLICT")
    default = routing.get("default_route")
    if (
        not isinstance(default, Mapping)
        or default.get("id") != "ROUTE-DEFAULT-REVIEW"
        or default.get("route") != "REVIEW"
        or not isinstance(default.get("explanation"), str)
        or not default["explanation"].strip()
    ):
        raise PolicyError("Default REVIEW route is invalid", code="ROUTING_DEFAULT_INVALID")
    return rules, default


def _matches(
    rule: Mapping[str, object], facts: Mapping[str, object]
) -> tuple[bool, tuple[str, ...]]:
    conditions = rule["conditions"]
    if not isinstance(conditions, list):  # guaranteed by _validate_configuration
        raise PolicyError("Routing rule is malformed", code="ROUTING_CONFIGURATION_INVALID")
    results = tuple(
        evaluate_predicate(condition, facts)
        for condition in conditions
        if isinstance(condition, Mapping)
    )
    match = rule.get("match")
    if match == "all":
        matched = all(result.matched for result in results)
    elif match == "any":
        matched = any(result.matched for result in results)
    else:
        raise PolicyError(
            "Routing rule match mode is invalid", code="ROUTING_CONFIGURATION_INVALID"
        )
    return matched, tuple(result.explanation for result in results)


def _rule_sort_key(rule: Mapping[str, object]) -> tuple[int, str]:
    priority = rule.get("priority")
    return (-(priority if isinstance(priority, int) else -1), str(rule.get("id", "")))


def route_decision_unit(unit: Mapping[str, object], bundle: PolicyBundle) -> RouteDecision:
    """Route one unit, turning malformed Policy or incomplete facts into BLOCK."""
    identifier = unit.get("decision_unit_id")
    if not isinstance(identifier, str) or not identifier:
        return _block(
            "unknown", "ROUTING-DECISION-UNIT-INVALID", "Decision unit ID is required for routing."
        )
    try:
        rules, default = _validate_configuration(bundle)
        hits: list[RuleHit] = []
        for rule in sorted(rules, key=_rule_sort_key):
            matched, predicates = _matches(rule, unit)
            if matched:
                hits.append(
                    RuleHit(
                        rule_id=str(rule["id"]),
                        priority=rule["priority"] if isinstance(rule["priority"], int) else -1,
                        route=str(rule["route"]),
                        explanation=str(rule["explanation"]),
                        predicate_explanations=predicates,
                    )
                )
    except PolicyError as error:
        return _block(identifier, f"ROUTING-{error.code}", f"Routing blocked: {error.code}.")
    hits.sort(key=lambda hit: (-hit.priority, hit.rule_id))
    if not hits:
        default_priority = default.get("priority")
        default_hit = RuleHit(
            rule_id=str(default["id"]),
            priority=default_priority if isinstance(default_priority, int) else 0,
            route="REVIEW",
            explanation=str(default["explanation"]),
            predicate_explanations=(),
        )
        return RouteDecision(identifier, "REVIEW", (default_hit,), (default_hit.explanation,))
    effective = max((hit.route for hit in hits), key=ROUTE_ORDER.index)
    return RouteDecision(identifier, effective, tuple(hits), tuple(hit.explanation for hit in hits))


def _is_completed(unit: Mapping[str, object]) -> bool:
    return (
        unit.get("completed") is True
        or str(unit.get("status", unit.get("state", ""))).upper() == "COMPLETED"
    )


def summarize_task_routes(
    units: Sequence[Mapping[str, object]], bundle: PolicyBundle
) -> TaskRouteDecision:
    """Route units independently and aggregate only unfinished work."""
    decisions = tuple(route_decision_unit(unit, bundle) for unit in units)
    unfinished = [
        decision for unit, decision in zip(units, decisions, strict=True) if not _is_completed(unit)
    ]
    if not unfinished:
        return TaskRouteDecision("completed", decisions)
    return TaskRouteDecision(
        max((decision.effective_route for decision in unfinished), key=ROUTE_ORDER.index), decisions
    )


def route_task(task: Mapping[str, object], bundle: PolicyBundle) -> TaskRouteDecision:
    """Route a task record containing decision units."""
    units = task.get("decision_units")
    if not isinstance(units, list) or not all(isinstance(unit, Mapping) for unit in units):
        return TaskRouteDecision(
            "BLOCK",
            (_block("unknown", "ROUTING-DECISION-UNITS-INVALID", "Decision units are required."),),
        )
    return summarize_task_routes(units, bundle)


# The names below retain a compact API for callers introduced in later tasks.
evaluate_route = route_decision_unit
aggregate_routes = summarize_task_routes
