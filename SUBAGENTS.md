# Subagents

## notifier-orchestrator

- Name: `notifier-orchestrator`
- Purpose: Coordinate install/repair/uninstall lifecycle and systemd unit management.
- Scope: `scripts/manage.py`, `systemd/*`, installer command wrappers.
- Inputs: CLI command (`install|repair|verify|uninstall`), local environment paths.
- Outputs: Installed files, updated config hook, service state transitions, verification JSON.
- Tools/permissions: local filesystem writes to `CODEX_HOME`, user-level `systemctl`.
- Limits: no remote secret storage, no destructive system actions outside notifier assets.
- Triggers: install, repair, migration, uninstall operations.
- Dependencies: Python 3, Bash, systemd user service availability.

## notifier-validator

- Name: `notifier-validator`
- Purpose: Validate runtime health and message delivery readiness.
- Scope: `scripts/verify.sh`, `scripts/send-test.sh`, `scripts/send-approval-test.sh`.
- Inputs: configured local env (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`), hook payload test events.
- Outputs: pass/fail checks, test message delivery outcome.
- Tools/permissions: local reads plus outbound Telegram API connectivity.
- Limits: does not mutate install layout except state/event logs.
- Triggers: post-install validation, incident troubleshooting, migration acceptance checks.
- Dependencies: notifier hook files installed and valid credentials.
