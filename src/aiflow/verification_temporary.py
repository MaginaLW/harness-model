"""Run-owned pytest fixture directories without cleanup or environment changes.

The guards reject ordinary collisions and detectable path changes. They are not
an OS sandbox against another process deliberately racing filesystem operations.
"""

from __future__ import annotations

import os
import re
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PureWindowsPath
from types import MappingProxyType

from aiflow.errors import ContractError

_WINDOWS = os.name == "nt"
_TASK_ID = re.compile(r"TASK-[0-9]{4,}\Z")
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_EXECUTION_ID = re.compile(r"EXEC-[0-9]{3,}\Z")
_CONTAINER_NAME = re.compile(
    r"aiflow-pytest-(?P<task>TASK-[0-9]{4,})-(?P<run>[A-Za-z0-9][A-Za-z0-9_.-]*)\Z"
)
_DEVICE = re.compile(
    r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?\Z", re.I
)
DirectoryIdentity = tuple[int, int]
ParentIdentityChain = tuple[tuple[Path, DirectoryIdentity], ...]


@dataclass(frozen=True)
class PytestTemporaryLayout:
    """A pure plan, or an allocated plan carrying its container identity."""

    parent: Path
    container: Path
    leaves: Mapping[str, Path]
    parent_identity_chain: ParentIdentityChain
    container_identity: DirectoryIdentity | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "leaves", MappingProxyType(dict(self.leaves)))


def _invalid(code: str) -> ContractError:
    return ContractError("Pytest temporary directory or execution is invalid", code=code)


def _ordinary_component(value: str) -> bool:
    return bool(
        value
        and value not in {".", ".."}
        and not value.endswith((".", " "))
        and not _DEVICE.fullmatch(value)
        and not any(character in value for character in ":/\\")
        and not any(unicodedata.category(character) in {"Cc", "Cs"} for character in value)
    )


def _drive_type(path: Path) -> int:
    import ctypes

    return int(ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor)))


def _ordinary_absolute_path(path: Path) -> Path:
    if not isinstance(path, Path):
        raise _invalid("PYTEST_TEMP_ROOT_INVALID")
    raw = os.fspath(path)
    windows = PureWindowsPath(raw)
    if (
        not path.is_absolute()
        or raw.replace("\\", "/").startswith("//")
        or any(unicodedata.category(character) in {"Cc", "Cs"} for character in raw)
        or windows.drive
        and not re.fullmatch(r"[A-Za-z]:", windows.drive)
        or any(not _ordinary_component(part) for part in windows.parts if part != windows.anchor)
    ):
        raise _invalid("PYTEST_TEMP_ROOT_INVALID")
    if _WINDOWS:
        try:
            supported = _drive_type(path) in {2, 3, 5, 6}
        except (OSError, ValueError):
            raise _invalid("PYTEST_TEMP_ROOT_INVALID") from None
        if not supported:
            raise _invalid("PYTEST_TEMP_ROOT_INVALID")
    return path


def _io_path(path: Path) -> Path:
    # Lexical validation precedes use of extended Win32 paths for long fixture roots.
    return Path("\\\\?\\" + str(path)) if _WINDOWS else path


def _lstat(path: Path) -> os.stat_result:
    return _io_path(path).lstat()


def _identity(metadata: os.stat_result) -> DirectoryIdentity:
    return metadata.st_dev, metadata.st_ino


def _directory_identity(path: Path) -> DirectoryIdentity:
    try:
        metadata = _lstat(path)
    except (OSError, ValueError):
        raise _invalid("PYTEST_TEMP_ROOT_INVALID") from None
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or getattr(metadata, "st_file_attributes", 0) & 1024
        or metadata.st_ino <= 0
    ):
        raise _invalid("PYTEST_TEMP_ROOT_INVALID")
    return _identity(metadata)


def _lexists(path: Path) -> bool:
    try:
        _lstat(path)
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        raise _invalid("PYTEST_TEMP_ROOT_INVALID") from None
    return True


def _parent_paths(parent: Path) -> tuple[Path, ...]:
    return (*reversed(parent.parents), parent)


def _unmarked_directory_identity(path: Path) -> DirectoryIdentity:
    identity = _directory_identity(path)
    if _lexists(path / ".git") or (
        _lexists(path / "HEAD") and (_lexists(path / "objects") or _lexists(path / "commondir"))
    ):
        raise _invalid("PYTEST_TEMP_ROOT_INVALID")
    return identity


def _parent_chain(parent: Path) -> ParentIdentityChain:
    _ordinary_absolute_path(parent)
    chain: list[tuple[Path, DirectoryIdentity]] = []
    for path in _parent_paths(parent):
        identity = _unmarked_directory_identity(path)
        chain.append((path, identity))
    return tuple(chain)


def _resolve_parent(parent: Path) -> Path:
    """Read the physical destination only after rejecting logical link boundaries."""
    canonical = _io_path(parent).resolve(strict=True)
    raw = os.fspath(canonical)
    # Only unwrap local drive paths returned by our internal extended-path lookup.
    # User namespaces have already been refused; all other results stay invalid.
    if _WINDOWS and raw.startswith("\\\\?\\") and re.fullmatch(r"[A-Za-z]:\\.*", raw[4:]):
        return Path(raw[4:])
    return canonical


def _canonical_parent(parent: Path) -> tuple[Path, ParentIdentityChain]:
    logical_chain = _parent_chain(parent)
    try:
        canonical = _resolve_parent(parent)
    except (OSError, ValueError, RuntimeError):
        raise _invalid("PYTEST_TEMP_ROOT_INVALID") from None
    physical_chain = _parent_chain(canonical)
    if logical_chain[-1][1] != physical_chain[-1][1] or _parent_chain(parent) != logical_chain:
        raise _invalid("PYTEST_TEMP_IDENTITY_CHANGED")
    return canonical, physical_chain


def validate_pytest_temp_root(parent: Path) -> Path:
    """Return a validated physical parent outside logical and physical Git ancestry."""
    canonical, _chain = _canonical_parent(parent)
    return canonical


def _safe_id(value: str, pattern: re.Pattern[str]) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= 255
        and bool(pattern.fullmatch(value))
        and _ordinary_component(value)
    )


def _assert_absent(path: Path) -> None:
    if _lexists(path):
        raise _invalid("PYTEST_TEMP_DIRECTORY_CONFLICT")


def plan_pytest_temporary(
    parent: Path, task_id: str, run_id: str, execution_ids: Sequence[str]
) -> PytestTemporaryLayout:
    """Inspect the parent and derive deterministic paths without creating directories."""
    parent, chain = _canonical_parent(parent)
    if not _safe_id(task_id, _TASK_ID) or not _safe_id(run_id, _RUN_ID):
        raise _invalid("PYTEST_TEMP_LAYOUT_INVALID")
    identifiers = tuple(execution_ids)
    if not all(
        _safe_id(identifier, _EXECUTION_ID) and len(f"pytest-{identifier}") <= 255
        for identifier in identifiers
    ) or len(set(identifiers)) != len(identifiers):
        raise _invalid("PYTEST_TEMP_LAYOUT_INVALID")
    name = f"aiflow-pytest-{task_id}-{run_id}"
    if len(name) > 255:
        raise _invalid("PYTEST_TEMP_LAYOUT_INVALID")
    container = parent / name
    _assert_absent(container)
    return PytestTemporaryLayout(
        parent,
        container,
        {identifier: container / f"pytest-{identifier}" for identifier in identifiers},
        chain,
    )


def _valid_identity(identity: object) -> bool:
    return (
        isinstance(identity, tuple)
        and len(identity) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) for value in identity)
        and identity[0] >= 0
        and identity[1] > 0
    )


def _validate_layout(layout: PytestTemporaryLayout) -> None:
    if not isinstance(layout, PytestTemporaryLayout):
        raise _invalid("PYTEST_TEMP_LAYOUT_INVALID")
    _ordinary_absolute_path(layout.parent)
    if not isinstance(layout.container, Path):
        raise _invalid("PYTEST_TEMP_LAYOUT_INVALID")
    name = _CONTAINER_NAME.fullmatch(layout.container.name)
    if (
        layout.container.parent != layout.parent
        or name is None
        or not _safe_id(name.group("task"), _TASK_ID)
        or not _safe_id(name.group("run"), _RUN_ID)
        or not _ordinary_component(layout.container.name)
        or len(layout.container.name) > 255
        or any(
            not _safe_id(identifier, _EXECUTION_ID)
            or len(f"pytest-{identifier}") > 255
            or leaf != layout.container / f"pytest-{identifier}"
            for identifier, leaf in layout.leaves.items()
        )
        or not isinstance(layout.parent_identity_chain, tuple)
        or len(layout.parent_identity_chain) != len(_parent_paths(layout.parent))
        or any(
            not isinstance(entry, tuple)
            or len(entry) != 2
            or entry[0] != path
            or not _valid_identity(entry[1])
            for path, entry in zip(_parent_paths(layout.parent), layout.parent_identity_chain)
        )
        or layout.container_identity is not None
        and not _valid_identity(layout.container_identity)
    ):
        raise _invalid("PYTEST_TEMP_LAYOUT_INVALID")


def _assert_parent_identity(layout: PytestTemporaryLayout) -> None:
    if _parent_chain(layout.parent) != layout.parent_identity_chain:
        raise _invalid("PYTEST_TEMP_IDENTITY_CHANGED")


def _mkdir_container(path: Path) -> None:
    _io_path(path).mkdir(mode=0o700, exist_ok=False)


def create_pytest_temporary(layout: PytestTemporaryLayout) -> PytestTemporaryLayout:
    """Atomically claim one new container; leave all existing content untouched."""
    _validate_layout(layout)
    if layout.container_identity is not None or not layout.leaves:
        raise _invalid("PYTEST_TEMP_LAYOUT_INVALID")
    _assert_parent_identity(layout)
    _assert_absent(layout.container)
    try:
        _mkdir_container(layout.container)
    except FileExistsError:
        raise _invalid("PYTEST_TEMP_DIRECTORY_CONFLICT") from None
    except (OSError, ValueError):
        raise _invalid("PYTEST_TEMP_ROOT_INVALID") from None
    _assert_parent_identity(layout)
    prepared = replace(layout, container_identity=_unmarked_directory_identity(layout.container))
    for leaf in prepared.leaves.values():
        _assert_absent(leaf)
    return prepared


def validate_pytest_temporary(
    layout: PytestTemporaryLayout, execution_id: str, argv: tuple[str, ...]
) -> None:
    """Refuse changed ownership, old leaves, or any alternate basetemp argument."""
    _validate_layout(layout)
    leaf = layout.leaves.get(execution_id)
    if layout.container_identity is None or leaf is None:
        raise _invalid("PYTEST_TEMP_LAYOUT_INVALID")
    if (
        not isinstance(argv, tuple)
        or len(argv) < 4
        or not all(isinstance(argument, str) and argument for argument in argv)
        or argv[1:3] != ("-m", "pytest")
        or argv[-1] != f"--basetemp={leaf.as_posix()}"
        or sum(argument == "--basetemp" or argument.startswith("--basetemp=") for argument in argv)
        != 1
    ):
        raise _invalid("PYTEST_TEMP_ARGUMENT_INVALID")
    _assert_parent_identity(layout)
    if _unmarked_directory_identity(layout.container) != layout.container_identity:
        raise _invalid("PYTEST_TEMP_IDENTITY_CHANGED")
    _assert_absent(leaf)
    _assert_parent_identity(layout)
    if _unmarked_directory_identity(layout.container) != layout.container_identity:
        raise _invalid("PYTEST_TEMP_IDENTITY_CHANGED")
    _assert_absent(leaf)
