import { useEffect, useRef, useState } from 'react'
import { api, errorMessage } from '../api/client'
import type { CompletionResult, EmployeeProfile, Recommendation } from '../api/types'
import { Achievements } from '../components/employee/Achievements'
import { CompletionCelebration } from '../components/employee/CompletionCelebration'
import { confirmedCount, unlockedAchievements, validDevelopmentSummary } from '../gamification/achievements'
import { LoadingState, EmptyState } from '../components/common/States'
import { EmployeeHeader } from '../components/employee/EmployeeHeader'
import { CareerPath } from '../components/employee/CareerPath'
import { ProgressIndicator } from '../components/employee/ProgressIndicator'
import { SkillGapList } from '../components/employee/SkillGapList'
import { RecommendationCard } from '../components/employee/RecommendationCard'
import { ActivityHistory } from '../components/employee/ActivityHistory'
import { Sparkle } from '../components/common/Icons'

export function EmployeePage({selectedId}: {selectedId:string}) {
  const [employee,setEmployee]=useState<EmployeeProfile|null>(null)
  const [recommendations,setRecommendations]=useState<Recommendation[]>([])
  const [finding,setFinding]=useState(false)
  const [requested,setRequested]=useState(false)
  const [reason,setReason]=useState('')
  const [profileError,setProfileError]=useState('')
  const [actionError,setActionError]=useState('')
  const [completing,setCompleting]=useState(false)
  const [success,setSuccess]=useState<{key:string; result?:CompletionResult; unlocked:string[]}|null>(null)
  const alive=useRef(true)
  const profileRequest=useRef(0)
  const actionBusy=useRef(false)
  const requestKeys=useRef<Record<string,string>>({})
  const celebratedRequests=useRef(new Set<string>())

  async function loadProfile() {
    const token=++profileRequest.current
    setProfileError('')
    try {const result=await api.getEmployee(selectedId);if(alive.current&&token===profileRequest.current)setEmployee(result)}
    catch(e){if(alive.current&&token===profileRequest.current)setProfileError(errorMessage(e));throw e}
  }
  useEffect(()=>{
    alive.current=true
    void loadProfile().catch(()=>{})
    return ()=>{alive.current=false;profileRequest.current++}
  },[selectedId])

  async function refreshRecommendations() {
    const result=await api.getRecommendations(selectedId)
    if(!alive.current)return
    setRequested(true);setRecommendations(result.recommendations)
    setReason(result.reason || 'No eligible activity is available for your current target. Ask HR to review your next step.')
  }
  async function find() {
    if(actionBusy.current)return
    actionBusy.current=true;setFinding(true);setActionError('')
    try{await refreshRecommendations()}catch(e){if(alive.current)setActionError(errorMessage(e))}
    finally{actionBusy.current=false;if(alive.current)setFinding(false)}
  }
  async function complete(eventId:string) {
    if(actionBusy.current || !employee)return
    actionBusy.current=true;setCompleting(true);setActionError('');setSuccess(null)
    const actionKey=requestKeys.current[eventId] ||= crypto.randomUUID()
    let saved=false
    try {
      const result=(await api.completeActivity(selectedId,eventId,actionKey)) || undefined
      saved=true
      delete requestKeys.current[eventId]
      if(!alive.current)return
      setRecommendations([])
      const before=employee.development_summary.completed_unique_activities
      const after=validDevelopmentSummary(result?.development_summary) ? result.development_summary.completed_unique_activities : undefined
      setEmployee(current=>current ? {...current, development_summary:{completed_unique_activities:confirmedCount(current.development_summary.completed_unique_activities,result)}} : current)
      if(!celebratedRequests.current.has(actionKey)) {
        celebratedRequests.current.add(actionKey)
        setSuccess({key:actionKey,result,unlocked:unlockedAchievements(before,after)})
      }
      await loadProfile()
      await refreshRecommendations()
    } catch(e) {
      if(alive.current)setActionError(saved ? 'Completion was saved. '+errorMessage(e)+' Refresh the data; do not repeat completion.' : errorMessage(e))
    } finally {actionBusy.current=false;if(alive.current)setCompleting(false)}
  }
  if(!employee)return <div className="page-loading">{profileError?<div role="alert" className="state-card error-state">{profileError}<button className="text-button" onClick={()=>void loadProfile().catch(()=>{})}>Retry</button></div>:<LoadingState label="Loading your journey…"/>}</div>
  return <div className="page-wrap">
    <div className="page-intro"><div><div className="eyebrow dark">EMPLOYEE JOURNEY <span className="live-dot"/> LIVE PROFILE</div><p className="intro-copy">A clear next step for where you want to go.</p></div>{employee.dataset_as_of&&<span className="as-of">Dataset as of {employee.dataset_as_of}</span>}</div>
    <EmployeeHeader employee={employee}/>
    {success&&<CompletionCelebration key={success.key} result={success.result} unlocked={success.unlocked}/>}
    {(actionError||profileError)&&<div role="alert" className="notice error-notice">{actionError||profileError}<button className="text-button" disabled={completing||finding} onClick={()=>{void loadProfile().catch(()=>{});void find()}}>Refresh data</button></div>}
    <div className="journey-grid"><div className="journey-main"><CareerPath employee={employee}/><ProgressIndicator employee={employee}/><Achievements count={employee.development_summary.completed_unique_activities}/><SkillGapList skills={employee.skills}/></div>
      <aside className="journey-side"><div className="next-step-heading"><div><div className="section-kicker">DEVELOPMENT PLAN</div><h2>Your next step</h2></div><Sparkle size={20}/></div>
        <div className="recommendation-panel">{finding||completing?<LoadingState label={completing ? "Saving activity and refreshing your journey…" : "Reviewing your target, skills and participation history…"}/>:recommendations.length?<div className="recommendation-list">{recommendations.map(r=><RecommendationCard key={r.event_id} recommendation={r} onComplete={()=>void complete(r.event_id)} completing={completing}/>)}</div>:actionError?<EmptyState title="Could not refresh your next steps" detail="Use Refresh data above to try again. Saved completions are kept."/>:requested?<EmptyState title="No next step available" detail={reason} action={<button className="text-button" disabled={completing} onClick={()=>void find()}>Check again</button>}/>:<div className="find-cta"><div className="cta-icon"><Sparkle size={22}/></div><h3>Make your progress practical</h3><p>Get 1–3 development activities matched to your target role and the skills that matter most.</p><button className="primary-button full-button" disabled={completing} onClick={()=>void find()}>Find my next step <Sparkle size={16}/></button><span className="cta-note">Explainable recommendations</span></div>}</div>
      </aside></div><ActivityHistory history={employee.history}/>
  </div>
}
