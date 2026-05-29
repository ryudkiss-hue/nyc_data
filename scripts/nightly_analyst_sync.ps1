#Requires -Version 5.1
<#
.SYNOPSIS
  Nightly analyst pack + optional DuckDB sync (Task Scheduler friendly).
.EXAMPLE
  powershell -File scripts\nightly_analyst_sync.ps1
#>
param(
    [string] $RepoRoot = (Split-Path $PSScriptRoot -Parent),
    [string] $Profile = "config\analyst_profile.yaml"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

if (-not (Test-Path $Profile)) {
    Copy-Item "config\analyst_profile.example.yaml" $Profile -ErrorAction SilentlyContinue
}

$py = (Get-Command python -ErrorAction SilentlyContinue)?.Source
if (-not $py) { throw "Python not found on PATH." }

& $py -m socrata_toolkit.core.cli analyst run --profile $Profile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Nightly analyst pack complete. Review in Mission Control: python main.py"
exit 0
