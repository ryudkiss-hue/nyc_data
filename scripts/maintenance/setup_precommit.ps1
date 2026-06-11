#Requires -Version 5.1
<#
.SYNOPSIS
  Install pre-commit hooks for ruff (matches CI).
#>
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m pip install -U pre-commit ruff
pre-commit install
Write-Host "Pre-commit installed. Hooks run on git commit."
pre-commit run --all-files
