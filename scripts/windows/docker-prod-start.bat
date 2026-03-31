@echo off
chcp 65001 > nul
:: 快速啟動（不重新 build 鏡像）。
:: 適合：已跑過 deploy_docker.bat 之後，只需重啟容器時使用。

cd /d "%~dp0\..\.."

docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未啟動，請先開啟 Docker Desktop。
    pause
    exit /b 1
)

echo ▶️  快速啟動生產容器（跳過 build）...
docker compose -f docker-compose.prod.yml up -d

echo =========================================================
echo ✅ 容器已啟動：
echo 🌐 前端:    http://localhost:5173
echo ⚙️  Django:  http://localhost:8000
echo 🧠 FastAPI: http://localhost:9000/internal/health
echo.
echo 查看即時 log：
echo    docker compose -f docker-compose.prod.yml logs -f
echo =========================================================
pause
