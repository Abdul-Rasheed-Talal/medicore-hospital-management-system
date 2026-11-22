# Implementation Plan: Laboratory (007)

**Branch**: `docs/medicore-all-specs` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — spec not yet approved by the owner. **P1 CANDIDATE —
pending the owner's priority call.** Do not implement until the owner
explicitly includes this feature (Master Plan §4.2 P1 Candidate, §17 Phase
6 — choose lab OR billing OR prescription, not all in parallel).

## Summary

Build laboratory management (Master Plan §6 M08, §7 WF-03, §8 FR-014/
FR-015): a Doctor creates a test request linked to a patient and a
finalised encounter; Lab staff work it through Requested → Collected →
Received → In-progress → Completed (or Cancelled before completion),
recording specimen details and entering results (value, unit, reference
range) with author and timestamps; completed results change only through
traceable corrections. Access is restricted to Lab staff and the requesting
care staff, with minimum patient identifiers only.

Technical approach: modular monolith — React + TypeScript + Vite + Tailwind
+ shadcn/ui frontend, Django + DRF + PostgreSQL backend, `laboratory`
Django app, REST API under `/api/lab-requests/` and `/api/lab-results/`,
status transitions enforced by a database constraint plus service-layer
rules, audit events for status changes, result entry, approval, and
correction. Stack is ACCEPTED (ADR-001, owner approval 2026-11-22); session
auth is the decided auth strategy (Spec 001 D-09).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided,
ADR-001; verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19 + Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing Library (frontend), Playwright (E2E, one journey: request → collect → receive → in-progress → result → completed)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2 seconds under a small demo dataset and local test conditions (Master Plan NFR-05, provisional)

**Constraints**: Synthetic data only; no real patient records; secrets via environment only; backend validation is authoritative (frontend validation is usability only); no hard deletion of requests, results, or corrections; no clinical interpretation of results; no patient CNIC / B-Form visible to Lab staff

**Scale/Scope**: Single hospital, single deployment; tens of staff users; thousands of patient records, encounters, requests, and results in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a draft and a P1 candidate; implementation waits for owner approval and the priority call. PASS when approved. |
| II. Modular architecture | `laboratory` Django app, separate frontend pages/components, business rules in services — not duplicated in views/serializers. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced; least privilege (Lab staff request-scoped, minimum identifiers; Doctor cannot enter results; no Receptionist/Billing access); synthetic data only. PASS by design. |
| IV. Data integrity | PostgreSQL, status constraint, transactions for status change + audit, migrations version-controlled, no hard delete, correction history append-only. PASS by design. |
| V. Test-first | Permission allow/deny tests, state-machine tests, validation tests, E2E journey test are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; API contract documented. PASS by design. |
| VIII. Scope discipline | Lab requests/results only. No analyzer integration, no test catalog invented, no result interpretation, no pharmacy/billing. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/007-laboratory/
├── spec.md              # Feature specification (draft 2026-11-22, P1 CANDIDATE)
├── plan.md              # This file
└── tasks.md             # Phase 2 output (NOT created yet)
```

### Source Code (repository root)

```text
backend/
├── config/              # Django settings (env-based), urls
├── apps/
│   ├── accounts/        # Users, roles, permissions (prerequisite, M01)
│   ├── patients/        # Patient identity (prerequisite, Spec 001)
│   ├── encounters/      # Encounters (prerequisite, Spec 005)
│   ├── laboratory/      # Lab requests, results, corrections
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py  # Request, advance status, enter result, approve, correct
│   │   ├── views.py     # DRF viewsets, permission-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── audit/           # Audit events (shared)
└── tests/

frontend/
├── src/
│   ├── components/      # LabRequestForm, LabQueue, ResultEntryForm, ResultDetail, CorrectionHistory
│   ├── pages/           # Lab queue, request detail, doctor's requested tests
│   ├── services/        # API client for /api/lab-requests/ and /api/lab-results/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` + `docs/`.
Backend apps are created only when their scope is approved — `accounts`,
`patients`, and `encounters` are prerequisites for this feature. Do not
create every app in Master Plan §10.4 at initialisation.

## Data model sketch

**LabRequest**: id (UUID PK); patient (FK → Patient, required); encounter
(FK → Encounter, required, must be Finalized at creation — L-02);
requester (FK → User, Doctor role, required); test_name (Text, required);
specimen_type (Text, nullable until Collected); collected_at (DateTime,
nullable); collected_by (FK → User, Lab staff, nullable); status (Enum:
Requested / Collected / Received / In-progress / Completed / Cancelled);
created_by, created_at, cancelled_by (nullable), cancelled_at (nullable),
cancellation_reason (Text, required when cancelling). Constraints: status
transitions per L-04 only, enforced in the service layer and by a database
check constraint; no delete; one test per request (L-01).

**LabResult**: id (UUID PK); request (FK → LabRequest, required); value
(Text, required — numeric or textual per test); unit (Text, required);
reference_range (Text, required); author (FK → User, Lab staff, required);
entered_at (DateTime); approved_by (FK → User, nullable); approved_at
(DateTime, nullable); approval_status (Enum: Pending / Approved /
Not required — see Q-003). One request may have one or more results
(Master Plan §11.2).

**LabResultCorrection**: id (UUID PK); result (FK → LabResult); field;
old_value; new_value; author (FK → User); created_at; reason (Text,
required). Append-only; history is never overwritten.

**AuditEvent** (shared, from the `audit` app): actor, action (e.g.
`lab.request_create`, `lab.status_change`, `lab.result_entry`,
`lab.result_approve`, `lab.result_correct`, `lab.request_cancel`),
target_type / target_id (LabRequest / LabResult, the record id), timestamp,
outcome, metadata (limited, non-sensitive context only).

Relationships: one Patient → many LabRequests; one Encounter → many
LabRequests; one LabRequest → many LabResults; one LabResult → many
LabResultCorrections. Patient is distinct from User (Master Plan §7.1).
Indexes: patient, encounter, requester, status, created_at. No index on
result values.

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `POST /api/lab-requests/` | Create a test request (Doctor). Body: encounter (must be Finalized), test name, specimen details where known. Returns 201 with Requested request, or 400/403 per the spec's rules. |
| `GET /api/lab-requests/?status=&patient=&page=` | Lab queue / request list in the caller's authorised scope (Lab staff: queue with minimum identifiers; Doctor: own requests). Paginated. |
| `GET /api/lab-requests/{id}/` | Request detail with specimen details, results, and correction history. |
| `POST /api/lab-requests/{id}/advance/` | Advance status to the next permitted state (Lab staff only; specimen details required at Collected). |
| `POST /api/lab-requests/{id}/cancel/` | Cancel a request before completion (requesting Doctor or Lab staff; reason required). Refused once Completed. |
| `POST /api/lab-requests/{id}/results/` | Enter a result (Lab staff only; from In-progress status; value, unit, reference range required). Completes the request subject to the approval rule (Q-003). |
| `GET /api/lab-results/{id}/` | Result detail with author and timestamps. |
| `POST /api/lab-results/{id}/approve/` | Approve a result (Lab staff, where approval applies; see Q-003). |
| `POST /api/lab-results/{id}/corrections/` | Record a correction to a completed result (Lab staff; reason required). |
| `GET /api/lab-results/{id}/corrections/` | Correction history (authorised viewers). |

All endpoints require authentication; all mutations require the role in the
spec's permissions table; validation errors return structured field-level
errors. No endpoint returns a patient's CNIC / B-Form number to Lab staff.

## Security approach

- Django session authentication (decided, ADR-001 / Spec 001 D-09): secure
  HttpOnly cookie, CSRF protection, server-side session revocation. No JWT
  in v1.
- Permission classes per endpoint + object-level checks (Lab staff
  request-scoped; Doctor own-requests scope); deny by default.
- Request/result creation server-side only; never trust a client-supplied
  requester, author, status, or timestamp.
- Lab staff see minimum patient identifiers only (MRN, name). Patient CNIC
  / B-Form is never exposed through lab endpoints: encrypted at rest,
  visible in full only to Receptionist/Admin, masked otherwise, never
  searchable (Spec 001 D-06, D-12).
- Audit events for request creation, status changes, result entry,
  approval, correction, and cancellation.
- Rate-limit login; throttle lab endpoints against abuse.

## Test strategy

- **Unit**: state-machine transitions (valid and invalid), validation rules
  (test name required, specimen details at Collected, value/unit/reference
  range at result entry), cancel-only-before-completion rule.
- **Model/DB**: status constraint, one-or-more-results-per-request,
  correction rows append-only, no hard delete, migration applies cleanly
  from fresh setup.
- **API**: auth required (401 unauthenticated), permission allow/deny per
  role (Receptionist view → 403; Doctor result entry → 403; Lab staff
  request creation → 403), validation errors (400 with field errors),
  standalone request refused, request on draft encounter refused,
  skip-state result entry refused, correction flow (old value preserved).
- **Component**: lab queue, request form validation feedback, result-entry
  form, correction-history display, empty queue state.
- **E2E (Playwright)**: finalised encounter → create request → Collected →
  Received → In-progress → enter result → Completed → requesting Doctor
  reviews the result.
- **Security**: object-level access (Lab staff cannot fetch another
  patient's full record by changing an ID; a Doctor cannot fetch another
  Doctor's request by changing an ID unless authorised), no CNIC in any
  lab response in test output.

Tests are written first (Constitution Principle V) and must fail before implementation.

## Risks for this feature

- **Candidate status (priority call not made)** — the feature may never be
  implemented if the owner picks prescription or billing instead (Master
  Plan §17 Phase 6). Mitigation: no implementation work starts until the
  owner explicitly includes it.
- **Test catalog undefined (Q-001)** — free-text test names risk requests
  for tests the lab does not perform. Mitigation: accepted for v1; handled
  by cancellation with a reason. A catalog is a later spec decision owned
  by hospital setup (M02), not invented here.
- **Approval rule undefined (Q-003)** — whether approval is mandatory and
  who approves. Mitigation: approval fields exist in the data model; the
  default until decided is that result entry completes the request without
  a separate approval step.
- **Reference-range source undefined (Q-002)** — ranges vary by age/sex.
  Mitigation: entered per result in v1; do not guess a range table.
- **Auth/RBAC (M01), patients (001), encounters (005) not built yet** — this
  feature cannot be demonstrated without them. Mitigation: build in
  dependency order (M01 → 001 → 005 → 007).
- **Scope creep into interpretation or analyzer integration** — explicitly
  out of scope (Master Plan §4.3). Mitigation: the spec's out-of-scope list
  is enforced at review.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
