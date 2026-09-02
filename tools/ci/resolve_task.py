from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

TASK_PATTERN = re.compile(r"^\.ai/tasks/(TASK-[A-Z0-9][A-Z0-9-]*)/")


def _git_paths(root: Path, base: str, head: str) -> tuple[str, ...]:
    # Three-dot: compare against the merge base so the result is what this pull
    # request introduces. A two-dot diff compares the two trees, so an advancing
    # base branch reports its own task directories as head-side changes.
    result = subprocess.run(
        ["git", "diff", "--name-only", "-z", f"{base}...{head}"],
        cwd=root,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return tuple(path for path in result.stdout.decode("utf-8").split("\0") if path)


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve one AI Flow task for CI")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--task")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        task_id = resolve_task_id(
            Path.cwd().resolve(), arguments.base, arguments.head, arguments.task
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    line = f"task_id={task_id}\n"
    if arguments.output is None:
        print(line, end="")
    else:
        with arguments.output.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
