"""Synthetic mutation-evidence contract test; it never calls the runner."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest

from aiflow import mutation_evidence
from aiflow.mutation_evidence import (
    MutationEvidenceArtifact,
    _canonical_bytes,
    _make_artifact,
    _sha256_bytes,
)
from aiflow.mutation_manifest import CANONICAL_MANIFEST_PATH, load_mutation_manifest
from aiflow.mutation_materials import _module_identity_matches, materials_sha256
from aiflow.mutation_runner import MutationProbe, MutationRun

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RECORD_ID = "MUTRUN-20000101T000000Z-0000000000000000"


def test_recorder_module_with_contextmanager_matches_its_source() -> None:
    relative = "src/aiflow/mutation_evidence.py"
    materials = {relative: (REPOSITORY_ROOT / relative).read_bytes()}
    assert _module_identity_matches(
        REPOSITORY_ROOT, materials, mutation_evidence.__name__, mutation_evidence
    )


@pytest.mark.parametrize(
    "previous",
    [
        b"from contextlib import contextmanager\n@contextmanager\ndef example():\n    yield 1\n",
        b"class Example:\n    def outcome(self):\n        return 1\n",
    ],
)
def test_loaded_code_must_match_the_current_subject(tmp_path: Path, previous: bytes) -> None:
    relative = "src/aiflow/example.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    module = ModuleType("aiflow.example")
    module.__file__ = str(path)
    current = previous.replace(b"1\n", b"2\n")
    path.write_bytes(previous)
    exec(compile(previous, str(path), "exec", dont_inherit=True), vars(module))
    path.write_bytes(current)
    materials = {relative: current}
    assert not _module_identity_matches(tmp_path, materials, module.__name__, module)
    exec(compile(current, str(path), "exec", dont_inherit=True), vars(module))
    assert _module_identity_matches(tmp_path, materials, module.__name__, module)


def _mocked_run() -> MutationRun:
    manifest = load_mutation_manifest(REPOSITORY_ROOT)
    return MutationRun(
        manifest.manifest_id,
        "a" * 40,
        tuple(MutationProbe(item.mutation_id, 0, 1, False, 0, None) for item in manifest.mutations),
        True,
        None,
    )


def _write_synthetic_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, MutationEvidenceArtifact]:
    """Private mapper seam only: no task lookup, Git inspection, or runner call."""
    root = tmp_path / "r"
    record_root = root / ".ai" / "tasks" / "TASK-0014" / "logs" / RECORD_ID
    record_root.mkdir(parents=True)
    manifest = load_mutation_manifest(REPOSITORY_ROOT)
    materials = {item.target: b"synthetic fixture\n" for item in manifest.mutations}
    monkeypatch.setattr(mutation_evidence, "subject_materials", lambda *_: materials)
    artifact = _make_artifact(
        root,
        "TASK-0014",
        "a" * 40,
        run=_mocked_run(),
        now=datetime(2000, 1, 1, tzinfo=timezone.utc),
        record_id=RECORD_ID,
        record_root=record_root,
        task={
            "repository_id": "b85e5a53-4935-4436-bdbc-c26a241bfae8",
            "branch": "synthetic",
            "base_commit": "b" * 40,
            "frozen_spec_sha256": "c" * 64,
        },
        classification={"classification_input_sha256": "d" * 64},
        policy_sha="e" * 64,
        manifest=manifest,
        manifest_sha=_sha256_bytes((REPOSITORY_ROOT / CANONICAL_MANIFEST_PATH).read_bytes()),
        runner_sha=_sha256_bytes((REPOSITORY_ROOT / "src/aiflow/mutation_runner.py").read_bytes()),
        subject_materials_sha256=materials_sha256(materials),
    )
    return root, artifact


def test_targeted_mutation_evidence_synthetic_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exit-only synthetic run records the codes without claiming attribution."""
    root, artifact = _write_synthetic_artifact(tmp_path, monkeypatch)
    value = json.loads((root / artifact.evidence_ref).read_text(encoding="utf-8"))
    unsigned = {key: item for key, item in value.items() if key != "mutation_evidence_sha256"}
    assert value["record_id"] == artifact.record_id == RECORD_ID
    assert value["mutation_evidence_sha256"] == artifact.mutation_evidence_sha256
    assert value["mutation_evidence_sha256"] == _sha256_bytes(_canonical_bytes(unsigned))
    assert value["schema_version"] == "2.0"
    assert [item["outcome"] for item in value["results"]] == ["unverified"] * 5
    assert value["uncovered_mutation_ids"] == [f"MUT-V2-{index:03d}" for index in range(1, 6)]
    assert len(artifact.log_refs) == 5
    for result, reference in zip(value["results"], artifact.log_refs, strict=True):
        log_path = root / reference
        log = json.loads(log_path.read_text(encoding="utf-8"))
        assert result["log_ref"] == reference
        assert result["log_sha256"] == _sha256_bytes(log_path.read_bytes())
        assert log["outcome"] == result["outcome"] == "unverified"
        assert log["baseline_exit_code"] == result["baseline_exit_code"] == 0
        assert log["mutant_exit_code"] == result["mutant_exit_code"] == 1
        for key in (
            "mutation_id",
            "safeguard_id",
            "target",
            "target_symbol",
            "operator",
            "expected_detector",
            "expected_outcome",
        ):
            assert log[key] == result[key]
