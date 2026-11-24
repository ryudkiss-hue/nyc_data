# NYC DOT SIM — nightly data refresh + DuckDB backup (solo workstation)
# Runs the checkpointed local pipeline, then rotates a backup of the analytics DB.
# Logs to pipeline/logs/nightly_refresh.log (gitignored directory).
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$log = Join-Path $root "pipeline\logs\nightly_refresh.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
"=== nightly refresh started $(Get-Date -Format o) ===" | Add-Content $log

& "$root\.venv\Scripts\python.exe" "$root\pipeline\run_local.py" *>> $log
$exit = $LASTEXITCODE
"pipeline exit code: $exit" | Add-Content $log

# Backup rotation (keep 3) — only after a successful run so backups are consistent
if ($exit -eq 0) {
    $db = Join-Path $root "nyc_dot_analytics.duckdb"
    if (Test-Path $db) {
        $bdir = Join-Path $root "backups"
        New-Item -ItemType Directory -Force $bdir | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd"
        Copy-Item $db (Join-Path $bdir "nyc_dot_analytics.$stamp.duckdb") -Force
        Get-ChildItem $bdir -Filter "nyc_dot_analytics.*.duckdb" |
            Sort-Object Name -Descending | Select-Object -Skip 3 |
            Remove-Item -Force -Confirm:$false
        "backup rotated: nyc_dot_analytics.$stamp.duckdb" | Add-Content $log
    }
}
"=== nightly refresh finished $(Get-Date -Format o) (exit $exit) ===" | Add-Content $log
exit $exit
