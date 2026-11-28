/**
 * First Playwright E2E journey (M2-T05, Spec 003 SC-001): an Admin signs
 * in and sets up the hospital — department, staff profile, service — in
 * a real browser against the real backend.
 *
 * Run it with one command from frontend/:
 *
 *   npm run test:e2e
 *
 * That boots the backend (Django runserver :8000, SQLite dev database)
 * and the frontend (Vite dev :5173), migrates, and seeds the E2E admin
 * (see e2e/global-setup.ts and e2e/seed-admin.py). Override the seeded
 * account with E2E_ADMIN_USERNAME / E2E_ADMIN_PASSWORD.
 *
 * Records are named with a per-run suffix so the journey can run twice
 * against the same dev database without hitting duplicate-code errors.
 */

import { expect, test } from '@playwright/test'

const ADMIN_USERNAME = process.env.E2E_ADMIN_USERNAME ?? 'e2e-admin'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'E2EAdminPass123'

test('admin sets up the hospital: department, staff member, service', async ({
  page,
}) => {
  const suffix = Date.now().toString().slice(-6)
  const deptName = `E2E Outpatient ${suffix}`
  const deptCode = `E2E${suffix}`
  const staffName = `E2E Dr ${suffix}`
  const categoryName = `E2E Consultation ${suffix}`
  const serviceName = `E2E General Consultation ${suffix}`
  const serviceCode = `E2E-SVC-${suffix}`

  // Sign in as the seeded E2E admin.
  await page.goto('/login')
  await page.getByLabel('Username or email').fill(ADMIN_USERNAME)
  await page.getByLabel('Password').fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(
    page.getByRole('heading', { name: `Welcome, ${ADMIN_USERNAME}` }),
  ).toBeVisible()

  // 1. Department.
  await page.goto('/setup/departments')
  await page.getByRole('button', { name: 'New department' }).click()
  await page.getByLabel('Name').fill(deptName)
  await page.getByLabel('Code').fill(deptCode)
  await page.getByLabel('Description').fill('E2E test department')
  await page.getByRole('button', { name: 'Create department' }).click()
  await expect(page.getByRole('status')).toHaveText('Department created.')
  await expect(page.getByRole('cell', { name: deptName })).toBeVisible()

  // 2. Staff member in that department.
  await page.goto('/setup/staff')
  await page.getByRole('button', { name: 'New staff member' }).click()
  await page.getByLabel('Full name').fill(staffName)
  await page.getByLabel('Job title').fill('Consultant Physician')
  await page
    .getByLabel('Department')
    .selectOption({ label: `${deptName} (${deptCode})` })
  await page.getByLabel('System role').selectOption('doctor')
  await page.getByRole('button', { name: 'Create staff member' }).click()
  await expect(page.getByRole('status')).toHaveText('Staff profile created.')
  await expect(page.getByRole('cell', { name: staffName })).toBeVisible()

  // 3. Service — a category must exist first.
  await page.goto('/setup/services')
  await page.getByRole('button', { name: 'Categories' }).click()
  await page.getByRole('button', { name: 'New category' }).click()
  await page.getByLabel('Name').fill(categoryName)
  await page.getByRole('button', { name: 'Create category' }).click()
  await expect(page.getByRole('status')).toHaveText('Category created.')
  await page.getByRole('button', { name: 'Services' }).click()
  await page.getByRole('button', { name: 'New service' }).click()
  await page.getByLabel('Name').fill(serviceName)
  await page.getByLabel('Code').fill(serviceCode)
  await page.getByLabel('Category').selectOption({ label: categoryName })
  await page
    .getByLabel('Department')
    .selectOption({ label: `${deptName} (${deptCode})` })
  await page.getByRole('button', { name: 'Create service' }).click()
  await expect(page.getByRole('status')).toHaveText('Service created.')
  await expect(page.getByRole('cell', { name: serviceName })).toBeVisible()
})
