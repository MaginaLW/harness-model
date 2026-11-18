from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from aiflow.contracts import SCHEMA_RELATIVE_DIRECTORY, schema_directory_context
from aiflow.errors import AiflowError
from aiflow.git_context import resolve_repository_root
from aiflow.observation import parse_observation
from aiflow.observation_service import apply_observation
from aiflow.policy import load_policy_bundle
from aiflow.scope import assess_scope, collect_changed_paths
from aiflow.status_service import summarize_task
from aiflow.task_service import read_task_record_strict, resolve_hook_task_id
from aiflow.workflow import WorkflowFacts, evaluate_preconditions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check AI Flow scope before commit")
    parser.add_argument("--task")
    return parser


def check_pre_commit(root: Path, task_id: str | None) -> tuple[bool, tuple[str, ...]]:
    root = resolve_repository_root(root)
    with schema_directory_context(root / SCHEMA_RELATIVE_DIRECTORY):
        resolved = resolve_hook_task_id(root, task_id)
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
