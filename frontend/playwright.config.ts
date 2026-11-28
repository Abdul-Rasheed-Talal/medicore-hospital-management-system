import { defineConfig, devices } from '@playwright/test'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Playwright E2E (M2-T05): the first end-to-end journey runs the real
// frontend against the real Django backend in a real browser.
//
//   npm run test:e2e
//
// The two webServers below boot the backend (Django runserver on :8000,
// SQLite dev database) and the frontend (Vite dev on :5173, proxying /api
// to the backend). globalSetup migrates and seeds the E2E admin first.
// Servers already running are reused locally; CI always starts fresh.

const backendDir = path.resolve(__dirname, '..', 'backend')
const venvPython = path.join(backendDir, '.venv', 'bin', 'python')
const python = existsSync(venvPython) ? venvPython : 'python'

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup',
  timeout: 60 * 1000,
  expect: { timeout: 10 * 1000 },
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `${python} manage.py runserver 127.0.0.1:8000 --noreload`,
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/api/auth/csrf/',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
  ],
})
