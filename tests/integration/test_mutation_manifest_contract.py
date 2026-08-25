"""Repository-level contract and unchanged V2 safeguard tests for mutation declarations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiflow.approval as approval
import aiflow.gate as gate
from aiflow.mutation_evidence import TargetedMutationFacts
from aiflow.mutation_manifest import load_mutation_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

EXPECTED = (
    (
        "MUT-V2-001",
        "V2_REQUIRED_CHECK_SET",
        "src/aiflow/policy.py",
        "_validate_cross_file",
        "drop_targeted_mutation_required_check",
        "tests/unit/test_policy.py::test_v2_policy_requires_ordered_semantic_prefix_and_fixed_required_extras",
    ),
    (
        "MUT-V2-002",
        "V2_VERIFIER_INDEPENDENCE",
        "src/aiflow/verifier_service.py",
        "validate_verifier_actor",
        "allow_same_verifier_actor",
        "tests/integration/test_verify_command.py::test_v2_actor_rejections_happen_before_plan_or_runner",
    ),
    (
        "MUT-V2-003",
        "V2_CODE_APPROVAL_REQUIRES_PASSING_EVIDENCE",
        "src/aiflow/approval.py",
        "_v2_evidence_current",
        "allow_nonpassing_required_check",
        "tests/integration/test_mutation_manifest_contract.py::test_v2_code_approval_rejects_nonpassing_required_check",
    ),
    (
        "MUT-V2-004",
        "V2_GATE_REQUIRES_KILLED_MUTATIONS",
        "src/aiflow/gate.py",
        "_v2_gate_facts",
        "accept_non_killed_mutation",
        "tests/integration/test_mutation_manifest_contract.py::test_v2_gate_rejects_non_killed_mutation",
    ),
    (
        "MUT-V2-005",
        "V2_SNAPSHOT_BINDS_VERIFICATION_FACTS",
        "src/aiflow/evidence.py",
        "validate_v2_snapshot",
        "ignore_snapshot_mismatch",
        "tests/unit/test_evidence.py::test_v2_snapshot_rejects_mutation_of_bound_verification_facts",
    ),
)


def _declaration_tuple(declaration: Any) -> tuple[str, str, str, str, str, str]:
    return (
        declaration.mutation_id,
        declaration.safeguard_id,
        declaration.target,
        declaration.target_symbol,
        declaration.operator,
        declaration.expected_detector,
    )


def test_canonical_manifest_is_exactly_the_five_stable_v2_safeguards() -> None:
    manifest = load_mutation_manifest(REPOSITORY_ROOT)
    assert manifest.schema_version == "1.0"
    assert manifest.manifest_id == "phase-02-critical"
    assert manifest.scope == "phase-02-critical-safeguards"
    assert tuple(_declaration_tuple(item) for item in manifest.mutations) == EXPECTED
    assert all(item.expected_outcome == "killed" for item in manifest.mutations)


def test_canonical_manifest_references_existing_top_level_symbols_and_detectors() -> None:
    manifest = load_mutation_manifest(REPOSITORY_ROOT)
    for item in manifest.mutations:
        assert (REPOSITORY_ROOT / item.target).is_file()
        detector_file, function = item.expected_detector.split("::", maxsplit=1)
        assert (REPOSITORY_ROOT / detector_file).is_file()
        assert function.startswith("test_")


def test_canonical_manifest_loading_is_read_only_for_the_worktree() -> None:
    before = {
        path: path.read_bytes()
        for path in (
            REPOSITORY_ROOT / ".ai" / "mutations" / "phase-02-critical-manifest.json",
            REPOSITORY_ROOT / "src" / "aiflow" / "approval.py",
            REPOSITORY_ROOT / "src" / "aiflow" / "gate.py",
        )
    }
    load_mutation_manifest(REPOSITORY_ROOT)
    assert {path: path.read_bytes() for path in before} == before


def _patch_v2_context(monkeypatch: Any, module: Any) -> None:
    monkeypatch.setattr(module, "validate_v2_snapshot", lambda _evidence: None)
    monkeypatch.setattr(module, "current_implementer_actor", lambda _events: "implementer")
    monkeypatch.setattr(module, "validate_verifier_actor", lambda *_args: None)
    monkeypatch.setattr(module, "load_verifier_context", lambda *_args: {})
    monkeypatch.setattr(module, "build_verifier_context", lambda *_args: {})
    monkeypatch.setattr(module, "validate_verifier_context_current", lambda *_args: None)


def _final_evidence(
    *, check_status: str = "passed", mutation_outcome: str = "killed"
) -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "phase": "final",
        "mode": "local",
        "verifier_actor": "independent-verifier",
        "verifier_context_sha256": "a" * 64,
        "checks": [{"check_id": "required", "status": check_status}],
        "targeted_mutation": {
            "evidence_ref": (
                ".ai/tasks/TASK-0012/logs/MUTRUN-20260825T120000Z-"
                "0000000000000000/targeted-mutation/evidence.json"
            ),
            "mutation_evidence_sha256": "a" * 64,
            "manifest_ref": ".ai/mutations/phase-02-critical-manifest.json",
            "results": [
                {
                    "mutation_id": f"MUT-V2-{index:03d}",
                    "outcome": mutation_outcome,
                    "log_ref": None,
                }
                for index in range(1, 6)
            ],
        },
    }


def test_v2_code_approval_rejects_nonpassing_required_check(monkeypatch: Any) -> None:
    _patch_v2_context(monkeypatch, approval)
    downstream_calls: list[tuple[object, ...]] = []

    def passing_mutation_fact(*arguments: object) -> TargetedMutationFacts:
        downstream_calls.append(arguments)
        return TargetedMutationFacts(True, None, None, None, None, ())

    monkeypatch.setattr(approval, "consume_targeted_mutation_evidence", passing_mutation_fact)
    assert not approval._v2_evidence_current(
        REPOSITORY_ROOT,
        "TASK-0012",
        _final_evidence(check_status="failed"),
        events=(),
        policy_checks=[{"id": "required", "required": True}],
    )
    assert downstream_calls == []


def test_v2_gate_rejects_non_killed_mutation(monkeypatch: Any) -> None:
    _patch_v2_context(monkeypatch, gate)
    facts = gate._v2_gate_facts(
        REPOSITORY_ROOT,
        "TASK-0012",
        _final_evidence(mutation_outcome="survived"),
        events=(),
        policy_checks=[{"id": "required", "required": True}],
        decision_unit_ids=[],
    )
    assert facts["v2_checks_current"] is True
    assert facts["v2_mutation_killed"] is False


def test_v2_approval_and_gate_use_the_same_loader_backed_mutation_fact(
    monkeypatch: Any,
) -> None:
    evidence = _final_evidence()
    _patch_v2_context(monkeypatch, approval)
    _patch_v2_context(monkeypatch, gate)
    rejected = TargetedMutationFacts(
        False,
        "MUTATION_EVIDENCE_INVALID",
        None,
        None,
        None,
        (),
    )
    monkeypatch.setattr(approval, "consume_targeted_mutation_evidence", lambda *_args: rejected)
    monkeypatch.setattr(gate, "consume_targeted_mutation_evidence", lambda *_args: rejected)

    assert not approval._v2_evidence_current(
        REPOSITORY_ROOT,
        "TASK-0012",
        evidence,
        events=(),
        policy_checks=[{"id": "required", "required": True}],
    )
    rejected_gate = gate._v2_gate_facts(
        REPOSITORY_ROOT,
        "TASK-0012",
        evidence,
        events=(),
        policy_checks=[{"id": "required", "required": True}],
        decision_unit_ids=[],
    )
    assert rejected_gate["v2_mutation_killed"] is False

    mutation = evidence["targeted_mutation"]
    assert isinstance(mutation, dict)
    results = mutation["results"]
    assert isinstance(results, list)
    accepted = TargetedMutationFacts(
        True,
        None,
        str(mutation["evidence_ref"]),
        "a" * 64,
        ".ai/mutations/phase-02-critical-manifest.json",
        tuple(results),
    )
    monkeypatch.setattr(approval, "consume_targeted_mutation_evidence", lambda *_args: accepted)
    monkeypatch.setattr(gate, "consume_targeted_mutation_evidence", lambda *_args: accepted)
    assert approval._v2_evidence_current(
        REPOSITORY_ROOT,
        "TASK-0012",
        evidence,
        events=(),
        policy_checks=[{"id": "required", "required": True}],
    )
    accepted_gate = gate._v2_gate_facts(
        REPOSITORY_ROOT,
        "TASK-0012",
        evidence,
        events=(),
        policy_checks=[{"id": "required", "required": True}],
        decision_unit_ids=[],
    )
    assert accepted_gate["v2_mutation_killed"] is True
