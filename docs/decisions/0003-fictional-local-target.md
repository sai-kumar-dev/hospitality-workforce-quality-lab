# ADR 0003: Fictional local target

Status: Accepted — 2026-07-29

## Decision

Build and test ShiftBridge locally instead of scraping or exercising a live employer marketplace.

## Consequences

The suite controls data, faults, concurrency, schema, and reset behavior without legal, privacy,
availability, or rate-limit risk. Product scope stays intentionally small.

