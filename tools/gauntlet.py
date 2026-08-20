from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from aiflow.errors import AiflowError
from aiflow.verification_service import verify_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Thin AI Flow verification wrapper")
    parser.add_argument("--task", required=True)
    parser.add_argument("--provisional", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        result = verify_task(
            Path.cwd(),
            arguments.task,
            actor="gauntlet",
            provisional=arguments.provisional,
        )
    except AiflowError as error:
        print(error.message, file=sys.stderr)
        return 1
    if arguments.format == "json":
        print(
            json.dumps(
                {
                    "task_id": result.task_id,
                    "state": result.state,
                    "conclusion": result.conclusion,
                    "evidence_path": str(result.evidence_path),
                    "reason_codes": list(result.reason_codes),
                },
                sort_keys=True,
            )
        )
    else:
        print(f"{result.task_id} {result.state or 'CI'} {result.conclusion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
