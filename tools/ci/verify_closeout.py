"""Verify a post-merge task closeout against the exact PR Git snapshots."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path


def _ensure_src_on_path() -> None:
    repo_src = str(Path(__file__).resolve().parents[2] / "src")
    if repo_src not in sys.path:
        sys.path.insert(0, repo_src)


def verify_closeout(root: Path, base: str, head: str, task_id: str) -> None:
    """Delegate closeout ledger verification to the portable core module."""
    _ensure_src_on_path()
    from aiflow.closeout_check import verify_closeout as _verify_closeout

    _verify_closeout(root, base, head, task_id)


def verify_retained(root: Path, base: str, head: str, task_id: str) -> None:
    """Delegate retained ledger verification to the portable core module."""
    _ensure_src_on_path()
    from aiflow.closeout_check import verify_retained as _verify_retained

    _verify_retained(root, base, head, task_id)


def main(argv: Sequence[str] | None = None) -> int:
    """Delegate CLI closeout verification to the portable core module."""
    _ensure_src_on_path()
    from aiflow.closeout_check import main as _main

    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
