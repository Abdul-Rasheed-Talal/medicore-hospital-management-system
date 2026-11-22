# Feature Specification: Patient Registration

**Feature Branch**: `docs/medicore-day1-spec-001` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Approved by owner 2026-11-22. The 10 open questions from the draft
were decided by the owner (he delegated the choices to the agent; see
"Decisions" below). Implementation may proceed once the scaffold (M01
authentication/RBAC) exists; this spec is the binding requirement for
patient registration.

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline), §4 P0 patient
registration, §6 M03, §7 WF-01, §8 FR-005 / FR-006 / FR-007; MediCore Constitution
v1.0.0, Principles I, III, IV, V, VI, VII.

## Overview

### Problem

A hospital that keeps patient identity in disconnected registers or spreadsheets
re-enters the same information, searches across records, and risks treating the
same person as two different patients — or two different people as one. Patient
registration establishes one reliable patient identity (with a unique internal
medical record number, MRN) that appointments, encounters, laboratory requests,
and billing can all link to. Without it, every later workflow is built on
unreliable identity.

This is the first feature specification for MediCore. It is deliberately narrow:
register a patient, find a patient, review possible duplicates, and keep a
correction history. It does not include appointments, encounters, billing, or a
patient portal — those are separate features with their own specifications.

### Scope

**In scope**

- Register a new patient with a unique MRN (FR-005)
- Search patients using approved search fields, showing only permitted information (FR-006)
- Flag potential duplicate patient records for controlled review — never silently merge (FR-007)
- View a patient summary and authorised visit history (read-only at this stage; visit history appears once appointments/encounters exist)
- Maintain status and correction history for important demographic changes (Master Plan §6 M03)

**Out of scope**

- Appointment scheduling (separate feature; WF-01 step 4 onward is out of scope here)
- Encounter / clinical documentation, prescriptions, laboratory, billing
- Patient portal, notifications, or patient self-registration
- Multi-hospital tenancy, national identity integration, insurance, real payments
- Migration of real patient records; all demo/test data is synthetic

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Register a new patient (Priority: P1)

A receptionist/registration clerk searches for a patient, finds no reliable match,
and registers them. The system issues a unique MRN and the patient can immediately
be used by later workflows (appointment booking will link to this record).

**Why this priority**: Patient identity is the foundation of every later workflow.
Without a reliable register-and-identify step, appointments and encounters cannot
be linked to the right person. This is Master Plan §4, P0 core.

**Independent Test**: A receptionist can register a synthetic patient with the
required fields, receives a unique MRN, and can find that patient again by MRN
and by name. No other feature needs to exist for this to be demonstrated.

**Acceptance Scenarios**:

1. **Given** a signed-in Receptionist with no existing match for the person,
   **When** they submit the registration form with all required fields,
   **Then** a patient record is created with a unique MRN, status Active, and
   created-by / created-at audit fields.
2. **Given** a registration form with a missing required field,
   **When** they submit it,
   **Then** the record is not created and a field-level error names the missing field.
3. **Given** a registration form with an invalid value (e.g. a date of birth in the
   future, or a phone number that is not 9–15 digits, optional leading `+`),
   **When** they submit it,
   **Then** the record is not created and a field-level error explains the problem.
4. **Given** two registration attempts for the same person in quick succession,
   **When** both are submitted,
   **Then** only one patient record is created (MRN uniqueness is enforced by a
   database constraint, not by the UI alone).

### User Story 2 — Search for a patient (Priority: P1)

A receptionist or doctor searches for an existing patient before registering or
booking, using approved identifiers, and sees only the information their role
permits.

**Why this priority**: Registration without search creates duplicates. Search is
the first step of WF-01 and the guard against FR-007 duplicates.

**Independent Test**: With several synthetic patients registered, a receptionist
can find one by MRN, by name (minimum 3 characters), and by phone number,
and a Doctor sees the same patient via a read-only search. CNIC search does
not exist in v1.

**Acceptance Scenarios**:

1. **Given** registered patients exist, **When** a Receptionist searches by MRN,
   **Then** the exact patient is returned.
2. **Given** registered patients exist, **When** a Receptionist searches by full
   name, **Then** matching patients are listed, paginated, with MRN, name, and
   status — and no clinical or financial detail.
3. **Given** no patient matches the search, **When** the search runs,
   **Then** an explicit "no match found" state is shown (not an empty or
   ambiguous screen), with a clear path to register a new patient.
4. **Given** a signed-in Doctor, **When** they search for a patient,
   **Then** they can find and view the patient summary, but cannot create, edit,
   or delete patient records.

### User Story 3 — Review a possible duplicate (Priority: P2)

When registration data closely matches an existing patient, the system flags it
for controlled review instead of creating a second record silently or merging
records automatically.

**Why this priority**: Duplicate records are a patient-safety and data-integrity
risk; silent merging is worse than a duplicate. The review step is FR-007 and
Master Plan §6 M03.

**Independent Test**: Registering a patient whose name + date of birth match an
existing patient produces a duplicate warning with a review action, and no second
record is created until a human decides.

**Acceptance Scenarios**:

1. **Given** an existing patient, **When** a Receptionist submits a registration
   with the same name and date of birth,
   **Then** the system shows a duplicate warning listing the candidate match(es)
   and asks for a decision — it does not create the record yet.
2. **Given** a duplicate warning, **When** the Receptionist confirms "this is a
   different person" and writes a reason note,
   **Then** the record is created and the decision (who, when, reason) is recorded.
3. **Given** a duplicate warning, **When** the Receptionist confirms "this is the
   same person",
   **Then** no new record is created and they are taken to the existing patient.
4. **Given** a duplicate decision is recorded, **When** an Admin later reviews the
   patient, **Then** the duplicate-review history is visible.
5. **Given** two records are found to be the same person, **When** a Receptionist
   tries to merge them, **Then** the merge is refused — only an Admin may merge
   records, and the merge (kept MRN, archived MRN, reason, actor) is recorded;
   the losing record's status becomes Merged, it is never hard-deleted.
6. **Given** a registration whose phone number matches an existing patient's phone
   exactly, **When** the name + date of birth do not match,
   **Then** the system shows a weaker "possible match — same phone number"
   warning (a strong secondary signal), but registration may proceed without a
   mandatory decision.

### User Story 4 — Correct a patient's details (Priority: P3)

A receptionist corrects an important demographic field (e.g. a misspelled name or
wrong phone number). The correction is recorded; the old value is not silently
overwritten.

**Why this priority**: Demographic errors are inevitable; a traceable correction
history is a data-integrity requirement (Constitution Principle IV, Master Plan
§6 M03, §9 NFR-04).

**Independent Test**: Editing a patient's phone number updates the current value
and leaves a visible correction-history entry with author and timestamp.

**Acceptance Scenarios**:

1. **Given** an existing patient, **When** a Receptionist edits a demographic
   field and saves,
   **Then** the new value is stored and a correction-history entry records the
   old value, new value, author, and timestamp.
2. **Given** a correction is saved, **When** an Admin views the patient,
   **Then** the full correction history is visible in chronological order.

### Edge Cases

- What happens when the MRN generator collides or the database is unavailable mid-registration? Registration must fail safely with an actionable error and no partial record.
- What happens when a patient has no phone number? It cannot happen in v1: phone is a required field. A patient with no phone must be registered with a guardian/next-of-kin phone number, recorded as such in the emergency-contact field.
- What happens when a search term matches many patients? Results are paginated and sorted deterministically; no unbounded list is returned.
- What happens when a Receptionist tries to register a patient while signed in as a Doctor? The action is denied by the backend with a permission error, not just hidden in the UI.
- What happens when the same MRN is requested twice concurrently? The database unique constraint rejects the second write.
- What happens to a patient record that is no longer needed? Records are not hard-deleted; status change (Active → Inactive / Archived, with a recorded reason) is used instead. Two records found to be the same person are merged only by an Admin; the losing record becomes Merged.
- What happens when a CNIC is entered? It is optional, stored encrypted at rest, and masked (only last 4 digits visible) for every role except Receptionist and Admin.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow an authorised Receptionist or Admin to register a new patient with a unique MRN (Master Plan FR-005).
- **FR-002**: The system MUST generate the MRN automatically; staff MUST NOT type it by hand. Format: `MC-YYYY-NNNNNN` — `MC` prefix, 4-digit year, 6-digit sequence that resets to `000001` each year (see Decisions, D-01).
- **FR-003**: The system MUST validate required fields on the backend before saving; the frontend MUST show field-level errors (Master Plan FR-021). Required fields are full name, date of birth, and phone number (see Decisions, D-02).
- **FR-004**: The system MUST allow authorised users to search patients by MRN, by full name (minimum 3 characters), and by phone number. There is no CNIC search in v1 (Master Plan FR-006).
- **FR-005**: Search results MUST be paginated, sorted deterministically, and limited to permitted fields for the caller's role.
- **FR-006**: The system MUST flag potential duplicate patients: an exact match on full name + date of birth blocks registration pending a recorded human decision; an exact phone-number match alone shows a non-blocking "possible match" warning. No fuzzy matching in v1 (documented limitation). The system MUST NOT create a second record or merge records without a recorded human decision (Master Plan FR-007).
- **FR-007**: The system MUST record duplicate-review decisions (who, when, decision, reason). The registering Receptionist may resolve a duplicate warning with a written reason; only an Admin may merge two records.
- **FR-008**: The system MUST keep a correction history for demographic changes: old value, new value, author, timestamp. Corrections MUST NOT silently overwrite history.
- **FR-009**: The system MUST NOT hard-delete patient records. Status changes MUST be recorded with a reason.
- **FR-010**: The system MUST show a patient summary (demographics + status) and, once later features exist, an authorised visit history.
- **FR-011**: The system MUST enforce permissions on the backend: Receptionist/Admin can create and correct; Doctor is read-only for patient records; other roles have no patient-record access unless explicitly granted (see Permissions).
- **FR-012**: The system MUST record audit events for patient creation, correction, status change, and duplicate-review decisions (actor, action, target, timestamp, outcome).
- **FR-013**: The system MUST reject unauthenticated access to all patient endpoints.
- **FR-014**: The system MUST return understandable errors without exposing secrets, stack traces, or unnecessary patient data (Master Plan FR-023).

### Key Entities

- **Patient**: A person receiving care; distinct from a staff user account. Key
  attributes: MRN (unique, `MC-YYYY-NNNNNN`), full name (required), date of
  birth (required), phone (required), sex/gender (optional), address
  (optional), emergency contact (optional), CNIC (optional, encrypted at
  rest, masked except for Receptionist/Admin), status (Active / Inactive /
  Merged / Archived), created-by, created-at, updated-at. See "Data fields".
- **DuplicateCandidate**: A flagged possible match between a new registration and
  an existing patient, with the matching fields, the reviewer's decision, and
  the decision timestamp.
- **PatientCorrection**: A single demographic change: field, old value, new value,
  author, timestamp.
- **AuditEvent**: Who did what, when, to which patient record, and whether it succeeded.
  Audit records MUST NOT contain passwords, tokens, or full clinical content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Receptionist can complete a new-patient registration, from search
  to issued MRN, in a single uninterrupted flow with no more than one duplicate
  warning to resolve.
- **SC-002**: Searching by MRN returns the exact patient; searching by name returns
  all and only the matching patients, paginated.
- **SC-003**: 100% of attempted duplicate registrations (same name + date of birth
  in test data) produce a review prompt; zero are silently created or merged.
- **SC-004**: Every patient creation, correction, status change, and duplicate
  decision in test data has a corresponding audit event with actor and timestamp.
- **SC-005**: A Doctor attempting to create or edit a patient record is denied by
  the backend (not merely by a hidden button) in automated permission tests.
- **SC-006**: All P0 acceptance scenarios above pass against the implemented
  feature before it is considered complete.

## Permissions (decided — see D-04, D-05)

| Role | Search patients | Register patient | Correct demographics | View correction / duplicate history | Merge records | Delete patient |
|---|---|---|---|---|---|---|
| Admin | Yes | Yes | Yes | Yes | Yes | No (status change only) |
| Receptionist / Registration | Yes | Yes | Yes | Yes (own + team) | No | No |
| Doctor / Clinician | Yes (read-only) | No | No | Yes (for patients they may view) | No | No |
| Nurse | No in v1 | No | No | No | No | No |
| Lab Technician | No in v1 | No | No | No | No | No |
| Pharmacist | No in v1 | No | No | No | No | No |
| Billing | No in v1 | No | No | No | No | No |

Doctor read-only access here is for patient *demographics/summary*, not for
clinical notes (which belong to the encounter feature). Nurse / Lab /
Pharmacist / Billing have no patient-search access in v1: the Master Plan
gives them no patient-registration workflow, and granting search without a
workflow reason would violate least privilege (Constitution Principle III).
Their own feature specs (encounters, lab, billing) will grant the search
access their workflows need, when those features are specified.

## Data fields (decided — see D-02, D-05, D-07)

Required fields: full name, date of birth, phone number.
Optional fields: sex/gender (Female / Male / Other / Prefer not to say),
address, emergency contact name/phone, CNIC.
System fields: MRN (auto-generated, `MC-YYYY-NNNNNN`), status
(Active / Inactive / Merged / Archived), created-by, created-at, updated-at.

CNIC is optional and encrypted at rest; it is shown in full only to
Receptionist and Admin and masked (last 4 digits only) for all other roles.
No field is collected "because it might be useful" — data minimisation is a
constitution requirement (Principle III, §2.4).

## Assumptions

- The hospital is a single organisation; one deployment instance (Master Plan §2.4).
- Authentication and RBAC (Master Plan M01) exist before or alongside this feature;
  patient endpoints assume a signed-in user with a role. If M01 is not yet built,
  this feature cannot be demonstrated end-to-end.
- All demo/test data is synthetic; no real patient records are used.
- Display timezone for dates/times is Asia/Karachi (decided — the hospital is
  in Pakistan; timestamps are stored in UTC and displayed in Asia/Karachi).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner (2026-11-22);
  implementation may proceed on that basis.

## Decisions

The draft spec's 10 open questions were decided on 2026-11-22: the owner
approved the spec and delegated the choices to the agent. Each decision below
records the choice and its rationale. These are binding for implementation;
changing one requires an owner decision and a spec amendment.

1. **D-01 — MRN format: `MC-YYYY-NNNNNN`.** Year + 6-digit sequence, reset
   to `000001` each 1 January (e.g. `MC-2026-000123`). Rationale: human-readable,
   sortable by year, and the yearly reset keeps numbers short for a small
   hospital; a plain sequential number grows unboundedly and a hospital-code
   prefix adds nothing for a single-hospital system. Generated server-side
   only; uniqueness enforced by a database constraint.
2. **D-02 — Required fields: full name, date of birth, phone number.**
   Optional: sex/gender, address, emergency contact, CNIC. Rationale: name +
   date of birth are the minimum identity for the duplicate rule (D-03), and
   a phone number is needed to contact the patient and as the secondary
   duplicate signal; everything else is genuinely optional at registration
   time and can be completed later, so requiring it would block front-desk
   flow. Phone validation: 9–15 digits, optional leading `+`.
3. **D-03 — Duplicate rule: exact match only.** An exact match on full name +
   date of birth blocks registration pending a recorded human decision. An
   exact phone-number match alone is a strong secondary signal: a
   non-blocking "possible match — same phone number" warning. No fuzzy
   matching in v1 — documented limitation. Rationale: fuzzy matching needs
   tuning data the project does not have and would produce false positives
   that block legitimate registrations; exact matching is predictable and
   testable, and the phone signal catches the common case of a name spelled
   differently.
4. **D-04 — Who can register: Receptionist and Admin.** No separate
   Registration role in v1. Rationale: registration is a front-desk job and
   Admin already holds all Receptionist powers for cover; a separate role
   adds RBAC complexity with no workflow behind it. If a hospital later
   splits reception from registration duties, add the role then.
5. **D-05 — Patient statuses: Active / Inactive / Merged / Archived.**
   Rationale: Active is the default; Inactive covers patients no longer
   attending (with a recorded reason); Merged is set only by an Admin merge
   (D-08) and preserves the losing record; Archived covers records retired
   from day-to-day use without deleting history. No Deceased status in v1 —
   that is a clinical-record concern, not a registration one. No status is
   ever hard-deleted.
6. **D-06 — Search fields: MRN, full name (minimum 3 characters), phone
   number.** No CNIC search in v1. Rationale: MRN is the exact key, name is
   the everyday lookup, phone is the fallback when the patient has forgotten
   their MRN; a 3-character minimum keeps name search usable while avoiding
   one-letter queries that return the whole register. CNIC search is withheld
   because CNIC is sensitive (D-07) and no workflow needs to look a patient
   up by CNIC.
7. **D-07 — CNIC: optional to collect; encrypted at rest; visible in full
   only to Receptionist and Admin, masked (last 4 digits) for all other
   roles; never in logs, list views, or URLs.** Rationale: CNIC is useful as
   a strong identity anchor in Pakistan, so collecting it is justified — but
   only optionally, since many patients will not have it to hand at
   registration, and restricting visibility follows data minimisation and
   least privilege (Constitution Principle III).
8. **D-08 — Duplicate-review authority: the registering Receptionist may
   resolve a duplicate warning with a written reason note; actually merging
   two records requires Admin.** Rationale: making every duplicate warning
   wait for an Admin would queue the front desk; the Receptionist is the
   person with the patient in front of them and best placed to judge, and
   the mandatory reason note plus audit trail makes the decision reviewable.
   Merging is destructive to identity, so it stays Admin-only.
9. **D-09 — Auth/session strategy: Django session authentication** (secure
   HttpOnly cookie, CSRF protection) for the web app; no JWT in v1. Recorded
   in ADR-001. Rationale: the product is a browser app for staff on one
   deployment — Django's built-in session auth is the simplest mature option,
   with server-side revocation (disable the account / end the session) that
   JWT would have to be hand-built to match. JWT is revisited only if a
   separate mobile/portal client is ever approved.
10. **D-10 — Licence: MIT stays.** Rationale: the usual final-year-project
    default; permissive and simple, and the owner raised no objection.

## Deferred (not decided here)

- **Visit history on the patient summary**: which later workflows appear
  there (appointments, encounters) is decided by those features' own specs.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1;
  §§19–23 (deployment, risk register, governance/decision log, acceptance,
  open decisions) are listed in the contents but absent from the document.
  Explicitly deferred: they must be supplied or formally deferred before
  release planning (Phase 8), but they do not block this feature.
- **Auth/session strategy is decided (D-09)**; the remaining ADR-001 open
  points (Python/Node versions, display timezone — Asia/Karachi adopted in
  this spec) are confirmed at scaffold.
