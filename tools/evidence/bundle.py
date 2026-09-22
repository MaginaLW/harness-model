"""Copy explicitly selected evidence bytes into a local, independently checkable ZIP."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import stat
import struct
import sys
import zipfile
import zlib
from pathlib import Path, PureWindowsPath
from typing import IO, Any

FORMAT = "aiflow-evidence-bundle"
MAX_FILES = 10_000
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_CENTRAL_BYTES = 8 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
WINDOWS = os.name == "nt"
KINDS = {"git-text", "runtime-original"}
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.IGNORECASE)


class BundleError(ValueError):
    """A stable error code that never includes a private machine path."""


def _object(value: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise BundleError("INVALID_FIELDS")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BundleError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _json(data: bytes) -> Any:
    if len(data) > MAX_JSON_BYTES:
        raise BundleError("JSON_TOO_LARGE")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    except BundleError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise BundleError("INVALID_JSON") from exc


def _relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise BundleError("UNSAFE_PATH")
    parts = value.split("/")
    if any(
        part in {"", ".", ".."}
        or part.endswith((" ", "."))
        or RESERVED.fullmatch(part)
        or any(ord(char) < 32 or char in '\\:*?"<>|' for char in part)
        for part in parts
    ):
        raise BundleError("UNSAFE_PATH")
    return value


def _entries(value: Any, *, manifest: bool) -> list[dict[str, Any]]:
    keys = {"version", "files", "format"} if manifest else {"version", "files"}
    document = _object(value, keys)
    if type(document["version"]) is not int or document["version"] != 1:
        raise BundleError("UNSUPPORTED_VERSION")
    if manifest and document["format"] != FORMAT:
        raise BundleError("INVALID_FORMAT")
    entries = document["files"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FILES:
        raise BundleError("INVALID_FILE_COUNT")
    seen: set[str] = set()
    total = 0
    for entry in entries:
        entry_keys = {"kind", "path", "size", "sha256"} if manifest else {"kind", "path"}
        _object(entry, entry_keys)
        if not isinstance(entry["kind"], str) or entry["kind"] not in KINDS:
            raise BundleError("INVALID_KIND")
        name = f"{entry['kind']}/{_relative_path(entry['path'])}"
        if name.casefold() in seen:
            raise BundleError("DUPLICATE_PATH")
        seen.add(name.casefold())
        if manifest:
            size = entry["size"]
            if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES:
                raise BundleError("INVALID_FILE_SIZE")
            digest = entry["sha256"]
            if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
                raise BundleError("INVALID_DIGEST")
            total += size
    if total > MAX_TOTAL_BYTES:
        raise BundleError("TOTAL_TOO_LARGE")
    return entries


def _plain_path(path: Path, *, directory: bool = False) -> Path:
    """Check every existing component, including Windows junction/reparse points."""
    if WINDOWS:
        original = PureWindowsPath(str(path))
        if (original.drive and not original.is_absolute()) or (
            original.root and not original.drive
        ):
            raise BundleError("NONLOCAL_PATH")
        if original.drive and not re.fullmatch(r"[A-Za-z]:", original.drive):
            raise BundleError("NONLOCAL_PATH")
    path = Path(os.path.abspath(path))
    if WINDOWS:
        _require_local_windows_path(str(path))
    for part in reversed((path, *path.parents)):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise BundleError("LINK_NOT_ALLOWED")
    mode = path.stat().st_mode
    if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
        raise BundleError("INVALID_FILE_TYPE")
    return path


def _drive_type(anchor: str) -> int:
    get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
    get_drive_type.argtypes = [ctypes.c_wchar_p]
    get_drive_type.restype = ctypes.c_uint
    return int(get_drive_type(anchor))


def _require_local_windows_path(value: str) -> None:
    path = PureWindowsPath(value)
    if not re.fullmatch(r"[A-Za-z]:", path.drive) or path.root != "\\":
        raise BundleError("NONLOCAL_PATH")
    # Unknown/no-root/network drives fail closed before any file metadata access.
    if _drive_type(path.anchor) not in {2, 3, 5, 6}:
        raise BundleError("NONLOCAL_PATH")


def _read_json(path: Path) -> Any:
    with _plain_path(path).open("rb") as stream:
        return _json(stream.read(MAX_JSON_BYTES + 1))


def _digest(stream: IO[bytes], limit: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    while data := stream.read(CHUNK_BYTES):
        total += len(data)
        if total > limit:
            raise BundleError("CONTENT_TOO_LARGE")
        digest.update(data)
    return digest.hexdigest(), total


def _signature(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _output_path(output: Path, roots: list[Path]) -> Path:
    _relative_path(output.name)
    output = Path(os.path.abspath(output))
    _plain_path(output.parent, directory=True)
    # Include Git worktree roots (a .git file) as well as ordinary repositories.
    prohibited = set(roots)
    for root in roots:
        prohibited.update(parent for parent in (root, *root.parents) if (parent / ".git").exists())
    if any(output.is_relative_to(root) for root in prohibited):
        raise BundleError("OUTPUT_MUST_BE_OUTSIDE_SOURCE_AND_REPOSITORY")
    if output.exists() or output.is_symlink():
        raise BundleError("OUTPUT_EXISTS")
    return output


def export_bundle(
    task_dir: Path, selection: Path, output: Path, raw_dir: Path | None = None
) -> dict[str, Any]:
    """Export only allowlisted files; labels assert no Git or identity verification."""
    roots = {"git-text": _plain_path(task_dir, directory=True)}
    if raw_dir is not None:
        roots["runtime-original"] = _plain_path(raw_dir, directory=True)
    entries = _entries(_read_json(selection), manifest=False)
    output = _output_path(output, list(roots.values()))
    sources: list[tuple[dict[str, Any], Path]] = []
    total = 0
    for entry in entries:
        if entry["kind"] not in roots:
            raise BundleError("RAW_DIR_REQUIRED")
        path = _plain_path(roots[entry["kind"]] / entry["path"])
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise BundleError("CONTENT_TOO_LARGE")
        total += size
        sources.append((entry, path))
    if total > MAX_TOTAL_BYTES:
        raise BundleError("TOTAL_TOO_LARGE")

    manifest_entries: list[dict[str, Any]] = []
    copied_bytes = 0
    # Exclusive creation prevents silently replacing a previous handoff.
    with output.open("xb") as destination:
        try:
            with zipfile.ZipFile(
                destination, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=False
            ) as archive:
                for entry, path in sources:
                    _plain_path(path)
                    with path.open("rb") as source:
                        before = os.fstat(source.fileno())
                        digest = hashlib.sha256()
                        size = 0
                        with archive.open(f"{entry['kind']}/{entry['path']}", "w") as target:
                            while data := source.read(CHUNK_BYTES):
                                size += len(data)
                                if size > MAX_FILE_BYTES:
                                    raise BundleError("CONTENT_TOO_LARGE")
                                copied_bytes += len(data)
                                if copied_bytes > MAX_TOTAL_BYTES:
                                    raise BundleError("TOTAL_TOO_LARGE")
                                digest.update(data)
                                target.write(data)
                        after = os.fstat(source.fileno())
                    if (
                        _signature(before) != _signature(after)
                        or _signature(before) != _signature(_plain_path(path).stat())
                        or size != before.st_size
                    ):
                        raise BundleError("SOURCE_CHANGED_DURING_EXPORT")
                    manifest_entries.append({**entry, "size": size, "sha256": digest.hexdigest()})
                manifest = {"format": FORMAT, "version": 1, "files": manifest_entries}
                _entries(manifest, manifest=True)
                data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                if len(data) > MAX_JSON_BYTES:
                    raise BundleError("JSON_TOO_LARGE")
                archive.writestr("manifest.json", data)
        except BaseException:
            destination.close()
            output.unlink()
            raise
    result = verify_bundle(output)
    result["status"] = "EXPORTED"
    return result


def verify_bundle(bundle: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    """Verify archive bytes without extracting anything or interpreting evidence."""
    bundle = _plain_path(bundle)
    if expected_sha256 is not None and not DIGEST.fullmatch(expected_sha256):
        raise BundleError("INVALID_EXPECTED_DIGEST")
    with bundle.open("rb") as source:
        before = os.fstat(source.fileno())
        _preflight_zip(source, before.st_size)
        source.seek(0)
        digest = _digest(source, MAX_TOTAL_BYTES + MAX_JSON_BYTES + MAX_FILES * 4096)[0]
        if expected_sha256 is not None and digest != expected_sha256:
            raise BundleError("BUNDLE_DIGEST_MISMATCH")
        source.seek(0)
        with zipfile.ZipFile(source) as archive:
            count, total = _verify_archive(archive)
        if _signature(before) != _signature(os.fstat(source.fileno())) or _signature(
            before
        ) != _signature(_plain_path(bundle).stat()):
            raise BundleError("BUNDLE_CHANGED_DURING_VERIFICATION")
    return {
        "status": "VERIFIED",
        "files": count,
        "bytes": total,
        "bundle_sha256": digest,
        "expected_digest_matched": expected_sha256 is not None,
        "source_authenticated": False,
        "governance_effect": "none",
    }


def _preflight_zip(source: IO[bytes], size: int) -> None:
    """Bound central-directory parsing before ZipFile allocates its member list."""
    if size < 22 or size > MAX_TOTAL_BYTES + MAX_JSON_BYTES + MAX_CENTRAL_BYTES:
        raise BundleError("INVALID_ARCHIVE_SIZE")
    source.seek(size - 22)
    signature, disk, central_disk, disk_count, count, length, offset, comment = struct.unpack(
        "<4s4H2LH", source.read(22)
    )
    # Exported bundles need neither comments, multiple disks, nor ZIP64. Requiring
    # the ordinary EOCD at EOF also rejects trailing data and ZIP64 locators.
    if signature != b"PK\x05\x06" or disk or central_disk or comment:
        raise BundleError("UNSUPPORTED_ZIP_LAYOUT")
    if count == 0xFFFF or length == 0xFFFFFFFF or offset == 0xFFFFFFFF:
        raise BundleError("ZIP64_NOT_SUPPORTED")
    if not 2 <= count <= MAX_FILES + 1 or disk_count != count:
        raise BundleError("INVALID_MEMBER_COUNT")
    if length > MAX_CENTRAL_BYTES or offset + length != size - 22:
        raise BundleError("INVALID_CENTRAL_DIRECTORY")
    source.seek(offset)
    end = offset + length
    for _ in range(count):
        if source.tell() + 46 > end:
            raise BundleError("INVALID_CENTRAL_DIRECTORY")
        header = source.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise BundleError("INVALID_CENTRAL_DIRECTORY")
        if header[6] == 45:
            raise BundleError("ZIP64_NOT_SUPPORTED")
        compressed, uncompressed = struct.unpack_from("<2L", header, 20)
        name_size, extra_size, comment_size, member_disk = struct.unpack_from("<4H", header, 28)
        local_offset = struct.unpack_from("<L", header, 42)[0]
        if 0xFFFFFFFF in {compressed, uncompressed, local_offset} or member_disk == 0xFFFF:
            raise BundleError("ZIP64_NOT_SUPPORTED")
        if member_disk or source.tell() + name_size + extra_size + comment_size > end:
            raise BundleError("INVALID_CENTRAL_DIRECTORY")
        source.seek(name_size, 1)
        extra = source.read(extra_size)
        cursor = 0
        while cursor < len(extra):
            if cursor + 4 > len(extra):
                raise BundleError("INVALID_CENTRAL_DIRECTORY")
            field, field_size = struct.unpack_from("<2H", extra, cursor)
            if field == 1:
                raise BundleError("ZIP64_NOT_SUPPORTED")
            cursor += 4 + field_size
            if cursor > len(extra):
                raise BundleError("INVALID_CENTRAL_DIRECTORY")
        source.seek(comment_size, 1)
    if source.tell() != end:
        raise BundleError("INVALID_CENTRAL_DIRECTORY")


def _verify_archive(archive: zipfile.ZipFile) -> tuple[int, int]:
    members = archive.infolist()
    if not 2 <= len(members) <= MAX_FILES + 1:
        raise BundleError("INVALID_MEMBER_COUNT")
    by_name: dict[str, zipfile.ZipInfo] = {}
    for member in members:
        name = _relative_path(member.orig_filename)
        if name in by_name:
            raise BundleError("DUPLICATE_ZIP_MEMBER")
        by_name[name] = member
        if member.flag_bits & 1 or member.compress_type not in {
            zipfile.ZIP_STORED,
            zipfile.ZIP_DEFLATED,
        }:
            raise BundleError("UNSUPPORTED_ZIP_MEMBER")
        mode = stat.S_IFMT(member.external_attr >> 16)
        if mode not in {0, stat.S_IFREG}:
            raise BundleError("INVALID_ZIP_FILE_TYPE")
        limit = MAX_JSON_BYTES if name == "manifest.json" else MAX_FILE_BYTES
        if member.file_size > limit:
            raise BundleError("CONTENT_TOO_LARGE")
    if "manifest.json" not in by_name:
        raise BundleError("MISSING_MANIFEST")
    with archive.open("manifest.json") as stream:
        entries = _entries(_json(stream.read(MAX_JSON_BYTES + 1)), manifest=True)
    expected = {f"{entry['kind']}/{entry['path']}" for entry in entries} | {"manifest.json"}
    if set(by_name) != expected:
        raise BundleError("MEMBER_SET_MISMATCH")
    total = 0
    for entry in entries:
        name = f"{entry['kind']}/{entry['path']}"
        if by_name[name].file_size != entry["size"]:
            raise BundleError("FILE_SIZE_MISMATCH")
        with archive.open(name) as stream:
            actual_digest, size = _digest(stream, entry["size"])
        if actual_digest != entry["sha256"] or size != entry["size"]:
            raise BundleError("FILE_DIGEST_MISMATCH")
        total += size
    return len(entries), total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser(
        "export", help="copy an explicit file allowlist to a new local ZIP"
    )
    export.add_argument("--task-dir", type=Path, required=True)
    export.add_argument("--raw-dir", type=Path)
    export.add_argument("--selection", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify", help="read and hash a ZIP without extraction")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--expected-sha256")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            result = export_bundle(args.task_dir, args.selection, args.output, args.raw_dir)
        else:
            result = verify_bundle(args.bundle, args.expected_sha256)
    except BundleError as exc:
        print(json.dumps({"status": "ERROR", "code": str(exc)}), file=sys.stderr)
        return 1
    except (
        OSError,
        UnicodeError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        RuntimeError,
        NotImplementedError,
        EOFError,
        zlib.error,
        struct.error,
    ):
        print(json.dumps({"status": "ERROR", "code": "IO_OR_ZIP_ERROR"}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
