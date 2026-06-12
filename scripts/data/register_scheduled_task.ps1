#Requires -Version 5.1
<#
.SYNOPSIS
  Register Windows Task Scheduler job for weekly Analyst Pack.

.PARAMETER AppDir
  Install directory containing nyc-dot-toolkit.exe and config\analyst_profile.yaml

.PARAMETER ProfilePath
  Analyst profile YAML path (default: config\analyst_profile.yaml). Use this for multi-profile installs
  (e.g. config\profiles\team_a\analyst_profile.yaml).

.PARAMETER TaskName
  Task Scheduler name (default: NYC DOT Analyst Pack)

.PARAMETER DayOfWeek
  Day name for weekly trigger (default: Sunday)

.PARAMETER Time
  Local time HH:mm (default: 23:00 = 11 PM)

.PARAMETER Schedule
  Trigger cadence: Weekly or Daily (default: Weekly)

.PARAMETER Preview
  Print the resolved command and exit without changes.

.PARAMETER Remove
  Unregister the task instead of creating it.
#>
param(
    [Parameter(Mandatory = $true)]
    [string] $AppDir,

    [string] $TaskName = "NYC DOT Analyst Pack",

    [string] $ProfilePath = "",

    [ValidateSet("Weekly","Daily")]
    [string] $Schedule = "Weekly",

    [ValidateSet(
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
    )]
    [string] $DayOfWeek = "Sunday",

    [string] $Time = "23:00",

    [switch] $Preview,

    [switch] $Remove
)

$ErrorActionPreference = "Stop"
$AppDir = (Resolve-Path $AppDir).Path
$Exe = Join-Path $AppDir "nyc-dot-toolkit.exe"
$Profile = if ($ProfilePath -and $ProfilePath.Trim().Length -gt 0) {
    if ([System.IO.Path]::IsPathRooted($ProfilePath)) { $ProfilePath } else { Join-Path $AppDir $ProfilePath }
} else {
    Join-Path $AppDir "config\analyst_profile.yaml"
}
$Resolved = Resolve-Path -LiteralPath $Profile -ErrorAction SilentlyContinue
if ($Resolved) { $Profile = $Resolved.Path }

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Executable not found: $Exe"
}
if (-not (Test-Path -LiteralPath $Profile)) {
    Write-Warning "Profile missing: $Profile — run Setup Wizard or copy analyst_profile.example.yaml"
}

$Arguments = "analyst run --profile `"$Profile`""

Write-Host "Resolved command:"
Write-Host "  Program: $Exe"
Write-Host "  Args:    $Arguments"
Write-Host "  StartIn: $AppDir"

if ($Preview) {
    Write-Host "Preview mode: no changes applied."
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$Action = New-ScheduledTaskAction -Execute $Exe -Argument $Arguments -WorkingDirectory $AppDir
if ($Schedule -eq "Daily") {
    $Trigger = New-ScheduledTaskTrigger -Daily -At $Time
} else {
    $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $Time
}
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "NYC DOT Sidewalk Toolkit — weekly Analyst Pack autopilot" `
    | Out-Null

if ($Schedule -eq "Daily") {
    Write-Host "Registered task '$TaskName' — Daily at $Time"
} else {
    Write-Host "Registered task '$TaskName' — $DayOfWeek at $Time"
}
