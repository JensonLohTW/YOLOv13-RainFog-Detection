#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "啟動 Django 後端"
ensure_command uv

start_service "backend" "$REPO_ROOT/backend" "uv run python manage.py runserver 0.0.0.0:8000"
