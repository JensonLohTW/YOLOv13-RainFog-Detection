#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "安裝前端依賴"
ensure_command npm

if [[ ! -f "$REPO_ROOT/frontend/.env" && -f "$REPO_ROOT/frontend/.env.example" ]]; then
  cp "$REPO_ROOT/frontend/.env.example" "$REPO_ROOT/frontend/.env"
  echo "[INFO] 已生成 frontend/.env"
fi

cd "$REPO_ROOT/frontend"
npm install
