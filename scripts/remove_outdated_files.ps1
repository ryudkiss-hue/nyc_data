# remove_outdated_files.ps1
# Cleans up old, deprecated test files and modules that no longer fit the current architecture.

$outdatedPatterns = @(
    # Deprecated Integrations
    "test_airflow_*.py",
    "test_m365_*.py",
    "test_bi_integration.py",
    "test_excel_integration.py",
    "test_microsoft_graph.py",
    "test_sql_integration.py",
    "test_dbeaver_profiles.py",
    "test_integration_quick_start.py",
    
    # Deprecated Ops & Advanced Modules
    "test_nlp_*.py",
    "test_quantum_*.py",
    "test_ops.py",
    "test_workflow_engine.py",
    "test_work_management.py",
    "test_task_board.py",
    "test_alert_delivery.py",
    "test_observability.py"
)

$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path
Write-Host "🧹 Sweeping for outdated files in $projectRoot..." -ForegroundColor Yellow

$deletedCount = 0

foreach ($pattern in $outdatedPatterns) {
    $files = Get-ChildItem -Path $projectRoot -Filter $pattern -Recurse -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        Remove-Item -Path $file.FullName -Force
        Write-Host "🗑️ Deleted: $($file.Name)" -ForegroundColor DarkGray
        $deletedCount++
    }
}

Write-Host "`n✅ Cleanup complete! Removed $deletedCount outdated files." -ForegroundColor Green