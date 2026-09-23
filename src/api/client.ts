import type { CareerQuestApi, EmployeeListItem, ImportResult, RecommendationsResponse, EmployeeProfile, HRSummary } from './types'
import { mockApi } from '../mock/mockApi'

const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const useMocks = import.meta.env.VITE_USE_MOCKS !== 'false'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, init)
  if (!response.ok) throw new Error(`Request failed: ${response.status}`)
  return response.json() as Promise<T>
}

const realApi: CareerQuestApi = {
  async getEmployees() {
    const result = await request<{ employees: EmployeeListItem[] }>('/api/employees')
    return result.employees
  },
  getEmployee: (id) => request<EmployeeProfile>(`/api/employees/${id}`),
  getRecommendations: (id) => request<RecommendationsResponse>(`/api/employees/${id}/recommendations`, { method: 'POST' }),
  completeActivity: async (id, eventId) => {
    await request(`/api/employees/${id}/complete`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event_id: eventId }) })
  },
  getHrSummary: () => request<HRSummary>('/api/hr/summary'),
  importData: async ({ employees, history }) => {
    const form = new FormData()
    if (employees) form.append('employees', employees)
    if (history) form.append('history', history)
    return request<ImportResult>('/api/import', { method: 'POST', body: form })
  },
}

export const api: CareerQuestApi = useMocks ? mockApi : realApi
