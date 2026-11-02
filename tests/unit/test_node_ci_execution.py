"""Synthetic byte-reader contracts, never Node/Job/GitHub execution evidence."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from initialization_helpers import fixture_git
from test_installed_mutation_transactions import parser_phase, pure_guard
from test_node_ci import _documents
from test_node_profile_contract import (
    _NATIVE_OWNERSHIP_UNIT_BYTES,
    _negative_process_original,
    native_ownership_cache,
    report,
    source,
)
from test_node_v2_contract import node_documents, write_policy
from test_node_v2_coverage import catalog, product_fixture

from aiflow import installed_mutations as installed
from aiflow import node_ci
from aiflow import node_execution as node
from aiflow.errors import AiflowError
from aiflow.redaction import redact_text

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def forbid_producing_paths(monkeypatch: pytest.MonkeyPatch, producing_root: Path):
    """Historical coordinates permit lexical operations, never filesystem access."""
    attempts = []
    with monkeypatch.context() as patch:
        for name in ("resolve", "stat", "lstat", "open"):
            original = getattr(Path, name)

            def observe(path, *args, _original=original, _name=name, **kwargs):
                if Path(path).is_relative_to(producing_root):
                    attempts.append(_name)
                    raise AssertionError("replay inspected a historical producing path")
                return _original(path, *args, **kwargs)

            patch.setattr(Path, name, observe)
        yield
    assert not attempts


def synthetic_materials(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Real source pins around non-executable fixture interpreter/host roles."""
    prefix, base, system = root / "e", root / "b", root / "w"
    site = prefix / "Lib/site-packages/aiflow"
    site.mkdir(parents=True)
    for name in {
        "__init__.py",
        "installed_probe.py",
        "installed_mutations.py",
        "mutation_runner.py",
        *(target[0] for target in installed._TARGETS.values()),
    }:
        shutil.copyfile(ROOT / "src/aiflow" / name, site / name)
    for path in (prefix / "Scripts/python.exe", base / "python.exe", base / "python311.dll"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic role only: never executed\n")
    (prefix / "Scripts/aiflow.exe").write_bytes(b"synthetic distribution entrypoint\n")
    configuration = prefix / "pyvenv.cfg"
    configuration.write_bytes(b"include-system-site-packages = false\n")
    metadata = site.parent / "aiflow-0.2.0.dist-info"
    (metadata / "licenses").mkdir(parents=True)
    (metadata / "METADATA").write_bytes(b"Metadata-Version: 2.1\nName: aiflow\nVersion: 0.2.0\n")
    (metadata / "licenses/LICENSE").write_bytes(b"Public synthetic unimported license fixture.\n")
    distribution_files = sorted(
        path
        for path in prefix.rglob("*")
        if path.is_file() and path not in {prefix / "Scripts/python.exe", configuration}
    )
    record = []
    for path in distribution_files:
        data = path.read_bytes()
        relative = (
            path.relative_to(site.parent).as_posix()
            if path.is_relative_to(site.parent)
            else "../../" + path.relative_to(prefix).as_posix()
        )
        digest = base64.urlsafe_b64encode(bytes.fromhex(node._sha(data))).decode().rstrip("=")
        record.append(f"{relative},sha256={digest},{len(data)}")
    (metadata / "RECORD").write_text(
        "\n".join([*record, "aiflow-0.2.0.dist-info/RECORD,,"]) + "\n", encoding="utf8"
    )
    distribution_files.append(metadata / "RECORD")
    distribution_rows = [installed._file(path) for path in distribution_files]
    script_row = next(row for row in distribution_rows if Path(row["path"]).name == "aiflow.exe")
    # importlib.metadata preserves this ordinary RECORD spelling. Keep it in
    # original installed metadata while the real local closure is canonical.
    script_row["path"] = str(site.parent / "../../Scripts/aiflow.exe")
    engine = {
        "python": str(prefix / "Scripts/python.exe"),
        "distributions": [
            {
                "name": "aiflow",
                "version": "0.2.0",
                "files": distribution_rows,
            }
        ],
        "startup": {
            "files": [],
            "setuptools": False,
            "pyvenv_configuration": installed._file(configuration),
            "python_environment": {
                "prefix": str(prefix),
                "site_roots": [str(site.parent)],
                "active_site_roots": [str(site.parent)],
                "enable_user_site": False,
            },
            "site_roots": [
                {"path": str(site.parent), "identity": node._identity(site.parent.stat())}
            ],
        },
    }
    closure = installed._closure(engine, prefix)
    probes = installed._probe_contract()
    probes["source"] = installed._file(site / "installed_probe.py")
    tools = {}
    for role, relative in node._OS_TOOL_PATHS.items():
        tools[role] = {**installed._file(base / "python.exe"), "path": str(system / relative)}
        tools[role + "_config"] = None
    monkeypatch.setattr(node, "_windows_root", lambda: system)
    return {
        "kind": installed.ACTION_TYPE,
        "version": 1,
        "engine": {"installed": engine, "closure": closure},
        "interpreter": {
            "executable": installed._file(prefix / "Scripts/python.exe"),
            "base_executable": installed._file(base / "python.exe"),
            "runtime": installed._file(base / "python311.dll"),
            "prefix": str(prefix),
            "site": str(site.parent),
            "base_prefix": str(base),
            "implementation": "cpython",
            "version": [3, 11, 0],
            "cache_tag": "cpython-311",
        },
        "host_tools": tools,
        "probes": probes,
        "operators": {
            "declarations": deepcopy(installed._TARGETS),
            "source": installed._file(site / "installed_mutations.py"),
            "native_source": installed._file(site / "mutation_runner.py"),
            "bootstrap_sha256": node._sha(installed._BOOTSTRAP.encode()),
        },
    }


def receipt_input(root: Path) -> tuple[dict, dict, dict, list[str], dict]:
    """A parser input only: no claim that this synthetic process ever ran."""
    streams = {"stdout": b"synthetic output\xff\n", "stderr": b""}
    logs = {
        name: redact_text(data.decode("utf8", errors="replace")).encode()
        for name, data in streams.items()
    }
    argv, environment = [str(root / "node.exe"), "--version"], {"TEMP": str(root / "tmp")}
    receipt = {
        "returncode": 0,
        "timed_out": False,
        "stdout_overflow": False,
        "stderr_overflow": False,
        "cleanup": "confirmed",
        "execution_error": False,
        "receipt": {
            "process_id": 100,
            "creation_time_filetime": 100,
            "created_suspended": True,
            "assigned": True,
            "initial_membership": True,
            "resumed": True,
            "job_empty": True,
            "stdout_eof": True,
            "stderr_eof": True,
            "terminate_requested": False,
            "closed": True,
        },
        **{name + "_size": len(data) for name, data in streams.items()},
        **{name + "_sha256": node._sha(data) for name, data in streams.items()},
        "argv": argv,
        "cwd": str(root),
        "environment_sha256": node._sha(node._canonical(environment)),
        "timeout_seconds": 30,
        "duration_ms": 1,
    }
    return receipt, streams, logs, argv, environment


def test_receipt_reader_accepts_bound_bytes_without_opening_producing_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = tmp_path / "absent-producer"
    receipt, streams, logs, argv, environment = receipt_input(old)
    with pure_guard(monkeypatch):
        node.validate_receipt_originals(
            receipt,
            receipt=deepcopy(receipt),
            streams=streams,
            logs=logs,
            argv=argv,
            cwd=old,
            environment=environment,
        )
    assert not old.exists()


@pytest.mark.parametrize(
    "variant",
    [
        "receipt_binding",
        "raw",
        "log",
        "stream_role",
        "log_role",
        "unknown",
        "boolean_integer",
        "timed_out",
        "overflow",
        "cleanup",
        "job_empty",
        "eof",
        "zero_pid",
        "timeout",
        "argv",
        "cwd",
        "environment",
        "stream_budget",
    ],
)
def test_receipt_reader_rejects_incomplete_or_rebound_originals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    old = tmp_path / "absent-producer"
    receipt, streams, logs, argv, environment = receipt_input(old)
    if variant == "raw":
        streams["stdout"] += b"changed"
    elif variant == "log":
        logs["stdout"] = streams["stdout"]  # UTF-8 replacement is part of the wire contract.
    elif variant == "stream_role":
        streams["extra"] = b""
    elif variant == "log_role":
        del logs["stderr"]
    elif variant == "unknown":
        receipt["extra"] = None
    elif variant == "boolean_integer":
        receipt["duration_ms"] = True
    elif variant == "timed_out":
        receipt["timed_out"] = True
    elif variant == "overflow":
        receipt["stdout_overflow"] = True
    elif variant == "cleanup":
        receipt["cleanup"] = "unconfirmed"
    elif variant in {"job_empty", "eof", "zero_pid"}:
        key = {"job_empty": "job_empty", "eof": "stdout_eof", "zero_pid": "process_id"}[variant]
        receipt["receipt"][key] = 0 if variant == "zero_pid" else False
    elif variant == "timeout":
        receipt["timeout_seconds"] = 0
    elif variant == "argv":
        receipt["argv"] = ["different-executable"]
    elif variant == "cwd":
        receipt["cwd"] = str(old / "other")
    elif variant == "environment":
        receipt["environment_sha256"] = "0" * 64
    elif variant == "stream_budget":
        streams["stdout"] = b"x" * (1024 * 1024 + 1)
        receipt["stdout_size"] = len(streams["stdout"])
        receipt["stdout_sha256"] = node._sha(streams["stdout"])
        logs["stdout"] = streams["stdout"]
    expected = deepcopy(receipt)
    if variant == "receipt_binding":
        expected["duration_ms"] += 1
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        node.validate_receipt_originals(
            expected,
            receipt=receipt,
            streams=streams,
            logs=logs,
            argv=argv,
            cwd=old,
            environment=environment,
        )


def coverage_input(checkout: Path) -> tuple[dict, dict, dict, dict, bytes]:
    relative = "src/local/example.ts"
    original = str(checkout / relative)
    sources = {relative: source(2)}
    reports = {original: report(original, [1, 1])}
    summary = {
        key: {"lines": {"total": 2, "covered": 2, "skipped": 0}} for key in (original, "total")
    }
    expected = {
        "schema_version": "1.0",
        "method": node.COVERAGE_METHOD,
        "files": {relative: {"sha256": node._sha(sources[relative]), "lines": [1, 2]}},
    }
    diff = b"--- a/src/local/example.ts\n+++ b/src/local/example.ts\n@@ -1,2 +1,2 @@\n"
    return sources, reports, summary, expected, diff


def test_coverage_reader_recomputes_retained_arithmetic_without_old_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = tmp_path / "absent-checkout"
    sources, reports, summary, expected, diff = coverage_input(old)
    original = deepcopy((sources, reports, summary, expected))
    with pure_guard(monkeypatch):
        result = node._coverage_from_originals(
            old,
            sources,
            node._canonical(reports),
            node._canonical(summary),
            expected,
            diff,
            revision=1,
        )
    assert result["total"] == {"covered": 2, "executable": 2, "threshold": 85}
    assert result["changed"]["covered"] == 2
    assert (sources, reports, summary, expected) == original
    assert not old.exists()


@pytest.mark.parametrize(
    "variant",
    ["external_path", "source_hash", "summary", "map_members", "diff", "timeout", "budget"],
)
def test_coverage_reader_rejects_unbound_or_unsafe_originals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    old = tmp_path / "absent-checkout"
    sources, reports, summary, expected, diff = coverage_input(old)
    if variant == "external_path":
        value = reports.pop(next(iter(reports)))
        value["path"] = str(tmp_path / "outside.ts")
        reports[value["path"]] = value
    elif variant == "source_hash":
        expected["files"]["src/local/example.ts"]["sha256"] = "0" * 64
    elif variant == "summary":
        summary["total"]["lines"]["covered"] = 1
    elif variant == "map_members":
        expected["files"]["src/local/missing.ts"] = {}
    elif variant == "diff":
        diff = b"+++ /unbound/path\n"
    elif variant == "timeout":
        ticks = iter((0, 30_000_000_001))
        monkeypatch.setattr(node, "monotonic_ns", lambda: next(ticks))
    elif variant == "budget":
        # Exercise the real input boundary with a tiny cap, without a large allocation.
        monkeypatch.setattr(node, "MAX_JSON_BYTES", 1)
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        node._coverage_from_originals(
            old,
            sources,
            node._canonical(reports),
            node._canonical(summary),
            expected,
            diff,
            revision=2 if variant == "budget" else 1,
        )


def test_retained_diff_preserves_deleted_sources_and_deduplicates_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = (
        b"--- a/src/local/gone.ts\n+++ /dev/null\n"
        b"--- a/src/local/kept.ts\n+++ b/src/local/kept.ts\n"
        b"@@ -1 +2,2 @@\n@@ -1 +2 @@\n"
    )
    with pure_guard(monkeypatch):
        assert node._parse_changed_lines(raw) == (
            {"src/local/kept.ts": [2, 3]},
            ("src/local/gone.ts",),
            raw,
        )


@pytest.mark.parametrize("variant", [None, "engine_bytes", "engine_origin", "host_bytes"])
def test_engine_and_host_replay_opens_exact_transported_origins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str | None
) -> None:
    engine_root = tmp_path / "absent-engine"
    system_root = tmp_path / "absent-windows"
    files = {"engine/Lib/guard.py": b"public source\n", "host/cmd": b"public host role\n"}
    for relative, data in files.items():
        path = tmp_path / "originals" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    row = {
        "path": str(engine_root / "Lib/guard.py"),
        "size": len(files["engine/Lib/guard.py"]),
        "sha256": node._sha(files["engine/Lib/guard.py"]),
    }
    manifests = {
        "engine.json": {"distributions": [{"files": [row]}], "startup": {"files": []}},
        "host-tools.json": {
            "cmd": {
                "path": str(system_root / "System32/cmd.exe"),
                "size": len(files["host/cmd"]),
                "sha256": node._sha(files["host/cmd"]),
            },
            "cmd_config": None,
        },
    }
    roles = {"engine": {"root": str(engine_root)}}
    if variant == "engine_bytes":
        (tmp_path / "originals/engine/Lib/guard.py").write_bytes(b"drift")
    elif variant == "engine_origin":
        row["path"] = str(tmp_path / "outside.py")
    elif variant == "host_bytes":
        (tmp_path / "originals/host/cmd").write_bytes(b"drift")
    with pure_guard(monkeypatch):
        if variant is None:
            assert node._ci_engine_host_originals(tmp_path, manifests, roles) == system_root
        else:
            with pytest.raises(AiflowError):
                node._ci_engine_host_originals(tmp_path, manifests, roles)
    assert not engine_root.exists() and not system_root.exists()


@pytest.mark.parametrize("escape", [False, True])
def test_node_engine_replay_uses_lexical_ordinary_record_script_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, escape: bool
) -> None:
    producing = tmp_path / "absent-engine"
    script = tmp_path / "originals/engine/Scripts/aiflow.exe"
    script.parent.mkdir(parents=True)
    script.write_bytes(b"public synthetic distribution entrypoint\n")
    cmd = tmp_path / "originals/host/cmd"
    cmd.parent.mkdir(parents=True)
    cmd.write_bytes(b"public host role\n")
    raw = str(
        producing
        / "Lib/site-packages"
        / ("../../../Scripts/aiflow.exe" if escape else "../../Scripts/aiflow.exe")
    )
    row = {"path": raw, "size": script.stat().st_size, "sha256": node._sha(script.read_bytes())}
    windows = tmp_path / "absent-windows"
    manifests = {
        "engine.json": {
            "distributions": [{"files": [row]}],
            "startup": {"files": [], "pyvenv_configuration": None},
        },
        "host-tools.json": {
            "cmd": {
                "path": str(windows / "System32/cmd.exe"),
                "size": cmd.stat().st_size,
                "sha256": node._sha(cmd.read_bytes()),
            }
        },
    }
    with forbid_producing_paths(monkeypatch, producing), pure_guard(monkeypatch):
        if escape:
            with pytest.raises(AiflowError):
                node._ci_engine_host_originals(
                    tmp_path, manifests, {"engine": {"root": str(producing)}}
                )
        else:
            assert (
                node._ci_engine_host_originals(
                    tmp_path, manifests, {"engine": {"root": str(producing)}}
                )
                == windows
            )
    assert row["path"] == raw


def test_node_projection_excludes_only_own_run_but_transport_manifest_seals_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "originals/node"
    (directory / "checkout").mkdir(parents=True)
    (directory / "run.json").write_bytes(b"public run original")
    (directory / "checkout/run.json").write_bytes(b"public source file with same leaf name")
    plan = SimpleNamespace(executions=())
    with pure_guard(monkeypatch):
        projection = node._node_inventory(directory, "V0", plan)
        complete = {"id": "node", **node._inventory(directory)}
        node._ci_verify_role(tmp_path, "node", complete)
    assert {row["path"] for row in projection} == {"checkout", "checkout/run.json"}
    assert "run.json" in {row["path"] for row in complete["entries"]}
    (directory / "run.json").write_bytes(b"changed original")
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        node._ci_verify_role(tmp_path, "node", complete)


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
@pytest.mark.parametrize("entrypoint", ["prepare", "execute", "replay"])
def test_unregistered_public_entrypoints_never_enter_physical_kernels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, level: str, entrypoint: str
) -> None:
    assert node_ci.CI_CAPS_REGISTERED is False
    documents = _documents(level)
    attested = documents["AttestedSource"]
    descriptor = documents["Descriptor"]
    admission = documents["Admission"]
    descriptor["source_tuple_sha256"] = node._sha(node._canonical(attested))
    admission["descriptor_sha256"] = node._sha(node._canonical(descriptor))
    attempt = tmp_path / "attempt"
    (attempt / "control").mkdir(parents=True)
    for name, value in (
        ("source-tuple", attested),
        ("descriptor", descriptor),
        ("admission", admission),
    ):
        (attempt / "control" / (name + ".json")).write_bytes(node._canonical(value))
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append("physical-kernel")
        raise AssertionError("an unregistered public entrypoint entered its kernel")

    for name in (
        "_prepare_ci_materials_kernel",
        "_execute_ci_node_kernel",
        "_replay_ci_node_kernel",
    ):
        monkeypatch.setattr(node, name, forbidden)
    with pure_guard(monkeypatch):
        if entrypoint == "replay":
            facts = node.replay_ci_node(
                package_root=tmp_path,
                prepared=documents["Prepared"],
                run=documents["Run"],
                role_manifests={},
            )
            assert facts == {
                "passed": False,
                "checks": [],
                "node_binding": None,
                "reason_codes": ["NODE_CI_UNAVAILABLE"],
            }
        else:
            with pytest.raises(AiflowError) as caught:
                if entrypoint == "prepare":
                    node.prepare_ci_materials(
                        tmp_path / "source",
                        tmp_path / "payload",
                        attempt_root=attempt,
                        admission=admission,
                        source_tuple=attested,
                    )
                else:
                    node.execute_ci_node(
                        tmp_path / "source",
                        "TASK-0001",
                        attempt_root=attempt,
                        admission=admission,
                        prepared=documents["Prepared"],
                        source_tuple=attested,
                    )
            assert caught.value.code == "NODE_CI_UNAVAILABLE"
    assert not attempts


_CI_CONFIG = b"// Public synthetic Vitest input; never evaluated by Node.\n"
_CI_PRODUCERS = {
    name: b"// Public synthetic producer role: " + name.encode() + b"\n"
    for name in node.ISTANBUL_FILES
}
_CI_SOURCE_SEEDS = pytest.StashKey[dict]()
_CI_RECORDED_SEEDS = pytest.StashKey[dict]()


@pytest.fixture(scope="session")
def ci_source_seeds(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> dict:
    """Immutable small Git histories; no task approval or Current is supplied."""
    existing = request.config.stash.get(_CI_SOURCE_SEEDS, None)
    if existing is not None:
        return existing
    seeds = {}
    for native in (False, True):
        root = tmp_path_factory.mktemp("s") / "source"
        root.mkdir()
        write_policy(root, node_documents())
        _products, tests, _coverage, _checkout = product_fixture(root.parent)
        packages = {
            "node_modules/" + name: {
                "version": version,
                "resolved": "https://registry.npmjs.org/synthetic/-/fixture.tgz",
                "integrity": "sha512-synthetic-fixture",
            }
            for name, version in {
                "vitest": node.VERSIONS["vitest"],
                "vite": node.VERSIONS["vite"],
                **node.ISTANBUL_PACKAGES,
            }.items()
        }
        config = {
            "compilerOptions": {
                "rootDir": "src/local",
                "outDir": "dist",
                "sourceMap": True,
                "declaration": True,
                "declarationMap": True,
            }
        }
        files = {
            "package.json": node._canonical(
                {
                    "name": "public-synthetic-kernel",
                    "scripts": {
                        name: node.SEMANTIC_CONTRACT["test_script"]
                        if name == "test"
                        else "synthetic-never-executed"
                        for name in ("build", "check", "test", "typecheck", "docs:check", "clean")
                    },
                }
            ),
            "package-lock.json": node._canonical({"lockfileVersion": 3, "packages": packages}),
            "tsconfig.json": node._canonical(config),
            "tsconfig.tests.json": b"{}",
            "agent-commands.json": b"{}",
            "vitest.config.ts": _CI_CONFIG,
            "src/local/run.ts": b"export const value = 0;\n",
            ".gitignore": b"node_modules/\ndist/\n.runtime/\n",
            ".ai/tasks/TASK-0001/task.yaml": b"task_id: TASK-0001\ncurrent_state: NEW\n",
            **tests,
            **(_NATIVE_OWNERSHIP_UNIT_BYTES if native else {}),
        }
        # The production fixture collector derives this exact temporary prefix
        # from tracked test bytes. The comment itself is never executed.
        files[next(iter(tests))] += b'// mkdtemp(join(tmpdir(), "synthetic-ci-"))\n'
        for relative, data in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        fixture_git(root, "init", "-b", "codex/synthetic-kernel")
        fixture_git(root, "config", "user.name", "Public Fixture")
        fixture_git(root, "config", "user.email", "fixture@example.invalid")
        fixture_git(root, "config", "core.autocrlf", "false")
        fixture_git(root, "add", ".")
        fixture_git(root, "commit", "-m", "Synthetic baseline")
        base = fixture_git(root, "rev-parse", "HEAD")
        (root / "src/local/run.ts").write_bytes(b"export const value = 1;\n")
        fixture_git(root, "add", "src/local/run.ts")
        fixture_git(root, "commit", "-m", "Synthetic subject")
        seeds[native] = (root, base, fixture_git(root, "rev-parse", "HEAD"))
    request.config.stash[_CI_SOURCE_SEEDS] = seeds
    return seeds


def kernel_parser_pairs(materials: dict, attempt: Path) -> dict:
    """Complete synthetic pair protocol, with real copy/overlay/parser guards."""
    pairs = []
    for index, probe_id in enumerate(installed.PROBE_IDS):
        pair = {"id": probe_id, "overlay": None, "baseline": None, "mutant": None}
        for suffix, key in (("b", "baseline"), ("m", "mutant")):
            phase = attempt / f"pair-{index}-{suffix}"
            phase.mkdir()
            node._copy_tree(
                Path(materials["engine"]["closure"]["root"]),
                phase / "i",
                materials["engine"]["closure"],
            )
            relative = "Lib/site-packages/aiflow/" + installed._TARGETS[probe_id][0]
            before = (phase / "i" / relative).read_bytes()
            if suffix == "m":
                after = installed._transformed_source(probe_id, before)
                (phase / "i" / relative).write_bytes(after)
                pair["overlay"] = {
                    "path": relative,
                    "before_sha256": node._sha(before),
                    "after_sha256": node._sha(after),
                }
            for name in ("c", "h", "t"):
                (phase / name).mkdir()
            stage = {
                "closure": node._inventory(phase / "i"),
                "cache": node._inventory(phase / "c"),
                "receipt": None,
            }
            parser_phase(
                SimpleNamespace(materials=materials),
                phase,
                probe_id,
                stage=stage,
                mutant=suffix == "m",
            )
            pair[key] = stage
        pairs.append(pair)
    return {"pairs": pairs, "failure": None}


@pytest.fixture
def ci_kernel_case(
    tmp_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    request,
    ci_source_seeds: dict,
):
    """Same-body CI protocol fixture. All tools and Job observations are synthetic.

    Only tool discovery/process boundaries and explicit public fixture byte pins
    are replaced. Source/dependency parsers, Git, fresh snapshots, receipts,
    catalog/product arithmetic and native ownership/seals remain production code.
    """
    parameters = getattr(request, "param", ("V0", False))
    level, native = parameters[:2]
    branch = parameters[2] if len(parameters) > 2 else None
    workspace = tmp_path
    source_root = workspace / "source"
    seed, base, subject = ci_source_seeds[native]
    shutil.copytree(seed, source_root)
    if branch is not None:
        assert fixture_git(source_root, "check-ref-format", "--branch", branch) == branch
        fixture_git(source_root, "branch", "-m", branch)
    attempt = workspace / ".tmp/node-ci/1-1"
    (attempt / "control").mkdir(parents=True)
    payload = workspace / "payload"
    npm = payload / "node/node_modules/npm"
    (npm / "bin").mkdir(parents=True)
    header = bytearray(128)
    header[:2], header[60:64], header[64:68], header[68:70], header[88:90] = (
        b"MZ",
        (64).to_bytes(4, "little"),
        b"PE\0\0",
        (0x8664).to_bytes(2, "little"),
        (0x20B).to_bytes(2, "little"),
    )
    (payload / "node/node.exe").write_bytes(header)
    (npm / "package.json").write_bytes(
        node._canonical({"name": "npm", "version": node.VERSIONS["npm"]})
    )
    for path in (payload / "node/npm.cmd", npm / "bin/npm.cmd", npm / "bin/npm-cli.js"):
        path.write_bytes(b"synthetic npm role; never executed\n")
    deps = payload / "dependencies/node_modules"
    lock = json.loads((source_root / "package-lock.json").read_bytes())
    for path, row in lock["packages"].items():
        package = deps / path.removeprefix("node_modules/")
        package.mkdir(parents=True, exist_ok=True)
        (package / "package.json").write_bytes(
            node._canonical({"name": package.name, "version": row["version"]})
        )
    for name, data in _CI_PRODUCERS.items():
        path = deps / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    monkeypatch.setattr(node, "NODE_V2_CONFIG_SHA256", node._sha(_CI_CONFIG))
    monkeypatch.setattr(
        node, "ISTANBUL_FILES", {name: node._sha(data) for name, data in _CI_PRODUCERS.items()}
    )
    if native:
        monkeypatch.setattr(
            node,
            "NATIVE_OWNERSHIP_INPUTS",
            {name: node._sha(data) for name, data in _NATIVE_OWNERSHIP_UNIT_BYTES.items()},
        )
    material = synthetic_materials(attempt, monkeypatch)
    engine = material["engine"]["installed"]
    host = material["host_tools"]
    host["python"] = installed._file(attempt / "b/python.exe")
    host["git"] = {**host["python"], "path": str(attempt / "g/cmd/git.exe")}
    state = {"calls": [], "fault": None, "events": [], "setup_members": {}}

    def discover_engine(*, budget=None):
        current = (
            engine
            if state["fault"] != "engine"
            or not any(call.startswith("EXEC-") for call in state["calls"])
            else {"distributions": [], "startup": {"files": []}}
        )
        if budget is not None:
            startup = current["startup"]
            configuration = startup.get("pyvenv_configuration")
            if configuration is not None:
                node._take_budget(budget, configuration["size"])
            for _root in startup.get("site_roots", []):
                node._take_budget(budget)
            startup_paths = {row["path"] for row in startup["files"]}
            for row in startup["files"]:
                node._take_budget(budget, row["size"])
            site = Path(material["interpreter"]["site"])
            for distribution in current["distributions"]:
                roots = set()
                for row in distribution["files"]:
                    if row["path"] not in startup_paths:
                        node._take_budget(budget, row["size"])
                    path = Path(row["path"])
                    if path.is_relative_to(site):
                        first = path.relative_to(site).parts[0]
                        anchor = site / first
                        if first not in {".", ".."} and anchor.is_dir():
                            roots.add(anchor)
                for root in roots:
                    inventory = node._inventory(root)
                    node._take_budget(budget)
                    for row in inventory["entries"]:
                        if row["kind"] == "directory":
                            node._take_budget(budget)
        return current

    def discover_host(*, budget=None):
        if budget is not None:
            # Host accounting owns exact paths, not cross-domain inode aliases.
            paths = {row["path"]: row for row in host.values() if row is not None}
            for row in paths.values():
                node._take_budget(budget, row["size"])
        return host

    monkeypatch.setattr(node, "_engine", discover_engine)
    monkeypatch.setattr(node, "_host_tools", discover_host)
    monkeypatch.setattr(installed, "_materials", lambda: node._canonical(material))
    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))
    for name in ("TEMP", "TMP", "TMPDIR"):
        monkeypatch.setenv(name, str(workspace / ".tmp"))
    # Python caches gettempdir(); select the same real owned temp root that the
    # workflow environment supplies, keeping _run_directory's check unchanged.
    monkeypatch.setattr(tempfile, "tempdir", str(workspace / ".tmp"))
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    docs = _documents(level)
    attested, descriptor, admission = docs["AttestedSource"], docs["Descriptor"], docs["Admission"]
    attested["binding"].update(
        base_commit=base,
        subject_commit=subject,
        subject_tree=fixture_git(source_root, "rev-parse", "HEAD^{tree}"),
        policy_sha256=node.load_policy_bundle(source_root).sha256,
    )
    attested["attestation_head"] = subject
    admission["platform"].update(run_id=1, run_attempt=1, head_sha=subject)
    if branch is not None:
        attested["binding"]["branch"] = branch
        admission["platform"]["workflow_ref"] = "refs/heads/" + branch
    contract = {"kind": "synthetic-unregistered-kernel-contract", "verification_level": level}
    descriptor.update(
        source_tuple_sha256=node._sha(node._canonical(attested)),
        attestation_head=subject,
        execution_contract_sha256=node._sha(node._canonical(contract)),
    )
    admission["descriptor_sha256"] = node._sha(node._canonical(descriptor))
    initial = node_ci._ci_input_materials(source_root, payload, attested)
    admission["input_materials_sha256"] = node._sha(node._canonical(initial))
    admission["engine_content_sha256"] = node._sha(node._canonical(engine))
    for name, value in (
        ("source-tuple", attested),
        ("descriptor", descriptor),
        ("admission", admission),
        ("input-materials", initial),
        ("pair-materials", material),
    ):
        (attempt / "control" / (name + ".json")).write_bytes(node._canonical(value))
    pairs = kernel_parser_pairs(material, attempt) if level == "V2" else None
    if pairs is not None:
        pairs.update(
            admission_sha256=node._sha(node._canonical(admission)),
            engine_content_sha256=admission["engine_content_sha256"],
        )
    source_manifest = initial["source"]

    def coverage_outputs(checkout: Path, node_dir: Path) -> tuple[dict, dict]:
        reports, rows = {}, {}
        for row in source_manifest["files"]:
            name = row["path"]
            if not name.startswith("src/local/") or not name.endswith(".ts"):
                continue
            data = (checkout / name).read_bytes()
            absolute = str(checkout / name)
            reports[absolute] = report(absolute, [1])
            reports[absolute]["statementMap"]["0"]["end"]["column"] = len(
                data.decode().rstrip("\n")
            )
            rows[name] = {"sha256": node._sha(data), "lines": [1], "implicit_else": []}
        directory = node_dir / "coverage"
        directory.mkdir(exist_ok=True)
        (directory / "coverage-final.json").write_bytes(node._canonical(reports))
        summary = {name: {"lines": {"total": 1, "covered": 1, "skipped": 0}} for name in reports}
        summary["total"] = {"lines": {"total": len(reports), "covered": len(reports), "skipped": 0}}
        (directory / "coverage-summary.json").write_bytes(node._canonical(summary))
        return reports, catalog(rows)

    def process(argv, *, cwd, environment, timeout, output):
        name = output.name
        state["calls"].append(name)
        state["events"].append((name, tuple(argv), str(cwd), dict(environment), timeout))
        stdout = b"synthetic process protocol; no Node/native execution\n"
        if name in {"node", "npm"}:
            stdout = (("v" if name == "node" else "") + node.VERSIONS[name]).encode() + b"\n"
            if name == "node" and state["fault"] == "version":
                stdout = b"v0.0.0\n"
        elif name == "setup-clone":
            state["preclone_members"] = physical_members(attempt / "node")
            git_setup(
                source_root,
                environment,
                "clone",
                "--no-hardlinks",
                "--no-checkout",
                "--local",
                "--",
                str(source_root),
                str(attempt / "node/checkout"),
            )
        elif name == "setup-checkout":
            git_setup(
                cwd, environment, "-c", "core.autocrlf=false", "checkout", "--detach", subject
            )
        elif name == "EXEC-004":
            for relative in node._dist_paths(cwd, source_manifest):
                path = cwd / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic build artifact, never compiled\n")
        elif name == "EXEC-005":
            if native:
                native_ownership_cache(
                    SimpleNamespace(
                        root=cwd,
                        cs_sha=node.NATIVE_OWNERSHIP_INPUTS["scripts/windows-owned-launcher.cs"],
                    )
                )
            (cwd / ".runtime/no-zcode-p0p1/probe-test-tmp/live-fake-ci").mkdir(parents=True)
            (attempt / "node/tmp/synthetic-ci-one").mkdir()
        elif name == "EXEC-009":
            reports, _expected = coverage_outputs(cwd, output.parent.parent)
            product, _tests, _coverage, _root = product_fixture(cwd.parent)
            product["coverageMap"] = reports
            (output.parent.parent / "vitest.json").write_bytes(node._canonical(product))
        elif name == "EXEC-010":
            _reports, expected = coverage_outputs(cwd, output.parent.parent)
            (output.parent.parent / "expected-map.json").write_bytes(node._canonical(expected))
        receipt = _negative_process_original(node, output, argv, cwd, environment, stdout)
        receipt["timeout_seconds"] = timeout
        fault = state["fault"]
        if name == "node" and fault == "preparation_source":
            (source_root / "src/local/run.ts").write_bytes(b"changed during version probe\n")
        if name == "EXEC-004" and fault in {"nonzero", "cleanup", "eof"}:
            if fault == "nonzero":
                receipt["returncode"] = 17
            elif fault == "cleanup":
                receipt.update(returncode=None, cleanup="unknown", execution_error=True)
            else:
                receipt["receipt"]["stdout_eof"] = False
        if name == "EXEC-003" and fault in {"source", "protected", "dependencies"}:
            path = (
                source_root / "src/local/run.ts"
                if fault == "source"
                else attempt / "node/checkout/src/local/run.ts"
                if fault == "protected"
                else deps / "vitest/package.json"
            )
            path.write_bytes(b"controlled input drift\n")
        if name == "EXEC-006" and fault in {"native", "dist"}:
            path = (
                next((attempt / "node/checkout/.runtime/native-ownership").glob("*.exe"))
                if fault == "native"
                else next((attempt / "node/checkout/dist").rglob("*.js"))
            )
            path.write_bytes(b"self-consistent late output drift\n")
            if fault == "native":
                sidecar = path.with_name(path.name + ".json")
                value = json.loads(sidecar.read_bytes())
                value["executableHash"] = node._sha(path.read_bytes())
                sidecar.write_bytes(json.dumps(value, separators=(",", ":")).encode() + b"\n")
        (output / "receipt.json").write_bytes(node._canonical(receipt))
        if name in {"setup-clone", "setup-checkout"}:
            state["setup_members"][name] = physical_members(attempt / "node")
        return receipt

    def physical_members(root: Path) -> dict[str, int]:
        # Independent observations must not themselves enforce the production
        # cap; otherwise a post-write overflow could falsely look preempted.
        result = {}
        for directory, dirs, files in os.walk(root, followlinks=False):
            here = Path(directory)
            for name in dirs:
                result[(here / name).relative_to(root).as_posix()] = 0
            for name in files:
                path = here / name
                result[path.relative_to(root).as_posix()] = path.stat().st_size
        return result

    def git_setup(cwd: Path, environment: dict, *arguments: str) -> None:
        # The actual Git copy/checkout remains real. Honor the CI-only fixed
        # committer in its actual reflogs as well as the synthetic receipt.
        selected = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        selected.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        for name in ("GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
            if name in environment:
                selected[name] = environment[name]
        subprocess.run(
            ["git", "-c", "core.fsmonitor=false", *arguments],
            cwd=cwd,
            env=selected,
            capture_output=True,
            check=True,
            timeout=30,
        )

    monkeypatch.setattr(node, "_process", process)
    case = SimpleNamespace(
        workspace=workspace,
        source=source_root,
        payload=payload,
        attempt=attempt,
        admission=admission,
        attested=attested,
        descriptor=descriptor,
        contract=contract,
        material=material,
        state=state,
        pairs=pairs,
        level=level,
        native=native,
        initial=initial,
    )
    case.prepare = lambda: node._prepare_ci_materials_kernel(
        source_root,
        payload,
        attempt_root=attempt,
        admission=admission,
        source_tuple=attested,
        descriptor=descriptor,
    )
    case.execute = lambda prepared: node._execute_ci_node_kernel(
        source_root,
        "TASK-0001",
        attempt_root=attempt,
        admission=admission,
        source_tuple=attested,
        descriptor=descriptor,
        prepared=prepared,
        pairs=pairs,
    )
    return case


@pytest.fixture(scope="session")
def ci_recorded_seeds(
    tmp_path_factory: pytest.TempPathFactory, ci_source_seeds: dict, request: pytest.FixtureRequest
) -> dict:
    """One immutable real collector/writer result per tier, shared with replay."""
    # Pytest creates distinct FixtureDefs for a fixture imported by two test
    # modules. Its session stash keeps the one immutable input set common to
    # both definitions without caching any production reader or live identity.
    existing = request.config.stash.get(_CI_RECORDED_SEEDS, None)
    if existing is not None:
        return existing
    seeds = {}
    for level, native in (("V0", True), ("V1", False), ("V2", False)):
        root = tmp_path_factory.mktemp("c")
        with pytest.MonkeyPatch.context() as patch:
            case = ci_kernel_case.__wrapped__(
                root,
                tmp_path_factory,
                patch,
                SimpleNamespace(param=(level, native)),
                ci_source_seeds,
            )
            before = node._inventory(case.source)
            prepared = case.prepare()
            run = case.execute(prepared)
        seeds[level] = (case, prepared, run, before)
    request.config.stash[_CI_RECORDED_SEEDS] = seeds
    return seeds


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_private_kernels_collect_and_record_the_fixed_synthetic_sequence(
    ci_recorded_seeds: dict, level: str
):
    case, prepared, run, before = ci_recorded_seeds[level]
    assert run["failure"] is None
    count = 8 if case.level == "V0" else 10
    assert case.state["calls"] == [
        "node",
        "npm",
        "setup-clone",
        "setup-checkout",
        *[f"EXEC-{number:03d}" for number in range(1, count + 1)],
    ]
    assert node._inventory(case.source) == before
    assert run["inputs"]["engine"] == case.initial["engine"]
    assert run["environment"]["TMPDIR"] == str(case.attempt / "node/tmp")
    assert set(run["outputs"]) == {"build_dist", "dist", "fixtures", "node_inventory"}
    assert (run["coverage"] is not None) == (case.level != "V0")
    assert (run["product_tests"] is not None) == (case.level == "V2")
    assert (run["installed_mutation"] is not None) == (case.level == "V2")
    assert (case.attempt / "node/run.json").read_bytes() == node._canonical(run)
    assert_setup_within_forecast(case, run)


def assert_setup_within_forecast(case, run: dict) -> None:
    allocation = node._ci_clone_allocation(
        case.source,
        run["roots"]["original"],
        run["inputs"]["source"],
        run["inputs"]["prepared_dependencies"],
        run["environment"],
    )
    expected = dict(case.state["preclone_members"])
    for name, size in allocation.items():
        expected[name] = max(expected.get(name, 0), size)
        for parent in Path(name).parents:
            if str(parent) != ".":
                expected.setdefault(parent.as_posix(), 0)
    for phase, members in case.state["setup_members"].items():
        assert all(name in expected and size <= expected[name] for name, size in members.items()), (
            phase,
            {
                name: {"actual": size, "reserved": expected.get(name)}
                for name, size in members.items()
                if name not in expected or size > expected[name]
            },
        )
    assert run["environment"]["GIT_COMMITTER_NAME"] == "aiflow-ci"
    assert run["environment"]["GIT_COMMITTER_EMAIL"] == "aiflow-ci@invalid"
    assert (
        b"aiflow-ci <aiflow-ci@invalid>"
        in (case.attempt / "node/checkout/.git/logs/HEAD").read_bytes()
    )


@pytest.mark.parametrize("ci_kernel_case", [("V0", False, "codex/fixture#semi;")], indirect=True)
def test_clone_forecast_covers_a_valid_attached_branch_with_config_comment_characters(
    ci_kernel_case,
) -> None:
    case = ci_kernel_case
    branch = "codex/fixture#semi;"
    assert fixture_git(case.source, "symbolic-ref", "--short", "HEAD") == branch
    before = node._inventory(case.source)
    prepared = case.prepare()
    run = case.execute(prepared)
    assert run["failure"] is None
    assert node._inventory(case.source) == before
    assert case.attested["binding"]["branch"] == branch
    assert (
        fixture_git(
            case.attempt / "node/checkout", "config", "--local", "--get", f"branch.{branch}.merge"
        )
        == "refs/heads/" + branch
    )
    assert_setup_within_forecast(case, run)


@pytest.mark.parametrize(
    "fault,last",
    [
        ("nonzero", "EXEC-004"),
        ("cleanup", "EXEC-004"),
        ("eof", "EXEC-004"),
        ("source", "EXEC-003"),
        ("protected", "EXEC-003"),
        ("dependencies", "EXEC-003"),
        ("dist", "EXEC-006"),
        ("engine", "EXEC-008"),
    ],
)
def test_private_execution_retains_failed_prefix_and_never_continues(ci_kernel_case, fault, last):
    case = ci_kernel_case
    prepared = case.prepare()
    case.state["fault"] = fault
    run = case.execute(prepared)
    assert run["failure"] is not None
    assert case.state["calls"][-1] == last
    assert set(run["outputs"]) == (
        {"build_dist", "dist", "fixtures", "node_inventory"}
        if fault == "engine"
        else {"node_inventory"}
    )
    assert run["coverage"] is None and run["product_tests"] is None
    assert (case.attempt / "node/run.json").read_bytes() == node._canonical(run)


@pytest.mark.parametrize("ci_kernel_case", [("V0", True)], indirect=True)
def test_private_execution_rejects_a_self_consistent_native_replacement_after_first_seal(
    ci_kernel_case,
):
    case = ci_kernel_case
    prepared = case.prepare()
    case.state["fault"] = "native"
    run = case.execute(prepared)
    assert run["failure"] == "NODE_OUTPUT_INVALID"
    assert case.state["calls"][-1] == "EXEC-006"
    assert "fixtures" not in run["outputs"]


def test_node_role_cumulative_budget_is_enforced_before_copy_writes_exceed_it(
    ci_kernel_case, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A small finite cap measures the real .git/checkout/dependency write domain."""
    case = ci_kernel_case
    prepared = case.prepare()
    source_bytes = node._inventory(case.source)["total_bytes"]
    dependency_bytes = case.initial["dependencies"]["total_bytes"]
    limit = source_bytes + dependency_bytes - 1
    assert source_bytes < limit and dependency_bytes < limit
    assert source_bytes + case.initial["source"]["total_bytes"] + dependency_bytes > limit
    node_root = case.attempt / "node"
    over_limit_writes = []
    armed = []
    binding, process, copy = node._ci_input_binding, node._process, node._copy_tree

    def size_now() -> int:
        return sum(
            (Path(directory) / name).stat().st_size
            for directory, _dirs, names in os.walk(node_root, followlinks=False)
            for name in names
        )

    def bind_then_arm(*args, **kwargs):
        # Keep the complete admission/input-domain check real at its unchanged
        # production cap, then apply this finite cap to the following Node role.
        result = binding(*args, **kwargs)
        monkeypatch.setattr(node, "MAX_TOTAL_BYTES", limit)
        armed.append(True)
        return result

    def observe_process(*args, **kwargs):
        result = process(*args, **kwargs)
        if kwargs["output"].name in {"setup-clone", "setup-checkout"}:
            actual = size_now()
            if actual > limit:
                over_limit_writes.append((kwargs["output"].name, actual))
        return result

    def observe_copy(source, destination, inventory):
        result = copy(source, destination, inventory)
        if destination == node_root / "checkout/node_modules":
            actual = size_now()
            if actual > limit:
                over_limit_writes.append(("dependencies", actual))
        return result

    monkeypatch.setattr(node, "_ci_input_binding", bind_then_arm)
    monkeypatch.setattr(node, "_process", observe_process)
    monkeypatch.setattr(node, "_copy_tree", observe_copy)
    with pytest.raises(AiflowError):
        case.execute(prepared)
    assert armed, "the real admitted inputs must be checked before the finite Node cap is armed"
    assert not over_limit_writes, (
        f"Node originals were written past their cumulative cap: {over_limit_writes}"
    )


@pytest.mark.parametrize("limit,accepted", [(110, True), (109, False)])
def test_node_copy_reservation_combines_git_source_and_dependency_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: int, accepted: bool
) -> None:
    root = tmp_path / "node"
    (root / "checkout/.git/objects").mkdir(parents=True)
    (root / "checkout/.git/objects/synthetic").write_bytes(b"g" * 40)
    (root / "checkout/source.ts").write_bytes(b"s" * 30)
    before = node._inventory(root)
    monkeypatch.setattr(node, "MAX_TOTAL_BYTES", limit)
    with pure_guard(monkeypatch):
        if accepted:
            node._ci_node_copy_budget(root, {"checkout/node_modules/package/index.js": 40})
        else:
            with pytest.raises(AiflowError):
                node._ci_node_copy_budget(root, {"checkout/node_modules/package/index.js": 40})
    assert node._inventory(root) == before
    assert not (root / "checkout/node_modules").exists()


@pytest.mark.parametrize(
    "variant",
    ["workspace", "platform", "control", "input_digest", "head", "version", "preparation_source"],
)
def test_private_preparation_rejects_rebinding_or_drift_without_publishing_a_selection(
    ci_kernel_case, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    case = ci_kernel_case
    if variant == "workspace":
        monkeypatch.setenv("GITHUB_WORKSPACE", str(case.workspace / "other"))
    elif variant == "platform":
        case.admission["platform"]["run_attempt"] += 1
    elif variant in {"control", "input_digest"}:
        path = (
            case.attempt
            / "control"
            / ("descriptor.json" if variant == "control" else "input-materials.json")
        )
        path.write_bytes(path.read_bytes() + b"\n")
    elif variant == "head":
        fixture_git(case.source, "checkout", "--detach", case.attested["binding"]["base_commit"])
    else:
        case.state["fault"] = variant
    with pytest.raises(AiflowError):
        case.prepare()
    assert not (case.attempt / "control/prepared.json").exists()
    assert not (case.attempt / "control/source.json").exists()
    if variant not in {"version", "preparation_source"}:
        assert case.state["calls"] == []


def test_private_preparation_never_reuses_a_spent_selection(ci_kernel_case) -> None:
    case = ci_kernel_case
    prepared = case.prepare()
    calls = list(case.state["calls"])
    with pytest.raises(AiflowError):
        case.prepare()
    assert case.state["calls"] == calls
    assert (case.attempt / "control/prepared.json").read_bytes() == node._canonical(prepared)


def test_synthetic_fixture_does_not_change_the_production_byte_pins_or_registration() -> None:
    assert (
        node.NODE_V2_CONFIG_SHA256
        == "74bed4fc135f16dd29e85987c221ab2d877a778fa44e774dcc5dbc4a646654ed"
    )
    assert node.ISTANBUL_FILES == {
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
    assert node_ci.CI_CAPS_REGISTERED is False
    assert all(values == (0, 0, 0, 0, 0) for values in node_ci.CI_CAPS.values())


@pytest.mark.parametrize(
    "variant",
    [None, "unknown", "missing_role", "boolean_size", "zero_size", "digest", "noncanonical"],
)
def test_transport_json_selection_is_closed_bounded_and_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str | None
) -> None:
    path = tmp_path / "originals/control/selected.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{"fixture":true}')
    reference = {
        "ref": "control/selected.json",
        "size": path.stat().st_size,
        "sha256": node._sha(path.read_bytes()),
    }
    if variant == "unknown":
        reference["current"] = True
    elif variant == "missing_role":
        reference["ref"] = "selected.json"
    elif variant == "boolean_size":
        reference["size"] = True
    elif variant == "zero_size":
        reference["size"] = 0
    elif variant == "digest":
        reference["sha256"] = "0" * 64
    elif variant == "noncanonical":
        path.write_bytes(b'{"fixture": true}\n')
        reference.update(size=path.stat().st_size, sha256=node._sha(path.read_bytes()))
    with pure_guard(monkeypatch):
        if variant is None:
            assert node._ci_transport_ref(tmp_path, reference) == {"fixture": True}
        else:
            with pytest.raises(AiflowError):
                node._ci_transport_ref(tmp_path, reference)


@pytest.mark.parametrize("variant", [None, "members", "path", "hash"])
def test_prepared_manifest_selections_bind_the_fixed_seven_originals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str | None
) -> None:
    (tmp_path / "control").mkdir()
    names = ("source", "node", "npm", "dependencies", "engine", "host_tools", "preflight")
    refs, originals = {}, {}
    for key, name in zip(names, node.MANIFEST_NAMES, strict=True):
        data = node._canonical({"synthetic_role": key})
        (tmp_path / "control" / name).write_bytes(data)
        refs[key] = {"ref": "control/" + name, "size": len(data), "sha256": node._sha(data)}
        originals[name] = {"synthetic_role": key}
    if variant == "members":
        del refs["source"]
    elif variant == "path":
        refs["source"]["ref"] = "control/node.json"
    elif variant == "hash":
        refs["source"]["sha256"] = "0" * 64
    with pure_guard(monkeypatch):
        if variant is None:
            assert node._ci_manifests(tmp_path, {"manifests": refs}) == originals
        else:
            with pytest.raises(AiflowError):
                node._ci_manifests(tmp_path, {"manifests": refs})


@pytest.mark.parametrize(
    "variant",
    [
        "closed",
        "relative_root",
        "entry_budget",
        "nonobject",
        "identity",
        "member_fields",
        "bytes",
        "order",
        "total",
        "foreign_member",
    ],
)
def test_transport_role_rejects_unsafe_identity_membership_and_budgets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    root = tmp_path / "originals/source"
    root.mkdir(parents=True)
    (root / "a").write_bytes(b"public source\n")
    (root / "b").write_bytes(b"second source\n")
    manifest = {"id": "source", **node._inventory(root)}
    manifest["root"] = str(tmp_path / "absent/source")
    if variant == "closed":
        manifest["extra"] = None
    elif variant == "relative_root":
        manifest["root"] = "source"
    elif variant == "entry_budget":
        monkeypatch.setattr(node, "MAX_ENTRIES", 1)
    elif variant == "nonobject":
        manifest["entries"][0] = None
    elif variant == "identity":
        manifest["identity"]["inode"] = True
    elif variant == "member_fields":
        manifest["entries"][0]["unknown"] = None
    elif variant == "bytes":
        (root / "a").write_bytes(b"changed\n")
    elif variant == "order":
        manifest["entries"].reverse()
    elif variant == "total":
        manifest["total_bytes"] += 1
    elif variant == "foreign_member":
        (root / "foreign").write_bytes(b"not inventoried\n")
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        node._ci_verify_role(tmp_path, "source", manifest)


@pytest.mark.parametrize("variant", ["outside", "content", "identity"])
def test_inventory_producing_facts_cannot_be_rebound_to_another_retained_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    root = tmp_path / "role"
    root.mkdir()
    (root / "a").write_bytes(b"public source\n")
    original = node._inventory(root)
    role = {"id": "source", **deepcopy(original)}
    if variant == "outside":
        original["root"] = str(tmp_path / "outside")
    elif variant == "content":
        original["entries"][0]["sha256"] = "0" * 64
    else:
        original["identity"]["inode"] += 1
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        node._ci_inventory_in_role(original, role)


@pytest.mark.parametrize("variant", ["source_name", "boolean_attempt", "zero_run"])
def test_fixed_attempt_coordinates_reject_ambiguous_producing_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    root, platform = tmp_path / "source", {"run_id": 1, "run_attempt": 1}
    if variant == "source_name":
        root = tmp_path / "other"
    else:
        platform["run_id" if variant == "zero_run" else "run_attempt"] = (
            0 if variant == "zero_run" else True
        )
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        node._ci_attempt_coordinate(root, platform)


@pytest.mark.parametrize("variant", ["host", "binding"])
def test_private_kernel_coherence_rejects_unsupported_host_or_rebound_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    docs = _documents("V0")
    source_tuple, descriptor, admission = (
        docs["AttestedSource"],
        docs["Descriptor"],
        docs["Admission"],
    )
    descriptor["source_tuple_sha256"] = node._sha(node._canonical(source_tuple))
    if variant == "binding":
        descriptor["source_tuple_sha256"] = "0" * 64
    admission["descriptor_sha256"] = node._sha(node._canonical(descriptor))
    root = tmp_path / "source"
    attempt = node._ci_attempt_coordinate(root, admission["platform"])
    (attempt / "control").mkdir(parents=True)
    for name, value in (
        ("descriptor", descriptor),
        ("source-tuple", source_tuple),
        ("admission", admission),
    ):
        (attempt / "control" / (name + ".json")).write_bytes(node._canonical(value))
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    if variant == "host":
        monkeypatch.setattr(sys, "maxsize", 2**31 - 1)
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        node._ci_kernel_inputs(root, attempt, admission, source_tuple, descriptor)


@pytest.mark.parametrize("variant", ["prepared", "task", "pairs"])
def test_private_execution_rejects_foreign_selection_before_materials_or_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    docs = _documents("V0")
    attested, descriptor, admission = docs["AttestedSource"], docs["Descriptor"], docs["Admission"]
    descriptor["source_tuple_sha256"] = node._sha(node._canonical(attested))
    admission["descriptor_sha256"] = node._sha(node._canonical(descriptor))
    root = tmp_path / "source"
    attempt = node._ci_attempt_coordinate(root, admission["platform"])
    (attempt / "control").mkdir(parents=True)
    for name, value in (
        ("descriptor", descriptor),
        ("source-tuple", attested),
        ("admission", admission),
        ("prepared", docs["Prepared"]),
    ):
        (attempt / "control" / (name + ".json")).write_bytes(node._canonical(value))
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        node._execute_ci_node_kernel(
            root,
            "TASK-9999" if variant == "task" else "TASK-0001",
            attempt_root=attempt,
            admission=admission,
            source_tuple=attested,
            descriptor=descriptor,
            prepared={"foreign": True} if variant == "prepared" else docs["Prepared"],
            pairs={} if variant == "pairs" else None,
        )


def test_retained_process_receipt_requires_the_exact_canonical_wire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = tmp_path / "absent"
    receipt, streams, logs, argv, environment = receipt_input(old)
    root = tmp_path / "originals/node/raw/example"
    root.mkdir(parents=True)
    (root / "receipt.json").write_bytes(node._canonical(receipt) + b"\n")
    for name in streams:
        (root / (name + ".raw")).write_bytes(streams[name])
        (root / (name + ".log")).write_bytes(logs[name])
    with pure_guard(monkeypatch), pytest.raises(AiflowError, match="noncanonical"):
        node._ci_retained_receipt(
            tmp_path, "node", "raw/example", receipt, argv=argv, cwd=old, environment=environment
        )
