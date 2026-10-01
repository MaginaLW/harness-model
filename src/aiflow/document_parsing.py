"""Bounded YAML decoding qualified against recognized standard parser dispatch."""

from __future__ import annotations

import abc
import base64
import binascii
import codecs
import collections
import collections.abc
import datetime as datetime_module
import dis
import re
import sys
from collections import OrderedDict
from copy import deepcopy
from datetime import date, datetime
from importlib.machinery import ModuleSpec
from itertools import chain
from threading import Lock
from types import (
    BuiltinFunctionType,
    CodeType,
    FunctionType,
    GetSetDescriptorType,
    MemberDescriptorType,
    MethodDescriptorType,
    ModuleType,
    WrapperDescriptorType,
)
from typing import Any

import yaml
from yaml.loader import SafeLoader

_MAX_ENTRIES = 64
_MAX_TEXT_CHARACTERS = 16384
_MAX_GRAPH_VISITS = 4096
_MAX_GRAPH_DEPTH = 64
_MAX_DISPATCH_OBJECTS = 4096
_MAX_DISPATCH_DEPTH = 64
_MISSING = object()
_PATTERN_TYPE = re.Pattern
_ABC_IMPLEMENTATION = sys.modules["_collections_abc"]
_STANDARD_FUNCTION_MODULES = frozenset(("base64", "abc", "collections.abc"))
_STANDARD_NATIVE_FUNCTIONS = (
    frozenset(
        (
            ("builtins", name)
            for name in (
                "chr",
                "getattr",
                "hasattr",
                "isinstance",
                "len",
                "max",
                "next",
                "ord",
                "print",
                "repr",
            )
        )
    )
    | frozenset(
        (
            ("_abc", name)
            for name in (
                "_abc_init",
                "_abc_instancecheck",
                "_abc_register",
                "_abc_subclasscheck",
                "_get_dump",
                "_reset_caches",
                "_reset_registry",
                "get_cache_token",
            )
        )
    )
    | frozenset(
        (("_codecs", name) for name in ("utf_16_be_decode", "utf_16_le_decode", "utf_8_decode"))
    )
    | frozenset((("binascii", "a2b_base64"),))
)
_DEPENDENCY_MEMBERS = (
    (
        codecs,
        ("BOM_UTF16_LE", "BOM_UTF16_BE", "utf_16_le_decode", "utf_16_be_decode", "utf_8_decode"),
    ),
    (datetime_module, ("date", "datetime", "timedelta", "timezone")),
    (base64, ("decodebytes", "decodestring", "_input_type_check")),
    (binascii, ("Error", "a2b_base64")),
    (sys.modules["types"], ("GeneratorType",)),
    (collections, ("abc",)),
    (collections.abc, ("Hashable",)),
    (abc, ("_get_dump",)),
)


def _type_field(value: type[Any], name: str) -> Any:
    # Call the immutable type descriptor directly, bypassing a mutable
    # metaclass's __getattribute__ and data descriptors alike.
    return type.__dict__[name].__get__(value)


def _class_namespace(value: type[Any]) -> Any:
    return _type_field(value, "__dict__")


_SPEC_DICTIONARY = _class_namespace(ModuleSpec).get("__dict__")


class _DispatchGuard:
    """A finite observed standard dispatch plan, not arbitrary Python purity."""

    def __init__(self) -> None:
        self._seen: set[int] = set()
        self._active_containers: set[int] = set()
        self._pending: list[tuple[Any, int]] = []
        self._classes: list[tuple[Any, ...]] = []
        self._functions: list[tuple[Any, ...]] = []
        self._native_functions: list[tuple[Any, str, str]] = []
        self._containers: list[tuple[Any, ...]] = []
        self._modules: list[tuple[ModuleType, dict[str, Any]]] = []
        self._namespaces: dict[int, tuple[dict[str, Any], tuple[tuple[str, Any], ...]]] = {}
        self._global_names: dict[int, tuple[dict[str, Any], set[str]]] = {}
        self._bindings: list[tuple[dict[str, Any], str, Any]] = []
        self._patterns: list[tuple[Any, str | bytes, int]] = []
        self._specifications: list[ModuleSpec] = []
        self._state_items = 0
        self._code_items = 0
        self._code_names: dict[int, set[str]] = {}
        self._hashable = collections.abc.Hashable
        self._abc_meta = abc.ABCMeta
        meta_origin = _type_field(self._abc_meta, "__module__")
        meta_name = _type_field(self._abc_meta, "__qualname__")
        hashable_origin = _type_field(self._hashable, "__module__")
        hashable_name = _type_field(self._hashable, "__qualname__")
        if (
            type(self._abc_meta) is not type
            or type(self._hashable) is not self._abc_meta
            or type(meta_origin) is not str
            or type(meta_name) is not str
            or type(hashable_origin) is not str
            or type(hashable_name) is not str
            or (meta_origin, meta_name) != ("abc", "ABCMeta")
            or (hashable_origin, hashable_name) != ("collections.abc", "Hashable")
        ):
            raise ValueError("custom parser ABC dispatch")
        self._registry_reader = abc._get_dump  # type: ignore[attr-defined]
        self._constructor_tables()
        if yaml.SafeLoader is not SafeLoader:
            raise ValueError("custom parser entry loader")
        self._visit(SafeLoader)
        for name in ("safe_load", "load"):
            function = yaml.__dict__.get(name)
            if type(function) is not FunctionType or self._function_names(function) != (
                "yaml",
                name,
                name,
            ):
                raise ValueError("custom parser entry callable")
            self._visit(function)
        self._visit(self._hashable)
        self._visit(self._abc_meta)
        for module, member_names in _DEPENDENCY_MEMBERS:
            namespace = ModuleType.__getattribute__(module, "__dict__")
            for name in member_names:
                value = namespace.get(name, _MISSING)
                self._bindings.append((namespace, name, value))
                if value is not _MISSING:
                    self._native_binding(name, value)
                    self._visit(value)
        while self._pending:
            self._examine(*self._pending.pop())
        for namespace, names in self._global_names.values():
            for name in sorted(names):
                self._bindings.append((namespace, name, namespace.get(name, _MISSING)))
        self._reserve(len(self._bindings))
        if not self._empty_registry():
            raise ValueError("custom Hashable virtual registration")
        self._utc = datetime_module.timezone.utc

    def _constructor_tables(self) -> None:
        mro = _type_field(SafeLoader, "__mro__")
        for name in ("yaml_constructors", "yaml_multi_constructors"):
            table = next(
                (_class_namespace(cls)[name] for cls in mro if name in _class_namespace(cls)),
                _MISSING,
            )
            if type(table) is not dict:
                raise ValueError("custom parser constructor table")
            self._reserve(len(table))
            for tag, function in table.items():
                if type(tag) not in (str, type(None)) or type(function) is not FunctionType:
                    raise ValueError("custom parser constructor registration")
                if self._function_names(function)[0] != "yaml.constructor":
                    raise ValueError("custom parser constructor origin")

    @staticmethod
    def _native_binding(name: str, value: Any) -> None:
        if type(value) is BuiltinFunctionType:
            if type(value.__name__) is not str or value.__name__ != name:
                raise ValueError("custom native parser binding")

    def _empty_registry(self) -> bool:
        state = self._registry_reader(self._hashable)
        return type(state) is tuple and len(state) == 4 and type(state[0]) is set and not state[0]

    @staticmethod
    def _function_names(value: FunctionType) -> tuple[str, str, str]:
        names = (value.__module__, value.__name__, value.__qualname__)
        if any(type(name) is not str for name in names):
            raise ValueError("unknown parser callable metadata")
        return names

    def _reserve(self, count: int) -> None:
        self._state_items += count
        if self._state_items > _MAX_DISPATCH_OBJECTS:
            raise ValueError("parser qualification state limit")

    def _namespace(self, namespace: dict[str, Any]) -> None:
        if id(namespace) not in self._namespaces:
            self._reserve(len(namespace))
            if any(type(key) is not str for key in namespace):
                raise ValueError("unsupported parser namespace key")
            self._namespaces[id(namespace)] = (namespace, tuple(namespace.items()))

    def _visit(self, value: Any, depth: int = 0) -> None:
        if depth > _MAX_DISPATCH_DEPTH:
            raise ValueError("parser qualification depth limit")
        identity = id(value)
        if identity in self._active_containers:
            raise ValueError("cyclic parser configuration")
        if identity in self._seen:
            return
        self._seen.add(identity)
        if len(self._seen) > _MAX_DISPATCH_OBJECTS:
            raise ValueError("parser qualification object limit")
        kind = type(value)
        if kind in (str, int, float, bool, type(None), bytes):
            return
        if kind in (dict, list, tuple, frozenset):
            self._reserve(len(value))
            self._active_containers.add(identity)
            try:
                if kind is dict:
                    entries = tuple(value.items())
                    self._containers.append((value, entries))
                    for key, item in entries:
                        self._visit(key, depth + 1)
                        self._visit(item, depth + 1)
                else:
                    entries = tuple(value)
                    if kind is list:
                        self._containers.append((value, entries))
                    for item in entries:
                        self._visit(item, depth + 1)
            finally:
                self._active_containers.remove(identity)
            return
        if kind in (classmethod, staticmethod):
            self._visit(value.__func__, depth + 1)
            self._visit(value.__dict__, depth + 1)
            return
        if kind is property:
            for function in (value.fget, value.fset, value.fdel):
                if function is not None and type(function) is not FunctionType:
                    raise ValueError("custom parser property accessor")
                self._visit(function, depth + 1)
            return
        if kind is _PATTERN_TYPE:
            pattern, flags = value.pattern, value.flags
            if type(pattern) not in (str, bytes) or type(flags) is not int:
                raise ValueError("unknown parser regular expression")
            self._patterns.append((value, pattern, flags))
            return
        if kind is BuiltinFunctionType:
            origin = (value.__module__, value.__name__)
            if (
                any(type(name) is not str for name in origin)
                or origin not in _STANDARD_NATIVE_FUNCTIONS
            ):
                raise ValueError("unrecognized native parser callable")
            self._native_functions.append((value, origin[0], origin[1]))
            return
        if kind in (
            MethodDescriptorType,
            WrapperDescriptorType,
            GetSetDescriptorType,
            MemberDescriptorType,
        ):
            return
        if kind is ModuleType:
            module_name = ModuleType.__getattribute__(value, "__dict__").get("__name__")
            if type(module_name) is not str or not (
                module_name == "yaml"
                or module_name.startswith("yaml.")
                or value is _ABC_IMPLEMENTATION
                or any(value is module for module, _names in _DEPENDENCY_MEMBERS)
            ):
                raise ValueError("unsupported parser module")
            namespace = ModuleType.__getattribute__(value, "__dict__")
            self._modules.append((value, namespace))
            self._namespace(namespace)
            return
        if kind is FunctionType:
            module_name, _name, _qualname = self._function_names(value)
            if not (
                module_name == "yaml"
                or module_name.startswith("yaml.")
                or module_name in _STANDARD_FUNCTION_MODULES
            ):
                raise ValueError("custom parser callable")
            self._pending.append((value, depth))
            return
        if kind is type or value is self._hashable or value is self._abc_meta:
            module_name = _type_field(value, "__module__")
            if type(module_name) is not str:
                raise ValueError("unknown parser class metadata")
            if module_name.startswith("yaml.") or any(
                value is standard for standard in (self._hashable, self._abc_meta, binascii.Error)
            ):
                self._pending.append((value, depth))
            elif module_name not in ("builtins", "datetime", "types"):
                raise ValueError("custom parser type")
            return
        if value is NotImplemented or value is Ellipsis:
            return
        if value is _class_namespace(self._hashable)["_abc_impl"]:
            # Only the recognized ABC registry inspection below can qualify it;
            # lookup memo contents are intentionally not treated as configuration.
            return
        raise ValueError("opaque parser configuration")

    def _examine(self, value: Any, depth: int) -> None:
        if type(value) is not FunctionType:
            namespace = _class_namespace(value)
            self._reserve(len(namespace))
            entries = tuple(namespace.items())
            bases = _type_field(value, "__bases__")
            mro = _type_field(value, "__mro__")
            self._classes.append((value, bases, mro, entries))
            for base in mro[1:]:
                self._visit(base, depth + 1)
            class_name = _type_field(value, "__qualname__")
            if type(class_name) is not str:
                raise ValueError("unknown parser class name")
            for name, item in entries:
                if type(name) is not str:
                    raise ValueError("unsupported parser class key")
                function = item.__func__ if type(item) in (classmethod, staticmethod) else item
                if type(function) is BuiltinFunctionType or type(item) is type:
                    raise ValueError("custom native parser method")
                if type(item) in (classmethod, staticmethod) and type(function) is not FunctionType:
                    raise ValueError("custom parser method descriptor")
                if type(function) is FunctionType and self._function_names(function)[2] != (
                    class_name + "." + name
                ):
                    raise ValueError("custom parser method")
                self._visit(item, depth + 1)
            return
        names = self._function_names(value)
        self._namespace(value.__globals__)
        module_name = value.__globals__.get("__name__")
        if type(module_name) is not str:
            raise ValueError("unknown parser globals origin")
        module = sys.modules[module_name]
        # Python3.11's collections.abc is a wrapper, whereas the observed
        # Hashable functions own _collections_abc globals bearing that alias.
        if (
            module_name == "collections.abc"
            and type(_ABC_IMPLEMENTATION) is ModuleType
            and value.__globals__ is ModuleType.__getattribute__(_ABC_IMPLEMENTATION, "__dict__")
        ):
            module = _ABC_IMPLEMENTATION
        if type(module) is not ModuleType:
            raise ValueError("unknown parser origin module")
        namespace = ModuleType.__getattribute__(module, "__dict__")
        origin = namespace.get("__file__")
        spec = namespace.get("__spec__")
        if type(spec) is not ModuleSpec:
            raise ValueError("unknown parser module spec")
        if type(_SPEC_DICTIONARY) is not GetSetDescriptorType:
            raise ValueError("unknown parser spec descriptor")
        spec_namespace = _SPEC_DICTIONARY.__get__(spec)
        if type(spec_namespace) is not dict or any(type(key) is not str for key in spec_namespace):
            raise ValueError("unknown parser spec dictionary")
        self._namespace(spec_namespace)
        if not any(spec is previous for previous in self._specifications):
            self._specifications.append(spec)
        spec_name = spec_namespace.get("name")
        filename = value.__code__.co_filename
        if (
            type(origin) is not str
            or type(spec_name) is not str
            or type(filename) is not str
            or value.__globals__ is not namespace
            or filename not in (origin, "<frozen " + spec_name + ">")
            or value.__code__.co_qualname != names[2]
        ):
            raise ValueError("unrecognized parser function origin")
        builtin_namespace = getattr(value, "__builtins__")
        if type(builtin_namespace) is not dict:
            raise ValueError("unknown parser builtin namespace")
        closure = tuple(cell.cell_contents for cell in value.__closure__ or ())
        self._functions.append(
            (
                value,
                value.__code__,
                value.__defaults__,
                value.__kwdefaults__,
                value.__closure__,
                closure,
                value.__globals__,
                builtin_namespace,
                tuple(value.__dict__.items()),
                names,
            )
        )
        for item in (value.__defaults__, value.__kwdefaults__, value.__dict__, *closure):
            self._visit(item, depth + 1)
        self._namespace(value.__globals__)
        self._namespace(builtin_namespace)
        self._visit(module, depth + 1)
        for name in self._names(value.__code__, depth + 1):
            self._global_names.setdefault(id(value.__globals__), (value.__globals__, set()))[1].add(
                name
            )
            item = value.__globals__.get(name, _MISSING)
            if item is not _MISSING:
                self._native_binding(name, item)
                self._visit(item, depth + 1)
            else:
                self._global_names.setdefault(id(builtin_namespace), (builtin_namespace, set()))[
                    1
                ].add(name)
                builtin = builtin_namespace.get(name, _MISSING)
                if builtin is not _MISSING:
                    self._native_binding(name, builtin)
                    self._visit(builtin, depth + 1)

    def _names(self, code: CodeType, depth: int) -> set[str]:
        if depth > _MAX_DISPATCH_DEPTH:
            raise ValueError("parser code qualification depth limit")
        identity = id(code)
        if identity in self._code_names:
            return self._code_names[identity]
        if identity not in self._seen:
            self._seen.add(identity)
            if len(self._seen) > _MAX_DISPATCH_OBJECTS:
                raise ValueError("parser code object limit")
        self._code_items += len(code.co_consts) + 1
        if self._code_items > _MAX_DISPATCH_OBJECTS:
            raise ValueError("parser code qualification state limit")
        self._reserve(len(code.co_names))
        names = {
            instruction.argval
            for instruction in dis.get_instructions(code)
            if instruction.opname == "LOAD_GLOBAL"
        }
        for child in code.co_consts:
            if type(child) is CodeType:
                names.update(self._names(child, depth + 1))
        self._code_names[identity] = names
        return names

    @staticmethod
    def _entries_match(
        current: Any, original: tuple[tuple[str, Any], ...], *, ordered: bool = True
    ) -> bool:
        if len(current) != len(original):
            return False
        if ordered:
            return all(
                key is old_key and item is old_item
                for (key, item), (old_key, old_item) in zip(current.items(), original)
            )
        # Class/module namespace order is not dispatch. Confirm exact string
        # keys before lookup so no unknown key's equality can qualify a hit.
        return all(type(key) is str for key in current) and all(
            current.get(key, _MISSING) is item for key, item in original
        )

    @staticmethod
    def _same_types(current: Any, original: tuple[Any, ...]) -> bool:
        return (
            type(current) is tuple
            and len(current) == len(original)
            and all(item is old for item, old in zip(current, original))
        )

    def unchanged(self) -> bool:
        try:
            if type(self._hashable) is not self._abc_meta or type(self._abc_meta) is not type:
                return False
            for namespace, entries in self._namespaces.values():
                if not self._entries_match(namespace, entries, ordered=False):
                    return False
            if any(type(spec) is not ModuleSpec for spec in self._specifications):
                return False
            for module, namespace in self._modules:
                if type(module) is not ModuleType or (
                    ModuleType.__getattribute__(module, "__dict__") is not namespace
                ):
                    return False
            for value, bases, mro, entries in self._classes:
                if (
                    not self._same_types(_type_field(value, "__bases__"), bases)
                    or not self._same_types(_type_field(value, "__mro__"), mro)
                    or not self._entries_match(_class_namespace(value), entries, ordered=False)
                ):
                    return False
            for function, module_name, name in self._native_functions:
                current = (function.__module__, function.__name__)
                if any(type(part) is not str for part in current) or current != (module_name, name):
                    return False
            for (
                function,
                code,
                defaults,
                kwdefaults,
                closure,
                contents,
                globals_dict,
                builtin_dict,
                attrs,
                names,
            ) in self._functions:
                if (
                    self._function_names(function) != names
                    or function.__code__ is not code
                    or function.__defaults__ is not defaults
                    or function.__kwdefaults__ is not kwdefaults
                    or function.__closure__ is not closure
                    or function.__globals__ is not globals_dict
                    or getattr(function, "__builtins__") is not builtin_dict
                    or not self._entries_match(function.__dict__, attrs, ordered=False)
                ):
                    return False
                if closure and any(
                    cell.cell_contents is not old for cell, old in zip(closure, contents)
                ):
                    return False
            for container, entries in self._containers:
                if type(container) is dict:
                    if not self._entries_match(container, entries):
                        return False
                elif len(container) != len(entries) or any(
                    item is not old for item, old in zip(container, entries)
                ):
                    return False
            for namespace, name, value in self._bindings:
                if namespace.get(name, _MISSING) is not value:
                    return False
            if datetime_module.timezone.utc is not self._utc:
                return False
            for pattern, text, flags in self._patterns:
                if type(pattern) is not _PATTERN_TYPE:
                    return False
                current_text, current_flags = pattern.pattern, pattern.flags
                if (
                    type(current_text) not in (str, bytes)
                    or type(current_flags) is not int
                    or current_text != text
                    or current_flags != flags
                ):
                    return False
            return self._empty_registry()
        except Exception:
            return False


def _capture_parser_guard() -> _DispatchGuard | None:
    try:
        return _DispatchGuard()
    except Exception:
        return None


_PARSER_GUARD = _capture_parser_guard()
_CACHE: OrderedDict[str, Any] = OrderedDict()
_LOCK = Lock()


def _parser_unchanged() -> bool:
    return _PARSER_GUARD is not None and _PARSER_GUARD.unchanged()


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
