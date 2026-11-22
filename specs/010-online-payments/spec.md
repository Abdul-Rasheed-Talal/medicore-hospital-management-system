# Feature Specification: Online Payments

**Feature Branch**: `docs/modules-prescription-billing-payments` (spec work; implementation branch to follow)

**Created**: 2026-11-22

**Status**: Draft — **separate module M9, not yet approved by the owner. DO NOT
IMPLEMENT YET.** The owner decided on 2026-11-22 that Prescription, Billing
and Online Payments are each their own separate module because they are
important, and must not be lumped together or deferred as a group. Online
Payments is therefore committed scope in the module plan (M9), but this spec
is a draft: it becomes an implementation instruction only when the owner
answers the Open Questions below (gateway choice first of all) and approves
this spec (Master Plan §4.4 Scope Control Rule).

**Input**: Master Plan v1.0 (22 November 2026, draft planning baseline),
§4.2 P1 Candidate billing, §4.3 out of scope (real payment settlement —
see Decisions: explicitly approved as its own module M9 by the owner on
2026-11-22), §5 Billing Staff / Cashier, §6 M09, §7 WF-04, §7.1 invoice
vs. payment, §8 FR-016 / FR-017 / FR-020 / FR-021 / FR-022 / FR-023 /
FR-024, §9 NFR-01–05 and §9.1 (decimal-safe money), §10.4 `billing` app
boundary, §16, §17 Phase 6; MediCore Constitution v1.0.0, Principles I,
III, IV, V, VI, VII, VIII; Spec 001 Patient Registration (patient
identity, MRN, permissions baseline); Spec 002 Auth & RBAC (session auth,
roles); Spec 008 Billing and Payments (invoices, offline payment
recording, void/refund — this spec's prerequisite).

## Overview

### Problem

Spec 008 records money that was already received offline (cash at the
counter) — it states what is owed and records what arrived, but it cannot
collect money. A patient who is not standing at the counter has no way to
pay, so the invoice stays Unpaid even when the patient is willing and able
to pay from elsewhere. Online Payments closes that gap: Billing initiates
an online payment against an existing invoice, the patient pays through a
payment gateway outside MediCore (a payment link or reference the hospital
shares with them), and the gateway tells MediCore what happened through a
callback/webhook. MediCore then reconciles the result — a successful
payment becomes a Payment record under Spec 008, in the same transaction
that updates the invoice balance and state; a failed or timed-out payment
leaves the invoice exactly as it was.

This spec is deliberately narrow: initiate an online payment, receive and
verify the gateway's result, reconcile it against the invoice, and audit
every step. It does not include a patient portal or patient self-service
(no patient touches this flow in v1 — Billing initiates, the patient only
pays on the gateway's own page), it does not choose a payment gateway, and
it does not invent fees, settlement timelines, or regulatory claims (see
Open Questions).

### Scope

**In scope**

- Initiate an online payment against an Unpaid or Partially paid invoice,
  for an amount up to the outstanding balance, and record it as an
  `OnlinePayment` in state Initiated with a gateway reference (FR-001)
- Produce a payment reference / link for the patient to pay on the
  gateway's page (the gateway owns the payment page, not MediCore)
- Receive the gateway's result via callback/webhook, verify it (signature
  / secret check), and reconcile it: success → create a Spec 008 Payment
  record and update invoice balance + state in one transaction; failure →
  mark the online payment Failed and leave the invoice unchanged;
  timeout/expiry → mark it Expired (FR-002, FR-003)
- Handle duplicate, late, and out-of-order gateway notifications
  idempotently — the same gateway event must never create two Payment
  records (FR-004)
- Track online-payment states Initiated / Paid / Failed / Refunded /
  Expired with actor and timestamp history; refund of an online payment
  follows the Spec 008 refund process and updates the online-payment
  state (FR-005)
- Audit every initiation, callback, reconciliation, failure, and refund
  (Master Plan FR-020)

**Out of scope**

- Choosing the payment gateway — decided in OQ-010-1 (Easypaisa, JazzCash,
  bank transfer as primary; Stripe as the card option). Per-gateway
  integration details are confirmed at implementation time.
- A patient portal, patient accounts, or patient self-service payment
  (Master Plan §6 M13 — future module, not in v1)
- Storing or handling card numbers, PINs, CVVs, or any cardholder data —
  MediCore never sees them; they live only on the gateway's page
- Real money in development, testing, or demonstrations: sandbox / test
  mode only, with synthetic invoices (see Assumptions)
- Insurance claim submission, banking integrations beyond the chosen
  gateway, and tax/discount rules (Spec 008 OQ-008-6 / OQ-008-7)
- Fees, settlement timelines, and regulatory claims — none are stated
  here, because none are known (see Open Questions)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Initiate an online payment (Priority: P1)

Billing staff open an Unpaid or Partially paid invoice and initiate an
online payment for an amount up to the outstanding balance. The system
creates an `OnlinePayment` in state Initiated with a gateway reference and
a payment link/reference to share with the patient. No money has moved
yet; the invoice is unchanged.

**Why this priority**: Initiation is the record everything else hangs
off. Without it there is no payment to reconcile, no gateway event to
match, and no audit trail for the money's journey.

**Independent Test**: Against a synthetic Partially paid invoice with
3,000 outstanding, Billing can initiate an online payment of 2,000 and
see an Initiated `OnlinePayment` with a gateway reference, while the
invoice stays Partially paid with balance 3,000. No gateway needs to
exist for this to be demonstrated (the gateway call is stubbed in test).

**Acceptance Scenarios**:

1. **Given** a signed-in Billing user and an invoice with 3,000
   outstanding,
   **When** they initiate an online payment of 2,000,
   **Then** an `OnlinePayment` is created in state Initiated with the
   invoice, amount 2,000, currency PKR (working assumption — see
   OQ-010-9), a unique gateway reference, initiated-by and initiated-at,
   and a payment link/reference is returned; the invoice balance and
   state are unchanged.
2. **Given** an invoice with 3,000 outstanding,
   **When** Billing tries to initiate an online payment of 3,001,
   **Then** the initiation is rejected with an understandable error and
   no `OnlinePayment` is created — an online payment may not exceed the
   outstanding balance (same rule as Spec 008 FR-007).
3. **Given** an invoice with 0 outstanding (Paid),
   **When** Billing tries to initiate an online payment against it,
   **Then** the initiation is rejected — a paid invoice needs no payment.
4. **Given** a Voided or Refunded invoice,
   **When** Billing tries to initiate an online payment against it,
   **Then** the initiation is rejected — voided/refunded invoices cannot
   accept payments (Spec 008 FR-008).
5. **Given** a signed-in Doctor or Receptionist,
   **When** they try to initiate an online payment,
   **Then** the action is denied by the backend with a permission error,
   not just hidden in the UI.

### User Story 2 — Reconcile a successful gateway payment (Priority: P1)

The patient pays on the gateway's page. The gateway calls MediCore's
callback/webhook with the result. MediCore verifies the notification,
matches it to the `OnlinePayment`, and — in one database transaction —
creates a Spec 008 Payment record, marks the online payment Paid, and
updates the invoice balance and state.

**Why this priority**: Reconciliation is the point of the module. An
initiated payment that never becomes a Payment record is money the
hospital cannot account for; a reconciliation that runs twice is money
counted twice.

**Independent Test**: With a stubbed gateway, an Initiated online payment
of 2,000 against a 3,000-balance invoice, on a verified success callback,
produces exactly one Payment record of 2,000, the online payment in state
Paid, and the invoice at balance 1,000 (still Partially paid).

**Acceptance Scenarios**:

1. **Given** an Initiated online payment of 2,000 against an invoice with
   3,000 outstanding,
   **When** a verified gateway success callback arrives for it,
   **Then** one Payment record is created (amount 2,000, method Online,
   receipt reference from the gateway reference, recorded-by = system /
   gateway), the `OnlinePayment` becomes Paid with paid-at, and the
   invoice balance becomes 1,000 and stays Partially paid — all in one
   transaction.
2. **Given** an Initiated online payment that would complete the invoice,
   **When** a verified success callback arrives,
   **Then** the invoice balance becomes 0 and its state becomes Paid.
3. **Given** a success callback,
   **When** its signature / secret verification fails,
   **Then** the callback is rejected (HTTP 401/403), nothing is recorded,
   and the failure is logged as a security event — an unverified callback
   must never move money.
4. **Given** a success callback for an `OnlinePayment` that is already
   Paid,
   **When** the same gateway event arrives a second time (duplicate
   delivery),
   **Then** it is recognised by its gateway event id, ignored, and no
   second Payment record is created.
5. **Given** a callback that names an unknown gateway reference,
   **When** it arrives,
   **Then** it is rejected with an understandable error, logged, and no
   invoice is touched.

### User Story 3 — Handle a failed or expired payment (Priority: P2)

A payment can fail at the gateway (declined, cancelled by the patient) or
simply never be completed. The gateway's failure callback, or the expiry
of the payment link, marks the online payment Failed or Expired. The
invoice is untouched — the patient may try again with a new initiation.

**Why this priority**: Failure is the normal case, not the exception.
If a failed payment left the invoice in a half-paid state, or blocked
re-initiation, Billing would have to fix it by hand for every declined
card.

**Independent Test**: An Initiated online payment that receives a failure
callback ends in state Failed with a failure reason, the invoice is
unchanged, and Billing can initiate a new online payment against the same
invoice.

**Acceptance Scenarios**:

1. **Given** an Initiated online payment,
   **When** a verified gateway failure callback arrives with a reason,
   **Then** the `OnlinePayment` becomes Failed with the failure reason
   recorded, and the invoice balance and state are unchanged.
2. **Given** an Initiated online payment whose link has expired (expiry
   duration: OQ-010-5),
   **When** the expiry is detected (by a scheduled check or a late
   callback),
   **Then** the `OnlinePayment` becomes Expired and the invoice is
   unchanged.
3. **Given** a Failed or Expired online payment,
   **When** Billing initiates a new online payment against the same
   invoice,
   **Then** it succeeds as a new, separate `OnlinePayment` — a failed
   attempt never blocks a retry.
4. **Given** a success callback that arrives after the payment was
   already marked Expired,
   **When** it is processed,
   **Then** it is handled by the reconciliation rule for late arrivals
   (see Edge Cases): the payment is still reconciled if the gateway
   confirms the money was taken, and the late arrival is audit-logged —
   an Expired state must not silently swallow real money.

### Edge Cases

- What happens when two callbacks for the same payment arrive at the
  same time? The reconciliation runs in one database transaction with
  row locking on the `OnlinePayment`; the first creates the Payment
  record, the second sees it is already Paid and is ignored.
- What happens when a success callback arrives for an amount different
  from the initiated amount? The callback is rejected and logged; no
  Payment record is created. An amount mismatch is never silently
  accepted — it must be investigated, not auto-corrected.
- What happens when the gateway is unreachable at initiation time? The
  initiation fails with an understandable error and no `OnlinePayment`
  is created (or it is created in a failed state — the choice is an
  implementation detail, but it must be recorded and consistent).
- What happens when a success callback arrives after the payment was
  marked Expired? See User Story 3, scenario 4: reconcile it if the
  gateway confirms money was taken, and audit-log the late arrival.
- What happens when a refund is needed for an online payment? The Spec
  008 refund process applies: the refund is recorded against the
  invoice, and the `OnlinePayment` becomes Refunded — but only once the
  gateway confirms the refund (OQ-010-4: whether the gateway's refund
  API is used, or the refund is manual and reconciled by hand).
- What happens when the gateway sends a callback for a payment MediCore
  never initiated? Rejected and logged (User Story 2, scenario 5) —
  unknown references never touch an invoice.
- What happens when Billing initiates an online payment and the patient
  pays by cash instead? The online payment stays Initiated until it
  expires; the cash payment is recorded separately under Spec 008. The
  two records never merge, and the expired online payment is never
  reconciled.
- What happens when the gateway's sandbox/test mode is used? All
  development and demonstration payments are sandbox only; no real
  money, no real card data, no production credentials in the repository
  or in test data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow authorised Billing staff to initiate
  an online payment against an Unpaid or Partially paid invoice, for a
  positive amount up to the outstanding balance, and MUST record it as
  an `OnlinePayment` in state Initiated with a unique gateway reference
  (Master Plan FR-017, §7 WF-04).
- **FR-002**: The system MUST receive the gateway's result through a
  callback/webhook endpoint, MUST verify the notification (signature /
  secret, per the chosen gateway's mechanism — OQ-010-1), and MUST
  reject unverified callbacks without recording anything.
- **FR-003**: On a verified success callback, the system MUST, in one
  database transaction: create a Spec 008 Payment record (amount,
  method Online, receipt reference from the gateway reference), mark
  the `OnlinePayment` Paid, and update the invoice balance and state
  (Spec 008 FR-006). The transaction MUST fail as a whole if any part
  fails.
- **FR-004**: The system MUST process each gateway event at most once:
  a gateway event id MUST be stored and checked, so a duplicate,
  retried, or out-of-order delivery can never create a second Payment
  record for the same payment.
- **FR-005**: Online-payment states MUST be exactly Initiated / Paid /
  Failed / Refunded / Expired, as an explicit enum with enforced
  transitions: Initiated → Paid; Initiated → Failed; Initiated →
  Expired; Paid → Refunded. No other transition is permitted.
- **FR-006**: On a verified failure callback, or on expiry, the system
  MUST mark the `OnlinePayment` Failed or Expired with the reason
  recorded, and MUST leave the invoice balance and state unchanged.
- **FR-007**: The system MUST reject an initiation that would exceed the
  invoice's outstanding balance, or that targets a Paid, Voided, or
  Refunded invoice, with an understandable error and no record created
  (same rule as Spec 008 FR-007/FR-008).
- **FR-008**: The system MUST enforce permissions on the backend: only
  Billing and Admin may initiate or view online payments; Doctor, Nurse,
  Lab Technician, Pharmacist, and Receptionist have no online-payment
  access; patients have no access at all in v1 (no patient portal).
- **FR-009**: All money MUST be decimal-safe: Python `Decimal` and
  PostgreSQL `NUMERIC`, never binary floating point (Master Plan §9.1);
  amounts are stored to two decimal places; money is serialised as
  decimal strings in JSON.
- **FR-010**: The system MUST record audit events for initiation,
  callback receipt, reconciliation, failure, expiry, and refund (actor,
  action, target, timestamp, outcome) (Master Plan FR-020). Audit
  records MUST NOT contain card data, gateway secrets, or full gateway
  payloads — only the gateway reference, event id, amount, and outcome.
- **FR-011**: The system MUST validate all input on the backend before
  saving (Master Plan FR-021): amount is a positive decimal with at
  most two decimal places and does not exceed the balance; the gateway
  reference is present and unique; callback payloads are checked
  against the initiated record before any reconciliation.
- **FR-012**: The system MUST reject unauthenticated access to all
  online-payment endpoints, and MUST return understandable errors
  without exposing secrets, stack traces, gateway credentials, or
  unnecessary patient data (Master Plan FR-023).
- **FR-013**: No real money may move in development, testing, or
  demonstration: the gateway MUST be in sandbox / test mode outside
  production, and production credentials MUST come from environment
  variables only, never from source control or test data.
- **FR-014**: The system MUST never store, log, or display card numbers,
  PINs, CVVs, or any other cardholder data. The gateway owns the
  payment page; MediCore stores only the gateway reference, event id,
  amount, status, and outcome.

### Key Entities

- **OnlinePayment**: The online attempt against one invoice. Key
  attributes: gateway reference (unique, system-generated), invoice
  (link), amount (`Decimal`), currency (PKR — working assumption,
  OQ-010-9), gateway (name of the chosen gateway — OQ-010-1), status
  (Initiated / Paid / Failed / Refunded / Expired), gateway event id
  (for idempotency), failure reason (when Failed), initiated-by,
  initiated-at, paid-at, created-at, updated-at. See "Data fields".
- **Payment** (Spec 008): Money received. An online success creates a
  Payment record with method Online — the invoice's balance and state
  are updated by that Payment record, exactly as for a cash payment.
  Online Payments and Payments are separate entities by design: one is
  the attempt, the other is the money.
- **Invoice** (Spec 008): What is owed. Online Payments never change an
  invoice directly — only a reconciled Payment record does.
- **AuditEvent**: Who did what, when, to which online payment/invoice,
  and whether it succeeded (shared `audit` app; see Spec 001
  data-model.md).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Billing can initiate an online payment against a synthetic
  invoice and receive an Initiated record with a unique gateway
  reference, while the invoice balance and state are unchanged.
- **SC-002**: A verified success callback produces exactly one Payment
  record, the online payment in state Paid, and the correct invoice
  balance and state — verified by a test that delivers the same callback
  twice and asserts only one Payment record exists.
- **SC-003**: 100% of unverified callbacks in test data are rejected
  with no record created and a security event logged.
- **SC-004**: 100% of over-balance initiations and initiations against
  Paid/Voided/Refunded invoices in test data are rejected with no
  `OnlinePayment` created.
- **SC-005**: A failed or expired online payment leaves the invoice
  unchanged, and a new initiation against the same invoice succeeds.
- **SC-006**: All P1 acceptance scenarios above pass against the
  implemented feature before it is considered complete — once this spec
  is approved and the owner has chosen a gateway.

## Permissions

| Role | Initiate online payment | View online payments | Reconcile (callback) | Refund online payment | Patient search |
|---|---|---|---|---|---|
| Admin | Yes | Yes | System (gateway) | Yes (per Spec 008 refund approver) | Yes (per Spec 001) |
| Billing / Cashier | Yes | Yes | System (gateway) | No — approver to be confirmed, Spec 008 OQ-008-8 | No in v1 |
| Receptionist | No | No | No | No | Yes (per Spec 001) |
| Doctor / Clinician | No | No | No | No | Yes, read-only (per Spec 001) |
| Nurse | No | No | No | No | No in v1 |
| Lab Technician | No | No | No | No | No in v1 |
| Pharmacist | No | No | No | No | No in v1 |

Reconciliation is not a human action: only the gateway's verified
callback may move an `OnlinePayment` from Initiated to Paid or Failed.
No staff role may mark an online payment Paid by hand — that would let
money be invented without the gateway. Billing's access to patient
identity is the minimum needed (name and MRN only, via the linked
invoice; no CNIC, no clinical notes — Spec 001 D-06/D-07/D-12).

## Data fields

- **OnlinePayment**: gateway reference (system-generated, unique;
  format decided with the gateway, OQ-010-1), invoice (required),
  amount (`Decimal`, 2dp, positive, ≤ outstanding balance at
  initiation), currency (PKR — working assumption, OQ-010-9), gateway
  (required; name of the chosen gateway — OQ-010-1), status (Initiated
  / Paid / Failed / Refunded / Expired), gateway event id (required on
  callback, unique, for idempotency), failure reason (free text, when
  Failed), payment link/reference (returned at initiation, for sharing
  with the patient), initiated-by, initiated-at, paid-at (when Paid),
  created-at, updated-at.
- **Payment** (Spec 008, created by reconciliation): invoice
  (required), amount (`Decimal`, 2dp), method Online, date (from the
  gateway's paid timestamp, Asia/Karachi), receipt reference (from the
  gateway reference, unique), recorded-by (system/gateway), recorded-at.
- **Currency**: amounts are stored as `Decimal` in the hospital's
  billing currency. The currency is the working assumption PKR — to be
  confirmed (OQ-010-9), not assumed.

## Assumptions

- The hospital is a single organisation; one deployment instance (Master
  Plan §2.4).
- Spec 008 Billing exists before or alongside this feature: online
  payments are reconciled into Spec 008 Payment records, and the invoice
  balance/state rules are Spec 008's, not re-decided here. Without an
  invoice there is nothing to pay against, so this feature cannot be
  demonstrated alone.
- Authentication and RBAC (M01), hospital setup (M02), and patient
  registration (M03, Spec 001) exist; online-payment endpoints assume a
  signed-in Billing/Admin user.
- All demo/test data is synthetic; no real patient or financial records
  are used. No real money moves in development or demonstration: the
  gateway is in sandbox / test mode, and production credentials are
  environment variables only.
- The gateway owns the payment page: the patient enters payment details
  on the gateway's page, never in MediCore. MediCore never sees, stores,
  or logs card data.
- Display timezone for dates/times is Asia/Karachi; timestamps are
  stored in UTC and displayed in Asia/Karachi (ADR-001).
- The stack in `docs/adr/001-stack.md` is ACCEPTED by the owner
  (2026-11-22); Python 3.12 / Node 20 LTS.
- Patient identity rules are inherited from Spec 001 and are not
  re-decided here: MRN `MC-YYYY-NNNNNN`; required patient fields name /
  DOB / phone / gender / CNIC-B-Form; blood group optional; patient
  statuses Active / Inactive / Merged / Archived; CNIC encrypted at rest,
  full view only Receptionist/Admin, masked otherwise, never searchable;
  Nurse / Lab / Pharmacist / Billing have no patient search in v1.

## Decisions

- **Owner decision (2026-11-22) — Online Payments is its own module
  (M9)**: Prescription, Billing and Online Payments are each separate
  modules because they are important. They must not be lumped together
  or deferred as a group. This spec exists because of that decision.
  (Master Plan §4.3 listed real payment settlement as out of scope
  unless explicitly approved — this module is that explicit approval,
  limited to the scope in this spec.)
- **Inherited — invoice vs. payment are separate records (Master Plan
  §7.1, WF-04, Spec 008)**: an invoice states what is owed; a payment
  records money received. An online payment adds a third record — the
  attempt — which becomes a Payment record only when the gateway
  confirms the money.
- **Inherited — decimal-safe money (Master Plan §9.1)**: `Decimal` /
  `NUMERIC`, never binary floating point.
- **Inherited — no human may mark an online payment Paid**: only a
  verified gateway callback reconciles a payment. This is a security
  decision, not a convenience rule — it prevents money from being
  invented without the gateway.
- **Inherited — patient privacy (Spec 001 D-06/D-07/D-12)**: CNIC /
  B-Form encrypted, Receptionist/Admin only, never searchable; Billing
  has no patient search in v1 and sees name + MRN only via a linked
  record.

Everything else about online payments is an Open Question below. In
particular, no gateway is chosen here, and no fee, settlement timeline,
or regulatory claim is made.

## Open Questions

These are genuinely undecided. They must be answered by the owner (with
hospital/discovery input where noted) before or at approval; this spec
does not guess them.

- **OQ-010-1 — Which payment gateway? RESOLVED 2026-11-22 by the owner.**
  Easypaisa and JazzCash (mobile wallets) and bank transfer are the
  convenient primary methods; Stripe is an additional option for users
  who pay by card. MediCore therefore supports multiple gateways — one
  adapter implementation per gateway behind the single gateway interface —
  rather than a single gateway. The per-gateway integration details (API,
  callback format, signature verification, sandbox access, whether a
  refund API exists) are still to be confirmed per gateway at
  implementation time; no implementation work may start before the spec
  itself is approved.
- **OQ-010-2 — Fees.** Is there a per-transaction fee, who bears it (the
  hospital or the patient), and is it added to the invoice, absorbed by
  the hospital, or shown separately? No fee may be charged or displayed
  until this is defined — and no fee amount is stated in this spec.
- **OQ-010-3 — Settlement timeline and reconciliation cadence.** When
  does money the gateway collected actually reach the hospital's
  account, and how often must MediCore reconcile gateway records
  against its own (daily? on demand?)? No timeline is stated here.
- **OQ-010-4 — Refunds through the gateway.** Does the chosen gateway
  offer a refund API, and if so who may call it? If not, refunds are
  manual and reconciled by hand under Spec 008 — and that must be stated
  as the procedure, not improvised at the counter.
- **OQ-010-5 — Payment link expiry.** How long is an initiated payment
  valid before it expires (e.g. 30 minutes? 24 hours?) and who may
  extend or re-issue it? The expiry rule is undecided; the states and
  transitions in this spec do not depend on the value.
- **OQ-010-6 — Webhook delivery guarantees.** What does the chosen
  gateway guarantee about retries, ordering, and redelivery, and how
  must MediCore respond (HTTP status, response body, retry window)?
  The idempotency rule in this spec (FR-004) holds whatever the answer,
  but the exact handshake depends on the gateway.
- **OQ-010-7 — Receipt format for online payments.** What does the
  patient receive as proof of an online payment (gateway receipt?
  MediCore receipt reusing the Spec 008 receipt reference? both?), and
  what must it show? Format undecided (Spec 008 OQ-008-3 also applies).
- **OQ-010-8 — Payment methods inside the gateway.** Which methods does
  the hospital accept online (cards? mobile wallets? bank transfer?) —
  the answer depends on the gateway chosen in OQ-010-1, and each method
  may need its own handling.
- **OQ-010-9 — Currency.** Expected to be PKR (hospital in Pakistan) —
  to be confirmed. Amounts need a currency recorded with them if anything
  other than a single fixed currency is ever possible.
- **OQ-010-10 — Disputes and chargebacks.** What happens if a patient
  disputes an online payment with the gateway or their bank? Who is
  notified, what state does the invoice go to, and who investigates?
  No procedure is defined in this spec.

## Deferred (not decided here)

- **Patient portal / patient self-service payment**: out of scope in v1;
  a future module (Master Plan §6 M13) if the owner approves it.
- **Fees, settlement timelines, regulatory claims**: deferred until
  OQ-010-2 / OQ-010-3 are answered; nothing about them is stated in
  this spec.
- **Partial refunds of online payments**: deferred until OQ-010-4 and
  Spec 008 OQ-008-8 are answered.
- **Master Plan §§19–23 missing**: the Master Plan body ends at §18.1;
  §§19–23 (deployment, risk register, governance/decision log,
  acceptance, open decisions) are listed in the contents but absent from
  the document. Explicitly deferred: they must be supplied or formally
  deferred before release planning (Phase 8), but they do not block this
  feature's specification.
- **Auth/session strategy is decided (Spec 001 D-09, ADR-001)**; no auth
  question is reopened here.
