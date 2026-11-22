# Feature Specification: Dashboard and Reports

**Feature Branch**: `docs/medicore-all-specs` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — **P1 CANDIDATE, NOT APPROVED.** Dashboard and
operational reports are a P1 Candidate in the Master Plan (§4.2:
"Dashboard and operational reports — start with simple, role-specific
summaries") and §6 M10 ("Basic dashboard for MVP; advanced analytics
later"). The roadmap (§17) places reports in Phase 7 (Weeks 20–22),
after the Phase 6 supporting module is chosen and stable. This spec is a
requirements draft for that decision; implementation may proceed only
once the owner approves this spec (Master Plan §4.4 Scope Control Rule).

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline), §4.2
P1 Candidate, §5 role access boundaries, §6 M10, §8 FR-018 / FR-019 /
FR-020 / FR-024, §9 NFR-01–07 and §9.1, §10.4 `reporting` app boundary,
§16, §17 Phase 7; MediCore Constitution v1.0.0, Principles I, III, IV,
V, VI, VII, VIII.

## Overview

### Problem

Every role in the hospital needs a different answer to "what needs my
attention today?" — a receptionist needs today's appointments, a doctor
needs their own work queue, billing needs unpaid invoices, a department
manager needs department totals. If each role instead opens raw lists and
counts by hand, work is missed and the numbers different people quote
will not agree. The dashboard and reports feature gives each role one
view built only from records they are authorised to see, with filters
(date, department, status) that apply consistently, totals that reconcile
exactly with the source records they summarise, and exports that are
protected and carry no unnecessary patient identifiers.

This spec is deliberately narrow: role-specific dashboards, filtered
operational reports, and protected exports — all computed from existing
source records, with no separate reporting store and no advanced
analytics. It does not include a patient portal, notifications, or any
analytics beyond the basic summaries listed here.

### Scope

**In scope**

- Role-specific dashboards: counts, work queues, appointment summaries,
  pending tasks, and basic financial/operational metrics where the role
  is authorised (FR-018, Master Plan §6 M10)
- Operational reports with date, department, and status filters
  (FR-019, M10)
- Reconciliation: every report total is computed from the source records
  it summarises, so totals agree with the underlying lists (M10)
- Protected exports: role-checked, audit-logged, with no unnecessary
  patient identifiers (M10)

**Out of scope**

- Advanced analytics, trend forecasting, or clinical decision support
  (Master Plan §4.2 P2 "analytics" — defer unless mandated)
- A separate reporting database, data warehouse, or cached totals store
  — totals are computed from source records at query time (see FR-004)
- Patient portal or notifications (Master Plan §4.2 P2, M13)
- Any new data collection: dashboards and reports only summarise records
  other features already create
- Real-time push/live updates (refresh behaviour is OQ-009-5)
- Cross-hospital or multi-organisation reporting (single hospital,
  Master Plan §2.4)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — See my role dashboard on sign-in (Priority: P1)

After signing in, each user lands on a dashboard that shows only their
own work: counts, their work queue, today's appointment summary, and
pending tasks. A doctor sees their own patients and appointments, not
the hospital's finances; billing sees outstanding balances, not clinical
notes.

**Why this priority**: The dashboard is the front door of the system for
every role. If it shows the wrong person's work — or work the role is not
allowed to see — it is both useless and a privacy failure. This is Master
Plan §6 M10 and §8 FR-018.

**Independent Test**: Signed in as each role in turn with synthetic data,
the user sees their own counts and queues, and sees nothing belonging to
another role's authorised scope. No report or export feature needs to
exist for this to be demonstrated.

**Acceptance Scenarios**:

1. **Given** a signed-in Receptionist,
   **When** they open the dashboard,
   **Then** they see today's appointment counts by status, the
   check-in queue, and the count of duplicate reviews pending — and no
   financial totals and no clinical notes.
2. **Given** a signed-in Doctor,
   **When** they open the dashboard,
   **Then** they see their own appointments for today, their draft
   encounters awaiting finalisation, and their own pending tasks — and
   no other doctor's queue and no hospital-wide financial figures.
3. **Given** a signed-in Billing user,
   **When** they open the dashboard,
   **Then** they see counts and totals of Unpaid and Partially paid
   invoices and the outstanding balance — and no clinical notes and no
   patient CNIC / B-Form number. (Only if the billing module M09 is
   included; otherwise this section does not appear — see Edge Cases.)
4. **Given** a signed-in Admin,
   **When** they open the dashboard,
   **Then** they see hospital-wide operational aggregates (registrations,
   appointments, encounters, billing totals where M09 is included) —
   but no clinical content unless explicitly required (Master Plan §5:
   Admin has no automatic entitlement to read all clinical content).
5. **Given** a signed-in user,
   **When** they open the dashboard with no data for their scope,
   **Then** they see an explicit empty state (e.g. "No appointments
   today"), not a blank or ambiguous screen.

### User Story 2 — Filter an operational report (Priority: P1)

An authorised user opens an operational report (e.g. appointments,
registrations, invoices), applies date, department, and status filters,
and sees a list and totals that match the filters exactly.

**Why this priority**: A report whose filters do not change its totals
is worse than no report — it produces numbers people act on that are
wrong. Filters are FR-019 and M10.

**Independent Test**: With synthetic records across dates, departments,
and statuses, applying each filter changes the list and the totals to
exactly the matching records, and clearing the filters restores the full
set.

**Acceptance Scenarios**:

1. **Given** an authorised user viewing the appointments report,
   **When** they filter by a single date,
   **Then** the list and the count show only appointments on that date
   (Asia/Karachi day boundaries), and the count equals the number of
   rows shown.
2. **Given** an authorised user viewing a report,
   **When** they filter by department,
   **Then** only records belonging to that department are listed and
   counted — a Department Manager sees only their own department's
   records.
3. **Given** an authorised user viewing a report,
   **When** they filter by status (e.g. invoices: Unpaid),
   **Then** only records in that status are listed and counted.
4. **Given** filters that match no records,
   **When** the report runs,
   **Then** an explicit "no records match" state is shown with the
   filters still visible, not an empty or ambiguous screen.
5. **Given** a report list,
   **When** the user pages through it,
   **Then** results are paginated and sorted deterministically (Master
   Plan FR-024).

### User Story 3 — Reconcile a report total with its source records (Priority: P1)

Any total shown on a dashboard or report can be traced back to the
records it summarises, and the numbers agree exactly.

**Why this priority**: M10 requires report totals to reconcile with
source records. A total that cannot be explained from the underlying
records is not a report, it is a guess — and for financial totals it is
a data-integrity failure (Constitution Principle IV).

**Independent Test**: For each report total in test data, the total
computed by the report equals the total computed by directly counting or
summing the underlying source records with the same filters.

**Acceptance Scenarios**:

1. **Given** a dashboard showing "appointments today: N",
   **When** the underlying appointment list for today is counted,
   **Then** the count is exactly N.
2. **Given** a financial summary showing outstanding balance B (Billing /
   Admin only, M09 included),
   **When** the balances of the listed Unpaid and Partially paid
   invoices are summed,
   **Then** the sum is exactly B.
3. **Given** a report total,
   **When** a user opens the underlying list with the same filters,
   **Then** the list and the total agree — the total is derived from
   those records, not from a separate stored figure.

### User Story 4 — Export a report (Priority: P2)

An authorised user exports a report (e.g. for a supervisor review). The
export is role-checked and audit-logged, and it contains no unnecessary
patient identifiers — never a CNIC / B-Form number, and patient names or
MRNs only where the report is patient-level and the role is authorised
to see them.

**Why this priority**: Exports are where access control most easily
leaks: a file leaves the system and cannot be taken back. M10 requires
exports to be protected and free of unnecessary patient identifiers, and
the constitution requires data minimisation (Principle III, §2.4).

**Independent Test**: Exporting each report as each role produces a file
only for authorised roles, an audit event is recorded, and no export
contains a CNIC / B-Form number or any identifier the exporting role is
not authorised to see.

**Acceptance Scenarios**:

1. **Given** a signed-in Receptionist,
   **When** they export the appointments report,
   **Then** the export succeeds, contains only the fields their role may
   see, and an audit event records who exported what, when, and with
   which filters.
2. **Given** a signed-in Billing user,
   **When** they export a financial summary,
   **Then** the export contains invoice numbers, amounts, and balances —
   and no clinical notes and no CNIC / B-Form number.
3. **Given** any export,
   **When** its contents are inspected,
   **Then** no CNIC / B-Form number appears anywhere in it, in any
   report, for any role.
4. **Given** a signed-in Doctor,
   **When** they try to export the hospital-wide financial summary,
   **Then** the export is denied by the backend — the role is not
   authorised for that report.
5. **Given** an aggregate report (counts/totals by department or day),
   **When** it is exported,
   **Then** it contains no patient identifiers at all — aggregates do not
   need them.

### User Story 5 — Department manager's department view (Priority: P3)

A Department Manager opens the dashboard and sees operational summaries
scoped to their own department only: appointment counts, pending tasks,
and basic metrics for that department.

**Why this priority**: Master Plan §5 gives the Department Manager
aggregated or department-scoped information, with patient-level detail
only when justified. The department scope is the access boundary; without
it the role sees either everything or nothing.

**Independent Test**: A Department Manager for Department A sees
Department A's figures and none of Department B's, in both the dashboard
and the filtered reports.

**Acceptance Scenarios**:

1. **Given** a Department Manager for Department A,
   **When** they open the dashboard,
   **Then** all counts and queues shown are Department A's only.
2. **Given** a Department Manager for Department A,
   **When** they open a patient-level list,
   **Then** patient-level detail is shown only where justified for their
   role (see OQ-009-3); otherwise they see aggregates only.

### Edge Cases

- What happens when a dashboard section's underlying module is not
  included (e.g. the billing section when M09 was deferred, or the lab
  queue when M08 was deferred)? The section does not appear — no error,
  no empty box promising data that cannot exist. Dashboard sections are
  driven by which modules exist, not hard-coded.
- What happens when a date filter spans a day boundary? Dates are
  interpreted in Asia/Karachi: a "today" filter means the Asia/Karachi
  calendar day, and a date-range filter includes whole Asia/Karachi days.
- What happens when two roles look at the "same" number (e.g. Admin and
  Billing both see outstanding balance)? They see the same number: both
  views compute it from the same source records with the same definition.
- What happens when a report is exported and then the underlying records
  change? The export is a snapshot of the moment it was generated; it is
  labelled with the generation time and filters, and it is not updated.
  Whether exports are stored or only downloaded is OQ-009-4.
- What happens when a user has no department (e.g. Admin)? Department
  filtering still works: Admin may filter by any department; a user with
  no department assignment sees hospital-wide aggregates only where
  authorised.
- What happens when a Nurse, Lab Technician, or Pharmacist opens the
  dashboard? They see only the queues their own feature specs grant them
  (their own module's work queue and pending tasks) — this spec does not
  grant them patient search or any wider view (Spec 001: no patient
  search in v1 for these roles).
- What happens when a dashboard is opened before any module data exists?
  Empty states throughout — counts of zero with labels, not errors.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a role-specific dashboard after
  sign-in, showing only records and figures the signed-in role is
  authorised to see (Master Plan FR-018, §6 M10). No role may see another
  role's work queue or figures through the dashboard.
- **FR-002**: Each dashboard MUST show, where the underlying module
  exists and the role is authorised: counts (e.g. appointments today by
  status, registrations today), the role's work queue (e.g. today's
  appointments, check-in queue, lab queue, duplicate reviews pending),
  appointment summaries, pending tasks (e.g. draft encounters awaiting
  finalisation, unpaid invoices, duplicate reviews), and basic
  financial/operational metrics where authorised (e.g. outstanding
  balance, collections in period — Billing/Admin only, M09 included).
- **FR-003**: Reports MUST support date, department, and status filters
  (Master Plan FR-019, M10). Filters MUST apply identically to the list
  and to the totals shown with it. Date filters use Asia/Karachi day
  boundaries. Filtered lists MUST be paginated and sorted
  deterministically (Master Plan FR-024).
- **FR-004**: Every total shown on a dashboard or report MUST be computed
  from the source records it summarises, at query time, with the same
  filters as the list it accompanies (M10: "report totals reconcile with
  source records"). The system MUST NOT keep a separate stored totals
  figure that can drift from the source records.
- **FR-005**: Exports MUST be protected: an export is permitted only for
  a role authorised for that report, is audit-logged (who, when, which
  report, which filters, how many rows), and MUST contain no unnecessary
  patient identifiers (M10). In particular: no CNIC / B-Form number in
  any export for any role; patient name and MRN only in a patient-level
  report for a role authorised to see them; aggregate reports MUST
  contain no patient identifiers at all; no clinical notes in any export.
- **FR-006**: Dashboards and reports MUST NOT expose clinical content
  beyond the viewing role's authorisation. Admin sees operational
  aggregates without automatic access to clinical content (Master Plan
  §5); Billing sees financial data only; Doctor sees their own scope only.
- **FR-007**: Dashboard sections for a module that is not included in the
  build MUST NOT appear (no error, no empty placeholder promising data).
  Sections appear only when their source module exists.
- **FR-008**: The system MUST enforce permissions on the backend for every
  dashboard figure, report, and export: the backend MUST re-check the
  caller's role and scope (own / department / hospital-wide) for each
  query, not rely on the UI hiding a section.
- **FR-009**: The system MUST record audit events for exports and for
  access to sensitive reports (actor, report, filters, timestamp,
  outcome) (Master Plan FR-020). Audit records MUST NOT contain
  passwords, tokens, clinical content, or patient identifiers beyond
  what the report itself legitimately contains.
- **FR-010**: The system MUST return understandable errors without
  exposing secrets, stack traces, or unnecessary patient data (Master
  Plan FR-023), and MUST validate filter input on the backend (Master
  Plan FR-021) — e.g. an end date before a start date is rejected with a
  field-level error.
- **FR-011**: The system MUST reject unauthenticated access to all
  dashboard, report, and export endpoints.
- **FR-012**: Dashboard and report responses MUST meet the provisional
  performance target for common operations (Master Plan NFR-05: within 2
  seconds under a small demo dataset and local test conditions). Totals
  MUST be computed by aggregate queries over indexed source tables, not
  by loading full record sets into application memory.

### Key Entities

- **DashboardView**: Not a stored entity. A per-role, per-scope assembly
  of counts, queues, summaries, and metrics, computed at request time
  from source records (patients, appointments, encounters, invoices,
  laboratory requests — only the modules that exist). Key attributes:
  role, scope (own / department / hospital-wide), sections shown, figures
  shown. Nothing about it is stored; it is recomputed on every load.
- **Report**: A defined, authorised query over source records with
  filters (date range, department, status), a list, and totals. Key
  attributes: report definition (which records, which filters), applied
  filters, list (paginated), totals (computed from the same filtered
  source records). The list of reports that exist is OQ-009-1.
- **ReportExport**: The audit record of an export. Key attributes:
  report, exported-by, exported-at, applied filters, row count, format
  (format itself is OQ-009-2). The exported file is a snapshot labelled
  with generation time and filters; whether the file itself is stored or
  only downloaded is OQ-009-4.
- **AuditEvent**: Who did what, when, to which report/export, and whether
  it succeeded (shared `audit` app; see Spec 001 data-model.md).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Signed in as each role, the dashboard shows that role's own
  counts and queues and nothing outside its authorised scope, in manual
  and automated permission tests.
- **SC-002**: For every report total in test data, the total equals the
  count or sum computed directly from the source records with the same
  filters — 100% reconciliation across all reports and filter
  combinations tested.
- **SC-003**: Applying a date, department, or status filter changes the
  list and the totals to exactly the matching records, in automated tests.
- **SC-004**: No export produced in test data contains a CNIC / B-Form
  number, and no export contains a patient identifier the exporting role
  is not authorised to see.
- **SC-005**: A user attempting to view a report or export outside their
  role/scope is denied by the backend (not merely by a hidden link) in
  automated permission tests.
- **SC-006**: All P1 acceptance scenarios above pass against the
  implemented feature before it is considered complete — once this spec
  is approved.

## Permissions

Dashboard and report access by role. "Own" means records assigned to or
created by the user; "Dept" means the user's department; "All" means
hospital-wide where authorised. A section appears only when its source
module exists (FR-007).

| Role | Own appointments / queue | Dept appointments | Hospital-wide ops aggregates | Financial metrics | Clinical content | Exports |
|---|---|---|---|---|---|---|
| Admin | Yes | Yes | Yes | Yes (where M09 included) | No automatic access (Master Plan §5) | Yes, authorised reports only |
| Receptionist | Yes (front-desk queue) | No | No | No | No | Yes, appointments/registration reports only |
| Doctor / Clinician | Yes (own queue, own draft encounters) | No | No | No | Own patients' authorised history only | Yes, own-scope reports only |
| Nurse | Own module queue only (per nursing spec, when specified) | No | No | No | Assigned duties only | Only where their spec grants it |
| Lab Technician | Own lab queue only (per lab spec, when specified) | No | No | No | No | Only where their spec grants it |
| Pharmacist | Own module queue only (per pharmacy spec, when specified) | No | No | No | No | Only where their spec grants it |
| Billing | No | No | No | Yes (where M09 included) | No | Yes, financial reports only |
| Department Manager | No | Yes (own dept only) | No | Dept aggregates only, where authorised | No | Yes, own-dept reports only |
| Auditor / Supervisor | No | No | Yes, read-only authorised views | Yes, read-only where authorised | No | Yes, authorised reports only |

Department Manager and Auditor / Supervisor appear in Master Plan §5,
but whether those roles exist as system roles in v1 is OQ-009-3 — the
table states what they may see *if* the roles exist. Nurse / Lab /
Pharmacist have no patient search in v1 (Spec 001) and this spec grants
them no wider view; their dashboard sections come from their own feature
specs when those are written.

## Data fields

There is no new stored data in this feature beyond the audit record of an
export. The fields below are the filter and output fields of reports.

- **Filters (all reports where applicable)**: date range (start date,
  end date — Asia/Karachi days), department, status (the status enum of
  the records being reported on, e.g. appointment status, invoice
  status), page, page size, sort.
- **Dashboard figures**: counts (integers, never negative), sums of
  money (`Decimal`, 2dp — only in financial sections, only where M09 is
  included), queues (paginated lists of the underlying records, showing
  only fields the role may see).
- **Report rows**: only fields the viewing role is authorised to see for
  those records. Patient-identifying fields in a row are limited by
  FR-005: name and MRN only in patient-level reports for authorised
  roles; never CNIC / B-Form, never phone unless the report's purpose
  requires it and the role is authorised (see OQ-009-1).
- **ReportExport audit record**: report, exported-by, exported-at,
  applied filters, row count, format.

## Assumptions

- The hospital is a single organisation; one deployment instance (Master
  Plan §2.4).
- Authentication and RBAC (M01) exist before this feature; dashboard and
  report endpoints assume a signed-in user with a role and, where
  relevant, a department assignment. The modules being summarised
  (patients M03, appointments M04, encounters M05, and the Phase 6
  supporting module) exist before their dashboard sections can appear.
- All demo/test data is synthetic; no real patient records are used.
- Display timezone for dates/times is Asia/Karachi; timestamps are stored
  in UTC and displayed in Asia/Karachi (ADR-001). Date filters use
  Asia/Karachi day boundaries.
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner
  (2026-11-22); Python 3.12 / Node 20 LTS.
- Patient identity and privacy rules are inherited from Spec 001 and are
  not re-decided here: MRN `MC-YYYY-NNNNNN`; required patient fields
  name / DOB / phone / gender / CNIC-B-Form; blood group optional;
  patient statuses Active / Inactive / Merged / Archived; CNIC encrypted
  at rest, full view only Receptionist/Admin, masked otherwise, never
  searchable; Nurse / Lab / Pharmacist / Billing have no patient search
  in v1.
- Billing figures on any dashboard or report exist only if the billing
  module (Spec 008, M09) is included; financial metrics are never
  invented from non-billing data.

## Decisions

No decisions were delegated for this spec and none are taken here. The
rules below are **inherited, not re-decided** — they come from the Master
Plan, the constitution, ADR-001, or Spec 001, and changing one requires a
change to its source, not to this spec.

- **Inherited — role-specific summaries (Master Plan §4.2, §6 M10)**:
  start with simple, role-specific summaries; advanced analytics later.
- **Inherited — totals reconcile (Master Plan §6 M10)**: report totals
  reconcile with source records.
- **Inherited — exports protected, identifiers minimised (Master Plan
  §6 M10)**: protect exports and avoid exposing unnecessary patient
  identifiers.
- **Inherited — role access boundaries (Master Plan §5)**: Admin has no
  automatic entitlement to read all clinical content; Department Manager
  sees aggregated or department-scoped information; Auditor/Supervisor
  is read-only on authorised views; Billing sees billing data with
  clinical notes hidden.
- **Inherited — patient privacy (Spec 001 D-06/D-07/D-12)**: CNIC /
  B-Form encrypted, Receptionist/Admin only, never searchable; no
  patient search in v1 for Nurse / Lab / Pharmacist / Billing.
- **Inherited — no separate totals store (Constitution Principle II,
  Master Plan §10.3)**: one source of truth for business rules and data;
  totals are computed from source records, not kept in a second store
  that can drift.

Everything else about dashboards and reports is an Open Question below.

## Open Questions

These are genuinely undecided. They must be answered by the owner (with
hospital/discovery input where noted) before or at approval; this spec
does not guess them.

- **OQ-009-1 — The exact list of reports and metrics.** Which reports
  exist (appointments by day/department/status? registrations per period?
  encounters per clinician? collections per period?) and exactly which
  figure appears on each role's dashboard? The spec fixes the *kinds* of
  content (counts, queues, summaries, pending tasks, basic metrics) and
  the rules they must obey; the concrete list needs the owner's call,
  informed by which modules are included.
- **OQ-009-2 — Export formats.** CSV? PDF? Both? The Master Plan does
  not say. The choice affects the export implementation and what a
  "report" file looks like; it also decides whether exports are meant to
  be printed, filed, or re-imported.
- **OQ-009-3 — Do Department Manager and Auditor / Supervisor exist as
  system roles in v1?** Master Plan §5 lists them as actors, but the
  role set for v1 is decided by the auth/RBAC spec (M01). If they do not
  exist in v1, their rows in the Permissions table do not apply and
  department reporting is Admin-only.
- **OQ-009-4 — Are exported files stored or only downloaded?** If
  stored, where, for how long, and who may re-download them? If only
  downloaded, the audit record (ReportExport) is the only trace. Either
  way, a stored export containing patient identifiers is a privacy
  liability and needs a retention rule.
- **OQ-009-5 — Refresh behaviour.** Is the dashboard computed fresh on
  every load only, or does it auto-refresh? (No live push is in scope
  either way; the question is only whether the page reloads figures on
  a timer.)
- **OQ-009-6 — Financial metrics, if billing is included.** Which
  financial figures appear (outstanding balance total? collections in a
  period? invoices by status?) and for exactly which roles? The spec
  allows Billing/Admin (and Auditor read-only, if that role exists) but
  the concrete list needs the owner's call — and it depends on Spec 008
  being approved at all (OQ-008-1).
- **OQ-009-7 — Patient identifiers in patient-level report rows.** Name
  and MRN are the working assumption for authorised roles; is the
  patient's phone number ever needed in a report row, and is date of
  birth ever shown (e.g. to distinguish same-name patients)? Data
  minimisation says no unless a workflow needs it — the owner must say
  which reports, if any, need more than name + MRN.
- **OQ-009-8 — Department assignment of staff.** Department-scoped
  dashboards need every staff user assigned to a department (M02). What
  happens for staff with no department, or with more than one? That
  belongs to the hospital-setup spec, but this feature depends on the
  answer for its department scope to work.

## Deferred (not decided here)

- **Advanced analytics, trends, forecasting**: deferred per Master Plan
  §4.2 (P2) and §6 M10 ("advanced analytics later").
- **Patient portal and notifications**: out of scope for this feature
  (Master Plan §4.2 P2, M13).
- **Real-time / live dashboard updates**: not in scope; see OQ-009-5.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1;
  §§19–23 (deployment, risk register, governance/decision log,
  acceptance, open decisions) are listed in the contents but absent from
  the document. Explicitly deferred: they must be supplied or formally
  deferred before release planning (Phase 8), but they do not block this
  feature's specification.
- **Auth/session strategy is decided (Spec 001 D-09, ADR-001)**; no auth
  question is reopened here.
