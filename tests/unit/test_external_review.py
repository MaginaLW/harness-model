"""Pure byte, JSON and lexical safety boundaries for external reviews."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from aiflow import external_review
from aiflow.errors import ContractError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_SECRET = "SYNTHETIC_UNIT_INPUT_SECRET"


@pytest.mark.parametrize(
    "path",
    [
        r"\\synthetic-server\share\file.json",
        r"\\?\C:\synthetic\file.json",
        r"C:\synthetic\file.json:ads",
        r"C:\synthetic\NUL.json",
        r"C:\synthetic\COM1",
        r"C:\synthetic\CONIN$",
        r"C:\synthetic\CONOUT$",
        r"C:\synthetic\COM¹.json",
        r"C:\synthetic\LPT²",
        "synthetic.json.",
        "synthetic.json ",
    ],
)
def test_unsafe_windows_lexical_paths_are_rejected_before_metadata(
    path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def unexpected_metadata(self: Path, *args: object, **kwargs: object) -> os.stat_result:
        calls.append(self)
        raise AssertionError("Unsafe lexical input reached filesystem metadata")

    monkeypatch.setattr(Path, "lstat", unexpected_metadata)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(Path(path), 1024)
    assert caught.value.code.startswith("EXTERNAL_REVIEW_")
    assert calls == []


def assert_safe_error(error: ContractError, code: str) -> None:
    assert error.code == code
    assert SYNTHETIC_SECRET not in json.dumps(error.to_dict())


@pytest.mark.parametrize(
    "payload,code",
    [
        (b"\xef\xbb\xbf{}", "EXTERNAL_REVIEW_JSON_INVALID"),
        (b"\xff", "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unknown":NaN}', "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unknown":Infinity}', "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unknown":1e9999}', "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unknown":"\\ud800"}', "EXTERNAL_REVIEW_JSON_INVALID"),
        (b"[]", "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unclosed":', "EXTERNAL_REVIEW_JSON_INVALID"),
        (
            b'{"SYNTHETIC_UNIT_INPUT_SECRET":1,"SYNTHETIC_UNIT_INPUT_SECRET":2}',
            "EXTERNAL_REVIEW_JSON_DUPLICATE_KEY",
        ),
        (b'{"SYNTHETIC_UNIT_INPUT_SECRET":"unknown"}', "EXTERNAL_REVIEW_CONTRACT_INVALID"),
    ],
)
def test_strict_json_loader_refuses_invalid_bytes_without_reflecting_input(
    payload: bytes, code: str
) -> None:
    with pytest.raises(ContractError) as caught:
        external_review._load_json_bytes(payload, "external-review", PROJECT_ROOT)
    assert_safe_error(caught.value, code)


@pytest.mark.parametrize(
    "contract_name",
    ["external-review", "external-review-import", "external-review-repository-mapping"],
)
def test_strict_loader_accepts_real_contract_fixture_without_git(contract_name: str) -> None:
    value = json.loads(
        (PROJECT_ROOT / f"tests/fixtures/contracts/valid/{contract_name}.json").read_text()
    )
    compact = external_review.canonical_json(value).encode("utf-8")
    pretty = json.dumps(value, ensure_ascii=False, indent=4).encode("utf-8")
    assert external_review._load_json_bytes(compact, contract_name, PROJECT_ROOT) == value
    assert external_review._load_json_bytes(pretty, contract_name, PROJECT_ROOT) == value
    assert external_review.canonical_sha256(json.loads(compact)) == (
        external_review.canonical_sha256(json.loads(pretty))
    )


@pytest.mark.parametrize("depth", [32, 33])
def test_json_depth_is_bounded_before_contract_validation(depth: int) -> None:
    payload = b"[" * depth + b"0" + b"]" * depth
    with pytest.raises(ContractError) as caught:
        external_review._load_json_bytes(payload, "external-review", PROJECT_ROOT)
    assert_safe_error(
        caught.value,
        "EXTERNAL_REVIEW_DEPTH_LIMIT" if depth == 33 else "EXTERNAL_REVIEW_JSON_INVALID",
    )


def test_json_scanner_ignores_brackets_and_escaped_quotes_inside_narrative() -> None:
    narrative = json.dumps({"description": '[{}] "quoted" \\ narrative ' * 40})
    assert external_review._bounded_json_text(narrative.encode()) == narrative


@pytest.mark.parametrize("unsupported", [{"a", "b"}, float("nan"), float("inf"), "\ud800"])
def test_canonical_digest_refuses_unsupported_or_nonutf8_values(unsupported: object) -> None:
    with pytest.raises(ContractError) as caught:
        external_review.canonical_sha256({SYNTHETIC_SECRET: unsupported})
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_JSON_INVALID")


@pytest.mark.parametrize("payload,limit", [(b"", 0), (b"opaque\x00\xff", 8), (b"1234", 4)])
def test_bounded_reader_accepts_exact_limits_and_opaque_bytes_without_writes(
    tmp_path: Path, payload: bytes, limit: int
) -> None:
    source = tmp_path / "synthetic.bin"
    source.write_bytes(payload)
    before = source.stat()
    assert external_review._read_bounded_file(source, limit) == payload
    assert source.read_bytes() == payload
    after = source.stat()
    assert (after.st_size, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == [source.name]


@pytest.mark.parametrize("kind", ["missing", "directory", "oversized"])
def test_bounded_reader_refuses_unreadable_nonregular_and_oversized_sources(
    tmp_path: Path, kind: str
) -> None:
    source = tmp_path / "synthetic.bin"
    if kind == "directory":
        source.mkdir()
    elif kind == "oversized":
        source.write_bytes(b"12345")
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, 4)
    assert_safe_error(
        caught.value,
        {
            "missing": "EXTERNAL_REVIEW_INPUT_UNREADABLE",
            "directory": "EXTERNAL_REVIEW_PATH_INVALID",
            "oversized": "EXTERNAL_REVIEW_SIZE_LIMIT",
        }[kind],
    )


@pytest.mark.parametrize("replace_on_open", [1, 2], ids=["first-handle", "second-handle"])
def test_bounded_reader_detects_replacement_before_each_handle_identity_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replace_on_open: int
) -> None:
    source = tmp_path / "synthetic.bin"
    source.write_bytes(b"same-size")
    replacement = tmp_path / "synthetic-replacement.bin"
    replacement.write_bytes(b"same-size")
    original_open = Path.open
    calls = 0

    def replace_before_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        if self == external_review._io_path(source) and args and args[0] == "rb":
            calls += 1
            if calls == replace_on_open:
                os.replace(replacement, source)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_before_open)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, 32)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_INPUT_CHANGED")
    assert calls == replace_on_open
    assert not replacement.exists()


def test_bounded_reader_stops_growth_at_limit_plus_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "synthetic.bin"
    source.write_bytes(b"123")
    original_open = Path.open
    triggered = False

    class GrowingReader:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> GrowingReader:
            return self

        def __exit__(self, *args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return int(self.stream.fileno())

        def read(self, limit: int) -> bytes:
            nonlocal triggered
            triggered = True
            assert limit == 5
            with original_open(source, "ab") as writer:
                writer.write(b"45")
            return bytes(self.stream.read(limit))

    def grow_when_read(self: Path, *args: Any, **kwargs: Any) -> Any:
        stream = original_open(self, *args, **kwargs)
        if self == external_review._io_path(source) and args and args[0] == "rb":
            return GrowingReader(stream)
        return stream

    monkeypatch.setattr(Path, "open", grow_when_read)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, 4)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_SIZE_LIMIT")
    assert triggered


@pytest.mark.parametrize(
    "reference",
    [
        "https://example.invalid/%2525252541/report",
        "https://example.invalid/%GG/report",
        "https://example.invalid:443/report",
        "https://example.invalid/%40secret/report",
        "https://example.invalid/report?token=SYNTHETIC_UNIT_INPUT_SECRET",
        "https://example.invalid/report#SYNTHETIC_UNIT_INPUT_SECRET",
    ],
)
def test_encoded_or_sensitive_url_boundaries_refuse_without_git(reference: str) -> None:
    with pytest.raises(ContractError) as caught:
        external_review._https_reference(reference)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_REFERENCE_INVALID")
