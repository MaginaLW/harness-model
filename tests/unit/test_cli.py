"""Regression tests for the root aiflow command."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from importlib.metadata import metadata, version
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

import aiflow
from aiflow import cli, initialization, verification_service
from aiflow.errors import ContractError


def test_module_help_succeeds(
    run_aiflow: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    result = run_aiflow("--help")

    assert result.returncode == 0
    assert "Auditable AI code collaboration CLI" in result.stdout
    assert result.stderr == ""


def test_module_version_is_stable(
    run_aiflow: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    result = run_aiflow("--version")

    assert result.returncode == 0
    assert result.stdout == "aiflow 0.2.0\n"
    assert result.stderr == ""


def test_package_metadata_matches_runtime_version() -> None:
    assert version("aiflow") == aiflow.__version__ == "0.2.0"
    package_metadata = metadata("aiflow")
    assert package_metadata["License-Expression"] == "MIT"
    assert package_metadata.get_all("License-File") == ["LICENSE"]


def test_unknown_argument_uses_argparse_error_contract(
    run_aiflow: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    result = run_aiflow("--definitely-unknown")

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert "error:" in result.stderr
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [("external-review",), ("verify", "TASK-0001", "--pytest-temp-root", "unused")],
)
def test_retired_interfaces_use_argparse_rejection(
    run_aiflow: Callable[..., subprocess.CompletedProcess[str]], arguments: tuple[str, ...]
) -> None:
    result = run_aiflow(*arguments)

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert "error:" in result.stderr
    assert "Traceback" not in result.stdout + result.stderr


def test_help_exposes_only_supported_interfaces(
    run_aiflow: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    root = run_aiflow("--help")
    verify = run_aiflow("verify", "--help")

    assert root.returncode == verify.returncode == 0
    assert "external-review" not in root.stdout
    assert "--pytest-temp-root" not in verify.stdout
    assert "observe" in root.stdout
    assert "--finalize" in verify.stdout
    assert "--node-ci" in verify.stdout
    assert "--node-ci-payload" in verify.stdout
    assert "node-ci" in root.stdout


@pytest.fixture
def node_ci_interface(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Isolate routing from producer kernels; these stubs are not integration proof."""
    module = ModuleType("aiflow.node_ci")
    monkeypatch.setitem(sys.modules, "aiflow.node_ci", module)
    return module


@pytest.fixture
def cli_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cli, "resolve_repository_root", lambda _cwd: tmp_path)
    monkeypatch.setattr(initialization, "require_initialization_ready", lambda _root: None)
    return tmp_path


@pytest.mark.parametrize(
    "invalid",
    [
        {"node_ci": False},
        {"ci": False},
        {"node_ci_payload": None},
        {"ci_run_dir": None},
        {"output": None},
        {"actor": "verifier"},
        {"actor": ""},
        {"check_ids": ("contract",)},
        {"provisional": True},
        {"run_id": "run"},
        {"run_id": ""},
        {"finalize": True},
        {"abandon": True},
        {"reason": "reason"},
        {"reason": ""},
        {"node_materials_sha256": "a" * 64},
        {"node_installed_mutation_run": "IMUT-" + "a" * 16},
    ],
)
def test_node_ci_invalid_modes_reject_before_policy_recovery_or_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: dict[str, object]
) -> None:
    forbidden = Mock(side_effect=AssertionError("rejection entered local work"))
    for name in (
        "_verification_policy",
        "load_task_record",
        "read_task_record_strict",
        "transition_task_record",
        "_finalize_v2_task",
        "_abandon_interrupted_verification",
        "_execute_plan",
        "save_evidence",
    ):
        monkeypatch.setattr(verification_service, name, forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    arguments = {
        "node_ci": True,
        "ci": True,
        "node_ci_payload": tmp_path / "payload",
        "ci_run_dir": tmp_path / "attempt",
        "output": tmp_path / "evidence.json",
        **invalid,
    }
    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(tmp_path, "TASK-0001", **arguments)
    assert caught.value.code == "NODE_CI_MODE_INVALID"
    forbidden.assert_not_called()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("node_policy,policy_version", [(False, "3.2.0"), (True, "3.1.0")])
def test_node_ci_rejects_unsupported_profile_before_local_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    node_policy: bool,
    policy_version: str,
) -> None:
    monkeypatch.setattr(
        verification_service,
        "_verification_policy",
        lambda _root: SimpleNamespace(policy_version=policy_version),
    )
    monkeypatch.setattr(verification_service, "is_node_policy", lambda _bundle: node_policy)
    forbidden = Mock(side_effect=AssertionError("unsupported profile entered local work"))
    for name in ("load_task_record", "read_task_record_strict", "_execute_plan", "save_evidence"):
        monkeypatch.setattr(verification_service, name, forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    with pytest.raises(ContractError) as caught:
        verification_service.verify_task(
            tmp_path,
            "TASK-0001",
            node_ci=True,
            ci=True,
            node_ci_payload=tmp_path / "payload",
            ci_run_dir=tmp_path / "attempt",
            output=tmp_path / "evidence.json",
        )
    assert caught.value.code == "NODE_CI_PROFILE_INVALID"
    forbidden.assert_not_called()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("conclusion", ["passed", "failed", "provisional", None])
def test_node_ci_service_routes_only_to_explicit_producer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    node_ci_interface: ModuleType,
    conclusion: str | None,
) -> None:
    monkeypatch.setattr(
        verification_service,
        "_verification_policy",
        lambda _root: SimpleNamespace(policy_version="3.2.0"),
    )
    monkeypatch.setattr(verification_service, "is_node_policy", lambda _bundle: True)
    producer = Mock(return_value={"conclusion": conclusion})
    monkeypatch.setattr(node_ci_interface, "verify_node_ci", producer, raising=False)
    forbidden = Mock(side_effect=AssertionError("producer entered local lifecycle"))
    for name in ("load_task_record", "read_task_record_strict", "_execute_plan", "save_evidence"):
        monkeypatch.setattr(verification_service, name, forbidden)
    arguments = {
        "node_ci": True,
        "ci": True,
        "node_ci_payload": tmp_path / "payload",
        "ci_run_dir": tmp_path / "attempt",
        "output": tmp_path / "evidence.json",
    }
    if conclusion in {"passed", "failed"}:
        result = verification_service.verify_task(tmp_path, "TASK-0001", **arguments)
        assert result.conclusion == conclusion
        assert result.state is None
        assert result.evidence_path == tmp_path / "evidence.json"
        assert result.reason_codes == (
            () if conclusion == "passed" else ("NODE_CI_VERIFICATION_FAILED",)
        )
    else:
        with pytest.raises(ContractError) as caught:
            verification_service.verify_task(tmp_path, "TASK-0001", **arguments)
        assert caught.value.code == "NODE_CI_EVIDENCE_INVALID"
    producer.assert_called_once_with(
        tmp_path,
        "TASK-0001",
        run_dir=tmp_path / "attempt",
        output=tmp_path / "evidence.json",
        payload_root=tmp_path / "payload",
    )
    forbidden.assert_not_called()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("conclusion,exit_code", [("passed", 0), ("failed", 2)])
def test_node_ci_producer_cli_arguments_and_exit(
    cli_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    conclusion: str,
    exit_code: int,
) -> None:
    producer = Mock(
        return_value=verification_service.VerifyResult(
            "TASK-0001", conclusion, None, cli_repository / "evidence.json", ()
        )
    )
    monkeypatch.setattr(cli, "verify_task", producer)
    assert (
        cli.main(
            [
                "verify",
                "TASK-0001",
                "--node-ci",
                "--ci",
                "--node-ci-payload",
                "payload",
                "--ci-run-dir",
                "attempt",
                "--output",
                "evidence.json",
            ]
        )
        == exit_code
    )
    producer.assert_called_once_with(
        cli_repository,
        "TASK-0001",
        actor=None,
        check_ids=[],
        ci=True,
        ci_run_dir=Path("attempt"),
        output=Path("evidence.json"),
        finalize=False,
        abandon=False,
        reason=None,
        node_materials_sha256=None,
        node_ci=True,
        node_ci_payload=Path("payload"),
    )
    assert capsys.readouterr().out == f"TASK-0001 CI {conclusion}\n"


@pytest.mark.parametrize("passed,exit_code", [(True, 0), (False, 2), (1, 2), (None, 2)])
def test_node_ci_consumer_cli_routes_typed_selectors_and_emits_json(
    cli_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    node_ci_interface: ModuleType,
    capsys: pytest.CaptureFixture[str],
    passed: object,
    exit_code: int,
) -> None:
    decision = {"passed": passed, "local_current": False, "reason_codes": ["synthetic"]}
    consumer = Mock(return_value=decision)
    monkeypatch.setattr(node_ci_interface, "evaluate_node_ci_gate", consumer, raising=False)
    assert (
        cli.main(
            [
                "node-ci",
                "gate",
                "TASK-0001",
                "--run",
                "42",
                "--attempt",
                "2",
                "--download-dir",
                "download",
            ]
        )
        == exit_code
    )
    consumer.assert_called_once_with(
        cli_repository, "TASK-0001", run_id=42, attempt=2, download_dir=Path("download")
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out) == decision
    assert captured.err == ""


@pytest.mark.parametrize(
    "arguments",
    [
        ["node-ci"],
        ["node-ci", "gate", "TASK-0001"],
        ["node-ci", "gate", "TASK-0001", "--run", "x", "--attempt", "1", "--download-dir", "d"],
        ["node-ci", "gate", "TASK-0001", "--run", "1", "--attempt", "x", "--download-dir", "d"],
    ],
)
def test_node_ci_consumer_parser_rejects_missing_or_untyped_selectors(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    repository = Mock(side_effect=AssertionError("invalid CLI reached repository"))
    monkeypatch.setattr(cli, "resolve_repository_root", repository)
    with pytest.raises(SystemExit) as caught:
        cli.main(arguments)
    assert caught.value.code == 2
    repository.assert_not_called()


def test_ordinary_verify_keeps_existing_service_arguments_and_exit(
    cli_repository: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    local = Mock(
        return_value=verification_service.VerifyResult(
            "TASK-0001", "failed", "FAILED", cli_repository / "evidence.json", ()
        )
    )
    monkeypatch.setattr(cli, "verify_task", local)
    assert cli.main(["verify", "TASK-0001", "--actor", "implementer"]) == 0
    local.assert_called_once_with(
        cli_repository,
        "TASK-0001",
        actor="implementer",
        check_ids=[],
        ci=False,
        ci_run_dir=None,
        output=None,
        finalize=False,
        abandon=False,
        reason=None,
        node_materials_sha256=None,
    )
    assert capsys.readouterr().out == "TASK-0001 FAILED failed\n"
