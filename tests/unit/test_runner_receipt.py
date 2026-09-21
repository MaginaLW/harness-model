"""Runner receipt trust, freshness, failure propagation, and legacy association boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from tools.runner import receipt as subject

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "self-hosted-runner"
SCRIPT = ROOT / "tools" / "runner" / "receipt.py"


@pytest.fixture
def pair() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        subject.load_json(EXAMPLES / "runner-profile.example.json"),
        subject.load_json(EXAMPLES / "execution-receipt.example.json"),
    )


def test_synthetic_example_matches_without_asserting_authentication_or_gate(pair: Any) -> None:
    before = deepcopy(pair)
    result = subject.validate_receipt(*pair)
    assert result["status"] == "CONTRACT_MATCH"
    assert result["contract_matched"] is True
    assert result["source_authenticated"] is False
    assert result["artifact_content_verified"] is False
    assert result["governance_effect"] == "none"
    assert result["association_checked"] is False
    assert pair == before


@pytest.mark.parametrize(
    ("group", "field"),
    [
        ("code", "base_commit"),
        ("code", "subject_commit"),
        ("code", "checkout_commit"),
        ("code", "tree_sha256"),
        ("repository", "owner_name"),
        ("runner", "profile_id"),
        ("runner", "runner_version"),
        ("runner", "network_boundary_ref"),
        ("runner", "environment_sha256"),
        ("definition", "workflow_sha256"),
        ("definition", "check_set_sha256"),
        ("definition", "dependency_lock_sha256"),
    ],
)
def test_newline_suffixed_bindings_reject_even_when_both_documents_agree(
    pair: Any, group: str, field: str
) -> None:
    # I3-F1: matching two malformed values is not a valid full-length identity.
    for document in pair:
        document[group][field] += "\n"
    with pytest.raises(subject.ReceiptError, match="SCHEMA_MISMATCH"):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize("field", ["run_id", "job_id", "observation_sha256"])
def test_newline_suffixed_observer_identity_is_not_a_fresh_execution(pair: Any, field: str) -> None:
    pair[0]["run"][field] += "\n"
    pair[1]["source"][field] += "\n"
    with pytest.raises(subject.ReceiptError, match="SCHEMA_MISMATCH"):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize("field", ["id", "command_ref"])
def test_newline_suffixed_check_definition_rejects_matching_forgery(pair: Any, field: str) -> None:
    pair[0]["required_checks"][0][field] += "\n"
    pair[1]["checks"][0][field] += "\n"
    with pytest.raises(subject.ReceiptError, match="SCHEMA_MISMATCH"):
        subject.validate_receipt(*pair)


def test_newline_suffixed_artifact_digest_is_not_a_sha256(pair: Any) -> None:
    pair[0]["required_artifacts"][0]["sha256"] += "\n"
    pair[1]["artifacts"][0]["sha256"] += "\n"
    with pytest.raises(subject.ReceiptError, match="SCHEMA_MISMATCH"):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize(
    ("group", "field", "replacement"),
    [
        ("repository", "github_id", 654321),
        ("repository", "owner_name", "other/project"),
        ("repository", "github_id", True),
        ("repository", "visibility", "public"),
        ("repository", "trust", "unknown"),
        ("runner", "id", 43),
        ("runner", "id", True),
        ("runner", "id", 0),
        ("runner", "scope", "organization"),
        ("runner", "profile_id", "wrong-runner"),
        ("runner", "os", "Windows"),
        ("runner", "architecture", "ARM64"),
        ("runner", "runner_version", "2.100.0"),
        ("runner", "privilege", "administrator"),
        ("runner", "isolated_workspace", False),
        ("runner", "active_instances", 2),
        ("runner", "active_instances", True),
        ("runner", "environment_sha256", "1" * 64),
        ("code", "base_commit", "4" * 40),
        ("code", "subject_commit", "4" * 40),
        ("code", "checkout_commit", "4" * 40),
        ("code", "tree_sha256", "4" * 64),
        ("code", "dirty", True),
        ("definition", "workflow_sha256", "1" * 64),
        ("definition", "check_set_sha256", "1" * 64),
        ("definition", "dependency_lock_sha256", "1" * 64),
        ("source", "kind", "agent_claim"),
        ("source", "kind", "local_tool"),
        ("source", "run_id", "old-run"),
        ("source", "job_id", "old-job"),
        ("source", "attempt", 2),
        ("source", "attempt", True),
        ("source", "observation_sha256", "1" * 64),
    ],
)
def test_identity_scope_code_environment_and_old_run_are_rejected(
    pair: Any, group: str, field: str, replacement: Any
) -> None:
    expected, receipt = pair
    receipt[group][field] = replacement
    with pytest.raises(subject.ReceiptError):
        subject.validate_receipt(expected, receipt)


@pytest.mark.parametrize("result", ["failed", "cancelled", "incomplete", "PASS", "unknown"])
def test_incomplete_or_failed_execution_cannot_be_promoted(pair: Any, result: str) -> None:
    pair[1]["result"] = result
    with pytest.raises(subject.ReceiptError):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize(
    ("status", "exit_code"),
    [
        ("skipped", 0),
        ("unknown", None),
        ("failed", 0),
        ("cancelled", 0),
        ("passed", 7),
        ("passed", None),
        ("passed", False),
    ],
)
def test_failed_native_check_remains_failed_after_later_success(
    pair: Any, status: str, exit_code: Any
) -> None:
    pair[1]["checks"][0].update(status=status, exit_code=exit_code)
    assert pair[1]["checks"][1]["status"] == "passed"
    with pytest.raises(subject.ReceiptError):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize("change", ["missing", "duplicate", "unknown", "wrong-command"])
def test_frozen_check_set_cannot_be_replaced(pair: Any, change: str) -> None:
    checks = pair[1]["checks"]
    if change == "missing":
        checks.pop()
    elif change == "duplicate":
        checks.append(deepcopy(checks[0]))
    elif change == "unknown":
        checks[0]["id"] = "not-required"
    else:
        checks[0]["command_ref"] = "disabled-tests"
    with pytest.raises(subject.ReceiptError):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "/root/log",
        "C:/temp/log",
        "logs/../../log",
        "a\\log",
        "file://log",
        "logs/%2e%2e",
        "logs/CON",
        "logs/com1.txt",
        "logs/a.",
        "logs//x",
        "logs/*",
    ],
)
def test_artifact_escape_and_nonportable_paths_reject_even_matching_baseline(
    pair: Any, path: str
) -> None:
    pair[0]["required_artifacts"][0]["path"] = path
    pair[1]["artifacts"][0]["path"] = path
    with pytest.raises(subject.ReceiptError, match="UNSAFE_REFERENCE"):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize("change", ["hash", "missing", "duplicate", "extra"])
def test_artifact_manifest_requires_exact_independent_observation(pair: Any, change: str) -> None:
    artifacts = pair[1]["artifacts"]
    if change == "hash":
        artifacts[0]["sha256"] = "0" * 64
    elif change == "missing":
        artifacts.clear()
    elif change == "duplicate":
        artifacts.append(deepcopy(artifacts[0]))
    else:
        artifacts.append({"path": "unrequested.json", "sha256": "0" * 64})
    with pytest.raises(subject.ReceiptError):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize(
    "field", ["gate_pass", "approval", "merge_authorized", "token", "logs", "command"]
)
def test_extra_control_secret_and_log_content_fields_rejected(pair: Any, field: str) -> None:
    pair[1][field] = "untrusted"
    with pytest.raises(subject.ReceiptError, match="SCHEMA_MISMATCH"):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize(
    "secret", ["ghp_SyntheticOnly123", "github_pat_SyntheticOnly123", "sk-SyntheticOnly123"]
)
def test_secret_shaped_reference_is_rejected_without_echoing_value(pair: Any, secret: str) -> None:
    pair[0]["credential_mechanism_ref"] = secret
    with pytest.raises(subject.ReceiptError, match="SECRET_VALUE_REJECTED") as caught:
        subject.validate_receipt(*pair)
    assert secret not in str(caught.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("started_at", "2026-08-01T00:00:00Z"),
        ("finished_at", "2026-09-13T00:11:00Z"),
        ("finished_at", "2026-09-13T00:00:01Z"),
        ("started_at", "2026-09-13T00:00:01"),
        ("started_at", "yesterday"),
    ],
)
def test_stale_reversed_or_unobserved_time_window_rejected(
    pair: Any, field: str, value: str
) -> None:
    pair[1][field] = value
    with pytest.raises(subject.ReceiptError):
        subject.validate_receipt(*pair)


def test_pr_merge_checkout_is_recorded_separately_and_must_match(pair: Any) -> None:
    for item in pair:
        item["code"]["checkout_commit"] = "3" * 40
    assert subject.validate_receipt(*pair)["contract_matched"]
    pair[1]["code"]["checkout_commit"] = pair[1]["code"]["subject_commit"]
    with pytest.raises(subject.ReceiptError, match="BOUND_FACT_MISMATCH"):
        subject.validate_receipt(*pair)


def test_baseline_itself_cannot_contain_duplicate_checks_or_dirty_snapshot(pair: Any) -> None:
    pair[0]["required_checks"].append(deepcopy(pair[0]["required_checks"][0]))
    with pytest.raises(subject.ReceiptError, match="DUPLICATE_ENTRY"):
        subject.validate_receipt(*pair)
    pair[0]["required_checks"].pop()
    for item in pair:
        item["code"]["dirty"] = True
    with pytest.raises(subject.ReceiptError, match="SCHEMA_MISMATCH"):
        subject.validate_receipt(*pair)


def associated(pair: Any) -> dict[str, Any]:
    evidence = subject.load_json(ROOT / "tests/fixtures/contracts/valid/evidence.json")
    evidence["generated_at"] = pair[1]["finished_at"]
    pair[0]["run"]["source_kind"] = pair[1]["source"]["kind"] = "local_tool"
    pair[0]["required_checks"] = [{"id": "pytest", "command_ref": "locked-pytest"}]
    pair[1]["checks"] = [
        {"id": "pytest", "command_ref": "locked-pytest", "status": "passed", "exit_code": 0}
    ]
    association = {
        "repository_uuid": evidence["repository_id"],
        "task_id": evidence["task_id"],
        "evidence_canonical_sha256": subject.canonical_sha256(evidence),
        "spec_sha256": evidence["spec_sha256"],
        "policy_sha256": evidence["policy_sha256"],
        "classification_input_sha256": evidence["classification_input_sha256"],
    }
    for item in pair:
        item["association"] = deepcopy(association)
    return evidence


def rebind_digest(pair: Any, evidence: Any) -> None:
    for item in pair:
        item["association"]["evidence_canonical_sha256"] = subject.canonical_sha256(evidence)


def test_existing_evidence_is_associated_without_mutation_or_gate_promotion(pair: Any) -> None:
    evidence = associated(pair)
    before = deepcopy(evidence)
    result = subject.validate_receipt(*pair, evidence=evidence)
    assert result["association_checked"]
    assert result["governance_effect"] == "none"
    assert evidence == before
    assert pair[0]["repository"]["github_id"] != pair[0]["association"]["repository_uuid"]


def test_local_evidence_cannot_attest_a_different_actual_checkout(pair: Any) -> None:
    # I3-F2: a correct subject and evidence digest do not cover another checked-out commit.
    evidence = associated(pair)
    for document in pair:
        document["code"]["checkout_commit"] = "3" * 40
    with pytest.raises(subject.ReceiptError, match="ASSOCIATED_CHECKOUT_MISMATCH"):
        subject.validate_receipt(*pair, evidence=evidence)


def test_newline_suffixed_task_identity_cannot_match_legacy_evidence(pair: Any) -> None:
    evidence = associated(pair)
    evidence["task_id"] += "\n"
    for document in pair:
        document["association"]["task_id"] = evidence["task_id"]
    rebind_digest(pair, evidence)
    with pytest.raises(subject.ReceiptError, match="SCHEMA_MISMATCH"):
        subject.validate_receipt(*pair, evidence=evidence)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("repository_id", "223e4567-e89b-42d3-a456-426614174000"),
        ("subject_commit", "9" * 40),
        ("base_commit", "9" * 40),
        ("task_id", "TASK-0002"),
        ("policy_sha256", "9" * 64),
        ("spec_sha256", "9" * 64),
        ("classification_input_sha256", "9" * 64),
        ("generated_at", "2026-08-20T05:00:00Z"),
        ("conclusion", "provisional"),
        ("unverified_scenarios", ["not-run"]),
    ],
)
def test_legacy_association_rechecks_identity_and_freshness_after_digest_match(
    pair: Any, field: str, replacement: Any
) -> None:
    evidence = associated(pair)
    evidence[field] = replacement
    rebind_digest(pair, evidence)
    with pytest.raises(subject.ReceiptError):
        subject.validate_receipt(*pair, evidence=evidence)


def test_legacy_evidence_digest_tampering_missing_and_wrong_check_set_fail(pair: Any) -> None:
    evidence = associated(pair)
    with pytest.raises(subject.ReceiptError, match="ASSOCIATED_EVIDENCE_MISSING"):
        subject.validate_receipt(*pair)
    evidence["reproduce_command"].append("changed")
    with pytest.raises(subject.ReceiptError, match="DIGEST_MISMATCH"):
        subject.validate_receipt(*pair, evidence=evidence)
    rebind_digest(pair, evidence)
    evidence["checks"][0]["check_id"] = "unrelated"
    rebind_digest(pair, evidence)
    with pytest.raises(subject.ReceiptError, match="ASSOCIATED_CHECK_SET_MISMATCH"):
        subject.validate_receipt(*pair, evidence=evidence)


def test_existing_schema_remains_strict_and_rejects_forged_pass(pair: Any) -> None:
    evidence = associated(pair)
    evidence["checks"][0]["exit_code"] = 9
    rebind_digest(pair, evidence)
    with pytest.raises(subject.ReceiptError):
        subject.validate_receipt(*pair, evidence=evidence)
    evidence["checks"][0]["exit_code"] = 0
    evidence["runner_profile"] = "cannot-add-to-old-schema"
    rebind_digest(pair, evidence)
    with pytest.raises(subject.ReceiptError, match="LEGACY_EVIDENCE_INVALID"):
        subject.validate_receipt(*pair, evidence=evidence)


def test_external_v2_pre_review_evidence_keeps_original_semantics(pair: Any) -> None:
    from aiflow.evidence import verification_snapshot_sha256

    associated(pair)
    evidence = subject.load_json(ROOT / "tests/fixtures/contracts/valid/evidence-v2.json")
    evidence.update(
        mode="ci",
        phase="pre_implementation_review",
        attestation_head="2" * 40,
        attestation_governance_only=True,
        generated_at=pair[1]["finished_at"],
    )
    evidence["review_refs"].pop("implementation")
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    pair[0]["run"]["source_kind"] = pair[1]["source"]["kind"] = "github_api"
    pair[0]["required_checks"] = [
        {"id": check["check_id"], "command_ref": check["check_id"]} for check in evidence["checks"]
    ]
    pair[1]["checks"] = [
        {
            "id": check["check_id"],
            "command_ref": check["check_id"],
            "status": "passed",
            "exit_code": 0,
        }
        for check in evidence["checks"]
    ]
    rebind_digest(pair, evidence)
    before = deepcopy(evidence)
    result = subject.validate_receipt(*pair, evidence=evidence)
    assert result["association_checked"] is True
    assert result["governance_effect"] == "none"
    assert evidence == before
    evidence["attestation_head"] = "3" * 40
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    rebind_digest(pair, evidence)
    with pytest.raises(subject.ReceiptError, match="ASSOCIATED_CHECKOUT_MISMATCH"):
        subject.validate_receipt(*pair, evidence=evidence)
    evidence["verification_snapshot_sha256"] = "0" * 64
    rebind_digest(pair, evidence)
    with pytest.raises(subject.ReceiptError, match="ASSOCIATED_SNAPSHOT_MISMATCH"):
        subject.validate_receipt(*pair, evidence=evidence)


def test_profile_source_and_legacy_evidence_mode_cannot_conflict(pair: Any) -> None:
    evidence = associated(pair)
    pair[0]["run"]["source_kind"] = pair[1]["source"]["kind"] = "github_api"
    with pytest.raises(subject.ReceiptError, match="ASSOCIATED_SOURCE_MODE_MISMATCH"):
        subject.validate_receipt(*pair, evidence=evidence)


def test_lightweight_receipt_cannot_smuggle_unrequested_evidence(pair: Any) -> None:
    with pytest.raises(subject.ReceiptError, match="UNEXPECTED_EVIDENCE"):
        subject.validate_receipt(*pair, evidence={"conclusion": "passed"})


def test_cached_receipt_identifier_is_rejected(pair: Any) -> None:
    pair[1]["receipt_id"] = "previous-receipt"
    with pytest.raises(subject.ReceiptError, match="RECEIPT_IDENTITY_MISMATCH"):
        subject.validate_receipt(*pair)


@pytest.mark.parametrize(
    "data",
    [
        b'{"id":1,"id":2}',
        b'{"number":NaN}',
        b'{"number":Infinity}',
        b'{"number":-Infinity}',
        b"\xff",
        b"[] trailing",
    ],
)
def test_ambiguous_nonfinite_or_malformed_json_is_rejected(tmp_path: Path, data: bytes) -> None:
    path = tmp_path / "input.json"
    path.write_bytes(data)
    with pytest.raises(subject.ReceiptError):
        subject.load_json(path)


def test_bounded_files_and_nonregular_inputs_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "large.json"
    path.write_bytes(b" " * (subject.MAX_JSON_BYTES + 1))
    with pytest.raises(subject.ReceiptError, match="JSON_SIZE_LIMIT"):
        subject.load_json(path)
    with pytest.raises(subject.ReceiptError, match="INPUT_NOT_REGULAR"):
        subject.load_json(tmp_path)
    path.write_text("[" * 30 + "0" + "]" * 30, encoding="utf-8")
    with pytest.raises(subject.ReceiptError, match="JSON_DEPTH_LIMIT"):
        subject.load_json(path)


def test_cli_examples_and_disabled_adapter_do_not_write_inputs_or_execute_commands(
    tmp_path: Path,
) -> None:
    expected = EXAMPLES / "runner-profile.example.json"
    receipt = EXAMPLES / "execution-receipt.example.json"
    originals = expected.read_bytes(), receipt.read_bytes()
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "validate",
            "--expected",
            str(expected),
            "--receipt",
            str(receipt),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "CONTRACT_MATCH"
    disabled = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "validate",
            "--disabled",
            "--expected",
            str(tmp_path / "absent.json"),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert disabled.returncode == 0
    assert json.loads(disabled.stdout)["contract_matched"] is False
    assert json.loads(disabled.stdout)["status"] == "ADAPTER_DISABLED"
    assert originals == (expected.read_bytes(), receipt.read_bytes())


def test_cli_rejection_is_nonzero_and_does_not_echo_secrets(tmp_path: Path, pair: Any) -> None:
    path = tmp_path / "secret.json"
    pair[1]["token"] = "ghp_SyntheticSecretShouldNeverEcho"
    path.write_text(json.dumps(pair[1]), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "validate",
            "--expected",
            str(EXAMPLES / "runner-profile.example.json"),
            "--receipt",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "REJECTED"
    assert "ghp_" not in completed.stdout + completed.stderr


def test_missing_cli_arguments_are_nonzero_and_disabled_is_explicit(capsys: Any) -> None:
    assert subject.main(["validate"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "REJECTED"
    result = subject.validate_receipt(None, None, evidence=object(), disabled=True)
    assert result["status"] == "ADAPTER_DISABLED"
    assert result["contract_matched"] is False
