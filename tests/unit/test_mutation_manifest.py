"""Strict, read-only validation tests for the phase-two mutation manifest."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from aiflow.contracts import validate_contract
from aiflow.errors import ContractError
from aiflow.mutation_manifest import CANONICAL_MANIFEST_PATH, load_mutation_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def manifest_value() -> dict[str, Any]:
    """Return a valid five-item declaration without borrowing repository state."""
    declarations = (
        (
            "MUT-V2-001",
            "V2_REQUIRED_CHECK_SET",
            "src/aiflow/policy.py",
            "_validate_cross_file",
            "drop_targeted_mutation_required_check",
            "tests/unit/test_policy.py::test_v2_policy_requires_ordered_semantic_prefix_and_fixed_required_extras",
        ),
        (
            "MUT-V2-002",
            "V2_VERIFIER_INDEPENDENCE",
            "src/aiflow/verifier_service.py",
            "validate_verifier_actor",
            "allow_same_verifier_actor",
            "tests/integration/test_verify_command.py::test_v2_actor_rejections_happen_before_plan_or_runner",
        ),
        (
            "MUT-V2-003",
            "V2_CODE_APPROVAL_REQUIRES_PASSING_EVIDENCE",
            "src/aiflow/approval.py",
            "_v2_evidence_current",
            "allow_nonpassing_required_check",
            "tests/integration/test_mutation_manifest_contract.py::test_v2_code_approval_rejects_nonpassing_required_check",
        ),
        (
            "MUT-V2-004",
            "V2_GATE_REQUIRES_KILLED_MUTATIONS",
            "src/aiflow/gate.py",
            "_v2_gate_facts",
            "accept_non_killed_mutation",
            "tests/integration/test_mutation_manifest_contract.py::test_v2_gate_rejects_non_killed_mutation",
        ),
        (
            "MUT-V2-005",
            "V2_SNAPSHOT_BINDS_VERIFICATION_FACTS",
            "src/aiflow/evidence.py",
            "validate_v2_snapshot",
            "ignore_snapshot_mismatch",
            "tests/unit/test_evidence.py::test_v2_snapshot_rejects_mutation_of_bound_verification_facts",
        ),
    )
    return {
        "schema_version": "1.0",
        "manifest_id": "phase-02-critical",
        "scope": "phase-02-critical-safeguards",
        "mutations": [
            {
                "mutation_id": mutation_id,
                "safeguard_id": safeguard_id,
                "target": target,
                "target_symbol": target_symbol,
                "operator": operator,
                "expected_detector": detector,
                "expected_outcome": "killed",
            }
            for mutation_id, safeguard_id, target, target_symbol, operator, detector in declarations
        ],
    }


def write_manifest(repository: Path, value: dict[str, Any]) -> None:
    path = repository / CANONICAL_MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_target_and_detector_files(repository: Path, value: dict[str, Any]) -> None:
    detectors: dict[Path, list[str]] = {}
    for mutation in value["mutations"]:
        assert isinstance(mutation, dict)
        target = repository / str(mutation["target"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"def {mutation['target_symbol']}():\n    return None\n", encoding="utf-8"
        )
        detector_file, function = str(mutation["expected_detector"]).split("::")
        detector = repository / detector_file
        detectors.setdefault(detector, []).append(function)
    for detector, functions in detectors.items():
        detector.parent.mkdir(parents=True, exist_ok=True)
        detector.write_text(
            "\n".join(f"def {function}():\n    assert True\n" for function in functions),
            encoding="utf-8",
        )


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    value = manifest_value()
    schema = tmp_path / ".ai" / "schemas" / "mutation-manifest.schema.json"
    schema.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPOSITORY_ROOT / ".ai" / "schemas" / schema.name, schema)
    write_target_and_detector_files(tmp_path, value)
    write_manifest(tmp_path, value)
    return tmp_path


def load_error(repository: Path) -> ContractError:
    with pytest.raises(ContractError) as caught:
        load_mutation_manifest(repository)
    return caught.value


def test_schema_accepts_a_complete_closed_manifest() -> None:
    assert validate_contract("mutation-manifest", manifest_value()) == []


@pytest.mark.parametrize("field", ["schema_version", "manifest_id", "scope", "mutations"])
def test_schema_rejects_missing_top_level_fields(field: str) -> None:
    value = manifest_value()
    value.pop(field)
    assert any(
        error.startswith(f"/{field}:") for error in validate_contract("mutation-manifest", value)
    )


def test_schema_rejects_extra_fields_and_empty_declarations() -> None:
    extra = manifest_value()
    extra["command"] = "not allowed"
    assert "/command: unexpected property" in validate_contract("mutation-manifest", extra)

    empty = manifest_value()
    empty["mutations"] = []
    assert validate_contract("mutation-manifest", empty)


@pytest.mark.parametrize("size", [4, 6])
def test_schema_requires_exactly_five_declarations(size: int) -> None:
    value = manifest_value()
    if size == 4:
        value["mutations"].pop()
    else:
        value["mutations"].append(deepcopy(value["mutations"][-1]))
    write_value = validate_contract("mutation-manifest", value)
    assert write_value


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("operator", "run_shell_command"),
        ("mutation_id", "not a mutation id"),
        ("expected_detector", "tests/unit/test_policy.py"),
        ("expected_detector", "tests/../src/aiflow/policy.py::test_required"),
        ("expected_outcome", "survived"),
    ],
)
def test_schema_rejects_invalid_operator_id_and_pytest_nodeid(field: str, bad_value: str) -> None:
    value = manifest_value()
    value["mutations"][0][field] = bad_value
    assert validate_contract("mutation-manifest", value)


def test_valid_nonobject_json_is_a_contract_failure(repository: Path) -> None:
    (repository / CANONICAL_MANIFEST_PATH).write_text("[]", encoding="utf-8")
    assert load_error(repository).code == "CONTRACT_VALIDATION_FAILED"


@pytest.mark.parametrize("change", ["order", "safeguard"])
def test_loader_rejects_noncanonical_order_or_fields(repository: Path, change: str) -> None:
    value = manifest_value()
    if change == "order":
        value["mutations"].reverse()
    else:
        value["mutations"][0]["safeguard_id"] = "V2_OTHER_SAFEGUARD"
    write_manifest(repository, value)
    assert load_error(repository).code == "CONTRACT_VALIDATION_FAILED"


@pytest.mark.parametrize(
    "field",
    ["mutation_id", "safeguard_id", "target", "operator", "expected_detector"],
)
def test_loader_rejects_each_independent_duplicate(repository: Path, field: str) -> None:
    value = manifest_value()
    value["mutations"][1][field] = value["mutations"][0][field]
    write_manifest(repository, value)
    assert load_error(repository).code == "MUTATION_MANIFEST_DUPLICATE"


@pytest.mark.parametrize(
    "target",
    [
        "/absolute.py",
        "src\\aiflow\\policy.py",
        "src//aiflow/policy.py",
        "src/aiflow/./policy.py",
        "src/aiflow/../outside.py",
        "tests/unit/test_policy.py",
        ".ai/policy/policy.py",
        ".ai/tasks/TASK-0001/task.py",
    ],
)
def test_loader_rejects_lexically_unsafe_or_nonimplementation_targets(
    repository: Path, target: str
) -> None:
    value = manifest_value()
    value["mutations"][0]["target"] = target
    write_manifest(repository, value)
    assert load_error(repository).code == "MUTATION_MANIFEST_PATH_INVALID"


def test_loader_rejects_a_missing_target(repository: Path) -> None:
    (repository / "src/aiflow/policy.py").unlink()
    assert load_error(repository).code == "MUTATION_MANIFEST_TARGET_MISSING"


def test_loader_rejects_a_missing_target_symbol(repository: Path) -> None:
    (repository / "src/aiflow/policy.py").write_text(
        "def other_symbol():\n    return None\n", encoding="utf-8"
    )
    assert load_error(repository).code == "MUTATION_MANIFEST_SYMBOL_MISSING"


def test_loader_rejects_a_missing_detector_file(repository: Path) -> None:
    detector = repository / "tests/unit/test_policy.py"
    detector.unlink()
    assert load_error(repository).code == "MUTATION_MANIFEST_DETECTOR_MISSING"


def test_loader_rejects_a_missing_detector_function(repository: Path) -> None:
    detector = repository / "tests/unit/test_policy.py"
    detector.write_text("def test_other():\n    assert True\n", encoding="utf-8")
    assert load_error(repository).code == "MUTATION_MANIFEST_DETECTOR_MISSING"


def test_loader_returns_immutable_stable_declarations_without_mutating_input(
    repository: Path,
) -> None:
    before = (repository / CANONICAL_MANIFEST_PATH).read_bytes()
    first = load_mutation_manifest(repository)
    second = load_mutation_manifest(repository)

    assert first == second
    assert isinstance(first.mutations, tuple)
    assert first.mutations[0].target == "src/aiflow/policy.py"
    assert (repository / CANONICAL_MANIFEST_PATH).read_bytes() == before


def test_loader_rejects_symlink_path_escape_deterministically(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Patch the resolver boundary so Windows symlink rights are unnecessary."""
    import aiflow.mutation_manifest as mutation_manifest

    value = manifest_value()
    value["mutations"][0]["target"] = "src/aiflow/linked.py"
    write_manifest(repository, value)

    # The production helper is intentionally the single resolve boundary used for targets.
    original = mutation_manifest._resolve_path

    def escaped(path: Path) -> Path:
        if path == repository / "src" / "aiflow" / "linked.py":
            return repository.parent / "outside.py"
        return original(path)

    monkeypatch.setattr(mutation_manifest, "_resolve_path", escaped)
    assert load_error(repository).code == "MUTATION_MANIFEST_PATH_ESCAPE"


def test_loader_rejects_schema_directory_escape_deterministically(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import aiflow.mutation_manifest as mutation_manifest

    original = mutation_manifest._resolve_path

    def escaped(path: Path) -> Path:
        if path == repository / ".ai" / "schemas":
            return repository.parent / "external-schemas"
        return original(path)

    monkeypatch.setattr(mutation_manifest, "_resolve_path", escaped)
    assert load_error(repository).code == "MUTATION_MANIFEST_PATH_ESCAPE"


def test_loader_rejects_duplicate_json_object_keys(repository: Path) -> None:
    path = repository / CANONICAL_MANIFEST_PATH
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            '"scope": "phase-02-critical-safeguards",',
            '"scope": "phase-02-critical-safeguards",\n  "scope": "phase-02-critical-safeguards",',
            1,
        ),
        encoding="utf-8",
    )
    assert load_error(repository).code == "MUTATION_MANIFEST_READ_FAILED"


def test_loader_does_not_accept_manifest_input_mutation(repository: Path) -> None:
    """Changing an in-memory copy cannot affect the read-only on-disk declaration."""
    value = manifest_value()
    copy = deepcopy(value)
    copy["mutations"][0]["expected_outcome"] = "survived"
    assert load_mutation_manifest(repository).mutations[0].expected_outcome == "killed"
