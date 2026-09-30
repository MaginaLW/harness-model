"""Real initial Git repositories, independent copies, and conservative fallback."""

from __future__ import annotations

import importlib
import os
import shutil
import stat
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.integration import repository_fixture as fixture
from tests.integration import test_begin_close_commands as helpers


@pytest.fixture
def owner(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Iterator[fixture.RepositoryOwner]:
    # Do not overwrite or lose the integration session owner after this test.
    previous = fixture._owner
    token = fixture.RepositoryOwner(tmp_path_factory, tmp_path_factory.getbasetemp())
    monkeypatch.setattr(fixture, "_owner", token)
    try:
        yield token
    finally:
        fixture._owner = previous


def seed(tmp_path: Path, owner: fixture.RepositoryOwner) -> Path:
    repository = helpers.create_repository(tmp_path / "seed")
    assert not (repository / ".ai/tasks").exists()
    assert helpers.run_git(repository, "log", "-1", "--format=%s") == "initial"
    if owner.disabled and owner.reason in {
        fixture.IneligibleReason.GIT_LAYOUT,
        fixture.IneligibleReason.CONFIGURATION,
        fixture.IneligibleReason.ATTRIBUTES,
        fixture.IneligibleReason.TEMPLATE,
        fixture.IneligibleReason.GIT_ENVIRONMENT,
    }:
        pytest.skip(f"Warm copy is inapplicable: {owner.reason.value}")
    assert owner.snapshot is not None and owner.qualification is not None
    assert not owner.disabled and owner.cold == 1 and owner.hits == 0
    assert not (owner.snapshot / ".ai/tasks").exists()
    assert repository != owner.snapshot
    return repository


def source_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project = tmp_path / "src"
    (project / ".ai").mkdir(parents=True)
    for name in ("schemas", "policy", "templates"):
        shutil.copytree(helpers.PROJECT_ROOT / ".ai" / name, project / ".ai" / name)
    monkeypatch.setattr(helpers, "PROJECT_ROOT", project)
    return project


def snapshot(path: Path) -> str:
    return fixture._digest(fixture._path_fact(path))


def test_real_copy_isolation(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    original = seed(tmp_path, owner)
    assert owner.snapshot is not None
    pristine = snapshot(owner.snapshot)
    first = helpers.create_repository(tmp_path / "a")
    second = helpers.create_repository(tmp_path / "b")
    assert owner.hits == 2 and owner.cold == 1
    assert snapshot(first) == pristine == snapshot(second) == snapshot(original)
    for relative in (path.relative_to(first) for path in first.rglob("*") if path.is_file()):
        files = [root / relative for root in (first, second, owner.snapshot)]
        identities = {(path.stat().st_dev, path.stat().st_ino) for path in files}
        assert len(identities) == 3
        assert all(path.stat().st_nlink == 1 for path in files)
    first_index = (first / ".git/index").read_bytes()
    (first / "tracked.txt").write_text("left\n")
    (first / ".ai/policy/private.txt").write_text("left policy\n")
    helpers.commit_all(first, "left")
    helpers.run_git(first, "branch", "left")
    assert (first / ".git/index").read_bytes() != first_index
    assert snapshot(second) == pristine == snapshot(owner.snapshot) == snapshot(original)
    first_after = snapshot(first)
    (second / "tracked.txt").write_text("right\n")
    helpers.commit_all(second, "right")
    assert snapshot(first) == first_after
    assert snapshot(owner.snapshot) == pristine == snapshot(original)
    assert helpers.run_git(first, "rev-parse", "HEAD") != helpers.run_git(
        second, "rev-parse", "HEAD"
    )
    object_file = next(path for path in (first / ".git/objects").rglob("*") if path.is_file())
    object_file.chmod(stat.S_IWRITE | stat.S_IREAD)
    object_file.unlink()
    assert snapshot(owner.snapshot) == pristine
    assert not (first / ".git/objects/info/alternates").exists()


def test_aliases_share_owner(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    seed(tmp_path, owner)
    alias = importlib.import_module("test_begin_close_commands")
    alias.create_repository(tmp_path / "other")
    assert owner.hits == 1 and fixture._owner is owner


def test_case_label_only(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "synthetic next case (call)")
    result = helpers.create_repository(tmp_path / "next")
    assert owner.hits == 1
    assert os.environ["PYTEST_CURRENT_TEST"] == "synthetic next case (call)"
    assert helpers.run_git(result, "branch", "--show-current") == "main"


def test_returned_target_is_not_baseline(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    original = seed(tmp_path, owner)
    assert owner.snapshot is not None
    pristine = snapshot(owner.snapshot)
    helpers.run_git(original, "config", "core.hooksPath", "unused")
    (original / "tracked.txt").write_text("returned target changed\n")
    helpers.create_repository(tmp_path / "next")
    assert owner.hits == 1 and snapshot(owner.snapshot) == pristine


def test_no_owner_is_cold(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fixture, "_owner", None)
    result = helpers.create_repository(tmp_path / "cold")
    assert owner.snapshot is None and owner.hits == 0
    assert helpers.run_git(result, "branch", "--show-current") == "main"


def test_nested_owner_restores(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    with monkeypatch.context() as scoped:
        nested = fixture.RepositoryOwner(owner.factory, owner.basetemp)
        scoped.setattr(fixture, "_owner", nested)
        helpers.create_repository(tmp_path / "nested")
        assert nested.snapshot is not None and nested.snapshot != owner.snapshot
        fixture.unregister_owner(owner)
        assert fixture._owner is nested
    assert fixture._owner is owner
    helpers.create_repository(tmp_path / "again")
    assert owner.hits == 1


def test_other_exec_is_cold(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    owner.basetemp = tmp_path / "other-exec"
    owner.basetemp.mkdir()
    result = helpers.create_repository(tmp_path / "cold")
    assert owner.snapshot is None and owner.hits == 0
    assert helpers.run_git(result, "branch", "--show-current") == "main"


def test_intermediate_link_is_cold(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    seed(tmp_path, owner)
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "link"
    if os.name == "nt":
        command = Path(os.environ["SystemRoot"]) / "System32/cmd.exe"
        subprocess.run(
            [str(command), "/c", "mklink", "/J", str(link), str(actual)],
            capture_output=True,
            check=True,
            timeout=10,
        )
    else:
        link.symlink_to(actual, target_is_directory=True)
    result = helpers.create_repository(link / "cold")
    assert owner.hits == 0 and result.is_dir()
    assert helpers.run_git(actual / "cold", "branch", "--show-current") == "main"


@pytest.mark.parametrize(
    "failure", ["mkdir_exists", "mkdir_parent", "init", "add", "commit", "copy"]
)
def test_original_failure(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    target = tmp_path / "target"
    if failure == "mkdir_exists":
        target.mkdir()
        with pytest.raises(FileExistsError):
            helpers.create_repository(target)
    elif failure == "mkdir_parent":
        with pytest.raises(FileNotFoundError):
            helpers.create_repository(target / "child")
        assert not target.exists()
    else:
        original = helpers.run_git
        error = OSError("synthetic builder error")

        def fail_git(path: Path, *arguments: str) -> str:
            if failure in arguments:
                raise error
            return original(path, *arguments)

        def fail_copy(*_args: object, **_kwargs: object) -> None:
            raise error

        if failure == "copy":
            monkeypatch.setattr(shutil, "copytree", fail_copy)
        else:
            monkeypatch.setattr(helpers, "run_git", fail_git)
        with pytest.raises(OSError) as caught:
            helpers.create_repository(target)
        assert caught.value is error and target.is_dir()
        assert (target / ".git").exists() == (failure != "init")
    assert owner.snapshot is None and owner.hits == 0


def test_publish_failure_keeps_success(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = OSError("synthetic publication error")

    def fail(source: Path, target: Path) -> Path:
        (target / "partial").write_text("kept")
        raise error

    monkeypatch.setattr(fixture, "_copy_snapshot", fail)
    result = helpers.create_repository(tmp_path / "first")
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"
    assert owner.disabled and owner.snapshot is None
    helpers.create_repository(tmp_path / "second")
    assert owner.hits == 0


def test_warm_failure_never_retries(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    error = OSError("synthetic warm copy error")

    def fail(source: Path, target: Path) -> Path:
        assert source == owner.snapshot
        (target / "partial").write_text("kept")
        raise error

    monkeypatch.setattr(fixture, "_copy_snapshot", fail)
    target = tmp_path / "warm"
    with pytest.raises(OSError) as caught:
        helpers.create_repository(target)
    assert caught.value is error
    assert sorted(path.name for path in target.iterdir()) == ["partial"]
    assert owner.hits == 1 and owner.cold == 1


@pytest.mark.parametrize("change", ["edit", "same_time", "add", "delete", "missing"])
def test_current_source_change(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    project = source_copy(tmp_path, monkeypatch)
    seed(tmp_path, owner)
    assert owner.snapshot is not None
    pristine = snapshot(owner.snapshot)
    source = project / ".ai/policy/routing.yaml"
    if change in {"edit", "same_time"}:
        before = source.stat()
        contents = source.read_bytes()
        replacement = contents.replace(b"version", b"versioN", 1)
        assert replacement != contents and len(replacement) == len(contents)
        source.write_bytes(replacement)
        if change == "same_time":
            os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    elif change == "add":
        source = project / ".ai/policy/new.txt"
        source.write_text("new bytes")
    elif change == "delete":
        source.unlink()
    else:
        shutil.rmtree(project / ".ai/templates")
    target = tmp_path / "next"
    if change == "missing":
        with pytest.raises(FileNotFoundError):
            helpers.create_repository(target)
        assert target.is_dir() and (target / ".git").exists()
    else:
        helpers.create_repository(target)
        expected = target / ".ai" / source.relative_to(project / ".ai")
        assert expected.exists() == source.exists()
        if source.exists():
            assert expected.read_bytes() == source.read_bytes()
    assert owner.hits == 0 and snapshot(owner.snapshot) == pristine


@pytest.mark.parametrize("error_type", [PermissionError, RuntimeError, RecursionError])
def test_source_read_failure_is_cold(
    tmp_path: Path,
    owner: fixture.RepositoryOwner,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    seed(tmp_path, owner)
    original = fixture._source_fact

    def unreadable(_path: Path) -> str:
        raise error_type("synthetic secret not readable")

    monkeypatch.setattr(fixture, "_source_fact", unreadable)
    result = helpers.create_repository(tmp_path / "cold")
    assert result.is_dir() and owner.hits == 0
    monkeypatch.setattr(fixture, "_source_fact", original)


@pytest.mark.parametrize("variable", ["GIT_CONFIG_COUNT", "HOME", "XDG_CONFIG_HOME"])
def test_current_environment_change(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    seed(tmp_path, owner)
    value = "0" if variable.startswith("GIT_") else str(tmp_path / "empty-profile")
    monkeypatch.setenv(variable, value)
    helpers.create_repository(tmp_path / "cold")
    assert owner.hits == 0


def test_helper_monkeypatch_is_cold(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    original = helpers.run_git
    calls = []

    def observed(path: Path, *arguments: str) -> str:
        calls.append(arguments)
        return original(path, *arguments)

    monkeypatch.setattr(helpers, "run_git", observed)
    helpers.create_repository(tmp_path / "cold")
    assert owner.hits == 0 and calls[0] == ("init", "-b", "main")


def test_popen_monkeypatch_is_cold(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    original = subprocess.Popen
    calls = []

    def observed(*arguments: object, **keywords: object) -> subprocess.Popen[str]:
        calls.append(arguments[0])
        return original(*arguments, **keywords)

    monkeypatch.setattr(subprocess, "Popen", observed)
    helpers.create_repository(tmp_path / "cold")
    assert owner.hits == 0 and calls[0] == ["git", "init", "-b", "main"]


def test_git_locator_change_is_cold(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    current = shutil.which
    monkeypatch.setattr(shutil, "which", lambda command: str(tmp_path / "other-git"))
    # A changed locator invalidates qualification before any optional Git query;
    # the actual unmodified command runner still executes the original builder.
    helpers.create_repository(tmp_path / "cold")
    assert owner.hits == 0
    monkeypatch.setattr(shutil, "which", current)


def test_git_var_no_path_and_errors() -> None:
    def no_path(_repository: Path, *_arguments: str) -> str:
        raise subprocess.CalledProcessError(1, "git", output="", stderr="")

    assert fixture._var_paths(no_path, Path("."), "GIT_CONFIG_GLOBAL") == ()

    def failure(_repository: Path, *_arguments: str) -> str:
        raise subprocess.CalledProcessError(1, "git", output="", stderr="synthetic-secret")

    with pytest.raises(subprocess.CalledProcessError):
        fixture._var_paths(failure, Path("."), "GIT_CONFIG_GLOBAL")


@pytest.mark.parametrize(
    "key", ["private.synthetic-secret", "core.hooksPath", "include.path", "filter.other.clean"]
)
def test_unknown_config_privacy(
    tmp_path: Path, owner: fixture.RepositoryOwner, capsys: pytest.CaptureFixture[str], key: str
) -> None:
    secret = "synthetic-secret-value"
    path = tmp_path / "target"
    path.mkdir()

    def populate(target: Path) -> Path:
        result = helpers._populate_repository(target)
        helpers.run_git(target, "config", key, secret)
        return result

    fixture.populate_or_copy(
        path,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=populate,
        run_git=helpers.run_git,
        standard_helpers=True,
    )
    assert owner.snapshot is None and owner.disabled
    output = capsys.readouterr()
    assert secret not in output.out + output.err and key not in output.out + output.err


@pytest.mark.parametrize("name", [".gitattributes", "info/attributes"])
def test_attributes_are_cold(tmp_path: Path, owner: fixture.RepositoryOwner, name: str) -> None:
    path = tmp_path / "target"
    path.mkdir()

    def populate(target: Path) -> Path:
        result = helpers._populate_repository(target)
        attribute = target / (".git" if name.startswith("info/") else ".ai") / name
        attribute.write_text("* -filter\n")
        return result

    fixture.populate_or_copy(
        path,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=populate,
        run_git=helpers.run_git,
        standard_helpers=True,
    )
    assert owner.snapshot is None and owner.disabled


def test_snapshot_corruption_is_cold(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    seed(tmp_path, owner)
    assert owner.snapshot is not None
    (owner.snapshot / "tracked.txt").write_text("private corruption\n")
    target = helpers.create_repository(tmp_path / "cold")
    assert owner.hits == 0 and (target / "tracked.txt").read_text() == "initial\n"


@pytest.mark.parametrize("kind", ["configuration", "template", "active_hook", "absence"])
def test_current_guard_change(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    seed(tmp_path, owner)
    assert owner.qualification is not None
    original = owner.qualification
    copied_template = tmp_path / "template"
    shutil.copytree(original.template, copied_template)
    config = tmp_path / "config"
    config.write_text("ordinary private configuration\n")
    absent = tmp_path / "attributes"
    # Controlled private guards retain the actual successful qualification; only
    # safe copied files are changed, never host/source Git configuration.
    replacement = fixture._Qualification((config,), (absent,), copied_template, original.git, "")
    bound = replacement.current(helpers.PROJECT_ROOT, helpers.REPOSITORY_ID)
    owner.qualification = fixture._Qualification(
        (config,), (absent,), copied_template, original.git, bound
    )
    if kind == "configuration":
        config.write_text("changed private configuration\n")
    elif kind == "template":
        (copied_template / "description").write_text("changed template\n")
    elif kind == "active_hook":
        (copied_template / "hooks/pre-commit").write_text("synthetic inactive test file\n")
    else:
        absent.write_text("* -filter\n")
    result = helpers.create_repository(tmp_path / "cold")
    assert owner.hits == 0 and helpers.run_git(result, "log", "-1", "--format=%s") == "initial"


@pytest.mark.parametrize("value", ["synthetic-secret-invalid", "!synthetic-secret-command"])
def test_invalid_core_value_is_cold(
    tmp_path: Path, owner: fixture.RepositoryOwner, capsys: pytest.CaptureFixture[str], value: str
) -> None:
    path = tmp_path / "target"
    path.mkdir()

    def populate(target: Path) -> Path:
        result = helpers._populate_repository(target)
        helpers.run_git(target, "config", "core.autocrlf", value)
        return result

    fixture.populate_or_copy(
        path,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=populate,
        run_git=helpers.run_git,
        standard_helpers=True,
    )
    assert owner.snapshot is None and owner.disabled
    captured = capsys.readouterr()
    assert value not in captured.out + captured.err


def test_optional_query_failure_is_private(
    tmp_path: Path, owner: fixture.RepositoryOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "target"
    path.mkdir()

    def failed_query(_path: Path, *_arguments: str) -> str:
        raise subprocess.CalledProcessError(2, "synthetic-secret", stderr="synthetic-secret")

    result = fixture.populate_or_copy(
        path,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=helpers._populate_repository,
        run_git=failed_query,
        standard_helpers=True,
    )
    assert result == path and owner.disabled and owner.snapshot is None
    output = capsys.readouterr()
    assert "synthetic-secret" not in output.out + output.err


@pytest.mark.parametrize("extra", ["hooks/pre-commit", "hooks/extra.sample", "info/extra"])
def test_extra_git_template_entry_is_cold(
    tmp_path: Path, owner: fixture.RepositoryOwner, extra: str
) -> None:
    path = tmp_path / "target"
    path.mkdir()

    def populate(target: Path) -> Path:
        result = helpers._populate_repository(target)
        (target / ".git" / extra).write_text("synthetic inactive test entry\n")
        return result

    result = fixture.populate_or_copy(
        path,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=populate,
        run_git=helpers.run_git,
        standard_helpers=True,
    )
    assert result == path and owner.snapshot is None and owner.disabled


def test_nonempty_attribute_proof_is_cold(
    tmp_path: Path, owner: fixture.RepositoryOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "target"
    path.mkdir()

    def observed(repository: Path, *arguments: str) -> str:
        if arguments[0] == "check-attr":
            return "synthetic-secret-attribute"
        return helpers.run_git(repository, *arguments)

    fixture.populate_or_copy(
        path,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=helpers._populate_repository,
        run_git=observed,
        standard_helpers=True,
    )
    assert owner.reason is fixture.IneligibleReason.ATTRIBUTES and owner.snapshot is None
    captured = capsys.readouterr()
    assert "synthetic-secret" not in captured.out + captured.err


def test_query_input_race_is_not_portable(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    path = tmp_path / "target"
    path.mkdir()

    def observed(repository: Path, *arguments: str) -> str:
        result = helpers.run_git(repository, *arguments)
        if arguments[0] == "check-attr":
            (repository / ".git/config").write_text(
                (repository / ".git/config").read_text() + "\n# same semantics different bytes\n"
            )
        return result

    result = fixture.populate_or_copy(
        path,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=helpers._populate_repository,
        run_git=observed,
        standard_helpers=True,
    )
    assert result == path and owner.snapshot is None and owner.disabled
    assert owner.reason is fixture.IneligibleReason.INPUT_CHANGED


def test_template_mismatch_is_not_portable(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    path = tmp_path / "target"
    path.mkdir()

    def populate(target: Path) -> Path:
        result = helpers._populate_repository(target)
        hook = next((target / ".git/hooks").glob("*.sample"))
        hook.write_text("changed normal template entry\n")
        return result

    fixture.populate_or_copy(
        path,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=populate,
        run_git=helpers.run_git,
        standard_helpers=True,
    )
    assert owner.reason is fixture.IneligibleReason.QUALIFICATION_FAILED
    assert owner.disabled and owner.snapshot is None


def test_target_mode_preserves_mkdir(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    seed(tmp_path, owner)
    target = tmp_path / "mode"
    target.mkdir()
    mode = stat.S_IMODE(target.stat().st_mode)
    target.chmod(stat.S_IREAD if os.name == "nt" else mode ^ stat.S_IROTH)
    changed = stat.S_IMODE(target.stat().st_mode)
    assert changed != mode
    result = fixture.populate_or_copy(
        target,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=helpers._populate_repository,
        run_git=helpers.run_git,
        standard_helpers=True,
    )
    assert result == target and owner.hits == 0
    assert stat.S_IMODE(target.stat().st_mode) == changed


def test_replaced_base_has_new_owner(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "base"
    base.mkdir()

    class PrivateFactory:
        def getbasetemp(self) -> Path:
            return base

        def mktemp(self, prefix: str) -> Path:
            path = base / prefix
            path.mkdir()
            return path

    token = fixture.RepositoryOwner(PrivateFactory(), base)
    monkeypatch.setattr(fixture, "_owner", token)
    helpers.create_repository(base / "first")
    assert token.snapshot is not None
    pristine = snapshot(token.snapshot)
    previous = tmp_path / "old"
    base.rename(previous)
    base.mkdir()
    helpers.create_repository(base / "second")
    assert token.hits == 0 and not token.contains(base / "second")
    assert snapshot(previous / "b") == pristine


def _synthetic_windows_git_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    from types import SimpleNamespace

    prefix = tmp_path / "portable"
    wrapper = prefix / "cmd/git.exe"
    core = prefix / "mingw64/bin/git.exe"
    template = prefix / "mingw64/share/git-core/templates"
    wrapper.parent.mkdir(parents=True)
    core.parent.mkdir(parents=True)
    template.mkdir(parents=True)
    wrapper.write_bytes(b"synthetic wrapper bytes")
    core.write_bytes(b"synthetic core bytes")
    # Only the fixture module sees this facade. pathlib and global os.name
    # retain the actual host platform; no synthetic executable is launched.
    monkeypatch.setattr(fixture, "os", SimpleNamespace(name="nt"))
    return wrapper, core, template


@pytest.mark.parametrize("endpoint", ["cmd", "core"])
def test_windows_git_pair_layout_and_live_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    from types import SimpleNamespace

    wrapper, core, template = _synthetic_windows_git_pair(tmp_path, monkeypatch)
    selected = wrapper if endpoint == "cmd" else core
    assert fixture._template_for(wrapper) == template == fixture._template_for(core)
    initial = fixture._git_fact(selected)
    assert {Path(path) for path, _ in initial} == {wrapper, core}
    wrapper.write_bytes(b"changed wrapper bytes")
    wrapper_changed = fixture._git_fact(selected)
    assert wrapper_changed != initial
    core.write_bytes(b"changed core bytes")
    both_changed = fixture._git_fact(selected)
    assert both_changed != wrapper_changed

    # Exercise both live mode facts without changing process umask or relying
    # on Windows chmod to expose POSIX permission bits. This is a pure fact
    # seam, not a qualified warm copy or an alteration of global OS semantics.
    original_lstat = Path.lstat
    for changed_path in (wrapper, core):

        def changed_mode(path: Path, *, mode_path: Path = changed_path) -> object:
            metadata = original_lstat(path)
            if path == mode_path:
                return SimpleNamespace(
                    st_mode=metadata.st_mode ^ stat.S_IWUSR,
                    st_file_attributes=getattr(metadata, "st_file_attributes", 0),
                )
            return metadata

        with monkeypatch.context() as scoped:
            scoped.setattr(Path, "lstat", changed_mode)
            assert fixture._git_fact(selected) != both_changed


@pytest.mark.parametrize("layout", ["wrong-basename", "ucrt64", "generic-bin"])
def test_windows_git_pair_unknown_layout_is_ineligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str
) -> None:
    wrapper, _, _ = _synthetic_windows_git_pair(tmp_path, monkeypatch)
    prefix = wrapper.parent.parent
    relative = {
        "wrong-basename": "mingw64/bin/not-git.exe",
        "ucrt64": "ucrt64/bin/git.exe",
        "generic-bin": "bin/git.exe",
    }[layout]
    selected = prefix / relative
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(b"synthetic unsupported executable")
    for operation in (fixture._template_for, fixture._git_fact):
        with pytest.raises(fixture._Ineligible) as rejected:
            operation(selected)
        assert rejected.value.reason == fixture.IneligibleReason.GIT_LAYOUT


@pytest.mark.parametrize("endpoint", ["cmd", "core"])
def test_windows_git_pair_missing_counterpart_is_ineligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    wrapper, core, _ = _synthetic_windows_git_pair(tmp_path, monkeypatch)
    selected, counterpart = (wrapper, core) if endpoint == "cmd" else (core, wrapper)
    counterpart.unlink()
    # Preserve the existing missing ordinary file failure; optional
    # qualification, rather than this fact reader, owns cold fallback.
    with pytest.raises(FileNotFoundError):
        fixture._git_fact(selected)


def test_windows_git_pair_missing_template_is_ineligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, core, template = _synthetic_windows_git_pair(tmp_path, monkeypatch)
    template.rmdir()
    with pytest.raises(fixture._Ineligible) as rejected:
        fixture._template_for(core)
    assert rejected.value.reason == fixture.IneligibleReason.GIT_LAYOUT


@pytest.mark.parametrize("unsafe_part", ["wrapper", "core-parent", "template"])
def test_windows_git_pair_reparse_metadata_is_ineligible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsafe_part: str
) -> None:
    from types import SimpleNamespace

    wrapper, core, template = _synthetic_windows_git_pair(tmp_path, monkeypatch)
    unsafe = {"wrapper": wrapper, "core-parent": core.parent, "template": template}[unsafe_part]
    original_lstat = Path.lstat

    def reparse_lstat(path: Path) -> object:
        metadata = original_lstat(path)
        if path == unsafe:
            return SimpleNamespace(
                st_mode=metadata.st_mode,
                st_file_attributes=getattr(metadata, "st_file_attributes", 0) | 0x400,
            )
        return metadata

    # Reach the real ordinary/reparse guard using one metadata seam. This
    # proves the Windows flag branch, not an actual junction or full owner
    # qualification; _standard_io correctly disallows warm copies under it.
    monkeypatch.setattr(Path, "lstat", reparse_lstat)
    with pytest.raises(fixture._Ineligible):
        if unsafe_part == "template":
            fixture._template_for(core)
        else:
            fixture._git_fact(core)


@pytest.mark.skipif(os.name != "nt", reason="Windows full mingw64 endpoint qualification")
def test_real_mingw64_endpoint_qualifies_and_warms(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    locator = shutil.which("git")
    assert locator is not None
    actual = Path(locator).absolute()
    if actual.name.lower() == "git.exe" and actual.parent.name.lower() == "cmd":
        prefix = actual.parent.parent
    elif (
        actual.name.lower() == "git.exe"
        and actual.parent.name.lower() == "bin"
        and actual.parent.parent.name.lower() == "mingw64"
    ):
        prefix = actual.parents[2]
    else:
        # The existing seed proves original-builder success and task-free
        # initialization before its five explicit portable reason skips.
        seed(tmp_path, owner)
        pytest.fail("An unsupported Windows endpoint unexpectedly qualified")

    wrapper = prefix / "cmd/git.exe"
    core = prefix / "mingw64/bin/git.exe"
    assert wrapper.is_file() and core.is_file()
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", str(core.parent) + os.pathsep + original_path)
    assert Path(shutil.which("git") or "").absolute() == core
    original = helpers.create_repository(tmp_path / "seed")
    assert not (original / ".ai/tasks").exists()
    assert helpers.run_git(original, "log", "-1", "--format=%s") == "initial"
    assert not owner.disabled and owner.cold == 1 and owner.hits == 0
    assert owner.snapshot is not None and owner.qualification is not None
    qualification = owner.qualification
    assert qualification.git == core
    assert qualification.template == prefix / "mingw64/share/git-core/templates"
    assert {Path(path) for path, _ in fixture._git_fact(core)} == {wrapper, core}

    # The actual direct Git reports system attributes; no config/attributes
    # check or inactive proof is replaced. Present ordinary standard files
    # must remain in the live file binding and absent ones in absence facts.
    for attribute in fixture._var_paths(helpers.run_git, original, "GIT_ATTR_SYSTEM"):
        assert attribute.absolute() in {
            prefix / "etc/gitattributes",
            prefix / "mingw64/etc/gitattributes",
        }
        if attribute.exists():
            assert attribute in qualification.files
        else:
            assert attribute in qualification.attributes

    pristine = snapshot(owner.snapshot)
    copied = helpers.create_repository(tmp_path / "direct-copy")
    assert owner.hits == 1 and owner.cold == 1 and not owner.disabled
    assert not (copied / ".ai/tasks").exists()
    assert snapshot(copied) == pristine == snapshot(original)
    assert snapshot(owner.snapshot) == pristine
    for path in (path for path in copied.rglob("*") if path.is_file()):
        relative = path.relative_to(copied)
        entities = [path, owner.snapshot / relative, original / relative]
        identities = {(entity.stat().st_dev, entity.stat().st_ino) for entity in entities}
        assert len(identities) == 3
        assert all(entity.stat().st_nlink == 1 for entity in entities)
    assert not (copied / ".git/objects/info/alternates").exists()
