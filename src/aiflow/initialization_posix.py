"""Narrow POSIX object operations for non-overwriting initialization.

Creation uses O_NOFOLLOW/O_CLOEXEC and directory file descriptors so existing
objects and symlinks are rejected, and identity publication uses atomic
non-replacing link + unlink + fsync. This is not a sandbox against concurrent
same-user writers.
"""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from aiflow.errors import AiflowError

_DIRECTORY = 0x10
_REPARSE = 0x400
_MAX_FILE_BYTES = 1024 * 1024
_REQUIRED_API = (
    "O_NOFOLLOW",
    "O_DIRECTORY",
    "O_CLOEXEC",
    "O_RDONLY",
    "O_RDWR",
    "O_CREAT",
    "O_EXCL",
    "open",
    "mkdir",
    "link",
    "unlink",
    "fstat",
    "fsync",
    "lseek",
    "read",
    "write",
    "close",
)


@dataclass
class _OwnedHandle:
    directory: bool
    writable: bool = False
    allow_rename: bool = False
    created: bool = False
    write_started: bool = False
    parent_fd: int | None = None
    name: str | None = None
    parent_path: Path | None = None
    owns_parent_fd: bool = False
    path: Path | None = None


def _invalid() -> AiflowError:
    return AiflowError(
        "Initialization POSIX operation has invalid input",
        code="INITIALIZATION_POSIX_INVALID",
    )


def _absolute_name(path: Path) -> str:
    if not isinstance(path, Path) or not path.is_absolute() or "\0" in str(path):
        raise _invalid()
    text = str(path)
    try:
        text.encode("utf-8")
    except UnicodeError as error:
        raise _invalid() from error
    return text


def _child_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or any(ord(char) < 32 or ord(char) == 127 or char in "/\\\0" for char in name)
    ):
        raise _invalid()
    try:
        encoded = name.encode("utf-8")
    except UnicodeError as error:
        raise _invalid() from error
    if len(encoded) > 255:
        raise _invalid()
    return name


class PosixFilesystem:
    """Only initialization's fixed handle operations, with an injectable flat POSIX API."""

    def __init__(self, api: Any = None) -> None:
        if api is None:
            if (
                os.name != "posix"
                or sys.implementation.name != "cpython"
                or sys.version_info < (3, 11)
            ):
                raise AiflowError(
                    "Initialization requires POSIX and CPython >= 3.11",
                    code="INITIALIZATION_UNSUPPORTED",
                )
            resolved: dict[str, Any] = {}
            for name in _REQUIRED_API:
                member = getattr(os, name, None)
                if member is None:
                    raise AiflowError(
                        "Initialization POSIX APIs are unavailable",
                        code="INITIALIZATION_UNSUPPORTED",
                    )
                resolved[name] = member
            resolved["fstatvfs"] = getattr(os, "fstatvfs", None)
            api = SimpleNamespace(**resolved)
        else:
            for name in _REQUIRED_API:
                if getattr(api, name, None) is None:
                    raise AiflowError(
                        "Initialization POSIX APIs are unavailable",
                        code="INITIALIZATION_UNSUPPORTED",
                    )
        self._api = api
        self._handles: dict[int, _OwnedHandle] = {}

    def _failed(self, operation: str, error: OSError | None = None) -> AiflowError:
        details: dict[str, Any] = {"operation": operation}
        if error is not None and error.errno is not None:
            details["errno"] = error.errno
        return AiflowError(
            "Initialization POSIX operation failed",
            code="INITIALIZATION_POSIX_FAILED",
            details=details,
        )

    def _owned(self, handle: int) -> _OwnedHandle:
        if not isinstance(handle, int) or isinstance(handle, bool) or handle not in self._handles:
            raise _invalid()
        return self._handles[handle]

    def _stat(self, fd: int) -> tuple[dict[str, int], int]:
        try:
            st = self._api.fstat(fd)
        except OSError as error:
            raise self._failed("fstat", error) from error
        mode = int(st.st_mode)
        attributes = (_DIRECTORY if stat.S_ISDIR(mode) else 0) | (
            _REPARSE if stat.S_ISLNK(mode) else 0
        )
        return (
            {
                "volume": int(st.st_dev),
                "file_id": int(st.st_ino),
                "links": int(st.st_nlink),
                "attributes": attributes,
                "size": int(st.st_size),
            },
            mode,
        )

    def _open_raw(
        self,
        path: str,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
        create: bool = False,
    ) -> int:
        try:
            if create:
                fd = self._api.open(path, flags, mode, dir_fd=dir_fd)
            elif dir_fd is not None:
                fd = self._api.open(path, flags, dir_fd=dir_fd)
            else:
                fd = self._api.open(path, flags)
        except OSError as error:
            raise self._failed("open", error) from error
        if not isinstance(fd, int) or isinstance(fd, bool) or fd < 0 or fd in self._handles:
            raise self._failed("open")
        return fd

    def _close_raw(self, fd: int) -> None:
        try:
            self._api.close(fd)
        except OSError:
            pass

    def _register(self, fd: int, ownership: _OwnedHandle) -> int:
        self._handles[fd] = ownership
        try:
            facts, mode = self._stat(fd)
            if (
                facts["attributes"] & _REPARSE
                or bool(facts["attributes"] & _DIRECTORY) is not ownership.directory
                or (not ownership.directory and (not stat.S_ISREG(mode) or facts["links"] != 1))
            ):
                raise _invalid()
        except AiflowError:
            self.close(fd)
            raise
        return fd

    def _dir_flags(self) -> int:
        return int(
            self._api.O_RDONLY | self._api.O_DIRECTORY | self._api.O_NOFOLLOW | self._api.O_CLOEXEC
        )

    def _pin_ancestor(self, path: Path) -> int:
        text = _absolute_name(path)
        fd = self._open_raw(text, self._dir_flags())
        return self._register(fd, _OwnedHandle(directory=True, path=path))

    def open_directory(self, path: Path, *, share_write: bool = False) -> int:
        del share_write
        text = _absolute_name(path)
        fd = self._open_raw(text, self._dir_flags())
        return self._register(fd, _OwnedHandle(directory=True, path=path))

    def open_file(self, path: Path, *, writable: bool = False, allow_rename: bool = False) -> int:
        text = _absolute_name(path)
        flags = (
            (self._api.O_RDWR if writable else self._api.O_RDONLY)
            | self._api.O_NOFOLLOW
            | self._api.O_CLOEXEC
        )
        if not allow_rename:
            fd = self._open_raw(text, flags)
            return self._register(fd, _OwnedHandle(directory=False, writable=writable))
        child = _child_name(path.name)
        parent_text = _absolute_name(path.parent)
        dir_flags = (
            self._api.O_RDONLY | self._api.O_DIRECTORY | self._api.O_NOFOLLOW | self._api.O_CLOEXEC
        )
        parent_fd = self._open_raw(parent_text, dir_flags)
        try:
            parent_st = self._api.fstat(parent_fd)
        except OSError as error:
            self._close_raw(parent_fd)
            raise self._failed("fstat", error) from error
        parent_mode = int(parent_st.st_mode)
        if stat.S_ISLNK(parent_mode) or not stat.S_ISDIR(parent_mode):
            self._close_raw(parent_fd)
            raise _invalid()
        try:
            fd = self._open_raw(child, flags, dir_fd=parent_fd)
        except AiflowError:
            self._close_raw(parent_fd)
            raise
        return self._register(
            fd,
            _OwnedHandle(
                directory=False,
                writable=writable,
                allow_rename=True,
                parent_fd=parent_fd,
                name=child,
                parent_path=path.parent,
                owns_parent_fd=True,
            ),
        )

    def create_directory(self, parent_handle: int, name: str, *, share_write: bool = False) -> int:
        del share_write
        parent = self._owned(parent_handle)
        if not parent.directory:
            raise _invalid()
        child = _child_name(name)
        try:
            self._api.mkdir(child, 0o755, dir_fd=parent_handle)
        except OSError as error:
            raise self._failed("mkdir", error) from error
        fd = self._open_raw(child, self._dir_flags(), dir_fd=parent_handle)
        child_path = parent.path / child if parent.path is not None else None
        return self._register(fd, _OwnedHandle(directory=True, created=True, path=child_path))

    def create_file(self, parent_handle: int, name: str, *, allow_rename: bool = False) -> int:
        parent = self._owned(parent_handle)
        if not parent.directory:
            raise _invalid()
        child = _child_name(name)
        flags = (
            self._api.O_CREAT
            | self._api.O_EXCL
            | self._api.O_RDWR
            | self._api.O_NOFOLLOW
            | self._api.O_CLOEXEC
        )
        fd = self._open_raw(child, flags, 0o644, dir_fd=parent_handle, create=True)
        return self._register(
            fd,
            _OwnedHandle(
                directory=False,
                writable=True,
                allow_rename=allow_rename,
                created=True,
                parent_fd=parent_handle if allow_rename else None,
                name=child if allow_rename else None,
                parent_path=parent.path if allow_rename else None,
                owns_parent_fd=False,
            ),
        )

    def _seek_start(self, handle: int) -> None:
        try:
            self._api.lseek(handle, 0, 0)
        except OSError as error:
            raise self._failed("lseek", error) from error

    def read(self, handle: int, limit: int) -> bytes:
        if (
            self._owned(handle).directory
            or not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 0 <= limit <= _MAX_FILE_BYTES
        ):
            raise _invalid()
        self._seek_start(handle)
        data = bytearray()
        while len(data) <= limit:
            amount = min(64 * 1024, limit + 1 - len(data))
            try:
                chunk = self._api.read(handle, amount)
            except OSError as error:
                raise self._failed("read", error) from error
            if not isinstance(chunk, bytes) or len(chunk) > amount:
                raise self._failed("read")
            if not chunk:
                return bytes(data)
            data.extend(chunk)
        raise _invalid()

    def write(self, handle: int, data: bytes) -> None:
        ownership = self._owned(handle)
        if (
            ownership.directory
            or not ownership.created
            or not ownership.writable
            or ownership.write_started
            or not isinstance(data, bytes)
            or len(data) > _MAX_FILE_BYTES
        ):
            raise _invalid()
        ownership.write_started = True
        self._seek_start(handle)
        for offset in range(0, len(data), 64 * 1024):
            chunk = data[offset : offset + 64 * 1024]
            try:
                written = self._api.write(handle, chunk)
            except OSError as error:
                raise self._failed("write", error) from error
            if not isinstance(written, int) or isinstance(written, bool) or written != len(chunk):
                raise self._failed("write")

    def flush(self, handle: int) -> None:
        self._owned(handle)
        try:
            self._api.fsync(handle)
        except OSError as error:
            raise self._failed("fsync", error) from error

    def identity(self, handle: int) -> dict[str, int]:
        self._owned(handle)
        facts, _ = self._stat(handle)
        return facts

    def volume(self, handle: int) -> dict[str, str | int]:
        self._owned(handle)
        fstatvfs = getattr(self._api, "fstatvfs", None)
        if fstatvfs is None:
            return {"filesystem": "POSIX", "flags": 0, "max_component": 255}
        try:
            stats = fstatvfs(handle)
        except OSError as error:
            raise self._failed("fstatvfs", error) from error
        return {
            "filesystem": "POSIX",
            "flags": int(stats.f_flag),
            "max_component": int(stats.f_namemax),
        }

    def rename_no_replace(self, handle: int, target: Path) -> None:
        ownership = self._owned(handle)
        if not ownership.allow_rename or ownership.parent_fd is None or ownership.name is None:
            raise _invalid()
        _absolute_name(target)
        target_name = _child_name(target.name)
        if ownership.parent_path is not None and target.parent != ownership.parent_path:
            raise _invalid()
        if not ownership.owns_parent_fd:
            self._owned(ownership.parent_fd)
        before = self.identity(handle)
        parent_fd = ownership.parent_fd
        pending_name = ownership.name
        try:
            self._api.link(pending_name, target_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        except OSError as error:
            raise self._failed("link", error) from error
        try:
            self._api.unlink(pending_name, dir_fd=parent_fd)
        except OSError as error:
            raise self._failed("unlink", error) from error
        try:
            self._api.fsync(parent_fd)
        except OSError as error:
            raise self._failed("fsync", error) from error
        ownership.name = target_name
        after = self.identity(handle)
        if (after["volume"], after["file_id"]) != (before["volume"], before["file_id"]) or after[
            "links"
        ] != 1:
            raise self._failed("rename_no_replace")

    def close(self, handle: int) -> None:
        ownership = self._owned(handle)
        first_error: OSError | None = None
        try:
            self._api.close(handle)
        except OSError as error:
            first_error = error
        if ownership.owns_parent_fd and ownership.parent_fd is not None:
            try:
                self._api.close(ownership.parent_fd)
            except OSError as error:
                if first_error is None:
                    first_error = error
            ownership.owns_parent_fd = False
            ownership.parent_fd = None
        if first_error is not None:
            raise self._failed("close", first_error) from first_error
        del self._handles[handle]
