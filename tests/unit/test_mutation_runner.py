"""Deterministic seam tests for the isolated mutation runner."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

import aiflow.mutation_evidence as mutation_evidence
import aiflow.mutation_process as process
import aiflow.mutation_protocol as protocol
import aiflow.mutation_reporter as reporter
import aiflow.mutation_runner as runner
from aiflow.errors import ContractError, PolicyError
from aiflow.mutation_manifest import MutationManifest, load_mutation_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SUBJECT = "a" * 40


@pytest.fixture(scope="module")
def manifest() -> MutationManifest:
    return load_mutation_manifest(REPOSITORY_ROOT)


def _failure_code(call: Any) -> str:
    with pytest.raises(runner.MutationRunError) as caught:
        call()
    return caught.value.code


def _new_runner_authorization(
    root: Path, subject: str
) -> tuple[runner._MutationRunnerAuthorization, Path]:
    task_directory = root / ".ai" / "tasks" / "TASK-9999"
    task_directory.mkdir(parents=True, exist_ok=True)
    receipt = task_directory / f"action-use-{'a' * 64}.md"
    receipt.write_text("authorized\n", encoding="utf-8")
    action = task_directory / "action-v2-targeted-mutation-test.json"
    action.write_text("{}\n", encoding="utf-8")
    return _issue_test_authorization(root, subject, receipt), receipt


def _issue_test_authorization(
    root: Path, subject: str, receipt: Path
) -> runner._MutationRunnerAuthorization:
    task_id = "TASK-9999"
    return runner._issue_runner_authorization(
        root,
        task_id,
        subject,
        action_sha256="a" * 64,
        receipt_path=receipt,
        action_path=root / ".ai" / "tasks" / task_id / "action-v2-targeted-mutation-test.json",
        decision_unit_id="DU-001",
        spec_sha256="b" * 64,
        policy_sha256="c" * 64,
        base_commit="d" * 40,
        classification_input_sha256="e" * 64,
    )


def _authorized_run(root: Path, subject: str):
    authorization, receipt = _new_runner_authorization(root, subject)
    validator = runner._validate_authoritative_runner_launch
    runner._validate_authoritative_runner_launch = lambda _authorization: None
    try:
        return runner.run_targeted_mutations(root, subject, authorization=authorization)
    finally:
        runner._validate_authoritative_runner_launch = validator
        receipt.unlink(missing_ok=True)


def test_public_runner_requires_recorder_authorization(tmp_path: Path) -> None:
    with pytest.raises(ContractError) as caught:
        runner.run_targeted_mutations(tmp_path, SUBJECT)

    assert caught.value.code == "MUTATION_ACTION_REQUIRED"


def test_runner_authorization_is_one_shot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    authorization, receipt = _new_runner_authorization(tmp_path, SUBJECT)
    monkeypatch.setattr(runner, "_validate_authoritative_runner_launch", lambda _value: None)
    try:
        runner._consume_runner_authorization(tmp_path.resolve(), SUBJECT, authorization)
        with pytest.raises(ContractError) as caught:
            runner._consume_runner_authorization(tmp_path.resolve(), SUBJECT, authorization)
    finally:
        receipt.unlink(missing_ok=True)

    assert caught.value.code == "MUTATION_ACTION_REQUIRED"


def test_runner_authorization_forwards_all_bound_facts_to_authority_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorization, receipt = _new_runner_authorization(tmp_path, SUBJECT)
    captured: dict[str, object] = {}
    replay_calls = 0

    def authorize(
        repository_root: Path, task_id: str, subject_commit: str, **bindings: object
    ) -> None:
        nonlocal replay_calls
        replay_calls += 1
        captured.update(
            {
                "repository_root": repository_root,
                "task_id": task_id,
                "subject_commit": subject_commit,
                **bindings,
            }
        )

    monkeypatch.setattr(mutation_evidence, "_authorize_targeted_mutation_runner_launch", authorize)
    try:
        runner._consume_runner_authorization(tmp_path.resolve(), SUBJECT, authorization)
        with pytest.raises(ContractError) as caught:
            runner._consume_runner_authorization(tmp_path.resolve(), SUBJECT, authorization)
    finally:
        receipt.unlink(missing_ok=True)

    assert caught.value.code == "MUTATION_ACTION_REQUIRED"
    assert replay_calls == 1
    assert captured == {
        "repository_root": tmp_path.resolve(),
        "task_id": "TASK-9999",
        "subject_commit": SUBJECT,
        "action_sha256": "a" * 64,
        "receipt_path": receipt,
        "action_path": receipt.parent / "action-v2-targeted-mutation-test.json",
        "decision_unit_id": "DU-001",
        "spec_sha256": "b" * 64,
        "policy_sha256": "c" * 64,
        "base_commit": "d" * 40,
        "classification_input_sha256": "e" * 64,
        "receipt_device": authorization.receipt_device,
        "receipt_inode": authorization.receipt_inode,
    }


def test_runner_authorization_rejects_replaced_receipt(tmp_path: Path) -> None:
    authorization, receipt = _new_runner_authorization(tmp_path, SUBJECT)
    original = receipt.with_suffix(".original")
    receipt.replace(original)
    receipt.write_text("replacement\n", encoding="utf-8")

    with pytest.raises(ContractError) as caught:
        runner._consume_runner_authorization(tmp_path.resolve(), SUBJECT, authorization)

    assert caught.value.code == "MUTATION_ACTION_REQUIRED"
    assert receipt.read_text(encoding="utf-8") == "replacement\n"


def test_runner_authorization_rejects_pending_approval_transaction(tmp_path: Path) -> None:
    authorization, receipt = _new_runner_authorization(tmp_path, SUBJECT)
    (receipt.parent / "approval_pending.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ContractError) as caught:
        runner._consume_runner_authorization(tmp_path.resolve(), SUBJECT, authorization)

    assert caught.value.code == "MUTATION_ACTION_REQUIRED"


def test_runner_issuer_rejects_missing_or_malformed_receipt(tmp_path: Path) -> None:
    missing = tmp_path / ".ai" / "tasks" / "TASK-9999" / f"action-use-{'a' * 64}.md"
    with pytest.raises(ContractError) as caught:
        _issue_test_authorization(tmp_path, SUBJECT, missing)
    assert caught.value.code == "MUTATION_ACTION_REQUIRED"

    malformed = tmp_path / "action-use-malformed.md"
    malformed.write_text("invalid\n", encoding="utf-8")
    with pytest.raises(ContractError) as caught:
        _issue_test_authorization(tmp_path, SUBJECT, malformed)
    assert caught.value.code == "MUTATION_ACTION_REQUIRED"


def test_runner_authorization_rejects_deleted_receipt(tmp_path: Path) -> None:
    authorization, receipt = _new_runner_authorization(tmp_path, SUBJECT)
    receipt.unlink()

    with pytest.raises(ContractError) as caught:
        runner._consume_runner_authorization(tmp_path.resolve(), SUBJECT, authorization)

    assert caught.value.code == "MUTATION_ACTION_REQUIRED"


def test_runner_issuer_has_only_the_recorder_as_a_production_caller() -> None:
    callers = {
        path.name
        for path in (REPOSITORY_ROOT / "src" / "aiflow").glob("*.py")
        if path.name != "mutation_runner.py"
        and "_issue_runner_authorization" in path.read_text(encoding="utf-8")
    }

    assert callers == {"mutation_evidence.py"}


def _target_function(tree: ast.Module, symbol: str) -> ast.FunctionDef:
    matches = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == symbol
    ]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize("index", range(5))
def test_each_closed_operator_changes_only_its_exact_function(
    tmp_path: Path, manifest: MutationManifest, index: int
) -> None:
    declaration = manifest.mutations[index]
    source = (REPOSITORY_ROOT / declaration.target).read_text(encoding="utf-8")
    path = tmp_path / Path(declaration.target).name
    path.write_text(source, encoding="utf-8")
    before = ast.parse(source)

    runner._apply_mutation(declaration, path)

    result = path.read_text(encoding="utf-8")
    after = ast.parse(result)
    assert runner._outside_target_dump(after, declaration.target_symbol) == (
        runner._outside_target_dump(before, declaration.target_symbol)
    )
    assert ast.dump(_target_function(after, declaration.target_symbol)) != ast.dump(
        _target_function(before, declaration.target_symbol)
    )
    compile(result, str(path), "exec")

    function = _target_function(after, declaration.target_symbol)
    if index == 0:
        assignments = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "extras" for target in node.targets
            )
        ]
        assert len(assignments) == 1
        assert "targeted_mutation" not in ast.literal_eval(assignments[0].value)
    elif index in {1, 2, 4}:
        assert any(
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Constant)
            and node.test.value is False
            for node in ast.walk(function)
        )
    else:
        assignments = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Assign)
            and any(
                ast.unparse(target) == "result['v2_mutation_killed']" for target in node.targets
            )
        ]
        assert len(assignments) == 1
        assert isinstance(assignments[0].value, ast.Constant)
        assert assignments[0].value.value is True


def test_gate_operator_rejects_an_ambiguous_consumer_guard(
    tmp_path: Path, manifest: MutationManifest
) -> None:
    declaration = manifest.mutations[3]
    source = (REPOSITORY_ROOT / declaration.target).read_text(encoding="utf-8")
    anchor = '        result["v2_mutation_killed"] = mutation_facts.passed'
    assert source.count(anchor) == 1
    path = tmp_path / "gate.py"
    path.write_text(source.replace(anchor, f"{anchor}\n{anchor}"), encoding="utf-8")

    assert _failure_code(lambda: runner._apply_mutation(declaration, path)) == (
        "MUTATION_OPERATOR_PRECONDITION_FAILED"
    )


def test_operator_rejects_crossed_binding_missing_and_duplicate_anchor(
    tmp_path: Path, manifest: MutationManifest
) -> None:
    declaration = manifest.mutations[0]
    path = tmp_path / "policy.py"
    path.write_bytes((REPOSITORY_ROOT / declaration.target).read_bytes())

    crossed = replace(declaration, target="src/aiflow/gate.py")
    assert _failure_code(lambda: runner._apply_mutation(crossed, path)) == (
        "MUTATION_OPERATOR_UNSUPPORTED"
    )

    path.write_text(f"def {declaration.target_symbol}():\n    return None\n", encoding="utf-8")
    assert _failure_code(lambda: runner._apply_mutation(declaration, path)) == (
        "MUTATION_OPERATOR_PRECONDITION_FAILED"
    )

    original = ast.parse((REPOSITORY_ROOT / declaration.target).read_text(encoding="utf-8"))
    function = _target_function(original, declaration.target_symbol)
    path.write_text(f"{ast.unparse(function)}\n{ast.unparse(function)}\n", encoding="utf-8")
    assert _failure_code(lambda: runner._apply_mutation(declaration, path)) == (
        "MUTATION_OPERATOR_PRECONDITION_FAILED"
    )


def test_operator_normalizes_parse_compile_and_write_failures(
    tmp_path: Path, manifest: MutationManifest, monkeypatch: pytest.MonkeyPatch
) -> None:
    declaration = manifest.mutations[0]
    path = tmp_path / "policy.py"
    path.write_text("not valid python (", encoding="utf-8")
    assert _failure_code(lambda: runner._apply_mutation(declaration, path)) == (
        "MUTATION_OPERATOR_PRECONDITION_FAILED"
    )

    path.write_bytes((REPOSITORY_ROOT / declaration.target).read_bytes())
    original_write = Path.write_bytes

    def fail_write(self: Path, *_args: object, **_kwargs: object) -> int:
        if self == path:
            raise OSError("write blocked")
        return original_write(self, *_args, **_kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    assert _failure_code(lambda: runner._apply_mutation(declaration, path)) == (
        "MUTATION_PATCH_WRITE_FAILED"
    )


def test_public_results_are_frozen_exact_and_do_not_expose_scratch_paths() -> None:
    probe = runner.MutationProbe("MUT-V2-001", 0, 1, False, 7, None)
    result = runner.MutationRun("phase-02-critical", SUBJECT, (probe,), True, None)
    assert tuple(field.name for field in fields(probe)) == (
        "mutation_id",
        "baseline_exit_code",
        "mutant_exit_code",
        "timed_out",
        "duration_ms",
        "reason_code",
        "baseline_report",
        "mutant_report",
        "baseline_target_sha256",
        "mutant_target_sha256",
        "baseline_lifecycle",
        "mutant_lifecycle",
    )
    assert tuple(field.name for field in fields(result)) == (
        "manifest_id",
        "subject_commit",
        "probes",
        "main_tree_unchanged",
        "reason_code",
    )
    with pytest.raises(FrozenInstanceError):
        probe.reason_code = "changed"  # type: ignore[misc]
    assert "scratch" not in repr(result).lower()


def test_ast_guard_helpers_reject_ambiguous_or_wrong_shapes() -> None:
    function = _target_function(
        ast.parse("def target():\n    if True:\n        pass\n    if True:\n        pass\n"),
        "target",
    )
    assert runner._replace_guard(function, lambda _node: True) is False

    non_raise = ast.If(test=ast.Constant(True), body=[ast.Pass()], orelse=[])
    wrong_raise = ast.If(
        test=ast.Constant(True),
        body=[ast.Raise(exc=ast.Call(func=ast.Name(id="Other"), args=[], keywords=[]))],
        orelse=[],
    )
    assert runner._raises_contract_code(non_raise, "CODE") is False
    assert runner._raises_contract_code(wrong_raise, "CODE") is False


@pytest.mark.parametrize("name", ["", "../outside", "nested/name", "nested\\name"])
def test_validated_child_rejects_non_direct_or_escaping_names(tmp_path: Path, name: str) -> None:
    root = tmp_path.resolve()
    assert _failure_code(lambda: runner._validated_child(root, name)) == (
        "MUTATION_WORKTREE_PATH_ESCAPE"
    )


def test_validated_child_accepts_one_resolved_direct_child(tmp_path: Path) -> None:
    child = runner._validated_child(tmp_path.resolve(), "MUT-V2-001")
    assert child.parent == tmp_path.resolve()


def test_workspace_root_normalizes_creation_and_containment_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    system_temp = tmp_path / "system-temp"
    system_temp.mkdir()
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(system_temp))
    monkeypatch.setattr(
        runner.tempfile,
        "mkdtemp",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("creation failed")),
    )
    assert _failure_code(runner._create_workspace_root) == "MUTATION_WORKSPACE_INVALID"

    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(runner.tempfile, "mkdtemp", lambda **_kwargs: str(outside))
    assert _failure_code(runner._create_workspace_root) == "MUTATION_WORKSPACE_INVALID"


def test_git_wrapper_uses_empty_hooks_fixed_argv_and_no_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((arguments, kwargs))
        return subprocess.CompletedProcess(arguments, 0, b"ok", b"")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner._git(tmp_path, hooks, "rev-parse", "HEAD")
    assert result.stdout == b"ok"
    arguments, kwargs = calls[0]
    assert arguments == ["git", "-c", f"core.hooksPath={hooks}", "rev-parse", "HEAD"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 15

    (hooks / "unexpected").write_text("x", encoding="utf-8")
    with pytest.raises(ContractError) as caught:
        runner._git(tmp_path, hooks, "status")
    assert caught.value.code == "MUTATION_WORKSPACE_INVALID"


def test_subject_validation_allows_a_governance_attestation_head_descendant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    head = "b" * 40
    calls: list[tuple[tuple[str, ...], bool]] = []

    def ancestor(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append((arguments, check))
        if arguments[:2] == ("rev-parse", "--verify"):
            output = SUBJECT.encode()
        elif arguments == ("rev-parse", "HEAD"):
            output = head.encode()
        else:
            assert arguments == ("merge-base", "--is-ancestor", SUBJECT, head)
            assert check is False
            output = b""
        return subprocess.CompletedProcess(list(arguments), 0, output + b"\n", b"")

    monkeypatch.setattr(runner, "_git", ancestor)

    runner._validate_subject(tmp_path, hooks, SUBJECT)

    assert calls == [
        (("rev-parse", "--verify", f"{SUBJECT}^{{commit}}"), True),
        (("rev-parse", "HEAD"), True),
        (("merge-base", "--is-ancestor", SUBJECT, head), False),
    ]


def test_subject_validation_rejects_invalid_nonancestor_and_unresolved_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    with pytest.raises(ContractError) as caught:
        runner._validate_subject(tmp_path, hooks, "short")
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"

    monkeypatch.setattr(
        runner,
        "_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("git missing")),
    )
    with pytest.raises(ContractError) as caught:
        runner._validate_subject(tmp_path, hooks, SUBJECT)
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"

    def mismatch(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        output = ("c" * 40).encode() if "--verify" in arguments else ("b" * 40).encode()
        return subprocess.CompletedProcess(list(arguments), 0, output + b"\n", b"")

    monkeypatch.setattr(runner, "_git", mismatch)
    with pytest.raises(ContractError) as caught:
        runner._validate_subject(tmp_path, hooks, SUBJECT)
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"

    def nonancestor(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        if arguments[:2] == ("rev-parse", "--verify"):
            return subprocess.CompletedProcess(list(arguments), 0, SUBJECT.encode() + b"\n", b"")
        if arguments == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(list(arguments), 0, ("b" * 40).encode() + b"\n", b"")
        assert arguments == ("merge-base", "--is-ancestor", SUBJECT, "b" * 40)
        assert check is False
        return subprocess.CompletedProcess(list(arguments), 1, b"", b"")

    monkeypatch.setattr(runner, "_git", nonancestor)
    with pytest.raises(ContractError) as caught:
        runner._validate_subject(tmp_path, hooks, SUBJECT)
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"

    def invalid_head(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        output = SUBJECT.encode() if "--verify" in arguments else b"not-a-commit"
        return subprocess.CompletedProcess(list(arguments), 0, output + b"\n", b"")

    monkeypatch.setattr(runner, "_git", invalid_head)
    with pytest.raises(ContractError) as caught:
        runner._validate_subject(tmp_path, hooks, SUBJECT)
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"


def test_controlled_drift_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    paths = ("src/aiflow/policy.py", "tests/unit/test_policy.py")

    def dirty(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        output = b" M src/aiflow/policy.py\n" if arguments[0] == "status" else b""
        return subprocess.CompletedProcess(list(arguments), 0, output, b"")

    monkeypatch.setattr(runner, "_git", dirty)
    with pytest.raises(ContractError) as caught:
        runner._assert_controlled_paths_at_subject(tmp_path, hooks, SUBJECT, paths)
    assert caught.value.code == "MUTATION_SUBJECT_DRIFT"


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing_material",
        "duplicate_tree_path",
        "missing_row",
        "duplicate_row",
        "out_of_order",
        "extra_row",
        "incomplete_row",
        "unrelated_filter",
        "wrong_attribute",
        "reserved_driver",
    ],
)
def test_checkout_filter_checks_the_whole_tree_in_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str | None
) -> None:
    material = b"src/aiflow/policy.py"
    unrelated = b"docs/file\nwith newline"
    tree = b"\0".join((material, unrelated, b""))
    material_row = b"\0".join((material, b"filter", b"unset", b""))
    unrelated_row = b"\0".join((unrelated, b"filter", b"unspecified", b""))
    rows = material_row + unrelated_row
    if fault == "missing_material":
        tree = unrelated + b"\0"
    elif fault == "duplicate_tree_path":
        tree += unrelated + b"\0"
    elif fault == "missing_row":
        rows = material_row
    elif fault == "duplicate_row":
        rows = material_row * 2
    elif fault == "out_of_order":
        rows = unrelated_row + material_row
    elif fault == "extra_row":
        rows += unrelated_row
    elif fault == "incomplete_row":
        rows = rows[:-1]
    elif fault == "unrelated_filter":
        rows = material_row + unrelated_row.replace(b"unspecified", b"lfs")
    elif fault == "wrong_attribute":
        rows = rows.replace(b"filter", b"other")

    def git(
        root: Path, hooks: Path, *args: str, check: bool = True, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        assert root == tmp_path and hooks == tmp_path / "hooks"
        if args[0] == "ls-tree":
            assert args == ("ls-tree", "-r", "-z", "--name-only", "--full-tree", SUBJECT)
            return subprocess.CompletedProcess(args, 0, tree, b"")
        if args[0] == "check-attr":
            assert args == ("check-attr", f"--source={SUBJECT}", "-z", "--stdin", "filter")
            assert input_bytes == tree
            return subprocess.CompletedProcess(args, 0, rows, b"")
        assert args[:3] == ("config", "--name-only", "--get-regexp") and not check
        assert all(
            re.fullmatch(args[-1], f"filter.{name}.process") for name in ("unset", "unspecified")
        )
        if fault == "reserved_driver":
            return subprocess.CompletedProcess(args, 0, b"filter.unspecified.process\n", b"")
        return subprocess.CompletedProcess(args, 1, b"", b"")

    monkeypatch.setattr(runner, "_git", git)
    if fault is None:
        runner.assert_no_checkout_filters(
            tmp_path, tmp_path / "hooks", SUBJECT, (material.decode(),)
        )
    else:
        with pytest.raises(ContractError) as caught:
            runner.assert_no_checkout_filters(
                tmp_path, tmp_path / "hooks", SUBJECT, (material.decode(),)
            )
        assert caught.value.code == "MUTATION_WORKSPACE_INVALID"


def test_controlled_checks_accept_exact_clean_outputs_and_normalize_git_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    paths = ("src/aiflow/policy.py", "tests/unit/test_policy.py")

    def clean(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        return subprocess.CompletedProcess(list(arguments), 0, b"", b"")

    monkeypatch.setattr(runner, "_git", clean)
    runner._assert_controlled_paths_at_subject(tmp_path, hooks, SUBJECT, paths)

    monkeypatch.setattr(
        runner,
        "_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired([], 1)),
    )
    with pytest.raises(ContractError) as caught:
        runner._assert_controlled_paths_at_subject(tmp_path, hooks, SUBJECT, paths)
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"
    with pytest.raises(ContractError) as caught:
        runner.assert_no_checkout_filters(tmp_path, hooks, SUBJECT, paths)
    assert caught.value.code == "MUTATION_WORKSPACE_INVALID"


def test_snapshot_detects_byte_changes_and_read_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    controlled = tmp_path / "controlled.py"
    controlled.write_bytes(b"before")

    def facts(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        output = b"registry" if arguments[:2] == ("worktree", "list") else b"status"
        return subprocess.CompletedProcess(list(arguments), 0, output, b"")

    monkeypatch.setattr(runner, "_git", facts)
    snapshot = runner._snapshot_main_tree(tmp_path, hooks, ("controlled.py",))
    assert runner._main_tree_unchanged(tmp_path, hooks, snapshot) is True
    controlled.write_bytes(b"after")
    assert runner._main_tree_unchanged(tmp_path, hooks, snapshot) is False
    controlled.unlink()
    with pytest.raises(ContractError) as caught:
        runner._snapshot_main_tree(tmp_path, hooks, ("controlled.py",))
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"


def test_main_tree_comparison_normalizes_snapshot_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    snapshot = runner._MainSnapshot(b"status", b"registry", ())
    monkeypatch.setattr(
        runner,
        "_snapshot_main_tree",
        lambda *_args: (_ for _ in ()).throw(
            ContractError("snapshot failed", code="MUTATION_SUBJECT_INVALID")
        ),
    )
    assert runner._main_tree_unchanged(tmp_path, hooks, snapshot) is False


def test_minimal_environment_is_closed_and_contains_resolved_tool_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git = tmp_path / "git-bin" / ("git.exe" if os.name == "nt" else "git")
    git.parent.mkdir()
    git.write_bytes(b"")
    monkeypatch.setattr(runner.shutil, "which", lambda _name: str(git))
    monkeypatch.setenv("SECRET_TOKEN", "must-not-pass")
    monkeypatch.setenv("HTTPS_PROXY", "must-not-pass")
    worktree = tmp_path / "worktree"
    scratch = tmp_path / "scratch"

    environment = runner.detector_environment(worktree, scratch)

    expected = {
        "PATH",
        "TMP",
        "TEMP",
        "PYTHONPATH",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONNOUSERSITE",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    }
    if os.name == "nt":
        expected.add("SystemRoot")
    assert set(environment) == expected
    assert "SECRET_TOKEN" not in environment and "HTTPS_PROXY" not in environment
    assert environment["PYTHONPATH"] == str(worktree / "src")
    assert str(git.resolve().parent) in environment["PATH"].split(os.pathsep)
    assert str(Path(sys.executable).resolve().parent) in environment["PATH"].split(os.pathsep)


def test_minimal_environment_rejects_missing_tools_or_windows_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner.shutil, "which", lambda _name: None)
    assert _failure_code(lambda: runner.detector_environment(tmp_path, tmp_path)) == (
        "MUTATION_DETECTOR_EXECUTION_FAILED"
    )
    if os.name == "nt":
        monkeypatch.setattr(runner.shutil, "which", lambda _name: str(tmp_path / "git.exe"))
        monkeypatch.delenv("SystemRoot", raising=False)
        assert _failure_code(lambda: runner.detector_environment(tmp_path, tmp_path)) == (
            "MUTATION_DETECTOR_EXECUTION_FAILED"
        )


@pytest.mark.parametrize(
    ("exit_code", "reason"),
    [
        (0, None),
        (1, None),
        (2, "MUTATION_DETECTOR_INFRA_FAILURE"),
        (-9, "MUTATION_DETECTOR_INFRA_FAILURE"),
    ],
)
def test_detector_uses_exact_argv_and_normalizes_exit_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int, reason: str | None
) -> None:
    from aiflow.mutation_process import ProcessOutcome

    captured: dict[str, Any] = {}
    report = protocol.encode_report(_synthetic_report("MUT-V2-001"))

    def execute(arguments: list[str], **kwargs: object) -> ProcessOutcome:
        captured["arguments"] = arguments
        captured.update(kwargs)
        return ProcessOutcome(
            exit_code, report, None, False, 4, _clean_lifecycle(report, exit_code)
        )

    monkeypatch.setattr(runner, "detector_environment", lambda *_args: {"PATH": "fixed"})
    monkeypatch.setattr(runner, "run_bounded_process", execute)
    worktree = tmp_path / "worktree"
    result = runner._run_detector(worktree, tmp_path / "scratch", "MUT-V2-001", "a" * 64)

    assert result[0] == exit_code and result[1] is False and result[3] == reason
    assert captured["arguments"] == [
        sys.executable,
        "-I",
        "-B",
        str(worktree / "src/aiflow/mutation_reporter.py"),
        "MUT-V2-001",
        str(worktree),
        "a" * 64,
    ]
    if reason is None:
        assert result[4:] == (report, _clean_lifecycle(report, exit_code))
    assert captured["cwd"] == worktree
    assert captured["timeout_seconds"] == runner._TIMEOUT_SECONDS
    assert captured["max_output_bytes"] == 16384


@pytest.mark.parametrize(
    ("process_reason", "unknown", "expected", "timed_out"),
    [
        ("timeout", False, "MUTATION_DETECTOR_TIMEOUT", True),
        ("overflow", False, "MUTATION_DETECTOR_REPORT_INVALID", False),
        ("read_error", False, "MUTATION_DETECTOR_REPORT_INVALID", False),
        ("report_incomplete", False, "MUTATION_DETECTOR_REPORT_INVALID", False),
        ("processes_remaining", False, "MUTATION_DETECTOR_PROCESSES_REMAIN", False),
        ("launch_error", False, "MUTATION_DETECTOR_EXECUTION_FAILED", False),
        ("timeout", True, "MUTATION_PROCESS_CLEANUP_UNKNOWN", True),
        ("pytest_early_stop", False, "MUTATION_DETECTOR_EARLY_STOP", False),
    ],
)
def test_detector_process_failure_is_unverified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    process_reason: str,
    unknown: bool,
    expected: str,
    timed_out: bool,
) -> None:
    from aiflow.mutation_process import ProcessOutcome

    monkeypatch.setattr(runner, "detector_environment", lambda *_args: {})
    monkeypatch.setattr(
        runner,
        "run_bounded_process",
        lambda *_args, **_kwargs: ProcessOutcome(None, None, process_reason, unknown, 3),
    )
    result = runner._run_detector(tmp_path, tmp_path, "MUT-V2-001", "a" * 64)
    assert result == (None, timed_out, 3, expected, None, None)


def test_detector_rejects_bad_or_absent_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow.mutation_process import ProcessOutcome

    monkeypatch.setattr(runner, "detector_environment", lambda *_args: {})
    for report, expected in (
        (None, "MUTATION_DETECTOR_INFRA_FAILURE"),
        (b"not a report", "MUTATION_DETECTOR_REPORT_INVALID"),
    ):
        monkeypatch.setattr(
            runner,
            "run_bounded_process",
            lambda *_args, report=report, **_kwargs: ProcessOutcome(
                0, report, None, False, 1, _clean_lifecycle(report, 0) if report else None
            ),
        )
        result = runner._run_detector(tmp_path, tmp_path, "MUT-V2-001", "a" * 64)
        assert result[3] == expected and result[4] is None


def test_detector_environment_failure_is_a_stable_execution_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner,
        "detector_environment",
        lambda *_args: (_ for _ in ()).throw(runner.MutationRunError("MUTATION_WORKSPACE_INVALID")),
    )
    result = runner._run_detector(tmp_path, tmp_path, "MUT-V2-001", "a" * 64)
    assert result == (None, False, 0, "MUTATION_DETECTOR_EXECUTION_FAILED", None, None)


def test_detector_unexpected_process_exception_preserves_cleanup_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "detector_environment", lambda *_args: {})
    monkeypatch.setattr(
        runner,
        "run_bounded_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("unexpected")),
    )
    result = runner._run_detector(tmp_path, tmp_path, "MUT-V2-001", "a" * 64)
    assert result[3] == "MUTATION_PROCESS_CLEANUP_UNKNOWN" and result[4] is None


def test_windows_system_root_rejects_missing_or_invalid_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SystemRoot", raising=False)
    assert _failure_code(runner._windows_system_root) == "MUTATION_DETECTOR_EXECUTION_FAILED"

    monkeypatch.setenv("SystemRoot", str(tmp_path / "missing"))
    assert _failure_code(runner._windows_system_root) == "MUTATION_DETECTOR_EXECUTION_FAILED"


def test_worktree_create_and_cleanup_helpers_are_bounded_and_contained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    worktree = tmp_path / "MUT-V2-001"
    calls: list[tuple[str, ...]] = []

    def git(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        calls.append(arguments)
        return subprocess.CompletedProcess(list(arguments), 0, b"", b"")

    def verify_checkout_filters(
        path: Path, supplied_hooks: Path, subject: str, paths: tuple[str, ...]
    ) -> None:
        assert path == worktree and supplied_hooks == hooks and subject == SUBJECT and not paths
        calls.append(("verify_checkout_filters",))

    monkeypatch.setattr(runner, "assert_no_checkout_filters", verify_checkout_filters)
    monkeypatch.setattr(runner, "_git", git)
    runner._create_detached_worktree(tmp_path, hooks, worktree, SUBJECT)
    assert calls[0][:4] == ("worktree", "add", "--detach", "--no-checkout")
    assert calls[1:] == [("verify_checkout_filters",), ("checkout", "--detach", SUBJECT)]
    calls.clear()

    def reject_checkout(*_args: object) -> None:
        raise ContractError("filter present", code="MUTATION_WORKSPACE_INVALID")

    monkeypatch.setattr(runner, "assert_no_checkout_filters", reject_checkout)
    with pytest.raises(ContractError) as caught:
        runner._create_detached_worktree(tmp_path, hooks, worktree, SUBJECT)
    assert caught.value.code == "MUTATION_WORKSPACE_INVALID"
    assert [call[0] for call in calls] == ["worktree"]

    monkeypatch.setattr(
        runner,
        "_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired([], 1)),
    )
    assert (
        _failure_code(lambda: runner._create_detached_worktree(tmp_path, hooks, worktree, SUBJECT))
        == "MUTATION_WORKTREE_CREATE_FAILED"
    )

    outside = tmp_path.parent / "outside"
    assert runner._remove_worktree_with_retry(tmp_path, hooks, tmp_path, outside) is False
    assert runner._remove_tree_with_retry(tmp_path, outside) is False


def test_worktree_cleanup_retries_stop_after_three_git_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    worktree = root / "MUT-V2-001"
    worktree.mkdir()
    attempts: list[tuple[object, ...]] = []

    def blocked(*args: object, **_kwargs: object) -> None:
        attempts.append(args)
        raise OSError("git remove failed")

    monkeypatch.setattr(runner, "_git", blocked)
    monkeypatch.setattr(runner, "monotonic", lambda: 0.0)
    assert runner._remove_worktree_with_retry(tmp_path, hooks, root, worktree) is False
    assert len(attempts) == 3


def test_delete_retries_stop_after_three_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = tmp_path / "child"
    child.mkdir()
    attempts: list[Path] = []

    def blocked(path: Path, *, onerror: object) -> None:
        del onerror
        attempts.append(path)
        raise OSError("locked")

    monkeypatch.setattr(runner.shutil, "rmtree", blocked)
    monkeypatch.setattr(runner, "monotonic", lambda: 0.0)
    assert runner._remove_tree_with_retry(tmp_path, child) is False
    assert attempts == [child.resolve(), child.resolve(), child.resolve()]


def test_delete_clears_readonly_entry_only_inside_validated_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = tmp_path / "child"
    child.mkdir()
    readonly = child / "object"
    readonly.write_bytes(b"git object")
    readonly.chmod(stat.S_IREAD)
    retried: list[Path] = []

    def rmtree(path: Path, *, onerror: Any) -> None:
        try:
            raise PermissionError("readonly")
        except PermissionError:

            def remove(failed_path: str) -> None:
                target = Path(failed_path)
                retried.append(target)
                assert target.stat().st_mode & stat.S_IWRITE
                target.unlink()

            onerror(remove, str(readonly), sys.exc_info())
        path.rmdir()

    monkeypatch.setattr(runner.shutil, "rmtree", rmtree)
    assert runner._remove_tree_with_retry(tmp_path, child) is True
    assert retried == [readonly.resolve()]


def test_delete_readonly_callback_rejects_path_outside_validated_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = tmp_path / "child"
    child.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"keep")
    outside.chmod(stat.S_IREAD)
    retried: list[Path] = []

    def rmtree(_path: Path, *, onerror: Any) -> None:
        try:
            raise PermissionError("readonly")
        except PermissionError:
            onerror(
                lambda failed_path: retried.append(Path(failed_path)),
                str(outside),
                sys.exc_info(),
            )

    monkeypatch.setattr(runner.shutil, "rmtree", rmtree)
    monkeypatch.setattr(runner, "monotonic", lambda: 0.0)
    assert runner._remove_tree_with_retry(tmp_path, child) is False
    assert retried == []
    assert outside.read_bytes() == b"keep"


def _mock_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    manifest: MutationManifest,
    detector_results: Iterator[tuple[int | None, bool, int, str | None]],
    *,
    apply_failure: str | None = None,
    create_failure_at: int | None = None,
    cleanup_ok: bool = True,
    unchanged: bool = True,
) -> list[Path]:
    sequence = sum(1 for _ in tmp_path.glob("aiflow-mutation-unit-*"))
    workspace = tmp_path / f"aiflow-mutation-unit-{sequence}"
    workspace.mkdir()
    attempts: list[Path] = []
    monkeypatch.setattr(runner, "load_mutation_manifest", lambda _root: manifest)
    monkeypatch.setattr(runner, "_create_workspace_root", lambda: workspace)
    monkeypatch.setattr(runner, "_validate_subject", lambda *_args: None)
    monkeypatch.setattr(runner, "_assert_controlled_paths_at_subject", lambda *_args: None)
    monkeypatch.setattr(runner, "assert_no_checkout_filters", lambda *_args: None)
    materials = {path: b"synthetic" for path in runner._controlled_paths(manifest)}
    monkeypatch.setattr(runner, "subject_materials", lambda *_args: materials)
    monkeypatch.setattr(runner, "checkout_matches_materials", lambda *_args: True)
    monkeypatch.setattr(runner, "material_file_matches", lambda *_args: True)
    monkeypatch.setattr(runner, "loaded_engine_matches", lambda *_args: True)
    monkeypatch.setattr(runner, "_digest", lambda *_args: "a" * 64)
    monkeypatch.setattr(runner, "mutation_bytes", lambda *_args: b"synthetic mutation")
    snapshot = runner._MainSnapshot(b"status", b"worktrees", ())
    monkeypatch.setattr(runner, "_snapshot_main_tree", lambda *_args: snapshot)
    monkeypatch.setattr(runner, "_main_tree_unchanged", lambda *_args: unchanged)

    def create(_root: Path, _hooks: Path, path: Path, _subject: str) -> None:
        attempts.append(path)
        if create_failure_at is not None and len(attempts) == create_failure_at:
            raise runner.MutationRunError("MUTATION_WORKTREE_CREATE_FAILED")
        path.mkdir()

    monkeypatch.setattr(runner, "_create_detached_worktree", create)

    def detector(_root: Path, _scratch: Path, mutation_id: str, _digest: str) -> tuple:
        exit_code, timed_out, duration, reason = next(detector_results)
        report = None
        if reason is None and exit_code in {0, 1}:
            facts = _synthetic_report(mutation_id)
            if exit_code == 1:
                case, exception, anchor, semantic = protocol.SIGNATURES[mutation_id]
                target = next(item for item in facts["cases"] if item["case"] == case)
                target["call"] = "failed"
                target["failure"] = {
                    "exception": exception,
                    "anchor": anchor,
                    "semantic": semantic,
                }
            report = protocol.encode_report(facts)
        lifecycle = (
            _clean_lifecycle(report, exit_code)
            if report is not None and exit_code is not None
            else None
        )
        return exit_code, timed_out, duration, reason, report, lifecycle

    monkeypatch.setattr(runner, "_run_detector", detector)

    def apply(*_args: object) -> None:
        if apply_failure is not None:
            raise runner.MutationRunError(apply_failure)

    monkeypatch.setattr(runner, "_apply_mutation", apply)
    monkeypatch.setattr(runner, "_remove_worktree_with_retry", lambda *_args: cleanup_ok)
    monkeypatch.setattr(runner, "_remove_tree_with_retry", lambda *_args: True)
    return attempts


def test_orchestrator_rejects_main_source_drift_before_creating_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    attempts = _mock_orchestrator(monkeypatch, tmp_path, manifest, iter(()))
    monkeypatch.setattr(runner, "material_file_matches", lambda *_args: False)
    with pytest.raises(ContractError) as caught:
        _authorized_run(tmp_path, SUBJECT)
    assert caught.value.code == "MUTATION_SUBJECT_DRIFT"
    assert attempts == []


def test_orchestrator_rejects_loaded_engine_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    attempts = _mock_orchestrator(monkeypatch, tmp_path, manifest, iter(()))
    monkeypatch.setattr(runner, "loaded_engine_matches", lambda *_args: False)
    with pytest.raises(ContractError) as caught:
        _authorized_run(tmp_path, SUBJECT)
    assert caught.value.code == "MUTATION_SUBJECT_DRIFT"
    assert attempts == []


@pytest.mark.parametrize("at_mutant", [False, True])
def test_orchestrator_preserves_workspace_when_process_cleanup_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest, at_mutant: bool
) -> None:
    facts = [(None, False, 1, "MUTATION_PROCESS_CLEANUP_UNKNOWN")]
    if at_mutant:
        facts.insert(0, (0, False, 1, None))
    attempts = _mock_orchestrator(monkeypatch, tmp_path, manifest, iter(facts))
    removed: list[Path] = []
    monkeypatch.setattr(
        runner,
        "_remove_worktree_with_retry",
        lambda _root, _hooks, _workspace, path: removed.append(path) is None,
    )
    monkeypatch.setattr(
        runner,
        "_remove_tree_with_retry",
        lambda _parent, path: removed.append(path) is None,
    )
    result = _authorized_run(tmp_path, SUBJECT)
    assert result.reason_code == "MUTATION_PROCESS_CLEANUP_UNKNOWN"
    assert result.probes[0].reason_code == "MUTATION_PROCESS_CLEANUP_UNKNOWN"
    assert len(attempts) == 1 and attempts[0].exists()
    assert removed == []


@pytest.mark.parametrize("at_mutant", [False, True])
def test_orchestrator_rejects_missing_report_before_classifying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest, at_mutant: bool
) -> None:
    _mock_orchestrator(monkeypatch, tmp_path, manifest, iter(()))
    report = protocol.encode_report(_synthetic_report("MUT-V2-001"))
    facts = iter(
        [(0, False, 1, None, report, _clean_lifecycle(report, 0)), (1, False, 1, None, None, None)]
        if at_mutant
        else [(0, False, 1, None, None, None)]
    )
    monkeypatch.setattr(runner, "_run_detector", lambda *_args: next(facts))
    result = _authorized_run(tmp_path, SUBJECT)
    assert result.reason_code == "MUTATION_DETECTOR_REPORT_INVALID"
    assert result.probes[0].reason_code == "MUTATION_DETECTOR_REPORT_INVALID"


def test_orchestrator_rejects_mutant_setup_failure_even_with_exit_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    _mock_orchestrator(monkeypatch, tmp_path, manifest, iter(()))
    baseline = _synthetic_report("MUT-V2-001")
    mutant = _synthetic_report("MUT-V2-001")
    mutant["cases"][0]["setup"] = "failed"
    mutant["cases"][0]["call"] = "skipped"
    facts = iter(
        (code, False, 1, None, raw, _clean_lifecycle(raw, code))
        for code, raw in enumerate(
            (protocol.encode_report(baseline), protocol.encode_report(mutant))
        )
    )
    monkeypatch.setattr(runner, "_run_detector", lambda *_args: next(facts))
    result = _authorized_run(tmp_path, SUBJECT)
    assert result.probes[0].baseline_exit_code == 0
    assert result.probes[0].mutant_exit_code == 1
    assert result.reason_code == "MUTATION_DETECTOR_REPORT_INVALID"


def test_orchestrator_returns_five_ordered_success_facts_without_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    results = iter(
        (value for _ in range(5) for value in ((0, False, 2, None), (1, False, 3, None)))
    )
    attempts = _mock_orchestrator(monkeypatch, tmp_path, manifest, results)

    result = _authorized_run(tmp_path, SUBJECT)

    assert len(attempts) == 5
    assert tuple(probe.mutation_id for probe in result.probes) == tuple(
        item.mutation_id for item in manifest.mutations
    )
    assert all(probe.baseline_exit_code == 0 for probe in result.probes)
    assert all(probe.mutant_exit_code == 1 for probe in result.probes)
    assert all(probe.duration_ms == 5 and probe.reason_code is None for probe in result.probes)
    for probe in result.probes:
        assert probe.baseline_report is not None and probe.mutant_report is not None
        assert probe.baseline_lifecycle == _clean_lifecycle(probe.baseline_report, 0)
        assert probe.mutant_lifecycle == _clean_lifecycle(probe.mutant_report, 1)
    assert result.main_tree_unchanged is True and result.reason_code is None


def test_orchestrator_preserves_baseline_and_fills_after_operator_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    results = iter(((0, False, 4, None),))
    attempts = _mock_orchestrator(
        monkeypatch,
        tmp_path,
        manifest,
        results,
        apply_failure="MUTATION_OPERATOR_PRECONDITION_FAILED",
    )

    result = _authorized_run(tmp_path, SUBJECT)

    assert len(attempts) == 1
    assert result.probes[0].baseline_exit_code == 0
    assert result.probes[0].duration_ms == 4
    assert result.probes[0].reason_code == "MUTATION_OPERATOR_PRECONDITION_FAILED"
    assert all(item.reason_code == "MUTATION_NOT_EXECUTED" for item in result.probes[1:])
    assert result.reason_code == "MUTATION_OPERATOR_PRECONDITION_FAILED"


@pytest.mark.parametrize(
    ("detector_fact", "expected"),
    [
        ((1, False, 3, None), "MUTATION_BASELINE_FAILED"),
        ((None, True, 3, "MUTATION_DETECTOR_TIMEOUT"), "MUTATION_DETECTOR_TIMEOUT"),
    ],
)
def test_orchestrator_stops_on_baseline_or_detector_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: MutationManifest,
    detector_fact: tuple[int | None, bool, int, str | None],
    expected: str,
) -> None:
    attempts = _mock_orchestrator(monkeypatch, tmp_path, manifest, iter((detector_fact,)))
    result = _authorized_run(tmp_path, SUBJECT)
    assert len(attempts) == 1
    assert result.probes[0].reason_code == expected
    assert result.reason_code == expected
    assert all(item.reason_code == "MUTATION_NOT_EXECUTED" for item in result.probes[1:])


def test_orchestrator_stops_on_mutant_detector_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    attempts = _mock_orchestrator(
        monkeypatch,
        tmp_path,
        manifest,
        iter(
            (
                (0, False, 2, None),
                (None, True, 4, "MUTATION_DETECTOR_TIMEOUT"),
            )
        ),
    )
    result = _authorized_run(tmp_path, SUBJECT)
    assert len(attempts) == 1
    assert result.probes[0].baseline_exit_code == 0
    assert result.probes[0].timed_out is True
    assert result.probes[0].duration_ms == 6
    assert result.reason_code == "MUTATION_DETECTOR_TIMEOUT"


def test_orchestrator_stops_after_create_or_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    attempts = _mock_orchestrator(
        monkeypatch,
        tmp_path,
        manifest,
        iter(()),
        create_failure_at=1,
    )
    created = _authorized_run(tmp_path, SUBJECT)
    assert len(attempts) == 1
    assert created.probes[0].reason_code == "MUTATION_WORKTREE_CREATE_FAILED"
    assert created.reason_code == "MUTATION_WORKTREE_CREATE_FAILED"

    monkeypatch.undo()
    attempts = _mock_orchestrator(
        monkeypatch,
        tmp_path,
        manifest,
        iter(((0, False, 1, None), (1, False, 1, None))),
        cleanup_ok=False,
    )
    cleaned = _authorized_run(tmp_path, SUBJECT)
    assert len(attempts) == 1
    assert cleaned.reason_code == "MUTATION_WORKTREE_CLEANUP_FAILED"
    assert all(item.reason_code == "MUTATION_NOT_EXECUTED" for item in cleaned.probes[1:])


def test_item_contract_errors_are_normalized_for_body_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    attempts = _mock_orchestrator(monkeypatch, tmp_path, manifest, iter(()))
    monkeypatch.setattr(
        runner,
        "_create_detached_worktree",
        lambda *_args: (_ for _ in ()).throw(
            ContractError("hooks changed", code="MUTATION_WORKSPACE_INVALID")
        ),
    )
    body = _authorized_run(tmp_path, SUBJECT)
    assert attempts == []
    assert body.probes[0].reason_code == "MUTATION_WORKSPACE_INVALID"
    assert body.reason_code == "MUTATION_WORKSPACE_INVALID"

    monkeypatch.undo()
    _mock_orchestrator(
        monkeypatch,
        tmp_path,
        manifest,
        iter(((0, False, 1, None), (1, False, 1, None))),
    )
    monkeypatch.setattr(
        runner,
        "_remove_worktree_with_retry",
        lambda *_args: (_ for _ in ()).throw(
            ContractError("hooks changed", code="MUTATION_WORKSPACE_INVALID")
        ),
    )
    cleanup = _authorized_run(tmp_path, SUBJECT)
    assert cleanup.reason_code == "MUTATION_WORKTREE_CLEANUP_FAILED"
    assert all(item.reason_code == "MUTATION_NOT_EXECUTED" for item in cleanup.probes[1:])


def test_main_tree_change_overrides_cleanup_and_probe_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    _mock_orchestrator(
        monkeypatch,
        tmp_path,
        manifest,
        iter(((0, False, 1, None), (1, False, 1, None))),
        cleanup_ok=False,
        unchanged=False,
    )
    result = _authorized_run(tmp_path, SUBJECT)
    assert result.main_tree_unchanged is False
    assert result.reason_code == "MUTATION_MAIN_TREE_CHANGED"


def test_orchestrator_rejects_isolated_manifest_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    hooks: Path | None = None
    calls = 0

    def load(root: Path) -> MutationManifest:
        nonlocal calls
        calls += 1
        if calls == 1:
            return manifest
        return replace(manifest, manifest_id="drifted")

    monkeypatch.setattr(runner, "load_mutation_manifest", load)
    monkeypatch.setattr(runner, "_create_workspace_root", lambda: workspace)
    monkeypatch.setattr(runner, "_validate_subject", lambda *_args: None)
    monkeypatch.setattr(runner, "_assert_controlled_paths_at_subject", lambda *_args: None)
    monkeypatch.setattr(runner, "assert_no_checkout_filters", lambda *_args: None)
    materials = {path: b"synthetic" for path in runner._controlled_paths(manifest)}
    monkeypatch.setattr(runner, "subject_materials", lambda *_args: materials)
    monkeypatch.setattr(runner, "checkout_matches_materials", lambda *_args: True)
    monkeypatch.setattr(runner, "material_file_matches", lambda *_args: True)
    monkeypatch.setattr(runner, "loaded_engine_matches", lambda *_args: True)
    monkeypatch.setattr(
        runner, "_snapshot_main_tree", lambda *_args: runner._MainSnapshot(b"", b"", ())
    )
    monkeypatch.setattr(runner, "_main_tree_unchanged", lambda *_args: True)

    def create(_root: Path, supplied_hooks: Path, path: Path, _subject: str) -> None:
        nonlocal hooks
        hooks = supplied_hooks
        path.mkdir()

    monkeypatch.setattr(runner, "_create_detached_worktree", create)
    monkeypatch.setattr(runner, "_remove_worktree_with_retry", lambda *_args: True)
    monkeypatch.setattr(runner, "_remove_tree_with_retry", lambda *_args: True)
    result = _authorized_run(tmp_path, SUBJECT)
    assert hooks is not None
    assert result.probes[0].reason_code == "MUTATION_SUBJECT_DRIFT"
    assert result.reason_code == "MUTATION_SUBJECT_DRIFT"


def test_orchestrator_normalizes_isolated_loader_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    results = iter(((0, False, 1, None),))
    _mock_orchestrator(monkeypatch, tmp_path, manifest, results)
    calls = 0

    def load(_root: Path) -> MutationManifest:
        nonlocal calls
        calls += 1
        if calls == 1:
            return manifest
        raise OSError("isolated manifest unreadable")

    monkeypatch.setattr(runner, "load_mutation_manifest", load)
    result = _authorized_run(tmp_path, SUBJECT)
    assert result.probes[0].reason_code == "MUTATION_SUBJECT_DRIFT"


def test_runtime_os_error_returns_five_facts_and_always_cleans_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    attempts = _mock_orchestrator(monkeypatch, tmp_path, manifest, iter(()))
    cleanup_calls: list[Path] = []
    monkeypatch.setattr(
        runner,
        "_remove_tree_with_retry",
        lambda _parent, path: cleanup_calls.append(path) is None or True,
    )
    original_mkdir = Path.mkdir

    def mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if self.name.endswith("-tmp"):
            raise OSError("scratch unavailable")
        original_mkdir(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "mkdir", mkdir)
    result = _authorized_run(tmp_path, SUBJECT)
    assert attempts == []
    assert result.probes[0].reason_code == "MUTATION_WORKSPACE_INVALID"
    assert all(item.reason_code == "MUTATION_NOT_EXECUTED" for item in result.probes[1:])
    assert result.reason_code == "MUTATION_WORKSPACE_INVALID"
    assert len(cleanup_calls) == 1
    assert cleanup_calls[0].name.startswith("aiflow-mutation-unit-")


def test_workspace_failure_before_first_worktree_is_a_contract_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    monkeypatch.setattr(runner, "load_mutation_manifest", lambda _root: manifest)
    monkeypatch.setattr(
        runner,
        "_create_workspace_root",
        lambda: (_ for _ in ()).throw(runner.MutationRunError("MUTATION_WORKSPACE_INVALID")),
    )
    with pytest.raises(ContractError) as caught:
        _authorized_run(tmp_path, SUBJECT)
    assert caught.value.code == "MUTATION_WORKSPACE_INVALID"


def test_preflight_contract_and_os_errors_clean_workspace_and_remain_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    for failure, expected in (
        (ContractError("subject", code="MUTATION_SUBJECT_INVALID"), "MUTATION_SUBJECT_INVALID"),
        (OSError("hooks"), "MUTATION_WORKSPACE_INVALID"),
    ):
        workspace = tmp_path / f"workspace-{expected}-{failure.__class__.__name__}"
        workspace.mkdir()
        cleaned: list[Path] = []
        monkeypatch.setattr(runner, "load_mutation_manifest", lambda _root: manifest)
        monkeypatch.setattr(runner, "_create_workspace_root", lambda: workspace)
        monkeypatch.setattr(
            runner,
            "_validate_subject",
            lambda *_args, error=failure: (_ for _ in ()).throw(error),
        )
        monkeypatch.setattr(
            runner,
            "_remove_tree_with_retry",
            lambda _parent, path: cleaned.append(path) is None or True,
        )
        with pytest.raises(ContractError) as caught:
            _authorized_run(tmp_path, SUBJECT)
        assert caught.value.code == expected
        assert cleaned == [workspace]
        monkeypatch.undo()


def test_preflight_cleanup_failure_overrides_the_original_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    workspace = tmp_path / "workspace-cleanup-failure"
    workspace.mkdir()
    monkeypatch.setattr(runner, "load_mutation_manifest", lambda _root: manifest)
    monkeypatch.setattr(runner, "_create_workspace_root", lambda: workspace)
    monkeypatch.setattr(
        runner,
        "_validate_subject",
        lambda *_args: (_ for _ in ()).throw(
            ContractError("subject", code="MUTATION_SUBJECT_INVALID")
        ),
    )
    monkeypatch.setattr(runner, "_remove_tree_with_retry", lambda *_args: False)
    with pytest.raises(ContractError) as caught:
        _authorized_run(tmp_path, SUBJECT)
    assert caught.value.code == "MUTATION_WORKTREE_CLEANUP_FAILED"


def _synthetic_report(mutation_id: str) -> dict[str, Any]:
    return {
        "protocol": "1.0",
        "mutation_id": mutation_id,
        "python": "3.11",
        "pytest": "9.1.1",
        "platform": "windows",
        "cases": [
            {
                "case": case,
                "setup": "passed",
                "call": "passed",
                "teardown": "passed",
                "failure": None,
            }
            for case in protocol.CASES[mutation_id]
        ],
        "imports": {"target_sha256": "a" * 64, "reference_ok": True},
        "complete": True,
    }


@pytest.mark.parametrize(
    ("mutation_id", "case_name", "exception", "anchor", "semantic"),
    [
        ("MUT-V2-001", "only", "policy_error", "policy_valid", "policy_check_reference_invalid"),
        ("MUT-V2-002", "same_actor", "assertion_error", "actor_unexpected", "actor_sentinel"),
        ("MUT-V2-003", "only", "assertion_error", "approval_assert", "none"),
        ("MUT-V2-004", "only", "assertion_error", "gate_assert", "none"),
        ("MUT-V2-005", "only", "pytest_failed", "snapshot_raises", "missing_contract_error"),
    ],
)
def test_report_classifies_only_the_reviewed_call(
    mutation_id: str, case_name: str, exception: str, anchor: str, semantic: str
) -> None:
    report = _synthetic_report(mutation_id)

    def classify(exit_code: int, *, baseline: bool) -> str:
        return protocol.classify_report(
            report,
            mutation_id=mutation_id,
            target_sha256="a" * 64,
            exit_code=exit_code,
            baseline=baseline,
        )

    assert classify(0, baseline=True) == "passed"
    assert classify(0, baseline=False) == "survived"
    target = next(case for case in report["cases"] if case["case"] == case_name)
    target.update(
        call="failed", failure={"exception": exception, "anchor": anchor, "semantic": semantic}
    )
    assert classify(1, baseline=False) == "killed"
    assert classify(0, baseline=False) == "unverified"
    assert classify(1, baseline=True) == "unverified"


@pytest.mark.parametrize(
    "fault", ["setup", "teardown", "wrong_call", "skip", "xfail", "xpass", "reference"]
)
def test_protocol_synthetic_unrelated_or_incomplete_failure_is_unverified(fault: str) -> None:
    report = _synthetic_report("MUT-V2-002")
    target = report["cases"][1]
    target["call"] = "failed"
    target["failure"] = {
        "exception": "assertion_error",
        "anchor": "actor_unexpected",
        "semantic": "actor_sentinel",
    }
    if fault == "setup":
        target["setup"] = "failed"
        target["call"] = "notrun"
        target["failure"] = None
    elif fault == "teardown":
        target["teardown"] = "failed"
    elif fault == "wrong_call":
        target["failure"]["semantic"] = "unknown"
    elif fault == "reference":
        report["imports"]["reference_ok"] = False
    else:
        report["cases"][0]["call"] = {"skip": "skipped", "xfail": "xfailed", "xpass": "xpassed"}[
            fault
        ]
    assert (
        protocol.classify_report(
            report, mutation_id="MUT-V2-002", target_sha256="a" * 64, exit_code=1, baseline=False
        )
        == "unverified"
    )


@pytest.mark.parametrize(
    "fault", ["duplicate_case", "extra_case", "version", "target", "platform", "unknown_field"]
)
def test_protocol_rejects_synthetic_identity_and_schema_drift(fault: str) -> None:
    report = _synthetic_report("MUT-V2-002")
    if fault == "duplicate_case":
        report["cases"][1]["case"] = "blank"
    elif fault == "extra_case":
        report["cases"].append(dict(report["cases"][0]))
    elif fault == "version":
        report["pytest"] = "8.0.0"
    elif fault == "target":
        report["imports"]["target_sha256"] = "b" * 64
    elif fault == "platform":
        report["platform"] = "linux"
    else:
        report["private_path"] = "discard"
    with pytest.raises(ValueError):
        protocol.parse_report(protocol.encode_report(report), "MUT-V2-002", "a" * 64)


def test_protocol_rejects_duplicate_json_keys_trailing_bytes_and_overflow() -> None:
    data = protocol.encode_report(_synthetic_report("MUT-V2-001"))
    duplicate = data.replace(b'"complete":true', b'"complete":true,"complete":true')
    assert duplicate != data
    for invalid in (duplicate, data + b" ", b"x" * (protocol.MAX_REPORT_BYTES + 1)):
        with pytest.raises(ValueError):
            protocol.parse_report(invalid, "MUT-V2-001", "a" * 64)


@pytest.mark.parametrize(
    ("mutation_id", "line", "error", "expected"),
    [
        (
            "MUT-V2-001",
            206,
            PolicyError("safe", code="POLICY_CHECK_REFERENCE_INVALID"),
            ("policy_error", "policy_valid", "policy_check_reference_invalid"),
        ),
        (
            "MUT-V2-002",
            1272,
            AssertionError("V2 rejection must happen before plan parsing or runner start"),
            ("assertion_error", "actor_unexpected", "actor_sentinel"),
        ),
        (
            "MUT-V2-003",
            148,
            AssertionError("private"),
            ("assertion_error", "approval_assert", "none"),
        ),
        ("MUT-V2-004", 169, AssertionError("private"), ("assertion_error", "gate_assert", "none")),
        (
            "MUT-V2-005",
            165,
            pytest.fail.Exception("DID NOT RAISE ContractError"),
            ("pytest_failed", "snapshot_raises", "missing_contract_error"),
        ),
    ],
)
def test_reporter_synthetic_failure_tokens_are_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation_id: str,
    line: int,
    error: BaseException,
    expected: tuple[str, str, str],
) -> None:
    detector = tmp_path / "test_detector.py"
    detector.write_text("synthetic", encoding="utf-8")
    entry = SimpleNamespace(path=detector, lineno=line - 1)
    trace = [entry]
    if mutation_id == "MUT-V2-005":

        def frame(code: object) -> SimpleNamespace:
            return SimpleNamespace(
                path=tmp_path / "pytest_internal.py",
                lineno=0,
                frame=SimpleNamespace(code=SimpleNamespace(raw=code)),
            )

        trace.extend(
            [
                frame(type(pytest.raises(ContractError)).__exit__.__code__),
                frame(type(pytest.fail).__call__.__code__),
            ]
        )
    call = SimpleNamespace(excinfo=SimpleNamespace(value=error, traceback=trace))
    monkeypatch.setattr(reporter, "_PYTEST", pytest)
    failure = reporter._failure(mutation_id, None, call, detector)
    assert (failure["exception"], failure["anchor"], failure["semantic"]) == expected
    assert "private" not in json.dumps(failure)
    entry.lineno += -1 if mutation_id == "MUT-V2-002" else 1
    assert reporter._failure(mutation_id, None, call, detector)["anchor"] == "unknown"


@pytest.mark.parametrize(("mutation_id", "line"), [("MUT-V2-003", 148), ("MUT-V2-004", 169)])
def test_reporter_rejects_assertion_raised_inside_called_function(
    tmp_path: Path, mutation_id: str, line: int
) -> None:
    detector = tmp_path / "test_detector.py"
    detector.write_text("synthetic", encoding="utf-8")
    inner = tmp_path / "production.py"
    inner.write_text("synthetic", encoding="utf-8")
    call = SimpleNamespace(
        excinfo=SimpleNamespace(
            value=AssertionError("unrelated"),
            traceback=[
                SimpleNamespace(path=detector, lineno=line - 1),
                SimpleNamespace(path=inner, lineno=18),
            ],
        )
    )
    assert reporter._failure(mutation_id, None, call, detector) == {
        "exception": "unknown",
        "anchor": "unknown",
        "semantic": "unknown",
    }


def test_reporter_matches_real_pytest_raises_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    detector = tmp_path / "test_detector.py"
    detector.write_text("synthetic", encoding="utf-8")
    with pytest.raises(pytest.fail.Exception) as missing:
        with pytest.raises(ContractError):
            pass
    actual_trace = list(missing.traceback)
    call = SimpleNamespace(
        excinfo=SimpleNamespace(
            value=missing.value,
            traceback=[SimpleNamespace(path=detector, lineno=164), *actual_trace[-2:]],
        )
    )
    monkeypatch.setattr(reporter, "_PYTEST", pytest)
    assert reporter._failure("MUT-V2-005", None, call, detector) == {
        "exception": "pytest_failed",
        "anchor": "snapshot_raises",
        "semantic": "missing_contract_error",
    }


def test_reporter_normalizes_crlf_but_rejects_a_bare_cr(tmp_path: Path) -> None:
    detector = tmp_path / "test_detector.py"
    lf = b"# detector\nassert True\n"
    expected = hashlib.sha256(lf).hexdigest()
    for content in (lf, lf.replace(b"\n", b"\r\n")):
        detector.write_bytes(content)
        assert reporter._test_digest(detector) == expected

    detector.write_bytes(b"# detector\rassert True\r\n")
    with pytest.raises(ValueError, match="invalid detector line ending"):
        reporter._test_digest(detector)


def test_reporter_requires_directories_and_a_regular_source_file(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    detector = tests_dir / "test_detector.py"
    detector.touch()
    assert reporter._safe_file(tmp_path, "tests/test_detector.py") == detector
    with pytest.raises(ValueError, match="invalid controlled file"):
        reporter._safe_file(tmp_path, "tests")
    with pytest.raises(ValueError, match="invalid controlled directory"):
        reporter._safe_file(tmp_path, "tests/test_detector.py/child.py")


@pytest.mark.parametrize("mutation_id", tuple(protocol.CASES))
def test_reporter_checks_target_and_direct_import_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation_id: str
) -> None:
    """A correctly named detector cannot silently import another engine copy."""
    from types import ModuleType

    contract = list(reporter._CONTRACTS[mutation_id])
    detector = tmp_path / contract[0]
    target = tmp_path / contract[3]
    package_path = tmp_path / "src/aiflow/__init__.py"
    errors_path = tmp_path / "src/aiflow/errors.py"
    for path in (detector, target, package_path, errors_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic\n", encoding="utf-8")
    contract[1] = reporter._test_digest(detector)
    contracts = dict(reporter._CONTRACTS)
    contracts[mutation_id] = tuple(contract)
    monkeypatch.setattr(reporter, "_CONTRACTS", contracts)
    package = ModuleType("aiflow")
    package.__file__ = str(package_path)
    errors = ModuleType("aiflow.errors")
    errors.__file__ = str(errors_path)
    errors.PolicyError = type("PolicyError", (Exception,), {})
    errors.ContractError = type("ContractError", (Exception,), {})
    module = ModuleType(contract[4])
    module.__file__ = str(target)
    exec(compile(f"def {contract[5]}():\n    pass\n", str(target), "exec"), module.__dict__)
    function = getattr(module, contract[5])
    detector_module = ModuleType("test_detector")
    detector_module.__file__ = str(detector)
    exec(
        compile(f"def {contract[2]}():\n    pass\n", str(detector), "exec"),
        detector_module.__dict__,
    )
    modules = {"aiflow": package, "aiflow.errors": errors, contract[4]: module}
    if mutation_id == "MUT-V2-002":
        service_path = tmp_path / "src/aiflow/verification_service.py"
        service_path.write_text("# synthetic\n", encoding="utf-8")
        service = ModuleType("aiflow.verification_service")
        service.__file__ = str(service_path)
        service.validate_verifier_actor = function
        modules[service.__name__] = service
        helper_path = tmp_path / "tests/integration/test_begin_close_commands.py"
        helper = ModuleType("test_begin_close_commands")
        helper.__file__ = str(helper_path)
        helper_path.write_text("# synthetic\n", encoding="utf-8")
        for name in ("create_repository", "start", "make_ready", "commit_all", "run_git"):
            exec(compile(f"def {name}():\n    pass\n", str(helper_path), "exec"), helper.__dict__)
            setattr(detector_module, name, getattr(helper, name))
        modules[helper.__name__] = helper
        detector_module.verification_service = service
        detector_module.ContractError = errors.ContractError
    elif mutation_id in {"MUT-V2-003", "MUT-V2-004"}:
        setattr(detector_module, contract[4].rsplit(".", 1)[1], module)
    else:
        setattr(detector_module, contract[5], function)
        setattr(
            detector_module,
            "PolicyError" if mutation_id == "MUT-V2-001" else "ContractError",
            errors.PolicyError if mutation_id == "MUT-V2-001" else errors.ContractError,
        )
    monkeypatch.setattr(reporter, "sys", SimpleNamespace(modules=modules))
    ini = tmp_path / "pyproject.toml"
    ini.write_text("# synthetic\n", encoding="utf-8")
    conftest = ModuleType("conftest")
    conf = tmp_path / "tests/conftest.py"
    conf.write_text("# synthetic\n", encoding="utf-8")
    conftest.__file__ = str(conf)
    plugins = {conftest}
    config = SimpleNamespace(
        rootpath=tmp_path, inipath=ini, pluginmanager=SimpleNamespace(get_plugins=lambda: plugins)
    )
    item = SimpleNamespace(
        module=detector_module, obj=getattr(detector_module, contract[2]), config=config
    )
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    assert reporter._reference_ok(mutation_id, tmp_path, digest, item)
    with monkeypatch.context() as patch:
        patch.setattr(package, "__file__", None)
        assert not reporter._reference_ok(mutation_id, tmp_path, digest, item)
    item.obj = lambda: None
    assert not reporter._reference_ok(mutation_id, tmp_path, digest, item)
    item.obj = getattr(detector_module, contract[2])
    plugins.clear()
    assert not reporter._reference_ok(mutation_id, tmp_path, digest, item)
    plugins.add(conftest)
    config.inipath = tmp_path / "other.toml"
    assert not reporter._reference_ok(mutation_id, tmp_path, digest, item)
    config.inipath = ini
    if mutation_id == "MUT-V2-002":
        detector_module.create_repository = lambda: None
        assert not reporter._reference_ok(mutation_id, tmp_path, digest, item)
        detector_module.create_repository = helper.create_repository
    original_package = package.__file__
    package.__file__ = str(detector)
    assert not reporter._reference_ok(mutation_id, tmp_path, digest, item)
    package.__file__ = original_package
    if mutation_id in {"MUT-V2-001", "MUT-V2-002", "MUT-V2-005"}:
        exception_name = "PolicyError" if mutation_id == "MUT-V2-001" else "ContractError"
        original_exception = getattr(detector_module, exception_name)
        setattr(detector_module, exception_name, object())
        assert not reporter._reference_ok(mutation_id, tmp_path, digest, item)
        setattr(detector_module, exception_name, original_exception)
    assert not reporter._reference_ok(mutation_id, tmp_path, "0" * 64, item)
    if mutation_id == "MUT-V2-002":
        service.validate_verifier_actor = lambda: None
    elif mutation_id in {"MUT-V2-003", "MUT-V2-004"}:
        setattr(detector_module, contract[4].rsplit(".", 1)[1], object())
    else:
        setattr(detector_module, contract[5], lambda: None)
    assert not reporter._reference_ok(mutation_id, tmp_path, digest, item)


def _clean_lifecycle(report: bytes, code: int) -> process.ProcessLifecycle:
    return process.ProcessLifecycle(
        created_suspended=True,
        assigned=True,
        initial_membership=True,
        resumed=True,
        job_empty=True,
        stdout_eof=True,
        stderr_eof=True,
        closed=True,
        terminate_requested=False,
        returncode=code,
        report_sha256=hashlib.sha256(report).hexdigest(),
    )


@pytest.fixture
def completed_job_receipt() -> dict[str, object]:
    lifecycle = _clean_lifecycle(b"synthetic", 0)
    receipt = {
        field.name: getattr(lifecycle, field.name)
        for field in fields(lifecycle)
        if field.name not in {"returncode", "report_sha256"}
    }
    receipt.update(process_id=1, creation_time_filetime=1)
    return receipt


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "stderr",
        "stdout_overflow",
        "stderr_overflow",
        "execution_error",
        "timed_out",
        "cleanup_unknown",
        "no_receipt",
        "early_stop",
        "early_stop_with_output",
        "early_stop_without_cleanup",
        "incomplete_report",
        "job_empty",
        "stdout_eof",
        "stderr_eof",
        "closed",
        "created_suspended",
        "assigned",
        "initial_membership",
        "resumed",
        "terminate_requested",
    ],
)
def test_process_adapter_requires_complete_child_and_channel_observations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str | None,
    completed_job_receipt: dict[str, object],
) -> None:
    from aiflow.process_runner import NodeProcessResult

    data = protocol.encode_report(_synthetic_report("MUT-V2-001"))
    lifecycle = _clean_lifecycle(data, 1)
    receipt = completed_job_receipt
    result = NodeProcessResult(1, False, data, b"", False, False, "confirmed", False, receipt)
    if fault in receipt:
        receipt[fault] = not receipt[fault]
    elif fault == "stderr":
        result = replace(result, stderr=b"unexpected")
    elif fault in {"stdout_overflow", "stderr_overflow", "execution_error", "timed_out"}:
        result = replace(result, **{fault: True})
    elif fault == "cleanup_unknown":
        result = replace(result, cleanup="unknown")
    elif fault == "no_receipt":
        result = replace(result, receipt=None)
    elif fault in {"early_stop", "early_stop_with_output", "early_stop_without_cleanup"}:
        result = replace(
            result,
            returncode=protocol.EARLY_STOP_EXIT_CODE,
            stdout=b"unexpected" if fault == "early_stop_with_output" else b"",
            receipt=None if fault == "early_stop_without_cleanup" else receipt,
        )
    elif fault == "incomplete_report":
        result = replace(result, returncode=2, stdout=b"")

    commands: list[tuple[str, ...]] = []

    def fake_node(argv: tuple[str, ...], **kwargs: Any) -> NodeProcessResult:
        commands.append(argv)
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout_seconds"] == 60
        assert kwargs["max_output_bytes"] == 16384
        return result

    monkeypatch.setattr(process, "run_node_process", fake_node)
    outcome = process.run_bounded_process(
        [sys.executable, "synthetic.py"],
        cwd=tmp_path,
        env={"PATH": "fixed"},
        timeout_seconds=60,
        max_output_bytes=16384,
    )
    assert commands == [(sys.executable, "synthetic.py")]
    if fault is None:
        assert outcome.reason is None and not outcome.cleanup_unknown
        assert outcome.report == data and outcome.lifecycle == lifecycle
    else:
        assert outcome.reason is not None and outcome.report is None
        assert outcome.lifecycle is None
        if fault in {"cleanup_unknown", "early_stop_without_cleanup"}:
            assert outcome.cleanup_unknown
        if fault == "early_stop":
            assert outcome.reason == "pytest_early_stop" and not outcome.cleanup_unknown
        if fault in {"early_stop_with_output", "incomplete_report"}:
            assert outcome.reason == "report_incomplete" and not outcome.cleanup_unknown


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "duplicate_collection",
        "missing_collection",
        "missing_sessionfinish",
        "duplicate_sessionfinish",
        "missing_call",
        "missing_teardown",
        "call_before_setup",
        "teardown_before_call",
        "failed_setup",
        "skipped_setup",
        "xfailed_setup",
        "duplicate_setup",
        "unknown_node",
        "unknown_phase",
        "mismatched_report_node",
        "mismatched_call_phase",
    ],
)
def test_report_requires_one_complete_pytest_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    monkeypatch.setattr(reporter, "_PYTEST", pytest)
    monkeypatch.setattr(reporter, "_reference_ok", lambda *_args: True)
    instance = reporter._Reporter("MUT-V2-001", tmp_path, "a" * 64)
    item = SimpleNamespace(nodeid=next(iter(instance.nodes)))
    session = SimpleNamespace(items=[item])

    stopped_setup = fault in {"failed_setup", "skipped_setup", "xfailed_setup"}

    def session_report() -> dict[str, Any]:
        if fault != "missing_collection":
            instance.pytest_collection_finish(session)
        if fault == "duplicate_collection":
            instance.pytest_collection_finish(session)
        phases = ["setup", "call", "teardown"]
        if fault == "missing_call" or stopped_setup:
            phases.remove("call")
        if fault == "missing_teardown":
            phases.remove("teardown")
        if fault == "call_before_setup":
            phases = ["call", "setup", "teardown"]
        if fault == "teardown_before_call":
            phases = ["setup", "teardown", "call"]
        if fault == "duplicate_setup":
            phases.insert(1, "setup")
        if fault == "unknown_phase":
            phases[1] = "unknown"
        if fault == "unknown_node":
            item.nodeid = "uncollected"
        for phase in phases:
            call_phase = "setup" if fault == "mismatched_call_phase" else phase
            hook = instance.pytest_runtest_makereport(
                item, SimpleNamespace(excinfo=None, when=call_phase)
            )
            next(hook)
            report_node = "other" if fault == "mismatched_report_node" else item.nodeid
            event = SimpleNamespace(nodeid=report_node, outcome="passed", when=phase)
            if phase == "setup" and stopped_setup:
                event.outcome = "failed" if fault == "failed_setup" else "skipped"
                if fault == "xfailed_setup":
                    event.wasxfail = "expected"
                    event.skipped = True
            with pytest.raises(StopIteration):
                hook.send(SimpleNamespace(get_result=lambda result=event: result))
        if fault != "missing_sessionfinish":
            instance.pytest_sessionfinish(session, 1 if fault == "failed_setup" else 0)
        if fault == "duplicate_sessionfinish":
            instance.pytest_sessionfinish(session, 0)
        return instance.report()

    if fault is not None:
        with pytest.raises((ValueError, pytest.exit.Exception)):
            session_report()
        assert instance.stopped_before_call() is stopped_setup
        return
    report = session_report()
    assert not instance.stopped_before_call()
    assert (
        protocol.classify_report(
            report, mutation_id="MUT-V2-001", target_sha256="a" * 64, exit_code=0, baseline=True
        )
        == "passed"
    )


def test_reporter_rejects_partial_actor_detector_collection(
    tmp_path: Path, manifest: MutationManifest, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor_detector = next(m for m in manifest.mutations if m.mutation_id == "MUT-V2-002")
    node = f"{actor_detector.expected_detector}[ -VERIFIER_ACTOR_REQUIRED]"
    session = SimpleNamespace(items=[SimpleNamespace(nodeid=node)])
    monkeypatch.setattr(reporter, "_PYTEST", pytest)
    instance = reporter._Reporter(actor_detector.mutation_id, tmp_path, "a" * 64)

    with pytest.raises(pytest.exit.Exception, match="invalid detector collection") as stopped:
        instance.pytest_collection_finish(session)
    assert stopped.value.returncode == 2
    instance.pytest_sessionfinish(session, stopped.value.returncode)
    with pytest.raises(ValueError, match="invalid detector run"):
        instance.report()


def _run_reporter(
    tmp_path: Path, arguments: list[str], *, stdin_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    import coverage

    script = Path(reporter.__file__).resolve()
    command = [sys.executable, "-I", "-B"]
    active = coverage.Coverage.current()
    data_file = tmp_path / ".coverage-reporter"
    if active is not None:
        # Measure only this checkout's reporter in this test's own child.
        command.extend(
            [
                "-m",
                "coverage",
                "run",
                f"--rcfile={os.devnull}",
                f"--data-file={data_file}",
                f"--include={script}",
            ]
        )
        if active.get_option("run:branch"):
            command.append("--branch")

    result = subprocess.run(
        [*command, str(script), *arguments],
        cwd=REPOSITORY_ROOT,
        env=runner.detector_environment(REPOSITORY_ROOT, tmp_path),
        stdin=subprocess.DEVNULL if stdin_bytes is None else None,
        input=stdin_bytes,
        capture_output=True,
        check=False,
        timeout=40,
    )
    if active is not None:
        measured = coverage.CoverageData(basename=str(data_file))
        measured.read()
        assert {Path(name) for name in measured.measured_files()} == {script}, result.stderr
        active.get_data().update(measured)
    return result


_FIXED_DETECTOR = (
    sys.platform == "win32" and sys.version_info[:2] == (3, 11) and pytest.__version__ == "9.1.1"
)


@pytest.mark.parametrize(
    "fault",
    [
        "unexpected_stdin",
        "unknown_detector",
        pytest.param(
            "missing_files",
            marks=pytest.mark.skipif(
                not _FIXED_DETECTOR, reason="file checks follow fixed-runtime admission"
            ),
        ),
        pytest.param(
            "wrong_digest",
            marks=pytest.mark.skipif(
                not _FIXED_DETECTOR, reason="file checks follow fixed-runtime admission"
            ),
        ),
    ],
)
def test_reporter_rejects_invalid_inputs_without_emitting_report(
    tmp_path: Path, manifest: MutationManifest, fault: str
) -> None:
    declaration = manifest.mutations[0]
    digest = hashlib.sha256((REPOSITORY_ROOT / declaration.target).read_bytes()).hexdigest()
    arguments = [
        "unknown" if fault == "unknown_detector" else declaration.mutation_id,
        str(tmp_path if fault == "missing_files" else REPOSITORY_ROOT),
        "0" * 64 if fault == "wrong_digest" else digest,
    ]
    result = _run_reporter(
        tmp_path, arguments, stdin_bytes=b"unexpected" if fault == "unexpected_stdin" else None
    )
    assert (result.returncode, result.stdout, result.stderr) == (2, b"", b"")


@pytest.mark.skipif(not _FIXED_DETECTOR, reason="fixed native detector environment")
@pytest.mark.parametrize("index", range(5))
def test_reporter_records_each_node_of_the_unmodified_detector(
    tmp_path: Path, manifest: MutationManifest, index: int
) -> None:
    declaration = manifest.mutations[index]
    digest = hashlib.sha256((REPOSITORY_ROOT / declaration.target).read_bytes()).hexdigest()
    result = _run_reporter(tmp_path, [declaration.mutation_id, str(REPOSITORY_ROOT), digest])

    assert result.returncode == 0 and result.stderr == b""
    report = protocol.parse_report(result.stdout, declaration.mutation_id, digest)
    expected_cases = ["blank", "same_actor"] if index == 1 else ["only"]
    assert [case["case"] for case in report["cases"]] == expected_cases
    assert (
        protocol.classify_report(
            report,
            mutation_id=declaration.mutation_id,
            target_sha256=digest,
            exit_code=result.returncode,
            baseline=True,
        )
        == "passed"
    )


@pytest.mark.parametrize("fault", ["missing", "wrong_exit", "wrong_report"])
def test_detector_rejects_receipt_from_different_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    raw = protocol.encode_report(_synthetic_report("MUT-V2-001"))
    receipt = _clean_lifecycle(raw, 0)
    if fault == "wrong_exit":
        receipt = replace(receipt, returncode=1)
    elif fault == "wrong_report":
        receipt = replace(receipt, report_sha256="0" * 64)
    outcome = process.ProcessOutcome(
        0, raw, None, False, 1, None if fault == "missing" else receipt
    )
    monkeypatch.setattr(runner, "detector_environment", lambda *_args: {})
    monkeypatch.setattr(runner, "run_bounded_process", lambda *_args, **_kwargs: outcome)
    result = runner._run_detector(tmp_path, tmp_path, "MUT-V2-001", "a" * 64)
    assert result[3:] == ("MUTATION_PROCESS_CLEANUP_UNKNOWN", None, None)


@pytest.mark.parametrize("size", [0, 16 * 1024 + 1, True])
def test_process_adapter_rejects_invalid_report_budget_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    monkeypatch.setattr(
        process, "run_node_process", lambda *_a, **_kw: pytest.fail("unexpected child")
    )
    outcome = process.run_bounded_process(
        [sys.executable],
        cwd=tmp_path,
        env={},
        timeout_seconds=60,
        max_output_bytes=size,
    )
    assert (
        outcome.reason == "invalid_input" and outcome.lifecycle is None and outcome.report is None
    )


@pytest.mark.parametrize("platform,arch", [("linux", "linux-x86_64"), ("win32", "win32")])
def test_process_preflight_rejects_unsupported_platform_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, arch: str
) -> None:
    monkeypatch.setattr(process, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setattr(process.sysconfig, "get_platform", lambda: arch)
    monkeypatch.setattr(
        process, "run_node_process", lambda *_a, **_kw: pytest.fail("unexpected child")
    )
    with pytest.raises(ContractError) as caught:
        process.preflight_mutation_runtime(tmp_path, {})
    assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"


@pytest.mark.parametrize(
    "fault", [None, "assigned", "stdout_eof", "stderr_eof", "wrong_version", "not_started"]
)
def test_process_preflight_requires_version_from_the_completed_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_job_receipt: dict[str, object],
    fault: str | None,
) -> None:
    from aiflow.process_runner import NodeProcessResult

    monkeypatch.setattr(
        process, "sys", SimpleNamespace(platform="win32", executable=sys.executable)
    )
    monkeypatch.setattr(process.sysconfig, "get_platform", lambda: "win-amd64")
    version = b"3.11 9.1.1" if fault != "wrong_version" else b"3.11 9.1.0"
    if fault in completed_job_receipt:
        completed_job_receipt[fault] = False
    result = NodeProcessResult(
        0, False, version, b"", False, False, "confirmed", False, completed_job_receipt
    )
    if fault == "not_started":
        result = replace(
            result,
            returncode=None,
            stdout=b"",
            cleanup="not_started",
            execution_error=True,
            receipt=None,
        )

    def run(argv: tuple[str, ...], **kwargs: Any) -> NodeProcessResult:
        assert argv[:4] == (sys.executable, "-I", "-B", "-c") and len(argv) == 5
        assert kwargs["cwd"] == tmp_path and kwargs["environment"] == {"PATH": "fixed"}
        assert kwargs["timeout_seconds"] == 10 and kwargs["max_output_bytes"] == 64
        return result

    monkeypatch.setattr(process, "run_node_process", run)
    if fault is None:
        process.preflight_mutation_runtime(tmp_path, {"PATH": "fixed"})
    else:
        with pytest.raises(ContractError) as caught:
            process.preflight_mutation_runtime(tmp_path, {"PATH": "fixed"})
        assert caught.value.code == "MUTATION_EVIDENCE_INPUT_MISMATCH"
