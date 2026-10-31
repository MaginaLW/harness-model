"""Narrow Windows object operations for non-overwriting initialization.

Creation returns the new object's handle directly. Sharing protects held objects;
it is not a sandbox against malicious code running as the same user.
"""

from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from aiflow.errors import AiflowError

_U32 = ctypes.c_uint32
_U16 = ctypes.c_uint16
_PTR = ctypes.c_void_p
_SYNCHRONIZE = 0x00100000
_DIRECTORY_ACCESS = _SYNCHRONIZE | 0x01 | 0x20 | 0x80
_FILE_READ = 0x80000000
_FILE_WRITE = 0x40000000
_DELETE = 0x00010000
_REPARSE = 0x400
_DIRECTORY = 0x10
_MAX_FILE_BYTES = 1024 * 1024
_INVALID_HANDLE = _PTR(-1).value


class _UnicodeString(ctypes.Structure):
    _fields_ = [("length", _U16), ("maximum_length", _U16), ("buffer", _PTR)]


class _ObjectAttributes(ctypes.Structure):
    _fields_ = [
        ("length", _U32),
        ("root", _PTR),
        ("name", ctypes.POINTER(_UnicodeString)),
        ("attributes", _U32),
        ("security", _PTR),
        ("quality", _PTR),
    ]


class _StatusPointer(ctypes.Union):
    _fields_ = [("status", ctypes.c_int32), ("pointer", _PTR)]


class _IoStatusBlock(ctypes.Structure):
    _fields_ = [("status", _StatusPointer), ("information", ctypes.c_size_t)]


class _HandleInformation(ctypes.Structure):
    _fields_ = [
        (name, _U32)
        for name in (
            "attributes",
            "creation_low",
            "creation_high",
            "access_low",
            "access_high",
            "write_low",
            "write_high",
            "volume",
            "size_high",
            "size_low",
            "links",
            "index_high",
            "index_low",
        )
    ]


@dataclass
class _OwnedHandle:
    directory: bool
    writable: bool = False
    allow_rename: bool = False
    created: bool = False
    write_started: bool = False


def _invalid() -> AiflowError:
    return AiflowError(
        "Initialization Windows operation has invalid input",
        code="INITIALIZATION_WINDOWS_INVALID",
    )


def _absolute_name(path: Path) -> bytes:
    if not isinstance(path, Path) or not path.is_absolute() or "\0" in str(path):
        raise _invalid()
    try:
        return str(path).encode("utf-16-le")
    except UnicodeError as error:
        raise _invalid() from error


def _child_name(name: str) -> bytes:
    devices = {"con", "prn", "aux", "nul", "conin$", "conout$"}
    devices.update(f"{prefix}{digit}" for prefix in ("com", "lpt") for digit in "123456789¹²³")
    if (
        not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or name.endswith((".", " "))
        or any(ord(char) < 32 or char in '/\\:\0*?"<>|' for char in name)
        or name.split(".", 1)[0].rstrip(" ").casefold() in devices
    ):
        raise _invalid()
    try:
        encoded = name.encode("utf-16-le")
    except UnicodeError as error:
        raise _invalid() from error
    if len(encoded) > 510:
        raise _invalid()
    return encoded


class WindowsFilesystem:
    """Only initialization's fixed handle operations, with an injectable flat API."""

    def __init__(self, api: Any = None) -> None:
        if ctypes.sizeof(_PTR) != 8 or (
            ctypes.sizeof(_UnicodeString),
            ctypes.sizeof(_ObjectAttributes),
            ctypes.sizeof(_IoStatusBlock),
        ) != (16, 48, 16):
            raise AiflowError("Windows x64 ABI is required", code="INITIALIZATION_UNSUPPORTED")
        if api is None:
            if (
                os.name != "nt"
                or sys.implementation.name != "cpython"
                or sys.version_info[:2] != (3, 11)
            ):
                raise AiflowError(
                    "Initialization requires Windows x64 and CPython 3.11",
                    code="INITIALIZATION_UNSUPPORTED",
                )
            try:
                kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
                native = getattr(ctypes, "WinDLL")("ntdll", use_last_error=True)
            except OSError as error:
                raise AiflowError(
                    "Initialization Windows APIs are unavailable",
                    code="INITIALIZATION_UNSUPPORTED",
                ) from error
            api = SimpleNamespace(
                **{
                    name: getattr(
                        native if name in {"NtCreateFile", "RtlNtStatusToDosError"} else kernel,
                        name,
                    )
                    for name in (
                        "CreateFileW",
                        "NtCreateFile",
                        "RtlNtStatusToDosError",
                        "ReadFile",
                        "WriteFile",
                        "SetFilePointerEx",
                        "FlushFileBuffers",
                        "GetFileInformationByHandle",
                        "GetVolumeInformationByHandleW",
                        "SetFileInformationByHandle",
                        "CloseHandle",
                    )
                }
            )
        self._api = api
        self._handles: dict[int, _OwnedHandle] = {}
        signatures = {
            "CreateFileW": (_PTR, [_PTR, _U32, _U32, _PTR, _U32, _U32, _PTR]),
            "NtCreateFile": (
                ctypes.c_int32,
                [
                    ctypes.POINTER(_PTR),
                    _U32,
                    ctypes.POINTER(_ObjectAttributes),
                    ctypes.POINTER(_IoStatusBlock),
                    _PTR,
                    _U32,
                    _U32,
                    _U32,
                    _U32,
                    _PTR,
                    _U32,
                ],
            ),
            "RtlNtStatusToDosError": (_U32, [ctypes.c_int32]),
            "ReadFile": (ctypes.c_int32, [_PTR, _PTR, _U32, ctypes.POINTER(_U32), _PTR]),
            "WriteFile": (ctypes.c_int32, [_PTR, _PTR, _U32, ctypes.POINTER(_U32), _PTR]),
            "SetFilePointerEx": (ctypes.c_int32, [_PTR, ctypes.c_int64, _PTR, _U32]),
            "FlushFileBuffers": (ctypes.c_int32, [_PTR]),
            "GetFileInformationByHandle": (
                ctypes.c_int32,
                [_PTR, ctypes.POINTER(_HandleInformation)],
            ),
            "GetVolumeInformationByHandleW": (
                ctypes.c_int32,
                [
                    _PTR,
                    _PTR,
                    _U32,
                    ctypes.POINTER(_U32),
                    ctypes.POINTER(_U32),
                    ctypes.POINTER(_U32),
                    _PTR,
                    _U32,
                ],
            ),
            "SetFileInformationByHandle": (ctypes.c_int32, [_PTR, ctypes.c_int32, _PTR, _U32]),
            "CloseHandle": (ctypes.c_int32, [_PTR]),
        }
        for name, (result, arguments) in signatures.items():
            function = getattr(api, name)
            function.restype, function.argtypes = result, arguments

    def _failed(self, operation: str, winerror: int | None = None) -> AiflowError:
        if winerror is None:
            winerror = int(getattr(ctypes, "get_last_error")())
        return AiflowError(
            "Initialization Windows operation failed",
            code="INITIALIZATION_WINDOWS_FAILED",
            details={"operation": operation, "winerror": winerror & 0xFFFFFFFF},
        )

    def _owned(self, handle: int) -> _OwnedHandle:
        if not isinstance(handle, int) or isinstance(handle, bool) or handle not in self._handles:
            raise _invalid()
        return self._handles[handle]

    def _register(self, handle: int | None, ownership: _OwnedHandle) -> int:
        if handle in {None, 0, _INVALID_HANDLE}:
            raise self._failed("CreateFileW")
        assert handle is not None
        self._handles[handle] = ownership
        try:
            facts = self.identity(handle)
            if (
                facts["attributes"] & _REPARSE
                or bool(facts["attributes"] & _DIRECTORY) is not ownership.directory
                or (not ownership.directory and facts["links"] != 1)
            ):
                raise _invalid()
        except AiflowError:
            self.close(handle)
            raise
        return handle

    def _pin_ancestor(self, path: Path) -> int:
        # TRAVERSE participates in sharing protection; attributes-only does not.
        buffer = ctypes.create_string_buffer(_absolute_name(path) + b"\0\0")
        handle = self._api.CreateFileW(buffer, 0xA0, 3, None, 3, 0x02200000, None)
        return self._register(handle, _OwnedHandle(directory=True))

    def open_directory(self, path: Path, *, share_write: bool = False) -> int:
        buffer = ctypes.create_string_buffer(_absolute_name(path) + b"\0\0")
        handle = self._api.CreateFileW(
            buffer, _DIRECTORY_ACCESS, 3 if share_write else 1, None, 3, 0x02200000, None
        )
        return self._register(handle, _OwnedHandle(directory=True))

    def open_file(self, path: Path, *, writable: bool = False, allow_rename: bool = False) -> int:
        buffer = ctypes.create_string_buffer(_absolute_name(path) + b"\0\0")
        access = _FILE_READ | (_FILE_WRITE if writable else 0) | (_DELETE if allow_rename else 0)
        handle = self._api.CreateFileW(buffer, access, 1, None, 3, 0x00200000, None)
        return self._register(handle, _OwnedHandle(False, writable, allow_rename))

    def _create(self, parent: int, name: str, ownership: _OwnedHandle, share: int) -> int:
        if not self._owned(parent).directory:
            raise _invalid()
        encoded = _child_name(name)
        buffer = ctypes.create_string_buffer(encoded + b"\0\0")
        string = _UnicodeString(len(encoded), len(encoded) + 2, ctypes.cast(buffer, _PTR))
        attributes = _ObjectAttributes(
            ctypes.sizeof(_ObjectAttributes), parent, ctypes.pointer(string), 0x40, None, None
        )
        iosb, handle = _IoStatusBlock(), _PTR()
        access = (
            _DIRECTORY_ACCESS
            if ownership.directory
            else (
                _FILE_READ | _FILE_WRITE | _SYNCHRONIZE | (_DELETE if ownership.allow_rename else 0)
            )
        )
        options = 0x00200000 | 0x20 | (1 if ownership.directory else 0x40)
        status = int(
            self._api.NtCreateFile(
                ctypes.byref(handle),
                access,
                ctypes.byref(attributes),
                ctypes.byref(iosb),
                None,
                0x80,
                share,
                2,
                options,
                None,
                0,
            )
        )
        if status != 0:
            code = int(self._api.RtlNtStatusToDosError(ctypes.c_int32(status).value))
            raise self._failed("NtCreateFile", code)
        if iosb.status.status != 0 or iosb.information != 2:
            created = handle.value
            if created is not None and created not in {0, _INVALID_HANDLE}:
                self._handles[created] = ownership
                self.close(created)
            raise self._failed("NtCreateFile", 87)
        return self._register(handle.value, ownership)

    def create_directory(self, parent_handle: int, name: str, *, share_write: bool = False) -> int:
        return self._create(
            parent_handle, name, _OwnedHandle(directory=True, created=True), 3 if share_write else 1
        )

    def create_file(self, parent_handle: int, name: str, *, allow_rename: bool = False) -> int:
        return self._create(parent_handle, name, _OwnedHandle(False, True, allow_rename, True), 1)

    def _seek_start(self, handle: int) -> None:
        if not self._api.SetFilePointerEx(handle, 0, None, 0):
            raise self._failed("SetFilePointerEx")

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
            buffer, count = ctypes.create_string_buffer(amount), _U32()
            if not self._api.ReadFile(handle, buffer, amount, ctypes.byref(count), None):
                raise self._failed("ReadFile")
            if count.value > amount:
                raise self._failed("ReadFile", 87)
            if count.value == 0:
                return bytes(data)
            data.extend(buffer.raw[: count.value])
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
            buffer, count = ctypes.create_string_buffer(chunk), _U32()
            if not self._api.WriteFile(handle, buffer, len(chunk), ctypes.byref(count), None):
                raise self._failed("WriteFile")
            if count.value != len(chunk):
                raise self._failed("WriteFile", 29)

    def flush(self, handle: int) -> None:
        self._owned(handle)
        if not self._api.FlushFileBuffers(handle):
            raise self._failed("FlushFileBuffers")

    def identity(self, handle: int) -> dict[str, int]:
        self._owned(handle)
        info = _HandleInformation()
        if not self._api.GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise self._failed("GetFileInformationByHandle")
        return {
            "volume": int(info.volume),
            "file_id": (int(info.index_high) << 32) | info.index_low,
            "links": int(info.links),
            "attributes": int(info.attributes),
            "size": (int(info.size_high) << 32) | info.size_low,
        }

    def volume(self, handle: int) -> dict[str, str | int]:
        self._owned(handle)
        name, filesystem = (_U16 * 256)(), (_U16 * 256)()
        serial, component, flags = _U32(), _U32(), _U32()
        if not self._api.GetVolumeInformationByHandleW(
            handle,
            name,
            256,
            ctypes.byref(serial),
            ctypes.byref(component),
            ctypes.byref(flags),
            filesystem,
            256,
        ):
            raise self._failed("GetVolumeInformationByHandleW")
        try:
            label = bytes(filesystem).decode("utf-16-le").split("\0", 1)[0]
        except UnicodeError as error:
            raise _invalid() from error
        return {
            "filesystem": label,
            "flags": int(flags.value),
            "max_component": int(component.value),
        }

    def rename_no_replace(self, handle: int, target: Path) -> None:
        if not self._owned(handle).allow_rename:
            raise _invalid()
        encoded = _absolute_name(target)

        class Rename(ctypes.Structure):
            _fields_ = [
                ("flags", _U32),
                ("root", _PTR),
                ("length", _U32),
                ("name", ctypes.c_ubyte * (len(encoded) + 2)),
            ]

        if Rename.name.offset != 20:
            raise _invalid()
        # FILE_RENAME_INFO.FileName is NUL-terminated; FileNameLength excludes it.
        record = Rename(
            0,
            None,
            len(encoded),
            (ctypes.c_ubyte * (len(encoded) + 2)).from_buffer_copy(encoded + b"\0\0"),
        )
        if not self._api.SetFileInformationByHandle(
            handle, 3, ctypes.byref(record), ctypes.sizeof(record)
        ):
            raise self._failed("SetFileInformationByHandle")

    def close(self, handle: int) -> None:
        self._owned(handle)
        if not self._api.CloseHandle(handle):
            raise self._failed("CloseHandle")
        del self._handles[handle]
