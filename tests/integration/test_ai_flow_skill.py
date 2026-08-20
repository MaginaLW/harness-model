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
REQUIRED_COMMANDS = {
    "answer",
    "approve",
    "begin",
    "classify",
    "close",
    "escalate",
    "freeze",
    "gate",
    "resolve",
    "start",
    "status",
    "verify",
}


def _skill_parts() -> tuple[dict[str, object], str]:
    text = SKILL.read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def _cli_commands() -> set[str]:
    parser = build_parser()
    action = next(item for item in parser._actions if isinstance(item, _SubParsersAction))
    return set(action.choices)


def test_skill_is_discoverable_and_scoped_to_mutating_work() -> None:
    frontmatter, body = _skill_parts()

    assert frontmatter["name"] == "ai-flow"
    description = str(frontmatter["description"])
    assert "code, configuration, CI" in description
    assert "Purely read-only" in description
    assert "grants no permission" in body


def test_skill_orchestrates_only_live_cli_commands_in_order() -> None:
    _, body = _skill_parts()
    referenced = set(COMMAND_PATTERN.findall(body))

    assert REQUIRED_COMMANDS <= referenced
    assert referenced <= _cli_commands()
    lifecycle = ["start", "classify", "freeze", "begin", "verify", "gate", "close"]
    offsets = [body.index(f"aiflow {command}") for command in lifecycle]
    assert offsets == sorted(offsets)


def test_skill_links_current_templates_and_repository_guidance() -> None:
    _, body = _skill_parts()
    links = LINK_PATTERN.findall(body)

    assert {
        "../../../.ai/templates/ask.md",
        "../../../.ai/templates/review-package.md",
        "../../../.ai/templates/spec.md",
    } <= set(links)
    for link in links:
        assert (SKILL.parent / link).resolve().exists(), link


def test_skill_preserves_human_gates_and_escalation_boundaries() -> None:
    _, body = _skill_parts()

    assert "2–4 substantively different options" in body
    assert "benefits, costs, and risks" in body
    assert "human owns directional and risk decisions" in body
    assert "Code approval never authorizes an external action" in body
    for trigger in ("scope expands", "new dependency", "network", "credentials", "failures repeat"):
        assert trigger in body
    for prohibited in (
        "Never edit task state directly",
        "fabricate evidence",
        "skip required commands",
        "use code approval as action approval",
    ):
        assert prohibited in body


def test_skill_does_not_copy_policy_or_state_matrices() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "BLOCK > REVIEW > ASK > AUTO" not in text
    assert "ROUTE-DEFAULT-REVIEW" not in text
    assert "NEW -> CLASSIFIED" not in text
    assert "NEW → CLASSIFIED" not in text
    assert not re.search(r"\b(?:ROUTE|VERIFY|PERMISSION)-[A-Z0-9-]+\b", text)
