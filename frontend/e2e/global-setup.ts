import { execSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Runs once before the E2E suite: migrate the dev database and seed the
// E2E admin account (idempotent — creating it only if it is missing).
// The backend webServer may already be up; Django opens the SQLite file
// lazily, so migrating here is safe either way.

function pythonBin(): string {
  const venvPython = path.resolve(
    __dirname,
    '..',
    '..',
    'backend',
    '.venv',
    'bin',
    'python',
  )
  return existsSync(venvPython) ? venvPython : 'python'
}

export default async function globalSetup() {
  const backendDir = path.resolve(__dirname, '..', '..', 'backend')
  const python = pythonBin()
  execSync(`${python} manage.py migrate --noinput`, {
    cwd: backendDir,
    stdio: 'inherit',
  })
  const seed = readFileSync(path.resolve(__dirname, 'seed-admin.py'), 'utf8')
  execSync(`${python} manage.py shell`, {
    cwd: backendDir,
    input: seed,
    stdio: ['pipe', 'inherit', 'inherit'],
  })
}
