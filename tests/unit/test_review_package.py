"""Review-package and pure approval preparation tests."""

from __future__ import annotations

import pytest

from aiflow.approval import (
    ApprovalContext,
    approval_is_current,
    prepare_approval,
    validate_action_file,
)
from aiflow.errors import ContractError, StateTransitionError
from aiflow.review import assess_review_package, validate_review_package

NOW = "2026-08-21T01:00:00Z"
LATER = "2026-08-22T01:00:00Z"
HASH = "a" * 64
COMMIT = "b" * 40


def package(recommendation: str = "APPROVE") -> str:
    return f"""# Review Package

## 审核目标

决定是否接受变更。

## 背景

最小任务背景。

## 代码地图

`src/aiflow/module.py`。

## 语义变更

增加一个确定性检查。

## 风险

输入无效时拒绝。

## 证据

- 已验证：`pytest` 通过。
- 未验证：生产环境行为。

## 审核问题

- 是否满足规格？

## 推荐结论

{recommendation}\n"""


def context(state: str = "WAITING_FOR_SPEC_REVIEW", **changes: object) -> ApprovalContext:
    values: dict[str, object] = {
        "task_id": "TASK-0001",
        "decision_unit_id": "DU-001",
        "task_state": state,
        "spec_sha256": HASH,
        "policy_sha256": HASH,
        "subject_commit": COMMIT,
    }
    values.update(changes)
    return ApprovalContext(**values)  # type: ignore[arg-type]


def action_file(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "action_type": "notify",
        "target": "issue-123",
        "parameter_summary": "one notification",
        "subject_commit": COMMIT,
        "conditions": ["review approved"],
        "expires_at": LATER,
        "single_use": True,
    }
    value.update(changes)
    return value


def test_complete_review_package_has_valid_recommendation() -> None:
    assessment = assess_review_package(package("APPROVE_WITH_CONDITIONS"))
    assert assessment.valid is True
    assert assessment.recommendation == "APPROVE_WITH_CONDITIONS"


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (package().replace("## 风险\n\n输入无效时拒绝。\n\n", ""), "REVIEW_SECTION_MISSING"),
        (package().replace("已验证", "已经检查"), "REVIEW_EVIDENCE_VERIFIED_MISSING"),
        (package().replace("未验证", "待检查"), "REVIEW_EVIDENCE_UNVERIFIED_MISSING"),
        (package("MAYBE"), "REVIEW_RECOMMENDATION_INVALID"),
    ],
)
def test_review_package_reports_stable_issues(content: str, code: str) -> None:
    assessment = assess_review_package(content)
    assert code in {issue.code for issue in assessment.issues}
    with pytest.raises(ContractError) as caught:
        validate_review_package(content)
    assert caught.value.code == "REVIEW_PACKAGE_INVALID"


def test_spec_approval_is_bound_to_current_versions() -> None:
    prepared = prepare_approval(
        approval_type="spec",
        context=context(),
        actor="reviewer",
        reason="meets direction",
        approved_at=NOW,
    )
    assert approval_is_current(prepared.record, context()) is True
    assert approval_is_current(prepared.record, context(spec_sha256="c" * 64)) is False


def test_code_approval_requires_review_evidence_and_clean_governance_context() -> None:
    with pytest.raises(ContractError) as caught:
        prepare_approval(
            approval_type="code",
            context=context("WAITING_FOR_FINAL_REVIEW"),
            actor="reviewer",
            reason="approved",
            approved_at=NOW,
            review_package=package(),
        )
    assert caught.value.code == "CODE_EVIDENCE_STALE"

    approved = prepare_approval(
        approval_type="code",
        context=context("WAITING_FOR_FINAL_REVIEW"),
        actor="reviewer",
        reason="approved",
        approved_at=NOW,
        review_package=package(),
        evidence_current=True,
        worktree_governance_only=True,
    )
    assert approved.record["approval_type"] == "code"


def test_approval_type_state_is_not_interchangeable() -> None:
    with pytest.raises(StateTransitionError) as caught:
        prepare_approval(
            approval_type="spec",
            context=context("READY_TO_IMPLEMENT"),
            actor="reviewer",
            reason="approved",
            approved_at=NOW,
        )
    assert caught.value.code == "APPROVAL_STATE_INVALID"


def test_action_file_is_exact_single_use_and_expiry_bound() -> None:
    action = validate_action_file(action_file(), subject_commit=COMMIT, now=NOW)
    assert action["parameter_summary"] == "one notification"
    with pytest.raises(ContractError) as caught:
        validate_action_file(action_file(single_use=False), subject_commit=COMMIT, now=NOW)
    assert caught.value.code == "ACTION_SINGLE_USE_REQUIRED"
    with pytest.raises(ContractError) as caught:
        validate_action_file(action_file(expires_at=NOW), subject_commit=COMMIT, now=NOW)
    assert caught.value.code == "ACTION_APPROVAL_EXPIRED"


def test_action_approval_does_not_execute_and_keeps_metadata_separate() -> None:
    prepared = prepare_approval(
        approval_type="action",
        context=context(),
        actor="reviewer",
        reason="one permitted notification",
        approved_at=NOW,
        action_file=action_file(),
    )
    assert prepared.record["approval_type"] == "action"
    assert prepared.action is not None
    assert prepared.action["target"] == "issue-123"
    action_sha256 = prepared.record["action_sha256"]
    assert isinstance(action_sha256, str)
    current_context = context(action_sha256=action_sha256)
    assert approval_is_current(prepared.record, current_context, now=NOW) is True
    assert approval_is_current(prepared.record, current_context, now=LATER) is False


def test_review_package_requires_an_explicit_question() -> None:
    content = package().replace("- 是否满足规格？", "请审核上述内容")
    assessment = assess_review_package(content)
    assert "REVIEW_QUESTION_MISSING" in {issue.code for issue in assessment.issues}
