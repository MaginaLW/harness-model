"""Command-line interface for aiflow."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from aiflow import __version__
from aiflow.errors import AiflowError
from aiflow.task_service import begin_task, close_task, recover_task, start_task

DESCRIPTION = "Auditable AI code collaboration CLI"


def build_parser() -> ArgumentParser:
    """Build the stage-one command parser."""
    parser = ArgumentParser(prog="aiflow", description=DESCRIPTION)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    start = subparsers.add_parser("start", help="create or recover an AI Flow task")
    start.add_argument("--objective")
    start.add_argument("--allow", action="append", default=[])
    start.add_argument("--forbid-action", action="append", default=[])
    start.add_argument("--allow-detached", action="store_true")
    start.add_argument("--recover", metavar="TASK-ID")
    begin = subparsers.add_parser("begin", help="begin implementation or retry")
    begin.add_argument("task_id")
    begin.add_argument("--actor", required=True)
    begin.add_argument("--reason")
    close = subparsers.add_parser("close", help="record an externally completed merge")
    close.add_argument("task_id")
    close.add_argument("--result", required=True, choices=["merged"])
    close.add_argument("--merge-commit", required=True)
    close.add_argument("--actor", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the root command without exposing unfinished business subcommands."""
    try:
        arguments = build_parser().parse_args(argv)
        if arguments.command == "start":
            if arguments.recover is not None:
                if arguments.objective is not None or arguments.allow or arguments.forbid_action:
                    raise AiflowError(
                        "Recovery cannot be combined with creation arguments",
                        code="START_INPUT_INVALID",
                    )
                start_result = recover_task(Path.cwd(), arguments.recover)
            else:
                start_result = start_task(
                    Path.cwd(),
                    objective=arguments.objective,
                    allowed_scope=arguments.allow,
                    forbidden_actions=arguments.forbid_action,
                    allow_detached=arguments.allow_detached,
                )
            print(start_result.task_id)
            print(start_result.task_directory.resolve())
        elif arguments.command == "begin":
            transition_result = begin_task(
                Path.cwd(),
                arguments.task_id,
                actor=arguments.actor,
                reason=arguments.reason,
            )
            print(f"{arguments.task_id} {transition_result.task['current_state']}")
        elif arguments.command == "close":
            transition_result = close_task(
                Path.cwd(),
                arguments.task_id,
                result=arguments.result,
                merge_commit=arguments.merge_commit,
                actor=arguments.actor,
            )
            print(f"{arguments.task_id} {transition_result.task['current_state']}")
    except AiflowError as error:
        print(error.message, file=sys.stderr)
        return 1
    return 0
