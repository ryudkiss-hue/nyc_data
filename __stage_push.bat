@echo off
cd /d C:\Users\ryudk\Desktop\nyc_data
git add -A
git status --short | head -5
git commit -m "style: apply ruff auto-fixes (import sorting, type annotation upgrades)"
git push origin main
echo PUSH_DONE=%ERRORLEVEL%
del __stage_push.bat
