# Runtime Schema

## Visual Flow

```mermaid
flowchart LR
  A[Codex CLI Events] --> B[telegram-notify.sh]
  B --> C[codex_telegram.py notify]
  C --> D[Telegram Bot API sendMessage]
  E[systemd user service] --> F[codex_telegram.py bot]
  F --> G[Telegram Bot API getUpdates]
  G --> F
  F --> D
  C --> H[~/.codex/hooks/state/*]
  F --> H
```

## Components

- Event ingress: `hooks/telegram-notify.sh`
- Event processor + bot loop: `hooks/codex_telegram.py`
- Installer/orchestration: `scripts/manage.py`
- Service template: `systemd/codex-telegram-bot.service.template`
- Local credentials: `~/.codex/hooks/telegram.env` (not stored in git)
