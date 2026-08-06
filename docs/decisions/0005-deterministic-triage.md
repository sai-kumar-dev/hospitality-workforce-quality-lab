# ADR 0005: Deterministic triage before an LLM

Status: Accepted — 2026-07-29

## Decision

Normalize, group, redact, and classify failures with local transparent rules. Define an adapter
boundary for an optional future LLM, disabled by default.

## Consequences

CI remains repeatable, private, cheap, and available offline. The report explains evidence and
confidence; it does not overstate rules as machine learning.
