"""The optional SDK supplement preserves native review-context authority."""

from __future__ import annotations

import builtins
import copy
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pytest
from test_begin_close_commands import commit_all, create_repository, make_ready, run_git
from test_governance_paths import _auto_unit
from test_verify_command import _plan

from aiflow import cli, verification_service
from aiflow.errors import StorageError
from aiflow.review_service import build_review_context, validate_review_context
from aiflow.status_service import summarize_task
from aiflow.storage import atomic_write_json, atomic_write_yaml, read_task_json, resolve_task_path
from aiflow.task_service import load_task_record, transition_task_record

TASK_ID = "TASK-0001"
DOCUMENT = "docs/contract.md"


@pytest.fixture
def ready_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repository = create_repository(tmp_path / "repository")
    (repository / "docs").mkdir()
    (repository / DOCUMENT).write_text("# Contract\n\nOriginal requirement.\n", encoding="utf-8")
    (repository / "docs/unchanged.md").write_text("# Unchanged\n", encoding="utf-8")
    (repository / ".gitignore").write_text("/build/\n/.ai/tasks/*/logs/\n", encoding="utf-8")
    commit_all(repository, "docs: baseline contract")
    monkeypatch.chdir(repository)
    assert cli.main(["start", "--objective", "Revise one contract", "--allow", "docs/**"]) == 0
    task = load_task_record(repository, TASK_ID).task
    unit = _auto_unit(TASK_ID)
    unit["impact_scope"] = [DOCUMENT]
    unit["impact"] = {"level": "medium"}
    task["decision_units"] = [unit]
    atomic_write_yaml(resolve_task_path(repository, TASK_ID, "task.yaml"), task)
    make_ready(repository, route="REVIEW", valid_approval=True)
    assert cli.main(["begin", TASK_ID, "--actor", "implementer"]) == 0
    (repository / DOCUMENT).write_text("# Contract\n\nRevised requirement.\n", encoding="utf-8")
    commit_all(repository, "docs: implement the bounded contract change")
    monkeypatch.setattr(verification_service, "parse_verification_plan", _plan())
    assert cli.main(["verify", TASK_ID, "--actor", "verifier"]) == 0
    status = summarize_task(repository, TASK_ID)
    assert status.current_state == "WAITING_FOR_FINAL_REVIEW"
    assert status.classification == "fresh"
    assert status.evidence == "passed"
    context = build_review_context(repository, TASK_ID, "implementation")
    assert DOCUMENT in context["content"]["diff_summary"]["changed_paths"]
    return repository


def native_bytes(repository: Path) -> dict[str, bytes]:
    root = resolve_task_path(repository, TASK_ID)
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def arguments(
    repository: Path, *, output: Path | None = None, stage: str = "implementation"
) -> list[str]:
    return [
        "review",
        "context",
        TASK_ID,
        "--stage",
        stage,
        "--sdk-review-enable-once",
        "--sdk-review-document",
        DOCUMENT,
        "--sdk-review-reference-document",
        DOCUMENT,
        "--sdk-review-question",
        "Check the changed requirement against the fixed reference.",
        "--sdk-review-output",
        str(output or repository / "build/sdk-supplement"),
    ]


def install_fake_runtime(
    monkeypatch: pytest.MonkeyPatch, *, status: str = "completed", outcome: str = "APPROVE"
) -> list[dict[str, Any]]:
    module = importlib.import_module("aiflow.sdk_review")
    calls: list[dict[str, Any]] = []

    def run(request: dict[str, Any], workdir: Path, expected: dict[str, str]) -> dict[str, Any]:
        calls.append(copy.deepcopy(request))
        findings = (
            []
            if outcome == "APPROVE"
            else [
                {
                    "finding_id": "RF-001",
                    "severity": "medium",
                    "title": "A contract contradiction",
                    "path": DOCUMENT,
                    "line": 3,
                    "evidence": "The two supplied requirements conflict.",
                }
            ]
        )
        return {
            "status": status,
            "report": json.dumps(
                {"outcome": outcome, "summary": "Scoped review.", "findings": findings}
            ),
            "runtime_version": "0.163.0",
        }

    monkeypatch.setattr(module, "_run_sdk", run)
    return calls


def block_sdk_imports(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    attempted: list[str] = []
    real_import = builtins.__import__
    real_import_module = importlib.import_module

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        fromlist = kwargs.get("fromlist", args[2] if len(args) > 2 else ()) or ()
        if (
            name == "aiflow.sdk_review"
            or name.startswith("openai_codex")
            or (name == "aiflow" and "sdk_review" in fromlist)
        ):
            attempted.append(name)
            raise AssertionError("SDK runner imported before supplement eligibility")
        return real_import(name, *args, **kwargs)

    def guarded_module(name: str, package: str | None = None) -> Any:
        if name == "aiflow.sdk_review" or name.startswith("openai_codex"):
            attempted.append(name)
            raise AssertionError("SDK runner imported before supplement eligibility")
        return real_import_module(name, package)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(importlib, "import_module", guarded_module)
    return attempted


def rehash(context: dict[str, Any]) -> dict[str, Any]:
    content = {key: value for key, value in context.items() if key != "context_sha256"}
    context["context_sha256"] = hashlib.sha256(
        json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    validate_review_context(context)
    return context


@pytest.mark.parametrize("outcome", ["APPROVE", "REQUEST_CHANGES"])
def test_enabled_supplement_dispatches_once_without_native_state_effects(
    ready_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    repository = ready_task
    expected = dict(build_review_context(repository, TASK_ID, "implementation"))
    before = native_bytes(repository)
    calls = install_fake_runtime(monkeypatch, outcome=outcome)
    capsys.readouterr()

    assert cli.main(arguments(repository)) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
    assert "completed" in captured.err
    assert len(calls) == 1
    assert calls[0]["candidate"] == expected["subject_commit"]
    assert calls[0]["reference"] == expected["base_commit"]
    receipt = json.loads(
        (repository / "build/sdk-supplement/receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["report"]["outcome"] == outcome
    assert receipt["trigger_binding"] == {
        "node": "review_context_implementation",
        "task_id": TASK_ID,
        "context_sha256": expected["context_sha256"],
    }
    assert native_bytes(repository) == before


@pytest.mark.parametrize("file_output", [False, True])
def test_default_context_output_and_zero_runner_import_are_unchanged(
    ready_task: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    file_output: bool,
) -> None:
    expected = dict(build_review_context(ready_task, TASK_ID, "implementation"))
    before = native_bytes(ready_task)
    attempted = block_sdk_imports(monkeypatch)
    argv = ["review", "context", TASK_ID, "--stage", "implementation"]
    destination = tmp_path / "native-context.json"
    if file_output:
        argv += ["--output", str(destination)]
    capsys.readouterr()

    assert cli.main(argv) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    if file_output:
        assert captured.out.strip() == str(destination.resolve())
        assert json.loads(destination.read_text(encoding="utf-8")) == expected
    else:
        assert json.loads(captured.out) == expected
    assert attempted == []
    assert native_bytes(ready_task) == before
    assert not (ready_task / "build").exists()


def reject_before_runner_import(
    repository: Path,
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = native_bytes(repository)
    attempted = block_sdk_imports(monkeypatch)
    capsys.readouterr()
    assert cli.main(argv) == 1
    captured = capsys.readouterr()
    assert captured.err
    assert str(repository) not in captured.err
    assert attempted == []
    assert native_bytes(repository) == before
    assert not (repository / "build").exists()


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--sdk-review-document", DOCUMENT),
        ("--sdk-review-reference-document", DOCUMENT),
        ("--sdk-review-question", "Check this contract."),
        ("--sdk-review-output", "build/partial"),
        ("--sdk-review-global-instructions-sha256", "0" * 64),
    ],
)
def test_partial_options_without_enable_reject_before_runner_import(
    ready_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flag: str,
    value: str,
) -> None:
    reject_before_runner_import(
        ready_task,
        ["review", "context", TASK_ID, "--stage", "implementation", flag, value],
        monkeypatch,
        capsys,
    )


def test_design_stage_rejects_enabled_supplement_before_runner_import(
    ready_task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reject_before_runner_import(
        ready_task, arguments(ready_task, stage="design"), monkeypatch, capsys
    )


@pytest.mark.parametrize(
    "flag",
    [
        "--sdk-review-document",
        "--sdk-review-reference-document",
        "--sdk-review-question",
        "--sdk-review-output",
    ],
)
def test_enabled_supplement_requires_each_explicit_material_before_runner_import(
    ready_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flag: str,
) -> None:
    argv = arguments(ready_task)
    index = argv.index(flag)
    del argv[index : index + 2]
    reject_before_runner_import(ready_task, argv, monkeypatch, capsys)


@pytest.mark.parametrize(
    "condition", ["classification", "stale-evidence", "failed-evidence", "state"]
)
def test_unready_native_facts_reject_before_runner_import(
    ready_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    condition: str,
) -> None:
    if condition == "classification":
        record = read_task_json(ready_task, TASK_ID, "classification.json")
        record["policy_sha256"] = "0" * 64
        atomic_write_json(resolve_task_path(ready_task, TASK_ID, "classification.json"), record)
    elif condition == "state":
        transition_task_record(
            ready_task,
            TASK_ID,
            target_state="VERIFYING",
            event_type="verification_restarted",
            actor="fixture",
            payload={},
            satisfied_preconditions={"reverification_requested"},
        )
    else:
        record = read_task_json(ready_task, TASK_ID, "evidence.json")
        if condition == "failed-evidence":
            record["conclusion"] = "failed"
        else:
            record["subject_commit"] = record["base_commit"]
        atomic_write_json(resolve_task_path(ready_task, TASK_ID, "evidence.json"), record)
    reject_before_runner_import(ready_task, arguments(ready_task), monkeypatch, capsys)


@pytest.mark.parametrize(
    "binding", ["task_id", "repository_id", "base_commit", "subject_commit", "hash"]
)
def test_wrong_context_binding_or_hash_rejects_before_runner_import(
    ready_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    binding: str,
) -> None:
    original = cli.build_review_context

    def wrong_context(*args: Any, **kwargs: Any) -> dict[str, Any]:
        context = copy.deepcopy(dict(original(*args, **kwargs)))
        if binding == "task_id":
            context["task_id"] = "TASK-9999"
        elif binding == "repository_id":
            context["repository_id"] = "123e4567-e89b-42d3-a456-426614174001"
        elif binding == "base_commit":
            context["base_commit"] = context["subject_commit"]
        elif binding == "subject_commit":
            context["subject_commit"] = context["base_commit"]
        else:
            context["context_sha256"] = "0" * 64
            return context
        return rehash(context)

    monkeypatch.setattr(cli, "build_review_context", wrong_context)
    reject_before_runner_import(ready_task, arguments(ready_task), monkeypatch, capsys)


def test_recomputed_context_change_rejects_without_dispatch(
    ready_task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original = cli.build_review_context
    contexts = 0

    def changing_context(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal contexts
        contexts += 1
        context = copy.deepcopy(dict(original(*args, **kwargs)))
        if contexts >= 2:
            context["content"]["goal"] = "Changed while preparing this supplement"
            return rehash(context)
        return context

    monkeypatch.setattr(cli, "build_review_context", changing_context)
    reject_before_runner_import(ready_task, arguments(ready_task), monkeypatch, capsys)
    assert contexts >= 2


@pytest.mark.parametrize(
    "path", ["docs/unchanged.md", "docs/missing.md", "tracked.txt", "../docs/contract.md"]
)
def test_candidate_selection_must_be_explicit_changed_documentation(
    ready_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    path: str,
) -> None:
    argv = arguments(ready_task)
    argv[argv.index("--sdk-review-document") + 1] = path
    reject_before_runner_import(ready_task, argv, monkeypatch, capsys)


def test_governance_head_tail_does_not_replace_the_fixed_candidate(
    ready_task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    subject = load_task_record(ready_task, TASK_ID).task["subject_commit"]
    resolve_task_path(ready_task, TASK_ID, "tail.md").write_text(
        "Own-task governance tail.\n", encoding="utf-8"
    )
    commit_all(ready_task, "task: record governance attestation after the reviewed subject")
    assert run_git(ready_task, "rev-parse", "HEAD") != subject
    assert summarize_task(ready_task, TASK_ID).evidence == "passed"
    before = native_bytes(ready_task)
    calls = install_fake_runtime(monkeypatch)
    capsys.readouterr()

    assert cli.main(arguments(ready_task)) == 0

    assert len(calls) == 1
    assert calls[0]["candidate"] == subject
    candidate = next(item for item in calls[0]["documents"] if item["role"] == "candidate")
    assert candidate["blob"] == run_git(ready_task, "rev-parse", f"{subject}:{DOCUMENT}")
    assert native_bytes(ready_task) == before


@pytest.mark.parametrize("status", ["completed", "failed", "unknown"])
def test_supplement_result_is_retained_and_same_output_never_replays(
    ready_task: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: str,
) -> None:
    expected = dict(build_review_context(ready_task, TASK_ID, "implementation"))
    before = native_bytes(ready_task)
    calls = install_fake_runtime(monkeypatch, status=status)
    capsys.readouterr()
    assert cli.main(arguments(ready_task)) == (0 if status == "completed" else 1)
    first = capsys.readouterr()
    assert json.loads(first.out) == expected
    assert status in first.err
    receipt_path = ready_task / "build/sdk-supplement/receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == status
    original = receipt_path.read_bytes()

    assert cli.main(arguments(ready_task)) == 1

    assert len(calls) == 1
    assert receipt_path.read_bytes() == original
    assert native_bytes(ready_task) == before


def test_supplement_execution_exception_preserves_native_context_and_safe_error(
    ready_task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = importlib.import_module("aiflow.sdk_review")
    calls = 0

    def failing_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise RuntimeError("PRIVATE SDK TRANSPORT DETAIL")

    monkeypatch.setattr(module, "execute_review", failing_execute)
    expected = dict(build_review_context(ready_task, TASK_ID, "implementation"))
    before = native_bytes(ready_task)
    capsys.readouterr()

    assert cli.main(arguments(ready_task)) == 1

    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
    assert captured.err
    assert "PRIVATE" not in captured.err
    assert str(ready_task) not in captured.err
    assert calls == 1
    assert native_bytes(ready_task) == before


def test_dispatch_recheck_after_input_preparation_preserves_the_original_context(
    ready_task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    expected = dict(build_review_context(ready_task, TASK_ID, "implementation"))
    before = native_bytes(ready_task)
    calls = install_fake_runtime(monkeypatch)
    original = cli.build_review_context
    contexts = 0

    def changing_context(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal contexts
        contexts += 1
        context = copy.deepcopy(dict(original(*args, **kwargs)))
        if contexts >= 3:
            context["content"]["goal"] = "Changed after the fixed inputs were prepared"
            return rehash(context)
        return context

    monkeypatch.setattr(cli, "build_review_context", changing_context)
    capsys.readouterr()

    assert cli.main(arguments(ready_task)) == 1

    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
    assert captured.err
    assert contexts >= 3
    assert calls == []
    assert not (ready_task / "build").exists()
    assert native_bytes(ready_task) == before


def test_native_context_output_failure_never_dispatches_or_replaces_the_previous_file(
    ready_task: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destination = tmp_path / "native-context.json"
    destination.write_bytes(b"Previous context retained.\n")
    previous = destination.read_bytes()
    before = native_bytes(ready_task)
    calls = install_fake_runtime(monkeypatch)

    def unavailable_output(*args: Any, **kwargs: Any) -> None:
        raise StorageError("Native context output is unavailable", code="STORAGE_WRITE_FAILED")

    monkeypatch.setattr(cli, "atomic_write_json", unavailable_output)
    capsys.readouterr()

    assert cli.main(arguments(ready_task) + ["--output", str(destination)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err
    assert destination.read_bytes() == previous
    assert calls == []
    assert not (ready_task / "build").exists()
    assert native_bytes(ready_task) == before
