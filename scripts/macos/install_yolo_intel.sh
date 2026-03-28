#!/usr/bin/env bash
# Intel Mac (x86_64) 專用 ultralytics 安裝腳本。
#
# 背景：PyTorch 自 2.3 起停止提供 macOS x86_64 PyPI wheel，
# 因此 `uv sync --extra yolo` 在 Intel Mac 上會失敗。
# 本腳本改用 `uv pip install` 直接安裝相容版本，繞過 lock 檔限制。
#
# 使用方式：
#   ./scripts/macos/install_yolo_intel.sh

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "確認 uv 已安裝"
ensure_command uv

print_step "安裝 Intel Mac 相容版本的 PyTorch（torch<=2.2.2）"
echo "[INFO] 此步驟會下載約 200MB，首次執行需要一些時間..."
cd "$REPO_ROOT/backend"
uv pip install "torch==2.2.2" "torchvision==0.17.2"

print_step "安裝 ultralytics（不更新 torch）"
uv pip install "ultralytics>=8.3,<9.0" --no-deps
uv pip install "psutil" "py-cpuinfo" "seaborn" "pandas" "matplotlib" "scipy" "thop"

print_step "降級 NumPy 至 1.x（torch 2.2.2 以 NumPy 1.x 編譯，2.x 不相容）"
uv pip install "numpy<2"

print_step "驗證安裝"
uv run python -c "
import torch, ultralytics
print(f'torch     : {torch.__version__}')
print(f'ultralytics: {ultralytics.__version__}')
print(f'CUDA 可用  : {torch.cuda.is_available()}')
"

echo
echo "[OK] ultralytics 安裝完成，可執行 ./scripts/macos/train.sh 開始訓練"
