"""Small deterministic redaction boundary for verification logs and summaries."""

from __future__ import annotations

import re
from collections.abc import Sequence

REDACTED = "[REDACTED]"
_DEFAULT_PATTERNS = (
    re.compile(r"(?i)\b(password|secret|token|api[_-]?key)\s*([=:])\s*[^\s,;]+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
)


def redact_text(
    text: str,
    *,
    sensitive_values: Sequence[str] = (),
    extra_patterns: Sequence[str] = (),
) -> str:
    """Redact known secret forms before text reaches any persistent log."""
    result = text
    for value in sorted({value for value in sensitive_values if value}, key=len, reverse=True):
        result = result.replace(value, REDACTED)
    for pattern in _DEFAULT_PATTERNS:
        if pattern.pattern.startswith("(?i)\\b(password"):
            result = pattern.sub(
                lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", result
            )
        else:
            result = pattern.sub(REDACTED, result)
    for raw_pattern in extra_patterns:
        try:
            result = re.sub(raw_pattern, REDACTED, result)
        except re.error:
            continue
    return result


def redact_command_summary(
    argv: Sequence[str],
    *,
    sensitive_values: Sequence[str] = (),
    extra_patterns: Sequence[str] = (),
) -> str:
    """Keep a command's program and benign argv while removing obvious sensitive values."""
    safe: list[str] = []
    for argument in argv:
        lower = argument.casefold()
        if any(value and value in argument for value in sensitive_values) or any(
            marker in lower for marker in ("token", "secret", "password", "api_key", "apikey")
        ):
            safe.append(REDACTED)
        else:
            safe.append(
                redact_text(
                    argument, sensitive_values=sensitive_values, extra_patterns=extra_patterns
                )
            )
    return " ".join(safe)
