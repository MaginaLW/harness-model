"""Build synthetic process observations for CI and Gate replay tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from aiflow import mutation_evidence as evidence
from aiflow.mutation_manifest import CANONICAL_MANIFEST_PATH, load_mutation_manifest
from aiflow.mutation_materials import materials_sha256
from aiflow.storage import resolve_task_path
from aiflow.task_service import load_task_record
from tests.unit.test_mutation_evidence import (
    _record_synthetic_launch,
    _run,
    _synthetic_materials,
    _v2_projection,
)


def replay_synthetic_mutation(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    now: datetime,
    first_survived: bool = False,
) -> tuple[evidence.MutationEvidenceArtifact, dict[str, Any]]:
    """Write synthetic observations, then replay their logs and projection through public APIs."""
    task_id = "TASK-0001"
    task = dict(load_task_record(repository, task_id).task)
    task.update(base_commit="b" * 40, subject_commit="a" * 40, frozen_spec_sha256="c" * 64)
    classification = {"classification_input_sha256": "d" * 64}
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[1])
    materials = _synthetic_materials(manifest)
    # The fixture supplies subject inputs; both reads check the emitted evidence and launch claim.
    monkeypatch.setattr(evidence, "_validate_bindings", lambda *_: (task, classification, "e" * 64))
    monkeypatch.setattr(evidence, "_load_manifest", lambda _: manifest)
    monkeypatch.setattr(evidence, "subject_materials", lambda *_: materials)
    monkeypatch.setattr(evidence, "loaded_engine_matches", lambda *_: True)
    monkeypatch.setattr(
        evidence, "material_file_matches", lambda _root, name, content: materials[name] == content
    )
    monkeypatch.setattr(
        evidence, "mutation_bytes", lambda _item, data: data + b"synthetic mutant\n"
    )
    run = _run(manifest)
    if first_survived:
        first = _run(manifest, mutant=0).probes[0]
        run = replace(run, probes=(first, *run.probes[1:]))
    record_id = f"MUTRUN-{now:%Y%m%dT%H%M%SZ}-0000000000000000"
    record_root = resolve_task_path(repository, task_id, Path("logs") / record_id)
    record_root.mkdir(parents=True)
    artifact = evidence._make_artifact(
        repository,
        task_id,
        run.subject_commit,
        run=run,
        now=now,
        record_id=record_id,
        record_root=record_root,
        task=task,
        classification=classification,
        policy_sha="e" * 64,
        manifest=manifest,
        manifest_sha=evidence._sha256_bytes(materials[CANONICAL_MANIFEST_PATH.as_posix()]),
        runner_sha=evidence._sha256_bytes(materials["src/aiflow/mutation_runner.py"]),
        subject_materials_sha256=materials_sha256(materials),
    )
    _record_synthetic_launch(repository, task_id, artifact, now, monkeypatch)
    value = dict(
        evidence.load_targeted_mutation_evidence(repository, task_id, artifact.evidence_ref)
    )
    facts = evidence.consume_targeted_mutation_evidence(
        repository, task_id, _v2_projection(value, artifact.evidence_ref)
    )
    assert value["schema_version"] == "2.0"
    expected = ["survived" if first_survived else "killed"] + ["killed"] * 4
    assert [item["outcome"] for item in facts.results] == expected
    assert facts.passed is (not first_survived)
    assert facts.reason_code == ("MUTATION_EVIDENCE_NOT_KILLED" if first_survived else None)
    return artifact, value
