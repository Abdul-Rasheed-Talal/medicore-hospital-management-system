# Feature Specification: Billing and Payments

**Feature Branch**: `docs/medicore-all-specs` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — **committed module M8, NOT APPROVED, DO NOT IMPLEMENT
YET.** The owner decided on 2026-11-22 that Prescription, Billing and
Online Payments are each their own separate module because they are
important, and must not be lumped together or deferred as a group.
Billing is therefore committed scope in the module plan (M8), not a
deferred candidate — the old Phase 6 "choose lab OR billing OR
prescription" pick no longer applies to it. This spec becomes an
implementation instruction only when the owner confirms or replaces the
Open Questions below and approves this spec (Master Plan §4.4 Scope
Control Rule). Until then it is a requirements draft, not an
implementation instruction.

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline), §4.2
P1 Candidate, §4.3 out of scope, §5 Billing Staff / Cashier, §6 M09, §7
WF-04, §7.1 invoice vs. payment, §8 FR-016 / FR-017 / FR-020 / FR-021 /
FR-022 / FR-023 / FR-024, §9 NFR-01–05 and §9.1 (decimal-safe money),
§10.4 `billing` app boundary, §16, §17 Phase 6; MediCore Constitution
v1.0.0, Principles I, III, IV, V, VI, VII, VIII.

## Overview

### Problem

A hospital must be able to state what a patient owes and record what was
actually received — as two different facts. If the amount owed and the money
received live in one editable field, the hospital cannot tell whether an
invoice is unpaid, partially paid, or paid; cannot prove what changed or
when; and cannot survive a rounding error in its own totals. Billing
therefore keeps an **invoice** (what is owed, built from approved chargeable
services) strictly separate from **payments** (money received, each with
amount, method, date, and receipt reference), computes every total with
decimal-safe arithmetic, and retains the full transaction history.

This spec is deliberately narrow: create invoices from approved services,
record payments, track the invoice balance and state, and correct mistakes
through an approved, audited void/refund process. It does not include real
payment settlement, banking integration, insurance claims, or tax/discount
rules — none of those are defined (see Open Questions).

### Scope

**In scope**

- Create an invoice with line items from approved services and charges
  (FR-016, Master Plan §6 M09, §7 WF-04 steps 1–2)
- Calculate subtotal and total using decimal-safe arithmetic; discount/tax
  only if defined — no discount or tax rule is defined in v1, so none is
  applied (see FR-003 and OQ-008-6 / OQ-008-7)
- Record one or more payments per invoice, each with amount, method, date,
  and receipt reference, as records separate from the invoice (FR-017,
  WF-04 steps 3–5)
- Track invoice states Unpaid / Partially paid / Paid / Voided / Refunded
  and the outstanding balance; prevent overpayment and invalid transitions
  (M09, WF-04 step 4)
- Correct mistakes through an approved, audited void/refund process; retain
  transaction history; never hard-delete financial records (WF-04 step 6,
  Constitution Principle IV, Master Plan FR-022)

**Out of scope**

- Real payment settlement, banking integrations, card processing, or
  insurance claim submission (Master Plan §4.3 — out of scope unless
  explicitly approved)
- Discount or tax calculation rules (none defined; see Open Questions)
- Setting service prices — prices come from the approved service catalog
  (M02 hospital setup); this spec only consumes them
- Clinical content: Billing sees billing data only; clinical notes are
  hidden unless specifically needed (Master Plan §5)
- Patient portal, notifications, or patient self-payment
- Multi-hospital tenancy; migration of real financial records; all
  demo/test data is synthetic

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Create an invoice (Priority: P1)

Billing staff open a patient's billable context (an encounter or
appointment), select approved chargeable services, and the system creates
an invoice with line items and a calculated total. The invoice states what
is owed; no money has moved yet.

**Why this priority**: The invoice is the record everything else hangs
off. Without it there is nothing to pay against, no balance to track, and
no financial history. This is Master Plan §6 M09 and §8 FR-016.

**Independent Test**: With a synthetic patient, an encounter/appointment,
and approved services in the catalog, Billing staff can create an invoice
whose line items and total match the selected services, and the invoice
starts in state Unpaid with balance equal to its total. No payment feature
needs to exist for this to be demonstrated.

**Acceptance Scenarios**:

1. **Given** a signed-in Billing user and approved chargeable services,
   **When** they create an invoice for a patient from those services,
   **Then** an invoice is created with one line item per selected service,
   each showing service, quantity, unit price, and line total, a subtotal
   equal to the sum of the line totals, a total equal to the subtotal (no
   discount/tax rule is defined in v1), state Unpaid, and created-by /
   created-at audit fields.
2. **Given** an invoice-creation form with a missing required field (e.g.
   no patient, no line items),
   **When** they submit it,
   **Then** no invoice is created and a field-level error names the
   missing field.
3. **Given** a service whose catalog price changed after an earlier invoice
   was created,
   **When** the earlier invoice is viewed,
   **Then** its line-item prices are unchanged — prices are fixed on the
   invoice at creation time, so later catalog changes never rewrite
   history.
4. **Given** a signed-in Doctor or Receptionist,
   **When** they try to create an invoice,
   **Then** the action is denied by the backend with a permission error,
   not just hidden in the UI.

### User Story 2 — Record a payment (Priority: P1)

A cashier records money received against an invoice: amount, method, date,
and receipt reference. The system updates the outstanding balance and the
invoice state. A payment is a separate record from the invoice; an invoice
may receive more than one payment.

**Why this priority**: Recording payment is the other half of WF-04 and
FR-017. An invoice without payments is only a statement of what is owed.

**Independent Test**: Against a synthetic Unpaid invoice, a cashier can
record a payment and see the balance fall and the state change; recording
payments totalling the full amount moves the invoice to Paid.

**Acceptance Scenarios**:

1. **Given** an Unpaid invoice with total 5,000,
   **When** a cashier records a payment of 2,000 with method, date, and
   receipt reference,
   **Then** a separate Payment record is created, the outstanding balance
   becomes 3,000, and the invoice state becomes Partially paid.
2. **Given** a Partially paid invoice with 3,000 outstanding,
   **When** a cashier records a further payment of 3,000,
   **Then** the balance becomes 0 and the invoice state becomes Paid.
3. **Given** an invoice with 3,000 outstanding,
   **When** a cashier tries to record a payment of 3,001,
   **Then** the payment is rejected with an understandable error and no
   Payment record is created — overpayment is not permitted.
4. **Given** a payment form with a missing required field (amount, method,
   date, or receipt reference),
   **When** they submit it,
   **Then** no Payment record is created and a field-level error names the
   missing field.
5. **Given** a payment with a date in the future,
   **When** they submit it,
   **Then** the payment is rejected — a payment cannot be dated after
   today (Asia/Karachi).

### User Story 3 — View an invoice and its transaction history (Priority: P2)

Billing staff and Admin view an invoice with its line items, every payment
against it, the outstanding balance, and the history of state changes. The
history is the audit trail for the money.

**Why this priority**: Traceability is a constitution requirement for
financial transactions (Principle IV) and Master Plan FR-020/FR-022. A
balance nobody can explain is not a working billing system.

**Independent Test**: An invoice with two payments and a state change shows
line items, both payments, the balance, and a chronological history of
every change with actor and timestamp.

**Acceptance Scenarios**:

1. **Given** an invoice with payments recorded,
   **When** Billing staff view it,
   **Then** they see line items, each payment (amount, method, date,
   receipt reference, recorded-by), the outstanding balance, and the
   state-change history in chronological order.
2. **Given** an invoice exists,
   **When** a Doctor views billing data,
   **Then** they cannot see the invoice — Billing data is not part of
   clinical access, and the backend denies it.
3. **Given** an invoice exists,
   **When** Billing staff view the linked patient,
   **Then** they see only the minimum identifiers needed for the task
   (name and MRN) — no CNIC / B-Form number, no clinical notes (see
   Permissions).

### User Story 4 — Void or refund an invoice (Priority: P2)

When an invoice is wrong, it is corrected through an approved, audited
process — never by editing the invoice's line items or deleting the record.
An unpaid invoice is voided and reissued; a paid invoice is refunded.

**Why this priority**: WF-04 step 6 requires corrections/refunds to follow
an approved, audited process, and the constitution forbids unsafe
destructive changes to financial history (Principle IV, Master Plan §9.1).
Silent edits would destroy the audit trail.

**Independent Test**: Voiding an Unpaid invoice leaves the voided invoice
visible with state Voided and a recorded reason; refunding a Paid invoice
leaves the invoice and its payments visible with state Refunded and a
recorded reason. In neither case is any record deleted or any line item
edited.

**Acceptance Scenarios**:

1. **Given** an Unpaid invoice created in error,
   **When** an authorised user voids it with a written reason,
   **Then** the invoice state becomes Voided, the reason, actor, and
   timestamp are recorded, and the invoice and its history remain
   visible — nothing is deleted.
2. **Given** a Voided invoice,
   **When** a cashier tries to record a payment against it,
   **Then** the payment is rejected — a voided invoice cannot accept
   payments.
3. **Given** a Paid invoice,
   **When** an authorised user tries to void it,
   **Then** the void is refused — an invoice with payments recorded
   cannot be voided; it must go through the refund process.
4. **Given** a Paid invoice,
   **When** an authorised user processes a refund with a written reason,
   **Then** the invoice state becomes Refunded, the refund (amount,
   method, date, reference, actor) is recorded as a transaction against
   the invoice, and the full history remains visible.
5. **Given** any invoice,
   **When** an authorised user tries to edit its line items or total
   directly,
   **Then** the edit is refused — a finalised invoice's line items are
   immutable; the correction path is void-and-reissue (if unpaid) or
   refund (if paid).

### Edge Cases

- What happens when two payments are recorded against the same invoice at
  the same time and together exceed the balance? The balance check and the
  state update run in one database transaction; the second payment is
  rejected if the balance it would exceed has already been taken.
- What happens when a payment is recorded against an invoice whose patient
  record is Inactive, Merged, or Archived? The invoice is still payable —
  the patient status governs registration, not money already owed. The
  payment is recorded normally; creating a *new* invoice for a Merged or
  Archived patient is refused (the active record must be used instead).
- What happens when the service catalog price changes? Nothing, for
  existing invoices: line-item prices are fixed at invoice creation (see
  User Story 1, scenario 3). New invoices use the current catalog price.
- What happens when an invoice total is zero (e.g. all line items are
  zero-priced services)? A zero-total invoice is created in state Paid
  with balance 0 — it is owed nothing, so no payment is needed. (If the
  owner instead wants zero-total invoices to be impossible, that is
  OQ-008-12.)
- What happens when a payment's receipt reference duplicates an existing
  one? Receipt references are unique; the duplicate is rejected with an
  understandable error.
- What happens when a cashier tries to record a payment of zero or a
  negative amount? Rejected by backend validation.
- What happens when an invoice is partially paid and then voided? It
  cannot be voided — an invoice with any payment recorded must go through
  refund (see User Story 4, scenario 3). How a *partial* refund is handled
  is not defined in v1 (OQ-008-8).
- What happens when a payment is recorded with a backdated date? Not
  decided in this spec — see OQ-008-11.
- What happens when billing staff search for a patient? They cannot
  free-text search patients in v1 (Spec 001 permissions; Nurse / Lab /
  Pharmacist / Billing have no patient search in v1). Billing reaches a
  patient only through a linked appointment, encounter, or invoice, seeing
  name and MRN only.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow authorised Billing staff to create an
  invoice from approved charge items (Master Plan FR-016, §6 M09, WF-04
  steps 1–2). Charge items come from the approved service catalog (M02);
  an invoice MUST NOT be created from free-text amounts with no catalog
  item behind them.
- **FR-002**: Each invoice line item MUST record the service, quantity,
  unit price, and line total. Unit prices MUST be fixed on the invoice at
  creation time (snapshot); later catalog price changes MUST NOT alter an
  existing invoice.
- **FR-003**: All money arithmetic MUST be decimal-safe: Python `Decimal`
  and PostgreSQL `NUMERIC`/`DECIMAL`, never binary floating point
  (Master Plan §9.1). Subtotal MUST equal the exact sum of line totals.
  Discount and tax MUST be calculated only if defined — no discount or tax
  rule is defined in v1, so the invoice total MUST equal the subtotal and
  no discount/tax line may appear. Amounts are stored to two decimal
  places.
- **FR-004**: Every invoice MUST have a unique system-generated invoice
  number, a link to exactly one patient (by MRN), an optional link to the
  originating appointment and/or encounter, a state, a total, an
  outstanding balance, and created-by / created-at audit fields. Staff
  MUST NOT type the invoice number by hand. (Number format: OQ-008-2.)
- **FR-005**: Payments MUST be records separate from invoices (Master Plan
  FR-017, §7.1). Each payment MUST record amount, method, date, receipt
  reference, the invoice it pays, and recorded-by / recorded-at audit
  fields. One invoice MAY receive more than one payment.
- **FR-006**: The outstanding balance MUST equal total minus the sum of
  payments recorded against the invoice, and MUST be maintained in the
  same database transaction as each payment. Invoice state MUST follow
  the balance: no payments → Unpaid; some but not all paid → Partially
  paid; balance zero after at least one payment (or a zero total) → Paid.
- **FR-007**: The system MUST reject any payment that would make total
  payments exceed the invoice total (no overpayment). The check MUST run
  on the backend, inside the payment transaction, not only in the UI.
- **FR-008**: Invoice states MUST be exactly Unpaid / Partially paid /
  Paid / Voided / Refunded, as an explicit enum with enforced
  transitions: Unpaid → Partially paid → Paid; Unpaid → Voided; Paid →
  Refunded. No other transition is permitted. In particular, an invoice
  with any payment recorded MUST NOT be voided, and a Voided or Refunded
  invoice MUST NOT accept payments.
- **FR-009**: A finalised invoice's line items and total MUST be
  immutable. Corrections MUST go through void-and-reissue (Unpaid
  invoice) or refund (Paid invoice), each with a written reason recorded.
  (Refund approver and partial-refund handling: OQ-008-8.)
- **FR-010**: The system MUST retain the full transaction history:
  invoices, line items, payments, voids, and refunds MUST NOT be
  hard-deleted. Every state change MUST record actor, timestamp, and
  reason where a reason is required (Master Plan FR-022, Constitution
  Principle IV).
- **FR-011**: The system MUST enforce permissions on the backend: Billing
  creates invoices and records payments; Admin has oversight access (see
  Permissions); Doctor, Nurse, Lab Technician, and Pharmacist have no
  billing access; Receptionist has no billing access in v1.
- **FR-012**: Billing access to patient identity MUST be the minimum
  needed: Billing reaches a patient only via a linked appointment,
  encounter, or invoice, and sees name and MRN only. Billing MUST NOT
  see the patient's CNIC / B-Form number (encrypted, Receptionist/Admin
  only — Spec 001 D-07/D-12) or clinical notes, and MUST NOT free-text
  search patients in v1.
- **FR-013**: The system MUST validate all billing input on the backend
  before saving (Master Plan FR-021): amounts are positive decimals with
  at most two decimal places; quantity is a positive integer; payment
  date is not in the future; receipt reference is present and unique.
  The frontend MUST show field-level errors.
- **FR-014**: The system MUST record audit events for invoice creation,
  payment recording, void, and refund (actor, action, target, timestamp,
  outcome) (Master Plan FR-020). Audit records MUST NOT contain
  passwords, tokens, or clinical content.
- **FR-015**: The system MUST reject unauthenticated access to all billing
  endpoints, and MUST return understandable errors without exposing
  secrets, stack traces, or unnecessary patient data (Master Plan FR-023).

### Key Entities

- **Invoice**: What is owed. Key attributes: invoice number (unique,
  system-generated), patient (link by MRN; patient fields name/DOB/phone/
  gender/CNIC-B-Form per Spec 001 — Billing sees name and MRN only),
  originating appointment and/or encounter (optional link), state
  (Unpaid / Partially paid / Paid / Voided / Refunded), subtotal, total,
  outstanding balance, created-by, created-at, updated-at. See "Data
  fields".
- **InvoiceLineItem**: One charge on an invoice. Key attributes: invoice,
  service (reference to the approved service-catalog item), description,
  quantity, unit price (snapshot at creation), line total. Prices are
  `Decimal`, never float.
- **Payment**: Money received. Key attributes: invoice, amount
  (`Decimal`), method, date, receipt reference (unique), recorded-by,
  recorded-at. Separate from the invoice by design (Master Plan §7.1).
- **Refund**: Money returned against a Paid invoice. Key attributes:
  invoice, amount, method, date, reference, reason, processed-by,
  processed-at. A full refund moves the invoice to Refunded; partial
  refunds are not defined in v1 (OQ-008-8).
- **AuditEvent**: Who did what, when, to which invoice/payment, and
  whether it succeeded (shared `audit` app; see Spec 001 data-model.md).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Billing staff can create an invoice from approved services
  in a single flow, and its subtotal and total equal the exact sum of its
  line items with no floating-point error (verified by a test that sums
  amounts known to expose binary-float error, e.g. 0.1 + 0.2 cases).
- **SC-002**: Recording payments totalling the invoice amount moves the
  invoice to Paid with balance exactly 0; a lesser total leaves it
  Partially paid with the exact remaining balance.
- **SC-003**: 100% of attempted overpayments in test data are rejected by
  the backend with no Payment record created.
- **SC-004**: Every invoice creation, payment, void, and refund in test
  data has a corresponding audit event with actor and timestamp, and no
  voided/refunded invoice or payment is hard-deleted.
- **SC-005**: A Doctor or Receptionist attempting any billing mutation is
  denied by the backend (not merely by a hidden button) in automated
  permission tests.
- **SC-006**: All P1 acceptance scenarios above pass against the
  implemented feature before it is considered complete — once this spec
  is approved and the owner has made the priority call.

## Permissions

| Role | Create invoice | Record payment | View invoices / payments | Void invoice | Refund invoice | Patient search |
|---|---|---|---|---|---|---|
| Admin | Yes | Yes | Yes | Yes | To be confirmed — see OQ-008-8 (recommended: Admin-only) | Yes (per Spec 001) |
| Billing / Cashier | Yes | Yes | Yes | Yes (Unpaid only, with reason) | No — approver to be confirmed, OQ-008-8 | No in v1 (see FR-012) |
| Receptionist | No | No | No | No | No | Yes (per Spec 001) |
| Doctor / Clinician | No | No | No | No | No | Yes, read-only (per Spec 001) |
| Nurse | No | No | No | No | No | No in v1 |
| Lab Technician | No | No | No | No | No | No in v1 |
| Pharmacist | No | No | No | No | No | No in v1 |

Billing Staff / Cashier is a single role in v1, matching Master Plan §5
("Billing Staff / Cashier — prepare invoices, record payments, issue
receipts and view balances"). Whether invoice creation and payment
recording should be split between two people (separation of duties,
Master Plan §5.2) is OQ-008-9. Admin's void/refund powers above are the
spec's working assumption for the void of an Unpaid invoice; the refund
approver is genuinely undecided and is an Open Question, not a decision.

## Data fields

- **Invoice**: invoice number (system-generated, unique; format OQ-008-2),
  patient (required, by MRN), appointment (optional link), encounter
  (optional link), state (Unpaid / Partially paid / Paid / Voided /
  Refunded), subtotal (`Decimal`, 2dp), discount total (`Decimal`, 2dp —
  always 0 in v1, no rule defined), tax total (`Decimal`, 2dp — always 0
  in v1, no rule defined), total (`Decimal`, 2dp), outstanding balance
  (`Decimal`, 2dp), created-by, created-at, updated-at.
- **InvoiceLineItem**: service (required, reference to approved
  service-catalog item), description (as on the invoice), quantity
  (positive integer), unit price (`Decimal`, 2dp, snapshot at creation),
  line total (`Decimal`, 2dp = quantity × unit price).
- **Payment**: invoice (required), amount (`Decimal`, 2dp, positive),
  method (required; allowed values OQ-008-4), date (required, not in the
  future), receipt reference (required, unique; format OQ-008-3),
  recorded-by, recorded-at.
- **Refund**: invoice (required), amount (`Decimal`, 2dp, positive), method
  (required), date (required), reference (required, unique), reason
  (required free text), processed-by, processed-at.
- **Currency**: amounts are stored as `Decimal` in the hospital's billing
  currency. The currency itself is not stated in the Master Plan and is
  OQ-008-1 (expected: PKR — to be confirmed, not assumed).

## Assumptions

- The hospital is a single organisation; one deployment instance (Master
  Plan §2.4).
- Authentication and RBAC (M01), hospital setup with the service catalog
  (M02), patient registration (M03, Spec 001), and appointments (M04) and
  encounters (M05) exist before or alongside this feature; billing
  endpoints assume a signed-in user with a role, approved services to
  charge from, and a patient/encounter to bill. If the service catalog
  does not exist, invoices cannot be created from approved items (FR-001)
  and this feature cannot be demonstrated.
- All demo/test data is synthetic; no real patient or financial records
  are used. No real money moves in the system: payments recorded here are
  records of money received offline (e.g. cash at the counter), not a
  payment-gateway settlement.
- Display timezone for dates/times is Asia/Karachi; timestamps are stored
  in UTC and displayed in Asia/Karachi (ADR-001).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner
  (2026-11-22); Python 3.12 / Node 20 LTS.
- Patient identity rules are inherited from Spec 001 and are not
  re-decided here: MRN `MC-YYYY-NNNNNN`; required patient fields name /
  DOB / phone / gender / CNIC-B-Form; blood group optional; patient
  statuses Active / Inactive / Merged / Archived; CNIC encrypted at rest,
  full view only Receptionist/Admin, masked otherwise, never searchable;
  Nurse / Lab / Pharmacist / Billing have no patient search in v1.

## Decisions

No decisions were delegated for this spec and none are taken here. The
rules below are **inherited, not re-decided** — they come from the Master
Plan, the constitution, ADR-001, or Spec 001, and changing one requires a
change to its source, not to this spec.

- **Inherited — decimal-safe money (Master Plan §9.1)**: use decimal-safe
  numeric types for money; do not use floating-point arithmetic for
  invoice totals.
- **Inherited — invoice vs. payment are separate records (Master Plan
  §7.1, WF-04)**: an invoice states what is owed; a payment records
  money received. An invoice may be unpaid, partially paid, or fully paid.
- **Inherited — invoice states (Master Plan §6 M09)**: unpaid, partially
  paid, paid, voided/refunded, as policy permits; overpayment and invalid
  transitions prevented; transaction history retained.
- **Inherited — corrections are audited, not silent (Master Plan §9.1,
  Constitution Principle IV)**: no hard deletion of important financial
  history; correction, cancellation, and archival rules defined per
  feature.
- **Inherited — patient privacy (Spec 001 D-06/D-07/D-12)**: CNIC /
  B-Form encrypted, Receptionist/Admin only, never searchable; Billing
  has no patient search in v1 and sees name + MRN only via a linked
  record.

Everything else about billing is an Open Question below.

## Open Questions

These are genuinely undecided. They must be answered by the owner (with
hospital/discovery input where noted) before or at approval; this spec
does not guess them.

- **OQ-008-1 — RESOLVED 2026-11-22: billing is in scope as its own module
  (M8).** The owner decided Prescription, Billing and Online Payments are
  each separate modules. The old Phase 6 "choose lab OR billing OR
  prescription" pick no longer applies. (Number kept so later OQ
  references do not shift.)
- **OQ-008-2 — Invoice number format.** Required to be unique and
  system-generated (FR-004); the format itself is undecided. Suggested
  pattern mirroring the MRN: `INV-YYYY-NNNNNN` — to be confirmed, not
  assumed.
- **OQ-008-3 — Receipt reference format and receipt content.** Each
  payment needs a receipt reference (FR-005); whether it is
  system-generated sequential, entered by the cashier, or both, and what a
  printed/displayed receipt shows (invoice number, line items, payments,
  balance, hospital name?) is undecided.
- **OQ-008-4 — Currency.** Expected to be PKR (hospital in Pakistan) —
  to be confirmed. Amounts need a currency recorded with them if anything
  other than a single fixed currency is ever possible.
- **OQ-008-5 — Payment methods accepted.** Which methods exist (Cash?
  Card? Bank transfer? Mobile wallet?) and whether each needs extra
  fields (e.g. card/bank reference). Cash at the counter is the only
  method the Master Plan clearly implies; the rest need the owner's call.
- **OQ-008-6 — Discount rules.** Is any discount offered (e.g. staff,
  hardship, package)? Who authorises it, is it a percentage or a fixed
  amount, and is it applied per line or per invoice? No discount may be
  implemented until this is defined (FR-003).
- **OQ-008-7 — Tax rules.** Is any tax applied to invoices, at what rate,
  and is it included in or added to the price? No tax may be implemented
  until this is defined (FR-003).
- **OQ-008-8 — Refund approver and partial refunds.** Who approves a
  refund (recommended: Admin-only, per separation of duties §5.2 — to be
  confirmed)? Is a partial refund possible, and if so what state does the
  invoice end in? Full refund → Refunded is specified; anything partial
  is not.
- **OQ-008-9 — Separation of duties inside Billing.** Should the person
  who creates an invoice be a different person from the one who records
  its payments (Master Plan §5.2)? In v1 the spec treats Billing/Cashier
  as one role; splitting it needs the owner's call.
- **OQ-008-10 — Standalone invoices.** Must every invoice link to an
  appointment or encounter, or may Billing raise an invoice with no
  encounter (e.g. a direct charge)? The appointment/encounter link is
  optional in this spec's data fields pending this answer.
- **OQ-008-11 — Backdated payments.** May a cashier record a payment
  dated before today (e.g. yesterday's cash entered this morning), or
  must the payment date always be today? Future dates are rejected
  (FR-013); past dates are undecided.
- **OQ-008-12 — Zero-total invoices.** This spec treats a zero-total
  invoice as Paid with balance 0 (Edge Cases). If the owner instead wants
  zero-total invoices refused, or free services handled differently, that
  changes FR-006.
- **OQ-008-13 — Who sets service prices and how often may they change?**
  Prices come from the M02 service catalog; who may change a price, and
  whether a price change needs approval or an effective date, belongs to
  the hospital-setup spec — but billing depends on the answer, because it
  fixes which price an invoice snapshots.

## Deferred (not decided here)

- **Insurance claims and real payment settlement**: out of scope per
  Master Plan §4.3 unless explicitly approved.
- **Discount/tax calculation**: deferred until OQ-008-6 / OQ-008-7 are
  answered; the fields exist in the data model at 0 in v1.
- **Partial refunds**: deferred until OQ-008-8 is answered.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1;
  §§19–23 (deployment, risk register, governance/decision log,
  acceptance, open decisions) are listed in the contents but absent from
  the document. Explicitly deferred: they must be supplied or formally
  deferred before release planning (Phase 8), but they do not block this
  feature's specification.
- **Auth/session strategy is decided (Spec 001 D-09, ADR-001)**; no auth
  question is reopened here.
