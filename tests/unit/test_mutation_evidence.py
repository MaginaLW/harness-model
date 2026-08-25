"""Synthetic, zero-worktree tests for Chapter 11.4 mutation evidence."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import aiflow.mutation_evidence as evidence
from aiflow.errors import AiflowError, ContractError, StorageError
from aiflow.mutation_manifest import load_mutation_manifest
from aiflow.mutation_runner import MutationProbe, MutationRun


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
    return MutationRun(
        manifest.manifest_id,
        "a" * 40,
        tuple(
            MutationProbe(item.mutation_id, baseline, mutant, timed_out, 1, probe_reason)
            for item in manifest.mutations
        ),
        unchanged,
        reason,
    )


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    run: MutationRun,
    *,
    authorized: bool = True,
):
    root = tmp_path
    (root / ".ai" / "tasks" / "TASK-0014").mkdir(parents=True)
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
    task = {
        "task_id": "TASK-0014",
        "repository_id": "b85e5a53-4935-4436-bdbc-c26a241bfae8",
        "branch": "main",
        "base_commit": "b" * 40,
        "subject_commit": "a" * 40,
        "frozen_spec_sha256": "c" * 64,
    }
    classification = {"classification_input_sha256": "d" * 64}
    calls = {"runner": 0}
    monkeypatch.setattr(evidence, "_validate_bindings", lambda *_: (task, classification, "e" * 64))
    monkeypatch.setattr(evidence, "_load_manifest", lambda _: manifest)
    monkeypatch.setattr(evidence, "_source_sha256", lambda _: "f" * 64)
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
        monkeypatch.setattr(
            evidence,
            "_consume_targeted_mutation_action",
            lambda *_args: action_use,
        )
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
    root, _, calls = _prepare(tmp_path, monkeypatch, _run(manifest))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    loaded = evidence.load_targeted_mutation_evidence(root, "TASK-0014", artifact.evidence_ref)
    assert calls == {"runner": 1}
    assert artifact.record_id == "MUTRUN-20000101T000000Z-0000000000000000"
    assert artifact.log_refs == tuple(item["log_ref"] for item in loaded["results"])
    assert loaded["uncovered_mutation_ids"] == []
    with pytest.raises(FrozenInstanceError):
        artifact.record_id = "changed"  # type: ignore[misc]

    schema = json.loads(
        (
            Path(__file__).resolve().parents[2] / ".ai/schemas/mutation-evidence.schema.json"
        ).read_text(encoding="utf-8")
    )
    first_log = json.loads((root / artifact.log_refs[0]).read_text(encoding="utf-8"))
    assert set(first_log) == set(schema["$defs"]["execution_log"]["properties"])


@pytest.mark.parametrize(
    ("baseline", "mutant", "reason", "unchanged", "timed_out", "probe_reason", "expected"),
    [
        (0, 1, None, True, False, None, "killed"),
        (0, 0, None, True, False, None, "survived"),
        (0, -9, None, True, False, None, "unverified"),
        (0, 3221225781, None, True, False, None, "unverified"),
        (1, 1, None, True, False, None, "unverified"),
        (None, None, None, True, False, None, "unverified"),
        (0, 1, "cleanup", True, False, None, "unverified"),
        (0, 1, None, False, False, None, "unverified"),
        (0, 1, None, True, True, None, "unverified"),
        (0, 1, None, True, False, "infra", "unverified"),
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    artifact = evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    path = root / artifact.evidence_ref
    value = json.loads(path.read_text(encoding="utf-8"))
    if tamper == "evidence_duplicate_key":
        content = path.read_text(encoding="utf-8")
        path.write_text(
            content.replace(
                '"schema_version": "1.0",',
                '"schema_version": "1.0",\n  "schema_version": "1.0",',
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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


@pytest.mark.parametrize("state", ["IMPLEMENTING", "VERIFYING"])
def test_selector_allows_current_focused_and_v1_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    tasks = tmp_path / ".ai/tasks"
    (tasks / "TASK-0014").mkdir(parents=True)
    record = SimpleNamespace(task={"current_state": state, "subject_commit": "a" * 40})
    monkeypatch.setattr(evidence, "task_root", lambda _: tasks)
    monkeypatch.setattr(evidence, "read_task_record_strict", lambda *_: record)
    monkeypatch.setattr(evidence, "_validate_bindings", lambda *_: ({}, {}, "b" * 64))
    assert evidence._task0014_production_subject(tmp_path) == "a" * 40


def test_selector_inactive_never_calls_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = tmp_path / ".ai/tasks"
    (tasks / "TASK-0014").mkdir(parents=True)
    (tasks / "TASK-10000").mkdir()

    class Record:
        task = {"current_state": "IMPLEMENTING", "subject_commit": "a" * 40}

    calls = {"runner": 0}
    monkeypatch.setattr(evidence, "task_root", lambda _: tasks)
    monkeypatch.setattr(evidence, "read_task_record_strict", lambda *_: Record())
    monkeypatch.setattr(
        evidence, "run_targeted_mutations", lambda *_: calls.__setitem__("runner", 1)
    )
    assert evidence._task0014_production_subject(tmp_path) is None
    assert calls == {"runner": 0}


def test_selector_ignores_historical_nonterminal_tasks_on_old_subjects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = tmp_path / ".ai/tasks"
    for task_id in ("TASK-0008", "TASK-0009", "TASK-0014"):
        (tasks / task_id).mkdir(parents=True)
    current_binding = {
        "repository_id": "b85e5a53-4935-4436-bdbc-c26a241bfae8",
        "branch": "main",
    }
    records = {
        "TASK-0008": SimpleNamespace(
            task={
                **current_binding,
                "current_state": "BLOCKED",
                "subject_commit": "8" * 40,
            }
        ),
        "TASK-0009": SimpleNamespace(
            task={
                **current_binding,
                "current_state": "APPROVED_FOR_MERGE",
                "subject_commit": "9" * 40,
            }
        ),
        "TASK-0014": SimpleNamespace(
            task={
                **current_binding,
                "current_state": "IMPLEMENTING",
                "subject_commit": "a" * 40,
            }
        ),
    }
    monkeypatch.setattr(evidence, "task_root", lambda _: tasks)
    monkeypatch.setattr(evidence, "read_task_record_strict", lambda _root, name: records[name])
    monkeypatch.setattr(evidence, "_validate_bindings", lambda *_: ({}, {}, "b" * 64))

    assert evidence._task0014_production_subject(tmp_path) == "a" * 40


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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
    with pytest.raises(ContractError) as caught:
        evidence._validate_run(manifest, bad_run, "a" * 40)  # type: ignore[arg-type]
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"


@pytest.mark.parametrize("tamper", ["result_order", "result_declaration", "log_ref", "record_id"])
def test_loader_stable_codes_for_structural_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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

    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
    root, _, _ = _prepare(tmp_path, monkeypatch, _run(manifest))
    monkeypatch.setattr(
        evidence, "require_valid_contract", lambda *_: (_ for _ in ()).throw(KeyError("x"))
    )
    with pytest.raises(ContractError) as caught:
        evidence.record_targeted_mutation_evidence(root, "TASK-0014", "a" * 40)
    assert caught.value.code == "MUTATION_EVIDENCE_SEMANTICS_INVALID"


def test_selector_fail_closed_inventory_and_state_variants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        evidence,
        "task_root",
        lambda _: SimpleNamespace(iterdir=lambda: (_ for _ in ()).throw(OSError("blocked"))),
    )
    with pytest.raises(ContractError) as caught:
        evidence._task0014_production_subject(tmp_path)
    assert caught.value.code == "MUTATION_EVIDENCE_BINDING_STALE"

    tasks = tmp_path / ".ai/tasks"
    (tasks / "TASK-0014").mkdir(parents=True)
    (tasks / "TASK-10000").mkdir()
    (tasks / "not-a-task").mkdir()
    monkeypatch.setattr(evidence, "task_root", lambda _: tasks)
    current = SimpleNamespace(task={"current_state": "CLOSED", "subject_commit": "a" * 40})
    merged = SimpleNamespace(task={"current_state": "MERGED"})
    monkeypatch.setattr(
        evidence,
        "read_task_record_strict",
        lambda _root, name: current if name == "TASK-0014" else merged,
    )
    assert evidence._task0014_production_subject(tmp_path) is None

    current.task = {"current_state": "IMPLEMENTING", "subject_commit": None}
    with pytest.raises(ContractError) as caught:
        evidence._task0014_production_subject(tmp_path)
    assert caught.value.code == "MUTATION_EVIDENCE_SUBJECT_INVALID"

    current.task = {"current_state": "IMPLEMENTING", "subject_commit": "a" * 40}
    monkeypatch.setattr(
        evidence,
        "read_task_record_strict",
        lambda _root, name: (
            current
            if name == "TASK-0014"
            else (_ for _ in ()).throw(AiflowError("another task is malformed"))
        ),
    )
    assert evidence._task0014_production_subject(tmp_path) is None


def test_loader_internal_semantics_cover_reordered_and_uncovered_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
