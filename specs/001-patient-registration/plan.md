# Implementation Plan: Patient Registration (001)

**Branch**: `docs/medicore-day1-spec-001` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Approved by owner 2026-11-22. Spec 001 and ADR-001 are approved;
the 10 open questions are decided (see spec.md "Decisions"), as amended
2026-11-22 by owner instruction: gender required (D-11), CNIC / B-Form
required (D-12), blood group optional (D-13). Implementation may proceed
once the scaffold (M01 authentication/RBAC) exists.

## Summary

Build patient registration (Master Plan §4 P0, §6 M03, §7 WF-01, §8 FR-005/006/007):
a Receptionist searches for a patient, registers them if no reliable match exists,
receives an auto-generated unique MRN, and any close match is flagged for
controlled duplicate review — never silently merged. A correction history is kept
for demographic changes. Permissions are enforced on the backend; Doctor is
read-only for patient records.

Technical approach: modular monolith — React + TypeScript + Vite + Tailwind +
shadcn/ui frontend, Django + DRF + PostgreSQL backend, `patients` Django app,
REST API under `/api/patients/`, MRN uniqueness enforced by a database
constraint, audit events for create/correct/status/duplicate decisions.
Stack is ACCEPTED (ADR-001, owner approval 2026-11-22); session auth is the
decided auth strategy (see spec.md D-09).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided;
verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19 + Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing Library (frontend), Playwright (E2E, one journey: search → register → find)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2 seconds under a small demo dataset and local test conditions (Master Plan NFR-05, provisional)

**Constraints**: Synthetic data only; no real patient records; secrets via environment only; backend validation is authoritative (frontend validation is usability only); no hard deletion of patient records

**Scale/Scope**: Single hospital, single deployment; tens of staff users; thousands of patient records in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec + plan approved by owner 2026-11-22; implementation may proceed once the scaffold exists. PASS. |
| II. Modular architecture | `patients` Django app, separate frontend pages/components, business rules in services — not duplicated in views/serializers. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced; least privilege (Doctor read-only); synthetic data only; no secrets in code; no patient data in logs. PASS by design. |
| IV. Data integrity | PostgreSQL, MRN unique constraint, transactions for register + audit, migrations version-controlled, no hard delete. PASS by design. |
| V. Test-first | Permission allow/deny tests, duplicate tests, validation tests, E2E journey test are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; ADR-001 records the stack decision; API contract documented. PASS by design. |
| VIII. Scope discipline | Registration/search/duplicate-review/correction-history only. Appointments, encounters, billing, portal are separate features. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/001-patient-registration/
├── spec.md              # Feature specification (approved 2026-11-22)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (Patient sketch)
├── contracts/           # Phase 1 output (API contract — to be written at plan approval)
└── tasks.md             # Phase 2 output (NOT created yet)
```

### Source Code (repository root)

```text
backend/
├── config/              # Django settings (env-based), urls
├── apps/
│   ├── accounts/        # Users, roles, permissions (prerequisite, M01)
│   ├── patients/        # Patient identity, search, duplicates, corrections
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py  # Registration, duplicate check, correction history
│   │   ├── views.py     # DRF viewsets, permission-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── audit/           # Audit events (shared)
└── tests/

frontend/
├── src/
│   ├── components/      # PatientForm, PatientSearch, DuplicateWarning, CorrectionHistory
│   ├── pages/           # Patient list/search, patient profile, registration
│   ├── services/        # API client for /api/patients/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` + `docs/`.
Backend apps are created only when their scope is approved — `accounts` and
`audit` are prerequisites for this feature and must land first (or alongside it,
with this feature's tests depending on them). Do not create every app in
Master Plan §10.4 at initialisation.

## Data model sketch

See `data-model.md` (Patient, DuplicateCandidate, PatientCorrection, AuditEvent).
Key constraints: MRN unique (database), patient status as an explicit enum,
correction history as separate rows (never overwrite), audit events without
clinical content or secrets.

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `POST /api/patients/` | Register a patient (Receptionist/Admin). Returns 201 with MRN, or 409/duplicate-warning payload when a candidate match exists (name + DOB, or CNIC / B-Form). |
| `GET /api/patients/?search=&page=` | Search by MRN, name (min 3 chars), or phone. Paginated, role-filtered fields; CNIC never searchable, never in list views. |
| `GET /api/patients/{id}/` | Patient summary + authorised visit history (later features). |
| `PATCH /api/patients/{id}/` | Correct demographics (Receptionist/Admin). Writes a correction-history row. |
| `POST /api/patients/{id}/duplicate-review/` | Resolve a duplicate warning (decision + reason recorded). |
| `GET /api/patients/{id}/corrections/` | Correction history (Admin/Receptionist; Doctor read-only where permitted). |

All endpoints require authentication; all mutations require the role in the spec's
permissions table; validation errors return structured field-level errors.

## Security approach

- Django session authentication (decided, ADR-001 / spec D-09): secure
  HttpOnly cookie, CSRF protection, server-side session revocation. No JWT
  in v1.
- Permission classes per endpoint + object-level checks; deny by default.
- MRN generation server-side only; never trust a client-supplied MRN.
  Format `MC-YYYY-NNNNNN`, sequence resets yearly (spec D-01).
- CNIC / B-Form stored encrypted at rest; uniqueness enforced on a
  deterministic hash of the 13 digits (the encrypted value cannot be
  queried); masked (last 4 digits) for all roles except Receptionist and
  Admin; never in logs, list views, or URLs; never searchable by design
  (spec D-06, D-12).
- Audit events for create / correct / status change / duplicate review / merge.
- No patient data in logs, URLs (beyond the MRN in a path), or error messages
  beyond what the caller's role may see.
- Rate-limit login; throttle registration endpoints against abuse.

## Test strategy

- **Unit**: MRN generation/uniqueness, duplicate-matching rule (name + DOB
  and CNIC / B-Form), validation rules (gender enum, 13-digit national ID,
  blood-group enum), status transitions.
- **Model/DB**: unique constraint, correction-history rows, no hard delete, migration applies cleanly from fresh setup.
- **API**: auth required (401 unauthenticated), permission allow/deny per role (Doctor create → 403), validation errors (400 with field errors), duplicate flow (warning → confirm-different → created; confirm-same → no new record), pagination.
- **Component**: registration form validation feedback, duplicate-warning dialog, empty search state.
- **E2E (Playwright)**: search → no match → register → MRN issued → search by MRN finds the patient.
- **Security**: object-level access (a user cannot fetch another role's forbidden record by changing an ID), audit events recorded.

Tests are written first (Constitution Principle V) and must fail before implementation.

## Risks for this feature

- **MRN format / required fields decided** (spec D-01, D-02, D-11, D-12,
  D-13) — the model and form are unblocked. Gender and CNIC / B-Form are
  required; blood group is optional.
- **Auth/RBAC (M01) not built yet** — this feature cannot be demonstrated without it. Mitigation: build M01 first or in parallel, with this feature's tests depending on it.
- **Duplicate rule is exact-only** — it will miss typo'd names (documented
  limitation, spec D-03). Mitigation: the phone-number secondary signal
  catches many of those cases, and the CNIC / B-Form match (D-12) catches
  the same person even when the name is spelled differently; log every
  warning and review with the owner after the first demo before considering
  fuzzy matching.
- **Scope creep into appointments** — WF-01 continues into booking; that is a separate feature. Mitigation: the spec's out-of-scope list is enforced at review.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
