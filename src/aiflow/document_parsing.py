"""Bounded pure YAML decoding; callers still read and validate current files."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from datetime import date, datetime
from itertools import chain
from threading import Lock
from typing import Any

import yaml
from yaml.loader import SafeLoader

_MAX_ENTRIES = 64
_MAX_TEXT_CHARACTERS = 16384
_MAX_GRAPH_VISITS = 4096
_MAX_GRAPH_DEPTH = 64
_SAFE_LOAD = yaml.safe_load
_LOAD = yaml.load
_LOADER = SafeLoader
_CONSTRUCTORS = dict(_LOADER.yaml_constructors)
_MULTI_CONSTRUCTORS = dict(_LOADER.yaml_multi_constructors)
_IMPLICIT_RESOLVERS = {
    key: tuple(values) for key, values in _LOADER.yaml_implicit_resolvers.items()
}
_PATH_RESOLVERS = dict(_LOADER.yaml_path_resolvers)
_STANDARD_PARSER = (
    getattr(_SAFE_LOAD, "__module__", None) == "yaml"
    and getattr(_LOAD, "__module__", None) == "yaml"
    and _LOADER.__module__ == "yaml.loader"
    and all(
        getattr(constructor, "__module__", None) == "yaml.constructor"
        for constructor in chain(_CONSTRUCTORS.values(), _MULTI_CONSTRUCTORS.values())
    )
)
_CACHE: OrderedDict[str, Any] = OrderedDict()
_LOCK = Lock()
_MISSING = object()


def _parser_unchanged() -> bool:
    try:
        return (
            _STANDARD_PARSER
            and yaml.safe_load is _SAFE_LOAD
            and yaml.load is _LOAD
            and yaml.SafeLoader is _LOADER
            and _LOADER.yaml_constructors == _CONSTRUCTORS
            and _LOADER.yaml_multi_constructors == _MULTI_CONSTRUCTORS
            and {key: tuple(values) for key, values in _LOADER.yaml_implicit_resolvers.items()}
            == _IMPLICIT_RESOLVERS
            and _LOADER.yaml_path_resolvers == _PATH_RESOLVERS
        )
    except Exception:
        # Unknown configuration comparisons must preserve the original parser.
        return False


def _cacheable(
    value: object, active: set[int], seen: set[int], remaining: list[int], depth: int = 0
) -> bool:
    remaining[0] -= 1
    if remaining[0] < 0 or depth > _MAX_GRAPH_DEPTH:
        return False
    if type(value) in (str, int, float, bool, type(None), bytes, date, datetime):
        return True
    if type(value) not in (dict, list, tuple, set):
        return False
    identity = id(value)
    if identity in active:
        return False
    if identity in seen:
        return True
    active.add(identity)
    assert isinstance(value, (dict, list, tuple, set))
    children = chain.from_iterable(value.items()) if isinstance(value, dict) else iter(value)
    accepted = all(_cacheable(child, active, seen, remaining, depth + 1) for child in children)
    active.remove(identity)
    seen.add(identity)
    return accepted


def load_yaml_text(text: str) -> Any:
    """Decode current text with isolated results and original parser errors.

    Large texts, changed parser configuration, custom values and cyclic graphs
    use the current parser directly. No path, validation or error is cached.
    """
    if len(text) > _MAX_TEXT_CHARACTERS or not _parser_unchanged():
        return yaml.safe_load(text)
    with _LOCK:
        retained = _CACHE.get(text, _MISSING)
        if retained is not _MISSING:
            _CACHE.move_to_end(text)
    if retained is not _MISSING:
        try:
            return deepcopy(retained)
        except Exception:
            # Copying must not introduce an exception absent from fresh parsing.
            with _LOCK:
                _CACHE.pop(text, None)
            return yaml.safe_load(text)
    value = yaml.safe_load(text)
    if not _cacheable(value, set(), set(), [_MAX_GRAPH_VISITS]):
        return value
    try:
        retained = deepcopy(value)
    except Exception:
        return value
    if _parser_unchanged():
        with _LOCK:
            _CACHE[text] = retained
            _CACHE.move_to_end(text)
            while len(_CACHE) > _MAX_ENTRIES:
                _CACHE.popitem(last=False)
    return value
