# Security policy

## Scope

This repository is a fictional, local-only demonstration application. Do not aim its tests,
Locust users, or security checks at a real employer, candidate, hospitality company, or public
service.

## Supported version

Only the current `main` branch is maintained. There are no production deployments or customer
data.

## Reporting a vulnerability

Report suspected vulnerabilities privately to the repository owner instead of opening a public
issue. Include the affected commit, local reproduction steps, impact, and sanitized evidence.
Never include live credentials, tokens, full cookies, personal data, or destructive payloads.

## Local security controls

- Passwords are Argon2-hashed.
- Authentication uses a short-lived HttpOnly cookie and server-side role checks.
- CORS accepts only configured origins.
- Problem details hide stack traces and persistence details.
- Seed/reset commands reject production environments.
- Logs and triage outputs redact credential-like values.
- Containers run without root where practical.

## Reviewed dependency advisory

The current React Router release reports `GHSA-qwww-vcr4-c8h2`, which applies to React Server
Components/server-action mode. ShiftBridge is a client-rendered Vite `BrowserRouter` application
and ships no React Router server runtime or server actions, so that execution path is absent.
`scripts/check_npm_audit.py` permits only that exact advisory and still fails on every other high or
critical npm finding. Remove the exception as soon as an unaffected stable React Router release is
available.

The included authorization, input-boundary, mass-assignment, dependency-audit, and CodeQL checks
are defensive regression tests. They are not a penetration-testing product or permission to test
external systems.
