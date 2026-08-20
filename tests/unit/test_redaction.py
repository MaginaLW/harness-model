"""Redaction boundaries for logs and command summaries."""

from aiflow.redaction import REDACTED, redact_command_summary, redact_text


def test_redacts_common_secret_forms_and_explicit_values() -> None:
    value = "TOKEN=top-secret Bearer abcdefghijklmnopqrstuvwxyz ghp_abcdefghijklmnopqrstuv"
    redacted = redact_text(value, sensitive_values=["top-secret"])
    assert "top-secret" not in redacted and "abcdefghijklmnopqrstuvwxyz" not in redacted
    assert REDACTED in redacted


def test_command_summary_redacts_secret_arguments() -> None:
    summary = redact_command_summary(
        ["python", "--token=top-secret", "safe"], sensitive_values=["top-secret"]
    )
    assert "top-secret" not in summary and summary.endswith("safe")


def test_command_summary_honors_extra_patterns() -> None:
    assert "customer-42" not in redact_command_summary(
        ["python", "customer-42"], extra_patterns=[r"customer-[0-9]+"]
    )
