"""Offline, panel-relative benchmark references; never local success probabilities."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from statistics import median
from typing import cast
from urllib.parse import urlsplit


def _object(value: object, fields: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label}: expected exactly the documented fields")
    return cast(dict[str, object], value)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: expected a nonempty string")
    return value


def _list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{label}: expected a list")
    return value


def build_reference(document: object) -> dict[str, object]:
    """Validate supplied provenance and compute ordinal references without side effects.

    Validation establishes input shape, not authenticity, benchmark independence,
    protocol comparability, actual runtime identity, or transfer to code review.
    """
    data = _object(document, {"schema_version", "task_category", "models", "sources"}, "input")
    if data["schema_version"] != "1.0":
        raise ValueError("schema_version: expected 1.0")
    category = _text(data["task_category"], "task_category")
    models = [_text(value, "model_id") for value in _list(data["models"], "models")]
    if len(models) < 2 or len(set(models)) != len(models):
        raise ValueError("models: require at least two unique profiles")
    source_values = _list(data["sources"], "sources")
    if not source_values:
        raise ValueError("sources: require at least one source")
    source_ids: set[str] = set()
    families: set[str] = set()
    source_reports: list[dict[str, object]] = []
    components: dict[str, dict[str, float]] = {model: {} for model in models}
    matching = 0
    incomplete = False
    for value in source_values:
        source = _object(
            value,
            {
                "source_id",
                "family",
                "category",
                "url",
                "retrieved_at",
                "as_of",
                "revision",
                "metric",
                "direction",
                "protocol",
                "observations",
            },
            "source",
        )
        for field in ("source_id", "family", "category", "metric", "protocol"):
            _text(source[field], field)
        source_id = cast(str, source["source_id"])
        family = cast(str, source["family"])
        if source_id in source_ids or family in families:
            raise ValueError("sources: duplicate source_id or benchmark family")
        source_ids.add(source_id)
        families.add(family)
        url = urlsplit(_text(source["url"], "url"))
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username is not None
            or url.password is not None
        ):
            raise ValueError("url: require a public HTTPS URL without user credentials")
        retrieved_at = datetime.fromisoformat(_text(source["retrieved_at"], "retrieved_at"))
        if retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at: timezone required")
        if source["as_of"] is not None:
            as_of = _text(source["as_of"], "as_of")
            if date.fromisoformat(as_of).isoformat() != as_of:
                raise ValueError("as_of: expected YYYY-MM-DD or null")
        if source["revision"] is not None:
            _text(source["revision"], "revision")
        direction = source["direction"]
        if direction not in ("higher", "lower"):
            raise ValueError("direction: expected higher or lower")
        scores: dict[str, int | float | None] = {}
        for item in _list(source["observations"], "observations"):
            observation = _object(
                item, {"model_id", "label", "configuration", "score"}, "observation"
            )
            model_id = _text(observation["model_id"], "model_id")
            if model_id not in models or model_id in scores:
                raise ValueError("observations: require unique declared profile IDs")
            _text(observation["label"], "label")
            _text(observation["configuration"], "configuration")
            score = observation["score"]
            if score is None:
                scores[model_id] = None
            elif type(score) in (int, float):
                numeric_score = cast(int | float, score)
                if isinstance(numeric_score, float) and not math.isfinite(numeric_score):
                    raise ValueError("score: not finite")
                scores[model_id] = numeric_score
            else:
                raise ValueError("score: expected a finite number or null")
        references: dict[str, float] = {}
        if source["category"] != category:
            status = "out_of_scope"
        else:
            matching += 1
            if any(scores.get(model) is None for model in models):
                status = "incomplete_panel"
                incomplete = True
            else:
                status = "available"
                complete_scores = {model: cast(int | float, scores[model]) for model in models}
                for model, score in complete_scores.items():
                    better = sum(
                        other > score if direction == "higher" else other < score
                        for other in complete_scores.values()
                    )
                    tied = sum(other == score for other in complete_scores.values())
                    midrank = better + (tied + 1) / 2
                    percentile = 100 * (len(models) - midrank) / (len(models) - 1)
                    references[model] = round(percentile, 2)
                    components[model][source_id] = percentile
        source_reports.append(
            {**deepcopy(source), "status": status, "reference_scores": references}
        )
    reference_status = (
        "out_of_scope" if matching == 0 else "incomplete_panel" if incomplete else "available"
    )
    return {
        "schema_version": "1.0",
        "task_category": category,
        "score_kind": "external_rank_reference",
        "reference_method": "median_within_panel_midrank_percentile",
        "reference_status": reference_status,
        "probability_status": "unestimated",
        "execution_allowed": False,
        "permission_effect": "none",
        "ledger_effect": "none",
        "runtime_identity_status": "not_evaluated",
        "models": [
            {
                "model_id": model,
                "reference_score": (
                    round(median(components[model].values()), 2)
                    if reference_status == "available"
                    else None
                ),
                "components": {key: round(value, 2) for key, value in components[model].items()},
            }
            for model in models
        ],
        "sources": source_reports,
        "limitations": [
            "BENCHMARK_TO_REVIEW_TRANSFER_UNVALIDATED",
            "PANEL_DEPENDENT_ORDINAL_SCORE",
            "SUPPLIED_SOURCE_AND_PROFILE_IDENTITIES_UNVERIFIED",
        ],
    }


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON: duplicate object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"JSON: invalid numeric constant {value}")


def main(argv: list[str] | None = None) -> int:
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Curated public reference JSON")
    arguments = parser.parse_args(argv)
    try:
        original = arguments.input.read_bytes()
        document = json.loads(
            original.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        report = build_reference(document)
        report["input_sha256"] = hashlib.sha256(original).hexdigest()
    except (OSError, ValueError, RecursionError):
        print("Invalid reference input.", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
