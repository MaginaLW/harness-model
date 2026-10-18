"""Check explicit committed documentation references without admitting observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

_MAX_BLOB_BYTES = 1024 * 1024
_OPPORTUNITY_REFS = (
    "contract_ref",
    "object_ref",
    "instance_ref",
    "adjudication_ref",
    "matching_ref",
)


def _check_reference(
    repository: Path, reference: dict[str, Any] | None
) -> tuple[dict[str, Any], bytes | None]:
    from approval_overhead import LedgerDataError, _snapshot_git

    observed: dict[str, Any] = {
        "git_blob": None,
        "mode": None,
        "bytes_read": None,
        "content_sha256": None,
    }
    result = {"status": "not_checked", "reason": "REFERENCE_NOT_PROVIDED", "observed": observed}
    if reference is None:
        return result, None
    if reference["kind"] != "git":
        result["reason"] = "PR_REFERENCE_NOT_READ"
        return result, None
    path = reference["path"]
    if not path.startswith("docs/"):
        result["reason"] = "PATH_OUTSIDE_DOCS_SCOPE"
        return result, None
    contents: bytes | None = None
    try:
        commit = reference["source_commit"]
        if _snapshot_git(repository, "cat-file", "-t", commit).strip() != b"commit":
            result.update(status="conflict", reason="COMMIT_TYPE_MISMATCH")
            return result, None
        tree = _snapshot_git(repository, "--literal-pathspecs", "ls-tree", "-z", commit, "--", path)
        if not tree:
            result.update(status="unavailable", reason="PATH_NOT_IN_TREE")
            return result, None
        entries = tree.split(b"\0")
        if len(entries) != 2 or entries[1]:
            raise ValueError("unexpected tree response")
        metadata, actual_path = entries[0].split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        if actual_path != path.encode("utf-8") or re.fullmatch(r"[0-9a-f]{40}", blob) is None:
            raise ValueError("unexpected tree entry")
        observed.update(git_blob=blob if kind == "blob" else None, mode=mode)
        if mode not in {"100644", "100755"} or kind != "blob":
            result["reason"] = "NON_REGULAR_GIT_ENTRY"
            return result, None
        if blob != reference["git_blob"]:
            result.update(status="conflict", reason="GIT_BLOB_MISMATCH")
            return result, None
        size = int(_snapshot_git(repository, "cat-file", "-s", blob))
        if size < 0:
            raise ValueError("invalid object size")
        if size > _MAX_BLOB_BYTES:
            result["reason"] = "BLOB_SIZE_LIMIT"
            return result, None
        contents = _snapshot_git(repository, "cat-file", "blob", blob)
        if len(contents) != size:
            raise ValueError("incomplete object read")
        observed.update(bytes_read=size, content_sha256=hashlib.sha256(contents).hexdigest())
        object_id = hashlib.sha1(f"blob {size}\0".encode("ascii") + contents).hexdigest()
        if object_id != blob:
            result.update(status="conflict", reason="GIT_OBJECT_HASH_MISMATCH")
        else:
            result.update(status="matched_git_object", reason="MATCHED_GIT_OBJECT")
    except (LedgerDataError, ValueError, UnicodeError):
        result.update(status="unavailable", reason="GIT_READ_UNAVAILABLE")
    return result, contents if result["status"] == "matched_git_object" else None


def _resolve_locator(contents: bytes | None, locator: str) -> dict[str, Any]:
    observed: dict[str, Any] = dict.fromkeys(
        ("start_line", "end_line", "byte_start", "byte_end", "span_sha256")
    )
    result = {"status": "not_evaluated", "reason": "SOURCE_NOT_MATCHED", "observed": observed}
    if contents is None:
        return result
    try:
        contents.decode("utf-8")
    except UnicodeDecodeError:
        result["reason"] = "DOCUMENT_ENCODING_UNSUPPORTED"
        return result
    if b"\0" in contents:
        result["reason"] = "DOCUMENT_ENCODING_UNSUPPORTED"
        return result
    result["reason"] = "UNSUPPORTED_LOCATOR"
    if not locator.startswith("lines-v1:"):
        return result
    result.update(status="invalid_selector", reason="INVALID_LINE_SELECTOR")
    match = re.fullmatch(r"lines-v1:L([1-9][0-9]*)-L([1-9][0-9]*):sha256=([0-9a-f]{64})", locator)
    if match is None:
        return result
    first, last, expected = match.groups()
    digit_limit = len(str(len(contents)))
    if len(first) > digit_limit or len(last) > digit_limit:
        return result
    start, end = int(first), int(last)
    if start > end or end > len(contents):
        return result
    ends = [index + 1 for index, byte in enumerate(contents) if byte == 10]
    if contents and not contents.endswith(b"\n"):
        ends.append(len(contents))
    if end > len(ends):
        result.update(status="span_unavailable", reason="LINE_RANGE_NOT_PRESENT")
        return result
    byte_start = 0 if start == 1 else ends[start - 2]
    byte_end = ends[end - 1]
    actual = hashlib.sha256(contents[byte_start:byte_end]).hexdigest()
    observed.update(
        start_line=start,
        end_line=end,
        byte_start=byte_start,
        byte_end=byte_end,
        span_sha256=actual,
    )
    if actual == expected:
        result.update(status="matched_span", reason="MATCHED_LINE_SPAN")
    else:
        result.update(status="conflict", reason="SPAN_HASH_MISMATCH")
    return result


def build_source_checks(
    repository: Path, document: object, *, resolve_locators: bool = False
) -> dict[str, Any]:
    """Read only explicitly referenced docs blobs; leave semantic source conditions open."""
    from approval_overhead import _snapshot_git
    from review_detection_input import build_detection_input

    declarations = build_detection_input(document)
    repository = repository.resolve(strict=True)
    root = _snapshot_git(repository, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    if Path(root).resolve(strict=True) != repository:
        raise ValueError("explicit repository root is required")
    checks: list[dict[str, Any]] = []
    cache: dict[tuple[str, str, str], tuple[dict[str, Any], bytes | None]] = {}
    for index, candidate in enumerate(declarations["reported_candidates"]):
        location = f"$.candidates[{index}]"
        references = [
            (f"{location}.refs.{role}", reference)
            for role, reference in sorted(candidate["refs"].items())
        ]
        references.extend(
            (f"{location}.opportunities[{opp_index}].{field}", opportunity[field])
            for opp_index, opportunity in enumerate(candidate["opportunities"])
            for field in _OPPORTUNITY_REFS
        )
        for locator, reference in references:
            key = (
                (reference["source_commit"], reference["path"], reference["git_blob"])
                if reference is not None and reference["kind"] == "git"
                else None
            )
            if key is not None and key in cache:
                checked, contents = cache[key]
            else:
                checked, contents = _check_reference(repository, reference)
                if key is not None:
                    cache[key] = checked, contents
            item = {
                "input_locator": locator,
                "reported_reference": deepcopy(reference),
                **deepcopy(checked),
                "locator_resolution": "not_evaluated",
            }
            if resolve_locators:
                resolution = _resolve_locator(contents, reference["locator"] if reference else "")
                item.update(locator_check=resolution, locator_resolution=resolution["status"])
            checks.append(item)
    return {
        "schema_version": "2.0" if resolve_locators else "1.0",
        "measurement": (
            "review_detection_git_locator_checks"
            if resolve_locators
            else "review_detection_git_source_checks"
        ),
        "repository": declarations["repository"],
        "admission_package": declarations["admission_package"],
        "window": deepcopy(declarations["window"]),
        "source_checks": checks,
        "next_source_checks": deepcopy(declarations["next_source_checks"]),
        "source_assurance": "local_git_object_checks",
        "repository_identity": "unknown",
        "source_atomicity": "unknown",
        **{
            field: declarations[field]
            for field in (
                "source_authenticity",
                "history_completeness",
                "observation_admission",
                "statistical_independence",
                "actual_model_identity",
                "method_status",
                "probability_status",
                "model_score_update_status",
                "execution_allowed",
                "permission_effect",
                "ledger_effect",
            )
        },
    }


def main(argv: list[str] | None = None) -> int:
    sys.dont_write_bytecode = True
    from approval_overhead import LedgerDataError
    from benchmark_reference import _reject_constant, _unique_object

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path, help="Explicit local Git worktree root")
    parser.add_argument(
        "--resolve-locators", action="store_true", help="Check explicit lines-v1 byte spans (v2)"
    )
    arguments = parser.parse_args(argv)
    try:
        original = sys.stdin.buffer.read()
        document = json.loads(
            original.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        report = build_source_checks(
            arguments.repository, document, resolve_locators=arguments.resolve_locators
        )
        report["input_sha256"] = hashlib.sha256(original).hexdigest()
        report["executed_tool_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except (LedgerDataError, OSError, ValueError, RecursionError):
        print(
            "review-detection-sources: supplied declarations or repository are invalid",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
