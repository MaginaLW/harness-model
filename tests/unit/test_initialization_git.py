"""Read-only initialization facts and bounded Git process failures."""

from __future__ import annotations

import hashlib
import importlib
import io
import os
import shutil
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

import pytest
from initialization_helpers import fixture_git as git
from initialization_helpers import snapshot_tree as tree

from aiflow.errors import AiflowError

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/aiflow/initialization_git.py"
try:
    SOURCE.lstat()
except FileNotFoundError:
    pytestmark = pytest.mark.skip(reason="initialization Git helper is not implemented")
else:
    helper = importlib.import_module("aiflow.initialization_git")
    if helper.__file__ is None or Path(helper.__file__).resolve() != SOURCE.resolve():
        raise ImportError("initialization Git helper is not from the tested checkout")


@pytest.fixture(scope="session")
def git_seed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("initialization-git-seed")
    git(root, "init", "-b", "feature")
    (root / ".gitignore").write_bytes(b".private/\n")
    (root / "source.py").write_bytes(b"x = 1\n")
    (root / "readme.txt").write_bytes(b"source fixture\n")
    git(root, "add", ".gitignore", "source.py", "readme.txt")
    git(
        root,
        "-c",
        "user.name=AI Flow Test",
        "-c",
        "user.email=initialization@example.invalid",
        "commit",
        "-m",
        "fixture baseline",
    )
    return root


@pytest.fixture
def repository(tmp_path: Path, git_seed: Path) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(git_seed, root)
    return root


def test_root_and_child_resolve_to_the_same_physical_repository(repository: Path) -> None:
    child = repository / "folder"
    child.mkdir()
    before = tree(repository)
    assert helper.resolve_initialization_root(repository) == repository
    assert helper.resolve_initialization_root(child) == repository
    assert tree(repository) == before


def test_observation_is_read_only_and_binds_head_index_and_file_content(repository: Path) -> None:
    before = tree(repository)
    observed = helper.observe_initialization_target(repository)

    assert observed["root"] == repository.as_posix()
    assert observed["git_dir"] == (repository / ".git").as_posix()
    assert observed["common_dir"] == observed["git_dir"]
    assert observed["head"] == git(repository, "rev-parse", "HEAD")
    assert observed["branch"] == {"kind": "branch", "name": "feature"}
    assert observed["root_identity"] == {
        "device": repository.stat().st_dev,
        "inode": repository.stat().st_ino,
    }
    assert (
        observed["index_sha256"]
        == hashlib.sha256((repository / ".git/index").read_bytes()).hexdigest()
    )
    assert observed["tracked_count"] == observed["file_count"] == 3
    assert observed["untracked_count"] == 0
    assert observed["python_source_count"] == 1
    assert tree(repository) == before


def test_detached_head_and_branch_literally_named_detached_are_typed(repository: Path) -> None:
    git(repository, "switch", "-c", "DETACHED")
    branch = helper.observe_initialization_target(repository)
    git(repository, "switch", "--detach", "HEAD")
    detached = helper.observe_initialization_target(repository)
    assert branch["branch"] == {"kind": "branch", "name": "DETACHED"}
    assert detached["branch"] == {"kind": "detached"}
    assert branch["head"] == detached["head"]


@pytest.mark.parametrize("kind", ["tracked", "untracked"])
def test_repeated_dirty_edits_are_bound_even_when_git_status_is_the_same(
    repository: Path, kind: str
) -> None:
    path = repository / ("source.py" if kind == "tracked" else "untracked.py")
    path.write_bytes(b"first edit\n")
    first = helper.observe_initialization_target(repository)
    path.write_bytes(b"second edit\n")
    second = helper.observe_initialization_target(repository)
    assert first["worktree_sha256"] != second["worktree_sha256"]
    assert first["index_sha256"] == second["index_sha256"]


def test_ignored_private_bytes_are_outside_the_observation(repository: Path) -> None:
    ignored = repository / ".private"
    ignored.mkdir()
    secret = ignored / "credentials.txt"
    secret.write_bytes(b"first private fixture\n")
    first = helper.observe_initialization_target(repository)
    secret.write_bytes(b"second private fixture\n")
    second = helper.observe_initialization_target(repository)
    assert first == second


def test_only_exact_installation_paths_can_be_excluded(repository: Path) -> None:
    before = helper.observe_initialization_target(repository)
    directory = repository / ".ai"
    directory.mkdir()
    (directory / "init-state.json").write_bytes(b"synthetic state fixture\n")
    excluded = helper.observe_initialization_target(repository, exclude_initialization=True)
    assert excluded == before
    (directory / "unrelated.txt").write_bytes(b"unknown user bytes\n")
    unknown = helper.observe_initialization_target(repository, exclude_initialization=True)
    assert unknown["worktree_sha256"] != before["worktree_sha256"]
    assert unknown["untracked_count"] == 1


def test_tracked_identity_history_cannot_be_given_a_fresh_installation(repository: Path) -> None:
    directory = repository / ".ai"
    directory.mkdir()
    (directory / "repository-id").write_bytes(b"existing identity\n")
    git(repository, "add", ".ai/repository-id")
    before = tree(repository)
    with pytest.raises(AiflowError) as error:
        helper.observe_initialization_target(repository, exclude_initialization=True)
    assert error.value.code == "INIT_EXISTING_IDENTITY"
    assert tree(repository) == before


def test_deleted_tracked_file_is_bound_as_missing(repository: Path) -> None:
    original = helper.observe_initialization_target(repository)
    (repository / "source.py").unlink()
    deleted = helper.observe_initialization_target(repository)
    assert deleted["worktree_sha256"] != original["worktree_sha256"]
    assert deleted["tracked_count"] == original["tracked_count"]
    assert deleted["python_source_count"] == 0


@pytest.mark.parametrize(
    "limit",
    ["MAX_FILES", "MAX_FILE_BYTES", "MAX_TOTAL_BYTES", "MAX_INDEX_BYTES", "MAX_GIT_OUTPUT_BYTES"],
)
def test_observation_limits_reject_without_changing_any_fixture_bytes(
    repository: Path, monkeypatch: pytest.MonkeyPatch, limit: str
) -> None:
    monkeypatch.setattr(helper, limit, 1)
    before = tree(repository)
    with pytest.raises(AiflowError):
        helper.observe_initialization_target(repository)
    assert tree(repository) == before


def test_whole_observation_has_a_deadline(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(helper, "OBSERVATION_TIMEOUT_SECONDS", 0)
    before = tree(repository)
    with pytest.raises(AiflowError) as error:
        helper.observe_initialization_target(repository)
    assert error.value.code == "INIT_GIT_TIMEOUT"
    assert tree(repository) == before


def test_hardlinked_worktree_input_is_not_an_ordinary_bound_file(
    repository: Path, tmp_path: Path
) -> None:
    os.link(repository / "source.py", tmp_path / "shared.py")
    before = tree(repository)
    with pytest.raises(AiflowError):
        helper.observe_initialization_target(repository)
    assert tree(repository) == before


def test_local_fsmonitor_helper_is_never_executed(repository: Path) -> None:
    marker = repository / ".git/was-executed"
    script = repository / ".git/untrusted.py"
    script.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n", encoding="utf-8"
    )
    git(repository, "config", "core.fsmonitor", f'"{sys.executable}" "{script}"')
    before = tree(repository)
    helper.observe_initialization_target(repository)
    assert not marker.exists()
    assert tree(repository) == before


def test_git_environment_injection_cannot_change_repository_selection(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evil = tmp_path / "not-a-git-directory"
    evil.mkdir()
    monkeypatch.setenv("GIT_DIR", str(evil))
    monkeypatch.setenv("GIT_WORK_TREE", str(evil))
    assert helper.resolve_initialization_root(repository) == repository
    assert helper.observe_initialization_target(repository)["root"] == repository.as_posix()


def test_nongit_and_unborn_repositories_cannot_be_initialized(tmp_path: Path) -> None:
    root = tmp_path / "unborn"
    root.mkdir()
    with pytest.raises(AiflowError):
        helper.resolve_initialization_root(root)
    git(root, "init", "-b", "feature")
    before = tree(root)
    with pytest.raises(AiflowError):
        helper.observe_initialization_target(root)
    assert tree(root) == before


def test_nested_repository_is_observed_independently(repository: Path, git_seed: Path) -> None:
    nested = repository / "nested"
    shutil.copytree(git_seed, nested)
    observed = helper.observe_initialization_target(nested)
    assert observed["root"] == nested.as_posix()
    assert observed["git_dir"] == (nested / ".git").as_posix()


def test_inflight_head_change_is_not_a_stable_observation(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = helper._head_and_branch
    calls = 0

    def changed(*arguments):
        nonlocal calls
        calls += 1
        head, branch = original(*arguments)
        return (head, branch) if calls == 1 else ("0" * 40, branch)

    monkeypatch.setattr(helper, "_head_and_branch", changed)
    before = tree(repository)
    with pytest.raises(AiflowError) as error:
        helper.observe_initialization_target(repository)
    assert error.value.code == "INIT_GIT_CHANGED"
    assert tree(repository) == before


class FakeProcess:
    def __init__(self, stdout=b"facts\n", stderr=b"", code=0, running=False):
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)
        self.returncode = None if running else code
        self.killed = False
        self.fail_cleanup = False

    def poll(self):
        return self.returncode

    def kill(self):
        if self.fail_cleanup:
            raise OSError("synthetic unconfirmed process termination")
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.fail_cleanup:
            raise subprocess.TimeoutExpired("fixture", timeout)
        return self.returncode


def fake_runner(monkeypatch: pytest.MonkeyPatch, process: FakeProcess) -> list:
    calls = []

    def spawn(command, **keywords):
        calls.append((command, keywords))
        return process

    monkeypatch.setattr(helper.subprocess, "Popen", spawn)
    return calls


def run_fake(repository: Path, *, allowed=(0,), deadline=None):
    return helper._run_git(
        repository,
        ("rev-parse", "--show-toplevel"),
        deadline=monotonic() + 1 if deadline is None else deadline,
        allowed_returncodes=allowed,
        program=Path(sys.executable),
    )


def test_runner_uses_fixed_argv_and_an_explicit_credential_free_environment(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("NPM_TOKEN", "private-test-marker")
    monkeypatch.setenv("HTTPS_PROXY", "private-test-proxy")
    calls = fake_runner(monkeypatch, FakeProcess())
    assert run_fake(repository) == (0, b"facts\n")
    command, options = calls[0]
    assert command[-2:] == ["rev-parse", "--show-toplevel"]
    assert "core.fsmonitor=false" in command
    assert options["shell"] is False
    assert options["stdout"] == options["stderr"] == subprocess.PIPE
    environment = options["env"]
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert not {"GIT_CONFIG_COUNT", "NPM_TOKEN", "HTTPS_PROXY"}.intersection(environment)


@pytest.mark.parametrize("stream", ["stdout", "stderr", "aggregate"])
def test_runner_bounds_both_output_streams_before_accepting_exit_zero(
    repository: Path, monkeypatch: pytest.MonkeyPatch, stream: str
) -> None:
    monkeypatch.setattr(helper, "MAX_GIT_OUTPUT_BYTES", 4)
    process = FakeProcess(
        stdout=b"12345" if stream == "stdout" else b"123",
        stderr=b"12345" if stream == "stderr" else (b"45" if stream == "aggregate" else b""),
    )
    fake_runner(monkeypatch, process)
    with pytest.raises(AiflowError) as error:
        run_fake(repository)
    assert error.value.code == "INIT_GIT_OUTPUT_LIMIT"


@pytest.mark.parametrize("code,allowed", [(1, (0,)), (2, (0, 1)), (-9, (0,))])
def test_runner_nonpermitted_exit_is_not_a_valid_fact(
    repository: Path, monkeypatch: pytest.MonkeyPatch, code: int, allowed: tuple
) -> None:
    fake_runner(monkeypatch, FakeProcess(code=code))
    with pytest.raises(AiflowError):
        run_fake(repository, allowed=allowed)


def test_runner_allows_only_explicitly_permitted_nonzero_result(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_runner(monkeypatch, FakeProcess(code=1))
    assert run_fake(repository, allowed=(0, 1)) == (1, b"facts\n")


def test_runner_deadline_stops_a_process_that_does_not_exit(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(stdout=b"", running=True)
    fake_runner(monkeypatch, process)
    monkeypatch.setattr(helper, "GIT_TIMEOUT_SECONDS", 0.02)
    with pytest.raises(AiflowError) as error:
        run_fake(repository)
    assert error.value.code == "INIT_GIT_TIMEOUT"
    assert process.killed


def test_runner_unconfirmed_termination_cannot_produce_facts(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = FakeProcess(stdout=b"", running=True)
    process.fail_cleanup = True
    fake_runner(monkeypatch, process)
    monkeypatch.setattr(helper, "GIT_TIMEOUT_SECONDS", 0.02)
    with pytest.raises(AiflowError) as error:
        run_fake(repository)
    assert error.value.code == "INIT_GIT_CLEANUP_UNCONFIRMED"


def test_runner_deadline_also_covers_eof_after_process_exit(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()

    class HeldPipe(io.BytesIO):
        def read1(self, size=-1):
            release.wait()
            return b""

    process = FakeProcess(stdout=b"")
    process.stdout = HeldPipe()
    fake_runner(monkeypatch, process)
    monkeypatch.setattr(helper, "GIT_TIMEOUT_SECONDS", 0.02)
    try:
        with pytest.raises(AiflowError) as error:
            run_fake(repository)
        assert error.value.code == "INIT_GIT_CLEANUP_UNCONFIRMED"
    finally:
        release.set()


def test_runner_expired_deadline_does_not_start_a_process(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = fake_runner(monkeypatch, FakeProcess())
    with pytest.raises(AiflowError):
        run_fake(repository, deadline=monotonic() - 1)
    assert not calls


@pytest.mark.parametrize(
    "raw", [b"relative\\file", b"../outside", b"/absolute", b"C:/outside", b"a//b", b"\xff"]
)
def test_git_paths_cannot_escape_or_use_ambiguous_encoding(raw: bytes) -> None:
    with pytest.raises(AiflowError):
        helper._relative_path(raw)


@pytest.mark.parametrize("raw", [b"not-terminated", b"\0", b"one\0\0"])
def test_nul_git_records_are_complete_nonempty_records(raw: bytes) -> None:
    with pytest.raises(AiflowError):
        helper._records(raw)


@pytest.mark.parametrize("kind", ["missing", "file", "traversal"])
def test_target_paths_must_be_real_nontraversing_directories(repository: Path, kind: str) -> None:
    path = {
        "missing": repository / "absent",
        "file": repository / "source.py",
        "traversal": repository / "folder/../source.py",
    }[kind]
    with pytest.raises(AiflowError):
        helper.resolve_initialization_root(path)


@pytest.mark.parametrize("kind", ["missing", "inside-target", "wrong-program"])
def test_git_program_must_be_available_and_outside_the_target(
    repository: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    if kind == "missing":
        found = None
    elif kind == "inside-target":
        candidate = repository / "git.exe"
        candidate.write_bytes(b"untrusted target executable\n")
        found = str(candidate)
    else:
        found = sys.executable
    monkeypatch.setattr(helper.shutil, "which", lambda _name: found)
    with pytest.raises(AiflowError) as error:
        helper.resolve_initialization_root(repository)
    assert error.value.code == "INIT_GIT_UNAVAILABLE"


def test_posix_environment_does_not_add_windows_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    proxy = SimpleNamespace(**{**vars(os), "name": "posix"})
    monkeypatch.setattr(helper, "os", proxy)
    environment = helper._environment(Path(sys.executable))
    assert "SystemRoot" not in environment


def test_windows_environment_requires_a_system_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    proxy = SimpleNamespace(**{**vars(os), "name": "nt", "environ": {}})
    monkeypatch.setattr(helper, "os", proxy)
    with pytest.raises(AiflowError):
        helper._environment(Path(sys.executable))


def test_git_spawn_failure_does_not_produce_empty_successful_facts(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(*_arguments, **_keywords):
        raise OSError("synthetic missing executable")

    monkeypatch.setattr(helper.subprocess, "Popen", unavailable)
    with pytest.raises(AiflowError) as error:
        run_fake(repository)
    assert error.value.code == "INIT_GIT_UNAVAILABLE"


def test_pipe_read_failure_cannot_be_reported_as_exit_zero_success(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailedPipe(io.BytesIO):
        def read1(self, _size=-1):
            raise OSError("synthetic read failure")

    process = FakeProcess()
    process.stdout = FailedPipe()
    fake_runner(monkeypatch, process)
    with pytest.raises(AiflowError):
        run_fake(repository)


def fake_git_protocol(repository: Path, monkeypatch: pytest.MonkeyPatch) -> dict[tuple, tuple]:
    names = [".gitignore", "readme.txt", "source.py"]
    protocol = {
        ("rev-parse", "--show-toplevel"): (0, repository.as_posix().encode() + b"\n"),
        ("rev-parse", "--absolute-git-dir"): (0, (repository / ".git").as_posix().encode() + b"\n"),
        ("rev-parse", "--git-common-dir"): (0, b".git\n"),
        ("rev-parse", "--verify", "HEAD^{commit}"): (0, b"a" * 40 + b"\n"),
        ("symbolic-ref", "--quiet", "HEAD"): (0, b"refs/heads/feature\n"),
        ("ls-tree", "-r", "-z", "--name-only", "HEAD"): (
            0,
            b"\0".join(name.encode() for name in names) + b"\0",
        ),
        ("ls-files", "--stage", "-z"): (
            0,
            b"".join(b"100644 " + b"b" * 40 + b" 0\t" + name.encode() + b"\0" for name in names),
        ),
        ("ls-files", "--others", "--exclude-standard", "-z"): (0, b""),
    }

    def read(_cwd, arguments, **_keywords):
        return protocol[arguments]

    monkeypatch.setattr(helper, "_run_git", read)
    return protocol


@pytest.mark.parametrize(
    "record",
    [
        b"no-tab\0",
        b"100644\tfile\0",
        b"120000 " + b"a" * 40 + b" 0\tfile\0",
        b"100644 invalid-sha 0\tfile\0",
        b"100644 " + b"a" * 40 + b" 1\tfile\0",
        (b"100644 " + b"a" * 40 + b" 0\tsource.py\0") * 2,
    ],
    ids=["no-separator", "missing-fields", "not-regular", "bad-sha", "unmerged", "duplicate"],
)
def test_git_stage_records_must_be_complete_regular_unique_stage_zero_entries(
    repository: Path, monkeypatch: pytest.MonkeyPatch, record: bytes
) -> None:
    protocol = fake_git_protocol(repository, monkeypatch)
    protocol[("ls-files", "--stage", "-z")] = (0, record)
    with pytest.raises(AiflowError):
        helper.observe_initialization_target(repository)


@pytest.mark.parametrize("data", [b"not-a-sha\n", b"\xff\n"])
def test_invalid_head_protocol_is_not_a_valid_identity(
    repository: Path, monkeypatch: pytest.MonkeyPatch, data: bytes
) -> None:
    protocol = fake_git_protocol(repository, monkeypatch)
    protocol[("rev-parse", "--verify", "HEAD^{commit}")] = (0, data)
    with pytest.raises(AiflowError):
        helper.observe_initialization_target(repository)


@pytest.mark.parametrize("branch", [b"", b"HEAD\n", b"refs/heads/\n"])
def test_symbolic_ref_must_be_a_nonempty_branch_reference(
    repository: Path, monkeypatch: pytest.MonkeyPatch, branch: bytes
) -> None:
    protocol = fake_git_protocol(repository, monkeypatch)
    protocol[("symbolic-ref", "--quiet", "HEAD")] = (0, branch)
    with pytest.raises(AiflowError):
        helper.observe_initialization_target(repository)


@pytest.mark.parametrize("untracked", [b"new.py\0new.py\0", b"source.py\0", b"missing.py\0"])
def test_untracked_protocol_cannot_duplicate_tracked_or_missing_content(
    repository: Path, monkeypatch: pytest.MonkeyPatch, untracked: bytes
) -> None:
    protocol = fake_git_protocol(repository, monkeypatch)
    protocol[("ls-files", "--others", "--exclude-standard", "-z")] = (0, untracked)
    with pytest.raises(AiflowError):
        helper.observe_initialization_target(repository)


def test_combined_tracked_and_untracked_count_is_bounded(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protocol = fake_git_protocol(repository, monkeypatch)
    (repository / "new.py").write_bytes(b"new file\n")
    protocol[("ls-files", "--others", "--exclude-standard", "-z")] = (0, b"new.py\0")
    monkeypatch.setattr(helper, "MAX_FILES", 3)
    with pytest.raises(AiflowError) as error:
        helper.observe_initialization_target(repository)
    assert error.value.code == "INIT_GIT_FILE_LIMIT"


def test_missing_tracked_parent_is_a_bound_deletion(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protocol = fake_git_protocol(repository, monkeypatch)
    protocol[("ls-files", "--stage", "-z")] = (
        0,
        b"100644 " + b"a" * 40 + b" 0\tmissing/deep/source.py\0",
    )
    observed = helper.observe_initialization_target(repository)
    assert observed["tracked_count"] == 1
    assert observed["file_count"] == 1
    assert observed["python_source_count"] == 0


def test_linked_worktree_cannot_be_fresh_initialized(repository: Path) -> None:
    marker = repository / ".git"
    relocated = repository / "git-data"
    marker.rename(relocated)
    marker.write_text(f"gitdir: {relocated.as_posix()}\n", encoding="utf-8")
    before = tree(repository)
    with pytest.raises(AiflowError) as error:
        helper.observe_initialization_target(repository)
    assert error.value.code == "INIT_LINKED_WORKTREE_UNSUPPORTED"
    assert tree(repository) == before


def test_external_config_include_is_rejected_before_spawning_git(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with (repository / ".git/config").open("ab") as stream:
        stream.write(b'\n[include]\n path = "outside-config"\n')

    def unexpected(*_arguments, **_keywords):
        pytest.fail("Git was spawned before rejecting an external config include")

    monkeypatch.setattr(helper.subprocess, "Popen", unexpected)
    with pytest.raises(AiflowError) as error:
        helper.observe_initialization_target(repository)
    assert error.value.code == "INIT_GIT_CONFIG_UNSUPPORTED"


@pytest.mark.parametrize("stage", ["opened", "after-read"])
def test_file_object_or_metadata_drift_during_read_is_rejected(
    repository: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    original = os.fstat
    calls = 0

    def changed(descriptor):
        nonlocal calls
        calls += 1
        info = original(descriptor)
        if (stage == "opened" and calls == 1) or (stage == "after-read" and calls == 2):
            fields = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
            fields["st_ino" if stage == "opened" else "st_mtime_ns"] += 1
            return SimpleNamespace(**fields)
        return info

    monkeypatch.setattr(helper, "os", SimpleNamespace(**{**vars(os), "fstat": changed}))
    with pytest.raises(AiflowError) as error:
        helper._file_facts(repository / "source.py", 1024, monotonic() + 5)
    assert error.value.code == "INIT_GIT_CHANGED"


@pytest.mark.parametrize("bound", ["individual", "total"])
def test_growing_file_cannot_exceed_a_bound_between_stat_and_read(
    repository: Path, monkeypatch: pytest.MonkeyPatch, bound: str
) -> None:
    path = repository / "source.py"
    path.write_bytes(b"1234")
    real_fdopen = os.fdopen

    class GrowingReader:
        def __init__(self, stream):
            self.stream = stream
            self.grown = False

        def fileno(self):
            return self.stream.fileno()

        def read(self, size):
            if not self.grown:
                with path.open("ab") as output:
                    output.write(b"5")
                self.grown = True
            return self.stream.read(size)

    @contextmanager
    def fdopen(descriptor, mode):
        with real_fdopen(descriptor, mode) as stream:
            yield GrowingReader(stream)

    monkeypatch.setattr(helper, "os", SimpleNamespace(**{**vars(os), "fdopen": fdopen}))
    with pytest.raises(AiflowError) as error:
        helper._file_facts(
            path,
            4 if bound == "individual" else 10,
            monotonic() + 5,
            total_remaining=4 if bound == "total" else None,
        )
    assert error.value.code == "INIT_GIT_FILE_LIMIT"
    assert path.read_bytes() == b"12345"


def test_unreadable_or_missing_file_is_not_an_empty_digest(repository: Path) -> None:
    with pytest.raises(AiflowError) as error:
        helper._file_facts(repository / "missing", 1024, monotonic() + 5)
    assert error.value.code == "INIT_GIT_READ_FAILED"


@pytest.mark.parametrize("entry", ["resolve", "observe", "runner"])
@pytest.mark.parametrize(
    "nested,outer_tool",
    [(False, False), (True, False), (True, True)],
    ids=["plain-worktree", "nested-worktree", "outer-tool-hidden-by-nested-marker"],
)
def test_subdirectory_invocation_rejects_tools_inside_any_enclosing_worktree(
    repository: Path,
    git_seed: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry: str,
    nested: bool,
    outer_tool: bool,
) -> None:
    root = repository
    if nested:
        root = repository / "nested"
        shutil.copytree(git_seed, root)
    child = root / "subdirectory"
    child.mkdir()
    program = (repository if outer_tool else root) / "bin/git.exe"
    program.parent.mkdir()
    program.write_bytes(b"target-controlled program; must never execute\n")
    monkeypatch.setattr(helper.shutil, "which", lambda _name: str(program))

    def unexpected(*_arguments, **_keywords):
        pytest.fail("a repository-controlled Git program was executed")

    monkeypatch.setattr(helper.subprocess, "Popen", unexpected)
    with pytest.raises(AiflowError) as error:
        if entry == "resolve":
            helper.resolve_initialization_root(child)
        elif entry == "observe":
            helper.observe_initialization_target(child)
        else:
            helper._run_git(child, ("rev-parse", "--show-toplevel"), deadline=monotonic() + 1)
    assert error.value.code == "INIT_GIT_UNAVAILABLE"


@pytest.mark.parametrize("kind", ["file-link", "directory-link", "junction"])
def test_git_program_aliases_are_rejected_before_process_creation(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    real = tmp_path / "real-tools"
    real.mkdir()
    (real / "git.exe").write_bytes(b"synthetic external executable; never execute\n")
    alias = tmp_path / "tool-alias"
    if kind == "file-link":
        alias.mkdir()
        try:
            (alias / "git.exe").symlink_to(real / "git.exe")
        except OSError as error:
            pytest.skip(f"file symlinks unavailable: {error}")
    elif kind == "directory-link":
        try:
            alias.symlink_to(real, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"directory symlinks unavailable: {error}")
    else:
        if sys.platform != "win32":
            pytest.skip("junction creation is Windows-specific")
        subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(alias), str(real)],
            capture_output=True,
            check=True,
            timeout=15,
        )
    monkeypatch.setattr(helper.shutil, "which", lambda _name: str(alias / "git.exe"))

    def unexpected(*_arguments, **_keywords):
        pytest.fail("Git was spawned through an unverified program alias")

    monkeypatch.setattr(helper.subprocess, "Popen", unexpected)
    with pytest.raises(AiflowError) as error:
        helper.resolve_initialization_root(repository)
    assert error.value.code == "INIT_GIT_UNAVAILABLE"
