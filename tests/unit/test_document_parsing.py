"""Content reuse must preserve parser behavior and independent returned graphs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Iterator

import pytest
import yaml

from aiflow import document_parsing as parsing


@pytest.fixture(autouse=True)
def empty_cache() -> Iterator[None]:
    with parsing._LOCK:
        parsing._CACHE.clear()
    yield
    with parsing._LOCK:
        parsing._CACHE.clear()


def test_mutable_results_and_aliases_are_independent_between_calls() -> None:
    text = "first: &value {items: [original]}\nsecond: *value\n"
    first = parsing.load_yaml_text(text)
    second = parsing.load_yaml_text(text)
    assert first["first"] is first["second"]
    assert second["first"] is second["second"]
    assert first["first"] is not second["first"]
    first["first"]["items"].append("changed")
    second["second"]["items"].clear()
    assert parsing.load_yaml_text(text)["first"]["items"] == ["original"]


def test_first_result_is_independent_of_the_cached_value() -> None:
    text = "key: [original]"
    parsing.load_yaml_text(text)["key"].append("changed")
    assert text in parsing._CACHE
    assert parsing.load_yaml_text(text) == {"key": ["original"]}


@pytest.mark.parametrize(
    "text", ["null", "false", "42", "3.5", "!!binary aGVsbG8=", "!!set {a: null}"]
)
def test_standard_scalars_and_sets_match_fresh_parsing(text: str) -> None:
    expected = yaml.safe_load(text)
    assert parsing.load_yaml_text(text) == expected
    assert parsing.load_yaml_text(text) == expected


def test_date_and_timestamp_types_are_preserved() -> None:
    text = "date: 2026-09-30\ntime: 2026-09-30T10:00:00Z\n"
    for _ in range(2):
        value = parsing.load_yaml_text(text)
        assert type(value["date"]) is date
        assert type(value["time"]) is datetime
        assert value == yaml.safe_load(text)


def test_cycles_retain_their_original_topology_without_shared_results() -> None:
    text = "&loop [*loop]"
    first = parsing.load_yaml_text(text)
    second = parsing.load_yaml_text(text)
    assert first[0] is first
    assert second[0] is second
    assert first is not second


@pytest.mark.parametrize(
    "text", ["[" * 66 + "0" + "]" * 66, "x: &a []\ny: [" + ",".join(["*a"] * 4100) + "]"]
)
def test_deep_and_wide_graphs_match_fresh_parsing(text: str) -> None:
    first = parsing.load_yaml_text(text)
    second = parsing.load_yaml_text(text)
    assert first == second == yaml.safe_load(text)
    assert first is not second


def test_repeated_parse_errors_are_not_cached() -> None:
    text = "items: ["
    errors = []
    for _ in range(2):
        with pytest.raises(yaml.YAMLError) as caught:
            parsing.load_yaml_text(text)
        errors.append(str(caught.value))
    assert errors[0] == errors[1]
    assert text not in parsing._CACHE


def test_size_boundary_and_lru_eviction_are_bounded() -> None:
    limit = parsing._MAX_TEXT_CHARACTERS
    fitting = "x" * limit
    oversized = fitting + "x"
    assert parsing.load_yaml_text(fitting) == fitting
    assert fitting in parsing._CACHE
    assert parsing.load_yaml_text(oversized) == oversized
    assert oversized not in parsing._CACHE
    parsing._CACHE.clear()
    for index in range(parsing._MAX_ENTRIES):
        parsing.load_yaml_text(f"value: {index}")
    parsing.load_yaml_text("value: 0")
    parsing.load_yaml_text("value: 64")
    assert len(parsing._CACHE) == parsing._MAX_ENTRIES
    assert "value: 0" in parsing._CACHE
    assert "value: 1" not in parsing._CACHE


def test_cache_hit_does_not_parse_again(monkeypatch: pytest.MonkeyPatch) -> None:
    text = "key: [original]"
    parsing.load_yaml_text(text)

    def must_not_parse(_text: str) -> object:
        raise AssertionError("a cache hit must not parse again")

    monkeypatch.setattr(yaml, "safe_load", must_not_parse)
    assert parsing.load_yaml_text(text) == {"key": ["original"]}


def test_parallel_callers_receive_independent_graphs() -> None:
    text = "x: [original]"
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(parsing.load_yaml_text, [text] * 24))
    for index, value in enumerate(values):
        value["x"].append(index)
    assert [value["x"] for value in values] == [["original", index] for index in range(24)]
    assert parsing.load_yaml_text(text) == {"x": ["original"]}
