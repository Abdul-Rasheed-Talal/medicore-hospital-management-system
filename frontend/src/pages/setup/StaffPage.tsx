import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import {
  BLOOD_GROUPS,
  createStaff,
  getStaffStatusHistory,
  listDepartments,
  listStaff,
  listUsers,
  roleLabel,
  updateStaff,
  ROLES,
  type Department,
  type StaffProfile,
  type StaffStatus,
  type StaffStatusChange,
  type UserOption,
} from '@/lib/organization'
import {
  FieldError,
  SetupNav,
  firstError,
  inputClassName,
  isAdmin,
} from '@/pages/setup/common'

type Filter = 'all' | StaffStatus

const STATUS_LABEL: Record<StaffStatus, string> = {
  active: 'Active',
  inactive: 'Inactive',
}

/** Staff directory (Spec 003 User Stories 2 and 5, FR-002, FR-011).
 * Admin manages profiles; other roles see the directory without contact
 * details or blood group (the backend strips those fields — Spec 003
 * Permissions table). Profiles are never deleted; a status change to
 * Inactive with a reason is the controlled alternative. */
export default function StaffPage() {
  const { user } = useAuth()
  const admin = isAdmin(user)
  const [staff, setStaff] = useState<StaffProfile[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [users, setUsers] = useState<UserOption[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<StaffProfile | null>(null)
  const [fullName, setFullName] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [role, setRole] = useState('doctor')
  const [userId, setUserId] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [bloodGroup, setBloodGroup] = useState('')
  const [status, setStatus] = useState<StaffStatus>('active')
  const [statusReason, setStatusReason] = useState('')
  const [fieldErrors, setFieldErrors] = useState<
    Record<string, string[]> | undefined
  >()
  const [pending, setPending] = useState(false)
  const [historyFor, setHistoryFor] = useState<StaffProfile | null>(null)
  const [history, setHistory] = useState<StaffStatusChange[]>([])
  const [historyError, setHistoryError] = useState<string | null>(null)

  const departmentName = useCallback(
    (id: number | null) =>
      departments.find((d) => d.id === id)?.name ?? '—',
    [departments],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [staffPage, departmentsPage] = await Promise.all([
        listStaff(filter === 'all' ? undefined : { status: filter }),
        listDepartments({ is_active: true }),
      ])
      setStaff(staffPage.results)
      setDepartments(departmentsPage.results)
      if (admin) {
        try {
          const usersPage = await listUsers()
          setUsers(usersPage.results)
        } catch {
          setUsers([])
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not load staff.')
    } finally {
      setLoading(false)
    }
  }, [filter, admin])

  useEffect(() => {
    void load()
  }, [load])

  function openCreate() {
    setEditing(null)
    setFullName('')
    setJobTitle('')
    setDepartmentId('')
    setRole('doctor')
    setUserId('')
    setPhone('')
    setEmail('')
    setBloodGroup('')
    setStatus('active')
    setStatusReason('')
    setFieldErrors(undefined)
    setError(null)
    setShowForm(true)
  }

  function openEdit(profile: StaffProfile) {
    setEditing(profile)
    setFullName(profile.full_name)
    setJobTitle(profile.job_title)
    setDepartmentId(profile.department?.toString() ?? '')
    setRole(profile.role)
    setUserId(profile.user?.toString() ?? '')
    setPhone(profile.phone ?? '')
    setEmail(profile.email ?? '')
    setBloodGroup(profile.blood_group ?? '')
    setStatus(profile.status)
    setStatusReason('')
    setFieldErrors(undefined)
    setError(null)
    setShowForm(true)
  }

  const statusChanged = editing !== null && status !== editing.status

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setFieldErrors(undefined)
    setError(null)
    if (statusChanged && statusReason.trim() === '') {
      setFieldErrors({
        status_reason: ['A reason is required when changing staff status.'],
      })
      return
    }
    setPending(true)
    try {
      const base = {
        full_name: fullName,
        job_title: jobTitle,
        department: departmentId === '' ? null : Number(departmentId),
        role,
        user: userId === '' ? null : Number(userId),
        phone,
        email,
        blood_group: bloodGroup === '' ? null : bloodGroup,
      }
      if (editing) {
        await updateStaff(editing.id, {
          ...base,
          status,
          ...(statusChanged ? { status_reason: statusReason.trim() } : {}),
        })
        setNotice('Staff profile updated.')
      } else {
        await createStaff(base)
        setNotice('Staff profile created.')
      }
      setShowForm(false)
      setEditing(null)
      await load()
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        setFieldErrors(err.fieldErrors)
      } else {
        setError(
          err instanceof ApiError ? err.detail : 'Could not save the staff profile.',
        )
      }
    } finally {
      setPending(false)
    }
  }

  async function handleHistory(profile: StaffProfile) {
    setHistoryFor(profile)
    setHistory([])
    setHistoryError(null)
    try {
      const page = await getStaffStatusHistory(profile.id)
      setHistory(page.results)
    } catch (err) {
      setHistoryError(
        err instanceof ApiError ? err.detail : 'Could not load status history.',
      )
    }
  }

  const showPhone = staff.some((s) => s.phone !== undefined)
  const showEmail = staff.some((s) => s.email !== undefined)
  const showBloodGroup = staff.some((s) => s.blood_group !== undefined)

  return (
    <div>
      <SetupNav />
      <h1 className="text-2xl font-semibold">Staff directory</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Staff profiles — the work identity for scheduling and appointments.
        Contact details are visible only to Admins and to the staff member
        themself.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-sm font-medium">
          Show
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value as Filter)}
            className={inputClassName}
          >
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
        {admin && (
          <Button type="button" onClick={openCreate}>
            New staff member
          </Button>
        )}
      </div>

      {notice && (
        <p role="status" className="mt-4 text-sm text-muted-foreground">
          {notice}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-4 text-sm text-destructive">
          {error}
        </p>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="mt-4 flex max-w-md flex-col gap-4 rounded-md border p-4"
        >
          <h2 className="text-lg font-semibold">
            {editing ? 'Edit staff profile' : 'New staff member'}
          </h2>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Full name
            <input
              type="text"
              required
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              className={inputClassName}
            />
            <FieldError message={firstError(fieldErrors, 'full_name')} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Job title
            <input
              type="text"
              required
              value={jobTitle}
              onChange={(event) => setJobTitle(event.target.value)}
              className={inputClassName}
            />
            <FieldError message={firstError(fieldErrors, 'job_title')} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Department
            <select
              value={departmentId}
              onChange={(event) => setDepartmentId(event.target.value)}
              className={inputClassName}
            >
              <option value="">No department</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
            <FieldError message={firstError(fieldErrors, 'department')} />
          </label>
          <p className="-mt-3 text-xs text-muted-foreground">
            Required for Doctor, Nurse and Lab Technician.
          </p>
          <label className="flex flex-col gap-1 text-sm font-medium">
            System role
            <select
              value={role}
              onChange={(event) => setRole(event.target.value)}
              className={inputClassName}
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
            <FieldError message={firstError(fieldErrors, 'role')} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Linked user account
            <select
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              className={inputClassName}
            >
              <option value="">No account linked</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.username} ({roleLabel(u.role)})
                </option>
              ))}
            </select>
            <FieldError message={firstError(fieldErrors, 'user')} />
          </label>
          <p className="-mt-3 text-xs text-muted-foreground">
            Optional — a profile without an account cannot sign in.
          </p>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Phone
            <input
              type="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              className={inputClassName}
            />
            <FieldError message={firstError(fieldErrors, 'phone')} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={inputClassName}
            />
            <FieldError message={firstError(fieldErrors, 'email')} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Blood group
            <select
              value={bloodGroup}
              onChange={(event) => setBloodGroup(event.target.value)}
              className={inputClassName}
            >
              <option value="">Not recorded</option>
              {BLOOD_GROUPS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
            <FieldError message={firstError(fieldErrors, 'blood_group')} />
          </label>
          {editing && (
            <label className="flex flex-col gap-1 text-sm font-medium">
              Status
              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as StaffStatus)
                }
                className={inputClassName}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
              <FieldError message={firstError(fieldErrors, 'status')} />
            </label>
          )}
          {statusChanged && (
            <label className="flex flex-col gap-1 text-sm font-medium">
              Reason for status change
              <textarea
                value={statusReason}
                onChange={(event) => setStatusReason(event.target.value)}
                className="min-h-16 rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              <FieldError message={firstError(fieldErrors, 'status_reason')} />
            </label>
          )}
          <div className="flex gap-2">
            <Button type="submit" disabled={pending}>
              {editing ? 'Save changes' : 'Create staff member'}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="mt-4 text-sm text-muted-foreground">Loading…</p>
      ) : staff.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No staff profiles yet. An Admin creates them here.
        </p>
      ) : (
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="py-2 pr-4 font-medium">Staff ID</th>
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Job title</th>
              <th className="py-2 pr-4 font-medium">Department</th>
              <th className="py-2 pr-4 font-medium">Role</th>
              {showPhone && <th className="py-2 pr-4 font-medium">Phone</th>}
              {showEmail && <th className="py-2 pr-4 font-medium">Email</th>}
              {showBloodGroup && (
                <th className="py-2 pr-4 font-medium">Blood group</th>
              )}
              <th className="py-2 pr-4 font-medium">Status</th>
              <th className="py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {staff.map((profile) => (
              <tr key={profile.id} className="border-b">
                <td className="py-2 pr-4 font-medium">{profile.staff_id}</td>
                <td className="py-2 pr-4">{profile.full_name}</td>
                <td className="py-2 pr-4">{profile.job_title}</td>
                <td className="py-2 pr-4">
                  {departmentName(profile.department)}
                </td>
                <td className="py-2 pr-4">{roleLabel(profile.role)}</td>
                {showPhone && (
                  <td className="py-2 pr-4">{profile.phone ?? '—'}</td>
                )}
                {showEmail && (
                  <td className="py-2 pr-4">{profile.email ?? '—'}</td>
                )}
                {showBloodGroup && (
                  <td className="py-2 pr-4">{profile.blood_group ?? '—'}</td>
                )}
                <td className="py-2 pr-4">{STATUS_LABEL[profile.status]}</td>
                <td className="flex flex-wrap gap-1 py-2">
                  {admin && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => openEdit(profile)}
                    >
                      Edit
                    </Button>
                  )}
                  {(admin || profile.user === user?.id) && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void handleHistory(profile)}
                    >
                      History
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {historyFor && (
        <section
          aria-label="Status history"
          className="mt-4 rounded-md border p-4"
        >
          <h2 className="text-lg font-semibold">
            Status history — {historyFor.full_name}
          </h2>
          {historyError && (
            <p role="alert" className="mt-2 text-sm text-destructive">
              {historyError}
            </p>
          )}
          {history.length === 0 && !historyError ? (
            <p className="mt-2 text-sm text-muted-foreground">
              No status changes recorded.
            </p>
          ) : (
            <ul className="mt-2 flex flex-col gap-2 text-sm">
              {history.map((change) => (
                <li key={change.id} className="border-b pb-2 last:border-0">
                  <span className="font-medium">
                    {STATUS_LABEL[change.previous_status]} →{' '}
                    {STATUS_LABEL[change.new_status]}
                  </span>
                  {' — '}
                  {change.reason}
                  <span className="text-muted-foreground">
                    {' '}
                    ({change.actor ?? '—'},{' '}
                    {new Date(change.timestamp).toLocaleString()})
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => setHistoryFor(null)}
          >
            Close
          </Button>
        </section>
      )}

      <p className="mt-4 text-sm text-muted-foreground">
        Staff profiles are never deleted, so past work keeps its author — use
        a status change to Inactive with a reason instead.
      </p>
    </div>
  )
}
