# MediCore frontend

React + TypeScript + Vite, Tailwind CSS v4 + shadcn/ui-style components.
Staff web app for the MediCore hospital management system (see the
repository README and `docs/adr/001-stack.md`).

## Run

```bash
npm install
npm run dev        # http://localhost:5173 — /api is proxied to the Django backend
```

The backend must be running on `http://localhost:8000` (see the
repository README). Auth is Django session auth: the app calls
`GET /api/auth/csrf/` before login and sends the CSRF token with
unsafe requests (see `src/lib/api.ts`).

## Test / build

```bash
npm test           # Vitest + React Testing Library
npx tsc --noEmit   # typecheck
npm run build      # typecheck + production build
```

## Layout

```text
src/
  components/
    Layout.tsx     # shared header/nav/page shell
    ui/button.tsx  # shadcn/ui-style Button (source install)
  context/
    AuthContext.tsx  # session user, login/logout
  lib/
    api.ts         # fetch client with CSRF handling
    utils.ts       # cn() class helper
  pages/
    DashboardPage.tsx  # placeholder — feature pages land with their specs
    LoginPage.tsx      # sign-in shell (session auth, no patient UI yet)
```

No feature pages exist yet: patient registration is the first feature
(Spec 001) and lands in its own PR after this scaffold.
