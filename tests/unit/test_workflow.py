"""Shared workflow precondition tests."""

from __future__ import annotations

from aiflow.workflow import WorkflowFacts, evaluate_preconditions


def ready_facts(**changes: object) -> WorkflowFacts:
    values: dict[str, object] = {
        "current_state": "CLASSIFIED",
        "allowed_states": frozenset({"CLASSIFIED"}),
        "specification_frozen": True,
        "require_specification_frozen": True,
    }
    values.update(changes)
    return WorkflowFacts(**values)  # type: ignore[arg-type]


def test_complete_facts_pass_and_optional_approval_is_not_applicable() -> None:
    result = evaluate_preconditions(ready_facts())
    assert result.passed is True
    assert result.failure_codes == ()
    assert (
        next(item for item in result.results if item.name == "approvals_present").status
        == "not_applicable"
    )
    assert (
        next(item for item in result.results if item.name == "specification_complete").status
        == "pass"
    )
    assert (
        next(item for item in result.results if item.name == "specification_frozen").status
        == "pass"
    )
    assert (
        next(item for item in result.results if item.name == "specification_summary_matches").status
        == "pass"
    )


def test_required_approval_is_a_stable_failure() -> None:
    result = evaluate_preconditions(ready_facts(approvals_required=True))
    assert result.passed is False
    assert result.failure_codes == ("REQUIRED_APPROVAL_MISSING",)


def test_unfrozen_complete_specification_can_be_accepted_when_freeze_is_not_required() -> None:
    result = evaluate_preconditions(
        ready_facts(specification_frozen=False, require_specification_frozen=False)
    )
    assert result.passed is True
    assert (
        next(item for item in result.results if item.name == "specification_frozen").status
        == "not_applicable"
    )
    assert (
        next(item for item in result.results if item.name == "specification_summary_matches").status
        == "not_applicable"
    )


def test_tampered_frozen_specification_fails() -> None:
    result = evaluate_preconditions(ready_facts(specification_summary_matches=False))
    assert result.failure_codes == ("SPECIFICATION_TAMPERED",)


def test_required_verification_configuration_must_be_complete() -> None:
    result = evaluate_preconditions(
        ready_facts(
            require_verification_configuration=True,
            verification_configuration_complete=False,
        )
    )
    assert result.failure_codes == ("VERIFICATION_CONFIGURATION_INCOMPLETE",)


def test_unrequired_frozen_metadata_still_detects_tampering() -> None:
    result = evaluate_preconditions(
        ready_facts(
            specification_frozen=True,
            require_specification_frozen=False,
            specification_summary_matches=False,
        )
    )
    assert result.failure_codes == ("SPECIFICATION_TAMPERED",)
    assert (
        next(item for item in result.results if item.name == "specification_frozen").status
        == "not_applicable"
    )


def test_multiple_failures_are_safety_sorted_not_input_sorted() -> None:
    result = evaluate_preconditions(
        ready_facts(
            current_state="NEW",
            action_allowed=False,
            scope_unchanged=False,
            git_context_valid=False,
            classification_fresh=False,
        )
    )
    assert result.failure_codes == (
        "ACTION_PERMISSION_DENIED",
        "SCOPE_EXPANDED",
        "GIT_CONTEXT_INVALID",
        "CLASSIFICATION_STALE",
        "STATE_NOT_ALLOWED",
    )
