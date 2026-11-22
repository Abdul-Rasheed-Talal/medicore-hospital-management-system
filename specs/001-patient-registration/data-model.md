# Data Model Sketch: Patient Registration (001)

**Status**: Draft — sketch only, pending approval of the spec's Open Questions
(MRN format, required fields, duplicate rule, statuses). Do not generate
migrations from this sketch until the plan is approved.

## Patient

| Field | Type (proposed) | Notes |
|---|---|---|
| id | UUID (PK) | Stable internal key; never exposed as the patient identifier |
| mrn | String, unique, indexed | Auto-generated server-side. Proposed format `MC-YYYY-NNNNNN` — **to confirm** |
| full_name | String, required | As given; preserve original spelling |
| date_of_birth | Date, required (proposed) | Validation: not in the future — **to confirm required vs optional** |
| sex | Enum, required (proposed) | Values to confirm (e.g. Female / Male / Other / Prefer not to say) |
| phone | String, optional (proposed) | Format validation rule to confirm |
| address | Text, optional (proposed) | — |
| emergency_contact_name | String, optional (proposed) | — |
| emergency_contact_phone | String, optional (proposed) | — |
| national_id | String, optional, restricted visibility | Collect only if approved (spec Open Question 7); never in logs or list views |
| status | Enum: Active / Inactive (proposed) | Exact values to confirm; no hard delete |
| created_by | FK → User | Who registered the patient |
| created_at | DateTime (UTC) | — |
| updated_at | DateTime (UTC) | — |

Constraints: `mrn` unique (database); `date_of_birth <= today` (backend);
status transitions recorded, not silent.

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
decision allows the registration to proceed; a "same person" decision blocks
creation and links to the existing patient.

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

## Indexes (proposed)

- `mrn` (unique), `full_name` + `date_of_birth` (duplicate search),
  `phone` (if phone search is approved), `status`, `created_at`.
