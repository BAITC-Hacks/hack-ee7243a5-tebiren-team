import type { CareerQuestApi, EmployeeListItem, EmployeeProfile, HRSummary, RecommendationsResponse } from '../api/types'

const wait = (ms = 450) => new Promise((resolve) => setTimeout(resolve, ms))

const employeeRows: EmployeeListItem[] = [
  { employee_id: 'E0002', full_name: 'Arman Zhaksylykov', department: 'Backend Development', role: 'Backend Engineer', grade: 'Middle' },
  { employee_id: 'E0004', full_name: 'Nikita Smirnov', department: 'Data & Analytics', role: 'Data Analyst', grade: 'Middle' },
  { employee_id: 'E0001', full_name: 'Marat Yessenov', department: 'Backend Development', role: 'Backend Engineer', grade: 'Junior' },
  { employee_id: 'E0007', full_name: 'Kanat Tulegenov', department: 'Backend Development', role: 'Backend Engineer', grade: 'Senior' },
  { employee_id: 'E0014', full_name: 'Yulia Kuznetsova', department: 'Human Resources', role: 'HR Business Partner', grade: 'Lead' },
  { employee_id: 'E0018', full_name: 'Aigerim Sarsenova', department: 'Product Management', role: 'Product Manager', grade: 'Middle' },
]

const profileStore: Record<string, EmployeeProfile> = {
  E0002: {
    ...employeeRows[0], tenure_months: 41, work_format: 'remote', preferred_language: 'ru', last_review_date: '2026-07-23', target: { role: 'Backend Engineer', grade: 'Senior' }, progress: 64,
    skills: [
      { skill_id: 'SK_SYSTEM_DESIGN', name: 'System Design', current: 2, required: 4, gap: 2, critical: true },
      { skill_id: 'SK_API_DESIGN', name: 'API Design', current: 2, required: 4, gap: 2, critical: true },
      { skill_id: 'SK_CLOUD', name: 'Cloud Architecture', current: 2, required: 3, gap: 1, critical: false },
      { skill_id: 'SK_MENTORING', name: 'Mentoring', current: 1, required: 3, gap: 2, critical: false },
    ],
    history: [
      { record_id: 'R-201', event_id: 'EV_021', title: 'API Design Lab', date: '2026-08-12', status: 'completed', completion_pct: 100, score: 82, feedback_rating: 5 },
      { record_id: 'R-198', event_id: 'EV_014', title: 'Peer Code Review Circle', date: '2026-07-18', status: 'in_progress', completion_pct: 60 },
      { record_id: 'R-176', event_id: 'EV_009', title: 'Cloud Foundations', date: '2026-04-05', status: 'dropped', completion_pct: 35, feedback_rating: 3 },
    ],
  },
  E0004: {
    ...employeeRows[1], tenure_months: 59, work_format: 'office', preferred_language: 'ru', last_review_date: '2026-01-12', target: { role: 'Product Manager', grade: 'Middle' }, progress: 48,
    skills: [
      { skill_id: 'SK_PRODUCT_DISCOVERY', name: 'Product Discovery', current: 1, required: 3, gap: 2, critical: true },
      { skill_id: 'SK_PRODUCT_ANALYTICS', name: 'Product Analytics', current: 2, required: 3, gap: 1, critical: true },
      { skill_id: 'SK_STAKEHOLDER_MGMT', name: 'Stakeholder Management', current: 2, required: 3, gap: 1, critical: false },
      { skill_id: 'SK_ROADMAPPING', name: 'Roadmapping', current: 1, required: 2, gap: 1, critical: false },
    ],
    history: [{ record_id: 'R-180', event_id: 'EV_032', title: 'Analytics for Product Decisions', date: '2026-05-09', status: 'completed', completion_pct: 100, score: 74, feedback_rating: 4 }],
  },
  E0001: {
    ...employeeRows[2], tenure_months: 5, work_format: 'office', preferred_language: 'kk', last_review_date: '2026-09-11', target: { role: 'Backend Engineer', grade: 'Middle' }, progress: 38,
    skills: [{ skill_id: 'SK_API_DESIGN', name: 'API Design', current: 1, required: 3, gap: 2, critical: true }, { skill_id: 'SK_CLOUD', name: 'Cloud Architecture', current: 1, required: 2, gap: 1, critical: false }, { skill_id: 'SK_PYTHON', name: 'Python', current: 3, required: 3, gap: 0, critical: false }, { skill_id: 'SK_TEAMWORK', name: 'Teamwork', current: 2, required: 3, gap: 1, critical: false }],
    history: [],
  },
  E0007: {
    ...employeeRows[3], tenure_months: 95, work_format: 'office', preferred_language: 'kk', last_review_date: '2026-07-31', target: { role: 'Backend Engineer', grade: 'Lead' }, progress: 81,
    skills: [{ skill_id: 'SK_LEADERSHIP', name: 'Leadership', current: 2, required: 4, gap: 2, critical: true }, { skill_id: 'SK_MENTORING', name: 'Mentoring', current: 3, required: 4, gap: 1, critical: true }, { skill_id: 'SK_OBSERVABILITY', name: 'Observability', current: 1, required: 4, gap: 3, critical: false }, { skill_id: 'SK_SYSTEM_DESIGN', name: 'System Design', current: 4, required: 5, gap: 1, critical: false }],
    history: [{ record_id: 'R-176', event_id: 'EV_009', title: 'Cloud Foundations', date: '2026-04-05', status: 'no_show', completion_pct: 0 }],
  },
  E0014: {
    ...employeeRows[4], tenure_months: 83, work_format: 'office', preferred_language: 'en', last_review_date: '2026-06-02', target: { role: 'Product Manager', grade: 'Lead' }, progress: 72,
    skills: [{ skill_id: 'SK_PRODUCT_DISCOVERY', name: 'Product Discovery', current: 3, required: 5, gap: 2, critical: true }, { skill_id: 'SK_LEADERSHIP', name: 'Leadership', current: 5, required: 4, gap: 0, critical: false }, { skill_id: 'SK_STAKEHOLDER_MGMT', name: 'Stakeholder Management', current: 3, required: 5, gap: 2, critical: false }, { skill_id: 'SK_COMMUNICATION', name: 'Communication', current: 5, required: 5, gap: 0, critical: false }],
    history: [{ record_id: 'R-121', event_id: 'EV_041', title: 'Leadership Mentoring', date: '2026-03-21', status: 'completed', completion_pct: 100, score: 91, feedback_rating: 5 }],
  },
  E0018: {
    ...employeeRows[5], tenure_months: 29, work_format: 'hybrid', preferred_language: 'en', last_review_date: '2026-08-03', target: null, progress: null,
    skills: [{ skill_id: 'SK_PRODUCT_ANALYTICS', name: 'Product Analytics', current: 3, required: 0, gap: 0, critical: false }, { skill_id: 'SK_COMMUNICATION', name: 'Communication', current: 4, required: 0, gap: 0, critical: false }],
    history: [{ record_id: 'R-098', event_id: 'EV_012', title: 'Product Metrics Deep Dive', date: '2026-02-16', status: 'declined', completion_pct: 0 }],
  },
}

const recommendations: Record<string, RecommendationsResponse> = {
  E0002: { employee_id: 'E0002', recommendations: [{ event_id: 'EV_007', title: 'System Design Mentoring', description: 'Pair with a senior architect to practice turning product constraints into resilient service boundaries.', type: 'mentoring', format: 'online', duration_hours: 8, next_session: '2026-10-23', score: 0.87, reasons: ['System Design is 2 while Senior requires 4', 'System Design is critical for the target grade', 'This activity increases System Design by 1', 'Your previous participation history supports this format'], skill_impacts: [{ skill_id: 'SK_SYSTEM_DESIGN', name: 'System Design', before: 2, after: 3, required: 4 }] }, { event_id: 'EV_014', title: 'Peer Code Review Circle', description: 'A focused weekly practice group for architectural trade-offs and API boundaries.', type: 'workshop', format: 'hybrid', duration_hours: 6, next_session: '2026-10-28', score: 0.72, reasons: ['API Design is below the target requirement', 'The format builds on your current in-progress activity', 'Peers provide feedback on real production decisions'], skill_impacts: [{ skill_id: 'SK_API_DESIGN', name: 'API Design', before: 2, after: 3, required: 4 }] }] },
  E0004: { employee_id: 'E0004', recommendations: [{ event_id: 'EV_035', title: 'Product Discovery Sprint', description: 'Work through a real customer problem from interview notes to an opportunity brief.', type: 'workshop', format: 'in_person', duration_hours: 12, next_session: '2026-10-19', score: 0.84, reasons: ['Product Discovery is 1 while Middle requires 3', 'Product Discovery is critical for the target role', 'The sprint creates evidence in your cross-role transition'], skill_impacts: [{ skill_id: 'SK_PRODUCT_DISCOVERY', name: 'Product Discovery', before: 1, after: 2, required: 3 }] }] },
  E0001: { employee_id: 'E0001', recommendations: [{ event_id: 'EV_021', title: 'API Design Lab', description: 'A practical lab for writing consistent, observable APIs with clear contracts.', type: 'workshop', format: 'online', duration_hours: 5, next_session: '2026-10-14', score: 0.79, reasons: ['API Design is the largest current gap', 'API Design is critical for the target grade', 'The lab gives a fast practice loop for a new engineer'], skill_impacts: [{ skill_id: 'SK_API_DESIGN', name: 'API Design', before: 1, after: 2, required: 3 }] }] },
  E0007: { employee_id: 'E0007', recommendations: [{ event_id: 'EV_041', title: 'Leadership Mentoring', description: 'A guided practice series for leading through influence and developing other engineers.', type: 'mentoring', format: 'hybrid', duration_hours: 10, next_session: '2026-10-30', score: 0.81, reasons: ['Leadership is 2 while Lead requires 4', 'Leadership is critical for the target grade', 'The format builds on your mentoring strength'], skill_impacts: [{ skill_id: 'SK_LEADERSHIP', name: 'Leadership', before: 2, after: 3, required: 4 }] }] },
  E0014: { employee_id: 'E0014', recommendations: [{ event_id: 'EV_050', title: 'Product Strategy Case Lab', description: 'Translate a people challenge into a measurable product strategy and roadmap.', type: 'case_lab', format: 'online', duration_hours: 10, next_session: '2026-11-04', score: 0.68, reasons: ['Product Discovery is 3 while Lead requires 5', 'Product Discovery is critical for the target role', 'Your stakeholder experience transfers well into this case format'], skill_impacts: [{ skill_id: 'SK_PRODUCT_DISCOVERY', name: 'Product Discovery', before: 3, after: 4, required: 5 }] }] },
}

const hrSummary: HRSummary = {
  skill_gaps: [{ skill_id: 'SK_SYSTEM_DESIGN', name: 'System Design', employee_count: 42 }, { skill_id: 'SK_PUBLIC_SPEAKING', name: 'Public Speaking', employee_count: 31 }, { skill_id: 'SK_LEADERSHIP', name: 'Leadership', employee_count: 26 }, { skill_id: 'SK_STAKEHOLDER_MGMT', name: 'Stakeholder Management', employee_count: 22 }],
  activity_participation: [{ event_id: 'EV_007', title: 'System Design Mentoring', completed: 41, in_progress: 7, dropped: 5, no_show: 3, declined: 1, overdue: 0 }, { event_id: 'EV_041', title: 'Leadership Mentoring', completed: 28, in_progress: 5, dropped: 4, no_show: 7, declined: 3, overdue: 1 }, { event_id: 'EV_035', title: 'Product Discovery Sprint', completed: 24, in_progress: 8, dropped: 2, no_show: 4, declined: 2, overdue: 2 }],
  employees_without_recommendations: [{ ...employeeRows[5], full_name: 'Aigerim Sarsenova' }, { employee_id: 'E0027', full_name: 'Daniyar Omarov', department: 'Sales', role: 'Sales Manager', grade: 'Senior' }, { employee_id: 'E0042', full_name: 'Mariya Petrova', department: 'Customer Support', role: 'Customer Support Specialist', grade: 'Lead' }],
}

export const mockApi: CareerQuestApi = {
  async getEmployees() { await wait(250); return employeeRows },
  async getEmployee(id) { await wait(400); const profile = profileStore[id]; if (!profile) throw new Error('Employee not found'); return structuredClone(profile) },
  async getRecommendations(id) { await wait(1600); return structuredClone(recommendations[id] || { employee_id: id, recommendations: [] }) },
  async completeActivity(id, eventId) { await wait(900); const profile = profileStore[id]; if (!profile) return; const activity = Object.values(recommendations).flatMap((item) => item.recommendations).find((item) => item.event_id === eventId); if (activity) { for (const impact of activity.skill_impacts) { const skill = profile.skills.find((item) => item.skill_id === impact.skill_id); if (skill) { skill.current = impact.after; skill.gap = Math.max(0, skill.required - skill.current) } } profile.progress = Math.min(100, (profile.progress ?? 0) + 12); profile.history = [{ record_id: `R-${Date.now()}`, event_id: eventId, title: activity.title, date: '2026-10-04', status: 'completed', completion_pct: 100, score: 88, feedback_rating: 5 }, ...profile.history]; if (recommendations[id]) recommendations[id].recommendations = recommendations[id].recommendations.filter((item) => item.event_id !== eventId) } },
  async getHrSummary() { await wait(700); return structuredClone(hrSummary) },
  async importData({ employees, history }) { await wait(1100); return { imported_employees: employees ? 1 : 0, imported_history: history ? 12 : 0, message: 'Files validated and queued for import' } },
}
