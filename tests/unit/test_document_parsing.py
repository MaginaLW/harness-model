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


@pytest.mark.parametrize("owner_name", ["SafeLoader", "SafeConstructor", "BaseConstructor"])
def test_warm_cache_preserves_changed_inherited_scalar_calls(
    owner_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import yaml.constructor

    text = "key: scalar"
    assert parsing.load_yaml_text(text) == {"key": "scalar"}
    owner = getattr(yaml, owner_name, None) or getattr(yaml.constructor, owner_name)
    original = owner.construct_scalar
    calls: list[str] = []

    def changed(loader: object, node: object) -> str:
        value = original(loader, node)
        calls.append(value)
        return value.upper()

    monkeypatch.setattr(owner, "construct_scalar", changed)
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text(text) == {"KEY": "SCALAR"}
    assert parsing.load_yaml_text(text) == {"KEY": "SCALAR"}
    assert calls == ["key", "scalar", "key", "scalar"]


def test_warm_cache_preserves_inplace_function_code_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "key: scalar"
    assert parsing.load_yaml_text(text) == {"key": "scalar"}
    function = yaml.SafeLoader.construct_yaml_str

    def changed(_loader: object, _node: object) -> str:
        return "changed"

    monkeypatch.setattr(function, "__code__", changed.__code__)
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text(text) == yaml.safe_load(text) == {"changed": "changed"}
    assert parsing.load_yaml_text(text) == {"changed": "changed"}


@pytest.mark.parametrize("attribute", ["__defaults__", "__kwdefaults__"])
def test_function_default_state_changes_bypass_retained_interpretation(
    attribute: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = "key: scalar"
    parsing.load_yaml_text(text)
    function = yaml.SafeLoader.construct_yaml_str
    changed = (None,) if attribute == "__defaults__" else {"unused": None}
    monkeypatch.setattr(function, attribute, changed)
    assert not parsing._parser_unchanged()
    first = parsing.load_yaml_text(text)
    second = parsing.load_yaml_text(text)
    assert first == second == yaml.safe_load(text)
    assert first is not second


def test_closure_change_preserves_current_parser_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml.constructor

    text = "key: scalar"
    parsing.load_yaml_text(text)
    function = yaml.constructor.SafeConstructor.construct_scalar
    assert function.__closure__ is not None
    monkeypatch.setattr(function.__closure__[0], "cell_contents", yaml.constructor.BaseConstructor)
    assert not parsing._parser_unchanged()
    with pytest.raises(AttributeError) as fresh:
        yaml.safe_load(text)
    for _ in range(2):
        with pytest.raises(AttributeError) as actual:
            parsing.load_yaml_text(text)
        assert str(actual.value) == str(fresh.value)


def test_deleted_inherited_method_preserves_new_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml.constructor

    text = "!!str {=: scalar}"
    assert parsing.load_yaml_text(text) == "scalar"
    monkeypatch.delattr(yaml.constructor.SafeConstructor, "construct_scalar")
    assert not parsing._parser_unchanged()
    with pytest.raises(yaml.YAMLError) as fresh:
        yaml.safe_load(text)
    for _ in range(2):
        with pytest.raises(type(fresh.value)) as actual:
            parsing.load_yaml_text(text)
        assert str(actual.value) == str(fresh.value)


def test_same_loader_changed_bases_preserves_replacement_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml.constructor

    text = "key: scalar"
    parsing.load_yaml_text(text)

    class Replacement(yaml.constructor.SafeConstructor):
        def construct_scalar(self, node: object) -> str:
            return super().construct_scalar(node).upper()

    bases = tuple(
        Replacement if base is yaml.constructor.SafeConstructor else base
        for base in yaml.SafeLoader.__bases__
    )
    original_bases = yaml.SafeLoader.__bases__
    try:
        yaml.SafeLoader.__bases__ = bases
        assert not parsing._parser_unchanged()
        assert parsing.load_yaml_text(text) == yaml.safe_load(text) == {"KEY": "SCALAR"}
    finally:
        yaml.SafeLoader.__bases__ = original_bases


def test_constructor_datetime_module_change_preserves_factory_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    import yaml.constructor

    text = "date: 2026-01-01"
    assert parsing.load_yaml_text(text) == {"date": date(2026, 1, 1)}
    calls: list[tuple[int, int, int]] = []

    def changed(year: int, month: int, day: int) -> date:
        calls.append((year, month, day))
        return date(year, month, day + len(calls))

    monkeypatch.setattr(yaml.constructor, "datetime", SimpleNamespace(date=changed))
    assert parsing.load_yaml_text(text) == {"date": date(2026, 1, 2)}
    assert parsing.load_yaml_text(text) == {"date": date(2026, 1, 3)}
    assert calls == [(2026, 1, 1), (2026, 1, 1)]


def test_datetime_date_member_change_preserves_current_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import datetime as module

    text = "date: 2026-01-01"
    parsing.load_yaml_text(text)
    monkeypatch.setattr(module, "date", lambda year, month, day: date(year, month, day + 1))
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text(text) == yaml.safe_load(text) == {"date": date(2026, 1, 2)}
    assert parsing.load_yaml_text(text) == {"date": date(2026, 1, 2)}


def test_mutated_scanner_escape_table_preserves_new_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml.scanner

    text = '"a\\nb"'
    assert parsing.load_yaml_text(text) == "a\nb"
    monkeypatch.setitem(yaml.scanner.Scanner.ESCAPE_REPLACEMENTS, "n", "changed")
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text(text) == yaml.safe_load(text) == "achangedb"


def test_mutated_nested_resolver_list_preserves_new_scalar_type() -> None:
    text = "key: 1"
    assert parsing.load_yaml_text(text) == {"key": 1}
    resolvers = yaml.SafeLoader.yaml_implicit_resolvers["1"]
    index = next(i for i, (tag, _pattern) in enumerate(resolvers) if tag.endswith(":int"))
    original = resolvers[index]
    resolvers[index] = ("tag:yaml.org,2002:str", original[1])
    try:
        assert not parsing._parser_unchanged()
        assert parsing.load_yaml_text(text) == yaml.safe_load(text) == {"key": "1"}
    finally:
        resolvers[index] = original


@pytest.mark.parametrize("owner", ["base64", "binascii"])
def test_binary_dependency_member_change_preserves_value_and_calls(
    owner: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import binascii

    text = "!!binary aGVsbG8="
    assert parsing.load_yaml_text(text) == b"hello"
    calls: list[object] = []

    def changed(value: object) -> bytes:
        calls.append(value)
        return b"changed"

    module = base64 if owner == "base64" else binascii
    name = "decodebytes" if owner == "base64" else "a2b_base64"
    monkeypatch.setattr(module, name, changed)
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text(text) == b"changed"
    assert parsing.load_yaml_text(text) == b"changed"
    assert len(calls) == 2


def test_binary_helper_inplace_code_change_preserves_new_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import base64

    text = "!!binary aGVsbG8="
    parsing.load_yaml_text(text)

    def changed(_value: object) -> None:
        raise ValueError("changed helper")

    monkeypatch.setattr(base64._input_type_check, "__code__", changed.__code__)  # type: ignore[attr-defined]
    assert not parsing._parser_unchanged()
    for _ in range(2):
        with pytest.raises(ValueError, match="changed helper"):
            parsing.load_yaml_text(text)


def test_heap_exception_class_configuration_is_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import binascii

    parsing.load_yaml_text("!!binary aGVsbG8=")
    monkeypatch.setattr(binascii.Error, "parser_config", [], raising=False)
    assert not parsing._parser_unchanged()
    assert parsing._capture_parser_guard() is not None
    assert parsing.load_yaml_text("!!binary aGVsbG8=") == b"hello"


def test_standard_configuration_keeps_real_cache_hit_and_isolated_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "key: [original]"
    assert parsing._parser_unchanged()
    parsing.load_yaml_text(text)
    assert text in parsing._CACHE

    def must_not_reclassify(*_args: object) -> bool:
        raise AssertionError("a standard cache hit must not parse and classify again")

    monkeypatch.setattr(parsing, "_cacheable", must_not_reclassify)
    first = parsing.load_yaml_text(text)
    first["key"].append("changed")
    assert parsing.load_yaml_text(text) == {"key": ["original"]}


def test_normal_hashable_lookup_and_unrelated_registration_keep_cache_eligible() -> None:
    import abc
    import collections.abc

    assert not issubclass(list, collections.abc.Hashable)
    assert issubclass(str, collections.abc.Hashable)

    class Unrelated(metaclass=abc.ABCMeta):
        pass

    class Registered:
        pass

    Unrelated.register(Registered)
    assert parsing._parser_unchanged()
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
    assert "key: scalar" in parsing._CACHE


def test_hashable_virtual_registration_bypasses_retained_results() -> None:
    import abc
    import collections.abc

    hashable = collections.abc.Hashable
    before = set(abc._get_dump(hashable)[0])  # type: ignore[attr-defined]
    assert not before
    parsing.load_yaml_text("key: scalar")

    class Registered:
        __hash__ = None  # type: ignore[assignment]

    try:
        hashable.register(Registered)
        assert not parsing._parser_unchanged()
        assert parsing._capture_parser_guard() is None
        assert parsing.load_yaml_text("key: scalar") == yaml.safe_load("key: scalar")
    finally:
        abc._reset_registry(hashable)  # type: ignore[attr-defined]
        abc._reset_caches(hashable)  # type: ignore[attr-defined]
    assert parsing._parser_unchanged()


@pytest.mark.parametrize("replacement", [print, int, staticmethod(print)])
def test_initial_native_method_override_cannot_hide_side_effects_in_cache(
    replacement: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(yaml.SafeLoader, "construct_scalar", replacement)
    assert parsing._capture_parser_guard() is None


def test_initial_builtin_constructor_uses_current_parser_on_every_call(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = "!!str scalar"
    constructors = dict(yaml.SafeLoader.yaml_constructors)
    constructors["tag:yaml.org,2002:str"] = print
    monkeypatch.setattr(yaml.SafeLoader, "yaml_constructors", constructors)
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text(text) is None
    assert parsing.load_yaml_text(text) is None
    assert len(capsys.readouterr().out.splitlines()) == 2
    assert text not in parsing._CACHE


def test_initial_obvious_python_method_override_is_ineligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = yaml.SafeLoader.construct_scalar
    monkeypatch.setattr(
        yaml.SafeLoader, "construct_scalar", lambda loader, node: original(loader, node).upper()
    )
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    assert (
        parsing.load_yaml_text("key: scalar") == yaml.safe_load("key: scalar") == {"KEY": "SCALAR"}
    )
    assert "key: scalar" not in parsing._CACHE


@pytest.mark.parametrize(
    "kind", ["opaque", "dict_subclass", "custom_type", "descriptor", "cycle", "depth", "state"]
)
def test_unknown_or_unbounded_initial_configuration_uses_fresh_parser(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    class UnknownDict(dict):
        pass

    class Unknown:
        def __get__(self, *_args: object) -> object:
            raise AssertionError("qualification must not execute an unknown descriptor")

    if kind == "opaque":
        value: object = object()
    elif kind == "dict_subclass":
        value = UnknownDict()
    elif kind == "custom_type":
        value = Unknown
    elif kind == "descriptor":
        value = Unknown()
    elif kind == "cycle":
        loop: list[object] = []
        loop.append(loop)
        value = loop
    elif kind == "depth":
        value = None
        for _ in range(parsing._MAX_DISPATCH_DEPTH + 1):
            value = [value]
    else:
        value = [None] * (parsing._MAX_DISPATCH_OBJECTS + 1)
    monkeypatch.setattr(yaml.SafeLoader, "qualification_config", value, raising=False)
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    first = parsing.load_yaml_text("key: [scalar]")
    second = parsing.load_yaml_text("key: [scalar]")
    assert first == second == yaml.safe_load("key: [scalar]")
    assert first is not second
    assert "key: [scalar]" not in parsing._CACHE


@pytest.mark.parametrize(
    "location", ["function_module", "module_name", "module_file", "module_spec", "class_module"]
)
def test_unknown_origin_metadata_does_not_execute_comparison_callbacks(
    location: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import yaml.constructor

    callbacks: list[str] = []

    class Unknown:
        def __eq__(self, _other: object) -> bool:
            callbacks.append("equality")
            return True

        def startswith(self, _other: object) -> bool:
            callbacks.append("startswith")
            return True

        @property
        def name(self) -> str:
            callbacks.append("property")
            return "yaml.constructor"

    unknown = Unknown()
    parsing.load_yaml_text("key: scalar")
    first_line = yaml.constructor.SafeConstructor.__dict__.get("__firstlineno__")
    try:
        with monkeypatch.context() as changes:
            if location == "function_module":
                changes.setattr(yaml.SafeLoader.construct_yaml_str, "__module__", unknown)
            elif location == "module_name":
                changes.setattr(yaml.constructor, "__name__", unknown)
            elif location == "module_file":
                changes.setattr(yaml.constructor, "__file__", unknown)
            elif location == "module_spec":
                changes.setattr(yaml.constructor, "__spec__", unknown)
            else:
                changes.setattr(yaml.constructor.SafeConstructor, "__module__", unknown)
            assert not parsing._parser_unchanged()
            assert parsing._capture_parser_guard() is None
            assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
            assert callbacks == []
    finally:
        # Python3.13 removes this field when assigning class.__module__.
        if first_line is not None:
            yaml.constructor.SafeConstructor.__firstlineno__ = first_line


def test_unknown_namespace_key_does_not_certify_eligibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml.constructor

    key = object()
    monkeypatch.setitem(yaml.constructor.__dict__, key, "unknown")
    assert parsing._capture_parser_guard() is None
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}


def test_changed_function_attribute_content_bypasses_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    function = yaml.SafeLoader.construct_yaml_str
    monkeypatch.setattr(function, "qualification_config", ["original"], raising=False)
    guard = parsing._capture_parser_guard()
    assert guard is not None
    monkeypatch.setattr(parsing, "_PARSER_GUARD", guard)
    parsing.load_yaml_text("key: scalar")
    function.qualification_config.append("changed")  # type: ignore[attr-defined]
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}


def test_dispatch_change_during_parse_cannot_publish_new_cache_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = parsing.deepcopy

    def copying(value: object) -> object:
        monkeypatch.setattr(yaml.SafeLoader, "qualification_config", object(), raising=False)
        return original(value)

    monkeypatch.setattr(parsing, "deepcopy", copying)
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
    assert "key: scalar" not in parsing._CACHE


def test_restored_standard_dispatch_can_reuse_original_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "key: scalar"
    parsing.load_yaml_text(text)
    with monkeypatch.context() as changes:
        changes.setattr(yaml.SafeLoader, "qualification_config", object(), raising=False)
        assert not parsing._parser_unchanged()
        assert parsing.load_yaml_text(text) == yaml.safe_load(text)
    assert parsing._parser_unchanged()
    assert parsing.load_yaml_text(text) == {"key": "scalar"}


@pytest.mark.parametrize("accessor", [print, len])
def test_initial_native_property_accessor_is_not_standard_dispatch(
    accessor: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(yaml.SafeLoader, "qualification_config", property(accessor), raising=False)
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
    assert "key: scalar" not in parsing._CACHE


def test_initial_native_dependency_alias_cannot_cache_side_effects(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import base64

    monkeypatch.setattr(base64, "decodebytes", print)
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text("!!binary aGVsbG8=") is None
    assert parsing.load_yaml_text("!!binary aGVsbG8=") is None
    assert len(capsys.readouterr().out.splitlines()) == 2
    assert "!!binary aGVsbG8=" not in parsing._CACHE


@pytest.mark.parametrize("kind", ["fanout", "depth"])
def test_nested_code_configuration_limits_preserve_fresh_parser(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    function = yaml.SafeLoader.construct_yaml_str
    original = function.__code__

    def empty() -> None:
        pass

    child = empty.__code__
    if kind == "fanout":
        extras = (child,) * (parsing._MAX_DISPATCH_OBJECTS + 1)
    else:
        for _ in range(parsing._MAX_DISPATCH_DEPTH + 1):
            child = child.replace(co_consts=(None, child))
        extras = (child,)
    monkeypatch.setattr(
        function, "__code__", original.replace(co_consts=original.co_consts + extras)
    )
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text("key: scalar") == yaml.safe_load("key: scalar")
    assert "key: scalar" not in parsing._CACHE


def test_unknown_metaclass_descriptor_is_not_executed_by_qualification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import abc

    callbacks: list[str] = []
    meta = abc.ABCMeta
    original_module = meta.__module__
    first_line = parsing._class_namespace(meta).get("__firstlineno__")

    def unknown_getter(_value: object) -> str:
        callbacks.append("getter")
        raise AssertionError("unknown metaclass getter must not qualify a cache hit")

    try:
        meta.__module__ = property(unknown_getter)  # type: ignore[assignment]
        assert not parsing._parser_unchanged()
        assert parsing._capture_parser_guard() is None
        assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
        assert callbacks == []
    finally:
        meta.__module__ = original_module
        if first_line is not None:
            meta.__firstlineno__ = first_line
    assert parsing._parser_unchanged()


def test_unknown_module_spec_name_uses_raw_known_fields_without_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml.constructor

    callbacks: list[str] = []

    class Unknown:
        def __eq__(self, _other: object) -> bool:
            callbacks.append("equality")
            return True

    monkeypatch.setattr(yaml.constructor.__spec__, "name", Unknown())
    assert parsing._capture_parser_guard() is None
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
    assert callbacks == []


@pytest.mark.parametrize("entry", ["safe_load", "load"])
def test_initial_builtin_entry_function_cannot_cache_print_side_effects(
    entry: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(yaml, entry, print)
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text("key: scalar") is None
    assert parsing.load_yaml_text("key: scalar") is None
    assert len(capsys.readouterr().out.splitlines()) == 2
    assert "key: scalar" not in parsing._CACHE


def test_custom_pattern_payload_never_certifies_cache_by_equality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import re

    import yaml.reader

    calls: list[str] = []

    class CustomPattern(str):
        def __ne__(self, _other: object) -> bool:
            calls.append("comparison")
            return False

    original = yaml.reader.Reader.NON_PRINTABLE
    custom = re.compile(CustomPattern(original.pattern), original.flags)
    monkeypatch.setattr(yaml.reader.Reader, "NON_PRINTABLE", custom)
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text("key: scalar") == yaml.safe_load("key: scalar")
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
    assert calls == []
    assert "key: scalar" not in parsing._CACHE


def test_initial_custom_hashable_metaclass_preserves_every_instancecheck(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import abc
    import collections.abc

    calls: list[object] = []

    class CustomMeta(abc.ABCMeta):
        def __instancecheck__(cls, value: object) -> bool:
            calls.append(value)
            return True

    class CustomHashable(metaclass=CustomMeta):
        pass

    monkeypatch.setattr(collections.abc, "Hashable", CustomHashable)
    monkeypatch.setattr(parsing, "_PARSER_GUARD", parsing._capture_parser_guard())
    assert not parsing._parser_unchanged()
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
    assert parsing.load_yaml_text("key: scalar") == {"key": "scalar"}
    assert calls == ["key", "key"]
    assert "key: scalar" not in parsing._CACHE
