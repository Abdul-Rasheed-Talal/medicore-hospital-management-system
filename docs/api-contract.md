# MediCore API Contract

**Status**: Draft for approval (part of Master Plan deliverable D-04).
**Date**: 2026-11-22
**Sources**: Master Plan v1.0 §§8, 14; Constitution Principles III, IV, VII;
Spec 001 (patient endpoints, decisions D-01–D-13); ADR-001; `docs/data-model.md`.

This contract is the single source of truth for the REST API. Implementation
must match it; if implementation needs to differ, this document is amended
first (Constitution VII). Endpoint groups for P1-candidate modules are marked
**[P1]** — they are defined here so clients can be planned, but they are not
committed scope until their feature specs are approved (Master Plan §4.4).

## 1. Conventions

### 1.1 Base, format, auth

- Base path: `/api/` (no version prefix in v1 — see OQ-1).
- All requests/responses are JSON. All timestamps are ISO 8601 UTC
  (e.g. `2026-11-22T10:30:00Z`); clients display them in Asia/Karachi.
  Dates are `YYYY-MM-DD`.
- **Auth**: Django session authentication. The browser sends the session
  cookie (secure, HttpOnly) and a CSRF token on state-changing requests
  (`POST`/`PATCH`/`PUT`/`DELETE`). No JWT, no bearer tokens in v1
  (ADR-001; Spec 001 D-09). Unauthenticated requests to protected endpoints
  return `401`. There is no public/anonymous API.
- **Permissions**: every endpoint lists its required permission. Checks run
  on the backend before data is returned or mutated; deny by default.
  Object-level checks apply on every detail lookup (changing an ID in the
  URL must not leak another role's forbidden record).
- **IDs in URLs**: the UUID `id` of the record, except patient lookup by
  MRN which uses the `?search=` query (see §7). The MRN may appear in a
  path only where this contract says so; the full national_id never appears
  in a URL.

### 1.2 Errors (all endpoints)

```json
{
  "detail": "Human-readable message.",
  "code": "permission_denied",
  "errors": { "phone": ["Phone must be 9-15 digits."] }
}
```

- `detail`: always present, human-readable, no secrets/stack traces/patient
  data beyond what the caller's role may see (Master Plan FR-023).
- `code`: machine-readable string, always present on errors.
- `errors`: field-level errors, present only on validation failures (400).
- Status codes: `200` OK, `201` Created, `204` No Content, `400` validation,
  `401` unauthenticated, `403` forbidden (authenticated but not permitted),
  `404` not found (also used where revealing existence would leak data),
  `409` conflict / duplicate-warning payload (see §7.1), `429` throttled.
  `500` is never returned with a stack trace.

### 1.3 Pagination, filtering, sorting

- List endpoints are paginated (Master Plan FR-024). Response shape:

```json
{
  "count": 128,
  "next": "/api/patients/?page=2",
  "previous": null,
  "results": [ { "..." : "..." } ]
}
```

- Query params: `page` (default 1), `page_size` (default 20, max 100).
  These defaults are adopted by this contract; they are not Master Plan
  decisions.
- Filtering uses only the filters listed per endpoint. Unknown filter params
  are ignored (never an error, never a data leak).
- Sorting uses `?ordering=<field>` with only the whitelisted fields per
  endpoint; default sort is stated per endpoint. No unbounded lists are ever
  returned.
- Search: `?search=` where listed. Patient name search requires a minimum
  of 3 characters (Spec 001 D-06).

### 1.4 Field visibility rules (apply everywhere)

- `national_id`: **never** in list responses; in detail responses only for
  Receptionist/Admin (full value), masked to last 4 digits for all other
  permitted roles. Never searchable. `national_id_hash` is never exposed.
- Passwords, tokens, and hashes are never exposed.
- List responses contain only the fields the caller's role may see; detail
  responses may contain more, per the same rule.

## 2. `/api/auth/` — Authentication (P0, M01)

| Method & path | Permission | Request | Response | Notes |
|---|---|---|---|---|
| `POST /api/auth/login/` | None (public endpoint, throttled) | `{ "username": "...", "password": "..." }` | `200 { "user": { ... } }` + session cookie | Sets the session cookie. Failed attempts return `401` with a generic message (no "user not found" vs "wrong password" distinction). Throttled against brute force. |
| `POST /api/auth/logout/` | Authenticated | — (CSRF required) | `204` | Destroys the server-side session. |
| `GET /api/auth/me/` | Authenticated | — | `200 User object` (see §3) | Current user, roles, and permissions. Used by the frontend to build role-aware navigation. |
| `POST /api/auth/password-change/` | Authenticated | `{ "old_password": "...", "new_password": "..." }` | `200 { "detail": "Password changed." }` | New password must meet Django's validators. |
| `POST /api/auth/password-reset/` | None | `{ "email": "..." }` | `200` (generic) | **Only if email is configured.** Otherwise this endpoint does not exist in the deployment (Master Plan M01: optional, subject to email configuration). Response is generic whether or not the email exists. |

User object shape (`GET /api/auth/me/`, and nested in other responses):

```json
{
  "id": "uuid",
  "username": "a.receptionist",
  "email": "receptionist@hospital.example",
  "first_name": "Ayesha",
  "last_name": "Khan",
  "is_active": true,
  "roles": ["Receptionist"],
  "permissions": ["patients.view_patient", "patients.add_patient"]
}
```

## 3. `/api/users/` — User administration (P0, M01)

Admin only (permission `accounts.manage_users`).

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/users/` | Admin | `?search=&is_active=&role=&page=` | Paginated user list (User object shape, §2). `search` matches username/first/last name. |
| `POST /api/users/` | Admin | `{ username, email, first_name, last_name, password, roles: [...] }` | `201` User object. Password is set server-side, never returned. |
| `GET /api/users/{id}/` | Admin | — | `200` User object + staff profile link where one exists. |
| `PATCH /api/users/{id}/` | Admin | `{ first_name, last_name, email, is_active, roles }` (partial) | `200` User object. Setting `is_active=false` disables the account (revokes access). |
| `POST /api/users/{id}/reset-password/` | Admin | `{ "new_password": "..." }` or `{}` for a generated one | `200 { "detail": "..." }`. The new password is returned **once** in this response if generated, never stored or logged in plaintext. Exact behaviour (admin-set vs generated) is an OQ — see OQ-4. |
| `POST /api/users/{id}/disable/` | Admin | `{ "reason": "..." }` | `200` User object with `is_active=false`. Reason is audited. Prefer this over `PATCH is_active` so the reason is recorded. |

Rules: a user cannot disable themselves; a user cannot grant themselves
privileges; role changes are audited (`auth.role_change`). No user deletion
endpoint — disable instead.

## 4. `/api/roles/` — Roles and permissions (P0, M01)

Admin only.

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/roles/` | Admin | `?page=` | Paginated roles: `{ id, name, description, permissions: [codes], is_active }`. |
| `POST /api/roles/` | Admin | `{ name, description, permissions: [codes] }` | `201` Role object. |
| `GET /api/roles/{id}/` | Admin | — | `200` Role object. |
| `PATCH /api/roles/{id}/` | Admin | `{ name, description, permissions, is_active }` (partial) | `200` Role object. Role/permission changes are audited. |
| `GET /api/roles/permissions/` | Admin | — | `200 [ { "code": "...", "description": "..." } ]` — the full permission catalogue. |

No role deletion endpoint while the role is assigned to any user; deactivate
instead. Whether multiple roles per user are permitted is OQ-3 in
`docs/data-model.md`.

## 5. `/api/departments/` — Departments (P0, M02)

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/departments/` | Authenticated (any role) | `?is_active=&page=` | Paginated: `{ id, name, code, description, is_active }`. |
| `POST /api/departments/` | Admin | `{ name, code, description }` | `201` Department object. |
| `GET /api/departments/{id}/` | Authenticated | — | `200` Department object. |
| `PATCH /api/departments/{id}/` | Admin | `{ name, code, description, is_active }` (partial) | `200` Department object. |
| `DELETE /api/departments/{id}/` | — | — | **Does not exist.** A department in use by historical records cannot be deleted; deactivate with `is_active=false` (Master Plan M02). |

## 6. `/api/staff/` — Staff profiles (P0, M02)

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/staff/` | Admin; Department Manager (own department) | `?department=&status=&search=&page=` | Paginated: `{ id, user, staff_code, department, job_title, blood_group, phone, status }`. `search` matches name/staff_code. |
| `POST /api/staff/` | Admin | `{ user, staff_code, department, job_title, blood_group, phone }` | `201` Staff object. `blood_group` optional, A+ to O- (Spec 001 D-13). |
| `GET /api/staff/{id}/` | Admin; Department Manager (own department); the staff member themselves | — | `200` Staff object. |
| `PATCH /api/staff/{id}/` | Admin | `{ department, job_title, blood_group, phone, status }` (partial) | `200` Staff object. Status change instead of delete. |

`staff_code` format is not decided (data-model.md OQ-5); the contract
requires only that it is unique and non-empty.

## 7. `/api/patients/` — Patients (P0, M03; Spec 001 — binding)

Permissions (Spec 001): Receptionist/Admin — search, register, correct,
view correction/duplicate history, merge (Admin only). Doctor — read-only
search/view of demographics/summary. Nurse / Lab Technician / Pharmacist /
Billing — **no patient-search access in v1**; their specs grant access when
their workflows are specified.

### 7.1 Register — `POST /api/patients/`

- Permission: Receptionist, Admin.
- Request:

```json
{
  "full_name": "Ahmed Raza",
  "date_of_birth": "1990-05-14",
  "sex": "Male",
  "phone": "+923001234567",
  "national_id": "35202-1234567-1",
  "blood_group": "O+",
  "address": "Street 4, Bhakkar",
  "emergency_contact_name": "Sara Raza",
  "emergency_contact_phone": "+923001234568"
}
```

- Required: `full_name`, `date_of_birth`, `sex`, `phone`, `national_id`.
  Optional: `blood_group`, `address`, `emergency_contact_name`,
  `emergency_contact_phone`.
- Validation (backend, authoritative): `date_of_birth` not in the future;
  `phone` matches `^\+?[0-9]{9,15}$`; `sex` in {Male, Female, Other};
  `national_id` exactly 13 digits after stripping dashes; `blood_group` in
  the eight values when given. Failures return `400` with field-level
  `errors`.
- Success: `201` with the Patient object (see §7.4). The MRN is generated
  server-side; a client-supplied MRN is ignored/rejected.
- **Duplicate warning: `409`** with a duplicate-candidate payload (not a
  plain error) when an exact name + date-of-birth match or an exact
  national_id match exists:

```json
{
  "detail": "A possible duplicate patient record exists.",
  "code": "duplicate_candidate",
  "candidates": [
    { "patient_id": "uuid", "mrn": "MC-2026-000123", "full_name": "Ahmed Raza",
      "date_of_birth": "1990-05-14", "matched_on": "name_dob" }
  ],
  "duplicate_review_id": "uuid",
  "blocking": true
}
```

  A phone-only match returns a non-blocking warning instead: the registration
  proceeds with `201` and a `warnings` array containing the phone-match
  candidate. The client then calls `POST .../duplicate-review/` (see §7.5)
  to resolve a blocking warning with a decision + reason; only then may the
  registration be re-submitted/confirmed. No fuzzy matching in v1.

### 7.2 Search/list — `GET /api/patients/`

- Permission: Receptionist, Admin, Doctor (read-only).
- Query: `?search=&status=&page=&page_size=&ordering=`.
  `search` matches MRN (exact), full name (minimum 3 characters), or phone.
  No CNIC/national_id search exists in v1, by design.
- Default ordering: `full_name`, then `mrn`. Allowed `ordering` values:
  `full_name`, `-full_name`, `created_at`, `-created_at`, `mrn`.
- Response: paginated list of Patient summaries — `{ id, mrn, full_name,
  date_of_birth, sex, phone, blood_group, status, created_at }`.
  No national_id, no clinical/financial detail in list views.
- No match: `200` with `count: 0` and empty `results` (the frontend shows
  an explicit "no match found" state with a path to register).

### 7.3 Detail — `GET /api/patients/{id}/`

- Permission: Receptionist, Admin, Doctor (read-only).
- Response: full Patient object (see §7.4) plus, once later features exist,
  an authorised visit history (appointments/encounters — shape defined by
  those specs). In v1 the visit history is an empty list.
- `404` if the patient does not exist or the caller has no access.

### 7.4 Patient object shape

```json
{
  "id": "uuid",
  "mrn": "MC-2026-000123",
  "full_name": "Ahmed Raza",
  "date_of_birth": "1990-05-14",
  "sex": "Male",
  "phone": "+923001234567",
  "blood_group": "O+",
  "address": "Street 4, Bhakkar",
  "emergency_contact_name": "Sara Raza",
  "emergency_contact_phone": "+923001234568",
  "national_id": "35202-1234567-1",
  "national_id_masked": "*********5671",
  "status": "Active",
  "created_by": "uuid",
  "created_at": "2026-11-22T10:30:00Z",
  "updated_at": "2026-11-22T10:30:00Z"
}
```

`national_id` (full) appears only for Receptionist/Admin; all other
permitted roles receive `national_id_masked` only (last 4 digits visible).
`national_id_hash` is never present.

### 7.5 Correct, status, duplicate review, merge, history

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `PATCH /api/patients/{id}/` | Receptionist, Admin | Partial demographics (any of the §7.1 fields except `mrn`; `national_id` change is allowed but re-checks uniqueness and is audited) | `200` Patient object. Each changed field writes a PatientCorrection row (old/new value, author, timestamp). |
| `POST /api/patients/{id}/duplicate-review/` | Receptionist (own warning), Admin | `{ "duplicate_review_id": "uuid", "decision": "different_person" \| "same_person", "reason": "..." }` | `200 { "decision": "...", "patient_id": "uuid or null" }`. `reason` is mandatory. "different_person" allows the registration to proceed; "same_person" blocks creation and returns the existing patient. |
| `GET /api/patients/{id}/corrections/` | Receptionist, Admin; Doctor (read-only, for patients they may view) | `?page=` | Paginated: `{ id, field, old_value, new_value, author, created_at }`. National_id values are masked here. |
| `GET /api/patients/{id}/duplicates/` | Receptionist, Admin | `?page=` | Paginated duplicate-review history for this patient. |
| `POST /api/patients/{id}/merge/` | Admin only | `{ "losing_patient_id": "uuid", "reason": "..." }` | `200 { "kept_mrn": "...", "archived_mrn": "..." }`. The losing record's status becomes Merged (never deleted); kept MRN, archived MRN, reason, and actor are recorded. `reason` mandatory. |
| `POST /api/patients/{id}/status/` | Receptionist, Admin | `{ "status": "Inactive" \| "Archived", "reason": "..." }` | `200` Patient object. `reason` mandatory. Status `Merged` cannot be set here (merge endpoint only). |

No `DELETE /api/patients/{id}/` endpoint exists. Ever.

## 8. `/api/appointments/` — Appointments (P0, M04; spec not yet written)

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/appointments/` | Receptionist, Admin, Doctor (own schedule) | `?patient=&provider=&department=&status=&date_from=&date_to=&page=&ordering=` | Paginated: `{ id, patient, provider, department, visit_type, scheduled_start, scheduled_end, status, notes }`. Default ordering `scheduled_start`. |
| `POST /api/appointments/` | Receptionist, Admin | `{ patient, provider, department, visit_type, scheduled_start, scheduled_end, notes }` | `201` Appointment object. Conflict rules validated server-side (rules defined by the appointments spec). |
| `GET /api/appointments/{id}/` | Receptionist, Admin, Doctor (own) | — | `200` Appointment object. |
| `PATCH /api/appointments/{id}/` | Receptionist, Admin | `{ provider, department, visit_type, scheduled_start, scheduled_end, notes }` (partial; reschedule) | `200` Appointment object. |
| `POST /api/appointments/{id}/status/` | Receptionist, Admin | `{ "status": "Arrived" \| "Checked-in" \| "Completed" \| "Cancelled" \| "No-show", "reason": "..." }` | `200` Appointment object. `reason` mandatory for Cancelled/No-show. Only valid transitions accepted (see data-model.md §4); invalid transitions return `400`. |

No delete endpoint; cancellation is the retirement path.

## 9. `/api/encounters/` — Encounters (P0, M05; spec not yet written)

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/encounters/` | Doctor (own/authorised), Admin | `?patient=&clinician=&department=&status=&date_from=&date_to=&page=` | Paginated: `{ id, patient, appointment, clinician, department, encounter_date, reason_for_visit, status }`. Notes are **not** in list responses. |
| `POST /api/encounters/` | Doctor | `{ patient, appointment, department, encounter_date, reason_for_visit, notes, diagnoses: [...] }` | `201` Encounter object (status Draft). |
| `GET /api/encounters/{id}/` | Doctor (authorised), Admin | — | `200` Encounter object with `notes` and `diagnoses`. |
| `PATCH /api/encounters/{id}/` | Doctor (author, while Draft) | `{ reason_for_visit, notes, diagnoses }` (partial) | `200` Encounter object. Editing a Finalised encounter is rejected (`400`/`403`) until the encounters spec defines the correction path. |
| `POST /api/encounters/{id}/finalize/` | Doctor (author) | — | `200` Encounter object (status Finalised). |
| `GET /api/encounters/{id}/diagnoses/` | Doctor (authorised), Admin | — | `200 [ { id, code, description, author, created_at } ]`. |

Receptionist has no encounter access in v1 (no workflow reason — least
privilege). Billing/Lab access to encounters is granted only as their specs
require.

## 10. `/api/prescriptions/` — Prescriptions **[M7]** (Spec 006, draft)

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/prescriptions/` | Doctor (own/authorised), Admin | `?encounter=&patient=&status=&page=` | Paginated prescription list. |
| `POST /api/prescriptions/` | Doctor | `{ encounter, medication_name, strength, dosage, route, frequency, duration, instructions }` | `201` Prescription object (status Draft). |
| `GET /api/prescriptions/{id}/` | Doctor (authorised), Admin | — | `200` Prescription object. |
| `PATCH /api/prescriptions/{id}/` | Doctor (author, while Draft) | Partial fields | `200` Prescription object. |
| `POST /api/prescriptions/{id}/finalize/` | Doctor (author) | — | `200` Prescription object (Finalised). |
| `POST /api/prescriptions/{id}/cancel/` | Doctor (author), Admin | `{ "reason": "..." }` | `200` Prescription object (Cancelled). |

No dosing recommendations, no automated treatment advice — the API records
what a clinician entered, nothing more.

## 11. `/api/lab-requests/` and `/api/lab-results/` — Laboratory **[M6]** (Spec 007, draft)

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/lab-requests/` | Lab Technician, Doctor (own requests), Admin | `?patient=&encounter=&status=&page=` | Paginated: `{ id, patient, encounter, requester, test_name, specimen_details, priority, status }`. |
| `POST /api/lab-requests/` | Doctor | `{ patient, encounter, test_name, specimen_details, priority }` | `201` LabRequest (status Requested). |
| `GET /api/lab-requests/{id}/` | Lab Technician, Doctor (authorised), Admin | — | `200` LabRequest object. |
| `POST /api/lab-requests/{id}/status/` | Lab Technician, Admin | `{ "status": "Collected" \| "Received" \| "In-progress" \| "Completed" \| "Cancelled", "reason": "..." }` | `200` LabRequest object. Only valid transitions; `reason` mandatory for Cancelled. |
| `GET /api/lab-requests/{id}/results/` | Lab Technician, Doctor (authorised), Admin | — | `200 [ LabResult ]`. |
| `POST /api/lab-requests/{id}/results/` | Lab Technician | `{ result_value, unit, reference_range }` | `201` LabResult (status Draft). |
| `PATCH /api/lab-results/{id}/` | Lab Technician (author, while Draft) | `{ result_value, unit, reference_range }` | `200` LabResult object. |
| `POST /api/lab-results/{id}/finalize/` | Lab Technician (author) | — | `200` LabResult (Finalised). |
| `POST /api/lab-results/{id}/approve/` | Lab Technician (approver — not the author, if the spec requires separation), Admin | — | `200` LabResult (Approved). Only if the lab spec adopts the approval step. |

## 12. `/api/invoices/` and `/api/payments/` — Billing **[M8]** (Spec 008, draft)

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/invoices/` | Billing, Admin | `?patient=&status=&date_from=&date_to=&page=` | Paginated: `{ id, invoice_number, patient, encounter, currency, subtotal, discount_total, tax_total, total, amount_paid, balance, status, issued_at }`. All money fields are decimal strings (e.g. `"1500.00"`), never floats. |
| `POST /api/invoices/` | Billing, Admin | `{ patient, encounter, lines: [{ service, description, quantity, unit_price }], discount_total, tax_total }` | `201` Invoice object. Totals computed server-side with Decimal; client-supplied totals are ignored. |
| `GET /api/invoices/{id}/` | Billing, Admin | — | `200` Invoice object with `lines: [...]`. |
| `POST /api/invoices/{id}/void/` | Billing (with approval — see OQ-5), Admin | `{ "reason": "..." }` | `200` Invoice (Voided). Audited; never a delete. |
| `POST /api/invoices/{id}/refund/` | Admin | `{ "reason": "...", "amount": "0.00" }` | `200` Invoice (Refunded, or Partially paid if a partial refund is approved — see OQ-5). Audited. |
| `GET /api/payments/` | Billing, Admin | `?invoice=&method=&date_from=&date_to=&page=` | Paginated payments. |
| `POST /api/payments/` | Billing, Admin | `{ invoice, amount, method, receipt_reference, paid_at }` | `201` Payment object. Rejected (`400`) if `amount <= 0` or if it would overpay the invoice. Invoice `amount_paid`, `balance`, and `status` update in the same transaction. |
| `GET /api/payments/{id}/` | Billing, Admin | — | `200` Payment object. |
| `POST /api/payments/{id}/void/` | Admin | `{ "reason": "..." }` | `200` Payment (Voided). Audited; invoice balances recompute in the same transaction. |

Offline payment recording only. Online payment collection is §12a below
(Spec 010, module M9). `method` values: Cash / Card / Bank transfer /
Other (exact list confirmed by the billing spec).

## 12a. `/api/online-payments/` — Online Payments **[M9]** (Spec 010, draft)

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `POST /api/online-payments/` | Billing, Admin | `{ invoice, amount }` | `201` OnlinePayment (Initiated) with gateway reference and payment link. Rejected (`400`) if the amount exceeds the outstanding balance or the invoice is Paid/Voided/Refunded. |
| `GET /api/online-payments/` | Billing, Admin | `?invoice=&status=&page=` | Paginated online payments. |
| `GET /api/online-payments/{id}/` | Billing, Admin | — | `200` OnlinePayment object with status history. |
| `POST /api/online-payments/webhook/` | Gateway (signature-verified, no session auth) | Gateway callback payload | Gateway's expected acknowledgement. Unverified → `401`/`403`, nothing recorded. A verified success creates a Spec 008 Payment (method Online) and updates the invoice in one transaction; a duplicate event id is ignored. |
| `POST /api/online-payments/{id}/refund/` | Admin | `{ "reason": "..." }` | `200` OnlinePayment (Refunded) once the gateway confirms the refund (Spec 010 OQ-010-4). Audited. |

No card data ever enters MediCore; sandbox/test mode only outside
production; gateway credentials from environment only. Gateway choice is
Spec 010 OQ-010-1 (JazzCash, Easypaisa, Stripe, or bank transfer — owner
picks).

## 13. `/api/reports/` — Dashboards and reports **[M10]** (Spec 009, draft)

Read-only. Every report respects the caller's role permissions; totals must
reconcile with source records (Master Plan M10).

| Method & path | Permission | Request | Response |
|---|---|---|---|
| `GET /api/reports/dashboard/` | Authenticated | — | `200` role-specific summary: today's appointments, pending tasks, counts the role may see. Shape is role-dependent and defined by the reporting spec. |
| `GET /api/reports/appointments/` | Receptionist, Admin, Department Manager (own department) | `?department=&date_from=&date_to=&status=` | `200` aggregated appointment summary for the period. |
| `GET /api/reports/billing/` | Billing, Admin | `?date_from=&date_to=` | `200` invoiced / paid / outstanding totals (Decimal strings). |
| `GET /api/reports/lab/` | Lab Technician, Admin | `?date_from=&date_to=&status=` | `200` request/result counts by status. |

Exports (CSV/PDF), if approved, are a separate decision — see OQ-6. No
report endpoint returns full national_id values or unnecessary patient
identifiers.

## 14. Audit access

There is **no public audit-write endpoint**. Audit events are written
server-side by the audit service. Read access:

| Method & path | Permission | Notes |
|---|---|---|
| `GET /api/audit-events/` | Admin; Auditor/Supervisor | `?actor=&action=&target_type=&date_from=&date_to=&page=`. Paginated. Metadata contains no sensitive content. |

The exact path/prefix for this group is provisional (`/api/audit-events/`
is adopted by this contract; it was not in the Master Plan's illustrative
list in §14.2).

## Open Questions

- **OQ-1 — API versioning.** Master Plan §14.1 says version "when
  compatibility needs justify it". This contract adopts unversioned `/api/`
  for the single browser client. Confirm whether `/api/v1/` should be
  adopted from the start to avoid a later breaking change.
- **OQ-2 — Duplicate-review confirmation flow.** §7.1/§7.5 assume a
  two-step flow (409 → duplicate-review → re-submit). The alternative is a
  single `POST /api/patients/` with a `duplicate_review_id` + decision in
  the same call. Spec 001 does not fix the HTTP shape; the patients
  implementation must pick one and amend this contract.
- **OQ-3 — `sex` vs `gender` field name.** Spec 001 D-11 says field
  `sex` / `gender`. This contract uses `sex` (matching the Spec 001
  data-model). Confirm the API field name before implementation.
- **OQ-4 — Admin password reset behaviour.** Whether `POST
  /api/users/{id}/reset-password/` sets an admin-chosen password or
  generates one (and how it reaches the user) is not decided, and depends
  on whether email is configured.
- **OQ-5 — Billing approvals.** Who may void an invoice (Billing alone, or
  Admin approval required?) and whether partial refunds exist are not
  decided; the billing spec must define them.
- **OQ-6 — Report exports.** Whether reports are exportable (CSV/PDF),
  and who may export them, is not decided; the reporting spec must define
  it, including protection of downloaded reports (Master Plan §12.3).
- **OQ-7 — Walk-in encounters without an appointment.** The contract
  allows `appointment: null` on encounter creation, following Master Plan
  §7.1 ("a walk-in may create an encounter without a prior appointment if
  policy allows"). Whether the hospital policy allows it is not decided.
- **OQ-8 — Doctor's patient-search scope.** Spec 001 grants Doctors
  read-only patient search. Whether a Doctor may search *all* patients or
  only patients in their authorised care relationships is not decided;
  the encounters/appointments specs must define the object-level rule.
