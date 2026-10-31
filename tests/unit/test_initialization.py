"""Public initialization behavior in small, disposable Git repositories."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from uuid import UUID

import pytest
from initialization_helpers import PortableFilesystem

from aiflow.errors import AiflowError
from aiflow.resource_bundle import RESOURCE_KINDS, build_bundle

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


def git(root: Path, *arguments: str) -> str:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", *arguments],
        cwd=root,
        env=environment,
        capture_output=True,
        check=True,
        encoding="utf-8",
        timeout=15,
    )
    return result.stdout.rstrip("\r\n")


def tree(root: Path) -> dict[str, tuple[object, ...]]:
    """Observe all fixture bytes and directory entries without following links."""
    result: dict[str, tuple[object, ...]] = {}
    for directory, directories, filenames in os.walk(root, followlinks=False):
        for name in (*directories, *filenames):
            path = Path(directory) / name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                result[relative] = ("link", os.readlink(path))
            elif path.is_dir():
                result[relative] = ("directory", info.st_dev, info.st_ino)
            else:
                result[relative] = (
                    "file",
                    info.st_dev,
                    info.st_ino,
                    info.st_mtime_ns,
                    path.read_bytes(),
                )
    return result


@pytest.fixture(scope="session")
def initialization_seed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("initialization-seed")
    git(root, "init", "-b", "feature")
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
    return root


@pytest.fixture
def repository(tmp_path: Path, initialization_seed: Path) -> Path:
    root = tmp_path / "repository"
    # A byte copy keeps every fixture ordinary and avoids a Git reference to another root.
    shutil.copytree(initialization_seed, root)
    return root


@pytest.fixture(scope="session")
def initialization_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("initialization-bundle")
    manifest, resources = build_bundle(ROOT)
    for relative, data in resources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


@pytest.fixture
def bundle(tmp_path: Path, initialization_bundle: Path) -> Path:
    root = tmp_path / "bundle"
    shutil.copytree(initialization_bundle, root)
    return root


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


def test_preview_is_read_only_and_binds_a_fresh_uuid(repository: Path, bundle: Path) -> None:
    before, bundle_before = tree(repository), tree(bundle)
    first, second = preview(repository, bundle), preview(repository / "folder", bundle)

    assert tree(repository) == before
    assert tree(bundle) == bundle_before
    assert first["schema_version"] == "1.0"
    assert first["kind"] == "aiflow-init-preview"
    assert first["profile"] == "native-python-v1"
    identifier = UUID(first["repository_id"])
    assert identifier.version == 4
    assert str(identifier) == first["repository_id"]
    assert first["repository_id"] != second["repository_id"]
    assert first["target"] == second["target"]
    assert len(first["preview_sha256"]) == 64
    assert not (repository / ".ai").exists()


def test_preview_keeps_existing_dirty_and_ignored_material(repository: Path, bundle: Path) -> None:
    (repository / "README.md").write_bytes(b"user work\n")
    (repository / "untracked.txt").write_bytes(b"not an installer output\n")
    (repository / ".private").mkdir()
    secret = repository / ".private/secret.txt"
    secret.write_bytes(b"private-fixture-marker-do-not-copy")
    before = tree(repository)

    candidate = preview(repository, bundle)

    assert tree(repository) == before
    assert b"private-fixture-marker-do-not-copy" not in json.dumps(candidate).encode()
    assert not (repository / ".ai").exists()


def test_branch_named_detached_is_distinct_from_detached_head(
    repository: Path, bundle: Path
) -> None:
    git(repository, "switch", "-c", "DETACHED")
    branch = preview(repository, bundle)
    git(repository, "switch", "--detach", "HEAD")
    detached = preview(repository, bundle)

    assert branch["target"] != detached["target"]


def test_preview_does_not_invoke_configured_fsmonitor(repository: Path, bundle: Path) -> None:
    marker = repository / ".git/fsmonitor-was-called"
    helper = repository / ".git/untrusted-fsmonitor.py"
    helper.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('unexpected external command')\n",
        encoding="utf-8",
    )
    git(repository, "config", "core.fsmonitor", f'"{sys.executable}" "{helper}"')
    before = tree(repository)

    preview(repository, bundle)

    assert not marker.exists()
    assert tree(repository) == before


@pytest.mark.parametrize("profile", ["node-v0", "node-v1", "", "python", None, 1])
def test_unsupported_profile_rejects_before_any_target_write(
    repository: Path, bundle: Path, profile: object
) -> None:
    before = tree(repository)
    with pytest.raises(AiflowError):
        initialization.preview_initialization(repository, bundle_root=bundle, profile=profile)
    assert tree(repository) == before


def test_node_target_cannot_be_installed_under_the_python_label(
    repository: Path, bundle: Path
) -> None:
    (repository / "package.json").write_bytes(b'{"name":"node-fixture","scripts":{"check":"true"}}')
    before = tree(repository)
    with pytest.raises(AiflowError):
        preview(repository, bundle)
    assert tree(repository) == before


@pytest.mark.parametrize(
    "content", [None, b"", b"not valid [toml", b"[project]\n", b"[project]\nname=1\n"]
)
def test_missing_or_invalid_python_project_is_rejected(
    repository: Path, bundle: Path, content: bytes | None
) -> None:
    path = repository / "pyproject.toml"
    if content is None:
        path.unlink()
    else:
        path.write_bytes(content)
    before = tree(repository)
    with pytest.raises(AiflowError):
        preview(repository, bundle)
    assert tree(repository) == before


@pytest.mark.parametrize(
    "name", ["manifest.json", "schemas/policy.schema.json", "policy/routing.yaml"]
)
def test_missing_bundle_material_rejects_without_target_writes(
    repository: Path, bundle: Path, name: str
) -> None:
    (bundle / name).unlink()
    before = tree(repository)
    with pytest.raises(AiflowError):
        preview(repository, bundle)
    assert tree(repository) == before


@pytest.mark.parametrize(
    "name", ["schemas/policy.schema.json", "policy/routing.yaml", "templates/spec.md"]
)
def test_changed_bundle_material_rejects_without_target_writes(
    repository: Path, bundle: Path, name: str
) -> None:
    with (bundle / name).open("ab") as stream:
        stream.write(b"\nchanged\n")
    before = tree(repository)
    with pytest.raises(AiflowError):
        preview(repository, bundle)
    assert tree(repository) == before


def test_extra_bundle_entry_rejects_without_target_writes(repository: Path, bundle: Path) -> None:
    (bundle / "unexpected.txt").write_bytes(b"unknown\n")
    before = tree(repository)
    with pytest.raises(AiflowError):
        preview(repository, bundle)
    assert tree(repository) == before


@pytest.mark.parametrize("change", ["missing", "extra", "invalid", "hardlink", "directory"])
def test_policy_candidate_must_be_exact_and_ordinary(
    repository: Path, bundle: Path, tmp_path: Path, change: str
) -> None:
    candidate = tmp_path / "candidate-policy"
    shutil.copytree(bundle / "policy", candidate)
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
    before = tree(repository)

    with pytest.raises(AiflowError):
        initialization.preview_initialization(
            repository, bundle_root=bundle, policy_directory=candidate
        )
    assert tree(repository) == before


def test_policy_candidate_cannot_supply_a_weaker_schema(
    repository: Path, bundle: Path, tmp_path: Path
) -> None:
    candidate = tmp_path / "candidate-policy"
    shutil.copytree(bundle / "policy", candidate)
    (candidate / "policy.schema.json").write_bytes(b"{}")
    (candidate / "routing.yaml").write_bytes(b"arbitrary: true\n")
    before = tree(repository)

    with pytest.raises(AiflowError):
        initialization.preview_initialization(
            repository, bundle_root=bundle, policy_directory=candidate
        )
    assert tree(repository) == before


def test_policy_review_binds_candidate_bytes_not_just_semantics(
    repository: Path, bundle: Path, tmp_path: Path
) -> None:
    candidate = tmp_path / "candidate-policy"
    shutil.copytree(bundle / "policy", candidate)
    initial = initialization.preview_initialization(
        repository, bundle_root=bundle, policy_directory=candidate
    )
    decision = review(initial)
    with (candidate / "routing.yaml").open("ab") as stream:
        stream.write(b"\n# Different reviewed bytes with the same Policy semantics.\n")
    before = tree(repository)

    with pytest.raises(AiflowError):
        initialization.apply_initialization(
            repository,
            initial,
            decision,
            bundle_root=bundle,
            policy_directory=candidate,
        )
    assert tree(repository) == before


@pytest.mark.parametrize("kind", ["directory", "file", "case-alias"])
def test_unknown_ai_created_after_preview_is_preserved(
    repository: Path, bundle: Path, kind: str
) -> None:
    candidate = preview(repository, bundle)
    if kind == "file":
        (repository / ".ai").write_bytes(b"unknown\n")
    else:
        directory = repository / (".AI" if kind == "case-alias" else ".ai")
        directory.mkdir()
        (directory / "owner.txt").write_bytes(b"preexisting owner data\n")
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert tree(repository) == before


@pytest.mark.parametrize(
    "field", ["repository_id", "profile", "preview_sha256", "objects", "target"]
)
def test_tampered_preview_is_rejected_without_writes(
    repository: Path, bundle: Path, field: str
) -> None:
    candidate = preview(repository, bundle)
    decision = review(candidate)
    candidate[field] = "tampered"
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle, decision)
    assert tree(repository) == before


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
    repository: Path, bundle: Path, field: str, value: object
) -> None:
    candidate = preview(repository, bundle)
    decision = review(candidate)
    decision[field] = value
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle, decision)
    assert tree(repository) == before


@pytest.mark.parametrize("entry", ["preview", "review"])
def test_unknown_top_level_fields_are_rejected(repository: Path, bundle: Path, entry: str) -> None:
    candidate = preview(repository, bundle)
    decision = review(candidate)
    (candidate if entry == "preview" else decision)["unknown"] = True
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle, decision)
    assert tree(repository) == before


@pytest.mark.parametrize("change", ["digest", "duplicate", "missing", "extra-field"])
def test_review_requires_four_exact_policy_digests(
    repository: Path, bundle: Path, change: str
) -> None:
    candidate = preview(repository, bundle)
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
    repository: Path, bundle: Path, drift: str
) -> None:
    candidate = preview(repository, bundle)
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
        apply(repository, candidate, bundle)
    assert tree(repository) == before


def test_apply_rejects_bundle_drift_after_review(repository: Path, bundle: Path) -> None:
    candidate = preview(repository, bundle)
    (bundle / "templates/spec.md").write_bytes(b"changed after review\n")
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert tree(repository) == before


def test_preview_cannot_be_reused_for_another_clone(
    repository: Path, bundle: Path, tmp_path: Path
) -> None:
    candidate = preview(repository, bundle)
    clone = tmp_path / "another-clone"
    shutil.copytree(repository, clone)
    before = tree(clone)
    with pytest.raises(AiflowError):
        apply(clone, candidate, bundle)
    assert tree(clone) == before


def test_unsupported_platform_application_does_not_write(
    repository: Path, bundle: Path, native_filesystem: None
) -> None:
    candidate = preview(repository, bundle)
    # This is the real boundary on POSIX; Windows behavior is covered below.
    if sys.platform == "win32":
        pytest.skip("unsupported-platform behavior is exercised on POSIX")
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert tree(repository) == before


def test_install_creates_only_planned_resources_and_a_fresh_identity(
    repository: Path, bundle: Path
) -> None:
    candidate = preview(repository, bundle)
    original = tree(repository)

    result = apply(repository, candidate, bundle)

    assert result["phase"] == "installed"
    assert (repository / ".ai/repository-id").read_text("utf-8").strip() == candidate[
        "repository_id"
    ]
    assert not (repository / ".ai/.repository-id.pending").exists()
    for relative in RESOURCE_KINDS:
        assert (repository / ".ai" / relative).read_bytes() == (bundle / relative).read_bytes()
    after = tree(repository)
    assert {path: value for path, value in after.items() if path.split("/")[0] != ".ai"} == original
    assert not (repository / ".ai/bootstrap-mode.yaml").exists()
    assert not (repository / ".ai/tasks").exists()
    initialization.require_initialization_ready(repository)


def test_completed_replay_is_byte_and_metadata_preserving(repository: Path, bundle: Path) -> None:
    candidate = preview(repository, bundle)
    apply(repository, candidate, bundle)
    before = tree(repository)

    result = apply(repository, candidate, bundle)

    assert result["phase"] == "already_complete"
    assert tree(repository) == before


def test_verified_interruption_resumes_original_uuid_without_rewriting_completed_files(
    repository: Path, bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, bundle)
    create = PortableFilesystem.create_file

    def interrupt(self, parent_handle, name, **keywords):
        if name == "task.schema.json":
            raise AiflowError("injected interruption before creating the next object")
        return create(self, parent_handle, name, **keywords)

    monkeypatch.setattr(PortableFilesystem, "create_file", interrupt)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert (repository / ".ai/init-state.json").is_file()
    assert not (repository / ".ai/repository-id").exists()
    partial = tree(repository)
    monkeypatch.setattr(PortableFilesystem, "create_file", create)

    result = apply(repository, candidate, bundle)

    assert result["phase"] == "resumed"
    assert result["repository_id"] == candidate["repository_id"]
    final = tree(repository)
    for name, facts in partial.items():
        if name.endswith(".repository-id.pending"):
            continue
        assert final[name] == facts
    initialization.require_initialization_ready(repository)


def test_partially_written_object_is_preserved_and_cannot_be_resumed(
    repository: Path, bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, bundle)
    write = PortableFilesystem.write
    resource = (bundle / "schemas/task.schema.json").read_bytes()

    def interrupted_write(self, handle, data):
        if data == resource:
            write(self, handle, data[:11])
            raise AiflowError("injected incomplete file write")
        return write(self, handle, data)

    monkeypatch.setattr(PortableFilesystem, "write", interrupted_write)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    monkeypatch.setattr(PortableFilesystem, "write", write)
    before = tree(repository)

    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert tree(repository) == before
    assert not (repository / ".ai/repository-id").exists()


@pytest.mark.parametrize("stage", ["first", "complete"])
def test_flush_failure_never_publishes_a_successful_identity(
    repository: Path, bundle: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    candidate = preview(repository, bundle)
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
        apply(repository, candidate, bundle)
    assert not (repository / ".ai/repository-id").exists()
    with pytest.raises(AiflowError):
        initialization.require_initialization_ready(repository)


def test_competitor_at_atomic_directory_creation_is_preserved(
    repository: Path, bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, bundle)
    create = PortableFilesystem.create_directory
    foreign = repository / ".ai/foreign.txt"

    def compete(self, parent_handle, name, **keywords):
        if name == ".ai":
            foreign.parent.mkdir()
            foreign.write_bytes(b"competitor-owned bytes\n")
        return create(self, parent_handle, name, **keywords)

    monkeypatch.setattr(PortableFilesystem, "create_directory", compete)

    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert foreign.read_bytes() == b"competitor-owned bytes\n"
    assert sorted(path.name for path in foreign.parent.iterdir()) == ["foreign.txt"]


def test_competitor_identity_is_not_replaced_at_publication(
    repository: Path, bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = preview(repository, bundle)
    publish = PortableFilesystem.rename_no_replace
    foreign = repository / ".ai/repository-id"

    def compete(self, handle, target):
        foreign.write_bytes(b"competitor identity\n")
        return publish(self, handle, target)

    monkeypatch.setattr(PortableFilesystem, "rename_no_replace", compete)

    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert foreign.read_bytes() == b"competitor identity\n"
    before = tree(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert tree(repository) == before


@pytest.mark.parametrize("change", ["extra", "resource", "review", "identity", "state", "complete"])
def test_complete_installation_tampering_blocks_ready_and_replay(
    repository: Path, bundle: Path, change: str
) -> None:
    candidate = preview(repository, bundle)
    apply(repository, candidate, bundle)
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
        apply(repository, candidate, bundle)
    assert tree(repository) == before


def test_ready_guard_allows_normal_task_history_without_accepting_preview_replay(
    repository: Path, bundle: Path
) -> None:
    candidate = preview(repository, bundle)
    apply(repository, candidate, bundle)
    task = repository / ".ai/tasks/TASK-0001"
    task.mkdir(parents=True)
    (task / "history.txt").write_bytes(b"append-only fixture history\n")
    before = tree(repository)

    initialization.require_initialization_ready(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
    assert tree(repository) == before


def test_a_managed_file_with_another_hardlink_is_not_a_ready_installation(
    repository: Path, bundle: Path, tmp_path: Path
) -> None:
    candidate = preview(repository, bundle)
    apply(repository, candidate, bundle)
    resource = repository / ".ai/templates/spec.md"
    os.link(resource, tmp_path / "another-link.md")
    before = tree(repository)

    with pytest.raises(AiflowError):
        initialization.require_initialization_ready(repository)
    with pytest.raises(AiflowError):
        apply(repository, candidate, bundle)
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


def test_inspect_and_migration_plan_are_read_only(repository: Path, bundle: Path) -> None:
    candidate = preview(repository, bundle)
    apply(repository, candidate, bundle)
    before, bundle_before = tree(repository), tree(bundle)

    inspected = initialization.inspect_initialization(repository)
    migration = initialization.plan_initialization_migration(repository, bundle_root=bundle)

    assert isinstance(inspected, dict)
    assert isinstance(migration, dict)
    assert tree(repository) == before
    assert tree(bundle) == bundle_before
    serialized = json.dumps(migration)
    assert candidate["repository_id"] in serialized
    assert "readonly" in serialized.lower() or "read_only" in serialized.lower()


def test_persistent_installer_metadata_has_no_machine_paths(repository: Path, bundle: Path) -> None:
    candidate = preview(repository, bundle)
    apply(repository, candidate, bundle)

    for filename in ("init-state.json", "policy-review.json", "init-complete.json"):
        raw = (repository / ".ai" / filename).read_bytes()
        document = json.loads(raw)
        assert isinstance(document, dict)
        assert str(repository).encode() not in raw
        assert repository.as_posix().encode() not in raw
        assert str(bundle).encode() not in raw
        assert bundle.as_posix().encode() not in raw
    state = json.loads((repository / ".ai/init-state.json").read_bytes())
    assert candidate["repository_id"] in json.dumps(state)


def test_actual_windows_backend_installs_and_replays(
    repository: Path, bundle: Path, native_filesystem: None
) -> None:
    require_windows_apply()
    candidate = preview(repository, bundle)

    assert apply(repository, candidate, bundle)["phase"] == "installed"
    initialization.require_initialization_ready(repository)
    before = tree(repository)
    assert apply(repository, candidate, bundle)["phase"] == "already_complete"
    assert tree(repository) == before


def test_actual_windows_handles_hold_resources_until_identity_publication(
    repository: Path, bundle: Path, native_filesystem: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    require_windows_apply()
    from aiflow.initialization_windows import WindowsFilesystem

    candidate = preview(repository, bundle)
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

    assert apply(repository, candidate, bundle)["phase"] == "installed"
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
    repository: Path, bundle: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    before = tree(repository)

    result = run_cli(
        outside,
        "init",
        "preview",
        "--target",
        str(repository),
        "--profile",
        "native-python-v1",
        "--bundle-root",
        str(bundle),
    )

    assert result.returncode == 0, result.stderr
    candidate = json.loads(result.stdout)
    assert candidate["kind"] == "aiflow-init-preview"
    assert UUID(candidate["repository_id"]).version == 4
    assert tree(repository) == before
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(
    "data",
    [b"{}", b"[]", b'{"kind":1,"kind":2}', b"x" * (64 * 1024 + 1)],
    ids=["empty-object", "array", "duplicate-key", "oversize"],
)
def test_cli_rejects_invalid_review_input_before_target_writes(
    repository: Path, bundle: Path, tmp_path: Path, data: bytes
) -> None:
    candidate = preview(repository, bundle)
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
    repository: Path, bundle: Path, tmp_path: Path, native_filesystem: None
) -> None:
    require_windows_apply()
    candidate = preview(repository, bundle)
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
        str(bundle),
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
