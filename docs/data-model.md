# MediCore Data Model

**Status**: Draft for approval (Master Plan deliverable D-05).
**Date**: 2026-11-22
**Sources**: Master Plan v1.0 §11; Constitution Principle IV; Spec 001
(patient data model, decisions D-01–D-13); ADR-001.

This is the complete data model for the MVP scope (P0 modules plus the P1
candidates, marked as such). Entities belonging to P1-candidate modules are
defined here so their relationships are fixed early, but they are **not**
committed scope until their feature specs are approved (Master Plan §4.4).
Patient fields match Spec 001 exactly.

## 1. Conventions

- **Primary keys**: UUID (`id`) for every entity — stable internal key, never
  the human-facing identifier. Human identifiers (MRN, invoice number) are
  separate unique fields.
- **Timestamps**: stored in UTC (`created_at`, `updated_at`); displayed in
  Asia/Karachi. `date_of_birth` and similar calendar dates are `Date`
  (no time component).
- **Money**: `Decimal` with fixed precision (see §3, Invoice/InvoiceLine/
  Payment). Never floating-point for money.
- **Enums**: explicit status/type enumerations, never free-form status
  strings (Master Plan §9.1).
- **No hard delete**: patient, clinical, and financial records are never
  hard-deleted. Retirement is by status change (with a recorded reason) or
  by an audited correction/void. Reference data (departments, services) in
  use by historical transactions cannot be deleted — deactivate instead.
- **Audit fields**: every business entity carries `created_by` (FK → User)
  and `created_at` / `updated_at` unless noted. Correction/status history
  lives in dedicated history rows, never by overwriting silently.
- **Validation**: enforced on the backend (Constitution IV). Frontend
  validation is usability only.
- **Synthetic data only** in development, tests, and demos (Constitution III).

## 2. ERD (text form)

```text
User 1───* StaffProfile *───1 Department
  |                |                    |
  |                |                    *───* Appointment (via provider/department)
  |                |                    *───* Encounter (via clinician/department)
  |                *─── AuditEvent (actor)
  |
  *───* Patient (created_by)
  *───* Appointment (created_by)      *───* Encounter (created_by / clinician)
  *───* Prescription (prescriber)     *───* LabRequest (requester)
  *───* LabResult (author)            *───* Invoice (created_by)
  *───* Payment (recorded_by)         *───* AuditEvent (actor)

Patient 1───* Appointment
Patient 1───* Encounter
Patient 1───* LabRequest
Patient 1───* Invoice
Patient 1───* DuplicateCandidate (as candidate)
Patient 1───* PatientCorrection
Patient 1───* AuditEvent (as target)

Appointment 1───0..1 Encounter        (an encounter may also be a walk-in: no appointment)
Encounter 1───* Diagnosis
Encounter 1───* Prescription  [P1]
Encounter 1───* LabRequest    [P1]
Encounter 1───* Invoice       [P1]

LabRequest 1───* LabResult    [P1]

Invoice 1───* InvoiceLine     [P1]
Invoice 1───* Payment         [P1]

Department 1───* StaffProfile
Department 1───* Appointment (department)
```

Cardinality notes (Master Plan §11.2): one patient has many appointments and
encounters; an appointment may lead to an encounter, but a walk-in encounter
may exist without one; one encounter may have many diagnoses, prescriptions,
and lab requests; one lab request may have one or more results; one invoice
has many lines and may receive many payments; a user may hold one or more
roles only if the approved access model permits it (see OQ-3).

## 3. Data dictionary

Field types are given as Django/PostgreSQL types. "Req." = required at
creation unless noted. Lengths are maxima; exact lengths are an
implementation detail unless stated.

### 3.1 User (`accounts`)

Staff login identity. Distinct from Patient (Master Plan §7.1).

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| username | varchar(150), unique, indexed | Yes | Login name; unique |
| email | varchar(254), unique | Yes | Used for account contact / optional password reset |
| password | varchar (hashed) | Yes | Django framework hashing; never plaintext, never exposed |
| first_name | varchar(150) | Yes | |
| last_name | varchar(150) | Yes | |
| is_active | boolean | — | Default true; disabling revokes access (WF-05) |
| is_staff / is_superuser | boolean | — | Django admin flags; superuser only for system administration, not routine work |
| roles | M2M → Role | Yes | At least one role; see §3.2 |
| last_login | datetime (UTC), nullable | — | |
| created_at / updated_at | datetime (UTC) | — | |

Constraints: `username` unique; `email` unique. No role is granted by
default; a user with no role can sign in but can do nothing protected.

### 3.2 Role and Permission (`accounts`)

Named roles mapped to explicit permissions (Master Plan §5.1).

| Field | Type | Req. | Notes |
|---|---|---|---|
| Role.id | UUID PK | — | |
| Role.name | varchar(100), unique | Yes | e.g. `Admin`, `Receptionist`, `Doctor`, `Nurse`, `Lab Technician`, `Pharmacist`, `Billing`, `Department Manager`, `Auditor` |
| Role.description | text, optional | No | |
| Role.permissions | M2M → Permission | Yes | Explicit permission codes, e.g. `patients.add_patient` |
| Role.is_active | boolean | — | Default true; deactivating a role removes its access |
| Permission.code | varchar(100), unique | Yes | e.g. `patients.view_patient`, `billing.add_payment` |
| Permission.description | text | Yes | |

Roles in v1 are the Master Plan §5 starting set. Whether a user may hold
more than one role is OQ-3. Permission checks use permission codes, not
role-name string checks scattered through the code.

### 3.3 StaffProfile (`organization`)

Work identity and organisational details for a staff member.

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| user | FK → User, unique (OneToOne) | Yes | The login identity; a staff profile belongs to one user |
| staff_code | varchar(50), unique, indexed | Yes | Human staff identifier (format: see OQ-5) |
| department | FK → Department, nullable | No | Null until assigned; required for clinical staff in practice (see OQ-4) |
| job_title | varchar(150) | Yes | e.g. "Medical Officer", "Lab Technologist" |
| blood_group | enum, nullable | No | Optional, A+ to O- (Spec 001 D-13: same optional field as patients) |
| phone | varchar(20), nullable | No | 9–15 digits, optional leading `+` |
| status | enum: Active / Inactive | — | Default Active; Inactive instead of delete |
| created_by | FK → User | Yes | |
| created_at / updated_at | datetime (UTC) | — | |

Constraints: `user` one-to-one; `staff_code` unique. A StaffProfile is not a
Patient and never links to patient records as a patient.

### 3.4 Department (`organization`)

Hospital organisational unit.

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| name | varchar(200), unique | Yes | e.g. "Outpatient", "Laboratory", "Radiology" |
| code | varchar(20), unique, indexed | Yes | Short code, e.g. `OPD`, `LAB` |
| description | text, optional | No | |
| is_active | boolean | — | Default true; a department in use by historical records cannot be deleted — deactivate instead |
| created_by | FK → User | Yes | |
| created_at / updated_at | datetime (UTC) | — | |

Constraints: `name` unique; `code` unique. Deleting a department that has
staff, appointments, or encounters is forbidden (Master Plan M02).

### 3.5 Patient (`patients`) — matches Spec 001 exactly

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | Stable internal key; never exposed as the patient identifier |
| mrn | varchar(20), unique, indexed | System | Auto-generated server-side only; format `MC-YYYY-NNNNNN`; 6-digit sequence resets to `000001` each 1 January (Spec 001 D-01). Staff never type it. |
| full_name | varchar(255) | Yes | As given; preserve original spelling |
| date_of_birth | date | Yes | Validation: not in the future |
| sex | enum: Male / Female / Other | Yes | Required (Spec 001 D-11). Field name `sex` in the model; API exposes `sex` (see api-contract.md). No "Prefer not to say" option. |
| phone | varchar(20) | Yes | 9–15 digits, optional leading `+`; regex `^\+?[0-9]{9,15}$` |
| blood_group | enum: A+ / A- / B+ / B- / AB+ / AB- / O+ / O-, nullable | No | Optional (Spec 001 D-13) |
| address | text, nullable | No | Optional |
| emergency_contact_name | varchar(255), nullable | No | Optional |
| emergency_contact_phone | varchar(20), nullable | No | Optional; same phone format when given |
| national_id | text (encrypted at rest) | Yes | CNIC for adults, B-Form for children; exactly 13 digits (`xxxxx-xxxxxxx-x`, dashes optional on input, digits only stored). Encrypted at rest; full view only Receptionist/Admin; masked (last 4 digits) for all other roles; never in logs, list views, or URLs; never searchable (D-06/D-07/D-12). |
| national_id_hash | varchar(128), unique, indexed | System | Deterministic HMAC-SHA256 of the 13 digits with a server-side secret from the environment (never a per-record salt, never committed). Uniqueness and the CNIC duplicate check are enforced on this hash, since the encrypted value cannot be queried. Never exposed via the API. |
| status | enum: Active / Inactive / Merged / Archived | — | Default Active (D-05). No Deceased status in v1. Status changes recorded with a reason; never hard-deleted. |
| merged_into | FK → Patient (self), nullable | — | Set only by an Admin merge: points at the surviving record. Null otherwise. |
| status_reason | text, nullable | — | Reason for the latest status change |
| created_by | FK → User | Yes | Who registered the patient |
| created_at / updated_at | datetime (UTC) | — | Displayed in Asia/Karachi |

Constraints: `mrn` unique (DB); `national_id_hash` unique (DB — this is what
enforces CNIC/B-Form uniqueness); `date_of_birth <= today` (backend);
`phone` regex (backend); `national_id` 13 digits after stripping dashes
(backend); `sex` in {Male, Female, Other}; `blood_group` in the eight values
when given. Duplicate rule (D-03/D-12): exact full name + date of birth
blocks pending a recorded human decision; exact `national_id_hash` match
blocks the same way; exact phone match alone is a non-blocking warning. No
fuzzy matching in v1.

Indexes: `mrn` (unique); `national_id_hash` (unique); `(full_name,
date_of_birth)` (duplicate search); `phone` (search + secondary duplicate
signal); `status`; `created_at`. **No index on the encrypted `national_id`
itself** — it is encrypted at rest and not searchable by design.

### 3.6 DuplicateCandidate (`patients`)

A flagged possible match between a new registration and an existing patient.
Never an automatic merge.

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| candidate_patient | FK → Patient | Yes | The existing record it may duplicate |
| new_registration_data | JSON, nullable | — | Submitted fields that triggered the warning, stored for review, not as a patient. Must not contain the full national_id in plaintext — store the hash/masked form only (see OQ-6). |
| matched_on | varchar(100) | Yes | Which fields matched: `name_dob`, `national_id`, or `phone` (weak signal) |
| is_blocking | boolean | — | True for name+DOB and national_id matches; false for phone-only |
| decision | enum: Pending / Different person / Same person | — | Default Pending |
| decided_by | FK → User, nullable | — | Null until decided |
| decided_at | datetime (UTC), nullable | — | Null until decided |
| reason | text, nullable | — | Required when deciding (mandatory written reason) |
| created_by | FK → User | Yes | The registering Receptionist |
| created_at / updated_at | datetime (UTC) | — | |

Rules: "Different person" (with reason) allows registration to proceed;
"Same person" blocks creation and links to the existing patient. Merging two
records is a separate Admin-only action (losing record → status Merged).

### 3.7 PatientCorrection (`patients`)

One row per demographic change; append-only history.

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| patient | FK → Patient | Yes | |
| field | varchar(100) | Yes | Which demographic field changed, e.g. `phone` |
| old_value | text, nullable | — | Previous value (may be empty). For national_id, store masked form only — never the full value (see OQ-6). |
| new_value | text, nullable | — | New value (same masking rule for national_id) |
| author | FK → User | Yes | |
| created_at | datetime (UTC) | — | |

Rule: the current value lives on Patient; history lives here, never
overwritten.

### 3.8 Appointment (`appointments`) — P0, spec not yet written

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| patient | FK → Patient | Yes | |
| provider | FK → User (Doctor), nullable | No | The clinician; null if booked by department only (see OQ-1) |
| department | FK → Department | Yes | |
| visit_type | varchar(100) | Yes | From the approved reference list (organization app) — exact values decided by the appointments spec |
| scheduled_start | datetime (UTC) | Yes | Displayed in Asia/Karachi |
| scheduled_end | datetime (UTC), nullable | No | Optional; used by conflict rules if the spec adopts them |
| status | enum: Scheduled / Arrived / Checked-in / In-progress / Completed / Cancelled / No-show | — | Default Scheduled. Exact state set confirmed by the appointments spec; Master Plan M04 lists no-show, arrived, checked-in, completed. |
| status_reason | text, nullable | — | Reason for cancellation / no-show |
| notes | text, optional | No | Front-desk notes only — no clinical content |
| created_by | FK → User | Yes | |
| created_at / updated_at | datetime (UTC) | — | |

Constraints: required fields + conflict rules validated by the appointments
spec (see architecture.md OQ-3). An appointment is a reservation, not a
care record — it never contains clinical notes.

Indexes: `(provider, scheduled_start)`; `(department, scheduled_start)`;
`(patient, scheduled_start)`; `status`.

### 3.9 Encounter (`encounters`) — P0, spec not yet written

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| patient | FK → Patient | Yes | |
| appointment | FK → Appointment, nullable | — | Null for an approved walk-in encounter |
| clinician | FK → User (Doctor) | Yes | Responsible clinician |
| department | FK → Department | Yes | |
| encounter_date | datetime (UTC) | Yes | When the visit happened; displayed in Asia/Karachi |
| reason_for_visit | text | Yes | |
| notes | text, optional | No | Structured clinical notes; never copied into logs or audit metadata |
| status | enum: Draft / Finalised | — | Default Draft. Finalised encounters are not silently edited — corrections are traceable (see OQ-2). |
| created_by | FK → User | Yes | |
| created_at / updated_at | datetime (UTC) | — | |

Rules: authorship and timestamps preserved; a finalised encounter's
corrections must be traceable. Clinical content stays out of general-purpose
logs and unnecessary reports (Master Plan M05).

Indexes: `(patient, encounter_date)`; `(clinician, encounter_date)`; `status`.

### 3.10 Diagnosis (`encounters`) — P0, spec not yet written

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| encounter | FK → Encounter | Yes | |
| code | varchar(50), nullable | No | Diagnosis code if a coding scheme is adopted (see OQ-7 in architecture.md); null if free text only |
| description | text | Yes | Clinician's assessment, free text |
| author | FK → User | Yes | |
| created_at | datetime (UTC) | — | |

One encounter may have many diagnoses. A diagnosis records an assessment;
it does not imply a prescription (Master Plan §7.1).

### 3.11 Prescription (`prescriptions`) — M7

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| encounter | FK → Encounter | Yes | |
| prescriber | FK → User (Doctor) | Yes | |
| medication_name | varchar(255) | Yes | |
| strength | varchar(100), nullable | No | e.g. "500 mg" |
| dosage | varchar(100) | Yes | Structured where possible; avoid ambiguous free-text-only prescriptions |
| route | varchar(50), nullable | No | e.g. Oral, IV — value list decided by the prescriptions spec |
| frequency | varchar(100) | Yes | e.g. "twice daily" |
| duration | varchar(100), nullable | No | e.g. "7 days" |
| instructions | text, optional | No | |
| status | enum: Draft / Finalised / Cancelled | — | Default Draft |
| created_by | FK → User | Yes | |
| created_at / updated_at | datetime (UTC) | — | |

Rules: no treatment recommendations or automated dosing decisions (Master
Plan M06). No pharmacy dispensing/stock logic — that is M12, out of scope.

### 3.12 LabRequest (`laboratory`) — M6

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| patient | FK → Patient | Yes | Denormalised link for the lab queue; must always agree with the encounter's patient |
| encounter | FK → Encounter, nullable | — | Null only if a request without an encounter is approved by the lab spec |
| requester | FK → User (Doctor) | Yes | |
| test_name | varchar(255) | Yes | From the test catalogue if one is approved (see OQ-8); free text until then |
| specimen_details | text, optional | No | |
| priority | enum: Routine / Urgent, nullable | No | Default Routine if the spec adopts it |
| status | enum: Requested / Collected / Received / In-progress / Completed / Cancelled | — | Default Requested |
| created_by | FK → User | Yes | |
| created_at / updated_at | datetime (UTC) | — | |

### 3.13 LabResult (`laboratory`) — M6

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| lab_request | FK → LabRequest | Yes | |
| result_value | varchar(255) | Yes | Value as recorded; numeric vs text decided by the lab spec |
| unit | varchar(50), nullable | No | e.g. "mg/dL" |
| reference_range | varchar(255), nullable | No | Reference information where defined |
| status | enum: Draft / Finalised / Approved | — | Default Draft; approval step only if the lab spec requires it |
| author | FK → User | Yes | Who entered the result |
| approved_by | FK → User, nullable | — | Null until/unless approved |
| created_at / updated_at | datetime (UTC) | — | |

Rules: result entry and result approval are separate duties where the
approved workflow requires it; unauthorised users cannot alter results.
Corrections to a finalised result are traceable, not silent overwrites.

### 3.14 Invoice (`billing`) — M8

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| invoice_number | varchar(50), unique, indexed | System | Human identifier; format decided by the billing spec (see OQ-9) |
| patient | FK → Patient | Yes | |
| encounter | FK → Encounter, nullable | — | Link where the charges arise from a visit |
| currency | varchar(3) | — | Fixed value for v1 (see OQ-10); stored explicitly per Master Plan §11.1 |
| subtotal | decimal(12,2) | System | Sum of line amounts; computed, never hand-entered |
| discount_total | decimal(12,2) | — | Default 0.00; discounts/taxes only if defined by the billing spec |
| tax_total | decimal(12,2) | — | Default 0.00; only if defined |
| total | decimal(12,2) | System | subtotal − discount + tax; Decimal arithmetic only |
| amount_paid | decimal(12,2) | System | Sum of payments; computed, never hand-entered |
| balance | decimal(12,2) | System | total − amount_paid; computed |
| status | enum: Unpaid / Partially paid / Paid / Voided / Refunded | — | Default Unpaid; derived from balance except Voided/Refunded, which are explicit audited states |
| issued_at | datetime (UTC), nullable | — | When the invoice was issued |
| created_by | FK → User | Yes | |
| created_at / updated_at | datetime (UTC) | — | |

Constraints: totals are computed from lines/payments in a transaction;
`total >= 0`; `amount_paid <= total` (overpayment prevented, Master Plan
M09). Void/refund follows an approved, audited process — never a delete.

### 3.15 InvoiceLine (`billing`) — M8

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| invoice | FK → Invoice | Yes | |
| service | FK → Service (organization catalogue), nullable | — | Null only if ad-hoc charges are approved by the billing spec |
| description | varchar(255) | Yes | Line description as printed |
| quantity | decimal(10,2) | Yes | Default 1; Decimal, not float |
| unit_price | decimal(12,2) | Yes | Decimal |
| line_total | decimal(12,2) | System | quantity × unit_price; computed |
| created_at | datetime (UTC) | — | |

### 3.16 Payment (`billing`) — M8

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| invoice | FK → Invoice | Yes | |
| amount | decimal(12,2) | Yes | Must be > 0 and must not overpay the invoice |
| method | enum: Cash / Card / Bank transfer / Other | Yes | Exact method list decided by the billing spec (no real payment settlement in v1 — recording only) |
| receipt_reference | varchar(100), nullable | No | Receipt / payment reference |
| paid_at | datetime (UTC) | Yes | When the payment was recorded |
| recorded_by | FK → User | Yes | Cashier / billing staff |
| status | enum: Recorded / Voided / Refunded | — | Default Recorded; void/refund is audited, never a delete |
| created_at | datetime (UTC) | — | |

Invoice and payment are separate records (Master Plan §7.1). Offline
payment recording only — online collection is Spec 010 (M9) below.

### 3.16b OnlinePayment (`payments`) — M9 (Spec 010)

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| gateway_reference | varchar(100), unique, indexed | System | System-generated; format decided with the gateway (Spec 010 OQ-010-1) |
| invoice | FK → Invoice | Yes | Must be Unpaid / Partially paid at initiation |
| amount | decimal(12,2) | Yes | Positive; must not exceed the outstanding balance at initiation |
| currency | varchar(10) | Yes | PKR — working assumption (Spec 010 OQ-010-9) |
| gateway | varchar(50) | Yes | Name of the chosen gateway (Spec 010 OQ-010-1) |
| status | enum: Initiated / Paid / Failed / Refunded / Expired | — | Default Initiated; transitions enforced |
| gateway_event_id | varchar(100), unique, nullable | — | Idempotency key for callbacks; a duplicate event is ignored |
| failure_reason | text, nullable | — | Recorded when Failed; never card data |
| initiated_by | FK → User | Yes | Billing / Admin |
| initiated_at | datetime (UTC) | — | |
| paid_at | datetime (UTC), nullable | — | Set from the gateway's paid timestamp when Paid |
| created_at | datetime (UTC) | — | |

A verified success callback creates a Spec 008 Payment record (method
Online) and updates the invoice balance/state in one transaction. No
card data is ever stored. No real money moves outside sandbox/test mode
in development or demonstration.

### 3.17 AuditEvent (`audit`) — shared

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| actor | FK → User, nullable | — | Null only for unauthenticated attempts (e.g. failed sign-in) |
| action | varchar(100), indexed | Yes | e.g. `patient.create`, `patient.correct`, `patient.status_change`, `duplicate.review`, `auth.login_failed`, `invoice.void`, `payment.record` |
| target_type | varchar(100) | Yes | e.g. `Patient`, `Invoice` |
| target_id | UUID, nullable | — | The target record's id |
| timestamp | datetime (UTC), indexed | — | |
| outcome | enum: Success / Failure | — | |
| metadata | JSON, nullable | — | Limited, non-sensitive context only. Never passwords, tokens, full clinical content, or full national_id. |

Rule: append-only. No update/delete API for audit events. Audit records refer
to actors and targets without copying sensitive content into the log.

### 3.18 Service — chargeable service catalogue (`organization`, P1 support)

Reference data for billing line items (Master Plan M02 "service catalog
basics"). Defined here because InvoiceLine references it; its management UI
and exact fields are decided by the organization/billing specs.

| Field | Type | Req. | Notes |
|---|---|---|---|
| id | UUID PK | — | |
| name | varchar(255) | Yes | e.g. "General consultation" |
| code | varchar(50), unique | Yes | |
| category | varchar(100), nullable | No | Service category from the approved reference list |
| default_price | decimal(12,2) | Yes | Decimal |
| is_active | boolean | — | Default true; a service used by historical invoices cannot be deleted |
| created_by | FK → User | Yes | |
| created_at / updated_at | datetime (UTC) | — | |

## 4. Status state machines (summary)

| Entity | States | Allowed transitions (enforced in services) |
|---|---|---|
| Patient | Active / Inactive / Merged / Archived | Active → Inactive / Archived (reason recorded); any → Merged only by Admin merge; Merged is terminal. No transition deletes the record. |
| Appointment | Scheduled / Arrived / Checked-in / In-progress / Completed / Cancelled / No-show | Forward flow Scheduled → Arrived → Checked-in → In-progress → Completed; Cancelled / No-show from Scheduled (or Arrived, per appointments spec). Exact set confirmed by that spec. |
| Encounter | Draft / Finalised | Draft → Finalised. Finalised → correction only via a traceable correction path (OQ-2). |
| Prescription [P1] | Draft / Finalised / Cancelled | Draft → Finalised / Cancelled. Finalised → Cancelled (audited). |
| LabRequest [P1] | Requested / Collected / Received / In-progress / Completed / Cancelled | Forward through the chain; Cancelled from any pre-Completed state. |
| LabResult [P1] | Draft / Finalised / Approved | Draft → Finalised → Approved (approval step only if the lab spec requires it). |
| Invoice [P1] | Unpaid / Partially paid / Paid / Voided / Refunded | Unpaid → Partially paid → Paid as payments arrive; → Voided / Refunded only via the approved audited process. |
| Payment [P1] | Recorded / Voided / Refunded | Recorded → Voided / Refunded (audited). |

## 5. Indexes (summary)

- User: `username` (unique), `email` (unique).
- Patient: `mrn` (unique), `national_id_hash` (unique), `(full_name,
  date_of_birth)`, `phone`, `status`, `created_at`. No index on encrypted
  `national_id`.
- Appointment: `(provider, scheduled_start)`, `(department,
  scheduled_start)`, `(patient, scheduled_start)`, `status`.
- Encounter: `(patient, encounter_date)`, `(clinician, encounter_date)`,
  `status`.
- LabRequest: `(patient, created_at)`, `status`; LabResult:
  `(lab_request, created_at)`.
- Invoice: `invoice_number` (unique), `(patient, created_at)`, `status`;
  Payment: `(invoice, paid_at)`.
- AuditEvent: `(target_type, target_id)`, `action`, `timestamp`,
  `(actor, timestamp)`.
- Add further indexes only after observing real query patterns (Master Plan
  §11.1).

## 6. Migrations and evolution

- Migrations are version-controlled and reproducible (Constitution IV); they
  must apply cleanly from a fresh setup (Master Plan §16.3).
- Schema changes go through a new migration — never by editing an applied
  migration or by hand-editing the database.
- New entities/fields for P1 modules are added by their own feature specs;
  this document fixes the intended shape so those specs do not have to
  re-decide relationships.
- The parked scaffold code (if any) does not define this model; the model
  here is authoritative until a spec amends it.

## Open Questions

- **OQ-1 — Appointment provider optional?** Must every appointment name a
  provider, or can it be booked against a department only (provider
  assigned later)? The appointments spec must decide; the model allows null
  until then.
- **OQ-2 — Finalised-encounter corrections.** What is the correction path
  for a finalised encounter (amendment record? new version? Admin-only
  reopen)? Not decided; the encounters spec must define it. The model
  assumes corrections are traceable and never silent overwrites.
- **OQ-3 — Multiple roles per user.** Master Plan §11.2 allows a user one
  or more roles "only if the approved access model permits it". Not decided
  whether v1 permits multiple roles per user or exactly one.
- **OQ-4 — Department required for staff?** Whether `StaffProfile.
  department` is required (and for which job titles) is not decided.
- **OQ-5 — Staff code format.** No format is decided for `staff_code`
  (unlike MRN, which is fully specified). The organization spec must define
  it.
- **OQ-6 — National ID in history payloads.** `DuplicateCandidate.
  new_registration_data` and `PatientCorrection.old_value/new_value` must
  never store the full national_id in plaintext. Whether they store the
  masked form, the hash, or omit the field entirely is not decided — the
  patients implementation must pick one and record it; masked form is the
  working assumption.
- **OQ-7 — Lab test catalogue.** Whether lab tests come from a managed
  catalogue entity or free text is not decided; the laboratory spec must
  decide. The model uses `test_name` text until then.
- **OQ-8 — Visit-type / service-category value lists.** The approved
  reference lists for `visit_type`, service categories, and payment methods
  are not decided; the organization spec (with appointments/billing input)
  must define them.
- **OQ-9 — Invoice number format.** No format is decided (unlike MRN).
  The billing spec must define it (e.g. yearly sequence like MRN, or a
  plain sequence).
- **OQ-10 — Currency.** The currency for invoices is not decided in any
  source. The working assumption is a single fixed currency for v1
  (hospital is in Pakistan); the billing spec must confirm it and the value.
- **OQ-11 — Patient age / DOB edge cases.** No rule is decided for
  implausibly old dates of birth (e.g. > 120 years) or for recording a
  guardian for child patients beyond the emergency-contact field. The
  patients spec amendment (if needed) must decide.
