"""Policy loading, cross-file validation, and digest tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from aiflow.errors import PolicyError
from aiflow.policy import POLICY_FILES, load_policy_bundle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_POLICY = PROJECT_ROOT / ".ai" / "policy"


def copy_policy(tmp_path: Path) -> Path:
    target = tmp_path / "policy"
    shutil.copytree(SOURCE_POLICY, target)
    return target


def read(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def test_valid_policy_has_complete_stable_bundle() -> None:
    bundle = load_policy_bundle(PROJECT_ROOT)

    assert set(bundle.documents) == set(POLICY_FILES)
    assert bundle.policy_version == "1.0.0"
    assert len(bundle.sha256) == 64
    assert bundle.sha256 == load_policy_bundle(PROJECT_ROOT).sha256


def test_missing_fixed_file_is_rejected(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    (policy / "routing.yaml").unlink()

    with pytest.raises(PolicyError) as caught:
        load_policy_bundle(tmp_path, policy_directory=policy)

    assert caught.value.code == "POLICY_FILE_MISSING"


def test_conflicting_extension_is_rejected(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    (policy / "routing.yml").write_text("conflict: true\n", encoding="utf-8")

    with pytest.raises(PolicyError) as caught:
        load_policy_bundle(tmp_path, policy_directory=policy)

    assert caught.value.code == "POLICY_FILE_CONFLICT"


def test_policy_file_symlink_escape_is_rejected(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    (repository / ".ai").mkdir(parents=True)
    outside = copy_policy(tmp_path / "outside")
    link = repository / ".ai" / "policy"
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"junction creation unavailable: {result.stderr}")
    else:
        link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(PolicyError) as caught:
        load_policy_bundle(repository)

    assert caught.value.code == "POLICY_PATH_ESCAPE"


def test_unknown_field_is_rejected_by_schema(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    path = policy / "routing.yaml"
    value = read(path)
    value["unknown"] = "not allowed"
    write(path, value)

    with pytest.raises(PolicyError) as caught:
        load_policy_bundle(tmp_path, policy_directory=policy)

    assert caught.value.code == "POLICY_SCHEMA_INVALID"


def test_duplicate_rule_id_is_rejected(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    path = policy / "routing.yaml"
    value = read(path)
    value["rules"][0]["id"] = "HARD-BLOCK-EXTERNAL-SENSITIVE"  # type: ignore[index]
    write(path, value)

    with pytest.raises(PolicyError) as caught:
        load_policy_bundle(tmp_path, policy_directory=policy)

    assert caught.value.code == "POLICY_RULE_ID_DUPLICATE"


def test_duplicate_priority_is_rejected(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    path = policy / "routing.yaml"
    value = read(path)
    value["rules"][0]["priority"] = 1000  # type: ignore[index]
    write(path, value)

    with pytest.raises(PolicyError) as caught:
        load_policy_bundle(tmp_path, policy_directory=policy)

    assert caught.value.code == "POLICY_RULE_PRIORITY_DUPLICATE"


def test_unknown_predicate_and_command_string_are_rejected(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    routing = read(policy / "routing.yaml")
    routing["rules"][0]["conditions"][0]["operator"] = "execute"  # type: ignore[index]
    write(policy / "routing.yaml", routing)
    with pytest.raises(PolicyError) as predicate_error:
        load_policy_bundle(tmp_path, policy_directory=policy)
    assert predicate_error.value.code == "POLICY_SCHEMA_INVALID"

    policy = copy_policy(tmp_path / "second")
    levels = read(policy / "verification-levels.yaml")
    levels["levels"][0]["checks"][0]["command"] = "python -m aiflow"  # type: ignore[index]
    write(policy / "verification-levels.yaml", levels)
    with pytest.raises(PolicyError) as command_error:
        load_policy_bundle(tmp_path, policy_directory=policy)
    assert command_error.value.code == "POLICY_SCHEMA_INVALID"


def test_missing_permission_reference_is_rejected(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    path = policy / "permissions.yaml"
    value = read(path)
    value["rules"] = value["rules"][1:]  # type: ignore[index]
    write(path, value)

    with pytest.raises(PolicyError) as caught:
        load_policy_bundle(tmp_path, policy_directory=policy)

    assert caught.value.code == "POLICY_PERMISSION_REFERENCE_INVALID"


def test_comment_and_newline_changes_do_not_change_digest(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    before = load_policy_bundle(tmp_path, policy_directory=policy).sha256
    path = policy / "routing.yaml"
    path.write_text(
        "# comment\r\n" + path.read_text(encoding="utf-8").replace("\n", "\r\n"), encoding="utf-8"
    )

    assert load_policy_bundle(tmp_path, policy_directory=policy).sha256 == before


def test_semantic_rule_change_changes_digest(tmp_path: Path) -> None:
    policy = copy_policy(tmp_path)
    before = load_policy_bundle(tmp_path, policy_directory=policy).sha256
    path = policy / "routing.yaml"
    value = read(path)
    value["rules"][0]["explanation"] = "A changed semantic explanation."  # type: ignore[index]
    write(path, value)

    assert load_policy_bundle(tmp_path, policy_directory=policy).sha256 != before
