"""Bind the fixed mutation execution materials to Git blobs at the subject."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Mapping
from inspect import CO_NEWLOCALS
from pathlib import Path
from types import CodeType, FunctionType, ModuleType

from aiflow.errors import ContractError

_DIRECTORIES = ("src", "tests", ".ai/policy", ".ai/schemas", ".ai/mutations", ".ai/templates")
_FILES = ("pyproject.toml", "uv.lock", ".gitattributes")
_OPTIONAL_FILES = (
    "conftest.py",
    "pytest.ini",
    ".pytest.ini",
    "pytest.toml",
    ".pytest.toml",
    "tox.ini",
    "setup.cfg",
)
_LIMIT = 64 * 1024 * 1024


def _invalid() -> ContractError:
    return ContractError("Mutation subject materials are invalid", code="MUTATION_SUBJECT_INVALID")


def git_environment() -> dict[str, str]:
    environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    environment.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_OPTIONAL_LOCKS="0",
        GIT_NO_REPLACE_OBJECTS="1",
        GIT_NO_LAZY_FETCH="1",
    )
    return environment


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            env=git_environment(),
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise _invalid() from error
    return result.stdout


def subject_materials(root: Path, subject: str) -> dict[str, bytes]:
    """Read the fixed, bounded closure directly from a full commit's Git blobs."""
    if re.fullmatch(r"[0-9a-f]{40}", subject) is None:
        raise _invalid()
    tree = _git(root, "ls-tree", "-r", "-l", "-z", "--full-tree", subject)
    if len(tree) > 8 * 1024 * 1024:
        raise _invalid()
    entries: list[tuple[str, str, int]] = []
    seen: set[str] = set()
    total = 0
    try:
        for item in tree.split(b"\0"):
            if not item:
                continue
            metadata, raw_path = item.split(b"\t", 1)
            mode, kind, oid, size = metadata.split()
            path = raw_path.decode("utf-8", "strict")
            selected = (
                path in _FILES
                or path in _OPTIONAL_FILES
                or ("/" not in path and path.lower().endswith(".py"))
                or any(path.startswith(d + "/") for d in _DIRECTORIES)
            )
            if not selected:
                continue
            if path in seen or mode not in (b"100644", b"100755") or kind != b"blob":
                raise ValueError
            if any(p in ("", ".", "..") for p in path.split("/")) or "\\" in path or ":" in path:
                raise ValueError
            length = int(size)
            total += length
            if length < 0 or total > _LIMIT:
                raise ValueError
            entries.append((path, oid.decode("ascii"), length))
            seen.add(path)
        if not all(f in seen for f in _FILES) or not all(
            any(p.startswith(d + "/") for p in seen) for d in _DIRECTORIES
        ):
            raise ValueError
        request = b"".join(oid.encode("ascii") + b"\n" for _, oid, _ in entries)
        output = _git(root, "cat-file", "--batch", input_bytes=request)
        position = 0
        result: dict[str, bytes] = {}
        for path, object_id, length in entries:
            end = output.index(b"\n", position)
            if output[position:end] != f"{object_id} blob {length}".encode("ascii"):
                raise ValueError
            position = end + 1
            payload = output[position : position + length]
            position += length
            if len(payload) != length or output[position : position + 1] != b"\n":
                raise ValueError
            position += 1
            result[path] = payload
        if position != len(output):
            raise ValueError
        return result
    except (UnicodeError, ValueError, IndexError) as error:
        raise _invalid() from error


def materials_sha256(materials: Mapping[str, bytes]) -> str:
    """Hash sorted paths and SHA-256 of each canonical Git blob."""
    pairs = [[path, hashlib.sha256(data).hexdigest()] for path, data in sorted(materials.items())]
    return hashlib.sha256(
        json.dumps(pairs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def content_matches(actual: bytes, original: bytes) -> bool:
    if actual == original:
        return True
    if b"\x00" in original or b"\r" in original:
        return False
    try:
        original.decode("utf-8", "strict")
    except UnicodeError:
        return False
    return actual == original.replace(b"\n", b"\r\n")


def _is_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def material_file_matches(root: Path, path: str, original: bytes) -> bool:
    """Compare one regular, nonsymlinked checkout file with its Git blob."""
    if (
        not path
        or "\\" in path
        or ":" in path
        or any(part in ("", ".", "..") for part in path.split("/"))
    ):
        return False
    current = root
    try:
        for part in path.split("/"):
            current = current / part
            if _is_link(current):
                return False
        if not current.is_file():
            return False
        # A CRLF checkout can add at most one byte per canonical LF.
        with current.open("rb") as source:
            actual = source.read(len(original) + original.count(b"\n") + 1)
        return content_matches(actual, original)
    except (OSError, ValueError):
        return False


def checkout_matches_materials(root: Path, materials: Mapping[str, bytes]) -> bool:
    """Require exact closure paths and Git bytes, allowing plain UTF-8 LF/CRLF checkout."""
    found: set[str] = set()
    try:
        for directory in _DIRECTORIES:
            start = root / directory
            if _is_link(start) or not start.is_dir():
                return False
            for current, dirs, files in os.walk(start, followlinks=False):
                base = Path(current)
                if any(_is_link(base / name) for name in (*dirs, *files)):
                    return False
                for name in files:
                    path = base / name
                    if not path.is_file():
                        return False
                    found.add(path.relative_to(root).as_posix())
        for name in _FILES:
            path = root / name
            if _is_link(path) or not path.is_file():
                return False
            found.add(name)
        for path in root.iterdir():
            if path.name.lower() in _OPTIONAL_FILES or path.name.lower().endswith(".py"):
                if _is_link(path) or not path.is_file():
                    return False
                found.add(path.name)
        if found != set(materials):
            return False
        return all(material_file_matches(root, name, blob) for name, blob in materials.items())
    except (OSError, UnicodeError):
        return False


def _class_methods_match(cls: type, body: CodeType, path: Path, module: ModuleType) -> bool:
    expected = {
        code
        for code in body.co_consts
        if isinstance(code, CodeType)
        and code.co_flags & CO_NEWLOCALS
        and code.co_name.isidentifier()
    }
    observed: set[CodeType] = set()
    for name, descriptor in vars(cls).items():
        if isinstance(descriptor, (staticmethod, classmethod)):
            descriptor = descriptor.__func__
        functions = (
            (descriptor.fget, descriptor.fset, descriptor.fdel)
            if isinstance(descriptor, property)
            else (descriptor,)
        )
        for function in functions:
            if not isinstance(function, FunctionType):
                continue
            code = function.__code__
            origin = Path(code.co_filename)
            # dataclasses adds methods outside the class body. Only code from
            # this source may satisfy (or add to) its declared methods.
            if origin.is_absolute() and origin.resolve() == path:
                if code.co_name != name or function.__globals__ is not vars(module):
                    return False
                observed.add(code)
    return observed == expected


def _module_identity_matches(
    root: Path, materials: Mapping[str, bytes], name: str, module: ModuleType
) -> bool:
    """Check a loaded module's source path, blob bytes, and owned functions."""
    if name != "aiflow" and not name.startswith("aiflow."):
        return False
    parts = name.split(".")
    if any(not part.isidentifier() for part in parts):
        return False
    prefix = "/".join(("src", *parts))
    candidates = (prefix + ".py", prefix + "/__init__.py")
    try:
        if not isinstance(module.__file__, str):
            return False
        path = Path(module.__file__).resolve(strict=True)
        matches = [
            candidate
            for candidate in candidates
            if candidate in materials and (root / candidate).resolve(strict=True) == path
        ]
        if len(matches) != 1 or module.__name__ != name:
            return False
        relative = matches[0]
        if not material_file_matches(root, relative, materials[relative]):
            return False
        # A long-lived caller can still hold old functions after switching the
        # checkout at the same path. Compare the code loaded by this interpreter.
        subject_code = compile(materials[relative], str(path), "exec", dont_inherit=True)
        for body in subject_code.co_consts:
            if isinstance(body, CodeType) and not body.co_flags & CO_NEWLOCALS:
                cls = vars(module).get(body.co_name)
                if (
                    not isinstance(cls, type)
                    or cls.__module__ != name
                    or cls.__qualname__ != body.co_qualname
                    or not _class_methods_match(cls, body, path, module)
                ):
                    return False
        for member in vars(module).values():
            if isinstance(member, FunctionType) and member.__module__ == name:
                wrapped = getattr(member, "__wrapped__", None)
                if (
                    isinstance(wrapped, FunctionType)
                    and member.__code__ is contextlib.contextmanager(wrapped).__code__
                ):
                    # contextmanager's helper executes the function in its closure.
                    if (
                        member.__globals__ is not vars(contextlib)
                        or member.__closure__ is None
                        or len(member.__closure__) != 1
                        or member.__closure__[0].cell_contents is not wrapped
                        or wrapped.__module__ != name
                    ):
                        return False
                    member = wrapped
                if (
                    Path(member.__code__.co_filename).resolve(strict=True) != path
                    or member.__code__ not in subject_code.co_consts
                ):
                    return False
        return True
    except (OSError, AttributeError, SyntaxError, TypeError, ValueError):
        return False


def loaded_engine_matches(root: Path, materials: Mapping[str, bytes]) -> bool:
    """Fail closed if any loaded AI Flow module is not the bound subject copy."""
    modules = [
        (name, module)
        for name, module in tuple(sys.modules.items())
        if name == "aiflow" or name.startswith("aiflow.")
    ]
    if not any(name == "aiflow" for name, _ in modules):
        return False
    return all(
        isinstance(module, ModuleType) and _module_identity_matches(root, materials, name, module)
        for name, module in modules
    )
