"""Chapter 13.4 negative self-hosting chains through public entry points.

The unit and integration suites exercise the individual contracts.  These
scenarios deliberately keep their assertions at the boundary: an invalid fact
must be rejected before it can create a verification artefact or make an
existing REVIEW task merge-ready.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
E2E_TESTS = ROOT / "tests" / "e2e"
INTEGRATION_TESTS = ROOT / "tests" / "integration"
if str(E2E_TESTS) not in sys.path:
    sys.path.insert(0, str(E2E_TESTS))
if str(INTEGRATION_TESTS) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_TESTS))

from scenario_support import TASK_ID, complete_spec, prepare_task, review_package  # noqa: E402
from test_begin_close_commands import create_repository, make_ready, run_git, start  # noqa: E402
from test_v2_verifier_scenario import (  # noqa: E402
    _passed_v2_pre,
    _record_approving_review,
)
from test_verify_command import _enable_v2, _prepare  # noqa: E402

from aiflow import gate as gate_service  # noqa: E402
from aiflow import mutation_evidence, mutation_runner, verification_service  # noqa: E402
from aiflow.cli import main  # noqa: E402
from aiflow.decision_units import classification_input_digest, parse_decision_units  # noqa: E402
from aiflow.errors import ContractError  # noqa: E402
from aiflow.gate import evaluate_gate  # noqa: E402
from aiflow.mutation_manifest import load_mutation_manifest  # noqa: E402
from aiflow.observation import parse_observation  # noqa: E402
from aiflow.observation_service import apply_observation  # noqa: E402
from aiflow.review_service import ReviewAssessment  # noqa: E402
from aiflow.storage import (  # noqa: E402
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record  # noqa: E402


def _task_bytes(repository: Path) -> dict[Path, bytes]:
    directory = resolve_task_path(repository, "TASK-0001")
    return {
        path.relative_to(directory): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize(("actor", "message"), [("implementer", "must differ"), (" ", "required")])
def test_invalid_v2_actor_verify_fails_before_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    actor: str,
    message: str,
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    before = _task_bytes(repository)

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("invalid verifier actor reached plan or runner")

    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)

    assert main(["verify", "TASK-0001", "--actor", actor]) == 1
    assert message in capsys.readouterr().err.lower()
    assert _task_bytes(repository) == before
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "IMPLEMENTING"


def test_survived_ci_mutation_replay_rejects_without_source_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CI reaches the real public consumer and rejects one authentic survived result."""
    repository = _prepare(tmp_path, monkeypatch, route="REVIEW")
    prepared = load_task_record(repository, "TASK-0001").task
    prepared["decision_units"][0]["impact_scope"] = ["src/**"]
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), prepared)
    prepared_classification = read_task_json(repository, "TASK-0001", "classification.json")
    assert isinstance(prepared_classification, dict)
    prepared_classification["classification_input_sha256"] = classification_input_digest(
        prepared, parse_decision_units(prepared)
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"),
        prepared_classification,
    )
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)
    record = load_task_record(repository, "TASK-0001")
    manifest = load_mutation_manifest(ROOT)
    record_id = "MUTRUN-20000101T000000Z-0000000000000000"
    record_root = resolve_task_path(repository, "TASK-0001", Path("logs") / record_id)
    record_root.mkdir(parents=True)
    task = {
        "task_id": "TASK-0001",
        "repository_id": record.task["repository_id"],
        "branch": record.task["branch"],
        "base_commit": "b" * 40,
        "subject_commit": "a" * 40,
        "frozen_spec_sha256": "c" * 64,
    }
    classification = {"classification_input_sha256": "d" * 64}
    run = mutation_runner.MutationRun(
        manifest.manifest_id,
        "a" * 40,
        tuple(
            mutation_runner.MutationProbe(
                item.mutation_id,
                0,
                0 if index == 0 else 1,
                False,
                1,
                None,
            )
            for index, item in enumerate(manifest.mutations)
        ),
        True,
        None,
    )
    monkeypatch.setattr(
        mutation_evidence, "_validate_bindings", lambda *_args: (task, classification, "e" * 64)
    )
    monkeypatch.setattr(mutation_evidence, "_load_manifest", lambda _root: manifest)
    monkeypatch.setattr(mutation_evidence, "_source_sha256", lambda _path: "f" * 64)
    artifact = mutation_evidence._make_artifact(
        repository,
        "TASK-0001",
        "a" * 40,
        run=run,
        now=datetime(2000, 1, 1, tzinfo=timezone.utc),
        record_id=record_id,
        record_root=record_root,
        task=task,
        classification=classification,
        policy_sha="e" * 64,
        manifest=manifest,
        manifest_sha="f" * 64,
        runner_sha="f" * 64,
    )
    artifact_value = json.loads((repository / artifact.evidence_ref).read_text(encoding="utf-8"))
    assert artifact_value["results"][0]["outcome"] == "survived"
    assert artifact_value["uncovered_mutation_ids"] == ["MUT-V2-001"]
    source = {
        "schema_version": "2.0",
        "task_id": "TASK-0001",
        "decision_unit_ids": ["DU-001"],
        "verification_level": "V2",
        "mode": "local",
        "phase": "final",
        "conclusion": "passed",
        "verifier_actor": "verifier",
        "verifier_context_sha256": "c" * 64,
        "verification_snapshot_sha256": "s" * 64,
        "review_refs": {
            "design": {"review_id": "REV-0001", "context_sha256": "d" * 64},
            "implementation": {"review_id": "REV-0002", "context_sha256": "i" * 64},
        },
        "targeted_mutation": {
            "evidence_ref": artifact.evidence_ref,
            "mutation_evidence_sha256": artifact.mutation_evidence_sha256,
            "manifest_ref": artifact_value["manifest_ref"],
            "results": [
                {
                    "mutation_id": result["mutation_id"],
                    "outcome": result["outcome"],
                    "log_ref": result["log_ref"],
                }
                for result in artifact_value["results"]
            ],
        },
    }
    original_read = verification_service.read_task_json
    monkeypatch.setattr(
        verification_service,
        "read_task_json",
        lambda *a, **k: (
            source if len(a) >= 3 and a[2] == "evidence.json" else original_read(*a, **k)
        ),
    )
    monkeypatch.setattr(verification_service, "validate_v2_snapshot", lambda *_args: None)
    monkeypatch.setattr(
        verification_service,
        "evaluate_freshness",
        lambda *_args: SimpleNamespace(status="fresh"),
    )
    monkeypatch.setattr(verification_service, "load_verifier_context", lambda *_args: object())
    monkeypatch.setattr(verification_service, "build_verifier_context", lambda *_args: object())
    monkeypatch.setattr(
        verification_service, "validate_verifier_context_current", lambda *_args: None
    )
    monkeypatch.setattr(
        verification_service,
        "latest_review_assessment",
        lambda *_args, **_kwargs: ReviewAssessment(
            {"context_sha256": "i" * 64 if _args[2] == "implementation" else "d" * 64},
            {"review_id": "REV-0002" if _args[2] == "implementation" else "REV-0001"},
        ),
    )
    monkeypatch.setattr(
        verification_service,
        "parse_verification_plan",
        lambda *_a, **_k: pytest.fail("survived mutant reached plan"),
    )
    run_directory = tmp_path / "ci"
    run_directory.mkdir()
    before = _task_bytes(repository)
    refs_before = run_git(repository, "show-ref")
    with pytest.raises(ContractError) as error:
        verification_service.verify_task(
            repository,
            "TASK-0001",
            ci=True,
            ci_run_dir=run_directory,
            output=run_directory / "evidence.json",
        )
    assert error.value.code == "MUTATION_EVIDENCE_NOT_KILLED"
    assert _task_bytes(repository) == before
    assert run_git(repository, "show-ref") == refs_before
    assert not (run_directory / "evidence.json").exists()

    original_gate_read = gate_service.read_task_json
    monkeypatch.setattr(
        gate_service,
        "read_task_json",
        lambda *args, **kwargs: (
            source
            if len(args) >= 3 and args[2] == "evidence.json"
            else original_gate_read(*args, **kwargs)
        ),
    )
    monkeypatch.setattr(gate_service, "validate_v2_snapshot", lambda *_args: None)
    monkeypatch.setattr(
        gate_service, "evaluate_freshness", lambda *_args: SimpleNamespace(status="fresh")
    )
    monkeypatch.setattr(gate_service, "load_verifier_context", lambda *_args: object())
    monkeypatch.setattr(gate_service, "build_verifier_context", lambda *_args: object())
    monkeypatch.setattr(gate_service, "validate_verifier_context_current", lambda *_args: None)
    monkeypatch.setattr(
        gate_service,
        "latest_review_assessment",
        lambda *_args, **_kwargs: ReviewAssessment(
            {"context_sha256": "i" * 64 if _args[2] == "implementation" else "d" * 64},
            {"review_id": "REV-0002" if _args[2] == "implementation" else "REV-0001"},
        ),
    )
    gate_decision = evaluate_gate(repository, "TASK-0001")
    assert gate_decision.passed is False
    assert "GATE_V2_MUTATION_NOT_KILLED" in gate_decision.reason_codes
    assert _task_bytes(repository) == before
    assert run_git(repository, "show-ref") == refs_before


def test_scope_observation_persists_escalation_and_blocks_begin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    task = load_task_record(repository, "TASK-0001").task
    observation = parse_observation(
        {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "base_commit": task["base_commit"],
            "subject_commit": task["subject_commit"],
            "policy_sha256": read_task_json(repository, "TASK-0001", "classification.json")[
                "policy_sha256"
            ],
            "source": "hook_pre_commit",
            "kind": "scope_out_of_bounds",
            "summary": {"paths": ["outside.txt"]},
        }
    )
    applied = apply_observation(repository, "TASK-0001", observation, actor="hook_pre_commit")
    assert applied.decision.disposition.value == "escalate"
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "ESCALATED"
    assert record.events[-1]["event_type"] == "task_escalated"
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 1


def test_latest_non_approving_review_prevents_approval_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A current REQUEST_CHANGES record wins over an older APPROVE everywhere."""
    repository, unit, _expected = prepare_task(tmp_path, monkeypatch, "review-workflow-change")
    unit["verification_requirements"] = {
        "acceptance_required": False,
        "integration_required": False,
        "targeted_mutation_required": False,
        "independent_verifier_required": True,
    }
    task_path = resolve_task_path(repository, TASK_ID, "task.yaml")
    task = read_task_yaml(repository, TASK_ID, "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [unit]
    atomic_write_yaml(task_path, task)
    resolve_task_path(repository, TASK_ID, "spec.md").write_text(
        complete_spec(unit), encoding="utf-8"
    )

    assert main(["classify", TASK_ID, "--actor", "classifier"]) == 0
    assert main(["freeze", TASK_ID, "--actor", "specifier"]) == 0
    design_context = _record_approving_review(repository, "design", "REV-1001", tmp_path)
    assert (
        main(
            [
                "approve",
                TASK_ID,
                "--type",
                "spec",
                "--actor",
                "reviewer",
                "--reason",
                "design approved",
            ]
        )
        == 0
    )
    assert main(["begin", TASK_ID, "--actor", "implementer"]) == 0

    pre = _passed_v2_pre(repository, design_context)
    evidence_path = resolve_task_path(repository, TASK_ID, "evidence.json")
    atomic_write_json(evidence_path, pre)
    verification_service._start_local_verification(
        repository, TASK_ID, load_task_record(repository, TASK_ID), "verifier"
    )
    assert (
        verification_service._finish_local_verification(
            repository,
            TASK_ID,
            actor="verifier",
            conclusion="passed",
            route="REVIEW",
        )
        == "WAITING_FOR_FINAL_REVIEW"
    )
    implementation_context = _record_approving_review(
        repository, "implementation", "REV-1002", tmp_path
    )
    negative_review = tmp_path / "REV-1003.json"
    atomic_write_json(
        negative_review,
        {
            "schema_version": "1.0",
            "review_id": "REV-1003",
            "review_stage": "implementation",
            "recorded_at": "2026-08-23T05:01:00Z",
            "context_sha256": implementation_context["context_sha256"],
            "outcome": "REQUEST_CHANGES",
            "summary": "The latest current review rejects finalization.",
            "findings": [],
        },
    )
    assert (
        main(
            [
                "review",
                "record",
                TASK_ID,
                "--input",
                str(negative_review),
                "--actor",
                "second-reviewer",
            ]
        )
        == 0
    )

    evidence_before = evidence_path.read_bytes()
    approvals_path = resolve_task_path(repository, TASK_ID, "approvals.json")
    approvals_before = approvals_path.read_bytes()
    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(repository, TASK_ID, actor="verifier", finalize=True)
    assert caught.value.code == "REVIEW_OUTCOME_NOT_APPROVABLE"
    assert evidence_path.read_bytes() == evidence_before
    assert read_task_json(repository, TASK_ID, "evidence.json")["phase"] == (
        "pre_implementation_review"
    )

    resolve_task_path(repository, TASK_ID, "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    assert (
        main(
            [
                "approve",
                TASK_ID,
                "--type",
                "code",
                "--actor",
                "approver",
                "--reason",
                "must not fall back to REV-1002",
            ]
        )
        == 1
    )
    assert approvals_path.read_bytes() == approvals_before
    decision = evaluate_gate(repository, TASK_ID)
    assert decision.passed is False
    assert "GATE_V2_EVIDENCE_NOT_FINAL" in decision.reason_codes
    assert "GATE_V2_REVIEW_STALE" in decision.reason_codes
    assert load_task_record(repository, TASK_ID).task["current_state"] == (
        "WAITING_FOR_FINAL_REVIEW"
    )
