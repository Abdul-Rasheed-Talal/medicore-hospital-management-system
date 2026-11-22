# MediCore Deployment Guide

**Status**: Draft (Master Plan deliverable D-10).
**Date**: 2026-11-22
**Sources**: Master Plan v1.0 §§2.4, 9 (NFR-12/13), 10, 15.2, 16.3, 17;
Constitution Principles III, IV; ADR-001; Spec 001 plan.

This guide covers local development setup and the demo environment. There
is no production hospital deployment: MediCore is an academic project and
must not be represented as a certified clinical system or production-ready
hospital platform (Master Plan, "How to Read This Plan"). The hosting
provider for any hosted demo is **not decided** (Master Plan §19 is missing
from the supplied document) — see OQ-1. Until it is decided, "demo
environment" here means a clean machine or VM running the same steps as
local setup.

## 1. Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12 | Verify against what the lab machines actually run; a patch-level change needs no new ADR, a major-version change does (ADR-001) |
| Node.js | 20 LTS | Verify against the lab machines at scaffold |
| PostgreSQL | 16 | Required by Constitution Principle IV; SQLite is not a substitute |
| Git | any recent | GitHub is the remote |
| Modern desktop browser | current | Exact browser matrix to be chosen before release (architecture.md OQ-6) |

No other services are required: no Redis, no message queue, no object
storage, no email server in v1 (password reset is optional and subject to
email configuration).

## 2. Repository layout

```text
medicore-hospital-management-system/
├── backend/            # Django + DRF (config/, apps/, tests/)
├── frontend/           # React + TypeScript + Vite
├── docs/               # This guide, architecture, data model, API contract, ADRs
├── specs/              # Spec Kit feature specifications
├── .specify/           # Constitution, templates
└── .env.example        # Template only — copy to .env, never commit .env
```

Backend Django apps are created only when their scope is approved
(Master Plan §10.4). Do not create every app at initialisation.

## 3. Configuration (.env vars)

Copy `.env.example` to `.env` in the backend directory (and a separate
one for the frontend if it needs one). **Never commit `.env`** (Master Plan
§15.2). All values below are placeholders/examples, not real secrets.

### 3.1 Backend (`backend/.env`)

| Variable | Example | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | `change-me-to-a-long-random-string` | Required. Generate per environment; never reuse across environments; never commit. |
| `DEBUG` | `True` (local) / `False` (hosted) | Must be `False` in any hosted/demo environment. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Add the demo host when one exists. |
| `DATABASE_URL` | `postgres://medicore:password@localhost:5432/medicore` | PostgreSQL connection. Or discrete `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` vars if the settings use those instead — the settings file is authoritative; this table lists the values it must provide. |
| `NATIONAL_ID_HASH_SECRET` | `change-me-test-only-secret` | Required. Server-side secret for the deterministic HMAC-SHA256 of national_id (Spec 001 data-model.md). Never commit; never a per-record salt; rotating it invalidates the stored hashes — see §7. |
| `NATIONAL_ID_ENCRYPTION_KEY` | `change-me-encryption-key` | Required. Key for encrypting `national_id` at rest. Never commit. Key management/rotation is OQ-3. |
| `TIME_ZONE` | `Asia/Karachi` | Display timezone; timestamps stored in UTC (ADR-001). |
| `SESSION_COOKIE_SECURE` | `True` (hosted) / `False` (local http) | Secure HttpOnly session cookie; `True` wherever HTTPS is used. |
| `CSRF_COOKIE_SECURE` | `True` (hosted) / `False` (local http) | As above. |
| `SESSION_COOKIE_AGE` | `43200` | Session expiry in seconds — value is provisional, see OQ-4. |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | (empty by default) | Only if password reset is configured. Empty/unset means the reset endpoint is unavailable (Master Plan M01). |
| `FRONTEND_URL` | `http://localhost:5173` | Used for any links sent to users (e.g. password reset, if configured) and CORS/CSRF trusted origins. |

### 3.2 Frontend (`frontend/.env`)

| Variable | Example | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend base URL. Same-origin in the demo if the frontend is served by the same host (preferred — avoids cross-origin cookie complexity). |

## 4. Local setup (first time, clean checkout)

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in real local values
python manage.py migrate         # applies all migrations; must work from fresh
python manage.py createsuperuser # admin account for Django admin / first login
python manage.py seed_demo_data  # synthetic demo data only — see §6
python manage.py runserver       # http://localhost:8000
```

Frontend (second terminal):

```bash
cd frontend
npm install
cp .env.example .env             # if the frontend has one; set VITE_API_BASE_URL
npm run dev                      # http://localhost:5173
```

Health check: `GET http://localhost:8000/api/auth/me/` returns `401` when
signed out (proves the API is up and auth is enforced); after signing in
it returns the current user. There is no unauthenticated health endpoint
that exposes system internals — whether a dedicated `/api/health/` endpoint
exists is OQ-5.

## 5. Migrations

- Migrations are version-controlled and reproducible (Constitution IV).
- Create after a model change: `python manage.py makemigrations`, review
  the generated migration, then `python manage.py migrate`.
- Never edit an applied migration; never hand-edit the database schema.
  Fix forward with a new migration.
- Migrations must apply cleanly from a fresh setup — this is part of the
  release quality gate (Master Plan §16.3). Verify with a fresh database
  before any demo: drop/recreate the DB, run `migrate`, confirm no errors.
- Roll back one step only with `python manage.py migrate <app> <previous>`
  in development. In a demo environment, prefer restoring from backup (§7)
  over rolling migrations back.

## 6. Seed data (synthetic only)

- Command (name provisional — the implementation must provide it):
  `python manage.py seed_demo_data`.
- Seeds: roles and permissions, departments, a small staff set (one user
  per role), a handful of synthetic patients (with invented 13-digit
  national_id values), appointments, and (once those modules exist) an
  encounter, lab request, and invoice — enough to demonstrate WF-01–WF-04.
- **All seeded patient data is synthetic.** Never seed real patient
  records. Seeded data must be reset reproducibly before demonstrations
  (Master Plan §16.1): re-run the seed on a fresh database, or provide a
  `flush + seed` procedure documented with the command.
- The seed command is idempotent or refuses to run on a non-empty database
  — whichever the implementation chooses, it must be documented with the
  command; silently duplicating seed data on a second run is a bug.
- Demo accounts and their passwords are documented only in the demo run
  sheet (not in this guide, not in the repository) and use obviously
  non-production passwords.

## 7. Backup and restore

PostgreSQL only (the application stores no business data anywhere else).

Backup:

```bash
pg_dump -U medicore -h localhost -d medicore -F c -f medicore-YYYY-MM-DD.backup
```

- Store the backup file securely (it contains patient data, including
  encrypted national_id values — treat it as sensitive; do not upload it
  to any shared drive or chat).
- The backup does **not** include the `.env` secrets. The
  `NATIONAL_ID_HASH_SECRET` and `NATIONAL_ID_ENCRYPTION_KEY` must be
  backed up separately and securely by whoever owns the environment: a
  database restore without the same secrets makes the stored national_id
  values unreadable and the hashes unverifiable. Rotating either secret
  after data exists is a data-loss event for those fields unless a
  re-encryption/re-hash migration is written — do not rotate casually.

Restore:

```bash
dropdb -U medicore -h localhost medicore
createdb -U medicore -h localhost medicore
pg_restore -U medicore -h localhost -d medicore -F c medicore-YYYY-MM-DD.backup
```

- **Test the restore at least once** before release review (Master Plan
  NFR-12, §16.3): restore to a scratch database, run migrations check
  (`python manage.py migrate --check`), sign in, and confirm a seeded
  patient and an appointment are visible.
- Restore verification is part of the release quality gate; record the date
  and result in the demo run sheet.

## 8. How to run (day to day)

| Task | Command |
|---|---|
| Backend | `cd backend && source .venv/bin/activate && python manage.py runserver` |
| Frontend | `cd frontend && npm run dev` |
| Backend tests | `cd backend && python -m pytest` |
| Frontend tests | `cd frontend && npm test` (Vitest) |
| E2E tests | `cd frontend && npx playwright test` (or the repo's documented E2E command) |
| Lint/format | Per the repo's configured tools (documented in the README when chosen — see OQ-6) |

Stop conditions: if `migrate` fails, if the seed command fails, or if the
login page does not load, do not demo around the failure — fix it or record
it as a known defect with its severity (see `docs/test-strategy.md` §7).

## 9. Demo environment notes

- Same steps as §4, on a clean machine/VM, with `DEBUG=False`,
  `ALLOWED_HOSTS` set to the demo host, and HTTPS if the host supports it.
- Demo data is seeded fresh (§6) before each demonstration; the demo uses
  the seeded synthetic patients only.
- A demo run sheet (separate from this guide) should list: the demo URL,
  the seeded accounts per role, the scripted journey (WF-01 → WF-02, plus
  any included P1 flow), and the fallback (screenshots/video) if the live
  demo fails. The run sheet is a Phase 9 deliverable (Master Plan §17),
  not part of this guide.
- Do not leave a demo environment running with known critical defects, and
  do not present the demo as a certified clinical system or a
  production-ready hospital platform.

## Open Questions

- **OQ-1 — Hosting provider.** No host is decided for the demo
  environment (Master Plan §19 missing). Options (VPS, PaaS, university
  hosting) have not been evaluated; the choice affects HTTPS, static-file
  serving, and the backup schedule.
- **OQ-2 — Production server.** The WSGI server (e.g. Gunicorn) and
  static-file/HTTPS arrangement are not decided; the architecture plan
  assumes a conventional Django deployment without fixing the server.
- **OQ-3 — Encryption key management/rotation.** How the national_id
  encryption key is stored (environment variable only, or a key manager)
  and rotated is not decided. Environment-variable storage is the working
  assumption for v1.
- **OQ-4 — Session expiry length.** `SESSION_COOKIE_AGE` has no decided
  value; the 12-hour example in §3.1 is provisional.
- **OQ-5 — Health-check endpoint.** Whether a dedicated unauthenticated
  `/api/health/` endpoint exists (and what it returns) is not decided.
- **OQ-6 — Lint/format tooling.** Formatter/linter choices (e.g. Ruff/
  Black for Python, ESLint/Prettier for TypeScript) are not decided in any
  source; the README must record them once chosen.
- **OQ-7 — Seed command name and behaviour.** The command name
  `seed_demo_data` and its idempotency behaviour are provisional (see §6);
  the implementation must confirm them and amend this guide.
