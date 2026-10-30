"""Build and inspect distributions without borrowing the source checkout at runtime."""

from __future__ import annotations

import base64
import configparser
import csv
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import sysconfig
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest
from packaging.requirements import Requirement
from packaging.tags import parse_tag, sys_tags
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
_resource_source = ROOT / "src/aiflow/resource_bundle.py"
# Only an absent source may skip; import or source-identity errors must fail.
try:
    _resource_source.lstat()
except FileNotFoundError:
    pytestmark = pytest.mark.skip(reason="resource bundle is not implemented on this baseline")
else:
    _resource_module = importlib.import_module("aiflow.resource_bundle")
    _module_path = getattr(_resource_module, "__file__", None)
    if _module_path is None or Path(_module_path).resolve() != _resource_source.resolve():
        raise ImportError("resource bundle imported outside this checkout")

BUNDLE = "aiflow/_bundled_resources/"
RUNTIME_TOPS = {
    "pyyaml": {"yaml", "_yaml"},
    "jsonschema": {"jsonschema"},
    "jsonschema-specifications": {"jsonschema_specifications"},
    "attrs": {"attr", "attrs"},
    "referencing": {"referencing"},
    "rpds-py": {"rpds"},
    "typing-extensions": {"typing_extensions.py"},
}


def _regular_bytes(root: Path, relative: str) -> bytes:
    path = root
    root_info = root.lstat()
    if (
        not stat.S_ISDIR(root_info.st_mode)
        or stat.S_ISLNK(root_info.st_mode)
        or getattr(root_info, "st_file_attributes", 0) & 0x400
    ):
        raise ValueError("invalid distribution root")
    for index, part in enumerate(PurePosixPath(relative).parts):
        path = path / part
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked distribution path")
        if index < len(PurePosixPath(relative).parts) - 1:
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("distribution ancestor is not a directory")
        elif not stat.S_ISREG(info.st_mode):
            raise ValueError("distribution file is not regular")
        elif info.st_nlink != 1:
            raise ValueError("distribution file has non-unique links")
    return path.read_bytes()


def test_regular_bytes_rejects_hardlink_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = tmp_path / "site"
    site.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"external bytes")
    linked = site / "linked"
    os.link(outside, linked)
    assert linked.lstat().st_nlink > 1
    before = outside.read_bytes()
    original_read = Path.read_bytes
    read_paths: list[Path] = []

    def record_read(path: Path) -> bytes:
        read_paths.append(path)
        return original_read(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", record_read)
        with pytest.raises(ValueError, match="non-unique links"):
            _regular_bytes(site, "linked")
    assert read_paths == []
    assert outside.read_bytes() == before


def test_regular_bytes_rejects_unproven_unique_link_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = tmp_path / "site"
    site.mkdir()
    target = site / "file"
    target.write_bytes(b"unchanged")
    original_lstat = Path.lstat
    original_read = Path.read_bytes
    read_paths: list[Path] = []

    def fake_lstat(path: Path, *args: object, **kwargs: object) -> object:
        info = original_lstat(path, *args, **kwargs)
        if path == target:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0, st_nlink=0)
        return info

    def record_read(path: Path) -> bytes:
        read_paths.append(path)
        return original_read(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "lstat", fake_lstat)
        patch.setattr(Path, "read_bytes", record_read)
        with pytest.raises(ValueError, match="non-unique links"):
            _regular_bytes(site, "file")
    assert read_paths == []
    assert target.read_bytes() == b"unchanged"


def _scripts_directory(prefix: Path, scripts: Path) -> Path:
    if not prefix.is_absolute() or not scripts.is_absolute() or ".." in scripts.parts:
        raise ValueError("scripts directory is not an absolute venv path")
    try:
        relative = scripts.relative_to(prefix)
    except ValueError as error:
        raise ValueError("scripts directory escapes venv") from error
    if not relative.parts:
        raise ValueError("scripts directory is not inside venv")
    current = prefix
    for part in (None, *relative.parts):
        if part is not None:
            current /= part
        info = current.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError("scripts directory contains a link or invalid directory")
    return scripts


def _record_files(
    site: Path, dist_info: str, raw_record: str, allowed: set[str], scripts: set[str]
) -> dict[str, bytes]:
    """Validate RECORD before reading approved venv files; never read generated scripts."""
    result: dict[str, bytes] = {}
    seen: set[str] = set()
    script_dir = (
        _scripts_directory(Path(sys.prefix), Path(sysconfig.get_path("scripts")))
        if scripts
        else None
    )
    script_paths = {
        os.path.relpath(script_dir / (name + (".exe" if os.name == "nt" else "")), site).replace(
            "\\", "/"
        )
        for name in scripts
    }
    for row in csv.reader(io.StringIO(raw_record, newline="")):
        if len(row) != 3:
            raise ValueError("invalid RECORD row")
        name, digest, size = row
        if name in seen:
            raise ValueError("duplicate RECORD path")
        seen.add(name)
        if name in script_paths:
            continue
        path = PurePosixPath(name)
        if (
            not name
            or "\\" in name
            or path.is_absolute()
            or str(path) != name
            or any(part in {"..", "."} for part in path.parts)
            or ":" in name
            or "\x00" in name
        ):
            raise ValueError("invalid RECORD path")
        if path.parts[0] not in allowed | {dist_info} or ".data" in name.split("/")[0]:
            raise ValueError("unknown RECORD path")
        if path.parts[0] == dist_info:
            meta = path.parts[1:]
            if not meta or (
                meta[0] not in {"licenses", "sboms"}
                and (
                    len(meta) != 1
                    or meta[0]
                    not in {
                        "METADATA",
                        "WHEEL",
                        "RECORD",
                        "INSTALLER",
                        "REQUESTED",
                        "entry_points.txt",
                        "top_level.txt",
                    }
                )
            ):
                raise ValueError("unknown distribution metadata")
        if name == f"{dist_info}/RECORD":
            if digest or size:
                raise ValueError("invalid RECORD self entry")
            continue
        if path.suffix == ".pyc" and "__pycache__" in path.parts:
            continue
        if not digest.startswith("sha256=") or not size.isascii() or not size.isdigit():
            raise ValueError("missing RECORD hash or size")
        data = _regular_bytes(site, name)
        actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
        if digest != f"sha256={actual}" or int(size) != len(data):
            raise ValueError("distribution file digest mismatch")
        result[name] = data
    if f"{dist_info}/RECORD" not in seen:
        raise ValueError("missing RECORD self entry")
    return result


def _locked_versions() -> dict[str, str]:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for package in lock["package"]:
        name = canonicalize_name(package["name"])
        if name in RUNTIME_TOPS:
            if name in result:
                raise ValueError("ambiguous lock version")
            result[name] = package["version"]
    if set(result) != set(RUNTIME_TOPS):
        raise ValueError("missing locked runtime dependency")
    return result


def _console_scripts(site: Path, dist_info: str, rows: list[list[str]]) -> set[str]:
    entry_path = f"{dist_info}/entry_points.txt"
    matches = [row for row in rows if row and row[0] == entry_path]
    if not matches:
        return set()
    if len(matches) != 1 or len(matches[0]) != 3:
        raise ValueError("invalid entry points RECORD")
    _, digest, size = matches[0]
    if not digest.startswith("sha256=") or not size.isascii() or not size.isdigit():
        raise ValueError("invalid entry points RECORD hash")
    data = _regular_bytes(site, entry_path)
    actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
    if digest != f"sha256={actual}" or int(size) != len(data):
        raise ValueError("entry points integrity mismatch")
    entry_points = configparser.ConfigParser(interpolation=None)
    entry_points.optionxform = str
    entry_points.read_string(data.decode("utf-8"))
    scripts = (
        set(entry_points["console_scripts"])
        if entry_points.has_section("console_scripts")
        else set()
    )
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", script) for script in scripts):
        raise ValueError("invalid console script name")
    return scripts


def _verify_closure(
    locked: dict[str, str],
    dependencies: dict[str, list[Requirement]],
    *,
    python_version: str | None = None,
) -> set[str]:
    version = python_version or f"{sys.version_info.major}.{sys.version_info.minor}"
    discovered = {"pyyaml", "jsonschema"}
    pending = list(discovered)
    while pending:
        name = pending.pop()
        if name not in dependencies:
            raise ValueError("missing active runtime dependency")
        for requirement in dependencies[name]:
            if requirement.marker is not None and not requirement.marker.evaluate(
                {"extra": "", "python_version": version}
            ):
                continue
            name = canonicalize_name(requirement.name)
            if (
                name not in locked
                or requirement.url
                or requirement.extras
                or not requirement.specifier.contains(locked[name])
            ):
                raise ValueError("unrecognized or incompatible runtime dependency")
            if name not in discovered:
                discovered.add(name)
                pending.append(name)
    if version == "3.11" and discovered != set(locked):
        raise ValueError("runtime dependency closure does not match allowlist")
    return discovered


def _verify_project_requirements(project: dict, locked: dict[str, str]) -> None:
    roots: set[str] = set()
    for value in project["project"]["dependencies"]:
        requirement = Requirement(value)
        if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
            continue
        name = canonicalize_name(requirement.name)
        if (
            name not in {"pyyaml", "jsonschema"}
            or name in roots
            or requirement.url
            or requirement.extras
            or not requirement.specifier.contains(locked[name])
        ):
            raise ValueError("unrecognized project runtime requirement")
        roots.add(name)
    if roots != {"pyyaml", "jsonschema"}:
        raise ValueError("missing project runtime requirement")


def _wheelhouse(root: Path) -> dict[str, str]:
    """Reconstruct local wheels from checked installed distribution bytes, not cached wheels."""
    locked = _locked_versions()
    if set(locked) != set(RUNTIME_TOPS):
        raise ValueError("missing locked runtime dependency")
    _verify_project_requirements(
        tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8")), locked
    )
    site = Path(sysconfig.get_path("purelib"))
    if not site.resolve().is_relative_to(Path(sys.prefix).resolve()):
        raise ValueError("site-packages outside selected venv")
    current = Path(sys.prefix)
    for part in site.relative_to(current).parts:
        info = current.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError("linked site-packages ancestor")
        current /= part
    root.mkdir()
    dependencies: dict[str, list[Requirement]] = {}
    pending = ["pyyaml", "jsonschema"]
    while pending:
        name = pending.pop()
        if name in dependencies:
            continue
        version = locked[name]
        try:
            dist = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise ValueError("missing active runtime dependency") from error
        dist_info = Path(str(dist._path)).name
        if not dist_info.endswith(".dist-info") or Path(str(dist._path)).parent != site:
            raise ValueError("distribution metadata outside selected site-packages")
        raw = _regular_bytes(site, f"{dist_info}/RECORD").decode("utf-8")
        rows = list(csv.reader(io.StringIO(raw, newline="")))
        scripts = _console_scripts(site, dist_info, rows)
        files = _record_files(site, dist_info, raw, RUNTIME_TOPS[name], scripts)
        metadata = BytesParser().parsebytes(files[f"{dist_info}/METADATA"])
        if canonicalize_name(metadata["Name"]) != name or metadata["Version"] != version:
            raise ValueError("installed distribution does not match lock")
        wheel = BytesParser().parsebytes(files[f"{dist_info}/WHEEL"])
        tags = wheel.get_all("Tag", [])
        compatible = [tag for tag in tags if parse_tag(tag).intersection(sys_tags())]
        if not compatible:
            raise ValueError("incompatible installed wheel tag")
        dependencies[name] = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
        for requirement in dependencies[name]:
            if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
                continue
            dependency = canonicalize_name(requirement.name)
            if (
                dependency not in locked
                or requirement.url
                or requirement.extras
                or not requirement.specifier.contains(locked[dependency])
            ):
                raise ValueError("unrecognized or incompatible runtime dependency")
            pending.append(dependency)
        filename = f"{name.replace('-', '_')}-{version}-{compatible[0]}.whl"
        record_name = f"{dist_info}/RECORD"
        rows = []
        with zipfile.ZipFile(root / filename, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, data in sorted(files.items()):
                archive.writestr(path, data)
                digest = (
                    base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
                )
                rows.append((path, f"sha256={digest}", str(len(data))))
            output = io.StringIO(newline="")
            writer = csv.writer(output, lineterminator="\n")
            writer.writerows([*rows, (record_name, "", "")])
            archive.writestr(record_name, output.getvalue())
    active = _verify_closure(locked, dependencies)
    return {name: locked[name] for name in active}


def _environment(cwd: Path) -> dict[str, str]:
    home = cwd / "empty-home"
    temporary = cwd / "temp"
    home.mkdir(exist_ok=True)
    temporary.mkdir(exist_ok=True)
    env = {
        "PATH": os.defpath,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "XDG_CACHE_HOME": str(home / "cache"),
        "PIP_CACHE_DIR": str(home / "pip-cache"),
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONNOUSERSITE": "1",
        "TMPDIR": str(temporary),
        "TMP": str(temporary),
        "TEMP": str(temporary),
    }
    if os.name == "nt" and "SystemRoot" in os.environ:
        env["SystemRoot"] = os.environ["SystemRoot"]
    return env


def _run(*arguments: str, cwd: Path) -> None:
    result = subprocess.run(
        arguments, cwd=cwd, env=_environment(cwd), capture_output=True, text=True, timeout=180
    )
    assert result.returncode == 0, (
        f"command failed: {arguments!r}\n{result.stdout}\n{result.stderr}"
    )


def _source(root: Path, *, crlf: bool, identity: bytes) -> None:
    root.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE", "setup.py", "MANIFEST.in"):
        path = ROOT / name
        if path.is_file():
            shutil.copyfile(path, root / name)
    shutil.copytree(
        ROOT / "src/aiflow",
        root / "src/aiflow",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_bundled_resources"),
    )
    for directory in ("schemas", "policy"):
        shutil.copytree(ROOT / ".ai" / directory, root / ".ai" / directory)
    (root / ".ai/templates").mkdir(parents=True)
    shutil.copyfile(ROOT / ".ai/templates/spec.md", root / ".ai/templates/spec.md")
    for directory in (root / ".ai/schemas", root / ".ai/policy", root / ".ai/templates"):
        for path in directory.iterdir():
            data = path.read_bytes().replace(b"\r\n", b"\n")
            path.write_bytes(data.replace(b"\n", b"\r\n") if crlf else data)
    # These deliberately mimic real locations outside the distributable allow-list.
    for name in (
        ".ai/repository-id",
        ".ai/tasks/TASK-9999/task.yaml",
        ".ai/templates/task.yaml",
        "tests/test_private.py",
        "tests/unit/test_review_records.py",
        "docs/history.md",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(identity + b"\n")


def _unpack_sdist(sdist: Path, destination: Path) -> Path:
    destination.mkdir()
    prefix: str | None = None
    with tarfile.open(sdist, "r:gz") as archive:
        for item in archive.getmembers():
            parts = PurePosixPath(item.name).parts
            if (
                not parts
                or PurePosixPath(item.name).is_absolute()
                or ".." in parts
                or "\\" in item.name
                or ":" in item.name
            ):
                raise ValueError("unsafe sdist path")
            if prefix is None:
                prefix = parts[0]
            if parts[0] != prefix:
                raise ValueError("multiple sdist roots")
            target = destination.joinpath(*parts)
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif item.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(item)
                if stream is None:
                    raise ValueError("missing sdist file")
                with target.open("xb") as out:
                    shutil.copyfileobj(stream, out)
            else:
                raise ValueError("unsupported sdist entry")
    if prefix is None:
        raise ValueError("empty sdist")
    return destination / prefix


def _build(source: Path, output: Path, kind: str, cwd: Path) -> Path:
    output.mkdir()
    if source.is_file():
        source = _unpack_sdist(source, output.parent / f"{output.name}-source")
    _run(
        sys.executable,
        "-I",
        "-m",
        "build",
        "--no-isolation",
        f"--{kind}",
        "--outdir",
        str(output),
        str(source),
        cwd=cwd,
    )
    files = list(output.glob("*.whl" if kind == "wheel" else "*.tar.gz"))
    assert len(files) == 1
    return files[0]


def _wheel_resources(wheel: Path, identity: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert all(identity not in archive.read(name) for name in names if not name.endswith("/"))
        return {
            name.removeprefix(BUNDLE): archive.read(name)
            for name in names
            if name.startswith(BUNDLE) and not name.endswith("/")
        }


def _inspect_sdist(sdist: Path, identity: bytes, expected: set[str]) -> None:
    with tarfile.open(sdist, "r:gz") as archive:
        members = archive.getmembers()
        assert all(item.isfile() or item.isdir() for item in members)
        assert all(
            not item.name.startswith("/")
            and ".." not in PurePosixPath(item.name).parts
            and "\\" not in item.name
            for item in members
        )
        files = [item for item in members if item.isfile()]
        names = [item.name.split("/", 1)[1] for item in files]
        assert len(names) == len(set(names))
        assert not any(name.startswith((".ai/tasks/", "tests/", "docs/")) for name in names)
        assert ".ai/repository-id" not in names
        assert ".ai/templates/task.yaml" not in names
        assert {name for name in names if name.startswith(".ai/")} == {
            f".ai/{name}" for name in expected
        }
        for item in files:
            stream = archive.extractfile(item)
            assert stream is not None
            assert identity not in stream.read(), item.name


def _installed_bundle(
    wheel: Path, wheelhouse: Path, locked: dict[str, str], target: Path, cwd: Path
) -> dict:
    assert not cwd.resolve().is_relative_to(ROOT.resolve()), "working directory is inside source"
    _run(sys.executable, "-I", "-m", "venv", str(target), cwd=cwd)
    python = target / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    _run(
        str(python),
        "-I",
        "-m",
        "pip",
        "install",
        "--no-index",
        "--find-links",
        str(wheelhouse),
        str(wheel),
        cwd=cwd,
    )
    _run(str(python), "-I", "-m", "pip", "check", cwd=cwd)
    result = subprocess.run(
        [str(python), "-I", "-B", "-m", "aiflow", "--help"],
        cwd=cwd,
        env=_environment(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "usage: aiflow" in result.stdout
    code = (
        "import json, sys; from importlib.resources import files; "
        "import aiflow, importlib; from pathlib import Path; "
        "from importlib.metadata import version; "
        "names={'pyyaml':['yaml'],'jsonschema':['jsonschema'],"
        "'jsonschema-specifications':['jsonschema_specifications'],'attrs':['attr','attrs'],"
        "'referencing':['referencing'],'rpds-py':['rpds'],"
        "'typing-extensions':['typing_extensions']}; "
        "locked=json.loads(sys.argv[2]); "
        "mods=[importlib.import_module(m) for n in locked for m in names[n]]; "
        "assert Path(aiflow.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve()); "
        "assert all(Path(m.__file__).resolve().is_relative_to("
        "Path(sys.argv[1]).resolve()) for m in mods); "
        "assert all(version(n)==v for n,v in locked.items()); "
        "import aiflow.resource_bundle as resource_bundle; "
        "assert Path(resource_bundle.__file__).resolve().is_relative_to("
        "Path(sys.argv[1]).resolve()); "
        "manifest, content = resource_bundle.read_bundle("
        "files('aiflow').joinpath('_bundled_resources')); "
        "print(json.dumps({'manifest': manifest, 'paths': sorted(content)}))"
    )
    result = subprocess.run(
        [str(python), "-I", "-B", "-c", code, str(target), json.dumps(locked)],
        cwd=cwd,
        env=_environment(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_offline_distributions_are_complete_and_exclude_source_identity(tmp_path: Path) -> None:
    identity = (ROOT / ".ai/repository-id").read_bytes().strip()
    assert identity
    wheelhouse = tmp_path / "wheelhouse"
    locked = _wheelhouse(wheelhouse)
    resources = []
    manifests = []
    for mode in ("lf", "crlf"):
        source = tmp_path / mode
        _source(source, crlf=mode == "crlf", identity=identity)
        before = {
            path.relative_to(source).as_posix(): path.read_bytes()
            for path in (source / ".ai").rglob("*")
            if path.is_file()
        }
        direct = _build(source, tmp_path / f"{mode}-direct", "wheel", tmp_path)
        direct_resources = _wheel_resources(direct, identity)
        direct_manifest = json.loads(direct_resources["manifest.json"])
        sdist = _build(source, tmp_path / f"{mode}-sdist", "sdist", tmp_path)
        _inspect_sdist(sdist, identity, {entry["path"] for entry in direct_manifest["files"]})
        rebuilt = _build(sdist, tmp_path / f"{mode}-rebuilt", "wheel", tmp_path)
        resources.extend([direct_resources, _wheel_resources(rebuilt, identity)])
        for origin, wheel in (("direct", direct), ("rebuilt", rebuilt)):
            manifests.append(
                _installed_bundle(
                    wheel, wheelhouse, locked, tmp_path / f"{mode}-{origin}-installed", tmp_path
                )
            )
        assert {
            path.relative_to(source).as_posix(): path.read_bytes()
            for path in (source / ".ai").rglob("*")
            if path.is_file()
        } == before
    assert all(item == resources[0] for item in resources)
    assert len(resources[0]) == 21  # 20 inputs and manifest.json
    assert all(item == manifests[0] for item in manifests)
    assert len(manifests[0]["paths"]) == 20


def test_incomplete_source_distribution_cannot_build_wheel(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    sdist = _build(source, tmp_path / "sdist", "sdist", tmp_path)
    incomplete = tmp_path / "incomplete.tar.gz"
    omitted = ".ai/schemas/task.schema.json"
    with tarfile.open(sdist, "r:gz") as original, tarfile.open(incomplete, "w:gz") as modified:
        members = original.getmembers()
        matches = [item for item in members if item.name.endswith(f"/{omitted}")]
        assert len(matches) == 1 and matches[0].isfile()
        for item in members:
            if item.name == matches[0].name:
                continue
            modified.addfile(item, original.extractfile(item) if item.isfile() else None)

    unpacked = _unpack_sdist(incomplete, tmp_path / "unpacked")
    assert not (unpacked / omitted).exists()
    output = tmp_path / "wheel"
    output.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "build",
            "--no-isolation",
            "--wheel",
            "--outdir",
            str(output),
            str(unpacked),
        ],
        cwd=tmp_path,
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode != 0
    assert "resource path is unavailable" in result.stdout + result.stderr
    assert not list(output.glob("*.whl"))


def test_editable_install_does_not_write_bundle_into_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    output = tmp_path / "editable-wheel"
    output.mkdir()
    code = "import setuptools.build_meta as b,sys; b.build_editable(sys.argv[1])"
    _run(sys.executable, "-I", "-c", code, str(output), cwd=source)
    wheels = list(output.glob("*.whl"))
    assert len(wheels) == 1
    target = tmp_path / "editable-venv"
    _run(sys.executable, "-I", "-m", "venv", str(target), cwd=tmp_path)
    python = target / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    _run(
        str(python),
        "-I",
        "-m",
        "pip",
        "install",
        "--no-index",
        "--no-deps",
        str(wheels[0]),
        cwd=tmp_path,
    )
    _run(
        str(python),
        "-I",
        "-c",
        "import aiflow,sys; from pathlib import Path; "
        "assert Path(aiflow.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())",
        str(source / "src"),
        cwd=tmp_path,
    )
    assert not (source / "src/aiflow/_bundled_resources").exists()


@pytest.mark.parametrize(
    "case",
    [
        "traversal",
        "absolute",
        "backslash",
        "duplicate",
        "no_hash",
        "bad_hash",
        "bad_size",
        "unknown",
        "data",
        "script",
        "unknown_metadata",
        "missing_record",
    ],
)
def test_record_rejects_invalid_inputs_without_reading_outside(tmp_path: Path, case: str) -> None:
    site = tmp_path / "site"
    (site / "toy").mkdir(parents=True)
    (site / "toy/file.py").write_bytes(b"safe\n")
    outside = tmp_path / "outside"
    outside.write_bytes(b"preserve\n")
    digest = base64.urlsafe_b64encode(hashlib.sha256(b"safe\n").digest()).decode().rstrip("=")
    rows = [["toy/file.py", f"sha256={digest}", "5"], ["toy-1.dist-info/RECORD", "", ""]]
    if case == "traversal":
        rows[0][0] = "../outside"
    elif case == "absolute":
        rows[0][0] = "/outside"
    elif case == "backslash":
        rows[0][0] = "toy\\file.py"
    elif case == "duplicate":
        rows.append(rows[0][:])
    elif case == "no_hash":
        rows[0][1] = ""
    elif case == "bad_hash":
        rows[0][1] = "sha256=" + "0" * 43
    elif case == "bad_size":
        rows[0][2] = "99"
    elif case == "unknown":
        rows[0][0] = "unknown/file.py"
    elif case == "data":
        rows[0][0] = "toy-1.data/scripts/run"
    elif case == "script":
        rows[0][0] = "../../Scripts/unrecognized.exe"
    elif case == "unknown_metadata":
        rows[0][0] = "toy-1.dist-info/direct_url.json"
    elif case == "missing_record":
        rows.pop()
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    with pytest.raises(ValueError):
        _record_files(site, "toy-1.dist-info", output.getvalue(), {"toy"}, {"known"})
    assert outside.read_bytes() == b"preserve\n"


def test_record_rejects_linked_distribution_file(tmp_path: Path) -> None:
    site = tmp_path / "site"
    (site / "toy").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_bytes(b"safe\n")
    link = site / "toy/file.py"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"file symlinks unavailable: {error}")
    digest = base64.urlsafe_b64encode(hashlib.sha256(b"safe\n").digest()).decode().rstrip("=")
    raw = f"toy/file.py,sha256={digest},5\ntoy-1.dist-info/RECORD,,\n"
    try:
        with pytest.raises(ValueError, match="linked distribution path"):
            _record_files(site, "toy-1.dist-info", raw, {"toy"}, set())
        assert outside.read_bytes() == b"safe\n"
    finally:
        link.unlink()


def test_record_ignores_only_declared_installer_script_without_reading_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = tmp_path / "venv/lib/site-packages"
    (site / "toy").mkdir(parents=True)
    (site / "toy/file.py").write_bytes(b"safe\n")
    scripts = tmp_path / "venv/Scripts"
    scripts.mkdir()
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.setattr(sysconfig, "get_path", lambda _: str(scripts))
    script = scripts / ("known.exe" if os.name == "nt" else "known")
    raw_script = os.path.relpath(script, site).replace("\\", "/")
    digest = base64.urlsafe_b64encode(hashlib.sha256(b"safe\n").digest()).decode().rstrip("=")
    raw = (
        f"toy/file.py,sha256={digest},5\n{raw_script},sha256=ignored,1\ntoy-1.dist-info/RECORD,,\n"
    )
    assert _record_files(site, "toy-1.dist-info", raw, {"toy"}, {"known"}) == {
        "toy/file.py": b"safe\n"
    }
    assert not script.exists()


def test_scripts_directory_rejects_lexical_escape_without_access(tmp_path: Path) -> None:
    prefix = tmp_path / "venv"
    prefix.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="scripts directory escapes venv"):
        _scripts_directory(prefix, outside)


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_scripts_directory_rejects_links_without_reading_external_files(
    tmp_path: Path, kind: str
) -> None:
    prefix = tmp_path / "venv"
    prefix.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "marker"
    marker.write_bytes(b"preserve\n")
    link = prefix / "Scripts"
    if kind == "junction":
        if sys.platform != "win32":
            pytest.skip("junctions are Windows-specific")
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode:
            pytest.skip("directory junctions unavailable")
    else:
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"directory symlinks unavailable: {error}")
    try:
        with pytest.raises(ValueError, match="scripts directory contains a link"):
            _scripts_directory(prefix, link)
        assert marker.read_bytes() == b"preserve\n"
    finally:
        if kind == "junction":
            os.rmdir(link)
        else:
            link.unlink()


def test_altered_entry_points_are_rejected_before_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    info = tmp_path / "toy-1.dist-info"
    info.mkdir()
    entry = info / "entry_points.txt"
    original = b"[console_scripts]\nknown = toy:main\n"
    digest = base64.urlsafe_b64encode(hashlib.sha256(original).digest()).decode().rstrip("=")
    entry.write_bytes(b"[console_scripts]\nchanged = toy:main\n")
    monkeypatch.setattr(configparser.ConfigParser, "read_string", lambda *_: pytest.fail("parsed"))
    with pytest.raises(ValueError, match="entry points integrity mismatch"):
        _console_scripts(
            tmp_path,
            "toy-1.dist-info",
            [["toy-1.dist-info/entry_points.txt", f"sha256={digest}", str(len(original))]],
        )


@pytest.mark.parametrize("case", ["missing", "wrong_version", "wrong_tag"])
def test_wheelhouse_rejects_missing_or_incompatible_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    locked = _locked_versions()
    if case == "missing":
        locked.pop("pyyaml")
    elif case == "wrong_version":
        locked["attrs"] = "0.0.0"
    else:
        monkeypatch.setattr(sys.modules[__name__], "sys_tags", lambda: iter(()))
    monkeypatch.setattr(sys.modules[__name__], "_locked_versions", lambda: locked)
    with pytest.raises(ValueError):
        _wheelhouse(tmp_path / "wheelhouse")


def test_dependency_closure_rejects_unknown_active_requirement() -> None:
    locked = _locked_versions()
    dependencies = {name: [] for name in locked}
    dependencies["jsonschema"] = [Requirement("unrecognized-package>=1")]
    with pytest.raises(ValueError, match="unrecognized or incompatible"):
        _verify_closure(locked, dependencies)


def test_dependency_closure_respects_python_marker_and_requires_active_packages() -> None:
    locked = _locked_versions()
    dependencies = {name: [] for name in locked}
    dependencies["jsonschema"] = [
        Requirement(name)
        for name in ("attrs", "jsonschema-specifications", "referencing", "rpds-py")
    ]
    dependencies["referencing"] = [Requirement('typing-extensions; python_version < "3.13"')]
    assert _verify_closure(locked, dependencies, python_version="3.11") == set(locked)
    dependencies.pop("typing-extensions")
    assert _verify_closure(locked, dependencies, python_version="3.13") == (
        set(locked) - {"typing-extensions"}
    )
    with pytest.raises(ValueError, match="missing active runtime dependency"):
        _verify_closure(locked, dependencies, python_version="3.11")
    dependencies["referencing"].append(Requirement('new-dependency; python_version >= "3.13"'))
    with pytest.raises(ValueError, match="unrecognized or incompatible"):
        _verify_closure(locked, dependencies, python_version="3.13")


def test_project_runtime_requirements_reject_new_dependency() -> None:
    locked = _locked_versions()
    project = {"project": {"dependencies": ["PyYAML>=6,<7", "jsonschema>=4,<5", "new-dep"]}}
    with pytest.raises(ValueError, match="unrecognized project runtime requirement"):
        _verify_project_requirements(project, locked)


@pytest.mark.parametrize("kind", ["symlink", "junction"])
@pytest.mark.parametrize("position", ["build-lib", "package", "bundle"])
def test_build_rejects_linked_output_before_writing_outside(
    tmp_path: Path, kind: str, position: str
) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / ("manifest.json" if position == "bundle" else "marker.txt")
    marker.write_bytes(b"preserve outside file\n")
    build_lib = source / "build/lib"
    link = {
        "build-lib": build_lib,
        "package": build_lib / "aiflow",
        "bundle": build_lib / "aiflow/_bundled_resources",
    }[position]
    link.parent.mkdir(parents=True, exist_ok=True)
    if kind == "symlink":
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"directory symlinks unavailable: {error}")
    elif sys.platform == "win32":
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if created.returncode:
            pytest.skip("directory junctions unavailable")
    else:
        pytest.skip("junctions are Windows-specific")
    before = {
        path.relative_to(outside).as_posix(): path.read_bytes()
        for path in outside.rglob("*")
        if path.is_file()
    }
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "setup.py",
                "build_py",
                "--build-lib",
                str(build_lib),
            ],
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        after = {
            path.relative_to(outside).as_posix(): path.read_bytes()
            for path in outside.rglob("*")
            if path.is_file()
        }
        assert after == before, "build modified the linked outside directory"
        assert result.returncode != 0, "build accepted a linked output path"
        output = result.stdout + result.stderr
        assert "resource path contains a link or reparse point" in output, output
    finally:
        if kind == "junction":
            os.rmdir(link)
        else:
            link.unlink()


def test_build_rejects_linked_python_output_before_writing_outside(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"preserve outside file\n")
    build_lib = source / "build/lib"
    package = build_lib / "aiflow"
    package.mkdir(parents=True)
    link = package / "__init__.py"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"file symlinks unavailable: {error}")
    before = outside.read_bytes()
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "setup.py",
                "build_py",
                "--build-lib",
                str(build_lib),
            ],
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert outside.read_bytes() == before, "build modified the linked outside file"
        assert result.returncode != 0, "build accepted a linked Python output file"
        assert "resource path contains a link or reparse point" in result.stdout + result.stderr
    finally:
        link.unlink()


def test_build_rejects_preexisting_manifest_without_rewriting_it(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    build_lib = source / "build/lib"
    bundle = build_lib / "aiflow/_bundled_resources"
    bundle.mkdir(parents=True)
    manifest = bundle / "manifest.json"
    manifest.write_bytes(b"existing user data\n")
    result = subprocess.run(
        [sys.executable, "-I", "setup.py", "build_py", "--build-lib", str(build_lib)],
        cwd=source,
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode != 0
    assert "bundle inventory does not match the allowlist" in result.stdout + result.stderr
    assert manifest.read_bytes() == b"existing user data\n"
    assert sorted(path.name for path in bundle.iterdir()) == ["manifest.json"]
    assert sorted(path.name for path in bundle.parent.iterdir()) == ["_bundled_resources"]


def test_build_rejects_different_python_output_without_overwriting_it(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    build_lib = source / "build/lib"
    existing = build_lib / "aiflow/cli.py"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"preserve Python output\n")
    result = subprocess.run(
        [sys.executable, "-I", "setup.py", "build_py", "--build-lib", str(build_lib)],
        cwd=source,
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode != 0
    assert "existing Python build output differs from source" in result.stdout + result.stderr
    assert existing.read_bytes() == b"preserve Python output\n"
    assert sorted(path.name for path in existing.parent.iterdir()) == ["cli.py"]


def test_direct_wheel_rejects_existing_output_without_overwriting_it(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    output = tmp_path / "dist"
    output.mkdir()
    existing = output / "aiflow-0.2.0-py3-none-any.whl"
    existing.write_bytes(b"preserve existing wheel\n")
    result = subprocess.run(
        [sys.executable, "-I", "setup.py", "bdist_wheel", "--dist-dir", str(output)],
        cwd=source,
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode != 0
    assert "wheel output already exists" in result.stdout + result.stderr
    assert existing.read_bytes() == b"preserve existing wheel\n"
    assert sorted(path.name for path in output.iterdir()) == [existing.name]


def test_direct_sdist_rejects_existing_archive_without_overwriting_it(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    output = tmp_path / "dist"
    output.mkdir()
    existing = output / "aiflow-0.2.0.tar.gz"
    existing.write_bytes(b"preserve existing archive\n")
    result = subprocess.run(
        [sys.executable, "-I", "setup.py", "sdist", "--dist-dir", str(output)],
        cwd=source,
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode != 0
    assert "source archive output already exists" in result.stdout + result.stderr
    assert existing.read_bytes() == b"preserve existing archive\n"
    assert sorted(path.name for path in output.iterdir()) == [existing.name]


@pytest.mark.parametrize("target", ["package", "bundle", "metadata"])
def test_build_rejects_hardlinked_output_without_modifying_external_file(
    tmp_path: Path, target: str
) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    outside = tmp_path / "outside"
    outside.write_bytes(b"preserve external file\n")
    build_lib = source / "build/lib"
    link = {
        "package": build_lib / "aiflow/__init__.py",
        "bundle": build_lib / "aiflow/_bundled_resources/manifest.json",
        "metadata": source / "src/aiflow.egg-info/PKG-INFO",
    }[target]
    link.parent.mkdir(parents=True)
    try:
        os.link(outside, link)
    except OSError as error:
        pytest.skip(f"hard links unavailable: {error}")
    try:
        arguments = (
            [sys.executable, "-I", "setup.py", "sdist", "--dist-dir", str(tmp_path / "dist")]
            if target == "metadata"
            else [sys.executable, "-I", "setup.py", "build_py", "--build-lib", str(build_lib)]
        )
        result = subprocess.run(
            arguments,
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        expected = (
            "metadata output contains a link or invalid file"
            if target == "metadata"
            else "resource file is not an ordinary file"
        )
        assert result.returncode != 0
        assert expected in result.stdout + result.stderr
        assert outside.read_bytes() == b"preserve external file\n"
        assert link.read_bytes() == b"preserve external file\n"
        assert not list((tmp_path / "dist").glob("*.tar.gz"))
    finally:
        link.unlink()


def test_repeated_build_reuses_identical_bundle_without_rewriting_it(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    build_lib = source / "build/lib"
    arguments = [sys.executable, "-I", "setup.py", "build_py", "--build-lib", str(build_lib)]
    _run(*arguments, cwd=source)
    bundle = build_lib / "aiflow/_bundled_resources"
    files = [path for path in bundle.rglob("*") if path.is_file()]
    assert len(files) == 21
    fixed_time = 946684800_000_000_000
    for path in files:
        os.utime(path, ns=(fixed_time, fixed_time))
    before = {
        path.relative_to(bundle).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in files
    }
    _run(*arguments, cwd=source)
    after = {
        path.relative_to(bundle).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in bundle.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_build_rejects_parent_traversal_without_writing_outside(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    (source / "build").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "marker"
    marker.write_bytes(b"preserve\n")
    traversal = source / "build/../../outside"
    result = subprocess.run(
        [sys.executable, "-I", "setup.py", "build_py", "--build-lib", str(traversal)],
        cwd=source,
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode != 0
    assert "bundle build output contains a parent traversal" in result.stdout + result.stderr
    assert sorted(path.name for path in outside.iterdir()) == ["marker"]
    assert marker.read_bytes() == b"preserve\n"


@pytest.mark.parametrize("kind", ["file_symlink", "dir_symlink", "dir_junction"])
def test_build_does_not_execute_linked_resource_helper(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    directory = source / "src/aiflow"
    if kind == "file_symlink":
        link = directory / "resource_bundle.py"
        link.rename(tmp_path / "original-helper.py")
        outside = tmp_path / "outside-helper.py"
    else:
        link = directory
        outside_dir = tmp_path / "outside-package"
        directory.rename(outside_dir)
        outside = outside_dir / "resource_bundle.py"
    marker = b'print("SYNTHETIC_HELPER_EXECUTED")\n'
    outside.write_bytes(marker)
    if kind == "dir_junction":
        if sys.platform != "win32":
            pytest.skip("junctions are Windows-specific")
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside.parent)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if created.returncode:
            pytest.skip("directory junctions unavailable")
    else:
        try:
            link.symlink_to(
                outside if kind == "file_symlink" else outside.parent,
                target_is_directory=kind == "dir_symlink",
            )
        except OSError as error:
            pytest.skip(f"symlinks unavailable: {error}")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "setup.py",
                "build_py",
                "--build-lib",
                str(source / "build/lib"),
            ],
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0
        assert "package source contains a link or reparse point" in output
        assert "SYNTHETIC_HELPER_EXECUTED" not in output
        assert outside.read_bytes() == marker
    finally:
        if kind == "dir_junction":
            os.rmdir(link)
        else:
            link.unlink()


@pytest.mark.parametrize("kind", ["directory", "symlink", "junction"])
def test_sdist_rejects_existing_staging_without_modification(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    stage = source / "aiflow-0.2.0"
    outside = tmp_path / "outside"
    if kind == "directory":
        outside = stage
        outside.mkdir()
    else:
        outside.mkdir()
        if kind == "junction":
            if sys.platform != "win32":
                pytest.skip("junctions are Windows-specific")
            created = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(stage), str(outside)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if created.returncode:
                pytest.skip("directory junctions unavailable")
        else:
            try:
                stage.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                pytest.skip(f"directory symlinks unavailable: {error}")
    marker = outside / "marker"
    marker.write_bytes(b"preserve\n")
    output = tmp_path / "dist"
    output.mkdir()
    try:
        result = subprocess.run(
            [sys.executable, "-I", "setup.py", "sdist", "--dist-dir", str(output)],
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode != 0
        assert "source distribution staging path already exists" in result.stdout + result.stderr
        assert marker.read_bytes() == b"preserve\n"
        assert sorted(path.name for path in outside.iterdir()) == ["marker"]
        assert not list(output.glob("*.tar.gz"))
    finally:
        if kind == "junction":
            os.rmdir(stage)
        elif kind == "symlink":
            stage.unlink()


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_wheel_rejects_linked_package_before_discovery(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    outside = tmp_path / "outside-package"
    outside.mkdir()
    marker = outside / "__init__.py"
    marker.write_bytes(b"EXTERNAL_PACKAGE_MARKER = True\n")
    link = source / "src/aiflow/external_package"
    if kind == "junction":
        if sys.platform != "win32":
            pytest.skip("junctions are Windows-specific")
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode:
            pytest.skip("directory junctions unavailable")
    else:
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"directory symlinks unavailable: {error}")
    try:
        output = tmp_path / "dist"
        result = subprocess.run(
            [sys.executable, "-I", "setup.py", "bdist_wheel", "--dist-dir", str(output)],
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode != 0
        assert "package source contains a link or reparse point" in result.stdout + result.stderr
        assert marker.read_bytes() == b"EXTERNAL_PACKAGE_MARKER = True\n"
        assert not list(output.glob("*.whl"))
    finally:
        if kind == "junction":
            os.rmdir(link)
        else:
            link.unlink()


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_wheel_rejects_linked_sibling_package_before_discovery(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    outside = tmp_path / "outside-package"
    outside.mkdir()
    marker = outside / "__init__.py"
    marker.write_bytes(b"SYNTHETIC_IDENTITY_MARKER = True\n")
    link = source / "src/external_package"
    if kind == "junction":
        if sys.platform != "win32":
            pytest.skip("junctions are Windows-specific")
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if created.returncode:
            pytest.skip("directory junctions unavailable")
    else:
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"directory symlinks unavailable: {error}")
    try:
        output = tmp_path / "dist"
        result = subprocess.run(
            [sys.executable, "-I", "setup.py", "bdist_wheel", "--dist-dir", str(output)],
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode != 0
        assert "package source contains a link or reparse point" in result.stdout + result.stderr
        assert marker.read_bytes() == b"SYNTHETIC_IDENTITY_MARKER = True\n"
        assert not list(output.glob("*.whl"))
    finally:
        if kind == "junction":
            os.rmdir(link)
        else:
            link.unlink()


@pytest.mark.parametrize("position", ["root", "package"])
def test_build_rejects_unknown_cached_file_without_modification(
    tmp_path: Path, position: str
) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    build_lib = source / "build/lib"
    marker = (build_lib if position == "root" else build_lib / "aiflow") / "unexpected.py"
    marker.parent.mkdir(parents=True)
    marker.write_bytes(b"SYNTHETIC_IDENTITY_MARKER = True\n")
    result = subprocess.run(
        [sys.executable, "-I", "setup.py", "build_py", "--build-lib", str(build_lib)],
        cwd=source,
        env=_environment(tmp_path),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode != 0
    assert "unexpected file in existing Python build output" in result.stdout + result.stderr
    assert marker.read_bytes() == b"SYNTHETIC_IDENTITY_MARKER = True\n"
    assert [path for path in build_lib.rglob("*") if path.is_file()] == [marker]


@pytest.mark.parametrize("kind", ["directory", "symlink", "junction"])
def test_wheel_rejects_existing_staging_without_modification(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    stage = source / "build/wheel-staging"
    stage.parent.mkdir()
    outside = tmp_path / "outside"
    if kind == "directory":
        outside = stage
        stage.mkdir()
    else:
        outside.mkdir()
        if kind == "junction":
            if sys.platform != "win32":
                pytest.skip("junctions are Windows-specific")
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(stage), str(outside)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode:
                pytest.skip("directory junctions unavailable")
        else:
            try:
                stage.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                pytest.skip(f"directory symlinks unavailable: {error}")
    marker = outside / "marker"
    marker.write_bytes(b"preserve\n")
    output = tmp_path / "dist"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "setup.py",
                "bdist_wheel",
                "--bdist-dir",
                str(stage),
                "--dist-dir",
                str(output),
            ],
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode != 0
        assert "wheel staging path already exists" in result.stdout + result.stderr
        assert marker.read_bytes() == b"preserve\n"
        assert sorted(path.name for path in outside.iterdir()) == ["marker"]
        assert not list(output.glob("*.whl"))
    finally:
        if kind == "junction":
            os.rmdir(stage)
        elif kind == "symlink":
            stage.unlink()


def test_changed_source_and_resources_build_without_rewriting_previous_outputs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    first = _build(source, tmp_path / "first-wheel", "wheel", tmp_path)
    first_bytes = first.read_bytes()
    original_outputs = {
        path.relative_to(source).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (source / "build").rglob("*")
        if path.is_file()
    }
    assert original_outputs
    with (source / "src/aiflow/cli.py").open("ab") as stream:
        stream.write(b"\n# synthetic source change\n")
    with (source / ".ai/templates/spec.md").open("ab") as stream:
        stream.write(b"\nSynthetic resource change.\n")
    second = _build(source, tmp_path / "second-wheel", "wheel", tmp_path)
    assert first.read_bytes() == first_bytes
    for relative, (data, modified) in original_outputs.items():
        path = source / relative
        assert (path.read_bytes(), path.stat().st_mtime_ns) == (data, modified)
    first_resources = _wheel_resources(first, b"synthetic-only-identity")
    second_resources = _wheel_resources(second, b"synthetic-only-identity")
    assert first_resources["manifest.json"] != second_resources["manifest.json"]
    assert second_resources["templates/spec.md"].endswith(b"\nSynthetic resource change.\n")
    with zipfile.ZipFile(second) as archive:
        assert archive.read("aiflow/cli.py").endswith(b"\n# synthetic source change\n")


@pytest.mark.parametrize("command", ["sdist", "pep517_metadata"])
@pytest.mark.parametrize("kind", ["directory_symlink", "directory_junction", "file_symlink"])
def test_metadata_refuses_links_before_any_outside_write(
    tmp_path: Path, command: str, kind: str
) -> None:
    source = tmp_path / "source"
    _source(source, crlf=False, identity=b"synthetic-only-identity")
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "PKG-INFO"
    marker.write_bytes(b"preserve\n")
    metadata = source / "src/aiflow.egg-info" if command == "sdist" else tmp_path / "metadata"
    if kind == "file_symlink":
        directory = metadata if command == "sdist" else metadata / "aiflow-0.2.0.dist-info"
        directory.mkdir(parents=True)
        link = directory / "PKG-INFO"
    else:
        link = metadata
    if kind == "directory_junction":
        if sys.platform != "win32":
            pytest.skip("junctions are Windows-specific")
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if created.returncode:
            pytest.skip("directory junctions unavailable")
    else:
        try:
            link.symlink_to(
                marker if kind == "file_symlink" else outside,
                target_is_directory=kind == "directory_symlink",
            )
        except OSError as error:
            pytest.skip(f"symlinks unavailable: {error}")
    try:
        if command == "sdist":
            arguments = [
                sys.executable,
                "-I",
                "setup.py",
                "sdist",
                "--dist-dir",
                str(tmp_path / "dist"),
            ]
        else:
            code = (
                "import setuptools.build_meta as b,sys; "
                "b.prepare_metadata_for_build_wheel(sys.argv[1])"
            )
            arguments = [sys.executable, "-I", "-c", code, str(metadata)]
        result = subprocess.run(
            arguments,
            cwd=source,
            env=_environment(tmp_path),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if command == "sdist":
            expected = "package source contains a link or reparse point"
        elif kind == "file_symlink":
            expected = "distribution metadata output already exists"
        else:
            expected = "metadata output path contains a link or invalid directory"
        assert result.returncode != 0
        assert expected in result.stdout + result.stderr
        assert marker.read_bytes() == b"preserve\n"
        assert sorted(path.name for path in outside.iterdir()) == ["PKG-INFO"]
        assert not list((tmp_path / "dist").glob("*.tar.gz"))
    finally:
        if kind == "directory_junction":
            os.rmdir(link)
        else:
            link.unlink()
