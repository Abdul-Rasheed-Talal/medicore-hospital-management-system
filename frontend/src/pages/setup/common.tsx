import { NavLink } from 'react-router-dom'
import type { SessionUser } from '@/context/AuthContext'

/** Shared bits for the hospital-setup pages (Spec 003, M2). */

/** Tailwind classes for form inputs, matching LoginPage. */
export const inputClassName =
  'h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring'

export const selectClassName = inputClassName

/** The backend is authoritative on permissions (FR-009); the frontend
 * only hides mutation controls. The session role is the stored value
 * ('admin', 'doctor', …). */
export function isAdmin(user: SessionUser | null): boolean {
  return user?.role === 'admin'
}

/** One field's backend error, rendered under its input. */
export function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return (
    <p role="alert" className="text-sm text-destructive">
      {message}
    </p>
  )
}

export function firstError(
  fieldErrors: Record<string, string[]> | undefined,
  field: string,
): string | undefined {
  return fieldErrors?.[field]?.[0]
}

/** Sub-navigation shared by the three setup pages. */
export function SetupNav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-sm font-medium ${
      isActive
        ? 'bg-primary text-primary-foreground'
        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
    }`
  return (
    <nav aria-label="Hospital setup" className="mb-4 flex gap-1">
      <NavLink to="/setup/departments" className={linkClass}>
        Departments
      </NavLink>
      <NavLink to="/setup/staff" className={linkClass}>
        Staff
      </NavLink>
      <NavLink to="/setup/services" className={linkClass}>
        Services
      </NavLink>
    </nav>
  )
}
