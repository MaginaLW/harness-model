"""Package only the explicitly selected AI Flow seed resources."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from types import ModuleType

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py
from setuptools.command.dist_info import dist_info
from setuptools.command.egg_info import egg_info
from setuptools.command.sdist import sdist


def _guard_metadata_path(path: Path, *, inspect_children: bool = False) -> None:
    """Reject existing links before setuptools creates or updates metadata."""
    absolute = path.absolute()
    if ".." in absolute.parts:
        raise ValueError("metadata output contains a parent traversal")
    for item in reversed((absolute, *absolute.parents)):
        if os.path.lexists(item):
            info = item.lstat()
            reparse = getattr(info, "st_file_attributes", 0) & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
            )
            if stat.S_ISLNK(info.st_mode) or reparse or not stat.S_ISDIR(info.st_mode):
                raise ValueError("metadata output path contains a link or invalid directory")
    if inspect_children and absolute.exists():
        for item in absolute.rglob("*"):
            info = item.lstat()
            reparse = getattr(info, "st_file_attributes", 0) & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
            )
            if (
                stat.S_ISLNK(info.st_mode)
                or reparse
                or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
                or (stat.S_ISREG(info.st_mode) and info.st_nlink != 1)
            ):
                raise ValueError("metadata output contains a link or invalid file")


class ResourceEggInfo(egg_info):
    def initialize_options(self) -> None:
        super().initialize_options()
        self._owned_egg_base = None

    def finalize_options(self) -> None:
        # Never let setuptools writers reuse a source-tree egg-info directory.
        if self._owned_egg_base is None:
            build_root = Path(__file__).parent.absolute() / "build"
            _guard_metadata_path(build_root)
            build_root.mkdir(parents=True, exist_ok=True)
            _guard_metadata_path(build_root)
            self._owned_egg_base = tempfile.mkdtemp(prefix="aiflow-egg-info-", dir=build_root)
        self.egg_base = self._owned_egg_base
        super().finalize_options()

    def run(self) -> None:
        _guard_metadata_path(
            Path(__file__).parent.absolute() / "src/aiflow.egg-info", inspect_children=True
        )
        metadata = Path(self.egg_info)
        _guard_metadata_path(metadata, inspect_children=True)
        if os.path.lexists(metadata / "native_libs.txt"):
            raise ValueError("unexpected legacy metadata file")
        super().run()


class ResourceDistInfo(dist_info):
    def run(self) -> None:
        _guard_metadata_path(self.output_dir)
        if os.path.lexists(self.dist_info_dir):
            raise ValueError("distribution metadata output already exists")
        egg_info = Path(self.egg_info.egg_info)
        kept_egg_info = self.output_dir / egg_info.name
        if self.keep_egg_info and os.path.lexists(kept_egg_info):
            raise ValueError("egg metadata output already exists")
        super().run()
        if self.keep_egg_info:
            _guard_metadata_path(egg_info, inspect_children=True)
            _guard_metadata_path(self.output_dir)
            shutil.copytree(egg_info, kept_egg_info)


class ResourceWheel(bdist_wheel):
    def run(self) -> None:
        source_root = Path(__file__).parent.absolute()
        staging = Path(self.bdist_dir).absolute()
        try:
            relative = staging.relative_to(source_root)
        except ValueError as error:
            raise ValueError("wheel staging path escapes source root") from error
        if ".." in relative.parts:
            raise ValueError("wheel staging path contains a parent traversal")
        tag = "-".join(self.get_tag())
        _guard_metadata_path(Path(self.dist_dir))
        wheel = Path(self.dist_dir) / f"{self.wheel_dist_name}-{tag}.whl"
        if os.path.lexists(wheel):
            raise ValueError("wheel output already exists")
        _guard_metadata_path(staging.parent)
        if os.path.lexists(staging):
            raise ValueError("wheel staging path already exists")
        staging.parent.mkdir(parents=True, exist_ok=True)
        _guard_metadata_path(staging.parent)
        module = resource_module()
        manifest, files = module.build_bundle(source_root)
        digest = hashlib.sha256()
        for path in sorted((source_root / "src/aiflow").rglob("*.py")):
            relative_source = path.relative_to(source_root).as_posix()
            content = module._source_file(source_root, relative_source).read_bytes()
            digest.update(relative_source.encode("utf-8") + b"\0")
            digest.update(hashlib.sha256(content).digest())
        digest.update(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        for name, content in sorted(files.items()):
            digest.update(name.encode("utf-8") + b"\0" + hashlib.sha256(content).digest())
        build = self.get_finalized_command("build")
        # This is only a cache directory name; existing outputs are still
        # compared byte-for-byte, so a prefix collision fails closed.
        build.build_lib = str(source_root / "build" / ("rb-" + digest.hexdigest()[:24]))
        self.reinitialize_command("build_py")
        staging.mkdir()
        super().run()


def resource_module() -> ModuleType:
    source_root = Path(__file__).parent.absolute()
    source = source_root
    for part, directory in (
        (None, True),
        ("src", True),
        ("aiflow", True),
        ("resource_bundle.py", False),
    ):
        if part is not None:
            source = source / part
        info = source.lstat()
        reparse = getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        )
        if (
            stat.S_ISLNK(info.st_mode)
            or reparse
            or (directory and not stat.S_ISDIR(info.st_mode))
            or (not directory and not stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)
        ):
            raise ValueError("resource builder path contains a link or invalid file")
    spec = importlib.util.spec_from_file_location("aiflow_resource_bundle_build", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("resource bundle builder is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResourceBuild(build_py):
    def copy_file(
        self,
        infile: str,
        outfile: str,
        preserve_mode: bool = True,
        preserve_times: bool = True,
        link: str | None = None,
        level: object = 1,
    ) -> tuple[str, bool]:
        if link is not None:
            raise ValueError("linked build output is not supported")
        source = Path(infile)
        destination = Path(outfile)
        module = resource_module()
        module._check_path(source, directory=False)
        if os.path.lexists(destination):
            module._check_path(destination, directory=False)
            if destination.read_bytes() != source.read_bytes():
                raise ValueError("existing Python build output differs from source")
            return str(destination), False
        with source.open("rb") as input_stream, destination.open("xb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream)
        if preserve_mode:
            shutil.copymode(source, destination)
        if preserve_times:
            source_stat = source.stat()
            os.utime(destination, ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns))
        return str(destination), True

    def run(self) -> None:
        if self.editable_mode:
            # Setuptools points editable builds at a temporary directory; the
            # normal source checkout remains the editable runtime source.
            super().run()
            return
        module = resource_module()
        source_root = Path(__file__).parent.absolute()
        target = (Path(self.build_lib) / "aiflow" / "_bundled_resources").absolute()
        try:
            relative_target = target.relative_to(source_root)
        except ValueError as error:
            raise ValueError("bundle build output escapes source root") from error
        if ".." in relative_target.parts:
            raise ValueError("bundle build output contains a parent traversal")

        def check_output() -> None:
            current = source_root
            module._check_path(current, directory=True)
            for part in relative_target.parts:
                current = current / part
                if os.path.lexists(current):
                    module._check_path(current, directory=True)

        check_output()
        module._check_path(source_root / "src", directory=True)
        module._check_path(source_root / "src/aiflow", directory=True)
        package_source = source_root / "src/aiflow"
        sources = tuple(package_source.rglob("*.py"))
        for source in sources:
            module._source_file(source_root, source.relative_to(source_root).as_posix())
        package_output = target.parent
        manifest, files = module.build_bundle(source_root)
        build_output = package_output.parent
        expected_files = (
            {"aiflow/" + source.relative_to(package_source).as_posix() for source in sources}
            | {"aiflow/_bundled_resources/" + name for name in files}
            | {"aiflow/_bundled_resources/manifest.json"}
        )
        expected_directories = {
            parent.as_posix()
            for name in expected_files
            for parent in Path(name).parents
            if parent.as_posix() != "."
        }
        if build_output.exists():
            for path in build_output.rglob("*"):
                is_directory = module._check_path(path, directory=None)
                relative = path.relative_to(build_output).as_posix()
                if (is_directory and relative not in expected_directories) or (
                    not is_directory and relative not in expected_files
                ):
                    raise ValueError("unexpected file in existing Python build output")
            for source in sources:
                destination = package_output / source.relative_to(package_source)
                if os.path.lexists(destination):
                    module._check_path(destination, directory=False)
                    if destination.read_bytes() != source.read_bytes():
                        raise ValueError("existing Python build output differs from source")
        manifest_bytes = (
            json.dumps(manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        existing = target.exists()

        def check_existing() -> None:
            if (
                module._read_bundle(target, module.CLI_VERSION) != (manifest, files)
                or (target / "manifest.json").read_bytes() != manifest_bytes
            ):
                raise ValueError("existing bundle build output differs from expected resources")

        if existing:
            check_existing()
        super().run()
        check_output()
        if existing:
            check_existing()
            return
        target.mkdir()
        for directory in ("schemas", "policy", "templates"):
            (target / directory).mkdir()
        for name, data in files.items():
            path = target / name
            with path.open("xb") as stream:
                stream.write(data)
        with (target / "manifest.json").open("xb") as stream:
            stream.write(manifest_bytes)


class ResourceSdist(sdist):
    def run(self) -> None:
        suffixes = {
            "bztar": ".tar.bz2",
            "gztar": ".tar.gz",
            "tar": ".tar",
            "xztar": ".tar.xz",
            "zip": ".zip",
            "ztar": ".tar.Z",
        }
        _guard_metadata_path(Path(self.dist_dir))
        for fmt in self.formats:
            if fmt not in suffixes:
                raise ValueError("unsupported source archive format")
            destination = Path(self.dist_dir) / (self.distribution.get_fullname() + suffixes[fmt])
            if os.path.lexists(destination):
                raise ValueError("source archive output already exists")
        super().run()

    def make_release_tree(self, base_dir: str, files: list[str]) -> None:
        if os.path.lexists(base_dir):
            raise ValueError("source distribution staging path already exists")
        module = resource_module()
        module.build_bundle(Path(__file__).parent)
        required = {f".ai/{path}" for path in module.RESOURCE_KINDS}
        root_files = {"LICENSE", "pyproject.toml", "setup.py", "MANIFEST.in"}
        selected = []
        for name in files:
            normalized = name.replace("\\", "/")
            if (
                normalized in required
                or normalized in root_files
                or (normalized.startswith("src/aiflow/") and normalized.endswith(".py"))
            ):
                selected.append(name)
        if not required.issubset({name.replace("\\", "/") for name in selected}):
            raise ValueError("source distribution omits required seed resources")
        for name in selected:
            module._source_file(Path(__file__).parent, name.replace("\\", "/"))
        # Create our staging directory exclusively; a concurrent creator must
        # not be treated as a directory this build is allowed to populate.
        os.mkdir(base_dir)
        super().make_release_tree(base_dir, selected)


def _guard_source_tree() -> None:
    """Check package discovery inputs before setuptools follows directories."""
    source_root = Path(__file__).parent.absolute() / "src"
    _guard_metadata_path(source_root)
    try:
        package_info = (source_root / "aiflow").lstat()
    except OSError as error:
        raise ValueError("package source directory is missing") from error
    reparse = getattr(package_info, "st_file_attributes", 0) & getattr(
        stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
    )
    if stat.S_ISLNK(package_info.st_mode) or reparse:
        raise ValueError("package source contains a link or reparse point")
    if not stat.S_ISDIR(package_info.st_mode):
        raise ValueError("package source directory is missing")
    for path in source_root.rglob("*"):
        info = path.lstat()
        reparse = getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        )
        if (
            stat.S_ISLNK(info.st_mode)
            or reparse
            or (path.suffix == ".py" and stat.S_ISREG(info.st_mode) and info.st_nlink != 1)
        ):
            raise ValueError("package source contains a link or reparse point")


_guard_source_tree()
setup(
    cmdclass={
        "build_py": ResourceBuild,
        "bdist_wheel": ResourceWheel,
        "sdist": ResourceSdist,
        "egg_info": ResourceEggInfo,
        "dist_info": ResourceDistInfo,
    }
)
