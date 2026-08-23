"""Pure assembly and atomic persistence of verification evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, cast

from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError
from aiflow.process_runner import ProcessResult
from aiflow.storage import atomic_write_json
from aiflow.verification import VerificationCheck

_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
V2_PRE_IMPLEMENTATION_REVIEW = "pre_implementation_review"
V2_FINAL = "final"


@dataclass(frozen=True)
class EvidenceFacts:
    """Version, run, and authority facts supplied by the verification orchestrator."""

    task_id: str
    decision_unit_ids: tuple[str, ...]
    repository_id: str
    branch: str
    base_commit: str
    subject_commit: str
    spec_sha256: str
    policy_sha256: str
    classification_input_sha256: str
    verification_level: Literal["V0", "V1"]
    mode: Literal["local", "ci"]
    run_id: str
    run_dir: Path
    generated_at: str
    reproduce_command: tuple[str, ...]
    attestation_head: str | None = None
    attestation_governance_only: bool | None = None


def _log_ref(facts: EvidenceFacts, reference: str) -> str:
    candidate = PurePosixPath(reference.replace("\\", "/"))
    if (
        not reference
        or candidate.is_absolute()
        or ".." in candidate.parts
        or candidate.parts[:1] == ("logs",)
        or len(candidate.parts) != 1
    ):
        raise ContractError("Evidence log reference is invalid", code="EVIDENCE_LOG_REF_INVALID")
    run_dir = facts.run_dir.resolve()
    if _RUN_ID_PATTERN.fullmatch(facts.run_id) is None or run_dir.name != facts.run_id:
        raise ContractError("Evidence run identity is invalid", code="EVIDENCE_RUN_ID_INVALID")
    path = (run_dir / candidate.name).resolve()
    if path.parent != run_dir or not path.is_file():
        raise ContractError("Evidence log reference is invalid", code="EVIDENCE_LOG_REF_INVALID")
    return f"logs/{facts.run_id}/{candidate.as_posix()}"


def _version_complete(facts: EvidenceFacts) -> bool:
    values = (
        facts.task_id,
        facts.repository_id,
        facts.branch,
        facts.base_commit,
        facts.subject_commit,
        facts.spec_sha256,
        facts.policy_sha256,
        facts.classification_input_sha256,
        facts.run_id,
        facts.generated_at,
    )
    ci_complete = facts.mode != "ci" or (
        bool(facts.attestation_head) and facts.attestation_governance_only is True
    )
    return bool(facts.decision_unit_ids and facts.reproduce_command) and all(values) and ci_complete


def decide_evidence_conclusion(
    checks: Sequence[Mapping[str, object]], *, provisional: bool, version_complete: bool
) -> Literal["passed", "failed", "provisional"]:
    """Return the sole overall conclusion: required failures take precedence over provisional."""
    if (
        not version_complete
        or not checks
        or not any(check.get("required") is True for check in checks)
    ):
        return "failed"
    if any(check.get("required") is True and check.get("status") != "passed" for check in checks):
        return "failed"
    return "provisional" if provisional else "passed"


def verification_snapshot_sha256(evidence: Mapping[str, object]) -> str:
    """Hash the V2 verification facts that must survive review finalization."""
    if evidence.get("schema_version") != "2.0" or evidence.get("verification_level") != "V2":
        raise ContractError(
            "Verification snapshot requires V2 evidence", code="EVIDENCE_SNAPSHOT_INVALID"
        )
    projection = json.loads(json.dumps(dict(evidence)))
    projection.pop("phase", None)
    projection.pop("verification_snapshot_sha256", None)
    review_refs = projection.get("review_refs")
    if not isinstance(review_refs, dict):
        raise ContractError(
            "Verification snapshot review references are invalid", code="EVIDENCE_SNAPSHOT_INVALID"
        )
    review_refs.pop("implementation", None)
    canonical = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_v2_snapshot(evidence: Mapping[str, object]) -> None:
    """Reject a V2 artifact whose declared stable verification projection changed."""
    snapshot = evidence.get("verification_snapshot_sha256")
    if not isinstance(snapshot, str) or snapshot != verification_snapshot_sha256(evidence):
        raise ContractError("V2 verification snapshot is stale", code="EVIDENCE_SNAPSHOT_STALE")


def prepare_v2_pre_evidence(evidence: Mapping[str, object]) -> dict[str, object]:
    """Create schema-valid V2 evidence before an implementation review exists."""
    candidate = cast(dict[str, object], json.loads(json.dumps(dict(evidence))))
    if candidate.get("schema_version") != "2.0" or candidate.get("verification_level") != "V2":
        raise ContractError("V2 pre evidence is invalid", code="EVIDENCE_V2_PHASE_INVALID")
    review_refs = candidate.get("review_refs")
    if not isinstance(review_refs, dict):
        raise ContractError("V2 pre evidence lacks design review", code="EVIDENCE_V2_PHASE_INVALID")
    review_refs.pop("implementation", None)
    candidate["phase"] = V2_PRE_IMPLEMENTATION_REVIEW
    candidate["verification_snapshot_sha256"] = verification_snapshot_sha256(candidate)
    require_valid_contract("evidence", candidate)
    return candidate


def finalize_v2_evidence(
    evidence: Mapping[str, object], implementation_review: Mapping[str, object]
) -> dict[str, object]:
    """Append the implementation review without changing V2 verification facts."""
    candidate = cast(dict[str, object], json.loads(json.dumps(dict(evidence))))
    if candidate.get("phase") != V2_PRE_IMPLEMENTATION_REVIEW:
        raise ContractError(
            "V2 evidence is not awaiting implementation review", code="EVIDENCE_V2_PHASE_INVALID"
        )
    if candidate.get("conclusion") != "passed":
        raise ContractError("V2 pre evidence has not passed", code="EVIDENCE_V2_NOT_PASSED")
    validate_v2_snapshot(candidate)
    review_id = implementation_review.get("review_id")
    context_sha256 = implementation_review.get("context_sha256")
    if not isinstance(review_id, str) or not isinstance(context_sha256, str):
        raise ContractError(
            "Implementation review reference is invalid", code="EVIDENCE_REVIEW_REF_INVALID"
        )
    review_refs = candidate.get("review_refs")
    if not isinstance(review_refs, dict):
        raise ContractError("V2 review references are invalid", code="EVIDENCE_REVIEW_REF_INVALID")
    review_refs["implementation"] = {
        "review_id": review_id,
        "context_sha256": context_sha256,
    }
    candidate["phase"] = V2_FINAL
    validate_v2_snapshot(candidate)
    require_valid_contract("evidence", candidate)
    return candidate


def build_evidence(
    facts: EvidenceFacts,
    checks: Sequence[VerificationCheck],
    results: Sequence[ProcessResult],
    *,
    tool_versions: Mapping[str, str],
    unverified_scenarios: Sequence[str] = (),
    provisional: bool = False,
) -> dict[str, object]:
    """Combine supplied runner facts into complete evidence without running any command."""
    by_id = {result.check_id: result for result in results}
    if len(by_id) != len(results) or any(
        result.check_id not in {check.check_id for check in checks} for result in results
    ):
        raise ContractError("Evidence check results are invalid", code="EVIDENCE_RESULTS_INVALID")
    entries: list[dict[str, object]] = []
    unverified = {item.strip() for item in unverified_scenarios if item.strip()}
    for check in checks:
        result = by_id.get(check.check_id)
        reason_code: str | None
        if result is None:
            tool_missing = f"VERIFICATION_TOOL_MISSING:{check.check_id}" in unverified_scenarios
            status = "unverified"
            exit_code: int | None = None
            timed_out = False
            duration_ms = 0
            stdout_ref = stderr_ref = None
            summary = "required tool unavailable" if tool_missing else "result unavailable"
            reason_code = "VERIFICATION_TOOL_MISSING" if tool_missing else "VERIFICATION_NO_RESULT"
            unverified.add(f"check:{check.check_id}:result-unavailable")
        else:
            status = "passed"
            if (
                result.timed_out
                or result.returncode is None
                or result.returncode != 0
                or result.conclusion == "failed"
            ):
                status = "failed"
            exit_code = result.returncode
            timed_out = result.timed_out
            duration_ms = result.duration_ms
            if result.reason_code == "RUNNER_LOG_WRITE_FAILED":
                stdout_ref = stderr_ref = None
            else:
                stdout_ref = (
                    _log_ref(facts, result.stdout_log_ref) if result.stdout_log_ref else None
                )
                stderr_ref = (
                    _log_ref(facts, result.stderr_log_ref) if result.stderr_log_ref else None
                )
            summary = result.command_summary
            reason_code = result.reason_code
            if status == "failed" and reason_code is None:
                reason_code = (
                    "RUNNER_TIMEOUT"
                    if result.timed_out
                    else "RUNNER_NO_RESULT"
                    if result.returncode is None
                    else "RUNNER_NONZERO"
                    if result.returncode != 0
                    else "VERIFICATION_FAILED"
                )
        version = tool_versions.get(check.check_id, "")
        if not version or not check.required and status != "passed":
            status = "unverified"
            reason = "tool-version-unavailable" if not version else reason_code or "failed"
            unverified.add(f"check:{check.check_id}:{reason}")
        entries.append(
            {
                "check_id": check.check_id,
                "category": check.check_id,
                "status": status,
                "reason_code": reason_code,
                "required": check.required,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "duration_ms": duration_ms,
                "stdout_log_ref": stdout_ref,
                "stderr_log_ref": stderr_ref,
                "command_summary": summary,
                "tool_version": version or "unavailable",
            }
        )
    evidence: dict[str, object] = {
        "schema_version": "1.0",
        "task_id": facts.task_id,
        "decision_unit_ids": list(facts.decision_unit_ids),
        "repository_id": facts.repository_id,
        "branch": facts.branch,
        "base_commit": facts.base_commit,
        "subject_commit": facts.subject_commit,
        "spec_sha256": facts.spec_sha256,
        "policy_sha256": facts.policy_sha256,
        "classification_input_sha256": facts.classification_input_sha256,
        "verification_level": facts.verification_level,
        "mode": facts.mode,
        "checks": entries,
        "unverified_scenarios": sorted(unverified),
        "conclusion": decide_evidence_conclusion(
            entries, provisional=provisional, version_complete=_version_complete(facts)
        ),
        "generated_at": facts.generated_at,
        "reproduce_command": list(facts.reproduce_command),
    }
    if facts.mode == "ci":
        evidence["attestation_head"] = facts.attestation_head
        evidence["attestation_governance_only"] = facts.attestation_governance_only
    require_valid_contract("evidence", evidence)
    return evidence


def save_evidence(
    path: Path, evidence: Mapping[str, object], *, archive_path: Path | None = None
) -> None:
    """Persist an optional per-run copy, then atomically replace current evidence."""
    require_valid_contract("evidence", evidence)
    if archive_path is not None:
        atomic_write_json(archive_path, evidence)
    atomic_write_json(path, evidence)
