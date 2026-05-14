@echo off
chcp 65001 > nul
color 0B

echo ╔═════════════════════════════════════════════════════════════════╗
echo ║           NYC DOT MISSION CONTROL - DATA SYNC                   ║
echo ║                Automated Ingestion Protocol                     ║
echo ╚═════════════════════════════════════════════════════════════════╝
echo.

:: Point this to your mapped network drive or shared folder containing the keys
set SHARED_ENV_PATH=Z:\Shared_Configs\nyc_socrata_api.env
echo 🔐 Mounting Secure Configuration: %SHARED_ENV_PATH%
echo.

cd /d "%~dp0"
dist\nyc_toolkit.exe cli sync -i erm2-nwe9 --table complaints_311 --optimize
echo.
pause