# Implementation Plan: Prescriptions (006)

**Branch**: `docs/medicore-all-specs` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — spec not yet approved by the owner. **Committed module
M7** (owner decision 2026-11-22: Prescription is its own separate module).
Do not implement until the owner approves this spec.

## Summary

Build prescriptions (Master Plan §6 M06, §8 FR-013): a Doctor records a
structured prescription (name, strength, dosage, route, frequency,
duration, instructions) linked to a finalised encounter and to themself as
prescriber, and moves it through draft / finalized / cancelled states. A
finalised prescription is never edited in place — change means cancel with
a reason and reissue. The feature contains no treatment recommendations and
no automated dosing decisions of any kind.

Technical approach: modular monolith — React + TypeScript + Vite + Tailwind
+ shadcn/ui frontend, Django + DRF + PostgreSQL backend, `prescriptions`
Django app, REST API under `/api/prescriptions/`, status transitions
enforced by a database constraint plus service-layer rules, audit events for
create/finalise/cancel. Stack is ACCEPTED (ADR-001, owner approval
2026-11-22); session auth is the decided auth strategy (Spec 001 D-09).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided,
ADR-001; verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19 + Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing Library (frontend), Playwright (E2E, one journey: finalised encounter → prescription → finalise)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2 seconds under a small demo dataset and local test conditions (Master Plan NFR-05, provisional)

**Constraints**: Synthetic data only; no real patient records; secrets via environment only; backend validation is authoritative (frontend validation is usability only); no hard deletion of prescriptions; no treatment recommendations or automated dosing decisions anywhere in the feature; no clinical content in logs, audit metadata, or error messages beyond what the caller's role may see

**Scale/Scope**: Single hospital, single deployment; tens of staff users; thousands of patient records, encounters, and prescriptions in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a draft, committed module M7; implementation waits for owner approval. PASS when approved. |
| II. Modular architecture | `prescriptions` Django app, separate frontend pages/components, business rules in services — not duplicated in views/serializers. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced; least privilege (prescriber-only mutations; no Receptionist/Lab/Billing access; Admin no clinical content by default); synthetic data only. PASS by design. |
| IV. Data integrity | PostgreSQL, status constraint, transactions for finalise/cancel + audit, migrations version-controlled, no hard delete, cancel-and-reissue preserves history. PASS by design. |
| V. Test-first | Permission allow/deny tests, status-transition tests, validation tests, E2E journey test are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; API contract documented. PASS by design. |
| VIII. Scope discipline | Prescription records only. No recommendations, no dosing logic, no dispensing, no interaction/allergy checks. PASS — the forbidden behaviours are named in the spec (FR-013d). |

## Project Structure

### Documentation (this feature)

```text
specs/006-prescriptions/
├── spec.md              # Feature specification (draft 2026-11-22, module M7)
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
│   ├── prescriptions/   # Prescription records
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py  # Create, finalise, cancel (status rules live here)
│   │   ├── views.py     # DRF viewsets, permission-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── audit/           # Audit events (shared)
└── tests/

frontend/
├── src/
│   ├── components/      # PrescriptionForm, PrescriptionHistory, PrescriptionDetail
│   ├── pages/           # Encounter prescriptions, prescription detail
│   ├── services/        # API client for /api/prescriptions/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` + `docs/`.
Backend apps are created only when their scope is approved — `accounts`,
`patients`, and `encounters` are prerequisites for this feature. Do not
create every app in Master Plan §10.4 at initialisation.

## Data model sketch

**Prescription**: id (UUID PK); encounter (FK → Encounter, required);
patient (FK → Patient, required, denormalised from the encounter for
querying — always equals the encounter's patient, enforced in the service
layer); prescriber (FK → User, Doctor role, required); medication_name
(Text, required); strength (Text, required); dosage (Text, required);
route (Text, required); frequency (Text, required); duration (Text,
required); instructions (Text, optional); status (Enum: Draft / Finalized /
Cancelled); created_by, created_at, finalised_by (nullable), finalised_at
(nullable), cancelled_by (nullable), cancelled_at (nullable),
cancellation_reason (Text, required when cancelling). Constraints: status
transitions Draft → Finalized, Draft → Cancelled, Finalized → Cancelled
only, enforced in the service layer and by a database check constraint;
no delete; encounter must be Finalized at creation (P-02).

**AuditEvent** (shared, from the `audit` app): actor, action (e.g.
`prescription.create`, `prescription.finalize`, `prescription.cancel`),
target_type / target_id (Prescription, the prescription id), timestamp,
outcome, metadata (limited, non-sensitive context only — never a
recommendation or dosing logic; there is none in this feature).

Relationships: one Encounter → many Prescriptions; one Patient → many
Prescriptions (via encounters); one User (Doctor) → many Prescriptions (as
prescriber). Patient is distinct from User (Master Plan §7.1). Indexes:
encounter, patient, prescriber, status, created_at. No medication catalog
table in v1 (P-05).

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `POST /api/prescriptions/` | Create a prescription (Doctor). Body: encounter (must be Finalized), structured medication fields. Returns 201 with Draft prescription, or 400/403 per the spec's rules. |
| `GET /api/prescriptions/?encounter=&patient=&status=&page=` | List prescriptions in the caller's authorised scope (Doctor: own). Paginated. |
| `GET /api/prescriptions/{id}/` | Prescription detail with prescriber and timestamps. |
| `PATCH /api/prescriptions/{id}/` | Edit own draft (Doctor, prescriber only). Refused on a finalised or cancelled prescription. |
| `POST /api/prescriptions/{id}/finalize/` | Finalise own draft (Doctor, prescriber only). |
| `POST /api/prescriptions/{id}/cancel/` | Cancel own draft or finalised prescription (Doctor, prescriber only; reason required). |

All endpoints require authentication; all mutations require the role in the
spec's permissions table; validation errors return structured field-level
errors. No endpoint suggests, recommends, or calculates any medication,
dose, or duration.

## Security approach

- Django session authentication (decided, ADR-001 / Spec 001 D-09): secure
  HttpOnly cookie, CSRF protection, server-side session revocation. No JWT
  in v1.
- Permission classes per endpoint + object-level checks (prescriber-only for
  edit/finalise/cancel; own-prescriptions scope for Doctor reads); deny by
  default.
- Prescription creation server-side only; never trust a client-supplied
  prescriber, status, or timestamp.
- Patient CNIC / B-Form is never exposed through prescription endpoints: it
  is encrypted at rest, visible in full only to Receptionist/Admin, masked
  otherwise, and never searchable (Spec 001 D-06, D-12).
- Audit events for create / finalise / cancel.
- Rate-limit login; throttle prescription endpoints against abuse.

## Test strategy

- **Unit**: status-transition rules (draft editable, finalised locked,
  cancelled terminal, cancel requires reason), validation rules (all six
  structured fields required, instructions optional).
- **Model/DB**: status constraint, encounter-must-be-finalised rule,
  no hard delete, migration applies cleanly from fresh setup.
- **API**: auth required (401 unauthenticated), permission allow/deny per
  role (Receptionist create → 403; second Doctor finalise → 403),
  validation errors (400 with field errors), standalone prescription
  refused, prescription on draft encounter refused, cancel-and-reissue
  flow.
- **Component**: prescription form validation feedback, draft/finalise/
  cancel states, prescription-history display.
- **E2E (Playwright)**: finalised encounter → create prescription → finalise
  → view in encounter history; cancel with reason → status Cancelled.
- **Security**: object-level access (a Doctor cannot fetch another Doctor's
  prescription by changing an ID unless authorised); review that no
  endpoint, field, or UI element recommends a medication, dose, or
  duration (FR-013d).

Tests are written first (Constitution Principle V) and must fail before implementation.

## Risks for this feature

- **Not yet approved** — the spec is a draft awaiting the owner's approval.
  Mitigation: no implementation work starts until it is approved.
- **No medication catalog (Q-001)** — free-text medication fields risk
  inconsistent spelling. Mitigation: accepted for v1 (P-05); a catalog is
  a later spec decision, not an implementation improvisation.
- **No safety checking (Q-003)** — interaction/allergy/duplicate checks are
  out of scope and must not be half-built. Mitigation: the spec forbids
  them explicitly (FR-013d); any future check needs its own spec and a
  clinical knowledge source.
- **Auth/RBAC (M01), patients (001), encounters (005) not built yet** — this
  feature cannot be demonstrated without them. Mitigation: build in
  dependency order (M01 → 001 → 005 → 006).
- **Scope creep into dispensing/pharmacy (M12)** — a future module.
  Mitigation: the spec's out-of-scope list is enforced at review.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
