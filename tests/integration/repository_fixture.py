"""Session-private copies of a proven, unstarted initial integration repository."""

from __future__ import annotations

import dis
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import weakref
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import thread as futures_thread
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import BuiltinFunctionType, TracebackType
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pytest

Git = Callable[..., str]
Populate = Callable[[Path], Path]
_COPYTREE = shutil.copytree
_COPY2 = shutil.copy2
_LSTAT = Path.lstat
_READ_BYTES = Path.read_bytes
_WRITE_TEXT = Path.write_text
_MKDIR = Path.mkdir
_POPEN = subprocess.Popen
_SOURCE_DIRECTORIES = ("schemas", "policy", "templates")
_COPYSTAT = shutil.copystat
_SCANDIR = os.scandir
_MAKEDIRS = os.makedirs
_AUDIT = sys.audit
_EXECUTOR = ThreadPoolExecutor
_EXECUTOR_INIT = ThreadPoolExecutor.__init__
_EXECUTOR_SUBMIT = ThreadPoolExecutor.submit
_EXECUTOR_SHUTDOWN = ThreadPoolExecutor.shutdown
_EXECUTOR_ADJUST = ThreadPoolExecutor._adjust_thread_count
_THREAD = threading.Thread
_THREAD_START = threading.Thread.start
_THREAD_JOIN = threading.Thread.join
_THREAD_INIT = threading.Thread.__init__
_THREAD_RUN = threading.Thread.run
_THREAD_BOOTSTRAP = getattr(threading.Thread, "_bootstrap")
_THREAD_BOOTSTRAP_INNER = getattr(threading.Thread, "_bootstrap_inner")
_EVENT = threading.Event
_EVENT_WAIT = threading.Event.wait
_EVENT_SET = threading.Event.set
_EVENT_IS_SET = threading.Event.is_set
_NATIVE_START_NAME = (
    "_start_joinable_thread" if sys.version_info[:2] == (3, 13) else "_start_new_thread"
)
_NATIVE_START = getattr(threading, _NATIVE_START_NAME, None)
_SET_SENTINEL = getattr(threading, "_set_sentinel", None)
_LIMBO_LOCK = getattr(threading, "_active_limbo_lock")
_POOL_WORKER: Any = getattr(futures_thread, "_worker")
_POOL_THREAD_QUEUES = getattr(futures_thread, "_threads_queues")
_WEAKREF = weakref.ref
_THREAD_HANDLE = getattr(threading, "_ThreadHandle", None)
_HANDLE_JOIN: Any = getattr(_THREAD_HANDLE, "join", None)
_HANDLE_IS_DONE: Any = getattr(_THREAD_HANDLE, "is_done", None)
_FUTURE_RESULT = Future.result
_FUTURE_EXCEPTION = Future.exception
_FUTURE_DONE = Future.done
_FUTURE_CANCELLED = Future.cancelled
_PARALLEL_FILE_LIMIT = 256
_PARALLEL_WORKERS = 4
_BOOLEAN_KEYS = {
    "core.symlinks",
    "core.fscache",
    "core.filemode",
    "core.bare",
    "core.logallrefupdates",
    "core.ignorecase",
}
_INACTIVE_KEYS = {
    "color.interactive",
    "color.ui",
    "help.format",
    "diff.astextplain.textconv",
    "rebase.autosquash",
    "credential.helper",
    "filter.lfs.clean",
    "filter.lfs.smudge",
    "filter.lfs.process",
    "filter.lfs.required",
}
_ALLOWED_KEYS = (
    _BOOLEAN_KEYS
    | _INACTIVE_KEYS
    | {
        "core.autocrlf",
        "core.repositoryformatversion",
    }
)
_FALSE = {"false", "no", "off", "0", ""}
_TRUE = {"true", "yes", "on", "1"}


class IneligibleReason(str, Enum):
    GIT_LAYOUT = "UNSUPPORTED_GIT_LAYOUT"
    CONFIGURATION = "UNSUPPORTED_CONFIGURATION"
    ATTRIBUTES = "ACTIVE_ATTRIBUTES"
    TEMPLATE = "UNSUPPORTED_TEMPLATE"
    GIT_ENVIRONMENT = "GIT_ENVIRONMENT_OVERRIDE"
    QUALIFICATION_FAILED = "QUALIFICATION_FAILED"
    PUBLICATION_FAILED = "PUBLICATION_FAILED"
    INPUT_CHANGED = "INPUT_CHANGED"


class _Ineligible(Exception):
    """Private fixed diagnostic: never retain configuration or path text."""

    def __init__(self, reason: IneligibleReason = IneligibleReason.QUALIFICATION_FAILED) -> None:
        self.reason = reason
        super().__init__(reason.value)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _ordinary(path: Path) -> os.stat_result:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
        raise _Ineligible()
    if not (stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode)):
        raise _Ineligible()
    return metadata


def _path_fact(path: Path) -> object:
    """Read actual bytes, mode, and absence; never follow an unsafe ancestor."""
    for ancestor in reversed(path.absolute().parents):
        try:
            _ordinary(ancestor)
        except FileNotFoundError:
            pass
    try:
        metadata = _ordinary(path)
    except FileNotFoundError:
        return ["absent"]
    if stat.S_ISDIR(metadata.st_mode):
        entries = [[child.name, _path_fact(child)] for child in sorted(path.iterdir())]
        return ["directory", stat.S_IMODE(metadata.st_mode), entries]
    contents = path.read_bytes()
    return ["file", stat.S_IMODE(metadata.st_mode), hashlib.sha256(contents).hexdigest()]


def _source_fact(project_root: Path) -> str:
    roots = [project_root / ".ai" / name for name in _SOURCE_DIRECTORIES]
    for root in roots:
        if not stat.S_ISDIR(_ordinary(root).st_mode):
            raise _Ineligible()
    return _digest([_path_fact(root) for root in roots])


def _environment_fact() -> str:
    # This pytest label changes per case, is not consumed by Git, and remains
    # untouched in the actual child environment. All other entries stay bound.
    if any(name.upper().startswith("GIT_") for name in os.environ):
        raise _Ineligible(IneligibleReason.GIT_ENVIRONMENT)
    return _digest(
        {key: value for key, value in os.environ.items() if key != "PYTEST_CURRENT_TEST"}
    )


def _standard_io() -> bool:
    return (
        shutil.copytree is _COPYTREE
        and shutil.copy2 is _COPY2
        and Path.lstat is _LSTAT
        and Path.read_bytes is _READ_BYTES
        and Path.write_text is _WRITE_TEXT
        and Path.mkdir is _MKDIR
        and subprocess.Popen is _POPEN
        and git_child_environment is _GIT_CHILD_ENVIRONMENT
        and git_child_environment.__code__ is _GIT_CHILD_ENVIRONMENT_CODE
        and _git_context_fact is _GIT_CONTEXT_FACT
        and _git_context_fact.__code__ is _GIT_CONTEXT_FACT_CODE
    )


def _template_for(git: Path) -> Path:
    # Only proven conventional layouts qualify; all other installations go cold.
    if os.name == "nt" and git.name.lower() == "git.exe":
        if git.parent.name.lower() == "cmd":
            prefix = git.parent.parent
        elif git.parent.name.lower() == "bin" and git.parent.parent.name.lower() == "mingw64":
            prefix = git.parents[2]
        else:
            raise _Ineligible(IneligibleReason.GIT_LAYOUT)
        template = prefix / "mingw64" / "share" / "git-core" / "templates"
    elif sys.platform.startswith("linux") and git == Path("/usr/bin/git"):
        template = Path("/usr/share/git-core/templates")
    else:
        raise _Ineligible(IneligibleReason.GIT_LAYOUT)
    try:
        if not stat.S_ISDIR(_ordinary(template).st_mode):
            raise _Ineligible(IneligibleReason.GIT_LAYOUT)
    except FileNotFoundError:
        raise _Ineligible(IneligibleReason.GIT_LAYOUT) from None
    return template


def _git_fact(git: Path) -> object:
    files = [git]
    if os.name == "nt":
        if git.name.lower() != "git.exe":
            raise _Ineligible(IneligibleReason.GIT_LAYOUT)
        if git.parent.name.lower() == "cmd":
            prefix = git.parent.parent
        elif git.parent.name.lower() == "bin" and git.parent.parent.name.lower() == "mingw64":
            prefix = git.parents[2]
        else:
            raise _Ineligible(IneligibleReason.GIT_LAYOUT)
        files = list(dict.fromkeys((git, prefix / "cmd/git.exe", prefix / "mingw64/bin/git.exe")))
    if any(not stat.S_ISREG(_ordinary(path).st_mode) for path in files):
        raise _Ineligible()
    return [[str(path), _path_fact(path)] for path in files]


def _template_payload(fact: Any) -> Any:
    """Project only modes out of internally generated ordinary path facts."""
    if fact[0] == "directory":
        return ["directory", [[name, _template_payload(child)] for name, child in fact[2]]]
    if fact[0] == "file":
        return ["file", fact[2]]
    return fact


def _template_fact(
    template: Path, repository: Path | None = None, reference: Path | None = None
) -> str:
    if not stat.S_ISDIR(_ordinary(template).st_mode):
        raise _Ineligible()
    for root in template.iterdir():
        if root.name not in {"branches", "hooks", "info", "description"}:
            raise _Ineligible(IneligibleReason.TEMPLATE)
    for parent, directories, files in os.walk(template, followlinks=False):
        base = Path(parent)
        for name in [*directories, *files]:
            _ordinary(base / name)
        for name in files:
            source = base / name
            relative = source.relative_to(template)
            if relative.parts[0] == "hooks" and not name.endswith(".sample"):
                raise _Ineligible(IneligibleReason.TEMPLATE)
            if relative.parts[0] == "info":
                if relative.as_posix() != "info/exclude":
                    raise _Ineligible(IneligibleReason.TEMPLATE)
                if any(
                    line.strip() and not line.lstrip().startswith(b"#")
                    for line in source.read_bytes().splitlines()
                ):
                    raise _Ineligible(IneligibleReason.TEMPLATE)
            expected = source if reference is None else reference / ".git" / relative
            if repository is not None and _path_fact(expected) != _path_fact(
                repository / ".git" / relative
            ):
                raise _Ineligible()
    if repository is not None:
        for name in ("description", "branches", "hooks", "info"):
            if reference is not None:
                source_payload = _template_payload(_path_fact(template / name))
                for target in (repository, reference):
                    if source_payload != _template_payload(_path_fact(target / ".git" / name)):
                        raise _Ineligible()
            expected = (template if reference is None else reference / ".git") / name
            actual = repository / ".git" / name
            expected_names = (
                {path.name for path in expected.iterdir()} if expected.is_dir() else set()
            )
            actual_names = {path.name for path in actual.iterdir()} if actual.is_dir() else set()
            if actual_names - expected_names:
                raise _Ineligible(IneligibleReason.TEMPLATE)
            if _path_fact(expected) != _path_fact(actual):
                # Missing/changed normal entries can be a copy/input failure,
                # not a portable reason to silently skip warm-path assertions.
                raise _Ineligible()
    return _digest(_path_fact(template))


def _template_reference(
    owner: RepositoryOwner, repository: Path, project_root: Path, run_git: Git
) -> Path:
    """Initialize one fresh owner-private metadata reference after qualification."""
    if not owner.contains(repository):
        raise _Ineligible()
    existing = {path.name for path in owner.basetemp.iterdir()}
    reference = owner.factory.mktemp("q")
    if type(reference) is not type(owner.basetemp):
        raise _Ineligible()
    if (
        reference.parent != owner.basetemp
        or reference.name in existing
        or not owner.contains(reference)
        or any(reference.iterdir())
    ):
        raise _Ineligible()
    protected = [repository, project_root]
    if owner.snapshot is not None:
        protected.append(owner.snapshot)
    for path in protected:
        if reference.absolute().is_relative_to(path.absolute()) or path.absolute().is_relative_to(
            reference.absolute()
        ):
            raise _Ineligible()
    metadata = _ordinary(reference)
    identity = (metadata.st_dev, metadata.st_ino)
    run_git(reference, "init", "-b", "main")
    metadata = _ordinary(reference)
    if not owner.contains(reference) or (metadata.st_dev, metadata.st_ino) != identity:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    return reference


def _parse_config(raw: str, *, values: bool) -> list[tuple[str, str, str, str]]:
    fields = raw.split("\0")
    if fields[-1] != "" or (len(fields) - 1) % 3:
        raise _Ineligible()
    result = []
    for index in range(0, len(fields) - 1, 3):
        scope, origin, item = fields[index : index + 3]
        key, separator, value = item.partition("\n") if values else (item, "", "")
        if scope not in {"system", "global", "local"} or not origin.startswith("file:"):
            raise _Ineligible()
        if key not in _ALLOWED_KEYS:
            raise _Ineligible(IneligibleReason.CONFIGURATION)
        if values and not separator:
            raise _Ineligible()
        result.append((scope, origin[5:], key, value))
    return result


def _config_values_valid(entries: list[tuple[str, str, str, str]]) -> bool:
    for _scope, _origin, key, value in entries:
        normalized = value.lower()
        if key in _BOOLEAN_KEYS and normalized not in _FALSE | _TRUE:
            return False
        if key == "core.autocrlf" and normalized not in _FALSE | _TRUE | {"input"}:
            return False
        if key == "core.bare" and normalized not in _FALSE:
            return False
        if key == "core.repositoryformatversion" and value != "0":
            return False
    return True


def _var_paths(run_git: Git, repository: Path, name: str) -> tuple[Path, ...]:
    try:
        text = run_git(repository, "var", name)
    except subprocess.CalledProcessError as error:
        # Git var returns 1 with no output when this recognized variable has no
        # configured path (e.g. native MINENV has no HOME/global config). Unknown
        # variables, diagnostics and all other command failures stay ineligible.
        if error.returncode == 1 and not error.output and not error.stderr:
            return ()
        raise
    result = []
    for line in text.splitlines():
        path = Path(line)
        if not path.is_absolute() or "\0" in line:
            raise _Ineligible()
        result.append(path)
    return tuple(result)


def _no_attributes(repository: Path) -> None:
    for parent, directories, files in os.walk(repository / ".ai", followlinks=False):
        base = Path(parent)
        for name in [*directories, *files]:
            _ordinary(base / name)
        if any(name.lower() == ".gitattributes" for name in files):
            raise _Ineligible(IneligibleReason.ATTRIBUTES)
    if (repository / ".gitattributes").exists() or (repository / ".git/info/attributes").exists():
        raise _Ineligible(IneligibleReason.ATTRIBUTES)


@dataclass(frozen=True)
class _Qualification:
    files: tuple[Path, ...]
    attributes: tuple[Path, ...]
    template: Path
    git: Path
    inputs_sha256: str
    context_binding: _GitContextBinding | None = None

    def current(self, project_root: Path, repository_id: str) -> str:
        if not _standard_io():
            raise _Ineligible(IneligibleReason.INPUT_CHANGED)
        locator = shutil.which("git")
        if locator is None or Path(locator).absolute() != self.git:
            raise _Ineligible()
        for path in self.attributes:
            if _path_fact(path) != ["absent"]:
                raise _Ineligible(IneligibleReason.ATTRIBUTES)
        return _digest(
            [
                str(project_root.absolute()),
                repository_id,
                _source_fact(project_root),
                _environment_fact(),
                (
                    self.context_binding.current()
                    if self.context_binding is not None
                    else _git_context_fact()
                ),
                str(self.git),
                _git_fact(self.git),
                [[str(path), _path_fact(path)] for path in self.files],
                [[str(path), _path_fact(path)] for path in self.attributes],
                _template_fact(self.template),
            ]
        )


def _qualify(
    repository: Path,
    project_root: Path,
    repository_id: str,
    run_git: Git,
    *,
    owner: RepositoryOwner,
) -> _Qualification:
    executable = shutil.which("git")
    if executable is None:
        raise _Ineligible()
    git = Path(executable).absolute()
    # Check ordinary spelling before resolve: a symlink executable must go cold.
    _ordinary(git)
    template = _template_for(git)
    windows_prefix = template.parents[3] if os.name == "nt" else None
    _template_fact(template)
    _no_attributes(repository)
    if any(not path.name.endswith(".sample") for path in (repository / ".git/hooks").iterdir()):
        raise _Ineligible()
    if (repository / ".ai/tasks").exists() or (
        repository / ".git/objects/info/alternates"
    ).exists():
        raise _Ineligible()
    names = _parse_config(
        run_git(
            repository,
            "config",
            "--includes",
            "--null",
            "--show-origin",
            "--show-scope",
            "--name-only",
            "--list",
        ),
        values=False,
    )
    config_paths = (
        *_var_paths(run_git, repository, "GIT_CONFIG_SYSTEM"),
        *_var_paths(run_git, repository, "GIT_CONFIG_GLOBAL"),
    )
    system_attributes = _var_paths(run_git, repository, "GIT_ATTR_SYSTEM")
    global_attributes = _var_paths(run_git, repository, "GIT_ATTR_GLOBAL")
    inactive_system = []
    absent_system = []
    for attribute in system_attributes:
        fact = _path_fact(attribute)
        if fact == ["absent"]:
            absent_system.append(attribute)
        elif (
            os.name == "nt"
            and windows_prefix is not None
            and attribute.absolute()
            in {
                windows_prefix / "etc/gitattributes",
                windows_prefix / "mingw64/etc/gitattributes",
            }
            and fact[0] == "file"
        ):
            inactive_system.append(attribute)
        else:
            raise _Ineligible(IneligibleReason.ATTRIBUTES)
    allowed_origins = {path.absolute() for path in config_paths}
    for scope, origin, _key, _value in names:
        path = Path(origin)
        if not path.is_absolute():
            path = repository / path
        if scope == "local":
            if path.absolute() != (repository / ".git/config").absolute():
                raise _Ineligible()
        elif path.absolute() not in allowed_origins:
            raise _Ineligible()
    # Global ignore can change add semantics too. Unknown/default paths go cold;
    # these ordinary candidates are checked as live absence facts on every hit.
    global_configs = _var_paths(run_git, repository, "GIT_CONFIG_GLOBAL")
    ignores = tuple(path.parent / "ignore" for path in global_configs if path.name == "config")
    qualification = _Qualification(
        tuple(dict.fromkeys((*config_paths, *inactive_system))),
        tuple(dict.fromkeys((*global_attributes, *absent_system, *ignores))),
        template,
        git,
        "",
        _GitContextBinding.capture(owner),
    )
    if run_git(repository, "status", "--porcelain=v1"):
        raise _Ineligible()
    current = qualification.current(project_root, repository_id)
    pristine = _digest(_path_fact(repository))
    # Bind current origin bytes before interpreting values; unknown values are
    # never printed. Recheck all inputs and pristine local config after queries.
    values = _parse_config(
        run_git(
            repository, "config", "--includes", "--null", "--show-origin", "--show-scope", "--list"
        ),
        values=True,
    )
    if [entry[:3] for entry in names] != [entry[:3] for entry in values]:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    if not _config_values_valid(values):
        raise _Ineligible(IneligibleReason.CONFIGURATION)
    initial_paths = sorted(
        path.relative_to(repository).as_posix()
        for path in repository.rglob("*")
        if ".git" not in path.relative_to(repository).parts and path.is_file()
    )
    if any("\n" in path or "\r" in path for path in initial_paths):
        raise _Ineligible()
    if run_git(repository, "check-attr", "-z", "--all", "--", *initial_paths):
        raise _Ineligible(IneligibleReason.ATTRIBUTES)
    if qualification.current(project_root, repository_id) != current:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    if _digest(_path_fact(repository)) != pristine:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    reference = _template_reference(owner, repository, project_root, run_git)
    reference_fact = _digest(_path_fact(reference))
    if qualification.current(project_root, repository_id) != current:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    if _digest(_path_fact(repository)) != pristine:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    # Git creates template modes through its own copy rules and current umask;
    # bind the source completely, then compare the actual initialized output.
    _template_fact(template, repository, reference)
    if qualification.current(project_root, repository_id) != current:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    if _digest(_path_fact(repository)) != pristine:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    if not owner.contains(reference) or _digest(_path_fact(reference)) != reference_fact:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    return _Qualification(
        qualification.files,
        qualification.attributes,
        template,
        git,
        current,
        qualification.context_binding,
    )


@dataclass
class RepositoryOwner:
    """An internal owner token; the snapshot is never a caller repository."""

    factory: pytest.TempPathFactory
    basetemp: Path
    snapshot: Path | None = None
    snapshot_sha256: str | None = None
    qualification: _Qualification | None = None
    disabled: bool = False
    hits: int = 0
    cold: int = 0
    reason: IneligibleReason | None = None
    basetemp_identity: tuple[int, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        metadata = _ordinary(self.basetemp)
        self.basetemp_identity = (metadata.st_dev, metadata.st_ino)

    def contains(self, path: Path) -> bool:
        try:
            metadata = _ordinary(self.basetemp)
            if (metadata.st_dev, metadata.st_ino) != self.basetemp_identity:
                return False
            if any(
                (ancestor / ".git").exists() for ancestor in (self.basetemp, *self.basetemp.parents)
            ):
                return False
            if not path.absolute().is_relative_to(self.basetemp.absolute()):
                return False
            component = path.absolute()
            while component != self.basetemp.absolute():
                _ordinary(component)
                component = component.parent
            return (
                self.factory.getbasetemp() == self.basetemp
                and path.resolve().is_relative_to(self.basetemp.resolve())
                and _ordinary(path).st_dev == _ordinary(self.basetemp).st_dev
            )
        except (OSError, _Ineligible):
            return False


@dataclass(frozen=True, eq=False)
class _PrivateGitContext:
    """A pytest-owned system input, shared only by owners within its private root."""

    scope: RepositoryOwner
    factory: pytest.TempPathFactory
    root: Path
    system: Path
    initial_fact: object

    @classmethod
    def create(cls, scope: RepositoryOwner, system: Path) -> _PrivateGitContext:
        if not scope.contains(system) or system.read_bytes() != b"":
            raise _Ineligible()
        context = cls(scope, scope.factory, scope.basetemp, system.absolute(), None)
        return cls(scope, scope.factory, scope.basetemp, system.absolute(), context.file_fact())

    def matches(self, token: RepositoryOwner | None, repository: Path) -> bool:
        return (
            token is not None
            and token.basetemp.absolute().is_relative_to(self.root.absolute())
            and repository.absolute().is_relative_to(token.basetemp.absolute())
            and self.scope.contains(token.basetemp)
            and token.contains(repository)
        )

    def file_fact(self) -> object:
        if (
            self.scope.factory is not self.factory
            or self.scope.basetemp != self.root
            or not self.scope.contains(self.system)
        ):
            raise _Ineligible(IneligibleReason.INPUT_CHANGED)
        metadata = _ordinary(self.system)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise _Ineligible(IneligibleReason.INPUT_CHANGED)
        ancestors = []
        for path in (self.system.parent, *self.system.parent.parents):
            item = _ordinary(path)
            ancestors.append([str(path), item.st_dev, item.st_ino, stat.S_IMODE(item.st_mode)])
            if path == self.root:
                break
        return [metadata.st_dev, metadata.st_ino, _path_fact(self.system), ancestors]


_owner: RepositoryOwner | None = None
_private_git_context: _PrivateGitContext | None = None


def git_child_environment(repository: Path) -> dict[str, str] | None:
    """Select the actual owned system file without changing the parent environment."""
    context = _private_git_context
    if context is None or not context.matches(_owner, repository):
        return None
    # Unsafe/missing inputs fail explicitly. Ordinary changed bytes still reach
    # cold Git at the fixed path; qualification separately rejects their drift.
    context.file_fact()
    environment = dict(os.environ)
    if not any(name.upper() == "GIT_CONFIG_SYSTEM" for name in environment):
        environment["GIT_CONFIG_SYSTEM"] = str(context.system)
    return environment


_GIT_CHILD_ENVIRONMENT = git_child_environment
_GIT_CHILD_ENVIRONMENT_CODE = git_child_environment.__code__


def _git_context_fact() -> object:
    if not _standard_io():
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    token = _owner
    context = _private_git_context
    if token is None or context is None or not context.matches(token, token.basetemp):
        return None
    current = context.file_fact()
    if current != context.initial_fact:
        raise _Ineligible(IneligibleReason.INPUT_CHANGED)
    environment = git_child_environment(token.basetemp)
    assert environment is not None
    return [
        id(context),
        id(token),
        id(token.factory),
        str(token.basetemp),
        token.basetemp_identity,
        current,
        _digest({key: value for key, value in environment.items() if key != "PYTEST_CURRENT_TEST"}),
    ]


_GIT_CONTEXT_FACT = _git_context_fact
_GIT_CONTEXT_FACT_CODE = _git_context_fact.__code__


@dataclass(frozen=True, eq=False)
class _GitContextBinding:
    owner: RepositoryOwner
    factory: pytest.TempPathFactory
    root: Path
    context: _PrivateGitContext | None

    @classmethod
    def capture(cls, owner: RepositoryOwner) -> _GitContextBinding:
        context = _private_git_context
        if context is not None and not context.matches(owner, owner.basetemp):
            context = None
        return cls(owner, owner.factory, owner.basetemp, context)

    def current(self) -> object:
        context = _private_git_context
        if context is not None and not context.matches(_owner, self.root):
            context = None
        if (
            _owner is not self.owner
            or self.owner.factory is not self.factory
            or self.owner.basetemp != self.root
            or not self.owner.contains(self.root)
            or context is not self.context
        ):
            raise _Ineligible(IneligibleReason.INPUT_CHANGED)
        return _git_context_fact()


def register_owner(factory: pytest.TempPathFactory) -> RepositoryOwner:
    global _owner
    token = RepositoryOwner(factory, factory.getbasetemp())
    _owner = token
    return token


def unregister_owner(token: RepositoryOwner) -> None:
    global _owner
    if _owner is token:
        _owner = None


def populate_or_copy(
    path: Path,
    *,
    project_root: Path,
    repository_id: str,
    populate: Populate,
    run_git: Git,
    standard_helpers: bool,
) -> Path:
    """The caller has performed the original mkdir; original failures propagate."""
    token = _owner
    if token is None or token.disabled or not standard_helpers or not _standard_io():
        return populate(path)
    if not token.contains(path):
        return populate(path)
    sources = None
    warm = False
    try:
        sources = _source_fact(project_root)
        _environment_fact()
        if token.snapshot is not None and token.qualification is not None:
            current = token.qualification.current(project_root, repository_id)
            snapshot_valid = _digest(_path_fact(token.snapshot)) == token.snapshot_sha256
            mode_valid = stat.S_IMODE(_ordinary(path).st_mode) == stat.S_IMODE(
                _ordinary(token.snapshot).st_mode
            )
            if current == token.qualification.inputs_sha256 and snapshot_valid and mode_valid:
                warm = True
    except Exception:
        pass
    if warm:
        # Deliberately outside the qualification handler: an actual copy error
        # preserves its partial destination and never retries the builder.
        assert token.snapshot is not None
        token.hits += 1
        return _copy_snapshot(token.snapshot, path)
    token.cold += 1
    result = populate(path)
    if token.snapshot is not None or sources is None:
        return result
    stage = IneligibleReason.QUALIFICATION_FAILED
    try:
        qualification = _qualify(path, project_root, repository_id, run_git, owner=token)
        if _source_fact(project_root) != sources:
            raise _Ineligible(IneligibleReason.INPUT_CHANGED)
        snapshot = token.factory.mktemp("b")
        stage = IneligibleReason.PUBLICATION_FAILED
        _copy_snapshot(path, snapshot)
        if qualification.current(project_root, repository_id) != qualification.inputs_sha256:
            raise _Ineligible(IneligibleReason.INPUT_CHANGED)
        if _source_fact(snapshot) != sources:
            raise _Ineligible()
        snapshot_digest = _digest(_path_fact(snapshot))
        if snapshot_digest != _digest(_path_fact(path)):
            raise _Ineligible()
        token.snapshot = snapshot
        token.snapshot_sha256 = snapshot_digest
        token.qualification = qualification
    except _Ineligible as error:
        token.disabled = True
        token.reason = error.reason
    except Exception:
        # Original repository is already successful. Do not expose optional
        # qualification details or replace its success with publication failure.
        token.disabled = True
        token.reason = stage
    return result


def _copy_snapshot(source: Path, target: Path) -> Path:
    try:
        parallel = _parallel_copy_eligible(source, target)
    except Exception:
        # Optional prewrite reads may fail; preserve the original serial copy.
        # KeyboardInterrupt and other BaseException values are not eligibility.
        parallel = False
    if parallel:
        _parallel_copy_snapshot(source, target)
    else:
        shutil.copytree(
            source, target, copy_function=shutil.copy2, dirs_exist_ok=True, symlinks=False
        )
    return target


def _parallel_bindings_known() -> bool:
    return (
        _standard_io()
        and shutil.copystat is _COPYSTAT
        and os.scandir is _SCANDIR
        and os.makedirs is _MAKEDIRS
        and sys.audit is _AUDIT
        and ThreadPoolExecutor is _EXECUTOR
        and ThreadPoolExecutor.__init__ is _EXECUTOR_INIT
        and ThreadPoolExecutor.submit is _EXECUTOR_SUBMIT
        and ThreadPoolExecutor.shutdown is _EXECUTOR_SHUTDOWN
        and ThreadPoolExecutor._adjust_thread_count is _EXECUTOR_ADJUST
        and threading.Thread is _THREAD
        and threading.Thread.start is _THREAD_START
        and threading.Thread.join is _THREAD_JOIN
        and Future.result is _FUTURE_RESULT
        and Future.exception is _FUTURE_EXCEPTION
        and Future.done is _FUTURE_DONE
        and Future.cancelled is _FUTURE_CANCELLED
        and _owned_protocol_known()
    )


def _parallel_entry_metadata(entry: os.DirEntry[str]) -> os.stat_result:
    metadata = entry.stat(follow_symlinks=False)
    if (
        stat.S_ISLNK(metadata.st_mode)
        or getattr(metadata, "st_file_attributes", 0) & 0x400
        or not (stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode))
    ):
        raise RuntimeError("REPOSITORY_FIXTURE_COPY_UNSAFE")
    return metadata


def _parallel_tree_count(source: Path) -> int:
    if not stat.S_ISDIR(_ordinary(source).st_mode):
        raise _Ineligible()
    with os.scandir(source) as iterator:
        entries = list(iterator)
    count = 0
    for entry in entries:
        metadata = _parallel_entry_metadata(entry)
        if stat.S_ISDIR(metadata.st_mode):
            count += _parallel_tree_count(Path(entry.path))
        else:
            count += 1
        if count > _PARALLEL_FILE_LIMIT:
            return count
    return count


def _parallel_copy_eligible(source: Path, target: Path) -> bool:
    token = _owner
    if (
        token is None
        or token.disabled
        or token.snapshot != source
        or token.qualification is None
        or not _parallel_bindings_known()
        or not token.contains(source)
        or not token.contains(target)
    ):
        return False
    for path in (source, target):
        for ancestor in reversed(path.absolute().parents):
            _ordinary(ancestor)
        if not stat.S_ISDIR(_ordinary(path).st_mode):
            return False
    with os.scandir(target) as iterator:
        if next(iterator, None) is not None:
            return False
    return _parallel_tree_count(source) <= _PARALLEL_FILE_LIMIT


@dataclass
class _CopyFailure:
    error: BaseException
    traceback: TracebackType | None

    def reraise(self) -> None:
        raise self.error.with_traceback(self.traceback)


def _owned_native_call_offsets() -> tuple[int, ...]:
    """Recognize the supported standard start's actual native-create call."""
    offsets = []
    native_loaded = False
    for instruction in dis.get_instructions(_THREAD_START):
        if instruction.opname == "LOAD_GLOBAL" and instruction.argval == _NATIVE_START_NAME:
            native_loaded = True
        elif native_loaded and instruction.opname in {"CALL", "CALL_KW"}:
            offsets.append(instruction.offset)
            native_loaded = False
    return tuple(offsets)


def _owned_protocol_known() -> bool:
    # Only these actual stdlib protocols were reviewed. Unknown implementations
    # select the original serial builder before any destination write.
    return (
        sys.version_info[:2] in {(3, 11), (3, 13)}
        and sys.implementation.name == "cpython"
        and threading.Thread is _THREAD
        and threading.Thread.__init__ is _THREAD_INIT
        and threading.Thread.start is _THREAD_START
        and threading.Thread.join is _THREAD_JOIN
        and threading.Thread.run is _THREAD_RUN
        and getattr(threading.Thread, "_bootstrap", None) is _THREAD_BOOTSTRAP
        and getattr(threading.Thread, "_bootstrap_inner", None) is _THREAD_BOOTSTRAP_INNER
        and threading.Event is _EVENT
        and threading.Event.wait is _EVENT_WAIT
        and threading.Event.set is _EVENT_SET
        and threading.Event.is_set is _EVENT_IS_SET
        and getattr(threading, "_active_limbo_lock", None) is _LIMBO_LOCK
        and getattr(threading, _NATIVE_START_NAME, None) is _NATIVE_START
        and type(_NATIVE_START) is BuiltinFunctionType
        and getattr(_NATIVE_START, "__module__", None) == "_thread"
        and getattr(threading, "_set_sentinel", None) is _SET_SENTINEL
        and getattr(futures_thread, "_worker", None) is _POOL_WORKER
        and getattr(getattr(_POOL_WORKER, "__code__", None), "co_argcount", None) == 4
        and getattr(futures_thread, "_threads_queues", None) is _POOL_THREAD_QUEUES
        and weakref.ref is _WEAKREF
        and len(_owned_native_call_offsets()) == 1
        and (
            sys.version_info[:2] == (3, 11)
            or (
                getattr(threading, "_ThreadHandle", None) is _THREAD_HANDLE
                and getattr(_THREAD_HANDLE, "join", None) is _HANDLE_JOIN
                and getattr(_THREAD_HANDLE, "is_done", None) is _HANDLE_IS_DONE
            )
        )
    )


@dataclass
class _OwnedWorker:
    thread: Any
    worker_done: threading.Event
    handle: Any
    start_attempted: bool = False
    not_started: bool = False
    terminal: bool = False
    terminal_unknown: bool = False
    startup_failure: _CopyFailure | None = None
    native_create_eligible: bool = False
    cleanup_failure: _CopyFailure | None = None


def _owned_native_creation_failed(record: _OwnedWorker, error: BaseException) -> bool:
    """Do not infer non-start from an arbitrary exception or an absent limbo entry."""
    thread = record.thread
    if (
        not isinstance(error, Exception)
        or not record.native_create_eligible
        or not _owned_protocol_known()
        or type(thread) is not _THREAD
        or type(getattr(thread, "_started")) is not _EVENT
        or not getattr(thread, "_initialized")
        or getattr(getattr(thread, "_bootstrap"), "__func__", None) is not _THREAD_BOOTSTRAP
        or getattr(thread, "_started").is_set()
        or thread.ident is not None
    ):
        return False
    offsets = _owned_native_call_offsets()
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code is _THREAD_START.__code__ and traceback.tb_lasti in offsets:
            # Under the recognized, unchanged native primitive, this is the
            # native-create Exception branch whose standard except cleanup
            # removed this exact fresh Thread from limbo. Other call sites,
            # custom creators and BaseException cannot authorize this proof.
            with _LIMBO_LOCK:
                return thread not in getattr(threading, "_limbo")
        traceback = traceback.tb_next
    return False


def _owned_worker_body(record: _OwnedWorker, arguments: tuple[Any, Any, Any, Any]) -> None:
    try:
        _POOL_WORKER(*arguments)
    finally:
        # BODY completion only. Bootstrap/native teardown still follows.
        record.worker_done.set()


class _OwnedCopyExecutor(ThreadPoolExecutor):
    """Retain every actual Thread before start, including failed registration."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.owned_workers: list[_OwnedWorker] = []

    def _adjust_thread_count(self) -> None:
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_callback(_: object, work_queue: Any = self._work_queue) -> None:
            work_queue.put(None)

        number = len(self.owned_workers)
        if number >= self._max_workers:
            return
        arguments = (
            weakref.ref(self, weakref_callback),
            self._work_queue,
            self._initializer,
            self._initargs,
        )
        done = threading.Event()
        # The closure is not run until start; its record is retained first.
        thread: Any = threading.Thread(
            name=f"{self._thread_name_prefix or self}_{number}",
            target=lambda: _owned_worker_body(record, arguments),
        )
        record = _OwnedWorker(thread, done, getattr(thread, "_handle", None))
        self.owned_workers.append(record)
        try:
            record.native_create_eligible = (
                _owned_protocol_known()
                and type(thread) is _THREAD
                and type(getattr(thread, "_started", None)) is _EVENT
                and getattr(getattr(thread, "_bootstrap"), "__func__", None) is _THREAD_BOOTSTRAP
                and not getattr(thread, "_started").is_set()
                and thread.ident is None
            )
            record.start_attempted = True
            thread.start()
        except BaseException as error:
            record.startup_failure = _CopyFailure(error, error.__traceback__)
            try:
                record.not_started = _owned_native_creation_failed(record, error)
            except BaseException:
                # The original startup exception remains selected; missing
                # negative proof leaves ownership unresolved, never guessed.
                pass
            raise
        cast(Any, self._threads).add(thread)
        _POOL_THREAD_QUEUES[thread] = self._work_queue


def _owned_hold_unknown(record: _OwnedWorker) -> None:
    record.terminal_unknown = True
    unresolved = threading.Event()
    while True:
        try:
            unresolved.wait()
        except BaseException:
            # No native terminal evidence exists here. Preserve actual partial
            # and the selected exception until the original outer process
            # deadline recovers this owned process. No thread deadline is added.
            continue


def _owned_finish_worker(record: _OwnedWorker) -> _CopyFailure | None:
    if record.terminal_unknown:
        _owned_hold_unknown(record)
    if record.terminal:
        return record.cleanup_failure
    if not record.start_attempted or record.not_started:
        record.terminal = True
        return None
    while True:
        try:
            record.thread._started.wait()
            record.worker_done.wait()
            break
        except BaseException as error:
            if record.cleanup_failure is None:
                record.cleanup_failure = _CopyFailure(error, error.__traceback__)
    try:
        if sys.version_info[:2] == (3, 13) and record.thread._handle is not record.handle:
            _owned_hold_unknown(record)
        record.thread.join()
        record.terminal = True
    except BaseException as error:
        if record.cleanup_failure is None:
            record.cleanup_failure = _CopyFailure(error, error.__traceback__)
        if (
            sys.version_info[:2] != (3, 13)
            or record.handle is None
            or type(record.handle) is not _THREAD_HANDLE
            or getattr(type(record.handle), "join", None) is not _HANDLE_JOIN
            or getattr(type(record.handle), "is_done", None) is not _HANDLE_IS_DONE
        ):
            # 3.11 join may release the still-live sentinel and falsely _stop
            # the Thread. Later join/is_alive/Done can never clear this latch.
            _owned_hold_unknown(record)
        while True:
            try:
                _HANDLE_JOIN(record.handle)
                if _HANDLE_IS_DONE(record.handle):
                    record.terminal = True
                    break
            except BaseException:
                # Wait the retained real handle, preserving the first failure.
                continue
    return record.cleanup_failure


@dataclass
class _CopyJob:
    entry: os.DirEntry[str]
    source_name: str
    target_name: str
    future: Future[None] | None = None
    failure: _CopyFailure | None = None
    consumed: bool = False


@dataclass
class _ParallelCopy:
    executor: _OwnedCopyExecutor
    copy_file: Callable[[os.DirEntry[str], str], object]
    jobs: list[_CopyJob] = field(default_factory=list)
    submission_failed: bool = False
    cleanup_failure: _CopyFailure | None = None


def _parallel_file_job(job: _CopyJob, copy_file: Callable[[os.DirEntry[str], str], object]) -> None:
    try:
        copy_file(job.entry, job.target_name)
    except BaseException as error:
        # Keep the original object, including a worker BaseException, while the
        # coordinator completes every submitted job before logical attribution.
        if job.failure is None:
            job.failure = _CopyFailure(error, error.__traceback__)


def _parallel_append_error(
    errors: list[tuple[object, object, str]],
    error: BaseException,
    source: object,
    target: object,
) -> None:
    # Error subclasses OSError: list expansion must win over an OS triple.
    if isinstance(error, shutil.Error):
        errors.extend(error.args[0])
    elif isinstance(error, OSError):
        errors.append((source, target, str(error)))
    else:
        raise error


def _parallel_complete_batch(
    pending: list[_CopyJob], errors: list[tuple[object, object, str]]
) -> tuple[_CopyFailure | None, _CopyFailure | None]:
    interruption = None
    for job in pending:
        if job.future is None:
            continue
        while True:
            try:
                job.future.result()
                break
            except BaseException as error:
                # File exceptions are normally stored by the job wrapper. A
                # Future's own stored failure is distinct from an interruption
                # delivered to the coordinator while result() is waiting.
                if interruption is None:
                    interruption = _CopyFailure(error, error.__traceback__)
                try:
                    cancelled = job.future.cancelled()
                    stored = job.future.exception() if job.future.done() and not cancelled else None
                except BaseException:
                    # result() already supplied the selected interruption. A
                    # later metadata observation must not replace that object.
                    continue
                if cancelled or stored is not None:
                    if job.failure is None:
                        original = error if cancelled else stored
                        assert original is not None
                        job.failure = _CopyFailure(original, original.__traceback__)
                    if interruption.error is (error if cancelled else stored):
                        interruption = None
                    break
    failure = None
    try:
        for job in pending:
            if job.failure is not None:
                try:
                    _parallel_append_error(
                        errors, job.failure.error, job.source_name, job.target_name
                    )
                except BaseException as error:
                    failure = _CopyFailure(error, error.__traceback__)
                    break
    finally:
        for job in pending:
            job.consumed = True
        pending.clear()
    return failure, interruption


def _parallel_drain_batch(
    pending: list[_CopyJob], errors: list[tuple[object, object, str]]
) -> None:
    failure, interruption = _parallel_complete_batch(pending, errors)
    if failure is not None:
        failure.reraise()
    if interruption is not None:
        interruption.reraise()


def _parallel_copy_directory(
    source: Path | os.DirEntry[str], target: Path | str, state: _ParallelCopy
) -> None:
    sys.audit("shutil.copytree", source, target)
    if not stat.S_ISDIR(_ordinary(Path(os.fspath(source))).st_mode):
        raise RuntimeError("REPOSITORY_FIXTURE_COPY_UNSAFE")
    with os.scandir(source) as iterator:
        entries = list(iterator)
    os.makedirs(target, exist_ok=True)
    if not stat.S_ISDIR(_ordinary(Path(target)).st_mode):
        raise RuntimeError("REPOSITORY_FIXTURE_COPY_UNSAFE")
    errors: list[tuple[object, object, str]] = []
    pending: list[_CopyJob] = []
    for entry in entries:
        try:
            source_name = os.path.join(source, entry.name)
            target_name = os.path.join(target, entry.name)
        except BaseException:
            _parallel_drain_batch(pending, errors)
            raise
        try:
            metadata = _parallel_entry_metadata(entry)
            if stat.S_ISDIR(metadata.st_mode):
                _parallel_drain_batch(pending, errors)
                _parallel_copy_directory(entry, target_name, state)
                continue
        except BaseException as error:
            _parallel_drain_batch(pending, errors)
            _parallel_append_error(errors, error, source_name, target_name)
            continue
        if len(state.jobs) >= _PARALLEL_FILE_LIMIT:
            _parallel_drain_batch(pending, errors)
            raise RuntimeError("REPOSITORY_FIXTURE_COPY_LIMIT")
        job = _CopyJob(entry, source_name, target_name)
        # Retain the slot before submit: standard submit queues its WorkItem
        # before attempting to start a thread and may then return no Future.
        state.jobs.append(job)
        try:
            job.future = state.executor.submit(_parallel_file_job, job, state.copy_file)
        except BaseException as error:
            state.submission_failed = True
            job.failure = _CopyFailure(error, error.__traceback__)
            job.consumed = True
            _parallel_drain_batch(pending, errors)
            # Executor submission is a coordinator failure, not a file-copy OS
            # triple. Keep its exact object; final shutdown also joins a queued
            # job which an existing worker may already have started.
            raise
        pending.append(job)
    _parallel_drain_batch(pending, errors)
    try:
        shutil.copystat(source, target)
    except OSError as error:
        if getattr(error, "winerror", None) is None:
            errors.append((source, target, str(error)))
    if errors:
        raise shutil.Error(errors)


def _parallel_shutdown(state: _ParallelCopy) -> _CopyFailure | None:
    while True:
        try:
            # Publish the sentinel/cancel only still-pending jobs. Standard
            # shutdown's _threads set misses a start-before-registration fault.
            state.executor.shutdown(wait=False, cancel_futures=state.submission_failed)
            break
        except BaseException as error:
            if state.cleanup_failure is None:
                state.cleanup_failure = _CopyFailure(error, error.__traceback__)
    index = 0
    while index < len(state.executor.owned_workers):
        try:
            worker_failure = _owned_finish_worker(state.executor.owned_workers[index])
        except BaseException as error:
            if state.cleanup_failure is None:
                state.cleanup_failure = _CopyFailure(error, error.__traceback__)
            # An interruption between ownership observations must not skip an
            # actual worker. Unknown/latching branches remain incomplete.
            continue
        if state.cleanup_failure is None:
            state.cleanup_failure = worker_failure
        index += 1
    return state.cleanup_failure


def _parallel_copy_snapshot(
    source: Path,
    target: Path,
    *,
    copy_file: Callable[[os.DirEntry[str], str], object] | None = None,
    executor_factory: Callable[..., _OwnedCopyExecutor] | None = None,
) -> None:
    """Private algorithm seams do not bypass public warm eligibility."""
    factory = _OwnedCopyExecutor if executor_factory is None else executor_factory
    state = _ParallelCopy(
        factory(max_workers=_PARALLEL_WORKERS, thread_name_prefix="aiflow-copy"),
        shutil.copy2 if copy_file is None else copy_file,
    )
    failure = None
    try:
        _parallel_copy_directory(source, target, state)
    except BaseException as error:
        failure = _CopyFailure(error, error.__traceback__)
    while True:
        try:
            _parallel_shutdown(state)
            break
        except BaseException as error:
            if state.cleanup_failure is None:
                state.cleanup_failure = _CopyFailure(error, error.__traceback__)
            # The helper's loop/record bookkeeping can itself be interrupted.
            # Resolved records are reentrant; unresolved/latching records still
            # require actual terminal evidence or original outer recovery.
    shutdown_failure = state.cleanup_failure
    # Normally batches were consumed by the walker. An unexpected coordinator
    # failure may leave earlier slots: after shutdown, their logical fatal wins
    # over that later failure, while their OS list does not mask it.
    try:
        remaining = [job for job in state.jobs if not job.consumed]
        earlier_failure, late_interruption = _parallel_complete_batch(remaining, [])
    except BaseException as error:
        # Workers already joined. A later final-drain observation must not
        # replace the selected walk/shutdown failure or become false success.
        if failure is None:
            failure = shutdown_failure or _CopyFailure(error, error.__traceback__)
    else:
        if earlier_failure is not None:
            failure = earlier_failure
        if failure is None:
            failure = shutdown_failure or late_interruption
    if failure is not None:
        failure.reraise()
