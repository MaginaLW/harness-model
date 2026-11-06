"""Portable authority/transaction/parser tests, never Windows execution evidence.

Task history, Git and retained files are real. Windows host-material discovery
uses public fixture files; recorder tests stop at a rejected or interrupted Job
boundary. Parser receipts below are deliberately synthetic inputs, never proof
that a Job ran.
Actual installed-wheel execution remains in the Windows integration suite.
"""

from __future__ import annotations

import ast
import builtins
import io
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier, local
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from initialization_helpers import fixture_git, snapshot_tree
from test_policy import v2_documents

from aiflow import installed_mutations as runtime
from aiflow import node_execution as node
from aiflow import process_runner as processes
from aiflow.approval import approve_task
from aiflow.classification_service import classify_task
from aiflow.errors import AiflowError, ContractError, PolicyError
from aiflow.facts_service import record_risk_facts
from aiflow.mutation_runner import _outside_target_dump
from aiflow.review_service import build_review_context, record_review
from aiflow.specification import REQUIRED_SECTIONS
from aiflow.storage import read_task_yaml, resolve_task_path
from aiflow.task_service import (
    begin_task,
    freeze_task,
    record_task_event,
    start_task,
    transition_task_record,
)
from aiflow.verifier_service import build_verifier_context, save_verifier_context

ROOT = Path(__file__).resolve().parents[2]
TASK = "TASK-0001"
ACTOR = "fixture-independent-verifier"
PROBE = "MUT-V2-001"
OS_PROCESS_APIS = (
    "system",
    "popen",
    "execv",
    "execve",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
    "posix_spawn",
    "startfile",
)


def put_json(path: Path, value: object) -> None:
    path.write_bytes(node._canonical(value))


@contextmanager
def pure_guard(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """Count attempts even when production code catches the injected exception."""
    attempts: list[str] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        attempts.append("process-or-write")
        raise AssertionError("pure reader attempted a process or filesystem write")

    actual_open, actual_io_open = os.open, io.open

    def read_descriptor(path, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            forbidden(path, flags)
        return actual_open(path, flags, *args, **kwargs)

    def read_stream(path, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            forbidden(path, mode)
        return actual_io_open(path, mode, *args, **kwargs)

    with monkeypatch.context() as patch:
        for name in OS_PROCESS_APIS:
            if hasattr(os, name):
                patch.setattr(os, name, forbidden)
        for module, names in (
            (subprocess, ("Popen", "run", "call", "check_call", "check_output")),
            (node, ("run_node_process", "_process")),
            (processes, ("run_node_process", "run_execution")),
            (
                os,
                (
                    "mkdir",
                    "makedirs",
                    "remove",
                    "unlink",
                    "rmdir",
                    "rename",
                    "replace",
                    "write",
                    "ftruncate",
                    "truncate",
                    "chmod",
                    "utime",
                ),
            ),
            (
                Path,
                (
                    "write_bytes",
                    "write_text",
                    "mkdir",
                    "unlink",
                    "rmdir",
                    "rename",
                    "replace",
                    "touch",
                    "chmod",
                ),
            ),
        ):
            for name in names:
                patch.setattr(module, name, forbidden)
        patch.setattr(os, "open", read_descriptor)
        patch.setattr(io, "open", read_stream)
        patch.setattr(builtins, "open", read_stream)
        yield attempts
    assert not attempts, "the reader caught a forbidden operation instead of avoiding it"


@dataclass(frozen=True)
class Model:
    root: Path
    inputs: runtime.InstalledMutationInputs
    context: dict
    materials: dict
    recorder: Callable
    process_writer: Callable
    material_collector: Callable


@pytest.fixture
def model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request) -> Iterator[Model]:
    recorder, process_writer, material_collector = (
        runtime.record_installed_mutations,
        node._process,
        runtime._materials,
    )
    attempts: list[str] = []

    def no_execution(*args, **kwargs):
        attempts.append("record-or-probe")
        raise AssertionError("portable logic fixture must not record or launch a probe")

    actual_popen = subprocess.Popen

    class GitOnlyPopen(actual_popen):
        # Keep Popen a class: Windows asyncio subclasses it during cold imports.
        def __init__(self, argv, *args, **kwargs):
            if not isinstance(argv, (tuple, list)) or Path(argv[0]).name.casefold() not in {
                "git",
                "git.exe",
            }:
                no_execution(argv)
            super().__init__(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", GitOnlyPopen)
    monkeypatch.setattr(runtime, "record_installed_mutations", no_execution)
    for name in OS_PROCESS_APIS:
        if hasattr(os, name):
            monkeypatch.setattr(os, name, no_execution)
    for module, names in (
        (node, ("run_node_process", "_process")),
        (processes, ("run_node_process", "run_execution")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, no_execution)
    root = tmp_path / "task"
    root.mkdir()
    for name in ("policy", "schemas", "templates"):
        shutil.copytree(ROOT / ".ai" / name, root / ".ai" / name)
    if getattr(request, "param", None) == "node-v2":
        import yaml
        from test_node_v2_contract import node_documents

        for name, document in node_documents().items():
            (root / ".ai/policy" / name).write_text(
                yaml.safe_dump(document, sort_keys=False), encoding="utf8"
            )
    (root / ".ai/repository-id").write_text(str(uuid4()) + "\n", encoding="utf8")
    (root / "fixture.py").write_text("value = 1\n", encoding="utf8")
    (root / ".gitignore").write_text(".ai/tasks/*/logs/\n__pycache__/\n", encoding="utf8")
    fixture_git(root, "init", "-b", "fixture")
    fixture_git(root, "config", "user.name", "Public Fixture")
    fixture_git(root, "config", "user.email", "fixture@example.invalid")
    fixture_git(root, "add", ".")
    fixture_git(root, "commit", "-m", "public synthetic fixture")
    assert (
        start_task(
            root,
            objective="Closed transaction model",
            allowed_scope=["fixture.py"],
            forbidden_actions=["push", "deploy"],
        ).task_id
        == TASK
    )
    facts = dict(
        impact_categories=[],
        controlled_actions=[],
        permission_requirements=["action_approval"],
        reversibility="reversible",
        business_direction_count=1,
        scope={"clear": True},
        impact={"level": "medium"},
        protections={"verified_backup": False, "dry_run": False},
        verification={"automatic": True, "tools_missing": False},
        change_characteristics=dict(
            mechanical=False,
            behavior_changed=True,
            code_modified=True,
            interaction_scope="cross_module",
            regression_risk=True,
            error_detectability="high",
        ),
        verification_requirements=dict(
            acceptance_required=True,
            integration_required=True,
            targeted_mutation_required=True,
            independent_verifier_required=True,
        ),
    )
    facts_path = tmp_path / "facts.json"
    put_json(facts_path, facts)
    record_risk_facts(
        root, TASK, decision_unit_id="DU-001", input_path=facts_path, actor="fixture-classifier"
    )
    spec = (
        "# Public fixture\n\n"
        + "\n\n".join(
            "## " + heading + "\n\nRun bounded fixture checks; retain synthetic originals."
            for heading in REQUIRED_SECTIONS.values()
        )
        + "\n"
    )
    resolve_task_path(root, TASK, "spec.md").write_text(spec, encoding="utf8")
    freeze_task(root, TASK, actor="fixture-specifier")
    classification = classify_task(root, TASK, actor="fixture-classifier")
    assert classification["effective_route"] == "REVIEW"
    assert classification["effective_verification_level"] == "V2"
    context = build_review_context(root, TASK, "design")
    record_review(
        root,
        TASK,
        actor="fixture-design-reviewer",
        input_path=dict(
            schema_version="1.0",
            review_id="REV-0001",
            review_stage="design",
            recorded_at=datetime.now(timezone.utc).isoformat(),
            context_sha256=context["context_sha256"],
            outcome="APPROVE",
            summary="Public synthetic fixture only",
            findings=[],
        ),
    )
    approve_task(root, TASK, approval_type="spec", actor="project-owner", reason="Fixture only")
    begin_task(root, TASK, actor="fixture-implementer")
    verifier_context = build_verifier_context(root, TASK)
    save_verifier_context(root, TASK, verifier_context)

    # The sole positive host seam: ordinary fixture files instead of Windows
    # interpreter/distribution discovery. No probe or process result is supplied.
    prefix, base = tmp_path / "engine", tmp_path / "base"
    site = prefix / "Lib/site-packages/aiflow"
    site.mkdir(parents=True)
    for name in (
        "__init__.py",
        "policy.py",
        "verifier_service.py",
        "approval.py",
        "gate.py",
        "evidence.py",
        "errors.py",
        "installed_probe.py",
        "installed_mutations.py",
    ):
        shutil.copyfile(ROOT / "src/aiflow" / name, site / name)
    (prefix / "Scripts").mkdir()
    base.mkdir()
    for path in (prefix / "Scripts/python.exe", base / "python.exe", base / "python311.dll"):
        path.write_bytes(b"public fixture, not an executable\n")
    interpreter = dict(
        executable=runtime._file(prefix / "Scripts/python.exe"),
        base_executable=runtime._file(base / "python.exe"),
        runtime=runtime._file(base / "python311.dll"),
        prefix=str(prefix),
        site=str(site.parent),
        base_prefix=str(base),
        implementation="cpython",
        version=[3, 11, 0],
        cache_tag="cpython-311",
    )
    material = dict(
        kind=runtime.ACTION_TYPE,
        version=1,
        engine={"installed": {}, "closure": node._inventory(prefix)},
        interpreter=interpreter,
        host_tools={},
        probes=runtime._probe_contract(),
        operators={},
    )
    monkeypatch.setattr(runtime, "_materials", lambda: node._canonical(material))
    monkeypatch.setattr(node, "_windows_root", lambda: tmp_path / "public-windows-role")
    inputs = runtime.prepare_installed_mutations(root, TASK, verifier_actor=ACTOR)
    yield Model(
        root, inputs, verifier_context, material, recorder, process_writer, material_collector
    )
    assert not attempts, "a caught launch attempt must not make a logical test pass"


def action_file(model: Model, *, approved: bool = True, suffix: str = "fixture") -> Path:
    action = dict(
        action_type=runtime.ACTION_TYPE,
        target=TASK,
        parameter_summary=runtime._summary(model.inputs),
        decision_unit_id="DU-001",
        classification_input_sha256=model.inputs.classification_input_sha256,
        subject_commit=model.inputs.subject_commit,
        conditions=["Synthetic fixture only", suffix],
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        single_use=True,
    )
    path = resolve_task_path(
        model.root, TASK, "action-installed-engine-mutation-" + suffix + ".json"
    )
    put_json(path, action)
    if approved:
        approve_task(
            model.root,
            TASK,
            approval_type="action",
            actor="project-owner",
            reason="Logical temporary fixture; never authorizes host execution",
            action_file=path,
        )
    return path


def test_prepare_uses_real_git_without_consumption_or_target_writes(model: Model) -> None:
    before = snapshot_tree(model.root)
    again = runtime.prepare_installed_mutations(model.root, TASK, verifier_actor=ACTOR)
    assert again.sha256 == model.inputs.sha256
    assert snapshot_tree(model.root) == before
    assert not list(resolve_task_path(model.root, TASK, "logs").glob("installed-action-*"))


@pytest.mark.parametrize("change", ["source", "actor", "state"])
def test_authority_rejects_drift_before_consumption(model: Model, change: str) -> None:
    actor = ACTOR
    if change == "source":
        (model.root / "fixture.py").write_text("value = 2\n", encoding="utf8")
    elif change == "actor":
        actor = "fixture-implementer"
    else:
        transition_task_record(
            model.root,
            TASK,
            target_state="VERIFYING",
            event_type="verification_started",
            actor=ACTOR,
            payload={},
            satisfied_preconditions={"implementation_complete"},
        )
    before = snapshot_tree(model.root)
    with pytest.raises(AiflowError):
        runtime.prepare_installed_mutations(model.root, TASK, verifier_actor=actor)
    assert snapshot_tree(model.root) == before


@pytest.mark.parametrize("unapproved", [False, True])
def test_missing_action_rejects_without_creating_receipt(model: Model, unapproved: bool) -> None:
    if unapproved:
        action_file(model, approved=False)
    before = snapshot_tree(model.root)
    with pytest.raises(AiflowError) as caught:
        runtime._select_action(model.root, model.inputs)
    assert caught.value.code == "ACTION_APPROVAL_REQUIRED"
    assert snapshot_tree(model.root) == before


def test_duplicate_current_approvals_are_ambiguous(model: Model) -> None:
    action_file(model, suffix="first")
    action_file(model, suffix="second")
    with pytest.raises(AiflowError) as caught:
        runtime._select_action(model.root, model.inputs)
    assert caught.value.code == "ACTION_APPROVAL_AMBIGUOUS"


def test_consumption_keeps_exact_originals_and_rejects_reuse(model: Model) -> None:
    action_file(model)
    ref = f".ai/tasks/{TASK}/logs/IMUT-{'0' * 16}"
    use = runtime._consume_action(model.root, model.inputs, ref)
    runtime._action_originals(model.root, model.inputs, use, model.root / ref)
    before = snapshot_tree(model.root)
    with pytest.raises(AiflowError) as caught:
        runtime._consume_action(model.root, model.inputs, ref)
    assert caught.value.code == "ACTION_APPROVAL_USED"
    assert snapshot_tree(model.root) == before


class Interrupted(BaseException):
    """Simulate loss of the transaction owner, without claiming process success."""


@pytest.mark.parametrize("point", ["event", "claim"])
def test_interrupted_reservation_cannot_be_reused(
    model: Model, monkeypatch: pytest.MonkeyPatch, point: str
) -> None:
    action_file(model)
    with monkeypatch.context() as patch:
        if point == "event":

            def stop_event(*args, **kwargs):
                raise Interrupted()

            patch.setattr(runtime, "record_task_event", stop_event)
        else:
            actual_write = node._write_new

            def stop_claim(path, data):
                if path.name.startswith("installed-action-launch-"):
                    raise Interrupted()
                return actual_write(path, data)

            patch.setattr(node, "_write_new", stop_claim)
        with pytest.raises(Interrupted):
            runtime._consume_action(
                model.root, model.inputs, f".ai/tasks/{TASK}/logs/IMUT-{'0' * 16}"
            )
    with pytest.raises(AiflowError) as caught:
        runtime._select_action(model.root, model.inputs)
    assert caught.value.code == "ACTION_APPROVAL_USED"
    assert (
        len(list(resolve_task_path(model.root, TASK, "logs").glob("installed-action-use-*"))) == 1
    )


def test_concurrent_reservations_have_one_owner(
    model: Model, monkeypatch: pytest.MonkeyPatch
) -> None:
    action_file(model)
    barrier, per_thread = Barrier(2), local()
    select = runtime._select_action

    def simultaneous_select(*args):
        value = select(*args)
        if not getattr(per_thread, "selected", False):
            per_thread.selected = True
            barrier.wait(timeout=15)
        return value

    monkeypatch.setattr(runtime, "_select_action", simultaneous_select)

    def reserve(index):
        try:
            return runtime._consume_action(
                model.root, model.inputs, f".ai/tasks/{TASK}/logs/IMUT-{index:016x}"
            )
        except AiflowError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(reserve, (1, 2)))
    assert sum(isinstance(value, dict) for value in outcomes) == 1
    assert "ACTION_APPROVAL_USED" in outcomes
    logs = resolve_task_path(model.root, TASK, "logs")
    assert len(list(logs.glob("installed-action-use-*"))) == 1
    assert len(list(logs.glob("installed-action-launch-*"))) == 1


@pytest.mark.parametrize("mode", ["not_started", "interrupted", "root_changed"])
def test_recorder_failure_retains_spent_action_without_any_probe_execution(
    model: Model, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    action_file(model)
    calls = []

    def rejected_job(argv, **kwargs):
        calls.append((argv, kwargs))
        assert argv[1:4] == ("-I", "-S", "-B")
        assert kwargs["timeout_seconds"] == 60
        assert kwargs["cwd"].name == "b"
        assert kwargs["environment"]["TMP"] == str(kwargs["cwd"] / "t")
        if mode == "interrupted":
            raise Interrupted()
        if mode == "root_changed":
            (model.root / "fixture.py").write_text("value = 9\n", encoding="utf8")
        return processes.NodeProcessResult(None, False, b"", b"", False, False, "not_started", True)

    monkeypatch.setattr(node, "_process", model.process_writer)
    monkeypatch.setattr(node, "run_node_process", rejected_job)
    arguments = dict(verifier_actor=ACTOR, expected_inputs_sha256=model.inputs.sha256)
    if mode == "interrupted":
        with pytest.raises(Interrupted):
            model.recorder(model.root, TASK, **arguments)
    else:
        reference = model.recorder(model.root, TASK, **arguments)
        document = node._json(model.root / reference.ref)
        completion = node._json(
            model.root / reference.ref.removesuffix("run.json") / "completion.json"
        )
        assert document["failure"] is not None
        assert completion["reference"] == asdict(reference)
        assert completion["failure"] == document["failure"]
        assert document["pairs"][0]["baseline"]["receipt"]["cleanup"] == "not_started"
        assert document["pairs"][0]["mutant"] is None
        assert all(pair["baseline"] is None for pair in document["pairs"][1:])
        if mode == "root_changed":
            assert document["failure"] == "INSTALLED_MUTATION_ROOT_CHANGED"
    assert len(calls) == 1
    assert read_task_yaml(model.root, TASK, "task.yaml")["current_state"] == "IMPLEMENTING"
    logs = resolve_task_path(model.root, TASK, "logs")
    assert len(list(logs.glob("installed-action-use-*"))) == 1
    assert len(list(logs.glob("installed-action-launch-*"))) == 1
    with pytest.raises(AiflowError):
        model.recorder(model.root, TASK, **arguments)
    assert len(calls) == 1, "a spent action reached the Job boundary a second time"


def test_recorder_rejects_stale_preparation_before_action_consumption(model: Model) -> None:
    action_file(model)
    before = snapshot_tree(model.root)
    with pytest.raises(AiflowError):
        model.recorder(model.root, TASK, verifier_actor=ACTOR, expected_inputs_sha256="0" * 64)
    assert snapshot_tree(model.root) == before


@pytest.mark.parametrize("probe_id", runtime.PROBE_IDS)
def test_stage_copies_and_fixed_overlay_stop_at_process_boundary(
    model: Model, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_id: str
) -> None:
    original = snapshot_tree(Path(model.materials["engine"]["closure"]["root"]))
    pair = dict(id=probe_id, overlay=None, baseline=None, mutant=None)
    calls = []

    def stop(argv, **kwargs):
        calls.append((argv, kwargs))
        raise Interrupted()

    monkeypatch.setattr(node, "_process", stop)
    for role in ("baseline", "mutant"):
        phase = tmp_path / role
        with pytest.raises(Interrupted):
            runtime._run_stage(
                phase,
                pair,
                role,
                probe_id,
                model.materials,
                [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES],
            )
        assert pair[role]["receipt"] is None
        assert pair[role]["cache"]["entries"] == []
        assert all(
            item["identity"]["nlink"] == 1
            for item in pair[role]["closure"]["entries"]
            if item["kind"] == "file"
        )
    filename = runtime._TARGETS[probe_id][0]
    relative = "Lib/site-packages/aiflow/" + filename
    before = (tmp_path / "baseline/i" / relative).read_bytes()
    changed = (tmp_path / "mutant/i" / relative).read_bytes()
    assert changed == runtime._transformed(probe_id, before) and changed != before
    assert pair["overlay"] == dict(
        path=relative, before_sha256=node._sha(before), after_sha256=node._sha(changed)
    )
    assert len(calls) == 2
    assert snapshot_tree(Path(model.materials["engine"]["closure"]["root"])) == original


@dataclass(frozen=True)
class LogicalRun:
    model: Model
    path: Path
    reference: runtime.InstalledMutationReference


@pytest.fixture
def logical_run(model: Model) -> LogicalRun:
    """A closed failure record with no probe reports and no claimed Job execution."""
    action_file(model)
    return retained_logical_run(model)


def retained_logical_run(model: Model) -> LogicalRun:
    run = resolve_task_path(model.root, TASK, "logs") / ("IMUT-" + "0" * 16)
    use = runtime._consume_action(model.root, model.inputs, run.relative_to(model.root).as_posix())
    run.mkdir()
    put_json(run / "context.json", model.context)
    for index in range(5):
        (run / str(index) / "b").mkdir(parents=True)
        (run / str(index) / "m").mkdir()
    snapshot = node._root_snapshot(model.root, TASK, run)
    document = dict(
        kind="installed-mutation-run-v1",
        version=1,
        inputs=runtime._input_document(model.inputs),
        action=use,
        before=snapshot,
        after=snapshot,
        pairs=[
            dict(id=probe, overlay=None, baseline=None, mutant=None) for probe in runtime.PROBE_IDS
        ],
        failure="FIXTURE_NO_EXECUTION",
    )
    reference = rewrite_run(run / "run.json", document, model.inputs)
    return LogicalRun(model, run / "run.json", reference)


def rewrite_run(path: Path, document: dict, inputs) -> runtime.InstalledMutationReference:
    raw = node._canonical(document)
    path.write_bytes(raw)
    reference = runtime.InstalledMutationReference(
        path.relative_to(path.parents[5]).as_posix(), len(raw), node._sha(raw)
    )
    # The root role is explicit rather than inferred from serialized content.
    assert reference.ref.startswith(".ai/tasks/")
    put_json(
        path.parent / "completion.json",
        dict(
            kind="installed-mutation-completion-v1",
            version=1,
            inputs_sha256=inputs.sha256,
            reference=asdict(reference),
            failure=document["failure"],
        ),
    )
    return reference


class ParserReached(BaseException):
    """Stop before any incomplete pair can be projected as executed or killed."""


def parser_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:
    def reached(*args, **kwargs):
        raise ParserReached()

    monkeypatch.setattr(runtime, "_pair_originals", reached)


def collect(run: LogicalRun, reference=None):
    return runtime.collect_installed_mutation_current(
        run.model.root, reference or run.reference, verifier_actor=ACTOR
    )


def test_current_is_typed_reference_bound_and_authority_is_read_only(
    logical_run: LogicalRun,
) -> None:
    before = snapshot_tree(logical_run.model.root)
    current = collect(logical_run)
    assert type(current) is runtime.InstalledMutationCurrent
    assert current.inputs.sha256 == logical_run.model.inputs.sha256
    assert current.reference == logical_run.reference
    assert type(current.root_snapshot) is bytes
    assert current.root_snapshot == node._canonical(node._json_bytes(current.root_snapshot))
    assert current.allowed_git_paths == tuple(sorted(set(current.allowed_git_paths)))
    assert snapshot_tree(logical_run.model.root) == before


def test_valid_logical_prefix_reaches_pair_parser_without_execution_or_write(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = collect(logical_run)
    parser_sentinel(monkeypatch)
    before = snapshot_tree(logical_run.model.root)
    with pure_guard(monkeypatch), pytest.raises(ParserReached):
        runtime.replay_installed_mutations(
            logical_run.model.root, logical_run.reference, current=current
        )
    assert snapshot_tree(logical_run.model.root) == before


def stage_node_v2_code_marker(run: LogicalRun, phase: str) -> dict:
    """Real ledger/files, synthetic public evidence; never authorize an execution."""
    from test_node_v2_evidence import public_node_evidence

    from aiflow.contracts import require_valid_contract
    from aiflow.evidence import verification_snapshot_sha256
    from aiflow.policy import load_policy_bundle
    from aiflow.review_service import _context_digest
    from aiflow.state import TRANSITIONS, create_transition_event
    from aiflow.task_service import _persist_event_and_task, read_task_record_strict

    root = run.model.root
    directory = resolve_task_path(root, TASK)
    # These synthetic state transitions model a stopped approval transaction;
    # neither they nor the structural evidence substitute for runtime acceptance.
    for target in ("VERIFYING", "VERIFIED", "WAITING_FOR_FINAL_REVIEW"):
        record = read_task_record_strict(root, TASK)
        rule = TRANSITIONS[(record.task["current_state"], target)]
        transition_task_record(
            root,
            TASK,
            target_state=target,
            event_type=rule.event_type,
            actor=ACTOR,
            payload={},
            satisfied_preconditions=rule.preconditions,
        )
    record = read_task_record_strict(root, TASK)
    classification = node._json(directory / "classification.json")
    policy_sha = load_policy_bundle(root).sha256
    evidence = public_node_evidence(root)
    for key in ("repository_id", "branch", "base_commit", "subject_commit"):
        evidence[key] = record.task[key]
    evidence["spec_sha256"] = record.task["frozen_spec_sha256"]
    evidence["classification_input_sha256"] = classification["classification_input_sha256"]
    evidence["verifier_actor"] = ACTOR
    evidence["verifier_context_sha256"] = run.model.inputs.verifier_context_sha256
    evidence["reproduce_command"][6] = ACTOR
    design = node._json(directory / "reviews/REV-0001-r0001.json")
    evidence["review_refs"]["design"] = {
        key: design[key] for key in ("review_id", "context_sha256")
    }
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    context = {
        "schema_version": "2.0",
        "review_stage": "implementation",
        "task_id": TASK,
        "decision_unit_ids": ["DU-001"],
        **{
            key: record.task[key]
            for key in ("repository_id", "branch", "base_commit", "subject_commit")
        },
        "spec_sha256": record.task["frozen_spec_sha256"],
        "policy_sha256": policy_sha,
        "classification_input_sha256": classification["classification_input_sha256"],
        "verification_snapshot_sha256": evidence["verification_snapshot_sha256"],
        "content": {},
    }
    context["context_sha256"] = _context_digest(context)
    review = {
        "schema_version": "1.0",
        "review_id": "REV-0002",
        "revision": 1,
        "task_id": TASK,
        "review_stage": "implementation",
        "reviewer": "fixture-code-reviewer",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "context_sha256": context["context_sha256"],
        "outcome": "APPROVE",
        "summary": "Synthetic interrupted transaction only",
        "findings": [],
    }
    require_valid_contract("review-context", context)
    require_valid_contract("review-record", review)
    put_json(directory / f"review-contexts/{context['context_sha256']}.json", context)
    put_json(directory / "reviews/REV-0002-r0001.json", review)
    reference = {
        key: review[key] for key in ("review_id", "revision", "review_stage", "context_sha256")
    }
    record_task_event(
        root, TASK, event_type="review_recorded", actor=review["reviewer"], payload=reference
    )
    evidence["review_refs"]["implementation"] = {
        key: review[key] for key in ("review_id", "context_sha256")
    }
    require_valid_contract("evidence", evidence)
    put_json(directory / "evidence.json", evidence)
    approvals = node._json(directory / "approvals.json")
    record = read_task_record_strict(root, TASK)
    instant = datetime.now(timezone.utc).isoformat()
    candidate = {
        **approvals[0],
        "approval_type": "code",
        "approved_at": instant,
        "reason": "Logical staged transaction; no host execution claim",
        "evidence_sha256": node._sha(node._canonical(evidence)),
    }
    event = create_transition_event(
        record.task,
        target_state="APPROVED_FOR_MERGE",
        event_type="code_approved",
        actor="project-owner",
        payload={"approval_type": "code", "approvals": [candidate], "structured_review": reference},
        sequence=len(record.events) + 1,
        satisfied_preconditions={"code_approval_valid"},
        occurred_at=instant,
    )
    marker = {
        "schema_version": "1.0",
        "task_id": TASK,
        "task": {**record.task, "current_state": "APPROVED_FOR_MERGE", "updated_at": instant},
        "event": event,
        "approvals": [*approvals, candidate],
    }
    put_json(directory / "approval_pending.json", marker)
    if phase in {"ledger_written", "event_applied"}:
        put_json(directory / "approvals.json", marker["approvals"])
    if phase == "event_applied":
        _persist_event_and_task(directory, marker["task"], event)
    return marker


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize("phase", ["pending", "ledger_written", "event_applied"])
def test_node_v2_real_current_replays_each_valid_code_transaction_phase_without_writes(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    stage_node_v2_code_marker(logical_run, phase)
    before = snapshot_tree(logical_run.model.root)
    current = collect(logical_run)
    assert (
        f".ai/tasks/{TASK}/approval_pending.json"
        in node._json_bytes(current.root_snapshot)["governance"]["paths"]
    )
    parser_sentinel(monkeypatch)
    with pure_guard(monkeypatch), pytest.raises(ParserReached):
        runtime.replay_installed_mutations(
            logical_run.model.root, logical_run.reference, current=current
        )
    assert snapshot_tree(logical_run.model.root) == before


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize("role", ["before", "after"])
def test_node_v2_live_pending_exception_cannot_validate_a_forged_historical_role(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    stage_node_v2_code_marker(logical_run, "ledger_written")
    current = collect(logical_run)
    live = node._json_bytes(current.root_snapshot)
    # The actual live approval inventory is ahead of its event inventory. It is
    # valid only as Current, even when historical.events exactly equals live.
    assert (
        runtime._snapshot(live, logical_run.model.root, logical_run.model.inputs, current=True)
        == live
    )
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        runtime._snapshot(live, logical_run.model.root, logical_run.model.inputs)
    document = node._json(logical_run.path)
    document[role] = deepcopy(live)
    reference = rewrite_run(logical_run.path, document, logical_run.model.inputs)
    before = snapshot_tree(logical_run.model.root)
    with pytest.raises(AiflowError):
        collect(logical_run, reference)
    parser_sentinel(monkeypatch)
    with pure_guard(monkeypatch):
        facts = runtime.replay_installed_mutations(
            logical_run.model.root, reference, current=replace(current, reference=reference)
        )
    assert not facts.current and not facts.passed and facts.reason_codes
    assert snapshot_tree(logical_run.model.root) == before


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize("finalize", [False, True])
def test_node_v2_public_service_rejects_implementer_before_claim_or_execution(
    model: Model, monkeypatch: pytest.MonkeyPatch, finalize: bool
) -> None:
    import aiflow.verification_service as service
    from aiflow.verifier_service import validate_verifier_actor

    observed, attempts = [], []

    def actor_guard(implementer, verifier):
        observed.append((implementer, verifier))
        return validate_verifier_actor(implementer, verifier)

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("The implementer reached claim, transition or execution")

    monkeypatch.setattr(service, "validate_verifier_actor", actor_guard)
    # Host provenance and Git assessment are separate contracts. The actor
    # decision must still be the real production validator reached via verify.
    monkeypatch.setattr(node, "precheck_node_materials", lambda *_: None)
    monkeypatch.setattr(service, "_ci_git_assessment", lambda *_: None)
    monkeypatch.setattr(service, "_start_local_verification", forbidden)
    monkeypatch.setattr(node, "claim_node_v2_run", forbidden)
    monkeypatch.setattr(node, "execute_node_verification", forbidden)
    before = snapshot_tree(model.root)
    options = (
        {"finalize": True}
        if finalize
        else {
            "node_materials_sha256": "a" * 64,
            "node_installed_mutation_run": "IMUT-0123456789abcdef",
        }
    )
    with pytest.raises(AiflowError) as caught:
        service.verify_task(model.root, TASK, actor="fixture-implementer", **options)
    assert caught.value.code == "VERIFIER_ACTOR_NOT_INDEPENDENT"
    assert observed == [("fixture-implementer", "fixture-implementer")]
    assert attempts == []
    assert snapshot_tree(model.root) == before


def test_preparation_inputs_cannot_stand_in_for_typed_current(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser_sentinel(monkeypatch)
    with pure_guard(monkeypatch):
        facts = runtime.replay_installed_mutations(
            logical_run.model.root, logical_run.reference, current=logical_run.model.inputs
        )
    assert not facts.current and not facts.passed and facts.reason_codes


@pytest.mark.parametrize("change", ["path", "size", "digest"])
def test_current_cannot_be_reused_for_another_reference(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    current = collect(logical_run)
    wrong = replace(
        logical_run.reference,
        **{
            "path": {"ref": logical_run.reference.ref.replace("IMUT-000", "IMUT-100")},
            "size": {"size": logical_run.reference.size + 1},
            "digest": {"sha256": "f" * 64},
        }[change],
    )
    parser_sentinel(monkeypatch)
    with pure_guard(monkeypatch):
        facts = runtime.replay_installed_mutations(logical_run.model.root, wrong, current=current)
    assert not facts.current and not facts.passed and facts.reason_codes


@pytest.mark.parametrize("key", ["files", "metadata"])
def test_self_rehashed_missing_inventory_is_rejected_before_pair_parser(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    parser_sentinel(monkeypatch)
    original = collect(logical_run)
    with pure_guard(monkeypatch), pytest.raises(ParserReached):
        runtime.replay_installed_mutations(
            logical_run.model.root, logical_run.reference, current=original
        )
    document = node._json(logical_run.path)
    assert document["before"][key]
    document["before"][key] = document["after"][key] = []
    reference = rewrite_run(logical_run.path, document, logical_run.model.inputs)
    try:
        current = collect(logical_run, reference)
    except AiflowError:
        return  # The live collector may reject the incomplete historical inventory.
    with pure_guard(monkeypatch):
        facts = runtime.replay_installed_mutations(
            logical_run.model.root, reference, current=current
        )
    assert not facts.current and not facts.passed and facts.reason_codes


def test_collector_accepts_registered_state_advancement_with_stable_inputs(
    logical_run: LogicalRun,
) -> None:
    model = logical_run.model
    transition_task_record(
        model.root,
        TASK,
        target_state="VERIFYING",
        event_type="verification_started",
        actor=ACTOR,
        payload={},
        satisfied_preconditions={"implementation_complete"},
    )
    current = collect(logical_run)
    assert read_task_yaml(model.root, TASK, "task.yaml")["current_state"] == "VERIFYING"
    assert current.inputs.sha256 == model.inputs.sha256


def test_collector_accepts_registered_governance_only_commit(logical_run: LogicalRun) -> None:
    model = logical_run.model
    approve_task(
        model.root,
        TASK,
        approval_type="action",
        actor="project-owner",
        reason="Append-only fixture approval; never grants host execution",
        action_file=resolve_task_path(
            model.root, TASK, "action-installed-engine-mutation-fixture.json"
        ),
    )
    prefix = f".ai/tasks/{TASK}/"
    fixture_git(
        model.root, "add", prefix + "approvals.json", prefix + "events.jsonl", prefix + "task.yaml"
    )
    fixture_git(model.root, "commit", "-m", "append fixture governance only")
    current = collect(logical_run)
    assert current.inputs.sha256 == model.inputs.sha256
    assert current.allowed_git_paths


@pytest.mark.parametrize("drift", ["tracked", "ignored", "unregistered_governance", "history"])
def test_collector_rejects_complete_root_or_history_drift(
    logical_run: LogicalRun, drift: str
) -> None:
    model = logical_run.model
    if drift == "tracked":
        (model.root / "fixture.py").write_text("value = 2\n", encoding="utf8")
    elif drift == "ignored":
        (model.root / "__pycache__").mkdir()
        (model.root / "__pycache__/unbound.pyc").write_bytes(b"unbound")
    elif drift == "unregistered_governance":
        resolve_task_path(model.root, TASK, "unregistered.json").write_bytes(b"{}")
    else:
        reflog = model.root / ".git/logs/HEAD"
        history = reflog.read_bytes()
        assert history.endswith(b"\n")
        reflog.write_bytes(history[:-1])
    before = snapshot_tree(model.root)
    with pytest.raises(AiflowError):
        collect(logical_run)
    assert snapshot_tree(model.root) == before


@pytest.mark.parametrize(
    "fault",
    [
        "head_argument",
        "tree_argument",
        "index_digest",
        "git_parent_escape",
        "foreign_git_role",
        "branch_ref_escape",
        "reflog_digest",
        "protected_path_escape",
        "protected_digest",
        "protected_boolean_size",
        "identity_type",
        "foreign_metadata",
        "metadata_alias",
        "immutable_inventory",
        "approval_prefix",
        "approval_inventory_shortened",
        "consume_digest",
        "consume_prefix",
    ],
)
def test_self_rehashed_historical_bindings_reject_before_untrusted_git_use(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    document = node._json(logical_run.path)
    sentinel = "--untrusted-historical-argument"
    for snapshot in (document["before"], document["after"]):
        if fault == "head_argument":
            snapshot["git"]["head"] = sentinel
        elif fault == "tree_argument":
            snapshot["git"]["tree"] = sentinel
        elif fault == "index_digest":
            snapshot["git"]["index_sha256"] = "A" * 64
        elif fault == "git_parent_escape":
            snapshot["git"]["git_directory"] += "/../foreign.git"
        elif fault == "foreign_git_role":
            snapshot["git_audit"]["git"] = str(logical_run.model.root.parent / "foreign.git")
        elif fault == "branch_ref_escape":
            snapshot["git_audit"]["ref"] = "refs/heads/../../foreign"
        elif fault == "reflog_digest":
            next(iter(snapshot["git_audit"]["logs"].values()))["sha256"] = "not-a-digest"
        elif fault == "protected_path_escape":
            snapshot["files"][0]["path"] = "../foreign.py"
        elif fault == "protected_digest":
            snapshot["files"][0]["sha256"] = "not-a-digest"
        elif fault == "protected_boolean_size":
            snapshot["files"][0]["size"] = True
        elif fault == "identity_type":
            snapshot["identity"]["inode"] = True
        elif fault == "foreign_metadata":
            snapshot["metadata"][0]["path"] = str(logical_run.model.root.parent / "foreign.py")
        elif fault == "metadata_alias":
            snapshot["metadata"].append(deepcopy(snapshot["metadata"][0]))
        elif fault == "immutable_inventory":
            assert snapshot["governance"]["immutable"]
            snapshot["governance"]["immutable"] = {}
        elif fault == "approval_prefix":
            snapshot["governance"]["approvals"][0]["reason"] = "rewritten historical approval"
        elif fault == "approval_inventory_shortened":
            assert snapshot["governance"]["approvals"]
            snapshot["governance"]["approvals"] = []
        elif fault == "consume_digest":
            snapshot["events"][-1]["payload"]["action_sha256"] = "0" * 64
        else:
            snapshot["events"].pop()
    reference = rewrite_run(logical_run.path, document, logical_run.model.inputs)
    actual_git, unsafe = node._git, []

    def checked_git(root, *arguments):
        if any(sentinel in value for value in arguments):
            unsafe.append(arguments)
            raise AssertionError("historical command data reached Git before validation")
        return actual_git(root, *arguments)

    monkeypatch.setattr(node, "_git", checked_git)
    before = snapshot_tree(logical_run.model.root)
    with pytest.raises(AiflowError):
        collect(logical_run, reference)
    assert not unsafe
    assert snapshot_tree(logical_run.model.root) == before


def test_retried_approval_identity_keeps_first_seen_ledger_record(
    model: Model, monkeypatch: pytest.MonkeyPatch
) -> None:
    action_file(model)
    approvals = node._json(resolve_task_path(model.root, TASK, "approvals.json"))
    first = deepcopy(approvals[-1])
    duplicate = {**first, "approved_at": "2000-01-01T00:00:00Z"}
    assert duplicate != first
    record_task_event(
        model.root,
        TASK,
        event_type="approval_recorded",
        actor=first["actor"],
        payload={"approval_type": "action", "approvals": [duplicate]},
    )
    run = retained_logical_run(model)
    document = node._json(run.path)
    assert document["before"]["governance"]["approvals"][-1] == first
    current = collect(run)
    parser_sentinel(monkeypatch)
    with pure_guard(monkeypatch), pytest.raises(ParserReached):
        runtime.replay_installed_mutations(model.root, run.reference, current=current)


@pytest.mark.parametrize(
    "fault",
    [
        "snapshot_protocol",
        "noncanonical_snapshot",
        "git_directory_allowance",
        "foreign_allowance",
        "duplicate_allowance",
        "post_collection_bytes",
        "post_collection_metadata",
        "post_collection_history",
    ],
)
def test_pure_reader_rejects_changed_authority_or_current_files_without_git_or_writes(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    current = collect(logical_run)
    root = logical_run.model.root
    if fault == "snapshot_protocol":
        current = replace(current, root_snapshot=b"{}")
    elif fault == "noncanonical_snapshot":
        current = replace(current, root_snapshot=current.root_snapshot + b"\n")
    elif fault == "git_directory_allowance":
        current = replace(current, allowed_git_paths=(str(root / ".git/objects"),))
    elif fault == "foreign_allowance":
        current = replace(current, allowed_git_paths=(str(root / "fixture.py"),))
    elif fault == "duplicate_allowance":
        current = replace(current, allowed_git_paths=(str(root / ".git/index"),) * 2)
    elif fault == "post_collection_bytes":
        (root / "fixture.py").write_bytes(b"value = 2\n")
    elif fault == "post_collection_metadata":
        (root / "__pycache__").mkdir()
    else:
        transition_task_record(
            root,
            TASK,
            target_state="VERIFYING",
            event_type="verification_started",
            actor=ACTOR,
            payload={},
            satisfied_preconditions={"implementation_complete"},
        )
    parser_sentinel(monkeypatch)
    before = snapshot_tree(root)
    with pure_guard(monkeypatch):
        facts = runtime.replay_installed_mutations(root, logical_run.reference, current=current)
    assert not facts.current and not facts.passed and facts.reason_codes
    assert snapshot_tree(root) == before


@dataclass(frozen=True)
class PhaseFixture:
    phase: Path
    stage: dict
    materials: dict
    report: dict


@pytest.fixture
def phase_fixture(model: Model, tmp_path: Path) -> PhaseFixture:
    """Exact parser input files, not an assertion that their synthetic Job ran."""
    return parser_phase(model, tmp_path / "parser-phase", PROBE)


def parser_phase(
    model: Model, phase: Path, probe_id: str, *, stage=None, mutant=False
) -> PhaseFixture:
    if stage is None:
        phase.mkdir()
        closure = node._copy_tree(
            Path(model.materials["engine"]["closure"]["root"]),
            phase / "i",
            model.materials["engine"]["closure"],
        )
        for name in ("c", "t", "h"):
            (phase / name).mkdir()
        stage = dict(closure=closure, cache=node._inventory(phase / "c"), receipt=None)
    closure = stage["closure"]
    (phase / "raw").mkdir()
    report = dict(
        protocol="installed-probe-v1",
        probe_id=probe_id,
        terminal="complete",
        cases=[
            dict(
                id=case_id,
                setup="passed",
                call="passed",
                teardown="passed",
                observed=observation,
                exception=None,
            )
            for case_id, observation in model.materials["probes"]["cases"][probe_id]
        ],
    )
    if mutant:
        anchor = model.materials["probes"]["anchors"][probe_id]
        report["cases"][-1].update(
            call="failed",
            observed=model.materials["probes"]["mutant_observations"][probe_id],
            exception=dict(
                type="AssertionError",
                message="synthetic classifier input only",
                frames=[
                    dict(
                        path=str(phase / "i/Lib/site-packages/aiflow/installed_probe.py"),
                        line=anchor["line"],
                        function=anchor["function"],
                    )
                ],
            ),
        )
    files = {
        item["path"].removeprefix("Lib/site-packages/"): item
        for item in closure["entries"]
        if item["kind"] == "file"
    }
    loaded = []
    target = runtime._TARGETS[probe_id][0].removesuffix(".py")
    for name, relative in sorted(
        (
            ("aiflow", "aiflow/__init__.py"),
            ("aiflow.installed_probe", "aiflow/installed_probe.py"),
            ("aiflow." + target, "aiflow/" + target + ".py"),
        )
    ):
        row = files[relative]
        loaded.append(dict(name=name, path=relative, size=row["size"], sha256=row["sha256"]))
    interpreter = model.materials["interpreter"]
    outer = dict(
        kind="installed-probe-execution-v1",
        probe=report,
        loaded=loaded,
        interpreter=dict(
            executable=interpreter["executable"]["path"],
            base_executable=interpreter["base_executable"]["path"],
            base_prefix=interpreter["base_prefix"],
            implementation="cpython",
            version=[3, 11, 0],
            cache_tag="cpython-311",
            isolated=1,
            no_site=1,
            optimize=0,
            dont_write_bytecode=True,
            debug=True,
            cache_prefix=str(phase / "c"),
        ),
    )
    job = dict(
        process_id=100,
        creation_time_filetime=100,
        created_suspended=True,
        assigned=True,
        initial_membership=True,
        resumed=True,
        job_empty=True,
        stdout_eof=True,
        stderr_eof=True,
        terminate_requested=False,
        closed=True,
    )
    raw = node._canonical(outer) + b"\n"
    receipt = dict(
        returncode=int(mutant),
        timed_out=False,
        stdout_overflow=False,
        stderr_overflow=False,
        cleanup="confirmed",
        execution_error=False,
        receipt=job,
        stdout_sha256=node._sha(raw),
        stderr_sha256=node._sha(b""),
        stdout_size=len(raw),
        stderr_size=0,
        argv=list(runtime._argv(phase, probe_id, model.materials)),
        cwd=str(phase),
        environment_sha256=node._sha(node._canonical(runtime._environment(phase, interpreter))),
        timeout_seconds=60,
        duration_ms=1,
    )
    stage["receipt"] = receipt
    (phase / "raw/stdout.raw").write_bytes(raw)
    (phase / "raw/stdout.log").write_bytes(raw)
    (phase / "raw/stderr.raw").write_bytes(b"")
    (phase / "raw/stderr.log").write_bytes(b"")
    put_json(phase / "raw/receipt.json", receipt)
    put_json(phase / "report.json", outer)
    return PhaseFixture(phase, stage, model.materials, report)


def test_closed_report_parser_reads_valid_synthetic_protocol_without_side_effects(
    phase_fixture: PhaseFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = phase_fixture
    before = snapshot_tree(fixture.phase)
    with pure_guard(monkeypatch):
        report = runtime._envelope(fixture.phase, fixture.stage, PROBE, fixture.materials)
    assert report == fixture.report
    assert snapshot_tree(fixture.phase) == before


@pytest.mark.parametrize("role", ["i", "c"])
def test_closed_parser_rejects_root_change_after_parent_identity_sample(
    phase_fixture: PhaseFixture, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    fixture = phase_fixture
    before = snapshot_tree(fixture.phase)
    root = fixture.phase / role
    actual_lstat = Path.lstat
    sampled = False

    def changing_root(path: Path, *args, **kwargs):
        nonlocal sampled
        info = actual_lstat(path, *args, **kwargs)
        if path != root:
            return info
        if not sampled:
            # The parent inventory captures the original identity first.
            sampled = True
            return info
        # Model one later stable metadata change without writing in pure_guard.
        changed = SimpleNamespace(
            **{name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
        )
        changed.st_mtime_ns += 1
        return changed

    with monkeypatch.context() as patch:
        patch.setattr(Path, "lstat", changing_root)
        with pure_guard(monkeypatch), pytest.raises(AiflowError):
            runtime._envelope(fixture.phase, fixture.stage, PROBE, fixture.materials)
    assert sampled, "the root identity fault was not reached"
    assert snapshot_tree(fixture.phase) == before


def test_retained_parser_never_queries_unavailable_producing_filesystem(
    phase_fixture: PhaseFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = phase_fixture
    phase = fixture.phase
    producing = tmp_path / "unavailable-producing-phase"
    assert not producing.exists()
    stage = deepcopy(fixture.stage)
    stage["closure"]["root"] = str(producing / "i")
    stage["cache"]["root"] = str(producing / "c")
    environment = runtime._environment(producing, fixture.materials["interpreter"])
    outer = node._json(phase / "report.json")
    outer["interpreter"]["cache_prefix"] = str(producing / "c")
    raw = node._canonical(outer) + b"\n"
    receipt = stage["receipt"]
    receipt.update(
        argv=list(runtime._argv(producing, PROBE, fixture.materials)),
        cwd=str(producing),
        environment_sha256=node._sha(node._canonical(environment)),
        stdout_sha256=node._sha(raw),
        stdout_size=len(raw),
    )
    # These are still synthetic parser inputs, never a relocated Job execution.
    put_json(phase / "report.json", outer)
    for name in ("stdout.raw", "stdout.log"):
        (phase / "raw" / name).write_bytes(raw)
    put_json(phase / "raw/receipt.json", receipt)
    retained = node._inventory(phase)
    retained["root"] = str(producing)
    before = snapshot_tree(phase)
    attempts = []

    def only_transported(operation):
        def checked(path: Path, *args, **kwargs):
            if path == producing or path.is_relative_to(producing):
                attempts.append(str(path))
                raise AssertionError("retained parser queried a producing coordinate")
            return operation(path, *args, **kwargs)

        return checked

    # Include all metadata and payload entry points used by the real parser.
    with monkeypatch.context() as patch:
        for name in ("lstat", "stat", "open"):
            patch.setattr(Path, name, only_transported(getattr(Path, name)))
        with pure_guard(monkeypatch):
            report = runtime._envelope(
                phase,
                stage,
                PROBE,
                fixture.materials,
                producing_phase=producing,
                retained_inventory=retained,
                environment=environment,
            )
    assert report == fixture.report
    assert runtime._baseline_passes(report, PROBE, fixture.materials)
    assert not attempts, "the reader caught a producing-path query instead of avoiding it"
    assert snapshot_tree(phase) == before
    assert not producing.exists()


def make_parser_pair(
    model: Model, run: Path, probe_id: str, monkeypatch: pytest.MonkeyPatch, *, index=0
) -> dict:
    """Stop real copy/AST logic before execution, then write synthetic protocol inputs."""
    (run / str(index)).mkdir(parents=True, exist_ok=True)
    pair = dict(id=probe_id, overlay=None, baseline=None, mutant=None)

    def stop(*args, **kwargs):
        raise Interrupted()

    with monkeypatch.context() as patch:
        patch.setattr(node, "_process", stop)
        for role, name in (("baseline", "b"), ("mutant", "m")):
            phase = run / str(index) / name
            if phase.exists():
                assert not any(phase.iterdir()), "only the fixture-created empty role is reusable"
                phase.rmdir()
            with pytest.raises(Interrupted):
                runtime._run_stage(
                    phase,
                    pair,
                    role,
                    probe_id,
                    model.materials,
                    [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES],
                )
            parser_phase(model, phase, probe_id, stage=pair[role], mutant=role == "mutant")
    return pair


@pytest.mark.parametrize("failure", ["FIXTURE_NO_EXECUTION", "invalid failure marker"])
def test_synthetic_logical_failure_cannot_become_execution_pass(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    model = logical_run.model
    document = node._json(logical_run.path)
    document["pairs"] = [
        make_parser_pair(model, logical_run.path.parent, probe_id, monkeypatch, index=index)
        for index, probe_id in enumerate(runtime.PROBE_IDS)
    ]
    document["failure"] = failure
    reference = rewrite_run(logical_run.path, document, model.inputs)
    try:
        current = collect(logical_run, reference)
    except AiflowError:
        assert failure != "FIXTURE_NO_EXECUTION"
        return
    with pure_guard(monkeypatch):
        facts = runtime.replay_installed_mutations(model.root, reference, current=current)
    assert not facts.passed and not facts.all_killed
    assert facts.current is (failure == "FIXTURE_NO_EXECUTION")
    if facts.current:
        assert list(facts.results) == [(probe, "killed") for probe in runtime.PROBE_IDS]
    # These are synthetic parser inputs with an explicit failure marker. Their
    # complete pair classifications must still never become execution evidence.


@pytest.mark.parametrize("probe_id", runtime.PROBE_IDS)
def test_synthetic_pair_protocol_binds_real_fixed_overlay_without_claiming_execution(
    model: Model, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe_id: str
) -> None:
    run = tmp_path / "synthetic-parser-run"
    pair = make_parser_pair(model, run, probe_id, monkeypatch)
    before = snapshot_tree(run)
    with pure_guard(monkeypatch):
        outcome = runtime._pair_originals(run, 0, pair, probe_id, model.materials)
    assert outcome == "killed", "synthetic classifier input did not match its fixed assertion"
    assert snapshot_tree(run) == before
    # There is intentionally no InstalledMutationFacts.passed assertion: the
    # synthetic Job receipts establish parser behavior, never execution evidence.


@pytest.mark.parametrize(
    "fault", ["overlay", "role", "baseline_bytes", "extra_mutant_change", "shared_identity"]
)
def test_pair_parser_rejects_bound_copy_or_overlay_substitution(
    model: Model, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    run = tmp_path / "synthetic-parser-run"
    pair = make_parser_pair(model, run, PROBE, monkeypatch)
    if fault == "overlay":
        pair["overlay"]["after_sha256"] = "0" * 64
    elif fault == "role":
        pair["mutant"]["closure"]["root"] = pair["baseline"]["closure"]["root"]
    elif fault in {"baseline_bytes", "extra_mutant_change"}:
        name, role = ("b", "baseline") if fault == "baseline_bytes" else ("m", "mutant")
        prefix = run / "0" / name / "i"
        (prefix / "Lib/site-packages/aiflow/errors.py").write_bytes(b"unrelated = True\n")
        pair[role]["closure"] = node._inventory(prefix)
    else:
        original = next(
            item
            for item in model.materials["engine"]["closure"]["entries"]
            if item["kind"] == "file"
        )
        row = next(
            item
            for item in pair["baseline"]["closure"]["entries"]
            if item["path"] == original["path"]
        )
        row["identity"] = original["identity"]
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        runtime._pair_originals(run, 0, pair, PROBE, model.materials)


def test_failed_positive_control_in_synthetic_pair_is_unverified(
    model: Model, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = tmp_path / "synthetic-parser-run"
    pair = make_parser_pair(model, run, PROBE, monkeypatch)
    phase = run / "0/b"
    outer = node._json(phase / "report.json")
    outer["probe"]["cases"][0]["observed"] = {"unrelated": True}
    data = node._canonical(outer) + b"\n"
    put_json(phase / "report.json", outer)
    (phase / "raw/stdout.raw").write_bytes(data)
    (phase / "raw/stdout.log").write_bytes(data)
    pair["baseline"]["receipt"].update(stdout_size=len(data), stdout_sha256=node._sha(data))
    put_json(phase / "raw/receipt.json", pair["baseline"]["receipt"])
    with pure_guard(monkeypatch):
        assert runtime._pair_originals(run, 0, pair, PROBE, model.materials) == "unverified"


def interpreter_layout(model: Model, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Model the host-layout parser with ordinary data files, never run them."""
    interpreter = model.materials["interpreter"]
    facts = dict(
        prefix=interpreter["prefix"],
        base_prefix=interpreter["base_prefix"],
        executable=interpreter["executable"]["path"],
        _base_executable=interpreter["base_executable"]["path"],
        implementation=SimpleNamespace(name="cpython", cache_tag="cpython-311"),
        version_info=(3, 11, 0),
        dont_write_bytecode=True,
        flags=SimpleNamespace(isolated=0),
    )
    monkeypatch.setattr(runtime, "sys", SimpleNamespace(**facts))
    monkeypatch.setattr(runtime, "os", SimpleNamespace(name="nt"))
    return facts


def test_supported_layout_parser_binds_all_interpreter_file_bytes(
    model: Model, monkeypatch: pytest.MonkeyPatch
) -> None:
    interpreter_layout(model, monkeypatch)
    with pure_guard(monkeypatch):
        facts = runtime._interpreter()
    assert facts == model.materials["interpreter"]


@pytest.mark.parametrize(
    "fault", ["bytecode_enabled", "base_install", "wrong_executable", "wrong_version"]
)
def test_layout_parser_rejects_unsupported_or_write_enabled_parent(
    model: Model, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    facts = interpreter_layout(model, monkeypatch)
    if fault == "bytecode_enabled":
        facts["dont_write_bytecode"] = False
    elif fault == "base_install":
        facts["prefix"] = facts["base_prefix"]
    elif fault == "wrong_executable":
        facts["executable"] = facts["_base_executable"]
    else:
        facts["version_info"] = (3, 12, 0)
    monkeypatch.setattr(runtime, "sys", SimpleNamespace(**facts))
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        runtime._interpreter()


def test_material_collector_binds_copyable_distribution_and_fixed_probe_sources(
    model: Model, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import installed_probe

    # Equivalent JSON cannot introduce a second raw representation of the
    # material bytes bound by preparation and its single-use action digest.
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        runtime._input_document(replace(model.inputs, materials=model.inputs.materials + b"\n"))

    interpreter = model.materials["interpreter"]
    prefix = Path(interpreter["prefix"])
    files = [runtime._file(path) for path in prefix.rglob("*") if path.is_file()]
    installed = dict(
        distributions=[dict(files=files)], startup=dict(files=[], pyvenv_configuration=None)
    )
    monkeypatch.setattr(runtime, "_interpreter", lambda: interpreter)
    monkeypatch.setattr(
        runtime, "__file__", str(Path(interpreter["site"]) / "aiflow/installed_mutations.py")
    )
    monkeypatch.setattr(
        installed_probe, "__file__", str(Path(interpreter["site"]) / "aiflow/installed_probe.py")
    )
    monkeypatch.setattr(node, "_engine", lambda **kwargs: installed)
    monkeypatch.setattr(node, "_host_tools", lambda **kwargs: {})
    with pure_guard(monkeypatch):
        material = node._json_bytes(model.material_collector())
    assert material["engine"]["closure"] == runtime._closure(installed, prefix)
    assert material["probes"]["source"]["path"] == installed_probe.__file__
    assert material["operators"]["bootstrap_sha256"] == node._sha(runtime._BOOTSTRAP.encode())
    monkeypatch.setattr(runtime, "__file__", str(ROOT / "src/aiflow/installed_mutations.py"))
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        model.material_collector()


def test_distribution_closure_rejects_file_outside_bound_prefix(
    model: Model, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside.py"
    outside.write_bytes(b"unbound = True\n")
    installed = dict(
        distributions=[dict(files=[runtime._file(outside)])],
        startup=dict(files=[], pyvenv_configuration=None),
    )
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        runtime._closure(installed, Path(model.materials["interpreter"]["prefix"]))


BOOTSTRAP_MODULES = {
    "plain": "def plain():\n    return 'bound'\n",
    "contextmanager": "from contextlib import contextmanager\n"
    "def plain():\n    return 'bound'\n"
    "@contextmanager\ndef guard():\n    yield 'bound'\n",
    "wrong_plain_filename": "exec(compile(\"def guard():\\n    return 'foreign'\\n\","
    " 'foreign.py', 'exec'))\n",
    "forged_wrapped_plain": "def generator():\n    yield 'bound'\n"
    "exec(compile(\"def guard():\\n    return 'foreign'\\n\", 'foreign.py', 'exec'))\n"
    "guard.__wrapped__ = generator\n",
    "foreign_decorator": "from functools import wraps\n"
    "def generator():\n    yield 'bound'\n"
    "namespace={'__name__':'foreign_decorator','wraps':wraps}\n"
    "exec(compile('def decorate(func):\\n @wraps(func)\\n"
    " def helper(*args, **kwargs):\\n  return func(*args, **kwargs)\\n"
    " return helper\\n', 'foreign_decorator.py', 'exec'),namespace)\n"
    "guard=namespace['decorate'](generator)\n",
    "foreign_wrapper_globals": "import contextlib\nfrom types import FunctionType\n"
    "from functools import update_wrapper\n"
    "def generator():\n    yield 'bound'\n"
    "original=contextlib.contextmanager(generator)\n"
    "guard=FunctionType(original.__code__,dict(vars(contextlib)),closure=original.__closure__)\n"
    "update_wrapper(guard,generator)\n",
    "wrong_closure": "from contextlib import contextmanager\n"
    "@contextmanager\ndef guard():\n    yield 'bound'\n"
    "def other():\n    yield 'bound'\n"
    "guard.__wrapped__=other\n",
    "nongenerator_wrapped": "from contextlib import contextmanager\n"
    "@contextmanager\ndef guard():\n    return 'bound'\n",
    "wrong_wrapped_filename": "from contextlib import contextmanager\n"
    "exec(compile(\"def generator():\\n    yield 'foreign'\\n\",'foreign.py','exec'))\n"
    "guard=contextmanager(generator)\ndel generator\n",
    "empty_closure": "from contextlib import contextmanager\n"
    "@contextmanager\ndef guard():\n    yield 'bound'\n"
    "del guard.__closure__[0].cell_contents\n",
    "nonfunction_wrapped": "from contextlib import contextmanager\n"
    "@contextmanager\ndef guard():\n    yield 'bound'\n"
    "guard.__wrapped__=object()\n",
    "async_generator_wrapped": "from contextlib import contextmanager\n"
    "@contextmanager\nasync def guard():\n    yield 'bound'\n",
}


@pytest.mark.parametrize("case", tuple(BOOTSTRAP_MODULES))
def test_real_isolated_bootstrap_enforces_bound_function_origin_and_exact_wire(
    tmp_path: Path, case: str
) -> None:
    """A minimal synthetic package tests bootstrap, never ordinary pair acceptance."""
    site = tmp_path / "site"
    package = site / "aiflow"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf8")
    (package / "guards.py").write_text(BOOTSTRAP_MODULES[case], encoding="utf8")
    (package / "installed_probe.py").write_text(
        "from . import guards\n"
        "def run_probe(probe_id):\n"
        "    assert probe_id == 'MUT-V2-001'\n"
        "    return dict(protocol='synthetic-bootstrap-only',probe_id=probe_id,\n"
        "        terminal='complete',\n"
        "        cases=[dict(id='synthetic-only',setup='passed',call='passed',teardown='passed',\n"
        "            observed={'synthetic':True},exception=None)])\n",
        encoding="utf8",
    )
    cache, temporary, home = (tmp_path / name for name in ("c", "t", "h"))
    for directory in (cache, temporary, home):
        directory.mkdir()
    environment = {
        "PATH": os.defpath,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "TMP": str(temporary),
        "TEMP": str(temporary),
        "TMPDIR": str(temporary),
    }
    for name in ("SystemRoot", "WINDIR", "SystemDrive"):
        if name in os.environ:
            environment[name] = os.environ[name]
    before = snapshot_tree(site)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-X",
            "pycache_prefix=" + str(cache),
            "-c",
            runtime._BOOTSTRAP,
            str(site),
            PROBE,
            str(cache),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert snapshot_tree(site) == before
    assert not list(cache.iterdir()), "bootstrap wrote bytecode despite -B"
    if case in {"plain", "contextmanager"}:
        assert result.returncode == 0, result.stderr.decode("utf8", errors="replace")
        assert result.stderr == b""
        outer = node._json_bytes(result.stdout)
        assert result.stdout == node._canonical(outer) + b"\n", repr(result.stdout[-8:])
        assert result.stdout.count(b"\n") == 1
        assert outer["probe"]["protocol"] == "synthetic-bootstrap-only"
        assert [row["name"] for row in outer["loaded"]] == [
            "aiflow",
            "aiflow.guards",
            "aiflow.installed_probe",
        ]
        assert outer["interpreter"]["isolated"] == outer["interpreter"]["no_site"] == 1
        assert outer["interpreter"]["dont_write_bytecode"] is True
        assert outer["interpreter"]["cache_prefix"] == str(cache)
    else:
        assert result.returncode != 0 and result.stdout == b""
        assert b"GUARD_CODE_ORIGIN_MISMATCH" in result.stderr, result.stderr


@pytest.mark.parametrize(
    "fault",
    [
        "unknown_cleanup",
        "missing_job",
        "job_eof",
        "timeout",
        "overflow",
        "wrong_argv",
        "wrong_environment",
        "boolean_exit",
        "wrong_cwd",
        "wrong_duration",
        "raw_mismatch",
        "stderr",
        "loaded_path",
        "loaded_valid_wrong_name",
        "missing_guard",
        "duplicate_module",
        "wrong_interpreter",
        "extra_field",
        "duplicate_key",
        "undeclared_output",
        "cache_output",
        "closure_changed",
    ],
)
def test_closed_parser_rejects_self_rehashed_unsafe_protocol(
    phase_fixture: PhaseFixture, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from aiflow.redaction import redact_text

    fixture = phase_fixture
    phase, stage = fixture.phase, fixture.stage
    receipt = deepcopy(stage["receipt"])
    outer = node._json(phase / "report.json")
    if fault == "unknown_cleanup":
        receipt["cleanup"] = "unknown"
    elif fault == "missing_job":
        receipt["receipt"] = None
    elif fault == "job_eof":
        receipt["receipt"]["stdout_eof"] = False
    elif fault == "timeout":
        receipt["timed_out"] = True
    elif fault == "overflow":
        receipt["stderr_overflow"] = True
    elif fault == "wrong_argv":
        receipt["argv"].append("unbound")
    elif fault == "wrong_environment":
        receipt["environment_sha256"] = "0" * 64
    elif fault == "boolean_exit":
        receipt["returncode"] = False
    elif fault == "wrong_cwd":
        receipt["cwd"] = str(phase.parent)
    elif fault == "wrong_duration":
        receipt["duration_ms"] = True
    elif fault == "raw_mismatch":
        (phase / "raw/stdout.raw").write_bytes(b"{}\n")
    elif fault == "stderr":
        data = b"Traceback (most recent call last):\nRuntimeError: unreported\n"
        (phase / "raw/stderr.raw").write_bytes(data)
        (phase / "raw/stderr.log").write_bytes(redact_text(data.decode()).encode())
        receipt.update(stderr_size=len(data), stderr_sha256=node._sha(data))
    elif fault == "loaded_path":
        outer["loaded"][-1]["path"] = "aiflow/unbound.py"
    elif fault == "loaded_valid_wrong_name":
        row = next(
            item
            for item in stage["closure"]["entries"]
            if item["path"] == "Lib/site-packages/aiflow/errors.py"
        )
        outer["loaded"][-1].update(path="aiflow/errors.py", size=row["size"], sha256=row["sha256"])
    elif fault == "missing_guard":
        outer["loaded"].pop()
    elif fault == "duplicate_module":
        outer["loaded"].append(outer["loaded"][-1])
    elif fault == "wrong_interpreter":
        outer["interpreter"]["isolated"] = 0
    elif fault == "extra_field":
        outer["probe"]["unbound"] = True
    elif fault == "undeclared_output":
        (phase / "unexpected.txt").write_bytes(b"unbound")
    elif fault == "cache_output":
        (phase / "c/unbound.pyc").write_bytes(b"unbound")
    elif fault == "closure_changed":
        (phase / "i/Lib/site-packages/aiflow/errors.py").write_bytes(b"unbound")
    if fault in {
        "loaded_path",
        "loaded_valid_wrong_name",
        "missing_guard",
        "duplicate_module",
        "wrong_interpreter",
        "extra_field",
        "duplicate_key",
    }:
        data = node._canonical(outer)
        put_json(phase / "report.json", outer)
        if fault == "duplicate_key":
            data = b'{"kind":"installed-probe-execution-v1",' + data[1:]
        data += b"\n"
        (phase / "raw/stdout.raw").write_bytes(data)
        (phase / "raw/stdout.log").write_bytes(redact_text(data.decode()).encode())
        receipt.update(stdout_size=len(data), stdout_sha256=node._sha(data))
    stage["receipt"] = receipt
    put_json(phase / "raw/receipt.json", receipt)
    before = snapshot_tree(phase)
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        runtime._envelope(phase, stage, PROBE, fixture.materials)
    assert snapshot_tree(phase) == before


# Preserve the fixed AST regressions in a uniquely named module so default
# pytest collection can also import the separate installed acceptance module.
POLICY_SOURCE = ROOT / "src/aiflow/policy.py"
SYMBOL = "_validate_cross_file"
EXTRAS = ("acceptance", "integration", "targeted_mutation", "independent_verifier")
COMPARISON = ast.parse(
    "tuple(check['id'] for check in v2_checks[len(v1_checks):]) != extras", mode="eval"
).body
NODE_COMPARISON = ast.parse(
    "tuple(check['id'] for check in node_v2_checks[len(NODE_V1_CHECKS):]) != node_v2_extras",
    mode="eval",
).body


@pytest.fixture
def copied_policy(tmp_path: Path):
    original = POLICY_SOURCE.read_bytes()
    path = tmp_path / "policy.py"
    path.write_bytes(original)
    yield path
    assert POLICY_SOURCE.read_bytes() == original, "Mutation touched the original Policy module"


def _target(tree: ast.Module) -> ast.FunctionDef:
    matches = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == SYMBOL
    ]
    assert len(matches) == 1
    return matches[0]


def _comparison(function: ast.FunctionDef, template: ast.AST = COMPARISON) -> ast.Compare:
    expected = ast.dump(template, include_attributes=False)
    matches = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Compare) and ast.dump(node, include_attributes=False) == expected
    ]
    assert len(matches) == 1
    return matches[0]


def _load_policy(path: Path) -> ModuleType:
    # Compile the actual source bytes instead of reading an adjacent cached pyc.
    name = "aiflow._installed_mutation_policy_fixture"
    module = ModuleType(name)
    module.__file__ = str(path)
    with patch.dict(sys.modules, {name: module}):
        exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def _without_check(identifier: str) -> dict:
    documents = v2_documents()
    levels = documents["verification-levels.yaml"]["levels"]
    v2 = next(level for level in levels if level["id"] == "V2")
    v2["checks"] = [check for check in v2["checks"] if check["id"] != identifier]
    return documents


def test_installed_001_changes_only_the_fixed_native_and_node_comparisons(
    copied_policy: Path,
) -> None:
    from aiflow import installed_mutations

    before = ast.parse(copied_policy.read_bytes())
    expected = deepcopy(before)
    for name, template in (("extras", COMPARISON), ("node_v2_extras", NODE_COMPARISON)):
        comparison = _comparison(_target(expected), template)
        comparison.ops = [ast.NotIn()]
        comparison.comparators = [
            ast.Tuple(
                elts=[
                    ast.Name(id=name, ctx=ast.Load()),
                    ast.Tuple(
                        elts=[
                            ast.Constant(value=value)
                            for value in EXTRAS
                            if value != "targeted_mutation"
                        ],
                        ctx=ast.Load(),
                    ),
                ],
                ctx=ast.Load(),
            )
        ]
    installed_mutations._mutate("MUT-V2-001", copied_policy)
    after_bytes = copied_policy.read_bytes()
    after = ast.parse(after_bytes)
    assert ast.dump(after, include_attributes=False) == ast.dump(expected, include_attributes=False)
    assert _outside_target_dump(after, SYMBOL) == _outside_target_dump(before, SYMBOL)
    for name in ("extras", "node_v2_extras"):
        assignments = [
            node
            for node in ast.walk(_target(after))
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
        ]
        assert len(assignments) == 1
        assert ast.literal_eval(assignments[0].value) == EXTRAS
    compile(after_bytes, str(copied_policy), "exec")


def test_installed_001_keeps_the_positive_policy_control(copied_policy: Path) -> None:
    baseline = _load_policy(copied_policy)
    assert baseline._validate_cross_file(v2_documents()) == "2.6.0"
    with pytest.raises(PolicyError) as caught:
        baseline._validate_cross_file(_without_check("targeted_mutation"))
    assert caught.value.code == "POLICY_CHECK_REFERENCE_INVALID"

    from aiflow import installed_mutations

    installed_mutations._mutate("MUT-V2-001", copied_policy)
    mutant = _load_policy(copied_policy)
    assert mutant._validate_cross_file(v2_documents()) == "2.6.0"
    # This acceptance is the intended injected defect, not a production PASS.
    assert mutant._validate_cross_file(_without_check("targeted_mutation")) == "2.6.0"
    for other in ("acceptance", "integration", "independent_verifier"):
        with pytest.raises(PolicyError) as caught:
            mutant._validate_cross_file(_without_check(other))
        assert caught.value.code == "POLICY_CHECK_REFERENCE_INVALID"


def test_installed_001_has_the_same_positive_and_designated_negative_controls_for_node2(
    copied_policy: Path,
) -> None:
    from test_node_v2_contract import node_documents

    from aiflow import installed_mutations

    def without(identifier):
        documents = node_documents()
        level = documents["verification-levels.yaml"]["levels"][2]
        level["checks"] = [row for row in level["checks"] if row["id"] != identifier]
        return documents

    baseline = _load_policy(copied_policy)
    assert baseline._validate_cross_file(node_documents()) == "3.2.0"
    with pytest.raises(PolicyError) as caught:
        baseline._validate_cross_file(without("targeted_mutation"))
    assert caught.value.code == "POLICY_CHECK_REFERENCE_INVALID"
    installed_mutations._mutate("MUT-V2-001", copied_policy)
    mutant = _load_policy(copied_policy)
    assert mutant._validate_cross_file(node_documents()) == "3.2.0"
    # Only this intentionally injected omission is permitted by the mutant.
    assert mutant._validate_cross_file(without("targeted_mutation")) == "3.2.0"
    for other in ("acceptance", "integration", "independent_verifier"):
        with pytest.raises(PolicyError) as caught:
            mutant._validate_cross_file(without(other))
        assert caught.value.code == "POLICY_CHECK_REFERENCE_INVALID"


@pytest.mark.parametrize("mutation_id", ["MUT-V2-000", "MUT-V2-006", "unknown"])
def test_installed_mutator_rejects_unknown_ids_without_writes(
    copied_policy: Path, mutation_id: str
) -> None:
    from aiflow import installed_mutations

    original = copied_policy.read_bytes()
    with pytest.raises(ContractError):
        installed_mutations._mutate(mutation_id, copied_policy)
    assert copied_policy.read_bytes() == original


@pytest.mark.parametrize("shape", ["missing_comparison", "duplicate_comparison", "missing_symbol"])
def test_installed_001_rejects_unknown_or_ambiguous_ast_without_writes(
    copied_policy: Path, shape: str
) -> None:
    from aiflow import installed_mutations

    tree = ast.parse(copied_policy.read_bytes())
    function = _target(tree)
    comparison = _comparison(function)
    if shape == "missing_comparison":
        comparison.ops = [ast.Eq()]
    elif shape == "duplicate_comparison":
        owner = next(
            node
            for node in ast.walk(function)
            if isinstance(node, ast.If) and comparison in list(ast.walk(node.test))
        )
        owner.test = ast.BoolOp(op=ast.Or(), values=[owner.test, deepcopy(comparison)])
    else:
        function.name = "_different_policy_symbol"
    copied_policy.write_text(ast.unparse(ast.fix_missing_locations(tree)) + "\n", encoding="utf8")
    original = copied_policy.read_bytes()
    with pytest.raises(ContractError):
        installed_mutations._mutate("MUT-V2-001", copied_policy)
    assert copied_policy.read_bytes() == original


@pytest.mark.parametrize(
    "shape",
    [
        "missing_comparison",
        "duplicate_comparison",
        "missing_extras",
        "duplicate_extras",
        "changed_extras",
    ],
)
def test_installed_001_rejects_unknown_node_guard_shapes_without_writes(copied_policy, shape):
    from aiflow import installed_mutations

    tree = ast.parse(copied_policy.read_bytes())
    function = _target(tree)
    comparison = _comparison(function, NODE_COMPARISON)
    extras = next(
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "node_v2_extras"
            for target in node.targets
        )
    )
    if shape == "missing_comparison":
        comparison.ops = [ast.Eq()]
    elif shape == "duplicate_comparison":
        owner = next(
            node
            for node in ast.walk(function)
            if isinstance(node, ast.If) and comparison in list(ast.walk(node.test))
        )
        owner.test = ast.BoolOp(op=ast.Or(), values=[owner.test, deepcopy(comparison)])
    elif shape == "duplicate_extras":
        function.body.append(deepcopy(extras))
    elif shape == "missing_extras":
        extras.targets[0].id = "foreign_extras"
    else:
        extras.value = ast.Tuple(elts=[ast.Constant(value="unsupported")], ctx=ast.Load())
    copied_policy.write_text(ast.unparse(ast.fix_missing_locations(tree)) + "\n", encoding="utf8")
    original = copied_policy.read_bytes()
    with pytest.raises(ContractError) as caught:
        installed_mutations._mutate("MUT-V2-001", copied_policy)
    assert caught.value.code == "INSTALLED_MUTATION_OPERATOR_INVALID"
    assert copied_policy.read_bytes() == original


@pytest.mark.parametrize("invalid", [b"def broken(", b"\xff"])
def test_installed_001_rejects_invalid_source_without_writes(
    copied_policy: Path, invalid: bytes
) -> None:
    from aiflow import installed_mutations

    copied_policy.write_bytes(invalid)
    with pytest.raises(ContractError):
        installed_mutations._mutate("MUT-V2-001", copied_policy)
    assert copied_policy.read_bytes() == invalid


@pytest.mark.parametrize(
    "mutation_id,name,source",
    [
        ("MUT-V2-001", "unrelated.py", "policy.py"),
        ("MUT-V2-002", "policy.py", "verifier_service.py"),
        ("MUT-V2-003", "policy.py", "approval.py"),
        ("MUT-V2-004", "policy.py", "gate.py"),
        ("MUT-V2-005", "policy.py", "evidence.py"),
    ],
)
def test_installed_mutator_rejects_wrong_file_targets(
    tmp_path: Path, mutation_id: str, name: str, source: str
) -> None:
    from aiflow import installed_mutations

    # Each body has the correct real guard; only its bound filename is wrong.
    original = (ROOT / "src/aiflow" / source).read_bytes()
    path = tmp_path / name
    path.write_bytes(original)
    with pytest.raises(ContractError):
        installed_mutations._mutate(mutation_id, path)
    assert path.read_bytes() == original


def test_installed_001_rejects_wrong_module_even_with_expected_basename(
    copied_policy: Path,
) -> None:
    from aiflow import installed_mutations

    original = (ROOT / "src/aiflow/evidence.py").read_bytes()
    copied_policy.write_bytes(original)
    with pytest.raises(ContractError):
        installed_mutations._mutate("MUT-V2-001", copied_policy)
    assert copied_policy.read_bytes() == original


def node_archive_framing(run: LogicalRun) -> SimpleNamespace:
    """Schema/byte framing only: the primitive remains FIXTURE_NO_EXECUTION.

    No Current is manufactured and this document is never submitted as runtime
    acceptance. Each test below corrupts a specific binding and requires the
    real archive validator to reject it without writes or process execution.
    """
    from test_node_v2_evidence import public_node_evidence

    from aiflow.evidence import prepare_v2_pre_evidence, validate_node_evidence

    inputs = run.model.inputs
    directory = run.path.parent
    evidence = public_node_evidence(run.model.root)
    implementation = evidence["review_refs"]["implementation"]
    for key in (
        "task_id",
        "repository_id",
        "branch",
        "base_commit",
        "subject_commit",
        "spec_sha256",
        "policy_sha256",
        "classification_input_sha256",
        "verifier_actor",
        "verifier_context_sha256",
    ):
        evidence[key] = getattr(inputs, key)
    evidence["decision_unit_ids"] = list(inputs.decision_unit_ids)
    evidence["reproduce_command"][6] = inputs.verifier_actor
    evidence["reproduce_command"][-1] = directory.name
    for check in evidence["checks"]:
        for execution in check["executions"]:
            for stream in ("stdout", "stderr"):
                for role in ("raw_ref", "log_ref"):
                    execution[stream][role] = execution[stream][role].replace(
                        "IMUT-0123456789abcdef", directory.name
                    )
    projection = {
        "reference": asdict(run.reference),
        "inputs_sha256": inputs.sha256,
        "results": [[probe, "killed"] for probe in runtime.PROBE_IDS],
    }
    evidence["installed_mutation"] = projection
    node_directory = directory / "node"
    node_directory.mkdir()
    original = {
        "kind": "aiflow-node-run-3.2",
        "installed_mutation": deepcopy(projection),
        "unit_fixture_no_execution": True,
    }
    put_json(node_directory / "run.json", original)
    evidence["node_binding"]["subject_tree"] = inputs.subject_tree
    evidence["node_binding"]["product_tests"]["report"]["ref"] = (
        f"logs/{directory.name}/node/vitest.json"
    )
    evidence["node_binding"]["run"] = {
        "ref": f"logs/{directory.name}/node/run.json",
        "size": len(node._canonical(original)),
        "sha256": node._sha(node._canonical(original)),
    }
    evidence["node_binding_sha256"] = node._sha(node._canonical(evidence["node_binding"]))
    evidence = prepare_v2_pre_evidence(evidence)
    validate_node_evidence(evidence)
    archive = directory / "evidence.json"
    current = resolve_task_path(run.model.root, TASK, "evidence.json")
    put_json(archive, evidence)
    put_json(current, evidence)
    assert node._json(run.path)["failure"] == "FIXTURE_NO_EXECUTION"
    return SimpleNamespace(
        run=run,
        evidence=evidence,
        original=original,
        archive=archive,
        current=current,
        implementation=implementation,
    )


def write_archive_framing(case: SimpleNamespace) -> None:
    from aiflow.evidence import validate_node_evidence, verification_snapshot_sha256

    evidence = case.evidence
    evidence["node_binding_sha256"] = node._sha(node._canonical(evidence["node_binding"]))
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    validate_node_evidence(evidence)
    put_json(case.archive, evidence)
    put_json(case.current, evidence)


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("final_role", "pre archive has the wrong role"),
        ("noncanonical", "pre archive has the wrong role"),
        ("foreign_actor", "foreign task binding"),
        ("foreign_branch", "foreign task binding"),
        ("foreign_units", "foreign decision units"),
        ("mutation_reference", "foreign mutation original"),
        ("mutation_inputs", "foreign mutation original"),
        ("mutation_results", "foreign mutation original"),
        ("node_size", "foreign Node run"),
        ("subject_tree", "foreign Node run"),
        ("node_kind", "does not bind this exact mutation original"),
        ("node_projection", "does not bind this exact mutation original"),
        ("current_snapshot", "differs from the current stable snapshot"),
    ],
)
def test_node_archive_rejects_corrupt_framing_with_real_schema_and_byte_guards(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, fault: str, message: str
) -> None:
    from aiflow.evidence import verification_snapshot_sha256

    case = node_archive_framing(logical_run)
    evidence = case.evidence
    if fault == "final_role":
        evidence["phase"] = "final"
        evidence["review_refs"]["implementation"] = case.implementation
    elif fault == "foreign_actor":
        evidence["verifier_actor"] = "foreign-verifier"
        evidence["reproduce_command"][6] = "foreign-verifier"
    elif fault == "foreign_branch":
        evidence["branch"] = "foreign-branch"
    elif fault == "foreign_units":
        evidence["decision_unit_ids"] = ["DU-999"]
    elif fault == "mutation_reference":
        evidence["installed_mutation"]["reference"]["size"] += 1
    elif fault == "mutation_inputs":
        evidence["installed_mutation"]["inputs_sha256"] = "a" * 64
    elif fault == "mutation_results":
        evidence["installed_mutation"]["results"][0][1] = "survived"
        for check in evidence["checks"]:
            if check["check_id"] in {"targeted_mutation", "independent_verifier"}:
                check["status"] = "failed"
        evidence["conclusion"] = "failed"
    elif fault == "node_size":
        evidence["node_binding"]["run"]["size"] += 1
    elif fault == "subject_tree":
        evidence["node_binding"]["subject_tree"] = "a" * 40
    elif fault in {"node_kind", "node_projection"}:
        if fault == "node_kind":
            case.original["kind"] = "foreign-node-role"
        else:
            case.original["installed_mutation"]["inputs_sha256"] = "a" * 64
        raw = node._canonical(case.original)
        (logical_run.path.parent / "node/run.json").write_bytes(raw)
        evidence["node_binding"]["run"].update(size=len(raw), sha256=node._sha(raw))
    write_archive_framing(case)
    if fault == "noncanonical":
        case.archive.write_bytes(case.archive.read_bytes() + b"\n")
    elif fault == "current_snapshot":
        current = deepcopy(evidence)
        current["node_binding"]["materials_sha256"] = "a" * 64
        current["node_binding_sha256"] = node._sha(node._canonical(current["node_binding"]))
        current["verification_snapshot_sha256"] = verification_snapshot_sha256(current)
        put_json(case.current, current)
    before = snapshot_tree(logical_run.model.root)
    with pure_guard(monkeypatch), pytest.raises(AiflowError, match=message):
        runtime._validate_node_pre_archive(
            logical_run.model.root,
            logical_run.reference,
            logical_run.model.inputs,
            logical_run.path.parent,
        )
    assert snapshot_tree(logical_run.model.root) == before
    assert node._json(logical_run.path)["failure"] == "FIXTURE_NO_EXECUTION"


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("decision_units", "decision units are invalid"),
        ("foreign_task", "belongs to a different task"),
        ("lower_level", "Only Node V2 may own additional installed run roles"),
        ("archive_without_node", "archive has no owned Node role"),
        ("node_file", "directory"),
        ("unknown_child", "missing or undeclared outputs"),
        ("extra_phase", "missing or undeclared phases"),
    ],
)
def test_node_installed_run_children_reject_invalid_inputs_or_owned_roles(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, fault: str, message: str
) -> None:
    root, run = logical_run.model.root, logical_run.path.parent
    reference = logical_run.reference
    if fault in {"decision_units", "foreign_task"}:
        document = node._json(logical_run.path)
        document["inputs"]["decision_unit_ids" if fault == "decision_units" else "task_id"] = (
            "DU-001" if fault == "decision_units" else "TASK-0002"
        )
        reference = rewrite_run(logical_run.path, document, logical_run.model.inputs)
        completion = node._json(run / "completion.json")
        completion["inputs_sha256"] = node._sha(node._canonical(document["inputs"]))
        put_json(run / "completion.json", completion)
    elif fault == "lower_level":
        from aiflow.contracts import require_valid_contract

        (run / "node").mkdir()
        path = resolve_task_path(root, TASK, "classification.json")
        classification = node._json(path)
        classification["schema_version"] = "1.0"
        classification["effective_verification_level"] = "V1"
        for item in classification["classifications"]:
            item["verification_level"] = "V1"
        require_valid_contract("classification", classification)
        put_json(path, classification)
    elif fault == "archive_without_node":
        put_json(run / "evidence.json", {})
    elif fault == "node_file":
        (run / "node").write_bytes(b"not a directory")
    elif fault == "unknown_child":
        (run / "unowned").mkdir()
    else:
        (run / "0/extra").mkdir()
    before = snapshot_tree(root)
    with pure_guard(monkeypatch), pytest.raises(AiflowError, match=message):
        runtime._validate_run_children(root, reference)
    assert snapshot_tree(root) == before
    if fault in {"decision_units", "foreign_task"}:
        with pytest.raises(AiflowError):
            collect(logical_run, reference)
        assert snapshot_tree(root) == before


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_owned_empty_node_role_does_not_turn_a_failed_primitive_into_execution(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = logical_run.model.root
    (logical_run.path.parent / "node").mkdir()
    current = collect(logical_run)
    before = snapshot_tree(root)
    reached = []
    parse = runtime._pair_originals

    def actual_parser(*args, **kwargs):
        reached.append(True)
        return parse(*args, **kwargs)

    monkeypatch.setattr(runtime, "_pair_originals", actual_parser)
    with pure_guard(monkeypatch):
        facts = runtime.replay_installed_mutations(root, logical_run.reference, current=current)
    assert reached and not facts.passed and not facts.all_killed
    assert facts.reason_codes and facts.results == ()
    assert snapshot_tree(root) == before


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize("fault", ["pre_phase", "classification"])
def test_node_pending_code_exception_rejects_wrong_phase_or_verification_strength(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    stage_node_v2_code_marker(logical_run, "pending")
    root = logical_run.model.root
    if fault == "pre_phase":
        path = resolve_task_path(root, TASK, "evidence.json")
        evidence = node._json(path)
        evidence["phase"] = "pre_implementation_review"
        put_json(path, evidence)
        before = snapshot_tree(root)
        with pytest.raises(AiflowError, match="Only current Node V2 final code approval"):
            collect(logical_run)
    else:
        from aiflow.contracts import require_valid_contract

        path = resolve_task_path(root, TASK, "classification.json")
        classification = node._json(path)
        classification["schema_version"] = "1.0"
        classification["effective_verification_level"] = "V1"
        for item in classification["classifications"]:
            item["verification_level"] = "V1"
        require_valid_contract("classification", classification)
        put_json(path, classification)
        before = snapshot_tree(root)
        with pure_guard(monkeypatch), pytest.raises(AiflowError, match="Only a Node V2 task"):
            runtime._require_pending_approval(root, TASK, executing=False, node_v2=True)
        with pytest.raises(AiflowError):
            collect(logical_run)
    assert snapshot_tree(root) == before


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
@pytest.mark.parametrize("fault", ["approval_inventory", "event_prefix"])
def test_node_pending_current_rejects_a_different_valid_snapshot_without_recovery(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    stage_node_v2_code_marker(logical_run, "ledger_written")
    current = collect(logical_run)
    snapshot = node._json_bytes(current.root_snapshot)
    if fault == "approval_inventory":
        snapshot["governance"]["approvals"][-1]["reason"] = "different valid approval text"
    else:
        snapshot["events"].pop()
    corrupted = replace(current, root_snapshot=node._canonical(snapshot))
    messages = []
    error = runtime._error

    def observed_error(*args, **kwargs):
        result = error(*args, **kwargs)
        messages.append(result.message)
        return result

    monkeypatch.setattr(runtime, "_error", observed_error)
    before = snapshot_tree(logical_run.model.root)
    with pure_guard(monkeypatch):
        facts = runtime.replay_installed_mutations(
            logical_run.model.root, logical_run.reference, current=corrupted
        )
    assert not facts.current and not facts.passed and facts.results == ()
    assert "Current pending approval inventory is not the exact validated live state" in messages
    assert snapshot_tree(logical_run.model.root) == before


@pytest.mark.parametrize("model", ["node-v2"], indirect=True)
def test_node_archive_dispatcher_validates_the_actual_current_snapshot(
    logical_run: LogicalRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow.evidence import verification_snapshot_sha256

    case = node_archive_framing(logical_run)
    current = deepcopy(case.evidence)
    current["generated_at"] = "2026-09-01T00:00:00Z"
    current["verification_snapshot_sha256"] = verification_snapshot_sha256(current)
    put_json(case.current, current)
    before = snapshot_tree(logical_run.model.root)
    with pure_guard(monkeypatch), pytest.raises(AiflowError, match="current stable snapshot"):
        runtime._validate_run_children(logical_run.model.root, logical_run.reference)
    assert snapshot_tree(logical_run.model.root) == before
    assert node._json(logical_run.path)["failure"] == "FIXTURE_NO_EXECUTION"
