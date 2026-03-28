#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "停止 Django 後端"
stop_service_by_pid_file "backend"
