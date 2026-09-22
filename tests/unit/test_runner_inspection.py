"""Exercise the real PowerShell entry points with explicitly synthetic observations."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "runner"
PRIVATE = "private_fixture_value_do_not_emit"
SID = "S-1-5-21-1000-2000-3000-4000"
SERVICE = f"actions.runner.{PRIVATE}"


@pytest.fixture(scope="module")
def pwsh() -> str:
    executable = os.environ.get("RUNNER_INSPECTION_PWSH") or shutil.which("pwsh")
    assert executable, "PowerShell 7 is required; set RUNNER_INSPECTION_PWSH to its executable"
    return executable


def inputs(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = {
        "schemaVersion": "1.0",
        "profileId": "synthetic-profile",
        "repository": "synthetic-owner/synthetic-repository",
        "repositoryId": 123456,
        "runnerId": 42,
        "serviceName": SERVICE,
        "expectedServiceSid": SID,
        "runnerRoot": str(tmp_path / PRIVATE),
        "minimumFreeBytes": 1024,
        "requiredTools": [
            {"name": "git", "path": str(tmp_path / "git.exe"), "expectedVersion": "2.55.0"}
        ],
    }
    facts = {
        "platform": "Windows",
        "architecture": "X64",
        "currentIdentity": {
            "tokenKnown": True,
            "identitySid": SID,
            "tokenGroupSids": ["S-1-1-0", "S-1-5-32-545"],
            "roleAdministrator": False,
            "localMembershipKnown": True,
            "administratorMemberSids": ["S-1-5-21-500"],
        },
        "serviceQuery": {
            "status": "observed",
            "services": [
                {
                    "name": SERVICE,
                    "state": "Running",
                    "startMode": "Auto",
                    "processId": 100,
                    "accountSid": SID,
                    "executablePath": str(tmp_path / PRIVATE / "bin" / "RunnerService.exe"),
                }
            ],
        },
        "processQuery": {
            "status": "observed",
            "processes": [
                {
                    "name": "RunnerService.exe",
                    "processId": 100,
                    "parentProcessId": 1,
                    "ownerSid": SID,
                    "executablePath": str(tmp_path / PRIVATE / "bin" / "RunnerService.exe"),
                },
                {
                    "name": "Runner.Listener.exe",
                    "processId": 101,
                    "parentProcessId": 100,
                    "ownerSid": SID,
                    "executablePath": str(tmp_path / PRIVATE / "bin" / "Runner.Listener.exe"),
                },
            ],
        },
        "runnerRoot": {"status": "present"},
        "registration": {
            "status": "observed",
            "runnerId": 42,
            "repository": "synthetic-owner/synthetic-repository",
            "scope": "repository",
        },
        "disk": {"status": "observed", "freeBytes": 10240},
        "tools": [{"name": "git", "status": "observed", "version": "2.55.0"}],
        "remote": {
            "status": "observed",
            "registered": True,
            "private": True,
            "runnerId": 42,
            "repositoryId": 123456,
            "repository": "synthetic-owner/synthetic-repository",
            "online": True,
            "busy": False,
            "os": "Windows",
        },
    }
    return profile, facts


def invoke(
    pwsh: str,
    tmp_path: Path,
    profile: dict[str, Any] | None,
    facts: dict[str, Any],
    *,
    script: str = "inventory.ps1",
    extra: tuple[str, ...] = (),
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    fixture_path = tmp_path / "observations.json"
    fixture_path.write_text(json.dumps({"schemaVersion": "1.0", "observations": facts}))
    argv = [pwsh, "-NoProfile", "-File", str(TOOLS / script), "-Format", "Json"]
    if profile is not None:
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(json.dumps(profile))
        argv += ["-ProfilePath", str(profile_path)]
    argv += ["-FixturePath", str(fixture_path), *extra]
    result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert not result.stderr, result.stderr
    return result, json.loads(result.stdout)


@pytest.mark.parametrize("script", ["inventory.ps1", "health-check.ps1"])
def test_synthetic_success_never_claims_runtime_or_acceptance(
    pwsh: str, tmp_path: Path, script: str
) -> None:
    profile, facts = inputs(tmp_path)
    result, report = invoke(pwsh, tmp_path, profile, facts, script=script)
    assert result.returncode == 0
    assert report["status"] == "SYNTHETIC_HEALTHY"
    assert report["source"] == "synthetic_fixture"
    assert report["ready"] is False
    assert report["runtimeVerified"] is False
    assert report["credentialIsolationVerified"] is False
    assert report["postRestartWorkloadVerified"] is False
    assert report["gatePass"] is False
    assert PRIVATE not in result.stdout
    assert SID not in result.stdout
    assert str(tmp_path) not in result.stdout
    assert report["declared"]["profileConfigured"] is True
    assert report["observed"]["currentIdentityClass"] == "non_administrator"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("platform", "unsupported", "PLATFORM_UNSUPPORTED"),
        ("architecture", "Arm64", "ARCHITECTURE_UNSUPPORTED"),
        ("currentIdentity.tokenKnown", False, "SERVICE_NON_ADMINISTRATOR_NOT_VERIFIED"),
        ("currentIdentity.localMembershipKnown", False, "SERVICE_NON_ADMINISTRATOR_NOT_VERIFIED"),
        ("currentIdentity.roleAdministrator", True, "SERVICE_NON_ADMINISTRATOR_NOT_VERIFIED"),
        ("currentIdentity.identitySid", "S-1-5-21-999", "SERVICE_NON_ADMINISTRATOR_NOT_VERIFIED"),
        ("serviceQuery.status", "access_denied", "SERVICE_OBSERVATION_UNKNOWN"),
        ("processQuery.status", "unavailable", "PROCESS_OBSERVATION_UNKNOWN"),
        ("runnerRoot.status", "access_denied", "RUNNER_ROOT_NOT_CONFIRMED"),
        ("runnerRoot.status", "reparse", "RUNNER_ROOT_NOT_CONFIRMED"),
        ("disk.status", "unknown", "DISK_BUDGET_NOT_CONFIRMED"),
        ("disk.freeBytes", 1023, "DISK_BUDGET_NOT_CONFIRMED"),
        ("remote.status", "unknown", "REMOTE_STATE_UNKNOWN"),
        ("remote.registered", False, "REMOTE_PROFILE_MISMATCH"),
        ("remote.runnerId", 43, "REMOTE_PROFILE_MISMATCH"),
        ("remote.repositoryId", 98765, "REMOTE_PROFILE_MISMATCH"),
        ("remote.repository", "other/repository", "REMOTE_PROFILE_MISMATCH"),
        ("registration.status", "not_found", "LOCAL_REGISTRATION_AND_PATHS_NOT_BOUND"),
        ("registration.status", "access_denied", "LOCAL_REGISTRATION_AND_PATHS_NOT_BOUND"),
        ("registration.status", "reparse", "LOCAL_REGISTRATION_AND_PATHS_NOT_BOUND"),
        ("registration.status", "invalid_output", "LOCAL_REGISTRATION_AND_PATHS_NOT_BOUND"),
        ("registration.runnerId", 999, "LOCAL_REGISTRATION_AND_PATHS_NOT_BOUND"),
        ("registration.repository", "other/repository", "LOCAL_REGISTRATION_AND_PATHS_NOT_BOUND"),
        ("registration.scope", "unknown", "LOCAL_REGISTRATION_AND_PATHS_NOT_BOUND"),
        ("remote.private", False, "REMOTE_PROFILE_MISMATCH"),
        ("remote.os", "Linux", "REMOTE_PROFILE_MISMATCH"),
        ("remote.online", False, "REMOTE_OFFLINE"),
        ("remote.busy", True, "RUNNER_BUSY"),
    ],
)
def test_missing_or_conflicting_observations_fail_closed(
    pwsh: str, tmp_path: Path, field: str, value: object, reason: str
) -> None:
    profile, facts = inputs(tmp_path)
    target = facts
    parts = field.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    result, report = invoke(pwsh, tmp_path, profile, facts)
    assert result.returncode == 1
    assert report["ready"] is False
    assert reason in report["missingOrUnhealthy"]


@pytest.mark.parametrize("mode", ["deny_only", "direct_member", "nested_member", "empty_groups"])
def test_administrator_group_evidence_cannot_be_hidden_by_filtered_token(
    pwsh: str, tmp_path: Path, mode: str
) -> None:
    profile, facts = inputs(tmp_path)
    identity = facts["currentIdentity"]
    if mode == "deny_only":
        identity["tokenGroupSids"].append("S-1-5-32-544")
    elif mode == "direct_member":
        identity["administratorMemberSids"].append(SID)
    elif mode == "nested_member":
        identity["tokenGroupSids"].append("S-1-5-21-999")
        identity["administratorMemberSids"].append("S-1-5-21-999")
    else:
        identity["tokenGroupSids"] = []
    result, report = invoke(pwsh, tmp_path, profile, facts)
    assert result.returncode == 1
    assert "SERVICE_NON_ADMINISTRATOR_NOT_VERIFIED" in report["missingOrUnhealthy"]


@pytest.mark.parametrize(
    "mode",
    [
        "other_service",
        "pending_service",
        "duplicate_service",
        "second_listener",
        "worker",
        "wrong_owner",
        "wrong_parent",
        "wrong_service_path",
        "wrong_process_path",
        "wrong_listener_path",
    ],
)
def test_instance_and_process_binding_rejects_concurrency_and_identity_conflicts(
    pwsh: str, tmp_path: Path, mode: str
) -> None:
    profile, facts = inputs(tmp_path)
    services = facts["serviceQuery"]["services"]
    processes = facts["processQuery"]["processes"]
    if mode in {"other_service", "pending_service", "duplicate_service"}:
        duplicate = copy.deepcopy(services[0])
        if mode != "duplicate_service":
            duplicate["name"] += "-other"
        if mode == "pending_service":
            duplicate["state"] = "Start Pending"
        duplicate["processId"] += 10
        services.append(duplicate)
    elif mode == "second_listener":
        duplicate = copy.deepcopy(processes[1])
        duplicate["processId"] += 10
        processes.append(duplicate)
    elif mode == "worker":
        processes.append(
            {
                "name": "Runner.Worker.exe",
                "processId": 102,
                "parentProcessId": 101,
                "ownerSid": SID,
                "executablePath": str(tmp_path / PRIVATE / "bin" / "Runner.Worker.exe"),
            }
        )
    elif mode == "wrong_owner":
        processes[1]["ownerSid"] = "S-1-5-21-999"
    elif mode == "wrong_service_path":
        services[0]["executablePath"] = str(tmp_path / "other" / "RunnerService.exe")
    elif mode == "wrong_process_path":
        processes[0]["executablePath"] = str(tmp_path / "other" / "RunnerService.exe")
    elif mode == "wrong_listener_path":
        processes[1]["executablePath"] = str(tmp_path / "other" / "Runner.Listener.exe")
    else:
        processes[1]["parentProcessId"] = 999
    result, report = invoke(pwsh, tmp_path, profile, facts)
    assert result.returncode == 1
    assert report["ready"] is False


@pytest.mark.parametrize(
    ("root_state", "service_state", "expected"),
    [
        ("not_found", None, "not_installed"),
        ("access_denied", None, "unknown"),
        ("present", None, "configuration_conflict"),
        ("present", "Stopped", "stopped"),
    ],
)
def test_local_installation_classification_keeps_access_denial_unknown(
    pwsh: str, tmp_path: Path, root_state: str, service_state: str | None, expected: str
) -> None:
    profile, facts = inputs(tmp_path)
    facts["runnerRoot"]["status"] = root_state
    if service_state is None:
        facts["serviceQuery"]["services"] = []
    else:
        facts["serviceQuery"]["services"][0]["state"] = service_state
        facts["serviceQuery"]["services"][0]["processId"] = 0
    result, report = invoke(pwsh, tmp_path, profile, facts)
    assert result.returncode == 1
    assert report["observed"]["instanceState"] == expected
    assert report["observed"]["remote"]["registered"] is True


@pytest.mark.parametrize("mode", ["nonzero", "timeout", "version", "duplicate", "missing"])
def test_tool_errors_and_wrong_versions_cannot_be_overridden_by_successful_last_command(
    pwsh: str, tmp_path: Path, mode: str
) -> None:
    profile, facts = inputs(tmp_path)
    if mode in {"nonzero", "timeout"}:
        facts["tools"][0]["status"] = mode
    elif mode == "version":
        facts["tools"][0]["version"] = "9.9.9"
    elif mode == "duplicate":
        facts["tools"].append(copy.deepcopy(facts["tools"][0]))
    else:
        facts["tools"] = []
    result, report = invoke(pwsh, tmp_path, profile, facts)
    assert result.returncode == 1
    assert "REQUIRED_TOOLS_NOT_CONFIRMED" in report["missingOrUnhealthy"]


@pytest.mark.parametrize("mode", ["boolean_string", "extra_secret", "bad_sid", "bad_version"])
def test_invalid_inputs_return_only_redacted_error(pwsh: str, tmp_path: Path, mode: str) -> None:
    profile, facts = inputs(tmp_path)
    if mode == "boolean_string":
        facts["remote"]["busy"] = "false"
    elif mode == "extra_secret":
        profile["token"] = PRIVATE
    elif mode == "bad_sid":
        facts["currentIdentity"]["identitySid"] = PRIVATE
    else:
        facts["tools"][0]["version"] = PRIVATE
    result, report = invoke(pwsh, tmp_path, profile, facts)
    assert result.returncode == 2
    assert report["status"] == "INPUT_OR_PROBE_ERROR"
    assert report["ready"] is False
    assert PRIVATE not in result.stdout


def test_no_profile_is_useful_inventory_but_not_readiness(pwsh: str, tmp_path: Path) -> None:
    _, facts = inputs(tmp_path)
    result, report = invoke(pwsh, tmp_path, None, facts)
    assert result.returncode == 1
    assert report["observed"]["activeServiceCount"] == 1
    assert report["declared"]["profileConfigured"] is False
    assert "PROFILE_REQUIRED" in report["missingOrUnhealthy"]


def test_fixture_cannot_enable_network_or_claim_real_observations(
    pwsh: str, tmp_path: Path
) -> None:
    profile, facts = inputs(tmp_path)
    result, report = invoke(pwsh, tmp_path, profile, facts, extra=("-CheckRemote",))
    assert result.returncode == 2
    assert report["ready"] is False


def test_private_details_require_explicit_switch(pwsh: str, tmp_path: Path) -> None:
    profile, facts = inputs(tmp_path)
    result, report = invoke(pwsh, tmp_path, profile, facts, extra=("-IncludePrivateDetails",))
    assert result.returncode == 0
    assert report["privateDetails"]["profile"]["serviceName"] == SERVICE
    assert report["privateDetails"]["currentIdentitySid"] == SID


def test_second_read_only_invocation_preserves_all_inputs(pwsh: str, tmp_path: Path) -> None:
    profile, facts = inputs(tmp_path)
    first, first_report = invoke(pwsh, tmp_path, profile, facts)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    second, second_report = invoke(pwsh, tmp_path, profile, facts)
    after = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert before == after
    assert first.returncode == second.returncode == 0
    first_report.pop("observedAtUtc")
    second_report.pop("observedAtUtc")
    assert first_report == second_report


def test_text_output_is_redacted_and_preserves_failed_exit(pwsh: str, tmp_path: Path) -> None:
    profile, facts = inputs(tmp_path)
    facts["remote"]["status"] = "unknown"
    invoke(pwsh, tmp_path, profile, facts)
    result = subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-File",
            str(TOOLS / "health-check.ps1"),
            "-ProfilePath",
            str(tmp_path / "profile.json"),
            "-FixturePath",
            str(tmp_path / "observations.json"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 1
    assert not result.stderr
    assert "NOT_READY" in result.stdout
    assert "REMOTE_STATE_UNKNOWN" in result.stdout
    assert PRIVATE not in result.stdout
    assert SID not in result.stdout


@pytest.mark.parametrize("native_exit", [0, 17])
def test_native_probe_checks_actual_process_exit(
    pwsh: str, tmp_path: Path, native_exit: int
) -> None:
    # Directly exercise the private primitive with a controlled child, without any host probe.
    # Command arguments are fixed by entry-point code; this test hook is not an exported interface.
    command = (
        "$m=Import-Module $env:INSPECTION_TEST_MODULE -Force -PassThru; "
        "& $m { Invoke-InspectionNative -Path $env:INSPECTION_TEST_PWSH "
        "-Arguments @('-NoProfile','-Command',$env:INSPECTION_TEST_CHILD) } "
        "| ConvertTo-Json -Compress"
    )
    environment = os.environ.copy()
    environment.update(
        INSPECTION_TEST_MODULE=str(TOOLS / "RunnerInspection.psm1"),
        INSPECTION_TEST_PWSH=pwsh,
        INSPECTION_TEST_CHILD=f"Write-Output 'controlled-output'; exit {native_exit}",
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env=environment,
    )
    assert result.returncode == 0
    assert not result.stderr
    report = json.loads(result.stdout)
    if os.name != "nt":
        assert report["status"] == "unavailable"
        assert report["cleanupConfirmed"] is False
        return
    assert report["status"] == ("observed" if native_exit == 0 else "nonzero")
    assert report["cleanupConfirmed"] is True
    assert report["output"].replace("\r\n", "\n") == (
        "controlled-output\n" if native_exit == 0 else ""
    )


@pytest.mark.parametrize("kind", ["missing", "directory", "file"])
def test_real_path_metadata_distinguishes_missing_from_wrong_type(
    pwsh: str, tmp_path: Path, kind: str
) -> None:
    target = tmp_path / "synthetic-target"
    if kind == "directory":
        target.mkdir()
    elif kind == "file":
        target.write_text("synthetic non-secret data")
    command = (
        "$m=Import-Module $env:INSPECTION_TEST_MODULE -Force -PassThru; "
        "& $m { Get-InspectionPathState -Path $env:INSPECTION_TEST_TARGET }"
    )
    environment = os.environ.copy()
    environment.update(
        INSPECTION_TEST_MODULE=str(TOOLS / "RunnerInspection.psm1"),
        INSPECTION_TEST_TARGET=str(target),
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env=environment,
    )
    assert result.returncode == 0
    assert not result.stderr
    assert (
        result.stdout.strip()
        == {"missing": "not_found", "directory": "wrong_type", "file": "present"}[kind]
    )


def inspect_path_with_metadata_spy(
    pwsh: str,
    tmp_path: Path,
    path: str,
    *,
    operation: str = "state",
    drive_type: int | str = 3,
    blocked_path: str = "",
    failure: str = "",
    windows: bool = True,
    psdrive_root: str | None = None,
) -> dict[str, Any]:
    """Model metadata access without opening any test drive, share or device."""
    json_source = tmp_path / "plain.json"
    json_source.write_text('{"synthetic":true}', encoding="utf-8")
    command = r"""
$m = Import-Module $env:INSPECTION_TEST_MODULE -Force -PassThru
& $m {
    $script:probe = ConvertFrom-Json $env:INSPECTION_TEST_PATH_PROBE -AsHashtable
    $script:IsWindows = $script:probe.windows
    $script:metadataCalls = [Collections.Generic.List[string]]::new()
    $script:driveCalls = [Collections.Generic.List[string]]::new()
    $script:psdriveCalls = [Collections.Generic.List[string]]::new()
    function Get-InspectionDriveType {
        param([string]$Root)
        $script:driveCalls.Add($Root)
        if ($script:probe.driveType -eq 'error') { throw 'synthetic_drive_error' }
        return $script:probe.driveType
    }
    function Get-PSDrive {
        param([string]$Name, [string]$PSProvider, [string]$ErrorAction)
        $script:psdriveCalls.Add("${Name}:$PSProvider")
        if ($script:probe.psdriveRoot -eq '<missing>') { return @() }
        if ($script:probe.psdriveRoot -eq '<error>') {
            throw [System.Management.Automation.ItemNotFoundException]::new('drive missing')
        }
        $root = if ($null -eq $script:probe.psdriveRoot) { "${Name}:\" }
            else { $script:probe.psdriveRoot }
        [pscustomobject]@{ Root = $root }
    }
    function Get-Item {
        param([string]$LiteralPath, [switch]$Force, [string]$ErrorAction)
        $script:metadataCalls.Add($LiteralPath)
        $attributes = [IO.FileAttributes]::Normal
        $container = $LiteralPath -cne $script:probe.path
        if ($LiteralPath -ceq $script:probe.blockedPath) {
            switch ($script:probe.failure) {
                'reparse' { $attributes = [IO.FileAttributes]::ReparsePoint }
                'access_denied' { throw [UnauthorizedAccessException]::new('synthetic') }
                'not_found' {
                    throw [System.Management.Automation.ItemNotFoundException]::new('synthetic')
                }
                'unknown' { throw [IO.IOException]::new('synthetic') }
                'wrong_type' { $container = $false }
            }
        }
        [pscustomobject]@{
            PSIsContainer = $container; Attributes = $attributes; Directory = $null
            Length = 18; FullName = $script:probe.jsonSource
        }
    }
    if ($script:probe.operation -eq 'json') {
        try { $null = Read-InspectionJson $script:probe.path; $state = 'accepted' }
        catch { $state = 'rejected' }
    }
    else { $state = Get-InspectionPathState $script:probe.path }
    [pscustomobject]@{
        state = $state; metadataCalls = @($script:metadataCalls)
        driveCalls = @($script:driveCalls); psdriveCalls = @($script:psdriveCalls)
    } | ConvertTo-Json -Compress
}
"""
    environment = os.environ.copy()
    environment.update(
        INSPECTION_TEST_MODULE=str(TOOLS / "RunnerInspection.psm1"),
        INSPECTION_TEST_PATH_PROBE=json.dumps(
            {
                "path": path,
                "operation": operation,
                "driveType": drive_type,
                "blockedPath": blocked_path,
                "failure": failure,
                "windows": windows,
                "psdriveRoot": psdrive_root,
                "jsonSource": str(json_source),
            }
        ),
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env=environment,
    )
    assert result.returncode == 0
    assert not result.stderr
    report: dict[str, Any] = json.loads(result.stdout)
    return report


@pytest.mark.parametrize("operation", ["state", "json"])
@pytest.mark.parametrize(
    "path",
    [
        r"\\never-contact.invalid\share\probe.json",
        "//never-contact.invalid/share/probe.json",
        r"\\?\C:\safe\probe.json",
        r"\\.\C:\safe\probe.json",
        r"FileSystem::C:\safe\probe.json",
        r"Registry::HKEY_LOCAL_MACHINE\probe",
        "Env:PATH",
        "C:probe.json",
        r"\safe\probe.json",
        r"C:\safe\parent\..\probe.json",
        r"C:\safe\NUL.txt",
        r"C:\safe\CONIN$",
        r"C:\safe\CONOUT$",
        "C:\\safe\\COM\u00b9.txt",
        "C:\\safe\\LPT\u00b2",
        r"C:\safe\probe.json:stream",
        r"C:\safe.\probe.json",
    ],
)
def test_windows_nonlocal_or_ambiguous_paths_never_reach_metadata(
    pwsh: str, tmp_path: Path, path: str, operation: str
) -> None:
    report = inspect_path_with_metadata_spy(pwsh, tmp_path, path, operation=operation)
    assert report["state"] == ("rejected" if operation == "json" else "unknown")
    assert report["metadataCalls"] == []
    assert report["driveCalls"] == []
    assert report["psdriveCalls"] == []


@pytest.mark.parametrize("operation", ["state", "json"])
@pytest.mark.parametrize("drive_type", [0, 1, 4, 99, "error"])
def test_network_or_unconfirmed_drive_never_reaches_metadata(
    pwsh: str, tmp_path: Path, operation: str, drive_type: int | str
) -> None:
    report = inspect_path_with_metadata_spy(
        pwsh, tmp_path, r"Z:\safe\probe.json", operation=operation, drive_type=drive_type
    )
    assert report["state"] == ("rejected" if operation == "json" else "unknown")
    assert report["metadataCalls"] == []
    assert report["driveCalls"] == ["Z:\\"]
    assert report["psdriveCalls"] == []


@pytest.mark.parametrize("operation", ["state", "json"])
@pytest.mark.parametrize(
    "alias", [r"D:\local-alias", r"\\never-contact.invalid\share", "", "<missing>", "<error>"]
)
def test_psdrive_alias_is_rejected_before_any_metadata(
    pwsh: str, tmp_path: Path, operation: str, alias: str
) -> None:
    report = inspect_path_with_metadata_spy(
        pwsh, tmp_path, r"C:\probe.json", operation=operation, psdrive_root=alias
    )
    assert report["state"] == ("rejected" if operation == "json" else "unknown")
    assert report["metadataCalls"] == []
    assert report["driveCalls"] == ["C:\\"]
    assert report["psdriveCalls"] == ["C:FileSystem"]


@pytest.mark.skipif(os.name != "nt", reason="Windows process-local PSDrive binding")
def test_real_process_local_psdrive_alias_cannot_redirect_json_reads(
    pwsh: str, tmp_path: Path
) -> None:
    receipt = tmp_path / "receipt.json"
    receipt.write_text('{"synthetic":"must-not-be-read"}', encoding="utf-8")
    command = r"""
# Preload the cmdlets before replacing a drive in this short-lived process only.
$null = ConvertTo-Json (ConvertFrom-Json '{}')
$null = Get-Command Get-Item, Get-PSDrive, Remove-PSDrive, New-PSDrive
$m = Import-Module $env:INSPECTION_TEST_MODULE -Force -PassThru
$driveName = $env:INSPECTION_TEST_SYSTEM_DRIVE.Substring(0, 1)
Set-Location $env:INSPECTION_TEST_ALIAS_ROOT
Remove-PSDrive -Name $driveName -Force
$null = New-PSDrive -Name $driveName -PSProvider FileSystem -Root $env:INSPECTION_TEST_ALIAS_ROOT
& $m {
    $script:metadataCalls = [Collections.Generic.List[string]]::new()
    function Get-Item {
        param([string]$LiteralPath, [switch]$Force, [string]$ErrorAction)
        $script:metadataCalls.Add($LiteralPath)
        Microsoft.PowerShell.Management\Get-Item -LiteralPath $LiteralPath -Force -ErrorAction Stop
    }
    $path = $env:INSPECTION_TEST_SYSTEM_DRIVE + '\receipt.json'
    $state = Get-InspectionPathState $path
    try { $null = Read-InspectionJson $path; $jsonRead = $true }
    catch { $jsonRead = $false }
    [pscustomobject]@{
        state = $state; jsonRead = $jsonRead; metadataCalls = @($script:metadataCalls)
        nativeDriveType = Get-InspectionDriveType ($env:INSPECTION_TEST_SYSTEM_DRIVE + '\')
    } | ConvertTo-Json -Compress
}
"""
    environment = os.environ.copy()
    environment.update(
        INSPECTION_TEST_MODULE=str(TOOLS / "RunnerInspection.psm1"),
        INSPECTION_TEST_SYSTEM_DRIVE=os.environ.get("SystemDrive", "C:"),
        INSPECTION_TEST_ALIAS_ROOT=str(tmp_path),
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env=environment,
    )
    assert result.returncode == 0
    assert not result.stderr
    report = json.loads(result.stdout)
    assert report["nativeDriveType"] in {2, 3, 5, 6}
    assert report["state"] == "unknown"
    assert report["jsonRead"] is False
    assert report["metadataCalls"] == []
    assert receipt.read_text(encoding="utf-8") == '{"synthetic":"must-not-be-read"}'


@pytest.mark.parametrize("drive_type", [2, 3, 5, 6])
def test_plain_local_drive_is_inspected_from_root_to_leaf(
    pwsh: str, tmp_path: Path, drive_type: int
) -> None:
    report = inspect_path_with_metadata_spy(
        pwsh, tmp_path, r"C:\safe\probe.json", drive_type=drive_type
    )
    assert report["state"] == "present"
    assert report["driveCalls"] == ["C:\\"]
    assert report["psdriveCalls"] == ["C:FileSystem"]
    assert report["metadataCalls"] == ["C:\\", r"C:\safe", r"C:\safe\probe.json"]


@pytest.mark.parametrize("operation", ["state", "json"])
@pytest.mark.parametrize("blocked_index", [0, 1, 2])
def test_reparse_component_stops_before_any_child_or_json_read(
    pwsh: str, tmp_path: Path, operation: str, blocked_index: int
) -> None:
    paths = ["C:\\", r"C:\junction", r"C:\junction\probe.json"]
    report = inspect_path_with_metadata_spy(
        pwsh,
        tmp_path,
        paths[-1],
        operation=operation,
        blocked_path=paths[blocked_index],
        failure="reparse",
    )
    assert report["state"] == ("rejected" if operation == "json" else "reparse")
    assert report["metadataCalls"] == paths[: blocked_index + 1]


@pytest.mark.parametrize("failure", ["access_denied", "not_found", "unknown", "wrong_type"])
def test_parent_failure_keeps_classification_and_never_reads_leaf(
    pwsh: str, tmp_path: Path, failure: str
) -> None:
    report = inspect_path_with_metadata_spy(
        pwsh,
        tmp_path,
        r"C:\parent\probe.json",
        blocked_path=r"C:\parent",
        failure=failure,
    )
    assert report["state"] == failure
    assert report["metadataCalls"] == ["C:\\", r"C:\parent"]


@pytest.mark.parametrize("operation", ["state", "json"])
def test_posix_plain_files_and_reparse_ancestors_keep_fixture_compatibility(
    pwsh: str, tmp_path: Path, operation: str
) -> None:
    path = "/synthetic/probe.json"
    plain = inspect_path_with_metadata_spy(pwsh, tmp_path, path, operation=operation, windows=False)
    assert plain["state"] == ("accepted" if operation == "json" else "present")
    assert plain["metadataCalls"] == ["/", "/synthetic", path]
    assert plain["driveCalls"] == []
    linked = inspect_path_with_metadata_spy(
        pwsh,
        tmp_path,
        path,
        operation=operation,
        blocked_path="/synthetic",
        failure="reparse",
        windows=False,
    )
    assert linked["state"] == ("rejected" if operation == "json" else "reparse")
    assert linked["metadataCalls"] == ["/", "/synthetic"]


@pytest.mark.parametrize(
    ("root_state", "root_path", "drive_root"),
    [
        ("present", r"C:\synthetic", "C:\\"),
        ("present", "C:/synthetic", "C:\\"),
        ("present", r"C:\synthetic", "Z:\\"),
        ("not_found", r"C:\synthetic", "C:\\"),
        ("access_denied", r"C:\synthetic", "C:\\"),
        ("reparse", r"C:\synthetic", "C:\\"),
        ("wrong_type", r"C:\synthetic", "C:\\"),
        ("unknown", r"\\never-contact.invalid\share\root", "Z:\\"),
        ("unknown", r"Z:\mapped-root", "Z:\\"),
    ],
)
def test_disk_probe_only_reads_the_confirmed_local_root(
    pwsh: str, root_state: str, root_path: str, drive_root: str
) -> None:
    command = r"""
$m = Import-Module $env:INSPECTION_TEST_MODULE -Force -PassThru
function global:Join-Path { throw 'Synthetic Windows fixture must not resolve a host drive' }
& $m {
    $script:IsWindows = $true
    $script:driveCalls = [Collections.Generic.List[string]]::new()
    $script:freeReads = 0
    function Join-Path {
        param([string]$Path, [string]$ChildPath)
        # The fixture uses Windows syntax even when PowerShell runs on Linux.
        return $Path.Replace('/', '\').TrimEnd('\') + '\' + $ChildPath
    }
    function Get-CimInstance { @() }
    function Get-InspectionIdentity { @{} }
    function Get-InspectionPathState {
        param([string]$Path, [bool]$RequireDirectory)
        if ($RequireDirectory) { return $env:INSPECTION_TEST_ROOT_STATE }
        return 'not_found'
    }
    function Get-PSDrive {
        param([string]$Name, [string]$PSProvider, [string]$ErrorAction)
        $script:driveCalls.Add("${Name}:$PSProvider")
        $drive = [pscustomobject]@{ Root = $env:INSPECTION_TEST_DRIVE_ROOT }
        $drive | Add-Member -MemberType ScriptProperty -Name Free -Value {
            $script:freeReads++; return 4096
        }
        return $drive
    }
    $facts = Get-InspectionObservations @{
        runnerRoot = $env:INSPECTION_TEST_ROOT_PATH; requiredTools = @()
    } $false
    [pscustomobject]@{
        disk = $facts.disk; driveCalls = @($script:driveCalls); freeReads = $script:freeReads
    } | ConvertTo-Json -Compress
}
"""
    environment = os.environ.copy()
    environment.update(
        INSPECTION_TEST_MODULE=str(TOOLS / "RunnerInspection.psm1"),
        INSPECTION_TEST_ROOT_STATE=root_state,
        INSPECTION_TEST_ROOT_PATH=root_path,
        INSPECTION_TEST_DRIVE_ROOT=drive_root,
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env=environment,
    )
    assert result.returncode == 0
    assert not result.stderr
    report = json.loads(result.stdout)
    if root_state == "present":
        assert report["driveCalls"] == ["C:FileSystem"]
        if drive_root == "C:\\":
            assert report["disk"] == {"status": "observed", "freeBytes": 4096}
            assert report["freeReads"] > 0
        else:
            assert report["disk"] == {"status": "unknown", "freeBytes": 0}
            assert report["freeReads"] == 0
    else:
        assert report["driveCalls"] == []
        assert report["freeReads"] == 0
        assert report["disk"] == {"status": "unknown", "freeBytes": 0}


def native_probe_child(pwsh: str, code: str) -> subprocess.Popen[str]:
    command = (
        "$m=Import-Module $env:INSPECTION_TEST_MODULE -Force -PassThru; "
        "& $m { Invoke-InspectionNative -Path $env:INSPECTION_TEST_PYTHON "
        "-Arguments @('-c',$env:INSPECTION_TEST_CHILD) } | ConvertTo-Json -Compress"
    )
    environment = os.environ.copy()
    environment.update(
        INSPECTION_TEST_MODULE=str(TOOLS / "RunnerInspection.psm1"),
        INSPECTION_TEST_PYTHON=sys.executable,
        INSPECTION_TEST_CHILD=code,
    )
    return subprocess.Popen(
        [pwsh, "-NoProfile", "-Command", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def windows_process_alive(pid: int) -> bool:
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, pid)
    if not handle:
        return False
    try:
        return bool(kernel.WaitForSingleObject(handle, 0) == 258)
    finally:
        kernel.CloseHandle(handle)


@pytest.mark.parametrize("mode", ["stdout_descendant", "stderr_descendant", "parent_timeout"])
def test_native_job_deadline_stops_exact_descendants_and_preserves_unrelated_process(
    pwsh: str, tmp_path: Path, mode: str
) -> None:
    pid_file = tmp_path / "owned-pid.txt"
    save_pid = (
        f"import os,pathlib,time; pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); "
    )
    if mode == "parent_timeout":
        code = save_pid + "time.sleep(22)"
    else:
        child_code = save_pid + "time.sleep(22)"
        pipe_setting = (
            "stderr=subprocess.DEVNULL"
            if mode == "stdout_descendant"
            else "stdout=subprocess.DEVNULL"
        )
        code = (
            "import subprocess,sys; "
            + f"subprocess.Popen([sys.executable,'-c',{child_code!r}],{pipe_setting})"
        )
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    started = time.monotonic()
    probe = native_probe_child(pwsh, code)
    try:
        stdout, stderr = probe.communicate(timeout=17)
        elapsed = time.monotonic() - started
        assert probe.returncode == 0
        assert not stderr
        report = json.loads(stdout)
        if os.name != "nt":
            assert report["status"] == "unavailable"
            assert not pid_file.exists()
            return
        assert report["status"] == "timeout"
        assert report["cleanupConfirmed"] is True
        # Includes PowerShell startup/type compilation around the 10 s native deadline.
        assert elapsed < 16
        assert not windows_process_alive(int(pid_file.read_text()))
        assert unrelated.poll() is None
    finally:
        if probe.poll() is None:
            probe.kill()
            probe.communicate(timeout=5)
        unrelated.terminate()
        unrelated.wait(timeout=5)


@pytest.mark.parametrize("mode", ["normal_descendant", "oversize", "invalid_utf8"])
def test_native_job_normal_completion_and_output_errors_are_terminal(
    pwsh: str, tmp_path: Path, mode: str
) -> None:
    code = {
        "normal_descendant": (
            "import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
            "'import time; time.sleep(0.2)']); print('complete')"
        ),
        "oversize": "import os,time; os.write(1,b'x'*70000); time.sleep(22)",
        "invalid_utf8": "import os; os.write(1,b'\\xff')",
    }[mode]
    started = time.monotonic()
    probe = native_probe_child(pwsh, code)
    try:
        stdout, stderr = probe.communicate(timeout=8)
        assert probe.returncode == 0
        assert not stderr
        report = json.loads(stdout)
        if os.name != "nt":
            assert report["status"] == "unavailable"
            return
        assert time.monotonic() - started < 7
        assert report["cleanupConfirmed"] is True
        assert (
            report["status"]
            == {
                "normal_descendant": "observed",
                "oversize": "oversize",
                "invalid_utf8": "unavailable",
            }[mode]
        )
        assert report["output"].strip() == ("complete" if mode == "normal_descendant" else "")
    finally:
        if probe.poll() is None:
            probe.kill()
            probe.communicate(timeout=5)


def test_probe_owner_termination_closes_job_and_terminates_payload(
    pwsh: str, tmp_path: Path
) -> None:
    pid_file = tmp_path / "cancelled-pid.txt"
    code = (
        f"import pathlib,os,time; pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); "
        "time.sleep(22)"
    )
    probe = native_probe_child(pwsh, code)
    try:
        if os.name != "nt":
            stdout, _ = probe.communicate(timeout=8)
            assert json.loads(stdout)["status"] == "unavailable"
            return
        deadline = time.monotonic() + 8
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pid_file.exists()
        payload_pid = int(pid_file.read_text())
        assert windows_process_alive(payload_pid)
        probe.terminate()
        probe.communicate(timeout=5)
        deadline = time.monotonic() + 3
        while windows_process_alive(payload_pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not windows_process_alive(payload_pid)
    finally:
        if probe.poll() is None:
            probe.kill()
            probe.communicate(timeout=5)


@pytest.mark.parametrize(
    "registration", [None, {"agentId": 999, "gitHubUrl": "https://github.com/other/project"}]
)
def test_live_collector_reads_fixed_nonsecret_registration_file(
    pwsh: str, tmp_path: Path, registration: dict[str, Any] | None
) -> None:
    profile, _ = inputs(tmp_path)
    selected_root = Path(profile["runnerRoot"])
    selected_root.mkdir()
    if registration is not None:
        (selected_root / ".runner").write_text(json.dumps(registration))
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(json.dumps(profile))
    command = (
        "$m=Import-Module $env:INSPECTION_TEST_MODULE -Force -PassThru; "
        "& $m { function Get-CimInstance { @() }; "
        "function Get-InspectionIdentity { @{} }; "
        "$p=Read-InspectionProfile $env:INSPECTION_TEST_PROFILE; "
        "(Get-InspectionObservations $p $false).registration } | ConvertTo-Json -Compress"
    )
    environment = os.environ.copy()
    environment.update(
        INSPECTION_TEST_MODULE=str(TOOLS / "RunnerInspection.psm1"),
        INSPECTION_TEST_PROFILE=str(profile_file),
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        timeout=15,
    )
    assert result.returncode == 0
    assert not result.stderr
    observed = json.loads(result.stdout)
    if os.name != "nt":
        assert observed["status"] == "unknown"
    elif registration is None:
        assert observed["status"] == "not_found"
    else:
        assert observed["status"] == "observed"
        assert observed["runnerId"] == 999
        assert observed["repository"] == "other/project"
        assert observed["scope"] == "repository"
