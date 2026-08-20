"""Evidence assembly decision-table and persistence tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.errors import ContractError, StorageError
from aiflow.evidence import EvidenceFacts, build_evidence, decide_evidence_conclusion, save_evidence
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
