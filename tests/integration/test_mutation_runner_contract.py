"""Dual-mode mutation-evidence contract test; ordinary runs never call runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from aiflow.mutation_evidence import (
    MutationEvidenceArtifact,
    _canonical_bytes,
    _make_artifact,
    _sha256_bytes,
    _task0014_production_subject,
    load_targeted_mutation_evidence,
    record_targeted_mutation_evidence,
)
from aiflow.mutation_manifest import CANONICAL_MANIFEST_PATH, load_mutation_manifest
from aiflow.mutation_runner import MutationProbe, MutationRun

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(".ai/schemas/mutation-manifest.schema.json")
RECORD_ID = "MUTRUN-20000101T000000Z-0000000000000000"


def _git_bytes(*arguments: str) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        timeout=10,
        shell=False,
    )
    assert result.returncode == 0
    return result.stdout


def _controlled_hashes() -> dict[str, str]:
    manifest = load_mutation_manifest(REPOSITORY_ROOT)
    paths = {CANONICAL_MANIFEST_PATH.as_posix(), SCHEMA_PATH.as_posix()}
    for item in manifest.mutations:
        paths.update((item.target, item.expected_detector.split("::", 1)[0]))
    return {
        item: hashlib.sha256((REPOSITORY_ROOT / item).read_bytes()).hexdigest() for item in paths
    }


def _mocked_run() -> MutationRun:
    manifest = load_mutation_manifest(REPOSITORY_ROOT)
    return MutationRun(
        manifest.manifest_id,
        "a" * 40,
        tuple(MutationProbe(item.mutation_id, 0, 1, False, 0, None) for item in manifest.mutations),
        True,
        None,
    )


def _write_synthetic_artifact(tmp_path: Path) -> tuple[Path, MutationEvidenceArtifact]:
    """Private mapper seam only: no task lookup, Git inspection, or runner call."""
    root = tmp_path / "synthetic-repository"
    record_root = root / ".ai" / "tasks" / "TASK-0014" / "logs" / RECORD_ID
    record_root.mkdir(parents=True)
    manifest = load_mutation_manifest(REPOSITORY_ROOT)
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
    )
    return root, artifact


def test_targeted_mutation_evidence_dual_mode(tmp_path: Path) -> None:
    """Production has one public recorder; inactive mode writes only a mock record."""
    subject = _task0014_production_subject(REPOSITORY_ROOT)
    if subject is None:
        root, artifact = _write_synthetic_artifact(tmp_path)
        value = json.loads((root / artifact.evidence_ref).read_text(encoding="utf-8"))
        unsigned = {key: item for key, item in value.items() if key != "mutation_evidence_sha256"}
        assert value["record_id"] == artifact.record_id == RECORD_ID
        assert value["mutation_evidence_sha256"] == artifact.mutation_evidence_sha256
        assert value["mutation_evidence_sha256"] == _sha256_bytes(_canonical_bytes(unsigned))
        assert [item["outcome"] for item in value["results"]] == ["killed"] * 5
        assert value["uncovered_mutation_ids"] == []
        assert len(artifact.log_refs) == 5
        for result, reference in zip(value["results"], artifact.log_refs, strict=True):
            log_path = root / reference
            log = json.loads(log_path.read_text(encoding="utf-8"))
            assert result["log_ref"] == reference
            assert result["log_sha256"] == _sha256_bytes(log_path.read_bytes())
            assert log["outcome"] == result["outcome"] == "killed"
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
        return

    # Requires the separate, current single-use action approval before collection.
    status_before = _git_bytes("status", "--porcelain=v1", "--untracked-files=all")
    registry_before = _git_bytes("worktree", "list", "--porcelain")
    hashes_before = _controlled_hashes()
    artifact = record_targeted_mutation_evidence(REPOSITORY_ROOT, "TASK-0014", subject)
    value = load_targeted_mutation_evidence(REPOSITORY_ROOT, "TASK-0014", artifact.evidence_ref)
    assert value["mutation_evidence_sha256"] == artifact.mutation_evidence_sha256
    assert value["main_tree_unchanged"] is True
    assert value["run_reason_code"] is None
    assert [item["baseline_exit_code"] for item in value["results"]] == [0] * 5
    assert [item["mutant_exit_code"] for item in value["results"]] == [1] * 5
    assert [item["outcome"] for item in value["results"]] == ["killed"] * 5
    assert value["uncovered_mutation_ids"] == []
    assert len(artifact.log_refs) == 5
    assert tuple(item["log_ref"] for item in value["results"]) == artifact.log_refs
    assert _controlled_hashes() == hashes_before
    assert _git_bytes("status", "--porcelain=v1", "--untracked-files=all") == status_before
    assert _git_bytes("worktree", "list", "--porcelain") == registry_before
