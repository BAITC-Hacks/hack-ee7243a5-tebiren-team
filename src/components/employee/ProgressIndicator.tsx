import type { EmployeeProfile } from '../../api/types'

export function ProgressIndicator({employee}: {employee:EmployeeProfile}) {
  if(employee.progress===null||!employee.target)return null
  return <section className="progress-panel card"><div><div className="section-kicker">CAREER READINESS</div><div className="progress-number">{employee.progress}<span>%</span></div><p>Coverage of your target skill requirements.</p>
    <details className="progress-help"><summary>How is this calculated?</summary><p>For each target skill, we compare your current level with the required level, capped at 100%. Critical skills have a weight of 1.5, others 1. The weighted average is rounded to one decimal place. Readiness is not a guarantee of promotion.</p></details>
  </div><div className="progress-track-wrap"><div className="progress-track"><div className="progress-fill" style={{width:employee.progress+'%'}}><span className="progress-knob"/></div></div><div className="progress-labels"><span>{employee.grade}</span><span>{employee.target.grade}</span></div><div className="progress-delta">{employee.progress>=100?'Target skill requirements met':'Your progress towards the target'}</div></div></section>
}
