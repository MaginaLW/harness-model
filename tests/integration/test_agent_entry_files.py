from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENTRY_FILES = (ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / "README.md")
LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)]+)\)")


@pytest.mark.parametrize("entry_file", ENTRY_FILES, ids=lambda path: path.name)
def test_entry_file_relative_links_exist(entry_file: Path) -> None:
    links = LINK_PATTERN.findall(entry_file.read_text(encoding="utf-8"))

    assert links
    for link in links:
        if "://" in link:
            continue
        target = link.split("#", 1)[0]
        assert not target or (ROOT / target).exists(), link


def test_documented_startup_command_is_available() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "aiflow", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "Auditable AI code collaboration CLI" in result.stdout
