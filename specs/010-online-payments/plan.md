# Implementation Plan: Online Payments (010)

**Branch**: `docs/modules-prescription-billing-payments` | **Date**: 2026-11-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `./spec.md`

**Status**: Draft — **separate module M9, NOT APPROVED, DO NOT IMPLEMENT
YET.** The owner decided on 2026-11-22 that Online Payments is its own
module. This plan describes how the spec *would* be implemented once the
owner chooses a payment gateway (OQ-010-1), answers the spec's Open
Questions (OQ-010-1–OQ-010-10), and approves the spec. No implementation
work may start before then — the gateway choice decides the integration,
so building before it would build the wrong integration.

## Summary

Build online payment collection against invoices (Master Plan §7 WF-04,
§8 FR-017): Billing initiates an online payment against an Unpaid or
Partially paid invoice; the patient pays on the gateway's page; the
gateway's verified callback/webhook reconciles the result — success
creates a Spec 008 Payment record and updates the invoice balance and
state in one transaction, failure or expiry leaves the invoice unchanged.
Duplicate callbacks are idempotent (gateway event id); unverified
callbacks are rejected; no human may mark an online payment Paid; no
card data ever enters MediCore; sandbox/test mode only outside
production.

Technical approach: modular monolith — React + TypeScript + Vite +
Tailwind + shadcn/ui frontend, Django + DRF + PostgreSQL backend, a
`payments` Django app (separate from `billing`, which owns invoices and
offline payment recording), REST API under `/api/online-payments/` plus
a public webhook endpoint, money as Python `Decimal` / PostgreSQL
`NUMERIC`, online-payment state as an explicit enum with enforced
transitions, audit events for initiation/callback/reconciliation/
failure/refund. Stack is ACCEPTED (ADR-001, owner approval 2026-11-22);
session auth is the decided auth strategy (Spec 001 D-09).

## Technical Context

**Language/Version**: Python 3.12, TypeScript 5.x, Node 20 LTS (decided,
ADR-001; verify against the lab machines at scaffold)

**Primary Dependencies**: Django 5.x + Django REST Framework, React 18/19
+ Vite, Tailwind CSS + shadcn/ui (all decided, ADR-001 ACCEPTED); the
chosen gateway's SDK/API client — **not yet chosen** (OQ-010-1)

**Storage**: PostgreSQL 16 (Constitution Principle IV requires PostgreSQL)

**Testing**: pytest + Django test client (backend), Vitest + React Testing
Library (frontend), Playwright (E2E, one journey: initiate online payment
→ stubbed success callback → Paid)

**Target Platform**: Modern desktop browsers (primary); usable on smaller screens

**Project Type**: Web application (frontend + backend, modular monolith)

**Performance Goals**: Common list/detail API operations respond within 2
seconds under a small demo dataset and local test conditions (Master Plan
NFR-05, provisional); webhook handling must answer quickly and never block
on slow work — reconciliation runs inside the request, retries are the
gateway's

**Constraints**: Synthetic data only; no real patient or financial records;
sandbox/test mode only outside production; gateway credentials via
environment only; no card data stored, logged, or displayed; backend
validation is authoritative (frontend validation is usability only);
no hard deletion of online-payment or payment records; no floats for money

**Scale/Scope**: Single hospital, single deployment; tens of staff users;
online payments are a small fraction of invoice volume in demo data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check for this feature |
|---|---|
| I. Requirements-first | Spec is a DRAFT; implementation is blocked until the owner chooses a gateway (OQ-010-1), answers OQ-010-1–OQ-010-10, and approves the spec. No implementation on this plan alone. GATE NOT YET PASSED. |
| II. Modular architecture | Separate `payments` Django app from `billing` (invoices/offline payments); gateway integration behind one service interface so the gateway can change without touching billing rules. PASS by design. |
| III. Security/privacy by design | Auth required; RBAC backend-enforced; least privilege (Billing sees name + MRN only, no CNIC, no clinical notes); webhook signature verification; no card data anywhere; synthetic data only; secrets via environment only. PASS by design. |
| IV. Data integrity | PostgreSQL, `Decimal`/`NUMERIC` for all money, gateway-reference and gateway-event-id unique constraints, reconciliation (Payment creation + balance + state) in one transaction with row locking, migrations version-controlled, no hard delete. PASS by design. |
| V. Test-first | Duplicate-callback, unverified-callback, over-balance, and state-transition tests are specified before implementation. PASS by design. |
| VI. Consistent/accessible UX | shadcn/ui components, labelled forms, field-level errors, keyboard-operable, visible focus, status not by colour alone. PASS by design. |
| VII. Documentation/traceability | Spec → plan → tasks → tests traceable; API contract documented; every initiation, callback, and reconciliation auditable. PASS by design. |
| VIII. Scope discipline | Initiate / callback / reconcile / refund only. No patient portal, no gateway choice made here, no fees, no settlement claims, no card handling. PASS. |

## Project Structure

### Documentation (this feature)

```text
specs/010-online-payments/
├── spec.md              # Feature specification (DRAFT — not approved)
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
│   ├── billing/         # Invoices, line items, offline payments, refunds (prerequisite, M8 — Spec 008)
│   ├── payments/        # OnlinePayment records, gateway service, webhook handler
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py  # Initiation, callback verification, reconciliation
│   │   ├── gateway.py   # Gateway adapter interface (one implementation per gateway)
│   │   ├── views.py     # DRF viewsets (staff) + webhook view (gateway)
│   │   ├── urls.py
│   │   └── tests/
│   └── audit/           # Audit events (shared)
└── tests/

frontend/
├── src/
│   ├── components/      # OnlinePaymentForm, OnlinePaymentStatus, PaymentLinkDisplay
│   ├── pages/           # Invoice detail (initiate online payment), online payments list
│   ├── services/        # API client for /api/online-payments/
│   └── tests/
└── tests/               # Playwright E2E
```

**Structure Decision**: Modular monolith, monorepo `frontend/` + `backend/` +
`docs/`. The `payments` app is separate from `billing` on purpose: billing
owns what is owed and what was received offline; payments owns the online
attempt and the gateway conversation. The gateway adapter is one interface
so the gateway can be swapped without touching billing rules. Backend apps
are created only when their scope is approved — `billing` (M8) is a
prerequisite for this feature and must land first (or alongside it, with
this feature's tests depending on it). Do not create every app in Master
Plan §10.4 at initialisation.

## Data model sketch

No separate `data-model.md` is written for this spec: the entity below is
the full sketch, and migrations may be generated from it once the spec is
approved, a gateway is chosen, and the scaffold exists. (OQ-010-1–OQ-010-10
must be answered first where they affect a field: gateway name and
reference format OQ-010-1, currency OQ-010-9, link expiry OQ-010-5,
refund handling OQ-010-4.)

### OnlinePayment

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | Stable internal key; never exposed as the payment identifier |
| gateway_reference | String, unique, indexed | System-generated server-side only; format decided with the gateway (OQ-010-1) |
| invoice | FK → Invoice | The invoice being paid; must be Unpaid or Partially paid at initiation |
| amount | Decimal(12, 2) | Positive; must not exceed the invoice's outstanding balance at initiation |
| currency | String | PKR — working assumption (OQ-010-9) |
| gateway | String | Name of the chosen gateway (OQ-010-1) |
| status | Enum: Initiated / Paid / Failed / Refunded / Expired | Explicit enum; transitions enforced in the service layer and by a DB check constraint where practical |
| gateway_event_id | String, unique, nullable until callback | Gateway's event/transaction id; the idempotency key — a second callback with the same id is ignored |
| failure_reason | Text, nullable | Recorded when Failed; never contains card data |
| payment_link | String, nullable | Link/reference returned at initiation, for sharing with the patient; generated by the gateway |
| initiated_by | FK → User | Who initiated the payment (Billing/Admin) |
| initiated_at | DateTime (UTC) | Displayed in Asia/Karachi |
| paid_at | DateTime (UTC), nullable | Set from the gateway's paid timestamp when Paid |
| created_at | DateTime (UTC) | Displayed in Asia/Karachi |
| updated_at | DateTime (UTC) | Displayed in Asia/Karachi |

Constraints: `gateway_reference` unique (database); `gateway_event_id`
unique where present (database); `amount > 0`, `amount <= invoice
balance at initiation` (backend, inside the initiation transaction);
`status` transitions enforced server-side (Initiated → Paid / Failed /
Expired; Paid → Refunded; no other transition). Reconciliation (Payment
creation + `OnlinePayment` Paid + invoice balance/state update) runs in
one transaction with row locking on the `OnlinePayment`, so concurrent
duplicate callbacks cannot create two Payment records.

## API groups (contract to be finalised at implementation; fields and rules are decided)

| Group | Operations |
|---|---|
| `POST /api/online-payments/` | Initiate an online payment (Billing/Admin). Body: `{ invoice, amount }`. Returns 201 with gateway reference, payment link, status Initiated. Rejected (400/422) when the amount exceeds the balance or the invoice is Paid/Voided/Refunded. |
| `GET /api/online-payments/?invoice=&status=&page=` | List online payments, paginated, role-filtered; Billing/Admin only. |
| `GET /api/online-payments/{id}/` | Online payment detail: invoice, amount, gateway, status, gateway reference, history. |
| `POST /api/online-payments/webhook/` | Gateway callback (public endpoint, no session auth — verified by gateway signature/secret instead). Verifies the notification, reconciles it, returns the gateway's expected acknowledgement. Unverified → 401/403, nothing recorded. |
| `POST /api/online-payments/{id}/refund/` | Refund a Paid online payment (Admin, approver per Spec 008 OQ-008-8; gateway refund API per OQ-010-4). |

All staff endpoints require session authentication; all mutations require
the role in the spec's permissions table; validation errors return
structured field-level errors. Money is serialised as decimal strings in
JSON, never as binary floats. The webhook endpoint is the only public
endpoint in the system: it must verify the gateway signature before
reading the payload, rate-limit by source, and never return internal
detail.

## Security approach

- Django session authentication for staff endpoints (decided, ADR-001 /
  Spec 001 D-09): secure HttpOnly cookie, CSRF protection, server-side
  session revocation. No JWT in v1.
- Webhook verification is the security boundary for the gateway: signature
  / secret check per the chosen gateway's mechanism, before any payload
  is trusted; unverified callbacks are rejected and logged as security
  events; the webhook view must not trust any field (amount, reference,
  status) until verification passes.
- Permission classes per endpoint + object-level checks; deny by default.
  Billing sees name + MRN only for the linked patient; CNIC / B-Form is
  never returned to Billing (encrypted, Receptionist/Admin only — Spec
  001 D-07/D-12), clinical notes are never returned to Billing, and
  Billing has no patient free-text search in v1.
- Gateway credentials (API keys, webhook secrets) come from environment
  variables only; they are never committed, never logged, and never
  returned by any API. Sandbox/test credentials in development; production
  credentials only in the production environment.
- No card data anywhere: no card numbers, PINs, or CVVs are stored,
  logged, or displayed — the gateway owns the payment page. A lint/test
  guard should fail the build if a card-data field appears in any model
  or serializer.
- All money as `Decimal` end to end: Django `DecimalField`, PostgreSQL
  `NUMERIC`, JSON decimal strings. No `float` anywhere in the money path
  (Master Plan §9.1).
- Audit events for initiation / callback / reconciliation / failure /
  expiry / refund; audit records contain only the gateway reference,
  event id, amount, and outcome — never secrets or full payloads.
- No patient or financial data in logs or URLs (beyond the gateway
  reference in a path) beyond what the caller's role may see.

## Test strategy

- **Unit**: amount validation (positive, 2dp, ≤ balance); state-transition
  table (allowed vs. refused transitions); gateway-reference uniqueness;
  amount-mismatch rejection on callback.
- **Model/DB**: unique constraints (gateway reference, gateway event
  id), check constraints (`amount > 0`), no hard delete, migration
  applies cleanly from fresh setup.
- **API**: auth required (401 unauthenticated) on staff endpoints;
  permission allow/deny per role (Doctor/Receptionist initiate → 403);
  validation errors (400 with field errors); over-balance initiation
  rejected with no `OnlinePayment` created; unverified callback rejected
  with nothing recorded; duplicate-callback test (same event delivered
  twice → exactly one Payment record); concurrent-callback test (two
  simultaneous deliveries → one Payment record); failure/expiry flows
  (invoice unchanged; re-initiation succeeds); late success after expiry
  (reconciled if the gateway confirms money was taken, audit-logged).
- **Component**: initiate-payment form, online-payment status display,
  payment-link display, failure/expiry feedback.
- **E2E (Playwright)**: create invoice → initiate online payment →
  stubbed gateway success callback → Paid, with balance shown correctly
  at each step.
- **Security**: webhook signature verification (valid, invalid, missing);
  object-level access (a Billing user cannot fetch another role's
  forbidden record by changing an ID; CNIC never appears in any payment
  response); no card-data field exists in any model/serializer; gateway
  secrets never appear in logs or responses.

Tests are written first (Constitution Principle V) and must fail before
implementation. No tests are written until the spec is approved and a
gateway is chosen — writing them now would test an undecided integration
(OQ-010-1–OQ-010-10).

## Risks for this feature

- **Gateway not chosen (OQ-010-1)** — the blocking decision: the
  integration, callback format, signature scheme, sandbox access, and
  refund capability all depend on it. Mitigation: this spec and plan
  exist so the decision can be taken on understood scope; the gateway
  adapter interface isolates the choice; no code is written before it.
- **Money counted twice** — duplicate or retried callbacks could create
  two Payment records for one payment. Mitigation: gateway-event-id
  idempotency + one-transaction reconciliation with row locking; covered
  by dedicated API tests.
- **Unverified callbacks moving money** — a forged callback could invent
  a payment. Mitigation: signature verification before any payload is
  trusted; no human may mark a payment Paid; security tests for invalid
  and missing signatures.
- **Fees, settlement, and disputes unknown (OQ-010-2/3/10)** — charging
  or displaying a fee, or claiming a settlement timeline, before these
  are defined would mislead the hospital and the patient. Mitigation:
  the spec states none of them; implementation is blocked until they
  are answered.
- **Scope creep into a patient portal** — Master Plan §6 M13 is a future
  module. Mitigation: the spec's out-of-scope list is enforced at
  review; any patient self-service work needs a new approved spec.
- **Dependency on billing (M8)** — without invoices and Spec 008's
  Payment/balance rules, online payments have nothing to reconcile
  into. Mitigation: M8 lands before or alongside this module.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
