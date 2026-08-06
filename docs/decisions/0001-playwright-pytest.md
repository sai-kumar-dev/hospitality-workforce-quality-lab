# ADR 0001: Playwright with pytest

Status: Accepted — 2026-07-29

## Context

The portfolio requires UI behavior, API postconditions, cross-browser execution, artifacts, and a
Python-first quality framework.

## Decision

Use Playwright's synchronous Python API through pytest-playwright. Keep domain page objects small
and rely on web-first assertions and plugin-supported trace/screenshot/video retention.

## Consequences

Python fixtures and API helpers compose naturally; Chromium, Firefox, and WebKit share one test
model. Browser binaries add setup time, so only Chromium gates pull requests.

