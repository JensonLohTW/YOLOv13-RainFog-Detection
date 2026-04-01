@echo off
setlocal

cd /d "%~dp0\..\.."

echo =========================================================
echo  YOLOv13 RainFog Detection - Local Dev Stop
echo =========================================================

echo.
echo Stopping Django + FastAPI + React...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-all.ps1"

echo.
echo [OK] Application services stopped.
echo      MySQL and Redis are local services - stop them manually if needed:
echo        net stop MySQL
echo        redis-cli shutdown
pause
