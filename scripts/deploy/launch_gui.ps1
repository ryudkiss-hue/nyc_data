#Requires -Version 5.1
<#
.SYNOPSIS
  Launch Dash Mission Control (PRIMARY) with fallback to Streamlit (SECONDARY).

.DESCRIPTION
  Attempts launch in priority order:
  1. python main.py                    (launcher shim — picks Dash)
  2. python app/dash_app.py            (Dash Mission Control — PRIMARY)
  3. streamlit run app/app.py          (Streamlit alternative — SECONDARY)
  4. nyc-dot-toolkit.exe dash          (packaged installer executable)
  5. GETTING_STARTED.md                (Opens setup guide if all else fails)
#>
param(
    [string] $AppDir = $PSScriptRoot
)

$ErrorActionPreference = "Continue"
$AppDir = (Resolve-Path $AppDir).Path
$Exe = Join-Path $AppDir "nyc-dot-toolkit.exe"
$GettingStarted = Join-Path $AppDir "docs\GETTING_STARTED.md"

$DashApp = Join-Path $AppDir "app\dash_app.py"
$StreamlitApp = Join-Path $AppDir "app\app.py"

# Try launcher shim first (picks Dash primary automatically)
$MainPy = Join-Path $AppDir "main.py"
if (Test-Path -LiteralPath $MainPy) {
    $py = (Get-Command python -ErrorAction SilentlyContinue)?.Source
    if ($py) {
        $env:PYTHONPATH = "$(Join-Path $AppDir 'src');$AppDir"
        & $py $MainPy
        if ($LASTEXITCODE -eq 0) { exit 0 }
    }
}

# Try Dash Mission Control directly (PRIMARY)
if (Test-Path -LiteralPath $DashApp) {
    $py = (Get-Command python -ErrorAction SilentlyContinue)?.Source
    if ($py) {
        $env:PYTHONPATH = "$(Join-Path $AppDir 'src');$AppDir"
        & $py $DashApp
        if ($LASTEXITCODE -eq 0) { exit 0 }
    }
}

# Try Streamlit as fallback (SECONDARY)
if (Test-Path -LiteralPath $StreamlitApp) {
    $py = (Get-Command python -ErrorAction SilentlyContinue)?.Source
    if ($py) {
        $env:PYTHONPATH = "$(Join-Path $AppDir 'src');$AppDir"
        & $py -m streamlit run $StreamlitApp
        if ($LASTEXITCODE -eq 0) { exit 0 }
    }
}

# Try packaged executable
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
