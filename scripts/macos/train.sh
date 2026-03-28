#!/usr/bin/env bash
# YOLOv13 微調訓練啟動腳本（前景執行，訓練日誌直接輸出至終端）
#
# 使用方式：
#   ./scripts/macos/train.sh [OPTIONS]
#
# 範例：
#   ./scripts/macos/train.sh --epochs 100 --batch 8 --model yolov13s.pt
#   ./scripts/macos/train.sh --device cpu --imgsz 416
#   ./scripts/macos/train.sh --resume
#
# 所有可用參數：執行 ./scripts/macos/train.sh --help

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "確認執行環境"
ensure_command uv

print_step "確認 ultralytics 依賴（需 --extra yolo）"
if ! (cd "$REPO_ROOT/backend" && uv run python -c "import ultralytics" 2>/dev/null); then
  echo "[ERROR] ultralytics 未安裝，請先執行："
  echo "  cd backend && uv sync --extra yolo"
  exit 1
fi

print_step "啟動 YOLOv13 微調訓練"
echo "[INFO] 訓練輸出目錄預設為：data/train_runs/rainfog_finetune/"
echo "[INFO] 可透過 --project 與 --name 參數自訂"
echo

cd "$REPO_ROOT/backend"
uv run python -m training.train "$@"
