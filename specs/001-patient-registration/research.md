# Research: Patient Registration (001)

**Date**: 2026-11-22 | **Status**: Draft — Phase 0 output

## Sources

- Master Plan v1.0 (22 November 2026, draft planning baseline), §4 P0, §6 M03,
  §7 WF-01, §8 FR-005/006/007, §9 NFR-01–05, §10–11, §12, §16.
- MediCore Constitution v1.0.0 (ratified 2026-11-07), Principles I–VIII.
- Spec Kit templates in `.specify/templates/` (spec, plan, tasks).

## Decisions (proposed — to be confirmed at plan approval)

### Stack

| Choice | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| Frontend | React + TypeScript + Vite | Team direction in the constitution (§2.2); Vite is the standard React dev/build tool; TypeScript catches form/API shape errors early | Next.js (heavier, SSR unneeded for an admin HMS); plain JavaScript (loses type safety on patient records) |
| UI | Tailwind CSS + shadcn/ui | Consistent, accessible components; constitution proposes it; avoids a bespoke design system for an FYP | Material UI (heavier, opinionated look); Bootstrap (weaker accessibility defaults) |
| Backend | Django + Django REST Framework | Constitution §2.2; Django's ORM, migrations, admin, and auth reduce bespoke code for a data-heavy HMS; DRF gives serializers + permission classes that map directly onto the RBAC requirement | FastAPI (less built-in auth/admin; more code for the same result); Flask (too minimal for this scope) |
| Database | PostgreSQL | Constitution Principle IV *requires* PostgreSQL as the primary database | SQLite (dev-only; no production-grade constraints story); MySQL (no advantage, weaker constraint defaults) |
| Auth | DRF token/JWT — TO CONFIRM | Session auth is Django's default and simplest for a browser app; token/JWT suits a separate frontend. Decision deferred to scaffold — see ADR-001 open point | Session-only (simplest, CSRF needed); JWT-only (revocation complexity) |
| Testing | pytest + Django tests; Vitest + RTL; Playwright | Master Plan §10.1 / §16; pytest is the Django community standard; Playwright covers the one E2E journey | unittest only (weaker fixtures); Cypress (heavier than Playwright for one journey) |

### Architecture

- **Modular monolith**, not microservices: Master Plan §10.3. One backend, domain
  Django apps (`accounts`, `patients`, `audit`, …), created only when their scope
  is approved. A 6–7 month academic project cannot afford service boundaries.
- **Monorepo** `frontend/` + `backend/` + `docs/`: one repository, one PR flow,
  one CI run. Matches the existing GitHub setup.
- **Backend validation is authoritative**; frontend validation is usability only
  (Master Plan §9.1). The duplicate check and MRN generation live server-side.

### MRN

- Proposal: `MC-YYYY-NNNNNN` (e.g. `MC-2026-000123`), sequential per year,
  generated server-side, enforced unique by a database constraint.
- Not decided: the owner/supervisor must confirm the format (spec Open Question 1)
  before the model is written. Alternatives (plain sequential, hospital-code
  prefix) are recorded in the spec.

### Duplicate detection

- Starting rule (proposal): exact match on full name + date of birth flags a
  candidate. No fuzzy matching in v1 — fuzzy matching adds false positives and
  needs tuning data the project does not have.
- Decision is always human-recorded; the system never merges automatically
  (Master Plan §6 M03, FR-007).

### Timezone

- Proposed display timezone: **Asia/Karachi** (hospital location; to confirm).
  Store timestamps in UTC; display in the hospital timezone. This matches the
  lesson from the attendance project, where UTC-based "today" stats were wrong
  by 5 hours.

## Unknowns / risks carried into the plan

- Auth/session strategy (see above) — decide at scaffold, record in ADR-001.
- Whether `accounts` (M01) lands before or with this feature — affects the demo.
- Exact required fields and duplicate rule — owner/supervisor decisions (spec
  Open Questions 1–9).
- Master Plan §§19–23 are absent from the supplied document (listed in contents,
  body ends at §18.1) — deployment, risk register, governance, and acceptance
  sections must be supplied or explicitly deferred.
- No hospital partner or real workflow data was available for this research;
  the Master Plan's problem statement is explicitly a hypothesis "to validate"
  (§2.2). Discovery interviews remain an open item.
