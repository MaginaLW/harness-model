"""Chapter 5 end-to-end verification, evidence, freshness, and Gate regression."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from test_approve_command import review_package
from test_begin_close_commands import create_repository, make_ready, run_git, start
from test_gate_command import _prepare_gate
from test_governance_paths import _auto_unit
from test_verify_command import _plan

from aiflow import verification_service
from aiflow.cli import main
from aiflow.review_service import build_review_context, record_review
from aiflow.storage import (
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record
from aiflow.verification import (
    V0_CHECK_IDS,
    V1_CHECK_IDS,
    VerificationCheck,
    VerificationContext,
    VerificationExecution,
    VerificationPlan,
)


def _full_category_plan():
    def build(_bundle, context: VerificationContext, *, level: str) -> VerificationPlan:
        check_ids = V0_CHECK_IDS if level == "V0" else V1_CHECK_IDS
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
        argv = (sys.executable, "-c", "print('chapter-five-checks-passed')")
        checks = tuple(
            VerificationCheck(
                check_id,
                level,
                argv,
                {},
                context.repository_root.resolve(),
                10,
                True,
                "exit_zero",
            )
            for check_id in check_ids
        )
        execution = VerificationExecution(
            "EXEC-CHAPTER-05", argv, {}, checks[0].cwd, 10, tuple(check_ids)
        )
        return VerificationPlan(
            level,
            run_dir,
            checks,
            (execution,),
            (),
            (),
            context.subject_commit,
        )

    return build


def _missing_tool_plan():
    base = _plan()

    def build(bundle, context: VerificationContext, *, level: str) -> VerificationPlan:
        plan = base(bundle, context, level=level)
        return VerificationPlan(
            plan.level,
            plan.run_dir,
            plan.checks,
            plan.executions,
            ("VERIFICATION_TOOL_MISSING:smoke",),
            (),
            plan.comparison_subject,
        )

    return build


def _timeout_plan():
    def build(_bundle, context: VerificationContext, *, level: str) -> VerificationPlan:
        run_dir = (
            context.repository_root / ".ai" / "tasks" / context.task_id / "logs" / context.run_id
        ).resolve()
        argv = (sys.executable, "-c", "import time; time.sleep(2)")
        check = VerificationCheck(
            "smoke", level, argv, {}, context.repository_root.resolve(), 1, True, "exit_zero"
        )
        execution = VerificationExecution("EXEC-TIMEOUT", argv, {}, check.cwd, 1, ("smoke",))
        return VerificationPlan(
            level, run_dir, (check,), (execution,), (), (), context.subject_commit
        )

    return build


def _prepare_real_policy_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, review: bool
) -> Path:
    repository = create_repository(tmp_path / "repository")
    (repository / "src").mkdir()
    (repository / "src" / "sample.py").write_text("value: int = 1\n", encoding="utf-8")
    (repository / "tests" / "unit").mkdir(parents=True)
    (repository / "tests" / "unit" / "test_sample.py").write_text(
        "from pathlib import Path\n\nimport aiflow\n\n"
        "\n"
        "def test_sample_source_exists() -> None:\n"
        '    assert (Path(__file__).parents[2] / "src" / "sample.py").is_file()\n'
        "    assert aiflow.__version__\n",
        encoding="utf-8",
    )
    (repository / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths = ['tests']\n"
        "[tool.mypy]\npython_version = '3.11'\nstrict = true\nfiles = ['src']\n"
        "[tool.ruff]\ntarget-version = 'py311'\n",
        encoding="utf-8",
    )
    (repository / ".gitignore").write_text(
        ".pytest_cache/\n.mypy_cache/\n.ruff_cache/\n__pycache__/\n*.pyc\n",
        encoding="utf-8",
    )
    run_git(repository, "add", "src", "tests", "pyproject.toml", ".gitignore")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "verification fixture",
    )
    start(repository, monkeypatch)
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    unit = _auto_unit("TASK-0001")
    if review:
        unit["impact"] = {"level": "medium"}
        unit["change_characteristics"] = {
            "mechanical": False,
            "behavior_changed": True,
            "code_modified": True,
            "interaction_scope": "cross_module",
            "regression_risk": True,
            "error_detectability": "low",
        }
    task["decision_units"] = [unit]
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    make_ready(repository, route="REVIEW" if review else "AUTO", valid_approval=review)
    classification = read_task_json(
        repository, "TASK-0001", "classification.json", contract_name="classification"
    )
    if not review:
        classification["effective_verification_level"] = "V0"
        classification["classifications"][0]["verification_level"] = "V0"
        atomic_write_json(
            resolve_task_path(repository, "TASK-0001", "classification.json"), classification
        )
    else:
        approvals = read_task_json(repository, "TASK-0001", "approvals.json")
        approvals[0]["base_commit"] = task["base_commit"]
        atomic_write_json(resolve_task_path(repository, "TASK-0001", "approvals.json"), approvals)
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    return repository


def _record_structured_review(repository: Path, *, stage: str) -> None:
    review_directory = resolve_task_path(repository, "TASK-0001", "reviews")
    review_id = f"REV-{9001 + len(list(review_directory.glob('REV-*-r*.json'))):04d}"
    context = build_review_context(repository, "TASK-0001", stage)
    record_review(
        repository,
        "TASK-0001",
        actor="reviewer",
        input_path={
            "schema_version": "1.0",
            "review_id": review_id,
            "review_stage": stage,
            "recorded_at": "2026-08-22T01:00:00Z",
            "context_sha256": context["context_sha256"],
            "outcome": "APPROVE",
            "summary": f"current {stage} context approved",
            "findings": [],
        },
    )


def _approve_code(repository: Path, *, reason: str) -> None:
    resolve_task_path(repository, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    _record_structured_review(repository, stage="implementation")
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
                reason,
            ]
        )
        == 0
    )


@pytest.mark.parametrize(
    ("review", "expected_level", "expected_check_ids"),
    [(False, "V0", V0_CHECK_IDS), (True, "V1", V1_CHECK_IDS)],
)
def test_v0_v1_evidence_reproduction_and_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    review: bool,
    expected_level: str,
    expected_check_ids: tuple[str, ...],
) -> None:
    repository = _prepare_real_policy_plan(tmp_path, monkeypatch, review=review)
    monkeypatch.setattr(verification_service, "parse_verification_plan", _full_category_plan())

    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    assert evidence["verification_level"] == expected_level
    assert tuple(check["check_id"] for check in evidence["checks"]) == expected_check_ids
    reproduce = evidence["reproduce_command"]
    assert reproduce[:3] == ["python", "-m", "aiflow"]
    assert main(reproduce[3:]) == 0

    if review:
        _approve_code(repository, reason="chapter exit review")
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    assert not (repository / ".coverage").exists()
    assert not (repository / "coverage.xml").exists()


def test_failed_evidence_and_logs_are_retained_after_reasoned_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan(failed=True))

    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    failed = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    failed_ref = failed["checks"][0]["stdout_log_ref"]
    failed_log = resolve_task_path(repository, "TASK-0001", failed_ref)
    failed_run = Path(failed_ref).parts[1]
    failed_archive = resolve_task_path(repository, "TASK-0001", f"logs/{failed_run}/evidence.json")
    assert failed["conclusion"] == "failed" and failed_log.is_file()
    assert main(["gate", "TASK-0001", "--format", "json"]) == 2

    assert (
        main(
            [
                "begin",
                "TASK-0001",
                "--actor",
                "implementer",
                "--reason",
                "fix the failed verification",
            ]
        )
        == 0
    )
    implementation = repository / "src" / "module.py"
    implementation.parent.mkdir(exist_ok=True)
    implementation.write_text("fixed after failed verification\n", encoding="utf-8")
    run_git(repository, "add", "src/module.py")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "fix failed verification",
    )
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan())
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    passed = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")

    assert passed["conclusion"] == "passed"
    assert passed["checks"][0]["stdout_log_ref"] != failed_ref
    assert failed_log.is_file()
    assert json.loads(failed_archive.read_text(encoding="utf-8"))["conclusion"] == "failed"
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0


def test_governance_attestation_preserves_subject_and_ci_gate_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    subject = load_task_record(repository, "TASK-0001").task["subject_commit"]
    attestation = resolve_task_path(repository, "TASK-0001", "attestation.md")
    attestation.write_text("governance attestation\n", encoding="utf-8")
    run_git(repository, "add", ".ai/tasks/TASK-0001/attestation.md")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "task governance attestation",
    )

    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    assert load_task_record(repository, "TASK-0001").task["subject_commit"] == subject
    ci_run = tmp_path / "chapter-ci-run"
    ci_run.mkdir()
    ci_evidence = ci_run / "evidence.json"
    assert (
        main(
            [
                "verify",
                "TASK-0001",
                "--ci",
                "--ci-run-dir",
                str(ci_run),
                "--output",
                str(ci_evidence),
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
                str(ci_evidence),
                "--format",
                "json",
            ]
        )
        == 0
    )
    assert json.loads(ci_evidence.read_text(encoding="utf-8"))["attestation_governance_only"]


def test_review_attestation_and_business_change_require_fresh_code_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch, review=True)
    _approve_code(repository, reason="approve first review snapshot")
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0
    subject = load_task_record(repository, "TASK-0001").task["subject_commit"]
    run_git(
        repository,
        "add",
        ".ai/tasks/TASK-0001/evidence.json",
        ".ai/tasks/TASK-0001/approvals.json",
        ".ai/tasks/TASK-0001/events.jsonl",
    )
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "review evidence attestation",
    )
    ci_run = tmp_path / "review-ci"
    ci_run.mkdir()
    external = ci_run / "evidence.json"
    assert (
        main(
            [
                "verify",
                "TASK-0001",
                "--ci",
                "--ci-run-dir",
                str(ci_run),
                "--output",
                str(external),
            ]
        )
        == 0
    )
    assert main(["gate", "TASK-0001", "--evidence", str(external), "--format", "json"]) == 0
    assert load_task_record(repository, "TASK-0001").task["subject_commit"] == subject

    implementation = repository / "src" / "module.py"
    implementation.parent.mkdir(exist_ok=True)
    implementation.write_text("reviewed business update\n", encoding="utf-8")
    run_git(repository, "add", "src/module.py")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "review business update",
    )
    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert (
        "GATE_CODE_APPROVAL_STALE"
        in json.loads(capsys.readouterr().out.splitlines()[-1])["reason_codes"]
    )
    _approve_code(repository, reason="approve updated review snapshot")
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0


def test_business_commit_stales_gate_until_reverification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    implementation = repository / "src" / "module.py"
    implementation.parent.mkdir(exist_ok=True)
    implementation.write_text("changed after evidence\n", encoding="utf-8")
    run_git(repository, "add", "src/module.py")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "new implementation snapshot",
    )

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0

    implementation.write_text("second implementation snapshot\n", encoding="utf-8")
    run_git(repository, "add", "src/module.py")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "second implementation snapshot",
    )
    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0


@pytest.mark.parametrize(
    ("plan_builder", "reason_code", "timed_out"),
    [
        (_missing_tool_plan, "VERIFICATION_TOOL_MISSING", False),
        (_timeout_plan, "RUNNER_TIMEOUT", True),
    ],
)
def test_missing_tool_and_timeout_produce_failed_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    plan_builder,
    reason_code: str,
    timed_out: bool,
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    monkeypatch.setattr(verification_service, "parse_verification_plan", plan_builder())

    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    evidence = read_task_json(repository, "TASK-0001", "evidence.json", contract_name="evidence")
    check = evidence["checks"][0]
    assert evidence["conclusion"] == "failed"
    assert check["reason_code"] == reason_code
    assert check["timed_out"] is timed_out
    assert load_task_record(repository, "TASK-0001").task["current_state"] == "FAILED"
    archived = list(resolve_task_path(repository, "TASK-0001", "logs").glob("*/evidence.json"))
    assert any(
        json.loads(path.read_text(encoding="utf-8"))["checks"][0]["reason_code"] == reason_code
        for path in archived
    )


def test_spec_change_recovers_via_escalate_resolve_reclassify_and_reapprove(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    spec = resolve_task_path(repository, "TASK-0001", "spec.md")
    spec.write_text(spec.read_text(encoding="utf-8") + "\nChanged requirement.\n", encoding="utf-8")
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    unit = task["decision_units"][0]
    unit["impact"] = {"level": "medium"}
    unit["change_characteristics"].update(
        {"mechanical": False, "behavior_changed": True, "code_modified": True}
    )
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    resolution = resolve_task_path(repository, "TASK-0001", "resolution.md")
    resolution.write_text("specification was revised and reviewed\n", encoding="utf-8")

    assert (
        main(
            [
                "escalate",
                "TASK-0001",
                "--to",
                "REVIEW",
                "--reason-code",
                "spec_changed",
                "--impact",
                "specification binding changed",
                "--next-step",
                "reclassify and reapprove",
                "--actor",
                "implementer",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "resolve",
                "TASK-0001",
                "--condition",
                "spec_changed",
                "--evidence-ref",
                "resolution.md",
                "--reason",
                "revised specification is ready",
                "--actor",
                "implementer",
            ]
        )
        == 0
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 0
    _record_structured_review(repository, stage="design")
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
                "revised specification approved",
            ]
        )
        == 0
    )
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _approve_code(repository, reason="recovered specification implementation approved")
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0


def test_policy_change_recovers_after_explicit_scoped_subject_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    policy_path = repository / ".ai" / "policy" / "routing.yaml"
    policy_path.write_text(
        policy_path.read_text(encoding="utf-8").replace(
            "Multiple reasonable business directions require a user choice.",
            "Multiple reasonable business directions require an explicit user choice.",
        ),
        encoding="utf-8",
    )
    task = read_task_yaml(repository, "TASK-0001", "task.yaml", contract_name="task")
    task["allowed_scope"].append(".ai/policy/**")
    unit = task["decision_units"][0]
    unit["impact_scope"].append(".ai/policy/routing.yaml")
    unit["impact"] = {"level": "medium"}
    unit["change_characteristics"].update(
        {"mechanical": False, "behavior_changed": True, "code_modified": True}
    )
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)
    run_git(repository, "add", ".ai/policy/routing.yaml")
    run_git(
        repository,
        "-c",
        "user.name=AI Flow Tests",
        "-c",
        "user.email=aiflow@example.invalid",
        "commit",
        "-m",
        "update verification policy explanation",
    )
    assert main(["sync", "TASK-0001", "--actor", "implementer"]) == 0
    resolution = resolve_task_path(repository, "TASK-0001", "resolution.md")
    resolution.write_text("policy update was reviewed\n", encoding="utf-8")
    assert (
        main(
            [
                "escalate",
                "TASK-0001",
                "--to",
                "REVIEW",
                "--reason-code",
                "policy_changed",
                "--impact",
                "Policy binding changed",
                "--next-step",
                "reclassify and reapprove",
                "--actor",
                "implementer",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "resolve",
                "TASK-0001",
                "--condition",
                "policy_changed",
                "--evidence-ref",
                "resolution.md",
                "--reason",
                "updated Policy is ready",
                "--actor",
                "implementer",
            ]
        )
        == 0
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert main(["freeze", "TASK-0001", "--actor", "specifier"]) == 0
    _record_structured_review(repository, stage="design")
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
                "updated Policy specification approved",
            ]
        )
        == 0
    )
    assert main(["begin", "TASK-0001", "--actor", "implementer"]) == 0
    assert main(["verify", "TASK-0001", "--actor", "verifier"]) == 0
    _approve_code(repository, reason="updated Policy implementation approved")
    assert main(["gate", "TASK-0001", "--format", "json"]) == 0


@pytest.mark.parametrize("changed_artifact", ["spec", "policy"])
def test_specification_and_policy_changes_invalidate_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    changed_artifact: str,
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    capsys.readouterr()
    if changed_artifact == "spec":
        path = resolve_task_path(repository, "TASK-0001", "spec.md")
        path.write_text(
            path.read_text(encoding="utf-8") + "\nChanged requirement.\n", encoding="utf-8"
        )
        expected = "GATE_SPEC_STALE"
    else:
        path = repository / ".ai" / "policy" / "routing.yaml"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(
                "Multiple reasonable business directions require a user choice.",
                "Multiple reasonable business directions require an explicit user choice.",
            ),
            encoding="utf-8",
        )
        expected = "GATE_CLASSIFICATION_STALE"

    assert main(["gate", "TASK-0001", "--format", "json"]) == 2
    assert expected in json.loads(capsys.readouterr().out)["reason_codes"]


def test_chapter_flow_leaves_no_root_coverage_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _prepare_gate(tmp_path, monkeypatch)
    assert not (repository / ".coverage").exists()
    assert not (repository / "coverage.xml").exists()
