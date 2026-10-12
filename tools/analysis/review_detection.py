"""Calculate a bounded synthetic review-detection interval without admitting real data."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from math import comb, fsum
from pathlib import Path
from typing import Any

VERIFIED_N_MAX = 104
TAIL = 0.025
TARGET_WIDTH = 0.20


def _root(k: int, n: int, target: float) -> float:
    coefficients = tuple(comb(n, j) for j in range(k + 1))
    low, high = 0.0, 1.0
    for _ in range(56):
        p = (low + high) / 2
        q = 1 - p
        cumulative = fsum(coefficients[j] * p**j * q ** (n - j) for j in range(k + 1))
        if cumulative > target:
            low = p
        else:
            high = p
    return (low + high) / 2


def build_detection(document: object) -> dict[str, Any]:
    """Return conditional mathematics for supplied synthetic counts, without I/O."""
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "record_origin",
        "n",
        "k",
    }:
        raise ValueError("invalid object fields")
    if document["schema_version"] != "1.0" or document["record_origin"] != "synthetic":
        raise ValueError("unsupported schema version or record origin")
    n, k = document["n"], document["k"]
    if type(n) is not int or type(k) is not int:
        raise ValueError("counts must be integers")
    if not 0 <= n <= VERIFIED_N_MAX or not 0 <= k <= n:
        raise ValueError("counts outside the verified domain")

    result: dict[str, Any] = {
        "n": n,
        "k": k,
        "proportion": None,
        "lower": None,
        "upper": None,
        "width": None,
        "precision_met": None,
    }
    if n > 0:
        lower = 0.0 if k == 0 else _root(k - 1, n, 1 - TAIL)
        upper = 1.0 if k == n else _root(k, n, TAIL)
        width = upper - lower
        result.update(
            proportion=k / n,
            lower=lower,
            upper=upper,
            width=width,
            precision_met=width <= TARGET_WIDTH,
        )
    return {
        "schema_version": "1.0",
        "measurement": "synthetic_review_detection",
        "record_origin": "synthetic",
        "source_assurance": "synthetic_supplied_counts",
        "method": "clopper_pearson_equal_tailed",
        "coverage": 0.95,
        "target_width": TARGET_WIDTH,
        "verified_n_max": VERIFIED_N_MAX,
        "calculation_status": "calculated" if n > 0 else "no_positive_units",
        "conditional_result": result,
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
        report = build_detection(document)
        report["input_sha256"] = hashlib.sha256(original).hexdigest()
        report["executed_tool_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except (OSError, ValueError, RecursionError):
        print("review-detection: supplied synthetic counts are invalid", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
