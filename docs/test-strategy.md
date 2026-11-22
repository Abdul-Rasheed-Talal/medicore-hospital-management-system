# MediCore Test Strategy

**Status**: Draft for approval (part of Master Plan deliverable D-09).
**Date**: 2026-11-22
**Sources**: Master Plan v1.0 §16; Constitution Principle V; Spec 001
(acceptance scenarios, test strategy in plan.md); ADR-001.

Tests are written first and must fail before implementation (Constitution V;
Spec 001 plan). A feature is not complete until its acceptance scenarios
pass and the release quality gate (§7) is met. Existing tests must not be
weakened or removed merely to make an implementation pass.

## 1. Test levels

| Level | What it verifies | Tools | Evidence |
|---|---|---|---|
| Unit | Business rules, validators, status transitions, calculations, utility functions (MRN generation, duplicate rule, Decimal totals) | pytest + Django tests; Vitest | Backend/frontend suites |
| Model / database | Constraints, relationships, migrations, uniqueness, transaction behaviour (register + audit commit together; no partial record) | pytest + Django test DB (PostgreSQL) | DB tests on isolated data |
| API | Authentication (401 unauthenticated), permissions (allow/deny per role), validation errors (400 field-level), status codes, filtering, pagination | pytest + Django test client / DRF APIClient | API test suite |
| Component | Forms, tables, navigation, loading/error/empty states, duplicate-warning dialog, field-level error display | Vitest + React Testing Library | Frontend suite |
| Integration | Frontend/API interaction and multi-module workflows (patient → appointment → encounter; invoice → payment balance update) | Test environment with controlled fixtures | Integration suite |
| End-to-end (E2E) | High-value journeys in a real browser: register patient, schedule appointment, complete encounter, selected P1 flows | Playwright | E2E suite + demo evidence |
| Security | Access denial, object-level access (ID tampering), input abuse, session behaviour, secret handling (no committed secrets, no secrets in logs) | pytest + manual review | Security tests + review checklist |
| Usability review | Task completion, labels, errors, navigation, accessibility basics | Scenario walkthrough with feedback | Walkthrough notes |
| Regression | Fixes and new features do not break approved behaviour | Relevant suite on every meaningful change | CI run per change |

Test database: PostgreSQL (the same engine as production). SQLite is not
an acceptable substitute for model/DB tests — constraint behaviour differs
(ADR-001 rejects SQLite as the primary database).

## 2. Coverage targets

Targets, not guarantees — they are the bar a feature must meet at review.
"Covered" means an automated test exists and passes; manual walkthroughs do
not substitute for the starred items.

| Area | Target |
|---|---|
| Protected endpoints: permission allow/deny tests | 100% of protected endpoints have at least one allow and one deny test |
| Critical business rules (MRN uniqueness, duplicate rule, status transitions, Decimal money, no-overpayment) | 100% of the rules in the approved spec, each with a positive and a negative case |
| Backend validation rules | Every validated field has valid + invalid cases |
| Patient registration acceptance scenarios (Spec 001 SC-001–SC-006) | 100% pass before the feature is considered complete |
| E2E journeys | At least one E2E test per included MVP workflow (register → book → encounter; plus each included P1 workflow) |
| Audit events | Every audited action in the spec has a test proving the event is written (actor, action, target, timestamp, outcome) |
| Overall line coverage | No project-wide line-coverage percentage is set by any source — see OQ-1. The targets above are rule/endpoint-based, not line-based. |

## 3. Test data strategy (Master Plan §16.1)

- **Synthetic data ONLY. Never real patient data** — in development, tests,
  screenshots, or demonstrations (Constitution III, §2.4). Synthetic
  identities must be clearly synthetic (obviously invented names, phone
  numbers in reserved/test ranges where possible, CNIC/B-Form numbers that
  are valid in format but invented).
- Repeatable fixtures for roles, departments, patients, appointments, and
  encounters. Fixtures are seeded by a documented command (see
  `docs/deployment-guide.md`) and reset reproducibly before demonstrations.
- Test data must not be copied from any real hospital register, and demo
  data must not be reused as if it were real.
- National ID values in tests are invented 13-digit numbers; the encryption
  secret in tests is a test-only value from the test environment, never a
  production secret.
- Tests that need a "second hospital" or cross-hospital data do not exist —
  multi-tenancy is out of scope.

## 4. Negative cases (must be tested, not just the happy path)

From Master Plan §16.1 and Spec 001:

- Duplicate identifiers: same name + DOB; same national_id; same phone
  (warning, non-blocking). Zero silent creations or merges.
- Invalid dates: DOB in the future; appointment end before start.
- Invalid formats: phone not 9–15 digits; national_id not 13 digits;
  sex/blood group outside the enums.
- Conflicting appointments (rules per the appointments spec).
- Forbidden role actions: Doctor creating/editing a patient (→ 403);
  Receptionist merging records (→ 403); Billing reading clinical notes
  (→ 403/404); unauthenticated access to every protected endpoint (→ 401).
- Invalid state transitions: finalising an already-finalised encounter;
  paying a voided invoice; overpaying an invoice; recording a payment of
  zero or negative amount; completing an appointment that was cancelled.
- Object-level access: user A fetches user B's forbidden record by changing
  the ID in the URL (→ 403/404); a Doctor fetches a patient outside their
  authorised scope (per the scope rule once decided — see OQ-2).
- Session abuse: expired session, missing CSRF token on a mutation,
  disabled account attempting to sign in.
- Failure safety: database unavailable mid-registration → actionable error,
  no partial record; concurrent duplicate submissions → one record only.
- Input abuse: oversized inputs, unexpected fields (ignored, never trusted
  — e.g. a client-supplied MRN is ignored), script content in text fields
  (stored safely, rendered escaped).

## 5. E2E journeys (Playwright)

Minimum set for the MVP (one per included workflow):

1. **Register → find**: search → no match → register → MRN issued → search
   by MRN finds the patient (Spec 001 plan).
2. **Register → book**: journey 1, then book an appointment → appointment
   appears in the schedule.
3. **Arrival → encounter**: check in → doctor's queue → start encounter →
   draft → finalise.
4. **Lab** [P1, if included]: request from encounter → lab queue → result
   entry → finalised → clinician review.
5. **Billing** [P1, if included]: invoice from services → record payment →
   balance/status update → receipt reference.
6. **Admin**: create user → assign role → sign in as that user → only
   permitted functions visible; disable account → access revoked.

E2E runs against a seeded synthetic dataset in a test environment, never
against a shared demo database that other work depends on.

## 6. Security testing

- Every protected endpoint has automated allow/deny tests (see §2).
- Object-level access tested with multiple users and roles.
- No committed secrets: CI checks for secrets in the diff (exact tool not
  decided — see OQ-3); `.env` files, credentials, real patient data, local
  databases, and generated dependencies are never committed (Master Plan
  §15.2).
- Input validation, output encoding, and safe file handling reviewed.
- Dependencies kept reasonably current; known critical vulnerabilities
  addressed.
- Debug mode and detailed error traces disabled in hosted/demo environments;
  error responses contain no stack traces.
- Login throttling verified (repeated failed logins are throttled).

## 7. Release quality gate (Master Plan §16.3)

All of the following must hold before a release/demo is accepted:

1. All P0 acceptance scenarios pass.
2. No open critical security, privacy, or data-integrity defects. (Defect
   severity: Critical = data disclosure, privilege escalation, data
   corruption/loss, or core workflow unusable — must be fixed before
   release/demo acceptance; High = important workflow fails or creates
   materially incorrect records — fixed or explicitly accepted with
   supervisor/owner sign-off; Medium/Low — prioritised or documented.)
3. Backend permission tests pass for each protected feature.
4. Database migrations apply cleanly from a fresh setup.
5. The documented setup and demo procedure works on a clean environment.
6. Backup/restore procedure is demonstrated for the chosen database
   environment.
7. Known limitations and deferred features are documented.

## 8. CI and workflow

- Tests run on every meaningful change (Constitution V); the relevant suite
  runs after any change to the code it covers.
- Keep the main branch in a known working state; feature branches for
  substantial features; pull requests as a review checkpoint even for a
  solo project (Master Plan §15.2).
- A failing test blocks the merge of the feature that broke it. A test is
  fixed by fixing the code or the (wrong) test expectation with a recorded
  reason — never by deleting or weakening the test to make it pass.
- Test evidence (suite results, E2E evidence, defect records) is kept as
  part of the deliverable (Master Plan D-09).

## Open Questions

- **OQ-1 — Line-coverage target.** No source sets a line-coverage
  percentage. Whether to adopt one (e.g. 80% on backend services) is
  undecided; this strategy deliberately uses rule/endpoint targets instead.
- **OQ-2 — Doctor patient-scope rule.** Object-level tests for Doctor
  patient access depend on the undecided scope rule (all patients vs
  authorised care relationships only) — see api-contract.md OQ-8.
- **OQ-3 — Secret scanning tool.** Which tool enforces "no committed
  secrets" in CI (e.g. gitleaks, trufflehog, or a GitHub-native check) is
  not decided.
- **OQ-4 — Performance testing.** NFR-05's 2-second target is provisional
  ("under a small demo dataset and local test conditions"). Whether any
  automated performance/load test is run, and with what dataset size, is
  not decided.
- **OQ-5 — Accessibility testing.** Whether automated accessibility checks
  (e.g. axe) run in CI, or accessibility is verified by manual walkthrough
  only, is not decided.
