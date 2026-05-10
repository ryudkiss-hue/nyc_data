@echo off
setlocal

set SRC=C:\Users\ryudk\Downloads\nyc_data
set DST=C:\Users\ryudk\Desktop\nyc_data_updated_2026-05-08

if not exist "%SRC%" (
  echo Source path does not exist: %SRC%
  exit /b 1
)

if not exist "%DST%" mkdir "%DST%"

robocopy "%SRC%" "%DST%" /MIR /R:1 /W:1 /XD .git __pycache__ .venv
if %ERRORLEVEL% GEQ 8 (
  echo Robocopy failed with exit code %ERRORLEVEL%
  exit /b %ERRORLEVEL%
)

echo Files copied successfully to %DST%
endlocal
