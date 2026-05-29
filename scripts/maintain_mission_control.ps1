# maintain_mission_control.ps1
# Automates environment health and cleanup tasks

Write-Host "--- Manhattan Mission Control: Maintenance Engine ---" -ForegroundColor Cyan

# 1. Clean build artifacts and pycache to prevent import ghosting
Write-Host "Purging build artifacts..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "__pycache__" -Recurse | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Filter "*.pyc" -Recurse | Remove-Item -Force

# 2. Sync dependencies
# If you changed dependencies in pyproject.toml, this forces the link
Write-Host "Updating editable installation..." -ForegroundColor Yellow
& .venv\Scripts\pip install -e .

# 3. Environment Validation
Write-Host "Running import sanity check..." -ForegroundColor Yellow
$check = & .venv\Scripts\python -c "import socrata_toolkit; print('Backend: OK'); from app import data_loader; print('Frontend: OK')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "Environment Health: PASSED" -ForegroundColor Green
    Write-Host $check
} else {
    Write-Host "Environment Health: FAILED. Check your python path." -ForegroundColor Red
}

# 4. Ready to Launch
Write-Host "`nReady to launch Mission Control." -ForegroundColor Green
Write-Host "Command: streamlit run app/app.py"