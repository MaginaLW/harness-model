"""Closed stdlib probes for installed native-engine safeguards.

These small detector cases isolate unrelated context; they do not establish a
complete target lifecycle. The parent runner binds copies, imports and reports.
"""

from __future__ import annotations

import ast
import inspect
import traceback
from collections.abc import Callable
from contextlib import ExitStack
from copy import deepcopy
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import patch

from aiflow.errors import ContractError, PolicyError

PROTOCOL = "installed-probe-v1"
CASE_SPECS: dict[str, tuple[tuple[str, dict[str, object]], ...]] = {
    "MUT-V2-001": (
        ("policy_complete", {"version": "2.6.0"}),
        ("policy_missing_targeted_mutation", {"error": "POLICY_CHECK_REFERENCE_INVALID"}),
    ),
    "MUT-V2-002": (
        ("verifier_blank", {"errors": ["VERIFIER_IMPLEMENTER_MISSING", "VERIFIER_ACTOR_REQUIRED"]}),
        ("verifier_distinct", {"actors": ["implementer", "independent-verifier"]}),
        ("verifier_same", {"error": "VERIFIER_ACTOR_NOT_INDEPENDENT"}),
    ),
    "MUT-V2-003": (
        ("approval_passing_checks", {"current": True, "mutation_calls": 1}),
        ("approval_failed_required_check", {"current": False, "mutation_calls": 0}),
    ),
    "MUT-V2-004": (
        (
            "gate_killed_mutations",
            {"checks_current": True, "mutation_killed": True, "mutation_calls": 1},
        ),
        (
            "gate_survived_mutation",
            {"checks_current": True, "mutation_killed": False, "mutation_calls": 1},
        ),
    ),
    "MUT-V2-005": (
        ("snapshot_unchanged", {"errors": [None, None], "same_snapshot": True}),
        ("snapshot_tampered", {"errors": ["EVIDENCE_SNAPSHOT_STALE", "EVIDENCE_SNAPSHOT_STALE"]}),
    ),
}
MUTANT_OBSERVATIONS: dict[str, dict[str, object]] = {
    "MUT-V2-001": {"error": None},
    "MUT-V2-002": {"error": None},
    "MUT-V2-003": {"current": True, "mutation_calls": 1},
    "MUT-V2-004": {"checks_current": True, "mutation_killed": True, "mutation_calls": 1},
    "MUT-V2-005": {"errors": [None, None]},
}
ASSERTION_ANCHORS = {
    "MUT-V2-001": "_policy_missing_targeted_mutation",
    "MUT-V2-002": "_verifier_same",
    "MUT-V2-003": "_approval_failed_required_check",
    "MUT-V2-004": "_gate_survived_mutation",
    "MUT-V2-005": "_snapshot_tampered",
}


def _bundle_root() -> Traversable:
    return files("aiflow").joinpath("_bundled_resources")


def _consumer_link(
    consumer: Callable[..., object], name: str, guard: Callable[..., object]
) -> None:
    """Check the loaded caller still names and resolves the actual guard."""
    if not isinstance(consumer, FunctionType):
        raise RuntimeError("Installed consumer is not a Python function")
    tree = ast.parse(inspect.getsource(consumer))
    if consumer.__globals__.get(name) is not guard or not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name
        for node in ast.walk(tree)
    ):
        raise RuntimeError("Installed consumer no longer references its declared guard")


def _contract_code(call: Callable[[], object]) -> str | None:
    try:
        call()
    except (ContractError, PolicyError) as error:
        return error.code
    return None


def _evidence(status: str = "passed") -> dict[str, Any]:
    # Minimal guard inputs, not a schema-valid public evidence artifact.
    from aiflow.evidence import verification_snapshot_sha256

    evidence: dict[str, Any] = {
        "schema_version": "2.0",
        "verification_level": "V2",
        "phase": "final",
        "mode": "local",
        "verifier_actor": "independent-verifier",
        "verifier_context_sha256": "a" * 64,
        "checks": [{"check_id": "required", "status": status}],
        "targeted_mutation": {"mutation_evidence_sha256": "b" * 64},
        "review_refs": {
            stage: {"review_id": "REV-0001", "context_sha256": "c" * 64}
            for stage in ("design", "implementation")
        },
    }
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    return evidence


def _isolate_context(module: ModuleType, stack: ExitStack, context: dict[str, Any]) -> None:
    from aiflow.mutation_evidence import TargetedMutationFacts

    for name in ("load_verifier_context", "build_verifier_context"):
        stack.enter_context(patch.object(module, name, lambda *_args: {}))
    stack.enter_context(
        patch.object(module, "validate_verifier_context_current", lambda *_args: None)
    )

    def mutation_facts(*_args: object) -> TargetedMutationFacts:
        context["mutation_calls"] += 1
        return TargetedMutationFacts(context["mutation_killed"], None, None, None, None, ())

    stack.enter_context(patch.object(module, "consume_targeted_mutation_evidence", mutation_facts))


def _setup(probe_id: str, case_id: str, stack: ExitStack, context: dict[str, Any]) -> None:
    if probe_id == "MUT-V2-001":
        import yaml

        from aiflow import policy
        from aiflow.resource_bundle import read_bundle

        _consumer_link(
            policy.load_policy_bundle, "_validate_cross_file", policy._validate_cross_file
        )
        _manifest, resources = read_bundle(_bundle_root())
        context["documents"] = {
            name: yaml.safe_load(resources[f"policy/{name}"].decode("utf-8"))
            for name in policy.POLICY_FILES
        }
        if case_id == "policy_missing_targeted_mutation":
            checks = context["documents"]["verification-levels.yaml"]["levels"][2]["checks"]
            context["documents"]["verification-levels.yaml"]["levels"][2]["checks"] = [
                check for check in checks if check["id"] != "targeted_mutation"
            ]
        context["module"] = policy
    elif probe_id == "MUT-V2-002":
        from aiflow import verification_service, verifier_service

        _consumer_link(
            verification_service.verify_task,
            "validate_verifier_actor",
            verifier_service.validate_verifier_actor,
        )
        context["module"] = verifier_service
    elif probe_id in {"MUT-V2-003", "MUT-V2-004"}:
        from aiflow import approval, gate

        module = approval if probe_id == "MUT-V2-003" else gate
        consumer = approval._evidence if probe_id == "MUT-V2-003" else gate.evaluate_gate
        guard_name = "_v2_evidence_current" if probe_id == "MUT-V2-003" else "_v2_gate_facts"
        _consumer_link(consumer, guard_name, getattr(module, guard_name))
        context.update(
            module=module,
            evidence=_evidence(
                "failed" if case_id == "approval_failed_required_check" else "passed"
            ),
            mutation_calls=0,
            mutation_killed=case_id != "gate_survived_mutation",
        )
        _isolate_context(module, stack, context)
        if probe_id == "MUT-V2-004":
            stack.enter_context(
                patch.object(
                    module,
                    "latest_review_assessment",
                    lambda *_args, **_kwargs: SimpleNamespace(
                        record={"review_id": "REV-0001", "context_sha256": "c" * 64}
                    ),
                )
            )
    else:
        from aiflow import approval, evidence, gate, verification_service

        for snapshot_consumer in (
            approval._v2_evidence_current,
            gate._v2_gate_facts,
            evidence.finalize_v2_evidence,
        ):
            _consumer_link(snapshot_consumer, "validate_v2_snapshot", evidence.validate_v2_snapshot)
        _consumer_link(
            verification_service._finalize_v2_task,
            "validate_v2_snapshot",
            evidence.validate_v2_snapshot,
        )
        context.update(module=evidence, evidence=_evidence())


def _policy_complete(context: dict[str, Any]) -> None:
    observed = {"version": context["module"]._validate_cross_file(context["documents"])}
    context["observed"] = observed
    assert observed == {"version": "2.6.0"}


def _policy_missing_targeted_mutation(context: dict[str, Any]) -> None:
    observed = {
        "error": _contract_code(
            lambda: context["module"]._validate_cross_file(context["documents"])
        )
    }
    context["observed"] = observed
    assert observed == {"error": "POLICY_CHECK_REFERENCE_INVALID"}


def _verifier_blank(context: dict[str, Any]) -> None:
    validate = context["module"].validate_verifier_actor
    observed = {
        "errors": [
            _contract_code(lambda: validate("", "independent-verifier")),
            _contract_code(lambda: validate("implementer", "")),
        ]
    }
    context["observed"] = observed
    assert observed == {"errors": ["VERIFIER_IMPLEMENTER_MISSING", "VERIFIER_ACTOR_REQUIRED"]}


def _verifier_distinct(context: dict[str, Any]) -> None:
    observed = {
        "actors": list(
            context["module"].validate_verifier_actor("implementer", "independent-verifier")
        )
    }
    context["observed"] = observed
    assert observed == {"actors": ["implementer", "independent-verifier"]}


def _verifier_same(context: dict[str, Any]) -> None:
    observed = {
        "error": _contract_code(
            lambda: context["module"].validate_verifier_actor("implementer", "implementer")
        )
    }
    context["observed"] = observed
    assert observed == {"error": "VERIFIER_ACTOR_NOT_INDEPENDENT"}


def _approval_call(context: dict[str, Any]) -> dict[str, object]:
    current = context["module"]._v2_evidence_current(
        Path.cwd(),
        "TASK-0001",
        context["evidence"],
        events=({"event_type": "implementation_started", "actor": "implementer"},),
        policy_checks=[{"id": "required", "required": True}],
    )
    return {"current": current, "mutation_calls": context["mutation_calls"]}


def _approval_passing_checks(context: dict[str, Any]) -> None:
    observed = _approval_call(context)
    context["observed"] = observed
    assert observed == {"current": True, "mutation_calls": 1}


def _approval_failed_required_check(context: dict[str, Any]) -> None:
    observed = _approval_call(context)
    context["observed"] = observed
    assert observed == {"current": False, "mutation_calls": 0}


def _gate_call(context: dict[str, Any]) -> dict[str, object]:
    facts = context["module"]._v2_gate_facts(
        Path.cwd(),
        "TASK-0001",
        context["evidence"],
        events=({"event_type": "implementation_started", "actor": "implementer"},),
        policy_checks=[{"id": "required", "required": True}],
        decision_unit_ids=[],
    )
    return {
        "checks_current": facts["v2_checks_current"],
        "mutation_killed": facts["v2_mutation_killed"],
        "mutation_calls": context["mutation_calls"],
    }


def _gate_killed_mutations(context: dict[str, Any]) -> None:
    observed = _gate_call(context)
    context["observed"] = observed
    assert observed == {"checks_current": True, "mutation_killed": True, "mutation_calls": 1}


def _gate_survived_mutation(context: dict[str, Any]) -> None:
    observed = _gate_call(context)
    context["observed"] = observed
    assert observed == {"checks_current": True, "mutation_killed": False, "mutation_calls": 1}


def _snapshot_unchanged(context: dict[str, Any]) -> None:
    module, original = context["module"], context["evidence"]
    final = deepcopy(original)
    final["phase"] = "pre_implementation_review"
    final["review_refs"]["implementation"] = {"review_id": "REV-0002", "context_sha256": "d" * 64}
    observed = {
        "errors": [
            _contract_code(lambda: module.validate_v2_snapshot(original)),
            _contract_code(lambda: module.validate_v2_snapshot(final)),
        ],
        "same_snapshot": module.verification_snapshot_sha256(original)
        == module.verification_snapshot_sha256(final),
    }
    context["observed"] = observed
    assert observed == {"errors": [None, None], "same_snapshot": True}


def _snapshot_tampered(context: dict[str, Any]) -> None:
    module, original = context["module"], context["evidence"]
    check_changed, mutation_changed = deepcopy(original), deepcopy(original)
    check_changed["checks"][0]["status"] = "failed"
    mutation_changed["targeted_mutation"]["mutation_evidence_sha256"] = "e" * 64
    observed = {
        "errors": [
            _contract_code(lambda: module.validate_v2_snapshot(check_changed)),
            _contract_code(lambda: module.validate_v2_snapshot(mutation_changed)),
        ]
    }
    context["observed"] = observed
    assert observed == {"errors": ["EVIDENCE_SNAPSHOT_STALE", "EVIDENCE_SNAPSHOT_STALE"]}


_CASE_CALLS: dict[str, Callable[[dict[str, Any]], None]] = {
    call.__name__.removeprefix("_"): call
    for call in (
        _policy_complete,
        _policy_missing_targeted_mutation,
        _verifier_blank,
        _verifier_distinct,
        _verifier_same,
        _approval_passing_checks,
        _approval_failed_required_check,
        _gate_killed_mutations,
        _gate_survived_mutation,
        _snapshot_unchanged,
        _snapshot_tampered,
    )
}


def _exception(error: Exception) -> dict[str, object]:
    return {
        "type": type(error).__name__,
        "message": str(error),
        "frames": [
            {"path": frame.filename, "line": frame.lineno, "function": frame.name}
            for frame in traceback.extract_tb(error.__traceback__)
        ],
    }


def _run_case(probe_id: str, case_id: str) -> dict[str, object]:
    context: dict[str, Any] = {}
    stack = ExitStack()
    result: dict[str, object] = {
        "id": case_id,
        "setup": "failed",
        "call": "not_run",
        "teardown": "not_run",
        "observed": None,
        "exception": None,
    }
    try:
        _setup(probe_id, case_id, stack, context)
        result["setup"] = "passed"
    except Exception as error:
        result["exception"] = _exception(error)
    else:
        try:
            _CASE_CALLS[case_id](context)
            result["call"] = "passed"
        except Exception as error:
            result["call"] = "failed"
            result["exception"] = _exception(error)
    finally:
        result["observed"] = context.get("observed")
        try:
            stack.close()
            result["teardown"] = "passed"
        except Exception as error:
            result["teardown"] = "failed"
            result["exception"] = _exception(error)
    return result


def run_probe(probe_id: str) -> dict[str, object]:
    """Run every fixed detector case; the parent alone attributes a mutation."""
    if not isinstance(probe_id, str) or probe_id not in CASE_SPECS:
        raise ValueError("Unknown installed probe")
    return {
        "protocol": PROTOCOL,
        "probe_id": probe_id,
        "cases": [_run_case(probe_id, case_id) for case_id, _observed in CASE_SPECS[probe_id]],
        "terminal": "complete",
    }
