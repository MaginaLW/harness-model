"""Integration tests for deterministic, read-only local and CI Gate decisions."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_approve_command import _record_review, review_package
from test_begin_close_commands import create_repository, make_ready, run_git, start
from test_governance_paths import _auto_unit
from test_verify_command import _plan

from aiflow import gate as gate_service
from aiflow import verification_service
from aiflow.cli import main
from aiflow.mutation_evidence import TargetedMutationFacts
from aiflow.storage import (
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record


def _prepare_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    review: bool = False,
    implementation_path: str | None = None,
) -> Path:
    repository = create_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    unit = _auto_unit("TASK-0001")
    if review:
        unit["impact"] = {"level": "medium"}
        characteristics = unit["change_characteristics"]
        assert isinstance(characteristics, dict)
        characteristics.update(
            {"mechanical": False, "behavior_changed": True, "code_modified": True}
        )
    task["decision_units"] = [unit]
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    route = "REVIEW" if review else "AUTO"
    make_ready(repository, route=route, valid_approval=review)
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    if not review:
        classification["effective_verification_level"] = "V0"
        classification["classifications"][0]["verification_level"] = "V0"
        atomic_write_json(
            resolve_task_path(repository, "TASK-0001", "classification.json"), classification
        )
    else:
        approvals = read_task_json(repository, "TASK-0001", "approvals.json")
        assert isinstance(approvals, list)
        approvals[0]["base_commit"] = task["base_commit"]
        atomic_write_json(resolve_task_path(repository, "TASK-0001", "approvals.json"), approvals)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    if implementation_path is not None:
        implementation = repository / implementation_path
        implementation.parent.mkdir(parents=True, exist_ok=True)
        implementation.write_text("implemented\n", encoding="utf-8")
        run_git(repository, "add", implementation_path)
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
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan())
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    return repository


def test_auto_gate_passes_repeatably_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    capsys.readouterr()
    paths = [
        resolve_task_path(repository, "TASK-0001", name)
        for name in ("task.yaml", "events.jsonl", "approvals.json", "evidence.json")
    ]
    before = {path: path.read_bytes() for path in paths}

    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    first = capsys.readouterr().out
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    second = capsys.readouterr().out

    assert first == second
    assert json.loads(first)["passed"] is True
    assert before == {path: path.read_bytes() for path in paths}


def test_gate_rejects_governance_tail_outside_current_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    capsys.readouterr()
    (repository / "tracked.txt").write_text("new tail\n", encoding="utf-8")
    run_git(repository, "add", "tracked.txt")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "outside tail",
    )

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert "GATE_SCOPE_CHANGED" in json.loads(capsys.readouterr().out)["reason_codes"]


def test_auto_gate_rejects_subject_change_outside_decision_unit_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_gate(
        tmp_path,
        monkeypatch,
        implementation_path="src/outside-decision-unit.py",
    )
    capsys.readouterr()

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert "GATE_SCOPE_CHANGED" in json.loads(capsys.readouterr().out)["reason_codes"]


def test_gate_rejects_non_ancestral_commit_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_gate(tmp_path, monkeypatch)
    capsys.readouterr()
    monkeypatch.setattr(gate_service, "commits_are_ancestral", lambda *args, **kwargs: False)

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert "GATE_REPOSITORY_CHANGED" in json.loads(capsys.readouterr().out)["reason_codes"]


def test_review_gate_requires_code_approval_and_then_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    capsys.readouterr()
    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    rejected = json.loads(capsys.readouterr().out)
    assert "GATE_CODE_APPROVAL_STALE" in rejected["reason_codes"]
    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    _record_review(
        repository,
        tmp_path,
        stage="implementation",
        review_id="REV-9001",
    )

    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "code",
                "--actor",
                "reviewer",
                "--reason",
                "current implementation approved",
            ]
        )
        == 0
    )
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["passed"] is True


def test_ci_gate_uses_external_attested_evidence_but_local_code_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_gate(tmp_path, monkeypatch)
    ci_run_dir = tmp_path / "gate-ci"
    ci_run_dir.mkdir()
    external = ci_run_dir / "evidence.json"
    assert (
        main(
            [
                "verify",
                "TASK-0001",
                "--ci",
                "--ci-run-dir",
                str(ci_run_dir),
                "--output",
                str(external),
            ]
        )
        == 0
    )

    assert (
        main(
            [
                "gate",
                "TASK-0001",
                "--evidence",
                str(external),
                "--format",
                "json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["passed"] is True


def test_v2_ci_evidence_uses_current_design_review_without_implementation_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CI's pre-review artifact must not be mistaken for a final local review."""
    evidence = {
        "schema_version": "2.0",
        "phase": "pre_implementation_review",
        "verifier_actor": "verifier",
        "verifier_context_sha256": "context",
        "verification_snapshot_sha256": "snapshot",
        "checks": [{"check_id": "required", "status": "passed"}],
        "targeted_mutation": {},
        "review_refs": {"design": {"review_id": "REV-1", "context_sha256": "design"}},
    }
    reviewed_stages: list[str] = []
    monkeypatch.setattr(gate_service, "validate_v2_snapshot", lambda _evidence: None)
    monkeypatch.setattr(gate_service, "current_implementer_actor", lambda _events: "implementer")
    monkeypatch.setattr(gate_service, "validate_verifier_actor", lambda *_args: None)
    monkeypatch.setattr(gate_service, "load_verifier_context", lambda *_args: object())
    monkeypatch.setattr(gate_service, "build_verifier_context", lambda *_args: object())
    monkeypatch.setattr(gate_service, "validate_verifier_context_current", lambda *_args: None)
    monkeypatch.setattr(
        gate_service,
        "consume_targeted_mutation_evidence",
        lambda *_args: TargetedMutationFacts(True, None, None, None, None, ()),
    )

    def current_review(*_args: object, **kwargs: object) -> SimpleNamespace:
        stage = str(_args[2])
        reviewed_stages.append(stage)
        return SimpleNamespace(record={"review_id": "REV-1", "context_sha256": "design"})

    monkeypatch.setattr(gate_service, "latest_review_assessment", current_review)

    facts = gate_service._v2_gate_facts(
        Path("."),
        "TASK-0001",
        evidence,
        events=(),
        policy_checks=[{"id": "required", "required": True}],
        decision_unit_ids=["DU-001"],
        review_stages=("design",),
    )

    assert facts["v2_reviews_current"] is True
    assert reviewed_stages == ["design"]


@pytest.mark.parametrize(
    ("tamper", "reason"),
    [
        (None, None),
        ("local_stale", "GATE_EVIDENCE_STALE"),
        ("local_missing", "GATE_EVIDENCE_STALE"),
        ("local_final", "GATE_V2_EVIDENCE_NOT_FINAL"),
        ("local_review", "GATE_V2_REVIEW_STALE"),
        ("code_approval", "GATE_CODE_APPROVAL_STALE"),
        ("ci_phase", "GATE_EVIDENCE_STALE"),
        ("ci_check", "GATE_V2_CHECKS_INCOMPLETE"),
        ("ci_snapshot", "GATE_V2_SNAPSHOT_STALE"),
        ("ci_verifier", "GATE_V2_VERIFIER_NOT_INDEPENDENT"),
        ("ci_context", "GATE_V2_CONTEXT_STALE"),
        ("ci_review", "GATE_V2_REVIEW_STALE"),
        ("ci_mutation", "GATE_V2_MUTATION_NOT_KILLED"),
        ("ci_attestation", "GATE_EVIDENCE_STALE"),
    ],
)
def test_v2_ci_gate_merges_local_final_and_external_pre_facts_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str | None,
    reason: str | None,
) -> None:
    """Exercise the real Gate merge path without duplicating the V2 handshake fixture."""
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    record = load_task_record(repository, "TASK-0001")
    task = {**record.task, "current_state": "APPROVED_FOR_MERGE"}
    gate_record = SimpleNamespace(task=task, events=record.events)
    local = {
        "mode": "local",
        "phase": "final",
        "conclusion": "passed",
        "decision_unit_ids": ["DU-001"],
    }
    external = {
        "mode": "ci",
        "phase": "pre_implementation_review",
        "conclusion": "passed",
        "decision_unit_ids": ["DU-001"],
    }
    local_v2 = {
        "v2_final_evidence": True,
        "v2_snapshot_current": True,
        "v2_verifier_independent": True,
        "v2_context_current": True,
        "v2_reviews_current": True,
        "v2_checks_current": True,
        "v2_mutation_killed": True,
    }
    ci_v2 = dict(local_v2)
    if tamper == "local_final":
        local_v2["v2_final_evidence"] = False
    elif tamper == "local_review":
        local_v2["v2_reviews_current"] = False
    elif tamper == "ci_snapshot":
        ci_v2["v2_snapshot_current"] = False
    elif tamper == "ci_check":
        ci_v2["v2_checks_current"] = False
    elif tamper == "ci_verifier":
        ci_v2["v2_verifier_independent"] = False
    elif tamper == "ci_context":
        ci_v2["v2_context_current"] = False
    elif tamper == "ci_review":
        ci_v2["v2_reviews_current"] = False
    elif tamper == "ci_mutation":
        ci_v2["v2_mutation_killed"] = False
    elif tamper == "ci_phase":
        external["phase"] = "final"

    def freshness(_kind: str, artifact: object, _current: object) -> SimpleNamespace:
        stale = (tamper == "local_stale" and artifact is local) or (
            tamper == "ci_attestation" and artifact is external
        )
        return SimpleNamespace(status="stale" if stale else "fresh")

    route = SimpleNamespace(
        effective_route="REVIEW",
        unit_decisions=(SimpleNamespace(decision_unit_id="DU-001", effective_route="REVIEW"),),
    )
    verification = SimpleNamespace(
        level="V2",
        unit_decisions=(SimpleNamespace(decision_unit_id="DU-001", level="V2"),),
    )
    classification = {
        "effective_route": "REVIEW",
        "effective_verification_level": "V2",
        "classifications": [
            {"decision_unit_id": "DU-001", "route": "REVIEW", "verification_level": "V2"}
        ],
    }
    approvals = (
        []
        if tamper == "code_approval"
        else [{"approval_type": "code", "decision_unit_id": "DU-001"}]
    )
    approvals.append({"approval_type": "spec", "decision_unit_id": "DU-001"})

    monkeypatch.setattr(gate_service, "read_task_record_strict", lambda *_args: gate_record)
    monkeypatch.setattr(gate_service, "read_task_json", lambda *_args, **_kwargs: classification)
    monkeypatch.setattr(
        gate_service,
        "_read_local_evidence",
        lambda *_args: None if tamper == "local_missing" else local,
    )
    monkeypatch.setattr(gate_service, "_read_external_evidence", lambda *_args: external)
    monkeypatch.setattr(gate_service, "_read_approvals", lambda *_args: tuple(approvals))
    monkeypatch.setattr(gate_service, "evaluate_freshness", freshness)
    monkeypatch.setattr(gate_service, "route_task", lambda *_args: route)
    monkeypatch.setattr(gate_service, "verification_for_task", lambda *_args: verification)
    monkeypatch.setattr(
        gate_service,
        "_v2_gate_facts",
        lambda *_args, **kwargs: local_v2 if kwargs.get("review_stages") != ("design",) else ci_v2,
    )

    decision = gate_service.evaluate_gate(
        repository, "TASK-0001", evidence_path=tmp_path / "ci.json"
    )

    assert decision.passed is (reason is None)
    if reason is not None:
        assert reason in decision.reason_codes


def test_action_approval_does_not_replace_review_code_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    task = load_task_record(repository, "TASK-0001").task
    action_path = tmp_path / "action.json"
    action_path.write_text(
        json.dumps(
            {
                "decision_unit_id": "DU-001",
                "action_type": "notify",
                "target": "issue-1",
                "parameter_summary": "one notification",
                "subject_commit": task["subject_commit"],
                "conditions": ["reviewed"],
                "expires_at": "2099-01-01T00:00:00Z",
                "single_use": True,
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "action",
                "--action-file",
                str(action_path),
                "--actor",
                "reviewer",
                "--reason",
                "notification only",
            ]
        )
        == 0
    )

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert (
        "GATE_CODE_APPROVAL_STALE"
        in json.loads(capsys.readouterr().out.splitlines()[-1])["reason_codes"]
    )


def test_gate_distinguishes_invalid_external_input_from_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_gate(tmp_path, monkeypatch)
    broken = tmp_path / "broken.json"
    broken.write_text("{broken", encoding="utf-8")
    assert main(["gate", "TASK-0001", "--evidence", str(broken)]) == 1


def test_gate_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["gate", "--help"])
    assert caught.value.code == 0
    output = capsys.readouterr().out
    assert "--evidence" in output and "--format" in output
