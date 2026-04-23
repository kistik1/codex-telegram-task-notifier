# notifier-orchestrator

Main orchestrator for lifecycle operations of the Codex Telegram notifier.

## Responsibilities

- Execute install/repair/uninstall flows through `scripts/manage.py`.
- Ensure hook registration in `config.toml`.
- Maintain user service unit consistency.

## Non-Responsibilities

- Storing credentials in version control.
- Managing unrelated Codex plugins or services.
