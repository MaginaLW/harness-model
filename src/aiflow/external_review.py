"""Read-only, bounded preflight for externally supplied review attachments.

The writer consumes a freshly prepared value; none of the functions here repair
task materialization, fetch a URL, or interpret the original report.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import signal
import stat
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import unquote, urlsplit

from aiflow.contracts import _validate_contract_with_schema_directory
from aiflow.decision_units import parse_decision_units
from aiflow.errors import AiflowError, ContractError
from aiflow.freshness import current_classification_input_digest, evaluate_freshness
from aiflow.git_context import HEAD_PATTERN, GitContext, _read_repository_id, commits_are_ancestral
from aiflow.policy import load_policy_bundle
from aiflow.review_service import build_review_context, validate_review_record
from aiflow.scope import _diff_paths, _status_paths, assess_governance_only_scope
from aiflow.specification import specification_digest
from aiflow.storage import resolve_task_path, validate_task_id
from aiflow.task_service import read_task_record_strict

MAX_ENVELOPE_BYTES = 256 * 1024
MAX_MAPPING_BYTES = 64 * 1024
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_RECORD_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 32
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_RECORD_NAME = re.compile(r"[0-9a-f]{64}\.json\Z")
_TEMP_NAME = re.compile(r"\.[0-9a-f]{64}\.tmp-[A-Za-z0-9_-]+\Z")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_AUTH = re.compile(r"(?i)(?:password|secret|token|api[_-]?key|authorization)\s*[=:]")
_DEVICE = re.compile(
    r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?\Z", re.I
)
_STATES = {
    "design": {"WAITING_FOR_SPEC_REVIEW", "READY_TO_IMPLEMENT"},
    "implementation": {"VERIFYING", "VERIFIED", "WAITING_FOR_FINAL_REVIEW", "APPROVED_FOR_MERGE"},
}


def _invalid(reason: str) -> ContractError:
    return ContractError(
        "External review input or binding is invalid", code=f"EXTERNAL_REVIEW_{reason}"
    )


def canonical_json(value: object) -> str:
    """Return the frozen canonical JSON form, never a reflective failure."""
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError, RecursionError, UnicodeError) as error:
        raise _invalid("JSON_INVALID") from error


def canonical_sha256(value: object) -> str:
    try:
        return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    except UnicodeError as error:
        raise _invalid("JSON_INVALID") from error


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class PreparedExternalReview:
    """Validated immutable candidate and safe facts consumed by the local writer."""

    repository_root: Path
    task_id: str
    series_path: Path
    target_path: Path
    guard_path: Path
    record_candidate: dict[str, Any]
    existing_record: dict[str, Any] | None
    cleanup_paths: tuple[Path, ...]
    binding: dict[str, Any]
    result: dict[str, Any]

    @property
    def no_op(self) -> bool:
        return self.existing_record is not None

    @property
    def preflight_sha256(self) -> str:
        return str(self.result["preflight_sha256"])

    @property
    def input_sha256(self) -> str:
        return str(self.result["input_sha256"])


def _lexical_path(path: Path) -> Path:
    raw = os.fspath(path)
    if _CONTROL.search(raw) or raw.replace("\\", "/").startswith("//"):
        raise _invalid("PATH_INVALID")
    windows = PureWindowsPath(raw)
    if windows.drive and not re.fullmatch(r"[A-Za-z]:", windows.drive):
        raise _invalid("PATH_INVALID")
    for part in windows.parts:
        if part == windows.anchor or part in {".", ".."}:
            continue
        if ":" in part or part.endswith((".", " ")) or _DEVICE.fullmatch(part):
            raise _invalid("PATH_INVALID")
    if os.name == "nt":
        import ctypes

        absolute = Path(os.path.abspath(raw))
        drive_type = getattr(ctypes, "windll").kernel32.GetDriveTypeW(str(absolute.anchor))
        if drive_type not in {2, 3, 5, 6}:
            raise _invalid("PATH_INVALID")
    return Path(os.path.abspath(raw))


def _io_path(path: Path) -> Path:
    """Use extended Win32 I/O only after validating the ordinary local path."""
    return Path("\\\\?\\" + str(path)) if os.name == "nt" else path


def _assert_no_links(path: Path) -> None:
    """Inspect every existing component without first following a reparse point."""
    absolute = _lexical_path(path)
    for candidate in (*reversed(absolute.parents), absolute):
        try:
            metadata = _io_path(candidate).lstat()
        except FileNotFoundError:
            break
        except OSError as error:
            raise _invalid("PATH_INVALID") from error
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 1024:
            raise _invalid("PATH_INVALID")


def _task_path(root: Path, task_id: str, relative: str = "") -> Path:
    validate_task_id(task_id)
    _assert_no_links(root / ".ai/tasks" / task_id / relative)
    return resolve_task_path(root, task_id, relative)


def _metadata_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    creation_or_change_ns = metadata.st_ctime_ns
    if os.name == "nt":
        creation_or_change_ns = getattr(metadata, "st_birthtime_ns", creation_or_change_ns)
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        creation_or_change_ns,
    )


def _read_bounded_file(path: Path, maximum: int, *, outside_task_root: Path | None = None) -> bytes:
    """Read a bounded regular file twice, rejecting replacement and growth."""
    absolute = _lexical_path(path)
    if outside_task_root is not None:
        if absolute.is_relative_to(outside_task_root):
            raise _invalid("PATH_INVALID")
        parts = [part.casefold() for part in absolute.parts]
        if any(parts[index : index + 2] == [".ai", "tasks"] for index in range(len(parts) - 1)):
            raise _invalid("PATH_INVALID")
    _assert_no_links(absolute)
    physical = _io_path(absolute)
    try:
        before = physical.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise _invalid("PATH_INVALID")
        if before.st_size > maximum:
            raise _invalid("SIZE_LIMIT")
        with physical.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if _metadata_identity(opened) != _metadata_identity(before):
                raise _invalid("INPUT_CHANGED")
            data = stream.read(maximum + 1)
            after_read = os.fstat(stream.fileno())
        if len(data) > maximum:
            raise _invalid("SIZE_LIMIT")
        _assert_no_links(absolute)
        after = physical.lstat()
        if (
            not (
                _metadata_identity(before)
                == _metadata_identity(after_read)
                == _metadata_identity(after)
            )
            or len(data) != after.st_size
        ):
            raise _invalid("INPUT_CHANGED")
        with physical.open("rb") as stream:
            if _metadata_identity(os.fstat(stream.fileno())) != _metadata_identity(before):
                raise _invalid("INPUT_CHANGED")
            repeated = stream.read(maximum + 1)
            final_handle = os.fstat(stream.fileno())
        _assert_no_links(absolute)
        if (
            _metadata_identity(final_handle) != _metadata_identity(before)
            or _metadata_identity(physical.lstat()) != _metadata_identity(before)
            or data != repeated
        ):
            raise _invalid("INPUT_CHANGED")
        return data
    except OSError as error:
        raise _invalid("INPUT_UNREADABLE") from error


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _invalid("JSON_DUPLICATE_KEY")
        value[key] = item
    return value


def _reject_constant(_value: str) -> None:
    raise _invalid("JSON_INVALID")


def _bounded_json_text(data: bytes) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeError as error:
        raise _invalid("JSON_INVALID") from error
    if text.startswith("\ufeff"):
        raise _invalid("JSON_INVALID")
    depth = 0
    quoted = escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise _invalid("DEPTH_LIMIT")
        elif character in "]}":
            depth -= 1
    return text


def _validate_json_strings(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key.encode("utf-8")
            _validate_json_strings(item)
    elif isinstance(value, list):
        for item in value:
            _validate_json_strings(item)
    elif isinstance(value, str):
        value.encode("utf-8")
    elif isinstance(value, float) and not math.isfinite(value):
        raise _invalid("JSON_INVALID")


def _load_json_bytes(data: bytes, contract_name: str, root: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            _bounded_json_text(data),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(value, dict):
            raise _invalid("JSON_INVALID")
        _validate_json_strings(value)
        errors = _validate_contract_with_schema_directory(
            contract_name, value, root / ".ai/schemas"
        )
        if errors:
            raise _invalid("CONTRACT_INVALID")
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError, TypeError) as error:
        raise _invalid("JSON_INVALID") from error


def _decoded_reference(value: str) -> str:
    if _CONTROL.search(value):
        raise _invalid("REFERENCE_INVALID")
    decoded = value
    for _attempt in range(4):
        if re.search(r"%(?![0-9A-Fa-f]{2})", decoded):
            raise _invalid("REFERENCE_INVALID")
        next_value = unquote(decoded, errors="strict")
        if next_value == decoded:
            break
        decoded = next_value
    if unquote(decoded, errors="strict") != decoded:
        raise _invalid("REFERENCE_INVALID")
    if _CONTROL.search(decoded) or "\\" in decoded or _AUTH.search(decoded):
        raise _invalid("REFERENCE_INVALID")
    return decoded


def _portable_path(value: str) -> None:
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or ":" in value
        or _CONTROL.search(value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise _invalid("REFERENCE_INVALID")


def _https_reference(value: str) -> None:
    for candidate in {value, _decoded_reference(value)}:
        parsed = urlsplit(candidate)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or "?" in candidate
            or "#" in candidate
            or "@" in candidate
            or parsed.port is not None
            or not re.fullmatch(r"[A-Za-z0-9.-]+", parsed.netloc)
        ):
            raise _invalid("REFERENCE_INVALID")
        _portable_path(parsed.path.removeprefix("/"))


def _portable_reference(value: str) -> None:
    decoded = _decoded_reference(value)
    if decoded in {"", ".", ".."}:
        raise _invalid("REFERENCE_INVALID")
    if "://" in value or "://" in decoded:
        _https_reference(value)
    elif re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]+(?::[A-Za-z0-9][A-Za-z0-9._-]*)+", decoded):
        # Portable logical references such as report:subject-header and git:base.
        return
    elif (
        value.startswith(("/", "\\"))
        or PureWindowsPath(decoded).is_absolute()
        or re.match(r"^[A-Za-z]:", decoded)
        or ":" in decoded
        or "\\" in decoded
    ):
        raise _invalid("REFERENCE_INVALID")
    elif "/" in decoded:
        _portable_path(decoded)


def _check_references(envelope: Mapping[str, Any], mapping: Mapping[str, Any] | None) -> None:
    source_repository = envelope["source_subject"]["repository"]
    if source_repository["kind"] == "repository_locator":
        _https_reference(source_repository["locator"])
    source_location = envelope["source"]["location"]
    if source_location["kind"] == "https_url":
        _https_reference(source_location["value"])
    confirmations = [envelope["source_subject"]["confirmation"]]
    if mapping is not None:
        _https_reference(mapping["locator"])
        confirmations.append(mapping["confirmation"])
    for confirmation in confirmations:
        for reference in confirmation["fact_refs"]:
            _portable_reference(reference)
    for reference in (
        *envelope["completion"]["reviewed_scope"],
        *envelope["completion"]["unreviewed_scope"],
    ):
        _portable_reference(reference)
    identifiers: set[str] = set()
    for finding in envelope["findings"]:
        identifier = finding["source_finding_id"]
        if identifier in identifiers:
            raise _invalid("FINDING_DUPLICATE")
        identifiers.add(identifier)
        _portable_path(_decoded_reference(finding["location"]["path"]))
        for reference in finding["evidence_refs"]:
            _portable_reference(reference)


def _resolve_source_repository(
    envelope: Mapping[str, Any], mapping: Mapping[str, Any] | None
) -> str:
    source = envelope["source_subject"]["repository"]
    target_id = str(envelope["target_context"]["repository_id"])
    for name in ("review_stage", "base_commit", "subject_commit"):
        if envelope["source_subject"].get(name) != envelope["target_context"].get(name):
            raise _invalid("SOURCE_MISMATCH")
    if source["kind"] == "aiflow_repository_id":
        if mapping is not None or source["repository_id"] != target_id:
            raise _invalid("SOURCE_MISMATCH")
    elif (
        mapping is None
        or mapping["mapping_record_id"] != source["mapping_record_id"]
        or mapping["locator"] != source["locator"]
        or mapping["repository_id"] != target_id
    ):
        raise _invalid("SOURCE_MISMATCH")
    return target_id


def _source_key(envelope: Mapping[str, Any], repository_id: str) -> str:
    return canonical_sha256(
        {
            "product": envelope["source"]["product"],
            "source.location": envelope["source"]["location"],
            "resolved_repository_id": repository_id,
            "source_subject.review_stage": envelope["source_subject"]["review_stage"],
        }
    )


def _version_key(envelope: Mapping[str, Any]) -> str:
    return hashlib.sha256(str(envelope["source"]["report_version"]).encode("utf-8")).hexdigest()


def _snapshot_task_files(root: Path, task_id: str) -> dict[str, str | None]:
    paths = {
        "task.yaml": MAX_RECORD_BYTES,
        "events.jsonl": 32 * 1024 * 1024,
        "spec.md": MAX_RECORD_BYTES,
        "classification.json": MAX_RECORD_BYTES,
        "evidence.json": 16 * 1024 * 1024,
        "approvals.json": 16 * 1024 * 1024,
    }
    result: dict[str, str | None] = {}
    pending = _task_path(root, task_id, "task.yaml.next")
    _assert_no_links(pending)
    if pending.exists():
        raise _invalid("TASK_PENDING")
    for name, maximum in paths.items():
        path = _task_path(root, task_id, name)
        _assert_no_links(path)
        if name in {"evidence.json", "approvals.json"} and not path.exists():
            result[name] = None
        else:
            result[name] = _bytes_sha256(_read_bounded_file(path, maximum))
    return result


def _cleanup_read_only_git(process: subprocess.Popen[bytes]) -> tuple[bytes, bytes] | None:
    """Bound owned cleanup waits without replacing the initiating exception."""
    if os.name == "nt":
        try:
            if process.poll() is None:
                taskkill = Path(os.environ["SystemRoot"]) / "System32" / "taskkill.exe"
                helper = subprocess.Popen(
                    [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW"),
                )
                try:
                    helper.wait(timeout=5)
                except BaseException:
                    try:
                        helper.kill()
                    except BaseException:
                        pass
                    try:
                        helper.wait(timeout=1)
                    except BaseException:
                        pass
        except BaseException:
            pass
    else:
        try:
            # A reaped parent's numeric group may already belong to another process.
            if process.poll() is None:
                kill_group = getattr(os, "killpg")
                kill_signal = getattr(signal, "SIGKILL")
                kill_group(process.pid, kill_signal)
        except BaseException:
            pass
    try:
        process.kill()
    except BaseException:
        pass
    try:
        return process.communicate(timeout=5)
    except BaseException:
        return None


def _read_only_git(root: Path, *arguments: str) -> bytes:
    """Read binary Git output with a local environment and owned bounded cleanup."""
    process: subprocess.Popen[bytes] | None = None
    drained = False
    streams_closed = False
    try:
        process = subprocess.Popen(
            ["git", "--no-optional-locks", *arguments],
            cwd=root,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name != "nt",
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP") if os.name == "nt" else 0,
        )
        stdout, _stderr = process.communicate(timeout=10)
        drained = True
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        streams_closed = True
        if process.returncode != 0:
            raise _invalid("GIT_BINDING_STALE")
        return stdout
    except BaseException as original:
        if process is not None and not drained:
            try:
                drained = _cleanup_read_only_git(process) is not None
            except BaseException:
                pass
        if isinstance(original, (OSError, subprocess.TimeoutExpired)):
            raise _invalid("GIT_BINDING_STALE") from original
        raise
    finally:
        if drained and not streams_closed and process is not None:
            # Undrained Windows readers can retain a stream lock: do not close them.
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except BaseException:
                        pass


def _read_only_checkout(root: Path) -> tuple[GitContext, tuple[str, ...]]:
    # rev-parse preserves Git's canonical, disambiguated short branch name.
    checkout = _read_only_git(
        root, "rev-parse", "--show-toplevel", "HEAD", "--abbrev-ref=loose", "HEAD"
    )
    lines = checkout.removesuffix(b"\n").split(b"\n")
    if len(lines) not in {2, 3}:
        raise _invalid("GIT_BINDING_STALE")
    actual_root = Path(lines[0].decode().strip())
    head = lines[1].decode().strip()
    branch = lines[2].decode().strip() if len(lines) == 3 else "HEAD"
    if branch == "HEAD":
        # Ambiguous raw refs named HEAD can suppress rev-parse's abbreviation.
        # Preserve the previous symbolic-ref result; detached HEAD still fails.
        branch = _read_only_git(root, "symbolic-ref", "--short", "-q", "HEAD").decode().strip()
    if (
        actual_root.resolve() != root
        or HEAD_PATTERN.fullmatch(head) is None
        or not branch
        or _CONTROL.search(branch)
        or " " in branch
    ):
        raise _invalid("GIT_BINDING_STALE")
    _assert_no_links(root / ".ai/repository-id")
    dirty = tuple(
        sorted(
            _status_paths(
                _read_only_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
            )
        )
    )
    return GitContext(
        _read_repository_id(root), root.as_posix(), branch, head, bool(dirty), dirty
    ), dirty


def _current_target(
    root: Path,
    task_id: str,
    envelope: Mapping[str, Any],
    ignored: set[str],
    *,
    unchanged_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = read_task_record_strict(root, task_id)
    task = record.task
    stage = str(envelope["target_context"]["review_stage"])
    if task.get("current_state") not in _STATES[stage]:
        raise _invalid("STATE_INVALID")
    git, dirty = _read_only_checkout(root)
    base, subject = task.get("base_commit"), task.get("subject_commit")
    if (
        git.repository_id != task.get("repository_id")
        or git.branch != task.get("branch")
        or not isinstance(base, str)
        or not isinstance(subject, str)
        or not commits_are_ancestral(
            root, base_commit=base, subject_commit=subject, head_commit=git.head
        )
    ):
        raise _invalid("GIT_BINDING_STALE")
    attestation = (
        tuple(
            sorted(
                _diff_paths(
                    _read_only_git(
                        root,
                        "diff",
                        "--name-status",
                        "-z",
                        "--find-renames",
                        "--find-copies",
                        subject,
                        git.head,
                    )
                )
            )
        )
        if subject != git.head
        else ()
    )
    dirty_paths = [path for path in dirty if path not in ignored]
    if not assess_governance_only_scope(
        (*attestation, *dirty_paths), task_id=task_id, repository_root=root
    ).passed:
        raise _invalid("GIT_BINDING_STALE")
    context = (
        dict(build_review_context(root, task_id, stage))
        if unchanged_context is None
        else unchanged_context
    )
    policy_sha = load_policy_bundle(root).sha256
    if context["policy_sha256"] != policy_sha:
        raise _invalid("INPUT_CHANGED")
    spec_bytes = _read_bounded_file(_task_path(root, task_id, "spec.md"), MAX_RECORD_BYTES)
    spec_sha = specification_digest(spec_bytes.decode("utf-8"))
    if spec_sha != task.get("frozen_spec_sha256") or context["spec_sha256"] != spec_sha:
        raise _invalid("SPEC_STALE")
    classification = _load_json_bytes(
        _read_bounded_file(_task_path(root, task_id, "classification.json"), MAX_RECORD_BYTES),
        "classification",
        root,
    )
    _digest, synchronized = current_classification_input_digest(
        task, parse_decision_units(task), classification, record.events
    )
    facts = {
        **context,
        "subject_commit": subject,
        "subject_synchronized": synchronized,
        "classification_input_sha256": _digest,
        "verification_level": classification["effective_verification_level"],
        "attestation_head": git.head,
        "governance_only": True,
        "attestation_governance_only": True,
    }
    if evaluate_freshness("classification", classification, facts).status != "fresh":
        raise _invalid("CLASSIFICATION_STALE")
    if stage == "implementation":
        evidence = _load_json_bytes(
            _read_bounded_file(_task_path(root, task_id, "evidence.json"), 16 * 1024 * 1024),
            "evidence",
            root,
        )
        if evaluate_freshness("evidence", evidence, facts).status != "fresh":
            raise _invalid("EVIDENCE_STALE")
    target = envelope["target_context"]
    for name in ("task_id", "repository_id", "review_stage", "base_commit", "context_sha256"):
        if target.get(name) != context.get(name):
            raise _invalid("TARGET_MISMATCH")
    if target.get("subject_commit") != context.get("subject_commit"):
        raise _invalid("TARGET_MISMATCH")
    git_binding = {
        "repository_id": git.repository_id,
        "branch": git.branch,
        "head": git.head,
        "attestation": list(attestation),
        "dirty_paths": sorted(dirty_paths),
        "policy_sha256": policy_sha,
    }
    return context, git_binding


def _finding_reference_bindings(
    root: Path, task_id: str, envelope: Mapping[str, Any], context: Mapping[str, Any]
) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for finding in envelope["findings"]:
        mapping = finding["mapping"]
        if mapping["status"] == "pending":
            continue
        if mapping["task_id"] != task_id:
            raise _invalid("FINDING_MISMATCH")
        relative = f"reviews/{mapping['review_id']}-r{mapping['revision']:04d}.json"
        raw = _read_bounded_file(_task_path(root, task_id, relative), MAX_RECORD_BYTES)
        review = _load_json_bytes(raw, "review-record", root)
        if (
            review["review_id"] != mapping["review_id"]
            or review["revision"] != mapping["revision"]
            or review["review_stage"] != context["review_stage"]
            or review["context_sha256"] != context["context_sha256"]
        ):
            raise _invalid("FINDING_MISMATCH")
        context_relative = f"review-contexts/{review['context_sha256']}.json"
        raw_context = _read_bounded_file(
            _task_path(root, task_id, context_relative), MAX_RECORD_BYTES
        )
        referenced = _load_json_bytes(raw_context, "review-context", root)
        validate_review_record(review, referenced)
        if any(referenced.get(name) != value for name, value in context.items()) or not any(
            item["finding_id"] == mapping["finding_id"] for item in review["findings"]
        ):
            raise _invalid("FINDING_MISMATCH")
        bindings[relative] = _bytes_sha256(raw)
        bindings[context_relative] = _bytes_sha256(raw_context)
    return bindings


def _load_series_history(
    root: Path,
    task_id: str,
    series: Path,
    source_key: str,
    version_key: str,
    ignored_runtime_paths: set[Path],
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any], tuple[Path, ...]]:
    _assert_no_links(series)
    guard = series.parent / f".{source_key}.lock"
    _assert_no_links(guard)
    cleanup: list[Path] = []
    runtime: dict[str, str] = {}
    if _io_path(guard).exists() and guard not in ignored_runtime_paths:
        cleanup.append(guard)
        runtime[guard.name] = _bytes_sha256(_read_bounded_file(guard, MAX_MAPPING_BYTES))
    if not _io_path(series).exists():
        return None, None, {"records": {}, "runtime": runtime}, tuple(cleanup)
    if not _io_path(series).is_dir():
        raise _invalid("HISTORY_INVALID")
    paths = sorted(series / child.name for child in _io_path(series).iterdir())
    entries: dict[str, dict[str, Any]] = {}
    by_digest: dict[str, str] = {}
    existing: dict[str, Any] | None = None
    for path in paths:
        _assert_no_links(path)
        if path in ignored_runtime_paths:
            continue
        if _TEMP_NAME.fullmatch(path.name):
            cleanup.append(path)
            runtime[path.name] = _bytes_sha256(_read_bounded_file(path, MAX_RECORD_BYTES))
            continue
        if not _RECORD_NAME.fullmatch(path.name):
            raise _invalid("HISTORY_INVALID")
        raw = _read_bounded_file(path, MAX_RECORD_BYTES)
        value = _load_json_bytes(raw, "external-review-import", root)
        saved_envelope = value["envelope"]
        saved_mapping = value["repository_mapping"]
        _check_references(saved_envelope, saved_mapping)
        saved_repository = _resolve_source_repository(saved_envelope, saved_mapping)
        if (
            value["source_key_sha256"] != source_key
            or _source_key(saved_envelope, saved_repository) != source_key
            or saved_envelope["target_context"]["task_id"] != task_id
            or path.name != f"{_version_key(saved_envelope)}.json"
            or value["input_sha256"]
            != canonical_sha256(
                {
                    "envelope": saved_envelope,
                    "repository_mapping": saved_mapping,
                }
            )
        ):
            raise _invalid("HISTORY_INVALID")
        digest = canonical_sha256(value)
        if digest in by_digest:
            raise _invalid("HISTORY_INVALID")
        by_digest[digest] = path.name
        entries[path.name] = {
            "raw_sha256": _bytes_sha256(raw),
            "record_sha256": digest,
            "previous_record_sha256": value.get("previous_record_sha256"),
            # Archived references bind their saved target, which can precede the
            # current context. Their bytes remain part of the drift token.
            "finding_references": _finding_reference_bindings(
                root, task_id, saved_envelope, saved_envelope["target_context"]
            ),
        }
        if path.name == f"{version_key}.json":
            existing = value
    if sorted(series / child.name for child in _io_path(series).iterdir()) != paths:
        raise _invalid("INPUT_CHANGED")
    previous_values = [entry["previous_record_sha256"] for entry in entries.values()]
    if entries and (
        previous_values.count(None) != 1
        or len([item for item in previous_values if item is not None])
        != len({item for item in previous_values if item is not None})
        or any(item is not None and item not in by_digest for item in previous_values)
    ):
        raise _invalid("HISTORY_INVALID")
    heads = set(by_digest) - set(previous_values)
    if entries and len(heads) != 1:
        raise _invalid("HISTORY_INVALID")
    head = next(iter(heads)) if heads else None
    seen: set[str] = set()
    cursor = head
    while cursor is not None:
        if cursor in seen:
            raise _invalid("HISTORY_INVALID")
        seen.add(cursor)
        cursor = entries[by_digest[cursor]]["previous_record_sha256"]
    if len(seen) != len(entries):
        raise _invalid("HISTORY_INVALID")
    return existing, head, {"records": entries, "runtime": runtime}, tuple(cleanup)


def _prepare_external_review(
    repository_root: Path,
    task_id: str,
    envelope_path: Path,
    report_path: Path,
    *,
    repository_mapping_path: Path | None = None,
    ignored_runtime_paths: Sequence[Path] = (),
) -> PreparedExternalReview:
    """Prepare fresh input and bindings, omitting only writer-owned guard/temp paths."""
    try:
        root = _lexical_path(repository_root)
        _assert_no_links(root / ".ai/tasks")
        task_directory = _task_path(root, task_id)
        _assert_no_links(task_directory)
        envelope_bytes = _read_bounded_file(
            envelope_path, MAX_ENVELOPE_BYTES, outside_task_root=root / ".ai/tasks"
        )
        envelope = _load_json_bytes(envelope_bytes, "external-review", root)
        report_bytes = _read_bounded_file(
            report_path, MAX_REPORT_BYTES, outside_task_root=root / ".ai/tasks"
        )
        if not report_bytes or _bytes_sha256(report_bytes) != envelope["source"]["raw_sha256"]:
            raise _invalid("REPORT_MISMATCH")
        mapping_bytes = None
        mapping = None
        if repository_mapping_path is not None:
            mapping_bytes = _read_bounded_file(
                repository_mapping_path, MAX_MAPPING_BYTES, outside_task_root=root / ".ai/tasks"
            )
            mapping = _load_json_bytes(mapping_bytes, "external-review-repository-mapping", root)
        _check_references(envelope, mapping)
        repository_id = _resolve_source_repository(envelope, mapping)
        source_key = _source_key(envelope, repository_id)
        version_key = _version_key(envelope)
        series = _task_path(root, task_id, f"external-reviews/{source_key}")
        target = series / f"{version_key}.json"
        guard = series.parent / f".{source_key}.lock"
        ignored: set[Path] = set()
        for path in ignored_runtime_paths:
            absolute = _lexical_path(path)
            if absolute != guard and not (
                absolute.parent == series and _TEMP_NAME.fullmatch(absolute.name)
            ):
                raise _invalid("RUNTIME_PATH_INVALID")
            ignored.add(absolute)
        ignored_names = {path.relative_to(root).as_posix() for path in ignored}
        task_binding = _snapshot_task_files(root, task_id)
        context, git_binding = _current_target(root, task_id, envelope, ignored_names)
        finding_bindings = _finding_reference_bindings(root, task_id, envelope, context)
        existing, head, history, cleanup = _load_series_history(
            root, task_id, series, source_key, version_key, ignored
        )
        input_sha = canonical_sha256({"envelope": envelope, "repository_mapping": mapping})
        candidate: dict[str, Any] = {
            "kind": "external-review-import",
            "schema_version": "1.0",
            "source_key_sha256": source_key,
            "input_sha256": input_sha,
            "envelope": envelope,
            "repository_mapping": mapping,
        }
        if existing is not None:
            if (
                existing["input_sha256"] != input_sha
                or existing["envelope"] != envelope
                or existing["repository_mapping"] != mapping
            ):
                raise _invalid("IMMUTABLE_CONFLICT")
            candidate = existing
        elif head is not None:
            candidate["previous_record_sha256"] = head
        if _validate_contract_with_schema_directory(
            "external-review-import", candidate, root / ".ai/schemas"
        ):
            raise _invalid("CONTRACT_INVALID")
        if task_binding != _snapshot_task_files(root, task_id):
            raise _invalid("INPUT_CHANGED")
        # Only the pure context calculation is reused inside this fresh preparation.
        # Its complete task inputs are byte-bound before and after the second read;
        # Git, Policy, strict task state, freshness and referenced artifacts are reread.
        repeated_context, repeated_git = _current_target(
            root, task_id, envelope, ignored_names, unchanged_context=context
        )
        if (
            task_binding != _snapshot_task_files(root, task_id)
            or context != repeated_context
            or git_binding != repeated_git
            or finding_bindings != _finding_reference_bindings(root, task_id, envelope, context)
            or envelope_bytes
            != _read_bounded_file(
                envelope_path, MAX_ENVELOPE_BYTES, outside_task_root=root / ".ai/tasks"
            )
            or report_bytes
            != _read_bounded_file(
                report_path, MAX_REPORT_BYTES, outside_task_root=root / ".ai/tasks"
            )
        ):
            raise _invalid("INPUT_CHANGED")
        if repository_mapping_path is not None and mapping_bytes != _read_bounded_file(
            repository_mapping_path, MAX_MAPPING_BYTES, outside_task_root=root / ".ai/tasks"
        ):
            raise _invalid("INPUT_CHANGED")
        _existing_again, _head_again, repeated_history, repeated_cleanup = _load_series_history(
            root, task_id, series, source_key, version_key, ignored
        )
        if history != repeated_history or cleanup != repeated_cleanup:
            raise _invalid("INPUT_CHANGED")
        binding = {
            "schema_version": "1.0",
            "input_sha256": input_sha,
            "input_bytes": {
                "envelope_sha256": _bytes_sha256(envelope_bytes),
                "report_sha256": _bytes_sha256(report_bytes),
                "repository_mapping_sha256": _bytes_sha256(mapping_bytes)
                if mapping_bytes is not None
                else None,
            },
            "task_files": task_binding,
            "context_sha256": context["context_sha256"],
            "git": git_binding,
            "finding_references": finding_bindings,
            "history": history,
        }
        result = {
            "status": "cleanup_required"
            if cleanup
            else "already_recorded"
            if existing
            else "ready",
            "reason_codes": ["EXTERNAL_REVIEW_CLEANUP_REQUIRED"] if cleanup else [],
            "task_id": task_id,
            "review_stage": context["review_stage"],
            "context_sha256": context["context_sha256"],
            "input_sha256": input_sha,
            "source_key_sha256": source_key,
            "record_path": target.relative_to(root).as_posix(),
            "preflight_sha256": canonical_sha256(binding),
        }
        return PreparedExternalReview(
            root, task_id, series, target, guard, candidate, existing, cleanup, binding, result
        )
    except AiflowError as error:
        if error.code.startswith("EXTERNAL_REVIEW_"):
            raise
        raise _invalid("BINDING_INVALID") from error
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        raise _invalid("INPUT_INVALID") from error


def preflight_external_review(
    repository_root: Path,
    task_id: str,
    envelope_path: Path,
    report_path: Path,
    *,
    repository_mapping_path: Path | None = None,
) -> dict[str, Any]:
    """Return the safe preflight protocol without creating or changing task files."""
    return dict(
        _prepare_external_review(
            repository_root,
            task_id,
            envelope_path,
            report_path,
            repository_mapping_path=repository_mapping_path,
        ).result
    )


def _publish_create_only(temporary_path: Path, target_path: Path) -> None:
    """Publish one complete file atomically, without replacing any existing name."""
    _assert_no_links(temporary_path)
    _assert_no_links(target_path)
    os.link(_io_path(temporary_path), _io_path(target_path))


def _cleanup_runtime_paths(paths: tuple[Path, ...], created_directories: tuple[Path, ...]) -> bool:
    cleaned = True
    for path in reversed(paths):
        try:
            _assert_no_links(path)
            _io_path(path).unlink(missing_ok=True)
        except (OSError, AiflowError):
            cleaned = False
    for directory in reversed(created_directories):
        try:
            _assert_no_links(directory)
            physical = _io_path(directory)
            if physical.exists() and not any(physical.iterdir()):
                physical.rmdir()
        except (OSError, AiflowError):
            cleaned = False
    return cleaned


def _same_token_after_competing_commit(prepared: PreparedExternalReview, expected: str) -> bool:
    """Accept only the identical target added to the precise previously bound history."""
    if not prepared.no_op or prepared.cleanup_paths:
        return False
    binding = json.loads(canonical_json(prepared.binding))
    records = binding["history"]["records"]
    entry = records.pop(prepared.target_path.name, None)
    if entry is None or any(
        other["previous_record_sha256"] == entry["record_sha256"] for other in records.values()
    ):
        return False
    relative = prepared.target_path.relative_to(prepared.repository_root).as_posix()
    binding["git"]["dirty_paths"] = [
        path for path in binding["git"]["dirty_paths"] if path != relative
    ]
    return canonical_sha256(binding) == expected


def record_external_review(
    repository_root: Path,
    task_id: str,
    envelope_path: Path,
    report_path: Path,
    *,
    repository_mapping_path: Path | None = None,
    expected_preflight_sha256: str,
) -> dict[str, Any]:
    """Revalidate the token and append one immutable attachment under a source guard."""
    if not _HEX.fullmatch(expected_preflight_sha256):
        raise _invalid("TOKEN_INVALID")
    prepared = _prepare_external_review(
        repository_root,
        task_id,
        envelope_path,
        report_path,
        repository_mapping_path=repository_mapping_path,
    )
    if prepared.cleanup_paths:
        raise _invalid("CLEANUP_REQUIRED")
    if prepared.preflight_sha256 != expected_preflight_sha256 and not (
        _same_token_after_competing_commit(prepared, expected_preflight_sha256)
    ):
        raise _invalid("PREFLIGHT_STALE")
    if prepared.no_op:
        return {**prepared.result, "status": "no_op"}

    created_directories: list[Path] = []
    runtime_paths: list[Path] = []
    committed = False
    failure: AiflowError | None = None
    temporary = prepared.series_path / (f".{prepared.target_path.stem}.tmp-{secrets.token_hex(16)}")
    try:
        for directory in (prepared.series_path.parent,):
            _assert_no_links(directory)
            try:
                _io_path(directory).mkdir()
                created_directories.append(directory)
            except FileExistsError:
                if not _io_path(directory).is_dir():
                    raise _invalid("PATH_INVALID")
        _assert_no_links(prepared.guard_path)
        with _io_path(prepared.guard_path).open("xb") as guard:
            runtime_paths.append(prepared.guard_path)
            guard.write(b'{"kind":"external-review-source-guard"}\n')
            guard.flush()
            os.fsync(guard.fileno())
        fresh = _prepare_external_review(
            repository_root,
            task_id,
            envelope_path,
            report_path,
            repository_mapping_path=repository_mapping_path,
            ignored_runtime_paths=(prepared.guard_path,),
        )
        if fresh.cleanup_paths:
            raise _invalid("CLEANUP_REQUIRED")
        if fresh.preflight_sha256 != expected_preflight_sha256:
            if _same_token_after_competing_commit(fresh, expected_preflight_sha256):
                prepared = fresh
            else:
                raise _invalid("PREFLIGHT_STALE")
        else:
            prepared = fresh
        if not prepared.no_op:
            _assert_no_links(prepared.series_path)
            try:
                _io_path(prepared.series_path).mkdir()
                created_directories.append(prepared.series_path)
            except FileExistsError:
                if not _io_path(prepared.series_path).is_dir():
                    raise _invalid("PATH_INVALID")
            _assert_no_links(temporary)
            with _io_path(temporary).open("xb") as stream:
                runtime_paths.append(temporary)
                stream.write((canonical_json(prepared.record_candidate) + "\n").encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            final = _prepare_external_review(
                repository_root,
                task_id,
                envelope_path,
                report_path,
                repository_mapping_path=repository_mapping_path,
                ignored_runtime_paths=(prepared.guard_path, temporary),
            )
            if final.preflight_sha256 != prepared.preflight_sha256 or final.cleanup_paths:
                raise _invalid("PREFLIGHT_STALE")
            try:
                _publish_create_only(temporary, prepared.target_path)
                committed = True
            except FileExistsError:
                competing = _prepare_external_review(
                    repository_root,
                    task_id,
                    envelope_path,
                    report_path,
                    repository_mapping_path=repository_mapping_path,
                    ignored_runtime_paths=(prepared.guard_path, temporary),
                )
                if not _same_token_after_competing_commit(competing, prepared.preflight_sha256):
                    raise _invalid("PREFLIGHT_STALE")
                prepared = competing
    except AiflowError as error:
        failure = error
    except (OSError, ValueError) as error:
        failure = _invalid("PUBLICATION_FAILED")
        failure.__cause__ = error
    cleaned = _cleanup_runtime_paths(tuple(runtime_paths), tuple(created_directories))
    if committed:
        return {
            **prepared.result,
            "status": "recorded",
            "reason_codes": [] if cleaned else ["EXTERNAL_REVIEW_COMMITTED_CLEANUP_REQUIRED"],
        }
    if not cleaned:
        raise _invalid("PRECOMMIT_CLEANUP_REQUIRED") from failure
    if failure is not None:
        raise failure
    return {**prepared.result, "status": "no_op"}
