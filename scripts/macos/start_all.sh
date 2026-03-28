#!/usr/bin/env bash

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/start_backend.sh"
"$SCRIPT_DIR/start_inference.sh"
"$SCRIPT_DIR/start_frontend.sh"
