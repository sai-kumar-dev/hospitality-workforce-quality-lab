# ADR 0004: Chromium pull-request gate

Status: Accepted — 2026-07-29

## Decision

Gate pull requests with focused Chromium smoke. Run Firefox and WebKit on `main`, schedule, and
manual dispatch.

## Consequences

Developers receive fast high-signal feedback while the project still detects engine-specific
regressions. Expensive suites are not multiplied without risk justification.

