@echo off
title AI Job Discovery & Resume Tailoring System
cd /d "%~dp0"
echo ============================================================
echo   Running Daily AI Job Discovery & Resume Tailoring Pipeline
echo ============================================================
python main.py --run
echo.
echo Pipeline completed. Check output\dashboard.html for today's results!
pause
