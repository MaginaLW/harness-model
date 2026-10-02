"""Creation-time compatibility and real bounded-reader mutation boundaries."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, BinaryIO, cast

import pytest

from aiflow import external_review
from aiflow.errors import ContractError

SYNTHETIC_SECRET = "SYNTHETIC_METADATA_SECRET"


def metadata(birthtime: int | None = 11, **changes: int) -> os.stat_result:
    fields = {"st_dev": 2, "st_ino": 3, "st_size": 4, "st_mtime_ns": 5, "st_ctime_ns": 6}
    if birthtime is not None:
        fields["st_birthtime_ns"] = birthtime
    fields.update(changes)
    return cast(os.stat_result, SimpleNamespace(**fields))


def safe_error(error: ContractError, code: str, source: Path) -> None:
    assert error.code == code
    rendered = json.dumps(error.to_dict())
    assert SYNTHETIC_SECRET not in rendered
    assert str(source) not in rendered


@pytest.mark.parametrize(
    "platform,birthtime,chosen_creation",
    [("nt", 11, 11), ("nt", 0, 0), ("nt", None, 6), ("posix", 11, 6)],
    ids=["windows-birthtime", "windows-zero", "windows-legacy", "posix-keeps-ctime"],
)
def test_metadata_selects_creation_without_changing_global_platform(
    monkeypatch: pytest.MonkeyPatch, platform: str, birthtime: int | None, chosen_creation: int
) -> None:
    original_platform = os.name
    monkeypatch.setattr(external_review, "os", SimpleNamespace(name=platform))
    assert external_review._metadata_identity(metadata(birthtime)) == (2, 3, 4, 5, chosen_creation)
    assert os.name == original_platform


@pytest.mark.parametrize("field", ["st_dev", "st_ino", "st_size", "st_mtime_ns", "st_birthtime_ns"])
def test_windows_identity_retains_every_original_field_and_chosen_creation(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    monkeypatch.setattr(external_review, "os", SimpleNamespace(name="nt"))
    original = metadata()
    changed = metadata(**{field: getattr(original, field) + 1})
    assert external_review._metadata_identity(original) != external_review._metadata_identity(
        changed
    )


def test_windows_birthtime_ignores_only_legacy_ctime_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(external_review, "os", SimpleNamespace(name="nt"))
    assert external_review._metadata_identity(metadata(st_ctime_ns=6)) == (
        external_review._metadata_identity(metadata(st_ctime_ns=7))
    )


@pytest.mark.parametrize("platform,birthtime", [("nt", None), ("posix", 11)])
def test_legacy_windows_and_posix_still_detect_ctime_changes(
    monkeypatch: pytest.MonkeyPatch, platform: str, birthtime: int | None
) -> None:
    monkeypatch.setattr(external_review, "os", SimpleNamespace(name=platform))
    assert external_review._metadata_identity(metadata(birthtime, st_ctime_ns=6)) != (
        external_review._metadata_identity(metadata(birthtime, st_ctime_ns=7))
    )


def test_atomically_published_unchanged_input_remains_readable(tmp_path: Path) -> None:
    source = tmp_path / "published.bin"
    pending = tmp_path / "pending.bin"
    payload = SYNTHETIC_SECRET.encode() + b"\x00\xff"
    pending.write_bytes(payload)
    os.replace(pending, source)
    before = source.stat()
    assert external_review._read_bounded_file(source, len(payload)) == payload
    after = source.stat()
    assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == [source.name]


@pytest.mark.parametrize("open_number", [1, 2], ids=["first-open", "second-open"])
@pytest.mark.parametrize("same_bytes", [False, True], ids=["different-bytes", "same-bytes"])
def test_equal_length_replacement_with_restored_mtime_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, open_number: int, same_bytes: bool
) -> None:
    source = tmp_path / f"{SYNTHETIC_SECRET}.bin"
    replacement = tmp_path / "replacement.bin"
    payload = SYNTHETIC_SECRET.encode()
    changed = payload if same_bytes else payload[:-1] + b"!"
    source.write_bytes(payload)
    before = source.stat()
    replacement.write_bytes(changed)
    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert replacement.stat().st_ino != before.st_ino
    physical = external_review._io_path(source)
    original_open = Path.open
    opens = 0

    def replacing_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        nonlocal opens
        if self == physical and args and args[0] == "rb":
            opens += 1
            if opens == open_number:
                os.replace(replacement, source)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replacing_open)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, len(payload))
    safe_error(caught.value, "EXTERNAL_REVIEW_INPUT_CHANGED", source)
    assert opens == open_number
    after = source.stat()
    assert after.st_ino != before.st_ino
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)
    assert not replacement.exists()


class ObservedReader:
    def __init__(self, stream: BinaryIO, before_read: Callable[[], None]) -> None:
        self.stream = stream
        self.before_read = before_read

    def __enter__(self) -> ObservedReader:
        return self

    def __exit__(self, *args: object) -> None:
        self.stream.close()

    def fileno(self) -> int:
        return self.stream.fileno()

    def read(self, maximum: int) -> bytes:
        self.before_read()
        return self.stream.read(maximum)


def test_second_raw_read_rejects_same_inode_rewrite_with_restored_mtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / f"{SYNTHETIC_SECRET}.bin"
    payload = SYNTHETIC_SECRET.encode()
    changed = payload[:-1] + b"!"
    source.write_bytes(payload)
    before = source.stat()
    physical = external_review._io_path(source)
    original_open = Path.open
    original_identity = external_review._metadata_identity
    creation = original_identity(before)[4]
    opens = reads = 0
    second_payload: bytes | None = None

    def stable_creation(value: os.stat_result) -> tuple[int, int, int, int, int]:
        # Model unchanged creation identity also on POSIX, whose real ctime
        # changes on writes. Keep dev/ino/size/mtime from actual metadata so
        # this case specifically proves the independent raw-byte comparison.
        identity = original_identity(value)
        return (*identity[:4], creation)

    def observed_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        nonlocal opens
        stream = original_open(self, *args, **kwargs)
        if self != physical or not args or args[0] != "rb":
            return stream
        opens += 1
        this_open = opens

        def before_read() -> None:
            nonlocal reads
            reads += 1
            if this_open == 2:
                with original_open(source, "r+b") as writer:
                    writer.write(changed)
                os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))

        class RecordingReader(ObservedReader):
            def read(self, maximum: int) -> bytes:
                nonlocal second_payload
                data = super().read(maximum)
                if this_open == 2:
                    second_payload = data
                return data

        return RecordingReader(stream, before_read)

    # Windows exercises the real helper. POSIX alone freezes its fifth quantity
    # to isolate the raw guard; the genuine POSIX ctime semantics are tested above.
    if os.name != "nt":
        monkeypatch.setattr(external_review, "_metadata_identity", stable_creation)
    monkeypatch.setattr(Path, "open", observed_open)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, len(payload))
    safe_error(caught.value, "EXTERNAL_REVIEW_INPUT_CHANGED", source)
    assert opens == reads == 2
    assert second_payload == changed and changed != payload
    assert external_review._metadata_identity(source.stat()) == (
        external_review._metadata_identity(before)
    )
    assert source.stat().st_ino == before.st_ino


def test_real_growth_keeps_original_limit_plus_one_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / f"{SYNTHETIC_SECRET}.bin"
    payload = SYNTHETIC_SECRET.encode()
    source.write_bytes(payload)
    physical = external_review._io_path(source)
    original_open = Path.open
    requested: list[int] = []

    def growing_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        stream = original_open(self, *args, **kwargs)
        if self != physical or not args or args[0] != "rb":
            return stream

        class GrowingReader(ObservedReader):
            def read(self, maximum: int) -> bytes:
                requested.append(maximum)
                return super().read(maximum)

        def before_read() -> None:
            with original_open(source, "ab") as writer:
                writer.write(b"!")

        return GrowingReader(stream, before_read)

    monkeypatch.setattr(Path, "open", growing_open)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, len(payload))
    safe_error(caught.value, "EXTERNAL_REVIEW_SIZE_LIMIT", source)
    assert requested == [len(payload) + 1]
    assert source.stat().st_size == len(payload) + 1
