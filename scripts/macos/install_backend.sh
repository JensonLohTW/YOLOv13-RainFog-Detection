#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "安裝後端依賴"
ensure_command uv

if [[ ! -f "$REPO_ROOT/backend/.env" && -f "$REPO_ROOT/backend/.env.example" ]]; then
  # 首次安裝時自動複製環境變量模板，減少手工操作。
  cp "$REPO_ROOT/backend/.env.example" "$REPO_ROOT/backend/.env"
  echo "[INFO] 已生成 backend/.env"
fi

cd "$REPO_ROOT/backend"
uv sync --extra yolo
