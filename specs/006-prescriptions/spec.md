# Feature Specification: Prescriptions

**Feature Branch**: `docs/medicore-all-specs` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — not yet approved by the owner. **Committed module M7.**
The owner decided on 2026-11-22 that Prescription, Billing and Online
Payments are each their own separate module because they are important, and
must not be lumped together or deferred as a group. Prescription is
therefore committed scope in the module plan (M7), not a deferred
candidate — the old Phase 6 "choose lab OR billing OR prescription"
pick no longer applies to it. This spec is still a draft awaiting the
owner's approval before any implementation. Do not implement this spec
until the owner approves it.

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline),
§4 P1 candidate prescription record and §4.3 out-of-scope (no clinical
decision support), §5 Doctor / Clinician actor, §6 M06, §7.1 (diagnosis vs.
prescription), §8 FR-013, §11 Prescription entity, §12.4 Clinical record
audit, §17 Phase 6 (choose one supporting module); MediCore Constitution
v1.0.0, Principles I, III, IV, V, VI, VII; Spec 001 Patient Registration
(patient identity, MRN, permissions baseline); Spec 005 Encounters
(encounter record this feature links to).

## Overview

### Problem

A diagnosis records a clinician's assessment; a prescription records
medication instructions. One does not automatically imply the other (Master
Plan §7.1). Without a prescription record, medication instructions live
only inside encounter notes as unstructured text — ambiguous, unsearchable,
and impossible to track through draft / finalised / cancelled states. A
structured prescription (name, strength, dosage, route, frequency,
duration, instructions) linked to the encounter and the prescriber gives
the hospital a reviewable medication record.

This spec is deliberately narrow and deliberately safe: it records
medication instructions a clinician has already decided, and nothing more.
It does not generate treatment recommendations, does not make automated
dosing decisions, and does not dispense medication. Those are explicitly
out of scope (Master Plan §4.3, M06).

### Scope

**In scope**

- Create a structured prescription linked to an encounter and a prescriber
  (FR-013)
- Structured medication fields: name, strength, dosage, route, frequency,
  duration, instructions (M06)
- Track draft / finalized / cancelled states and changes (M06)
- Validate required fields and avoid ambiguous free-text-only prescriptions
  (M06)
- View a prescription and the prescription history of an encounter for
  authorised roles

**Out of scope**

- Treatment recommendations or automated dosing decisions — explicitly
  forbidden (Master Plan §4.3, M06). The system MUST NOT suggest a
  medication, a dose, or a duration.
- Automated diagnosis, triage recommendations, or any clinical decision
  support (Master Plan §4.3)
- Dispensing, pharmacy stock, batches, expiry, or inventory (M12 Pharmacy
  and Inventory — future module, significant scope)
- Drug-interaction checking, allergy checking, or formulary validation —
  no clinical knowledge base exists in v1 and none is invented here
  (see Open Questions, Q-003)
- Patient portal, notifications, multi-hospital tenancy, real patient
  records; all demo/test data is synthetic

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Record a structured prescription as a draft (Priority: P1)

A Doctor, during or after a finalised encounter, records a medication
instruction with all structured fields and saves it as a draft, so the
instruction is complete and unambiguous before it is finalised.

**Why this priority**: The structured record is the whole point of the
feature — without it, prescriptions remain ambiguous free text inside
encounter notes. This is Master Plan M06 and §8 FR-013.

**Independent Test**: With a synthetic patient and a finalised encounter, a
Doctor can create a prescription with all structured fields, save it as a
draft, and reopen it with the fields intact. No other feature needs to
exist for this to be demonstrated (encounters are a prerequisite).

**Acceptance Scenarios**:

1. **Given** a signed-in Doctor and a finalised encounter, **When** they
   create a prescription with medication name, strength, dosage, route,
   frequency, duration, and instructions, **Then** a prescription is
   created in Draft status, linked to the encounter, the patient, and the
   Doctor as prescriber, with created-by and created-at recorded.
2. **Given** a prescription form missing a required structured field (name,
   strength, dosage, route, frequency, or duration),
   **When** they submit it,
   **Then** the prescription is not created and a field-level error names
   the missing field.
3. **Given** a signed-in Doctor, **When** they try to create a prescription
   on a draft (not finalised) encounter,
   **Then** the system refuses with an understandable error — prescriptions
   attach to a finalised encounter only (see Decisions, P-02).
4. **Given** a signed-in Doctor, **When** they try to create a prescription
   with no encounter (a standalone prescription),
   **Then** the system refuses — every prescription MUST link to an
   encounter and a prescriber (FR-013).
5. **Given** a signed-in Receptionist, **When** they try to create a
   prescription, **Then** the action is denied by the backend with a
   permission error, not just hidden in the UI.

### User Story 2 — Finalise or cancel a prescription (Priority: P2)

A Doctor reviews a draft prescription, finalises it so it becomes the
record of the medication instruction, or cancels it if it is no longer
needed. A finalised prescription cannot be edited in place: changing it
means cancelling it (with a reason) and creating a new one.

**Why this priority**: Draft/finalised/cancelled states are M06's explicit
workflow. Finalisation is the control that turns a working draft into the
instruction other workflows (and a future pharmacy module) may rely on;
cancellation is the safe way to withdraw it.

**Independent Test**: A Doctor can finalise a draft prescription, and can
cancel a draft or finalised prescription with a reason; a cancelled
prescription remains visible as Cancelled with its history, and is never
deleted.

**Acceptance Scenarios**:

1. **Given** a draft prescription, **When** the prescriber finalises it,
   **Then** its status becomes Finalized, with finalised-by and finalised-at
   recorded.
2. **Given** a draft prescription, **When** the prescriber edits a structured
   field and saves, **Then** the draft is updated (no correction record is
   needed — a draft is not yet the instruction).
3. **Given** a finalised prescription, **When** the prescriber tries to edit
   a structured field in place, **Then** the edit is refused — a finalised
   prescription changes only by cancellation and reissue.
4. **Given** a draft or finalised prescription, **When** the prescriber
   cancels it and gives a reason, **Then** its status becomes Cancelled,
   with cancelled-by, cancelled-at, and the reason recorded; the record is
   never deleted.
5. **Given** a cancelled prescription, **When** anyone tries to finalise or
   edit it, **Then** the action is refused — Cancelled is terminal.
6. **Given** a prescription, **When** a Doctor other than the prescriber
   tries to finalise or cancel it, **Then** the action is denied — only the
   prescriber finalises or cancels their own prescription (see Permissions;
   see Open Questions, Q-002).

### User Story 3 — Review prescription history for an encounter (Priority: P3)

A Doctor reviewing a patient opens the encounter and sees its prescriptions
— draft, finalised, and cancelled — with prescriber, timestamps, and
cancellation reasons, so the medication history is reviewable and nothing
is silently lost.

**Why this priority**: A prescription that disappears when cancelled is a
patient-safety failure; the history is what makes the record auditable
(Constitution Principle IV, Master Plan §12.4). It is P3 because reading
history only matters once prescriptions exist.

**Independent Test**: An encounter with a finalised prescription and a
cancelled prescription shows both in its prescription history, with
statuses, prescribers, and timestamps.

**Acceptance Scenarios**:

1. **Given** an encounter with prescriptions in different states, **When**
   the prescriber (or an authorised Doctor) views the encounter,
   **Then** all prescriptions are listed with status, structured fields,
   prescriber, and created / finalised / cancelled timestamps.
2. **Given** a cancelled prescription, **When** it is viewed, **Then** the
   cancellation reason is visible.
3. **Given** a prescription, **When** a Receptionist, Lab Technician, or
   Billing user tries to view it, **Then** access is denied — prescription
   content is clinical content, not scheduling or billing data.
4. **Given** any prescription action, **When** the audit trail is inspected,
   **Then** the audit event records actor, action, prescription, and
   timestamp — and contains no treatment recommendation or dosing logic
   (there is none to record).

### Edge Cases

- What happens when the linked encounter is corrected after a prescription
  was finalised? The prescription is unaffected — it records the
  instruction as given at finalisation. If the encounter correction changes
  the clinical basis, the prescriber cancels and reissues the prescription;
  the system does not do this automatically.
- What happens when a prescription's patient record is Merged or Archived?
  Existing prescriptions stay linked to the surviving MRN (merge) or
  remain readable as history (archive); no prescription is deleted because
  the patient status changed.
- What happens when a Doctor tries to finalise a prescription whose
  encounter belongs to another Doctor? The action is denied — only the
  prescriber finalises or cancels their own prescription.
- What happens when the same medication is prescribed twice for one
  encounter? The system allows it (two separate prescription records, e.g.
  different durations) and does not block or warn — duplicate-medication
  checking is clinical decision support and is out of scope (see Open
  Questions, Q-003).
- What happens when a prescription is requested for a patient with no
  encounter? It cannot be created — the encounter link is mandatory
  (FR-013). A walk-in must first have an encounter (Spec 005).
- What happens when the system is asked for a prescription list? Lists are
  paginated, filtered to the caller's authorised scope (own prescriptions
  for a Doctor), and sorted deterministically.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-013**: The system MUST allow authorised clinicians (Doctors) to
  create and finalize prescription records linked to an encounter (Master
  Plan §8 FR-013, §6 M06). Every prescription MUST link to exactly one
  encounter and one prescriber; a prescription with no encounter MUST be
  refused.
- **FR-013a**: A prescription MUST carry structured medication fields:
  medication name, strength, dosage, route, frequency, duration, and
  instructions (Master Plan §6 M06). Name, strength, dosage, route,
  frequency, and duration are required; instructions are optional free
  text (see Decisions, P-01). Free-text-only prescriptions MUST be refused.
- **FR-013b**: A prescription MUST have statuses Draft, Finalized, and
  Cancelled. Draft → Finalized, Draft → Cancelled, Finalized → Cancelled
  are the only transitions. Cancelled is terminal. A finalised prescription
  MUST NOT be edited in place; changing it requires cancellation (with a
  reason) and a new prescription.
- **FR-013c**: Prescriptions MUST attach to a finalised encounter only
  (see Decisions, P-02). A prescription on a draft encounter MUST be
  refused.
- **FR-013d**: The system MUST NOT generate treatment recommendations and
  MUST NOT make automated dosing decisions. There is no recommendation,
  suggestion, default dose, or calculated duration anywhere in this
  feature (Master Plan §4.3, M06). Every field value is entered by the
  prescriber.
- **FR-020**: The system MUST record audit events for prescription creation,
  finalisation, and cancellation (actor, action, target, timestamp,
  outcome) (Master Plan §8 FR-020, §12.4).
- **FR-021**: The system MUST validate input and enforce business rules on
  the backend before saving (Master Plan §8 FR-021): required structured
  fields present; encounter finalised; prescriber is the authoring Doctor.
- **FR-022**: The system MUST preserve prescription history and MUST NOT
  hard-delete prescriptions. Cancellation is a status change with a
  recorded reason, never a deletion (Master Plan §8 FR-022).
- **FR-023**: The system MUST return understandable errors without exposing
  secrets, stack traces, or unnecessary patient data (Master Plan §8
  FR-023).
- **FR-024**: Prescription lists MUST be paginated, filtered to the caller's
  authorised scope, and sorted deterministically (Master Plan §8 FR-024).

### Key Entities

- **Prescription**: A medication instruction record. Key attributes:
  encounter (FK → Encounter, required), patient (FK → Patient, via the
  encounter, MRN `MC-YYYY-NNNNNN`), prescriber (FK → User, Doctor role,
  required), medication name (required), strength (required), dosage
  (required), route (required), frequency (required), duration (required),
  instructions (optional free text), status (Draft / Finalized /
  Cancelled), created-by, created-at, finalised-by, finalised-at,
  cancelled-by, cancelled-at, cancellation reason. One diagnosis does not
  automatically imply a prescription, and a prescription does not imply a
  diagnosis beyond the encounter it links to (Master Plan §7.1).
- **AuditEvent**: Who did what, when, to which prescription, and whether it
  succeeded. Audit records MUST NOT contain treatment recommendations or
  dosing logic (there is none in this feature).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Doctor can create a structured prescription on a finalised
  encounter, with all required fields, and save it as a draft in a single
  uninterrupted flow.
- **SC-002**: A draft prescription can be finalised only by its prescriber;
  a finalised prescription cannot be edited in place; cancellation
  requires a reason and is terminal.
- **SC-003**: 100% of prescriptions in test data link to an encounter and a
  prescriber; zero standalone prescriptions exist.
- **SC-004**: Every prescription creation, finalisation, and cancellation in
  test data has a corresponding audit event with actor and timestamp.
- **SC-005**: A Receptionist attempting to create, finalise, or cancel a
  prescription is denied by the backend (not merely by a hidden button) in
  automated permission tests; a Doctor attempting to finalise or cancel
  another Doctor's prescription is likewise denied.
- **SC-006**: The implemented feature contains no treatment-recommendation
  or automated-dosing behaviour: no endpoint, field, or UI element suggests
  a medication, dose, or duration. (Verified by review against FR-013d.)
- **SC-007**: All P1 acceptance scenarios above pass against the implemented
  feature before it is considered complete; P2/P3 scenarios pass before the
  feature is considered fully complete.

## Permissions

| Role | Create prescription | Edit own draft | Finalise own prescription | Cancel own prescription | View prescription |
|---|---|---|---|---|---|
| Admin | No | No | No | No | No — no automatic entitlement to clinical content (Master Plan §5) |
| Receptionist / Registration | No | No | No | No | No |
| Doctor / Clinician | Yes — on a finalised encounter, as prescriber | Yes | Yes | Yes | Yes — own prescriptions; other Doctors' prescriptions only where an authorised care relationship exists (same open rule as Spec 005 Q-004) |
| Nurse | No in this spec | No | No | No | No in this spec — granted only as the nursing spec (M07) allows |
| Lab Technician | No | No | No | No | No |
| Pharmacist | No in this spec | No | No | No | No in this spec — dispensing is M12 (future); whether a Pharmacist gets a read-only view for dispensing preparation is an Open Question (Q-004) |
| Billing | No | No | No | No | No — clinical content hidden unless specifically needed (Master Plan §5); not granted here |

Only a Doctor prescribes. Patient demographics/summary access is governed
by Spec 001. Nurse / Lab / Pharmacist / Billing have no patient-search
access in v1 (Spec 001): their own feature specs grant the search access
their workflows need, when those features are specified.

## Data fields

Prescription: encounter (required FK), prescriber (required, the authoring
Doctor), medication name (required text), strength (required text, e.g.
"500 mg"), dosage (required text, e.g. "1 tablet"), route (required text,
e.g. "Oral"), frequency (required text, e.g. "twice daily"), duration
(required text, e.g. "7 days"), instructions (optional free text),
status (Draft / Finalized / Cancelled), created-by, created-at,
finalised-by, finalised-at, cancelled-by, cancelled-at, cancellation
reason (required when cancelling).

All structured fields are free text entered by the prescriber in v1 — no
medication catalog, no coded values, no dose calculation (see Open
Questions, Q-001). Patient identity fields are owned by Spec 001 and are
not re-decided here: MRN `MC-YYYY-NNNNNN`; required patient fields full
name, date of birth, phone, gender (Male / Female / Other), CNIC / B-Form
number (`national_id`, 13 digits, encrypted at rest, full view only
Receptionist/Admin, masked otherwise, never searchable); blood group
optional; patient statuses Active / Inactive / Merged / Archived.

## Assumptions

- The hospital is a single organisation; one deployment instance (Master Plan
  §2.4).
- Authentication and RBAC (Master Plan M01), patient registration (Spec 001,
  M03), and encounters (Spec 005, M05) exist before this feature; prescription
  endpoints assume a signed-in Doctor and a finalised encounter.
- **Module status**: this feature is committed module M7 (owner decision
  2026-11-22); it is implemented only once the owner approves this spec.
- All demo/test data is synthetic; no real patient records are used.
- Display timezone for dates/times is Asia/Karachi; timestamps are stored in
  UTC and displayed in Asia/Karachi (ADR-001).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner (2026-11-22);
  Python 3.12 / Node 20 LTS; Django session auth, no JWT in v1.

## Decisions

Decisions recorded here are binding for implementation within this spec;
changing one requires an owner decision and a spec amendment. Numbers are
local to this spec (P-01…) and do not collide with Spec 001's D-01…D-13 or
Spec 005's E-01…E-08.

1. **P-01 — All six structured fields required except instructions.**
   Medication name, strength, dosage, route, frequency, and duration are
   required; instructions are optional free text. Rationale: M06 requires
   validating required fields and avoiding ambiguous free-text-only
   prescriptions; a prescription missing strength or route is ambiguous,
   while instructions genuinely may be empty ("as directed" is not
   recorded as a default — if the prescriber has no extra instructions,
   the field stays empty).
2. **P-02 — Prescriptions attach to a finalised encounter only.**
   Rationale: a prescription is the record of a medication instruction
   arising from a completed clinical assessment; attaching it to a draft
   encounter would let prescriptions exist for visits whose documentation
   was never finalised. The encounter must be finalised first.
3. **P-03 — A finalised prescription is never edited in place; change means
   cancel (with reason) and reissue.** Rationale: the finalised
   prescription is the instruction of record; silent in-place edits would
   destroy the history of what was instructed. Cancel-and-reissue keeps
   every version visible (FR-022).
4. **P-04 — Only the prescriber finalises or cancels their own
   prescription.** Rationale: authorship is the accountability mechanism
   for clinical content (as in Spec 005 E-07); letting another clinician
   alter a colleague's prescription would break it. Whether a second
   clinician may ever cancel is left open (Q-002).
5. **P-05 — No medication catalog, no coded values, no dose calculation in
   v1.** Rationale: no formulary or catalog has been agreed, and any dose
   logic would be automated dosing — explicitly forbidden (FR-013d).
   Structured fields are prescriber-entered free text in v1. A catalog is
   a later spec decision (Q-001), not something invented here.

## Open Questions

1. **Q-001 — Should medication name / strength / route come from an
   admin-managed catalog, or stay free text?** A catalog would improve
   consistency but needs a formulary source and maintenance ownership
   (M02 reference data). Undecided; v1 uses prescriber-entered free text
   (P-05).
2. **Q-002 — May a Doctor other than the prescriber cancel a prescription
   (e.g. a senior clinician, or the covering Doctor)?** This spec says no
   (P-04). A supervised-cancellation workflow would need an owner
   decision.
3. **Q-003 — Is any safety checking wanted (drug interactions, allergies,
   duplicate medication)?** Any such check is clinical decision support,
   which Master Plan §4.3 puts out of scope unless explicitly approved.
   Undecided and not implemented in v1; even a warning would need an
   explicit owner decision and a clinical knowledge source.
4. **Q-004 — Does a Pharmacist get a read-only view of finalised
   prescriptions (for dispensing preparation)?** Dispensing itself is M12
   (future). Whether a Pharmacist needs to see prescriptions before M12
   exists is undecided; this spec grants no Pharmacist access.
5. **Q-005 — Is there a prescription print / hand-to-patient step?** The
   Master Plan does not define one. Printing, patient handout format, and
   whether a printed prescription is the record or a copy are undecided
   and not implemented in v1.
6. **Q-006 — Can one prescription cover multiple medications, or is it one
   medication per prescription?** This spec models one medication per
   prescription record (M06 lists singular medication fields; Master Plan
   §11 lists one prescription per medication instruction). A multi-item
   prescription would be a different data model and needs an owner
   decision if wanted.

## Deferred (not decided here)

- **Pharmacy / dispensing (M12)**: future module; this spec defines no
  dispensing fields, stock, or pharmacist workflow.
- **Clinical decision support of any kind**: explicitly out of scope
  (Master Plan §4.3) unless the owner approves it — including interaction
  and allergy checks.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1;
  §§19–23 (deployment, risk register, governance/decision log, acceptance,
  open decisions) are listed in the contents but absent from the document.
  Explicitly deferred: they must be supplied or formally deferred before
  release planning (Phase 8), but they do not block this feature.
- **Module status**: this feature is committed module M7 (owner decision
  2026-11-22); its spec is still a draft awaiting the owner's approval
  before implementation.
