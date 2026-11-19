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
from aiflow.mutation_materials import (
    checkout_matches_materials,
    git_environment,
    loaded_engine_matches,
    material_file_matches,
    subject_materials,
)
from aiflow.mutation_process import ProcessLifecycle, run_bounded_process
from aiflow.mutation_protocol import classify_report, parse_report

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
    baseline_report: bytes | None = None
    mutant_report: bytes | None = None
    baseline_target_sha256: str | None = None
    mutant_target_sha256: str | None = None
    baseline_lifecycle: ProcessLifecycle | None = None
    mutant_lifecycle: ProcessLifecycle | None = None


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


class MutationRunError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


# The installed mutation adapter also catches this exception under its original name.
_RunFailure = MutationRunError


def _contract(message: str, code: str) -> ContractError:
    return ContractError(message, code=code)


def _within(candidate: Path, parent: Path, *, direct: bool = False) -> bool:
    try:
        relative = candidate.relative_to(parent)
    except ValueError:
        return False
    return bool(relative.parts) and (not direct or len(relative.parts) == 1)


def _git(
    root: Path, hooks: Path, *arguments: str, check: bool = True, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run a fixed Git command with hooks disabled and no shell."""
    if not hooks.is_dir() or any(hooks.iterdir()):
        raise _contract("Mutation hooks directory is invalid", "MUTATION_WORKSPACE_INVALID")
    return subprocess.run(
        ["git", "-c", f"core.hooksPath={hooks}", *arguments],
        cwd=root,
        env=git_environment(),
        input=input_bytes,
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


def assert_no_checkout_filters(
    root: Path, hooks: Path, subject: str, paths: tuple[str, ...]
) -> None:
    """Check the exact tree Git will populate, including paths outside the evidence materials."""
    try:
        tree = _git(
            root, hooks, "ls-tree", "-r", "-z", "--name-only", "--full-tree", subject
        ).stdout
        if not tree.endswith(b"\0") or len(tree) > 8 * 1024 * 1024:
            raise ValueError
        tracked = tree[:-1].split(b"\0")
        names = set(tracked)
        if (
            b"" in names
            or len(names) != len(tracked)
            or any(path.encode("utf-8") not in names for path in paths)
        ):
            raise ValueError
        output = _git(
            root,
            hooks,
            "check-attr",
            f"--source={subject}",
            "-z",
            "--stdin",
            "filter",
            input_bytes=tree,
        ).stdout
        fields = output.split(b"\0")
        if fields.pop() or len(fields) != 3 * len(tracked):
            raise ValueError
        for index, path_bytes in enumerate(tracked):
            name, attribute, value = fields[3 * index : 3 * index + 3]
            if (
                name != path_bytes
                or attribute != b"filter"
                or value not in (b"unspecified", b"unset")
            ):
                raise ValueError
        # check-attr renders literal driver names and its two inactive states identically.
        states = "|".join(sorted({value.decode("ascii") for value in fields[2::3]}))
        drivers = _git(
            root,
            hooks,
            "config",
            "--name-only",
            "--get-regexp",
            rf"^filter\.({states})\.(clean|smudge|process|required)$",
            check=False,
        )
        if drivers.returncode != 1 or drivers.stdout or drivers.stderr:
            raise ValueError
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise _contract(
            "Checkout filters could not be verified", "MUTATION_WORKSPACE_INVALID"
        ) from error


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
        raise MutationRunError("MUTATION_WORKSPACE_INVALID") from error
    if not _within(root, system_temp, direct=True) or not root.name.startswith("aiflow-mutation-"):
        raise MutationRunError("MUTATION_WORKSPACE_INVALID")
    return root


def _validated_child(root: Path, name: str) -> Path:
    if not name or name in {".", ".."} or "/" in name or "\\" in name or Path(name).name != name:
        raise MutationRunError("MUTATION_WORKTREE_PATH_ESCAPE")
    candidate = (root / name).resolve()
    if not _within(candidate, root, direct=True):
        raise MutationRunError("MUTATION_WORKTREE_PATH_ESCAPE")
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
        assert_no_checkout_filters(path, hooks, subject, ())
        _git(path, hooks, "checkout", "--detach", subject)
    except (OSError, subprocess.SubprocessError) as error:
        raise MutationRunError("MUTATION_WORKTREE_CREATE_FAILED") from error


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


def mutation_bytes(declaration: MutationDeclaration, original: bytes) -> bytes:
    """Derive the fixed transformation without executing or writing target code."""
    if _OPERATOR_BINDINGS.get(declaration.operator) != (
        declaration.target,
        declaration.target_symbol,
    ):
        raise MutationRunError("MUTATION_OPERATOR_UNSUPPORTED")
    try:
        tree = ast.parse(original.decode("utf-8", "strict"), filename=declaration.target)
    except (UnicodeDecodeError, SyntaxError) as error:
        raise MutationRunError("MUTATION_OPERATOR_PRECONDITION_FAILED") from error
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == declaration.target_symbol
    ]
    if len(functions) != 1:
        raise MutationRunError("MUTATION_OPERATOR_PRECONDITION_FAILED")
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
        raise MutationRunError("MUTATION_OPERATOR_UNSUPPORTED")
    if not changed:
        raise MutationRunError("MUTATION_OPERATOR_PRECONDITION_FAILED")
    ast.fix_missing_locations(tree)
    if _outside_target_dump(tree, declaration.target_symbol) != outside_before:
        raise MutationRunError("MUTATION_OPERATOR_PRECONDITION_FAILED")
    try:
        source = ast.unparse(tree)
        compile(source, declaration.target, "exec")
    except (SyntaxError, ValueError, TypeError) as error:
        raise MutationRunError("MUTATION_OPERATOR_PRECONDITION_FAILED") from error
    return (source + "\n").encode("utf-8")


def _apply_mutation(declaration: MutationDeclaration, path: Path) -> None:
    """Write the deterministic transformation to the isolated worktree only."""
    try:
        original = path.read_bytes()
        path.write_bytes(mutation_bytes(declaration, original))
    except OSError as error:
        raise MutationRunError("MUTATION_PATCH_WRITE_FAILED") from error


def detector_environment(worktree: Path, scratch: Path) -> dict[str, str]:
    executable_dir = str(Path(sys.executable).resolve().parent)
    git = shutil.which("git")
    git_path = Path(git).resolve() if git is not None else None
    if (
        git_path is None
        or not git_path.is_file()
        or git_path.name.lower() not in {"git", "git.exe"}
    ):
        raise MutationRunError("MUTATION_DETECTOR_EXECUTION_FAILED")
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
        raise MutationRunError("MUTATION_DETECTOR_EXECUTION_FAILED")
    try:
        root = Path(value).resolve()
    except OSError as error:
        raise MutationRunError("MUTATION_DETECTOR_EXECUTION_FAILED") from error
    if not root.is_absolute() or not root.is_dir() or not (root / "System32").is_dir():
        raise MutationRunError("MUTATION_DETECTOR_EXECUTION_FAILED")
    return root


def _run_detector(
    worktree: Path, scratch: Path, mutation_id: str, target_sha256: str
) -> tuple[int | None, bool, int, str | None, bytes | None, ProcessLifecycle | None]:
    """Run the controlled reporter with a bounded pipe and verified process cleanup."""
    try:
        result = run_bounded_process(
            [
                sys.executable,
                "-I",
                "-B",
                str(worktree / "src/aiflow/mutation_reporter.py"),
                mutation_id,
                str(worktree),
                target_sha256,
            ],
            cwd=worktree,
            env=detector_environment(worktree, scratch),
            timeout_seconds=_TIMEOUT_SECONDS,
            max_output_bytes=16384,
        )
    except MutationRunError:
        return None, False, 0, "MUTATION_DETECTOR_EXECUTION_FAILED", None, None
    except BaseException:
        # A failed process wrapper cannot prove that descendants were reaped.
        return None, False, 0, "MUTATION_PROCESS_CLEANUP_UNKNOWN", None, None
    if result.cleanup_unknown:
        return (
            result.returncode,
            result.reason == "timeout",
            result.duration_ms,
            "MUTATION_PROCESS_CLEANUP_UNKNOWN",
            None,
            None,
        )
    if result.reason is not None:
        reason = {
            "timeout": "MUTATION_DETECTOR_TIMEOUT",
            "overflow": "MUTATION_DETECTOR_REPORT_INVALID",
            "read_error": "MUTATION_DETECTOR_REPORT_INVALID",
            "report_incomplete": "MUTATION_DETECTOR_REPORT_INVALID",
            "pytest_early_stop": "MUTATION_DETECTOR_EARLY_STOP",
            "processes_remaining": "MUTATION_DETECTOR_PROCESSES_REMAIN",
        }.get(result.reason, "MUTATION_DETECTOR_EXECUTION_FAILED")
        return result.returncode, result.reason == "timeout", result.duration_ms, reason, None, None
    if result.returncode not in {0, 1} or result.report is None:
        return (
            result.returncode,
            False,
            result.duration_ms,
            "MUTATION_DETECTOR_INFRA_FAILURE",
            None,
            None,
        )
    if result.lifecycle is None or not result.lifecycle.matches_observation(
        result.report, result.returncode
    ):
        return (
            result.returncode,
            False,
            result.duration_ms,
            "MUTATION_PROCESS_CLEANUP_UNKNOWN",
            None,
            None,
        )
    try:
        parse_report(result.report, mutation_id, target_sha256)
    except (ValueError, TypeError):
        return (
            result.returncode,
            False,
            result.duration_ms,
            "MUTATION_DETECTOR_REPORT_INVALID",
            None,
            None,
        )
    return result.returncode, False, result.duration_ms, None, result.report, result.lifecycle


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
            raise MutationRunError("MUTATION_WORKSPACE_INVALID")
        _validate_subject(root, hooks, subject_commit)
        declared_paths = _controlled_paths(manifest)
        materials = subject_materials(root, subject_commit)
        if not loaded_engine_matches(root, materials):
            raise MutationRunError("MUTATION_SUBJECT_DRIFT")
        paths = tuple(sorted(materials))
        if not set(declared_paths).issubset(materials):
            raise MutationRunError("MUTATION_SUBJECT_DRIFT")
        assert_no_checkout_filters(root, hooks, subject_commit, paths)
        _assert_controlled_paths_at_subject(root, hooks, subject_commit, paths)
        if not all(material_file_matches(root, path, materials[path]) for path in paths):
            raise MutationRunError("MUTATION_SUBJECT_DRIFT")
        snapshot = _snapshot_main_tree(root, hooks, paths)
    except MutationRunError as error:
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
    cleanup_unknown = False
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
                    raise MutationRunError("MUTATION_WORKSPACE_INVALID") from error
                _create_detached_worktree(root, hooks, worktree, subject_commit)
                if not checkout_matches_materials(worktree, materials):
                    raise MutationRunError("MUTATION_SUBJECT_DRIFT")
                try:
                    isolated = load_mutation_manifest(worktree)
                except (ContractError, OSError, UnicodeError) as error:
                    raise MutationRunError("MUTATION_SUBJECT_DRIFT") from error
                if isolated != manifest:
                    raise MutationRunError("MUTATION_SUBJECT_DRIFT")
                baseline_target_sha256 = _digest(worktree / declaration.target)
                baseline, timeout, duration, reason, baseline_report, baseline_lifecycle = (
                    _run_detector(
                        worktree, scratch, declaration.mutation_id, baseline_target_sha256
                    )
                )
                if reason is None and (baseline_report is None or baseline is None):
                    reason = "MUTATION_DETECTOR_REPORT_INVALID"
                if reason is None and baseline_report is not None and baseline is not None:
                    baseline_facts = parse_report(
                        baseline_report, declaration.mutation_id, baseline_target_sha256
                    )
                    if (
                        classify_report(
                            baseline_facts,
                            mutation_id=declaration.mutation_id,
                            target_sha256=baseline_target_sha256,
                            exit_code=baseline,
                            baseline=True,
                        )
                        != "passed"
                    ):
                        reason = "MUTATION_BASELINE_FAILED"
                if reason is None and not checkout_matches_materials(worktree, materials):
                    reason = "MUTATION_SUBJECT_DRIFT"
                if reason is not None:
                    cleanup_unknown = reason == "MUTATION_PROCESS_CLEANUP_UNKNOWN"
                    probes[index] = MutationProbe(
                        declaration.mutation_id,
                        baseline,
                        None,
                        timeout,
                        duration,
                        reason,
                        baseline_report,
                        None,
                        baseline_target_sha256,
                        None,
                        baseline_lifecycle,
                        None,
                    )
                    run_reason = reason
                    break
                _apply_mutation(declaration, worktree / declaration.target)
                mutant_target_sha256 = _digest(worktree / declaration.target)
                mutant_materials = dict(materials)
                mutant_materials[declaration.target] = mutation_bytes(
                    declaration, materials[declaration.target]
                )
                if not checkout_matches_materials(worktree, mutant_materials):
                    raise MutationRunError("MUTATION_SUBJECT_DRIFT")
                mutant, timeout, mutant_duration, reason, mutant_report, mutant_lifecycle = (
                    _run_detector(worktree, scratch, declaration.mutation_id, mutant_target_sha256)
                )
                if reason is None and (mutant_report is None or mutant is None):
                    reason = "MUTATION_DETECTOR_REPORT_INVALID"
                if reason is None and mutant_report is not None and mutant is not None:
                    mutant_facts = parse_report(
                        mutant_report, declaration.mutation_id, mutant_target_sha256
                    )
                    if classify_report(
                        mutant_facts,
                        mutation_id=declaration.mutation_id,
                        target_sha256=mutant_target_sha256,
                        exit_code=mutant,
                        baseline=False,
                    ) not in {"killed", "survived"}:
                        reason = "MUTATION_DETECTOR_REPORT_INVALID"
                if reason is None and not checkout_matches_materials(worktree, mutant_materials):
                    reason = "MUTATION_SUBJECT_DRIFT"
                probes[index] = MutationProbe(
                    declaration.mutation_id,
                    baseline,
                    mutant,
                    timeout,
                    duration + mutant_duration,
                    reason,
                    baseline_report,
                    mutant_report,
                    baseline_target_sha256,
                    mutant_target_sha256,
                    baseline_lifecycle,
                    mutant_lifecycle,
                )
                if reason is not None:
                    cleanup_unknown = reason == "MUTATION_PROCESS_CLEANUP_UNKNOWN"
                    run_reason = reason
                    break

            except MutationRunError as error:
                probes[index] = MutationProbe(
                    declaration.mutation_id, baseline, None, False, duration, error.code
                )
                run_reason = error.code
                break
            except (ContractError, OSError, ValueError, TypeError, subprocess.SubprocessError):
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
                        not cleanup_unknown
                        and worktree is not None
                        and worktree.exists()
                        and not _remove_worktree_with_retry(root, hooks, workspace, worktree)
                    ):
                        cleanup_failed = True
                    if (
                        not cleanup_unknown
                        and scratch is not None
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
        if not cleanup_unknown and not _cleanup_workspace_root(workspace):
            cleanup_failed = True
    if cleanup_unknown:
        run_reason = "MUTATION_PROCESS_CLEANUP_UNKNOWN"
    elif not unchanged:
        run_reason = "MUTATION_MAIN_TREE_CHANGED"
    elif cleanup_failed:
        run_reason = "MUTATION_WORKTREE_CLEANUP_FAILED"
    return MutationRun(manifest.manifest_id, subject_commit, tuple(probes), unchanged, run_reason)
