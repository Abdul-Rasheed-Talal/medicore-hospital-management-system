# Implementation Plan: Authentication & RBAC (002)

**Branch**: `docs/medicore-all-specs` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — spec is not yet approved by the owner. The open
questions in the spec (OQ-001–OQ-011) must be decided before the
implementation that depends on them; the plan records which parts are
blocked by which question (see Risks).

## Summary

Build authentication and RBAC (Master Plan §4 P0, §5, §6 M01, §7 WF-05,
§8 FR-001/002/003/020): staff sign in/out with Django session auth,
Admin-managed account lifecycle (create/activate/disable/reset), named
roles mapped to explicit permissions, backend authorisation including
object-level checks, and audit events for auth actions. This is the
foundation every other feature depends on — Spec 001 (patient
registration) cannot be demonstrated end-to-end until this exists — so it
is built first, as the scaffold's first feature slice.

Technical approach: modular monolith — React + TypeScript + Vite + Tailwind +
shadcn/ui frontend, Django + DRF + PostgreSQL backend, `accounts` Django app
(Django built-in User/Group/Permission + session framework) and shared
`audit` app, REST API under `/api/auth/` and `/api/users/`, permission
checks as DRF permission classes backed by named permission codes, deny by
default. Stack is ACCEPTED (ADR-001, owner approval 2026-11-22); session
auth is the decided auth strategy (spec D-01, Spec 001 D-09).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided;
verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19 + Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing Library (frontend), Playwright (E2E, one journey: sign in → protected page → sign out → denied)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2 seconds under a small demo dataset and local test conditions (Master Plan NFR-05, provisional)

**Constraints**: Synthetic data only; no real staff or patient records; secrets via environment only; backend validation is authoritative (frontend validation is usability only); passwords never stored in plaintext, never logged; no JWT in v1; no email service configured in v1

**Scale/Scope**: Single hospital, single deployment; tens of staff users; seven roles in v1

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a draft; implementation must wait for owner approval and for the blocking open questions (OQ-002, OQ-003, OQ-010) to be decided. CONDITIONAL PASS. |
| II. Modular architecture | `accounts` Django app, shared `audit` app, permission logic in permission classes/services — not duplicated in views/serializers. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced incl. object-level; deny by default; least privilege; synthetic data only; no secrets in code; no passwords/tokens in logs or audit events. PASS by design. |
| IV. Data integrity | PostgreSQL, unique username constraint, transactions for account + role + audit writes, migrations version-controlled, no hard delete of accounts (disable instead). PASS by design. |
| V. Test-first | Permission allow/deny tests, object-level tests, session tests, audit tests are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, errors not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; ADR-001 records the stack decision; API contract documented. PASS by design. |
| VIII. Scope discipline | Sign-in/out, lifecycle, roles, enforcement, audit only. Patient portal, SSO/MFA, email reset are separate/deferred. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/002-auth-rbac/
├── spec.md              # Feature specification (draft 2026-11-22)
├── plan.md              # This file
└── tasks.md             # Phase 2 output (NOT created yet)
```

No `research.md`: no new research decision was needed — the stack and
session strategy are already decided in ADR-001 and Spec 001 D-09, and
the remaining choices are recorded as open questions in the spec, not
resolved by research. No `data-model.md`: the data model sketch below is
small (Django built-in auth models plus the shared AuditEvent) and lives
in this plan.

### Source Code (repository root)

```text
backend/
├── config/              # Django settings (env-based), urls
├── apps/
│   ├── accounts/        # Users, roles, permissions, session auth (this feature)
│   │   ├── models.py    # Uses Django built-in User/Group/Permission; no custom user model in v1
│   │   ├── serializers.py
│   │   ├── services.py  # Account lifecycle, role assignment, session handling
│   │   ├── permissions.py  # DRF permission classes from named permission codes
│   │   ├── views.py     # DRF viewsets, permission-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── audit/           # Audit events (shared; created with this feature)
└── tests/

frontend/
├── src/
│   ├── components/      # SignInForm, UserForm, RoleAssign, AuditLogList
│   ├── pages/           # Sign-in, user administration, audit log
│   ├── services/        # API client for /api/auth/ and /api/users/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` + `docs/`.
`accounts` and `audit` are created with this feature — they are the
prerequisite for every later feature (Spec 001's `patients` app depends
on them). Do not create every app in Master Plan §10.4 at initialisation;
each app is created only when its scope is approved.

## Data model sketch

Built on Django's built-in auth models — no custom user model in v1
(spec D-08: staff organisational details live in StaffProfile, Spec 003,
not in the user account). The trade-off is recorded under Risks: switching
to a custom user model later is expensive, so if the owner ever wants
email-as-username or extra account fields, that decision must come before
the first migration that other apps depend on.

| Entity | Key fields / notes |
|---|---|
| User (Django `auth.User`) | username (unique), first/last name, email (optional, v1 display only), password hash (Django, never plaintext), `is_active` (disable = `is_active=False`, never hard delete), `date_joined`, `last_login` |
| Group (≈ Role) | Django Group named for each v1 role (Admin, Doctor, Nurse, Receptionist, Lab Technician, Pharmacist, Billing). A user holds their role(s) via group membership. |
| Permission | Django Permission objects plus named custom permission codes per app (e.g. `patients.register`); attached to groups, never checked by role-name string in business code. |
| Session (Django) | Server-side session, HttpOnly cookie; ended on sign-out; invalidated when the account is disabled. |
| AuditEvent (shared, `audit` app) | id (UUID PK), actor (FK → User), action (e.g. `auth.sign_in`, `auth.sign_in_failed`, `auth.sign_out`, `accounts.create`, `accounts.disable`, `accounts.role_change`, `accounts.password_reset`), target_type / target_id, timestamp (UTC), outcome (success/failure), metadata (limited, non-sensitive only — never passwords, tokens, or session values). |

Constraints: username unique (database); account + role changes and
their audit events written in one transaction where they belong together;
disabled accounts (`is_active=False`) cannot authenticate and their
sessions stop authorising requests.

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `POST /api/auth/login/` | Sign in with credentials. Returns the session (HttpOnly cookie) and the current-user summary; 401 with a generic error on failure (no account-vs-password distinction). |
| `POST /api/auth/logout/` | Sign out. Ends the session server-side. |
| `GET /api/auth/me/` | Current signed-in user: username, full name, role(s). 401 when unauthenticated. |
| `POST /api/auth/change-password/` | Signed-in user changes own password; requires the current password. |
| `GET /api/users/` | List staff accounts (Admin). Paginated, role-filtered fields. |
| `POST /api/users/` | Create an account + assign role(s) (Admin). Returns 201; 400 on duplicate username / invalid fields. |
| `GET /api/users/{id}/` | Account detail (Admin; a user may view their own). |
| `PATCH /api/users/{id}/` | Update account / activate / disable / assign or revoke roles (Admin). Self-disable and self-demotion refused. |
| `POST /api/users/{id}/reset-password/` | Admin resets a user's password (Admin). |
| `GET /api/audit/events/` | List audit events (Admin). Filterable by actor/action/date; paginated. |

All endpoints require authentication except login; all mutations require
the role in the spec's permissions table; validation errors return
structured field-level errors. CSRF protection applies to all
state-changing requests (DRF session authentication).

## Security approach

- Django session authentication (decided, ADR-001 / spec D-01): secure HttpOnly session cookie, CSRF protection, server-side session revocation (sign-out, account disable). No JWT in v1.
- Cookie flags: `SESSION_COOKIE_HTTPONLY` on, `SESSION_COOKIE_SECURE` on in any hosted (HTTPS) environment, `SESSION_COOKIE_SAMESITE=Lax`; CSRF token via Django's csrf cookie + header for state-changing requests.
- Passwords stored only as Django hashes; Django's default password validators are the baseline until OQ-004 is decided; passwords never in logs, audit events, URLs, or error messages.
- Permission classes per endpoint + object-level checks; deny by default; no hard-coded role-name checks in business code (spec D-03).
- Throttling on the login endpoint (spec FR-011); exact threshold/lockout is OQ-003 — implement the throttle mechanism with the threshold as a setting, so deciding OQ-003 is a configuration change, not a code change.
- Audit events for every auth/account action (spec FR-008).
- Rate-limit login; throttle account-admin endpoints against abuse.
- Debug mode and detailed error traces disabled in hosted demonstration environments.

## Test strategy

- **Unit**: password change/reset rules, self-disable refusal, role-assignment rules, session invalidation on disable.
- **Model/DB**: unique username constraint, `is_active` behaviour, group/permission assignment, migration applies cleanly from fresh setup.
- **API**: auth required (401 unauthenticated), permission allow/deny per role for every endpoint (Admin-only create → 403 for Receptionist), validation errors (400 with field errors), generic error on failed sign-in, sign-out invalidates the session, disabled account cannot sign in and its session stops working.
- **Security**: object-level access (a user cannot fetch another user's forbidden record by changing an ID), self-privilege-escalation refused, audit events recorded with no secret values, CSRF enforced on state-changing requests, login throttling.
- **Component**: sign-in form validation feedback, user-admin form, audit-log list with empty state.
- **E2E (Playwright)**: sign in → protected page → sign out → protected page denied; Admin creates a Receptionist account → that user signs in with Receptionist-only access.
- **Security**: session cookie flags (HttpOnly, Secure in hosted env), no password/token in logs or audit metadata.

Tests are written first (Constitution Principle V) and must fail before implementation.

## Risks for this feature

- **Open questions block parts of implementation**: OQ-002 (session expiry) and OQ-003 (lockout) block finalising sign-in behaviour and its tests; OQ-010 (first-Admin bootstrap) blocks the first deployment's login; OQ-005 (role-change timing) blocks the role-change test. Mitigation: decide OQ-002, OQ-003, OQ-005, OQ-010 with the owner before implementation starts; build the throttle and session handling so the undecided values are settings, not code.
- **No custom user model in v1**: switching later (e.g. if OQ-001 decides email sign-in) is expensive once other apps reference the user model. Mitigation: decide OQ-001 early; if email sign-in is wanted, revisit this choice before the first migration other apps depend on.
- **This feature gates everything else**: Spec 001 cannot be demonstrated end-to-end until M01 exists. Mitigation: build M01 first, as the scaffold's first feature slice, with Spec 001's tests depending on it.
- **Scope creep into feature permissions**: each feature spec owns its table; this feature must not pre-grant encounters/lab/billing access. Mitigation: the spec's permissions table grants nothing to later features in advance.
- **Seed/demo accounts**: demo data needs staff accounts for every role. Mitigation: seed script with synthetic accounts and documented credentials that exist only in the demo/dev environment, never committed as real credentials.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
