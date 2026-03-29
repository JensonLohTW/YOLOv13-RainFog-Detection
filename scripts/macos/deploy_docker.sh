#!/usr/bin/env bash
# YOLOv13-RainFog-Detection macOS / Linux Docker Deployment Script
# 目的：一鍵啟動以 docker-compose.prod.yml 為基礎的生產級全端容器部署
set -e

# 自動切換工作目錄至專案根目錄
cd "$(dirname "$0")/../.."

echo "🚀 YOLOv13 RainFog Detection - 開始全端 Docker 部署"
echo "========================================================="

# 檢查 Docker 使否有成功開啟
if ! docker info > /dev/null 2>&1; then
  echo "❌ 錯誤：Docker 未啟動或未安裝！"
  echo "👉 解決：請在應用程式啟動 Docker Desktop 或是 OrbStack 後再重試。"
  exit 1
fi

# 協助確認並備妥環境變數檔
if [ ! -f "backend/.env" ]; then
  echo "⚠️ 發現尚未配置 backend/.env，自動將 .env.example 複製一份作為預設配置..."
  cp backend/.env.example backend/.env
  echo "✨ 注意：若是真實上線，請記得手動進入 backend/.env 修改密碼配置。"
fi

echo "🔄 正在關閉任何可能卡住埠號的舊有開發環境 (docker-compose.dev.yml)..."
docker compose -f docker-compose.dev.yml down 2>/dev/null || true

echo "📦 正在編譯映像檔 (Images) 並背景啟動所有服務..."
# 使用 -d 代表背景執行模式，--build 強制由 Dockerfile 重拉依賴
docker compose -f docker-compose.prod.yml up -d --build

echo "========================================================="
echo "✅ 系統已經在容器中啟動成功！以下為對外服務入口點："
echo ""
echo "🌐 業務與儀表板前端: http://localhost:5173"
echo "⚙️ Django 後端系統 (開發除錯介面): http://localhost:8000"
echo "🧠 FastAPI 推理端 (僅供健康探針): http://localhost:9000/internal/health"
echo ""
echo "👉 小提示：若要隨時觀察各個服務輸出了什麼，請於終端機執行："
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo "========================================================="
