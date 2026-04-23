# Codex Telegram Task Notifier

Global Codex Telegram notifications for:
- task completion
- approval requests
- user input requests
- bot commands `/codex_status` and `/ping`

## Quick Start (Clone + Install)

```bash
git clone git@github.com:kistik1/codex-telegram-task-notifier.git
cd codex-telegram-task-notifier
./scripts/install.sh
~/.codex/hooks/setup-telegram-notify.sh
./scripts/verify.sh
```

Setup prompts for `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` and stores them only on the local machine in `~/.codex/hooks/telegram.env`.

## Runtime Layout

- Skill bundle: `~/.codex/skills/telegram-task-notifier`
- Notify hook: `~/.codex/hooks/telegram-notify.sh`
- Bot bridge: `~/.codex/hooks/codex_telegram.py`
- Local secrets: `~/.codex/hooks/telegram.env`
- Bot state: `~/.codex/hooks/state/`
- User service: `~/.config/systemd/user/codex-telegram-bot.service`

## Common Commands

```bash
./scripts/install.sh
./scripts/repair.sh
./scripts/verify.sh
```

Manual send test (optional):

```bash
python3 ./scripts/manage.py send-test manual
```

## Migration to Another Machine

```bash
git clone git@github.com:kistik1/codex-telegram-task-notifier.git
cd codex-telegram-task-notifier
./scripts/install.sh
~/.codex/hooks/setup-telegram-notify.sh
./scripts/verify.sh
```

Notes:
- Do not copy `telegram.env` via git.
- The installer is path-aware and supports `CODEX_HOME` override.
