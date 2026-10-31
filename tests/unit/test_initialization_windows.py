"""Win32 ABI and failure contracts using a bounded in-memory kernel API."""

from __future__ import annotations

import ctypes
import importlib
import os
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiflow.errors import AiflowError

ROOT = Path(__file__).resolve().parents[2]
FAKE_ROOT = ROOT / "synthetic-windows-fixture"
SOURCE = ROOT / "src/aiflow/initialization_windows.py"
try:
    SOURCE.lstat()
except FileNotFoundError:
    pytestmark = pytest.mark.skip(reason="initialization Windows helper is not implemented")
else:
    windows = importlib.import_module("aiflow.initialization_windows")
    if windows.__file__ is None or Path(windows.__file__).resolve() != SOURCE.resolve():
        raise ImportError("initialization Windows helper is not from the tested checkout")


def integer(value: object) -> int:
    return int(getattr(value, "value", value) or 0)


def put_u32(pointer: object, value: int) -> None:
    ctypes.memmove(pointer, struct.pack("<I", value), 4)


class FakeKernel:
    """Only the documented initialization APIs; no host filesystem access."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []
        self.handles: dict[int, dict] = {}
        self.fail: dict[str, int] = {}
        self.last_error = 5
        self.partial_write = False
        self.attributes = 0
        self.links = 1
        self.filesystem = "NTFS"
        self.creation_information = 2
        self.io_status = 0
        self.native_names: list[str] = []
        self.native_roots: list[int] = []
        callbacks = {
            "CreateFileW": self._open,
            "NtCreateFile": self._create,
            "RtlNtStatusToDosError": lambda _status: 183,
            "GetFileInformationByHandle": self._information,
            "GetVolumeInformationByHandleW": self._volume,
            "ReadFile": self._read,
            "WriteFile": self._write,
            "SetFilePointerEx": self._seek,
            "FlushFileBuffers": lambda _handle: 1,
            "SetFileInformationByHandle": lambda *_arguments: 1,
            "CloseHandle": lambda _handle: 1,
        }
        for name, callback in callbacks.items():
            # Plain functions support the .argtypes/.restype assigned by ctypes users.
            setattr(self, name, self._function(name, callback))

    def _function(self, name: str, callback: object):
        def call(*arguments: object):
            self.calls.append((name, arguments))
            if name in self.fail:
                return self.fail[name]
            return callback(*arguments)

        return call

    def _new(self, *, directory: bool) -> int:
        handle = 100 + len(self.handles)
        self.handles[handle] = {
            "directory": directory,
            "content": b"",
            "position": 0,
        }
        return handle

    def _open(self, _path, _access, _sharing, _security, _disposition, flags, _template):
        return self._new(directory=bool(integer(flags) & 0x02000000))

    def _create(self, output, _access, attributes, iosb, _allocation, *_arguments):
        # Verify the Windows x64 ABI independently of Python's host wchar/long sizes.
        assert ctypes.sizeof(attributes._obj) == 48
        raw = ctypes.string_at(attributes, 48)
        assert struct.unpack_from("<I", raw)[0] == 48
        self.native_roots.append(struct.unpack_from("<Q", raw, 8)[0])
        name_pointer = struct.unpack_from("<Q", raw, 16)[0]
        name_record = ctypes.string_at(name_pointer, 16)
        name_length = struct.unpack_from("<H", name_record)[0]
        maximum = struct.unpack_from("<H", name_record, 2)[0]
        assert name_length <= maximum
        assert name_length % 2 == 0
        name_buffer = struct.unpack_from("<Q", name_record, 8)[0]
        self.native_names.append(ctypes.string_at(name_buffer, name_length).decode("utf-16-le"))
        assert struct.unpack_from("<I", raw, 24)[0] == 0x40
        assert ctypes.sizeof(iosb._obj) == 16
        options = integer(_arguments[3])
        handle = self._new(directory=bool(options & 1))
        ctypes.memmove(output, struct.pack("<Q", handle), 8)
        ctypes.memmove(iosb, struct.pack("<QQ", self.io_status, self.creation_information), 16)
        return 0

    def _information(self, handle, output):
        record = self.handles[integer(handle)]
        attributes = (0x10 if record["directory"] else 0x80) | self.attributes
        size = len(record["content"])
        assert ctypes.sizeof(output._obj) == 52
        ctypes.memmove(
            output,
            struct.pack(
                "<13I",
                attributes,
                0,
                0,
                0,
                0,
                0,
                0,
                123,
                size >> 32,
                size & 0xFFFFFFFF,
                self.links,
                0,
                integer(handle),
            ),
            52,
        )
        return 1

    def _volume(self, _handle, _name, _name_size, serial, component, flags, filesystem, size):
        encoded = (self.filesystem + "\0").encode("utf-16-le")
        assert len(encoded) <= integer(size) * 2
        ctypes.memmove(filesystem, encoded, len(encoded))
        if serial:
            put_u32(serial, 123)
        put_u32(component, 255)
        put_u32(flags, 0)
        return 1

    def _seek(self, handle, position, output, method):
        assert integer(method) == 0
        self.handles[integer(handle)]["position"] = integer(position)
        if output:
            ctypes.memmove(output, struct.pack("<q", integer(position)), 8)
        return 1

    def _read(self, handle, output, size, count, _overlapped):
        record = self.handles[integer(handle)]
        offset = record["position"]
        data = record["content"][offset : offset + integer(size)]
        ctypes.memmove(output, data, len(data))
        put_u32(count, len(data))
        record["position"] += len(data)
        return 1

    def _write(self, handle, source, size, count, _overlapped):
        record = self.handles[integer(handle)]
        written = 0 if self.partial_write else integer(size)
        data = ctypes.string_at(source, written)
        offset = record["position"]
        record["content"] = record["content"][:offset] + data
        record["position"] += written
        put_u32(count, written)
        return 1


@pytest.fixture
def kernel(monkeypatch: pytest.MonkeyPatch) -> FakeKernel:
    api = FakeKernel()
    # CPython exposes these only on Windows. The fake path must still be testable on POSIX.
    monkeypatch.setattr(ctypes, "get_last_error", lambda: api.last_error, raising=False)
    monkeypatch.setattr(ctypes, "set_last_error", lambda _value: None, raising=False)
    return api


def test_injected_api_never_loads_native_dlls(kernel: FakeKernel, monkeypatch: pytest.MonkeyPatch):
    def unexpected_dll(*_arguments, **_keywords):
        pytest.fail("a fake kernel tried to load a host Windows DLL")

    monkeypatch.setattr(ctypes, "WinDLL", unexpected_dll, raising=False)
    filesystem = windows.WindowsFilesystem(api=kernel)
    handle = filesystem.open_directory(FAKE_ROOT, share_write=True)
    assert isinstance(handle, int)
    filesystem.close(handle)


@pytest.mark.parametrize("share_write,expected", [(False, 1), (True, 3)])
def test_open_directory_holds_object_without_delete_sharing(
    kernel: FakeKernel, share_write: bool, expected: int
) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    handle = filesystem.open_directory(FAKE_ROOT, share_write=share_write)
    call = next(arguments for name, arguments in kernel.calls if name == "CreateFileW")

    assert integer(call[2]) == expected
    assert integer(call[4]) == 3  # OPEN_EXISTING
    assert integer(call[5]) & 0x00200000  # OPEN_REPARSE_POINT
    assert integer(call[5]) & 0x02000000  # BACKUP_SEMANTICS
    assert filesystem.identity(handle)["file_id"] == handle
    filesystem.close(handle)


def test_atomic_child_creation_returns_the_created_object(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    child = filesystem.create_directory(parent, ".ai", share_write=True)
    file = filesystem.create_file(child, "init-state.json")
    calls = [arguments for name, arguments in kernel.calls if name == "NtCreateFile"]

    assert kernel.native_roots == [parent, child]
    assert kernel.native_names == [".ai", "init-state.json"]
    assert integer(calls[0][7]) == integer(calls[1][7]) == 2  # FILE_CREATE
    assert integer(calls[0][8]) & 1  # FILE_DIRECTORY_FILE
    assert integer(calls[1][8]) & 0x40  # FILE_NON_DIRECTORY_FILE
    for call in calls:
        assert integer(call[1]) & 0x100000  # Explicit SYNCHRONIZE for synchronous NT I/O.
        assert integer(call[8]) & 0x20
        assert integer(call[8]) & 0x200000
        assert not integer(call[6]) & 4
    assert filesystem.identity(child)["file_id"] == child
    assert filesystem.identity(file)["file_id"] == file
    filesystem.close(file)
    filesystem.close(child)
    filesystem.close(parent)


@pytest.mark.parametrize("operation", ["directory", "file"])
def test_invalid_open_handle_is_rejected(kernel: FakeKernel, operation: str) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    kernel.fail["CreateFileW"] = ctypes.c_void_p(-1).value
    with pytest.raises(AiflowError):
        if operation == "directory":
            filesystem.open_directory(FAKE_ROOT)
        else:
            filesystem.open_file(FAKE_ROOT / "file")


@pytest.mark.parametrize(
    "writable,rename", [(False, False), (True, False), (False, True), (True, True)]
)
def test_open_file_access_and_sharing_are_explicit(
    kernel: FakeKernel, writable: bool, rename: bool
) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    handle = filesystem.open_file(FAKE_ROOT / "file", writable=writable, allow_rename=rename)
    call = next(arguments for name, arguments in kernel.calls if name == "CreateFileW")
    desired = integer(call[1])
    assert desired & 0x80000000
    assert bool(desired & 0x40000000) is writable
    assert bool(desired & 0x10000) is rename
    assert integer(call[2]) == 1
    assert integer(call[4]) == 3
    assert integer(call[5]) & 0x200000
    filesystem.close(handle)


@pytest.mark.parametrize("operation", ["directory", "file"])
def test_reparse_objects_are_rejected_after_open(kernel: FakeKernel, operation: str) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    kernel.attributes = 0x400
    with pytest.raises(AiflowError):
        if operation == "directory":
            filesystem.open_directory(FAKE_ROOT)
        else:
            filesystem.open_file(FAKE_ROOT / "file")


@pytest.mark.parametrize(
    "name", ["", ".", "..", "../escape", "child/name", "child\\name", "C:evil", "a\0b"]
)
def test_child_names_cannot_escape_the_held_parent(kernel: FakeKernel, name: str) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    before = len(kernel.calls)
    with pytest.raises(AiflowError):
        filesystem.create_directory(parent, name)
    assert not any(call == "NtCreateFile" for call, _arguments in kernel.calls[before:])
    filesystem.close(parent)


def test_read_write_flush_use_the_original_created_handle(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    handle = filesystem.create_file(parent, "resource.json")
    data = b"same object bytes\n"

    filesystem.write(handle, data)
    filesystem.flush(handle)

    assert filesystem.read(handle, len(data)) == data
    assert filesystem.read(handle, len(data)) == data  # Each read starts at offset zero.
    assert filesystem.identity(handle)["size"] == len(data)
    assert all(
        integer(arguments[0]) == handle
        for name, arguments in kernel.calls
        if name in {"WriteFile", "ReadFile", "FlushFileBuffers"}
    )
    filesystem.close(handle)
    filesystem.close(parent)


def test_read_refuses_more_than_the_bound(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    handle = filesystem.open_file((FAKE_ROOT / "file"))
    kernel.handles[handle]["content"] = b"12345"
    with pytest.raises(AiflowError):
        filesystem.read(handle, 4)
    filesystem.close(handle)


@pytest.mark.parametrize("limit", [-1, True, "4", None])
def test_invalid_read_bounds_do_not_call_native_read(kernel: FakeKernel, limit: object) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    handle = filesystem.open_file((FAKE_ROOT / "file"))
    before = len(kernel.calls)
    with pytest.raises(AiflowError):
        filesystem.read(handle, limit)
    assert not any(name == "ReadFile" for name, _arguments in kernel.calls[before:])
    filesystem.close(handle)


def test_partial_write_is_not_reported_as_success(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    handle = filesystem.create_file(parent, "resource.json")
    kernel.partial_write = True
    with pytest.raises(AiflowError):
        filesystem.write(handle, b"required complete contents")
    filesystem.close(handle)
    filesystem.close(parent)


@pytest.mark.parametrize(
    "api_name",
    ["ReadFile", "WriteFile", "SetFilePointerEx", "FlushFileBuffers", "GetFileInformationByHandle"],
)
def test_native_io_failure_never_becomes_success(kernel: FakeKernel, api_name: str) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    handle = filesystem.create_file(parent, "resource.json")
    kernel.fail[api_name] = 0
    operations = {
        "ReadFile": lambda: filesystem.read(handle, 4),
        "WriteFile": lambda: filesystem.write(handle, b"data"),
        "SetFilePointerEx": lambda: filesystem.read(handle, 4),
        "FlushFileBuffers": lambda: filesystem.flush(handle),
        "GetFileInformationByHandle": lambda: filesystem.identity(handle),
    }
    with pytest.raises(AiflowError):
        operations[api_name]()
    kernel.fail.clear()
    filesystem.close(handle)
    filesystem.close(parent)


def test_nt_collision_is_translated_and_never_retried_as_open_existing(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    kernel.fail["NtCreateFile"] = 0xC0000035
    before = len(kernel.calls)
    with pytest.raises(AiflowError):
        filesystem.create_directory(parent, ".ai", share_write=True)
    calls = kernel.calls[before:]
    assert [name for name, _arguments in calls].count("NtCreateFile") == 1
    assert any(name == "RtlNtStatusToDosError" for name, _arguments in calls)
    assert not any(name == "CreateFileW" for name, _arguments in calls)
    kernel.fail.clear()
    filesystem.close(parent)


@pytest.mark.parametrize("status", [0x103, 0x40000000, 0x80000005, 0xC0000022])
def test_nt_nonzero_status_is_not_synchronous_creation_success(
    kernel: FakeKernel, status: int
) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    kernel.fail["NtCreateFile"] = status
    with pytest.raises(AiflowError):
        filesystem.create_directory(parent, ".ai", share_write=True)
    kernel.fail.clear()
    filesystem.close(parent)


@pytest.mark.parametrize("information", [0, 1, 3, 99])
def test_nt_success_requires_file_created_information(kernel: FakeKernel, information: int) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    kernel.creation_information = information
    with pytest.raises(AiflowError):
        filesystem.create_directory(parent, ".ai", share_write=True)
    assert any(name == "CloseHandle" for name, _arguments in kernel.calls)
    filesystem.close(parent)


def test_volume_reports_actual_filesystem_facts(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    handle = filesystem.open_directory(FAKE_ROOT, share_write=True)
    facts = filesystem.volume(handle)
    assert facts["filesystem"] == "NTFS"
    assert facts["max_component"] == 255
    assert facts["flags"] == 0
    kernel.fail["GetVolumeInformationByHandleW"] = 0
    with pytest.raises(AiflowError):
        filesystem.volume(handle)
    kernel.fail.clear()
    filesystem.close(handle)


@pytest.mark.parametrize("padding", [0, 1, 2, 3], ids=["align-0", "align-1", "align-2", "align-3"])
def test_identity_publication_uses_no_replace_absolute_utf16_name(
    kernel: FakeKernel, padding: int
) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    handle = filesystem.create_file(parent, ".repository-id.pending", allow_rename=True)
    target = FAKE_ROOT / ".ai" / ("repository-id" + "x" * padding + "😀")

    filesystem.rename_no_replace(handle, target)

    call = next(
        arguments for name, arguments in kernel.calls if name == "SetFileInformationByHandle"
    )
    assert integer(call[0]) == handle
    assert integer(call[1]) == 3  # FileRenameInfo
    raw = ctypes.string_at(call[2], integer(call[3]))
    assert struct.unpack_from("<I", raw)[0] == 0
    assert struct.unpack_from("<Q", raw, 8)[0] == 0
    length = struct.unpack_from("<I", raw, 16)[0]
    assert length == len(str(target).encode("utf-16-le"))
    name = raw[20 : 20 + length].decode("utf-16-le")
    assert name.replace("\\", "/") == str(target).replace("\\", "/")
    assert raw[20 + length : 20 + length + 2] == b"\0\0"
    create = next(arguments for name, arguments in kernel.calls if name == "NtCreateFile")
    assert integer(create[1]) & 0x10000  # DELETE on the original pending object.
    kernel.fail["SetFileInformationByHandle"] = 0
    with pytest.raises(AiflowError):
        filesystem.rename_no_replace(handle, target)
    kernel.fail.clear()
    filesystem.close(handle)
    filesystem.close(parent)


def test_publication_rejects_relative_names_before_native_rename(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT, share_write=True)
    handle = filesystem.create_file(parent, ".repository-id.pending", allow_rename=True)
    before = len(kernel.calls)
    with pytest.raises(AiflowError):
        filesystem.rename_no_replace(handle, Path("relative/repository-id"))
    assert not any(
        name == "SetFileInformationByHandle" for name, _arguments in kernel.calls[before:]
    )
    filesystem.close(handle)
    filesystem.close(parent)


def test_unknown_close_result_is_an_error(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    handle = filesystem.open_file((FAKE_ROOT / "file"))
    kernel.fail["CloseHandle"] = 0
    with pytest.raises(AiflowError):
        filesystem.close(handle)


def test_default_api_rejects_unsupported_platform_without_loading_dlls() -> None:
    if os.name == "nt":
        pytest.skip("the unsupported default path is exercised on POSIX")
    with pytest.raises(AiflowError):
        windows.WindowsFilesystem()


def native_environment(monkeypatch: pytest.MonkeyPatch, kernel: FakeKernel, loader) -> None:
    """Replace only this module's references, never the interpreter's os.name."""
    proxy = SimpleNamespace(**{**vars(ctypes), "WinDLL": loader})
    monkeypatch.setattr(windows, "ctypes", proxy)
    monkeypatch.setattr(windows, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        windows,
        "sys",
        SimpleNamespace(implementation=SimpleNamespace(name="cpython"), version_info=(3, 11)),
    )


def test_default_loader_binds_only_the_two_expected_dlls(
    kernel: FakeKernel, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded = []

    def load(name, **keywords):
        loaded.append((name, keywords))
        return kernel

    native_environment(monkeypatch, kernel, load)
    filesystem = windows.WindowsFilesystem()
    handle = filesystem.open_directory(FAKE_ROOT)
    filesystem.close(handle)
    assert loaded == [("kernel32", {"use_last_error": True}), ("ntdll", {"use_last_error": True})]


def test_default_loader_failure_is_unsupported(
    kernel: FakeKernel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(*_arguments, **_keywords):
        raise OSError("synthetic missing Windows API")

    native_environment(monkeypatch, kernel, unavailable)
    with pytest.raises(AiflowError) as error:
        windows.WindowsFilesystem()
    assert error.value.code == "INITIALIZATION_UNSUPPORTED"


@pytest.mark.parametrize("reason", ["os", "interpreter", "version"])
def test_default_api_checks_runtime_before_loading_any_dll(
    kernel: FakeKernel, monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    def unexpected(*_arguments, **_keywords):
        pytest.fail("unsupported runtime attempted to load a DLL")

    native_environment(monkeypatch, kernel, unexpected)
    if reason == "os":
        monkeypatch.setattr(windows, "os", SimpleNamespace(name="posix"))
    else:
        monkeypatch.setattr(
            windows,
            "sys",
            SimpleNamespace(
                implementation=SimpleNamespace(
                    name="pypy" if reason == "interpreter" else "cpython"
                ),
                version_info=(3, 12) if reason == "version" else (3, 11),
            ),
        )
    with pytest.raises(AiflowError):
        windows.WindowsFilesystem()


def test_unknown_abi_is_rejected_before_api_use(
    kernel: FakeKernel, monkeypatch: pytest.MonkeyPatch
) -> None:
    proxy = SimpleNamespace(**{**vars(ctypes), "sizeof": lambda _value: 4})
    monkeypatch.setattr(windows, "ctypes", proxy)
    with pytest.raises(AiflowError):
        windows.WindowsFilesystem(api=kernel)
    assert not kernel.calls


@pytest.mark.parametrize(
    "name",
    ["\ud800", "x" * 256, "😀" * 128, "CON.txt", "aux", "trailing.", "trailing "],
    ids=["surrogate", "too-long", "utf16-too-long", "device-extension", "device", "dot", "space"],
)
def test_child_name_encoding_and_windows_aliases_are_rejected(
    kernel: FakeKernel, name: str
) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    parent = filesystem.open_directory(FAKE_ROOT)
    with pytest.raises(AiflowError):
        filesystem.create_file(parent, name)
    filesystem.close(parent)


def test_absolute_name_rejects_invalid_utf16_without_opening(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    with pytest.raises(AiflowError):
        filesystem.open_file(FAKE_ROOT / "\ud800")
    assert not kernel.calls


@pytest.mark.parametrize("handle", [None, True, 0, 999])
def test_unknown_handles_cannot_reach_kernel_io(kernel: FakeKernel, handle: object) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    with pytest.raises(AiflowError):
        filesystem.identity(handle)
    assert not kernel.calls


def test_only_directory_handles_can_own_new_children(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    file = filesystem.open_file(FAKE_ROOT / "file")
    with pytest.raises(AiflowError):
        filesystem.create_file(file, "child")
    filesystem.close(file)


def test_kernel_cannot_claim_more_read_bytes_than_the_buffer(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    file = filesystem.open_file(FAKE_ROOT / "file")

    def oversized_count(_handle, _buffer, size, count, _overlapped):
        put_u32(count, integer(size) + 1)
        return 1

    kernel.ReadFile = oversized_count
    with pytest.raises(AiflowError):
        filesystem.read(file, 4)
    filesystem.close(file)


def test_opened_files_cannot_be_overwritten_even_with_writable_access(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    file = filesystem.open_file(FAKE_ROOT / "existing", writable=True)
    kernel.handles[file]["content"] = b"owner data"
    with pytest.raises(AiflowError):
        filesystem.write(file, b"replacement")
    assert kernel.handles[file]["content"] == b"owner data"
    filesystem.close(file)


def test_new_file_gets_only_one_write_attempt(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    root = filesystem.open_directory(FAKE_ROOT)
    file = filesystem.create_file(root, "new")
    filesystem.write(file, b"first")
    with pytest.raises(AiflowError):
        filesystem.write(file, b"second")
    assert kernel.handles[file]["content"] == b"first"
    filesystem.close(file)
    filesystem.close(root)


def test_rename_requires_the_original_rename_capable_handle(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    file = filesystem.open_file(FAKE_ROOT / "not-owned-for-rename")
    with pytest.raises(AiflowError):
        filesystem.rename_no_replace(file, FAKE_ROOT / "destination")
    filesystem.close(file)


def test_closed_handles_are_not_closed_again_or_reused(kernel: FakeKernel) -> None:
    filesystem = windows.WindowsFilesystem(api=kernel)
    file = filesystem.open_file(FAKE_ROOT / "file")
    filesystem.close(file)
    count = sum(name == "CloseHandle" for name, _arguments in kernel.calls)
    with pytest.raises(AiflowError):
        filesystem.close(file)
    assert sum(name == "CloseHandle" for name, _arguments in kernel.calls) == count
