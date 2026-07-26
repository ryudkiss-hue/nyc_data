# NYC DOT SIM — weekly live registry drift/scope audit (scheduled task target)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$log = Join-Path $root "pipeline\logs\drift_audit.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
"=== drift audit $(Get-Date -Format o) ===" | Add-Content $log
& "$root\.venv\Scripts\python.exe" "$root\scripts\audit_registry_drift.py" *>> $log
exit $LASTEXITCODE
