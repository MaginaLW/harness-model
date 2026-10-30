"""Checks for the distributable, repository-independent resource bundle."""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import warnings
import zipfile
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

import aiflow
from aiflow.contracts import SCHEMA_FILES
from aiflow.policy import POLICY_FILES

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_SOURCE = ROOT / "src/aiflow/resource_bundle.py"

# Only an absent source file is a skip. A broken or mismatched import fails.
try:
    BUNDLE_SOURCE.lstat()
except FileNotFoundError:
    pytestmark = pytest.mark.skip(reason="resource bundle is not implemented on this baseline")
else:
    resource_bundle = importlib.import_module("aiflow.resource_bundle")
    if resource_bundle.__file__ is None or Path(resource_bundle.__file__).resolve() != (
        BUNDLE_SOURCE.resolve()
    ):
        raise ImportError("resource bundle is not loaded from the tested checkout")
    _source_file = resource_bundle._source_file
    build_bundle = resource_bundle.build_bundle
    read_bundle = resource_bundle.read_bundle

SCHEMAS = {
    "approval",
    "ask-options",
    "classification",
    "decision-unit",
    "event",
    "evidence",
    "mutation-evidence",
    "mutation-manifest",
    "observation",
    "observation-decision",
    "policy",
    "review-context",
    "review-record",
    "task",
    "verifier-context",
}
POLICIES = {"hard-rules", "permissions", "routing", "verification-levels"}
PATHS = (
    {f"schemas/{name}.schema.json" for name in SCHEMAS}
    | {f"policy/{name}.yaml" for name in POLICIES}
    | {"templates/spec.md"}
)


@pytest.fixture
def source(tmp_path: Path) -> Path:
    """A source root containing only the bundle's documented inputs."""
    root = tmp_path / "source"
    root.mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", root / "pyproject.toml")
    (root / "src/aiflow").mkdir(parents=True)
    shutil.copyfile(ROOT / "src/aiflow/__init__.py", root / "src/aiflow/__init__.py")
    for relative in PATHS:
        target = root / ".ai" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        original = (ROOT / ".ai" / relative).read_bytes()
        target.write_bytes(original.replace(b"\r\n", b"\n"))
    return root


def write_bundle(root: Path, manifest: dict, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True)
    for relative, data in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def directory_link(link: Path, target: Path, kind: str) -> None:
    if kind == "symlink":
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"directory symlinks unavailable: {error}")
    elif sys.platform == "win32":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode:
            pytest.skip("directory junctions unavailable")
    else:
        pytest.skip("junctions are Windows-specific")


def remove_directory_link(link: Path, kind: str) -> None:
    if kind == "junction":
        os.rmdir(link)
    else:
        link.unlink()


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("kind", ["symlink", "junction"])
@pytest.mark.parametrize("ancestor", [".ai", ".ai/schemas", "src/aiflow", "root"])
def test_source_links_are_rejected_without_changing_outside_files(
    source: Path, tmp_path: Path, kind: str, ancestor: str
) -> None:
    if ancestor == "root":
        link, outside = tmp_path / "source-link", source
        call_root = link
    else:
        link, outside = source / ancestor, tmp_path / "outside"
        link.rename(outside)
        call_root = source
    before = tree_bytes(outside)
    directory_link(link, outside, kind)
    try:
        with pytest.raises(ValueError):
            build_bundle(call_root)
        assert tree_bytes(outside) == before
    finally:
        remove_directory_link(link, kind)


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_bundle_root_link_is_rejected_without_changing_outside_files(
    source: Path, tmp_path: Path, kind: str
) -> None:
    outside, link = tmp_path / "outside-bundle", tmp_path / "bundle-link"
    write_bundle(outside, *build_bundle(source))
    before = tree_bytes(outside)
    directory_link(link, outside, kind)
    try:
        with pytest.raises(ValueError):
            read_bundle(link)
        assert tree_bytes(outside) == before
    finally:
        remove_directory_link(link, kind)


def test_bundle_is_exact_and_manifest_hashes_canonical_bytes(source: Path) -> None:
    manifest, files = build_bundle(source)
    assert set(files) == PATHS
    assert {f"schemas/{name}" for name in SCHEMA_FILES.values()} == {
        path for path in PATHS if path.startswith("schemas/")
    }
    assert {f"policy/{name}" for name in POLICY_FILES} == {
        path for path in PATHS if path.startswith("policy/")
    }
    assert set(manifest) == {
        "schema_version",
        "bundle_version",
        "compatible_cli_versions",
        "policy_version",
        "files",
    }
    assert manifest["schema_version"] == "1.0"
    assert manifest["bundle_version"] == "1.0"
    assert manifest["compatible_cli_versions"] == ["0.2.0"]
    assert manifest["policy_version"] == "2.5.0"
    entries = manifest["files"]
    assert [entry["path"] for entry in entries] == sorted(PATHS)
    for entry in entries:
        path = entry["path"]
        assert set(entry) == {"path", "kind", "size", "sha256"}
        assert (
            entry["kind"]
            == {"schemas": "schema", "policy": "policy", "templates": "template"}[
                path.split("/", 1)[0]
            ]
        )
        assert entry["size"] == len(files[path])
        assert entry["sha256"] == hashlib.sha256(files[path]).hexdigest()
        assert b"\r" not in files[path]
        files[path].decode("utf-8")


def test_crlf_and_lf_source_produce_identical_bundle(source: Path) -> None:
    expected = build_bundle(source)
    for relative in PATHS:
        path = source / ".ai" / relative
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert build_bundle(source) == expected


@pytest.mark.parametrize("bad", [b"\xff", b"bad\rline\n"])
def test_invalid_utf8_or_bare_carriage_return_is_rejected(source: Path, bad: bytes) -> None:
    (source / ".ai/templates/spec.md").write_bytes(bad)
    with pytest.raises(ValueError):
        build_bundle(source)


def test_missing_resource_or_mismatched_policy_version_is_rejected(source: Path) -> None:
    path = source / ".ai/policy/routing.yaml"
    original = path.read_text(encoding="utf-8")
    path.unlink()
    with pytest.raises(ValueError):
        build_bundle(source)
    path.write_text(
        original.replace('policy_version: "2.5.0"', 'policy_version: "9.0.0"'), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        build_bundle(source)


@pytest.mark.parametrize(
    ("path", "bad"),
    [
        ("pyproject.toml", b"[project\n"),
        ("pyproject.toml", b'[project]\nversion = "9.0.0"\n'),
        ("src/aiflow/__init__.py", b"__version__ = \n"),
        ("src/aiflow/__init__.py", b'__version__ = "9.0.0"\n'),
    ],
)
def test_invalid_or_incompatible_project_version_is_rejected(
    source: Path, path: str, bad: bytes
) -> None:
    (source / path).write_bytes(bad)
    with pytest.raises(ValueError, match="(?:cannot verify|incompatible) CLI version"):
        build_bundle(source)


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (b"schema_version: [\n", "invalid Policy seed"),
        (b'policy_version: "2.5.0"\npolicy_version: "2.5.0"\n', "duplicate Policy key"),
        (b"- list\n", "incompatible Policy seed metadata"),
        (b'schema_version: "9.0"\n', "incompatible Policy seed metadata"),
    ],
)
def test_invalid_policy_seed_is_rejected(source: Path, bad: bytes, message: str) -> None:
    (source / ".ai/policy/routing.yaml").write_bytes(bad)
    with pytest.raises(ValueError, match=message):
        build_bundle(source)


def test_unreadable_source_resource_is_reported(
    source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.open
    denied = source / ".ai/templates/spec.md"

    def open_file(path: Path, *args: object, **kwargs: object) -> object:
        if path == denied:
            raise PermissionError("synthetic access refusal")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_file)
    with pytest.raises(ValueError, match="cannot read resource source"):
        build_bundle(source)


def test_source_requires_directory_ancestors_and_regular_files(source: Path) -> None:
    schema = source / ".ai/schemas/task.schema.json"
    schema.rename(source / "saved-schema")
    schema.mkdir()
    with pytest.raises(ValueError, match="resource file is not an ordinary file"):
        build_bundle(source)
    schema.rmdir()
    (source / "saved-schema").rename(schema)
    directory = source / ".ai/templates"
    directory.rename(source / "saved-templates")
    directory.write_bytes(b"not a directory")
    with pytest.raises(ValueError, match="resource directory is not a directory"):
        build_bundle(source)


@pytest.mark.parametrize(
    "relative",
    [
        "src/aiflow/../../../outside",
        ".ai/./schemas",
        ".ai//schemas",
        "/outside",
        "C:/outside",
        ".ai\\schemas/task.schema.json",
    ],
)
def test_source_rejects_unsafe_relative_paths_before_outside_access(
    source: Path, tmp_path: Path, relative: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.write_bytes(b"preserve\n")
    lstat = Path.lstat

    def guarded(path: Path) -> os.stat_result:
        if path == outside:
            pytest.fail("attempted to inspect outside file")
        return lstat(path)

    monkeypatch.setattr(Path, "lstat", guarded)
    with pytest.raises(ValueError, match="resource path is not a safe relative path"):
        _source_file(source, relative)
    assert outside.read_bytes() == b"preserve\n"


def test_bundle_reader_supports_zip_traversable(source: Path, tmp_path: Path) -> None:
    manifest, files = build_bundle(source)
    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("bundle/manifest.json", json.dumps(manifest))
        for path, data in files.items():
            archive.writestr(f"bundle/{path}", data)
    with zipfile.ZipFile(archive_path) as archive:
        assert read_bundle(zipfile.Path(archive, "bundle/")) == (manifest, files)


@contextmanager
def bounded_bundle(tmp_path: Path, storage: str, manifest: bytes, files: dict[str, bytes]):
    if storage == "filesystem":
        root = tmp_path / "bundle"
        root.mkdir()
        (root / "manifest.json").write_bytes(manifest)
        for path, data in files.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        yield root
    else:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("bundle/manifest.json", manifest)
            for path, data in files.items():
                archive.writestr(f"bundle/{path}", data)
        with zipfile.ZipFile(io.BytesIO(output.getvalue())) as archive:
            yield zipfile.Path(archive, "bundle/")


def track_bundle_reads(monkeypatch: pytest.MonkeyPatch, storage: str, limits: dict[str, int]):
    path_type = Path if storage == "filesystem" else zipfile.Path
    original_open = path_type.open
    counts: dict[str, int] = {}

    def guarded_open(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        depth = 0

        def wrap(method_name):
            original_read = getattr(stream, method_name)

            def guarded_read(*read_args, **read_kwargs):
                nonlocal depth
                depth += 1
                try:
                    result = original_read(*read_args, **read_kwargs)
                finally:
                    depth -= 1
                if depth == 0:
                    size = result if method_name == "readinto" else len(result)
                    counts[path.name] = counts.get(path.name, 0) + size
                    assert counts[path.name] <= limits[path.name] + 1
                    total = sum(count for name, count in counts.items() if name != "manifest.json")
                    assert total <= resource_bundle.MAX_BUNDLE_BYTES + 1
                return result

            monkeypatch.setattr(stream, method_name, guarded_read)

        for method_name in ("read", "read1", "readinto"):
            if hasattr(stream, method_name):
                wrap(method_name)
        return stream

    monkeypatch.setattr(path_type, "open", guarded_open)


@pytest.mark.parametrize("storage", ["filesystem", "zip"])
def test_manifest_size_is_limited(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, storage: str
) -> None:
    _, files = build_bundle(source)
    monkeypatch.setattr(resource_bundle, "MAX_MANIFEST_BYTES", 64)
    with bounded_bundle(tmp_path, storage, b" " * 256, files) as root:
        track_bundle_reads(monkeypatch, storage, {"manifest.json": 64})
        with pytest.raises(ValueError):
            read_bundle(root)


@pytest.mark.parametrize("storage", ["filesystem", "zip"])
@pytest.mark.parametrize("overflow", ["resource", "total"])
def test_declared_limits_reject_without_unbounded_reads(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, storage: str, overflow: str
) -> None:
    manifest, files = build_bundle(source)
    if overflow == "resource":
        monkeypatch.setattr(resource_bundle, "MAX_RESOURCE_BYTES", max(map(len, files.values())))
        manifest["files"][0]["size"] = resource_bundle.MAX_RESOURCE_BYTES + 1
        files[manifest["files"][0]["path"]] = b"x" * (resource_bundle.MAX_RESOURCE_BYTES + 100)
    else:
        monkeypatch.setattr(resource_bundle, "MAX_BUNDLE_BYTES", sum(map(len, files.values())) // 2)
    manifest_bytes = json.dumps(manifest).encode()
    with bounded_bundle(tmp_path, storage, manifest_bytes, files) as root:
        limits = {Path(path).name: resource_bundle.MAX_RESOURCE_BYTES for path in files}
        limits["manifest.json"] = resource_bundle.MAX_MANIFEST_BYTES
        track_bundle_reads(monkeypatch, storage, limits)
        with pytest.raises(ValueError):
            read_bundle(root)


@pytest.mark.parametrize("storage", ["filesystem", "zip"])
def test_resource_read_is_limited_by_resource_cap(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, storage: str
) -> None:
    manifest, files = build_bundle(source)
    target = "templates/spec.md"
    monkeypatch.setattr(resource_bundle, "MAX_RESOURCE_BYTES", max(map(len, files.values())))
    files[target] = b"x" * (resource_bundle.MAX_RESOURCE_BYTES + 100)
    with bounded_bundle(tmp_path, storage, json.dumps(manifest).encode(), files) as root:
        limits = {Path(path).name: resource_bundle.MAX_RESOURCE_BYTES for path in files}
        limits["manifest.json"] = resource_bundle.MAX_MANIFEST_BYTES
        track_bundle_reads(monkeypatch, storage, limits)
        with pytest.raises(ValueError):
            read_bundle(root)


@pytest.mark.parametrize("content", [b"x" * 129, b"\r\n" * 129])
def test_builder_limits_raw_and_normalized_resources(
    source: Path, monkeypatch: pytest.MonkeyPatch, content: bytes
) -> None:
    (source / "pyproject.toml").write_text('[project]\nversion = "0.2.0"\n', encoding="utf-8")
    (source / "src/aiflow/__init__.py").write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    for relative in PATHS:
        path = source / ".ai" / relative
        if relative.startswith("policy/"):
            data = (
                'schema_version: "1.0"\npolicy_version: "2.5.0"\n'
                f"policy_kind: {resource_bundle.POLICIES[path.name]}\n"
            ).encode()
        else:
            data = b"{}\n"
        path.write_bytes(data)
    monkeypatch.setattr(resource_bundle, "MAX_RESOURCE_BYTES", 128)
    monkeypatch.setattr(resource_bundle, "MAX_BUNDLE_BYTES", 4096)
    template = source / ".ai/templates/spec.md"
    for valid in (b"x" * 128, b"\r\n" * 128):
        template.write_bytes(valid)
        assert len(build_bundle(source)[1]["templates/spec.md"]) == 128
    template.write_bytes(content)
    with pytest.raises(ValueError, match="size limit"):
        build_bundle(source)


@pytest.mark.parametrize("conflict", ["resource", "manifest", "directory", "file_directory"])
def test_zip_duplicate_or_conflicting_paths_are_rejected(source: Path, conflict: str) -> None:
    manifest, files = build_bundle(source)
    output = io.BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(output, "w") as archive:
        warnings.filterwarnings("ignore", message="Duplicate name:", category=UserWarning)
        archive.writestr("bundle/manifest.json", json.dumps(manifest))
        archive.writestr("bundle/schemas/", b"")
        for path, data in files.items():
            archive.writestr(f"bundle/{path}", data)
        if conflict == "resource":
            archive.writestr("bundle/schemas/task.schema.json", files["schemas/task.schema.json"])
        elif conflict == "manifest":
            archive.writestr("bundle/manifest.json", json.dumps(manifest))
        elif conflict == "directory":
            archive.writestr("bundle/schemas/", b"")
        else:
            archive.writestr("bundle/schemas", b"file conflicts with directory")
    before = output.getvalue()
    with zipfile.ZipFile(io.BytesIO(before)) as archive:
        with pytest.raises(ValueError, match="bundle contains a duplicate path"):
            read_bundle(zipfile.Path(archive, "bundle/"))
    assert output.getvalue() == before


def test_bundle_rejects_incompatible_running_cli_version(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "bundle"
    write_bundle(root, *build_bundle(source))
    monkeypatch.setattr(aiflow, "__version__", "9.0.0")
    with pytest.raises(ValueError, match="bundle is incompatible with the running CLI version"):
        read_bundle(root)


@pytest.mark.parametrize(
    "change",
    [
        "missing_manifest",
        "missing_entry",
        "duplicate_entry",
        "unsafe_path",
        "absolute_path",
        "bad_hash",
        "bad_size",
        "bad_kind",
        "bad_schema_version",
        "bad_bundle_version",
        "bad_cli_version",
        "bad_policy_version",
        "extra_field",
        "duplicate_json_key",
        "invalid_json",
        "extra_directory",
        "invalid_entry",
    ],
)
def test_invalid_manifest_and_contents_are_rejected(
    source: Path, tmp_path: Path, change: str
) -> None:
    manifest, files = build_bundle(source)
    manifest = deepcopy(manifest)
    root = tmp_path / "bundle"
    write_bundle(root, manifest, files)
    entries = manifest["files"]
    first = entries[0]
    if change == "missing_manifest":
        (root / "manifest.json").unlink()
    elif change == "extra_directory":
        (root / "unexpected").mkdir()
    elif change == "missing_entry":
        entries.pop()
    elif change == "duplicate_entry":
        entries.append(deepcopy(first))
    elif change == "unsafe_path":
        first["path"] = "../outside"
    elif change == "absolute_path":
        first["path"] = "/outside"
    elif change == "bad_hash":
        first["sha256"] = "0" * 64
    elif change == "bad_size":
        first["size"] += 1
    elif change == "bad_kind":
        first["kind"] = "unknown"
    elif change == "bad_schema_version":
        manifest["schema_version"] = "9.0"
    elif change == "bad_bundle_version":
        manifest["bundle_version"] = "9.0"
    elif change == "bad_cli_version":
        manifest["compatible_cli_versions"] = ["9.0.0"]
    elif change == "bad_policy_version":
        manifest["policy_version"] = "9.0.0"
    elif change == "extra_field":
        manifest["extra"] = True
    elif change == "invalid_entry":
        entries[0] = {"path": first["path"]}
    if change == "duplicate_json_key":
        data = json.dumps(manifest)
        (root / "manifest.json").write_text('{"schema_version":"1.0",' + data[1:], encoding="utf-8")
    elif change == "invalid_json":
        (root / "manifest.json").write_text("{", encoding="utf-8")
    elif change not in {
        "missing_manifest",
        "extra_directory",
    }:
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        read_bundle(root)
