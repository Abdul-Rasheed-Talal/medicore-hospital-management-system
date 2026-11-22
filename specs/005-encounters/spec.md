# Feature Specification: Encounters / Consultation

**Feature Branch**: `docs/medicore-all-specs` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — not yet approved by the owner. This is a P0 Core feature
(Master Plan §4.2), but it is still a draft: the exact clinical content
requires review (Master Plan §4.2, M05), and the Open Questions below must be
resolved before implementation.

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline), §4 P0
encounter/visit record, §5 Doctor / Clinician and Reception actors, §6 M05,
§7 WF-02 and §7.1 (appointment vs. encounter), §8 FR-011 / FR-012, §11
Encounter and Diagnosis entities, §12.4 Clinical record audit; MediCore
Constitution v1.0.0, Principles I, III, IV, V, VI, VII; Spec 001 Patient
Registration (patient identity, MRN, permissions baseline).

## Overview

### Problem

An appointment reserves a visit; it does not record the care that actually
happened. Without an encounter record, the hospital has a schedule but no
clinical documentation: no reason for visit, no notes, no diagnosis, and no
way to show what a clinician did during a visit. Later workflows —
prescriptions, laboratory requests, billing — all hang off the encounter as
the record of the actual care interaction. The encounter is also the point
where clinical content enters the system, so it is where authorship,
finalisation, correction traceability, and keeping clinical content out of
logs and reports matter most.

This spec is deliberately narrow: start an encounter from an arrived
appointment or an approved walk-in, record reason for visit, structured
notes and diagnosis entries, save as draft or finalise, and correct a
finalised encounter only through a traceable correction. It does not include
prescriptions, laboratory requests, billing, nursing observations, or a
patient portal — those are separate features with their own specifications.

### Scope

**In scope**

- Start an encounter from an arrived appointment, or from an approved walk-in
  with no prior appointment (FR-011, WF-02)
- Record encounter date/time, responsible clinician, reason for visit,
  structured notes, and diagnosis entries (FR-012)
- Save an encounter as draft; finalise/close it according to an explicit
  workflow (FR-011, FR-012)
- Preserve authorship and timestamps on the encounter and on every diagnosis
  entry; corrections to a finalised encounter are traceable, never silent
  overwrites (FR-012, FR-022)
- Keep clinical content out of general-purpose logs, audit metadata, and
  unnecessary reports (M05, Master Plan §12.3)
- View an encounter and authorised history for a patient (read-only at this
  stage; later features link to it)

**Out of scope**

- Appointment scheduling, arrival/check-in itself (appointment feature, M04;
  this spec consumes the "arrived" state, it does not define it)
- Prescriptions (Spec 006), laboratory requests/results (Spec 007), billing,
  nursing observations/vital signs (M07), inpatient admission
- Clinical decision support, automated diagnosis, triage recommendations, or
  treatment advice (Master Plan §4.3 — out of scope unless explicitly
  approved)
- Diagnosis coding systems (ICD or other) — free text in v1, coding deferred
  (see Decisions, E-03)
- Patient portal, notifications, multi-hospital tenancy, real patient records;
  all demo/test data is synthetic

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Start an encounter and save it as a draft (Priority: P1)

A Doctor opens their work queue, sees an arrived patient (or an approved
walk-in), starts an encounter, records the reason for visit, and saves it as
a draft so the documentation can be completed during or after the visit.

**Why this priority**: The encounter is the P0 core record of the patient
visit workflow (Master Plan §4.2, §17 Phase 5, Gate D). Without a started
encounter there is nothing for notes, diagnosis, prescriptions, or lab
requests to attach to.

**Independent Test**: With a synthetic patient and an arrived appointment, a
Doctor can start an encounter, enter a reason for visit, save it as a draft,
and reopen it later with the draft content intact. No other feature needs to
exist for this to be demonstrated (appointments are a prerequisite only for
the appointment-linked path; the walk-in path is testable without them).

**Acceptance Scenarios**:

1. **Given** a signed-in Doctor and an appointment in Arrived status for a
   patient, **When** the Doctor starts an encounter from that appointment,
   **Then** an encounter is created in Draft status, linked to the patient,
   the appointment, and the Doctor as responsible clinician, with created-by
   and created-at recorded.
2. **Given** a signed-in Doctor and an approved walk-in (no appointment),
   **When** the Doctor starts an encounter for that patient,
   **Then** an encounter is created in Draft status linked to the patient and
   the Doctor, with no appointment link.
3. **Given** a draft encounter, **When** the Doctor enters a reason for visit
   and saves,
   **Then** the draft is stored with the reason for visit, author, and
   updated-at; the appointment (if any) is not marked complete by this alone.
4. **Given** a signed-in Doctor, **When** they try to start an encounter for
   a patient whose appointment has not arrived (e.g. still Scheduled),
   **Then** the system refuses with an understandable error — an encounter
   may only start from an arrived appointment or an approved walk-in.
5. **Given** a signed-in Doctor, **When** they try to start a second open
   encounter for the same patient while one is already in Draft,
   **Then** the system refuses and points to the existing draft — one open
   encounter per patient at a time (see Decisions, E-05).
6. **Given** a signed-in Receptionist, **When** they try to start an
   encounter, **Then** the action is denied by the backend with a permission
   error, not just hidden in the UI.

### User Story 2 — Record notes and diagnosis, then finalise (Priority: P2)

A Doctor completes a draft encounter by recording structured notes and one
or more diagnosis entries (free text in v1), then finalises it. Finalisation
locks the encounter against casual editing and records who finalised it and
when.

**Why this priority**: Draft capture is the must-have; finalisation is the
workflow control that turns working notes into the visit record other
workflows (prescriptions, lab, billing) may rely on. It is M05's
"finalize/close according to an explicit workflow".

**Independent Test**: A Doctor can complete a draft with notes and a
diagnosis, finalise it, and the finalised encounter shows author, created,
and finalised timestamps; a second Doctor cannot finalise the first
Doctor's draft.

**Acceptance Scenarios**:

1. **Given** a draft encounter, **When** the authoring Doctor adds structured
   notes and at least one diagnosis entry and finalises it,
   **Then** the encounter status becomes Finalized, with finalised-by and
   finalised-at recorded, and the diagnosis entries keep their own author
   and timestamp.
2. **Given** a draft encounter with no diagnosis entry, **When** the Doctor
   tries to finalise it, **Then** finalisation is refused with an
   understandable error — a finalised encounter must carry at least one
   diagnosis entry (see Decisions, E-04).
3. **Given** a draft encounter, **When** a Doctor other than the author tries
   to finalise it, **Then** the action is denied — only the authoring Doctor
   finalises their own encounter (see Permissions).
4. **Given** a finalised encounter, **When** the authoring Doctor tries to
   edit its notes or diagnosis in place, **Then** the edit is refused — a
   finalised encounter changes only through a recorded correction (User
   Story 3).
5. **Given** a finalised encounter, **When** an authorised Doctor views it,
   **Then** they see the notes, diagnosis entries, author, and created /
   finalised timestamps — and no other patient's encounters.

### User Story 3 — Correct a finalised encounter traceably (Priority: P3)

A Doctor discovers an error in a finalised encounter (e.g. a wrong
diagnosis wording). They record a correction, which preserves the original
text, records the new text, the author, the timestamp, and a reason — the
history is visible to anyone authorised to view the encounter.

**Why this priority**: Clinical errors are inevitable; a silently overwritten
record is a data-integrity and patient-safety failure (Constitution
Principle IV, Master Plan §6 M05, §12.4). Traceable correction is what makes
the encounter record trustworthy after finalisation.

**Independent Test**: Correcting a diagnosis on a finalised encounter leaves
the original entry visible in the correction history with author, timestamp,
and reason, and the current view shows the corrected value.

**Acceptance Scenarios**:

1. **Given** a finalised encounter, **When** the authoring Doctor corrects a
   diagnosis entry and gives a reason,
   **Then** a correction record is created (old value, new value, author,
   timestamp, reason), the current value is updated, and the original value
   remains visible in the correction history.
2. **Given** a correction is saved, **When** an authorised Doctor later views
   the encounter, **Then** the full correction history is visible in
   chronological order.
3. **Given** a finalised encounter, **When** a Doctor other than the author
   tries to correct it, **Then** the action is denied (see Open Questions,
   Q-005 — whether a second clinician may ever correct).
4. **Given** a draft encounter, **When** the author edits notes or diagnosis,
   **Then** the edit is stored directly — no correction record is needed,
   because a draft is not yet the visit record.
5. **Given** any encounter action, **When** the audit trail is inspected,
   **Then** the audit event records actor, action, encounter, and timestamp —
   and contains no clinical note or diagnosis text (see Decisions, E-06).

### Edge Cases

- What happens when the appointment is cancelled or marked no-show after an
  encounter was started from it? The encounter stays linked to the
  appointment as it was; the encounter itself is unaffected, and the
  appointment's later status change does not delete or finalise the
  encounter. (The appointment feature owns appointment status rules.)
- What happens when a Doctor starts an encounter and the patient leaves
  before finalisation? The encounter remains a draft; it is not
  auto-finalised, and a draft never counts as a completed visit record.
- What happens when an encounter's patient record is Merged or Archived?
  Existing encounters stay linked to the surviving MRN (merge) or remain
  readable as history (archive); no encounter is deleted because the
  patient status changed.
- What happens when a Doctor tries to view an encounter for a patient they
  are not responsible for? Access is denied by the backend (object-level
  check) unless the Doctor is the responsible clinician or an explicitly
  authorised care relationship exists — see Open Questions, Q-004.
- What happens when a diagnosis entry is added to a draft after another
  diagnosis was already added? Each entry is a separate row with its own
  author and timestamp; entries are never merged into one text block.
- What happens when the system is asked for an encounter list? Lists are
  paginated, filtered by the caller's authorised scope (own encounters for a
  Doctor, schedule context only for a Receptionist), and never return
  clinical content in a list view beyond reason for visit where the caller's
  role permits it (see Permissions).
- What happens when a walk-in has not been approved? No encounter may be
  started — "approved walk-in" is a defined state owned by the appointment /
  front-desk workflow; this spec does not define the approval step (see Open
  Questions, Q-001).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-011**: The system MUST allow authorised clinicians (Doctors) to create
  and maintain encounters linked to patients — from an arrived appointment
  or an approved walk-in — and MUST keep the encounter linked to the
  patient, the responsible clinician, and the appointment where one exists
  (Master Plan §8 FR-011, §6 M05, §7 WF-02).
- **FR-012**: The system MUST store encounter notes and diagnosis information
  with authorship and timestamps: encounter created-by / created-at /
  finalised-by / finalised-at, and per-diagnosis-entry author and timestamp
  (Master Plan §8 FR-012, §6 M05).
- **FR-012a**: Diagnosis entries in v1 MUST be free text; no diagnosis
  coding system is required or accepted in v1 (see Decisions, E-03).
- **FR-012b**: An encounter MUST have statuses Draft and Finalized only in
  v1. A draft MAY be edited by its author; a finalised encounter MUST NOT
  be edited in place — changes MUST go through a recorded correction
  (see User Story 3).
- **FR-012c**: A finalised encounter MUST carry at least one diagnosis entry
  and a reason for visit; finalisation MUST be refused otherwise (see
  Decisions, E-04).
- **FR-012d**: Corrections to a finalised encounter MUST be recorded as
  separate correction rows (field, old value, new value, author, timestamp,
  reason). The original value MUST remain visible in the correction history.
  Corrections MUST NOT silently overwrite history (Master Plan §8 FR-022).
- **FR-012e**: Clinical content (notes text, diagnosis text) MUST NOT appear
  in application logs, audit-event metadata, error messages, or general
  reports. Audit events record actor, action, target encounter, timestamp,
  and outcome only (see Decisions, E-06).
- **FR-020**: The system MUST record audit events for encounter creation,
  finalisation, and correction (actor, action, target, timestamp, outcome),
  without clinical content (Master Plan §8 FR-020, §12.4).
- **FR-021**: The system MUST validate input and enforce business rules on
  the backend before saving (Master Plan §8 FR-021): reason for visit is
  required to save a draft; notes and at least one diagnosis entry are
  required to finalise; encounter date/time must not be in the future.
- **FR-022**: The system MUST preserve encounter history and MUST NOT
  hard-delete encounters. There is no encounter delete in v1 (Master Plan
  §8 FR-022).
- **FR-023**: The system MUST return understandable errors without exposing
  secrets, stack traces, or unnecessary patient data (Master Plan §8
  FR-023).
- **FR-024**: Encounter lists MUST be paginated, filtered to the caller's
  authorised scope, and sorted deterministically (Master Plan §8 FR-024).

### Key Entities

- **Encounter**: The actual care interaction / visit record. Key attributes:
  patient (FK → Patient, MRN `MC-YYYY-NNNNNN`), appointment (FK →
  Appointment, nullable — walk-ins have none), responsible clinician
  (FK → User, Doctor role), encounter date/time, reason for visit
  (required), status (Draft / Finalized), created-by, created-at,
  finalised-by, finalised-at. Distinct from an Appointment, which only
  reserves a visit (Master Plan §7.1).
- **EncounterNote**: Structured notes belonging to one encounter. Key
  attributes: encounter (FK), note content (structured fields — exact
  fields are an Open Question, Q-002), author, created-at, updated-at.
  Notes live on the encounter; a draft's notes are editable by the author,
  a finalised encounter's notes change only via EncounterCorrection.
- **DiagnosisEntry**: One clinical assessment attached to an encounter. Key
  attributes: encounter (FK), diagnosis text (free text in v1, no code),
  author, created-at. An encounter has zero or more entries while a draft,
  and at least one when finalised. One diagnosis does not automatically
  imply a prescription (Master Plan §7.1).
- **EncounterCorrection**: One traceable change to a finalised encounter. Key
  attributes: encounter (FK), field / entry corrected, old value, new value,
  author, timestamp, reason (required).
- **AuditEvent**: Who did what, when, to which encounter, and whether it
  succeeded. Audit records MUST NOT contain clinical note or diagnosis text.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Doctor can start an encounter from an arrived appointment,
  record a reason for visit, and save it as a draft in a single
  uninterrupted flow.
- **SC-002**: A draft encounter can be finalised only with a reason for visit,
  notes, and at least one diagnosis entry; finalisation records author and
  timestamp.
- **SC-003**: 100% of corrections to finalised encounters in test data leave
  a correction record with old value, new value, author, timestamp, and
  reason; zero are silent overwrites.
- **SC-004**: Every encounter creation, finalisation, and correction in test
  data has a corresponding audit event with actor and timestamp, and no
  audit event contains clinical note or diagnosis text.
- **SC-005**: A Receptionist attempting to create, edit, or finalise an
  encounter is denied by the backend (not merely by a hidden button) in
  automated permission tests; a Doctor attempting to finalise or correct
  another Doctor's encounter is likewise denied.
- **SC-006**: All P1 acceptance scenarios above pass against the implemented
  feature before it is considered complete; P2/P3 scenarios pass before the
  feature is considered fully complete.

## Permissions

| Role | Start encounter | Edit own draft | Finalise own encounter | Correct own finalised encounter | View encounter (clinical content) | View schedule context |
|---|---|---|---|---|---|---|
| Admin | No | No | No | No | No — no automatic entitlement to clinical content (Master Plan §5) | No |
| Receptionist / Registration | No | No | No | No | No | Yes — read-only: appointment, patient identity (MRN, name), arrival status; no notes or diagnosis |
| Doctor / Clinician | Yes — own encounters only | Yes | Yes | Yes | Yes — own encounters; other Doctors' encounters only where an authorised care relationship exists (see Q-004) | Yes — own work queue |
| Nurse | No in this spec | No | No | No | No in this spec — granted only as the nursing spec (M07) allows | No |
| Lab Technician | No | No | No | No | No — lab access is request-scoped, granted by Spec 007, not by this spec | No |
| Pharmacist | No | No | No | No | No — granted only as the prescription/pharmacy specs allow | No |
| Billing | No | No | No | No | No — clinical notes hidden unless specifically needed (Master Plan §5); not granted here | No |

Doctor access here is to *clinical* content. Patient demographics/summary
access is governed by Spec 001. Nurse / Lab / Pharmacist / Billing have no
patient-search access in v1 (Spec 001): their own feature specs grant the
search access their workflows need, when those features are specified.
Admin has no clinical-content access by default (Master Plan §5: "no
automatic entitlement to read all clinical content unless explicitly
required") — administration of users and reference data is not clinical
access, and any exception requires an explicit owner decision.

## Data fields

Encounter: patient (required, FK by MRN), appointment (optional, FK),
responsible clinician (required, the authoring Doctor), encounter
date/time (required, not in the future), reason for visit (required text),
status (Draft / Finalized), created-by, created-at, finalised-by,
finalised-at. Notes: structured note content (exact fields — Open Question
Q-002), author, timestamps. Diagnosis entry: free-text diagnosis (required
at finalisation), author, created-at. Correction: field/entry, old value,
new value, author, timestamp, reason (required).

Patient identity fields are owned by Spec 001 and are not re-decided here:
MRN `MC-YYYY-NNNNNN`; required patient fields full name, date of birth,
phone, gender (Male / Female / Other), CNIC / B-Form number (`national_id`,
13 digits, encrypted at rest, full view only Receptionist/Admin, masked
otherwise, never searchable); blood group optional; patient statuses
Active / Inactive / Merged / Archived.

## Assumptions

- The hospital is a single organisation; one deployment instance (Master Plan
  §2.4).
- Authentication and RBAC (Master Plan M01) and patient registration
  (Spec 001, M03) exist before or alongside this feature; encounter
  endpoints assume a signed-in user with a role.
- The appointment feature (M04, not yet specified) exists before or
  alongside the appointment-linked path: it owns appointment statuses
  (including Arrived) and the walk-in approval step. The walk-in path of
  this spec depends on that definition (see Open Questions, Q-001).
- All demo/test data is synthetic; no real patient records are used.
- Display timezone for dates/times is Asia/Karachi; timestamps are stored in
  UTC and displayed in Asia/Karachi (ADR-001).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner (2026-11-22);
  Python 3.12 / Node 20 LTS; Django session auth, no JWT in v1.

## Decisions

Decisions recorded here are binding for implementation within this spec;
changing one requires an owner decision and a spec amendment. Numbers are
local to this spec (E-01…) and do not collide with Spec 001's D-01…D-13.

1. **E-01 — Encounter starts only from an arrived appointment or an approved
   walk-in.** Rationale: WF-02 step 1 is arrival/check-in; an encounter
   before arrival would let clinical documentation exist for a visit that
   never happened. A walk-in is the only appointment-free path, and it must
   be approved (see Q-001 for who approves).
2. **E-02 — Appointment and encounter are distinct records; a completed
   appointment does not mean clinical documentation is complete**
   (Master Plan §7 WF-02 expected outcome, §7.1). Rationale: the schedule
   and the care record answer different questions; conflating them would
   mark visits "done" with no clinical record.
3. **E-03 — Diagnosis entries are free text in v1; diagnosis coding is
   deferred.** Rationale: Master Plan M05 says "using the agreed coding or
   free-text approach" and §4.2 says exact clinical content requires
   review; no coding system (ICD or other) has been agreed, and choosing
   one without clinical review would be a guess. Free text is testable now;
   a coding field is added by a later spec amendment once a system is
   agreed. This is a deliberate deferral, not an oversight.
4. **E-04 — A finalised encounter must carry a reason for visit, notes, and
   at least one diagnosis entry.** Rationale: a finalised record with no
   diagnosis is not a usable visit record for the workflows that depend on
   it (prescriptions, lab, billing); refusing to finalise an empty record
   is cheaper than chasing missing documentation later. A draft may be
   saved with only a reason for visit.
5. **E-05 — One open (Draft) encounter per patient at a time.**
   Rationale: two simultaneous open encounters for one patient would split
   the visit record and make authorship ambiguous. A new encounter may be
   started once the previous one is finalised.
6. **E-06 — No clinical content in logs, audit metadata, error messages, or
   general reports.** Rationale: Master Plan M05 ("keep clinical content
   out of general-purpose logs and unnecessary reports"), §11.2, §12.3, and
   Constitution Principle III. Audit events record actor, action, target
   encounter, timestamp, and outcome only. Reports that need clinical
   content require their own explicit authorisation (not granted here).
7. **E-07 — Only the authoring Doctor creates, edits, finalises, and
   corrects their own encounter.** Rationale: authorship is the
   accountability mechanism for clinical content (FR-012); letting another
   clinician silently alter a colleague's record would break it. Whether a
   second clinician may ever correct is left open (Q-005).
8. **E-08 — No encounter delete in v1; no encounter status beyond Draft /
   Finalized in v1.** Rationale: deletion would destroy the visit record
   (FR-022); a Cancelled/Voided status has no defined workflow behind it
   and is not added speculatively. If a void workflow is ever needed, it
   requires its own spec decision.

## Open Questions

1. **Q-001 — Who approves a walk-in, and what does "approved" mean?**
   WF-02 and M05 both say "approved walk-in" but no step defines the
   approval. Is it a Receptionist recording arrival for a patient with no
   appointment, an Admin decision, or a Doctor accepting the patient? The
   appointment feature (M04) must define this before the walk-in path can
   be implemented; the appointment-linked path is not blocked by it.
2. **Q-002 — What are the structured-note fields?** M05 requires
   "structured notes" but the Master Plan does not list the fields, and
   §4.2 says exact clinical content requires review. Candidate fields
   (e.g. history, examination, assessment, plan) must be agreed with
   clinical review; until then the note content is a single structured
   text area, not a set of invented clinical sections.
3. **Q-003 — Is there an encounter "closed/completed" state beyond
   Finalized, or a reopen rule?** M05 says "finalize/close according to an
   explicit workflow" without defining close. This spec treats Finalized as
   the terminal state; whether a finalised encounter can ever be reopened
   (and by whom) is undecided.
4. **Q-004 — Which Doctors may view another Doctor's encounters?** Master
   Plan §5 allows clinical records "for assigned/authorized care
   relationships" without defining the relationship. This spec grants a
   Doctor their own encounters only; cross-clinician viewing (referral,
   cover, department) needs a defined rule.
5. **Q-005 — May a Doctor other than the author correct a finalised
   encounter (e.g. a senior clinician or the covering Doctor)?**
   This spec says no (E-07). A supervised-correction or countersign
   workflow would need an owner decision.
6. **Q-006 — How long may an encounter stay in Draft, and who chases
   unfinished drafts?** No Master Plan rule exists. A stale-draft rule
   (reminder, escalation, auto-close) is undecided and not implemented
   in v1.
7. **Q-007 — Does finalising an encounter change the linked appointment's
   status (e.g. to Completed)?** WF-02's expected outcome says a completed
   appointment does not itself mean documentation is complete, but the
   reverse direction — whether finalisation completes the appointment — is
   not stated. Owned by the appointment feature (M04); this spec does not
   change appointment status.

## Deferred (not decided here)

- **Prescriptions, laboratory, billing, nursing observations**: separate
  specs (006, 007, and later); this spec grants them no permissions and
  defines no fields for them beyond the encounter link they will use.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1;
  §§19–23 (deployment, risk register, governance/decision log, acceptance,
  open decisions) are listed in the contents but absent from the document.
  Explicitly deferred: they must be supplied or formally deferred before
  release planning (Phase 8), but they do not block this feature.
- **Visit history on the patient summary**: which encounters appear there
  and for which roles is decided by the patient-summary view; this spec
  defines the encounter record, not its presentation on the patient
  profile.
