# Feature Specification: Patient Registration

**Feature Branch**: `docs/medicore-day1-spec-001` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — pending owner/supervisor approval. Do not implement before approval.

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
   future, an implausible phone format — exact rules to be confirmed),
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
can find one by MRN, by name, and by phone number (if phone search is approved),
and a Doctor sees the same patient via a read-only search.

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
   different person",
   **Then** the record is created and the decision (who, when, why) is recorded.
3. **Given** a duplicate warning, **When** the Receptionist confirms "this is the
   same person",
   **Then** no new record is created and they are taken to the existing patient.
4. **Given** a duplicate decision is recorded, **When** an Admin later reviews the
   patient, **Then** the duplicate-review history is visible.

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
- What happens when a patient has no phone number or no date of birth (if those fields turn out to be optional)? The form must accept the record and mark the missing data clearly.
- What happens when a search term matches many patients? Results are paginated and sorted deterministically; no unbounded list is returned.
- What happens when a Receptionist tries to register a patient while signed in as a Doctor? The action is denied by the backend with a permission error, not just hidden in the UI.
- What happens when the same MRN is requested twice concurrently? The database unique constraint rejects the second write.
- What happens to a patient record that is no longer needed? Records are not hard-deleted; status change (e.g. Active → Inactive) and its reason are recorded. Exact statuses are an open decision (see below).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow an authorised Receptionist or Admin to register a new patient with a unique MRN (Master Plan FR-005).
- **FR-002**: The system MUST generate the MRN automatically; staff MUST NOT type it by hand. Format is an open decision (see Open Questions).
- **FR-003**: The system MUST validate required fields on the backend before saving; the frontend MUST show field-level errors (Master Plan FR-021).
- **FR-004**: The system MUST allow authorised users to search patients by MRN and by name, and by phone number only if phone search is approved (Master Plan FR-006).
- **FR-005**: Search results MUST be paginated, sorted deterministically, and limited to permitted fields for the caller's role.
- **FR-006**: The system MUST flag potential duplicate patients (same name + date of birth, at minimum — exact matching rule is an open decision) and MUST NOT create a second record or merge records without a recorded human decision (Master Plan FR-007).
- **FR-007**: The system MUST record duplicate-review decisions (who, when, decision, reason).
- **FR-008**: The system MUST keep a correction history for demographic changes: old value, new value, author, timestamp. Corrections MUST NOT silently overwrite history.
- **FR-009**: The system MUST NOT hard-delete patient records. Status changes MUST be recorded with a reason.
- **FR-010**: The system MUST show a patient summary (demographics + status) and, once later features exist, an authorised visit history.
- **FR-011**: The system MUST enforce permissions on the backend: Receptionist/Admin can create and correct; Doctor is read-only for patient records; other roles have no patient-record access unless explicitly granted (see Permissions).
- **FR-012**: The system MUST record audit events for patient creation, correction, status change, and duplicate-review decisions (actor, action, target, timestamp, outcome).
- **FR-013**: The system MUST reject unauthenticated access to all patient endpoints.
- **FR-014**: The system MUST return understandable errors without exposing secrets, stack traces, or unnecessary patient data (Master Plan FR-023).

### Key Entities

- **Patient**: A person receiving care; distinct from a staff user account. Key
  attributes: MRN (unique), full name, date of birth (if approved as required),
  sex/gender (if approved), phone, address (if approved), status, created-by,
  created-at, updated-at. Full field list is an open decision.
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

## Permissions (proposal — to confirm)

| Role | Search patients | Register patient | Correct demographics | View correction / duplicate history | Delete patient |
|---|---|---|---|---|---|
| Admin | Yes | Yes | Yes | Yes | No (status change only) |
| Receptionist / Registration | Yes | Yes | Yes | Yes (own + team) | No |
| Doctor / Clinician | Yes (read-only) | No | No | Yes (for patients they may view) | No |
| Nurse | To confirm | No | No | To confirm | No |
| Lab Technician | To confirm | No | No | No | No |
| Pharmacist | To confirm | No | No | No | No |
| Billing | To confirm | No | No | No | No |

Doctor read-only access here is for patient *demographics/summary*, not for
clinical notes (which belong to the encounter feature). Nurse / Lab / Billing
search access is deliberately left "to confirm" — the Master Plan does not
decide it, and granting it without a workflow reason would violate least
privilege (Constitution Principle III).

## Data fields (proposal — to confirm)

Proposed required fields: full name, date of birth, sex/gender, phone number.
Proposed optional fields: address, emergency contact name/phone, national ID
number (only if a workflow justifies collecting it — see Open Questions).
Proposed system fields: MRN (auto-generated), status (Active/Inactive — exact
values to confirm), created-by, created-at, updated-at.

No field is final until the owner/supervisor confirms it. Do not collect
fields "because they might be useful" — data minimisation is a constitution
requirement (Principle III, §2.4).

## Assumptions

- The hospital is a single organisation; one deployment instance (Master Plan §2.4).
- Authentication and RBAC (Master Plan M01) exist before or alongside this feature;
  patient endpoints assume a signed-in user with a role. If M01 is not yet built,
  this feature cannot be demonstrated end-to-end.
- All demo/test data is synthetic; no real patient records are used.
- Display timezone for dates/times is Asia/Karachi (proposed; to confirm).
- The stack in `docs/adr/001-stack.md` is approved before implementation begins.

## Open Questions — do not guess, decide with owner/supervisor

1. **MRN format**: What should the MRN look like? Proposal: `MC-YYYY-NNNNNN`
   (e.g. `MC-2026-000123`), sequential per year. Alternatives: plain sequential
   number, or a hospital-code prefix. The format must be agreed before the
   database constraint and the UI are built.
2. **Required vs optional fields**: Which demographic fields are required?
   (Name and date of birth are proposed as required; phone, address, emergency
   contact, national ID are undecided.)
3. **Duplicate rule**: Exactly which fields trigger a duplicate warning?
   (Proposal: same full name + same date of birth. Should phone number also
   count? Should a fuzzy/typo-tolerant match be used?)
4. **Who can register**: Is registration Receptionist-only, or also Admin?
   (Proposal: both. Is there a separate "Registration" role, or is it part of
   Reception?)
5. **Patient statuses**: Which statuses exist? (Proposal: Active / Inactive.
   Is there a "Deceased", "Merged", or "Archived" status? What may trigger
   each, and who may set it?)
6. **Search fields**: Is phone-number search allowed? Is search by national ID
   allowed? What is the minimum search input (e.g. 3 characters)?
7. **National ID / CNIC**: Should it be collected at all? If yes, how is it
   stored and who may see it? (Privacy: collecting it without a workflow
   reason violates data minimisation.)
8. **Visit history on the patient summary**: Which later workflows appear there
   (appointments, encounters)? This depends on those features' specs.
9. **Duplicate-review authority**: Can the same Receptionist who registered the
   patient also resolve the duplicate warning, or must a second person/Admin
   review it?
10. **Master Plan gaps**: The Master Plan body ends at §18.1; §§19–23 (deployment,
    risk register, governance/decision log, acceptance, open decisions) are
    listed in the contents but absent from the document. Those sections must be
    supplied or explicitly deferred before release planning.
