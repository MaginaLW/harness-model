"""Integration coverage for local and read-only CI verification lifecycles."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from test_begin_close_commands import create_repository, make_ready, run_git, start

from aiflow import cli, verification_service
from aiflow.cli import build_parser, main
from aiflow.errors import ContractError, StorageError
from aiflow.review_service import ReviewAssessment
from aiflow.storage import atomic_write_json, read_task_json, resolve_task_path
from aiflow.task_service import load_task_record
from aiflow.verification import (
    VerificationCheck,
    VerificationContext,
    VerificationExecution,
    VerificationPlan,
)
from aiflow.verification_service import VerifyResult


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


@pytest.mark.parametrize("route", ["AUTO", "ASK"])
def test_full_non_review_verification_reaches_merge_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    route: str,
) -> None:
    repository = _prepare(tmp_path, monkeypatch, route=route)

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


def test_v2_live_run_uses_v1_prefix_and_writes_failed_pre_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _prepare(tmp_path, monkeypatch)
    _enable_v2(repository)
    levels: list[str] = []
    base_plan = _plan()

    def v2_plan(bundle, context: VerificationContext, *, level: str) -> VerificationPlan:
        levels.append(level)
        prefix = base_plan(bundle, context, level=level)
        extras = tuple(
            VerificationCheck(
                check_id,
                "V2",
                (sys.executable, "-m", "aiflow", "--help"),
                {},
                context.repository_root.resolve(),
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
        return VerificationPlan(
            level,
            prefix.run_dir,
            (*prefix.checks, *extras),
            prefix.executions,
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

    result = verification_service.verify_task(repository, "TASK-0001", actor="verifier")

    assert levels == ["V2"]
    assert result.conclusion == "failed"
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    assert evidence["schema_version"] == "2.0"
    assert evidence["phase"] == "pre_implementation_review"
    assert evidence["verification_level"] == "V2"
    assert len(str(evidence["verifier_context_sha256"])) == 64
    checks = {str(check["check_id"]): check for check in evidence["checks"]}
    for check_id in ("acceptance", "integration", "targeted_mutation"):
        assert checks[check_id]["status"] == "unverified"
        assert checks[check_id]["required"] is True
        assert checks[check_id]["reason_code"]
    assert checks["independent_verifier"]["status"] == "passed"
    assert checks["independent_verifier"]["required"] is True


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
