"""Session-private copies of a proven, unstarted initial integration repository."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

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
    )


def _template_for(git: Path) -> Path:
    # Only proven conventional layouts qualify; all other installations go cold.
    if os.name == "nt" and git.name.lower() == "git.exe" and git.parent.name.lower() == "cmd":
        template = git.parent.parent / "mingw64" / "share" / "git-core" / "templates"
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
    if os.name == "nt" and git.parent.name.lower() == "cmd":
        files.append(git.parent.parent / "mingw64/bin/git.exe")
    if any(not stat.S_ISREG(_ordinary(path).st_mode) for path in files):
        raise _Ineligible()
    return [[str(path), _path_fact(path)] for path in files]


def _template_fact(template: Path, repository: Path | None = None) -> str:
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
            if repository is not None and _path_fact(source) != _path_fact(
                repository / ".git" / relative
            ):
                raise _Ineligible()
    if repository is not None:
        for name in ("branches", "hooks", "info"):
            expected = template / name
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

    def current(self, project_root: Path, repository_id: str) -> str:
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
                str(self.git),
                _git_fact(self.git),
                [[str(path), _path_fact(path)] for path in self.files],
                [[str(path), _path_fact(path)] for path in self.attributes],
                _template_fact(self.template),
            ]
        )


def _qualify(
    repository: Path, project_root: Path, repository_id: str, run_git: Git
) -> _Qualification:
    executable = shutil.which("git")
    if executable is None:
        raise _Ineligible()
    git = Path(executable).absolute()
    # Check ordinary spelling before resolve: a symlink executable must go cold.
    _ordinary(git)
    template = _template_for(git)
    _template_fact(template, repository)
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
            and git.parent.name.lower() == "cmd"
            and attribute.absolute()
            in {
                git.parent.parent / "etc/gitattributes",
                git.parent.parent / "mingw64/etc/gitattributes",
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
    return _Qualification(qualification.files, qualification.attributes, template, git, current)


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


_owner: RepositoryOwner | None = None


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
        qualification = _qualify(path, project_root, repository_id, run_git)
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
    shutil.copytree(source, target, copy_function=shutil.copy2, dirs_exist_ok=True, symlinks=False)
    return target
