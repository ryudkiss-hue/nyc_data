#Requires -Version 5.1
<#
.SYNOPSIS
  Launch Streamlit Mission Control or legacy Dash; open Getting Started if unavailable.
#>
param(
    [string] $AppDir = $PSScriptRoot
)

$ErrorActionPreference = "Continue"
$AppDir = (Resolve-Path $AppDir).Path
$Exe = Join-Path $AppDir "nyc-dot-toolkit.exe"
$GettingStarted = Join-Path $AppDir "docs\GETTING_STARTED.md"

$StreamlitApp = Join-Path $AppDir "app\app.py"
$DashLegacy = Join-Path $AppDir "legacy_archive\dash_app\app.py"

if (Test-Path -LiteralPath $StreamlitApp) {
    $py = (Get-Command python -ErrorAction SilentlyContinue)?.Source
    if ($py) {
        & $py -m streamlit run $StreamlitApp
        if ($LASTEXITCODE -eq 0) { exit 0 }
    }
}

if (Test-Path -LiteralPath $Exe) {
    & $Exe dash
    if ($LASTEXITCODE -eq 0) { exit 0 }
}

if (Test-Path -LiteralPath $DashLegacy) {
    $py = (Get-Command python -ErrorAction SilentlyContinue)?.Source
    if ($py) {
        & $py $DashLegacy
        if ($LASTEXITCODE -eq 0) { exit 0 }
    }
}

if (Test-Path -LiteralPath $GettingStarted) {
    Start-Process $GettingStarted
    exit 0
}

Write-Host "Dashboard requires Python (dash/plotly) or Docker. See docs\GETTING_STARTED.md."
exit 1
