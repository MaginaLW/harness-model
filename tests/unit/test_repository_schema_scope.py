"""Acceptance checks for repository-local, context-scoped contract resources."""

from __future__ import annotations

import json
from contextvars import Context, copy_context
from pathlib import Path
from typing import Any

import pytest

from aiflow import contracts, git_context

SCHEMA_URI = "https://aiflow.local/schemas/decision-unit.schema.json"


def _schemas(directory: Path, marker: str) -> Path:
    directory.mkdir(parents=True)
    common = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
    primary = {
        **common,
        "$id": "https://aiflow.local/schemas/task.schema.json",
        "title": marker,
        "type": "object",
        "required": ["choice"],
        "properties": {"choice": {"$ref": SCHEMA_URI}},
    }
    referenced = {**common, "$id": SCHEMA_URI, "enum": [marker]}
    (directory / "task.schema.json").write_text(json.dumps(primary), encoding="utf-8")
    (directory / "decision-unit.schema.json").write_text(json.dumps(referenced), encoding="utf-8")
    return directory


def _scope(directory: Path) -> Any:
    factory = getattr(contracts, "schema_directory_context", None)
    assert callable(factory), "contracts.schema_directory_context must bind one Schema directory"
    return factory(directory)


def test_existing_library_default_remains_local_and_does_not_discover_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _schemas(tmp_path / ".ai" / "schemas", "default")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        git_context, "_run_git", lambda *_args, **_kwargs: pytest.fail("library Git")
    )

    assert contracts.load_schema("task")["title"] == "default"
    assert contracts.validate_contract("task", {"choice": "default"}) == []
    contracts.require_valid_contract("task", {"choice": "default"})


def test_scope_binds_loading_validation_requirement_and_ref_registry_to_one_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _schemas(tmp_path / ".ai" / "schemas", "invocation")
    selected = _schemas(tmp_path / "repository" / ".ai" / "schemas", "selected")
    monkeypatch.chdir(tmp_path)

    with _scope(selected):
        assert contracts.load_schema("task")["title"] == "selected"
        assert contracts.validate_contract("task", {"choice": "selected"}) == []
        assert contracts.validate_contract("task", {"choice": "invocation"})
        contracts.require_valid_contract("task", {"choice": "selected"})
        with pytest.raises(contracts.ContractValidationError):
            contracts.require_valid_contract("task", {"choice": "invocation"})

    assert contracts.load_schema("task")["title"] == "invocation"


def test_missing_scoped_resources_do_not_fall_back_to_the_callers_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _schemas(tmp_path / ".ai" / "schemas", "invocation")
    monkeypatch.chdir(tmp_path)

    with _scope(tmp_path / "uninitialized" / ".ai" / "schemas"):
        with pytest.raises(OSError):
            contracts.load_schema("task")
        with pytest.raises(OSError):
            contracts.validate_contract("task", {"choice": "invocation"})

    assert contracts.load_schema("task")["title"] == "invocation"


def test_explicit_absolute_and_relative_directories_override_scope_with_same_ref_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _schemas(tmp_path / ".ai" / "schemas", "invocation")
    selected = _schemas(tmp_path / "selected", "selected")
    explicit = _schemas(tmp_path / "explicit", "explicit")
    monkeypatch.chdir(tmp_path)

    with _scope(selected):
        for directory in (explicit, Path("explicit")):
            assert contracts.load_schema("task", directory)["title"] == "explicit"
            assert (
                contracts._validate_contract_with_schema_directory(
                    "task", {"choice": "explicit"}, directory
                )
                == []
            )
            contracts._require_valid_contract_with_schema_directory(
                "task", {"choice": "explicit"}, directory
            )
            assert contracts._validate_contract_with_schema_directory(
                "task", {"choice": "selected"}, directory
            )
        assert contracts.load_schema("task")["title"] == "selected"


def test_nested_scope_and_exception_restore_previous_resource_without_changing_cwd_or_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _schemas(tmp_path / ".ai" / "schemas", "default")
    outer = _schemas(tmp_path / "outer", "outer")
    inner = _schemas(tmp_path / "inner", "inner")
    monkeypatch.chdir(tmp_path)
    before = contracts.SCHEMA_RELATIVE_DIRECTORY

    with _scope(outer):
        with pytest.raises(RuntimeError, match="scope sentinel"):
            with _scope(inner):
                assert contracts.load_schema("task")["title"] == "inner"
                assert Path.cwd() == tmp_path
                assert contracts.SCHEMA_RELATIVE_DIRECTORY == before
                raise RuntimeError("scope sentinel")
        assert contracts.load_schema("task")["title"] == "outer"

    assert contracts.load_schema("task")["title"] == "default"
    assert Path.cwd() == tmp_path
    assert contracts.SCHEMA_RELATIVE_DIRECTORY == before


def test_independent_and_copied_contexts_keep_their_own_resources_without_a_global_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _schemas(tmp_path / ".ai" / "schemas", "default")
    first = _schemas(tmp_path / "first", "first")
    second = _schemas(tmp_path / "second", "second")
    monkeypatch.chdir(tmp_path)
    independent = Context()

    def read_second() -> str:
        with _scope(second):
            assert contracts.validate_contract("task", {"choice": "second"}) == []
            return str(contracts.load_schema("task")["title"])

    with _scope(first):
        saved = copy_context()
        assert independent.run(read_second) == "second"
        assert contracts.validate_contract("task", {"choice": "first"}) == []
        assert contracts.load_schema("task")["title"] == "first"

    with _scope(second):
        assert saved.run(contracts.load_schema, "task")["title"] == "first"
        assert saved.run(contracts.validate_contract, "task", {"choice": "first"}) == []
        assert contracts.load_schema("task")["title"] == "second"

    assert contracts.load_schema("task")["title"] == "default"
    assert independent.run(contracts.load_schema, "task")["title"] == "default"
