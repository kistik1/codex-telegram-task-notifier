# Legal and Compliance

## Scope

This project handles notification metadata and Telegram delivery credentials on the local machine of the operator.

## Israeli Privacy Law Considerations

- Comply with the Israeli Protection of Privacy Law, 1981, including minimal collection and purpose limitation.
- Avoid storing personally identifiable information unless required for notifier operation.
- Keep local credential files permission-restricted (`chmod 600`).

## International Regulations (Including GDPR)

- Data minimization: send only operational notification content needed by the user.
- Purpose limitation: use data solely for Codex task and approval notifications.
- Storage limitation: retain only operational logs/state needed for troubleshooting.
- User rights: operator can clear local state files and uninstall the notifier at any time.

## Data Handling Policy

- Secrets are local-only (`~/.codex/hooks/telegram.env`) and excluded from git.
- Runtime state is local-only (`~/.codex/hooks/state`).
- No third-party data broker integrations.

## User Consent

- User explicitly configures Telegram bot token/chat ID during setup.
- User opts in by installing hook and service.
- User can opt out via `./scripts/uninstall.sh`.

## API Terms

- Telegram Bot API usage must comply with Telegram terms and acceptable use policies.
- Any upstream Codex-related integration must follow provider terms.

## Data Retention

- Retain only transient runtime/session state required for status and bot commands.
- Rotate/delete state logs manually as needed.

## Security Principles

- Least privilege: user-level service only.
- Secret isolation: no credential commit to repository.
- Explicit configuration and verification before use.
