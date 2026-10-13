"""Read supplied observation declarations without authenticating or admitting them."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

_ID = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_SHA = r"[0-9a-f]{40}"
_UTC = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)"
_REFS = {
    "candidate",
    "declaration",
    "related_group",
    "conditions",
    "roles",
    "budget",
    "report",
    "closure",
}
_CANDIDATE_TIMES = ("declared_at", "entered_at", "report_fixed_at", "closed_at")
_SOURCE_CHECKS = (
    "VERIFY_ORIGINALS",
    "VERIFY_NATURAL_DOCS_SCOPE",
    "VERIFY_PRIOR_DECLARATION",
    "VERIFY_ROLES_AND_INPUTS",
    "VERIFY_TRUTH_AND_MATCH",
    "VERIFY_BUDGET_AND_CLOSURE",
    "VERIFY_GROUP_CONDITIONS",
)


def _object(value: object, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("invalid object fields")
    return cast(dict[str, Any], value)


def _pattern(value: object, pattern: str) -> str:
    if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
        raise ValueError("invalid string")
    return value


def _time(value: object) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(_pattern(value, _UTC).replace("Z", "+00:00"))


def _reference(value: object, repository: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError("invalid reference")
    if value.get("kind") == "git":
        ref = _object(value, {"kind", "source_commit", "path", "git_blob", "locator"})
        for field in ("source_commit", "git_blob"):
            _pattern(ref[field], _SHA)
        path = ref["path"]
        if (
            not isinstance(path, str)
            or "\\" in path
            or re.match(r"[A-Za-z]:", path)
            or any(part in ("", ".", "..") for part in path.split("/"))
            or any(unicodedata.category(char) == "Cc" for char in path)
        ):
            raise ValueError("invalid Git path")
    elif value.get("kind") == "pr":
        ref = _object(value, {"kind", "url", "locator"})
        _pattern(
            ref["url"],
            rf"https://github\.com/{re.escape(repository)}/pull/[1-9][0-9]*(?:#[A-Za-z0-9_-]+)?",
        )
    else:
        raise ValueError("invalid reference kind")
    if not isinstance(ref["locator"], str) or not ref["locator"].strip():
        raise ValueError("invalid locator")


def _validate(document: object) -> dict[str, Any]:
    data = _object(
        document, {"schema_version", "repository", "admission_package", "window", "candidates"}
    )
    if (
        data["schema_version"] != "1.0"
        or data["admission_package"] != "review-detection-admission-v0.1"
    ):
        raise ValueError("unsupported schema or admission package")
    repository = _pattern(data["repository"], r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
    if any(part in (".", "..") for part in repository.split("/")):
        raise ValueError("invalid repository")
    window = _object(data["window"], {"t0", "t1"})
    for value in window.values():
        _time(value)
    if not isinstance(data["candidates"], list):
        raise ValueError("invalid candidate list")
    candidate_ids: set[str] = set()
    for value in data["candidates"]:
        candidate = _object(
            value,
            {"candidate_id", "related_group", "candidate_commit", "refs", "opportunities"}
            | set(_CANDIDATE_TIMES),
        )
        candidate_id = _pattern(candidate["candidate_id"], _ID)
        if candidate_id in candidate_ids:
            raise ValueError("duplicate candidate ID")
        candidate_ids.add(candidate_id)
        for field, pattern in (("related_group", _ID), ("candidate_commit", _SHA)):
            if candidate[field] is not None:
                _pattern(candidate[field], pattern)
        for field in _CANDIDATE_TIMES:
            _time(candidate[field])
        refs = _object(candidate["refs"], _REFS)
        for ref in refs.values():
            _reference(ref, repository)
        if not isinstance(candidate["opportunities"], list):
            raise ValueError("invalid opportunity list")
        opportunity_ids: set[str] = set()
        for value in candidate["opportunities"]:
            opportunity = _object(
                value,
                {
                    "opportunity_id",
                    "contract_ref",
                    "object_ref",
                    "instance_ref",
                    "defect_class",
                    "truth",
                    "adjudication_ref",
                    "adjudication_fixed_at",
                    "match",
                    "matching_ref",
                    "matched_at",
                },
            )
            opportunity_id = _pattern(opportunity["opportunity_id"], _ID)
            if opportunity_id in opportunity_ids:
                raise ValueError("duplicate opportunity ID")
            opportunity_ids.add(opportunity_id)
            if (
                opportunity["defect_class"] != "direct_contradiction"
                or opportunity["truth"] not in ("positive", "negative", "disputed", "unknown")
                or opportunity["match"] not in ("detected", "not_detected", "unknown")
            ):
                raise ValueError("invalid opportunity classification")
            for field in (
                "contract_ref",
                "object_ref",
                "instance_ref",
                "adjudication_ref",
                "matching_ref",
            ):
                _reference(opportunity[field], repository)
            for field in ("adjudication_fixed_at", "matched_at"):
                _time(opportunity[field])
    return data


def _reference_key(ref: dict[str, str]) -> tuple[str, ...]:
    fields = (
        ("kind", "source_commit", "path", "git_blob", "locator")
        if ref["kind"] == "git"
        else ("kind", "url", "locator")
    )
    return tuple(ref[field] for field in fields)


def build_detection_input(document: object) -> dict[str, Any]:
    """Validate shape, preserve declarations and report mechanical gaps without I/O."""
    data = _validate(document)
    candidates: list[dict[str, Any]] = data["candidates"]
    t0, t1 = (_time(data["window"][field]) for field in ("t0", "t1"))
    checks: list[dict[str, str]] = []

    def check(code: str, locator: str, consistent: bool | None) -> None:
        checks.append(
            {
                "code": code,
                "status": "unknown"
                if consistent is None
                else "consistent_reported"
                if consistent
                else "conflict",
                "locator": locator,
            }
        )

    def binding(locator: str, commit: str | None, ref: dict[str, Any] | None) -> None:
        consistent = None
        if commit is not None and ref is not None and ref["kind"] == "git":
            consistent = commit == ref["source_commit"]
        check("CANDIDATE_BINDING", locator, consistent)

    def order(locator: str, left: object, right: object, *, strict: bool = False) -> None:
        before, after = _time(left), _time(right)
        consistent = None
        if before is not None and after is not None:
            consistent = before < after if strict else before <= after
        check("EVENT_ORDER", locator, consistent)

    valid_window = None if t0 is None or t1 is None else t1 - t0 == timedelta(days=30)
    check("WINDOW_DURATION", "$.window", valid_window)
    groups: dict[str | None, list[tuple[int, dict[str, Any]]]] = {}
    next_checks: list[dict[str, str]] = []
    for i, candidate in enumerate(candidates):
        location = f"$.candidates[{i}]"
        groups.setdefault(candidate["related_group"], []).append((i, candidate))
        next_checks.extend({"code": code, "locator": location} for code in _SOURCE_CHECKS)
        entry, closure = (_time(candidate[field]) for field in ("entered_at", "closed_at"))
        check(
            "ENTRY_WINDOW",
            f"{location}.entered_at",
            None if t0 is None or t1 is None or entry is None else t0 <= entry < t1,
        )
        check(
            "CLOSURE_WINDOW",
            f"{location}.closed_at",
            None if t1 is None or closure is None else closure < t1,
        )
        order(
            f"{location}.entered_at", candidate["declared_at"], candidate["entered_at"], strict=True
        )
        order(f"{location}.report_fixed_at", candidate["entered_at"], candidate["report_fixed_at"])
        binding(
            f"{location}.refs.candidate",
            candidate["candidate_commit"],
            candidate["refs"]["candidate"],
        )
        for field in sorted(_REFS):
            check(
                "REQUIRED_REFERENCE",
                f"{location}.refs.{field}",
                True if candidate["refs"][field] is not None else None,
            )
        for j, opportunity in enumerate(candidate["opportunities"]):
            opp_location = f"{location}.opportunities[{j}]"
            for field in ("contract_ref", "object_ref", "instance_ref"):
                check(
                    "REQUIRED_REFERENCE",
                    f"{opp_location}.{field}",
                    True if opportunity[field] is not None else None,
                )
            for field, required in (
                ("adjudication_ref", opportunity["truth"] in ("positive", "negative")),
                ("matching_ref", opportunity["match"] != "unknown"),
            ):
                if required or opportunity[field] is not None:
                    check(
                        "REQUIRED_REFERENCE",
                        f"{opp_location}.{field}",
                        True if opportunity[field] is not None else None,
                    )
            binding(
                f"{opp_location}.object_ref",
                candidate["candidate_commit"],
                opportunity["object_ref"],
            )
            check(
                "TRUTH_MATCH",
                f"{opp_location}.match",
                None if opportunity["match"] == "unknown" else opportunity["truth"] == "positive",
            )
            order(
                f"{opp_location}.adjudication_fixed_at",
                candidate["report_fixed_at"],
                opportunity["adjudication_fixed_at"],
            )
            order(
                f"{opp_location}.matched_at",
                opportunity["adjudication_fixed_at"],
                opportunity["matched_at"],
            )
            order(f"{location}.closed_at", opportunity["matched_at"], candidate["closed_at"])

    selections: list[dict[str, Any]] = []
    for group in sorted(groups, key=lambda value: (value is not None, value or "")):
        members = groups[group]
        selection: dict[str, Any] = {
            "related_group": group,
            "status": "unknown",
            "candidate_id": None,
            "opportunity_id": None,
        }
        selections.append(selection)
        group_location = f"$.candidates[{members[0][0]}].related_group"
        if (
            None in groups
            or valid_window is not True
            or any(member["entered_at"] is None for _, member in members)
        ):
            check("GROUP_SELECTION", group_location, None)
            continue
        inside = [
            (i, member)
            for i, member in members
            if cast(datetime, t0)
            <= cast(datetime, _time(member["entered_at"]))
            < cast(datetime, t1)
        ]
        if not inside:
            selection["status"] = "no_in_window_candidate"
            check("GROUP_SELECTION", group_location, True)
            continue
        if any(member["declared_at"] is None for _, member in inside):
            check("GROUP_SELECTION", group_location, None)
            continue
        declarations = [_time(member["declared_at"]) for _, member in inside]
        entries = [_time(member["entered_at"]) for _, member in inside]
        declared_order = sorted(
            inside, key=lambda item: cast(datetime, _time(item[1]["declared_at"]))
        )
        entered_order = sorted(
            inside, key=lambda item: cast(datetime, _time(item[1]["entered_at"]))
        )
        if (
            len(set(declarations)) != len(inside)
            or len(set(entries)) != len(inside)
            or [i for i, _ in declared_order] != [i for i, _ in entered_order]
            or any(
                cast(datetime, declared) >= cast(datetime, entered)
                for declared, entered in zip(declarations, entries, strict=True)
            )
        ):
            check("GROUP_SELECTION", group_location, False)
            continue
        check("GROUP_SELECTION", group_location, True)
        i, first = declared_order[0]
        opportunities = first["opportunities"]
        opp_location = f"$.candidates[{i}].opportunities"
        if not opportunities or any(
            opportunity[field] is None
            for opportunity in opportunities
            for field in ("contract_ref", "object_ref", "instance_ref")
        ):
            check("OPPORTUNITY_SELECTION", opp_location, None)
            continue
        keys = [
            (
                _reference_key(opportunity["contract_ref"]),
                _reference_key(opportunity["object_ref"]),
                opportunity["defect_class"],
            )
            for opportunity in opportunities
        ]
        instances = [_reference_key(opportunity["instance_ref"]) for opportunity in opportunities]
        if len(set(keys)) != len(keys) or len(set(instances)) != len(instances):
            check("OPPORTUNITY_SELECTION", opp_location, False)
            continue
        check("OPPORTUNITY_SELECTION", opp_location, True)
        chosen = opportunities[min(range(len(keys)), key=keys.__getitem__)]
        selection.update(
            status="selected_reported",
            candidate_id=first["candidate_id"],
            opportunity_id=chosen["opportunity_id"],
        )

    if not candidates:
        next_checks.append({"code": "LOCATE_NATURAL_CANDIDATE", "locator": "$.candidates"})
    return {
        "schema_version": "1.0",
        "measurement": "review_detection_input_readback",
        "repository": data["repository"],
        "admission_package": data["admission_package"],
        "window": deepcopy(data["window"]),
        "reported_candidates": deepcopy(candidates),
        "group_selections": selections,
        "condition_checks": checks,
        "next_source_checks": next_checks,
        "coverage": {
            "reported_candidates": len(candidates),
            "reported_groups": len(groups) - (None in groups),
            "reported_opportunities": sum(
                len(candidate["opportunities"]) for candidate in candidates
            ),
        },
        "source_assurance": "supplied_observation_declarations",
        "source_authenticity": "unknown",
        "history_completeness": "unknown",
        "observation_admission": "unknown",
        "statistical_independence": "unknown",
        "method_status": "design_pending",
        "probability_status": "unestimated",
        "model_score_update_status": "not_implemented",
        "actual_model_identity": "unknown",
        "execution_allowed": False,
        "permission_effect": "none",
        "ledger_effect": "none",
    }


def main(argv: list[str] | None = None) -> int:
    sys.dont_write_bytecode = True
    from benchmark_reference import _reject_constant, _unique_object

    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        original = sys.stdin.buffer.read()
        document = json.loads(
            original.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        report = build_detection_input(document)
        report["input_sha256"] = hashlib.sha256(original).hexdigest()
        report["executed_tool_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except (OSError, ValueError, RecursionError):
        print("review-detection-input: supplied declarations are invalid", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
