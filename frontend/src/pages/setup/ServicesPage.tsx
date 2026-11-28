import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import {
  createService,
  createServiceCategory,
  createVisitType,
  deleteService,
  deleteServiceCategory,
  deleteVisitType,
  listDepartments,
  listServiceCategories,
  listServices,
  listVisitTypes,
  updateService,
  updateServiceCategory,
  updateVisitType,
  type Department,
  type Service,
  type ServiceCategory,
  type VisitType,
} from '@/lib/organization'
import {
  FieldError,
  SetupNav,
  firstError,
  inputClassName,
  isAdmin,
} from '@/pages/setup/common'

type Tab = 'services' | 'categories' | 'visit-types'

interface SimpleRecord {
  id: number
  name: string
  is_active: boolean
}

/** Manager for a name-only reference list (service categories, visit
 * types). Same rules as departments: Admin manages, delete of a used
 * record is refused by the backend, deactivation hides it from new
 * selections. */
function SimpleReferenceManager({
  items,
  singular,
  createItem,
  updateItem,
  deleteItem,
  onChanged,
  admin,
}: {
  items: SimpleRecord[]
  singular: string
  createItem: (data: { name: string }) => Promise<unknown>
  updateItem: (
    id: number,
    data: { name?: string; is_active?: boolean },
  ) => Promise<unknown>
  deleteItem: (id: number) => Promise<unknown>
  onChanged: () => void
  admin: boolean
}) {
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<SimpleRecord | null>(null)
  const [name, setName] = useState('')
  const [fieldErrors, setFieldErrors] = useState<
    Record<string, string[]> | undefined
  >()
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  const capitalised = singular[0].toUpperCase() + singular.slice(1)

  function openCreate() {
    setEditing(null)
    setName('')
    setFieldErrors(undefined)
    setError(null)
    setShowForm(true)
  }

  function openEdit(record: SimpleRecord) {
    setEditing(record)
    setName(record.name)
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
        await updateItem(editing.id, { name })
        setNotice(`${capitalised} updated.`)
      } else {
        await createItem({ name })
        setNotice(`${capitalised} created.`)
      }
      setShowForm(false)
      setEditing(null)
      onChanged()
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        setFieldErrors(err.fieldErrors)
      } else {
        setError(err instanceof ApiError ? err.detail : `Could not save the ${singular}.`)
      }
    } finally {
      setPending(false)
    }
  }

  async function handleToggleActive(record: SimpleRecord) {
    setError(null)
    try {
      await updateItem(record.id, { is_active: !record.is_active })
      setNotice(
        record.is_active ? `${capitalised} deactivated.` : `${capitalised} re-activated.`,
      )
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : `Could not update the ${singular}.`)
    }
  }

  async function handleDelete(record: SimpleRecord) {
    if (confirmDeleteId !== record.id) {
      setConfirmDeleteId(record.id)
      return
    }
    setConfirmDeleteId(null)
    setError(null)
    try {
      await deleteItem(record.id)
      setNotice(`${capitalised} deleted.`)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : `Could not delete the ${singular}.`)
    }
  }

  return (
    <div>
      {admin && (
        <Button type="button" onClick={openCreate} className="mt-4">
          New {singular}
        </Button>
      )}
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
            {editing ? `Edit ${singular}` : `New ${singular}`}
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
          <div className="flex gap-2">
            <Button type="submit" disabled={pending}>
              {editing ? 'Save changes' : `Create ${singular}`}
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
      {items.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No {singular}s yet.
        </p>
      ) : (
        <table className="mt-4 w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Status</th>
              {admin && <th className="py-2 font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((record) => (
              <tr key={record.id} className="border-b">
                <td className="py-2 pr-4 font-medium">{record.name}</td>
                <td className="py-2 pr-4">
                  {record.is_active ? 'Active' : 'Inactive'}
                </td>
                {admin && (
                  <td className="flex flex-wrap gap-1 py-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => openEdit(record)}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void handleToggleActive(record)}
                    >
                      {record.is_active ? 'Deactivate' : 'Reactivate'}
                    </Button>
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      onClick={() => void handleDelete(record)}
                    >
                      {confirmDeleteId === record.id
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

/** Service catalog (Spec 003 User Story 3, FR-004). Services live on one
 * tab; their categories and the visit types live on the other two, so the
 * reference lists appointments pick from are managed in one place. No
 * price field in v1 (D-10). */
export default function ServicesPage() {
  const { user } = useAuth()
  const admin = isAdmin(user)
  const [tab, setTab] = useState<Tab>('services')
  const [services, setServices] = useState<Service[]>([])
  const [categories, setCategories] = useState<ServiceCategory[]>([])
  const [visitTypes, setVisitTypes] = useState<VisitType[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [loading, setLoading] = useState(true)
  const hasLoadedRef = useRef(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Service | null>(null)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [fieldErrors, setFieldErrors] = useState<
    Record<string, string[]> | undefined
  >()
  const [pending, setPending] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  const loadAll = useCallback(async () => {
    // Only show the full-page loading state on the first load. Reloads
    // after a create/edit/delete must not unmount the tab content — the
    // reference managers keep their success notice in local state, and
    // unmounting wipes it (M2-T05 E2E caught "Category created." never
    // appearing).
    if (!hasLoadedRef.current) setLoading(true)
    setError(null)
    try {
      const [servicesPage, categoriesPage, visitTypesPage, departmentsPage] =
        await Promise.all([
          listServices(),
          listServiceCategories(),
          listVisitTypes(),
          listDepartments({ is_active: true }),
        ])
      setServices(servicesPage.results)
      setCategories(categoriesPage.results)
      setVisitTypes(visitTypesPage.results)
      setDepartments(departmentsPage.results)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not load services.')
    } finally {
      setLoading(false)
      hasLoadedRef.current = true
    }
  }, [])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  const categoryName = (id: number) =>
    categories.find((c) => c.id === id)?.name ?? '—'
  const departmentName = (id: number | null) =>
    departments.find((d) => d.id === id)?.name ?? '—'

  /** FR-005: a deactivated category must not appear in the selection
   * list for a new service. When editing a service, its own category
   * stays offered even if deactivated, so the existing link is kept. */
  const categoryOptions = categories.filter(
    (c) => c.is_active || (editing !== null && c.id === editing.category),
  )

  function openCreate() {
    setEditing(null)
    setName('')
    setCode('')
    setCategoryId('')
    setDepartmentId('')
    setFieldErrors(undefined)
    setError(null)
    setShowForm(true)
  }

  function openEdit(service: Service) {
    setEditing(service)
    setName(service.name)
    setCode(service.code)
    setCategoryId(service.category.toString())
    setDepartmentId(service.department?.toString() ?? '')
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
      const data = {
        name,
        code,
        category: Number(categoryId),
        department: departmentId === '' ? null : Number(departmentId),
      }
      if (editing) {
        await updateService(editing.id, data)
        setNotice('Service updated.')
      } else {
        await createService(data)
        setNotice('Service created.')
      }
      setShowForm(false)
      setEditing(null)
      await loadAll()
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        setFieldErrors(err.fieldErrors)
      } else {
        setError(err instanceof ApiError ? err.detail : 'Could not save the service.')
      }
    } finally {
      setPending(false)
    }
  }

  async function handleToggleActive(service: Service) {
    setError(null)
    try {
      await updateService(service.id, { is_active: !service.is_active })
      setNotice(
        service.is_active ? 'Service deactivated.' : 'Service re-activated.',
      )
      await loadAll()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not update the service.')
    }
  }

  async function handleDelete(service: Service) {
    if (confirmDeleteId !== service.id) {
      setConfirmDeleteId(service.id)
      return
    }
    setConfirmDeleteId(null)
    setError(null)
    try {
      await deleteService(service.id)
      setNotice('Service deleted.')
      await loadAll()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Could not delete the service.')
    }
  }

  const tabClass = (active: boolean) =>
    `rounded-md px-3 py-1.5 text-sm font-medium ${
      active
        ? 'bg-primary text-primary-foreground'
        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
    }`

  return (
    <div>
      <SetupNav />
      <h1 className="text-2xl font-semibold">Services</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        The service catalog appointments pick from, grouped by category —
        plus the visit types appointments use.
      </p>

      <div aria-label="Service catalog" className="mt-4 flex gap-1">
        <button
          type="button"
          aria-pressed={tab === 'services'}
          className={tabClass(tab === 'services')}
          onClick={() => setTab('services')}
        >
          Services
        </button>
        <button
          type="button"
          aria-pressed={tab === 'categories'}
          className={tabClass(tab === 'categories')}
          onClick={() => setTab('categories')}
        >
          Categories
        </button>
        <button
          type="button"
          aria-pressed={tab === 'visit-types'}
          className={tabClass(tab === 'visit-types')}
          onClick={() => setTab('visit-types')}
        >
          Visit types
        </button>
      </div>

      {loading ? (
        <p className="mt-4 text-sm text-muted-foreground">Loading…</p>
      ) : tab === 'categories' ? (
        <SimpleReferenceManager
          items={categories}
          singular="category"
          createItem={(data) => createServiceCategory(data)}
          updateItem={(id, data) => updateServiceCategory(id, data)}
          deleteItem={(id) => deleteServiceCategory(id)}
          onChanged={() => void loadAll()}
          admin={admin}
        />
      ) : tab === 'visit-types' ? (
        <SimpleReferenceManager
          items={visitTypes}
          singular="visit type"
          createItem={(data) => createVisitType(data)}
          updateItem={(id, data) => updateVisitType(id, data)}
          deleteItem={(id) => deleteVisitType(id)}
          onChanged={() => void loadAll()}
          admin={admin}
        />
      ) : (
        <div>
          {admin && (
            <Button type="button" onClick={openCreate} className="mt-4">
              New service
            </Button>
          )}
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
                {editing ? 'Edit service' : 'New service'}
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
                Short uppercase code, unique — e.g. CONS-GEN.
              </p>
              <label className="flex flex-col gap-1 text-sm font-medium">
                Category
                <select
                  value={categoryId}
                  onChange={(event) => setCategoryId(event.target.value)}
                  className={inputClassName}
                >
                  <option value="">Select a category</option>
                  {categoryOptions.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <FieldError message={firstError(fieldErrors, 'category')} />
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
                Optional — the department that provides the service.
              </p>
              <div className="flex gap-2">
                <Button type="submit" disabled={pending}>
                  {editing ? 'Save changes' : 'Create service'}
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
          {services.length === 0 ? (
            <p className="mt-4 text-sm text-muted-foreground">
              No services yet. An Admin creates them here.
            </p>
          ) : (
            <table className="mt-4 w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th className="py-2 pr-4 font-medium">Code</th>
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Category</th>
                  <th className="py-2 pr-4 font-medium">Department</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  {admin && <th className="py-2 font-medium">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {services.map((service) => (
                  <tr key={service.id} className="border-b">
                    <td className="py-2 pr-4 font-medium">{service.code}</td>
                    <td className="py-2 pr-4">{service.name}</td>
                    <td className="py-2 pr-4">{categoryName(service.category)}</td>
                    <td className="py-2 pr-4">
                      {departmentName(service.department)}
                    </td>
                    <td className="py-2 pr-4">
                      {service.is_active ? 'Active' : 'Inactive'}
                    </td>
                    {admin && (
                      <td className="flex flex-wrap gap-1 py-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => openEdit(service)}
                        >
                          Edit
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => void handleToggleActive(service)}
                        >
                          {service.is_active ? 'Deactivate' : 'Reactivate'}
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          onClick={() => void handleDelete(service)}
                        >
                          {confirmDeleteId === service.id
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
      )}
    </div>
  )
}
