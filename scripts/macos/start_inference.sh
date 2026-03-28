#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "啟動 FastAPI 推理服務"
ensure_command uv

start_service "inference" "$REPO_ROOT/backend" "uv run uvicorn inference_service.main:app --host 0.0.0.0 --port 9000 --reload"
