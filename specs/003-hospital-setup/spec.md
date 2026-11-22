# Feature Specification: Hospital Setup & Staff Management

**Feature Branch**: `docs/medicore-all-specs` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — not yet approved by the owner. The staff blood-group
field is already decided by owner instruction (Spec 001 D-13); everything
else that needs a choice is listed under "Open Questions" and must be
decided before implementation.

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline), §4 P0
hospital setup, §6 M02, §8 FR-004, §11 data architecture; MediCore
Constitution v1.0.0, Principles I, II, III, IV, V, VII; ADR-001 (ACCEPTED
2026-11-22); Spec 001 D-13 (blood group optional for staff); Spec 002
(auth/RBAC — accounts, roles, audit).

**Release status**: P0 core capability (Master Plan §4.2). This is not a
P1 candidate — hospital setup provides the reference data (departments,
staff, services) that appointments, encounters, and later modules depend
on, and must be kept small for the MVP.

## Overview

### Problem

Appointments need a provider and a department, encounters need a
clinician, and billing (later) needs a service catalog — but none of those
can be entered reliably if departments, staff, and services are free text
typed differently on every screen. Hospital setup creates the controlled
reference data other modules link to: departments, staff profiles, and the
service catalog (including visit types and service categories). It also
protects that reference data: a department or service that historical
records point to must not be deletable out from under them.

This feature is deliberately narrow: departments, staff profiles, service
catalog, and the reference-data protection rule. It does not include user
accounts and roles (Spec 002 — a staff profile is the work identity, the
user account is the sign-in identity; the two are linked, not the same),
shift/rota scheduling, leave, payroll, or billing prices (billing is a
later P1-candidate module).

### Scope

**In scope**

- Manage departments (Master Plan FR-004, M02)
- Manage staff profiles, including the OPTIONAL blood group field for all staff (owner decision, Spec 001 D-13), and link each profile to a department, a job title, a system role, and (where applicable) a user account (M02)
- Manage the service catalog and the limited reference lists: service categories and visit types (M02)
- Staff status (Active / Inactive in v1)
- Reference-data protection: no deleting records used by historical transactions — deactivate instead (M02, Master Plan FR-022)
- Audit events for setup changes (Master Plan FR-020)

**Out of scope**

- User accounts, passwords, roles, and sign-in (Spec 002)
- Appointment scheduling itself (Spec 004 — it consumes departments, staff, and services)
- Service prices / charges (billing, Master Plan M09, is a P1 candidate, not specified yet — see Open Question OQ-003)
- Shift/rota scheduling, leave management, payroll, organisational hierarchy
- Multi-hospital tenancy (Master Plan §4.3)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Admin creates and manages departments (Priority: P1)

An Admin sets up the hospital's departments (e.g. Outpatient, Laboratory)
so that staff, services, and appointments can be linked to them.

**Why this priority**: Departments are the reference data every other
module points to. Without them, staff cannot be organised and
appointments cannot be department-scoped. This is Master Plan §4, P0
core, and M02.

**Independent Test**: An Admin can create a department with a unique code,
list departments, edit one, and deactivate one — with no other feature
needing to exist.

**Acceptance Scenarios**:

1. **Given** a signed-in Admin, **When** they create a department with a name and a unique code, **Then** the department exists in active status with created-by / created-at audit fields.
2. **Given** a signed-in Admin, **When** they try to create a department with a code that already exists, **Then** the department is not created and a field-level error names the problem.
3. **Given** a signed-in Admin, **When** they try to create a department with a missing required field, **Then** the department is not created and a field-level error names the missing field.
4. **Given** a signed-in non-Admin user, **When** they try to create, edit, or deactivate a department, **Then** the action is denied by the backend (403), not just hidden in the UI.
5. **Given** departments exist, **When** a signed-in staff member lists them, **Then** they see the active departments (read-only) for use in daily work.

### User Story 2 — Admin creates a staff profile (Priority: P1)

An Admin creates a staff profile for a clinician or other staff member:
name, job title, department, system role, optional blood group, and a
link to their user account where they sign in.

**Why this priority**: Staff profiles are what appointments book against
(a provider) and what work queues are assigned to. Without them, M04
appointments have no provider to schedule. This is Master Plan M02.

**Independent Test**: An Admin can create a staff profile for a Doctor in
a department, link it to a user account, record an optional blood group,
and see the profile in the staff directory.

**Acceptance Scenarios**:

1. **Given** a signed-in Admin, **When** they create a staff profile with all required fields, **Then** the profile exists with status Active and the department, job title, and system role are recorded.
2. **Given** a signed-in Admin, **When** they create a staff profile with a blood group, **Then** it is stored only if it is one of A+, A-, B+, B-, AB+, AB-, O+, O-; any other value is rejected with a field-level error (owner decision, Spec 001 D-13).
3. **Given** a signed-in Admin, **When** they create a staff profile without a blood group, **Then** the profile is created — blood group is optional and never blocks staff setup.
4. **Given** a signed-in Admin, **When** they link a staff profile to a user account, **Then** the profile and the account refer to the same person, and the link is visible on both records.
5. **Given** a signed-in Admin, **When** they try to create a staff profile with a missing required field, **Then** the profile is not created and a field-level error names the missing field.
6. **Given** a staff profile exists, **When** a signed-in staff member views the directory, **Then** they see name, department, job title, and system role — and contact details only if they are an Admin or viewing their own profile (least privilege; see Permissions).

### User Story 3 — Admin manages the service catalog, categories, and visit types (Priority: P2)

An Admin maintains the list of services the hospital offers, grouped by
category, and the visit types appointments use (e.g. first visit,
follow-up) — so appointments and (later) billing pick from a controlled
list instead of free text.

**Why this priority**: A controlled service catalog is what makes
appointment visit types and future invoice line items consistent. It is
P2 because departments and staff must exist first, and appointments can
start with a minimal catalog.

**Independent Test**: An Admin can create a service in a category, create
a visit type, and a Receptionist creating an appointment (Spec 004) can
pick both from lists.

**Acceptance Scenarios**:

1. **Given** a signed-in Admin, **When** they create a service with a name, a unique code, and a category, **Then** the service exists in active status.
2. **Given** a signed-in Admin, **When** they create a service category or a visit type, **Then** it appears in the reference lists other screens use.
3. **Given** a signed-in Admin, **When** they try to create a service with a code that already exists, **Then** the service is not created and a field-level error names the problem.
4. **Given** a signed-in non-Admin user, **When** they try to create or edit a service, category, or visit type, **Then** the action is denied by the backend (403).
5. **Given** services exist, **When** a signed-in Receptionist or Doctor lists them, **Then** they see the active services (read-only) for appointment and encounter work.

### User Story 4 — Reference data used by history cannot be deleted (Priority: P2)

An Admin tries to delete a department or service that existing records
point to. The system refuses and offers deactivation instead, so history
keeps its meaning.

**Why this priority**: Deleting a referenced department or service would
orphan appointments and break reports. This is Master Plan M02 ("prevent
deletion of reference records used by historical transactions") and
FR-022 (preserve required historical records).

**Independent Test**: With a department linked to a staff profile (or a
service linked to an appointment), deleting it is refused with an
understandable error; deactivating it succeeds and hides it from new
selections while existing records keep their link.

**Acceptance Scenarios**:

1. **Given** a department linked to one or more staff profiles, **When** an Admin tries to delete it, **Then** the deletion is refused with an understandable error explaining the link, and the department still exists.
2. **Given** a service linked to one or more appointments, **When** an Admin tries to delete it, **Then** the deletion is refused in the same way.
3. **Given** a department or service that is no longer wanted for new use, **When** an Admin deactivates it, **Then** it no longer appears in selection lists for new records, but existing records keep their link and history is intact.
4. **Given** a reference record that has never been used by any other record, **When** an Admin deletes it, **Then** the deletion succeeds (unused reference data may be removed; used data may not).
5. **Given** a deactivated department or service, **When** an Admin re-activates it, **Then** it appears in selection lists again and an audit event records the change.

### User Story 5 — Staff status changes are controlled and traceable (Priority: P3)

An Admin marks a staff member Inactive when they leave, instead of
deleting the profile, so their past appointments and encounters keep an
author.

**Why this priority**: Staff history must survive departure — past work
was done by a real person. Status change with a recorded reason is the
controlled alternative to deletion (Master Plan §9.1). It is P3 because
it is a maintenance action, not a daily workflow.

**Independent Test**: An Admin can change a staff profile from Active to
Inactive with a reason; the profile remains in the directory with its
history, and the change is auditable.

**Acceptance Scenarios**:

1. **Given** an active staff profile, **When** an Admin changes its status to Inactive with a reason, **Then** the status changes, the reason and actor are recorded, and the profile is not deleted.
2. **Given** an inactive staff profile, **When** a Receptionist creates a new appointment, **Then** that staff member does not appear as an available provider.
3. **Given** a status change, **When** an Admin views the staff profile, **Then** the status history is visible in chronological order.

### Edge Cases

- What happens when a department is deactivated while it still has active staff? Deactivation is allowed (it only hides the department from new selections); staff profiles keep their department link, and the Admin is warned. Whether deactivation should be blocked while active staff remain is not decided — see Open Question OQ-006.
- What happens when a staff profile has no linked user account? The profile exists for scheduling/reference, but that person cannot sign in until an account is linked (Spec 002). Whether a profile may exist without an account at all is Open Question OQ-005.
- What happens when a staff member belongs to no department? Department is required for clinical roles (Doctor, Nurse, Lab Technician) and optional for others (see Decisions D-05).
- What happens when two staff members have the same name? Names are not unique; the staff record is identified by its internal staff identifier (format: Open Question OQ-001).
- What happens when a service is deactivated while future appointments reference it? Existing appointments keep their service link; no new appointment may select it.
- What happens when an Admin tries to manage setup while signed in as a Doctor? The action is denied by the backend with a permission error, not just hidden in the UI.
- What happens to a staff profile when its linked user account is disabled (Spec 002)? The profile itself is unchanged; the person simply cannot sign in. Whether disabling the account should also change the staff status is Open Question OQ-007.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow an authorised Admin to create, edit, and deactivate departments, with a unique code per department (Master Plan FR-004).
- **FR-002**: The system MUST allow an authorised Admin to create, edit, and change the status of staff profiles, recording department, job title, system role, and an optional blood group (Master Plan FR-004).
- **FR-003**: The system MUST link a staff profile to at most one user account, and a user account to at most one staff profile (Master Plan §11).
- **FR-004**: The system MUST allow an authorised Admin to create, edit, and deactivate services, service categories, and visit types, with a unique code per service (Master Plan FR-004).
- **FR-005**: The system MUST refuse to delete a department, staff profile, service, category, or visit type that any other record references; it MUST offer deactivation instead, and deactivated records MUST NOT appear in selection lists for new records while existing links are preserved (Master Plan FR-004, FR-022).
- **FR-006**: The system MUST allow an authorised Admin to delete a reference record that no other record references.
- **FR-007**: The system MUST validate required fields on the backend before saving and show field-level errors on the frontend; blood group, when given, MUST be one of A+, A-, B+, B-, AB+, AB-, O+, O- (Master Plan FR-021; Spec 001 D-13).
- **FR-008**: The system MUST record audit events for department, staff, service, category, and visit-type creation, edits, status changes, deactivation, and refused deletions (actor, action, target, timestamp, outcome) (Master Plan FR-020).
- **FR-009**: The system MUST enforce permissions on the backend: Admin manages setup; other roles have read-only access as defined in the Permissions table (Master Plan FR-002).
- **FR-010**: The system MUST paginate, filter, and sort list views (departments, staff, services) and return only fields the caller's role may see (Master Plan FR-024).
- **FR-011**: The system MUST record staff status changes with a reason, actor, and timestamp; staff profiles MUST NOT be hard-deleted (Master Plan FR-022, §9.1).
- **FR-012**: The system MUST return understandable errors without exposing secrets, stack traces, or unnecessary personal data (Master Plan FR-023).
- **FR-013**: The system MUST NOT show inactive staff as available providers for new appointments (Spec 004 consumes this rule).

### Traceability to Master Plan requirements

| Master Plan FR | Covered by (this spec) |
|---|---|
| FR-004 Reference data | FR-001, FR-002, FR-003, FR-004 |
| FR-002 Authorization | FR-009 |
| FR-020 Audit trail | FR-008 |
| FR-021 Validation | FR-007 |
| FR-022 History | FR-005, FR-006, FR-011 |
| FR-023 Error handling | FR-012 |
| FR-024 Search and filtering | FR-010 |

### Key Entities

- **Department**: A hospital organisational unit. Key attributes: name (required), code (required, unique), description (optional), active flag, created-by, created-at.
- **StaffProfile**: A staff member's work identity — distinct from their user account (Master Plan §7.1). Key attributes: full name (required), job title (required), department (required for clinical roles, optional otherwise), system role (required — one of the Spec 002 roles), linked user account (optional), phone (optional), email (optional), blood group (optional: A+, A-, B+, B-, AB+, AB-, O+, O-), status (Active / Inactive), staff identifier (format: Open Question OQ-001), created-by, created-at.
- **Service**: An item in the service catalog. Key attributes: name (required), code (required, unique), category (required), department (optional link), active flag. No price in v1 (see Open Question OQ-003).
- **ServiceCategory**: A grouping for services (e.g. Consultation, Laboratory, Imaging). Key attributes: name (required, unique), active flag.
- **VisitType**: A kind of appointment visit (e.g. first visit, follow-up). Key attributes: name (required, unique), active flag. Duration, if visit types ever carry one, is decided by Spec 004's Open Question OQ-001 — not here.
- **AuditEvent**: Who did what, when, to which setup record, and whether it succeeded (shared `audit` app, Spec 002).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An Admin can create a department, a staff profile (with optional blood group), and a service in a single setup flow, and each appears in the lists other modules use.
- **SC-002**: Attempting to delete a referenced department or service is refused in automated tests; deactivating it succeeds and hides it from new selections while existing links survive.
- **SC-003**: An unused reference record can be deleted by an Admin; a used one cannot.
- **SC-004**: A non-Admin attempting any setup mutation is denied by the backend (403) in automated permission tests.
- **SC-005**: Every setup creation, edit, status change, deactivation, and refused deletion in test data has a corresponding audit event with actor and timestamp.
- **SC-006**: Inactive staff do not appear as available providers for new appointments.
- **SC-007**: All P0 acceptance scenarios above pass against the implemented feature before it is considered complete.

## Permissions (decided — Admin manages; others read-only as needed)

| Role | Manage departments | Manage staff profiles | Manage services / categories / visit types | Read departments & services | View staff directory |
|---|---|---|---|---|---|
| Admin | Yes | Yes | Yes | Yes | Yes (full detail) |
| Receptionist | No | No | No | Yes | Yes (name, department, job title, role only) |
| Doctor | No | No | No | Yes | Yes (name, department, job title, role only) |
| Nurse | No | No | No | Yes | Yes (name, department, job title, role only) |
| Lab Technician | No | No | No | Yes | Yes (name, department, job title, role only) |
| Pharmacist | No | No | No | Yes | Yes (name, department, job title, role only) |
| Billing | No | No | No | Yes | Yes (name, department, job title, role only) |

Staff contact details (phone, email) and blood group are visible to Admin
and to the staff member themselves; other roles see only name, department,
job title, and system role in the directory. Blood group is clinical
information, not directory information — it is never shown in list views
to other roles. Every staff member may view and correct (via Admin) their
own profile; nobody edits another person's profile except an Admin.

## Data fields (decided — see D-01, D-05)

- **Department**: name (required), code (required, unique), description (optional), active flag. System fields: created-by, created-at, updated-at.
- **StaffProfile**: full name (required), job title (required), department (required for Doctor / Nurse / Lab Technician roles, optional for others — D-05), system role (required, one of the Spec 002 roles), linked user account (optional, at most one), phone (optional), email (optional), blood group (optional: A+, A-, B+, B-, AB+, AB-, O+, O- — D-01), status (Active / Inactive), staff identifier (format undecided — OQ-001). System fields: created-by, created-at, updated-at.
- **Service**: name (required), code (required, unique), category (required), department (optional link), active flag. No price field in v1 (OQ-003). System fields: created-by, created-at, updated-at.
- **ServiceCategory / VisitType**: name (required, unique), active flag. System fields: created-by, created-at, updated-at.

## Assumptions

- The hospital is a single organisation; one deployment instance (Master Plan §2.4).
- Authentication and RBAC (Spec 002) exist before or alongside this feature; setup endpoints assume a signed-in user with a role. If Spec 002 is not yet built, this feature cannot be demonstrated end-to-end.
- All demo/test data is synthetic; no real staff records are used.
- Display timezone for dates/times is Asia/Karachi; timestamps are stored in UTC (ADR-001).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner (2026-11-22); implementation may proceed on that basis.
- The initial departments, categories, visit types, and services are entered by the Admin through the UI; no seed list is assumed (see Open Question OQ-004).

## Decisions

Decisions below are taken from already-approved sources or are minimal
choices with stated rationale. Anything not listed here is an Open Question.

1. **D-01 — Blood group is an optional field for all staff profiles** (A+, A-, B+, B-, AB+, AB-, O+, O-). Source: owner instruction, Spec 001 D-13. Rationale: the same consistent demographic field as for patients (Spec 001); useful clinical information (transfusion readiness, emergencies) but often unknown, so requiring it would block setup.
2. **D-02 — No deleting records used by historical transactions.** Source: Master Plan §6 M02. A referenced department, service, category, visit type, or staff profile cannot be hard-deleted; it is deactivated instead, and existing links are preserved. An unreferenced record may be deleted by an Admin.
3. **D-03 — Admin manages all setup; other roles are read-only as needed.** Source: Master Plan §5 (System Administrator configures reference data), §6 M02. Rationale: reference data is shared by every workflow, so uncontrolled edits would corrupt appointments and reports; read access is granted where daily work needs it (booking, queues).
4. **D-04 — Staff profile and user account are separate entities, linked at most one-to-one.** Source: Master Plan §7.1 ("Patient vs. user account" distinction applied to staff: the profile is the work identity, the account is the sign-in identity), §11. Rationale: a profile is needed for scheduling even before sign-in exists, and account lifecycle (Spec 002) must not delete work history.
5. **D-05 — Department is required for clinical roles (Doctor, Nurse, Lab Technician) and optional for other roles.** Rationale: clinical work is department-scoped (queues, schedules, reports), so a clinician without a department cannot be placed in any workflow; non-clinical staff (e.g. Billing) may not belong to a clinical department.
6. **D-06 — Staff statuses in v1 are Active / Inactive only.** Rationale: the minimal pair the workflows need — available for new work, or not. Any richer set (on leave, terminated, suspended) is Open Question OQ-002.
7. **D-07 — No price on services in v1.** Rationale: prices are billing data (Master Plan M09, a P1 candidate not yet specified); adding a price field now would pre-decide billing rules. Whether a price/charge field is added with this catalog or only when billing is specified is Open Question OQ-003.

## Open Questions

Genuinely undecided — do not guess; each needs an owner decision before
the implementation that depends on it.

- **OQ-001 — Staff identifier: what format, and is it auto-generated?** Master Plan §11 says to define uniqueness for staff identifiers "where required" but gives no format (unlike the MRN, which is specified in Spec 001). Needed before staff records can be referenced reliably.
- **OQ-002 — Staff statuses beyond Active / Inactive?** E.g. On leave, Suspended, Terminated. Undecided; affects status transitions and whether inactive staff keep appearing in history views.
- **OQ-003 — Service price: does the service catalog carry a charge/price now, or only when billing (M09) is specified?** Undecided. Adding it now pre-decides billing rules; leaving it out means the catalog cannot yet support invoicing.
- **OQ-004 — Seed data: what are the initial departments, service categories, visit types, and services?** Undecided. The Admin can enter them through the UI, but a sensible starter list (and whether one is seeded at all) needs an owner or supervisor decision.
- **OQ-005 — May a staff profile exist with no linked user account?** Undecided. Scheduling needs clinicians listed, but a profile without an account can never sign in; whether that state is allowed (and for how long) is a policy choice.
- **OQ-006 — Deactivating a department that still has active staff: allowed with a warning, or blocked?** Undecided. The spec allows deactivation (existing links are preserved) but the safer behaviour for a department with active staff is a policy choice.
- **OQ-007 — When a user account is disabled (Spec 002), should the linked staff profile's status change too?** Undecided. The two lifecycles are separate by design (D-04); whether they are coupled on disable is a policy choice.
- **OQ-008 — Department code format: is there a naming convention (e.g. short uppercase codes), and who chooses it?** Undecided. Codes must be unique (FR-001); any format rule beyond uniqueness is undecided.

## Deferred (not decided here)

- **Shift/rota scheduling, leave management, payroll**: not in the Master Plan's M02; deferred until a real requirement exists.
- **Organisational hierarchy** (reporting lines, department heads): not in M02; deferred.
- **Billing prices and charges**: Master Plan M09, P1 candidate — decided when billing is specified (OQ-003).
- **Appointment duration on visit types**: decided by Spec 004's Open Question OQ-001, not here.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1; §§19–23 (deployment, risk register, governance/decision log, acceptance, open decisions) are listed in the contents but absent from the document. Explicitly deferred: they must be supplied or formally deferred before release planning (Phase 8), but they do not block this feature.
