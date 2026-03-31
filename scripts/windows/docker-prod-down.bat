@echo off
chcp 65001 > nul
:: 停止並移除所有 docker-compose.prod.yml 容器

cd /d "%~dp0\..\.."

echo 🛑 正在停止 YOLOv13 RainFog Detection 生產容器...
docker compose -f docker-compose.prod.yml down

if %errorlevel% equ 0 (
    echo ✅ 所有容器已停止。
) else (
    echo ❌ 停止失敗，請確認 Docker Desktop 是否正在執行。
)
pause
