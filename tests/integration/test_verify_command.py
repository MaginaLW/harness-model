"""Integration coverage for local and read-only CI verification lifecycles."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest
from test_begin_close_commands import commit_all, create_repository, make_ready, run_git, start

from aiflow import cli, mutation_evidence, mutation_runner, verification_service
from aiflow.approval import canonical_action_sha256, validate_action_file
from aiflow.cli import build_parser, main
from aiflow.decision_units import classification_input_digest, parse_decision_units
from aiflow.errors import ContractError, StorageError
from aiflow.mutation_manifest import load_mutation_manifest
from aiflow.review_service import ReviewAssessment
from aiflow.storage import (
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    resolve_task_path,
)
from aiflow.task_service import load_task_record
from aiflow.verification import (
    VerificationCheck,
    VerificationContext,
    VerificationExecution,
    VerificationPlan,
)
from aiflow.verification_service import VerifyResult


def _mutation_artifact(outcome: str = "killed", task_id: str = "TASK-0001") -> dict[str, object]:
    results = [
        {"mutation_id": f"MUT-V2-{index:03d}", "outcome": outcome, "log_ref": None}
        for index in range(1, 6)
    ]
    return {
        "evidence_ref": (
            f".ai/tasks/{task_id}/logs/MUTRUN-20260825T120000Z-"
            "0000000000000000/targeted-mutation/evidence.json"
        ),
        "mutation_evidence_sha256": "1" * 64,
        "manifest_ref": ".ai/mutations/phase-02-critical-manifest.json",
        "results": results,
        "uncovered_mutation_ids": (
            [] if outcome == "killed" else [item["mutation_id"] for item in results]
        ),
    }


def test_v2_mutation_collection_seam_records_once_then_publicly_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    evidence_ref = (
        ".ai/tasks/TASK-0001/logs/MUTRUN-20260825T120000Z-"
        "0000000000000000/targeted-mutation/evidence.json"
    )
    expected = _mutation_artifact()
    expected_facts = mutation_evidence.TargetedMutationFacts(
        True,
        None,
        evidence_ref,
        str(expected["mutation_evidence_sha256"]),
        str(expected["manifest_ref"]),
        tuple(expected["results"]),  # type: ignore[arg-type]
    )

    def record(
        _root: Path, task_id: str, subject: str
    ) -> mutation_evidence.MutationEvidenceArtifact:
        calls.append((task_id, subject))
        return mutation_evidence.MutationEvidenceArtifact(
            "MUTRUN-20260825T120000Z-0000000000000000",
            evidence_ref,
            str(expected["mutation_evidence_sha256"]),
            (),
        )

    def consume(
        _root: Path,
        task_id: str,
        evidence: dict[str, object],
        *,
        recorded_artifact: mutation_evidence.MutationEvidenceArtifact,
    ) -> mutation_evidence.TargetedMutationFacts:
        assert evidence == {}
        calls.append((task_id, recorded_artifact.evidence_ref))
        return expected_facts

    monkeypatch.setattr(verification_service, "record_targeted_mutation_evidence", record)
    monkeypatch.setattr(verification_service, "consume_targeted_mutation_evidence", consume)

    assert (
        verification_service._v2_targeted_mutation_artifact(tmp_path, "TASK-0001", "f" * 40)
        == expected_facts
    )
    assert calls == [
        ("TASK-0001", "f" * 40),
        ("TASK-0001", evidence_ref),
    ]


def _plan(*, failed: bool = False):
    def build(_bundle, context: VerificationContext, *, level: str) -> VerificationPlan:
        run_dir = (
            context.ci_run_dir.resolve()
            if context.ci_run_dir is not None
            else (
                context.repository_root
                / ".ai"
                / "tasks"
                / context.task_id
                / "logs"
                / context.run_id
            ).resolve()
        )
        argv = (
            sys.executable,
            "-c",
            "import sys; print('checked'); sys.exit(1)" if failed else "print('checked')",
        )
        check = VerificationCheck(
            "smoke",
            level,
            argv,
            {},
            context.repository_root.resolve(),
            10,
            True,
            "exit_zero",
        )
        execution = VerificationExecution("EXEC-001", argv, {}, check.cwd, 10, ("smoke",))
        return VerificationPlan(
            level,
            run_dir,
            (check,),
            (execution,),
            (),
            (),
            context.subject_commit,
        )

    return build


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    route: str = "AUTO",
) -> Path:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    make_ready(repository, route=route, valid_approval=route == "REVIEW")
    if route == "REVIEW":
        approvals = read_task_json(repository, "TASK-0001", "approvals.json")
        assert isinstance(approvals, list)
        approvals[0]["base_commit"] = load_task_record(repository, "TASK-0001").task["base_commit"]
        atomic_write_json(resolve_task_path(repository, "TASK-0001", "approvals.json"), approvals)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan())
    return repository


def _enable_v2(repository: Path) -> None:
    """Turn the prepared task into a current V2 classification fixture."""
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    classification["schema_version"] = "2.0"
    classification["effective_verification_level"] = "V2"
    entry = classification["classifications"][0]
    assert isinstance(entry, dict)
    entry["verification_level"] = "V2"
    entry["verification_rule_ids"] = [
        "VERIFICATION-V2-ACCEPTANCE-REQUIRED",
        "VERIFICATION-V2-INTEGRATION-REQUIRED",
        "VERIFICATION-V2-TARGETED-MUTATION-REQUIRED",
        "VERIFICATION-V2-INDEPENDENT-VERIFIER-REQUIRED",
    ]
    entry["verification_explanations"] = ["V2 verification is required."]
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"), classification
    )


def _enable_v2_action_requirement(repository: Path) -> None:
    """Add the permission facts enforced by the real mutation action boundary."""
    record = load_task_record(repository, "TASK-0001")
    task = record.task
    unit = task["decision_units"][0]
    assert isinstance(unit, dict)
    unit["permission_requirements"] = ["action_approval"]
    unit["verification_requirements"] = {
        "acceptance_required": True,
        "integration_required": True,
        "targeted_mutation_required": True,
        "independent_verifier_required": True,
    }
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    classification["classification_input_sha256"] = classification_input_digest(
        task, parse_decision_units(task)
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"), classification
    )


def _approve_v2_action(
    repository: Path,
    suffix: str,
    *,
    parameter_summary: str | None = None,
) -> tuple[Path, str]:
    record = load_task_record(repository, "TASK-0001")
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    action_path = resolve_task_path(
        repository,
        "TASK-0001",
        f"action-v2-targeted-mutation-{suffix}.json",
    )
    atomic_write_json(
        action_path,
        {
            "decision_unit_id": "DU-001",
            "classification_input_sha256": classification["classification_input_sha256"],
            "action_type": "targeted_mutation_v2",
            "target": "TASK-0001",
            "parameter_summary": parameter_summary
            or f"fixed V2 mutation collection {suffix}; one runner; five worktrees maximum",
            "subject_commit": record.task["subject_commit"],
            "conditions": [
                f"Action {suffix}: launch, failure, or interruption consumes approval; no retry."
            ],
            "expires_at": "2999-01-01T00:00:00Z",
            "single_use": True,
        },
    )
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "action",
                "--actor",
                "user",
                "--reason",
                f"approve fixed V2 mutation collection {suffix}",
                "--action-file",
                str(action_path),
            ]
        )
        == 0
    )
    approvals = read_task_json(repository, "TASK-0001", "approvals.json")
    assert isinstance(approvals, list)
    return action_path, str(approvals[-1]["action_sha256"])


def test_v2_recorder_without_action_approval_never_calls_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    record = load_task_record(repository, "TASK-0001")
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("runner must not run without current action approval")

    monkeypatch.setattr(mutation_evidence, "run_targeted_mutations", unexpected)
    with pytest.raises(ContractError) as caught:
        mutation_evidence.record_targeted_mutation_evidence(
            repository, "TASK-0001", str(record.task["subject_commit"])
        )

    assert caught.value.code == "ACTION_APPROVAL_REQUIRED"


def test_v2_recorder_rejects_pending_action_approval_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "approval_pending.json"),
        {"incomplete": True},
    )

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("pending approval transaction must fail before runner")

    monkeypatch.setattr(mutation_evidence, "run_targeted_mutations", unexpected)
    with pytest.raises(ContractError) as caught:
        mutation_evidence.record_targeted_mutation_evidence(repository, "TASK-0001", subject)

    assert caught.value.code == "ACTION_APPROVAL_PENDING"


@pytest.mark.parametrize(
    ("attestation_path", "reaches_consume"),
    [
        (".ai/tasks/TASK-0001/attestation.md", True),
        ("src/attestation.py", False),
        (".ai/tasks/TASK-0002/attestation.md", False),
    ],
)
def test_v2_mutation_binding_allows_only_current_task_governance_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attestation_path: str,
    reaches_consume: bool,
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _approve_v2_action(repository, "001")
    subject = str(load_task_record(repository, "TASK-0001").task["subject_commit"])
    path = repository / attestation_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("attestation\n", encoding="utf-8")
    commit_all(repository, "attestation after fixed subject")
    record = load_task_record(repository, "TASK-0001")
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    reached: list[str] = []

    def consume(*_args: object, **_kwargs: object) -> object:
        reached.append("consume")
        raise ContractError("consume seam reached", code="TEST_ACTION_CONSUME_REACHED")

    def unexpected_runner(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("binding failures must precede the runner")

    monkeypatch.setattr(mutation_evidence, "_consume_targeted_mutation_action", consume)
    monkeypatch.setattr(mutation_evidence, "run_targeted_mutations", unexpected_runner)

    with pytest.raises(ContractError) as caught:
        mutation_evidence.record_targeted_mutation_evidence(repository, "TASK-0001", subject)

    assert caught.value.code == (
        "TEST_ACTION_CONSUME_REACHED" if reaches_consume else "MUTATION_EVIDENCE_BINDING_STALE"
    )
    assert reached == (["consume"] if reaches_consume else [])
    task_directory = resolve_task_path(repository, "TASK-0001")
    assert not tuple(task_directory.glob("action-use-*.md"))
    assert not tuple((task_directory / "logs").glob("action-launch-*.json"))
    assert not any(
        event["event_type"] == "approval_recorded"
        and event["payload"].get("action_status") == "consumed"
        for event in load_task_record(repository, "TASK-0001").events
    )


def test_v2_runner_allows_current_task_governance_head_after_subject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _action_path, digest = _approve_v2_action(repository, "001")
    subject = str(load_task_record(repository, "TASK-0001").task["subject_commit"])
    attestation = repository / ".ai" / "tasks" / "TASK-0001" / "attestation.md"
    attestation.write_text("current task governance attestation\n", encoding="utf-8")
    commit_all(repository, "current task governance attestation after subject")

    assert run_git(repository, "rev-parse", "HEAD") != subject
    assert run_git(repository, "merge-base", subject, "HEAD") == subject

    record = load_task_record(repository, "TASK-0001")
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )
    action_use = mutation_evidence._consume_targeted_mutation_action(
        repository,
        "TASK-0001",
        subject,
        task,
        classification,
        policy_sha256,
    )
    mutation_evidence._revalidate_targeted_mutation_action(
        repository, "TASK-0001", subject, action_use
    )
    authorization = mutation_runner._issue_runner_authorization(
        repository,
        "TASK-0001",
        subject,
        action_sha256=action_use.action_sha256,
        receipt_path=action_use.receipt_path,
        action_path=action_use.action_path,
        decision_unit_id=action_use.decision_unit_id,
        spec_sha256=action_use.spec_sha256,
        policy_sha256=action_use.policy_sha256,
        base_commit=action_use.base_commit,
        classification_input_sha256=action_use.classification_input_sha256,
    )
    worktrees_before = run_git(repository, "worktree", "list", "--porcelain")
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])

    def controlled_paths_sentinel(*_args: object, **_kwargs: object) -> tuple[str, ...]:
        raise ContractError("controlled paths seam reached", code="TEST_CONTROLLED_PATHS_REACHED")

    monkeypatch.setattr(mutation_runner, "load_mutation_manifest", lambda _root: manifest)
    monkeypatch.setattr(mutation_runner, "_controlled_paths", controlled_paths_sentinel)
    with pytest.raises(ContractError) as caught:
        mutation_runner.run_targeted_mutations(
            repository,
            subject,
            authorization=authorization,
        )

    assert caught.value.code == "TEST_CONTROLLED_PATHS_REACHED"
    receipt = action_use.receipt_path.read_text(encoding="utf-8")
    assert "Status: `started`" in receipt
    assert "Approval consumed: `true`" in receipt
    task_directory = resolve_task_path(repository, "TASK-0001")
    claim_path = task_directory / "logs" / f"action-launch-{digest}.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    assert set(claim) == {
        "action_sha256",
        "claimed_at",
        "receipt_device",
        "receipt_inode",
        "receipt_ref",
        "schema_version",
        "single_use",
        "subject_commit",
        "task_id",
    }
    assert claim["action_sha256"] == digest
    assert isinstance(claim["claimed_at"], str)
    assert claim["receipt_device"] == action_use.receipt_device
    assert claim["receipt_inode"] == action_use.receipt_inode
    assert claim["receipt_ref"] == action_use.receipt_path.relative_to(repository).as_posix()
    assert claim["schema_version"] == "1.0"
    assert claim["single_use"] is True
    assert claim["subject_commit"] == subject
    assert claim["task_id"] == "TASK-0001"
    assert run_git(repository, "worktree", "list", "--porcelain") == worktrees_before
    assert not tuple((task_directory / "logs").glob("MUTRUN-*/targeted-mutation/evidence.json"))


def test_v2_mutation_binding_rejects_equivalent_nonancestor_business_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    initial = load_task_record(repository, "TASK-0001").task
    base = str(initial["base_commit"])
    business_path = repository / "src" / "equivalent.py"
    business_path.parent.mkdir(exist_ok=True)
    business_path.write_text("same business tree\n", encoding="utf-8")
    run_git(repository, "add", "src/equivalent.py")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "subject business change",
    )
    subject = run_git(repository, "rev-parse", "HEAD")
    task = load_task_record(repository, "TASK-0001").task
    task["subject_commit"] = subject
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    classification = read_task_json(repository, "TASK-0001", "classification.json")
    assert isinstance(classification, dict)
    classification["subject_commit"] = subject
    classification["classification_input_sha256"] = classification_input_digest(
        task, parse_decision_units(task)
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"), classification
    )
    commit_all(repository, "current task governance after subject")
    governance_head = run_git(repository, "rev-parse", "HEAD")

    run_git(repository, "switch", "-c", "equivalent-nonancestor", base)
    business_path.parent.mkdir(exist_ok=True)
    business_path.write_text("same business tree\n", encoding="utf-8")
    run_git(repository, "add", "src/equivalent.py")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "equivalent business change",
    )
    run_git(repository, "checkout", governance_head, "--", ".ai/tasks/TASK-0001")
    commit_all(repository, "current task governance attestation")
    head = run_git(repository, "rev-parse", "HEAD")

    assert run_git(repository, "merge-base", subject, head) != subject
    assert run_git(repository, "show", f"{subject}:src/equivalent.py") == business_path.read_text(
        encoding="utf-8"
    ).rstrip("\n")
    assert run_git(repository, "diff", "--name-only", f"{subject}..{head}").splitlines() == [
        ".ai/tasks/TASK-0001/approvals.json",
        ".ai/tasks/TASK-0001/classification.json",
        ".ai/tasks/TASK-0001/events.jsonl",
        ".ai/tasks/TASK-0001/spec.md",
        ".ai/tasks/TASK-0001/task.yaml",
    ]

    record = load_task_record(repository, "TASK-0001")
    assert record.task["subject_commit"] == subject
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    monkeypatch.setattr(
        mutation_evidence,
        "_consume_targeted_mutation_action",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("consume must not run")),
    )
    monkeypatch.setattr(
        mutation_evidence,
        "run_targeted_mutations",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runner must not run")),
    )

    with pytest.raises(ContractError) as caught:
        mutation_evidence.record_targeted_mutation_evidence(repository, "TASK-0001", subject)

    assert caught.value.code == "MUTATION_EVIDENCE_BINDING_STALE"
    task_directory = resolve_task_path(repository, "TASK-0001")
    assert not tuple(task_directory.glob("action-use-*.md"))
    assert not tuple((task_directory / "logs").glob("action-launch-*.json"))
    assert not any(
        event["event_type"] == "approval_recorded"
        and event["payload"].get("action_status") == "consumed"
        for event in load_task_record(repository, "TASK-0001").events
    )


def test_v2_mutation_action_is_consumed_once_before_collection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    action_path, digest = _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )

    action_use = mutation_evidence._consume_targeted_mutation_action(
        repository,
        "TASK-0001",
        subject,
        task,
        classification,
        policy_sha256,
    )

    assert action_use.action_sha256 == digest
    assert action_use.receipt_path.name == f"action-use-{digest}.md"
    assert "Status: `started`" in action_use.receipt_path.read_text(encoding="utf-8")
    mutation_evidence._revalidate_targeted_mutation_action(
        repository, "TASK-0001", subject, action_use
    )
    launch_arguments = {
        "action_sha256": action_use.action_sha256,
        "receipt_path": action_use.receipt_path,
        "action_path": action_use.action_path,
        "decision_unit_id": action_use.decision_unit_id,
        "spec_sha256": action_use.spec_sha256,
        "policy_sha256": action_use.policy_sha256,
        "base_commit": action_use.base_commit,
        "classification_input_sha256": action_use.classification_input_sha256,
        "receipt_device": action_use.receipt_device,
        "receipt_inode": action_use.receipt_inode,
    }
    mutation_evidence._authorize_targeted_mutation_runner_launch(
        repository, "TASK-0001", subject, **launch_arguments
    )
    assert resolve_task_path(
        repository,
        "TASK-0001",
        f"logs/action-launch-{action_use.action_sha256}.json",
    ).is_file()
    with pytest.raises(ContractError) as caught:
        mutation_evidence._authorize_targeted_mutation_runner_launch(
            repository, "TASK-0001", subject, **launch_arguments
        )
    assert caught.value.code == "ACTION_APPROVAL_USED"
    with pytest.raises(ContractError) as caught:
        mutation_evidence._consume_targeted_mutation_action(
            repository,
            "TASK-0001",
            subject,
            task,
            classification,
            policy_sha256,
        )
    assert caught.value.code == "ACTION_APPROVAL_USED"

    changed_action = read_task_json(repository, "TASK-0001", action_path.name)
    assert isinstance(changed_action, dict)
    changed_action["parameter_summary"] = "changed after receipt"
    atomic_write_json(action_path, changed_action)
    with pytest.raises(ContractError) as caught:
        mutation_evidence._revalidate_targeted_mutation_action(
            repository, "TASK-0001", subject, action_use
        )
    assert caught.value.code == "ACTION_BINDING_STALE"


def test_v2_runner_rejects_synthetic_token_without_consumption_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    action_path, digest = _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )
    receipt = resolve_task_path(repository, "TASK-0001", f"action-use-{digest}.md")
    receipt.write_text("synthetic receipt\n", encoding="utf-8")
    authorization = mutation_runner._issue_runner_authorization(
        repository,
        "TASK-0001",
        subject,
        action_sha256=digest,
        receipt_path=receipt,
        action_path=action_path,
        decision_unit_id="DU-001",
        spec_sha256=str(task["frozen_spec_sha256"]),
        policy_sha256=policy_sha256,
        base_commit=str(task["base_commit"]),
        classification_input_sha256=str(classification["classification_input_sha256"]),
    )

    with pytest.raises(ContractError) as caught:
        mutation_runner._consume_runner_authorization(repository, subject, authorization)

    assert caught.value.code == "ACTION_BINDING_STALE"
    assert not resolve_task_path(
        repository, "TASK-0001", f"logs/action-launch-{digest}.json"
    ).exists()


def test_v2_consumption_ledger_blocks_replay_after_receipt_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )
    action_use = mutation_evidence._consume_targeted_mutation_action(
        repository,
        "TASK-0001",
        subject,
        task,
        classification,
        policy_sha256,
    )
    consumed = load_task_record(repository, "TASK-0001").events[-1]
    assert consumed["payload"]["action_status"] == "consumed"
    assert consumed["payload"]["receipt_device"] == action_use.receipt_device
    assert consumed["payload"]["receipt_inode"] == action_use.receipt_inode

    action_use.receipt_path.unlink()

    with pytest.raises(ContractError) as caught:
        mutation_evidence._consume_targeted_mutation_action(
            repository,
            "TASK-0001",
            subject,
            task,
            classification,
            policy_sha256,
        )
    assert caught.value.code == "ACTION_APPROVAL_USED"


def test_v2_consumption_stays_used_when_event_persistence_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _path, digest = _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )
    original_record_event = mutation_evidence.record_task_event
    monkeypatch.setattr(
        mutation_evidence,
        "record_task_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            StorageError("event unavailable", code="STATE_EVENT_APPEND_FAILED")
        ),
    )
    with pytest.raises(ContractError) as caught:
        mutation_evidence._consume_targeted_mutation_action(
            repository,
            "TASK-0001",
            subject,
            task,
            classification,
            policy_sha256,
        )
    assert caught.value.code == "ACTION_RECEIPT_WRITE_FAILED"
    assert resolve_task_path(repository, "TASK-0001", f"action-use-{digest}.md").is_file()

    monkeypatch.setattr(mutation_evidence, "record_task_event", original_record_event)
    with pytest.raises(ContractError) as caught:
        mutation_evidence._consume_targeted_mutation_action(
            repository,
            "TASK-0001",
            subject,
            task,
            classification,
            policy_sha256,
        )
    assert caught.value.code == "ACTION_APPROVAL_USED"


def test_v2_result_append_rejects_replaced_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )
    action_use = mutation_evidence._consume_targeted_mutation_action(
        repository,
        "TASK-0001",
        subject,
        task,
        classification,
        policy_sha256,
    )
    original = action_use.receipt_path.with_suffix(".original")
    action_use.receipt_path.replace(original)
    replacement = "replacement must remain unchanged\n"
    action_use.receipt_path.write_text(replacement, encoding="utf-8")
    artifact = mutation_evidence.MutationEvidenceArtifact(
        "MUTRUN-20260825T000000Z-0123456789abcdef",
        ".ai/tasks/TASK-0001/logs/MUTRUN-20260825T000000Z-0123456789abcdef/"
        "targeted-mutation/evidence.json",
        "a" * 64,
        (),
    )

    with pytest.raises(ContractError) as caught:
        mutation_evidence._complete_targeted_mutation_action(action_use, artifact)

    assert caught.value.code == "ACTION_RECEIPT_WRITE_FAILED"
    assert action_use.receipt_path.read_text(encoding="utf-8") == replacement
    assert "## Result" not in original.read_text(encoding="utf-8")


def test_v2_action_digest_binds_decision_unit_and_classification() -> None:
    base = {
        "decision_unit_id": "DU-001",
        "classification_input_sha256": "a" * 64,
        "action_type": "targeted_mutation_v2",
        "target": "TASK-0001",
        "parameter_summary": "one fixed collection",
        "subject_commit": "b" * 40,
        "conditions": ["single fixed transaction"],
        "expires_at": "2999-01-01T00:00:00Z",
        "single_use": True,
    }
    normalized = validate_action_file(base, subject_commit="b" * 40)
    changed_unit = validate_action_file(
        {**base, "decision_unit_id": "DU-002"}, subject_commit="b" * 40
    )
    changed_classification = validate_action_file(
        {**base, "classification_input_sha256": "c" * 64},
        subject_commit="b" * 40,
    )

    assert canonical_action_sha256(normalized) != canonical_action_sha256(changed_unit)
    assert canonical_action_sha256(normalized) != canonical_action_sha256(changed_classification)


def test_v2_old_action_approval_is_rejected_after_reclassification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    task = record.task
    unit = task["decision_units"][0]
    assert isinstance(unit, dict)
    unit["planned_actions"] = [*unit["planned_actions"], "reclassified action facts"]
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    classification["classification_input_sha256"] = classification_input_digest(
        task, parse_decision_units(task)
    )
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"), classification
    )
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("stale action approval must fail before runner")

    monkeypatch.setattr(mutation_evidence, "run_targeted_mutations", unexpected)
    with pytest.raises(ContractError) as caught:
        mutation_evidence.record_targeted_mutation_evidence(repository, "TASK-0001", subject)
    assert caught.value.code == "ACTION_CLASSIFICATION_MISMATCH"


def test_v2_used_action_allows_only_a_new_separately_approved_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _path, first_digest = _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )
    first = mutation_evidence._consume_targeted_mutation_action(
        repository,
        "TASK-0001",
        subject,
        task,
        classification,
        policy_sha256,
    )
    _path, second_digest = _approve_v2_action(repository, "002")
    second = mutation_evidence._consume_targeted_mutation_action(
        repository,
        "TASK-0001",
        subject,
        task,
        classification,
        policy_sha256,
    )

    assert first.action_sha256 == first_digest
    assert second.action_sha256 == second_digest
    assert first_digest != second_digest


def test_v2_multiple_unused_current_actions_are_ambiguous(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _approve_v2_action(repository, "001")
    _approve_v2_action(repository, "002")
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )

    with pytest.raises(ContractError) as caught:
        mutation_evidence._consume_targeted_mutation_action(
            repository,
            "TASK-0001",
            subject,
            task,
            classification,
            policy_sha256,
        )
    assert caught.value.code == "ACTION_APPROVAL_AMBIGUOUS"


def test_v2_concurrent_consumers_get_one_action_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    _enable_v2_action_requirement(repository)
    _approve_v2_action(repository, "001")
    record = load_task_record(repository, "TASK-0001")
    subject = str(record.task["subject_commit"])
    verification_service._start_local_verification(repository, "TASK-0001", record, "verifier")
    task, classification, policy_sha256 = mutation_evidence._validate_bindings(
        repository, "TASK-0001", subject
    )
    barrier = Barrier(2)

    def consume() -> mutation_evidence.MutationActionUse | str:
        barrier.wait()
        try:
            return mutation_evidence._consume_targeted_mutation_action(
                repository,
                "TASK-0001",
                subject,
                task,
                classification,
                policy_sha256,
            )
        except ContractError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _index: consume(), range(2)))

    assert sum(isinstance(result, mutation_evidence.MutationActionUse) for result in results) == 1
    assert results.count("ACTION_APPROVAL_USED") == 1
    events = load_task_record(repository, "TASK-0001").events
    consumed = [
        event
        for event in events
        if event["event_type"] == "approval_recorded"
        and event["payload"].get("action_status") == "consumed"
    ]
    assert len(consumed) == 1
    assert len({event["sequence"] for event in events}) == len(events)


@pytest.mark.parametrize("route", ["AUTO", "ASK"])
def test_full_non_review_verification_reaches_merge_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    route: str,
) -> None:
    repository = _prepare(tmp_path, monkeypatch, route=route)

    def unexpected_mutation(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("V1 must not collect or consume targeted mutation evidence")

    monkeypatch.setattr(verification_service, "_v2_targeted_mutation_artifact", unexpected_mutation)

    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "APPROVED_FOR_MERGE"
    assert [event["event_type"] for event in record.events[-3:]] == [
        "verification_started",
        "verification_passed",
        "merge_approved_automatically",
    ]
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    assert evidence["conclusion"] == "passed"
    assert "APPROVED_FOR_MERGE passed" in capsys.readouterr().out


def test_review_verification_waits_for_final_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch, route="REVIEW")

    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0

    assert (
        load_task_record(repository, "TASK-0001").task["current_state"]
        == "WAITING_FOR_FINAL_REVIEW"
    )


@pytest.mark.parametrize(
    ("route", "expected_state"),
    [("AUTO", "APPROVED_FOR_MERGE"), ("REVIEW", "WAITING_FOR_FINAL_REVIEW")],
)
def test_verified_state_can_be_explicitly_reverified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    expected_state: str,
) -> None:
    repository = _prepare(tmp_path, monkeypatch, route=route)
    arguments = ["verify", "TASK-0001", "--actor", "verifier"]
    assert main(arguments) == 0

    assert main(arguments) == 0

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == expected_state
    assert [event["event_type"] for event in record.events[-3:]] == [
        "verification_restarted",
        "verification_passed",
        "final_review_required" if route == "REVIEW" else "merge_approved_automatically",
    ]


def test_required_failure_runs_and_enters_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan(failed=True))

    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0

    assert load_task_record(repository, "TASK-0001").task["current_state"] == "FAILED"
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    assert evidence["conclusion"] == "failed"


def test_targeted_check_is_provisional_and_returns_to_implementing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)

    assert (
        main(
            [
                "verify",
                "TASK-0001",
                "--actor",
                "verifier",
                "--check",
                "smoke",
            ]
        )
        == 0
    )

    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "IMPLEMENTING"
    assert [event["event_type"] for event in record.events[-2:]] == [
        "verification_started",
        "verification_checked",
    ]
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    assert evidence["conclusion"] == "provisional"


def test_final_verification_keeps_classification_fresh_after_audited_subject_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    (repository / "src").mkdir()
    (repository / "src" / "module.py").write_text("implemented\n", encoding="utf-8")
    run_git(repository, "add", "src/module.py")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "implementation",
    )

    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    assert main(["status", "TASK-0001", "--format", "json"]) == 0

    record = load_task_record(repository, "TASK-0001")
    assert record.task["subject_commit"] == run_git(repository, "rev-parse", "HEAD")
    assert any(event["event_type"] == "subject_commit_synchronized" for event in record.events)
    summary = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert summary["classification"] == "fresh"
    assert summary["evidence"] == "passed"


def test_stale_policy_rejects_before_process_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    classification["policy_sha256"] = "0" * 64
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"), classification
    )

    def unexpected(*_args, **_kwargs):
        raise AssertionError("runner must not start")

    monkeypatch.setattr(verification_service, "run_execution", unexpected)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 1
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "IMPLEMENTING"


@pytest.mark.parametrize(
    ("actor", "expected_code"),
    [(" ", "VERIFIER_ACTOR_REQUIRED"), (" implementer ", "VERIFIER_ACTOR_NOT_INDEPENDENT")],
)
def test_v2_actor_rejections_happen_before_plan_or_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    actor: str,
    expected_code: str,
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)

    def unexpected(*_args, **_kwargs):
        raise AssertionError("V2 rejection must happen before plan parsing or runner start")

    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "_start_local_verification", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(repository, "TASK-0001", actor=actor)

    assert caught.value.code == expected_code
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "IMPLEMENTING"


def test_v2_rejects_a_blank_current_implementer_before_plan_or_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    events_path = resolve_task_path(repository, "TASK-0001", "events.jsonl")
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events[-1]["actor"] = " "
    events_path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8"
    )

    def unexpected(*_args, **_kwargs):
        raise AssertionError("V2 actor rejection must happen before plan parsing or runner start")

    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "_start_local_verification", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(repository, "TASK-0001", actor="verifier")

    assert caught.value.code == "VERIFIER_IMPLEMENTER_MISSING"


@pytest.mark.parametrize(
    ("mutation_outcome", "expected_conclusion", "expected_reason"),
    [
        ("killed", "passed", None),
        ("survived", "failed", "MUTATION_EVIDENCE_NOT_KILLED"),
        ("unverified", "failed", "MUTATION_EVIDENCE_NOT_KILLED"),
        (None, "failed", "ACTION_APPROVAL_REQUIRED"),
    ],
)
def test_v2_live_run_consumes_current_mutation_or_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation_outcome: str | None,
    expected_conclusion: str,
    expected_reason: str | None,
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    levels: list[str] = []
    loader_calls: list[str] = []
    base_plan = _plan()

    def v2_plan(bundle, context: VerificationContext, *, level: str) -> VerificationPlan:
        levels.append(level)
        prefix = base_plan(bundle, context, level=level)
        extras = (
            VerificationCheck(
                "acceptance",
                "V2",
                (sys.executable, "-c", "print('acceptance')"),
                {},
                context.repository_root.resolve(),
                10,
                True,
                "pytest",
            ),
            VerificationCheck(
                "integration",
                "V2",
                (sys.executable, "-c", "print('integration')"),
                {},
                context.repository_root.resolve(),
                10,
                True,
                "pytest",
            ),
            VerificationCheck(
                "targeted_mutation",
                "V2",
                (sys.executable, "-m", "aiflow", "--help"),
                {},
                context.repository_root.resolve(),
                10,
                True,
                "exit_zero",
            ),
            VerificationCheck(
                "independent_verifier",
                "V2",
                (sys.executable, "-m", "aiflow", "--help"),
                {},
                context.repository_root.resolve(),
                10,
                True,
                "exit_zero",
            ),
        )
        executable_extras = tuple(
            VerificationExecution(
                f"EXEC-V2-{index:03d}",
                check.argv,
                check.environment,
                check.cwd,
                check.timeout_seconds,
                (check.check_id,),
            )
            for index, check in enumerate(extras[:2], start=1)
        )
        return VerificationPlan(
            level,
            prefix.run_dir,
            (*prefix.checks, *extras),
            (*prefix.executions, *executable_extras),
            (),
            (),
            prefix.comparison_subject,
        )

    monkeypatch.setattr(verification_service, "parse_verification_plan", v2_plan)
    monkeypatch.setattr(
        verification_service,
        "latest_review_assessment",
        lambda *_args, **_kwargs: ReviewAssessment(
            {"context_sha256": "d" * 64}, {"review_id": "REV-0001"}
        ),
    )
    if mutation_outcome is not None:
        artifact = _mutation_artifact(mutation_outcome)

        def load_artifact(_root: Path, _task_id: str, evidence_ref: str) -> dict[str, object]:
            loader_calls.append(evidence_ref)
            return artifact

        monkeypatch.setattr(
            verification_service,
            "record_targeted_mutation_evidence",
            lambda *_args: mutation_evidence.MutationEvidenceArtifact(
                "MUTRUN-20260825T120000Z-0000000000000000",
                str(artifact["evidence_ref"]),
                str(artifact["mutation_evidence_sha256"]),
                (),
            ),
        )
        monkeypatch.setattr(
            mutation_evidence,
            "load_targeted_mutation_evidence",
            load_artifact,
        )

    result = verification_service.verify_task(repository, "TASK-0001", actor="verifier")

    assert levels == ["V2"]
    assert len(loader_calls) == (1 if mutation_outcome is not None else 0)
    assert result.conclusion == expected_conclusion
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    assert evidence["schema_version"] == "2.0"
    assert evidence["phase"] == "pre_implementation_review"
    assert evidence["verification_level"] == "V2"
    assert len(str(evidence["verifier_context_sha256"])) == 64
    checks = {str(check["check_id"]): check for check in evidence["checks"]}
    for check_id in ("acceptance", "integration"):
        assert checks[check_id]["status"] == "passed"
        assert checks[check_id]["required"] is True
        assert checks[check_id]["exit_code"] == 0
        assert checks[check_id]["timed_out"] is False
        assert checks[check_id]["stdout_log_ref"]
        assert checks[check_id]["stderr_log_ref"]
        assert str(checks[check_id]["tool_version"]).endswith(":available")
    assert checks["targeted_mutation"]["status"] == (
        "passed" if mutation_outcome == "killed" else "failed"
    )
    assert checks["targeted_mutation"]["reason_code"] == expected_reason
    assert checks["independent_verifier"]["status"] == "passed"
    assert checks["independent_verifier"]["required"] is True


@pytest.mark.parametrize("selected_check", ["acceptance", "integration"])
def test_v2_selected_real_check_fails_when_mutation_evidence_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected_check: str
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    base_plan = _plan()

    def v2_plan(bundle, context: VerificationContext, *, level: str) -> VerificationPlan:
        prefix = base_plan(bundle, context, level=level)
        extras = tuple(
            VerificationCheck(
                check_id,
                "V2",
                (sys.executable, "-c", f"print('{check_id}')"),
                {},
                context.repository_root.resolve(),
                10,
                True,
                "pytest" if check_id != "targeted_mutation" else "exit_zero",
            )
            for check_id in (
                "acceptance",
                "integration",
                "targeted_mutation",
                "independent_verifier",
            )
        )
        executions = tuple(
            VerificationExecution(
                f"EXEC-V2-{index:03d}",
                check.argv,
                check.environment,
                check.cwd,
                check.timeout_seconds,
                (check.check_id,),
            )
            for index, check in enumerate(extras[:2], start=1)
        )
        return VerificationPlan(
            level,
            prefix.run_dir,
            (*prefix.checks, *extras),
            (*prefix.executions, *executions),
            (),
            (),
            prefix.comparison_subject,
        )

    monkeypatch.setattr(verification_service, "parse_verification_plan", v2_plan)
    monkeypatch.setattr(
        verification_service,
        "latest_review_assessment",
        lambda *_args, **_kwargs: ReviewAssessment(
            {"context_sha256": "d" * 64}, {"review_id": "REV-0001"}
        ),
    )

    result = verification_service.verify_task(
        repository, "TASK-0001", actor="verifier", check_ids=(selected_check,)
    )

    assert result.conclusion == "failed"
    assert result.state == "FAILED"
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    checks = {str(check["check_id"]): check for check in evidence["checks"]}
    assert checks[selected_check]["status"] == "passed"
    other = "integration" if selected_check == "acceptance" else "acceptance"
    assert checks[other]["status"] == "unverified"
    assert checks["targeted_mutation"]["status"] == "failed"
    assert checks["targeted_mutation"]["reason_code"] == "MUTATION_EVIDENCE_MISSING"
    assert evidence["targeted_mutation"] == {
        "evidence_ref": (
            ".ai/tasks/TASK-0001/logs/MUTRUN-19700101T000000Z-0000000000000000/"
            "targeted-mutation/evidence.json"
        ),
        "mutation_evidence_sha256": "0" * 64,
        "manifest_ref": ".ai/mutations/phase-02-critical-manifest.json",
        "results": [
            {
                "mutation_id": f"MUT-V2-{index:03d}",
                "outcome": "unverified",
                "log_ref": None,
            }
            for index in range(1, 6)
        ],
    }


def test_v2_selected_failure_remains_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    base_plan = _plan()

    def v2_plan(bundle, context: VerificationContext, *, level: str) -> VerificationPlan:
        prefix = base_plan(bundle, context, level=level)
        acceptance = VerificationCheck(
            "acceptance",
            "V2",
            (sys.executable, "-c", "import sys; sys.exit(1)"),
            {},
            context.repository_root.resolve(),
            10,
            True,
            "pytest",
        )
        integration = VerificationCheck(
            "integration",
            "V2",
            (sys.executable, "-c", "print('integration')"),
            {},
            context.repository_root.resolve(),
            10,
            True,
            "pytest",
        )
        mutation = VerificationCheck(
            "targeted_mutation",
            "V2",
            (sys.executable, "-m", "aiflow", "--help"),
            {},
            context.repository_root.resolve(),
            10,
            True,
            "exit_zero",
        )
        role = VerificationCheck(
            "independent_verifier",
            "V2",
            (sys.executable, "-m", "aiflow", "--help"),
            {},
            context.repository_root.resolve(),
            10,
            True,
            "exit_zero",
        )
        return VerificationPlan(
            level,
            prefix.run_dir,
            (*prefix.checks, acceptance, integration, mutation, role),
            (
                *prefix.executions,
                VerificationExecution(
                    "EXEC-V2-001", acceptance.argv, {}, acceptance.cwd, 10, ("acceptance",)
                ),
            ),
            (),
            (),
            prefix.comparison_subject,
        )

    monkeypatch.setattr(verification_service, "parse_verification_plan", v2_plan)
    monkeypatch.setattr(
        verification_service,
        "latest_review_assessment",
        lambda *_args, **_kwargs: ReviewAssessment(
            {"context_sha256": "d" * 64}, {"review_id": "REV-0001"}
        ),
    )

    result = verification_service.verify_task(
        repository, "TASK-0001", actor="verifier", check_ids=("acceptance",)
    )

    assert result.conclusion == "failed"
    assert result.state == "FAILED"
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    checks = {str(check["check_id"]): check for check in evidence["checks"]}
    assert checks["acceptance"]["status"] == "failed"
    assert evidence["conclusion"] == "failed"


def test_v2_finalize_never_starts_a_runner_and_conflicting_check_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)

    def unexpected(*_args, **_kwargs):
        raise AssertionError("finalize must not parse or execute a verification plan")

    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "_start_local_verification", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)

    with pytest.raises(ContractError):
        verification_service.verify_task(
            repository, "TASK-0001", actor="verifier", finalize=True, check_ids=("smoke",)
        )
    with pytest.raises(ContractError):
        verification_service.verify_task(repository, "TASK-0001", actor="verifier", finalize=True)


def test_finalize_rejects_non_v2_task_without_starting_a_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)

    def unexpected(*_args, **_kwargs):
        raise AssertionError("finalize must not parse or execute a verification plan")

    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(repository, "TASK-0001", actor="verifier", finalize=True)

    assert caught.value.code == "VERIFY_FINALIZE_LEVEL_INVALID"


def test_legacy_verify_still_requires_a_nonempty_actor_before_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)

    def unexpected(*_args, **_kwargs):
        raise AssertionError("actor validation must happen before plan parsing or runner start")

    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(repository, "TASK-0001", actor=" ")

    assert caught.value.code == "VERIFY_ACTOR_REQUIRED"


def test_verify_finalize_cli_forwards_flag_without_starting_a_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    def finalize_only(*_args: object, **kwargs: object) -> VerifyResult:
        received.update(kwargs)
        return VerifyResult("TASK-0001", "failed", "FAILED", Path("evidence.json"), ())

    monkeypatch.setattr(cli, "verify_task", finalize_only)

    assert cli.main(["verify", "TASK-0001", "--actor", "verifier", "--finalize"]) == 0
    assert received["finalize"] is True


def test_verify_finalize_cli_rejects_a_check_selection() -> None:
    with pytest.raises(SystemExit) as caught:
        build_parser().parse_args(
            ["verify", "TASK-0001", "--actor", "verifier", "--finalize", "--check", "smoke"]
        )

    assert caught.value.code == 2


def test_evidence_write_failure_enters_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)

    def fail_save(*_args, **_kwargs):
        raise StorageError("write failed", code="STORAGE_WRITE_FAILED")

    monkeypatch.setattr(verification_service, "save_evidence", fail_save)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 1
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "FAILED"
    assert record.events[-1]["payload"]["reason_code"] == "EVIDENCE_WRITE_FAILED"


def test_ci_verification_writes_only_external_run_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    events_path = resolve_task_path(repository, "TASK-0001", "events.jsonl")
    evidence_path = resolve_task_path(repository, "TASK-0001", "evidence.json")
    before = {path: path.read_bytes() for path in (task_path, events_path, evidence_path)}
    ci_run_dir = tmp_path / "ci-run"
    ci_run_dir.mkdir()
    output = ci_run_dir / "ci-evidence.json"

    def unexpected_recovery(*_args, **_kwargs):
        raise AssertionError("CI must not use the recovering task loader")

    monkeypatch.setattr(verification_service, "load_task_record", unexpected_recovery)

    assert (
        main(
            [
                "verify",
                "TASK-0001",
                "--ci",
                "--ci-run-dir",
                str(ci_run_dir),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    assert before == {path: path.read_bytes() for path in before}
    ci_evidence = json.loads(output.read_text(encoding="utf-8"))
    assert ci_evidence["mode"] == "ci"
    assert ci_evidence["conclusion"] == "passed"
    assert ci_evidence["attestation_governance_only"] is True


@pytest.mark.parametrize(
    ("mutation_reason", "actor"),
    [
        (None, None),
        (None, "verifier"),
        ("MUTATION_EVIDENCE_INVALID", None),
        ("MUTATION_EVIDENCE_PROJECTION_INVALID", None),
        ("MUTATION_EVIDENCE_NOT_KILLED", None),
    ],
)
def test_v2_ci_replays_final_source_without_mutation_collection_or_task_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation_reason: str | None,
    actor: str | None,
) -> None:
    """The V2 CI seam consumes only the finalized source projection."""
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)
    task_directory = resolve_task_path(repository, "TASK-0001")
    before = {
        path.relative_to(task_directory): path.read_bytes()
        for path in task_directory.rglob("*")
        if path.is_file()
    }
    source = {
        "schema_version": "2.0",
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
        "targeted_mutation": _mutation_artifact(),
    }
    design = ReviewAssessment({"context_sha256": "d" * 64}, {"review_id": "REV-0001"})
    implementation = ReviewAssessment({"context_sha256": "i" * 64}, {"review_id": "REV-0002"})
    facts = mutation_evidence.TargetedMutationFacts(
        mutation_reason is None,
        mutation_reason,
        str(source["targeted_mutation"]["evidence_ref"]),
        str(source["targeted_mutation"]["mutation_evidence_sha256"]),
        str(source["targeted_mutation"]["manifest_ref"]),
        tuple(source["targeted_mutation"]["results"]),
    )
    replayed: list[object] = []

    def v2_plan(_bundle: object, context: VerificationContext, *, level: str) -> VerificationPlan:
        prefix = _plan()(_bundle, context, level=level)
        checks = tuple(
            VerificationCheck(
                check_id,
                level,
                (sys.executable, "-c", "pass"),
                {},
                context.repository_root,
                10,
                True,
                "exit_zero",
            )
            for check_id in (
                "acceptance",
                "integration",
                "targeted_mutation",
                "independent_verifier",
            )
        )
        executions = tuple(
            VerificationExecution(
                f"V2-{index}", check.argv, check.environment, check.cwd, 10, (check.check_id,)
            )
            for index, check in enumerate(checks[:2], start=1)
        )
        return VerificationPlan(
            level,
            prefix.run_dir,
            (*prefix.checks, *checks),
            (*prefix.executions, *executions),
            (),
            (),
            prefix.comparison_subject,
        )

    def replay(
        _root: Path, _task_id: str, evidence: object, **_kwargs: object
    ) -> mutation_evidence.TargetedMutationFacts:
        replayed.append(evidence)
        return facts

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("V2 CI must not collect, consume an action, or run mutations")

    if mutation_reason is None:
        monkeypatch.setattr(verification_service, "parse_verification_plan", v2_plan)
    else:
        monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    original_read = verification_service.read_task_json

    def read_source(*args: object, **kwargs: object) -> object:
        if len(args) >= 3 and args[2] == "evidence.json":
            return source
        return original_read(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(verification_service, "read_task_json", read_source)
    monkeypatch.setattr(verification_service, "validate_v2_snapshot", lambda *_args: None)
    monkeypatch.setattr(
        verification_service, "evaluate_freshness", lambda *_args: SimpleNamespace(status="fresh")
    )
    monkeypatch.setattr(verification_service, "load_verifier_context", lambda *_args: object())
    monkeypatch.setattr(verification_service, "build_verifier_context", lambda *_args: object())
    monkeypatch.setattr(
        verification_service, "validate_verifier_context_current", lambda *_args: None
    )
    monkeypatch.setattr(
        verification_service,
        "latest_review_assessment",
        lambda *_args, **kwargs: implementation if _args[2] == "implementation" else design,
    )
    monkeypatch.setattr(verification_service, "consume_targeted_mutation_evidence", replay)
    monkeypatch.setattr(verification_service, "record_targeted_mutation_evidence", unexpected)
    monkeypatch.setattr(mutation_evidence, "_consume_targeted_mutation_action", unexpected)
    monkeypatch.setattr(mutation_evidence, "run_targeted_mutations", unexpected)
    run_directory = tmp_path / "ci-v2"
    run_directory.mkdir()
    output = run_directory / "evidence.json"

    if mutation_reason is not None:
        with pytest.raises(ContractError) as caught:
            verification_service.verify_task(
                repository,
                "TASK-0001",
                actor=actor,
                ci=True,
                ci_run_dir=run_directory,
                output=output,
            )
        assert caught.value.code == mutation_reason
        assert replayed == [source]
        assert before == {
            path.relative_to(task_directory): path.read_bytes()
            for path in task_directory.rglob("*")
            if path.is_file()
        }
        return

    result = verification_service.verify_task(
        repository,
        "TASK-0001",
        actor=actor,
        ci=True,
        ci_run_dir=run_directory,
        output=output,
    )

    assert result.conclusion == "passed"
    assert replayed == [source]
    assert before == {
        path.relative_to(task_directory): path.read_bytes()
        for path in task_directory.rglob("*")
        if path.is_file()
    }
    evidence = json.loads(output.read_text(encoding="utf-8"))
    checks = {check["check_id"]: check for check in evidence["checks"]}
    assert checks["targeted_mutation"]["status"] == "passed"
    assert evidence["verifier_actor"] == "verifier"


def test_v2_ci_rejects_missing_source_before_plan_or_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)
    resolve_task_path(repository, "TASK-0001", "evidence.json").unlink()

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("missing V2 CI source must stop before plan or runner")

    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)
    run_directory = tmp_path / "ci-missing-source"
    run_directory.mkdir()

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(
            repository,
            "TASK-0001",
            ci=True,
            ci_run_dir=run_directory,
            output=run_directory / "evidence.json",
        )

    assert caught.value.code == "VERIFY_FINALIZE_EVIDENCE_INVALID"


@pytest.mark.parametrize(
    ("check_ids", "provisional"),
    [("smoke", False), ("", True)],
)
def test_v2_ci_rejects_partial_invocation_before_source_plan_or_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    check_ids: str,
    provisional: bool,
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("partial V2 CI must stop before source, plan, or runner")

    monkeypatch.setattr(verification_service, "_load_v2_ci_source_evidence", unexpected)
    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)
    run_directory = tmp_path / "ci-partial"
    run_directory.mkdir()

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(
            repository,
            "TASK-0001",
            check_ids=(check_ids,) if check_ids else (),
            provisional=provisional,
            ci=True,
            ci_run_dir=run_directory,
            output=run_directory / "evidence.json",
        )

    assert caught.value.code == "VERIFY_CI_V2_PARTIAL_INVALID"


@pytest.mark.parametrize(
    ("field", "value"),
    [("phase", "pre_implementation_review"), ("mode", "ci"), ("conclusion", "failed")],
)
def test_v2_ci_rejects_nonfinal_source_before_plan_or_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)
    source = {
        "schema_version": "2.0",
        "verification_level": "V2",
        "mode": "local",
        "phase": "final",
        "conclusion": "passed",
    }
    source[field] = value
    original_read = verification_service.read_task_json

    def read_source(*args: object, **kwargs: object) -> object:
        if len(args) >= 3 and args[2] == "evidence.json":
            return source
        return original_read(*args, **kwargs)  # type: ignore[arg-type]

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("invalid V2 CI source must stop before plan or runner")

    monkeypatch.setattr(verification_service, "read_task_json", read_source)
    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)
    run_directory = tmp_path / "ci-invalid-source"
    run_directory.mkdir()

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(
            repository,
            "TASK-0001",
            ci=True,
            ci_run_dir=run_directory,
            output=run_directory / "evidence.json",
        )

    assert caught.value.code == "VERIFY_FINALIZE_EVIDENCE_INVALID"


def test_v2_ci_rejects_actor_mismatch_before_consumer_plan_or_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)
    task_directory = resolve_task_path(repository, "TASK-0001")
    before = {path: path.read_bytes() for path in task_directory.rglob("*") if path.is_file()}
    source = {
        "schema_version": "2.0",
        "verification_level": "V2",
        "mode": "local",
        "phase": "final",
        "conclusion": "passed",
        "verifier_actor": "verifier",
    }
    original_read = verification_service.read_task_json

    def read_source(*args: object, **kwargs: object) -> object:
        if len(args) >= 3 and args[2] == "evidence.json":
            return source
        return original_read(*args, **kwargs)  # type: ignore[arg-type]

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("actor mismatch must stop before mutation replay or runner")

    monkeypatch.setattr(verification_service, "read_task_json", read_source)
    monkeypatch.setattr(verification_service, "validate_v2_snapshot", lambda *_args: None)
    monkeypatch.setattr(
        verification_service, "evaluate_freshness", lambda *_args: SimpleNamespace(status="fresh")
    )
    monkeypatch.setattr(verification_service, "consume_targeted_mutation_evidence", unexpected)
    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)
    run_directory = tmp_path / "ci-actor"
    run_directory.mkdir()

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(
            repository,
            "TASK-0001",
            actor="other-verifier",
            ci=True,
            ci_run_dir=run_directory,
            output=run_directory / "evidence.json",
        )

    assert caught.value.code == "VERIFY_FINALIZE_ACTOR_STALE"
    assert before == {
        path: path.read_bytes() for path in task_directory.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("failure", ["stale", "snapshot"])
def test_v2_ci_rejects_stale_or_tampered_source_before_plan_or_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)
    source = {
        "schema_version": "2.0",
        "verification_level": "V2",
        "mode": "local",
        "phase": "final",
        "conclusion": "passed",
    }
    original_read = verification_service.read_task_json

    def read_source(*args: object, **kwargs: object) -> object:
        if len(args) >= 3 and args[2] == "evidence.json":
            return source
        return original_read(*args, **kwargs)  # type: ignore[arg-type]

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("stale or tampered V2 source must stop before plan or runner")

    monkeypatch.setattr(verification_service, "read_task_json", read_source)
    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)
    if failure == "snapshot":

        def stale_snapshot(*_args: object) -> None:
            raise ContractError("snapshot is stale", code="EVIDENCE_SNAPSHOT_STALE")

        monkeypatch.setattr(verification_service, "validate_v2_snapshot", stale_snapshot)
        expected = "EVIDENCE_SNAPSHOT_STALE"
    else:
        monkeypatch.setattr(verification_service, "validate_v2_snapshot", lambda *_args: None)
        monkeypatch.setattr(
            verification_service,
            "evaluate_freshness",
            lambda kind, *_args: SimpleNamespace(status="stale" if kind == "evidence" else "fresh"),
        )
        expected = "VERIFY_FINALIZE_EVIDENCE_STALE"
    run_directory = tmp_path / f"ci-{failure}"
    run_directory.mkdir()

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(
            repository,
            "TASK-0001",
            ci=True,
            ci_run_dir=run_directory,
            output=run_directory / "evidence.json",
        )

    assert caught.value.code == expected


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("context", "VERIFIER_CONTEXT_STALE"),
        ("design_review", "VERIFY_FINALIZE_REVIEW_STALE"),
        ("implementation_review", "VERIFY_FINALIZE_REVIEW_STALE"),
    ],
)
def test_v2_ci_rejects_stale_context_or_reviews_before_plan_or_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected: str,
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)
    source = {
        "schema_version": "2.0",
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
    }
    if failure == "design_review":
        source["review_refs"]["design"]["review_id"] = "REV-0003"
    if failure == "implementation_review":
        source["review_refs"]["implementation"]["review_id"] = "REV-0003"
    original_read = verification_service.read_task_json

    def read_source(*args: object, **kwargs: object) -> object:
        if len(args) >= 3 and args[2] == "evidence.json":
            return source
        return original_read(*args, **kwargs)  # type: ignore[arg-type]

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("stale V2 source fact must stop before consumer, plan, or runner")

    design = ReviewAssessment({"context_sha256": "d" * 64}, {"review_id": "REV-0001"})
    implementation = ReviewAssessment({"context_sha256": "i" * 64}, {"review_id": "REV-0002"})
    monkeypatch.setattr(verification_service, "read_task_json", read_source)
    monkeypatch.setattr(verification_service, "validate_v2_snapshot", lambda *_args: None)
    monkeypatch.setattr(
        verification_service, "evaluate_freshness", lambda *_args: SimpleNamespace(status="fresh")
    )
    monkeypatch.setattr(verification_service, "load_verifier_context", lambda *_args: object())
    monkeypatch.setattr(verification_service, "build_verifier_context", lambda *_args: object())
    if failure == "context":

        def stale_context(*_args: object) -> None:
            raise ContractError("context is stale", code="VERIFIER_CONTEXT_STALE")

        monkeypatch.setattr(
            verification_service, "validate_verifier_context_current", stale_context
        )
    else:
        monkeypatch.setattr(
            verification_service, "validate_verifier_context_current", lambda *_args: None
        )
    monkeypatch.setattr(
        verification_service,
        "latest_review_assessment",
        lambda *_args, **_kwargs: implementation if _args[2] == "implementation" else design,
    )
    monkeypatch.setattr(verification_service, "consume_targeted_mutation_evidence", unexpected)
    monkeypatch.setattr(verification_service, "parse_verification_plan", unexpected)
    monkeypatch.setattr(verification_service, "run_execution", unexpected)
    run_directory = tmp_path / f"ci-{failure}"
    run_directory.mkdir()

    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(
            repository,
            "TASK-0001",
            ci=True,
            ci_run_dir=run_directory,
            output=run_directory / "evidence.json",
        )

    assert caught.value.code == expected


def test_v2_ci_real_consumer_rejects_tampered_log_before_plan_or_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the CI seam on the public loader path for an actual artifact tamper."""
    repository = _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _enable_v2(repository)
    record = load_task_record(repository, "TASK-0001")
    manifest = load_mutation_manifest(Path(__file__).resolve().parents[2])
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
            mutation_runner.MutationProbe(item.mutation_id, 0, 1, False, 1, None)
            for item in manifest.mutations
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
    artifact_path = repository / artifact.evidence_ref
    artifact_value = json.loads(artifact_path.read_text(encoding="utf-8"))
    first_log = repository / str(artifact_value["results"][0]["log_ref"])
    first_log.write_text("{}", encoding="utf-8")
    task_directory = resolve_task_path(repository, "TASK-0001")
    before = {
        path.relative_to(task_directory): path.read_bytes()
        for path in task_directory.rglob("*")
        if path.is_file()
    }
    source = {
        "schema_version": "2.0",
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
        lambda *args, **kwargs: (
            source
            if len(args) >= 3 and args[2] == "evidence.json"
            else original_read(*args, **kwargs)
        ),
    )
    monkeypatch.setattr(verification_service, "validate_v2_snapshot", lambda *_args: None)
    monkeypatch.setattr(
        verification_service, "evaluate_freshness", lambda *_args: SimpleNamespace(status="fresh")
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
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not parse")),
    )
    run_directory = tmp_path / "ci-real-tamper"
    run_directory.mkdir()
    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(
            repository,
            "TASK-0001",
            ci=True,
            ci_run_dir=run_directory,
            output=run_directory / "evidence.json",
        )
    assert caught.value.code == "MUTATION_EVIDENCE_INVALID"
    assert before == {
        path.relative_to(task_directory): path.read_bytes()
        for path in task_directory.rglob("*")
        if path.is_file()
    }


def test_ci_requires_temp_run_dir_and_contained_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare(tmp_path, monkeypatch)
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    assert main(["verify", "TASK-0001", "--ci"]) == 1
    outside = tmp_path / "outside.json"
    run_dir = tmp_path / "ci-run"
    run_dir.mkdir()
    assert (
        main(
            [
                "verify",
                "TASK-0001",
                "--ci",
                "--ci-run-dir",
                str(run_dir),
                "--output",
                str(outside),
            ]
        )
        == 1
    )


def test_verify_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["verify", "--help"])
    assert caught.value.code == 0
    output = capsys.readouterr().out
    assert "--ci-run-dir" in output and "--check" in output
