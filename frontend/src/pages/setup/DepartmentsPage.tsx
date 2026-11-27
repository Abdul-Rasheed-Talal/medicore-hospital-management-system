import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import {
  createDepartment,
  deleteDepartment,
  listDepartments,
  updateDepartment,
  type Department,
} from '@/lib/organization'
import {
  FieldError,
  SetupNav,
  firstError,
  inputClassName,
  isAdmin,
} from '@/pages/setup/common'

type Filter = 'all' | 'active' | 'inactive'

/** Departments (Spec 003 User Story 1, FR-001). Admin manages; other
 * roles read the list. Deactivating a department with active staff is
 * allowed with a warning (D-13); deleting a referenced department is
 * refused by the backend and the refusal is shown (FR-005). */
export default function DepartmentsPage() {
  const { user } = useAuth()
  const admin = isAdmin(user)
  const [departments, setDepartments] = useState<Department[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Department | null>(null)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [description, setDescription] = useState('')
  const [fieldErrors, setFieldErrors] = useState<
    Record<string, string[]> | undefined
  >()
  const [pending, setPending] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const page = await listDepartments(
        filter === 'all' ? undefined : { is_active: filter === 'active' },
      )
      setDepartments(page.results)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not load departments.')
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    void load()
  }, [load])

  function openCreate() {
    setEditing(null)
    setName('')
    setCode('')
    setDescription('')
    setFieldErrors(undefined)
    setError(null)
    setShowForm(true)
  }

  function openEdit(department: Department) {
    setEditing(department)
    setName(department.name)
    setCode(department.code)
    setDescription(department.description)
    setFieldErrors(undefined)
    setError(null)
    setShowForm(true)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setFieldErrors(undefined)
    setError(null)
    setPending(true)
    try {
      if (editing) {
        await updateDepartment(editing.id, { name, code, description })
        setNotice('Department updated.')
      } else {
        await createDepartment({ name, code, description })
        setNotice('Department created.')
      }
      setShowForm(false)
      setEditing(null)
      await load()
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        setFieldErrors(err.fieldErrors)
      } else {
        setError(err instanceof ApiError ? err.detail : 'Could not save the department.')
      }
    } finally {
      setPending(false)
    }
  }

  async function handleToggleActive(department: Department) {
    setError(null)
    setNotice(null)
    try {
      const updated = await updateDepartment(department.id, {
        is_active: !department.is_active,
      })
      if (updated.warning) setNotice(updated.warning)
      else
        setNotice(
          updated.is_active ? 'Department re-activated.' : 'Department deactivated.',
        )
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not update the department.')
    }
  }

  async function handleDelete(department: Department) {
    if (confirmDeleteId !== department.id) {
      setConfirmDeleteId(department.id)
      return
    }
    setConfirmDeleteId(null)
    setError(null)
    try {
      await deleteDepartment(department.id)
      setNotice('Department deleted.')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not delete the department.')
    }
  }

  return (
    <div>
      <SetupNav />
      <h1 className="text-2xl font-semibold">Departments</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Hospital departments. Staff, services and appointments link to these
        records.
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
            New department
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
            {editing ? 'Edit department' : 'New department'}
          </h2>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Name
            <input
              type="text"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={inputClassName}
            />
            <FieldError message={firstError(fieldErrors, 'name')} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Code
            <input
              type="text"
              required
              value={code}
              onChange={(event) => setCode(event.target.value.toUpperCase())}
              className={inputClassName}
            />
            <FieldError message={firstError(fieldErrors, 'code')} />
          </label>
          <p className="-mt-3 text-xs text-muted-foreground">
            Short uppercase code, unique — e.g. OPD, LAB.
          </p>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="min-h-16 rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
            <FieldError message={firstError(fieldErrors, 'description')} />
          </label>
          <div className="flex gap-2">
            <Button type="submit" disabled={pending}>
              {editing ? 'Save changes' : 'Create department'}
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
      ) : departments.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No departments yet. An Admin creates them here.
        </p>
      ) : (
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="py-2 pr-4 font-medium">Code</th>
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Description</th>
              <th className="py-2 pr-4 font-medium">Status</th>
              {admin && <th className="py-2 font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {departments.map((department) => (
              <tr key={department.id} className="border-b">
                <td className="py-2 pr-4 font-medium">{department.code}</td>
                <td className="py-2 pr-4">{department.name}</td>
                <td className="py-2 pr-4 text-muted-foreground">
                  {department.description || '—'}
                </td>
                <td className="py-2 pr-4">
                  {department.is_active ? 'Active' : 'Inactive'}
                </td>
                {admin && (
                  <td className="flex flex-wrap gap-1 py-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => openEdit(department)}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void handleToggleActive(department)}
                    >
                      {department.is_active ? 'Deactivate' : 'Reactivate'}
                    </Button>
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      onClick={() => void handleDelete(department)}
                    >
                      {confirmDeleteId === department.id
                        ? 'Confirm delete'
                        : 'Delete'}
                    </Button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
