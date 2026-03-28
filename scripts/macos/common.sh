#!/usr/bin/env bash

set -euo pipefail

# 統一解析專案根目錄，避免不同腳本重複寫路徑。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUN_DIR="$REPO_ROOT/.run"
LOG_DIR="$REPO_ROOT/logs"

mkdir -p "$RUN_DIR" "$LOG_DIR"

print_step() {
  echo
  echo "[STEP] $1"
}

ensure_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] 缺少命令：$1"
    exit 1
  fi
}

stop_service_by_pid_file() {
  local name="$1"
  local pid_file="$RUN_DIR/$name.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "[INFO] $name 沒有 PID 文件，跳過停止。"
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"

  if ps -p "$pid" >/dev/null 2>&1; then
    pkill -TERM -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
    echo "[INFO] 已停止 ${name}，PID=$pid"
  else
    echo "[WARN] $name 的 PID=$pid 不存在，將清理 PID 文件。"
  fi

  rm -f "$pid_file"
}

start_service() {
  local name="$1"
  local workdir="$2"
  local command="$3"
  local pid_file="$RUN_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"

  if [[ -f "$pid_file" ]]; then
    local existing_pid
    existing_pid="$(cat "$pid_file")"
    if ps -p "$existing_pid" >/dev/null 2>&1; then
      echo "[INFO] $name 已在運行，PID=$existing_pid"
      return 0
    fi
    rm -f "$pid_file"
  fi

  # 使用 nohup 背景啟動，方便本地長時間運行。
  nohup bash -lc "cd '$workdir' && $command" >"$log_file" 2>&1 &
  local pid=$!
  echo "${pid}" >"${pid_file}"
  echo "[INFO] 已啟動 ${name}，PID=${pid}，日誌=${log_file}"
}
