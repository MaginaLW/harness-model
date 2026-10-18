"""Independent checks for replayable public benchmark reference scores."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "tools" / "analysis" / "benchmark_reference.py"


@pytest.fixture(scope="module")
def reference() -> Any:
    spec = importlib.util.spec_from_file_location("benchmark_reference", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source(
    source_id: str = "repair", scores: tuple[object, ...] = (9, 6, 6, 1), **changes: object
) -> dict[str, object]:
    source: dict[str, object] = {
        "source_id": source_id,
        "family": source_id,
        "category": "coding",
        "url": "https://example.org/leaderboard",
        "retrieved_at": "2026-10-12T01:00:00+08:00",
        "as_of": "2026-10-08",
        "revision": "synthetic-fixture-v1",
        "metric": "test_pass_percent",
        "direction": "higher",
        "protocol": "Synthetic single-attempt fixed harness; no real model claim.",
        "observations": [
            {
                "model_id": model_id,
                "label": f"Synthetic {model_id}",
                "configuration": "fixture harness; model version fixed by fixture only",
                "score": score,
            }
            for model_id, score in zip(("a", "b", "c", "d"), scores, strict=True)
        ],
    }
    source.update(changes)
    return source


def _document(*sources: dict[str, object]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_category": "coding",
        "models": ["a", "b", "c", "d"],
        "sources": list(sources) if sources else [_source()],
    }


def _scores(report: dict[str, Any]) -> dict[str, object]:
    return {model["model_id"]: model["reference_score"] for model in report["models"]}


def test_ties_use_midrank_and_preserve_the_original_scores(reference: Any) -> None:
    document = _document()
    original = copy.deepcopy(document)

    report = reference.build_reference(document)

    assert report["reference_status"] == "available"
    assert _scores(report) == {"a": 100.0, "b": 50.0, "c": 50.0, "d": 0.0}
    assert report["sources"][0]["reference_scores"] == _scores(report)
    assert report["sources"][0]["observations"] == original["sources"][0]["observations"]
    assert document == original

    report["sources"][0]["observations"][0]["score"] = -999
    assert document == original, "Output mutation must not alter the supplied source records."


def test_lower_is_better_and_median_uses_unrounded_ranks(reference: Any) -> None:
    report = reference.build_reference(
        _document(_source(), _source("latency", (4, 1, 2, 3), direction="lower"))
    )

    assert report["sources"][1]["reference_scores"] == {
        "a": 0.0,
        "b": 100.0,
        "c": 66.67,
        "d": 33.33,
    }
    assert _scores(report) == {"a": 50.0, "b": 75.0, "c": 58.33, "d": 16.67}
    assert report["models"][2]["components"] == {"repair": 50.0, "latency": 66.67}


def test_median_is_not_a_mean_and_raw_units_do_not_set_source_weight(reference: Any) -> None:
    report = reference.build_reference(
        _document(
            _source("one", (3, 2, 1, 0)),
            _source("two", (30_000, 20_000, 10_000, 0)),
            _source("three", (0.01, 0.02, 0.03, 0.04)),
        )
    )

    assert _scores(report) == {"a": 100.0, "b": 66.67, "c": 33.33, "d": 0.0}


@pytest.mark.parametrize("direction", ["higher", "lower"])
def test_an_entirely_tied_panel_has_no_preferred_candidate(reference: Any, direction: str) -> None:
    report = reference.build_reference(_document(_source(scores=(7, 7, 7, 7), direction=direction)))
    assert _scores(report) == dict.fromkeys(("a", "b", "c", "d"), 50.0)


def test_two_candidate_panel_and_zero_or_negative_raw_scores(reference: Any) -> None:
    document = _document(_source(scores=(-5, 0, 1, 2)))
    document["models"] = ["a", "b"]
    document["sources"][0]["observations"] = document["sources"][0]["observations"][:2]

    assert _scores(reference.build_reference(document)) == {"a": 0.0, "b": 100.0}


@pytest.mark.parametrize("baseline", [2**53, 2**2048])
def test_distinct_integer_scores_are_not_turned_into_a_float_precision_tie(
    reference: Any, baseline: int
) -> None:
    document = _document(_source(scores=(baseline, baseline + 1, 0, 1)))

    report = reference.build_reference(document)

    assert _scores(report) == {"a": 66.67, "b": 100.0, "c": 0.0, "d": 33.33}


def test_source_order_and_observation_order_do_not_change_scores(reference: Any) -> None:
    document = _document(_source(), _source("other", (1, 2, 3, 4)))
    expected = _scores(reference.build_reference(document))
    document["sources"].reverse()
    for source in document["sources"]:
        source["observations"].reverse()
    document["models"].reverse()

    report = reference.build_reference(document)

    assert _scores(report) == expected
    assert [item["model_id"] for item in report["models"]] == ["d", "c", "b", "a"]


def test_out_of_scope_source_cannot_change_a_coding_reference(reference: Any) -> None:
    unrelated = _source("chat", (0, 10, 20, 30), category="chat")
    report = reference.build_reference(_document(_source(), unrelated))

    assert report["reference_status"] == "available"
    assert _scores(report) == {"a": 100.0, "b": 50.0, "c": 50.0, "d": 0.0}
    assert report["sources"][1]["status"] == "out_of_scope"
    assert report["sources"][1]["reference_scores"] == {}
    assert report["models"][0]["components"] == {"repair": 100.0}


def test_only_out_of_scope_sources_leave_the_reference_unestimated(reference: Any) -> None:
    report = reference.build_reference(_document(_source(category="chat")))

    assert report["reference_status"] == "out_of_scope"
    assert _scores(report) == dict.fromkeys(("a", "b", "c", "d"))
    assert all(model["components"] == {} for model in report["models"])


@pytest.mark.parametrize("missing_kind", ["missing_row", "null_score", "empty_panel"])
def test_incomplete_relevant_source_withholds_the_whole_aggregate(
    reference: Any, missing_kind: str
) -> None:
    document = _document(_source(), _source("missing", (4, 3, 2, 1)))
    observations = document["sources"][1]["observations"]
    if missing_kind == "missing_row":
        observations.pop()
    elif missing_kind == "null_score":
        observations[-1]["score"] = None
    else:
        observations.clear()

    report = reference.build_reference(document)

    assert report["reference_status"] == "incomplete_panel"
    assert _scores(report) == dict.fromkeys(("a", "b", "c", "d"))
    assert report["sources"][1]["status"] == "incomplete_panel"
    assert report["sources"][1]["reference_scores"] == {}
    assert report["models"][0]["components"] == {"repair": 100.0}
    assert report["sources"][1]["observations"] == observations


def test_missing_observations_outside_the_task_category_do_not_block_the_panel(
    reference: Any,
) -> None:
    report = reference.build_reference(
        _document(_source(), _source("chat", observations=[], category="chat"))
    )

    assert report["reference_status"] == "available"
    assert report["sources"][1]["status"] == "out_of_scope"
    assert report["models"][0]["reference_score"] == 100.0


def test_a_different_model_configuration_cannot_be_aliased_into_a_missing_row(
    reference: Any,
) -> None:
    document = _document()
    document["models"][-1] = "d-high"
    document["sources"][0]["observations"].pop()

    report = reference.build_reference(document)

    assert report["reference_status"] == "incomplete_panel"
    assert report["models"][-1]["model_id"] == "d-high"
    assert report["models"][-1]["reference_score"] is None


def test_even_a_perfect_reference_does_not_estimate_probability_or_grant_permission(
    reference: Any,
) -> None:
    report = reference.build_reference(_document(_source(scores=(100, 0, 0, 0))))

    assert report["models"][0]["reference_score"] == 100.0
    assert report["probability_status"] == "unestimated"
    assert report["execution_allowed"] is False
    assert report["permission_effect"] == "none"
    assert report["ledger_effect"] == "none"
    assert report["runtime_identity_status"] == "not_evaluated"
    assert report["score_kind"] == "external_rank_reference"
    assert report["reference_method"] == "median_within_panel_midrank_percentile"
    assert "BENCHMARK_TO_REVIEW_TRANSFER_UNVALIDATED" in report["limitations"]


@pytest.mark.parametrize("document", [None, [], "1.0", 1, True])
def test_non_object_documents_are_rejected(reference: Any, document: object) -> None:
    with pytest.raises(ValueError):
        reference.build_reference(document)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2.0"),
        ("schema_version", 1.0),
        ("task_category", ""),
        ("task_category", " "),
        ("task_category", None),
        ("models", []),
        ("models", ["a"]),
        ("models", ["a", "a"]),
        ("models", ["a", ""]),
        ("models", ["a", " "]),
        ("models", ["a", False]),
        ("models", "ab"),
        ("sources", []),
        ("sources", {}),
        ("sources", [None]),
    ],
)
def test_invalid_panel_or_top_level_metadata_is_rejected(
    reference: Any, field: str, value: object
) -> None:
    document = _document()
    document[field] = value
    with pytest.raises(ValueError):
        reference.build_reference(document)


@pytest.mark.parametrize("location", ["document", "source", "observation"])
@pytest.mark.parametrize("change", ["extra", "missing"])
def test_unrecognized_and_missing_fields_cannot_be_silently_ignored(
    reference: Any, location: str, change: str
) -> None:
    document = _document()
    targets = {
        "document": (document, "schema_version"),
        "source": (document["sources"][0], "protocol"),
        "observation": (document["sources"][0]["observations"][0], "configuration"),
    }
    target, required = targets[location]
    if change == "extra":
        target["confidence_probability"] = 0.99
    else:
        del target[required]
    with pytest.raises(ValueError):
        reference.build_reference(document)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", ""),
        ("family", " "),
        ("category", 1),
        ("metric", ""),
        ("protocol", None),
        ("direction", "descending"),
        ("direction", False),
        ("url", "http://example.org/leaderboard"),
        ("url", "https://user:password@example.org/leaderboard"),
        ("url", "https://user@example.org/leaderboard"),
        ("url", "https://"),
        ("retrieved_at", "2026-10-12T01:00:00"),
        ("retrieved_at", "2026-10-12"),
        ("retrieved_at", "2026-02-30T01:00:00+08:00"),
        ("retrieved_at", False),
        ("as_of", "2026-02-30"),
        ("as_of", "20261012"),
        ("as_of", "2026-10-12T01:00:00Z"),
        ("revision", ""),
        ("revision", 123),
        ("observations", {}),
        ("observations", [None]),
    ],
)
def test_invalid_source_metadata_is_rejected(reference: Any, field: str, value: object) -> None:
    document = _document()
    document["sources"][0][field] = value
    with pytest.raises(ValueError):
        reference.build_reference(document)


def test_unknown_publication_date_and_revision_remain_unknown(reference: Any) -> None:
    report = reference.build_reference(
        _document(_source(as_of=None, revision=None, retrieved_at="2026-10-11T17:00:00Z"))
    )
    assert report["sources"][0]["as_of"] is None
    assert report["sources"][0]["revision"] is None
    assert report["sources"][0]["retrieved_at"] == "2026-10-11T17:00:00Z"


@pytest.mark.parametrize("duplicate_field", ["source_id", "family"])
def test_mirrors_or_duplicate_sources_do_not_gain_extra_weight(
    reference: Any, duplicate_field: str
) -> None:
    document = _document(_source(), _source("mirror", (0, 1, 2, 3)))
    document["sources"][1][duplicate_field] = document["sources"][0][duplicate_field]
    with pytest.raises(ValueError):
        reference.build_reference(document)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_id", "not-in-panel"),
        ("model_id", ""),
        ("label", ""),
        ("label", None),
        ("configuration", " "),
        ("score", True),
        ("score", "99"),
        ("score", float("nan")),
        ("score", float("inf")),
        ("score", float("-inf")),
        ("score", []),
    ],
)
def test_invalid_observation_or_unbound_profile_is_rejected(
    reference: Any, field: str, value: object
) -> None:
    document = _document()
    document["sources"][0]["observations"][0][field] = value
    with pytest.raises(ValueError):
        reference.build_reference(document)


def test_duplicate_observation_cannot_replace_another_profile(reference: Any) -> None:
    document = _document()
    document["sources"][0]["observations"][1]["model_id"] = "a"
    with pytest.raises(ValueError):
        reference.build_reference(document)


def test_malformed_out_of_scope_sources_are_still_rejected(reference: Any) -> None:
    document = _document(_source(category="chat", direction="unknown"))
    with pytest.raises(ValueError):
        reference.build_reference(document)


def test_cli_replays_exact_input_bytes_and_does_not_write_or_execute(
    reference: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = (json.dumps(_document(), indent=2) + "\r\n").encode("utf-8")
    input_path = tmp_path / "input.json"
    input_path.write_bytes(payload)
    before = sorted(path.name for path in tmp_path.iterdir())

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Reference calculation attempted a network, process, or file write.")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)

    code = reference.main(["--input", str(input_path)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["input_sha256"] == hashlib.sha256(payload).hexdigest()
    assert _scores(report) == {"a": 100.0, "b": 50.0, "c": 50.0, "d": 0.0}
    assert sorted(path.name for path in tmp_path.iterdir()) == before
    assert input_path.read_bytes() == payload


@pytest.mark.parametrize(
    "payload",
    [
        b'{"schema_version":"1.0","schema_version":"2.0"}',
        b'{"outer":{"score":1,"score":2}}',
        b'{"score":NaN}',
        b'{"score":Infinity}',
        b'{"score":-Infinity}',
        b'{"bad":',
        b"[]",
        b"\xff\xfe",
    ],
)
def test_cli_rejects_ambiguous_or_invalid_input_without_partial_output(
    reference: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str], payload: bytes
) -> None:
    input_path = tmp_path / "invalid.json"
    input_path.write_bytes(payload)

    code = reference.main(["--input", str(input_path)])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert captured.err == "Invalid reference input.\n"
    assert input_path.read_bytes() == payload


@pytest.mark.parametrize("duplicate", ["top_level", "observation"])
def test_cli_rejects_duplicate_keys_even_when_last_value_is_a_valid_document(
    reference: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    duplicate: str,
) -> None:
    payload = json.dumps(_document())
    if duplicate == "top_level":
        payload = payload.replace(
            '"schema_version": "1.0"',
            '"schema_version": "2.0", "schema_version": "1.0"',
            1,
        )
    else:
        payload = payload.replace('"score": 9', '"score": 999, "score": 9', 1)
    assert reference.build_reference(json.loads(payload))["reference_status"] == "available"
    input_path = tmp_path / "duplicate.json"
    input_path.write_text(payload, encoding="utf-8")

    code = reference.main(["--input", str(input_path)])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert captured.err == "Invalid reference input.\n"


@pytest.mark.parametrize("file_kind", ["missing", "directory"])
def test_cli_io_errors_are_reported_without_a_traceback(
    reference: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str], file_kind: str
) -> None:
    input_path = tmp_path if file_kind == "directory" else tmp_path / "absent.json"

    code = reference.main(["--input", str(input_path)])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert captured.err == "Invalid reference input.\n"


@pytest.mark.parametrize("stream_encoding", ["ascii", "gbk", "utf-8"])
@pytest.mark.parametrize("failure", ["missing", "directory", "retrieved_at", "as_of"])
def test_cli_errors_do_not_echo_paths_or_input_values(
    tmp_path: Path, stream_encoding: str, failure: str
) -> None:
    marker = "SYNTHETIC_PRIVATE_中文_🙂"
    input_path = tmp_path / f"{marker}.json"
    original: bytes | None = None
    if failure == "directory":
        input_path.mkdir()
    elif failure != "missing":
        document = _document(_source(**{failure: marker}))
        original = json.dumps(document, ensure_ascii=False).encode("utf-8")
        input_path.write_bytes(original)
    before = sorted(path.name for path in tmp_path.iterdir())
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = stream_encoding

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(input_path)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.splitlines() == [b"Invalid reference input."]
    assert sorted(path.name for path in tmp_path.iterdir()) == before
    if original is not None:
        assert input_path.read_bytes() == original
    if failure == "directory":
        assert list(input_path.iterdir()) == []


def test_standalone_script_works_without_the_repository_python_package(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(_document()), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--input", str(input_path)],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["reference_status"] == "available"
    assert report["permission_effect"] == "none"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["input.json"]


@pytest.mark.parametrize("stdout_encoding", ["ascii", "gbk"])
@pytest.mark.parametrize("text", ["Synthetic 中文 🙂", "Escaped lone surrogate \ud800"])
def test_cli_preserves_unicode_fields_with_a_restricted_stdout_encoding(
    tmp_path: Path, stdout_encoding: str, text: str
) -> None:
    document = _document()
    observation = document["sources"][0]["observations"][0]
    observation["label"] = text
    observation["configuration"] = f"Exact profile configuration: {text}"
    escaped_surrogate = "\ud800" in text
    original = json.dumps(document, ensure_ascii=escaped_surrogate).encode("utf-8")
    input_path = tmp_path / "unicode-input.json"
    input_path.write_bytes(original)
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = stdout_encoding

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(input_path)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
        encoding="ascii",
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.isascii()
    report = json.loads(result.stdout)
    assert report["sources"][0]["observations"][0] == observation
    assert report["input_sha256"] == hashlib.sha256(original).hexdigest()
    assert input_path.read_bytes() == original


@pytest.mark.parametrize("filename", ["swebench.json", "aider.json", "arena-webdev.json"])
def test_documented_examples_are_replayable_and_preserve_source_configuration(
    reference: Any, capsys: pytest.CaptureFixture[str], filename: str
) -> None:
    input_path = (
        PROJECT_ROOT / "docs" / "operations" / "examples" / "benchmark-reference" / filename
    )
    original = input_path.read_bytes()
    document = json.loads(original)

    code = reference.main(["--input", str(input_path)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["reference_status"] == "available"
    assert all(model["reference_score"] is not None for model in report["models"])
    assert [model["model_id"] for model in report["models"]] == document["models"]
    for source, emitted in zip(document["sources"], report["sources"], strict=True):
        assert {key: emitted[key] for key in source} == source
    assert report["input_sha256"] == hashlib.sha256(original).hexdigest()
    assert input_path.read_bytes() == original
