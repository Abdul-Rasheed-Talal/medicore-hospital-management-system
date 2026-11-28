# End-to-end tests (Playwright)

The first E2E journey (`organization.spec.ts`) signs in as an Admin and
sets up the hospital — department, staff member, service — in a real
browser against the real Django backend.

## Run

From `frontend/`:

```sh
npm run test:e2e
```

One command is enough. Playwright boots both servers itself (Django
runserver on :8000, Vite dev on :5173), runs migrations, and seeds the
E2E admin account (`e2e/global-setup.ts` + `e2e/seed-admin.py`). The
browsers are installed with `npx playwright install chromium`.

To run against servers you already started yourself, start them first
and run the same command — the running servers are reused.

## Seeded account

The journey signs in as the seeded E2E admin. Override it with
environment variables (the password is test-only, for the local/CI
throwaway database):

```sh
E2E_ADMIN_USERNAME=e2e-admin E2E_ADMIN_PASSWORD=<a test password> npm run test:e2e
```

Created records are named with a per-run suffix, so the journey can run
twice against the same dev database without duplicate-code errors.
