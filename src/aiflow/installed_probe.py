"""Closed stdlib probes for installed native and Node V2 safeguards.

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
        ("policy_complete", {"version": "2.6.0", "node": {"version": "3.2.0"}}),
        (
            "policy_missing_targeted_mutation",
            {
                "error": "POLICY_CHECK_REFERENCE_INVALID",
                "node": {"error": "POLICY_CHECK_REFERENCE_INVALID"},
            },
        ),
    ),
    "MUT-V2-002": (
        (
            "verifier_blank",
            {
                "errors": ["VERIFIER_IMPLEMENTER_MISSING", "VERIFIER_ACTOR_REQUIRED"],
                "node_guard_linked": True,
            },
        ),
        (
            "verifier_distinct",
            {"actors": ["implementer", "independent-verifier"], "node_guard_linked": True},
        ),
        ("verifier_same", {"error": "VERIFIER_ACTOR_NOT_INDEPENDENT", "node_guard_linked": True}),
    ),
    "MUT-V2-003": (
        (
            "approval_passing_checks",
            {
                "current": True,
                "mutation_calls": 1,
                "node": {"current": True, "mutation_reached": True},
            },
        ),
        (
            "approval_failed_required_check",
            {
                "current": False,
                "mutation_calls": 0,
                "node": {"current": False, "mutation_reached": False},
            },
        ),
    ),
    "MUT-V2-004": (
        (
            "gate_killed_mutations",
            {
                "checks_current": True,
                "mutation_killed": True,
                "mutation_calls": 1,
                "node": {"checks_current": True, "mutation_killed": True},
            },
        ),
        (
            "gate_survived_mutation",
            {
                "checks_current": True,
                "mutation_killed": False,
                "mutation_calls": 1,
                "node": {"checks_current": True, "mutation_killed": False},
            },
        ),
    ),
    "MUT-V2-005": (
        (
            "snapshot_unchanged",
            {
                "errors": [None, None],
                "same_snapshot": True,
                "node": {"errors": [None, None], "same_snapshot": True},
            },
        ),
        (
            "snapshot_tampered",
            {
                "errors": ["EVIDENCE_SNAPSHOT_STALE", "EVIDENCE_SNAPSHOT_STALE"],
                "node": {"errors": ["EVIDENCE_SNAPSHOT_STALE"] * 5},
            },
        ),
    ),
}
MUTANT_OBSERVATIONS: dict[str, dict[str, object]] = {
    "MUT-V2-001": {"error": None, "node": {"error": None}},
    "MUT-V2-002": {"error": None, "node_guard_linked": True},
    "MUT-V2-003": {
        "current": True,
        "mutation_calls": 1,
        "node": {"current": True, "mutation_reached": True},
    },
    "MUT-V2-004": {
        "checks_current": True,
        "mutation_killed": True,
        "mutation_calls": 1,
        "node": {"checks_current": True, "mutation_killed": True},
    },
    "MUT-V2-005": {"errors": [None, None], "node": {"errors": [None] * 5}},
}
ASSERTION_ANCHORS = {
    "MUT-V2-001": "_policy_missing_targeted_mutation",
    "MUT-V2-002": "_verifier_same",
    "MUT-V2-003": "_approval_failed_required_check",
    "MUT-V2-004": "_gate_survived_mutation",
    "MUT-V2-005": "_snapshot_tampered",
}
_EXPECTED_OBSERVATIONS = {
    case_id: observed for cases in CASE_SPECS.values() for case_id, observed in cases
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


def _evidence(status: str = "passed", *, node_profile: bool = False) -> dict[str, Any]:
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
    if node_profile:
        evidence["schema_version"] = "3.2"
        evidence.pop("targeted_mutation")
        evidence["installed_mutation"] = {
            "reference": {
                "ref": ".ai/tasks/TASK-0001/logs/IMUT-0000000000000001/run.json",
                "size": 1,
                "sha256": "b" * 64,
            },
            "inputs_sha256": "b" * 64,
            "results": [[f"MUT-V2-{number:03d}", "killed"] for number in range(1, 6)],
        }
        evidence["node_binding"] = {
            "profile": "agent-bridge-node@2",
            "coverage": {"total": {"covered": 1}},
            "run": {"ref": "logs/IMUT-0000000000000001/node/run.json", "sha256": "b" * 64},
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
        node_documents = deepcopy(context["documents"])
        for document in node_documents.values():
            document["policy_version"] = policy.NODE_V2_POLICY_VERSION
        node_documents["verification-levels.yaml"] = {
            "schema_version": "1.0",
            "policy_version": policy.NODE_V2_POLICY_VERSION,
            "policy_kind": "verification_levels",
            "profile": {"id": policy.NODE_PROFILE_ID, "revision": policy.NODE_V2_PROFILE_REVISION},
            "levels": [
                {"id": "V0", "checks": deepcopy(list(policy.NODE_V0_CHECKS))},
                {"id": "V1", "checks": deepcopy(list(policy.NODE_V1_CHECKS))},
                {"id": "V2", "checks": deepcopy(list(policy.NODE_V2_CHECKS))},
            ],
        }
        context["node_documents"] = node_documents
        if case_id == "policy_missing_targeted_mutation":
            for documents in (context["documents"], context["node_documents"]):
                checks = documents["verification-levels.yaml"]["levels"][2]["checks"]
                documents["verification-levels.yaml"]["levels"][2]["checks"] = [
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
        for node_consumer in (
            verification_service._verify_node_local,
            verification_service._finalize_v2_task,
        ):
            _consumer_link(
                node_consumer, "validate_verifier_actor", verifier_service.validate_verifier_actor
            )
        context["node_guard_linked"] = True
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
        from aiflow.installed_mutations import InstalledMutationFacts
        from aiflow.node_execution import NodeEvidenceFacts

        context["node_evidence"] = _evidence(
            "failed" if case_id == "approval_failed_required_check" else "passed",
            node_profile=True,
        )
        installed_facts = InstalledMutationFacts(
            True,
            context["mutation_killed"],
            tuple((f"MUT-V2-{number:03d}", "killed") for number in range(1, 6)),
            (),
        )
        context["node_facts"] = NodeEvidenceFacts(
            True, True, (), None, None, None, installed_mutation_facts=installed_facts
        )
        context["node_mutation_reached"] = False
        if probe_id == "MUT-V2-003":

            def node_mutation_facts(_facts: NodeEvidenceFacts) -> InstalledMutationFacts:
                context["node_mutation_reached"] = True
                return installed_facts

            # Spy only on consumption of precomputed downstream facts. The
            # actual shared required-check guard remains the installed code.
            stack.enter_context(
                patch.object(
                    NodeEvidenceFacts, "installed_mutation_facts", property(node_mutation_facts)
                )
            )
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
        context.update(
            module=evidence, evidence=_evidence(), node_evidence=_evidence(node_profile=True)
        )


def _policy_complete(context: dict[str, Any]) -> None:
    observed = {
        "version": context["module"]._validate_cross_file(context["documents"]),
        "node": {"version": context["module"]._validate_cross_file(context["node_documents"])},
    }
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["policy_complete"]


def _policy_missing_targeted_mutation(context: dict[str, Any]) -> None:
    observed = {
        "error": _contract_code(
            lambda: context["module"]._validate_cross_file(context["documents"])
        ),
        "node": {
            "error": _contract_code(
                lambda: context["module"]._validate_cross_file(context["node_documents"])
            )
        },
    }
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["policy_missing_targeted_mutation"]


def _verifier_blank(context: dict[str, Any]) -> None:
    validate = context["module"].validate_verifier_actor
    observed = {
        "errors": [
            _contract_code(lambda: validate("", "independent-verifier")),
            _contract_code(lambda: validate("implementer", "")),
        ],
        "node_guard_linked": context["node_guard_linked"],
    }
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["verifier_blank"]


def _verifier_distinct(context: dict[str, Any]) -> None:
    observed = {
        "actors": list(
            context["module"].validate_verifier_actor("implementer", "independent-verifier")
        ),
        "node_guard_linked": context["node_guard_linked"],
    }
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["verifier_distinct"]


def _verifier_same(context: dict[str, Any]) -> None:
    observed = {
        "error": _contract_code(
            lambda: context["module"].validate_verifier_actor("implementer", "implementer")
        ),
        "node_guard_linked": context["node_guard_linked"],
    }
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["verifier_same"]


def _approval_call(context: dict[str, Any]) -> dict[str, object]:
    current = context["module"]._v2_evidence_current(
        Path.cwd(),
        "TASK-0001",
        context["evidence"],
        events=({"event_type": "implementation_started", "actor": "implementer"},),
        policy_checks=[{"id": "required", "required": True}],
    )
    node_current = context["module"]._v2_evidence_current(
        Path.cwd(),
        "TASK-0001",
        context["node_evidence"],
        events=({"event_type": "implementation_started", "actor": "implementer"},),
        policy_checks=[{"id": "required", "required": True}],
        node_facts=context["node_facts"],
    )
    return {
        "current": current,
        "mutation_calls": context["mutation_calls"],
        "node": {"current": node_current, "mutation_reached": context["node_mutation_reached"]},
    }


def _approval_passing_checks(context: dict[str, Any]) -> None:
    observed = _approval_call(context)
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["approval_passing_checks"]


def _approval_failed_required_check(context: dict[str, Any]) -> None:
    observed = _approval_call(context)
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["approval_failed_required_check"]


def _gate_call(context: dict[str, Any]) -> dict[str, object]:
    facts = context["module"]._v2_gate_facts(
        Path.cwd(),
        "TASK-0001",
        context["evidence"],
        events=({"event_type": "implementation_started", "actor": "implementer"},),
        policy_checks=[{"id": "required", "required": True}],
        decision_unit_ids=[],
    )
    node_facts = context["module"]._v2_gate_facts(
        Path.cwd(),
        "TASK-0001",
        context["node_evidence"],
        events=({"event_type": "implementation_started", "actor": "implementer"},),
        policy_checks=[{"id": "required", "required": True}],
        decision_unit_ids=[],
        node_facts=context["node_facts"],
    )
    return {
        "checks_current": facts["v2_checks_current"],
        "mutation_killed": facts["v2_mutation_killed"],
        "mutation_calls": context["mutation_calls"],
        "node": {
            "checks_current": node_facts["v2_checks_current"],
            "mutation_killed": node_facts["v2_mutation_killed"],
        },
    }


def _gate_killed_mutations(context: dict[str, Any]) -> None:
    observed = _gate_call(context)
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["gate_killed_mutations"]


def _gate_survived_mutation(context: dict[str, Any]) -> None:
    observed = _gate_call(context)
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["gate_survived_mutation"]


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
    node_original = context["node_evidence"]
    node_final = deepcopy(node_original)
    node_final["phase"] = "pre_implementation_review"
    node_final["review_refs"]["implementation"] = {
        "review_id": "REV-0002",
        "context_sha256": "d" * 64,
    }
    observed["node"] = {
        "errors": [
            _contract_code(lambda: module.validate_v2_snapshot(node_original)),
            _contract_code(lambda: module.validate_v2_snapshot(node_final)),
        ],
        "same_snapshot": module.verification_snapshot_sha256(node_original)
        == module.verification_snapshot_sha256(node_final),
    }
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["snapshot_unchanged"]


def _snapshot_tampered(context: dict[str, Any]) -> None:
    module, original = context["module"], context["evidence"]
    check_changed, mutation_changed = deepcopy(original), deepcopy(original)
    check_changed["checks"][0]["status"] = "failed"
    mutation_changed["targeted_mutation"]["mutation_evidence_sha256"] = "e" * 64
    observed: dict[str, object] = {
        "errors": [
            _contract_code(lambda: module.validate_v2_snapshot(check_changed)),
            _contract_code(lambda: module.validate_v2_snapshot(mutation_changed)),
        ]
    }
    node_original = context["node_evidence"]
    node_variants = [deepcopy(node_original) for _ in range(5)]
    node_variants[0]["checks"][0]["status"] = "failed"
    node_variants[1]["installed_mutation"]["reference"]["sha256"] = "e" * 64
    node_variants[2]["installed_mutation"]["results"][0][1] = "survived"
    node_variants[3]["node_binding"]["coverage"]["total"]["covered"] = 0
    node_variants[4]["node_binding"]["run"]["sha256"] = "e" * 64
    observed["node"] = {
        "errors": [
            _contract_code(lambda: module.validate_v2_snapshot(variant))
            for variant in node_variants
        ]
    }
    context["observed"] = observed
    assert observed == _EXPECTED_OBSERVATIONS["snapshot_tampered"]


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
