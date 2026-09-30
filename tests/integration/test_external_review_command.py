"""Real Git-backed service and CLI integration for immutable external reports."""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from typing import Any

import pytest
from test_approve_command import _evidence, _prepare
from test_begin_close_commands import commit_all, run_git

from aiflow import cli, external_review
from aiflow.classification_service import classify_task
from aiflow.cli import main
from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError
from aiflow.evidence import verification_snapshot_sha256
from aiflow.gate import evaluate_gate
from aiflow.review_service import (
    build_review_context,
    latest_review_assessment,
    record_review,
    validate_review_record,
)
from aiflow.status_service import summarize_task
from aiflow.storage import atomic_write_json, atomic_write_yaml
from aiflow.task_service import (
    freeze_task,
    read_task_record_strict,
    start_task,
    transition_task_record,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "TASK-0001"
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"
_ROOT_COUNTER = count()
SYNTHETIC_SECRET = "SYNTHETIC_EXTERNAL_REVIEW_SECRET"
SPECIFICATION = """# Task Specification

## 目标
验证 synthetic 任务的确定性行为。
## 范围
仅修改 src/module.py。
## 非目标
不执行外部动作。
## 验收条件
合成断言通过。
## 禁止动作
不得推送或读取秘密。
## 错误行为
错配应拒绝。
## 回滚
仅恢复本次合成输入。
"""


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, check=True, encoding="utf-8", timeout=10
    )
    return result.stdout.rstrip("\r\n")


def commit(root: Path, message: str) -> str:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Synthetic Tests",
        "-c",
        "user.email=synthetic@example.invalid",
        "commit",
        "-m",
        message,
    )
    return git(root, "rev-parse", "HEAD")


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def tree_snapshot(root: Path) -> dict[str, bytes | None]:
    """Include empty directories as well as every byte under the full task root."""
    physical_root = Path("\\\\?\\" + str(root)) if os.name == "nt" else root
    return {
        path.relative_to(physical_root).as_posix(): None if path.is_dir() else path.read_bytes()
        for path in sorted(physical_root.rglob("*"))
    }


@dataclass
class Case:
    root: Path
    envelope_path: Path
    report_path: Path
    envelope: dict[str, Any]
    context: dict[str, Any]
    mapping_path: Path | None = None

    @property
    def tasks(self) -> Path:
        return self.root / ".ai" / "tasks"

    @property
    def task(self) -> Path:
        return self.tasks / TASK_ID

    def save(self) -> None:
        atomic_write_json(self.envelope_path, self.envelope)

    def preflight(self) -> dict[str, Any]:
        return external_review.preflight_external_review(
            self.root,
            TASK_ID,
            self.envelope_path,
            self.report_path,
            repository_mapping_path=self.mapping_path,
        )

    def record(self, token: str | None = None) -> dict[str, Any]:
        token = token or self.preflight()["preflight_sha256"]
        return external_review.record_external_review(
            self.root,
            TASK_ID,
            self.envelope_path,
            self.report_path,
            repository_mapping_path=self.mapping_path,
            expected_preflight_sha256=token,
        )


def make_case(
    tmp_path: Path, *, implementation: bool = False, v2: bool = False, reversed_units: bool = False
) -> Case:
    # Keep real Windows atomic-publication paths below MAX_PATH in test fixtures.
    root = tmp_path.parent / f"r{next(_ROOT_COUNTER)}"
    root.mkdir()
    git(root, "init", "-b", "main")
    for directory in ("schemas", "policy", "templates"):
        shutil.copytree(PROJECT_ROOT / ".ai" / directory, root / ".ai" / directory)
    (root / ".ai" / "repository-id").write_text(REPOSITORY_ID + "\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "module.py").write_text("value = 1\n", encoding="utf-8")
    commit(root, "synthetic baseline")
    start_task(
        root, objective="synthetic report target", allowed_scope=["src/**"], forbidden_actions=[]
    )
    (root / ".ai" / "task-sequence").unlink(missing_ok=True)
    task_path = root / ".ai" / "tasks" / TASK_ID / "task.yaml"
    task = read_task_record_strict(root, TASK_ID).task
    task["decision_units"][0].update(
        {
            "impact_scope": ["src/module.py"],
            "impact_categories": [],
            "controlled_actions": [],
            "scope": {"clear": True},
            "impact": {"level": "medium"},
            "verification": {"automatic": True, "tools_missing": False},
        }
    )
    if v2:
        task["decision_units"][0]["verification_requirements"] = {
            "acceptance_required": True,
            "integration_required": True,
            "independent_verifier_required": True,
            "targeted_mutation_required": True,
        }
    if reversed_units:
        second = deepcopy(task["decision_units"][0])
        second["decision_unit_id"] = "DU-002"
        second["goal"] = "Validate a second synthetic independently classified fact"
        task["decision_units"] = [second, task["decision_units"][0]]
    atomic_write_yaml(task_path, task)
    (task_path.parent / "spec.md").write_text(SPECIFICATION, encoding="utf-8")
    classification = classify_task(root, TASK_ID, actor="synthetic-classifier")
    assert read_task_record_strict(root, TASK_ID).task["current_state"] == "WAITING_FOR_SPEC_REVIEW"
    freeze_task(root, TASK_ID, actor="synthetic-specifier")
    stage = "design"
    if implementation:
        for state, event, preconditions in (
            ("READY_TO_IMPLEMENT", "spec_approved", {"spec_frozen", "spec_approval_valid"}),
            ("IMPLEMENTING", "implementation_started", {"readiness_satisfied"}),
            ("VERIFYING", "verification_started", {"implementation_complete"}),
            ("VERIFIED", "verification_passed", {"verification_passed"}),
            ("WAITING_FOR_FINAL_REVIEW", "final_review_required", {"final_review_required"}),
        ):
            transition_task_record(
                root,
                TASK_ID,
                target_state=state,
                event_type=event,
                actor="synthetic-role",
                payload={},
                satisfied_preconditions=preconditions,
            )
        task = read_task_record_strict(root, TASK_ID).task
        fixture_name = "evidence-v2.json" if v2 else "evidence.json"
        evidence = json.loads(
            (PROJECT_ROOT / "tests/fixtures/contracts/valid" / fixture_name).read_text()
        )
        for field in ("task_id", "repository_id", "branch", "base_commit", "subject_commit"):
            evidence[field] = task[field]
        evidence["spec_sha256"] = task["frozen_spec_sha256"]
        evidence["policy_sha256"] = classification["policy_sha256"]
        evidence["classification_input_sha256"] = classification["classification_input_sha256"]
        evidence["verification_level"] = classification["effective_verification_level"]
        if v2:
            evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
        require_valid_contract("evidence", evidence)
        atomic_write_json(task_path.parent / "evidence.json", evidence)
        stage = "implementation"
    commit(root, "synthetic task governance")
    context = dict(build_review_context(root, TASK_ID, stage))
    envelope = json.loads(
        (PROJECT_ROOT / "tests/fixtures/contracts/valid/external-review.json").read_text()
    )
    envelope["target_context"] = {
        key: context[key]
        for key in ("task_id", "repository_id", "review_stage", "base_commit", "context_sha256")
    }
    envelope["source_subject"]["repository"]["repository_id"] = REPOSITORY_ID
    envelope["source_subject"]["review_stage"] = stage
    envelope["source_subject"]["base_commit"] = context["base_commit"]
    if implementation:
        envelope["target_context"]["subject_commit"] = context["subject_commit"]
        envelope["source_subject"]["subject_commit"] = context["subject_commit"]
    report_path = tmp_path / "synthetic-report.bin"
    report_path.write_bytes(b"Synthetic opaque report\x00\xff\n")
    envelope["source"]["raw_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    case = Case(root, tmp_path / "synthetic-envelope.json", report_path, envelope, context)
    case.save()
    return case


@pytest.fixture(scope="module")
def baseline_cases(tmp_path_factory: pytest.TempPathFactory) -> dict[tuple[bool, bool], Case]:
    """Classify/freeze real Git baselines once; every test receives its own full copy."""
    return {
        identity: make_case(
            tmp_path_factory.mktemp("er"), implementation=identity[0], v2=identity[1]
        )
        for identity in ((False, False), (True, False), (True, True))
    }


def copy_case(tmp_path: Path, baseline: Case) -> Case:
    root = tmp_path.parent / f"r{next(_ROOT_COUNTER)}"
    shutil.copytree(baseline.root, root)
    report = tmp_path / "synthetic-report.bin"
    report.write_bytes(baseline.report_path.read_bytes())
    mapping = None
    if baseline.mapping_path is not None:
        mapping = tmp_path / "synthetic-mapping.json"
        mapping.write_bytes(baseline.mapping_path.read_bytes())
    result = Case(
        root,
        tmp_path / "synthetic-envelope.json",
        report,
        deepcopy(baseline.envelope),
        deepcopy(baseline.context),
        mapping,
    )
    result.save()
    return result


@pytest.fixture
def case(tmp_path: Path, baseline_cases: dict[tuple[bool, bool], Case]) -> Case:
    return copy_case(tmp_path, baseline_cases[(False, False)])


def rejected_without_writes(
    case: Case, operation: str = "preflight", token: str | None = None
) -> ContractError:
    before = tree_snapshot(case.tasks)
    with pytest.raises(ContractError) as caught:
        case.record(token) if operation == "record" else case.preflight()
    assert caught.value.code.startswith("EXTERNAL_REVIEW_")
    rendered = json.dumps(caught.value.to_dict())
    assert SYNTHETIC_SECRET not in rendered
    assert str(case.root) not in rendered
    assert str(case.envelope_path) not in rendered
    assert tree_snapshot(case.tasks) == before
    return caught.value


def use_locator(case: Case) -> dict[str, Any]:
    locator = "https://example.invalid/synthetic/repository"
    case.envelope["source_subject"]["repository"] = {
        "kind": "repository_locator",
        "locator": locator,
        "mapping_record_id": "synthetic-map-001",
    }
    mapping = {
        "kind": "external-review-repository-mapping",
        "schema_version": "1.0",
        "mapping_record_id": "synthetic-map-001",
        "locator": locator,
        "repository_id": REPOSITORY_ID,
        "confirmation": deepcopy(case.envelope["source_subject"]["confirmation"]),
    }
    case.mapping_path = case.envelope_path.with_name("synthetic-mapping.json")
    atomic_write_json(case.mapping_path, mapping)
    case.save()
    return mapping


@pytest.fixture(scope="module")
def recorded_baselines(
    tmp_path_factory: pytest.TempPathFactory, baseline_cases: dict[tuple[bool, bool], Case]
) -> dict[bool, Case]:
    """Record genuine first imports once; tests clone the complete uncommitted Git tree."""
    result: dict[bool, Case] = {}
    for locator in (False, True):
        baseline = copy_case(
            tmp_path_factory.mktemp("recorded-baseline"), baseline_cases[(False, False)]
        )
        if locator:
            use_locator(baseline)
        token = baseline.preflight()["preflight_sha256"]
        assert baseline.record(token)["status"] == "recorded"
        result[locator] = baseline
    return result


@pytest.fixture
def recorded_case(tmp_path: Path, recorded_baselines: dict[bool, Case]) -> Case:
    return copy_case(tmp_path, recorded_baselines[False])


def source_finding() -> dict[str, Any]:
    return {
        "source_finding_id": "synthetic-F1",
        "title": "Synthetic finding",
        "location": {"path": "src/module.py", "line": 1},
        "source_priority": "P2",
        "evidence_refs": ["report:line:1"],
        "mapping": {"status": "pending"},
    }


@pytest.mark.parametrize("implementation", [False, True], ids=["design", "implementation"])
def test_preflight_binds_real_git_frozen_task_without_writing(
    tmp_path: Path, implementation: bool, baseline_cases: dict[tuple[bool, bool], Case]
) -> None:
    case = copy_case(tmp_path, baseline_cases[(implementation, False)])
    before = tree_snapshot(case.tasks)
    index = (case.root / ".git/index").read_bytes()
    first = case.preflight()
    assert first == case.preflight()
    assert first["status"] == "ready" and first["reason_codes"] == []
    assert first["task_id"] == TASK_ID
    assert first["review_stage"] == case.context["review_stage"]
    assert first["context_sha256"] == case.context["context_sha256"]
    assert first["input_sha256"] == digest({"envelope": case.envelope, "repository_mapping": None})
    for field in ("preflight_sha256", "input_sha256", "source_key_sha256"):
        assert len(first[field]) == 64 and set(first[field]) <= set("0123456789abcdef")
    version = hashlib.sha256(case.envelope["source"]["report_version"].encode()).hexdigest()
    assert (
        first["record_path"]
        == f".ai/tasks/{TASK_ID}/external-reviews/{first['source_key_sha256']}/{version}.json"
    )
    assert tree_snapshot(case.tasks) == before
    assert (case.root / ".git/index").read_bytes() == index
    assert not (case.task / "review-contexts").exists()


@pytest.mark.parametrize(
    ("branch", "collision_depth", "warn_ambiguous"),
    [
        ("codex/plain", 0, True),
        ("codex/collision", 1, True),
        ("codex/collision", 2, True),
        ("codex/collision", 1, False),
        ("codex/collision", 2, False),
        ("codex/x\u00a0y", 0, True),
        ("codex/x\u2003y", 0, True),
        ("codex/x\u2028y", 0, True),
    ],
)
def test_read_only_checkout_preserves_git_canonical_branch_identity(
    case: Case, branch: str, collision_depth: int, warn_ambiguous: bool
) -> None:
    git(case.root, "branch", "-m", branch)
    git(case.root, "config", "core.warnAmbiguousRefs", str(warn_ambiguous).lower())
    if collision_depth:
        git(case.root, "tag", branch)
    if collision_depth > 1:
        git(case.root, "tag", "heads/" + branch)
    expected_branch = git(case.root, "symbolic-ref", "--short", "-q", "HEAD")
    expected_head = git(case.root, "rev-parse", "HEAD")
    before = tree_snapshot(case.tasks)
    index = (case.root / ".git/index").read_bytes()
    context, dirty = external_review._read_only_checkout(case.root)
    assert context.branch == expected_branch
    assert context.head == expected_head
    assert context.repository_id == REPOSITORY_ID
    assert dirty == () and not context.worktree_dirty
    assert tree_snapshot(case.tasks) == before
    assert (case.root / ".git/index").read_bytes() == index


@pytest.mark.parametrize("ref_namespace", ["heads", "tags"])
def test_read_only_checkout_preserves_raw_head_ref_ambiguity(
    case: Case, ref_namespace: str
) -> None:
    git(case.root, "update-ref", f"refs/{ref_namespace}/HEAD", "HEAD")
    if ref_namespace == "heads":
        git(case.root, "symbolic-ref", "HEAD", "refs/heads/HEAD")
    expected_branch = git(case.root, "symbolic-ref", "--short", "-q", "HEAD")
    expected_head = git(case.root, "rev-parse", "HEAD")
    before = tree_snapshot(case.tasks)
    index = (case.root / ".git/index").read_bytes()
    context, dirty = external_review._read_only_checkout(case.root)
    assert context.branch == expected_branch
    assert context.head == expected_head
    assert dirty == ()
    assert tree_snapshot(case.tasks) == before
    assert (case.root / ".git/index").read_bytes() == index


def test_detached_head_preflight_is_rejected_without_task_or_index_writes(case: Case) -> None:
    git(case.root, "checkout", "--detach", "HEAD")
    index = (case.root / ".git/index").read_bytes()
    error = rejected_without_writes(case)
    assert error.code == "EXTERNAL_REVIEW_GIT_BINDING_STALE"
    assert (case.root / ".git/index").read_bytes() == index


def test_manual_locator_mapping_resolves_uuid_without_guessing(case: Case) -> None:
    mapping = use_locator(case)
    before = tree_snapshot(case.tasks)
    result = case.preflight()
    assert result["status"] == "ready"
    assert result["input_sha256"] == digest(
        {"envelope": case.envelope, "repository_mapping": mapping}
    )
    assert tree_snapshot(case.tasks) == before


@pytest.mark.parametrize("field", ["locator", "mapping_record_id", "repository_id", "confirmation"])
def test_locator_mapping_mismatch_is_zero_write(case: Case, field: str) -> None:
    mapping = use_locator(case)
    if field == "confirmation":
        del mapping[field]
    elif field == "repository_id":
        mapping[field] = "223e4567-e89b-42d3-a456-426614174000"
    else:
        mapping[field] += ".git"
    atomic_write_json(case.mapping_path, mapping)
    rejected_without_writes(case)


def test_uuid_source_rejects_superfluous_repository_mapping(case: Case) -> None:
    mapping = use_locator(case)
    case.envelope["source_subject"]["repository"] = {
        "kind": "aiflow_repository_id",
        "repository_id": REPOSITORY_ID,
    }
    case.save()
    assert mapping["repository_id"] == REPOSITORY_ID
    rejected_without_writes(case)


def test_locator_source_requires_explicit_mapping(case: Case) -> None:
    use_locator(case)
    case.mapping_path = None
    rejected_without_writes(case)


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("target_context", "task_id", "TASK-0002"),
        ("target_context", "repository_id", "223e4567-e89b-42d3-a456-426614174000"),
        ("target_context", "base_commit", "f" * 40),
        ("target_context", "context_sha256", "f" * 64),
        ("source_subject", "base_commit", "f" * 40),
        ("source_subject", "review_stage", "implementation"),
        ("source", "raw_sha256", "f" * 64),
    ],
)
def test_wrong_source_or_target_binding_is_zero_write(
    case: Case, section: str, field: str, value: str
) -> None:
    case.envelope[section][field] = value
    case.save()
    rejected_without_writes(case)


def test_cross_repository_dotfiles_shape_cannot_target_harness_task(case: Case) -> None:
    """The historical dotfiles raw report is unavailable; this is synthetic only."""
    case.envelope["target_context"]["task_id"] = TASK_ID
    case.envelope["source_subject"]["repository"]["repository_id"] = (
        "223e4567-e89b-42d3-a456-426614174000"
    )
    case.envelope["source_subject"]["base_commit"] = "5" * 40
    case.envelope["source"]["location"]["value"] = "synthetic-dotfiles-51044a55"
    case.save()
    rejected_without_writes(case)


@pytest.mark.parametrize(
    "target", ["spec", "classification", "source", "branch", "uuid", "other-task"]
)
def test_current_freshness_and_checkout_are_not_replaced_by_context_hash(
    case: Case, target: str
) -> None:
    if target == "spec":
        (case.task / "spec.md").write_text(SPECIFICATION + "\nChanged facts.\n", encoding="utf-8")
    elif target == "classification":
        path = case.task / "classification.json"
        value = json.loads(path.read_text())
        value["classification_input_sha256"] = "f" * 64
        atomic_write_json(path, value)
    elif target == "source":
        (case.root / "src/module.py").write_text("value = 2\n", encoding="utf-8")
    elif target == "branch":
        git(case.root, "checkout", "-b", "wrong-branch")
    elif target == "uuid":
        (case.root / ".ai/repository-id").write_text("223e4567-e89b-42d3-a456-426614174000\n")
    else:
        other = case.tasks / "TASK-0002"
        other.mkdir()
        (other / "foreign.txt").write_text("foreign synthetic data")
    rejected_without_writes(case)


@pytest.mark.parametrize("mutation", ["failed", "wrong-spec", "wrong-subject", "missing"])
def test_implementation_requires_current_passed_evidence(
    tmp_path: Path, mutation: str, baseline_cases: dict[tuple[bool, bool], Case]
) -> None:
    case = copy_case(tmp_path, baseline_cases[(True, False)])
    path = case.task / "evidence.json"
    if mutation == "missing":
        path.unlink()
    else:
        value = json.loads(path.read_text())
        if mutation == "failed":
            value["conclusion"] = "failed"
            value["checks"][0].update(status="failed", exit_code=1)
        else:
            value["spec_sha256" if mutation == "wrong-spec" else "subject_commit"] = "f" * (
                64 if mutation == "wrong-spec" else 40
            )
        atomic_write_json(path, value)
    rejected_without_writes(case)


def test_strict_read_never_repairs_event_ahead_materialization(case: Case) -> None:
    path = case.task / "task.yaml"
    original = read_task_record_strict(case.root, TASK_ID).task
    atomic_write_yaml(case.task / "task.yaml.next", original)
    stale = deepcopy(original)
    stale["current_state"] = "CLASSIFIED"
    atomic_write_yaml(path, stale)
    rejected_without_writes(case)
    assert (case.task / "task.yaml.next").exists()


@pytest.mark.parametrize(
    "payload",
    [
        b"\xef\xbb\xbf{}",
        b'{"kind":"external-review","kind":"external-review"}',
        b'{"number":NaN}',
        b'{"number":Infinity}',
        b"\xff",
        b"[]",
        b"null",
        b"{",
        b"[" * 33 + b"0" + b"]" * 33,
    ],
)
def test_strict_json_rejects_ambiguous_or_unbounded_inputs(case: Case, payload: bytes) -> None:
    case.envelope_path.write_bytes(payload)
    rejected_without_writes(case)


@pytest.mark.parametrize(
    "input_name,maximum",
    [("envelope", 256 * 1024), ("report", 16 * 1024 * 1024), ("mapping", 64 * 1024)],
)
def test_input_byte_limits_are_enforced_before_decoding(
    case: Case, input_name: str, maximum: int
) -> None:
    if input_name == "mapping":
        use_locator(case)
        path = case.mapping_path
    else:
        path = case.envelope_path if input_name == "envelope" else case.report_path
    assert path is not None
    path.write_bytes(b" " * (maximum + 1))
    rejected_without_writes(case)


def test_empty_raw_report_is_rejected_even_with_matching_hash(case: Case) -> None:
    case.report_path.write_bytes(b"")
    case.envelope["source"]["raw_sha256"] = hashlib.sha256(b"").hexdigest()
    case.save()
    rejected_without_writes(case)


@pytest.mark.parametrize("parent", [(), ("source",), ("source_subject", "confirmation")])
def test_unknown_sensitive_fields_are_not_reflected(case: Case, parent: tuple[str, ...]) -> None:
    node = case.envelope
    for key in parent:
        node = node[key]
    node[SYNTHETIC_SECRET] = SYNTHETIC_SECRET
    case.save()
    rejected_without_writes(case)


@pytest.mark.parametrize(
    "location",
    [
        "https://user:password@example.invalid/report",
        "https://example.invalid/report?token=secret",
        "https://example.invalid/report#secret",
        "https://example.invalid/%2e%2e/report",
        "https://example.invalid/%252e%252e/report",
        "https://example.invalid/%5creport",
        "https://example.invalid/%0areport",
        "https://example.invalid/%40secret/report",
        "https://example.invalid/%FF/report",
        "https://example.invalid/%2525252541/report",
    ],
)
def test_https_identifiers_reject_authentication_and_encoded_escape(
    case: Case, location: str
) -> None:
    case.envelope["source"]["location"] = {"kind": "https_url", "value": location}
    case.save()
    rejected_without_writes(case)


@pytest.mark.parametrize(
    "path",
    [
        "/absolute",
        "../escape",
        "src/../module.py",
        "C:/local",
        "src\\module.py",
        "src//module.py",
        "src/./module.py",
        "src/module.py:ads",
        "src/\x00module.py",
    ],
)
def test_finding_paths_are_portable_data_and_cannot_escape(case: Case, path: str) -> None:
    finding = source_finding()
    finding["location"]["path"] = path
    case.envelope["findings"] = [finding]
    case.save()
    rejected_without_writes(case)


@pytest.mark.parametrize(
    "path",
    [
        "/local/path",
        "C:\\local\\path",
        "../escape",
        "https://user:password@example.invalid/log",
        "https://example.invalid/%2e%2e/log",
    ],
)
def test_scope_and_fact_references_receive_path_and_url_checks(case: Case, path: str) -> None:
    case.envelope["source_subject"]["confirmation"]["fact_refs"] = [path]
    case.save()
    rejected_without_writes(case)


def test_input_under_tasks_is_rejected_without_copying_or_context_creation(case: Case) -> None:
    path = case.task / "synthetic-envelope.json"
    path.write_bytes(case.envelope_path.read_bytes())
    case.envelope_path = path
    rejected_without_writes(case)


def test_symlink_input_is_rejected(case: Case) -> None:
    link = case.envelope_path.with_name("synthetic-link.json")
    try:
        link.symlink_to(case.envelope_path)
    except OSError:
        pytest.skip("Host does not permit synthetic symlink creation")
    case.envelope_path = link
    rejected_without_writes(case)


def test_duplicate_source_finding_ids_cannot_be_silently_collapsed(case: Case) -> None:
    case.envelope["findings"] = [source_finding(), source_finding()]
    case.save()
    rejected_without_writes(case)


def add_formal_review(case: Case) -> dict[str, Any]:
    current = dict(build_review_context(case.root, TASK_ID, case.context["review_stage"]))
    record_review(
        case.root,
        TASK_ID,
        actor="synthetic-independent-reviewer",
        input_path={
            "schema_version": "1.0",
            "review_id": "REV-0001",
            "review_stage": current["review_stage"],
            "recorded_at": "2026-09-30T00:00:00Z",
            "context_sha256": current["context_sha256"],
            "outcome": "REQUEST_CHANGES",
            "summary": "Synthetic formal review",
            "findings": [
                {
                    "finding_id": "RF-001",
                    "severity": "medium",
                    "title": "Synthetic",
                    "location": {"path": "src/module.py"},
                    "evidence_refs": [],
                    "status": "open",
                }
            ],
        },
    )
    finding = source_finding()
    finding["mapping"] = {
        "status": "suggested",
        "task_id": TASK_ID,
        "review_id": "REV-0001",
        "revision": 1,
        "finding_id": "RF-001",
    }
    case.envelope["findings"] = [finding]
    case.save()
    return finding


def test_exact_existing_composite_finding_reference_is_read_only(case: Case) -> None:
    add_formal_review(case)
    before = tree_snapshot(case.tasks)
    assert case.preflight()["status"] == "ready"
    assert tree_snapshot(case.tasks) == before


@pytest.fixture(scope="module")
def historical_finding_baselines(
    tmp_path_factory: pytest.TempPathFactory, baseline_cases: dict[tuple[bool, bool], Case]
) -> dict[bool, Case]:
    """Seed genuine native Review/first writer once; every test clones its complete Git tree."""
    result: dict[bool, Case] = {}
    for implementation in (False, True):
        baseline = copy_case(
            tmp_path_factory.mktemp("historical-finding-baseline"),
            baseline_cases[(implementation, False)],
        )
        add_formal_review(baseline)
        assert baseline.record()["status"] == "recorded"
        result[implementation] = baseline
    return result


@pytest.fixture
def historical_case(tmp_path: Path, historical_finding_baselines: dict[bool, Case]) -> Case:
    return copy_case(tmp_path, historical_finding_baselines[False])


def historical_attachment(case: Case) -> tuple[Path, bytes, dict[str, Any]]:
    paths = list((case.task / "external-reviews").rglob("*.json"))
    assert len(paths) == 1
    raw = paths[0].read_bytes()
    value = json.loads(raw)
    require_valid_contract("external-review-import", value)
    return paths[0], raw, value


@pytest.mark.parametrize("operation", ["preflight", "record"])
@pytest.mark.parametrize(
    "corruption",
    [
        "mapping-task",
        "mapping-review",
        "mapping-revision",
        "mapping-finding",
        "formal-review-id",
        "formal-revision",
        "formal-finding",
        "context-stage",
        "context-base",
        "context-subject",
        "context-repository",
        "context-task",
        "target-digest",
        "missing-context",
    ],
)
def test_historical_suggested_finding_requires_exact_valid_formal_binding(
    tmp_path: Path,
    historical_finding_baselines: dict[bool, Case],
    corruption: str,
    operation: str,
) -> None:
    case = copy_case(tmp_path, historical_finding_baselines[corruption == "context-subject"])
    saved_path, _saved_bytes, saved = historical_attachment(case)
    case.envelope["findings"] = []
    case.envelope["source"]["report_version"] = "synthetic-next-version"
    case.save()
    review_path = case.task / "reviews/REV-0001-r0001.json"
    review = json.loads(review_path.read_text())
    context_path = case.task / f"review-contexts/{review['context_sha256']}.json"
    archived = json.loads(context_path.read_text())
    validate_review_record(review, archived)
    mapping = saved["envelope"]["findings"][0]["mapping"]
    expected_code = "EXTERNAL_REVIEW_FINDING_MISMATCH"
    if corruption.startswith("mapping-"):
        field, value = {
            "mapping-task": ("task_id", "TASK-9999"),
            "mapping-review": ("review_id", "REV-9999"),
            "mapping-revision": ("revision", 9999),
            "mapping-finding": ("finding_id", "RF-999"),
        }[corruption]
        mapping[field] = value
        if corruption in {"mapping-review", "mapping-revision"}:
            expected_code = "EXTERNAL_REVIEW_INPUT_UNREADABLE"
    elif corruption.startswith("formal-"):
        if corruption == "formal-review-id":
            review["review_id"] = "REV-9999"
        elif corruption == "formal-revision":
            review["revision"] = 9999
        else:
            review["findings"][0]["finding_id"] = "RF-999"
        validate_review_record(review, archived)
        atomic_write_json(review_path, review)
    elif corruption == "target-digest":
        saved["envelope"]["target_context"]["context_sha256"] = "f" * 64
    elif corruption == "missing-context":
        # Remove only the exact synthetic archive owned by this isolated case.
        context_path.unlink()
        expected_code = "EXTERNAL_REVIEW_INPUT_UNREADABLE"
    else:
        if corruption == "context-stage":
            archived.update(review_stage="implementation", subject_commit="f" * 40)
            archived["evidence_sha256"] = "e" * 64
            review["review_stage"] = "implementation"
        elif corruption == "context-base":
            archived["base_commit"] = "f" * 40
        elif corruption == "context-subject":
            archived["subject_commit"] = "f" * 40
        elif corruption == "context-repository":
            archived["repository_id"] = "223e4567-e89b-42d3-a456-426614174000"
        else:
            archived["task_id"] = "TASK-9999"
            review["task_id"] = "TASK-9999"
        archived["context_sha256"] = digest(
            {key: value for key, value in archived.items() if key != "context_sha256"}
        )
        review["context_sha256"] = archived["context_sha256"]
        # Each altered Review/archive remains internally valid; only its saved target differs.
        validate_review_record(review, archived)
        atomic_write_json(
            case.task / f"review-contexts/{archived['context_sha256']}.json", archived
        )
        atomic_write_json(review_path, review)
        saved["envelope"]["target_context"]["context_sha256"] = archived["context_sha256"]
    saved["input_sha256"] = digest(
        {"envelope": saved["envelope"], "repository_mapping": saved["repository_mapping"]}
    )
    require_valid_contract("external-review-import", saved)
    atomic_write_json(saved_path, saved)
    index = (case.root / ".git/index").read_bytes()
    # A syntactically valid token must not let writer skip its historical-reference check.
    error = rejected_without_writes(case, operation, token="f" * 64)
    assert error.code == expected_code
    assert (case.root / ".git/index").read_bytes() == index


def freeze_new_context_without_old_mapping(case: Case) -> None:
    (case.task / "spec.md").write_text(
        SPECIFICATION + "\nAdditional synthetic acceptance: retain historical Finding binding.\n",
        encoding="utf-8",
    )
    freeze_task(case.root, TASK_ID, actor="synthetic-specifier")
    current = dict(build_review_context(case.root, TASK_ID, "design"))
    assert current["context_sha256"] != case.context["context_sha256"]
    case.context = current
    case.envelope["target_context"]["context_sha256"] = current["context_sha256"]
    case.envelope["findings"] = []
    case.envelope["source"]["report_version"] = "synthetic-new-context-version"
    case.save()


def test_historical_suggested_finding_retains_valid_old_context_when_new_context_appends(
    historical_case: Case,
) -> None:
    case = historical_case
    first_path, first_bytes, first_value = historical_attachment(case)
    old_context_hash = case.context["context_sha256"]
    review_path = case.task / "reviews/REV-0001-r0001.json"
    context_path = case.task / f"review-contexts/{old_context_hash}.json"
    review_bytes, context_bytes = review_path.read_bytes(), context_path.read_bytes()
    freeze_new_context_without_old_mapping(case)
    index = (case.root / ".git/index").read_bytes()
    before = tree_snapshot(case.tasks)
    prepared = case.preflight()
    assert prepared["status"] == "ready"
    assert tree_snapshot(case.tasks) == before
    second = case.record(prepared["preflight_sha256"])
    assert second["status"] == "recorded"
    appended = json.loads((case.root / second["record_path"]).read_bytes())
    assert appended["previous_record_sha256"] == digest(first_value)
    assert (
        appended["envelope"]["target_context"]["context_sha256"] == case.context["context_sha256"]
    )
    assert first_value["envelope"]["target_context"]["context_sha256"] == old_context_hash
    assert first_path.read_bytes() == first_bytes
    assert review_path.read_bytes() == review_bytes
    assert context_path.read_bytes() == context_bytes
    validate_review_record(json.loads(review_bytes), json.loads(context_bytes))
    after = tree_snapshot(case.tasks)
    assert all(after[name] == value for name, value in before.items())
    assert (case.root / ".git/index").read_bytes() == index


@pytest.mark.parametrize("artifact", ["formal-review", "review-context"])
def test_historical_finding_reference_byte_drift_invalidates_preflight_token(
    historical_case: Case, artifact: str
) -> None:
    case = historical_case
    saved_path, saved_bytes, _saved = historical_attachment(case)
    review_path = case.task / "reviews/REV-0001-r0001.json"
    review = json.loads(review_path.read_bytes())
    context_path = case.task / f"review-contexts/{review['context_sha256']}.json"
    freeze_new_context_without_old_mapping(case)
    token = case.preflight()["preflight_sha256"]
    path = review_path if artifact == "formal-review" else context_path
    original_bytes = path.read_bytes()
    original = json.loads(original_bytes)
    path.write_text(json.dumps(original, ensure_ascii=False, indent=4) + "\n\n", encoding="utf-8")
    assert path.read_bytes() != original_bytes
    assert json.loads(path.read_bytes()) == original
    validate_review_record(
        json.loads(review_path.read_bytes()), json.loads(context_path.read_bytes())
    )
    index = (case.root / ".git/index").read_bytes()
    error = rejected_without_writes(case, "record", token)
    assert error.code == "EXTERNAL_REVIEW_PREFLIGHT_STALE"
    assert saved_path.read_bytes() == saved_bytes
    assert (case.root / ".git/index").read_bytes() == index


@pytest.mark.parametrize(
    "field,value",
    [
        ("task_id", "TASK-0002"),
        ("review_id", "REV-0002"),
        ("revision", 2),
        ("finding_id", "RF-002"),
    ],
)
def test_mapping_requires_exact_task_review_revision_and_finding(
    case: Case, field: str, value: object
) -> None:
    finding = add_formal_review(case)
    finding["mapping"][field] = value
    case.save()
    rejected_without_writes(case)


def test_old_context_formal_finding_is_not_current_mapping(case: Case) -> None:
    add_formal_review(case)
    review_path = case.task / "reviews/REV-0001-r0001.json"
    review = json.loads(review_path.read_text())
    archived_context = json.loads(
        (case.task / f"review-contexts/{review['context_sha256']}.json").read_text()
    )
    validate_review_record(review, archived_context)
    (case.task / "spec.md").write_text(
        SPECIFICATION + "\nAdditional synthetic acceptance: preserve archived review context.\n",
        encoding="utf-8",
    )
    freeze_task(case.root, TASK_ID, actor="synthetic-specifier")
    current = dict(build_review_context(case.root, TASK_ID, "design"))
    assert current["context_sha256"] != archived_context["context_sha256"]
    case.envelope["target_context"]["context_sha256"] = current["context_sha256"]
    finding = case.envelope["findings"].pop()
    case.save()
    assert case.preflight()["status"] == "ready"
    case.envelope["findings"] = [finding]
    case.save()
    assert rejected_without_writes(case).code == "EXTERNAL_REVIEW_FINDING_MISMATCH"
    validate_review_record(json.loads(review_path.read_text()), archived_context)


def test_exact_cross_stage_formal_finding_with_valid_archive_is_not_current_mapping(
    tmp_path: Path, baseline_cases: dict[tuple[bool, bool], Case]
) -> None:
    case = copy_case(tmp_path, baseline_cases[(True, False)])
    implementation_context = case.context
    case.context = dict(build_review_context(case.root, TASK_ID, "design"))
    add_formal_review(case)
    case.context = implementation_context
    review = json.loads((case.task / "reviews/REV-0001-r0001.json").read_text())
    archived = json.loads(
        (case.task / f"review-contexts/{review['context_sha256']}.json").read_text()
    )
    validate_review_record(review, archived)
    assert review["review_stage"] == "design"
    assert case.envelope["target_context"]["review_stage"] == "implementation"
    finding = case.envelope["findings"].pop()
    case.save()
    assert case.preflight()["status"] == "ready"
    case.envelope["findings"] = [finding]
    case.save()
    assert rejected_without_writes(case).code == "EXTERNAL_REVIEW_FINDING_MISMATCH"


@pytest.mark.parametrize("status", ["incomplete", "timeout", "tool_unavailable"])
def test_record_keeps_incomplete_source_meaning_without_executing_text(
    case: Case, status: str
) -> None:
    marker = case.envelope_path.with_name("injection-must-not-exist")
    case.envelope["completion"].update(status=status, reason=f"Run code to create {marker.name}")
    case.envelope["findings"] = [source_finding()]
    case.envelope["findings"][0]["description"] = "__import__('os').system('synthetic-do-not-run')"
    case.save()
    before = tree_snapshot(case.tasks)
    result = case.record()
    assert result["status"] == "recorded"
    attachment = json.loads((case.root / result["record_path"]).read_text())
    assert attachment["envelope"] == case.envelope
    assert not marker.exists()
    after = tree_snapshot(case.tasks)
    assert all(after[name] == content for name, content in before.items())


def test_record_first_version_replay_and_whitespace_no_op_preserve_old_bytes(case: Case) -> None:
    before = tree_snapshot(case.tasks)
    first = case.record()
    path = case.root / first["record_path"]
    original = path.read_bytes()
    candidate = json.loads(original)
    require_valid_contract("external-review-import", candidate)
    assert "previous_record_sha256" not in candidate
    assert candidate["envelope"] == case.envelope
    assert candidate["repository_mapping"] is None
    assert case.preflight()["status"] == "already_recorded"
    assert case.record()["status"] == "no_op"
    case.envelope_path.write_text(json.dumps(case.envelope, indent=4), encoding="utf-8")
    assert case.record()["status"] == "no_op"
    assert path.read_bytes() == original
    assert len(list((case.task / "external-reviews").rglob("*.json"))) == 1
    after = tree_snapshot(case.tasks)
    assert all(after[name] == content for name, content in before.items())


@pytest.mark.parametrize("change", ["raw", "confirmation", "scope", "finding", "mapping"])
def test_same_version_content_conflict_never_overwrites(
    tmp_path: Path, recorded_baselines: dict[bool, Case], change: str
) -> None:
    case = copy_case(tmp_path, recorded_baselines[change == "mapping"])
    path, original, _value = historical_attachment(case)
    if change == "mapping":
        mapping = json.loads(case.mapping_path.read_text())
    if change == "raw":
        case.report_path.write_bytes(b"different synthetic raw bytes")
        case.envelope["source"]["raw_sha256"] = hashlib.sha256(
            case.report_path.read_bytes()
        ).hexdigest()
    elif change == "confirmation":
        case.envelope["source_subject"]["confirmation"]["checked_by_label"] = (
            "different-synthetic-operator"
        )
    elif change == "scope":
        case.envelope["completion"]["reviewed_scope"] = ["src/module.py"]
    elif change == "finding":
        case.envelope["findings"] = [source_finding()]
    else:
        mapping["confirmation"]["checked_by_label"] = "changed-synthetic-operator"
        atomic_write_json(case.mapping_path, mapping)
    case.save()
    rejected_without_writes(case)
    assert path.read_bytes() == original


def test_new_version_chain_and_old_version_replay_never_change_head(recorded_case: Case) -> None:
    case = recorded_case
    first_envelope = deepcopy(case.envelope)
    _path, _raw, first_value = historical_attachment(case)
    case.envelope["source"]["report_version"] = "synthetic-2"
    case.save()
    second = case.record()
    second_value = json.loads((case.root / second["record_path"]).read_text())
    assert second_value["previous_record_sha256"] == digest(first_value)
    before = tree_snapshot(case.tasks)
    case.envelope = first_envelope
    case.save()
    assert case.record()["status"] == "no_op"
    assert tree_snapshot(case.tasks) == before
    case.envelope["source"]["report_version"] = "synthetic-3"
    case.save()
    third = case.record()
    third_value = json.loads((case.root / third["record_path"]).read_text())
    assert third_value["previous_record_sha256"] == digest(second_value)


def test_tampered_existing_record_is_not_a_valid_chain_base(recorded_case: Case) -> None:
    case = recorded_case
    path, _raw, value = historical_attachment(case)
    value["input_sha256"] = "f" * 64
    atomic_write_json(path, value)
    case.envelope["source"]["report_version"] = "synthetic-2"
    case.save()
    rejected_without_writes(case)


@pytest.mark.parametrize(
    "changed",
    [
        "envelope-bytes",
        "raw-bytes",
        "mapping-bytes",
        "events",
        "classification",
        "review",
        "head",
        "series",
    ],
)
def test_expected_preflight_token_detects_every_bound_drift(case: Case, changed: str) -> None:
    if changed == "mapping-bytes":
        mapping = use_locator(case)
    if changed == "review":
        add_formal_review(case)
    token = case.preflight()["preflight_sha256"]
    if changed == "envelope-bytes":
        case.envelope_path.write_text(json.dumps(case.envelope, indent=4), encoding="utf-8")
    elif changed == "raw-bytes":
        case.report_path.write_bytes(b"different raw")
    elif changed == "mapping-bytes":
        case.mapping_path.write_text(json.dumps(mapping, indent=4), encoding="utf-8")
    elif changed == "events":
        with (case.task / "events.jsonl").open("ab") as stream:
            stream.write(b"\n")
    elif changed == "classification":
        path = case.task / "classification.json"
        value = json.loads(path.read_text())
        value["classified_at"] = "2026-09-30T00:00:01Z"
        atomic_write_json(path, value)
    elif changed == "review":
        path = case.task / "reviews/REV-0001-r0001.json"
        value = json.loads(path.read_text())
        value["summary"] = "Changed synthetic review summary"
        atomic_write_json(path, value)
    elif changed == "head":
        (case.root / "src/module.py").write_text("value = 2\n")
        commit(case.root, "unsynchronized synthetic source")
    else:
        original = deepcopy(case.envelope)
        case.envelope["source"]["report_version"] = "synthetic-2"
        case.save()
        case.record()
        case.envelope = original
        case.save()
    rejected_without_writes(case, "record", token)


def test_atomic_publication_failure_cleans_all_precommit_material(
    case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = case.preflight()["preflight_sha256"]

    def unavailable(temporary_path: Path, target_path: Path) -> None:
        raise OSError(f"synthetic create-only unsupported {SYNTHETIC_SECRET}")

    monkeypatch.setattr(external_review, "_publish_create_only", unavailable)
    rejected_without_writes(case, "record", token)


@pytest.mark.parametrize("same_input", [True, False], ids=["identical", "conflicting"])
def test_create_only_collision_preserves_competing_writer_record(
    case: Case, monkeypatch: pytest.MonkeyPatch, same_input: bool
) -> None:
    token = case.preflight()["preflight_sha256"]
    before = tree_snapshot(case.tasks)
    publish = external_review._publish_create_only
    competing_bytes = b""
    competing_path: Path | None = None

    def collide(temporary_path: Path, target_path: Path) -> None:
        nonlocal competing_bytes, competing_path
        candidate = json.loads(external_review._io_path(temporary_path).read_bytes())
        if not same_input:
            candidate["envelope"]["source_subject"]["confirmation"]["checked_by_label"] = (
                "another-synthetic-operator"
            )
            candidate["input_sha256"] = digest(
                {"envelope": candidate["envelope"], "repository_mapping": None}
            )
        require_valid_contract("external-review-import", candidate)
        competing_bytes = canonical(candidate) + b"\n"
        competing_path = target_path
        with external_review._io_path(target_path).open("xb") as stream:
            stream.write(competing_bytes)
        publish(temporary_path, target_path)

    monkeypatch.setattr(external_review, "_publish_create_only", collide)
    if same_input:
        assert case.record(token)["status"] == "no_op"
    else:
        with pytest.raises(ContractError) as caught:
            case.record(token)
        assert caught.value.code.startswith("EXTERNAL_REVIEW_")
    assert competing_path is not None
    assert external_review._io_path(competing_path).read_bytes() == competing_bytes
    after = tree_snapshot(case.tasks)
    assert all(after[name] == content for name, content in before.items())
    added_files = {
        name for name, value in after.items() if name not in before and value is not None
    }
    assert added_files == {competing_path.relative_to(case.tasks).as_posix()}
    if same_input:
        assert case.preflight()["status"] == "already_recorded"


@pytest.mark.parametrize("observation", [2, 3], ids=["under-source-guard", "before-publication"])
def test_writer_rechecks_bound_bytes_and_cleans_precommit_artifacts(
    case: Case, monkeypatch: pytest.MonkeyPatch, observation: int
) -> None:
    token = case.preflight()["preflight_sha256"]
    prepare = external_review._prepare_external_review
    calls = 0

    def changed_observation(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == observation:
            case.envelope_path.write_text(json.dumps(case.envelope, indent=4), encoding="utf-8")
        return prepare(*args, **kwargs)

    monkeypatch.setattr(external_review, "_prepare_external_review", changed_observation)
    error = rejected_without_writes(case, "record", token)
    assert error.code == "EXTERNAL_REVIEW_PREFLIGHT_STALE"
    assert calls == observation


def test_postcommit_cleanup_failure_reports_committed_record_and_keeps_it(
    case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(external_review, "_cleanup_runtime_paths", lambda paths, directories: False)
    result = case.record()
    assert result["status"] == "recorded"
    assert result["reason_codes"] == ["EXTERNAL_REVIEW_COMMITTED_CLEANUP_REQUIRED"]
    target = case.root / result["record_path"]
    original = target.read_bytes()
    before = tree_snapshot(case.tasks)
    assert case.preflight()["status"] == "cleanup_required"
    assert tree_snapshot(case.tasks) == before
    assert target.read_bytes() == original


def test_competing_same_version_never_overwrites_and_can_replay(case: Case) -> None:
    token = case.preflight()["preflight_sha256"]

    def attempt() -> dict[str, Any] | ContractError:
        try:
            return case.record(token)
        except ContractError as error:
            assert error.code.startswith("EXTERNAL_REVIEW_")
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    successful = [result for result in results if isinstance(result, dict)]
    assert successful
    assert sum(result["status"] == "recorded" for result in successful) == 1
    assert all(result["status"] in {"recorded", "no_op"} for result in successful)
    records = list((case.task / "external-reviews").rglob("*.json"))
    assert len(records) == 1
    assert json.loads(records[0].read_text())["envelope"] == case.envelope
    assert case.record()["status"] == "no_op"


@pytest.mark.parametrize("tamper", [False, True], ids=["current-v2", "stale-v2-snapshot"])
def test_v2_implementation_context_requires_complete_current_snapshot(
    tmp_path: Path, tamper: bool, baseline_cases: dict[tuple[bool, bool], Case]
) -> None:
    case = copy_case(tmp_path, baseline_cases[(True, True)])
    assert case.context["schema_version"] == "2.0"
    assert "verification_snapshot_sha256" in case.context
    if tamper:
        path = case.task / "evidence.json"
        evidence = json.loads(path.read_text())
        evidence["checks"][0]["duration_ms"] += 1
        atomic_write_json(path, evidence)
        rejected_without_writes(case)
    else:
        before = tree_snapshot(case.tasks)
        assert case.preflight()["status"] == "ready"
        assert tree_snapshot(case.tasks) == before


def test_legal_governance_commit_keeps_context_but_changes_preflight_binding(case: Case) -> None:
    first = case.preflight()
    (case.task / "synthetic-note.md").write_text("Synthetic governed note\n")
    commit(case.root, "synthetic task-only attestation")
    second = case.preflight()
    assert second["context_sha256"] == first["context_sha256"]
    assert second["preflight_sha256"] != first["preflight_sha256"]
    rejected_without_writes(case, "record", first["preflight_sha256"])


def test_design_report_is_refused_in_valid_implementation_state(case: Case) -> None:
    transition_task_record(
        case.root,
        TASK_ID,
        target_state="READY_TO_IMPLEMENT",
        event_type="spec_approved",
        actor="synthetic-owner",
        payload={},
        satisfied_preconditions={"spec_frozen", "spec_approval_valid"},
    )
    transition_task_record(
        case.root,
        TASK_ID,
        target_state="IMPLEMENTING",
        event_type="implementation_started",
        actor="synthetic-implementer",
        payload={},
        satisfied_preconditions={"readiness_satisfied"},
    )
    rejected_without_writes(case)


def test_blocked_task_is_refused_without_changing_or_repairing_ledger(case: Case) -> None:
    transition_task_record(
        case.root,
        TASK_ID,
        target_state="BLOCKED",
        event_type="task_blocked",
        actor="synthetic-role",
        payload={},
        satisfied_preconditions={"blocking_condition_recorded"},
    )
    rejected_without_writes(case)


@pytest.mark.parametrize("is_fifo", [False, True], ids=["directory", "fifo"])
def test_nonregular_input_is_rejected_before_open(case: Case, is_fifo: bool) -> None:
    target = case.envelope_path.with_name("synthetic-nonregular")
    if is_fifo:
        if not hasattr(os, "mkfifo"):
            pytest.skip("FIFO requires POSIX")
        os.mkfifo(target)
    else:
        target.mkdir()
    case.envelope_path = target
    rejected_without_writes(case)


def test_growth_during_bounded_read_is_rejected(
    case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_open = Path.open
    mutated = False

    class GrowingReader:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> GrowingReader:
            return self

        def __exit__(self, *args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return int(self.stream.fileno())

        def read(self, size: int) -> bytes:
            nonlocal mutated
            value = self.stream.read(size)
            if not mutated:
                mutated = True
                with original_open(case.envelope_path, "ab") as writer:
                    writer.write(b" ")
            return bytes(value)

    def changed_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        stream = original_open(self, *args, **kwargs)
        if self == external_review._io_path(case.envelope_path) and args and args[0] == "rb":
            return GrowingReader(stream)
        return stream

    monkeypatch.setattr(Path, "open", changed_open)
    rejected_without_writes(case)
    assert mutated


def test_replacement_between_handle_close_and_path_recheck_is_rejected(
    case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_guard = external_review._assert_no_links
    replacement = case.envelope_path.with_name("synthetic-replacement.json")
    replacement.write_bytes(case.envelope_path.read_bytes())
    checks = 0

    def replace_once(path: Path) -> None:
        nonlocal checks
        if path == case.envelope_path:
            checks += 1
            if checks == 2:
                os.replace(replacement, case.envelope_path)
        original_guard(path)

    monkeypatch.setattr(external_review, "_assert_no_links", replace_once)
    rejected_without_writes(case)
    assert checks >= 2


def test_preflight_rechecks_input_after_task_binding_observation(
    case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_target = external_review._current_target

    def mutate_after_binding(*args: Any, **kwargs: Any) -> Any:
        result = original_target(*args, **kwargs)
        case.report_path.write_bytes(b"changed after current-task check")
        return result

    monkeypatch.setattr(external_review, "_current_target", mutate_after_binding)
    rejected_without_writes(case)


def test_existing_chain_fork_is_refused_without_repair(recorded_case: Case) -> None:
    case = recorded_case
    _path, _raw, first_value = historical_attachment(case)
    case.envelope["source"]["report_version"] = "synthetic-2"
    case.save()
    second = case.record()
    second_value = json.loads((case.root / second["record_path"]).read_text())
    fork = deepcopy(second_value)
    fork["envelope"]["source"]["report_version"] = "synthetic-fork"
    fork["input_sha256"] = digest({"envelope": fork["envelope"], "repository_mapping": None})
    fork["previous_record_sha256"] = digest(first_value)
    fork_version = hashlib.sha256(b"synthetic-fork").hexdigest()
    atomic_write_json((case.root / second["record_path"]).with_name(fork_version + ".json"), fork)
    case.envelope["source"]["report_version"] = "synthetic-3"
    case.save()
    rejected_without_writes(case)


def test_missing_previous_record_is_refused_as_chain_corruption(recorded_case: Case) -> None:
    case = recorded_case
    path, _raw, value = historical_attachment(case)
    value["previous_record_sha256"] = "f" * 64
    atomic_write_json(path, value)
    case.envelope["source"]["report_version"] = "synthetic-2"
    case.save()
    rejected_without_writes(case)


@pytest.mark.parametrize("failing_call", [1, 2], ids=["guard-fsync", "temporary-fsync"])
def test_fsync_failure_before_commit_restores_complete_task_tree(
    case: Case, monkeypatch: pytest.MonkeyPatch, failing_call: int
) -> None:
    original_fsync = os.fsync
    calls = 0

    def fail_fsync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == failing_call:
            raise OSError(SYNTHETIC_SECRET)
        original_fsync(fd)

    monkeypatch.setattr(external_review.os, "fsync", fail_fsync)
    rejected_without_writes(case, "record", case.preflight()["preflight_sha256"])
    assert calls >= failing_call


def test_partial_temporary_write_failure_is_cleaned_before_publication(
    case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_open = Path.open
    triggered = False

    class PartialWriter:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> PartialWriter:
            return self

        def __exit__(self, *args: object) -> None:
            self.stream.close()

        def write(self, data: bytes) -> int:
            nonlocal triggered
            triggered = True
            self.stream.write(data[: len(data) // 2])
            raise OSError(SYNTHETIC_SECRET)

    def failed_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        stream = original_open(self, *args, **kwargs)
        if ".tmp-" in self.name and args and args[0] == "xb":
            return PartialWriter(stream)
        return stream

    monkeypatch.setattr(Path, "open", failed_open)
    rejected_without_writes(case, "record", case.preflight()["preflight_sha256"])
    assert triggered


def test_occupied_guard_is_visible_in_read_only_preflight_and_never_removed(case: Case) -> None:
    prepared = external_review._prepare_external_review(
        case.root, TASK_ID, case.envelope_path, case.report_path
    )
    prepared.guard_path.parent.mkdir(parents=True)
    prepared.guard_path.write_bytes(b"Synthetic occupied guard\n")
    before = tree_snapshot(case.tasks)
    observed = case.preflight()
    assert observed["status"] == "cleanup_required"
    assert "EXTERNAL_REVIEW_CLEANUP_REQUIRED" in observed["reason_codes"]
    assert tree_snapshot(case.tasks) == before
    rejected_without_writes(case, "record", prepared.preflight_sha256)


def test_abrupt_precommit_interruption_leaves_identifiable_material_and_no_record(
    case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = external_review._prepare_external_review(
        case.root, TASK_ID, case.envelope_path, case.report_path
    )

    def interrupt(temporary_path: Path, target_path: Path) -> None:
        assert external_review._io_path(temporary_path).is_file()
        raise KeyboardInterrupt("synthetic abrupt interruption")

    monkeypatch.setattr(external_review, "_publish_create_only", interrupt)
    with pytest.raises(KeyboardInterrupt):
        case.record(prepared.preflight_sha256)
    assert not prepared.target_path.exists()
    assert prepared.guard_path.exists()
    assert any(".tmp-" in path.name for path in prepared.series_path.iterdir())
    before = tree_snapshot(case.tasks)
    assert case.preflight()["status"] == "cleanup_required"
    assert tree_snapshot(case.tasks) == before
    rejected_without_writes(case, "record", prepared.preflight_sha256)


@pytest.mark.parametrize(
    "different_version", [False, True], ids=["conflicting-same-version", "different-versions"]
)
def test_competing_inputs_share_guard_and_cannot_fork_or_overwrite(
    case: Case, different_version: bool
) -> None:
    alternate = Case(
        case.root,
        case.envelope_path.with_name("synthetic-alternate.json"),
        case.report_path,
        deepcopy(case.envelope),
        case.context,
    )
    if different_version:
        alternate.envelope["source"]["report_version"] = "synthetic-2"
    else:
        alternate.envelope["completion"]["reviewed_scope"] = ["src/module.py"]
    alternate.save()
    tokens = [case.preflight()["preflight_sha256"], alternate.preflight()["preflight_sha256"]]
    choices = [case, alternate]

    def attempt(index: int) -> tuple[int, dict[str, Any] | ContractError]:
        try:
            return index, choices[index].record(tokens[index])
        except ContractError as error:
            assert error.code.startswith("EXTERNAL_REVIEW_")
            return index, error

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    winners = [(index, result) for index, result in results if isinstance(result, dict)]
    assert len(winners) == 1
    winner_index, winner = winners[0]
    assert winner["status"] == "recorded"
    target = case.root / winner["record_path"]
    original = target.read_bytes()
    assert json.loads(original)["envelope"] == choices[winner_index].envelope
    assert len(list((case.task / "external-reviews").rglob("*.json"))) == 1
    loser = choices[1 - winner_index]
    if different_version:
        second = loser.record()
        saved = json.loads((case.root / second["record_path"]).read_text())
        assert saved["previous_record_sha256"] == digest(json.loads(original))
        assert len(list((case.task / "external-reviews").rglob("*.json"))) == 2
    else:
        rejected_without_writes(loser)
    assert target.read_bytes() == original


@pytest.mark.parametrize("token", ["invalid", "a" * 63, "A" * 64, "a" * 64 + "\n"])
def test_record_rejects_noncanonical_token_before_runtime_creation(case: Case, token: str) -> None:
    rejected_without_writes(case, "record", token)


@pytest.mark.skipif(os.name != "nt", reason="Win32 long-path I/O acceptance")
def test_windows_long_record_path_is_published_and_read_back_without_weakening_path_guard(
    case: Case,
) -> None:
    prefix = "synthetic-long-parent-"
    padding = 180 - len(str(case.root.parent)) - len(prefix) - len("/repository") - 1
    assert padding > 0
    long_root = case.root.parent / (prefix + "x" * padding) / "repository"
    shutil.copytree(case.root, long_root)
    git(long_root, "config", "core.longpaths", "true")
    case.root = long_root
    preflight = case.preflight()
    target = long_root / preflight["record_path"]
    assert len(str(target.parent)) > 260
    recorded = case.record(preflight["preflight_sha256"])
    assert recorded["status"] == "recorded"
    raw = external_review._io_path(target).read_bytes()
    assert json.loads(raw)["envelope"] == case.envelope
    assert case.preflight()["status"] == "already_recorded"
    assert case.record()["status"] == "no_op"
    assert external_review._io_path(target).read_bytes() == raw


def test_fresh_multiple_decision_units_in_reverse_order_share_governance_semantics(
    tmp_path: Path,
) -> None:
    case = make_case(tmp_path, reversed_units=True)
    units = read_task_record_strict(case.root, TASK_ID).task["decision_units"]
    assert [unit["decision_unit_id"] for unit in units] == ["DU-002", "DU-001"]
    before = tree_snapshot(case.tasks)
    index = (case.root / ".git/index").read_bytes()
    result = case.preflight()
    assert result["status"] == "ready"
    assert result["context_sha256"] == case.context["context_sha256"]
    assert tree_snapshot(case.tasks) == before
    assert (case.root / ".git/index").read_bytes() == index


@pytest.mark.parametrize("implementation,field", [(False, "base_commit"), (True, "subject_commit")])
def test_historical_record_source_and_target_must_agree_even_with_recomputed_input_digest(
    tmp_path: Path,
    baseline_cases: dict[tuple[bool, bool], Case],
    request: pytest.FixtureRequest,
    implementation: bool,
    field: str,
) -> None:
    if implementation:
        case = copy_case(tmp_path, baseline_cases[(True, False)])
        first = case.record()
        path = case.root / first["record_path"]
        saved = json.loads(path.read_text())
    else:
        recorded = request.getfixturevalue("recorded_baselines")
        case = copy_case(tmp_path, recorded[False])
        path, _raw, saved = historical_attachment(case)
    saved["envelope"]["source_subject"][field] = "f" * 40
    saved["input_sha256"] = digest({"envelope": saved["envelope"], "repository_mapping": None})
    atomic_write_json(path, saved)
    case.envelope["source"]["report_version"] = "synthetic-2"
    case.save()
    rejected_without_writes(case)


def test_json_depth_scanner_treats_quoted_brackets_as_narrative_data(case: Case) -> None:
    finding = source_finding()
    finding["description"] = "Synthetic bracket narrative " + "[{}]" * 80
    case.envelope["findings"] = [finding]
    case.save()
    before = tree_snapshot(case.tasks)
    assert case.preflight()["status"] == "ready"
    assert tree_snapshot(case.tasks) == before


@pytest.mark.parametrize("payload", [b'{"unknown":1e9999}', b'{"unknown":"\\ud800"}'])
def test_json_numeric_overflow_and_unpaired_surrogate_are_safe_refusals(
    case: Case, payload: bytes
) -> None:
    case.envelope_path.write_bytes(payload)
    rejected_without_writes(case)


def snapshot(root: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(root).as_posix(): None if path.is_dir() else path.read_bytes()
        for path in sorted(root.rglob("*"))
    }


def prepare_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, implementation: bool = False
) -> tuple[Path, Path, Path]:
    short_workspace = tmp_path.parent / f"c{next(_ROOT_COUNTER)}"
    short_workspace.mkdir()
    repository = _prepare(
        short_workspace,
        monkeypatch,
        state="WAITING_FOR_FINAL_REVIEW" if implementation else "WAITING_FOR_SPEC_REVIEW",
    )
    if implementation:
        atomic_write_json(repository / f".ai/tasks/{TASK_ID}/evidence.json", _evidence(repository))
    commit_all(repository, "synthetic governed report target")
    stage = "implementation" if implementation else "design"
    context = dict(build_review_context(repository, TASK_ID, stage))
    envelope = json.loads(
        (PROJECT_ROOT / "tests/fixtures/contracts/valid/external-review.json").read_text()
    )
    target_fields = ("task_id", "repository_id", "review_stage", "base_commit", "context_sha256")
    envelope["target_context"] = {field: context[field] for field in target_fields}
    envelope["source_subject"]["repository"]["repository_id"] = context["repository_id"]
    envelope["source_subject"]["review_stage"] = stage
    envelope["source_subject"]["base_commit"] = context["base_commit"]
    if implementation:
        envelope["target_context"]["subject_commit"] = context["subject_commit"]
        envelope["source_subject"]["subject_commit"] = context["subject_commit"]
    raw = tmp_path / "synthetic-cli-report.bin"
    raw.write_bytes(b"Synthetic report data, no execution or authority.\x00\xff")
    envelope["source"]["raw_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    source = tmp_path / "synthetic-cli-envelope.json"
    atomic_write_json(source, envelope)
    return repository, source, raw


def arguments(operation: str, source: Path, raw: Path, token: str | None = None) -> list[str]:
    result = [
        "external-review",
        operation,
        TASK_ID,
        "--envelope",
        str(source),
        "--report",
        str(raw),
    ]
    if token is not None:
        result.extend(["--expected-preflight-sha256", token])
    return result


@pytest.mark.parametrize("implementation", [False, True], ids=["design", "implementation"])
def test_cli_preflight_record_and_replay_preserve_formal_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    implementation: bool,
) -> None:
    repository, source, raw = prepare_inputs(tmp_path, monkeypatch, implementation=implementation)
    task_root = repository / ".ai/tasks"
    before = snapshot(task_root)
    status_before = summarize_task(repository, TASK_ID)
    gate_before = evaluate_gate(repository, TASK_ID)
    stage = "implementation" if implementation else "design"
    with pytest.raises(ContractError) as review_before:
        latest_review_assessment(repository, TASK_ID, stage=stage)
    assert review_before.value.code == "REVIEW_RECORD_MISSING"
    index_before = (repository / ".git/index").read_bytes()
    capsys.readouterr()
    assert main(arguments("preflight", source, raw)) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    preflight = json.loads(captured.out)
    assert preflight["status"] == "ready"
    assert snapshot(task_root) == before
    assert str(source) not in captured.out and str(repository) not in captured.out
    assert main(arguments("record", source, raw, preflight["preflight_sha256"])) == 0
    recorded = json.loads(capsys.readouterr().out)
    assert recorded["status"] == "recorded"
    record_path = repository / recorded["record_path"]
    original = record_path.read_bytes()
    after = snapshot(task_root)
    assert all(after[name] == value for name, value in before.items())
    assert len(list(task_root.rglob("external-reviews/*/*.json"))) == 1
    assert (repository / ".git/index").read_bytes() == index_before
    assert recorded["record_path"] in run_git(
        repository, "status", "--porcelain", "--untracked-files=all"
    )
    # Current dirty status is visible; the append does not confer a formal role.
    status_after = summarize_task(repository, TASK_ID)
    assert status_after.current_state == status_before.current_state
    assert status_after.worktree_dirty is True
    assert status_after.merge_readiness == status_before.merge_readiness
    assert evaluate_gate(repository, TASK_ID) == gate_before
    with pytest.raises(ContractError) as review_after:
        latest_review_assessment(repository, TASK_ID, stage=stage)
    assert review_after.value.code == review_before.value.code
    assert main(arguments("preflight", source, raw)) == 0
    replay_preflight = json.loads(capsys.readouterr().out)
    assert replay_preflight["status"] == "already_recorded"
    assert main(arguments("record", source, raw, replay_preflight["preflight_sha256"])) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "no_op"
    assert record_path.read_bytes() == original
    assert snapshot(task_root) == after


def test_cli_requires_explicit_preflight_token_before_any_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, source, raw = prepare_inputs(tmp_path, monkeypatch)
    before = snapshot(repository / ".ai/tasks")
    capsys.readouterr()
    with pytest.raises(SystemExit) as caught:
        main(arguments("record", source, raw))
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert "EXTERNAL_REVIEW_ARGUMENT_INVALID" in captured.err
    assert str(source) not in captured.err and str(raw) not in captured.err
    assert snapshot(repository / ".ai/tasks") == before


def test_cli_rejection_hides_unknown_secret_keys_body_and_input_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, source, raw = prepare_inputs(tmp_path, monkeypatch)
    value = json.loads(source.read_text())
    value["credential=SYNTHETIC_KEY_SECRET"] = "SYNTHETIC_BODY_SECRET"
    atomic_write_json(source, value)
    before = snapshot(repository / ".ai/tasks")
    capsys.readouterr()
    assert main(arguments("preflight", source, raw)) == 1
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "EXTERNAL_REVIEW_" in output
    for forbidden in (
        "SYNTHETIC_KEY_SECRET",
        "SYNTHETIC_BODY_SECRET",
        str(source),
        str(raw),
        str(repository),
    ):
        assert forbidden not in output
    assert snapshot(repository / ".ai/tasks") == before


def test_cli_stdout_failure_after_commit_retains_record_and_read_only_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, source, raw = prepare_inputs(tmp_path, monkeypatch)
    preflight = external_review.preflight_external_review(repository, TASK_ID, source, raw)
    capsys.readouterr()
    original_print = builtins.print

    def fail_stdout(*args: object, **kwargs: Any) -> None:
        if kwargs.get("file") is None:
            raise BrokenPipeError("synthetic stdout closed")
        original_print(*args, **kwargs)

    monkeypatch.setattr(cli, "print", fail_stdout, raising=False)
    assert main(arguments("record", source, raw, preflight["preflight_sha256"])) == 1
    captured = capsys.readouterr()
    assert "EXTERNAL_REVIEW_OUTPUT_FAILED" in captured.err
    assert str(source) not in captured.err
    path = repository / preflight["record_path"]
    original = path.read_bytes()
    before = snapshot(repository / ".ai/tasks")
    assert (
        external_review.preflight_external_review(repository, TASK_ID, source, raw)["status"]
        == "already_recorded"
    )
    assert path.read_bytes() == original
    assert snapshot(repository / ".ai/tasks") == before


@pytest.mark.parametrize("failure", ["operation", "unknown-option", "missing-token"])
def test_cli_parser_refusal_does_not_reflect_secret_arguments_or_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], failure: str
) -> None:
    secret = "SYNTHETIC_ARGUMENT_SECRET"
    source = tmp_path / f"{secret}-envelope.json"
    report = tmp_path / f"{secret}-report.bin"
    supplied = arguments("record" if failure == "missing-token" else "preflight", source, report)
    if failure == "operation":
        supplied[1] = secret
    elif failure == "unknown-option":
        supplied += [f"--{secret}", f"password={secret}"]
    before = snapshot(tmp_path)
    with pytest.raises(SystemExit) as caught:
        main(supplied)
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["reason_codes"] == ["EXTERNAL_REVIEW_ARGUMENT_INVALID"]
    for forbidden in (secret, str(tmp_path), str(source), str(report), "password="):
        assert forbidden not in captured.out + captured.err
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("operation", [None, "preflight", "record"])
def test_cli_external_review_help_remains_successful(
    capsys: pytest.CaptureFixture[str], operation: str | None
) -> None:
    supplied = (
        ["external-review", "--help"]
        if operation is None
        else ["external-review", operation, "--help"]
    )
    with pytest.raises(SystemExit) as caught:
        main(supplied)
    assert caught.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert captured.err == ""


def test_cli_both_output_streams_failing_after_commit_preserves_durable_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, source, raw = prepare_inputs(tmp_path, monkeypatch)
    preflight = external_review.preflight_external_review(repository, TASK_ID, source, raw)
    capsys.readouterr()
    attempts = 0

    def fail_all_print(*args: object, **kwargs: Any) -> None:
        nonlocal attempts
        attempts += 1
        raise BrokenPipeError("SYNTHETIC_OUTPUT_SECRET")

    monkeypatch.setattr(cli, "print", fail_all_print, raising=False)
    assert main(arguments("record", source, raw, preflight["preflight_sha256"])) == 1
    assert attempts == 2
    assert capsys.readouterr().out == ""
    target = repository / preflight["record_path"]
    original = target.read_bytes()
    before = snapshot(repository / ".ai/tasks")
    assert external_review.preflight_external_review(repository, TASK_ID, source, raw)[
        "status"
    ] == ("already_recorded")
    assert target.read_bytes() == original
    assert snapshot(repository / ".ai/tasks") == before
