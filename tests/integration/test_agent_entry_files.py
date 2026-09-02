from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS_FILE = ROOT / "AGENTS.md"
CLAUDE_FILE = ROOT / "CLAUDE.md"
BOOTSTRAP_MARKER = ROOT / ".ai" / "bootstrap-mode.yaml"
AI_FLOW_SKILL = ROOT / ".claude" / "skills" / "ai-flow" / "SKILL.md"
CORE_PRINCIPLES = (
    "必须进入 AI Flow",
    "不得绕过任务状态、允许范围、所需批准或验证门",
    "不得自行降低分流或验证等级",
    "高风险动作必须单独获批",
    "批准和证据必须绑定当前规格、Policy 与 `subject_commit`",
    "不在 Agent 文件中复制规则表",
)
FORBIDDEN_RULE_COPIES = (
    "BLOCK > REVIEW > ASK > AUTO",
    "ROUTE-DEFAULT-REVIEW",
    "NEW -> CLASSIFIED",
    "NEW → CLASSIFIED",
    "verification-levels:",
)
LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def test_agents_entry_has_complete_shared_principles_and_remains_brief() -> None:
    text = AGENTS_FILE.read_text(encoding="utf-8")

    assert all(principle in text for principle in CORE_PRINCIPLES)
    assert "python -m aiflow --help" in text
    assert len(text.splitlines()) <= 25
    assert not any(copied_rule in text for copied_rule in FORBIDDEN_RULE_COPIES)
    assert not re.search(r"\b(?:ROUTE|VERIFY|PERMISSION)-[A-Z0-9-]+\b", text)


def test_claude_entry_is_brief_adapter_without_copied_core_principles() -> None:
    text = CLAUDE_FILE.read_text(encoding="utf-8")

    assert "平台适配入口" in text
    assert "完整阅读并遵守 [AGENTS.md](AGENTS.md)" in text
    assert "唯一共同权威" in text
    assert "python -m aiflow --help" in text
    assert len(text.splitlines()) <= 12
    assert not any(principle in text for principle in CORE_PRINCIPLES)
    assert not any(copied_rule in text for copied_rule in FORBIDDEN_RULE_COPIES)
    assert not re.search(r"\b(?:ROUTE|VERIFY|PERMISSION)-[A-Z0-9-]+\b", text)


@pytest.mark.parametrize("entry_file", (AGENTS_FILE, CLAUDE_FILE), ids=lambda path: path.name)
def test_entry_file_relative_links_exist(entry_file: Path) -> None:
    links = LINK_PATTERN.findall(entry_file.read_text(encoding="utf-8"))

    assert links
    for link in links:
        assert "://" not in link
        assert (ROOT / link).exists(), link


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


def test_formal_self_governance_is_explicit_in_shared_agent_authority() -> None:
    assert not BOOTSTRAP_MARKER.exists()
    text = AGENTS_FILE.read_text(encoding="utf-8")
    assert ".ai/bootstrap-mode.yaml" in text
    assert "AI Flow 正式自用治理已启用" in text
    assert "task-free 自举例外" in text
    assert "项目所有者" in text
    skill = AI_FLOW_SKILL.read_text(encoding="utf-8")
    assert "Governance activation" in skill
    assert "bootstrap marker is intentionally absent" in skill
    assert "task-free bootstrap exception" in skill
