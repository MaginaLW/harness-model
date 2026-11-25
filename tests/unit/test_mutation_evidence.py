"""Synthetic, zero-worktree tests for Chapter 11.4 mutation evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import aiflow.mutation_evidence as evidence
from aiflow import mutation_materials, mutation_protocol
from aiflow.errors import AiflowError, ContractError, StorageError
from aiflow.mutation_manifest import MutationManifest, load_mutation_manifest
from aiflow.mutation_process import ProcessLifecycle
from aiflow.mutation_runner import MutationProbe, MutationRun
from tests.integration.test_begin_close_commands import commit_all, run_git

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PRODUCTION_PREFLIGHT = evidence._preflight_targeted_mutation
_CACHED_MANIFEST: MutationManifest | None = None
_CACHED_MATERIALS: dict[str, bytes] | None = None
_MATERIAL_SEED_BASE_DIR: Path | None = None
_MATERIAL_SEED_ENTRY: tuple[Path, str] | None = None


def _lifecycle(report: bytes, code: int | None) -> ProcessLifecycle | None:
    if code is None:
        return None
    return ProcessLifecycle(
        created_suspended=True,
        assigned=True,
        initial_membership=True,
        resumed=True,
        job_empty=True,
        stdout_eof=True,
        stderr_eof=True,
        closed=True,
        terminate_requested=False,
        returncode=code,
        report_sha256=evidence._sha256_bytes(report),
    )


def _run(
    manifest,
    *,
    reason=None,
    unchanged=True,
    baseline=0,
    mutant=1,
    timed_out=False,
    probe_reason=None,
) -> MutationRun:
    def report(mutation_id: str, digest: str, failure: bool) -> bytes:
        expected_case, exception, anchor, semantic = mutation_protocol.SIGNATURES[mutation_id]
        cases = []
        for case in mutation_protocol.CASES[mutation_id]:
            failed = failure and case == expected_case
            cases.append(
                {
                    "case": case,
                    "setup": "passed",
                    "call": "failed" if failed else "passed",
                    "teardown": "passed",
                    "failure": {"exception": exception, "anchor": anchor, "semantic": semantic}
                    if failed
                    else None,
                }
            )
        return mutation_protocol.encode_report(
            {
                "protocol": "1.0",
                "mutation_id": mutation_id,
                "python": "3.11",
                "pytest": "9.1.1",
                "platform": "windows",
                "cases": cases,
                "imports": {"target_sha256": digest, "reference_ok": True},
                "complete": True,
            }
        )

    probes = []
    for item in manifest.mutations:
        original = f"synthetic {item.target}\n".encode()
        baseline_hash = evidence._sha256_bytes(original)
        mutant_hash = evidence._sha256_bytes(original + b"synthetic mutant\n")
        baseline_report = report(item.mutation_id, baseline_hash, False)
        mutant_report = report(item.mutation_id, mutant_hash, mutant == 1)
        probes.append(
            MutationProbe(
                item.mutation_id,
                baseline,
                mutant,
                timed_out,
                1,
                probe_reason,
                baseline_report,
                mutant_report,
                baseline_hash,
                mutant_hash,
                baseline_lifecycle=_lifecycle(baseline_report, baseline),
                mutant_lifecycle=_lifecycle(mutant_report, mutant),
            )
        )
    return MutationRun(
        manifest.manifest_id,
        "a" * 40,
        tuple(probes),
        unchanged,
        reason,
    )


def _synthetic_materials(manifest) -> dict[str, bytes]:
    source_root = PROJECT_ROOT
    paths = {item.target for item in manifest.mutations} | {
        ".ai/mutations/phase-02-critical-manifest.json",
        ".ai/policy/permissions.yaml",
        ".ai/schemas/mutation-evidence.schema.json",
        ".ai/templates/mutation-evidence.json",
        ".gitattributes",
        "pyproject.toml",
        "uv.lock",
        "tests/conftest.py",
        "tests/integration/test_begin_close_commands.py",
        "tests/fixtures/contracts/valid/evidence-v2.json",
        "tests/unit/test_policy.py",
        "tests/integration/test_verify_command.py",
        "tests/integration/test_mutation_manifest_contract.py",
        "tests/unit/test_evidence.py",
        *(
            f"src/aiflow/{name}"
            for name in (
                "__init__.py",
                "mutation_evidence.py",
                "mutation_manifest.py",
                "mutation_materials.py",
                "mutation_process.py",
                "process_runner.py",
                "mutation_protocol.py",
                "mutation_runner.py",
                "mutation_reporter.py",
            )
        ),
    }
    materials = {name: (source_root / name).read_bytes().replace(b"\r\n", b"\n") for name in paths}
    for item in manifest.mutations:
        materials[item.target] = f"synthetic {item.target}\n".encode()
    return materials


def _cached_manifest() -> MutationManifest:
    global _CACHED_MANIFEST
    if _CACHED_MANIFEST is None:
        _CACHED_MANIFEST = load_mutation_manifest(PROJECT_ROOT)
    return _CACHED_MANIFEST


def _cached_materials() -> dict[str, bytes]:
    global _CACHED_MATERIALS
    if _CACHED_MATERIALS is None:
        _CACHED_MATERIALS = _synthetic_materials(_cached_manifest())
    return _CACHED_MATERIALS


def _seed_tree_sha256(root: Path) -> str:
    """Digest every directory, file byte, and link count inside a shared module seed."""
    hasher = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise AssertionError(f"shared seed contains link: {path}")
        if stat.S_ISDIR(info.st_mode):
            hasher.update(b"D\0" + relative + b"\0")
        elif stat.S_ISREG(info.st_mode):
            assert info.st_nlink == 1, f"shared seed file has hardlink: {path}"
            hasher.update(b"F\0" + relative + b"\0" + path.read_bytes() + b"\0")
        else:
            raise AssertionError(f"unexpected seed entry: {path}")
    return hasher.hexdigest()


@pytest.fixture(scope="module", autouse=True)
def _material_seed_guard(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    global _MATERIAL_SEED_BASE_DIR, _MATERIAL_SEED_ENTRY
    _MATERIAL_SEED_BASE_DIR = tmp_path_factory.mktemp("mutation-evidence-seeds")
    _MATERIAL_SEED_ENTRY = None
    try:
        yield
        if _MATERIAL_SEED_ENTRY is not None:
            seed_path, expected = _MATERIAL_SEED_ENTRY
            assert _seed_tree_sha256(seed_path) == expected, (
                "Module material seed was mutated during test execution"
            )
    finally:
        _MATERIAL_SEED_ENTRY = None
        _MATERIAL_SEED_BASE_DIR = None


def _ensure_material_seed() -> Path:
    global _MATERIAL_SEED_ENTRY
    if _MATERIAL_SEED_ENTRY is None:
        assert _MATERIAL_SEED_BASE_DIR is not None
        seed_dir = _MATERIAL_SEED_BASE_DIR / "materials"
        seed_dir.mkdir(parents=True, exist_ok=True)
        for name, content in _cached_materials().items():
            destination = seed_dir / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        _MATERIAL_SEED_ENTRY = (seed_dir, _seed_tree_sha256(seed_dir))
    return _MATERIAL_SEED_ENTRY[0]


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    run: MutationRun,
    *,
    authorized: bool = True,
):
    root = tmp_path
    shutil.copytree(
        _ensure_material_seed(),
        root,
        dirs_exist_ok=True,
        copy_function=shutil.copyfile,
    )
    (root / ".ai" / "tasks" / "TASK-0014").mkdir(parents=True, exist_ok=True)
    manifest = _cached_manifest()
    task = {
        "task_id": "TASK-0014",
        "current_state": "IMPLEMENTING",
        "repository_id": "b85e5a53-4935-4436-bdbc-c26a241bfae8",
        "branch": "main",
        "base_commit": "b" * 40,
        "subject_commit": "a" * 40,
        "frozen_spec_sha256": "c" * 64,
    }
    classification = {"classification_input_sha256": "d" * 64}
    calls = {"runner": 0}
    materials = dict(_cached_materials())
    monkeypatch.setattr(evidence, "subject_materials", lambda *_: materials)
    monkeypatch.setattr(
        evidence, "mutation_bytes", lambda _item, data: data + b"synthetic mutant\n"
    )
    monkeypatch.setattr(evidence, "_validate_bindings", lambda *_: (task, classification, "e" * 64))
    monkeypatch.setattr(evidence, "_load_manifest", lambda _: manifest)
    monkeypatch.setattr(evidence, "loaded_engine_matches", lambda *_: True)
    monkeypatch.setattr(evidence, "_preflight_targeted_mutation", lambda *_: None)
    monkeypatch.setattr(evidence, "_verify_recorded_action", lambda *_: None)
    monkeypatch.setattr(evidence, "_utc_now", lambda: datetime(2000, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(evidence, "_nonce_hex", lambda: "0" * 16)
    if authorized:
        task_directory = root / ".ai" / "tasks" / "TASK-0014"
        receipt = task_directory / f"action-use-{'a' * 64}.md"
        receipt.write_text("authorized\n", encoding="utf-8")
        action_path = task_directory / "action-v2-targeted-mutation-test.json"
        action_path.write_text("{}\n", encoding="utf-8")
        receipt_stat = receipt.stat()
        action_use = evidence.MutationActionUse(
            "a" * 64,
            receipt,
            action_path,
            "DU-001",
            "c" * 64,
            "e" * 64,
            "b" * 40,
            "d" * 64,
            receipt_stat.st_dev,
            receipt_stat.st_ino,
        )

        def fake_consume(*_args, check_inputs):
            check_inputs()
            return action_use

        monkeypatch.setattr(evidence, "_consume_targeted_mutation_action", fake_consume)
        monkeypatch.setattr(
            evidence,
            "_revalidate_targeted_mutation_action",
            lambda *_args: (task, classification, "e" * 64),
        )
        monkeypatch.setattr(
            evidence,
            "_complete_targeted_mutation_action",
            lambda *_args: None,
        )
        monkeypatch.setattr(
            evidence, "_issue_runner_authorization", lambda *_args, **_kwargs: object()
        )

    def runner(*_args, **_kwargs):
        calls["runner"] += 1
        return run

    monkeypatch.setattr(evidence, "run_targeted_mutations", runner)
    return root, manifest, calls


def test_public_recorder_rejects_missing_action_before_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest), authorized=False)

    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)

    assert caught.value.code == "ACTION_STATE_INVALID"
    assert calls == {"runner": 0}


def _resign(value: dict) -> None:
    unsigned = {key: item for key, item in value.items() if key != "mutation_evidence_sha256"}
    value["mutation_evidence_sha256"] = evidence._sha256_bytes(evidence._canonical_bytes(unsigned))


def _v2_projection(artifact: dict, artifact_ref: str) -> dict[str, object]:
    return {
        "targeted_mutation": {
            "evidence_ref": artifact_ref,
            "mutation_evidence_sha256": artifact["mutation_evidence_sha256"],
            "manifest_ref": artifact["manifest_ref"],
            "results": [
                {
                    "mutation_id": item["mutation_id"],
                    "outcome": item["outcome"],
                    "log_ref": item["log_ref"],
                }
                for item in artifact["results"]
            ],
        }
    }


@pytest.mark.parametrize("case", ["not-list", "not-object", "invalid-contract"])
def test_action_approval_inventory_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    value: object = {} if case == "not-list" else [None]
    if case == "invalid-contract":
        value = [{}]
        monkeypatch.setattr(
            evidence,
            "require_valid_contract",
            lambda *_args: (_ for _ in ()).throw(ContractError("invalid", code="CONTRACT_INVALID")),
        )
    monkeypatch.setattr(evidence, "read_task_json", lambda *_args, **_kwargs: value)

    with pytest.raises(ContractError) as caught:
        evidence._action_approvals(tmp_path, "TASK-0014")

    assert caught.value.code == "ACTION_APPROVAL_INVALID"


def test_action_consumption_history_fails_closed_for_read_or_digest_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        evidence,
        "read_task_record_strict",
        lambda *_args: (_ for _ in ()).throw(
            StorageError("unreadable", code="STATE_EVENT_LOG_READ_FAILED")
        ),
    )
    with pytest.raises(ContractError) as caught:
        evidence._used_action_digests(tmp_path, "TASK-0014")
    assert caught.value.code == "ACTION_APPROVAL_INVALID"

    monkeypatch.setattr(
        evidence,
        "read_task_record_strict",
        lambda *_args: SimpleNamespace(
            events=[
                {
                    "event_type": "approval_recorded",
                    "payload": {
                        "approval_type": "action",
                        "action_status": "consumed",
                        "action_sha256": "invalid",
                    },
                }
            ]
        ),
    )
    with pytest.raises(ContractError) as caught:
        evidence._used_action_digests(tmp_path, "TASK-0014")
    assert caught.value.code == "ACTION_APPROVAL_INVALID"


@pytest.mark.parametrize(
    "payload, duplicate",
    [
        ({"receipt_ref": None}, False),
        ({"receipt_ref": 1}, False),
        ({"receipt_device": None}, False),
        ({"receipt_device": -1}, False),
        ({"receipt_device": True}, False),
        ({"receipt_inode": None}, False),
        ({"receipt_inode": -1}, False),
        ({"receipt_inode": True}, False),
        ({}, True),
    ],
    ids=(
        "missing-receipt-ref",
        "invalid-receipt-ref",
        "missing-receipt-device",
        "negative-receipt-device",
        "boolean-receipt-device",
        "missing-receipt-inode",
        "negative-receipt-inode",
        "boolean-receipt-inode",
        "duplicate-authoritative-digest",
    ),
)
def test_action_consumption_ledger_rejects_invalid_receipt_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    duplicate: bool,
) -> None:
    digest = "a" * 64
    valid = {
        "approval_type": "action",
        "action_status": "consumed",
        "action_sha256": digest,
        "receipt_ref": f".ai/tasks/TASK-0014/action-use-{digest}.md",
        "receipt_device": 1,
        "receipt_inode": 2,
    }
    invalid = {**valid, **payload}
    events = [{"event_type": "approval_recorded", "payload": invalid}]
    if duplicate:
        events.append({"event_type": "approval_recorded", "payload": valid})
    monkeypatch.setattr(
        evidence, "read_task_record_strict", lambda *_args: SimpleNamespace(events=events)
    )

    with pytest.raises(ContractError) as caught:
        evidence._used_action_digests(tmp_path, "TASK-0014")

    assert caught.value.code == "ACTION_APPROVAL_INVALID"


@pytest.mark.parametrize("identity_part", ["receipt_ref", "receipt_device", "receipt_inode"])
def test_action_revalidation_rejects_ledger_receipt_identity_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, identity_part: str
) -> None:
    digest = "a" * 64
    receipt = tmp_path / f"action-use-{digest}.md"
    receipt.write_text("authorized\n", encoding="utf-8")
    receipt_stat = receipt.stat()
    action_path = tmp_path / "action-v2-targeted-mutation-test.json"
    action_path.write_text("{}\n", encoding="utf-8")
    action = {"value": "bound"}
    action_use = evidence.MutationActionUse(
        digest,
        receipt,
        action_path,
        "DU-001",
        "b" * 64,
        "c" * 64,
        "d" * 40,
        "e" * 64,
        receipt_stat.st_dev,
        receipt_stat.st_ino,
    )
    task = {
        "current_state": "VERIFYING",
        "frozen_spec_sha256": action_use.spec_sha256,
        "base_commit": action_use.base_commit,
    }
    classification = {"classification_input_sha256": action_use.classification_input_sha256}
    ledger_identity: tuple[str, int, int] = (
        receipt.relative_to(tmp_path).as_posix(),
        receipt_stat.st_dev,
        receipt_stat.st_ino,
    )
    mismatched = list(ledger_identity)
    index = {"receipt_ref": 0, "receipt_device": 1, "receipt_inode": 2}[identity_part]
    mismatched[index] = "other-receipt.md" if index == 0 else int(mismatched[index]) + 1

    monkeypatch.setattr(
        evidence,
        "_validate_bindings",
        lambda *_args: (task, classification, action_use.policy_sha256),
    )
    monkeypatch.setattr(evidence, "_require_no_pending_approval", lambda *_args: None)
    monkeypatch.setattr(evidence, "_require_action_task_facts", lambda *_args: {})
    monkeypatch.setattr(
        evidence, "_used_action_digests", lambda *_args: {digest: tuple(mismatched)}
    )
    monkeypatch.setattr(
        evidence, "_normalized_current_action", lambda *_args, **_kwargs: (action, "DU-001")
    )

    with pytest.raises(ContractError) as caught:
        evidence._revalidate_targeted_mutation_action(tmp_path, "TASK-0014", "f" * 40, action_use)

    assert caught.value.code == "ACTION_BINDING_STALE"


def test_pending_approval_inspection_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task_directory = tmp_path / "TASK-0014"
    task_directory.mkdir()
    monkeypatch.setattr(evidence, "resolve_task_path", lambda *_args: task_directory)
    original_lstat = Path.lstat

    def fail_marker_lstat(self: Path):
        if self.name == evidence.APPROVAL_MARKER:
            raise OSError("marker unavailable")
        return original_lstat(self)

    monkeypatch.setattr(Path, "lstat", fail_marker_lstat)
    with pytest.raises(ContractError) as caught:
        evidence._require_no_pending_approval(tmp_path, "TASK-0014")

    assert caught.value.code == "ACTION_APPROVAL_PENDING"


def test_posix_action_lock_adapter_uses_flock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []
    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_UN=2,
        flock=lambda _descriptor, operation: calls.append(operation),
    )
    monkeypatch.setattr(evidence.os, "name", "posix")
    monkeypatch.setattr(evidence.importlib, "import_module", lambda _name: fake_fcntl)
    path = tmp_path / "lock"
    descriptor = evidence.os.open(path, evidence.os.O_CREAT | evidence.os.O_RDWR)
    try:
        evidence._lock_descriptor(descriptor)
        evidence._unlock_descriptor(descriptor)
    finally:
        evidence.os.close(descriptor)

    assert calls == [fake_fcntl.LOCK_EX, fake_fcntl.LOCK_UN]


def test_windows_action_lock_adapter_uses_msvcrt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[int, int, int]] = []
    fake_msvcrt = SimpleNamespace(
        LK_LOCK=1,
        LK_UNLCK=2,
        locking=lambda descriptor, operation, length: calls.append((descriptor, operation, length)),
    )
    monkeypatch.setattr(evidence.os, "name", "nt")
    monkeypatch.setattr(evidence.importlib, "import_module", lambda _name: fake_msvcrt)
    path = tmp_path / "lock"
    descriptor = evidence.os.open(path, evidence.os.O_CREAT | evidence.os.O_RDWR)
    try:
        evidence._lock_descriptor(descriptor)
        evidence._unlock_descriptor(descriptor)
    finally:
        evidence.os.close(descriptor)

    assert calls == [
        (descriptor, fake_msvcrt.LK_LOCK, 1),
        (descriptor, fake_msvcrt.LK_UNLCK, 1),
    ]


def test_action_lock_reservation_error_is_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_directory = tmp_path / "logs"
    monkeypatch.setattr(evidence, "resolve_task_path", lambda *_args: lock_directory)
    monkeypatch.setattr(
        evidence.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("lock unavailable")),
    )

    with pytest.raises(ContractError) as caught:
        with evidence._locked_action_consumption(tmp_path, "TASK-0014"):
            pass

    assert caught.value.code == "ACTION_RECEIPT_WRITE_FAILED"


@pytest.mark.parametrize(
    ("projection", "recorded", "expected"),
    [
        (
            {"unexpected": True},
            evidence.MutationEvidenceArtifact("record", "ref", "a" * 64, ()),
            "MUTATION_EVIDENCE_PROJECTION_INVALID",
        ),
        ({}, None, "MUTATION_EVIDENCE_MISSING"),
        (
            {
                "targeted_mutation": {
                    "evidence_ref": "ref",
                    "mutation_evidence_sha256": "a" * 64,
                }
            },
            None,
            "MUTATION_EVIDENCE_PROJECTION_INVALID",
        ),
    ],
)
def test_v2_consumer_rejects_incomplete_projection_before_loader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    projection: dict[str, object],
    recorded: evidence.MutationEvidenceArtifact | None,
    expected: str,
) -> None:
    monkeypatch.setattr(
        evidence,
        "load_targeted_mutation_evidence",
        lambda *_args: (_ for _ in ()).throw(AssertionError("loader must not run")),
    )

    facts = evidence.consume_targeted_mutation_evidence(
        tmp_path,
        "TASK-0014",
        projection,
        recorded_artifact=recorded,
    )

    assert facts.passed is False
    assert facts.reason_code == expected


def test_v2_consumer_uses_only_current_loader_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    receipt = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    artifact = evidence.load_targeted_mutation_evidence(root, "TASK-0014", receipt.evidence_ref)

    facts = evidence.consume_targeted_mutation_evidence(
        root, "TASK-0014", _v2_projection(artifact, receipt.evidence_ref)
    )

    assert facts.passed is True
    assert facts.reason_code is None
    assert facts.results == tuple(
        _v2_projection(artifact, receipt.evidence_ref)["targeted_mutation"]["results"]
    )


@pytest.mark.parametrize("tamper", ["missing", "digest", "projection", "survived"])
def test_v2_consumer_fails_closed_for_missing_or_non_killed_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(
        tmp_path, monkeypatch, _run(manifest, mutant=0 if tamper == "survived" else 1)
    )
    receipt = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    artifact = evidence.load_targeted_mutation_evidence(root, "TASK-0014", receipt.evidence_ref)
    projection = _v2_projection(artifact, receipt.evidence_ref)
    mutation = projection["targeted_mutation"]
    assert isinstance(mutation, dict)
    if tamper == "missing":
        mutation.pop("evidence_ref")
    elif tamper == "digest":
        mutation["mutation_evidence_sha256"] = "0" * 64
    elif tamper == "projection":
        mutation["results"] = []

    facts = evidence.consume_targeted_mutation_evidence(root, "TASK-0014", projection)

    assert facts.passed is False
    assert facts.reason_code in {
        "MUTATION_EVIDENCE_MISSING",
        "MUTATION_EVIDENCE_PROJECTION_INVALID",
        "MUTATION_EVIDENCE_NOT_KILLED",
    }


def test_record_and_public_loader_round_trip_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    loaded = evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    assert calls == {"runner": 1}
    assert artifact.record_id == "MUTRUN-20000101T000000Z-0000000000000000"
    assert artifact.log_refs == tuple(item["log_ref"] for item in loaded["results"])
    assert loaded["uncovered_mutation_ids"] == []
    with pytest.raises(FrozenInstanceError):
        artifact.record_id = "changed"  # type: ignore[misc]

    assert loaded["schema_version"] == "2.0"
    first_log = json.loads((root / artifact.log_refs[0]).read_bytes())
    assert first_log["baseline_report"] and first_log["mutant_report"]


@pytest.mark.parametrize(
    ("baseline", "mutant", "reason", "unchanged", "timed_out", "probe_reason", "expected"),
    [
        (0, 1, None, True, False, None, "killed"),
        (0, 0, None, True, False, None, "survived"),
        (0, -9, None, True, False, None, "unverified"),
        (0, 3221225781, None, True, False, None, "unverified"),
        (1, 1, None, True, False, None, "unverified"),
        (None, None, None, True, False, None, "unverified"),
        (0, 1, "CLEANUP", True, False, None, "unverified"),
        (0, 1, None, False, False, None, "unverified"),
        (0, 1, None, True, True, None, "unverified"),
        (0, 1, None, True, False, "INFRA", "unverified"),
    ],
)
def test_record_derives_closed_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    baseline,
    mutant,
    reason,
    unchanged,
    timed_out,
    probe_reason,
    expected,
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(
        tmp_path,
        monkeypatch,
        _run(
            manifest,
            baseline=baseline,
            mutant=mutant,
            reason=reason,
            unchanged=unchanged,
            timed_out=timed_out,
            probe_reason=probe_reason,
        ),
    )
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    loaded = evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    assert {item["outcome"] for item in loaded["results"]} == {expected}
    assert loaded["uncovered_mutation_ids"] == (
        [] if expected == "killed" else [item.mutation_id for item in manifest.mutations]
    )


@pytest.mark.parametrize("kind", ["missing", "duplicate", "reorder"])
def test_record_rejects_noncanonical_runner_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    manifest = _cached_manifest()
    run = _run(manifest)
    probes = list(run.probes)
    if kind == "missing":
        probes.pop()
    elif kind == "duplicate":
        probes[-1] = probes[0]
    else:
        probes.reverse()
    root, _, _ = _prepare(
        tmp_path,
        monkeypatch,
        MutationRun(run.manifest_id, run.subject_commit, tuple(probes), True, None),
    )
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"


@pytest.mark.parametrize(
    "tamper",
    [
        "digest",
        "outcome",
        "uncovered",
        "manifest",
        "runner",
        "log_missing",
        "log_content",
        "log_hash",
        "evidence_duplicate_key",
        "log_duplicate_key",
        "record_time",
    ],
)
def test_loader_fails_closed_for_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    path = root / artifact.evidence_ref
    value = json.loads(path.read_text(encoding="utf-8"))
    if tamper == "evidence_duplicate_key":
        content = path.read_text(encoding="utf-8")
        path.write_text(
            content.replace(
                '"schema_version": "2.0",',
                '"schema_version": "2.0",\n  "schema_version": "2.0",',
                1,
            ),
            encoding="utf-8",
        )
    elif tamper == "digest":
        value["branch"] = "other"
    elif tamper == "outcome":
        value["results"][0]["outcome"] = "survived"
        _resign(value)
    elif tamper == "uncovered":
        value["uncovered_mutation_ids"] = ["MUT-V2-001"]
        _resign(value)
    elif tamper == "manifest":
        value["manifest_sha256"] = "0" * 64
        _resign(value)
    elif tamper == "runner":
        value["runner_source_sha256"] = "0" * 64
        _resign(value)
    elif tamper == "record_time":
        value["generated_at"] = "2000-01-02T00:00:00Z"
        _resign(value)
    else:
        log = root / value["results"][0]["log_ref"]
        if tamper == "log_missing":
            log.unlink()
        elif tamper == "log_content":
            log.write_text('{"x":1}', encoding="utf-8")
        elif tamper == "log_duplicate_key":
            content = log.read_text(encoding="utf-8")
            log.write_text(
                content.replace(
                    '"mutation_id": "MUT-V2-001",',
                    '"mutation_id": "MUT-V2-001",\n  "mutation_id": "MUT-V2-001",',
                    1,
                ),
                encoding="utf-8",
            )
            value["results"][0]["log_sha256"] = evidence._source_sha256(log)
            _resign(value)
        else:
            value["results"][0]["log_sha256"] = "0" * 64
            _resign(value)
    if tamper != "evidence_duplicate_key":
        path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ContractError):
        evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)


def test_collision_and_symlink_fail_before_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest))
    logs = root / ".ai/tasks/TASK-0014/logs"
    logs.mkdir(parents=True)
    for number in range(3):
        (logs / f"MUTRUN-20000101T000000Z-{number:016x}").mkdir()
    values = iter(f"{number:016x}" for number in range(3))
    monkeypatch.setattr(evidence, "_nonce_hex", lambda: next(values))
    with pytest.raises(ContractError):
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert calls == {"runner": 0}
    with pytest.raises(ContractError):
        evidence._relative_path("../escape", root=root)


def test_log_root_symlink_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest))
    target = root / "outside"
    target.mkdir()
    logs = root / ".ai/tasks/TASK-0014/logs"
    try:
        logs.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows test host")
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_PATH_INVALID"
    assert calls == {"runner": 0}


def test_partial_write_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest))
    original = evidence._write_new_json
    writes = {"count": 0}

    def fail_after_first(path, value):
        writes["count"] += 1
        original(path, value)
        if writes["count"] == 1:
            raise ContractError("write", code="MUTATION_EVIDENCE_WRITE_FAILED")

    monkeypatch.setattr(evidence, "_write_new_json", fail_after_first)
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_WRITE_FAILED"
    assert calls == {"runner": 1}


def test_lexical_symlink_escape_is_rejected_without_platform_symlink_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.is_symlink

    def fake_is_symlink(path: Path) -> bool:
        return path.name == "logs" or original(path)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    with pytest.raises(ContractError) as caught:
        evidence._relative_path(
            ".ai/tasks/TASK-0014/logs/MUTRUN-20000101T000000Z-0000000000000000/"
            "targeted-mutation/evidence.json",
            root=tmp_path,
        )
    assert caught.value.code == "MUTATION_EVIDENCE_PATH_ESCAPE"


def test_create_new_publish_is_immutable(tmp_path: Path) -> None:
    target = tmp_path / "record.json"
    evidence._write_new_json(target, {"version": 1})
    original = target.read_bytes()

    with pytest.raises(ContractError) as caught:
        evidence._write_new_json(target, {"version": 2})

    assert caught.value.code == "MUTATION_EVIDENCE_IMMUTABLE_CONFLICT"
    assert target.read_bytes() == original


@pytest.mark.parametrize(
    ("clock", "nonce"),
    [
        (datetime(2000, 1, 1), "0" * 16),
        (datetime(2000, 1, 1, tzinfo=timezone.utc), "not-a-nonce"),
    ],
)
def test_invalid_clock_or_nonce_fails_before_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: datetime, nonce: str
) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest))
    monkeypatch.setattr(evidence, "_utc_now", lambda: clock)
    monkeypatch.setattr(evidence, "_nonce_hex", lambda: nonce)

    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)

    assert caught.value.code == "MUTATION_EVIDENCE_ID_FAILED"
    assert calls == {"runner": 0}


def test_binding_introspection_errors_are_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        evidence,
        "read_task_record_strict",
        lambda *_: (_ for _ in ()).throw(AiflowError("bad task")),
    )
    with pytest.raises(ContractError) as caught:
        evidence._validate_bindings(tmp_path, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_BINDING_STALE"

    record = SimpleNamespace(
        task={
            "subject_commit": "a" * 40,
            "repository_id": "repo",
            "branch": "main",
            "base_commit": "b" * 40,
            "allowed_scope": ["src/**"],
        },
        events=(),
    )
    monkeypatch.setattr(evidence, "read_task_record_strict", lambda *_: record)
    monkeypatch.setattr(
        evidence,
        "evaluate_verification_git_context",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AiflowError("bad git")),
    )
    with pytest.raises(ContractError) as caught:
        evidence._validate_bindings(tmp_path, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_SUBJECT_INVALID"


def test_bindings_accept_only_current_governance_and_an_audited_subject_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# current spec\n", encoding="utf-8")
    task = {
        "repository_id": "b85e5a53-4935-4436-bdbc-c26a241bfae8",
        "branch": "main",
        "base_commit": "b" * 40,
        "subject_commit": "a" * 40,
        "frozen_spec_sha256": evidence.specification_digest("# current spec\n"),
        "allowed_scope": ["src/**"],
        "decision_units": [],
    }
    record = SimpleNamespace(task=task, events=({"event_type": "subject_commit_synchronized"},))
    classification = {
        "base_commit": "b" * 40,
        "subject_commit": "9" * 40,
        "policy_sha256": "e" * 64,
        "classification_input_sha256": "d" * 64,
    }
    monkeypatch.setattr(evidence, "read_task_record_strict", lambda *_: record)
    monkeypatch.setattr(
        evidence,
        "evaluate_verification_git_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            gate_eligible=True,
            subject_commit="a" * 40,
            attestation_head="a" * 40,
            committed_scope=SimpleNamespace(passed=True),
            attestation_scope=SimpleNamespace(passed=True),
            worktree_scope=SimpleNamespace(passed=True),
        ),
    )
    monkeypatch.setattr(
        evidence, "commits_are_ancestral", lambda *_args, **_kwargs: True, raising=False
    )
    monkeypatch.setattr(evidence, "resolve_task_path", lambda *_: spec_path)
    monkeypatch.setattr(evidence, "read_task_json", lambda *_args, **_kwargs: classification)
    monkeypatch.setattr(evidence, "load_policy_bundle", lambda *_: SimpleNamespace(sha256="e" * 64))
    synchronized = {"value": True}
    monkeypatch.setattr(
        evidence,
        "current_classification_input_digest",
        lambda *_: ("d" * 64, synchronized["value"]),
    )

    loaded_task, loaded_classification, policy_sha = evidence._validate_bindings(
        tmp_path, "TASK-0014", "a" * 40
    )
    assert loaded_task is task
    assert loaded_classification is classification
    assert policy_sha == "e" * 64

    synchronized["value"] = False
    with pytest.raises(ContractError) as caught:
        evidence._validate_bindings(tmp_path, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_BINDING_STALE"

    monkeypatch.setattr(
        evidence,
        "resolve_task_path",
        lambda *_: (_ for _ in ()).throw(AiflowError("bad storage")),
    )
    with pytest.raises(ContractError) as caught:
        evidence._validate_bindings(tmp_path, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_BINDING_STALE"


@pytest.mark.parametrize(
    "failure",
    [None, "gate", "subject", "committed", "attestation", "worktree", "ancestry"],
    ids=(
        "current-task-governance-attestation-is-allowed",
        "gate-ineligible",
        "assessment-synchronizes-subject-to-head",
        "committed-scope-failed",
        "attestation-scope-failed",
        "worktree-scope-failed",
        "base-subject-attestation-chain-is-not-ancestral",
    ),
)
def test_bindings_require_a_current_final_git_assessment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str | None
) -> None:
    """Keep an unconsumed action bound to the final Git assessment contract."""
    subject = "a" * 40
    head = "f" * 40
    task = {
        "repository_id": "repo",
        "branch": "main",
        "base_commit": "b" * 40,
        "subject_commit": subject,
        "frozen_spec_sha256": "c" * 64,
        "allowed_scope": ["src/**"],
        "decision_units": [],
    }
    classification = {
        "base_commit": task["base_commit"],
        "subject_commit": subject,
        "policy_sha256": "d" * 64,
        "classification_input_sha256": "e" * 64,
    }
    scopes = {
        name: SimpleNamespace(passed=failure != name)
        for name in ("committed", "attestation", "worktree")
    }
    assessment = SimpleNamespace(
        gate_eligible=failure != "gate",
        subject_commit=head if failure == "subject" else subject,
        attestation_head=head,
        committed_scope=scopes["committed"],
        attestation_scope=scopes["attestation"],
        worktree_scope=scopes["worktree"],
    )
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    ancestry_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def evaluate(*args: object, **kwargs: object) -> SimpleNamespace:
        calls.append((args, kwargs))
        return assessment

    def ancestral(*args: object, **kwargs: object) -> bool:
        ancestry_calls.append((args, kwargs))
        return failure != "ancestry"

    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# current spec\n", encoding="utf-8")
    record = SimpleNamespace(task=task, events=())
    monkeypatch.setattr(evidence, "read_task_record_strict", lambda *_args: record)
    monkeypatch.setattr(
        evidence,
        "collect_git_context",
        lambda *_args: SimpleNamespace(repository_id="repo", branch="main", head=head),
    )
    monkeypatch.setattr(evidence, "resolve_task_path", lambda *_args: spec_path)
    monkeypatch.setattr(evidence, "read_task_json", lambda *_args, **_kwargs: classification)
    monkeypatch.setattr(
        evidence, "load_policy_bundle", lambda *_args: SimpleNamespace(sha256="d" * 64)
    )
    monkeypatch.setattr(evidence, "specification_digest", lambda *_args: "c" * 64)
    monkeypatch.setattr(
        evidence, "current_classification_input_digest", lambda *_args: ("e" * 64, False)
    )
    monkeypatch.setattr(evidence, "evaluate_verification_git_context", evaluate, raising=False)
    monkeypatch.setattr(evidence, "commits_are_ancestral", ancestral, raising=False)

    if failure is None:
        loaded_task, loaded_classification, policy_sha = evidence._validate_bindings(
            tmp_path, "TASK-0015", subject
        )
        assert loaded_task is task
        assert loaded_classification is classification
        assert policy_sha == "d" * 64
    else:
        with pytest.raises(ContractError) as caught:
            evidence._validate_bindings(tmp_path, "TASK-0015", subject)
        assert caught.value.code == "MUTATION_EVIDENCE_BINDING_STALE"

    assert len(calls) == 1
    arguments, keywords = calls[0]
    assert arguments == (tmp_path,)
    assert keywords["task_id"] == "TASK-0015"
    assert keywords["allowed_scope"] == ("src/**",)
    assert keywords["mode"] == "final"
    binding = keywords["binding"]
    assert binding.repository_id == "repo"
    assert binding.branch == "main"
    assert binding.base_commit == "b" * 40
    assert binding.subject_commit == subject
    if failure in {None, "ancestry"}:
        assert ancestry_calls == [
            (
                (tmp_path,),
                {
                    "base_commit": "b" * 40,
                    "subject_commit": subject,
                    "head_commit": head,
                },
            )
        ]
    else:
        assert ancestry_calls == []


def test_small_helpers_fail_closed_without_runner(tmp_path: Path) -> None:
    assert evidence._utc_now().tzinfo is timezone.utc
    assert len(evidence._nonce_hex()) == 16

    non_object = tmp_path / "array.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ContractError) as caught:
        evidence._read_json(non_object)
    assert caught.value.code == "MUTATION_EVIDENCE_LOG_INVALID"

    with pytest.raises(ContractError) as caught:
        evidence._source_sha256(tmp_path / "missing")
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"

    with pytest.raises(ContractError) as caught:
        evidence._write_new_json(tmp_path / "invalid.json", {"invalid": {1, 2}})
    assert caught.value.code == "MUTATION_EVIDENCE_WRITE_FAILED"


@pytest.mark.parametrize(
    ("subject", "assessment", "expected"),
    [
        ("not-a-commit", None, "MUTATION_EVIDENCE_SUBJECT_INVALID"),
        ("a" * 40, AiflowError("git unavailable"), "MUTATION_EVIDENCE_SUBJECT_INVALID"),
        (
            "a" * 40,
            SimpleNamespace(
                gate_eligible=False,
                subject_commit="a" * 40,
                committed_scope=SimpleNamespace(passed=True),
                attestation_scope=SimpleNamespace(passed=True),
                worktree_scope=SimpleNamespace(passed=True),
            ),
            "MUTATION_EVIDENCE_BINDING_STALE",
        ),
    ],
)
def test_binding_subject_and_context_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    subject: str,
    assessment: object,
    expected: str,
) -> None:
    record = SimpleNamespace(
        task={
            "subject_commit": subject,
            "repository_id": "repo",
            "branch": "main",
            "base_commit": "b" * 40,
            "allowed_scope": ["src/**"],
        },
        events=(),
    )
    monkeypatch.setattr(evidence, "read_task_record_strict", lambda *_: record)
    if isinstance(assessment, Exception):
        monkeypatch.setattr(
            evidence,
            "evaluate_verification_git_context",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(assessment),
        )
    elif assessment is not None:
        monkeypatch.setattr(
            evidence, "evaluate_verification_git_context", lambda *_args, **_kwargs: assessment
        )
    with pytest.raises(ContractError) as caught:
        evidence._validate_bindings(tmp_path, "TASK-0014", subject)
    assert caught.value.code == expected


@pytest.mark.parametrize("failure", [AiflowError("task root"), AiflowError("resolved path")])
def test_reserve_path_errors_are_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: AiflowError
) -> None:
    if str(failure) == "task root":
        monkeypatch.setattr(evidence, "task_root", lambda *_: (_ for _ in ()).throw(failure))
    else:
        monkeypatch.setattr(
            evidence, "resolve_task_path", lambda *_: (_ for _ in ()).throw(failure)
        )
    with pytest.raises(ContractError) as caught:
        evidence._reserve_record_root(
            tmp_path, "TASK-0014", datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
    assert caught.value.code == "MUTATION_EVIDENCE_PATH_ESCAPE"


def test_reserve_logs_mkdir_oserror_is_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logs = tmp_path / ".ai/tasks/TASK-0014/logs"
    monkeypatch.setattr(evidence, "task_root", lambda *_: tmp_path / ".ai/tasks")
    monkeypatch.setattr(evidence, "resolve_task_path", lambda *_: logs)
    original = Path.mkdir

    def fail_logs(path: Path, *args, **kwargs) -> None:
        if path == logs:
            raise OSError("read-only")
        original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_logs)
    with pytest.raises(ContractError) as caught:
        evidence._reserve_record_root(
            tmp_path, "TASK-0014", datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
    assert caught.value.code == "MUTATION_EVIDENCE_ID_FAILED"


@pytest.mark.parametrize("bad_run", [None, object()])
def test_runner_type_and_manifest_fail_before_artifact(bad_run: object) -> None:
    manifest = _cached_manifest()
    with pytest.raises(ContractError) as caught:
        evidence._validate_run(manifest, bad_run, "a" * 40)  # type: ignore[arg-type]
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"


@pytest.mark.parametrize("tamper", ["result_order", "result_declaration", "log_ref", "record_id"])
def test_loader_stable_codes_for_structural_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    path = root / artifact.evidence_ref
    value = json.loads(path.read_text(encoding="utf-8"))
    if tamper == "result_order":
        value["results"].reverse()
        expected = "MUTATION_EVIDENCE_INPUT_MISMATCH"
    elif tamper == "result_declaration":
        value["results"][0]["operator"] = "wrong"
        expected = "CONTRACT_VALIDATION_FAILED"
    elif tamper == "log_ref":
        value["results"][0]["log_ref"] = "elsewhere.json"
        expected = "CONTRACT_VALIDATION_FAILED"
    else:
        value["record_id"] = "MUTRUN-20000101T000001Z-0000000000000000"
        expected = "MUTATION_EVIDENCE_PATH_INVALID"
    _resign(value)
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ContractError) as caught:
        evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    assert caught.value.code == expected


def test_manifest_load_failure_stops_before_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest))
    monkeypatch.setattr(
        evidence,
        "_load_manifest",
        lambda *_: (_ for _ in ()).throw(
            ContractError("bad manifest", code="MUTATION_EVIDENCE_INPUT_MISMATCH")
        ),
    )
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"
    assert calls == {"runner": 0}


def test_loader_semantic_tampering_is_stable_after_schema_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    path = root / artifact.evidence_ref
    value = json.loads(path.read_text(encoding="utf-8"))
    value["results"][0]["operator"] = "different-but-well-formed"
    _resign(value)
    path.write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr(evidence, "require_valid_contract", lambda *_: None)
    with pytest.raises(ContractError) as caught:
        evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"


@pytest.mark.parametrize(
    "bad_ref", ["", "bad", ".ai/tasks/TASK-0015/logs/x/targeted-mutation/evidence.json"]
)
def test_loader_rejects_noncanonical_reference(tmp_path: Path, bad_ref: str) -> None:
    with pytest.raises(ContractError) as caught:
        evidence.load_targeted_mutation_evidence(tmp_path, "TASK-0014", bad_ref)
    assert caught.value.code == "MUTATION_EVIDENCE_PATH_INVALID"


def test_reserve_rejects_bad_nonce_and_directory_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logs = tmp_path / ".ai/tasks/TASK-0014/logs"
    logs.mkdir(parents=True)
    monkeypatch.setattr(evidence, "task_root", lambda *_: tmp_path / ".ai/tasks")
    monkeypatch.setattr(evidence, "resolve_task_path", lambda *_: logs)
    monkeypatch.setattr(evidence, "_nonce_hex", lambda: "bad")
    with pytest.raises(ContractError) as caught:
        evidence._reserve_record_root(
            tmp_path, "TASK-0014", datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
    assert caught.value.code == "MUTATION_EVIDENCE_ID_FAILED"

    monkeypatch.setattr(evidence, "_nonce_hex", lambda: "0" * 16)
    monkeypatch.setattr(Path, "is_symlink", lambda path: path.name.startswith("MUTRUN-"))
    with pytest.raises(ContractError) as caught:
        evidence._reserve_record_root(
            tmp_path, "TASK-0014", datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
    assert caught.value.code == "MUTATION_EVIDENCE_PATH_ESCAPE"


def test_load_manifest_and_contract_key_errors_are_normalized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        evidence, "load_mutation_manifest", lambda *_: (_ for _ in ()).throw(ValueError("bad"))
    )
    with pytest.raises(ContractError) as caught:
        evidence._load_manifest(tmp_path)
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"

    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    monkeypatch.setattr(
        evidence, "require_valid_contract", lambda *_: (_ for _ in ()).throw(KeyError("x"))
    )
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_SEMANTICS_INVALID"


def test_loader_internal_semantics_cover_reordered_and_uncovered_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest, mutant=0))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    path = root / artifact.evidence_ref
    value = json.loads(path.read_text(encoding="utf-8"))
    value["results"].reverse()
    _resign(value)
    path.write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setattr(evidence, "require_valid_contract", lambda *_: None)
    with pytest.raises(ContractError) as caught:
        evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"

    value["results"].reverse()
    value["uncovered_mutation_ids"] = []
    _resign(value)
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ContractError) as caught:
        evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    assert caught.value.code == "MUTATION_EVIDENCE_SEMANTICS_INVALID"


def test_manifest_success_and_record_time_helpers(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    assert evidence._load_manifest(root).mutations
    assert not evidence._record_time_matches("not-a-record", "2000-01-01T00:00:00Z")


def test_reserve_rejects_lexical_log_symlink_and_unconvertible_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logs = tmp_path / ".ai/tasks/TASK-0014/logs"
    monkeypatch.setattr(evidence, "task_root", lambda *_: tmp_path / ".ai/tasks")
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == logs)
    with pytest.raises(ContractError) as caught:
        evidence._reserve_record_root(
            tmp_path, "TASK-0014", datetime(2000, 1, 1, tzinfo=timezone.utc)
        )
    assert caught.value.code == "MUTATION_EVIDENCE_PATH_INVALID"

    class BadClock:
        tzinfo = timezone.utc

        @staticmethod
        def utcoffset():
            return timezone.utc.utcoffset(None)

        @staticmethod
        def astimezone(_zone):
            raise ValueError("clock failed")

    monkeypatch.setattr(Path, "is_symlink", lambda _: False)
    monkeypatch.setattr(evidence, "resolve_task_path", lambda *_: logs)
    with pytest.raises(ContractError) as caught:
        evidence._reserve_record_root(tmp_path, "TASK-0014", BadClock())  # type: ignore[arg-type]
    assert caught.value.code == "MUTATION_EVIDENCE_ID_FAILED"


def test_v2_loader_rejects_process_source_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    (root / "src/aiflow/mutation_process.py").write_text("changed", encoding="utf-8")
    with pytest.raises(ContractError):
        evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)


@pytest.fixture
def material_checkout(tmp_path: Path) -> dict[str, bytes]:
    paths = (
        "src/aiflow/__init__.py",
        "tests/conftest.py",
        ".ai/policy/rules.yml",
        ".ai/schemas/schema.json",
        ".ai/mutations/manifest.json",
        ".ai/templates/task.yaml",
        "pyproject.toml",
        "uv.lock",
        ".gitattributes",
    )
    materials = {name: b"sample\n" for name in paths}
    for name, data in materials.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return materials


def test_material_closure_rejects_extra_pytest_config_and_src_module(
    tmp_path: Path, material_checkout: dict[str, bytes]
) -> None:
    materials = material_checkout
    assert mutation_materials.checkout_matches_materials(tmp_path, materials)
    extra = tmp_path / "pytest.ini"
    extra.write_text("[pytest]\n", encoding="utf-8")
    assert not mutation_materials.checkout_matches_materials(tmp_path, materials)
    materials["pytest.ini"] = extra.read_bytes()
    assert mutation_materials.checkout_matches_materials(tmp_path, materials)
    module = tmp_path / "src/sitecustomize.py"
    module.write_text("pass\n", encoding="utf-8")
    assert not mutation_materials.checkout_matches_materials(tmp_path, materials)


@pytest.mark.parametrize("missing", ["src", "uv.lock"])
def test_material_closure_requires_source_tree_and_lockfile(
    tmp_path: Path, material_checkout: dict[str, bytes], missing: str
) -> None:
    (tmp_path / missing).rename(tmp_path / "omitted")
    assert not mutation_materials.checkout_matches_materials(tmp_path, material_checkout)


def test_material_closure_fails_closed_when_root_cannot_be_listed(
    tmp_path: Path, material_checkout: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreadable(_path: Path):
        raise PermissionError("cannot list checkout")

    monkeypatch.setattr(Path, "iterdir", unreadable)
    assert not mutation_materials.checkout_matches_materials(tmp_path, material_checkout)


def test_loaded_module_requires_exact_subject_path_and_function_source(tmp_path: Path) -> None:
    module_path = tmp_path / "src/aiflow/example.py"
    module_path.parent.mkdir(parents=True)
    data = b"def example():\n    return 1\n"
    module_path.write_bytes(data)
    materials = {"src/aiflow/example.py": data}
    module = ModuleType("aiflow.example")
    module.__file__ = str(module_path)
    exec(compile(data, str(module_path), "exec", dont_inherit=True), module.__dict__)
    assert mutation_materials._module_identity_matches(
        tmp_path, materials, "aiflow.example", module
    )
    module.example = lambda: None
    module.example.__module__ = "aiflow.example"
    assert not mutation_materials._module_identity_matches(
        tmp_path, materials, "aiflow.example", module
    )
    module.__file__ = str(tmp_path / "wrong.py")
    assert not mutation_materials._module_identity_matches(
        tmp_path, materials, "aiflow.example", module
    )


def test_hashed_log_uses_one_bounded_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "log.json"
    payload = b'{"value":1}'
    path.write_bytes(payload)
    reads = []
    original = evidence._bounded_bytes

    def read_once(path: Path, limit: int) -> bytes:
        reads.append(path)
        data = original(path, limit)
        path.write_bytes(b'{"value":2}')
        return data

    monkeypatch.setattr(evidence, "_bounded_bytes", read_once)
    assert evidence._read_hashed_log(path, evidence._sha256_bytes(payload)) == {"value": 1}
    assert reads == [path]


def test_artifact_and_log_reject_oversized_content(tmp_path: Path) -> None:
    path = tmp_path / "huge.json"
    path.write_bytes(b"x" * (evidence._MAX_ARTIFACT_BYTES + 1))
    with pytest.raises(ContractError):
        evidence._read_json(path)
    with pytest.raises(ContractError):
        evidence._read_hashed_log(path, "a" * 64)


def test_missing_historical_artifact_reports_unknown(tmp_path: Path) -> None:
    reference = (
        ".ai/tasks/TASK-0014/logs/MUTRUN-20000101T000000Z-0000000000000000/"
        "targeted-mutation/evidence.json"
    )
    facts = evidence.read_historical_mutation_evidence(tmp_path, "TASK-0014", reference)
    assert facts.integrity == "unknown" and facts.exit_outcomes == ()


def _record_synthetic_launch(
    root: Path,
    task_id: str,
    artifact: evidence.MutationEvidenceArtifact,
    now: datetime,
    monkeypatch: pytest.MonkeyPatch,
):
    """Write the consumed and completed action receipts and the exclusive launch claim."""
    task_dir = root / ".ai/tasks" / task_id
    subject, base, spec, policy, classification_sha = (
        "a" * 40,
        "b" * 40,
        "c" * 64,
        "e" * 64,
        "d" * 64,
    )
    event_time = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    expires = (now + timedelta(days=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
    action = {
        "decision_unit_id": "DU-001",
        "classification_input_sha256": classification_sha,
        "action_type": "targeted_mutation_v2",
        "target": task_id,
        "parameter_summary": "fixed tests",
        "subject_commit": subject,
        "conditions": [],
        "expires_at": expires,
        "single_use": True,
    }
    action_file = task_dir / "action-v2-targeted-mutation-test.json"
    action_file.write_text(json.dumps(action), encoding="utf-8")
    digest = evidence.canonical_action_sha256(
        evidence.validate_action_file(action, subject_commit=subject)
    )
    approval = {
        "schema_version": "1.0",
        "task_id": task_id,
        "decision_unit_id": "DU-001",
        "approval_type": "action",
        "actor": "project-owner",
        "reason": "approved",
        "spec_sha256": spec,
        "policy_sha256": policy,
        "base_commit": base,
        "subject_commit": subject,
        "approved_at": event_time,
        "action_sha256": digest,
        "expires_at": expires,
        "single_use": True,
    }
    approvals = [approval]
    approval_event = {
        "event_type": "approval_recorded",
        "occurred_at": event_time,
        "payload": {"approval_type": "action", "approvals": [approval]},
    }
    events = [approval_event]
    task = {"current_state": "IMPLEMENTING", "frozen_spec_sha256": spec, "base_commit": base}
    unit = {
        "decision_unit_id": "DU-001",
        "permission_requirements": ["action_approval"],
        "verification_requirements": {"targeted_mutation_required": True},
    }
    monkeypatch.setattr(
        evidence, "read_task_record_strict", lambda *_: SimpleNamespace(events=events)
    )
    monkeypatch.setattr(evidence, "_action_approvals", lambda *_: tuple(approvals))
    monkeypatch.setattr(evidence, "parse_decision_units", lambda *_: [unit])

    def capture_event(root, task_id, *, event_type, actor, payload):
        events.append({"event_type": event_type, "occurred_at": event_time, "payload": payload})

    with monkeypatch.context() as writer:
        writer.setattr(evidence, "record_task_event", capture_event)
        writer.setattr(evidence, "_utc_text", lambda: event_time)
        writer.setattr(
            evidence,
            "_current_targeted_mutation_action",
            lambda *_: (digest, action, action_file, "DU-001"),
        )
        use = evidence._consume_targeted_mutation_action(
            root,
            task_id,
            subject,
            task,
            {"classification_input_sha256": classification_sha},
            policy,
            check_inputs=lambda: None,
        )
        writer.setattr(
            evidence,
            "_revalidate_targeted_mutation_action",
            lambda *_: (task, {"classification_input_sha256": classification_sha}, policy),
        )
        evidence._authorize_targeted_mutation_runner_launch(
            root,
            task_id,
            subject,
            action_sha256=use.action_sha256,
            receipt_path=use.receipt_path,
            action_path=use.action_path,
            decision_unit_id=use.decision_unit_id,
            spec_sha256=spec,
            policy_sha256=policy,
            base_commit=base,
            classification_input_sha256=classification_sha,
            receipt_device=use.receipt_device,
            receipt_inode=use.receipt_inode,
        )
        evidence._complete_targeted_mutation_action(use, artifact)
    return use, events, approvals


@pytest.mark.parametrize(
    "tamper",
    [
        None,
        "expiry",
        "missing_approval",
        "late_approval",
        "amended_receipt",
        "wrong_material",
        "missing_consumption",
        "missing_launch",
        "wrong_subject",
        "false_single_use",
        "wrong_inode_type",
        "late_launch",
    ],
)
def test_current_action_receipt_is_replayed_at_consumption_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str | None
) -> None:
    task_id = "TASK-0014"
    manifest = _cached_manifest()
    original_action_functions = (
        evidence._consume_targeted_mutation_action,
        evidence._complete_targeted_mutation_action,
        evidence._verify_recorded_action,
    )
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    receipt = evidence.record_targeted_mutation_evidence(root, task_id, "a" * 40)
    artifact = json.loads((root / receipt.evidence_ref).read_bytes())
    for function in original_action_functions:
        monkeypatch.setattr(evidence, function.__name__, function)
    use, events, approvals = _record_synthetic_launch(
        root, task_id, receipt, datetime(2000, 1, 1, tzinfo=timezone.utc), monkeypatch
    )
    projection = _v2_projection(artifact, receipt.evidence_ref)
    claim = use.receipt_path.parent / "logs" / f"action-launch-{use.action_sha256}.json"
    if tamper == "expiry":
        events[-1]["occurred_at"] = "2002-01-01T00:00:00Z"
    elif tamper == "missing_approval":
        approvals.clear()
    elif tamper == "late_approval":
        events.reverse()
    elif tamper == "amended_receipt":
        with use.receipt_path.open("a", encoding="utf-8") as stream:
            stream.write("- Approval consumed: `false`\n")
    elif tamper == "wrong_material":
        with use.receipt_path.open("a", encoding="utf-8") as stream:
            stream.write("- Canonical mutation-evidence SHA-256: changed\n")
    elif tamper == "missing_consumption":
        events.pop()

    elif tamper == "missing_launch":
        claim.unlink()
    elif tamper in {"wrong_subject", "false_single_use", "wrong_inode_type", "late_launch"}:
        fields = json.loads(claim.read_bytes())
        key, value = {
            "wrong_subject": ("subject_commit", "0" * 40),
            "false_single_use": ("single_use", False),
            "wrong_inode_type": ("receipt_inode", str(use.receipt_inode)),
            "late_launch": ("claimed_at", "2003-01-01T00:00:00Z"),
        }[tamper]
        fields[key] = value
        claim.write_text(json.dumps(fields), encoding="utf-8")
    facts = evidence.consume_targeted_mutation_evidence(root, task_id, projection)
    if tamper is None:
        assert facts.passed and facts.reason_code is None
    else:
        assert not facts.passed and facts.reason_code == "MUTATION_EVIDENCE_INVALID"


@pytest.mark.parametrize(
    "failure",
    [
        "runtime",
        "missing_pytest",
        "identity",
        "subject_bytes",
        "unreviewed_detector",
        "job",
        "unsupported_platform",
        "python",
    ],
)
def test_preflight_rejects_before_consuming_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest), authorized=False)
    task_dir = root / ".ai/tasks/TASK-0014"
    monkeypatch.setattr(
        evidence,
        "_current_targeted_mutation_action",
        lambda *_: (
            "1" * 64,
            {"expires_at": "2099-01-01T00:00:00Z"},
            task_dir / "action.json",
            "DU-001",
        ),
    )
    monkeypatch.setattr(evidence, "_preflight_targeted_mutation", _PRODUCTION_PREFLIGHT)
    monkeypatch.setattr(evidence, "sys", SimpleNamespace(platform="win32", version_info=(3, 11)))
    monkeypatch.setattr(evidence.metadata, "version", lambda _: "9.1.1")
    monkeypatch.setattr(evidence, "preflight_mutation_runtime", lambda *_: None)
    monkeypatch.setattr(evidence, "assert_no_checkout_filters", lambda *_: None)
    _PRODUCTION_PREFLIGHT(root, "a" * 40, evidence.subject_materials(root, "a" * 40), True)
    if failure == "unsupported_platform":
        evidence.sys.platform = "linux"
    elif failure == "python":
        evidence.sys.version_info = (3, 12)
    elif failure == "runtime":
        monkeypatch.setattr(evidence.metadata, "version", lambda _: "0.0")
    elif failure == "missing_pytest":

        def no_pytest(_name: str) -> str:
            raise evidence.metadata.PackageNotFoundError("pytest")

        monkeypatch.setattr(evidence.metadata, "version", no_pytest)
    elif failure == "identity":
        monkeypatch.setattr(evidence, "loaded_engine_matches", lambda *_: False)
    elif failure == "unreviewed_detector":
        detector = "tests/unit/test_policy.py"
        materials = dict(evidence.subject_materials(root, "a" * 40))
        materials[detector] += b"# detector source changed\n"
        (root / detector).write_bytes(materials[detector])
        monkeypatch.setattr(evidence, "subject_materials", lambda *_: materials)
    elif failure == "job":

        def job_unavailable(*_):
            raise ContractError("Job unavailable", code="MUTATION_EVIDENCE_INPUT_MISMATCH")

        monkeypatch.setattr(evidence, "preflight_mutation_runtime", job_unavailable)
    else:
        (root / "src/aiflow/mutation_process.py").write_text("drift", encoding="utf-8")
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"
    assert not list(task_dir.glob("action-use-*.md"))
    assert not (task_dir / "events.jsonl").exists()
    assert calls["runner"] == 0


def test_material_drift_under_reservation_lock_keeps_approval_unused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest), authorized=False)
    original_materials = evidence.subject_materials
    materials = dict(original_materials(root, "a" * 40))
    real_lock = evidence._locked_action_consumption
    monkeypatch.setattr(evidence, "subject_materials", lambda *_: dict(materials))
    task_dir = root / ".ai/tasks/TASK-0014"
    monkeypatch.setattr(
        evidence,
        "_current_targeted_mutation_action",
        lambda *_: (
            "1" * 64,
            {"expires_at": "2099-01-01T00:00:00Z"},
            task_dir / "action.json",
            "DU-001",
        ),
    )

    @contextmanager
    def change_materials_on_reservation(*args):
        with real_lock(*args):
            materials["tests/conftest.py"] = b"# fixture was changed before reservation\n"
            yield

    monkeypatch.setattr(evidence, "_locked_action_consumption", change_materials_on_reservation)
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"
    assert not list(task_dir.glob("action-use-*.md"))
    assert not (task_dir / "events.jsonl").exists()
    assert calls["runner"] == 0


def _record_historical_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    artifact_path = root / artifact.evidence_ref
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    data["schema_version"] = "1.0"
    data.pop("subject_materials_sha256")
    for result in data["results"]:
        log_path = root / result["log_ref"]
        log = json.loads(log_path.read_text(encoding="utf-8"))
        for key in (
            "baseline_report",
            "mutant_report",
            "baseline_target_sha256",
            "mutant_target_sha256",
            "baseline_lifecycle",
            "mutant_lifecycle",
        ):
            del log[key]
        log_path.write_bytes(json.dumps(log, indent=2).encode("utf-8") + b"\n")
        result["log_sha256"] = evidence._source_sha256(log_path)
    _resign(data)
    artifact_path.write_text(json.dumps(data), encoding="utf-8")
    return root, manifest, artifact, data


def test_historical_v1_reports_exits_and_never_satisfies_current_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, manifest, artifact, data = _record_historical_exits(tmp_path, monkeypatch)
    historical = evidence.read_historical_mutation_evidence(
        root, "TASK-0014", artifact.evidence_ref
    )
    assert historical.integrity == "unknown"
    assert historical.exit_outcomes == tuple(
        (item.mutation_id, "killed") for item in manifest.mutations
    )
    assert historical.exit_codes == tuple((item.mutation_id, 0, 1) for item in manifest.mutations)
    projection = _v2_projection(data, artifact.evidence_ref)
    assert not evidence.consume_targeted_mutation_evidence(root, "TASK-0014", projection).passed
    with pytest.raises(ContractError):
        evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    (root / data["results"][0]["log_ref"]).unlink()
    missing = evidence.read_historical_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    assert (
        missing.integrity == "unknown" and missing.exit_outcomes == () and missing.exit_codes == ()
    )


def test_subject_materials_include_root_config_templates_and_extra_src(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = (
        "src/sitecustomize.py",
        "tests/conftest.py",
        ".ai/policy/rules.yml",
        ".ai/schemas/schema.json",
        ".ai/mutations/manifest.json",
        ".ai/templates/task.yaml",
        "pyproject.toml",
        "uv.lock",
        ".gitattributes",
        "pytest.ini",
        "conftest.py",
    )
    oid = "1" * 40
    tree = b"".join(f"100644 blob {oid}       2\t{name}\0".encode() for name in paths)
    objects = b"".join(f"{oid} blob 2\n".encode() + b"x\n\n" for _ in paths)

    def fake_git(_root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
        return tree if args[0] == "ls-tree" else objects

    monkeypatch.setattr(mutation_materials, "read_material_git", fake_git)
    materials = mutation_materials.subject_materials(tmp_path, "a" * 40)
    assert set(materials) == set(paths)
    assert materials["conftest.py"] == b"x\n"


@pytest.mark.parametrize(
    "kind",
    [
        "subject",
        "oversized_tree",
        "duplicate",
        "symlink",
        "path_escape",
        "negative_size",
        "missing_file",
        "header",
        "truncated",
        "trailing",
        "git_failure",
    ],
)
def test_subject_materials_reject_malformed_or_incomplete_git_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    paths = [
        "src/aiflow/__init__.py",
        "tests/conftest.py",
        ".ai/policy/rules.yml",
        ".ai/schemas/schema.json",
        ".ai/mutations/manifest.json",
        ".ai/templates/task.yaml",
        "pyproject.toml",
        "uv.lock",
        ".gitattributes",
    ]
    oid = "1" * 40

    def row(name: str, *, mode: str = "100644", size: int = 2) -> bytes:
        return f"{mode} blob {oid} {size}\t{name}\0".encode()

    tree = b"".join(row(name) for name in paths)
    objects = b"".join(f"{oid} blob 2\n".encode() + b"x\n\n" for _ in paths)
    if kind == "oversized_tree":
        tree = b"x" * (8 * 1024 * 1024 + 1)
    elif kind == "duplicate":
        tree += row(paths[0])
    elif kind == "symlink":
        tree = tree.replace(row(paths[0]), row(paths[0], mode="120000"))
    elif kind == "path_escape":
        tree += row("src/../escape.py")
    elif kind == "negative_size":
        tree = tree.replace(row(paths[0]), row(paths[0], size=-1))
    elif kind == "missing_file":
        tree = tree.replace(row("uv.lock"), b"")
    elif kind == "header":
        objects = objects.replace(f"{oid} blob 2\n".encode(), b"invalid header\n", 1)
    elif kind == "truncated":
        objects = objects[:-2]
    elif kind == "trailing":
        objects += b"unexpected"

    def fake_git(_root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
        if kind == "git_failure":
            raise ContractError("git failed", code="MUTATION_SUBJECT_INVALID")
        return tree if args[0] == "ls-tree" else objects

    monkeypatch.setattr(mutation_materials, "read_material_git", fake_git)
    with pytest.raises(ContractError) as caught:
        mutation_materials.subject_materials(tmp_path, "bad" if kind == "subject" else "a" * 40)
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"


def test_material_git_wrapper_strips_git_environment_and_handles_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_DIR", "untrusted")

    def fake_run(argv, **kwargs):
        assert argv[:2] == ["git", "status"]
        assert "GIT_DIR" not in kwargs["env"]
        assert kwargs["env"]["GIT_CONFIG_NOSYSTEM"] == "1"
        return SimpleNamespace(stdout=b"clean")

    monkeypatch.setattr(mutation_materials.subprocess, "run", fake_run)
    assert mutation_materials.read_material_git(tmp_path, "status") == b"clean"

    def fail(*_args, **_kwargs):
        raise OSError("missing git")

    monkeypatch.setattr(mutation_materials.subprocess, "run", fail)
    with pytest.raises(ContractError) as caught:
        mutation_materials.read_material_git(tmp_path, "status")
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"


@pytest.mark.parametrize(
    ("original", "actual", "expected"),
    [
        (b"a\nb\n", b"a\r\nb\r\n", True),
        (b"a\nb\n", b"a\r\nb\n", False),
        (b"\0\n", b"\0\r\n", False),
        (b"a\r\nb\n", b"a\r\nb\r\n", False),
        (b"\xff\n", b"\xff\r\n", False),
        (b"binary\0", b"binary\0", True),
    ],
)
def test_material_checkout_allows_only_exact_or_whole_lf_conversion(
    original: bytes, actual: bytes, expected: bool
) -> None:
    assert mutation_materials.content_matches(actual, original) is expected


def test_material_files_reject_missing_links_and_invalid_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "src/aiflow/mod.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"source\n")
    assert mutation_materials.material_file_matches(tmp_path, "src/aiflow/mod.py", b"source\n")
    assert not mutation_materials.material_file_matches(tmp_path, "../mod.py", b"source\n")
    assert not mutation_materials.material_file_matches(tmp_path, "src\\mod.py", b"source\n")
    assert not mutation_materials.material_file_matches(tmp_path, "src/missing", b"x")
    original = mutation_materials.is_link_or_reparse_point
    monkeypatch.setattr(
        mutation_materials,
        "is_link_or_reparse_point",
        lambda candidate: candidate == path or original(candidate),
    )
    assert not mutation_materials.material_file_matches(tmp_path, "src/aiflow/mod.py", b"source\n")


def test_loaded_engine_identity_rejects_missing_and_foreign_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "src/aiflow/__init__.py"
    package.parent.mkdir(parents=True)
    package.write_bytes(b"# bound\n")
    bound = ModuleType("aiflow")
    bound.__file__ = str(package)
    materials = {"src/aiflow/__init__.py": b"# bound\n"}
    fake_sys = SimpleNamespace(modules={"aiflow": bound})
    monkeypatch.setattr(mutation_materials, "sys", fake_sys)
    assert mutation_materials.loaded_engine_matches(tmp_path, materials)
    fake_sys.modules["aiflow.unbound"] = ModuleType("aiflow.unbound")
    assert not mutation_materials.loaded_engine_matches(tmp_path, materials)
    fake_sys.modules.clear()
    assert not mutation_materials.loaded_engine_matches(tmp_path, materials)


@pytest.mark.parametrize("invalid", ["bad_base64", "noncanonical", "oversized", "nonstring"])
def test_report_storage_rejects_invalid_encoded_inputs(invalid: str) -> None:
    candidate = {
        "bad_base64": "!!!!",
        "noncanonical": "YQ",
        "oversized": "A" * 21849,
        "nonstring": 1,
    }[invalid]
    with pytest.raises(ContractError):
        evidence._decode_report(candidate)
    assert evidence._decode_report(None) is None
    assert evidence._safe_report(b"untrusted output", "MUT-V2-001", "a" * 64) is None
    assert evidence._safe_report(None, "MUT-V2-001", None) is None


@pytest.mark.parametrize(
    "kind",
    [
        "baseline_setup",
        "teardown",
        "missing_report",
        "target_drift",
        "unknown_runtime",
        "survived",
        "no_source",
    ],
)
def test_derive_outcome_requires_pinned_report_and_transform(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    manifest = _cached_manifest()
    declaration = manifest.mutations[0]
    run = _run(manifest, mutant=0 if kind == "survived" else 1)
    probe = run.probes[0]
    materials = {declaration.target: f"synthetic {declaration.target}\n".encode()}
    monkeypatch.setattr(
        evidence, "mutation_bytes", lambda _item, data: data + b"synthetic mutant\n"
    )
    if kind in {"baseline_setup", "teardown", "unknown_runtime"}:
        is_baseline = kind == "baseline_setup"
        report = json.loads(probe.baseline_report if is_baseline else probe.mutant_report)
        if kind == "baseline_setup":
            report["cases"][0]["setup"] = "failed"
            report["cases"][0]["call"] = "skipped"
        elif kind == "teardown":
            report["cases"][0]["teardown"] = "failed"
        else:
            report["imports"]["reference_ok"] = False
        raw = mutation_protocol.encode_report(report)
        probe = replace(
            probe,
            **(
                {
                    "baseline_report": raw,
                    "baseline_lifecycle": _lifecycle(raw, probe.baseline_exit_code),
                }
                if is_baseline
                else {
                    "mutant_report": raw,
                    "mutant_lifecycle": _lifecycle(raw, probe.mutant_exit_code),
                }
            ),
        )
    elif kind == "missing_report":
        probe = replace(probe, mutant_report=None)
    elif kind == "target_drift":
        probe = replace(probe, mutant_target_sha256="0" * 64)
    elif kind == "no_source":
        materials.clear()
    outcome = evidence._derive_outcome(probe, run, declaration, materials)
    assert outcome == ("survived" if kind == "survived" else "unverified")


@pytest.mark.parametrize("failure", ["unrelated_call", "setup"])
def test_failed_mutant_requires_expected_call_to_satisfy_consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    manifest = _cached_manifest()
    run = _run(manifest)
    probe = run.probes[0]
    assert probe.mutant_report is not None
    report = json.loads(probe.mutant_report)
    failed_case = next(case for case in report["cases"] if case["call"] == "failed")
    if failure == "unrelated_call":
        failed_case["failure"]["anchor"] = "unknown"
    else:
        failed_case.update(setup="failed", call="skipped", failure=None)
    raw = mutation_protocol.encode_report(report)
    changed = replace(probe, mutant_report=raw, mutant_lifecycle=_lifecycle(raw, 1))
    root, _, _ = _prepare(tmp_path, monkeypatch, replace(run, probes=(changed, *run.probes[1:])))
    receipt = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    artifact = evidence.load_targeted_mutation_evidence(root, "TASK-0014", receipt.evidence_ref)
    assert [item["outcome"] for item in artifact["results"]] == [
        "unverified",
        *("killed" for _ in run.probes[1:]),
    ]
    assert artifact["uncovered_mutation_ids"] == [probe.mutation_id]
    assert not evidence.consume_targeted_mutation_evidence(
        root, "TASK-0014", _v2_projection(artifact, receipt.evidence_ref)
    ).passed


@pytest.mark.parametrize(
    ("phase", "tamper"),
    [
        ("baseline", "missing"),
        ("mutant", "job_empty"),
        ("baseline", "stderr_eof"),
        ("mutant", "closed"),
        ("mutant", "terminate_requested"),
        ("baseline", "returncode"),
        ("mutant", "report_sha256"),
    ],
)
def test_replay_rejects_resigned_receipt_with_incomplete_or_unbound_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, tamper: str
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    receipt = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    path = root / receipt.evidence_ref
    artifact = json.loads(path.read_bytes())
    item = artifact["results"][0]
    log_path = root / item["log_ref"]
    log = json.loads(log_path.read_bytes())
    field = f"{phase}_lifecycle"
    if tamper == "missing":
        del log[field]
    elif tamper == "report_sha256":
        log[field][tamper] = "0" * 64
    elif tamper == "returncode":
        log[field][tamper] = 1
    else:
        log[field][tamper] = tamper == "terminate_requested"
    log_path.write_text(json.dumps(log), encoding="utf-8")
    item["log_sha256"] = evidence._source_sha256(log_path)
    _resign(artifact)
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ContractError):
        evidence.load_targeted_mutation_evidence(root, "TASK-0014", receipt.evidence_ref)
    assert not evidence.consume_targeted_mutation_evidence(
        root, "TASK-0014", _v2_projection(artifact, receipt.evidence_ref)
    ).passed


@pytest.mark.parametrize("moment", ["initial", "locked"])
def test_tracked_checkout_filter_rejects_before_action_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, moment: str
) -> None:
    manifest = _cached_manifest()
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest), authorized=False)
    doc = root / "docs/fixture.txt"
    doc.parent.mkdir()
    doc.write_bytes(b"outside the mutation materials\n")
    run_git(root, "init", "-b", "main")
    commit_all(root, "Synthetic checkout")
    subject = run_git(root, "rev-parse", "HEAD")
    attributes = root / ".git/info/attributes"
    filtered = b"docs/fixture.txt filter=unconfigured-fixture\n"
    task_dir = root / ".ai/tasks/TASK-0014"
    monkeypatch.setattr(
        evidence,
        "_current_targeted_mutation_action",
        lambda *_: (
            "1" * 64,
            {"expires_at": "2099-01-01T00:00:00Z"},
            task_dir / "action.json",
            "DU-001",
        ),
    )
    monkeypatch.setattr(evidence, "_preflight_targeted_mutation", _PRODUCTION_PREFLIGHT)
    monkeypatch.setattr(evidence, "sys", SimpleNamespace(platform="win32", version_info=(3, 11)))
    monkeypatch.setattr(evidence.metadata, "version", lambda _: "9.1.1")
    monkeypatch.setattr(evidence, "preflight_mutation_runtime", lambda *_: None)
    _PRODUCTION_PREFLIGHT(root, subject, evidence.subject_materials(root, subject), False)
    real_lock = evidence._locked_action_consumption
    entered = []

    @contextmanager
    def reserve(*args):
        with real_lock(*args):
            entered.append(True)
            if moment == "locked":
                attributes.write_bytes(filtered)
            yield

    if moment == "initial":
        attributes.write_bytes(filtered)
    monkeypatch.setattr(evidence, "_locked_action_consumption", reserve)
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", subject)
    assert caught.value.code == "MUTATION_WORKSPACE_INVALID"
    assert entered == ([True] if moment == "locked" else [])
    assert not list(task_dir.glob("action-use-*.md"))
    assert not (task_dir / "events.jsonl").exists()
    assert calls["runner"] == 0


@pytest.mark.parametrize("position", [0, 3, 5])
def test_consumer_rejects_non_object_at_any_projection_position(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, position: int
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    record = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    artifact = evidence.load_targeted_mutation_evidence(root, "TASK-0014", record.evidence_ref)
    projection = _v2_projection(artifact, record.evidence_ref)
    projection["targeted_mutation"]["results"].insert(position, None)
    facts = evidence.consume_targeted_mutation_evidence(root, "TASK-0014", projection)
    assert not facts.passed and facts.reason_code == "MUTATION_EVIDENCE_PROJECTION_INVALID"


def test_consumer_normalizes_oversized_json_integer_within_artifact_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _cached_manifest()
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    record = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    artifact = evidence.load_targeted_mutation_evidence(root, "TASK-0014", record.evidence_ref)
    projection = _v2_projection(artifact, record.evidence_ref)
    saved_limit = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        (root / record.evidence_ref).write_bytes(b'{"count":' + b"1" * 5000 + b"}")
        facts = evidence.consume_targeted_mutation_evidence(root, "TASK-0014", projection)
    finally:
        sys.set_int_max_str_digits(saved_limit)
    assert not facts.passed and facts.reason_code == "MUTATION_EVIDENCE_INVALID"


def test_historical_reader_rejects_unrelated_task_or_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, artifact, _ = _record_historical_exits(tmp_path, monkeypatch)
    with pytest.raises(ContractError) as wrong_task:
        evidence.read_historical_mutation_evidence(root, "TASK-0015", artifact.evidence_ref)
    assert wrong_task.value.code == "MUTATION_EVIDENCE_PATH_INVALID"

    other_ref = artifact.evidence_ref.replace(
        artifact.record_id, "MUTRUN-20000102T000000Z-" + "1" * 16
    )
    misplaced = root / other_ref
    misplaced.parent.mkdir(parents=True)
    misplaced.write_bytes((root / artifact.evidence_ref).read_bytes())
    with pytest.raises(ContractError) as wrong_record:
        evidence.read_historical_mutation_evidence(root, "TASK-0014", other_ref)
    assert wrong_record.value.code == "MUTATION_EVIDENCE_PATH_INVALID"


@pytest.mark.parametrize(
    "case",
    ["consistent", "mixed", "edited", "missing_blob", "other_blob", "symlink_blob", "unborn"],
)
def test_historical_crlf_requires_exact_regular_git_blob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    root, manifest, artifact, data = _record_historical_exits(tmp_path, monkeypatch)
    ref = data["results"][0]["log_ref"]
    log = root / ref
    original = log.read_bytes()
    run_git(root, "init", "-b", "main")
    if case == "missing_blob":
        log.unlink()
    elif case == "other_blob":
        log.write_bytes(original.replace(b"killed", b"failed"))
    run_git(root, "add", ".")
    if case == "symlink_blob":
        blob = run_git(root, "hash-object", "-w", "--", ref)
        run_git(root, "update-index", "--cacheinfo", "120000", blob, ref)
    if case != "unborn":
        run_git(
            root,
            "-c",
            "user.name=AI Flow Tests",
            "-c",
            "user.email=aiflow@example.invalid",
            "commit",
            "-m",
            "Synthetic historical log",
        )
    checkout = original.replace(b"\n", b"\r\n")
    if case == "mixed":
        checkout = checkout.replace(b"\r\n", b"\n", 1)
    elif case == "edited":
        checkout = checkout.replace(b"killed", b"failed")
    log.write_bytes(checkout)
    if case == "consistent":
        facts = evidence.read_historical_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
        assert facts.integrity == "unknown"
        assert facts.exit_codes == tuple((item.mutation_id, 0, 1) for item in manifest.mutations)
    else:
        with pytest.raises(ContractError) as caught:
            evidence.read_historical_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
        assert caught.value.code == "MUTATION_EVIDENCE_LOG_INVALID"
