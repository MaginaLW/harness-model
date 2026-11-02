"""Pure assembly and atomic persistence of verification evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast
from uuid import UUID

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
    verification_level: Literal["V0", "V1", "V2"]
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
    if (
        evidence.get("schema_version") not in {"2.0", "3.2"}
        or evidence.get("verification_level") != "V2"
    ):
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
    if (
        candidate.get("schema_version") not in {"2.0", "3.2"}
        or candidate.get("verification_level") != "V2"
    ):
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
    if evidence.get("schema_version") in {"3.1", "3.2"}:
        validate_node_evidence(evidence)
    require_valid_contract("evidence", evidence)
    if archive_path is not None:
        atomic_write_json(archive_path, evidence)
    atomic_write_json(path, evidence)


_NODE_TOP_FIELDS = frozenset(
    {
        "schema_version",
        "task_id",
        "decision_unit_ids",
        "repository_id",
        "branch",
        "base_commit",
        "subject_commit",
        "spec_sha256",
        "policy_sha256",
        "classification_input_sha256",
        "verification_level",
        "mode",
        "checks",
        "unverified_scenarios",
        "conclusion",
        "generated_at",
        "reproduce_command",
        "node_binding",
        "node_binding_sha256",
    }
)
_NODE_BINDING_FIELDS = frozenset(
    {
        "profile",
        "subject_tree",
        "prepared",
        "run",
        "materials_sha256",
        "semantic_contract_sha256",
        "execution_contract_sha256",
        "environment_sha256",
        "coverage",
    }
)
_NODE_EXECUTION_FIELDS = frozenset(
    {
        "execution_id",
        "argv_template",
        "cwd_role",
        "timeout_seconds",
        "returncode",
        "timed_out",
        "duration_ms",
        "stdout",
        "stderr",
        "stdout_overflow",
        "stderr_overflow",
        "cleanup",
        "execution_error",
    }
)
_NODE_COVERAGE_METHOD = "vite-8.2.1-oxc-es2024-ast-v8-to-istanbul-zero-hit-v1"
_NODE_ISTANBUL_COVERAGE_METHOD = (
    "vitest-4.1.10-istanbul-vite-8.2.1-oxc-es2024-zero-hit-ts-ast-wire-v2"
)


def _node_invalid() -> ContractError:
    return ContractError("Node evidence contract is invalid", code="NODE_EVIDENCE_INVALID")


def _node_object(value: object, fields: frozenset[str] | set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise _node_invalid()
    return value


def _node_text(value: object, pattern: str = r"[^\x00-\x1f\x7f]+") -> str:
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise _node_invalid()
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise _node_invalid() from error
    return value


def _node_integer(value: object, *, minimum: int = 0, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or maximum is not None and value > maximum:
        raise _node_invalid()
    return value


def _node_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _node_evidence_plan(level: str, *, revision: int = 1) -> dict[str, object]:
    """The fixed public role contract; no Policy, materials, or executable is consulted."""
    if (
        type(revision) is not int
        or revision not in {1, 2}
        or level not in (("V0", "V1", "V2") if revision == 2 else ("V0", "V1"))
    ):
        raise _node_invalid()
    python = ["P", "-I", "-B", "-m", "aiflow"]
    npm = ["N", "M", "--userconfig", "U", "--globalconfig", "C", "--offline", "run"]
    git = [
        "G",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "diff",
        "--no-ext-diff",
        "--no-textconv",
    ]
    definitions: list[tuple[str, int, list[list[str]], str, int | None]] = [
        ("contract", 30, [python + ["validate", "T"]], "original", None),
        ("scope", 30, [python + ["scope", "T"]], "original", None),
        ("smoke", 30, [python + ["--help"]], "original", None),
        ("node_build", 300, [npm + ["build"]], "isolated", None),
        ("node_check", 600, [npm + ["check"]], "isolated", None),
        (
            "diff_whitespace",
            30,
            [
                git + ["--check", "--"],
                git + ["--cached", "--check", "--"],
                git + ["--check", "B", "S", "--"],
            ],
            "original",
            None,
        ),
    ]
    if level in {"V1", "V2"}:
        definitions.extend(
            [
                (
                    "ts_coverage",
                    600,
                    [
                        npm
                        + [
                            "test",
                            "--",
                            "--coverage.enabled",
                            "--coverage.provider=istanbul"
                            if revision == 2
                            else "--coverage.provider=v8",
                            "--coverage.include=src/local/**/*.ts",
                            "--coverage.reporter=json-summary",
                            "--coverage.reporter=json",
                            "--coverage.reporter=text",
                            "--coverage.reportsDirectory=R",
                            "--coverage.reportOnFailure",
                        ]
                        + (
                            [
                                "--config={node_source_config}",
                                "--dangerouslyIgnoreUnhandledErrors=false",
                                "--reporter=default",
                                "--reporter=json",
                                "--outputFile.json={node_product_report}",
                            ]
                            if revision == 2
                            else []
                        ),
                        [
                            "N",
                            "--input-type=module",
                            "--eval",
                            "{node_map_script}",
                            "{node_source_manifest}",
                            "{node_expected_map}",
                        ],
                    ],
                    "isolated",
                    None,
                ),
                ("ts_total_lines", 30, [], "isolated", 85),
                ("ts_diff_lines", 30, [], "isolated", 90),
            ]
        )
    if level == "V2":
        definitions.extend(
            (check_id, 30, [], "isolated", None)
            for check_id in (
                "acceptance",
                "integration",
                "targeted_mutation",
                "independent_verifier",
            )
        )
    checks: list[dict[str, object]] = []
    executions: list[dict[str, object]] = []
    for check_id, timeout, commands, cwd_role, threshold in definitions:
        checks.append(
            {
                "check_id": check_id,
                "required": True,
                "timeout_seconds": timeout,
                "threshold": threshold,
            }
        )
        for index, command in enumerate(commands):
            executions.append(
                {
                    "execution_id": f"EXEC-{len(executions) + 1:03d}",
                    "argv_template": command,
                    "cwd_role": cwd_role,
                    "timeout_seconds": 30 if check_id == "ts_coverage" and index == 1 else timeout,
                    "check_ids": (
                        ["ts_coverage", "acceptance", "integration"]
                        if level == "V2" and check_id == "ts_coverage" and index == 0
                        else [check_id]
                    ),
                }
            )
    return {"level": level, "checks": checks, "executions": executions}


def _node_coverage(value: object, *, revision: int = 1) -> dict[str, Any]:
    coverage = _node_object(value, {"scope_files", "total", "changed", "method"})
    _node_integer(coverage["scope_files"], minimum=1, maximum=20_000)
    if coverage["method"] != (
        _NODE_ISTANBUL_COVERAGE_METHOD if revision == 2 else _NODE_COVERAGE_METHOD
    ):
        raise _node_invalid()
    for key, threshold in (("total", 85), ("changed", 90)):
        fields = {"covered", "executable", "threshold"}
        counts = _node_object(
            coverage[key], fields | ({"applicability"} if key == "changed" else set())
        )
        denominator = _node_integer(counts["executable"], minimum=1 if key == "total" else 0)
        _node_integer(counts["covered"], maximum=denominator)
        if _node_integer(counts["threshold"]) != threshold:
            raise _node_invalid()
        if key == "changed" and counts["applicability"] != (
            "applicable" if denominator else "not_applicable"
        ):
            raise _node_invalid()
    if (
        coverage["changed"]["executable"] > coverage["total"]["executable"]
        or coverage["changed"]["covered"] > coverage["total"]["covered"]
    ):
        raise _node_invalid()
    return coverage


def _node_execution(
    value: object,
    fixed: Mapping[str, object],
    *,
    run_id: str,
) -> bool:
    execution = _node_object(value, _NODE_EXECUTION_FIELDS)
    for key in ("execution_id", "cwd_role"):
        if _node_text(execution[key]) != fixed[key]:
            raise _node_invalid()
    argv = execution["argv_template"]
    if (
        type(argv) is not list
        or any(type(arg) is not str for arg in argv)
        or argv != fixed["argv_template"]
    ):
        raise _node_invalid()
    if _node_integer(execution["timeout_seconds"], minimum=1) != fixed["timeout_seconds"]:
        raise _node_invalid()
    if execution["returncode"] is not None:
        _node_integer(execution["returncode"], maximum=0xFFFFFFFF)
    _node_integer(execution["duration_ms"])
    for key in ("timed_out", "stdout_overflow", "stderr_overflow", "execution_error"):
        if type(execution[key]) is not bool:
            raise _node_invalid()
    if execution["cleanup"] not in ("confirmed", "unknown", "not_started"):
        raise _node_invalid()
    if execution["cleanup"] == "confirmed" and execution["returncode"] is None:
        raise _node_invalid()
    for name in ("stdout", "stderr"):
        stream = _node_object(execution[name], {"bytes", "sha256", "raw_ref", "log_ref"})
        size = _node_integer(stream["bytes"], maximum=1024 * 1024)
        _node_text(stream["sha256"], r"[0-9a-f]{64}")
        prefix = f"logs/{run_id}/node/raw/{fixed['execution_id']}/{name}"
        if stream["raw_ref"] != prefix + ".raw" or stream["log_ref"] != prefix + ".log":
            raise _node_invalid()
        if size == 0 and stream["sha256"] != hashlib.sha256(b"").hexdigest():
            raise _node_invalid()
        if execution[f"{name}_overflow"] and size != 1024 * 1024:
            raise _node_invalid()
    return (
        execution["returncode"] == 0
        and execution["timed_out"] is False
        and execution["stdout_overflow"] is False
        and execution["stderr_overflow"] is False
        and execution["cleanup"] == "confirmed"
        and execution["execution_error"] is False
    )


def _node_installed_projection(value: object, *, task_id: str, run_id: str) -> dict[str, Any]:
    installed = _node_object(value, {"reference", "inputs_sha256", "results"})
    reference = _node_object(installed["reference"], {"ref", "size", "sha256"})
    if (
        re.fullmatch(r"IMUT-[0-9a-f]{16}", run_id) is None
        or reference["ref"] != f".ai/tasks/{task_id}/logs/{run_id}/run.json"
    ):
        raise _node_invalid()
    _node_integer(reference["size"], minimum=1, maximum=16 * 1024 * 1024)
    for value in (reference["sha256"], installed["inputs_sha256"]):
        _node_text(value, r"[0-9a-f]{64}")
    results = installed["results"]
    if type(results) is not list or len(results) != 5:
        raise _node_invalid()
    for index, row in enumerate(results, 1):
        if (
            type(row) is not list
            or len(row) != 2
            or row[0] != f"MUT-V2-{index:03d}"
            or row[1] not in ("killed", "survived", "unverified")
        ):
            raise _node_invalid()
    return installed


def _node_product_projection(value: object, *, run_id: str) -> dict[str, Any] | None:
    if value is None:
        return None
    from aiflow.node_verification import PRODUCT_TESTS

    product = _node_object(value, {"report", "inventory_sha256", "acceptance", "integration"})
    report = _node_object(product["report"], {"ref", "size", "sha256"})
    if report["ref"] != f"logs/{run_id}/node/vitest.json":
        raise _node_invalid()
    _node_integer(report["size"], minimum=1, maximum=16 * 1024 * 1024)
    for digest in (report["sha256"], product["inventory_sha256"]):
        _node_text(digest, r"[0-9a-f]{64}")
    for category in ("acceptance", "integration"):
        expected = [
            {"file": path, "full_name": ancestor + " " + title}
            for kind, path, ancestor, title in PRODUCT_TESTS
            if kind == category
        ]
        if _node_digest(product[category]) != _node_digest(expected):
            raise _node_invalid()
    return product


def validate_node_evidence(
    evidence: Mapping[str, object],
    *,
    require_passed: bool = False,
) -> None:
    """Check the closed Node public versions, without I/O or runtime replay.

    A structurally passed document still needs the single production material recheck;
    compact hashes and process claims cannot authenticate historical execution.
    """
    if not isinstance(evidence, Mapping):
        raise _node_invalid()
    revision = 2 if evidence.get("schema_version") == "3.2" else 1
    lifecycle = revision == 2 and evidence.get("verification_level") == "V2"
    lifecycle_fields = {
        "phase",
        "verifier_actor",
        "verifier_context_sha256",
        "verification_snapshot_sha256",
        "review_refs",
        "installed_mutation",
    }
    if set(evidence) != _NODE_TOP_FIELDS | (lifecycle_fields if lifecycle else set()):
        raise _node_invalid()
    if (
        type(require_passed) is not bool
        or evidence["schema_version"] not in ("3.1", "3.2")
        or evidence["mode"] != "local"
        or evidence["verification_level"]
        not in (("V0", "V1", "V2") if revision == 2 else ("V0", "V1"))
        or evidence["conclusion"] not in ("passed", "failed")
    ):
        raise _node_invalid()
    task_id = _node_text(evidence["task_id"], r"TASK-[0-9]{4,}")
    units = evidence["decision_unit_ids"]
    if type(units) is not list or not units:
        raise _node_invalid()
    for unit in units:
        _node_text(unit, r"DU-[0-9]{3,}")
    if len(units) != len(set(units)):
        raise _node_invalid()
    repository_id = _node_text(evidence["repository_id"])
    generated = _node_text(evidence["generated_at"])
    try:
        if str(UUID(repository_id)) != repository_id or "T" not in generated:
            raise _node_invalid()
        if datetime.fromisoformat(generated.replace("Z", "+00:00")).tzinfo is None:
            raise _node_invalid()
    except ValueError as error:
        raise _node_invalid() from error
    _node_text(evidence["branch"])
    for key in ("base_commit", "subject_commit"):
        _node_text(evidence[key], r"[0-9a-f]{40}")
    for key in (
        "spec_sha256",
        "policy_sha256",
        "classification_input_sha256",
        "node_binding_sha256",
    ):
        _node_text(evidence[key], r"[0-9a-f]{64}")
    binding = _node_object(
        evidence["node_binding"], _NODE_BINDING_FIELDS | ({"product_tests"} if lifecycle else set())
    )
    profile = _node_object(binding["profile"], {"id", "revision"})
    if profile["id"] != "agent-bridge-node" or _node_integer(profile["revision"]) != revision:
        raise _node_invalid()
    _node_text(binding["subject_tree"], r"[0-9a-f]{40}")
    for key in (
        "materials_sha256",
        "semantic_contract_sha256",
        "execution_contract_sha256",
        "environment_sha256",
    ):
        _node_text(binding[key], r"[0-9a-f]{64}")
    prepared = _node_object(binding["prepared"], {"ref", "size", "sha256"})
    run = _node_object(binding["run"], {"ref", "size", "sha256"})
    for item, maximum in ((prepared, 64 * 1024), (run, 16 * 1024 * 1024)):
        _node_integer(item["size"], minimum=1, maximum=maximum)
        _node_text(item["sha256"], r"[0-9a-f]{64}")
    if prepared["ref"] != f"logs/node-prepared/{prepared['sha256']}/prepared.json":
        raise _node_invalid()
    reference = _node_text(run["ref"], r"logs/[A-Za-z0-9][A-Za-z0-9_.-]*/node/run\.json")
    run_id = reference.split("/")[1]
    if (
        run_id.endswith(".")
        or len(run_id) > 255
        or run_id.split(".")[0].casefold()
        in (
            "con",
            "prn",
            "aux",
            "nul",
            *(f"{prefix}{index}" for prefix in ("com", "lpt") for index in range(1, 10)),
        )
    ):
        raise _node_invalid()
    reproduce = evidence["reproduce_command"]
    suffix = ["--node-materials", prepared["sha256"]]
    if lifecycle:
        suffix += ["--installed-mutations", run_id]
    if (
        type(reproduce) is not list
        or len(reproduce) != 7 + len(suffix)
        or reproduce[:6] != ["python", "-m", "aiflow", "verify", task_id, "--actor"]
        or reproduce[7:] != suffix
    ):
        raise _node_invalid()
    _node_text(reproduce[6], r"[A-Za-z0-9][A-Za-z0-9_.@-]*")
    installed = product = None
    if lifecycle:
        installed = _node_installed_projection(
            evidence["installed_mutation"], task_id=task_id, run_id=run_id
        )
        product = _node_product_projection(binding["product_tests"], run_id=run_id)
        if evidence["phase"] not in (V2_PRE_IMPLEMENTATION_REVIEW, V2_FINAL):
            raise _node_invalid()
        if _node_text(evidence["verifier_actor"]) != reproduce[6]:
            raise _node_invalid()
        _node_text(evidence["verifier_context_sha256"], r"[0-9a-f]{64}")
        refs = _node_object(
            evidence["review_refs"],
            {"design", "implementation"} if evidence["phase"] == V2_FINAL else {"design"},
        )
        for ref in refs.values():
            item = _node_object(ref, {"review_id", "context_sha256"})
            _node_text(item["review_id"], r"REV-[0-9]{4,}")
            _node_text(item["context_sha256"], r"[0-9a-f]{64}")
        validate_v2_snapshot(evidence)
    level = _node_text(evidence["verification_level"])
    coverage = None
    if binding["coverage"] is not None:
        if level not in ("V1", "V2"):
            raise _node_invalid()
        coverage = _node_coverage(binding["coverage"], revision=revision)
    plan = _node_evidence_plan(level, revision=revision)
    if binding["execution_contract_sha256"] != _node_digest(plan):
        raise _node_invalid()
    checks = evidence["checks"]
    fixed_checks = cast(list[dict[str, object]], plan["checks"])
    fixed_executions = cast(list[dict[str, object]], plan["executions"])
    if type(checks) is not list or len(checks) != len(fixed_checks):
        raise _node_invalid()
    incomplete = stopped = False
    all_processes = True
    seen_executions: dict[str, tuple[object, bool]] = {}
    for value, fixed_check in zip(checks, fixed_checks, strict=True):
        check = _node_object(value, {"check_id", "required", "status", "executions"})
        if (
            check["check_id"] != fixed_check["check_id"]
            or check["required"] is not True
            or check["status"] not in ("passed", "failed", "unverified")
        ):
            raise _node_invalid()
        fixed = [
            row
            for row in fixed_executions
            if check["check_id"] in cast(list[str], row["check_ids"])
        ]
        actual = check["executions"]
        if type(actual) is not list or len(actual) > len(fixed):
            raise _node_invalid()
        succeeded = True
        for execution, template in zip(actual, fixed, strict=False):
            identity = str(template["execution_id"])
            previous = seen_executions.get(identity)
            if lifecycle and previous is not None:
                if _node_digest(execution) != _node_digest(previous[0]):
                    raise _node_invalid()
                succeeded = previous[1]
            else:
                if incomplete or stopped:
                    raise _node_invalid()
                succeeded = _node_execution(execution, template, run_id=run_id)
                seen_executions[identity] = (execution, succeeded)
                stopped = not succeeded
        complete = len(actual) == len(fixed)
        if fixed:
            incomplete |= not complete
            all_processes &= complete and succeeded
            if not complete and check["status"] != "unverified":
                raise _node_invalid()
            if complete and not succeeded and check["status"] != "failed":
                raise _node_invalid()
            if check["status"] == "passed" and not (complete and succeeded):
                raise _node_invalid()
        elif actual:
            raise _node_invalid()
        elif check["status"] == "passed":
            if lifecycle and check["check_id"] in ("targeted_mutation", "independent_verifier"):
                if installed is None or any(row[1] != "killed" for row in installed["results"]):
                    raise _node_invalid()
            elif coverage is None or not all_processes:
                raise _node_invalid()
        if (
            lifecycle
            and check["status"] == "passed"
            and check["check_id"] in ("acceptance", "integration")
            and product is None
        ):
            raise _node_invalid()
        if check["status"] == "passed" and check["check_id"] in ("ts_total_lines", "ts_diff_lines"):
            assert coverage is not None
            counts = coverage["total" if check["check_id"] == "ts_total_lines" else "changed"]
            if counts["covered"] * 100 < counts["executable"] * counts["threshold"]:
                raise _node_invalid()
        if check["check_id"] == "ts_coverage" and check["status"] == "passed" and coverage is None:
            raise _node_invalid()
    expected_unverified = [check["check_id"] for check in checks if check["status"] == "unverified"]
    if evidence["unverified_scenarios"] != expected_unverified:
        raise _node_invalid()
    passed = all(check["status"] == "passed" for check in checks)
    if evidence["conclusion"] != ("passed" if passed else "failed"):
        raise _node_invalid()
    if coverage is not None and not all_processes:
        raise _node_invalid()
    if passed and (not all_processes or level in ("V1", "V2") and coverage is None):
        raise _node_invalid()
    if evidence["node_binding_sha256"] != _node_digest(binding):
        raise _node_invalid()
    if require_passed and not passed:
        raise ContractError("Node evidence has not passed", code="NODE_EVIDENCE_NOT_PASSED")
