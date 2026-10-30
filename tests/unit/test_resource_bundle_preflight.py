"""Resource-bundle contract tests, enabled when the bundle is implemented."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import io
import json
import stat
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
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
PATHS = (
    {f"schemas/{name}.schema.json" for name in SCHEMAS}
    | {
        f"policy/{name}.yaml"
        for name in ("hard-rules", "permissions", "routing", "verification-levels")
    }
    | {"templates/spec.md"}
)

# An absent feature is the only skip condition. Broken imports of an existing
# module must fail so dependency and initialization errors cannot be hidden.
pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("aiflow.resource_bundle") is None,
    reason="resource bundle is not implemented on this baseline",
)


@pytest.fixture
def bundle(tmp_path: Path):
    module = importlib.import_module("aiflow.resource_bundle")
    manifest, files = module.build_bundle(ROOT)
    root = tmp_path / "bundle"
    root.mkdir()
    for relative, data in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return module, root, manifest, files


def test_bundle_contains_exact_canonical_source_resources(bundle) -> None:
    module, root, manifest, files = bundle
    assert set(files) == PATHS
    assert module.read_bundle(root) == (manifest, files)
    entries = {entry["path"]: entry for entry in manifest["files"]}
    assert set(entries) == PATHS
    for path in PATHS:
        expected = (ROOT / ".ai" / path).read_bytes().replace(b"\r\n", b"\n")
        assert files[path] == expected
        assert entries[path]["size"] == len(expected)
        assert entries[path]["sha256"] == hashlib.sha256(expected).hexdigest()


@pytest.mark.parametrize("corruption", ["altered", "missing", "extra"])
def test_bundle_rejects_altered_missing_or_extra_resource(bundle, corruption: str) -> None:
    module, root, _, _ = bundle
    target = root / "templates/spec.md"
    if corruption == "altered":
        target.write_bytes(b"altered\n")
    elif corruption == "missing":
        target.unlink()
    else:
        (root / "templates/extra.md").write_bytes(b"extra\n")
    with pytest.raises(ValueError):
        module.read_bundle(root)


def test_bundle_rejects_zip_symlink_even_when_bytes_match(bundle) -> None:
    module, _, manifest, files = bundle
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("bundle/manifest.json", json.dumps(manifest))
        for path, data in files.items():
            if path == "templates/spec.md":
                entry = zipfile.ZipInfo(f"bundle/{path}")
                entry.create_system = 3
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(entry, data)
            else:
                archive.writestr(f"bundle/{path}", data)
    with zipfile.ZipFile(io.BytesIO(output.getvalue())) as archive:
        entry = archive.getinfo("bundle/templates/spec.md")
        assert stat.S_ISLNK(entry.external_attr >> 16)
        with pytest.raises(ValueError):
            module.read_bundle(zipfile.Path(archive, "bundle/"))


def test_source_rejects_file_with_unknown_link_count(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("aiflow.resource_bundle")
    target = ROOT / ".ai/templates/spec.md"
    original = Path.lstat

    def lstat(path: Path):
        info = original(path)
        if path != target:
            return info
        return SimpleNamespace(
            st_mode=info.st_mode,
            st_nlink=0,
            st_file_attributes=getattr(info, "st_file_attributes", 0),
        )

    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ValueError):
        module.build_bundle(ROOT)
