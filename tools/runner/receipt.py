"""Validate an independent runner envelope; never execute checks or issue a Gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

MAX_JSON_BYTES = 1024 * 1024
MAX_DEPTH = 24
# These dictionaries are consumed by Python's jsonschema/re implementation.
# Absolute end anchors reject a trailing LF; '$' would also match before it.
IDENTIFIER = {"type": "string", "pattern": r"\A[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z"}
SHA = {"type": "string", "pattern": r"\A[0-9a-f]{40}\Z"}
DIGEST = {"type": "string", "pattern": r"\A[0-9a-f]{64}\Z"}
TIME = {"type": "string", "format": "date-time", "maxLength": 40}
POSITIVE = {"type": "integer", "minimum": 1, "maximum": 9007199254740991}
PATH = {"type": "string", "minLength": 1, "maxLength": 240}


class ReceiptError(ValueError):
    """A bounded, non-sensitive error code suitable for public diagnostics."""


def record(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def sequence(items: dict[str, Any], *, minimum: int = 1) -> dict[str, Any]:
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": 128}


REPOSITORY = record(
    {
        "github_id": POSITIVE,
        "owner_name": {"type": "string", "pattern": r"\A[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z"},
        "visibility": {"const": "private"},
        "trust": {"const": "trusted"},
    }
)
RUNNER = record(
    {
        "id": POSITIVE,
        "profile_id": IDENTIFIER,
        "scope": {"const": "repository"},
        "os": {"enum": ["Windows", "Linux", "macOS"]},
        "architecture": {"enum": ["X64", "ARM64"]},
        "runner_version": {"type": "string", "pattern": r"\A[0-9]+\.[0-9]+\.[0-9]+\Z"},
        "privilege": {"const": "low"},
        "isolated_workspace": {"const": True},
        "active_instances": {"const": 1, "type": "integer"},
        "network_boundary_ref": IDENTIFIER,
        "environment_sha256": DIGEST,
    }
)
CODE = record(
    {
        "base_commit": SHA,
        "subject_commit": SHA,
        "checkout_commit": SHA,
        "tree_sha256": DIGEST,
        "dirty": {"const": False},
    }
)
DEFINITION = record(
    {
        "workflow_ref": PATH,
        "workflow_sha256": DIGEST,
        "check_set_sha256": DIGEST,
        "dependency_lock_sha256": DIGEST,
    }
)
ARTIFACT = record({"path": PATH, "sha256": DIGEST})
ASSOCIATION = record(
    {
        "repository_uuid": {"type": "string", "format": "uuid"},
        "task_id": {"type": "string", "pattern": r"\ATASK-[0-9]{4,}\Z"},
        "evidence_canonical_sha256": DIGEST,
        "spec_sha256": DIGEST,
        "policy_sha256": DIGEST,
        "classification_input_sha256": DIGEST,
    }
)
OPTIONAL_ASSOCIATION = {"anyOf": [{"type": "null"}, ASSOCIATION]}
EXPECTED_SCHEMA = record(
    {
        "schema_version": {"const": "1.0"},
        "kind": {"const": "runner_profile"},
        "repository": REPOSITORY,
        "runner": RUNNER,
        "code": CODE,
        "definition": DEFINITION,
        "storage": record(
            {
                "work_root_ref": IDENTIFIER,
                "cache_root_ref": IDENTIFIER,
                "temp_root_ref": IDENTIFIER,
                "retention_policy_ref": IDENTIFIER,
            }
        ),
        "credential_mechanism_ref": IDENTIFIER,
        "observation": record({"id": IDENTIFIER, "observed_at": TIME}),
        "run": record(
            {
                "receipt_id": IDENTIFIER,
                "source_kind": {"enum": ["github_api", "local_tool"]},
                "run_id": IDENTIFIER,
                "job_id": IDENTIFIER,
                "attempt": POSITIVE,
                "observation_sha256": DIGEST,
                "not_before": TIME,
                "not_after": TIME,
            }
        ),
        "required_checks": sequence(record({"id": IDENTIFIER, "command_ref": IDENTIFIER})),
        "required_artifacts": sequence(ARTIFACT),
        "association": OPTIONAL_ASSOCIATION,
    }
)
RECEIPT_SCHEMA = record(
    {
        "schema_version": {"const": "1.0"},
        "kind": {"const": "execution_receipt"},
        "receipt_id": IDENTIFIER,
        "repository": REPOSITORY,
        "runner": RUNNER,
        "code": CODE,
        "definition": DEFINITION,
        "source": record(
            {
                "kind": {"enum": ["github_api", "local_tool", "agent_claim"]},
                "run_id": IDENTIFIER,
                "job_id": IDENTIFIER,
                "attempt": POSITIVE,
                "observation_sha256": DIGEST,
                "observed_at": TIME,
            }
        ),
        "started_at": TIME,
        "finished_at": TIME,
        "result": {"enum": ["succeeded", "failed", "cancelled", "incomplete"]},
        "checks": sequence(
            record(
                {
                    "id": IDENTIFIER,
                    "command_ref": IDENTIFIER,
                    "status": {"enum": ["passed", "failed", "skipped", "cancelled", "unknown"]},
                    "exit_code": {"type": ["integer", "null"], "minimum": -2147483648},
                }
            )
        ),
        "artifacts": sequence(ARTIFACT),
        "association": OPTIONAL_ASSOCIATION,
    }
)


def _reject_constants(_value: str) -> None:
    raise ReceiptError("NONFINITE_JSON")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReceiptError("DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def _bounded(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ReceiptError("JSON_DEPTH_LIMIT")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ReceiptError("INVALID_JSON_KEY")
            _bounded(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _bounded(item, depth + 1)


def _no_secret_values(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _no_secret_values(item)
    elif isinstance(value, list):
        for item in value:
            _no_secret_values(item)
    elif isinstance(value, str) and re.search(
        r"(?:gh[pousr]_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+|"
        r"-----BEGIN [A-Z ]*PRIVATE KEY|(?i:password|token|secret)\s*[=:])",
        value,
    ):
        raise ReceiptError("SECRET_VALUE_REJECTED")


def canonical_sha256(value: Any) -> str:
    """Hash the parsed document, including all fields; this is not source authentication."""
    _bounded(value)
    try:
        data = json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError, RecursionError) as error:
        raise ReceiptError("INVALID_JSON") from error
    if len(data.encode("utf-8")) > MAX_JSON_BYTES:
        raise ReceiptError("JSON_SIZE_LIMIT")
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    """Read one bounded regular JSON file, refusing a link/reparse-point input."""
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ReceiptError("INPUT_NOT_REGULAR")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            observed = os.fstat(handle.fileno())
            if not stat.S_ISREG(observed.st_mode) or (observed.st_dev, observed.st_ino) != (
                metadata.st_dev,
                metadata.st_ino,
            ):
                raise ReceiptError("INPUT_CHANGED")
            data = handle.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            raise ReceiptError("JSON_SIZE_LIMIT")
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_reject_constants
        )
        canonical_sha256(value)
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ReceiptError("INPUT_UNREADABLE_OR_INVALID") from error


def _schema(value: Any, schema: dict[str, Any]) -> None:
    canonical_sha256(value)
    _no_secret_values(value)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    if not validator.is_valid(value):
        raise ReceiptError("SCHEMA_MISMATCH")


def _path(reference: str) -> None:
    # References are portable logical names, not paths this validator will open.
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", reference)
        or any(part in {".", ".."} or part.endswith(".") for part in reference.split("/"))
        or any(
            part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL"}
            for part in reference.split("/")
        )
        or any(
            re.fullmatch(r"(?:COM|LPT)[1-9](?:\..*)?", part, re.I) for part in reference.split("/")
        )
    ):
        raise ReceiptError("UNSAFE_REFERENCE")


def _indexed(items: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    indexed = {item[field]: item for item in items}
    if len(indexed) != len(items):
        raise ReceiptError("DUPLICATE_ENTRY")
    return indexed


def _when(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReceiptError("INVALID_TIME") from error
    if parsed.tzinfo is None:
        raise ReceiptError("INVALID_TIME")
    return parsed


def validate_receipt(
    expected: Any, receipt: Any, *, evidence: Any = None, disabled: bool = False
) -> dict[str, Any]:
    """Pure contract/association checks. The caller supplies an independently frozen baseline."""
    if disabled:
        return {
            "status": "ADAPTER_DISABLED",
            "contract_matched": False,
            "source_authenticated": False,
            "association_checked": False,
            "governance_effect": "none",
        }
    _schema(expected, EXPECTED_SCHEMA)
    _schema(receipt, RECEIPT_SCHEMA)
    for document in (expected, receipt):
        _path(document["definition"]["workflow_ref"])
    for field in ("repository", "runner", "code", "definition", "association"):
        if receipt[field] != expected[field]:
            raise ReceiptError("BOUND_FACT_MISMATCH")
    run = expected["run"]
    source = receipt["source"]
    if source["kind"] == "agent_claim" or source["kind"] != run["source_kind"]:
        raise ReceiptError("UNACCEPTED_SOURCE")
    for field in ("run_id", "job_id", "attempt", "observation_sha256"):
        if source[field] != run[field]:
            raise ReceiptError("RUN_IDENTITY_MISMATCH")
    if receipt["receipt_id"] != run["receipt_id"]:
        raise ReceiptError("RECEIPT_IDENTITY_MISMATCH")
    if not (
        _when(run["not_before"])
        <= _when(receipt["started_at"])
        <= _when(receipt["finished_at"])
        <= _when(source["observed_at"])
        <= _when(run["not_after"])
    ):
        raise ReceiptError("STALE_OR_INVALID_TIME_WINDOW")
    if receipt["result"] != "succeeded":
        raise ReceiptError("EXECUTION_NOT_SUCCEEDED")
    required = _indexed(expected["required_checks"], "id")
    observed = _indexed(receipt["checks"], "id")
    if required.keys() != observed.keys():
        raise ReceiptError("CHECK_SET_MISMATCH")
    for identifier, requirement in required.items():
        check = observed[identifier]
        if check["command_ref"] != requirement["command_ref"]:
            raise ReceiptError("COMMAND_REFERENCE_MISMATCH")
        if (
            check["status"] != "passed"
            or type(check["exit_code"]) is not int
            or check["exit_code"] != 0
        ):
            raise ReceiptError("REQUIRED_CHECK_NOT_PASSED")
    for items in (expected["required_artifacts"], receipt["artifacts"]):
        for artifact in items:
            _path(artifact["path"])
    if _indexed(expected["required_artifacts"], "path") != _indexed(receipt["artifacts"], "path"):
        raise ReceiptError("ARTIFACT_MANIFEST_MISMATCH")
    association = expected["association"]
    if association is None:
        if evidence is not None:
            raise ReceiptError("UNEXPECTED_EVIDENCE")
    else:
        _validate_association(expected, evidence)
    return {
        "status": "CONTRACT_MATCH",
        "contract_matched": True,
        "source_authenticated": False,
        "artifact_content_verified": False,
        "association_checked": association is not None,
        "governance_effect": "none",
        "expected_canonical_sha256": canonical_sha256(expected),
        "receipt_canonical_sha256": canonical_sha256(receipt),
    }


def _validate_association(expected: dict[str, Any], evidence: Any) -> None:
    from aiflow.contracts import validate_contract
    from aiflow.evidence import verification_snapshot_sha256

    association = expected["association"]
    if evidence is None:
        raise ReceiptError("ASSOCIATED_EVIDENCE_MISSING")
    canonical_sha256(evidence)
    if validate_contract("evidence", evidence):
        raise ReceiptError("LEGACY_EVIDENCE_INVALID")
    if evidence["schema_version"] == "2.0" and (
        evidence["verification_snapshot_sha256"] != verification_snapshot_sha256(evidence)
    ):
        raise ReceiptError("ASSOCIATED_SNAPSHOT_MISMATCH")
    if canonical_sha256(evidence) != association["evidence_canonical_sha256"]:
        raise ReceiptError("ASSOCIATED_EVIDENCE_DIGEST_MISMATCH")
    if evidence["repository_id"] != association["repository_uuid"]:
        raise ReceiptError("ASSOCIATED_REPOSITORY_MISMATCH")
    for field in ("task_id", "spec_sha256", "policy_sha256", "classification_input_sha256"):
        if evidence[field] != association[field]:
            raise ReceiptError("ASSOCIATED_FACT_MISMATCH")
    for field in ("base_commit", "subject_commit"):
        if evidence[field] != expected["code"][field]:
            raise ReceiptError("ASSOCIATED_CODE_MISMATCH")
    if evidence["conclusion"] != "passed" or evidence["unverified_scenarios"]:
        raise ReceiptError("ASSOCIATED_EVIDENCE_NOT_PASSED")
    if not (
        _when(expected["run"]["not_before"])
        <= _when(evidence["generated_at"])
        <= _when(expected["run"]["not_after"])
    ):
        raise ReceiptError("ASSOCIATED_EVIDENCE_STALE")
    if (
        evidence["mode"]
        != {"local_tool": "local", "github_api": "ci"}[expected["run"]["source_kind"]]
    ):
        raise ReceiptError("ASSOCIATED_SOURCE_MODE_MISMATCH")
    if evidence["mode"] == "ci" and (
        evidence["attestation_head"] != expected["code"]["checkout_commit"]
    ):
        raise ReceiptError("ASSOCIATED_CHECKOUT_MISMATCH")
    if evidence["mode"] == "local" and (
        evidence["subject_commit"] != expected["code"]["checkout_commit"]
    ):
        raise ReceiptError("ASSOCIATED_CHECKOUT_MISMATCH")
    required = _indexed(expected["required_checks"], "id")
    evidence_checks = _indexed(evidence["checks"], "check_id")
    if {key for key, item in evidence_checks.items() if item["required"]} != required.keys():
        raise ReceiptError("ASSOCIATED_CHECK_SET_MISMATCH")
    if any(
        item["required"]
        and (item["status"] != "passed" or item["exit_code"] != 0 or item["timed_out"])
        for item in evidence["checks"]
    ):
        raise ReceiptError("ASSOCIATED_CHECK_NOT_PASSED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("validate", help="compare a receipt with a frozen profile")
    command.add_argument("--expected", type=Path)
    command.add_argument("--receipt", type=Path)
    command.add_argument("--evidence", type=Path)
    command.add_argument(
        "--disabled", action="store_true", help="bypass this optional adapter only"
    )
    arguments = parser.parse_args(argv)
    try:
        if arguments.disabled:
            result = validate_receipt(None, None, disabled=True)
        else:
            if arguments.expected is None or arguments.receipt is None:
                raise ReceiptError("EXPECTED_AND_RECEIPT_REQUIRED")
            result = validate_receipt(
                load_json(arguments.expected),
                load_json(arguments.receipt),
                evidence=load_json(arguments.evidence) if arguments.evidence else None,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except ReceiptError as error:
        print(json.dumps({"status": "REJECTED", "reason": str(error), "governance_effect": "none"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
