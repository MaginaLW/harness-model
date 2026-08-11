"""Command-line interface for aiflow."""

from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Sequence

from aiflow import __version__

DESCRIPTION = "Auditable AI code collaboration CLI"


def build_parser() -> ArgumentParser:
    """Build the minimal stage-one command parser."""
    parser = ArgumentParser(prog="aiflow", description=DESCRIPTION)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the root command without exposing unfinished business subcommands."""
    build_parser().parse_args(argv)
    return 0
