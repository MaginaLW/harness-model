"""Safe loading and semantic hashing for AI Flow Policy documents."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aiflow.contracts import contract_validation_batch, validate_contract
from aiflow.document_parsing import load_yaml_text
from aiflow.errors import PolicyError

POLICY_FILES: Mapping[str, str] = {
    "hard-rules.yaml": "hard_rules",
    "routing.yaml": "routing",
    "verification-levels.yaml": "verification_levels",
    "permissions.yaml": "permissions",
}
NODE_POLICY_VERSION = "3.1.0"
NODE_PROFILE_ID = "agent-bridge-node"
NODE_PROFILE_REVISION = 1
NODE_V0_CHECKS = (
    {"id": "contract", "required": True, "timeout_seconds": 30},
    {"id": "scope", "required": True, "timeout_seconds": 30},
    {"id": "smoke", "required": True, "timeout_seconds": 30},
    {"id": "node_build", "required": True, "timeout_seconds": 300},
    {"id": "node_check", "required": True, "timeout_seconds": 600},
    {"id": "diff_whitespace", "required": True, "timeout_seconds": 30},
)
NODE_V1_CHECKS = NODE_V0_CHECKS + (
    {"id": "ts_coverage", "required": True, "timeout_seconds": 600},
    {"id": "ts_total_lines", "required": True, "timeout_seconds": 30, "threshold": 85},
    {"id": "ts_diff_lines", "required": True, "timeout_seconds": 30, "threshold": 90},
)
NODE_V0_CHECK_IDS = tuple(str(check["id"]) for check in NODE_V0_CHECKS)
NODE_V1_CHECK_IDS = tuple(str(check["id"]) for check in NODE_V1_CHECKS)


@dataclass(frozen=True)
class PolicyBundle:
    """A complete, validated Policy set and its canonical semantic digest."""

    documents: dict[str, dict[str, Any]]
    policy_version: str
    sha256: str


@dataclass(frozen=True)
class ActionPermission:
    """One Policy-derived automatic action permission decision."""

    action: str
    allowed_automatically: bool
    required_approval: str | None = None
    rule_id: str | None = None


class _UniqueKeyLoader(yaml.SafeLoader):
    """Reject ambiguous mappings in the permissions Policy, including nested ones."""

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self._checked_mappings: set[yaml.MappingNode] = set()
        self._flattening_mappings: set[yaml.MappingNode] = set()

    def flatten_mapping(self, node: yaml.MappingNode) -> None:
        if node in self._flattening_mappings:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found a recursive merge",
                node.start_mark,
            )
        if node in self._checked_mappings:
            return
        self._checked_mappings.add(node)
        keys: set[Any] = set()
        merge_key = object()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                key = merge_key
            elif key_node.tag == "tag:yaml.org,2002:value":
                key = "="
            else:
                key = self.construct_object(key_node)
            try:
                duplicate = key in keys
                keys.add(key)
            except TypeError as error:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable key",
                    key_node.start_mark,
                ) from error
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a duplicate key",
                    key_node.start_mark,
                )
        self._flattening_mappings.add(node)
        try:
            super().flatten_mapping(node)
        finally:
            self._flattening_mappings.remove(node)


def evaluate_action_permission(bundle: PolicyBundle, action: str) -> ActionPermission:
    """Evaluate one normalized action without performing it or consuming approval."""
    normalized = action.strip().casefold()
    if not normalized:
        raise PolicyError("Action category is required", code="POLICY_ACTION_INVALID")
    rules = bundle.documents["permissions.yaml"]["rules"]
    matching = [rule for rule in rules if str(rule["action"]).casefold() == normalized]
    if matching:
        rule = matching[0]
        return ActionPermission(
            normalized,
            rule["effect"] != "deny_automatic",
            str(rule["required_approval"]),
            str(rule["id"]),
        )
    allowed = bundle.documents["permissions.yaml"].get("allowed_automatic_actions", [])
    if isinstance(allowed, list) and normalized in allowed:
        return ActionPermission(normalized, True, rule_id="PERMISSION-ALLOW-AUTOMATIC")
    return ActionPermission(normalized, False, rule_id="PERMISSION-DEFAULT-DENY")


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


def _load_document(
    root: Path,
    filename: str,
    expected_kind: str,
    validate: Callable[[object], list[str]],
) -> dict[str, Any]:
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
        text = path.read_text(encoding="utf-8")
        value = (
            yaml.load(text, Loader=_UniqueKeyLoader)
            if filename == "permissions.yaml"
            else load_yaml_text(text)
        )
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
    version = value.get("policy_version")
    if (
        isinstance(version, str)
        and version.split(".", 1)[0] == "3"
        and version != NODE_POLICY_VERSION
    ):
        raise PolicyError("Policy version is unsupported", code="POLICY_LEVEL_INVALID")
    errors = validate(value)
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
    permission_rules = permissions["rules"]
    permission_actions = {rule["action"] for rule in permission_rules}
    allowed = permissions.get("allowed_automatic_actions", [])
    if (
        not isinstance(allowed, list)
        or forbidden != permission_actions
        or len(permission_actions) != len(permission_rules)
        or forbidden.intersection(allowed)
    ):
        raise PolicyError(
            "Every forbidden action must have exactly one permission rule",
            code="POLICY_PERMISSION_REFERENCE_INVALID",
        )

    levels = documents["verification-levels.yaml"]["levels"]
    level_ids = [level["id"] for level in levels]
    version = str(next(iter(versions)))
    major = version.split(".", maxsplit=1)[0]
    if is_node_policy_candidate(documents):
        expected = {
            "schema_version": "1.0",
            "policy_version": NODE_POLICY_VERSION,
            "policy_kind": "verification_levels",
            "profile": {"id": NODE_PROFILE_ID, "revision": NODE_PROFILE_REVISION},
            "levels": [
                {"id": "V0", "checks": list(NODE_V0_CHECKS)},
                {"id": "V1", "checks": list(NODE_V1_CHECKS)},
            ],
        }
        # Canonical bytes preserve integer types: 1, true and 1.0 are distinct.
        if (
            version != NODE_POLICY_VERSION
            or any(type(priority) is not int for priority in priorities)
            or any(
                "profile" in document
                for name, document in documents.items()
                if name != "verification-levels.yaml"
            )
            or _canonical(documents["verification-levels.yaml"]) != _canonical(expected)
        ):
            raise PolicyError("Node Policy contract is invalid", code="POLICY_LEVEL_INVALID")
        return version
    if major == "1":
        expected_levels = ["V0", "V1"]
    elif major == "2":
        expected_levels = ["V0", "V1", "V2"]
    else:
        raise PolicyError("Policy version is unsupported", code="POLICY_LEVEL_INVALID")
    if level_ids != expected_levels:
        raise PolicyError(
            "Policy verification levels are missing, duplicated, unknown, or unordered",
            code="POLICY_LEVEL_INVALID",
        )
    by_level = {level["id"]: level for level in levels}
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
    v0_checks = by_level["V0"]["checks"]
    v1_checks = by_level["V1"]["checks"]
    if v1_checks[: len(v0_checks)] != v0_checks:
        raise PolicyError(
            "V1 must retain the complete V0 check prefix", code="POLICY_CHECK_REFERENCE_INVALID"
        )
    if major == "2":
        v2_checks = by_level["V2"]["checks"]
        extras = ("acceptance", "integration", "targeted_mutation", "independent_verifier")
        if (
            v2_checks[: len(v1_checks)] != v1_checks
            or tuple(check["id"] for check in v2_checks[len(v1_checks) :]) != extras
            or any(check["required"] is not True for check in v2_checks[len(v1_checks) :])
        ):
            raise PolicyError(
                "V2 must retain V1 and add the required checks in fixed order",
                code="POLICY_CHECK_REFERENCE_INVALID",
            )
    return version


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False
    ).encode("utf-8")


def _digest(documents: Mapping[str, Mapping[str, Any]]) -> str:
    canonical = json.dumps(
        {filename: documents[filename] for filename in POLICY_FILES},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def is_node_policy_candidate(documents: Mapping[str, Mapping[str, Any]]) -> bool:
    """Recognize Node-shaped inputs for rejection, without trusting their contract."""
    return any(
        "profile" in document or str(document.get("policy_version", "")).split(".", 1)[0] == "3"
        for document in documents.values()
    )


def is_node_policy(bundle: PolicyBundle) -> bool:
    """Accept only a complete, validated, digest-matched closed Node bundle."""
    if bundle.policy_version != NODE_POLICY_VERSION or set(bundle.documents) != set(POLICY_FILES):
        return False
    try:
        if any(validate_contract("policy", document) for document in bundle.documents.values()):
            return False
        return (
            _validate_cross_file(bundle.documents) == NODE_POLICY_VERSION
            and _digest(bundle.documents) == bundle.sha256
        )
    except (PolicyError, OSError, KeyError, TypeError, ValueError, RecursionError):
        return False


def load_policy_bundle(
    repository_root: Path,
    *,
    policy_directory: Path | None = None,
) -> PolicyBundle:
    """Load the four fixed Policy files and reject unsafe or contradictory input."""
    if policy_directory is None:
        from aiflow.initialization import require_initialization_ready

        require_initialization_ready(repository_root)
    root = _policy_root(repository_root, policy_directory)
    try:
        _reject_conflicts(root)
    except OSError as error:
        raise PolicyError(
            "Could not inspect Policy directory", code="POLICY_READ_FAILED"
        ) from error
    with contract_validation_batch("policy", len(POLICY_FILES)) as validate:
        documents = {
            filename: _load_document(root, filename, expected_kind, validate)
            for filename, expected_kind in POLICY_FILES.items()
        }
        version = _validate_cross_file(documents)
    return PolicyBundle(documents=documents, policy_version=version, sha256=_digest(documents))
