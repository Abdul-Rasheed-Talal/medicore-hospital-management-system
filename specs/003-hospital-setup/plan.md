# Implementation Plan: Hospital Setup & Staff Management (003)

**Branch**: `docs/medicore-all-specs` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — spec is not yet approved by the owner. The open
questions in the spec (OQ-001–OQ-008) must be decided before the
implementation that depends on them; the plan records which parts are
blocked by which question (see Risks).

## Summary

Build hospital setup (Master Plan §4 P0, §6 M02, §8 FR-004): Admin-managed
departments, staff profiles (with the optional blood-group field decided
by the owner in Spec 001 D-13), service catalog with categories and visit
types, staff status, and the reference-data protection rule — no deleting
records used by historical transactions, deactivate instead. This is the
reference data that appointments (Spec 004) and later modules link to, so
it is built before them and kept small for the MVP.

Technical approach: modular monolith — React + TypeScript + Vite + Tailwind +
shadcn/ui frontend, Django + DRF + PostgreSQL backend, `organization` Django
app, REST API under `/api/departments/`, `/api/staff/`, `/api/services/`,
`/api/visit-types/`, deletion refused by the backend when references exist,
audit events for setup changes. Stack is ACCEPTED (ADR-001, owner approval
2026-11-22). Depends on Spec 002 (`accounts` for roles, `audit` for audit
events).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided;
verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19 + Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing Library (frontend), Playwright (E2E, one journey: create department → create staff profile → create service → verify lists)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2 seconds under a small demo dataset and local test conditions (Master Plan NFR-05, provisional)

**Constraints**: Synthetic data only; no real staff records; secrets via environment only; backend validation is authoritative (frontend validation is usability only); no hard deletion of referenced records or staff profiles; no price field on services in v1

**Scale/Scope**: Single hospital, single deployment; tens of staff users; tens of departments/services in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a draft; implementation must wait for owner approval and for the blocking open questions (OQ-001, OQ-004) to be decided. CONDITIONAL PASS. |
| II. Modular architecture | `organization` Django app, separate frontend pages/components, business rules in services — not duplicated in views/serializers. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced (Admin manages, others read-only); staff contact details and blood group restricted by role; synthetic data only; no secrets in code. PASS by design. |
| IV. Data integrity | PostgreSQL, unique codes (database), foreign keys, transactions for create + audit, migrations version-controlled, no hard delete of referenced records. PASS by design. |
| V. Test-first | Deletion-refusal tests, permission allow/deny tests, validation tests, E2E journey test are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; ADR-001 records the stack decision; API contract documented. PASS by design. |
| VIII. Scope discipline | Departments, staff, services, categories, visit types, and the deletion rule only. Prices, shifts, leave, payroll are separate/deferred. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/003-hospital-setup/
├── spec.md              # Feature specification (draft 2026-11-22)
├── plan.md              # This file
└── tasks.md             # Phase 2 output (NOT created yet)
```

No `research.md`: no new research decision was needed — the stack is
already decided in ADR-001, the blood-group field in Spec 001 D-13, and
the remaining choices are recorded as open questions in the spec, not
resolved by research. No `data-model.md`: the data model sketch below
lives in this plan.

### Source Code (repository root)

```text
backend/
├── config/              # Django settings (env-based), urls
├── apps/
│   ├── accounts/        # Users, roles (prerequisite, Spec 002)
│   ├── audit/           # Audit events (prerequisite, Spec 002)
│   ├── organization/    # Departments, staff profiles, services (this feature)
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py  # Reference-data protection, status changes
│   │   ├── views.py     # DRF viewsets, permission-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── patients/        # Patient identity (Spec 001; consumes nothing from this app yet)
└── tests/

frontend/
├── src/
│   ├── components/      # DepartmentForm, StaffForm, ServiceForm, StaffDirectory
│   ├── pages/           # Administration (departments, staff, services)
│   ├── services/        # API client for /api/departments/, /api/staff/, /api/services/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` + `docs/`.
Backend apps are created only when their scope is approved — `organization`
is created with this feature; it depends on `accounts` (roles, user link)
and `audit` (Spec 002), which must land first or alongside it. Do not
create every app in Master Plan §10.4 at initialisation.

## Data model sketch

| Entity | Key fields / notes |
|---|---|
| Department | id (UUID PK), name (required), code (required, unique, indexed), description (optional), is_active (bool), created_by (FK → User), created_at, updated_at |
| StaffProfile | id (UUID PK), staff_identifier (format: spec OQ-001 — placeholder field until decided), full_name (required), job_title (required), department (FK → Department, required for Doctor/Nurse/Lab Technician roles, optional otherwise), role (link to Spec 002 role/group, required), user (FK → User, optional, unique — at most one profile per account and one account per profile), phone (optional), email (optional), blood_group (enum, optional: A+, A-, B+, B-, AB+, AB-, O+, O-, Spec 001 D-13), status (enum: Active / Inactive), created_by (FK → User), created_at, updated_at |
| Service | id (UUID PK), name (required), code (required, unique, indexed), category (FK → ServiceCategory, required), department (FK → Department, optional), is_active (bool), created_by (FK → User), created_at, updated_at. No price field in v1 (spec D-07). |
| ServiceCategory | id (UUID PK), name (required, unique), is_active (bool), created_by, created_at |
| VisitType | id (UUID PK), name (required, unique), is_active (bool), created_by, created_at |
| StaffStatusChange | id (UUID PK), staff_profile (FK → StaffProfile), old_status, new_status, reason (required), author (FK → User), created_at. Append-only history, like PatientCorrection in Spec 001. |
| AuditEvent (shared, `audit` app) | See Spec 002 plan: actor, action (e.g. `organization.department_create`, `organization.staff_status_change`, `organization.delete_refused`), target, timestamp, outcome, non-sensitive metadata only. |

Constraints: department code unique (database); service code unique
(database); category/visit-type name unique (database); one user ↔ at
most one staff profile (database unique on the link); department required
for clinical roles (backend validation); blood group validated against
the eight values (backend); status changes recorded with a reason, never
silent. Deletion protection is enforced in the service layer, not only in
the UI: a delete request for a referenced record is refused with an
understandable error; an unreferenced record may be deleted by an Admin.

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `GET /api/departments/` | List departments (all signed-in staff, read-only; filter `?active=`). Paginated. |
| `POST /api/departments/` | Create a department (Admin). Returns 201; 400 on duplicate code / missing fields. |
| `GET/PATCH /api/departments/{id}/` | Department detail / edit (Admin for PATCH). |
| `DELETE /api/departments/{id}/` | Delete only if unreferenced (Admin); 409 with an understandable error if referenced. Deactivation is via PATCH `is_active=false`. |
| `GET /api/staff/` | List staff profiles (role-filtered fields; filter `?department=&status=&role=`). Paginated. |
| `POST /api/staff/` | Create a staff profile (Admin). Returns 201. |
| `GET/PATCH /api/staff/{id}/` | Staff detail / edit (Admin for PATCH; a staff member may view their own full detail). |
| `PATCH /api/staff/{id}/status/` | Change staff status with a required reason (Admin). Writes a StaffStatusChange row. |
| `GET /api/staff/{id}/status-history/` | Status history (Admin; own profile for the staff member). |
| `GET /api/services/` | List services (all signed-in staff, read-only; filter `?category=&department=&active=`). Paginated. |
| `POST /api/services/` | Create a service (Admin). Returns 201; 400 on duplicate code. |
| `GET/PATCH/DELETE /api/services/{id}/` | Service detail / edit / delete-if-unreferenced (Admin for mutations; delete refused with 409 if referenced). |
| `GET/POST /api/service-categories/` and `GET/POST /api/visit-types/` | Reference-list management (Admin for POST/PATCH/DELETE; read for all signed-in staff). |

All endpoints require authentication; all mutations require Admin (see the
spec's permissions table); validation errors return structured field-level
errors. Staff contact details and blood group are excluded from list
responses for non-Admin callers (role-filtered serialisation).

## Security approach

- Django session authentication (decided, ADR-001 / Spec 002): secure HttpOnly cookie, CSRF protection, server-side session revocation. No JWT in v1.
- Permission classes per endpoint; deny by default; Admin-only mutations enforced on the backend.
- Role-filtered serialisation: phone, email, and blood group are returned only to Admin and to the staff member themselves; other roles receive name, department, job title, and system role only.
- No staff personal data in logs, URLs (beyond internal IDs in a path), or error messages beyond what the caller's role may see.
- Audit events for create / edit / status change / deactivation / refused deletion.
- Rate-limit/throttle setup endpoints against abuse (same approach as Spec 002).

## Test strategy

- **Unit**: blood-group enum validation, department-required-for-clinical-roles rule, status-transition rules, deletion-refusal rule (referenced vs unreferenced).
- **Model/DB**: unique code constraints, one-to-one user↔profile link, migration applies cleanly from fresh setup.
- **API**: auth required (401 unauthenticated), permission allow/deny per role (non-Admin create/edit/delete → 403), validation errors (400 with field errors), delete-referenced → 409 with understandable error, deactivate hides from new selections but preserves existing links, role-filtered fields (non-Admin list omits phone/email/blood group), pagination and filters.
- **Component**: department/staff/service forms with validation feedback, staff directory with role-appropriate columns, deactivation confirm dialog.
- **E2E (Playwright)**: Admin creates a department → creates a staff profile in it (with blood group) → creates a service → Receptionist sees the department and service in read-only lists.
- **Security**: object-level access (a user cannot fetch another staff member's contact details by changing an ID), audit events recorded.

Tests are written first (Constitution Principle V) and must fail before implementation.

## Risks for this feature

- **Open questions block parts of implementation**: OQ-001 (staff identifier format) blocks the staff model field; OQ-004 (seed data) blocks demo setup. Mitigation: decide OQ-001 and OQ-004 with the owner before implementation starts; keep the staff identifier as a plain unique field so the format decision is a validation change, not a schema change.
- **Spec 002 dependency**: setup endpoints assume signed-in users with roles. Mitigation: build Spec 002 first or in parallel, with this feature's tests depending on it.
- **Deletion rule is easy to get wrong**: a missed reference (e.g. a future module's foreign key) would allow a delete that orphans history. Mitigation: enforce the check in the service layer with an explicit reference registry per entity, and test every reference that exists at the time; re-check the rule when each new module lands.
- **Price question (OQ-003)**: if billing later needs a price on services, the catalog gains a field. Mitigation: no price field in v1 by decision (spec D-07); adding it later is a migration, not a redesign.
- **Scope creep into scheduling/HR**: shifts, leave, and payroll are explicitly out of scope. Mitigation: the spec's out-of-scope list is enforced at review.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
