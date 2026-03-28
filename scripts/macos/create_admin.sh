#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "建立 Django 超級管理員"
ensure_command uv

cd "$REPO_ROOT/backend"
uv run python manage.py createsuperuser
