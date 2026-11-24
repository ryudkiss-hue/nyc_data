@echo off
rem NYC DOT SIM Mission Control — one-command launcher (solo workstation)
rem Starts the Dash app on http://localhost:8011 using the project venv.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Create it first:  uv venv ^&^& uv pip install -e ".[mission]" -r requirements-dev.txt
    exit /b 1
)

echo Starting Mission Control at http://localhost:8011 ...
start "" http://localhost:8011
".venv\Scripts\python.exe" app\dash_app.py
endlocal
