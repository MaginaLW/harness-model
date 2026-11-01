"""Real AST expectations for the installed-only required-check mutation.

A mutant accepting the missing safeguard is the intended injected defect, never
production verification PASS. No process, task action or native mutation runs.
"""

from __future__ import annotations

import ast
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest
from test_policy import v2_documents

from aiflow.errors import ContractError, PolicyError
from aiflow.mutation_runner import _outside_target_dump

ROOT = Path(__file__).resolve().parents[2]
POLICY_SOURCE = ROOT / "src/aiflow/policy.py"
SYMBOL = "_validate_cross_file"
EXTRAS = ("acceptance", "integration", "targeted_mutation", "independent_verifier")
COMPARISON = ast.parse(
    "tuple(check['id'] for check in v2_checks[len(v1_checks):]) != extras", mode="eval"
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


def _comparison(function: ast.FunctionDef) -> ast.Compare:
    expected = ast.dump(COMPARISON, include_attributes=False)
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


def test_installed_001_changes_only_the_unique_expected_comparison(copied_policy: Path) -> None:
    from aiflow import installed_mutations

    before = ast.parse(copied_policy.read_bytes())
    expected = deepcopy(before)
    comparison = _comparison(_target(expected))
    comparison.ops = [ast.NotIn()]
    comparison.comparators = [
        ast.Tuple(
            elts=[
                ast.Name(id="extras", ctx=ast.Load()),
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
    assignments = [
        node
        for node in ast.walk(_target(after))
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "extras" for target in node.targets)
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
