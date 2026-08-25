"""Evidence assembly decision-table and persistence tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from aiflow.errors import ContractError, StorageError
from aiflow.evidence import (
    EvidenceFacts,
    build_evidence,
    decide_evidence_conclusion,
    finalize_v2_evidence,
    prepare_v2_pre_evidence,
    save_evidence,
    validate_v2_snapshot,
    verification_snapshot_sha256,
)
from aiflow.process_runner import ProcessResult
from aiflow.verification import VerificationCheck


def facts(**changes: object) -> EvidenceFacts:
    values: dict[str, object] = {
        "task_id": "TASK-0001",
        "decision_unit_ids": ("DU-001",),
        "repository_id": "123e4567-e89b-42d3-a456-426614174000",
        "branch": "main",
        "base_commit": "a" * 40,
        "subject_commit": "b" * 40,
        "spec_sha256": "c" * 64,
        "policy_sha256": "d" * 64,
        "classification_input_sha256": "e" * 64,
        "verification_level": "V1",
        "mode": "local",
        "run_id": Path.cwd().name,
        "run_dir": Path.cwd(),
        "generated_at": "2026-08-21T00:00:00Z",
        "reproduce_command": ("python", "-m", "aiflow", "verify", "TASK-0001"),
    }
    values.update(changes)
    return EvidenceFacts(**values)  # type: ignore[arg-type]


def check(*, required: bool = True) -> VerificationCheck:
    return VerificationCheck(
        "pytest", "V1", ("python", "-m", "pytest"), {}, Path.cwd(), 10, required, "pytest"
    )


def result(*, conclusion: str = "passed", timed_out: bool = False) -> ProcessResult:
    return ProcessResult(
        "EXEC-001",
        "pytest",
        "python -m pytest",
        "start",
        "finish",
        12,
        0,
        timed_out,
        "AGENTS.md",
        "AGENTS.md",
        conclusion,
        "RUNNER_TIMEOUT" if timed_out else None,
    )


def v2_evidence() -> dict[str, object]:
    path = Path(__file__).parents[1] / "fixtures" / "contracts" / "valid" / "evidence-v2.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


@pytest.mark.parametrize(
    ("checks", "provisional", "version_complete", "expected"),
    [
        ([{"required": True, "status": "passed"}], False, True, "passed"),
        ([{"required": True, "status": "failed"}], False, True, "failed"),
        ([{"required": False, "status": "failed"}], False, True, "failed"),
        ([{"required": True, "status": "unverified"}], False, True, "failed"),
        ([{"required": True, "status": "passed"}], True, True, "provisional"),
        ([], False, True, "failed"),
        ([{"required": True, "status": "passed"}], False, False, "failed"),
    ],
)
def test_conclusion_decision_table(
    checks: list[dict[str, object]], provisional: bool, version_complete: bool, expected: str
) -> None:
    assert (
        decide_evidence_conclusion(
            checks, provisional=provisional, version_complete=version_complete
        )
        == expected
    )


def test_builds_contract_valid_full_evidence_and_marks_optional_failure_unverified() -> None:
    optional = check(required=False)
    evidence = build_evidence(
        facts(), [optional], [result(conclusion="failed")], tool_versions={"pytest": "pytest 9"}
    )
    assert evidence["conclusion"] == "failed"
    assert evidence["checks"][0]["status"] == "unverified"  # type: ignore[index]
    assert evidence["unverified_scenarios"] == ["check:pytest:VERIFICATION_FAILED"]


def test_required_timeout_missing_version_and_log_escape_are_not_hidden() -> None:
    with_timeout = build_evidence(
        facts(),
        [check()],
        [result(conclusion="failed", timed_out=True)],
        tool_versions={"pytest": "pytest 9"},
    )
    assert with_timeout["conclusion"] == "failed"
    missing = build_evidence(facts(), [check()], [], tool_versions={})
    assert missing["checks"][0]["status"] == "unverified"  # type: ignore[index]
    assert missing["conclusion"] == "failed"
    escaped = result()
    object.__setattr__(escaped, "stdout_log_ref", "../outside.log")
    with pytest.raises(ContractError) as caught:
        build_evidence(facts(), [check()], [escaped], tool_versions={"pytest": "pytest 9"})
    assert caught.value.code == "EVIDENCE_LOG_REF_INVALID"


def test_ci_binds_governance_attestation_and_local_cannot_claim_it() -> None:
    ci = build_evidence(
        facts(mode="ci", attestation_head="f" * 40, attestation_governance_only=True),
        [check()],
        [result()],
        tool_versions={"pytest": "pytest 9"},
    )
    assert ci["attestation_governance_only"] is True
    with pytest.raises(ContractError):
        build_evidence(
            facts(mode="ci", attestation_head="f" * 40, attestation_governance_only=False),
            [check()],
            [result()],
            tool_versions={"pytest": "pytest 9"},
        )


def test_v2_snapshot_is_stable_across_implementation_review_finalization() -> None:
    pre = prepare_v2_pre_evidence(v2_evidence())
    assert pre["phase"] == "pre_implementation_review"
    validate_v2_snapshot(pre)

    final = finalize_v2_evidence(
        pre,
        {"review_id": "REV-0002", "context_sha256": "f" * 64},
    )
    assert final["phase"] == "final"
    assert final["verification_snapshot_sha256"] == pre["verification_snapshot_sha256"]
    validate_v2_snapshot(final)


def test_v2_snapshot_rejects_mutation_of_bound_verification_facts() -> None:
    pre = prepare_v2_pre_evidence(v2_evidence())
    checks = pre["checks"]
    assert isinstance(checks, list) and isinstance(checks[0], dict)
    checks[0]["status"] = "failed"
    with pytest.raises(ContractError) as caught:
        validate_v2_snapshot(pre)
    assert caught.value.code == "EVIDENCE_SNAPSHOT_STALE"

    artifact_tamper = prepare_v2_pre_evidence(v2_evidence())
    targeted = artifact_tamper["targeted_mutation"]
    assert isinstance(targeted, dict)
    targeted["mutation_evidence_sha256"] = "1" * 64
    with pytest.raises(ContractError) as caught:
        validate_v2_snapshot(artifact_tamper)
    assert caught.value.code == "EVIDENCE_SNAPSHOT_STALE"


def test_v2_helpers_reject_invalid_versions_missing_refs_and_invalid_finalization_inputs() -> None:
    legacy = v2_evidence()
    legacy["schema_version"] = "1.0"
    with pytest.raises(ContractError) as caught:
        verification_snapshot_sha256(legacy)
    assert caught.value.code == "EVIDENCE_SNAPSHOT_INVALID"

    missing_refs = v2_evidence()
    missing_refs["review_refs"] = []
    with pytest.raises(ContractError) as caught:
        verification_snapshot_sha256(missing_refs)
    assert caught.value.code == "EVIDENCE_SNAPSHOT_INVALID"

    with pytest.raises(ContractError) as caught:
        prepare_v2_pre_evidence(legacy)
    assert caught.value.code == "EVIDENCE_V2_PHASE_INVALID"

    pre = prepare_v2_pre_evidence(v2_evidence())
    wrong_phase = deepcopy(pre)
    wrong_phase["phase"] = "final"
    with pytest.raises(ContractError) as caught:
        finalize_v2_evidence(wrong_phase, {"review_id": "REV-0002", "context_sha256": "f" * 64})
    assert caught.value.code == "EVIDENCE_V2_PHASE_INVALID"

    failed = deepcopy(pre)
    failed["conclusion"] = "failed"
    with pytest.raises(ContractError) as caught:
        finalize_v2_evidence(failed, {"review_id": "REV-0002", "context_sha256": "f" * 64})
    assert caught.value.code == "EVIDENCE_V2_NOT_PASSED"

    with pytest.raises(ContractError) as caught:
        finalize_v2_evidence(pre, {"review_id": "REV-0002"})
    assert caught.value.code == "EVIDENCE_REVIEW_REF_INVALID"


def test_failure_evidence_is_atomically_saved_and_write_error_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = build_evidence(
        facts(), [check()], [result(conclusion="failed")], tool_versions={"pytest": "pytest 9"}
    )
    target = tmp_path / "evidence.json"
    save_evidence(target, evidence)
    assert '"conclusion": "failed"' in target.read_text(encoding="utf-8")
    from aiflow import evidence as module

    monkeypatch.setattr(
        module,
        "atomic_write_json",
        lambda *_args: (_ for _ in ()).throw(StorageError("no", code="STORAGE_WRITE_FAILED")),
    )
    with pytest.raises(StorageError):
        save_evidence(target, evidence)
