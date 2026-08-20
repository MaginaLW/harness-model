"""Command-line interface for aiflow."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Sequence

from aiflow import __version__
from aiflow.errors import AiflowError

DESCRIPTION = "Auditable AI code collaboration CLI"


def build_parser() -> ArgumentParser:
    """Build the minimal stage-one command parser."""
    parser = ArgumentParser(prog="aiflow", description=DESCRIPTION)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the root command without exposing unfinished business subcommands."""
    try:
        build_parser().parse_args(argv)
    except AiflowError as error:
        print(error.message, file=sys.stderr)
        return 1
    return 0
