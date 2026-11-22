# Feature Specification: Authentication & Role-Based Access Control (RBAC)

**Feature Branch**: `docs/medicore-all-specs` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — not yet approved by the owner. Decisions in the
"Decisions" section are taken from already-approved sources (Constitution
v1.0.0, ADR-001, Master Plan v1.0, Spec 001) and are binding as stated
there; everything else that needs a choice is listed under "Open Questions"
and must be decided before implementation.

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline), §4 P0
authentication and role-based access, §5 actors and permissions, §6 M01,
§7 WF-05, §8 FR-001 / FR-002 / FR-003 / FR-020, §12 security, privacy and
auditability; MediCore Constitution v1.0.0, Principles I, III, V, VII;
ADR-001 (ACCEPTED 2026-11-22); Spec 001, D-09 (session auth).

**Release status**: P0 core capability (Master Plan §4.2). This is not a
P1 candidate — authentication and RBAC are the foundation for every
protected workflow and must be implemented early.

## Overview

### Problem

Every MediCore workflow — patient registration, appointments, encounters,
billing — handles sensitive hospital data and must be limited to authorised
staff. Without a single, backend-enforced authentication and authorisation
mechanism, each feature would invent its own access checks (or have none),
and a user could reach another role's data simply by changing a URL or an
ID. This feature provides the one sign-in, the account lifecycle, the named
roles and permissions, and the audit trail that all other features build on.

This feature is deliberately narrow: sign in and out, staff account
lifecycle, role assignment, permission enforcement (including object-level
checks), and audit events for auth actions. It does not define the
feature-level permission tables — each feature specification owns its own
table (Spec 001 already defines the patient-registration table; Specs 003
and 004 define theirs). This spec defines the mechanism and the
cross-cutting rules every feature table must follow.

### Scope

**In scope**

- Sign in and sign out for staff users (Master Plan FR-001)
- Django session authentication: secure HttpOnly cookie, CSRF protection, no JWT in v1 (ADR-001, Spec 001 D-09)
- Account lifecycle: create, activate, disable, reset credentials (Master Plan FR-003, M01)
- Role and permission management by an authorised Admin (Master Plan FR-003, M01)
- Backend authorisation: named roles mapped to explicit permissions, deny by default, object-level checks (Master Plan FR-002, §5.1)
- Audit events for authentication and access-control actions (Master Plan FR-020, §12.4)
- A signed-in user changing their own password; an Admin resetting another user's password

**Out of scope**

- Patient portal, patient self-registration, or any non-staff login (Master Plan §4.3 / M13 — future module)
- Email-based self-service password reset (no email service is configured in v1; see Decisions D-07)
- Single sign-on, OAuth, or multi-factor authentication (not in the Master Plan; deferred, not decided)
- Feature-level permission tables — those live in each feature's own spec
- Department Manager and Auditor / Supervisor as separate login roles (Master Plan §5 lists them as actors; whether they are separate roles in v1 is Open Question OQ-008)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Sign in and sign out (Priority: P1)

A staff member signs in with their credentials, is taken to the workspace
their role permits, works, and signs out, ending the session server-side.

**Why this priority**: Nothing protected can be demonstrated without
sign-in. This is Master Plan §4, P0 core, and the first step of every
workflow (WF-01 step 1, WF-05 step 3).

**Independent Test**: A seeded staff account can sign in with correct
credentials, reach a protected page, sign out, and then be denied access
to that page until signing in again. No other feature needs to exist for
this to be demonstrated.

**Acceptance Scenarios**:

1. **Given** an active staff account, **When** they sign in with correct credentials, **Then** a session is created, they are recognised as signed in, and they see only the navigation their role permits.
2. **Given** a signed-in user, **When** they sign out, **Then** the session is ended server-side and a subsequent request to a protected page is denied (401/redirect to sign-in).
3. **Given** a sign-in attempt with wrong credentials, **When** it is submitted, **Then** sign-in fails with a generic error that does not say whether the account or the password was wrong, and a failed sign-in audit event is recorded.
4. **Given** an unauthenticated request to any protected API endpoint, **When** it is made, **Then** it is rejected (401) without revealing any data.
5. **Given** a signed-in user, **When** they request their own session/user details, **Then** they receive their username, full name, and assigned role(s) — and no other user's data.

### User Story 2 — Admin creates an account and assigns a role (Priority: P1)

An Admin creates a staff account, assigns an approved role, and activates
it. The new user signs in and receives access only to the functions and
records their role permits (WF-05 steps 1–3).

**Why this priority**: Accounts and roles are how the hospital onboards
staff; without them, RBAC cannot be exercised at all. This is Master Plan
M01 and FR-003.

**Independent Test**: An Admin creates a synthetic account with the
Receptionist role; that user signs in and can reach Receptionist functions
but is denied Admin functions by the backend.

**Acceptance Scenarios**:

1. **Given** a signed-in Admin, **When** they create an account with a unique username and assign the Receptionist role, **Then** the account exists in active status with that role, and an audit event records the creation and the role assignment.
2. **Given** a signed-in Admin, **When** they try to create an account with a username that already exists, **Then** the account is not created and a field-level error names the problem.
3. **Given** a newly created active account, **When** the user signs in, **Then** they receive access only to permitted functions and records for their role.
4. **Given** a signed-in non-Admin user, **When** they try to create an account or assign a role, **Then** the action is denied by the backend (403), not just hidden in the UI.
5. **Given** a signed-in user, **When** they try to grant themselves a role or raise their own privileges, **Then** the action is denied — a user cannot grant themselves privileges (Master Plan §5.1).

### User Story 3 — Disable an account and reset credentials (Priority: P2)

An Admin disables an account that is no longer authorised, or resets the
credentials of a user who cannot sign in. A disabled account cannot sign in,
and any active session it holds stops working.

**Why this priority**: Account lifecycle is the revocation path session auth
exists to support (ADR-001 rationale). A hospital must be able to remove
access when staff leave. This is Master Plan M01 and WF-05 step 5.

**Independent Test**: An Admin disables a synthetic account that is
signed in; that account's next request is denied and a fresh sign-in
attempt fails, while other users are unaffected.

**Acceptance Scenarios**:

1. **Given** a signed-in Admin, **When** they disable an active account, **Then** the account status becomes disabled, an audit event is recorded, and the disabled user can no longer sign in.
2. **Given** a disabled account with an active session, **When** that session is next used, **Then** the request is denied (the session no longer authorises access).
3. **Given** a signed-in Admin, **When** they re-activate a disabled account, **Then** the account can sign in again and an audit event records the re-activation.
4. **Given** a signed-in Admin, **When** they reset a user's password, **Then** the old password stops working, the new credential works, and an audit event records the reset (without recording the password itself).
5. **Given** a signed-in user, **When** they change their own password, **Then** the change requires their current password, and the new password applies from the next sign-in.
6. **Given** a signed-in Admin, **When** they try to disable their own account or remove their own Admin role, **Then** the action is refused with an understandable error (a hospital must not be left with no Admin by accident; see Open Question OQ-007 for the last-Admin rule).

### User Story 4 — Permissions are enforced on the backend, including object-level checks (Priority: P2)

A user who tries to perform an action outside their role, or to fetch a
record outside their permitted scope by changing an ID, is denied by the
backend — regardless of what the UI shows.

**Why this priority**: Backend enforcement is Constitution Principle III
and Master Plan §5.1. Frontend-only hiding is not access control. This is
Master Plan FR-002.

**Independent Test**: With two synthetic users of different roles, a
permission allow/deny test for each protected operation passes: allowed
actions succeed, denied actions return 403, and fetching an out-of-scope
record by ID returns 403/404 without revealing it.

**Acceptance Scenarios**:

1. **Given** a signed-in Receptionist, **When** they call an Admin-only endpoint, **Then** the backend returns 403.
2. **Given** a signed-in user, **When** they request a record outside their permitted scope by changing its ID in the URL, **Then** access is denied — object-level scope is checked, not only whether the user is signed in (Master Plan §5.1).
3. **Given** a user with no role assigned, **When** they sign in, **Then** they can reach nothing protected — access is denied by default (least privilege, Constitution Principle III).
4. **Given** a role assignment is changed for a user, **When** the change takes effect, **Then** their permitted functions change accordingly (the exact timing — immediately or at next sign-in — is Open Question OQ-005).
5. **Given** a denied access attempt, **When** it happens, **Then** the response is a generic permission error that does not reveal the record's existence or contents beyond what the caller may know.

### User Story 5 — Admin reviews the security audit trail (Priority: P3)

An Admin reviews the recorded security events — sign-ins, failures,
account changes, role changes — to answer "who did what, when".

**Why this priority**: Auditability is a constitution requirement
(Principle IV) and Master Plan FR-020 / §12.4. It is P3 because it is a
review activity, not a workflow blocker, but the events must be recorded
from the start or the history is lost.

**Independent Test**: After performing sign-ins, a failed sign-in, an
account creation, and a role change with synthetic data, an Admin can list
those audit events with actor, action, target, timestamp, and outcome.

**Acceptance Scenarios**:

1. **Given** auth and account actions have occurred, **When** an Admin lists audit events, **Then** each event shows actor, action, target, timestamp, and outcome.
2. **Given** audit events exist, **When** a non-Admin user tries to list them, **Then** access is denied by the backend.
3. **Given** an audit event is recorded, **When** it is inspected, **Then** it contains no password, token, or session value (Master Plan §12.4).

### Edge Cases

- What happens when a disabled user tries to sign in? Sign-in fails with the same generic error as a wrong password (so the response does not reveal that the account exists but is disabled).
- What happens when an Admin disables the last Admin account? The action is refused (see User Story 3, scenario 6); the exact last-Admin rule is Open Question OQ-007.
- What happens when a user's role is changed while they are signed in? Their permissions change according to the session policy — the timing is Open Question OQ-005.
- What happens when the same user signs in from two browsers? Whether concurrent sessions are allowed is Open Question OQ-009; by default the spec does not forbid it.
- What happens when a session cookie is presented after the server session has ended? The request is treated as unauthenticated (401).
- What happens when a password reset is requested by the user themselves? There is no email-based self-service reset in v1 (no email service configured); the user asks an Admin to reset it (Decisions D-07).
- What happens when sign-in fails repeatedly? Repeated failures are throttled (Master Plan §12.1); the threshold and lockout duration are Open Question OQ-003.
- What happens when a user has no role? They can sign in but reach nothing protected (deny by default, User Story 4, scenario 3).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST authenticate active authorised users before granting access to protected functions (Master Plan FR-001).
- **FR-002**: The system MUST end a session server-side on sign-out, so the session cannot be reused afterwards (Master Plan FR-001).
- **FR-003**: The system MUST reject unauthenticated access to all protected endpoints with 401, without revealing data (Master Plan FR-001).
- **FR-004**: The system MUST allow an authorised Admin to create staff accounts with a unique username, and to activate and disable them (Master Plan FR-003).
- **FR-005**: The system MUST allow an authorised Admin to assign and revoke roles for a user account; a user MUST NOT be able to grant themselves privileges or bypass approval (Master Plan FR-003, §5.1).
- **FR-006**: The system MUST map named roles to explicit permissions; business code MUST NOT rely on hard-coded role-name checks (Master Plan FR-002, §5.1).
- **FR-007**: The system MUST enforce authorisation on the backend for every protected operation, deny by default, and check object-level scope — not only whether the user is authenticated (Master Plan FR-002, §5.1; Constitution Principle III).
- **FR-008**: The system MUST record audit events for successful and failed sign-ins, sign-outs, account creation/activation/disable, role or permission changes, password resets, and password changes — each with actor, action, target, timestamp, and outcome, and without passwords, tokens, or session values (Master Plan FR-020, §12.4).
- **FR-009**: The system MUST allow a signed-in user to change their own password (requiring the current password) and an Admin to reset another user's password (Master Plan FR-003).
- **FR-010**: The system MUST use Django session authentication (secure HttpOnly cookie, CSRF protection) for the web app; it MUST NOT use JWT in v1 (Master Plan FR-001; ADR-001; Spec 001 D-09).
- **FR-011**: The system MUST throttle repeated failed sign-in attempts (Master Plan §12.1); the threshold and lockout duration are Open Question OQ-003.
- **FR-012**: The system MUST validate account fields on the backend before saving (unique username, required fields) and show field-level errors on the frontend (Master Plan FR-021).
- **FR-013**: The system MUST return understandable errors without exposing secrets, stack traces, or unnecessary user data (Master Plan FR-023).
- **FR-014**: The system MUST refuse an Admin disabling their own account or removing their own Admin role (see Open Question OQ-007 for the full last-Admin rule).
- **FR-015**: The system MUST NOT create a user account for a patient; a patient is a person receiving care and a user account is a staff identity that can authenticate — they are separate entities (Master Plan §7.1; Spec 001).

### Traceability to Master Plan requirements

| Master Plan FR | Covered by (this spec) |
|---|---|
| FR-001 Authentication | FR-001, FR-002, FR-003, FR-010, FR-011 |
| FR-002 Authorization | FR-006, FR-007 |
| FR-003 User administration | FR-004, FR-005, FR-009, FR-014 |
| FR-020 Audit trail | FR-008 |
| FR-021 Validation | FR-012 |
| FR-023 Error handling | FR-013 |

### Key Entities

- **User**: A staff identity that can authenticate. Distinct from a Patient (Master Plan §7.1). Key attributes: username (unique, required), full name, email (optional in v1 — no email is sent), password hash managed by Django (never plaintext), active status, assigned role(s), created-at, last sign-in.
- **Role**: A named grouping of permissions (Admin, Doctor, Nurse, Receptionist, Lab Technician, Pharmacist, Billing in v1). Roles are assigned to users by an Admin; permissions are explicit codes attached to roles, not hard-coded role-name checks.
- **Permission**: A single allowed action (e.g. `patients.register`, `appointments.create`). Checked on the backend before an operation runs.
- **Session**: A server-side Django session identified by a secure HttpOnly cookie. Ended on sign-out or when the account is disabled.
- **AuditEvent**: Who did what, when, to which record, and whether it succeeded. Audit records MUST NOT contain passwords, tokens, session values, or clinical content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A staff user can sign in, reach a protected page, sign out, and then be denied that page until signing in again.
- **SC-002**: An Admin can create an account, assign a role, and the new user receives only that role's access; a non-Admin attempting the same is denied by the backend (403).
- **SC-003**: 100% of protected endpoints in automated tests return 401 when unauthenticated and 403 for a signed-in user without the required permission.
- **SC-004**: Object-level access is denied in automated tests when a user requests a record outside their permitted scope by changing its ID.
- **SC-005**: Every sign-in (success and failure), sign-out, account change, role change, and password reset in test data has a corresponding audit event with actor and timestamp, containing no secret values.
- **SC-006**: A disabled account cannot sign in and its existing session stops authorising requests.
- **SC-007**: All P0 acceptance scenarios above pass against the implemented feature before it is considered complete.

## Permissions (cross-cutting — feature specs own their own tables)

This table states the auth/admin capabilities and summarises feature
access. The feature specifications are authoritative for their own rows:
Spec 001 for patients, Spec 003 for hospital setup, Spec 004 for
appointments. Later feature specs (encounters, lab, billing) will extend
the columns they need; this spec does not grant them anything in advance.

| Capability | Admin | Receptionist | Doctor | Nurse | Lab Technician | Pharmacist | Billing |
|---|---|---|---|---|---|---|---|
| Sign in to the system | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Change own password | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Create / activate / disable accounts | Yes | No | No | No | No | No | No |
| Assign / revoke roles | Yes | No | No | No | No | No | No |
| Reset another user's password | Yes | No | No | No | No | No | No |
| View security audit log | Yes | No | No | No | No | No | No |
| Manage departments, staff, services (Spec 003) | Yes | Read-only | Read-only | Read-only | Read-only | Read-only | Read-only |
| Register / correct patients (Spec 001) | Yes | Yes | Read-only | No in v1 | No in v1 | No in v1 | No in v1 |
| Manage appointments (Spec 004) | Yes | Yes | Own schedule | Read-only | No in v1 | No in v1 | No in v1 |

"Read-only" for hospital setup means the reference data needed for daily
work (departments, services); staff-profile contact detail is Admin-only
except for the staff member themselves (see Spec 003). Nurse / Lab /
Pharmacist / Billing have no patient-search access in v1, per Spec 001
(least privilege — their own feature specs will grant the search access
their workflows need, when those features are specified).

## Data fields (account)

Required: username (unique), full name, password (set at creation by the
Admin; the user changes it after first sign-in — see Open Question OQ-006
on forced change), assigned role(s) (at least one role for the account to
be usable; an account with no role can sign in but reaches nothing
protected). Optional: email (display/contact only in v1; no email is sent).
System fields: active status (active/disabled), created-by, created-at,
last sign-in timestamp.

Passwords are stored only as Django password hashes, never in plaintext
(Constitution Principle III). Passwords, tokens, and session values never
appear in logs, audit events, list views, URLs, or error messages.

## Assumptions

- The hospital is a single organisation; one deployment instance (Master Plan §2.4).
- All demo/test data is synthetic; no real staff or patient records are used.
- Display timezone for timestamps is Asia/Karachi; timestamps are stored in UTC (ADR-001).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner (2026-11-22); implementation may proceed on that basis.
- No email service is configured for this project in v1, so no workflow may depend on sending email.
- Django's built-in authentication (User, Group, Permission, session framework) is the implementation basis; staff organisational details live in the StaffProfile entity (Spec 003), not in the user account.

## Decisions

Decisions below are taken from already-approved sources and are binding;
they are not re-decided here. Anything not listed here is either in a
feature spec or an Open Question.

1. **D-01 — Django session authentication** (secure HttpOnly cookie, CSRF protection) for the web app; no JWT in v1. Source: ADR-001, Spec 001 D-09. Rationale: the product is a browser app for staff on one deployment — Django's built-in session auth is the simplest mature option, with server-side revocation (disable the account / end the session) that JWT would have to be hand-built to match.
2. **D-02 — Seven roles in v1**: Admin, Doctor, Nurse, Receptionist, Lab Technician, Pharmacist, Billing. Source: Master Plan §5 actors, Spec 001 permissions table. No separate Registration role in v1 (Spec 001 D-04). Department Manager and Auditor / Supervisor are Master Plan actors, not v1 login roles (see OQ-008).
3. **D-03 — Named roles mapped to explicit permissions; no hard-coded role-name checks** in business code. Source: Master Plan §5.1. Rationale: permission checks stay explicit, testable, and changeable without hunting role names through the codebase.
4. **D-04 — Deny by default; authorisation enforced on the backend, including object-level scope.** Source: Constitution Principle III, Master Plan §5.1. Frontend hiding is presentation only and is never access control.
5. **D-05 — Audit categories follow Master Plan §12.4**: authentication events (successful/failed sign-in, sign-out, account disable, password reset initiation) and access-control events (role or permission change, privileged configuration change), each with actor, action, target, timestamp, outcome — and no passwords, tokens, or clinical content.
6. **D-06 — A patient is not a user account.** Source: Master Plan §7.1. Patients never sign in; staff accounts are never patient records.
7. **D-07 — No email-based self-service password reset in v1.** Source: Master Plan §6 M01 ("optional password reset and account recovery workflow, subject to email configuration") — no email is configured, so the v1 reset path is Admin-initiated only. Email reset is deferred, not decided.
8. **D-08 — Staff organisational details live in StaffProfile (Spec 003), not in the user account.** Rationale: the user account is the authentication identity; the staff profile is the work identity (department, job title, blood group). Keeping them separate follows Master Plan §7.1 and §11.

## Open Questions

Genuinely undecided — do not guess; each needs an owner decision before
the implementation that depends on it.

- **OQ-001 — Sign-in identifier: username, email, or either?** Master Plan §11 lists "username/email" for a User without choosing. The account has a unique username; whether sign-in accepts the email address as well (or instead) is undecided.
- **OQ-002 — Session expiry: how long does a session last, and is there an idle timeout?** Master Plan §12.1 requires the session strategy to be documented (expiry, refresh, logout, revocation) but sets no durations. Needed before sign-in behaviour can be tested.
- **OQ-003 — Brute-force protection: after how many failed sign-ins is an account or address throttled/locked, and for how long?** Master Plan §12.1 requires throttling; the threshold and duration are undecided. The requirement to throttle (FR-011) stands regardless.
- **OQ-004 — Password policy: what rules beyond Django's defaults?** Minimum length, complexity, password expiry, and password-history rules are undecided. Django's default validators are the baseline until the owner decides otherwise.
- **OQ-005 — Role-change timing: does a role change take effect immediately for an active session, or only at the next sign-in?** Master Plan WF-05 step 4 says role changes take effect "according to session policy" — that policy is undecided.
- **OQ-006 — Forced password change: must a user change their password at first sign-in after an Admin creates or resets it?** Undecided; affects the account-creation flow.
- **OQ-007 — Last-Admin rule: what exactly prevents the hospital being left with no Admin?** Refusing self-disable/self-demotion is specified (FR-014); whether the system must also refuse disabling the last remaining Admin account, and how the first Admin is recovered if that ever happens, is undecided.
- **OQ-008 — Department Manager and Auditor / Supervisor: separate login roles, or Admin views?** Master Plan §5 lists them as actors with department-scoped summaries and read-only audit/report access. Whether they are roles in v1 or covered by Admin access is undecided.
- **OQ-009 — Multiple roles per user: may one user hold more than one role?** Master Plan §11 notes "a user may have one or more roles only if the approved access model permits it". Undecided for v1.
- **OQ-010 — First Admin bootstrap: who creates the first Admin account, and how?** There is no Admin before the first one exists. The mechanism (seeded account, setup command, installer step) and its credentials handling are undecided.
- **OQ-011 — Concurrent sessions: may one user be signed in from more than one browser/device at once?** Undecided; the spec does not forbid it by default.

## Deferred (not decided here)

- **Multi-factor authentication, SSO, OAuth**: not in the Master Plan; deferred until a real requirement exists.
- **Email-based password reset / account recovery**: deferred until an email service is configured (D-07).
- **Patient portal / patient login**: Master Plan M13, future module.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1; §§19–23 (deployment, risk register, governance/decision log, acceptance, open decisions) are listed in the contents but absent from the document. Explicitly deferred: they must be supplied or formally deferred before release planning (Phase 8), but they do not block this feature.
- **Feature-level permission tables**: defined by each feature's own spec (Specs 001, 003, 004 now; encounters, lab, billing later).
