"""Verify ancestor consistency and merge commit integrity for a closed task."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from aiflow.errors import AiflowError, ContractError
from aiflow.git_context import resolve_repository_root
from aiflow.task_service import _require_merge_commit, read_task_record_strict


def verify_closeout(repository_root: Path, task_id: str) -> None:
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    record = read_task_record_strict(repository_root, task_id)
    if record.task.get("current_state") != "MERGED":
        raise ContractError("Task is not in MERGED state", code="CLOSEOUT_NOT_MERGED")

    merge_events = [event for event in record.events if event.get("event_type") == "merge_recorded"]
    if not merge_events:
        raise ContractError(
            "No merge_recorded event found in task history", code="CLOSEOUT_EVENT_MISSING"
        )

    last_merge = merge_events[-1]
    payload = last_merge.get("payload") or {}
    merge_commit = payload.get("merge_commit")
    if not isinstance(merge_commit, str):
        raise ContractError("Merge commit missing from event payload", code="CLOSE_COMMIT_INVALID")

    base_commit = str(record.task.get("base_commit"))
    subject_commit = str(record.task.get("subject_commit"))

    _require_merge_commit(
        repository_root,
        merge_commit,
        base_commit=base_commit,
        subject_commit=subject_commit,
    )
    print(f"Task {task_id} closeout verified: merge commit {merge_commit} is ancestral.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify task closeout integrity in CI")
    parser.add_argument("--task", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = resolve_repository_root(Path.cwd())
    try:
        verify_closeout(root, args.task)
    except ContractError as err:
        print(f"Closeout verification failed: {err.message} ({err.code})", file=sys.stderr)
        return 1
    except AiflowError as err:
        print(f"Closeout verification failed: {err.message} ({err.code})", file=sys.stderr)
        return 1
    except Exception as err:
        print(f"Closeout verification error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
