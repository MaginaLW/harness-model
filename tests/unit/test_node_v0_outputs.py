"""Synthetic path and state-delta checks for an owned Node checkout.

The caller supplies exact output paths derived from bound source/configuration.
No target package extension or real-checkout ignored-directory exemption exists.
Dynamic owned test roots still need orchestration-level inventory tests.
"""

from __future__ import annotations

# ruff: noqa: E402 -- Source-absence guard must precede candidate-only imports.
import ctypes
import stat
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

# Baseline-only absence is not a functional pass; malformed or stale imports fail.
ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file() and (parent / "src/aiflow/__init__.py").is_file()
)
NODE_SOURCE = ROOT / "src/aiflow/node_verification.py"
try:
    NODE_SOURCE_INFO = NODE_SOURCE.lstat()
except FileNotFoundError:
    pytest.skip(
        "Node implementation is absent: test-preparation baseline only, not feature PASS",
        allow_module_level=True,
    )
if (
    not stat.S_ISREG(NODE_SOURCE_INFO.st_mode)
    or getattr(NODE_SOURCE_INFO, "st_file_attributes", 0)
    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    or not NODE_SOURCE.resolve().is_relative_to(ROOT.resolve())
):
    raise ImportError("Node source is not a regular checkout module")

import aiflow
import aiflow.node_verification as node_checkout

if (
    aiflow.__file__ is None
    or Path(aiflow.__file__).resolve() != (ROOT / "src/aiflow/__init__.py").resolve()
    or node_checkout.__file__ is None
    or Path(node_checkout.__file__).resolve() != NODE_SOURCE.resolve()
):
    raise ImportError("Node contracts were not imported from this tested checkout")

node = node_checkout
from aiflow.errors import AiflowError, ContractError

MODULE_SOURCE = NODE_SOURCE
if node.__file__ is None or Path(node.__file__).resolve() != MODULE_SOURCE.resolve():
    raise ImportError("Node output validator was not loaded from the tested source tree")

HASH_A = "a" * 64
HASH_B = "b" * 64
PROTECTED = ("node_modules/pkg/index.js", "package.json", "src/app.ts")


def item(path: str, status: str, digest: str = HASH_A) -> dict[str, str]:
    return {"path": path, "git_status": status, "sha256": digest}


def before_state() -> list[dict[str, str]]:
    return [
        item("node_modules/pkg/index.js", "ignored"),
        item("package.json", "tracked"),
        item("src/app.ts", "tracked"),
    ]


def test_output_rejects_too_many_output_entries() -> None:
    outputs = [f"dist/{index:05}.js" for index in range(65_537)]
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta([], [], outputs, protected_paths=(), reserved_paths=())


@pytest.mark.parametrize(
    "field", ["outputs", "before", "after", "protected_paths", "reserved_paths"]
)
def test_each_oversized_inventory_is_rejected_before_traversal(field: str) -> None:
    class NoTraversal(list):
        def __iter__(self):
            pytest.fail("oversized inventory was traversed instead of rejected")

    entry = item("dist/out.js", "ignored") if field in {"before", "after"} else "dist/out.js"
    oversized = NoTraversal([entry] * 65_537)
    arguments = {
        "before": [],
        "after": [],
        "outputs": (),
        "protected_paths": (),
        "reserved_paths": (),
    }
    arguments[field] = oversized
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta(
            arguments["before"],
            arguments["after"],
            arguments["outputs"],
            protected_paths=arguments["protected_paths"],
            reserved_paths=arguments["reserved_paths"],
        )


@pytest.mark.parametrize("kind", ["utf8_bytes", "segments"])
def test_output_path_limits_at_the_boundary(kind: str) -> None:
    if kind == "utf8_bytes":
        valid = "/".join(["é" * 102] * 5)
        invalid = valid + "é"
        assert len(valid.encode("utf-8")) == 1024
    else:
        valid = "/".join(["a"] * 64)
        invalid = valid + "/a"
    node.validate_node_v0_output_delta(
        [], [item(valid, "ignored")], (valid,), protected_paths=(), reserved_paths=()
    )
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta(
            [], [], (invalid,), protected_paths=(), reserved_paths=()
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "dist/a.js",
        [1],
        ["dist/b.js", "dist/a.js"],
        ["dist/a.js", "dist/a.js"],
        ["dist/A.js", "dist/a.js"],
        ["dist/a", "dist/a/file.js"],
    ],
)
def test_output_rejects_invalid_collection_order_or_aliases(value: object) -> None:
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta([], [], value, protected_paths=(), reserved_paths=())


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/dist/a.js",
        "../outside.js",
        "dist/../outside.js",
        "dist/./a.js",
        "dist//a.js",
        "C:/outside.js",
        "dist\\a.js",
        "dist/*.js",
        "dist/file?.js",
        ".git",
        ".git/config",
        ".GIT/config",
        "dist/NUL.txt",
        "dist/CON/a.js",
        "dist/LPT1.js",
        "dist/file. ",
    ],
)
def test_output_rejects_unsafe_or_nonportable_paths(value: str) -> None:
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta([], [], (value,), protected_paths=(), reserved_paths=())


@pytest.mark.parametrize("existing", [False, True])
def test_delta_accepts_only_exact_declared_file_creation_or_change(existing: bool) -> None:
    before = before_state()
    old_output = item("dist/out.js", "ignored")
    if existing:
        before.insert(0, old_output)
    after = deepcopy(before)
    if existing:
        after[0]["sha256"] = HASH_B
    else:
        after.insert(0, item("dist/out.js", "ignored", HASH_B))
    assert (
        node.validate_node_v0_output_delta(
            before, after, ("dist/out.js",), protected_paths=PROTECTED, reserved_paths=()
        )
        is None
    )


@pytest.mark.parametrize(
    "change",
    [
        "undeclared",
        "descendant",
        "delete_output",
        "delete_tracked",
        "tracked_content",
        "installed_content",
        "status",
        "extra_entry",
        "duplicate",
        "unordered",
        "unknown_status",
    ],
)
def test_delta_rejects_unknown_deletions_or_protected_changes(change: str) -> None:
    before = [item("dist/out.js", "ignored"), *before_state()]
    after = deepcopy(before)
    if change == "undeclared":
        after.insert(0, item("dist/other.js", "ignored"))
    elif change == "descendant":
        after.insert(1, item("dist/out.js/child", "ignored"))
    elif change == "delete_output":
        after.pop(0)
    elif change == "delete_tracked":
        after.pop(2)
    elif change == "tracked_content":
        after[2]["sha256"] = HASH_B
    elif change == "installed_content":
        after[1]["sha256"] = HASH_B
    elif change == "status":
        after[0]["git_status"] = "untracked"
    elif change == "extra_entry":
        after[0]["extra"] = "unexpected"
    elif change == "duplicate":
        after.insert(1, deepcopy(after[0]))
    elif change == "unordered":
        after.reverse()
    else:
        after[0]["git_status"] = "unknown"
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta(
            before, after, ("dist/out.js",), protected_paths=PROTECTED, reserved_paths=()
        )


@pytest.mark.parametrize(
    "output", ["package.json", "src", "src/app.ts/child", "NODE_MODULES/pkg/index.js"]
)
def test_delta_rejects_protected_path_or_ancestor_collisions(output: str) -> None:
    before = before_state()
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta(
            before, deepcopy(before), (output,), protected_paths=PROTECTED, reserved_paths=()
        )


def test_delta_allows_excluded_reserved_audit_file_to_be_absent() -> None:
    before = before_state()
    after = [item("dist/out.js", "ignored", HASH_B), *deepcopy(before)]
    assert (
        node.validate_node_v0_output_delta(
            before,
            after,
            ("dist/out.js",),
            protected_paths=PROTECTED,
            reserved_paths=("logs/run/stdout",),
        )
        is None
    )


@pytest.mark.parametrize("output", ["logs", "logs/run/stdout", "logs/run/stdout/child"])
def test_delta_rejects_reserved_audit_path_or_ancestor_collisions(output: str) -> None:
    before = before_state()
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta(
            before,
            deepcopy(before),
            (output,),
            protected_paths=PROTECTED,
            reserved_paths=("logs/run/stdout",),
        )


def test_delta_requires_protected_files_to_exist_on_both_sides() -> None:
    before = before_state()
    missing = [entry for entry in before if entry["path"] != "src/app.ts"]
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta(
            missing, deepcopy(missing), (), protected_paths=PROTECTED, reserved_paths=()
        )


@pytest.mark.parametrize("output", [".git", ".git/config", ".GIT/config"])
def test_delta_rejects_git_metadata_even_without_reserved_paths(output: str) -> None:
    with pytest.raises(AiflowError):
        node.validate_node_v0_output_delta([], [], (output,), protected_paths=(), reserved_paths=())


def test_reserved_paths_are_explicit_and_non_git_outputs_remain_valid() -> None:
    output = ".github/report.txt"
    with pytest.raises(TypeError):
        node.validate_node_v0_output_delta([], [], (), protected_paths=())
    assert (
        node.validate_node_v0_output_delta(
            [], [item(output, "untracked")], (output,), protected_paths=(), reserved_paths=()
        )
        is None
    )


# These tests exercise private original-reading boundaries, never mocked product PASS.
import json
import os
import subprocess
import sys

import aiflow.node_execution as runtime


def test_material_inventory_detects_independent_copy_and_later_replacement(tmp_path: Path) -> None:
    original = tmp_path / "materials"
    (original / "nested/empty").mkdir(parents=True)
    (original / "nested/tool.js").write_bytes(b"export default 1;\n")
    inventory = runtime._inventory(original)
    runtime._unchanged(inventory)
    copied = runtime._copy_tree(original, tmp_path / "copy", inventory)
    assert runtime._content(copied) == runtime._content(inventory)
    file = original / "nested/tool.js"
    replacement = original / "replacement"
    replacement.write_bytes(file.read_bytes())
    os.replace(replacement, file)
    with pytest.raises(AiflowError, match="changed"):
        runtime._unchanged(inventory)


@pytest.mark.parametrize("bound", ["entries", "file", "total"])
def test_material_limits_reject_before_unbounded_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: str
) -> None:
    directory = tmp_path / "materials"
    directory.mkdir()
    (directory / "one").write_bytes(b"a" * 4)
    (directory / "two").write_bytes(b"b" * 4)
    name, maximum = {
        "entries": ("MAX_ENTRIES", 1),
        "file": ("MAX_FILE_BYTES", 3),
        "total": ("MAX_TOTAL_BYTES", 7),
    }[bound]
    monkeypatch.setattr(runtime, name, maximum)
    with pytest.raises(AiflowError):
        runtime._inventory(directory)


def test_material_hardlinks_are_rejected_even_with_matching_content(tmp_path: Path) -> None:
    first, second = tmp_path / "one", tmp_path / "two"
    first.write_bytes(b"same bytes")
    os.link(first, second)
    with pytest.raises(AiflowError):
        runtime._read(first)
    with pytest.raises(AiflowError):
        runtime._inventory(tmp_path)


def test_missing_prepared_original_raises_a_compact_domain_error(tmp_path: Path) -> None:
    with pytest.raises(AiflowError) as caught:
        runtime._load_prepared(tmp_path, "TASK-0001", "0" * 64, {})
    assert caught.value.code == "NODE_MATERIALS_INVALID"


def test_os_hardlink_exception_is_bound_to_the_exact_fixed_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "_windows_root", lambda: tmp_path)
    cmd = tmp_path / "System32/cmd.exe"
    cmd.parent.mkdir()
    cmd.write_bytes(b"controlled host-role fixture; never executed")
    os.link(cmd, tmp_path / "alias.exe")
    assert runtime._read(cmd, os_role="cmd") == cmd.read_bytes()
    with pytest.raises(AiflowError):
        runtime._read(cmd)
    with pytest.raises(AiflowError):
        runtime._read(tmp_path / "alias.exe", os_role="cmd")
    with pytest.raises(AiflowError):
        runtime._read(cmd, os_role="git")
    with pytest.raises(AiflowError):
        runtime._safe_info(tmp_path / "System32", directory=True, os_role="cmd")


@pytest.mark.skipif(os.name != "nt", reason="Real API-derived Windows host roles")
def test_actual_os_role_binding_ignores_caller_systemroot(monkeypatch: pytest.MonkeyPatch) -> None:
    root = runtime._windows_root()
    monkeypatch.setenv("SystemRoot", str(root / "not-the-system-root"))
    assert runtime._windows_root() == root
    paths = runtime._os_tool_paths()
    assert set(paths) == set(runtime._OS_TOOL_PATHS) | {
        role + "_config" for role in runtime._OS_TOOL_PATHS
    }
    for role in runtime._OS_TOOL_PATHS:
        info = runtime._safe_info(paths[role], os_role=role)
        assert type(info.st_nlink) is int and info.st_nlink > 0
        assert runtime._read(paths[role], os_role=role)


@pytest.mark.parametrize("result", ["absolute", "zero", "full_buffer", "oversized", "relative"])
def test_windows_root_uses_api_result_and_rejects_invalid_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: str
) -> None:
    # Change only this module's platform binding; pathlib keeps the real host OS.
    monkeypatch.setattr(runtime, "os", SimpleNamespace(**(vars(os) | {"name": "nt"})))
    root = tmp_path / "Windows-系统"
    root.mkdir()
    monkeypatch.setenv("SystemRoot", str(tmp_path / "caller-controlled"))
    directory = "relative/Windows" if result == "relative" else str(root)
    calls = []

    def get_windows_directory(buffer, size):
        calls.append(size)
        buffer.value = directory
        return {
            "zero": 0,
            "full_buffer": size,
            "oversized": size + 1,
        }.get(result, len(directory))

    def load_kernel(name, *, use_last_error):
        assert name == "kernel32"
        assert use_last_error is True
        return SimpleNamespace(GetWindowsDirectoryW=get_windows_directory)

    monkeypatch.setattr(ctypes, "WinDLL", load_kernel, raising=False)
    if result == "absolute":
        assert runtime._windows_root() == root
    else:
        with pytest.raises(AiflowError) as caught:
            runtime._windows_root()
        assert caught.value.code == "NODE_HOST_UNSUPPORTED"
    from ctypes import wintypes

    assert calls == [32768]
    assert get_windows_directory.argtypes == (wintypes.LPWSTR, wintypes.UINT)
    assert get_windows_directory.restype is wintypes.UINT


@pytest.mark.parametrize("entry", ["cmd/git.exe", "mingw64/bin/git.exe"])
def test_fixed_git_catalog_closes_wrapper_backend_transport_and_shell(
    tmp_path: Path, entry: str
) -> None:
    roles = runtime._git_role_paths(tmp_path / entry)
    assert roles == {
        "git": tmp_path / entry,
        "git_backend": tmp_path / "mingw64/bin/git.exe",
        "git_upload_pack": tmp_path / "mingw64/bin/git-upload-pack.exe",
        "git_sh": tmp_path / "usr/bin/sh.exe",
    }


@pytest.mark.parametrize("entry", ["tools/git.exe", "cmd/not-git.exe", "git.exe"])
def test_unknown_git_install_layout_cannot_supply_extra_tool_roles(
    tmp_path: Path, entry: str
) -> None:
    with pytest.raises(AiflowError):
        runtime._git_role_paths(tmp_path / entry)


@pytest.mark.parametrize(
    "mutation",
    [
        "git",
        "git_backend",
        "git_upload_pack",
        "git_sh",
        "config_added",
        "config_removed",
        "git_hardlink",
    ],
)
def test_host_tool_catalog_rebinds_every_git_image_and_os_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    monkeypatch.setattr(runtime, "os", SimpleNamespace(**(vars(os) | {"name": "nt"})))
    python = tmp_path / "python.exe"
    python.write_bytes(b"controlled Python fixture; never executed")
    monkeypatch.setattr(runtime, "sys", SimpleNamespace(executable=str(python)))
    git = tmp_path / "Git/cmd/git.exe"
    roles = runtime._git_role_paths(git)
    for role, path in roles.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("controlled tool " + role).encode())
    windows = tmp_path / "Windows"
    monkeypatch.setattr(runtime, "_windows_root", lambda: windows)
    for relative in runtime._OS_TOOL_PATHS.values():
        path = windows / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"controlled fixed OS-role fixture")
    config = windows / "System32/WindowsPowerShell/v1.0/powershell.exe.config"
    if mutation == "config_removed":
        config.write_bytes(b"controlled configuration")
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: str(git))
    before = runtime._host_tools()
    if mutation == "config_added":
        config.write_bytes(b"new configuration")
    elif mutation == "config_removed":
        config.unlink()
    elif mutation == "git_hardlink":
        os.link(roles["git_upload_pack"], tmp_path / "alias.exe")
        with pytest.raises(AiflowError):
            runtime._host_tools()
        return
    else:
        path = roles[mutation]
        replacement = path.with_name("replacement.exe")
        replacement.write_bytes(path.read_bytes())
        os.replace(replacement, path)
    assert runtime._canonical(runtime._host_tools()) != runtime._canonical(before)


def test_host_tool_catalog_rejects_missing_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime, "os", SimpleNamespace(**(vars(os) | {"name": "nt"})))
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: None)
    with pytest.raises(AiflowError, match="Bound Git is unavailable"):
        runtime._host_tools()


@pytest.mark.parametrize(
    "data", [b'{"x":1,"x":1}', b'{"x":NaN}', b'{"x":1e9999}', b'"\\ud800"', b'"\xff"', b"["]
)
def test_material_json_rejects_ambiguous_or_invalid_bytes(data: bytes) -> None:
    with pytest.raises(AiflowError):
        runtime._json_bytes(data)


@pytest.mark.parametrize("variant", ["arm64", "x86", "signature", "offset", "truncated"])
def test_node_materials_reject_non_x64_or_invalid_pe(tmp_path: Path, variant: str) -> None:
    executable = bytearray(128)
    executable[:2] = b"MZ"
    executable[60:64] = (64).to_bytes(4, "little")
    executable[64:68] = b"PE\0\0"
    executable[68:70] = (0x8664).to_bytes(2, "little")
    executable[88:90] = (0x20B).to_bytes(2, "little")
    path = tmp_path / "node.exe"
    path.write_bytes(executable)
    runtime._node_x64(path)
    if variant in {"arm64", "x86"}:
        executable[68:70] = (0xAA64 if variant == "arm64" else 0x14C).to_bytes(2, "little")
    elif variant == "signature":
        executable[64:68] = b"fake"
    elif variant == "offset":
        executable[60:64] = (999).to_bytes(4, "little")
    else:
        executable = executable[:60]
    path.write_bytes(executable)
    with pytest.raises(AiflowError):
        runtime._node_x64(path)


def test_private_reads_enforce_limit_and_no_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "original"
    runtime._write_new(path, b"1234")
    assert runtime._read(path, limit=4) == b"1234"
    with pytest.raises(AiflowError):
        runtime._read(path, limit=3)
    with pytest.raises(FileExistsError):
        runtime._write_new(path, b"overwritten")
    assert path.read_bytes() == b"1234"


@pytest.mark.parametrize("suffix", [".cmd", ".exe", ".ps1"])
def test_windows_path_execute_bit_inference_does_not_change_file_identity(
    tmp_path: Path, suffix: str
) -> None:
    path = tmp_path / ("ordinary" + suffix)
    path.write_bytes(b"ordinary immutable material")
    assert runtime._read(path) == b"ordinary immutable material"


def test_combined_material_limit_is_shared_across_independent_roots(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "one").write_bytes(b"abcd")
    (second / "two").write_bytes(b"efgh")
    budget = [2, 7]
    runtime._inventory(first, budget=budget)
    with pytest.raises(AiflowError, match="Combined"):
        runtime._inventory(second, budget=budget)


@pytest.mark.parametrize("kind", ["command", "directory"])
def test_dependency_shim_without_locked_bin_owner_is_rejected(tmp_path: Path, kind: str) -> None:
    (tmp_path / ".bin").mkdir()
    if kind == "command":
        (tmp_path / ".bin/unowned.cmd").write_bytes(b"@echo off\r\necho unowned\r\n")
    else:
        (tmp_path / ".bin/unowned").mkdir()
    with pytest.raises(AiflowError):
        runtime._dependency_shims(tmp_path, set(), runtime._inventory(tmp_path))


def test_coverage_pure_calculation_cannot_pass_after_fixed_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(node, "monotonic", iter((0.0, 31.0)).__next__)
    path = "src/local/example.ts"
    with pytest.raises(AiflowError) as caught:
        node.validate_node_line_coverage(
            {path: {}},
            tracked_sources={path: b"export const x = 1;\n"},
            changed_lines={},
            deleted_sources=(),
            expected_executable_lines={path: [1]},
        )
    assert caught.value.code == "NODE_COVERAGE_TIMEOUT"


@pytest.mark.parametrize(
    "counter,value", [("f", True), ("f", 1.0), ("b", [False]), ("b", [0.0]), ("b", 1)]
)
def test_unused_auxiliary_hits_still_require_exact_integer_counts(
    counter: str, value: object
) -> None:
    path = "src/local/example.ts"
    report = {
        "path": path,
        "statementMap": {
            "0": {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": 19}}
        },
        "s": {"0": 1},
        counter: {"0": value},
    }
    with pytest.raises(AiflowError):
        node.validate_node_line_coverage(
            {path: report},
            tracked_sources={path: b"export const x = 1;\n"},
            expected_executable_lines={path: [1]},
            changed_lines={},
            deleted_sources=(),
        )


def _prepared_originals(root: Path, mutation: str = "") -> tuple[str, dict]:
    task = root / ".ai/tasks/TASK-0001/logs"
    payload = task / "node-payload/preparation"
    (payload / "node").mkdir(parents=True)
    (payload / "dependencies/node_modules").mkdir(parents=True)
    binding = {"task_id": "TASK-0001", "profile": runtime.PROFILE}
    originals = {name: runtime._canonical({"role": name}) for name in runtime.MANIFEST_NAMES}
    refs = [
        {"name": name, "size": len(data), "sha256": runtime._sha(data)}
        for name, data in originals.items()
    ]
    document = {
        "schema_version": "1.0",
        "kind": "aiflow-node-prepared-3.1",
        "binding": binding,
        "payload": {"path": str(payload), "identity": runtime._identity(payload.lstat())},
        "manifests": refs,
        "versions": deepcopy(runtime.VERSIONS),
        "semantic_contract_sha256": runtime.SEMANTIC_CONTRACT_SHA256,
    }
    if mutation == "unknown_field":
        document["unknown"] = True
    elif mutation == "old_version":
        document["kind"] = "aiflow-node-prepared-3.0"
    elif mutation == "version":
        document["versions"]["node"] = "0.0.0"
    elif mutation == "semantic":
        document["semantic_contract_sha256"] = "0" * 64
    elif mutation == "manifest_count":
        refs.pop()
    elif mutation == "manifest_name":
        refs[0]["name"] = "outside.json"
    elif mutation == "manifest_bool":
        refs[0]["size"] = True
    elif mutation == "manifest_float":
        refs[0]["size"] = float(refs[0]["size"])
    elif mutation == "manifest_digest":
        refs[0]["sha256"] = "0" * 64
    elif mutation == "payload_parent":
        document["payload"]["path"] = str(root)
    elif mutation == "payload_identity":
        document["payload"]["identity"]["inode"] = False
    data = runtime._canonical(document) + (b"\n" if mutation == "noncanonical" else b"")
    digest = runtime._sha(data)
    directory = task / "node-prepared" / digest
    directory.mkdir(parents=True)
    for name, value in {**originals, "prepared.json": data}.items():
        (directory / name).write_bytes(value)
    if mutation == "extra_original":
        (directory / "unknown.json").write_bytes(b"{}")
    if mutation == "mutated_original":
        (directory / "source.json").write_bytes(b"{}")
    return digest, binding


def test_prepared_loader_binds_exact_canonical_selector_and_all_seven_originals(
    tmp_path: Path,
) -> None:
    digest, binding = _prepared_originals(tmp_path)
    prepared, originals = runtime._load_prepared(tmp_path, "TASK-0001", digest, binding)
    assert prepared["binding"] == binding
    assert tuple(originals) == runtime.MANIFEST_NAMES


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_field",
        "old_version",
        "version",
        "semantic",
        "manifest_count",
        "manifest_name",
        "manifest_bool",
        "manifest_float",
        "manifest_digest",
        "payload_parent",
        "payload_identity",
        "noncanonical",
        "extra_original",
        "mutated_original",
    ],
)
def test_prepared_loader_rejects_rehashed_but_invalid_selections(
    tmp_path: Path, mutation: str
) -> None:
    digest, binding = _prepared_originals(tmp_path, mutation)
    with pytest.raises(AiflowError):
        runtime._load_prepared(tmp_path, "TASK-0001", digest, binding)


@pytest.mark.parametrize("selector", ["A" * 64, "0" * 63, "../outside", ""])
def test_prepared_selector_is_a_closed_lowercase_sha256(tmp_path: Path, selector: str) -> None:
    with pytest.raises(AiflowError):
        runtime._load_prepared(tmp_path, "TASK-0001", selector, {})


@pytest.mark.parametrize("source_root", ["src", "src/local"])
def test_build_output_derives_four_exact_files_for_each_bound_source(
    tmp_path: Path, source_root: str
) -> None:
    config = {
        "compilerOptions": {
            "outDir": "dist",
            "rootDir": source_root,
            "sourceMap": True,
            "declaration": True,
            "declarationMap": True,
        }
    }
    (tmp_path / "tsconfig.json").write_text(json.dumps(config), encoding="utf-8")
    source = {"files": [{"path": "src/local/example.ts"}]}
    outputs = runtime._dist_paths(tmp_path, source)
    expected_stem = "dist/local/example" if source_root == "src" else "dist/example"
    assert outputs == tuple(
        sorted(expected_stem + suffix for suffix in (".js", ".js.map", ".d.ts", ".d.ts.map"))
    )
    for output in outputs:
        path = tmp_path / output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"owned output")
    runtime._dist(tmp_path, outputs)
    (tmp_path / "dist/unexpected.js").write_bytes(b"unknown")
    with pytest.raises(AiflowError):
        runtime._dist(tmp_path, outputs)


@pytest.mark.parametrize(
    "change",
    [
        "extends",
        "rootDir",
        "declaration",
        "declarationMap",
        "sourceMap",
        "noEmit",
        "emitDeclarationOnly",
    ],
)
def test_build_configuration_must_have_a_complete_derivable_output_set(
    tmp_path: Path, change: str
) -> None:
    config = {
        "compilerOptions": {
            "outDir": "dist",
            "rootDir": "src",
            "sourceMap": True,
            "declaration": True,
            "declarationMap": True,
        }
    }
    if change == "extends":
        config["extends"] = "outside.json"
    elif change == "rootDir":
        config["compilerOptions"][change] = "unknown"
    else:
        config["compilerOptions"][change] = change in {"noEmit", "emitDeclarationOnly"}
    (tmp_path / "tsconfig.json").write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(AiflowError):
        runtime._dist_paths(tmp_path, {"files": []})


@pytest.mark.skipif(os.name != "nt", reason="Real Windows ownership receipt")
def test_original_receipt_replays_real_process_and_rejects_stream_tampering(tmp_path: Path) -> None:
    directory = tmp_path / "process"
    environment = {"SystemRoot": os.environ["SystemRoot"]}
    argv = (sys.executable, "-I", "-B", "-c", "print('token=private-value')")
    receipt = runtime._process(
        argv, cwd=tmp_path, environment=environment, timeout=30, output=directory
    )
    runtime._validate_receipt(directory, receipt, argv=argv, cwd=tmp_path, environment=environment)
    assert b"private-value" not in (directory / "stdout.log").read_bytes()
    (directory / "stdout.raw").write_bytes(b"forged output")
    with pytest.raises(AiflowError):
        runtime._validate_receipt(directory, receipt)


@pytest.mark.parametrize("mutation", ["bool_size", "float_time", "argv", "cwd", "env", "receipt"])
@pytest.mark.skipif(os.name != "nt", reason="Real Windows ownership receipt")
def test_receipt_rejects_typed_or_role_rebinding(tmp_path: Path, mutation: str) -> None:
    directory = tmp_path / "process"
    argv = (sys.executable, "-I", "-B", "-c", "pass")
    environment = {"SystemRoot": os.environ["SystemRoot"]}
    receipt = runtime._process(
        argv, cwd=tmp_path, environment=environment, timeout=30, output=directory
    )
    changed = deepcopy(receipt)
    if mutation == "bool_size":
        changed["stdout_size"] = False
    elif mutation == "float_time":
        changed["duration_ms"] = float(changed["duration_ms"])
    elif mutation == "argv":
        changed["argv"] = ["unbound"]
    elif mutation == "cwd":
        changed["cwd"] = str(tmp_path / "other")
    elif mutation == "env":
        changed["environment_sha256"] = "0" * 64
    else:
        changed["receipt"]["stdout_eof"] = False
    (directory / "receipt.json").write_bytes(runtime._canonical(changed))
    with pytest.raises(AiflowError):
        runtime._validate_receipt(
            directory, changed, argv=argv, cwd=tmp_path, environment=environment
        )


def test_source_checkout_cannot_claim_ordinary_wheel_installation() -> None:
    with pytest.raises(AiflowError) as caught:
        runtime._engine()
    assert caught.value.code == "NODE_ENGINE_NOT_INSTALLED"


def _git_fixture(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments), cwd=root, capture_output=True, text=True, check=True, timeout=30
    )
    return result.stdout.strip()


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_git_state_uses_one_strict_query_before_reading_its_index(tmp_path, monkeypatch, newline):
    directory = tmp_path / "git"
    head, tree = "a" * 40, "b" * 40
    calls, reads, ancestors = [], [], []

    def git(root, *arguments):
        calls.append((root, arguments))
        return (newline.join((str(directory), head, tree)) + newline).encode()

    def read(path):
        reads.append(path)
        return b"bound index bytes"

    monkeypatch.setattr(runtime, "_git", git)
    monkeypatch.setattr(runtime, "_read", read)
    monkeypatch.setattr(runtime, "_ancestors", ancestors.append)
    assert runtime._git_state(tmp_path) == {
        "head": head,
        "tree": tree,
        "index_sha256": runtime._sha(b"bound index bytes"),
        "git_directory": str(directory),
    }
    assert calls == [(tmp_path, ("rev-parse", "--absolute-git-dir", "HEAD", "HEAD^{tree}"))]
    assert ancestors == [directory]
    assert reads == [directory / "index"]


@pytest.mark.parametrize(
    "fault", ["missing", "extra", "blank", "relative", "head", "tree", "uppercase", "encoding"]
)
def test_git_state_rejects_malformed_query_before_any_private_read(tmp_path, monkeypatch, fault):
    fields = [str(tmp_path / "git"), "a" * 40, "b" * 40]
    if fault == "missing":
        fields.pop()
    elif fault == "extra":
        fields.append("unrecognized")
    elif fault == "blank":
        fields.append("")
    elif fault == "relative":
        fields[0] = "relative/git"
    elif fault == "head":
        fields[1] = "a" * 39
    elif fault == "tree":
        fields[2] = "not-a-tree"
    elif fault == "uppercase":
        fields[1] = "A" * 40
    raw = ("\n".join(fields) + "\n").encode()
    if fault == "encoding":
        raw = b"\xff" + raw

    def forbidden(*args, **kwargs):
        pytest.fail("Malformed Git facts reached a private path")

    monkeypatch.setattr(runtime, "_git", lambda *_: raw)
    monkeypatch.setattr(runtime, "_ancestors", forbidden)
    monkeypatch.setattr(runtime, "_read", forbidden)
    with pytest.raises(AiflowError) as caught:
        runtime._git_state(tmp_path)
    assert caught.value.code == "NODE_GIT_INVALID"


@pytest.fixture
def original_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from types import SimpleNamespace

    import aiflow.task_service

    _git_fixture(tmp_path, "init", "--quiet")
    _git_fixture(tmp_path, "config", "user.name", "Synthetic Test")
    _git_fixture(tmp_path, "config", "user.email", "synthetic@example.invalid")
    _git_fixture(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "protected.txt").write_bytes(b"protected\n")
    (tmp_path / ".gitignore").write_bytes(b".ai/\n")
    _git_fixture(tmp_path, "add", ".")
    _git_fixture(tmp_path, "commit", "--quiet", "-m", "Synthetic baseline")
    task = tmp_path / ".ai/tasks/TASK-0001"
    task.mkdir(parents=True)
    (task / "approvals.json").write_bytes(b"[]")
    (tmp_path / "untracked").mkdir()
    (tmp_path / ".ai/private").mkdir()
    (tmp_path / ".ai/private/note").write_bytes(b"first")
    record = SimpleNamespace(task={"task_id": "TASK-0001"}, events=[])
    monkeypatch.setattr(aiflow.task_service, "read_task_record_strict", lambda *_: record)
    return tmp_path


@pytest.mark.parametrize("mutation", ["nested", "ignored_new", "ignored_same_length"])
def test_original_root_rejects_unknown_nested_or_ignored_changes(
    original_root: Path, mutation: str
) -> None:
    before = runtime._root_snapshot(original_root, "TASK-0001")
    if mutation == "nested":
        (original_root / "untracked/new.txt").write_bytes(b"unknown")
    elif mutation == "ignored_new":
        (original_root / ".ai/private/new.txt").write_bytes(b"unknown")
    else:
        path = original_root / ".ai/private/note"
        info = path.stat()
        path.write_bytes(b"other")
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(original_root, "TASK-0001", before)
    assert caught.value.code == "NODE_ROOT_DRIFT"


def test_fixed_environment_disables_explicit_node_compile_cache(tmp_path: Path) -> None:
    git = tmp_path / "git/cmd/git.exe"
    environment = runtime._environment(tmp_path / "node/node.exe", tmp_path, tmp_path, git)
    assert environment["NODE_DISABLE_COMPILE_CACHE"] == "1"


def test_original_root_metadata_never_reads_unknown_private_contents(
    original_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = runtime._read
    private = original_root / ".ai/private/note"

    def read(path: Path, **options):
        assert path != private, "unknown original-root bytes must remain private"
        return original(path, **options)

    monkeypatch.setattr(runtime, "_read", read)
    before = runtime._root_snapshot(original_root, "TASK-0001")
    runtime._check_root(original_root, "TASK-0001", before)
    assert any(row["path"] == str(private) for row in before["metadata"])


@pytest.mark.parametrize("refresh", ["git_status", "identical_atomic_index"])
def test_original_root_accepts_identical_index_refresh_but_rejects_leftover_lock(
    original_root: Path, refresh: str
) -> None:
    from aiflow.git_context import _run_git

    before = runtime._root_snapshot(original_root, "TASK-0001")
    if refresh == "git_status":
        _run_git(
            original_root,
            ("status", "--porcelain=v1", "--untracked-files=all"),
            failure_code="GIT_STATUS_FAILED",
        )
    else:
        index = original_root / ".git/index"
        replacement = original_root / ".git/index.observed-refresh"
        replacement.write_bytes(index.read_bytes())
        replacement.replace(index)
    assert runtime._git_state(original_root) == before["git"]
    runtime._check_root(original_root, "TASK-0001", before)
    (original_root / ".git/index.lock").write_bytes(b"unowned active lock")
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(original_root, "TASK-0001", before)
    assert caught.value.code == "NODE_ROOT_DRIFT"


def _registered_review(original_root: Path):
    import aiflow.task_service

    record = aiflow.task_service.read_task_record_strict(original_root, "TASK-0001")
    task = original_root / ".ai/tasks/TASK-0001"
    (task / "reviews").mkdir()
    (task / "review-contexts").mkdir()
    context = {
        "schema_version": "1.0",
        "review_stage": "design",
        "task_id": "TASK-0001",
        "decision_unit_ids": ["DU-001"],
        "repository_id": "00000000-0000-4000-8000-000000000001",
        "branch": "feature",
        "base_commit": "a" * 40,
        "spec_sha256": "b" * 64,
        "policy_sha256": "c" * 64,
        "classification_input_sha256": "d" * 64,
        "content": {},
    }
    digest = runtime._sha(runtime._canonical(context))
    context["context_sha256"] = digest
    previous = {
        "schema_version": "1.0",
        "review_id": "REV-0001",
        "revision": 1,
        "task_id": "TASK-0001",
        "review_stage": "design",
        "reviewer": "reviewer",
        "recorded_at": "2026-10-31T00:00:00Z",
        "context_sha256": digest,
        "outcome": "APPROVE",
        "summary": "Synthetic review resolution boundary",
        "findings": [
            {
                "finding_id": "RF-001",
                "severity": "medium",
                "title": "Finding",
                "location": {"path": "protected.txt"},
                "evidence_refs": [],
                "status": "open",
            }
        ],
    }
    (task / "reviews/REV-0001-r0001.json").write_bytes(runtime._canonical(previous))
    (task / f"review-contexts/{digest}.json").write_bytes(runtime._canonical(context))
    record.events.append(
        {
            "event_type": "review_recorded",
            "actor": "reviewer",
            "payload": {
                "review_id": "REV-0001",
                "revision": 1,
                "context_sha256": digest,
                "review_stage": "design",
            },
        }
    )
    return record, previous


@pytest.mark.parametrize("fault", [None, "severity", "removed", "reviewer", "actor", "float"])
def test_original_root_tracks_only_the_existing_review_resolution_transaction(
    original_root: Path, fault: str | None
) -> None:
    record, previous = _registered_review(original_root)
    before = runtime._root_snapshot(original_root, "TASK-0001")
    resolved = deepcopy(previous)
    resolved.update(revision=2, recorded_at="2026-10-31T00:00:01Z")
    resolved["findings"][0].update(
        status="resolved",
        resolution={
            "reason": "Reviewed resolution",
            "actor": "reviewer",
            "resolved_at": resolved["recorded_at"],
        },
    )
    event = {
        "event_type": "review_finding_resolved",
        "actor": "reviewer",
        "payload": {"review_id": "REV-0001", "revision": 2, "finding_id": "RF-001"},
    }
    if fault == "severity":
        resolved["findings"][0]["severity"] = "low"
    elif fault == "removed":
        resolved["findings"] = []
    elif fault == "reviewer":
        resolved["reviewer"] = "other"
    elif fault == "actor":
        resolved["findings"][0]["resolution"]["actor"] = "other"
    elif fault == "float":
        event["payload"]["revision"] = 2.0
    path = original_root / ".ai/tasks/TASK-0001/reviews/REV-0001-r0002.json"
    path.write_bytes(runtime._canonical(resolved))
    record.events.append(event)
    if fault is not None:
        with pytest.raises(AiflowError):
            runtime._check_root(original_root, "TASK-0001", before)
        return
    runtime._check_root(original_root, "TASK-0001", before)
    after = runtime._governance_snapshot(original_root, "TASK-0001", record.events)
    assert str(path.relative_to(original_root).as_posix()) in after["paths"]
    assert all(
        after["immutable"][p] == digest for p, digest in before["governance"]["immutable"].items()
    )


def test_original_root_allows_only_its_exact_owned_run(original_root: Path) -> None:
    logs = original_root / ".ai/tasks/TASK-0001/logs"
    logs.mkdir()
    run = logs / "controlled-run"
    before = runtime._root_snapshot(original_root, "TASK-0001", run)
    (run / "node/raw").mkdir(parents=True)
    (run / "node/raw/output").write_bytes(b"owned output")
    runtime._check_root(original_root, "TASK-0001", before, run)
    (logs / "unowned-output").write_bytes(b"not owned by run")
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(original_root, "TASK-0001", before, run)
    assert caught.value.code == "NODE_ROOT_DRIFT"


def test_original_root_rejects_free_run_exemption(original_root: Path) -> None:
    before = runtime._root_snapshot(original_root, "TASK-0001")
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(original_root, "TASK-0001", before, original_root / "untracked")
    assert caught.value.code == "NODE_ROOT_DRIFT"


def _audit_commit(root: Path, message: str = "Synthetic governance update") -> None:
    path = root / ".ai/tasks/TASK-0001/task.yaml"
    path.write_bytes(b"synthetic: governance-only\n")
    _git_fixture(root, "add", "--force", ".ai/tasks/TASK-0001/task.yaml")
    _git_fixture(root, "commit", "--quiet", "-m", message)


def _git_object(root: Path, data: bytes, *arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments), cwd=root, input=data, capture_output=True, check=True, timeout=30
    )
    return result.stdout.decode().strip()


@pytest.mark.parametrize("history", ["reverted_change", "merge_ancestor", "unrelated_root"])
def test_original_root_rejects_non_governance_history_hidden_by_empty_net_diff(
    original_root: Path, history: str
) -> None:
    ancestor = _git_fixture(original_root, "rev-parse", "HEAD")
    if history == "merge_ancestor":
        (original_root / "protected.txt").write_bytes(b"already reviewed subject\n")
        _git_fixture(original_root, "add", "protected.txt")
        _git_fixture(original_root, "commit", "--quiet", "-m", "Synthetic reviewed subject")
    before = runtime._root_snapshot(original_root, "TASK-0001")
    old = before["git"]["head"]
    tree = _git_fixture(original_root, "rev-parse", "HEAD^{tree}")
    if history == "reverted_change":
        blob = _git_object(
            original_root, b"unrelated intermediate content\n", "hash-object", "-w", "--stdin"
        )
        listing = _git_fixture(original_root, "ls-tree", tree).splitlines()
        changed = [
            f"100644 blob {blob}\tprotected.txt" if row.endswith("\tprotected.txt") else row
            for row in listing
        ]
        bad_tree = _git_object(original_root, ("\n".join(changed) + "\n").encode(), "mktree")
        middle = _git_fixture(
            original_root, "commit-tree", bad_tree, "-p", old, "-m", "Unrelated change"
        )
        parents = ("-p", middle)
    elif history == "merge_ancestor":
        parents = ("-p", old, "-p", ancestor)
    else:
        other_root = _git_fixture(original_root, "commit-tree", tree, "-m", "Unrelated root")
        parents = ("-p", old, "-p", other_root)
    message = "Synthetic final governance commit"
    new = _git_fixture(original_root, "commit-tree", tree, *parents, "-m", message)
    _git_fixture(original_root, "update-ref", "-m", "commit: " + message, "HEAD", new, old)
    (original_root / ".git/COMMIT_EDITMSG").write_bytes((message + "\n").encode())
    assert _git_fixture(original_root, "diff", "--name-only", old, new) == ""
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(original_root, "TASK-0001", before)
    assert caught.value.code == "NODE_ROOT_DRIFT"


@pytest.mark.parametrize("packed", [False, True])
def test_original_root_accepts_exact_governance_commit_and_new_loose_ref(
    original_root: Path, packed: bool
) -> None:
    if packed:
        _git_fixture(original_root, "pack-refs", "--all")
    before = runtime._root_snapshot(original_root, "TASK-0001")
    _audit_commit(original_root)
    runtime._check_root(original_root, "TASK-0001", before)


@pytest.mark.parametrize("mutation", ["config", "hook", "info", "old_object", "unknown"])
def test_original_root_protects_git_admin_during_a_valid_governance_commit(
    original_root: Path, mutation: str
) -> None:
    before = runtime._root_snapshot(original_root, "TASK-0001")
    _audit_commit(original_root)
    git = original_root / ".git"
    if mutation == "config":
        with (git / "config").open("ab") as stream:
            stream.write(b"\n[synthetic]\nvalue = changed\n")
    elif mutation == "hook":
        (git / "hooks/pre-commit.sample").write_bytes(b"unknown\n")
    elif mutation == "info":
        (git / "info/exclude").write_bytes(b"unknown\n")
    elif mutation == "old_object":
        path = Path(
            next(
                row["path"]
                for row in before["metadata"]
                if "/objects/" in row["path"].replace("\\", "/")
                and stat.S_ISREG(row["identity"]["mode"])
            )
        )
        info = path.stat()
        data = path.read_bytes()
        path.chmod(0o666)
        path.write_bytes(data)
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
    else:
        (git / "unknown-admin-file").write_bytes(b"not an allowed Git output")
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(original_root, "TASK-0001", before)
    assert caught.value.code == "NODE_ROOT_DRIFT"


@pytest.mark.parametrize("mutation", ["prefix", "chain", "message", "unknown_object"])
def test_original_root_rejects_forged_governance_git_outputs(
    original_root: Path, mutation: str
) -> None:
    before = runtime._root_snapshot(original_root, "TASK-0001")
    _audit_commit(original_root)
    git = original_root / ".git"
    if mutation == "message":
        (git / "COMMIT_EDITMSG").write_bytes(b"not current commit message\n")
    elif mutation == "unknown_object":
        directory = git / "objects/aa"
        directory.mkdir(exist_ok=True)
        (directory / ("b" * 38)).write_bytes(b"not a reachable object")
    else:
        path = git / "logs/HEAD"
        data = path.read_bytes()
        if mutation == "prefix":
            data = b"1" + data[1:]
        else:
            size = before["git_audit"]["logs"][str(path)]["size"]
            data = data[:size] + b"0" * 40 + data[size + 40 :]
        path.write_bytes(data)
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(original_root, "TASK-0001", before)
    assert caught.value.code == "NODE_ROOT_DRIFT"


def test_original_root_metadata_covers_external_linked_worktree_admin(
    original_root: Path, tmp_path: Path
) -> None:
    linked = tmp_path.parent / (tmp_path.name + "-linked")
    _git_fixture(original_root, "worktree", "add", "--quiet", "-b", "synthetic-linked", str(linked))
    task = linked / ".ai/tasks/TASK-0001"
    task.mkdir(parents=True)
    (task / "approvals.json").write_bytes(b"[]")
    before = runtime._root_snapshot(linked, "TASK-0001")
    common_config = original_root / ".git/config"
    assert any(row["path"] == str(common_config) for row in before["metadata"])
    with common_config.open("ab") as stream:
        stream.write(b"\n[synthetic]\nvalue = changed\n")
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(linked, "TASK-0001", before)
    assert caught.value.code == "NODE_ROOT_DRIFT"


@pytest.mark.parametrize(
    "mutation", ["paths", "bool_size", "sha", "prefix_extra", "logs_type", "extra"]
)
def test_original_root_git_audit_rejects_self_reported_roles_before_private_reads(
    original_root: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    before = runtime._root_snapshot(original_root, "TASK-0001")
    _audit_commit(original_root)
    private = original_root / ".ai/private/note"
    audit = before["git_audit"]
    prefix = next(iter(audit["logs"].values()))
    if mutation == "paths":
        audit["logs"][str(private)] = {"size": 0, "sha256": runtime._sha(b"")}
    elif mutation == "bool_size":
        prefix["size"] = True
    elif mutation == "sha":
        prefix["sha256"] = "not-a-digest"
    elif mutation == "prefix_extra":
        prefix["extra"] = True
    elif mutation == "logs_type":
        audit["logs"] = []
    else:
        audit["extra"] = True
    original = runtime._read

    def read(path: Path, **options):
        assert path != private, "self-reported audit roles must not read unknown private bytes"
        return original(path, **options)

    monkeypatch.setattr(runtime, "_read", read)
    with pytest.raises(AiflowError) as caught:
        runtime._check_root(original_root, "TASK-0001", before)
    assert caught.value.code == "NODE_ROOT_DRIFT"


@pytest.fixture(scope="module")
def coverage_originals(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str, str, dict]:
    root = tmp_path_factory.mktemp("node-coverage-git")
    _git_fixture(root, "init", "--quiet")
    _git_fixture(root, "config", "user.name", "Synthetic Test")
    _git_fixture(root, "config", "user.email", "synthetic@example.invalid")
    _git_fixture(root, "config", "core.autocrlf", "false")
    (root / "src/local").mkdir(parents=True)
    (root / "src/local/example.ts").write_bytes(b"export const value = 0;\n")
    _git_fixture(root, "add", ".")
    _git_fixture(root, "commit", "--quiet", "-m", "Synthetic baseline")
    base = _git_fixture(root, "rev-parse", "HEAD")
    (root / "src/local/example.ts").write_bytes(b"export const value = 1;\n")
    _git_fixture(root, "add", ".")
    _git_fixture(root, "commit", "--quiet", "-m", "Synthetic subject")
    subject = _git_fixture(root, "rev-parse", "HEAD")
    return root, base, subject, runtime._source(root, subject)


def _coverage_reports(root: Path, directory: Path) -> None:
    reports = directory / "coverage"
    reports.mkdir()
    path = str(root / "src/local/example.ts")
    entry = {
        "path": path,
        "statementMap": {
            "0": {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": 23}}
        },
        "s": {"0": 1},
    }
    counts = {"lines": {"total": 1, "covered": 1, "skipped": 0, "pct": 100}}
    (reports / "coverage-final.json").write_text(json.dumps({path: entry}), encoding="utf-8")
    (reports / "coverage-summary.json").write_text(
        json.dumps({path: counts, "total": counts}), encoding="utf-8"
    )
    source = (root / "src/local/example.ts").read_bytes()
    mapping = {
        "schema_version": "1.0",
        "method": runtime.COVERAGE_METHOD,
        "files": {"src/local/example.ts": {"sha256": runtime._sha(source), "lines": [1]}},
    }
    (directory / "expected-map.json").write_text(json.dumps(mapping), encoding="utf-8")


def test_coverage_originals_recompute_exact_source_diff_and_summary(
    tmp_path: Path, coverage_originals: tuple[Path, str, str, dict]
) -> None:
    root, base, subject, source = coverage_originals
    _coverage_reports(root, tmp_path)
    changed, deleted, diff = runtime._changed_lines(root, base, subject)
    assert changed == {"src/local/example.ts": [1]}
    assert deleted == ()
    (tmp_path / "source.diff").write_bytes(diff)
    result = runtime._coverage(root, tmp_path, source, base, subject, root)
    assert result["changed"] == {
        "covered": 1,
        "executable": 1,
        "threshold": 90,
        "applicability": "applicable",
    }


def test_coverage_original_digest_detects_changed_hits_even_when_counts_are_identical(
    tmp_path: Path, coverage_originals: tuple[Path, str, str, dict]
) -> None:
    root, base, subject, source = coverage_originals
    _coverage_reports(root, tmp_path)
    (tmp_path / "source.diff").write_bytes(runtime._changed_lines(root, base, subject)[2])
    (tmp_path / "source-manifest.json").write_bytes(
        runtime._canonical(
            {
                "root": str(root),
                "files": [
                    {"path": row["path"], "sha256": row["sha256"]} for row in source["files"]
                ],
            }
        )
    )
    result = runtime._coverage(root, tmp_path, source, base, subject, root)
    originals = runtime._coverage_originals(tmp_path, result)
    path = tmp_path / "coverage/coverage-final.json"
    changed = json.loads(path.read_text())
    changed[next(iter(changed))]["s"]["0"] = 2
    path.write_text(json.dumps(changed), encoding="utf-8")
    assert runtime._coverage(root, tmp_path, source, base, subject, root) == result
    assert runtime._coverage_originals(tmp_path, result) != originals


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_report",
        "missing_map",
        "map_hash",
        "map_lines",
        "external_source",
        "path_identity",
        "missing_summary",
        "summary_count",
        "summary_bool",
        "summary_extra",
        "missing_diff",
        "wrong_diff",
    ],
)
def test_coverage_originals_reject_incomplete_or_rebound_artifacts(
    tmp_path: Path, coverage_originals: tuple[Path, str, str, dict], mutation: str
) -> None:
    root, base, subject, source = coverage_originals
    _coverage_reports(root, tmp_path)
    (tmp_path / "source.diff").write_bytes(runtime._changed_lines(root, base, subject)[2])
    final = tmp_path / "coverage/coverage-final.json"
    summary = tmp_path / "coverage/coverage-summary.json"
    mapping = tmp_path / "expected-map.json"
    if mutation == "extra_report":
        (tmp_path / "coverage/unknown.json").write_bytes(b"{}")
    elif mutation.startswith("map_") or mutation == "missing_map":
        document = json.loads(mapping.read_text())
        if mutation == "missing_map":
            document["files"] = {}
        elif mutation == "map_hash":
            document["files"]["src/local/example.ts"]["sha256"] = "0" * 64
        else:
            document["files"]["src/local/example.ts"]["lines"] = []
        mapping.write_text(json.dumps(document), encoding="utf-8")
    elif mutation in {"external_source", "path_identity"}:
        document = json.loads(final.read_text())
        key = next(iter(document))
        if mutation == "external_source":
            document[str(tmp_path / "outside.ts")] = document.pop(key)
        else:
            document[key]["path"] = "../outside.ts"
        final.write_text(json.dumps(document), encoding="utf-8")
    elif mutation.startswith("summary_") or mutation == "missing_summary":
        document = json.loads(summary.read_text())
        key = next(key for key in document if key != "total")
        if mutation == "missing_summary":
            del document[key]
        elif mutation == "summary_count":
            document[key]["lines"]["covered"] = 0
        elif mutation == "summary_bool":
            document[key]["lines"]["total"] = True
        else:
            document["unknown"] = document[key]
        summary.write_text(json.dumps(document), encoding="utf-8")
    elif mutation == "missing_diff":
        (tmp_path / "source.diff").unlink()
    else:
        (tmp_path / "source.diff").write_bytes(b"forged")
    with pytest.raises(AiflowError):
        runtime._coverage(root, tmp_path, source, base, subject, root)


FILETIME_EPOCH = 116444736000000000
CREATED_NS = 1_700_000_000_000_000_000
WRITTEN_NS = CREATED_NS + 200
CHANGE_TIME = FILETIME_EPOCH + CREATED_NS // 100 + 17
HANDLE = 81


@pytest.fixture
def native_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Keep pathlib's real OS while replacing only the runtime's OS reference."""
    monkeypatch.setattr(runtime, "os", SimpleNamespace(name="nt"))

    def prepare(kind="file", fault=None):
        path = tmp_path / kind
        if kind == "directory":
            path.mkdir()
        else:
            path.write_bytes(b"metadata only")
        directory = kind == "directory"
        attributes = 0x10 if directory else 0x20
        mode = (stat.S_IFDIR | 0o755) if directory else (stat.S_IFREG | 0o644)
        state = SimpleNamespace(opened=[], held=[], basic=[], closed=[], stat_reads=[])
        expected = {
            "device": 71,
            "inode": (3 << 32) | 19,
            "nlink": 1,
            "size": (5 << 32) | 23,
            "mtime_ns": WRITTEN_NS,
            "ctime_ns": CREATED_NS,
            "mode": (stat.S_IFDIR if directory else stat.S_IFREG) | 0o644,
            "attributes": attributes,
        }

        def safe_info(selected, *, directory=False):
            assert selected == path
            assert directory is (kind == "directory")
            state.stat_reads.append(selected)
            return SimpleNamespace(
                st_dev=expected["device"],
                st_ino=expected["inode"]
                + int(fault == "path_replaced" and len(state.stat_reads) == 2),
                st_nlink=1,
                st_size=expected["size"],
                st_mtime_ns=WRITTEN_NS,
                st_ctime_ns=CREATED_NS,
                st_mode=mode,
                st_file_attributes=attributes,
            )

        def create(*arguments):
            state.opened.append(arguments)
            if fault == "open_none":
                return None
            if fault == "open_invalid":
                return ctypes.c_void_p(-1).value
            return HANDLE

        def information(handle, pointer):
            state.held.append(handle)
            if fault == "information_unavailable":
                return False
            held = pointer._obj
            held.attributes = attributes ^ (0x10 if fault == "object_type" else 0)
            held.volume = 71 + int(fault == "volume")
            held.index_high = 3 + int(fault == "file_id")
            held.index_low = 19
            held.links = 2 if fault == "link_count" else 1
            held.size_high = 5 + int(fault == "size")
            held.size_low = 23
            for field, unix_ns in (("creation", CREATED_NS), ("write", WRITTEN_NS)):
                ticks = FILETIME_EPOCH + unix_ns // 100
                ticks += int(fault == field + "_time")
                setattr(held, field + "_low", ticks & 0xFFFFFFFF)
                setattr(held, field + "_high", ticks >> 32)
            return True

        def basic_information(handle, information_class, pointer, size):
            state.basic.append((handle, information_class, size))
            if fault == "basic_unavailable" or (
                fault == "final_unavailable" and len(state.basic) == 2
            ):
                return False
            basic = pointer._obj
            assert size == ctypes.sizeof(basic)
            basic.creation = FILETIME_EPOCH + CREATED_NS // 100
            basic.access = FILETIME_EPOCH + CREATED_NS // 100 + len(state.basic)
            basic.write = FILETIME_EPOCH + WRITTEN_NS // 100
            basic.change = CHANGE_TIME + int(fault == "change_time" and len(state.basic) == 2)
            basic.attributes = attributes
            return True

        def close(handle):
            state.closed.append(handle)
            return fault != "close_failed"

        kernel = SimpleNamespace(
            CreateFileW=create,
            GetFileInformationByHandle=information,
            GetFileInformationByHandleEx=basic_information,
            CloseHandle=close,
        )

        def load(name, *, use_last_error):
            assert name == "kernel32" and use_last_error is True
            return kernel

        monkeypatch.setattr(runtime, "_safe_info", safe_info)
        monkeypatch.setattr(ctypes, "WinDLL", load, raising=False)
        return path, expected, state

    return prepare


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_same_handle_change_time_and_attribute_only_open(native_metadata, kind):
    path, expected, state = native_metadata(kind)

    actual = runtime._metadata_identity(path)

    assert actual == {**expected, "change_time_ns": CHANGE_TIME * 100}
    assert actual["change_time_ns"] != actual["ctime_ns"]
    assert state.opened == [(str(path), 0x80, 7, None, 3, 0x02200000, None)]
    assert state.held == [HANDLE]
    assert [call[:2] for call in state.basic] == [(HANDLE, 0), (HANDLE, 0)]
    assert len(state.stat_reads) == 2
    assert state.closed == [HANDLE]


@pytest.mark.parametrize(
    "fault",
    [
        "open_none",
        "open_invalid",
        "information_unavailable",
        "basic_unavailable",
        "volume",
        "file_id",
        "link_count",
        "size",
        "object_type",
        "creation_time",
        "write_time",
        "path_replaced",
        "final_unavailable",
        "change_time",
        "close_failed",
    ],
)
def test_native_metadata_uncertainty_never_certifies_identity(native_metadata, fault):
    path, _expected, state = native_metadata(fault=fault)

    with pytest.raises(ContractError) as failure:
        runtime._metadata_identity(path)

    assert failure.value.code == "NODE_ROOT_DRIFT"
    assert state.closed == ([] if fault in {"open_none", "open_invalid"} else [HANDLE])
    if fault == "information_unavailable":
        assert state.basic == []
