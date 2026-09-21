[CmdletBinding()]
param(
    [string]$ProfilePath,
    [string]$FixturePath,
    [ValidateSet('Json', 'Text')][string]$Format = 'Text',
    [switch]$CheckRemote,
    [switch]$IncludePrivateDetails
)

# Same observations and decision as inventory; neither entry point mutates a host.
& (Join-Path $PSScriptRoot 'inventory.ps1') @PSBoundParameters
exit $LASTEXITCODE
