# Implementation Plan: Dashboard and Reports (009)

**Branch**: `docs/medicore-all-specs` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — **P1 CANDIDATE, NOT APPROVED.** Dashboard and reports
are a P1 Candidate (Master Plan §4.2, §6 M10) scheduled for Phase 7
(Weeks 20–22), after the Phase 6 supporting module is chosen and stable.
This plan describes how the spec *would* be implemented once the owner
approves the spec and answers its Open Questions (OQ-009-1–OQ-009-8).
No implementation work may start before then.

## Summary

Build role-specific dashboards and operational reports (Master Plan §4.2
P1 Candidate, §6 M10, §8 FR-018/FR-019): after sign-in each role sees
counts, their work queue, appointment summaries, pending tasks, and basic
financial/operational metrics where authorised — computed at request time
from the source records of the modules that exist, never from a separate
totals store, so every total reconciles exactly with the records it
summarises. Reports support date (Asia/Karachi day boundaries),
department, and status filters applied identically to lists and totals.
Exports are role-checked, audit-logged, and carry no unnecessary patient
identifiers — never a CNIC / B-Form number.

Technical approach: modular monolith — React + TypeScript + Vite +
Tailwind + shadcn/ui frontend, Django + DRF + PostgreSQL backend,
`reporting` Django app holding only query/aggregation services and the
export audit record (no new business data), REST API under
`/api/dashboard/` and `/api/reports/`, totals computed by aggregate
queries over indexed source tables. Stack is ACCEPTED (ADR-001, owner
approval 2026-11-22); session auth is the decided auth strategy (Spec
001 D-09).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided,
ADR-001; verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19
+ Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing
Library (frontend), Playwright (E2E, one journey: sign in as a role →
dashboard shows own queue → filter a report → export)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Performance Goals**: Common list/detail API operations respond within 2
seconds under a small demo dataset and local test conditions (Master Plan
NFR-05, provisional). Dashboard/report totals MUST be aggregate queries
(`COUNT`, `SUM` with filters) over indexed source tables, not full
record loads into application memory (spec FR-012).

**Constraints**: Synthetic data only; no real patient records; backend
validation is authoritative (frontend validation is usability only); no
separate reporting store or cached totals; no CNIC / B-Form number in any
dashboard, report, or export; no clinical content beyond the viewing
role's authorisation; sections appear only for modules that exist

**Scale/Scope**: Single hospital, single deployment; tens of staff users;
thousands of source records in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a DRAFT candidate; implementation is blocked until the owner approves the spec and answers OQ-009-1–OQ-009-8. No implementation on this plan alone. GATE NOT YET PASSED. |
| II. Modular architecture | `reporting` Django app contains only query/aggregation services + export audit; it owns no business data and duplicates no business rule — figures are computed from the source apps' records. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC + scope (own/department/hospital-wide) backend-enforced per query; least privilege (each role sees only its scope); no CNIC in any output; exports role-checked and audit-logged; synthetic data only. PASS by design. |
| IV. Data integrity | No separate totals store — totals are aggregate queries over source records at request time, so they cannot drift (spec FR-004). PASS by design. |
| V. Test-first | Reconciliation tests (report total vs. direct source count/sum), per-role permission tests, and export-identifier tests are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled filters, explicit empty states, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; each report definition documents its source records, filters, and identifier rules. PASS by design. |
| VIII. Scope discipline | Basic summaries, filters, and protected exports only. No advanced analytics, no separate reporting database, no portal/notifications. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/009-dashboard-reports/
├── spec.md              # Feature specification (DRAFT candidate — not approved)
└── plan.md              # This file
└── tasks.md             # Phase 2 output (NOT created yet — only after spec approval)
```

### Source Code (repository root)

```text
backend/
├── config/              # Django settings (env-based), urls
├── apps/
│   ├── accounts/        # Users, roles, departments, permissions (prerequisite, M01)
│   ├── organization/    # Departments, staff profiles (prerequisite, M02)
│   ├── patients/        # Patient identity (prerequisite, M03 — Spec 001)
│   ├── appointments/    # Appointments (prerequisite, M04)
│   ├── encounters/      # Encounters (prerequisite, M05)
│   ├── billing/         # Invoices/payments (Spec 008 — only if included)
│   ├── laboratory/      # Lab requests/results (only if included)
│   ├── reporting/       # Dashboard + report query services, export audit
│   │   ├── services.py  # Per-role dashboard assembly, report queries, totals
│   │   ├── serializers.py
│   │   ├── views.py     # DRF viewsets, permission- and scope-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── audit/           # Audit events (shared)
└── tests/

frontend/
├── src/
│   ├── components/      # DashboardCard, WorkQueue, ReportFilters, ReportTable
│   ├── pages/           # Dashboard, reports list, report detail/export
│   ├── services/        # API client for /api/dashboard/ and /api/reports/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` +
`docs/`. The `reporting` app is deliberately thin: it reads from the
source apps and owns no business data of its own, so a wrong figure can
only come from a wrong query, never from a stale copy. Dashboard sections
are registered per source module — a section is included only when its
module exists (spec FR-007). Do not create every app in Master Plan
§10.4 at initialisation.

## Data model sketch

No separate `data-model.md` is written for this spec: this feature stores
no new business data, and the sketch below is complete. (OQ-009-1–OQ-009-8
must be answered first where they affect a field: the report list
OQ-009-1, export format OQ-009-2, export storage OQ-009-4.)

### DashboardView (derived, not stored)

Computed at request time from source records. Per role and scope:

| Field | Notes |
|---|---|
| role / scope | Own / department / hospital-wide, from the signed-in user |
| sections | One per existing source module the role may see (appointments, patients, encounters, billing, laboratory); a section is omitted entirely when its module does not exist |
| counts | Integers from aggregate `COUNT` queries with the role's scope filter applied |
| queues | Paginated lists of the underlying records (appointments today, check-in queue, draft encounters, unpaid invoices, duplicate reviews pending), showing only fields the role may see |
| metrics | Sums from aggregate `SUM` queries (money as `Decimal`, 2dp — financial sections only, only where M09 is included) |

Rule: every figure is produced by one query function per section that
takes (role, scope, filters) and returns (list, totals) from the same
filtered queryset — the list and its total can never disagree, because
they come from the same query.

### Report (derived, not stored)

| Field | Notes |
|---|---|
| definition | Which source records, which filters (date range, department, status), which columns — from the approved report list (OQ-009-1) |
| filters | Start/end date (Asia/Karachi days), department, status, page, sort — validated on the backend |
| rows | Paginated, deterministically sorted source records, serialised with only the fields the role may see |
| totals | Aggregate query over the same filtered queryset as the rows |

Rule: the totals query and the rows query share one filtered queryset
builder. A test asserts, for every report, that the reported total equals
a direct count/sum over the source tables with the same filters.

### ReportExport (stored — audit record only)

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | — |
| report | String | Which report definition was exported |
| filters | JSON | The filters applied, as given |
| row_count | Integer | Rows in the export |
| format | String | Export format (OQ-009-2) |
| exported_by | FK → User | Who exported it |
| exported_at | DateTime (UTC) | Displayed in Asia/Karachi |

Rule: the exported file is a snapshot labelled with generation time and
filters. Whether the file itself is stored or only downloaded is
OQ-009-4; either way, no export may contain a CNIC / B-Form number, and
aggregate exports contain no patient identifiers at all.

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `GET /api/dashboard/` | Current user's role dashboard: sections, counts, queues, metrics for their role and scope. Sections for missing modules are absent. |
| `GET /api/reports/` | List of report definitions the caller's role may use. |
| `GET /api/reports/{report}/?start=&end=&department=&status=&page=` | Run a report with filters; returns paginated rows + totals computed from the same filtered queryset. |
| `POST /api/reports/{report}/export/` | Generate an export with the same filters; role-checked, audit-logged (ReportExport row). Returns the file (or a download reference, per OQ-009-4). |

All endpoints require authentication; every query re-checks the caller's
role and scope on the backend; validation errors return structured
field-level errors. Money in responses is serialised as decimal strings,
never as binary floats.

## Security approach

- Django session authentication (decided, ADR-001 / Spec 001 D-09):
  secure HttpOnly cookie, CSRF protection, server-side session
  revocation. No JWT in v1.
- Permission + scope classes per endpoint: each dashboard/report query
  is filtered by the caller's role and scope (own / department /
  hospital-wide) in the queryset itself, so a section cannot leak by
  omitting a filter. Deny by default.
- Identifier minimisation is enforced in serializers, not in the UI:
  the dashboard/report serializers for a role expose only that role's
  permitted fields; CNIC / B-Form is never present in any reporting
  serializer; aggregate serializers expose no patient identifiers at all.
- Exports are generated server-side from the same permission-checked
  queryset as the on-screen report; the export endpoint re-checks the
  role (it does not trust that the user could see the report page).
- Audit events for exports and for access to sensitive reports.
- No patient data in logs, URLs, or error messages beyond what the
  caller's role may see. Export files are generated on demand; if files
  are ever stored (OQ-009-4), storage, access, and retention rules must
  be specified before implementation.
- Rate-limit login; throttle export endpoints against abuse.

## Test strategy

- **Unit**: filter application (date/department/status each narrow the
  queryset correctly, including Asia/Karachi day boundaries); scope
  filtering (own vs. department vs. hospital-wide); serializer field
  allow-lists per role (CNIC never present, aggregates carry no patient
  identifiers).
- **Model/DB**: aggregate queries return correct counts/sums over
  fixtures; indexes on filtered fields (appointment date/status,
  invoice status, department) exist so the NFR-05 target holds.
- **API**: auth required (401 unauthenticated); permission allow/deny
  per role and scope (Doctor requesting hospital-wide finance → 403;
  Department Manager requesting another department → 403 or empty
  scope, per the decided behaviour); filter validation errors (end
  before start → 400 with field errors); pagination and deterministic
  sort.
- **Reconciliation**: for every report and a matrix of filter
  combinations, the reported total equals a direct count/sum over the
  source tables with the same filters — 100% agreement required
  (spec SC-002).
- **Export**: each report exported as each role — allowed only for
  authorised roles, audit event recorded, file contents inspected
  (no CNIC anywhere, no identifier the role may not see, aggregates
  identifier-free).
- **Component**: dashboard cards, empty states, filter controls, export
  button and its confirmation/feedback.
- **E2E (Playwright)**: sign in as Receptionist → dashboard shows own
  queue → open appointments report → filter by today → totals match the
  rows → export succeeds and is audit-logged.
- **Security**: object-level access (changing an ID or a department
  filter cannot widen scope), audit events recorded.

Tests are written first (Constitution Principle V) and must fail before
implementation. No tests are written until the spec is approved — writing
them now would test an undecided report list (OQ-009-1) and export
format (OQ-009-2).

## Risks for this feature

- **Not approved / report list undecided (OQ-009-1)** — the concrete
  reports and per-role metrics are not yet defined, and the feature is
  scheduled for Phase 7, after the Phase 6 module choice. Mitigation:
  this spec fixes the kinds of content and the rules (reconciliation,
  scope, identifiers); the list is decided at approval.
- **Totals drifting from source records** — the core M10 requirement.
  Mitigation: no stored totals; one shared filtered queryset feeds both
  rows and totals; reconciliation tests over a filter matrix.
- **Identifier leakage through exports** — files leave the system.
  Mitigation: serializers enforce field allow-lists per role, exports
  are generated from the permission-checked queryset, and export-content
  tests inspect the actual file bytes.
- **Scope leakage through filters** — a user passing another
  department's id as a filter parameter. Mitigation: scope is applied
  in the queryset from the authenticated user, never taken from a
  request parameter; a filter outside the caller's scope returns
  denied/empty, never the other scope's data.
- **Performance of aggregate queries** — dashboards run several
  aggregates per load. Mitigation: aggregate queries over indexed
  fields, no full-record loads; NFR-05 target checked in tests with
  demo data.
- **Dependency on other modules** — every dashboard section needs its
  source module. Mitigation: sections are registered per module and
  omitted when the module is absent (spec FR-007); this feature is
  Phase 7 precisely so its sources exist first.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
