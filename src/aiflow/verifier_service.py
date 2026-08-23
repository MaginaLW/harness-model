"""Immutable, minimal verification context construction and validation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError, StorageError
from aiflow.freshness import current_classification_input_digest
from aiflow.policy import load_policy_bundle
from aiflow.specification import specification_digest
from aiflow.storage import atomic_write_json, read_task_json, resolve_task_path
from aiflow.task_service import read_task_record_strict

_IMPLEMENTATION_EVENTS = frozenset({"implementation_started", "implementation_retried"})
_GIT_TIMEOUT_SECONDS = 10
_ACCEPTANCE_HEADING = re.compile(r"^##[ \t]+验收条件[ \t]*$", re.MULTILINE)
_HEADING = re.compile(r"^##[ \t]+.+?[ \t]*$", re.MULTILINE)


def canonical_json(value: Mapping[str, object]) -> str:
    """Return the canonical JSON representation used for context identities."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def context_sha256(context: Mapping[str, object]) -> str:
    """Hash all context facts except its self-referential digest field."""
    stable = {key: value for key, value in context.items() if key != "context_sha256"}
    return hashlib.sha256(canonical_json(stable).encode("utf-8")).hexdigest()


def validate_verifier_context(context: Mapping[str, object]) -> None:
    """Require a valid contract whose digest is bound to its exact content."""
    require_valid_contract("verifier-context", context)
    if context.get("context_sha256") != context_sha256(context):
        raise ContractError(
            "Verifier context digest is invalid", code="VERIFIER_CONTEXT_HASH_INVALID"
        )


def current_implementer_actor(events: Sequence[Mapping[str, object]]) -> str:
    """Return the actor of the current implementation cycle, or reject it."""
    for event in reversed(events):
        if event.get("event_type") not in _IMPLEMENTATION_EVENTS:
            continue
        actor = event.get("actor")
        normalized = actor.strip() if isinstance(actor, str) else ""
        if normalized:
            return normalized
        break
    raise ContractError(
        "Current implementation cycle has no actor", code="VERIFIER_IMPLEMENTER_MISSING"
    )


def validate_verifier_actor(implementer_actor: str, verifier_actor: str) -> tuple[str, str]:
    """Normalize task-local role labels and enforce their independence."""
    implementer = implementer_actor.strip() if isinstance(implementer_actor, str) else ""
    verifier = verifier_actor.strip() if isinstance(verifier_actor, str) else ""
    if not implementer:
        raise ContractError("Implementer actor is required", code="VERIFIER_IMPLEMENTER_MISSING")
    if not verifier:
        raise ContractError("Verifier actor is required", code="VERIFIER_ACTOR_REQUIRED")
    if implementer == verifier:
        raise ContractError(
            "Verifier actor must differ from implementer actor",
            code="VERIFIER_ACTOR_NOT_INDEPENDENT",
        )
    return implementer, verifier


def _diff_summary(
    root: Path, base_commit: str, subject_commit: str
) -> tuple[list[str], dict[str, int]]:
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--numstat",
                "--no-renames",
                "--format=",
                base_commit,
                subject_commit,
                "--",
            ],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise ContractError(
            "Verifier diff summary timed out", code="VERIFIER_CONTEXT_DIFF_TIMEOUT"
        ) from error
    except OSError as error:
        raise ContractError(
            "Verifier diff summary failed", code="VERIFIER_CONTEXT_DIFF_FAILED"
        ) from error
    if result.returncode != 0:
        raise ContractError("Verifier diff summary failed", code="VERIFIER_CONTEXT_DIFF_FAILED")
    try:
        lines = result.stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ContractError(
            "Verifier diff summary is invalid", code="VERIFIER_CONTEXT_DIFF_INVALID"
        ) from error
    paths: list[str] = []
    additions = 0
    deletions = 0
    binary_files = 0
    for line in lines:
        parts = line.split("\t", maxsplit=2)
        if len(parts) != 3 or not parts[2]:
            raise ContractError(
                "Verifier diff summary is invalid", code="VERIFIER_CONTEXT_DIFF_INVALID"
            )
        if parts[:2] == ["-", "-"]:
            binary_files += 1
        else:
            try:
                additions += int(parts[0])
                deletions += int(parts[1])
            except ValueError as error:
                raise ContractError(
                    "Verifier diff summary is invalid", code="VERIFIER_CONTEXT_DIFF_INVALID"
                ) from error
        paths.append(parts[2].replace("\\", "/"))
    paths.sort()
    return paths, {
        "files": len(paths),
        "additions": additions,
        "deletions": deletions,
        "binary_files": binary_files,
    }


def _acceptance_conditions(frozen_spec: str, task: Mapping[str, object]) -> list[str]:
    """Extract bounded acceptance lines from the frozen specification."""
    heading = _ACCEPTANCE_HEADING.search(frozen_spec)
    if heading is not None:
        following = _HEADING.search(frozen_spec, heading.end())
        body = frozen_spec[heading.end() : following.start() if following else len(frozen_spec)]
        specification_conditions = [
            line.strip().lstrip("-* ").strip() for line in body.splitlines() if line.strip()
        ]
        if specification_conditions:
            return list(dict.fromkeys(specification_conditions))
    conditions: list[str] = []
    units = task.get("decision_units")
    if isinstance(units, list):
        for unit in units:
            if not isinstance(unit, Mapping):
                continue
            methods = unit.get("verification_methods")
            if isinstance(methods, list):
                conditions.extend(
                    method.strip()
                    for method in methods
                    if isinstance(method, str) and method.strip()
                )
    return list(dict.fromkeys(conditions)) or [
        "Meet the frozen task specification acceptance conditions"
    ]


def build_verifier_context(repository_root: Path, task_id: str) -> dict[str, Any]:
    """Build the minimal immutable context from current, governed task facts."""
    root = repository_root.resolve()
    record = read_task_record_strict(root, task_id)
    task = record.task
    current_implementer_actor(record.events)
    classification = read_task_json(
        root, task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(classification, Mapping):
        raise ContractError(
            "Classification is invalid", code="VERIFIER_CONTEXT_CLASSIFICATION_INVALID"
        )
    units = task.get("decision_units")
    if not isinstance(units, list) or not all(isinstance(unit, Mapping) for unit in units):
        raise ContractError("Task decision units are invalid", code="VERIFIER_CONTEXT_INVALID")
    digest, _synchronized = current_classification_input_digest(
        task, units, classification, record.events
    )
    policy = load_policy_bundle(root)
    if (
        classification.get("classification_input_sha256") != digest
        or classification.get("policy_sha256") != policy.sha256
    ):
        raise ContractError("Classification is stale", code="VERIFIER_CONTEXT_CLASSIFICATION_STALE")
    spec_path = resolve_task_path(root, task_id, "spec.md")
    try:
        frozen_spec = spec_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise StorageError(
            "Could not read verifier specification", code="VERIFIER_CONTEXT_SPEC_READ_FAILED"
        ) from error
    spec_sha256 = specification_digest(frozen_spec)
    if task.get("frozen_spec_sha256") != spec_sha256:
        raise ContractError("Frozen specification is stale", code="VERIFIER_CONTEXT_SPEC_STALE")
    required_fields = ("repository_id", "branch", "base_commit", "subject_commit", "goal")
    if not all(
        isinstance(task.get(field), str) and str(task[field]).strip() for field in required_fields
    ):
        raise ContractError("Verifier context facts are invalid", code="VERIFIER_CONTEXT_INVALID")
    allowed_scope = task.get("allowed_scope")
    if not isinstance(allowed_scope, list) or not all(
        isinstance(path, str) and path for path in allowed_scope
    ):
        raise ContractError("Verifier context scope is invalid", code="VERIFIER_CONTEXT_INVALID")
    unit_ids = [
        str(unit["decision_unit_id"])
        for unit in units
        if isinstance(unit.get("decision_unit_id"), str)
    ]
    paths, totals = _diff_summary(root, str(task["base_commit"]), str(task["subject_commit"]))
    context: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": task_id,
        "decision_unit_ids": unit_ids,
        "repository_id": task["repository_id"],
        "branch": task["branch"],
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "spec_sha256": spec_sha256,
        "policy_sha256": policy.sha256,
        "classification_input_sha256": digest,
        "content": {
            "goal": task["goal"],
            "frozen_spec": frozen_spec,
            "code_map": {"allowed_scope": sorted(allowed_scope), "changed_paths": paths},
            "diff_summary": totals,
            "acceptance_conditions": _acceptance_conditions(frozen_spec, task),
            "known_limitations": [
                "Acceptance, integration, and targeted mutation execution are owned by Chapter 11."
            ],
            "reproduce_command": [
                "python",
                "-m",
                "aiflow",
                "verify",
                task_id,
                "--actor",
                "<verifier>",
            ],
        },
    }
    context["context_sha256"] = context_sha256(context)
    validate_verifier_context(context)
    return context


def _context_path(repository_root: Path, task_id: str, digest: str) -> Path:
    return resolve_task_path(repository_root, task_id, Path("verifier-contexts") / f"{digest}.json")


def save_verifier_context(
    repository_root: Path, task_id: str, context: Mapping[str, object]
) -> Path:
    """Store a context once; never replace a digest-addressed artifact."""
    validate_verifier_context(context)
    if context.get("task_id") != task_id:
        raise ContractError(
            "Verifier context task does not match storage", code="VERIFIER_CONTEXT_MISMATCH"
        )
    digest = str(context["context_sha256"])
    path = _context_path(repository_root, task_id, digest)
    if path.exists():
        existing = read_task_json(
            repository_root,
            task_id,
            path.relative_to(resolve_task_path(repository_root, task_id)),
            contract_name="verifier-context",
        )
        if not isinstance(existing, Mapping) or dict(existing) != dict(context):
            raise ContractError("Verifier context is immutable", code="VERIFIER_CONTEXT_IMMUTABLE")
        validate_verifier_context(existing)
        return path
    atomic_write_json(path, dict(context))
    return path


def load_verifier_context(repository_root: Path, task_id: str, digest: str) -> dict[str, Any]:
    """Load one digest-addressed context and enforce filename/content agreement."""
    path = _context_path(repository_root, task_id, digest)
    value = read_task_json(
        repository_root,
        task_id,
        path.relative_to(resolve_task_path(repository_root, task_id)),
        contract_name="verifier-context",
    )
    if not isinstance(value, dict):
        raise ContractError("Verifier context is invalid", code="VERIFIER_CONTEXT_INVALID")
    validate_verifier_context(value)
    if value.get("task_id") != task_id or value.get("context_sha256") != digest:
        raise ContractError(
            "Verifier context filename does not match content", code="VERIFIER_CONTEXT_MISMATCH"
        )
    return value


def validate_verifier_context_current(
    context: Mapping[str, object], current_context: Mapping[str, object]
) -> None:
    """Reject a valid context when any current binding or minimal content is stale."""
    validate_verifier_context(context)
    validate_verifier_context(current_context)
    if context_sha256(context) != context_sha256(current_context):
        raise ContractError("Verifier context is stale", code="VERIFIER_CONTEXT_STALE")
