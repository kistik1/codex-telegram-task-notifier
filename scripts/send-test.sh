#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="${1:-manual}"
python3 "$SCRIPT_DIR/manage.py" send-test "$LABEL"
