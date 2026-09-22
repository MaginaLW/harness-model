"""Check explicitly mapped log selections and producer/staged byte relationships."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.evidence import bundle


@dataclass(frozen=True)
class Fingerprint:
    raw: str
    size: int
    crlf_folded: str
    folded_size: int


class Reader:
    """Bounded reads with byte hashes and observed file identity checks."""

    def __init__(self) -> None:
        self.total = 0
        self.checks = 0
        self.cache: dict[Path, tuple[Fingerprint, tuple[int, int, int, int]]] = {}

    def read(self, path: Path, *, collect: bool = False) -> tuple[Fingerprint, bytes]:
        path = bundle._plain_path(path)
        if not collect and path in self.cache:
            cached, signature = self.cache[path]
            if bundle._signature(path.stat()) != signature:
                raise bundle.BundleError("SOURCE_CHANGED")
            return cached, b""
        limit = bundle.MAX_JSON_BYTES if collect else bundle.MAX_FILE_BYTES
        raw = hashlib.sha256()
        folded = hashlib.sha256()
        size = folded_size = 0
        pending_cr = b""
        content = bytearray()
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            if before.st_size > limit:
                raise bundle.BundleError("CONTENT_TOO_LARGE")
            while data := source.read(bundle.CHUNK_BYTES):
                size += len(data)
                self.total += len(data)
                if size > limit:
                    raise bundle.BundleError("CONTENT_TOO_LARGE")
                if self.total > bundle.MAX_TOTAL_BYTES:
                    raise bundle.BundleError("TOTAL_TOO_LARGE")
                raw.update(data)
                if collect:
                    content.extend(data)
                data = pending_cr + data
                pending_cr = b"\r" if data.endswith(b"\r") else b""
                if pending_cr:
                    data = data[:-1]
                data = data.replace(b"\r\n", b"\n")
                folded.update(data)
                folded_size += len(data)
            after = os.fstat(source.fileno())
        if (
            bundle._signature(before) != bundle._signature(after)
            or bundle._signature(before) != bundle._signature(bundle._plain_path(path).stat())
            or size != before.st_size
        ):
            raise bundle.BundleError("SOURCE_CHANGED")
        folded.update(pending_cr)
        result = Fingerprint(
            raw.hexdigest(), size, folded.hexdigest(), folded_size + len(pending_cr)
        )
        self.cache[path] = result, bundle._signature(before)
        return result, bytes(content)

    def document(self, path: Path) -> Any:
        return bundle._json(self.read(path, collect=True)[1])


def _request(value: Any) -> dict[str, Any]:
    document = bundle._object(value, {"version", "evidence", "pairs"})
    if type(document["version"]) is not int or document["version"] != 1:
        raise bundle.BundleError("UNSUPPORTED_VERSION")
    evidence, pairs = document["evidence"], document["pairs"]
    if (
        not isinstance(evidence, list)
        or not isinstance(pairs, list)
        or not 1 <= len(evidence) + len(pairs) <= bundle.MAX_FILES
    ):
        raise bundle.BundleError("INVALID_MAPPING_COUNT")
    seen: set[tuple[str, str]] = set()
    for item in evidence:
        bundle._object(item, {"path", "task_root"})
        path = bundle._relative_path(item["path"])
        root = item["task_root"]
        if root != "":
            root = bundle._relative_path(root)
        if path.rpartition("/")[0] != root:
            raise bundle.BundleError("EVIDENCE_ROOT_MISMATCH")
        key = ("evidence", path.casefold())
        if key in seen:
            raise bundle.BundleError("DUPLICATE_MAPPING")
        seen.add(key)
    for item in pairs:
        bundle._object(item, {"producer_path", "staged_path", "original_path"})
        for field in ("producer_path", "staged_path", "original_path"):
            if field == "original_path" and item[field] is None:
                continue
            path = bundle._relative_path(item[field])
            key = (field, path.casefold())
            if key in seen:
                raise bundle.BundleError("DUPLICATE_MAPPING")
            seen.add(key)
    return document


def _evidence(
    item: dict[str, Any], selected: set[tuple[str, str]], raw: Path, reader: Reader
) -> dict[str, Any]:
    result: dict[str, Any] = {"checks": 0, "log_references": 0, "issues": []}
    if ("runtime-original", item["path"]) not in selected:
        result["issues"].append({"code": "EVIDENCE_NOT_SELECTED"})
        return result
    try:
        document = reader.document(raw / item["path"])
    except FileNotFoundError:
        result["issues"].append({"code": "MISSING_EVIDENCE"})
        return result
    if not isinstance(document, dict) or document.get("schema_version") != "1.0":
        raise bundle.BundleError("UNSUPPORTED_EVIDENCE")
    checks = document.get("checks")
    if not isinstance(checks, list) or not 1 <= len(checks) <= bundle.MAX_FILES:
        raise bundle.BundleError("INVALID_CHECK_COUNT")
    reader.checks += len(checks)
    if reader.checks > bundle.MAX_FILES:
        raise bundle.BundleError("TOO_MANY_CHECKS")
    result["checks"] = len(checks)
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise bundle.BundleError("INVALID_CHECK")
        for stream in ("stdout", "stderr"):
            reference = check.get(f"{stream}_log_ref")
            code = None
            if reference is None:
                code = "MISSING_LOG_REFERENCE"
            else:
                reference = bundle._relative_path(reference)
                if not reference.startswith("logs/"):
                    raise bundle.BundleError("INVALID_LOG_REFERENCE")
                result["log_references"] += 1
                relative = f"{item['task_root']}/{reference}" if item["task_root"] else reference
                if ("runtime-original", relative) not in selected:
                    code = "LOG_NOT_SELECTED"
                else:
                    try:
                        reader.read(raw / relative)
                    except FileNotFoundError:
                        code = "MISSING_LOG"
            if code is not None:
                result["issues"].append({"check": index, "stream": stream, "code": code})
    return result


def _pair(
    item: dict[str, Any],
    selected: set[tuple[str, str]],
    task: Path,
    raw: Path,
    producer: Path,
    reader: Reader,
) -> dict[str, str]:
    result = {"comparison": "UNCHECKED", "original": "UNCHECKED"}
    if ("git-text", item["staged_path"]) not in selected:
        result["comparison"] = "STAGED_NOT_SELECTED"
        return result
    try:
        staged, _ = reader.read(task / item["staged_path"])
    except FileNotFoundError:
        result["comparison"] = "MISSING_STAGED"
        return result
    try:
        source, _ = reader.read(producer / item["producer_path"])
    except FileNotFoundError:
        result["comparison"] = "MISSING_PRODUCER"
        return result
    if (source.raw, source.size) == (staged.raw, staged.size):
        result["comparison"] = "RAW_IDENTICAL"
    elif (source.crlf_folded, source.folded_size) == (staged.crlf_folded, staged.folded_size):
        result["comparison"] = "CRLF_ONLY"
    else:
        result["comparison"] = "CONTENT_CONFLICT"
    original = item["original_path"]
    if original is None:
        result["original"] = (
            "NOT_REQUIRED" if result["comparison"] == "RAW_IDENTICAL" else "ORIGINAL_NOT_MAPPED"
        )
    elif ("runtime-original", original) not in selected:
        result["original"] = "ORIGINAL_NOT_SELECTED"
    else:
        try:
            saved, _ = reader.read(raw / original)
        except FileNotFoundError:
            result["original"] = "MISSING_ORIGINAL"
        else:
            result["original"] = (
                "MATCHED"
                if (saved.raw, saved.size) == (source.raw, source.size)
                else "ORIGINAL_MISMATCH"
            )
    return result


def review_selection(
    task_dir: Path,
    raw_dir: Path,
    selection: Path,
    request: Path,
    producer_dir: Path | None = None,
) -> dict[str, Any]:
    """Review only requested mappings; never discover, add, copy, or repair files."""
    reader = Reader()
    entries = bundle._entries(reader.document(selection), manifest=False)
    mappings = _request(reader.document(request))
    task = bundle._plain_path(task_dir, directory=True)
    raw = bundle._plain_path(raw_dir, directory=True)
    producer = None
    if mappings["pairs"]:
        if producer_dir is None:
            raise bundle.BundleError("PRODUCER_DIR_REQUIRED")
        producer = bundle._plain_path(producer_dir, directory=True)
    selected = {(entry["kind"], entry["path"]) for entry in entries}
    evidence_results = [_evidence(item, selected, raw, reader) for item in mappings["evidence"]]
    pair_results = [
        _pair(item, selected, task, raw, producer, reader)
        for item in mappings["pairs"]
        if producer is not None
    ]
    consistent = all(not result["issues"] for result in evidence_results) and all(
        pair["comparison"] in {"RAW_IDENTICAL", "CRLF_ONLY"}
        and pair["original"] in {"MATCHED", "NOT_REQUIRED"}
        for pair in pair_results
    )
    return {
        "status": "CONSISTENT" if consistent else "INCOMPLETE",
        "selected_files": len(entries),
        "checks": sum(result["checks"] for result in evidence_results),
        "log_references": sum(result["log_references"] for result in evidence_results),
        "bytes_read": reader.total,
        "evidence": evidence_results,
        "pairs": pair_results,
        "source_authenticated": False,
        "governance_effect": "none",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--producer-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        result = review_selection(
            args.task_dir, args.raw_dir, args.selection, args.request, args.producer_dir
        )
    except bundle.BundleError as exc:
        print(json.dumps({"status": "ERROR", "code": str(exc)}), file=sys.stderr)
        return 1
    except OSError:
        print(json.dumps({"status": "ERROR", "code": "IO_ERROR"}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "CONSISTENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
