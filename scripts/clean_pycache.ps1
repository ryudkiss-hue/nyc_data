# clean_pycache.ps1
# Cleans up all Python cache files and directories across the project.

$projectRoot = Resolve-Path "$PSScriptRoot\.."
Write-Host "🧹 Sweeping for Python cache files in $projectRoot..." -ForegroundColor Yellow

$deletedDirs = 0
$deletedFiles = 0

# Remove __pycache__ and .pytest_cache directories
$cacheDirs = Get-ChildItem -Path $projectRoot -Include "__pycache__", ".pytest_cache" -Recurse -Directory -ErrorAction SilentlyContinue
foreach ($dir in $cacheDirs) {
    Remove-Item -Path $dir.FullName -Recurse -Force
    Write-Host "🗑️ Deleted Dir: $($dir.FullName)" -ForegroundColor DarkGray
    $deletedDirs++
}

# Remove loose .pyc and .pyo files
$cacheFiles = Get-ChildItem -Path $projectRoot -Include "*.pyc", "*.pyo" -Recurse -File -ErrorAction SilentlyContinue
foreach ($file in $cacheFiles) {
    Remove-Item -Path $file.FullName -Force
    Write-Host "🗑️ Deleted File: $($file.FullName)" -ForegroundColor DarkGray
    $deletedFiles++
}

Write-Host "`n✅ Cleanup complete! Removed $deletedDirs cache directories and $deletedFiles loose cache files." -ForegroundColor Green
