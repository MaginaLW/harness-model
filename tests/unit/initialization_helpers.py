"""Portable state-machine model; it does not prove Windows locking or atomicity."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from aiflow.errors import AiflowError


class PortableFilesystem:
    """Use fixture files and the public helper API without a host-platform branch."""

    instances: list[PortableFilesystem] = []

    def __init__(self, api=None) -> None:
        self.handles: dict[int, dict] = {}
        self.next_handle = 1000
        self.instances.append(self)

    def _error(self, operation: str) -> AiflowError:
        return AiflowError(f"Portable fixture operation failed: {operation}")

    def _path(self, parent: int, name: str) -> Path:
        if (
            not isinstance(name, str)
            or name in {"", ".", ".."}
            or any(char in name for char in "/\\:\0")
        ):
            raise self._error("relative name")
        return self.handles[parent]["path"] / name

    def _hold(self, path: Path, *, directory: bool, create: bool = False) -> int:
        try:
            if path.is_symlink():
                raise self._error("link")
            if directory:
                if not path.is_dir():
                    raise self._error("directory")
                stream = None
            else:
                if not create and not stat.S_ISREG(path.lstat().st_mode):
                    raise self._error("regular file")
                stream = path.open("x+b" if create else "rb")
        except OSError as error:
            raise self._error("open") from error
        handle = self.next_handle
        self.next_handle += 1
        self.handles[handle] = {"path": path, "directory": directory, "stream": stream}
        return handle

    def open_directory(self, path: Path, *, share_write: bool = False) -> int:
        return self._hold(Path(path), directory=True)

    def create_directory(self, parent_handle: int, name: str, *, share_write: bool = False) -> int:
        path = self._path(parent_handle, name)
        try:
            path.mkdir()
        except OSError as error:
            raise self._error("create directory") from error
        return self._hold(path, directory=True)

    def open_file(self, path: Path, *, writable: bool = False, allow_rename: bool = False) -> int:
        return self._hold(Path(path), directory=False)

    def create_file(self, parent_handle: int, name: str, *, allow_rename: bool = False) -> int:
        return self._hold(self._path(parent_handle, name), directory=False, create=True)

    def read(self, handle: int, limit: int) -> bytes:
        if type(limit) is not int or limit < 0:
            raise self._error("read bound")
        stream = self.handles[handle]["stream"]
        stream.seek(0)
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise self._error("read bound")
        return data

    def write(self, handle: int, data: bytes) -> None:
        stream = self.handles[handle]["stream"]
        if stream.write(data) != len(data):
            raise self._error("partial write")

    def flush(self, handle: int) -> None:
        stream = self.handles[handle]["stream"]
        if stream is not None:
            stream.flush()
            os.fsync(stream.fileno())

    def identity(self, handle: int) -> dict:
        record = self.handles[handle]
        stream = record["stream"]
        if stream is not None:
            stream.flush()
        info = record["path"].lstat() if stream is None else os.fstat(stream.fileno())
        return {
            "volume": info.st_dev,
            "file_id": info.st_ino,
            "links": 1 if record["directory"] else info.st_nlink,
            "attributes": 0x10 if record["directory"] else 0x80,
            "size": 0 if record["directory"] else info.st_size,
        }

    def volume(self, handle: int) -> dict:
        return {"filesystem": "NTFS", "flags": 0, "max_component": 255}

    def rename_no_replace(self, handle: int, target: Path) -> None:
        record = self.handles[handle]
        stream = record["stream"]
        stream.close()
        try:
            # The model preserves inode identity and refuses existing destinations.
            # This two-step fake is not the Windows publication implementation.
            os.link(record["path"], target)
            record["path"].unlink()
        except OSError as error:
            record["stream"] = record["path"].open("rb")
            raise self._error("no-replace rename") from error
        record["path"] = Path(target)
        record["stream"] = record["path"].open("rb")

    def close(self, handle: int) -> None:
        record = self.handles.pop(handle, None)
        if record is not None and record["stream"] is not None:
            record["stream"].close()
