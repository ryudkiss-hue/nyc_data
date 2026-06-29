<#
.SYNOPSIS
  Register (or update) the NYC DOT nightly pipeline as a Windows Scheduled Task
  that wakes the machine to run pipeline\run_local.py.

.DESCRIPTION
  Creates a per-user task "NYC_DOT_Nightly_Pipeline" that runs scripts\run_nightly.cmd
  daily at the given time. WakeToRun is enabled so a sleeping machine wakes for the
  run; StartWhenAvailable catches up if the machine was off at the scheduled time.

  Idempotent: re-running updates the existing task in place.

.PARAMETER Time
  Daily start time, HH:mm (24h). Default 02:00 (matches the historical run window).

.PARAMETER Unregister
  Remove the task instead of creating it.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\register_nightly_task.ps1
  powershell -ExecutionPolicy Bypass -File scripts\register_nightly_task.ps1 -Time 03:30
  powershell -ExecutionPolicy Bypass -File scripts\register_nightly_task.ps1 -Unregister
#>
param(
  [string]$Time = "02:00",
  [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$TaskName = "NYC_DOT_Nightly_Pipeline"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Runner   = Join-Path $PSScriptRoot "run_nightly.cmd"

if ($Unregister) {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task '$TaskName'."
  } else {
    Write-Host "No scheduled task '$TaskName' to remove."
  }
  return
}

if (-not (Test-Path $Runner)) { throw "Runner not found: $Runner" }

$action   = New-ScheduledTaskAction -Execute $Runner -WorkingDirectory $RepoRoot
$trigger  = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet `
  -WakeToRun `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Hours 6) `
  -MultipleInstances IgnoreNew

# Run under the current user, only when logged on (no stored password needed).
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal `
  -Description "NYC DOT local-first pipeline: nightly ingest/staging/analytics/metrics/geo + publish serving layer to MotherDuck." `
  -Force | Out-Null

Write-Host "Registered scheduled task '$TaskName' (daily at $Time, wake-to-run)."
Write-Host "Runner: $Runner"
Write-Host "Inspect:   Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo"
Write-Host "Run now:   Start-ScheduledTask -TaskName $TaskName"
Write-Host "Remove:    powershell -ExecutionPolicy Bypass -File scripts\register_nightly_task.ps1 -Unregister"
