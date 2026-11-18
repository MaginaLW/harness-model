"""Verify a post-merge task closeout against the exact PR Git snapshots."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

import yaml

from aiflow.contracts import require_valid_contract
from aiflow.decision_units import apply_risk_facts
from aiflow.errors import AiflowError
from aiflow.state import replay_events
from aiflow.task_service import _is_subject_sync_staged_patch, _require_merge_commit
from tools.ci.resolve_task import git_bytes


def _task_directory(task_id: str) -> str:
    if not re.fullmatch(r"TASK-[A-Z0-9][A-Z0-9-]*", task_id):
        raise ValueError("invalid task ID")
    return f".ai/tasks/{task_id}"


def verify_closeout(root: Path, base: str, head: str, task_id: str) -> None:
    directory = _task_directory(task_id)
    fork = git_bytes(root, "merge-base", base, head).decode("ascii").strip()
    changed = (
        git_bytes(root, "diff", "--no-renames", "--name-only", "-z", fork, head, "--", directory)
        .decode("utf-8")
        .split("\0")
    )
    if set(filter(None, changed)) != {f"{directory}/task.yaml", f"{directory}/events.jsonl"}:
        raise ValueError(f"{task_id}: closeout must update only task.yaml and events.jsonl")

    original = yaml.safe_load(git_bytes(root, "show", f"{fork}:{directory}/task.yaml"))
    current = yaml.safe_load(git_bytes(root, "show", f"{head}:{directory}/task.yaml"))
    require_valid_contract("task", original)
    require_valid_contract("task", current)
    identity = git_bytes(root, "show", f"{base}:.ai/repository-id").decode("utf-8").strip()
    if (original["task_id"], original["repository_id"], original["current_state"]) != (
        task_id,
        identity,
        "APPROVED_FOR_MERGE",
    ):
        raise ValueError(f"{task_id}: base task must be approved and belong to this repository")

    previous = git_bytes(root, "show", f"{fork}:{directory}/events.jsonl")
    history = git_bytes(root, "show", f"{head}:{directory}/events.jsonl")
    if not history.startswith(previous) or len(history[len(previous) :].splitlines()) != 1:
        raise ValueError(f"{task_id}: expected exactly one appended merge event")
    events = [json.loads(line) for line in history.splitlines()]
    if replay_events(events, task_id=task_id) != "MERGED":
        raise ValueError(f"{task_id}: closeout history did not reach MERGED")
    last = events[-1]
    if (
        last["event_type"] != "merge_recorded"
        or last["from_state"] != "APPROVED_FOR_MERGE"
        or current != {**original, "current_state": "MERGED", "updated_at": last["occurred_at"]}
    ):
        raise ValueError(f"{task_id}: expected the native close transition")

    merge = last["payload"].get("merge_commit")
    if not isinstance(merge, str) or last["payload"] != {"result": "merged", "merge_commit": merge}:
        raise ValueError(f"{task_id}: expected the native merge event payload")
    _require_merge_commit(
        root, merge, base_commit=original["base_commit"], subject_commit=original["subject_commit"]
    )
    if git_bytes(root, "merge-base", merge, base).decode("ascii").strip() != merge:
        raise ValueError(f"{task_id}: recorded merge is not in the target branch history")


def verify_retained(root: Path, base: str, head: str, task_id: str) -> None:
    directory = _task_directory(task_id)
    fork = git_bytes(root, "merge-base", base, head).decode("ascii").strip()
    current = yaml.safe_load(git_bytes(root, "show", f"{head}:{directory}/task.yaml"))
    require_valid_contract("task", current)
    identity = git_bytes(root, "show", f"{base}:.ai/repository-id").decode("utf-8").strip()
    history = git_bytes(root, "show", f"{head}:{directory}/events.jsonl")
    events = [json.loads(line) for line in history.splitlines()]
    state = replay_events(events, task_id=task_id)
    if (
        state not in {"FAILED", "BLOCKED"}
        or current["current_state"] != state
        or (current["task_id"], current["repository_id"]) != (task_id, identity)
    ):
        raise ValueError(f"{task_id}: expected this repository's failed or blocked task")
    if not git_bytes(root, "ls-tree", fork, "--", directory):
        return

    # Additions keep the old originals. Only these three materializations
    # may change in a retained ledger, and their content must follow its events.
    changes = (
        git_bytes(root, "diff", "--no-renames", "--name-status", "-z", fork, head, "--", directory)
        .decode("utf-8")
        .split("\0")
    )
    statuses = dict(zip(changes[1::2], changes[::2]))
    projections = {
        f"{directory}/{name}" for name in ("task.yaml", "approvals.json", "events.jsonl")
    }
    if any(
        status != "A" and (status != "M" or path not in projections)
        for path, status in statuses.items()
    ):
        raise ValueError(f"{task_id}: retained originals must not be changed or deleted")

    previous = git_bytes(root, "show", f"{fork}:{directory}/events.jsonl")
    if not history.startswith(previous):
        raise ValueError(f"{task_id}: retained event history was rewritten")
    original = yaml.safe_load(git_bytes(root, "show", f"{fork}:{directory}/task.yaml"))
    require_valid_contract("task", original)
    appended = events[len(previous.splitlines()) :]
    expected = original
    for event in appended:
        if expected["current_state"] != event["from_state"]:
            raise ValueError(f"{task_id}: retained state does not match original history")
        payload = event["payload"]
        kind = event["event_type"]
        if kind == "subject_commit_synchronized":
            updated = {
                **expected,
                "subject_commit": payload["new_subject_commit"],
                "updated_at": event["occurred_at"],
            }
            if not _is_subject_sync_staged_patch(expected, updated, event):
                raise ValueError(
                    f"{task_id}: subject synchronization does not match the original binding"
                )
            expected = updated
        elif kind == "risk_facts_recorded":
            expected, before, after = apply_risk_facts(
                expected, payload["decision_unit_id"], payload["after"]
            )
            if before != payload["before"] or after != payload["after"]:
                raise ValueError(f"{task_id}: risk facts do not match their recorded transition")
        elif kind in {"spec_frozen", "ask_answered"}:
            digest = (
                payload["spec_sha256"] if kind == "spec_frozen" else payload["specification_sha256"]
            )
            expected = {
                **expected,
                "frozen_spec_sha256": digest,
                "spec_frozen_at": event["occurred_at"],
            }
        expected = {
            **expected,
            "current_state": event["to_state"],
            "updated_at": event["occurred_at"],
        }
    if current != expected:
        raise ValueError(f"{task_id}: retained task differs from its event projection")

    approvals_path = f"{directory}/approvals.json"
    if approvals_path in statuses or any(
        event["event_type"] in {"approval_recorded", "spec_approved", "code_approved"}
        for event in appended
    ):
        original_approvals = (
            json.loads(git_bytes(root, "show", f"{fork}:{approvals_path}"))
            if git_bytes(root, "ls-tree", fork, "--", approvals_path)
            else []
        )
        expected_approvals = list(original_approvals)
        for event in appended:
            if event["event_type"] in {"approval_recorded", "spec_approved", "code_approved"}:
                for approval in event["payload"]["approvals"]:
                    if approval not in expected_approvals:
                        expected_approvals.append(approval)
        if json.loads(git_bytes(root, "show", f"{head}:{approvals_path}")) != expected_approvals:
            raise ValueError(
                f"{task_id}: approvals must preserve and append the recorded approvals"
            )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--retained", action="store_true", help="validate a retained FAILED/BLOCKED record"
    )
    args = parser.parse_args(argv)
    try:
        verify = verify_retained if args.retained else verify_closeout
        verify(Path.cwd(), args.base, args.head, args.task)
    except (
        ValueError,
        AiflowError,
        KeyError,
        OSError,
        subprocess.TimeoutExpired,
        yaml.YAMLError,
    ) as error:
        print(f"Ledger verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Verified {'retained record' if args.retained else 'closeout'} for {args.task}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
