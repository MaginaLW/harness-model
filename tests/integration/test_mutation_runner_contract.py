"""Real, action-approved contract replay for the fixed Phase 02 mutations."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from aiflow.mutation_manifest import CANONICAL_MANIFEST_PATH, load_mutation_manifest
from aiflow.mutation_runner import MutationProbe, MutationRun, run_targeted_mutations

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(".ai/schemas/mutation-manifest.schema.json")


def _git_bytes(*arguments: str) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        timeout=10,
        shell=False,
    )
    assert result.returncode == 0, (arguments, result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def _controlled_hashes() -> dict[str, str]:
    manifest = load_mutation_manifest(REPOSITORY_ROOT)
    paths = {CANONICAL_MANIFEST_PATH.as_posix(), SCHEMA_PATH.as_posix()}
    for declaration in manifest.mutations:
        paths.add(declaration.target)
        paths.add(declaration.expected_detector.split("::", maxsplit=1)[0])
    return {
        relative: hashlib.sha256((REPOSITORY_ROOT / relative).read_bytes()).hexdigest()
        for relative in sorted(paths)
    }


def test_fixed_mutations_run_only_in_isolated_worktrees() -> None:
    """This test requires the exact current single-use delete action approval."""
    subject = _git_bytes("rev-parse", "HEAD").decode("ascii").strip()
    status_before = _git_bytes("status", "--porcelain=v1", "--untracked-files=all")
    registry_before = _git_bytes("worktree", "list", "--porcelain")
    hashes_before = _controlled_hashes()

    result = run_targeted_mutations(REPOSITORY_ROOT, subject)

    assert isinstance(result, MutationRun)
    assert result.manifest_id == "phase-02-critical"
    assert result.subject_commit == subject
    assert result.main_tree_unchanged is True
    assert result.reason_code is None
    assert isinstance(result.probes, tuple)
    assert all(isinstance(probe, MutationProbe) for probe in result.probes)
    assert tuple(probe.mutation_id for probe in result.probes) == tuple(
        item.mutation_id for item in load_mutation_manifest(REPOSITORY_ROOT).mutations
    )
    assert tuple(probe.baseline_exit_code for probe in result.probes) == (0, 0, 0, 0, 0)
    assert tuple(probe.mutant_exit_code for probe in result.probes) == (1, 1, 1, 1, 1)
    assert all(probe.timed_out is False for probe in result.probes)
    assert all(probe.duration_ms >= 0 for probe in result.probes)
    assert all(probe.reason_code is None for probe in result.probes)

    assert _controlled_hashes() == hashes_before
    assert _git_bytes("status", "--porcelain=v1", "--untracked-files=all") == status_before
    assert _git_bytes("worktree", "list", "--porcelain") == registry_before
