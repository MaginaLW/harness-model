from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from aiflow.contracts import SCHEMA_RELATIVE_DIRECTORY, schema_directory_context
from aiflow.errors import AiflowError, ContractError
from aiflow.git_context import resolve_repository_root
from aiflow.observation import parse_observation
from aiflow.observation_service import apply_observation
from aiflow.policy import load_policy_bundle
from aiflow.scope import assess_scope, collect_changed_paths
from aiflow.status_service import summarize_task
from aiflow.task_service import read_task_record_strict
from aiflow.workflow import WorkflowFacts, evaluate_preconditions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check AI Flow scope before commit")
    parser.add_argument("--task")
    return parser


_TASK_PATH_PATTERN = re.compile(r"^\.ai/tasks/(TASK-[A-Z0-9][A-Z0-9-]*)/")


def _git_candidate_tasks(root: Path) -> set[str]:
    candidates: set[str] = set()
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    try:
        status_res = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z"],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=10,
            env=env,
        )
        if status_res.returncode == 0:
            for entry in status_res.stdout.split(b"\x00"):
                if not entry:
                    continue
                text = entry.decode("utf-8", errors="replace").replace("\\", "/")
                for candidate_text in (text[3:], text):
                    match = _TASK_PATH_PATTERN.match(candidate_text)
                    if match:
                        candidates.add(match.group(1))

        mb_res = subprocess.run(
            ["git", "merge-base", "main", "HEAD"],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=10,
            env=env,
        )
        if mb_res.returncode == 0:
            merge_base = mb_res.stdout.decode("utf-8", errors="replace").strip()
            if merge_base and len(merge_base) == 40:
                diff_res = subprocess.run(
                    ["git", "diff", "--name-only", "-z", f"{merge_base}...HEAD"],
                    cwd=root,
                    capture_output=True,
                    check=False,
                    timeout=10,
                    env=env,
                )
                if diff_res.returncode == 0:
                    for entry in diff_res.stdout.split(b"\x00"):
                        if not entry:
                            continue
                        text = entry.decode("utf-8", errors="replace").replace("\\", "/")
                        match = _TASK_PATH_PATTERN.match(text)
                        if match:
                            candidates.add(match.group(1))
    except (OSError, subprocess.SubprocessError):
        pass
    return candidates


def _resolve_task_id(root: Path, explicit: str | None) -> str:
    if explicit is not None:
        read_task_record_strict(root, explicit)
        return explicit

    git_candidates = _git_candidate_tasks(root)
    active_git: list[str] = []
    for candidate in sorted(git_candidates):
        try:
            record = read_task_record_strict(root, candidate)
        except Exception:
            continue
        if record.task.get("current_state") != "MERGED":
            active_git.append(candidate)

    if len(active_git) == 1:
        return active_git[0]
    if len(active_git) > 1:
        raise ContractError(
            "Exactly one active task is required when --task is omitted",
            code="HOOK_TASK_AMBIGUOUS",
        )

    task_root = root / ".ai" / "tasks"
    active = []
    if task_root.is_dir():
        for directory in sorted(task_root.glob("TASK-*")):
            if not directory.is_dir():
                continue
            record = read_task_record_strict(root, directory.name)
            if record.task["current_state"] != "MERGED":
                active.append(directory.name)
    if len(active) != 1:
        raise ContractError(
            "Exactly one active task is required when --task is omitted",
            code="HOOK_TASK_AMBIGUOUS",
        )
    return active[0]


def check_pre_commit(root: Path, task_id: str | None) -> tuple[bool, tuple[str, ...]]:
    try:
        root = resolve_repository_root(root)
    except Exception:
        root = root.resolve()
    with schema_directory_context(root / SCHEMA_RELATIVE_DIRECTORY):
        resolved = _resolve_task_id(root, task_id)
        record = read_task_record_strict(root, resolved)
        summary = summarize_task(root, resolved)
        subject = record.task.get("subject_commit") or record.task["base_commit"]
        changed = collect_changed_paths(
            root,
            base_commit=str(record.task["base_commit"]),
            subject_commit=str(subject),
            head_commit=summary.observed_head,
        )
        scope = assess_scope(
            changed.paths,
            tuple(record.task["allowed_scope"]),
            task_id=resolved,
            repository_root=root,
            cache_patterns=(),
        )
        if scope.out_of_scope:
            policy = load_policy_bundle(root)
            observation = parse_observation(
                {
                    "schema_version": "1.0",
                    "task_id": resolved,
                    "base_commit": str(record.task["base_commit"]),
                    "subject_commit": str(subject),
                    "policy_sha256": policy.sha256,
                    "source": "hook_pre_commit",
                    "kind": "scope_out_of_bounds",
                    "summary": {"paths": list(scope.out_of_scope)},
                }
            )
            apply_observation(root, resolved, observation, actor="hook_pre_commit")
        evaluation = evaluate_preconditions(
            WorkflowFacts(
                current_state=summary.current_state,
                allowed_states=frozenset({"IMPLEMENTING"}),
                scope_unchanged=scope.passed,
            )
        )
        return evaluation.passed, evaluation.failure_codes


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        passed, reasons = check_pre_commit(Path.cwd().resolve(), arguments.task)
    except AiflowError as error:
        print(error.message, file=sys.stderr)
        return 1
    if not passed:
        print("pre-commit denied: " + ",".join(reasons), file=sys.stderr)
        return 2
    print("pre-commit allowed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
