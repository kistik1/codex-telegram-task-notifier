#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

PAYLOAD="${1:-$(cat)}"
printf '%s' "$PAYLOAD" | "$PYTHON_BIN" "$SCRIPT_DIR/codex_telegram.py" notify
