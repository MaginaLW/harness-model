"""Safe, atomic local storage for AI Flow task records."""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

import yaml

from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError, StorageError

TASK_ID_PATTERN = re.compile(r"^TASK-(?P<number>[0-9]{4,})$")
MAX_RESERVATION_ATTEMPTS = 10


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def task_root(repository_root: Path) -> Path:
    """Return the physical task root, rejecting repository-local symlink escapes."""
    repository = repository_root.resolve()
    root = (repository / ".ai" / "tasks").resolve()
    if not _is_within(root, repository):
        raise StorageError(
            "Task root escapes the repository",
            code="STORAGE_PATH_ESCAPE",
            details={"repository_root": str(repository)},
        )
    return root


def validate_task_id(task_id: str) -> int:
    """Validate a canonical task ID and return its numeric component."""
    match = TASK_ID_PATTERN.fullmatch(task_id)
    if match is None:
        raise StorageError(
            "Invalid task ID",
            code="STORAGE_INVALID_TASK_ID",
            details={"task_id": task_id},
        )
    return int(match.group("number"))


def resolve_task_path(
    repository_root: Path,
    task_id: str,
    relative_path: str | Path = Path(),
) -> Path:
    """Resolve a path below one task without permitting lexical or symlink escape."""
    validate_task_id(task_id)
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise StorageError(
            "Task subpath must be relative and cannot contain '..'",
            code="STORAGE_PATH_ESCAPE",
            details={"task_id": task_id},
        )

    root = task_root(repository_root)
    task_directory = (root / task_id).resolve()
    target = (task_directory / relative).resolve()
    if not _is_within(task_directory, root) or not _is_within(target, task_directory):
        raise StorageError(
            "Resolved task path escapes the task directory",
            code="STORAGE_PATH_ESCAPE",
            details={"task_id": task_id},
        )
    return target


def _existing_task_numbers(root: Path) -> list[int]:
    numbers: list[int] = []
    for entry in root.iterdir():
        match = TASK_ID_PATTERN.fullmatch(entry.name)
        if match is not None and entry.is_dir() and not entry.is_symlink():
            numbers.append(int(match.group("number")))
    return numbers


def _mkdir_reserved_directory(path: Path) -> None:
    path.mkdir(exist_ok=False)


def reserve_task_id(
    repository_root: Path,
    *,
    max_attempts: int = MAX_RESERVATION_ATTEMPTS,
) -> str:
    """Atomically reserve and return the next task ID, retrying creation races."""
    root = task_root(repository_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise StorageError(
            "Could not create task root",
            code="STORAGE_ID_RESERVATION_FAILED",
            details={},
        ) from error
    for _attempt in range(max_attempts):
        try:
            numbers = _existing_task_numbers(root)
        except OSError as error:
            raise StorageError(
                "Could not scan existing task IDs",
                code="STORAGE_ID_RESERVATION_FAILED",
                details={},
            ) from error
        next_number = max(numbers, default=0) + 1
        task_id = f"TASK-{next_number:04d}"
        try:
            _mkdir_reserved_directory(root / task_id)
        except FileExistsError:
            continue
        except OSError as error:
            raise StorageError(
                "Could not reserve task ID",
                code="STORAGE_ID_RESERVATION_FAILED",
                details={"task_id": task_id},
            ) from error
        return task_id

    raise StorageError(
        "Could not reserve a unique task ID after concurrent updates",
        code="STORAGE_ID_RESERVATION_FAILED",
        details={"attempts": max_attempts},
    )


def _atomic_write_text(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            text=True,
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except (OSError, TypeError, ValueError) as error:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
        raise StorageError(
            "Could not atomically write task document",
            code="STORAGE_WRITE_FAILED",
            details={"filename": target.name},
        ) from error


def atomic_write_json(target: Path, value: object) -> None:
    """Serialize and atomically replace a JSON document."""
    try:
        content = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    except (TypeError, ValueError) as error:
        raise StorageError(
            "Could not serialize JSON task document",
            code="STORAGE_WRITE_FAILED",
            details={"filename": target.name},
        ) from error
    _atomic_write_text(target, content)


def atomic_write_yaml(target: Path, value: object) -> None:
    """Serialize and atomically replace a YAML document."""
    try:
        content = yaml.safe_dump(value, allow_unicode=True, sort_keys=False)
    except yaml.YAMLError as error:
        raise StorageError(
            "Could not serialize YAML task document",
            code="STORAGE_WRITE_FAILED",
            details={"filename": target.name},
        ) from error
    _atomic_write_text(target, content)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise StorageError(
            "Could not read task document",
            code="STORAGE_READ_FAILED",
            details={"filename": path.name},
        ) from error


def _validate(contract_name: str | None, value: object) -> None:
    if contract_name is None:
        return
    try:
        require_valid_contract(contract_name, value)
    except ContractError:
        raise
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise ContractError(
            "Could not validate task document contract",
            code="CONTRACT_VALIDATION_FAILED",
            details={"contract_name": contract_name},
        ) from error


def read_task_json(
    repository_root: Path,
    task_id: str,
    relative_path: str | Path,
    *,
    contract_name: str | None = None,
) -> Any:
    """Read JSON from a safe task path and immediately validate its contract."""
    path = resolve_task_path(repository_root, task_id, relative_path)
    try:
        value = json.loads(_read_text(path))
    except json.JSONDecodeError as error:
        raise StorageError(
            "Could not parse JSON task document",
            code="STORAGE_PARSE_FAILED",
            details={"filename": path.name},
        ) from error
    _validate(contract_name, value)
    return value


def read_task_yaml(
    repository_root: Path,
    task_id: str,
    relative_path: str | Path,
    *,
    contract_name: str | None = None,
) -> Any:
    """Read YAML from a safe task path and immediately validate its contract."""
    path = resolve_task_path(repository_root, task_id, relative_path)
    try:
        value = yaml.safe_load(_read_text(path))
    except yaml.YAMLError as error:
        raise StorageError(
            "Could not parse YAML task document",
            code="STORAGE_PARSE_FAILED",
            details={"filename": path.name},
        ) from error
    _validate(contract_name, value)
    return value
