"""Determine pull request governance category by inspecting changed paths."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

import yaml

CHECKLIST_PREFIXES = (".github/", ".ai/", "src/aiflow/", "tools/ci/")
CHECKLIST_EXACT_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "pyproject.toml",
    "uv.lock",
    ".gitignore",
    ".gitattributes",
}
TASK_PATH_PATTERN = re.compile(r"^\.ai/tasks/(TASK-[A-Z0-9][A-Z0-9-]*)/")


def _is_bootstrap_active(root: Path, base: str) -> bool:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    result = subprocess.run(
        ["git", "show", f"{base}:.ai/bootstrap-mode.yaml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        env=env,
    )
    if result.returncode != 0:
        return False
    lines = result.stdout.splitlines()
    return "mode: bootstrap_auto" in lines and "status: active" in lines


def _changed_paths(root: Path, base: str, head: str) -> tuple[str, ...]:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    result = subprocess.run(
        ["git", "diff", "--name-only", "-z", f"{base}...{head}"],
        cwd=root,
        capture_output=True,
        check=False,
        timeout=20,
        env=env,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    raw = result.stdout.decode("utf-8")
    return tuple(p.replace("\\", "/") for p in raw.split("\0") if p)


def _matches_checklist(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        any(normalized.startswith(prefix) for prefix in CHECKLIST_PREFIXES)
        or normalized in CHECKLIST_EXACT_FILES
    )


def _read_task_state(root: Path, head: str, task_id: str) -> str | None:
    task_yaml = root / ".ai" / "tasks" / task_id / "task.yaml"
    text: str | None = None
    if task_yaml.is_file():
        try:
            text = task_yaml.read_text(encoding="utf-8")
        except OSError:
            text = None
    if text is None:
        env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
        res = subprocess.run(
            ["git", "show", f"{head}:.ai/tasks/{task_id}/task.yaml"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            env=env,
        )
        if res.returncode == 0:
            text = res.stdout
    if text is not None:
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                state = data.get("current_state")
                if isinstance(state, str):
                    return state
        except Exception:
            return None
    return None


def classify_pr(root: Path, base: str, head: str) -> tuple[str, str | None, bool]:
    """Return (category, task_id, bootstrap_active).

    Categories:
    - 'task_free'
    - 'task_closeout'
    - 'formal_governed'
    """
    bootstrap_active = _is_bootstrap_active(root, base)
    paths = _changed_paths(root, base, head)
    checklist_paths = [p for p in paths if _matches_checklist(p)]

    if not checklist_paths:
        return ("task_free", None, bootstrap_active)

    task_candidates: set[str] = set()
    all_in_tasks = True
    for p in checklist_paths:
        m = TASK_PATH_PATTERN.match(p)
        if m is None:
            all_in_tasks = False
            break
        task_candidates.add(m.group(1))

    if all_in_tasks and len(task_candidates) == 1:
        task_id = next(iter(task_candidates))
        state = _read_task_state(root, head, task_id)
        if state == "MERGED":
            return ("task_closeout", task_id, bootstrap_active)

    resolved_task_id = next(iter(task_candidates)) if len(task_candidates) == 1 else None
    return ("formal_governed", resolved_task_id, bootstrap_active)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify PR governance mode")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path.cwd().resolve()
    try:
        category, task_id, bootstrap_active = classify_pr(root, args.base, args.head)
    except Exception as err:
        print(f"Error classifying PR: {err}", file=sys.stderr)
        return 1

    lines = [
        f"category={category}\n",
        f"bootstrap_active={'true' if bootstrap_active else 'false'}\n",
        f"task_id={task_id or ''}\n",
    ]
    if args.output is None:
        sys.stdout.writelines(lines)
    else:
        with args.output.open("a", encoding="utf-8", newline="\n") as stream:
            stream.writelines(lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
