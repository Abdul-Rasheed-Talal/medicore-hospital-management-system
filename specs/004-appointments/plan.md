# Implementation Plan: Appointment Management (004)

**Branch**: `docs/medicore-all-specs` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — spec is not yet approved by the owner. The open
questions in the spec (OQ-001–OQ-007) must be decided before the
implementation that depends on them; the plan records which parts are
blocked by which question (see Risks).

## Summary

Build appointment management (Master Plan §4 P0, §6 M04, §7 WF-01/02,
§8 FR-008/009/010): a Receptionist creates appointments for registered
patients with a provider, date/time, and visit type; the backend refuses
overlapping bookings for the same provider and the same patient;
appointments move through Scheduled → Arrived → Completed (or Cancelled /
No-show) under an explicit transition table; check-in, reschedule, cancel
with reason, and daily schedule views complete the front-desk workflow.
An appointment is a reservation, not the care itself — the encounter
feature owns clinical documentation (Master Plan §7.1).

Technical approach: modular monolith — React + TypeScript + Vite + Tailwind +
shadcn/ui frontend, Django + DRF + PostgreSQL backend, `appointments` Django
app, REST API under `/api/appointments/`, conflict checks enforced by the
backend in a transaction (not only by the UI), status transitions enforced
in the service layer, audit events for every appointment action. Stack is
ACCEPTED (ADR-001, owner approval 2026-11-22). Depends on Spec 001
(`patients`), Spec 002 (`accounts`, `audit`), and Spec 003 (`organization`
for providers and visit types).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided;
verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19 + Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing Library (frontend), Playwright (E2E, one journey: search patient → create appointment → check in → mark Completed)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2 seconds under a small demo dataset and local test conditions (Master Plan NFR-05, provisional)

**Constraints**: Synthetic data only; no real patient records; secrets via environment only; backend validation is authoritative (frontend validation is usability only); no hard deletion of appointments; no double-booking — the conflict check must hold under concurrent requests; all times stored in UTC, displayed in Asia/Karachi

**Scale/Scope**: Single hospital, single deployment; tens of staff users; hundreds of appointments in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a draft; implementation must wait for owner approval and for the blocking open question (OQ-001, duration) to be decided. CONDITIONAL PASS. |
| II. Modular architecture | `appointments` Django app, separate frontend pages/components, business rules (conflicts, transitions) in services — not duplicated in views/serializers. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced; patient data in schedules limited by Spec 001 rules (name + MRN only, no CNIC); synthetic data only; no secrets in code. PASS by design. |
| IV. Data integrity | PostgreSQL, foreign keys, transactions for create/reschedule + audit, overlap enforced server-side under concurrency, migrations version-controlled, no hard delete. PASS by design. |
| V. Test-first | Conflict tests (including concurrent), transition tests, permission allow/deny tests, E2E journey test are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; ADR-001 records the stack decision; API contract documented. PASS by design. |
| VIII. Scope discipline | Create/reschedule/cancel/check-in/status/schedules only. Encounters, reminders, recurring bookings, billing are separate/deferred. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/004-appointments/
├── spec.md              # Feature specification (draft 2026-11-22)
├── plan.md              # This file
└── tasks.md             # Phase 2 output (NOT created yet)
```

No `research.md`: no new research decision was needed — the stack is
already decided in ADR-001, patient identity and privacy rules in Spec
001, and the remaining choices (notably duration, OQ-001) are recorded as
open questions in the spec, not resolved by research. No `data-model.md`:
the data model sketch below lives in this plan.

### Source Code (repository root)

```text
backend/
├── config/              # Django settings (env-based), urls
├── apps/
│   ├── accounts/        # Users, roles (prerequisite, Spec 002)
│   ├── audit/           # Audit events (prerequisite, Spec 002)
│   ├── patients/        # Patient identity, MRN (prerequisite, Spec 001)
│   ├── organization/    # Departments, staff, visit types (prerequisite, Spec 003)
│   ├── appointments/    # Schedules, slots, status transitions (this feature)
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py  # Conflict checks, status transitions
│   │   ├── views.py     # DRF viewsets, permission-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── encounters/      # NOT created — separate feature, separate spec
└── tests/

frontend/
├── src/
│   ├── components/      # AppointmentForm, ScheduleList, CheckInButton, StatusActions
│   ├── pages/           # Appointment calendar/list, appointment detail
│   ├── services/        # API client for /api/appointments/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` + `docs/`.
Backend apps are created only when their scope is approved — `appointments`
is created with this feature; it depends on `patients`, `organization`,
`accounts`, and `audit`, which must land first or alongside it. Do not
create every app in Master Plan §10.4 at initialisation.

## Data model sketch

| Entity | Key fields / notes |
|---|---|
| Appointment | id (UUID PK), patient (FK → Patient, required — via MRN `MC-YYYY-NNNNNN`, Spec 001 D-01), provider (FK → StaffProfile, Doctor role, required — Spec 003), department (FK → Department, derived from the provider), visit_type (FK → VisitType, required — Spec 003), start_at (DateTime, UTC, required), duration_minutes (integer, required — value source is spec OQ-001; until decided, entered per appointment), end_at (derived: start_at + duration; stored or computed — implementation detail, must be consistent for the overlap check), status (enum: Scheduled / Arrived / Completed / Cancelled / No-show), reason_for_visit (text, optional), cancellation_reason (text, required when Cancelled), arrived_at (DateTime, nullable), completed_at (DateTime, nullable), created_by (FK → User), created_at, updated_at |
| AuditEvent (shared, `audit` app) | See Spec 002 plan: actor, action (e.g. `appointments.create`, `appointments.reschedule`, `appointments.cancel`, `appointments.check_in`, `appointments.complete`, `appointments.no_show`), target, timestamp, outcome, non-sensitive metadata only (old/new times on reschedule). |

Constraints: patient FK, provider FK, visit-type FK (database); start_at
not in the past (backend, judged in Asia/Karachi); patient must be Active
(backend); provider and visit type must be active (backend); status
transitions only per the spec's transition table (service layer, tested);
overlap rule enforced in a transaction — the check-then-create sequence
must hold under concurrent requests (e.g. row-level locking on the
provider's appointments or a database exclusion constraint on the
provider/patient interval; the exact mechanism is an implementation
choice, the guarantee is not: two overlapping appointments for one
provider, or one patient, must never both be created). No hard delete;
cancellation is the end state. Indexes: provider + start_at, patient +
start_at, status + start_at (daily schedule queries).

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `POST /api/appointments/` | Create an appointment (Receptionist/Admin). Returns 201 with status Scheduled, or 409 with a conflict error (provider or patient overlap), or 400 with field/business-rule errors. |
| `GET /api/appointments/?date=&provider=&department=&patient=&status=&page=` | Daily schedule / search (role-filtered: Doctor sees own, Nurse own department, Receptionist/Admin all). Paginated, sorted by start time; patient search follows Spec 001 permissions. |
| `GET /api/appointments/{id}/` | Appointment detail (role-filtered patient fields: name + MRN only, no CNIC). |
| `PATCH /api/appointments/{id}/reschedule/` | Move to a new date/time (Receptionist/Admin, Scheduled only). Re-checks conflicts and the past-date rule; records old/new times in the audit event. |
| `PATCH /api/appointments/{id}/cancel/` | Cancel with a required reason (Receptionist/Admin, Scheduled or Arrived). |
| `PATCH /api/appointments/{id}/check-in/` | Record arrival (Receptionist/Admin, Scheduled only). Sets status Arrived + arrival timestamp. |
| `PATCH /api/appointments/{id}/complete/` | Mark Completed (Receptionist/Admin, or the Doctor for own appointments; Arrived only). |
| `PATCH /api/appointments/{id}/no-show/` | Mark No-show (Receptionist/Admin, Scheduled only). |

All endpoints require authentication; all mutations require the role in the
spec's permissions table; validation errors return structured field-level
errors; conflict errors return 409 with the clashing appointment identified
(minimal detail — no unnecessary patient data).

## Security approach

- Django session authentication (decided, ADR-001 / Spec 002): secure HttpOnly cookie, CSRF protection, server-side session revocation. No JWT in v1.
- Permission classes per endpoint + object-level checks (a Doctor may act only on their own appointments; a Nurse sees only their department's schedule); deny by default.
- Schedule responses contain patient name + MRN only — never CNIC / B-Form, never clinical or financial detail (Spec 001 privacy rules).
- No patient data in logs, URLs (beyond the MRN in a query/filter), or error messages beyond what the caller's role may see.
- Audit events for create / reschedule / cancel / check-in / complete / no-show.
- Rate-limit/throttle appointment endpoints against abuse (same approach as Spec 002).

## Test strategy

- **Unit**: overlap detection (provider and patient, boundary cases: back-to-back appointments do not overlap), transition-table enforcement, past-date rule, cancellation-reason requirement.
- **Model/DB**: foreign keys, migration applies cleanly from fresh setup, indexes present for schedule queries.
- **API**: auth required (401 unauthenticated), permission allow/deny per role (Lab/Pharm/Billing → 403; Doctor creating → 403; Doctor completing another provider's appointment → 403), validation errors (400 with field errors), conflict → 409, invalid transition → 409/400 with understandable error, pagination and filters on the schedule.
- **Concurrency**: two simultaneous overlapping bookings for the same provider result in exactly one appointment (the second is refused).
- **Component**: appointment form validation feedback, schedule list with empty state, check-in/cancel confirm flows.
- **E2E (Playwright)**: search patient by MRN → create appointment → schedule shows it → check in → mark Completed.
- **Security**: object-level access (a Doctor cannot fetch or change another provider's appointment by changing an ID), audit events recorded, no CNIC in schedule responses.

Tests are written first (Constitution Principle V) and must fail before implementation.

## Risks for this feature

- **Open question OQ-001 (duration) blocks the conflict check**: overlap needs an interval. Mitigation: decide the duration rule with the owner before implementation starts; keep `duration_minutes` a per-appointment field in the model so any of the three options (fixed default, per-appointment entry, visit-type default) is a small change.
- **Concurrency**: two Receptionists booking the same slot at the same time must not both succeed. Mitigation: enforce the overlap check in a transaction with locking or a database exclusion constraint; cover it with a concurrency test (see Test strategy).
- **Dependencies**: Specs 001, 002, and 003 must land first or alongside this feature. Mitigation: build in dependency order (002 → 001 → 003 → 004), with this feature's tests depending on them.
- **No-show handling (OQ-004)**: if the owner later wants automatic no-show, the status logic gains a scheduled job. Mitigation: manual marking only in v1; no background job is built on a guess.
- **Scope creep into encounters**: a Completed appointment is not a completed clinical record (spec D-07). Mitigation: the spec's out-of-scope list and the transition table are enforced at review; the encounter spec owns the appointment→encounter link.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
