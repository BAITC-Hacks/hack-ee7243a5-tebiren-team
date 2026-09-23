import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, errorMessage, getNoStepPage, resetDemo } from '../api/client'
import type { HRSummary, NoStepEmployee } from '../api/types'
import { LoadingState } from '../components/common/States'
import { Modal } from '../components/common/Modal'

export function HRPage({onSelect,onReset}: {onSelect:(id:string)=>void;onReset:()=>void}) {
  const [summary,setSummary]=useState<HRSummary|null>(null)
  const [people,setPeople]=useState<NoStepEmployee[]>([])
  const [total,setTotal]=useState(0)
  const [offset,setOffset]=useState(0)
  const [error,setError]=useState('')
  const [pageError,setPageError]=useState('')
  const [busy,setBusy]=useState(false)
  const [confirm,setConfirm]=useState(false)
  const [resetting,setResetting]=useState(false)
  useEffect(()=>{
    let active=true
    Promise.all([api.getHrSummary(),getNoStepPage()]).then(([s,p])=>{if(active){setSummary(s);setPeople(p.employees);setTotal(p.total)}}).catch(e=>{if(active)setError(errorMessage(e))})
    return ()=>{active=false}
  },[])
  async function page(next:number) {
    setBusy(true);setPageError('')
    try{const p=await getNoStepPage(next);setPeople(p.employees);setTotal(p.total);setOffset(next)}
    catch(e){setPageError(errorMessage(e))}finally{setBusy(false)}
  }
  if(!summary)return <div className="page-loading">{error?<div className="notice error-notice" role="alert">{error}<button onClick={onReset}>Retry</button></div>:<LoadingState label="Loading HR overview…"/>}</div>
  const participation=summary.participation_summary
  return <div className="page-wrap hr-page">
    <div className="page-intro"><div><div className="eyebrow dark">HR OVERVIEW</div><p className="intro-copy">See where development support is needed.</p></div><button className="text-button" onClick={()=>setConfirm(true)}>Reset demo data</button></div>
    <div className="hr-hero"><div><span className="hero-label">DEVELOPMENT HEALTH</span><h1>Turn skill gaps<br/><em>into momentum.</em></h1></div><div className="hero-stat"><span>Employees without a next step</span><strong>{total}<small> people</small></strong><span className="stat-caption">Review the reason for each profile below</span></div></div>
    <div className="hr-grid"><section className="card chart-card"><div className="section-heading"><div><div className="section-kicker">COMMON SKILL GAPS</div><h2>Where the team needs support</h2></div></div><div className="chart-wrap">{summary.skill_gaps.length?<ResponsiveContainer width="100%" height={300}><BarChart data={summary.skill_gaps} layout="vertical" margin={{left:5,right:25}}><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number"/><YAxis dataKey="name" type="category" width={140} tick={{fontSize:11}}/><Tooltip/><Bar dataKey="employee_count" name="Employees" fill="#117e79" radius={[0,5,5,0]}/></BarChart></ResponsiveContainer>:<p>No unresolved target gaps.</p>}</div></section>
    <section className="card participation-card"><div className="section-kicker">PARTICIPATION</div><h2>Overall participation</h2>{participation&&<div className="participation-summary"><div className="summary-stat"><strong>{participation.completion_rate.toFixed(1)}%</strong><span>completed records / all records</span></div><div className="summary-stat"><strong>{participation.unique_participants}</strong><span>unique employees with history</span></div><div className="summary-stat"><strong>{participation.total_records}</strong><span>participation records</span></div></div>}<p>Repeated attendance counts as multiple records, but each employee is counted only once as a unique participant.</p></section></div>
    <section className="card audit-section"><div className="section-kicker">BY ACTIVITY</div><h2>Participation across activities</h2><div className="table-scroll"><table className="data-table"><thead><tr><th>Activity</th><th>People</th><th>Completed</th><th>In progress</th><th>Dropped</th><th>No-show</th><th>Declined</th><th>Overdue</th></tr></thead><tbody>{summary.activity_participation.map(a=><tr key={a.event_id}><td><strong>{a.title}</strong><small>{a.event_id}</small></td><td>{a.unique_participants??'—'}</td><td>{a.completed}</td><td>{a.in_progress}</td><td>{a.dropped}</td><td>{a.no_show}</td><td>{a.declined}</td><td>{a.overdue}</td></tr>)}</tbody></table></div></section>
    <section className="card audit-section"><div className="section-kicker">NO NEXT STEP</div><h2>Profiles to review</h2><p>A missing next step can mean no target, requirements already met, or no eligible activity. It does not necessarily mean disengagement.</p>
      {pageError&&<p className="notice error-notice" role="alert">{pageError}</p>}
      <div className="no-step-list">{people.map(p=><button key={p.employee_id} className="profile-link" onClick={()=>onSelect(p.employee_id)}><div><strong>{p.full_name}</strong><span>{p.employee_id} · {p.role} · {p.grade}</span><p>{p.reason}</p></div><span>Open profile ↗</span></button>)}</div>
      {!people.length&&<p>Every employee has an eligible next step.</p>}
      <div className="pagination"><button className="outline-button" disabled={busy||offset===0} onClick={()=>void page(Math.max(0,offset-20))}>Previous</button><span>{total?offset+1:0}–{Math.min(offset+people.length,total)} of {total}</span><button className="outline-button" disabled={busy||offset+people.length>=total} onClick={()=>void page(offset+20)}>Next</button></div>
    </section>
    {confirm&&<Modal title="Reset demo data?" onClose={()=>{if(!resetting)setConfirm(false)}}><p>This removes imported profiles and simulated completions, restoring the original dataset. Local accounts remain. Back up your demo database first if you want to keep these changes.</p>{error&&<p role="alert" className="notice error-notice">{error}</p>}<div className="modal-footer"><button className="text-button" disabled={resetting} onClick={()=>setConfirm(false)}>Cancel</button><button className="primary-button" disabled={resetting} onClick={async()=>{setResetting(true);setError('');try{await resetDemo();onReset()}catch(e){setError(errorMessage(e));setResetting(false)}}}>{resetting?'Resetting…':'Reset demo data'}</button></div></Modal>}
  </div>
}
