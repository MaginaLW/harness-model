"""Public-tool fixtures for real installed Node tests; no target source or mocked PASS."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "agent-bridge-node@1"
CHECKS = (
    ("contract", 30),
    ("scope", 30),
    ("smoke", 30),
    ("node_build", 300),
    ("node_check", 600),
    ("diff_whitespace", 30),
)


def node_policies(directory: Path) -> Path:
    """Write all four explicit Policy inputs without altering the checkout Policy."""
    from aiflow.policy import POLICY_FILES

    directory.mkdir(parents=True)
    checks = [dict(id=name, required=True, timeout_seconds=seconds) for name, seconds in CHECKS]
    for name in POLICY_FILES:
        document = yaml.safe_load((ROOT / ".ai/policy" / name).read_text(encoding="utf8"))
        document["policy_version"] = "3.1.0"
        if name == "verification-levels.yaml":
            document = {
                "schema_version": "1.0",
                "policy_version": "3.1.0",
                "policy_kind": "verification_levels",
                "profile": {"id": "agent-bridge-node", "revision": 1},
                "levels": [
                    {"id": "V0", "checks": checks},
                    {
                        "id": "V1",
                        "checks": [
                            *checks,
                            dict(id="ts_coverage", required=True, timeout_seconds=600),
                            dict(
                                id="ts_total_lines", required=True, timeout_seconds=30, threshold=85
                            ),
                            dict(
                                id="ts_diff_lines", required=True, timeout_seconds=30, threshold=90
                            ),
                        ],
                    },
                ],
            }
        (directory / name).write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf8", newline="\n"
        )
    return directory


def tree_bytes(root: Path) -> dict[str, tuple[object, ...]]:
    """Complete small fixture projection; observe links instead of following them."""
    result = {}
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in (*directories, *files):
            path = Path(directory) / name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                result[relative] = ("link", os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                result[relative] = ("directory", info.st_dev, info.st_ino)
            else:
                result[relative] = (
                    "file",
                    info.st_dev,
                    info.st_ino,
                    info.st_mtime_ns,
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
    return result


def environment(root: Path) -> dict[str, str]:
    home, temporary = root / "home", root / "tmp"
    home.mkdir(exist_ok=True)
    temporary.mkdir(exist_ok=True)
    git = shutil.which("git")
    assert git, "Git is required for the real synthetic repository"
    paths = [str(Path(git).absolute().parent)]
    result = {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "roaming"),
        "LOCALAPPDATA": str(home / "local"),
        "TMP": str(temporary),
        "TEMP": str(temporary),
        "TMPDIR": str(temporary),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "CI": "1",
        "NO_COLOR": "1",
    }
    for key in ("SystemRoot", "WINDIR", "SystemDrive", "ProgramFiles", "ProgramFiles(x86)"):
        if key in os.environ:
            result[key] = os.environ[key]
    if os.name == "nt":
        system = Path(result["SystemRoot"])
        paths.extend((str(system / "System32"), str(system / "System32/WindowsPowerShell/v1.0")))
    else:
        paths.extend(("/usr/bin", "/bin"))
    result["PATH"] = os.pathsep.join(paths)
    return result


@dataclass(frozen=True)
class InstalledNodeEngine:
    python: Path
    state: Path

    def run(
        self,
        repository: Path,
        code: str,
        *arguments: str,
        git_directory: Path | None = None,
    ) -> dict:
        import coverage

        active = coverage.Coverage.current()
        data_file = self.state / (".coverage-node-" + uuid4().hex)
        if active is not None:
            # Load the instrumentation package alone, without exposing the parent
            # site-packages or editable source to the ordinary installed engine.
            wrapper = """
import importlib.util, sys
from pathlib import Path
code, package, data_file = (sys.argv.pop(1) for _ in range(3))
spec = importlib.util.spec_from_file_location('coverage', package,
    submodule_search_locations=[str(Path(package).parent)])
module = importlib.util.module_from_spec(spec)
sys.modules['coverage'] = module
spec.loader.exec_module(module)
collector = module.Coverage(data_file=data_file, branch=True, source=['aiflow'], config_file=False)
collector.start()
try:
    exec(compile(code, '<installed-node-test>', 'exec'), {'__name__': '__main__'})
finally:
    collector.stop()
    collector.save()
"""
            argv = [wrapper, code, str(Path(coverage.__file__)), str(data_file)]
        else:
            argv = [code]
        process_environment = environment(self.state)
        if git_directory is not None:
            process_environment["PATH"] = (
                str(git_directory) + os.pathsep + process_environment["PATH"]
            )
        completed = subprocess.run(
            [str(self.python), "-I", "-B", "-c", *argv, str(repository), *arguments],
            cwd=repository,
            env=process_environment,
            capture_output=True,
            text=True,
            encoding="utf8",
            timeout=900,
            check=False,
        )
        if active is not None and data_file.exists():
            installed = self.python.parents[1] / "Lib/site-packages/aiflow"
            measured = coverage.CoverageData(basename=str(data_file))
            measured.read()

            def source_path(filename: str) -> str:
                path = Path(filename)
                relative = path.resolve().relative_to(installed.resolve())
                source = ROOT / "src/aiflow" / relative
                assert source.read_bytes() == path.read_bytes(), "installed/source bytes differ"
                return str(source.resolve())

            active.get_data().update(measured, map_path=source_path)
        assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
        return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="session")
def installed_node_engine(tmp_path_factory: pytest.TempPathFactory) -> InstalledNodeEngine:
    """One ordinary wheel and offline isolated installation for both levels."""
    if os.name != "nt":
        pytest.skip("real installed Node lifecycle requires Windows x64")
    from test_resource_bundle_distribution import (
        _build,
        _installed_bundle,
        _source,
        _wheelhouse,
    )

    root = tmp_path_factory.mktemp("node-installed")
    wheelhouse = root / "wheelhouse"
    locked = _wheelhouse(wheelhouse)
    source = root / "source"
    _source(source, crlf=False, identity=b"synthetic-node-test-identity")
    wheel = _build(source, root / "wheels", "wheel", root)
    target = root / "environment"
    _installed_bundle(wheel, wheelhouse, locked, target, root)
    return InstalledNodeEngine(target / "Scripts/python.exe", root)


@pytest.fixture(scope="session")
def public_node_materials() -> Path:
    """Opt in with already installed public tools; never discover private target trees.

    AIFLOW_NODE_TEST_MATERIALS contains node/{node.exe,npm.cmd,node_modules/npm}
    and dependencies/node_modules with the fixed public versions. All selected
    material is independently copied and revalidated by the production API.
    Missing opt-in is a dependency skip; an explicitly selected bad tree fails.
    """
    if os.name != "nt":
        pytest.skip("real Node tool material is Windows x64 only")
    selected = os.environ.get("AIFLOW_NODE_TEST_MATERIALS")
    if not selected:
        pytest.skip("set AIFLOW_NODE_TEST_MATERIALS to the fixed public Node/npm/dependency tree")
    root = Path(selected)
    assert root.is_absolute() and root.is_dir()
    for relative in (
        "node/node.exe",
        "node/npm.cmd",
        "node/node_modules/npm/package.json",
        "dependencies/node_modules/.package-lock.json",
    ):
        path = root / relative
        info = path.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        assert not getattr(info, "st_file_attributes", 0) & 0x400
    for role in (root / "node", root / "dependencies"):
        for directory, directories, files in os.walk(role, followlinks=False):
            for name in (*directories, *files):
                path = Path(directory) / name
                info = path.lstat()
                assert not stat.S_ISLNK(info.st_mode)
                assert not getattr(info, "st_file_attributes", 0) & 0x400
                assert stat.S_ISDIR(info.st_mode) or (
                    stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                )
    return root


def synthetic_source(root: Path, materials: Path) -> None:
    """Own source plus the actual installed public lock metadata, never target code."""
    root.mkdir()
    modules = materials / "dependencies/node_modules"
    packages = json.loads((modules / ".package-lock.json").read_text(encoding="utf8"))["packages"]
    dev = {
        name: json.loads((modules / name / "package.json").read_text(encoding="utf8"))["version"]
        for name in ("typescript", "vitest", "vite", "@vitest/coverage-v8", "@types/node")
    }
    package = {
        "name": "synthetic-node-verification",
        "version": "0.0.0",
        "private": True,
        "type": "module",
        "engines": {"node": ">=24 <25"},
        "packageManager": "npm@11.13.0",
        "devDependencies": dev,
        "scripts": {
            "clean": "node scripts/clean.mjs",
            "build": "npm run clean && tsc -p tsconfig.json",
            "test": "vitest run --no-cache --configLoader=native",
            "typecheck": "tsc -p tsconfig.json --noEmit && tsc -p tsconfig.tests.json",
            "docs:check": "node scripts/docs.mjs",
            "check": "npm run typecheck && npm test && npm run docs:check",
        },
    }
    packages = {
        "": {"name": package["name"], "version": "0.0.0", "devDependencies": dev},
        **packages,
    }
    config = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "NodeNext",
            "moduleResolution": "NodeNext",
            "rootDir": "src",
            "outDir": "dist",
            "strict": True,
            "sourceMap": True,
            "declaration": True,
            "declarationMap": True,
            "skipLibCheck": True,
        },
        "include": ["src/**/*.ts"],
    }
    documents = {
        "package.json": package,
        "package-lock.json": {
            "name": package["name"],
            "version": "0.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": packages,
        },
        "tsconfig.json": config,
        "tsconfig.tests.json": {
            "compilerOptions": {**config["compilerOptions"], "rootDir": ".", "noEmit": True},
            "include": ["src/**/*.ts", "tests/**/*.ts"],
        },
        "agent-commands.json": {"commands": []},
    }
    for relative, value in documents.items():
        (root / relative).write_text(
            json.dumps(value, indent=2) + "\n", encoding="utf8", newline="\n"
        )
    files = {
        ".gitattributes": "* text eol=lf\n",
        ".gitignore": "node_modules/\ndist/\n.runtime/\n.ai/tasks/*/logs/\n",
        "README.md": "Synthetic Node verification fixture.\n",
        "src/local/add.ts": "export function add(a: number, b: number): number {\n"
        "  return a + b;\n}\n",
        "tests/local/add.test.ts": 'import { expect, it } from "vitest";\n'
        'import { add } from "../../src/local/add.js";\n'
        'it("adds", () => { expect(add(2, 3)).toBe(5); });\n',
        "vitest.config.ts": 'import { defineConfig } from "vitest/config";\n'
        "export default defineConfig({ test: {\n"
        'include: ["tests/local/**/*.test.ts"], maxWorkers: 1 } });\n',
        "scripts/clean.mjs": 'import { rmSync } from "node:fs";\n'
        'rmSync("dist", {recursive:true,force:true});\n',
        "scripts/docs.mjs": 'import { readFileSync } from "node:fs";\n'
        'if (!readFileSync("README.md", "utf8")\n'
        '.startsWith("Synthetic Node verification fixture.")) process.exit(1);\n',
    }
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf8", newline="\n")


@pytest.fixture(scope="session")
def independent_node_git(
    tmp_path_factory: pytest.TempPathFactory, public_node_materials: Path
) -> Path:
    """Copy public Git binaries so standard installation hardlinks are not trusted.

    Initialization retains its original outside-repository Git. Only subsequent
    Node verification uses these explicit ordinary copies inside the test tree.
    """
    del public_node_materials  # Preserve the public-material opt-in before copying tools.
    executable = shutil.which("git")
    assert executable, "Git is required for installed Node verification"
    entry = Path(executable).absolute()
    if entry.parent.name.casefold() == "cmd":
        source = entry.parent.parent
    else:
        assert entry.parent.name.casefold() == "bin"
        assert entry.parent.parent.name.casefold() == "mingw64"
        source = entry.parent.parent.parent
    target = tmp_path_factory.mktemp("g")
    for relative in ("cmd", "mingw64/bin", "usr/bin"):
        for directory, directories, files in os.walk(source / relative, followlinks=False):
            for name in (*directories, *files):
                info = (Path(directory) / name).lstat()
                assert not stat.S_ISLNK(info.st_mode)
                assert not getattr(info, "st_file_attributes", 0) & 0x400
        shutil.copytree(source / relative, target / relative, copy_function=shutil.copyfile)
    for relative in (
        "cmd/git.exe",
        "mingw64/bin/git.exe",
        "mingw64/bin/git-upload-pack.exe",
        "usr/bin/sh.exe",
    ):
        copied = target / relative
        assert copied.read_bytes() == (source / relative).read_bytes()
        assert copied.lstat().st_nlink == 1
    return target / "cmd"
