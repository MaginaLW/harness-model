"""Bounded YAML decoding cache that always returns independent results."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from typing import Any

import yaml

_MAX_ENTRIES = 64
_MAX_TEXT_CHARACTERS = 16384
_CACHE: OrderedDict[str, Any] = OrderedDict()
_LOCK = Lock()


def load_yaml_text(text: str) -> Any:
    """Decode YAML with ``yaml.safe_load``, reusing results for repeated small texts.

    Every call returns an independent deep copy, and parse errors are raised
    fresh and never cached. The cache is keyed by text alone, so changing
    PyYAML's loader configuration at runtime after a text was cached can return
    the earlier result; nothing in aiflow changes it.
    """
    if len(text) > _MAX_TEXT_CHARACTERS:
        return yaml.safe_load(text)
    with _LOCK:
        cached = text in _CACHE
        if cached:
            _CACHE.move_to_end(text)
            value = _CACHE[text]
    if not cached:
        value = yaml.safe_load(text)
        with _LOCK:
            _CACHE[text] = value
            _CACHE.move_to_end(text)
            while len(_CACHE) > _MAX_ENTRIES:
                _CACHE.popitem(last=False)
    return deepcopy(value)
