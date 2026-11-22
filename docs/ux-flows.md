# MediCore UX Flows

**Status**: Draft for approval (Master Plan deliverable D-06).
**Date**: 2026-11-22
**Sources**: Master Plan v1.0 §§5, 7, 13; Constitution Principle VI;
Spec 001 (user stories, acceptance scenarios); `docs/api-contract.md`;
`docs/data-model.md`.

This document defines the navigation map, the screen list, and the user
journeys for each role's main flows. It is a flow/UX specification, not a
visual design: no wireframe tool, colour scheme, or pixel layout is decided
here. Screens use shadcn/ui components with Tailwind CSS (ADR-001).

## 1. UX principles (Master Plan §13)

- **Role-oriented navigation**: each user sees the tasks relevant to their
  job — nothing more. Hiding a menu item is display only; the backend still
  enforces permissions (Constitution III).
- **Consistent layout**: shared header, navigation, page titles, form
  patterns, and status indicators on every screen.
- **Fast patient lookup**: clear search fields, loading feedback, empty
  states, and duplicate warnings.
- **Safe actions**: confirm irreversible or high-impact operations; provide
  a clear cancellation path. Destructive/sensitive actions have safeguards
  (Constitution VI).
- **Workflow visibility**: show status, responsible role, and the next
  permitted action.
- **Readable forms**: group related fields, mark required fields, explain
  validation errors next to the input (field-level errors, Master Plan
  FR-021).
- **Status is never shown by colour alone** — always pair colour with text
  or an icon with an accessible name.
- **Responsive**: primary use is desktop; screens must remain usable on
  smaller screens.
- **Accessibility baseline** (Master Plan §13.2): keyboard-operable
  controls, visible focus, logical focus order, programmatic labels,
  understandable errors, adequate contrast and readable sizing, meaningful
  table headers, no punishing timeouts.

## 2. Navigation map

The app shell is: header (hospital name, current user + role, sign out) +
role-based side/top navigation + page content. The table shows which
top-level sections each role sees. "—" means the section is not shown (and
the backend denies it).

| Section | Admin | Receptionist | Doctor | Nurse | Lab Tech | Pharmacist | Billing | Dept Manager | Auditor |
|---|---|---|---|---|---|---|---|---|---|
| Dashboard | Yes | Yes | Yes | Yes* | Yes* | Yes* | Yes | Yes | Yes* |
| Patients (list/search) | Yes | Yes | Yes (read-only) | — in v1 | — in v1 | — in v1 | — in v1 | — | — |
| Appointments | Yes | Yes | Yes (own) | — | — | — | — | Yes (own dept) | — |
| Encounters | Yes | — | Yes (own) | —* | — | — | — | — | — |
| Laboratory queue | Yes | — | Yes (own requests) | — | Yes | — | — | — | — |
| Prescriptions [P1] | Yes | — | Yes (own) | — | — | Yes* | — | — | — |
| Billing | Yes | — | — | — | — | — | Yes | — | — |
| Reports | Yes | Yes (appt) | Yes* | — | Yes (lab) | — | Yes | Yes (own dept) | Yes |
| Administration | Yes | — | — | — | — | — | — | — | — |
| Audit log | Yes | — | — | — | — | — | — | — | Yes |

\* Marked cells depend on a feature spec that does not exist yet: Nurse and
Pharmacist dashboard/encounter/prescription access, and the Doctor's
report scope, are decided by the encounters, prescriptions, and reporting
specs. Nurse / Lab / Pharmacist / Billing have **no patient-search access
in v1** (Spec 001) — their own specs grant the access their workflows need.
The Auditor/Supervisor role is read-only throughout.

## 3. Screen list

Candidate screens from Master Plan §13.3, extended with the screens Spec
001 requires. "Spec" = the feature spec that owns the screen.

| # | Screen | Primary user | Spec |
|---|---|---|---|
| S-01 | Sign-in | All | M01 (accounts) |
| S-02 | Dashboard (role-specific) | All | M10 [P1] reporting |
| S-03 | Patient list / search | Receptionist, Admin, Doctor (read-only) | Spec 001 |
| S-04 | Patient registration form | Receptionist, Admin | Spec 001 |
| S-05 | Duplicate warning dialog | Receptionist, Admin | Spec 001 |
| S-06 | Patient profile (summary + visit history + correction/duplicate history) | Receptionist, Admin, Doctor (read-only) | Spec 001 (+ later specs for visit history) |
| S-07 | Appointment calendar / list | Receptionist, Admin, Doctor | M04 appointments |
| S-08 | Appointment booking form | Receptionist, Admin | M04 |
| S-09 | Encounter workspace (notes, diagnoses) | Doctor | M05 encounters |
| S-10 | Laboratory queue | Lab Technician | M08 lab [P1] |
| S-11 | Lab result entry form | Lab Technician | M08 [P1] |
| S-12 | Prescription form | Doctor | M06 prescriptions [P1] |
| S-13 | Billing workspace (invoices, payments, balances) | Billing, Admin | M09 billing [P1] |
| S-14 | Invoice form / payment recording | Billing | M09 [P1] |
| S-15 | Administration (users, roles, departments, staff) | Admin | M01/M02 |
| S-16 | Reports | Per-role (see §2) | M10 [P1] |
| S-17 | Audit log viewer | Admin, Auditor | M01/audit |

Common patterns on every screen: loading state, empty state with a next
action, error state with an understandable message and a retry path, and
success confirmation after every mutation (Constitution VI).

## 4. Journeys

Notation: `->` is a step; `[decision]` is a branch; `(!)` marks a step
where the system must confirm or warn before proceeding.

### 4.1 Receptionist — register a patient and book an appointment (WF-01)

Primary flow (Spec 001 User Stories 1–2; Master Plan WF-01).

```text
Sign in (S-01)
  -> Dashboard (S-02): today's appointments, quick "Register patient" action
  -> Patient search (S-03): enter MRN, or name (>= 3 chars), or phone
  -> [Match found?] --Yes--> Open patient profile (S-06)
  |                          -> [Details correct?] --No--> Correct demographics
  |                                                        (writes correction history)
  -> [No match] --+--> "No match found" empty state
                  |     -> "Register new patient" (S-04)
                  +--> Registration form: required full name, DOB, sex,
                       phone, national_id (CNIC/B-Form, 13 digits);
                       optional blood group, address, emergency contact
                  -> Submit -> backend validates (field-level errors if invalid)
                  -> [Duplicate warning? (S-05)]
                       --Yes (name+DOB or national_id match, blocking)-->
                            Show candidate match(es)
                            -> [Same person?] --Yes--> Go to existing patient (S-06)
                            -> [Different person?] --Yes--> Enter mandatory reason
                                                          -> Registration proceeds
                       --Yes (phone-only match, non-blocking)-->
                            Show "possible match — same phone number" warning
                            -> Receptionist may proceed without a decision
                       --No--> MRN issued (MC-YYYY-NNNNNN), success confirmation
  -> From patient profile (S-06): "Book appointment"
  -> Appointment form (S-08): provider/department, date/time, visit type
  -> Submit -> conflict/required-field validation
  -> Appointment appears in the schedule (S-07); success confirmation
```

Failure paths: unauthenticated → sign-in; Doctor attempting registration →
backend `403` (the button is hidden, but the denial is enforced server-side);
MRN collision or database failure mid-registration → safe failure, actionable
error, no partial record; concurrent duplicate submissions → only one record
(DB unique constraint).

### 4.2 Receptionist — patient arrival / check-in (WF-02, front-desk part)

```text
Sign in -> Appointments (S-07): today's list, filter by department/status
  -> Find the appointment (search by patient name/MRN or browse the day)
  -> Open appointment detail
  -> "Mark arrived" / "Check in" (!) -> status Arrived / Checked-in
  -> Appointment now appears in the Doctor's work queue
  -> [Patient does not arrive?] -> "Mark no-show" (!) with reason
  -> [Patient cancels?] -> "Cancel appointment" (!) with reason
```

### 4.3 Doctor — encounter (WF-02, clinical part)

```text
Sign in -> Dashboard (S-02): work queue (arrived/checked-in patients)
  -> Open patient from the queue (S-06, read-only demographics +
     authorised visit history)
  -> "Start encounter" (S-09)
     -- from an appointment: encounter linked to it
     -- walk-in (only if policy allows — see api-contract.md OQ-7):
        encounter with no appointment link
  -> Encounter workspace: reason for visit, notes, diagnosis fields
  -> Save draft (can return and edit while Draft)
  -> [Order a lab test? (P1)] -> create lab request from the encounter
  -> [Prescribe? (P1)] -> prescription form (S-12), draft -> finalised
  -> "Finalise encounter" (!) -> status Finalised
  -> [Correction needed after finalising?] -> traceable correction path
     (exact path defined by the encounters spec — see data-model.md OQ-2;
      the UI must not offer a silent edit)
```

Doctor permissions in this flow: read-only on patient demographics; cannot
create/edit/delete patient records; sees only authorised patients/encounters.

### 4.4 Lab Technician — lab queue and result entry (WF-03) [P1]

```text
Sign in -> Laboratory queue (S-10): requests by status
     (Requested / Collected / Received / In-progress / Completed / Cancelled)
  -> Filter by date / test / priority; open a request
  -> Request detail: minimum patient identifiers needed for the task,
     encounter link, specimen details
  -> Update status as work progresses: Collected -> Received -> In-progress
  -> Enter result (S-11): value, unit, reference range, author, timestamp
  -> Save as Draft -> Finalise -> (Approve, if the lab spec requires it;
     approver is not the author where separation is required)
  -> Result visible to the authorised clinician
  -> [Correction to a finalised result?] -> traceable correction, never a
     silent overwrite; unauthorised users cannot alter results
```

Lab staff see only the lab workflow and the minimum patient identifiers
needed to perform the task — no full patient demographics, no clinical
notes, no billing.

### 4.5 Billing — invoice and payment (WF-04) [P1]

```text
Sign in -> Billing workspace (S-13): invoices by status, outstanding balances
  -> "New invoice" (S-14): select patient (billing's patient access is
     granted by the billing spec — see §2 note), select approved chargeable
     services -> line items with quantities/prices
  -> System computes subtotal/discount/tax/total (Decimal; shown live)
  -> Issue invoice -> status Unpaid; invoice number assigned
  -> "Record payment": amount, method, date, receipt reference
     -> System validates amount > 0 and no overpayment
     -> Balance + status update (Unpaid -> Partially paid -> Paid)
     -> Receipt / payment reference shown
  -> [Correction/refund?] -> audited void/refund process (!)
     (never a delete; who may void is defined by the billing spec)
```

Billing staff see billing data; clinical notes are hidden unless the billing
spec specifically requires them.

### 4.6 Admin — user and permission administration (WF-05)

```text
Sign in -> Administration (S-15)
  -> Users: create account -> assign approved role(s) -> activate
     -> user signs in and sees only permitted functions/records
  -> Roles: view/edit role -> permission mapping (explicit codes)
  -> [Role changed?] -> takes effect per session policy
     (see architecture.md OQ-2 — the UI must state what happens to
      existing sessions)
  -> [Account no longer authorised?] -> Disable account (!) with reason
     -> access revoked; action audited
  -> Departments / staff: create/edit/deactivate (never delete in-use
     reference data)
  -> Audit log (S-17): filter by actor / action / target / date;
     read-only; no sensitive content in the log
```

Admin powers do not include reading all clinical content by default: Admin
has administrative configuration access, and clinical access only where
explicitly required (Master Plan §5).

## 5. Cross-cutting interaction rules

- **Search first, then create**: every "new patient" flow starts with a
  search (Spec 001). The registration form is reached from an explicit
  no-match state, not as the default landing.
- **Duplicate warnings are interruptive**: a blocking duplicate warning is
  a modal/dialog (S-05), not a toast — the user must choose before the flow
  continues.
- **Confirmations**: merge, finalise, void/refund, disable account, cancel
  appointment — all require explicit confirmation with the consequence
  stated.
- **Errors**: field-level, next to the input; API errors shown in plain
  language; never expose stack traces or data the role may not see.
- **National ID handling in the UI**: full value only for Receptionist/
  Admin; masked (last 4 digits) for everyone else; never shown in list
  views; never placed in a URL.
- **Session expiry**: an expired session returns the user to sign-in with
  a message; unsaved form input handling on expiry is OQ-4 below.

## Open Questions

- **OQ-1 — Doctor's patient list scope.** Can a Doctor browse/search all
  patients, or only patients in their authorised care relationships? This
  decides whether S-03 for Doctors is a full search or a queue-scoped view.
- **OQ-2 — Walk-in encounters.** Whether walk-in encounters (no prior
  appointment) are allowed is undecided (api-contract.md OQ-7). If allowed,
  the entry point needs a defined screen (from S-06 or S-02).
- **OQ-3 — Nurse and Pharmacist screens.** Their workflows (observations
  M07, prescriptions/dispensing M06/M12) have no approved spec; their
  navigation and screens cannot be designed until those specs exist. The
  map in §2 marks them accordingly rather than inventing them.
- **OQ-4 — Unsaved work on session expiry.** What happens to a half-filled
  form when the session expires (draft saved? data lost with a warning?) is
  not decided.
- **OQ-5 — Dashboard contents per role.** The exact metrics/cards on each
  role's dashboard are decided by the reporting spec [P1]; this document
  fixes only that the dashboard is role-specific.
- **OQ-6 — Wireframes.** No wireframes exist yet. Whether wireframes are
  produced (and in what tool) before frontend implementation is a Phase 2
  decision, not fixed here.
