"""Public initialization behavior in small, disposable Git repositories."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from uuid import UUID

import pytest
from initialization_helpers import PortableFilesystem
from initialization_helpers import fixture_git as git
from initialization_helpers import snapshot_tree as tree

from aiflow.errors import AiflowError
from aiflow.resource_bundle import (
    MAX_BUNDLE_BYTES,
    MAX_RESOURCE_BYTES,
    RESOURCE_KINDS,
    build_bundle,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/aiflow/initialization.py"
try:
    SOURCE.lstat()
except FileNotFoundError:
    pytestmark = pytest.mark.skip(reason="initialization is not implemented on this baseline")
else:
    initialization = importlib.import_module("aiflow.initialization")
    if (
        initialization.__file__ is None
        or Path(initialization.__file__).resolve() != SOURCE.resolve()
    ):
        raise ImportError("initialization is not loaded from the tested checkout")


def _seed_tree_sha256(root: Path) -> str:
    """Digest every directory, file byte, and link count inside a shared module seed."""
    hasher = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise AssertionError(f"shared seed contains link: {path}")
        if path.is_dir():
            hasher.update(b"D\0" + relative + b"\0")
        else:
            assert info.st_nlink == 1, f"shared seed file has hardlink: {path}"
            hasher.update(b"F\0" + relative + b"\0" + path.read_bytes() + b"\0")
    return hasher.hexdigest()


@pytest.fixture(scope="module")
def initialization_seed(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    root = tmp_path_factory.mktemp("initialization-seed")
    git(root, "init", "--template=", "-b", "feature")
    (root / "README.md").write_bytes(b"Fixture source only.\n")
    (root / "pyproject.toml").write_bytes(
        b'[project]\nname = "initialization-fixture"\nversion = "0.0.0"\n'
    )
    (root / "example.py").write_bytes(b'"""Synthetic Python target; no V1/V2 run is claimed."""\n')
    (root / ".gitignore").write_bytes(b".private/\n")
    (root / "folder").mkdir()
    (root / "folder/source.txt").write_bytes(b"unchanged\n")
    git(root, "add", "README.md", "pyproject.toml", "example.py", ".gitignore", "folder/source.txt")
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
    digest = _seed_tree_sha256(root)
    yield root
    assert _seed_tree_sha256(root) == digest


@pytest.fixture
def repository(tmp_path: Path, initialization_seed: Path) -> Path:
    root = tmp_path / "repository"
    # A byte copy keeps every fixture ordinary and avoids a Git reference to another root.
    shutil.copytree(initialization_seed, root)
    return root


@pytest.fixture(scope="module")
def initialization_bundle(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    root = tmp_path_factory.mktemp("initialization-bundle")
    manifest, resources = build_bundle(ROOT)
    for relative, data in resources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    digest = _seed_tree_sha256(root)
    yield root
    assert _seed_tree_sha256(root) == digest


@pytest.fixture
def readonly_bundle(initialization_bundle: Path) -> Path:
    return initialization_bundle


@pytest.fixture
def bundle(tmp_path: Path, initialization_bundle: Path) -> Path:
    root = tmp_path / "bundle"
    shutil.copytree(initialization_bundle, root)
    return root


@pytest.fixture(scope="module")
def readonly_repository(
    tmp_path_factory: pytest.TempPathFactory, initialization_seed: Path
) -> Iterator[Path]:
    root = tmp_path_factory.mktemp("readonly-repository") / "repository"
    shutil.copytree(initialization_seed, root)
    digest = _seed_tree_sha256(root)
    yield root
    assert _seed_tree_sha256(root) == digest


@pytest.fixture(scope="module")
def readonly_preview_context(
    readonly_repository: Path, initialization_bundle: Path
) -> Iterator[tuple[Path, Path, dict]]:
    candidate = preview(readonly_repository, initialization_bundle)
    digest = _seed_tree_sha256(readonly_repository)
    yield readonly_repository, initialization_bundle, candidate
    assert _seed_tree_sha256(readonly_repository) == digest


def preview(repository: Path, bundle: Path) -> dict:
    return initialization.preview_initialization(repository, bundle_root=bundle)


def review(candidate: dict) -> dict:
    return {
        "schema_version": "1.0",
        "kind": "aiflow-policy-review",
        "preview_sha256": candidate["preview_sha256"],
        "repository_id": candidate["repository_id"],
        "profile": candidate["profile"],
        "policy_version": candidate["policy"]["policy_version"],
        "policies": [
            {"path": entry["path"], "sha256": entry["sha256"]}
            for entry in candidate["policy"]["files"]
        ],
        "reviewer": "independent-test-reviewer",
        "outcome": "APPROVE",
    }


def apply(repository: Path, candidate: dict, bundle: Path, decision: dict | None = None) -> dict:
    return initialization.apply_initialization(
        repository,
        candidate,
        review(candidate) if decision is None else decision,
        bundle_root=bundle,
    )


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def numeric_member(document: dict, field: str) -> tuple[dict, str]:
    if field == "policy-size":
        return document["policy"]["files"][0], "size"
    if field in {"resource-size", "identity-size"}:
        path = ".ai/templates/spec.md" if field == "resource-size" else ".ai/repository-id"
        return next(row for row in document["objects"] if row["path"] == path), "size"
    owner = document
    parts = field.split(".")
    for part in parts[:-1]:
        owner = owner[int(part) if part.isdecimal() else part]
    return owner, parts[-1]


def require_windows_apply() -> None:
    if sys.platform != "win32":
        pytest.skip("actual installation is supported only on Windows NTFS")


@pytest.fixture
def native_filesystem() -> None:
    """Select the actual helper instead of the portable state-machine model."""


@pytest.fixture(autouse=True)
def portable_filesystem(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    if "native_filesystem" in request.fixturenames:
        yield
        return
    PortableFilesystem.instances = []
    monkeypatch.setattr(initialization, "WindowsFilesystem", PortableFilesystem)
    yield
    leaked = sum(len(instance.handles) for instance in PortableFilesystem.instances)
    for instance in PortableFilesystem.instances:
        for handle in list(instance.handles):
            instance.close(handle)
    assert leaked == 0, "initialization left fixture object handles open"


@pytest.fixture(scope="module")
def complete_installation_seed(
    tmp_path_factory: pytest.TempPathFactory,
    initialization_seed: Path,
    initialization_bundle: Path,
) -> Iterator[Path]:
    """One logical installation to copy for read-only integrity tests, not fresh apply."""
    root = tmp_path_factory.mktemp("completed-initialization") / "repository"
    shutil.copytree(initialization_seed, root)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(initialization, "WindowsFilesystem", PortableFilesystem)
        candidate = preview(root, initialization_bundle)
        assert apply(root, candidate, initialization_bundle)["phase"] == "installed"
    assert all(not instance.handles for instance in PortableFilesystem.instances)
    initialization.require_initialization_ready(root)
    digest = _seed_tree_sha256(root)
    yield root
    assert _seed_tree_sha256(root) == digest


@pytest.fixture
def installed_repository(tmp_path: Path, complete_installation_seed: Path) -> Path:
    root = tmp_path / "installed-repository"
    shutil.copytree(complete_installation_seed, root)
    return root


def test_preview_is_read_only_and_binds_a_fresh_uuid(
    readonly_repository: Path, readonly_bundle: Path
) -> None:
    before, bundle_before = tree(readonly_repository), tree(readonly_bundle)
    first = preview(readonly_repository, readonly_bundle)
    second = preview(readonly_repository / "folder", readonly_bundle)

    assert tree(readonly_repository) == before
    assert tree(readonly_bundle) == bundle_before
    assert first["schema_version"] == "1.0"
    assert first["kind"] == "aiflow-init-preview"
    assert first["profile"] == "native-python-v1"
    identifier = UUID(first["repository_id"])
    assert identifier.version == 4
    assert str(identifier) == first["repository_id"]
    assert first["repository_id"] != second["repository_id"]
    assert first["target"] == second["target"]
    assert len(first["preview_sha256"]) == 64
    assert not (readonly_repository / ".ai").exists()


def test_preview_keeps_existing_dirty_and_ignored_material(
    repository: Path, readonly_bundle: Path
) -> None:
    (repository / "README.md").write_bytes(b"user work\n")
    (repository / "untracked.txt").write_bytes(b"not an installer output\n")
    (repository / ".private").mkdir()
    secret = repository / ".private/secret.txt"
    secret.write_bytes(b"private-fixture-marker-do-not-copy")
    before = tree(repository)

    candidate = preview(repository, readonly_bundle)

    assert tree(repository) == before
    assert b"private-fixture-marker-do-not-copy" not in json.dumps(candidate).encode()
    assert not (repository / ".ai").exists()


def test_branch_named_detached_is_distinct_from_detached_head(
    repository: Path, readonly_bundle: Path
) -> None:
    git(repository, "switch", "-c", "DETACHED")
    branch = preview(repository, readonly_bundle)
    git(repository, "switch", "--detach", "HEAD")
    detached = preview(repository, readonly_bundle)

    assert branch["target"] != detached["target"]


def test_preview_does_not_invoke_configured_fsmonitor(
    repository: Path, readonly_bundle: Path
) -> None:
    marker = repository / ".git/fsmonitor-was-called"
    helper = repository / ".git/untrusted-fsmonitor.py"
    helper.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('unexpected external command')\n",
        encoding="utf-8",
    )
    git(repository, "config", "core.fsmonitor", f'"{sys.executable}" "{helper}"')
    before = tree(repository)

    preview(repository, readonly_bundle)

    assert not marker.exists()
    assert tree(repository) == before


@pytest.mark.parametrize("profile", ["node-v0", "node-v1", "", "python", None, 1])
def test_unsupported_profile_rejects_before_any_target_write(
    readonly_repository: Path, readonly_bundle: Path, profile: object
) -> None:
    before = tree(readonly_repository)
    with pytest.raises(AiflowError):
        initialization.preview_initialization(
            readonly_repository, bundle_root=readonly_bundle, profile=profile
        )
    assert tree(readonly_repository) == before


def test_node_target_cannot_be_installed_under_the_python_label(
    repository: Path, readonly_bundle: Path
) -> None:
    (repository / "package.json").write_bytes(b'{"name":"node-fixture","scripts":{"check":"true"}}')
    before = tree(repository)
    with pytest.raises(AiflowError):
        preview(repository, readonly_bundle)
    assert tree(repository) == before


@pytest.mark.parametrize(
    "content", [None, b"", b"not valid [toml", b"[project]\n", b"[project]\nname=1\n"]
)
def test_missing_or_invalid_python_project_is_rejected(
    repository: Path, readonly_bundle: Path, content: bytes | None
) -> None:
    path = repository / "pyproject.toml"
    if content is None:
        path.unlink()
    else:
        path.write_bytes(content)
    before = tree(repository)
    with pytest.raises(AiflowError):
        preview(repository, readonly_bundle)
    assert tree(repository) == before


@pytest.mark.parametrize(
    "name", ["manifest.json", "schemas/policy.schema.json", "policy/routing.yaml"]
)
def test_missing_bundle_material_rejects_without_target_writes(
    readonly_repository: Path, bundle: Path, name: str
) -> None:
    (bundle / name).unlink()
    before = tree(readonly_repository)
    with pytest.raises(AiflowError):
        preview(readonly_repository, bundle)
    assert tree(readonly_repository) == before


@pytest.mark.parametrize(
    "name", ["schemas/policy.schema.json", "policy/routing.yaml", "templates/spec.md"]
)
def test_changed_bundle_material_rejects_without_target_writes(
    readonly_repository: Path, bundle: Path, name: str
) -> None:
    with (bundle / name).open("ab") as stream:
        stream.write(b"\nchanged\n")
    before = tree(readonly_repository)
    with pytest.raises(AiflowError):
        preview(readonly_repository, bundle)
    assert tree(readonly_repository) == before


def test_extra_bundle_entry_rejects_without_target_writes(
    readonly_repository: Path, bundle: Path
) -> None:
    (bundle / "unexpected.txt").write_bytes(b"unknown\n")
    before = tree(readonly_repository)
    with pytest.raises(AiflowError):
        preview(readonly_repository, bundle)
    assert tree(readonly_repository) == before


@pytest.mark.parametrize("change", ["missing", "extra", "invalid", "hardlink", "directory"])
def test_policy_candidate_must_be_exact_and_ordinary(
    readonly_repository: Path, readonly_bundle: Path, tmp_path: Path, change: str
) -> None:
    candidate = tmp_path / "candidate-policy"
    shutil.copytree(readonly_bundle / "policy", candidate)
    path = candidate / "routing.yaml"
    if change == "missing":
        path.unlink()
    elif change == "extra":
        (candidate / "unreviewed.yaml").write_bytes(b"unreviewed\n")
    elif change == "invalid":
        path.write_bytes(b"not: [valid, yaml\n")
    elif change == "hardlink":
        os.link(path, tmp_path / "shared-policy.yaml")
    else:
        path.unlink()
        path.mkdir()
    before = tree(readonly_repository)

    with pytest.raises(AiflowError):
        initialization.preview_initialization(
            readonly_repository, bundle_root=readonly_bundle, policy_directory=candidate
        )
    assert tree(readonly_repository) == before


def test_policy_candidate_cannot_supply_a_weaker_schema(
    readonly_repository: Path, readonly_bundle: Path, tmp_path: Path
) -> None:
    candidate = tmp_path / "candidate-policy"
    shutil.copytree(readonly_bundle / "policy", candidate)
    (candidate / "policy.schema.json").write_bytes(b"{}")
    (candidate / "routing.yaml").write_bytes(b"arbitrary: true\n")
    before = tree(readonly_repository)

    with pytest.raises(AiflowError):
        initialization.preview_initialization(
            readonly_repository, bundle_root=readonly_bundle, policy_directory=candidate
        )
    assert tree(readonly_repository) == before


def test_policy_review_binds_candidate_bytes_not_just_semantics(
    readonly_repository: Path, readonly_bundle: Path, tmp_path: Path
) -> None:
    candidate = tmp_path / "candidate-policy"
    shutil.copytree(readonly_bundle / "policy", candidate)
    initial = initialization.preview_initialization(
        readonly_repository, bundle_root=readonly_bundle, policy_directory=candidate
    )
    decision = review(initial)
    with (candidate / "routing.yaml").open("ab") as stream:
        stream.write(b"\n# Different reviewed bytes with the same Policy semantics.\n")
    before = tree(readonly_repository)

    with pytest.raises(AiflowError):
        initialization.apply_initialization(
            readonly_repository,
            initial,
            decision,
            bundle_root=readonly_bundle,
            policy_directory=candidate,
        )
    assert tree(readonly_repository) == before


def test_policy_candidate_changed_in_place_during_apply_is_never_published(
    repository: Path, readonly_bundle: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_directory = tmp_path / "candidate-policy"
    shutil.copytree(readonly_bundle / "policy", policy_directory)
    routing = policy_directory / "routing.yaml"
    original_inode = routing.stat().st_ino
    candidate = initialization.preview_initialization(
        repository, bundle_root=readonly_bundle, policy_directory=policy_directory
    )
    decision = review(candidate)
    flush = PortableFilesystem.flush
    changed = False

    def change_policy_after_first_flush(self, handle):
        nonlocal changed
        flush(self, handle)
        if not changed:
            with routing.open("ab") as stream:
                stream.write(b"\n# Concurrent edit; semantics unchanged, reviewed bytes changed.\n")
            changed = True

    monkeypatch.setattr(PortableFilesystem, "flush", change_policy_after_first_flush)

    with pytest.raises(AiflowError):
        initialization.apply_initialization(
            repository,
            candidate,
            decision,
            bundle_root=readonly_bundle,
            policy_directory=policy_directory,
        )
    assert changed
    assert routing.stat().st_ino == original_inode
    assert not (repository / ".ai/repository-id").exists()


def test_valid_individual_policies_cannot_exceed_the_aggregate_bundle_limit(
    readonly_repository: Path, readonly_bundle: Path, tmp_path: Path
) -> None:
    from aiflow.contracts import schema_directory_context
    from aiflow.policy import POLICY_FILES, load_policy_bundle

    policy_directory = tmp_path / "large-policy"
    shutil.copytree(readonly_bundle / "policy", policy_directory)
    with schema_directory_context(readonly_bundle / "schemas"):
        original = load_policy_bundle(
            readonly_repository, policy_directory=readonly_bundle / "policy"
        )
    for name in POLICY_FILES:
        path = policy_directory / name
        original_bytes = path.read_bytes()
        padding = b"\n#" + b"x" * (MAX_RESOURCE_BYTES - len(original_bytes) - 3) + b"\n"
        path.write_bytes(original_bytes + padding)
        assert path.stat().st_size == MAX_RESOURCE_BYTES
    # These remain four independently valid Policies with unchanged semantics.
    with schema_directory_context(readonly_bundle / "schemas"):
        padded = load_policy_bundle(readonly_repository, policy_directory=policy_directory)
    assert padded.sha256 == original.sha256
    assert sum(path.stat().st_size for path in policy_directory.iterdir()) == MAX_BUNDLE_BYTES
    before = tree(readonly_repository)

    with pytest.raises(AiflowError):
        initialization.preview_initialization(
            readonly_repository, bundle_root=readonly_bundle, policy_directory=policy_directory
        )

    assert tree(readonly_repository) == before
    assert not (readonly_repository / ".ai").exists()


@pytest.mark.parametrize("kind", ["directory", "file", "case-alias"])
def test_unknown_ai_created_after_preview_is_preserved(
    repository: Path, readonly_bundle: Path, kind: str
) -> None:
    candidate = preview(repository, readonly_bundle)
    if kind == "file":
        (repository / ".ai").write_bytes(b"unknown\n")
    else:
        directory = repository / (".AI" if kind == "case-alias" else ".ai")
        directory.mkdir()
        (directory / "owner.txt").write_bytes(b"preexisting owner data\n")
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert tree(repository) == before


@pytest.mark.parametrize(
    "field", ["repository_id", "profile", "preview_sha256", "objects", "target"]
)
def test_tampered_preview_is_rejected_without_writes(
    readonly_preview_context: tuple[Path, Path, dict], field: str
) -> None:
    repository, bundle, base_candidate = readonly_preview_context
    candidate = deepcopy(base_candidate)
    decision = review(candidate)
    candidate[field] = "tampered"
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle, decision)
    assert tree(repository) == before


@pytest.mark.parametrize(
    "field,number_type",
    [
        ("resource-size", float),
        ("identity-size", float),
        ("policy-size", float),
        ("target.file_count", float),
        ("target.python_source_count", bool),
        ("target.untracked_count", bool),
        ("target.root_identity.device", float),
        ("target.ancestors.0.device", float),
    ],
)
def test_rehashed_preview_rejects_equal_numbers_of_the_wrong_json_type_without_writes(
    readonly_preview_context: tuple[Path, Path, dict], field: str, number_type: type
) -> None:
    repository, bundle, base_candidate = readonly_preview_context
    candidate = deepcopy(base_candidate)
    owner, key = numeric_member(candidate, field)
    original = owner[key]
    assert type(original) is int
    owner[key] = number_type(original)
    assert owner[key] == original and type(owner[key]) is not int
    candidate["preview_sha256"] = hashlib.sha256(
        canonical_json({key: value for key, value in candidate.items() if key != "preview_sha256"})
    ).hexdigest()
    decision = review(candidate)
    before = tree(repository)

    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle, decision)

    assert tree(repository) == before
    assert not (repository / ".ai").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "2.0"),
        ("kind", "another-review"),
        ("preview_sha256", "0" * 64),
        ("repository_id", "d34142ea-3097-4697-b5f4-6f36d38171da"),
        ("profile", "node-v0"),
        ("policy_version", "0.0.0"),
        ("outcome", "REQUEST_CHANGES"),
        ("reviewer", ""),
        ("reviewer", "   "),
        ("policies", []),
    ],
)
def test_policy_review_must_bind_exact_approved_material(
    readonly_preview_context: tuple[Path, Path, dict], field: str, value: object
) -> None:
    repository, bundle, base_candidate = readonly_preview_context
    candidate = deepcopy(base_candidate)
    decision = review(candidate)
    decision[field] = value
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle, decision)
    assert tree(repository) == before


@pytest.mark.parametrize("entry", ["preview", "review"])
def test_unknown_top_level_fields_are_rejected(
    readonly_preview_context: tuple[Path, Path, dict], entry: str
) -> None:
    repository, bundle, base_candidate = readonly_preview_context
    candidate = deepcopy(base_candidate)
    decision = review(candidate)
    (candidate if entry == "preview" else decision)["unknown"] = True
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle, decision)
    assert tree(repository) == before


@pytest.mark.parametrize("change", ["digest", "duplicate", "missing", "extra-field"])
def test_review_requires_four_exact_policy_digests(
    readonly_preview_context: tuple[Path, Path, dict], change: str
) -> None:
    repository, bundle, base_candidate = readonly_preview_context
    candidate = deepcopy(base_candidate)
    decision = review(candidate)
    if change == "digest":
        decision["policies"][0]["sha256"] = "0" * 64
    elif change == "duplicate":
        decision["policies"][1] = decision["policies"][0].copy()
    elif change == "missing":
        decision["policies"].pop()
    else:
        decision["policies"][0]["unknown"] = True
    before = tree(repository)

    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle, decision)
    assert tree(repository) == before


@pytest.mark.parametrize("drift", ["branch", "head", "index", "tracked", "untracked"])
def test_apply_rejects_git_and_worktree_drift_without_overwriting_it(
    repository: Path, readonly_bundle: Path, drift: str
) -> None:
    candidate = preview(repository, readonly_bundle)
    if drift == "branch":
        git(repository, "switch", "-c", "other-branch")
    elif drift == "head":
        git(
            repository,
            "-c",
            "user.name=AI Flow Test",
            "-c",
            "user.email=initialization@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "later head",
        )
    elif drift == "index":
        (repository / "README.md").write_bytes(b"staged change\n")
        git(repository, "add", "README.md")
    elif drift == "tracked":
        (repository / "README.md").write_bytes(b"later edit\n")
    else:
        (repository / "later.txt").write_bytes(b"new user data\n")
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert tree(repository) == before


def test_apply_rejects_bundle_drift_after_review(readonly_repository: Path, bundle: Path) -> None:
    candidate = preview(readonly_repository, bundle)
    (bundle / "templates/spec.md").write_bytes(b"changed after review\n")
    before = tree(readonly_repository)
    with pytest.raises(AiflowError):
        apply(readonly_repository, candidate, bundle)
    assert tree(readonly_repository) == before


def test_preview_cannot_be_reused_for_another_clone(
    readonly_preview_context: tuple[Path, Path, dict], tmp_path: Path
) -> None:
    repository, bundle, base_candidate = readonly_preview_context
    clone = tmp_path / "another-clone"
    shutil.copytree(repository, clone)
    before = tree(clone)
    with pytest.raises(AiflowError):
        apply(clone, deepcopy(base_candidate), bundle)
    assert tree(clone) == before


def test_unsupported_platform_application_does_not_write(
    readonly_preview_context: tuple[Path, Path, dict], native_filesystem: None
) -> None:
    repository, bundle, base_candidate = readonly_preview_context
    # This is the real boundary on POSIX; Windows behavior is covered below.
    if sys.platform == "win32":
        pytest.skip("unsupported-platform behavior is exercised on POSIX")
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, deepcopy(base_candidate), bundle)
    assert tree(repository) == before


def test_install_creates_only_planned_resources_and_a_fresh_identity(
    repository: Path, readonly_bundle: Path
) -> None:
    candidate = preview(repository, readonly_bundle)
    original = tree(repository)

    result = apply(repository, candidate, readonly_bundle)

    assert result["phase"] == "installed"
    assert (repository / ".ai/repository-id").read_text("utf-8").strip() == candidate[
        "repository_id"
    ]
    assert not (repository / ".ai/.repository-id.pending").exists()
    for relative in RESOURCE_KINDS:
        assert (repository / ".ai" / relative).read_bytes() == (
            readonly_bundle / relative
        ).read_bytes()
    after = tree(repository)
    assert {path: value for path, value in after.items() if path.split("/")[0] != ".ai"} == original
    assert not (repository / ".ai/bootstrap-mode.yaml").exists()
    assert not (repository / ".ai/tasks").exists()
    initialization.require_initialization_ready(repository)


def test_completed_replay_is_byte_and_metadata_preserving(
    repository: Path, readonly_bundle: Path
) -> None:
    candidate = preview(repository, readonly_bundle)
    apply(repository, candidate, readonly_bundle)
    before = tree(repository)

    result = apply(repository, candidate, readonly_bundle)

    assert result["phase"] == "already_complete"
    assert tree(repository) == before


def test_verified_interruption_resumes_original_uuid_without_rewriting_completed_files(
    repository: Path, readonly_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, readonly_bundle)
    create = PortableFilesystem.create_file

    def interrupt(self, parent_handle, name, **keywords):
        if name == "task.schema.json":
            raise AiflowError("injected interruption before creating the next object")
        return create(self, parent_handle, name, **keywords)

    monkeypatch.setattr(PortableFilesystem, "create_file", interrupt)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert (repository / ".ai/init-state.json").is_file()
    assert not (repository / ".ai/repository-id").exists()
    partial = tree(repository)
    monkeypatch.setattr(PortableFilesystem, "create_file", create)

    result = apply(repository, candidate, readonly_bundle)

    assert result["phase"] == "resumed"
    assert result["repository_id"] == candidate["repository_id"]
    final = tree(repository)
    for name, facts in partial.items():
        if name.endswith(".repository-id.pending"):
            continue
        assert final[name] == facts
    initialization.require_initialization_ready(repository)


def test_partially_written_object_is_preserved_and_cannot_be_resumed(
    repository: Path, readonly_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, readonly_bundle)
    write = PortableFilesystem.write
    resource = (readonly_bundle / "schemas/task.schema.json").read_bytes()

    def interrupted_write(self, handle, data):
        if data == resource:
            write(self, handle, data[:11])
            raise AiflowError("injected incomplete file write")
        return write(self, handle, data)

    monkeypatch.setattr(PortableFilesystem, "write", interrupted_write)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    monkeypatch.setattr(PortableFilesystem, "write", write)
    before = tree(repository)

    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert tree(repository) == before
    assert not (repository / ".ai/repository-id").exists()


@pytest.mark.parametrize("stage", ["first", "complete"])
def test_flush_failure_never_publishes_a_successful_identity(
    repository: Path, readonly_bundle: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    candidate = preview(repository, readonly_bundle)
    flush = PortableFilesystem.flush
    count = 0

    def fail_flush(self, handle):
        nonlocal count
        count += 1
        path = self.handles[handle]["path"]
        if (stage == "first" and count == 1) or path.name == "init-complete.json":
            raise AiflowError("injected flush failure")
        return flush(self, handle)

    monkeypatch.setattr(PortableFilesystem, "flush", fail_flush)

    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert not (repository / ".ai/repository-id").exists()
    with pytest.raises(AiflowError):
        initialization.require_initialization_ready(repository)


def test_competitor_at_atomic_directory_creation_is_preserved(
    repository: Path, readonly_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, readonly_bundle)
    create = PortableFilesystem.create_directory
    foreign = repository / ".ai/foreign.txt"

    def compete(self, parent_handle, name, **keywords):
        if name == ".ai":
            foreign.parent.mkdir()
            foreign.write_bytes(b"competitor-owned bytes\n")
        return create(self, parent_handle, name, **keywords)

    monkeypatch.setattr(PortableFilesystem, "create_directory", compete)

    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert foreign.read_bytes() == b"competitor-owned bytes\n"
    assert sorted(path.name for path in foreign.parent.iterdir()) == ["foreign.txt"]


def test_competitor_identity_is_not_replaced_at_publication(
    repository: Path, readonly_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, readonly_bundle)
    publish = PortableFilesystem.rename_no_replace
    foreign = repository / ".ai/repository-id"

    def compete(self, handle, target):
        foreign.write_bytes(b"competitor identity\n")
        return publish(self, handle, target)

    monkeypatch.setattr(PortableFilesystem, "rename_no_replace", compete)

    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert foreign.read_bytes() == b"competitor identity\n"
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert tree(repository) == before


def test_wrong_publication_name_is_preserved_and_cannot_report_installation_success(
    repository: Path, readonly_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, readonly_bundle)
    publish = PortableFilesystem.rename_no_replace
    wrong_name = repository / ".ai/repository-id-unexpected"
    published = False

    def publish_to_wrong_name(self, handle, target):
        nonlocal published
        publish(self, handle, target.with_name(wrong_name.name))
        published = True

    monkeypatch.setattr(PortableFilesystem, "rename_no_replace", publish_to_wrong_name)

    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)

    assert published
    assert not (repository / ".ai/repository-id").exists()
    assert wrong_name.read_bytes() == (candidate["repository_id"] + "\n").encode("utf-8")
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert tree(repository) == before


@pytest.mark.parametrize("change", ["extra", "resource", "review", "identity", "state", "complete"])
def test_complete_installation_tampering_blocks_ready_and_replay(
    repository: Path, readonly_bundle: Path, change: str
) -> None:
    candidate = preview(repository, readonly_bundle)
    apply(repository, candidate, readonly_bundle)
    paths = {
        "resource": "templates/spec.md",
        "review": "policy-review.json",
        "identity": "repository-id",
        "state": "init-state.json",
        "complete": "init-complete.json",
        "extra": "unknown.txt",
    }
    (repository / ".ai" / paths[change]).write_bytes(b"later user edit\n")
    before = tree(repository)
    with pytest.raises(AiflowError):
        initialization.require_initialization_ready(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert tree(repository) == before


def test_ready_guard_allows_normal_task_history_without_accepting_preview_replay(
    repository: Path, readonly_bundle: Path
) -> None:
    candidate = preview(repository, readonly_bundle)
    apply(repository, candidate, readonly_bundle)
    task = repository / ".ai/tasks/TASK-0001"
    task.mkdir(parents=True)
    (task / "history.txt").write_bytes(b"append-only fixture history\n")
    before = tree(repository)

    initialization.require_initialization_ready(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert tree(repository) == before


def test_a_managed_file_with_another_hardlink_is_not_a_ready_installation(
    repository: Path, readonly_bundle: Path, tmp_path: Path
) -> None:
    candidate = preview(repository, readonly_bundle)
    apply(repository, candidate, readonly_bundle)
    resource = repository / ".ai/templates/spec.md"
    os.link(resource, tmp_path / "another-link.md")
    before = tree(repository)

    with pytest.raises(AiflowError):
        initialization.require_initialization_ready(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    assert tree(repository) == before


def test_legacy_repository_without_installer_state_is_unchanged(repository: Path) -> None:
    (repository / ".ai").mkdir()
    (repository / ".ai/repository-id").write_bytes(b"legacy fixture identity\n")
    before = tree(repository)

    initialization.require_initialization_ready(repository)

    assert tree(repository) == before


@pytest.mark.parametrize("contents", [b"", b"{}", b"not json", b"[]"])
def test_corrupt_state_is_not_treated_as_legacy(repository: Path, contents: bytes) -> None:
    (repository / ".ai").mkdir()
    (repository / ".ai/init-state.json").write_bytes(contents)
    before = tree(repository)

    with pytest.raises(AiflowError):
        initialization.require_initialization_ready(repository)
    assert tree(repository) == before


def test_inspect_and_migration_plan_are_read_only(
    installed_repository: Path, readonly_bundle: Path
) -> None:
    repository_id = (installed_repository / ".ai/repository-id").read_text("utf-8").strip()
    before, bundle_before = tree(installed_repository), tree(readonly_bundle)

    inspected = initialization.inspect_initialization(installed_repository)
    migration = initialization.plan_initialization_migration(
        installed_repository, bundle_root=readonly_bundle
    )

    assert isinstance(inspected, dict)
    assert isinstance(migration, dict)
    assert tree(installed_repository) == before
    assert tree(readonly_bundle) == bundle_before
    serialized = json.dumps(migration)
    assert repository_id in serialized
    assert "readonly" in serialized.lower() or "read_only" in serialized.lower()


def test_persistent_installer_metadata_has_no_machine_paths(
    installed_repository: Path, complete_installation_seed: Path, readonly_bundle: Path
) -> None:
    repository_id = (installed_repository / ".ai/repository-id").read_text("utf-8").strip()
    assert UUID(repository_id).version == 4

    for filename in ("init-state.json", "policy-review.json", "init-complete.json"):
        raw = (installed_repository / ".ai" / filename).read_bytes()
        document = json.loads(raw)
        assert isinstance(document, dict)
        for path in (installed_repository, complete_installation_seed, readonly_bundle):
            assert str(path).encode() not in raw
            assert path.as_posix().encode() not in raw
    state = json.loads((installed_repository / ".ai/init-state.json").read_bytes())
    assert repository_id in json.dumps(state)


def test_actual_windows_backend_installs_and_replays(
    repository: Path, readonly_bundle: Path, native_filesystem: None
) -> None:
    require_windows_apply()
    candidate = preview(repository, readonly_bundle)

    assert apply(repository, candidate, readonly_bundle)["phase"] == "installed"
    initialization.require_initialization_ready(repository)
    before = tree(repository)
    assert apply(repository, candidate, readonly_bundle)["phase"] == "already_complete"
    assert tree(repository) == before


def test_actual_windows_system_temp_installation_keeps_ancestors_pinned(
    initialization_seed: Path,
    readonly_bundle: Path,
    native_filesystem: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    require_windows_apply()
    from aiflow.initialization_windows import WindowsFilesystem

    system_temp = Path(os.environ["SystemRoot"]) / "Temp"
    pin = WindowsFilesystem._pin_ancestor
    observed = []
    script = (
        "import json,os,sys\n"
        "try:\n"
        " os.rename(sys.argv[1],sys.argv[2])\n"
        "except OSError as error:\n"
        " print(json.dumps({'renamed':False,'winerror':error.winerror}))\n"
        "else:\n"
        " print(json.dumps({'renamed':True}))\n"
    )
    with tempfile.TemporaryDirectory(prefix="aiflow-init-system-temp-", dir=system_temp) as name:
        parent = Path(name)
        moved = parent.with_name(parent.name + "-rename-control")
        # This owned directory can be renamed before the protective handle exists.
        parent.rename(moved)
        moved.rename(parent)
        root = parent / "repository"
        shutil.copytree(initialization_seed, root)
        candidate = preview(root, readonly_bundle)

        def checked_pin(self, path):
            handle = pin(self, path)
            observed.append(Path(path))
            if Path(path) == parent:
                result = subprocess.run(
                    [sys.executable, "-I", "-B", "-c", script, str(parent), str(moved)],
                    cwd=system_temp,
                    capture_output=True,
                    check=True,
                    encoding="utf-8",
                    timeout=15,
                )
                assert json.loads(result.stdout) == {"renamed": False, "winerror": 32}
            return handle

        monkeypatch.setattr(WindowsFilesystem, "_pin_ancestor", checked_pin)

        assert apply(root, candidate, readonly_bundle)["phase"] == "installed"
        assert system_temp in observed
        assert parent in observed
        assert (root / ".ai/repository-id").read_bytes() == (
            candidate["repository_id"] + "\n"
        ).encode("utf-8")
        initialization.require_initialization_ready(root)
        assert initialization.inspect_initialization(root)["status"] == "complete"
        before = tree(root)
        assert apply(root, candidate, readonly_bundle)["phase"] == "already_complete"
        assert tree(root) == before


def test_actual_windows_handles_hold_resources_until_identity_publication(
    repository: Path,
    readonly_bundle: Path,
    native_filesystem: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    require_windows_apply()
    from aiflow.initialization_windows import WindowsFilesystem

    candidate = preview(repository, readonly_bundle)
    publish = WindowsFilesystem.rename_no_replace
    observed = False
    script = (
        "import os,sys\n"
        "from pathlib import Path\n"
        "p=Path(sys.argv[1]); operation=sys.argv[2]\n"
        "try:\n"
        " if operation=='rename': os.rename(p, str(p)+'-moved')\n"
        " elif operation=='write': p.write_bytes(b'competitor')\n"
        " elif operation=='read': p.read_bytes()\n"
        "except OSError: sys.exit(0)\n"
        "sys.exit(1)\n"
    )

    def checked_publish(self, handle, target):
        nonlocal observed
        for path, operation in (
            (repository, "rename"),
            (repository / ".ai", "rename"),
            (repository / ".ai/schemas/task.schema.json", "write"),
            (repository / ".ai/policy-review.json", "write"),
            (repository / ".ai/init-state.json", "write"),
            (repository / ".ai/init-complete.json", "write"),
            (repository / ".ai/.repository-id.pending", "read"),
        ):
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", script, str(path), operation],
                cwd=repository.parent,
                capture_output=True,
                timeout=15,
            )
            assert result.returncode == 0, (path.name, operation, result.stderr)
        observed = True
        return publish(self, handle, target)

    monkeypatch.setattr(WindowsFilesystem, "rename_no_replace", checked_publish)

    assert apply(repository, candidate, readonly_bundle)["phase"] == "installed"
    assert observed


def run_cli(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-m", "aiflow", *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        check=False,
        encoding="utf-8",
        timeout=30,
    )


def test_cli_preview_works_outside_any_repository_without_writing_target(
    readonly_repository: Path, readonly_bundle: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    before = tree(readonly_repository)

    result = run_cli(
        outside,
        "init",
        "preview",
        "--target",
        str(readonly_repository),
        "--profile",
        "native-python-v1",
        "--bundle-root",
        str(readonly_bundle),
    )

    assert result.returncode == 0, result.stderr
    candidate = json.loads(result.stdout)
    assert candidate["kind"] == "aiflow-init-preview"
    assert UUID(candidate["repository_id"]).version == 4
    assert tree(readonly_repository) == before
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(
    "data",
    [b"{}", b"[]", b'{"kind":1,"kind":2}', b"x" * (64 * 1024 + 1)],
    ids=["empty-object", "array", "duplicate-key", "oversize"],
)
def test_cli_rejects_invalid_review_input_before_target_writes(
    readonly_preview_context: tuple[Path, Path, dict], tmp_path: Path, data: bytes
) -> None:
    repository, bundle, candidate = readonly_preview_context
    preview_path = tmp_path / "preview.json"
    review_path = tmp_path / "review.json"
    preview_path.write_text(json.dumps(candidate), encoding="utf-8")
    review_path.write_bytes(data)
    before = tree(repository)

    result = run_cli(
        tmp_path,
        "init",
        "apply",
        "--target",
        str(repository),
        "--preview",
        str(preview_path),
        "--policy-review",
        str(review_path),
        "--bundle-root",
        str(bundle),
    )

    assert result.returncode != 0
    assert not result.stdout.strip()
    assert "Traceback" not in result.stderr
    assert tree(repository) == before


def test_cli_apply_and_inspect_use_the_same_target_and_identity(
    repository: Path, readonly_bundle: Path, tmp_path: Path, native_filesystem: None
) -> None:
    require_windows_apply()
    candidate = preview(repository, readonly_bundle)
    preview_path = tmp_path / "preview.json"
    review_path = tmp_path / "review.json"
    preview_path.write_text(json.dumps(candidate), encoding="utf-8")
    review_path.write_text(json.dumps(review(candidate)), encoding="utf-8")

    result = run_cli(
        tmp_path,
        "init",
        "apply",
        "--target",
        str(repository),
        "--preview",
        str(preview_path),
        "--policy-review",
        str(review_path),
        "--bundle-root",
        str(readonly_bundle),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["repository_id"] == candidate["repository_id"]
    before = tree(repository)

    inspected = run_cli(tmp_path, "init", "inspect", "--target", str(repository))

    assert inspected.returncode == 0, inspected.stderr
    assert candidate["repository_id"] in inspected.stdout
    assert tree(repository) == before


@pytest.mark.parametrize(
    "arguments",
    [
        ["start", "--objective", "fixture", "--allow", "README.md"],
        ["start", "--recover", "TASK-0001"],
        ["begin", "TASK-0001", "--actor", "fixture"],
        ["verify", "TASK-0001", "--actor", "verifier"],
        ["verify", "TASK-0001", "--finalize", "--actor", "verifier"],
        ["verify", "TASK-0001", "--abandon", "--actor", "verifier", "--reason", "fixture"],
    ],
)
def test_incomplete_installation_rejects_cli_before_dispatch(
    repository: Path, monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    from aiflow import cli

    (repository / ".ai").mkdir()
    (repository / ".ai/init-state.json").write_bytes(b"{}")
    before = tree(repository)
    monkeypatch.chdir(repository)

    def unexpected_dispatch(*_arguments: object) -> None:
        pytest.fail("an incomplete installation reached a normal governance command")

    monkeypatch.setattr(cli, "_dispatch", unexpected_dispatch)

    assert cli.main(arguments) == 1
    assert tree(repository) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("policy", None),
        ("policy.files", "not an array"),
        ("policy.semantic_sha256", None),
        ("policy.policy_version", True),
        ("bundle", []),
        ("bundle.manifest_sha256", ["not a digest"]),
        ("objects", {}),
        ("policy_review_sha256", False),
    ],
)
def test_malformed_nested_state_returns_domain_rejection_and_readonly_conflict(
    installed_repository: Path, field: str, value: object
) -> None:
    path = installed_repository / ".ai/init-state.json"
    state = json.loads(path.read_bytes())
    parts = field.split(".")
    owner = state
    for part in parts[:-1]:
        owner = owner[part]
    owner[parts[-1]] = value
    path.write_text(json.dumps(state), encoding="utf-8")
    before = tree(installed_repository)

    with pytest.raises(AiflowError):
        initialization.require_initialization_ready(installed_repository)
    inspected = initialization.inspect_initialization(installed_repository)

    assert inspected["status"] == "conflict"
    assert inspected["issues"]
    assert tree(installed_repository) == before


@pytest.mark.parametrize("field", ["policy-size", "resource-size", "identity-size"])
def test_state_rejects_equal_float_sizes_even_with_a_valid_completion_digest(
    installed_repository: Path, field: str
) -> None:
    state_path = installed_repository / ".ai/init-state.json"
    state = json.loads(state_path.read_bytes())
    owner, key = numeric_member(state, field)
    original = owner[key]
    assert type(original) is int
    owner[key] = float(original)
    assert owner[key] == original and type(owner[key]) is float
    encoded = canonical_json(state)
    state_path.write_bytes(encoded)
    complete_path = installed_repository / ".ai/init-complete.json"
    complete = json.loads(complete_path.read_bytes())
    complete["state_sha256"] = hashlib.sha256(encoded).hexdigest()
    complete_path.write_bytes(canonical_json(complete))
    before = tree(installed_repository)

    with pytest.raises(AiflowError):
        initialization.require_initialization_ready(installed_repository)
    inspected = initialization.inspect_initialization(installed_repository)

    assert inspected["status"] == "conflict"
    assert inspected["issues"]
    assert tree(installed_repository) == before


@pytest.mark.parametrize("field", ["profile", "cli_version", "bundle_version"])
def test_inspect_distinguishes_unsupported_versions_from_corrupt_installations(
    installed_repository: Path, field: str
) -> None:
    path = installed_repository / ".ai/init-state.json"
    state = json.loads(path.read_bytes())
    if field == "profile":
        state["profile"] = "unavailable-profile"
    else:
        state["bundle"][field] = "99.0.0"
    path.write_text(json.dumps(state), encoding="utf-8")
    before = tree(installed_repository)

    inspected = initialization.inspect_initialization(installed_repository)

    assert inspected["status"] == "unsupported"
    assert tree(installed_repository) == before


def test_inspect_absent_repository_does_not_create_state(readonly_repository: Path) -> None:
    before = tree(readonly_repository)
    inspected = initialization.inspect_initialization(readonly_repository)
    assert inspected["status"] == "absent"
    assert inspected["issues"] == []
    assert inspected["has_history"] is False
    assert tree(readonly_repository) == before


def test_inspect_verified_partial_reports_relative_missing_paths_without_recovery(
    repository: Path, readonly_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, readonly_bundle)
    create = PortableFilesystem.create_file

    def interrupt(self, parent_handle, name, **keywords):
        if name == "task.schema.json":
            raise AiflowError("injected stop before a planned resource")
        return create(self, parent_handle, name, **keywords)

    monkeypatch.setattr(PortableFilesystem, "create_file", interrupt)
    with pytest.raises(AiflowError):
        apply(repository, candidate, readonly_bundle)
    before = tree(repository)

    inspected = initialization.inspect_initialization(repository)

    assert inspected["status"] == "incomplete"
    assert inspected["repository_id"] == candidate["repository_id"]
    assert {"path": ".ai/schemas/task.schema.json", "code": "missing"} in inspected["issues"]
    assert all(issue["code"] == "missing" for issue in inspected["issues"])
    assert all(not Path(issue["path"]).is_absolute() for issue in inspected["issues"])
    assert tree(repository) == before


@pytest.mark.parametrize("change", ["modified", "missing", "unknown"])
def test_inspect_and_migration_preserve_and_report_changed_managed_files(
    installed_repository: Path, readonly_bundle: Path, change: str
) -> None:
    relative = ".ai/templates/spec.md"
    path = installed_repository / relative
    if change == "modified":
        path.write_bytes(b"later owner change\n")
    elif change == "missing":
        path.unlink()
    else:
        path.unlink()
        path.mkdir()
    before = tree(installed_repository)

    inspected = initialization.inspect_initialization(installed_repository)
    planned = initialization.plan_initialization_migration(
        installed_repository, bundle_root=readonly_bundle
    )

    assert inspected["status"] == "conflict"
    assert planned["read_only"] is True
    assert {"path": relative, "status": change} in [
        {"path": row["path"], "status": row["status"]} for row in planned["files"]
    ]
    assert tree(installed_repository) == before


def test_migration_reports_unknown_files_and_preserves_task_history(
    installed_repository: Path, readonly_bundle: Path
) -> None:
    unknown = installed_repository / ".ai/owner-note.txt"
    unknown.write_bytes(b"unknown owner material\n")
    history = installed_repository / ".ai/tasks/TASK-0001/events.jsonl"
    history.parent.mkdir(parents=True)
    history.write_bytes(b"frozen original history\n")
    before = tree(installed_repository)

    planned = initialization.plan_initialization_migration(
        installed_repository, bundle_root=readonly_bundle
    )

    assert planned["has_history"] is True
    assert planned["read_only"] is True
    assert {"path": ".ai/owner-note.txt", "code": "unknown"} in planned["issues"]
    assert tree(installed_repository) == before
