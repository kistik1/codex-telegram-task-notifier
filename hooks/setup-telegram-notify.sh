#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ENV_FILE="${CODEX_TELEGRAM_ENV_FILE:-$SCRIPT_DIR/telegram.env}"
BOT_TOKEN="${1:-${TELEGRAM_BOT_TOKEN:-}}"
CHAT_ID="${2:-${TELEGRAM_CHAT_ID:-}}"

if [[ -z "$BOT_TOKEN" ]]; then
  read -r -p "Telegram bot token: " BOT_TOKEN
fi

if [[ -z "$CHAT_ID" ]]; then
  read -r -p "Telegram chat ID: " CHAT_ID
fi

mkdir -p "$(dirname "$ENV_FILE")"
umask 077

cat >"$ENV_FILE" <<EOF
TELEGRAM_BOT_TOKEN='$BOT_TOKEN'
TELEGRAM_CHAT_ID='$CHAT_ID'
EOF

chmod 600 "$ENV_FILE"

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload || true
  systemctl --user enable --now codex-telegram-bot.service || true
  systemctl --user restart codex-telegram-bot.service || true
fi

printf '%s' '{"type":"agent-turn-complete","source":"setup","thread_id":"telegram-setup","message":"Telegram notifications configured"}' | \
  "$PYTHON_BIN" "$SCRIPT_DIR/codex_telegram.py" notify

printf 'Saved Telegram credentials to %s\n' "$ENV_FILE"
