"""Offline TASK-0025 self-hosting replay and fail-closed scenarios."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from aiflow.approval import canonical_action_sha256
from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError
from aiflow.evidence import finalize_v2_evidence, prepare_v2_pre_evidence, validate_v2_snapshot
from aiflow.freshness import evaluate_freshness
from aiflow.gate import GateFacts, evaluate_gate_facts
from aiflow.mutation_evidence import (
    consume_targeted_mutation_evidence,
    load_targeted_mutation_evidence,
)
from aiflow.review_service import (
    latest_review_assessment,
    validate_review_context,
    validate_review_record,
)
from aiflow.scope import assess_scope
from aiflow.storage import read_task_json
from aiflow.task_service import read_task_record_strict
from aiflow.verification import V1_CHECK_IDS, V2_EXTRA_CHECK_IDS
from aiflow.verifier_service import (
    build_verifier_context,
    current_implementer_actor,
    load_verifier_context,
    validate_verifier_actor,
    validate_verifier_context_current,
)

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "TASK-0025"
BUNDLE_DIRECTORY = ROOT / ".ai/tasks/TASK-0025/historical-snapshots/h1-fe30565"
MANIFEST_PATH = BUNDLE_DIRECTORY / "manifest.json"


def canonical_sha256(value: dict[str, object], *, omit: str | None = None) -> str:
    candidate = {key: item for key, item in value.items() if key != omit}
    canonical = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_bundle_manifest() -> dict[str, object]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert canonical_sha256(value, omit="bundle_sha256") == value["bundle_sha256"]
    return value


def bundle_files_by_target(manifest: dict[str, object]) -> dict[str, Path]:
    entries = manifest["files"]
    assert isinstance(entries, list)
    bundled_by_target: dict[str, Path] = {}
    for entry in entries:
        assert isinstance(entry, dict)
        bundle_path = entry.get("bundle_path")
        target_path = entry.get("target_path")
        digest = entry.get("sha256")
        assert isinstance(bundle_path, str)
        assert isinstance(target_path, str)
        assert isinstance(digest, str)
        bundled = BUNDLE_DIRECTORY / bundle_path
        assert bundled.is_file()
        assert hashlib.sha256(bundled.read_bytes()).hexdigest() == digest
        assert target_path not in bundled_by_target
        bundled_by_target[target_path] = bundled
    assert len(bundled_by_target) == len(entries)
    return bundled_by_target


@pytest.fixture
def historical_replay(tmp_path: Path) -> dict[str, object]:
    manifest = load_bundle_manifest()
    bundled_by_target = bundle_files_by_target(manifest)
    source_commit = manifest["source_governance_commit"]
    assert isinstance(source_commit, str)

    replay = tmp_path / "replay"
    subprocess.run(
        [
            "git",
            "clone",
            "-c",
            "core.autocrlf=true",
            "--no-hardlinks",
            str(ROOT),
            str(replay),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=true",
            "-C",
            str(replay),
            "checkout",
            "-B",
            "main",
            source_commit,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert (
        subprocess.check_output(["git", "-C", str(replay), "rev-parse", "HEAD"], text=True).strip()
        == source_commit
    )
    assert (
        subprocess.check_output(
            ["git", "-C", str(replay), "symbolic-ref", "--short", "HEAD"], text=True
        ).strip()
        == "main"
    )
    non_task_inputs = manifest["non_task_inputs"]
    assert isinstance(non_task_inputs, list)
    for item in non_task_inputs:
        assert isinstance(item, dict)
        path = item.get("path")
        digest = item.get("sha256")
        assert isinstance(path, str) and isinstance(digest, str)
        eol = subprocess.check_output(
            ["git", "-C", str(replay), "ls-files", "--eol", "--", path], text=True
        ).strip()
        assert "w/crlf" in eol
        assert hashlib.sha256((replay / path).read_bytes()).hexdigest() == digest
    entries = manifest["files"]
    assert isinstance(entries, list)
    for entry in entries:
        assert isinstance(entry, dict)
        target_path = entry.get("target_path")
        digest = entry.get("sha256")
        assert isinstance(target_path, str) and isinstance(digest, str)
        target = replay / target_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundled_by_target[target_path], target)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    return {
        "manifest": manifest,
        "replay": replay,
        "bundled_by_target": bundled_by_target,
    }


@pytest.fixture
def actual_reviews() -> dict[str, dict[str, object]]:
    manifest = load_bundle_manifest()
    bundled_by_target = bundle_files_by_target(manifest)
    values: dict[str, dict[str, object]] = {}
    review_details = (
        ("design", manifest.get("design_review")),
        ("implementation", manifest.get("implementation_review")),
    )
    for label, details in review_details:
        assert isinstance(details, dict)
        context = json.loads(
            bundled_by_target[
                f".ai/tasks/{TASK_ID}/review-contexts/{details['context_sha256']}.json"
            ].read_text(encoding="utf-8")
        )
        record = json.loads(
            bundled_by_target[
                f".ai/tasks/{TASK_ID}/reviews/{details['review_id']}-r{details['revision']:04d}.json"
            ].read_text(encoding="utf-8")
        )
        values[f"{label}_context"] = context
        values[f"{label}_record"] = record
    return values


@pytest.fixture
def modeled_non_authoritative_gate_facts() -> GateFacts:
    return GateFacts(
        task_id=TASK_ID,
        current_state="APPROVED_FOR_MERGE",
        route="REVIEW",
        verification_level="V2",
        ask_required=False,
        review_required=True,
        repository_current=True,
        scope_current=True,
        classification_current=True,
        specification_current=True,
        ask_answered=True,
        spec_approval_current=True,
        evidence_current=True,
        evidence_passed=True,
        code_approval_current=True,
        unresolved_block_or_escalation=False,
        v2_final_evidence=True,
        v2_snapshot_current=True,
        v2_verifier_independent=True,
        v2_context_current=True,
        v2_reviews_current=True,
        v2_checks_current=True,
        v2_mutation_killed=True,
    )


@pytest.fixture
def modeled_non_authoritative_current_binding() -> dict[str, object]:
    task = read_task_record_strict(ROOT, TASK_ID).task
    classification = read_task_json(
        ROOT, TASK_ID, "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    design_record = json.loads(
        (ROOT / ".ai/tasks/TASK-0025/reviews/REV-0046-r0001.json").read_text(encoding="utf-8")
    )
    assert isinstance(design_record, dict)
    evidence = json.loads(
        (ROOT / "tests/fixtures/contracts/valid/evidence-v2.json").read_text(encoding="utf-8")
    )
    assert isinstance(evidence, dict)
    units = task.get("decision_units")
    assert isinstance(units, list)
    evidence.update(
        task_id=TASK_ID,
        decision_unit_ids=[
            item["decision_unit_id"]
            for item in units
            if isinstance(item, dict) and isinstance(item.get("decision_unit_id"), str)
        ],
        repository_id=task["repository_id"],
        branch=task["branch"],
        base_commit=task["base_commit"],
        subject_commit=task["subject_commit"],
        spec_sha256=task["frozen_spec_sha256"],
        policy_sha256=classification["policy_sha256"],
        classification_input_sha256=classification["classification_input_sha256"],
        reproduce_command=["python", "-m", "aiflow", "verify", TASK_ID],
        verifier_actor="modeled-independent-verifier",
    )
    evidence["checks"] = [
        {**evidence["checks"][0], "check_id": identifier, "category": identifier}
        for identifier in (*V1_CHECK_IDS, *V2_EXTRA_CHECK_IDS)
    ]
    evidence["review_refs"] = {
        "design": {
            "review_id": design_record["review_id"],
            "context_sha256": design_record["context_sha256"],
        }
    }
    mutation = evidence["targeted_mutation"]
    assert isinstance(mutation, dict)
    mutation["evidence_ref"] = str(mutation["evidence_ref"]).replace("TASK-0001", TASK_ID)
    pre = prepare_v2_pre_evidence(evidence)
    return {
        "task": task,
        "classification": classification,
        "design_record": design_record,
        "pre_evidence": pre,
    }


def test_historical_h1_replays_real_artifacts_without_current_readiness(
    historical_replay: dict[str, object], actual_reviews: dict[str, dict[str, object]]
) -> None:
    manifest = historical_replay["manifest"]
    replay = historical_replay["replay"]
    assert isinstance(manifest, dict) and isinstance(replay, Path)
    task_dir = replay / f".ai/tasks/{TASK_ID}"
    evidence = json.loads(
        (replay / manifest["pre_evidence_original_ref"]).read_text(encoding="utf-8")
    )
    artifact = load_targeted_mutation_evidence(replay, TASK_ID, manifest["artifact_original_ref"])
    facts = consume_targeted_mutation_evidence(replay, TASK_ID, evidence)
    action = json.loads(
        (task_dir / "action-v2-targeted-mutation-fe30565e.json").read_text(encoding="utf-8")
    )
    approvals = json.loads((task_dir / "approvals.json").read_text(encoding="utf-8"))
    receipt = task_dir / f"action-use-{canonical_action_sha256(action)}.md"
    context = load_verifier_context(replay, TASK_ID, evidence["verifier_context_sha256"])
    task_record = read_task_record_strict(replay, TASK_ID)
    require_valid_contract("evidence", evidence)
    validate_v2_snapshot(evidence)
    assert (
        action["subject_commit"] == manifest["source_subject_commit"] == evidence["subject_commit"]
    )
    assert any(item.get("action_sha256") == canonical_action_sha256(action) for item in approvals)
    assert receipt.is_file() and canonical_action_sha256(action) in receipt.read_text(
        encoding="utf-8"
    )
    validate_verifier_actor(
        current_implementer_actor(task_record.events), str(evidence["verifier_actor"])
    )
    assert context["context_sha256"] == evidence["verifier_context_sha256"]
    validate_verifier_context_current(context, build_verifier_context(replay, TASK_ID))
    assert tuple(item["check_id"] for item in evidence["checks"]) == (
        *V1_CHECK_IDS,
        *V2_EXTRA_CHECK_IDS,
    )
    assert all(item["required"] and item["status"] == "passed" for item in evidence["checks"])
    assert facts.passed and facts.mutation_evidence_sha256 == manifest["mutation_evidence_sha256"]
    assert [item["mutation_id"] for item in artifact["results"]] == [
        f"MUT-V2-{i:03d}" for i in range(1, 6)
    ]
    assert all(
        item["outcome"] == "killed"
        and (replay / item["log_ref"]).is_file()
        and hashlib.sha256((replay / item["log_ref"]).read_bytes()).hexdigest()
        == item["log_sha256"]
        for item in artifact["results"]
    )
    for label in ("design", "implementation"):
        validate_review_context(actual_reviews[f"{label}_context"])
        validate_review_record(
            actual_reviews[f"{label}_record"], actual_reviews[f"{label}_context"]
        )
    design = latest_review_assessment(replay, TASK_ID, "design")
    assert design.record["outcome"] == "APPROVE"
    assert actual_reviews["implementation_record"]["outcome"] == "REQUEST_CHANGES"
    with pytest.raises(ContractError) as error:
        latest_review_assessment(
            replay,
            TASK_ID,
            "implementation",
            verification_snapshot_sha256=evidence["verification_snapshot_sha256"],
        )
    assert error.value.code == "REVIEW_OUTCOME_NOT_APPROVABLE"


def test_modeled_non_authoritative_current_binding_contract(
    modeled_non_authoritative_gate_facts: GateFacts,
    modeled_non_authoritative_current_binding: dict[str, object],
) -> None:
    task = modeled_non_authoritative_current_binding["task"]
    classification = modeled_non_authoritative_current_binding["classification"]
    design_record = modeled_non_authoritative_current_binding["design_record"]
    pre = modeled_non_authoritative_current_binding["pre_evidence"]
    assert isinstance(task, dict)
    assert isinstance(classification, dict)
    assert isinstance(design_record, dict)
    assert isinstance(pre, dict)
    expected_binding = {
        "task_id": TASK_ID,
        "repository_id": task["repository_id"],
        "branch": task["branch"],
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "spec_sha256": task["frozen_spec_sha256"],
        "policy_sha256": classification["policy_sha256"],
        "classification_input_sha256": classification["classification_input_sha256"],
    }
    assert {key: pre[key] for key in expected_binding} == expected_binding
    assert pre["review_refs"] == {
        "design": {
            "review_id": design_record["review_id"],
            "context_sha256": design_record["context_sha256"],
        }
    }
    modeled_implementation_review = {
        "review_id": "REV-9999",
        "context_sha256": "f" * 64,
        "outcome": "APPROVE",
    }
    final = finalize_v2_evidence(pre, modeled_implementation_review)
    require_valid_contract("evidence", final)
    validate_v2_snapshot(final)
    assert final["phase"] == "final"
    assert {key: final[key] for key in expected_binding} == expected_binding
    assert final["review_refs"]["implementation"]["review_id"] == "REV-9999"
    assert evaluate_gate_facts(modeled_non_authoritative_gate_facts).passed


@pytest.mark.parametrize(
    "implementer, verifier, reason_code",
    [
        ("same", "same", "VERIFIER_ACTOR_NOT_INDEPENDENT"),
        ("same", "", "VERIFIER_ACTOR_REQUIRED"),
        ("", "verifier", "VERIFIER_IMPLEMENTER_MISSING"),
    ],
)
def test_same_or_empty_actor_fails_closed(
    implementer: str, verifier: str, reason_code: str
) -> None:
    with pytest.raises(ContractError) as error:
        validate_verifier_actor(implementer, verifier)
    assert error.value.code == reason_code


def write_mutation_variant(
    replay: Path,
    manifest: dict[str, object],
    evidence: dict[str, object],
    scenario: str,
) -> dict[str, object]:
    artifact_ref = manifest["artifact_original_ref"]
    assert isinstance(artifact_ref, str)
    artifact_path = replay / artifact_ref
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert isinstance(artifact, dict)
    results = artifact["results"]
    assert isinstance(results, list) and all(isinstance(item, dict) for item in results)
    if scenario == "missing":
        missing = results.pop()
        artifact["uncovered_mutation_ids"] = [missing["mutation_id"]]
    else:
        result = results[0]
        assert isinstance(result, dict)
        if scenario == "survived":
            result.update(mutant_exit_code=0, reason_code=None, outcome="survived")
        elif scenario == "unexecuted":
            result.update(
                mutant_exit_code=None,
                reason_code="MUTATION_NOT_EXECUTED",
                outcome="unverified",
            )
        elif scenario == "unknown":
            result["outcome"] = "unknown"
        else:  # pragma: no cover - parameter list is the closed scenario set
            raise AssertionError(scenario)
        log_ref = result["log_ref"]
        assert isinstance(log_ref, str)
        log_path = replay / log_ref
        log = json.loads(log_path.read_text(encoding="utf-8"))
        assert isinstance(log, dict)
        for key in ("mutant_exit_code", "reason_code", "outcome"):
            log[key] = result[key]
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["log_sha256"] = hashlib.sha256(log_path.read_bytes()).hexdigest()
        artifact["uncovered_mutation_ids"] = [result["mutation_id"]]
    artifact["mutation_evidence_sha256"] = canonical_sha256(
        artifact, omit="mutation_evidence_sha256"
    )
    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    candidate = deepcopy(evidence)
    targeted = candidate["targeted_mutation"]
    assert isinstance(targeted, dict)
    targeted["mutation_evidence_sha256"] = artifact["mutation_evidence_sha256"]
    targeted["results"] = [
        {
            "mutation_id": item["mutation_id"],
            "outcome": item["outcome"],
            "log_ref": item["log_ref"],
        }
        for item in results
    ]
    return candidate


@pytest.mark.parametrize(
    "scenario, expected_reason",
    [
        ("survived", "MUTATION_EVIDENCE_NOT_KILLED"),
        ("missing", "MUTATION_EVIDENCE_INVALID"),
        ("unexecuted", "MUTATION_EVIDENCE_NOT_KILLED"),
        ("unknown", "MUTATION_EVIDENCE_INVALID"),
    ],
)
def test_non_killed_or_invalid_mutant_fails_public_replay_and_gate(
    historical_replay: dict[str, object],
    modeled_non_authoritative_gate_facts: GateFacts,
    scenario: str,
    expected_reason: str,
) -> None:
    manifest = historical_replay["manifest"]
    replay = historical_replay["replay"]
    assert isinstance(manifest, dict) and isinstance(replay, Path)
    evidence_ref = manifest["pre_evidence_original_ref"]
    assert isinstance(evidence_ref, str)
    evidence = json.loads((replay / evidence_ref).read_text(encoding="utf-8"))
    assert isinstance(evidence, dict)
    candidate = write_mutation_variant(replay, manifest, evidence, scenario)
    mutation = consume_targeted_mutation_evidence(replay, TASK_ID, candidate)
    assert mutation.passed is False
    assert mutation.reason_code == expected_reason
    gate_facts = GateFacts(
        **{
            **modeled_non_authoritative_gate_facts.__dict__,
            "v2_mutation_killed": mutation.passed,
        }
    )
    assert "GATE_V2_MUTATION_NOT_KILLED" in evaluate_gate_facts(gate_facts).reason_codes


def test_scope_snapshot_evidence_and_attestation_fail_closed() -> None:
    assert not assess_scope(("src/aiflow/x.py",), ("tests/e2e/**",), task_id=TASK_ID).passed
    manifest = load_bundle_manifest()
    evidence_ref = manifest["pre_evidence_original_ref"]
    assert isinstance(evidence_ref, str)
    evidence = json.loads(
        bundle_files_by_target(manifest)[evidence_ref].read_text(encoding="utf-8")
    )
    assert isinstance(evidence, dict)
    tampered = deepcopy(evidence)
    tampered["subject_commit"] = "3" * 40
    with pytest.raises(ContractError) as snapshot_error:
        validate_v2_snapshot(tampered)
    assert snapshot_error.value.code == "EVIDENCE_SNAPSHOT_STALE"
    binding_fields = (
        "task_id",
        "repository_id",
        "branch",
        "base_commit",
        "subject_commit",
        "policy_sha256",
        "spec_sha256",
        "classification_input_sha256",
    )
    current = {field: evidence[field] for field in binding_fields}
    current.update(
        verification_level="V2",
        governance_only=True,
        attestation_governance_only=True,
    )
    stale = evaluate_freshness("evidence", evidence, {**current, "subject_commit": "4" * 40})
    assert stale.status == "stale"
    assert stale.reason_codes == ("FRESHNESS_SUBJECT_CHANGED",)
    ci = deepcopy(evidence)
    ci.update(mode="ci", attestation_head="4" * 40, attestation_governance_only=True)
    attestation = evaluate_freshness("evidence", ci, {**current, "attestation_head": "5" * 40})
    assert attestation.status == "stale"
    assert attestation.reason_codes == ("FRESHNESS_ATTESTATION_CHANGED",)
    missing_attestation = deepcopy(ci)
    missing_attestation.pop("attestation_head")
    with pytest.raises(ContractError):
        require_valid_contract("evidence", missing_attestation)


@pytest.mark.parametrize("label", ["design", "implementation"])
def test_review_context_tampering_fails_closed(
    actual_reviews: dict[str, dict[str, object]], label: str
) -> None:
    context = actual_reviews[f"{label}_context"]
    record = actual_reviews[f"{label}_record"]
    validate_review_context(context)
    validate_review_record(record, context)
    changed = deepcopy(context)
    content = changed["content"]
    assert isinstance(content, dict)
    content["goal"] = "tampered"
    with pytest.raises(ContractError) as error:
        validate_review_context(changed)
    assert error.value.code == "REVIEW_CONTEXT_HASH_INVALID"


@pytest.mark.parametrize(
    "stage, decision_unit_ids, snapshot",
    [
        ("design", ("DU-999",), None),
        ("implementation", None, "0" * 64),
    ],
)
def test_stale_design_or_implementation_review_binding_fails_closed(
    historical_replay: dict[str, object],
    stage: str,
    decision_unit_ids: tuple[str, ...] | None,
    snapshot: str | None,
) -> None:
    replay = historical_replay["replay"]
    assert isinstance(replay, Path)
    with pytest.raises(ContractError) as error:
        latest_review_assessment(
            replay,
            TASK_ID,
            stage,
            decision_unit_ids=decision_unit_ids,
            verification_snapshot_sha256=snapshot,
        )
    assert error.value.code == "REVIEW_RECORD_STALE"
