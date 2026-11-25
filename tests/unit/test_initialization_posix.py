"""POSIX handle, atomicity, and failure contracts plus POSIX real-FS integration."""

from __future__ import annotations

import errno
import importlib
import json
import os
import stat
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from initialization_helpers import fixture_git as git
from initialization_helpers import snapshot_tree as tree

from aiflow.errors import AiflowError
from aiflow.resource_bundle import RESOURCE_KINDS, build_bundle

ROOT = Path(__file__).resolve().parents[2]
FAKE_ROOT = ROOT / "synthetic-posix-fixture"
SOURCE = ROOT / "src/aiflow/initialization_posix.py"
try:
    SOURCE.lstat()
except FileNotFoundError:
    pytestmark = pytest.mark.skip(reason="initialization POSIX helper is not implemented")
else:
    posix_fs = importlib.import_module("aiflow.initialization_posix")
    if posix_fs.__file__ is None or Path(posix_fs.__file__).resolve() != SOURCE.resolve():
        raise ImportError("initialization POSIX helper is not from the tested checkout")


class FakePosixApi:
    """In-memory POSIX fd/inode simulator with no host filesystem side effects."""

    O_NOFOLLOW = 0x20000
    O_DIRECTORY = 0x10000
    O_CLOEXEC = 0x80000
    O_RDONLY = 0x0
    O_RDWR = 0x2
    O_CREAT = 0x40
    O_EXCL = 0x80

    def __init__(self, *, include_fstatvfs: bool = True) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.inodes: dict[int, dict[str, Any]] = {}
        self.fds: dict[int, dict[str, Any]] = {}
        self.fail: dict[str, OSError] = {}
        self.next_inode = 100
        self.next_fd = 10
        self.partial_write = False
        self.override_mode: int | None = None
        self.override_links: int | None = None
        self.override_after_link_links: int | None = None
        self.override_after_link_inode: int | None = None
        self.bad_read_return: Any = None
        self.bad_open_return: Any = None
        self.namemax = 255
        self.fs_flags = 4096
        if include_fstatvfs:
            self.fstatvfs = self._wrap("fstatvfs", self._fstatvfs)

        for name, func in (
            ("open", self._open),
            ("mkdir", self._mkdir),
            ("link", self._link),
            ("unlink", self._unlink),
            ("fstat", self._fstat),
            ("fsync", self._fsync),
            ("lseek", self._lseek),
            ("read", self._read),
            ("write", self._write),
            ("close", self._close),
        ):
            setattr(self, name, self._wrap(name, func))

        # Seed FAKE_ROOT and its ancestors in memory.
        self._seed_path(FAKE_ROOT)

    def _wrap(self, name: str, func: Any) -> Any:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, args, kwargs))
            if name in self.fail:
                raise self.fail[name]
            return func(*args, **kwargs)

        return wrapped

    def _alloc_inode(self, mode: int, *, content: bytes = b"") -> int:
        inode = self.next_inode
        self.next_inode += 1
        self.inodes[inode] = {
            "mode": mode,
            "links": 2 if stat.S_ISDIR(mode) else 1,
            "content": content,
            "children": {} if stat.S_ISDIR(mode) else None,
        }
        return inode

    def _seed_path(self, path: Path) -> int:
        parts = list(path.parts)
        root_key = parts[0]
        if not hasattr(self, "_root_inode"):
            self._root_inode = self._alloc_inode(stat.S_IFDIR | 0o755)
        current = self._root_inode
        for part in parts[1:]:
            children = self.inodes[current]["children"]
            if part not in children:
                children[part] = self._alloc_inode(stat.S_IFDIR | 0o755)
            current = children[part]
        _ = root_key
        return current

    def seed_file(self, path: Path, content: bytes = b"", *, mode: int | None = None) -> int:
        parent_ino = self._seed_path(path.parent)
        inode = self._alloc_inode((stat.S_IFREG | 0o644) if mode is None else mode, content=content)
        self.inodes[parent_ino]["children"][path.name] = inode
        return inode

    def seed_symlink(self, path: Path) -> int:
        parent_ino = self._seed_path(path.parent)
        inode = self._alloc_inode(stat.S_IFLNK | 0o777, content=b"target")
        self.inodes[parent_ino]["children"][path.name] = inode
        return inode

    def _resolve_path(self, path_str: str) -> tuple[int, str, int]:
        path = Path(path_str)
        parts = list(path.parts)
        if not parts:
            raise FileNotFoundError(errno.ENOENT, "empty path")
        current = self._root_inode
        if len(parts) == 1:
            return current, parts[0], current
        for part in parts[1:-1]:
            children = self.inodes[current]["children"]
            if children is None or part not in children:
                raise FileNotFoundError(errno.ENOENT, "missing parent", part)
            current = children[part]
            if stat.S_ISLNK(self.inodes[current]["mode"]):
                raise OSError(errno.ELOOP, "symlink in path")
        children = self.inodes[current]["children"]
        leaf = parts[-1]
        if children is None or leaf not in children:
            raise FileNotFoundError(errno.ENOENT, "missing", path_str)
        return current, leaf, children[leaf]

    def _alloc_fd(self, inode: int, flags: int) -> int:
        fd = self.next_fd
        self.next_fd += 1
        self.fds[fd] = {"inode": inode, "flags": flags, "pos": 0}
        return fd

    def _open(self, path: str, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        _ = mode
        if self.bad_open_return is not None:
            return self.bad_open_return
        if dir_fd is not None:
            if dir_fd not in self.fds:
                raise OSError(errno.EBADF, "bad dir_fd")
            parent_ino = self.fds[dir_fd]["inode"]
            children = self.inodes[parent_ino]["children"]
            if children is None:
                raise NotADirectoryError(errno.ENOTDIR, "not a dir")
            if flags & self.O_CREAT:
                if path in children:
                    if flags & self.O_EXCL:
                        raise FileExistsError(errno.EEXIST, "exists", path)
                    inode = children[path]
                else:
                    inode = self._alloc_inode(stat.S_IFREG | 0o644)
                    children[path] = inode
            else:
                if path not in children:
                    raise FileNotFoundError(errno.ENOENT, "missing", path)
                inode = children[path]
        else:
            _, _, inode = self._resolve_path(path)
        node = self.inodes[inode]
        if (flags & self.O_NOFOLLOW) and stat.S_ISLNK(node["mode"]):
            raise OSError(errno.ELOOP, "symlink")
        if (flags & self.O_DIRECTORY) and not stat.S_ISDIR(node["mode"]):
            raise NotADirectoryError(errno.ENOTDIR, "not a directory")
        return self._alloc_fd(inode, flags)

    def _mkdir(self, path: str, mode: int = 0o777, *, dir_fd: int | None = None) -> None:
        _ = mode
        assert dir_fd is not None
        parent_ino = self.fds[dir_fd]["inode"]
        children = self.inodes[parent_ino]["children"]
        if children is None:
            raise NotADirectoryError(errno.ENOTDIR, "not a dir")
        if path in children:
            raise FileExistsError(errno.EEXIST, "exists", path)
        children[path] = self._alloc_inode(stat.S_IFDIR | 0o755)

    def _link(
        self,
        src: str,
        dst: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        assert src_dir_fd is not None and dst_dir_fd is not None
        src_children = self.inodes[self.fds[src_dir_fd]["inode"]]["children"]
        dst_children = self.inodes[self.fds[dst_dir_fd]["inode"]]["children"]
        if src not in src_children:
            raise FileNotFoundError(errno.ENOENT, "missing", src)
        if dst in dst_children:
            raise FileExistsError(errno.EEXIST, "target exists", dst)
        inode = src_children[src]
        dst_children[dst] = inode
        self.inodes[inode]["links"] += 1
        if self.override_after_link_links is not None:
            self.inodes[inode]["links"] = self.override_after_link_links + 1
        if self.override_after_link_inode is not None:
            for fd_rec in self.fds.values():
                if fd_rec["inode"] == inode:
                    fd_rec["inode"] = self.override_after_link_inode
                    self.inodes[self.override_after_link_inode] = {
                        "mode": stat.S_IFREG | 0o644,
                        "links": 1,
                        "content": b"",
                        "children": None,
                    }

    def _unlink(self, path: str, *, dir_fd: int | None = None) -> None:
        assert dir_fd is not None
        children = self.inodes[self.fds[dir_fd]["inode"]]["children"]
        if path not in children:
            raise FileNotFoundError(errno.ENOENT, "missing", path)
        inode = children.pop(path)
        self.inodes[inode]["links"] -= 1

    def _fstat(self, fd: int) -> SimpleNamespace:
        if fd not in self.fds:
            raise OSError(errno.EBADF, "bad fd")
        inode = self.fds[fd]["inode"]
        node = self.inodes[inode]
        mode = self.override_mode if self.override_mode is not None else node["mode"]
        links = self.override_links if self.override_links is not None else node["links"]
        return SimpleNamespace(
            st_mode=mode,
            st_dev=777,
            st_ino=inode,
            st_nlink=links,
            st_size=len(node["content"]),
        )

    def _fstatvfs(self, fd: int) -> SimpleNamespace:
        if fd not in self.fds:
            raise OSError(errno.EBADF, "bad fd")
        return SimpleNamespace(f_flag=self.fs_flags, f_namemax=self.namemax)

    def _fsync(self, fd: int) -> None:
        if fd not in self.fds:
            raise OSError(errno.EBADF, "bad fd")

    def _lseek(self, fd: int, pos: int, how: int) -> int:
        assert how == 0
        self.fds[fd]["pos"] = pos
        return pos

    def _read(self, fd: int, amount: int) -> bytes:
        if self.bad_read_return is not None:
            return self.bad_read_return
        rec = self.fds[fd]
        node = self.inodes[rec["inode"]]
        pos = rec["pos"]
        chunk = node["content"][pos : pos + amount]
        rec["pos"] += len(chunk)
        return chunk

    def _write(self, fd: int, data: bytes) -> int:
        rec = self.fds[fd]
        node = self.inodes[rec["inode"]]
        if self.partial_write:
            written = max(0, len(data) - 1)
        else:
            written = len(data)
        pos = rec["pos"]
        node["content"] = node["content"][:pos] + data[:written] + node["content"][pos + written :]
        rec["pos"] += written
        return written

    def _close(self, fd: int) -> None:
        if fd not in self.fds:
            raise OSError(errno.EBADF, "bad fd")
        del self.fds[fd]


@pytest.fixture
def api() -> FakePosixApi:
    return FakePosixApi()


def test_default_api_rejects_unsupported_platform_without_touching_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(posix_fs, "os", SimpleNamespace(name="nt"))
    with pytest.raises(AiflowError) as error:
        posix_fs.PosixFilesystem()
    assert error.value.code == "INITIALIZATION_UNSUPPORTED"


@pytest.mark.parametrize("reason", ["os", "implementation", "version", "missing_symbol"])
def test_default_api_checks_runtime_and_required_os_symbols(
    api: FakePosixApi, monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    os_attrs = {name: getattr(api, name) for name in posix_fs._REQUIRED_API}
    os_attrs["name"] = "nt" if reason == "os" else "posix"
    os_attrs["fstatvfs"] = api.fstatvfs
    if reason == "missing_symbol":
        del os_attrs["O_NOFOLLOW"]
    monkeypatch.setattr(posix_fs, "os", SimpleNamespace(**os_attrs))
    monkeypatch.setattr(
        posix_fs,
        "sys",
        SimpleNamespace(
            implementation=SimpleNamespace(
                name="pypy" if reason == "implementation" else "cpython"
            ),
            version_info=(3, 10, 9) if reason == "version" else (3, 11, 5),
        ),
    )
    with pytest.raises(AiflowError) as error:
        posix_fs.PosixFilesystem()
    assert error.value.code == "INITIALIZATION_UNSUPPORTED"


def test_default_api_binds_posix_os_namespace(
    api: FakePosixApi, monkeypatch: pytest.MonkeyPatch
) -> None:
    os_attrs = {name: getattr(api, name) for name in posix_fs._REQUIRED_API}
    os_attrs["name"] = "posix"
    os_attrs["fstatvfs"] = api.fstatvfs
    monkeypatch.setattr(posix_fs, "os", SimpleNamespace(**os_attrs))
    monkeypatch.setattr(
        posix_fs,
        "sys",
        SimpleNamespace(implementation=SimpleNamespace(name="cpython"), version_info=(3, 11, 0)),
    )
    fs = posix_fs.PosixFilesystem()
    handle = fs.open_directory(FAKE_ROOT)
    assert fs.volume(handle)["filesystem"] == "POSIX"
    fs.close(handle)
    assert not api.fds


def test_injected_api_missing_required_symbol_is_unsupported(api: FakePosixApi) -> None:
    broken = SimpleNamespace(
        **{name: getattr(api, name) for name in posix_fs._REQUIRED_API if name != "O_CLOEXEC"}
    )
    with pytest.raises(AiflowError) as error:
        posix_fs.PosixFilesystem(api=broken)
    assert error.value.code == "INITIALIZATION_UNSUPPORTED"


@pytest.mark.parametrize("share_write", [False, True])
def test_open_directory_and_pin_ancestor_use_nofollow_directory_cloexec(
    api: FakePosixApi, share_write: bool
) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    ancestor = fs._pin_ancestor(FAKE_ROOT.parent)
    root = fs.open_directory(FAKE_ROOT, share_write=share_write)
    open_calls = [args for name, args, _ in api.calls if name == "open"]
    expected_flags = api.O_RDONLY | api.O_DIRECTORY | api.O_NOFOLLOW | api.O_CLOEXEC
    assert open_calls[0][1] == expected_flags
    assert open_calls[1][1] == expected_flags
    assert fs.identity(ancestor)["attributes"] & 0x10
    assert fs.identity(root)["attributes"] & 0x10
    fs.close(root)
    fs.close(ancestor)
    assert not api.fds


@pytest.mark.parametrize("operation", ["pin", "open_dir", "open_file"])
def test_symlink_and_wrong_type_are_rejected_and_do_not_leak_fds(
    api: FakePosixApi, operation: str
) -> None:
    api.seed_file(FAKE_ROOT / "regular.txt", b"data")
    api.seed_symlink(FAKE_ROOT / "link")
    fs = posix_fs.PosixFilesystem(api=api)

    with pytest.raises(AiflowError):
        if operation == "pin":
            fs._pin_ancestor(FAKE_ROOT / "link")
        elif operation == "open_dir":
            fs.open_directory(FAKE_ROOT / "regular.txt")
        else:
            fs.open_file(FAKE_ROOT)
    assert not api.fds

    # Also test post-open fstat detecting symlink / wrong mode (closes fd cleanly).
    api.override_mode = stat.S_IFLNK | 0o777
    with pytest.raises(AiflowError):
        fs.open_file(FAKE_ROOT / "regular.txt")
    assert not api.fds


def test_open_file_rejects_fifo_and_hardlinked_files(api: FakePosixApi) -> None:
    api.seed_file(FAKE_ROOT / "fifo", mode=stat.S_IFIFO | 0o644)
    ino = api.seed_file(FAKE_ROOT / "hardlinked", b"abc")
    api.inodes[ino]["links"] = 2
    fs = posix_fs.PosixFilesystem(api=api)

    with pytest.raises(AiflowError):
        fs.open_file(FAKE_ROOT / "fifo")
    with pytest.raises(AiflowError):
        fs.open_file(FAKE_ROOT / "hardlinked")
    assert not api.fds


def test_open_file_flags_and_allow_rename_parent_lifecycle(api: FakePosixApi) -> None:
    api.seed_file(FAKE_ROOT / ".ai/.repository-id.pending", b"uuid\n")
    fs = posix_fs.PosixFilesystem(api=api)

    ro = fs.open_file(FAKE_ROOT / ".ai/.repository-id.pending", writable=False, allow_rename=False)
    rw = fs.open_file(FAKE_ROOT / ".ai/.repository-id.pending", writable=True, allow_rename=True)
    open_calls = [(args, kwargs) for name, args, kwargs in api.calls if name == "open"]
    assert open_calls[0][0][1] == (api.O_RDONLY | api.O_NOFOLLOW | api.O_CLOEXEC)
    assert open_calls[1][0][1] == (api.O_RDONLY | api.O_DIRECTORY | api.O_NOFOLLOW | api.O_CLOEXEC)
    assert open_calls[2][0][1] == (api.O_RDWR | api.O_NOFOLLOW | api.O_CLOEXEC)
    assert "dir_fd" in open_calls[2][1]

    fs.rename_no_replace(rw, FAKE_ROOT / ".ai/repository-id")
    assert fs.read(rw, 64) == b"uuid\n"
    fs.close(rw)
    fs.close(ro)
    assert not api.fds


def test_open_file_allow_rename_error_paths_clean_up_parent_fd(api: FakePosixApi) -> None:
    api.seed_file(FAKE_ROOT / ".ai/pending", b"uuid\n")
    fs = posix_fs.PosixFilesystem(api=api)

    # Child open fails -> parent_fd is closed.
    with pytest.raises(AiflowError):
        fs.open_file(FAKE_ROOT / ".ai/missing", allow_rename=True)
    assert not api.fds

    # Parent fstat fails -> parent_fd is closed.
    api.fail["fstat"] = OSError(errno.EIO, "io")
    with pytest.raises(AiflowError):
        fs.open_file(FAKE_ROOT / ".ai/pending", allow_rename=True)
    assert not api.fds
    api.fail.clear()

    # Parent fstat returns non-directory -> parent_fd is closed.
    api.override_mode = stat.S_IFREG | 0o644
    with pytest.raises(AiflowError):
        fs.open_file(FAKE_ROOT / ".ai/pending", allow_rename=True)
    assert not api.fds
    api.override_mode = None

    # Close failure on parent_fd when closing owned handle, and when both fds fail.
    handle = fs.open_file(FAKE_ROOT / ".ai/pending", allow_rename=True)
    parent_fd = fs._handles[handle].parent_fd
    orig_close = api.close

    def fail_on_parent_close(fd: int) -> None:
        if fd == parent_fd:
            raise OSError(errno.EIO, "parent close failed")
        orig_close(fd)

    api.close = fail_on_parent_close
    with pytest.raises(AiflowError) as error:
        fs.close(handle)
    assert error.value.code == "INITIALIZATION_POSIX_FAILED"

    api.close = orig_close
    handle2 = fs.open_file(FAKE_ROOT / ".ai/pending", allow_rename=True)
    api.fail["close"] = OSError(errno.EIO, "both fail")
    with pytest.raises(AiflowError) as error:
        fs.close(handle2)
    assert error.value.code == "INITIALIZATION_POSIX_FAILED"
    api.fail.clear()


def test_atomic_child_creation_write_flush_read_and_rename(api: FakePosixApi) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    root = fs.open_directory(FAKE_ROOT, share_write=True)
    ai = fs.create_directory(root, ".ai", share_write=True)
    pending = fs.create_file(ai, ".repository-id.pending", allow_rename=True)

    create_call = next(
        (args, kwargs)
        for name, args, kwargs in api.calls
        if name == "open" and "dir_fd" in kwargs and args[0] == ".repository-id.pending"
    )
    assert create_call[0][1] == (
        api.O_CREAT | api.O_EXCL | api.O_RDWR | api.O_NOFOLLOW | api.O_CLOEXEC
    )
    assert create_call[1]["dir_fd"] == ai

    payload = b"11111111-2222-4333-8444-555555555555\n"
    fs.write(pending, payload)
    fs.flush(pending)
    assert fs.read(pending, len(payload)) == payload
    assert fs.read(pending, len(payload)) == payload  # Seeks to 0 each time.
    assert fs.identity(pending)["size"] == len(payload)

    before_id = fs.identity(pending)
    fs.rename_no_replace(pending, FAKE_ROOT / ".ai/repository-id")
    after_id = fs.identity(pending)
    assert after_id == before_id
    assert after_id["links"] == 1
    assert fs.read(pending, len(payload)) == payload

    # Existing target cannot be replaced.
    second = fs.create_file(ai, ".repository-id.pending", allow_rename=True)
    fs.write(second, b"replacement\n")
    with pytest.raises(AiflowError) as error:
        fs.rename_no_replace(second, FAKE_ROOT / ".ai/repository-id")
    assert error.value.code == "INITIALIZATION_POSIX_FAILED"
    assert error.value.details["errno"] == errno.EEXIST

    fs.close(second)
    fs.close(pending)
    fs.close(ai)
    fs.close(root)
    assert not api.fds


def test_multi_chunk_read_and_write(api: FakePosixApi) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    root = fs.open_directory(FAKE_ROOT)
    handle = fs.create_file(root, "large.bin")
    data = b"A" * (130 * 1024)
    fs.write(handle, data)
    assert fs.read(handle, len(data)) == data
    with pytest.raises(AiflowError):
        fs.read(handle, len(data) - 1)
    fs.close(handle)
    fs.close(root)


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "../escape",
        "child/name",
        "child\\name",
        "a\0b",
        "bad\nname",
        "del\x7fname",
        "\ud800",
        "x" * 256,
        "😀" * 64,
    ],
)
def test_invalid_child_names_rejected_before_api_calls(api: FakePosixApi, name: str) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    parent = fs.open_directory(FAKE_ROOT)
    before = len(api.calls)
    with pytest.raises(AiflowError) as error:
        fs.create_file(parent, name)
    assert error.value.code == "INITIALIZATION_POSIX_INVALID"
    assert len(api.calls) == before
    fs.close(parent)


@pytest.mark.parametrize(
    "bad_path", [Path("relative/path"), FAKE_ROOT / "a\0b", FAKE_ROOT / "\ud800"]
)
def test_invalid_absolute_paths_rejected_before_api_calls(
    api: FakePosixApi, bad_path: Path
) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    with pytest.raises(AiflowError) as error:
        fs.open_directory(bad_path)
    assert error.value.code == "INITIALIZATION_POSIX_INVALID"
    assert not api.calls


@pytest.mark.parametrize("handle", [None, True, -1, 999])
def test_invalid_or_unknown_handles_rejected_without_api_calls(
    api: FakePosixApi, handle: Any
) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    with pytest.raises(AiflowError) as error:
        fs.identity(handle)
    assert error.value.code == "INITIALIZATION_POSIX_INVALID"
    assert not api.calls


def test_only_directory_handles_can_create_children(api: FakePosixApi) -> None:
    api.seed_file(FAKE_ROOT / "file", b"x")
    fs = posix_fs.PosixFilesystem(api=api)
    file = fs.open_file(FAKE_ROOT / "file")
    with pytest.raises(AiflowError):
        fs.create_directory(file, "sub")
    with pytest.raises(AiflowError):
        fs.create_file(file, "sub")
    fs.close(file)


def test_write_constraints_and_short_write_rejection(api: FakePosixApi) -> None:
    api.seed_file(FAKE_ROOT / "existing", b"owner")
    fs = posix_fs.PosixFilesystem(api=api)
    existing = fs.open_file(FAKE_ROOT / "existing", writable=True)
    with pytest.raises(AiflowError):
        fs.write(existing, b"overwrite")
    fs.close(existing)

    root = fs.open_directory(FAKE_ROOT)
    created = fs.create_file(root, "new.txt")
    fs.write(created, b"once")
    with pytest.raises(AiflowError):
        fs.write(created, b"twice")
    with pytest.raises(AiflowError):
        fs.write(root, b"dir")

    short_target = fs.create_file(root, "short.txt")
    api.partial_write = True
    with pytest.raises(AiflowError) as error:
        fs.write(short_target, b"hello")
    assert error.value.code == "INITIALIZATION_POSIX_FAILED"

    fs.close(short_target)
    fs.close(created)
    fs.close(root)


@pytest.mark.parametrize("limit", [-1, True, "4", None, 1024 * 1024 + 1])
def test_invalid_read_bounds_do_not_call_api(api: FakePosixApi, limit: Any) -> None:
    api.seed_file(FAKE_ROOT / "file", b"x")
    fs = posix_fs.PosixFilesystem(api=api)
    file = fs.open_file(FAKE_ROOT / "file")
    before = len(api.calls)
    with pytest.raises(AiflowError):
        fs.read(file, limit)
    assert not any(name == "read" for name, _, _ in api.calls[before:])
    fs.close(file)


def test_corrupt_read_and_open_returns_are_rejected(api: FakePosixApi) -> None:
    api.seed_file(FAKE_ROOT / "file", b"x")
    fs = posix_fs.PosixFilesystem(api=api)
    file = fs.open_file(FAKE_ROOT / "file")
    api.bad_read_return = b"123456"
    with pytest.raises(AiflowError):
        fs.read(file, 4)
    api.bad_read_return = None
    fs.close(file)

    api.bad_open_return = -1
    with pytest.raises(AiflowError):
        fs.open_file(FAKE_ROOT / "file")


@pytest.mark.parametrize(
    "op", ["mkdir", "lseek", "read", "write", "fsync", "fstat", "fstatvfs", "close"]
)
def test_os_errors_translate_to_posix_failed(api: FakePosixApi, op: str) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    root = fs.open_directory(FAKE_ROOT)
    file = fs.create_file(root, "item")
    api.fail[op] = OSError(errno.EIO, "injected")
    actions = {
        "mkdir": lambda: fs.create_directory(root, "dir"),
        "lseek": lambda: fs.read(file, 4),
        "read": lambda: fs.read(file, 4),
        "write": lambda: fs.write(file, b"abc"),
        "fsync": lambda: fs.flush(file),
        "fstat": lambda: fs.identity(file),
        "fstatvfs": lambda: fs.volume(root),
        "close": lambda: fs.close(file),
    }
    with pytest.raises(AiflowError) as error:
        actions[op]()
    assert error.value.code == "INITIALIZATION_POSIX_FAILED"
    api.fail.clear()
    fs.close(file)
    fs.close(root)


def test_volume_fallback_without_fstatvfs() -> None:
    api = FakePosixApi(include_fstatvfs=False)
    fs = posix_fs.PosixFilesystem(api=api)
    root = fs.open_directory(FAKE_ROOT)
    assert fs.volume(root) == {"filesystem": "POSIX", "flags": 0, "max_component": 255}
    fs.close(root)


def test_rename_no_replace_guards_and_post_publish_identity_checks(api: FakePosixApi) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    root = fs.open_directory(FAKE_ROOT)
    ai = fs.create_directory(root, ".ai")
    not_renameable = fs.create_file(ai, "plain", allow_rename=False)
    with pytest.raises(AiflowError):
        fs.rename_no_replace(not_renameable, FAKE_ROOT / ".ai/dest")
    fs.close(not_renameable)

    pending = fs.create_file(ai, ".repository-id.pending", allow_rename=True)
    with pytest.raises(AiflowError):
        fs.rename_no_replace(pending, Path("relative/dest"))
    with pytest.raises(AiflowError):
        fs.rename_no_replace(pending, FAKE_ROOT / "wrong-parent/dest")

    # Failure in unlink / fsync translates to domain error.
    api.fail["unlink"] = OSError(errno.EPERM, "unlink denied")
    with pytest.raises(AiflowError):
        fs.rename_no_replace(pending, FAKE_ROOT / ".ai/id1")
    api.fail.clear()

    pending2 = fs.create_file(ai, ".repository-id.pending2", allow_rename=True)
    api.fail["fsync"] = OSError(errno.EIO, "fsync failed")
    with pytest.raises(AiflowError):
        fs.rename_no_replace(pending2, FAKE_ROOT / ".ai/id2")
    api.fail.clear()

    # Post-publish link count != 1 triggers failure.
    pending3 = fs.create_file(ai, ".repository-id.pending3", allow_rename=True)
    api.override_after_link_links = 2
    with pytest.raises(AiflowError) as error:
        fs.rename_no_replace(pending3, FAKE_ROOT / ".ai/id3")
    assert error.value.code == "INITIALIZATION_POSIX_FAILED"
    api.override_after_link_links = None

    # Post-publish inode mismatch triggers failure.
    pending4 = fs.create_file(ai, ".repository-id.pending4", allow_rename=True)
    api.override_after_link_inode = 9999
    with pytest.raises(AiflowError) as error:
        fs.rename_no_replace(pending4, FAKE_ROOT / ".ai/id4")
    assert error.value.code == "INITIALIZATION_POSIX_FAILED"
    api.override_after_link_inode = None

    for handle in (pending4, pending3, pending2, pending, ai, root):
        fs.close(handle)


def test_close_cannot_be_repeated_and_close_raw_swallows_cleanup_oserror(api: FakePosixApi) -> None:
    fs = posix_fs.PosixFilesystem(api=api)
    root = fs.open_directory(FAKE_ROOT)
    fs.close(root)
    with pytest.raises(AiflowError):
        fs.close(root)
    api.fail["close"] = OSError(errno.EBADF, "ignored during raw cleanup")
    fs._close_raw(999)


def test_initialization_dispatch_selects_posix_and_checks_volume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import aiflow.initialization as initialization

    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "--template=", "-b", "feature")
    (root / "pyproject.toml").write_bytes(
        b'[project]\nname = "posix-dispatch"\nversion = "0.0.0"\n'
    )
    (root / "example.py").write_bytes(b'"""fixture."""\n')
    git(root, "add", "pyproject.toml", "example.py")
    git(
        root,
        "-c",
        "user.name=AI Flow Test",
        "-c",
        "user.email=init@example.invalid",
        "commit",
        "-m",
        "baseline",
    )
    bundle = tmp_path / "bundle"
    manifest, resources = build_bundle(ROOT)
    for rel, data in resources.items():
        target = bundle / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    proposal = initialization.preview_initialization(root, bundle_root=bundle)
    decision = {
        "schema_version": "1.0",
        "kind": "aiflow-policy-review",
        "preview_sha256": proposal["preview_sha256"],
        "repository_id": proposal["repository_id"],
        "profile": proposal["profile"],
        "policy_version": proposal["policy"]["policy_version"],
        "policies": [
            {"path": row["path"], "sha256": row["sha256"]} for row in proposal["policy"]["files"]
        ],
        "reviewer": "independent-test-reviewer",
        "outcome": "APPROVE",
    }

    class FakePosixBackend(posix_fs.PosixFilesystem):
        def __init__(self) -> None:
            fake = FakePosixApi()
            for ancestor in (*reversed(root.parents), root):
                ino = fake._seed_path(ancestor)
                real = ancestor.lstat()
                fake.inodes[ino]["real_dev"] = real.st_dev
                fake.inodes[ino]["real_ino"] = real.st_ino
            orig_fstat = fake._fstat

            def real_aligned_fstat(fd: int) -> SimpleNamespace:
                res = orig_fstat(fd)
                node = fake.inodes[fake.fds[fd]["inode"]]
                if "real_ino" in node:
                    res.st_dev = node["real_dev"]
                    res.st_ino = node["real_ino"]
                return res

            fake._fstat = real_aligned_fstat
            fake.fstat = fake._wrap("fstat", real_aligned_fstat)
            super().__init__(api=fake)

        def volume(self, handle: int) -> dict[str, str | int]:
            return {"filesystem": "FAT32", "flags": 0, "max_component": 255}

    monkeypatch.setattr(initialization, "_platform_name", lambda: "posix")
    monkeypatch.setattr(initialization, "PosixFilesystem", FakePosixBackend)
    with pytest.raises(AiflowError) as error:
        initialization.apply_initialization(root, proposal, decision, bundle_root=bundle)
    assert error.value.code == "INITIALIZATION_FILESYSTEM_UNSUPPORTED"


@pytest.mark.skipif(os.name != "posix", reason="POSIX real filesystem test")
def test_real_posix_preview_apply_resume_replay_and_no_replace(tmp_path: Path) -> None:
    import aiflow.initialization as initialization

    bundle = tmp_path / "bundle"
    manifest, resources = build_bundle(ROOT)
    for rel, data in resources.items():
        target = bundle / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "--template=", "-b", "feature")
    (root / "pyproject.toml").write_bytes(b'[project]\nname = "real-posix"\nversion = "0.0.0"\n')
    (root / "app.py").write_bytes(b'"""Real POSIX fixture."""\n')
    git(root, "add", "pyproject.toml", "app.py")
    git(
        root,
        "-c",
        "user.name=AI Flow Test",
        "-c",
        "user.email=init@example.invalid",
        "commit",
        "-m",
        "baseline",
    )

    # Full install + inspect + idempotent replay.
    proposal = initialization.preview_initialization(root, bundle_root=bundle)
    decision = {
        "schema_version": "1.0",
        "kind": "aiflow-policy-review",
        "preview_sha256": proposal["preview_sha256"],
        "repository_id": proposal["repository_id"],
        "profile": proposal["profile"],
        "policy_version": proposal["policy"]["policy_version"],
        "policies": [
            {"path": row["path"], "sha256": row["sha256"]} for row in proposal["policy"]["files"]
        ],
        "reviewer": "independent-test-reviewer",
        "outcome": "APPROVE",
    }
    applied = initialization.apply_initialization(root, proposal, decision, bundle_root=bundle)
    assert applied["phase"] == "installed"
    initialization.require_initialization_ready(root)
    assert initialization.inspect_initialization(root)["status"] == "complete"
    assert (root / ".ai/repository-id").read_text("utf-8").strip() == proposal["repository_id"]
    assert not (root / ".ai/.repository-id.pending").exists()

    before = tree(root)
    replayed = initialization.apply_initialization(root, proposal, decision, bundle_root=bundle)
    assert replayed["phase"] == "already_complete"
    assert tree(root) == before

    # Partial resume path on real POSIX (uses open_file(..., allow_rename=True)).
    (root / ".ai/repository-id").unlink()
    (root / ".ai/init-complete.json").unlink()
    for rel in RESOURCE_KINDS:
        (root / ".ai" / rel).unlink()
        break
    (root / ".ai/.repository-id.pending").write_bytes(
        (proposal["repository_id"] + "\n").encode("utf-8")
    )
    assert initialization.inspect_initialization(root)["status"] == "incomplete"
    resumed = initialization.apply_initialization(
        root, deepcopy(proposal), deepcopy(decision), bundle_root=bundle
    )
    assert resumed["phase"] == "resumed"
    assert resumed["repository_id"] == proposal["repository_id"]
    assert initialization.inspect_initialization(root)["status"] == "complete"

    # Existing target cannot be overwritten by PosixFilesystem.rename_no_replace.
    fs = posix_fs.PosixFilesystem()
    dir_fd = fs.open_directory(root / ".ai")
    try:
        pending_fd = fs.create_file(dir_fd, ".repository-id.pending", allow_rename=True)
        try:
            fs.write(pending_fd, b"new-id\n")
            with pytest.raises(AiflowError) as error:
                fs.rename_no_replace(pending_fd, root / ".ai/repository-id")
            assert error.value.code == "INITIALIZATION_POSIX_FAILED"
            assert error.value.details["errno"] == errno.EEXIST
            assert (root / ".ai/repository-id").read_text("utf-8").strip() == proposal[
                "repository_id"
            ]
        finally:
            fs.close(pending_fd)
    finally:
        fs.close(dir_fd)
