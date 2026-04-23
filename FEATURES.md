# Features Roadmap

## Existing Features

- Global Codex notify hook integration via `notify = [".../telegram-notify.sh"]`.
- Telegram alerts for:
  - `agent-turn-complete`
  - `approval-requested`
  - `user-input-requested`
- Telegram bot listener with `/codex_status` and `/ping`.
- User-level systemd service installer for persistent bot polling.
- Verification and test scripts:
  - `verify.sh`
  - `send-test.sh`
  - `send-approval-test.sh`
- Repair workflow for migrated environments (`repair.sh`).

## Planned Features

- Optional richer message formatting (Markdown-safe summaries).
- Optional message throttling windows for noisy sessions.
- Optional per-project label routing in status output.
- Optional installation profile for non-systemd environments.
