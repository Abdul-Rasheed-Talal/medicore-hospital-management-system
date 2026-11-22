# Research: Patient Registration (001)

**Date**: 2026-11-22 | **Status**: Approved by owner 2026-11-22 — the decisions
below are binding (see spec.md "Decisions" D-01–D-13, as amended 2026-11-22
by owner instruction: D-11 gender required, D-12 CNIC / B-Form required,
D-13 blood group optional)

## Sources

- Master Plan v1.0 (22 November 2026, draft planning baseline), §4 P0, §6 M03,
  §7 WF-01, §8 FR-005/006/007, §9 NFR-01–05, §10–11, §12, §16.
- MediCore Constitution v1.0.0 (ratified 2026-11-07), Principles I–VIII.
- Spec Kit templates in `.specify/templates/` (spec, plan, tasks).

## Decisions (approved by owner 2026-11-22)

### Stack

| Choice | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| Frontend | React + TypeScript + Vite | Team direction in the constitution (§2.2); Vite is the standard React dev/build tool; TypeScript catches form/API shape errors early | Next.js (heavier, SSR unneeded for an admin HMS); plain JavaScript (loses type safety on patient records) |
| UI | Tailwind CSS + shadcn/ui | Consistent, accessible components; constitution proposes it; avoids a bespoke design system for an FYP | Material UI (heavier, opinionated look); Bootstrap (weaker accessibility defaults) |
| Backend | Django + Django REST Framework | Constitution §2.2; Django's ORM, migrations, admin, and auth reduce bespoke code for a data-heavy HMS; DRF gives serializers + permission classes that map directly onto the RBAC requirement | FastAPI (less built-in auth/admin; more code for the same result); Flask (too minimal for this scope) |
| Database | PostgreSQL | Constitution Principle IV *requires* PostgreSQL as the primary database | SQLite (dev-only; no production-grade constraints story); MySQL (no advantage, weaker constraint defaults) |
| Auth | Django session auth (secure HttpOnly cookie, CSRF protection); no JWT in v1 | Decided (spec D-09, ADR-001): the product is a browser app for staff on one deployment — Django's built-in session auth is the simplest mature option, with server-side revocation that JWT would have to be hand-built to match | DRF token/JWT (revocation complexity; suits a separate frontend — revisit only if a mobile/portal client is approved) |
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

- Decided (spec D-01): `MC-YYYY-NNNNNN` (e.g. `MC-2026-000123`), sequential
  per year, sequence resets to `000001` each 1 January, generated
  server-side, enforced unique by a database constraint. Rejected
  alternatives: plain sequential (grows unboundedly), hospital-code prefix
  (adds nothing for a single-hospital system).

### Duplicate detection

- Decided rule (spec D-03, D-12): exact match on full name + date of birth
  blocks registration pending a recorded human decision, and an exact match
  on CNIC / B-Form number also blocks registration pending a recorded human
  decision — a CNIC / B-Form number is a unique national identifier, so a
  match on it is as strong as a name + date of birth match. An exact
  phone-number match alone is a strong secondary signal (non-blocking
  warning). No fuzzy matching in v1 — fuzzy matching adds false positives
  and needs tuning data the project does not have (documented limitation).
- Decision is always human-recorded; the system never merges automatically
  (Master Plan §6 M03, FR-007). The registering Receptionist may resolve a
  duplicate warning with a written reason; merging two records requires
  Admin (spec D-08).

### Fields and statuses

- Decided (spec D-02, D-05, D-07, D-11, D-12, D-13): required — full name,
  date of birth, phone, gender (Male / Female / Other), CNIC / B-Form
  number (`national_id`, 13 digits, `xxxxx-xxxxxxx-x`, dashes optional on
  input, digits only stored, unique); optional — blood group (A+, A-, B+,
  B-, AB+, AB-, O+, O-), address, emergency contact. Patient statuses:
  Active / Inactive / Merged / Archived. CNIC / B-Form is required for
  every registration, encrypted at rest, visible in full only to
  Receptionist and Admin, masked for all other roles; no CNIC search in v1
  — a deliberate decision (D-06, D-12), not an oversight: no workflow needs
  to look a patient up by CNIC, and uniqueness is enforced via a
  deterministic hash of the digits since the encrypted value cannot be
  queried. The same optional blood-group field will apply to staff profiles
  when the staff / hospital-setup feature is specified (D-13).
- Search fields decided (spec D-06): MRN, full name (minimum 3 characters),
  phone number.

### Timezone

- Decided display timezone: **Asia/Karachi** (hospital is in Pakistan).
  Store timestamps in UTC; display in the hospital timezone. This matches the
  lesson from the attendance project, where UTC-based "today" stats were wrong
  by 5 hours.

## Unknowns / risks carried into the plan

- Whether `accounts` (M01) lands before or with this feature — affects the demo.
- Master Plan §§19–23 are absent from the supplied document (listed in contents,
  body ends at §18.1) — deployment, risk register, governance, and acceptance
  sections are explicitly deferred until release planning (Phase 8).
- No hospital partner or real workflow data was available for this research;
  the Master Plan's problem statement is explicitly a hypothesis "to validate"
  (§2.2). Discovery interviews remain an open item.
