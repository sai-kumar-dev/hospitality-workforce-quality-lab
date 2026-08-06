# ADR 0002: API-based UI test setup

Status: Accepted — 2026-07-29

## Decision

Create prerequisites through typed API domain methods, then exercise only the user behavior under
test in the browser and verify important postconditions through the API.

## Consequences

Tests are faster and failures localize cleanly. Separate E2E journeys still cover complete UI
setup where cross-layer integration is the purpose.

