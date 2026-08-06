# Test strategy

## Scope and objectives

The strategy protects ShiftBridge authentication, role boundaries, job discovery, employer job
ownership, application uniqueness, failure behavior, and operability. It also tests the QA
framework itself because faulty configuration, data, parsing, or diagnostics can invalidate
product evidence.

Out of scope: real third-party services, email, payments, admin functions, destructive security
testing, formal capacity certification, and production data.

## Principal quality risks

| Risk | Impact | Primary controls |
|---|---|---|
| Cross-role or cross-employer data disclosure | Critical | service, API, E2E authorization tests |
| Duplicate applications under concurrency | High | DB unique constraint, service translation, concurrent API test |
| Authentication ambiguity or secret leakage | High | neutral errors, response/log/artifact redaction tests |
| Search/paging defects hide suitable jobs | Medium | business-rule, API property, and UI filter checks |
| Client failure state crashes or resubmits | High | deterministic Playwright interception |
| Framework flakiness obscures real failures | High | unique identities, web-first waits, no retries/order coupling |
| Unhealthy dependency accepted as ready | High | bounded database readiness and Compose health dependencies |
| Undiagnosable CI failure | Medium | trace/video/screenshot/JUnit/logs plus rule-based triage |

## Levels and pyramid

1. Pure unit tests validate parsing, factories, configuration, redaction, normalization, and rules.
2. Backend service tests validate business decisions without browser cost.
3. API tests validate HTTP contracts, authentication, authorization, persistence, and concurrency.
4. Schemathesis/Hypothesis explore generated types and boundaries with bounded PR profiles.
5. Focused UI smoke validates accessible user behavior.
6. E2E verifies cross-layer postconditions through both API and UI.
7. Scheduled cross-browser, reliability, accessibility, security, and performance suites broaden risk
   coverage without delaying every change.

## Entry criteria

- Locked dependencies resolve.
- Database migration succeeds.
- Seed CLI accepts only a safe environment.
- `/health/live`, `/health/ready`, and web health return success.
- Each test run has a run ID, writable artifact root, and explicit non-production base URLs.

## Exit criteria

- Mandatory unit, type, lint, format, frontend-build, API, bounded contract, and Chromium smoke gates pass.
- Backend coverage is at least 85% line / 80% branch.
- QA framework coverage is at least 90% line / 85% branch.
- No S1/S2 open defect affects the changed scope.
- No unexplained 500, authorization leak, raw integrity error, or sensitive artifact is observed.
- Reports and teardown complete even when a test fails.

## Browser and viewport policy

Chromium is the pull-request gate. Chromium, Firefox, and WebKit smoke run on `main`, schedule, and
manual dispatch. Desktop uses 1440×900; mobile uses a representative 390×844 viewport. Selected
tests assert navigation, forms, overflow, and primary actions—not pixel identity.

## Environment policy

Allowed QA environments are `local`, `test`, and `ci`. Both app and API base URLs are mandatory;
the settings object rejects unknown environments, non-HTTP URLs, and production-like hosts in safe
test modes. Tests never silently target production.

## Test data and isolation

Factories use stable per-run seeds plus UUID fragments and xdist worker IDs. Emails and job titles
are unique. API setup is preferred for UI tests because it is faster and narrows failure scope.
Cleanup uses owned namespaces or deterministic disposable Compose volumes. Tests cannot depend on
execution order or mutable session-scoped identities.

Authentication state, if used, is created during the run beneath ignored `artifacts/`; it is never
committed. A small number of database-reset/seed checks are marked `serial` because destructive
namespace operations cannot safely share a database; the rest remain parallel-safe.

## Locator and waiting policy

Use role, label, placeholder, unique visible text, test ID, justified CSS, then exceptional XPath.
Arbitrary sleeps, fixed waits, blanket retries, element handles, and globally inflated timeouts are
prohibited. Use Playwright auto-waiting, web-first assertions, and meaningful UI/network state with
bounded limits.

## Accessibility

Keyboard behavior and semantics are asserted directly. The local official axe-core package scans
login, jobs, detail, and create-job pages. Serious and critical impacts block CI; moderate/minor
findings are recorded for review. Automated checks do not replace manual screen-reader evaluation.

## Flaky-test policy

A failure is not automatically flaky. Pull-request gates have no retries. Diagnostic scheduled
experiments may retry only while preserving the original failure. Quarantine requires owner,
reason, issue, and expiration; it remains visible in reporting. Root cause is Product, Test,
Environment, Data, or Unknown.

## Defect severity

- **S1 Critical:** credential/data exposure, destructive corruption, or all core flows unavailable.
- **S2 High:** role bypass, duplicate persistence, or a primary journey blocked without workaround.
- **S3 Medium:** partial functional/reliability/accessibility defect with workaround.
- **S4 Low:** low-impact presentation, documentation, or diagnostic issue.

## Reporting and diagnostics

CI produces JUnit, pytest HTML, line/branch coverage, traces, screenshots, selected video, console
and HTTP failures, Schemathesis results, Locust CSV/HTML, and Compose logs. Artifacts are
run/browser/test namespaced and secret-redacted. Triage normalizes volatile values, groups similar
failures, and provides transparent probable-layer rules without replacing the original exception.

## Performance thresholds

The initial smoke gates are aggregate failure rate <1%, jobs-list p95 <750 ms, and health p95
<250 ms. The parser fails only on documented thresholds. CI results are regression signals from a
noisy shared runner; they are not formal capacity results.

