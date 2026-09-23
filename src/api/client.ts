import type { ActivityHistoryItem, CareerQuestApi, EmployeeListItem, EmployeeProfile, HRSummary, ImportResult, ParticipationSummary, Recommendation, RecommendationsResponse, SkillGap, SkillImpact } from './types'
import { mockApi } from '../mock/mockApi'

const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const useMocks = import.meta.env.VITE_USE_MOCKS !== 'false'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, init)
  if (!response.ok) throw new Error(`Request failed: ${response.status}`)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

interface RawEmployeeProfile extends EmployeeListItem {
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
  employee_id: string
  recommendations?: RawRecommendation[]
}

interface RawHRSummary {
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
  success?: boolean
  employees_added?: number
  history_rows_added?: number
  warnings?: string[]
}

function normalizeEmployee(raw: RawEmployeeProfile): EmployeeProfile {
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
    date: item.date || item.activity_date || new Date().toISOString(),
    status: item.status,
    completion_pct: item.completion_pct ?? item.completion_percent,
    score: item.score,
    feedback_rating: item.feedback_rating,
  }))
  const target = raw.target || raw.career_goal
  return {
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
  return {
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
  const participation: ParticipationSummary | undefined = raw.participation ? {
    total_records: raw.participation.total_records,
    unique_participants: raw.participation.unique_participants,
    status_counts: raw.participation.status_counts,
    completion_rate: raw.participation.completion_rate,
  } : undefined
  return {
    skill_gaps: (raw.most_common_unresolved_target_gaps || []).map((gap) => ({ skill_id: gap.skill_id, name: gap.skill_name, employee_count: gap.employees })),
    activity_participation: [],
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
    return { employee_id: result.employee_id, recommendations: (result.recommendations || []).map(normalizeRecommendation) } satisfies RecommendationsResponse
  },
  completeActivity: async (id, eventId) => {
    await request(`/api/employees/${id}/complete`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event_id: eventId }) })
  },
  async getHrSummary() {
    return normalizeHrSummary(await request<RawHRSummary>('/api/hr/summary'))
  },
  importData: async ({ employees, history }) => {
    const form = new FormData()
    if (employees) form.append('employees', employees)
    if (history) form.append('history', history)
    const result = await request<RawImportResult>('/api/import', { method: 'POST', body: form })
    return { imported_employees: result.employees_added, imported_history: result.history_rows_added, message: result.warnings?.join('; ') } satisfies ImportResult
  },
}

export const api: CareerQuestApi = useMocks ? mockApi : realApi
