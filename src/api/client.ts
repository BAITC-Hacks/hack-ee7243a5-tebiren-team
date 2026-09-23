import type { ActivityHistoryItem, CareerQuestApi, EmployeeListItem, EmployeeProfile, HRSummary, ImportResult, ParticipationSummary, Recommendation, RecommendationsResponse, SkillGap, SkillImpact } from './types'
import { mockApi } from '../mock/mockApi'
import type { SessionUser, EmployeePageResult, NoStepEmployee, CompletionResult } from './types'
import { validDevelopmentSummary } from '../gamification/achievements'

const baseUrl = import.meta.env.VITE_API_URL || ''
export const useMocks = import.meta.env.VITE_USE_MOCKS === 'true'
let csrfToken = ''

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

export function errorMessage(error: unknown) { return error instanceof Error ? error.message : 'Something went wrong. Please retry.' }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Recover after a development hot reload without storing the token in localStorage.
  if (init?.method === 'POST' && path !== '/api/auth/login' && !csrfToken) {
    try {
      const user = await request<SessionUser>('/api/auth/me')
      csrfToken = user.csrf_token
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) window.dispatchEvent(new Event('cq-session-expired'))
      throw error
    }
  }
  let response: Response
  try {
    response = await fetch(`${baseUrl}${path}`, { ...init, credentials: 'include', headers: { 'X-Requested-With': 'CareerQuest', ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}), ...init?.headers } })
  } catch { throw new ApiError('Cannot reach the server. Check your connection and retry.', 0) }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = body.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((e: {msg: string}) => e.msg).join('; ') : detail?.message ? `${detail.file ? detail.file + ': ' : ''}${detail.row ? 'row ' + detail.row + ': ' : ''}${detail.message}` : `Request failed (${response.status})`
    if (response.status === 401 && !path.startsWith('/api/auth')) window.dispatchEvent(new Event('cq-session-expired'))
    throw new ApiError(message, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

interface RawEmployeeProfile extends EmployeeListItem {
  development_summary?: unknown
  dataset_as_of?: string
  department?: string
  tenure_months: number
  work_format?: string
  preferred_language?: string
  last_review_date?: string
  career_goal?: { target_role?: string; target_grade?: string; role?: string; grade?: string } | null
  target?: { role?: string; grade?: string } | null
  effective_skills?: Record<string, number>
  required_target_skills?: Record<string, number>
  skill_gaps?: Array<{ skill_id: string; skill_name?: string; name?: string; current: number; required: number; gap: number; critical?: boolean }>
  critical_skills?: string[]
  career_progress?: number | null
  recent_activity_history?: RawHistoryItem[]
  history?: RawHistoryItem[]
}

interface RawHistoryItem {
  record_id?: string
  event_id?: string
  title?: string
  activity_title?: string
  event_title?: string
  date?: string
  activity_date?: string
  status: ActivityHistoryItem['status']
  completion_pct?: number
  completion_percent?: number
  score?: number
  feedback_rating?: number
}

interface RawRecommendation extends Omit<Recommendation, 'type' | 'format' | 'duration_hours' | 'skill_impacts'> {
  type?: string
  format?: string
  duration_hours?: number
  skill_impacts?: Array<{ skill_id: string; skill_name?: string; name?: string; before: number; after_if_completed?: number; after?: number; required: number; critical?: boolean }>
  score_breakdown?: Record<string, number | string>
  explanation?: string
  explanation_source?: string
}

interface RawRecommendationsResponse {
  reason?: string | null
  reason_code?: string | null
  employee_id: string
  recommendations?: RawRecommendation[]
}

interface RawHRSummary {
  activity_participation?: HRSummary['activity_participation']
  total_employees?: number
  most_common_unresolved_target_gaps?: Array<{ skill_id: string; skill_name: string; employees: number; critical_for_target?: number }>
  participation?: {
    total_records: number
    unique_participants: number
    status_counts: Record<string, number>
    completion_rate: number
  }
  employees_with_no_valid_next_step?: number
}

interface RawImportResult {
  imported_employee_ids?: string[]
  success?: boolean
  employees_added?: number
  history_rows_added?: number
  warnings?: string[]
}

function normalizeEmployee(raw: RawEmployeeProfile): EmployeeProfile {
  if (!raw.employee_id || !raw.full_name || !raw.dataset_as_of || !Array.isArray(raw.skill_gaps) ||
      !Array.isArray(raw.recent_activity_history) || !Object.hasOwn(raw, 'career_progress')) {
    throw new Error('Invalid profile response. Check that frontend and backend versions match.')
  }
  if (!validDevelopmentSummary(raw.development_summary)) {
    throw new Error('Achievement data is missing or invalid. Restart the updated backend and retry.')
  }
  const criticalIds = new Set(raw.critical_skills || [])
  const skills: SkillGap[] = (raw.skill_gaps || []).map((skill) => ({
    skill_id: skill.skill_id,
    name: skill.skill_name || skill.name || skill.skill_id,
    current: skill.current,
    required: skill.required,
    gap: skill.gap,
    critical: skill.critical ?? criticalIds.has(skill.skill_id),
  }))
  const history = (raw.recent_activity_history || raw.history || []).map((item, index): ActivityHistoryItem => ({
    record_id: item.record_id || `history-${raw.employee_id}-${index}`,
    event_id: item.event_id || 'unknown',
    title: item.title || item.activity_title || item.event_title,
    date: item.date || item.activity_date || '',
    status: item.status,
    completion_pct: item.completion_pct ?? item.completion_percent,
    score: item.score,
    feedback_rating: item.feedback_rating,
  }))
  const target = raw.target || raw.career_goal
  return {
    dataset_as_of: raw.dataset_as_of,
    development_summary: raw.development_summary,
    employee_id: raw.employee_id,
    full_name: raw.full_name,
    department: raw.department,
    role: raw.role,
    grade: raw.grade,
    tenure_months: raw.tenure_months,
    work_format: raw.work_format,
    preferred_language: raw.preferred_language,
    last_review_date: raw.last_review_date,
    effective_skills: raw.effective_skills,
    required_target_skills: raw.required_target_skills,
    target: target?.role && target.grade ? { role: target.role, grade: target.grade } : null,
    progress: raw.career_progress ?? null,
    skills,
    history,
  }
}

function normalizeRecommendation(raw: RawRecommendation): Recommendation {
  if (!raw.event_id || !raw.title || !Array.isArray(raw.reasons) || raw.reasons.length < 3 ||
      !Array.isArray(raw.skill_impacts) || !Array.isArray(raw.evidence)) {
    throw new Error('Invalid recommendation response. Please update the backend and retry.')
  }
  return {
    rank: raw.rank,
    evidence: raw.evidence,
    event_id: raw.event_id,
    title: raw.title,
    description: raw.description,
    type: raw.type || 'development activity',
    format: raw.format,
    duration_hours: raw.duration_hours,
    next_session: raw.next_session,
    score: raw.score,
    reasons: raw.reasons || (raw.explanation ? [raw.explanation] : []),
    explanation: raw.explanation,
    explanation_source: raw.explanation_source,
    score_breakdown: raw.score_breakdown,
    skill_impacts: (raw.skill_impacts || []).map((impact): SkillImpact => ({
      skill_id: impact.skill_id,
      name: impact.skill_name || impact.name || impact.skill_id,
      before: impact.before,
      after: impact.after_if_completed ?? impact.after ?? impact.before,
      required: impact.required,
      critical: impact.critical,
    })),
  }
}

function normalizeHrSummary(raw: RawHRSummary): HRSummary {
  if (!Array.isArray(raw.activity_participation) || !Array.isArray(raw.most_common_unresolved_target_gaps) ||
      !raw.participation || typeof raw.employees_with_no_valid_next_step !== 'number') {
    throw new Error('Invalid HR response. Check that frontend and backend versions match.')
  }
  const participation: ParticipationSummary | undefined = raw.participation ? {
    total_records: raw.participation.total_records,
    unique_participants: raw.participation.unique_participants,
    status_counts: raw.participation.status_counts,
    completion_rate: raw.participation.completion_rate,
  } : undefined
  return {
    skill_gaps: (raw.most_common_unresolved_target_gaps || []).map((gap) => ({ skill_id: gap.skill_id, name: gap.skill_name, employee_count: gap.employees })),
    activity_participation: raw.activity_participation || [],
    employees_without_recommendations: [],
    employees_without_recommendations_count: raw.employees_with_no_valid_next_step || 0,
    participation_summary: participation,
  }
}

const realApi: CareerQuestApi = {
  async getEmployees() {
    const result = await request<{ employees: EmployeeListItem[] }>('/api/employees')
    return result.employees
  },
  async getEmployee(id) {
    return normalizeEmployee(await request<RawEmployeeProfile>(`/api/employees/${id}`))
  },
  async getRecommendations(id) {
    const result = await request<RawRecommendationsResponse>(`/api/employees/${id}/recommendations`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ max_recommendations: 3 }) })
    if (!Array.isArray(result.recommendations)) throw new Error('Invalid recommendations response')
    return { employee_id: result.employee_id, recommendations: result.recommendations.map(normalizeRecommendation), reason: result.reason, reason_code: result.reason_code } satisfies RecommendationsResponse
  },
  completeActivity: async (id, eventId, idempotencyKey) => {
    return request<CompletionResult>(`/api/employees/${id}/complete`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...(idempotencyKey ? {'Idempotency-Key': idempotencyKey} : {}) }, body: JSON.stringify({ event_id: eventId }) })
  },
  async getHrSummary() {
    return normalizeHrSummary(await request<RawHRSummary>('/api/hr/summary'))
  },
  importData: async ({ employees, history }) => {
    const form = new FormData()
    if (employees) form.append('employees', employees)
    if (history) form.append('history', history)
    const result = await request<RawImportResult>('/api/import', { method: 'POST', body: form })
    return { imported_employees: result.employees_added, imported_history: result.history_rows_added, message: result.warnings?.join('; '), warnings: result.warnings, imported_employee_ids: result.imported_employee_ids } satisfies ImportResult
  },
}

export const api: CareerQuestApi = useMocks ? mockApi : realApi

const mockUser: SessionUser = {username: 'Mock preview', role: 'hr', employee_id: null, csrf_token: ''}
export const authApi = {
  async me() {
    const user = useMocks ? mockUser : await request<SessionUser>('/api/auth/me')
    csrfToken = user.csrf_token
    return user
  },
  async login(username: string, password: string) {
    const user = await request<SessionUser>('/api/auth/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username, password})})
    csrfToken = user.csrf_token
    return user
  },
  async logout() { if (!useMocks) await request('/api/auth/logout', {method:'POST'}); csrfToken = '' },
}

export async function getEmployeePage(search = '', offset = 0): Promise<EmployeePageResult> {
  if (useMocks) {
    const employees = (await mockApi.getEmployees()).filter(e => `${e.full_name} ${e.employee_id} ${e.role}`.toLowerCase().includes(search.toLowerCase()))
    return {employees: employees.slice(offset, offset+30), total: employees.length, limit: 30, offset}
  }
  const page = await request<EmployeePageResult>(`/api/employees?search=${encodeURIComponent(search)}&limit=30&offset=${offset}`)
  if (!Array.isArray(page.employees) || typeof page.total !== 'number') throw new Error('Invalid employee list response')
  return page
}

export async function getNoStepPage(offset = 0): Promise<{employees: NoStepEmployee[]; total: number; limit: number; offset: number}> {
  if (useMocks) {
    const s = await mockApi.getHrSummary()
    return {employees: s.employees_without_recommendations.map(e=>({...e, reason:'No eligible next step'})), total:s.employees_without_recommendations.length, limit:20, offset:0}
  }
  const page = await request<{employees: NoStepEmployee[]; total: number; limit: number; offset: number}>(`/api/hr/employees-without-next-step?limit=20&offset=${offset}`)
  if (!Array.isArray(page.employees) || typeof page.total !== 'number') throw new Error('Invalid HR employee list response')
  return page
}

export async function resetDemo() { if (useMocks) throw new Error('Reset is available with the backend'); return request('/api/reset', {method:'POST'}) }
