"""Temporary-root boundaries using owned files and short, local operations only."""

from __future__ import annotations

import os
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiflow import verification_temporary as temporary
from aiflow.errors import ContractError


def parent_directory(tmp_path: Path) -> Path:
    parent = tmp_path / "fixture roots β"
    parent.mkdir()
    return parent


def plan(parent: Path, run_id: str = "run-001") -> temporary.PytestTemporaryLayout:
    return temporary.plan_pytest_temporary(parent, "TASK-0056", run_id, ("EXEC-001", "EXEC-002"))


def argv(
    layout: temporary.PytestTemporaryLayout, execution_id: str = "EXEC-001"
) -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        "pytest",
        "tests/unit",
        "-q",
        f"--basetemp={layout.leaves[execution_id].as_posix()}",
    )


def test_validation_and_plan_are_read_only_and_layout_is_immutable(tmp_path: Path) -> None:
    parent = parent_directory(tmp_path)
    sentinel = parent / "preserved.txt"
    sentinel.write_bytes(b"keep\x00bytes")
    before = tuple(parent.iterdir())
    assert temporary.validate_pytest_temp_root(parent) == parent
    layout = plan(parent)
    assert tuple(parent.iterdir()) == before
    assert sentinel.read_bytes() == b"keep\x00bytes"
    assert not layout.container.exists()
    assert layout.container.parent == parent
    assert layout.container_identity is None
    assert tuple(layout.leaves) == ("EXEC-001", "EXEC-002")
    with pytest.raises(TypeError):
        layout.leaves["EXEC-003"] = parent  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        layout.parent = tmp_path  # type: ignore[misc]


def test_create_claims_only_container_and_leaves_are_never_reused(tmp_path: Path) -> None:
    parent = parent_directory(tmp_path)
    original = plan(parent)
    prepared = temporary.create_pytest_temporary(original)
    assert original.container_identity is None
    assert prepared.container_identity is not None
    assert prepared.container.is_dir()
    assert list(prepared.container.iterdir()) == []
    temporary.validate_pytest_temporary(prepared, "EXEC-001", argv(prepared))
    first = prepared.leaves["EXEC-001"]
    first.mkdir()
    (first / "failed-test.txt").write_bytes(b"retain failed fixture")
    temporary.validate_pytest_temporary(prepared, "EXEC-002", argv(prepared, "EXEC-002"))
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temporary(prepared, "EXEC-001", argv(prepared))
    assert error.value.code == "PYTEST_TEMP_DIRECTORY_CONFLICT"
    assert (first / "failed-test.txt").read_bytes() == b"retain failed fixture"
    with pytest.raises(ContractError):
        temporary.create_pytest_temporary(prepared)


def test_new_runs_have_separate_paths_and_empty_execution_plan_creates_nothing(
    tmp_path: Path,
) -> None:
    parent = parent_directory(tmp_path)
    first = plan(parent)
    second = plan(parent, "run-002")
    assert first.container != second.container
    assert set(first.leaves.values()).isdisjoint(second.leaves.values())
    empty = temporary.plan_pytest_temporary(parent, "TASK-0056", "run-empty", ())
    with pytest.raises(ContractError):
        temporary.create_pytest_temporary(empty)
    assert list(parent.iterdir()) == []


@pytest.mark.parametrize("kind", ["relative", "missing", "file", "traversal"])
def test_invalid_parent_refusal_preserves_existing_content(tmp_path: Path, kind: str) -> None:
    parent = parent_directory(tmp_path)
    file = parent / "private-secret-file"
    file.write_bytes(b"original")
    supplied = {
        "relative": Path("relative-root"),
        "missing": parent / "missing",
        "file": file,
        "traversal": parent / ".." / parent.name,
    }[kind]
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temp_root(supplied)
    assert error.value.code == "PYTEST_TEMP_ROOT_INVALID"
    assert "private-secret-file" not in str(error.value.to_dict())
    assert file.read_bytes() == b"original"
    assert tuple(parent.iterdir()) == (file,)


@pytest.mark.parametrize(
    "name",
    ["CON", "nul.txt", "COM¹", "LPT².log", "CONIN$", "bad:stream", "tail.", "tail ", "bad\x01"],
)
def test_unsafe_lexical_names_refuse_before_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    calls: list[Path] = []

    def metadata(path: Path) -> os.stat_result:
        calls.append(path)
        raise AssertionError("unsafe path reached metadata")

    monkeypatch.setattr(temporary, "_lstat", metadata)
    with pytest.raises(ContractError):
        temporary.validate_pytest_temp_root(tmp_path / name)
    assert not calls


@pytest.mark.parametrize(
    "path", ["//never-contact.invalid/share", r"\\?\C:\fixture", r"\\.\C:\fixture"]
)
def test_unc_and_device_namespaces_refuse_without_metadata_or_drive_probe(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    def unexpected(_path: Path) -> int:
        raise AssertionError("unsafe path reached filesystem")

    monkeypatch.setattr(temporary, "_WINDOWS", True)
    monkeypatch.setattr(temporary, "_drive_type", unexpected)
    monkeypatch.setattr(temporary, "_lstat", unexpected)
    with pytest.raises(ContractError):
        temporary.validate_pytest_temp_root(Path(path))


@pytest.mark.parametrize("drive_type", [0, 1, 4])
def test_nonlocal_windows_drive_types_refuse_before_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drive_type: int
) -> None:
    monkeypatch.setattr(temporary, "_WINDOWS", True)
    monkeypatch.setattr(temporary, "_drive_type", lambda _path: drive_type)
    monkeypatch.setattr(temporary, "_lstat", lambda _path: pytest.fail("metadata must not run"))
    with pytest.raises(ContractError):
        temporary.validate_pytest_temp_root(tmp_path)


def test_portable_path_branch_avoids_windows_drive_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = parent_directory(tmp_path)
    monkeypatch.setattr(temporary, "_WINDOWS", False)
    monkeypatch.setattr(temporary, "_drive_type", lambda _path: pytest.fail("Windows-only probe"))
    assert temporary.validate_pytest_temp_root(parent) == parent


@pytest.mark.parametrize("marker", ["git_file", "git_directory", "bare_objects", "bare_commondir"])
def test_ancestor_repository_markers_are_rejected_without_reading_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marker: str
) -> None:
    ancestor = tmp_path / "marked-ancestor"
    ancestor.mkdir()
    parent = ancestor / "child"
    parent.mkdir()
    if marker == "git_file":
        (ancestor / ".git").write_text("gitdir: never-read\n", encoding="utf-8")
    elif marker == "git_directory":
        (ancestor / ".git").mkdir()
    else:
        (ancestor / "HEAD").write_bytes(b"not read")
        if marker == "bare_objects":
            (ancestor / "objects").mkdir()
        else:
            (ancestor / "commondir").write_bytes(b"never read")
    monkeypatch.setattr(Path, "read_bytes", lambda _path: pytest.fail("marker content read"))
    with pytest.raises(ContractError):
        temporary.validate_pytest_temp_root(parent)
    assert list(parent.iterdir()) == []


def test_real_directory_symlink_and_dangling_git_marker_are_not_followed(tmp_path: Path) -> None:
    target = parent_directory(tmp_path)
    link = tmp_path / "parent-link"
    marker = target / ".git"
    try:
        link.symlink_to(target, target_is_directory=True)
        marker.symlink_to(tmp_path / "missing-git-marker")
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ContractError):
        temporary.validate_pytest_temp_root(link)
    with pytest.raises(ContractError):
        temporary.validate_pytest_temp_root(target)
    assert marker.is_symlink()
    assert list(target.iterdir()) == [marker]


def test_reparse_attribute_rejects_before_descendant_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = parent_directory(tmp_path)
    original = temporary._lstat
    calls: list[Path] = []

    def metadata(path: Path) -> os.stat_result:
        calls.append(path)
        if path == tmp_path:
            return SimpleNamespace(  # type: ignore[return-value]
                st_mode=stat.S_IFDIR, st_dev=1, st_ino=1, st_file_attributes=1024
            )
        return original(path)

    monkeypatch.setattr(temporary, "_lstat", metadata)
    with pytest.raises(ContractError):
        temporary.validate_pytest_temp_root(parent)
    assert parent not in calls
    assert tmp_path / ".git" not in calls


@pytest.mark.parametrize(
    "identifier", [".", "..", "run.", "NUL", "a/b", "a\\b", "tail ", "run\x00"]
)
def test_unsafe_run_identity_is_rejected_without_allocating(
    tmp_path: Path, identifier: str
) -> None:
    parent = parent_directory(tmp_path)
    with pytest.raises(ContractError):
        plan(parent, identifier)
    assert list(parent.iterdir()) == []


@pytest.mark.parametrize(
    "identifiers", [("EXEC-001", "EXEC-001"), ("../escape",), ("CON",), ("EXEC-" + "9" * 255,)]
)
def test_invalid_execution_identity_is_rejected_without_allocating(
    tmp_path: Path, identifiers: tuple[str, ...]
) -> None:
    parent = parent_directory(tmp_path)
    with pytest.raises(ContractError):
        temporary.plan_pytest_temporary(parent, "TASK-0056", "run-001", identifiers)
    assert list(parent.iterdir()) == []


def test_existing_container_and_create_race_preserve_competitor_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = parent_directory(tmp_path)
    layout = plan(parent)
    original = temporary._mkdir_container

    def competitor(path: Path) -> None:
        path.mkdir()
        (path / "competitor.txt").write_bytes(b"do not overwrite")
        original(path)

    monkeypatch.setattr(temporary, "_mkdir_container", competitor)
    with pytest.raises(ContractError) as error:
        temporary.create_pytest_temporary(layout)
    assert error.value.code == "PYTEST_TEMP_DIRECTORY_CONFLICT"
    assert (layout.container / "competitor.txt").read_bytes() == b"do not overwrite"
    with pytest.raises(ContractError):
        plan(parent)


def test_two_creators_cannot_both_claim_a_container(tmp_path: Path) -> None:
    layout = plan(parent_directory(tmp_path))

    def attempt() -> temporary.PytestTemporaryLayout | ContractError:
        try:
            return temporary.create_pytest_temporary(layout)
        except ContractError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: attempt(), range(2)))
    assert sum(isinstance(result, temporary.PytestTemporaryLayout) for result in results) == 1
    assert sum(isinstance(result, ContractError) for result in results) == 1
    assert list(layout.container.iterdir()) == []


def test_replaced_parent_or_container_is_detected_and_not_cleaned(tmp_path: Path) -> None:
    parent = parent_directory(tmp_path)
    layout = plan(parent)
    retained_parent = tmp_path / "old-parent"
    parent.rename(retained_parent)
    parent.mkdir()
    with pytest.raises(ContractError) as error:
        temporary.create_pytest_temporary(layout)
    assert error.value.code == "PYTEST_TEMP_IDENTITY_CHANGED"
    assert not layout.container.exists()
    prepared = temporary.create_pytest_temporary(plan(parent, "run-002"))
    retained_container = parent / "retained-container"
    prepared.container.rename(retained_container)
    prepared.container.mkdir()
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temporary(prepared, "EXEC-001", argv(prepared))
    assert error.value.code == "PYTEST_TEMP_IDENTITY_CHANGED"
    assert retained_parent.is_dir()
    assert retained_container.is_dir()
    assert list(prepared.container.iterdir()) == []


def test_marker_added_after_planning_or_preparation_is_rejected(tmp_path: Path) -> None:
    parent = parent_directory(tmp_path)
    layout = plan(parent)
    (parent / ".git").write_bytes(b"do not read")
    with pytest.raises(ContractError):
        temporary.create_pytest_temporary(layout)
    assert not layout.container.exists()
    sibling = tmp_path / "other-root"
    sibling.mkdir()
    prepared = temporary.create_pytest_temporary(plan(sibling))
    (sibling / "HEAD").write_bytes(b"bare marker")
    (sibling / "commondir").write_bytes(b"not a path to follow")
    with pytest.raises(ContractError):
        temporary.validate_pytest_temporary(prepared, "EXEC-001", argv(prepared))
    assert list(prepared.container.iterdir()) == []


@pytest.mark.parametrize(
    "mode", ["missing", "duplicate", "split", "not_last", "wrong_leaf", "wrong_module"]
)
def test_invalid_basetemp_argv_is_refused_without_fixture_creation(
    tmp_path: Path, mode: str
) -> None:
    prepared = temporary.create_pytest_temporary(plan(parent_directory(tmp_path)))
    valid = argv(prepared)
    supplied = {
        "missing": valid[:-1],
        "duplicate": (*valid[:-1], valid[-1], valid[-1]),
        "split": (*valid[:-1], "--basetemp", prepared.parent.as_posix(), valid[-1]),
        "not_last": (*valid, "-q"),
        "wrong_leaf": (*valid[:-1], f"--basetemp={prepared.parent.as_posix()}"),
        "wrong_module": (sys.executable, "-m", "aiflow", valid[-1]),
    }[mode]
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temporary(prepared, "EXEC-001", supplied)
    assert error.value.code == "PYTEST_TEMP_ARGUMENT_INVALID"
    assert list(prepared.container.iterdir()) == []


def test_forged_layout_cannot_escape_parent_or_omit_ancestor_binding(tmp_path: Path) -> None:
    parent = parent_directory(tmp_path)
    layout = plan(parent)
    for forged in (
        replace(layout, container=tmp_path / "outside"),
        replace(layout, container=parent / "aiflow-pytest-TASK-0056-NUL"),
        replace(layout, leaves={"EXEC-001": tmp_path / "outside"}),
        replace(layout, parent_identity_chain=layout.parent_identity_chain[-1:]),
    ):
        with pytest.raises(ContractError):
            temporary.create_pytest_temporary(forged)
    assert list(parent.iterdir()) == []


def test_filesystem_failure_does_not_echo_private_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = parent_directory(tmp_path)
    layout = plan(parent)

    def denied(_path: Path) -> None:
        raise PermissionError("synthetic private-secret-path")

    monkeypatch.setattr(temporary, "_mkdir_container", denied)
    with pytest.raises(ContractError) as error:
        temporary.create_pytest_temporary(layout)
    assert "private-secret-path" not in str(error.value.to_dict())
    assert error.value.__suppress_context__ is True
    assert not layout.container.exists()


@pytest.mark.parametrize("marker", ["git_file", "git_directory", "bare_objects", "bare_commondir"])
def test_container_repository_markers_refuse_before_any_leaf_is_used(
    tmp_path: Path, marker: str
) -> None:
    prepared = temporary.create_pytest_temporary(plan(parent_directory(tmp_path)))
    container = prepared.container
    sentinel = container / "retained.txt"
    sentinel.write_bytes(b"existing content")
    if marker == "git_file":
        (container / ".git").write_bytes(b"do not read")
    elif marker == "git_directory":
        (container / ".git").mkdir()
    else:
        (container / "HEAD").write_bytes(b"do not read")
        (container / ("objects" if marker == "bare_objects" else "commondir")).mkdir()
    with pytest.raises(ContractError):
        temporary.validate_pytest_temporary(prepared, "EXEC-001", argv(prepared))
    assert sentinel.read_bytes() == b"existing content"
    assert not prepared.leaves["EXEC-001"].exists()


def test_leaf_appearing_during_final_identity_check_is_not_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = temporary.create_pytest_temporary(plan(parent_directory(tmp_path)))
    original = temporary._assert_parent_identity
    calls = 0
    leaf = prepared.leaves["EXEC-001"]

    def identity(layout: temporary.PytestTemporaryLayout) -> None:
        nonlocal calls
        original(layout)
        calls += 1
        if calls == 2:
            leaf.mkdir()
            (leaf / "late-owner.txt").write_bytes(b"preserved")

    monkeypatch.setattr(temporary, "_assert_parent_identity", identity)
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temporary(prepared, "EXEC-001", argv(prepared))
    assert error.value.code == "PYTEST_TEMP_DIRECTORY_CONFLICT"
    assert (leaf / "late-owner.txt").read_bytes() == b"preserved"


@pytest.mark.parametrize("kind", ["directory_error", "marker_error", "unknown_identity"])
def test_unavailable_metadata_cannot_become_a_valid_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    parent = parent_directory(tmp_path)
    original = temporary._lstat

    def metadata(path: Path) -> os.stat_result:
        if path == parent and kind == "directory_error":
            raise PermissionError("synthetic private path")
        if path == parent / ".git" and kind == "marker_error":
            raise PermissionError("synthetic private marker")
        if path == parent and kind == "unknown_identity":
            return SimpleNamespace(  # type: ignore[return-value]
                st_mode=stat.S_IFDIR, st_dev=1, st_ino=0, st_file_attributes=0
            )
        return original(path)

    monkeypatch.setattr(temporary, "_lstat", metadata)
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temp_root(parent)
    assert "private" not in str(error.value.to_dict())
    assert list(parent.iterdir()) == []


def test_long_ordinary_root_uses_local_metadata_and_preserves_basetemp_binding(
    tmp_path: Path,
) -> None:
    parent = tmp_path
    for number in range(6):
        parent = parent / f"segment-{number}-{'x' * 32}"
        physical = Path("\\\\?\\" + str(parent)) if os.name == "nt" else parent
        physical.mkdir()
    prepared = temporary.create_pytest_temporary(plan(parent))
    temporary.validate_pytest_temporary(prepared, "EXEC-001", argv(prepared))
    assert not temporary._io_path(prepared.leaves["EXEC-001"]).exists()


def simulated_alias(monkeypatch: pytest.MonkeyPatch, logical: Path, physical: Path) -> None:
    """Model read-only alias resolution and identity, without creating OS mappings."""
    metadata = temporary._lstat
    monkeypatch.setattr(temporary, "_resolve_parent", lambda _path: physical)
    monkeypatch.setattr(
        temporary, "_lstat", lambda path: metadata(physical) if path == logical else metadata(path)
    )


def test_safe_alias_plans_and_creates_only_canonical_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logical = parent_directory(tmp_path)
    physical = tmp_path / "physical-root"
    physical.mkdir()
    simulated_alias(monkeypatch, logical, physical)
    assert temporary.validate_pytest_temp_root(logical) == physical
    layout = plan(logical)
    assert layout.parent == physical
    assert layout.container.parent == physical
    assert layout.parent_identity_chain[-1][0] == physical
    assert all(leaf.parent == layout.container for leaf in layout.leaves.values())
    monkeypatch.setattr(
        temporary,
        "_resolve_parent",
        lambda _path: pytest.fail("old alias consulted during execution"),
    )
    prepared = temporary.create_pytest_temporary(layout)
    temporary.validate_pytest_temporary(prepared, "EXEC-001", argv(prepared))
    assert prepared.container.is_dir()
    assert list(logical.iterdir()) == []
    assert physical.as_posix() in argv(prepared)[-1]


@pytest.mark.parametrize("marker", ["git_file", "git_directory", "bare_objects", "bare_commondir"])
def test_alias_cannot_hide_physical_repository_ancestors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marker: str
) -> None:
    logical = parent_directory(tmp_path)
    ancestor = tmp_path / "physical-repository"
    ancestor.mkdir()
    physical = ancestor / "mapped-child"
    physical.mkdir()
    if marker == "git_file":
        (ancestor / ".git").write_bytes(b"not read")
    elif marker == "git_directory":
        (ancestor / ".git").mkdir()
    else:
        (ancestor / "HEAD").write_bytes(b"not read")
        (ancestor / ("objects" if marker == "bare_objects" else "commondir")).mkdir()
    simulated_alias(monkeypatch, logical, physical)
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temp_root(logical)
    assert error.value.code == "PYTEST_TEMP_ROOT_INVALID"
    with pytest.raises(ContractError):
        plan(logical)
    assert list(logical.iterdir()) == []
    assert list(physical.iterdir()) == []


def test_resolver_cannot_bind_a_different_directory_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logical = parent_directory(tmp_path)
    different = tmp_path / "different-root"
    different.mkdir()
    monkeypatch.setattr(temporary, "_resolve_parent", lambda _path: different)
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temp_root(logical)
    assert error.value.code == "PYTEST_TEMP_IDENTITY_CHANGED"
    assert list(logical.iterdir()) == []
    assert list(different.iterdir()) == []


def test_identity_drift_during_resolution_refuses_without_allocating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = parent_directory(tmp_path)
    retained = tmp_path / "retained-original"

    def resolve(path: Path) -> Path:
        path.rename(retained)
        path.mkdir()
        return path

    monkeypatch.setattr(temporary, "_resolve_parent", resolve)
    with pytest.raises(ContractError) as error:
        plan(parent)
    assert error.value.code == "PYTEST_TEMP_IDENTITY_CHANGED"
    assert list(parent.iterdir()) == []
    assert retained.is_dir()


def test_logical_ancestor_drift_with_same_destination_identity_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logical = parent_directory(tmp_path)
    physical = tmp_path / "physical-root"
    physical.mkdir()
    original = temporary._lstat
    resolved = False

    def resolve(_path: Path) -> Path:
        nonlocal resolved
        resolved = True
        return physical

    def metadata(path: Path) -> os.stat_result:
        result = original(physical if path == logical else path)
        if resolved and path == tmp_path:
            return SimpleNamespace(  # type: ignore[return-value]
                st_mode=result.st_mode,
                st_dev=result.st_dev,
                st_ino=result.st_ino + 1,
                st_file_attributes=getattr(result, "st_file_attributes", 0),
            )
        return result

    monkeypatch.setattr(temporary, "_resolve_parent", resolve)
    monkeypatch.setattr(temporary, "_lstat", metadata)
    with pytest.raises(ContractError) as error:
        plan(logical)
    assert error.value.code == "PYTEST_TEMP_IDENTITY_CHANGED"
    assert list(logical.iterdir()) == []
    assert list(physical.iterdir()) == []


@pytest.mark.parametrize(
    "destination",
    [r"\\?\UNC\never-contact.invalid\share", r"\\?\Volume{synthetic}\fixture", r"\\.\C:\fixture"],
)
def test_internal_resolve_does_not_unwrap_nonlocal_or_device_namespaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, destination: str
) -> None:
    parent = parent_directory(tmp_path)
    monkeypatch.setattr(Path, "resolve", lambda _path, *, strict: Path(destination))
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temp_root(parent)
    assert error.value.code == "PYTEST_TEMP_ROOT_INVALID"
    assert list(parent.iterdir()) == []


@pytest.mark.parametrize("mode", ["relative", "namespace", "missing", "error"])
def test_invalid_canonical_destination_or_resolution_error_is_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    parent = parent_directory(tmp_path)

    def resolve(_path: Path) -> Path:
        if mode == "error":
            raise OSError("private-resolution-secret")
        return {
            "relative": Path("relative-root"),
            "namespace": Path(r"\\?\C:\never-query"),
            "missing": tmp_path / "missing-physical-root",
        }[mode]

    monkeypatch.setattr(temporary, "_resolve_parent", resolve)
    with pytest.raises(ContractError) as error:
        temporary.validate_pytest_temp_root(parent)
    assert error.value.code == "PYTEST_TEMP_ROOT_INVALID"
    assert "private-resolution-secret" not in str(error.value.to_dict())
    assert list(parent.iterdir()) == []


def test_logical_symlink_is_rejected_before_canonicalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = parent_directory(tmp_path)
    link = tmp_path / "logical-link"
    try:
        link.symlink_to(parent, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    monkeypatch.setattr(
        temporary, "_resolve_parent", lambda _path: pytest.fail("link reached canonicalizer")
    )
    with pytest.raises(ContractError):
        temporary.validate_pytest_temp_root(link)
    assert list(parent.iterdir()) == []
