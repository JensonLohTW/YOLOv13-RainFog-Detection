#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "停止 Docker 基礎設施"
ensure_command docker

cd "$REPO_ROOT"
docker compose -f docker-compose.dev.yml down
