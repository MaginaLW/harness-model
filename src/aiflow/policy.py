"""Safe loading and semantic hashing for AI Flow Policy documents."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aiflow.contracts import validate_contract
from aiflow.errors import PolicyError

POLICY_FILES: Mapping[str, str] = {
    "hard-rules.yaml": "hard_rules",
    "routing.yaml": "routing",
    "verification-levels.yaml": "verification_levels",
    "permissions.yaml": "permissions",
}


@dataclass(frozen=True)
class PolicyBundle:
    """A complete, validated Policy set and its canonical semantic digest."""

    documents: dict[str, dict[str, Any]]
    policy_version: str
    sha256: str


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _policy_root(repository_root: Path, policy_directory: Path | None) -> Path:
    repository = repository_root.resolve()
    candidate = policy_directory if policy_directory is not None else repository / ".ai" / "policy"
    root = candidate.resolve()
    if policy_directory is None and not _is_within(root, repository):
        raise PolicyError("Policy root escapes the repository", code="POLICY_PATH_ESCAPE")
    if not root.is_dir():
        raise PolicyError("Policy root is missing", code="POLICY_ROOT_MISSING")
    return root


def _reject_conflicts(root: Path) -> None:
    expected_stems = {Path(filename).stem.casefold() for filename in POLICY_FILES}
    for entry in root.iterdir():
        if (
            entry.is_file()
            and entry.name not in POLICY_FILES
            and entry.stem.casefold() in expected_stems
        ):
            raise PolicyError(
                "Policy directory contains a conflicting file name",
                code="POLICY_FILE_CONFLICT",
                details={"filename": entry.name},
            )


def _load_document(root: Path, filename: str, expected_kind: str) -> dict[str, Any]:
    path = root / filename
    if not path.exists():
        raise PolicyError(
            "Required Policy file is missing",
            code="POLICY_FILE_MISSING",
            details={"filename": filename},
        )
    resolved = path.resolve()
    if not _is_within(resolved, root):
        raise PolicyError(
            "Policy file symlink escapes the Policy root",
            code="POLICY_PATH_ESCAPE",
            details={"filename": filename},
        )
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise PolicyError(
            "Could not read or parse Policy file",
            code="POLICY_READ_FAILED",
            details={"filename": filename},
        ) from error
    if not isinstance(value, dict):
        raise PolicyError(
            "Policy document must be an object",
            code="POLICY_SCHEMA_INVALID",
            details={"filename": filename},
        )
    errors = validate_contract("policy", value)
    if errors:
        raise PolicyError(
            "Policy document does not satisfy its Schema",
            code="POLICY_SCHEMA_INVALID",
            details={"filename": filename, "errors": errors},
        )
    if value.get("policy_kind") != expected_kind:
        raise PolicyError(
            "Policy kind does not match its fixed file name",
            code="POLICY_KIND_MISMATCH",
            details={"filename": filename},
        )
    return value


def _rules(documents: Mapping[str, Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for document in documents.values():
        rules = document.get("rules", [])
        if isinstance(rules, list):
            result.extend(rule for rule in rules if isinstance(rule, Mapping))
    return result


def _validate_cross_file(documents: dict[str, dict[str, Any]]) -> str:
    versions = {document["policy_version"] for document in documents.values()}
    if len(versions) != 1:
        raise PolicyError("Policy versions do not match", code="POLICY_VERSION_MISMATCH")

    rules = _rules(documents)
    identifiers = [rule.get("id") for rule in rules]
    priorities = [rule.get("priority") for rule in rules]
    default = documents["routing.yaml"]["default_route"]
    identifiers.append(default["id"])
    priorities.append(default["priority"])
    if len(identifiers) != len(set(identifiers)):
        raise PolicyError(
            "Policy rule IDs must be globally unique", code="POLICY_RULE_ID_DUPLICATE"
        )
    if len(priorities) != len(set(priorities)):
        raise PolicyError(
            "Policy priorities must be globally unique",
            code="POLICY_RULE_PRIORITY_DUPLICATE",
        )

    explicit_safety_priorities = [
        int(rule["priority"])
        for filename in ("hard-rules.yaml", "routing.yaml")
        for rule in documents[filename].get("rules", [])
    ]
    if default.get("id") != "ROUTE-DEFAULT-REVIEW" or default.get("route") != "REVIEW":
        raise PolicyError("Default REVIEW rule is invalid", code="POLICY_DEFAULT_REVIEW_INVALID")
    if explicit_safety_priorities and int(default["priority"]) >= min(explicit_safety_priorities):
        raise PolicyError(
            "Default REVIEW rule must follow explicit safety rules",
            code="POLICY_DEFAULT_REVIEW_ORDER_INVALID",
        )

    permissions = documents["permissions.yaml"]
    forbidden = set(permissions["forbidden_automatic_actions"])
    permission_actions = {rule["action"] for rule in permissions["rules"]}
    if forbidden != permission_actions:
        raise PolicyError(
            "Every forbidden action must have exactly one permission rule",
            code="POLICY_PERMISSION_REFERENCE_INVALID",
        )

    levels = documents["verification-levels.yaml"]["levels"]
    by_level = {level["id"]: level for level in levels}
    if set(by_level) != {"V0", "V1"} or len(levels) != 2:
        raise PolicyError("Policy must define V0 and V1 exactly once", code="POLICY_LEVEL_INVALID")
    check_sets: dict[str, set[str]] = {}
    for level_id, level in by_level.items():
        check_ids = [check["id"] for check in level["checks"]]
        if len(check_ids) != len(set(check_ids)):
            raise PolicyError(
                "Verification checks must be unique within a level",
                code="POLICY_CHECK_DUPLICATE",
            )
        check_sets[level_id] = set(check_ids)
    if not check_sets["V0"].issubset(check_sets["V1"]):
        raise PolicyError("V1 must include every V0 check", code="POLICY_CHECK_REFERENCE_INVALID")
    return str(next(iter(versions)))


def _digest(documents: Mapping[str, Mapping[str, Any]]) -> str:
    canonical = json.dumps(
        {filename: documents[filename] for filename in POLICY_FILES},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_policy_bundle(
    repository_root: Path,
    *,
    policy_directory: Path | None = None,
) -> PolicyBundle:
    """Load the four fixed Policy files and reject unsafe or contradictory input."""
    root = _policy_root(repository_root, policy_directory)
    try:
        _reject_conflicts(root)
    except OSError as error:
        raise PolicyError(
            "Could not inspect Policy directory", code="POLICY_READ_FAILED"
        ) from error
    documents = {
        filename: _load_document(root, filename, expected_kind)
        for filename, expected_kind in POLICY_FILES.items()
    }
    version = _validate_cross_file(documents)
    return PolicyBundle(documents=documents, policy_version=version, sha256=_digest(documents))
