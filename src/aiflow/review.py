"""Deterministic validation of standalone REVIEW packages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from aiflow.errors import ContractError

REQUIRED_REVIEW_SECTIONS: Mapping[str, str] = MappingProxyType(
    {
        "objective": "审核目标",
        "background": "背景",
        "code_map": "代码地图",
        "semantic_change": "语义变更",
        "risks": "风险",
        "evidence": "证据",
        "questions": "审核问题",
        "recommendation": "推荐结论",
    }
)
RECOMMENDATIONS = frozenset(
    {"APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_CHANGES", "REJECT", "BLOCKED"}
)
_HEADING_PATTERN = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_RECOMMENDATION_PATTERN = re.compile(
    r"\b(?:APPROVE_WITH_CONDITIONS|REQUEST_CHANGES|APPROVE|REJECT|BLOCKED)\b"
)
_QUESTION_PATTERN = re.compile(r"(?:^\s*[-*]\s+\S.+$|[?？])", re.MULTILINE)


@dataclass(frozen=True)
class ReviewIssue:
    """A stable, non-sensitive review-package diagnosis."""

    code: str
    section: str | None = None


@dataclass(frozen=True)
class ReviewAssessment:
    """Completeness result for a standalone review package."""

    valid: bool
    issues: tuple[ReviewIssue, ...]
    recommendation: str | None
    summary: Mapping[str, str]


def _section_bodies(content: str) -> dict[str, str]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    headings = list(_HEADING_PATTERN.finditer(normalized))
    bodies: dict[str, str] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(normalized)
        bodies[heading.group(1).strip()] = normalized[heading.end() : end].strip()
    return bodies


def assess_review_package(content: str) -> ReviewAssessment:
    """Validate all required sections and REVIEW-specific evidence semantics."""
    if not isinstance(content, str):
        raise TypeError("Review package content must be text")
    bodies = _section_bodies(content)
    issues: list[ReviewIssue] = []
    for key, title in REQUIRED_REVIEW_SECTIONS.items():
        body = bodies.get(title)
        if body is None:
            issues.append(ReviewIssue("REVIEW_SECTION_MISSING", key))
        elif not body:
            issues.append(ReviewIssue("REVIEW_SECTION_EMPTY", key))

    evidence = bodies.get(REQUIRED_REVIEW_SECTIONS["evidence"], "")
    if evidence and "已验证" not in evidence:
        issues.append(ReviewIssue("REVIEW_EVIDENCE_VERIFIED_MISSING", "evidence"))
    if evidence and "未验证" not in evidence:
        issues.append(ReviewIssue("REVIEW_EVIDENCE_UNVERIFIED_MISSING", "evidence"))

    questions = bodies.get(REQUIRED_REVIEW_SECTIONS["questions"], "")
    if questions and _QUESTION_PATTERN.search(questions) is None:
        issues.append(ReviewIssue("REVIEW_QUESTION_MISSING", "questions"))

    recommendation_body = bodies.get(REQUIRED_REVIEW_SECTIONS["recommendation"], "")
    recommendations = set(_RECOMMENDATION_PATTERN.findall(recommendation_body))
    recommendation = next(iter(recommendations)) if len(recommendations) == 1 else None
    if recommendation not in RECOMMENDATIONS:
        issues.append(ReviewIssue("REVIEW_RECOMMENDATION_INVALID", "recommendation"))

    ordered = tuple(sorted(set(issues), key=lambda issue: (issue.code, issue.section or "")))
    return ReviewAssessment(
        valid=not ordered,
        issues=ordered,
        recommendation=recommendation,
        summary=MappingProxyType(
            {
                key: "present" if bodies.get(title, "").strip() else "missing"
                for key, title in REQUIRED_REVIEW_SECTIONS.items()
            }
        ),
    )


def validate_review_package(content: str) -> ReviewAssessment:
    """Return a valid package assessment or a stable error without raw package text."""
    assessment = assess_review_package(content)
    if assessment.valid:
        return assessment
    raise ContractError(
        "Review package is incomplete or invalid",
        code="REVIEW_PACKAGE_INVALID",
        details={
            "issues": [
                {"code": issue.code, "section": issue.section} for issue in assessment.issues
            ]
        },
    )
