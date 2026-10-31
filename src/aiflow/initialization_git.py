"""Bounded, read-only Git observations for the fresh-repository initializer."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import threading
from io import BufferedReader
from pathlib import Path
from time import monotonic
from typing import Any, cast

from aiflow.errors import AiflowError
from aiflow.resource_bundle import RESOURCE_KINDS

MAX_FILES = 10_000
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_INDEX_BYTES = 16 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 8 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 10
OBSERVATION_TIMEOUT_SECONDS = 30
_READ_CHUNK = 64 * 1024
_COMMIT = re.compile(r"[0-9a-f]{40}")
_INITIALIZATION_PATHS = frozenset(
    {f".ai/{name}" for name in RESOURCE_KINDS}
    | {
        ".ai",
        ".ai/schemas",
        ".ai/policy",
        ".ai/templates",
        ".ai/init-state.json",
        ".ai/policy-review.json",
        ".ai/init-complete.json",
        ".ai/.repository-id.pending",
        ".ai/repository-id",
    }
)


def _fail(code: str = "INIT_GIT_INVALID") -> AiflowError:
    return AiflowError("Initialization Git facts are unavailable or unsafe", code=code)


def _remaining(deadline: float) -> float:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise _fail("INIT_GIT_TIMEOUT")
    return remaining


def _is_reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _directory_identity(path: Path) -> dict[str, int]:
    try:
        info = path.lstat()
    except (OSError, ValueError) as error:
        raise _fail("INIT_PATH_INVALID") from error
    if _is_reparse(info) or not stat.S_ISDIR(info.st_mode) or info.st_ino <= 0:
        raise _fail("INIT_PATH_INVALID")
    return {"device": info.st_dev, "inode": info.st_ino}


def _absolute_directory(path: Path) -> Path:
    if ".." in path.parts or str(path).replace("\\", "/").startswith("//"):
        raise _fail("INIT_PATH_INVALID")
    try:
        absolute = path.absolute()
        for ancestor in reversed((absolute, *absolute.parents)):
            _directory_identity(ancestor)
        return absolute
    except (OSError, ValueError) as error:
        raise _fail("INIT_PATH_INVALID") from error


def _git_program(root: Path) -> Path:
    found = shutil.which("git")
    if found is None:
        raise _fail("INIT_GIT_UNAVAILABLE")
    try:
        repository_roots = (
            root,
            *(ancestor for ancestor in root.parents if os.path.lexists(ancestor / ".git")),
        )
        original = Path(found).absolute()
        _absolute_directory(original.parent)
        original_info = original.lstat()
        program = original.resolve(strict=True)
        _absolute_directory(program.parent)
        program_info = program.lstat()
        if (
            original.name.casefold() not in {"git", "git.exe"}
            or program.name.casefold() not in {"git", "git.exe"}
            or _is_reparse(original_info)
            or _is_reparse(program_info)
            or not stat.S_ISREG(original_info.st_mode)
            or not stat.S_ISREG(program_info.st_mode)
            or any(
                original.is_relative_to(repository_root) or program.is_relative_to(repository_root)
                for repository_root in repository_roots
            )
            or (original_info.st_dev, original_info.st_ino)
            != (program_info.st_dev, program_info.st_ino)
        ):
            raise _fail("INIT_GIT_UNAVAILABLE")
        return program
    except (OSError, ValueError, AiflowError) as error:
        raise _fail("INIT_GIT_UNAVAILABLE") from error


def _environment(program: Path) -> dict[str, str]:
    environment = {
        "PATH": str(program.parent),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot")
        if not system_root:
            raise _fail("INIT_GIT_UNAVAILABLE")
        environment["SystemRoot"] = system_root
    return environment


def _run_git(
    cwd: Path,
    arguments: tuple[str, ...],
    *,
    deadline: float,
    allowed_returncodes: tuple[int, ...] = (0,),
    program: Path | None = None,
) -> tuple[int, bytes]:
    timeout = min(GIT_TIMEOUT_SECONDS, _remaining(deadline))
    executable = program or _git_program(_marker_root(_absolute_directory(cwd)))
    command = [
        str(executable),
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-c",
        "core.preloadIndex=false",
        "-c",
        f"core.excludesFile={os.devnull}",
        "-c",
        f"core.attributesFile={os.devnull}",
        *arguments,
    ]
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=_environment(executable),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as error:
        raise _fail("INIT_GIT_UNAVAILABLE") from error
    assert process.stdout is not None and process.stderr is not None
    buffers = [bytearray(), bytearray()]
    failed = threading.Event()
    lock = threading.Lock()
    total = 0

    def drain(index: int) -> None:
        nonlocal total
        stream = process.stdout if index == 0 else process.stderr
        assert stream is not None
        try:
            while not failed.is_set():
                with lock:
                    amount = min(_READ_CHUNK, max(1, MAX_GIT_OUTPUT_BYTES - total + 1))
                chunk = cast(BufferedReader, stream).read1(amount)
                if not chunk:
                    return
                with lock:
                    remaining = max(0, MAX_GIT_OUTPUT_BYTES + 1 - total)
                    buffers[index].extend(chunk[:remaining])
                    total += len(chunk)
                    if total > MAX_GIT_OUTPUT_BYTES:
                        failed.set()
        except (OSError, ValueError):
            failed.set()

    readers = [threading.Thread(target=drain, args=(index,), daemon=True) for index in (0, 1)]
    for reader in readers:
        reader.start()
    finish = monotonic() + timeout
    reason: str | None = None
    while process.poll() is None or any(reader.is_alive() for reader in readers):
        if failed.is_set():
            reason = "INIT_GIT_OUTPUT_LIMIT"
            break
        if monotonic() >= finish:
            reason = "INIT_GIT_TIMEOUT"
            break
        for reader in readers:
            reader.join(timeout=0.005)
    if reason is not None:
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            reason = "INIT_GIT_CLEANUP_UNCONFIRMED"
        for reader in readers:
            reader.join(timeout=0.1)
    complete = not any(reader.is_alive() for reader in readers)
    if complete:
        process.stdout.close()
        process.stderr.close()
    if not complete:
        raise _fail("INIT_GIT_CLEANUP_UNCONFIRMED")
    if reason is not None or failed.is_set():
        raise _fail(reason or "INIT_GIT_OUTPUT_LIMIT")
    if process.returncode not in allowed_returncodes:
        raise _fail()
    return process.returncode, bytes(buffers[0])


def _text(data: bytes) -> str:
    try:
        return data.decode("utf-8").rstrip("\r\n")
    except UnicodeError as error:
        raise _fail() from error


def _marker_root(target: Path) -> Path:
    """Locate the physical worktree boundary before selecting a Git executable."""
    marker_root = next(
        (path for path in (target, *target.parents) if os.path.lexists(path / ".git")),
        None,
    )
    if marker_root is None:
        raise _fail()
    if not (marker_root / ".git").is_dir():
        raise _fail("INIT_LINKED_WORKTREE_UNSUPPORTED")
    _directory_identity(marker_root / ".git")
    return marker_root


def _resolve_root(target: Path, program: Path, deadline: float) -> Path:
    marker_root = _marker_root(target)
    _configuration_facts(marker_root / ".git", deadline)
    _, output = _run_git(
        target, ("rev-parse", "--show-toplevel"), deadline=deadline, program=program
    )
    root = Path(_text(output))
    if not root.is_absolute():
        raise _fail("INIT_PATH_INVALID")
    root = _absolute_directory(root)
    if root != marker_root or not target.is_relative_to(root):
        raise _fail("INIT_PATH_INVALID")
    cursor = target
    while cursor != root:
        if os.path.lexists(cursor / ".git"):
            raise _fail("INIT_PATH_INVALID")
        cursor = cursor.parent
    return root


def resolve_initialization_root(target: Path) -> Path:
    """Locate a plain enclosing worktree using only bounded, fixed Git reads."""
    requested = _absolute_directory(target)
    return _resolve_root(
        requested, _git_program(_marker_root(requested)), monotonic() + OBSERVATION_TIMEOUT_SECONDS
    )


def _relative_path(raw: bytes) -> str:
    try:
        path = raw.decode("utf-8")
    except UnicodeError as error:
        raise _fail("INIT_PATH_INVALID") from error
    if (
        not path
        or "\\" in path
        or ":" in path
        or Path(path).is_absolute()
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise _fail("INIT_PATH_INVALID")
    return path


def _records(data: bytes, *, allow_initialization: bool = False) -> list[bytes]:
    if not data:
        return []
    if not data.endswith(b"\0"):
        raise _fail()
    records = data[:-1].split(b"\0")
    maximum = MAX_FILES + (len(_INITIALIZATION_PATHS) if allow_initialization else 0)
    if len(records) > maximum or any(not record for record in records):
        raise _fail("INIT_GIT_FILE_LIMIT")
    return records


def _file_facts(
    path: Path,
    limit: int,
    deadline: float,
    *,
    total_remaining: int | None = None,
    _content: bytearray | None = None,
) -> tuple[str, int, int]:
    _remaining(deadline)
    try:
        before = path.lstat()
        if (
            _is_reparse(before)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_ino <= 0
        ):
            raise _fail("INIT_PATH_INVALID")
        if before.st_size > limit or (
            total_remaining is not None and before.st_size > total_remaining
        ):
            raise _fail("INIT_GIT_FILE_LIMIT")
        digest = hashlib.sha256()
        size = 0
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise _fail("INIT_GIT_CHANGED")
            while True:
                _remaining(deadline)
                maximum = limit - size
                if total_remaining is not None:
                    maximum = min(maximum, total_remaining - size)
                data = stream.read(min(_READ_CHUNK, maximum + 1))
                if not data:
                    break
                size += len(data)
                if size > limit or (total_remaining is not None and size > total_remaining):
                    raise _fail("INIT_GIT_FILE_LIMIT")
                digest.update(data)
                if _content is not None:
                    _content.extend(data)
            after = os.fstat(stream.fileno())
        current = path.lstat()
        attributes = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
        if any(
            getattr(before, name) != getattr(other, name)
            for name in attributes
            for other in (opened, after, current)
        ):
            raise _fail("INIT_GIT_CHANGED")
        return digest.hexdigest(), size, stat.S_IMODE(before.st_mode)
    except (OSError, ValueError) as error:
        raise _fail("INIT_GIT_READ_FAILED") from error


def _configuration_facts(git_dir: Path, deadline: float) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name in ("config", "config.worktree"):
        path = git_dir / name
        if not os.path.lexists(path):
            result[name] = None
            continue
        content = bytearray()
        result[name] = _file_facts(path, MAX_FILE_BYTES, deadline, _content=content)[0]
        normalized = bytes(content).removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n")
        # This is a deliberately narrow input subset, not a Git config parser.
        # Refuse continuation/escaped section syntax rather than overlooking includes.
        if b"\\\n" in normalized or b"\r" in normalized:
            raise _fail("INIT_GIT_CONFIG_UNSUPPORTED")
        for line in normalized.splitlines():
            header = line.lstrip()
            if not header.startswith(b"["):
                continue
            match = re.fullmatch(
                rb'\[([A-Za-z0-9][A-Za-z0-9.-]*)(?:[ \t]+"[^"\\\r\n]*")?\]'
                rb"[ \t]*(?:[#;].*)?",
                header,
            )
            if match is None:
                raise _fail("INIT_GIT_CONFIG_UNSUPPORTED")
            section = match[1].lower().split(b".", 1)[0]
            if section in {b"include", b"includeif"}:
                raise _fail("INIT_GIT_CONFIG_UNSUPPORTED")
    return result


def _head_and_branch(root: Path, program: Path, deadline: float) -> tuple[str, dict[str, str]]:
    _, output = _run_git(
        root, ("rev-parse", "--verify", "HEAD^{commit}"), deadline=deadline, program=program
    )
    head = _text(output)
    if _COMMIT.fullmatch(head) is None:
        raise _fail()
    code, output = _run_git(
        root,
        ("symbolic-ref", "--quiet", "HEAD"),
        deadline=deadline,
        allowed_returncodes=(0, 1),
        program=program,
    )
    if code == 1:
        return head, {"kind": "detached"}
    branch = _text(output)
    if not branch.startswith("refs/heads/") or branch == "refs/heads/":
        raise _fail()
    return head, {"kind": "branch", "name": branch.removeprefix("refs/heads/")}


def observe_initialization_target(
    target: Path, *, exclude_initialization: bool = False
) -> dict[str, Any]:
    """Bind local physical facts and file digests without exposing a full inventory."""
    deadline = monotonic() + OBSERVATION_TIMEOUT_SECONDS
    requested = _absolute_directory(target)
    program = _git_program(_marker_root(requested))
    root = _resolve_root(requested, program, deadline)
    paths: list[Path] = []
    for arguments in (("rev-parse", "--absolute-git-dir"), ("rev-parse", "--git-common-dir")):
        _, output = _run_git(root, arguments, deadline=deadline, program=program)
        path = Path(_text(output))
        paths.append(_absolute_directory(path if path.is_absolute() else root / path))
    git_dir, common_dir = paths
    if git_dir != root / ".git" or common_dir != git_dir:
        raise _fail("INIT_LINKED_WORKTREE_UNSUPPORTED")
    ancestors = [
        {"path": path.as_posix(), **_directory_identity(path)}
        for path in reversed((root, *root.parents))
    ]
    root_identity = _directory_identity(root)
    git_identity = _directory_identity(git_dir)
    configuration = _configuration_facts(git_dir, deadline)
    head, branch = _head_and_branch(root, program, deadline)
    index = git_dir / "index"
    index_digest, _, _ = _file_facts(index, MAX_INDEX_BYTES, deadline)
    _, listing = _run_git(
        root, ("ls-tree", "-r", "-z", "--name-only", "HEAD"), deadline=deadline, program=program
    )
    head_paths = [_relative_path(record) for record in _records(listing)]
    _, listing = _run_git(root, ("ls-files", "--stage", "-z"), deadline=deadline, program=program)
    tracked: dict[str, str] = {}
    for record in _records(listing):
        header, separator, raw_path = record.partition(b"\t")
        fields = header.split()
        if (
            not separator
            or len(fields) != 3
            or fields[0] not in {b"100644", b"100755"}
            or not _COMMIT.fullmatch(fields[1].decode("ascii", "replace"))
            or fields[2] != b"0"
        ):
            raise _fail()
        relative_path = _relative_path(raw_path)
        if relative_path in tracked:
            raise _fail()
        tracked[relative_path] = fields[0].decode("ascii")
    if any(path.split("/", 1)[0].casefold() == ".ai" for path in (*head_paths, *tracked)):
        raise _fail("INIT_EXISTING_IDENTITY")
    _, listing = _run_git(
        root,
        ("ls-files", "--others", "--exclude-standard", "-z"),
        deadline=deadline,
        program=program,
    )
    untracked = [
        _relative_path(record)
        for record in _records(listing, allow_initialization=exclude_initialization)
    ]
    if len(set(untracked)) != len(untracked) or set(untracked).intersection(tracked):
        raise _fail()
    entries = {**{path: ("tracked", mode) for path, mode in tracked.items()}}
    entries.update({path: ("untracked", "") for path in untracked})
    if exclude_initialization:
        entries = {
            path: entry for path, entry in entries.items() if path not in _INITIALIZATION_PATHS
        }
    if len(entries) > MAX_FILES:
        raise _fail("INIT_GIT_FILE_LIMIT")
    rows: list[tuple[object, ...]] = []
    total = 0
    python_sources = 0
    for relative, (kind, mode) in sorted(entries.items()):
        _remaining(deadline)
        path = root / relative
        missing = False
        for directory in (
            *(root / ancestor for ancestor in reversed(path.parent.relative_to(root).parents)),
            path.parent,
        ):
            if not os.path.lexists(directory):
                missing = True
                break
            _directory_identity(directory)
        if missing or not os.path.lexists(path):
            if kind != "tracked":
                raise _fail("INIT_GIT_CHANGED")
            rows.append((relative, kind, mode, "missing"))
            continue
        digest, size, file_mode = _file_facts(
            path, MAX_FILE_BYTES, deadline, total_remaining=MAX_TOTAL_BYTES - total
        )
        total += size
        python_sources += path.suffix == ".py"
        rows.append((relative, kind, mode, digest, size, file_mode))
    if (
        _head_and_branch(root, program, deadline) != (head, branch)
        or _file_facts(index, MAX_INDEX_BYTES, deadline)[0] != index_digest
        or _directory_identity(root) != root_identity
        or _directory_identity(git_dir) != git_identity
        or _configuration_facts(git_dir, deadline) != configuration
        or ancestors
        != [
            {"path": path.as_posix(), **_directory_identity(path)}
            for path in reversed((root, *root.parents))
        ]
    ):
        raise _fail("INIT_GIT_CHANGED")
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    _remaining(deadline)
    return {
        "root": root.as_posix(),
        "git_dir": git_dir.as_posix(),
        "common_dir": common_dir.as_posix(),
        "head": head,
        "branch": branch,
        "root_identity": root_identity,
        "git_dir_identity": git_identity,
        "common_dir_identity": dict(git_identity),
        "ancestors": ancestors,
        "index_sha256": index_digest,
        "git_config_sha256": hashlib.sha256(
            json.dumps(configuration, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "worktree_sha256": hashlib.sha256(payload).hexdigest(),
        "tracked_count": sum(entry[0] == "tracked" for entry in entries.values()),
        "untracked_count": sum(entry[0] == "untracked" for entry in entries.values()),
        "file_count": len(rows),
        "python_source_count": python_sources,
    }
