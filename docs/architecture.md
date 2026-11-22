# MediCore Architecture Plan

**Status**: Draft for owner/supervisor approval (Master Plan Gate B — Architecture).
**Date**: 2026-11-22
**Sources**: Master Plan v1.0 §§4, 6, 9, 10, 11, 12, 14, 17; Constitution v1.0.0
Principles I–VIII; ADR-001 (ACCEPTED 2026-11-22); Spec 001 Patient Registration
(approved 2026-11-22, decisions D-01–D-13).

This document is the approved-architecture-plan candidate (Master Plan
deliverable D-04). It confirms the stack already accepted in ADR-001 and fixes
module boundaries, the API approach, the security model, core data flows, and
the deployment shape. Anything it does not decide is listed under
§9 "Not decided / deferred" — it is not decided by silence.

## 1. Decisions already binding (do not re-decide here)

| Decision | Source |
|---|---|
| Modular monolith in a monorepo (`frontend/` + `backend/` + `docs/`); no microservices | ADR-001; Master Plan §10.3 |
| Frontend React + TypeScript + Vite; Tailwind CSS + shadcn/ui | ADR-001 (ACCEPTED) |
| Backend Python 3.12 + Django 5.x + Django REST Framework | ADR-001 (ACCEPTED) |
| Database PostgreSQL 16 (Constitution Principle IV *requires* PostgreSQL) | ADR-001; Constitution IV |
| Django session authentication (secure HttpOnly cookie, CSRF protection); **no JWT in v1** | ADR-001; Spec 001 D-09 |
| Timestamps stored in UTC, displayed in **Asia/Karachi** | ADR-001; Spec 001 |
| Node 20 LTS; TypeScript 5.x | ADR-001; Spec 001 plan |
| MRN format `MC-YYYY-NNNNNN`, server-generated, yearly sequence reset | Spec 001 D-01 |
| CNIC / B-Form (`national_id`): required, 13 digits, encrypted at rest, uniqueness via deterministic hash, full view only Receptionist/Admin, masked (last 4 digits) otherwise, never searchable, never in logs/list views/URLs | Spec 001 D-06/D-07/D-12 |
| Decimal-safe money (never floating-point for invoice totals) | Master Plan §9.1 |
| No hard delete of patient records or clinical/financial history; status change / correction / archival instead | Spec 001 D-05/D-09; Master Plan §9.1 |
| Spec-driven development: no feature is implemented without an approved spec | Constitution I, §3 |

## 2. System shape

One deployment instance serving one hospital organisation (Master Plan §2.4).
Staff use modern desktop browsers (primary); the UI must remain usable on
smaller screens. There is no native mobile app, no patient portal, and no
external integration in v1 (Master Plan §4.3).

```text
                    +------------------ Staff browser ------------------+
                    |  React + TypeScript + Vite + Tailwind + shadcn/ui |
                    |  role-aware navigation, forms, validation (UX only)|
                    +---------------+----------------------------------+
                                    | HTTPS, session cookie + CSRF token
                                    | REST /api/  (JSON)
                    +---------------v----------------------------------+
                    |  Django + Django REST Framework (modular monolith)|
                    |  API boundary -> services (business rules)        |
                    |  -> Django ORM -> PostgreSQL 16                   |
                    |  Cross-cutting: audit, auth/RBAC, logging, config |
                    +----------------------------------------------------+
```

### 2.1 Logical layers

| Layer | Responsibility | Must NOT contain |
|---|---|---|
| Browser / UI | Pages, reusable components, forms, role-aware navigation, validation feedback, loading/empty/error states | Business rules, permission decisions (UI hiding is display only) |
| API boundary | DRF viewsets/serializers, request validation, auth + permission checks, response shapes, pagination/filtering | Multi-step business rules, calculations |
| Application / domain (services) | Use cases, workflow transitions, calculations, transaction orchestration, duplicate checks, MRN generation | HTTP concerns, SQL strings |
| Persistence | Django ORM models, migrations, PostgreSQL constraints and indexes | Business rules that belong in services (except DB-enforced uniqueness) |
| Cross-cutting | Audit logging, error handling, environment config, structured logging | Feature logic |

Rules: backend validation is authoritative; frontend validation is usability
only (Master Plan §9.1). Business rules live in exactly one place — services,
not duplicated across views/serializers or between frontend and backend
(Constitution II, VIII; Master Plan §9.1).

## 3. Module boundaries (Django apps)

Apps are created **only when their scope is approved** (Master Plan §10.4;
Spec 001 plan). Do not create every app at initialisation. The table below is
the full boundary map so later specs slot into it; the "Status" column is the
current approval state.

| App | Responsibility | Depends on | Status |
|---|---|---|---|
| `accounts` | Users, roles/permissions, session auth support, account lifecycle (create/activate/disable/reset), staff login identity | `audit` (security events) | P0 — prerequisite (M01). Must land before/with Spec 001 |
| `organization` | Departments, staff profiles, service/reference catalogues (visit types, service categories, chargeable services) | `accounts` | P0 — minimal setup (M02) |
| `patients` | Patient identity, demographics, search, duplicate review, correction history, status, patient summary | `accounts`, `audit` | P0 — Spec 001 approved (M03) |
| `appointments` | Schedules/slots, appointment create/reschedule/cancel, status transitions, conflict rules, daily schedules | `patients`, `organization`, `audit` | P0 — spec not yet written (M04) |
| `encounters` | Visit/encounter records, notes, diagnoses, draft → finalised lifecycle, corrections | `patients`, `appointments`, `organization`, `audit` | P0 — spec not yet written (M05) |
| `prescriptions` | Medication order records linked to encounters, draft/finalised/cancelled states | `encounters`, `audit` | **P1 candidate** (M06) — include only if workflow and safe demo scope are clear |
| `laboratory` | Test catalogue, lab requests, specimen/status workflow, results, approval | `patients`, `encounters`, `audit` | **P1 candidate** (M08) — may be deferred if time is tight |
| `billing` | Invoices, invoice lines, payments, receipts, balances, void/refund (audited) | `patients`, `encounters`, `organization`, `audit` | **P1 candidate** (M09) — financial rules need discovery |
| `audit` | Audit events (actor, action, target, timestamp, outcome, limited non-sensitive metadata) | `accounts` (actor) | P0 — shared, lands with M01 |
| `reporting` | Role-specific dashboards and report queries (read-only aggregations over the other apps) | all read sources | **P1 candidate** (M10) — basic dashboard for MVP, advanced analytics later |

Dependency rules:

- No app imports another app's views/serializers; cross-app reads go through
  the owning app's models/services.
- `patients` never depends on `appointments`, `encounters`, `laboratory`, or
  `billing` — patient identity is the foundation, not a consumer of later
  workflows. Later apps depend on `patients`.
- `audit` is append-only and depends on nothing except the actor identity;
  no feature app writes audit rows directly — it calls the audit service.
- `reporting` is read-only: it never writes business records and never
  bypasses permission checks.
- Out of scope in v1 (P2 / future, Master Plan §4.2): nursing observations
  (M07), inpatient/bed management (M11), pharmacy/inventory (M12),
  notifications/patient portal (M13). No app is created for these.

### 3.1 Frontend module boundaries (mirrors the backend)

`frontend/src/` is organised by feature area, mirroring the backend apps:
`features/auth/`, `features/patients/`, `features/appointments/`,
`features/encounters/`, `features/lab/`, `features/billing/`,
`features/admin/`, `features/reports/`, plus shared `components/`,
`services/` (API client), `lib/` (auth/session helpers). Feature areas are
added only when their backend scope is approved. Shared UI primitives come
from shadcn/ui; no feature duplicates a shared component.

## 4. API approach

Full contract: `docs/api-contract.md`. Summary of the approach:

- Resource-oriented REST under `/api/`, JSON throughout, consistent HTTP
  semantics and structured validation errors (Master Plan §14.1).
- Django session auth for the browser app; every protected endpoint requires
  authentication; CSRF protection on state-changing requests; no JWT in v1.
- Permission checks run **before** object details are returned or mutations
  are performed; deny by default; object-level checks on every lookup
  (a user cannot reach another role's forbidden record by changing an ID).
- List endpoints are paginated, with only approved filters and sort fields
  (Master Plan FR-024).
- Serializers are the single source of response/request shapes; the API
  contract document is kept consistent with implementation (Constitution VII).
- No API versioning prefix in v1 — see Open Question OQ-1 (§9).
- No external integrations in v1 (Master Plan §14.3).

## 5. Security model

### 5.1 Authentication

- Django session authentication: server-side sessions, secure HttpOnly
  cookie, CSRF protection, logout destroys the server-side session.
  Accounts can be disabled server-side, which revokes access immediately
  (the property JWT would have to be hand-built to match — Spec 001 D-09).
- Passwords hashed with Django's framework mechanism; never plaintext
  (Constitution III; Master Plan §12.1).
- Login is throttled/rate-limited against brute force (Spec 001 plan).
- Password reset / account recovery is optional and subject to email
  configuration (Master Plan M01) — not assumed to exist in v1.

### 5.2 Authorisation (RBAC)

- Named roles mapped to explicit permissions; avoid hard-coded role-name
  checks scattered through the application (Master Plan §5.1). Permissions
  are checked by DRF permission classes backed by role→permission mappings.
- Roles (Master Plan §5, starting point; exact duties to be confirmed in
  discovery): Admin, Receptionist, Doctor, Nurse, Lab Technician,
  Pharmacist, Billing, Department Manager, Auditor/Supervisor.
- Least privilege, deny by default. A user cannot grant themselves
  privileges or bypass approval workflows (Master Plan §5.1).
- Object-level scope, not only "is authenticated": e.g. a Doctor sees
  patients/encounters within their authorised care relationships; Billing
  sees billing data, not clinical notes (Master Plan §5).
- Spec 001's binding patient permissions (v1): Receptionist/Admin may
  search, register, correct; Doctor is read-only for patient demographics;
  Nurse / Lab Technician / Pharmacist / Billing have **no patient-search
  access in v1** — their own feature specs grant the search access their
  workflows need, when those features are specified.
- Separation of duties where appropriate: clinical documentation vs billing,
  user administration vs routine care, result entry vs result approval
  (Master Plan §5.2). Exact separations depend on hospital policy and MVP
  feasibility — see OQ-4.

### 5.3 Data protection

- Synthetic data only in development, tests, screenshots, and demos
  (Constitution III, §2.4). No real patient records, ever.
- Data minimisation: collect only fields justified by approved workflows.
- `national_id` (CNIC / B-Form): encrypted at rest; deterministic
  HMAC-SHA256 hash (server-side secret from the environment, never a
  per-record salt, never committed) enforces uniqueness and the duplicate
  check; full value visible only to Receptionist/Admin, masked (last 4
  digits) for all other roles; never in logs, list views, or URLs; never
  searchable (Spec 001 D-06/D-07/D-12, data-model.md).
- No patient details, passwords, tokens, or full clinical content in logs,
  error messages, URLs, or audit metadata (Constitution III; Master Plan
  §12.3). Errors are understandable without exposing secrets or stack
  traces (Master Plan FR-023).
- HTTPS in any hosted environment; `DEBUG` off and detailed error traces
  disabled in hosted/demo environments (Master Plan §12.5).
- Secrets and private configuration via environment variables only, never
  committed (Constitution III).

### 5.4 Audit

- Append-only `AuditEvent` records: actor, action, target type/ID,
  timestamp (UTC), outcome, limited non-sensitive metadata.
- Audited categories (Master Plan §12.4): authentication (sign-in/out,
  failures, disable, password reset), access control (role/permission
  changes), patient records (create, correction, status change, merge
  decision), clinical records (encounter create/finalise/correct, diagnosis
  or prescription change), laboratory (status change, result entry,
  approval/correction), financial (invoice issue/void, payment, refund/
  correction).
- Audit records never contain passwords, tokens, or full clinical content.

## 6. Data flow — core workflows

### 6.1 WF-01 New patient and appointment (Master Plan §7)

```text
Receptionist signs in (session auth)
  -> Search patients by MRN / name (>=3 chars) / phone
  -> No reliable match? Register patient (server generates MRN MC-YYYY-NNNNNN)
       - Duplicate check: exact name+DOB blocks; exact national_id hash blocks;
         exact phone alone warns (non-blocking). Human decision recorded; never auto-merge.
  -> Create appointment (patient + provider/department + date/time + visit type)
  -> System validates required fields + scheduling conflicts
  -> Appointment appears in the authorised schedule
```

Transaction boundary: registration + its audit event commit together; a
failure leaves no partial patient record (Master Plan NFR-04; Spec 001 edge
cases). MRN uniqueness is enforced by a database constraint, not by the UI.

### 6.2 WF-02 Patient arrival and encounter (Master Plan §7)

```text
Receptionist locates appointment -> records arrival / check-in
  -> Doctor's work queue shows the arrived patient
  -> Doctor opens patient + authorised history
  -> Doctor starts encounter (from appointment, or approved walk-in without one)
       records reason, notes, diagnosis fields; saves draft or finalises
  -> Encounter stays linked to patient, provider, appointment
```

Appointment and encounter are distinct records: a completed appointment does
not mean clinical documentation is complete. Encounter corrections are
traceable; clinical content stays out of general logs and unnecessary reports.

### 6.3 WF-03 Laboratory request and result (P1 candidate, if included)

```text
Doctor creates lab request from an encounter
  -> Lab queue (authorised lab staff only) shows the request
  -> Lab updates collection / processing statuses
  -> Lab enters result (value, unit, reference metadata, author, timestamp)
  -> Result finalised / approved if required
  -> Authorised clinician reviews the result
```

Request, specimen, and result states are traceable; unauthorised users cannot
alter results. Result entry and result approval are separate duties where the
approved workflow requires it.

### 6.4 WF-04 Invoice and payment (P1 candidate, if included)

```text
Billing selects approved chargeable services
  -> Invoice created with line items; total computed with Decimal arithmetic
  -> Cashier records payment (amount, method, date, receipt reference)
  -> Outstanding balance + invoice status updated (Unpaid / Partially paid /
     Paid / Voided / Refunded, per approved policy)
  -> Receipt / payment reference available
  -> Corrections / refunds follow an approved, audited process
```

Invoice and payment are separate records; an invoice may receive multiple
payments; overpayment and invalid transitions are prevented.

### 6.5 WF-05 User and permission administration (Master Plan §7)

```text
Admin creates / activates a staff account -> assigns approved role(s)
  -> User signs in, sees only permitted functions and records
  -> Role changes take effect per session policy (see OQ-2)
  -> Account disabled when no longer authorised
  -> Security-relevant actions recorded in audit
```

## 7. Deployment shape

Full guide: `docs/deployment-guide.md`. Shape in brief:

- Single deployment instance, one hospital (Master Plan §2.4). No
  multi-tenancy, no service mesh, no containers required by this plan —
  containers/caching/async jobs only when a demonstrated need justifies
  them (Master Plan §10.3). Hosting provider is **not decided** — see OQ-5.
- Backend: Django + Gunicorn-style WSGI server (or the equivalent
  production server chosen at deployment time) in front of PostgreSQL 16;
  static/media handling and HTTPS termination per the chosen host.
- Frontend: Vite production build served as static files (same host or a
  static host — see OQ-5), calling the same-origin `/api/` where possible
  so session cookies and CSRF work without cross-origin complexity.
- Configuration entirely via environment variables (`.env` never committed);
  `DEBUG=False` in any hosted environment.
- Database backup/restore documented and demonstrated at least once before
  release review (Master Plan NFR-12, §16.3).
- CI: tests run on every meaningful change; migrations must apply cleanly
  from a fresh setup (Master Plan §16.3).

## 8. Non-functional requirements — how this architecture meets them

| NFR | How |
|---|---|
| NFR-01 Security | Session auth, backend RBAC + object checks, deny by default, no committed secrets |
| NFR-02 Privacy | Synthetic data only; data minimisation; national_id encryption/masking/no-search |
| NFR-03 Integrity | PostgreSQL constraints, transactions for multi-record operations, migrations version-controlled |
| NFR-04 Reliability | Fail safely, no silent partial success, actionable errors |
| NFR-05 Performance | Provisional: common list/detail API calls < 2 s under a small demo dataset, local test conditions; indexes on search/relationship fields |
| NFR-06 Usability | Consistent layout, role-aware navigation, clear labels/validation/status feedback |
| NFR-07 Accessibility | Keyboard-operable, visible focus, labelled controls, status not by colour alone |
| NFR-08 Maintainability | Layered modular monolith, single source of truth for business rules |
| NFR-09 Testability | Rules and permissions testable without the UI (services + API tests) |
| NFR-10 Compatibility | Current mainstream desktop browsers; exact matrix to be chosen before release (OQ-6) |
| NFR-11 Observability | Structured error/operational logging without secrets or clinical detail |
| NFR-12 Backup/recovery | Documented backup/restore, tested at least once |
| NFR-13 Portability | Environment-based config, reproducible setup instructions |
| NFR-14 Scalability | No premature optimisation; modular boundaries + indexed query fields |

## 9. Not decided / deferred

- **Master Plan §§19–23 are missing** from the supplied document (body ends
  at §18.1): deployment/operations, risk register, governance/decision log,
  acceptance, and open decisions. They must be supplied or formally deferred
  before release planning (Phase 8). This architecture plan does not invent
  their content.
- P1 modules (prescriptions, laboratory, billing, reporting) are candidates,
  not commitments — each needs its own approved spec before implementation
  (Master Plan §4.4).
- P2/future modules (nursing observations, inpatient/beds, pharmacy/
  inventory, portal/notifications) are out of scope unless explicitly
  approved.

## Open Questions

- **OQ-1 — API versioning.** Master Plan §14.1 says "version the API when
  compatibility needs justify it". No versioning scheme is decided for v1.
  This plan assumes unversioned `/api/` for the single browser client;
  confirm whether a `/api/v1/` prefix should be adopted from the start.
- **OQ-2 — Session/role-change policy.** When an Admin changes a user's
  role or disables an account, do existing sessions end immediately, at
  next request, or at expiry? Django can revoke server-side, but the exact
  policy (and session expiry length) is not decided.
- **OQ-3 — Appointment conflict rules.** Which conflicts block booking
  (same doctor overlapping time? same room? double-booking a patient?) is
  for the appointments spec, not this plan. Listed here so the boundary is
  explicit.
- **OQ-4 — Separation-of-duties specifics.** Master Plan §5.2 leaves exact
  separations (e.g. who approves lab results, who may void an invoice) to
  hospital policy and MVP feasibility. Each feature spec must state them.
- **OQ-5 — Hosting / deployment target.** No hosting provider, server, or
  demo-environment host is decided (Master Plan §19 is missing). Local and
  demo setup are documented in `docs/deployment-guide.md`; the production-
  like host decision is deferred to Phase 8/9.
- **OQ-6 — Browser matrix.** "Current mainstream desktop browsers" is the
  provisional target (NFR-10); the exact matrix must be chosen before
  release.
- **OQ-7 — Diagnosis coding.** Free text vs a coding scheme (e.g. ICD-10)
  for diagnoses is not decided; the encounters spec must decide it. This
  plan assumes free text with an optional code field until then.
- **OQ-8 — Background jobs / notifications.** No async jobs, email, or SMS
  are assumed. If appointment reminders or notifications are ever approved,
  the job runner, provider, and consent handling need a separate decision.
