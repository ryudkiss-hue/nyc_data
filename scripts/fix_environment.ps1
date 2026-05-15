# fix_environment.ps1
# Comprehensive script to install dependencies, clean imports, auto-fix linting, and verify tests.

$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path

Write-Host "🚀 Starting NYC DOT Toolkit Environment Fixer..." -ForegroundColor Cyan

Write-Host "`n📦 1. Installing Required Dependencies..." -ForegroundColor Yellow
# Install the package in editable mode with all extras and dev tools
python -m pip install -e "$projectRoot[all,dev]"
# Explicitly install known missing packages flagged in the reports
python -m pip install fastapi uvicorn psycopg[binary] shapely nicegui python-docx networkx kaleido pytest autoflake ruff black isort

Write-Host "`n🧹 2. Cleaning up unused imports (Autoflake)..." -ForegroundColor Yellow
python -m autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive "$projectRoot\socrata_toolkit" "$projectRoot\tests"

Write-Host "`n🛠️ 3. Auto-fixing linting issues (Ruff)..." -ForegroundColor Yellow
python -m ruff check "$projectRoot" --fix

Write-Host "`n🔤 4. Sorting imports (isort)..." -ForegroundColor Yellow
python -m isort "$projectRoot" --profile black

Write-Host "`n✨ 5. Formatting code (Black)..." -ForegroundColor Yellow
python -m black "$projectRoot" --line-length 100

Write-Host "`n🧪 6. Running Core API Tests..." -ForegroundColor Yellow
python -m pytest "$projectRoot\tests\test_type_exports.py" -v

Write-Host "`n✅ Environment fixed, code cleaned, and tests validated!" -ForegroundColor Green