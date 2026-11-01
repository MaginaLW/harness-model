"""Real ordinary-wheel Node lifecycles and zero-execution rejection boundaries."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

# The shared helper lives in the explicitly owned unit-test scope. Keep focused
# integration invocations independent of pytest's collection order.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))

# ruff: noqa: E402 -- Shared test helper path is fixed above, never a product import path.
from node_helpers import CHECKS, InstalledNodeEngine, node_policies, synthetic_source, tree_bytes
from node_helpers import installed_node_engine as installed_node_engine
from node_helpers import public_node_materials as public_node_materials
from test_answer_command import specification
from test_approve_command import review_package
from test_begin_close_commands import run_git

from aiflow import node_execution, verification_service
from aiflow.errors import AiflowError
from aiflow.policy import POLICY_FILES


@pytest.fixture
def rejection_root(tmp_path: Path) -> Path:
    root = tmp_path / "rejection"
    root.mkdir()
    node_policies(root / ".ai/policy")
    return root


@pytest.mark.parametrize(
    "options",
    [
        {"ci": True},
        {"ci": True, "abandon": True, "reason": "recovery must not run"},
        {"ci": True, "finalize": True},
        {"ci": True, "check_ids": ("node_check",)},
        {"ci_run_dir": Path("external")},
        {"output": Path("external/evidence.json")},
        {"ci": True, "ci_run_dir": Path("external"), "output": Path("external/evidence.json")},
    ],
)
def test_node_ci_rejects_before_task_recovery_processes_or_writes(
    rejection_root: Path, monkeypatch: pytest.MonkeyPatch, options: dict
) -> None:
    before = tree_bytes(rejection_root)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Node CI reached task recovery or process execution")

    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(node_execution, "run_node_process", forbidden)
    with pytest.raises(AiflowError) as caught:
        verification_service.verify_task(rejection_root, "TASK-0001", actor="verifier", **options)
    assert caught.value.code == "VERIFY_NODE_CI_UNSUPPORTED"
    assert tree_bytes(rejection_root) == before


@pytest.mark.parametrize(
    "options", [{"check_ids": ("node_check",)}, {"provisional": True}, {"finalize": True}]
)
def test_node_partial_modes_reject_without_preparing_materials(
    rejection_root: Path, monkeypatch: pytest.MonkeyPatch, options: dict
) -> None:
    before = tree_bytes(rejection_root)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("partial Node verification reached task recovery or process execution")

    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(node_execution, "run_node_process", forbidden)
    with pytest.raises(AiflowError) as caught:
        verification_service.verify_task(rejection_root, "TASK-0001", actor="verifier", **options)
    assert caught.value.code == "NODE_CAPABILITY_UNAVAILABLE"
    assert tree_bytes(rejection_root) == before


@pytest.mark.parametrize("selector", [None, "", "A" * 64, "a" * 63, "../materials", True])
def test_bad_material_selector_rejects_before_recovery(
    rejection_root: Path, monkeypatch: pytest.MonkeyPatch, selector: object
) -> None:
    # A negative-only seam isolates the early selector guard. It never supplies
    # process results, prepared originals, valid evidence, or a positive PASS.
    monkeypatch.setattr(
        verification_service, "_classification", lambda *_: {"effective_verification_level": "V0"}
    )

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid selector reached recovery or process execution")

    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(node_execution, "run_node_process", forbidden)
    before = tree_bytes(rejection_root)
    with pytest.raises(AiflowError) as caught:
        verification_service.verify_task(
            rejection_root, "TASK-0001", actor="verifier", node_materials_sha256=selector
        )
    assert caught.value.code == "NODE_MATERIALS_REQUIRED"
    assert tree_bytes(rejection_root) == before


def test_source_import_cannot_stand_in_for_an_ordinary_engine() -> None:
    with pytest.raises(AiflowError) as caught:
        node_execution._engine()
    assert caught.value.code == "NODE_ENGINE_NOT_INSTALLED"


@pytest.fixture(scope="session")
def node_initialization_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from aiflow.resource_bundle import build_bundle

    root = tmp_path_factory.mktemp("node-init-bundle")
    manifest, content = build_bundle(Path(__file__).resolve().parents[2])
    for relative, data in content.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf8")
    return root


@pytest.fixture
def node_initialization_target(tmp_path: Path) -> Path:
    root = tmp_path / "node-target"
    root.mkdir()
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "node-init-fixture",
                "scripts": {"build": "tsc", "check": "npm test", "test": "vitest run"},
            }
        ),
        encoding="utf8",
    )
    (root / "example.ts").write_text("export const fixture = 1;\n", encoding="utf8")
    run_git(root, "init", "-b", "feature")
    run_git(root, "add", ".")
    run_git(
        root,
        "-c",
        "user.name=Node Fixture",
        "-c",
        "user.email=node@example.invalid",
        "commit",
        "-m",
        "node initialization fixture",
    )
    return root


def test_portable_node_initialization_namespace_is_not_execution_acceptance(
    tmp_path: Path,
    node_initialization_target: Path,
    node_initialization_bundle: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from initialization_helpers import PortableFilesystem

    from aiflow import initialization

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Node initialization tried to prepare tools or a runtime-bound plan")

    monkeypatch.setattr(initialization, "WindowsFilesystem", PortableFilesystem)
    monkeypatch.setattr(initialization, "parse_verification_plan", forbidden)
    monkeypatch.setattr(node_execution, "prepare_node_materials", forbidden)
    policy = node_policies(tmp_path / "policies")
    root = node_initialization_target
    proposal = initialization.preview_initialization(
        root,
        bundle_root=node_initialization_bundle,
        policy_directory=policy,
        profile="agent-bridge-node@1",
    )
    assert not (root / ".ai").exists()
    decision = {
        "schema_version": "1.0",
        "kind": "aiflow-policy-review",
        "preview_sha256": proposal["preview_sha256"],
        "repository_id": proposal["repository_id"],
        "profile": proposal["profile"],
        "policy_version": proposal["policy"]["policy_version"],
        "policies": [
            {"path": row["path"], "sha256": row["sha256"]} for row in proposal["policy"]["files"]
        ],
        "reviewer": "independent-policy-reviewer",
        "outcome": "APPROVE",
    }
    applied = initialization.apply_initialization(
        root, proposal, decision, bundle_root=node_initialization_bundle, policy_directory=policy
    )
    assert applied["phase"] == "installed"
    initialization.require_initialization_ready(root)
    assert initialization.inspect_initialization(root)["profile"] == "agent-bridge-node@1"
    assert not (root / ".ai/tasks").exists()
    assert not (root / ".ai/bootstrap-mode.yaml").exists()
    assert not (root / "node_modules").exists()
    assert not (root / "dist").exists()
    before = tree_bytes(root)
    replay = initialization.apply_initialization(
        root, proposal, decision, bundle_root=node_initialization_bundle, policy_directory=policy
    )
    assert replay["phase"] == "already_complete"
    migration = initialization.plan_initialization_migration(
        root,
        bundle_root=node_initialization_bundle,
        policy_directory=policy,
        profile="agent-bridge-node@1",
    )
    assert migration["read_only"] is True
    assert migration["profile"] == "agent-bridge-node@1"
    assert tree_bytes(root) == before


@pytest.mark.parametrize("missing", [None, *POLICY_FILES])
def test_node_initialization_requires_explicit_complete_policy_without_writes(
    tmp_path: Path,
    node_initialization_target: Path,
    node_initialization_bundle: Path,
    missing: str | None,
) -> None:
    from aiflow.initialization import preview_initialization

    policy = node_policies(tmp_path / "policies") if missing is not None else None
    if missing is not None:
        assert policy is not None
        (policy / missing).unlink()
    before = tree_bytes(node_initialization_target)
    with pytest.raises(AiflowError):
        preview_initialization(
            node_initialization_target,
            bundle_root=node_initialization_bundle,
            policy_directory=policy,
            profile="agent-bridge-node@1",
        )
    assert tree_bytes(node_initialization_target) == before


@pytest.mark.parametrize("variant", ["unshipped", "mixed", "revision_bool", "revision_float"])
def test_node_initialization_rejects_profile_or_policy_drift(
    tmp_path: Path, node_initialization_target: Path, node_initialization_bundle: Path, variant: str
) -> None:
    from aiflow.initialization import preview_initialization

    policy = node_policies(tmp_path / "policies")
    for path in policy.iterdir():
        value = yaml.safe_load(path.read_text(encoding="utf8"))
        if variant == "unshipped":
            value["policy_version"] = "3.0.0"
        elif variant == "mixed" and path.name == "routing.yaml":
            value["policy_version"] = "2.6.0"
        elif variant.startswith("revision") and path.name == "verification-levels.yaml":
            value["profile"]["revision"] = True if variant == "revision_bool" else 1.0
        path.write_text(yaml.safe_dump(value), encoding="utf8")
    before = tree_bytes(node_initialization_target)
    with pytest.raises(AiflowError):
        preview_initialization(
            node_initialization_target,
            bundle_root=node_initialization_bundle,
            policy_directory=policy,
            profile="agent-bridge-node@1",
        )
    assert tree_bytes(node_initialization_target) == before


@pytest.mark.parametrize("variant", ["missing", "invalid", "duplicate", "name", "script", "empty"])
def test_node_initialization_requires_real_bounded_project_input(
    tmp_path: Path, node_initialization_target: Path, node_initialization_bundle: Path, variant: str
) -> None:
    from aiflow.initialization import preview_initialization

    package = node_initialization_target / "package.json"
    if variant == "missing":
        package.unlink()
    elif variant == "invalid":
        package.write_bytes(b"not-json")
    elif variant == "duplicate":
        package.write_bytes(b'{"name":"fixture","name":"duplicate","scripts":{}}')
    else:
        document = json.loads(package.read_text(encoding="utf8"))
        if variant == "name":
            document["name"] = True
        elif variant == "script":
            document["scripts"]["build"] = 1
        else:
            document["scripts"]["test"] = " "
        package.write_text(json.dumps(document), encoding="utf8")
    policy = node_policies(tmp_path / "policies")
    before = tree_bytes(node_initialization_target)
    with pytest.raises(AiflowError):
        preview_initialization(
            node_initialization_target,
            bundle_root=node_initialization_bundle,
            policy_directory=policy,
            profile="agent-bridge-node@1",
        )
    assert tree_bytes(node_initialization_target) == before


@pytest.fixture
def initialized_node_namespace(
    tmp_path: Path,
    node_initialization_target: Path,
    node_initialization_bundle: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    from initialization_helpers import PortableFilesystem
    from test_initialization import review

    from aiflow import initialization

    root = node_initialization_target
    policy = node_policies(tmp_path / "policies")
    # This models only installation namespace operations. Classification and the
    # subsequent V2 rejection are actual product calls and run on Linux too.
    with monkeypatch.context() as patch:
        patch.setattr(initialization, "WindowsFilesystem", PortableFilesystem)
        proposal = initialization.preview_initialization(
            root,
            bundle_root=node_initialization_bundle,
            policy_directory=policy,
            profile="agent-bridge-node@1",
        )
        initialization.apply_initialization(
            root,
            proposal,
            review(proposal),
            bundle_root=node_initialization_bundle,
            policy_directory=policy,
        )
    run_git(root, "add", ".ai")
    run_git(
        root,
        "-c",
        "user.name=Node Fixture",
        "-c",
        "user.email=node@example.invalid",
        "commit",
        "-m",
        "initialized Node namespace baseline",
    )
    return root


def test_real_v2_classification_stays_blocked_before_any_material_preparation(
    tmp_path: Path, initialized_node_namespace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_classify_command import _unit

    from aiflow.classification_service import classify_task
    from aiflow.storage import atomic_write_yaml, read_task_yaml, resolve_task_path
    from aiflow.task_service import read_task_record_strict, start_task

    root = initialized_node_namespace
    started = start_task(
        root,
        objective="synthetic acceptance requirement",
        allowed_scope=["example.ts"],
        forbidden_actions=["push"],
    )
    task_id = started.task_id
    task = read_task_yaml(root, task_id, "task.yaml", contract_name="task")
    task["decision_units"] = [
        _unit(
            task_id,
            impact_scope=["example.ts"],
            verification_requirements={
                "acceptance_required": True,
                "integration_required": False,
                "targeted_mutation_required": False,
                "independent_verifier_required": False,
            },
        )
    ]
    atomic_write_yaml(resolve_task_path(root, task_id, "task.yaml"), task)
    classification = classify_task(root, task_id, actor="classifier")
    assert classification["effective_verification_level"] == "V2"
    assert classification["effective_route"] == "BLOCK"
    assert read_task_record_strict(root, task_id).task["current_state"] == "BLOCKED"

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("a blocked V2 task attempted Node process execution")

    monkeypatch.setattr(node_execution, "run_node_process", forbidden)
    before = tree_bytes(root / ".ai/tasks")
    with pytest.raises(AiflowError) as caught:
        node_execution.prepare_node_materials(root, task_id, payload_root=tmp_path / "absent")
    assert caught.value.code == "VERIFY_NODE_V2_UNSUPPORTED"
    with pytest.raises(AiflowError) as caught:
        verification_service.verify_task(
            root, task_id, actor="verifier", node_materials_sha256="a" * 64
        )
    assert caught.value.code == "NODE_CAPABILITY_UNAVAILABLE"
    assert tree_bytes(root / ".ai/tasks") == before


def test_real_missing_prepared_sha_rejects_before_recovery_state_or_process_writes(
    initialized_node_namespace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from test_classify_command import _unit

    from aiflow.classification_service import classify_task
    from aiflow.storage import atomic_write_yaml, read_task_yaml, resolve_task_path
    from aiflow.task_service import begin_task, freeze_task, start_task

    root = initialized_node_namespace
    task_id = start_task(
        root,
        objective="missing materials negative fixture",
        allowed_scope=["example.ts"],
        forbidden_actions=["push"],
    ).task_id
    task = read_task_yaml(root, task_id, "task.yaml", contract_name="task")
    task["decision_units"] = [_unit(task_id, impact_scope=["example.ts"])]
    atomic_write_yaml(resolve_task_path(root, task_id, "task.yaml"), task)
    classification = classify_task(root, task_id, actor="classifier")
    assert classification["effective_verification_level"] == "V0"
    resolve_task_path(root, task_id, "spec.md").write_text(specification(), encoding="utf8")
    freeze_task(root, task_id, actor="specifier")
    begin_task(root, task_id, actor="implementer")

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("missing prepared SHA reached task recovery or Node execution")

    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(node_execution, "run_node_process", forbidden)
    before = tree_bytes(root / ".ai/tasks")
    with pytest.raises(AiflowError):
        verification_service.verify_task(
            root,
            task_id,
            actor="verifier",
            node_materials_sha256="a" * 64,
            run_id="missing-materials",
        )
    assert tree_bytes(root / ".ai/tasks") == before


PREPARE_TASK = r"""
import json, os, subprocess, sys
from pathlib import Path
from aiflow.initialization import preview_initialization, apply_initialization
from aiflow.task_service import start_task, freeze_task, begin_task
from aiflow.task_service import evaluate_and_sync_verification_subject
from aiflow.classification_service import classify_task
from aiflow.storage import read_task_yaml, atomic_write_yaml, resolve_task_path
from aiflow.review_service import build_review_context, record_review
from aiflow.approval import approve_task
root, level, policies = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
proposal = preview_initialization(root, policy_directory=policies, profile='agent-bridge-node@1')
review = dict(schema_version='1.0', kind='aiflow-policy-review',
    preview_sha256=proposal['preview_sha256'], repository_id=proposal['repository_id'],
    profile=proposal['profile'], policy_version=proposal['policy']['policy_version'],
    policies=[dict(path=x['path'],sha256=x['sha256']) for x in proposal['policy']['files']],
    reviewer='independent-policy-reviewer', outcome='APPROVE')
installed = apply_initialization(root, proposal, review, policy_directory=policies)
assert installed['phase'] == 'installed'
def git(*args):
    return subprocess.run(['git','-c','core.fsmonitor=false',*args],cwd=root,
        capture_output=True,text=True,check=True).stdout.strip()
git('add','.ai')
git('-c','user.name=Node Fixture','-c','user.email=node@example.invalid','commit','-m','initialize')
started = start_task(root,objective='bounded synthetic Node change',
    allowed_scope=['README.md','src/local/**','tests/local/**'],forbidden_actions=['push'])
task_id = started.task_id
assert task_id == 'TASK-0001'
changed = root / ('README.md' if level == 'V0' else 'src/local/add.ts')
task = read_task_yaml(root,task_id,'task.yaml',contract_name='task')
unit = dict(schema_version='1.0',task_id=task_id,decision_unit_id='DU-001',
    goal='bounded fixture change',inputs=[],planned_actions=['edit'],controlled_actions=[],
    impact_categories=[],impact_scope=[changed.relative_to(root).as_posix()],
    reversibility='reversible',verification_methods=['complete fake suite'],
    external_side_effects=[],
    permission_requirements=[],scope={'clear':True},impact={'level':'medium'},
    protections={'verified_backup':True,'dry_run':True},
    verification={'automatic':True,'tools_missing':False},change_characteristics=dict(
        mechanical=level=='V0',behavior_changed=False,code_modified=level!='V0',
        interaction_scope='local',regression_risk=False,error_detectability='high'))
task['decision_units']=[unit]
atomic_write_yaml(resolve_task_path(root,task_id,'task.yaml'),task)
resolve_task_path(root,task_id,'spec.md').write_text(sys.argv[4],encoding='utf8')
classification=classify_task(root,task_id,actor='classifier')
assert classification['effective_verification_level']==level
freeze_task(root,task_id,actor='specifier')
context=build_review_context(root,task_id,'design')
record_review(root,task_id,actor='independent-design-reviewer',input_path=dict(
    schema_version='1.0',review_id='REV-0001',review_stage='design',
    recorded_at='2026-10-31T00:00:00Z',context_sha256=context['context_sha256'],
    outcome='APPROVE',summary='Synthetic design reviewed',findings=[]))
approve_task(root,task_id,approval_type='spec',actor='project-owner',
    reason='synthetic spec approval')
begin_task(root,task_id,actor='implementer')
if level == 'V0':
    changed.write_text(changed.read_text()+'Documented synthetic fixture.\n',
        encoding='utf8',newline='\n')
else:
    changed.write_text(changed.read_text().replace('return a + b;', 'return a + b + 0;'),
        encoding='utf8',newline='\n')
git('add',str(changed.relative_to(root)))
git('-c','user.name=Node Fixture','-c','user.email=node@example.invalid',
    'commit','-m','bounded change')
evaluate_and_sync_verification_subject(root,task_id,mode='final',actor='implementer')
resolve_task_path(root,task_id,'review-package.md').write_text(sys.argv[5],encoding='utf8')
print(json.dumps(dict(task_id=task_id,level=level,profile=proposal['profile'])))
"""


VERIFY_AND_GATE = r"""
import json, sys
from pathlib import Path
import aiflow.node_execution as runtime
from aiflow.errors import AiflowError
from aiflow.node_execution import prepare_node_materials, recheck_node_evidence
from aiflow.verification_service import verify_task
from aiflow.review_service import build_review_context, record_review
from aiflow.approval import approve_task
from aiflow.gate import evaluate_gate
from aiflow.storage import read_task_json
root=Path(sys.argv[1]); task='TASK-0001'
materials=prepare_node_materials(root,task,payload_root=Path(sys.argv[2]))
result=verify_task(root,task,actor='verifier',node_materials_sha256=materials,run_id='real-node-run')
evidence=read_task_json(root,task,'evidence.json',contract_name='evidence')
assert result.conclusion=='passed', evidence
assert evidence['conclusion']=='passed'
facts=recheck_node_evidence(root,task,evidence)
assert facts.current and facts.passed, facts
context=build_review_context(root,task,'implementation')
record_review(root,task,actor='independent-implementation-reviewer',input_path=dict(
    schema_version='1.0',review_id='REV-0002',review_stage='implementation',
    recorded_at='2026-10-31T00:00:00Z',context_sha256=context['context_sha256'],
    outcome='APPROVE',summary='Synthetic implementation reviewed against actual evidence',
    findings=[]))
approve_task(root,task,approval_type='code',actor='project-owner',reason='synthetic code approval')
decision=evaluate_gate(root,task)
assert decision.passed, decision
rejected=[]
def no_process(*args,**kwargs):
    raise AssertionError('an evidence consumer attempted process execution')
runtime.run_node_process=no_process
if evidence['verification_level']=='V0':
    # Negative-only injection: read-only consumers may never refresh originals
    # or run probes to make a corrupted real run current again.
    task_directory=root/'.ai/tasks'/task
    raw=root/'.ai/tasks'/task/evidence['checks'][0]['executions'][0]['stdout']['raw_ref']
    original=raw.read_bytes()
    raw.write_bytes(original+b'changed')
    assert not recheck_node_evidence(root,task,evidence).current
    raw.write_bytes(original)
    rejected.append('raw_stream')
    run=root/'.ai/tasks'/task/evidence['node_binding']['run']['ref']
    missing=run.with_suffix('.missing')
    run.rename(missing)
    assert not recheck_node_evidence(root,task,evidence).current
    missing.rename(run)
    rejected.append('missing_run')
    first=evidence['checks'][0]['executions'][0]['execution_id']
    receipt=run.parent/'raw'/first/'receipt.json'
    original_receipt=receipt.read_bytes()
    for variant in ['cleanup','duration','eof']:
        value=json.loads(original_receipt)
        if variant=='cleanup':
            value['cleanup']='unknown'
        elif variant=='duration':
            value['duration_ms']=float(value['duration_ms'])
        else:
            value['receipt']['stdout_eof']=False
        receipt.write_text(json.dumps(value),encoding='utf8')
        try:
            runtime._validate_receipt(receipt.parent,value)
        except AiflowError:
            pass
        else:
            raise AssertionError('a real process receipt accepted '+variant)
        receipt.write_bytes(original_receipt)
        rejected.append('receipt_'+variant)
    # This changes only this test's independently owned material tree. It does
    # not alter the session's public tools, another task, or an active target.
    extra=Path(sys.argv[2])/'node/node_modules/npm/unrecognized-material.txt'
    extra.write_text('undeclared',encoding='utf8')
    def metadata():
        paths=list(task_directory.glob('*'))+list((task_directory/'reviews').glob('*'))
        return {str(p.relative_to(task_directory)):p.read_bytes() for p in paths if p.is_file()}
    before=metadata()
    facts=recheck_node_evidence(root,task,evidence)
    assert not facts.current and not facts.passed
    from aiflow.status_service import summarize_task
    assert summarize_task(root,task).evidence!='fresh'
    for consumer in [lambda:build_review_context(root,task,'implementation'),
            lambda:approve_task(root,task,approval_type='code',actor='project-owner',reason='retry')]:
        try:
            consumer()
        except AiflowError:
            pass
        else:
            raise AssertionError('a consumer accepted undeclared material')
    try:
        assert not evaluate_gate(root,task).passed
    except AiflowError:
        pass
    assert metadata()==before
    rejected.append('material_extra')
else:
    run=root/'.ai/tasks'/task/evidence['node_binding']['run']['ref']
    original_run=json.loads(run.read_bytes())
    node_dir=run.parent
    checkout=node_dir/'checkout'
    for variant in ['map_lines','hit_float']:
        selected=node_dir/('expected-map.json' if variant=='map_lines'
            else 'coverage/coverage-final.json')
        original=selected.read_bytes()
        value=json.loads(original)
        if variant=='map_lines':
            source=next(iter(value['files'].values()))
            assert source['lines']
            source['lines']=source['lines'][1:]
        else:
            source=next(iter(value.values()))
            identity=next(iter(source['s']))
            source['s'][identity]=float(source['s'][identity])
        selected.write_text(json.dumps(value),encoding='utf8')
        try:
            runtime._coverage(checkout,node_dir,original_run['inputs']['source'],
                evidence['base_commit'],evidence['subject_commit'],root)
        except AiflowError:
            pass
        else:
            raise AssertionError('actual coverage originals accepted '+variant)
        selected.write_bytes(original)
        rejected.append('coverage_'+variant)
print(json.dumps(dict(materials=materials,evidence=evidence,gate=decision.to_dict(),rejected=rejected)))
"""


@pytest.mark.parametrize("level,logical,processes", [("V0", 6, 8), ("V1", 9, 10)])
def test_ordinary_wheel_real_node_lifecycle(
    tmp_path: Path,
    public_node_materials: Path,
    installed_node_engine: InstalledNodeEngine,
    level: str,
    logical: int,
    processes: int,
) -> None:
    repository = tmp_path / "target"
    synthetic_source(repository, public_node_materials)
    policies = node_policies(tmp_path / "node-policy")
    run_git(repository, "init", "-b", "feature")
    run_git(repository, "add", ".")
    run_git(
        repository,
        "-c",
        "user.name=Node Fixture",
        "-c",
        "user.email=node@example.invalid",
        "commit",
        "-m",
        "synthetic source",
    )
    installed_node_engine.run(
        repository, PREPARE_TASK, level, str(policies), specification(), review_package()
    )
    payload = repository / ".ai/tasks/TASK-0001/logs/node-payload/public-fixture"
    payload.mkdir(parents=True)
    # Exactly two independent copies per invocation (one per genuine level),
    # rather than copying the 93 MiB Node tree for every rejection example.
    shutil.copytree(public_node_materials / "node", payload / "node", copy_function=shutil.copyfile)
    shutil.copytree(
        public_node_materials / "dependencies",
        payload / "dependencies",
        copy_function=shutil.copyfile,
    )
    outcome = installed_node_engine.run(repository, VERIFY_AND_GATE, str(payload))
    evidence = outcome["evidence"]
    assert evidence["schema_version"] == "3.1"
    assert evidence["base_commit"] != evidence["subject_commit"]
    assert evidence["verification_level"] == level
    assert len(evidence["checks"]) == logical
    assert [check["check_id"] for check in evidence["checks"][:6]] == [name for name, _ in CHECKS]
    executed = {
        entry["execution_id"] for check in evidence["checks"] for entry in check["executions"]
    }
    assert len(executed) == processes
    assert all(check["status"] == "passed" for check in evidence["checks"])
    assert outcome["gate"]["passed"] is True
    assert not (repository / "node_modules").exists()
    assert not (repository / "dist").exists()
    public = json.dumps(evidence)
    assert str(repository) not in public and str(payload) not in public
    for check in evidence["checks"]:
        for execution in check["executions"]:
            assert execution["cleanup"] == "confirmed"
    if level == "V1":
        assert evidence["node_binding"]["coverage"] is not None
        assert outcome["rejected"] == ["coverage_map_lines", "coverage_hit_float"]
    else:
        assert outcome["rejected"] == [
            "raw_stream",
            "missing_run",
            "receipt_cleanup",
            "receipt_duration",
            "receipt_eof",
            "material_extra",
        ]
