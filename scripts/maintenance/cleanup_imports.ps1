# Install autoflake if not present
if (-not (python -m autoflake --version 2>$null)) {
    Write-Host "Installing autoflake..." -ForegroundColor Cyan
    python -m pip install autoflake
}

Write-Host "🧹 Scrubbing unused imports and variables across the project..." -ForegroundColor Yellow
$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path
# --in-place modifies files directly, --recursive searches directories
python -m autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive "$projectRoot\socrata_toolkit" "$projectRoot\tests"

Write-Host "✅ Cleanup complete! All unused imports have been removed." -ForegroundColor Green