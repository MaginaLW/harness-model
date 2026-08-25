"""Execute the fixed Phase 02 mutations in disposable, isolated worktrees.

This module intentionally has no CLI integration and accepts no caller supplied
mutation program.  It is the narrow Chapter 11.3 execution primitive only.
"""

# ruff: noqa: E501

from __future__ import annotations

import ast
import hashlib
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic
from types import TracebackType
from typing import Callable

from aiflow.errors import ContractError
from aiflow.mutation_manifest import (
    CANONICAL_MANIFEST_PATH,
    MutationDeclaration,
    MutationManifest,
    load_mutation_manifest,
)

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_TIMEOUT_SECONDS = 60
_OPERATOR_BINDINGS = {
    "drop_targeted_mutation_required_check": ("src/aiflow/policy.py", "_validate_cross_file"),
    "allow_same_verifier_actor": ("src/aiflow/verifier_service.py", "validate_verifier_actor"),
    "allow_nonpassing_required_check": ("src/aiflow/approval.py", "_v2_evidence_current"),
    "accept_non_killed_mutation": ("src/aiflow/gate.py", "_v2_gate_facts"),
    "ignore_snapshot_mismatch": ("src/aiflow/evidence.py", "validate_v2_snapshot"),
}
_RUNNER_AUTHORITY = object()
_RUNNER_AUTHORIZATIONS: set[object] = set()
_RUNNER_AUTHORIZATION_LOCK = Lock()
_ACTION_RECEIPT_NAME = re.compile(r"^action-use-[0-9a-f]{64}\.md$")


@dataclass(frozen=True)
class MutationProbe:
    """Raw execution facts for one declaration, in manifest order."""

    mutation_id: str
    baseline_exit_code: int | None
    mutant_exit_code: int | None
    timed_out: bool
    duration_ms: int
    reason_code: str | None


@dataclass(frozen=True)
class MutationRun:
    """The non-persistent Chapter 11.3 result."""

    manifest_id: str
    subject_commit: str
    probes: tuple[MutationProbe, ...]
    main_tree_unchanged: bool
    reason_code: str | None


@dataclass(frozen=True)
class _MutationRunnerAuthorization:
    authority: object
    token: object
    repository_root: Path
    task_id: str
    subject_commit: str
    action_sha256: str
    receipt_path: Path
    action_path: Path
    decision_unit_id: str
    spec_sha256: str
    policy_sha256: str
    base_commit: str
    classification_input_sha256: str
    receipt_device: int
    receipt_inode: int


def _issue_runner_authorization(
    repository_root: Path,
    task_id: str,
    subject_commit: str,
    *,
    action_sha256: str,
    receipt_path: Path,
    action_path: Path,
    decision_unit_id: str,
    spec_sha256: str,
    policy_sha256: str,
    base_commit: str,
    classification_input_sha256: str,
) -> _MutationRunnerAuthorization:
    """Issue one fully bound token; the runner independently replays its authority."""
    root = Path(repository_root).resolve()
    receipt = Path(os.path.abspath(receipt_path))
    action = Path(os.path.abspath(action_path))
    try:
        relative = receipt.relative_to(root)
        action_relative = action.relative_to(root)
        receipt_stat = receipt.stat(follow_symlinks=False)
    except (OSError, ValueError) as error:
        raise _contract(
            "Targeted mutation runner authorization is invalid",
            "MUTATION_ACTION_REQUIRED",
        ) from error
    if (
        _COMMIT.fullmatch(subject_commit) is None
        or len(relative.parts) != 4
        or relative.parts[:2] != (".ai", "tasks")
        or relative.parts[2] != task_id
        or re.fullmatch(r"TASK-[0-9]{4,}", task_id) is None
        or relative.name != f"action-use-{action_sha256}.md"
        or _ACTION_RECEIPT_NAME.fullmatch(relative.name) is None
        or len(action_relative.parts) != 4
        or action_relative.parts[:3] != relative.parts[:3]
        or re.fullmatch(r"action-v2-targeted-mutation-.+\.json", action_relative.name) is None
        or not stat.S_ISREG(receipt_stat.st_mode)
    ):
        raise _contract(
            "Targeted mutation runner authorization is invalid",
            "MUTATION_ACTION_REQUIRED",
        )
    token = object()
    with _RUNNER_AUTHORIZATION_LOCK:
        _RUNNER_AUTHORIZATIONS.add(token)
    return _MutationRunnerAuthorization(
        _RUNNER_AUTHORITY,
        token,
        root,
        task_id,
        subject_commit,
        action_sha256,
        receipt,
        action,
        decision_unit_id,
        spec_sha256,
        policy_sha256,
        base_commit,
        classification_input_sha256,
        receipt_stat.st_dev,
        receipt_stat.st_ino,
    )


def _validate_authoritative_runner_launch(
    authorization: _MutationRunnerAuthorization,
) -> None:
    """Replay current approval/ledger facts and atomically claim the sole launch."""
    from aiflow.mutation_evidence import _authorize_targeted_mutation_runner_launch

    _authorize_targeted_mutation_runner_launch(
        authorization.repository_root,
        authorization.task_id,
        authorization.subject_commit,
        action_sha256=authorization.action_sha256,
        receipt_path=authorization.receipt_path,
        action_path=authorization.action_path,
        decision_unit_id=authorization.decision_unit_id,
        spec_sha256=authorization.spec_sha256,
        policy_sha256=authorization.policy_sha256,
        base_commit=authorization.base_commit,
        classification_input_sha256=authorization.classification_input_sha256,
        receipt_device=authorization.receipt_device,
        receipt_inode=authorization.receipt_inode,
    )


def _consume_runner_authorization(
    root: Path,
    subject_commit: str,
    authorization: _MutationRunnerAuthorization | None,
) -> None:
    valid_shape = (
        isinstance(authorization, _MutationRunnerAuthorization)
        and authorization.authority is _RUNNER_AUTHORITY
    )
    if not valid_shape:
        raise _contract(
            "Targeted mutation runner requires recorder authorization",
            "MUTATION_ACTION_REQUIRED",
        )
    assert authorization is not None
    with _RUNNER_AUTHORIZATION_LOCK:
        if authorization.token not in _RUNNER_AUTHORIZATIONS:
            raise _contract(
                "Targeted mutation runner authorization was already used",
                "MUTATION_ACTION_REQUIRED",
            )
        _RUNNER_AUTHORIZATIONS.remove(authorization.token)
    try:
        receipt_stat = authorization.receipt_path.stat(follow_symlinks=False)
    except OSError as error:
        raise _contract(
            "Targeted mutation runner authorization changed before launch",
            "MUTATION_ACTION_REQUIRED",
        ) from error
    if (
        authorization.repository_root != root
        or authorization.subject_commit != subject_commit
        or (authorization.receipt_path.parent / "approval_pending.json").exists()
        or (authorization.receipt_path.parent / "approval_pending.json").is_symlink()
        or not stat.S_ISREG(receipt_stat.st_mode)
        or receipt_stat.st_dev != authorization.receipt_device
        or receipt_stat.st_ino != authorization.receipt_inode
    ):
        raise _contract(
            "Targeted mutation runner authorization changed before launch",
            "MUTATION_ACTION_REQUIRED",
        )
    _validate_authoritative_runner_launch(authorization)


@dataclass(frozen=True)
class _MainSnapshot:
    status: bytes
    worktrees: bytes
    digests: tuple[tuple[str, str], ...]


class _RunFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _contract(message: str, code: str) -> ContractError:
    return ContractError(message, code=code)


def _within(candidate: Path, parent: Path, *, direct: bool = False) -> bool:
    try:
        relative = candidate.relative_to(parent)
    except ValueError:
        return False
    return bool(relative.parts) and (not direct or len(relative.parts) == 1)


def _git(
    root: Path, hooks: Path, *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    """Run a fixed Git command with hooks disabled and no shell."""
    if not hooks.is_dir() or any(hooks.iterdir()):
        raise _contract("Mutation hooks directory is invalid", "MUTATION_WORKSPACE_INVALID")
    return subprocess.run(
        ["git", "-c", f"core.hooksPath={hooks}", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        shell=False,
        timeout=15,
    )


def _validate_subject(root: Path, hooks: Path, subject_commit: str) -> None:
    if not _COMMIT.fullmatch(subject_commit):
        raise _contract("Mutation subject must be a full commit SHA", "MUTATION_SUBJECT_INVALID")
    try:
        resolved = _git(
            root, hooks, "rev-parse", "--verify", f"{subject_commit}^{{commit}}"
        ).stdout.strip()
        head = _git(root, hooks, "rev-parse", "HEAD").stdout.strip()
        ancestry = _git(
            root,
            hooks,
            "merge-base",
            "--is-ancestor",
            subject_commit,
            head.decode("ascii", "strict"),
            check=False,
        )
    except (OSError, UnicodeDecodeError, subprocess.SubprocessError) as error:
        raise _contract(
            "Mutation subject could not be inspected", "MUTATION_SUBJECT_INVALID"
        ) from error
    if (
        resolved.decode("ascii", "replace") != subject_commit
        or _COMMIT.fullmatch(head.decode("ascii", "replace")) is None
        or ancestry.returncode != 0
    ):
        raise _contract(
            "Mutation subject is not an ancestor of the governed HEAD",
            "MUTATION_SUBJECT_INVALID",
        )


def _controlled_paths(manifest: MutationManifest) -> tuple[str, ...]:
    paths = {CANONICAL_MANIFEST_PATH.as_posix(), ".ai/schemas/mutation-manifest.schema.json"}
    for declaration in manifest.mutations:
        paths.add(declaration.target)
        paths.add(declaration.expected_detector.partition("::")[0])
    return tuple(sorted(paths))


def _assert_controlled_paths_at_subject(
    root: Path, hooks: Path, subject: str, paths: tuple[str, ...]
) -> None:
    try:
        changed = _git(
            root, hooks, "status", "--porcelain=v1", "--untracked-files=all", "--", *paths
        ).stdout
        compared = _git(
            root, hooks, "diff", "--quiet", subject, "--", *paths, check=False
        ).returncode
    except (OSError, subprocess.SubprocessError) as error:
        raise _contract(
            "Controlled paths could not be checked", "MUTATION_SUBJECT_INVALID"
        ) from error
    if changed or compared != 0:
        raise _contract(
            "Controlled paths drift from the mutation subject", "MUTATION_SUBJECT_DRIFT"
        )


def _assert_no_checkout_filters(
    root: Path, hooks: Path, subject: str, paths: tuple[str, ...]
) -> None:
    for path in paths:
        try:
            output = _git(
                root, hooks, "check-attr", f"--source={subject}", "filter", "--", path
            ).stdout.decode("utf-8", "strict")
        except (OSError, UnicodeDecodeError, subprocess.SubprocessError) as error:
            raise _contract(
                "Checkout filters could not be checked", "MUTATION_WORKSPACE_INVALID"
            ) from error
        lines = output.splitlines()
        fields = lines[0].rsplit(": ", 2) if len(lines) == 1 else []
        if (
            len(fields) != 3
            or fields[0] != path
            or fields[1] != "filter"
            or fields[2] not in {"unspecified", "unset"}
        ):
            raise _contract("Checkout filters are not permitted", "MUTATION_WORKSPACE_INVALID")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_main_tree(root: Path, hooks: Path, paths: tuple[str, ...]) -> _MainSnapshot:
    try:
        status = _git(root, hooks, "status", "--porcelain=v1", "--untracked-files=all").stdout
        worktrees = _git(root, hooks, "worktree", "list", "--porcelain").stdout
        digests = tuple((path, _digest(root / path)) for path in paths)
    except (OSError, subprocess.SubprocessError) as error:
        raise _contract(
            "Main worktree could not be snapshotted", "MUTATION_SUBJECT_INVALID"
        ) from error
    return _MainSnapshot(status, worktrees, digests)


def _main_tree_unchanged(root: Path, hooks: Path, snapshot: _MainSnapshot) -> bool:
    try:
        current = _snapshot_main_tree(root, hooks, tuple(path for path, _ in snapshot.digests))
    except (ContractError, OSError):
        return False
    return current == snapshot


def _create_workspace_root() -> Path:
    system_temp = Path(tempfile.gettempdir()).resolve()
    try:
        root = Path(tempfile.mkdtemp(prefix="aiflow-mutation-", dir=system_temp)).resolve()
    except OSError as error:
        raise _RunFailure("MUTATION_WORKSPACE_INVALID") from error
    if not _within(root, system_temp, direct=True) or not root.name.startswith("aiflow-mutation-"):
        raise _RunFailure("MUTATION_WORKSPACE_INVALID")
    return root


def _validated_child(root: Path, name: str) -> Path:
    if not name or name in {".", ".."} or "/" in name or "\\" in name or Path(name).name != name:
        raise _RunFailure("MUTATION_WORKTREE_PATH_ESCAPE")
    candidate = (root / name).resolve()
    if not _within(candidate, root, direct=True):
        raise _RunFailure("MUTATION_WORKTREE_PATH_ESCAPE")
    return candidate


def _create_detached_worktree(repository_root: Path, hooks: Path, path: Path, subject: str) -> None:
    try:
        _git(
            repository_root,
            hooks,
            "worktree",
            "add",
            "--detach",
            "--no-checkout",
            str(path),
            subject,
        )
        _git(path, hooks, "checkout", "--detach", subject)
    except (OSError, subprocess.SubprocessError) as error:
        raise _RunFailure("MUTATION_WORKTREE_CREATE_FAILED") from error


def _remove_worktree_with_retry(
    repository_root: Path, hooks: Path, root: Path, worktree: Path
) -> bool:
    parent = root.resolve()
    deadline = monotonic() + 1
    for _ in range(3):
        try:
            candidate = worktree.resolve()
        except OSError:
            return False
        if not _within(candidate, parent, direct=True):
            return False
        try:
            _git(repository_root, hooks, "worktree", "remove", "--force", str(candidate))
            return _remove_tree_with_retry(parent, candidate)
        except (OSError, subprocess.SubprocessError):
            if monotonic() >= deadline:
                break
    return False


def _remove_tree_with_retry(parent: Path, path: Path) -> bool:
    """Delete only a resolved direct child, with a bounded Windows-safe retry."""
    try:
        resolved_parent = parent.resolve()
    except OSError:
        return False
    deadline = monotonic() + 1
    for _ in range(3):
        try:
            candidate = path.resolve()
        except OSError:
            return False
        if not _within(candidate, resolved_parent, direct=True):
            return False
        try:
            if candidate.exists():
                shutil.rmtree(
                    candidate,
                    onerror=lambda function, failed_path, error: _clear_readonly_and_retry(
                        candidate, function, failed_path, error
                    ),
                )
            return not candidate.exists()
        except OSError:
            if monotonic() >= deadline:
                break
    return False


def _clear_readonly_and_retry(
    root: Path,
    function: Callable[[str], object],
    failed_path: str,
    error: tuple[type[BaseException], BaseException, TracebackType],
) -> None:
    """Retry one Windows read-only removal without escaping the validated root."""
    failure = error[1]
    if not isinstance(failure, PermissionError):
        raise failure
    try:
        candidate = Path(failed_path).resolve()
    except OSError:
        raise failure
    if candidate != root and not _within(candidate, root):
        raise failure
    try:
        os.chmod(candidate, candidate.stat().st_mode | stat.S_IWRITE)
        function(failed_path)
    except OSError:
        raise


def _replace_guard(function: ast.AST, predicate: Callable[[ast.If], bool]) -> bool:
    matches = [node for node in ast.walk(function) if isinstance(node, ast.If) and predicate(node)]
    if len(matches) != 1:
        return False
    matches[0].test = ast.Constant(value=False)
    return True


def _raises_contract_code(node: ast.If, code: str) -> bool:
    if len(node.body) != 1 or not isinstance(node.body[0], ast.Raise):
        return False
    exception = node.body[0].exc
    if (
        not isinstance(exception, ast.Call)
        or not isinstance(exception.func, ast.Name)
        or exception.func.id != "ContractError"
    ):
        return False
    return any(
        keyword.arg == "code"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == code
        for keyword in exception.keywords
    )


def _returns_literal_false(node: ast.If) -> bool:
    return (
        len(node.body) == 1
        and isinstance(node.body[0], ast.Return)
        and isinstance(node.body[0].value, ast.Constant)
        and node.body[0].value.value is False
    )


def _outside_target_dump(tree: ast.Module, symbol: str) -> tuple[str, ...]:
    """Return a structural baseline for everything except the selected function."""
    return tuple(
        ast.dump(node, include_attributes=False)
        for node in tree.body
        if not isinstance(node, ast.FunctionDef) or node.name != symbol
    )


def _apply_mutation(declaration: MutationDeclaration, path: Path) -> None:
    """Apply one closed AST transformation, rejecting all unexpected shapes."""
    if _OPERATOR_BINDINGS.get(declaration.operator) != (
        declaration.target,
        declaration.target_symbol,
    ):
        raise _RunFailure("MUTATION_OPERATOR_UNSUPPORTED")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        raise _RunFailure("MUTATION_OPERATOR_PRECONDITION_FAILED") from error
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == declaration.target_symbol
    ]
    if len(functions) != 1:
        raise _RunFailure("MUTATION_OPERATOR_PRECONDITION_FAILED")
    outside_before = _outside_target_dump(tree, declaration.target_symbol)
    function = functions[0]
    operator = declaration.operator
    changed = False
    if (
        operator == "drop_targeted_mutation_required_check"
        and declaration.target_symbol == "_validate_cross_file"
    ):
        assignments = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "extras"
            and isinstance(node.value, ast.Tuple)
            and len(node.value.elts) == 4
            and tuple(
                item.value
                for item in node.value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            )
            == ("acceptance", "integration", "targeted_mutation", "independent_verifier")
        ]
        if len(assignments) == 1 and isinstance(assignments[0].value, ast.Tuple):
            assignments[0].value.elts = [
                item
                for item in assignments[0].value.elts
                if not (isinstance(item, ast.Constant) and item.value == "targeted_mutation")
            ]
            changed = True
    elif (
        operator == "allow_same_verifier_actor"
        and declaration.target_symbol == "validate_verifier_actor"
    ):
        changed = _replace_guard(
            function,
            lambda node: (
                isinstance(node.test, ast.Compare)
                and ast.unparse(node.test) == "implementer == verifier"
                and _raises_contract_code(node, "VERIFIER_ACTOR_NOT_INDEPENDENT")
            ),
        )
    elif (
        operator == "allow_nonpassing_required_check"
        and declaration.target_symbol == "_v2_evidence_current"
    ):
        changed = _replace_guard(
            function,
            lambda node: (
                ast.unparse(node.test)
                == "any((by_id[identifier].get('status') != 'passed' for identifier in expected))"
                and _returns_literal_false(node)
            ),
        )
    elif operator == "accept_non_killed_mutation" and declaration.target_symbol == "_v2_gate_facts":
        assignments = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Assign)
            and ast.unparse(node.value) == "mutation_facts.passed"
            and any(
                ast.unparse(target) == "result['v2_mutation_killed']" for target in node.targets
            )
        ]
        if len(assignments) == 1:
            assignments[0].value = ast.Constant(value=True)
            changed = True
    elif (
        operator == "ignore_snapshot_mismatch"
        and declaration.target_symbol == "validate_v2_snapshot"
    ):
        changed = _replace_guard(
            function,
            lambda node: (
                ast.unparse(node.test)
                == (
                    "not isinstance(snapshot, str) or snapshot != "
                    "verification_snapshot_sha256(evidence)"
                )
                and _raises_contract_code(node, "EVIDENCE_SNAPSHOT_STALE")
            ),
        )
    else:
        raise _RunFailure("MUTATION_OPERATOR_UNSUPPORTED")
    if not changed:
        raise _RunFailure("MUTATION_OPERATOR_PRECONDITION_FAILED")
    ast.fix_missing_locations(tree)
    if _outside_target_dump(tree, declaration.target_symbol) != outside_before:
        raise _RunFailure("MUTATION_OPERATOR_PRECONDITION_FAILED")
    try:
        source = ast.unparse(tree)
        compile(source, str(path), "exec")
    except (SyntaxError, ValueError, TypeError) as error:
        raise _RunFailure("MUTATION_OPERATOR_PRECONDITION_FAILED") from error
    try:
        path.write_text(source + "\n", encoding="utf-8", newline="\n")
    except OSError as error:
        raise _RunFailure("MUTATION_PATCH_WRITE_FAILED") from error


def _minimal_environment(worktree: Path, scratch: Path) -> dict[str, str]:
    executable_dir = str(Path(sys.executable).resolve().parent)
    git = shutil.which("git")
    git_path = Path(git).resolve() if git is not None else None
    if (
        git_path is None
        or not git_path.is_file()
        or git_path.name.lower() not in {"git", "git.exe"}
    ):
        raise _RunFailure("MUTATION_DETECTOR_EXECUTION_FAILED")
    git_dir = str(git_path.parent)
    environment = {
        "PATH": os.pathsep.join((executable_dir, git_dir)),
        "TMP": str(scratch),
        "TEMP": str(scratch),
        "PYTHONPATH": str(worktree / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    if os.name == "nt":
        system_root = _windows_system_root()
        environment["SystemRoot"] = str(system_root)
        environment["PATH"] = os.pathsep.join(
            (executable_dir, git_dir, str(Path(system_root) / "System32"))
        )
    return environment


def _windows_system_root() -> Path:
    value = os.environ.get("SystemRoot")
    if not value:
        raise _RunFailure("MUTATION_DETECTOR_EXECUTION_FAILED")
    try:
        root = Path(value).resolve()
    except OSError as error:
        raise _RunFailure("MUTATION_DETECTOR_EXECUTION_FAILED") from error
    if (
        not root.is_absolute()
        or not root.is_dir()
        or not (root / "System32" / "taskkill.exe").is_file()
    ):
        raise _RunFailure("MUTATION_DETECTOR_EXECUTION_FAILED")
    return root


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        try:
            taskkill = _windows_system_root() / "System32" / "taskkill.exe"
            result = subprocess.run(
                [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                shell=False,
                timeout=5,
            )
            if result.returncode == 0:
                return
        except (OSError, subprocess.SubprocessError, _RunFailure):
            pass
    elif hasattr(os, "killpg"):
        try:
            os.killpg(process.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
            return
        except OSError:
            pass
    process.kill()


def _run_detector(
    worktree: Path, scratch: Path, detector: str
) -> tuple[int | None, bool, int, str | None]:
    started = monotonic()
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "pytest", "-q", detector],
            cwd=worktree,
            env=_minimal_environment(worktree, scratch),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        try:
            exit_code = process.wait(timeout=_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            _terminate_process_tree(process)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    return (
                        None,
                        True,
                        round((monotonic() - started) * 1000),
                        "MUTATION_DETECTOR_EXECUTION_FAILED",
                    )
            return None, True, round((monotonic() - started) * 1000), "MUTATION_DETECTOR_TIMEOUT"
    except (OSError, subprocess.SubprocessError):
        return (
            None,
            False,
            round((monotonic() - started) * 1000),
            "MUTATION_DETECTOR_EXECUTION_FAILED",
        )
    duration = round((monotonic() - started) * 1000)
    if exit_code not in {0, 1}:
        return exit_code, False, duration, "MUTATION_DETECTOR_INFRA_FAILURE"
    return exit_code, False, duration, None


def _not_executed(declarations: tuple[MutationDeclaration, ...]) -> list[MutationProbe]:
    return [
        MutationProbe(item.mutation_id, None, None, False, 0, "MUTATION_NOT_EXECUTED")
        for item in declarations
    ]


def _cleanup_workspace_root(workspace: Path | None) -> bool:
    if workspace is None:
        return True
    try:
        system_temp = Path(tempfile.gettempdir()).resolve()
        return _remove_tree_with_retry(system_temp, workspace)
    except OSError:
        return False


def run_targeted_mutations(
    repository_root: Path,
    subject_commit: str,
    *,
    authorization: _MutationRunnerAuthorization | None = None,
) -> MutationRun:
    """Run the five fixed mutations in serial disposable worktrees.

    Preflight failures deliberately raise ``ContractError``.  Once a workspace
    creation has been attempted, failures are returned as ordered raw probe
    facts so callers can never mistake a partial run for success.
    """
    root = Path(repository_root).resolve()
    _consume_runner_authorization(root, subject_commit, authorization)
    manifest = load_mutation_manifest(root)
    workspace: Path | None = None
    hooks: Path | None = None
    try:
        workspace = _create_workspace_root()
        hooks = _validated_child(workspace, "hooks")
        hooks.mkdir()
        if not hooks.is_dir() or any(hooks.iterdir()):
            raise _RunFailure("MUTATION_WORKSPACE_INVALID")
        _validate_subject(root, hooks, subject_commit)
        paths = _controlled_paths(manifest)
        _assert_controlled_paths_at_subject(root, hooks, subject_commit, paths)
        _assert_no_checkout_filters(root, hooks, subject_commit, paths)
        snapshot = _snapshot_main_tree(root, hooks, paths)
    except _RunFailure as error:
        if not _cleanup_workspace_root(workspace):
            raise _contract(
                "Mutation preflight workspace cleanup failed",
                "MUTATION_WORKTREE_CLEANUP_FAILED",
            ) from error
        raise _contract("Mutation workspace is invalid", error.code) from error
    except ContractError as error:
        if not _cleanup_workspace_root(workspace):
            raise _contract(
                "Mutation preflight workspace cleanup failed",
                "MUTATION_WORKTREE_CLEANUP_FAILED",
            ) from error
        raise
    except OSError as error:
        if not _cleanup_workspace_root(workspace):
            raise _contract(
                "Mutation preflight workspace cleanup failed",
                "MUTATION_WORKTREE_CLEANUP_FAILED",
            ) from error
        raise _contract("Mutation workspace is invalid", "MUTATION_WORKSPACE_INVALID") from error
    assert workspace is not None
    assert hooks is not None
    probes = _not_executed(manifest.mutations)
    cleanup_failed = False
    run_reason: str | None = None
    unchanged = False
    try:
        for index, declaration in enumerate(manifest.mutations):
            worktree: Path | None = None
            scratch: Path | None = None
            baseline: int | None = None
            duration = 0
            try:
                worktree = _validated_child(workspace, declaration.mutation_id)
                scratch = _validated_child(workspace, f"{declaration.mutation_id}-tmp")
                try:
                    scratch.mkdir()
                except OSError as error:
                    raise _RunFailure("MUTATION_WORKSPACE_INVALID") from error
                _create_detached_worktree(root, hooks, worktree, subject_commit)
                try:
                    isolated = load_mutation_manifest(worktree)
                except (ContractError, OSError, UnicodeError) as error:
                    raise _RunFailure("MUTATION_SUBJECT_DRIFT") from error
                if isolated != manifest:
                    raise _RunFailure("MUTATION_SUBJECT_DRIFT")
                baseline, timeout, duration, reason = _run_detector(
                    worktree, scratch, declaration.expected_detector
                )
                if reason is not None:
                    probes[index] = MutationProbe(
                        declaration.mutation_id, baseline, None, timeout, duration, reason
                    )
                    run_reason = reason
                    break
                if baseline != 0:
                    probes[index] = MutationProbe(
                        declaration.mutation_id,
                        baseline,
                        None,
                        False,
                        duration,
                        "MUTATION_BASELINE_FAILED",
                    )
                    run_reason = "MUTATION_BASELINE_FAILED"
                    break
                _apply_mutation(declaration, worktree / declaration.target)
                mutant, timeout, mutant_duration, reason = _run_detector(
                    worktree, scratch, declaration.expected_detector
                )
                probes[index] = MutationProbe(
                    declaration.mutation_id,
                    baseline,
                    mutant,
                    timeout,
                    duration + mutant_duration,
                    reason,
                )
                if reason is not None:
                    run_reason = reason
                    break
            except _RunFailure as error:
                probes[index] = MutationProbe(
                    declaration.mutation_id, baseline, None, False, duration, error.code
                )
                run_reason = error.code
                break
            except (ContractError, OSError, subprocess.SubprocessError):
                probes[index] = MutationProbe(
                    declaration.mutation_id,
                    baseline,
                    None,
                    False,
                    duration,
                    "MUTATION_WORKSPACE_INVALID",
                )
                run_reason = "MUTATION_WORKSPACE_INVALID"
                break
            finally:
                try:
                    if (
                        worktree is not None
                        and worktree.exists()
                        and not _remove_worktree_with_retry(root, hooks, workspace, worktree)
                    ):
                        cleanup_failed = True
                    if (
                        scratch is not None
                        and scratch.exists()
                        and not _remove_tree_with_retry(workspace, scratch)
                    ):
                        cleanup_failed = True
                except (ContractError, OSError, subprocess.SubprocessError):
                    cleanup_failed = True
            if cleanup_failed:
                break
    finally:
        try:
            unchanged = _main_tree_unchanged(root, hooks, snapshot)
        except (ContractError, OSError, subprocess.SubprocessError):
            unchanged = False
        if not _cleanup_workspace_root(workspace):
            cleanup_failed = True
    if not unchanged:
        run_reason = "MUTATION_MAIN_TREE_CHANGED"
    elif cleanup_failed:
        run_reason = "MUTATION_WORKTREE_CLEANUP_FAILED"
    return MutationRun(manifest.manifest_id, subject_commit, tuple(probes), unchanged, run_reason)
