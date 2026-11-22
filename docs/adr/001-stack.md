# ADR-001: Technology Stack

**Status**: ACCEPTED 2026-11-22 — approved by the project owner (Gate B,
Master Plan §17.1). Binding for implementation. The supervisor may still
raise objections; any change requires a new ADR with rationale.

**Date**: 2026-11-22 (accepted 2026-11-22)
**Deciders**: Project owner (Abdul Rasheed Talal); academic supervisor review
still outstanding — the supervisor may object, but the owner has approved
proceeding on this stack.
**Context**: MediCore Constitution v1.0.0 §2.2 proposes a stack but states final
technology selections "MUST be confirmed through the approved architecture plan".
Master Plan v1.0 §10.1 proposes the same stack. Both are now confirmed by
this accepted ADR.

## Decision (accepted)

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite |
| UI styling | Tailwind CSS + shadcn/ui |
| Backend | Python + Django + Django REST Framework |
| Database | PostgreSQL |
| Testing | pytest + Django tests, Vitest + React Testing Library, Playwright |
| Version control | Git + GitHub |
| Spec workflow | GitHub Spec Kit |

Architecture shape: **modular monolith** in a monorepo (`frontend/` + `backend/` +
`docs/`). One backend application organised into cohesive Django apps
(`accounts`, `patients`, `audit`, …), created only when their scope is approved.
No microservices.

## Rationale

- **Django + DRF**: The constitution already proposes it. Django's ORM,
  migrations, admin, and auth reduce bespoke code for a data-heavy HMS, and
  DRF serializers + permission classes map directly onto the RBAC requirement
  (Constitution Principle III). FastAPI would need more hand-built auth/admin
  for the same result; Flask is too minimal for this scope.
- **PostgreSQL**: Required by Constitution Principle IV, not a free choice.
- **React + TypeScript + Vite**: The constitution proposes it. TypeScript
  catches form/API shape errors early — valuable on patient records where a
  mistyped field is a data-integrity risk. Vite is the standard React build tool.
- **Tailwind + shadcn/ui**: Consistent, accessible components without building a
  bespoke design system for a final-year project.
- **Modular monolith**: Master Plan §10.3. A 6–7 month academic project cannot
  afford service boundaries, distributed transactions, or deployment complexity
  for a single-hospital system.
- **Testing stack**: pytest is the Django community standard; Playwright covers
  the end-to-end journeys the Master Plan requires (§16).

## Alternatives considered

- Next.js instead of Vite + React: heavier, server-side rendering unneeded for
  a staff admin application. Rejected.
- FastAPI instead of Django: less built-in auth/admin; more code for the same
  result. Rejected.
- Microservices: rejected — unjustifiable complexity for one hospital and one team.
- SQLite as primary database: rejected — the constitution requires PostgreSQL.

## Decided points

1. **Auth/session strategy — DECIDED (spec D-09)**: Django session
   authentication (secure HttpOnly cookie, CSRF protection) for the web app;
   no JWT in v1. Rationale: the product is a browser app for staff on one
   deployment — Django's built-in session auth is the simplest mature option,
   with server-side revocation that JWT would have to be hand-built to match.
   Revisit only if a separate mobile/portal client is ever approved.
2. **Python / Node versions — DECIDED**: Python 3.12, Node 20 LTS. Verify
   against what the lab machines actually run at scaffold; a patch-level
   change does not need a new ADR, a major-version change does.
3. **Display timezone — DECIDED**: Asia/Karachi (hospital is in Pakistan).
   Timestamps stored in UTC, displayed in Asia/Karachi.

## Consequences

- The scaffold PR (frontend + backend shells, CI, health check) may proceed;
  feature implementation still needs its own approved spec — Spec 001 was
  approved by the owner on the same date (2026-11-22).
- If the supervisor prefers a different stack, this ADR is amended (with
  rationale, per Constitution §4) and the plan/spec are updated before any code.
- Changing the stack after implementation starts requires owner approval and a
  new ADR — it is not a contributor-level decision.
