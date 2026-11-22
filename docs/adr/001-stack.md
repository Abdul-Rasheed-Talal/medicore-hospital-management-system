# ADR-001: Technology Stack

**Status**: Proposed — pending owner/supervisor approval (Gate B, Master Plan §17.1).
Nothing in this ADR is binding until it is approved. Implementation must not
start on the basis of this draft alone.

**Date**: 2026-11-22
**Deciders**: Project owner (Abdul Rasheed Talal), academic supervisor (to confirm)
**Context**: MediCore Constitution v1.0.0 §2.2 proposes a stack but states final
technology selections "MUST be confirmed through the approved architecture plan".
Master Plan v1.0 §10.1 proposes the same stack, also marked "proposed".

## Decision (proposed)

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

## Open points (must be decided at scaffold, before implementation)

1. **Auth/session strategy**: Django session auth (simplest for a browser app,
   CSRF needed) vs DRF token/JWT (suits a separate frontend, revocation
   complexity). Proposed lean: session auth for the browser app; revisit if a
   separate mobile/portal client is ever approved.
2. **Python / Node versions**: proposed Python 3.12, Node 20 LTS — confirm at
   scaffold against what the lab machines actually run.
3. **Display timezone**: proposed Asia/Karachi — confirm with the supervisor.

## Consequences

- If approved, the scaffold PR (frontend + backend shells, CI, health check)
  may proceed; feature implementation still needs its own approved spec.
- If the supervisor prefers a different stack, this ADR is amended (with
  rationale, per Constitution §4) and the plan/spec are updated before any code.
- Changing the stack after implementation starts requires owner approval and a
  new ADR — it is not a contributor-level decision.
