# Codex Telegram Task Notifier

Reusable global Codex Telegram notifications for:
- task completion
- approval requests
- user input requests
- Telegram bot commands `/codex_status` and `/ping`

## Install

```bash
git clone <your-repo-url> codex-telegram-task-notifier
cd codex-telegram-task-notifier
./scripts/install.sh
~/.codex/hooks/setup-telegram-notify.sh <bot_token> <chat_id>
./scripts/verify.sh
./scripts/send-test.sh
```

## Publish

```bash
git init
git add .
git commit -m "Add Codex Telegram task notifier skill"
git remote add origin <your-github-repo-url>
git push -u origin main
git tag v1.0.0
git push origin v1.0.0
```

## Notes

- The installer copies the skill to `~/.codex/skills/telegram-task-notifier`
- The runtime hooks live under `~/.codex/hooks`
- The systemd user unit lives at `~/.config/systemd/user/codex-telegram-bot.service`
- The installer preserves existing `telegram.env` credentials
