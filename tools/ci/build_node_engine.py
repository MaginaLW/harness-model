"""Build the fixed, authenticated public Node engine artifact.

Run with the locked build-tools Python, outside any ordinary engine runtime:
    python -I -B source/tools/ci/build_node_engine.py --output-dir DIR

Only an actual same-repository pull-request Actions job may publish this shape.
Environment IDs are selectors; the package-owned official-client adapter fetches
their live GitHub association. Build from committed blobs in a disposable sibling
of the protected source checkout. The output has exactly four regular members.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, BinaryIO

if TYPE_CHECKING:
    from aiflow.process_runner import NodeProcessResult

SOURCE_REPOSITORY_ID = 1319293089
SOURCE_FULL_NAME = "MaginaLW/harness-model"
WORKFLOW_PATH = ".github/workflows/node-engine-artifacts.yml"
JOB_KEY = "node-engine-artifacts"
WHEEL = "aiflow-0.2.0-py3-none-any.whl"
SDIST = "aiflow-0.2.0.tar.gz"
GENERATED_SETUP_CONFIG = b"[egg_info]\ntag_build = \ntag_date = 0\n\n"
PAYLOADS = (
    ("direct/" + WHEEL, "direct"),
    ("sdist/" + SDIST, "source"),
    ("sdist-rebuilt/" + WHEEL, "sdist_rebuilt"),
)
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 20_000
_STDOUT_LIMIT = 16 * 1024 * 1024
BUILD_TOOLS = (
    "build",
    "setuptools",
    "wheel",
    "pyyaml",
    "packaging",
    "pyproject-hooks",
    "colorama",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _ordinary(path: Path, *, directory: bool) -> None:
    """Reject links/reparse points throughout an existing physical path."""
    for item in reversed((path, *path.parents)):
        if not os.path.lexists(item):
            continue
        info = item.lstat()
        _require(
            not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
            "Build path contains a link or reparse point",
        )
        if item == path and not directory:
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "Not an ordinary file")
        else:
            _require(stat.S_ISDIR(info.st_mode), "Not an ordinary directory")


class _JobFailure(ValueError):
    """Actual finite process originals awaiting retention by the authenticated caller."""

    def __init__(
        self,
        message: str,
        result: NodeProcessResult,
        stdout: bytes | None = None,
        *,
        retained: bool = False,
    ) -> None:
        super().__init__(message)
        self.result = result
        self.stdout = stdout
        self.stderr = result.stderr
        self.retained = retained


def _run_job(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: int,
    stdout_sink: BinaryIO,
) -> NodeProcessResult:
    """Use the existing Job/pipe/teardown state machine, with its fixed stderr cap."""
    from aiflow import process_runner

    expected = Path(__file__).resolve().parents[2] / "src/aiflow/process_runner.py"
    _require(
        Path(process_runner.__file__).resolve() == expected, "Unexpected process runner origin"
    )
    return process_runner.run_node_process(
        argv,
        cwd=cwd,
        environment=environment,
        timeout_seconds=timeout_seconds,
        stdout_sink=stdout_sink,
        stdout_limit=_STDOUT_LIMIT,
    )


def _job_succeeded(result: NodeProcessResult) -> bool:
    receipt = result.receipt
    pid = receipt.get("process_id") if receipt is not None else None
    created = receipt.get("creation_time_filetime") if receipt is not None else None
    return (
        type(result.returncode) is int
        and result.returncode == 0
        and result.stdout == b""
        and result.timed_out is False
        and result.stdout_overflow is False
        and result.stderr_overflow is False
        and result.execution_error is False
        and result.cleanup == "confirmed"
        and receipt is not None
        and type(pid) is int
        and pid > 0
        and type(created) is int
        and created > 0
        and all(
            receipt.get(key) is True
            for key in (
                "created_suspended",
                "assigned",
                "initial_membership",
                "resumed",
                "job_empty",
                "stdout_eof",
                "stderr_eof",
                "closed",
            )
        )
        and receipt.get("terminate_requested") is False
    )


def _retain_job(
    work: Path, label: str, result: NodeProcessResult, stdout: bytes | None = None
) -> None:
    """Keep actual bounded raw partials and the unchanged closed Job receipt."""
    _ordinary(work, directory=True)
    stdout_path = work / (label + ".stdout.raw")
    stderr_path = work / (label + ".stderr.raw")
    if stdout is not None:
        _require(len(stdout) <= _STDOUT_LIMIT, "Git output exceeded its finite sink")
        with stdout_path.open("xb") as stream:
            stream.write(stdout)
    _ordinary(stdout_path, directory=False)
    _require(stdout_path.stat().st_size <= _STDOUT_LIMIT, "Build output exceeded its finite sink")
    _require(len(result.stderr) <= 1024 * 1024, "Build stderr exceeded its fixed bound")
    with stderr_path.open("xb") as stream:
        stream.write(result.stderr)
    value = {
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "stdout_overflow": result.stdout_overflow,
        "stderr_overflow": result.stderr_overflow,
        "execution_error": result.execution_error,
        "cleanup": result.cleanup,
        "receipt": dict(result.receipt) if result.receipt is not None else None,
        "stdout": {
            "path": stdout_path.name,
            "size": stdout_path.stat().st_size,
            "sha256": _sha(stdout_path.read_bytes()),
        },
        "stderr": {
            "path": stderr_path.name,
            "size": len(result.stderr),
            "sha256": _sha(result.stderr),
        },
    }
    with (work / (label + ".receipt.json")).open("xb") as stream:
        stream.write(_canonical(value))


def _git(source: Path, *arguments: str) -> bytes:
    environment = {
        key: os.environ[key]
        for key in (
            "PATH",
            "SystemRoot",
            "COMSPEC",
            "PATHEXT",
            "TEMP",
            "TMP",
            "TMPDIR",
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "XDG_CACHE_HOME",
            "PYTHONDONTWRITEBYTECODE",
        )
        if key in os.environ
    }
    environment.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_OPTIONAL_LOCKS="0",
        GIT_TERMINAL_PROMPT="0",
        GIT_NO_REPLACE_OBJECTS="1",
    )
    executable = shutil.which("git", path=environment.get("PATH"))
    _require(executable is not None, "Git executable is unavailable")
    assert executable is not None
    with io.BytesIO() as sink:
        result = _run_job(
            (
                str(Path(executable).absolute()),
                "--no-optional-locks",
                "-c",
                "core.fsmonitor=false",
                *arguments,
            ),
            cwd=source,
            environment=environment,
            timeout_seconds=30,
            stdout_sink=sink,
        )
        raw = sink.getvalue()
    if not _job_succeeded(result):
        raise _JobFailure("Committed source Git Job failed", result, raw)
    return raw


def _positive_selector(name: str) -> int:
    value = os.environ.get(name, "")
    _require(re.fullmatch(r"[1-9][0-9]{0,18}", value) is not None, "Invalid Actions selector")
    return int(value)


def _source_files(source: Path, head: str, resources: set[str]) -> dict[str, bytes]:
    """Use the existing package builder's source allowlist, never a whole .ai copy."""
    root_files = {"LICENSE", "pyproject.toml", "setup.py", "MANIFEST.in"}
    files: dict[str, bytes] = {}
    total = 0
    for row in _git(source, "ls-tree", "-rz", head).split(b"\0"):
        if not row:
            continue
        metadata, raw_name = row.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split(" ")
        name = raw_name.decode("utf-8")
        if not (
            name in root_files | resources
            or (name.startswith("src/aiflow/") and name.endswith(".py"))
        ):
            continue
        _require(mode in {"100644", "100755"} and kind == "blob", "Linked package source")
        _require(
            all(part not in {"", ".", ".."} for part in name.split("/"))
            and "\\" not in name
            and ":" not in name,
            "Unsafe source member",
        )
        size = int(_git(source, "cat-file", "-s", blob).decode("ascii"))
        _require(0 <= size <= MAX_FILE_BYTES, "Source member exceeds bound")
        total += size
        _require(total <= MAX_TOTAL_BYTES and len(files) < MAX_ENTRIES, "Source exceeds bound")
        raw = _git(source, "cat-file", "blob", blob)
        _require(len(raw) == size, "Committed source changed during collection")
        files[name] = raw
    _require(root_files | resources <= files.keys(), "Missing required package source")
    return files


def _locked_tools(lock: bytes, project: bytes) -> dict[str, str]:
    document = tomllib.loads(project.decode("utf-8"))
    _require(
        document["build-system"]
        == {
            "requires": ["setuptools>=77", "PyYAML>=6,<7"],
            "build-backend": "setuptools.build_meta",
        },
        "Unsupported build recipe",
    )
    packages = tomllib.loads(lock.decode("utf-8"))["package"]
    installed = {}
    for name in BUILD_TOOLS:
        rows = [item for item in packages if item.get("name") == name]
        _require(len(rows) == 1, "Build tool is not uniquely locked")
        version = rows[0]["version"]
        _require(
            isinstance(version, str)
            and re.fullmatch(r"[0-9][A-Za-z0-9.+!-]{0,63}", version) is not None,
            "Invalid locked tool version",
        )
        _require(importlib.metadata.version(name) == version, "Build tool differs from source lock")
        installed[name] = version
    return installed


def _build(source: Path, output: Path, kind: str, work: Path, environment: dict[str, str]) -> None:
    output.mkdir()
    with (work / (output.name + ".stdout.raw")).open("xb", buffering=0) as stdout:
        result = _run_job(
            (
                sys.executable,
                "-I",
                "-B",
                "-m",
                "build",
                "--no-isolation",
                "--" + kind,
                "--outdir",
                str(output),
                str(source),
            ),
            cwd=work,
            environment=environment,
            timeout_seconds=180,
            stdout_sink=stdout,
        )
        stdout.flush()
        os.fsync(stdout.fileno())
    _retain_job(work, output.name, result)
    if not _job_succeeded(result):
        raise _JobFailure(
            "Ordinary package build Job failed; retain its originals", result, retained=True
        )
    expected = WHEEL if kind == "wheel" else SDIST
    _require({path.name for path in output.iterdir()} == {expected}, "Unexpected build output")
    _ordinary(output / expected, directory=False)
    _require((output / expected).stat().st_size <= MAX_FILE_BYTES, "Build output exceeds bound")


def _unpack_sdist(archive_path: Path, destination: Path, allowed: set[str]) -> Path:
    """Inspect every header before writing the ordinary, single-root source tree."""
    entries = []
    names: set[str] = set()
    total = 0
    with tarfile.open(archive_path, "r:gz") as archive:
        for item in archive:
            parts = item.name.split("/")
            if item.isdir() and parts[-1] == "":
                parts.pop()
            _require(
                bool(parts)
                and parts[0] == "aiflow-0.2.0"
                and all(part not in {"", ".", ".."} for part in parts)
                and not any(part.endswith((".", " ")) for part in parts)
                and not any("\\" in part or ":" in part for part in parts),
                "Unsafe source archive member",
            )
            relative = "/".join(parts[1:])
            _require(item.isfile() or item.isdir(), "Unsupported source archive entry")
            alias = "/".join(parts).casefold()
            _require(alias not in names and len(names) < MAX_ENTRIES, "Duplicate source member")
            names.add(alias)
            if item.isfile():
                _require(
                    relative in allowed | {"PKG-INFO", "setup.cfg"},
                    "Unexpected source archive payload",
                )
                _require(0 <= item.size <= MAX_FILE_BYTES, "Source member exceeds bound")
                if relative == "setup.cfg":
                    stream = archive.extractfile(item)
                    if stream is None:
                        raise ValueError("Missing generated source configuration")
                    with stream:
                        raw = stream.read(len(GENERATED_SETUP_CONFIG) * 2 + 1)
                    _require(
                        raw
                        in {
                            GENERATED_SETUP_CONFIG,
                            GENERATED_SETUP_CONFIG.replace(b"\n", b"\r\n"),
                        },
                        "Unsupported generated source configuration",
                    )
                total += item.size
                _require(total <= MAX_TOTAL_BYTES, "Expanded source exceeds bound")
            else:
                _require(
                    not relative or any(name.startswith(relative + "/") for name in allowed),
                    "Unexpected source directory",
                )
            entries.append((item, parts))
        _require(
            allowed <= {item.name.split("/", 1)[1] for item, _ in entries if item.isfile()},
            "Incomplete source archive",
        )
        destination.mkdir()
        for item, parts in entries:
            target = destination.joinpath(*parts)
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = archive.extractfile(item)
            if stream is None:
                raise ValueError("Missing source archive payload")
            with stream, target.open("xb") as output:
                remaining = item.size
                while remaining:
                    raw = stream.read(min(1024 * 1024, remaining))
                    _require(bool(raw), "Truncated source archive payload")
                    output.write(raw)
                    remaining -= len(raw)
    return destination / "aiflow-0.2.0"


def build_engine(output_dir: Path) -> dict[str, Any]:
    source = Path(__file__).resolve().parents[2]
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    _require(
        source == workspace / "source", "Protected source must be the workflow source checkout"
    )
    _require(sys.flags.isolated == 1 and sys.dont_write_bytecode, "Use the isolated -I -B Python")
    _require(
        sys.platform == "win32" and sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32,
        "Requires Windows CPython3.11 x64",
    )
    _require(
        Path(sys.prefix).resolve() == workspace / "tools/build-env", "Use locked build-tools env"
    )
    _require(os.environ.get("GITHUB_ACTIONS") == "true", "Not an Actions producer")
    _require(os.environ.get("GITHUB_EVENT_NAME") == "pull_request", "Requires pull_request")
    _require(os.environ.get("GITHUB_JOB") == JOB_KEY, "Unexpected producer job")
    for name in (
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "XDG_CACHE_HOME",
        "UV_CACHE_DIR",
        "UV_PROJECT_ENVIRONMENT",
        "GH_CONFIG_DIR",
    ):
        path = Path(os.environ[name]).absolute()
        _ordinary(path, directory=True)
        path = path.resolve()
        _require(
            path.is_relative_to(workspace) and not path.is_relative_to(source),
            "Tool state must remain in workspace siblings",
        )
    run_id, attempt = _positive_selector("GITHUB_RUN_ID"), _positive_selector("GITHUB_RUN_ATTEMPT")
    attempt_root = workspace / ".tmp/node-ci" / f"{run_id}-{attempt}"
    output_dir = output_dir.absolute()
    _require(output_dir == attempt_root / "artifact", "Output must be this attempt's artifact root")
    _ordinary(output_dir, directory=True)
    _require(not os.path.lexists(attempt_root), "An engine-build attempt cannot be reused")

    sys.path.insert(0, str(source / "src"))
    from aiflow.node_ci import (
        authenticate_workflow,
        inspect_engine_wheel,
        validate_engine_artifact_archive,
        validate_node_ci_document,
    )
    from aiflow.resource_bundle import RESOURCE_KINDS

    platform = authenticate_workflow(
        SOURCE_REPOSITORY_ID,
        SOURCE_FULL_NAME,
        WORKFLOW_PATH,
        JOB_KEY,
        run_id=run_id,
        attempt=attempt,
        completed=False,
    )
    work = attempt_root / "build"
    created_here = False
    try:
        head = _git(source, "rev-parse", "HEAD").decode("ascii").strip()
        _require(platform["head_sha"] == head, "Authenticated PR/run and checkout heads differ")
        branch = os.environ.get("GITHUB_HEAD_REF", "")
        _git(source, "check-ref-format", "--branch", branch)
        _require(
            _git(source, "symbolic-ref", "--short", "HEAD").decode("utf-8").strip() == branch,
            "Exact PR branch is not attached",
        )
        _require(
            platform["workflow_path"] == WORKFLOW_PATH and platform["job_key"] == JOB_KEY,
            "Unexpected authenticated workflow/job",
        )
        _require(_git(source, "diff", "--name-only") == b"", "Dirty source checkout")
        _require(_git(source, "diff", "--cached", "--name-only") == b"", "Dirty source index")
        _require(
            _git(source, "ls-files", "--others", "--exclude-standard", "-z") == b"",
            "Unregistered source files",
        )
        workflow = _git(source, "show", head + ":" + WORKFLOW_PATH)
        _require(
            _sha(workflow) == platform["workflow_sha256"], "Executing workflow differs from source"
        )
        lock = _git(source, "show", head + ":uv.lock")
        files = _source_files(source, head, {".ai/" + name for name in RESOURCE_KINDS})
        versions = _locked_tools(lock, files["pyproject.toml"])
        timestamp = _git(source, "show", "-s", "--format=%ct", head).decode("ascii").strip()
        _require(timestamp.isdecimal() and int(timestamp) >= 315532800, "Invalid source timestamp")

        attempt_root.mkdir(parents=True)
        created_here = True
        work.mkdir()
        output_dir.mkdir()
        staging = work / "source"
        staging.mkdir()
        for name, raw in files.items():
            target = staging.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
        environment = {
            key: os.environ[key]
            for key in (
                "PATH",
                "SystemRoot",
                "COMSPEC",
                "PATHEXT",
                "TEMP",
                "TMP",
                "TMPDIR",
                "HOME",
                "USERPROFILE",
                "APPDATA",
                "LOCALAPPDATA",
                "XDG_CACHE_HOME",
            )
            if key in os.environ
        }
        environment.update(
            PYTHONDONTWRITEBYTECODE="1",
            SOURCE_DATE_EPOCH=timestamp,
            PIP_NO_INDEX="1",
            PIP_CONFIG_FILE=os.devnull,
        )
        _build(staging, output_dir / "direct", "wheel", work, environment)
        _build(staging, output_dir / "sdist", "sdist", work, environment)
        rebuilt_source = _unpack_sdist(output_dir / "sdist" / SDIST, work / "unpacked", set(files))
        _build(rebuilt_source, output_dir / "sdist-rebuilt", "wheel", work, environment)
        direct = inspect_engine_wheel(output_dir / "direct" / WHEEL)
        rebuilt = inspect_engine_wheel(output_dir / "sdist-rebuilt" / WHEEL)
        _require(direct == rebuilt, "Direct and rebuilt package/resource payloads differ")
        members = []
        for name, origin in PAYLOADS:
            raw = (output_dir / name).read_bytes()
            members.append({"path": name, "origin": origin, "size": len(raw), "sha256": _sha(raw)})
        manifest = {
            "kind": "aiflow-node-engine-build",
            "schema_version": "1.0",
            "repository_id": SOURCE_REPOSITORY_ID,
            "source_head": head,
            "workflow_path": WORKFLOW_PATH,
            "workflow_blob_sha256": _sha(workflow),
            "job_key": JOB_KEY,
            "run_id": run_id,
            "run_attempt": attempt,
            "python_version": list(sys.version_info[:3]),
            "setuptools_version": versions["setuptools"],
            "members": members,
            "package_payload_sha256": direct["package_payload_sha256"],
            "resource_manifest_sha256": direct["resource_manifest_sha256"],
        }
        validate_node_ci_document(manifest, kind="aiflow-node-engine-build")
        with (output_dir / "build-manifest.json").open("xb") as stream:
            stream.write(_canonical(manifest))
        expected = {name for name, _ in PAYLOADS} | {"build-manifest.json"}
        _require(
            {p.relative_to(output_dir).as_posix() for p in output_dir.rglob("*") if p.is_file()}
            == expected,
            "Engine artifact membership is not closed",
        )
        # Validate the exact upload container with the same portable reader used by
        # admission/selection. This local ZIP is outside the four-member artifact.
        archive_path = work / "engine-artifact.zip"
        with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_STORED) as archive:
            for name in sorted(expected):
                archive.write(output_dir / name, name)
        validate_engine_artifact_archive(archive_path)
        _require(_git(source, "rev-parse", "HEAD").decode().strip() == head, "Source head changed")
        _require(_git(source, "diff", "--name-only") == b"", "Source changed during build")
        _require(_git(source, "diff", "--cached", "--name-only") == b"", "Source index changed")
        _require(
            _git(source, "ls-files", "--others", "--exclude-standard", "-z") == b"",
            "Source acquired unregistered files during build",
        )
        return manifest
    except _JobFailure as error:
        if not error.retained:
            # Authentication and exact workspace/output validation already passed.
            # An exclusive creation avoids touching another invocation's attempt.
            if not created_here:
                attempt_root.mkdir(parents=True)
                work.mkdir()
            _require(error.stdout is not None, "Missing bounded Git failure originals")
            _retain_job(work, "git-failure", error.result, error.stdout)
            error.retained = True
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    arguments = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from aiflow.errors import AiflowError

    try:
        manifest = build_engine(arguments.output_dir)
    except (
        KeyError,
        OSError,
        ValueError,
        subprocess.SubprocessError,
        tarfile.TarError,
        AiflowError,
    ) as error:
        # No authenticated API responses, environment values or tool stderr are
        # echoed. Build logs remain in the owned sibling, outside public payload.
        print("Node engine artifact build rejected (" + type(error).__name__ + ")", file=sys.stderr)
        return 2
    print(_canonical(manifest).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
