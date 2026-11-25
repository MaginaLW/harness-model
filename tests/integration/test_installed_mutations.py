"""Ordinary-wheel acceptance for the closed installed-engine primitive.

The synthetic fixture uses real initialization, governance and action services.
Only explicitly isolated rejection tests replace a process wrapper; a successful
five-pair acceptance must execute the installed bytes in actual Windows Jobs.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import zipfile
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from test_answer_command import specification
from test_resource_bundle_distribution import (
    _build,
    _environment,
    _installed_bundle,
    _source,
    _wheelhouse,
)

ROOT = Path(__file__).resolve().parents[2]
MODULES = ("installed_mutations.py", "installed_probe.py")
PROBES = tuple(f"MUT-V2-{number:03d}" for number in range(1, 6))
TASK = "TASK-0001"


def _copy_git(root: Path) -> Path:
    """Give the runtime ordinary copies of the fixed public Git host roles."""
    executable = shutil.which("git")
    assert executable, "Git is required for the synthetic task"
    entry = Path(executable).absolute()
    if entry.parent.name.casefold() == "cmd":
        source = entry.parent.parent
    else:
        assert entry.parent.name.casefold() == "bin"
        assert entry.parent.parent.name.casefold() == "mingw64"
        source = entry.parent.parent.parent
    for relative in ("cmd", "mingw64/bin", "usr/bin"):
        for directory, names, files in os.walk(source / relative, followlinks=False):
            for name in (*names, *files):
                info = (Path(directory) / name).lstat()
                assert not stat.S_ISLNK(info.st_mode)
                assert not getattr(info, "st_file_attributes", 0) & 0x400
        shutil.copytree(source / relative, root / relative, copy_function=shutil.copyfile)
    for relative in (
        "cmd/git.exe",
        "mingw64/bin/git.exe",
        "mingw64/bin/git-upload-pack.exe",
        "usr/bin/sh.exe",
    ):
        actual = root / relative
        assert actual.read_bytes() == (source / relative).read_bytes()
        assert actual.lstat().st_nlink == 1
    return root / "cmd"


_COVERAGE_MERGE_LOCK = threading.Lock()


@dataclass(frozen=True)
class OrdinaryEngine:
    python: Path
    root: Path
    git: Path
    wheel: Path
    origin: str

    def run(
        self,
        target: Path,
        code: str,
        *arguments: str,
        original_git: bool = False,
        instrument: bool = True,
        env_root: Path | None = None,
    ) -> dict:
        import coverage

        active = coverage.Coverage.current() if instrument else None
        data_file = self.root / (".coverage-installed-" + uuid4().hex)
        if active is not None:
            installed = self.python.parents[1] / "Lib/site-packages/aiflow"
            source_files = {
                path.relative_to(ROOT / "src/aiflow"): path.read_bytes()
                for path in (ROOT / "src/aiflow").rglob("*.py")
            }
            assert source_files == {
                path.relative_to(installed): path.read_bytes() for path in installed.rglob("*.py")
            }, "instrumentation requires current, byte-identical ordinary engine sources"
            # Match the existing installed-Node harness: import instrumentation
            # alone, never the source engine/site. Real acceptance is also run
            # without this collector; these data do not cover child Job probes.
            wrapper = """
import importlib.util, sys
from pathlib import Path
code, package, output = (sys.argv.pop(1) for _ in range(3))
spec=importlib.util.spec_from_file_location('coverage',package,
    submodule_search_locations=[str(Path(package).parent)])
module=importlib.util.module_from_spec(spec)
sys.modules['coverage']=module
spec.loader.exec_module(module)
collector=module.Coverage(data_file=output,branch=True,source=['aiflow'],config_file=False)
collector.start()
try:
    exec(compile(code,'<installed-mutation-test>','exec'),{'__name__':'__main__'})
finally:
    collector.stop()
    collector.save()
"""
            argv = [wrapper, code, str(Path(coverage.__file__)), str(data_file)]
        else:
            argv = [code]
        original = shutil.which("git")
        assert original
        git = Path(original).absolute().parent if original_git else self.git
        temp_env: tempfile.TemporaryDirectory[str] | None = None
        if env_root is None:
            temp_env = tempfile.TemporaryDirectory(
                prefix="env-", dir=self.root, ignore_cleanup_errors=True
            )
            isolated_root = Path(temp_env.name)
        else:
            isolated_root = env_root
        try:
            environment = _environment(isolated_root)
            environment["PATH"] = str(git) + os.pathsep + environment["PATH"]
            environment["GIT_CONFIG_GLOBAL"] = os.devnull
            environment["GIT_CONFIG_NOSYSTEM"] = "1"
            environment["GIT_OPTIONAL_LOCKS"] = "0"
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                [str(self.python), "-I", "-B", "-c", *argv, str(target), *arguments],
                cwd=target,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=900,
                check=False,
            )
        finally:
            if temp_env is not None:
                temp_env.cleanup()
        if active is not None and data_file.exists():
            installed = self.python.parents[1] / "Lib/site-packages/aiflow"
            measured = coverage.CoverageData(basename=str(data_file))
            measured.read()

            def source_path(filename: str) -> str:
                path = Path(filename).resolve()
                relative = path.relative_to(installed.resolve())
                source = ROOT / "src/aiflow" / relative
                assert source.read_bytes() == path.read_bytes(), "installed/source bytes differ"
                return str(source.resolve())

            with _COVERAGE_MERGE_LOCK:
                active.get_data().update(measured, map_path=source_path)
        assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
        assert completed.stderr == "", completed.stderr
        return json.loads(completed.stdout.strip())


@pytest.fixture(scope="session")
def ordinary_engines(tmp_path_factory: pytest.TempPathFactory) -> dict[str, OrdinaryEngine]:
    if sys.platform != "win32" or sys.version_info[:2] != (3, 11):
        pytest.skip("installed primitive execution supports Windows CPython 3.11")
    root = tmp_path_factory.mktemp("im")
    assert not root.resolve().is_relative_to(ROOT), "ordinary acceptance must run outside checkout"
    source = root / "s"
    _source(source, crlf=False, identity=b"public-synthetic-installed-mutations-only")
    source_sdist = root / "s-sd"
    shutil.copytree(source, source_sdist, copy_function=shutil.copyfile)
    wheels = root / "wh"
    env_wd = root / "env-wd"
    env_sd = root / "env-sd"
    env_wr = root / "env-wr"
    for directory in (env_wd, env_sd, env_wr):
        directory.mkdir()

    def build_rebuilt() -> Path:
        sdist = _build(source_sdist, root / "sd", "sdist", env_sd)
        return _build(sdist, root / "wr", "wheel", env_wr)

    with ThreadPoolExecutor(max_workers=4) as executor:
        git_future = executor.submit(_copy_git, root / "g")
        wheelhouse_future = executor.submit(_wheelhouse, wheels)
        direct_future = executor.submit(_build, source, root / "wd", "wheel", env_wd)
        rebuilt_future = executor.submit(build_rebuilt)
        git = git_future.result()
        locked = wheelhouse_future.result()
        direct = direct_future.result()
        rebuilt = rebuilt_future.result()

    contents = []
    for wheel in (direct, rebuilt):
        with zipfile.ZipFile(wheel) as archive:
            payload = {name: archive.read("aiflow/" + name) for name in MODULES}
        assert payload == {name: (ROOT / "src/aiflow" / name).read_bytes() for name in MODULES}
        contents.append(payload)
    assert contents[0] == contents[1]

    def install_origin(origin: str, wheel: Path) -> OrdinaryEngine:
        prefix = root / origin
        env_dir = root / f"env-{origin}"
        env_dir.mkdir()
        _installed_bundle(wheel, wheels, locked, prefix, env_dir)
        if origin == "direct":
            # Keep setuptools installed in "rebuilt" for _engine_startup coverage, and drop
            # build-only tools from "direct" so installed closures stay lean during replay.
            subprocess.run(
                [
                    str(prefix / "Scripts/python.exe"),
                    "-I",
                    "-m",
                    "pip",
                    "uninstall",
                    "-y",
                    "pip",
                    "setuptools",
                ],
                cwd=env_dir,
                env=_environment(env_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                timeout=60,
            )
        return OrdinaryEngine(prefix / "Scripts/python.exe", root, git, wheel, origin)

    with ThreadPoolExecutor(max_workers=2) as executor:
        direct_engine_future = executor.submit(install_origin, "direct", direct)
        rebuilt_engine_future = executor.submit(install_origin, "rebuilt", rebuilt)
        return {
            "direct": direct_engine_future.result(),
            "rebuilt": rebuilt_engine_future.result(),
        }


PREPARE = r"""
import hashlib, json, os, subprocess, sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from aiflow.approval import approve_task, canonical_action_sha256
from aiflow.classification_service import classify_task
from aiflow.facts_service import record_risk_facts
from aiflow.initialization import preview_initialization, apply_initialization
from aiflow.installed_mutations import prepare_installed_mutations
from aiflow.review_service import build_review_context, record_review
from aiflow.storage import read_task_yaml, resolve_task_path
from aiflow.task_service import start_task, freeze_task, begin_task
from aiflow.verifier_service import build_verifier_context, save_verifier_context

root, copied_git, frozen_spec = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
def git(*args):
    return subprocess.run(['git','-c','core.fsmonitor=false',*args],cwd=root,
        capture_output=True,text=True,check=True).stdout.strip()

(root/'src/aiflow').mkdir(parents=True)
(root/'src/aiflow/fixture.py').write_text('value = 1\n',encoding='utf8')
(root/'pyproject.toml').write_text('[project]\nname="installed-fixture"\n',encoding='utf8')
(root/'.gitignore').write_text('.ai/tasks/*/logs/\n__pycache__/\n',encoding='utf8')
git('init','-b','fixture')
git('add','.')
git('-c','user.name=Public Fixture','-c','user.email=fixture@example.invalid',
    'commit','-m','public synthetic initial tree')
preview=preview_initialization(root)
review=dict(schema_version='1.0',kind='aiflow-policy-review',
    preview_sha256=preview['preview_sha256'],repository_id=preview['repository_id'],
    profile=preview['profile'],policy_version=preview['policy']['policy_version'],
    policies=[dict(path=x['path'],sha256=x['sha256']) for x in preview['policy']['files']],
    reviewer='fixture-policy-reviewer',outcome='APPROVE')
assert apply_initialization(root,preview,review)['phase']=='installed'
git('add','.ai')
git('-c','user.name=Public Fixture','-c','user.email=fixture@example.invalid',
    'commit','-m','initialize independent fixture identity')
task=start_task(root,objective='public synthetic installed-engine guard acceptance',
    allowed_scope=['src/aiflow/fixture.py'],forbidden_actions=['push','deploy']).task_id
assert task=='TASK-0001'
facts=dict(impact_categories=[],controlled_actions=[],permission_requirements=['action_approval'],
    reversibility='reversible',business_direction_count=1,scope={'clear':True},
    impact={'level':'medium'},protections={'verified_backup':False,'dry_run':False},
    verification={'automatic':True,'tools_missing':False},
    change_characteristics=dict(mechanical=False,behavior_changed=True,code_modified=True,
        interaction_scope='cross_module',regression_risk=True,error_detectability='high'),
    verification_requirements=dict(acceptance_required=True,integration_required=True,
        targeted_mutation_required=True,independent_verifier_required=True))
input_path=root.parent/(root.name+'-facts.json')
input_path.write_text(json.dumps(facts),encoding='utf8')
record_risk_facts(root,task,decision_unit_id='DU-001',input_path=input_path,actor='fixture-classifier')
resolve_task_path(root,task,'spec.md').write_text(frozen_spec,encoding='utf8')
freeze_task(root,task,actor='fixture-specifier')
classification=classify_task(root,task,actor='fixture-classifier')
assert classification['effective_route']=='REVIEW'
assert classification['effective_verification_level']=='V2'
context=build_review_context(root,task,'design')
record_review(root,task,actor='fixture-design-reviewer',input_path=dict(
    schema_version='1.0',review_id='REV-0001',review_stage='design',
    recorded_at=datetime.now(timezone.utc).isoformat(),context_sha256=context['context_sha256'],
    outcome='APPROVE',summary='Public synthetic fixture contract only',findings=[]))
approve_task(root,task,approval_type='spec',actor='project-owner',reason='Synthetic fixture spec')
begin_task(root,task,actor='fixture-implementer')
save_verifier_context(root,task,build_verifier_context(root,task))
os.environ['PATH']=copied_git+os.pathsep+os.environ['PATH']
before={str(path.relative_to(root)):path.read_bytes() for path in root.rglob('*') if path.is_file()}
inputs=prepare_installed_mutations(root,task,verifier_actor='fixture-independent-verifier')
assert before=={str(path.relative_to(root)):path.read_bytes()
    for path in root.rglob('*') if path.is_file()},'preparation wrote fixture material'
assert read_task_yaml(root,task,'task.yaml')['current_state']=='IMPLEMENTING'
action=dict(action_type='installed_engine_mutation_v1',target=task,
    parameter_summary=json.dumps(dict(kind='installed_engine_mutation_v1',inputs_sha256=inputs.sha256),
        ensure_ascii=False,sort_keys=True,separators=(',',':')),
    decision_unit_id='DU-001',classification_input_sha256=inputs.classification_input_sha256,
    subject_commit=inputs.subject_commit,
    conditions=['Only fixed public synthetic installed probes'],
    expires_at=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat(),single_use=True)
draft=root/'.ai/tasks'/task/'action-installed-engine-mutation-fixture.json'
draft.write_text(json.dumps(action),encoding='utf8')
review=asdict(inputs)
review['materials']=json.loads(inputs.materials)
review['materials_sha256']=hashlib.sha256(inputs.materials).hexdigest()
review['inputs_sha256']=inputs.sha256
review['action']=action
review['action_sha256']=canonical_action_sha256(action)
review_path=root.parent/(root.name+'-prepared.json')
review_path.write_text(json.dumps(review,ensure_ascii=False,sort_keys=True,indent=2),encoding='utf8')
print(json.dumps(dict(task=task,inputs_sha256=inputs.sha256,action=str(draft),
    review=str(review_path),action_sha256=review['action_sha256'],
    subject=inputs.subject_commit,verifier=inputs.verifier_actor,state='IMPLEMENTING')))
"""


@dataclass(frozen=True)
class PreparedTask:
    engine: OrdinaryEngine
    root: Path
    prepared: dict


def _new_ir_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temporary = tmp_path_factory.getbasetemp().parent
    if temporary.name.startswith("aiflow-check-"):
        temporary = temporary.parent
    return temporary / f"ir-{uuid4().hex[:12]}"


def _prepare_task(engine: OrdinaryEngine, tmp_path_factory: pytest.TempPathFactory) -> PreparedTask:
    temporary = tmp_path_factory.getbasetemp().parent
    if temporary.name.startswith("aiflow-check-"):
        temporary = temporary.parent
    target = Path(tempfile.mkdtemp(prefix="ir", dir=temporary))
    prepared = engine.run(target, PREPARE, str(engine.git), specification(), original_git=True)
    assert prepared["state"] == "IMPLEMENTING"
    assert len(prepared["inputs_sha256"]) == 64
    review_path = Path(prepared["review"])
    review = json.loads(review_path.read_bytes())
    review["candidate"] = {
        "origin": engine.origin,
        "wheel": str(engine.wheel),
        "size": engine.wheel.stat().st_size,
        "sha256": hashlib.sha256(engine.wheel.read_bytes()).hexdigest(),
        "modules": {
            name: hashlib.sha256((ROOT / "src/aiflow" / name).read_bytes()).hexdigest()
            for name in MODULES
        },
    }
    review_path.write_text(
        json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf8"
    )
    return PreparedTask(engine, target, prepared)


def _clone_prepared_task(
    seed: PreparedTask, tmp_path_factory: pytest.TempPathFactory
) -> PreparedTask:
    target = _new_ir_dir(tmp_path_factory)
    shutil.copytree(seed.root, target, copy_function=shutil.copyfile)
    cloned_prepared = dict(seed.prepared)
    cloned_prepared["action"] = str(
        target / ".ai/tasks" / TASK / "action-installed-engine-mutation-fixture.json"
    )
    review_src = Path(seed.prepared["review"])
    review_dst = target.parent / f"{target.name}-prepared.json"
    if review_src.is_file():
        shutil.copyfile(review_src, review_dst)
    cloned_prepared["review"] = str(review_dst)
    return PreparedTask(seed.engine, target, cloned_prepared)


def _host_fast_snapshot(root: Path) -> dict[str, tuple[int, int, int, int]]:
    result: dict[str, tuple[int, int, int, int]] = {}
    stack: list[tuple[str, Path]] = [("", root)]
    while stack:
        rel_prefix, current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                rel = entry.name if not rel_prefix else f"{rel_prefix}{os.sep}{entry.name}"
                info = os.lstat(entry.path)
                if stat.S_ISDIR(info.st_mode):
                    stack.append((rel, Path(entry.path)))
                elif stat.S_ISREG(info.st_mode):
                    result[rel] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    return result


@pytest.fixture(scope="module")
def prepared_origins(
    ordinary_engines: dict[str, OrdinaryEngine],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, PreparedTask]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        direct_future = executor.submit(_prepare_task, ordinary_engines["direct"], tmp_path_factory)
        rebuilt_future = executor.submit(
            _prepare_task, ordinary_engines["rebuilt"], tmp_path_factory
        )
        return {
            "direct": direct_future.result(),
            "rebuilt": rebuilt_future.result(),
        }


@pytest.mark.parametrize("origin", ["direct", "rebuilt"])
def test_ordinary_wheel_prepares_real_current_inputs_without_consumption(
    prepared_origins: dict[str, PreparedTask],
    origin: str,
) -> None:
    prepared = prepared_origins[origin]
    task = prepared.root / ".ai/tasks" / TASK
    assert not list((task / "logs").glob("installed-action-*"))
    assert not list((task / "logs").glob("IMUT-*"))
    events = [json.loads(line) for line in (task / "events.jsonl").read_text().splitlines()]
    assert not any(event["payload"].get("action_status") == "consumed" for event in events)
    assert json.loads(Path(prepared.prepared["action"]).read_text())["action_type"] == (
        "installed_engine_mutation_v1"
    )


COLD_IMPORT = r"""
import hashlib, json, os, sys
from pathlib import Path
root=Path(sys.argv[1])
site=Path(sys.prefix)/'Lib/site-packages'
assert sys.dont_write_bytecode and 'aiflow.installed_mutations' not in sys.modules
def snapshot():
    return {str(path):(path.stat().st_size,hashlib.sha256(path.read_bytes()).hexdigest())
        for directory in (root,site) for path in directory.rglob('*') if path.is_file()}
before=snapshot(); attempts=[]
def audit(event,args):
    writes=event in ('subprocess.Popen','os.system','os.posix_spawn','os.spawn',
        'os.mkdir','os.remove','os.rename','os.rmdir','os.truncate','os.chmod','os.utime')
    if event=='open':
        writes=isinstance(args[2],int) and bool(args[2] & (
            os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
    if writes:
        attempts.append(event)
        raise AssertionError('cold installed import attempted a write or process')
sys.addaudithook(audit)
import aiflow.installed_mutations as runtime
assert not attempts,attempts
assert snapshot()==before,'cold installed import changed fixture or installed bytes'
assert Path(runtime.__file__).is_relative_to(site)
print(json.dumps(dict(read_only=True,engine=str(Path(runtime.__file__)))))
"""


def test_cold_installed_import_has_no_process_or_filesystem_writes(
    ordinary_engines: dict[str, OrdinaryEngine], tmp_path: Path
) -> None:
    # This independent cold-import proof installs a permanent no-write audit
    # hook, so a coverage collector cannot write its own teardown database.
    result = ordinary_engines["direct"].run(tmp_path, COLD_IMPORT, instrument=False)
    assert result["read_only"] is True


REPLAY_BASE = r"""
import builtins, hashlib, io, json, os, stat, subprocess, sys
from contextlib import ExitStack
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch
import aiflow
import aiflow.installed_mutations as runtime
import aiflow.node_execution as node
import aiflow.process_runner as processes
from aiflow.approval import approve_task
from aiflow.errors import AiflowError
from aiflow.storage import read_task_yaml

root=Path(sys.argv[1]); task='TASK-0001'; actor='fixture-independent-verifier'
assert Path(aiflow.__file__).is_relative_to(Path(sys.prefix))
assert Path(runtime.__file__).is_relative_to(Path(sys.prefix))
def _iter_regular_files():
    stack=[('',str(root))]
    while stack:
        rel_prefix,current=stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                rel=entry.name if not rel_prefix else rel_prefix+os.sep+entry.name
                info=os.lstat(entry.path)
                if stat.S_ISDIR(info.st_mode):
                    stack.append((rel,entry.path))
                elif stat.S_ISREG(info.st_mode):
                    yield rel,entry.path,info
def snapshot():
    result={}
    for rel,full_path,info in _iter_regular_files():
        with builtins.open(full_path,'rb') as handle:
            digest=hashlib.file_digest(handle,'sha256').hexdigest()
        result[rel]=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,digest)
    return result
def fast_snapshot():
    result={}
    for rel,_,info in _iter_regular_files():
        result[rel]=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)
    return result
attempts=[]
def forbidden(*args,**kwargs):
    attempts.append((args,kwargs))
    raise AssertionError('pure replay attempted a process or filesystem write')
def replay(reference,*,full_hash=True):
    snap=snapshot if full_hash else fast_snapshot
    before=snap()
    # Live authority may use read-only Git collectors, never a probe or a write.
    # Install the broader process prohibition only after authority is complete.
    try:
        with ExitStack() as stack:
            for module,name in [(node,'run_node_process'),(node,'_process'),
                    (processes,'run_node_process'),(processes,'run_execution')]:
                stack.enter_context(patch.object(module,name,forbidden))
            current=runtime.collect_installed_mutation_current(root,reference,verifier_actor=actor)
    finally:
        assert not attempts,'authority attempted a probe launch'
        assert snap()==before,'authority changed retained originals'
    with ExitStack() as stack:
        for module,name in [(subprocess,'Popen'),(subprocess,'run'),
                (subprocess,'call'),(subprocess,'check_call'),(subprocess,'check_output'),
                (node,'run_node_process'),(node,'_process'),
                (processes,'run_node_process'),(processes,'run_execution')]:
            stack.enter_context(patch.object(module,name,forbidden))
        for name in ('mkdir','makedirs','remove','unlink','rmdir','rename','replace',
                'write','ftruncate','truncate','chmod','utime'):
            stack.enter_context(patch.object(os,name,forbidden))
        for name in ('write_bytes','write_text','mkdir','unlink','rmdir','rename','replace',
                'touch','chmod'):
            stack.enter_context(patch.object(Path,name,forbidden))
        actual_open=os.open
        def read_only_open(path,flags,*args,**kwargs):
            if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                forbidden(path,flags)
            return actual_open(path,flags,*args,**kwargs)
        stack.enter_context(patch.object(os,'open',read_only_open))
        actual_io_open=io.open
        def read_only_io_open(path,mode='r',*args,**kwargs):
            if any(flag in mode for flag in 'wax+'):
                forbidden(path,mode)
            return actual_io_open(path,mode,*args,**kwargs)
        stack.enter_context(patch.object(io,'open',read_only_io_open))
        stack.enter_context(patch.object(builtins,'open',read_only_io_open))
        facts=runtime.replay_installed_mutations(root,reference,current=current)
    assert not attempts,'pure reader caught a forbidden side effect instead of avoiding it'
    assert snap()==before,'pure replay changed retained originals'
    return facts
"""


CURRENT = (
    REPLAY_BASE
    + r"""
inputs=runtime.prepare_installed_mutations(root,task,verifier_actor=actor)
def approve_fixture_action():
    action=root/'.ai/tasks'/task/'action-installed-engine-mutation-fixture.json'
    value=json.loads(action.read_text())
    summary=json.loads(value['parameter_summary'])
    assert summary==dict(kind='installed_engine_mutation_v1',inputs_sha256=inputs.sha256)
    assert value['classification_input_sha256']==inputs.classification_input_sha256
    approve_task(root,task,approval_type='action',actor='project-owner',
        reason='Reviewed public synthetic installed-engine fixture action only',action_file=action)
"""
)


MISSING_REFERENCES_BATCH = (
    REPLAY_BASE
    + r"""
references=json.loads(sys.argv[2])
before=snapshot()
results={}
for value in references:
    reference=runtime.InstalledMutationReference(value,1,'0'*64)
    try:
        facts=replay(reference,full_hash=False)
    except AiflowError as error:
        assert error.code
        current=False; passed=False; reasons=[error.code]; rejected_by='authority'
    else:
        assert not facts.current and not facts.all_killed
        assert not facts.passed and facts.reason_codes
        current=facts.current; passed=facts.passed; reasons=facts.reason_codes; rejected_by='reader'
    assert not attempts
    results[value]=dict(current=current,passed=passed,reasons=reasons,rejected_by=rejected_by)
assert snapshot()==before and not attempts
assert read_task_yaml(root,task,'task.yaml')['current_state']=='IMPLEMENTING'
print(json.dumps(results))
"""
)


MISSING_REFERENCE_CASES = (
    ".ai/tasks/TASK-0001/logs/IMUT-0000000000000000/run.json",
    "../outside.json",
    ".ai/tasks/TASK-0002/logs/IMUT-0000000000000000/run.json",
)


@pytest.fixture(scope="module")
def pure_reader_rejections(
    prepared_origins: dict[str, PreparedTask],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, dict]:
    prepared = _clone_prepared_task(prepared_origins["direct"], tmp_path_factory)
    return prepared.engine.run(
        prepared.root, MISSING_REFERENCES_BATCH, json.dumps(list(MISSING_REFERENCE_CASES))
    )


@pytest.mark.parametrize(
    "reference",
    list(MISSING_REFERENCE_CASES),
    ids=["missing-original", "traversal", "other-task"],
)
def test_pure_reader_rejects_missing_or_invalid_references_without_processes_or_writes(
    pure_reader_rejections: dict[str, dict],
    reference: str,
) -> None:
    result = pure_reader_rejections[reference]
    assert not result["current"] and not result["passed"] and result["reasons"]


REAL_PAIRS = (
    CURRENT
    + r"""
approve_fixture_action()
reference=runtime.record_installed_mutations(root,task,verifier_actor=actor,
    expected_inputs_sha256=inputs.sha256)
facts=replay(reference)
assert facts.current and facts.all_killed and facts.passed,asdict(facts)
assert list(facts.results)==[(f'MUT-V2-{i:03d}','killed') for i in range(1,6)]
path=root/reference.ref
assert path.is_file() and path.stat().st_size==reference.size
assert hashlib.sha256(path.read_bytes()).hexdigest()==reference.sha256
document=json.loads(path.read_bytes())
assert [pair['id'] for pair in document['pairs']]==[f'MUT-V2-{i:03d}' for i in range(1,6)]
receipts=[]
for pair in document['pairs']:
    for role,code in [('baseline',0),('mutant',1)]:
        stage=pair[role]
        receipt=stage['receipt']
        assert receipt['returncode']==code and receipt['cleanup']=='confirmed'
        assert receipt['timed_out'] is False and receipt['execution_error'] is False
        assert receipt['stdout_overflow'] is False and receipt['stderr_overflow'] is False
        assert receipt['stdout_size']>0 and receipt['stderr_size']==0
        assert isinstance(receipt['receipt'],dict),'actual Job receipt was not retained'
        receipts.append(receipt)
assert len(receipts)==10
assert read_task_yaml(root,task,'task.yaml')['current_state']=='IMPLEMENTING'
event_path=root/'.ai/tasks'/task/'events.jsonl'
events=[json.loads(line) for line in event_path.read_text().splitlines()]
uses=[event for event in events if event['payload'].get('action_status')=='consumed']
assert len(uses)==1
before=fast_snapshot()
try:
    runtime.record_installed_mutations(root,task,verifier_actor=actor,
        expected_inputs_sha256=inputs.sha256)
except AiflowError:
    pass
else:
    raise AssertionError('spent installed action was reused')
assert fast_snapshot()==before,'reused action wrote or started another run'
print(json.dumps(dict(reference=asdict(reference),facts=asdict(facts),processes=len(receipts),
    engine=str(Path(runtime.__file__)),inputs_sha256=inputs.sha256)))
"""
)


@pytest.fixture(scope="module")
def _installed_suite_runs(
    prepared_origins: dict[str, PreparedTask],
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[dict[str, object], None, None]:
    # Actual invocation of this fixture requires the reviewed fixture-action
    # execution boundary; defining/collecting the test never starts a pair.
    rebuilt_task = _clone_prepared_task(prepared_origins["rebuilt"], tmp_path_factory)
    direct_task = _clone_prepared_task(prepared_origins["direct"], tmp_path_factory)

    def run_rebuilt() -> tuple[dict, dict[str, tuple[int, int, int, int]]]:
        result = rebuilt_task.engine.run(rebuilt_task.root, REAL_PAIRS)
        return result, _host_fast_snapshot(rebuilt_task.root)

    def run_direct_and_faults() -> tuple[
        dict, dict[str, dict], dict[str, tuple[int, int, int, int]]
    ]:
        result = direct_task.engine.run(direct_task.root, REAL_PAIRS)
        faults = direct_task.engine.run(
            direct_task.root,
            REHASHED_FAULTS_BATCH,
            json.dumps(result["reference"]),
            json.dumps(list(FAULTS)),
        )
        return result, faults, _host_fast_snapshot(direct_task.root)

    with ThreadPoolExecutor(max_workers=2) as executor:
        rebuilt_future = executor.submit(run_rebuilt)
        direct_future = executor.submit(run_direct_and_faults)
        rebuilt_result, rebuilt_snapshot = rebuilt_future.result()
        direct_result, fault_results, direct_snapshot = direct_future.result()

    runs = {
        "direct": (direct_task, direct_result),
        "rebuilt": (rebuilt_task, rebuilt_result),
    }
    yield {"runs": runs, "faults": fault_results}
    assert _host_fast_snapshot(direct_task.root) == direct_snapshot, (
        "direct run was unexpectedly modified"
    )
    assert _host_fast_snapshot(rebuilt_task.root) == rebuilt_snapshot, (
        "rebuilt run was unexpectedly modified"
    )


@pytest.fixture(scope="module")
def recorded_runs(
    _installed_suite_runs: dict[str, object],
) -> dict[str, tuple[PreparedTask, dict]]:
    runs = _installed_suite_runs["runs"]
    assert isinstance(runs, dict)
    return runs


@pytest.fixture(params=["direct", "rebuilt"])
def recorded_task(
    recorded_runs: dict[str, tuple[PreparedTask, dict]], request: pytest.FixtureRequest
) -> tuple[PreparedTask, dict]:
    return recorded_runs[request.param]


def test_ordinary_wheel_runs_five_actual_pairs_and_independently_replays_originals(
    recorded_task: tuple[PreparedTask, dict],
) -> None:
    prepared, result = recorded_task
    assert result["facts"]["current"] is True
    assert result["facts"]["all_killed"] is True
    assert result["facts"]["results"] == [[identifier, "killed"] for identifier in PROBES]
    assert result["processes"] == 10
    assert Path(result["engine"]).is_relative_to(prepared.engine.python.parents[1])
    retained = prepared.root / result["reference"]["ref"]
    assert hashlib.sha256(retained.read_bytes()).hexdigest() == result["reference"]["sha256"]


INTERRUPTED_RECORD = (
    CURRENT
    + r"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
approve_fixture_action()
mode=sys.argv[2]
entered=Event(); release=Event(); starts=[]
class SimulatedInterruption(BaseException):
    pass
def reject_process(argv,**kwargs):
    starts.append((argv,kwargs))
    entered.set()
    if mode=='concurrent':
        assert release.wait(30),'test did not release the one claimed launch'
    if mode=='interrupted':
        raise SimulatedInterruption()
    return processes.NodeProcessResult(None,False,b'',b'',False,False,'not_started',True)
def attempt():
    try:
        reference=runtime.record_installed_mutations(root,task,verifier_actor=actor,
            expected_inputs_sha256=inputs.sha256)
    except SimulatedInterruption:
        return 'interrupted'
    except AiflowError as error:
        assert error.code=='ACTION_APPROVAL_USED',error.code
        return 'action-used'
    try:
        facts=replay(reference)
    except AiflowError as error:
        # A deliberately failed run need not have collectible current authority.
        # Preserve the root guard and accept only its precise retained rejection.
        document=json.loads((root/reference.ref).read_bytes())
        assert document['failure']=='INSTALLED_MUTATION_ROOT_CHANGED',document['failure']
        assert error.code=='INSTALLED_MUTATION_INVALID',error.code
        return 'authority-rejected'
    assert not facts.passed and not facts.all_killed and facts.reason_codes,asdict(facts)
    assert not any(outcome=='killed' for _probe,outcome in facts.results),asdict(facts)
    return 'recorded-failure'
with ExitStack() as stack:
    for module in (runtime,node,processes):
        if hasattr(module,'run_node_process'):
            stack.enter_context(patch.object(module,'run_node_process',reject_process))
    if mode=='concurrent':
        with ThreadPoolExecutor(max_workers=2) as executor:
            first=executor.submit(attempt)
            assert entered.wait(30),'recorder never reached its claimed fixed process'
            try:
                second=executor.submit(attempt)
                second_result=second.result(timeout=30)
                assert len(starts)==1,'two callers launched with the same action'
            finally:
                release.set()
            first_result=first.result(timeout=30)
        assert second_result=='action-used',second_result
    else:
        second_result=None
        first_result=attempt()
    expected={'interrupted'} if mode=='interrupted' else {'recorded-failure','authority-rejected'}
    assert first_result in expected,first_result
    assert len(starts)==1,'recorder skipped real authority or launched past first failure'
    count=len(starts)
    try:
        runtime.record_installed_mutations(root,task,verifier_actor=actor,
            expected_inputs_sha256=inputs.sha256)
    except AiflowError as error:
        assert error.code=='ACTION_APPROVAL_USED',error.code
    else:
        raise AssertionError('a failed/interrupted action was reusable')
    assert len(starts)==count,'spent action reached the process wrapper'
event_path=root/'.ai/tasks'/task/'events.jsonl'
events=[json.loads(line) for line in event_path.read_text().splitlines()]
uses=[event for event in events if event['payload'].get('action_status')=='consumed']
assert len(uses)==1
logs=root/'.ai/tasks'/task/'logs'
assert len(list(logs.glob('installed-action-use-*.json')))==1
assert len(list(logs.glob('installed-action-launch-*.json')))==1
assert read_task_yaml(root,task,'task.yaml')['current_state']=='IMPLEMENTING'
print(json.dumps(dict(consumptions=len(uses),process_starts=len(starts),mode=mode,
    first_result=first_result,second_result=second_result)))
"""
)


@pytest.fixture(scope="module")
def interrupted_action_results(
    prepared_origins: dict[str, PreparedTask],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, dict]:
    modes = ("launch-error", "interrupted", "concurrent")
    clones = {
        mode: _clone_prepared_task(prepared_origins["direct"], tmp_path_factory) for mode in modes
    }
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            mode: executor.submit(
                clones[mode].engine.run, clones[mode].root, INTERRUPTED_RECORD, mode
            )
            for mode in modes
        }
        return {mode: futures[mode].result() for mode in modes}


@pytest.mark.parametrize("mode", ["launch-error", "interrupted", "concurrent"])
def test_failed_interrupted_and_concurrent_actions_remain_single_use(
    interrupted_action_results: dict[str, dict],
    mode: str,
) -> None:
    result = interrupted_action_results[mode]
    assert result["consumptions"] == result["process_starts"] == 1
    assert result["mode"] == mode
    expected = (
        {"interrupted"} if mode == "interrupted" else {"recorded-failure", "authority-rejected"}
    )
    assert result["first_result"] in expected
    assert result["second_result"] == ("action-used" if mode == "concurrent" else None)


@pytest.fixture(scope="module")
def probe_materials() -> dict:
    from aiflow import installed_mutations

    return {"probes": installed_mutations._probe_contract()}


def _baseline_report(probe_id: str, materials: dict) -> dict:
    """A classifier input fixture, never authority or evidence of actual execution."""
    return {
        "protocol": "installed-probe-v1",
        "probe_id": probe_id,
        "terminal": "complete",
        "cases": [
            {
                "id": identifier,
                "setup": "passed",
                "call": "passed",
                "teardown": "passed",
                "observed": deepcopy(observed),
                "exception": None,
            }
            for identifier, observed in materials["probes"]["cases"][probe_id]
        ],
    }


def _mutant_report(probe_id: str, phase: Path, materials: dict) -> dict:
    report = _baseline_report(probe_id, materials)
    case = report["cases"][-1]
    anchor = materials["probes"]["anchors"][probe_id]
    case.update(
        call="failed",
        observed=deepcopy(materials["probes"]["mutant_observations"][probe_id]),
        exception={
            "type": "AssertionError",
            "message": "",
            "frames": [
                {
                    "path": str(phase / "i/Lib/site-packages/aiflow/installed_probe.py"),
                    "function": anchor["function"],
                    "line": anchor["line"],
                }
            ],
        },
    )
    return report


@pytest.mark.parametrize("probe_id", PROBES)
def test_pure_outcome_projection_distinguishes_survival_from_the_exact_assertion(
    tmp_path: Path, probe_materials: dict, probe_id: str
) -> None:
    from aiflow import installed_mutations

    phase = tmp_path / "m"
    baseline = _baseline_report(probe_id, probe_materials)
    assert installed_mutations._baseline_passes(baseline, probe_id, probe_materials)
    assert (
        installed_mutations._derive_mutant(baseline, probe_id, phase, probe_materials) == "survived"
    )
    mutant = _mutant_report(probe_id, phase, probe_materials)
    assert not installed_mutations._baseline_passes(mutant, probe_id, probe_materials)
    assert installed_mutations._derive_mutant(mutant, probe_id, phase, probe_materials) == "killed"


@pytest.mark.parametrize("probe_id", PROBES)
@pytest.mark.parametrize(
    "fault",
    [
        "setup",
        "teardown",
        "not_run",
        "exception_type",
        "missing_exception",
        "wrong_observation",
        "assertion_line",
        "assertion_function",
        "assertion_path",
        "other_case_failed",
    ],
)
def test_pure_outcome_projection_rejects_other_failures(
    tmp_path: Path, probe_materials: dict, probe_id: str, fault: str
) -> None:
    from aiflow import installed_mutations

    phase = tmp_path / "m"
    report = _mutant_report(probe_id, phase, probe_materials)
    case = report["cases"][-1]
    if fault in {"setup", "teardown"}:
        case[fault] = "failed"
    elif fault == "not_run":
        case["call"] = "not_run"
    elif fault == "exception_type":
        case["exception"]["type"] = "RuntimeError"
    elif fault == "missing_exception":
        case["exception"] = None
    elif fault == "wrong_observation":
        case["observed"] = {"unrelated": True}
    elif fault == "assertion_line":
        case["exception"]["frames"][-1]["line"] += 1
    elif fault == "assertion_function":
        case["exception"]["frames"][-1]["function"] = "unrelated_assertion"
    elif fault == "assertion_path":
        case["exception"]["frames"][-1]["path"] = str(tmp_path / "wrong_module.py")
    else:
        report["cases"][0]["call"] = "failed"
    assert (
        installed_mutations._derive_mutant(report, probe_id, phase, probe_materials) == "unverified"
    )


FAULTS = (
    "missing_report",
    "missing_receipt",
    "missing_completion",
    "closure_binding",
    "root_snapshot_rows",
    "root_snapshot_metadata",
    "context_binding",
    "extra_report_field",
    "duplicate_json_key",
    "wrong_loaded_origin",
    "loaded_name_path_mismatch",
    "unreported_stderr",
    "wrong_observation",
    "unrelated_assertion",
    "setup_error",
    "teardown_error",
    "survived",
    "receipt_cleanup",
    "receipt_eof",
    "process_timeout",
    "output_overflow",
)


_REHASHED_FAULTS_BODY = r"""
from copy import deepcopy
from aiflow.redaction import redact_text
path=root/reference.ref; run=path.parent; phase=run/'0/m'
base_document=json.loads(path.read_bytes())
base_completion=json.loads((run/'completion.json').read_bytes())
base_outer=json.loads((phase/'raw/stdout.raw').read_bytes())
base_survived_probe=deepcopy(json.loads((run/'0/b/report.json').read_bytes())['probe'])
def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),
        allow_nan=False).encode()
def content_snapshot():
    return {k:(v[0],v[1],v[2],v[4]) for k,v in snapshot().items()}
initial=content_snapshot()
results={}
for fault in faults:
    document=deepcopy(base_document)
    stage=document['pairs'][0]['mutant']
    originals={}
    moved=None
    def put(filename,data):
        if filename not in originals:
            originals[filename]=filename.read_bytes()
        filename.write_bytes(data)
    candidate=reference
    try:
        if fault in ('missing_report','missing_receipt','missing_completion'):
            missing={'missing_report':phase/'report.json',
                'missing_receipt':phase/'raw/receipt.json',
                'missing_completion':run/'completion.json'}[fault]
            held=run/'held-original'
            assert not held.exists()
            missing.rename(held)
            moved=(held,missing)
        else:
            if fault in ('root_snapshot_rows','root_snapshot_metadata'):
                key='files' if fault=='root_snapshot_rows' else 'metadata'
                assert document['before'][key]
                document['before'][key]=[]
                document['after'][key]=[]
            elif fault=='closure_binding':
                stage['closure']['entries'][0]['identity']['inode']+=1
            elif fault=='context_binding':
                document['inputs']['verifier_context_sha256']='0'*64
            elif fault in ('receipt_cleanup','receipt_eof','process_timeout','output_overflow',
                    'unreported_stderr'):
                receipt=deepcopy(stage['receipt'])
                if fault=='receipt_cleanup':
                    receipt['cleanup']='unknown'
                elif fault=='receipt_eof':
                    receipt['receipt']['stdout_eof']=False
                elif fault=='process_timeout':
                    receipt['timed_out']=True
                elif fault=='output_overflow':
                    receipt['stdout_overflow']=True
                else:
                    stderr=b'Traceback (most recent call last):\nRuntimeError: unrelated error\n'
                    put(phase/'raw/stderr.raw',stderr)
                    put(phase/'raw/stderr.log',redact_text(stderr.decode()).encode())
                    receipt.update(stderr_size=len(stderr),stderr_sha256=hashlib.sha256(stderr).hexdigest())
                stage['receipt']=receipt
                put(phase/'raw/receipt.json',canonical(receipt))
            else:
                outer=deepcopy(base_outer)
                negative=outer['probe']['cases'][-1]
                if fault=='extra_report_field':
                    outer['probe']['unbound']=True
                elif fault=='wrong_loaded_origin':
                    row=next(row for row in outer['loaded'] if row['name']=='aiflow.policy')
                    row['path']='aiflow/unbound.py'
                elif fault=='loaded_name_path_mismatch':
                    row=next(row for row in outer['loaded'] if row['name']=='aiflow.policy')
                    original=next(entry for entry in stage['closure']['entries']
                        if entry['path']=='Lib/site-packages/aiflow/errors.py')
                    row.update(path='aiflow/errors.py',size=original['size'],sha256=original['sha256'])
                elif fault=='wrong_observation':
                    negative['observed']={'error':'unrelated'}
                elif fault=='unrelated_assertion':
                    negative['exception']['frames'][-1]['function']='different_assertion'
                elif fault=='setup_error':
                    negative.update(setup='failed',call='not_run',observed=None)
                elif fault=='teardown_error':
                    negative['teardown']='failed'
                elif fault=='survived':
                    outer['probe']=deepcopy(base_survived_probe)
                elif fault!='duplicate_json_key':
                    raise AssertionError('unknown fault')
                wire=canonical(outer)
                put(phase/'report.json',wire)
                if fault=='duplicate_json_key':
                    wire=b'{"kind":"installed-probe-execution-v1",'+wire[1:]
                wire+=b'\n'
                put(phase/'raw/stdout.raw',wire)
                put(phase/'raw/stdout.log',redact_text(wire.decode()).encode())
                receipt=deepcopy(stage['receipt'])
                receipt.update(stdout_size=len(wire),stdout_sha256=hashlib.sha256(wire).hexdigest())
                if fault=='survived':
                    receipt['returncode']=0
                stage['receipt']=receipt
                put(phase/'raw/receipt.json',canonical(receipt))
            raw=canonical(document)
            candidate=replace(reference,size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            put(path,raw)
            completion=deepcopy(base_completion)
            completion['reference']=asdict(candidate)
            put(run/'completion.json',canonical(completion))
        outcome_faults=('survived','wrong_observation','unrelated_assertion','setup_error','teardown_error')
        try:
            facts=replay(candidate,full_hash=False)
        except AiflowError as error:
            assert fault not in outcome_faults,(fault,error)
            assert error.code
            passed=False; is_current=False; rejected_by='authority'
        else:
            assert not facts.all_killed and not facts.passed, (fault,asdict(facts))
            if fault=='survived':
                assert facts.current and facts.results[0]==('MUT-V2-001','survived'),asdict(facts)
            elif fault in outcome_faults:
                assert facts.current and facts.results[0]==('MUT-V2-001','unverified'),asdict(facts)
            else:
                assert not facts.current and facts.reason_codes,(fault,asdict(facts))
            passed=facts.passed; is_current=facts.current; rejected_by='reader'
    finally:
        if moved is not None:
            moved[0].rename(moved[1])
        for filename,data in originals.items():
            filename.write_bytes(data)
        assert all(filename.read_bytes()==data for filename,data in originals.items())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==reference.sha256
    results[fault]=dict(fault=fault,passed=passed,current=is_current,rejected_by=rejected_by)
assert content_snapshot()==initial
restored=replay(reference,full_hash=False)
assert restored.passed,asdict(restored)
print(json.dumps(results))
"""


REHASHED_FAULTS_BATCH = (
    REPLAY_BASE
    + "\nreference=runtime.InstalledMutationReference(**json.loads(sys.argv[2]))"
    + "\nfaults=json.loads(sys.argv[3])\n"
    + _REHASHED_FAULTS_BODY
)


@pytest.fixture(scope="module")
def rehashed_fault_results(
    _installed_suite_runs: dict[str, object],
) -> dict[str, dict]:
    faults = _installed_suite_runs["faults"]
    assert isinstance(faults, dict)
    return faults


@pytest.mark.parametrize("fault", FAULTS)
def test_real_originals_reject_missing_or_self_rehashed_tampering(
    rehashed_fault_results: dict[str, dict], fault: str
) -> None:
    checked = rehashed_fault_results[fault]
    assert checked["fault"] == fault and checked["passed"] is False
