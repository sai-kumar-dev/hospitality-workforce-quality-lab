# Automated test traceability

Every mandatory scenario maps to executable code. “Seeded stack” means Compose is healthy and the
development-only idempotent seed has run. API/UI suites use unique run/worker data unless the
precondition explicitly names immutable demo data.

## Framework and backend rules

| Test ID | Feature | Risk | Layer | Preconditions | Steps | Expected result | Automated test location | Marker | Priority |
|---|---|---|---|---|---|---|---|---|---|
| QAF-001 | Config | Wrong target | Unit | Env mapping | Load valid explicit URLs | Typed settings load | `qa/tests/unit/test_config.py` | unit | P0 |
| QAF-002 | Config | Silent production target | Unit | API URL missing | Load settings | Useful validation error | `qa/tests/unit/test_config.py` | unit | P0 |
| QAF-003 | Config | Unsafe environment | Unit | `TEST_ENV=production` | Load settings | Environment rejected | `qa/tests/unit/test_config.py` | unit | P0 |
| QAF-004 | Candidate factory | Invalid setup data | Unit | Fixed seed | Build default | Valid candidate payload | `qa/tests/unit/test_factories.py` | unit | P1 |
| QAF-005 | Factories | Override ignored | Unit | Fixed seed | Override every domain factory | Overrides preserved | `qa/tests/unit/test_factories.py` | unit | P1 |
| QAF-006 | Candidate factory | Parallel collision | Unit | Worker/run ID | Generate multiple emails | All emails unique | `qa/tests/unit/test_factories.py` | unit | P0 |
| QAF-007 | Problem parser | Unhelpful API failures | Unit | Valid problem JSON | Parse response | Typed fields preserved | `qa/tests/unit/test_problem_details.py` | unit | P1 |
| QAF-008 | Problem parser | Parser hides malformed response | Unit | Invalid JSON/body | Parse response | Safe fallback with status | `qa/tests/unit/test_problem_details.py` | unit | P1 |
| QAF-009 | Redaction | Secret artifact leakage | Unit | Token/password/cookie text | Redact recursively | Secrets absent | `qa/tests/unit/test_redaction.py` | unit | P0 |
| QAF-010 | Signatures | Duplicate incidents ungrouped | Unit | Equivalent volatile errors | Normalize | Signatures match | `qa/tests/unit/test_signatures.py` | unit | P1 |
| QAF-011 | Triage grouping | Noisy diagnosis | Unit | Equivalent JUnit failures | Triage | One group with members | `qa/tests/unit/test_triage.py` | unit | P1 |
| QAF-012 | Performance gates | False green load run | Unit | Boundary CSV metrics | Evaluate thresholds | Exact pass/fail decision | `qa/tests/unit/test_performance_thresholds.py` | unit | P1 |
| BE-001 | Passwords | Auth bypass | Unit/service | Hashed password | Verify correct/incorrect input | Only correct password passes | `apps/api/tests/test_core.py` | unit | P0 |
| BE-002 | Roles | Function-level bypass | Unit/service | Candidate/employer users | Enforce required role | Wrong role gets 403 | `apps/api/tests/test_core.py` | unit | P0 |
| BE-003 | Filters | Search mismatch | Unit/service | Mixed whitespace/case | Normalize filter | Stable trimmed form | `apps/api/tests/test_core.py` | unit | P1 |
| BE-004 | Applications | Raw integrity exception | Unit/service | Existing pair | Submit duplicate | Domain conflict, rollback | `apps/api/tests/test_core.py` | unit | P0 |
| BE-005 | Pagination | Missing/duplicate rows | Unit/service | Boundary inputs | Normalize page/page size | Safe bounds | `apps/api/tests/test_core.py` | unit | P1 |
| BE-006 | Inactive jobs | Invalid application | Unit/service | Inactive job | Apply | Domain rejection | `apps/api/tests/test_core.py` | unit | P0 |
| BE-007 | Ownership | Applicant disclosure | Unit/service | Employer B, employer A job | Check ownership | Access denied | `apps/api/tests/test_core.py` | unit | P0 |
| BE-008 | Problem details | Internal leakage | Unit/service | Domain error/request ID | Build response | Stable safe shape | `apps/api/tests/test_core.py` | unit | P0 |

## HTTP API

| Test ID | Feature | Risk | Layer | Preconditions | Steps | Expected result | Automated test location | Marker | Priority |
|---|---|---|---|---|---|---|---|---|---|
| API-001 | Liveness | Dead process accepted | API | Running API | `GET /health/live` | 200 alive | `qa/tests/api/test_api_contract_cases.py` | api, smoke | P0 |
| API-002 | Readiness | DB outage accepted | API | Healthy DB | `GET /health/ready` | 200 ready | same | api, smoke | P0 |
| API-003 | Registration | Candidate cannot join | API | Unique factory candidate | Register | 201 candidate, session set | same | api | P0 |
| API-004 | Registration | Duplicate identity | API | Registered email | Register again | 409 stable problem | same | api | P0 |
| API-005 | Login | Valid auth broken | API | Demo candidate | Login | 200 and HttpOnly cookie | same | api, smoke | P0 |
| API-006 | Login privacy | Account enumeration | API | Invalid credential variants | Login | Same neutral 401 detail | same | api, security | P0 |
| API-007 | Protected access | Auth bypass | API | No session | Read applications | 401 problem | same | api, security | P0 |
| API-008 | Job creation | Employer journey broken | API | Employer session | Create valid job | 201 owned job | same | api | P0 |
| API-009 | Role authorization | Candidate creates job | API | Candidate session | Create valid job | 403, no job | same | api, security | P0 |
| API-010 | Validation | Unactionable errors | API | Employer session | Omit required fields | 422 field errors | same | api | P0 |
| API-011 | Keyword search | Irrelevant results | API | Seeded jobs | Search keyword | Only matches returned | same | api | P1 |
| API-012 | Location search | Wrong geography | API | Three+ locations | Filter location | Only location matches | same | api | P1 |
| API-013 | Pagination | Unsafe boundaries | API | Seeded jobs | Query zero/huge/beyond | Documented 422/empty behavior | same | api | P1 |
| API-014 | Application | Candidate cannot apply | API | Candidate + active job | Submit note | 201 submitted record | same | api | P0 |
| API-015 | Application uniqueness | Duplicate record | API | Existing pair | Submit again | 409 deterministic conflict | same | api, security | P0 |
| API-016 | Candidate history | Missing own data | API | Candidate application | List mine | Own application returned | same | api | P0 |
| API-017 | Applicant list | Employer cannot hire | API | Employer-owned job/app | List applicants | Candidate summary returned | same | api | P0 |
| API-018 | Object authorization | Cross-employer disclosure | API | Employer B, A job | List applicants | 403; no protected data | same | api, security | P0 |
| API-019 | Function authorization | Candidate sees applicants | API | Candidate session | List applicants | 403 | same | api, security | P0 |
| API-020 | Not found | Inconsistent unknown resource | API | Auth as needed | Request missing job | 404 consistent problem | same | api | P1 |
| API-021 | Invalid IDs | Unhandled parser error | API | Running API | Request malformed/invalid IDs | 4xx, never 500 | same | api, security | P0 |
| API-022 | Extra fields | Mass assignment | API | Candidate/employer payload | Add unknown/role fields | Contracted reject/ignore; no escalation | same | api, security | P0 |
| API-023 | Request correlation | Failure not diagnosable | API | Invalid request | Inspect problem/header | Non-empty matching request ID | same | api | P0 |
| API-024 | Data exposure | Password/hash/token leak | API | Auth and list responses | Recursively inspect JSON | Sensitive keys/values absent | same | api, security | P0 |
| API-025 | Concurrency | Race creates duplicates | API | New candidate/job | Submit two requests concurrently | Exactly one 201, one 409, one record | same | api, reliability | P0 |

## Contract, property, UI, and journeys

| Test ID | Feature | Risk | Layer | Preconditions | Steps | Expected result | Automated test location | Marker | Priority |
|---|---|---|---|---|---|---|---|---|---|
| CON-001 | OpenAPI response schema | Drift | Contract | Healthy API | Generate bounded operations | Responses validate | `qa/tests/contract/test_openapi_contract.py` | contract | P0 |
| CON-002 | Status documentation | Hidden behavior | Contract | OpenAPI loaded | Compare generated responses | Status is documented | same | contract | P1 |
| CON-003 | Malformed generated requests | Unhandled input | Contract | CI profile | Generate invalid bodies | No unhandled 500 | same | contract | P0 |
| CON-004 | Auth schema | Misleading clients | Contract | OpenAPI loaded | Inspect protected operations | Cookie security represented | same | contract | P1 |
| CON-005 | Type/boundary generation | Weak schema | Contract | CI/deep profile | Exercise common boundaries | Contracted 2xx/4xx only | same | contract | P1 |
| CON-006 | Business properties | Boundary defects | Property | Hypothesis cache | Generate titles/pages/filters/data | Invariants hold | `qa/tests/contract/test_properties.py` | contract | P1 |
| UI-001 | Home | Broken entry | UI | Seeded stack | Open `/` | Expected H1 visible | `qa/tests/ui/test_smoke.py` | ui, smoke | P0 |
| UI-002 | Registration | Join journey | UI | Unique candidate | Complete form | Signed-in success | same | ui, smoke | P0 |
| UI-003 | Login | Auth journey | UI | Demo candidate | Login | Candidate state visible | same | ui, smoke | P0 |
| UI-004 | Login error | Inaccessible failure | UI | Invalid password | Submit | Associated live error | same | ui, smoke | P0 |
| UI-005 | Jobs | Discovery empty | UI | Seeded stack | Open jobs | Seeded cards visible | same | ui, smoke | P0 |
| UI-006 | Job filters | Wrong discovery | UI | Seeded jobs | Filter location/keyword | Matching cards only | same | ui, smoke | P1 |
| UI-007 | Job detail | Broken navigation | UI | Seeded jobs | Open a card | Correct job heading/details | same | ui, smoke | P0 |
| UI-008 | Apply | Submission blocked | UI | Candidate + new job | Submit note | Success visible | same | ui, smoke | P0 |
| UI-009 | Duplicate apply | Confusing conflict | UI | Existing pair | Apply again | Clear duplicate message | same | ui, smoke | P0 |
| UI-010 | Candidate dashboard | Missing history | UI | New application | Open dashboard | Application visible | same | ui, smoke | P0 |
| UI-011 | Employer create | Hiring blocked | UI | Employer session | Complete job form | New job visible | same | ui, smoke | P0 |
| UI-012 | Employer applicants | Applicant hidden | UI | Owned job + app | Open applicants | Candidate visible | same | ui, smoke | P0 |
| UI-013 | Logout | Session remains | UI | Signed in | Log out | Unauthenticated nav/login | same | ui, smoke | P0 |
| UI-014 | Not found | Client crash | UI | Running web | Open unknown route | Accessible not-found page | same | ui, smoke | P1 |
| E2E-001 | Candidate journey | Cross-layer break | E2E | Healthy clean namespace | UI register/filter/apply; API/dashboard verify | One persisted application | `qa/tests/e2e/test_journeys.py` | e2e | P0 |
| E2E-002 | Employer journey | Cross-layer break | E2E | Employer + unique data | UI create; API/public verify; API apply; UI verify | Applicant appears | same | e2e | P0 |
| E2E-003 | Authorization journey | Protected render/data | E2E | Employer A data, B session | Attempt API and UI access | Denied; no protected data | same | e2e, security | P0 |

## Reliability, responsive, accessibility, and security

| Test ID | Feature | Risk | Layer | Preconditions | Steps | Expected result | Automated test location | Marker | Priority |
|---|---|---|---|---|---|---|---|---|---|
| REL-001 | Jobs 500 | UI crash/leak | UI reliability | Intercept jobs | Fulfill 500 | Safe retryable error | `qa/tests/reliability/test_failure_injection.py` | reliability | P0 |
| REL-002 | Delayed jobs | Missing loading feedback | UI reliability | Gated intercepted response | Open jobs before release | Loading state visible | same | reliability | P1 |
| REL-003 | Aborted request | Client crash | UI reliability | Abort route | Open jobs | Safe network state | same | reliability | P0 |
| REL-004 | Apply timeout | Accidental repeat | UI reliability | Delay submission | Submit once | Busy state prevents second submit | same | reliability | P0 |
| REL-005 | Double click | Duplicate application | UI reliability | Candidate/new job | Double-click Apply | One server record | same | reliability | P0 |
| REL-006 | Authenticated refresh | Lost session | UI reliability | Candidate signed in | Reload protected page | Predictable authenticated state | same | reliability | P1 |
| REL-007 | Expired auth | Stale protected UI | UI reliability | Invalid/expired cookie | Visit protected page | Redirect/session message | same | reliability | P0 |
| REL-008 | Hostile error text | Script injection | UI reliability | Intercept HTML-like detail | Trigger error | Text escaped, no injected node | same | reliability, security | P0 |
| RWD-001 | Desktop | Hidden navigation/action | Responsive UI | 1440×900 | Run selected smoke | Nav/forms/actions usable, no overflow | `qa/tests/ui/test_responsive.py` | ui | P1 |
| RWD-002 | Mobile | Hidden navigation/action | Responsive UI | 390×844 | Run selected smoke | Nav/forms/actions usable, no overflow | same | ui | P1 |
| A11Y-001 | Keyboard login | Mouse-only auth | Accessibility | Login page | Tab/type/submit | Flow completes by keyboard | `qa/tests/accessibility/test_accessibility.py` | accessibility | P0 |
| A11Y-002 | Form labels/errors | Unannounced failure | Accessibility | Invalid forms | Inspect associations/live region | Labels and errors associated | same | accessibility | P0 |
| A11Y-003 | Heading hierarchy | Disorientation | Accessibility | Key pages | Inspect headings | Sensible single-page hierarchy | same | accessibility | P1 |
| A11Y-004 | Accessible names | Unusable controls | Accessibility | Key pages | Inspect buttons/links | Meaningful names | same | accessibility | P0 |
| A11Y-005 | Axe login/jobs | Serious violation | Accessibility | Healthy pages | Run local axe | No serious/critical findings | same | accessibility | P0 |
| A11Y-006 | Axe detail/create | Serious violation | Accessibility | Auth where needed | Run local axe | No serious/critical findings | same | accessibility | P0 |
| SEC-001 | CORS | Cross-origin credential misuse | Integration | Running API | Preflight allowed/disallowed origins | Exact allowlist only | `qa/tests/integration/test_security_boundaries.py` | integration | P0 |
| SEC-002 | Oversized/unsafe text | Resource/injection issue | Integration | Auth sessions | Submit boundaries/content | Contracted 4xx or escaped text | same | integration, security | P0 |
| SEC-003 | Seed safety | Destructive production reset | Integration | Production settings | Invoke seed/reset | Operation rejected | `apps/api/tests/test_core.py` | unit, security | P0 |

## Performance and diagnostics

| Test ID | Feature | Risk | Layer | Preconditions | Steps | Expected result | Automated test location | Marker | Priority |
|---|---|---|---|---|---|---|---|---|---|
| PERF-001 | Candidate browsing | Discovery slowdown | Performance | Healthy seeded stack | List, filter, open jobs | Requests recorded; thresholds evaluated | `qa/performance/locustfile.py` | performance | P1 |
| PERF-002 | Application behavior | Write regression | Performance | Prepared/unique candidates | Auth, open, submit | Stable low-error behavior | same | performance | P1 |
| DIA-001 | Failure artifact hook | Missing evidence | Framework/integration | Failing browser case | Finish test | Metadata retained without masking failure | `qa/tests/unit/test_triage.py` | unit | P1 |
| DIA-002 | Triage outputs | Manual-only diagnosis | Framework/integration | JUnit/console/HTTP fixtures | Run CLI | JSON and Markdown with grouping/layer/action/confidence | same | unit | P1 |

The API authorization and validation rows also satisfy the OWASP-inspired object authorization,
function authorization, authentication, excessive exposure, mass-assignment, invalid-ID,
oversized-input, unsafe-content, duplicate-action, CORS, and safe-environment requirements.
