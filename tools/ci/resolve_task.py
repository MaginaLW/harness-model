from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple, Sequence

import yaml

from aiflow.scope import matches_scope
from aiflow.task_service import COMMIT_PATTERN

TASK_PATTERN = re.compile(r"^\.ai/tasks/(TASK-[A-Z0-9][A-Z0-9-]*)/")


def git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=False,
        timeout=20,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if result.returncode:
        raise ValueError(
            result.stderr.decode("utf-8", errors="replace").strip() or "Git check failed"
        )
    return result.stdout


def _git_paths(root: Path, base: str, head: str) -> tuple[str, ...]:
    # Count both paths of a rename. The three-dot range excludes target-only changes.
    raw = git_bytes(root, "diff", "--no-renames", "--name-only", "-z", f"{base}...{head}", "--")
    return tuple(p for p in raw.decode("utf-8").split("\0") if p)


def resolve_task_id(root: Path, base: str, head: str, explicit: str | None = None) -> str:
    if not (root / ".ai" / "repository-id").is_file():
        raise ValueError(".ai/repository-id is missing")
    requested = (explicit or os.environ.get("AI_FLOW_TASK_ID", "")).strip()
    if requested:
        if not re.fullmatch(r"TASK-[A-Z0-9][A-Z0-9-]*", requested):
            raise ValueError("explicit task ID is invalid")
        if not (root / ".ai" / "tasks" / requested).is_dir():
            raise ValueError("explicit task directory is missing")
        return requested
    candidates = {
        match.group(1)
        for path in _git_paths(root, base, head)
        if (match := TASK_PATTERN.match(path)) is not None
    }
    if len(candidates) != 1:
        raise ValueError(
            "base-to-head diff must identify exactly one .ai/tasks/TASK-* directory; "
            "set AI_FLOW_TASK_ID when the task is intentionally explicit"
        )
    return next(iter(candidates))


class PullRequestRoute(NamedTuple):
    bootstrap_active: bool
    task_id: str | None
    closeouts: tuple[str, ...]
    retained: tuple[str, ...]


def _bootstrap_active(root: Path, base: str) -> bool:
    path = ".ai/bootstrap-mode.yaml"
    if not git_bytes(root, "ls-tree", base, "--", path):
        return False
    lines = git_bytes(root, "show", f"{base}:{path}").splitlines()
    return b"mode: bootstrap_auto" in lines and b"status: active" in lines


def _governed_paths(root: Path, base: str, paths: Sequence[str]) -> set[str]:
    policy = yaml.safe_load(git_bytes(root, "show", f"{base}:.ai/policy/hard-rules.yaml"))
    for rule in policy["rules"]:
        if rule["id"] == "HARD-REVIEW-GOVERNANCE-SURFACE":
            for condition in rule["conditions"]:
                if (
                    condition["field"] == "impact_scope"
                    and condition["operator"] == "overlaps_paths"
                ):
                    return {
                        path
                        for path in paths
                        if any(matches_scope(path, pat) for pat in condition["value"])
                    }
    raise ValueError("base policy is missing the governance scope rule")


def _task_at_commit(root: Path, head: str, task_id: str) -> dict[str, Any]:
    record = yaml.safe_load(git_bytes(root, "show", f"{head}:.ai/tasks/{task_id}/task.yaml"))
    if not isinstance(record, dict) or record.get("task_id") != task_id:
        raise ValueError(f"task identity mismatch: {task_id}")
    return record


def classify_pr(root: Path, base: str, head: str, explicit: str | None = None) -> PullRequestRoute:
    paths = _git_paths(root, base, head)
    active = _bootstrap_active(root, base)
    outside_tasks = [p for p in paths if not TASK_PATTERN.match(p)]
    task_ids = sorted({match[1] for p in paths if (match := TASK_PATTERN.match(p))})
    closeouts: list[str] = []
    retained: list[str] = []
    candidates: list[str] = []
    for task_id in task_ids:
        state = _task_at_commit(root, head, task_id)["current_state"]
        if state == "MERGED":
            closeouts.append(task_id)
        elif state in {"FAILED", "BLOCKED"}:
            retained.append(task_id)
        else:
            candidates.append(task_id)

    # A closeout records a merge that already occurred. Ordinary maintenance
    # docs may accompany it. In formal mode those docs require their own task.
    needs_task = bool(candidates or retained)
    if active:
        needs_task |= bool(_governed_paths(root, base, outside_tasks))
    else:
        needs_task |= bool(outside_tasks) or not closeouts
    selected = None
    if needs_task:
        requested = (explicit or os.environ.get("AI_FLOW_TASK_ID", "")).strip()
        if requested:
            selected = resolve_task_id(root, base, head, requested)
            if (
                selected not in task_ids
                and _task_at_commit(root, head, selected)["current_state"] != "APPROVED_FOR_MERGE"
            ):
                raise ValueError("explicit task is not approved at the PR head")
            if (
                selected in closeouts
                or selected in retained
                or (candidates and selected not in candidates)
            ):
                raise ValueError("explicit task is not an implementation candidate for this PR")
        elif len(candidates) == 1:
            selected = candidates[0]
        else:
            raise ValueError(
                "PR requires exactly one implementation task; set AI_FLOW_TASK_ID if ambiguous"
            )
    return PullRequestRoute(active, selected, tuple(closeouts), tuple(retained))


def verify_implementation_range(root: Path, base: str, head: str, route: PullRequestRoute) -> None:
    """Require the PR's governed implementation to begin within the reviewed task range."""
    if route.task_id is None:
        return
    task_base = _task_at_commit(root, head, route.task_id).get("base_commit")
    if not isinstance(task_base, str) or not COMMIT_PATTERN.fullmatch(task_base):
        raise ValueError(f"{route.task_id}: invalid recorded base commit")
    # Use the PR-side contribution present at task creation, including paths
    # renamed later. Three-dot excludes changes already on the target branch.
    preceding = _git_paths(root, base, task_base)
    companions = set(route.closeouts + route.retained)
    outside = sorted(
        path
        for path in preceding
        if not (match := TASK_PATTERN.match(path)) or match[1] not in companions
    )
    if route.bootstrap_active and outside:
        outside = sorted(_governed_paths(root, base, outside))
    if outside:
        raise ValueError(f"{route.task_id}: PR changes precede task base: {', '.join(outside)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve task governance for CI")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--task")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--route", action="store_true", help="include maintenance and closeout routing"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path.cwd().resolve()
    try:
        if args.route:
            route = classify_pr(root, args.base, args.head, args.task)
            verify_implementation_range(root, args.base, args.head, route)
            lines = (
                f"bootstrap_active={str(route.bootstrap_active).lower()}\n"
                f"task_id={route.task_id or ''}\n"
                f"closeouts={' '.join(route.closeouts)}\n"
                f"retained={' '.join(route.retained)}\n"
            )
        else:
            lines = f"task_id={resolve_task_id(root, args.base, args.head, args.task)}\n"
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired, yaml.YAMLError) as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.output is None:
        print(lines, end="")
    else:
        with args.output.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
