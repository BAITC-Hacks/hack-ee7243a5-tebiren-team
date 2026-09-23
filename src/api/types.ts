export type ActivityStatus = 'completed' | 'in_progress' | 'dropped' | 'no_show' | 'declined' | 'overdue'

export interface EmployeeListItem {
  employee_id: string
  full_name: string
  department?: string
  role: string
  grade: string
}

export interface CareerTarget {
  role: string
  grade: string
}

export interface SkillGap {
  skill_id: string
  name: string
  current: number
  required: number
  gap: number
  critical: boolean
}

export interface ActivityHistoryItem {
  record_id: string
  event_id: string
  title?: string
  date: string
  status: ActivityStatus
  completion_pct?: number
  score?: number
  feedback_rating?: number
}

export interface DevelopmentSummary {
  completed_unique_activities: number
}

export interface EmployeeProfile extends EmployeeListItem {
  development_summary: DevelopmentSummary
  dataset_as_of?: string
  tenure_months: number
  work_format?: string
  preferred_language?: string
  last_review_date?: string
  effective_skills?: Record<string, number>
  required_target_skills?: Record<string, number>
  target: CareerTarget | null
  progress: number | null
  skills: SkillGap[]
  history: ActivityHistoryItem[]
}

export interface SkillImpact {
  skill_id: string
  name: string
  before: number
  after: number
  required: number
  critical?: boolean
}

export interface Recommendation {
  rank?: number
  evidence?: Array<{ id: string; factor: string; text: string }>
  event_id: string
  title: string
  description?: string
  type: string
  format?: string
  duration_hours?: number
  next_session?: string
  score?: number
  reasons: string[]
  skill_impacts: SkillImpact[]
  explanation?: string
  explanation_source?: string
  score_breakdown?: Record<string, number | string>
}

export interface RecommendationsResponse {
  reason?: string | null
  reason_code?: string | null
  employee_id: string
  recommendations: Recommendation[]
}

export interface HRSkillGap {
  skill_id: string
  name: string
  employee_count: number
}

export interface ActivityParticipation {
  unique_participants?: number
  event_id: string
  title: string
  completed: number
  in_progress: number
  dropped: number
  no_show: number
  declined: number
  overdue: number
}

export interface HRSummary {
  skill_gaps: HRSkillGap[]
  activity_participation: ActivityParticipation[]
  employees_without_recommendations: EmployeeListItem[]
  employees_without_recommendations_count?: number
  participation_summary?: ParticipationSummary
}

export interface ParticipationSummary {
  total_records: number
  unique_participants: number
  status_counts: Record<string, number>
  completion_rate: number
}

export interface ImportResult {
  imported_employee_ids?: string[]
  warnings?: string[]
  imported_employees?: number
  imported_history?: number
  message?: string
}

export interface CareerQuestApi {
  getEmployees(): Promise<EmployeeListItem[]>
  getEmployee(id: string): Promise<EmployeeProfile>
  getRecommendations(id: string): Promise<RecommendationsResponse>
  completeActivity(id: string, eventId: string, idempotencyKey?: string): Promise<CompletionResult | void>
  getHrSummary(): Promise<HRSummary>
  importData(files: { employees: File | null; history: File | null }): Promise<ImportResult>
}

export interface CompletionResult {
  development_summary?: DevelopmentSummary | null
  progress_before: number | null
  progress_after: number | null
  updated_skills: Array<{ skill_id: string; skill_name?: string; before: number; after: number }>
}

export interface SessionUser {
  username: string
  role: 'hr' | 'employee'
  employee_id: string | null
  csrf_token: string
}

export interface EmployeePageResult {
  employees: EmployeeListItem[]
  total: number
  limit: number
  offset: number
}

export interface NoStepEmployee extends EmployeeListItem {
  target?: CareerTarget | null
  reason: string
  reason_code?: string
}
