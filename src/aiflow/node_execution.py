"""Owned, local execution and read-only replay of the closed Node profile.

Private material manifests deliberately remain under the task's ignored logs.
Public evidence contains only fixed relative references and compact digests.
"""

from __future__ import annotations

import base64
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from time import monotonic_ns
from typing import TYPE_CHECKING, Any, cast

from aiflow.errors import AiflowError, ContractError
from aiflow.evidence import EvidenceFacts
from aiflow.node_verification import (
    COVERAGE_ISTANBUL_METHOD,
    COVERAGE_METHOD,
    PRODUCT_TESTS,
    _ordered_paths,
    _path,
    validate_node_istanbul_line_coverage,
    validate_node_line_coverage,
    validate_node_product_tests,
)
from aiflow.policy import PolicyBundle, load_policy_bundle
from aiflow.process_runner import run_node_process
from aiflow.verification import VerificationContext, parse_verification_plan

if TYPE_CHECKING:
    from aiflow.installed_mutations import (
        InstalledMutationCurrent,
        InstalledMutationFacts,
        InstalledMutationReference,
    )

MAX_ENTRIES = 20_000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_PREPARED_BYTES = 64 * 1024
MANIFEST_NAMES = (
    "source.json",
    "node.json",
    "npm.json",
    "dependencies.json",
    "engine.json",
    "host-tools.json",
    "preflight.json",
)
PROFILE = {"id": "agent-bridge-node", "revision": 1}
PROFILE_V2 = {"id": "agent-bridge-node", "revision": 2}
NODE_V2_CONFIG_SHA256 = "74bed4fc135f16dd29e85987c221ab2d877a778fa44e774dcc5dbc4a646654ed"
NATIVE_OWNERSHIP_DIRECTORY = ".runtime/native-ownership"
NATIVE_OWNERSHIP_INPUTS = {
    "scripts/windows-owned-launcher.cs": (
        "7972a55b7a45bd00e557eae709d228c69f04f460c8057614ea820bf18da4b8f3"
    ),
    "src/local/ownership/windows-native.ts": (
        "438e19b624334a59e8346f767b5a16eaffa01b811b3b9a4238a94e038f394007"
    ),
}
ISTANBUL_PACKAGES = {
    "@vitest/coverage-istanbul": "4.1.10",
    "@babel/core": "7.29.7",
    "@babel/parser": "7.29.12",
    "@jridgewell/trace-mapping": "0.3.31",
    "istanbul-lib-coverage": "3.2.2",
    "@istanbuljs/schema": "0.1.6",
}
ISTANBUL_FILES = {
    "@vitest/coverage-istanbul/dist/provider.js": (
        "9ab927dcd749855046ed01e49d31ecde70ab900614f2e109a5b1fc4aa0a5a09b"
    ),
    "@babel/parser/lib/index.js": (
        "86bfb625edc968a1bf7c7bb0caa54a94395cb1b21493ef44845e51546f701730"
    ),
    "@istanbuljs/schema/index.js": (
        "197006c28b6b2073a3d379536fdeb5fde36359307725af2f531bb23b92b8e945"
    ),
    "vitest/dist/chunks/index.UpGiHP7g.js": (
        "cdafaf8e508042dddba72f8c7bbae84e2836ddb6b06c7026520c35d91af4e798"
    ),
}
VERSIONS = {"node": "24.20.0", "npm": "11.13.0", "vitest": "4.1.10", "vite": "8.2.1"}
SEMANTIC_CONTRACT = {
    "profile": PROFILE,
    "versions": VERSIONS,
    "coverage_method": COVERAGE_METHOD,
    "limits": {"entries": MAX_ENTRIES, "file": MAX_FILE_BYTES, "total": MAX_TOTAL_BYTES},
    "test_script": "vitest run --no-cache --configLoader=native",
    "source": "subject-tracked-regular-files",
    "runtime": "official-node-npm-windows",
    "execution": "owned-clone-copy-offline-v1",
    "engine_startup": "only-exact-RECORD-distutils-precedence-plus-complete-setuptools-v1",
    "node_compile_cache": {"NODE_DISABLE_COMPILE_CACHE": "1"},
    "dist_rebuild": {
        "roles": ["node_check", "ts_coverage"],
        "execution": "successful-exact-primary-check-argv-only",
        "content": "canonical-complete-path-kind-size-sha256-equal-to-build-dist",
        "initial_inventory": "outputs.build_dist",
        "final_inventory": "outputs.dist",
        "other_phases": "full-identity-unchanged",
    },
    "original_root": "complete-metadata-native-change-time-exact-run-audit-git-delta-v1",
    "code_approval_marker": {
        "path": "TASK/approval_pending.json",
        "validation": "closed-current-code-transaction-review-evidence-replay-v1",
    },
    "coverage_end_column": {
        "null": "bound-source-line-utf16-length-before-CR-LF",
        "roles": [
            "statementMap.end",
            "fnMap.decl.end",
            "fnMap.loc.end",
            "branchMap.loc.end",
            "branchMap.locations[].end",
        ],
        "other_coordinates": "strict-integer-utf16-boundary",
        "original_report": "unchanged-bytes-and-digest",
    },
}
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_GIT_OPTIONS = ("--no-optional-locks", "-c", "core.fsmonitor=false")
_OS_TOOL_PATHS = {
    "cmd": "System32/cmd.exe",
    "powershell": "System32/WindowsPowerShell/v1.0/powershell.exe",
    "csc": "Microsoft.NET/Framework64/v4.0.30319/csc.exe",
    "cvtres": "Microsoft.NET/Framework64/v4.0.30319/cvtres.exe",
    "conhost": "System32/conhost.exe",
}
SEMANTIC_CONTRACT["host_os_boundary"] = {
    "root": "GetWindowsDirectoryW",
    "executables": _OS_TOOL_PATHS,
    "optional_configs": "same-named.exe.config",
    "nlink": "positive-for-exact-os-roles-only",
}
SEMANTIC_CONTRACT["git_roles"] = {
    "entry": "ROOT/cmd/git.exe-or-ROOT/mingw64/bin/git.exe",
    "backend": "ROOT/mingw64/bin/git.exe",
    "upload_pack": "ROOT/mingw64/bin/git-upload-pack.exe",
    "shell": "ROOT/usr/bin/sh.exe",
    "exec_path": "ROOT/mingw64/bin",
}
SEMANTIC_CONTRACT["git_inputs"] = {
    "system_global_config": "disabled",
    "fsmonitor": "false",
    "templates": "empty",
    "source_hooks": "ordinary-sample-files-only",
}


@dataclass(frozen=True)
class NodeEvidenceFacts:
    """Original-material replay result; no check or mutation is re-executed."""

    current: bool
    passed: bool
    reason_codes: tuple[str, ...]
    evidence_sha256: str | None
    materials_sha256: str | None
    run_id: str | None
    installed_mutation_facts: InstalledMutationFacts | None = None


def _error(message: str, code: str = "NODE_MATERIALS_INVALID") -> ContractError:
    return ContractError(message, code=code)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


SEMANTIC_CONTRACT_SHA256 = _sha(_canonical(SEMANTIC_CONTRACT))
SEMANTIC_CONTRACT_V2 = {
    **SEMANTIC_CONTRACT,
    "profile": PROFILE_V2,
    "coverage_method": COVERAGE_ISTANBUL_METHOD,
    "coverage_packages": ISTANBUL_PACKAGES,
    "coverage_files": ISTANBUL_FILES,
    "source_config_sha256": NODE_V2_CONFIG_SHA256,
    "implicit_else_finite_end": {
        "exact": "original-ts-if-end",
        "one_space_after": "original-ts-if-end+1-only-U+0020",
        "semicolon_before": "original-ts-if-end-1-only-U+003B-final-Babel-semicolon-token",
        "token_span": "[node.end-1,node.end)",
        "reader_trust": "authenticated-fixed-producer-AST-span-and-bound-source-UTF16-geometry",
    },
    "product_tests": PRODUCT_TESTS,
    "execution": "owned-imut-node-copy-offline-v2",
    "node_inventory": "closed-path-kind-size-sha256-excluding-run-json",
    "native_ownership_output": {
        "directory": NATIVE_OWNERSHIP_DIRECTORY,
        "inputs": NATIVE_OWNERSHIP_INPUTS,
        "applicability": "both-absent-forbidden-or-exact-pair-mandatory-after-node-check",
        "files": ["own-<source-sha256>.exe", "own-<source-sha256>.exe.json"],
        "sidecar": "sourceHash-first-executableHash-second-compact-json-one-LF",
        "host_roles": [
            "powershell",
            "powershell_config",
            "csc",
            "csc_config",
            "cvtres",
            "cvtres_config",
        ],
        "seal": "first-successful-fixed-node-check-unchanged-through-plan-and-replay",
        "trust": "same-reviewed-source-tool-and-fixed-process-output-model-as-dist",
    },
}
SEMANTIC_CONTRACT_V2_SHA256 = _sha(_canonical(SEMANTIC_CONTRACT_V2))


def _profile_revision(binding: Mapping[str, Any]) -> int:
    profile = _canonical(binding.get("profile"))
    if profile == _canonical(PROFILE):
        return 1
    if profile == _canonical(PROFILE_V2):
        return 2
    raise _error("Node profile binding is unsupported")


def _semantic_digest(binding: Mapping[str, Any]) -> str:
    return (
        SEMANTIC_CONTRACT_SHA256 if _profile_revision(binding) == 1 else SEMANTIC_CONTRACT_V2_SHA256
    )


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _error("Duplicate JSON member")
        result[key] = value
    return result


def _constant(_value: str) -> None:
    raise _error("Non-finite JSON number")


def _json_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise _error("Non-finite JSON number")
    return result


def _json_bytes(data: bytes) -> Any:
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_constant=_constant,
            parse_float=_json_float,
        )
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, str):
                item.encode("utf-8", errors="strict")
            elif isinstance(item, dict):
                pending.extend(item)
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        return value
    except (UnicodeError, ValueError, RecursionError) as error:
        raise _error("Invalid bounded UTF-8 JSON") from error


def _identity(info: os.stat_result) -> dict[str, int]:
    return {
        "device": info.st_dev,
        "inode": info.st_ino,
        "nlink": info.st_nlink,
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "ctime_ns": info.st_ctime_ns,
        # Windows lstat infers execute bits from .exe/.cmd suffixes; handle fstat
        # has no filename and cannot report those inferred bits.
        "mode": info.st_mode & ~0o111 if os.name == "nt" else info.st_mode,
        "attributes": getattr(info, "st_file_attributes", 0),
    }


def _windows_root() -> Path:
    if os.name != "nt":
        raise _error("Windows host roles are unavailable", "NODE_HOST_UNSUPPORTED")
    import ctypes
    from ctypes import wintypes

    kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
    kernel.GetWindowsDirectoryW.argtypes = (wintypes.LPWSTR, wintypes.UINT)
    kernel.GetWindowsDirectoryW.restype = wintypes.UINT
    buffer = ctypes.create_unicode_buffer(32768)
    count = kernel.GetWindowsDirectoryW(buffer, len(buffer))
    if not 0 < count < len(buffer):
        raise _error("The Windows host root is unavailable", "NODE_HOST_UNSUPPORTED")
    root = Path(buffer.value)
    if not root.is_absolute():
        raise _error("The Windows host root is not absolute", "NODE_HOST_UNSUPPORTED")
    return root


def _os_tool_paths() -> dict[str, Path]:
    root = _windows_root()
    paths = {role: root / relative for role, relative in _OS_TOOL_PATHS.items()}
    return {
        **paths,
        **{role + "_config": Path(str(path) + ".config") for role, path in paths.items()},
    }


def _safe_info(
    path: Path, *, directory: bool = False, os_role: str | None = None
) -> os.stat_result:
    if os_role is not None and (directory or _os_tool_paths().get(os_role) != path):
        raise _error("Host OS role does not match its fixed API-derived file")
    try:
        info = path.lstat()
    except OSError as error:
        raise _error("Material file or directory is missing or unreadable") from error
    if (
        getattr(info, "st_file_attributes", 0) & 0x400
        or stat.S_ISLNK(info.st_mode)
        or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        or (
            not directory
            and (
                type(info.st_nlink) is not int
                or info.st_nlink < 1
                or (os_role is None and info.st_nlink != 1)
            )
        )
    ):
        raise _error("Material is not an independent ordinary file or directory")
    return info


def _ancestors(path: Path) -> None:
    for ancestor in (path, *path.parents):
        _safe_info(ancestor, directory=True)


def _read(path: Path, *, limit: int = MAX_FILE_BYTES, os_role: str | None = None) -> bytes:
    _ancestors(path.parent)
    before = _safe_info(path, os_role=os_role)
    if before.st_size > limit:
        raise _error("Material file exceeds its byte limit")
    chunks: list[bytes] = []
    total = 0
    try:
        with path.open("rb") as stream:
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise _error("Material file changed while opening")
            while chunk := stream.read(min(1024 * 1024, limit + 1 - total)):
                total += len(chunk)
                if total > limit:
                    raise _error("Material file exceeds its byte limit")
                chunks.append(chunk)
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise _error("Material file changed while reading")
    except OSError as error:
        raise _error("Material file could not be read") from error
    if _identity(_safe_info(path, os_role=os_role)) != _identity(before) or total != before.st_size:
        raise _error("Material file changed while reading")
    return b"".join(chunks)


def _json(path: Path, *, limit: int = MAX_JSON_BYTES) -> Any:
    return _json_bytes(_read(path, limit=limit))


def _take_budget(budget: list[int], size: int = 0) -> None:
    if size > MAX_FILE_BYTES or budget[0] < 1 or budget[1] < size:
        raise _error("Combined material inventory exceeds its entry or byte limit")
    budget[0] -= 1
    budget[1] -= size


def _inventory(root: Path, *, budget: list[int] | None = None) -> dict[str, Any]:
    """Enumerate every item, including directories, before trusting a manifest."""
    _ancestors(root)
    rows: list[dict[str, object]] = []
    total = 0
    if budget is None:
        budget = [MAX_ENTRIES, MAX_TOTAL_BYTES]
    pending = [root]
    while pending:
        directory = pending.pop()
        before = _identity(_safe_info(directory, directory=True))
        with os.scandir(directory) as children:
            for child in children:
                if len(rows) >= MAX_ENTRIES:
                    raise _error("Material tree exceeds its entry limit")
                path = Path(child.path)
                relative = _path(path.relative_to(root).as_posix())
                # DirEntry.stat() reports zero identity fields on some Windows versions.
                info = path.lstat()
                if stat.S_ISDIR(info.st_mode):
                    _take_budget(budget)
                    _safe_info(path, directory=True)
                    rows.append(
                        {"path": relative, "kind": "directory", "identity": _identity(info)}
                    )
                    pending.append(path)
                else:
                    _safe_info(path)
                    if info.st_size > MAX_FILE_BYTES or total + info.st_size > MAX_TOTAL_BYTES:
                        raise _error("Material tree exceeds its byte limit")
                    _take_budget(budget, info.st_size)
                    data = _read(path)
                    total += len(data)
                    rows.append(
                        {
                            "path": relative,
                            "kind": "file",
                            "identity": _identity(info),
                            "size": len(data),
                            "sha256": _sha(data),
                        }
                    )
        if _identity(_safe_info(directory, directory=True)) != before:
            raise _error("Material directory changed during enumeration")
    rows.sort(key=lambda row: str(row["path"]).encode("utf-8"))
    aliases: set[str] = set()
    for row in rows:
        folded = str(row["path"]).casefold()
        if folded in aliases:
            raise _error("Material tree contains path aliases")
        aliases.add(folded)
    return {
        "root": str(root),
        "identity": _identity(_safe_info(root, directory=True)),
        "entries": rows,
        "total_bytes": total,
    }


def _content(inventory: Mapping[str, Any]) -> list[dict[str, object]]:
    return [
        {key: row[key] for key in ("path", "kind", "size", "sha256") if key in row}
        for row in inventory["entries"]
    ]


def _unchanged(inventory: Mapping[str, Any]) -> None:
    if _canonical(_inventory(Path(inventory["root"]))) != _canonical(inventory):
        raise _error("Bound material tree has changed", "NODE_MATERIALS_DRIFT")


def _write_new(path: Path, data: bytes) -> None:
    _ancestors(path.parent)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _git_role_paths(entry: Path) -> dict[str, Path]:
    if not entry.is_absolute() or entry.name.casefold() != "git.exe":
        raise _error("The fixed Git role does not have a supported installed layout")
    if entry.parent.name.casefold() == "cmd":
        root = entry.parent.parent
    elif entry.parent.name.casefold() == "bin" and entry.parent.parent.name.casefold() == "mingw64":
        root = entry.parent.parent.parent
    else:
        raise _error("The fixed Git role does not have a supported installed layout")
    return {
        "git": entry,
        "git_backend": root / "mingw64/bin/git.exe",
        "git_upload_pack": root / "mingw64/bin/git-upload-pack.exe",
        "git_sh": root / "usr/bin/sh.exe",
    }


def _environment(node: Path, checkout: Path, run: Path, git: Path) -> dict[str, str]:
    system = _windows_root() if os.name == "nt" else Path("/unsupported-windows-host")
    return _bound_node_environment(node, checkout, run, git, system, windows=os.name == "nt")


def _bound_node_environment(
    node: Path, checkout: Path, run: Path, git: Path, system: Path, *, windows: bool
) -> dict[str, str]:
    """Construct the producing environment using lexical, already-bound roles."""
    git_roles = _git_role_paths(git) if windows else {"git": git}
    git_directories = tuple(dict.fromkeys(path.parent for path in git_roles.values()))
    home = run / "home"
    temporary = run / "tmp"
    environment = {
        "PATH": (";" if windows else ":").join(
            map(
                str,
                (
                    node.parent,
                    checkout / "node_modules/.bin",
                    *git_directories,
                    system / "System32",
                    system / "System32/WindowsPowerShell/v1.0",
                    system / "Microsoft.NET/Framework64/v4.0.30319",
                ),
            )
        ),
        "SystemRoot": str(system),
        "COMSPEC": str(system / "System32/cmd.exe"),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData/Roaming"),
        "LOCALAPPDATA": str(home / "AppData/Local"),
        "TEMP": str(temporary),
        "TMP": str(temporary),
        "npm_config_cache": str(run / "cache"),
        "npm_config_update_notifier": "false",
        "npm_config_audit": "false",
        "npm_config_fund": "false",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "nul" if windows else "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TEMPLATE_DIR": "",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "false",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NODE_DISABLE_COMPILE_CACHE": "1",
    }
    if windows:
        environment["GIT_EXEC_PATH"] = str(git_roles["git_backend"].parent)
    return environment


def _process(
    argv: tuple[str, ...], *, cwd: Path, environment: Mapping[str, str], timeout: int, output: Path
) -> dict[str, object]:
    started = monotonic_ns()
    result = run_node_process(argv, cwd=cwd, environment=environment, timeout_seconds=timeout)
    duration = (monotonic_ns() - started) // 1_000_000
    output.mkdir()
    _write_new(output / "stdout.raw", result.stdout)
    _write_new(output / "stderr.raw", result.stderr)
    from aiflow.redaction import redact_text

    _write_new(
        output / "stdout.log", redact_text(result.stdout.decode("utf-8", errors="replace")).encode()
    )
    _write_new(
        output / "stderr.log", redact_text(result.stderr.decode("utf-8", errors="replace")).encode()
    )
    receipt = asdict(result)
    receipt.pop("stdout")
    receipt.pop("stderr")
    receipt["stdout_sha256"] = _sha(result.stdout)
    receipt["stderr_sha256"] = _sha(result.stderr)
    receipt["stdout_size"] = len(result.stdout)
    receipt["stderr_size"] = len(result.stderr)
    receipt["argv"] = list(argv)
    receipt["cwd"] = str(cwd)
    receipt["environment_sha256"] = _sha(_canonical(environment))
    receipt["timeout_seconds"] = timeout
    receipt["duration_ms"] = duration
    _write_new(output / "receipt.json", _canonical(receipt))
    return receipt


def _successful(receipt: Mapping[str, object]) -> bool:
    return (
        type(receipt.get("returncode")) is int
        and receipt["returncode"] == 0
        and receipt.get("cleanup") == "confirmed"
        and all(
            receipt.get(key) is False
            for key in ("timed_out", "execution_error", "stdout_overflow", "stderr_overflow")
        )
    )


def _git(root: Path, *arguments: str) -> bytes:
    """Use the existing trusted Git role only for bounded read-only object queries."""
    git = shutil.which("git")
    if git is None:
        raise _error("Git role is unavailable")
    system = _windows_root() if os.name == "nt" else Path("/unsupported-windows-host")
    environment = {
        "SystemRoot": str(system),
        "PATH": os.pathsep.join((str(Path(git).parent), str(system / "System32"))),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TEMPLATE_DIR": "",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "false",
    }
    if os.name == "nt":
        roles = _git_role_paths(Path(git).absolute())
        environment["GIT_EXEC_PATH"] = str(roles["git_backend"].parent)
        environment["PATH"] = (
            os.pathsep.join(dict.fromkeys((str(path.parent) for path in roles.values())))
            + os.pathsep
            + str(system / "System32")
        )
    result = subprocess.run(
        (git, *_GIT_OPTIONS, *arguments),
        cwd=root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if (
        result.returncode
        or len(result.stdout) > MAX_TOTAL_BYTES
        or len(result.stderr) > 1024 * 1024
    ):
        raise _error("Read-only Git facts are unavailable", "NODE_GIT_INVALID")
    return result.stdout


def _source(root: Path, subject: str, *, budget: list[int] | None = None) -> dict[str, Any]:
    listing = _git(root, "ls-tree", "-rlz", "--full-tree", subject)
    rows: list[dict[str, object]] = []
    total = 0
    if budget is None:
        budget = [MAX_ENTRIES, MAX_TOTAL_BYTES]
    directories: set[str] = set()
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        if len(rows) >= MAX_ENTRIES:
            raise _error("Tracked source inventory is too large")
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, blob, size_text = metadata.decode("ascii").split()
        path = _path(raw_path.decode("utf-8", errors="strict"))
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise _error("Tracked source contains a non-ordinary file")
        size = int(size_text)
        if size > MAX_FILE_BYTES or total + size > MAX_TOTAL_BYTES:
            raise _error("Tracked source exceeds material limits")
        for parent in Path(path).parents:
            if parent.as_posix() != "." and parent.as_posix() not in directories:
                _take_budget(budget)
                directories.add(parent.as_posix())
        _take_budget(budget, size)
        data = _git(root, "cat-file", "blob", blob)
        actual_blob = hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest()
        if len(data) != size or actual_blob != blob:
            raise _error("Git object size changed")
        rows.append({"path": path, "blob": blob, "size": size, "sha256": _sha(data)})
        total += size
    _ordered_paths([str(row["path"]) for row in rows])
    return {
        "subject_commit": subject,
        "subject_tree": _git(root, "rev-parse", f"{subject}^{{tree}}").decode().strip(),
        "files": rows,
        "total_bytes": total,
    }


def _binding(root: Path, task_id: str) -> tuple[dict[str, Any], PolicyBundle]:
    from aiflow.decision_units import parse_decision_units
    from aiflow.freshness import current_classification_input_digest
    from aiflow.policy import is_node_policy
    from aiflow.specification import specification_digest
    from aiflow.storage import read_task_json
    from aiflow.task_service import read_task_record_strict

    record = read_task_record_strict(root, task_id)
    task = record.task
    _ancestors(root)
    git_marker = root / ".git"
    _safe_info(git_marker, directory=git_marker.is_dir())
    for arguments in (
        ("rev-parse", "--absolute-git-dir"),
        ("rev-parse", "--path-format=absolute", "--git-common-dir"),
    ):
        directory = Path(_git(root, *arguments).decode("utf-8").strip())
        _ancestors(directory)
        if arguments[-1] == "--git-common-dir":
            _ancestors(directory / "objects")
    if (
        _git(root, "rev-parse", "--abbrev-ref", "HEAD").decode("utf-8").strip() != task["branch"]
        or _read(root / ".ai/repository-id").decode("utf-8").strip() != task["repository_id"]
    ):
        raise _error(
            "Current repository identity or branch differs from the task", "NODE_BINDING_STALE"
        )
    _git(root, "merge-base", "--is-ancestor", task["base_commit"], task["subject_commit"])
    _git(root, "merge-base", "--is-ancestor", task["subject_commit"], "HEAD")
    bundle = load_policy_bundle(root)
    if not is_node_policy(bundle):
        raise _error("Node materials require the installed Node profile")
    classification = read_task_json(
        root, task_id, "classification.json", contract_name="classification"
    )
    levels = {item.get("verification_level") for item in classification["classifications"]}
    revision = 2 if bundle.policy_version == "3.2.0" else 1
    if "V2" in levels and revision != 2:
        raise _error("Installed Node V2 evidence is unavailable", "VERIFY_NODE_V2_UNSUPPORTED")
    digest, _ = current_classification_input_digest(
        task, parse_decision_units(task), classification, record.events
    )
    spec = specification_digest(_read(root / ".ai/tasks" / task_id / "spec.md").decode("utf-8"))
    if (
        spec != task.get("frozen_spec_sha256")
        or classification.get("policy_sha256") != bundle.sha256
        or classification.get("classification_input_sha256") != digest
    ):
        raise _error("Node preparation facts are stale", "NODE_BINDING_STALE")
    subject = str(task["subject_commit"])
    tree = _git(root, "rev-parse", f"{subject}^{{tree}}").decode().strip()
    return {
        "repository_id": task["repository_id"],
        "task_id": task_id,
        "branch": task["branch"],
        "base_commit": task["base_commit"],
        "subject_commit": subject,
        "subject_tree": tree,
        "spec_sha256": spec,
        "policy_sha256": bundle.sha256,
        "classification_input_sha256": digest,
        "profile": PROFILE if revision == 1 else PROFILE_V2,
    }, bundle


_DISTUTILS_PTH = (
    b"import os; var = 'SETUPTOOLS_USE_DISTUTILS'; "
    b"enabled = os.environ.get(var, 'local') == 'local'; "
    b"enabled and __import__('_distutils_hack').add_shim(); "
)


def _engine_site_facts() -> dict[str, Any]:
    import site

    return {
        "prefix": str(Path(sys.prefix).absolute()),
        "base_prefix": str(Path(sys.base_prefix).absolute()),
        "site_roots": [str(Path(path).absolute()) for path in site.getsitepackages()],
        "active_site_roots": [
            str(Path(path).absolute())
            for path in sys.path
            if path and Path(path).name.casefold() in {"site-packages", "dist-packages"}
        ],
        "enable_user_site": site.ENABLE_USER_SITE,
    }


def _engine_startup(installation: Path, budget: list[int]) -> dict[str, Any]:
    """Accept only the one ordinary-wheel startup hook with a closed payload."""
    files: list[dict[str, Any]] = []
    setuptools = False
    if "sitecustomize" in sys.modules or "usercustomize" in sys.modules:
        raise _error("Custom site startup code is outside the fixed installed engine")
    facts = _engine_site_facts()
    if (
        not isinstance(facts.get("prefix"), str)
        or not Path(facts["prefix"]).is_absolute()
        or facts.get("enable_user_site") is not False
    ):
        raise _error("The installed engine permits unknown user startup inputs")
    prefix = Path(facts["prefix"])
    configuration = prefix / "pyvenv.cfg"
    config: dict[str, Any] | None = None
    try:
        configuration.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise _error("Python environment configuration cannot be inspected") from error
    else:
        _take_budget(budget, _safe_info(configuration).st_size)
        data = _read(configuration)
        try:
            settings = [
                line.split("=", 1) for line in data.decode("utf-8").splitlines() if "=" in line
            ]
        except UnicodeError as error:
            raise _error("Python environment configuration is not UTF-8") from error
        includes = [
            value.strip().lower()
            for key, value in settings
            if key.strip().lower() == "include-system-site-packages"
        ]
        if includes != ["false"]:
            raise _error("Python environment enables additional startup sites")
        config = {
            "path": str(configuration),
            "size": len(data),
            "sha256": _sha(data),
            "identity": _identity(_safe_info(configuration)),
        }
    allowed = {prefix, installation}
    roots = facts.get("site_roots")
    active = facts.get("active_site_roots")
    if (
        not isinstance(roots, list)
        or not isinstance(active, list)
        or not all(isinstance(path, str) and Path(path).is_absolute() for path in (*roots, *active))
        or not roots
        or installation not in {Path(path) for path in roots}
        or any(Path(path) not in allowed for path in (*roots, *active))
        or len({Path(path) for path in roots}) != len(roots)
    ):
        raise _error("The installed engine has an additional third-party startup site")
    root_facts = []
    for root in sorted({Path(path) for path in roots}, key=lambda path: str(path).encode("utf-8")):
        _ancestors(root)
        _take_budget(budget)
        root_facts.append(
            {"path": str(root), "identity": _identity(_safe_info(root, directory=True))}
        )
        for child in root.iterdir():
            if child.name.split(".", 1)[0].casefold() in {"sitecustomize", "usercustomize"}:
                raise _error("Custom site startup code is outside the fixed installed engine")
            if not child.name.casefold().endswith(".pth"):
                continue
            if root != installation or child.name != "distutils-precedence.pth":
                raise _error("Unknown site startup hook is outside the fixed installed engine")
            _take_budget(budget, _safe_info(child).st_size)
            data = _read(child, limit=len(_DISTUTILS_PTH) + 2)
            if data.replace(b"\r\n", b"\n").removesuffix(b"\n") != _DISTUTILS_PTH:
                raise _error("The setuptools startup hook has unknown executable bytes")
            try:
                distribution = importlib.metadata.distribution("setuptools")
            except importlib.metadata.PackageNotFoundError as error:
                raise _error("The installed startup hook has no distribution owner") from error
            record = next(
                (item for item in distribution.files or () if str(item) == child.name), None
            )
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
            if (
                record is None
                or record.hash is None
                or record.hash.mode != "sha256"
                or record.hash.value != digest
                or type(record.size) is not int
                or record.size != len(data)
                or Path(str(distribution.locate_file(""))).resolve() != installation
            ):
                raise _error("The setuptools startup hook is not bound by ordinary-wheel RECORD")
            files.append(
                {
                    "path": str(child),
                    "size": len(data),
                    "sha256": _sha(data),
                    "identity": _identity(_safe_info(child)),
                }
            )
            setuptools = True
        cache = root / "__pycache__"
        if cache.exists():
            _safe_info(cache, directory=True)
            if any(
                child.name.startswith(("sitecustomize.", "usercustomize."))
                for child in cache.iterdir()
            ):
                raise _error("Custom site startup bytecode is outside the fixed installed engine")
    return {
        "files": files,
        "setuptools": setuptools,
        "python_environment": facts,
        "pyvenv_configuration": config,
        "site_roots": root_facts,
    }


def _engine(*, budget: list[int] | None = None) -> dict[str, Any]:
    import aiflow

    distribution = importlib.metadata.distribution("aiflow")
    if aiflow.__file__ is None:
        raise _error("The ordinary installed engine is unavailable")
    origin = Path(aiflow.__file__).resolve()
    installation = Path(str(distribution.locate_file(""))).resolve()
    if budget is None:
        budget = [MAX_ENTRIES, MAX_TOTAL_BYTES]
    if (
        "site-packages" not in origin.parts
        or origin.parent.parent != installation
        or not distribution.files
    ):
        raise _error(
            "Node execution requires an ordinary wheel installation", "NODE_ENGINE_NOT_INSTALLED"
        )
    direct = distribution.read_text("direct_url.json")
    if direct:
        source_metadata = _json_bytes(direct.encode())
        if not isinstance(source_metadata, dict) or not isinstance(
            source_metadata.get("dir_info", {}), dict
        ):
            raise _error("Installed engine origin metadata is invalid")
        if source_metadata.get("dir_info", {}).get("editable"):
            raise _error("Editable engine installations are unsupported")
    startup = _engine_startup(installation, budget)
    startup_paths = {item["path"] for item in startup["files"]}
    rows: list[dict[str, Any]] = []
    distributions_to_bind = (
        "aiflow",
        "PyYAML",
        "jsonschema",
        "attrs",
        "referencing",
        "jsonschema-specifications",
        "rpds-py",
        "typing_extensions",
    ) + (("setuptools",) if startup["setuptools"] else ())
    for name in distributions_to_bind:
        try:
            installed = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            if name == "typing_extensions":
                continue
            raise _error("A required installed engine dependency is missing") from None
        if not installed.files:
            raise _error("Installed engine metadata lacks a file inventory")
        if Path(str(installed.locate_file(""))).resolve() != installation:
            raise _error("Engine runtime dependencies belong to a different installation")
        files = []
        package_roots: set[Path] = set()
        for relative in installed.files:
            path = Path(str(installed.locate_file(relative))).absolute()
            if str(path) not in startup_paths:
                _take_budget(budget, _safe_info(path).st_size)
            if relative.parts and relative.parts[0] not in {".", ".."}:
                anchor = Path(str(installed.locate_file(relative.parts[0]))).absolute()
                if anchor.is_dir():
                    package_roots.add(anchor)
            data = _read(path)
            files.append(
                {
                    "path": str(path),
                    "size": len(data),
                    "sha256": _sha(data),
                    "identity": _identity(_safe_info(path)),
                }
            )
        expected_files = {file["path"] for file in files}
        module_name = {
            "PyYAML": "yaml",
            "rpds-py": "rpds",
            "jsonschema-specifications": "jsonschema_specifications",
            "setuptools": "_distutils_hack",
        }.get(name, name)
        loaded = importlib.import_module(module_name)
        if (
            loaded.__file__ is None
            or str(Path(loaded.__file__).absolute()) not in expected_files
            or loaded.__spec__ is None
            or loaded.__spec__.origin != loaded.__file__
        ):
            raise _error("A loaded runtime dependency is outside its bound installation")
        count = 0
        for anchor in package_roots:
            _ancestors(anchor)
            _take_budget(budget)
            for directory, names, children in os.walk(anchor, followlinks=False):
                for name in tuple(names):
                    child = Path(directory) / name
                    _safe_info(child, directory=True)
                    _take_budget(budget)
                for name in children:
                    count += 1
                    if count > MAX_ENTRIES:
                        raise _error("Engine installed tree exceeds its entry limit")
                    path = Path(directory) / name
                    _safe_info(path)
                    if str(path) not in expected_files:
                        raise _error("Engine installation contains an unrecorded file")
        rows.append(
            {"name": installed.metadata["Name"], "version": installed.version, "files": files}
        )
    if not any(Path(file["path"]) == origin for file in rows[0]["files"]):
        raise _error("Imported engine does not belong to the bound distribution")
    return {
        "python": str(Path(sys.executable).resolve()),
        "distributions": rows,
        "startup": startup,
    }


def _host_tools(*, budget: list[int] | None = None) -> dict[str, Any]:
    if os.name != "nt":
        raise _error("The installed Node profile requires Windows x64", "NODE_HOST_UNSUPPORTED")
    git = shutil.which("git")
    if not git:
        raise _error("Bound Git is unavailable")
    roles = {
        "python": Path(sys.executable).resolve(),
        **_git_role_paths(Path(git).absolute()),
        **_os_tool_paths(),
    }
    rows: dict[str, Any] = {}
    if budget is None:
        budget = [MAX_ENTRIES, MAX_TOTAL_BYTES]
    counted: set[Path] = set()
    for role, path in roles.items():
        os_role = role if role in _os_tool_paths() else None
        if role.endswith("_config"):
            try:
                path.lstat()
            except FileNotFoundError:
                rows[role] = None
                continue
            except OSError as error:
                raise _error("A fixed host OS configuration cannot be inspected") from error
        if path not in counted:
            _take_budget(budget, _safe_info(path, os_role=os_role).st_size)
            counted.add(path)
        data = _read(path, os_role=os_role)
        rows[role] = {
            "path": str(path),
            "size": len(data),
            "sha256": _sha(data),
            "identity": _identity(_safe_info(path, os_role=os_role)),
        }
    return rows


def _source_contract(
    root: Path, source: Mapping[str, Any], *, revision: int = 1
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(revision) is not int or revision not in {1, 2}:
        raise _error("Node source profile revision is unsupported")
    if revision == 2:
        _native_ownership_applicable(root, source)
    files = {row["path"]: row for row in source["files"]}
    configuration = _git(root, "config", "--local", "--list", "--no-includes").decode("utf-8")
    forbidden = (
        "include.",
        "includeif.",
        "filter.",
        "diff.external=",
        "core.hookspath=",
        "core.attributesfile=",
        "core.sshcommand=",
        "remote.origin.promisor=",
        "extensions.partialclone=",
        "core.sparsecheckout=",
    )
    if any(line.casefold().startswith(forbidden) for line in configuration.splitlines()):
        raise _error("Undeclared Git execution inputs are forbidden")
    if any(
        line.casefold().startswith("core.fsmonitor=")
        and line.split("=", 1)[1].lower() not in {"false", "0", "no", "off"}
        for line in configuration.splitlines()
    ):
        raise _error("Git fsmonitor execution is outside the fixed source contract")
    common = Path(
        _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        .decode("utf-8")
        .strip()
    )
    hooks = common / "hooks"
    try:
        hooks.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise _error("Git source hooks cannot be inspected") from error
    else:
        _ancestors(hooks)
        with os.scandir(hooks) as entries:
            for index, entry in enumerate(entries):
                if index >= MAX_ENTRIES or not entry.name.casefold().endswith(".sample"):
                    raise _error("Active or unknown Git source hooks are forbidden")
                _safe_info(Path(entry.path))
    for name, row in files.items():
        if Path(name).name == ".gitattributes":
            attributes = _git(root, "cat-file", "blob", row["blob"]).decode("utf-8")
            if re.search(
                r"(?:^|\s)(?:filter|working-tree-encoding|ident|eol=crlf)(?:=|\s|$)", attributes
            ):
                raise _error("Git attributes introduce an unsupported checkout transform")
    required = (
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "tsconfig.tests.json",
        "vitest.config.ts",
        "agent-commands.json",
    )
    if any(name not in files for name in required) or any(
        Path(name).name.casefold() == ".npmrc" for name in files
    ):
        raise _error("Fixed Node source inputs are missing or contain npm configuration")
    if revision == 2 and files["vitest.config.ts"]["sha256"] != NODE_V2_CONFIG_SHA256:
        raise _error("Revision2 Vitest configuration differs from its reviewed fixed bytes")
    package = _json_bytes(_git(root, "cat-file", "blob", files["package.json"]["blob"]))
    lock = _json_bytes(_git(root, "cat-file", "blob", files["package-lock.json"]["blob"]))
    if not isinstance(package, dict) or not isinstance(lock, dict):
        raise _error("Fixed package and lock inputs must be JSON objects")
    scripts = package.get("scripts")
    if not isinstance(scripts, dict) or not all(
        isinstance(scripts.get(name), str) and scripts[name]
        for name in ("build", "check", "test", "typecheck", "docs:check", "clean")
    ):
        raise _error("Fixed Node scripts are incomplete")
    if scripts["test"] != SEMANTIC_CONTRACT["test_script"]:
        raise _error("The fake suite must use the fixed uncached native-loader script")
    package_config = package.get("config", {})
    if not isinstance(package_config, dict):
        raise _error("Fixed package configuration must be a JSON object")
    if package_config.get("script-shell") or os.environ.get("NODE_OPTIONS"):
        raise _error("Undeclared Node execution configuration is forbidden")
    if lock.get("lockfileVersion") != 3 or type(lock.get("lockfileVersion")) is not int:
        raise _error("A complete npm lockfile v3 is required")
    return package, lock


_CMD_SHIM = """@ECHO off
GOTO start
:find_dp0
SET dp0=%~dp0
EXIT /b
:start
SETLOCAL
CALL :find_dp0

IF EXIST "%dp0%\\node.exe" (
  SET "_prog=%dp0%\\node.exe"
) ELSE (
  SET "_prog=node"
  SET PATHEXT=%PATHEXT:;.JS;=;%
)

endLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & "%_prog%"  "%dp0%\\{target}" %*
"""
_SH_SHIM = r"""#!/bin/sh
basedir=$(dirname "$(echo "$0" | sed -e 's,\\,/,g')")

case `uname` in
    *CYGWIN*|*MINGW*|*MSYS*)
        if command -v cygpath > /dev/null 2>&1; then
            basedir=`cygpath -w "$basedir"`
        fi
    ;;
esac

if [ -x "$basedir/node" ]; then
  exec "$basedir/node"  "$basedir/{target}" "$@"
else
  exec node  "$basedir/{target}" "$@"
fi
""".replace("\nelse\n", "\nelse \n")
_PS_SHIM = """#!/usr/bin/env pwsh
$basedir=Split-Path $MyInvocation.MyCommand.Definition -Parent

$exe=""
if ($PSVersionTable.PSVersion -lt "6.0" -or $IsWindows) {
  # Fix case when both the Windows and Linux builds of Node
  # are installed in the same directory
  $exe=".exe"
}
$ret=0
if (Test-Path "$basedir/node$exe") {
  # Support pipeline input
  if ($MyInvocation.ExpectingInput) {
    $input | & "$basedir/node$exe"  "$basedir/{target}" $args
  } else {
    & "$basedir/node$exe"  "$basedir/{target}" $args
  }
  $ret=$LASTEXITCODE
} else {
  # Support pipeline input
  if ($MyInvocation.ExpectingInput) {
    $input | & "node$exe"  "$basedir/{target}" $args
  } else {
    & "node$exe"  "$basedir/{target}" $args
  }
  $ret=$LASTEXITCODE
}
exit $ret
"""


def _dependency_shims(root: Path, packages: set[str], inventory: Mapping[str, Any]) -> None:
    expected: dict[str, bytes] = {}
    for package in packages:
        manifest = _json(root / package / "package.json")
        bins = manifest.get("bin", {})
        if isinstance(bins, str):
            bins = {str(manifest.get("name", "")).split("/")[-1]: bins}
        if not isinstance(bins, dict):
            raise _error("Dependency bin declarations are invalid")
        for name, relative in bins.items():
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
                raise _error("Dependency bin name is not canonical")
            if not isinstance(relative, str):
                raise _error("Dependency bin target is not a relative path")
            target = root / package / _path(relative.removeprefix("./"))
            first_line = _read(target).split(b"\n", 1)[0].rstrip(b"\r")
            if not re.fullmatch(rb"#!(?:/usr/bin/env node|/usr/bin/node)", first_line):
                raise _error("Dependency bin has an unsupported interpreter")
            parent = (
                package.rsplit("/node_modules/", 1)[0] + "/node_modules"
                if "/node_modules/" in package
                else ""
            )
            bin_root = root / parent / ".bin"
            relative_target = os.path.relpath(target, bin_root).replace("\\", "/")
            templates = {"": _SH_SHIM, ".cmd": _CMD_SHIM, ".ps1": _PS_SHIM}
            for suffix, template in templates.items():
                path = (bin_root / (name + suffix)).relative_to(root).as_posix()
                replacement = (
                    relative_target.replace("/", "\\") if suffix == ".cmd" else relative_target
                )
                data = template.replace("{target}", replacement)
                if suffix == ".cmd":
                    data = data.replace("\n", "\r\n")
                encoded = data.encode("utf-8")
                if path in expected and expected[path] != encoded:
                    raise _error("Dependency bin has ambiguous package ownership")
                expected[path] = encoded
    actual = {
        str(row["path"])
        for row in inventory["entries"]
        if row["kind"] == "file" and ".bin" in Path(str(row["path"])).parts
    }
    if any(
        row["kind"] == "directory"
        and ".bin" in Path(str(row["path"])).parts
        and Path(str(row["path"])).name != ".bin"
        for row in inventory["entries"]
    ):
        raise _error("Dependency shim directory contains an unowned child directory")
    if actual != set(expected):
        raise _error("Dependency shim inventory differs from the locked bin owners")
    for path, expected_bytes in expected.items():
        if _read(root / path) != expected_bytes:
            raise _error("Dependency shim differs from its official fixed package-bin bytes")


def _dependencies(
    root: Path, lock: Mapping[str, Any], *, budget: list[int] | None = None, revision: int = 1
) -> dict[str, Any]:
    if type(revision) is not int or revision not in {1, 2}:
        raise _error("Node dependency profile revision is unsupported")
    inventory = _inventory(root, budget=budget)
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise _error("Lockfile package inventory is missing")
    known = set()
    for path, package in packages.items():
        if not path:
            continue
        _path(path)
        if not path.startswith("node_modules/") or not isinstance(package, dict):
            raise _error("Lockfile package path is invalid")
        for selector, actual in (("os", "win32"), ("cpu", "x64")):
            allowed = package.get(selector, [])
            if not isinstance(allowed, list) or not all(
                isinstance(value, str) for value in allowed
            ):
                raise _error("Lockfile platform selector is invalid")
            positive = [value for value in allowed if not value.startswith("!")]
            if "!" + actual in allowed or (positive and actual not in positive):
                break
        else:
            installed = root / path.removeprefix("node_modules/")
            manifest = _json(installed / "package.json")
            if manifest.get("version") != package.get("version"):
                raise _error("Installed dependency differs from its exact locked version")
            resolved = package.get("resolved", "")
            if (
                not isinstance(resolved, str)
                or not resolved.startswith("https://registry.npmjs.org/")
                or not isinstance(package.get("integrity"), str)
            ):
                raise _error(
                    "Only integrity-bound anonymous public registry dependencies are supported"
                )
            known.add(path.removeprefix("node_modules/"))
            continue
        if (root / path.removeprefix("node_modules/")).exists():
            raise _error("A platform-inapplicable package is unexpectedly installed")
    required_versions = dict(
        (
            ("vitest", VERSIONS["vitest"]),
            ("vite", VERSIONS["vite"]),
        )
    )
    if revision == 1:
        required_versions["@vitest/coverage-v8"] = VERSIONS["vitest"]
    else:
        required_versions.update(ISTANBUL_PACKAGES)
    for name, version in required_versions.items():
        if _json(root / name / "package.json").get("version") != version:
            raise _error("Required coverage dependency has the wrong version")
    if revision == 2:
        for name, digest in ISTANBUL_FILES.items():
            if _sha(_read(root / name)) != digest:
                raise _error("Revision2 coverage producer bytes differ from the reviewed closure")
    for row in inventory["entries"]:
        path = str(row["path"])
        if (
            row["kind"] == "directory"
            and path != ".bin"
            and not path.endswith("/.bin")
            and not any(
                path == name or path.startswith(name + "/") or name.startswith(path + "/")
                for name in known
            )
        ):
            raise _error("Installed dependency directory has no locked package owner")
        if (
            row["kind"] == "file"
            and path not in {".package-lock.json"}
            and not path.startswith(".bin/")
        ):
            if not any(path.startswith(name + "/") for name in known):
                raise _error("Installed dependency file has no locked package owner")
    _dependency_shims(root, known, inventory)
    return inventory


def _node_x64(path: Path) -> None:
    data = _read(path)
    offset = int.from_bytes(data[60:64], "little") if len(data) >= 64 else -1
    if (
        data[:2] != b"MZ"
        or offset < 64
        or offset + 26 > len(data)
        or data[offset : offset + 4] != b"PE\0\0"
        or int.from_bytes(data[offset + 4 : offset + 6], "little") != 0x8664
        or int.from_bytes(data[offset + 24 : offset + 26], "little") != 0x20B
    ):
        raise _error("The fixed Node runtime is not a Windows x64 PE executable")


def prepare_node_materials(root: Path, task_id: str, *, payload_root: Path) -> str:
    """Bind explicit, already prepared ordinary materials without installing anything."""
    root = root.absolute()
    binding, _bundle = _binding(root, task_id)
    payload = payload_root.absolute()
    parent = root / ".ai/tasks" / task_id / "logs/node-payload"
    if payload.parent != parent or not _RUN.fullmatch(payload.name):
        raise _error("Payload must be one explicit preparation directory under this task")
    _ancestors(payload)
    if {child.name for child in payload.iterdir()} != {"node", "dependencies"}:
        raise _error("Payload has unknown or missing roles")
    if {child.name for child in (payload / "dependencies").iterdir()} != {"node_modules"}:
        raise _error("Dependency payload layout is invalid")
    budget = [MAX_ENTRIES, MAX_TOTAL_BYTES]
    source = _source(root, str(binding["subject_commit"]), budget=budget)
    revision = _profile_revision(binding)
    _package, lock = _source_contract(root, source, revision=revision)
    runtime = _inventory(payload / "node", budget=budget)
    _node_x64(payload / "node/node.exe")
    files = {str(row["path"]): row for row in runtime["entries"] if row["kind"] == "file"}
    if any(
        row["path"] not in {"node.exe", "npm.cmd", "node_modules", "node_modules/npm"}
        and not str(row["path"]).startswith("node_modules/npm/")
        for row in runtime["entries"]
    ):
        raise _error("Node runtime contains an unowned neighboring item")
    if set(files) != {"node.exe", "npm.cmd"} | {
        name for name in files if name.startswith("node_modules/npm/")
    }:
        raise _error("Node runtime contains unknown files")
    if _read(payload / "node/npm.cmd") != _read(payload / "node/node_modules/npm/bin/npm.cmd"):
        raise _error("The nested npm shim is not the official package shim")
    npm_package = _json(payload / "node/node_modules/npm/package.json")
    if npm_package.get("name") != "npm" or npm_package.get("version") != VERSIONS["npm"]:
        raise _error("The full npm package has the wrong version")
    dependencies = _dependencies(
        payload / "dependencies/node_modules", lock, budget=budget, revision=revision
    )
    engine, host = _engine(budget=budget), _host_tools(budget=budget)
    preflight_root = payload.parent.parent / ("node-preflight-" + payload.name)
    preflight_root.mkdir()
    for name in ("home", "tmp", "cache"):
        (preflight_root / name).mkdir()
    node = payload / "node/node.exe"
    environment = _environment(
        node, payload / "dependencies", preflight_root, Path(host["git"]["path"])
    )
    preflight = {}
    commands = (
        ("node", (str(node), "--version"), "v" + VERSIONS["node"]),
        (
            "npm",
            (str(node), str(payload / "node/node_modules/npm/bin/npm-cli.js"), "--version"),
            VERSIONS["npm"],
        ),
    )
    for name, argv, expected in commands:
        receipt = _process(
            argv, cwd=payload, environment=environment, timeout=30, output=preflight_root / name
        )
        if (
            not _successful(receipt)
            or _read(preflight_root / name / "stdout.raw").decode().strip() != expected
        ):
            raise _error("Fixed material version preflight failed", "NODE_PREFLIGHT_FAILED")
        preflight[name] = {
            "directory": str(preflight_root / name),
            "receipt": receipt,
            "expected": expected,
        }
    _unchanged(runtime)
    _unchanged(dependencies)
    manifests = {
        "source.json": source,
        "node.json": {"runtime": runtime, "selected": "node.exe"},
        "npm.json": {
            "runtime_sha256": _sha(_canonical(runtime)),
            "entry": "node_modules/npm/bin/npm-cli.js",
            "shim": "npm.cmd",
            "package": npm_package,
        },
        "dependencies.json": dependencies,
        "engine.json": engine,
        "host-tools.json": host,
        "preflight.json": preflight,
    }
    encoded = {name: _canonical(value) for name, value in manifests.items()}
    if (
        any(len(value) > MAX_JSON_BYTES for value in encoded.values())
        or sum(map(len, encoded.values())) > 64 * 1024 * 1024
    ):
        raise _error("Prepared JSON exceeds its limits")
    prepared = {
        "schema_version": "1.0",
        "kind": "aiflow-node-prepared-3.1" if revision == 1 else "aiflow-node-prepared-3.2",
        "binding": binding,
        "payload": {
            "path": str(payload),
            "identity": _identity(_safe_info(payload, directory=True)),
        },
        "manifests": [
            {"name": name, "size": len(encoded[name]), "sha256": _sha(encoded[name])}
            for name in MANIFEST_NAMES
        ],
        "versions": VERSIONS,
        "semantic_contract_sha256": _semantic_digest(binding),
    }
    data = _canonical(prepared)
    if len(data) > MAX_PREPARED_BYTES:
        raise _error("Prepared selector exceeds its byte limit")
    digest = _sha(data)
    destination = root / ".ai/tasks" / task_id / "logs/node-prepared" / digest
    destination.parent.mkdir(exist_ok=True)
    if destination.exists():
        if {child.name for child in destination.iterdir()} != {*MANIFEST_NAMES, "prepared.json"}:
            raise _error("Existing prepared directory has unknown content")
        for name, value in {**encoded, "prepared.json": data}.items():
            if _read(destination / name) != value:
                raise _error("An immutable prepared selection already differs")
    else:
        destination.mkdir()
        for name, value in {**encoded, "prepared.json": data}.items():
            _write_new(destination / name, value)
    return digest


def _load_prepared(
    root: Path, task_id: str, digest: str, binding: Mapping[str, object]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not _SHA.fullmatch(digest):
        raise _error("Node material selector must be a lowercase SHA-256")
    directory = root / ".ai/tasks" / task_id / "logs/node-prepared" / digest
    data = _read(directory / "prepared.json", limit=MAX_PREPARED_BYTES)
    if _sha(data) != digest:
        raise _error("Prepared selector does not match its immutable bytes")
    prepared = _json_bytes(data)
    fields = {
        "schema_version",
        "kind",
        "binding",
        "payload",
        "manifests",
        "versions",
        "semantic_contract_sha256",
    }
    if (
        not isinstance(prepared, dict)
        or set(prepared) != fields
        or prepared["schema_version"] != "1.0"
        or prepared["kind"]
        != (
            "aiflow-node-prepared-3.1"
            if _profile_revision(binding) == 1
            else "aiflow-node-prepared-3.2"
        )
        or _canonical(prepared["binding"]) != _canonical(binding)
        or _canonical(prepared["versions"]) != _canonical(VERSIONS)
        or prepared["semantic_contract_sha256"] != _semantic_digest(binding)
        or _canonical(prepared) != data
    ):
        raise _error("Prepared material binding is stale or invalid", "NODE_BINDING_STALE")
    if {child.name for child in directory.iterdir()} != {*MANIFEST_NAMES, "prepared.json"}:
        raise _error("Prepared directory contains unknown entries")
    refs = prepared["manifests"]
    if not isinstance(refs, list) or len(refs) != len(MANIFEST_NAMES):
        raise _error("Prepared manifest references are incomplete")
    manifests: dict[str, Any] = {}
    total = 0
    for name, ref in zip(MANIFEST_NAMES, refs, strict=True):
        if (
            not isinstance(ref, dict)
            or set(ref) != {"name", "size", "sha256"}
            or ref["name"] != name
            or type(ref["size"]) is not int
            or not 0 <= ref["size"] <= MAX_JSON_BYTES
        ):
            raise _error("Prepared manifest reference is invalid")
        raw = _read(directory / name, limit=MAX_JSON_BYTES)
        total += len(raw)
        if total > 64 * 1024 * 1024 or len(raw) != ref["size"] or _sha(raw) != ref["sha256"]:
            raise _error("Prepared manifest bytes do not match")
        document = _json_bytes(raw)
        if _canonical(document) != raw:
            raise _error("Prepared manifest is not canonical JSON")
        manifests[name] = document
    payload = prepared["payload"]
    expected_parent = root / ".ai/tasks" / task_id / "logs/node-payload"
    if (
        not isinstance(payload, dict)
        or set(payload) != {"path", "identity"}
        or Path(payload["path"]).parent != expected_parent
        or not _RUN.fullmatch(Path(payload["path"]).name)
        or _canonical(_identity(_safe_info(Path(payload["path"]), directory=True)))
        != _canonical(payload["identity"])
    ):
        raise _error("Prepared payload identity changed")
    return prepared, manifests


def _validate_receipt(
    directory: Path,
    expected: Mapping[str, object],
    *,
    argv: Sequence[str] | None = None,
    cwd: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    receipt = _json(directory / "receipt.json")
    _validate_receipt_metadata(receipt, expected, argv=argv, cwd=cwd, environment=environment)
    for stream in ("stdout", "stderr"):
        data = _read(directory / f"{stream}.raw", limit=1024 * 1024)
        if len(data) != receipt[f"{stream}_size"] or _sha(data) != receipt[f"{stream}_sha256"]:
            raise _error("Raw process stream has changed", "NODE_RECEIPT_INVALID")
        from aiflow.redaction import redact_text

        display = redact_text(data.decode("utf-8", errors="replace")).encode()
        if _read(directory / f"{stream}.log", limit=8 * 1024 * 1024) != display:
            raise _error("Process display log differs from the bound raw stream")


def _validate_receipt_metadata(
    receipt: object,
    expected: Mapping[str, object],
    *,
    argv: Sequence[str] | None = None,
    cwd: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    if not isinstance(receipt, dict) or set(receipt) != {
        "returncode",
        "timed_out",
        "stdout_overflow",
        "stderr_overflow",
        "cleanup",
        "execution_error",
        "receipt",
        "stdout_sha256",
        "stderr_sha256",
        "stdout_size",
        "stderr_size",
        "argv",
        "cwd",
        "environment_sha256",
        "timeout_seconds",
        "duration_ms",
    }:
        raise _error("Process receipt has unknown fields", "NODE_RECEIPT_INVALID")
    if _canonical(receipt) != _canonical(expected):
        raise _error("Process receipt differs from its bound original", "NODE_RECEIPT_INVALID")
    integers = ("returncode", "stdout_size", "stderr_size", "timeout_seconds", "duration_ms")
    if any(type(receipt.get(key)) is not int for key in integers):
        raise _error("Process receipt has an invalid integer", "NODE_RECEIPT_INVALID")
    if (
        not 0 <= receipt["stdout_size"] <= 1024 * 1024
        or not 0 <= receipt["stderr_size"] <= 1024 * 1024
        or receipt["duration_ms"] < 0
        or receipt["timeout_seconds"] < 1
    ):
        raise _error("Process receipt integer is out of range", "NODE_RECEIPT_INVALID")
    if any(
        type(receipt.get(key)) is not bool
        for key in ("timed_out", "execution_error", "stdout_overflow", "stderr_overflow")
    ):
        raise _error("Process receipt has an invalid boolean", "NODE_RECEIPT_INVALID")
    if not _successful(receipt):
        raise _error("Process did not finish with verified cleanup", "NODE_PROCESS_FAILED")
    observed = receipt.get("receipt")
    if (
        not isinstance(observed, dict)
        or set(observed)
        != {
            "process_id",
            "creation_time_filetime",
            "created_suspended",
            "assigned",
            "initial_membership",
            "resumed",
            "job_empty",
            "stdout_eof",
            "stderr_eof",
            "terminate_requested",
            "closed",
        }
        or type(observed.get("process_id")) is not int
        or type(observed.get("creation_time_filetime")) is not int
        or observed["process_id"] <= 0
        or observed["creation_time_filetime"] <= 0
        or any(
            observed.get(key) is not True
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
        or type(observed.get("terminate_requested")) is not bool
    ):
        raise _error("Runner ownership or EOF observations are incomplete", "NODE_RECEIPT_INVALID")
    if argv is not None and receipt.get("argv") != list(argv):
        raise _error("Process argv differs from its fixed plan", "NODE_RECEIPT_INVALID")
    if cwd is not None and receipt.get("cwd") != str(cwd):
        raise _error("Process cwd differs from its fixed role", "NODE_RECEIPT_INVALID")
    if environment is not None and receipt.get("environment_sha256") != _sha(
        _canonical(environment)
    ):
        raise _error("Process environment differs from its fixed roles", "NODE_RECEIPT_INVALID")


def validate_receipt_originals(
    expected: Mapping[str, object],
    *,
    receipt: object,
    streams: Mapping[str, bytes],
    logs: Mapping[str, bytes],
    argv: Sequence[str] | None = None,
    cwd: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Validate producing coordinates and exact bytes, without opening old paths."""
    _validate_receipt_metadata(receipt, expected, argv=argv, cwd=cwd, environment=environment)
    if set(streams) != {"stdout", "stderr"} or set(logs) != set(streams):
        raise _error("Process stream roles are incomplete", "NODE_RECEIPT_INVALID")
    bound = cast(dict[str, Any], receipt)
    from aiflow.redaction import redact_text

    for name, data in streams.items():
        if (
            len(data) > 1024 * 1024
            or len(data) != bound[name + "_size"]
            or _sha(data) != bound[name + "_sha256"]
        ):
            raise _error("Raw process stream has changed", "NODE_RECEIPT_INVALID")
        display = redact_text(data.decode("utf-8", errors="replace")).encode()
        if logs[name] != display:
            raise _error("Process display log differs from the bound raw stream")


def _check_materials(root: Path, prepared: Mapping[str, Any], manifests: Mapping[str, Any]) -> None:
    payload = Path(prepared["payload"]["path"])
    if {path.name for path in payload.iterdir()} != {"node", "dependencies"} or {
        path.name for path in (payload / "dependencies").iterdir()
    } != {"node_modules"}:
        raise _error("Prepared payload has unknown or missing role roots")
    node_manifest, npm_manifest = manifests["node.json"], manifests["npm.json"]
    if (
        not isinstance(node_manifest, dict)
        or set(node_manifest) != {"runtime", "selected"}
        or node_manifest["selected"] != "node.exe"
        or Path(node_manifest["runtime"]["root"]) != payload / "node"
        or Path(manifests["dependencies.json"]["root"]) != payload / "dependencies/node_modules"
    ):
        raise _error("Prepared material role is outside its fixed owned payload directory")
    runtime = node_manifest["runtime"]
    _node_x64(payload / "node/node.exe")
    if (
        not isinstance(npm_manifest, dict)
        or set(npm_manifest) != {"runtime_sha256", "entry", "shim", "package"}
        or npm_manifest["runtime_sha256"] != _sha(_canonical(runtime))
        or npm_manifest["entry"] != "node_modules/npm/bin/npm-cli.js"
        or npm_manifest["shim"] != "npm.cmd"
        or _canonical(npm_manifest["package"])
        != _canonical(_json(payload / "node/node_modules/npm/package.json"))
        or npm_manifest["package"].get("name") != "npm"
        or npm_manifest["package"].get("version") != VERSIONS["npm"]
        or _read(payload / "node/npm.cmd") != _read(payload / "node/node_modules/npm/bin/npm.cmd")
    ):
        raise _error("Prepared npm role differs from the complete official nested package")
    for row in runtime["entries"]:
        path = row["path"]
        if path not in {
            "node.exe",
            "npm.cmd",
            "node_modules",
            "node_modules/npm",
        } and not path.startswith("node_modules/npm/"):
            raise _error("Prepared Node runtime contains an unowned neighboring item")
    if not {"node.exe", "npm.cmd", "node_modules/npm/bin/npm-cli.js"}.issubset(
        {row["path"] for row in runtime["entries"] if row["kind"] == "file"}
    ):
        raise _error("Prepared Node runtime is incomplete")
    budget = [MAX_ENTRIES, MAX_TOTAL_BYTES]
    source = _source(root, str(prepared["binding"]["subject_commit"]), budget=budget)
    if _canonical(source) != _canonical(manifests["source.json"]):
        raise _error("Git source material changed", "NODE_MATERIALS_DRIFT")
    revision = _profile_revision(prepared["binding"])
    _package, lock = _source_contract(root, source, revision=revision)
    if _canonical(_inventory(Path(runtime["root"]), budget=budget)) != _canonical(runtime):
        raise _error("Bound Node runtime changed", "NODE_MATERIALS_DRIFT")
    dependencies = manifests["dependencies.json"]
    if _canonical(
        _dependencies(Path(dependencies["root"]), lock, budget=budget, revision=revision)
    ) != _canonical(dependencies):
        raise _error("Bound dependencies changed", "NODE_MATERIALS_DRIFT")
    if _canonical(_engine(budget=budget)) != _canonical(manifests["engine.json"]):
        raise _error("Installed engine changed", "NODE_ENGINE_DRIFT")
    if _canonical(_host_tools(budget=budget)) != _canonical(manifests["host-tools.json"]):
        raise _error("Host tool material changed", "NODE_MATERIALS_DRIFT")
    preflights = manifests["preflight.json"]
    if not isinstance(preflights, dict) or set(preflights) != {"node", "npm"}:
        raise _error("The fixed preflight inventory is incomplete")
    preflight_root = payload.parent.parent / ("node-preflight-" + payload.name)
    node = payload / "node/node.exe"
    environment = _environment(
        node,
        payload / "dependencies",
        preflight_root,
        Path(manifests["host-tools.json"]["git"]["path"]),
    )
    commands = {
        "node": ((str(node), "--version"), "v" + VERSIONS["node"]),
        "npm": (
            (str(node), str(payload / "node/node_modules/npm/bin/npm-cli.js"), "--version"),
            VERSIONS["npm"],
        ),
    }
    for name, (argv, expected) in commands.items():
        preflight = preflights[name]
        directory = preflight_root / name
        if (
            not isinstance(preflight, dict)
            or set(preflight) != {"directory", "receipt", "expected"}
            or preflight["directory"] != str(directory)
            or preflight["expected"] != expected
            or preflight["receipt"].get("timeout_seconds") != 30
            or type(preflight["receipt"].get("timeout_seconds")) is not int
        ):
            raise _error("Preflight binding differs from the fixed material roles")
        _validate_receipt(
            directory, preflight["receipt"], argv=argv, cwd=payload, environment=environment
        )
        if _read(directory / "stdout.raw").decode().strip() != expected:
            raise _error("Bound preflight version changed")


def precheck_node_materials(root: Path, task_id: str, material_sha256: str) -> None:
    """Reject unusable selections before any task recovery or state write."""
    binding, _bundle = _binding(root, task_id)
    prepared, manifests = _load_prepared(root, task_id, material_sha256, binding)
    _check_materials(root, prepared, manifests)


def _copy_tree(source: Path, destination: Path, inventory: Mapping[str, Any]) -> dict[str, Any]:
    destination.mkdir()
    for row in inventory["entries"]:
        target = destination / str(row["path"])
        if row["kind"] == "directory":
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            data = _read(source / str(row["path"]))
            if len(data) != row["size"] or _sha(data) != row["sha256"]:
                raise _error("Material changed while independently copying")
            # Disposable checkout copies become usable only after the complete
            # independent inventory below; durable audit publication uses fsync.
            with target.open("xb") as stream:
                stream.write(data)
    copied = _inventory(destination)
    if _canonical(_content(copied)) != _canonical(_content(inventory)):
        raise _error("Execution copy differs from its material source")
    for original, duplicate in zip(inventory["entries"], copied["entries"], strict=True):
        if (
            original["kind"] == "file"
            and original["identity"]["device"] == duplicate["identity"]["device"]
            and original["identity"]["inode"] == duplicate["identity"]["inode"]
        ):
            raise _error("Execution copy shares a material file identity")
    return copied


def _git_state(root: Path) -> dict[str, object]:
    try:
        fields = (
            _git(root, "rev-parse", "--absolute-git-dir", "HEAD", "HEAD^{tree}")
            .decode("utf-8")
            .splitlines()
        )
    except UnicodeError as error:
        raise _error("Read-only Git facts are malformed", "NODE_GIT_INVALID") from error
    if (
        len(fields) != 3
        or not Path(fields[0]).is_absolute()
        or re.fullmatch(r"[0-9a-f]{40}", fields[1]) is None
        or re.fullmatch(r"[0-9a-f]{40}", fields[2]) is None
    ):
        raise _error("Read-only Git facts are malformed", "NODE_GIT_INVALID")
    git_directory = Path(fields[0])
    _ancestors(git_directory)
    index = git_directory / "index"
    return {
        "head": fields[1],
        "tree": fields[2],
        "index_sha256": _sha(_read(index)),
        "git_directory": str(git_directory),
    }


def _metadata_identity(path: Path) -> dict[str, int]:
    """Read attributes, not unknown file contents; Windows ctime is creation time."""
    info = path.lstat()
    directory = stat.S_ISDIR(info.st_mode)
    before = _identity(_safe_info(path, directory=directory))
    if os.name != "nt":
        return {**before, "change_time_ns": info.st_ctime_ns}
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [
            ("creation", ctypes.c_int64),
            ("access", ctypes.c_int64),
            ("write", ctypes.c_int64),
            ("change", ctypes.c_int64),
            ("attributes", wintypes.DWORD),
        ]

    class Information(ctypes.Structure):
        _fields_ = [
            (name, wintypes.DWORD)
            for name in (
                "attributes",
                "creation_low",
                "creation_high",
                "access_low",
                "access_high",
                "write_low",
                "write_high",
                "volume",
                "size_high",
                "size_low",
                "links",
                "index_high",
                "index_low",
            )
        ]

    kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
    )
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetFileInformationByHandle.argtypes = (wintypes.HANDLE, ctypes.c_void_p)
    kernel.GetFileInformationByHandle.restype = wintypes.BOOL
    kernel.GetFileInformationByHandleEx.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    # READ_ATTRIBUTES; share read/write/delete; OPEN_EXISTING; no reparse following.
    handle = kernel.CreateFileW(str(path), 0x80, 7, None, 3, 0x02200000, None)
    if handle in {None, ctypes.c_void_p(-1).value}:
        raise _error("Original-root attributes cannot be opened", "NODE_ROOT_DRIFT")
    try:
        basic, held = Basic(), Information()
        if not kernel.GetFileInformationByHandle(handle, ctypes.byref(held)) or not (
            kernel.GetFileInformationByHandleEx(
                handle, 0, ctypes.byref(basic), ctypes.sizeof(basic)
            )
        ):
            raise _error("Original-root native attributes are unavailable", "NODE_ROOT_DRIFT")
        held_identity = {
            "device": held.volume,
            "inode": (held.index_high << 32) | held.index_low,
            "nlink": held.links,
            "size": (held.size_high << 32) | held.size_low,
            "attributes": held.attributes,
            "mtime_ns": (((held.write_high << 32) | held.write_low) - 116444736000000000) * 100,
            "ctime_ns": (((held.creation_high << 32) | held.creation_low) - 116444736000000000)
            * 100,
        }
        if any(before[key] != value for key, value in held_identity.items()) or (
            _identity(_safe_info(path, directory=directory)) != before
            or bool(held.attributes & 0x10) != directory
        ):
            raise _error("Original-root object changed while opening", "NODE_ROOT_DRIFT")
        final = Basic()
        if not kernel.GetFileInformationByHandleEx(
            handle, 0, ctypes.byref(final), ctypes.sizeof(final)
        ) or any(
            getattr(final, key) != getattr(basic, key)
            for key in ("creation", "write", "change", "attributes")
        ):
            raise _error("Original-root native attributes changed", "NODE_ROOT_DRIFT")
        return {**before, "change_time_ns": int(basic.change) * 100}
    finally:
        if not kernel.CloseHandle(handle):
            raise _error("Original-root attribute handle did not close", "NODE_ROOT_DRIFT")


def _root_metadata(root: Path, owned_run: Path | None) -> list[dict[str, Any]]:
    directories = [root]
    for arguments in (("--absolute-git-dir",), ("--path-format=absolute", "--git-common-dir")):
        directory = Path(_git(root, "rev-parse", *arguments).decode().strip())
        _ancestors(directory)
        if not any(directory.is_relative_to(parent) for parent in directories):
            directories = [parent for parent in directories if not parent.is_relative_to(directory)]
            directories.append(directory)
    rows: list[dict[str, Any]] = []
    pending = list(directories)
    while pending:
        path = pending.pop()
        if path == owned_run:
            continue
        if len(rows) >= MAX_ENTRIES:
            raise _error("Original-root metadata exceeds its entry limit", "NODE_ROOT_DRIFT")
        identity = _metadata_identity(path)
        rows.append({"path": str(path), "identity": identity})
        if stat.S_ISDIR(identity["mode"]):
            with os.scandir(path) as children:
                pending.extend(Path(child.path) for child in children)
            if _metadata_identity(path) != identity:
                raise _error(
                    "Original-root directory changed during enumeration", "NODE_ROOT_DRIFT"
                )
    rows.sort(key=lambda row: row["path"].encode("utf-8"))
    if len({row["path"].casefold() for row in rows}) != len(rows):
        raise _error("Original-root metadata contains path aliases", "NODE_ROOT_DRIFT")
    return rows


def _git_audit_inputs(root: Path) -> dict[str, Any]:
    git = Path(_git(root, "rev-parse", "--absolute-git-dir").decode().strip())
    common = Path(
        _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()
    )
    ref = _git(root, "symbolic-ref", "--quiet", "HEAD").decode().strip()
    if not ref.startswith("refs/heads/"):
        raise _error("Original-root Git HEAD is not a branch", "NODE_ROOT_DRIFT")
    _path(ref)
    logs = {}
    for path in (git / "logs/HEAD", common / "logs" / ref):
        data = _read(path, limit=MAX_JSON_BYTES) if path.exists() else b""
        logs[str(path)] = {"size": len(data), "sha256": _sha(data)}
    return {"git": str(git), "common": str(common), "ref": ref, "logs": logs}


def _root_snapshot(root: Path, task_id: str, owned_run: Path | None = None) -> dict[str, Any]:
    from aiflow.task_service import read_task_record_strict

    record = read_task_record_strict(root, task_id)
    task = {
        key: value
        for key, value in record.task.items()
        if key not in {"current_state", "updated_at"}
    }
    governance = _governance_snapshot(root, task_id, record.events)
    mutable = set(governance["paths"])
    rows = []
    paths = _git(root, "ls-files", "-z").decode("utf-8").split("\0")
    for path in paths:
        if not path or path in mutable:
            continue
        _path(path)
        data = _read(root / path)
        rows.append(
            {
                "path": path,
                "size": len(data),
                "sha256": _sha(data),
                "identity": _identity(_safe_info(root / path)),
            }
        )
    return {
        "identity": _identity(_safe_info(root, directory=True)),
        "git": _git_state(root),
        "files": rows,
        "task": task,
        "events": list(record.events),
        "governance": governance,
        "metadata": _root_metadata(root, owned_run),
        "git_audit": _git_audit_inputs(root),
    }


def _check_review_resolution(
    previous: Mapping[str, Any], current: Mapping[str, Any], event: Mapping[str, Any]
) -> None:
    finding_id = event["payload"].get("finding_id")
    matches = [item for item in current["findings"] if item["finding_id"] == finding_id]
    if (
        not isinstance(finding_id, str)
        or len(matches) != 1
        or matches[0].get("status") != "resolved"
        or matches[0].get("resolution", {}).get("actor") != event["actor"]
    ):
        raise _error("Review resolution differs from its registered finding")
    if previous["revision"] == current["revision"]:
        expected = previous
    else:
        old = [item for item in previous["findings"] if item["finding_id"] == finding_id]
        if (
            len(old) != 1
            or old[0]["status"] == "resolved"
            or matches[0]["resolution"]["resolved_at"] != current["recorded_at"]
        ):
            raise _error("Review resolution has no matching prior open finding")
        resolved = {**old[0], "status": "resolved", "resolution": matches[0]["resolution"]}
        expected = {
            **previous,
            "revision": previous["revision"] + 1,
            "recorded_at": current["recorded_at"],
            "findings": [
                resolved if item["finding_id"] == finding_id else item
                for item in previous["findings"]
            ],
        }
    if _canonical(expected) != _canonical(current):
        raise _error("Review resolution changed facts outside its existing transaction")


def _governance_snapshot(
    root: Path, task_id: str, events: Sequence[Mapping[str, Any]], *, include_pending: bool = True
) -> dict[str, Any]:
    """Derive exact audit paths from replayed records, never exempt a directory."""
    from aiflow.contracts import require_valid_contract
    from aiflow.review_service import validate_review_record

    prefix = f".ai/tasks/{task_id}/"
    paths = {
        prefix + name
        for name in (
            "task.yaml",
            "events.jsonl",
            "evidence.json",
            "approvals.json",
            "review-package.md",
        )
    }
    immutable = {}
    registered_reviews: dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any]]] = {}
    for event in events:
        if event["event_type"] not in {"review_recorded", "review_finding_resolved"}:
            continue
        payload = event["payload"]
        review_id, revision = payload.get("review_id"), payload.get("revision")
        if (
            not isinstance(review_id, str)
            or not re.fullmatch(r"REV-\d{4,}", review_id)
            or type(revision) is not int
            or revision < 1
        ):
            raise _error("Task review event has an invalid audit reference")
        review_path = prefix + f"reviews/{review_id}-r{revision:04d}.json"
        review = _json(root / review_path)
        require_valid_contract("review-record", review)
        if event["event_type"] == "review_finding_resolved":
            prior = registered_reviews.get((review_id, revision)) or registered_reviews.get(
                (review_id, revision - 1)
            )
            if prior is None:
                raise _error("Review resolution has no registered preceding revision")
            _check_review_resolution(prior[0], review, event)
            digest = prior[1]["context_sha256"]
        else:
            digest = payload.get("context_sha256")
        if not isinstance(digest, str) or not _SHA.fullmatch(digest):
            raise _error("Task review event has an invalid context digest")
        context_path = prefix + f"review-contexts/{digest}.json"
        context = _json(root / context_path)
        require_valid_contract("review-context", context)
        validate_review_record(review, context)
        if (
            review.get("review_id") != review_id
            or type(review.get("revision")) is not int
            or review["revision"] != revision
            or (
                event["event_type"] == "review_recorded"
                and review.get("review_stage") != payload.get("review_stage")
            )
            or review.get("task_id") != task_id
            or review.get("context_sha256") != digest
            or context.get("task_id") != task_id
            or context.get("context_sha256") != digest
            or _sha(
                _canonical(
                    {key: value for key, value in context.items() if key != "context_sha256"}
                )
            )
            != digest
        ):
            raise _error("Task review audit original differs from its event")
        for path in (review_path, context_path):
            paths.add(path)
            immutable[path] = _sha(_read(root / path, limit=MAX_JSON_BYTES))
        registered_reviews[(review_id, revision)] = (review, context)
    approvals = _json(root / prefix / "approvals.json")
    if not isinstance(approvals, list):
        raise _error("Task approval ledger is not an array")
    for approval in approvals:
        require_valid_contract("approval", approval)
    marker_path = root / prefix / "approval_pending.json"
    if include_pending and marker_path.exists():
        from aiflow.approval import _validate_node_code_approval_marker
        from aiflow.task_service import read_task_record_strict

        marker = _json(marker_path)
        pending_event = marker.get("event") if isinstance(marker, dict) else None
        pending_payload = pending_event.get("payload") if isinstance(pending_event, dict) else None
        reference = (
            pending_payload.get("structured_review") if isinstance(pending_payload, dict) else None
        )
        if (
            not isinstance(reference, dict)
            or set(reference) != {"review_id", "revision", "review_stage", "context_sha256"}
            or not isinstance(reference["review_id"], str)
            or type(reference["revision"]) is not int
            or reference["revision"] < 1
            or reference["review_stage"] != "implementation"
        ):
            raise _error(
                "Pending Node approval review role is invalid", "APPROVAL_RECOVERY_INVALID"
            )
        reviewed = registered_reviews.get((reference["review_id"], reference["revision"]))
        if reviewed is None:
            raise _error(
                "Pending Node approval review is not registered", "APPROVAL_RECOVERY_INVALID"
            )
        current = read_task_record_strict(root, task_id)
        classification = _json(root / prefix / "classification.json")
        require_valid_contract("classification", classification)
        evidence = _json(root / prefix / "evidence.json")
        require_valid_contract("evidence", evidence)
        _validate_node_code_approval_marker(
            marker,
            task_id=task_id,
            current_task=current.task,
            current_events=current.events,
            current_approvals=approvals,
            policy_sha256=load_policy_bundle(root).sha256,
            classification_sha256=classification["classification_input_sha256"],
            evidence_sha256=_sha(_canonical(evidence)),
            implementation_review=reviewed[0],
            review_context=reviewed[1],
            review_unit_ids={
                entry["decision_unit_id"]
                for entry in classification["classifications"]
                if entry["route"] == "REVIEW"
            },
            **(
                {"verification_snapshot_sha256": evidence["verification_snapshot_sha256"]}
                if evidence.get("schema_version") == "3.2"
                and evidence.get("verification_level") == "V2"
                else {}
            ),
        )
        paths.add(prefix + "approval_pending.json")
    return {"paths": sorted(paths), "immutable": immutable, "approvals": approvals}


def _git_audit_delta(root: Path, before: Mapping[str, Any], after: Mapping[str, Any]) -> set[Path]:
    old, current = before["git_audit"], after["git_audit"]
    if (
        not isinstance(old, dict)
        or set(old) != {"git", "common", "ref", "logs"}
        or not isinstance(old["logs"], dict)
        or set(old["logs"]) != set(current["logs"])
    ):
        raise _error("Original-root Git audit roles are not exact", "NODE_ROOT_DRIFT")
    for prefix in old["logs"].values():
        if (
            not isinstance(prefix, dict)
            or set(prefix) != {"size", "sha256"}
            or type(prefix["size"]) is not int
            or not 0 <= prefix["size"] <= MAX_JSON_BYTES
            or not isinstance(prefix["sha256"], str)
            or not _SHA.fullmatch(prefix["sha256"])
        ):
            raise _error("Original-root Git reflog prefix is invalid", "NODE_ROOT_DRIFT")
    if any(old[key] != current[key] for key in ("git", "common", "ref")):
        raise _error("Original-root Git administration moved", "NODE_ROOT_DRIFT")
    if _canonical(before["git"]) == _canonical(after["git"]):
        # Normal status queries may replace an identical index or remove its
        # temporary lock. Its bytes are unchanged; keep this exact mutable role.
        return {Path(current["git"]) / "index"}
    git, common = Path(current["git"]), Path(current["common"])
    old_head, new_head = before["git"]["head"], after["git"]["head"]
    allowed = {git / "index"}
    if old_head == new_head:
        return allowed
    ref = current["ref"]
    if (
        _read(git / "HEAD") != f"ref: {ref}\n".encode()
        or _read(common / ref) != (new_head + "\n").encode()
    ):
        raise _error("Advanced Git branch bytes differ from HEAD", "NODE_ROOT_DRIFT")
    allowed.update((git / "HEAD", common / ref))
    commits = set(_git(root, "rev-list", f"{old_head}..{new_head}").decode().splitlines())
    governance_paths = set(after["governance"]["paths"])
    for commit_id in commits:
        # -m compares every merge parent; --root also checks newly joined roots.
        changed = (
            _git(
                root,
                "diff-tree",
                "--root",
                "--no-commit-id",
                "--name-only",
                "-r",
                "-m",
                "-z",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                commit_id,
                "--",
            )
            .decode("utf-8")
            .split("\0")
        )
        if any(path and path not in governance_paths for path in changed):
            raise _error("Git commit history changed a non-governance path", "NODE_ROOT_DRIFT")
    for name, prefix in old["logs"].items():
        path = Path(name)
        data = _read(path, limit=MAX_JSON_BYTES)
        size = prefix["size"]
        if type(size) is not int or size < 0 or _sha(data[:size]) != prefix["sha256"]:
            raise _error("Git reflog history was rewritten", "NODE_ROOT_DRIFT")
        tail = data[size:]
        previous = old_head.encode()
        if not tail or not tail.endswith(b"\n"):
            raise _error("Git reflog lacks the complete advancement", "NODE_ROOT_DRIFT")
        for line in tail.splitlines():
            fields = line.split(b" ", 2)
            if len(fields) != 3 or fields[0] != previous or fields[1].decode() not in commits:
                raise _error("Git reflog is not a continuous commit chain", "NODE_ROOT_DRIFT")
            previous = fields[1]
        if previous != new_head.encode():
            raise _error("Git reflog does not reach current HEAD", "NODE_ROOT_DRIFT")
        allowed.add(path)
    commit = _git(root, "cat-file", "commit", new_head)
    if (
        b"\n\n" not in commit
        or _read(git / "COMMIT_EDITMSG", limit=MAX_JSON_BYTES) != (commit.split(b"\n\n", 1)[1])
    ):
        raise _error("Git commit message differs from current commit", "NODE_ROOT_DRIFT")
    allowed.add(git / "COMMIT_EDITMSG")
    previous_paths = {row["path"] for row in before["metadata"]}
    for object_id in (
        _git(root, "rev-list", "--objects", "--no-object-names", new_head, "^" + old_head)
        .decode()
        .splitlines()
    ):
        if not re.fullmatch(r"[0-9a-f]{40}", object_id):
            raise _error("Git advancement contains an invalid object ID", "NODE_ROOT_DRIFT")
        path = common / "objects" / object_id[:2] / object_id[2:]
        if str(path) not in previous_paths and path.exists():
            _safe_info(path)
            allowed.add(path)
    return allowed


def _check_root_metadata(
    before: Sequence[Mapping[str, Any]], after: Sequence[Mapping[str, Any]], allowed: set[Path]
) -> None:
    ancestors = {parent for path in allowed for parent in path.parents}
    previous_paths = {Path(row["path"]) for row in before}

    def protected(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for row in rows:
            path = Path(row["path"])
            if path in allowed:
                continue
            identity = dict(row["identity"])
            if path in ancestors and stat.S_ISDIR(identity["mode"]):
                # Child membership is still exact below, including ignored paths.
                for key in ("size", "mtime_ns", "ctime_ns", "change_time_ns", "nlink"):
                    identity.pop(key)
                if path not in previous_paths:
                    continue
            result.append({"path": str(path), "identity": identity})
        return result

    if _canonical(protected(before)) != _canonical(protected(after)):
        raise _error("Original-root metadata changed outside owned outputs", "NODE_ROOT_DRIFT")


def _check_root(
    root: Path, task_id: str, before: Mapping[str, Any], owned_run: Path | None = None
) -> None:
    if owned_run is not None:
        prefix = root / ".ai/tasks" / task_id / "logs"
        if owned_run.parent != prefix or not _RUN.fullmatch(owned_run.name):
            raise _error("Original-root owned run is not its fixed role", "NODE_ROOT_DRIFT")
    after = _root_snapshot(root, task_id, owned_run)
    for key in ("identity", "files", "task"):
        if _canonical(after[key]) != _canonical(before[key]):
            raise _error("Protected task worktree input changed", "NODE_ROOT_DRIFT")
    previous_governance, governance = before["governance"], after["governance"]
    for path, digest in previous_governance["immutable"].items():
        if governance["immutable"].get(path) != digest:
            raise _error("An existing task review original changed", "NODE_ROOT_DRIFT")
    old_approvals = previous_governance["approvals"]
    if _canonical(governance["approvals"][: len(old_approvals)]) != _canonical(old_approvals):
        raise _error("Task approval ledger was rewritten", "NODE_ROOT_DRIFT")
    if _canonical(after["git"]) != _canonical(before["git"]):
        old_head, new_head = before["git"]["head"], after["git"]["head"]
        if old_head != new_head:
            _git(root, "merge-base", "--is-ancestor", old_head, new_head)
        for args in (
            ("diff", "--name-only", "-z", old_head, new_head, "--"),
            ("diff", "--name-only", "-z", "--cached", new_head, "--"),
        ):
            changed = _git(root, *args).decode("utf-8").split("\0")
            if any(path and path not in governance["paths"] for path in changed):
                raise _error("Git advancement changed a non-governance path", "NODE_ROOT_DRIFT")
    events = after["events"]
    prefix = before["events"]
    if _canonical(events[: len(prefix)]) != _canonical(prefix):
        raise _error("Task event history was rewritten", "NODE_ROOT_DRIFT")
    for event in events[len(prefix) :]:
        if event.get("event_type") not in {
            "verification_passed",
            "evidence_generated",
            "final_review_required",
            "merge_approved_automatically",
            "code_approved",
            "merge_recorded",
            "review_recorded",
            "approval_recorded",
            "review_finding_resolved",
        }:
            raise _error("Unexpected task governance advancement", "NODE_ROOT_DRIFT")
    allowed = {root / path for path in governance["paths"]}
    allowed.update(_git_audit_delta(root, before, after))
    for path in allowed:
        if path.exists():
            _safe_info(path)
    if owned_run is not None:
        allowed.add(owned_run)
    _check_root_metadata(before["metadata"], after["metadata"], allowed)


def _checkout_files(checkout: Path, source: Mapping[str, Any]) -> dict[str, object]:
    rows = []
    for expected in source["files"]:
        path = checkout / expected["path"]
        data = _read(path)
        if len(data) != expected["size"] or _sha(data) != expected["sha256"]:
            raise _error("Checkout does not contain exact subject source bytes")
        rows.append(
            {
                "path": expected["path"],
                "sha256": _sha(data),
                "size": len(data),
                "identity": _identity(_safe_info(path)),
            }
        )
    git = _git_state(checkout)
    return {
        "root": str(checkout),
        "files": rows,
        "git": git,
        "administration": _inventory(Path(str(git["git_directory"]))),
    }


def _dist_paths(checkout: Path, source: Mapping[str, Any]) -> tuple[str, ...]:
    config = _json(checkout / "tsconfig.json")
    if not isinstance(config, dict) or not isinstance(config.get("compilerOptions", {}), dict):
        raise _error("Bound TypeScript configuration must contain an options object")
    options = config.get("compilerOptions", {})
    source_root = options.get("rootDir")
    if (
        options.get("outDir") != "dist"
        or source_root not in {"src", "src/local"}
        or any(
            options.get(key) is not True for key in ("sourceMap", "declaration", "declarationMap")
        )
        or options.get("noEmit") is True
        or options.get("emitDeclarationOnly") is True
        or "extends" in config
        or "references" in config
    ):
        raise _error("Build output cannot be exactly derived from the bound tsconfig")
    paths: list[str] = []
    for row in source["files"]:
        path = row["path"]
        if path.startswith("src/local/") and path.endswith(".ts") and not path.endswith(".d.ts"):
            stem = path.removeprefix(str(source_root) + "/").removesuffix(".ts")
            paths.extend(
                "dist/" + stem + suffix for suffix in (".js", ".js.map", ".d.ts", ".d.ts.map")
            )
    return _ordered_paths(sorted(paths, key=lambda path: path.encode("utf-8")))


def _dist(checkout: Path, expected: Sequence[str]) -> dict[str, object]:
    inventory = _inventory(checkout / "dist")
    files = {"dist/" + str(row["path"]) for row in inventory["entries"] if row["kind"] == "file"}
    if files != set(expected):
        raise _error(
            "Build output file set differs from the source-derived exact inventory",
            "NODE_OUTPUT_INVALID",
        )
    return inventory


def _changed_lines(
    root: Path, base: str, subject: str
) -> tuple[dict[str, list[int]], tuple[str, ...], bytes]:
    raw = _git(
        root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--unified=0",
        base,
        subject,
        "--",
    )
    return _parse_changed_lines(raw)


def _parse_changed_lines(raw: bytes) -> tuple[dict[str, list[int]], tuple[str, ...], bytes]:
    """Parse the retained fixed Git diff without running a transported Git tree."""
    changed: dict[str, list[int]] = {}
    deleted = []
    current: str | None = None
    old: str | None = None
    for line in raw.decode("utf-8", errors="strict").splitlines():
        if line.startswith("--- "):
            old = line[6:] if line.startswith("--- a/") else None
        elif line.startswith("+++ "):
            if line == "+++ /dev/null":
                if old and old.endswith(".ts") and old.startswith("src/local/"):
                    deleted.append(_path(old))
                elif old and re.search(r"\.(?:[cm]?[jt]sx?|ps1|cs)$", old, re.IGNORECASE):
                    changed.setdefault(_path(old), [])
                current = None
            elif line.startswith("+++ b/"):
                current = _path(line[6:])
                changed.setdefault(current, [])
            else:
                raise _error("Git diff path is not canonical", "NODE_DIFF_INVALID")
        elif line.startswith("@@ ") and current is not None:
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if match is None:
                raise _error("Git diff hunk is invalid", "NODE_DIFF_INVALID")
            start, count = int(match[1]), int(match[2] or "1")
            changed[current].extend(range(start, start + count))
    return (
        {path: sorted(set(lines)) for path, lines in changed.items()},
        tuple(sorted(deleted)),
        raw,
    )


NODE_COVERAGE_HELPER = r"""
import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const input = JSON.parse(await readFile(process.argv[1], 'utf8'));
const require = createRequire(join(input.root, 'package.json'));
const { transformWithOxc, parseAstAsync } = await import(
  pathToFileURL(require.resolve('vite')).href);
const { convert } = await import(pathToFileURL(require.resolve('ast-v8-to-istanbul')).href);
const { default: coverage } = await import(
  pathToFileURL(require.resolve('istanbul-lib-coverage')).href);
if (require('vite/package.json').version !== '8.2.1') throw Error('VITE_VERSION');
const canonical = (filename) => resolve(filename).replaceAll('\\', '/').toLowerCase();
const files = {};
for (const item of input.files) {
  const filename = resolve(input.root, item.path);
  const bytes = await readFile(filename);
  const source = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  if (createHash('sha256').update(bytes).digest('hex') !== item.sha256) throw Error('SOURCE_BYTES');
  if (/(?:istanbul|v8|c8)\s+ignore/i.test(source)) throw Error('COVERAGE_IGNORE');
  const transformed = await transformWithOxc(source, filename,
    { sourcemap: true, target: 'es2024' });
  if (transformed.map == null) throw Error('SOURCE_MAP_MISSING');
  const ast = await parseAstAsync(transformed.code);
  const map = typeof transformed.map === 'string' ? JSON.parse(transformed.map) : transformed.map;
  if (map.version !== 3 || !Array.isArray(map.sources) || typeof map.mappings !== 'string') {
    throw Error('SOURCE_MAP_INVALID');
  }
  const sources = map.sources.map((value) => canonical(value.startsWith('file:')
    ? fileURLToPath(value) : isAbsolute(value) ? value : resolve(dirname(filename), value)));
  if (sources.length !== 1 || sources[0] !== canonical(filename)
      || map.sourcesContent?.length !== 1 || map.sourcesContent[0] !== source) {
    throw Error('SOURCE_IDENTITY');
  }
  const result = await convert({ code: transformed.code, ast, sourceMap: map,
    coverage: { url: pathToFileURL(filename).href, functions: [] } });
  const keys = Object.keys(result);
  if (keys.length !== 1 || canonical(keys[0]) !== canonical(filename)) throw Error('MAP_INVENTORY');
  const entry = result[keys[0]];
  if (Object.values(entry.s).some((value) => value !== 0)) throw Error('MAP_NOT_ZERO');
  const lines = Object.keys(coverage.createFileCoverage(entry).getLineCoverage())
    .map(Number).sort((a, b) => a - b);
  if (lines.length && !map.mappings.length) throw Error('EXECUTABLE_SOURCE_UNMAPPED');
  files[item.path] = { sha256: item.sha256, lines };
}
const output = { schema_version: '1.0',
  method: 'vite-8.2.1-oxc-es2024-ast-v8-to-istanbul-zero-hit-v1', files };
await writeFile(process.argv[2], JSON.stringify(output), { flag: 'wx' });
""".strip()


NODE_ISTANBUL_HELPER = r"""

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { resolve, relative, join, dirname, isAbsolute } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
const manifest = JSON.parse(await readFile(process.argv[1], 'utf8'));
if (Object.keys(manifest).sort().join(',') !== 'files,root' ||
  typeof manifest.root !== 'string' ||
  !isAbsolute(manifest.root) ||
  !Array.isArray(manifest.files) ||
  !manifest.files.length ||
  manifest.files.length > 20000)
  throw Error('SOURCE_MANIFEST');
const outputFile = resolve(process.argv[2]),
  outputRoot = join(dirname(outputFile), 'domain-materials'),
  root = resolve(manifest.root).replaceAll('\\', '/');
await mkdir(outputRoot);
const require = createRequire(join(root, 'package.json')),
  {
    parse
  } = require('@babel/parser');
const providerModule = await import(
  pathToFileURL(require.resolve('@vitest/coverage-istanbul')).href);
const {
  transformWithOxc
} = await import(
  pathToFileURL(require.resolve('vite')).href);
const versions = {
  '@vitest/coverage-istanbul': '4.1.10',
  'vitest': '4.1.10',
  'vite': '8.2.1',
  '@babel/core': '7.29.7',
  '@babel/parser': '7.29.12',
  '@jridgewell/trace-mapping': '0.3.31',
  'istanbul-lib-coverage': '3.2.2',
  '@istanbuljs/schema': '0.1.6'
};
for (const [name, version] of Object.entries(versions)) {
  const packageFile = join(root, 'node_modules', name, 'package.json');
  if (JSON.parse(await readFile(packageFile,
     'utf8')).version !== version)
    throw Error('PRODUCER_VERSION');
  const resolved = resolve(require.resolve(name)).replaceAll('\\', '/').toLowerCase();
  if (!resolved.startsWith(resolve(root,
     'node_modules',
     name).replaceAll('\\',
     '/').toLowerCase() + '/'))
    throw Error('PRODUCER_ROLE');
}
const provider = await providerModule.default.getProvider();
provider.initialize({
  version: '4.1.10',
  config: {
    root,
    project: []
  },
  _coverageOptions: {
    include: ['src/local/**/*.ts'],
    exclude: [],
    reportsDirectory: join(outputRoot, 'materials'),
    cleanOnRerun: true
  },
  getProjectByName: () => ({
    config: {
      root
    }
  }),
  logger: {
    warn: message => {
      throw Error(message);
    },
    log: () => {}
  }
});
const expectedOptions = {
  produceSourceMap: true,
  autoWrap: false,
  esModules: true,
  compact: false,
  coverageVariable: '__VITEST_COVERAGE__',
  coverageGlobalScope: 'globalThis',
  coverageGlobalScopeFunc: false,
  ignoreClassMethods: [],
  generatorOpts: {
    importAttributesKeyword: 'with'
  },
  ignoreLines: true
};
for (const [key,
   value] of Object.entries(expectedOptions))
  if (JSON.stringify(provider.instrumenter.opts[key]) !== JSON.stringify(value))
  throw Error('INSTRUMENTER_OPTIONS');
const parserPlugins = ['asyncGenerators',
   'bigInt',
   'classProperties',
   'classPrivateProperties',
   'classPrivateMethods',
   'dynamicImport',
   'importMeta',
   'numericSeparator',
   'objectRestSpread',
   'optionalCatchBinding',
   'topLevelAwait',
   ['importAttributes',
   {
  deprecatedAssertSyntax: true
}]];
if (JSON.stringify(provider.instrumenter.opts.parserPlugins) !== JSON.stringify(parserPlugins))
  throw Error('INSTRUMENTER_PARSER');
await mkdir(provider.coverageFilesDirectory, {
  recursive: true
});
const initial = provider.createCoverageMap(),
  sources = new Map(),
  originals = new Map();
const walk = (node, visit) => {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) {
    for (const item of node) walk(item, visit);
    return;
  }
  if (typeof node.type === 'string') visit(node);
  for (const [key,
     value] of Object.entries(node))
    if (!['loc',
     'comments',
     'leadingComments',
     'trailingComments',
     'innerComments',
     'extra',
     'tokens'].includes(key)) walk(value,
     visit);
};
const keyFor = point => `${point.line}:${point.column}`;
let previousPath = null;
const foldedPaths = new Set();
for (const item of manifest.files) {
  if (Object.keys(item).sort().join(',') !== 'path,sha256' ||
    typeof item.path !== 'string' ||
    !item.path.startsWith('src/local/') ||
    !item.path.endsWith('.ts') ||
    item.path.split('/').some(x => !x ||
    x === '.' ||
    x === '..') ||
    /[\\:\x00-\x1f]/.test(item.path) ||
    typeof item.sha256 !== 'string' ||
    !/^[0-9a-f]{64}$/.test(item.sha256))
    throw Error('SOURCE_ENTRY');
  if (previousPath !== null &&
    Buffer.compare(Buffer.from(previousPath),
     Buffer.from(item.path)) >= 0 ||
    foldedPaths.has(item.path.toLowerCase()))
    throw Error('SOURCE_ORDER');
  previousPath = item.path;
  foldedPaths.add(item.path.toLowerCase());
  const filename = resolve(root, item.path).replaceAll('\\', '/'),
    bytes = await readFile(filename),
    text = new TextDecoder('utf8', {
      fatal: true
    }).decode(bytes);
  if (createHash('sha256').update(bytes).digest('hex') !== item.sha256) throw Error('SOURCE_BYTES');
  if (/(?:istanbul|v8|c8)\s+ignore/i.test(text)) throw Error('COVERAGE_IGNORE');
  const ast = parse(text, {
      sourceType: 'module',
      plugins: ['typescript', 'importAttributes'],
      tokens: true
    }),
    noElse = new Map();
  walk(ast.program, node => {
    if (node.type === 'IfStatement' && node.alternate == null) {
      const key = keyFor(node.loc.start);
      if (noElse.has(key)) throw Error('AMBIGUOUS_IF');
      noElse.set(key, node);
    }
  });
  sources.set(item.path, {
    text,
    ast,
    noElse,
    sha256: item.sha256
  });
  const transformed = await transformWithOxc(text, filename, {
    sourcemap: true,
    target: 'es2024'
  });
  const map = typeof transformed.map === 'string' ? JSON.parse(transformed.map) : transformed.map;
  if (!map ||
    map.version !== 3 ||
    typeof map.mappings !== 'string' ||
    !Array.isArray(map.sources) ||
    map.sources.length !== 1 ||
    !Array.isArray(map.sourcesContent) ||
    map.sourcesContent.length !== 1 ||
    map.sourcesContent[0] !== text)
    throw Error('SOURCE_MAP');
  const mapped = map.sources[0];
  if (typeof mapped !== 'string') throw Error('SOURCE_MAP_IDENTITY');
  const mappedPath = resolve(mapped.startsWith('file:') ?
    fileURLToPath(mapped) :
    isAbsolute(mapped) ?
    mapped :
    resolve(dirname(filename),
     mapped)).replaceAll('\\',
     '/');
  if (mappedPath.toLowerCase() !== filename.toLowerCase()) throw Error('SOURCE_MAP_IDENTITY');
  const result = provider.onFileTransform(transformed.code,
     filename + '?vitest-uncovered-coverage=true',
     {
    getCombinedSourcemap: () => structuredClone(map)
  });
  if (!result) throw Error('SOURCE_NOT_INSTRUMENTED');
  const zero = provider.instrumenter.lastFileCoverage();
  for (const role of ['s',
     'f',
     'b'])
    for (const count of Object.values(zero[role]))
    if ((Array.isArray(count) ?
    count :
    [count]).some(n => n !== 0))
    throw Error('DOMAIN_NOT_ZERO');
  initial.addFileCoverage(zero);
  originals.set(item.path, structuredClone(zero));
}
await provider.onAfterSuiteRun({
  coverage: initial.toJSON(),
  environment: 'node',
  projectName: 'zero-domain',
  testFiles: []
});
const remapped = await provider.generateCoverage({
  allTestsRun: false
});
const files = {},
  stats = {
    kind: 'independent-istanbul-zero-hit-domain-v1',
    sources: 0,
    mapped_sources: 0,
    empty_sources: [],
    implicit_else: 0,
    executable: 0,
    zero_only: true,
    runtime_report_input: false
  };
for (const filename of remapped.files()) {
  const path = relative(root, filename).replaceAll('\\', '/'),
    source = sources.get(path);
  if (!source) throw Error('EXTRA_SOURCE');
  const data = JSON.parse(JSON.stringify(remapped.fileCoverageFor(filename).toJSON())),
    lineMap = remapped.fileCoverageFor(filename).getLineCoverage();
  if (Object.values(lineMap).some(value => value !== 0)) throw Error('REMAPPED_NOT_ZERO');
  const entry = {
    sha256: source.sha256,
    lines: Object.keys(lineMap).map(Number).sort((a, b) => a - b),
    implicit_else: []
  };
  for (const branch of Object.values(data.branchMap))
    for (let index = 0;
     index < branch.locations.length;
     index++) {
    const location = branch.locations[index];
    if (Object.keys(location.start).length || Object.keys(location.end).length) continue;
    const node = source.noElse.get(keyFor(branch.loc.start));
    if (branch.type !== 'if' ||
      index !== 1 ||
      branch.locations.length !== 2 ||
      !node ||
      node.loc.end.line !== branch.loc.end.line)
      throw Error('IMPLICIT_ELSE_NOT_IN_TS_AST');
    if (branch.loc.end.column === null) {
      const lineEndIndex = source.text.indexOf('\n', node.end),
        lineEnd = lineEndIndex < 0 ? source.text.length : lineEndIndex;
      if (source.ast.tokens.some(token => token.start >= node.end &&
        token.start < lineEnd &&
        typeof token.type !== 'string' &&
        token.type.label !== 'eof'))
        throw Error('NULL_END_INCLUDES_CODE');
    } else if (branch.loc.end.column !== node.loc.end.column &&
      !(branch.loc.end.column === node.loc.end.column + 1 &&
      source.text.split(/\r?\n/u)[node.loc.end.line - 1].slice(node.loc.end.column,
       branch.loc.end.column) === ' ')) {
      const terminalSemicolon = branch.loc.end.column === node.loc.end.column - 1 &&
        source.text.split(/\r?\n/u)[node.loc.end.line - 1].slice(branch.loc.end.column,
          node.loc.end.column) === ';' &&
        source.ast.tokens.some(token => typeof token.type !== 'string' &&
          token.type.label === ';' && token.start === node.end - 1 && token.end === node.end);
      if (!terminalSemicolon) throw Error('FINITE_END_NOT_PROVEN');
    }
    entry.implicit_else.push({
      parent: branch.loc,
      locations: branch.locations,
      type: branch.type,
      ast_start: {
        line: node.loc.start.line,
        column: node.loc.start.column
      },
      ast_end: {
        line: node.loc.end.line,
        column: node.loc.end.column
      }
    });
    stats.implicit_else++;
  }
  files[path] = entry;
  stats.mapped_sources++;
  stats.executable += entry.lines.length;
}
for (const item of manifest.files) if (!files[item.path]) {
  const source = sources.get(item.path),
    zero = originals.get(item.path),
    map = zero.inputSourceMap;
  const reexports = source.ast.program.body.length > 0 &&
    !source.ast.program.directives.length &&
    source.ast.program.body.every(node => node.type === 'ExportNamedDeclaration' &&
    ['value',
     'type'].includes(node.exportKind) &&
    node.source?.type === 'StringLiteral' &&
    node.declaration == null &&
    node.specifiers.length > 0 &&
    node.specifiers.every(s => s.type === 'ExportSpecifier' &&
    s.local.type === 'Identifier' &&
    s.exported.type === 'Identifier'));
  if (!reexports ||
    !['s',
     'f',
     'b',
     'statementMap',
     'fnMap',
     'branchMap'].every(role => !Object.keys(zero[role]).length) ||
    map?.sources?.length !== 1 ||
    map?.sourcesContent?.length !== 1 ||
    map.sourcesContent[0] !== source.text)
    throw Error('EMPTY_DOMAIN_NOT_PROVEN');
  files[item.path] = {
    sha256: source.sha256,
    lines: [],
    implicit_else: [],
    empty_domain: {
      kind: 'named_source_reexports_only_v1',
      statements: source.ast.program.body.length
    }
  };
  stats.empty_sources.push(item.path);
}
stats.sources = Object.keys(files).length;
stats.original_ts_no_else = [...sources.values()].reduce((sum,
   source) => sum + source.noElse.size,
   0);
if (stats.implicit_else !== stats.original_ts_no_else)
  throw Error("INCOMPLETE_IMPLICIT_ELSE_CATALOG");
if (stats.sources !== manifest.files.length) throw Error('SOURCE_SET');
await writeFile(outputFile, JSON.stringify({
  kind: stats.kind,
  producer: '@vitest/coverage-istanbul@4.1.10',
  transform: 'vite@8.2.1-oxc-es2024',
  typescript_parser: '@babel/parser@7.29.12',
  files
}), {
  flag: 'wx'
});
await writeFile(join(outputRoot, 'summary.json'), JSON.stringify(stats, null, 2) + '\n', {
  flag: 'wx'
});
console.log(JSON.stringify(stats));
""".strip()


def _coverage(
    checkout: Path,
    node_dir: Path,
    source: Mapping[str, Any],
    base: str,
    subject: str,
    original: Path,
    *,
    revision: int = 1,
) -> dict[str, object]:
    started = monotonic_ns()
    directory = node_dir / "coverage"
    if not directory.is_dir():
        raise _error("Coverage reports are missing", "NODE_COVERAGE_INVALID")
    if {path.name for path in directory.iterdir()} != {
        "coverage-final.json",
        "coverage-summary.json",
    }:
        raise _error("Coverage report directory has unknown entries", "NODE_COVERAGE_INVALID")
    if type(revision) is not int or revision not in {1, 2}:
        raise _error("Node coverage profile revision is unsupported")
    limit = 32 * 1024 * 1024 if revision == 1 else MAX_JSON_BYTES
    raw = _read(directory / "coverage-final.json", limit=limit)
    summary_raw = _read(directory / "coverage-summary.json", limit=limit)
    if len(raw) + len(summary_raw) > 64 * 1024 * 1024:
        raise _error("Coverage reports exceed their aggregate byte limit")
    expected = _json(node_dir / "expected-map.json", limit=limit)
    sources = {
        row["path"]: _read(checkout / row["path"])
        for row in source["files"]
        if row["path"].startswith("src/local/") and row["path"].endswith(".ts")
    }
    changed, deleted, diff = _changed_lines(original, base, subject)
    diff_path = node_dir / "source.diff"
    if diff_path.exists():
        if _read(diff_path) != diff:
            raise _error("Bound coverage diff changed")
    else:
        # Only the execution caller is allowed to publish this original.
        raise _error("Bound coverage diff is missing")
    result = _coverage_from_originals(
        checkout, sources, raw, summary_raw, expected, diff, revision=revision
    )
    if monotonic_ns() - started > 30_000_000_000:
        raise _error("TypeScript coverage calculation timed out", "NODE_COVERAGE_TIMEOUT")
    return result


def _coverage_from_originals(
    checkout: Path,
    sources: Mapping[str, bytes],
    raw: bytes,
    summary_raw: bytes,
    expected: object,
    diff: bytes,
    *,
    revision: int = 2,
) -> dict[str, object]:
    """Replay coverage/catalog arithmetic on retained bytes and lexical coordinates."""
    started = monotonic_ns()
    if type(revision) is not int or revision not in {1, 2}:
        raise _error("Node coverage profile revision is unsupported")
    limit = 32 * 1024 * 1024 if revision == 1 else MAX_JSON_BYTES
    if (
        len(raw) > limit
        or len(summary_raw) > limit
        or len(raw) + len(summary_raw) > 64 * 1024 * 1024
    ):
        raise _error("Coverage reports exceed their aggregate byte limit")
    reports, summary = _json_bytes(raw), _json_bytes(summary_raw)
    if (
        not isinstance(expected, dict)
        or (
            revision == 1
            and (
                set(expected) != {"schema_version", "method", "files"}
                or expected.get("schema_version") != "1.0"
                or expected.get("method") != COVERAGE_METHOD
            )
        )
        or not isinstance(expected.get("files"), dict)
    ):
        raise _error("The independent executable map is invalid", "NODE_COVERAGE_INVALID")
    if set(expected["files"]) != set(sources):
        raise _error("The executable map source set is incomplete", "NODE_COVERAGE_INVALID")
    lines = {}
    for path, value in expected["files"].items():
        if (
            not isinstance(value, dict)
            or (revision == 1 and set(value) != {"sha256", "lines"})
            or value.get("sha256") != _sha(sources[path])
        ):
            raise _error("The executable map source bytes differ", "NODE_COVERAGE_INVALID")
        if revision == 1:
            lines[path] = value["lines"]
    if not isinstance(reports, dict) or not isinstance(summary, dict):
        raise _error("Coverage report is not an object", "NODE_COVERAGE_INVALID")
    normalized = {}
    summary_normalized = {}
    for original_path, value in reports.items():
        path = Path(original_path)
        if not path.is_absolute() or not path.is_relative_to(checkout):
            raise _error("Coverage report has an external source path", "NODE_COVERAGE_INVALID")
        relative = _path(path.relative_to(checkout).as_posix())
        if (
            relative in normalized
            or not isinstance(value, dict)
            or value.get("path") != original_path
        ):
            raise _error("Coverage report has duplicate or mismatched source identity")
        normalized[relative] = {**value, "path": relative}
        if original_path not in summary:
            raise _error("Coverage summary omits a source")
        summary_normalized[relative] = summary[original_path]
    if set(summary) != set(reports) | {"total"}:
        raise _error("Coverage summary inventory differs from the complete report")
    changed, deleted, _raw = _parse_changed_lines(diff)
    if revision == 1:
        result = validate_node_line_coverage(
            normalized,
            tracked_sources=sources,
            changed_lines=changed,
            deleted_sources=deleted,
            expected_executable_lines=lines,
        )
    else:
        result = validate_node_istanbul_line_coverage(
            normalized,
            tracked_sources=sources,
            changed_lines=changed,
            deleted_sources=deleted,
            catalog=expected,
        )
    if cast(dict[str, Any], result["total"])["executable"] == 0:
        raise _error("A real application cannot have an empty coverage denominator")
    for path, value in normalized.items():
        if monotonic_ns() - started > 30_000_000_000:
            raise _error("TypeScript coverage calculation timed out", "NODE_COVERAGE_TIMEOUT")
        hits: dict[int, int] = {}
        for identity, statement in value["statementMap"].items():
            line = statement["start"]["line"]
            hits[line] = max(hits.get(line, 0), value["s"][identity])
        _summary_lines(summary_normalized[path], len(hits), sum(hit > 0 for hit in hits.values()))
    total = cast(dict[str, Any], result["total"])
    _summary_lines(summary["total"], total["executable"], total["covered"])
    if monotonic_ns() - started > 30_000_000_000:
        raise _error("TypeScript coverage calculation timed out", "NODE_COVERAGE_TIMEOUT")
    return result


def _summary_lines(value: object, executable: int, covered: int) -> None:
    if not isinstance(value, dict) or not isinstance(value.get("lines"), dict):
        raise _error("Coverage line summary is missing")
    lines = value["lines"]
    if (
        type(lines.get("total")) is not int
        or type(lines.get("covered")) is not int
        or type(lines.get("skipped")) is not int
        or lines["total"] != executable
        or lines["covered"] != covered
        or lines["skipped"] != 0
    ):
        raise _error("Coverage summary disagrees with recomputed line counts")


def _coverage_originals(node_dir: Path, result: Mapping[str, object]) -> dict[str, object]:
    names = (
        "coverage/coverage-final.json",
        "coverage/coverage-summary.json",
        "expected-map.json",
        "source.diff",
        "source-manifest.json",
    )
    originals = []
    for name in names:
        data = _read(node_dir / name, limit=32 * 1024 * 1024)
        originals.append({"ref": name, "size": len(data), "sha256": _sha(data)})
    return {"originals": originals, "result": dict(result)}


def _role_template(argv: Sequence[str], context: VerificationContext) -> list[str]:
    bindings = context.node_bindings
    if bindings is None:
        raise _error("The execution plan is missing Node role bindings")
    roles = {
        context.python: "P",
        bindings.node_executable: "N",
        bindings.npm_cli: "M",
        bindings.git_executable: "G",
        str(bindings.user_config): "U",
        str(bindings.global_config): "C",
        str(bindings.coverage_directory): "R",
        context.task_id: "T",
        context.base_commit: "B",
        context.subject_commit: "S",
        str(bindings.source_manifest_file): "{node_source_manifest}",
        str(bindings.expected_map_file): "{node_expected_map}",
        NODE_COVERAGE_HELPER: "{node_map_script}",
        NODE_ISTANBUL_HELPER: "{node_map_script}",
        "--config="
        + str(bindings.execution_root / "vitest.config.ts"): "--config={node_source_config}",
        "--outputFile.json="
        + str(
            bindings.coverage_directory.parent / "vitest.json"
        ): "--outputFile.json={node_product_report}",
        "--coverage.reportsDirectory="
        + str(bindings.coverage_directory): "--coverage.reportsDirectory=R",
    }
    return [roles.get(value, value) for value in argv]


def node_execution_contract(plan: Any, context: VerificationContext) -> dict[str, object]:
    """Return the fixed role-only execution contract used by public evidence."""
    return {
        "level": plan.level,
        "checks": [
            {
                "check_id": check.check_id,
                "required": check.required,
                "timeout_seconds": check.timeout_seconds,
                "threshold": check.threshold,
            }
            for check in plan.checks
        ],
        "executions": [
            {
                "execution_id": execution.execution_id,
                "argv_template": _role_template(execution.argv, context),
                "cwd_role": "original" if execution.cwd == context.repository_root else "isolated",
                "timeout_seconds": execution.timeout_seconds,
                "check_ids": list(execution.check_ids),
            }
            for execution in plan.executions
        ],
    }


def _public_execution(
    execution: Any, receipt: Mapping[str, Any], context: VerificationContext
) -> dict[str, object]:
    prefix = f"logs/{context.run_id}/node/raw/{execution.execution_id}"
    return {
        "execution_id": execution.execution_id,
        "argv_template": _role_template(execution.argv, context),
        "cwd_role": "original" if execution.cwd == context.repository_root else "isolated",
        "timeout_seconds": execution.timeout_seconds,
        "returncode": receipt["returncode"],
        "timed_out": receipt["timed_out"],
        "duration_ms": receipt["duration_ms"],
        "stdout": {
            "bytes": receipt["stdout_size"],
            "sha256": receipt["stdout_sha256"],
            "raw_ref": prefix + "/stdout.raw",
            "log_ref": prefix + "/stdout.log",
        },
        "stderr": {
            "bytes": receipt["stderr_size"],
            "sha256": receipt["stderr_sha256"],
            "raw_ref": prefix + "/stderr.raw",
            "log_ref": prefix + "/stderr.log",
        },
        "stdout_overflow": receipt["stdout_overflow"],
        "stderr_overflow": receipt["stderr_overflow"],
        "cleanup": receipt["cleanup"],
        "execution_error": receipt["execution_error"],
    }


def _checks(
    plan: Any,
    context: VerificationContext,
    executions: Sequence[Mapping[str, Any]],
    coverage: object,
    failure: str | None,
    *,
    products: Mapping[str, Any] | None = None,
    installed: InstalledMutationFacts | Mapping[str, Any] | None = None,
) -> list[dict[str, object]]:
    public = {str(item["execution_id"]): item for item in executions}
    checks = []
    for check in plan.checks:
        fixed = [item for item in plan.executions if check.check_id in item.check_ids]
        actual = [public[item.execution_id] for item in fixed if item.execution_id in public]
        if check.check_id in {"acceptance", "integration"}:
            status = (
                "passed"
                if products is not None
                and failure is None
                and len(fixed) == 1
                and len(actual) == 1
                and all(_successful(item) for item in actual)
                else "unverified"
            )
        elif check.check_id in {"targeted_mutation", "independent_verifier"}:
            mutation_passed = (
                installed.get("passed") is True
                if isinstance(installed, Mapping)
                else installed is not None and installed.passed
            )
            status = "passed" if mutation_passed else "unverified"
        elif not check.argv:
            status = "passed" if coverage is not None and failure is None else "unverified"
        elif len(actual) != len(fixed):
            status = "unverified"
        else:
            status = "passed" if all(_successful(item) for item in actual) else "failed"
        if check.check_id == "ts_coverage" and coverage is None:
            status = "failed" if len(actual) == len(fixed) else "unverified"
        checks.append(
            {
                "check_id": check.check_id,
                "required": True,
                "status": status,
                "executions": actual,
            }
        )
    return checks


def _installed_for_node(
    root: Path,
    task_id: str,
    reference: InstalledMutationReference,
    *,
    verifier_actor: str | None = None,
    binding: Mapping[str, Any] | None = None,
    manifests: Mapping[str, Any] | None = None,
) -> tuple[InstalledMutationCurrent, InstalledMutationFacts]:
    from aiflow import installed_mutations as installed

    document = installed._run_original(root, reference)
    actor = document["inputs"].get("verifier_actor")
    if not isinstance(actor, str) or (verifier_actor is not None and actor != verifier_actor):
        raise _error("Node verifier differs from the selected installed mutation run")
    installed._validate_run_children(root, reference)
    current = installed.collect_installed_mutation_current(root, reference, verifier_actor=actor)
    facts = installed.replay_installed_mutations(root, reference, current=current)
    if current.inputs.task_id != task_id:
        raise _error(
            "Selected installed mutations belong to another task", "NODE_MUTATIONS_INVALID"
        )
    if binding is not None:
        for key in (
            "repository_id",
            "task_id",
            "branch",
            "base_commit",
            "subject_commit",
            "subject_tree",
            "spec_sha256",
            "policy_sha256",
            "classification_input_sha256",
        ):
            if getattr(current.inputs, key) != binding[key]:
                raise _error("Node and installed mutation bindings differ", "NODE_BINDING_STALE")
    if manifests is not None:
        material = _json_bytes(current.inputs.materials)
        if _canonical(material["engine"]["installed"]) != _canonical(
            manifests["engine.json"]
        ) or _canonical(material["host_tools"]) != _canonical(manifests["host-tools.json"]):
            raise _error("Node and installed mutations used different engine or host bytes")
    return current, facts


def claim_node_v2_run(
    root: Path,
    task_id: str,
    *,
    reference: InstalledMutationReference,
    verifier_actor: str,
) -> dict[str, int]:
    """Exclusively reserve the one Node role before verification state changes."""
    from aiflow.task_service import read_task_record_strict

    root = root.absolute()
    binding, bundle = _binding(root, task_id)
    record = read_task_record_strict(root, task_id)
    if bundle.policy_version != "3.2.0" or record.task["current_state"] != "IMPLEMENTING":
        raise _error("Only an IMPLEMENTING revision2 V2 task may claim an IMUT Node role")
    _current, mutation_facts = _installed_for_node(
        root, task_id, reference, verifier_actor=verifier_actor, binding=binding
    )
    if not mutation_facts.passed:
        raise _error(
            "Selected installed mutations are not current and killed", "NODE_MUTATIONS_INVALID"
        )
    run = root / reference.ref
    run = run.parent
    if (
        not re.fullmatch(r"IMUT-[0-9a-f]{16}", run.name)
        or run.parent != root / ".ai/tasks" / task_id / "logs"
    ):
        raise _error("Selected installed run is not the exact task-relative IMUT role")
    if (run / "node").exists() or (run / "evidence.json").exists():
        raise _error("The selected IMUT Node role was already claimed")
    (run / "node").mkdir()
    return _identity(_safe_info(run / "node", directory=True))


def _node_inventory(node_dir: Path, level: str, plan: Any) -> list[dict[str, object]]:
    allowed = {
        "raw",
        "home",
        "tmp",
        "cache",
        "user.npmrc",
        "global.npmrc",
        "checkout",
        "source-manifest.json",
        "run.json",
    }
    if level in {"V1", "V2"}:
        allowed.update(
            {"coverage", "expected-map.json", "source.diff", "domain-materials", "vitest.json"}
        )
    if not {child.name for child in node_dir.iterdir()}.issubset(allowed):
        raise _error("Node output contains an unknown top-level role")
    raw = node_dir / "raw"
    expected = {"setup-clone", "setup-checkout", *(e.execution_id for e in plan.executions)}
    if raw.exists():
        if not {child.name for child in raw.iterdir()}.issubset(expected):
            raise _error("Node raw outputs contain an undeclared execution")
        for directory in raw.iterdir():
            if {child.name for child in directory.iterdir()} != {
                "stdout.raw",
                "stderr.raw",
                "stdout.log",
                "stderr.log",
                "receipt.json",
            }:
                raise _error("Node raw execution originals have unknown or missing members")
    inventory = _inventory(node_dir)
    return [row for row in _content(inventory) if row["path"] != "run.json"]


def _products(node_dir: Path, source: Mapping[str, Any], checkout: Path) -> dict[str, Any]:
    raw = _read(node_dir / "vitest.json", limit=MAX_JSON_BYTES)
    test_sources = {
        row["path"]: _read(checkout / row["path"])
        for row in source["files"]
        if row["path"].startswith("tests/local/") and row["path"].endswith(".test.ts")
    }
    result = validate_node_product_tests(
        _json_bytes(raw),
        execution_root=checkout,
        tracked_tests=test_sources,
        expected_coverage=_json(node_dir / "coverage/coverage-final.json"),
    )
    return {
        "report": {"ref": "vitest.json", "size": len(raw), "sha256": _sha(raw)},
        "expected_tests": [{"file": p, "sha256": _sha(v)} for p, v in sorted(test_sources.items())],
        "result": result,
    }


def _product_projection(product: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "report": {**product["report"], "ref": f"logs/{run_id}/node/vitest.json"},
        **{k: product["result"][k] for k in ("inventory_sha256", "acceptance", "integration")},
    }


def _installed_projection(
    reference: InstalledMutationReference,
    current: InstalledMutationCurrent,
    facts: InstalledMutationFacts,
) -> dict[str, Any]:
    return {
        "reference": asdict(reference),
        "inputs_sha256": current.inputs.sha256,
        "results": [list(row) for row in facts.results],
    }


def _context(
    root: Path, task_id: str, run_id: str, binding: Mapping[str, Any], manifests: Mapping[str, Any]
) -> VerificationContext:
    from aiflow.verification import NodePlanBindings

    run = root / ".ai/tasks" / task_id / "logs" / run_id
    node_dir = run / "node"
    runtime = Path(manifests["node.json"]["runtime"]["root"])
    return VerificationContext(
        root,
        task_id,
        binding["base_commit"],
        binding["subject_commit"],
        manifests["host-tools.json"]["python"]["path"],
        run_id,
        node_bindings=NodePlanBindings(
            str(runtime / "node.exe"),
            str(runtime / "node_modules/npm/bin/npm-cli.js"),
            manifests["host-tools.json"]["git"]["path"],
            node_dir / "checkout",
            node_dir / "user.npmrc",
            node_dir / "global.npmrc",
            node_dir / "coverage",
            node_dir / "expected-map.json",
            node_dir / "source-manifest.json",
        ),
    )


def _native_ownership_applicable(root: Path, source: Mapping[str, Any]) -> bool:
    """Derive the fixed output role from ordinary, reviewed subject inputs."""
    _ancestors(root)
    rows: dict[str, Mapping[str, Any]] = {}
    for row in source["files"]:
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            raise _error("Native ownership source inventory is invalid")
        name = row["path"]
        if name in NATIVE_OWNERSHIP_INPUTS:
            if name in rows:
                raise _error("Native ownership source role is duplicated")
            rows[name] = row
    if rows and set(rows) != set(NATIVE_OWNERSHIP_INPUTS):
        raise _error("Native ownership requires both fixed source roles")
    for relative, digest in NATIVE_OWNERSHIP_INPUTS.items():
        # Even an absent leaf cannot hide a link or non-directory in its
        # existing ancestors. Never follow an untracked role to read bytes.
        location = root
        for part in Path(relative).parts[:-1]:
            location /= part
            try:
                location.lstat()
            except FileNotFoundError:
                break
            except OSError as error:
                raise _error("Native ownership source ancestor cannot be inspected") from error
            _safe_info(location, directory=True)
        path = root / relative
        try:
            path.lstat()
        except FileNotFoundError:
            if relative in rows:
                raise _error("Tracked native ownership source is missing") from None
            continue
        except OSError as error:
            raise _error("Native ownership source role cannot be inspected") from error
        _safe_info(path)
        if relative not in rows:
            raise _error("Untracked input cannot declare a native ownership role")
        row = rows[relative]
        if row.get("sha256") != digest:
            raise _error("Native ownership source differs from its reviewed fixed version")
        data = _read(path)
        if type(row.get("size")) is not int or row["size"] != len(data) or _sha(data) != digest:
            raise _error("Native ownership source bytes differ from the subject")
    return bool(rows)


def _native_ownership_inventory(checkout: Path, source: Mapping[str, Any]) -> dict[str, Any] | None:
    """Validate generated bytes, never infer authority from their sidecar."""
    applicable = _native_ownership_applicable(checkout, source)
    runtime = checkout / ".runtime"
    runtime_present = False
    try:
        runtime.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise _error("Native ownership runtime ancestor cannot be inspected") from error
    else:
        runtime_present = True
        _ancestors(runtime)
    # WindowsPath equality folds case. Verify the actual two fixed directory
    # names without following or reading any unrelated child.
    for parent, name in ((checkout, ".runtime"), (runtime, "native-ownership")):
        if parent == runtime and not runtime_present:
            continue
        before = _identity(_safe_info(parent, directory=True))
        matches = []
        try:
            with os.scandir(parent) as entries:
                for index, child in enumerate(entries):
                    if index >= MAX_ENTRIES:
                        raise _error("Native ownership role enumeration exceeds its item limit")
                    if child.name.casefold() == name:
                        matches.append(child.name)
        except OSError as error:
            raise _error("Native ownership role names cannot be inspected") from error
        if before != _identity(_safe_info(parent, directory=True)):
            raise _error("Native ownership role directory changed during enumeration")
        if matches and matches != [name]:
            raise _error("Native ownership role directory has a case alias")
    directory = checkout / NATIVE_OWNERSHIP_DIRECTORY
    try:
        directory.lstat()
    except FileNotFoundError:
        if applicable:
            raise _error(
                "Successful Node check did not produce the native ownership cache"
            ) from None
        return None
    except OSError as error:
        raise _error("Native ownership cache cannot be inspected") from error
    if not applicable:
        raise _error("Native ownership cache has no reviewed source roles")
    source_sha256 = NATIVE_OWNERSHIP_INPUTS["scripts/windows-owned-launcher.cs"]
    executable_name = f"own-{source_sha256}.exe"
    inventory = _inventory(directory)
    if {row["path"] for row in inventory["entries"]} != {
        executable_name,
        executable_name + ".json",
    } or any(row["kind"] != "file" for row in inventory["entries"]):
        raise _error("Native ownership cache must contain exactly its two ordinary files")
    executable = _read(directory / executable_name)
    raw = _read(directory / (executable_name + ".json"), limit=MAX_JSON_BYTES)
    sidecar = _json_bytes(raw)
    expected = {"sourceHash": source_sha256, "executableHash": _sha(executable)}
    wire = json.dumps(expected, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    if (
        not executable
        or not isinstance(sidecar, dict)
        or set(sidecar) != set(expected)
        or sidecar != expected
        or raw != wire
    ):
        raise _error("Native ownership sidecar differs from its fixed source/content wire")
    _unchanged(inventory)
    return inventory


def _fixtures(
    checkout: Path, temporary: Path, source: Mapping[str, Any], *, revision: int = 1
) -> dict[str, object]:
    if type(revision) is not int or revision not in {1, 2}:
        raise _error("Node fixture profile revision is unsupported")
    fixture_root = checkout / ".runtime/no-zcode-p0p1/probe-test-tmp"
    fixtures: dict[str, object] = {}
    if revision == 2:
        native = _native_ownership_inventory(checkout, source)
        if native is not None:
            fixtures["native_ownership"] = native
    if fixture_root.exists():
        for item in fixture_root.iterdir():
            if not item.name.startswith("live-fake-"):
                raise _error("Fake fixture output is outside the fixed owned prefix")
        fixtures["checkout"] = _inventory(fixture_root)
    # The fixed prefixes are extracted only from the exact reviewed tracked tests.
    prefixes = set()
    for row in source["files"]:
        if row["path"].startswith("tests/local/") and row["path"].endswith(".ts"):
            text = _read(checkout / row["path"]).decode("utf-8", errors="strict")
            prefixes.update(
                re.findall(
                    r"(?:tmpdir\(\)|(?:process\.)?env\.(?:TMP|TEMP))\s*,\s*['\"]([A-Za-z0-9_.-]+)['\"]",
                    text,
                )
            )
    for item in temporary.iterdir():
        if not any(item.name.startswith(prefix) for prefix in prefixes):
            raise _error("Temporary fixture output has no reviewed source prefix")
    fixtures["temporary"] = _inventory(temporary)
    return fixtures


def _output_check(
    checkout: Path,
    source: Mapping[str, Any],
    dist: Mapping[str, Any],
    dependencies: Mapping[str, Any],
    fixtures: Mapping[str, Any],
    *,
    revision: int = 1,
) -> None:
    if type(revision) is not int or revision not in {1, 2}:
        raise _error("Node output profile revision is unsupported")
    if revision == 2:
        # Derive all fixed roots again. A supplied inventory cannot name a
        # foreign directory or grant an otherwise absent output role.
        observed = _fixtures(checkout, checkout.parent / "tmp", source, revision=2)
        if _canonical(observed) != _canonical(fixtures):
            raise _error("Node fixture originals differ from their source-derived owned roles")
    _unchanged(dist)
    _unchanged(dependencies)
    for inventory in fixtures.values():
        _unchanged(inventory)
    allowed_files = {row["path"] for row in source["files"]}
    # Complete checkout enumeration names unknown outputs without reading ignored
    # material from the original task worktree.
    count = 0
    for directory, names, files in os.walk(checkout, followlinks=False):
        location = Path(directory)
        relative = location.relative_to(checkout).as_posix()
        if relative == ".":
            for known in (".git", "node_modules", "dist", ".runtime"):
                if known in names:
                    names.remove(known)
        for name in (*names, *files):
            count += 1
            if count > MAX_ENTRIES:
                raise _error("Checkout output enumeration exceeds its item limit")
            path = location / name
            _safe_info(path, directory=path.is_dir())
            if name in files and path.relative_to(checkout).as_posix() not in allowed_files:
                raise _error("Checkout contains an undeclared execution output")
    runtime = checkout / ".runtime"
    if runtime.exists():
        expected = checkout / ".runtime/no-zcode-p0p1/probe-test-tmp"
        for directory, names, files in os.walk(runtime, followlinks=False):
            location = Path(directory)
            if location == expected or (
                revision == 2
                and "native_ownership" in fixtures
                and location.relative_to(checkout).as_posix() == NATIVE_OWNERSHIP_DIRECTORY
            ):
                names.clear()
                continue
            if files or any(
                not expected.is_relative_to(location / name)
                and not (
                    revision == 2
                    and "native_ownership" in fixtures
                    and (location / name).relative_to(checkout).as_posix()
                    == NATIVE_OWNERSHIP_DIRECTORY
                )
                for name in names
            ):
                raise _error("Checkout runtime contains an undeclared output")


def execute_node_verification(
    root: Path,
    task_id: str,
    *,
    material_sha256: str,
    context: VerificationContext,
    bundle: PolicyBundle,
    facts: EvidenceFacts,
    installed_reference: InstalledMutationReference | None = None,
    node_claim_identity: Mapping[str, int] | None = None,
) -> dict[str, object]:
    """Execute the sole fixed plan in a new checkout, preserving failed originals."""
    root = root.absolute()
    binding, current_bundle = _binding(root, task_id)
    revision = _profile_revision(binding)
    v2 = facts.verification_level == "V2"
    if (
        bundle.sha256 != current_bundle.sha256
        or facts.mode != "local"
        or facts.verification_level not in ({"V0", "V1", "V2"} if revision == 2 else {"V0", "V1"})
    ):
        raise _error("Node execution facts do not match this local profile")
    prepared, manifests = _load_prepared(root, task_id, material_sha256, binding)
    _check_materials(root, prepared, manifests)
    if not _RUN.fullmatch(context.run_id):
        raise _error("Node run ID is invalid")
    run = root / ".ai/tasks" / task_id / "logs" / context.run_id
    node_dir = run / "node"
    installed_current = None
    installed_facts = None
    installed_projection = None
    if v2:
        if (
            installed_reference is None
            or node_claim_identity is None
            or installed_reference.ref != (run / "run.json").relative_to(root).as_posix()
            or not re.fullmatch(r"IMUT-[0-9a-f]{16}", context.run_id)
            or facts.run_dir != run
            or _canonical(_identity(_safe_info(node_dir, directory=True)))
            != _canonical(node_claim_identity)
            or list(node_dir.iterdir())
        ):
            raise _error("Node V2 must use the exact exclusively claimed empty IMUT Node role")
        from aiflow.task_service import read_task_record_strict

        record = read_task_record_strict(root, task_id)
        starts = [event for event in record.events if event["event_type"] == "verification_started"]
        installed_current, installed_facts = _installed_for_node(
            root, task_id, installed_reference, binding=binding, manifests=manifests
        )
        if not installed_facts.passed:
            raise _error(
                "Selected installed mutations are not current and killed", "NODE_MUTATIONS_INVALID"
            )
        installed_projection = _installed_projection(
            installed_reference, installed_current, installed_facts
        )
        if (
            record.task["current_state"] != "VERIFYING"
            or not starts
            or starts[-1]["actor"] != installed_current.inputs.verifier_actor
        ):
            raise _error("Node V2 verification was not started by its bound independent verifier")
    elif (
        installed_reference is not None
        or node_claim_identity is not None
        or facts.run_dir != run
        or run.exists()
    ):
        raise _error("A Node run must own a new task-relative directory")
    before = _root_snapshot(root, task_id, run)
    if not v2:
        run.mkdir()
        node_dir.mkdir()
    for name in ("raw", "home", "tmp", "cache"):
        (node_dir / name).mkdir()
    for name in ("user.npmrc", "global.npmrc"):
        _write_new(node_dir / name, b"")
    bound_context = _context(root, task_id, context.run_id, binding, manifests)
    roles = bound_context.node_bindings
    assert roles is not None
    environment = _environment(
        Path(roles.node_executable), roles.execution_root, node_dir, Path(roles.git_executable)
    )
    source = manifests["source.json"]
    checkout = roles.execution_root
    clone = _process(
        (
            roles.git_executable,
            *_GIT_OPTIONS,
            "clone",
            "--no-hardlinks",
            "--no-checkout",
            "--local",
            "--",
            str(root),
            str(checkout),
        ),
        cwd=root,
        environment=environment,
        timeout=30,
        output=node_dir / "raw/setup-clone",
    )
    if not _successful(clone):
        raise _error("Owned Git clone could not be established", "NODE_CHECKOUT_FAILED")
    checkout_receipt = _process(
        (
            roles.git_executable,
            *_GIT_OPTIONS,
            "-c",
            "core.autocrlf=false",
            "checkout",
            "--detach",
            binding["subject_commit"],
        ),
        cwd=checkout,
        environment=environment,
        timeout=30,
        output=node_dir / "raw/setup-checkout",
    )
    if not _successful(checkout_receipt):
        raise _error("Exact subject checkout could not be established", "NODE_CHECKOUT_FAILED")
    if (
        (checkout / "node_modules").exists()
        or (checkout / "dist").exists()
        or (checkout / ".runtime").exists()
    ):
        raise _error("Tracked input collides with an owned execution output")
    copied = _copy_tree(
        Path(manifests["dependencies.json"]["root"]),
        checkout / "node_modules",
        manifests["dependencies.json"],
    )
    protected = _checkout_files(checkout, source)
    if revision == 2:
        _native_ownership_applicable(checkout, source)
    inputs = {
        "source": source,
        "runtime": manifests["node.json"]["runtime"],
        "dependencies": copied,
        "prepared_dependencies": manifests["dependencies.json"],
        "engine": manifests["engine.json"],
        "host_tools": manifests["host-tools.json"],
    }
    tracked_ts = [
        {"path": row["path"], "sha256": row["sha256"]}
        for row in source["files"]
        if row["path"].startswith("src/local/") and row["path"].endswith(".ts")
    ]
    _write_new(roles.source_manifest_file, _canonical({"root": str(checkout), "files": tracked_ts}))
    expected_dist = _dist_paths(checkout, source)
    plan = parse_verification_plan(bundle, bound_context, level=facts.verification_level)
    if not plan.valid:
        raise _error("The fixed Node verification plan is unavailable", "NODE_PLAN_INVALID")
    public: list[dict[str, object]] = []
    private: list[dict[str, object]] = []
    failure: str | None = None
    coverage: dict[str, object] | None = None
    products: dict[str, Any] | None = None
    dist: dict[str, object] | None = None
    build_dist: dict[str, object] | None = None
    native_checked = False
    native_seal: dict[str, Any] | None = None
    rebuild_commands = {
        check.argv for check in plan.checks if check.check_id in {"node_check", "ts_coverage"}
    }
    outputs: dict[str, object] = {}
    try:
        for execution in plan.executions:
            _check_root(root, task_id, before, run)
            if _canonical(_checkout_files(checkout, source)) != _canonical(protected):
                raise _error("Protected checkout source changed", "NODE_ROOT_DRIFT")
            _unchanged(copied)
            _unchanged(inputs["runtime"])
            if dist is not None:
                _unchanged(dist)
            if (
                revision == 2
                and native_checked
                and _canonical(_native_ownership_inventory(checkout, source))
                != _canonical(native_seal)
            ):
                raise _error("Sealed native ownership output changed", "NODE_OUTPUT_INVALID")
            receipt = _process(
                execution.argv,
                cwd=execution.cwd,
                environment=environment,
                timeout=execution.timeout_seconds,
                output=node_dir / "raw" / execution.execution_id,
            )
            private.append({"execution_id": execution.execution_id, "receipt": receipt})
            public.append(_public_execution(execution, receipt, bound_context))
            if not _successful(receipt):
                failure = "NODE_PROCESS_FAILED"
                break
            if revision == 2 and "node_check" in execution.check_ids:
                # Seal the first successful check, including explicit
                # inapplicability. Later suites never choose another cache.
                _validate_receipt(
                    node_dir / "raw" / execution.execution_id,
                    receipt,
                    argv=execution.argv,
                    cwd=execution.cwd,
                    environment=environment,
                )
                native_seal = _native_ownership_inventory(checkout, source)
                native_checked = True
            if "node_build" in execution.check_ids:
                build_dist = dist = _dist(checkout, expected_dist)
            elif execution.argv in rebuild_commands:
                if build_dist is None:
                    raise _error("Fixed build output is missing")
                rebuilt = _dist(checkout, expected_dist)
                if _canonical(_content(rebuilt)) != _canonical(_content(build_dist)):
                    raise _error("Rebuilt Node output content changed", "NODE_OUTPUT_INVALID")
                dist = rebuilt
        if failure is None:
            if revision == 2 and (
                not native_checked
                or _canonical(_native_ownership_inventory(checkout, source))
                != _canonical(native_seal)
            ):
                raise _error("Final native ownership output differs from its first seal")
            if facts.verification_level in {"V1", "V2"}:
                _changed, _deleted, raw = _changed_lines(
                    root, str(binding["base_commit"]), str(binding["subject_commit"])
                )
                _write_new(node_dir / "source.diff", raw)
                coverage = _coverage(
                    checkout,
                    node_dir,
                    source,
                    str(binding["base_commit"]),
                    str(binding["subject_commit"]),
                    root,
                    **({"revision": 2} if revision == 2 else {}),
                )
                if v2:
                    products = _products(node_dir, source, checkout)
            if dist is None or build_dist is None:
                raise _error("Fixed build output is missing")
            fixtures = _fixtures(
                checkout,
                node_dir / "tmp",
                source,
                **({"revision": 2} if revision == 2 else {}),
            )
            if revision == 2:
                if _canonical(fixtures.get("native_ownership")) != _canonical(native_seal):
                    raise _error("Native ownership fixture does not preserve its first seal")
                if native_seal is not None:
                    fixtures["native_ownership"] = native_seal
            _output_check(
                checkout,
                source,
                dist,
                copied,
                fixtures,
                **({"revision": 2} if revision == 2 else {}),
            )
            outputs = {"build_dist": build_dist, "dist": dist, "fixtures": fixtures}
            _check_root(root, task_id, before, run)
            _check_materials(root, prepared, manifests)
            if _canonical(_checkout_files(checkout, source)) != _canonical(protected):
                raise _error("Protected checkout source changed", "NODE_ROOT_DRIFT")
    except (AiflowError, OSError, ValueError) as error:
        failure = error.code if isinstance(error, AiflowError) else "NODE_EXECUTION_INVALID"
    if v2:
        assert installed_reference is not None
        installed_current, installed_facts = _installed_for_node(
            root, task_id, installed_reference, binding=binding, manifests=manifests
        )
    if v2:
        checks = _checks(
            plan,
            bound_context,
            public,
            coverage,
            failure,
            products=products,
            installed=installed_facts,
        )
    else:
        checks = _checks(plan, bound_context, public, coverage, failure)
    # An output/material failure invalidates a process-success check as well.
    if failure and all(check["status"] == "passed" for check in checks):
        checks[-1]["status"] = "failed"
    contract = node_execution_contract(plan, bound_context)
    run_document = {
        "schema_version": "1.0",
        "kind": "aiflow-node-run-3.1" if revision == 1 else "aiflow-node-run-3.2",
        "binding": binding,
        "prepared_sha256": material_sha256,
        "roots": {
            "original": before,
            "checkout": protected,
            "clone": clone,
            "checkout_receipt": checkout_receipt,
        },
        "inputs": inputs,
        "environment": environment,
        "executions": private,
        "outputs": outputs,
        "coverage": _coverage_originals(node_dir, coverage) if coverage is not None else None,
    }
    if revision == 2:
        outputs["node_inventory"] = _node_inventory(node_dir, facts.verification_level, plan)
    if v2:
        assert (
            installed_reference is not None
            and installed_current is not None
            and installed_facts is not None
        )
        run_document["installed_mutation"] = installed_projection
        run_document["product_tests"] = products
    run_data = _canonical(run_document)
    if len(run_data) > MAX_JSON_BYTES:
        raise _error("Run original exceeds its bounded JSON limit")
    _write_new(node_dir / "run.json", run_data)
    prepared_data = _canonical(prepared)
    node_binding = {
        "profile": binding["profile"],
        "subject_tree": binding["subject_tree"],
        "prepared": {
            "ref": f"logs/node-prepared/{material_sha256}/prepared.json",
            "size": len(prepared_data),
            "sha256": material_sha256,
        },
        "run": {
            "ref": f"logs/{context.run_id}/node/run.json",
            "size": len(run_data),
            "sha256": _sha(run_data),
        },
        "materials_sha256": _sha(_canonical(inputs)),
        "semantic_contract_sha256": _semantic_digest(binding),
        "execution_contract_sha256": _sha(_canonical(contract)),
        "environment_sha256": _sha(_canonical(environment)),
        "coverage": coverage,
    }
    if v2:
        node_binding["product_tests"] = (
            _product_projection(products, context.run_id) if products is not None else None
        )
    evidence: dict[str, object] = {
        "schema_version": "3.1" if revision == 1 else "3.2",
        "task_id": task_id,
        "decision_unit_ids": list(facts.decision_unit_ids),
        "repository_id": facts.repository_id,
        "branch": facts.branch,
        "base_commit": facts.base_commit,
        "subject_commit": facts.subject_commit,
        "spec_sha256": facts.spec_sha256,
        "policy_sha256": facts.policy_sha256,
        "classification_input_sha256": facts.classification_input_sha256,
        "verification_level": facts.verification_level,
        "mode": "local",
        "checks": checks,
        "unverified_scenarios": [
            str(check["check_id"]) for check in checks if check["status"] == "unverified"
        ],
        "conclusion": "passed"
        if failure is None and all(check["status"] == "passed" for check in checks)
        else "failed",
        "generated_at": facts.generated_at,
        "reproduce_command": list(facts.reproduce_command),
        "node_binding": node_binding,
        "node_binding_sha256": _sha(_canonical(node_binding)),
    }
    from aiflow.evidence import validate_node_evidence

    if v2:
        evidence["installed_mutation"] = run_document["installed_mutation"]
    else:
        validate_node_evidence(evidence)
    return evidence


def recheck_node_evidence(
    root: Path, task_id: str, evidence: Mapping[str, object]
) -> NodeEvidenceFacts:
    """Read the same immutable originals for every production evidence consumer."""
    evidence_digest: str | None = None
    materials: str | None = None
    run_id: str | None = None
    try:
        from aiflow.evidence import validate_node_evidence

        validate_node_evidence(evidence)
        evidence_digest = _sha(_canonical(evidence))
        root = root.absolute()
        binding, bundle = _binding(root, task_id)
        revision = _profile_revision(binding)
        v2 = evidence["verification_level"] == "V2"
        from aiflow.storage import read_task_json
        from aiflow.task_service import read_task_record_strict

        task = read_task_record_strict(root, task_id).task
        classification = read_task_json(
            root, task_id, "classification.json", contract_name="classification"
        )
        units = [unit["decision_unit_id"] for unit in task["decision_units"]]
        if evidence.get("decision_unit_ids") != units or evidence.get(
            "verification_level"
        ) != classification.get("effective_verification_level"):
            raise _error(
                "Node evidence decision units or level differ from current facts",
                "NODE_BINDING_STALE",
            )
        for key in (
            "repository_id",
            "task_id",
            "branch",
            "base_commit",
            "subject_commit",
            "spec_sha256",
            "policy_sha256",
            "classification_input_sha256",
        ):
            if evidence.get(key) != binding[key]:
                raise _error("Node evidence current task binding differs", "NODE_BINDING_STALE")
        compact = cast(dict[str, Any], evidence["node_binding"])
        if revision == 2 and (
            compact["subject_tree"] != binding["subject_tree"]
            or _canonical(compact["profile"]) != _canonical(binding["profile"])
        ):
            raise _error("Node revision2 public profile/tree binding differs", "NODE_BINDING_STALE")
        selector = compact["prepared"]["sha256"]
        prepared, manifests = _load_prepared(root, task_id, selector, binding)
        expected_prepared = f"logs/node-prepared/{selector}/prepared.json"
        if compact["prepared"]["ref"] != expected_prepared or compact["prepared"]["size"] != len(
            _canonical(prepared)
        ):
            raise _error("Evidence prepared reference is not the fixed selected original")
        _check_materials(root, prepared, manifests)
        run_ref = compact["run"]["ref"]
        match = re.fullmatch(r"logs/([A-Za-z0-9][A-Za-z0-9_.-]*)/node/run\.json", run_ref)
        if match is None:
            raise _error("Node evidence run reference is not task-relative")
        run_id = match[1]
        context = _context(root, task_id, run_id, binding, manifests)
        roles = context.node_bindings
        assert roles is not None
        run_dir = root / ".ai/tasks" / task_id / "logs" / run_id / "node"
        raw = _read(run_dir / "run.json", limit=MAX_JSON_BYTES)
        if (
            type(compact["run"]["size"]) is not int
            or compact["run"]["size"] != len(raw)
            or compact["run"]["sha256"] != _sha(raw)
        ):
            raise _error("Node evidence run digest differs from the original")
        document = _json_bytes(raw)
        if (
            not isinstance(document, dict)
            or set(document)
            != {
                "schema_version",
                "kind",
                "binding",
                "prepared_sha256",
                "roots",
                "inputs",
                "environment",
                "executions",
                "outputs",
                "coverage",
            }
            | ({"installed_mutation", "product_tests"} if v2 else set())
            or document["schema_version"] != "1.0"
            or document["kind"]
            != ("aiflow-node-run-3.1" if revision == 1 else "aiflow-node-run-3.2")
            or document["prepared_sha256"] != selector
            or _canonical(document["binding"]) != _canonical(binding)
            or _canonical(document) != raw
        ):
            raise _error("Node run original has an invalid closed contract")
        expected_environment = _environment(
            Path(roles.node_executable), roles.execution_root, run_dir, Path(roles.git_executable)
        )
        if _canonical(document["environment"]) != _canonical(expected_environment) or compact[
            "environment_sha256"
        ] != _sha(_canonical(expected_environment)):
            raise _error("Node run environment differs from the fixed role environment")
        for name in ("user.npmrc", "global.npmrc"):
            if _read(run_dir / name) != b"":
                raise _error("Owned npm configuration is no longer empty")
        inputs = document["inputs"]
        if set(inputs) != {
            "source",
            "runtime",
            "dependencies",
            "prepared_dependencies",
            "engine",
            "host_tools",
        }:
            raise _error("Node run inputs have unknown roles")
        for role, manifest in (
            ("source", "source.json"),
            ("prepared_dependencies", "dependencies.json"),
            ("engine", "engine.json"),
            ("host_tools", "host-tools.json"),
        ):
            if _canonical(inputs[role]) != _canonical(manifests[manifest]):
                raise _error("Actual run input differs from the prepared material")
        if _canonical(inputs["runtime"]) != _canonical(manifests["node.json"]["runtime"]):
            raise _error("Actual Node runtime differs from the prepared material")
        if Path(inputs["dependencies"]["root"]) != roles.execution_root / "node_modules":
            raise _error("Execution dependency role is not the owned checkout copy")
        _unchanged(inputs["dependencies"])
        if _canonical(_content(inputs["dependencies"])) != _canonical(
            _content(manifests["dependencies.json"])
        ):
            raise _error("Execution dependency copy differs from its prepared bytes")
        materials = _sha(_canonical(inputs))
        if compact["materials_sha256"] != materials or compact[
            "semantic_contract_sha256"
        ] != _semantic_digest(binding):
            raise _error("Node evidence material or semantic contract digest differs")
        roots = document["roots"]
        if set(roots) != {"original", "checkout", "clone", "checkout_receipt"}:
            raise _error("Node run root roles are incomplete")
        _check_root(root, task_id, roots["original"], run_dir.parent)
        source = manifests["source.json"]
        source_manifest = {
            "root": str(roles.execution_root),
            "files": [
                {"path": row["path"], "sha256": row["sha256"]}
                for row in source["files"]
                if row["path"].startswith("src/local/") and row["path"].endswith(".ts")
            ],
        }
        if _read(roles.source_manifest_file, limit=MAX_JSON_BYTES) != _canonical(source_manifest):
            raise _error("Owned source mapping input differs from the full subject inventory")
        if _canonical(_checkout_files(roles.execution_root, source)) != _canonical(
            roots["checkout"]
        ):
            raise _error("Owned source checkout has changed")
        clone_argv = (
            roles.git_executable,
            *_GIT_OPTIONS,
            "clone",
            "--no-hardlinks",
            "--no-checkout",
            "--local",
            "--",
            str(root),
            str(roles.execution_root),
        )
        checkout_argv = (
            roles.git_executable,
            *_GIT_OPTIONS,
            "-c",
            "core.autocrlf=false",
            "checkout",
            "--detach",
            binding["subject_commit"],
        )
        _validate_receipt(
            run_dir / "raw/setup-clone",
            roots["clone"],
            argv=clone_argv,
            cwd=root,
            environment=expected_environment,
        )
        _validate_receipt(
            run_dir / "raw/setup-checkout",
            roots["checkout_receipt"],
            argv=checkout_argv,
            cwd=roles.execution_root,
            environment=expected_environment,
        )
        plan = parse_verification_plan(
            bundle,
            context,
            level=cast(Any, evidence["verification_level"]),
            tool_available=lambda _argv: True,
        )
        if not plan.valid:
            raise _error("Current Node execution contract is unavailable")
        if compact["execution_contract_sha256"] != _sha(
            _canonical(node_execution_contract(plan, context))
        ):
            raise _error("Node execution contract changed")
        actual = document["executions"]
        if not isinstance(actual, list) or len(actual) > len(plan.executions):
            raise _error("Node run execution inventory is invalid")
        public: list[dict[str, object]] = []
        native_check_succeeded = False
        for execution, original in zip(plan.executions, actual, strict=False):
            if (
                set(original) != {"execution_id", "receipt"}
                or original["execution_id"] != execution.execution_id
            ):
                raise _error("Node run execution order differs from the fixed plan")
            _validate_receipt(
                run_dir / "raw" / execution.execution_id,
                original["receipt"],
                argv=execution.argv,
                cwd=execution.cwd,
                environment=expected_environment,
            )
            if original["receipt"]["timeout_seconds"] != execution.timeout_seconds:
                raise _error("Node execution deadline differs from the fixed plan")
            public.append(_public_execution(execution, original["receipt"], context))
            if "node_check" in execution.check_ids and _successful(original["receipt"]):
                native_check_succeeded = True
        if len(actual) != len(plan.executions):
            raise _error(
                "Node verification did not execute every required process",
                "NODE_EVIDENCE_NOT_PASSED",
            )
        if revision == 2:
            _native_ownership_applicable(roles.execution_root, source)
            if not native_check_succeeded:
                raise _error(
                    "Node output replay lacks its actual successful fixed node check",
                    "NODE_EVIDENCE_NOT_PASSED",
                )
        expected_dist = _dist_paths(roles.execution_root, source)
        outputs = document["outputs"]
        if set(outputs) != {"build_dist", "dist", "fixtures"} | (
            {"node_inventory"} if revision == 2 else set()
        ):
            raise _error("Node run output inventory is incomplete")
        if revision == 2 and _canonical(
            _node_inventory(run_dir, str(evidence["verification_level"]), plan)
        ) != _canonical(outputs["node_inventory"]):
            raise _error("The complete Node output content or membership changed")
        dist = _dist(roles.execution_root, expected_dist)
        if _canonical(dist) != _canonical(outputs["dist"]):
            raise _error("Node build outputs changed")
        build_dist = outputs["build_dist"]
        if (
            not isinstance(build_dist, dict)
            or set(build_dist) != set(dist)
            or build_dist["root"] != dist["root"]
            or type(build_dist["total_bytes"]) is not int
            or build_dist["total_bytes"] != dist["total_bytes"]
            or _canonical(_content(build_dist)) != _canonical(_content(dist))
        ):
            raise _error("Initial and final Node output content differs", "NODE_OUTPUT_INVALID")
        _output_check(
            roles.execution_root,
            source,
            dist,
            inputs["dependencies"],
            outputs["fixtures"],
            **({"revision": 2} if revision == 2 else {}),
        )
        coverage = None
        if evidence["verification_level"] in {"V1", "V2"}:
            bound_coverage_originals = _coverage_originals(run_dir, compact["coverage"])
            if _canonical(bound_coverage_originals) != _canonical(document["coverage"]):
                raise _error("Node coverage original bytes changed")
            coverage = _coverage(
                roles.execution_root,
                run_dir,
                source,
                str(binding["base_commit"]),
                str(binding["subject_commit"]),
                root,
                **({"revision": 2} if revision == 2 else {}),
            )
        expected_originals = (
            _coverage_originals(run_dir, coverage) if coverage is not None else None
        )
        if _canonical(expected_originals) != _canonical(document["coverage"]) or _canonical(
            coverage
        ) != _canonical(compact["coverage"]):
            raise _error("Node coverage compact counts differ from the bound originals")
        products = None
        installed_facts = None
        if v2:
            from aiflow.installed_mutations import InstalledMutationReference

            projected = cast(dict[str, Any], evidence["installed_mutation"])
            reference = InstalledMutationReference(**projected["reference"])
            if reference.ref != (run_dir.parent / "run.json").relative_to(root).as_posix():
                raise _error("Node and installed mutation references select different owned runs")
            installed_current, installed_facts = _installed_for_node(
                root,
                task_id,
                reference,
                verifier_actor=str(evidence["verifier_actor"]),
                binding=binding,
                manifests=manifests,
            )
            if (
                not installed_facts.passed
                or installed_current.inputs.verifier_context_sha256
                != evidence["verifier_context_sha256"]
                or _canonical(_installed_projection(reference, installed_current, installed_facts))
                != _canonical(projected)
                or _canonical(document["installed_mutation"]) != _canonical(projected)
            ):
                raise _error(
                    "Node installed mutation projection or verifier is stale",
                    "NODE_MUTATIONS_INVALID",
                )
            products = _products(run_dir, source, roles.execution_root)
            if _canonical(products) != _canonical(document["product_tests"]) or _canonical(
                _product_projection(products, run_id)
            ) != _canonical(compact["product_tests"]):
                raise _error("Node product report projection differs from complete originals")
        if v2:
            derived = _checks(
                plan, context, public, coverage, None, products=products, installed=installed_facts
            )
        else:
            derived = _checks(plan, context, public, coverage, None)
        if _canonical(derived) != _canonical(evidence["checks"]):
            raise _error("Node evidence check results differ from the actual receipts")
        if evidence["conclusion"] != "passed" or evidence["unverified_scenarios"] != []:
            return NodeEvidenceFacts(
                True, False, ("NODE_EVIDENCE_NOT_PASSED",), evidence_digest, materials, run_id
            )
        return NodeEvidenceFacts(
            True, True, (), evidence_digest, materials, run_id, installed_facts
        )
    except (
        AiflowError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        subprocess.SubprocessError,
    ) as error:
        reason = error.code if isinstance(error, AiflowError) else "NODE_EVIDENCE_INVALID"
        return NodeEvidenceFacts(False, False, (reason,), evidence_digest, materials, run_id)


def _ci_ref(path: Path, attempt: Path) -> dict[str, Any]:
    data = _read(path, limit=MAX_JSON_BYTES)
    return {"ref": path.relative_to(attempt).as_posix(), "size": len(data), "sha256": _sha(data)}


def _ci_attempt_coordinate(source_root: Path, platform: Mapping[str, Any]) -> Path:
    if (
        not source_root.is_absolute()
        or source_root.name != "source"
        or any(
            type(platform.get(key)) is not int or platform[key] < 1
            for key in ("run_id", "run_attempt")
        )
    ):
        raise _error("CI source/platform coordinates are invalid", "NODE_CI_BINDING_INVALID")
    return source_root.parent / ".tmp/node-ci" / f"{platform['run_id']}-{platform['run_attempt']}"


def _ci_kernel_inputs(
    source_root: Path,
    attempt: Path,
    admission: Mapping[str, Any],
    source_tuple: Mapping[str, Any],
    descriptor: Mapping[str, Any],
) -> None:
    """Physical coherence is required even for non-authorizing finite measurement."""
    if (
        os.name != "nt"
        or sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 11)
        or sys.maxsize <= 2**32
        or not sys.dont_write_bytecode
        or not __debug__
    ):
        raise _error(
            "CI Node kernels require Windows x64 CPython3.11 with bytecode disabled",
            "NODE_HOST_UNSUPPORTED",
        )
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if (
        not workspace
        or not Path(workspace).is_absolute()
        or source_root != Path(workspace).absolute() / "source"
        or attempt != _ci_attempt_coordinate(source_root, admission["platform"])
    ):
        raise _error(
            "CI physical attempt differs from authenticated coordinates", "NODE_CI_BINDING_INVALID"
        )
    _ancestors(attempt)
    for name, value in (
        ("admission", admission),
        ("source-tuple", source_tuple),
        ("descriptor", descriptor),
    ):
        if _read(attempt / "control" / (name + ".json"), limit=MAX_JSON_BYTES) != _canonical(value):
            raise _error("CI kernel control selection changed", "NODE_CI_BINDING_INVALID")
    if (
        _sha(_canonical(descriptor)) != admission["descriptor_sha256"]
        or descriptor["source_tuple_sha256"] != _sha(_canonical(source_tuple))
        or admission["platform"]["head_sha"] != source_tuple["attestation_head"]
    ):
        raise _error("CI kernel immutable input binding changed", "NODE_CI_BINDING_INVALID")


def _ci_input_binding(
    source_root: Path,
    payload_root: Path,
    attempt: Path,
    source_tuple: Mapping[str, Any],
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    from aiflow.node_ci import _ci_input_materials

    material = _ci_input_materials(source_root, payload_root, source_tuple)
    raw = _canonical(material)
    if (
        _read(attempt / "control/input-materials.json", limit=MAX_JSON_BYTES) != raw
        or _sha(raw) != admission["input_materials_sha256"]
        or _read(attempt / "control/provision.json", limit=MAX_JSON_BYTES)
        != _canonical(material["python_provision"])
        or _read(attempt / "control/provision/uv.lock", limit=MAX_JSON_BYTES)
        != _read(attempt / "artifact/inputs/uv.lock", limit=MAX_JSON_BYTES)
    ):
        raise _error(
            "CI provisioned inputs changed after exclusive admission", "NODE_MATERIALS_DRIFT"
        )
    return material


def _ci_bound_control(
    attempt: Path, admission: Mapping[str, Any], source_tuple: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    from aiflow.node_ci import node_ci_execution_contract, validate_node_ci_document

    _ancestors(attempt)
    validate_node_ci_document(dict(admission), kind="aiflow-node-ci-admission")
    validate_node_ci_document(dict(source_tuple), kind="aiflow-node-ci-attested-source")
    for name, value in (("admission", admission), ("source-tuple", source_tuple)):
        if _read(attempt / "control" / (name + ".json"), limit=MAX_JSON_BYTES) != _canonical(value):
            raise _error(
                "CI control original differs from its selected object", "NODE_CI_BINDING_INVALID"
            )
    descriptor = _json(attempt / "control/descriptor.json")
    if (
        not isinstance(descriptor, dict)
        or _sha(_canonical(descriptor)) != admission["descriptor_sha256"]
        or descriptor["source_tuple_sha256"] != _sha(_canonical(source_tuple))
        or admission["platform"]["head_sha"] != source_tuple["attestation_head"]
        or descriptor["attestation_head"] != source_tuple["attestation_head"]
    ):
        raise _error("CI admission does not bind this source tuple", "NODE_CI_BINDING_INVALID")
    contract = node_ci_execution_contract(source_tuple["binding"]["verification_level"])
    if descriptor["execution_contract_sha256"] != _sha(_canonical(contract)):
        raise _error("CI fixed execution contract is stale", "NODE_CI_BINDING_INVALID")
    return descriptor, contract


def _ci_source_snapshot(root: Path, binding: Mapping[str, Any]) -> dict[str, Any]:
    """Actual producing checkout facts, without local-original freshness claims."""
    if _git(root, "rev-parse", "HEAD").decode().strip() != binding["attestation_head"]:
        raise _error("CI source HEAD changed", "NODE_ROOT_DRIFT")
    return {
        "root": str(root),
        "inventory": _inventory(root),
        "git": _git_state(root),
        "binding": dict(binding),
    }


def _ci_context(
    source_root: Path, node_dir: Path, binding: Mapping[str, Any], manifests: Mapping[str, Any]
) -> VerificationContext:
    from aiflow.verification import NodePlanBindings

    runtime = Path(manifests["node.json"]["runtime"]["root"])
    return VerificationContext(
        source_root,
        binding["task_id"],
        binding["base_commit"],
        binding["subject_commit"],
        manifests["host-tools.json"]["python"]["path"],
        "node-ci",
        ci_run_dir=node_dir,
        node_bindings=NodePlanBindings(
            str(runtime / "node.exe"),
            str(runtime / "node_modules/npm/bin/npm-cli.js"),
            manifests["host-tools.json"]["git"]["path"],
            node_dir / "checkout",
            node_dir / "user.npmrc",
            node_dir / "global.npmrc",
            node_dir / "coverage",
            node_dir / "expected-map.json",
            node_dir / "source-manifest.json",
        ),
    )


def _ci_environment(
    node: Path, checkout: Path, run: Path, git: Path, host: Mapping[str, Any]
) -> dict[str, str]:
    system = Path(host["cmd"]["path"]).parent.parent
    result = _bound_node_environment(node, checkout, run, git, system, windows=True)
    result["TMPDIR"] = str(run / "tmp")
    result["GIT_COMMITTER_NAME"] = "aiflow-ci"
    result["GIT_COMMITTER_EMAIL"] = "aiflow-ci@invalid"
    return result


def _ci_reserve_member(projected: dict[str, int], name: str, size: int) -> None:
    name = _path(name)
    path = Path(name)
    for item in (path, *path.parents):
        if str(item) == ".":
            continue
        relative = item.as_posix()
        if relative not in projected and len(projected) >= MAX_ENTRIES:
            raise _error("CI Node copy inventory exceeds its entry budget")
        projected[relative] = max(projected.get(relative, 0), size if item == path else 0)


def _ci_node_copy_budget(node_dir: Path, additions: Mapping[str, int]) -> None:
    """Reserve cumulative physical copies before writing into the Node role."""
    projected = {row["path"]: row.get("size", 0) for row in _inventory(node_dir)["entries"]}
    for name, size in additions.items():
        _ci_reserve_member(projected, name, size)
    budget = [MAX_ENTRIES, MAX_TOTAL_BYTES]
    for size in projected.values():
        _take_budget(budget, size)


def _ci_clone_allocation(
    source_root: Path,
    original: Mapping[str, Any],
    source: Mapping[str, Any],
    dependencies: Mapping[str, Any],
    environment: Mapping[str, str],
) -> dict[str, int]:
    """Conservatively derive the fixed clone/checkout's future physical members."""
    # Keep the entire original checkout, including all .git objects/admin,
    # occupied even when clone will not copy some of its working files.
    projected = {
        "checkout/" + row["path"]: row.get("size", 0) for row in original["inventory"]["entries"]
    }

    def reserve(name: str, size: int) -> None:
        _ci_reserve_member(projected, name, size)

    for row in source["files"]:
        reserve("checkout/" + row["path"], row["size"])
    reserve("checkout/node_modules", 0)
    for row in dependencies["entries"]:
        reserve("checkout/node_modules/" + row["path"], row.get("size", 0))

    refs = _git(source_root, "for-each-ref", "--format=%(refname)").decode("utf-8").splitlines()
    if len(refs) > MAX_ENTRIES:
        raise _error("CI clone reference inventory exceeds its entry budget")
    refs = [_path(name) for name in refs]
    head = _read(source_root / ".git/HEAD", limit=MAX_JSON_BYTES).decode("utf-8").strip()
    head_ref = _path(head[5:]) if head.startswith("ref: ") else None
    if head_ref is not None and head_ref not in refs:
        raise _error("CI source symbolic HEAD differs from its frozen reference inventory")
    mapped = {
        "refs/remotes/origin/" + name.removeprefix("refs/heads/")
        if name.startswith("refs/heads/")
        else name
        for name in refs
    }
    for name in set(refs) | mapped:
        reserve("checkout/.git/" + _path(name), len(source["subject_commit"]) + 1)
    packed = len(b"# pack-refs with: peeled fully-peeled sorted \n") + sum(
        len(name.encode("utf-8")) + 2 * (len(source["subject_commit"]) + 2) for name in mapped
    )
    # Each optional peeled row includes its own 40-hex object ID. All original
    # objects/admin remain occupied above; newly generated index is separately
    # reserved at the existing binary per-file ceiling, never the JSON ceiling.
    reserve("checkout/.git/packed-refs", packed)
    reserve("checkout/.git/index", MAX_FILE_BYTES)
    reserve("checkout/.git/HEAD", max(len(head.encode("utf-8")) + 1, 41))
    reserve("checkout/.git/ORIG_HEAD", 41)
    branch = (
        head_ref.removeprefix("refs/heads/")
        if head_ref is not None and head_ref.startswith("refs/heads/")
        else None
    )
    if branch is not None:
        remote_head = "ref: refs/remotes/origin/" + branch + "\n"
        reserve("checkout/.git/refs/remotes/origin/HEAD", len(remote_head.encode("utf-8")))

    # Include every fixed clone config field, with the longer Windows boolean
    # spelling and quoted/escaped path and branch strings as conservative bounds.
    escaped_root = str(source_root).replace("\\", "\\\\").replace('"', '\\"')
    config = (
        "[core]\n\trepositoryformatversion = 0\n\tfilemode = false\n\tbare = false\n"
        "\tlogallrefupdates = true\n\tsymlinks = false\n\tignorecase = false\n"
        '[remote "origin"]\n\turl = "' + escaped_root + '"\n'
        "\tfetch = +refs/heads/*:refs/remotes/origin/*\n"
    )
    if branch is not None:
        config += (
            '[branch "' + branch + '"]\n\tremote = origin\n\tmerge = "refs/heads/' + branch + '"\n'
        )
    reserve("checkout/.git/config", len(config.encode("utf-8")))

    # clone writes HEAD and, for a symbolic source HEAD, its local branch and
    # origin/HEAD reflogs; checkout appends one HEAD record. Identity is fixed.
    identity = environment["GIT_COMMITTER_NAME"] + " <" + environment["GIT_COMMITTER_EMAIL"] + ">"
    record = len(("0" * 40 + " " + "0" * 40 + " " + identity + " ").encode("utf-8"))
    record += len(str(-(1 << 63))) + len(" +0000\t\n")
    clone_log = record + len(("clone: from " + str(source_root)).encode("utf-8"))
    checkout_log = record + len(
        ("checkout: moving from " + (head_ref or head) + " to " + source["subject_commit"]).encode(
            "utf-8"
        )
    )
    reserve("checkout/.git/logs/HEAD", clone_log + checkout_log)
    if branch is not None:
        reserve("checkout/.git/logs/refs/heads/" + branch, clone_log)
        reserve("checkout/.git/logs/refs/remotes/origin/HEAD", clone_log)
    for setup in ("setup-clone", "setup-checkout"):
        for stream in ("stdout", "stderr"):
            reserve("raw/" + setup + "/" + stream + ".raw", 1024 * 1024)
            reserve("raw/" + setup + "/" + stream + ".log", 8 * 1024 * 1024)
        reserve("raw/" + setup + "/receipt.json", MAX_JSON_BYTES)
    return projected


def _ci_public_execution(
    execution: Any, receipt: Mapping[str, Any], context: VerificationContext
) -> dict[str, Any]:
    result = _public_execution(execution, receipt, context)
    for name in ("stdout", "stderr"):
        stream = cast(dict[str, Any], result[name])
        for key in ("raw_ref", "log_ref"):
            stream[key] = str(stream[key]).replace("logs/node-ci/node/", "node/", 1)
    return result


def _ci_manifests(attempt: Path, prepared: Mapping[str, Any]) -> dict[str, Any]:
    names = ("source", "node", "npm", "dependencies", "engine", "host_tools", "preflight")
    if set(prepared["manifests"]) != set(names):
        raise _error("CI prepared material roles differ")
    result = {}
    for key, name in zip(names, MANIFEST_NAMES, strict=True):
        ref = prepared["manifests"][key]
        if ref["ref"] != "control/" + name:
            raise _error("CI manifest reference is not its fixed role")
        data = _read(attempt / ref["ref"], limit=MAX_JSON_BYTES)
        if len(data) != ref["size"] or _sha(data) != ref["sha256"]:
            raise _error("CI material original changed", "NODE_MATERIALS_DRIFT")
        result[name] = _json_bytes(data)
    return result


def prepare_ci_materials(
    source_root: Path,
    payload_root: Path,
    *,
    attempt_root: Path,
    admission: Mapping[str, Any],
    source_tuple: Mapping[str, Any],
) -> dict[str, Any]:
    """Collect actual CI inputs and version probes, writing only the claimed root."""
    descriptor, _contract = _ci_bound_control(attempt_root.absolute(), admission, source_tuple)
    return _prepare_ci_materials_kernel(
        source_root,
        payload_root,
        attempt_root=attempt_root,
        admission=admission,
        source_tuple=source_tuple,
        descriptor=descriptor,
    )


def _prepare_ci_materials_kernel(
    source_root: Path,
    payload_root: Path,
    *,
    attempt_root: Path,
    admission: Mapping[str, Any],
    source_tuple: Mapping[str, Any],
    descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    """Fixed physical kernel; direct unregistered measurement proves no authority."""
    source_root, payload_root, attempt = (
        source_root.absolute(),
        payload_root.absolute(),
        attempt_root.absolute(),
    )
    _ci_kernel_inputs(source_root, attempt, admission, source_tuple, descriptor)
    if source_root == attempt or source_root in attempt.parents or attempt in source_root.parents:
        raise _error("CI attempt and source checkout must be disjoint")
    if (attempt / "control/prepared.json").exists():
        raise _error("CI material preparation was already attempted")
    _ancestors(payload_root)
    if {path.name for path in payload_root.iterdir()} != {"node", "dependencies"} or {
        path.name for path in (payload_root / "dependencies").iterdir()
    } != {"node_modules"}:
        raise _error("CI provisioned payload has unknown roles")
    binding = source_tuple["binding"]
    before = _ci_source_snapshot(
        source_root, {**binding, "attestation_head": source_tuple["attestation_head"]}
    )
    initial = _ci_input_binding(source_root, payload_root, attempt, source_tuple, admission)
    source = initial["source"]
    if source["subject_tree"] != binding["subject_tree"]:
        raise _error("CI subject tree differs", "NODE_BINDING_STALE")
    _source_contract(source_root, source, revision=2)
    runtime = initial["runtime"]
    _node_x64(payload_root / "node/node.exe")
    if any(
        row["path"] not in {"node.exe", "npm.cmd", "node_modules", "node_modules/npm"}
        and not row["path"].startswith("node_modules/npm/")
        for row in runtime["entries"]
    ):
        raise _error("CI Node runtime contains an unowned neighbor")
    npm_root = payload_root / "node/node_modules/npm"
    npm = _json(npm_root / "package.json")
    if (
        npm.get("name") != "npm"
        or npm.get("version") != VERSIONS["npm"]
        or _read(payload_root / "node/npm.cmd") != _read(npm_root / "bin/npm.cmd")
    ):
        raise _error("CI npm package/shim differs from its fixed version")
    manifests = {
        "source.json": source,
        "node.json": {"runtime": runtime, "selected": "node.exe"},
        "npm.json": {
            "runtime_sha256": _sha(_canonical(runtime)),
            "entry": "node_modules/npm/bin/npm-cli.js",
            "shim": "npm.cmd",
            "package": npm,
        },
        "dependencies.json": initial["dependencies"],
        "engine.json": initial["engine"],
        "host-tools.json": initial["host_tools"],
        "preflight.json": {},
    }
    preflight = attempt / "preflight"
    preflight.mkdir(exist_ok=True)
    if list(preflight.iterdir()):
        raise _error("CI preflight role is already spent")
    for name in ("home", "tmp", "cache"):
        (preflight / name).mkdir()
    node = payload_root / "node/node.exe"
    environment = _ci_environment(
        node,
        payload_root / "dependencies",
        preflight,
        Path(manifests["host-tools.json"]["git"]["path"]),
        manifests["host-tools.json"],
    )
    for name, argv, expected in (
        ("node", (str(node), "--version"), "v" + VERSIONS["node"]),
        ("npm", (str(node), str(npm_root / "bin/npm-cli.js"), "--version"), VERSIONS["npm"]),
    ):
        directory = preflight / name
        receipt = _process(
            argv, cwd=payload_root, environment=environment, timeout=30, output=directory
        )
        _validate_receipt(directory, receipt, argv=argv, cwd=payload_root, environment=environment)
        if _read(directory / "stdout.raw").decode().strip() != expected:
            raise _error("CI fixed version probe failed", "NODE_PREFLIGHT_FAILED")
        manifests["preflight.json"][name] = {
            "directory": str(directory),
            "receipt": receipt,
            "expected": expected,
        }
    _ci_closed_preflight_roles(_inventory(preflight))
    for inventory in (runtime, manifests["dependencies.json"]):
        _unchanged(inventory)
    if _canonical(before) != _canonical(_ci_source_snapshot(source_root, before["binding"])):
        raise _error("CI source changed during material preparation", "NODE_ROOT_DRIFT")
    _ci_input_binding(source_root, payload_root, attempt, source_tuple, admission)
    refs = {}
    for key, name in zip(
        ("source", "node", "npm", "dependencies", "engine", "host_tools", "preflight"),
        MANIFEST_NAMES,
        strict=True,
    ):
        _write_new(attempt / "control" / name, _canonical(manifests[name]))
        refs[key] = _ci_ref(attempt / "control" / name, attempt)
    prepared = {
        "kind": "aiflow-node-ci-prepared-3.3",
        "schema_version": "1.0",
        "descriptor": _ci_ref(attempt / "control/descriptor.json", attempt),
        "source_tuple": _ci_ref(attempt / "control/source-tuple.json", attempt),
        "admission": _ci_ref(attempt / "control/admission.json", attempt),
        "platform": dict(admission["platform"]),
        "profile": dict(PROFILE_V2),
        "verification_level": binding["verification_level"],
        "execution_contract_sha256": descriptor["execution_contract_sha256"],
        "manifests": refs,
    }
    _write_new(attempt / "control/prepared.json", _canonical(prepared))
    return prepared


def execute_ci_node(
    source_root: Path,
    task_id: str,
    *,
    attempt_root: Path,
    admission: Mapping[str, Any],
    prepared: Mapping[str, Any],
    source_tuple: Mapping[str, Any],
    pairs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the unchanged fixed Node2 operations in a new CI-owned physical role."""
    descriptor, _contract = _ci_bound_control(attempt_root.absolute(), admission, source_tuple)
    return _execute_ci_node_kernel(
        source_root,
        task_id,
        attempt_root=attempt_root,
        admission=admission,
        prepared=prepared,
        source_tuple=source_tuple,
        descriptor=descriptor,
        pairs=pairs,
    )


def _execute_ci_node_kernel(
    source_root: Path,
    task_id: str,
    *,
    attempt_root: Path,
    admission: Mapping[str, Any],
    prepared: Mapping[str, Any],
    source_tuple: Mapping[str, Any],
    descriptor: Mapping[str, Any],
    pairs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The same fixed operations for production and explicitly non-authorizing proof."""
    from aiflow import installed_mutations as installed
    from aiflow.verification import parse_node_ci_plan

    source_root, attempt = source_root.absolute(), attempt_root.absolute()
    _ci_kernel_inputs(source_root, attempt, admission, source_tuple, descriptor)
    if _read(attempt / "control/prepared.json", limit=MAX_JSON_BYTES) != _canonical(prepared):
        raise _error("CI prepared original differs")
    binding = source_tuple["binding"]
    if (
        task_id != binding["task_id"]
        or prepared["verification_level"] != binding["verification_level"]
    ):
        raise _error("CI task/tier binding differs", "NODE_BINDING_STALE")
    level = binding["verification_level"]
    if (level == "V2") != (pairs is not None):
        raise _error("CI pair applicability differs", "NODE_MUTATIONS_INVALID")
    manifests = _ci_manifests(attempt, prepared)
    payload_root = Path(manifests["node.json"]["runtime"]["root"]).parent
    _ci_input_binding(source_root, payload_root, attempt, source_tuple, admission)
    pair_materials = _json_bytes(installed._materials()) if pairs is not None else None
    if pairs is not None:
        assert pair_materials is not None
        if _canonical(pair_materials["engine"]["installed"]) != _canonical(
            manifests["engine.json"]
        ) or _canonical(pair_materials["host_tools"]) != _canonical(manifests["host-tools.json"]):
            raise _error("CI Node/pair engine or host roles differ", "NODE_MUTATIONS_INVALID")
        fact = installed.validate_ci_pair_run(
            attempt_root=attempt, admission=admission, materials=pair_materials, pairs=pairs
        )
        if not fact["passed"]:
            raise _error("CI installed pairs are not current and killed", "NODE_MUTATIONS_INVALID")
    pair_snapshots = (
        [_inventory(attempt / f"pair-{index}-{role}") for index in range(5) for role in ("b", "m")]
        if pairs is not None
        else []
    )
    node_dir = attempt / "node"
    node_dir.mkdir(exist_ok=True)
    if list(node_dir.iterdir()):
        raise _error("CI Node role is already spent")
    before = _ci_source_snapshot(
        source_root, {**binding, "attestation_head": source_tuple["attestation_head"]}
    )
    for name in ("raw", "home", "tmp", "cache"):
        (node_dir / name).mkdir()
    for name in ("user.npmrc", "global.npmrc"):
        _write_new(node_dir / name, b"")
    context = _ci_context(source_root, node_dir, binding, manifests)
    roles = context.node_bindings
    assert roles is not None
    bundle = load_policy_bundle(source_root)
    plan = parse_node_ci_plan(bundle, context, level=level)
    environment = _ci_environment(
        Path(roles.node_executable),
        roles.execution_root,
        node_dir,
        Path(roles.git_executable),
        manifests["host-tools.json"],
    )
    clone_argv = (
        roles.git_executable,
        *_GIT_OPTIONS,
        "clone",
        "--no-hardlinks",
        "--no-checkout",
        "--local",
        "--",
        str(source_root),
        str(roles.execution_root),
    )
    _ci_node_copy_budget(
        node_dir,
        _ci_clone_allocation(
            source_root,
            before,
            manifests["source.json"],
            manifests["dependencies.json"],
            environment,
        ),
    )
    _unchanged(before["inventory"])
    clone = _process(
        clone_argv,
        cwd=source_root,
        environment=environment,
        timeout=30,
        output=node_dir / "raw/setup-clone",
    )
    _validate_receipt(
        node_dir / "raw/setup-clone",
        clone,
        argv=clone_argv,
        cwd=source_root,
        environment=environment,
    )
    _ci_node_copy_budget(node_dir, {})
    checkout_argv = (
        roles.git_executable,
        *_GIT_OPTIONS,
        "-c",
        "core.autocrlf=false",
        "checkout",
        "--detach",
        binding["subject_commit"],
    )
    checkout_receipt = _process(
        checkout_argv,
        cwd=roles.execution_root,
        environment=environment,
        timeout=30,
        output=node_dir / "raw/setup-checkout",
    )
    _validate_receipt(
        node_dir / "raw/setup-checkout",
        checkout_receipt,
        argv=checkout_argv,
        cwd=roles.execution_root,
        environment=environment,
    )
    if any((roles.execution_root / name).exists() for name in ("node_modules", "dist", ".runtime")):
        raise _error("CI tracked input collides with an execution output")
    _ci_node_copy_budget(
        node_dir,
        {
            "checkout/node_modules": 0,
            **{
                "checkout/node_modules/" + row["path"]: row.get("size", 0)
                for row in manifests["dependencies.json"]["entries"]
            },
        },
    )
    copied = _copy_tree(
        Path(manifests["dependencies.json"]["root"]),
        roles.execution_root / "node_modules",
        manifests["dependencies.json"],
    )
    source = manifests["source.json"]
    protected = _checkout_files(roles.execution_root, source)
    _native_ownership_applicable(roles.execution_root, source)
    _write_new(
        roles.source_manifest_file,
        _canonical(
            {
                "root": str(roles.execution_root),
                "files": [
                    {"path": row["path"], "sha256": row["sha256"]}
                    for row in source["files"]
                    if row["path"].startswith("src/local/") and row["path"].endswith(".ts")
                ],
            }
        ),
    )
    expected_dist = _dist_paths(roles.execution_root, source)
    executions = []
    coverage: dict[str, object] | None = None
    products: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    dist = build_dist = native_seal = None
    native_checked = False
    failure = None
    try:
        for execution in plan.executions:
            _unchanged(before["inventory"])
            if _canonical(_checkout_files(roles.execution_root, source)) != _canonical(protected):
                raise _error("Protected CI checkout source changed", "NODE_ROOT_DRIFT")
            for inventory in (
                copied,
                manifests["node.json"]["runtime"],
                manifests["dependencies.json"],
            ):
                _unchanged(inventory)
            if dist is not None:
                _unchanged(dist)
            if native_checked and _canonical(
                _native_ownership_inventory(roles.execution_root, source)
            ) != _canonical(native_seal):
                raise _error("CI native ownership first seal changed", "NODE_OUTPUT_INVALID")
            receipt = _process(
                execution.argv,
                cwd=execution.cwd,
                environment=environment,
                timeout=execution.timeout_seconds,
                output=node_dir / "raw" / execution.execution_id,
            )
            executions.append({"execution_id": execution.execution_id, "receipt": receipt})
            if not _successful(receipt):
                failure = "NODE_PROCESS_FAILED"
                break
            _validate_receipt(
                node_dir / "raw" / execution.execution_id,
                receipt,
                argv=execution.argv,
                cwd=execution.cwd,
                environment=environment,
            )
            if "node_check" in execution.check_ids:
                native_seal = _native_ownership_inventory(roles.execution_root, source)
                native_checked = True
            if "node_build" in execution.check_ids:
                build_dist = dist = _dist(roles.execution_root, expected_dist)
            elif execution.argv in {
                check.argv
                for check in plan.checks
                if check.check_id in {"node_check", "ts_coverage"}
            }:
                rebuilt = _dist(roles.execution_root, expected_dist)
                if build_dist is None or _canonical(_content(rebuilt)) != _canonical(
                    _content(build_dist)
                ):
                    raise _error("CI rebuilt output content changed", "NODE_OUTPUT_INVALID")
                dist = rebuilt
        if failure is None:
            if not native_checked or _canonical(
                _native_ownership_inventory(roles.execution_root, source)
            ) != _canonical(native_seal):
                raise _error("CI final native ownership output differs from first seal")
            if level != "V0":
                _changed, _deleted, diff = _changed_lines(
                    source_root, binding["base_commit"], binding["subject_commit"]
                )
                _write_new(node_dir / "source.diff", diff)
                coverage = _coverage(
                    roles.execution_root,
                    node_dir,
                    source,
                    binding["base_commit"],
                    binding["subject_commit"],
                    source_root,
                    revision=2,
                )
            if level == "V2":
                products = _products(node_dir, source, roles.execution_root)
            if dist is None or build_dist is None:
                raise _error("CI fixed build output is missing")
            fixtures = _fixtures(roles.execution_root, node_dir / "tmp", source, revision=2)
            if _canonical(fixtures.get("native_ownership")) != _canonical(native_seal):
                raise _error("CI native fixture differs from first seal")
            _output_check(roles.execution_root, source, dist, copied, fixtures, revision=2)
            outputs = {"build_dist": build_dist, "dist": dist, "fixtures": fixtures}
            _unchanged(before["inventory"])
            if _canonical(_engine()) != _canonical(manifests["engine.json"]) or _canonical(
                _host_tools()
            ) != _canonical(manifests["host-tools.json"]):
                raise _error("CI engine/host materials changed", "NODE_MATERIALS_DRIFT")
            _ci_input_binding(source_root, payload_root, attempt, source_tuple, admission)
    except (AiflowError, OSError, ValueError, TypeError, KeyError) as error:
        failure = error.code if isinstance(error, AiflowError) else "NODE_EXECUTION_INVALID"
    if pairs is not None:
        assert pair_materials is not None
        for inventory in pair_snapshots:
            _unchanged(inventory)
        fact = installed.validate_ci_pair_run(
            attempt_root=attempt, admission=admission, materials=pair_materials, pairs=pairs
        )
        if not fact["passed"]:
            failure = "NODE_MUTATIONS_INVALID"
    output_document: dict[str, Any] = outputs or {}
    output_document["node_inventory"] = _node_inventory(node_dir, level, plan)
    run = {
        "kind": "aiflow-node-ci-run-3.3",
        "schema_version": "1.0",
        "prepared": _ci_ref(attempt / "control/prepared.json", attempt),
        "descriptor_sha256": _sha(_canonical(descriptor)),
        "platform": dict(admission["platform"]),
        "inputs": {
            "source": source,
            "runtime": manifests["node.json"]["runtime"],
            "dependencies": copied,
            "prepared_dependencies": manifests["dependencies.json"],
            "engine": manifests["engine.json"],
            "host_tools": manifests["host-tools.json"],
        },
        "environment": environment,
        "roots": {
            "original": before,
            "checkout": protected,
            "clone": clone,
            "checkout_receipt": checkout_receipt,
        },
        "executions": executions,
        "coverage": _coverage_originals(node_dir, coverage) if coverage is not None else None,
        "product_tests": products,
        "installed_mutation": pairs,
        "outputs": output_document,
        "failure": failure,
    }
    data = _canonical(run)
    if len(data) > MAX_JSON_BYTES:
        raise _error("CI Node run exceeds its JSON budget")
    _write_new(node_dir / "run.json", data)
    return run


def _ci_original(package_root: Path, role: str, relative: str) -> bytes:
    """Open only the new package's ordinary member, never a producing path."""
    _path(role)
    _path(relative)
    return _read(package_root / "originals" / role / relative)


def _ci_transport_ref(package_root: Path, reference: Mapping[str, Any]) -> Any:
    if set(reference) != {"ref", "size", "sha256"}:
        raise _error("CI original reference has unknown fields")
    role, separator, relative = _path(reference["ref"]).partition("/")
    if (
        not separator
        or type(reference["size"]) is not int
        or not 0 < reference["size"] <= MAX_JSON_BYTES
    ):
        raise _error("CI original reference lacks its role")
    raw = _ci_original(package_root, role, relative)
    if (
        type(reference["size"]) is not int
        or len(raw) != reference["size"]
        or _sha(raw) != reference["sha256"]
    ):
        raise _error("CI transported original differs", "NODE_MATERIALS_DRIFT")
    document = _json_bytes(raw)
    if _canonical(document) != raw:
        raise _error("CI transported JSON is noncanonical")
    return document


def _ci_verify_role(package_root: Path, role: str, manifest: Mapping[str, Any]) -> None:
    if (
        set(manifest) != {"id", "root", "identity", "entries", "total_bytes"}
        or manifest["id"] != role
    ):
        raise _error("CI role manifest has an invalid closed shape")
    identity_fields = {
        "device",
        "inode",
        "nlink",
        "size",
        "mtime_ns",
        "ctime_ns",
        "mode",
        "attributes",
    }
    if not isinstance(manifest["root"], str) or not Path(manifest["root"]).is_absolute():
        raise _error("CI producing role root is not an absolute coordinate")
    entries = manifest["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise _error("CI role inventory exceeds its entry budget")
    if any(not isinstance(row, dict) for row in entries):
        raise _error("CI role inventory has a nonobject member")
    identities = [manifest["identity"], *(row.get("identity") for row in entries)]
    for identity in identities:
        if (
            not isinstance(identity, dict)
            or set(identity) != identity_fields
            or any(type(value) is not int or value < 0 for value in identity.values())
        ):
            raise _error("CI producing identity facts are malformed")
    paths = []
    total = 0
    for row in entries:
        path = _path(row["path"])
        paths.append(path)
        if row["kind"] not in {"file", "directory"} or set(row) != {"path", "kind", "identity"} | (
            {"size", "sha256"} if row["kind"] == "file" else set()
        ):
            raise _error("CI role member has an invalid closed shape")
        if row["kind"] == "file":
            data = _ci_original(package_root, role, path)
            if (
                type(row["size"]) is not int
                or len(data) != row["size"]
                or _sha(data) != row["sha256"]
            ):
                raise _error("CI original member bytes changed", "NODE_MATERIALS_DRIFT")
            total += len(data)
        else:
            _safe_info(package_root / "originals" / role / path, directory=True)
    if paths != sorted(set(paths), key=lambda value: value.encode("utf8")) or len(
        set(path.casefold() for path in paths)
    ) != len(paths):
        raise _error("CI original paths are duplicate or aliased")
    if (
        type(manifest["total_bytes"]) is not int
        or total != manifest["total_bytes"]
        or total > MAX_TOTAL_BYTES
    ):
        raise _error("CI original inventory byte budget differs")
    actual = _inventory(package_root / "originals" / role)
    if _canonical(_content(actual)) != _canonical(_content(manifest)):
        raise _error("CI transported role has missing or extra members")


def _ci_inventory_in_role(inventory: Mapping[str, Any], role: Mapping[str, Any]) -> None:
    """Compare original identity facts to their sealed role, not to this host."""
    root, full_root = Path(inventory["root"]), Path(role["root"])
    if not root.is_relative_to(full_root):
        raise _error("CI inventory points outside its declared producing role")
    prefix = root.relative_to(full_root).as_posix()
    prefix = "" if prefix == "." else prefix + "/"
    selected = []
    for row in role["entries"]:
        if row["path"].startswith(prefix) and row["path"] != prefix.rstrip("/"):
            selected.append({**row, "path": row["path"][len(prefix) :]})
    if (
        _canonical(selected) != _canonical(inventory["entries"])
        or sum(row.get("size", 0) for row in selected) != inventory["total_bytes"]
    ):
        raise _error("CI inventory differs from complete retained originals")
    expected_identity = (
        role["identity"]
        if not prefix
        else next(
            (row["identity"] for row in role["entries"] if row["path"] == prefix.rstrip("/")), None
        )
    )
    if _canonical(expected_identity) != _canonical(inventory["identity"]):
        raise _error("CI producing inventory identity differs from its retained role")


def _ci_retained_receipt(
    package_root: Path,
    role: str,
    relative: str,
    receipt: Mapping[str, Any],
    *,
    argv: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
) -> None:
    raw = _ci_original(package_root, role, relative + "/receipt.json")
    parsed = _json_bytes(raw)
    if _canonical(parsed) != raw:
        raise _error("CI process receipt is noncanonical")
    validate_receipt_originals(
        receipt,
        receipt=parsed,
        streams={
            name: _ci_original(package_root, role, relative + "/" + name + ".raw")
            for name in ("stdout", "stderr")
        },
        logs={
            name: _ci_original(package_root, role, relative + "/" + name + ".log")
            for name in ("stdout", "stderr")
        },
        argv=argv,
        cwd=cwd,
        environment=environment,
    )


def _ci_native_originals(
    package_root: Path,
    source: Mapping[str, Any],
    fixtures: Mapping[str, Any],
    node_role: Mapping[str, Any],
) -> None:
    rows = {row["path"]: row for row in source["files"] if row["path"] in NATIVE_OWNERSHIP_INPUTS}
    if rows and set(rows) != set(NATIVE_OWNERSHIP_INPUTS):
        raise _error("CI native ownership source applicability is partial")
    for name, row in rows.items():
        if (
            row["sha256"] != NATIVE_OWNERSHIP_INPUTS[name]
            or _sha(_ci_original(package_root, "node", "checkout/" + name))
            != NATIVE_OWNERSHIP_INPUTS[name]
        ):
            raise _error("CI native ownership source differs from reviewed bytes")
    native = fixtures.get("native_ownership")
    if bool(rows) != (native is not None):
        raise _error("CI native ownership output applicability differs")
    if native is None:
        return
    _ci_inventory_in_role(native, node_role)
    source_sha = NATIVE_OWNERSHIP_INPUTS["scripts/windows-owned-launcher.cs"]
    executable = "own-" + source_sha + ".exe"
    if {row["path"] for row in native["entries"]} != {executable, executable + ".json"} or any(
        row["kind"] != "file" for row in native["entries"]
    ):
        raise _error("CI native ownership cache is not the exact two files")
    prefix = "checkout/" + NATIVE_OWNERSHIP_DIRECTORY + "/"
    binary = _ci_original(package_root, "node", prefix + executable)
    sidecar = _ci_original(package_root, "node", prefix + executable + ".json")
    expected = {"sourceHash": source_sha, "executableHash": _sha(binary)}
    if (
        not binary
        or sidecar != json.dumps(expected, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    ):
        raise _error("CI native ownership sidecar source/content wire differs")


def _ci_engine_host_originals(
    package_root: Path, manifests: Mapping[str, Any], role_manifests: Mapping[str, Any]
) -> Path:
    host = manifests["host-tools.json"]
    system = Path(host["cmd"]["path"]).parent.parent
    for name, row in host.items():
        if row is None:
            continue
        data = _ci_original(package_root, "host", name)
        if len(data) != row["size"] or _sha(data) != row["sha256"]:
            raise _error("CI retained host slot differs from bound original bytes")
    engine = manifests["engine.json"]
    engine_root = Path(role_manifests["engine"]["root"])
    files = [file for distribution in engine["distributions"] for file in distribution["files"]]
    files.extend(engine["startup"]["files"])
    if engine["startup"].get("pyvenv_configuration") is not None:
        files.append(engine["startup"]["pyvenv_configuration"])
    for row in files:
        raw = row["path"]
        if not isinstance(raw, str) or not Path(raw).is_absolute():
            raise _error("CI installed engine file path is not absolute")
        path = Path(os.path.normpath(raw))
        if not path.is_relative_to(engine_root):
            raise _error("CI installed engine file leaves its ordinary prefix")
        data = _ci_original(package_root, "engine", path.relative_to(engine_root).as_posix())
        if len(data) != row["size"] or _sha(data) != row["sha256"]:
            raise _error("CI installed engine original bytes changed")
    return system


def _ci_runtime_originals(
    package_root: Path, manifests: Mapping[str, Any], role: Mapping[str, Any]
) -> None:
    node = manifests["node.json"]
    npm = manifests["npm.json"]
    if (
        set(node) != {"runtime", "selected"}
        or node["selected"] != "node.exe"
        or set(npm) != {"runtime_sha256", "entry", "shim", "package"}
    ):
        raise _error("CI Node/npm material roles differ")
    inventory = node["runtime"]
    if (
        npm["runtime_sha256"] != _sha(_canonical(inventory))
        or npm["entry"] != "node_modules/npm/bin/npm-cli.js"
        or npm["shim"] != "npm.cmd"
    ):
        raise _error("CI npm selection differs from its fixed role")
    base = (
        package_root / "originals/runtime" / Path(inventory["root"]).relative_to(Path(role["root"]))
    )
    _node_x64(base / "node.exe")
    package = _json(base / "node_modules/npm/package.json")
    if (
        package != npm["package"]
        or package.get("name") != "npm"
        or package.get("version") != VERSIONS["npm"]
        or _read(base / "npm.cmd") != _read(base / "node_modules/npm/bin/npm.cmd")
    ):
        raise _error("CI transported npm/shim content differs")
    if any(
        row["path"] not in {"node.exe", "npm.cmd", "node_modules", "node_modules/npm"}
        and not row["path"].startswith("node_modules/npm/")
        for row in inventory["entries"]
    ):
        raise _error("CI Node runtime contains an undeclared neighbor")


def _ci_closed_node_roles(manifest: Mapping[str, Any], level: str, plan: Any) -> None:
    allowed = {
        "raw",
        "home",
        "tmp",
        "cache",
        "user.npmrc",
        "global.npmrc",
        "checkout",
        "source-manifest.json",
        "run.json",
    }
    if level != "V0":
        allowed.update(
            {"coverage", "expected-map.json", "source.diff", "domain-materials", "vitest.json"}
        )
    paths = {row["path"] for row in manifest["entries"]}
    if {path.split("/", 1)[0] for path in paths} != allowed:
        # Optional domain materials are retained whenever the fixed helper produced them.
        top = {path.split("/", 1)[0] for path in paths}
        if not top.issubset(allowed) or not (allowed - {"domain-materials"}).issubset(top):
            raise _error("CI Node output has missing or foreign top-level roles")
    executions = {"setup-clone", "setup-checkout", *(item.execution_id for item in plan.executions)}
    observed = {path.split("/")[1] for path in paths if path.startswith("raw/")}
    if observed != executions:
        raise _error("CI Node raw execution membership differs from fixed plan")
    for execution in executions:
        children = {
            path.removeprefix("raw/" + execution + "/")
            for path in paths
            if path.startswith("raw/" + execution + "/")
        }
        if children != {"receipt.json", "stdout.raw", "stderr.raw", "stdout.log", "stderr.log"}:
            raise _error("CI raw process has missing or additional originals")


def _ci_closed_preflight_roles(manifest: Mapping[str, Any]) -> None:
    paths = {row["path"] for row in manifest["entries"]}
    if {path.split("/", 1)[0] for path in paths} != {"node", "npm", "home", "tmp", "cache"}:
        raise _error("CI preflight has foreign or missing output roles")
    for name in ("node", "npm"):
        children = {path.removeprefix(name + "/") for path in paths if path.startswith(name + "/")}
        if children != {"receipt.json", "stdout.raw", "stderr.raw", "stdout.log", "stderr.log"}:
            raise _error("CI preflight has foreign or missing raw process originals")


def replay_ci_node(
    *,
    package_root: Path,
    prepared: Mapping[str, Any],
    run: Mapping[str, Any],
    role_manifests: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute fresh-CI proof from transported bytes; original paths are data."""
    from aiflow.node_ci import node_ci_execution_contract, validate_node_ci_document

    try:
        contract = node_ci_execution_contract(prepared["verification_level"])
        for key, kind in (
            ("source_tuple", "aiflow-node-ci-attested-source"),
            ("descriptor", "aiflow-node-ci-descriptor"),
            ("admission", "aiflow-node-ci-admission"),
        ):
            validate_node_ci_document(_ci_transport_ref(package_root, prepared[key]), kind=kind)
        return _replay_ci_node_kernel(
            package_root=package_root,
            prepared=prepared,
            run=run,
            role_manifests=role_manifests,
            execution_contract=contract,
        )
    except (AiflowError, ValueError, TypeError, KeyError) as error:
        return {
            "passed": False,
            "checks": [],
            "node_binding": None,
            "reason_codes": [
                error.code if isinstance(error, AiflowError) else "NODE_EVIDENCE_INVALID"
            ],
        }


def _replay_ci_node_kernel(
    *,
    package_root: Path,
    prepared: Mapping[str, Any],
    run: Mapping[str, Any],
    role_manifests: Mapping[str, Any],
    execution_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Byte kernel only: content validity cannot authenticate platform/LOCAL proof."""
    from aiflow import installed_mutations as installed
    from aiflow.evidence import _node_evidence_plan
    from aiflow.node_ci import _python_provision, validate_node_ci_document
    from aiflow.verification import _bound_node_plan

    try:
        validate_node_ci_document(dict(prepared), kind="aiflow-node-ci-prepared-3.3")
        validate_node_ci_document(dict(run), kind="aiflow-node-ci-run-3.3")
        for key, relative in (
            ("source_tuple", "source-tuple"),
            ("descriptor", "descriptor"),
            ("admission", "admission"),
        ):
            if prepared[key]["ref"] != "control/" + relative + ".json":
                raise _error("CI control selection is not its fixed path")
        if run["prepared"]["ref"] != "control/prepared.json":
            raise _error("CI preparation selection is not its fixed path")
        source_tuple = _ci_transport_ref(package_root, prepared["source_tuple"])
        descriptor = _ci_transport_ref(package_root, prepared["descriptor"])
        admission = _ci_transport_ref(package_root, prepared["admission"])
        if _ci_transport_ref(package_root, run["prepared"]) != prepared or _ci_original(
            package_root, "node", "run.json"
        ) != _canonical(run):
            raise _error("CI public selections do not identify retained originals")
        binding = source_tuple["binding"]
        level = binding["verification_level"]
        contract = execution_contract
        if (
            _sha(_canonical(descriptor)) != run["descriptor_sha256"]
            or admission["descriptor_sha256"] != run["descriptor_sha256"]
            or descriptor["source_tuple_sha256"] != _sha(_canonical(source_tuple))
            or descriptor["execution_contract_sha256"] != _sha(_canonical(contract))
            or prepared["execution_contract_sha256"] != descriptor["execution_contract_sha256"]
            or prepared["verification_level"] != level
            or prepared["profile"] != PROFILE_V2
            or _canonical(run["platform"]) != _canonical(admission["platform"])
            or _canonical(prepared["platform"]) != _canonical(admission["platform"])
            or admission["platform"]["head_sha"] != source_tuple["attestation_head"]
            or descriptor["attestation_head"] != source_tuple["attestation_head"]
        ):
            raise _error(
                "CI source/descriptor/admission/platform bindings differ", "NODE_CI_BINDING_INVALID"
            )
        required = {
            "source",
            "artifact",
            "engine",
            "runtime",
            "dependencies",
            "host",
            "preflight",
            "control",
            "node",
        }
        if level == "V2":
            required.update(f"pair-{index}-{role}" for index in range(5) for role in ("b", "m"))
        if set(role_manifests) != required:
            raise _error("CI complete tier roles differ")
        for role, manifest in role_manifests.items():
            _ci_verify_role(package_root, role, manifest)
        names = ("source", "node", "npm", "dependencies", "engine", "host_tools", "preflight")
        if set(prepared["manifests"]) != set(names):
            raise _error("CI prepared manifest roles differ")
        manifests = {
            name: _ci_transport_ref(package_root, prepared["manifests"][key])
            for key, name in zip(names, MANIFEST_NAMES, strict=True)
        }
        for key, name in zip(names, MANIFEST_NAMES, strict=True):
            if prepared["manifests"][key]["ref"] != "control/" + name:
                raise _error("CI prepared manifest path differs")
        initial_raw = _ci_original(package_root, "control", "input-materials.json")
        initial = _json_bytes(initial_raw)
        if (
            _canonical(initial) != initial_raw
            or _sha(initial_raw) != admission["input_materials_sha256"]
            or set(initial)
            != {
                "source",
                "runtime",
                "dependencies",
                "engine",
                "host_tools",
                "pair_materials",
                "engine_artifact",
                "python_provision",
            }
        ):
            raise _error("CI provisioned input digest differs from admission")
        provision = _python_provision(
            source_tuple, package_root / "originals/artifact", initial["engine"]
        )
        if (
            initial["python_provision"] != provision
            or _ci_original(package_root, "control", "provision.json") != _canonical(provision)
            or _ci_original(package_root, "control", "provision/uv.lock")
            != _ci_original(package_root, "artifact", "inputs/uv.lock")
        ):
            raise _error("CI transported Python lock/provision association differs")
        for key, manifest_name in (
            ("source", "source.json"),
            ("dependencies", "dependencies.json"),
            ("engine", "engine.json"),
            ("host_tools", "host-tools.json"),
        ):
            if initial[key] != manifests[manifest_name]:
                raise _error("CI prepared material differs from admitted inputs")
        if (
            initial["runtime"] != manifests["node.json"]["runtime"]
            or initial["engine_artifact"] != source_tuple["engine_artifact"]
        ):
            raise _error("CI selected runtime/artifact differs from admitted inputs")
        inputs = run["inputs"]
        if set(inputs) != {
            "source",
            "runtime",
            "dependencies",
            "prepared_dependencies",
            "engine",
            "host_tools",
        }:
            raise _error("CI Node input roles differ")
        for name, manifest in (
            ("source", "source.json"),
            ("prepared_dependencies", "dependencies.json"),
            ("engine", "engine.json"),
            ("host_tools", "host-tools.json"),
        ):
            if _canonical(inputs[name]) != _canonical(manifests[manifest]):
                raise _error("CI Node input differs from preparation")
        if _canonical(inputs["runtime"]) != _canonical(manifests["node.json"]["runtime"]):
            raise _error("CI Node runtime differs from preparation")
        roots = run["roots"]
        if set(roots) != {"original", "checkout", "clone", "checkout_receipt"} or set(
            roots["original"]
        ) != {"root", "inventory", "git", "binding"}:
            raise _error("CI Node root roles differ")
        original_root = Path(roots["original"]["root"])
        node_dir = Path(role_manifests["node"]["root"])
        expected_attempt = _ci_attempt_coordinate(
            Path(role_manifests["source"]["root"]), admission["platform"]
        )
        if (
            original_root != Path(role_manifests["source"]["root"])
            or node_dir != expected_attempt / "node"
            or Path(role_manifests["control"]["root"]) != expected_attempt / "control"
            or Path(role_manifests["preflight"]["root"]) != expected_attempt / "preflight"
        ):
            raise _error(
                "CI original roots were retagged to another attempt", "NODE_CI_BINDING_INVALID"
            )
        context = _ci_context(original_root, node_dir, binding, manifests)
        roles = context.node_bindings
        assert roles is not None
        if roots["original"]["binding"] != {
            **binding,
            "attestation_head": source_tuple["attestation_head"],
        }:
            raise _error("CI producing source snapshot binds a different subject")
        if (
            roots["original"]["git"]["head"] != source_tuple["attestation_head"]
            or roots["checkout"]["git"]["head"] != binding["subject_commit"]
            or roots["checkout"]["git"]["tree"] != binding["subject_tree"]
        ):
            raise _error("CI source/checkout Git coordinates differ")
        if roots["original"]["git"]["git_directory"] != str(original_root / ".git") or roots[
            "checkout"
        ]["git"]["git_directory"] != str(node_dir / "checkout/.git"):
            raise _error("CI Git administration points outside its owned clone")
        if (
            _sha(_ci_original(package_root, "source", ".git/index"))
            != roots["original"]["git"]["index_sha256"]
            or _sha(_ci_original(package_root, "node", "checkout/.git/index"))
            != roots["checkout"]["git"]["index_sha256"]
        ):
            raise _error("CI retained Git index differs")
        _ci_inventory_in_role(roots["original"]["inventory"], role_manifests["source"])
        for inventory, role in (
            (inputs["runtime"], "runtime"),
            (inputs["prepared_dependencies"], "dependencies"),
            (inputs["dependencies"], "node"),
            (roots["checkout"]["administration"], "node"),
        ):
            _ci_inventory_in_role(inventory, role_manifests[role])
        _ci_runtime_originals(package_root, manifests, role_manifests["runtime"])
        if Path(
            inputs["dependencies"]["root"]
        ) != roles.execution_root / "node_modules" or _canonical(
            _content(inputs["dependencies"])
        ) != _canonical(_content(inputs["prepared_dependencies"])):
            raise _error("CI copied dependencies differ from their selected bytes")
        source = manifests["source.json"]
        if (
            source["subject_commit"] != binding["subject_commit"]
            or source["subject_tree"] != binding["subject_tree"]
        ):
            raise _error("CI source tree binding differs")
        if roots["checkout"]["root"] != str(roles.execution_root) or len(
            roots["checkout"]["files"]
        ) != len(source["files"]):
            raise _error("CI checkout source membership differs")
        node_rows = {row["path"]: row for row in role_manifests["node"]["entries"]}
        for source_row, observed in zip(source["files"], roots["checkout"]["files"], strict=True):
            row = node_rows["checkout/" + source_row["path"]]
            data = _ci_original(package_root, "node", "checkout/" + source_row["path"])
            if (
                observed
                != {
                    "path": source_row["path"],
                    "size": source_row["size"],
                    "sha256": source_row["sha256"],
                    "identity": row["identity"],
                }
                or len(data) != source_row["size"]
                or _sha(data) != source_row["sha256"]
                or hashlib.sha1(
                    b"blob " + str(len(data)).encode("ascii") + b"\0" + data
                ).hexdigest()
                != source_row["blob"]
            ):
                raise _error("CI checkout bytes/identity differ from the subject")
        if (
            _sha(_ci_original(package_root, "node", "checkout/vitest.config.ts"))
            != NODE_V2_CONFIG_SHA256
        ):
            raise _error("CI Vitest configuration differs from the fixed revision2 bytes")
        _ci_engine_host_originals(package_root, manifests, role_manifests)
        expected_environment = _ci_environment(
            Path(roles.node_executable),
            roles.execution_root,
            node_dir,
            Path(roles.git_executable),
            manifests["host-tools.json"],
        )
        if _canonical(run["environment"]) != _canonical(expected_environment):
            raise _error("CI fixed Node environment differs")
        for name in ("user.npmrc", "global.npmrc"):
            if _ci_original(package_root, "node", name) != b"":
                raise _error("CI owned npm configuration is not empty")
        old_preflight = Path(role_manifests["preflight"]["root"])
        _ci_closed_preflight_roles(role_manifests["preflight"])
        runtime_root = Path(manifests["node.json"]["runtime"]["root"])
        payload_root = runtime_root.parent
        probe_environment = _ci_environment(
            runtime_root / "node.exe",
            payload_root / "dependencies",
            old_preflight,
            Path(roles.git_executable),
            manifests["host-tools.json"],
        )
        for name, argv, expected in (
            ("node", (str(runtime_root / "node.exe"), "--version"), "v" + VERSIONS["node"]),
            (
                "npm",
                (
                    str(runtime_root / "node.exe"),
                    str(runtime_root / "node_modules/npm/bin/npm-cli.js"),
                    "--version",
                ),
                VERSIONS["npm"],
            ),
        ):
            probe = manifests["preflight.json"][name]
            if (
                probe["directory"] != str(old_preflight / name)
                or probe["expected"] != expected
                or probe["receipt"]["timeout_seconds"] != 30
            ):
                raise _error("CI fixed preflight coordinates/version differ")
            _ci_retained_receipt(
                package_root,
                "preflight",
                name,
                probe["receipt"],
                argv=argv,
                cwd=payload_root,
                environment=probe_environment,
            )
            if (
                _ci_original(package_root, "preflight", name + "/stdout.raw").decode().strip()
                != expected
            ):
                raise _error("CI preflight version stream differs")
        source_mapping = {
            "root": str(roles.execution_root),
            "files": [
                {"path": row["path"], "sha256": row["sha256"]}
                for row in source["files"]
                if row["path"].startswith("src/local/") and row["path"].endswith(".ts")
            ],
        }
        if _ci_original(package_root, "node", "source-manifest.json") != _canonical(source_mapping):
            raise _error("CI source map input differs from full subject inventory")
        plan = _bound_node_plan(context, level, revision2=True, run_dir=node_dir)
        _ci_closed_node_roles(role_manifests["node"], level, plan)
        if node_execution_contract(plan, context) != _node_evidence_plan(level, revision=2):
            raise _error("CI fixed plan differs from the public tier contract")
        clone_argv = (
            roles.git_executable,
            *_GIT_OPTIONS,
            "clone",
            "--no-hardlinks",
            "--no-checkout",
            "--local",
            "--",
            str(original_root),
            str(roles.execution_root),
        )
        checkout_argv = (
            roles.git_executable,
            *_GIT_OPTIONS,
            "-c",
            "core.autocrlf=false",
            "checkout",
            "--detach",
            binding["subject_commit"],
        )
        _ci_retained_receipt(
            package_root,
            "node",
            "raw/setup-clone",
            roots["clone"],
            argv=clone_argv,
            cwd=original_root,
            environment=expected_environment,
        )
        _ci_retained_receipt(
            package_root,
            "node",
            "raw/setup-checkout",
            roots["checkout_receipt"],
            argv=checkout_argv,
            cwd=roles.execution_root,
            environment=expected_environment,
        )
        public = []
        actual = run["executions"]
        if not isinstance(actual, list) or len(actual) != len(plan.executions):
            raise _error(
                "CI Node did not execute every required process", "NODE_EVIDENCE_NOT_PASSED"
            )
        for execution, original in zip(plan.executions, actual, strict=True):
            if (
                set(original) != {"execution_id", "receipt"}
                or original["execution_id"] != execution.execution_id
                or original["receipt"]["timeout_seconds"] != execution.timeout_seconds
            ):
                raise _error("CI Node execution order/deadline differs")
            _ci_retained_receipt(
                package_root,
                "node",
                "raw/" + execution.execution_id,
                original["receipt"],
                argv=execution.argv,
                cwd=execution.cwd,
                environment=expected_environment,
            )
            public.append(_ci_public_execution(execution, original["receipt"], context))
        outputs = run["outputs"]
        if set(outputs) != {"build_dist", "dist", "fixtures", "node_inventory"}:
            raise _error("CI successful output roles are incomplete")
        expected_inventory = [
            row for row in _content(role_manifests["node"]) if row["path"] != "run.json"
        ]
        if outputs["node_inventory"] != expected_inventory:
            raise _error("CI complete Node content/membership changed")
        for inventory in (outputs["dist"], *outputs["fixtures"].values()):
            _ci_inventory_in_role(inventory, role_manifests["node"])
        if outputs["build_dist"]["root"] != outputs["dist"]["root"] or _content(
            outputs["build_dist"]
        ) != _content(outputs["dist"]):
            raise _error("CI rebuilt dist content differs")
        _ci_native_originals(package_root, source, outputs["fixtures"], role_manifests["node"])
        transported_checkout = package_root / "originals/node/checkout"
        transported_dependencies = (
            package_root
            / "originals/dependencies"
            / Path(inputs["prepared_dependencies"]["root"]).relative_to(
                Path(role_manifests["dependencies"]["root"])
            )
        )
        lock = _json(transported_checkout / "package-lock.json")
        checked_dependencies = _dependencies(transported_dependencies, lock, revision=2)
        if _content(checked_dependencies) != _content(inputs["prepared_dependencies"]):
            raise _error("CI transported dependencies differ from the locked closure")
        physical_dist = _dist(transported_checkout, _dist_paths(transported_checkout, source))
        physical_copied = _inventory(transported_checkout / "node_modules")
        physical_fixtures = _fixtures(
            transported_checkout, package_root / "originals/node/tmp", source, revision=2
        )
        if (
            _content(physical_dist) != _content(outputs["dist"])
            or _content(physical_copied) != _content(inputs["dependencies"])
            or set(physical_fixtures) != set(outputs["fixtures"])
        ):
            raise _error("CI transported output or fixture roles differ")
        for key in physical_fixtures:
            fixture = physical_fixtures[key]
            if not isinstance(fixture, Mapping) or _content(fixture) != _content(
                outputs["fixtures"][key]
            ):
                raise _error("CI transported fixture content differs")
        _output_check(
            transported_checkout,
            source,
            physical_dist,
            physical_copied,
            physical_fixtures,
            revision=2,
        )
        coverage = None
        if level != "V0":
            sources = {
                row["path"]: _ci_original(package_root, "node", "checkout/" + row["path"])
                for row in source["files"]
                if row["path"].startswith("src/local/") and row["path"].endswith(".ts")
            }
            coverage = _coverage_from_originals(
                roles.execution_root,
                sources,
                _ci_original(package_root, "node", "coverage/coverage-final.json"),
                _ci_original(package_root, "node", "coverage/coverage-summary.json"),
                _json_bytes(_ci_original(package_root, "node", "expected-map.json")),
                _ci_original(package_root, "node", "source.diff"),
            )
            originals = [
                {"ref": name, "size": len(data), "sha256": _sha(data)}
                for name in (
                    "coverage/coverage-final.json",
                    "coverage/coverage-summary.json",
                    "expected-map.json",
                    "source.diff",
                    "source-manifest.json",
                )
                for data in [_ci_original(package_root, "node", name)]
            ]
            if run["coverage"] != {"originals": originals, "result": coverage}:
                raise _error("CI coverage originals/projection differ")
        elif run["coverage"] is not None:
            raise _error("CI V0 cannot acquire coverage projection")
        products: dict[str, Any] | None = None
        pair_facts: dict[str, Any] | None = None
        if level == "V2":
            materials = _json_bytes(_ci_original(package_root, "control", "pair-materials.json"))
            if materials != initial["pair_materials"]:
                raise _error("CI pair materials differ from admitted inputs")
            if (
                materials["engine"]["installed"] != manifests["engine.json"]
                or materials["host_tools"] != manifests["host-tools.json"]
            ):
                raise _error("CI pair and Node installed materials differ")
            pair_facts = installed.replay_ci_pairs(
                package_root=package_root,
                admission=admission,
                materials=materials,
                pairs=run["installed_mutation"],
                role_manifests=role_manifests,
            )
            if not pair_facts["passed"]:
                raise _error("CI fresh installed mutations failed", "NODE_MUTATIONS_INVALID")
            raw_product = _ci_original(package_root, "node", "vitest.json")
            tests = {
                row["path"]: _ci_original(package_root, "node", "checkout/" + row["path"])
                for row in source["files"]
                if row["path"].startswith("tests/local/") and row["path"].endswith(".test.ts")
            }
            product_result = validate_node_product_tests(
                _json_bytes(raw_product),
                execution_root=roles.execution_root,
                tracked_tests=tests,
                expected_coverage=_json_bytes(
                    _ci_original(package_root, "node", "coverage/coverage-final.json")
                ),
            )
            products = {
                "report": {
                    "ref": "vitest.json",
                    "size": len(raw_product),
                    "sha256": _sha(raw_product),
                },
                "expected_tests": [
                    {"file": path, "sha256": _sha(data)} for path, data in sorted(tests.items())
                ],
                "result": product_result,
            }
            if run["product_tests"] != products:
                raise _error("CI product original/projection differs")
        elif (
            run["product_tests"] is not None
            or run["installed_mutation"] is not None
            or initial["pair_materials"] is not None
        ):
            raise _error("CI lower tier cannot acquire V2 facts")
        checks = _checks(
            plan, context, public, coverage, run["failure"], products=products, installed=pair_facts
        )
        passed = run["failure"] is None and all(row["status"] == "passed" for row in checks)
        node_binding = {
            "profile": dict(PROFILE_V2),
            "subject_tree": binding["subject_tree"],
            "prepared": dict(run["prepared"]),
            "run": {
                "ref": "node/run.json",
                "size": len(_canonical(run)),
                "sha256": _sha(_canonical(run)),
            },
            "materials_sha256": _sha(_canonical(inputs)),
            "semantic_contract_sha256": SEMANTIC_CONTRACT_V2_SHA256,
            "execution_contract_sha256": prepared["execution_contract_sha256"],
            "environment_sha256": _sha(_canonical(expected_environment)),
            "coverage": coverage,
        }
        if products is not None:
            node_binding["product_tests"] = {
                "report": {**products["report"], "ref": "node/vitest.json"},
                **{
                    key: products["result"][key]
                    for key in ("inventory_sha256", "acceptance", "integration")
                },
            }
        return {
            "passed": passed,
            "checks": checks,
            "node_binding": node_binding,
            "reason_codes": [] if passed else ["NODE_EVIDENCE_NOT_PASSED"],
        }
    except (AiflowError, OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        return {
            "passed": False,
            "checks": [],
            "node_binding": None,
            "reason_codes": [
                error.code if isinstance(error, AiflowError) else "NODE_EVIDENCE_INVALID"
            ],
        }
