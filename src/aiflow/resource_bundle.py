"""Build and read the fixed, portable seed resources for external initialization.

Hashes establish internal consistency, not the publisher's identity. Runtime
contracts and Policy continue to come from the target repository's .ai tree.
"""

from __future__ import annotations

import ast
import hashlib
import json
import stat
import tomllib
import zipfile
import zlib
from collections.abc import Mapping
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import yaml

SCHEMAS = (
    "approval",
    "ask-options",
    "classification",
    "decision-unit",
    "event",
    "evidence",
    "mutation-evidence",
    "mutation-manifest",
    "observation",
    "observation-decision",
    "policy",
    "review-context",
    "review-record",
    "task",
    "verifier-context",
)
POLICIES = {
    "hard-rules.yaml": "hard_rules",
    "routing.yaml": "routing",
    "verification-levels.yaml": "verification_levels",
    "permissions.yaml": "permissions",
}
RESOURCE_KINDS = {
    **{f"schemas/{name}.schema.json": "schema" for name in SCHEMAS},
    **{f"policy/{name}": "policy" for name in POLICIES},
    "templates/spec.md": "template",
}
SCHEMA_VERSION = "1.0"
BUNDLE_VERSION = "1.0"
CLI_VERSION = "0.2.0"
POLICY_VERSION = "2.6.0"
MAX_MANIFEST_BYTES = 64 * 1024
MAX_RESOURCE_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 4 * 1024 * 1024


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class _UniqueLoader(yaml.SafeLoader):
    """Reject ambiguous Policy metadata rather than accepting the last key."""


def _yaml_mapping(loader: _UniqueLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError("duplicate Policy key")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_mapping)


def _read_limited(path: Traversable, limit: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("resource data exceeds size limit")
    return data


def _canonical(raw: bytes) -> bytes:
    try:
        raw.decode("utf-8")
    except UnicodeError as error:
        raise ValueError("resource is not UTF-8") from error
    normalized = raw.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise ValueError("resource contains a bare carriage return")
    return normalized


def _check_path(path: Path, *, directory: bool | None) -> bool:
    """Reject symbolic links, Windows reparse points, and unexpected file types."""
    try:
        info = path.lstat()
    except OSError as error:
        raise ValueError("resource path is unavailable") from error
    reparse = getattr(info, "st_file_attributes", 0) & getattr(
        stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
    )
    if stat.S_ISLNK(info.st_mode) or reparse:
        raise ValueError("resource path contains a link or reparse point")
    is_directory = stat.S_ISDIR(info.st_mode)
    if directory and not is_directory:
        raise ValueError("resource directory is not a directory")
    if (directory is False or (directory is None and not is_directory)) and (
        not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
    ):
        raise ValueError("resource file is not an ordinary file")
    return is_directory


def _source_file(root: Path, relative: str) -> Path:
    _check_path(root, directory=True)
    path = root
    parts = relative.split("/")
    if any(part in {"", ".", ".."} or "\\" in part or ":" in part for part in parts):
        raise ValueError("resource path is not a safe relative path")
    for index, part in enumerate(parts):
        path = path / part
        _check_path(path, directory=index < len(parts) - 1)
    return path


def _version_source_text(path: Path) -> str:
    try:
        return (
            _read_limited(path, MAX_RESOURCE_BYTES)
            .decode("utf-8")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )
    except (OSError, ValueError) as error:
        raise ValueError("cannot verify CLI version") from error


def _check_versions(source_root: Path) -> None:
    try:
        project = tomllib.loads(_version_source_text(_source_file(source_root, "pyproject.toml")))
        parsed = ast.parse(
            _version_source_text(_source_file(source_root, "src/aiflow/__init__.py"))
        )
        versions = [
            item.value.value
            for item in parsed.body
            if isinstance(item, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in item.targets
            )
            and isinstance(item.value, ast.Constant)
        ]
        if project["project"]["version"] != CLI_VERSION or versions != [CLI_VERSION]:
            raise ValueError("incompatible CLI version")
    except (
        OSError,
        UnicodeError,
        SyntaxError,
        KeyError,
        TypeError,
        RecursionError,
        tomllib.TOMLDecodeError,
    ) as error:
        raise ValueError("cannot verify CLI version") from error


def _check_policy(path: str, data: bytes) -> None:
    try:
        document = yaml.load(data, Loader=_UniqueLoader)
    except (yaml.YAMLError, TypeError, RecursionError) as error:
        raise ValueError("invalid Policy seed") from error
    if not isinstance(document, Mapping) or (
        document.get("schema_version") != SCHEMA_VERSION
        or document.get("policy_version") != POLICY_VERSION
        or document.get("policy_kind") != POLICIES[path.removeprefix("policy/")]
    ):
        raise ValueError("incompatible Policy seed metadata")


def build_bundle(source_root: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Build a deterministic bundle from the fixed .ai source allowlist."""
    _check_versions(source_root)
    files: dict[str, bytes] = {}
    entries: list[dict[str, Any]] = []
    total_size = 0
    for path, kind in sorted(RESOURCE_KINDS.items()):
        source = _source_file(source_root, f".ai/{path}")
        limit = min(MAX_RESOURCE_BYTES, MAX_BUNDLE_BYTES - total_size)
        try:
            raw = _read_limited(source, 2 * limit)
        except OSError as error:
            raise ValueError("cannot read resource source") from error
        data = _canonical(raw)
        if len(data) > limit:
            raise ValueError("resource data exceeds size limit")
        total_size += len(data)
        if kind == "policy":
            _check_policy(path, data)
        files[path] = data
        entries.append(
            {
                "path": path,
                "kind": kind,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "bundle_version": BUNDLE_VERSION,
        "compatible_cli_versions": [CLI_VERSION],
        "policy_version": POLICY_VERSION,
        "files": entries,
    }
    return manifest, files


def _validate_zip_metadata(root: zipfile.Path) -> None:
    """Reject links and special entries in the bundle without extracting them."""
    prefix = root.at
    if prefix and (
        prefix.startswith("/")
        or not prefix.endswith("/")
        or "\\" in prefix
        or any(part in {"", ".", ".."} for part in prefix[:-1].split("/"))
    ):
        raise ValueError("bundle archive root is invalid")
    parts = prefix[:-1].split("/") if prefix else []
    ancestors = {"/".join(parts[:index]) for index in range(1, len(parts) + 1)}
    seen: set[str] = set()
    for info in root.root.infolist():
        name = info.filename
        ancestor = name.rstrip("/") in ancestors
        if not ancestor and not name.startswith(prefix):
            continue
        if name in seen:
            raise ValueError("bundle contains a duplicate path")
        seen.add(name)
        kind = stat.S_IFMT(info.external_attr >> 16)
        if kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise ValueError("bundle archive contains a link or special file")
        if (
            (ancestor and not name.endswith("/"))
            or (kind == stat.S_IFREG and name.endswith("/"))
            or (kind == stat.S_IFDIR and not name.endswith("/"))
        ):
            raise ValueError("bundle archive entry type is invalid")


def _inventory(root: Traversable, prefix: str = "", seen: set[str] | None = None) -> set[str]:
    paths: set[str] = set()
    if seen is None:
        seen = set()
    for entry in root.iterdir():
        path = f"{prefix}/{entry.name}" if prefix else entry.name
        if path in seen:
            raise ValueError("bundle contains a duplicate path")
        seen.add(path)
        if isinstance(entry, Path):
            directory = _check_path(entry, directory=None)
            file = not directory
        else:
            if getattr(entry, "is_symlink", lambda: False)():
                raise ValueError("bundle contains a symlink")
            directory = entry.is_dir()
            file = not directory and entry.is_file()
        if directory:
            if path not in {"schemas", "policy", "templates"}:
                raise ValueError("bundle contains an unexpected directory")
            paths.update(_inventory(entry, path, seen))
        elif file:
            paths.add(path)
        else:
            raise ValueError("bundle contains a non-file entry")
    return paths


def _read_bundle(root: Traversable, cli_version: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    if not isinstance(root, (Path, zipfile.Path)):
        raise ValueError("unsupported resource bundle root")
    if cli_version != CLI_VERSION:
        raise ValueError("bundle is incompatible with the running CLI version")
    try:
        if isinstance(root, Path):
            _check_path(root, directory=True)
        else:
            _validate_zip_metadata(root)
        if _inventory(root) != {*RESOURCE_KINDS, "manifest.json"}:
            raise ValueError("bundle inventory does not match the allowlist")
        manifest = json.loads(
            _read_limited(root.joinpath("manifest.json"), MAX_MANIFEST_BYTES).decode("utf-8"),
            object_pairs_hook=_unique_object,
        )
        if not isinstance(manifest, dict) or set(manifest) != {
            "schema_version",
            "bundle_version",
            "compatible_cli_versions",
            "policy_version",
            "files",
        }:
            raise ValueError("invalid bundle manifest")
        if (
            manifest["schema_version"] != SCHEMA_VERSION
            or manifest["bundle_version"] != BUNDLE_VERSION
            or manifest["compatible_cli_versions"] != [CLI_VERSION]
            or manifest["policy_version"] != POLICY_VERSION
        ):
            raise ValueError("incompatible bundle manifest")
        entries = manifest["files"]
        if not isinstance(entries, list) or len(entries) != len(RESOURCE_KINDS):
            raise ValueError("invalid bundle file list")
        total_size = 0
        for entry, (expected_path, kind) in zip(
            entries, sorted(RESOURCE_KINDS.items()), strict=True
        ):
            if not isinstance(entry, dict) or set(entry) != {"path", "kind", "size", "sha256"}:
                raise ValueError("invalid bundle file entry")
            if entry["path"] != expected_path or entry["kind"] != kind:
                raise ValueError("bundle file entry does not match allowlist")
            size = entry["size"]
            if type(size) is not int or not 0 <= size <= MAX_RESOURCE_BYTES:
                raise ValueError("invalid bundle resource size")
            total_size += size
            if total_size > MAX_BUNDLE_BYTES:
                raise ValueError("bundle resources exceed size limit")
        files: dict[str, bytes] = {}
        for entry, (expected_path, kind) in zip(
            entries, sorted(RESOURCE_KINDS.items()), strict=True
        ):
            data = _read_limited(root.joinpath(*expected_path.split("/")), entry["size"])
            if (
                _canonical(data) != data
                or entry["size"] != len(data)
                or entry["sha256"] != hashlib.sha256(data).hexdigest()
            ):
                raise ValueError("bundle file integrity mismatch")
            if kind == "policy":
                _check_policy(expected_path, data)
            files[expected_path] = data
        return manifest, files
    except (
        OSError,
        EOFError,
        RuntimeError,
        NotImplementedError,
        zipfile.BadZipFile,
        zlib.error,
        UnicodeError,
        json.JSONDecodeError,
        AttributeError,
        TypeError,
        RecursionError,
    ) as error:
        raise ValueError("cannot read resource bundle") from error


def read_bundle(root: Traversable) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Read and validate the whole bundle against the running CLI version."""
    from aiflow import __version__

    return _read_bundle(root, __version__)
