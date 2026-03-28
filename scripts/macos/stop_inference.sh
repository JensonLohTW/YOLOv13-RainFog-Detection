#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "停止 FastAPI 推理服務"
stop_service_by_pid_file "inference"
