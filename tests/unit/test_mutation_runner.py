"""Deterministic seam tests for the isolated mutation runner."""

from __future__ import annotations

import ast
import os
import stat
import subprocess
import sys
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from typing import Any, Iterator

import pytest

import aiflow.mutation_runner as runner
from aiflow.errors import ContractError
from aiflow.mutation_manifest import MutationManifest, load_mutation_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SUBJECT = "a" * 40


@pytest.fixture(scope="module")
def manifest() -> MutationManifest:
    return load_mutation_manifest(REPOSITORY_ROOT)


def _failure_code(call: Any) -> str:
    with pytest.raises(runner._RunFailure) as caught:
        call()
    return caught.value.code


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
        generators = [
            node.args[0]
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "all"
            and node.args
            and isinstance(node.args[0], ast.GeneratorExp)
        ]
        assert any(ast.unparse(item.elt) == "isinstance(item, Mapping)" for item in generators)


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
    original_write = Path.write_text

    def fail_write(self: Path, *_args: object, **_kwargs: object) -> int:
        if self == path:
            raise OSError("write blocked")
        return original_write(self, *_args, **_kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", fail_write)
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


@pytest.mark.parametrize("name", ["", "../outside", "nested/name", "nested\\name"])
def test_validated_child_rejects_non_direct_or_escaping_names(tmp_path: Path, name: str) -> None:
    root = tmp_path.resolve()
    assert _failure_code(lambda: runner._validated_child(root, name)) == (
        "MUTATION_WORKTREE_PATH_ESCAPE"
    )


def test_validated_child_accepts_one_resolved_direct_child(tmp_path: Path) -> None:
    child = runner._validated_child(tmp_path.resolve(), "MUT-V2-001")
    assert child.parent == tmp_path.resolve()


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


def test_subject_validation_rejects_invalid_and_non_head_values(
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
        output = SUBJECT.encode() if "--verify" in arguments else ("b" * 40).encode()
        return subprocess.CompletedProcess(list(arguments), 0, output + b"\n", b"")

    monkeypatch.setattr(runner, "_git", mismatch)
    with pytest.raises(ContractError) as caught:
        runner._validate_subject(tmp_path, hooks, SUBJECT)
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"


def test_controlled_drift_and_checkout_filter_checks_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    calls: list[tuple[str, ...]] = []

    def attributes(
        _root: Path, _hooks: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        calls.append(arguments)
        path = arguments[-1]
        value = "lfs" if path.endswith("test_policy.py") else "unspecified"
        return subprocess.CompletedProcess(
            list(arguments), 0, f"{path}: filter: {value}\n".encode(), b""
        )

    monkeypatch.setattr(runner, "_git", attributes)
    with pytest.raises(ContractError) as caught:
        runner._assert_no_checkout_filters(tmp_path, hooks, SUBJECT, paths)
    assert caught.value.code == "MUTATION_WORKSPACE_INVALID"
    assert len(calls) == 2
    assert all(call[1] == f"--source={SUBJECT}" for call in calls)


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
        if arguments[0] == "check-attr":
            path = arguments[-1]
            return subprocess.CompletedProcess(
                list(arguments), 0, f"{path}: filter: unset\n".encode(), b""
            )
        return subprocess.CompletedProcess(list(arguments), 0, b"", b"")

    monkeypatch.setattr(runner, "_git", clean)
    runner._assert_controlled_paths_at_subject(tmp_path, hooks, SUBJECT, paths)
    runner._assert_no_checkout_filters(tmp_path, hooks, SUBJECT, paths)

    monkeypatch.setattr(
        runner,
        "_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired([], 1)),
    )
    with pytest.raises(ContractError) as caught:
        runner._assert_controlled_paths_at_subject(tmp_path, hooks, SUBJECT, paths)
    assert caught.value.code == "MUTATION_SUBJECT_INVALID"
    with pytest.raises(ContractError) as caught:
        runner._assert_no_checkout_filters(tmp_path, hooks, SUBJECT, paths)
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

    environment = runner._minimal_environment(worktree, scratch)

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
    assert _failure_code(lambda: runner._minimal_environment(tmp_path, tmp_path)) == (
        "MUTATION_DETECTOR_EXECUTION_FAILED"
    )
    if os.name == "nt":
        monkeypatch.setattr(runner.shutil, "which", lambda _name: str(tmp_path / "git.exe"))
        monkeypatch.delenv("SystemRoot", raising=False)
        assert _failure_code(lambda: runner._minimal_environment(tmp_path, tmp_path)) == (
            "MUTATION_DETECTOR_EXECUTION_FAILED"
        )


class _FakeProcess:
    def __init__(self, waits: Iterator[int | BaseException]) -> None:
        self.pid = 321
        self._waits = waits
        self.killed = False

    def wait(self, timeout: int) -> int:
        del timeout
        value = next(self._waits)
        if isinstance(value, BaseException):
            raise value
        return value

    def kill(self) -> None:
        self.killed = True


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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int,
    reason: str | None,
) -> None:
    captured: dict[str, object] = {}
    process = _FakeProcess(iter((exit_code,)))

    def popen(arguments: list[str], **kwargs: object) -> _FakeProcess:
        captured["arguments"] = arguments
        captured.update(kwargs)
        return process

    monkeypatch.setattr(runner, "_minimal_environment", lambda *_args: {"PATH": "fixed"})
    monkeypatch.setattr(runner.subprocess, "Popen", popen)
    detector = "tests/unit/test_policy.py::test_detector"
    result = runner._run_detector(tmp_path / "worktree", tmp_path / "scratch", detector)

    assert result[0] == exit_code and result[1] is False and result[3] == reason
    assert captured["arguments"] == [sys.executable, "-m", "pytest", "-q", detector]
    assert captured["shell"] is False
    assert captured["stdout"] == subprocess.DEVNULL
    assert captured["stderr"] == subprocess.DEVNULL


def test_detector_timeout_terminates_and_reaps_with_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeout = subprocess.TimeoutExpired(["pytest"], runner._TIMEOUT_SECONDS)
    process = _FakeProcess(iter((timeout, -9)))
    terminated: list[int] = []
    monkeypatch.setattr(runner, "_minimal_environment", lambda *_args: {})
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(runner, "_terminate_process_tree", lambda item: terminated.append(item.pid))

    result = runner._run_detector(tmp_path / "worktree", tmp_path / "scratch", "nodeid")

    assert result[0] is None and result[1] is True
    assert result[3] == "MUTATION_DETECTOR_TIMEOUT"
    assert terminated == [321]


def test_detector_reports_unreapable_timeout_as_execution_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeout = subprocess.TimeoutExpired(["pytest"], runner._TIMEOUT_SECONDS)
    process = _FakeProcess(iter((timeout, timeout, timeout)))
    monkeypatch.setattr(runner, "_minimal_environment", lambda *_args: {})
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(runner, "_terminate_process_tree", lambda _item: None)
    result = runner._run_detector(tmp_path / "worktree", tmp_path / "scratch", "nodeid")
    assert result[0] is None and result[1] is True
    assert result[3] == "MUTATION_DETECTOR_EXECUTION_FAILED"
    assert process.killed is True


def test_detector_launch_failure_is_a_stable_execution_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "_minimal_environment", lambda *_args: {})
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("missing")),
    )
    result = runner._run_detector(tmp_path / "worktree", tmp_path / "scratch", "nodeid")
    assert result[0] is None and result[1] is False
    assert result[3] == "MUTATION_DETECTOR_EXECUTION_FAILED"


def test_process_tree_termination_has_a_kill_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    process = _FakeProcess(iter(()))
    if os.name == "nt":
        monkeypatch.setattr(
            runner.subprocess,
            "run",
            lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, b"", b""),
        )
    else:
        monkeypatch.setattr(runner.os, "killpg", lambda *_args: (_ for _ in ()).throw(OSError()))
    runner._terminate_process_tree(process)  # type: ignore[arg-type]
    assert process.killed is True


def test_process_tree_termination_accepts_successful_platform_kill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess(iter(()))
    if os.name == "nt":
        monkeypatch.setattr(
            runner.subprocess,
            "run",
            lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, b"", b""),
        )
    else:
        monkeypatch.setattr(runner.os, "killpg", lambda *_args: None)
    runner._terminate_process_tree(process)  # type: ignore[arg-type]
    assert process.killed is False


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

    monkeypatch.setattr(runner, "_git", git)
    runner._create_detached_worktree(tmp_path, hooks, worktree, SUBJECT)
    assert calls[0][:4] == ("worktree", "add", "--detach", "--no-checkout")
    assert calls[1] == ("checkout", "--detach", SUBJECT)

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
    monkeypatch.setattr(runner, "_assert_no_checkout_filters", lambda *_args: None)
    snapshot = runner._MainSnapshot(b"status", b"worktrees", ())
    monkeypatch.setattr(runner, "_snapshot_main_tree", lambda *_args: snapshot)
    monkeypatch.setattr(runner, "_main_tree_unchanged", lambda *_args: unchanged)

    def create(_root: Path, _hooks: Path, path: Path, _subject: str) -> None:
        attempts.append(path)
        if create_failure_at is not None and len(attempts) == create_failure_at:
            raise runner._RunFailure("MUTATION_WORKTREE_CREATE_FAILED")
        path.mkdir()

    monkeypatch.setattr(runner, "_create_detached_worktree", create)
    monkeypatch.setattr(runner, "_run_detector", lambda *_args: next(detector_results))

    def apply(*_args: object) -> None:
        if apply_failure is not None:
            raise runner._RunFailure(apply_failure)

    monkeypatch.setattr(runner, "_apply_mutation", apply)
    monkeypatch.setattr(runner, "_remove_worktree_with_retry", lambda *_args: cleanup_ok)
    monkeypatch.setattr(runner, "_remove_tree_with_retry", lambda *_args: True)
    return attempts


def test_orchestrator_returns_five_ordered_success_facts_without_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest: MutationManifest
) -> None:
    results = iter(
        (value for _ in range(5) for value in ((0, False, 2, None), (1, False, 3, None)))
    )
    attempts = _mock_orchestrator(monkeypatch, tmp_path, manifest, results)

    result = runner.run_targeted_mutations(tmp_path, SUBJECT)

    assert len(attempts) == 5
    assert tuple(probe.mutation_id for probe in result.probes) == tuple(
        item.mutation_id for item in manifest.mutations
    )
    assert all(probe.baseline_exit_code == 0 for probe in result.probes)
    assert all(probe.mutant_exit_code == 1 for probe in result.probes)
    assert all(probe.duration_ms == 5 and probe.reason_code is None for probe in result.probes)
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

    result = runner.run_targeted_mutations(tmp_path, SUBJECT)

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
    result = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    result = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    created = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    cleaned = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    body = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    cleanup = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    result = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    monkeypatch.setattr(runner, "_assert_no_checkout_filters", lambda *_args: None)
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
    result = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    result = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
    result = runner.run_targeted_mutations(tmp_path, SUBJECT)
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
        lambda: (_ for _ in ()).throw(runner._RunFailure("MUTATION_WORKSPACE_INVALID")),
    )
    with pytest.raises(ContractError) as caught:
        runner.run_targeted_mutations(tmp_path, SUBJECT)
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
            runner.run_targeted_mutations(tmp_path, SUBJECT)
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
        runner.run_targeted_mutations(tmp_path, SUBJECT)
    assert caught.value.code == "MUTATION_WORKTREE_CLEANUP_FAILED"
