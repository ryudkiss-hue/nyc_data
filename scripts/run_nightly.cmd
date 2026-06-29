@echo off
REM ==========================================================================
REM NYC DOT — nightly local-first pipeline runner (invoked by Task Scheduler).
REM Runs pipeline\run_local.py end-to-end (ingest -> staging -> analytics ->
REM metrics -> geo -> compact -> publish serving layer to MotherDuck), logging
REM to a dated file. Exit code is propagated so the scheduled task reports
REM success/failure correctly.
REM ==========================================================================
setlocal

REM Repo root = parent of this script's directory.
set "REPO=%~dp0.."
pushd "%REPO%"

REM Prefer the project venv; fall back to PATH python.
set "PY=%REPO%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

if not exist "%REPO%\pipeline\logs" mkdir "%REPO%\pipeline\logs"

REM Date stamp (locale-independent) via PowerShell.
for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "STAMP=%%d"
set "LOG=%REPO%\pipeline\logs\nightly_%STAMP%.log"

echo ====================================================================== >> "%LOG%"
echo NIGHTLY RUN start %DATE% %TIME% >> "%LOG%"
echo ====================================================================== >> "%LOG%"

"%PY%" pipeline\run_local.py >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"

echo NIGHTLY RUN end %DATE% %TIME% exit=%RC% >> "%LOG%"

popd
endlocal & exit /b %RC%
