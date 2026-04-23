# Research

## 2026-04-23 - Publish and Multi-Machine Reuse

### Problem

Existing notifier setup was working on this machine but not packaged in a publish-ready repository with clear onboarding and compliance/planning docs.

### Options

1. Keep local-only setup under `~/.codex`.
2. Publish as standalone repo with install scripts and local secret onboarding.
3. Convert to a larger mono-repo utility package.

### Trade-Offs

- Option 1: fastest short-term, poor portability.
- Option 2: best portability and lowest operational risk.
- Option 3: higher complexity with little immediate value.

### Risks

- Secrets leak risk if `telegram.env` or state files are committed.
- Machine drift risk if paths are hardcoded.
- Runtime risk if service unit is not enabled/restarted correctly after install.

### Decision

Use option 2:
- standalone GitHub repository
- clone + install workflow
- local-only secret onboarding with prompt-based setup
- verify and test scripts included in documented flow

### Planned Subagents

- `notifier-orchestrator`: coordinate install/repair/verify lifecycle.
- `notifier-validator`: run health checks and test-notification checks.
