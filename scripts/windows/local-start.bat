@echo off
setlocal

cd /d "%~dp0\..\.."

echo =========================================================
echo  YOLOv13 RainFog Detection - Local Dev Start
echo  Requires: MySQL + Redis running locally
echo =========================================================
echo.

if not exist "backend\.env" (
    echo [INFO] Copying .env.example to backend\.env
    copy "backend\.env.example" "backend\.env" >nul
    echo [INFO] Done. Edit backend\.env to set DB credentials.
    echo.
)

echo Starting Django + FastAPI + React...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-all.ps1"

echo.
echo =========================================================
echo  Services running in background:
echo    Frontend : http://localhost:5173
echo    Django   : http://localhost:8000
echo    FastAPI  : http://localhost:9000/internal/health
echo.
echo  Logs : logs\backend.log  logs\inference.log  logs\frontend.log
echo  Stop : local-stop.bat
echo =========================================================
pause
