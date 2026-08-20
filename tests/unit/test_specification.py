"""Specification completeness and canonicalization tests."""

from __future__ import annotations

import pytest

from aiflow.errors import ContractError
from aiflow.specification import (
    assess_specification,
    normalize_specification,
    validate_specification,
)


def complete_specification() -> str:
    return """# Task Specification

## 目标

实现可测试的冻结服务。

## 范围

仅修改 `src/aiflow`。

## 非目标

不实现远端发布。

## 验收条件

- `pytest` 通过。

## 禁止动作

不得推送远端。

## 错误行为

非法输入返回稳定错误码。

## 回滚

恢复该任务的可逆文件。
"""


def test_normalization_is_stable_across_line_endings() -> None:
    content = complete_specification().replace("\n", "\r\n").rstrip("\r\n")
    assert normalize_specification(content) == complete_specification()
    assert (
        assess_specification(content).sha256
        == assess_specification(complete_specification()).sha256
    )


def test_complete_specification_has_a_bounded_summary() -> None:
    result = assess_specification(complete_specification())
    assert result.valid is True
    assert result.issues == ()
    assert result.summary == {
        "goal": "present",
        "scope": "present",
        "acceptance": "present",
        "forbidden_actions": "present",
        "error_behavior": "present",
        "rollback": "present",
    }


@pytest.mark.parametrize(
    ("content", "code", "section"),
    [
        ("## 目标\n\n有效\n", "SPEC_SECTION_MISSING", "scope"),
        (
            complete_specification().replace("实现可测试的冻结服务。", ""),
            "SPEC_SECTION_EMPTY",
            "goal",
        ),
        (complete_specification() + "\nTBD\n", "SPEC_PLACEHOLDER_FORBIDDEN", None),
        (
            complete_specification().replace("`pytest` 通过。", "按需处理"),
            "SPEC_UNEXECUTABLE_LANGUAGE",
            None,
        ),
        (
            complete_specification().replace("- `pytest` 通过。", "- [ ]"),
            "SPEC_ACCEPTANCE_EMPTY_CHECKBOX",
            None,
        ),
    ],
)
def test_assessment_reports_stable_non_sensitive_issues(
    content: str, code: str, section: str | None
) -> None:
    result = assess_specification(content)
    assert result.valid is False
    assert (code, section) in {(issue.code, issue.section) for issue in result.issues}


def test_validation_raises_a_stable_error_without_specification_body() -> None:
    with pytest.raises(ContractError) as caught:
        validate_specification("## 目标\n\nTBD\n")

    assert caught.value.code == "SPECIFICATION_INVALID"
    assert "TBD" not in caught.value.message
