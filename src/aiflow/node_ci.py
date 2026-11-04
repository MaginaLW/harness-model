"""Closed Node CI authority, originals transport and original-host composition.

Committed source authority is deliberately an attestation.  Only the unchanged
local Gate can supply local-original currentness.  Platform observations are
obtained here through the pinned, read-only official client, never caller JSON.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import stat
import sys
import tarfile
import tomllib
import zipfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

from aiflow.errors import ContractError

MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_ROLE_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 20_000
CI_CAPS_REGISTERED = False
CI_CAPS: dict[str, tuple[int, int, int, int, int]] = {
    "V0": (0, 0, 0, 0, 0),
    "V1": (0, 0, 0, 0, 0),
    "V2": (0, 0, 0, 0, 0),
}
SOURCE_REPOSITORY_ID = 1319293089
SOURCE_REPOSITORY = "MaginaLW/harness-model"
SOURCE_WORKFLOW = ".github/workflows/node-engine-artifacts.yml"
TARGET_WORKFLOW = ".github/workflows/aiflow-node-ci.yml"
SOURCE_JOB = "node-engine-artifacts"
TARGET_JOB = "aiflow-node-ci"
DECLARATION = ".ai/node-ci-producer.json"
GH_VERSION = "2.103.3"
GH_EXE_SHA256 = "d303d8ac3f5e9438bf7c977b64dd6425513eae46218f8881d30694f28c1d0dfd"
APP_ID = 15368
PROFILE = {"id": "agent-bridge-node", "revision": 2}
COMMON_ROLES = (
    "source",
    "artifact",
    "engine",
    "runtime",
    "dependencies",
    "host",
    "preflight",
    "control",
    "node",
)
ENGINE_MEMBERS = (
    "direct/aiflow-0.2.0-py3-none-any.whl",
    "sdist/aiflow-0.2.0.tar.gz",
    "sdist-rebuilt/aiflow-0.2.0-py3-none-any.whl",
    "build-manifest.json",
)
CHECK_IDS = (
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
)
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_BINDING_FIELDS = {
    "repository_id",
    "task_id",
    "branch",
    "base_commit",
    "subject_commit",
    "subject_tree",
    "policy_sha256",
    "spec_sha256",
    "classification_input_sha256",
    "decision_unit_ids",
    "verification_level",
}
_PLATFORM_FIELDS = {
    "provider",
    "repository_id",
    "full_name",
    "workflow_id",
    "workflow_path",
    "workflow_ref",
    "workflow_sha256",
    "event",
    "head_sha",
    "run_id",
    "run_attempt",
    "job_id",
    "job_key",
    "check_run_id",
    "check_name",
    "app_id",
}
_ARTIFACT_FIELDS = {
    "origin",
    "source_repository_id",
    "source_full_name",
    "workflow_id",
    "workflow_path",
    "workflow_ref",
    "workflow_sha256",
    "source_head",
    "run_id",
    "run_attempt",
    "job_id",
    "artifact_id",
    "artifact_name",
    "artifact_digest",
    "wheel",
    "sdist",
    "build_manifest",
}
_IDENTITY_FIELDS = {
    "device",
    "inode",
    "size",
    "mtime_ns",
    "ctime_ns",
    "mode",
    "nlink",
    "attributes",
}


def _error(message: str, code: str = "NODE_CI_INVALID") -> ContractError:
    return ContractError(message, code=code)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise _error("CI document cannot be canonically encoded") from error


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _obj(value: Any, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise _error("CI object has missing or unknown fields")
    return value


def _text(value: Any, *, limit: int = 1024) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > limit
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise _error("CI text field is invalid")
    return value


def _integer(value: Any, *, minimum: int = 0, maximum: int = (1 << 63) - 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _error("CI integer field is invalid")
    return value


def _digest(value: Any, *, commit: bool = False) -> str:
    if not isinstance(value, str) or not (_COMMIT if commit else _SHA).fullmatch(value):
        raise _error("CI digest field is invalid")
    return value


def _level(value: Any) -> str:
    if not isinstance(value, str) or value not in CI_CAPS:
        raise _error("CI tier is unsupported")
    return value


def _path(value: Any) -> str:
    from aiflow.node_verification import _path as node_path

    text = _text(value, limit=4096)
    node_path(text)
    return text


def _timestamp(value: Any) -> str:
    text = _text(value, limit=64)
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})",
        text,
    ):
        raise _error("CI timestamp is not RFC3339")
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            raise ValueError("timezone missing")
    except ValueError as error:
        raise _error("CI timestamp is invalid") from error
    return text


def _list(value: Any, *, maximum: int = MAX_ENTRIES) -> list[Any]:
    if not isinstance(value, list) or len(value) > maximum:
        raise _error("CI array exceeds its closed bound")
    return value


def _ref(value: Any, *, member: bool = False) -> dict[str, Any]:
    result = _obj(value, {"member" if member else "ref", "size", "sha256"})
    _path(result["member" if member else "ref"])
    _integer(result["size"], maximum=MAX_FILE_BYTES)
    _digest(result["sha256"])
    return result


def _binding(value: Any) -> dict[str, Any]:
    result = _obj(value, _BINDING_FIELDS)
    try:
        if str(UUID(result["repository_id"])) != result["repository_id"]:
            raise ValueError("noncanonical UUID")
    except (ValueError, TypeError, AttributeError) as error:
        raise _error("CI repository UUID is invalid") from error
    if not re.fullmatch(r"TASK-[0-9]{4,}", _text(result["task_id"])):
        raise _error("CI task ID is invalid")
    _text(result["branch"])
    for key in ("base_commit", "subject_commit", "subject_tree"):
        _digest(result[key], commit=True)
    for key in ("policy_sha256", "spec_sha256", "classification_input_sha256"):
        _digest(result[key])
    units = _list(result["decision_unit_ids"])
    if not units or len(set(_text(unit) for unit in units)) != len(units):
        raise _error("CI decision-unit inventory is invalid")
    if any(not re.fullmatch(r"DU-[0-9]{3,}", unit) for unit in units):
        raise _error("CI decision-unit ID is invalid")
    _level(result["verification_level"])
    return result


def _platform(value: Any) -> dict[str, Any]:
    result = _obj(value, _PLATFORM_FIELDS)
    if result["provider"] != "github" or result["event"] != "pull_request":
        raise _error("CI platform/event is unsupported")
    for key in ("repository_id", "workflow_id", "run_id", "run_attempt", "job_id", "check_run_id"):
        _integer(result[key], minimum=1)
    if result["app_id"] != APP_ID or type(result["app_id"]) is not int:
        raise _error("CI Check app is unsupported")
    if not _REPOSITORY.fullmatch(_text(result["full_name"])):
        raise _error("CI provider repository is invalid")
    expected = {SOURCE_WORKFLOW: SOURCE_JOB, TARGET_WORKFLOW: TARGET_JOB}
    if result["workflow_path"] not in expected or (
        result["job_key"] != expected[result["workflow_path"]]
        or result["check_name"] != result["job_key"]
    ):
        raise _error("CI workflow/job identity is unsupported")
    _text(result["workflow_ref"])
    _digest(result["workflow_sha256"])
    _digest(result["head_sha"], commit=True)
    return result


def _artifact(value: Any) -> dict[str, Any]:
    result = _obj(value, _ARTIFACT_FIELDS)
    if (
        result["source_repository_id"] != SOURCE_REPOSITORY_ID
        or type(result["source_repository_id"]) is not int
        or result["source_full_name"] != SOURCE_REPOSITORY
        or result["workflow_path"] != SOURCE_WORKFLOW
        or result["origin"] not in {"direct", "sdist_rebuilt"}
    ):
        raise _error("CI engine artifact source is invalid")
    for key in ("workflow_id", "run_id", "run_attempt", "job_id", "artifact_id"):
        _integer(result[key], minimum=1)
    _text(result["workflow_ref"])
    _digest(result["workflow_sha256"])
    _provider_digest(result["artifact_digest"])
    _digest(result["source_head"], commit=True)
    if result["artifact_name"] != f"aiflow-node-engine-{result['run_id']}-{result['run_attempt']}":
        raise _error("CI engine artifact name is not attempt-specific")
    selected = ENGINE_MEMBERS[0 if result["origin"] == "direct" else 2]
    for key, name in (
        ("wheel", selected),
        ("sdist", ENGINE_MEMBERS[1]),
        ("build_manifest", ENGINE_MEMBERS[3]),
    ):
        if _ref(result[key], member=True)["member"] != name:
            raise _error("CI engine member selection is invalid")
    return result


def _declaration(value: Any) -> dict[str, Any]:
    result = _obj(
        value,
        {
            "kind",
            "schema_version",
            "repository",
            "profile",
            "policy_version",
            "workflow",
            "producer",
            "tier_contracts",
            "engine_source",
            "engine_artifact",
            "artifact_policy",
        },
    )
    repo = _obj(result["repository"], {"repository_id", "provider_repository_id", "full_name"})
    try:
        if str(UUID(repo["repository_id"])) != repo["repository_id"]:
            raise ValueError("noncanonical UUID")
    except (ValueError, TypeError, AttributeError) as error:
        raise _error("CI declaration UUID is invalid") from error
    _integer(repo["provider_repository_id"], minimum=1)
    if not _REPOSITORY.fullmatch(_text(repo["full_name"])):
        raise _error("CI declaration repository is invalid")
    if (
        result["profile"] != PROFILE
        or type(result["profile"].get("revision")) is not int
        or result["policy_version"] != "3.2.0"
    ):
        raise _error("CI declaration profile is invalid")
    workflow = _obj(result["workflow"], {"path", "ref", "sha256"})
    if workflow["path"] != TARGET_WORKFLOW or not _text(workflow["ref"]).startswith("refs/heads/"):
        raise _error("CI declaration workflow reference is invalid")
    _digest(workflow["sha256"])
    if (
        result["producer"]
        != {
            "job_key": TARGET_JOB,
            "check_name": TARGET_JOB,
            "app_id": APP_ID,
            "event": "pull_request",
        }
        or type(result["producer"].get("app_id")) is not int
    ):
        raise _error("CI declaration producer is invalid")
    for digest in _obj(result["tier_contracts"], {"V0", "V1", "V2"}).values():
        _digest(digest)
    source = _obj(
        result["engine_source"],
        {
            "repository_id",
            "full_name",
            "workflow_path",
            "workflow_ref",
            "workflow_sha256",
            "job_key",
            "artifact_name",
        },
    )
    artifact = _artifact(result["engine_artifact"])
    if any(
        source[key] != expected
        for key, expected in {
            "repository_id": SOURCE_REPOSITORY_ID,
            "full_name": SOURCE_REPOSITORY,
            "workflow_path": SOURCE_WORKFLOW,
            "workflow_ref": artifact["workflow_ref"],
            "workflow_sha256": artifact["workflow_sha256"],
            "job_key": SOURCE_JOB,
            "artifact_name": "aiflow-node-engine-<run_id>-<run_attempt>",
        }.items()
    ):
        raise _error("CI declaration source artifact constraints differ")
    policy = _obj(
        result["artifact_policy"], {"ci_artifact_name", "retention_days", "visibility_scope"}
    )
    if (
        policy["ci_artifact_name"] != "aiflow-node-ci-<run_id>-<run_attempt>"
        or policy["visibility_scope"] != "private_target_repository"
    ):
        raise _error("CI declaration artifact policy is invalid")
    _integer(policy["retention_days"], minimum=1, maximum=400)
    return result


def _review_ref(value: Any) -> None:
    result = _obj(value, {"record", "context", "review_id", "revision", "context_sha256"})
    _ref(result["record"])
    _ref(result["context"])
    if not re.fullmatch(r"REV-[0-9]{4,}", _text(result["review_id"])):
        raise _error("CI review ID is invalid")
    _integer(result["revision"], minimum=1)
    _digest(result["context_sha256"])


def _source_tuple(value: Any) -> dict[str, Any]:
    result = _obj(
        value,
        {
            "kind",
            "schema_version",
            "binding",
            "attestation_head",
            "static_declaration",
            "engine_artifact",
            "source_evidence",
            "task",
            "events",
            "classification",
            "spec",
            "policy_members",
            "approvals",
            "applicable_spec_approvals",
            "applicable_code_approvals",
            "v2",
        },
    )
    binding = _binding(result["binding"])
    _digest(result["attestation_head"], commit=True)
    for name in ("static_declaration", "task", "events", "classification", "spec", "approvals"):
        _ref(result[name])
    _artifact(result["engine_artifact"])
    evidence = _obj(result["source_evidence"], {"original", "canonical_sha256"})
    _ref(evidence["original"])
    _digest(evidence["canonical_sha256"])
    refs = _list(result["policy_members"], maximum=4)
    if len(refs) != 4:
        raise _error("CI source must bind four Policy originals")
    for item in refs:
        _ref(item)
    for kind in ("spec", "code"):
        items = _list(result[f"applicable_{kind}_approvals"])
        units = []
        for item in items:
            item = _obj(
                item,
                {"record_sha256", "decision_unit_id", "approval_type"}
                | ({"evidence_sha256"} if kind == "code" else set()),
            )
            _digest(item["record_sha256"])
            units.append(_text(item["decision_unit_id"]))
            if item["approval_type"] != kind:
                raise _error("CI approval projection has the wrong type")
            if kind == "code":
                _digest(item["evidence_sha256"])
        if len(units) != len(set(units)) or not set(units).issubset(binding["decision_unit_ids"]):
            raise _error("CI approval DU projection is invalid")
    if binding["verification_level"] == "V2":
        v2 = _obj(
            result["v2"],
            {"snapshot_sha256", "verifier_actor", "verifier_context", "design", "implementation"},
        )
        _digest(v2["snapshot_sha256"])
        _text(v2["verifier_actor"])
        _ref(v2["verifier_context"])
        _review_ref(v2["design"])
        _review_ref(v2["implementation"])
    elif result["v2"] is not None:
        raise _error("Lower CI tiers cannot acquire V2 authority")
    return result


def _inventory(value: Any, *, role: bool = False) -> dict[str, Any]:
    result = _obj(
        value, {"root", "identity", "entries", "total_bytes"} | ({"id"} if role else set())
    )
    _text(result["root"], limit=4096)
    root_identity = _obj(result["identity"], _IDENTITY_FIELDS)
    for item in root_identity.values():
        _integer(item)
    if not stat.S_ISDIR(root_identity["mode"]) or root_identity["attributes"] & 0x400:
        raise _error("CI inventory root identity is not an ordinary directory")
    paths: list[str] = []
    total = 0
    for row in _list(result["entries"]):
        if not isinstance(row, dict) or row.get("kind") not in {"file", "directory"}:
            raise _error("CI inventory entry kind is invalid")
        fields = {"path", "kind", "identity"} | (
            {"size", "sha256"} if row["kind"] == "file" else set()
        )
        _obj(row, fields)
        paths.append(_path(row["path"]))
        identity = _obj(row["identity"], _IDENTITY_FIELDS)
        for item in identity.values():
            _integer(item)
        if identity["attributes"] & 0x400 or stat.S_ISLNK(identity["mode"]):
            raise _error("CI inventory contains unsafe historical identity")
        if row["kind"] == "file":
            total += _integer(row["size"], maximum=MAX_FILE_BYTES)
            _digest(row["sha256"])
            if (
                not stat.S_ISREG(identity["mode"])
                or identity["nlink"] != 1
                or identity["size"] != row["size"]
            ):
                raise _error("CI inventory file identity is invalid")
        elif not stat.S_ISDIR(identity["mode"]):
            raise _error("CI inventory directory identity is invalid")
    if paths != sorted(set(paths), key=lambda path: path.encode("utf-8")) or len(
        {p.casefold() for p in paths}
    ) != len(paths):
        raise _error("CI inventory paths are unordered or aliased")
    if _integer(result["total_bytes"], maximum=MAX_ROLE_BYTES) != total:
        raise _error("CI inventory byte total differs")
    if role and result["id"] not in role_ids("V2"):
        raise _error("CI inventory role is unknown")
    return result


def role_ids(level: str) -> tuple[str, ...]:
    _level(level)
    return COMMON_ROLES + (
        tuple(f"pair-{i}-{side}" for i in range(5) for side in ("b", "m")) if level == "V2" else ()
    )


def _caps(level: str) -> tuple[int, int, int, int, int]:
    _level(level)
    if CI_CAPS_REGISTERED is not True or set(CI_CAPS) != {"V0", "V1", "V2"}:
        raise _error("Node CI transport caps are not registered", "NODE_CI_UNAVAILABLE")
    for row in CI_CAPS.values():
        if (
            type(row) is not tuple
            or len(row) != 5
            or any(type(v) is not int or v <= 0 for v in row)
            or row[3] > MAX_JSON_BYTES
        ):
            raise _error("Node CI transport cap table is invalid", "NODE_CI_UNAVAILABLE")
    return CI_CAPS[level]


def node_ci_execution_contract(level: str) -> dict[str, Any]:
    """Return the fixed cap-bearing contract; never enable an unregistered tier."""
    caps = _caps(level)
    from aiflow.evidence import _node_evidence_plan
    from aiflow.node_execution import SEMANTIC_CONTRACT_V2

    return {
        "kind": "aiflow-node-ci-execution-contract",
        "version": 1,
        "profile": dict(PROFILE),
        "policy_version": "3.2.0",
        "verification_level": level,
        "node": SEMANTIC_CONTRACT_V2,
        "plan": _node_evidence_plan(level, revision=2),
        "roles": list(role_ids(level)),
        "registered": True,
        "caps": {key: list(value) for key, value in CI_CAPS.items()},
        "tier_caps": list(caps),
        "pair_coordinates": [f"pair-{i}-{side}" for i in range(5) for side in ("b", "m")]
        if level == "V2"
        else [],
    }


def validate_node_ci_document(value: Any, *, kind: str | None = None) -> dict[str, Any]:
    """Validate closed CI models without recovery, execution or invented Current."""
    if not isinstance(value, dict) or len(_canonical(value)) > MAX_JSON_BYTES:
        raise _error("CI document is not a bounded object")
    selected = kind or value.get("kind")
    if selected == "platform":
        return _platform(value)
    if selected == "engine-artifact":
        return _artifact(value)
    if selected == "binding":
        return _binding(value)
    if selected == "role-manifest":
        return _inventory(value, role=True)
    if value.get("kind") != selected:
        raise _error("CI document kind differs from its role")
    version = "3.3" if selected == "aiflow-node-ci-evidence" else "1.0"
    if value.get("schema_version") != version:
        raise _error("CI document version is unsupported")
    if selected == "aiflow-node-ci-producer":
        return _declaration(value)
    if selected == "aiflow-node-ci-attested-source":
        return _source_tuple(value)
    if selected == "aiflow-node-engine-build":
        result = _obj(
            value,
            {
                "kind",
                "schema_version",
                "repository_id",
                "source_head",
                "workflow_path",
                "workflow_blob_sha256",
                "job_key",
                "run_id",
                "run_attempt",
                "python_version",
                "setuptools_version",
                "members",
                "package_payload_sha256",
                "resource_manifest_sha256",
            },
        )
        if (
            result["repository_id"] != SOURCE_REPOSITORY_ID
            or type(result["repository_id"]) is not int
            or result["workflow_path"] != SOURCE_WORKFLOW
            or result["job_key"] != SOURCE_JOB
        ):
            raise _error("Engine build producer is invalid")
        for key in ("run_id", "run_attempt"):
            _integer(result[key], minimum=1)
        version_parts = _list(result["python_version"], maximum=3)
        if len(version_parts) != 3 or version_parts[:2] != [3, 11]:
            raise _error("Engine build Python is unsupported")
        for part in version_parts:
            _integer(part, maximum=999)
        _text(result["setuptools_version"], limit=128)
        _digest(result["source_head"], commit=True)
        for key in ("workflow_blob_sha256", "package_payload_sha256", "resource_manifest_sha256"):
            _digest(result[key])
        rows = _list(result["members"], maximum=3)
        if len(rows) != 3:
            raise _error("Engine build payload set is incomplete")
        for row, name, origin in zip(
            rows, ENGINE_MEMBERS[:3], ("direct", "source", "sdist_rebuilt"), strict=True
        ):
            row = _obj(row, {"path", "origin", "size", "sha256"})
            if row["path"] != name or row["origin"] != origin:
                raise _error("Engine build member selection differs")
            _integer(row["size"], maximum=MAX_FILE_BYTES)
            _digest(row["sha256"])
        return result
    if selected == "aiflow-node-ci-descriptor":
        result = _obj(
            value,
            {
                "kind",
                "schema_version",
                "source_tuple_sha256",
                "static_declaration_sha256",
                "engine_artifact_sha256",
                "execution_contract_sha256",
                "verification_level",
                "attestation_head",
            },
        )
        for key in (
            "source_tuple_sha256",
            "static_declaration_sha256",
            "engine_artifact_sha256",
            "execution_contract_sha256",
        ):
            _digest(result[key])
        _digest(result["attestation_head"], commit=True)
        _level(result["verification_level"])
        return result
    if selected == "aiflow-node-ci-admission":
        result = _obj(
            value,
            {
                "kind",
                "schema_version",
                "descriptor_sha256",
                "platform",
                "input_materials_sha256",
                "engine_content_sha256",
                "claimed_at",
            },
        )
        for key in ("descriptor_sha256", "input_materials_sha256", "engine_content_sha256"):
            _digest(result[key])
        _platform(result["platform"])
        _timestamp(result["claimed_at"])
        return result
    if selected == "aiflow-node-ci-prepared-3.3":
        result = _obj(
            value,
            {
                "kind",
                "schema_version",
                "descriptor",
                "source_tuple",
                "admission",
                "platform",
                "profile",
                "verification_level",
                "execution_contract_sha256",
                "manifests",
            },
        )
        for key in ("descriptor", "source_tuple", "admission"):
            _ref(result[key])
        _platform(result["platform"])
        if result["profile"] != PROFILE or type(result["profile"].get("revision")) is not int:
            raise _error("CI prepared profile is invalid")
        _level(result["verification_level"])
        _digest(result["execution_contract_sha256"])
        for item in _obj(
            result["manifests"],
            {"source", "node", "npm", "dependencies", "engine", "host_tools", "preflight"},
        ).values():
            _ref(item)
        return result
    if selected == "aiflow-node-ci-run-3.3":
        result = _obj(
            value,
            {
                "kind",
                "schema_version",
                "prepared",
                "descriptor_sha256",
                "platform",
                "inputs",
                "environment",
                "roots",
                "executions",
                "coverage",
                "product_tests",
                "installed_mutation",
                "outputs",
                "failure",
            },
        )
        _ref(result["prepared"])
        _digest(result["descriptor_sha256"])
        _platform(result["platform"])
        _obj(
            result["inputs"],
            {"source", "runtime", "dependencies", "prepared_dependencies", "engine", "host_tools"},
        )
        _obj(result["roots"], {"original", "clone", "checkout", "checkout_receipt"})
        _obj(result["outputs"], {"build_dist", "dist", "fixtures", "node_inventory"})
        _list(result["executions"], maximum=10)
        if not isinstance(result["environment"], dict) or any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in result["environment"].items()
        ):
            raise _error("CI process environment is invalid")
        if result["failure"] is not None and not re.fullmatch(
            r"[A-Z][A-Z0-9_]{0,95}", _text(result["failure"])
        ):
            raise _error("CI failure code is invalid")
        return result
    if selected == "aiflow-node-ci-evidence":
        result = _obj(
            value,
            {
                "schema_version",
                "kind",
                "mode",
                "binding",
                "generated_at",
                "conclusion",
                "source_binding_kind",
                "source_tuple",
                "descriptor",
                "platform",
                "prepared",
                "run",
                "checks",
                "node_binding",
                "installed_mutation",
                "reproduce_command",
                "known_limitations",
            },
        )
        binding = _binding(result["binding"])
        if (
            result["mode"] != "ci"
            or result["source_binding_kind"] != "attested_committed_tuple"
            or result["conclusion"] not in {"passed", "failed"}
        ):
            raise _error("CI evidence mode/conclusion is invalid")
        _timestamp(result["generated_at"])
        for key in ("source_tuple", "descriptor", "prepared", "run"):
            _ref(result[key])
        _platform(result["platform"])
        checks = _list(result["checks"], maximum=13)
        expected = CHECK_IDS[: {"V0": 6, "V1": 9, "V2": 13}[binding["verification_level"]]]
        if [item.get("check_id") if isinstance(item, dict) else None for item in checks] != list(
            expected
        ):
            raise _error("CI evidence check inventory differs")
        for check in checks:
            if (
                check.get("status") not in {"passed", "failed", "unverified"}
                or check.get("required") is not True
            ):
                raise _error("CI evidence check status is invalid")
        if result["conclusion"] == "passed" and any(row["status"] != "passed" for row in checks):
            raise _error("CI evidence falsely reports passing checks")
        if binding["verification_level"] != "V2" and result["installed_mutation"] is not None:
            raise _error("Lower CI tier carries a V2 mutation projection")
        for key in ("reproduce_command", "known_limitations"):
            for item in _list(result[key]):
                _text(item, limit=4096)
        if not any(
            "original" in text.lower() and "host" in text.lower()
            for text in result["known_limitations"]
        ):
            raise _error("CI evidence omits its original-host limitation")
        return result
    if selected == "aiflow-node-ci-originals":
        result = _obj(
            value, {"kind", "schema_version", "evidence", "descriptor", "source_tuple", "roles"}
        )
        for key in ("evidence", "descriptor", "source_tuple"):
            _ref(result[key])
        ids = []
        for row in _list(result["roles"], maximum=19):
            row = _obj(row, {"id", "manifest"})
            ids.append(_text(row["id"]))
            _ref(row["manifest"])
        if tuple(ids) not in (role_ids("V0"), role_ids("V2")):
            raise _error("CI package role inventory differs")
        return result
    raise _error("Unknown CI document kind")


def _provider_digest(value: Any) -> str:
    text = _text(value, limit=71)
    if not text.startswith("sha256:"):
        raise _error("GitHub artifact has no supported authenticated digest")
    return _digest(text[7:])


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _error("Duplicate CI JSON key")
        result[key] = value
    return result


def _json(data: bytes) -> Any:
    if len(data) > MAX_JSON_BYTES:
        raise _error("CI JSON exceeds its byte limit", "NODE_CI_LIMIT_EXCEEDED")
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("nonfinite JSON")),
        )
    except (ValueError, UnicodeError, RecursionError) as error:
        raise _error("CI JSON is invalid") from error


def _ordinary(path: Path, *, directory: bool | None = None) -> os.stat_result:
    for ancestor in reversed((path, *path.parents)):
        info = ancestor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise _error("CI path contains a link or reparse point")
        if ancestor != path and not stat.S_ISDIR(info.st_mode):
            raise _error("CI path ancestor is not an ordinary directory")
    if directory is True and not stat.S_ISDIR(info.st_mode):
        raise _error("CI role root is not a directory")
    if directory is False and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
        raise _error("CI file is not independently owned")
    return info


def _read(path: Path, *, limit: int = MAX_FILE_BYTES) -> bytes:
    path = path.absolute()
    before = _ordinary(path, directory=False)
    if before.st_size > limit:
        raise _error("CI original exceeds its byte limit", "NODE_CI_LIMIT_EXCEEDED")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise _error("CI file changed while opening")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    if len(data) > limit or any(
        getattr(item, key) != getattr(before, key)
        for item in (after, current)
        for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
    ):
        raise _error("CI original changed during reading")
    return data


def _write_new(path: Path, data: bytes) -> None:
    if len(data) > MAX_FILE_BYTES:
        raise _error("CI output exceeds its byte limit", "NODE_CI_LIMIT_EXCEEDED")
    path.parent.mkdir(parents=True, exist_ok=True)
    _ordinary(path.parent, directory=True)
    with path.open("xb") as stream:
        stream.write(data)


def _file_ref(path: Path, root: Path) -> dict[str, Any]:
    data = _read(path)
    return {
        "ref": _path(path.relative_to(root).as_posix()),
        "size": len(data),
        "sha256": _sha(data),
    }


def _resolve_ref(root: Path, reference: Mapping[str, Any]) -> Path:
    _ref(dict(reference))
    name = reference["ref"]
    parts = PurePosixPath(name).parts
    # Logical producing role refs are retained verbatim inside originals/.
    if parts[0] in role_ids("V2"):
        path: Path = root / "originals" / name
    elif parts[0] in {"originals", "manifests"}:
        path = root / name
    else:
        raise _error("CI reference is outside the fixed package roles")
    _ordinary(path, directory=False)
    data = _read(path)
    if len(data) != reference["size"] or _sha(data) != reference["sha256"]:
        raise _error("CI reference differs from its original bytes")
    return path


def _ref_document(
    root: Path, reference: Mapping[str, Any], kind: str | None = None
) -> dict[str, Any]:
    value = _json(_read(_resolve_ref(root, reference), limit=MAX_JSON_BYTES))
    return validate_node_ci_document(value, kind=kind)


def _zip_files(archive: zipfile.ZipFile, *, entries: int, total: int) -> dict[str, zipfile.ZipInfo]:
    result: dict[str, zipfile.ZipInfo] = {}
    seen: set[str] = set()
    size = 0
    if len(archive.infolist()) > entries:
        raise _error("CI archive has too many entries", "NODE_CI_LIMIT_EXCEEDED")
    for info in archive.infolist():
        if info.orig_filename != info.filename or any(
            char in info.orig_filename for char in ("\\", "\0")
        ):
            raise _error("CI archive raw filename is unsafe")
        name = _path(info.filename.rstrip("/"))
        if name.casefold() in seen:
            raise _error("CI archive has duplicate or aliased entries")
        seen.add(name.casefold())
        mode = stat.S_IFMT(info.external_attr >> 16)
        if (
            mode not in {0, stat.S_IFREG, stat.S_IFDIR}
            or info.flag_bits & 1
            or info.external_attr & 0x400
        ):
            raise _error("CI archive contains a linked, encrypted or special entry")
        if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
            raise _error("CI archive codec is unsupported")
        if info.is_dir():
            if mode == stat.S_IFREG or info.file_size:
                raise _error("CI archive directory has file content")
            continue
        if mode == stat.S_IFDIR or info.file_size > MAX_FILE_BYTES:
            raise _error("CI archive file exceeds its closed role", "NODE_CI_LIMIT_EXCEEDED")
        size += info.file_size
        if size > total:
            raise _error("CI archive expanded bytes exceed the limit", "NODE_CI_LIMIT_EXCEEDED")
        result[name] = info
    # A file cannot also be an implicit parent directory.
    file_names = {name.casefold() for name in result}
    if any(
        parent.as_posix().casefold() in file_names
        for name in result
        for parent in PurePosixPath(name).parents
        if parent.as_posix() != "."
    ):
        raise _error("CI archive file/directory roles collide")
    return result


def _zip_read(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo, *, limit: int = MAX_FILE_BYTES
) -> bytes:
    if info.file_size > limit:
        raise _error("CI archive member is oversized", "NODE_CI_LIMIT_EXCEEDED")
    with archive.open(info) as stream:
        data = stream.read(info.file_size + 1)
    if len(data) != info.file_size:
        raise _error("CI archive member length differs")
    return data


def _inspect_wheel(data: bytes) -> dict[str, str]:
    from aiflow.resource_bundle import read_bundle

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = _zip_files(archive, entries=MAX_ENTRIES, total=MAX_ROLE_BYTES)
            if not files or any(
                not (name.startswith("aiflow/") or name.startswith("aiflow-0.2.0.dist-info/"))
                for name in files
            ):
                raise _error("Engine wheel exceeds its package allowlist")
            record = "aiflow-0.2.0.dist-info/RECORD"
            if record not in files or "aiflow/__init__.py" not in files:
                raise _error("Engine wheel is incomplete")
            payload = {name: _zip_read(archive, info) for name, info in files.items()}
            rows = list(csv.reader(io.StringIO(payload[record].decode("utf-8"), newline="")))
            if len(rows) != len(files) or {row[0] for row in rows if len(row) == 3} != set(files):
                raise _error("Engine wheel RECORD inventory differs")
            for name, digest, size in rows:
                if name == record:
                    if digest or size:
                        raise _error("Wheel RECORD cannot hash itself")
                    continue
                expected = "sha256=" + base64.urlsafe_b64encode(
                    hashlib.sha256(payload[name]).digest()
                ).decode().rstrip("=")
                if digest != expected or size != str(len(payload[name])):
                    raise _error("Engine wheel RECORD does not bind its bytes")
            manifest, _contents = read_bundle(zipfile.Path(archive, "aiflow/_bundled_resources/"))
            del manifest
            return {
                "package_payload_sha256": _sha(
                    _canonical(
                        [
                            {
                                "path": name,
                                "size": len(payload[name]),
                                "sha256": _sha(payload[name]),
                            }
                            for name in sorted(payload, key=lambda name: name.encode("utf-8"))
                        ]
                    )
                ),
                "resource_manifest_sha256": _sha(
                    payload["aiflow/_bundled_resources/manifest.json"]
                ),
            }
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, KeyError) as error:
        raise _error("Engine wheel originals are invalid") from error


def inspect_engine_wheel(path: Path) -> dict[str, str]:
    """Read a complete ordinary wheel/RECORD/bundle without extracting or importing."""
    return _inspect_wheel(_read(path))


def validate_engine_artifact_archive(
    path: Path, selection: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Validate all four actual authenticated source-artifact members, not a label."""
    archive_data = _read(path, limit=4 * MAX_FILE_BYTES)
    if selection is not None:
        chosen = _artifact(dict(selection))
        if _sha(archive_data) != _provider_digest(chosen["artifact_digest"]):
            raise _error("Source artifact differs from its authenticated digest")
    try:
        with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
            files = _zip_files(archive, entries=8, total=3 * MAX_FILE_BYTES + MAX_JSON_BYTES)
            if set(files) != set(ENGINE_MEMBERS):
                raise _error("Source artifact is not the exact four-member package")
            raw_manifest = _zip_read(archive, files[ENGINE_MEMBERS[3]], limit=MAX_JSON_BYTES)
            manifest = validate_node_ci_document(
                _json(raw_manifest), kind="aiflow-node-engine-build"
            )
            members = {name: _zip_read(archive, files[name]) for name in ENGINE_MEMBERS[:3]}
            for entry in manifest["members"]:
                data = members[entry["path"]]
                if entry["size"] != len(data) or entry["sha256"] != _sha(data):
                    raise _error("Source build manifest differs from raw payloads")
            wheels = [
                _inspect_wheel(members[name]) for name in (ENGINE_MEMBERS[0], ENGINE_MEMBERS[2])
            ]
            if wheels[0] != wheels[1] or any(
                manifest[key] != value for key, value in wheels[0].items()
            ):
                raise _error("Source wheel payload/resource relationship differs")
            with tarfile.open(
                fileobj=io.BytesIO(members[ENGINE_MEMBERS[1]]), mode="r:gz"
            ) as source:
                from aiflow.resource_bundle import RESOURCE_KINDS

                total = 0
                names: set[str] = set()
                ordinary: set[str] = set()
                resources = {".ai/" + name for name in RESOURCE_KINDS}
                for index, item in enumerate(source):
                    if index >= MAX_ENTRIES or not (item.isfile() or item.isdir()):
                        raise _error("Source sdist member kind/count is invalid")
                    name = _path(item.name.rstrip("/"))
                    if not name.startswith("aiflow-0.2.0/") and name != "aiflow-0.2.0":
                        raise _error("Source sdist has an unexpected root")
                    if name.casefold() in names or item.size > MAX_FILE_BYTES:
                        raise _error("Source sdist has aliases or oversized files")
                    names.add(name.casefold())
                    total += item.size
                    if total > MAX_ROLE_BYTES or any(
                        part in {".git", "node_modules", "logs", "tasks"}
                        for part in PurePosixPath(name).parts
                    ):
                        raise _error("Source sdist exceeds distributable scope")
                    if item.isfile():
                        relative = name.removeprefix("aiflow-0.2.0/")
                        if relative not in {
                            "LICENSE",
                            "pyproject.toml",
                            "setup.py",
                            "MANIFEST.in",
                            "PKG-INFO",
                            "setup.cfg",
                        } | resources and not re.fullmatch(
                            r"src/aiflow/[A-Za-z_][A-Za-z0-9_]*\.py", relative
                        ):
                            raise _error("Source sdist has an unauthorized regular member")
                        ordinary.add(relative)
                        if relative == "setup.cfg":
                            stream = source.extractfile(item)
                            if stream is None or stream.read(128) not in {
                                b"[egg_info]\ntag_build = \ntag_date = 0\n\n",
                                b"[egg_info]\r\ntag_build = \r\ntag_date = 0\r\n\r\n",
                            }:
                                raise _error("Source sdist generated configuration differs")
                if not resources.issubset(ordinary) or not {
                    "LICENSE",
                    "pyproject.toml",
                    "setup.py",
                    "MANIFEST.in",
                    "PKG-INFO",
                    "src/aiflow/__init__.py",
                }.issubset(ordinary):
                    raise _error("Source sdist omits required distribution resources")
            all_refs = {
                name: {"member": name, "size": len(data), "sha256": _sha(data)}
                for name, data in {**members, ENGINE_MEMBERS[3]: raw_manifest}.items()
            }
            if selection is not None:
                chosen = dict(selection)
                for key in ("wheel", "sdist", "build_manifest"):
                    if chosen[key] != all_refs[chosen[key]["member"]]:
                        raise _error("Chosen source member differs from the complete archive")
                if any(
                    manifest[key] != chosen[other]
                    for key, other in (
                        ("source_head", "source_head"),
                        ("run_id", "run_id"),
                        ("run_attempt", "run_attempt"),
                        ("workflow_blob_sha256", "workflow_sha256"),
                    )
                ):
                    raise _error("Source build manifest has a different producer binding")
            return {"manifest": manifest, "members": all_refs, **wheels[0]}
    except (OSError, ValueError, KeyError, tarfile.TarError, zipfile.BadZipFile) as error:
        raise _error("Source artifact archive is invalid") from error


def _gh_executable() -> Path:
    candidates = [Path(os.environ["AIFLOW_GH_EXE"])] if "AIFLOW_GH_EXE" in os.environ else []
    if os.environ.get("GITHUB_WORKSPACE"):
        candidates.append(Path(os.environ["GITHUB_WORKSPACE"]) / "tools/gh/bin/gh.exe")
    candidates.append(Path.cwd() / "build/adoption/tooling/gh/bin/gh.exe")
    for candidate in candidates:
        if candidate.is_file():
            candidate = candidate.absolute()
            if _sha(_read(candidate)) != GH_EXE_SHA256:
                raise _error(
                    "Official GitHub client integrity differs", "NODE_CI_PLATFORM_UNVERIFIED"
                )
            return candidate
    raise _error("Pinned official GitHub client is unavailable", "NODE_CI_PLATFORM_UNVERIFIED")


def _gh_environment() -> dict[str, str]:
    env = {
        key: os.environ[key]
        for key in (
            "SystemRoot",
            "WINDIR",
            "PATH",
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "GH_CONFIG_DIR",
            "GH_TOKEN",
            "GITHUB_TOKEN",
            "TEMP",
            "TMP",
            "TMPDIR",
        )
        if key in os.environ
    }
    env.update(
        GH_HOST="github.com",
        GH_PROMPT_DISABLED="1",
        GH_NO_UPDATE_NOTIFIER="1",
        GH_NO_EXTENSION_UPDATE_NOTIFIER="1",
        NO_COLOR="1",
    )
    return env


def _new_api_capture(prefix: str = "control/api-observations") -> dict[str, Any]:
    """Create one finite, non-authoritative collection of actual GET originals."""
    _path(prefix)
    if prefix not in {"control/api-observations", "api-observations"}:
        raise _error("CI API originals prefix is not a fixed owned role")
    index = {"kind": "aiflow-node-ci-api-observations", "schema_version": "1.0", "observations": []}
    return {
        "prefix": prefix,
        "observations": [],
        "total_bytes": len(_canonical(index)),
        "written": 0,
        "sealed": False,
    }


def _api_receipt(receipt: Any) -> dict[str, Any]:
    fields = {
        "process_id",
        "creation_time_filetime",
        "created_suspended",
        "assigned",
        "initial_membership",
        "resumed",
        "job_empty",
        "stdout_eof",
        "stderr_eof",
        "terminate_requested",
        "closed",
    }
    value = _obj(receipt, fields)
    for name in ("process_id", "creation_time_filetime"):
        _integer(value[name], minimum=1, maximum=(1 << 64) - 1)
    if any(
        value[name] is not (name != "terminate_requested")
        for name in fields - {"process_id", "creation_time_filetime"}
    ):
        raise _error("CI API Job lifecycle receipt is incomplete")
    return value


def _capture_api_response(
    capture: dict[str, Any],
    endpoint: str,
    raw: bytes,
    value: Any,
    receipt: Mapping[str, object] | None,
) -> None:
    if capture["sealed"] is not False:
        raise _error("CI API originals collection is already sealed")
    if len(raw) > 1024 * 1024 or len(capture["observations"]) >= MAX_ENTRIES:
        raise _error("CI API originals exceed their response/count bound", "NODE_CI_LIMIT_EXCEEDED")
    if receipt is None:
        raise _error("CI API observation has no actual Job receipt", "NODE_CI_PLATFORM_UNVERIFIED")
    # The existing Job receipt contains only process identity and lifecycle facts.
    # Never retain subprocess environment, stderr, HTTP headers or redirect URLs.
    receipt_bytes = _canonical(_api_receipt(dict(receipt)))
    if len(receipt_bytes) > 4096:
        raise _error("CI API Job receipt is oversized", "NODE_CI_LIMIT_EXCEEDED")
    sequence = len(capture["observations"]) + 1
    name = f"{capture['prefix']}/{sequence:06d}"
    entry = {
        "sequence": sequence,
        "method": "GET",
        "endpoint": endpoint,
        "response": {"ref": name + ".response.raw", "size": len(raw), "sha256": _sha(raw)},
        "response_canonical_sha256": _sha(_canonical(value)),
        "receipt": {
            "ref": name + ".receipt.json",
            "size": len(receipt_bytes),
            "sha256": _sha(receipt_bytes),
        },
    }
    total = (
        capture["total_bytes"]
        + len(raw)
        + len(receipt_bytes)
        + len(_canonical(entry))
        + (1 if sequence > 1 else 0)
    )
    if total > MAX_JSON_BYTES:
        raise _error(
            "CI API originals exceed their aggregate 16MiB bound", "NODE_CI_LIMIT_EXCEEDED"
        )
    capture["observations"].append({"entry": entry, "response": raw, "receipt": receipt_bytes})
    capture["total_bytes"] = total


def _write_api_observations(root: Path, capture: dict[str, Any], *, seal: bool = True) -> None:
    """Spool actual responses exclusively; the final index is never rewritten."""
    if capture["sealed"] is not False:
        raise _error("CI API originals are already sealed")
    _ordinary(root, directory=True)
    index = {
        "kind": "aiflow-node-ci-api-observations",
        "schema_version": "1.0",
        "observations": [item["entry"] for item in capture["observations"]],
    }
    raw_index = _canonical(index)
    if (
        len(raw_index)
        + sum(len(item["response"]) + len(item["receipt"]) for item in capture["observations"])
        != capture["total_bytes"]
        or capture["total_bytes"] > MAX_JSON_BYTES
    ):
        raise _error("CI API originals collection budget differs", "NODE_CI_LIMIT_EXCEEDED")
    for item in capture["observations"][capture["written"] :]:
        for name in ("response", "receipt"):
            ref = _ref(item["entry"][name])
            raw = item[name]
            if len(raw) != ref["size"] or _sha(raw) != ref["sha256"]:
                raise _error("CI API original no longer matches its captured bytes")
            _write_new(root / ref["ref"], raw)
        capture["written"] += 1
    if seal:
        _write_new(root / (capture["prefix"] + ".json"), raw_index)
        capture["sealed"] = True


def _validate_api_observations(root: Path, *, prefix: str = "control/api-observations") -> None:
    """Validate retained content, never use these JSON claims as authentication."""
    index_bytes = _read(root / (prefix + ".json"), limit=MAX_JSON_BYTES)
    index = _obj(_json(index_bytes), {"kind", "schema_version", "observations"})
    if (
        index["kind"] != "aiflow-node-ci-api-observations"
        or index["schema_version"] != "1.0"
        or _canonical(index) != index_bytes
    ):
        raise _error("CI API originals index is invalid")
    rows = _list(index["observations"])
    if not rows:
        raise _error("CI API response originals are missing")
    total = len(index_bytes)
    expected = set()
    for sequence, row in enumerate(rows, 1):
        _obj(
            row,
            {"sequence", "method", "endpoint", "response", "response_canonical_sha256", "receipt"},
        )
        if (
            type(row["sequence"]) is not int
            or row["sequence"] != sequence
            or row["method"] != "GET"
            or not re.fullmatch(
                r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_./?=&+-]+)?",
                _text(row["endpoint"], limit=4096),
            )
            or ".." in row["endpoint"]
        ):
            raise _error("CI API observation selector/sequence differs")
        originals = {}
        for name, suffix, limit in (
            ("response", ".response.raw", 1024 * 1024),
            ("receipt", ".receipt.json", 4096),
        ):
            ref = _ref(row[name])
            filename = f"{sequence:06d}" + suffix
            if ref["ref"] != prefix + "/" + filename or ref["size"] > limit:
                raise _error("CI API observation original reference differs")
            total += ref["size"]
            if total > MAX_JSON_BYTES:
                raise _error("CI API originals exceed aggregate bound", "NODE_CI_LIMIT_EXCEEDED")
            raw = _read(root / ref["ref"], limit=limit)
            if len(raw) != ref["size"] or _sha(raw) != ref["sha256"]:
                raise _error("CI API response/receipt raw original changed")
            originals[name] = raw
            expected.add(filename)
        if (
            _sha(_canonical(_json(originals["response"])))
            != _digest(row["response_canonical_sha256"])
            or _canonical(_api_receipt(_json(originals["receipt"]))) != originals["receipt"]
        ):
            raise _error("CI API response/receipt canonical binding differs")
    directory = root / prefix
    _ordinary(directory, directory=True)
    if {path.name for path in directory.iterdir()} != expected:
        raise _error("CI API observation physical membership differs")


def _gh_json(endpoint: str, *, _capture: dict[str, Any] | None = None) -> Any:
    from aiflow.process_runner import run_node_process

    executable = _gh_executable()
    result = run_node_process(
        (
            str(executable),
            "api",
            "--hostname",
            "github.com",
            "--method",
            "GET",
            "--header",
            "Accept: application/vnd.github+json",
            endpoint,
        ),
        cwd=Path.cwd().absolute(),
        environment=_gh_environment(),
        timeout_seconds=60,
    )
    if (
        result.returncode != 0
        or result.timed_out
        or result.stdout_overflow
        or result.stderr_overflow
        or result.cleanup != "confirmed"
        or result.execution_error
        or len(result.stdout) > 1024 * 1024
    ):
        raise _error(
            "Authenticated GitHub GET did not complete safely", "NODE_CI_PLATFORM_UNVERIFIED"
        )
    value = _json(result.stdout)
    if _capture is not None:
        _capture_api_response(_capture, endpoint, result.stdout, value, result.receipt)
    return value


def github_get(
    endpoint: str, *, paginate: bool = False, _capture: dict[str, Any] | None = None
) -> Any:
    """Read fixed GitHub repository endpoints using the pinned official client."""
    if (
        not isinstance(endpoint, str)
        or not re.fullmatch(
            r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_./?=&+-]+)?", endpoint
        )
        or ".." in endpoint
    ):
        raise _error("GitHub endpoint is outside the read-only repository scope")
    if not paginate:
        return _gh_json(endpoint) if _capture is None else _gh_json(endpoint, _capture=_capture)
    if "page=" in endpoint:
        raise _error("Caller cannot override authenticated pagination")
    accumulated: list[Any] = []
    total_bytes = 0
    expected_total: int | None = None
    collection: str | None = None
    for page in range(1, MAX_ENTRIES // 100 + 2):
        selected = endpoint + ("&" if "?" in endpoint else "?") + f"per_page=100&page={page}"
        value = _gh_json(selected) if _capture is None else _gh_json(selected, _capture=_capture)
        total_bytes += len(_canonical(value))
        if total_bytes > MAX_JSON_BYTES:
            raise _error("GitHub pagination exceeds its response bound", "NODE_CI_LIMIT_EXCEEDED")
        if isinstance(value, list):
            if collection not in {None, "array"}:
                raise _error("GitHub collection changed during pagination")
            collection = "array"
            rows = value
        elif isinstance(value, dict):
            keys = [
                key for key in ("jobs", "artifacts", "workflow_runs", "check_runs") if key in value
            ]
            if len(keys) != 1:
                raise _error("GitHub paginated collection is unsupported")
            if collection not in {None, keys[0]}:
                raise _error("GitHub collection changed during pagination")
            collection = keys[0]
            rows = _list(value[keys[0]])
            total = _integer(value.get("total_count"), maximum=MAX_ENTRIES)
            if expected_total is not None and expected_total != total:
                raise _error("GitHub collection changed during pagination")
            expected_total = total
        else:
            raise _error("GitHub collection is not an array")
        accumulated.extend(rows)
        if len(accumulated) > MAX_ENTRIES:
            raise _error("GitHub collection is oversized", "NODE_CI_LIMIT_EXCEEDED")
        if len(rows) < 100:
            if expected_total is not None and len(accumulated) != expected_total:
                raise _error("GitHub pagination is incomplete")
            identities = [row["id"] for row in accumulated if isinstance(row, dict) and "id" in row]
            for identity in identities:
                _integer(identity, minimum=1)
            if len(identities) != len(accumulated) or len(set(identities)) != len(identities):
                raise _error("GitHub pagination repeats or omits identities")
            return accumulated
    raise _error("GitHub pagination never terminated")


def _observed_get(
    endpoint: str, *, paginate: bool = False, _capture: dict[str, Any] | None = None
) -> Any:
    if _capture is None:
        return github_get(endpoint, paginate=paginate)
    return github_get(endpoint, paginate=paginate, _capture=_capture)


def _github_file(
    full_name: str, path: str, head: str, *, _capture: dict[str, Any] | None = None
) -> bytes:
    _digest(head, commit=True)
    _path(path)
    result = _observed_get(f"repos/{full_name}/contents/{path}?ref={head}", _capture=_capture)
    if (
        not isinstance(result, dict)
        or result.get("type") != "file"
        or result.get("encoding") != "base64"
    ):
        raise _error("GitHub source blob is not an ordinary file")
    try:
        if not isinstance(result["content"], str):
            raise ValueError("nontext content")
        data = base64.b64decode(result["content"].replace("\n", ""), validate=True)
    except (ValueError, TypeError, KeyError) as error:
        raise _error("GitHub source blob encoding is invalid") from error
    if (
        len(data) > MAX_JSON_BYTES
        or type(result.get("size")) is not int
        or result.get("size") != len(data)
        or hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        != result.get("sha")
    ):
        raise _error("GitHub source blob identity differs")
    return data


def authenticate_workflow(
    repository_id: int,
    full_name: str,
    workflow_path: str,
    job_key: str,
    *,
    run_id: int,
    attempt: int,
    completed: bool,
    _capture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Obtain an actual exact-attempt observation, never authenticate caller JSON."""
    _integer(repository_id, minimum=1)
    _integer(run_id, minimum=1)
    _integer(attempt, minimum=1)
    if (
        not _REPOSITORY.fullmatch(full_name)
        or {SOURCE_WORKFLOW: SOURCE_JOB, TARGET_WORKFLOW: TARGET_JOB}.get(workflow_path) != job_key
    ):
        raise _error("Workflow selector is unsupported")
    actual_repo = _observed_get(f"repos/{full_name}", _capture=_capture)
    if (
        not isinstance(actual_repo, dict)
        or type(actual_repo.get("id")) is not int
        or actual_repo.get("id") != repository_id
        or actual_repo.get("full_name") != full_name
        or actual_repo.get("private") is not (workflow_path == TARGET_WORKFLOW)
    ):
        raise _error("Authenticated repository identity differs")
    repository = _observed_get(
        f"repos/{full_name}/actions/workflows/{PurePosixPath(workflow_path).name}",
        _capture=_capture,
    )
    if not isinstance(repository, dict) or repository.get("path") != workflow_path:
        raise _error("Authenticated workflow path differs")
    workflow_id = _integer(repository.get("id"), minimum=1)
    run = _observed_get(
        f"repos/{full_name}/actions/runs/{run_id}/attempts/{attempt}", _capture=_capture
    )
    if not isinstance(run, dict) or any(
        run.get(key) != expected
        for key, expected in {
            "id": run_id,
            "run_attempt": attempt,
            "workflow_id": workflow_id,
            "event": "pull_request",
        }.items()
    ):
        raise _error("Authenticated workflow attempt differs")
    for key in ("id", "run_attempt", "workflow_id", "check_suite_id"):
        _integer(run.get(key), minimum=1)
    repo = run.get("repository")
    if (
        not isinstance(repo, dict)
        or repo.get("id") != repository_id
        or repo.get("full_name") != full_name
    ):
        raise _error("Authenticated workflow repository differs")
    head = _digest(run.get("head_sha"), commit=True)
    pulls = run.get("pull_requests")
    if not isinstance(pulls, list) or len(pulls) != 1:
        raise _error("Workflow has no unique same-repository PR")
    pr_head = pulls[0].get("head", {})
    if pr_head.get("sha") != head or pr_head.get("repo", {}).get("id") != repository_id:
        raise _error("Workflow is not bound to its same-repository PR head")
    number = _integer(pulls[0].get("number"), minimum=1)
    pr = _observed_get(f"repos/{full_name}/pulls/{number}", _capture=_capture)
    if (
        not isinstance(pr, dict)
        or pr.get("number") != number
        or type(pr.get("number")) is not int
        or pr.get("state") != "open"
    ):
        raise _error("Workflow pull request is unavailable or closed")
    for side in ("head", "base"):
        selected = pr.get(side)
        linked = pulls[0].get(side)
        if (
            not isinstance(selected, dict)
            or not isinstance(linked, dict)
            or selected.get("sha") != linked.get("sha")
            or selected.get("repo", {}).get("id") != repository_id
            or linked.get("repo", {}).get("id") != repository_id
        ):
            raise _error("Actual PR and exact-attempt head/base differ")
        _digest(selected.get("sha"), commit=True)
    if pr["head"]["sha"] != head or pr["head"].get("ref") != run.get("head_branch"):
        raise _error("Actual PR branch/head differs from workflow")
    merge = _observed_get(f"repos/{full_name}/git/ref/pull/{number}/merge", _capture=_capture)
    if (
        not isinstance(merge, dict)
        or merge.get("ref") != f"refs/pull/{number}/merge"
        or merge.get("object", {}).get("type") != "commit"
    ):
        raise _error("Actual merge execution reference is unavailable")
    merge_sha = _digest(merge["object"].get("sha"), commit=True)
    if merge_sha != pr.get("merge_commit_sha"):
        raise _error("PR merge reference changed")
    commit = _observed_get(f"repos/{full_name}/git/commits/{merge_sha}", _capture=_capture)
    parents = commit.get("parents") if isinstance(commit, dict) else None
    if (
        not isinstance(commit, dict)
        or commit.get("sha") != merge_sha
        or not isinstance(parents, list)
        or len(parents) != 2
        or {parent.get("sha") for parent in parents if isinstance(parent, dict)}
        != {head, pr["base"]["sha"]}
    ):
        raise _error("Workflow merge execution has different parents")
    if run.get("referenced_workflows"):
        raise _error("Reusable workflow execution is not supported")
    jobs = _observed_get(
        f"repos/{full_name}/actions/runs/{run_id}/attempts/{attempt}/jobs",
        paginate=True,
        _capture=_capture,
    )
    if len(jobs) != 1 or jobs[0].get("name") != job_key:
        raise _error("Workflow job identity is ambiguous")
    job = jobs[0]
    if (
        job.get("run_id") != run_id
        or job.get("run_attempt") != attempt
        or job.get("head_sha") != head
    ):
        raise _error("Workflow job belongs to another attempt/head")
    for key in ("id", "run_id", "run_attempt"):
        _integer(job.get(key), minimum=1)
    match = re.fullmatch(
        rf"https://api\.github\.com/repos/{re.escape(full_name)}/check-runs/([0-9]+)",
        str(job.get("check_run_url", "")),
    )
    if match is None:
        raise _error("Workflow job has no authenticated Check link")
    check_id = int(match[1])
    check = _observed_get(f"repos/{full_name}/check-runs/{check_id}", _capture=_capture)
    if (
        not isinstance(check, dict)
        or check.get("id") != check_id
        or type(check.get("id")) is not int
        or check.get("head_sha") != head
        or check.get("name") != job_key
        or check.get("app", {}).get("id") != APP_ID
        or type(check.get("app", {}).get("id")) is not int
        or check.get("check_suite", {}).get("id") != run.get("check_suite_id")
    ):
        raise _error("Workflow Check identity differs")
    for observation in (run, job, check):
        if completed:
            if (
                observation.get("status") != "completed"
                or observation.get("conclusion") != "success"
            ):
                raise _error("Workflow Check is not completed successfully")
        elif (
            observation.get("status") not in {"queued", "in_progress"}
            or observation.get("conclusion") is not None
        ):
            raise _error("Producer cannot borrow a completed or failed attempt")
    data = _github_file(full_name, workflow_path, head, _capture=_capture)
    if data != _github_file(full_name, workflow_path, merge_sha, _capture=_capture):
        raise _error("Executed merge workflow differs from declared PR workflow")
    platform = {
        "provider": "github",
        "repository_id": repository_id,
        "full_name": full_name,
        "workflow_id": workflow_id,
        "workflow_path": workflow_path,
        "workflow_ref": f"refs/pull/{number}/merge",
        "workflow_sha256": _sha(data),
        "event": "pull_request",
        "head_sha": head,
        "run_id": run_id,
        "run_attempt": attempt,
        "job_id": _integer(job.get("id"), minimum=1),
        "job_key": job_key,
        "check_run_id": check_id,
        "check_name": job_key,
        "app_id": APP_ID,
    }
    return _platform(platform)


def _select_artifact(
    platform: Mapping[str, Any], *, name: str, _capture: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Select one live exact-attempt artifact using authenticated provider facts."""
    _platform(dict(platform))
    _text(name)
    prefix = f"repos/{platform['full_name']}"
    job = _observed_get(f"{prefix}/actions/jobs/{platform['job_id']}", _capture=_capture)
    if (
        not isinstance(job, dict)
        or any(
            job.get(key) != platform[other]
            for key, other in (
                ("id", "job_id"),
                ("run_id", "run_id"),
                ("run_attempt", "run_attempt"),
                ("head_sha", "head_sha"),
                ("name", "job_key"),
            )
        )
        or job.get("status") != "completed"
        or job.get("conclusion") != "success"
    ):
        raise _error("Artifact job is not this completed exact attempt")
    for key in ("id", "run_id", "run_attempt"):
        _integer(job.get(key), minimum=1)
    start = datetime.fromisoformat(_timestamp(job.get("started_at")).replace("Z", "+00:00"))
    end = datetime.fromisoformat(_timestamp(job.get("completed_at")).replace("Z", "+00:00"))
    if start > end:
        raise _error("Artifact job timing is invalid")
    artifacts = _observed_get(
        f"{prefix}/actions/runs/{platform['run_id']}/artifacts", paginate=True, _capture=_capture
    )
    if not isinstance(artifacts, list):
        raise _error("Artifact collection is invalid")
    matches = [item for item in artifacts if isinstance(item, dict) and item.get("name") == name]
    if len(matches) != 1:
        raise _error("Artifact selection is missing or ambiguous")
    artifact = matches[0]
    _integer(artifact.get("id"), minimum=1)
    _integer(artifact.get("size_in_bytes"), minimum=1, maximum=19 * MAX_ROLE_BYTES)
    _provider_digest(artifact.get("digest"))
    run = artifact.get("workflow_run")
    if not isinstance(run, dict) or any(
        run.get(key) != platform[other]
        for key, other in (
            ("id", "run_id"),
            ("repository_id", "repository_id"),
            ("head_repository_id", "repository_id"),
            ("head_sha", "head_sha"),
        )
    ):
        raise _error("Artifact is associated with another run/repository/head")
    for key in ("id", "repository_id", "head_repository_id"):
        _integer(run.get(key), minimum=1)
    created = datetime.fromisoformat(_timestamp(artifact.get("created_at")).replace("Z", "+00:00"))
    expires = datetime.fromisoformat(_timestamp(artifact.get("expires_at")).replace("Z", "+00:00"))
    if (
        artifact.get("expired") is not False
        or expires <= datetime.now(timezone.utc)
        or not start <= created <= end
    ):
        raise _error("Artifact is expired or belongs to another attempt window")
    return artifact


def _git_blob(root: Path, head: str, name: str) -> bytes:
    from aiflow.node_execution import _git

    _digest(head, commit=True)
    _path(name)
    oid = _git(root, "rev-parse", f"{head}:{name}").decode().strip()
    _digest(oid, commit=True)
    size = int(_git(root, "cat-file", "-s", oid).decode().strip())
    if not 0 <= size <= MAX_JSON_BYTES:
        raise _error("Committed CI control blob is oversized", "NODE_CI_LIMIT_EXCEEDED")
    data = _git(root, "cat-file", "blob", oid)
    if (
        len(data) != size
        or hashlib.sha1(b"blob " + str(size).encode() + b"\0" + data).hexdigest() != oid
    ):
        raise _error("Committed CI control blob identity differs")
    return data


def _committed_diff(root: Path, base: str, subject: str) -> dict[str, Any]:
    from aiflow.node_execution import _git

    rows = []
    additions = deletions = 0
    for line in (
        _git(
            root,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--numstat",
            "--no-renames",
            "--format=",
            base,
            subject,
            "--",
        )
        .decode("utf-8")
        .splitlines()
    ):
        parts = line.split("\t", 2)
        if len(parts) != 3:
            raise _error("Committed source diff is invalid")
        binary = parts[:2] == ["-", "-"]
        added, removed = (None, None) if binary else (int(parts[0]), int(parts[1]))
        additions += added or 0
        deletions += removed or 0
        rows.append(
            {
                "path": parts[2].replace("\\", "/"),
                "additions": added,
                "deletions": removed,
                "binary": binary,
            }
        )
    rows.sort(key=lambda row: str(row["path"]))
    return {
        "changed_paths": [row["path"] for row in rows],
        "files": rows,
        "totals": {"files": len(rows), "additions": additions, "deletions": deletions},
    }


def _source_ask_identity(payload: Mapping[str, Any]) -> tuple[str, str, str]:
    from aiflow.ask_service import _require_answer_identity

    actor, reason, selection = (
        payload.get(name) for name in ("actor", "reason", "selected_option_id")
    )
    if not isinstance(actor, str) or not isinstance(reason, str) or not isinstance(selection, str):
        raise _error("CI source ASK actor/reason/selection must be actual strings")
    normalized = _require_answer_identity(actor, reason, selection)
    if (actor, reason, selection) != normalized:
        raise _error("CI source ASK identity differs from its recorded normalized transaction")
    return normalized


def _build_source_authority(
    source_root: Path,
    task_id: str,
    *,
    head: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes]]:
    """Authenticate committed source metadata, explicitly without local Current."""
    from aiflow import node_execution as node
    from aiflow import review_service as review
    from aiflow import verifier_service as verifier
    from aiflow.approval import ApprovalContext, approval_is_current
    from aiflow.ask_service import render_frozen_decision_section, validate_ask_options
    from aiflow.classification_service import _entries
    from aiflow.contracts import require_valid_contract
    from aiflow.decision_units import parse_decision_units
    from aiflow.document_parsing import load_yaml_text
    from aiflow.evidence import (
        finalize_v2_evidence,
        prepare_v2_pre_evidence,
        validate_node_evidence,
        validate_v2_snapshot,
    )
    from aiflow.freshness import current_classification_input_digest, evaluate_freshness
    from aiflow.policy import POLICY_FILES, is_node_policy, load_policy_bundle
    from aiflow.routing import entry_requires_ask, route_task
    from aiflow.scope import is_task_governance_path
    from aiflow.specification import specification_digest
    from aiflow.state import replay_events
    from aiflow.task_service import (
        TaskRecord,
        _require_materialized_risk_facts,
        read_task_record_strict,
    )
    from aiflow.verification_level import verification_for_task
    from aiflow.verification_service import _ci_git_assessment

    source_root = source_root.absolute()
    current_head = node._git(source_root, "rev-parse", "HEAD").decode().strip()
    selected_head = _digest(head or current_head, commit=True)
    node._git(source_root, "merge-base", "--is-ancestor", selected_head, current_head)
    if not re.fullmatch(r"TASK-[0-9]{4,}", task_id):
        raise _error("CI source task is invalid")
    prefix = f".ai/tasks/{task_id}/"
    blobs: dict[str, bytes] = {}

    def blob(name: str) -> tuple[bytes, dict[str, Any]]:
        logical = "control/blobs/" + name
        if logical not in blobs:
            blobs[logical] = _git_blob(source_root, selected_head, name)
        data = blobs[logical]
        return data, {"ref": logical, "size": len(data), "sha256": _sha(data)}

    def document(name: str, *, yaml_document: bool = False) -> Any:
        data, _reference = blob(name)
        return load_yaml_text(data.decode("utf-8")) if yaml_document else _json(data)

    task = document(prefix + "task.yaml", yaml_document=True)
    require_valid_contract("task", task)
    if task["current_state"] not in {"VERIFIED", "WAITING_FOR_FINAL_REVIEW", "APPROVED_FOR_MERGE"}:
        raise _error("Committed CI source is not in an eligible completed verification state")
    raw_events, events_ref = blob(prefix + "events.jsonl")
    events = tuple(_json(line) for line in raw_events.splitlines() if line.strip())
    if not events or replay_events(events, task_id=task_id) != task["current_state"]:
        raise _error("Committed source task does not match replay")
    record = TaskRecord(task=task, events=events)
    _require_materialized_risk_facts(record)
    paths = (
        node._git(source_root, "ls-tree", "-r", "--name-only", selected_head, "--", prefix)
        .decode()
        .splitlines()
    )
    if any(
        name.endswith(("_pending.json", "task.yaml.next", "creation_failed.json")) for name in paths
    ):
        raise _error("Committed source has an incomplete governance transaction")
    if selected_head == current_head:
        physical = read_task_record_strict(source_root, task_id)
        if _canonical(physical.task) != _canonical(task) or _canonical(
            physical.events
        ) != _canonical(events):
            raise _error("CI checkout metadata differs from committed source")
        if (
            _ci_git_assessment(source_root, task_id, record).subject_commit
            != task["subject_commit"]
        ):
            raise _error("CI source requires subject synchronization")
    node._git(
        source_root, "merge-base", "--is-ancestor", task["base_commit"], task["subject_commit"]
    )
    node._git(source_root, "merge-base", "--is-ancestor", task["subject_commit"], selected_head)
    for commit in (
        node._git(
            source_root, "rev-list", "--reverse", f"{task['subject_commit']}..{selected_head}"
        )
        .decode()
        .splitlines()
    ):
        changed = (
            node._git(
                source_root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "-m",
                "--no-renames",
                commit,
                "--",
            )
            .decode()
            .splitlines()
        )
        if any(not is_task_governance_path(name, task_id) for name in changed):
            raise _error("CI attestation includes a non-governance intermediate commit")
    bundle = load_policy_bundle(source_root)
    if bundle.policy_version != "3.2.0" or not is_node_policy(bundle):
        raise _error("CI source requires the exact Node2 Policy")
    policy_refs = []
    for name in POLICY_FILES:
        committed = document(".ai/policy/" + name, yaml_document=True)
        if committed != bundle.documents[name]:
            raise _error("CI committed Policy differs from trusted selected Policy")
        policy_refs.append(blob(".ai/policy/" + name)[1])
    units = parse_decision_units(task)
    classification = document(prefix + "classification.json")
    require_valid_contract("classification", classification)
    routes = route_task(task, bundle)
    verification = verification_for_task(task, bundle)
    expected_entries = _entries(
        routes,
        verification,
        version=bundle.policy_version,
        digest=bundle.sha256,
        at=classification["classified_at"],
    )
    if (
        routes.effective_route == "BLOCK"
        or verification.blocking_reasons
        or classification["classifications"] != expected_entries
        or classification["effective_route"] != routes.effective_route
        or classification["effective_verification_level"] != verification.level
    ):
        raise _error("CI committed classification does not recompute")
    digest, synchronized = current_classification_input_digest(task, units, classification, events)
    spec_bytes, spec_ref = blob(prefix + "spec.md")
    spec = spec_bytes.decode("utf-8").replace("\r\n", "\n")
    spec_sha = specification_digest(spec)
    current = {
        "task_id": task_id,
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "policy_sha256": bundle.sha256,
        "classification_input_sha256": digest,
        "subject_synchronized": synchronized,
    }
    if (
        evaluate_freshness("classification", classification, current).status != "fresh"
        or task.get("frozen_spec_sha256") != spec_sha
    ):
        raise _error("CI source classification/specification is stale")
    for entry in classification["classifications"]:
        if not entry_requires_ask(entry):
            continue
        candidates = [
            event
            for event in events
            if event["event_type"] == "ask_answered"
            and event["payload"].get("options", {}).get("decision_unit_id")
            == entry["decision_unit_id"]
        ]
        if not candidates:
            raise _error("CI source has an unanswered ASK")
        event = candidates[-1]
        payload = event["payload"]
        options = validate_ask_options(payload.get("options", {}), task_id=task_id)
        ask_actor, ask_reason, ask_selection = _source_ask_identity(payload)
        selected = [
            option for option in _list(options["options"]) if option["option_id"] == ask_selection
        ]
        if (
            len(selected) != 1
            or ask_actor != event["actor"]
            or payload.get("options_sha256") != _sha(_canonical(options))
            or payload.get("classification_input_sha256")
            != classification["classification_input_sha256"]
            or payload.get("policy_sha256") != bundle.sha256
            or payload.get("specification_sha256") != spec_sha
            or payload.get("answered_at") != event["occurred_at"]
        ):
            raise _error("CI source ASK transaction bindings differ")
        section = render_frozen_decision_section(
            decision_unit_id=entry["decision_unit_id"],
            selected_option=selected[0],
            actor=ask_actor,
            reason=ask_reason,
            answered_at=payload["answered_at"],
        )
        if section not in spec:
            raise _error("CI source ASK frozen decision differs")
    evidence = document(prefix + "evidence.json")
    validate_node_evidence(evidence, require_passed=True)
    level = verification.level
    binding = {
        key: task[key]
        for key in ("repository_id", "task_id", "branch", "base_commit", "subject_commit")
    }
    binding.update(
        subject_tree=node._git(source_root, "rev-parse", task["subject_commit"] + "^{tree}")
        .decode()
        .strip(),
        policy_sha256=bundle.sha256,
        spec_sha256=spec_sha,
        classification_input_sha256=digest,
        decision_unit_ids=[unit["decision_unit_id"] for unit in units],
        verification_level=level,
    )
    if (
        evidence["schema_version"] != "3.2"
        or any(
            evidence.get(key) != value for key, value in binding.items() if key != "subject_tree"
        )
        or evidence["node_binding"]["subject_tree"] != binding["subject_tree"]
    ):
        raise _error("CI committed final evidence has another source binding")
    final_sha = _sha(_canonical(evidence))
    diff = _committed_diff(source_root, task["base_commit"], task["subject_commit"])
    expected_review: dict[str, dict[str, Any]] = {}
    for stage in ("design", "implementation"):
        context = {
            "schema_version": "1.0",
            "review_stage": stage,
            **{
                key: binding[key]
                for key in (
                    "task_id",
                    "decision_unit_ids",
                    "repository_id",
                    "branch",
                    "base_commit",
                    "spec_sha256",
                    "policy_sha256",
                    "classification_input_sha256",
                )
            },
            "content": review._context_content(task, classification),
        }
        if stage == "implementation":
            context.update(subject_commit=task["subject_commit"])
            if level == "V2":
                context.update(
                    schema_version="2.0",
                    verification_snapshot_sha256=evidence.get("verification_snapshot_sha256"),
                )
            else:
                context["evidence_sha256"] = final_sha
            context["content"].update(
                diff_summary=diff,
                verification_summary={
                    **review._verification_summary(evidence),
                    "materials_sha256": evidence["node_binding"]["materials_sha256"],
                    "node_binding_sha256": evidence["node_binding_sha256"],
                },
            )
        context["context_sha256"] = review._context_digest(context)
        expected_review[stage] = context
    registered: dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any], int]] = {}
    latest: dict[str, tuple[dict[str, Any], dict[str, Any], int]] = {}
    for index, event in enumerate(events):
        if event["event_type"] not in {"review_recorded", "review_finding_resolved"}:
            continue
        payload = event["payload"]
        identity = (_text(payload.get("review_id")), _integer(payload.get("revision"), minimum=1))
        review_name = prefix + f"reviews/{identity[0]}-r{identity[1]:04d}.json"
        value = document(review_name)
        previous = latest.get(identity[0])
        context_sha = (
            payload.get("context_sha256")
            if event["event_type"] == "review_recorded"
            else (previous[0]["context_sha256"] if previous is not None else None)
        )
        context = document(prefix + f"review-contexts/{_digest(context_sha)}.json")
        review.validate_review_record(value, context)
        if (
            (value["review_id"], value["revision"]) != identity
            or value["context_sha256"] != context_sha
            or (
                event["event_type"] == "review_recorded"
                and value["review_stage"] != payload.get("review_stage")
            )
        ):
            raise _error("CI registered review identity differs")
        if event["event_type"] == "review_recorded":
            if identity[1] != 1 or event["actor"] != value["reviewer"] or identity in registered:
                raise _error("CI registered initial review actor/revision differs")
        else:
            if previous is None:
                raise _error("CI review resolution has no prior revision")
            node._check_review_resolution(previous[0], value, event)
        registered.setdefault(identity, (value, context, index))
        latest[identity[0]] = (value, context, index)
    if {
        name
        for name in paths
        if re.fullmatch(re.escape(prefix) + r"reviews/REV-[0-9]+-r[0-9]+\.json", name)
    } != {prefix + f"reviews/{key[0]}-r{key[1]:04d}.json" for key in registered}:
        raise _error("CI source contains unregistered review originals")
    selected_reviews = {}
    for stage in ("design", "implementation"):
        candidates = [row for row in latest.values() if row[0]["review_stage"] == stage]
        if candidates:
            chosen = max(candidates, key=lambda row: row[2])
            if chosen[1] != expected_review[stage] or not review.review_is_approvable(chosen[0]):
                raise _error("CI latest committed review is stale or not approvable")
            selected_reviews[stage] = chosen
    approvals = document(prefix + "approvals.json")
    if not isinstance(approvals, list):
        raise _error("CI committed approvals are invalid")
    for approval in approvals:
        require_valid_contract("approval", approval)
    required_ids = {
        entry["decision_unit_id"]
        for entry in classification["classifications"]
        if entry["route"] == "REVIEW"
    }
    applicable: dict[str, list[dict[str, Any]]] = {"spec": [], "code": []}
    approval_events: dict[str, int] = {}
    for kind in ("spec", "code"):
        stage = "design" if kind == "spec" else "implementation"
        for approval in approvals:
            unit = approval["decision_unit_id"]
            ctx = ApprovalContext(
                task_id=task_id,
                decision_unit_id=unit,
                task_state=task["current_state"],
                spec_sha256=spec_sha,
                policy_sha256=bundle.sha256,
                base_commit=task["base_commit"],
                subject_commit=task["subject_commit"],
            )
            if approval.get("approval_type") != kind or not approval_is_current(approval, ctx):
                continue
            if kind == "code" and approval.get("evidence_sha256") != final_sha:
                continue
            if stage not in selected_reviews:
                raise _error("CI applicable approval lacks the current structured review")
            selected = selected_reviews[stage]
            matches = []
            for index, event in enumerate(events):
                structured = event["payload"].get("structured_review")
                if (
                    event["event_type"] != kind + "_approved"
                    or event["actor"] != approval["actor"]
                    or not isinstance(structured, dict)
                ):
                    continue
                reference = registered.get(
                    (
                        _text(structured.get("review_id")),
                        _integer(structured.get("revision"), minimum=1),
                    )
                )
                if reference is None or structured != {
                    key: reference[0][key]
                    for key in ("review_id", "revision", "review_stage", "context_sha256")
                }:
                    continue
                if (
                    reference[0]["review_id"] != selected[0]["review_id"]
                    or reference[1] != selected[1]
                    or not review.review_is_approvable(reference[0])
                    or index <= reference[2]
                ):
                    continue
                if any(
                    _canonical(candidate) == _canonical(approval)
                    for candidate in event["payload"].get("approvals", [])
                ):
                    matches.append((index, event))
            if not matches:
                raise _error("CI applicable approval has no corresponding registered event")
            approval_events[kind] = max(approval_events.get(kind, -1), matches[-1][0])
            row = {
                "record_sha256": _sha(_canonical(approval)),
                "decision_unit_id": unit,
                "approval_type": kind,
            }
            if kind == "code":
                row["evidence_sha256"] = final_sha
            applicable[kind].append(row)
        if not required_ids.issubset({row["decision_unit_id"] for row in applicable[kind]}):
            raise _error("CI source lacks complete applicable approvals")
    v2 = None
    if level == "V2":
        validate_v2_snapshot(evidence)
        if evidence.get("phase") != "final" or set(selected_reviews) != {
            "design",
            "implementation",
        }:
            raise _error("CI V2 source is not final")
        pre = prepare_v2_pre_evidence(evidence)
        if (
            finalize_v2_evidence(
                pre,
                implementation_review={
                    key: selected_reviews["implementation"][0][key]
                    for key in ("review_id", "context_sha256")
                },
            )
            != evidence
        ):
            raise _error("CI V2 final projection does not reconstruct")
        verifier_actor = evidence["verifier_actor"]
        verifier.validate_verifier_actor(verifier.current_implementer_actor(events), verifier_actor)
        verifier_context = document(
            prefix + f"verifier-contexts/{evidence['verifier_context_sha256']}.json"
        )
        verifier.validate_verifier_context(verifier_context)
        # This helper rebuilds committed metadata/diff only; it never replays LOCAL raw.
        expected_verifier = {
            "schema_version": "1.0",
            **{
                key: binding[key]
                for key in (
                    "task_id",
                    "decision_unit_ids",
                    "repository_id",
                    "branch",
                    "base_commit",
                    "subject_commit",
                    "spec_sha256",
                    "policy_sha256",
                    "classification_input_sha256",
                )
            },
            "content": {
                "goal": task["goal"],
                "frozen_spec": spec,
                "code_map": {
                    "allowed_scope": sorted(task["allowed_scope"]),
                    "changed_paths": diff["changed_paths"],
                },
                "diff_summary": {
                    **diff["totals"],
                    "binary_files": sum(row["binary"] for row in diff["files"]),
                },
                "acceptance_conditions": verifier._acceptance_conditions(spec, task),
                "known_limitations": [
                    "Node V2 requires the complete fixed product suite, exact coverage originals, "
                    "five installed mutation pairs and same-verifier finalization.",
                    "Node CI and real-target application require separate acceptance.",
                ],
                "reproduce_command": [
                    "python",
                    "-m",
                    "aiflow",
                    "verify",
                    task_id,
                    "--actor",
                    "<verifier>",
                    "--node-materials",
                    "<materials-sha256>",
                    "--installed-mutations",
                    "<IMUT-id>",
                ],
            },
        }
        expected_verifier["context_sha256"] = verifier.context_sha256(expected_verifier)
        if verifier_context != expected_verifier:
            raise _error("CI committed verifier context is stale")
        cycle = max(
            (
                index
                for index, event in enumerate(events)
                if event["event_type"] in {"implementation_started", "implementation_retried"}
            ),
            default=-1,
        )
        started = [
            (index, event)
            for index, event in enumerate(events)
            if index > cycle
            and event["event_type"] in {"verification_started", "verification_restarted"}
        ]
        passed = [
            (index, event)
            for index, event in enumerate(events)
            if event["event_type"] == "verification_passed"
        ]
        implementation_registered = min(
            row[2]
            for identity, row in registered.items()
            if identity[0] == selected_reviews["implementation"][0]["review_id"]
        )
        if (
            cycle < 0
            or not started
            or not passed
            or not cycle < started[-1][0] < passed[-1][0] < implementation_registered
            or (required_ids and not implementation_registered < approval_events.get("code", -1))
            or started[-1][1]["actor"] != verifier_actor
            or passed[-1][1]["actor"] != verifier_actor
        ):
            raise _error("CI V2 verification/review/code cycle is incomplete")
        for stage in ("design", "implementation"):
            if evidence["review_refs"][stage] != {
                key: selected_reviews[stage][0][key] for key in ("review_id", "context_sha256")
            }:
                raise _error("CI final review projection differs from latest registered review")
        v2 = {
            "snapshot_sha256": evidence["verification_snapshot_sha256"],
            "verifier_actor": verifier_actor,
            "verifier_context": blob(
                prefix + f"verifier-contexts/{evidence['verifier_context_sha256']}.json"
            )[1],
        }
        for stage in ("design", "implementation"):
            selected = selected_reviews[stage][0]
            v2[stage] = {
                "record": blob(
                    prefix + f"reviews/{selected['review_id']}-r{selected['revision']:04d}.json"
                )[1],
                "context": blob(prefix + f"review-contexts/{selected['context_sha256']}.json")[1],
                **{key: selected[key] for key in ("review_id", "revision", "context_sha256")},
            }
    declaration = validate_node_ci_document(document(DECLARATION), kind="aiflow-node-ci-producer")
    if (
        declaration["repository"]["repository_id"] != binding["repository_id"]
        or declaration["workflow"]["ref"] != "refs/heads/" + binding["branch"]
        or _sha(blob(TARGET_WORKFLOW)[0]) != declaration["workflow"]["sha256"]
    ):
        raise _error("CI static producer does not bind this source branch/workflow")
    result = {
        "kind": "aiflow-node-ci-attested-source",
        "schema_version": "1.0",
        "binding": binding,
        "attestation_head": selected_head,
        "static_declaration": blob(DECLARATION)[1],
        "engine_artifact": declaration["engine_artifact"],
        "source_evidence": {
            "original": blob(prefix + "evidence.json")[1],
            "canonical_sha256": final_sha,
        },
        "task": blob(prefix + "task.yaml")[1],
        "events": events_ref,
        "classification": blob(prefix + "classification.json")[1],
        "spec": spec_ref,
        "policy_members": policy_refs,
        "approvals": blob(prefix + "approvals.json")[1],
        "applicable_spec_approvals": applicable["spec"],
        "applicable_code_approvals": applicable["code"],
        "v2": v2,
    }
    return validate_node_ci_document(result), declaration, blobs


def _ci_input_materials(
    source_root: Path, payload_root: Path, source_tuple: Mapping[str, Any]
) -> dict[str, Any]:
    """Inventory provisioned ordinary inputs before any package proof process."""
    from aiflow import installed_mutations as installed
    from aiflow import node_execution as node

    budget = [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES]
    source = node._source(source_root, source_tuple["binding"]["subject_commit"], budget=budget)
    _package, lock = node._source_contract(source_root, source, revision=2)
    engine = node._engine(budget=budget)
    return {
        "source": source,
        "runtime": node._inventory(payload_root / "node", budget=budget),
        "dependencies": node._dependencies(
            payload_root / "dependencies/node_modules", lock, budget=budget, revision=2
        ),
        "engine": engine,
        "host_tools": node._host_tools(budget=budget),
        "pair_materials": _json(installed._materials())
        if source_tuple["binding"]["verification_level"] == "V2"
        else None,
        "engine_artifact": dict(source_tuple["engine_artifact"]),
        "python_provision": _python_provision(
            source_tuple, payload_root.parent / "artifact", engine
        ),
    }


def _python_provision(
    source_tuple: Mapping[str, Any], artifact_root: Path, engine: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind retained locked wheels and install originals without executing them.

    This is a content check, not source authentication. The producer separately
    compares the raw lock with the selected public head through the GH adapter.
    The same check opens only transported members during portable replay.
    """
    selection = source_tuple["engine_artifact"]

    def original(name: str, *, limit: int = MAX_FILE_BYTES) -> tuple[bytes, dict[str, Any]]:
        data = _read(artifact_root / _path(name), limit=limit)
        return data, {"ref": "artifact/" + name, "size": len(data), "sha256": _sha(data)}

    lock_raw, lock_ref = original("inputs/uv.lock", limit=MAX_JSON_BYTES)
    try:
        lock = tomllib.loads(lock_raw.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise _error("CI Python source lock is invalid") from error
    names = {
        "attrs",
        "jsonschema",
        "jsonschema-specifications",
        "pyyaml",
        "referencing",
        "rpds-py",
        "typing-extensions",
    }

    def normalized(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    packages = {}
    for row in _list(lock.get("package")):
        if isinstance(row, dict) and row.get("name") in names:
            if row["name"] in packages:
                raise _error("CI Python source lock repeats a runtime package")
            packages[row["name"]] = row
    if set(packages) != names:
        raise _error("CI Python source lock lacks the fixed runtime packages")
    requirements_raw, requirements_ref = original(
        "inputs/runtime-requirements.txt", limit=MAX_JSON_BYTES
    )
    requirements = {}
    try:
        for line in requirements_raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            match = re.fullmatch(r"([a-z0-9-]+)==([^\s]+) --hash=sha256:([0-9a-f]{64})", line)
            if match is None or match[1] in requirements:
                raise _error("CI Python runtime requirements are not closed exact hashes")
            requirements[match[1]] = (match[2], match[3])
    except UnicodeError as error:
        raise _error("CI Python runtime requirements are not UTF-8") from error
    if set(requirements) != names:
        raise _error("CI Python runtime requirements differ from the fixed seven packages")
    sites = engine["startup"]["python_environment"]["active_site_roots"]
    if not isinstance(sites, list) or len(sites) != 1:
        raise _error("CI Python runtime installation has no unique site root")
    site = Path(sites[0])
    distributions = {normalized(row["name"]): row for row in engine["distributions"]}
    if len(distributions) != len(engine["distributions"]):
        raise _error("CI installed Python distributions repeat normalized names")
    wheel_root = artifact_root / "inputs/wheels"
    _ordinary(wheel_root, directory=True)
    wheel_names = {path.name for path in wheel_root.iterdir()}
    wheels = []
    selected_names = set()
    for name in sorted(names):
        version, digest = requirements[name]
        package = packages[name]
        if version != package.get("version"):
            raise _error("CI Python requirement differs from selected source lock version")
        candidates = [
            row
            for row in _list(package.get("wheels"))
            if isinstance(row, dict) and row.get("hash") == "sha256:" + digest
        ]
        if len(candidates) != 1:
            raise _error("CI Python wheel hash is absent or ambiguous in selected source lock")
        locked_wheel = candidates[0]
        filename = _path(_text(locked_wheel.get("url"), limit=4096).rsplit("/", 1)[-1])
        if "/" in filename or not filename.endswith(".whl") or filename not in wheel_names:
            raise _error("CI retained Python wheel differs from selected lock filename")
        raw, reference = original("inputs/wheels/" + filename)
        if reference["sha256"] != digest or reference["size"] != _integer(
            locked_wheel.get("size"), maximum=MAX_FILE_BYTES
        ):
            raise _error("CI retained Python wheel differs from selected source lock bytes")
        selected_names.add(filename)
        distribution = distributions.get(name)
        if distribution is None or distribution["version"] != version:
            raise _error("CI installed Python dependency differs from selected source lock")
        installed_files = {row["path"]: row for row in distribution["files"]}
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as wheel:
                files = _zip_files(wheel, entries=MAX_ENTRIES, total=MAX_ROLE_BYTES)
                for member, info in files.items():
                    if member.endswith(".dist-info/RECORD"):
                        continue  # pip's actual installed RECORD remains in the engine role.
                    data = _zip_read(wheel, info)
                    installed = installed_files.get(str(site / member))
                    if (
                        installed is None
                        or installed["size"] != len(data)
                        or installed["sha256"] != _sha(data)
                    ):
                        raise _error(
                            "CI installed Python dependency differs from retained wheel payload"
                        )
        except zipfile.BadZipFile as error:
            raise _error("CI retained Python wheel archive is invalid") from error
        wheels.append({"name": name, "version": version, "wheel": reference})
    if selected_names != wheel_names:
        raise _error("CI Python wheelhouse has missing or extra members")
    prefix = Path(engine["startup"]["python_environment"]["prefix"])
    producing_artifact = prefix.parent / "artifact"
    commands = {
        "runtime-install": [
            str(prefix / "Scripts/python.exe"),
            "-I",
            "-B",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-cache-dir",
            "--find-links",
            str(producing_artifact / "inputs/wheels"),
            "--require-hashes",
            "-r",
            str(producing_artifact / "inputs/runtime-requirements.txt"),
        ],
        "engine-install": [
            str(prefix / "Scripts/python.exe"),
            "-I",
            "-B",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-cache-dir",
            "--no-deps",
            str(producing_artifact / selection["wheel"]["member"]),
        ],
    }
    provision = []
    for command, argv in commands.items():
        receipt_raw, receipt_ref = original(
            "provision/" + command + ".receipt.json", limit=MAX_JSON_BYTES
        )
        receipt = _json(receipt_raw)
        receipt = _obj(
            receipt,
            {
                "argv",
                "cleanup",
                "cwd",
                "duration_ms",
                "environment_sha256",
                "execution_error",
                "receipt",
                "returncode",
                "stderr_overflow",
                "stderr_sha256",
                "stderr_size",
                "stdout_overflow",
                "stdout_sha256",
                "stdout_size",
                "timed_out",
                "timeout_seconds",
            },
        )
        _digest(receipt["environment_sha256"])
        _integer(receipt["duration_ms"])
        _integer(receipt["timeout_seconds"], minimum=1, maximum=180)
        if not Path(_text(receipt["cwd"], limit=4096)).is_absolute():
            raise _error("CI Python install receipt has no absolute producing cwd")
        if (
            receipt.get("argv") != argv
            or type(receipt.get("returncode")) is not int
            or receipt["returncode"] != 0
            or receipt.get("cleanup") != "confirmed"
            or any(
                receipt.get(key) is not False
                for key in ("timed_out", "execution_error", "stdout_overflow", "stderr_overflow")
            )
        ):
            raise _error("CI Python provision does not bind the fixed successful install")
        _api_receipt(receipt.get("receipt"))
        provision.append(receipt_ref)
        for stream in ("stdout", "stderr"):
            data, reference = original(
                "provision/" + command + "." + stream + ".raw", limit=1024 * 1024
            )
            if (
                type(receipt.get(stream + "_size")) is not int
                or receipt[stream + "_size"] != len(data)
                or receipt.get(stream + "_sha256") != _sha(data)
            ):
                raise _error("CI Python provision stream differs from install receipt")
            provision.append(reference)
    return {
        "kind": "aiflow-node-ci-python-provision",
        "schema_version": "1.0",
        "source": {
            "repository_id": selection["source_repository_id"],
            "full_name": selection["source_full_name"],
            "head": selection["source_head"],
            "path": "uv.lock",
            "git_blob_sha": hashlib.sha1(
                b"blob " + str(len(lock_raw)).encode() + b"\0" + lock_raw
            ).hexdigest(),
            "raw": lock_ref,
        },
        "requirements": requirements_ref,
        "wheels": wheels,
        "provision": provision,
    }


def _check_shared_input_budget(inputs: Mapping[str, Any], engine_role: Mapping[str, Any]) -> None:
    """Recount the original five-domain budget from validated portable metadata.

    Match the existing local collectors, including their local path-based
    de-duplication. Imported coordinates are data and are never opened here.
    Git administration, copied executions and V2 pairs retain their own budgets.
    """
    from aiflow import node_execution as node

    budget = [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES]

    def take_file(row: Mapping[str, Any]) -> None:
        node._take_budget(budget, _integer(row["size"], maximum=MAX_FILE_BYTES))

    source_directories: set[str] = set()
    for row in _list(inputs["source"]["files"]):
        for parent in PurePosixPath(_path(row["path"])).parents:
            name = parent.as_posix()
            if name != "." and name not in source_directories:
                node._take_budget(budget)
                source_directories.add(name)
        take_file(row)
    for name in ("runtime", "dependencies"):
        inventory = _inventory(inputs[name])
        for row in inventory["entries"]:
            if row["kind"] == "file":
                take_file(row)
            else:
                node._take_budget(budget)
    engine = inputs["engine"]
    startup = engine["startup"]
    if startup["pyvenv_configuration"] is not None:
        take_file(startup["pyvenv_configuration"])
    for _root in _list(startup["site_roots"]):
        node._take_budget(budget)
    startup_files = {}
    for row in _list(startup["files"]):
        startup_path_text = _text(row["path"], limit=4096)
        if startup_path_text in startup_files:
            raise _error("CI engine startup has duplicate physical declarations")
        startup_files[startup_path_text] = row
        take_file(row)
    sites = _list(startup["python_environment"]["active_site_roots"])
    if len(sites) != 1:
        raise _error("CI installed engine has no unique ordinary site root")
    site = Path(_text(sites[0], limit=4096))
    engine_root = Path(engine_role["root"])
    directories = {engine_root} | {
        engine_root / row["path"] for row in engine_role["entries"] if row["kind"] == "directory"
    }
    for distribution in _list(engine["distributions"]):
        package_roots = set()
        for row in _list(distribution["files"]):
            path_text = _text(row["path"], limit=4096)
            if path_text in startup_files:
                if _canonical(row) != _canonical(startup_files[path_text]):
                    raise _error("CI engine startup/distribution originals conflict")
            else:
                take_file(row)
            path = Path(path_text)
            if path.is_relative_to(site):
                parts = path.relative_to(site).parts
                if parts and parts[0] not in {".", ".."} and site / parts[0] in directories:
                    package_roots.add(site / parts[0])
        for anchor in package_roots:
            node._take_budget(budget)
            for path in directories:
                if path != anchor and path.is_relative_to(anchor):
                    node._take_budget(budget)
    host_paths: dict[Path, Mapping[str, Any]] = {}
    for row in inputs["host_tools"].values():
        if row is None:
            continue
        path = Path(_text(row["path"], limit=4096))
        if path in host_paths:
            if _canonical(
                {key: value for key, value in row.items() if key != "path"}
            ) != _canonical(
                {key: value for key, value in host_paths[path].items() if key != "path"}
            ):
                raise _error("CI host aliases declare conflicting originals")
        else:
            take_file(row)
            host_paths[path] = row


def _attempt_coordinates(source_root: Path, attempt: Path, platform: Mapping[str, Any]) -> None:
    source_root, attempt = source_root.absolute(), attempt.absolute()
    workspace_text = os.environ.get("GITHUB_WORKSPACE")
    if not workspace_text:
        raise _error("CI workflow workspace is unavailable")
    workspace = Path(workspace_text).absolute()
    expected = workspace / ".tmp/node-ci" / f"{platform['run_id']}-{platform['run_attempt']}"
    if source_root != workspace / "source" or attempt != expected:
        raise _error("CI source/attempt coordinates differ from fixed workflow ownership")
    _ordinary(source_root, directory=True)
    _ordinary(attempt, directory=True)
    for key in ("TEMP", "TMP", "TMPDIR"):
        value = os.environ.get(key)
        if not value or not Path(value).absolute().is_relative_to(workspace / ".tmp"):
            raise _error("CI temporary environment leaves the owned workflow workspace")


def _role_roots(
    source_root: Path, attempt: Path, payload_root: Path, level: str
) -> dict[str, Path]:
    roots = {
        "source": source_root.absolute(),
        "artifact": attempt / "artifact",
        "engine": Path(sys.prefix).absolute(),
        "runtime": payload_root / "node",
        "dependencies": payload_root / "dependencies/node_modules",
        "host": attempt / "host",
        "preflight": attempt / "preflight",
        "control": attempt / "control",
        "node": attempt / "node",
    }
    if level == "V2":
        roots.update({role: attempt / role for role in role_ids(level)[9:]})
    for role, path in roots.items():
        _ordinary(path, directory=True)
        if role != "source" and (path == attempt or not path.is_relative_to(attempt)):
            raise _error("CI owned original role leaves this attempt")
    for left, left_path in roots.items():
        if any(
            left != right and (left_path == path or left_path.is_relative_to(path))
            for right, path in roots.items()
        ):
            raise _error("CI physical role originals overlap")
    return roots


def _portable_coordinates(manifests: Mapping[str, Any], admission: Mapping[str, Any]) -> None:
    source = Path(manifests["source"]["root"])
    if not source.is_absolute() or source.name != "source":
        raise _error("CI producing source has no fixed workspace role")
    attempt = (
        source.parent
        / ".tmp/node-ci"
        / f"{admission['platform']['run_id']}-{admission['platform']['run_attempt']}"
    )
    roots = {key: Path(value["root"]) for key, value in manifests.items()}
    for role, path in roots.items():
        if role != "source" and (
            not path.is_absolute() or path == attempt or not path.is_relative_to(attempt)
        ):
            raise _error("CI producing role belongs to another attempt")
        if role in {"control", "preflight", "node", "artifact", "host"} or role.startswith("pair-"):
            if path != attempt / role:
                raise _error("CI producing fixed role coordinates differ")
        if any(
            role != other and (path == candidate or path.is_relative_to(candidate))
            for other, candidate in roots.items()
        ):
            raise _error("CI producing original roles overlap")


def _transport_totals(
    manifests: Mapping[str, Any], index_bytes: bytes, *, level: str
) -> dict[str, int]:
    caps = _caps(level)
    if tuple(manifests) != role_ids(level):
        raise _error("CI transport role inventory differs from its tier")
    entries = 4 + 2 * len(manifests)
    original_bytes = manifest_bytes = 0
    for role, value in manifests.items():
        _inventory(value, role=True)
        if value["id"] != role:
            raise _error("CI role manifest identity differs")
        raw = _canonical(value)
        if len(raw) > MAX_JSON_BYTES:
            raise _error("CI role manifest is oversized", "NODE_CI_LIMIT_EXCEEDED")
        entries += len(value["entries"])
        original_bytes += value["total_bytes"]
        manifest_bytes += len(raw)
        if entries > caps[0] or original_bytes > caps[1] or manifest_bytes > caps[2]:
            raise _error(
                "CI physical originals exceed the registered tier", "NODE_CI_LIMIT_EXCEEDED"
            )
    if len(index_bytes) > caps[3] or len(index_bytes) > MAX_JSON_BYTES:
        raise _error("CI package index exceeds its registered tier", "NODE_CI_LIMIT_EXCEEDED")
    return {
        "entries": entries,
        "original_bytes": original_bytes,
        "manifest_bytes": manifest_bytes,
        "index_bytes": len(index_bytes),
    }


def _admit_known_ci_materials(
    source_root: Path,
    attempt: Path,
    payload_root: Path,
    inputs: Mapping[str, Any],
    control_files: Mapping[str, bytes],
    host_files: Mapping[str, bytes],
    *,
    level: str,
) -> dict[str, int]:
    """Reject known aggregate tier overflow before creating any claimed output.

    Existing roles use their complete physical inventories, including source
    Git administration and the whole interpreter prefix. Future control/host
    members use their actual bytes plus bounded metadata/envelopes, never a
    fabricated role manifest accepted as proof. Later incremental/final checks
    still cover the outputs that do not yet exist.
    """
    from aiflow import node_execution as node

    caps = _caps(level)
    roots = {
        "source": source_root,
        "artifact": attempt / "artifact",
        "engine": Path(sys.prefix).absolute(),
        "runtime": payload_root / "node",
        "dependencies": payload_root / "dependencies/node_modules",
        **{role: attempt / role for role in role_ids(level)[5:]},
    }
    inventories = {
        "source": node._inventory(source_root),
        "artifact": node._inventory(roots["artifact"]),
        "engine": node._inventory(roots["engine"]),
        "runtime": inputs["runtime"],
        "dependencies": inputs["dependencies"],
    }
    _check_shared_input_budget(inputs, inventories["engine"])
    entries = 4 + 2 * len(roots)
    original_bytes = manifest_bytes = 0
    names = ["originals/", "manifests/", "index.json"]
    # Every admissible identity integer is bounded by the existing closed model.
    identity_bytes = len(_canonical({key: (1 << 63) - 1 for key in _IDENTITY_FIELDS}))
    for role, root in roots.items():
        names.extend(("originals/" + role + "/", "manifests/" + role + ".json"))
        if role in inventories:
            inventory = inventories[role]
            _inventory(inventory)
            role_bytes = inventory["total_bytes"]
            members = {row["path"]: row.get("size", 0) for row in inventory["entries"]}
            raw_size = len(_canonical({"id": role, **inventory}))
            directories = {
                row["path"] for row in inventory["entries"] if row["kind"] == "directory"
            }
        else:
            files = control_files if role == "control" else host_files if role == "host" else {}
            members = {}
            directories = set()
            for name, data in files.items():
                _integer(len(data), maximum=MAX_JSON_BYTES if role == "control" else MAX_FILE_BYTES)
                node._ci_reserve_member(members, _path(name), len(data))
                directories.update(
                    parent.as_posix()
                    for parent in PurePosixPath(name).parents
                    if parent.as_posix() != "."
                )
            if directories.intersection(files) or len({name.casefold() for name in members}) != len(
                members
            ):
                raise _error("CI planned originals have aliased or conflicting paths")
            role_bytes = sum(members.values())
            # Size-only canonical metadata envelope; no identities or manifests
            # are synthesized, written or presented to any proof reader.
            raw_size = len(_canonical({"id": role, "root": str(root), "total_bytes": role_bytes}))
            raw_size += len('"identity":,"entries":[]') + identity_bytes + 1
            for name, size in members.items():
                row: dict[str, Any] = {
                    "path": name,
                    "kind": "directory" if name in directories else "file",
                }
                if name not in directories:
                    row.update(size=size, sha256="0" * 64)
                raw_size += len(_canonical(row)) + len('"identity":') + identity_bytes + 2
        if len(members) > MAX_ENTRIES or role_bytes > MAX_ROLE_BYTES or raw_size > MAX_JSON_BYTES:
            raise _error("CI known role exceeds its original bound", "NODE_CI_LIMIT_EXCEEDED")
        entries += len(members)
        original_bytes += role_bytes
        manifest_bytes += raw_size
        names.extend(
            "originals/" + role + "/" + name + ("/" if name in directories else "")
            for name in members
        )

    # Fixed outer index fields and every tier role are counted even before their
    # future Ref sizes are known. The ordinary JSON bound limits those sizes.
    def envelope_ref(name: str) -> dict[str, Any]:
        return {"ref": name, "size": MAX_JSON_BYTES, "sha256": "0" * 64}

    index_bytes = len(
        _canonical(
            {
                "kind": "aiflow-node-ci-originals",
                "schema_version": "1.0",
                "evidence": envelope_ref("control/evidence.json"),
                "descriptor": envelope_ref("control/descriptor.json"),
                "source_tuple": envelope_ref("control/source-tuple.json"),
                "roles": [
                    {"id": role, "manifest": envelope_ref("manifests/" + role + ".json")}
                    for role in roots
                ],
            }
        )
    )
    archive_bytes = 1024 + original_bytes + manifest_bytes + index_bytes
    archive_bytes += sum(2 * len(name.encode("utf-8")) + 256 for name in names)
    totals = (entries, original_bytes, manifest_bytes, index_bytes, archive_bytes)
    if (
        any(value > bound for value, bound in zip(totals, caps, strict=True))
        or index_bytes > MAX_JSON_BYTES
    ):
        raise _error("CI known originals exceed the registered tier", "NODE_CI_LIMIT_EXCEEDED")
    return dict(
        zip(
            ("entries", "original_bytes", "manifest_bytes", "index_bytes", "archive_bytes"),
            totals,
            strict=True,
        )
    )


def _write_package(
    attempt: Path,
    roots: Mapping[str, Path],
    *,
    level: str,
    source_tuple: Mapping[str, Any],
    prepared: Mapping[str, Any],
    run: Mapping[str, Any],
) -> tuple[Path, dict[str, Any]]:
    from aiflow import node_execution as node

    _caps(level)
    package = attempt / "package"
    if package.exists():
        raise _error("CI package output is already spent")
    manifests = {role: {"id": role, **node._inventory(path)} for role, path in roots.items()}
    _transport_totals(manifests, b"{}", level=level)
    _portable_coordinates(
        manifests, _json(_read(attempt / "control/admission.json", limit=MAX_JSON_BYTES))
    )
    package.mkdir()
    (package / "originals").mkdir()
    (package / "manifests").mkdir()
    for role, manifest in manifests.items():
        inventory = {key: value for key, value in manifest.items() if key != "id"}
        node._copy_tree(roots[role], package / "originals" / role, inventory)
        node._unchanged(inventory)
    facts = node.replay_ci_node(
        package_root=package, prepared=prepared, run=run, role_manifests=manifests
    )
    if not facts["checks"] or facts["node_binding"] is None:
        raise _error(
            "CI proof cannot be replayed from retained complete originals",
            "NODE_CI_ORIGINALS_INVALID",
        )
    evidence = {
        "schema_version": "3.3",
        "kind": "aiflow-node-ci-evidence",
        "mode": "ci",
        "binding": dict(source_tuple["binding"]),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "conclusion": "passed" if facts["passed"] else "failed",
        "source_binding_kind": "attested_committed_tuple",
        "source_tuple": _file_ref(attempt / "control/source-tuple.json", attempt),
        "descriptor": _file_ref(attempt / "control/descriptor.json", attempt),
        "platform": dict(prepared["platform"]),
        "prepared": _file_ref(attempt / "control/prepared.json", attempt),
        "run": _file_ref(attempt / "node/run.json", attempt),
        "checks": facts["checks"],
        "node_binding": facts["node_binding"],
        "installed_mutation": run["installed_mutation"],
        "reproduce_command": [
            "python",
            "-I",
            "-B",
            "-m",
            "aiflow",
            "verify",
            source_tuple["binding"]["task_id"],
            "--ci",
            "--node-ci",
            "--ci-run-dir",
            "<new-attempt>",
            "--output",
            "<new-attempt>/evidence.json",
            "--node-ci-payload",
            "<new-provisioned-payload>",
        ],
        "known_limitations": [
            "Original-host LOCAL originals and the unchanged live Gate are required "
            "for combined readiness.",
            "CI source binding attests committed metadata; it does not supply LOCAL Current.",
        ],
    }
    validate_node_ci_document(evidence)
    raw_evidence = _canonical(evidence)
    caps = _caps(level)
    prior = _transport_totals(manifests, b"{}", level=level)
    if (
        prior["entries"] + 1 > caps[0]
        or prior["original_bytes"] + len(raw_evidence) > caps[1]
        or prior["manifest_bytes"] + 4096 > caps[2]
    ):
        raise _error(
            "CI completed evidence exceeds its registered package reserve", "NODE_CI_LIMIT_EXCEEDED"
        )
    _write_new(attempt / "control/evidence.json", raw_evidence)
    _write_new(package / "originals/control/evidence.json", raw_evidence)
    manifests["control"] = {"id": "control", **node._inventory(attempt / "control")}
    index: dict[str, Any] = {
        "kind": "aiflow-node-ci-originals",
        "schema_version": "1.0",
        **{
            key: _file_ref(attempt / "control" / filename, attempt)
            for key, filename in (
                ("evidence", "evidence.json"),
                ("descriptor", "descriptor.json"),
                ("source_tuple", "source-tuple.json"),
            )
        },
        "roles": [],
    }
    for role, manifest in manifests.items():
        raw = _canonical(manifest)
        index["roles"].append(
            {
                "id": role,
                "manifest": {
                    "ref": "manifests/" + role + ".json",
                    "size": len(raw),
                    "sha256": _sha(raw),
                },
            }
        )
    validate_node_ci_document(index)
    totals = _transport_totals(manifests, _canonical(index), level=level)
    for role, manifest in manifests.items():
        _write_new(package / "manifests" / (role + ".json"), _canonical(manifest))
    _write_new(package / "index.json", _canonical(index))
    return package, totals


def _package_manifests(package: Path, *, level: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bound every retained member before delegating pure content replay."""
    caps = _caps(level)
    index_bytes = _read(package / "index.json", limit=min(MAX_JSON_BYTES, caps[3]))
    index = validate_node_ci_document(_json(index_bytes), kind="aiflow-node-ci-originals")
    if index_bytes != _canonical(index):
        raise _error("CI index is not its canonical closed original")
    if tuple(row["id"] for row in index["roles"]) != role_ids(level):
        raise _error("CI outer index mixes tier roles")
    manifests = {}
    expected_files = {"index.json"}
    expected_dirs = {"originals", "manifests"}
    for item in index["roles"]:
        role = item["id"]
        if item["manifest"]["ref"] != "manifests/" + role + ".json":
            raise _error("CI role manifest reference differs")
        value = _ref_document(package, item["manifest"], "role-manifest")
        if _read(_resolve_ref(package, item["manifest"]), limit=MAX_JSON_BYTES) != _canonical(
            value
        ):
            raise _error("CI role manifest is not its canonical closed original")
        if value["id"] != role:
            raise _error("CI role manifest selects another role")
        manifests[role] = value
        expected_files.add(item["manifest"]["ref"])
        expected_dirs.add("originals/" + role)
        for row in value["entries"]:
            (expected_files if row["kind"] == "file" else expected_dirs).add(
                "originals/" + role + "/" + row["path"]
            )
    _transport_totals(manifests, index_bytes, level=level)
    actual_files: set[str] = set()
    actual_dirs: set[str] = set()
    total = count = 0
    pending = [package]
    while pending:
        directory = pending.pop()
        _ordinary(directory, directory=True)
        for path in directory.iterdir():
            count += 1
            if count + 1 > caps[0]:
                raise _error("CI package has excessive physical entries", "NODE_CI_LIMIT_EXCEEDED")
            relative = _path(path.relative_to(package).as_posix())
            info = _ordinary(path)
            if stat.S_ISDIR(info.st_mode):
                actual_dirs.add(relative)
                pending.append(path)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                actual_files.add(relative)
                total += info.st_size
                if info.st_size > MAX_FILE_BYTES or total > caps[1] + caps[2] + caps[3]:
                    raise _error(
                        "CI expanded package exceeds its registered tier", "NODE_CI_LIMIT_EXCEEDED"
                    )
            else:
                raise _error("CI package contains a nonordinary member")
    if actual_files != expected_files or actual_dirs != expected_dirs:
        raise _error("CI package physical membership differs from complete originals")
    for role, manifest in manifests.items():
        for row in manifest["entries"]:
            if row["kind"] == "file":
                data = _read(package / "originals" / role / row["path"])
                if len(data) != row["size"] or _sha(data) != row["sha256"]:
                    raise _error("CI transported original bytes differ from role manifest")
    return index, manifests


def validate_ci_originals(
    package_root: Path, descriptor: Mapping[str, Any], source_tuple: Mapping[str, Any]
) -> dict[str, Any]:
    """Content validity only; neither GitHub authentication nor LOCAL Current."""
    from aiflow.node_execution import replay_ci_node

    validate_node_ci_document(dict(descriptor), kind="aiflow-node-ci-descriptor")
    validate_node_ci_document(dict(source_tuple), kind="aiflow-node-ci-attested-source")
    level = source_tuple["binding"]["verification_level"]
    index, manifests = _package_manifests(package_root, level=level)
    _validate_api_observations(package_root / "originals")
    if (
        _ref_document(package_root, index["descriptor"]) != descriptor
        or _ref_document(package_root, index["source_tuple"]) != source_tuple
    ):
        raise _error("CI outer package binds another source tuple")
    evidence = _ref_document(package_root, index["evidence"], "aiflow-node-ci-evidence")
    prepared = _ref_document(package_root, evidence["prepared"], "aiflow-node-ci-prepared-3.3")
    run = _ref_document(package_root, evidence["run"], "aiflow-node-ci-run-3.3")
    admission = _ref_document(package_root, prepared["admission"], "aiflow-node-ci-admission")
    _portable_coordinates(manifests, admission)
    inputs = _json(
        _read(package_root / "originals/control/input-materials.json", limit=MAX_JSON_BYTES)
    )
    _obj(
        inputs,
        {
            "source",
            "runtime",
            "dependencies",
            "engine",
            "host_tools",
            "pair_materials",
            "engine_artifact",
            "python_provision",
        },
    )
    expected_host = {key: value for key, value in inputs["host_tools"].items() if value is not None}
    expected_host["gh"] = {"sha256": GH_EXE_SHA256}
    if level == "V2":
        expected_host.update(
            {
                "python_" + key: inputs["pair_materials"]["interpreter"][key]
                for key in ("base_executable", "runtime")
            }
        )
    if {row["path"] for row in manifests["host"]["entries"]} != set(expected_host) or any(
        row["kind"] != "file" for row in manifests["host"]["entries"]
    ):
        raise _error("CI retained host role omits or adds declared tool originals")
    for slot, row in expected_host.items():
        data = _read(package_root / "originals/host" / slot)
        if _sha(data) != row["sha256"] or ("size" in row and len(data) != row["size"]):
            raise _error("CI retained host/client/interpreter bytes differ from declared inputs")
    if (
        index["evidence"]["ref"] != "control/evidence.json"
        or evidence["run"]["ref"] != "node/run.json"
        or evidence["prepared"]["ref"] != "control/prepared.json"
        or index["descriptor"] != evidence["descriptor"]
        or index["source_tuple"] != evidence["source_tuple"]
        or evidence["binding"] != source_tuple["binding"]
        or evidence["platform"] != admission["platform"]
    ):
        raise _error("CI public/control evidence selections differ")
    facts = replay_ci_node(
        package_root=package_root, prepared=prepared, run=run, role_manifests=manifests
    )
    _check_shared_input_budget(inputs, manifests["engine"])
    if (
        facts["checks"] != evidence["checks"]
        or facts["node_binding"] != evidence["node_binding"]
        or evidence["installed_mutation"] != run["installed_mutation"]
        or evidence["conclusion"] != ("passed" if facts["passed"] else "failed")
    ):
        raise _error("CI public evidence differs from pure original replay")
    if (
        descriptor["static_declaration_sha256"] != source_tuple["static_declaration"]["sha256"]
        or descriptor["source_tuple_sha256"] != _sha(_canonical(source_tuple))
        or descriptor["engine_artifact_sha256"] != _sha(_canonical(source_tuple["engine_artifact"]))
        or descriptor["execution_contract_sha256"]
        != _sha(_canonical(node_ci_execution_contract(level)))
    ):
        raise _error("CI descriptor does not bind its closed execution inputs")
    return {
        "passed": facts["passed"],
        "reason_codes": facts["reason_codes"],
        "evidence": evidence,
        "admission": admission,
        "role_manifests": manifests,
    }


def _hash_file(path: Path, *, limit: int) -> str:
    before = _ordinary(path, directory=False)
    if before.st_size > limit:
        raise _error(
            "CI download exceeds the registered compressed bound", "NODE_CI_LIMIT_EXCEEDED"
        )
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise _error("CI download changed while opening")
        while data := stream.read(1024 * 1024):
            count += len(data)
            if count > limit:
                raise _error("CI download exceeds its actual byte bound", "NODE_CI_LIMIT_EXCEEDED")
            digest.update(data)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    if count != before.st_size or any(
        getattr(item, key) != getattr(before, key)
        for item in (after, current)
        for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
    ):
        raise _error("CI download changed during bounded hashing")
    return digest.hexdigest()


def _download_artifact(
    platform: Mapping[str, Any],
    *,
    name: str,
    destination: Path,
    level: str,
    _capture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stream the authenticated ZIP through the existing bounded Windows Job runner."""
    from aiflow.process_runner import run_node_process

    caps = _caps(level)
    metadata = (
        _select_artifact(platform, name=name)
        if _capture is None
        else _select_artifact(platform, name=name, _capture=_capture)
    )
    limit = caps[4]
    if metadata["size_in_bytes"] > limit:
        raise _error("GitHub artifact exceeds its registered tier", "NODE_CI_LIMIT_EXCEEDED")
    destination = destination.absolute()
    _ordinary(destination.parent, directory=True)
    executable = _gh_executable()
    endpoint = f"repos/{platform['full_name']}/actions/artifacts/{metadata['id']}/zip"
    with destination.open("xb") as stream:
        result = run_node_process(
            (
                str(executable),
                "api",
                "--hostname",
                "github.com",
                "--method",
                "GET",
                "--header",
                "Accept: application/vnd.github+json",
                endpoint,
            ),
            cwd=destination.parent,
            environment=_gh_environment(),
            timeout_seconds=300,
            stdout_sink=stream,
            stdout_limit=limit,
        )
    if (
        result.returncode != 0
        or result.timed_out
        or result.stdout_overflow
        or result.stderr_overflow
        or result.cleanup != "confirmed"
        or result.execution_error
    ):
        raise _error(
            "GitHub artifact stream did not complete safely; partial originals retained",
            "NODE_CI_PLATFORM_UNVERIFIED",
        )
    if _hash_file(destination, limit=limit) != _provider_digest(metadata["digest"]):
        raise _error("Downloaded artifact differs from authenticated provider digest")
    return metadata


def _extract_package(archive_path: Path, destination: Path, *, level: str) -> Path:
    """Admit every ZIP/member/manifest bound before creating extraction outputs.

    Actions transports exact file originals. Directory headers are optional in
    that representation: only closed manifest-declared directories are recreated,
    after all hashes, role membership and aggregate budgets have been admitted.
    Missing files and unknown explicit directory headers always reject.
    """
    caps = _caps(level)
    _ordinary(archive_path, directory=False)
    if archive_path.stat().st_size > caps[4]:
        raise _error("CI ZIP exceeds compressed tier cap", "NODE_CI_LIMIT_EXCEEDED")
    _ordinary(destination.parent, directory=True)
    if destination.exists():
        raise _error("CI extraction destination is already spent")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            files = _zip_files(archive, entries=caps[0], total=caps[1] + caps[2] + caps[3])
            if "index.json" not in files:
                raise _error("CI ZIP has no closed package index")
            raw_index = _zip_read(archive, files["index.json"], limit=min(MAX_JSON_BYTES, caps[3]))
            index = validate_node_ci_document(_json(raw_index), kind="aiflow-node-ci-originals")
            if raw_index != _canonical(index) or tuple(
                item["id"] for item in index["roles"]
            ) != role_ids(level):
                raise _error("CI ZIP index encoding/tier differs")
            manifests = {}
            expected_files = {"index.json"}
            expected_dirs = {"originals", "manifests"}
            for item in index["roles"]:
                role = item["id"]
                ref = item["manifest"]
                name = "manifests/" + role + ".json"
                if ref["ref"] != name or name not in files:
                    raise _error("CI ZIP omits its fixed role manifest")
                data = _zip_read(archive, files[name], limit=MAX_JSON_BYTES)
                if len(data) != ref["size"] or _sha(data) != ref["sha256"]:
                    raise _error("CI ZIP manifest differs from index reference")
                value = validate_node_ci_document(_json(data), kind="role-manifest")
                if value["id"] != role or _canonical(value) != data:
                    raise _error("CI ZIP role manifest encoding/identity differs")
                manifests[role] = value
                expected_files.add(name)
                expected_dirs.add("originals/" + role)
                for row in value["entries"]:
                    path = "originals/" + role + "/" + row["path"]
                    (expected_files if row["kind"] == "file" else expected_dirs).add(path)
            _transport_totals(manifests, raw_index, level=level)
            if set(files) != expected_files:
                raise _error("CI ZIP omits or adds a physical file original")
            if any(
                info.filename.rstrip("/") not in expected_dirs
                for info in archive.infolist()
                if info.is_dir()
            ):
                raise _error("CI ZIP has an undeclared explicit directory")
            if any(
                parent.as_posix() not in expected_dirs
                for name in expected_files | expected_dirs
                for parent in PurePosixPath(name).parents
                if parent.as_posix() != "."
            ):
                raise _error("CI role manifests omit a parent directory")
            for role, manifest in manifests.items():
                for row in manifest["entries"]:
                    if row["kind"] == "file":
                        info = files["originals/" + role + "/" + row["path"]]
                        if (
                            info.file_size != row["size"]
                            or _sha(_zip_read(archive, info)) != row["sha256"]
                        ):
                            raise _error("CI ZIP original bytes differ from its role manifest")
            destination.mkdir()
            for name in sorted(expected_dirs, key=lambda value: (value.count("/"), value.encode())):
                (destination / name).mkdir()
            for name in sorted(expected_files, key=lambda value: value.encode()):
                _write_new(destination / name, _zip_read(archive, files[name]))
    except (zipfile.BadZipFile, OSError, ValueError, KeyError) as error:
        raise _error("CI ZIP is invalid; retained originals were not repaired") from error
    _package_manifests(destination, level=level)
    return destination


def write_ci_archive(package_root: Path, destination: Path, *, level: str) -> dict[str, Any]:
    """Measure a complete bounded ZIP before platform upload; retain all directories."""
    caps = _caps(level)
    _index, _manifests = _package_manifests(package_root, level=level)
    members = sorted(
        package_root.rglob("*"), key=lambda path: path.relative_to(package_root).as_posix().encode()
    )
    # Stored ZIP needs no compressor allocation. This includes conservative
    # UTF-8/local/central/Zip64 envelope space before opening the output file.
    maximum = 1024
    for path in members:
        info = _ordinary(path)
        name = path.relative_to(package_root).as_posix() + ("/" if path.is_dir() else "")
        maximum += (
            (info.st_size if stat.S_ISREG(info.st_mode) else 0)
            + 2 * len(name.encode("utf-8"))
            + 256
        )
        if maximum > caps[4]:
            raise _error(
                "Complete CI ZIP exceeds its registered compressed reserve",
                "NODE_CI_LIMIT_EXCEEDED",
            )
    _ordinary(destination.parent, directory=True)
    with (
        destination.open("xb") as stream,
        zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive,
    ):
        for path in members:
            name = path.relative_to(package_root).as_posix()
            if path.is_dir():
                archive.writestr(name + "/", b"")
            else:
                archive.writestr(name, _read(path))
            if stream.tell() > caps[4]:
                raise _error(
                    "Actual CI ZIP exceeds its registered compressed cap", "NODE_CI_LIMIT_EXCEEDED"
                )
    digest = _hash_file(destination, limit=caps[4])
    _package_manifests(package_root, level=level)
    return {"size": destination.stat().st_size, "sha256": digest, "entries": len(members)}


def _authenticate_engine(
    selection: Mapping[str, Any], *, _capture: dict[str, Any] | None = None
) -> dict[str, Any]:
    chosen = _artifact(dict(selection))
    platform = authenticate_workflow(
        SOURCE_REPOSITORY_ID,
        SOURCE_REPOSITORY,
        SOURCE_WORKFLOW,
        SOURCE_JOB,
        run_id=chosen["run_id"],
        attempt=chosen["run_attempt"],
        completed=True,
        _capture=_capture,
    )
    if any(
        platform[key] != chosen[other]
        for key, other in (
            ("workflow_id", "workflow_id"),
            ("workflow_path", "workflow_path"),
            ("workflow_ref", "workflow_ref"),
            ("workflow_sha256", "workflow_sha256"),
            ("head_sha", "source_head"),
            ("job_id", "job_id"),
        )
    ):
        raise _error("Selected source engine has another authenticated producer")
    artifact = (
        _select_artifact(platform, name=chosen["artifact_name"])
        if _capture is None
        else _select_artifact(platform, name=chosen["artifact_name"], _capture=_capture)
    )
    if artifact["id"] != chosen["artifact_id"] or artifact["digest"] != chosen["artifact_digest"]:
        raise _error("Selected source engine differs from live artifact identity")
    return platform


def _installed_wheel_binding(
    archive_path: Path,
    selection: Mapping[str, Any],
    inputs: Mapping[str, Any],
    contract_sha: str,
    *,
    package_root: Path | None = None,
) -> str:
    """Bind exact selected wheel payload to the actual ordinary installed files."""
    facts = validate_engine_artifact_archive(archive_path, selection)
    with zipfile.ZipFile(archive_path) as archive:
        wheel_data = _zip_read(archive, archive.getinfo(selection["wheel"]["member"]))
    installed = inputs["engine"]
    distribution = installed["distributions"][0]
    if distribution["name"].lower() != "aiflow" or distribution["version"] != "0.2.0":
        raise _error("CI imported distribution is not the selected ordinary engine")
    sites = installed["startup"]["python_environment"]["active_site_roots"]
    if not isinstance(sites, list) or len(sites) != 1:
        raise _error("CI installed engine has no unique ordinary site root")
    site = Path(sites[0])
    rows = {row["path"]: row for row in distribution["files"]}
    chosen_wheel = archive_path.parent / selection["wheel"]["member"]
    if _read(chosen_wheel) != wheel_data:
        raise _error("Actual local installation wheel differs from selected artifact member")
    direct_name = site / "aiflow-0.2.0.dist-info/direct_url.json"
    direct_path = direct_name
    if package_root is not None:
        prefix = Path(installed["startup"]["python_environment"]["prefix"])
        if not direct_name.is_relative_to(prefix):
            raise _error("Producing installation provenance leaves ordinary engine prefix")
        direct_path = package_root / "originals/engine" / direct_name.relative_to(prefix)
    direct_raw = _read(direct_path, limit=MAX_JSON_BYTES)
    direct_row = rows.get(str(direct_name))
    if (
        direct_row is None
        or direct_row["sha256"] != _sha(direct_raw)
        or direct_row["size"] != len(direct_raw)
    ):
        raise _error("Installed wheel provenance differs from original installed inventory")
    direct = _json(direct_raw)
    if (
        not isinstance(direct, dict)
        or direct.get("archive_info", {}).get("hashes", {}).get("sha256")
        != selection["wheel"]["sha256"]
    ):
        raise _error("Ordinary installation provenance does not bind selected raw wheel")
    with zipfile.ZipFile(io.BytesIO(wheel_data)) as wheel:
        for name, info in _zip_files(wheel, entries=MAX_ENTRIES, total=MAX_ROLE_BYTES).items():
            if name == "aiflow-0.2.0.dist-info/RECORD":
                continue  # pip's installation RECORD is separately retained unchanged.
            row = rows.get(str(site / name))
            data = _zip_read(wheel, info)
            if row is None or row["size"] != len(data) or row["sha256"] != _sha(data):
                raise _error("Installed engine bytes differ from selected wheel originals")
    return _sha(
        _canonical(
            {
                "wheel_sha256": selection["wheel"]["sha256"],
                "package_payload_sha256": facts["package_payload_sha256"],
                "resource_manifest_sha256": facts["resource_manifest_sha256"],
                "execution_contract_sha256": contract_sha,
            }
        )
    )


def _descriptor(source_tuple: Mapping[str, Any], declaration: Mapping[str, Any]) -> dict[str, Any]:
    level = source_tuple["binding"]["verification_level"]
    contract_sha = _sha(_canonical(node_ci_execution_contract(level)))
    if declaration["tier_contracts"][level] != contract_sha:
        raise _error("CI declaration does not select this installed cap-bearing execution contract")
    return validate_node_ci_document(
        {
            "kind": "aiflow-node-ci-descriptor",
            "schema_version": "1.0",
            "source_tuple_sha256": _sha(_canonical(source_tuple)),
            "static_declaration_sha256": source_tuple["static_declaration"]["sha256"],
            "engine_artifact_sha256": _sha(_canonical(source_tuple["engine_artifact"])),
            "execution_contract_sha256": contract_sha,
            "verification_level": level,
            "attestation_head": source_tuple["attestation_head"],
        }
    )


def _current_local_engine() -> dict[str, Any]:
    """Read the actual ordinary installation on this original host."""
    from aiflow.node_execution import _engine

    return _engine()


def _local_wheel_binding(
    archive_path: Path, selection: Mapping[str, Any], contract_sha: str
) -> dict[str, str]:
    """Use authenticated raw references to bind this host's current installation.

    The archive may be transported; it supplies raw selected bytes only. The
    engine inventory and installation provenance are always read on this host,
    without resolving any installed path from the imported CI input document.
    """
    engine = _current_local_engine()
    content = _installed_wheel_binding(archive_path, selection, {"engine": engine}, contract_sha)
    return {"engine_sha256": _sha(_canonical(engine)), "engine_content_sha256": content}


def _source_identity(source_tuple: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "binding": source_tuple["binding"],
        "declaration": source_tuple["static_declaration"],
        "engine_artifact": source_tuple["engine_artifact"],
        "final_sha256": source_tuple["source_evidence"]["canonical_sha256"],
        "v2_snapshot": source_tuple["v2"]["snapshot_sha256"]
        if source_tuple["v2"] is not None
        else None,
    }


def _reject_source_git_authentication(source_root: Path) -> None:
    """Inspect actual local Git keys without following configuration includes."""
    from urllib.parse import urlsplit

    from aiflow.node_execution import _git

    _read(source_root / ".git/config", limit=MAX_JSON_BYTES)
    raw = _git(source_root, "config", "--null", "--local", "--list", "--no-includes")
    if len(raw) > MAX_JSON_BYTES:
        raise _error("CI source Git configuration exceeds its limit", "NODE_CI_LIMIT_EXCEEDED")
    if raw and not raw.endswith(b"\0"):
        raise _error("CI source Git configuration is malformed")

    def reject() -> None:
        raise _error("CI source administration contains persisted authentication")

    def check_url(value: str, *, proxy: bool = False) -> None:
        try:
            candidate = value.strip() if proxy else value
            if proxy and "://" not in candidate and not candidate.startswith("//"):
                candidate = "//" + candidate
            parsed = urlsplit(candidate)
            if (
                parsed.password is not None
                or (proxy and parsed.username is not None)
                or (
                    parsed.scheme.casefold() in {"http", "https"}
                    and (not parsed.netloc or parsed.username is not None)
                )
            ):
                reject()
        except ValueError:
            raise _error("CI source administration contains persisted authentication") from None

    for entry in raw.split(b"\0")[:-1]:
        key_bytes, _separator, value_bytes = entry.partition(b"\n")
        try:
            key, value = key_bytes.decode("utf-8"), value_bytes.decode("utf-8")
        except UnicodeError:
            raise _error("CI source Git configuration is not valid UTF-8") from None
        folded = key.casefold()
        variable = folded.rsplit(".", 1)[-1]
        if (
            folded.startswith(("include.", "includeif.", "credential."))
            or folded == "extensions.worktreeconfig"
        ):
            reject()
        if folded.startswith("http.") and variable in {
            "extraheader",
            "authorization",
            "proxyauthorization",
        }:
            reject()
        if folded.startswith("remote.") and variable in {"url", "pushurl", "proxy"}:
            check_url(value, proxy=variable == "proxy")
        if folded.startswith("url.") and variable in {"insteadof", "pushinsteadof"}:
            check_url(key[4 : -(len(variable) + 1)])
        if folded.startswith("http."):
            if variable == "proxy":
                check_url(value, proxy=True)
            if key.rsplit(".", 1)[0].casefold() != "http":
                check_url(key[5 : -(len(variable) + 1)])


def verify_node_ci(
    source_root: Path, task_id: str, *, run_dir: Path, output: Path, payload_root: Path
) -> dict[str, Any]:
    """Produce complete fresh CI originals without touching source task authority."""
    from aiflow import installed_mutations as installed
    from aiflow import node_execution as node

    # No claim, recovery marker, directory or proof process may precede admission.
    _caps("V0")
    api_capture = _new_api_capture()
    if os.name != "nt" or not sys.dont_write_bytecode:
        raise _error("Node CI requires the ordinary Windows x64 engine with -B")
    source_root, attempt = source_root.absolute(), run_dir.absolute()
    payload_root, output = payload_root.absolute(), output.absolute()
    if output != attempt / "evidence.json" or output.exists():
        raise _error("CI output must be the fresh fixed attempt/evidence.json")
    source_tuple, declaration, blobs = _build_source_authority(source_root, task_id)
    level = source_tuple["binding"]["verification_level"]
    _caps(level)
    descriptor = _descriptor(source_tuple, declaration)
    repository = declaration["repository"]
    try:
        run_id = int(os.environ["GITHUB_RUN_ID"])
        run_attempt = int(os.environ["GITHUB_RUN_ATTEMPT"])
    except (ValueError, KeyError) as error:
        raise _error("CI authenticated attempt selectors are unavailable") from error
    platform = authenticate_workflow(
        repository["provider_repository_id"],
        repository["full_name"],
        TARGET_WORKFLOW,
        TARGET_JOB,
        run_id=run_id,
        attempt=run_attempt,
        completed=False,
        _capture=api_capture,
    )
    _attempt_coordinates(source_root, attempt, platform)
    if (
        platform["head_sha"] != source_tuple["attestation_head"]
        or platform["workflow_sha256"] != declaration["workflow"]["sha256"]
    ):
        raise _error("CI authenticated producer differs from attested source/workflow")
    if payload_root != attempt / "payload" or Path(sys.prefix).absolute() != attempt / "engine":
        raise _error("CI provisioned runtime/engine are outside fixed attempt roles")
    if {path.name for path in attempt.iterdir()} != {"artifact", "engine", "payload"}:
        raise _error("CI attempt has unknown or previously spent neighbors")
    _reject_source_git_authentication(source_root)
    _authenticate_engine(source_tuple["engine_artifact"], _capture=api_capture)
    source_archive = attempt / "artifact/engine-source.zip"
    selection = source_tuple["engine_artifact"]
    trusted_lock = _github_file(
        selection["source_full_name"], "uv.lock", selection["source_head"], _capture=api_capture
    )
    if _read(attempt / "artifact/inputs/uv.lock", limit=MAX_JSON_BYTES) != trusted_lock:
        raise _error("CI provisioned Python lock differs from trusted selected source blob")
    inputs = _ci_input_materials(source_root, payload_root, source_tuple)
    engine_content = _installed_wheel_binding(
        source_archive,
        source_tuple["engine_artifact"],
        inputs,
        descriptor["execution_contract_sha256"],
    )
    admission = validate_node_ci_document(
        {
            "kind": "aiflow-node-ci-admission",
            "schema_version": "1.0",
            "descriptor_sha256": _sha(_canonical(descriptor)),
            "platform": platform,
            "input_materials_sha256": _sha(_canonical(inputs)),
            "engine_content_sha256": engine_content,
            "claimed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    control_files = {name.removeprefix("control/"): data for name, data in blobs.items()}
    control_files.update(
        {
            "descriptor.json": _canonical(descriptor),
            "source-tuple.json": _canonical(source_tuple),
            "input-materials.json": _canonical(inputs),
            "admission.json": _canonical(admission),
            "provision.json": _canonical(inputs["python_provision"]),
            "provision/uv.lock": trusted_lock,
        }
    )
    if level == "V2":
        control_files["pair-materials.json"] = _canonical(inputs["pair_materials"])
    api_files = {
        item["entry"][name]["ref"].removeprefix("control/"): item[name]
        for item in api_capture["observations"]
        for name in ("response", "receipt")
    }
    api_files["api-observations.json"] = _canonical(
        {
            "kind": "aiflow-node-ci-api-observations",
            "schema_version": "1.0",
            "observations": [item["entry"] for item in api_capture["observations"]],
        }
    )
    host_files = {}
    for slot, row in inputs["host_tools"].items():
        if row is not None:
            data = node._read(
                Path(row["path"]), os_role=slot if slot in node._os_tool_paths() else None
            )
            if len(data) != row["size"] or _sha(data) != row["sha256"]:
                raise _error("CI host input changed before exclusive claim")
            host_files[slot] = data
    host_files["gh"] = _read(_gh_executable())
    if level == "V2":
        for key in ("base_executable", "runtime"):
            row = inputs["pair_materials"]["interpreter"][key]
            data = _read(Path(row["path"]))
            if len(data) != row["size"] or _sha(data) != row["sha256"]:
                raise _error("CI interpreter input changed before exclusive claim")
            host_files["python_" + key] = data
    _admit_known_ci_materials(
        source_root,
        attempt,
        payload_root,
        inputs,
        {**control_files, **api_files},
        host_files,
        level=level,
    )
    control = attempt / "control"
    control.mkdir()
    for name, data in control_files.items():
        _write_new(control / name, data)
    _write_api_observations(attempt, api_capture, seal=False)
    host = attempt / "host"
    host.mkdir()
    for name, data in host_files.items():
        _write_new(host / name, data)
    prepared = node.prepare_ci_materials(
        source_root,
        payload_root,
        attempt_root=attempt,
        admission=admission,
        source_tuple=source_tuple,
    )
    pairs = (
        installed.record_ci_pairs(
            attempt_root=attempt, admission=admission, materials=inputs["pair_materials"]
        )
        if level == "V2"
        else None
    )
    run = node.execute_ci_node(
        source_root,
        task_id,
        attempt_root=attempt,
        admission=admission,
        prepared=prepared,
        source_tuple=source_tuple,
        pairs=pairs,
    )
    final_source, final_declaration, final_blobs = _build_source_authority(source_root, task_id)
    if final_source != source_tuple or final_declaration != declaration or final_blobs != blobs:
        raise _error("CI source authority changed during full fresh verification")
    if (
        authenticate_workflow(
            repository["provider_repository_id"],
            repository["full_name"],
            TARGET_WORKFLOW,
            TARGET_JOB,
            run_id=run_id,
            attempt=run_attempt,
            completed=False,
            _capture=api_capture,
        )
        != platform
    ):
        raise _error("CI platform association changed during verification")
    _write_api_observations(attempt, api_capture)
    roots = _role_roots(source_root, attempt, payload_root, level)
    package, _totals = _write_package(
        attempt, roots, level=level, source_tuple=source_tuple, prepared=prepared, run=run
    )
    facts = validate_ci_originals(package, descriptor, source_tuple)
    write_ci_archive(package, attempt / "transport.zip", level=level)
    _write_new(output, _canonical(facts["evidence"]))
    return validate_node_ci_document(facts["evidence"], kind="aiflow-node-ci-evidence")


def evaluate_node_ci_gate(
    source_root: Path, task_id: str, *, run_id: int, attempt: int, download_dir: Path
) -> dict[str, Any]:
    """Compose authenticated fresh-CI content with two unchanged live LOCAL Gates."""
    from aiflow.errors import AiflowError
    from aiflow.gate import evaluate_gate

    result: dict[str, Any] = {
        "task_id": task_id,
        "passed": False,
        "local_current": False,
        "source_tuple_matches": False,
        "fresh_ci_originals_passed": False,
        "platform_authenticated": False,
        "reason_codes": [],
    }
    reasons: list[str] = []
    first_gate = False
    api_capture: dict[str, Any] | None = None
    owned_download: Path | None = None
    try:
        _caps("V0")
        api_capture = _new_api_capture("api-observations")
        _integer(run_id, minimum=1)
        _integer(attempt, minimum=1)
        source_root = source_root.absolute()
        first = evaluate_gate(source_root, task_id)
        first_gate = first.passed
        if not first_gate:
            reasons.extend(first.reason_codes)
            return {**result, "reason_codes": list(dict.fromkeys(reasons))}
        initial_local_engine_sha = _sha(_canonical(_current_local_engine()))
        initial_source, initial_declaration, _initial_blobs = _build_source_authority(
            source_root, task_id
        )
        repository = initial_declaration["repository"]
        level = initial_source["binding"]["verification_level"]
        _caps(level)
        platform = authenticate_workflow(
            repository["provider_repository_id"],
            repository["full_name"],
            TARGET_WORKFLOW,
            TARGET_JOB,
            run_id=run_id,
            attempt=attempt,
            completed=True,
            _capture=api_capture,
        )
        historical, declaration, blobs = _build_source_authority(
            source_root, task_id, head=platform["head_sha"]
        )
        descriptor = _descriptor(historical, declaration)
        if (
            _source_identity(initial_source) != _source_identity(historical)
            or declaration != initial_declaration
            or platform["workflow_sha256"] != declaration["workflow"]["sha256"]
        ):
            raise _error("Authenticated CI source differs from current LOCAL authority")
        target = download_dir.absolute()
        if (
            target == source_root
            or target.is_relative_to(source_root)
            or source_root.is_relative_to(target)
        ):
            raise _error("CI downloads must be disjoint from protected source")
        _ordinary(target.parent, directory=True)
        if target.exists():
            _ordinary(target, directory=True)
            if list(target.iterdir()):
                raise _error("CI download directory is already spent")
        else:
            target.mkdir()
        owned_download = target
        name = f"aiflow-node-ci-{run_id}-{attempt}"
        _download_artifact(
            platform,
            name=name,
            destination=target / "originals.zip",
            level=level,
            _capture=api_capture,
        )
        package = _extract_package(target / "originals.zip", target / "package", level=level)
        facts = validate_ci_originals(package, descriptor, historical)
        for name, data in blobs.items():
            if _read(package / "originals" / name, limit=MAX_JSON_BYTES) != data:
                raise _error("CI attested raw source blob differs from trusted reachable Git")
        if facts["evidence"]["platform"] != platform:
            raise _error("CI originals belong to another authenticated producer")
        _authenticate_engine(historical["engine_artifact"], _capture=api_capture)
        selection = historical["engine_artifact"]
        if _github_file(
            selection["source_full_name"], "uv.lock", selection["source_head"], _capture=api_capture
        ) != _read(package / "originals/artifact/inputs/uv.lock", limit=MAX_JSON_BYTES):
            raise _error("CI retained Python lock differs from trusted selected source blob")
        inputs = _json(
            _read(package / "originals/control/input-materials.json", limit=MAX_JSON_BYTES)
        )
        engine_content = _installed_wheel_binding(
            package / "originals/artifact/engine-source.zip",
            historical["engine_artifact"],
            inputs,
            descriptor["execution_contract_sha256"],
            package_root=package,
        )
        if (
            engine_content != facts["admission"]["engine_content_sha256"]
            or _sha(_canonical(inputs)) != facts["admission"]["input_materials_sha256"]
        ):
            raise _error("CI admission differs from exact artifact/material originals")
        local_binding = _local_wheel_binding(
            package / "originals/artifact/engine-source.zip",
            historical["engine_artifact"],
            descriptor["execution_contract_sha256"],
        )
        if (
            local_binding["engine_sha256"] != initial_local_engine_sha
            or local_binding["engine_content_sha256"] != engine_content
        ):
            raise _error(
                "Current original-host installation differs from the selected raw wheel",
                "NODE_CI_LOCAL_ENGINE_STALE",
            )
        result["source_tuple_matches"] = True
        result["fresh_ci_originals_passed"] = facts["passed"]
        reasons.extend(facts["reason_codes"])
        if (
            authenticate_workflow(
                repository["provider_repository_id"],
                repository["full_name"],
                TARGET_WORKFLOW,
                TARGET_JOB,
                run_id=run_id,
                attempt=attempt,
                completed=True,
                _capture=api_capture,
            )
            != platform
        ):
            raise _error("CI platform association changed at the decision boundary")
        result["platform_authenticated"] = True
        final_source, final_declaration, _final_blobs = _build_source_authority(
            source_root, task_id
        )
        if (
            _source_identity(final_source) != _source_identity(initial_source)
            or final_declaration != initial_declaration
        ):
            result["source_tuple_matches"] = False
            raise _error("LOCAL source authority changed at the decision boundary")
        if (
            _local_wheel_binding(
                package / "originals/artifact/engine-source.zip",
                historical["engine_artifact"],
                descriptor["execution_contract_sha256"],
            )
            != local_binding
        ):
            raise _error(
                "Current original-host wheel/installation changed at the decision boundary",
                "NODE_CI_LOCAL_ENGINE_STALE",
            )
    except (AiflowError, OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        result["source_tuple_matches"] = False
        result["fresh_ci_originals_passed"] = False
        result["platform_authenticated"] = False
        reasons.append(error.code if isinstance(error, AiflowError) else "NODE_CI_INVALID")
    finally:
        if owned_download is not None and api_capture is not None:
            try:
                _write_api_observations(owned_download, api_capture)
            except (AiflowError, OSError, ValueError, TypeError, KeyError, AttributeError) as error:
                result["platform_authenticated"] = False
                reasons.append(
                    error.code
                    if isinstance(error, AiflowError)
                    else "NODE_CI_API_ORIGINALS_INVALID"
                )
        if first_gate:
            try:
                final_gate = evaluate_gate(source_root, task_id)
                result["local_current"] = final_gate.passed
                reasons.extend(final_gate.reason_codes)
            except (AiflowError, OSError, ValueError, TypeError, KeyError, AttributeError) as error:
                result["local_current"] = False
                reasons.append(
                    error.code if isinstance(error, AiflowError) else "NODE_CI_LOCAL_UNAVAILABLE"
                )
    result["passed"] = not reasons and all(
        result[key] is True
        for key in (
            "local_current",
            "source_tuple_matches",
            "fresh_ci_originals_passed",
            "platform_authenticated",
        )
    )
    result["reason_codes"] = list(dict.fromkeys(reasons))
    return result
