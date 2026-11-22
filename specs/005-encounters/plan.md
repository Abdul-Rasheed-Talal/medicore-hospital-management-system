# Implementation Plan: Encounters / Consultation (005)

**Branch**: `docs/medicore-all-specs` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — spec not yet approved by the owner. Implementation may
proceed only after the owner approves this spec and the Open Questions it
depends on are resolved (notably Q-001 walk-in approval, defined by the
appointment feature M04, and Q-002 structured-note fields, which need
clinical review).

## Summary

Build encounters (Master Plan §4 P0, §6 M05, §7 WF-02, §8 FR-011/FR-012):
a Doctor starts an encounter from an arrived appointment or an approved
walk-in, records reason for visit, structured notes, and free-text diagnosis
entries, saves it as a draft, and finalises it. Finalised encounters change
only through traceable corrections. Clinical content stays out of logs,
audit metadata, and reports. Permissions are enforced on the backend; only
the authoring Doctor creates, edits, finalises, and corrects their own
encounter.

Technical approach: modular monolith — React + TypeScript + Vite + Tailwind
+ shadcn/ui frontend, Django + DRF + PostgreSQL backend, `encounters`
Django app, REST API under `/api/encounters/`, encounter status enforced by
a database constraint plus service-layer rules, audit events for
create/finalise/correct. Stack is ACCEPTED (ADR-001, owner approval
2026-11-22); session auth is the decided auth strategy (Spec 001 D-09).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided,
ADR-001; verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19 + Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing Library (frontend), Playwright (E2E, one journey: arrived appointment → encounter → finalise)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2 seconds under a small demo dataset and local test conditions (Master Plan NFR-05, provisional)

**Constraints**: Synthetic data only; no real patient records; secrets via environment only; backend validation is authoritative (frontend validation is usability only); no hard deletion of encounters; no clinical content in logs, audit metadata, or error messages

**Scale/Scope**: Single hospital, single deployment; tens of staff users; thousands of patient records and encounters in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a draft; implementation waits for owner approval and resolution of blocking open questions (Q-001, Q-002). PASS when approved. |
| II. Modular architecture | `encounters` Django app, separate frontend pages/components, business rules in services — not duplicated in views/serializers. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced; least privilege (author-only clinical access; Receptionist schedule-context only; Admin no clinical content by default); synthetic data only; no clinical content in logs/audit. PASS by design. |
| IV. Data integrity | PostgreSQL, status constraint, transactions for finalise + audit, migrations version-controlled, no hard delete, correction history append-only. PASS by design. |
| V. Test-first | Permission allow/deny tests, draft/finalise tests, correction tests, E2E journey test are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; API contract documented. PASS by design. |
| VIII. Scope discipline | Encounters/notes/diagnosis/corrections only. Prescriptions, lab, billing, nursing are separate features. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/005-encounters/
├── spec.md              # Feature specification (draft 2026-11-22)
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
│   ├── appointments/    # Appointments, arrival status, walk-in approval (prerequisite for the appointment-linked path, M04)
│   ├── encounters/      # Encounter, notes, diagnosis entries, corrections
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py  # Start, finalise, correct (status rules live here)
│   │   ├── views.py     # DRF viewsets, permission-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── audit/           # Audit events (shared)
└── tests/

frontend/
├── src/
│   ├── components/      # EncounterForm, DiagnosisEntries, CorrectionHistory, EncounterDetail
│   ├── pages/           # Doctor work queue, encounter detail, patient encounter history
│   ├── services/        # API client for /api/encounters/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` + `docs/`.
Backend apps are created only when their scope is approved — `accounts`,
`patients`, and `appointments` are prerequisites for this feature (the
appointment-linked path needs M04's Arrived status; the walk-in path needs
its approval definition). Do not create every app in Master Plan §10.4 at
initialisation.

## Data model sketch

**Encounter**: id (UUID PK); patient (FK → Patient, required); appointment
(FK → Appointment, nullable); clinician (FK → User, Doctor role, required);
encounter_datetime (DateTime UTC, required, not in the future);
reason_for_visit (Text, required); status (Enum: Draft / Finalized);
created_by, created_at, finalised_by (nullable), finalised_at (nullable).
Constraints: one open (Draft) encounter per patient at a time (E-05);
status transitions Draft → Finalized only, enforced in the service layer
and by a database check constraint; no delete.

**EncounterNote**: id (UUID PK); encounter (FK → Encounter); content
(structured note fields — exact fields are Open Question Q-002; a single
structured text area until clinical review agrees the fields); author
(FK → User); created_at, updated_at. Draft notes editable by the author;
finalised notes change only via EncounterCorrection.

**DiagnosisEntry**: id (UUID PK); encounter (FK → Encounter); diagnosis_text
(Text, free text in v1, no code — E-03); author (FK → User); created_at.
One encounter has many entries; at least one is required at finalisation
(E-04).

**EncounterCorrection**: id (UUID PK); encounter (FK → Encounter); field
(which note/diagnosis entry changed); old_value; new_value; author
(FK → User); created_at; reason (Text, required). Append-only; history is
never overwritten.

**AuditEvent** (shared, from the `audit` app): actor, action (e.g.
`encounter.create`, `encounter.finalize`, `encounter.correct`), target_type /
target_id (Encounter, the encounter id), timestamp, outcome, metadata
(limited, non-sensitive context only — never note or diagnosis text, E-06).

Relationships: one Patient → many Encounters; one Appointment → zero or one
Encounter; one Encounter → many EncounterNotes, many DiagnosisEntries, many
EncounterCorrections, many AuditEvents. Patient is distinct from User
(Master Plan §7.1). Indexes: patient, appointment (unique where not null —
one encounter per appointment), clinician, status, created_at. No index on
clinical text.

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `POST /api/encounters/` | Start an encounter (Doctor). Body: patient, appointment (optional, must be Arrived) or walk-in flag. Returns 201 with Draft encounter, or 400/403/409 per the spec's rules. |
| `GET /api/encounters/?patient=&status=&page=` | List encounters in the caller's authorised scope (Doctor: own; Receptionist: schedule context only, no clinical content). Paginated. |
| `GET /api/encounters/{id}/` | Encounter detail: notes, diagnosis entries, correction history, author/timestamps. |
| `PATCH /api/encounters/{id}/` | Edit own draft (Doctor, author only). Refused on a finalised encounter. |
| `POST /api/encounters/{id}/finalize/` | Finalise own draft (Doctor, author only). Refused without reason for visit, notes, and at least one diagnosis entry. |
| `POST /api/encounters/{id}/corrections/` | Record a correction to a finalised encounter (Doctor, author only; reason required). |
| `GET /api/encounters/{id}/corrections/` | Correction history (authorised viewers). |

All endpoints require authentication; all mutations require the role in the
spec's permissions table; validation errors return structured field-level
errors. No endpoint returns or accepts clinical content in a URL or log line.

## Security approach

- Django session authentication (decided, ADR-001 / Spec 001 D-09): secure
  HttpOnly cookie, CSRF protection, server-side session revocation. No JWT
  in v1.
- Permission classes per endpoint + object-level checks (author-only for
  edit/finalise/correct; own-encounters scope for Doctor reads); deny by
  default.
- Encounter creation server-side only; never trust a client-supplied
  clinician, status, or timestamp.
- Clinical content (notes, diagnosis text) never in logs, audit metadata,
  error messages, list views beyond the caller's permitted scope, or URLs.
- Patient CNIC / B-Form is never exposed through encounter endpoints: it is
  encrypted at rest, visible in full only to Receptionist/Admin, masked
  otherwise, and never searchable (Spec 001 D-06, D-12).
- Audit events for create / finalise / correct, without clinical content.
- Rate-limit login; throttle encounter endpoints against abuse.

## Test strategy

- **Unit**: status-transition rules (draft editable, finalised locked,
  finalise requires diagnosis), one-open-draft rule, validation rules
  (reason required, encounter datetime not in the future).
- **Model/DB**: status constraint, one-encounter-per-appointment, correction
  rows append-only, no hard delete, migration applies cleanly from fresh
  setup.
- **API**: auth required (401 unauthenticated), permission allow/deny per
  role (Receptionist create → 403; second Doctor finalise → 403),
  validation errors (400 with field errors), finalise-without-diagnosis
  refused, correction flow (old value preserved in history).
- **Component**: encounter form validation feedback, draft/finalise states,
  correction-history display, empty queue state.
- **E2E (Playwright)**: arrived appointment → start encounter → record
  reason/notes/diagnosis → finalise → view finalised encounter with
  timestamps.
- **Security**: object-level access (a Doctor cannot fetch another Doctor's
  encounter by changing an ID unless authorised), no clinical content in
  audit events or logs in test output.

Tests are written first (Constitution Principle V) and must fail before implementation.

## Risks for this feature

- **Walk-in approval undefined (Q-001)** — the walk-in path cannot be
  implemented until the appointment feature defines it. Mitigation: build
  the appointment-linked path first; the walk-in path is a follow-up once
  M04 defines approval.
- **Structured-note fields undefined (Q-002)** — needs clinical review
  (Master Plan §4.2). Mitigation: implement a single structured text area
  for notes in v1; do not invent clinical sections. The field set is added
  by spec amendment after review.
- **Cross-clinician viewing undefined (Q-004)** — the strictest safe default
  (own encounters only) is specified; loosening it later is a spec decision,
  not a code change made silently.
- **Auth/RBAC (M01), patients (001), appointments (M04) not built yet** —
  this feature cannot be demonstrated without them. Mitigation: build in
  dependency order (M01 → 001 → M04 → 005).
- **Scope creep into prescriptions/lab/billing** — those are separate
  specs (006, 007, later). Mitigation: the spec's out-of-scope list is
  enforced at review.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
