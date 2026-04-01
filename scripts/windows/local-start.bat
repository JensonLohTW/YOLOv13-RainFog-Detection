@echo off
chcp 65001 > nul
:: 本地開發啟動腳本（完全不使用 Docker，MySQL 和 Redis 需自行安裝在本機）
:: 流程：檢查本機 MySQL/Redis → 啟動 Django → FastAPI → React

cd /d "%~dp0\..\.."

echo =========================================================
echo  YOLOv13 RainFog Detection - 本地開發環境啟動
echo  （完全本機模式，不使用 Docker）
echo =========================================================

:: 確認 backend\.env 存在
if not exist "backend\.env" (
    echo ⚠️  尚未設定 backend\.env，正在以範本自動生成...
    copy backend\.env.example backend\.env >nul
    echo ✅ 已生成 backend\.env，請確認 MYSQL_HOST / MYSQL_PASSWORD 等設定正確。
    echo.
)

:: 檢查本機 MySQL（3306 port）
echo [1/3] 檢查本機 MySQL (127.0.0.1:3306)...
powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient; try { $c.Connect('127.0.0.1',3306); Write-Host '[OK] MySQL 已在線'; $c.Close() } catch { Write-Host '[WARN] MySQL 未偵測到！請先啟動 MySQL 服務。'; exit 1 }"
if %errorlevel% neq 0 (
    echo.
    echo ❌ 請先啟動本機 MySQL，再執行此腳本。
    echo    下載安裝：https://dev.mysql.com/downloads/mysql/
    echo    啟動方式：在「服務」中啟動 MySQL，或執行：
    echo       net start MySQL
    pause
    exit /b 1
)

:: 檢查本機 Redis（6379 port）
echo [2/3] 檢查本機 Redis (127.0.0.1:6379)...
powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient; try { $c.Connect('127.0.0.1',6379); Write-Host '[OK] Redis 已在線'; $c.Close() } catch { Write-Host '[WARN] Redis 未偵測到！請先啟動 Redis 服務。'; exit 1 }"
if %errorlevel% neq 0 (
    echo.
    echo ❌ 請先啟動本機 Redis，再執行此腳本。
    echo    下載安裝：https://github.com/tporadowski/redis/releases
    echo    啟動方式：在「服務」中啟動 Redis，或執行：
    echo       redis-server
    pause
    exit /b 1
)

:: 啟動 Django + FastAPI + React
echo.
echo [3/3] 啟動 Django + FastAPI + React...
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
