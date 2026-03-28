#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "啟動 React 前端"
ensure_command npm

start_service "frontend" "$REPO_ROOT/frontend" "npm run dev -- --host 0.0.0.0 --port 5173"
