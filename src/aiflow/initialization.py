"""Reviewed, non-overwriting installation of repository-owned seed resources.

Digests bind bytes and observed facts; they do not authenticate an actor or grant
permission. Installation never imports the source repository's identity/history.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tomllib
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml

from aiflow import initialization_git as git
from aiflow.contracts import schema_directory_context
from aiflow.errors import AiflowError
from aiflow.initialization_windows import WindowsFilesystem
from aiflow.policy import POLICY_FILES, _UniqueKeyLoader, load_policy_bundle
from aiflow.resource_bundle import (
    BUNDLE_VERSION,
    CLI_VERSION,
    MAX_BUNDLE_BYTES,
    MAX_RESOURCE_BYTES,
    RESOURCE_KINDS,
    read_bundle,
)
from aiflow.verification import VerificationContext, parse_verification_plan

PROFILE = "native-python-v1"
MAX_JSON_BYTES = 64 * 1024
STATE = ".ai/init-state.json"
REVIEW = ".ai/policy-review.json"
COMPLETE = ".ai/init-complete.json"
PENDING = ".ai/.repository-id.pending"
IDENTITY = ".ai/repository-id"
DIRECTORIES = (".ai", ".ai/policy", ".ai/schemas", ".ai/templates")
RUNTIME_DIRECTORIES = frozenset({"tasks", "mutations"})
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _error(reason: str) -> AiflowError:
    return AiflowError("Initialization rejected: " + reason, code="INITIALIZATION_" + reason)


def _json(value: object) -> bytes:
    try:
        result = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False
        ).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise _error("JSON_INVALID") from error
    if len(result) > MAX_JSON_BYTES:
        raise _error("JSON_TOO_LARGE")
    return result


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: object) -> str:
    return _sha(_json(value))


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _error("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def read_initialization_json(path: Path) -> dict[str, Any]:
    """Read one bounded strict CLI input without accepting duplicate JSON keys."""
    try:
        value = json.loads(_read(path, MAX_JSON_BYTES).decode("utf-8"), object_pairs_hook=_unique)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise _error("JSON_INVALID") from error
    if not isinstance(value, dict):
        raise _error("JSON_INVALID")
    _json(value)
    return value


def _plain(path: Path, *, directory: bool | None = None) -> os.stat_result:
    try:
        for component in (*reversed(path.absolute().parents), path.absolute()):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise _error("PATH_LINK")
            if component != path.absolute() and not stat.S_ISDIR(info.st_mode):
                raise _error("PATH_TYPE")
        if directory is True and not stat.S_ISDIR(info.st_mode):
            raise _error("PATH_TYPE")
        if directory is False and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
            raise _error("PATH_TYPE")
        return info
    except OSError as error:
        raise _error("PATH_UNAVAILABLE") from error


def _read(path: Path, limit: int) -> bytes:
    before = _plain(path, directory=False)
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
            opened = os.fstat(stream.fileno())
        after = _plain(path, directory=False)
    except OSError as error:
        raise _error("READ_FAILED") from error
    if len(data) > limit:
        raise _error("READ_TOO_LARGE")

    def facts(item: os.stat_result) -> tuple[int, int, int, int]:
        return item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns

    if facts(before) != facts(opened) or facts(before) != facts(after):
        raise _error("READ_CHANGED")
    return data


def _profile(profile: object) -> None:
    if profile != PROFILE or not isinstance(profile, str):
        raise _error("PROFILE_UNSUPPORTED")


def _entries(directory: Path, limit: int) -> list[Path]:
    result: list[Path] = []
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if len(result) >= limit:
                    raise _error("INVENTORY_TOO_LARGE")
                result.append(Path(entry.path))
    except OSError as error:
        raise _error("INVENTORY_UNAVAILABLE") from error
    return result


def _project(root: Path) -> None:
    if any(entry.name.casefold() == "package.json" for entry in _entries(root, 10_000)):
        raise _error("TARGET_PROFILE_UNSUPPORTED")
    try:
        project = tomllib.loads(_read(root / "pyproject.toml", MAX_JSON_BYTES).decode("utf-8"))
        name = project.get("project", {}).get("name")
    except (ValueError, TypeError, AttributeError, UnicodeError) as error:
        raise _error("TARGET_PROFILE_UNSUPPORTED") from error
    if not isinstance(name, str) or not name.strip():
        raise _error("TARGET_PROFILE_UNSUPPORTED")


def _source_fact(path: Path, *, directory: bool = False) -> dict[str, Any]:
    info = _plain(path, directory=directory)
    result = {"path": str(path.absolute()), "device": info.st_dev, "inode": info.st_ino}
    if not directory:
        result.update(size=info.st_size, mtime_ns=info.st_mtime_ns)
    return result


def _materials(
    root: Path, bundle_root: Path | None, policy_directory: Path | None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes], list[dict[str, Any]]]:
    candidate = (
        files("aiflow").joinpath("_bundled_resources") if bundle_root is None else bundle_root
    )
    if not isinstance(candidate, Path):
        raise _error("BUNDLE_FILESYSTEM_REQUIRED")
    bundle = candidate.absolute()
    selected = bundle / "policy" if policy_directory is None else policy_directory.absolute()
    sources = [bundle, selected]
    source_files = [bundle / "manifest.json", *(bundle / name for name in RESOURCE_KINDS)]
    source_files.extend(selected / name for name in POLICY_FILES)

    def source_facts() -> list[dict[str, Any]]:
        return [
            *(_source_fact(path, directory=True) for path in sources),
            *(_source_fact(path) for path in source_files),
        ]

    before = source_facts()
    try:
        manifest, resources = read_bundle(bundle)
        if {entry.name for entry in _entries(selected, 4)} != set(POLICY_FILES):
            raise _error("POLICY_FILES_INVALID")
        for name in POLICY_FILES:
            data = _read(selected / name, MAX_RESOURCE_BYTES).replace(b"\r\n", b"\n")
            if b"\r" in data:
                raise _error("POLICY_ENCODING_INVALID")
            yaml.load(data.decode("utf-8"), Loader=_UniqueKeyLoader)
            resources["policy/" + name] = data
        if sum(len(data) for data in resources.values()) > MAX_BUNDLE_BYTES:
            raise _error("BUNDLE_TOO_LARGE")
        with schema_directory_context(bundle / "schemas"):
            policy = load_policy_bundle(root, policy_directory=selected)
            context = VerificationContext(root, "TASK-0001", "0" * 40, "0" * 40, "python", "init")
            # Pure structural validation. This callback never probes tools/import hooks.
            for level in ("V0", "V1", "V2"):
                parse_verification_plan(policy, context, level=level, tool_available=lambda _: True)
        for name in POLICY_FILES:
            current = _read(selected / name, MAX_RESOURCE_BYTES).replace(b"\r\n", b"\n")
            if current != resources["policy/" + name]:
                raise _error("SOURCE_CHANGED")
    except (ValueError, OSError, UnicodeError, yaml.YAMLError, RecursionError) as error:
        raise _error("BUNDLE_OR_POLICY_INVALID") from error
    if source_facts() != before:
        raise _error("SOURCE_CHANGED")
    bundle_projection = {
        "cli_version": CLI_VERSION,
        "bundle_version": manifest["bundle_version"],
        "manifest_sha256": _digest(manifest),
    }
    policy_projection = {
        "policy_version": policy.policy_version,
        "semantic_sha256": policy.sha256,
        "files": [
            {
                "path": "policy/" + name,
                "size": len(resources["policy/" + name]),
                "sha256": _sha(resources["policy/" + name]),
            }
            for name in sorted(POLICY_FILES)
        ],
    }
    return bundle_projection, policy_projection, resources, before


def _objects(resources: Mapping[str, bytes], repository_id: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = [{"path": path, "type": "directory"} for path in DIRECTORIES]
    result.extend(
        {"path": ".ai/" + path, "type": "file", "size": len(data), "sha256": _sha(data)}
        for path, data in resources.items()
    )
    result.extend(
        {"path": path, "type": "file", "derivation": derivation}
        for path, derivation in (
            (STATE, "state-v1"),
            (REVIEW, "policy-review-v1"),
            (COMPLETE, "complete-v1"),
        )
    )
    identifier = (repository_id + "\n").encode()
    result.extend(
        {
            "path": path,
            "type": "file",
            "size": len(identifier),
            "sha256": _sha(identifier),
            "phase": phase,
        }
        for path, phase in ((PENDING, "pending"), (IDENTITY, "complete"))
    )
    return sorted(result, key=lambda item: item["path"])


def _no_ai(root: Path) -> None:
    if any(entry.name.casefold() == ".ai" for entry in _entries(root, 10_000)):
        raise _error("EXISTING_AI")


def preview_initialization(
    target: Path,
    *,
    bundle_root: Path | None = None,
    policy_directory: Path | None = None,
    profile: str = PROFILE,
) -> dict[str, Any]:
    """Return a local, zero-write proposal; the caller saves/reviews it outside target."""
    _profile(profile)
    observed = git.observe_initialization_target(Path(target))
    if observed["python_source_count"] < 1:
        raise _error("TARGET_PROFILE_UNSUPPORTED")
    root = Path(observed["root"])
    _no_ai(root)
    _project(root)
    bundle, policy, resources, sources = _materials(root, bundle_root, policy_directory)
    observed = {**observed, "resource_sources": sources}
    identifier = str(uuid4())
    preview = {
        "schema_version": "1.0",
        "kind": "aiflow-init-preview",
        "repository_id": identifier,
        "profile": profile,
        "target": observed,
        "bundle": bundle,
        "policy": policy,
        "objects": _objects(resources, identifier),
    }
    return {**preview, "preview_sha256": _digest(preview)}


def _mapping(value: object, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise _error("INPUT_FIELDS_INVALID")
    result = dict(value)
    _json(result)
    return result


def _identifier(value: object) -> str:
    try:
        parsed = UUID(str(value))
    except (ValueError, TypeError, AttributeError) as error:
        raise _error("IDENTITY_INVALID") from error
    if parsed.version != 4 or str(parsed) != value:
        raise _error("IDENTITY_INVALID")
    return str(parsed)


def _review(preview: Mapping[str, Any], value: object) -> dict[str, Any]:
    decision = _mapping(
        value,
        {
            "schema_version",
            "kind",
            "preview_sha256",
            "repository_id",
            "profile",
            "policy_version",
            "policies",
            "reviewer",
            "outcome",
        },
    )
    expected = {
        "schema_version": "1.0",
        "kind": "aiflow-policy-review",
        "preview_sha256": preview["preview_sha256"],
        "repository_id": preview["repository_id"],
        "profile": preview["profile"],
        "policy_version": preview["policy"]["policy_version"],
        "policies": [
            {"path": entry["path"], "sha256": entry["sha256"]}
            for entry in preview["policy"]["files"]
        ],
        "outcome": "APPROVE",
    }
    reviewer = decision["reviewer"]
    if (
        not isinstance(reviewer, str)
        or not reviewer.strip()
        or len(reviewer.encode()) > 128
        or any(ord(character) < 32 for character in reviewer)
        or any(character in reviewer for character in "\\:")
    ):
        raise _error("POLICY_REVIEW_INVALID")
    if {key: item for key, item in decision.items() if key != "reviewer"} != expected:
        raise _error("POLICY_REVIEW_MISMATCH")
    return decision


def _payloads(
    preview: Mapping[str, Any], decision: Mapping[str, Any], resources: Mapping[str, bytes]
) -> dict[str, bytes]:
    state = {
        "schema_version": "1.0",
        "kind": "aiflow-init-state",
        **{
            key: preview[key]
            for key in ("repository_id", "profile", "preview_sha256", "bundle", "policy", "objects")
        },
        "policy_review_sha256": _digest(decision),
    }
    payloads = {".ai/" + path: data for path, data in resources.items()}
    payloads[STATE] = _json(state)
    payloads[REVIEW] = _json(decision)
    payloads[COMPLETE] = _json(
        {
            "schema_version": "1.0",
            "kind": "aiflow-init-complete",
            "repository_id": preview["repository_id"],
            "preview_sha256": preview["preview_sha256"],
            "state_sha256": _sha(payloads[STATE]),
            "policy_review_sha256": _sha(payloads[REVIEW]),
            "resources_sha256": _digest({path: _sha(data) for path, data in resources.items()}),
        }
    )
    payloads[PENDING] = payloads[IDENTITY] = (preview["repository_id"] + "\n").encode()
    return payloads


def _inventory(root: Path, *, allow_history: bool = False) -> dict[str, Path]:
    ai = root / ".ai"
    _plain(ai, directory=True)
    found: dict[str, Path] = {".ai": ai}
    pending = [ai]
    while pending:
        directory = pending.pop()
        entries = _entries(directory, 64)
        if len(found) + len(entries) > 64:
            raise _error("INVENTORY_TOO_LARGE")
        for path in entries:
            relative = path.relative_to(root).as_posix()
            info = _plain(path)
            if stat.S_ISDIR(info.st_mode):
                if allow_history and directory == ai and path.name in RUNTIME_DIRECTORIES:
                    continue
                pending.append(path)
            elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise _error("INVENTORY_TYPE")
            found[relative] = path
    return found


def _existing(
    root: Path, payloads: Mapping[str, bytes], *, allow_partial: bool, allow_history: bool = False
) -> tuple[dict[str, Path], bool]:
    found = _inventory(root, allow_history=allow_history)
    if set(found) - (set(payloads) | set(DIRECTORIES)):
        raise _error("UNKNOWN_INSTALLATION_OBJECT")
    if STATE not in found or PENDING in found and IDENTITY in found:
        raise _error("INSTALLATION_STATE_INVALID")
    for path, actual in found.items():
        if path in DIRECTORIES:
            _plain(actual, directory=True)
        elif _read(actual, len(payloads[path])) != payloads[path]:
            raise _error("INSTALLATION_BYTES_CHANGED")
    required = set(payloads) - {PENDING}
    completed = required.issubset(found)
    if IDENTITY in found and not completed:
        raise _error("INSTALLATION_INCOMPLETE")
    if COMPLETE in found and not (required - {IDENTITY}).issubset(found):
        raise _error("INSTALLATION_INCOMPLETE")
    if COMPLETE in found and PENDING not in found and IDENTITY not in found:
        raise _error("INSTALLATION_INCOMPLETE")
    if not completed and not allow_partial:
        raise _error("INSTALLATION_INCOMPLETE")
    return found, completed


def _same_target(root: Path, original: Mapping[str, Any], sources: list[dict[str, Any]]) -> None:
    current = {
        **git.observe_initialization_target(root, exclude_initialization=True),
        "resource_sources": sources,
    }
    if current["python_source_count"] < 1:
        raise _error("TARGET_PROFILE_UNSUPPORTED")
    if current != original:
        raise _error("PREVIEW_STALE")


def apply_initialization(
    target: Path,
    preview: Mapping[str, Any],
    policy_review: Mapping[str, Any],
    *,
    bundle_root: Path | None = None,
    policy_directory: Path | None = None,
) -> dict[str, Any]:
    """Create only planned objects, or resume/replay that exact verified proposal."""
    proposal = _mapping(
        preview,
        {
            "schema_version",
            "kind",
            "repository_id",
            "profile",
            "target",
            "bundle",
            "policy",
            "objects",
            "preview_sha256",
        },
    )
    _profile(proposal["profile"])
    if proposal["schema_version"] != "1.0" or proposal["kind"] != "aiflow-init-preview":
        raise _error("PREVIEW_INVALID")
    identifier = _identifier(proposal["repository_id"])
    if proposal["preview_sha256"] != _digest(
        {k: v for k, v in proposal.items() if k != "preview_sha256"}
    ):
        raise _error("PREVIEW_DIGEST_INVALID")
    root = git.resolve_initialization_root(Path(target))
    _project(root)
    bundle, policy, resources, sources = _materials(root, bundle_root, policy_directory)
    if proposal["bundle"] != bundle or proposal["policy"] != policy:
        raise _error("PREVIEW_MATERIAL_CHANGED")
    if proposal["objects"] != _objects(resources, identifier):
        raise _error("PREVIEW_OBJECTS_INVALID")
    _same_target(root, proposal["target"], sources)
    decision = _review(proposal, policy_review)
    payloads = _payloads(proposal, decision, resources)
    aliases = [path for path in _entries(root, 10_000) if path.name.casefold() == ".ai"]
    if aliases and (len(aliases) != 1 or aliases[0].name != ".ai"):
        raise _error("INSTALLATION_CASE_CONFLICT")
    found, completed = _existing(root, payloads, allow_partial=True) if aliases else ({}, False)
    if completed:
        return {
            "schema_version": "1.0",
            "repository_id": identifier,
            "profile": PROFILE,
            "phase": "already_complete",
        }
    fs = WindowsFilesystem()
    handles: list[int] = []
    held: dict[str, int] = {}
    phase = "resumed" if found else "installed"
    try:
        # Retain every ancestor object, not just the final path string.
        for path in (*reversed(root.parents), root):
            handle = fs.open_directory(path, share_write=True)
            handles.append(handle)
            info = _plain(path, directory=True)
            actual = fs.identity(handle)
            if (actual["volume"], actual["file_id"]) != (info.st_dev, info.st_ino):
                raise _error("DIRECTORY_IDENTITY_CHANGED")
            if path == root:
                held[""] = handle
        if fs.volume(held[""])["filesystem"] != "NTFS":
            raise _error("FILESYSTEM_UNSUPPORTED")
        _same_target(root, proposal["target"], sources)
        for relative in DIRECTORIES:
            path = root / relative
            if relative in found:
                handle = fs.open_directory(path, share_write=relative == ".ai")
            else:
                parent = Path(relative).parent.as_posix()
                handle = fs.create_directory(
                    held["" if parent == "." else parent], path.name, share_write=relative == ".ai"
                )
            handles.append(handle)
            held[relative] = handle
        order = [STATE, PENDING, *sorted(".ai/" + name for name in resources), REVIEW, COMPLETE]
        for relative in order:
            path = root / relative
            if relative in found:
                handle = fs.open_file(path, allow_rename=relative == PENDING)
            else:
                handle = fs.create_file(
                    held[path.relative_to(root).parent.as_posix()],
                    path.name,
                    allow_rename=relative == PENDING,
                )
                handles.append(handle)
                held[relative] = handle
                fs.write(handle, payloads[relative])
                fs.flush(handle)
            if relative not in held:
                handles.append(handle)
                held[relative] = handle
            actual = fs.identity(handle)
            if actual["attributes"] & (0x400 | 0x10) or actual["links"] != 1:
                raise _error("INSTALLATION_TYPE_CHANGED")
            if fs.read(handle, len(payloads[relative])) != payloads[relative]:
                raise _error("INSTALLATION_BYTES_CHANGED")
        # Recheck observed Git/worktree facts just before publishing identity. This
        # is a checked boundary, not an atomic lock of the entire application tree.
        final_bundle, final_policy, final_resources, final_sources = _materials(
            root, bundle_root, policy_directory
        )
        if (
            final_bundle != proposal["bundle"]
            or final_policy != proposal["policy"]
            or final_resources != resources
        ):
            raise _error("PREVIEW_MATERIAL_CHANGED")
        _same_target(root, proposal["target"], final_sources)
        # The pending identity's DELETE-capable handle deliberately prevents
        # ordinary path opens. Inspect names/types here and read the held objects.
        if set(_inventory(root)) != set(DIRECTORIES) | (set(payloads) - {IDENTITY}):
            raise _error("INSTALLATION_OBJECTS_CHANGED")
        original_id = fs.identity(held[PENDING])
        fs.rename_no_replace(held[PENDING], root / IDENTITY)
        if (
            fs.identity(held[PENDING]) != original_id
            or fs.read(held[PENDING], 64) != payloads[IDENTITY]
        ):
            raise _error("IDENTITY_PUBLICATION_CHANGED")
        for relative in order:
            if fs.read(held[relative], len(payloads[relative])) != payloads[relative]:
                raise _error("INSTALLATION_BYTES_CHANGED")
    finally:
        failures: list[Exception] = []
        for handle in reversed(handles):
            try:
                fs.close(handle)
            except Exception as error:
                failures.append(error)
        if failures:
            raise _error("CLOSE_UNCONFIRMED") from failures[0]
    return {
        "schema_version": "1.0",
        "repository_id": identifier,
        "profile": PROFILE,
        "phase": phase,
    }


def _state_manifest(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    state = read_initialization_json(root / STATE)
    _mapping(
        state,
        {
            "schema_version",
            "kind",
            "repository_id",
            "profile",
            "preview_sha256",
            "bundle",
            "policy",
            "objects",
            "policy_review_sha256",
        },
    )
    _profile(state["profile"])
    identifier = _identifier(state["repository_id"])
    if (
        state["schema_version"] != "1.0"
        or state["kind"] != "aiflow-init-state"
        or not isinstance(state["preview_sha256"], str)
        or not _HEX.fullmatch(state["preview_sha256"])
    ):
        raise _error("INSTALLATION_STATE_INVALID")
    bundle = _mapping(state["bundle"], {"cli_version", "bundle_version", "manifest_sha256"})
    if bundle["cli_version"] != CLI_VERSION or bundle["bundle_version"] != BUNDLE_VERSION:
        raise _error("INSTALLATION_VERSION_UNSUPPORTED")
    policy = _mapping(state["policy"], {"policy_version", "semantic_sha256", "files"})
    for digest in (
        bundle["manifest_sha256"],
        policy["semantic_sha256"],
        state["policy_review_sha256"],
    ):
        if not isinstance(digest, str) or not _HEX.fullmatch(digest):
            raise _error("INSTALLATION_STATE_INVALID")
    if not isinstance(policy["policy_version"], str) or not re.fullmatch(
        r"[12]\.[0-9]+\.[0-9]+", policy["policy_version"]
    ):
        raise _error("INSTALLATION_STATE_INVALID")
    rows = state["objects"]
    expected = _objects({name: b"" for name in RESOURCE_KINDS}, identifier)
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise _error("INSTALLATION_STATE_INVALID")
    resources: dict[str, dict[str, Any]] = {}
    for actual, planned in zip(rows, expected, strict=True):
        if planned["path"].removeprefix(".ai/") in RESOURCE_KINDS:
            row = _mapping(actual, {"path", "type", "size", "sha256"})
            if (
                type(row["size"]) is not int
                or not 0 <= row["size"] <= MAX_RESOURCE_BYTES
                or not isinstance(row["sha256"], str)
                or not _HEX.fullmatch(row["sha256"])
            ):
                raise _error("INSTALLATION_STATE_INVALID")
            planned = {**planned, "size": row["size"], "sha256": row["sha256"]}
            resources[planned["path"].removeprefix(".ai/")] = row
        if actual != planned:
            raise _error("INSTALLATION_STATE_INVALID")
    if policy["files"] != [
        {
            "path": "policy/" + name,
            "size": resources["policy/" + name]["size"],
            "sha256": resources["policy/" + name]["sha256"],
        }
        for name in sorted(POLICY_FILES)
    ]:
        raise _error("INSTALLATION_STATE_INVALID")
    if sum(row["size"] for row in resources.values()) > MAX_BUNDLE_BYTES:
        raise _error("BUNDLE_TOO_LARGE")
    return state, resources


def _installed(root: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    state, planned = _state_manifest(root)
    identifier = state["repository_id"]
    resources = {name: _read(root / ".ai" / name, planned[name]["size"]) for name in RESOURCE_KINDS}
    if state["objects"] != _objects(resources, identifier):
        raise _error("INSTALLATION_BYTES_CHANGED")
    with schema_directory_context(root / ".ai/schemas"):
        policy = load_policy_bundle(root, policy_directory=root / ".ai/policy")
    if (
        policy.policy_version != state["policy"]["policy_version"]
        or policy.sha256 != state["policy"]["semantic_sha256"]
    ):
        raise _error("POLICY_REVIEW_MISMATCH")
    decision = _review(state, read_initialization_json(root / REVIEW))
    if state["policy_review_sha256"] != _digest(decision):
        raise _error("POLICY_REVIEW_MISMATCH")
    payloads = _payloads(state, decision, resources)
    if payloads[STATE] != _read(root / STATE, MAX_JSON_BYTES):
        raise _error("INSTALLATION_STATE_INVALID")
    return state, payloads


def _inspection_issues(root: Path) -> tuple[list[dict[str, str]], str]:
    state, resources = _state_manifest(root)
    found = _inventory(root, allow_history=True)
    expected = {row["path"] for row in state["objects"]}
    issues = [{"path": path, "code": "unknown"} for path in sorted(set(found) - expected)]
    if _read(root / STATE, MAX_JSON_BYTES) != _json(state):
        issues.append({"path": STATE, "code": "modified"})
    required = expected - {PENDING}
    for path in sorted(required - set(found)):
        issues.append({"path": path, "code": "missing"})
    actual_resources: dict[str, bytes] = {}
    for name, row in resources.items():
        path = ".ai/" + name
        if path in found:
            if _plain(found[path], directory=False).st_size != row["size"]:
                issues.append({"path": path, "code": "modified"})
                continue
            data = _read(found[path], row["size"])
            actual_resources[name] = data
            if len(data) != row["size"] or _sha(data) != row["sha256"]:
                issues.append({"path": path, "code": "modified"})
    if REVIEW in found:
        decision = _review(state, read_initialization_json(found[REVIEW]))
        if _digest(decision) != state["policy_review_sha256"] or _read(
            found[REVIEW], MAX_JSON_BYTES
        ) != _json(decision):
            issues.append({"path": REVIEW, "code": "modified"})
        if COMPLETE in found and len(actual_resources) == len(RESOURCE_KINDS):
            expected_complete = _payloads(state, decision, actual_resources)[COMPLETE]
            if _read(found[COMPLETE], MAX_JSON_BYTES) != expected_complete:
                issues.append({"path": COMPLETE, "code": "modified"})
    if IDENTITY in found and _read(found[IDENTITY], 64) != (state["repository_id"] + "\n").encode():
        issues.append({"path": IDENTITY, "code": "modified"})
    if PENDING in found:
        if _read(found[PENDING], 64) != (state["repository_id"] + "\n").encode():
            issues.append({"path": PENDING, "code": "modified"})
        if IDENTITY in found:
            issues.append({"path": IDENTITY, "code": "duplicate_identity"})
    if IDENTITY in found or COMPLETE in found:
        # These files can only be published after every prerequisite is complete.
        if any(issue["code"] == "missing" and issue["path"] != IDENTITY for issue in issues):
            issues.append({"path": COMPLETE, "code": "invalid_phase"})
    return issues, state["repository_id"]


def require_initialization_ready(repository_root: Path) -> None:
    """Guard managed installations; leave existing unmarked repositories unchanged."""
    root = Path(repository_root)
    ai = root / ".ai"
    if not ai.is_dir() and not ai.is_symlink():
        return
    names = {path.name for path in _entries(ai, 64)}
    markers = {Path(path).name for path in (STATE, REVIEW, COMPLETE, PENDING)}
    if not any(name.casefold() in {marker.casefold() for marker in markers} for name in names):
        return
    _, payloads = _installed(root)
    _existing(root, payloads, allow_partial=False, allow_history=True)


def inspect_initialization(target: Path) -> dict[str, Any]:
    """Describe installation integrity without recovery or history writes."""
    root = git.resolve_initialization_root(Path(target))
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "kind": "aiflow-init-inspection",
        "has_history": (root / ".ai/tasks").exists(),
    }
    if not any(path.name.casefold() == ".ai" for path in _entries(root, 10_000)):
        return {**result, "status": "absent", "issues": []}
    try:
        state, payloads = _installed(root)
        _existing(root, payloads, allow_partial=False, allow_history=True)
        require_initialization_ready(root)
        return {
            **result,
            "status": "complete",
            "issues": [],
            "repository_id": state["repository_id"],
            "profile": state["profile"],
        }
    except AiflowError as error:
        identifier: str | None = None
        try:
            issues, identifier = _inspection_issues(root)
        except AiflowError:
            issues = [{"path": ".ai", "code": error.code}]
        incomplete = bool(issues) and all(issue["code"] == "missing" for issue in issues)
        status = "incomplete" if incomplete else "conflict"
        if error.code in {
            "INITIALIZATION_PROFILE_UNSUPPORTED",
            "INITIALIZATION_INSTALLATION_VERSION_UNSUPPORTED",
        }:
            status = "unsupported"
        return {
            **result,
            "status": status,
            "issues": issues,
            **({"repository_id": identifier} if identifier is not None else {}),
        }


def plan_initialization_migration(
    target: Path,
    *,
    bundle_root: Path | None = None,
    policy_directory: Path | None = None,
    profile: str = PROFILE,
) -> dict[str, Any]:
    """Compare files only; this plan never rewrites resources or historical facts."""
    _profile(profile)
    root = git.resolve_initialization_root(Path(target))
    inspected = inspect_initialization(root)
    bundle, policy, resources, _ = _materials(root, bundle_root, policy_directory)
    comparison: list[dict[str, Any]] = []
    for name, data in sorted(resources.items()):
        path = root / ".ai" / name
        try:
            current = _read(path, MAX_RESOURCE_BYTES)
            status = "unchanged" if current == data else "modified"
        except AiflowError:
            status = "unknown" if os.path.lexists(path) else "missing"
        comparison.append({"path": ".ai/" + name, "status": status, "proposed_sha256": _sha(data)})
    return {
        **inspected,
        "kind": "aiflow-init-migration-plan",
        "read_only": True,
        "proposed_bundle": bundle,
        "proposed_policy": policy,
        "files": comparison
        + [
            {"path": issue["path"], "status": "unknown"}
            for issue in inspected["issues"]
            if issue["code"] == "unknown"
        ],
    }
