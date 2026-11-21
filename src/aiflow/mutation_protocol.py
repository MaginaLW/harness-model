"""Closed, bounded detector reports and fail-closed outcome derivation.

Reports are structured execution facts, not authentication of test code.
"""

from __future__ import annotations

import json
import re
from typing import Any

MAX_REPORT_BYTES = 16 * 1024
EARLY_STOP_EXIT_CODE = 3
PYTHON_VERSION = "3.11"
PYTEST_VERSION = "9.1.1"
REVIEWED_INPUT_SHA256 = {
    ".ai/mutations/phase-02-critical-manifest.json": (
        "1dac9624e5a221784d56dc189e5bb225662334b550238b13ecf7587c96d277c0"
    ),
    "tests/unit/test_policy.py": "25721c57de7a8a4e0bbdddf15fb147a8f9cf46304f1c191c08b3ef5aac627962",
    "tests/integration/test_verify_command.py": (
        "5991bead1b4d67a83890da1ec16a0b1bac7aff005a49978a09d28324760fa9ed"
    ),
    "tests/integration/test_mutation_manifest_contract.py": (
        "353656eb2dc585c76751a5eebd7ee5654723949ecff1b621f9b9a217e2f516d9"
    ),
    "tests/unit/test_evidence.py": (
        "d27687837225257ac2ae89c89f5eae267f40d31a046d32d0099283b8a54005a8"
    ),
}
STATES = frozenset({"passed", "failed", "skipped", "xfailed", "xpassed"})
EXCEPTIONS = frozenset({"policy_error", "assertion_error", "pytest_failed", "unknown"})
ANCHORS = frozenset(
    {
        "policy_valid",
        "actor_unexpected",
        "approval_assert",
        "gate_assert",
        "snapshot_raises",
        "unknown",
    }
)
SEMANTICS = frozenset(
    {
        "policy_check_reference_invalid",
        "actor_sentinel",
        "missing_contract_error",
        "none",
        "unknown",
    }
)
CASES = {
    "MUT-V2-001": ("only",),
    "MUT-V2-002": ("blank", "same_actor"),
    "MUT-V2-003": ("only",),
    "MUT-V2-004": ("only",),
    "MUT-V2-005": ("only",),
}
SIGNATURES = {
    "MUT-V2-001": ("only", "policy_error", "policy_valid", "policy_check_reference_invalid"),
    "MUT-V2-002": ("same_actor", "assertion_error", "actor_unexpected", "actor_sentinel"),
    "MUT-V2-003": ("only", "assertion_error", "approval_assert", "none"),
    "MUT-V2-004": ("only", "assertion_error", "gate_assert", "none"),
    "MUT-V2-005": ("only", "pytest_failed", "snapshot_raises", "missing_contract_error"),
}
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate report key")
        result[key] = value
    return result


def encode_report(report: object) -> bytes:
    """Encode the sole accepted deterministic wire representation."""
    try:
        data = json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
            "ascii"
        )
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError("invalid report") from error
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("report is too large")
    return data


def parse_report(data: bytes, mutation_id: str, target_sha256: str) -> dict[str, Any]:
    """Parse a canonical, complete report without accepting arbitrary fields."""
    if (
        not isinstance(data, bytes)
        or len(data) > MAX_REPORT_BYTES
        or not isinstance(mutation_id, str)
        or mutation_id not in CASES
        or not isinstance(target_sha256, str)
        or _DIGEST.fullmatch(target_sha256) is None
    ):
        raise ValueError("invalid report input")
    try:
        value = json.loads(data.decode("ascii"), object_pairs_hook=_unique)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("invalid report JSON") from error
    if encode_report(value) != data:
        raise ValueError("noncanonical report")
    if not isinstance(value, dict) or set(value) != {
        "protocol",
        "mutation_id",
        "python",
        "pytest",
        "platform",
        "cases",
        "imports",
        "complete",
    }:
        raise ValueError("invalid report fields")
    if (
        value["protocol"] != "1.0"
        or value["mutation_id"] != mutation_id
        or value["python"] != PYTHON_VERSION
        or value["pytest"] != PYTEST_VERSION
        or value["platform"] != "windows"
        or value["complete"] is not True
    ):
        raise ValueError("invalid report identity")
    imports = value["imports"]
    if (
        not isinstance(imports, dict)
        or set(imports) != {"target_sha256", "reference_ok"}
        or imports["target_sha256"] != target_sha256
        or type(imports["reference_ok"]) is not bool
    ):
        raise ValueError("invalid report import facts")
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != len(CASES[mutation_id]):
        raise ValueError("invalid report case count")
    for case, expected in zip(cases, CASES[mutation_id], strict=True):
        if not isinstance(case, dict) or set(case) != {
            "case",
            "setup",
            "call",
            "teardown",
            "failure",
        }:
            raise ValueError("invalid report case")
        if case["case"] != expected or any(
            not isinstance(case[phase], str) or case[phase] not in STATES
            for phase in ("setup", "call", "teardown")
        ):
            raise ValueError("invalid report phase")
        failure = case["failure"]
        if case["call"] == "failed":
            if (
                not isinstance(failure, dict)
                or set(failure) != {"exception", "anchor", "semantic"}
                or not isinstance(failure["exception"], str)
                or failure["exception"] not in EXCEPTIONS
                or not isinstance(failure["anchor"], str)
                or failure["anchor"] not in ANCHORS
                or not isinstance(failure["semantic"], str)
                or failure["semantic"] not in SEMANTICS
            ):
                raise ValueError("invalid report failure")
        elif failure is not None:
            raise ValueError("unexpected report failure")
    return value


def classify_report(
    report: dict[str, Any], *, mutation_id: str, target_sha256: str, exit_code: int, baseline: bool
) -> str:
    """Revalidate structured facts and derive only a supported result."""
    if type(exit_code) is not int or type(baseline) is not bool:
        return "unverified"
    try:
        value = parse_report(encode_report(report), mutation_id, target_sha256)
    except (ValueError, TypeError, RecursionError):
        return "unverified"
    if value["imports"]["reference_ok"] is not True:
        return "unverified"
    cases = value["cases"]
    if all(
        all(case[phase] == "passed" for phase in ("setup", "call", "teardown")) for case in cases
    ):
        if exit_code != 0:
            return "unverified"
        return "passed" if baseline else "survived"
    if baseline or exit_code != 1:
        return "unverified"
    expected_case, exception, anchor, semantic = SIGNATURES[mutation_id]
    for case in cases:
        if case["setup"] != "passed" or case["teardown"] != "passed":
            return "unverified"
        if case["case"] == expected_case:
            if case["call"] != "failed" or case["failure"] != {
                "exception": exception,
                "anchor": anchor,
                "semantic": semantic,
            }:
                return "unverified"
        elif case["call"] != "passed":
            return "unverified"
    return "killed"
