#Requires -Version 5.1
<#
.SYNOPSIS
  Launch the analyst Dash GUI or open Getting Started if Dash is unavailable.
#>
param(
    [string] $AppDir = $PSScriptRoot
)

$ErrorActionPreference = "Continue"
$AppDir = (Resolve-Path $AppDir).Path
$Exe = Join-Path $AppDir "nyc-dot-toolkit.exe"
$GettingStarted = Join-Path $AppDir "docs\GETTING_STARTED.md"

if (Test-Path -LiteralPath $Exe) {
    & $Exe dash
    if ($LASTEXITCODE -eq 0) { exit 0 }
}

if (Test-Path -LiteralPath $GettingStarted) {
    Start-Process $GettingStarted
    exit 0
}

Write-Host "Dashboard requires Python (dash/plotly) or Docker. See docs\GETTING_STARTED.md."
exit 1
