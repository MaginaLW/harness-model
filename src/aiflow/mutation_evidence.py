"""Persist and replay the closed Chapter 11.4 mutation-evidence record."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import secrets
import stat
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from threading import Lock
from typing import Any, cast

from aiflow.approval import (
    APPROVAL_MARKER,
    ApprovalContext,
    canonical_action_sha256,
    matching_approval,
    validate_action_file,
)
from aiflow.contracts import ContractValidationError, require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import AiflowError, ContractError
from aiflow.freshness import current_classification_input_digest
from aiflow.git_context import collect_git_context
from aiflow.mutation_manifest import (
    CANONICAL_MANIFEST_PATH,
    MutationManifest,
    load_mutation_manifest,
)
from aiflow.mutation_runner import (
    MutationProbe,
    MutationRun,
    _issue_runner_authorization,
    run_targeted_mutations,
)
from aiflow.policy import load_policy_bundle
from aiflow.specification import specification_digest
from aiflow.storage import read_task_json, resolve_task_path, task_root
from aiflow.task_service import read_task_record_strict, record_task_event

_RECORD_ID = re.compile(r"^MUTRUN-\d{8}T\d{6}Z-[0-9a-f]{16}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_EVIDENCE_REF = re.compile(
    r"^\.ai/tasks/(?P<task_id>TASK-[0-9]{4,})/logs/"
    r"(?P<record_id>MUTRUN-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{16})/"
    r"targeted-mutation/evidence\.json$"
)
_MANIFEST_REF = CANONICAL_MANIFEST_PATH.as_posix()
_V2_MUTATION_ACTION_GLOB = "action-v2-targeted-mutation-*.json"
_V2_MUTATION_ACTION_TYPE = "targeted_mutation_v2"
_ACTION_CONSUMPTION_THREAD_LOCK = Lock()
_LOG_KEYS = frozenset(
    (
        "mutation_id",
        "safeguard_id",
        "target",
        "target_symbol",
        "operator",
        "expected_detector",
        "expected_outcome",
        "baseline_exit_code",
        "mutant_exit_code",
        "timed_out",
        "duration_ms",
        "reason_code",
        "outcome",
        "run_reason_code",
        "main_tree_unchanged",
    )
)


@dataclass(frozen=True)
class MutationEvidenceArtifact:
    record_id: str
    evidence_ref: str
    mutation_evidence_sha256: str
    log_refs: tuple[str, ...]


@dataclass(frozen=True)
class TargetedMutationFacts:
    """Closed V2 facts derived exclusively from one public-loader replay."""

    passed: bool
    reason_code: str | None
    evidence_ref: str | None
    mutation_evidence_sha256: str | None
    manifest_ref: str | None
    results: tuple[Mapping[str, object], ...]


@dataclass(frozen=True)
class MutationActionUse:
    """One consumed mutation action and the bindings rechecked before launch."""

    action_sha256: str
    receipt_path: Path
    action_path: Path
    decision_unit_id: str
    spec_sha256: str
    policy_sha256: str
    base_commit: str
    classification_input_sha256: str
    receipt_device: int
    receipt_inode: int


def _error(message: str, code: str) -> ContractError:
    return ContractError(message, code=code)


def _action_error(message: str, code: str) -> ContractError:
    return ContractError(message, code=code)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _nonce_hex() -> str:
    return secrets.token_hex(8)


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class _DuplicateKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, _DuplicateKey) as error:
        raise _error(
            "Mutation evidence JSON is invalid", "MUTATION_EVIDENCE_LOG_INVALID"
        ) from error
    if not isinstance(value, dict):
        raise _error("Mutation evidence JSON is invalid", "MUTATION_EVIDENCE_LOG_INVALID")
    return value


def _source_sha256(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as error:
        raise _error(
            "Mutation evidence input could not be read", "MUTATION_EVIDENCE_INPUT_MISMATCH"
        ) from error


def _relative_path(value: str, *, root: Path) -> Path:
    path = Path(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise _error("Mutation evidence path is invalid", "MUTATION_EVIDENCE_PATH_INVALID")
    lexical_root = root.resolve()
    lexical = lexical_root / path
    current = lexical_root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise _error("Mutation evidence path escapes its root", "MUTATION_EVIDENCE_PATH_ESCAPE")
    candidate = lexical.resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise _error(
            "Mutation evidence path escapes its root", "MUTATION_EVIDENCE_PATH_ESCAPE"
        ) from error
    return candidate


def _derive_outcome(probe: MutationProbe, run: MutationRun) -> str:
    if (
        run.reason_code is not None
        or run.main_tree_unchanged is not True
        or probe.reason_code is not None
    ):
        return "unverified"
    if probe.baseline_exit_code == 0 and probe.mutant_exit_code == 1 and probe.timed_out is False:
        return "killed"
    if probe.baseline_exit_code == 0 and probe.mutant_exit_code == 0 and probe.timed_out is False:
        return "survived"
    return "unverified"


def _validate_bindings(
    root: Path, task_id: str, subject: str
) -> tuple[dict[str, Any], dict[str, Any], str]:
    try:
        record = read_task_record_strict(root, task_id)
    except Exception as error:
        raise _error(
            "Mutation evidence bindings are stale", "MUTATION_EVIDENCE_BINDING_STALE"
        ) from error
    task = record.task
    if task.get("subject_commit") != subject or _COMMIT.fullmatch(subject) is None:
        raise _error("Mutation evidence subject is invalid", "MUTATION_EVIDENCE_SUBJECT_INVALID")
    try:
        context = collect_git_context(root)
    except (AiflowError, OSError, UnicodeError) as error:
        raise _error(
            "Mutation evidence subject could not be resolved",
            "MUTATION_EVIDENCE_SUBJECT_INVALID",
        ) from error
    if (
        context.repository_id != task.get("repository_id")
        or context.branch != task.get("branch")
        or context.head != subject
    ):
        raise _error("Mutation evidence bindings are stale", "MUTATION_EVIDENCE_BINDING_STALE")
    try:
        spec = resolve_task_path(root, task_id, "spec.md").read_text(encoding="utf-8")
        classification = read_task_json(
            root, task_id, "classification.json", contract_name="classification"
        )
        bundle = load_policy_bundle(root)
        input_digest, synchronized = current_classification_input_digest(
            task,
            task.get("decision_units", []),
            classification if isinstance(classification, Mapping) else {},
            record.events,
        )
    except (AiflowError, OSError, UnicodeError, KeyError, TypeError, ValueError) as error:
        raise _error(
            "Mutation evidence bindings are stale", "MUTATION_EVIDENCE_BINDING_STALE"
        ) from error
    classified_subject = (
        classification.get("subject_commit") if isinstance(classification, dict) else None
    )
    if (
        not isinstance(classification, dict)
        or task.get("frozen_spec_sha256") != specification_digest(spec)
        or classification.get("base_commit") != task.get("base_commit")
        or classification.get("policy_sha256") != bundle.sha256
        or classification.get("classification_input_sha256") != input_digest
        or (classified_subject != subject and not synchronized)
    ):
        raise _error("Mutation evidence bindings are stale", "MUTATION_EVIDENCE_BINDING_STALE")
    input_sha = classification.get("classification_input_sha256")
    if not isinstance(input_sha, str) or _SHA256.fullmatch(input_sha) is None:
        raise _error("Mutation evidence bindings are stale", "MUTATION_EVIDENCE_BINDING_STALE")
    return task, classification, bundle.sha256


def _utc_text() -> str:
    return _utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")


def _action_approvals(root: Path, task_id: str) -> tuple[Mapping[str, object], ...]:
    value = read_task_json(root, task_id, "approvals.json")
    if not isinstance(value, list):
        raise _action_error(
            "Targeted mutation action approvals are invalid",
            "ACTION_APPROVAL_INVALID",
        )
    approvals: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise _action_error(
                "Targeted mutation action approvals are invalid",
                "ACTION_APPROVAL_INVALID",
            )
        try:
            require_valid_contract("approval", item)
        except ContractError as error:
            raise _action_error(
                "Targeted mutation action approvals are invalid",
                "ACTION_APPROVAL_INVALID",
            ) from error
        approvals.append(item)
    return tuple(approvals)


def _used_action_digests(root: Path, task_id: str) -> Mapping[str, tuple[str, int, int]]:
    """Return action digests and receipt identities from append-only task history."""
    try:
        record = read_task_record_strict(root, task_id)
    except AiflowError as error:
        raise _action_error(
            "Targeted mutation action consumption history is invalid",
            "ACTION_APPROVAL_INVALID",
        ) from error
    consumed: dict[str, tuple[str, int, int]] = {}
    for event in record.events:
        payload = event.get("payload")
        if (
            event.get("event_type") != "approval_recorded"
            or not isinstance(payload, Mapping)
            or payload.get("approval_type") != "action"
            or payload.get("action_status") != "consumed"
        ):
            continue
        digest = payload.get("action_sha256")
        receipt_ref = payload.get("receipt_ref")
        receipt_device = payload.get("receipt_device")
        receipt_inode = payload.get("receipt_inode")
        if (
            not isinstance(digest, str)
            or _SHA256.fullmatch(digest) is None
            or not isinstance(receipt_ref, str)
            or not isinstance(receipt_device, int)
            or isinstance(receipt_device, bool)
            or receipt_device < 0
            or not isinstance(receipt_inode, int)
            or isinstance(receipt_inode, bool)
            or receipt_inode < 0
            or digest in consumed
        ):
            raise _action_error(
                "Targeted mutation action consumption history is invalid",
                "ACTION_APPROVAL_INVALID",
            )
        consumed[digest] = (receipt_ref, receipt_device, receipt_inode)
    return consumed


def _require_no_pending_approval(root: Path, task_id: str) -> None:
    approval_marker = resolve_task_path(root, task_id) / APPROVAL_MARKER
    try:
        approval_marker.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise _action_error(
            "Targeted mutation action approval transaction could not be inspected",
            "ACTION_APPROVAL_PENDING",
        ) from error
    raise _action_error(
        "Targeted mutation action approval transaction is incomplete",
        "ACTION_APPROVAL_PENDING",
    )


def _lock_descriptor(descriptor: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        return
    fcntl = importlib.import_module("fcntl")
    fcntl.flock(descriptor, fcntl.LOCK_EX)


def _unlock_descriptor(descriptor: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        return
    fcntl = importlib.import_module("fcntl")
    fcntl.flock(descriptor, fcntl.LOCK_UN)


@contextmanager
def _locked_action_consumption(root: Path, task_id: str) -> Iterator[None]:
    """Serialize the check-and-record reservation for one task across processes."""
    descriptor: int | None = None
    locked = False
    try:
        with _ACTION_CONSUMPTION_THREAD_LOCK:
            lock_directory = resolve_task_path(root, task_id, "logs")
            lock_directory.mkdir(exist_ok=True)
            descriptor = os.open(
                lock_directory / "action-consumption.lock", os.O_CREAT | os.O_RDWR, 0o600
            )
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
                os.fsync(descriptor)
            _lock_descriptor(descriptor)
            locked = True
            yield
    except OSError as error:
        raise _action_error(
            "Targeted mutation action consumption could not be reserved",
            "ACTION_RECEIPT_WRITE_FAILED",
        ) from error
    finally:
        if descriptor is not None:
            try:
                if locked:
                    _unlock_descriptor(descriptor)
            finally:
                os.close(descriptor)


def _require_action_task_facts(
    root: Path,
    task_id: str,
    subject_commit: str,
    task: Mapping[str, object],
    classification: Mapping[str, object],
) -> Mapping[str, Mapping[str, object]]:
    if task.get("current_state") != "VERIFYING":
        raise _action_error(
            "Targeted mutation action requires active verification",
            "ACTION_STATE_INVALID",
        )
    if task.get("subject_commit") != subject_commit:
        raise _action_error(
            "Targeted mutation action targets a stale subject",
            "ACTION_SUBJECT_MISMATCH",
        )
    if classification.get("effective_verification_level") != "V2":
        raise _action_error(
            "Targeted mutation action requires V2 verification",
            "ACTION_LEVEL_INVALID",
        )
    context = collect_git_context(root)
    task_prefix = f".ai/tasks/{task_id}/"
    if any(
        path != task_prefix.rstrip("/") and not path.startswith(task_prefix)
        for path in context.dirty_paths
    ):
        raise _action_error(
            "Targeted mutation action worktree is not governance-only",
            "ACTION_BINDING_STALE",
        )
    return {str(unit["decision_unit_id"]): unit for unit in parse_decision_units(task)}


def _require_current_spec_approvals(
    task_id: str,
    task: Mapping[str, object],
    classification: Mapping[str, object],
    approvals: tuple[Mapping[str, object], ...],
    *,
    policy_sha256: str,
) -> None:
    entries = classification.get("classifications")
    entries_list = entries if isinstance(entries, list) else []
    review_ids = {
        str(entry["decision_unit_id"])
        for entry in entries_list
        if isinstance(entry, Mapping) and entry.get("route") == "REVIEW"
    }
    for decision_unit_id in review_ids:
        context = ApprovalContext(
            task_id,
            decision_unit_id,
            str(task["current_state"]),
            str(task["frozen_spec_sha256"]),
            policy_sha256,
            str(task["base_commit"]),
            str(task["subject_commit"]),
        )
        if matching_approval(approvals, approval_type="spec", context=context) is None:
            raise _action_error(
                "Targeted mutation action requires current specification approval",
                "ACTION_APPROVAL_INVALID",
            )


def _normalized_current_action(
    action_path: Path,
    *,
    root: Path,
    task_id: str,
    subject_commit: str,
    classification_input_sha256: str,
    units: Mapping[str, Mapping[str, object]],
) -> tuple[Mapping[str, object], str]:
    task_directory = resolve_task_path(root, task_id)
    if action_path.parent != task_directory or action_path.is_symlink():
        raise _action_error("Targeted mutation action path is invalid", "ACTION_FILE_INVALID")
    raw = read_task_json(root, task_id, action_path.name)
    if not isinstance(raw, Mapping):
        raise _action_error("Targeted mutation action file is invalid", "ACTION_FILE_INVALID")
    action = validate_action_file(raw, subject_commit=subject_commit, now=_utc_text())
    decision_unit_id = action.get("decision_unit_id")
    unit = units.get(str(decision_unit_id))
    verification = unit.get("verification_requirements") if unit is not None else None
    permissions = unit.get("permission_requirements") if unit is not None else None
    if (
        unit is None
        or not isinstance(permissions, list)
        or "action_approval" not in permissions
        or not isinstance(verification, Mapping)
        or verification.get("targeted_mutation_required") is not True
        or action.get("classification_input_sha256") != classification_input_sha256
        or action.get("action_type") != _V2_MUTATION_ACTION_TYPE
        or action.get("target") != task_id
    ):
        raise _action_error(
            "Targeted mutation action does not match the fixed transaction",
            "ACTION_FILE_INVALID",
        )
    return action, str(decision_unit_id)


def _current_targeted_mutation_action(
    root: Path,
    task_id: str,
    subject_commit: str,
    task: Mapping[str, object],
    classification: Mapping[str, object],
    policy_sha256: str,
) -> tuple[str, Mapping[str, object], Path, str]:
    _require_no_pending_approval(root, task_id)
    units = _require_action_task_facts(root, task_id, subject_commit, task, classification)
    approvals = _action_approvals(root, task_id)
    _require_current_spec_approvals(
        task_id, task, classification, approvals, policy_sha256=policy_sha256
    )
    classification_sha256 = classification.get("classification_input_sha256")
    if (
        not isinstance(classification_sha256, str)
        or _SHA256.fullmatch(classification_sha256) is None
    ):
        raise _action_error(
            "Targeted mutation classification binding is invalid",
            "ACTION_CLASSIFICATION_MISMATCH",
        )
    task_directory = resolve_task_path(root, task_id)
    try:
        action_paths = tuple(sorted(task_directory.glob(_V2_MUTATION_ACTION_GLOB)))
    except OSError as error:
        raise _action_error(
            "Targeted mutation action inventory is unavailable",
            "ACTION_FILE_INVALID",
        ) from error

    approved: list[tuple[str, Mapping[str, object], Path, str]] = []
    used_digests: list[str] = []
    consumed_digests = _used_action_digests(root, task_id)
    classification_stale = False
    for action_path in action_paths:
        raw = read_task_json(root, task_id, action_path.name)
        if not isinstance(raw, Mapping):
            raise _action_error("Targeted mutation action file is invalid", "ACTION_FILE_INVALID")
        raw_subject = raw.get("subject_commit")
        if isinstance(raw_subject, str) and raw_subject != subject_commit:
            continue
        if not isinstance(raw_subject, str):
            raise _action_error(
                "Targeted mutation action file is incomplete", "ACTION_FILE_INVALID"
            )
        if raw.get("classification_input_sha256") != classification_sha256:
            classification_stale = True
            continue
        try:
            action, decision_unit_id = _normalized_current_action(
                action_path,
                root=root,
                task_id=task_id,
                subject_commit=subject_commit,
                classification_input_sha256=classification_sha256,
                units=units,
            )
        except ContractError as error:
            if error.code == "ACTION_APPROVAL_EXPIRED":
                continue
            raise
        digest = canonical_action_sha256(action)
        context = ApprovalContext(
            task_id,
            decision_unit_id,
            str(task["current_state"]),
            str(task["frozen_spec_sha256"]),
            policy_sha256,
            str(task["base_commit"]),
            subject_commit,
            digest,
        )
        if matching_approval(approvals, approval_type="action", context=context) is None:
            continue
        receipt = resolve_task_path(root, task_id, f"action-use-{digest}.md")
        if digest in consumed_digests or receipt.exists() or receipt.is_symlink():
            used_digests.append(digest)
        else:
            approved.append((digest, action, action_path, decision_unit_id))

    if len(approved) > 1:
        raise _action_error(
            "Multiple targeted mutation actions are currently approved",
            "ACTION_APPROVAL_AMBIGUOUS",
        )
    if not approved:
        if used_digests:
            raise _action_error(
                "Targeted mutation action approval was already used",
                "ACTION_APPROVAL_USED",
            )
        if classification_stale:
            raise _action_error(
                "Targeted mutation action classification binding is stale",
                "ACTION_CLASSIFICATION_MISMATCH",
            )
        raise _action_error(
            "Targeted mutation action approval is required",
            "ACTION_APPROVAL_REQUIRED",
        )
    return approved[0]


def _consume_targeted_mutation_action(
    root: Path,
    task_id: str,
    subject_commit: str,
    task: Mapping[str, object],
    classification: Mapping[str, object],
    policy_sha256: str,
) -> MutationActionUse:
    # Keep missing/stale/unapproved calls read-only; the locked lookup below is
    # repeated because only that one participates in the atomic reservation.
    _current_targeted_mutation_action(
        root, task_id, subject_commit, task, classification, policy_sha256
    )
    with _locked_action_consumption(root, task_id):
        digest, action, action_path, decision_unit_id = _current_targeted_mutation_action(
            root, task_id, subject_commit, task, classification, policy_sha256
        )
        receipt = resolve_task_path(root, task_id, f"action-use-{digest}.md")
        started_at = _utc_text()
        content = (
            f"# {task_id} V2 targeted mutation action use\n\n"
            f"- Task: `{task_id}`\n"
            f"- Decision unit: `{decision_unit_id}`\n"
            f"- Action type: `{_V2_MUTATION_ACTION_TYPE}`\n"
            f"- Action SHA-256: `{digest}`\n"
            f"- Subject commit: `{subject_commit}`\n"
            "- Classification input SHA-256: "
            f"`{classification['classification_input_sha256']}`\n"
            f"- Spec SHA-256: `{task['frozen_spec_sha256']}`\n"
            f"- Policy SHA-256: `{policy_sha256}`\n"
            f"- Base commit: `{task['base_commit']}`\n"
            "- Status: `started`\n"
            f"- Started at: `{started_at}`\n"
            f"- Expires at: `{action['expires_at']}`\n"
            "- Approval consumed: `true`\n"
            "- Reusable: `false`\n\n"
            "Creation of this receipt precedes the fixed runner invocation. Launch, "
            "failure, or interruption consumes the approval; no retry or deletion is "
            "authorized.\n"
        )
        receipt_stat: os.stat_result | None = None
        try:
            with receipt.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
                receipt_stat = os.fstat(stream.fileno())
        except FileExistsError as error:
            raise _action_error(
                "Targeted mutation action approval was already used",
                "ACTION_APPROVAL_USED",
            ) from error
        except OSError as error:
            raise _action_error(
                "Targeted mutation action receipt could not be created",
                "ACTION_RECEIPT_WRITE_FAILED",
            ) from error
        assert receipt_stat is not None
        try:
            record_task_event(
                root,
                task_id,
                event_type="approval_recorded",
                actor="aiflow-targeted-mutation-recorder",
                payload={
                    "approval_type": "action",
                    "action_status": "consumed",
                    "action_sha256": digest,
                    "decision_unit_id": decision_unit_id,
                    "subject_commit": subject_commit,
                    "classification_input_sha256": classification["classification_input_sha256"],
                    "receipt_ref": receipt.relative_to(root).as_posix(),
                    "receipt_device": receipt_stat.st_dev,
                    "receipt_inode": receipt_stat.st_ino,
                },
            )
        except AiflowError as error:
            raise _action_error(
                "Targeted mutation action consumption could not be recorded",
                "ACTION_RECEIPT_WRITE_FAILED",
            ) from error
    return MutationActionUse(
        digest,
        receipt,
        action_path,
        decision_unit_id,
        str(task["frozen_spec_sha256"]),
        policy_sha256,
        str(task["base_commit"]),
        str(classification["classification_input_sha256"]),
        receipt_stat.st_dev,
        receipt_stat.st_ino,
    )


def _revalidate_targeted_mutation_action(
    root: Path,
    task_id: str,
    subject_commit: str,
    action_use: MutationActionUse,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    _require_no_pending_approval(root, task_id)
    task, classification, policy_sha256 = _validate_bindings(root, task_id, subject_commit)
    units = _require_action_task_facts(root, task_id, subject_commit, task, classification)
    classification_sha256 = classification.get("classification_input_sha256")
    try:
        receipt_stat = action_use.receipt_path.stat(follow_symlinks=False)
        receipt_ref = action_use.receipt_path.relative_to(root).as_posix()
    except (OSError, ValueError) as error:
        raise _action_error(
            "Targeted mutation action changed after consumption",
            "ACTION_BINDING_STALE",
        ) from error
    consumed_identity = _used_action_digests(root, task_id).get(action_use.action_sha256)
    expected_identity = (
        receipt_ref,
        action_use.receipt_device,
        action_use.receipt_inode,
    )
    if (
        task.get("frozen_spec_sha256") != action_use.spec_sha256
        or task.get("base_commit") != action_use.base_commit
        or policy_sha256 != action_use.policy_sha256
        or classification_sha256 != action_use.classification_input_sha256
        or not stat.S_ISREG(receipt_stat.st_mode)
        or receipt_stat.st_dev != action_use.receipt_device
        or receipt_stat.st_ino != action_use.receipt_inode
        or consumed_identity != expected_identity
    ):
        raise _action_error(
            "Targeted mutation action changed after consumption",
            "ACTION_BINDING_STALE",
        )
    action, decision_unit_id = _normalized_current_action(
        action_use.action_path,
        root=root,
        task_id=task_id,
        subject_commit=subject_commit,
        classification_input_sha256=action_use.classification_input_sha256,
        units=units,
    )
    if (
        decision_unit_id != action_use.decision_unit_id
        or canonical_action_sha256(action) != action_use.action_sha256
    ):
        raise _action_error(
            "Targeted mutation action changed after consumption",
            "ACTION_BINDING_STALE",
        )
    approvals = _action_approvals(root, task_id)
    _require_current_spec_approvals(
        task_id, task, classification, approvals, policy_sha256=policy_sha256
    )
    context = ApprovalContext(
        task_id,
        decision_unit_id,
        str(task["current_state"]),
        action_use.spec_sha256,
        action_use.policy_sha256,
        action_use.base_commit,
        subject_commit,
        action_use.action_sha256,
    )
    if matching_approval(approvals, approval_type="action", context=context) is None:
        raise _action_error(
            "Targeted mutation action approval changed after consumption",
            "ACTION_APPROVAL_INVALID",
        )
    return task, classification, policy_sha256


def _complete_targeted_mutation_action(
    action_use: MutationActionUse, artifact: MutationEvidenceArtifact
) -> None:
    content = (
        "\n## Result\n\n"
        "- Status: `recorded`\n"
        f"- Evidence ref: `{artifact.evidence_ref}`\n"
        "- Canonical mutation-evidence SHA-256: "
        f"`{artifact.mutation_evidence_sha256}`\n"
        f"- Recorded at: `{_utc_text()}`\n"
    )
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(action_use.receipt_path, flags)
        descriptor_stat = os.fstat(descriptor)
        path_stat = action_use.receipt_path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(descriptor_stat.st_mode)
            or not stat.S_ISREG(path_stat.st_mode)
            or descriptor_stat.st_dev != action_use.receipt_device
            or descriptor_stat.st_ino != action_use.receipt_inode
            or path_stat.st_dev != action_use.receipt_device
            or path_stat.st_ino != action_use.receipt_inode
        ):
            raise OSError("targeted mutation action receipt identity changed")
        with os.fdopen(descriptor, "a", encoding="utf-8", newline="\n") as stream:
            descriptor = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise _action_error(
            "Targeted mutation action result could not be recorded",
            "ACTION_RECEIPT_WRITE_FAILED",
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _authorize_targeted_mutation_runner_launch(
    repository_root: Path,
    task_id: str,
    subject_commit: str,
    *,
    action_sha256: str,
    receipt_path: Path,
    action_path: Path,
    decision_unit_id: str,
    spec_sha256: str,
    policy_sha256: str,
    base_commit: str,
    classification_input_sha256: str,
    receipt_device: int,
    receipt_inode: int,
) -> None:
    """Independently replay authority and reserve the sole runner launch."""
    root = Path(repository_root).resolve()
    expected_receipt = resolve_task_path(root, task_id, f"action-use-{action_sha256}.md")
    task_directory = resolve_task_path(root, task_id)
    if receipt_path != expected_receipt or action_path.parent != task_directory:
        raise _action_error(
            "Targeted mutation runner bindings are invalid",
            "ACTION_BINDING_STALE",
        )
    action_use = MutationActionUse(
        action_sha256,
        receipt_path,
        action_path,
        decision_unit_id,
        spec_sha256,
        policy_sha256,
        base_commit,
        classification_input_sha256,
        receipt_device,
        receipt_inode,
    )
    _revalidate_targeted_mutation_action(root, task_id, subject_commit, action_use)
    claim_directory = resolve_task_path(root, task_id, "logs")
    claim = claim_directory / f"action-launch-{action_sha256}.json"
    payload = {
        "schema_version": "1.0",
        "task_id": task_id,
        "action_sha256": action_sha256,
        "subject_commit": subject_commit,
        "receipt_ref": receipt_path.relative_to(root).as_posix(),
        "receipt_device": receipt_device,
        "receipt_inode": receipt_inode,
        "claimed_at": _utc_text(),
        "single_use": True,
    }
    try:
        claim_directory.mkdir(exist_ok=True)
        with claim.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise _action_error(
            "Targeted mutation runner launch was already claimed",
            "ACTION_APPROVAL_USED",
        ) from error
    except OSError as error:
        raise _action_error(
            "Targeted mutation runner launch could not be claimed",
            "ACTION_RECEIPT_WRITE_FAILED",
        ) from error


def _task0014_production_subject(repository_root: Path) -> str | None:
    """Return the sole active TASK-0014 subject, or select the mocked mode.

    This selector deliberately performs no runner action.  A malformed current
    TASK-0014 is a governed failure, whereas another task bound to the same
    repository, branch, and subject merely makes production mode ineligible.
    """
    root = Path(repository_root).resolve()
    try:
        directories = tuple(sorted(path for path in task_root(root).iterdir() if path.is_dir()))
    except OSError as error:
        raise _error(
            "Mutation evidence task inventory is unavailable", "MUTATION_EVIDENCE_BINDING_STALE"
        ) from error
    task_records: list[tuple[str, dict[str, Any]]] = []
    current_task: dict[str, Any] | None = None
    for directory in directories:
        if not re.fullmatch(r"TASK-\d{4,}", directory.name):
            continue
        try:
            record = read_task_record_strict(root, directory.name)
        except Exception as error:
            if directory.name == "TASK-0014":
                raise _error(
                    "TASK-0014 bindings are invalid", "MUTATION_EVIDENCE_BINDING_STALE"
                ) from error
            return None
        task_records.append((directory.name, record.task))
        if directory.name == "TASK-0014":
            current_task = record.task
    if current_task is None:
        return None
    if current_task.get("current_state") not in {"IMPLEMENTING", "VERIFYING"}:
        return None
    subject = current_task.get("subject_commit")
    if not isinstance(subject, str):
        raise _error("TASK-0014 subject is invalid", "MUTATION_EVIDENCE_SUBJECT_INVALID")
    current_binding = (
        current_task.get("repository_id"),
        current_task.get("branch"),
        subject,
    )
    head_bound_active = [
        task_id
        for task_id, task in task_records
        if task.get("current_state") != "MERGED"
        and (task.get("repository_id"), task.get("branch"), task.get("subject_commit"))
        == current_binding
    ]
    if head_bound_active != ["TASK-0014"]:
        return None
    _validate_bindings(root, "TASK-0014", subject)
    return subject


def _reserve_record_root(root: Path, task_id: str, now: datetime) -> tuple[str, Path]:
    try:
        lexical_logs = task_root(root) / task_id / "logs"
    except AiflowError as error:
        raise _error(
            "Mutation evidence log root escapes the task", "MUTATION_EVIDENCE_PATH_ESCAPE"
        ) from error
    if lexical_logs.is_symlink():
        raise _error("Mutation evidence log root is invalid", "MUTATION_EVIDENCE_PATH_INVALID")
    try:
        logs = resolve_task_path(root, task_id, "logs")
    except AiflowError as error:
        raise _error(
            "Mutation evidence log root escapes the task", "MUTATION_EVIDENCE_PATH_ESCAPE"
        ) from error
    try:
        logs.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise _error(
            "Mutation evidence log root could not be prepared", "MUTATION_EVIDENCE_ID_FAILED"
        ) from error
    if logs.is_symlink():
        raise _error("Mutation evidence log root is invalid", "MUTATION_EVIDENCE_PATH_INVALID")
    if now.tzinfo is None or now.utcoffset() is None:
        raise _error("Mutation evidence clock is invalid", "MUTATION_EVIDENCE_ID_FAILED")
    try:
        stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    except (OverflowError, ValueError) as error:
        raise _error("Mutation evidence clock is invalid", "MUTATION_EVIDENCE_ID_FAILED") from error
    for _ in range(3):
        record_id = f"MUTRUN-{stamp}-{_nonce_hex()}"
        if _RECORD_ID.fullmatch(record_id) is None:
            raise _error("Mutation evidence ID generation failed", "MUTATION_EVIDENCE_ID_FAILED")
        target = logs / record_id
        try:
            target.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        except OSError as error:
            raise _error(
                "Mutation evidence record could not be reserved", "MUTATION_EVIDENCE_ID_FAILED"
            ) from error
        if target.is_symlink() or target.resolve().parent != logs.resolve():
            raise _error(
                "Mutation evidence record path escapes log root", "MUTATION_EVIDENCE_PATH_ESCAPE"
            )
        return record_id, target
    raise _error("Mutation evidence record already exists", "MUTATION_EVIDENCE_IMMUTABLE_CONFLICT")


def _write_new_json(path: Path, value: Mapping[str, object]) -> None:
    """Create one JSON file without replacing a historical artifact."""
    temporary: Path | None = None
    try:
        payload = (
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        )
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise _error(
                "Mutation evidence target already exists", "MUTATION_EVIDENCE_IMMUTABLE_CONFLICT"
            ) from error
    except (OSError, TypeError, ValueError) as error:
        raise _error(
            "Mutation evidence could not be written", "MUTATION_EVIDENCE_WRITE_FAILED"
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _load_manifest(root: Path) -> MutationManifest:
    try:
        return load_mutation_manifest(root)
    except (OSError, UnicodeError, ContractError, ValueError) as error:
        raise _error(
            "Mutation evidence manifest inputs are invalid", "MUTATION_EVIDENCE_INPUT_MISMATCH"
        ) from error


def _record_time_matches(record_id: str, generated_at: object) -> bool:
    if not isinstance(generated_at, str) or _RECORD_ID.fullmatch(record_id) is None:
        return False
    date = record_id[7:15]
    clock = record_id[16:22]
    return (
        generated_at == f"{date[:4]}-{date[4:6]}-{date[6:8]}T{clock[:2]}:{clock[2:4]}:{clock[4:6]}Z"
    )


def _validate_run(manifest: MutationManifest, run: MutationRun, subject: str) -> None:
    if not isinstance(run, MutationRun) or any(
        not isinstance(probe, MutationProbe) for probe in getattr(run, "probes", ())
    ):
        raise _error("Mutation runner probe is invalid", "MUTATION_EVIDENCE_INPUT_MISMATCH")
    if (
        run.manifest_id != manifest.manifest_id
        or run.subject_commit != subject
        or len(run.probes) != len(manifest.mutations)
    ):
        raise _error(
            "Mutation runner result does not match current inputs",
            "MUTATION_EVIDENCE_INPUT_MISMATCH",
        )
    if tuple(probe.mutation_id for probe in run.probes) != tuple(
        item.mutation_id for item in manifest.mutations
    ):
        raise _error(
            "Mutation runner result order does not match manifest",
            "MUTATION_EVIDENCE_INPUT_MISMATCH",
        )


def _make_artifact(
    root: Path,
    task_id: str,
    subject_commit: str,
    *,
    run: MutationRun,
    now: datetime,
    record_id: str,
    record_root: Path,
    task: Mapping[str, Any],
    classification: Mapping[str, Any],
    policy_sha: str,
    manifest: MutationManifest,
    manifest_sha: str,
    runner_sha: str,
) -> MutationEvidenceArtifact:
    if now.tzinfo is None or now.utcoffset() is None:
        raise _error("Mutation evidence clock is invalid", "MUTATION_EVIDENCE_ID_FAILED")
    generated_at = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    expected_record_ref = f".ai/tasks/{task_id}/logs/{record_id}"
    expected_record_root = _relative_path(expected_record_ref, root=root)
    if (
        not _record_time_matches(record_id, generated_at)
        or not record_root.is_dir()
        or record_root.is_symlink()
        or record_root.resolve() != expected_record_root
    ):
        raise _error("Mutation evidence record path is invalid", "MUTATION_EVIDENCE_PATH_INVALID")
    _validate_run(manifest, run, subject_commit)
    evidence_dir = record_root / "targeted-mutation"
    log_dir = evidence_dir / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise _error(
            "Mutation evidence target already exists", "MUTATION_EVIDENCE_IMMUTABLE_CONFLICT"
        ) from error
    except OSError as error:
        raise _error(
            "Mutation evidence could not be written", "MUTATION_EVIDENCE_WRITE_FAILED"
        ) from error
    results: list[dict[str, object]] = []
    log_refs: list[str] = []
    for declaration, probe in zip(manifest.mutations, run.probes, strict=True):
        outcome = _derive_outcome(probe, run)
        log = {
            "mutation_id": probe.mutation_id,
            "safeguard_id": declaration.safeguard_id,
            "target": declaration.target,
            "target_symbol": declaration.target_symbol,
            "operator": declaration.operator,
            "expected_detector": declaration.expected_detector,
            "expected_outcome": declaration.expected_outcome,
            "baseline_exit_code": probe.baseline_exit_code,
            "mutant_exit_code": probe.mutant_exit_code,
            "timed_out": probe.timed_out,
            "duration_ms": probe.duration_ms,
            "reason_code": probe.reason_code,
            "outcome": outcome,
            "run_reason_code": run.reason_code,
            "main_tree_unchanged": run.main_tree_unchanged,
        }
        if set(log) != _LOG_KEYS:
            raise _error("Mutation evidence log is invalid", "MUTATION_EVIDENCE_LOG_INVALID")
        log_path = log_dir / f"{probe.mutation_id}.json"
        _write_new_json(log_path, log)
        log_ref = log_path.relative_to(root.resolve()).as_posix()
        log_refs.append(log_ref)
        results.append(
            {
                "mutation_id": declaration.mutation_id,
                "safeguard_id": declaration.safeguard_id,
                "target": declaration.target,
                "target_symbol": declaration.target_symbol,
                "operator": declaration.operator,
                "expected_detector": declaration.expected_detector,
                "expected_outcome": declaration.expected_outcome,
                "baseline_exit_code": probe.baseline_exit_code,
                "mutant_exit_code": probe.mutant_exit_code,
                "timed_out": probe.timed_out,
                "duration_ms": probe.duration_ms,
                "reason_code": probe.reason_code,
                "outcome": outcome,
                "log_ref": log_ref,
                "log_sha256": _source_sha256(log_path),
            }
        )
    uncovered = [result["mutation_id"] for result in results if result["outcome"] != "killed"]
    evidence: dict[str, object] = {
        "schema_version": "1.0",
        "record_id": record_id,
        "task_id": task_id,
        "repository_id": task["repository_id"],
        "branch": task["branch"],
        "base_commit": task["base_commit"],
        "subject_commit": subject_commit,
        "spec_sha256": task["frozen_spec_sha256"],
        "policy_sha256": policy_sha,
        "classification_input_sha256": classification["classification_input_sha256"],
        "manifest_id": manifest.manifest_id,
        "manifest_ref": _MANIFEST_REF,
        "manifest_sha256": manifest_sha,
        "runner_source_sha256": runner_sha,
        "generated_at": generated_at,
        "main_tree_unchanged": run.main_tree_unchanged,
        "run_reason_code": run.reason_code,
        "results": results,
        "uncovered_mutation_ids": uncovered,
    }
    evidence["mutation_evidence_sha256"] = _sha256_bytes(_canonical_bytes(evidence))
    try:
        require_valid_contract("mutation-evidence", evidence)
    except ContractValidationError:
        raise
    except KeyError as error:
        raise _error(
            "Mutation evidence semantics are invalid", "MUTATION_EVIDENCE_SEMANTICS_INVALID"
        ) from error
    evidence_path = evidence_dir / "evidence.json"
    _write_new_json(evidence_path, evidence)
    return MutationEvidenceArtifact(
        record_id,
        evidence_path.relative_to(root.resolve()).as_posix(),
        str(evidence["mutation_evidence_sha256"]),
        tuple(log_refs),
    )


def record_targeted_mutation_evidence(
    repository_root: Path, task_id: str, subject_commit: str
) -> MutationEvidenceArtifact:
    """Run the fixed runner once and persist a new immutable evidence record."""
    root = Path(repository_root).resolve()
    task, classification, policy_sha = _validate_bindings(root, task_id, subject_commit)
    action_use = _consume_targeted_mutation_action(
        root, task_id, subject_commit, task, classification, policy_sha
    )
    task, classification, policy_sha = _revalidate_targeted_mutation_action(
        root, task_id, subject_commit, action_use
    )
    manifest_path = root / CANONICAL_MANIFEST_PATH
    manifest = _load_manifest(root)
    manifest_sha = _source_sha256(manifest_path)
    runner_sha = _source_sha256(root / "src/aiflow/mutation_runner.py")
    now = _utc_now()
    record_id, record_root = _reserve_record_root(root, task_id, now)
    task, classification, policy_sha = _revalidate_targeted_mutation_action(
        root, task_id, subject_commit, action_use
    )
    authorization = _issue_runner_authorization(
        root,
        task_id,
        subject_commit,
        action_sha256=action_use.action_sha256,
        receipt_path=action_use.receipt_path,
        action_path=action_use.action_path,
        decision_unit_id=action_use.decision_unit_id,
        spec_sha256=action_use.spec_sha256,
        policy_sha256=action_use.policy_sha256,
        base_commit=action_use.base_commit,
        classification_input_sha256=action_use.classification_input_sha256,
    )
    run = run_targeted_mutations(root, subject_commit, authorization=authorization)
    artifact = _make_artifact(
        root,
        task_id,
        subject_commit,
        run=run,
        now=now,
        record_id=record_id,
        record_root=record_root,
        task=task,
        classification=classification,
        policy_sha=policy_sha,
        manifest=manifest,
        manifest_sha=manifest_sha,
        runner_sha=runner_sha,
    )
    _complete_targeted_mutation_action(action_use, artifact)
    return artifact


def load_targeted_mutation_evidence(
    repository_root: Path, task_id: str, evidence_ref: str
) -> Mapping[str, object]:
    """Fail closed while loading one immutable current evidence artifact."""
    root = Path(repository_root).resolve()
    reference_match = _EVIDENCE_REF.fullmatch(evidence_ref)
    if reference_match is None or reference_match.group("task_id") != task_id:
        raise _error("Mutation evidence path is invalid", "MUTATION_EVIDENCE_PATH_INVALID")
    record_id = reference_match.group("record_id")
    path = _relative_path(evidence_ref, root=root)
    value = _read_json(path)
    try:
        require_valid_contract("mutation-evidence", value)
    except ContractValidationError:
        raise
    except KeyError as error:
        raise _error(
            "Mutation evidence semantics are invalid", "MUTATION_EVIDENCE_SEMANTICS_INVALID"
        ) from error
    digest = value.get("mutation_evidence_sha256")
    unsigned = {key: item for key, item in value.items() if key != "mutation_evidence_sha256"}
    if not isinstance(digest, str) or digest != _sha256_bytes(_canonical_bytes(unsigned)):
        raise _error("Mutation evidence digest is invalid", "MUTATION_EVIDENCE_DIGEST_INVALID")
    task, classification, policy_sha = _validate_bindings(
        root, task_id, str(value.get("subject_commit", ""))
    )
    if any(
        value.get(key) != expected
        for key, expected in (
            ("task_id", task_id),
            ("repository_id", task["repository_id"]),
            ("branch", task["branch"]),
            ("base_commit", task["base_commit"]),
            ("spec_sha256", task["frozen_spec_sha256"]),
            ("policy_sha256", policy_sha),
            ("classification_input_sha256", classification["classification_input_sha256"]),
        )
    ):
        raise _error("Mutation evidence bindings are stale", "MUTATION_EVIDENCE_BINDING_STALE")
    if value.get("record_id") != record_id or not _record_time_matches(
        record_id, value.get("generated_at")
    ):
        raise _error("Mutation evidence path is invalid", "MUTATION_EVIDENCE_PATH_INVALID")
    manifest = _load_manifest(root)
    if (
        value.get("manifest_id") != manifest.manifest_id
        or value.get("manifest_ref") != _MANIFEST_REF
        or value.get("manifest_sha256") != _source_sha256(root / CANONICAL_MANIFEST_PATH)
        or value.get("runner_source_sha256")
        != _source_sha256(root / "src/aiflow/mutation_runner.py")
    ):
        raise _error("Mutation evidence inputs are stale", "MUTATION_EVIDENCE_INPUT_MISMATCH")
    results = value.get("results")
    if not isinstance(results, list) or len(results) != len(manifest.mutations):
        raise _error("Mutation evidence results are invalid", "MUTATION_EVIDENCE_INPUT_MISMATCH")
    expected_ids = tuple(item.mutation_id for item in manifest.mutations)
    if (
        tuple(item.get("mutation_id") if isinstance(item, Mapping) else None for item in results)
        != expected_ids
    ):
        raise _error("Mutation evidence results are invalid", "MUTATION_EVIDENCE_INPUT_MISMATCH")
    recomputed_uncovered: list[str] = []
    for declaration, result in zip(manifest.mutations, results, strict=True):
        if not isinstance(result, dict) or any(
            result.get(key) != getattr(declaration, key)
            for key in (
                "mutation_id",
                "safeguard_id",
                "target",
                "target_symbol",
                "operator",
                "expected_detector",
                "expected_outcome",
            )
        ):
            raise _error(
                "Mutation evidence results are invalid", "MUTATION_EVIDENCE_INPUT_MISMATCH"
            )
        log_ref = result.get("log_ref")
        if not isinstance(log_ref, str):
            raise _error("Mutation evidence log is invalid", "MUTATION_EVIDENCE_LOG_INVALID")
        log_path = _relative_path(log_ref, root=root)
        expected_log = (
            f".ai/tasks/{task_id}/logs/{record_id}/targeted-mutation/logs/"
            f"{declaration.mutation_id}.json"
        )
        if (
            log_ref != expected_log
            or log_path.is_symlink()
            or not log_path.is_file()
            or result.get("log_sha256") != _source_sha256(log_path)
        ):
            raise _error("Mutation evidence log is invalid", "MUTATION_EVIDENCE_LOG_INVALID")
        log = _read_json(log_path)
        expected_log_value = {
            key: result.get(key)
            for key in _LOG_KEYS
            if key not in {"run_reason_code", "main_tree_unchanged"}
        }
        expected_log_value.update(
            {
                "run_reason_code": value.get("run_reason_code"),
                "main_tree_unchanged": value.get("main_tree_unchanged"),
            }
        )
        if set(log) != _LOG_KEYS or log != expected_log_value:
            raise _error("Mutation evidence log is invalid", "MUTATION_EVIDENCE_LOG_INVALID")
        timed_out = result.get("timed_out")
        duration_ms = result.get("duration_ms")
        if not isinstance(timed_out, bool) or not isinstance(duration_ms, int):
            raise _error(
                "Mutation evidence semantics are invalid", "MUTATION_EVIDENCE_SEMANTICS_INVALID"
            )
        probe = MutationProbe(
            declaration.mutation_id,
            cast(int | None, result.get("baseline_exit_code")),
            cast(int | None, result.get("mutant_exit_code")),
            timed_out,
            duration_ms,
            cast(str | None, result.get("reason_code")),
        )
        run = MutationRun(
            manifest.manifest_id,
            str(value["subject_commit"]),
            (),
            bool(value["main_tree_unchanged"]),
            value.get("run_reason_code"),
        )
        if result.get("outcome") != _derive_outcome(probe, run):
            raise _error(
                "Mutation evidence semantics are invalid", "MUTATION_EVIDENCE_SEMANTICS_INVALID"
            )
        if result.get("outcome") != "killed":
            recomputed_uncovered.append(declaration.mutation_id)
    if value.get("uncovered_mutation_ids") != recomputed_uncovered:
        raise _error(
            "Mutation evidence semantics are invalid", "MUTATION_EVIDENCE_SEMANTICS_INVALID"
        )
    return value


def consume_targeted_mutation_evidence(
    repository_root: Path,
    task_id: str,
    evidence: Mapping[str, object],
    *,
    recorded_artifact: MutationEvidenceArtifact | None = None,
) -> TargetedMutationFacts:
    """Return fail-closed V2 mutation facts from a current immutable artifact.

    The V2 projection is never trusted by itself: it must exactly match the
    public loader's current artifact replay before it can be considered killed.
    The recorder path supplies its opaque artifact identity so verification can
    derive the first projection from that same one loader replay.
    """
    projected: list[object] | None
    if recorded_artifact is not None:
        if evidence:
            return TargetedMutationFacts(
                False, "MUTATION_EVIDENCE_PROJECTION_INVALID", None, None, None, ()
            )
        evidence_ref = recorded_artifact.evidence_ref
        digest = recorded_artifact.mutation_evidence_sha256
        manifest_ref: str | None = None
        projected = None
    else:
        mutation = evidence.get("targeted_mutation")
        if not isinstance(mutation, Mapping):
            return TargetedMutationFacts(False, "MUTATION_EVIDENCE_MISSING", None, None, None, ())
        raw_evidence_ref = mutation.get("evidence_ref")
        raw_digest = mutation.get("mutation_evidence_sha256")
        manifest_ref = mutation.get("manifest_ref")
        raw_projected = mutation.get("results")
        if not isinstance(raw_evidence_ref, str) or not isinstance(raw_digest, str):
            return TargetedMutationFacts(False, "MUTATION_EVIDENCE_MISSING", None, None, None, ())
        evidence_ref = raw_evidence_ref
        digest = raw_digest
        if not isinstance(manifest_ref, str) or not isinstance(raw_projected, list):
            return TargetedMutationFacts(
                False,
                "MUTATION_EVIDENCE_PROJECTION_INVALID",
                evidence_ref,
                digest,
                None,
                (),
            )
        projected = raw_projected
    try:
        artifact = load_targeted_mutation_evidence(repository_root, task_id, evidence_ref)
    except ContractError:
        return TargetedMutationFacts(
            False, "MUTATION_EVIDENCE_INVALID", evidence_ref, digest, manifest_ref, ()
        )
    artifact_digest = artifact.get("mutation_evidence_sha256")
    artifact_manifest = artifact.get("manifest_ref")
    artifact_results = artifact.get("results")
    if (
        digest != artifact_digest
        or not isinstance(artifact_manifest, str)
        or not isinstance(artifact_results, list)
    ):
        return TargetedMutationFacts(
            False, "MUTATION_EVIDENCE_PROJECTION_INVALID", evidence_ref, digest, manifest_ref, ()
        )
    expected = tuple(
        {
            "mutation_id": item.get("mutation_id"),
            "outcome": item.get("outcome"),
            "log_ref": item.get("log_ref"),
        }
        for item in artifact_results
        if isinstance(item, Mapping)
    )
    if len(expected) != len(artifact_results):
        return TargetedMutationFacts(
            False,
            "MUTATION_EVIDENCE_PROJECTION_INVALID",
            evidence_ref,
            digest,
            artifact_manifest,
            (),
        )
    if projected is not None:
        actual = tuple(item for item in projected if isinstance(item, Mapping))
        if manifest_ref != artifact_manifest or actual != expected:
            return TargetedMutationFacts(
                False,
                "MUTATION_EVIDENCE_PROJECTION_INVALID",
                evidence_ref,
                digest,
                manifest_ref,
                (),
            )
    uncovered = artifact.get("uncovered_mutation_ids")
    if uncovered != [] or any(item.get("outcome") != "killed" for item in expected):
        return TargetedMutationFacts(
            False,
            "MUTATION_EVIDENCE_NOT_KILLED",
            evidence_ref,
            digest,
            artifact_manifest,
            expected,
        )
    return TargetedMutationFacts(True, None, evidence_ref, digest, artifact_manifest, expected)
