@echo off
chcp 65001 > nul
:: 本地開發啟動腳本（不使用 Docker 跑應用服務）
:: 流程：啟動 MySQL+Redis 基礎設施 → Django → FastAPI → React

cd /d "%~dp0\..\.."

echo =========================================================
echo  YOLOv13 RainFog Detection - 本地開發環境啟動
echo =========================================================

:: 檢查 Docker（MySQL / Redis 基礎設施仍需 Docker）
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未啟動！MySQL 和 Redis 需要 Docker Desktop。
    echo    請先開啟 Docker Desktop 後再執行此腳本。
    pause
    exit /b 1
)

:: 啟動 MySQL + Redis
echo.
echo [1/4] 啟動 MySQL + Redis 基礎設施...
docker compose -f docker-compose.dev.yml up -d
if %errorlevel% neq 0 (
    echo ❌ 基礎設施啟動失敗。
    pause
    exit /b 1
)
echo ✅ MySQL (3306) + Redis (6379) 已啟動

:: 等待 MySQL 就緒
echo.
echo [2/4] 等待 MySQL 就緒（5 秒）...
timeout /t 5 /nobreak > nul

:: 啟動 Django 後端
echo.
echo [3/4] 啟動 Django 後端 + FastAPI 推理服務 + React 前端...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-all.ps1"

echo.
echo =========================================================
echo ✅ 所有服務已在背景啟動：
echo.
echo 🌐 前端介面:    http://localhost:5173
echo ⚙️  Django API:  http://localhost:8000
echo 🧠 FastAPI:     http://localhost:9000/internal/health
echo.
echo 查看 log：  logs\backend.log / logs\inference.log / logs\frontend.log
echo 停止服務：  執行 local-stop.bat
echo =========================================================
pause
