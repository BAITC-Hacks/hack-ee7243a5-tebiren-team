import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { EmployeeListItem, EmployeeProfile, Recommendation } from '../api/types'
import { LoadingState, ErrorState, EmptyState } from '../components/common/States'
import { EmployeeHeader } from '../components/employee/EmployeeHeader'
import { CareerPath } from '../components/employee/CareerPath'
import { ProgressIndicator } from '../components/employee/ProgressIndicator'
import { SkillGapList } from '../components/employee/SkillGapList'
import { RecommendationCard } from '../components/employee/RecommendationCard'
import { ActivityHistory } from '../components/employee/ActivityHistory'
import { Sparkle } from '../components/common/Icons'

export function EmployeePage({ employees, selectedId, onSelect }: { employees: EmployeeListItem[]; selectedId: string; onSelect: (id: string) => void }) {
  const [employee, setEmployee] = useState<EmployeeProfile | null>(null)
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [finding, setFinding] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [justUpdated, setJustUpdated] = useState(false)

  const loadEmployee = useCallback(async () => { setLoading(true); setError(false); try { const result = await api.getEmployee(selectedId); setEmployee(result) } catch { setError(true) } finally { setLoading(false) } }, [selectedId])
  useEffect(() => { setRecommendations([]); void loadEmployee() }, [loadEmployee])
  async function findNextStep() { setFinding(true); try { const result = await api.getRecommendations(selectedId); setRecommendations(result.recommendations) } finally { setFinding(false) } }
  async function complete(eventId: string) { setCompleting(true); try { await api.completeActivity(selectedId, eventId); await loadEmployee(); const result = await api.getRecommendations(selectedId); setRecommendations(result.recommendations); setJustUpdated(true); window.setTimeout(() => setJustUpdated(false), 2600) } finally { setCompleting(false) } }

  if (loading) return <div className="page-loading"><LoadingState label="Loading your journey…" /></div>
  if (error || !employee) return <div className="page-loading"><ErrorState onRetry={loadEmployee} /></div>

  return <div className="page-wrap"><div className="page-intro"><div><div className="eyebrow dark">EMPLOYEE JOURNEY <span className="live-dot" /> LIVE PROFILE</div><p className="intro-copy">A clear next step for where you want to go.</p></div><span className="as-of">As of Oct 04, 2026</span></div><EmployeeHeader employee={employee} /><div className="journey-grid"><div className="journey-main"><CareerPath employee={employee} /><ProgressIndicator employee={employee} /><SkillGapList skills={employee.skills} /></div><aside className="journey-side"><div className="next-step-heading"><div><div className="section-kicker">DEVELOPMENT PLAN</div><h2>Your next step</h2></div><Sparkle size={20} /></div><div className={`recommendation-panel ${justUpdated ? 'updated' : ''}`}>{justUpdated && <div className="update-toast"><span className="success-check">✓</span> Profile updated from backend</div>}{finding ? <div className="analyzing"><div className="analysis-orbit"><Sparkle size={25} /></div><h3>Finding your next step</h3><p>Analyzing career goal, skill gaps and participation history…</p><div className="analysis-bars"><span /><span /><span /></div></div> : recommendations.length ? <div className="recommendation-list">{recommendations.map((item) => <RecommendationCard key={item.event_id} recommendation={item} onComplete={() => complete(item.event_id)} completing={completing} />)}</div> : <div className="find-cta"><div className="cta-icon"><Sparkle size={22} /></div><h3>Make your progress practical</h3><p>Get 1–3 development activities matched to your target role and the skills that matter most.</p><button className="primary-button full-button" onClick={findNextStep}>Find my next step <Sparkle size={16} /></button><span className="cta-note">Explainable recommendations · no black box</span></div>}</div></aside></div><ActivityHistory history={employee.history} /></div>
}
