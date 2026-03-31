@echo off
chcp 65001 > nul
:: 停止所有本地開發服務 + MySQL/Redis 基礎設施

cd /d "%~dp0\..\.."

echo =========================================================
echo  YOLOv13 RainFog Detection - 停止本地開發環境
echo =========================================================

:: 停止 Django / FastAPI / React（透過 PID 文件）
echo.
echo [1/2] 停止 Django + FastAPI + React...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-all.ps1"

:: 停止 MySQL + Redis
echo.
echo [2/2] 停止 MySQL + Redis 基礎設施...
docker compose -f docker-compose.dev.yml down

echo.
echo ✅ 所有服務已停止。
pause
