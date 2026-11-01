"""Logical Node V2 snapshot, shared-guard and pure-marker contracts.

Synthetic guard inputs isolate unrelated host material collection. They are not
ordinary-installation, process, product-test or completed Gate evidence.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_node_v0_contract import (
    code_marker_values as legacy_code_marker_values,  # noqa: F401 -- Shared pytest fixture.
)
from test_node_v2_contract import node_documents, write_policy

from aiflow.errors import AiflowError
from aiflow.evidence import validate_v2_snapshot, verification_snapshot_sha256
from aiflow.installed_mutations import InstalledMutationFacts
from aiflow.node_execution import NodeEvidenceFacts

PRODUCT_CASES = {
    "acceptance": [
        {
            "file": "tests/local/personal-dot-integration.test.ts",
            "full_name": "personal dot authenticated MCP + unified WeChat host (offline) "
            "persists duplicate input once, publishes one event, executes original text once "
            "and replies to the saved conversation once",
        },
        {
            "file": "tests/local/personal-dot-integration.test.ts",
            "full_name": "personal dot authenticated MCP + unified WeChat host (offline) "
            "rejects unauthenticated event calls, foreign targets and direct submissions "
            "before any dispatch",
        },
    ],
    "integration": [
        {
            "file": "tests/local/weixin-shared-integration.test.ts",
            "full_name": "synthetic Weixin, HTTP and shared runtime integration "
            "persists a polled task contract and returns its terminal result through "
            "the same shared host",
        },
        {
            "file": "tests/local/weixin-shared-integration.test.ts",
            "full_name": "synthetic Weixin, HTTP and shared runtime integration "
            "runs the isolated shared host with durable duplicate and uncertain reply handling",
        },
        {
            "file": "tests/local/weixin-shared-integration.test.ts",
            "full_name": "synthetic Weixin, HTTP and shared runtime integration "
            "shares route-bound tasks, reads, stop and client lifetime with a second client",
        },
    ],
}


def public_node_evidence(root: Path, *, level: str = "V2") -> dict:
    """Synthetic plan projections only; the receipts never establish execution."""
    from aiflow.node_execution import _public_execution, node_execution_contract
    from aiflow.policy import load_policy_bundle
    from aiflow.verification import NodePlanBindings, VerificationContext, parse_verification_plan

    owned = root / "roles"
    run_id = "IMUT-0123456789abcdef"
    context = VerificationContext(
        root,
        "TASK-0001",
        "a" * 40,
        "b" * 40,
        sys.executable,
        run_id,
        node_bindings=NodePlanBindings(
            str(owned / "node.exe"),
            str(owned / "npm-cli.js"),
            str(owned / "git.exe"),
            owned,
            owned / "user.npmrc",
            owned / "global.npmrc",
            owned / "coverage",
            owned / "expected.json",
            owned / "sources.json",
        ),
    )
    policy = load_policy_bundle(root)
    plan = parse_verification_plan(policy, context, level=level)
    receipt = {
        "returncode": 0,
        "timed_out": False,
        "duration_ms": 1,
        "stdout_size": 0,
        "stderr_size": 0,
        "stdout_sha256": hashlib.sha256(b"").hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "stdout_overflow": False,
        "stderr_overflow": False,
        "cleanup": "confirmed",
        "execution_error": False,
    }
    binding = {
        "profile": {"id": "agent-bridge-node", "revision": 2},
        "subject_tree": "c" * 40,
        "prepared": {
            "ref": "logs/node-prepared/" + "d" * 64 + "/prepared.json",
            "size": 1,
            "sha256": "d" * 64,
        },
        "run": {"ref": f"logs/{run_id}/node/run.json", "size": 1, "sha256": "e" * 64},
        "materials_sha256": "f" * 64,
        "semantic_contract_sha256": "1" * 64,
        "execution_contract_sha256": _digest(node_execution_contract(plan, context)),
        "environment_sha256": "2" * 64,
        "coverage": {
            "scope_files": 2,
            "total": {"covered": 85, "executable": 100, "threshold": 85},
            "changed": {
                "covered": 9,
                "executable": 10,
                "threshold": 90,
                "applicability": "applicable",
            },
            "method": "vitest-4.1.10-istanbul-vite-8.2.1-oxc-es2024-zero-hit-ts-ast-wire-v2",
        },
        "product_tests": {
            "report": {"ref": f"logs/{run_id}/node/vitest.json", "size": 1, "sha256": "6" * 64},
            "inventory_sha256": "7" * 64,
            **deepcopy(PRODUCT_CASES),
        },
    }
    evidence = {
        "schema_version": "3.2",
        "task_id": "TASK-0001",
        "decision_unit_ids": ["DU-001"],
        "repository_id": "11111111-2222-3333-4444-555555555555",
        "branch": "codex/synthetic",
        "base_commit": "a" * 40,
        "subject_commit": "b" * 40,
        "spec_sha256": "3" * 64,
        "policy_sha256": policy.sha256,
        "classification_input_sha256": "5" * 64,
        "verification_level": level,
        "mode": "local",
        "checks": [
            {
                "check_id": check.check_id,
                "required": True,
                "status": "passed",
                "executions": [
                    _public_execution(execution, receipt, context)
                    for execution in plan.executions
                    if check.check_id in execution.check_ids
                ],
            }
            for check in plan.checks
        ],
        "unverified_scenarios": [],
        "conclusion": "passed",
        "generated_at": "2026-11-01T00:00:00Z",
        "reproduce_command": [
            "python",
            "-m",
            "aiflow",
            "verify",
            "TASK-0001",
            "--actor",
            "independent-verifier",
            "--node-materials",
            "d" * 64,
            "--installed-mutations",
            run_id,
        ],
        "node_binding": binding,
        "node_binding_sha256": _digest(binding),
        "verifier_actor": "independent-verifier",
        "verifier_context_sha256": "8" * 64,
        "phase": "final",
        "review_refs": {
            stage: {"review_id": f"REV-{i:04d}", "context_sha256": str(i) * 64}
            for i, stage in enumerate(("design", "implementation"), 1)
        },
        "installed_mutation": {
            "reference": {
                "ref": f".ai/tasks/TASK-0001/logs/{run_id}/run.json",
                "size": 1,
                "sha256": "9" * 64,
            },
            "inputs_sha256": "0" * 64,
            "results": [[f"MUT-V2-{i:03d}", "killed"] for i in range(1, 6)],
        },
    }
    if level != "V2":
        for key in (
            "verifier_actor",
            "verifier_context_sha256",
            "phase",
            "review_refs",
            "installed_mutation",
        ):
            evidence.pop(key)
        del evidence["reproduce_command"][-2:]
        binding.pop("product_tests")
        if level == "V0":
            binding["coverage"] = None
        evidence["node_binding_sha256"] = _digest(binding)
    else:
        evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    return evidence


def _digest(value: object) -> str:
    from aiflow.node_execution import _canonical

    return hashlib.sha256(_canonical(value)).hexdigest()


@pytest.fixture
def public_node_v2(tmp_path):
    write_policy(tmp_path, node_documents())
    return public_node_evidence(tmp_path)


@pytest.mark.parametrize("level", ["V0", "V1"])
def test_second_node_profile_lower_levels_preserve_disjoint_public_contract(tmp_path, level):
    from aiflow.contracts import require_valid_contract
    from aiflow.evidence import validate_node_evidence

    write_policy(tmp_path, node_documents())
    evidence = public_node_evidence(tmp_path, level=level)
    validate_node_evidence(evidence, require_passed=True)
    require_valid_contract("evidence", evidence)
    assert evidence["schema_version"] == "3.2"
    assert evidence["node_binding"]["profile"]["revision"] == 2
    assert "product_tests" not in evidence["node_binding"]
    assert "installed_mutation" not in evidence
    assert "verification_snapshot_sha256" not in evidence
    evidence["phase"] = "final"
    with pytest.raises(AiflowError):
        validate_node_evidence(evidence)


@pytest.mark.parametrize("level", ["V0", "V1"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("attestation_head", "a" * 40),
        ("attestation_governance_only", True),
        ("conclusion", "provisional"),
    ],
)
def test_second_node_profile_lower_schema_rejects_ci_and_provisional_fields(
    tmp_path, level, field, value
):
    from aiflow.contracts import require_valid_contract
    from aiflow.evidence import validate_node_evidence

    write_policy(tmp_path, node_documents())
    evidence = public_node_evidence(tmp_path, level=level)
    require_valid_contract("evidence", evidence)
    validate_node_evidence(evidence)
    evidence[field] = value
    with pytest.raises(AiflowError):
        require_valid_contract("evidence", evidence)
    with pytest.raises(AiflowError):
        validate_node_evidence(evidence)


def test_public_node_v2_contract_has_exact_shared_executions_and_thirteen_checks(public_node_v2):
    from aiflow.contracts import require_valid_contract
    from aiflow.evidence import validate_node_evidence

    evidence = public_node_v2
    before = deepcopy(evidence)
    validate_node_evidence(evidence, require_passed=True)
    require_valid_contract("evidence", evidence)
    assert evidence == before
    assert [row["check_id"] for row in evidence["checks"]] == [
        "contract",
        "scope",
        "smoke",
        "node_build",
        "node_check",
        "diff_whitespace",
        "ts_coverage",
        "ts_total_lines",
        "ts_diff_lines",
        "acceptance",
        "integration",
        "targeted_mutation",
        "independent_verifier",
    ]
    executions = {row["check_id"]: row["executions"] for row in evidence["checks"]}
    assert len({item["execution_id"] for rows in executions.values() for item in rows}) == 10
    assert executions["acceptance"] == executions["integration"] == executions["ts_coverage"][:1]
    assert [row["execution_id"] for row in executions["ts_coverage"]] == ["EXEC-009", "EXEC-010"]
    for check in ("ts_total_lines", "ts_diff_lines", "targeted_mutation", "independent_verifier"):
        assert executions[check] == []


@pytest.mark.parametrize("phase", ["pre_implementation_review", "final"])
def test_public_node_v2_review_phase_shares_the_same_snapshot(public_node_v2, phase):
    from aiflow.contracts import require_valid_contract
    from aiflow.evidence import validate_node_evidence

    evidence = public_node_v2
    digest = evidence["verification_snapshot_sha256"]
    evidence["phase"] = phase
    if phase == "pre_implementation_review":
        evidence["review_refs"].pop("implementation")
    validate_node_evidence(evidence, require_passed=True)
    require_valid_contract("evidence", evidence)
    assert verification_snapshot_sha256(evidence) == digest


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), "3.1"),
        (("node_binding", "profile", "revision"), 1),
        (
            ("node_binding", "coverage", "method"),
            "vite-8.2.1-oxc-es2024-ast-v8-to-istanbul-zero-hit-v1",
        ),
        (("node_binding", "product_tests", "acceptance"), []),
        (
            ("node_binding", "product_tests", "integration", 0, "full_name"),
            "unrelated passing test",
        ),
        (("node_binding", "product_tests", "report", "ref"), "logs/other/node/vitest.json"),
        (
            ("installed_mutation", "reference", "ref"),
            ".ai/tasks/TASK-9999/logs/IMUT-0123456789abcdef/run.json",
        ),
        (
            ("installed_mutation", "reference", "ref"),
            ".ai/tasks/TASK-0001/logs/IMUT-9999999999999999/run.json",
        ),
        (("installed_mutation", "results", 0, 1), "survived"),
        (("checks", 9, "executions"), []),
        (("checks", 10, "executions", 0, "duration_ms"), 2),
    ],
)
def test_public_node_v2_rejects_independently_rehashed_contract_drift(public_node_v2, path, value):
    from aiflow.evidence import validate_node_evidence

    evidence = public_node_v2
    replace_value(evidence, path, value)
    evidence["node_binding_sha256"] = _digest(evidence["node_binding"])
    if evidence["schema_version"] == "3.2":
        evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    with pytest.raises(AiflowError):
        validate_node_evidence(evidence, require_passed=True)


@pytest.mark.parametrize(
    "path",
    [
        (),
        ("node_binding",),
        ("node_binding", "product_tests"),
        ("node_binding", "product_tests", "report"),
        ("node_binding", "product_tests", "acceptance", 0),
        ("installed_mutation",),
        ("installed_mutation", "reference"),
    ],
)
def test_public_node_v2_objects_remain_closed_after_rehash(public_node_v2, path):
    from aiflow.evidence import validate_node_evidence

    evidence = public_node_v2
    owner = evidence
    for key in path:
        owner = owner[key]
    owner["unregistered"] = True
    evidence["node_binding_sha256"] = _digest(evidence["node_binding"])
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    with pytest.raises(AiflowError):
        validate_node_evidence(evidence)


def guard_evidence(*, phase: str = "final") -> dict:
    """Minimal actual-guard inputs; deliberately not a public evidence certificate."""
    evidence = {
        "schema_version": "3.2",
        "verification_level": "V2",
        "phase": phase,
        "mode": "local",
        "subject_commit": "a" * 40,
        "policy_sha256": "b" * 64,
        "verifier_actor": "independent-verifier",
        "verifier_context_sha256": "c" * 64,
        "generated_at": "2026-11-01T00:00:00Z",
        "reproduce_command": ["python", "-m", "aiflow", "verify", "TASK-0001"],
        "checks": [{"check_id": "required", "required": True, "status": "passed"}],
        "node_binding": {
            "prepared": {"sha256": "d" * 64},
            "run": {"sha256": "e" * 64},
            "coverage": {"total": {"covered": 85, "executable": 100}},
            "product_tests": {
                "report": {"sha256": "f" * 64},
                "acceptance": [{"file": "tests/local/acceptance.test.ts", "full_name": "fixed"}],
            },
        },
        "installed_mutation": {
            "reference": {
                "ref": ".ai/tasks/TASK-0001/logs/IMUT-0123456789abcdef/run.json",
                "size": 1,
                "sha256": "1" * 64,
            },
            "inputs_sha256": "2" * 64,
            "results": [[f"MUT-V2-{i:03d}", "killed"] for i in range(1, 6)],
        },
        "review_refs": {
            "design": {"review_id": "REV-0001", "context_sha256": "3" * 64},
            "implementation": {"review_id": "REV-0002", "context_sha256": "4" * 64},
        },
    }
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    return evidence


def replace_value(value: dict, path: tuple, replacement: object) -> None:
    owner = value
    for part in path[:-1]:
        owner = owner[part]
    owner[path[-1]] = replacement


def test_node_snapshot_ignores_only_finalization_phase_and_implementation_reference():
    pre = guard_evidence(phase="pre_implementation_review")
    pre["review_refs"].pop("implementation")
    validate_v2_snapshot(pre)
    final = deepcopy(pre)
    final["phase"] = "final"
    final["review_refs"]["implementation"] = {"review_id": "REV-0009", "context_sha256": "9" * 64}
    validate_v2_snapshot(final)
    assert final["verification_snapshot_sha256"] == pre["verification_snapshot_sha256"]
    assert verification_snapshot_sha256(final) == verification_snapshot_sha256(pre)


@pytest.mark.parametrize(
    "path,value",
    [
        (("subject_commit",), "9" * 40),
        (("policy_sha256",), "9" * 64),
        (("verifier_actor",), "other-verifier"),
        (("verifier_context_sha256",), "9" * 64),
        (("generated_at",), "2026-11-02T00:00:00Z"),
        (("reproduce_command", 0), "other-python"),
        (("checks", 0, "status"), "failed"),
        (("node_binding", "prepared", "sha256"), "9" * 64),
        (("node_binding", "run", "sha256"), "9" * 64),
        (("node_binding", "coverage", "total", "covered"), 84),
        (("node_binding", "product_tests", "report", "sha256"), "9" * 64),
        (("node_binding", "product_tests", "acceptance", 0, "full_name"), "other"),
        (("installed_mutation", "reference", "sha256"), "9" * 64),
        (("installed_mutation", "inputs_sha256"), "9" * 64),
        (("installed_mutation", "results", 0, 1), "survived"),
        (("review_refs", "design", "context_sha256"), "9" * 64),
    ],
)
def test_node_snapshot_detects_every_bound_critical_fact_change(path, value):
    evidence = guard_evidence()
    replace_value(evidence, path, value)
    with pytest.raises(AiflowError) as caught:
        validate_v2_snapshot(evidence)
    assert caught.value.code == "EVIDENCE_SNAPSHOT_STALE"


@pytest.mark.parametrize(
    "version,level", [("3.1", "V2"), ("3.2", "V1"), ("3.2", "V0"), ("4.0", "V2")]
)
def test_shared_snapshot_does_not_admit_unimplemented_versions_or_strengths(version, level):
    value = {"schema_version": version, "verification_level": level, "review_refs": {}}
    with pytest.raises(AiflowError):
        verification_snapshot_sha256(value)


def node_facts(*, killed: bool = True, current: bool = True) -> NodeEvidenceFacts:
    installed = InstalledMutationFacts(
        current,
        killed,
        tuple((f"MUT-V2-{i:03d}", "killed" if killed else "survived") for i in range(1, 6)),
        () if current and killed else ("logical-negative",),
    )
    return NodeEvidenceFacts(
        current,
        current and killed,
        () if current and killed else ("logical-negative",),
        "a" * 64,
        "b" * 64,
        "IMUT-0123456789abcdef",
        installed_mutation_facts=installed,
    )


def isolate_unrelated_context(monkeypatch, module) -> list:
    """Preserve actual snapshot/actor/check/mutation guards; isolate context storage."""
    attempts = []
    monkeypatch.setattr(module, "load_verifier_context", lambda *_: {})
    monkeypatch.setattr(module, "build_verifier_context", lambda *_: {})
    monkeypatch.setattr(module, "validate_verifier_context_current", lambda *_: None)

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("Node guard fell back to native mutation execution/replay")

    monkeypatch.setattr(module, "consume_targeted_mutation_evidence", forbidden)
    return attempts


@pytest.mark.parametrize("status", ["passed", "failed", "unverified"])
@pytest.mark.parametrize("killed", [True, False])
def test_shared_code_guard_uses_node_required_checks_and_supplied_installed_facts(
    monkeypatch, status, killed
):
    import aiflow.approval as approval

    attempts = isolate_unrelated_context(monkeypatch, approval)
    evidence = guard_evidence()
    evidence["checks"][0]["status"] = status
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    result = approval._v2_evidence_current(
        Path("logical-only"),
        "TASK-0001",
        evidence,
        events=[{"event_type": "implementation_started", "actor": "implementer"}],
        policy_checks=[{"id": "required", "required": True}],
        node_facts=node_facts(killed=killed),
    )
    assert result is (status == "passed" and killed)
    assert attempts == []


@pytest.mark.parametrize(
    "fault",
    [
        "pre",
        "same-actor",
        "stale-snapshot",
        "missing-check",
        "duplicate-check",
        "missing-node-facts",
        "stale-node-facts",
    ],
)
def test_shared_node_code_guard_has_no_success_fallback(monkeypatch, fault):
    import aiflow.approval as approval

    attempts = isolate_unrelated_context(monkeypatch, approval)
    evidence = guard_evidence()
    facts = node_facts()
    if fault == "pre":
        evidence["phase"] = "pre_implementation_review"
    elif fault == "same-actor":
        evidence["verifier_actor"] = "implementer"
        evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    elif fault == "stale-snapshot":
        evidence["checks"][0]["status"] = "failed"
    elif fault == "missing-check":
        evidence["checks"] = []
        evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    elif fault == "duplicate-check":
        evidence["checks"].append(deepcopy(evidence["checks"][0]))
        evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    elif fault == "missing-node-facts":
        facts = None
    else:
        facts = node_facts(current=False)
    assert (
        approval._v2_evidence_current(
            Path("logical-only"),
            "TASK-0001",
            evidence,
            events=[{"event_type": "implementation_started", "actor": "implementer"}],
            policy_checks=[{"id": "required", "required": True}],
            node_facts=facts,
        )
        is False
    )
    assert attempts == []


@pytest.mark.parametrize("killed", [True, False])
def test_shared_node_gate_retains_the_actual_installed_passed_guard(monkeypatch, killed):
    import aiflow.gate as gate

    attempts = isolate_unrelated_context(monkeypatch, gate)
    evidence = guard_evidence()

    def assessment(_root, _task, stage, **kwargs):
        if stage == "implementation":
            assert (
                kwargs["verification_snapshot_sha256"] == evidence["verification_snapshot_sha256"]
            )
        return SimpleNamespace(record=dict(evidence["review_refs"][stage]))

    monkeypatch.setattr(gate, "latest_review_assessment", assessment)
    facts = gate._v2_gate_facts(
        Path("logical-only"),
        "TASK-0001",
        evidence,
        events=({"event_type": "implementation_started", "actor": "implementer"},),
        policy_checks=[{"id": "required", "required": True}],
        decision_unit_ids=["DU-001"],
        node_facts=node_facts(killed=killed),
    )
    assert facts["v2_final_evidence"] is True
    assert facts["v2_snapshot_current"] is True
    assert facts["v2_verifier_independent"] is True
    assert facts["v2_context_current"] is True
    # A failed Node material aggregate stops before review assessment.
    assert facts["v2_reviews_current"] is killed
    assert facts["v2_checks_current"] is True
    assert facts["v2_mutation_killed"] is killed
    assert attempts == []


@pytest.fixture
def node_v2_marker_values(request):
    """Upgrade the existing real marker grammar's logical fixture to snapshot review."""
    from aiflow.review_service import _context_digest

    values = request.getfixturevalue("legacy_code_marker_values")
    values["current_approvals"] = deepcopy(values["current_approvals"])
    context = values["review_context"]
    context["schema_version"] = "2.0"
    context.pop("evidence_sha256")
    context["verification_snapshot_sha256"] = "7" * 64
    context["context_sha256"] = _context_digest(context)
    values["verification_snapshot_sha256"] = "7" * 64
    values["implementation_review"]["context_sha256"] = context["context_sha256"]
    values["current_events"][-1]["payload"]["context_sha256"] = context["context_sha256"]
    values["marker"]["event"]["payload"]["structured_review"]["context_sha256"] = context[
        "context_sha256"
    ]
    return values


@pytest.mark.parametrize("phase", ["pending", "ledger_written", "event_applied"])
def test_node_v2_code_marker_is_pure_and_preserves_all_transaction_phases(
    monkeypatch, node_v2_marker_values, phase
):
    import aiflow.approval as approval
    import aiflow.node_execution as execution
    import aiflow.review_service as reviews

    values = node_v2_marker_values
    if phase != "pending":
        values["current_approvals"] = deepcopy(values["marker"]["approvals"])
    if phase == "event_applied":
        values["current_task"] = deepcopy(values["marker"]["task"])
        values["current_events"].append(deepcopy(values["marker"]["event"]))
    before = deepcopy(values)
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("Pure marker validation attempted recovery, process or replay")

    for owner, name in [
        (subprocess, "run"),
        (subprocess, "Popen"),
        (execution, "recheck_node_evidence"),
        (reviews, "build_review_context"),
        (approval, "_complete_marker"),
        (approval, "_v2_evidence_current"),
        (Path, "write_text"),
        (Path, "write_bytes"),
        (Path, "mkdir"),
    ]:
        monkeypatch.setattr(owner, name, forbidden)
    approval._validate_node_code_approval_marker(**values)
    assert values == before
    assert attempts == []


@pytest.mark.parametrize(
    "fault",
    [
        "review-snapshot",
        "approval-final-sha",
        "wrong-snapshot-argument",
        "latest-review",
        "prefix",
        "subject",
        "classification",
        "extra-context-evidence",
    ],
)
def test_node_v2_marker_binds_snapshot_review_and_full_final_approval_independently(
    node_v2_marker_values, fault
):
    import aiflow.approval as approval
    from aiflow.review_service import _context_digest

    values = node_v2_marker_values
    if fault == "approval-final-sha":
        values["evidence_sha256"] = "f" * 64
    elif fault == "wrong-snapshot-argument":
        values["verification_snapshot_sha256"] = values["evidence_sha256"]
    elif fault == "latest-review":
        values["current_events"][-1]["payload"]["review_id"] = "REV-9999"
    elif fault == "prefix":
        values["marker"]["approvals"][0]["reason"] = "rewritten prior approval"
    elif fault == "subject":
        values["current_task"]["subject_commit"] = "f" * 40
    else:
        context = values["review_context"]
        if fault == "review-snapshot":
            context["verification_snapshot_sha256"] = "f" * 64
        elif fault == "classification":
            context["classification_input_sha256"] = "f" * 64
        else:
            context["evidence_sha256"] = values["evidence_sha256"]
        context["context_sha256"] = _context_digest(context)
        values["implementation_review"]["context_sha256"] = context["context_sha256"]
        values["current_events"][-1]["payload"]["context_sha256"] = context["context_sha256"]
        values["marker"]["event"]["payload"]["structured_review"]["context_sha256"] = context[
            "context_sha256"
        ]
    with pytest.raises(AiflowError):
        approval._validate_node_code_approval_marker(**values)


V2_READY_FACTS = (
    "v2_final_evidence",
    "v2_snapshot_current",
    "v2_verifier_independent",
    "v2_context_current",
    "v2_reviews_current",
    "v2_checks_current",
    "v2_mutation_killed",
)


@pytest.mark.parametrize("missing", V2_READY_FACTS)
@pytest.mark.parametrize("value", [None, False, 1])
def test_node_v2_code_freshness_requires_every_explicit_shared_guard_fact(
    public_node_v2, missing, value
):
    from aiflow.freshness import evaluate_freshness

    evidence = public_node_v2
    digest = _digest(evidence)
    current = {
        "node_policy": True,
        "verification_level": "V2",
        "node_evidence_current": True,
        "node_evidence_passed": True,
        "node_evidence_sha256": digest,
        "node_materials_sha256": evidence["node_binding"]["materials_sha256"],
        "evidence_sha256": digest,
        "evidence_current": True,
        **{name: True for name in V2_READY_FACTS},
    }
    approval = {"evidence_sha256": digest}
    assert evaluate_freshness("code_approval", approval, current).status == "fresh"
    if value is None:
        current.pop(missing)
    else:
        current[missing] = value
    result = evaluate_freshness("code_approval", approval, current)
    assert result.status == "stale"
    assert result.reason_codes == ("FRESHNESS_EVIDENCE_NOT_PASSED",)


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "pre",
        "pre-reviewed",
        "auto-pre",
        "auto-pre-reviewed",
        "snapshot",
        "context",
        "review",
        "same-actor",
        "check",
        "mutations",
        "node",
    ],
)
def test_node_v2_status_uses_actual_shared_final_guards_and_never_recovers_or_writes(
    public_node_v2,
    tmp_path,
    monkeypatch,
    fault,
):
    from dataclasses import replace

    from initialization_helpers import snapshot_tree
    from test_installed_mutation_transactions import pure_guard

    import aiflow.approval as approval_service
    import aiflow.gate as gate
    import aiflow.node_execution as execution
    import aiflow.review_service as reviews
    import aiflow.status_service as status
    from aiflow.errors import ContractError
    from aiflow.task_service import TaskRecord

    evidence = public_node_v2
    pre = fault in {"pre", "pre-reviewed", "auto-pre", "auto-pre-reviewed"}
    reviewed = fault in {"pre-reviewed", "auto-pre-reviewed"}
    auto = fault in {"auto-pre", "auto-pre-reviewed"}
    if pre:
        evidence["phase"] = "pre_implementation_review"
        evidence["review_refs"].pop("implementation")
    elif fault == "snapshot":
        evidence["generated_at"] = "2026-11-02T00:00:00Z"
    elif fault == "same-actor":
        evidence["verifier_actor"] = evidence["reproduce_command"][6] = "implementer"
        evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    elif fault == "check":
        evidence["checks"][0]["status"] = "failed"
        evidence["conclusion"] = "failed"
        evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    directory = tmp_path / ".ai/tasks/TASK-0001"
    directory.mkdir(parents=True)
    marker = directory / "approval_pending.json"
    marker.write_bytes(b"unfinished marker must remain untouched\n")
    (directory / "evidence.json").write_bytes(execution._canonical(evidence))
    spec = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "decision_unit_id": "DU-001",
        "approval_type": "spec",
        "actor": "project-owner",
        "reason": "Logical status fixture",
        "approved_at": evidence["generated_at"],
        **{
            key: evidence[key]
            for key in ("base_commit", "subject_commit", "spec_sha256", "policy_sha256")
        },
    }
    code = {**spec, "approval_type": "code", "evidence_sha256": _digest(evidence)}
    (directory / "approvals.json").write_bytes(execution._canonical([spec, code]))
    task = {
        **{
            key: evidence[key]
            for key in ("task_id", "repository_id", "branch", "base_commit", "subject_commit")
        },
        "goal": "Logical read-only status",
        "current_state": "APPROVED_FOR_MERGE" if auto else "WAITING_FOR_FINAL_REVIEW",
        "decision_units": [{"decision_unit_id": "DU-001"}],
    }
    events = ({"event_type": "implementation_started", "actor": "implementer"},)
    classification = {
        "effective_route": "AUTO" if auto else "REVIEW",
        "effective_verification_level": "V2",
        "classifications": [{"decision_unit_id": "DU-001", "route": "AUTO" if auto else "REVIEW"}],
        **{
            key: evidence[key]
            for key in (
                "base_commit",
                "subject_commit",
                "policy_sha256",
                "classification_input_sha256",
            )
        },
    }
    current = {
        **{
            key: evidence[key]
            for key in (
                "task_id",
                "repository_id",
                "branch",
                "base_commit",
                "subject_commit",
                "spec_sha256",
                "policy_sha256",
                "classification_input_sha256",
            )
        },
        "node_policy": True,
        "verification_level": "V2",
        "governance_only": True,
    }
    monkeypatch.setattr(status, "read_task_record_strict", lambda *_: TaskRecord(task, events))
    monkeypatch.setattr(
        status,
        "collect_git_context",
        lambda *_: SimpleNamespace(
            head=evidence["subject_commit"], worktree_dirty=True, dirty_paths=()
        ),
    )
    monkeypatch.setattr(
        status,
        "_classification",
        lambda *_: (classification["effective_route"], "V2", classification, False),
    )
    monkeypatch.setattr(status, "_current_facts", lambda *_args, **_kwargs: dict(current))
    attempts = isolate_unrelated_context(monkeypatch, gate)
    if fault == "context":

        def stale_context(*_):
            raise ContractError("Synthetic stale verifier context")

        monkeypatch.setattr(gate, "validate_verifier_context_current", stale_context)

    def assessment(_root, _task, stage, **kwargs):
        if stage == "implementation":
            assert (
                kwargs["verification_snapshot_sha256"] == evidence["verification_snapshot_sha256"]
            )
        reference = dict(
            evidence["review_refs"].get(
                stage, {"review_id": "REV-0002", "context_sha256": "2" * 64}
            )
        )
        if fault == "review":
            reference["context_sha256"] = "0" * 64
        return SimpleNamespace(record=reference)

    monkeypatch.setattr(gate, "latest_review_assessment", assessment)
    status_reviews = []

    def current_implementation_review(_root, _task, stage, **kwargs):
        assert stage == "implementation"
        assert kwargs["decision_unit_ids"] == ["DU-001"]
        assert kwargs["verification_snapshot_sha256"] == evidence["verification_snapshot_sha256"]
        assert kwargs.get("evidence_sha256") is None
        status_reviews.append(kwargs)
        if not reviewed:
            raise ContractError(
                "Logical missing/stale implementation review", code="REVIEW_RECORD_STALE"
            )
        return SimpleNamespace(record={"outcome": "APPROVE"})

    monkeypatch.setattr(reviews, "latest_review_assessment", current_implementation_review)
    derived = replace(
        node_facts(killed=fault != "mutations", current=fault != "node"),
        evidence_sha256=_digest(evidence),
        materials_sha256=evidence["node_binding"]["materials_sha256"],
    )
    rechecks = []

    def recheck(root, task_id, value):
        rechecks.append((root, task_id, value))
        return derived

    def no_recovery(*args, **kwargs):
        pytest.fail("Status attempted approval recovery")

    monkeypatch.setattr(execution, "recheck_node_evidence", recheck)
    monkeypatch.setattr(approval_service, "_complete_marker", no_recovery)
    before = snapshot_tree(tmp_path)
    with pure_guard(monkeypatch):
        summary = status.summarize_task(tmp_path, "TASK-0001")
    assert snapshot_tree(tmp_path) == before
    assert len(rechecks) == 1
    assert attempts == []
    assert summary.approvals == (
        "not_applicable" if auto else "current" if fault is None else "stale"
    )
    if pre:
        assert summary.evidence == "awaiting_implementation_review_or_finalization"
        assert summary.missing_conditions == (
            ("finalization",) if reviewed else ("implementation_review", "finalization")
        )
        assert len(status_reviews) == 1
        assert summary.classification == "fresh"
        if auto:
            assert summary.merge_readiness == "not_ready"
    else:
        assert status_reviews == []
    assert ("code_approved" in summary.next_events) is (fault is None)


@pytest.fixture
def consumer_inputs(public_node_v2, tmp_path):
    """Bound logical authority inputs; never completed installed lifecycle proof."""
    import json

    import aiflow.node_execution as execution
    from aiflow.review import REQUIRED_REVIEW_SECTIONS
    from aiflow.specification import specification_digest
    from aiflow.task_service import TaskRecord

    evidence = public_node_v2
    task = json.loads(
        (Path(__file__).parents[2] / "tests/fixtures/contracts/valid/task.json").read_text("utf8")
    )
    task.update(
        {
            key: evidence[key]
            for key in ("task_id", "repository_id", "branch", "base_commit", "subject_commit")
        }
    )
    task.update(
        current_state="WAITING_FOR_FINAL_REVIEW",
        frozen_spec_sha256=specification_digest("Logical frozen specification\n"),
        spec_frozen_at=evidence["generated_at"],
    )
    directory = tmp_path / ".ai/tasks/TASK-0001"
    directory.mkdir(parents=True)
    (directory / "approvals.json").write_bytes(b"[]")
    (directory / "spec.md").write_text("Logical frozen specification\n", encoding="utf8")
    bodies = {key: "Bound logical authority inputs." for key in REQUIRED_REVIEW_SECTIONS}
    bodies.update(
        evidence="已验证：逻辑合同。\n未验证：安装运行。",
        questions="- Does the snapshot match?",
        recommendation="APPROVE",
    )
    (directory / "review-package.md").write_text(
        "\n\n".join(
            f"## {title}\n\n{bodies[key]}" for key, title in REQUIRED_REVIEW_SECTIONS.items()
        ),
        encoding="utf8",
    )
    evidence["spec_sha256"] = task["frozen_spec_sha256"]
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    (directory / "evidence.json").write_bytes(execution._canonical(evidence))
    classification = {
        **{
            key: evidence[key]
            for key in (
                "base_commit",
                "subject_commit",
                "policy_sha256",
                "classification_input_sha256",
            )
        },
        "effective_route": "REVIEW",
        "effective_verification_level": "V2",
        "classifications": [
            {"decision_unit_id": "DU-001", "route": "REVIEW", "verification_level": "V2"}
        ],
    }
    events = ({"event_type": "implementation_started", "actor": "implementer"},)
    reviews = {
        stage: {"revision": 1, "review_stage": stage, **evidence["review_refs"][stage]}
        for stage in ("design", "implementation")
    }
    return SimpleNamespace(
        root=tmp_path,
        directory=directory,
        task=task,
        record=TaskRecord(task, events),
        evidence=evidence,
        classification=classification,
        reviews=reviews,
    )


def consumer_authority(monkeypatch, module, inputs):
    """Keep public consumers and shared guards; hold unrelated authority constant."""
    from dataclasses import replace

    import aiflow.node_execution as execution

    monkeypatch.setattr(module, "read_task_record_strict", lambda *_: inputs.record)
    monkeypatch.setattr(
        module,
        "parse_decision_units",
        lambda *_: ({"decision_unit_id": "DU-001", "completed": True},),
    )
    monkeypatch.setattr(
        module,
        "current_classification_input_digest",
        lambda *_: (inputs.evidence["classification_input_sha256"], False),
    )
    actual_read = module.read_task_json

    def read(root, task, name, **kwargs):
        if name == "classification.json":
            return inputs.classification
        return actual_read(root, task, name, **kwargs)

    monkeypatch.setattr(module, "read_task_json", read)
    isolate_unrelated_context(monkeypatch, module)
    facts = replace(
        node_facts(),
        evidence_sha256=_digest(inputs.evidence),
        materials_sha256=inputs.evidence["node_binding"]["materials_sha256"],
    )
    rechecks = []

    def recheck(root, task, value):
        rechecks.append((root, task, value))
        return facts

    monkeypatch.setattr(execution, "recheck_node_evidence", recheck)
    return facts, rechecks


@pytest.mark.parametrize("phase", ["pre_implementation_review", "final"])
def test_actual_code_approval_entry_requires_final_and_selects_snapshot_review_before_any_write(
    consumer_inputs,
    monkeypatch,
    phase,
):
    from initialization_helpers import snapshot_tree
    from test_installed_mutation_transactions import pure_guard

    import aiflow.approval as approval
    import aiflow.node_execution as execution
    from aiflow.review_service import ReviewAssessment

    inputs = consumer_inputs
    evidence = inputs.evidence
    evidence["phase"] = phase
    if phase != "final":
        evidence["review_refs"].pop("implementation")
    (inputs.directory / "evidence.json").write_bytes(execution._canonical(evidence))
    _facts, rechecks = consumer_authority(monkeypatch, approval, inputs)
    monkeypatch.setattr(approval, "_governance_only", lambda *_: True)
    assessments, markers = [], []

    def assessment(_root, _task, stage, **kwargs):
        assessments.append((stage, kwargs))
        if stage == "implementation":
            assert kwargs["evidence_sha256"] is None
            assert (
                kwargs["verification_snapshot_sha256"] == evidence["verification_snapshot_sha256"]
            )
        return ReviewAssessment({}, inputs.reviews[stage])

    class WriteBoundaryReached(BaseException):
        pass

    def write(path, value):
        assert path.name == "approval_pending.json"
        markers.append(value)
        raise WriteBoundaryReached()

    monkeypatch.setattr(approval, "latest_review_assessment", assessment)
    monkeypatch.setattr(approval, "atomic_write_json", write)
    before = snapshot_tree(inputs.root)
    with pure_guard(monkeypatch):
        if phase == "final":
            with pytest.raises(WriteBoundaryReached):
                approval.approve_task(
                    inputs.root,
                    "TASK-0001",
                    approval_type="code",
                    actor="project-owner",
                    reason="Logical write-boundary test",
                )
        else:
            with pytest.raises(AiflowError) as caught:
                approval.approve_task(
                    inputs.root,
                    "TASK-0001",
                    approval_type="code",
                    actor="project-owner",
                    reason="Logical pre rejection",
                )
            assert caught.value.code == "CODE_EVIDENCE_STALE"
    assert snapshot_tree(inputs.root) == before
    assert len(rechecks) == 1
    assert [stage for stage, _ in assessments] == ["implementation", "design"]
    assert bool(markers) is (phase == "final")
    if markers:
        candidate = markers[0]["event"]["payload"]["approvals"][0]
        assert candidate["evidence_sha256"] == _digest(evidence)
        assert candidate["evidence_sha256"] != evidence["verification_snapshot_sha256"]


@pytest.mark.parametrize("phase", ["pre_implementation_review", "final"])
def test_actual_gate_entry_reaches_shared_node_v2_facts_and_still_requires_real_approvals(
    consumer_inputs,
    monkeypatch,
    phase,
):
    from initialization_helpers import snapshot_tree
    from test_installed_mutation_transactions import pure_guard

    import aiflow.gate as gate
    import aiflow.node_execution as execution

    inputs = consumer_inputs
    inputs.task["current_state"] = "APPROVED_FOR_MERGE"
    evidence = inputs.evidence
    evidence["phase"] = phase
    if phase != "final":
        evidence["review_refs"].pop("implementation")
    (inputs.directory / "evidence.json").write_bytes(execution._canonical(evidence))
    facts, rechecks = consumer_authority(monkeypatch, gate, inputs)
    monkeypatch.setattr(
        gate,
        "collect_git_context",
        lambda *_: SimpleNamespace(
            head=evidence["subject_commit"],
            repository_id=evidence["repository_id"],
            branch=evidence["branch"],
        ),
    )
    monkeypatch.setattr(
        gate,
        "collect_verification_changed_paths",
        lambda *_args, **_kwargs: SimpleNamespace(committed=(), attestation=(), worktree=()),
    )
    monkeypatch.setattr(
        gate, "assess_scope", lambda *_args, **_kwargs: SimpleNamespace(passed=True)
    )
    monkeypatch.setattr(
        gate, "assess_governance_only_scope", lambda *_args, **_kwargs: SimpleNamespace(passed=True)
    )
    monkeypatch.setattr(
        gate,
        "route_task",
        lambda *_: SimpleNamespace(
            effective_route="REVIEW",
            unit_decisions=(SimpleNamespace(decision_unit_id="DU-001", effective_route="REVIEW"),),
        ),
    )
    monkeypatch.setattr(
        gate,
        "verification_for_task",
        lambda *_: SimpleNamespace(
            level="V2", unit_decisions=(SimpleNamespace(decision_unit_id="DU-001", level="V2"),)
        ),
    )
    monkeypatch.setattr(gate, "commits_are_ancestral", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        gate,
        "latest_review_assessment",
        lambda _root, _task, stage, **_kwargs: SimpleNamespace(record=inputs.reviews[stage]),
    )
    actual_guard, guard_calls = gate._v2_gate_facts, []

    def guard(*args, **kwargs):
        assert kwargs["node_facts"] is facts
        guard_calls.append(kwargs)
        return actual_guard(*args, **kwargs)

    monkeypatch.setattr(gate, "_v2_gate_facts", guard)
    before = snapshot_tree(inputs.root)
    with pure_guard(monkeypatch):
        decision = gate.evaluate_gate(inputs.root, "TASK-0001")
    assert snapshot_tree(inputs.root) == before
    assert len(rechecks) == len(guard_calls) == 1
    # These logical material seams never produce a completed Gate PASS.
    assert decision.passed is False
    assert "GATE_CODE_APPROVAL_STALE" in decision.reason_codes
    assert "GATE_V2_MUTATION_NOT_KILLED" not in decision.reason_codes
    assert ("GATE_V2_EVIDENCE_NOT_FINAL" in decision.reason_codes) is (phase != "final")
    assert ("GATE_V2_REVIEW_STALE" in decision.reason_codes) is (phase != "final")


def test_actual_code_approval_entry_cannot_bypass_derived_installed_survival(
    consumer_inputs, monkeypatch
):
    from dataclasses import replace

    from initialization_helpers import snapshot_tree
    from test_installed_mutation_transactions import pure_guard

    import aiflow.approval as approval
    import aiflow.node_execution as execution
    from aiflow.review_service import ReviewAssessment

    inputs = consumer_inputs
    consumer_authority(monkeypatch, approval, inputs)
    # Deliberately inconsistent top-level claims isolate the installed guard:
    # a real original recheck must never certify this combination as passed.
    survived = replace(
        node_facts(killed=False),
        current=True,
        passed=True,
        evidence_sha256=_digest(inputs.evidence),
        materials_sha256=inputs.evidence["node_binding"]["materials_sha256"],
    )
    monkeypatch.setattr(execution, "recheck_node_evidence", lambda *_: survived)
    monkeypatch.setattr(approval, "_governance_only", lambda *_: True)
    monkeypatch.setattr(
        approval,
        "latest_review_assessment",
        lambda _root, _task, stage, **_kwargs: ReviewAssessment({}, inputs.reviews[stage]),
    )
    before = snapshot_tree(inputs.root)
    with pure_guard(monkeypatch), pytest.raises(AiflowError) as caught:
        approval.approve_task(
            inputs.root,
            "TASK-0001",
            approval_type="code",
            actor="project-owner",
            reason="Logical installed survival rejection",
        )
    assert caught.value.code == "CODE_EVIDENCE_STALE"
    assert snapshot_tree(inputs.root) == before
