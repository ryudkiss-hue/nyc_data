# Consolidated PowerShell script for Manhattan Mission Control repository cleanup

$root = Get-Location
$archive = Join-Path $root "legacy_archive"
if (!(Test-Path $archive)) { New-Item -ItemType Directory -Path $archive }

$appDir = Join-Path $root "app"
if (!(Test-Path $appDir)) { New-Item -ItemType Directory -Path $appDir }

Write-Host "Starting repository consolidation..." -ForegroundColor Cyan

# 1. Move Streamlit files to app/
$streamlitFiles = @("app.py", "analytics.py", "data_loader.py", "__init__.py")
foreach ($file in $streamlitFiles) {
    $src = Join-Path $root $file
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $appDir -Force
        Write-Host "Moved: $file -> app/"
    }
}

# 2. Archive legacy and unused folders
$foldersToArchive = @("dash_app", "frontend", "legacy", "outputs", "quality_catalog", "quality_reports", "schema_registry", "scratch")
foreach ($folder in $foldersToArchive) {
    $src = Join-Path $root $folder
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $archive -Force
        Write-Host "Archived: $folder/"
    }
}

# 3. Archive loose root clutter (non-essential scripts)
$clutter = @("run_nightly_sync.bat", "socrata_toolkit.config.json", "test_integration.py", "_tree_dupes_scan.py", "MissionControl.spec", "nyc_data.code-workspace")
foreach ($file in $clutter) {
    $src = Join-Path $root $file
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $archive -Force
        Write-Host "Archived clutter: $file"
    }
}

Write-Host "`nConsolidation complete. Repository is now in production-ready state." -ForegroundColor Green