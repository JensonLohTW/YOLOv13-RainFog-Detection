#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "執行 Django / 推理服務測試"
ensure_command uv

log_file="$LOG_DIR/backend-test.log"
(
  export DJANGO_SETTINGS_MODULE=config.settings.test
  cd "$REPO_ROOT/backend"
  uv run --group dev python -m pytest "$@"
) 2>&1 | tee "$log_file"
