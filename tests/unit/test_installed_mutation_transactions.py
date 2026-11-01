"""Portable authority/transaction/parser tests, never Windows execution evidence.

Task history, Git and retained files are real. Only Windows host-material
collection is replaced by public fixture files. Parser receipts below are
deliberately synthetic inputs; no test treats them as proof that a Job ran.
Actual installed-wheel execution remains in the Windows integration suite.
"""

from __future__ import annotations

import builtins
import io
import os
import shutil
import subprocess
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier, local
from uuid import uuid4

import pytest
from initialization_helpers import fixture_git, snapshot_tree

from aiflow import installed_mutations as runtime
from aiflow import node_execution as node
from aiflow import process_runner as processes
from aiflow.approval import approve_task
from aiflow.classification_service import classify_task
from aiflow.errors import AiflowError
from aiflow.facts_service import record_risk_facts
from aiflow.review_service import build_review_context, record_review
from aiflow.specification import REQUIRED_SECTIONS
from aiflow.storage import read_task_yaml, resolve_task_path
from aiflow.task_service import begin_task, freeze_task, start_task, transition_task_record
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


@pytest.fixture
def model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Model]:
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
    yield Model(root, inputs, verifier_context, material)
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


@dataclass(frozen=True)
class LogicalRun:
    model: Model
    path: Path
    reference: runtime.InstalledMutationReference


@pytest.fixture
def logical_run(model: Model) -> LogicalRun:
    """A closed failure record with no probe reports and no claimed Job execution."""
    action_file(model)
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


@dataclass(frozen=True)
class PhaseFixture:
    phase: Path
    stage: dict
    materials: dict
    report: dict


@pytest.fixture
def phase_fixture(model: Model, tmp_path: Path) -> PhaseFixture:
    """Exact parser input files, not an assertion that their synthetic Job ran."""
    phase = tmp_path / "parser-phase"
    phase.mkdir()
    closure = node._copy_tree(
        Path(model.materials["engine"]["closure"]["root"]),
        phase / "i",
        model.materials["engine"]["closure"],
    )
    for name in ("c", "t", "h", "raw"):
        (phase / name).mkdir()
    report = dict(
        protocol="installed-probe-v1",
        probe_id=PROBE,
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
            for case_id, observation in model.materials["probes"]["cases"][PROBE]
        ],
    )
    files = {
        item["path"].removeprefix("Lib/site-packages/"): item
        for item in closure["entries"]
        if item["kind"] == "file"
    }
    loaded = []
    for name, relative in (
        ("aiflow", "aiflow/__init__.py"),
        ("aiflow.installed_probe", "aiflow/installed_probe.py"),
        ("aiflow.policy", "aiflow/policy.py"),
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
        returncode=0,
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
        argv=list(runtime._argv(phase, PROBE, model.materials)),
        cwd=str(phase),
        environment_sha256=node._sha(node._canonical(runtime._environment(phase, interpreter))),
        timeout_seconds=60,
        duration_ms=1,
    )
    stage = dict(closure=closure, cache=node._inventory(phase / "c"), receipt=receipt)
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
