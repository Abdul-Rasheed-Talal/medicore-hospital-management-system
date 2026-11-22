# Data Model Sketch: Patient Registration (001)

**Status**: Approved by owner 2026-11-22 — decisions D-01–D-10 (spec.md)
applied. Migrations may be generated from this sketch once the scaffold
exists.

## Patient

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | Stable internal key; never exposed as the patient identifier |
| mrn | String, unique, indexed | Auto-generated server-side. Format `MC-YYYY-NNNNNN`, sequence resets yearly (D-01) |
| full_name | String, required | As given; preserve original spelling |
| date_of_birth | Date, required | Validation: not in the future |
| sex | Enum, optional | Female / Male / Other / Prefer not to say |
| phone | String, required | 9–15 digits, optional leading `+` |
| address | Text, optional | — |
| emergency_contact_name | String, optional | — |
| emergency_contact_phone | String, optional | — |
| national_id (CNIC) | String, optional, encrypted at rest | Visible in full only to Receptionist/Admin; masked (last 4 digits) for all other roles; never in logs, list views, or URLs (D-07) |
| status | Enum: Active / Inactive / Merged / Archived | No hard delete; status transitions recorded with a reason (D-05) |
| created_by | FK → User | Who registered the patient |
| created_at | DateTime (UTC) | Displayed in Asia/Karachi |
| updated_at | DateTime (UTC) | Displayed in Asia/Karachi |

Constraints: `mrn` unique (database); `date_of_birth <= today` (backend);
`phone` matches `^\+?[0-9]{9,15}$` (backend); status transitions recorded,
not silent.

## DuplicateCandidate

| Field | Notes |
|---|---|
| id | UUID (PK) |
| new_registration_data | The submitted fields that triggered the warning (stored for the review, not as a patient) |
| candidate_patient | FK → Patient (the existing record it may duplicate) |
| matched_on | Which fields matched (e.g. name + date of birth) |
| decision | Enum: Pending / Different person / Same person |
| decided_by | FK → User (nullable until decided) |
| decided_at | DateTime (nullable until decided) |
| reason | Free text, required when deciding |

Rule: a candidate is created, never an automatic merge. A "different person"
decision (with a mandatory written reason) allows the registration to
proceed; a "same person" decision blocks creation and links to the existing
patient. A phone-only match creates a candidate flagged as a weak/secondary
signal and does not block registration. Merging two records is a separate
Admin-only action: the losing record's status becomes Merged, never deleted.

## PatientCorrection

| Field | Notes |
|---|---|
| id | UUID (PK) |
| patient | FK → Patient |
| field | Which demographic field changed |
| old_value | Previous value (may be empty) |
| new_value | New value |
| author | FK → User |
| created_at | DateTime (UTC) |

Rule: one row per change; history is append-only. The current value lives on
Patient; the history lives here.

## AuditEvent (shared, from the `audit` app)

| Field | Notes |
|---|---|
| id | UUID (PK) |
| actor | FK → User |
| action | e.g. `patient.create`, `patient.correct`, `patient.status_change`, `duplicate.review` |
| target_type / target_id | e.g. `Patient`, the patient id |
| timestamp | DateTime (UTC) |
| outcome | Success / failure |
| metadata | Limited, non-sensitive context only |

Rule: no passwords, tokens, or clinical content in audit metadata.

## Relationships

- One Patient → many PatientCorrections, many DuplicateCandidates (as candidate),
  many AuditEvents.
- One User → many Patients (as created_by), many Corrections, many AuditEvents.
- Patient is distinct from User: a patient is a person receiving care; a user
  account is a staff identity that can authenticate (Master Plan §7.1).

## Indexes

- `mrn` (unique), `full_name` + `date_of_birth` (duplicate search),
  `phone` (phone search and secondary duplicate signal), `status`, `created_at`.
- No index on `national_id`: it is encrypted at rest and not searchable in v1.
