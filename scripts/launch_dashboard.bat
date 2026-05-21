@echo off
REM NYC DOT Toolkit — Streamlit / legacy Dash launcher (beside nyc-dot-toolkit.exe)
setlocal
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%launch_gui.ps1" -AppDir "%SCRIPT_DIR%"
endlocal
