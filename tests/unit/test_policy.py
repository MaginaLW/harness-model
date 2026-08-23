"""Policy loading, cross-file validation, and digest tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from aiflow.errors import PolicyError
from aiflow.policy import POLICY_FILES, _validate_cross_file, load_policy_bundle

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


def v2_documents() -> dict[str, dict[str, object]]:
    """Return an independent copy of the active V2 Policy documents."""
    return {filename: read(SOURCE_POLICY / filename) for filename in POLICY_FILES}


def v1_documents() -> dict[str, dict[str, object]]:
    """Build a legacy 1.x bundle to prove the old V0/V1 branch remains valid."""
    documents = v2_documents()
    for document in documents.values():
        document["policy_version"] = "1.0.0"
    levels = documents["verification-levels.yaml"]["levels"]
    assert isinstance(levels, list)
    del levels[2:]
    return documents


def test_valid_policy_has_complete_stable_bundle() -> None:
    bundle = load_policy_bundle(PROJECT_ROOT)

    assert set(bundle.documents) == set(POLICY_FILES)
    assert bundle.policy_version == "2.0.0"
    assert len(bundle.sha256) == 64
    assert bundle.sha256 == load_policy_bundle(PROJECT_ROOT).sha256


def test_legacy_v1_policy_branch_remains_valid() -> None:
    assert _validate_cross_file(v1_documents()) == "1.0.0"


def test_unknown_policy_major_version_is_rejected() -> None:
    documents = v2_documents()
    for document in documents.values():
        document["policy_version"] = "3.0.0"
    with pytest.raises(PolicyError) as caught:
        _validate_cross_file(documents)
    assert caught.value.code == "POLICY_LEVEL_INVALID"


def test_v1_must_preserve_the_semantic_v0_prefix() -> None:
    documents = v2_documents()
    levels = documents["verification-levels.yaml"]["levels"]
    assert isinstance(levels, list)
    v1 = levels[1]
    assert isinstance(v1, dict)
    checks = v1["checks"]
    assert isinstance(checks, list)
    checks[0]["timeout_seconds"] = 31
    with pytest.raises(PolicyError) as caught:
        _validate_cross_file(documents)
    assert caught.value.code == "POLICY_CHECK_REFERENCE_INVALID"


def test_v2_policy_requires_ordered_semantic_prefix_and_fixed_required_extras() -> None:
    documents = v2_documents()
    assert _validate_cross_file(documents) == "2.0.0"

    levels = documents["verification-levels.yaml"]["levels"]
    assert isinstance(levels, list)
    levels[1], levels[2] = levels[2], levels[1]
    with pytest.raises(PolicyError) as caught:
        _validate_cross_file(documents)
    assert caught.value.code == "POLICY_LEVEL_INVALID"

    documents = v2_documents()
    levels = documents["verification-levels.yaml"]["levels"]
    assert isinstance(levels, list)
    v2 = levels[2]
    assert isinstance(v2, dict)
    checks = v2["checks"]
    assert isinstance(checks, list)
    checks[0]["timeout_seconds"] = 31
    with pytest.raises(PolicyError) as caught:
        _validate_cross_file(documents)
    assert caught.value.code == "POLICY_CHECK_REFERENCE_INVALID"

    documents = v2_documents()
    levels = documents["verification-levels.yaml"]["levels"]
    assert isinstance(levels, list)
    v2 = levels[2]
    assert isinstance(v2, dict)
    checks = v2["checks"]
    assert isinstance(checks, list)
    checks[-1]["required"] = False
    with pytest.raises(PolicyError) as caught:
        _validate_cross_file(documents)
    assert caught.value.code == "POLICY_CHECK_REFERENCE_INVALID"


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
