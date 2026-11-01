"""Portable policy and entry-point boundaries for the second Node profile.

These logical contracts do not establish ordinary-wheel runtime provenance.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import UUID

import pytest
import yaml

from aiflow.errors import AiflowError
from aiflow.policy import POLICY_FILES, load_policy_bundle
from aiflow.verification_level import determine_verification_level

ROOT = Path(__file__).resolve().parents[2]
V0 = (
    ("contract", 30),
    ("scope", 30),
    ("smoke", 30),
    ("node_build", 300),
    ("node_check", 600),
    ("diff_whitespace", 30),
)
V2_EXTRA = ("acceptance", "integration", "targeted_mutation", "independent_verifier")
LOW_RISK = {
    "mechanical": True,
    "behavior_changed": False,
    "code_modified": False,
    "interaction_scope": "local",
    "regression_risk": False,
    "error_detectability": "high",
}


def node_documents(revision: int = 2) -> dict[str, dict]:
    documents = {
        name: yaml.safe_load((ROOT / ".ai/policy" / name).read_text(encoding="utf8"))
        for name in POLICY_FILES
    }
    version = {1: "3.1.0", 2: "3.2.0"}[revision]
    for document in documents.values():
        document["policy_version"] = version
    v0 = [{"id": name, "required": True, "timeout_seconds": timeout} for name, timeout in V0]
    v1 = [
        *deepcopy(v0),
        {"id": "ts_coverage", "required": True, "timeout_seconds": 600},
        {"id": "ts_total_lines", "required": True, "timeout_seconds": 30, "threshold": 85},
        {"id": "ts_diff_lines", "required": True, "timeout_seconds": 30, "threshold": 90},
    ]
    levels = [{"id": "V0", "checks": v0}, {"id": "V1", "checks": v1}]
    if revision == 2:
        levels.append(
            {
                "id": "V2",
                "checks": [
                    *deepcopy(v1),
                    *[{"id": name, "required": True, "timeout_seconds": 30} for name in V2_EXTRA],
                ],
            }
        )
    documents["verification-levels.yaml"] = {
        "schema_version": "1.0",
        "policy_version": version,
        "policy_kind": "verification_levels",
        "profile": {"id": "agent-bridge-node", "revision": revision},
        "levels": levels,
    }
    return documents


def write_policy(root: Path, documents: dict[str, dict]) -> Path:
    directory = root / ".ai/policy"
    directory.mkdir(parents=True)
    for name, document in documents.items():
        (directory / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf8")
    return directory


@pytest.mark.parametrize("revision", [1, 2])
@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_explicit_node_revisions_preserve_required_strength(tmp_path, revision, level):
    documents = node_documents(revision)
    directory = write_policy(tmp_path, documents)
    before = {name: (directory / name).read_bytes() for name in POLICY_FILES}
    bundle = load_policy_bundle(tmp_path)
    unit = {"decision_unit_id": "DU-001", "change_characteristics": deepcopy(LOW_RISK)}
    if level == "V1":
        unit["change_characteristics"].update(code_modified=True, mechanical=False)
    elif level == "V2":
        unit["verification_requirements"] = {"targeted_mutation_required": True}
    decision = determine_verification_level(unit, bundle)
    assert decision.level == level
    assert bool(decision.blocking_reasons) is (revision == 1 and level == "V2")
    assert bundle.policy_version == {1: "3.1.0", 2: "3.2.0"}[revision]
    assert {name: (directory / name).read_bytes() for name in POLICY_FILES} == before


def test_node_v2_has_the_complete_v1_prefix_and_four_required_pure_checks(tmp_path):
    documents = node_documents()
    write_policy(tmp_path, documents)
    bundle = load_policy_bundle(tmp_path)
    levels = bundle.documents["verification-levels.yaml"]["levels"]
    v0, v1, v2 = (row["checks"] for row in levels)
    assert v1[: len(v0)] == v0
    assert v2[: len(v1)] == v1
    assert len(v2) == 13
    assert [row["id"] for row in v2[-4:]] == list(V2_EXTRA)
    assert all(
        row == {"id": name, "required": True, "timeout_seconds": 30}
        for name, row in zip(V2_EXTRA, v2[-4:], strict=True)
    )
    assert [v1[-2]["threshold"], v1[-1]["threshold"]] == [85, 90]


def test_actual_node_v2_plan_shares_only_the_product_suite_and_binds_fixed_flags(tmp_path):
    from aiflow.node_execution import node_execution_contract
    from aiflow.verification import NodePlanBindings, VerificationContext, parse_verification_plan

    write_policy(tmp_path, node_documents())
    owned = tmp_path / "checkout"
    roles = NodePlanBindings(
        "node.exe",
        "npm-cli.js",
        "git.exe",
        owned,
        tmp_path / "user.npmrc",
        tmp_path / "global.npmrc",
        tmp_path / "coverage",
        tmp_path / "expected.json",
        tmp_path / "sources.json",
    )
    context = VerificationContext(
        tmp_path,
        "TASK-0001",
        "a" * 40,
        "b" * 40,
        "python.exe",
        "IMUT-0123456789abcdef",
        node_bindings=roles,
    )
    plan = parse_verification_plan(load_policy_bundle(tmp_path), context, level="V2")
    assert plan.valid
    assert len(plan.checks) == 13 and len(plan.executions) == 10
    assert [row.check_id for row in plan.checks] == [
        "contract",
        "scope",
        "smoke",
        "node_build",
        "node_check",
        "diff_whitespace",
        "ts_coverage",
        "ts_total_lines",
        "ts_diff_lines",
        *V2_EXTRA,
    ]
    suite, helper = plan.executions[-2:]
    assert suite.check_ids == ("ts_coverage", "acceptance", "integration")
    assert helper.check_ids == ("ts_coverage",)
    assert suite.timeout_seconds == 600 and helper.timeout_seconds == 30
    assert suite.cwd == helper.cwd == owned
    assert suite.argv[-5:] == (
        "--config=" + str(owned / "vitest.config.ts"),
        "--dangerouslyIgnoreUnhandledErrors=false",
        "--reporter=default",
        "--reporter=json",
        "--outputFile.json=" + str(tmp_path / "vitest.json"),
    )
    contract = node_execution_contract(plan, context)
    public_suite, public_helper = contract["executions"][-2:]
    assert public_suite["check_ids"] == ["ts_coverage", "acceptance", "integration"]
    assert public_helper["check_ids"] == ["ts_coverage"]
    assert public_suite["argv_template"][-5:] == [
        "--config={node_source_config}",
        "--dangerouslyIgnoreUnhandledErrors=false",
        "--reporter=default",
        "--reporter=json",
        "--outputFile.json={node_product_report}",
    ]
    assert "--coverage.provider=istanbul" in public_suite["argv_template"]


@pytest.mark.parametrize("index", range(13))
def test_node_v2_never_accepts_an_omitted_required_check(tmp_path, index):
    documents = node_documents()
    del documents["verification-levels.yaml"]["levels"][2]["checks"][index]
    write_policy(tmp_path, documents)
    with pytest.raises(AiflowError):
        load_policy_bundle(tmp_path)


@pytest.mark.parametrize(
    "fault",
    ["order", "duplicate", "nonrequired", "timeout", "argv", "threshold", "bool-timeout"],
)
def test_node_v2_rejects_rehashed_semantically_different_checks(tmp_path, fault):
    documents = node_documents()
    checks = documents["verification-levels.yaml"]["levels"][2]["checks"]
    if fault == "order":
        checks[-1], checks[-2] = checks[-2], checks[-1]
    elif fault == "duplicate":
        checks.append(deepcopy(checks[-1]))
    elif fault == "nonrequired":
        checks[-1]["required"] = False
    elif fault == "timeout":
        checks[-1]["timeout_seconds"] = 31
    elif fault == "argv":
        checks[-1]["command"] = ["arbitrary"]
    elif fault == "threshold":
        checks[7]["threshold"] = 84
    else:
        checks[-1]["timeout_seconds"] = True
    write_policy(tmp_path, documents)
    with pytest.raises(AiflowError):
        load_policy_bundle(tmp_path)


@pytest.mark.parametrize(
    "version,revision",
    [("3.1.0", 2), ("3.2.0", 1), ("3.3.0", 2), ("3.2.0", True), ("3.2.0", 2.0)],
)
def test_node_profile_revision_and_policy_version_cannot_be_cross_labeled(
    tmp_path, version, revision
):
    documents = node_documents()
    for document in documents.values():
        document["policy_version"] = version
    documents["verification-levels.yaml"]["profile"]["revision"] = revision
    write_policy(tmp_path, documents)
    with pytest.raises(AiflowError):
        load_policy_bundle(tmp_path)


@pytest.mark.parametrize("where", ["hard-rules.yaml", "routing.yaml", "permissions.yaml"])
def test_profile_marker_is_not_authority_on_other_policy_documents(tmp_path, where):
    documents = node_documents()
    documents[where]["profile"] = {"id": "agent-bridge-node", "revision": 2}
    write_policy(tmp_path, documents)
    with pytest.raises(AiflowError):
        load_policy_bundle(tmp_path)


@pytest.mark.parametrize("revision", [1, 2])
@pytest.mark.parametrize("options", [{}, {"finalize": True}, {"abandon": True}])
def test_node_ci_stays_rejected_before_task_recovery_or_execution(
    tmp_path, monkeypatch, revision, options
):
    import aiflow.verification_service as service

    write_policy(tmp_path, node_documents(revision))
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("Unavailable Node CI reached task loading/recovery or execution")

    for name in ("load_task_record", "read_task_record_strict", "_execute_plan"):
        monkeypatch.setattr(service, name, forbidden)
    with pytest.raises(AiflowError) as caught:
        service.verify_task(tmp_path, "TASK-0001", ci=True, **options)
    assert caught.value.code == "VERIFY_NODE_CI_UNSUPPORTED"
    assert attempts == []


def test_new_profile_is_explicit_and_unknown_profile_rejects_before_observation(
    tmp_path, monkeypatch
):
    import aiflow.initialization as initialization

    initialization._profile("agent-bridge-node@2")
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("Unsupported profile touched a target")

    monkeypatch.setattr(initialization.git, "observe_initialization_target", forbidden)
    with pytest.raises(AiflowError) as caught:
        initialization.preview_initialization(tmp_path, profile="agent-bridge-node@3")
    assert caught.value.code == "INITIALIZATION_PROFILE_UNSUPPORTED"
    assert attempts == []


def test_cli_transports_only_the_closed_installed_run_selector():
    from aiflow.cli import build_parser

    parsed = build_parser().parse_args(
        ["verify", "TASK-0001", "--installed-mutations", "IMUT-0123456789abcdef"]
    )
    assert parsed.installed_mutations == "IMUT-0123456789abcdef"
    assert parsed.node_materials is None
    assert parsed.ci is False
    assert json.loads(json.dumps(vars(parsed)))["installed_mutations"] == "IMUT-0123456789abcdef"


@pytest.mark.parametrize(
    "selector",
    [
        "",
        "IMUT-0123456789abcde",
        "IMUT-0123456789abcdef0",
        "IMUT-0123456789ABCDEf",
        "../IMUT-0123456789abcdef",
        "IMUT-0123456789abcdef/run.json",
        "logs/IMUT-0123456789abcdef",
        "run-0123456789abcdef",
        " IMUT-0123456789abcdef",
        "IMUT-0123456789abcdef\n",
        True,
        1,
    ],
)
def test_installed_selector_is_not_a_path_or_json_authority(tmp_path, monkeypatch, selector):
    import aiflow.verification_service as service

    bundle = load_policy_bundle(tmp_path, policy_directory=write_policy(tmp_path, node_documents()))
    monkeypatch.setattr(service, "_verification_policy", lambda _: bundle)
    monkeypatch.setattr(
        service, "_classification", lambda *_: {"effective_verification_level": "V2"}
    )
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("Malformed mutation selector reached recovery/execution")

    for name in (
        "load_task_record",
        "read_task_record_strict",
        "_execute_plan",
        "_finalize_v2_task",
    ):
        monkeypatch.setattr(service, name, forbidden)
    with pytest.raises(AiflowError):
        service.verify_task(
            tmp_path,
            "TASK-0001",
            actor="verifier",
            node_materials_sha256="a" * 64,
            node_installed_mutation_run=selector,
        )
    assert attempts == []


@pytest.mark.parametrize(
    "options",
    [
        {"ci": True},
        {"ci_run_dir": Path("ci-run")},
        {"output": Path("ci-evidence.json")},
        {"check_ids": ("contract",)},
        {"provisional": True},
        {"run_id": "IMUT-0123456789abcdef"},
        {"run_id": "other-run"},
        {"finalize": True},
        {"finalize": True, "node_materials_sha256": None},
    ],
)
def test_node_v2_selector_incompatible_modes_reject_before_recovery(tmp_path, monkeypatch, options):
    import aiflow.verification_service as service

    bundle = load_policy_bundle(tmp_path, policy_directory=write_policy(tmp_path, node_documents()))
    monkeypatch.setattr(service, "_verification_policy", lambda _: bundle)
    monkeypatch.setattr(
        service, "_classification", lambda *_: {"effective_verification_level": "V2"}
    )
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("Unsupported Node mode reached recovery/execution")

    for name in (
        "load_task_record",
        "read_task_record_strict",
        "_execute_plan",
        "_finalize_v2_task",
    ):
        monkeypatch.setattr(service, name, forbidden)
    values = dict(
        actor="verifier",
        node_materials_sha256="a" * 64,
        node_installed_mutation_run="IMUT-0123456789abcdef",
    )
    values.update(options)
    with pytest.raises(AiflowError):
        service.verify_task(tmp_path, "TASK-0001", **values)
    assert attempts == []


@pytest.mark.parametrize(
    "profile,level",
    [("native", "V2"), ("1", "V0"), ("1", "V1"), ("1", "V2"), ("2", "V0"), ("2", "V1")],
)
def test_installed_selector_cannot_enable_other_profiles_or_levels(
    tmp_path, monkeypatch, profile, level
):
    import aiflow.verification_service as service

    if profile == "native":
        bundle = load_policy_bundle(ROOT)
    else:
        bundle = load_policy_bundle(
            tmp_path, policy_directory=write_policy(tmp_path, node_documents(int(profile)))
        )
    monkeypatch.setattr(service, "_verification_policy", lambda _: bundle)
    monkeypatch.setattr(
        service, "_classification", lambda *_: {"effective_verification_level": level}
    )
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("Mutation selector crossed a profile or strength boundary")

    for name in (
        "load_task_record",
        "read_task_record_strict",
        "_execute_plan",
        "_finalize_v2_task",
    ):
        monkeypatch.setattr(service, name, forbidden)
    with pytest.raises(AiflowError):
        service.verify_task(
            tmp_path,
            "TASK-0001",
            actor="verifier",
            node_installed_mutation_run="IMUT-0123456789abcdef",
        )
    assert attempts == []


@pytest.fixture(scope="module")
def local_bundle(tmp_path_factory):
    from aiflow.resource_bundle import build_bundle

    root = tmp_path_factory.mktemp("n2bundle")
    manifest, resources = build_bundle(ROOT)
    for relative, data in resources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf8")
    return root


@pytest.fixture
def initialization_model(monkeypatch):
    """Portable state-machine coverage; no claim about NTFS locking semantics."""
    from initialization_helpers import PortableFilesystem

    import aiflow.initialization as initialization

    offset = len(PortableFilesystem.instances)
    monkeypatch.setattr(initialization, "WindowsFilesystem", PortableFilesystem)
    yield initialization
    created = PortableFilesystem.instances[offset:]
    leaked = sum(len(instance.handles) for instance in created)
    for instance in created:
        for handle in list(instance.handles):
            instance.close(handle)
    assert leaked == 0


def target_project(root: Path) -> None:
    from initialization_helpers import fixture_git

    root.mkdir()
    fixture_git(root, "init", "-b", "fixture")
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "public-node-init-fixture",
                "scripts": {
                    "build": "fixture build",
                    "check": "fixture check",
                    "test": "fixture test",
                },
            }
        ),
        encoding="utf8",
    )
    (root / "source.ts").write_bytes(b"export const fixture = true;\n")
    fixture_git(root, "add", "package.json", "source.ts")
    fixture_git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "Public initialization fixture",
    )


def policy_review(preview: dict) -> dict:
    return {
        "schema_version": "1.0",
        "kind": "aiflow-policy-review",
        "preview_sha256": preview["preview_sha256"],
        "repository_id": preview["repository_id"],
        "profile": preview["profile"],
        "policy_version": preview["policy"]["policy_version"],
        "policies": [
            {"path": row["path"], "sha256": row["sha256"]} for row in preview["policy"]["files"]
        ],
        "reviewer": "independent-synthetic-reviewer",
        "outcome": "APPROVE",
    }


def test_node2_nonoverwriting_initialization_owns_a_fresh_identity_and_replays_readonly(
    tmp_path, local_bundle, initialization_model
):
    from initialization_helpers import snapshot_tree

    target = tmp_path / "target"
    target_project(target)
    directory = write_policy(tmp_path / "candidate", node_documents())
    before = snapshot_tree(target)
    preview = initialization_model.preview_initialization(
        target,
        bundle_root=local_bundle,
        policy_directory=directory,
        profile="agent-bridge-node@2",
    )
    assert snapshot_tree(target) == before
    assert preview["profile"] == "agent-bridge-node@2"
    assert preview["policy"]["policy_version"] == "3.2.0"
    assert UUID(preview["repository_id"]).version == 4
    assert preview["repository_id"] != (ROOT / ".ai/repository-id").read_text("utf8").strip()
    decision = policy_review(preview)
    applied = initialization_model.apply_initialization(
        target, preview, decision, bundle_root=local_bundle, policy_directory=directory
    )
    assert applied["phase"] == "installed"
    completed = snapshot_tree(target)
    replayed = initialization_model.apply_initialization(
        target, preview, decision, bundle_root=local_bundle, policy_directory=directory
    )
    assert replayed["phase"] == "already_complete"
    inspected = initialization_model.inspect_initialization(target)
    assert inspected["status"] == "complete"
    assert inspected["profile"] == "agent-bridge-node@2"
    assert inspected["repository_id"] == preview["repository_id"]
    assert snapshot_tree(target) == completed
    assert (target / "source.ts").read_bytes() == b"export const fixture = true;\n"


def test_node2_migration_plan_preserves_old_profile_identity_and_all_history(
    tmp_path, local_bundle, initialization_model
):
    from initialization_helpers import snapshot_tree

    target = tmp_path / "target"
    target_project(target)
    old_policy = write_policy(tmp_path / "old", node_documents(1))
    new_policy = write_policy(tmp_path / "new", node_documents(2))
    preview = initialization_model.preview_initialization(
        target,
        bundle_root=local_bundle,
        policy_directory=old_policy,
        profile="agent-bridge-node@1",
    )
    initialization_model.apply_initialization(
        target,
        preview,
        policy_review(preview),
        bundle_root=local_bundle,
        policy_directory=old_policy,
    )
    history = target / ".ai/tasks/TASK-9999/original.txt"
    history.parent.mkdir(parents=True)
    history.write_bytes(b"original synthetic history\n")
    before = snapshot_tree(target)
    planned = initialization_model.plan_initialization_migration(
        target,
        bundle_root=local_bundle,
        policy_directory=new_policy,
        profile="agent-bridge-node@2",
    )
    assert planned["read_only"] is True
    assert planned["repository_id"] == preview["repository_id"]
    assert planned["profile"] == "agent-bridge-node@1"
    assert planned["proposed_policy"]["policy_version"] == "3.2.0"
    assert snapshot_tree(target) == before
    assert history.read_bytes() == b"original synthetic history\n"


def test_node2_init_replay_does_not_overwrite_modified_managed_bytes(
    tmp_path, local_bundle, initialization_model
):
    from initialization_helpers import snapshot_tree

    target = tmp_path / "target"
    target_project(target)
    directory = write_policy(tmp_path / "candidate", node_documents())
    preview = initialization_model.preview_initialization(
        target,
        bundle_root=local_bundle,
        policy_directory=directory,
        profile="agent-bridge-node@2",
    )
    decision = policy_review(preview)
    initialization_model.apply_initialization(
        target, preview, decision, bundle_root=local_bundle, policy_directory=directory
    )
    managed = target / ".ai/policy/routing.yaml"
    managed.write_bytes(managed.read_bytes() + b"# target-owned modification\n")
    before = snapshot_tree(target)
    inspected = initialization_model.inspect_initialization(target)
    assert inspected["status"] == "conflict"
    with pytest.raises(AiflowError):
        initialization_model.apply_initialization(
            target, preview, decision, bundle_root=local_bundle, policy_directory=directory
        )
    assert snapshot_tree(target) == before
