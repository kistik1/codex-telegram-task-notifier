# Plan

## 2026-04-23 - GitHub Publish + Reuse Standardization

### What Will Be Built

- A publish-ready repository for the Telegram notifier with complete onboarding documentation and compliance/planning artifacts.
- Deterministic cross-machine install flow based on `clone -> install -> setup secrets -> verify`.

### Architecture

- Hook path in Codex config triggers `telegram-notify.sh`.
- Hook script forwards structured payload to `codex_telegram.py notify`.
- Background bot process runs via user systemd unit for command polling.
- Runtime credentials remain local in `~/.codex/hooks/telegram.env`.

### Steps

1. Clean repository structure and ignore rules to prevent secret/runtime artifact commits.
2. Add missing operational docs (`SCHEMA.md`, `FEATURES.md`, `LEGAL.md`, `RESEARCH.md`, `PLAN.md`, `SUBAGENTS.md`).
3. Validate installer and notifier behavior with verify/test commands.
4. Publish repository to GitHub and tag initial release.

### Risks

- Medium: notifier notifications could pause if user service is not active after migration.
- Low: accidental secret exposure if local env file is manually added by mistake.

### Dependencies

- Python 3
- Bash
- user-level systemd (for persistent bot mode)
- Telegram bot token and chat ID configured locally

### Approval

HUMAN REVIEW approval recorded by explicit user command: "Implement the plan."
