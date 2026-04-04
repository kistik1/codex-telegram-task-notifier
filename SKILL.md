---
name: telegram-task-notifier
description: Install, repair, verify, or explain global Codex Telegram notifications that send a message when Codex completes a task turn, needs approval, or needs user input. Use when the user wants reusable Telegram alerts across projects, wants to migrate the notifier to another PC, or wants to troubleshoot the notify hook or Telegram bot service.
metadata:
  short-description: Global Codex Telegram alerts
---

# Telegram Task Notifier

This skill manages a global Codex Telegram notifier installed under `$CODEX_HOME` or `~/.codex`.

Use it when the user wants to:
- install Telegram completion alerts on this machine
- repair a broken Telegram notifier after a migration or path change
- verify whether the notify hook, credentials, and bot service are healthy
- package or publish the notifier for reuse on another PC

## Runtime Layout

Installed paths:
- Skill bundle: `$CODEX_HOME/skills/telegram-task-notifier`
- Notify hook: `$CODEX_HOME/hooks/telegram-notify.sh`
- Bot bridge: `$CODEX_HOME/hooks/codex_telegram.py`
- Credentials: `$CODEX_HOME/hooks/telegram.env`
- Service unit: `~/.config/systemd/user/codex-telegram-bot.service`
- Config hook entry: `notify = ["$CODEX_HOME/hooks/telegram-notify.sh"]`

## Preferred Workflow

If working from the GitHub clone or skill source repo:
1. Run `scripts/install.sh`
2. Run `scripts/repair.sh`
3. If credentials are not configured yet, run:
   `"$CODEX_HOME/hooks/setup-telegram-notify.sh" <bot_token> <chat_id>`
4. Verify with:
   `scripts/verify.sh`

## Commands

Primary commands from the skill repo:
- `scripts/install.sh`
- `scripts/repair.sh`
- `scripts/verify.sh`
- `scripts/send-test.sh`
- `scripts/uninstall.sh`

If the user explicitly wants a manual live test, run `scripts/send-test.sh`.

## Troubleshooting

If notifications do not arrive:
1. Check `scripts/verify.sh`
2. Confirm `notify` exists in `$CODEX_HOME/config.toml`
3. Confirm `$CODEX_HOME/hooks/telegram.env` contains both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
4. Confirm the user-level service is present and active
5. Run `scripts/send-test.sh` for a real Telegram API send

If the machine was migrated and old absolute paths remain, run `scripts/repair.sh`. The packaged runtime resolves its own install path and should not depend on `/home/ubuntu` or any project-specific directory.
