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


def _check_reference(repository: Path, reference: dict[str, Any] | None) -> dict[str, Any]:
    from approval_overhead import LedgerDataError, _snapshot_git

    observed: dict[str, Any] = {
        "git_blob": None,
        "mode": None,
        "bytes_read": None,
        "content_sha256": None,
    }
    result = {"status": "not_checked", "reason": "REFERENCE_NOT_PROVIDED", "observed": observed}
    if reference is None:
        return result
    if reference["kind"] != "git":
        result["reason"] = "PR_REFERENCE_NOT_READ"
        return result
    path = reference["path"]
    if not path.startswith("docs/"):
        result["reason"] = "PATH_OUTSIDE_DOCS_SCOPE"
        return result
    try:
        commit = reference["source_commit"]
        if _snapshot_git(repository, "cat-file", "-t", commit).strip() != b"commit":
            result.update(status="conflict", reason="COMMIT_TYPE_MISMATCH")
            return result
        tree = _snapshot_git(repository, "--literal-pathspecs", "ls-tree", "-z", commit, "--", path)
        if not tree:
            result.update(status="unavailable", reason="PATH_NOT_IN_TREE")
            return result
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
            return result
        if blob != reference["git_blob"]:
            result.update(status="conflict", reason="GIT_BLOB_MISMATCH")
            return result
        size = int(_snapshot_git(repository, "cat-file", "-s", blob))
        if size < 0:
            raise ValueError("invalid object size")
        if size > _MAX_BLOB_BYTES:
            result["reason"] = "BLOB_SIZE_LIMIT"
            return result
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
    return result


def build_source_checks(repository: Path, document: object) -> dict[str, Any]:
    """Read only explicitly referenced docs blobs; leave semantic source conditions open."""
    from approval_overhead import _snapshot_git
    from review_detection_input import build_detection_input

    declarations = build_detection_input(document)
    repository = repository.resolve(strict=True)
    root = _snapshot_git(repository, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    if Path(root).resolve(strict=True) != repository:
        raise ValueError("explicit repository root is required")
    checks: list[dict[str, Any]] = []
    cache: dict[tuple[str, str, str], dict[str, Any]] = {}
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
                checked = cache[key]
            else:
                checked = _check_reference(repository, reference)
                if key is not None:
                    cache[key] = checked
            checks.append(
                {
                    "input_locator": locator,
                    "reported_reference": deepcopy(reference),
                    **deepcopy(checked),
                    "locator_resolution": "not_evaluated",
                }
            )
    return {
        "schema_version": "1.0",
        "measurement": "review_detection_git_source_checks",
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
    arguments = parser.parse_args(argv)
    try:
        original = sys.stdin.buffer.read()
        document = json.loads(
            original.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        report = build_source_checks(arguments.repository, document)
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
