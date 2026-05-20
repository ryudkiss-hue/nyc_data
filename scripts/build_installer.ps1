#Requires -Version 5.1
<#
.SYNOPSIS
  Build dist\nyc-dot-toolkit.exe and compile the Windows Setup installer with Inno Setup.

.OUTPUTS
  installer\output\NYC-DOT-Sidewalk-Toolkit-Setup.exe

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
#>
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Find-InnoCompiler {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    return $null
}

Write-Host "=== NYC DOT Sidewalk Toolkit — installer build ===" -ForegroundColor Cyan

Write-Host "`n[1/3] Ensuring Python package (postgres, xlsx) …"
python -m pip install -e ".[postgres,xlsx,exe]" --quiet
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed"
}

$ExePath = Join-Path $RepoRoot "dist\nyc-dot-toolkit.exe"
if (-not (Test-Path -LiteralPath $ExePath)) {
    Write-Host "`n[2/3] Building standalone executable (PyInstaller) …"
    python (Join-Path $RepoRoot "scripts\build_exe.py")
    if ($LASTEXITCODE -ne 0) {
        throw "build_exe.py failed"
    }
} else {
    Write-Host "`n[2/3] Using existing $ExePath"
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Missing build output: $ExePath — run: python scripts\build_exe.py"
}

$Iscc = Find-InnoCompiler
if (-not $Iscc) {
    Write-Host ""
    Write-Host "ERROR: Inno Setup 6 compiler (ISCC.exe) was not found." -ForegroundColor Red
    Write-Host "Install Inno Setup 6 from: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host "Then add ISCC to PATH or use the default install location under Program Files (x86)."
    exit 1
}

$IssFile = Join-Path $RepoRoot "installer\nyc_dot_toolkit.iss"
$OutDir = Join-Path $RepoRoot "installer\output"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "`n[3/3] Compiling installer with: $Iscc"
& $Iscc $IssFile
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed (exit $LASTEXITCODE)"
}

$SetupExe = Join-Path $OutDir "NYC-DOT-Sidewalk-Toolkit-Setup.exe"
if (-not (Test-Path -LiteralPath $SetupExe)) {
    throw "Expected output not found: $SetupExe"
}

$sizeMb = [math]::Round((Get-Item $SetupExe).Length / 1MB, 1)
Write-Host ""
Write-Host "SUCCESS: $SetupExe ($sizeMb MB)" -ForegroundColor Green
