"""Evidence handoffs preserve bytes and reject ambiguous or unsafe archive inputs."""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import struct
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tools.evidence import bundle as subject


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    repo = tmp_path / "repo"
    task = repo / ".ai" / "tasks" / "TASK-0001"
    task.mkdir(parents=True)
    (repo / ".git").mkdir()
    raw = tmp_path / "raw"
    raw.mkdir()
    (task / "spec.md").write_bytes(b"Git checkout text\n")
    (raw / "evidence.json").write_bytes(b'{\r\n  "result": "ok"\r\n}\r\n')
    (raw / "not-selected.secret").write_bytes(b"must not be read or copied")
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps(
            {
                "version": 1,
                "files": [
                    {"kind": "git-text", "path": "spec.md"},
                    {"kind": "runtime-original", "path": "evidence.json"},
                ],
            }
        ),
        encoding="utf-8",
    )
    return {
        "repo": repo,
        "task": task,
        "raw": raw,
        "selection": selection,
        "output": tmp_path / "bundle.zip",
    }


def export(inputs: dict[str, Path], **kwargs: Any) -> dict[str, Any]:
    return subject.export_bundle(
        inputs["task"], inputs["selection"], inputs["output"], inputs["raw"], **kwargs
    )


def rewrite_archive(path: Path, *, transform: Any) -> None:
    with zipfile.ZipFile(path) as archive:
        content = {name: archive.read(name) for name in archive.namelist()}
    transform(content)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in content.items():
            archive.writestr(name, data)


def rewrite_manifest(path: Path, transform: Any) -> None:
    def update(content: dict[str, bytes]) -> None:
        manifest = json.loads(content["manifest.json"])
        transform(manifest)
        content["manifest.json"] = json.dumps(manifest).encode()

    rewrite_archive(path, transform=update)


def test_roundtrip_preserves_selected_bytes_and_never_leaks_root_paths(
    inputs: dict[str, Path],
) -> None:
    original = (inputs["raw"] / "evidence.json").read_bytes()
    result = export(inputs)
    assert result["status"] == "EXPORTED"
    assert result["files"] == 2
    assert result["source_authenticated"] is False
    assert result["governance_effect"] == "none"
    with zipfile.ZipFile(inputs["output"]) as archive:
        assert set(archive.namelist()) == {
            "manifest.json",
            "git-text/spec.md",
            "runtime-original/evidence.json",
        }
        assert archive.read("runtime-original/evidence.json") == original
        manifest = archive.read("manifest.json")
        assert str(inputs["raw"]).encode() not in manifest
        entries = json.loads(manifest)["files"]
        assert entries[1]["sha256"] == hashlib.sha256(original).hexdigest()
    assert (inputs["raw"] / "evidence.json").read_bytes() == original
    before = set(inputs["output"].parent.iterdir())
    verified = subject.verify_bundle(inputs["output"], result["bundle_sha256"])
    assert verified["status"] == "VERIFIED"
    assert verified["expected_digest_matched"] is True
    assert set(inputs["output"].parent.iterdir()) == before


def test_git_text_label_does_not_normalize_checkout_bytes(inputs: dict[str, Path]) -> None:
    (inputs["task"] / "spec.md").write_bytes(b"checkout\r\n")
    export(inputs)
    with zipfile.ZipFile(inputs["output"]) as archive:
        assert archive.read("git-text/spec.md") == b"checkout\r\n"


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "/secret",
        "dir/../file",
        "dir//file",
        "dir/./file",
        "C:/secret",
        "dir\\file",
        "file:stream",
        "NUL",
        "con.txt",
        "dir/COM1",
        "file.",
        "file ",
        "x\x00y",
    ],
)
def test_reject_unsafe_selected_paths_before_creating_output(
    inputs: dict[str, Path], path: str
) -> None:
    inputs["selection"].write_text(
        json.dumps({"version": 1, "files": [{"kind": "git-text", "path": path}]}),
        encoding="utf-8",
    )
    with pytest.raises(subject.BundleError, match="UNSAFE_PATH"):
        export(inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize("location", ["repo", "task", "raw"])
def test_output_must_be_outside_source_roots_and_repository(
    inputs: dict[str, Path], location: str
) -> None:
    inputs["output"] = inputs[location] / "bundle.zip"
    with pytest.raises(subject.BundleError, match="OUTPUT_MUST_BE_OUTSIDE"):
        export(inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize("worktree", [False, True])
def test_external_sources_cannot_export_into_an_unrelated_repository(
    inputs: dict[str, Path], worktree: bool
) -> None:
    external_task = inputs["output"].parent / "external-task-staging"
    external_task.mkdir()
    (external_task / "spec.md").write_bytes(b"external selected Git text\n")
    inputs["task"] = external_task
    unrelated = inputs["output"].parent / "unrelated-repository"
    unrelated.mkdir()
    if worktree:
        (unrelated / ".git").write_text("gitdir: uninspected-private-target\n", encoding="utf-8")
    else:
        (unrelated / ".git").mkdir()
    output_parent = unrelated / "nested"
    output_parent.mkdir()
    inputs["output"] = output_parent / "must-not-be-created.zip"
    with pytest.raises(subject.BundleError, match="OUTPUT_MUST_BE_OUTSIDE"):
        export(inputs)
    assert list(output_parent.iterdir()) == []


def test_git_marker_is_inspected_without_following_it(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = inputs["output"].parent / "marker-link-repository"
    repository.mkdir()
    marker = repository / ".git"
    try:
        marker.symlink_to(repository / "nonexistent-target", target_is_directory=True)
    except OSError:
        pytest.skip("host cannot create symlinks")
    original_stat = Path.stat

    def never_follow_marker(path: Path, **kwargs: Any) -> Any:
        if path == marker and kwargs.get("follow_symlinks", True):
            pytest.fail("Git marker target was followed")
        return original_stat(path, **kwargs)

    monkeypatch.setattr(Path, "stat", never_follow_marker)
    assert subject._has_git_marker(repository)
    output = repository / "must-not-be-created.zip"
    with pytest.raises(subject.BundleError, match="OUTPUT_MUST_BE_OUTSIDE"):
        subject._output_path(output, [inputs["task"], inputs["raw"]])
    # A source repository's marker is inspected by the same non-following helper.
    assert subject._output_path(inputs["output"], [repository]) == inputs["output"]
    assert not output.exists()


def test_export_never_overwrites_an_existing_bundle(inputs: dict[str, Path]) -> None:
    inputs["output"].write_bytes(b"existing handoff")
    with pytest.raises(subject.BundleError, match="OUTPUT_EXISTS"):
        export(inputs)
    assert inputs["output"].read_bytes() == b"existing handoff"


@pytest.mark.parametrize(
    "name", ["target.zip:stream", "NUL", "COM1.zip", "bundle.zip.", "bundle.zip "]
)
def test_output_basename_is_rejected_before_filesystem_access(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    output = inputs["output"].parent / name
    monkeypatch.setattr(Path, "open", lambda *a, **kw: pytest.fail("unsafe output opened"))
    monkeypatch.setattr(Path, "lstat", lambda _: pytest.fail("unsafe output inspected"))
    with pytest.raises(subject.BundleError, match="UNSAFE_PATH"):
        subject._output_path(output, [inputs["task"], inputs["raw"]])


def test_raw_directory_is_required_only_when_selected(inputs: dict[str, Path]) -> None:
    with pytest.raises(subject.BundleError, match="RAW_DIR_REQUIRED"):
        subject.export_bundle(inputs["task"], inputs["selection"], inputs["output"])
    selection = json.loads(inputs["selection"].read_text())
    selection["files"] = selection["files"][:1]
    inputs["selection"].write_text(json.dumps(selection), encoding="utf-8")
    assert (
        subject.export_bundle(inputs["task"], inputs["selection"], inputs["output"])["files"] == 1
    )


@pytest.mark.parametrize("parent_link", [False, True])
def test_symlinks_are_rejected_even_for_explicitly_selected_files(
    inputs: dict[str, Path], parent_link: bool
) -> None:
    path = inputs["raw"] / ("linked" if parent_link else "linked.json")
    target = inputs["task"] if parent_link else inputs["task"] / "spec.md"
    try:
        path.symlink_to(target, target_is_directory=parent_link)
    except OSError:
        pytest.skip("host cannot create symlinks")
    selected = "linked/spec.md" if parent_link else "linked.json"
    inputs["selection"].write_text(
        json.dumps({"version": 1, "files": [{"kind": "runtime-original", "path": selected}]}),
        encoding="utf-8",
    )
    with pytest.raises(subject.BundleError, match="LINK_NOT_ALLOWED"):
        export(inputs)
    assert not inputs["output"].exists()


def test_file_digest_detects_modified_payload(inputs: dict[str, Path]) -> None:
    export(inputs)
    rewrite_archive(
        inputs["output"],
        transform=lambda content: content.update({"git-text/spec.md": b"Xit checkout text\n"}),
    )
    with pytest.raises(subject.BundleError, match="FILE_DIGEST_MISMATCH"):
        subject.verify_bundle(inputs["output"])


def test_source_change_during_export_is_detected_and_partial_output_removed(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    original_open = zipfile.ZipFile.open

    def changing_open(archive: Any, name: Any, mode: str = "r", **kwargs: Any) -> Any:
        if mode == "w" and name == "git-text/spec.md":
            (inputs["task"] / "spec.md").write_bytes(b"changed while exporting\n")
        return original_open(archive, name, mode, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", changing_open)
    with pytest.raises(subject.BundleError, match="SOURCE_CHANGED_DURING_EXPORT"):
        export(inputs)
    assert not inputs["output"].exists()


def test_atomic_source_replacement_is_not_certified_as_the_original(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source = inputs["task"] / "spec.md"
    initial = source.stat()
    replacement = inputs["output"].parent / "replacement.md"
    replacement.write_bytes(b"X" * initial.st_size)
    os.utime(replacement, ns=(initial.st_atime_ns, initial.st_mtime_ns))
    original_plain = subject._plain_path
    visits = 0

    def replace_after_read(path: Path, *, directory: bool = False) -> Path:
        nonlocal visits
        if path == source:
            visits += 1
            if visits == 3:
                # A new inode with identical size/time, after the source FD closes.
                replacement.replace(source)
        return original_plain(path, directory=directory)

    monkeypatch.setattr(subject, "_plain_path", replace_after_read)
    with pytest.raises(subject.BundleError, match="SOURCE_CHANGED_DURING_EXPORT"):
        export(inputs)
    assert source.read_bytes() == b"X" * initial.st_size
    assert not inputs["output"].exists()


def test_actual_total_budget_is_enforced_before_writing_grown_sources(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = [inputs["task"] / "spec.md", inputs["raw"] / "evidence.json"]
    for path in sources:
        path.write_bytes(b"xx")
    monkeypatch.setattr(subject, "MAX_TOTAL_BYTES", 10)
    original_plain = subject._plain_path
    visits: dict[Path, int] = {}
    written: list[int] = []
    original_write = zipfile._ZipWriteFile.write

    def grow_before_open(path: Path, *, directory: bool = False) -> Path:
        if path in sources:
            visits[path] = visits.get(path, 0) + 1
            if visits[path] == 2:
                path.write_bytes(b"expanded")
        return original_plain(path, directory=directory)

    def count_write(target: Any, data: bytes) -> Any:
        written.append(len(data))
        return original_write(target, data)

    monkeypatch.setattr(subject, "_plain_path", grow_before_open)
    monkeypatch.setattr(zipfile._ZipWriteFile, "write", count_write)
    with pytest.raises(subject.BundleError, match="TOTAL_TOO_LARGE"):
        export(inputs)
    assert sum(written) == 8
    assert not inputs["output"].exists()


def test_bundle_change_during_verification_is_detected(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    export(inputs)
    original_verify = subject._verify_archive

    def changing_verify(archive: zipfile.ZipFile) -> tuple[int, int]:
        result = original_verify(archive)
        with inputs["output"].open("ab") as output:
            output.write(b"changed during verification")
        return result

    monkeypatch.setattr(subject, "_verify_archive", changing_verify)
    with pytest.raises(subject.BundleError, match="BUNDLE_CHANGED_DURING_VERIFICATION"):
        subject.verify_bundle(inputs["output"])


def test_nul_in_zip_name_cannot_hide_a_suffix(inputs: dict[str, Path]) -> None:
    export(inputs)
    contents = inputs["output"].read_bytes()
    inputs["output"].write_bytes(contents.replace(b"git-text/spec.md", b"git-text/spe\x00.md"))
    with pytest.raises(subject.BundleError, match="UNSAFE_PATH"):
        subject.verify_bundle(inputs["output"])


def test_malformed_compression_returns_path_free_cli_error(
    inputs: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    export(inputs)
    with zipfile.ZipFile(inputs["output"]) as archive:
        member = archive.getinfo("git-text/spec.md")
        data_offset = member.header_offset + 30 + len(member.filename.encode()) + len(member.extra)
    content = bytearray(inputs["output"].read_bytes())
    content[data_offset] = 0xFF  # Invalid deflate block type.
    inputs["output"].write_bytes(content)
    assert subject.main(["verify", str(inputs["output"])]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.err)["code"] == "IO_OR_ZIP_ERROR"
    assert str(inputs["output"]) not in captured.err


def test_invalid_utf8_zip_filename_returns_path_free_cli_error(
    inputs: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    export(inputs)
    content = bytearray(inputs["output"].read_bytes())
    central = struct.unpack_from("<L", content, len(content) - 6)[0]
    flags = struct.unpack_from("<H", content, central + 8)[0]
    struct.pack_into("<H", content, central + 8, flags | 0x800)
    content[central + 46] = 0xFF
    inputs["output"].write_bytes(content)
    assert subject.main(["verify", str(inputs["output"])]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.err)["code"] == "IO_OR_ZIP_ERROR"
    assert str(inputs["output"]) not in captured.err


@pytest.mark.parametrize(
    "data",
    [b"{", b"\xff", b'{"version":' + b"1" * 5000 + b',"files":[]}'],
    ids=["syntax", "utf8", "integer_digit_limit"],
)
def test_invalid_selection_json_never_leaks_parser_errors(
    inputs: dict[str, Path], capsys: pytest.CaptureFixture[str], data: bytes
) -> None:
    inputs["selection"].write_bytes(data)
    assert (
        subject.main(
            [
                "export",
                "--task-dir",
                str(inputs["task"]),
                "--raw-dir",
                str(inputs["raw"]),
                "--selection",
                str(inputs["selection"]),
                "--output",
                str(inputs["output"]),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert json.loads(captured.err)["code"] == "INVALID_JSON"
    assert str(inputs["selection"]) not in captured.err
    assert not inputs["output"].exists()


@pytest.mark.parametrize("mutation", ["add", "remove", "traversal"])
def test_archive_members_must_match_manifest_exactly(
    inputs: dict[str, Path], mutation: str
) -> None:
    export(inputs)

    def change(content: dict[str, bytes]) -> None:
        if mutation == "remove":
            del content["git-text/spec.md"]
        else:
            content["../escape" if mutation == "traversal" else "extra.txt"] = b"extra"

    rewrite_archive(inputs["output"], transform=change)
    with pytest.raises(subject.BundleError, match="MEMBER_SET_MISMATCH|UNSAFE_PATH"):
        subject.verify_bundle(inputs["output"])
    assert not (inputs["output"].parent / "escape").exists()


def test_duplicate_archive_members_are_rejected(inputs: dict[str, Path]) -> None:
    export(inputs)
    with zipfile.ZipFile(inputs["output"], "a") as archive:
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("git-text/spec.md", b"replacement")
    with pytest.raises(subject.BundleError, match="DUPLICATE_ZIP_MEMBER"):
        subject.verify_bundle(inputs["output"])


def test_symlink_archive_entry_is_rejected(inputs: dict[str, Path]) -> None:
    export(inputs)
    with zipfile.ZipFile(inputs["output"], "a") as archive:
        info = zipfile.ZipInfo("linked")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "elsewhere")
    with pytest.raises(subject.BundleError, match="INVALID_ZIP_FILE_TYPE"):
        subject.verify_bundle(inputs["output"])


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("size", True, "INVALID_FILE_SIZE"),
        ("size", -1, "INVALID_FILE_SIZE"),
        ("size", 999, "FILE_SIZE_MISMATCH"),
        ("sha256", "a" * 64 + "\n", "INVALID_DIGEST"),
        ("kind", "unknown", "INVALID_KIND"),
        ("private_root", "/private", "INVALID_FIELDS"),
    ],
)
def test_manifest_rejects_invalid_or_unknown_entry_fields(
    inputs: dict[str, Path], field: str, value: Any, code: str
) -> None:
    export(inputs)
    rewrite_manifest(inputs["output"], lambda data: data["files"][0].update({field: value}))
    with pytest.raises(subject.BundleError, match=code):
        subject.verify_bundle(inputs["output"])


@pytest.mark.parametrize("field", ["private_root", "gate_pass"])
def test_manifest_rejects_unknown_top_level_fields(inputs: dict[str, Path], field: str) -> None:
    export(inputs)
    rewrite_manifest(inputs["output"], lambda data: data.update({field: "unsupported"}))
    with pytest.raises(subject.BundleError, match="INVALID_FIELDS"):
        subject.verify_bundle(inputs["output"])


def test_selection_rejects_ambiguous_json_and_case_collisions(inputs: dict[str, Path]) -> None:
    inputs["selection"].write_text('{"version": 1, "version": 1, "files": []}', encoding="utf-8")
    with pytest.raises(subject.BundleError, match="DUPLICATE_JSON_KEY"):
        export(inputs)
    inputs["selection"].write_text(
        json.dumps(
            {
                "version": 1,
                "files": [
                    {"kind": "git-text", "path": "spec.md"},
                    {"kind": "git-text", "path": "SPEC.md"},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(subject.BundleError, match="DUPLICATE_PATH"):
        export(inputs)


def test_expected_bundle_digest_is_a_separate_trust_input(inputs: dict[str, Path]) -> None:
    result = export(inputs)
    with pytest.raises(subject.BundleError, match="BUNDLE_DIGEST_MISMATCH"):
        subject.verify_bundle(inputs["output"], "0" * 64)
    with pytest.raises(subject.BundleError, match="INVALID_EXPECTED_DIGEST"):
        subject.verify_bundle(inputs["output"], "bad")
    assert subject.verify_bundle(inputs["output"])["expected_digest_matched"] is False
    assert result["bundle_sha256"] == hashlib.sha256(inputs["output"].read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("fake_small_count", "INVALID_CENTRAL_DIRECTORY"),
        ("too_many_members", "INVALID_MEMBER_COUNT"),
        ("huge_directory", "INVALID_CENTRAL_DIRECTORY"),
        ("zip64_count", "ZIP64_NOT_SUPPORTED"),
        ("trailing_bytes", "UNSUPPORTED_ZIP_LAYOUT"),
        ("wrong_central_header", "INVALID_CENTRAL_DIRECTORY"),
    ],
)
def test_archive_preflight_bounds_central_directory_before_zipfile_allocation(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch, mutation: str, code: str
) -> None:
    export(inputs)
    content = bytearray(inputs["output"].read_bytes())
    eocd = len(content) - 22
    central_offset = struct.unpack_from("<L", content, eocd + 16)[0]
    if mutation == "fake_small_count":
        struct.pack_into("<2H", content, eocd + 8, 2, 2)
    elif mutation == "too_many_members":
        struct.pack_into("<2H", content, eocd + 8, 10_002, 10_002)
    elif mutation == "huge_directory":
        monkeypatch.setattr(subject, "MAX_CENTRAL_BYTES", 8)
    elif mutation == "zip64_count":
        struct.pack_into("<2H", content, eocd + 8, 0xFFFF, 0xFFFF)
    elif mutation == "trailing_bytes":
        content.extend(b"unexpected trailing data")
    else:
        content[central_offset] = 0
    inputs["output"].write_bytes(content)
    monkeypatch.setattr(
        subject.zipfile, "ZipFile", lambda *a, **kw: pytest.fail("unbounded ZIP parser invoked")
    )
    with pytest.raises(subject.BundleError, match=code):
        subject.verify_bundle(inputs["output"])


def test_small_forced_zip64_archive_is_rejected_before_zipfile(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    with zipfile.ZipFile(inputs["output"], "w") as archive:
        with archive.open("data", "w", force_zip64=True) as member:
            member.write(b"small but ZIP64")
        archive.writestr("manifest.json", b"{}")
    monkeypatch.setattr(
        subject.zipfile, "ZipFile", lambda *a, **kw: pytest.fail("ZIP64 parser invoked")
    )
    with pytest.raises(subject.BundleError, match="ZIP64_NOT_SUPPORTED"):
        subject.verify_bundle(inputs["output"])


@pytest.mark.parametrize(
    ("extra", "code"),
    [
        (b"\xfe\xca\x01\x00x", None),
        (b"x", "INVALID_CENTRAL_DIRECTORY"),
        (b"\xfe\xca\x09\x00x", "INVALID_CENTRAL_DIRECTORY"),
        (b"\x01\x00\x00\x00", "ZIP64_NOT_SUPPORTED"),
    ],
)
def test_central_directory_extra_fields_are_parsed_with_bounds(
    inputs: dict[str, Path], extra: bytes, code: str | None
) -> None:
    export(inputs)
    with zipfile.ZipFile(inputs["output"]) as archive:
        content = [(info, archive.read(info.filename)) for info in archive.infolist()]
    content[0][0].extra = extra
    with zipfile.ZipFile(inputs["output"], "w") as archive:
        for info, data in content:
            archive.writestr(info, data)
    if code is None:
        assert subject.verify_bundle(inputs["output"])["status"] == "VERIFIED"
    else:
        with pytest.raises(subject.BundleError, match=code):
            subject.verify_bundle(inputs["output"])


@pytest.mark.parametrize("field", ["compressed_size", "disk", "length"])
def test_central_directory_rejects_invalid_member_metadata_before_allocating(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    export(inputs)
    content = bytearray(inputs["output"].read_bytes())
    start = struct.unpack_from("<L", content, len(content) - 6)[0]
    if field == "compressed_size":
        struct.pack_into("<L", content, start + 20, 0xFFFFFFFF)
        code = "ZIP64_NOT_SUPPORTED"
    elif field == "disk":
        struct.pack_into("<H", content, start + 34, 1)
        code = "INVALID_CENTRAL_DIRECTORY"
    else:
        struct.pack_into("<H", content, start + 28, 0xFFFF)
        code = "INVALID_CENTRAL_DIRECTORY"
    inputs["output"].write_bytes(content)
    monkeypatch.setattr(
        subject.zipfile, "ZipFile", lambda *a, **kw: pytest.fail("unbounded ZIP parser invoked")
    )
    with pytest.raises(subject.BundleError, match=code):
        subject.verify_bundle(inputs["output"])


@pytest.mark.parametrize("short_size", [22, 46])
def test_concurrent_archive_short_read_has_a_stable_cli_error(
    inputs: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    short_size: int,
) -> None:
    export(inputs)
    content = inputs["output"].read_bytes()
    original_preflight = subject._preflight_zip

    class ShortRead(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            data = super().read(size)
            return data[:-1] if size == short_size else data

    def truncate_during_read(source: Any, size: int) -> None:
        original_preflight(ShortRead(content), size)

    monkeypatch.setattr(subject, "_preflight_zip", truncate_during_read)
    assert subject.main(["verify", str(inputs["output"])]) == 1
    expected = "IO_OR_ZIP_ERROR" if short_size == 22 else "INVALID_CENTRAL_DIRECTORY"
    assert json.loads(capsys.readouterr().err)["code"] == expected


@pytest.mark.parametrize("short_size", [4, 5, 6])
def test_central_header_short_prefix_is_rejected_before_indexing(
    inputs: dict[str, Path], short_size: int
) -> None:
    export(inputs)
    content = inputs["output"].read_bytes()

    class ShortCentralHeader(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            data = super().read(size)
            return data[:short_size] if size == 46 else data

    with pytest.raises(subject.BundleError, match="INVALID_CENTRAL_DIRECTORY"):
        subject._preflight_zip(ShortCentralHeader(content), len(content))


def test_ordinary_zip_limit_has_a_stable_cli_error_and_removes_partial_output(
    inputs: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 32)
    assert (
        subject.main(
            [
                "export",
                "--task-dir",
                str(inputs["task"]),
                "--raw-dir",
                str(inputs["raw"]),
                "--selection",
                str(inputs["selection"]),
                "--output",
                str(inputs["output"]),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert json.loads(captured.err)["code"] == "IO_OR_ZIP_ERROR"
    assert str(inputs["output"]) not in captured.err
    assert not inputs["output"].exists()


def test_tiny_archive_is_rejected_before_zipfile(tmp_path: Path) -> None:
    bundle = tmp_path / "tiny.zip"
    bundle.write_bytes(b"PK")
    with pytest.raises(subject.BundleError, match="INVALID_ARCHIVE_SIZE"):
        subject.verify_bundle(bundle)


@pytest.mark.parametrize(
    "value",
    [
        r"\\review-no-network\share",
        r"\\?\C:\private",
        r"\\.\C:\private",
        r"C:relative",
        r"\relative",
    ],
)
def test_windows_nonlocal_path_syntax_is_rejected_before_metadata(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subject, "WINDOWS", True)
    monkeypatch.setattr(Path, "lstat", lambda _: pytest.fail("network metadata accessed"))
    monkeypatch.setattr(subject, "_drive_type", lambda _: pytest.fail("invalid drive probed"))
    with pytest.raises(subject.BundleError, match="NONLOCAL_PATH"):
        subject._plain_path(Path(value))


@pytest.mark.parametrize("drive_type", [0, 1, 4])
def test_windows_mapped_network_and_unknown_drives_fail_closed(
    monkeypatch: pytest.MonkeyPatch, drive_type: int
) -> None:
    monkeypatch.setattr(subject, "_drive_type", lambda _: drive_type)
    monkeypatch.setattr(Path, "lstat", lambda _: pytest.fail("network metadata accessed"))
    with pytest.raises(subject.BundleError, match="NONLOCAL_PATH"):
        subject._require_local_windows_path(r"Z:\private")


@pytest.mark.parametrize("drive_type", [2, 3, 5, 6])
def test_windows_local_drive_types_are_supported(
    monkeypatch: pytest.MonkeyPatch, drive_type: int
) -> None:
    monkeypatch.setattr(subject, "_drive_type", lambda _: drive_type)
    subject._require_local_windows_path(r"C:\local")


def test_size_limits_bound_json_and_decompressed_content(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    export(inputs)
    monkeypatch.setattr(subject, "MAX_JSON_BYTES", 8)
    with pytest.raises(subject.BundleError, match="CONTENT_TOO_LARGE"):
        subject.verify_bundle(inputs["output"])
    with pytest.raises(subject.BundleError, match="JSON_TOO_LARGE"):
        subject._json(b" " * 9)
    with pytest.raises(subject.BundleError, match="CONTENT_TOO_LARGE"):
        subject._digest(io.BytesIO(b"x" * 10), 9)


def test_export_limits_and_failed_export_leave_no_partial_bundle(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subject, "MAX_FILE_BYTES", 1)
    with pytest.raises(subject.BundleError, match="CONTENT_TOO_LARGE"):
        export(inputs)
    assert not inputs["output"].exists()
    monkeypatch.setattr(subject, "MAX_FILE_BYTES", 1024)
    monkeypatch.setattr(subject, "MAX_TOTAL_BYTES", 1)
    with pytest.raises(subject.BundleError, match="TOTAL_TOO_LARGE"):
        export(inputs)
    monkeypatch.setattr(subject, "MAX_TOTAL_BYTES", 1024)

    def fail(*args: Any, **kwargs: Any) -> None:
        raise subject.BundleError("SIMULATED_WRITE_FAILURE")

    monkeypatch.setattr(zipfile.ZipFile, "writestr", fail)
    with pytest.raises(subject.BundleError, match="SIMULATED_WRITE_FAILURE"):
        export(inputs)
    assert not inputs["output"].exists()


def test_cli_success_and_bounded_path_free_error(
    inputs: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        subject.main(
            [
                "export",
                "--task-dir",
                str(inputs["task"]),
                "--raw-dir",
                str(inputs["raw"]),
                "--selection",
                str(inputs["selection"]),
                "--output",
                str(inputs["output"]),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "EXPORTED"
    assert subject.main(["verify", str(inputs["output"]), "--expected-sha256", "bad"]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.err)["code"] == "INVALID_EXPECTED_DIGEST"
    assert str(inputs["output"]) not in captured.err
    assert subject.main(["verify", str(inputs["raw"] / "private-missing.zip")]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.err)["code"] == "IO_OR_ZIP_ERROR"
    assert "private-missing" not in captured.err
