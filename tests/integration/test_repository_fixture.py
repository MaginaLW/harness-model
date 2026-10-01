"""Real initial Git repositories, independent copies, and conservative fallback."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import stat
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.integration import repository_fixture as fixture
from tests.integration import test_begin_close_commands as helpers

_QUALIFICATION_DIAGNOSTIC_CODES = (
    (fixture._qualify.__code__, "_qualify"),
    (fixture._template_reference.__code__, "_template_reference"),
    (fixture._template_fact.__code__, "_template_fact"),
    (fixture._ordinary.__code__, "_ordinary"),
    (fixture._path_fact.__code__, "_path_fact"),
    (fixture._parse_config.__code__, "_parse_config"),
    (fixture._var_paths.__code__, "_var_paths"),
    (fixture._Qualification.current.__code__, "_Qualification.current"),
)


def _qualification_diagnostic(repository: Path, owner: fixture.RepositoryOwner) -> str:
    """Report fixed trusted sites, never exception text, locals, paths or values."""
    try:
        fixture._qualify(
            repository,
            helpers.PROJECT_ROOT,
            helpers.REPOSITORY_ID,
            helpers.run_git,
            owner=owner,
        )
    except Exception as error:
        known_types = (
            (fixture._Ineligible, "_Ineligible"),
            (subprocess.CalledProcessError, "CalledProcessError"),
            (subprocess.TimeoutExpired, "TimeoutExpired"),
            (FileNotFoundError, "FileNotFoundError"),
            (PermissionError, "PermissionError"),
            (OSError, "OSError"),
            (RuntimeError, "RuntimeError"),
            (ValueError, "ValueError"),
            (TypeError, "TypeError"),
        )
        label = next((name for kind, name in known_types if type(error) is kind), None)
        sites = []
        if label is not None:
            traceback = BaseException.__getattribute__(error, "__traceback__")
            while traceback is not None:
                for code, name in _QUALIFICATION_DIAGNOSTIC_CODES:
                    if traceback.tb_frame.f_code is code:
                        sites.append({"function": name, "line": traceback.tb_lineno})
                traceback = traceback.tb_next
        return json.dumps({"type": label or "OTHER_EXCEPTION", "sites": sites}, sort_keys=True)
    return "DIRECT_RECHECK_PASSED"


@pytest.fixture
def _private_git_environment(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Use owned profile/system inputs; keep unknown-input guards and parent restoration."""
    home = tmp_path_factory.mktemp("git-home")
    xdg = home / "xdg"
    xdg.mkdir()
    monkeypatch.setitem(os.environ, "HOME", str(home))
    monkeypatch.setitem(os.environ, "XDG_CONFIG_HOME", str(xdg))
    for name in tuple(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delitem(os.environ, name)
    # Mapping-only seams have no owner proof and therefore install no context.
    if type(tmp_path_factory) is pytest.TempPathFactory:
        scope = fixture.RepositoryOwner(tmp_path_factory, tmp_path_factory.getbasetemp())
        directory = tmp_path_factory.mktemp("git-system")
        system = directory / "config"
        system.write_bytes(b"")
        context = fixture._PrivateGitContext.create(scope, system)
        monkeypatch.setattr(fixture, "_private_git_context", context)
    return home


@pytest.fixture
def owner(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    _private_git_environment: Path,
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
    if owner.disabled and owner.reason is fixture.IneligibleReason.QUALIFICATION_FAILED:
        diagnostic = _qualification_diagnostic(repository, owner)
        pytest.fail(f"Unexpected warm qualification failure: {diagnostic}", pytrace=False)
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


def _parallel_tree(tmp_path: Path, count: int = 3) -> tuple[Path, Path]:
    source, target = tmp_path / "s", tmp_path / "d"
    source.mkdir()
    target.mkdir()
    for number in range(count):
        (source / f"f{number:03}").write_bytes(f"original {number}\n".encode())
    return source, target


def _parallel_pool_factory(pools: list[object]) -> object:
    from concurrent.futures import ThreadPoolExecutor

    def create(**options: object) -> ThreadPoolExecutor:
        pool = fixture._OwnedCopyExecutor(**options)
        pools.append(pool)
        return pool

    return create


def _assert_parallel_pools_ended(pools: list[object]) -> None:
    assert len(pools) == 1
    assert pools[0]._max_workers == 4
    assert all(not thread.is_alive() for thread in pools[0]._threads)
    for record in pools[0].owned_workers:
        assert record.terminal and not record.terminal_unknown
        if record.start_attempted and not record.not_started:
            assert record.worker_done.is_set()
            assert not record.thread.is_alive()


def _parallel_metadata(root: Path) -> dict[Path, tuple[int, int, bytes | None]]:
    return {
        path.relative_to(root): (
            stat.S_IMODE(path.stat().st_mode),
            path.stat().st_mtime_ns,
            path.read_bytes() if path.is_file() else None,
        )
        for path in (root, *root.rglob("*"))
    }


def test_parallel_owner_warm_and_first_publication_serial(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected: list[tuple[Path, Path]] = []
    original_parallel = fixture._parallel_copy_snapshot

    def observe(source: Path, target: Path) -> None:
        assert owner.snapshot == source
        selected.append((source, target))
        original_parallel(source, target)

    monkeypatch.setattr(fixture, "_parallel_copy_snapshot", observe)
    original = seed(tmp_path, owner)
    assert selected == []
    assert owner.snapshot is not None
    pristine = snapshot(owner.snapshot)
    result = helpers.create_repository(tmp_path / "warm")
    assert selected == [(owner.snapshot, result)]
    assert owner.cold == 1 and owner.hits == 1 and not owner.disabled
    assert snapshot(original) == pristine == snapshot(owner.snapshot) == snapshot(result)
    for path in result.rglob("*"):
        if path.is_file():
            counterpart = owner.snapshot / path.relative_to(result)
            assert (path.stat().st_dev, path.stat().st_ino) != (
                counterpart.stat().st_dev,
                counterpart.stat().st_ino,
            )
            assert path.stat().st_nlink == 1


def test_parallel_readonly_nested_metadata_and_real_direntry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = _parallel_tree(tmp_path, 1)
    child = source / "child"
    child.mkdir()
    (child / "payload").write_bytes(b"nested payload")
    timestamp = 1_650_000_000_123_456_700
    for path in (source, *source.rglob("*")):
        os.utime(path, ns=(timestamp, timestamp))
    child.chmod(stat.S_IREAD if os.name == "nt" else 0o555)
    expected = _parallel_metadata(source)
    copied: list[str] = []
    metadata_order: list[str] = []
    original_copy2, original_copystat = shutil.copy2, shutil.copystat

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        assert isinstance(entry, os.DirEntry)
        result = original_copy2(entry, destination)
        copied.append(entry.name)
        return result

    def copy_stat(src: object, dst: object, **options: object) -> None:
        if Path(os.fspath(src)).is_dir():
            if Path(os.fspath(src)) == child:
                assert "payload" in copied
            if Path(os.fspath(src)) == source:
                assert metadata_order == ["child"]
            metadata_order.append(Path(os.fspath(src)).name)
        original_copystat(src, dst, **options)

    pools: list[object] = []
    monkeypatch.setattr(fixture.shutil, "copystat", copy_stat)
    try:
        fixture._parallel_copy_snapshot(
            source, target, copy_file=copy_file, executor_factory=_parallel_pool_factory(pools)
        )
        assert _parallel_metadata(target) == expected == _parallel_metadata(source)
        assert sorted(copied) == ["f000", "payload"]
        _assert_parallel_pools_ended(pools)
    finally:
        for path in (child, target / "child"):
            if path.exists():
                path.chmod(stat.S_IREAD | stat.S_IWRITE if os.name == "nt" else 0o755)


def test_parallel_custom_bindings_select_original_serial_before_write(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    seed(tmp_path, owner)
    assert owner.snapshot is not None

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Parallel must not be selected")

    bindings = [
        (fixture.shutil, "copy2"),
        (fixture.shutil, "copystat"),
        (fixture.os, "scandir"),
        (fixture.os, "makedirs"),
        (fixture.sys, "audit"),
        (fixture, "ThreadPoolExecutor"),
        (ThreadPoolExecutor, "submit"),
        (ThreadPoolExecutor, "shutdown"),
        (threading.Thread, "start"),
        (threading.Thread, "join"),
    ]
    for number, (container, name) in enumerate(bindings):
        actual = getattr(container, name)

        def delegated(*args: object, original: object = actual, **kwargs: object) -> object:
            return original(*args, **kwargs)

        target = tmp_path / f"c{number}"
        target.mkdir()
        with monkeypatch.context() as scoped:
            scoped.setattr(container, name, delegated)
            scoped.setattr(fixture, "_parallel_copy_snapshot", forbidden)
            assert not fixture._parallel_copy_eligible(owner.snapshot, target)
            assert fixture._copy_snapshot(owner.snapshot, target) == target
        assert snapshot(target) == snapshot(owner.snapshot)


def test_parallel_shape_limit_and_eligibility_failures_fall_back_before_write(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    assert owner.snapshot is not None
    source = owner.snapshot

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Parallel must not be selected")

    monkeypatch.setattr(fixture, "_parallel_copy_snapshot", forbidden)
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "extra").write_bytes(b"keep existing")
    assert not fixture._parallel_copy_eligible(source, occupied)
    fixture._copy_snapshot(source, occupied)
    assert (occupied / "extra").read_bytes() == b"keep existing"
    assert (occupied / "tracked.txt").read_bytes() == (source / "tracked.txt").read_bytes()

    # A private selection negative, not fabricated current warm qualification:
    # the original immutable-snapshot digest guard would reject these edits.
    extra_files = [source / f"extra{number:03}" for number in range(257)]
    try:
        for path in extra_files:
            path.write_bytes(b"over the parallel bound")
        oversized = tmp_path / "oversized"
        oversized.mkdir()
        assert not fixture._parallel_copy_eligible(source, oversized)
        fixture._copy_snapshot(source, oversized)
        assert (oversized / "extra256").read_bytes() == b"over the parallel bound"
    finally:
        for path in extra_files:
            path.unlink()

    def read_failure(path: Path) -> int:
        raise RuntimeError("synthetic eligibility read failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(fixture, "_parallel_tree_count", read_failure)
        target = tmp_path / "read-fallback"
        target.mkdir()
        assert fixture._copy_snapshot(source, target) == target
        assert snapshot(target) == snapshot(source)

    interruption = KeyboardInterrupt("synthetic eligibility interruption")

    def interrupted(path: Path) -> int:
        raise interruption

    target = tmp_path / "interrupted"
    target.mkdir()
    with monkeypatch.context() as scoped:
        scoped.setattr(fixture, "_parallel_tree_count", interrupted)
        with pytest.raises(KeyboardInterrupt) as raised:
            fixture._copy_snapshot(source, target)
    assert raised.value is interruption and list(target.iterdir()) == []


def test_parallel_four_workers_and_256_total_real_copies(tmp_path: Path) -> None:
    import threading

    source, target = _parallel_tree(tmp_path, 128)
    child = source / "child"
    child.mkdir()
    for number in range(128):
        (child / f"g{number:03}").write_bytes(b"child")
    # Establish exact directory times before copytree's DirEntry metadata is read.
    for directory, timestamp in (
        (source, 1_650_000_000_123_456_700),
        (child, 1_650_000_000_123_457_700),
    ):
        os.utime(directory, ns=(timestamp, timestamp))
        assert directory.stat().st_mtime_ns == timestamp
    expected = _parallel_metadata(source)
    lock, four_running, release = threading.Lock(), threading.Event(), threading.Event()
    active = maximum = copies = 0
    observer_errors: list[str] = []

    def release_workers() -> None:
        if not four_running.wait(5):
            observer_errors.append("Four actual workers did not enter")
        release.set()

    observer = threading.Thread(target=release_workers, name="fixture-copy-release")
    observer.start()

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        nonlocal active, maximum, copies
        with lock:
            active += 1
            maximum = max(maximum, active)
            if active == 4:
                four_running.set()
        try:
            assert release.wait(5)
            result = shutil.copy2(entry, destination)
            with lock:
                copies += 1
            return result
        finally:
            with lock:
                active -= 1

    pools: list[object] = []
    try:
        fixture._parallel_copy_snapshot(
            source, target, copy_file=copy_file, executor_factory=_parallel_pool_factory(pools)
        )
    finally:
        release.set()
        observer.join(5)
    assert not observer.is_alive() and observer_errors == []
    assert maximum == 4 and active == 0 and copies == 256
    assert _parallel_metadata(source) == expected
    assert _parallel_metadata(source) == _parallel_metadata(target)
    _assert_parallel_pools_ended(pools)


def test_parallel_runtime_bound_fails_without_recopy_or_cleanup(tmp_path: Path) -> None:
    source, target = _parallel_tree(tmp_path, 257)
    pools: list[object] = []
    with pytest.raises(RuntimeError, match="^REPOSITORY_FIXTURE_COPY_LIMIT$"):
        fixture._parallel_copy_snapshot(
            source, target, executor_factory=_parallel_pool_factory(pools)
        )
    actual_files = list(target.iterdir())
    assert len(actual_files) == 256
    assert all(path.read_bytes() == (source / path.name).read_bytes() for path in actual_files)
    _assert_parallel_pools_ended(pools)


def test_parallel_mixed_os_and_shutil_errors_keep_dfs_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = _parallel_tree(tmp_path, 2)
    child = source / "child"
    child.mkdir()
    (child / "nested").write_bytes(b"nested")
    original_copystat = shutil.copystat
    expected: list[tuple[str, str, str]] = []

    def expected_directory(src: Path, dst: Path) -> None:
        with os.scandir(src) as iterator:
            entries = list(iterator)
        for entry in entries:
            left, right = str(src / entry.name), str(dst / entry.name)
            if entry.is_dir():
                expected_directory(Path(entry.path), Path(right))
            elif entry.name == "f001":
                expected.extend([(left, right, "first nested"), (left, right, "second nested")])
            else:
                expected.append((left, right, "synthetic file OS failure"))
        expected.append((str(src), str(dst), "synthetic directory OS failure"))

    expected_directory(source, target)

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        if entry.name == "f001":
            raise shutil.Error(
                [
                    (entry.path, destination, "first nested"),
                    (entry.path, destination, "second nested"),
                ]
            )
        raise OSError("synthetic file OS failure")

    def copy_stat(src: object, dst: object, **options: object) -> None:
        if Path(os.fspath(src)).is_dir():
            raise OSError("synthetic directory OS failure")
        original_copystat(src, dst, **options)

    pools: list[object] = []
    monkeypatch.setattr(fixture.shutil, "copystat", copy_stat)
    with pytest.raises(shutil.Error) as raised:
        fixture._parallel_copy_snapshot(
            source, target, copy_file=copy_file, executor_factory=_parallel_pool_factory(pools)
        )
    actual = raised.value.args[0]
    assert [
        (os.fspath(left), os.fspath(right), message) for left, right, message in actual
    ] == expected
    assert isinstance(actual[-1][0], Path) and actual[-1][0] == source
    child_metadata = next(item for item in actual if os.fspath(item[0]) == str(child))
    assert isinstance(child_metadata[0], os.DirEntry) and isinstance(child_metadata[1], str)
    _assert_parallel_pools_ended(pools)


@pytest.mark.parametrize("winerror", [None, 0, 5])
def test_parallel_directory_metadata_original_winerror_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winerror: int | None
) -> None:
    source, target = _parallel_tree(tmp_path, 1)
    original_copystat = shutil.copystat
    failure = OSError("synthetic directory metadata failure")
    if winerror is not None:
        failure.winerror = winerror

    def copy_stat(src: object, dst: object, **options: object) -> None:
        if os.fspath(src) == str(source):
            raise failure
        original_copystat(src, dst, **options)

    pools: list[object] = []
    monkeypatch.setattr(fixture.shutil, "copystat", copy_stat)
    if winerror is None:
        with pytest.raises(shutil.Error) as raised:
            fixture._parallel_copy_snapshot(
                source, target, executor_factory=_parallel_pool_factory(pools)
            )
        assert raised.value.args[0] == [(source, target, str(failure))]
    else:
        fixture._parallel_copy_snapshot(
            source, target, executor_factory=_parallel_pool_factory(pools)
        )
    assert (target / "f000").read_bytes() == (source / "f000").read_bytes()
    _assert_parallel_pools_ended(pools)


@pytest.mark.parametrize("base_exception", [False, True])
def test_parallel_reverse_completion_first_fatal_identity_and_actual_partial(
    tmp_path: Path, base_exception: bool
) -> None:
    import threading

    source, target = _parallel_tree(tmp_path, 2)
    with os.scandir(source) as iterator:
        order = [entry.name for entry in iterator]
    second_done = threading.Event()
    original = KeyboardInterrupt("first") if base_exception else RuntimeError("first")
    later = ValueError("later")
    completion: list[str] = []

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        if entry.name == order[0]:
            assert second_done.wait(5)
            completion.append(entry.name)
            raise original
        shutil.copy2(entry, destination)
        completion.append(entry.name)
        second_done.set()
        raise later

    pools: list[object] = []
    with pytest.raises(type(original)) as raised:
        fixture._parallel_copy_snapshot(
            source, target, copy_file=copy_file, executor_factory=_parallel_pool_factory(pools)
        )
    assert raised.value is original and raised.value.args == original.args
    assert completion == [order[1], order[0]]
    assert not (target / order[0]).exists()
    assert (target / order[1]).read_bytes() == (source / order[1]).read_bytes()
    _assert_parallel_pools_ended(pools)


def test_parallel_malformed_shutil_error_expansion_is_logical_abort(tmp_path: Path) -> None:
    source, target = _parallel_tree(tmp_path, 2)
    with os.scandir(source) as iterator:
        order = [entry.name for entry in iterator]
    later = RuntimeError("later worker")

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        if entry.name == order[0]:
            raise shutil.Error(None)
        shutil.copy2(entry, destination)
        raise later

    pools: list[object] = []
    with pytest.raises(TypeError) as raised:
        fixture._parallel_copy_snapshot(
            source, target, copy_file=copy_file, executor_factory=_parallel_pool_factory(pools)
        )
    assert raised.value is not later
    assert (target / order[1]).read_bytes() == (source / order[1]).read_bytes()
    _assert_parallel_pools_ended(pools)


@pytest.mark.parametrize("stage", ["submit", "classification"])
@pytest.mark.parametrize("earlier_fatal", [False, True])
def test_parallel_later_coordinator_error_drains_prior_job_and_preserves_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str, earlier_fatal: bool
) -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    source, target = _parallel_tree(tmp_path, 2)
    with os.scandir(source) as iterator:
        order = [entry.name for entry in iterator]
    first_running, fault_seen, release = threading.Event(), threading.Event(), threading.Event()
    first_error, coordinator_error = RuntimeError("earlier worker"), ValueError("later coordinator")
    observer_errors: list[str] = []

    def release_worker() -> None:
        if not fault_seen.wait(5):
            observer_errors.append("Coordinator fault was not reached")
        release.set()

    observer = threading.Thread(target=release_worker, name="fixture-copy-release")
    observer.start()

    def fail_coordinator() -> None:
        assert first_running.wait(5)
        assert not release.is_set()
        fault_seen.set()
        raise coordinator_error

    class SubmissionFault(fixture._OwnedCopyExecutor):
        submissions = 0

        def submit(self, *args: object, **kwargs: object) -> object:
            self.submissions += 1
            if self.submissions == 2 and stage == "submit":
                fail_coordinator()
            return super().submit(*args, **kwargs)

    original_metadata = fixture._parallel_entry_metadata

    def classify(entry: os.DirEntry[str]) -> os.stat_result:
        if stage == "classification" and entry.name == order[1]:
            fail_coordinator()
        return original_metadata(entry)

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        assert entry.name == order[0]
        first_running.set()
        assert release.wait(5)
        if earlier_fatal:
            raise first_error
        return shutil.copy2(entry, destination)

    pools: list[object] = []

    def create(**options: object) -> ThreadPoolExecutor:
        pool = SubmissionFault(**options)
        pools.append(pool)
        return pool

    monkeypatch.setattr(fixture, "_parallel_entry_metadata", classify)
    expected = first_error if earlier_fatal else coordinator_error
    try:
        with pytest.raises(type(expected)) as raised:
            fixture._parallel_copy_snapshot(
                source, target, copy_file=copy_file, executor_factory=create
            )
        assert raised.value is expected
        assert not (target / order[1]).exists()
        assert (target / order[0]).exists() is not earlier_fatal
    finally:
        release.set()
        observer.join(5)
    assert observer_errors == [] and not observer.is_alive()
    _assert_parallel_pools_ended(pools)


@pytest.mark.parametrize("earlier_fatal", [False, True])
def test_parallel_real_submit_start_failure_joins_queued_and_running_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, earlier_fatal: bool
) -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    source, target = _parallel_tree(tmp_path, 3)
    with os.scandir(source) as iterator:
        order = [entry.name for entry in iterator]
    first_running, second_running = threading.Event(), threading.Event()
    start_failed, release = threading.Event(), threading.Event()
    first_error = KeyboardInterrupt("earlier actual worker")
    startup_error = KeyboardInterrupt("Thread.start failure after actual native startup")
    original_start, original_join = threading.Thread.start, threading.Thread.join
    attempts = 0
    returned = threading.Event()
    failures: list[BaseException] = []
    joined: list[threading.Thread] = []
    copy_attempts: list[str] = []
    lock = threading.Lock()

    def start(thread: threading.Thread) -> None:
        nonlocal attempts
        if thread.name.startswith("aiflow-copy"):
            attempts += 1
            if attempts == 2:
                assert first_running.wait(5)
                original_start(thread)
                assert second_running.wait(5)
                start_failed.set()
                raise startup_error
        original_start(thread)

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        with lock:
            copy_attempts.append(entry.name)
        if entry.name == order[0]:
            first_running.set()
            assert release.wait(5)
            if earlier_fatal:
                raise first_error
        elif entry.name == order[1]:
            second_running.set()
            assert release.wait(5)
        return shutil.copy2(entry, destination)

    pools: list[object] = []
    monkeypatch.setattr(threading.Thread, "start", start)

    def join(thread: threading.Thread, *args: object, **kwargs: object) -> None:
        original_join(thread, *args, **kwargs)
        if thread.name.startswith("aiflow-copy"):
            assert release.is_set()
            joined.append(thread)  # actual delegated join returned after release

    monkeypatch.setattr(threading.Thread, "join", join)

    def call() -> None:
        try:
            fixture._parallel_copy_snapshot(
                source, target, copy_file=copy_file, executor_factory=_parallel_pool_factory(pools)
            )
        except BaseException as error:
            failures.append(error)
        finally:
            returned.set()

    caller = threading.Thread(target=call, name="fixture-copy-caller")
    caller.start()
    expected = first_error if earlier_fatal else startup_error
    try:
        assert start_failed.wait(5) and second_running.is_set()
        assert len(pools[0].owned_workers) == 2
        assert pools[0].owned_workers[1].thread not in pools[0]._threads
        assert not returned.wait(0.02)  # second unregistered actual worker is still held
    finally:
        release.set()
        caller.join(5)
    assert not caller.is_alive() and returned.is_set()
    assert len(failures) == 1 and failures[0] is expected and failures[0].args == expected.args
    assert attempts == 2
    assert pools[0].owned_workers[1].startup_failure.error is startup_error
    assert not (target / order[2]).exists()
    assert (target / order[0]).exists() is not earlier_fatal
    assert (target / order[1]).read_bytes() == (source / order[1]).read_bytes()
    assert sorted(copy_attempts) == sorted(order[:2])
    assert set(joined) == {record.thread for record in pools[0].owned_workers}
    assert isinstance(pools[0], ThreadPoolExecutor)
    _assert_parallel_pools_ended(pools)


@pytest.mark.parametrize("observation", ["done", "exception"])
def test_parallel_wait_interruption_not_masked_by_observation_or_shutdown(
    tmp_path: Path, observation: str
) -> None:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    source, target = _parallel_tree(tmp_path, 1)
    release, observation_failed = threading.Event(), threading.Event()
    original = KeyboardInterrupt("first result interruption")
    later = KeyboardInterrupt("later observation interruption")
    shutdown_error = ValueError("later shutdown error")
    observer_errors: list[str] = []

    def release_worker() -> None:
        if not observation_failed.wait(5):
            observer_errors.append("Future observation fault was not reached")
        release.set()

    observer = threading.Thread(target=release_worker, name="fixture-copy-release")
    observer.start()

    class ObservationFault(fixture._OwnedCopyExecutor):
        def submit(self, *args: object, **kwargs: object) -> object:
            future = super().submit(*args, **kwargs)
            result, done, exception = future.result, future.done, future.exception
            injected_result = injected_observation = False

            def observe_result(*values: object, **options: object) -> object:
                nonlocal injected_result
                if not injected_result:
                    injected_result = True
                    if observation == "exception":
                        # Wait the real job so real done() reaches exception();
                        # the diagnostic does not fake completed state.
                        release.set()
                        result(*values, **options)
                    raise original
                return result(*values, **options)

            def observe_done() -> bool:
                nonlocal injected_observation
                if observation == "done" and not injected_observation:
                    injected_observation = True
                    observation_failed.set()
                    raise later
                return done()

            def observe_exception(*values: object, **options: object) -> object:
                nonlocal injected_observation
                if observation == "exception" and not injected_observation:
                    injected_observation = True
                    observation_failed.set()
                    raise later
                return exception(*values, **options)

            future.result, future.done, future.exception = (
                observe_result,
                observe_done,
                observe_exception,
            )
            return future

        def shutdown(self, *args: object, **kwargs: object) -> None:
            first = not getattr(self, "injected_shutdown", False)
            self.injected_shutdown = True
            super().shutdown(*args, **kwargs)
            if first:
                raise shutdown_error

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        assert release.wait(5)
        return shutil.copy2(entry, destination)

    pools: list[object] = []

    def create(**options: object) -> ThreadPoolExecutor:
        pool = ObservationFault(**options)
        pools.append(pool)
        return pool

    try:
        with pytest.raises(KeyboardInterrupt) as raised:
            fixture._parallel_copy_snapshot(
                source, target, copy_file=copy_file, executor_factory=create
            )
        assert raised.value is original and raised.value.args == original.args
        assert (target / "f000").read_bytes() == (source / "f000").read_bytes()
        assert observation_failed.is_set()
    finally:
        release.set()
        observer.join(5)
    assert observer_errors == [] and not observer.is_alive()
    _assert_parallel_pools_ended(pools)


@pytest.mark.parametrize("primary_failure", [False, True])
def test_parallel_final_drain_observation_preserves_failure_or_fails_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, primary_failure: bool
) -> None:
    source, target = _parallel_tree(tmp_path, 1)
    original, late = RuntimeError("original worker"), KeyboardInterrupt("final drain observation")
    actual_complete = fixture._parallel_complete_batch

    def complete(pending: object, errors: object) -> object:
        if not pending:
            raise late
        return actual_complete(pending, errors)

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        if primary_failure:
            raise original
        return shutil.copy2(entry, destination)

    pools: list[object] = []
    monkeypatch.setattr(fixture, "_parallel_complete_batch", complete)
    expected = original if primary_failure else late
    with pytest.raises(type(expected)) as raised:
        fixture._parallel_copy_snapshot(
            source, target, copy_file=copy_file, executor_factory=_parallel_pool_factory(pools)
        )
    assert raised.value is expected
    assert (target / "f000").exists() is not primary_failure
    _assert_parallel_pools_ended(pools)


@pytest.mark.parametrize("base_exception", [False, True])
def test_parallel_blocked_running_job_must_end_before_error_returns(
    tmp_path: Path, base_exception: bool
) -> None:
    import threading

    source, target = _parallel_tree(tmp_path, 2)
    with os.scandir(source) as iterator:
        order = [entry.name for entry in iterator]
    running, fault_seen, release, returned = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    original = KeyboardInterrupt("later worker") if base_exception else RuntimeError("later worker")
    actual_errors: list[BaseException] = []
    returned_after_release: list[bool] = []
    pools: list[object] = []

    def copy_file(entry: os.DirEntry[str], destination: str) -> object:
        if entry.name == order[0]:
            running.set()
            assert release.wait(5)
            return shutil.copy2(entry, destination)
        assert running.wait(5)
        fault_seen.set()
        raise original

    def invoke() -> None:
        try:
            fixture._parallel_copy_snapshot(
                source, target, copy_file=copy_file, executor_factory=_parallel_pool_factory(pools)
            )
        except BaseException as error:
            actual_errors.append(error)
        finally:
            returned_after_release.append(release.is_set())
            returned.set()

    caller = threading.Thread(target=invoke, name="fixture-copy-caller")
    caller.start()
    try:
        assert running.wait(5) and fault_seen.wait(5)
        assert not returned.wait(0.02)
    finally:
        release.set()
        caller.join(5)
    assert not caller.is_alive() and returned.is_set()
    assert actual_errors == [original] and actual_errors[0] is original
    assert returned_after_release == [True]
    assert (target / order[0]).read_bytes() == (source / order[0]).read_bytes()
    assert not (target / order[1]).exists()
    _assert_parallel_pools_ended(pools)


@pytest.mark.parametrize("fault", ["arbitrary", "custom-native", "custom-bootstrap"])
def test_parallel_start_failure_needs_exact_native_creation_proof(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import threading

    thread = threading.Thread(target=lambda: None)
    record = fixture._OwnedWorker(thread, threading.Event(), getattr(thread, "_handle", None))
    # No attempted call occurred. This narrow negative is independently known.
    assert fixture._owned_finish_worker(record) is None
    assert record.terminal and not record.worker_done.is_set()
    record.terminal = False
    record.start_attempted = True
    record.native_create_eligible = True
    error = RuntimeError("synthetic native-create failure")
    if fault == "arbitrary":
        assert not fixture._owned_native_creation_failed(record, error)
        return
    if fault == "custom-bootstrap":
        thread._bootstrap = None
    else:

        def failed_native(*args: object, **kwargs: object) -> None:
            raise error

        monkeypatch.setattr(fixture.threading, fixture._NATIVE_START_NAME, failed_native)
    # Exercise the real standard start's native CALL/except cleanup. A custom
    # native creator or bootstrap is deliberately not eligible negative proof;
    # no host resource exhaustion or real native-create failure is manufactured.
    with pytest.raises(Exception) as raised:
        fixture._THREAD_START(thread)
    assert not thread._started.is_set() and thread.ident is None
    with fixture._LIMBO_LOCK:
        assert thread not in threading._limbo
    assert not fixture._owned_native_creation_failed(record, raised.value)


def test_parallel_unknown_worker_protocol_selects_serial_before_write(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    assert owner.snapshot is not None
    original_worker = fixture.futures_thread._worker

    def worker(*args: object) -> None:
        original_worker(*args)

    monkeypatch.setattr(fixture.futures_thread, "_worker", worker)
    target = tmp_path / "unknown-worker"
    target.mkdir()
    assert not fixture._parallel_copy_eligible(owner.snapshot, target)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unknown worker must use the original serial copy")

    monkeypatch.setattr(fixture, "_parallel_copy_snapshot", forbidden)
    fixture._copy_snapshot(owner.snapshot, target)
    assert snapshot(target) == snapshot(owner.snapshot)


def _parallel_owned_child(tmp_path: Path, scenario: str) -> dict[str, object]:
    import ctypes
    import json
    import subprocess
    import sys
    import textwrap
    import time

    code = textwrap.dedent(
        """
        import json, pathlib, shutil, sys, threading, time
        sys.path.insert(0, sys.argv[1])
        import repository_fixture as fixture
        root, scenario = pathlib.Path(sys.argv[2]), sys.argv[3]
        source, target = root / 'child-source', root / 'child-target'
        source.mkdir(); target.mkdir(); (source / 'file').write_bytes(b'owned input')
        ready, request, result = root / 'ready.json', root / 'resolve', root / 'result.json'
        pools = []
        original_start, original_join = threading.Thread.start, threading.Thread.join
        native_version = tuple(sys.version_info[:2])
        original_error = KeyboardInterrupt('owned synthetic interruption')
        def factory(**options):
            pool = fixture._OwnedCopyExecutor(**options); pools.append(pool); return pool
        if scenario == 'resolve':
            actual_finish = fixture._owned_finish_worker
            def finish(record):
                if not record.thread._started.is_set():
                    ready.write_text(json.dumps({'stage': 'unknown-start',
                        'runtime': native_version,
                        'worker_done': record.worker_done.is_set()}), encoding='utf-8')
                return actual_finish(record)
            fixture._owned_finish_worker = finish
            def start(thread):
                if thread.name.startswith('aiflow-copy'):
                    raise original_error
                original_start(thread)
            def resolve():
                deadline = time.monotonic() + 5
                while not request.exists() and time.monotonic() < deadline:
                    time.sleep(.005)
                assert request.exists()
                record = pools[0].owned_workers[0]
                # Actual start of the same retained Thread; no fake Event/flags.
                original_start(record.thread)
            resolver = threading.Thread(target=resolve, name='owned-resolution')
            resolver.start()
            threading.Thread.start = start
            try:
                fixture._parallel_copy_snapshot(source, target, executor_factory=factory)
            except BaseException as error:
                assert error is original_error and error.args == original_error.args
            else:
                raise AssertionError('Startup failure must not become success')
            finally:
                original_join(resolver, 5)
            assert not resolver.is_alive()
            record = pools[0].owned_workers[0]
            assert record.terminal and not record.terminal_unknown and record.worker_done.is_set()
            assert record.thread not in pools[0]._threads and not record.thread.is_alive()
            assert list(target.iterdir()) == []  # truthful cancellation before actual start
            result.write_text(json.dumps({'stage': 'native-joined', 'same_error': True,
                'actual_version': native_version, 'worker_done': True,
                'terminal': True}), encoding='utf-8')
        else:
            # Current 3.13 runs this conservative 3.11 branch via a module-only
            # facade. On CI3.11 the actual legacy protocol is used. This fault
            # does not claim to reproduce CPython's sentinel-lock bug.
            class LegacyFacade:
                version_info = (3, 11)
                def __getattr__(self, name): return getattr(sys, name)
            fixture.sys = LegacyFacade()
            actual_body, actual_hold = fixture._owned_worker_body, fixture._owned_hold_unknown
            never = threading.Event()
            def body(record, arguments):
                actual_body(record, arguments)
                never.wait()  # BODY done, actual owned native Thread still live
            fixture._owned_worker_body = body
            def join(thread, *args, **kwargs):
                if thread.name.startswith('aiflow-copy'): raise original_error
                return original_join(thread, *args, **kwargs)
            threading.Thread.join = join
            def unknown(record):
                record.terminal_unknown = True
                assert record.cleanup_failure.error is original_error
                assert record.worker_done.is_set() and record.thread.is_alive()
                ready.write_text(json.dumps({'stage': 'terminal-unknown', 'worker_done': True,
                    'terminal': False, 'terminal_unknown': True, 'actual_version': native_version,
                    'legacy_facade': native_version != (3, 11)}), encoding='utf-8')
                actual_hold(record)
            fixture._owned_hold_unknown = unknown
            fixture._parallel_copy_snapshot(source, target, executor_factory=factory)
            raise AssertionError('Unknown native terminal must not return')
        """
    )
    stdout, stderr = tmp_path / "child.stdout.raw", tmp_path / "child.stderr.raw"
    ready, result = tmp_path / "ready.json", tmp_path / "result.json"
    flags = (
        subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )
    with stdout.open("xb") as out, stderr.open("xb") as err:
        child = subprocess.Popen(
            [sys.executable, "-B", "-c", code, str(Path(__file__).parent), str(tmp_path), scenario],
            cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            creationflags=flags,
            start_new_session=os.name != "nt",
        )

        def identity() -> tuple[int, int] | None:
            if os.name != "nt":
                return None  # direct unreaped child ownership, never numeric-PID guessing
            from ctypes import wintypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetProcessId.argtypes = [wintypes.HANDLE]
            kernel.GetProcessId.restype = wintypes.DWORD
            kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
                ctypes.POINTER(wintypes.FILETIME)
            ] * 4
            kernel.GetProcessTimes.restype = wintypes.BOOL
            times = [wintypes.FILETIME() for _ in range(4)]
            handle = wintypes.HANDLE(int(child._handle))
            assert kernel.GetProcessId(handle) == child.pid
            assert kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times))
            return child.pid, (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime

        retained_identity = None
        identity_captured = False
        actual_exit = None
        try:
            # Popen succeeded: identity observation is also inside owned
            # recovery, so an observation failure cannot leave this child live.
            retained_identity = identity()
            identity_captured = True
            deadline = time.monotonic() + 5
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.005)
            assert ready.exists(), "Owned child did not reach the expected ownership boundary"
            facts = json.loads(ready.read_text(encoding="utf-8"))
            # This observation bound is not a production copy/Git/600 deadline.
            with pytest.raises(subprocess.TimeoutExpired):
                child.wait(timeout=0.05)
            assert not result.exists()
            if scenario == "resolve":
                assert facts["stage"] == "unknown-start" and facts["worker_done"] is False
                (tmp_path / "resolve").write_bytes(b"actual-start")
                actual_exit = child.wait(timeout=5)
                assert actual_exit == 0
                facts = json.loads(result.read_text(encoding="utf-8"))
                assert facts["same_error"] and facts["terminal"] and facts["worker_done"]
            else:
                assert facts["stage"] == "terminal-unknown"
                assert facts["terminal_unknown"] and not facts["terminal"]
                assert facts["worker_done"]
        finally:
            # Only this retained child, including its owned native threads. It
            # launches no processes; no global enumeration, taskkill or PID kill.
            if child.poll() is None:
                child.kill()
            actual_exit = child.wait(timeout=5)
            assert child.poll() == actual_exit
            identity_matches = None
            if identity_captured:
                try:
                    identity_matches = identity() == retained_identity
                except Exception:
                    identity_matches = False
            (tmp_path / "owned-terminal.json").write_text(
                json.dumps(
                    {
                        "retained_identity": retained_identity,
                        "identity_captured": identity_captured,
                        "identity_matches": identity_matches,
                        "actual_exit": actual_exit,
                    }
                ),
                encoding="utf-8",
            )
            if identity_captured:
                assert identity_matches is True
    assert actual_exit == 0 if scenario == "resolve" else actual_exit != 0
    return facts


@pytest.mark.parametrize("scenario", ["resolve", "legacy-unknown"])
def test_parallel_unknown_start_resolution_and_legacy_join_have_owned_outer_recovery(
    tmp_path: Path, scenario: str
) -> None:
    facts = _parallel_owned_child(tmp_path, scenario)
    assert facts["stage"] == ("native-joined" if scenario == "resolve" else "terminal-unknown")


def test_parallel_shutdown_reentry_keeps_first_cleanup_and_drains_actual_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    source, target = _parallel_tree(tmp_path, 1)
    running, bookkeeping_fault, release, returned = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    original = RuntimeError("selected walk failure")
    first, second = (
        KeyboardInterrupt("first shutdown failure"),
        KeyboardInterrupt("later loop failure"),
    )
    failures: list[BaseException] = []
    states: list[object] = []
    pools: list[object] = []
    copies: list[str] = []

    class Records(list):
        armed = False
        interrupted = False

        def __len__(self) -> int:
            if self.armed and not self.interrupted:
                self.interrupted = True
                assert states[0].cleanup_failure.error is first
                bookkeeping_fault.set()
                raise second  # actual helper loop condition, outside its inner try
            return super().__len__()

    class ShutdownFault(fixture._OwnedCopyExecutor):
        injected = False

        def shutdown(self, *args: object, **kwargs: object) -> None:
            super().shutdown(*args, **kwargs)
            if not self.injected:
                self.injected = True
                self.owned_workers.armed = True
                raise first

    def factory(**options: object) -> object:
        pool = ShutdownFault(**options)
        pool.owned_workers = Records()
        pools.append(pool)
        return pool

    def held_copy(entry: os.DirEntry[str], destination: str) -> object:
        running.set()
        assert release.wait(5)
        copies.append(entry.name)
        return shutil.copy2(entry, destination)

    def interrupted_walk(src: object, dst: object, state: object) -> None:
        # A private coordinator fault while a real retained job is running.
        # It does not change the public walker or any original test assertion.
        states.append(state)
        with os.scandir(source) as iterator:
            entry = next(iterator)
        job = fixture._CopyJob(entry, str(source / entry.name), str(target / entry.name))
        state.jobs.append(job)
        job.future = state.executor.submit(fixture._parallel_file_job, job, state.copy_file)
        assert running.wait(5)
        raise original

    monkeypatch.setattr(fixture, "_parallel_copy_directory", interrupted_walk)

    def call() -> None:
        try:
            fixture._parallel_copy_snapshot(
                source, target, copy_file=held_copy, executor_factory=factory
            )
        except BaseException as error:
            failures.append(error)
        finally:
            returned.set()

    caller = threading.Thread(target=call, name="fixture-shutdown-caller")
    caller.start()
    try:
        assert bookkeeping_fault.wait(5) and running.is_set()
        assert not returned.wait(0.02)  # still-owned actual job has not drained
    finally:
        release.set()
        caller.join(5)
    assert not caller.is_alive() and returned.is_set()
    assert len(failures) == 1 and failures[0] is original
    assert states[0].cleanup_failure.error is first
    assert copies == ["f000"]
    assert (target / "f000").read_bytes() == (source / "f000").read_bytes()
    _assert_parallel_pools_ended(pools)


def _reference_populate(
    target: Path,
    run_git: fixture.Git,
    populate: fixture.Populate = helpers._populate_repository,
) -> Path:
    target.mkdir()
    return fixture.populate_or_copy(
        target,
        project_root=helpers.PROJECT_ROOT,
        repository_id=helpers.REPOSITORY_ID,
        populate=populate,
        run_git=run_git,
        standard_helpers=True,
    )


def test_reference_init_once_and_no_warm_init(
    tmp_path: Path, owner: fixture.RepositoryOwner
) -> None:
    references: list[Path] = []

    def observe(path: Path, *arguments: str) -> str:
        if arguments == ("init", "-b", "main"):
            assert owner.contains(path) and path.parent == owner.basetemp
            assert not list(path.iterdir())
            references.append(path)
        return helpers.run_git(path, *arguments)

    original = _reference_populate(tmp_path / "first", observe)
    assert len(references) == 1
    reference = references[0]
    assert reference not in {original, owner.snapshot, helpers.PROJECT_ROOT}
    assert not (reference / ".ai").exists()
    assert owner.snapshot is not None and owner.qualification is not None
    assert owner.cold == 1 and owner.hits == 0 and not owner.disabled
    initial = snapshot(original)
    copied = _reference_populate(tmp_path / "second", observe)
    assert len(references) == 1 and owner.cold == 1 and owner.hits == 1
    assert snapshot(copied) == initial == snapshot(owner.snapshot)
    assert helpers.run_git(copied, "log", "-1", "--format=%s") == "initial"


def _private_template(tmp_path: Path) -> Path:
    template = tmp_path / "template"
    for directory in ("branches", "hooks", "info"):
        (template / directory).mkdir(parents=True)
    (template / "description").write_bytes(b"private description\n")
    (template / "hooks/private.sample").write_bytes(b"private sample\n")
    (template / "info/exclude").write_bytes(b"# private inactive comment\n")
    return template


def _initialized_template_targets(tmp_path: Path, template: Path) -> tuple[Path, Path]:
    targets = (tmp_path / "seed", tmp_path / "reference")
    for target in targets:
        target.mkdir()
        helpers.run_git(target, "init", "-b", "main", f"--template={template}")
    return targets


def test_reference_accepts_actual_git_modes_and_binds_source_modes(tmp_path: Path) -> None:
    template = _private_template(tmp_path)
    source = template / "hooks/private.sample"
    source.chmod(stat.S_IREAD)
    before = fixture._template_fact(template)
    repository, reference = _initialized_template_targets(tmp_path, template)
    assert fixture._template_fact(template, repository, reference) == before
    assert fixture._path_fact(source) != fixture._path_fact(
        repository / ".git/hooks/private.sample"
    )
    with pytest.raises(fixture._Ineligible):
        fixture._template_fact(template, repository)
    source.chmod(stat.S_IREAD | stat.S_IWRITE)
    assert fixture._template_fact(template) != before


@pytest.mark.parametrize("damage", ["bytes", "extra", "missing", "type"])
def test_reference_and_seed_common_corruption_is_rejected(tmp_path: Path, damage: str) -> None:
    template = _private_template(tmp_path)
    repository, reference = _initialized_template_targets(tmp_path, template)
    for target in (repository, reference):
        sample = target / ".git/hooks/private.sample"
        if damage == "bytes":
            sample.write_bytes(b"same wrong bytes\n")
        elif damage == "extra":
            (sample.parent / "extra.sample").write_bytes(b"same extra\n")
        elif damage == "missing":
            sample.unlink()
        else:
            sample.unlink()
            sample.mkdir()
    assert fixture._path_fact(repository / ".git/hooks") == fixture._path_fact(
        reference / ".git/hooks"
    )
    with pytest.raises(fixture._Ineligible):
        fixture._template_fact(template, repository, reference)


@pytest.mark.parametrize("damage", ["bytes", "mode", "missing", "extra", "active"])
def test_reference_damage_preserves_original_cold_success(
    tmp_path: Path, owner: fixture.RepositoryOwner, damage: str
) -> None:
    references: list[Path] = []

    def corrupt(path: Path, *arguments: str) -> str:
        result = helpers.run_git(path, *arguments)
        if arguments == ("init", "-b", "main"):
            references.append(path)
            description = path / ".git/description"
            if damage == "bytes":
                description.write_bytes(b"corrupted reference\n")
            elif damage == "mode":
                old = description.stat().st_mode
                description.chmod(stat.S_IREAD)
                assert description.stat().st_mode != old
            elif damage == "missing":
                description.unlink()
            elif damage == "extra":
                (path / ".git/hooks/extra.sample").write_bytes(b"extra\n")
            else:
                (path / ".git/hooks/post-checkout").write_bytes(b"active\n")
        return result

    result = _reference_populate(tmp_path / "first", corrupt)
    assert len(references) == 1 and references[0].is_dir()
    assert owner.disabled and owner.reason is fixture.IneligibleReason.QUALIFICATION_FAILED
    assert owner.snapshot is None and owner.qualification is None
    assert owner.cold == 1 and owner.hits == 0
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"
    _reference_populate(tmp_path / "second", corrupt)
    assert len(references) == 1 and owner.hits == 0


@pytest.mark.parametrize(
    "key", ["init.templateDir", "core.sharedRepository", "include.path", "unknown.setting"]
)
def test_unknown_configuration_precedes_reference_init(
    tmp_path: Path, owner: fixture.RepositoryOwner, key: str
) -> None:
    references: list[Path] = []

    def configure(path: Path) -> Path:
        result = helpers._populate_repository(path)
        helpers.run_git(path, "config", key, "private-invalid-value")
        return result

    def observe(path: Path, *arguments: str) -> str:
        if arguments == ("init", "-b", "main"):
            references.append(path)
        return helpers.run_git(path, *arguments)

    result = _reference_populate(tmp_path / "first", observe, configure)
    assert not references
    assert owner.disabled and owner.reason is fixture.IneligibleReason.CONFIGURATION
    assert owner.snapshot is None and owner.hits == 0 and owner.cold == 1
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"


def test_attributes_precede_reference_init(tmp_path: Path, owner: fixture.RepositoryOwner) -> None:
    references: list[Path] = []

    def configure(path: Path) -> Path:
        result = helpers._populate_repository(path)
        (path / ".git/info/attributes").write_bytes(b"tracked.txt text\n")
        return result

    def observe(path: Path, *arguments: str) -> str:
        if arguments == ("init", "-b", "main"):
            references.append(path)
        return helpers.run_git(path, *arguments)

    result = _reference_populate(tmp_path / "first", observe, configure)
    assert not references
    assert owner.disabled and owner.reason is fixture.IneligibleReason.ATTRIBUTES
    assert owner.snapshot is None and owner.hits == 0
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"


@pytest.mark.parametrize(
    "location", ["existing", "occupied", "seed", "project", "nested", "outside"]
)
def test_reference_allocation_unsafe_paths_never_init(
    tmp_path: Path,
    owner: fixture.RepositoryOwner,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
) -> None:
    target = tmp_path / "seed"
    existing = owner.factory.mktemp("existing-reference")
    original_mktemp = owner.factory.mktemp
    calls: list[Path] = []

    def allocate(prefix: str, **kwargs: object) -> Path:
        assert prefix == "q"
        if location == "existing":
            return existing
        if location == "occupied":
            candidate = original_mktemp("occupied-reference")
            (candidate / "sentinel").write_bytes(b"keep\n")
            return candidate
        if location == "seed":
            return target
        if location == "project":
            return helpers.PROJECT_ROOT
        if location == "nested":
            candidate = target / "nested"
            candidate.mkdir()
            return candidate
        return owner.basetemp.parent

    def observe(path: Path, *arguments: str) -> str:
        if arguments == ("init", "-b", "main"):
            calls.append(path)
        return helpers.run_git(path, *arguments)

    monkeypatch.setattr(owner.factory, "mktemp", allocate)
    result = _reference_populate(target, observe)
    assert not calls and existing.is_dir()
    assert owner.disabled and owner.snapshot is None and owner.hits == 0
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"


@pytest.mark.parametrize("change", ["source", "config", "environment"])
def test_reference_init_input_drift_is_not_published(
    tmp_path: Path,
    owner: fixture.RepositoryOwner,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    project = source_copy(tmp_path, monkeypatch)
    target = tmp_path / "seed"
    references: list[Path] = []

    def drift(path: Path, *arguments: str) -> str:
        result = helpers.run_git(path, *arguments)
        if arguments == ("init", "-b", "main"):
            references.append(path)
            if change == "source":
                source = next(
                    path for path in (project / ".ai/policy").rglob("*") if path.is_file()
                )
                source.write_bytes(source.read_bytes() + b"\n")
            elif change == "config":
                config = target / ".git/config"
                config.write_bytes(config.read_bytes() + b"\n# changed during reference init\n")
            else:
                monkeypatch.setenv("AIFLOW_REFERENCE_TEST", "changed")
        return result

    result = _reference_populate(target, drift)
    assert len(references) == 1 and references[0].is_dir()
    assert owner.disabled and owner.reason is fixture.IneligibleReason.INPUT_CHANGED
    assert owner.snapshot is None and owner.hits == 0 and owner.cold == 1
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"


def test_reference_init_failure_keeps_partial_and_cold_result(
    tmp_path: Path, owner: fixture.RepositoryOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    references: list[Path] = []
    secret = "private-reference-error-not-for-diagnostics"

    def fail(path: Path, *arguments: str) -> str:
        result = helpers.run_git(path, *arguments)
        if arguments == ("init", "-b", "main"):
            references.append(path)
            raise RuntimeError(secret)
        return result

    result = _reference_populate(tmp_path / "seed", fail)
    assert len(references) == 1 and (references[0] / ".git").is_dir()
    assert owner.disabled and owner.reason is fixture.IneligibleReason.QUALIFICATION_FAILED
    assert owner.snapshot is None and owner.cold == 1 and owner.hits == 0
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err


def test_qualification_diagnostic_excludes_unknown_callbacks_and_private_text(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    callbacks: list[str] = []

    class PrivateError(RuntimeError):
        def __str__(self) -> str:
            callbacks.append("str")
            return "private secret"

        def __repr__(self) -> str:
            callbacks.append("repr")
            return "private secret"

    def fail(*args: object, **kwargs: object) -> None:
        raise PrivateError("private secret")

    monkeypatch.setattr(fixture, "_qualify", fail)
    assert json.loads(_qualification_diagnostic(tmp_path, owner)) == {
        "type": "OTHER_EXCEPTION",
        "sites": [],
    }
    assert not callbacks


def test_qualification_diagnostic_only_trusted_function_and_line(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(git: Path) -> Path:
        raise fixture._Ineligible()

    monkeypatch.setattr(fixture, "_template_for", fail)
    diagnostic = json.loads(_qualification_diagnostic(tmp_path, owner))
    assert diagnostic["type"] == "_Ineligible"
    assert len(diagnostic["sites"]) == 1
    site = diagnostic["sites"][0]
    assert set(site) == {"function", "line"}
    assert site["function"] == "_qualify" and type(site["line"]) is int


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit()])
def test_qualification_diagnostic_preserves_control_interruptions(
    tmp_path: Path,
    owner: fixture.RepositoryOwner,
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(fixture, "_qualify", fail)
    with pytest.raises(type(error)) as caught:
        _qualification_diagnostic(tmp_path, owner)
    assert caught.value is error


def test_seed_qualification_failure_still_fails_after_successful_recheck(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def create(path: Path) -> Path:
        path.mkdir()
        result = helpers._populate_repository(path)
        owner.disabled = True
        owner.reason = fixture.IneligibleReason.QUALIFICATION_FAILED
        return result

    monkeypatch.setattr(helpers, "create_repository", create)
    monkeypatch.setattr(fixture, "_qualify", lambda *args, **kwargs: object())
    with pytest.raises(pytest.fail.Exception, match="DIRECT_RECHECK_PASSED"):
        seed(tmp_path, owner)
    assert owner.snapshot is None and owner.qualification is None


def test_private_environment_isolates_and_restores_host_inputs(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    previous_owner = fixture._owner
    original_environment = dict(os.environ)
    host_home = tmp_path / "host-profile"
    host_home.mkdir()
    host_xdg = host_home / "xdg"
    host_xdg.mkdir()
    host_config = host_home / ".gitconfig"
    config_bytes = b"[user]\n\tname = private-host-user\n"
    host_config.write_bytes(config_bytes)
    with pytest.MonkeyPatch.context() as host:
        host.setenv("HOME", str(host_home))
        host.setenv("XDG_CONFIG_HOME", str(host_xdg))
        host.setenv("GIT_CONFIG_COUNT", "0")
        polluted_environment = dict(os.environ)
        with pytest.MonkeyPatch.context() as isolated:
            home = _private_git_environment.__wrapped__(tmp_path_factory, isolated)
            assert home.parent == tmp_path_factory.getbasetemp() and home != host_home
            assert list(home.iterdir()) == [home / "xdg"]
            assert not list((home / "xdg").iterdir())
            assert os.environ["HOME"] == str(home)
            assert os.environ["XDG_CONFIG_HOME"] == str(home / "xdg")
            assert not any(name.upper().startswith("GIT_") for name in os.environ)
            scoped_owner = owner.__wrapped__(tmp_path_factory, isolated, home)
            token = next(scoped_owner)
            references: list[Path] = []

            def observe(path: Path, *arguments: str) -> str:
                if arguments == ("init", "-b", "main"):
                    references.append(path)
                return helpers.run_git(path, *arguments)

            try:
                original = _reference_populate(tmp_path / "isolated-first", observe)
                assert not token.disabled and token.snapshot is not None
                assert token.qualification is not None and len(references) == 1
                copied = _reference_populate(tmp_path / "isolated-second", observe)
                assert token.cold == 1 and token.hits == 1 and len(references) == 1
                assert snapshot(original) == snapshot(copied) == snapshot(token.snapshot)
            finally:
                scoped_owner.close()
            assert fixture._owner is previous_owner
        assert dict(os.environ) == polluted_environment
    assert dict(os.environ) == original_environment
    assert fixture._owner is previous_owner and host_config.read_bytes() == config_bytes


@pytest.mark.parametrize("change", ["home_config", "xdg_config", "git_environment"])
def test_private_environment_keeps_unknown_input_guards(
    tmp_path: Path,
    owner: fixture.RepositoryOwner,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    if change == "git_environment":
        monkeypatch.setenv("GIT_CONFIG_COUNT", "0")
        reason = fixture.IneligibleReason.GIT_ENVIRONMENT
    else:
        home = Path(os.environ["HOME"])
        assert owner.contains(home)
        if change == "home_config":
            configuration = home / ".gitconfig"
        else:
            directory = Path(os.environ["XDG_CONFIG_HOME"]) / "git"
            directory.mkdir()
            configuration = directory / "config"
        configuration.write_bytes(b"[user]\n\tname = private-unsupported-user\n")
        reason = fixture.IneligibleReason.CONFIGURATION
    references: list[Path] = []

    def observe(path: Path, *arguments: str) -> str:
        if arguments == ("init", "-b", "main"):
            references.append(path)
        return helpers.run_git(path, *arguments)

    result = _reference_populate(tmp_path / "rejected", observe)
    assert not references and owner.disabled and owner.reason is reason
    assert owner.snapshot is None and owner.qualification is None
    assert owner.cold == 1 and owner.hits == 0
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"


def test_private_environment_handles_case_sensitive_mapping(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    from types import SimpleNamespace

    # A dictionary retains POSIX key spelling even on a Windows test host.
    environment = {
        "HOME": "outside-profile",
        "XDG_CONFIG_HOME": "outside-xdg",
        "git_config_count": "0",
        "GiT_PaGeR": "private-pager",
        "PATH": "unchanged-path",
        "OTHER": "unchanged-value",
    }
    original = environment.copy()
    with pytest.MonkeyPatch.context() as view:
        view.setitem(globals(), "os", SimpleNamespace(environ=environment))
        with pytest.MonkeyPatch.context() as isolated:
            home = _private_git_environment.__wrapped__(tmp_path_factory, isolated)
            assert environment == {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / "xdg"),
                "PATH": "unchanged-path",
                "OTHER": "unchanged-value",
            }
        assert environment == original


def test_private_system_context_reaches_every_git_command(
    tmp_path: Path, owner: fixture.RepositoryOwner
) -> None:
    import sys

    context = fixture._private_git_context
    assert context is not None and context.system.read_bytes() == b""
    parent = dict(os.environ)
    observed: list[tuple[list[str], dict[str, str] | None]] = []
    previous = sys.getprofile()

    def observe(frame: object, event: str, argument: object) -> None:
        from types import FrameType

        assert isinstance(frame, FrameType)
        if event == "call" and frame.f_code is helpers._run_fixture_command.__code__:
            observed.append((frame.f_locals["argv"], frame.f_locals["env"]))

    try:
        sys.setprofile(observe)
        original = helpers.create_repository(tmp_path / "first")
        assert owner.qualification is not None and owner.snapshot is not None
        assert context.system in owner.qualification.files
        assert helpers.run_git(original, "var", "GIT_CONFIG_SYSTEM").replace("\\", "/") == (
            str(context.system).replace("\\", "/")
        )
        copied = helpers.create_repository(tmp_path / "second")
        (copied / "tracked.txt").write_text("changed\n")
        helpers.commit_all(copied, "changed")
    finally:
        sys.setprofile(previous)
    assert owner.cold == 1 and owner.hits == 1
    assert dict(os.environ) == parent
    assert observed and all(argv[0] == "git" for argv, _ in observed)
    assert all(
        environment is not None
        and environment["GIT_CONFIG_SYSTEM"] == str(context.system)
        and {key: value for key, value in environment.items() if key != "GIT_CONFIG_SYSTEM"}
        == parent
        for _, environment in observed
    )
    commands = []
    for argv, _ in observed:
        arguments = argv[1:]
        while arguments[0] == "-c":
            arguments = arguments[2:]
        commands.append(arguments[0])
    assert commands.count("init") == 2
    assert {"init", "add", "commit", "config", "var", "status", "check-attr"} <= set(commands)


@pytest.mark.parametrize("change", ["bytes", "mode", "inode", "context", "owner", "factory"])
def test_private_system_context_drift_cannot_reuse_snapshot(
    tmp_path: Path,
    owner: fixture.RepositoryOwner,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    seed(tmp_path, owner)
    context = fixture._private_git_context
    assert context is not None and owner.qualification is not None
    assert owner.snapshot is not None
    pristine = snapshot(owner.snapshot)
    token = owner
    initial_mode = stat.S_IMODE(context.system.stat().st_mode)
    try:
        if change == "bytes":
            context.system.write_bytes(b"[core]\n\tautocrlf = false\n")
        elif change == "mode":
            context.system.chmod(0o444 if initial_mode & stat.S_IWUSR else 0o666)
            assert stat.S_IMODE(context.system.stat().st_mode) != initial_mode
        elif change == "inode":
            replacement = context.system.with_name("replacement")
            replacement.write_bytes(context.system.read_bytes())
            old_identity = (context.system.stat().st_dev, context.system.stat().st_ino)
            replacement.replace(context.system)
            assert (context.system.stat().st_dev, context.system.stat().st_ino) != old_identity
        elif change == "context":
            monkeypatch.setattr(
                fixture,
                "_private_git_context",
                fixture._PrivateGitContext.create(context.scope, context.system),
            )
        elif change == "owner":
            token = fixture.RepositoryOwner(owner.factory, owner.basetemp)
            token.snapshot = owner.snapshot
            token.snapshot_sha256 = owner.snapshot_sha256
            token.qualification = owner.qualification
            monkeypatch.setattr(fixture, "_owner", token)
        else:

            class Factory:
                def getbasetemp(self) -> Path:
                    return owner.basetemp

            monkeypatch.setattr(owner, "factory", Factory())
        with pytest.raises(fixture._Ineligible, match="INPUT_CHANGED"):
            owner.qualification.current(helpers.PROJECT_ROOT, helpers.REPOSITORY_ID)
        result = helpers.create_repository(tmp_path / "cold")
        assert token.hits == 0 and helpers.run_git(result, "log", "-1", "--format=%s") == "initial"
        assert snapshot(owner.snapshot) == pristine
    finally:
        context.system.chmod(initial_mode)


@pytest.mark.parametrize("change", ["missing", "directory", "hardlink"])
def test_private_system_context_unsafe_input_fails_without_host_fallback(
    tmp_path: Path, owner: fixture.RepositoryOwner, change: str
) -> None:
    seed(tmp_path, owner)
    context = fixture._private_git_context
    assert context is not None
    context.system.unlink()
    if change == "directory":
        context.system.mkdir()
    elif change == "hardlink":
        other = context.system.with_name("other")
        other.write_bytes(b"")
        context.system.hardlink_to(other)
    with pytest.raises((fixture._Ineligible, FileNotFoundError)):
        helpers.create_repository(tmp_path / "rejected")
    assert owner.hits == 0 and not (tmp_path / "rejected/.git").exists()


def test_private_system_unknown_configuration_remains_rejected(
    tmp_path: Path, owner: fixture.RepositoryOwner
) -> None:
    context = fixture._private_git_context
    assert context is not None
    context.system.write_bytes(b"[safe]\n\tdirectory = *\n")
    repository = helpers.create_repository(tmp_path / "unknown")
    assert owner.disabled and owner.reason is fixture.IneligibleReason.CONFIGURATION
    assert owner.snapshot is None and owner.qualification is None and owner.hits == 0
    assert helpers.run_git(repository, "config", "--name-only", "--get-regexp", "^safe\\.") == (
        "safe.directory"
    )


def test_private_system_preserves_parent_override_and_original_rejection(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_system = tmp_path / "parent-config"
    parent_system.write_bytes(b"[safe]\n\tdirectory = *\n")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(parent_system))
    environment = fixture.git_child_environment(tmp_path)
    assert environment is not None and environment["GIT_CONFIG_SYSTEM"] == str(parent_system)
    with pytest.raises(fixture._Ineligible, match="GIT_ENVIRONMENT_OVERRIDE"):
        fixture._environment_fact()
    repository = helpers.create_repository(tmp_path / "parent")
    assert owner.hits == 0 and owner.snapshot is None
    assert helpers.run_git(repository, "config", "--name-only", "--get-regexp", "^safe\\.") == (
        "safe.directory"
    )


def test_private_system_binder_replacement_remains_cold(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(tmp_path, owner)
    assert owner.qualification is not None
    calls: list[Path] = []
    original = fixture.git_child_environment

    def replacement(repository: Path) -> dict[str, str] | None:
        calls.append(repository)
        return original(repository)

    monkeypatch.setattr(fixture, "git_child_environment", replacement)
    assert not fixture._standard_io()
    with pytest.raises(fixture._Ineligible, match="INPUT_CHANGED"):
        owner.qualification.current(helpers.PROJECT_ROOT, helpers.REPOSITORY_ID)
    result = helpers.create_repository(tmp_path / "cold")
    assert calls and owner.hits == 0
    assert helpers.run_git(result, "log", "-1", "--format=%s") == "initial"


@pytest.mark.parametrize("change", ["constant", "code"])
def test_private_system_fact_replacement_remains_cold(
    tmp_path: Path,
    owner: fixture.RepositoryOwner,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    seed(tmp_path, owner)
    assert owner.qualification is not None
    original = fixture._git_context_fact
    captured = original()
    if change == "constant":
        # Do not delegate into the original fact's internal standard check.
        monkeypatch.setattr(fixture, "_git_context_fact", lambda: captured)
    else:

        def forbidden() -> object:
            raise AssertionError("Changed fact code must never certify current inputs")

        monkeypatch.setattr(original, "__code__", forbidden.__code__)
    assert not fixture._standard_io()
    with pytest.raises(fixture._Ineligible, match="INPUT_CHANGED"):
        owner.qualification.current(helpers.PROJECT_ROOT, helpers.REPOSITORY_ID)
    result = helpers.create_repository(tmp_path / "cold")
    assert owner.hits == 0 and helpers.run_git(result, "log", "-1", "--format=%s") == "initial"


def test_private_system_does_not_change_default_foreign_or_non_git_commands(
    tmp_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    owner: fixture.RepositoryOwner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    context = fixture._private_git_context
    assert context is not None
    assert fixture.git_child_environment(tmp_path) is not None
    with monkeypatch.context() as scoped:
        scoped.setattr(fixture, "_owner", None)
        assert fixture.git_child_environment(tmp_path) is None
    foreign_base = tmp_path_factory.mktemp("foreign")
    foreign = fixture.RepositoryOwner(owner.factory, foreign_base)
    with monkeypatch.context() as scoped:
        scoped.setattr(fixture, "_owner", foreign)
        assert fixture.git_child_environment(tmp_path) is None
    with monkeypatch.context() as scoped:
        scoped.setattr(fixture, "_private_git_context", None)
        assert fixture.git_child_environment(tmp_path) is None
    assert (
        helpers._run_fixture_command(
            tmp_path, [sys.executable, "-c", "import os; print('GIT_CONFIG_SYSTEM' in os.environ)"]
        )
        == "False"
    )
    assert dict(os.environ).get("GIT_CONFIG_SYSTEM") is None


def test_private_system_replaced_owner_root_never_selects_context(
    tmp_path: Path, owner: fixture.RepositoryOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "owned-root"
    base.mkdir()

    class Factory:
        def getbasetemp(self) -> Path:
            return base

    from typing import cast

    token = fixture.RepositoryOwner(cast(pytest.TempPathFactory, Factory()), base)
    monkeypatch.setattr(fixture, "_owner", token)
    assert fixture.git_child_environment(base) is not None
    assert fixture.git_child_environment(tmp_path) is None
    base.rename(tmp_path / "original-root")
    base.mkdir()
    assert not token.contains(base)
    assert fixture.git_child_environment(base) is None
    repository = helpers.create_repository(base / "cold")
    assert token.snapshot is None and token.hits == 0
    assert helpers.run_git(repository, "log", "-1", "--format=%s") == "initial"


@pytest.mark.parametrize("failure", [False, True])
def test_private_system_context_normal_and_exception_restoration(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory, failure: bool
) -> None:
    previous_context = fixture._private_git_context
    previous_owner = fixture._owner
    parent = dict(os.environ)
    holder: list[fixture._PrivateGitContext] = []
    try:
        with pytest.MonkeyPatch.context() as isolated:
            home = _private_git_environment.__wrapped__(tmp_path_factory, isolated)
            scoped_owner = owner.__wrapped__(tmp_path_factory, isolated, home)
            token = next(scoped_owner)
            try:
                context = fixture._private_git_context
                assert context is not None and context is not previous_context
                holder.append(context)
                helpers.create_repository(tmp_path / "owned")
                assert token.qualification is not None and token.snapshot is not None
                if failure:
                    raise RuntimeError("owned test failure")
            finally:
                scoped_owner.close()
    except RuntimeError as error:
        assert failure and str(error) == "owned test failure"
    assert len(holder) == 1 and holder[0].system.read_bytes() == b""
    assert fixture._private_git_context is previous_context and fixture._owner is previous_owner
    assert dict(os.environ) == parent
