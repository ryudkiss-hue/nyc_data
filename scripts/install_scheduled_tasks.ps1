# NYC DOT SIM — register user-level Windows scheduled tasks (solo workstation)
# Creates two tasks (no admin needed; run once, rerun-safe):
#   NYC-DOT-Nightly-Refresh   daily 02:00  — pipeline refresh + DuckDB backup
#   NYC-DOT-Weekly-Drift-Audit Mondays 08:00 — live registry drift/scope audit
# Remove with:  schtasks /Delete /TN "<name>" /F
$root = Split-Path -Parent $PSScriptRoot
$ps = "powershell.exe"

$nightly = "-NoProfile -ExecutionPolicy Bypass -File `"$root\scripts\nightly_refresh.ps1`""
schtasks /Create /F /TN "NYC-DOT-Nightly-Refresh" /SC DAILY /ST 02:00 /TR "$ps $nightly"

$audit = "-NoProfile -ExecutionPolicy Bypass -File `"$root\scripts\weekly_drift_audit.ps1`""
schtasks /Create /F /TN "NYC-DOT-Weekly-Drift-Audit" /SC WEEKLY /D MON /ST 08:00 /TR "$ps $audit"

Write-Host "`nInstalled tasks:"
schtasks /Query /TN "NYC-DOT-Nightly-Refresh" /FO LIST | Select-String "TaskName|Next Run"
schtasks /Query /TN "NYC-DOT-Weekly-Drift-Audit" /FO LIST | Select-String "TaskName|Next Run"
