#!/usr/bin/env bash

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/stop_frontend.sh"
"$SCRIPT_DIR/stop_inference.sh"
"$SCRIPT_DIR/stop_backend.sh"
