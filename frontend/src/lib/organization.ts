import { api } from '@/lib/api'

/**
 * API client for hospital setup (Spec 003, M2).
 *
 * The backend is authoritative on validation (FR-007) and permissions
 * (FR-009): Admin-only mutations return 403 for other roles, and field
 * errors arrive as DRF {"field": ["message"]} payloads, parsed onto
 * ApiError.fieldErrors by the shared client.
 *
 * List endpoints are DRF-paginated (page size 20) and accept
 * ?is_active=true|false; /api/staff/ also accepts ?status=active|inactive
 * and ?available=true (the provider list appointments use, FR-013).
 */

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Department {
  id: number
  name: string
  code: string
  description: string
  is_active: boolean
  created_by: string | null
  created_at: string
  updated_at: string
  /** Present when deactivating a department that still has active staff
   * (D-13): the deactivation is allowed, with this warning. */
  warning?: string
}

export interface ServiceCategory {
  id: number
  name: string
  is_active: boolean
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface VisitType {
  id: number
  name: string
  is_active: boolean
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface Service {
  id: number
  name: string
  code: string
  category: number
  department: number | null
  is_active: boolean
  created_by: string | null
  created_at: string
  updated_at: string
}

export type StaffStatus = 'active' | 'inactive'

export interface StaffProfile {
  id: number
  staff_id: string
  full_name: string
  job_title: string
  department: number | null
  role: string
  user: number | null
  /** Visible only to Admins and to the staff member themself (Spec 003
   * Permissions table); the backend strips these fields for others. */
  phone?: string
  email?: string
  blood_group?: string | null
  status: StaffStatus
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface StaffStatusChange {
  id: number
  previous_status: StaffStatus
  new_status: StaffStatus
  reason: string
  actor: string | null
  timestamp: string
}

export interface UserOption {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
  role: string
  is_active: boolean
}

export interface DepartmentInput {
  name: string
  code: string
  description: string
}

export interface ServiceCategoryInput {
  name: string
}

export interface VisitTypeInput {
  name: string
}

export interface ServiceInput {
  name: string
  code: string
  category: number
  department: number | null
}

export interface StaffInput {
  full_name: string
  job_title: string
  department: number | null
  role: string
  user: number | null
  phone: string
  email: string
  blood_group: string | null
}

export const ROLES: { value: string; label: string }[] = [
  { value: 'admin', label: 'Admin' },
  { value: 'doctor', label: 'Doctor' },
  { value: 'nurse', label: 'Nurse' },
  { value: 'receptionist', label: 'Receptionist' },
  { value: 'lab_technician', label: 'Lab Technician' },
  { value: 'pharmacist', label: 'Pharmacist' },
  { value: 'billing', label: 'Billing' },
]

export const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

/** Clinical roles need a department (Spec 003 D-05). */
export const CLINICAL_ROLES = new Set(['doctor', 'nurse', 'lab_technician'])

export function roleLabel(role: string): string {
  return ROLES.find((r) => r.value === role)?.label ?? role
}

function query(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, value)
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

// --- Departments (FR-001) ---

export function listDepartments(params?: { is_active?: boolean }) {
  return api<Paginated<Department>>(
    `/api/departments/${query({ is_active: params?.is_active?.toString() })}`,
  )
}

export function createDepartment(data: DepartmentInput) {
  return api<Department>('/api/departments/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateDepartment(
  id: number,
  data: Partial<DepartmentInput & { is_active: boolean }>,
) {
  return api<Department>(`/api/departments/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteDepartment(id: number) {
  return api<void>(`/api/departments/${id}/`, { method: 'DELETE' })
}

// --- Service categories (FR-004) ---

export function listServiceCategories(params?: { is_active?: boolean }) {
  return api<Paginated<ServiceCategory>>(
    `/api/service-categories/${query({ is_active: params?.is_active?.toString() })}`,
  )
}

export function createServiceCategory(data: ServiceCategoryInput) {
  return api<ServiceCategory>('/api/service-categories/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateServiceCategory(
  id: number,
  data: Partial<ServiceCategoryInput & { is_active: boolean }>,
) {
  return api<ServiceCategory>(`/api/service-categories/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteServiceCategory(id: number) {
  return api<void>(`/api/service-categories/${id}/`, { method: 'DELETE' })
}

// --- Visit types (FR-004) ---

export function listVisitTypes(params?: { is_active?: boolean }) {
  return api<Paginated<VisitType>>(
    `/api/visit-types/${query({ is_active: params?.is_active?.toString() })}`,
  )
}

export function createVisitType(data: VisitTypeInput) {
  return api<VisitType>('/api/visit-types/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateVisitType(
  id: number,
  data: Partial<VisitTypeInput & { is_active: boolean }>,
) {
  return api<VisitType>(`/api/visit-types/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteVisitType(id: number) {
  return api<void>(`/api/visit-types/${id}/`, { method: 'DELETE' })
}

// --- Services (FR-004) ---

export function listServices(params?: { is_active?: boolean }) {
  return api<Paginated<Service>>(
    `/api/services/${query({ is_active: params?.is_active?.toString() })}`,
  )
}

export function createService(data: ServiceInput) {
  return api<Service>('/api/services/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateService(
  id: number,
  data: Partial<ServiceInput & { is_active: boolean }>,
) {
  return api<Service>(`/api/services/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteService(id: number) {
  return api<void>(`/api/services/${id}/`, { method: 'DELETE' })
}

// --- Staff (FR-002, FR-011) ---

export function listStaff(params?: { status?: StaffStatus }) {
  return api<Paginated<StaffProfile>>(
    `/api/staff/${query({ status: params?.status })}`,
  )
}

export function createStaff(data: StaffInput) {
  return api<StaffProfile>('/api/staff/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateStaff(
  id: number,
  data: Partial<StaffInput & { status: StaffStatus; status_reason: string }>,
) {
  return api<StaffProfile>(`/api/staff/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function getStaffStatusHistory(id: number) {
  return api<Paginated<StaffStatusChange>>(`/api/staff/${id}/status-history/`)
}

// --- Users (link a staff profile to a sign-in account, D-04/D-12) ---

export function listUsers() {
  return api<Paginated<UserOption>>('/api/users/')
}
