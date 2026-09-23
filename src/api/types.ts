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

export interface EmployeeProfile extends EmployeeListItem {
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
  employee_id: string
  recommendations: Recommendation[]
}

export interface HRSkillGap {
  skill_id: string
  name: string
  employee_count: number
}

export interface ActivityParticipation {
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
  imported_employees?: number
  imported_history?: number
  message?: string
}

export interface CareerQuestApi {
  getEmployees(): Promise<EmployeeListItem[]>
  getEmployee(id: string): Promise<EmployeeProfile>
  getRecommendations(id: string): Promise<RecommendationsResponse>
  completeActivity(id: string, eventId: string): Promise<void>
  getHrSummary(): Promise<HRSummary>
  importData(files: { employees: File | null; history: File | null }): Promise<ImportResult>
}
