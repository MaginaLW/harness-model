"""Node 3.1 policy and rejection contracts, using synthetic data only.

The unshipped 3.0 evidence fixture is retained only as a rejection input.
Real 3.1 execution/evidence/review/approval/Gate success tests require the frozen
schema and a shared real synthetic-repository fixture; no mocked success here.
"""

from __future__ import annotations

# ruff: noqa: E402 -- Source-absence guard must precede candidate-only imports.
import json
import shutil
import stat
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

# Baseline-only absence is not a functional pass; malformed or stale imports fail.
ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file() and (parent / "src/aiflow/__init__.py").is_file()
)
NODE_SOURCE = ROOT / "src/aiflow/node_verification.py"
try:
    NODE_SOURCE_INFO = NODE_SOURCE.lstat()
except FileNotFoundError:
    pytest.skip(
        "Node implementation is absent: test-preparation baseline only, not feature PASS",
        allow_module_level=True,
    )
if (
    not stat.S_ISREG(NODE_SOURCE_INFO.st_mode)
    or getattr(NODE_SOURCE_INFO, "st_file_attributes", 0)
    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    or not NODE_SOURCE.resolve().is_relative_to(ROOT.resolve())
):
    raise ImportError("Node source is not a regular checkout module")

import aiflow
import aiflow.node_verification as node_checkout

if (
    aiflow.__file__ is None
    or Path(aiflow.__file__).resolve() != (ROOT / "src/aiflow/__init__.py").resolve()
    or node_checkout.__file__ is None
    or Path(node_checkout.__file__).resolve() != NODE_SOURCE.resolve()
):
    raise ImportError("Node contracts were not imported from this tested checkout")

import aiflow.approval as approval
import aiflow.cli as cli
import aiflow.gate as gate
import aiflow.policy as policy_module
import aiflow.process_runner as process_runner
import aiflow.status_service as status_service
import aiflow.verification_service as verification_service
from aiflow.contracts import validate_contract
from aiflow.errors import AiflowError
from aiflow.evidence import validate_node_evidence
from aiflow.freshness import evaluate_freshness
from aiflow.policy import POLICY_FILES, PolicyBundle, load_policy_bundle
from aiflow.verification_level import determine_verification_level

CHECKS = (
    ("contract", 30),
    ("scope", 30),
    ("smoke", 30),
    ("node_build", 300),
    ("node_check", 600),
    ("diff_whitespace", 30),
)
LOW_RISK = {
    "mechanical": True,
    "behavior_changed": False,
    "code_modified": False,
    "interaction_scope": "local",
    "regression_risk": False,
    "error_detectability": "high",
}


@pytest.mark.parametrize("level,processes,pure", [("V0", 8, 0), ("V1", 10, 2)])
def test_fixed_node_plan_preserves_process_budget_and_roles(
    tmp_path: Path, node_policy: PolicyBundle, level: str, processes: int, pure: int
) -> None:
    from aiflow.verification import NodePlanBindings, VerificationContext, parse_verification_plan

    bindings = NodePlanBindings(
        "node.exe",
        "npm-cli.js",
        "git.exe",
        tmp_path / "checkout",
        tmp_path / "user.npmrc",
        tmp_path / "global.npmrc",
        tmp_path / "coverage",
        tmp_path / "expected.json",
        tmp_path / "source.json",
    )
    context = VerificationContext(
        tmp_path, "TASK-0001", "a" * 40, "b" * 40, "python.exe", "RUN-001", node_bindings=bindings
    )
    plan = parse_verification_plan(node_policy, context, level=level)
    assert plan.valid
    assert len(plan.executions) == processes
    assert sum(not check.argv for check in plan.checks) == pure
    assert [execution.execution_id for execution in plan.executions] == [
        f"EXEC-{index:03d}" for index in range(1, processes + 1)
    ]
    assert plan.executions[0].argv == (
        "python.exe",
        "-I",
        "-B",
        "-m",
        "aiflow",
        "validate",
        "TASK-0001",
    )
    assert plan.executions[3].argv[-1] == "build"
    assert plan.executions[4].argv[-1] == "check"
    assert all(execution.environment == {} for execution in plan.executions)
    assert all(execution.cwd == tmp_path for execution in plan.executions[:3])
    assert all(execution.cwd == bindings.execution_root for execution in plan.executions[3:5])
    assert plan.executions[7].argv[-4:] == ("--check", "a" * 40, "b" * 40, "--")
    if level == "V1":
        assert plan.executions[8].argv[-2] == "--coverage.reportsDirectory=" + str(
            bindings.coverage_directory
        )
        assert plan.executions[9].timeout_seconds == 30
        assert plan.executions[9].check_ids == ("ts_coverage",)
        assert [check.threshold for check in plan.checks[-2:]] == [85, 90]


@pytest.mark.parametrize("mode", ["missing_bindings", "ci", "v2"])
def test_node_plan_rejects_unavailable_capabilities(
    tmp_path: Path, node_policy: PolicyBundle, mode: str
) -> None:
    from aiflow.verification import VerificationContext, parse_verification_plan

    context = VerificationContext(
        tmp_path,
        "TASK-0001",
        "a" * 40,
        "b" * 40,
        "python.exe",
        "RUN-001",
        ci_run_dir=tmp_path if mode == "ci" else None,
    )
    with pytest.raises(AiflowError):
        parse_verification_plan(node_policy, context, level="V2" if mode == "v2" else "V0")


def test_material_selection_is_rechecked_before_recovery_or_state_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, node_policy: PolicyBundle
) -> None:
    import aiflow.node_execution as execution
    from aiflow.errors import ContractError

    checked = []

    def reject_materials(root, task, selector):
        checked.append((root, task, selector))
        raise ContractError("missing prepared originals", code="NODE_MATERIALS_INVALID")

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid materials reached task recovery or a state write")

    monkeypatch.setattr(verification_service, "load_policy_bundle", lambda *a: node_policy)
    monkeypatch.setattr(
        verification_service, "_classification", lambda *a: {"effective_verification_level": "V0"}
    )
    monkeypatch.setattr(execution, "precheck_node_materials", reject_materials)
    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(verification_service, "evaluate_and_sync_verification_subject", forbidden)
    monkeypatch.setattr(verification_service, "_start_local_verification", forbidden)
    with pytest.raises(AiflowError) as caught:
        verification_service.verify_task(
            tmp_path, "TASK-0001", actor="verifier", node_materials_sha256="a" * 64
        )
    assert caught.value.code == "NODE_MATERIALS_INVALID"
    assert checked == [(tmp_path.resolve(), "TASK-0001", "a" * 64)]


@pytest.mark.parametrize(
    "actor,run_id",
    [
        (None, None),
        ("/private/path", None),
        ("verifier", "../escape"),
        ("verifier", "CON"),
        ("verifier", "occupied"),
    ],
)
def test_invalid_node_run_inputs_reject_before_materials_or_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    node_policy: PolicyBundle,
    actor: str | None,
    run_id: str | None,
) -> None:
    import aiflow.node_execution as execution

    occupied = tmp_path / ".ai/tasks/TASK-0001/logs/occupied"
    occupied.mkdir(parents=True)
    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid Node run inputs reached materials or task recovery")

    monkeypatch.setattr(verification_service, "load_policy_bundle", lambda *a: node_policy)
    monkeypatch.setattr(
        verification_service, "_classification", lambda *a: {"effective_verification_level": "V0"}
    )
    monkeypatch.setattr(execution, "precheck_node_materials", forbidden)
    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    with pytest.raises(AiflowError):
        verification_service.verify_task(
            tmp_path, "TASK-0001", actor=actor, run_id=run_id, node_materials_sha256="a" * 64
        )
    assert {path.relative_to(tmp_path) for path in tmp_path.rglob("*")} == before


@pytest.fixture
def policies(tmp_path: Path) -> Path:
    directory = tmp_path / "policy"
    directory.mkdir()
    for name in POLICY_FILES:
        document = yaml.safe_load((ROOT / ".ai/policy" / name).read_text(encoding="utf-8"))
        document["policy_version"] = "3.1.0"
        if name == "verification-levels.yaml":
            document = {
                "schema_version": "1.0",
                "policy_version": "3.1.0",
                "policy_kind": "verification_levels",
                "profile": {"id": "agent-bridge-node", "revision": 1},
                "levels": [
                    {
                        "id": "V0",
                        "checks": [
                            {"id": name, "required": True, "timeout_seconds": timeout}
                            for name, timeout in CHECKS
                        ],
                    },
                    {
                        "id": "V1",
                        "checks": [
                            *[
                                {"id": name, "required": True, "timeout_seconds": timeout}
                                for name, timeout in CHECKS
                            ],
                            {"id": "ts_coverage", "required": True, "timeout_seconds": 600},
                            {
                                "id": "ts_total_lines",
                                "required": True,
                                "timeout_seconds": 30,
                                "threshold": 85,
                            },
                            {
                                "id": "ts_diff_lines",
                                "required": True,
                                "timeout_seconds": 30,
                                "threshold": 90,
                            },
                        ],
                    },
                ],
            }
        (directory / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return directory


@pytest.fixture
def node_policy(tmp_path: Path, policies: Path) -> PolicyBundle:
    return load_policy_bundle(tmp_path, policy_directory=policies)


def test_node_policy_accepts_exact_profile_and_selects_v0(node_policy: PolicyBundle) -> None:
    assert node_policy.policy_version == "3.1.0"
    assert node_policy.documents["verification-levels.yaml"]["profile"] == {
        "id": "agent-bridge-node",
        "revision": 1,
    }
    unit = {"decision_unit_id": "DU-001", "change_characteristics": LOW_RISK}
    assert determine_verification_level(unit, node_policy).level == "V0"


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "reordered", "timeout", "bool_timeout", "required", "extra"]
)
def test_node_policy_rejects_invalid_checks(tmp_path: Path, policies: Path, change: str) -> None:
    path = policies / "verification-levels.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    checks = document["levels"][0]["checks"]
    if change == "missing":
        checks.pop()
    elif change == "duplicate":
        checks[1] = deepcopy(checks[0])
    elif change == "reordered":
        checks.reverse()
    elif change == "timeout":
        checks[0]["timeout_seconds"] += 1
    elif change == "bool_timeout":
        checks[0]["timeout_seconds"] = True
    elif change == "required":
        checks[0]["required"] = False
    else:
        checks[0]["command"] = ["unexpected"]
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(AiflowError):
        load_policy_bundle(tmp_path, policy_directory=policies)


@pytest.mark.parametrize(
    "change", ["profile_extra", "bool_revision", "document_extra", "other_profile"]
)
def test_node_policy_rejects_extra_fields_and_invalid_profile(
    tmp_path: Path, policies: Path, change: str
) -> None:
    name = "routing.yaml" if change == "other_profile" else "verification-levels.yaml"
    path = policies / name
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if change == "profile_extra":
        document["profile"]["extra"] = True
    elif change == "bool_revision":
        document["profile"]["revision"] = True
    elif change == "document_extra":
        document["unexpected"] = True
    else:
        document["profile"] = {"id": "agent-bridge-node", "revision": 1}
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(AiflowError):
        load_policy_bundle(tmp_path, policy_directory=policies)


def test_legacy_python_levels_and_invalid_node_v2_do_not_downgrade(
    tmp_path: Path,
    node_policy: PolicyBundle,
) -> None:
    legacy = load_policy_bundle(ROOT)
    unit = {"decision_unit_id": "DU-001", "change_characteristics": LOW_RISK}
    assert legacy.policy_version.startswith("2.")
    assert determine_verification_level(unit, legacy).level == "V0"
    v2_unit = {**unit, "verification_requirements": {"acceptance_required": True}}
    assert determine_verification_level(v2_unit, legacy).level == "V2"
    v1_dir = tmp_path / "legacy-v1"
    v1_dir.mkdir()
    for name, original in legacy.documents.items():
        document = deepcopy(original)
        document["policy_version"] = "1.0.0"
        if name == "verification-levels.yaml":
            document["levels"] = document["levels"][:2]
        (v1_dir / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    legacy_v1 = load_policy_bundle(tmp_path, policy_directory=v1_dir)
    assert legacy_v1.policy_version == "1.0.0"
    assert determine_verification_level(unit, legacy_v1).level == "V0"
    invalid = deepcopy(node_policy.documents)
    invalid["verification-levels.yaml"]["profile"]["revision"] = 2
    decision = determine_verification_level(
        v2_unit, PolicyBundle(invalid, node_policy.policy_version, node_policy.sha256)
    )
    assert decision.level == "V2"
    assert decision.blocking_reasons


@pytest.fixture
def unshipped_node_evidence() -> dict:
    h, commit, tree = "a" * 64, "b" * 40, "c" * 40
    root = dict(
        identity_sha256=h,
        head=commit,
        tree=tree,
        index_sha256=h,
        before_sha256=h,
        after_sha256=h,
        authorized_paths=[],
    )
    binding = {
        "profile": {"id": "node-v0", "revision": 1},
        "subject_tree": tree,
        "original_root": deepcopy(root),
        "isolated_root": deepcopy(root),
        "tracked_inputs": [
            {"path": "package-lock.json", "git_blob": commit, "sha256": h},
            {"path": "package.json", "git_blob": commit, "sha256": h},
        ],
        "installed_inputs": [],
        "toolchain": {
            "platform": {"os": "windows", "arch": "x64"},
            "node_version": "1.2.3",
            "npm_version": "1.2.3",
            "node_source": "node_installation",
            "npm_source": "node_installation",
            "node_sha256": h,
            "npm_installation_sha256": h,
            "python_sha256": h,
            "git_sha256": h,
            "aiflow_runtime_sha256": h,
            "package_manager": "npm@1.2.3",
            "executed_tools": [
                {
                    "role": "script_shell",
                    "root_role": "system",
                    "relative_path": "bin/shell",
                    "object_identity_sha256": h,
                    "content_sha256": h,
                    "source": "system",
                    "version": "1",
                }
            ],
            "runtime_materials": [],
        },
        "environment_sha256": h,
        "semantic_contract_sha256": h,
        "execution_contract_sha256": h,
    }
    npm = ["N", "M", "--userconfig", "U", "--globalconfig", "C", "--offline", "run"]
    git = [
        "G",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "diff",
        "--no-ext-diff",
        "--no-textconv",
    ]
    commands = [
        [["P", "-m", "aiflow", "validate", "T"]],
        [["P", "-m", "aiflow", "scope", "T"]],
        [["P", "-m", "aiflow", "--help"]],
        [npm + ["check"]],
        [npm + ["build"]],
        [
            git + ["--check", "--"],
            git + ["--cached", "--check", "--"],
            git + ["--check", "B", "S", "--"],
        ],
    ]
    checks = []
    for (name, timeout), executions in zip(CHECKS, commands, strict=True):
        checks.append(
            {
                "check_id": name,
                "required": True,
                "status": "passed",
                "executions": [
                    {
                        "argv_template": argv,
                        "cwd_role": "isolated" if name.startswith("node_") else "original",
                        "timeout_seconds": timeout,
                        "returncode": 0,
                        "timed_out": False,
                        "stdout_bytes": 0,
                        "stderr_bytes": 0,
                        "stdout_sha256": h,
                        "stderr_sha256": h,
                        "stdout_raw_ref": "raw/stdout",
                        "stderr_raw_ref": "raw/stderr",
                        "stdout_log_ref": "log/stdout",
                        "stderr_log_ref": "log/stderr",
                        "stdout_overflow": False,
                        "stderr_overflow": False,
                        "cleanup": "confirmed",
                    }
                    for argv in executions
                ],
            }
        )
    return {
        "schema_version": "3.0",
        "task_id": "TASK-0001",
        "decision_unit_ids": ["DU-001"],
        "repository_id": "12345678-1234-1234-1234-123456789abc",
        "branch": "branch",
        "base_commit": commit,
        "subject_commit": commit,
        "spec_sha256": h,
        "policy_sha256": h,
        "classification_input_sha256": h,
        "verification_level": "V0",
        "mode": "local",
        "checks": checks,
        "unverified_scenarios": [],
        "conclusion": "passed",
        "generated_at": "2026-10-30T00:00:00Z",
        "reproduce_command": ["aiflow", "verify"],
        "node_binding": binding,
        "node_binding_sha256": "60cf7592b82b3384260dc7e6637984d81b33b641f2e462aaa0abe4c00faf7ea0",
    }


@pytest.mark.parametrize(
    "options", [{}, {"check_ids": ("contract",)}, {"abandon": True}, {"finalize": True}]
)
def test_node_ci_service_rejects_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, node_policy: PolicyBundle, options: dict
) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("Node CI reached a forbidden execution or finalize/abandon path")

    before = {
        path.relative_to(tmp_path): path.read_bytes() if path.is_file() else None
        for path in tmp_path.rglob("*")
    }
    monkeypatch.setattr(
        verification_service,
        "read_task_record_strict",
        lambda *a, **k: SimpleNamespace(task={"current_state": "VERIFIED"}),
    )
    monkeypatch.setattr(
        verification_service, "_ci_paths", lambda *a, **k: (tmp_path / "run", tmp_path / "out")
    )
    monkeypatch.setattr(verification_service, "_classification", lambda *a, **k: {})
    monkeypatch.setattr(verification_service, "load_policy_bundle", lambda *a, **k: node_policy)
    monkeypatch.setattr(verification_service, "_abandon_interrupted_verification", forbidden)
    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(verification_service, "run_execution", forbidden)
    monkeypatch.setattr(verification_service, "run_node_process", forbidden, raising=False)
    monkeypatch.setattr(process_runner, "run_node_process", forbidden)
    monkeypatch.setattr(verification_service, "save_evidence", forbidden)
    with pytest.raises(AiflowError):
        verification_service.verify_task(tmp_path, "TASK-0001", ci=True, **options)
    after = {
        path.relative_to(tmp_path): path.read_bytes() if path.is_file() else None
        for path in tmp_path.rglob("*")
    }
    assert after == before


def test_node_gate_rejects_external_evidence_before_loading_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, node_policy: PolicyBundle
) -> None:
    monkeypatch.setattr(gate, "read_task_record_strict", lambda *a, **k: SimpleNamespace(task={}))
    monkeypatch.setattr(gate, "collect_git_context", lambda *a, **k: None)
    monkeypatch.setattr(gate, "read_task_json", lambda *a, **k: {})
    monkeypatch.setattr(gate, "load_policy_bundle", lambda *a, **k: node_policy)

    def forbidden(*args, **kwargs):
        pytest.fail("Node gate attempted to load external evidence")

    monkeypatch.setattr(gate, "resolve_task_path", forbidden)
    with pytest.raises(AiflowError):
        gate.evaluate_gate(tmp_path, "TASK-0001", evidence_path=tmp_path / "external.json")


@pytest.fixture
def legacy_evidence() -> dict:
    return json.loads((ROOT / "tests/fixtures/contracts/valid/evidence.json").read_text("utf-8"))


@pytest.mark.parametrize("consumer", ["freshness", "status"])
def test_unverified_node_policy_cannot_present_legacy_evidence_as_fresh_or_passed(
    legacy_evidence: dict,
    consumer: str,
) -> None:
    # This guard is intentionally conservative until current Node objects can be revalidated.
    current = {**legacy_evidence, "governance_only": True, "node_policy": True}
    if consumer == "freshness":
        assert evaluate_freshness("evidence", legacy_evidence, current).status != "fresh"
    else:
        assert status_service._evidence_status(legacy_evidence, current) != "passed"
    current["node_policy"] = False
    if consumer == "freshness":
        assert evaluate_freshness("evidence", legacy_evidence, current).status == "fresh"
    else:
        assert status_service._evidence_status(legacy_evidence, current) == "passed"


@pytest.mark.parametrize("failure", ["missing", "damaged", "unsupported"])
def test_marker_preserved_when_policy_cannot_be_trusted(
    tmp_path: Path, policies: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    # Pending reviewed specification: Node/unknown Policy cannot authorize marker recovery.
    target = tmp_path / ".ai/policy"
    shutil.copytree(policies, target)
    path = target / "verification-levels.yaml"
    if failure == "missing":
        path.unlink()
    elif failure == "damaged":
        path.write_text(": [broken", encoding="utf-8")
    else:
        for policy_file in target.glob("*.yaml"):
            document = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
            document["policy_version"] = "4.0.0"
            policy_file.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    marker = tmp_path / approval.APPROVAL_MARKER
    marker.write_bytes(b'{"synthetic":true}')

    def forbidden(*args, **kwargs):
        pytest.fail("Untrusted Policy reached persistent approval recovery")

    monkeypatch.setattr(
        approval, "resolve_task_path", lambda *a: tmp_path if len(a) == 2 else marker
    )
    monkeypatch.setattr(approval, "_complete_marker", forbidden)
    monkeypatch.setattr(approval, "atomic_write_json", forbidden)
    try:
        with pytest.raises(AiflowError):
            approval.approve_task(
                tmp_path, "TASK-0001", approval_type="code", actor="reviewer", reason="test"
            )
    finally:
        assert marker.read_bytes() == b'{"synthetic":true}'


@pytest.mark.parametrize("major", [1, 2])
def test_valid_python_policy_still_routes_marker_to_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, major: int
) -> None:
    target = tmp_path / ".ai/policy"
    shutil.copytree(ROOT / ".ai/policy", target)
    if major == 1:
        for policy_file in target.glob("*.yaml"):
            document = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
            document["policy_version"] = "1.0.0"
            if policy_file.name == "verification-levels.yaml":
                document["levels"] = document["levels"][:2]
            policy_file.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    marker = tmp_path / approval.APPROVAL_MARKER
    marker.write_bytes(b'{"synthetic":true}')
    sentinel = object()
    calls = []

    def recover(root, task_id):
        calls.append((root, task_id))
        return sentinel

    monkeypatch.setattr(
        approval, "resolve_task_path", lambda *a: tmp_path if len(a) == 2 else marker
    )
    monkeypatch.setattr(approval, "_complete_marker", recover)
    assert (
        approval.approve_task(
            tmp_path, "TASK-0001", approval_type="code", actor="reviewer", reason="test"
        )
        is sentinel
    )
    assert calls == [(tmp_path, "TASK-0001")]
    assert marker.read_bytes() == b'{"synthetic":true}'


def test_node_local_v2_finalize_rejects_before_evidence_or_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, node_policy: PolicyBundle
) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("Node V2 finalization attempted evidence access or persistence")

    monkeypatch.setattr(
        verification_service, "load_task_record", lambda *a: SimpleNamespace(task={}, events=[])
    )
    monkeypatch.setattr(
        verification_service, "_classification", lambda *a: {"effective_verification_level": "V2"}
    )
    monkeypatch.setattr(verification_service, "load_policy_bundle", lambda *a: node_policy)
    monkeypatch.setattr(verification_service, "_read_spec", forbidden)
    monkeypatch.setattr(verification_service, "save_evidence", forbidden)
    with pytest.raises(AiflowError):
        verification_service.verify_task(tmp_path, "TASK-0001", actor="reviewer", finalize=True)


@pytest.mark.parametrize("entrypoint", ["service", "cli"])
@pytest.mark.parametrize("kind", ["directory", "dangling_link", "special"])
def test_nonregular_approval_marker_is_rejected_and_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entrypoint: str, kind: str
) -> None:
    marker = tmp_path / approval.APPROVAL_MARKER
    injected = False
    if kind == "directory":
        marker.mkdir()
        (marker / "keep").write_bytes(b"preserve directory entry")
    elif kind == "dangling_link":
        try:
            marker.symlink_to("missing-target")
        except OSError:
            marker.write_bytes(b"synthetic link stand-in")
            injected = True
    else:
        marker.write_bytes(b"synthetic special-file stand-in")
        injected = True
    if injected:
        original_lstat = Path.lstat
        simulated_mode = stat.S_IFLNK if kind == "dangling_link" else stat.S_IFIFO

        def simulated_lstat(path, *args, **kwargs):
            if path == marker:
                return SimpleNamespace(st_mode=simulated_mode, st_file_attributes=0)
            return original_lstat(path, *args, **kwargs)

        monkeypatch.setattr(Path, "lstat", simulated_lstat)

    def forbidden(*args, **kwargs):
        pytest.fail("Nonregular marker reached approval recovery or persistence")

    monkeypatch.setattr(
        approval, "resolve_task_path", lambda _root, _task, *parts: tmp_path.joinpath(*parts)
    )
    monkeypatch.setattr(approval, "load_task_record", forbidden)
    monkeypatch.setattr(approval, "load_policy_bundle", forbidden)
    monkeypatch.setattr(approval, "_complete_marker", forbidden)
    monkeypatch.setattr(approval, "atomic_write_json", forbidden)
    if entrypoint == "service":
        with pytest.raises(AiflowError):
            approval.approve_task(
                tmp_path, "TASK-0001", approval_type="code", actor="reviewer", reason="test"
            )
    else:
        monkeypatch.setattr(cli, "resolve_repository_root", lambda _path: tmp_path)
        assert (
            cli.main(
                [
                    "approve",
                    "TASK-0001",
                    "--type",
                    "code",
                    "--actor",
                    "reviewer",
                    "--reason",
                    "test",
                ]
            )
            != 0
        )
    if kind == "directory":
        assert marker.is_dir() and (marker / "keep").read_bytes() == b"preserve directory entry"
    elif kind == "dangling_link" and not injected:
        assert marker.is_symlink() and marker.readlink() == Path("missing-target")
    else:
        expected = (
            b"synthetic link stand-in"
            if kind == "dangling_link"
            else b"synthetic special-file stand-in"
        )
        assert marker.read_bytes() == expected


@pytest.mark.parametrize("entrypoint", ["verify", "finalize", "abandon", "direct_finalize"])
@pytest.mark.parametrize("major", [1, 2])
def test_legacy_python_verification_can_reach_existing_recovery_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entrypoint: str, major: int
) -> None:
    legacy = load_policy_bundle(ROOT)
    assert legacy.policy_version.startswith("2.")
    if major == 1:
        target = tmp_path / "legacy-v1"
        target.mkdir()
        for name, original in legacy.documents.items():
            document = deepcopy(original)
            document["policy_version"] = "1.0.0"
            if name == "verification-levels.yaml":
                document["levels"] = document["levels"][:2]
            (target / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        legacy = load_policy_bundle(tmp_path, policy_directory=target)

    class RecoveryReadReached(Exception):
        pass

    def reached(*args, **kwargs):
        raise RecoveryReadReached

    monkeypatch.setattr(verification_service, "load_policy_bundle", lambda *a: legacy)
    monkeypatch.setattr(verification_service, "load_task_record", reached)
    monkeypatch.setattr(verification_service, "_abandon_interrupted_verification", reached)
    with pytest.raises(RecoveryReadReached):
        if entrypoint == "direct_finalize":
            verification_service._finalize_v2_task(
                tmp_path,
                "TASK-0001",
                actor="reviewer",
                check_ids=(),
                ci=False,
                ci_run_dir=None,
                output=None,
            )
        else:
            verification_service.verify_task(
                tmp_path,
                "TASK-0001",
                actor="reviewer",
                finalize=entrypoint == "finalize",
                abandon=entrypoint == "abandon",
                reason="synthetic",
            )


@pytest.mark.parametrize("failure", ["missing", "damaged", "unsupported"])
@pytest.mark.parametrize("entrypoint", ["verify", "finalize", "abandon", "direct_finalize"])
def test_verification_with_untrusted_policy_rejects_before_recovery(
    tmp_path: Path, policies: Path, monkeypatch: pytest.MonkeyPatch, failure: str, entrypoint: str
) -> None:
    target = tmp_path / ".ai/policy"
    shutil.copytree(policies, target)
    path = target / "verification-levels.yaml"
    if failure == "missing":
        path.unlink()
    elif failure == "damaged":
        path.write_text(": [broken", encoding="utf-8")
    else:
        for policy_file in target.glob("*.yaml"):
            document = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
            document["policy_version"] = "4.0.0"
            policy_file.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    task = tmp_path / ".ai/tasks/TASK-0001/task.json"
    task.parent.mkdir(parents=True)
    task.write_bytes(b"synthetic task before recovery")
    event = task.parent / "events.jsonl"
    event.write_bytes(b"synthetic event before recovery")

    def forbidden(*args, **kwargs):
        pytest.fail("Untrusted Policy reached a verification recovery read or write")

    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(verification_service, "read_task_record_strict", forbidden)
    monkeypatch.setattr(verification_service, "_abandon_interrupted_verification", forbidden)
    monkeypatch.setattr(verification_service, "save_evidence", forbidden)
    try:
        with pytest.raises(AiflowError):
            if entrypoint == "direct_finalize":
                verification_service._finalize_v2_task(
                    tmp_path,
                    "TASK-0001",
                    actor="reviewer",
                    check_ids=(),
                    ci=False,
                    ci_run_dir=None,
                    output=None,
                )
            else:
                verification_service.verify_task(
                    tmp_path,
                    "TASK-0001",
                    actor="reviewer",
                    finalize=entrypoint == "finalize",
                    abandon=entrypoint == "abandon",
                    reason="synthetic",
                )
    finally:
        assert task.read_bytes() == b"synthetic task before recovery"
        assert event.read_bytes() == b"synthetic event before recovery"


@pytest.mark.parametrize("failure", ["missing", "damaged", "unsupported"])
@pytest.mark.parametrize("entrypoint", ["service", "cli"])
def test_approval_without_marker_rejects_untrusted_policy_before_task_read(
    tmp_path: Path, policies: Path, monkeypatch: pytest.MonkeyPatch, failure: str, entrypoint: str
) -> None:
    target = tmp_path / ".ai/policy"
    shutil.copytree(policies, target)
    shutil.copytree(ROOT / ".ai/schemas", tmp_path / ".ai/schemas")
    path = target / "verification-levels.yaml"
    if failure == "missing":
        path.unlink()
    elif failure == "damaged":
        path.write_text(": [broken", encoding="utf-8")
    else:
        for policy_file in target.glob("*.yaml"):
            document = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
            document["policy_version"] = "4.0.0"
            policy_file.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    task = tmp_path / "task.json"
    event = tmp_path / "events.jsonl"
    task.write_bytes(b"synthetic task before approval")
    event.write_bytes(b"synthetic event before approval")
    marker = tmp_path / approval.APPROVAL_MARKER
    assert not marker.exists()

    def forbidden(*args, **kwargs):
        pytest.fail("Untrusted Policy reached an approval task read or write")

    monkeypatch.setattr(
        approval, "resolve_task_path", lambda _root, _task, *parts: tmp_path.joinpath(*parts)
    )
    monkeypatch.setattr(approval, "load_task_record", forbidden)
    monkeypatch.setattr(approval, "read_task_record_strict", forbidden)
    monkeypatch.setattr(approval, "_complete_marker", forbidden)
    monkeypatch.setattr(approval, "atomic_write_json", forbidden)
    try:
        if entrypoint == "service":
            with pytest.raises(AiflowError):
                approval.approve_task(
                    tmp_path, "TASK-0001", approval_type="code", actor="reviewer", reason="test"
                )
        else:
            monkeypatch.setattr(cli, "resolve_repository_root", lambda _path: tmp_path)
            assert (
                cli.main(
                    [
                        "approve",
                        "TASK-0001",
                        "--type",
                        "code",
                        "--actor",
                        "reviewer",
                        "--reason",
                        "test",
                    ]
                )
                != 0
            )
    finally:
        assert task.read_bytes() == b"synthetic task before approval"
        assert event.read_bytes() == b"synthetic event before approval"
        assert not marker.exists()


@pytest.mark.parametrize("entrypoint", ["service", "cli"])
def test_approval_without_marker_allows_valid_python_recovery_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entrypoint: str
) -> None:
    legacy = load_policy_bundle(ROOT)
    assert legacy.policy_version.startswith("2.")

    class RecoveryReadReached(Exception):
        pass

    def reached(*args, **kwargs):
        raise RecoveryReadReached

    def forbidden(*args, **kwargs):
        pytest.fail("Legacy approval did not use its existing recovery-capable reader")

    monkeypatch.setattr(
        approval, "resolve_task_path", lambda _root, _task, *parts: tmp_path.joinpath(*parts)
    )
    monkeypatch.setattr(approval, "load_policy_bundle", lambda *a: legacy)
    monkeypatch.setattr(approval, "load_task_record", reached)
    monkeypatch.setattr(approval, "read_task_record_strict", forbidden)
    with pytest.raises(RecoveryReadReached):
        if entrypoint == "service":
            approval.approve_task(
                tmp_path, "TASK-0001", approval_type="code", actor="reviewer", reason="test"
            )
        else:
            monkeypatch.setattr(cli, "resolve_repository_root", lambda _path: tmp_path)
            cli.main(
                [
                    "approve",
                    "TASK-0001",
                    "--type",
                    "code",
                    "--actor",
                    "reviewer",
                    "--reason",
                    "test",
                ]
            )


@pytest.fixture(params=["schema_error", "schema_invalid"])
def node_with_unavailable_revalidation(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, node_policy: PolicyBundle
) -> PolicyBundle:
    # The bundle was loaded successfully; a later schema reread fails or rejects it.
    def revalidate(*args, **kwargs):
        if request.param == "schema_error":
            raise OSError("synthetic second schema read failure")
        return ["synthetic schema validation failure"]

    monkeypatch.setattr(policy_module, "validate_contract", revalidate)
    return node_policy


@pytest.mark.parametrize("entrypoint", ["verify", "finalize", "abandon", "direct_finalize"])
def test_node_candidate_never_reaches_verification_recovery_on_failed_revalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    node_with_unavailable_revalidation: PolicyBundle,
    entrypoint: str,
) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("Node candidate reached recovery-capable verification")

    monkeypatch.setattr(
        verification_service, "load_policy_bundle", lambda *a: node_with_unavailable_revalidation
    )
    monkeypatch.setattr(verification_service, "load_task_record", forbidden)
    monkeypatch.setattr(verification_service, "_abandon_interrupted_verification", forbidden)
    monkeypatch.setattr(verification_service, "save_evidence", forbidden)
    with pytest.raises(AiflowError):
        if entrypoint == "direct_finalize":
            verification_service._finalize_v2_task(
                tmp_path,
                "TASK-0001",
                actor="reviewer",
                check_ids=(),
                ci=False,
                ci_run_dir=None,
                output=None,
            )
        else:
            verification_service.verify_task(
                tmp_path,
                "TASK-0001",
                actor="reviewer",
                finalize=entrypoint == "finalize",
                abandon=entrypoint == "abandon",
                reason="synthetic",
            )


@pytest.mark.parametrize("has_marker", [False, True])
def test_node_candidate_never_reaches_approval_recovery_on_failed_revalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    node_with_unavailable_revalidation: PolicyBundle,
    has_marker: bool,
) -> None:
    marker = tmp_path / approval.APPROVAL_MARKER
    if has_marker:
        marker.write_bytes(b"preserve synthetic marker")

    def forbidden(*args, **kwargs):
        pytest.fail("Node candidate reached recovery-capable approval")

    monkeypatch.setattr(
        approval, "resolve_task_path", lambda _root, _task, *parts: tmp_path.joinpath(*parts)
    )
    monkeypatch.setattr(
        approval, "load_policy_bundle", lambda *a: node_with_unavailable_revalidation
    )
    monkeypatch.setattr(approval, "load_task_record", forbidden)
    monkeypatch.setattr(
        approval, "read_task_record_strict", lambda *a: SimpleNamespace(task={}, events=[])
    )
    monkeypatch.setattr(approval, "_complete_marker", forbidden)
    monkeypatch.setattr(approval, "atomic_write_json", forbidden)
    with pytest.raises(AiflowError):
        approval.approve_task(
            tmp_path, "TASK-0001", approval_type="code", actor="reviewer", reason="test"
        )
    if has_marker:
        assert marker.read_bytes() == b"preserve synthetic marker"


@pytest.mark.parametrize("external", [False, True])
def test_node_candidate_gate_rejects_on_failed_revalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    node_with_unavailable_revalidation: PolicyBundle,
    external: bool,
) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("Node candidate gate fell through to legacy evidence")

    monkeypatch.setattr(gate, "read_task_record_strict", lambda *a: SimpleNamespace(task={}))
    monkeypatch.setattr(gate, "collect_git_context", lambda *a: None)
    monkeypatch.setattr(gate, "read_task_json", lambda *a, **k: {})
    monkeypatch.setattr(gate, "load_policy_bundle", lambda *a: node_with_unavailable_revalidation)
    monkeypatch.setattr(gate, "resolve_task_path", forbidden)
    with pytest.raises(AiflowError):
        gate.evaluate_gate(
            tmp_path, "TASK-0001", evidence_path=tmp_path / "external.json" if external else None
        )


def test_node_candidate_status_is_not_passed_on_failed_revalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    node_with_unavailable_revalidation: PolicyBundle,
    legacy_evidence: dict,
) -> None:
    monkeypatch.setattr(
        status_service, "load_policy_bundle", lambda *a: node_with_unavailable_revalidation
    )
    monkeypatch.setattr(status_service, "resolve_task_path", lambda *a: tmp_path / "missing-spec")
    monkeypatch.setattr(status_service, "parse_decision_units", lambda *a: [])
    facts = status_service._current_facts(
        tmp_path, "TASK-0001", {}, observed_head="a" * 40, classification=None, events=()
    )
    assert facts["node_policy"] is True
    current = {**legacy_evidence, "governance_only": True, "node_policy": facts["node_policy"]}
    assert status_service._evidence_status(legacy_evidence, current) != "passed"


@pytest.mark.parametrize("require_passed", [False, True])
def test_unshipped_30_evidence_is_rejected(
    unshipped_node_evidence: dict, require_passed: bool
) -> None:
    assert unshipped_node_evidence["schema_version"] == "3.0"
    assert validate_contract("evidence", unshipped_node_evidence)
    with pytest.raises(AiflowError):
        validate_node_evidence(unshipped_node_evidence, require_passed=require_passed)


def test_unshipped_30_policy_is_rejected(tmp_path: Path, policies: Path) -> None:
    for path in policies.glob("*.yaml"):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        document["policy_version"] = "3.0.0"
        if path.name == "verification-levels.yaml":
            document["profile"] = {"id": "node-v0", "revision": 1}
            document["levels"] = document["levels"][:1]
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(AiflowError):
        load_policy_bundle(tmp_path, policy_directory=policies)


def _node_service_claim(facts, *, outcome: str) -> dict:
    """Public-only claims for refusal tests; never stand in for real execution."""
    import hashlib

    from aiflow.evidence import _node_digest, _node_evidence_plan

    plan = _node_evidence_plan("V0")
    checks = []
    for index, check in enumerate(plan["checks"]):
        executions = []
        if outcome == "passed" or outcome == "failed" and index == 0:
            for fixed in plan["executions"]:
                if fixed["check_ids"] != [check["check_id"]]:
                    continue
                execution = {key: value for key, value in fixed.items() if key != "check_ids"}
                execution.update(
                    returncode=0 if outcome == "passed" else 1,
                    timed_out=False,
                    duration_ms=1,
                    stdout_overflow=False,
                    stderr_overflow=False,
                    cleanup="confirmed",
                    execution_error=False,
                )
                for stream in ("stdout", "stderr"):
                    prefix = f"logs/{facts.run_id}/node/raw/{fixed['execution_id']}/{stream}"
                    execution[stream] = {
                        "bytes": 0,
                        "sha256": hashlib.sha256(b"").hexdigest(),
                        "raw_ref": prefix + ".raw",
                        "log_ref": prefix + ".log",
                    }
                executions.append(execution)
        checks.append(
            {
                "check_id": check["check_id"],
                "required": True,
                "status": outcome if executions else "unverified",
                "executions": executions,
            }
        )
    binding = {
        "profile": {"id": "agent-bridge-node", "revision": 1},
        "subject_tree": "c" * 40,
        "prepared": {
            "ref": f"logs/node-prepared/{'d' * 64}/prepared.json",
            "size": 1,
            "sha256": "d" * 64,
        },
        "run": {"ref": f"logs/{facts.run_id}/node/run.json", "size": 1, "sha256": "e" * 64},
        "materials_sha256": "f" * 64,
        "semantic_contract_sha256": "a" * 64,
        "execution_contract_sha256": _node_digest(plan),
        "environment_sha256": "b" * 64,
        "coverage": None,
    }
    value = {
        "schema_version": "3.1",
        **{
            key: getattr(facts, key)
            for key in (
                "task_id",
                "repository_id",
                "branch",
                "base_commit",
                "subject_commit",
                "spec_sha256",
                "policy_sha256",
                "classification_input_sha256",
                "verification_level",
                "mode",
                "generated_at",
            )
        },
        "decision_unit_ids": list(facts.decision_unit_ids),
        "checks": checks,
        "unverified_scenarios": [
            row["check_id"] for row in checks if row["status"] == "unverified"
        ],
        "conclusion": "passed" if outcome == "passed" else "failed",
        "reproduce_command": list(facts.reproduce_command),
        "node_binding": binding,
        "node_binding_sha256": _node_digest(binding),
    }
    validate_node_evidence(value)
    assert validate_contract("evidence", value) == []
    return value


@pytest.fixture
def node_service_transaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, node_policy):
    """Trusted state seam plus real evidence files, restricted to negative outcomes."""
    import aiflow.node_execution as runtime
    from aiflow.task_service import TaskRecord
    from aiflow.verification import VerificationContext

    task = json.loads((ROOT / "tests/fixtures/contracts/valid/task.json").read_text("utf-8"))
    task.update(current_state="IMPLEMENTING", base_commit="a" * 40, subject_commit="b" * 40)
    task["decision_units"] = [{"decision_unit_id": "DU-001"}]
    record = TaskRecord(task, ())
    context = VerificationContext(
        tmp_path, "TASK-0001", "a" * 40, "b" * 40, "python", "RUN-negative"
    )
    directory = tmp_path / ".ai/tasks/TASK-0001"
    directory.mkdir(parents=True)
    state_file = directory / "negative-state.json"
    state_file.write_text(json.dumps({"state": "IMPLEMENTING", "events": []}), encoding="utf-8")
    events = []

    def transition(_root, _task, **kwargs):
        events.append(kwargs["event_type"])
        task["current_state"] = kwargs["target_state"]
        state_file.write_text(
            json.dumps({"state": task["current_state"], "events": events}), encoding="utf-8"
        )
        return SimpleNamespace(task=dict(task))

    monkeypatch.setattr(verification_service, "transition_task_record", transition)
    monkeypatch.setattr(
        runtime,
        "recheck_node_evidence",
        lambda *args: runtime.NodeEvidenceFacts(
            False, False, ("NODE_MATERIALS_UNAVAILABLE",), None, None, None
        ),
    )
    arguments = dict(
        root=tmp_path,
        task_id="TASK-0001",
        actor="reviewer",
        context=context,
        bundle=node_policy,
        record=record,
        classification={
            "effective_verification_level": "V0",
            "effective_route": "REVIEW",
            "classification_input_sha256": "a" * 64,
        },
        spec_sha256="a" * 64,
        materials="d" * 64,
    )
    return SimpleNamespace(
        arguments=arguments,
        runtime=runtime,
        directory=directory,
        run=directory / "logs/RUN-negative",
        state_file=state_file,
        events=events,
    )


@pytest.mark.parametrize("outcome", ["failed", "unverified"])
def test_node_service_archives_negative_evidence_and_finishes_failed(
    monkeypatch: pytest.MonkeyPatch, node_service_transaction, outcome: str
) -> None:
    seam = node_service_transaction
    produced = []

    def execute(*args, **kwargs):
        value = _node_service_claim(kwargs["facts"], outcome=outcome)
        produced.append(value)
        return value

    monkeypatch.setattr(seam.runtime, "execute_node_verification", execute)
    result = verification_service._verify_node_local(**seam.arguments)
    assert result.conclusion == "failed" and result.state == "FAILED"
    assert result.reason_codes == ("NODE_MATERIALS_UNAVAILABLE",)
    assert seam.events == ["verification_started", "verification_failed"]
    assert json.loads(seam.state_file.read_text("utf-8"))["state"] == "FAILED"
    for path in (seam.directory / "evidence.json", seam.run / "evidence.json"):
        assert json.loads(path.read_text("utf-8")) == produced[0]


@pytest.mark.parametrize("current,passed", [(False, False), (True, False), (False, True)])
def test_node_service_refuses_passed_claim_before_saving_or_finishing(
    monkeypatch: pytest.MonkeyPatch, node_service_transaction, current: bool, passed: bool
) -> None:
    seam = node_service_transaction
    sentinel = seam.directory / "evidence.json"
    sentinel.write_bytes(b"preserve earlier evidence")
    raw = seam.run / "node/raw/failure.txt"

    def execute(*args, **kwargs):
        raw.parent.mkdir(parents=True)
        raw.write_bytes(b"preserve run originals")
        return _node_service_claim(kwargs["facts"], outcome="passed")

    def forbidden(*args, **kwargs):
        pytest.fail("Unrevalidated passed claim reached evidence save or finish")

    monkeypatch.setattr(seam.runtime, "execute_node_verification", execute)
    monkeypatch.setattr(
        seam.runtime,
        "recheck_node_evidence",
        lambda *args: seam.runtime.NodeEvidenceFacts(
            current, passed, ("NODE_EVIDENCE_STALE",), None, None, None
        ),
    )
    monkeypatch.setattr(verification_service, "save_evidence", forbidden)
    monkeypatch.setattr(verification_service, "_finish_local_verification", forbidden)
    with pytest.raises(AiflowError) as caught:
        verification_service._verify_node_local(**seam.arguments)
    assert caught.value.code == "NODE_EVIDENCE_STALE"
    assert seam.events == ["verification_started"]
    assert json.loads(seam.state_file.read_text("utf-8"))["state"] == "VERIFYING"
    assert sentinel.read_bytes() == b"preserve earlier evidence"
    assert raw.read_bytes() == b"preserve run originals"
    assert not (seam.run / "evidence.json").exists()


@pytest.mark.parametrize("phase", ["execute", "save"])
def test_node_service_preserves_interrupted_run_without_claiming_success(
    monkeypatch: pytest.MonkeyPatch, node_service_transaction, phase: str
) -> None:
    import aiflow.evidence as evidence_module
    from aiflow.errors import StorageError

    seam = node_service_transaction
    sentinel = seam.directory / "evidence.json"
    sentinel.write_bytes(b"preserve earlier evidence")
    raw = seam.run / "node/raw/failure.txt"

    def execute(*args, **kwargs):
        raw.parent.mkdir(parents=True)
        raw.write_bytes(b"preserve interrupted run")
        if phase == "execute":
            raise StorageError("synthetic execution interruption", code="NODE_TEST_INTERRUPTED")
        return _node_service_claim(kwargs["facts"], outcome="failed")

    actual_write = evidence_module.atomic_write_json

    def write(path, value):
        if path == sentinel:
            assert (seam.run / "evidence.json").is_file()
            raise StorageError("synthetic current-evidence failure", code="NODE_TEST_INTERRUPTED")
        return actual_write(path, value)

    def forbidden(*args, **kwargs):
        pytest.fail("Interrupted Node run reached a final state")

    monkeypatch.setattr(seam.runtime, "execute_node_verification", execute)
    monkeypatch.setattr(evidence_module, "atomic_write_json", write)
    monkeypatch.setattr(verification_service, "_finish_local_verification", forbidden)
    with pytest.raises(StorageError) as caught:
        verification_service._verify_node_local(**seam.arguments)
    assert caught.value.code == "NODE_TEST_INTERRUPTED"
    assert seam.events == ["verification_started"]
    assert json.loads(seam.state_file.read_text("utf-8"))["state"] == "VERIFYING"
    assert sentinel.read_bytes() == b"preserve earlier evidence"
    assert raw.read_bytes() == b"preserve interrupted run"
    if phase == "save":
        archived = json.loads((seam.run / "evidence.json").read_text("utf-8"))
        validate_node_evidence(archived)
        assert archived["conclusion"] == "failed"
    else:
        assert not (seam.run / "evidence.json").exists()


@pytest.mark.parametrize("abandon", [False, True])
def test_python_service_rejects_node_materials_before_recovery_or_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, abandon: bool
) -> None:
    legacy = load_policy_bundle(ROOT)
    sentinel = tmp_path / "preserve.txt"
    sentinel.write_bytes(b"unrelated caller state")

    def forbidden(*args, **kwargs):
        pytest.fail("Python Node-material input reached task recovery, execution, or writes")

    monkeypatch.setattr(verification_service, "_verification_policy", lambda *args: legacy)
    for name in (
        "load_task_record",
        "read_task_record_strict",
        "_classification",
        "save_evidence",
        "_abandon_interrupted_verification",
        "transition_task_record",
    ):
        monkeypatch.setattr(verification_service, name, forbidden)
    with pytest.raises(AiflowError) as caught:
        verification_service.verify_task(
            tmp_path,
            "TASK-0001",
            actor="reviewer",
            node_materials_sha256="a" * 64,
            abandon=abandon,
            reason="not a Node profile",
        )
    assert caught.value.code == "NODE_MATERIALS_UNEXPECTED"
    assert list(tmp_path.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"unrelated caller state"


@pytest.fixture
def code_marker_values():
    """Pure staged-transaction data; it supplies no execution or Gate evidence."""
    from aiflow.review_service import _context_digest
    from aiflow.state import TRANSITIONS, create_record_event, create_transition_event

    task = json.loads((ROOT / "tests/fixtures/contracts/valid/task.json").read_text("utf-8"))
    task.update(
        subject_commit="2" * 40, frozen_spec_sha256="b" * 64, spec_frozen_at="2026-10-31T00:00:00Z"
    )
    instant = "2026-10-31T00:00:00Z"
    events = [
        create_record_event(
            task,
            event_type="task_created",
            actor="author",
            payload={},
            sequence=1,
            occurred_at=instant,
        )
    ]
    for target in [
        "CLASSIFIED",
        "WAITING_FOR_SPEC_REVIEW",
        "READY_TO_IMPLEMENT",
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "WAITING_FOR_FINAL_REVIEW",
    ]:
        rule = TRANSITIONS[(task["current_state"], target)]
        event = create_transition_event(
            task,
            target_state=target,
            event_type=rule.event_type,
            actor="author",
            payload={},
            sequence=len(events) + 1,
            satisfied_preconditions=rule.preconditions,
            occurred_at=instant,
        )
        events.append(event)
        task = {**task, "current_state": target, "updated_at": instant}
    context = {
        "schema_version": "1.0",
        "review_stage": "implementation",
        "task_id": "TASK-0001",
        "decision_unit_ids": ["DU-001"],
        "repository_id": task["repository_id"],
        "branch": task["branch"],
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "spec_sha256": task["frozen_spec_sha256"],
        "policy_sha256": "c" * 64,
        "classification_input_sha256": "d" * 64,
        "evidence_sha256": "e" * 64,
        "content": {},
    }
    context["context_sha256"] = _context_digest(context)
    review = {
        "schema_version": "1.0",
        "review_id": "REV-0002",
        "revision": 1,
        "task_id": "TASK-0001",
        "review_stage": "implementation",
        "reviewer": "reviewer",
        "recorded_at": instant,
        "context_sha256": context["context_sha256"],
        "outcome": "APPROVE",
        "summary": "Pure marker binding fixture",
        "findings": [],
    }
    reference = {
        key: review[key] for key in ("review_id", "revision", "review_stage", "context_sha256")
    }
    events.append(
        create_record_event(
            task,
            event_type="review_recorded",
            actor="reviewer",
            payload=reference,
            sequence=len(events) + 1,
            occurred_at=instant,
        )
    )
    prior = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "decision_unit_id": "DU-001",
        "approval_type": "spec",
        "actor": "project-owner",
        "reason": "Pure fixture",
        "approved_at": instant,
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "spec_sha256": task["frozen_spec_sha256"],
        "policy_sha256": "c" * 64,
    }
    candidate = {**prior, "approval_type": "code", "evidence_sha256": "e" * 64}
    event = create_transition_event(
        task,
        target_state="APPROVED_FOR_MERGE",
        event_type="code_approved",
        actor="project-owner",
        payload={"approval_type": "code", "approvals": [candidate], "structured_review": reference},
        sequence=len(events) + 1,
        satisfied_preconditions={"code_approval_valid"},
        occurred_at=instant,
    )
    marker = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "task": {**task, "current_state": "APPROVED_FOR_MERGE", "updated_at": instant},
        "event": event,
        "approvals": [prior, candidate],
    }
    return dict(
        marker=marker,
        task_id="TASK-0001",
        current_task=task,
        current_events=events,
        current_approvals=[prior],
        policy_sha256="c" * 64,
        classification_sha256="d" * 64,
        evidence_sha256="e" * 64,
        implementation_review=review,
        review_context=context,
        review_unit_ids={"DU-001"},
    )


@pytest.mark.parametrize("phase", ["pending", "ledger_written", "event_applied"])
def test_pure_node_code_marker_accepts_existing_transaction_phases(
    code_marker_values, phase
) -> None:
    values = code_marker_values
    if phase != "pending":
        values["current_approvals"] = deepcopy(values["marker"]["approvals"])
    if phase == "event_applied":
        values["current_task"] = deepcopy(values["marker"]["task"])
        values["current_events"].append(deepcopy(values["marker"]["event"]))
    approval._validate_node_code_approval_marker(**values)


@pytest.mark.parametrize("stage", ["implementation", "design"])
def test_pending_code_marker_requires_latest_implementation_registration(
    code_marker_values, stage
) -> None:
    from aiflow.state import create_record_event

    values = code_marker_values
    reference = {
        **values["marker"]["event"]["payload"]["structured_review"],
        "review_id": "REV-0003",
        "review_stage": stage,
    }
    values["current_events"].append(
        create_record_event(
            values["current_task"],
            event_type="review_recorded",
            actor="new-reviewer",
            payload=reference,
            sequence=len(values["current_events"]) + 1,
            occurred_at="2026-10-31T00:00:00Z",
        )
    )
    values["marker"]["event"]["sequence"] = len(values["current_events"]) + 1
    if stage == "design":
        approval._validate_node_code_approval_marker(**values)
    else:
        with pytest.raises(AiflowError):
            approval._validate_node_code_approval_marker(**values)


@pytest.mark.parametrize(
    "fault",
    [
        "extra",
        "schema",
        "task",
        "goal",
        "sequence_float",
        "sequence_bool",
        "event_actor",
        "event_type",
        "payload_extra",
        "kind_list",
        "prefix",
        "duplicate",
        "subject",
        "spec",
        "policy",
        "evidence",
        "unit",
        "review_revision_float",
        "registration",
        "review_outcome",
        "context_evidence",
        "context_classification",
        "context_branch",
    ],
)
def test_pure_node_code_marker_rejects_stale_or_malformed_transactions(
    code_marker_values, fault
) -> None:
    from aiflow.review_service import _context_digest

    values = code_marker_values
    marker = values["marker"]
    event = marker["event"]
    candidate = event["payload"]["approvals"][0]
    if fault == "extra":
        marker["unknown"] = True
    elif fault == "schema":
        marker["schema_version"] = "2.0"
    elif fault == "task":
        marker["task_id"] = "TASK-9999"
    elif fault == "goal":
        marker["task"]["goal"] = "unrelated task rewrite"
    elif fault == "sequence_float":
        event["sequence"] = float(event["sequence"])
    elif fault == "sequence_bool":
        event["sequence"] = True
    elif fault == "event_actor":
        event["actor"] = "other"
    elif fault == "event_type":
        event["event_type"] = "approval_recorded"
    elif fault == "payload_extra":
        event["payload"]["unknown"] = True
    elif fault == "kind_list":
        event["payload"]["approval_type"] = []
    elif fault == "prefix":
        marker["approvals"][0] = {**marker["approvals"][0], "reason": "rewritten"}
    elif fault == "duplicate":
        event["payload"]["approvals"].append(deepcopy(candidate))
        marker["approvals"].append(deepcopy(candidate))
    elif fault in {"subject", "spec", "policy", "evidence", "unit"}:
        field = {
            "subject": "subject_commit",
            "spec": "spec_sha256",
            "policy": "policy_sha256",
            "evidence": "evidence_sha256",
            "unit": "decision_unit_id",
        }[fault]
        candidate[field] = "DU-999" if fault == "unit" else "f" * (40 if fault == "subject" else 64)
    elif fault == "review_revision_float":
        event["payload"]["structured_review"]["revision"] = 1.0
    elif fault == "registration":
        values["current_events"][-1]["payload"]["review_id"] = "REV-0999"
    elif fault == "review_outcome":
        values["implementation_review"]["outcome"] = "REQUEST_CHANGES"
    else:
        context = values["review_context"]
        field = {
            "context_evidence": "evidence_sha256",
            "context_classification": "classification_input_sha256",
            "context_branch": "branch",
        }[fault]
        context[field] = "other" if fault == "context_branch" else "f" * 64
        context["context_sha256"] = _context_digest(context)
        values["implementation_review"]["context_sha256"] = context["context_sha256"]
        event["payload"]["structured_review"]["context_sha256"] = context["context_sha256"]
        values["current_events"][-1]["payload"]["context_sha256"] = context["context_sha256"]
    with pytest.raises(AiflowError):
        approval._validate_node_code_approval_marker(**values)


def _other_marker(values, kind):
    from aiflow.state import create_record_event, create_transition_event

    task = dict(values["current_task"])
    prior = deepcopy(values["current_approvals"])
    candidate = deepcopy(prior[0])
    if kind == "spec":
        task["current_state"] = "WAITING_FOR_SPEC_REVIEW"
        events = values["current_events"][:3]
        prior = []
        event = create_transition_event(
            task,
            target_state="READY_TO_IMPLEMENT",
            event_type="spec_approved",
            actor="project-owner",
            payload={"approval_type": "spec", "approvals": [candidate], "structured_review": None},
            sequence=len(events) + 1,
            satisfied_preconditions={"spec_frozen", "spec_approval_valid"},
            occurred_at=task["updated_at"],
        )
    else:
        events = values["current_events"]
        candidate.update(
            approval_type="action",
            action_sha256="a" * 64,
            expires_at="2050-01-01T00:00:00Z",
            single_use=True,
        )
        event = create_record_event(
            task,
            event_type="approval_recorded",
            actor="project-owner",
            payload={"approval_type": "action", "approvals": [candidate]},
            sequence=len(events) + 1,
            occurred_at=task["updated_at"],
        )
    marker = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "task": {**task, "current_state": event["to_state"], "updated_at": event["occurred_at"]},
        "event": event,
        "approvals": [*prior, candidate],
    }
    return marker, task, events, prior


@pytest.mark.parametrize("kind", ["spec", "action"])
def test_node_marker_envelope_preserves_other_existing_approval_types(
    code_marker_values, kind
) -> None:
    marker, task, events, prior = _other_marker(code_marker_values, kind)
    arguments = dict(
        task_id="TASK-0001", current_task=task, current_events=events, current_approvals=prior
    )
    approval._validate_node_approval_marker_envelope(marker, **arguments)
    marker["task"]["goal"] = "unrelated rewrite"
    with pytest.raises(AiflowError):
        approval._validate_node_approval_marker_envelope(marker, **arguments)


@pytest.mark.parametrize("kind", ["spec", "action", "code"])
def test_node_marker_recovery_rejects_task_rewrite_before_writes(
    tmp_path, monkeypatch, node_policy, code_marker_values, kind
) -> None:
    from aiflow.task_service import TaskRecord

    if kind == "code":
        marker = code_marker_values["marker"]
        task, events, prior = (
            code_marker_values[key]
            for key in ("current_task", "current_events", "current_approvals")
        )
    else:
        marker, task, events, prior = _other_marker(code_marker_values, kind)
    marker["task"]["goal"] = "unrelated rewrite"
    monkeypatch.setattr(approval, "load_policy_bundle", lambda *_: node_policy)
    monkeypatch.setattr(approval, "read_task_json", lambda *_: marker)
    monkeypatch.setattr(
        approval, "read_task_record_strict", lambda *_: TaskRecord(task, tuple(events))
    )
    monkeypatch.setattr(approval, "_load_approvals", lambda *_: prior)

    def forbidden(*_args, **_kwargs):
        pytest.fail("An invalid pending marker reached a write or cleanup")

    monkeypatch.setattr(approval, "atomic_write_json", forbidden)
    monkeypatch.setattr(approval, "_persist_event_and_task", forbidden)
    monkeypatch.setattr(approval, "_remove_marker", forbidden)
    with pytest.raises(AiflowError):
        approval._complete_marker(tmp_path, "TASK-0001")


@pytest.mark.parametrize(
    "fault", [None, "extra", "reference", "unregistered", "float_revision", "later_rejection"]
)
def test_pending_marker_audit_path_requires_current_registered_bindings(
    tmp_path, code_marker_values, fault
) -> None:
    """Exercise the readonly audit-path loader, without consuming execution facts."""
    from test_node_profile_contract import (
        node_policy_directory,
        node_policy_seed_bytes,
        node_public_evidence,
    )

    import aiflow.node_execution as runtime
    from aiflow.review_service import _context_digest
    from aiflow.task_service import read_task_record_strict

    policies = node_policy_directory.__wrapped__(tmp_path, node_policy_seed_bytes.__wrapped__())
    policy = load_policy_bundle(tmp_path)
    values = code_marker_values
    task, events = values["current_task"], values["current_events"]
    evidence = node_public_evidence.__wrapped__(tmp_path, policies)("V0")
    evidence.update(
        repository_id=task["repository_id"],
        branch=task["branch"],
        base_commit=task["base_commit"],
        subject_commit=task["subject_commit"],
        spec_sha256=task["frozen_spec_sha256"],
        policy_sha256=policy.sha256,
        classification_input_sha256="d" * 64,
    )
    evidence_sha = runtime._sha(runtime._canonical(evidence))
    for candidate in values["marker"]["approvals"]:
        candidate["policy_sha256"] = policy.sha256
        if candidate["approval_type"] == "code":
            candidate["evidence_sha256"] = evidence_sha
    context = values["review_context"]
    context.update(policy_sha256=policy.sha256, evidence_sha256=evidence_sha)
    context["context_sha256"] = _context_digest(context)
    digest = context["context_sha256"]
    review = values["implementation_review"]
    review["context_sha256"] = digest
    events[-1]["payload"]["context_sha256"] = digest
    reference = values["marker"]["event"]["payload"]["structured_review"]
    reference["context_sha256"] = digest
    classification = json.loads(
        (ROOT / "tests/fixtures/contracts/valid/classification.json").read_text("utf-8")
    )
    classification.update(
        policy_version="3.1.0",
        policy_sha256=policy.sha256,
        classification_input_sha256="d" * 64,
        subject_commit=task["subject_commit"],
    )
    for entry in classification["classifications"]:
        entry.update(policy_version="3.1.0", policy_sha256=policy.sha256)
    directory = tmp_path / ".ai/tasks/TASK-0001"
    (directory / "reviews").mkdir(parents=True)
    (directory / "review-contexts").mkdir()
    (directory / "task.yaml").write_text(yaml.safe_dump(task), encoding="utf-8")
    (directory / "events.jsonl").write_bytes(
        b"".join(runtime._canonical(e) + b"\n" for e in events)
    )
    for name, value in [
        ("approvals.json", values["current_approvals"]),
        ("classification.json", classification),
        ("evidence.json", evidence),
        ("reviews/REV-0002-r0001.json", review),
        (f"review-contexts/{digest}.json", context),
    ]:
        (directory / name).write_bytes(runtime._canonical(value))
    if fault == "extra":
        values["marker"]["unknown"] = True
    elif fault == "reference":
        reference["context_sha256"] = "f" * 64
    elif fault == "unregistered":
        reference["review_id"] = "REV-0999"
    elif fault == "float_revision":
        reference["revision"] = 1.0
    marker = directory / "approval_pending.json"
    if fault == "later_rejection":
        from aiflow.state import create_record_event

        newer = {**review, "review_id": "REV-0003", "outcome": "REQUEST_CHANGES"}
        (directory / "reviews/REV-0003-r0001.json").write_bytes(runtime._canonical(newer))
        events.append(
            create_record_event(
                task,
                event_type="review_recorded",
                actor="reviewer",
                payload={
                    "review_id": "REV-0003",
                    "revision": 1,
                    "review_stage": "implementation",
                    "context_sha256": digest,
                },
                sequence=len(events) + 1,
                occurred_at=task["updated_at"],
            )
        )
        values["marker"]["event"]["sequence"] = len(events) + 1
        (directory / "events.jsonl").write_bytes(
            b"".join(runtime._canonical(e) + b"\n" for e in events)
        )
    original = runtime._canonical(values["marker"])
    marker.write_bytes(original)
    current = read_task_record_strict(tmp_path, "TASK-0001")
    if fault is not None:
        with pytest.raises(AiflowError):
            runtime._governance_snapshot(tmp_path, "TASK-0001", current.events)
    else:
        snapshot = runtime._governance_snapshot(tmp_path, "TASK-0001", current.events)
        assert ".ai/tasks/TASK-0001/approval_pending.json" in snapshot["paths"]
    assert marker.read_bytes() == original
