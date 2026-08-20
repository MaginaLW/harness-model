"""Command-line interface for aiflow."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from aiflow import __version__
from aiflow.errors import AiflowError
from aiflow.task_service import recover_task, start_task

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
                result = recover_task(Path.cwd(), arguments.recover)
            else:
                result = start_task(
                    Path.cwd(),
                    objective=arguments.objective,
                    allowed_scope=arguments.allow,
                    forbidden_actions=arguments.forbid_action,
                    allow_detached=arguments.allow_detached,
                )
            print(result.task_id)
            print(result.task_directory.resolve())
    except AiflowError as error:
        print(error.message, file=sys.stderr)
        return 1
    return 0
