from __future__ import annotations

import re
from argparse import _SubParsersAction
from pathlib import Path

import yaml

from aiflow.cli import build_parser

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".claude" / "skills" / "ai-flow" / "SKILL.md"
COMMAND_PATTERN = re.compile(r"`aiflow\s+([a-z-]+)\b")
LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def _skill_parts() -> tuple[dict[str, object], str]:
    text = SKILL.read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def _cli_commands() -> set[str]:
    parser = build_parser()
    action = next(item for item in parser._actions if isinstance(item, _SubParsersAction))
    return set(action.choices)


def test_skill_frontmatter_is_valid() -> None:
    frontmatter, body = _skill_parts()

    assert frontmatter["name"] == "ai-flow"
    assert str(frontmatter["description"]).strip()
    assert body.strip()


def test_skill_references_only_live_cli_commands() -> None:
    _, body = _skill_parts()
    referenced = set(COMMAND_PATTERN.findall(body))

    assert referenced
    assert referenced <= _cli_commands()


def test_skill_relative_links_resolve() -> None:
    _, body = _skill_parts()
    links = LINK_PATTERN.findall(body)

    assert links
    for link in links:
        assert (SKILL.parent / link).resolve().exists(), link
