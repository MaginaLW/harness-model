from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_package_publish_requires_separate_action_approval() -> None:
    policy = yaml.safe_load(
        (ROOT / ".ai" / "policy" / "permissions.yaml").read_text(encoding="utf-8")
    )
    assert "package_publish" in policy["forbidden_automatic_actions"]
    rule = next(item for item in policy["rules"] if item["action"] == "package_publish")
    assert rule == {
        "id": "PERMISSION-DENY-AUTO-PACKAGE-PUBLISH",
        "priority": 630,
        "action": "package_publish",
        "effect": "deny_automatic",
        "required_approval": "action",
    }
