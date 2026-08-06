# Contributing

ShiftBridge is a quality-engineering portfolio lab. Changes should make behavior easier to
trust, diagnose, or maintain—not merely increase test count.

## Development workflow

1. Create a focused branch from `main`.
2. Copy `.env.example` to `.env`; keep all values local and fictional.
3. Run `make setup` (or `.\scripts\bootstrap.ps1` on Windows).
4. Start the stack with `make app-up`.
5. Add the smallest production change and tests at the right layer.
6. Run `make quality`, then the affected integration suites.
7. Update `docs/TEST_CASES.md` when behavior or coverage changes.

Use Conventional Commit-style subjects when practical, such as `feat(api): prevent inactive
job applications` or `test(ui): cover expired sessions`.

## Test expectations

- Exercise both success and meaningful failure paths.
- Prefer service/unit coverage for rules, API coverage for contracts and authorization, and UI
  coverage for user-visible integration.
- Use role, label, placeholder, and visible-text locators in that order.
- Never use arbitrary sleeps, blanket retries, production data, or order-dependent identities.
- New parallel-safe tests must use run/worker-aware factories.
- A failed test is evidence to investigate, not proof that a test is flaky.

## Quarantine policy

Quarantine is exceptional. A quarantined case must stay in reporting and name an owner, reason,
tracking issue, and expiration date. The root cause must be classified as Product, Test,
Environment, Data, or Unknown. There are no automatic retries in pull-request gates.

## Pull requests

Complete the repository pull-request template. Include request IDs or redacted artifacts for
defect fixes. Do not attach cookies, tokens, passwords, database dumps, or unredacted cover notes.

