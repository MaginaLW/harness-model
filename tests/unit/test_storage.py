"""Storage boundary tests for task records."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from aiflow.errors import ContractError, StorageError
from aiflow.storage import (
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    reserve_task_id,
    resolve_task_path,
)


def test_domain_error_has_stable_machine_representation() -> None:
    error = StorageError("Could not store task", details={"task_id": "TASK-0001"})

    assert str(error) == "Could not store task"
    assert error.to_dict() == {
        "code": "STORAGE_ERROR",
        "message": "Could not store task",
        "details": {"task_id": "TASK-0001"},
    }


def test_cli_domain_error_does_not_emit_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from aiflow import cli

    class FailingParser:
        def parse_args(self, _argv: object) -> None:
            raise StorageError("Readable storage failure", details={"secret": "not printed"})

    monkeypatch.setattr(cli, "build_parser", FailingParser)

    assert cli.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Readable storage failure\n"
    assert "Traceback" not in captured.err
    assert "not printed" not in captured.err


def test_reserve_first_task_id(tmp_path: Path) -> None:
    assert reserve_task_id(tmp_path) == "TASK-0001"
    assert (tmp_path / ".ai" / "tasks" / "TASK-0001").is_dir()


def test_reserve_scans_existing_ids_and_ignores_invalid_names(tmp_path: Path) -> None:
    tasks = tmp_path / ".ai" / "tasks"
    tasks.mkdir(parents=True)
    for name in ("TASK-0002", "TASK-0010", "TASK-nope", "TASK-1", "notes"):
        (tasks / name).mkdir()

    assert reserve_task_id(tmp_path) == "TASK-0011"


def test_reserve_retries_after_a_competing_creator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import storage

    original = storage._mkdir_reserved_directory
    raced = False

    def compete(path: Path) -> None:
        nonlocal raced
        if not raced:
            raced = True
            path.mkdir()
            raise FileExistsError(path)
        original(path)

    monkeypatch.setattr(storage, "_mkdir_reserved_directory", compete)

    assert reserve_task_id(tmp_path) == "TASK-0002"
    assert (tmp_path / ".ai" / "tasks" / "TASK-0001").is_dir()
    assert (tmp_path / ".ai" / "tasks" / "TASK-0002").is_dir()


def test_reserve_reports_retry_exhaustion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aiflow import storage

    attempts = 0

    def always_compete(_path: Path) -> None:
        nonlocal attempts
        attempts += 1
        raise FileExistsError

    monkeypatch.setattr(storage, "_mkdir_reserved_directory", always_compete)

    with pytest.raises(StorageError, match="concurrent updates") as caught:
        reserve_task_id(tmp_path)

    assert attempts == 10
    assert caught.value.details == {"attempts": 10}


@pytest.mark.parametrize("task_id", ["TASK-1", "task-0001", "TASK-0001/child", "../TASK-0001"])
def test_resolve_rejects_invalid_task_ids(tmp_path: Path, task_id: str) -> None:
    with pytest.raises(StorageError, match="task ID") as caught:
        resolve_task_path(tmp_path, task_id, "task.yaml")

    assert caught.value.code == "STORAGE_INVALID_TASK_ID"


@pytest.mark.parametrize("relative_path", ["../outside.json", Path("nested/../../outside.json")])
def test_resolve_rejects_parent_path_escape(tmp_path: Path, relative_path: str | Path) -> None:
    with pytest.raises(StorageError, match="relative") as caught:
        resolve_task_path(tmp_path, "TASK-0001", relative_path)

    assert caught.value.code == "STORAGE_PATH_ESCAPE"


def test_resolve_rejects_absolute_task_subpath(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="relative"):
        resolve_task_path(tmp_path, "TASK-0001", tmp_path / "outside.json")


def test_resolve_rejects_symlink_escape(tmp_path: Path) -> None:
    task_directory = tmp_path / ".ai" / "tasks" / "TASK-0001"
    outside = tmp_path / "outside"
    task_directory.mkdir(parents=True)
    outside.mkdir()
    link = task_directory / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if os.name != "nt":
            pytest.skip(f"symlink creation unavailable: {error}")
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"junction creation unavailable: {result.stderr}")

    with pytest.raises(StorageError, match="escapes"):
        resolve_task_path(tmp_path, "TASK-0001", "link/value.json")


def test_atomic_json_write_replaces_complete_document(tmp_path: Path) -> None:
    target = tmp_path / "task.json"
    target.write_text('{"old": true}\n', encoding="utf-8")

    atomic_write_json(target, {"new": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"new": True}
    assert not list(tmp_path.glob(f".{target.name}.*.tmp"))


def test_interrupted_atomic_write_preserves_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import storage

    target = tmp_path / "task.yaml"
    original = "old: value\n"
    target.write_text(original, encoding="utf-8")

    def interrupt(_source: Path, _target: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(storage.os, "replace", interrupt)

    with pytest.raises(StorageError, match="atomically") as caught:
        atomic_write_yaml(target, {"new": "value"})

    assert caught.value.code == "STORAGE_WRITE_FAILED"
    assert target.read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob(f".{target.name}.*.tmp"))


@pytest.mark.parametrize(
    ("filename", "content", "reader"),
    [
        ("task.json", "{not-json", read_task_json),
        ("task.yaml", "value: [not-yaml", read_task_yaml),
    ],
)
def test_read_rejects_corrupt_documents(
    tmp_path: Path, filename: str, content: str, reader: object
) -> None:
    path = tmp_path / ".ai" / "tasks" / "TASK-0001" / filename
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")

    with pytest.raises(StorageError, match="parse") as caught:
        reader(tmp_path, "TASK-0001", filename)  # type: ignore[operator]

    assert caught.value.code == "STORAGE_PARSE_FAILED"


def test_read_validates_schema_version_immediately(tmp_path: Path) -> None:
    path = tmp_path / ".ai" / "tasks" / "TASK-0001" / "task.yaml"
    path.parent.mkdir(parents=True)
    atomic_write_yaml(path, {"schema_version": "9.0"})

    with pytest.raises(ContractError) as caught:
        read_task_yaml(tmp_path, "TASK-0001", "task.yaml", contract_name="task")

    assert caught.value.code == "CONTRACT_VALIDATION_FAILED"
