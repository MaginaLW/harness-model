"""Integration tests for read-only status output."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_answer_command import specification
from test_approve_command import _record_review, review_package
from test_begin_close_commands import create_repository as create_policy_repository
from test_begin_close_commands import start
from test_gate_command import _prepare_gate
from test_governance_paths import _auto_unit

from aiflow import approval as approval_service
from aiflow import gate as gate_service
from aiflow import status_service, verification_service
from aiflow.cli import main
from aiflow.evidence import prepare_v2_pre_evidence
from aiflow.mutation_evidence import TargetedMutationFacts
from aiflow.policy import load_policy_bundle
from aiflow.state import TRANSITIONS, create_record_event, create_transition_event
from aiflow.storage import (
    atomic_write_json,
    atomic_write_text,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record
from aiflow.verifier_service import build_verifier_context, save_verifier_context

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"

PATHS: dict[str, list[str]] = {
    "NEW": [],
    "WAITING_FOR_ASK": ["CLASSIFIED", "WAITING_FOR_ASK"],
    "READY_TO_IMPLEMENT": ["CLASSIFIED", "READY_TO_IMPLEMENT"],
    "IMPLEMENTING": ["CLASSIFIED", "READY_TO_IMPLEMENT", "IMPLEMENTING"],
    "FAILED": ["CLASSIFIED", "READY_TO_IMPLEMENT", "IMPLEMENTING", "VERIFYING", "FAILED"],
    "VERIFIED": ["CLASSIFIED", "READY_TO_IMPLEMENT", "IMPLEMENTING", "VERIFYING", "VERIFIED"],
    "APPROVED_FOR_MERGE": [
        "CLASSIFIED",
        "READY_TO_IMPLEMENT",
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "APPROVED_FOR_MERGE",
    ],
    "MERGED": [
        "CLASSIFIED",
        "READY_TO_IMPLEMENT",
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "APPROVED_FOR_MERGE",
        "MERGED",
    ],
}


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=True,
        encoding="utf-8",
        timeout=10,
    )
    return result.stdout.rstrip("\r\n")


def create_repository(path: Path) -> Path:
    path.mkdir()
    run_git(path, "init", "-b", "main")
    ai_root = path / ".ai"
    ai_root.mkdir()
    shutil.copytree(PROJECT_ROOT / ".ai" / "schemas", ai_root / "schemas")
    (ai_root / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    run_git(path, "add", ".ai", "tracked.txt")
    run_git(
        path,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "initial",
    )
    return path


def create_task(repository: Path, state: str) -> Path:
    head = run_git(repository, "rev-parse", "HEAD")
    task = json.loads(
        (PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "task.json").read_text(
            encoding="utf-8"
        )
    )
    task.update(
        {
            "task_id": "TASK-0001",
            "repository_id": REPOSITORY_ID,
            "branch": "main",
            "base_commit": head,
            "subject_commit": head,
            "worktree_dirty": False,
            "current_state": state,
            "repository_path_at_creation": repository.resolve().as_posix(),
        }
    )
    task["decision_units"][0]["task_id"] = "TASK-0001"
    event_task = {"task_id": "TASK-0001", "current_state": "NEW"}
    events: list[dict[str, Any]] = [
        create_record_event(
            event_task,
            event_type="task_created",
            actor="aiflow",
            payload={},
            sequence=1,
            occurred_at="2026-08-20T14:00:00Z",
        )
    ]
    current = "NEW"
    for target in PATHS[state]:
        rule = TRANSITIONS[(current, target)]
        event_task["current_state"] = current
        events.append(
            create_transition_event(
                event_task,
                target_state=target,
                event_type=rule.event_type,
                actor="tester",
                payload={},
                sequence=len(events) + 1,
                satisfied_preconditions=set(rule.preconditions),
                occurred_at="2026-08-20T14:00:00Z",
            )
        )
        current = target
    directory = repository / ".ai" / "tasks" / "TASK-0001"
    directory.mkdir(parents=True)
    atomic_write_yaml(directory / "task.yaml", task)
    atomic_write_text(
        directory / "events.jsonl",
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
    )
    atomic_write_json(directory / "approvals.json", [])
    return directory


@pytest.mark.parametrize("state", list(PATHS))
def test_json_status_for_main_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    state: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    create_task(repository, state)
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001", "--format", "json"]) == 0

    summary = json.loads(capsys.readouterr().out)
    assert summary["task_id"] == "TASK-0001"
    assert summary["current_state"] == state
    assert summary["merge_readiness"] == (
        "reverification_required" if state == "APPROVED_FOR_MERGE" else "not_applicable"
    )
    assert summary["route"] == "not_available"
    assert summary["verification_level"] == "not_available"
    assert isinstance(summary["next_events"], list)
    assert summary["observed_head"] == run_git(repository, "rev-parse", "HEAD")
    if state == "APPROVED_FOR_MERGE":
        assert summary["missing_conditions"] == ["reverification"]


@pytest.mark.parametrize(
    ("state", "route", "classification", "approvals", "evidence", "expected"),
    [
        (
            "APPROVED_FOR_MERGE",
            "REVIEW",
            "fresh",
            "current",
            "passed",
            "gate_required",
        ),
        (
            "APPROVED_FOR_MERGE",
            "AUTO",
            "fresh",
            "not_available",
            "passed",
            "gate_required",
        ),
        (
            "APPROVED_FOR_MERGE",
            "REVIEW",
            "fresh",
            "stale",
            "passed",
            "reverification_required",
        ),
        (
            "APPROVED_FOR_MERGE",
            "REVIEW",
            "fresh",
            "current",
            "stale",
            "reverification_required",
        ),
        (
            "WAITING_FOR_FINAL_REVIEW",
            "REVIEW",
            "fresh",
            "not_available",
            "passed",
            "not_applicable",
        ),
    ],
)
def test_merge_readiness_projection(
    state: str,
    route: str,
    classification: str,
    approvals: str,
    evidence: str,
    expected: str,
) -> None:
    assert (
        status_service._merge_readiness(
            state=state,
            route=route,
            classification=classification,
            approvals=approvals,
            evidence=evidence,
        )
        == expected
    )


def test_text_status_is_concise_and_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "READY_TO_IMPLEMENT")
    monkeypatch.chdir(repository)
    paths = [directory / "task.yaml", directory / "events.jsonl"]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

    assert main(["status", "TASK-0001"]) == 0

    output = capsys.readouterr().out
    assert "State: READY_TO_IMPLEMENT" in output
    assert "Merge readiness: not_applicable" in output
    assert "Next events: implementation_started" in output
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_status_reports_classification_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "WAITING_FOR_ASK")
    classification = json.loads(
        (
            PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "classification.json"
        ).read_text(encoding="utf-8")
    )
    atomic_write_json(directory / "classification.json", classification)
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["route"] == "REVIEW"
    assert summary["verification_level"] == "V1"


def test_status_does_not_treat_unrequested_action_approval_as_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "READY_TO_IMPLEMENT")
    approval = json.loads(
        (PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "approval.json").read_text(
            encoding="utf-8"
        )
    )
    approval.update(
        {
            "approval_type": "action",
            "action_sha256": "c" * 64,
            "expires_at": "2099-01-01T00:00:00Z",
            "single_use": True,
        }
    )
    atomic_write_json(directory / "approvals.json", [approval])
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["approvals"] == "not_applicable"


def _approve_current_review_implementation(
    repository: Path,
    tmp_path: Path,
) -> None:
    """Finish the real REVIEW lifecycle with a current implementation approval."""
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
                "implementation is current",
            ]
        )
        == 0
    )


def test_status_uses_current_review_approvals_not_stale_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A replacement approval must restore status just as it restores Gate eligibility."""
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    capsys.readouterr()
    _approve_current_review_implementation(repository, tmp_path)
    capsys.readouterr()

    approvals = read_task_json(repository, "TASK-0001", "approvals.json")
    assert isinstance(approvals, list)
    current_spec = next(item for item in approvals if item["approval_type"] == "spec")
    current_code = next(item for item in approvals if item["approval_type"] == "code")
    stale_spec = {**current_spec, "spec_sha256": "0" * 64}
    stale_code = {**current_code, "evidence_sha256": "0" * 64}
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "approvals.json"),
        [stale_spec, current_spec, stale_code, current_code],
    )
    tracked = [
        resolve_task_path(repository, "TASK-0001", name)
        for name in ("task.yaml", "events.jsonl", "approvals.json", "evidence.json")
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked}

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["approvals"] == "current"
    assert status["merge_readiness"] == "gate_required"
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked}

    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True


def _review_approval_status(
    repository: Path,
    *,
    required_ids: list[str],
    current_ids: set[tuple[str, str]],
    state: str,
) -> str:
    """Evaluate real approval contracts against a compact REVIEW classification."""
    bindings = {
        "base_commit": "1" * 40,
        "subject_commit": "2" * 40,
        "policy_sha256": "b" * 64,
        "spec_sha256": "a" * 64,
    }
    evidence = {"schema_version": "1.0", "conclusion": "passed", **bindings}
    evidence_sha256 = status_service._artifact_digest(evidence)
    current = {
        "task_id": "TASK-0001",
        **bindings,
        "governance_only": True,
        "evidence_sha256": evidence_sha256,
        "evidence_current": True,
    }
    approvals: list[dict[str, object]] = []
    for decision_unit_id, approval_type in current_ids:
        approval: dict[str, object] = {
            "schema_version": "1.0",
            "task_id": "TASK-0001",
            "decision_unit_id": decision_unit_id,
            "approval_type": approval_type,
            "actor": "reviewer",
            "reason": "current approval",
            "spec_sha256": current["spec_sha256"],
            "policy_sha256": current["policy_sha256"],
            "base_commit": current["base_commit"],
            "subject_commit": current["subject_commit"],
            "approved_at": "2026-08-20T14:00:00Z",
        }
        if approval_type == "code":
            approval["evidence_sha256"] = evidence_sha256
        approvals.append(approval)
    task_directory = repository / ".ai" / "tasks" / "TASK-0001"
    task_directory.mkdir(parents=True)
    atomic_write_json(task_directory / "approvals.json", approvals)
    classification = {
        "classifications": [
            {"decision_unit_id": decision_unit_id, "route": "REVIEW"}
            for decision_unit_id in required_ids
        ]
    }
    return status_service._approval_status(
        repository,
        "TASK-0001",
        current,
        evidence,
        classification=classification,
        state=state,
    )


@pytest.mark.parametrize(
    ("current_ids", "state", "expected"),
    [
        (
            {("DU-001", "spec"), ("DU-002", "spec")},
            "READY_TO_IMPLEMENT",
            "current",
        ),
        (
            {("DU-001", "spec"), ("DU-002", "spec"), ("DU-001", "code")},
            "IMPLEMENTING",
            "current",
        ),
        (
            {("DU-001", "spec"), ("DU-002", "spec"), ("DU-001", "code")},
            "APPROVED_FOR_MERGE",
            "stale",
        ),
        (
            {("DU-001", "spec"), ("DU-001", "code"), ("DU-002", "code")},
            "APPROVED_FOR_MERGE",
            "stale",
        ),
        (
            {
                ("DU-001", "spec"),
                ("DU-001", "code"),
                ("DU-002", "spec"),
                ("DU-002", "code"),
            },
            "APPROVED_FOR_MERGE",
            "current",
        ),
    ],
)
def test_status_requires_current_approval_for_each_review_unit(
    tmp_path: Path,
    current_ids: set[tuple[str, str]],
    state: str,
    expected: str,
) -> None:
    repository = create_repository(tmp_path / "repository")
    assert (
        _review_approval_status(
            repository,
            required_ids=["DU-001", "DU-002"],
            current_ids=current_ids,
            state=state,
        )
        == expected
    )


def test_status_and_gate_reject_when_no_current_code_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stale history record cannot substitute for the final code approval."""
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    capsys.readouterr()
    approvals = read_task_json(repository, "TASK-0001", "approvals.json")
    assert isinstance(approvals, list)
    spec = next(item for item in approvals if item["approval_type"] == "spec")
    stale_code = {
        **spec,
        "approval_type": "code",
        "subject_commit": "0" * 40,
        "evidence_sha256": "0" * 64,
    }
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "approvals.json"), [spec, stale_code]
    )

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["approvals"] == "stale"
    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert "GATE_CODE_APPROVAL_STALE" in json.loads(capsys.readouterr().out)["reason_codes"]


@pytest.mark.parametrize("approval", [None, {}])
def test_status_cannot_infer_current_approval_without_valid_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    approval: dict[str, object] | None,
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "NEW")
    if approval is None:
        approval = json.loads(
            (PROJECT_ROOT / "tests/fixtures/contracts/valid/approval.json").read_text(
                encoding="utf-8"
            )
        )
    atomic_write_json(directory / "approvals.json", [approval])
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["approvals"] == "stale"


def test_status_does_not_require_old_review_approvals_for_non_review_work(
    tmp_path: Path,
) -> None:
    repository = create_repository(tmp_path / "repository")
    assert (
        _review_approval_status(
            repository,
            required_ids=[],
            current_ids={("DU-001", "spec")},
            state="IMPLEMENTING",
        )
        == "not_applicable"
    )


def test_status_rejects_corrupt_event_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "NEW")
    (directory / "events.jsonl").write_text("{broken\n", encoding="utf-8")
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001"]) == 1
    assert "parse" in capsys.readouterr().err.lower()


def test_status_rejects_materialized_state_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = create_repository(tmp_path / "repository")
    directory = create_task(repository, "NEW")
    task = yaml.safe_load((directory / "task.yaml").read_text(encoding="utf-8"))
    task["current_state"] = "CLASSIFIED"
    atomic_write_yaml(directory / "task.yaml", task)
    monkeypatch.chdir(repository)

    assert main(["status", "TASK-0001"]) == 1
    assert "match" in capsys.readouterr().err.lower()


def test_status_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["status", "--help"])
    assert caught.value.code == 0
    assert "--format" in capsys.readouterr().out


def _prepare_native_v2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Drive a real policy-backed REVIEW/V2 task through pre_implementation_review."""
    repository = create_policy_repository(tmp_path / "repository")
    start(repository, monkeypatch)
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    unit = _auto_unit("TASK-0001")
    unit["impact"] = {"level": "medium"}
    characteristics = unit["change_characteristics"]
    assert isinstance(characteristics, dict)
    characteristics.update({"mechanical": False, "behavior_changed": True, "code_modified": True})
    unit["verification_requirements"] = {
        "acceptance_required": True,
        "integration_required": True,
        "targeted_mutation_required": True,
        "independent_verifier_required": True,
    }
    task["decision_units"] = [unit]
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    resolve_task_path(repository, "TASK-0001", "spec.md").write_text(
        specification(), encoding="utf-8"
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 0
    _record_review(repository, tmp_path, stage="design", review_id="REV-1001")
    design_context = json.loads((tmp_path / "REV-1001-context.json").read_text(encoding="utf-8"))
    assert (
        main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "spec",
                "--actor",
                "reviewer",
                "--reason",
                "spec approved",
            ]
        )
        == 0
    )
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0

    verifier_context = build_verifier_context(repository, "TASK-0001")
    save_verifier_context(repository, "TASK-0001", verifier_context)
    current_task = load_task_record(repository, "TASK-0001").task
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    bundle = load_policy_bundle(repository)
    v2 = next(
        level
        for level in bundle.documents["verification-levels.yaml"]["levels"]
        if level["id"] == "V2"
    )
    pre = prepare_v2_pre_evidence(
        {
            "schema_version": "2.0",
            "task_id": "TASK-0001",
            "decision_unit_ids": ["DU-001"],
            "repository_id": current_task["repository_id"],
            "branch": current_task["branch"],
            "base_commit": current_task["base_commit"],
            "subject_commit": current_task["subject_commit"],
            "spec_sha256": current_task["frozen_spec_sha256"],
            "policy_sha256": bundle.sha256,
            "classification_input_sha256": classification["classification_input_sha256"],
            "verification_level": "V2",
            "mode": "local",
            "checks": [
                {
                    "check_id": check["id"],
                    "category": check["id"],
                    "status": "passed",
                    "reason_code": None,
                    "required": True,
                    "exit_code": 0,
                    "timed_out": False,
                    "duration_ms": 0,
                    "stdout_log_ref": None,
                    "stderr_log_ref": None,
                    "command_summary": "deterministic fixture",
                    "tool_version": "fixture",
                }
                for check in v2["checks"]
            ],
            "unverified_scenarios": [],
            "conclusion": "passed",
            "generated_at": "2026-08-23T05:00:00Z",
            "reproduce_command": [
                "python",
                "-m",
                "aiflow",
                "verify",
                "TASK-0001",
                "--actor",
                "verifier",
            ],
            "verifier_actor": "verifier",
            "verifier_context_sha256": verifier_context["context_sha256"],
            "review_refs": {
                "design": {
                    "review_id": "REV-1001",
                    "context_sha256": design_context["context_sha256"],
                }
            },
            "targeted_mutation": {
                "evidence_ref": (
                    ".ai/tasks/TASK-0001/logs/MUTRUN-20260823T050000Z-"
                    "0000000000000000/targeted-mutation/evidence.json"
                ),
                "mutation_evidence_sha256": "0" * 64,
                "manifest_ref": ".ai/mutations/phase-02-critical-manifest.json",
                "results": [
                    {
                        "mutation_id": f"MUT-V2-{index:03d}",
                        "outcome": "killed",
                        "log_ref": None,
                    }
                    for index in range(1, 6)
                ],
            },
        }
    )
    atomic_write_json(resolve_task_path(repository, "TASK-0001", "evidence.json"), pre)
    verification_service._start_local_verification(
        repository, "TASK-0001", load_task_record(repository, "TASK-0001"), "verifier"
    )
    assert (
        verification_service._finish_local_verification(
            repository,
            "TASK-0001",
            actor="verifier",
            conclusion="passed",
            route="REVIEW",
        )
        == "WAITING_FOR_FINAL_REVIEW"
    )
    return repository


def test_status_detects_policy_routing_drift_on_approved_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status rejects persisted routing drift even when policy/input digests still match."""
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    _approve_current_review_implementation(repository, tmp_path)
    capsys.readouterr()

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    baseline = json.loads(capsys.readouterr().out)
    assert baseline["classification"] == "fresh"
    assert baseline["merge_readiness"] == "gate_required"

    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    assert isinstance(classification, dict)
    classification["effective_route"] = "AUTO"
    classification["classifications"][0]["route"] = "AUTO"
    atomic_write_json(
        resolve_task_path(repository, "TASK-0001", "classification.json"), classification
    )

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    drifted = json.loads(capsys.readouterr().out)
    assert drifted["classification"] == "fresh"
    assert drifted["merge_readiness"] == "reverification_required"
    assert drifted["missing_conditions"] == ["reverification"]


def test_status_detects_out_of_scope_worktree_and_branch_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status reflects dirty out-of-scope worktree files and branch changes before merge."""
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    _approve_current_review_implementation(repository, tmp_path)
    capsys.readouterr()

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["merge_readiness"] == "gate_required"

    outside = repository / "outside.txt"
    outside.write_text("dirty outside scope\n", encoding="utf-8")
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    dirty = json.loads(capsys.readouterr().out)
    assert dirty["merge_readiness"] == "reverification_required"
    assert dirty["missing_conditions"] == ["reverification"]

    outside.unlink()
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["merge_readiness"] == "gate_required"

    run_git(repository, "checkout", "-b", "other-branch")
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    switched = json.loads(capsys.readouterr().out)
    assert switched["merge_readiness"] == "reverification_required"
    assert switched["missing_conditions"] == ["reverification"]


def test_status_fails_closed_when_subject_commit_or_policy_check_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing/unresolvable subject commits or policy check errors fail closed."""
    from aiflow.errors import ContractError

    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    _approve_current_review_implementation(repository, tmp_path)
    capsys.readouterr()

    task_path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    assert isinstance(task, dict)

    unresolvable = {**task, "subject_commit": "0" * 40}
    atomic_write_yaml(task_path, unresolvable)
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    missing_sha = json.loads(capsys.readouterr().out)
    assert missing_sha["merge_readiness"] == "reverification_required"
    assert missing_sha["evidence"] == "stale"

    null_subject = {**task, "subject_commit": None}
    atomic_write_yaml(task_path, null_subject)
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["merge_readiness"] == "reverification_required"

    atomic_write_yaml(task_path, task)
    monkeypatch.setattr(
        status_service,
        "classification_matches_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ContractError("bad policy mapping")),
    )
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    errored_policy = json.loads(capsys.readouterr().out)
    assert errored_policy["classification"] == "fresh"
    assert errored_policy["merge_readiness"] == "reverification_required"


def test_status_native_v2_lifecycle_and_freshness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status aligns with Gate across V2 pre-review, finalization, mutation, and snapshots."""
    repository = _prepare_native_v2(tmp_path, monkeypatch)
    capsys.readouterr()

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    pre_status = json.loads(capsys.readouterr().out)
    assert pre_status["verification_level"] == "V2"
    assert pre_status["evidence"] == "awaiting_implementation_review_or_finalization"
    assert "code_approved" not in pre_status["next_events"]
    assert pre_status["missing_conditions"] == ["implementation_review", "finalization"]

    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    _record_review(repository, tmp_path, stage="implementation", review_id="REV-1002")
    capsys.readouterr()

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    reviewed_status = json.loads(capsys.readouterr().out)
    assert reviewed_status["evidence"] == "awaiting_implementation_review_or_finalization"
    assert "code_approved" not in reviewed_status["next_events"]
    assert reviewed_status["missing_conditions"] == ["finalization"]

    verification_service.verify_task(repository, "TASK-0001", actor="verifier", finalize=True)
    final_evidence = read_task_json(
        repository, "TASK-0001", "evidence.json", contract_name="evidence"
    )
    assert isinstance(final_evidence, dict)
    mutation = final_evidence["targeted_mutation"]
    assert isinstance(mutation, dict)
    passing_facts = TargetedMutationFacts(
        True,
        None,
        str(mutation["evidence_ref"]),
        str(mutation["mutation_evidence_sha256"]),
        str(mutation["manifest_ref"]),
        tuple(mutation["results"]),
    )
    monkeypatch.setattr(
        approval_service, "consume_targeted_mutation_evidence", lambda *_args: passing_facts
    )
    monkeypatch.setattr(
        gate_service, "consume_targeted_mutation_evidence", lambda *_args: passing_facts
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
                "V2 final approved",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    approved_status = json.loads(capsys.readouterr().out)
    assert approved_status["current_state"] == "APPROVED_FOR_MERGE"
    assert approved_status["classification"] == "fresh"
    assert approved_status["evidence"] == "passed"
    assert approved_status["approvals"] == "current"
    assert approved_status["merge_readiness"] == "gate_required"

    failed_facts = TargetedMutationFacts(
        False,
        "MUTATION_NOT_KILLED",
        str(mutation["evidence_ref"]),
        str(mutation["mutation_evidence_sha256"]),
        str(mutation["manifest_ref"]),
        tuple(mutation["results"]),
    )
    monkeypatch.setattr(
        gate_service, "consume_targeted_mutation_evidence", lambda *_args: failed_facts
    )
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    mutation_failed = json.loads(capsys.readouterr().out)
    assert mutation_failed["evidence"] == "stale"
    assert mutation_failed["approvals"] == "stale"
    assert mutation_failed["merge_readiness"] == "reverification_required"

    monkeypatch.setattr(
        gate_service, "consume_targeted_mutation_evidence", lambda *_args: passing_facts
    )
    tampered = dict(final_evidence)
    tampered["generated_at"] = "2026-08-24T00:00:00Z"
    atomic_write_json(resolve_task_path(repository, "TASK-0001", "evidence.json"), tampered)
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    snapshot_tampered = json.loads(capsys.readouterr().out)
    assert snapshot_tampered["evidence"] == "stale"
    assert snapshot_tampered["approvals"] == "stale"
    assert snapshot_tampered["merge_readiness"] == "reverification_required"
