# Implementation Plan: Billing and Payments (008)

**Branch**: `docs/medicore-all-specs` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — **P1 CANDIDATE, NOT APPROVED, DO NOT IMPLEMENT YET.**
Billing is a P1 Candidate (Master Plan §4.2, §6 M09; roadmap §17 Phase 6:
choose lab OR billing OR prescription). This plan describes how the spec
*would* be implemented once the owner makes the priority call, answers the
spec's Open Questions (OQ-008-1–OQ-008-13), and approves the spec. No
implementation work may start before then.

## Summary

Build billing and payments (Master Plan §4.2 P1 Candidate, §6 M09, §7
WF-04, §8 FR-016/FR-017): Billing staff create invoices with line items
from approved services in the service catalog, the system computes
subtotal/total with decimal-safe arithmetic (no discount/tax rule is
defined in v1, so total = subtotal), cashiers record payments as records
separate from the invoice, and the outstanding balance and invoice state
(Unpaid / Partially paid / Paid / Voided / Refunded) update in the same
database transaction as each payment. Overpayment is rejected by the
backend; void and refund go through an approved, audited process; no
financial record is hard-deleted.

Technical approach: modular monolith — React + TypeScript + Vite +
Tailwind + shadcn/ui frontend, Django + DRF + PostgreSQL backend,
`billing` Django app, REST API under `/api/billing/`, money as Python
`Decimal` / PostgreSQL `NUMERIC`, invoice state as an explicit enum with
enforced transitions, audit events for create/payment/void/refund. Stack
is ACCEPTED (ADR-001, owner approval 2026-11-22); session auth is the
decided auth strategy (Spec 001 D-09).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided,
ADR-001; verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19
+ Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing
Library (frontend), Playwright (E2E, one journey: create invoice → record
payment → Paid)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2
seconds under a small demo dataset and local test conditions (Master Plan
NFR-05, provisional)

**Constraints**: Synthetic data only; no real patient or financial records;
no real money moves (payments recorded here are records of money received
offline, not gateway settlement); secrets via environment only; backend
validation is authoritative (frontend validation is usability only); no
hard deletion of invoices, payments, or refunds; no floats for money

**Scale/Scope**: Single hospital, single deployment; tens of staff users;
thousands of invoices in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a DRAFT candidate; implementation is blocked until the owner makes the Phase 6 priority call, answers OQ-008-1–OQ-008-13, and approves the spec. No implementation on this plan alone. GATE NOT YET PASSED. |
| II. Modular architecture | `billing` Django app, separate frontend pages/components, money/state rules in services — not duplicated in views/serializers. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced; least privilege (Billing sees name + MRN only, no CNIC, no clinical notes); synthetic data only; no secrets in code; no patient data in logs. PASS by design. |
| IV. Data integrity | PostgreSQL, `Decimal`/`NUMERIC` for all money, invoice-number and receipt-reference unique constraints, balance + state updated in the same transaction as each payment, migrations version-controlled, no hard delete. PASS by design. |
| V. Test-first | Overpayment, decimal-arithmetic, state-transition, and permission tests are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; API contract documented; every financial change auditable. PASS by design. |
| VIII. Scope discipline | Invoices/payments/void/refund only. No settlement, banking, insurance, discount/tax rules, or price-setting. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/008-billing/
├── spec.md              # Feature specification (DRAFT candidate — not approved)
└── plan.md              # This file
└── tasks.md             # Phase 2 output (NOT created yet — only after spec approval)
```

### Source Code (repository root)

```text
backend/
├── config/              # Django settings (env-based), urls
├── apps/
│   ├── accounts/        # Users, roles, permissions (prerequisite, M01)
│   ├── organization/    # Departments, staff, service catalog (prerequisite, M02)
│   ├── patients/        # Patient identity (prerequisite, M03 — Spec 001)
│   ├── appointments/    # Appointments (prerequisite, M04)
│   ├── encounters/      # Encounters (prerequisite, M05)
│   ├── billing/         # Invoices, line items, payments, refunds
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py  # Invoice totals, payment application, void/refund
│   │   ├── views.py     # DRF viewsets, permission-checked
│   │   ├── urls.py
│   │   └── tests/
│   └── audit/           # Audit events (shared)
└── tests/

frontend/
├── src/
│   ├── components/      # InvoiceForm, PaymentForm, InvoiceDetail, BalanceSummary
│   ├── pages/           # Billing list, invoice detail, record payment
│   ├── services/        # API client for /api/billing/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` +
`docs/`. Backend apps are created only when their scope is approved —
`accounts`, `organization` (service catalog), `patients`,
`appointments`, and `encounters` are prerequisites for this feature and
must land first (or alongside it, with this feature's tests depending on
them). Do not create every app in Master Plan §10.4 at initialisation.

## Data model sketch

No separate `data-model.md` is written for this spec: the entities below
are the full sketch, and migrations may be generated from it once the spec
is approved and the scaffold exists. (OQ-008-1–OQ-008-13 must be answered
first where they affect a field: invoice-number format OQ-008-2, receipt
format OQ-008-3, currency OQ-008-4, payment-method values OQ-008-5,
refund approver OQ-008-8.)

### Invoice

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | Stable internal key; never exposed as the invoice identifier |
| invoice_number | String, unique, indexed | System-generated server-side only; format OQ-008-2 |
| patient | FK → Patient | The patient billed, by MRN; Billing sees name + MRN only |
| appointment | FK → Appointment, nullable | Originating appointment, if any (OQ-008-10) |
| encounter | FK → Encounter, nullable | Originating encounter, if any (OQ-008-10) |
| status | Enum: Unpaid / Partially paid / Paid / Voided / Refunded | Explicit enum; transitions enforced in the service layer and by a DB check constraint where practical |
| subtotal | Decimal(12, 2) | Exact sum of line totals |
| discount_total | Decimal(12, 2) | Always 0 in v1 — no discount rule defined |
| tax_total | Decimal(12, 2) | Always 0 in v1 — no tax rule defined |
| total | Decimal(12, 2) | = subtotal in v1 |
| balance | Decimal(12, 2) | total − sum(payments); maintained in the same transaction as each payment; never negative |
| created_by | FK → User | Who created the invoice |
| created_at | DateTime (UTC) | Displayed in Asia/Karachi |
| updated_at | DateTime (UTC) | Displayed in Asia/Karachi |

Constraints: `invoice_number` unique (database); `total >= 0`,
`balance >= 0`, `balance <= total` (database check constraints);
`status` transitions enforced server-side (Unpaid → Partially paid →
Paid; Unpaid → Voided; Paid → Refunded; no other transition).

### InvoiceLineItem

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | — |
| invoice | FK → Invoice | — |
| service | FK → ServiceCatalogItem | Approved charge item from M02; never free text |
| description | String | As shown on the invoice (copied from the catalog item at creation) |
| quantity | Positive integer | — |
| unit_price | Decimal(12, 2) | Snapshot of the catalog price at invoice creation; later catalog changes never alter it |
| line_total | Decimal(12, 2) | quantity × unit_price, computed server-side |

Rule: line items are immutable once the invoice is created. Corrections
go through void-and-reissue or refund, never an edit.

### Payment

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | — |
| invoice | FK → Invoice | — |
| amount | Decimal(12, 2) | Positive; must not exceed the invoice's outstanding balance at the time of recording |
| method | Enum | Allowed values OQ-008-5 (expected: Cash at minimum) |
| date | Date | Not in the future (Asia/Karachi); backdating OQ-008-11 |
| receipt_reference | String, unique, indexed | Required; format OQ-008-3 |
| recorded_by | FK → User | Who recorded the payment |
| recorded_at | DateTime (UTC) | Displayed in Asia/Karachi |

Rule: recording a payment and updating the invoice balance + status
happens in one database transaction, with the balance re-checked inside
that transaction so two concurrent payments cannot together overpay.

### Refund

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | — |
| invoice | FK → Invoice | Must be Paid at the time of the refund |
| amount | Decimal(12, 2) | Positive; full refund in v1 (partial refunds OQ-008-8) |
| method | Enum | Same allowed values as Payment (OQ-008-5) |
| date | Date | Not in the future |
| reference | String, unique | Required |
| reason | Text, required | Why the refund was made |
| processed_by | FK → User | Approver per OQ-008-8 |
| processed_at | DateTime (UTC) | Displayed in Asia/Karachi |

Rule: a full refund moves the invoice to Refunded. The invoice, its line
items, and its payments remain visible — nothing is deleted.

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `POST /api/billing/invoices/` | Create an invoice from approved services (Billing/Admin). Returns 201 with invoice number, lines, subtotal, total, state Unpaid. |
| `GET /api/billing/invoices/?status=&patient=&page=` | List invoices, paginated, role-filtered; Billing sees billing data only. |
| `GET /api/billing/invoices/{id}/` | Invoice detail: line items, payments, balance, state-change history. |
| `POST /api/billing/invoices/{id}/payments/` | Record a payment (Billing/Admin). Returns 201, or 400/422 when the amount exceeds the balance or a field is invalid. Updates balance + state in the same transaction. |
| `GET /api/billing/invoices/{id}/payments/` | Payment history for the invoice. |
| `POST /api/billing/invoices/{id}/void/` | Void an Unpaid invoice with a written reason (Billing/Admin). |
| `POST /api/billing/invoices/{id}/refund/` | Refund a Paid invoice with amount, method, date, reference, reason (approver per OQ-008-8). |

All endpoints require authentication; all mutations require the role in
the spec's permissions table; validation errors return structured
field-level errors. Money is serialised as decimal strings in JSON, never
as binary floats.

## Security approach

- Django session authentication (decided, ADR-001 / Spec 001 D-09):
  secure HttpOnly cookie, CSRF protection, server-side session
  revocation. No JWT in v1.
- Permission classes per endpoint + object-level checks; deny by default.
  Billing sees name + MRN only for the linked patient; CNIC / B-Form is
  never returned to Billing (encrypted, Receptionist/Admin only — Spec
  001 D-07/D-12), clinical notes are never returned to Billing, and
  Billing has no patient free-text search in v1.
- Invoice numbers and receipt references are generated/validated
  server-side; never trust a client-supplied invoice number.
- All money as `Decimal` end to end: Django `DecimalField`, PostgreSQL
  `NUMERIC`, JSON decimal strings. No `float` anywhere in the money path
  (Master Plan §9.1). A lint/test guard should fail the build if a float
  enters the billing calculation path.
- Audit events for invoice create / payment / void / refund.
- No patient or financial data in logs, URLs (beyond the invoice number
  in a path), or error messages beyond what the caller's role may see.
- Rate-limit login; throttle payment endpoints against abuse.

## Test strategy

- **Unit**: decimal arithmetic (sums that expose binary-float error, e.g.
  0.1 + 0.2 cases, must be exact); line-total and subtotal computation;
  balance derivation; state-transition table (allowed vs. refused
  transitions); validation rules (positive amount, 2dp, payment date not
  in the future, receipt reference present).
- **Model/DB**: unique constraints (invoice number, receipt reference),
  check constraints (`balance >= 0`, `balance <= total`), no hard delete,
  migration applies cleanly from fresh setup.
- **API**: auth required (401 unauthenticated), permission allow/deny per
  role (Doctor/Receptionist create or pay → 403), validation errors (400
  with field errors), overpayment rejected with no Payment row created,
  concurrent-payment test (two payments that together exceed the balance
  — only the first succeeds), void/refund flows (void of a Paid invoice
  refused; payment against a Voided invoice refused; line-item edit
  refused).
- **Component**: invoice form, payment form validation feedback, balance
  display, void/refund confirmation dialogs with mandatory reason.
- **E2E (Playwright)**: create invoice → record partial payment →
  Partially paid → record remainder → Paid, with balance shown correctly
  at each step.
- **Security**: object-level access (a Billing user cannot fetch another
  role's forbidden record by changing an ID; CNIC never appears in any
  billing response), audit events recorded.

Tests are written first (Constitution Principle V) and must fail before
implementation. No tests are written until the spec is approved — writing
them now would test undecided rules (OQ-008-1–OQ-008-13).

## Risks for this feature

- **Not approved / priority undecided (OQ-008-1)** — the Phase 6 choice
  (lab OR billing OR prescription) has not been made. Mitigation: this
  spec and plan exist so the decision can be taken on understood scope;
  no code is written before it.
- **Financial rules need discovery (Master Plan §4.2, §6 M09)** —
  currency, payment methods, discount, tax, refund approver, and receipt
  format are all open (OQ-008-2–OQ-008-8). Mitigation: the spec makes
  each one an explicit question with a stated default (total = subtotal
  in v1); implementation is blocked until they are answered.
- **Money arithmetic** — a float anywhere in the path silently corrupts
  totals. Mitigation: `Decimal`/`NUMERIC` end to end, decimal strings in
  JSON, and a dedicated test with float-exposing amounts.
- **Concurrent overpayment** — two payments recorded at once could
  together exceed the balance. Mitigation: balance check + update inside
  one transaction with row locking on the invoice; covered by an API test.
- **Scope creep into real settlement / insurance** — Master Plan §4.3
  excludes both. Mitigation: the spec's out-of-scope list is enforced at
  review; any settlement or insurance work needs a new approved spec.
- **Dependency on the service catalog (M02)** — without approved services
  and prices, invoices cannot be created from approved items (spec
  FR-001). Mitigation: M02 lands before or alongside billing.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
