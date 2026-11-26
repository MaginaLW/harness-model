"""Unit tests for non-overwriting external Python candidate policy rendering."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from aiflow import cli, initialization
from aiflow.contracts import schema_directory_context
from aiflow.errors import AiflowError, ContractError
from aiflow.policy import POLICY_FILES, load_policy_bundle
from aiflow.resource_bundle import build_bundle
from aiflow.verification import PYTEST_CHECK_IDS, VerificationContext, parse_verification_plan

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def policy_render_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("render-bundle")
    manifest, resources = build_bundle(ROOT)
    for relative, data in resources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def sample_python_repo_seed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    import subprocess

    root = tmp_path_factory.mktemp("external-python-seed")
    subprocess.run(["git", "init", "--template=", "-b", "main", str(root)], check=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sample-pkg"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (root / "src" / "sample_pkg").mkdir(parents=True)
    (root / "src" / "sample_pkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "seed",
        ],
        check=True,
    )
    return root


def _rewrite_bundle_manifest(bundle: Path) -> None:
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        data = (bundle / entry["path"]).read_bytes()
        entry["size"] = len(data)
        entry["sha256"] = hashlib.sha256(data).hexdigest()
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.mark.parametrize(
    ("cov_target", "raw_sources", "expected_sources"),
    [
        ("sample_pkg", ["src/sample_pkg"], ["src/sample_pkg"]),
        (
            "src/sample_pkg",
            ["src/pkg_a", "src/pkg_b", "src/pkg_a"],
            ["src/pkg_a", "src/pkg_b"],
        ),
        (
            "pkg.subpkg",
            ("packages/core", "packages/cli", "packages/core"),
            ["packages/core", "packages/cli"],
        ),
    ],
)
def test_render_python_policy_valid_single_multi_and_dedup(
    tmp_path: Path,
    policy_render_bundle: Path,
    cov_target: str,
    raw_sources: list[str] | tuple[str, ...],
    expected_sources: list[str],
) -> None:
    output_dir = tmp_path / "rendered-policy"
    summary = initialization.render_python_policy(
        output_dir,
        cov_target=cov_target,
        sources=raw_sources,
        bundle_root=policy_render_bundle,
    )

    assert summary["schema_version"] == "1.0"
    assert summary["kind"] == "aiflow-rendered-python-policy"
    assert summary["policy_version"] == "2.6.0"
    assert summary["cov_target"] == cov_target
    assert summary["sources"] == expected_sources
    assert [entry["path"] for entry in summary["files"]] == sorted(POLICY_FILES)

    for filename in ("hard-rules.yaml", "routing.yaml", "permissions.yaml"):
        assert (output_dir / filename).read_bytes() == (
            policy_render_bundle / "policy" / filename
        ).read_bytes()

    rendered_bytes = (output_dir / "verification-levels.yaml").read_bytes()
    assert b"\r" not in rendered_bytes
    verification_doc = yaml.safe_load(rendered_bytes.decode("utf-8"))
    levels = {level["id"]: level for level in verification_doc["levels"]}
    assert list(levels) == ["V0", "V1", "V2"]
    for level_id in ("V1", "V2"):
        by_id = {check["id"]: check for check in levels[level_id]["checks"]}
        for check_id in PYTEST_CHECK_IDS & set(by_id):
            assert f"--cov={cov_target}" in by_id[check_id]["command"]
            assert "--cov=aiflow" not in by_id[check_id]["command"]
        expected_tail = [arg for src in expected_sources for arg in ("--source", src)]
        assert by_id["diff_coverage"]["command"] == [
            "{python}",
            "-m",
            "aiflow.coverage_check",
            "--run-dir",
            "{run_dir}",
            "--base",
            "{base_commit}",
            *expected_tail,
        ]

    with schema_directory_context(policy_render_bundle / "schemas"):
        loaded = load_policy_bundle(tmp_path, policy_directory=output_dir)
        assert loaded.sha256 == summary["semantic_sha256"]
        context = VerificationContext(tmp_path, "TASK-0001", "0" * 40, "0" * 40, "python", "init")
        for level_id in ("V0", "V1", "V2"):
            plan = parse_verification_plan(
                loaded, context, level=level_id, tool_available=lambda _: True
            )
            assert plan.valid

    for entry in summary["files"]:
        data = (output_dir / entry["path"]).read_bytes()
        assert entry["size"] == len(data)
        assert entry["sha256"] == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize(
    "bad_cov",
    ["", "../bad", "src/../bad", "a..b", "/abs/pkg", "pkg/", "pkg\\sub", "--flag", "123bad", 123],
)
def test_render_python_policy_rejects_invalid_cov_target(
    tmp_path: Path, policy_render_bundle: Path, bad_cov: object
) -> None:
    output_dir = tmp_path / "out"
    with pytest.raises(AiflowError) as caught:
        initialization.render_python_policy(
            output_dir,
            cov_target=bad_cov,  # type: ignore[arg-type]
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught.value.code == "INITIALIZATION_PYTHON_COV_TARGET_INVALID"
    assert not output_dir.exists()


@pytest.mark.parametrize(
    "bad_sources",
    [
        [],
        (),
        "src/pkg",
        [""],
        ["/abs/src"],
        ["src/"],
        ["src/../escape"],
        ["src\\pkg"],
        ["src with space"],
        ["src/good", "bad\\source"],
    ],
)
def test_render_python_policy_rejects_invalid_sources(
    tmp_path: Path, policy_render_bundle: Path, bad_sources: object
) -> None:
    output_dir = tmp_path / "out"
    with pytest.raises(AiflowError) as caught:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=bad_sources,  # type: ignore[arg-type]
            bundle_root=policy_render_bundle,
        )
    assert caught.value.code == "INITIALIZATION_PYTHON_SOURCE_INVALID"
    assert not output_dir.exists()


def test_render_python_policy_rejects_parent_traversal(
    tmp_path: Path, policy_render_bundle: Path
) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    traversal = nested / ".." / "out"
    with pytest.raises(AiflowError) as caught:
        initialization.render_python_policy(
            traversal,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught.value.code == "INITIALIZATION_OUTPUT_PATH_INVALID"
    assert not (tmp_path / "out").exists()


def test_render_python_policy_refuses_existing_directory_or_file(
    tmp_path: Path, policy_render_bundle: Path
) -> None:
    existing_dir = tmp_path / "existing-dir"
    existing_dir.mkdir()
    marker = existing_dir / "keep.txt"
    marker.write_bytes(b"preserve")
    with pytest.raises(AiflowError) as caught_dir:
        initialization.render_python_policy(
            existing_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_dir.value.code == "INITIALIZATION_OUTPUT_EXISTS"
    assert marker.read_bytes() == b"preserve"
    assert not (existing_dir / "verification-levels.yaml").exists()

    existing_file = tmp_path / "existing-file"
    existing_file.write_bytes(b"keep-file")
    with pytest.raises(AiflowError) as caught_file:
        initialization.render_python_policy(
            existing_file,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_file.value.code == "INITIALIZATION_OUTPUT_EXISTS"
    assert existing_file.read_bytes() == b"keep-file"


def test_render_python_policy_rejects_missing_non_dir_and_reparse_parent(
    tmp_path: Path, policy_render_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_parent = tmp_path / "missing" / "out"
    with pytest.raises(AiflowError) as caught_missing:
        initialization.render_python_policy(
            missing_parent,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_missing.value.code == "INITIALIZATION_PATH_UNAVAILABLE"

    file_parent = tmp_path / "file-parent"
    file_parent.write_bytes(b"not-a-dir")
    with pytest.raises(AiflowError) as caught_type:
        initialization.render_python_policy(
            file_parent / "out",
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_type.value.code == "INITIALIZATION_PATH_TYPE"

    reparse_parent = tmp_path / "reparse-parent"
    reparse_parent.mkdir()
    original_lstat = Path.lstat

    def fake_lstat(self: Path) -> os.stat_result | SimpleNamespace:
        info = original_lstat(self)
        if self == reparse_parent:
            return SimpleNamespace(
                st_mode=stat.S_IFDIR | 0o755,
                st_file_attributes=0x400,
                st_nlink=1,
            )
        return info

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(AiflowError) as caught_link:
        initialization.render_python_policy(
            reparse_parent / "out",
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_link.value.code == "INITIALIZATION_PATH_LINK"
    assert not (reparse_parent / "out").exists()


def test_render_python_policy_rejects_missing_corrupt_or_non_fs_bundle(
    tmp_path: Path, policy_render_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "out"

    with pytest.raises(AiflowError) as caught_missing:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=tmp_path / "missing-bundle",
        )
    assert caught_missing.value.code == "INITIALIZATION_PATH_UNAVAILABLE"
    assert not output_dir.exists()

    corrupt_bundle = tmp_path / "corrupt-bundle"
    shutil.copytree(policy_render_bundle, corrupt_bundle)
    (corrupt_bundle / "policy" / "routing.yaml").write_text("corrupted: true\n", encoding="utf-8")
    with pytest.raises(AiflowError) as caught_corrupt:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=corrupt_bundle,
        )
    assert caught_corrupt.value.code == "INITIALIZATION_BUNDLE_OR_POLICY_INVALID"
    assert not output_dir.exists()

    missing_cov_bundle = tmp_path / "missing-cov-bundle"
    shutil.copytree(policy_render_bundle, missing_cov_bundle)
    ver_path = missing_cov_bundle / "policy" / "verification-levels.yaml"
    ver_doc = yaml.safe_load(ver_path.read_text(encoding="utf-8"))
    ver_doc["levels"][1]["checks"][5]["command"] = [
        "{python}",
        "-m",
        "pytest",
        "--cov=other",
        "--cov-branch",
        "--cov-report=xml:{run_dir}/coverage.xml",
    ]
    ver_path.write_text(yaml.safe_dump(ver_doc, sort_keys=False), encoding="utf-8")
    _rewrite_bundle_manifest(missing_cov_bundle)
    with pytest.raises(AiflowError) as caught_ver:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=missing_cov_bundle,
        )
    assert caught_ver.value.code == "INITIALIZATION_BUNDLE_OR_POLICY_INVALID"
    assert not output_dir.exists()

    for bad_ver_doc in (
        {
            "schema_version": "1.0",
            "policy_version": "2.6.0",
            "policy_kind": "verification_levels",
            "levels": "bad",
        },
        {
            "schema_version": "1.0",
            "policy_version": "2.6.0",
            "policy_kind": "verification_levels",
            "levels": [{"id": "V0", "checks": "bad"}],
        },
        {
            "schema_version": "1.0",
            "policy_version": "2.6.0",
            "policy_kind": "verification_levels",
            "levels": [{"id": "V0", "checks": ["bad"]}],
        },
    ):
        bad_ver_bundle = tmp_path / f"bad-ver-{hash(str(bad_ver_doc))}"
        shutil.copytree(policy_render_bundle, bad_ver_bundle)
        (bad_ver_bundle / "policy" / "verification-levels.yaml").write_text(
            yaml.safe_dump(bad_ver_doc, sort_keys=False), encoding="utf-8"
        )
        _rewrite_bundle_manifest(bad_ver_bundle)
        with pytest.raises(AiflowError) as caught_bad_ver:
            initialization.render_python_policy(
                output_dir,
                cov_target="pkg",
                sources=["src/pkg"],
                bundle_root=bad_ver_bundle,
            )
        assert caught_bad_ver.value.code == "INITIALIZATION_BUNDLE_OR_POLICY_INVALID"
        assert not output_dir.exists()

    monkeypatch.setattr(
        initialization,
        "files",
        lambda _pkg: SimpleNamespace(joinpath=lambda _name: object()),
    )
    with pytest.raises(AiflowError) as caught_non_fs:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=None,
        )
    assert caught_non_fs.value.code == "INITIALIZATION_BUNDLE_FILESYSTEM_REQUIRED"
    assert not output_dir.exists()


def test_render_python_policy_staging_and_write_failures_leave_no_output_on_staging_error(
    tmp_path: Path, policy_render_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "out"

    def fail_parse(*_args: object, **_kwargs: object) -> object:
        raise ContractError("forced staging parse error", code="VERIFICATION_POLICY_INVALID")

    monkeypatch.setattr(initialization, "parse_verification_plan", fail_parse)
    with pytest.raises(AiflowError) as caught_stage:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_stage.value.code == "VERIFICATION_POLICY_INVALID"
    assert not output_dir.exists()

    monkeypatch.undo()
    real_mkdir = os.mkdir

    def mkdir_race(path: Path | str, *args: object) -> None:
        if Path(path) == output_dir.absolute():
            raise FileExistsError("race")
        real_mkdir(path, *args)  # type: ignore[arg-type]

    monkeypatch.setattr(initialization.os, "mkdir", mkdir_race)
    with pytest.raises(AiflowError) as caught_race:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_race.value.code == "INITIALIZATION_OUTPUT_EXISTS"

    def mkdir_denied(path: Path | str, *args: object) -> None:
        if Path(path) == output_dir.absolute():
            raise PermissionError("denied")
        real_mkdir(path, *args)  # type: ignore[arg-type]

    monkeypatch.setattr(initialization.os, "mkdir", mkdir_denied)
    with pytest.raises(AiflowError) as caught_mkdir:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_mkdir.value.code == "INITIALIZATION_WRITE_FAILED"

    monkeypatch.undo()
    real_open = open

    def fail_open(file: Path | str, mode: str = "r", *args: object, **kwargs: object) -> object:
        if mode == "xb" and Path(file).parent == output_dir.absolute():
            raise OSError("disk full")
        return real_open(file, mode, *args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr("builtins.open", fail_open)
    with pytest.raises(AiflowError) as caught_write:
        initialization.render_python_policy(
            output_dir,
            cov_target="pkg",
            sources=["src/pkg"],
            bundle_root=policy_render_bundle,
        )
    assert caught_write.value.code == "INITIALIZATION_WRITE_FAILED"


def test_render_python_policy_cli_and_preview_apply_migration_integration(
    tmp_path: Path,
    policy_render_bundle: Path,
    sample_python_repo_seed: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    policy_dir = outside / "rendered-policy"

    exit_code = cli.main(
        [
            "init",
            "render-python-policy",
            "--output-dir",
            str(policy_dir),
            "--cov-target",
            "sample_pkg",
            "--source",
            "src/sample_pkg",
            "--source",
            "src/sample_pkg",
            "--bundle-root",
            str(policy_render_bundle),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    rendered = json.loads(captured.out)
    assert rendered["kind"] == "aiflow-rendered-python-policy"
    assert rendered["sources"] == ["src/sample_pkg"]

    assert (
        cli.main(
            [
                "init",
                "render-python-policy",
                "--output-dir",
                str(policy_dir),
                "--cov-target",
                "sample_pkg",
                "--source",
                "src/sample_pkg",
                "--bundle-root",
                str(policy_render_bundle),
            ]
        )
        == 1
    )
    err_captured = capsys.readouterr()
    assert err_captured.out == ""
    assert "OUTPUT_EXISTS" in err_captured.err
    assert "Traceback" not in err_captured.err

    repo = tmp_path / "target-repo"
    shutil.copytree(sample_python_repo_seed, repo)
    preview = initialization.preview_initialization(
        repo, bundle_root=policy_render_bundle, policy_directory=policy_dir
    )
    review = {
        "schema_version": "1.0",
        "kind": "aiflow-policy-review",
        "preview_sha256": preview["preview_sha256"],
        "repository_id": preview["repository_id"],
        "profile": preview["profile"],
        "policy_version": preview["policy"]["policy_version"],
        "policies": [
            {"path": entry["path"], "sha256": entry["sha256"]}
            for entry in preview["policy"]["files"]
        ],
        "reviewer": "independent-reviewer",
        "outcome": "APPROVE",
    }
    applied = initialization.apply_initialization(
        repo,
        preview,
        review,
        bundle_root=policy_render_bundle,
        policy_directory=policy_dir,
    )
    assert applied["phase"] == "installed"
    assert initialization.inspect_initialization(repo)["status"] == "complete"

    migration = initialization.plan_initialization_migration(
        repo, bundle_root=policy_render_bundle, policy_directory=policy_dir
    )
    assert migration["read_only"] is True
    assert all(item["status"] == "unchanged" for item in migration["files"])
