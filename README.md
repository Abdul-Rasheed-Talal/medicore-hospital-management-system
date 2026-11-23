# MediCore — Hospital Management System

**Status: Spec 001 (Patient Registration) and ADR-001 (stack) approved by the
owner 2026-11-22. Application scaffold landed on `feat/medicore-scaffold`
(backend + frontend shells, session auth, CI). No feature code yet — the
Patient model and registration flow are the next PR.**
The Master Plan itself remains a draft planning baseline.
MediCore is a final-year academic project: a web-based Hospital Management System (HMS)
for a single hospital organisation, built with Spec-Driven Development (SDD).

> **Honest note:** MediCore is an **academic prototype**. It is not a certified
> clinical system, not a production-ready hospital platform, and not a legally
> compliant medical-record service. It must not be represented as one without the
> required validation, security assessment, operational controls, and
> jurisdiction-specific review. Development and demonstrations use **synthetic
> patient data only** — never real patient records.

## What it will do (planned MVP, P0)

- Authentication and role-based access (RBAC, enforced on the backend)
- Hospital setup: departments, staff, and service catalog basics
- Patient registration and patient search, with a unique medical record number (MRN)
- Appointment scheduling and status management
- Encounter / visit record with notes and diagnosis fields

Later candidates (P1, only if time and approval allow): prescriptions, billing,
laboratory workflow, dashboards and reports. Out of scope unless explicitly
approved: multi-hospital tenancy, clinical decision support, device/instrument
integration, insurance claims, real payment settlement, pharmacy inventory,
native mobile apps, and migration of real patient records.

Source of scope: `MediCore_Project_Master_Plan_v1.0.pdf` (v1.0, 22 November 2026,
draft planning baseline) and `.specify/memory/constitution.md` (v1.0.0, ratified
2026-11-07). Where the plan and a feature specification disagree, the approved
specification wins for that feature.

## Spec-Driven Development workflow

Every significant feature follows this lifecycle, in order:

1. **Constitution** — governing principles (already ratified, v1.0.0)
2. **Specify** — feature specification with actors, user stories, acceptance criteria
3. **Clarify** — resolve ambiguities; no hidden assumptions
4. **Plan** — architecture, data, APIs, security, test approach
5. **Checklist** — quality, security, UX, and requirement completeness
6. **Tasks** — ordered, testable implementation tasks
7. **Analyze** — consistency across spec, plan, and tasks
8. **Implement** — small changes, with tests
9. **Converge** — verify implementation against the specification

No implementation before an approved specification (Constitution Principle I).
No agent — human or AI — may independently change the stack, the constitution,
the approved scope, or bypass security/testing requirements. Such changes need
explicit project-owner approval.

Current state: **scaffold landed (branch `feat/medicore-scaffold`).** The first
feature is `specs/001-patient-registration/` (spec + plan, **approved by the
owner 2026-11-22**). The Patient model and registration flow are the next PR,
built on this scaffold.

## Stack — ACCEPTED 2026-11-22

> The stack below was **accepted by the project owner on 2026-11-22**
> (ADR-001). See ADR-001 for the rationale and the alternatives considered.
> Auth strategy: Django session auth (secure HttpOnly cookie, CSRF), no JWT
> in v1.

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite |
| UI styling | Tailwind CSS + shadcn/ui |
| Backend | Python + Django + Django REST Framework |
| Database | PostgreSQL |
| Testing | pytest / Django tests, Vitest + React Testing Library, Playwright |
| Version control | Git + GitHub |
| SDD | GitHub Spec Kit (`.specify/`) |

## Repository layout (planned)

```text
.specify/            Spec Kit: constitution, templates, scripts, workflows
docs/
  adr/               Architecture Decision Records (ADR-001 confirms the stack)
specs/
  001-patient-registration/
    spec.md          Feature specification (draft)
    plan.md          Architecture plan (draft)
    research.md      Phase 0 research
    data-model.md    Patient data model sketch (draft)
frontend/            React + TypeScript + Vite (scaffolded: layout, router,
                     auth context, login shell; no feature pages yet)
backend/             Django + DRF (scaffolded: settings split, accounts,
                     audit, app shells; no Patient model yet)
.github/workflows/   CI
```

## Setup

Prerequisites: Python 3.12, Node 20 LTS (ADR-001). The scaffold was built
and verified on Node 24 because Node 20 was not installed on the build
machine — a patch-level/major-version note, not a stack change; CI still
runs Node 20 LTS.

1. Clone the repository and copy the environment template:

   ```bash
   git clone https://github.com/abdulrasheed-tech/medicore-hospital-management-system.git
   cd medicore-hospital-management-system
   cp .env.example .env   # then fill in real values — never commit .env
   ```

2. Backend (Django + DRF, from `backend/`):

   ```bash
   python -m venv .venv && source .venv/bin/activate   # or use any venv
   pip install -r requirements.txt
   python manage.py migrate        # SQLite by default; see step 3 for Postgres
   python manage.py seed_roles     # create the 7 role groups (Admin … Billing)
   python manage.py createsuperuser
   python manage.py runserver      # http://localhost:8000
   ```

   Tests: `python -m pytest` (from `backend/`). System check:
   `python manage.py check`.

3. PostgreSQL (optional for local dev, required as the primary database):

   ```bash
   docker compose up -d db
   # in .env: DATABASE_URL=postgres://medicore:medicore@localhost:5432/medicore
   cd backend && python manage.py migrate
   ```

   Without `DATABASE_URL` the backend falls back to SQLite
   (`backend/db.sqlite3`) for local development only.

4. Frontend (React + TypeScript + Vite, from `frontend/`):

   ```bash
   npm install
   npm run dev        # http://localhost:5173 — /api is proxied to Django
   ```

   Tests: `npm test` (Vitest + React Testing Library). Typecheck:
   `npx tsc --noEmit`. Production build: `npm run build`.

5. Run both test suites; both must pass before any demo.

Environment variables are documented in `.env.example`. Secrets, credentials,
and private configuration must never be committed (Constitution Principle III).

## Documentation

- Constitution: `.specify/memory/constitution.md`
- Master Plan: `MediCore_Project_Master_Plan_v1.0.pdf` (uploaded by the owner;
  not stored in this repository — keep the copy with the project records)
- Feature specs: `specs/`
- Architecture decisions: `docs/adr/`

## Contributing

- Work on feature branches (`feature/NNN-short-name`), small coherent commits,
  pull requests for review — even for a solo project.
- Commit messages: `docs: …`, `feat: …`, `test: …`, `fix: …`
- Review the staged diff before committing. Never commit `.env`, credentials,
  real patient data, local databases, or generated dependencies.

## License

MIT — see `LICENSE`. The owner may change the licence; that is a decision for
the owner/supervisor, not for a contributor.
