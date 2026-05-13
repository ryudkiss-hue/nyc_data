# =========================================================
# NYC DATA TOOLKIT - FULL ENVIRONMENT BOOTSTRAP
# Windows PowerShell Setup Script
# =========================================================

Write-Host ""
Write-Host "==============================================="
Write-Host " NYC DATA TOOLKIT ENVIRONMENT SETUP"
Write-Host "==============================================="
Write-Host ""

# ---------------------------------------------------------
# VERIFY PROJECT ROOT
# ---------------------------------------------------------
$projectRoot = Get-Location
Write-Host "Project Root:" $projectRoot
Write-Host ""

# ---------------------------------------------------------
# CREATE VIRTUAL ENVIRONMENT
# ---------------------------------------------------------
if (!(Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}
else {
    Write-Host "Virtual environment already exists."
}
Write-Host ""

# ---------------------------------------------------------
# ACTIVATE VENV & UPGRADE PIP
# ---------------------------------------------------------
Write-Host "Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"
Write-Host "Upgrading pip..."
python -m pip install --upgrade pip
Write-Host ""

# ---------------------------------------------------------
# INSTALL CORE DEPENDENCIES
# ---------------------------------------------------------
$requirementsPath = "requirements-dev.txt"
if (Test-Path $requirementsPath) {
    Write-Host "Installing requirements-dev.txt..."
    pip install -r $requirementsPath
}
else {
    Write-Host "Warning: requirements-dev.txt not found."
}
Write-Host ""

# ---------------------------------------------------------
# CONFIGURE VS CODE SETTINGS
# ---------------------------------------------------------
Write-Host "Configuring VS Code settings..."
if (!(Test-Path ".vscode")) {
    New-Item -ItemType Directory -Path ".vscode" | Out-Null
}

$vscodeSettings = @'
{
    "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
    "python.analysis.extraPaths": ["/socrata_toolkit"],
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": ["tests"],
    "python.linting.pylintEnabled": true,
    "editor.formatOnSave": true,
    "python.formatting.provider": "black",
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true
    }
}
'@
Set-Content -Path ".vscode/settings.json" -Value $vscodeSettings
Write-Host "VS Code settings updated."
Write-Host ""

# ---------------------------------------------------------
# ENSURE __init__.py EXISTS
# ---------------------------------------------------------
if (!(Test-Path "socrata_toolkit/__init__.py")) {
    Set-Content -Path "socrata_toolkit/__init__.py" -Value ""
}

Write-Host "socrata_toolkit package finalized."
Write-Host ""
Write-Host "==============================================="
Write-Host " SETUP COMPLETE"
Write-Host "==============================================="
