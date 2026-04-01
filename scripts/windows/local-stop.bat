@echo off
chcp 65001 > nul
:: 停止本地開發服務（完全本機模式，不使用 Docker）
:: 只停止 Django / FastAPI / React，MySQL 和 Redis 由你自行管理

cd /d "%~dp0\..\.."

echo =========================================================
echo  YOLOv13 RainFog Detection - 停止本地開發環境
echo =========================================================

echo.
echo 停止 Django + FastAPI + React...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-all.ps1"

echo.
echo ✅ 應用服務已停止。
echo    MySQL / Redis 為本機服務，若需停止請手動執行：
echo       net stop MySQL
echo       redis-cli shutdown
pause
