from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from aiflow.errors import AiflowError, ContractError
from aiflow.policy import evaluate_action_permission, load_policy_bundle
from aiflow.workflow import WorkflowFacts, evaluate_preconditions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check one normalized external action")
    parser.add_argument("--action", required=True)
    parser.add_argument("--target", required=True)
    return parser


def check_pre_command(root: Path, action: str, target: str) -> tuple[bool, tuple[str, ...]]:
    if not target.strip():
        raise ContractError("Action target is required", code="HOOK_TARGET_INVALID")
    permission = evaluate_action_permission(load_policy_bundle(root), action)
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
            Path.cwd().resolve(), arguments.action, arguments.target
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
