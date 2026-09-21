[CmdletBinding()]
param(
    [string]$ProfilePath,
    [string]$FixturePath,
    [ValidateSet('Json', 'Text')][string]$Format = 'Text',
    [switch]$CheckRemote,
    [switch]$IncludePrivateDetails
)

$ErrorActionPreference = 'Stop'
try {
    Import-Module (Join-Path $PSScriptRoot 'RunnerInspection.psm1') -Force
    $result = Invoke-RunnerInspection -ProfilePath $ProfilePath -FixturePath $FixturePath `
        -CheckRemote:$CheckRemote -IncludePrivateDetails:$IncludePrivateDetails
    Write-RunnerInspection -Report $result -Format $Format
    exit $result.exitCode
}
catch {
    # Input paths, account names and arbitrary native errors are never echoed.
    '{"schemaVersion":"1.0","status":"INPUT_OR_PROBE_ERROR","ready":false,"exitCode":2}'
    exit 2
}
