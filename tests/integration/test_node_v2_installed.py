"""Portable file/guard integration for closed installed-Node execution originals.

Retained task/Git files are real. The shared logical primitive fixture explicitly
records FIXTURE_NO_EXECUTION, and supplied positive facts isolate claim/service
guards only. No test here establishes an ordinary wheel, Job, product run or
successful end-to-end Node lifecycle. Those require independent real execution.
"""

from __future__ import annotations

# ruff: noqa: E402 -- Reuse only explicitly located helpers from this checkout.
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
_original_path = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "tests/unit"))
    from test_installed_mutation_transactions import (
        ACTOR,
        OS_PROCESS_APIS,
        TASK,
        LogicalRun,
        Model,
        _build_model_seed,
        action_file,
        retained_logical_run,
        snapshot_tree,
    )
    from test_node_v2_evidence import public_node_evidence
finally:
    sys.path[:] = _original_path

import aiflow.installed_mutations as installed
import aiflow.node_execution as node
import aiflow.process_runner as processes
from aiflow.errors import AiflowError
from aiflow.verification import VerificationContext

RUN = "IMUT-0123456789abcdef"
_SEED_ENGINE_MODULES = (
    "__init__.py",
    "policy.py",
    "verifier_service.py",
    "approval.py",
    "gate.py",
    "evidence.py",
    "errors.py",
    "installed_probe.py",
    "installed_mutations.py",
)


def _seed_manifest(root: Path) -> tuple[tuple[str, int, str], ...]:
    """Snapshot regular-file SHA-256 digests and reject link/reparse drift."""
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    entries: list[tuple[str, int, str]] = []
    for current_dir, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        current_path = Path(current_dir)
        for name in dirnames:
            entry = current_path / name
            info = entry.lstat()
            assert not stat.S_ISLNK(info.st_mode), f"seed symlink directory: {entry}"
            assert not getattr(info, "st_file_attributes", 0) & reparse_flag, (
                f"seed reparse directory: {entry}"
            )
            entries.append((entry.relative_to(root).as_posix() + "/", -1, "dir"))
        for name in filenames:
            entry = current_path / name
            info = entry.lstat()
            assert not stat.S_ISLNK(info.st_mode), f"seed symlink file: {entry}"
            assert not getattr(info, "st_file_attributes", 0) & reparse_flag, (
                f"seed reparse file: {entry}"
            )
            assert info.st_nlink == 1, f"seed hardlink file (st_nlink={info.st_nlink}): {entry}"
            entries.append(
                (
                    entry.relative_to(root).as_posix(),
                    info.st_size,
                    hashlib.sha256(entry.read_bytes()).hexdigest(),
                )
            )
    entries.sort()
    return tuple(entries)


@dataclass(frozen=True)
class _NodeV2Seed:
    root: Path
    engine_dir: Path
    base_dir: Path
    task_dir: Path
    inputs: installed.InstalledMutationInputs
    verifier_context: dict
    material: dict
    material_bytes: bytes
    reference: installed.InstalledMutationReference
    action_digest: str
    git_audit_ref: str
    git_audit_logs_rel: dict[str, dict[str, object]]
    baseline_manifest: tuple[tuple[str, int, str], ...]

    def assert_untouched(self) -> None:
        assert _seed_manifest(self.root) == self.baseline_manifest, (
            "shared module-scoped node-v2 seed was modified"
        )


def _collect_root_metadata(root: Path, owned_run: Path) -> list[dict[str, object]]:
    """Collect real metadata identities without spawning git rev-parse per clone."""
    rows: list[dict[str, object]] = []
    pending = [root]
    while pending:
        path = pending.pop()
        if path == owned_run:
            continue
        identity = node._metadata_identity(path)
        rows.append({"path": str(path), "identity": identity})
        if stat.S_ISDIR(identity["mode"]):
            with os.scandir(path) as children:
                pending.extend(Path(child.path) for child in children)
    rows.sort(key=lambda row: str(row["path"]).encode("utf-8"))
    return rows


@pytest.fixture(scope="module")
def _node_v2_seed(tmp_path_factory: pytest.TempPathFactory) -> Iterator[_NodeV2Seed]:
    seed_root = tmp_path_factory.mktemp("node-v2-seed")
    prefix = seed_root / "engine"
    base = seed_root / "base"
    site = prefix / "Lib/site-packages/aiflow"
    site.mkdir(parents=True)
    for name in _SEED_ENGINE_MODULES:
        shutil.copyfile(ROOT / "src/aiflow" / name, site / name)
    (prefix / "Scripts").mkdir()
    base.mkdir()
    for path in (prefix / "Scripts/python.exe", base / "python.exe", base / "python311.dll"):
        path.write_bytes(b"public fixture, not an executable\n")
    interpreter = dict(
        executable=installed._file(prefix / "Scripts/python.exe"),
        base_executable=installed._file(base / "python.exe"),
        runtime=installed._file(base / "python311.dll"),
        prefix=str(prefix),
        site=str(site.parent),
        base_prefix=str(base),
        implementation="cpython",
        version=[3, 11, 0],
        cache_tag="cpython-311",
    )
    material = dict(
        kind=installed.ACTION_TYPE,
        version=1,
        engine={"installed": {}, "closure": node._inventory(prefix)},
        interpreter=interpreter,
        host_tools={},
        probes=installed._probe_contract(),
        operators={},
    )
    material_bytes = node._canonical(material)

    task_dir = seed_root / "task"
    model_seed_dir, verifier_context = _build_model_seed("node-v2")
    try:
        shutil.copytree(Path(model_seed_dir.name) / "task", task_dir, copy_function=shutil.copyfile)
    finally:
        model_seed_dir.cleanup()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(installed, "_materials", lambda: material_bytes)
        mp.setattr(node, "_windows_root", lambda: seed_root / "public-windows-role")
        inputs = installed.prepare_installed_mutations(task_dir, TASK, verifier_actor=ACTOR)
        seed_model = Model(
            task_dir,
            inputs,
            deepcopy(verifier_context),
            material,
            installed.record_installed_mutations,
            node._process,
            installed._materials,
        )
        action_file(seed_model)
        seed_logical = retained_logical_run(seed_model)

    run_doc = json.loads(seed_logical.path.read_bytes())
    git_audit = run_doc["before"]["git_audit"]
    seed_git_dir = Path(git_audit["git"])
    assert seed_git_dir == task_dir / ".git" and Path(git_audit["common"]) == seed_git_dir
    git_audit_logs_rel = {
        Path(path_str).relative_to(seed_git_dir).as_posix(): value
        for path_str, value in git_audit["logs"].items()
    }
    seed = _NodeV2Seed(
        root=seed_root,
        engine_dir=prefix,
        base_dir=base,
        task_dir=task_dir,
        inputs=inputs,
        verifier_context=verifier_context,
        material=material,
        material_bytes=material_bytes,
        reference=seed_logical.reference,
        action_digest=str(run_doc["action"]["digest"]),
        git_audit_ref=str(git_audit["ref"]),
        git_audit_logs_rel=git_audit_logs_rel,
        baseline_manifest=_seed_manifest(seed_root),
    )
    yield seed
    seed.assert_untouched()


@pytest.fixture
def model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    _node_v2_seed: _NodeV2Seed,
) -> Iterator[Model]:
    if getattr(request, "param", None) != "node-v2":
        raise ValueError(f"Unsupported model variant: {getattr(request, 'param', None)!r}")
    _node_v2_seed.assert_untouched()
    recorder, process_writer, material_collector = (
        installed.record_installed_mutations,
        node._process,
        installed._materials,
    )
    attempts: list[str] = []

    def no_execution(*args, **kwargs):
        attempts.append("record-or-probe")
        raise AssertionError("portable logic fixture must not record or launch a probe")

    actual_popen = subprocess.Popen

    class GitOnlyPopen(actual_popen):
        # Keep Popen a class: Windows asyncio subclasses it during cold imports.
        def __init__(self, argv, *args, **kwargs):
            if not isinstance(argv, (tuple, list)) or Path(argv[0]).name.casefold() not in {
                "git",
                "git.exe",
            }:
                no_execution(argv)
            super().__init__(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", GitOnlyPopen)
    monkeypatch.setattr(installed, "record_installed_mutations", no_execution)
    for name in OS_PROCESS_APIS:
        if hasattr(os, name):
            monkeypatch.setattr(os, name, no_execution)
    for module, names in (
        (node, ("run_node_process", "_process")),
        (processes, ("run_node_process", "run_execution")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, no_execution)
    monkeypatch.setattr(installed, "_materials", lambda: _node_v2_seed.material_bytes)
    monkeypatch.setattr(node, "_windows_root", lambda: tmp_path / "public-windows-role")

    root = tmp_path / "task"
    shutil.copytree(_node_v2_seed.task_dir, root, copy_function=shutil.copyfile)
    yield Model(
        root,
        _node_v2_seed.inputs,
        deepcopy(_node_v2_seed.verifier_context),
        deepcopy(_node_v2_seed.material),
        recorder,
        process_writer,
        material_collector,
    )
    assert not attempts, "a caught launch attempt must not make a logical test pass"
    _node_v2_seed.assert_untouched()


@pytest.fixture
def logical_run(model: Model, _node_v2_seed: _NodeV2Seed) -> LogicalRun:
    """Clone the module-scoped closed failure record with bound local paths and identities."""
    root = model.root
    logs_dir = root / ".ai/tasks" / TASK / "logs"
    receipt_path = logs_dir / f"installed-action-use-{_node_v2_seed.action_digest}.json"
    claim_path = logs_dir / f"installed-action-launch-{_node_v2_seed.action_digest}.json"
    receipt_identity = node._identity(node._safe_info(receipt_path))

    claim_doc = json.loads(claim_path.read_bytes())
    claim_doc["receipt_identity"] = receipt_identity
    claim_bytes = node._canonical(claim_doc)
    claim_path.write_bytes(claim_bytes)
    claim_identity = node._identity(node._safe_info(claim_path))

    events_path = root / ".ai/tasks" / TASK / "events.jsonl"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    events[-1]["payload"]["receipt_device"] = receipt_identity["device"]
    events[-1]["payload"]["receipt_inode"] = receipt_identity["inode"]
    events_path.write_bytes(
        "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in events
        ).encode("utf-8")
    )

    run_dir = logs_dir / f"IMUT-{'0' * 16}"
    run_path = run_dir / "run.json"
    metadata = _collect_root_metadata(root, run_dir)
    root_identity = node._identity(node._safe_info(root, directory=True))
    git_dir_str = str(root / ".git")
    git_audit = {
        "git": git_dir_str,
        "common": git_dir_str,
        "ref": _node_v2_seed.git_audit_ref,
        "logs": {
            str(root / ".git" / rel): value
            for rel, value in _node_v2_seed.git_audit_logs_rel.items()
        },
    }

    run_doc = json.loads(run_path.read_bytes())
    run_doc["action"]["receipt"]["path"] = str(receipt_path)
    run_doc["action"]["receipt"]["identity"] = receipt_identity
    run_doc["action"]["claim"]["path"] = str(claim_path)
    run_doc["action"]["claim"]["size"] = len(claim_bytes)
    run_doc["action"]["claim"]["sha256"] = node._sha(claim_bytes)
    run_doc["action"]["claim"]["identity"] = claim_identity
    for snapshot_key in ("before", "after"):
        snapshot = run_doc[snapshot_key]
        snapshot["identity"] = root_identity
        snapshot["git"]["git_directory"] = git_dir_str
        for row in snapshot["files"]:
            row["identity"] = node._identity(node._safe_info(root / row["path"]))
        snapshot["events"] = events
        snapshot["metadata"] = metadata
        snapshot["git_audit"] = git_audit
    raw_run = node._canonical(run_doc)
    run_path.write_bytes(raw_run)

    reference = installed.InstalledMutationReference(
        _node_v2_seed.reference.ref, len(raw_run), node._sha(raw_run)
    )
    completion_path = run_dir / "completion.json"
    completion_doc = json.loads(completion_path.read_bytes())
    completion_doc["reference"] = asdict(reference)
    completion_path.write_bytes(node._canonical(completion_doc))
    return LogicalRun(model, run_path, reference)


@pytest.fixture
def tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Keep genuine ledger/context paths short on the supported Windows host."""
    return tmp_path_factory.mktemp("n")


def forbid_processes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    attempts: list[str] = []

    def forbidden(*_args, **_kwargs):
        attempts.append("process")
        raise AssertionError("file/guard integration attempted a process")

    monkeypatch.setattr(node, "_process", forbidden)
    monkeypatch.setattr(node, "run_node_process", forbidden)
    return attempts


def output_tree(root: Path, *, level: str = "V2") -> tuple[Path, SimpleNamespace]:
    directory = root / "node"
    directory.mkdir()
    for name in ("raw", "home", "tmp", "cache", "checkout"):
        (directory / name).mkdir()
    for name in ("user.npmrc", "global.npmrc", "source-manifest.json", "run.json"):
        (directory / name).write_bytes(b"{}" if name.endswith(".json") else b"")
    for execution in ("setup-clone", "setup-checkout", "synthetic-stage"):
        stage = directory / "raw" / execution
        stage.mkdir()
        for name in ("stdout.raw", "stderr.raw", "stdout.log", "stderr.log", "receipt.json"):
            # Deliberately no fabricated Job receipt or assertion of execution.
            (stage / name).write_bytes(
                b'{"synthetic_only":true}' if name.endswith(".json") else b""
            )
    if level in {"V1", "V2"}:
        for name in ("coverage", "domain-materials"):
            (directory / name).mkdir()
        for name in ("expected-map.json", "vitest.json"):
            (directory / name).write_bytes(b"{}")
        (directory / "source.diff").write_bytes(b"bounded synthetic source diff\n")
        (directory / "coverage/coverage-final.json").write_bytes(b"{}")
        (directory / "domain-materials/zero.json").write_bytes(b"{}")
    return directory, SimpleNamespace(executions=[SimpleNamespace(execution_id="synthetic-stage")])


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_complete_owned_node_inventory_retains_files_and_empty_directories_without_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, level: str
) -> None:
    directory, plan = output_tree(tmp_path, level=level)
    before = snapshot_tree(directory)
    attempts = forbid_processes(monkeypatch)
    result = node._node_inventory(directory, level, plan)
    paths = {row["path"]: row for row in result}
    assert paths["cache"] == {"path": "cache", "kind": "directory"}
    assert paths["raw/synthetic-stage/receipt.json"] == {
        "path": "raw/synthetic-stage/receipt.json",
        "kind": "file",
        "size": len(b'{"synthetic_only":true}'),
        "sha256": hashlib.sha256(b'{"synthetic_only":true}').hexdigest(),
    }
    assert "run.json" not in paths
    assert [row["path"] for row in result] == sorted(paths, key=lambda value: value.encode("utf8"))
    assert snapshot_tree(directory) == before and attempts == []


def test_self_exclusion_is_only_the_run_manifest_and_other_content_or_membership_remains_bound(
    tmp_path: Path,
) -> None:
    directory, plan = output_tree(tmp_path)
    original = node._node_inventory(directory, "V2", plan)
    (directory / "run.json").write_bytes(b"different self-referenced manifest bytes")
    assert node._node_inventory(directory, "V2", plan) == original
    (directory / "vitest.json").write_bytes(b"[]")
    assert node._node_inventory(directory, "V2", plan) != original
    (directory / "vitest.json").write_bytes(b"{}")
    (directory / "cache/retained-cache").write_bytes(b"owned cache bytes")
    changed = node._node_inventory(directory, "V2", plan)
    assert {row["path"] for row in changed} - {row["path"] for row in original} == {
        "cache/retained-cache"
    }


@pytest.mark.parametrize(
    "fault", ["unknown_top", "unknown_raw_execution", "extra_raw_member", "missing_raw_member"]
)
def test_unknown_outputs_and_incomplete_raw_original_groups_are_rejected(
    tmp_path: Path, fault: str
) -> None:
    directory, plan = output_tree(tmp_path)
    if fault == "unknown_top":
        (directory / "unclaimed-output.json").write_bytes(b"{}")
    elif fault == "unknown_raw_execution":
        (directory / "raw/unplanned").mkdir()
    elif fault == "extra_raw_member":
        (directory / "raw/synthetic-stage/unknown").write_bytes(b"x")
    else:
        (directory / "raw/synthetic-stage/receipt.json").unlink()
    with pytest.raises(AiflowError):
        node._node_inventory(directory, "V2", plan)


@pytest.mark.parametrize(
    "role", ["coverage", "expected-map.json", "vitest.json", "domain-materials"]
)
def test_revision2_lower_level_cannot_admit_coverage_only_roles_as_v0(
    tmp_path: Path, role: str
) -> None:
    directory, plan = output_tree(tmp_path, level="V0")
    if "." in role:
        (directory / role).write_bytes(b"{}")
    else:
        (directory / role).mkdir()
    with pytest.raises(AiflowError):
        node._node_inventory(directory, "V0", plan)


def test_owned_originals_cannot_be_hard_link_aliases(tmp_path: Path) -> None:
    directory, plan = output_tree(tmp_path)
    os.link(directory / "vitest.json", tmp_path / "alias.json")
    with pytest.raises(AiflowError):
        node._node_inventory(directory, "V2", plan)


def test_a_symbolic_link_cannot_enter_a_closed_output_tree(tmp_path: Path) -> None:
    directory, plan = output_tree(tmp_path)
    target = tmp_path / "external-owned-fixture"
    target.write_bytes(b"public owned link fixture")
    link = directory / "cache/link"
    try:
        link.symlink_to(target)
    except OSError as error:
        pytest.skip(f"Host does not allow creating the synthetic symlink: {error.errno}")
    with pytest.raises(AiflowError):
        node._node_inventory(directory, "V2", plan)


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_installed_bridge_replays_real_failure_originals_truthfully_without_a_process(
    logical_run,
) -> None:
    root, reference = logical_run.model.root, logical_run.reference
    binding, _bundle = node._binding(root, TASK)
    current, facts = node._installed_for_node(
        root,
        TASK,
        reference,
        verifier_actor=ACTOR,
        binding=binding,
        manifests={"engine.json": {}, "host-tools.json": {}},
    )
    assert current.reference == reference and current.inputs == logical_run.model.inputs
    assert not facts.passed and not facts.all_killed
    assert facts.reason_codes, "FIXTURE_NO_EXECUTION must not become successful mutation evidence"


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize(
    "fault",
    ["wrong_actor", "wrong_task", "missing_completion", "changed_run", "changed_completion"],
)
def test_installed_node_bridge_rejects_foreign_or_damaged_real_originals(
    logical_run, fault: str
) -> None:
    root, reference = logical_run.model.root, logical_run.reference
    task, actor = TASK, ACTOR
    if fault == "wrong_actor":
        actor = "another-verifier"
    elif fault == "wrong_task":
        task = "TASK-0002"
    elif fault == "missing_completion":
        (logical_run.path.parent / "completion.json").unlink()
    elif fault == "changed_run":
        logical_run.path.write_bytes(logical_run.path.read_bytes() + b"\n")
    else:
        path = logical_run.path.parent / "completion.json"
        value = json.loads(path.read_bytes())
        value["failure"] = None
        path.write_bytes(node._canonical(value))
    with pytest.raises(AiflowError):
        node._installed_for_node(root, task, reference, verifier_actor=actor)


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize(
    "field",
    [
        "repository_id",
        "branch",
        "base_commit",
        "subject_commit",
        "subject_tree",
        "spec_sha256",
        "policy_sha256",
        "classification_input_sha256",
    ],
)
def test_node_binding_must_match_the_current_installed_original(logical_run, field: str) -> None:
    root, reference = logical_run.model.root, logical_run.reference
    binding, _bundle = node._binding(root, TASK)
    binding[field] = "foreign-bound-value"
    with pytest.raises(AiflowError) as caught:
        node._installed_for_node(root, TASK, reference, binding=binding)
    assert caught.value.code == "NODE_BINDING_STALE"


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize("role", ["engine.json", "host-tools.json"])
def test_node_and_installed_materials_cannot_be_substituted_even_with_valid_task_binding(
    logical_run, role: str
) -> None:
    manifests = {"engine.json": {}, "host-tools.json": {}}
    manifests[role] = {"foreign": True}
    with pytest.raises(AiflowError):
        node._installed_for_node(
            logical_run.model.root, TASK, logical_run.reference, manifests=manifests
        )


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize(
    "fault", ["extra_parent", "missing_pair", "extra_phase", "missing_context"]
)
def test_installed_parent_roles_are_closed_over_real_failure_originals(
    logical_run, fault: str
) -> None:
    run = logical_run.path.parent
    if fault == "extra_parent":
        (run / "sibling-output").mkdir()
    elif fault == "missing_pair":
        (run / "0/b").rmdir()
        (run / "0/m").rmdir()
        (run / "0").rmdir()
    elif fault == "extra_phase":
        (run / "0/other").mkdir()
    else:
        (run / "context.json").unlink()
    with pytest.raises(AiflowError):
        installed._validate_run_children(logical_run.model.root, logical_run.reference)


def known_claim_facts(monkeypatch: pytest.MonkeyPatch, logical_run):
    """Supply completed mutation facts only to isolate exclusive Node-role claim."""
    current = installed.InstalledMutationCurrent(
        logical_run.model.inputs, logical_run.reference, b"{}", ()
    )
    facts = installed.InstalledMutationFacts(
        True, True, tuple((probe, "killed") for probe in installed.PROBE_IDS), ()
    )
    calls = []

    def collected(root, task, reference, **kwargs):
        calls.append((root, task, reference, kwargs))
        return current, facts

    monkeypatch.setattr(node, "_installed_for_node", collected)
    return current, facts, calls


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_claim_reserves_exactly_one_real_empty_node_directory_before_any_execution(
    logical_run, monkeypatch: pytest.MonkeyPatch
) -> None:
    _current, _facts, calls = known_claim_facts(monkeypatch, logical_run)
    directory = logical_run.path.parent / "node"
    identity = node.claim_node_v2_run(
        logical_run.model.root, TASK, reference=logical_run.reference, verifier_actor=ACTOR
    )
    assert directory.is_dir() and not list(directory.iterdir())
    assert identity == node._identity(directory.lstat())
    assert len(calls) == 1 and calls[0][2] is logical_run.reference
    assert calls[0][3]["verifier_actor"] == ACTOR
    before = snapshot_tree(logical_run.model.root)
    with pytest.raises(AiflowError):
        node.claim_node_v2_run(
            logical_run.model.root, TASK, reference=logical_run.reference, verifier_actor=ACTOR
        )
    assert snapshot_tree(logical_run.model.root) == before


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize("existing", ["node", "evidence.json"])
def test_claim_never_reuses_an_existing_node_role_or_pre_archive(
    logical_run, monkeypatch: pytest.MonkeyPatch, existing: str
) -> None:
    known_claim_facts(monkeypatch, logical_run)
    path = logical_run.path.parent / existing
    if existing == "node":
        path.mkdir()
    else:
        path.write_bytes(b"immutable pre archive fixture")
    before = snapshot_tree(logical_run.model.root)
    with pytest.raises(AiflowError):
        node.claim_node_v2_run(
            logical_run.model.root, TASK, reference=logical_run.reference, verifier_actor=ACTOR
        )
    assert snapshot_tree(logical_run.model.root) == before


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_a_real_incomplete_mutation_original_cannot_claim_a_node_directory(logical_run) -> None:
    with pytest.raises(AiflowError) as caught:
        node.claim_node_v2_run(
            logical_run.model.root, TASK, reference=logical_run.reference, verifier_actor=ACTOR
        )
    assert caught.value.code == "NODE_MUTATIONS_INVALID"
    assert not (logical_run.path.parent / "node").exists()


def execution_case(root: Path, monkeypatch: pytest.MonkeyPatch):
    """Known preparation/host facts; the executor's role/phase guards stay real."""
    run = root / ".ai/tasks" / TASK / "logs" / RUN
    directory = run / "node"
    directory.mkdir(parents=True)
    reference = installed.InstalledMutationReference(
        f".ai/tasks/{TASK}/logs/{RUN}/run.json", 1, "a" * 64
    )
    binding = {"profile": {"id": "agent-bridge-node", "revision": 2}}
    bundle = SimpleNamespace(sha256="a" * 64, policy_version="3.2.0")
    monkeypatch.setattr(node, "_binding", lambda *_args: (binding, bundle))
    monkeypatch.setattr(node, "_load_prepared", lambda *_args: ({}, {}))
    monkeypatch.setattr(node, "_check_materials", lambda *_args: None)
    context = VerificationContext(root, TASK, "b" * 40, "c" * 40, sys.executable, RUN)
    facts = SimpleNamespace(mode="local", verification_level="V2", run_dir=run)
    return directory, reference, bundle, context, facts


@pytest.mark.parametrize(
    "fault",
    [
        "mode",
        "level",
        "policy_digest",
        "missing_reference",
        "missing_claim",
        "foreign_reference",
        "wrong_run_id",
        "wrong_run_directory",
        "changed_claim_identity",
        "nonempty_node",
    ],
)
def test_execution_refuses_invalid_role_or_mode_before_creating_outputs_or_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    directory, reference, bundle, context, facts = execution_case(tmp_path, monkeypatch)
    identity = node._identity(directory.lstat())
    kwargs = {"installed_reference": reference, "node_claim_identity": identity}
    if fault == "mode":
        facts.mode = "ci"
    elif fault == "level":
        facts.verification_level = "V3"
    elif fault == "policy_digest":
        bundle = SimpleNamespace(sha256="f" * 64)
    elif fault == "missing_reference":
        kwargs["installed_reference"] = None
    elif fault == "missing_claim":
        kwargs["node_claim_identity"] = None
    elif fault == "foreign_reference":
        kwargs["installed_reference"] = installed.InstalledMutationReference(
            reference.ref.replace(TASK, "TASK-0002"), 1, "a" * 64
        )
    elif fault == "wrong_run_id":
        context = VerificationContext(tmp_path, TASK, "b" * 40, "c" * 40, sys.executable, "other")
    elif fault == "wrong_run_directory":
        facts.run_dir = directory
    elif fault == "changed_claim_identity":
        kwargs["node_claim_identity"] = {**identity, "inode": identity["inode"] + 1}
    else:
        (directory / "unexpected").write_bytes(b"not empty")
    before = snapshot_tree(tmp_path)
    attempts = forbid_processes(monkeypatch)
    with pytest.raises(AiflowError):
        node.execute_node_verification(
            tmp_path,
            TASK,
            material_sha256="d" * 64,
            context=context,
            bundle=bundle,
            facts=facts,
            **kwargs,
        )
    assert snapshot_tree(tmp_path) == before and not attempts


def service_boundaries(logical_run, monkeypatch: pytest.MonkeyPatch):
    """Isolate service sequencing, not the original-material validator or executor.

    Real task/Git/review/context and archive operations remain active. The
    deliberately synthetic executor/recheck results are known boundary facts;
    they cannot be cited as execution, mutation or original-replay acceptance.
    """
    import aiflow.verification_service as service
    from aiflow.task_service import read_task_record_strict

    root = logical_run.model.root
    run = logical_run.path.parent
    selector = "d" * 64
    _current, mutation_facts, installed_calls = known_claim_facts(monkeypatch, logical_run)
    order: list[str] = []
    executions: list[dict] = []
    replays: list[str] = []
    claim = node.claim_node_v2_run

    def material_boundary(*_args):
        assert (
            root
            / ".ai/tasks"
            / TASK
            / "verifier-contexts"
            / (logical_run.model.inputs.verifier_context_sha256 + ".json")
        ).is_file()
        order.append("materials")
        return {}, {}

    def claim_boundary(*args, **kwargs):
        assert read_task_record_strict(root, TASK).task["current_state"] == "IMPLEMENTING"
        value = claim(*args, **kwargs)
        order.append("claim")
        return value

    def execution_boundary(_root, task, *, material_sha256, context, bundle, facts, **kwargs):
        assert _root == root and task == TASK and material_sha256 == selector
        assert read_task_record_strict(root, TASK).task["current_state"] == "VERIFYING"
        assert kwargs["installed_reference"] == logical_run.reference
        assert kwargs["node_claim_identity"] == node._identity((run / "node").lstat())
        assert not list((run / "node").iterdir())
        order.append("execute-after-start")
        executions.append(kwargs)
        evidence = public_node_evidence(root)
        for field in (
            "task_id",
            "repository_id",
            "branch",
            "base_commit",
            "subject_commit",
            "spec_sha256",
            "policy_sha256",
            "classification_input_sha256",
            "verification_level",
        ):
            evidence[field] = getattr(facts, field)
        evidence["decision_unit_ids"] = list(facts.decision_unit_ids)
        evidence["generated_at"] = facts.generated_at
        evidence["reproduce_command"] = list(facts.reproduce_command)
        evidence["node_binding"]["subject_tree"] = logical_run.model.inputs.subject_tree
        evidence["node_binding"]["run"]["ref"] = f"logs/{run.name}/node/run.json"
        evidence["node_binding"]["product_tests"]["report"]["ref"] = (
            f"logs/{run.name}/node/vitest.json"
        )
        for check in evidence["checks"]:
            for execution in check["executions"]:
                for stream in ("stdout", "stderr"):
                    for ref in ("raw_ref", "log_ref"):
                        execution[stream][ref] = execution[stream][ref].replace(RUN, run.name)
        evidence["installed_mutation"] = {
            "reference": asdict(logical_run.reference),
            "inputs_sha256": logical_run.model.inputs.sha256,
            "results": [list(row) for row in mutation_facts.results],
        }
        evidence["node_binding_sha256"] = node._sha(node._canonical(evidence["node_binding"]))
        return evidence

    def original_boundary(_root, task, evidence):
        assert _root == root and task == TASK
        phase = str(evidence["phase"])
        order.append("known-original-boundary:" + phase)
        replays.append(phase)
        return node.NodeEvidenceFacts(
            True,
            True,
            (),
            node._sha(node._canonical(evidence)),
            evidence["node_binding"]["materials_sha256"],
            run.name,
            mutation_facts,
        )

    monkeypatch.setattr(
        node, "precheck_node_materials", lambda *_args: order.append("precheck-materials")
    )
    monkeypatch.setattr(node, "_load_prepared", material_boundary)
    monkeypatch.setattr(node, "claim_node_v2_run", claim_boundary)
    monkeypatch.setattr(node, "execute_node_verification", execution_boundary)
    monkeypatch.setattr(node, "recheck_node_evidence", original_boundary)
    return SimpleNamespace(
        service=service,
        root=root,
        run=run,
        selector=selector,
        order=order,
        executions=executions,
        replays=replays,
        installed_calls=installed_calls,
        mutation_facts=mutation_facts,
    )


def begin_service(case):
    return case.service.verify_task(
        case.root,
        TASK,
        actor=ACTOR,
        node_materials_sha256=case.selector,
        node_installed_mutation_run=case.run.name,
    )


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_service_claims_before_start_and_finalizes_same_snapshot_without_reexecution(
    logical_run, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow.review_service import build_review_context, record_review
    from aiflow.storage import read_task_json
    from aiflow.task_service import read_task_record_strict

    case = service_boundaries(logical_run, monkeypatch)
    result = begin_service(case)
    assert result.conclusion == "passed"
    assert (
        read_task_record_strict(case.root, TASK).task["current_state"] == "WAITING_FOR_FINAL_REVIEW"
    )
    assert case.order[:4] == ["precheck-materials", "materials", "claim", "execute-after-start"]
    assert case.order[4] == "known-original-boundary:pre_implementation_review"
    archive = case.run / "evidence.json"
    archive_bytes = archive.read_bytes()
    pre = json.loads(archive_bytes)
    assert archive_bytes == node._canonical(pre)
    assert pre["phase"] == "pre_implementation_review" and set(pre["review_refs"]) == {"design"}
    assert read_task_json(case.root, TASK, "evidence.json", contract_name="evidence") == pre

    context = build_review_context(case.root, TASK, "implementation")
    record_review(
        case.root,
        TASK,
        actor="synthetic-implementation-reviewer",
        input_path={
            "schema_version": "1.0",
            "review_id": "REV-0002",
            "review_stage": "implementation",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "context_sha256": context["context_sha256"],
            "outcome": "APPROVE",
            "summary": "Synthetic service-boundary fixture only, not runtime acceptance",
            "findings": [],
        },
    )
    before_wrong_actor = snapshot_tree(case.root)
    with pytest.raises(AiflowError) as caught:
        case.service.verify_task(case.root, TASK, actor="alternate-verifier", finalize=True)
    assert caught.value.code == "VERIFY_FINALIZE_ACTOR_STALE"
    assert snapshot_tree(case.root) == before_wrong_actor

    final = case.service.verify_task(case.root, TASK, actor=ACTOR, finalize=True)
    assert final.conclusion == "passed"
    assert len(case.executions) == 1 and len(case.installed_calls) == 2
    current = read_task_json(case.root, TASK, "evidence.json", contract_name="evidence")
    assert current["phase"] == "final"
    assert current["verification_snapshot_sha256"] == pre["verification_snapshot_sha256"]
    assert current["review_refs"]["implementation"]["review_id"] == "REV-0002"
    assert archive.read_bytes() == archive_bytes


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_service_does_not_overwrite_a_preexisting_immutable_archive(
    logical_run, monkeypatch
) -> None:
    from aiflow.task_service import read_task_record_strict

    case = service_boundaries(logical_run, monkeypatch)
    archive = case.run / "evidence.json"
    archive.write_bytes(b"immutable preexisting archive fixture")
    original = archive.read_bytes()
    with pytest.raises(AiflowError):
        begin_service(case)
    assert archive.read_bytes() == original and case.executions == []
    assert not (case.run / "node").exists()
    assert read_task_record_strict(case.root, TASK).task["current_state"] == "IMPLEMENTING"


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_service_refuses_to_create_verifier_context_after_primitive_recording(
    logical_run, monkeypatch
) -> None:
    from aiflow.task_service import read_task_record_strict

    case = service_boundaries(logical_run, monkeypatch)
    context = (
        case.root
        / ".ai/tasks"
        / TASK
        / "verifier-contexts"
        / (logical_run.model.inputs.verifier_context_sha256 + ".json")
    )
    context.unlink()
    with pytest.raises(AiflowError):
        begin_service(case)
    assert not context.exists() and not (case.run / "node").exists()
    assert case.executions == [] and case.order == ["precheck-materials"]
    assert read_task_record_strict(case.root, TASK).task["current_state"] == "IMPLEMENTING"


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_service_does_not_save_success_when_its_original_boundary_is_stale(
    logical_run, monkeypatch
) -> None:
    from aiflow.task_service import read_task_record_strict

    case = service_boundaries(logical_run, monkeypatch)
    monkeypatch.setattr(
        node,
        "recheck_node_evidence",
        lambda *_args: node.NodeEvidenceFacts(
            False, False, ("KNOWN_STALE_BOUNDARY",), None, None, None
        ),
    )
    with pytest.raises(AiflowError) as caught:
        begin_service(case)
    assert caught.value.code == "NODE_EVIDENCE_STALE"
    assert (case.run / "node").is_dir() and not (case.run / "evidence.json").exists()
    assert not (case.root / ".ai/tasks" / TASK / "evidence.json").exists()
    assert len(case.executions) == 1
    assert read_task_record_strict(case.root, TASK).task["current_state"] == "VERIFYING"
