@echo off
chcp 65001 > nul
:: YOLOv13-RainFog-Detection Windows 一鍵部署批次檔 (.bat)
:: 目的：雙擊啟動以 docker-compose.prod.yml 為基礎的全端容器部署

echo 🚀 YOLOv13 RainFog Detection - 開始全端 Docker 部署 (for Windows)
echo =========================================================

:: 切換回專案根目錄 (透過此 bat 檔相對路徑計算)
cd /d "%~dp0\..\.."

:: 模擬與檢查 Docker Engine 連線狀態
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 錯誤：Docker 未啟動或未安裝！
    echo 👉 解決：這通常是因為 Docker Desktop 未開啟，或是底層的 WSL2 引擎尚在睡夢中。請開啟軟體後重試。
    echo =========================================================
    pause
    exit /b 1
)

:: 自動生成遺失的變數檔
if not exist "backend\.env" (
    echo ⚠️ 發現尚未配置 backend\.env！正在自動以範本生成...
    copy backend\.env.example backend\.env >nul
    echo ✨ 注意：若是真實對外公開的上線環境，請記得進去變更 MySQL 相關敏感密碼。
)

echo 🔄 正在強制停止任何可能霸佔 8000/3306 埠號之舊開發環境...
docker compose -f docker-compose.dev.yml down >nul 2>&1

echo 📦 正在讀取 Dockerfile 編譯您的最新代碼，並推送至背景啟動...
:: 呼叫正式的部署 Compose
docker compose -f docker-compose.prod.yml up -d --build

echo =========================================================
echo ✅ 系統已經順利建置進入 Docker 囉！各項服務的連結如下：
echo.
echo 🌐 儀表板與前端操作介面: http://localhost:5173
echo ⚙️ Django API 後台 (僅供管理者與 Swagger): http://localhost:8000
echo 🧠 FastAPI 模型服務存活偵測: http://localhost:9000/internal/health
echo.
echo 👉 若要隨時觀察所有伺服器輸出的即時訊息，請另開終端機輸入: 
echo    docker compose -f docker-compose.prod.yml logs -f
echo =========================================================
pause
