"""Read and validate the fixed Phase 02 mutation declaration manifest.

This module deliberately declares *what* later mutation work may exercise.  It
does not execute a mutation, invoke pytest, or write any result/evidence file.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError

CANONICAL_MANIFEST_PATH = Path(".ai/mutations/phase-02-critical-manifest.json")
_SCHEMA_DIRECTORY = Path(".ai/schemas")


@dataclass(frozen=True)
class MutationDeclaration:
    """One immutable, declarative mutation target."""

    mutation_id: str
    safeguard_id: str
    target: str
    target_symbol: str
    operator: str
    expected_detector: str
    expected_outcome: str


@dataclass(frozen=True)
class MutationManifest:
    """The immutable, repository-owned Phase 02 mutation manifest."""

    schema_version: str
    manifest_id: str
    scope: str
    mutations: tuple[MutationDeclaration, ...]


def _manifest_error(message: str, code: str) -> ContractError:
    return ContractError(message, code=code)


def _read_manifest(path: Path) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _manifest_error(
            "Mutation manifest could not be read", "MUTATION_MANIFEST_READ_FAILED"
        ) from error
    return value


def _duplicates(manifest: Mapping[str, Any]) -> bool:
    mutations = manifest["mutations"]
    assert isinstance(mutations, list)
    fields = ("mutation_id", "safeguard_id", "target", "operator", "expected_detector")
    for field in fields:
        values = [mutation[field] for mutation in mutations if isinstance(mutation, Mapping)]
        if len(values) != len(set(values)):
            return True
    return False


def _validate_target_lexically(target: str) -> None:
    if (
        "\\" in target
        or target.startswith("/")
        or PureWindowsPath(target).is_absolute()
        or any(part in {"", ".", ".."} for part in target.split("/"))
        or "::" in target
        or len(target.split("/")) != 3
        or not target.startswith("src/aiflow/")
        or not target.endswith(".py")
    ):
        raise _manifest_error("Mutation target path is invalid", "MUTATION_MANIFEST_PATH_INVALID")


def _resolve_path(path: Path) -> Path:
    """Canonicalize a filesystem path; retained as a deterministic test seam."""
    return path.resolve()


def _resolve_repository_path(repository_root: Path, relative_path: str) -> Path:
    """Resolve one validated path and reject any symlink escape."""
    root = _resolve_path(repository_root)
    candidate = _resolve_path(root / relative_path)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise _manifest_error(
            "Mutation manifest path escapes repository", "MUTATION_MANIFEST_PATH_ESCAPE"
        ) from error
    return candidate


def _has_top_level_function(path: Path, symbol: str) -> bool:
    try:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return False
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
        for node in module.body
    )


def _split_detector(detector: str) -> tuple[str, str]:
    path, separator, function = detector.partition("::")
    if not separator or "::" in function:
        raise _manifest_error("Mutation detector is missing", "MUTATION_MANIFEST_DETECTOR_MISSING")
    return path, function


def load_mutation_manifest(repository_root: Path) -> MutationManifest:
    """Load the fixed manifest from ``repository_root`` without executing it."""
    root = Path(repository_root)
    manifest_path = _resolve_repository_path(root, CANONICAL_MANIFEST_PATH.as_posix())
    value = _read_manifest(manifest_path)
    require_valid_contract("mutation-manifest", value, root / _SCHEMA_DIRECTORY)
    assert isinstance(value, dict)
    manifest: Mapping[str, Any] = value

    if _duplicates(manifest):
        raise _manifest_error(
            "Mutation manifest contains duplicate declarations", "MUTATION_MANIFEST_DUPLICATE"
        )

    mutations = manifest["mutations"]
    assert isinstance(mutations, list)
    for mutation in mutations:
        assert isinstance(mutation, Mapping)
        _validate_target_lexically(str(mutation["target"]))

    target_paths: list[Path] = []
    detector_paths: list[tuple[Path, str]] = []
    for mutation in mutations:
        assert isinstance(mutation, Mapping)
        target_paths.append(_resolve_repository_path(root, str(mutation["target"])))
        detector_relative_path, detector_function = _split_detector(
            str(mutation["expected_detector"])
        )
        detector_paths.append(
            (_resolve_repository_path(root, detector_relative_path), detector_function)
        )

    for target_path in target_paths:
        if not target_path.is_file():
            raise _manifest_error(
                "Mutation target does not exist", "MUTATION_MANIFEST_TARGET_MISSING"
            )

    for mutation, target_path in zip(mutations, target_paths, strict=True):
        assert isinstance(mutation, Mapping)
        if not _has_top_level_function(target_path, str(mutation["target_symbol"])):
            raise _manifest_error(
                "Mutation target symbol does not exist", "MUTATION_MANIFEST_SYMBOL_MISSING"
            )

    for detector_file_path, detector_function in detector_paths:
        if not detector_file_path.is_file() or not _has_top_level_function(
            detector_file_path, detector_function
        ):
            raise _manifest_error(
                "Mutation detector does not exist", "MUTATION_MANIFEST_DETECTOR_MISSING"
            )

    declarations = tuple(
        MutationDeclaration(
            mutation_id=str(mutation["mutation_id"]),
            safeguard_id=str(mutation["safeguard_id"]),
            target=str(mutation["target"]),
            target_symbol=str(mutation["target_symbol"]),
            operator=str(mutation["operator"]),
            expected_detector=str(mutation["expected_detector"]),
            expected_outcome=str(mutation["expected_outcome"]),
        )
        for mutation in mutations
        if isinstance(mutation, Mapping)
    )
    return MutationManifest(
        schema_version=str(manifest["schema_version"]),
        manifest_id=str(manifest["manifest_id"]),
        scope=str(manifest["scope"]),
        mutations=declarations,
    )
