# Fixed bridge to the existing observer; stdin contains operator-selected paths.
#Requires -Version 7.0
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
    if (-not $IsWindows) { throw 'unsupported_platform' }
    $inputText = [Console]::In.ReadToEnd()
    if ($inputText.Length -gt 32768) { throw 'invalid_input' }
    $paths = ConvertFrom-Json -InputObject $inputText -AsHashtable
    if ($paths -isnot [System.Collections.IDictionary] -or -not $paths.Contains('pwsh')) {
        throw 'invalid_input'
    }
    foreach ($name in $paths.Keys) {
        if ($name -cnotin @('python', 'git', 'pwsh') -or $paths[$name] -isnot [string] -or
            -not [IO.Path]::IsPathFullyQualified($paths[$name]) -or
            [IO.Path]::GetFileName($paths[$name]) -cne ($name + '.exe')) { throw 'invalid_input' }
    }
    $modulePath = Join-Path $PSScriptRoot '../runner/RunnerInspection.psm1'
    $module = Import-Module $modulePath -PassThru -Force
    $result = & $module {
        param($SelectedPaths)
        $observations = @{}
        foreach ($name in @('python', 'git', 'pwsh')) {
            if (-not $SelectedPaths.Contains($name)) { continue }
            $probe = Invoke-InspectionNative $SelectedPaths[$name] @('--version')
            $version = ''
            $status = 'unavailable'
            if ($probe.status -ceq 'observed' -and $probe.cleanupConfirmed) {
                $prefix = @{ python = 'Python '; git = 'git version '; pwsh = 'PowerShell ' }[$name]
                if ($probe.output -cmatch ('\A' + [regex]::Escape($prefix) +
                    '(?<version>\d+\.\d+\.\d+(?:\.windows\.\d+)?)\r?\n?\z')) {
                    $version = $Matches.version
                    $status = 'observed'
                } else { $status = 'invalid_output' }
            }
            $observations[$name] = @{
                status = $status; version = $version; cleanup_confirmed = [bool]$probe.cleanupConfirmed
            }
        }
        return $observations
    } $paths
    $result | ConvertTo-Json -Depth 4 -Compress
    exit 0
} catch {
    [Console]::Error.WriteLine('version_probe_unavailable')
    exit 1
}
