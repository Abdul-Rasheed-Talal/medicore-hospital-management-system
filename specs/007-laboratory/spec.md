# Feature Specification: Laboratory

**Feature Branch**: `docs/medicore-all-specs` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — not yet approved by the owner. **P1 CANDIDATE — pending
the owner's priority call.** This feature is a candidate, not committed
scope: Master Plan §4.2 lists laboratory requests and result entry as
"P1 - Candidate — useful cross-department workflow; may be deferred if time
is tight", and §17 Phase 6 says to choose lab OR billing OR prescription
based on approved priority and remaining time, avoiding implementing all in
parallel. Do not implement this spec until the owner explicitly includes it.

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline),
§4 P1 candidate laboratory requests and result entry, §5 Laboratory Staff
and Doctor / Clinician actors, §6 M08, §7 WF-03, §8 FR-014 / FR-015, §11
LabTest / LabRequest and LabResult entities, §12.4 Laboratory audit;
MediCore Constitution v1.0.0, Principles I, III, IV, V, VI, VII; Spec 001
Patient Registration (patient identity, MRN, permissions baseline); Spec
005 Encounters (encounter record this feature links to).

## Overview

### Problem

A clinician orders a test, the laboratory performs it, and the result comes
back — but without a tracked request, that chain lives in verbal handoffs
and paper slips. Requests get lost, nobody knows whether a sample was
collected, and a result can be entered, changed, or seen by the wrong person
with no trace. The laboratory workflow (WF-03) makes each step explicit and
traceable: request → collected → received → in-progress → completed
(or cancelled), with specimen details, a result value with unit and
reference range, a result author with timestamps, and approval where
required.

This spec is deliberately narrow: one test request per record, linked to a
patient and an encounter, processed through controlled states by Lab staff,
with results entered and approved under traceable rules. It does not include
laboratory analyzers or imaging integration, a test catalog (see Open
Questions, Q-001), pharmacy, billing, or a patient portal.

### Scope

**In scope**

- Create a test request linked to a patient and an encounter (FR-014)
- Track request statuses Requested / Collected / Received / In-progress /
  Completed / Cancelled (M08, FR-015)
- Record specimen details (M08)
- Record result value, unit, and reference range, with result author and
  timestamps, and approval status if required (M08, FR-015)
- Restrict access to authorized laboratory and care staff (M08)
- Correct a completed result only through a traceable correction; cancel a
  request only before completion, with a reason

**Out of scope**

- Integration with medical devices, laboratory analyzers, imaging systems,
  or national health infrastructure (Master Plan §4.3)
- A test catalog / service catalog — whether tests come from an
  admin-managed catalog or free text is an Open Question (Q-001); v1
  identifies the test by name as entered on the request
- Pharmacy and inventory, billing, nursing observations, patient portal
- Clinical interpretation of results or treatment advice based on results —
  the system records results; it does not interpret them (Master Plan §4.3)
- Multi-hospital tenancy, real patient records; all demo/test data is
  synthetic

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Request a test from an encounter (Priority: P1)

A Doctor, during or after an encounter, creates a laboratory test request
for the patient, linked to that encounter. The request appears in the
laboratory queue in Requested status.

**Why this priority**: The request is the start of WF-03 and the record
everything else hangs off. Without it there is no queue for Lab staff, no
specimen to track, and no result to enter. This is Master Plan M08 and
§8 FR-014.

**Independent Test**: With a synthetic patient and a finalised encounter, a
Doctor can create a test request, and Lab staff can see it in their
authorised queue in Requested status. No other feature needs to exist for
this to be demonstrated (encounters are a prerequisite).

**Acceptance Scenarios**:

1. **Given** a signed-in Doctor and a finalised encounter, **When** they
   create a test request naming the test and giving specimen details,
   **Then** a request is created in Requested status, linked to the
   patient, the encounter, and the Doctor as requester, with created-by
   and created-at recorded.
2. **Given** a signed-in Doctor, **When** they submit a test request
   with no test name,
   **Then** the request is not created and a field-level error names the
   missing field.
3. **Given** a signed-in Doctor, **When** they try to create a test request
   with no encounter (a standalone request),
   **Then** the system refuses — every request MUST link to a patient and
   an encounter (FR-014, see Decisions, L-02).
4. **Given** a signed-in Doctor, **When** they try to create a test request
   on a draft (not finalised) encounter,
   **Then** the system refuses — requests attach to a finalised encounter
   only (see Decisions, L-02).
5. **Given** a signed-in Receptionist, **When** they try to create a test
   request, **Then** the action is denied by the backend with a permission
   error, not just hidden in the UI.
6. **Given** a test request exists, **When** Lab staff view their queue,
   **Then** they see the request with the minimum patient identifiers
   needed to perform the task (MRN and name) — and no CNIC / B-Form
   number, which is never shown to Lab staff.

### User Story 2 — Process the request and enter the result (Priority: P2)

Lab staff work the request through its states — collected, received,
in-progress — then enter the result (value, unit, reference range) with
their authorship and timestamps, completing the request. Each state change
is recorded with who made it and when.

**Why this priority**: The state machine is the workflow: it is what makes
a request traceable from order to result instead of a slip of paper.
Result entry is FR-015. It is P2 because the request (P1) must exist
first, but the workflow is incomplete without it.

**Independent Test**: Lab staff can move a request Requested → Collected →
Received → In-progress, enter a result with value/unit/reference range,
and the request becomes Completed with result author and timestamps.
An invalid transition (e.g. Requested → Completed) is refused.

**Acceptance Scenarios**:

1. **Given** a request in Requested status, **When** Lab staff mark it
   Collected and record specimen details (specimen type, collected-at,
   collected-by), **Then** the status becomes Collected with the actor
   and timestamp recorded.
2. **Given** a request in Collected status, **When** Lab staff mark it
   Received, then In-progress, **Then** each transition is recorded with
   actor and timestamp.
3. **Given** a request in In-progress status, **When** Lab staff enter a
   result value with unit and reference range,
   **Then** a result record is created with the Lab staff member as author
   and entered-at timestamp, and the request status becomes Completed
   (subject to the approval rule, Q-003).
4. **Given** a request in Requested status, **When** Lab staff try to enter
   a result (skipping collection/processing), **Then** the action is
   refused — results are entered only from In-progress status.
5. **Given** a request in any status, **When** Lab staff try an invalid
   transition (e.g. Completed → In-progress, or Requested → Completed),
   **Then** the transition is refused with an understandable error.
6. **Given** a request in Requested, Collected, Received, or In-progress
   status, **When** the requesting Doctor or Lab staff cancel it and give
   a reason, **Then** the status becomes Cancelled with cancelled-by,
   cancelled-at, and the reason recorded; a Completed request cannot be
   cancelled (see Decisions, L-05).
7. **Given** a signed-in Doctor, **When** they try to change a request's
   processing status (Collected, Received, In-progress) or enter a result,
   **Then** the action is denied — processing and result entry are Lab
   staff work (see Permissions).

### User Story 3 — Approve and correct a result; clinician reviews it (Priority: P3)

Where approval is required, a result is approved before it counts as the
completed result; a completed result that turns out to be wrong is
corrected through a traceable correction, never a silent overwrite. The
requesting Doctor can review the completed result.

**Why this priority**: Approval and correction are the trust controls on
the result (Master Plan §6 M08 "approval status if required", §12.4).
They are P3 because the basic request → result flow (P1/P2) must work
first, and whether approval is mandatory for all results is itself an Open
Question (Q-003).

**Independent Test**: A completed result can be corrected with a reason,
leaving the original value visible in the correction history; the
requesting Doctor can view the completed result, while a Receptionist
cannot.

**Acceptance Scenarios**:

1. **Given** a completed result, **When** Lab staff correct the result
   value and give a reason, **Then** a correction record is created (old
   value, new value, author, timestamp, reason), the current value is
   updated, and the original value remains visible in the correction
   history.
2. **Given** a completed result, **When** the requesting Doctor views it,
   **Then** they see the result value, unit, reference range, author, and
   entered-at / approved-at timestamps.
3. **Given** a completed result, **When** a Receptionist, Billing user, or
   Pharmacist tries to view it, **Then** access is denied — results are
   restricted to Lab staff and care staff (M08).
4. **Given** any request status change, result entry, approval, or
   correction, **When** the audit trail is inspected, **Then** the audit
   event records actor, action, request/result, and timestamp.
5. **Given** a request in Completed status, **When** anyone tries to change
   its status back to an earlier state, **Then** the action is refused —
   Completed is terminal except through a recorded result correction.

### Edge Cases

- What happens when a request's encounter is corrected after the request
  was made? The request is unaffected — it records the order as given. If
  the encounter correction changes the clinical basis, the requester
  cancels the request (if not completed) and creates a new one; the system
  does not do this automatically.
- What happens when a request's patient record is Merged or Archived?
  Existing requests and results stay linked to the surviving MRN (merge)
  or remain readable as history (archive); no lab record is deleted
  because the patient status changed.
- What happens when a test request names a test the lab does not perform?
  There is no catalog check in v1 (Q-001); the request is created as
  entered, and Lab staff cancel it with a reason if it cannot be
  performed. A catalog would prevent this; its absence is a known v1
  limitation.
- What happens when one request needs more than one result (e.g. a panel)?
  One request may have one or more results (Master Plan §11.2); each
  result is a separate row with its own value, unit, reference range,
  author, and timestamps.
- What happens when a result value is outside its reference range? The
  system records the value as entered; it does not flag, interpret, or
  alert — interpretation is clinical work, not a system function in v1
  (see Open Questions, Q-004).
- What happens when Lab staff try to view a patient's full record? They
  cannot — Lab staff see the request queue with minimum patient
  identifiers (MRN, name) and the linked encounter's request context
  only. They have no patient search in v1 (Spec 001) and no access to
  encounter notes, diagnosis, or prescriptions.
- What happens when the system is asked for a lab queue list? Lists are
  paginated, filtered to the caller's authorised scope (Lab staff: the lab
  queue; Doctor: requests they made), and sorted deterministically.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-014**: The system MUST allow authorised clinicians (Doctors) to
  create test requests linked to patients and encounters (Master Plan §8
  FR-014, §6 M08, §7 WF-03). Every request MUST link to exactly one
  patient and one encounter; a request with no encounter MUST be refused.
- **FR-014a**: A request MUST name the test and record specimen details
  (specimen type, collected-at, collected-by) as the workflow progresses
  (Master Plan §6 M08). Test name is required at creation; specimen
  details are required at the Collected step.
- **FR-015**: The system MUST allow authorised laboratory staff to record
  and update results through controlled states (Master Plan §8 FR-015,
  §6 M08). Request statuses are Requested / Collected / Received /
  In-progress / Completed / Cancelled, and only the transitions in the
  state machine (see Decisions, L-04) are permitted.
- **FR-015a**: A result MUST carry a value, a unit, and a reference range,
  with result author and timestamps (entered-at; approved-at where
  approval applies) (Master Plan §6 M08, §11 LabResult).
- **FR-015b**: Result approval, where required, MUST be recorded (approver,
  timestamp). Whether approval is mandatory for all results or only some
  is an Open Question (Q-003); the approval fields exist regardless.
- **FR-015c**: Corrections to a completed result MUST be recorded as
  separate correction rows (field, old value, new value, author,
  timestamp, reason). The original value MUST remain visible in the
  correction history. Corrections MUST NOT silently overwrite history
  (Master Plan §8 FR-022).
- **FR-015d**: A Completed request MUST NOT be cancelled and MUST NOT move
  back to an earlier status. Cancellation is permitted only before
  completion, with a recorded reason (see Decisions, L-05).
- **FR-020**: The system MUST record audit events for request creation,
  status changes, result entry, approval, correction, and cancellation
  (actor, action, target, timestamp, outcome) (Master Plan §8 FR-020,
  §12.4).
- **FR-021**: The system MUST validate input and enforce business rules on
  the backend before saving (Master Plan §8 FR-021): test name required;
  specimen details required at collection; result value/unit/reference
  range required at result entry; state transitions valid.
- **FR-022**: The system MUST preserve laboratory history and MUST NOT
  hard-delete requests, results, or corrections (Master Plan §8 FR-022).
- **FR-023**: The system MUST return understandable errors without exposing
  secrets, stack traces, or unnecessary patient data (Master Plan §8
  FR-023).
- **FR-024**: Lab queues and request lists MUST be paginated, filtered to
  the caller's authorised scope, and sorted deterministically (Master Plan
  §8 FR-024).

### Key Entities

- **LabRequest**: A patient-specific test request. Key attributes: patient
  (FK → Patient, MRN `MC-YYYY-NNNNNN`), encounter (FK → Encounter,
  required), requester (FK → User, Doctor role, required), test name
  (required text in v1), specimen type (text), collected-at (DateTime,
  nullable until Collected), collected-by (FK → User, nullable until
  Collected), status (Requested / Collected / Received / In-progress /
  Completed / Cancelled), created-by, created-at, cancelled-by,
  cancelled-at, cancellation reason.
- **LabResult**: A result associated with a request. Key attributes:
  request (FK → LabRequest, required), result value (required text —
  numeric or textual, per the test), unit (required), reference range
  (required text, e.g. "4.0–11.0"), author (FK → User, Lab staff,
  required), entered-at (DateTime), approved-by (FK → User, nullable),
  approved-at (DateTime, nullable), approval status (Pending / Approved /
  Not required — see Q-003). One request may have one or more results
  (Master Plan §11.2).
- **LabResultCorrection**: One traceable change to a completed result. Key
  attributes: result (FK → LabResult), field, old value, new value,
  author, timestamp, reason (required).
- **AuditEvent**: Who did what, when, to which request/result, and whether
  it succeeded (Master Plan §12.4 Laboratory: request status change,
  result entry, approval or correction).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Doctor can create a test request on a finalised encounter
  and Lab staff can see it in their authorised queue in Requested status,
  in a single uninterrupted flow.
- **SC-002**: A request moves through Requested → Collected → Received →
  In-progress → Completed with a result (value, unit, reference range,
  author, timestamps); every invalid transition attempted in test data is
  refused.
- **SC-003**: 100% of requests in test data link to a patient and an
  encounter; zero standalone requests exist.
- **SC-004**: 100% of corrections to completed results in test data leave a
  correction record with old value, new value, author, timestamp, and
  reason; zero are silent overwrites.
- **SC-005**: Every request status change, result entry, approval, and
  correction in test data has a corresponding audit event with actor and
  timestamp.
- **SC-006**: A Receptionist attempting to view or change a lab request or
  result is denied by the backend (not merely by a hidden button) in
  automated permission tests; a Doctor attempting to enter a result is
  likewise denied.
- **SC-007**: All P1 acceptance scenarios above pass against the implemented
  feature before it is considered complete; P2/P3 scenarios pass before the
  feature is considered fully complete.

## Permissions

| Role | Create request | Change processing status / enter result | Approve result | Cancel request | View request / result |
|---|---|---|---|---|---|
| Admin | No | No | No | No | No — no automatic entitlement to clinical content (Master Plan §5) |
| Receptionist / Registration | No | No | No | No | No |
| Doctor / Clinician | Yes — on a finalised encounter, as requester | No | No | Yes — own requests, before completion | Yes — requests they made and their results |
| Nurse | No in this spec | No | No | No | No in this spec — granted only as the nursing spec (M07) allows |
| Lab Technician | No | Yes — status changes and result entry | Yes, where approval applies (see Q-003) | Yes — before completion, with reason | Yes — the lab queue, with minimum patient identifiers (MRN, name) only |
| Pharmacist | No | No | No | No | No |
| Billing | No | No | No | No | No — clinical content hidden unless specifically needed (Master Plan §5); not granted here |

Lab staff access is request-scoped: the queue, the request, its specimen
details, and its results — not the patient's full record, encounter notes,
diagnosis, or prescriptions. Lab staff have no patient-search access in v1
(Spec 001). Patient demographics/summary access is governed by Spec 001.
"Care staff" in M08 means the requesting Doctor (and, once specified, the
nursing staff whose spec grants it) — not every Doctor, and not
Receptionist, Billing, or Pharmacist.

## Data fields

LabRequest: patient (required FK), encounter (required FK), requester
(required, the Doctor), test name (required text), specimen type (text,
required at Collected), collected-at (DateTime), collected-by (Lab staff),
status (Requested / Collected / Received / In-progress / Completed /
Cancelled), created-by, created-at, cancelled-by, cancelled-at,
cancellation reason (required when cancelling). LabResult: request
(required FK), value (required text), unit (required text), reference
range (required text), author (required, Lab staff), entered-at,
approved-by, approved-at, approval status (Pending / Approved /
Not required). Correction: field, old value, new value, author,
timestamp, reason (required).

Patient identity fields are owned by Spec 001 and are not re-decided here:
MRN `MC-YYYY-NNNNNN`; required patient fields full name, date of birth,
phone, gender (Male / Female / Other), CNIC / B-Form number (`national_id`,
13 digits, encrypted at rest, full view only Receptionist/Admin, masked
otherwise, never searchable — Lab staff never see it); blood group
optional; patient statuses Active / Inactive / Merged / Archived.

## Assumptions

- The hospital is a single organisation; one deployment instance (Master Plan
  §2.4).
- Authentication and RBAC (Master Plan M01), patient registration (Spec 001,
  M03), and encounters (Spec 005, M05) exist before this feature; lab
  endpoints assume a signed-in user with a role.
- **Candidate status**: this feature is implemented only if the owner
  explicitly includes it (Master Plan §4.2 P1 Candidate, §17 Phase 6 — one
  supporting module, not all in parallel).
- All demo/test data is synthetic; no real patient records are used.
- Display timezone for dates/times is Asia/Karachi; timestamps are stored in
  UTC and displayed in Asia/Karachi (ADR-001).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner (2026-11-22);
  Python 3.12 / Node 20 LTS; Django session auth, no JWT in v1.

## Decisions

Decisions recorded here are binding for implementation within this spec;
changing one requires an owner decision and a spec amendment. Numbers are
local to this spec (L-01…) and do not collide with Spec 001's D-01…D-13,
Spec 005's E-01…E-08, or Spec 006's P-01…P-05.

1. **L-01 — One test per request; one request may have one or more results.**
   Rationale: Master Plan §11.2 says a laboratory request may have one or
   more results depending on the test workflow (e.g. a panel); the request
   itself names a single test so its status machine stays unambiguous.
   A panel is modelled as one request with multiple result rows, not as
   multiple requests.
2. **L-02 — Requests attach to a finalised encounter only, and always link
   patient + encounter.** Rationale: WF-03 step 1 is "clinician creates a
   test request from an encounter"; a request without an encounter has no
   clinical context, and a draft encounter's documentation was never
   finalised. The encounter must be finalised first.
3. **L-03 — Lab staff own processing and result entry; the requesting Doctor
   owns the request and its review.** Rationale: WF-03 steps 2–5 are Lab
   staff work; step 6 is clinician review. Separation of duties (Master
   Plan §5.2): the person who orders the test does not enter its result.
4. **L-04 — State machine: Requested → Collected → Received → In-progress →
   Completed; any of Requested / Collected / Received / In-progress →
   Cancelled.** No other transitions. Rationale: the Master Plan lists the
   states (M08) without ordering them; this order follows the physical
   workflow (collect, receive, process, result) and WF-03 steps 2–5.
   Skipping states is refused so no step is silently dropped.
5. **L-05 — Completed is terminal; cancellation only before completion, with
   a reason.** Rationale: a completed request has a result that other
   workflows may have relied on; cancelling it would destroy the audit
   trail. Errors in a completed result are fixed by a recorded correction
   (FR-015c), not by cancelling the request.
6. **L-06 — Lab staff see minimum patient identifiers only (MRN and name).**
   Rationale: Master Plan §5 gives Lab staff "lab workflow and minimum
   patient identifiers needed to perform the task". CNIC / B-Form is never
   shown to Lab staff, and Lab staff get no encounter notes, diagnosis, or
   prescriptions — the request and its results are their scope.
7. **L-07 — Result value, unit, and reference range are all required at
   result entry.** Rationale: a bare number without a unit or a reference
   range is not a usable result (M08: "result values/units/reference
   information where defined"). The reference range is entered per result
   in v1 (its source is Open Question Q-002).

## Open Questions

1. **Q-001 — Does the test name come from an admin-managed test catalog, or
   stay free text?** A catalog (M02 reference data) would prevent requests
   for tests the lab does not perform, but needs a catalog source and
   maintenance ownership. Undecided; v1 uses the test name as entered on
   the request (L-07 note). A wrong test is handled by cancellation with a
   reason.
2. **Q-002 — Where does the reference range come from?** Candidates: the
   test catalog (if Q-001 is yes), entered per result by Lab staff, or a
   standard range table. Undecided; v1 enters it per result (L-07).
   Reference ranges can vary by age/sex, which is a further reason not to
   guess.
3. **Q-003 — Is result approval mandatory for all results, only for some
   (e.g. abnormal), or not at all — and who approves?** M08 says "approval
   status if required" and WF-03 step 5 says "finalized/approved if
   required", but neither says when it is required. Candidates: the Lab
   staff member who entered the result self-approves; a second Lab staff
   member approves; the requesting Doctor approves. Undecided; the
   approval fields exist in the data model, and the default until decided
   is that a result entered by Lab staff completes the request without a
   separate approval step.
4. **Q-004 — Should the system flag results outside the reference range?**
   Flagging is a step toward interpretation. Undecided and not implemented
   in v1; the value is recorded as entered and the requesting Doctor
   interprets it.
5. **Q-005 — Who may correct a completed result — the Lab staff member who
   entered it, any Lab staff, or only a supervisor?** This spec allows Lab
   staff to correct with a reason and a traceable record, but does not
   restrict correction to the original author. Whether correction needs a
   second person or a supervisor is undecided.
6. **Q-006 — Is there a turnaround-time expectation (e.g. how long a request
   may sit in each state) or an overdue rule?** No Master Plan rule exists.
   Undecided and not implemented in v1.

## Deferred (not decided here)

- **Test catalog / service catalog (M02)**: whether tests are catalogued is
  Open Question Q-001; the catalog itself belongs to the hospital-setup
  feature, not this spec.
- **Analyzer / device integration**: explicitly out of scope (Master Plan
  §4.3).
- **Clinical interpretation of results**: out of scope (Master Plan §4.3);
  the system records results, it does not interpret them.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1;
  §§19–23 (deployment, risk register, governance/decision log, acceptance,
  open decisions) are listed in the contents but absent from the document.
  Explicitly deferred: they must be supplied or formally deferred before
  release planning (Phase 8), but they do not block this feature.
- **Candidate status**: inclusion of this feature is itself deferred to the
  owner's priority call (Master Plan §17 Phase 6). If the owner picks
  prescription or billing instead, this spec stays a draft and is not
  implemented.
