"""Deterministic task-specification validation and canonical summaries."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from aiflow.errors import ContractError

REQUIRED_SECTIONS: Mapping[str, str] = MappingProxyType(
    {
        "goal": "目标",
        "scope": "范围",
        "acceptance": "验收条件",
        "forbidden_actions": "禁止动作",
        "error_behavior": "错误行为",
        "rollback": "回滚",
    }
)
_HEADING_PATTERN = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_PLACEHOLDER_PATTERN = re.compile(r"\b(?:TODO|TBD)\b", re.IGNORECASE)
_UNEXECUTABLE_PATTERN = re.compile(r"按需处理")
_EMPTY_CHECKBOX_PATTERN = re.compile(r"^\s*[-*]\s*\[ \]\s*(?:$|\r?$)", re.MULTILINE)


@dataclass(frozen=True)
class SpecificationIssue:
    """A stable, non-sensitive diagnosis for an invalid specification."""

    code: str
    section: str | None = None


@dataclass(frozen=True)
class SpecificationAssessment:
    """The canonical form and completeness result for one specification."""

    valid: bool
    normalized: str
    sha256: str
    issues: tuple[SpecificationIssue, ...]
    summary: Mapping[str, str]


def normalize_specification(content: str) -> str:
    """Canonicalize line endings without changing meaningful specification text."""
    if not isinstance(content, str):
        raise TypeError("Specification content must be text")
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized if normalized.endswith("\n") else normalized + "\n"


def specification_digest(content: str) -> str:
    """Return the SHA-256 digest of canonical specification text."""
    return hashlib.sha256(normalize_specification(content).encode("utf-8")).hexdigest()


def _section_bodies(normalized: str) -> dict[str, str]:
    headings = list(_HEADING_PATTERN.finditer(normalized))
    result: dict[str, str] = {}
    for index, heading in enumerate(headings):
        title = heading.group(1).strip()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(normalized)
        result[title] = normalized[heading.end() : end].strip()
    return result


def _summary(bodies: Mapping[str, str]) -> Mapping[str, str]:
    """Return bounded section summaries, never raw arbitrary spec content."""
    return MappingProxyType(
        {
            key: "present" if bodies.get(title, "").strip() else "missing"
            for key, title in REQUIRED_SECTIONS.items()
        }
    )


def assess_specification(content: str) -> SpecificationAssessment:
    """Check required sections and reject incomplete or non-executable text."""
    normalized = normalize_specification(content)
    bodies = _section_bodies(normalized)
    issues: list[SpecificationIssue] = []

    for key, title in REQUIRED_SECTIONS.items():
        body = bodies.get(title)
        if body is None:
            issues.append(SpecificationIssue("SPEC_SECTION_MISSING", key))
        elif not body:
            issues.append(SpecificationIssue("SPEC_SECTION_EMPTY", key))

    if _PLACEHOLDER_PATTERN.search(normalized):
        issues.append(SpecificationIssue("SPEC_PLACEHOLDER_FORBIDDEN"))
    if _UNEXECUTABLE_PATTERN.search(normalized):
        issues.append(SpecificationIssue("SPEC_UNEXECUTABLE_LANGUAGE"))

    acceptance = bodies.get(REQUIRED_SECTIONS["acceptance"], "")
    if acceptance and _EMPTY_CHECKBOX_PATTERN.search(acceptance):
        meaningful_lines = [
            line.strip()
            for line in acceptance.splitlines()
            if line.strip() and not _EMPTY_CHECKBOX_PATTERN.fullmatch(line)
        ]
        if not meaningful_lines:
            issues.append(SpecificationIssue("SPEC_ACCEPTANCE_EMPTY_CHECKBOX"))

    ordered_issues = tuple(sorted(set(issues), key=lambda item: (item.code, item.section or "")))
    return SpecificationAssessment(
        valid=not ordered_issues,
        normalized=normalized,
        sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        issues=ordered_issues,
        summary=_summary(bodies),
    )


def validate_specification(content: str) -> SpecificationAssessment:
    """Return a valid assessment or a stable domain error without raw content."""
    assessment = assess_specification(content)
    if assessment.valid:
        return assessment
    raise ContractError(
        "Task specification is incomplete or not executable",
        code="SPECIFICATION_INVALID",
        details={
            "issues": [
                {"code": issue.code, "section": issue.section} for issue in assessment.issues
            ]
        },
    )
