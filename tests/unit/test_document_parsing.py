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
    assert text not in parsing._CACHE


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


@pytest.mark.parametrize(
    "text", ["[" * 66 + "0" + "]" * 66, "x: &a []\ny: [" + ",".join(["*a"] * 4100) + "]"]
)
def test_graph_limits_use_original_parsing_without_rejecting_valid_yaml(text: str) -> None:
    first = parsing.load_yaml_text(text)
    second = parsing.load_yaml_text(text)
    assert first == second == yaml.safe_load(text)
    assert first is not second
    assert text not in parsing._CACHE


def test_changed_safe_load_and_custom_values_use_current_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "x: 1"
    parsing.load_yaml_text(text)

    class Custom:
        def __deepcopy__(self, _memo: object) -> object:
            raise AssertionError("custom results must not be copied")

    custom = Custom()
    calls = []

    def changed(supplied: str) -> Custom:
        calls.append(supplied)
        return custom

    monkeypatch.setattr(yaml, "safe_load", changed)
    assert parsing.load_yaml_text(text) is custom
    assert parsing.load_yaml_text(text) is custom
    assert calls == [text, text]


def test_changed_load_function_and_loader_class_bypass_retained_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "x: 1"
    parsing.load_yaml_text(text)
    with monkeypatch.context() as changes:
        changes.setattr(yaml, "load", lambda *_args, **_kwargs: {"changed": True})
        assert parsing.load_yaml_text(text) == {"changed": True}
    with monkeypatch.context() as changes:

        class Replacement(yaml.SafeLoader):
            def get_single_data(self) -> object:
                return {"replacement": True}

        changes.setattr(yaml, "SafeLoader", Replacement)
        assert parsing.load_yaml_text(text) == {"replacement": True}
    assert parsing.load_yaml_text(text) == {"x": 1}


def test_changed_constructor_preserves_side_effects_even_for_builtin_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "x: 1"
    parsing.load_yaml_text(text)
    calls = []

    def construct(_loader: object, _node: object) -> int:
        calls.append(True)
        return len(calls)

    constructors = dict(yaml.SafeLoader.yaml_constructors)
    constructors["tag:yaml.org,2002:int"] = construct
    monkeypatch.setattr(yaml.SafeLoader, "yaml_constructors", constructors)
    assert parsing.load_yaml_text(text) == {"x": 1}
    assert parsing.load_yaml_text(text) == {"x": 2}
    assert calls == [True, True]


@pytest.mark.parametrize(
    "attribute", ["yaml_multi_constructors", "yaml_implicit_resolvers", "yaml_path_resolvers"]
)
def test_changed_registration_tables_bypass_cached_results(
    attribute: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = "x: 1"
    parsing.load_yaml_text(text)
    table = dict(getattr(yaml.SafeLoader, attribute))
    if attribute == "yaml_multi_constructors":
        table["!custom:"] = lambda *_args: None
    elif attribute == "yaml_implicit_resolvers":
        table["unused"] = []
    else:
        table[(((dict, "unused"),), None)] = "tag:yaml.org,2002:str"
    monkeypatch.setattr(yaml.SafeLoader, attribute, table)
    assert not parsing._parser_unchanged()
    first = parsing.load_yaml_text(text)
    second = parsing.load_yaml_text(text)
    assert first == second == yaml.safe_load(text)
    assert first is not second


@pytest.mark.parametrize("warm", [False, True])
def test_copy_failure_preserves_fresh_parser_result(
    warm: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = "x: [original]"
    if warm:
        parsing.load_yaml_text(text)

    def cannot_copy(_value: object) -> object:
        raise TypeError("copy unavailable")

    monkeypatch.setattr(parsing, "deepcopy", cannot_copy)
    value = parsing.load_yaml_text(text)
    value["x"].append("changed")
    assert parsing.load_yaml_text(text) == {"x": ["original"]}
    assert text not in parsing._CACHE


def test_custom_and_subclass_values_are_not_cacheable() -> None:
    class Custom(dict):
        pass

    for value in (object(), Custom(a=1)):
        assert not parsing._cacheable(value, set(), set(), [4096])


def test_configuration_comparison_failure_preserves_current_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "x: 1"
    parsing.load_yaml_text(text)

    class Constructor:
        def __eq__(self, _other: object) -> bool:
            raise RuntimeError("comparison unavailable")

        def __call__(self, _loader: object, _node: object) -> int:
            return 42

    constructors = dict(yaml.SafeLoader.yaml_constructors)
    constructors["tag:yaml.org,2002:int"] = Constructor()
    monkeypatch.setattr(yaml.SafeLoader, "yaml_constructors", constructors)
    assert parsing.load_yaml_text(text) == yaml.safe_load(text) == {"x": 42}


def test_parallel_callers_receive_independent_graphs() -> None:
    text = "x: [original]"
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(parsing.load_yaml_text, [text] * 24))
    for index, value in enumerate(values):
        value["x"].append(index)
    assert [value["x"] for value in values] == [["original", index] for index in range(24)]
    assert parsing.load_yaml_text(text) == {"x": ["original"]}
