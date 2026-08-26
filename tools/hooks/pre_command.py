from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from aiflow.errors import AiflowError, ContractError
from aiflow.observation import parse_observation
from aiflow.observation_service import apply_observation
from aiflow.policy import evaluate_action_permission, load_policy_bundle
from aiflow.task_service import read_task_record_strict
from aiflow.workflow import WorkflowFacts, evaluate_preconditions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check one normalized external action")
    parser.add_argument("--action", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--task")
    return parser


def _resolve_task_id(root: Path, explicit: str | None) -> str:
    if explicit is not None:
        read_task_record_strict(root, explicit)
        return explicit
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


def check_pre_command(
    root: Path, action: str, target: str, task_id: str | None = None
) -> tuple[bool, tuple[str, ...]]:
    if not target.strip():
        raise ContractError("Action target is required", code="HOOK_TARGET_INVALID")
    policy = load_policy_bundle(root)
    permission = evaluate_action_permission(policy, action)
    if not permission.allowed_automatically:
        resolved = _resolve_task_id(root, task_id)
        record = read_task_record_strict(root, resolved)
        observation = parse_observation(
            {
                "schema_version": "1.0",
                "task_id": resolved,
                "base_commit": str(record.task["base_commit"]),
                "subject_commit": str(record.task["subject_commit"]),
                "policy_sha256": policy.sha256,
                "source": "hook_pre_command",
                "kind": "high_risk_command",
                "summary": {
                    "action": permission.action,
                    "target_ref": target,
                },
            }
        )
        apply_observation(root, resolved, observation, actor="hook_pre_command")
    evaluation = evaluate_preconditions(
        WorkflowFacts(
            current_state="ACTION_CHECK",
            allowed_states=frozenset({"ACTION_CHECK"}),
            action_allowed=permission.allowed_automatically,
        )
    )
    return evaluation.passed, evaluation.failure_codes


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        passed, reasons = check_pre_command(
            Path.cwd().resolve(), arguments.action, arguments.target, arguments.task
        )
    except AiflowError as error:
        print(error.message, file=sys.stderr)
        return 1
    if not passed:
        print("pre-command denied: " + ",".join(reasons), file=sys.stderr)
        return 2
    print("pre-command allowed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
