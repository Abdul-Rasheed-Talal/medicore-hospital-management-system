# Feature Specification: Appointment Management

**Feature Branch**: `docs/medicore-all-specs` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — not yet approved by the owner. The statuses, conflict
rules, and patient link below follow the Master Plan and the already
approved Spec 001 (patient identity); everything else that needs a choice
is listed under "Open Questions" and must be decided before implementation.

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline), §4 P0
appointment scheduling, §6 M04, §7 WF-01 / WF-02, §8 FR-008 / FR-009 /
FR-010, §11 data architecture; MediCore Constitution v1.0.0, Principles I,
III, IV, V, VI, VII; ADR-001 (ACCEPTED 2026-11-22); Spec 001 (patient
registration, MRN, search, privacy rules); Spec 002 (auth/RBAC); Spec 003
(hospital setup — departments, staff, visit types).

**Release status**: P0 core capability (Master Plan §4.2). This is not a
P1 candidate — appointment scheduling and status management enable the
front-desk-to-clinician handoff and are part of the MVP.

## Overview

### Problem

A hospital that books visits in a paper diary or by word of mouth
double-books clinicians, loses track of who is expected when, and cannot
tell a clinician what their day looks like. Appointment management gives
the front desk one controlled way to reserve a visit — linked to a real
patient, a real provider, and a date/time — with validated states from
booking through arrival to completion, and with conflicts refused at the
point of booking rather than discovered in a crowded waiting room.

This feature is deliberately narrow: create, reschedule, and cancel
appointments; status transitions (Scheduled / Arrived / Completed /
Cancelled / No-show); conflict rules; check-in; daily schedules. It does
not include the encounter itself (a separate feature — an appointment
reserves a visit, an encounter records the care given; Master Plan §7.1),
reminders/notifications (M13, future), recurring appointments, or billing.

### Scope

**In scope**

- Create an appointment for a registered patient, a provider, a department, a date/time, and a visit type (Master Plan FR-008, M04; WF-01 steps 4–6)
- Validate required scheduling fields and conflict rules — no overlapping appointment for the same provider at the same time, and no overlapping appointment for the same patient (Master Plan FR-009)
- Reschedule and cancel appointments, with a recorded reason for cancellation (FR-008)
- Record patient arrival / check-in (Master Plan FR-010; WF-02 step 1)
- Statuses Scheduled / Arrived / Completed / Cancelled / No-show, with explicit allowed transitions (M04)
- Daily schedules and search/filter views for authorised staff (M04)
- Audit events for appointment actions (Master Plan FR-020)

**Out of scope**

- Encounter / clinical documentation (separate feature; WF-02 steps 3–6) — an appointment marked Completed does not mean clinical documentation is complete (Master Plan §7 WF-02)
- Walk-in encounters without an appointment (the encounter feature decides that; a walk-in patient is registered first, then given a same-day appointment here)
- Appointment reminders, notifications, patient portal (Master Plan M13, future module)
- Recurring appointments, waiting lists, provider availability calendars / leave blocking (see Open Questions OQ-005, OQ-006)
- Billing / charges for appointments (Master Plan M09, P1 candidate, not specified yet)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Create an appointment (Priority: P1)

A Receptionist searches for an existing patient, picks a provider,
department, date/time, and visit type, and creates the appointment. The
system validates the fields and refuses the booking if it conflicts with
an existing appointment for that provider or that patient.

**Why this priority**: Booking is the core of the module and WF-01 steps
4–6. Without it there is no schedule for clinicians to work from. This is
Master Plan §4, P0 core.

**Independent Test**: With a synthetic patient, provider, and department
registered, a Receptionist can create an appointment and see it in the
provider's daily schedule. No other feature needs to exist for this to be
demonstrated.

**Acceptance Scenarios**:

1. **Given** a signed-in Receptionist and a registered patient found by MRN, **When** they create an appointment with a provider, date/time, and visit type, **Then** the appointment is created with status Scheduled and appears in the provider's daily schedule.
2. **Given** a signed-in Receptionist, **When** they try to create an appointment with a missing required field, **Then** the appointment is not created and a field-level error names the missing field.
3. **Given** a signed-in Receptionist, **When** they try to create an appointment in the past, **Then** the appointment is not created and a business-rule error explains the problem.
4. **Given** an existing appointment for a provider at a given time, **When** a Receptionist tries to create an overlapping appointment for the same provider, **Then** the booking is refused with a conflict error naming the clash — no double-booking.
5. **Given** an existing appointment for a patient at a given time, **When** a Receptionist tries to create an overlapping appointment for the same patient, **Then** the booking is refused with a conflict error.
6. **Given** a signed-in Receptionist, **When** they try to create an appointment for a person with no patient record, **Then** the booking cannot proceed — the person must be registered first (WF-01 steps 2–3; Spec 001). A walk-in is registered, then given a same-day appointment.
7. **Given** a signed-in Receptionist, **When** they try to create an appointment for an Inactive, Merged, or Archived patient, **Then** the booking is refused with an understandable error (only Active patients can be booked).
8. **Given** a signed-in Receptionist, **When** they try to create an appointment with an inactive provider or an inactive visit type, **Then** the booking is refused — inactive reference data cannot be used for new records (Spec 003).

### User Story 2 — Record patient arrival / check-in (Priority: P1)

A Receptionist locates the day's appointment and records the patient's
arrival, so clinical staff see who is waiting (WF-02 step 1).

**Why this priority**: Check-in is the handoff from front desk to
clinician and the trigger for the clinical work queue. Without it, the
schedule cannot tell "expected" from "here". This is Master Plan FR-010.

**Independent Test**: With a Scheduled appointment for today, a
Receptionist can check the patient in; the appointment status becomes
Arrived and the provider's queue shows the patient as waiting.

**Acceptance Scenarios**:

1. **Given** a Scheduled appointment for today, **When** a Receptionist records arrival, **Then** the status becomes Arrived with an arrival timestamp and an audit event.
2. **Given** a Cancelled or Completed appointment, **When** a Receptionist tries to record arrival, **Then** the action is refused — the status transition is not allowed.
3. **Given** an Arrived appointment, **When** a Receptionist tries to record arrival again, **Then** the action is refused (already arrived; no duplicate check-in).

### User Story 3 — Reschedule an appointment (Priority: P2)

A Receptionist moves an appointment to a new date/time, e.g. at the
patient's request. The new slot is conflict-checked the same way as a new
booking, and the change is recorded.

**Why this priority**: Rescheduling is a daily front-desk reality; without
it, staff cancel and re-create, losing history. This is Master Plan
FR-008.

**Independent Test**: A Scheduled appointment can be moved to a free slot;
the appointment keeps its identity, the new time is shown, and the change
is auditable.

**Acceptance Scenarios**:

1. **Given** a Scheduled appointment, **When** a Receptionist reschedules it to a free slot, **Then** the appointment keeps its identity with the new date/time, status stays Scheduled, and an audit event records the old and new times.
2. **Given** a Scheduled appointment, **When** a Receptionist reschedules it to a slot that conflicts for the provider, **Then** the reschedule is refused with a conflict error and the original time is unchanged.
3. **Given** a Scheduled appointment, **When** a Receptionist reschedules it to a past date/time, **Then** the reschedule is refused.
4. **Given** an Arrived, Completed, Cancelled, or No-show appointment, **When** a Receptionist tries to reschedule it, **Then** the action is refused — only Scheduled appointments can be rescheduled (a No-show is rebooked as a new appointment).

### User Story 4 — Cancel an appointment (Priority: P2)

A Receptionist cancels an appointment that will not happen, recording a
reason, so the slot is freed and the record keeps its history instead of
being deleted.

**Why this priority**: Cancellation is the controlled alternative to
deletion (Master Plan FR-022, §9.1). A cancelled slot must be visibly
cancelled, not silently removed. This is Master Plan FR-008.

**Independent Test**: A Scheduled appointment can be cancelled with a
reason; it no longer blocks the provider's slot, and its status and reason
remain visible in history.

**Acceptance Scenarios**:

1. **Given** a Scheduled appointment, **When** a Receptionist cancels it with a reason, **Then** the status becomes Cancelled, the reason is recorded, and an audit event is written.
2. **Given** a Scheduled appointment, **When** a Receptionist tries to cancel it without a reason, **Then** the cancellation is refused — a reason is required.
3. **Given** a Cancelled appointment, **When** a Receptionist tries to cancel it again, **Then** the action is refused (already Cancelled).
4. **Given** a Cancelled appointment, **When** the provider's schedule is checked, **Then** the cancelled appointment does not block the slot — a new appointment may be booked there.
5. **Given** an Arrived appointment, **When** a Receptionist cancels it, **Then** the cancellation succeeds with a reason (the patient arrived but the visit will not proceed) and the status becomes Cancelled.

### User Story 5 — View the daily schedule (Priority: P2)

A Receptionist or Doctor views the day's schedule — by provider,
department, or date — and finds a patient's appointment, to run the day
and to check patients in.

**Why this priority**: The schedule is the working view for the whole
day; without it, appointments are invisible after booking. This is Master
Plan M04 ("daily schedules and search/filter views").

**Independent Test**: With several synthetic appointments across
providers and days, a Receptionist can list today's appointments for one
provider, and a Doctor can list their own day.

**Acceptance Scenarios**:

1. **Given** appointments exist, **When** a Receptionist views the daily schedule for a date, **Then** the appointments are listed in time order with patient, provider, visit type, and status.
2. **Given** appointments exist, **When** a Receptionist filters by provider or department, **Then** only that provider's / department's appointments are listed.
3. **Given** appointments exist, **When** a Receptionist searches by patient MRN or name, **Then** matching appointments are listed (patient search itself follows Spec 001: Receptionist/Admin/Doctor only in v1).
4. **Given** a signed-in Doctor, **When** they view the schedule, **Then** they see their own appointments — and no other provider's patient detail beyond what their role permits.
5. **Given** no appointments exist for a date, **When** the schedule is viewed, **Then** an explicit "no appointments" state is shown (not an empty or ambiguous screen).

### User Story 6 — Mark an appointment Completed or No-show (Priority: P3)

After the visit, the appointment is marked Completed; a patient who never
arrived is marked No-show. Both close the appointment so it no longer
sits in the day's work queue.

**Why this priority**: Closing the loop keeps the schedule truthful, but
it is P3 because the day can run on Scheduled/Arrived alone, and the
clinical record lives in the encounter, not here. This is Master Plan
FR-008 / M04.

**Independent Test**: An Arrived appointment can be marked Completed; a
Scheduled appointment whose time has passed can be marked No-show; both
are terminal states.

**Acceptance Scenarios**:

1. **Given** an Arrived appointment, **When** a Receptionist or the Doctor marks it Completed, **Then** the status becomes Completed with a timestamp and an audit event.
2. **Given** a Scheduled appointment, **When** it is marked No-show, **Then** the status becomes No-show and an audit event is written.
3. **Given** a Completed, Cancelled, or No-show appointment, **When** any status change is attempted, **Then** it is refused — these states are terminal.
4. **Given** an appointment is marked Completed, **When** the encounter feature later looks at it, **Then** the appointment remains linked to the patient and provider — marking an appointment Completed does not itself mean clinical documentation is complete (Master Plan §7 WF-02).

### Edge Cases

- What happens when two Receptionists book the same provider slot at the same time? The database constraint/transaction refuses the second write; only one appointment is created (the conflict check must not rely on the UI alone).
- What happens when an appointment is created for a provider who is later deactivated (Spec 003)? Existing appointments keep their provider link; no new appointment may select that provider.
- What happens when a patient record is merged (Spec 001) after appointments were booked? The appointments keep pointing at the surviving (kept) patient record — the merge handling for linked appointments is decided by the merge implementation, not here; see Open Question OQ-007.
- What happens when an appointment's date arrives and nobody marks it No-show? Whether No-show is set manually or automatically after the time passes is Open Question OQ-004.
- What happens when a patient arrives early or late? The check-in time window (how early, how late) is Open Question OQ-003.
- What happens when a Doctor tries to create an appointment? In v1, creation is Receptionist/Admin work; whether Doctors may create follow-up appointments is Open Question OQ-002.
- What happens when an appointment is booked without a named provider (department only)? Whether department-only appointments exist is Open Question OQ-005.
- What happens when an appointment is deleted? It cannot be — appointments are never hard-deleted; cancellation is the controlled end state (Master Plan FR-022).
- What happens when the appointment duration is not stated? The default duration and whether visit types define one is Open Question OQ-001.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow an authorised Receptionist or Admin to create an appointment for a registered patient, a provider, a date/time, and a visit type (Master Plan FR-008).
- **FR-002**: The system MUST validate required scheduling fields on the backend before saving: patient, provider, date/time, visit type; the date/time MUST NOT be in the past; the patient MUST be Active; the provider and visit type MUST be active (Master Plan FR-009, FR-021).
- **FR-003**: The system MUST refuse an overlapping appointment for the same provider: two appointments for one provider MUST NOT overlap in time (Master Plan FR-009). The check MUST be enforced by the backend (transaction/constraint), not only by the UI.
- **FR-004**: The system MUST refuse an overlapping appointment for the same patient: two appointments for one patient MUST NOT overlap in time (Master Plan FR-009).
- **FR-005**: The system MUST support the statuses Scheduled / Arrived / Completed / Cancelled / No-show and ONLY the allowed transitions in the "Status transitions" table below (Master Plan FR-008).
- **FR-006**: The system MUST allow an authorised Receptionist or Admin to reschedule a Scheduled appointment to a new date/time, re-checking conflicts and the past-date rule, and recording the change (Master Plan FR-008).
- **FR-007**: The system MUST allow an authorised Receptionist or Admin to cancel a Scheduled or Arrived appointment, requiring a recorded reason (Master Plan FR-008, FR-022).
- **FR-008**: The system MUST allow an authorised Receptionist or Admin to record arrival (check-in) for a Scheduled appointment, setting status Arrived with an arrival timestamp (Master Plan FR-010).
- **FR-009**: The system MUST allow an authorised Receptionist, Admin, or the Doctor to mark an Arrived appointment Completed, and an authorised Receptionist or Admin to mark a Scheduled appointment No-show (Master Plan FR-008).
- **FR-010**: The system MUST provide daily schedule views filtered by date, provider, and department, searchable by patient MRN or name (within Spec 001 search permissions), paginated and sorted by time (Master Plan FR-008, FR-024).
- **FR-011**: The system MUST link every appointment to an existing patient record via the MRN (`MC-YYYY-NNNNNN`, Spec 001 D-01); it MUST NOT create an appointment for an unregistered person (Master Plan FR-005, FR-008; WF-01).
- **FR-012**: The system MUST enforce permissions on the backend per the Permissions table (Master Plan FR-002).
- **FR-013**: The system MUST record audit events for appointment creation, rescheduling, cancellation, check-in, completion, and no-show (actor, action, target, timestamp, outcome) (Master Plan FR-020).
- **FR-014**: The system MUST NOT hard-delete appointments; cancellation is the controlled end state (Master Plan FR-022).
- **FR-015**: The system MUST return understandable errors without exposing secrets, stack traces, or unnecessary patient data (Master Plan FR-023).
- **FR-016**: The system MUST show the appointment's patient, provider, department, date/time, visit type, and status — and only the patient information the caller's role may see under Spec 001 (Master Plan FR-006).

### Status transitions (decided — see D-01)

| From | To | Allowed? |
|---|---|---|
| Scheduled | Arrived (check-in) | Yes |
| Scheduled | Cancelled | Yes |
| Scheduled | No-show | Yes |
| Scheduled | Completed | No (must arrive first) |
| Arrived | Completed | Yes |
| Arrived | Cancelled | Yes |
| Arrived | No-show | No (the patient arrived) |
| Arrived | Scheduled | No |
| Completed / Cancelled / No-show | Any | No (terminal) |

"Arrived" is the check-in state: Master Plan M04 lists "arrived, checked-in"
as the same step and WF-02 step 1 is "records arrival/check-in", so this
spec uses one status, Arrived, for both words (D-02).

### Traceability to Master Plan requirements

| Master Plan FR | Covered by (this spec) |
|---|---|
| FR-008 Appointments | FR-001, FR-005, FR-006, FR-007, FR-009, FR-010 |
| FR-009 Scheduling rules | FR-002, FR-003, FR-004 |
| FR-010 Check-in | FR-008 |
| FR-002 Authorization | FR-012 |
| FR-005 Patient registration (link) | FR-011 |
| FR-006 Patient search (within schedule search) | FR-010, FR-016 |
| FR-020 Audit trail | FR-013 |
| FR-021 Validation | FR-002 |
| FR-022 History | FR-007, FR-014 |
| FR-023 Error handling | FR-015 |
| FR-024 Search and filtering | FR-010 |

### Key Entities

- **Appointment**: A scheduled visit reservation — distinct from an Encounter, which records the actual care interaction (Master Plan §7.1). Key attributes: patient (FK → Patient, via MRN), provider (FK → StaffProfile, Doctor role), department (derived from the provider's department, Spec 003), date/time start (required), duration (see Open Question OQ-001), visit type (FK → VisitType, Spec 003), status (Scheduled / Arrived / Completed / Cancelled / No-show), reason for visit (optional free text), cancellation reason (required when Cancelled), arrival timestamp, created-by, created-at.
- **AuditEvent**: Who did what, when, to which appointment, and whether it succeeded (shared `audit` app, Spec 002).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Receptionist can create an appointment for a registered patient and see it in the provider's daily schedule in a single flow.
- **SC-002**: 100% of overlapping booking attempts for the same provider (and the same patient) in test data are refused, including concurrent attempts; zero double-bookings are created.
- **SC-003**: Every status change attempted outside the allowed transition table is refused in automated tests.
- **SC-004**: A Receptionist can check a patient in, reschedule, and cancel (with a reason) through the defined transitions, each with a corresponding audit event.
- **SC-005**: A Doctor viewing the schedule sees their own appointments; a Lab Technician / Pharmacist / Billing user attempting any appointment operation is denied by the backend in automated permission tests.
- **SC-006**: No appointment in test data is hard-deleted; every cancelled appointment retains its record, status, and reason.
- **SC-007**: All P0 acceptance scenarios above pass against the implemented feature before it is considered complete.

## Permissions (decided — see D-08)

| Role | Create appointment | Reschedule | Cancel | Check-in (Arrived) | Mark Completed / No-show | View daily schedule |
|---|---|---|---|---|---|---|
| Admin | Yes | Yes | Yes | Yes | Yes | Yes (all) |
| Receptionist | Yes | Yes | Yes | Yes | Yes | Yes (all) |
| Doctor | No in v1 (see OQ-002) | No | No | No | Yes (own appointments only) | Yes (own only) |
| Nurse | No | No | No | No | No | Yes (own department, read-only) |
| Lab Technician | No | No | No | No | No | No in v1 |
| Pharmacist | No | No | No | No | No | No in v1 |
| Billing | No | No | No | No | No | No in v1 |

Patient information shown in the schedule follows Spec 001: Receptionist,
Admin, and Doctor may search/view patients; Nurse / Lab / Pharmacist /
Billing have no patient-search access in v1. A Nurse sees the department
schedule (who is expected, and status) because that is the context for
assigned nursing duties — without patient search or patient detail beyond
name and MRN. Lab / Pharmacist / Billing have no appointment access in v1:
the Master Plan gives them no appointment workflow, and granting access
without a workflow reason would violate least privilege (Constitution
Principle III). Their own feature specs will grant the access their
workflows need, when those features are specified.

## Data fields (decided — see D-01, D-02, D-03)

Required: patient (existing record, via MRN `MC-YYYY-NNNNNN`), provider
(Doctor-role staff profile, Spec 003), date/time start, visit type (Spec
003). Optional: reason for visit (free text), duration (until OQ-001 is
decided, the field exists and is entered per appointment). System fields:
status (Scheduled / Arrived / Completed / Cancelled / No-show), department
(derived from the provider), cancellation reason (required when status is
Cancelled), arrival timestamp, created-by, created-at, updated-at.

All dates/times are stored in UTC and displayed in Asia/Karachi (ADR-001).
Patient CNIC / B-Form is never shown in appointment views (Spec 001
privacy rules): the schedule shows name and MRN only.

## Assumptions

- The hospital is a single organisation; one deployment instance (Master Plan §2.4).
- Authentication and RBAC (Spec 002), patient registration (Spec 001), and hospital setup (Spec 003) exist before or alongside this feature; appointment endpoints assume a signed-in user with a role, registered patients, and active providers/visit types. If any of those is not yet built, this feature cannot be demonstrated end-to-end.
- All demo/test data is synthetic; no real patient records are used.
- Display timezone for dates/times is Asia/Karachi; timestamps are stored in UTC (ADR-001).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner (2026-11-22); implementation may proceed on that basis.
- A walk-in patient is registered first (Spec 001) and then given a same-day appointment here; there is no appointment for an unregistered person (D-06).

## Decisions

Decisions below follow the Master Plan and the already-approved Spec 001,
or are minimal choices with stated rationale. Anything not listed here is
an Open Question.

1. **D-01 — Statuses are Scheduled / Arrived / Completed / Cancelled / No-show, with the transition table above.** Source: Master Plan §6 M04. Rationale: these are the states the Master Plan names for appointments; the table makes "terminal" explicit so no workflow can revive a closed appointment.
2. **D-02 — "Arrived" is the check-in state.** Source: Master Plan §6 M04 ("no-show, arrived, checked-in and completed states") and §7 WF-02 step 1 ("records arrival/check-in"). Rationale: the Master Plan uses "arrived" and "checked-in" for the same step; one status avoids a meaningless two-step check-in.
3. **D-03 — Conflict rule: no overlapping appointment for the same provider, and none for the same patient.** Source: Master Plan §6 M04 ("prevent conflicting bookings according to approved scheduling rules") and FR-009; the provider half is the rule the Master Plan states. Rationale: the patient half is the same rule applied to the other party — a patient cannot be in two places at once, and allowing it would create contradictory schedules. Overlap is judged on the appointment interval (start + duration).
4. **D-04 — No hard deletion of appointments; cancellation is the end state.** Source: Master Plan FR-022, §9.1. Rationale: a deleted appointment destroys the record of a booked visit; cancellation with a reason preserves history and frees the slot.
5. **D-05 — Cancellation requires a recorded reason.** Rationale: consistent with the correction/status-history pattern in Spec 001 (D-05) and Spec 003 — a status change without a reason is not reviewable.
6. **D-06 — An appointment requires a registered patient.** Source: Master Plan §7 WF-01 steps 2–4 (search, register if no match, then create the appointment). Rationale: the appointment links to patient identity; booking an unregistered person would recreate the duplicate-identity problem Spec 001 exists to prevent.
7. **D-07 — An appointment marked Completed does not mean clinical documentation is complete.** Source: Master Plan §7 WF-02 ("a completed appointment does not itself mean clinical documentation is complete") and §7.1 (appointment vs. encounter are distinct records). Rationale: the encounter feature owns clinical completeness; this feature only closes the scheduling state.
8. **D-08 — Front desk owns booking: Receptionist and Admin create, reschedule, cancel, and check in; Doctors act only on their own appointments.** Source: Master Plan §5 (Reception manages appointments; Doctor reviews assigned patients). Rationale: booking is a front-desk job; a Doctor's appointment actions are limited to their own schedule so one clinician cannot alter another's day.

## Open Questions

Genuinely undecided — do not guess; each needs an owner decision before
the implementation that depends on it.

- **OQ-001 — Appointment duration: what is the default length, and do visit types define it?** Undecided. The conflict rule needs an interval (start + duration) to judge overlap, so a duration must exist per appointment — whether it is a fixed default (e.g. 30 minutes), entered per appointment, or defined on the visit type (Spec 003) is undecided.
- **OQ-002 — May Doctors create follow-up appointments?** Undecided. In v1 only Receptionist/Admin create appointments; a clinician booking a follow-up during a consultation is a plausible workflow the Master Plan does not settle.
- **OQ-003 — Check-in window: how early before (and how late after) the appointment time may a patient check in?** Undecided. Affects whether early arrivals can be checked in and when a late arrival is refused or treated as a no-show.
- **OQ-004 — No-show: who marks it, and when — manually at the end of the day, or automatically once the appointment time has passed?** Undecided. The spec provides manual marking by Receptionist/Admin; any automatic transition is not decided.
- **OQ-005 — Department-only appointments: may an appointment be booked against a department with no named provider?** Undecided. Master Plan M04 says "provider/department", which does not settle whether a provider is always required.
- **OQ-006 — Scheduling granularity: free start-time entry, or fixed slots (e.g. every 15/30 minutes)?** Undecided. Affects the booking UI and the conflict check's edge behaviour.
- **OQ-007 — Patient merge: when two patient records are merged (Spec 001, Admin-only), what happens to the losing record's appointments?** Undecided. The appointments must end up on the surviving record, but the exact handling (re-point, cancel, or block the merge while appointments exist) is not decided here or in Spec 001.

## Deferred (not decided here)

- **Encounter / clinical documentation**: separate feature (Master Plan M05); its spec will define how an encounter links to an appointment, including walk-in encounters without a prior appointment.
- **Reminders and notifications**: Master Plan M13, future module.
- **Recurring appointments, waiting lists, provider availability / leave calendars**: not in M04; deferred until a real requirement exists (OQ-005/OQ-006 touch the edges of this).
- **Billing for appointments**: Master Plan M09, P1 candidate — decided when billing is specified.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1; §§19–23 (deployment, risk register, governance/decision log, acceptance, open decisions) are listed in the contents but absent from the document. Explicitly deferred: they must be supplied or formally deferred before release planning (Phase 8), but they do not block this feature.
