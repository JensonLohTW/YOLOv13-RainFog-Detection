#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"

print_step "初始化 MySQL 資料庫與帳號"
ensure_command mysql

MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_ROOT_USER="${MYSQL_ROOT_USER:-root}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-rainfog}"
MYSQL_APP_USER="${MYSQL_APP_USER:-rainfog}"
MYSQL_APP_PASSWORD="${MYSQL_APP_PASSWORD:-rainfog123}"

if [[ -z "$MYSQL_ROOT_PASSWORD" ]]; then
  echo "[ERROR] 請先設置 MYSQL_ROOT_PASSWORD 環境變量。"
  exit 1
fi

render_template() {
  local template_file="$1"
  sed \
    -e "s/{{MYSQL_DATABASE}}/$MYSQL_DATABASE/g" \
    -e "s/{{MYSQL_APP_USER}}/$MYSQL_APP_USER/g" \
    -e "s/{{MYSQL_APP_PASSWORD}}/$MYSQL_APP_PASSWORD/g" \
    "$template_file"
}

run_template() {
  local template_file="$1"
  local temp_file
  temp_file="$(mktemp)"
  render_template "$template_file" >"$temp_file"
  mysql \
    --host="$MYSQL_HOST" \
    --port="$MYSQL_PORT" \
    --user="$MYSQL_ROOT_USER" \
    --password="$MYSQL_ROOT_PASSWORD" <"$temp_file"
  rm -f "$temp_file"
}

# 依序建立資料庫、帳號與授權，便於後續手動部署 MySQL。
run_template "$REPO_ROOT/mysql/sql/00_create_database.sql.tpl"
run_template "$REPO_ROOT/mysql/sql/01_create_user.sql.tpl"
run_template "$REPO_ROOT/mysql/sql/02_grant_privileges.sql.tpl"

mysql \
  --host="$MYSQL_HOST" \
  --port="$MYSQL_PORT" \
  --user="$MYSQL_ROOT_USER" \
  --password="$MYSQL_ROOT_PASSWORD" <"$REPO_ROOT/mysql/sql/03_verify_setup.sql"

echo "[INFO] MySQL 初始化完成。"
