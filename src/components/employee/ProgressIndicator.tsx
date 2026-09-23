import type { EmployeeProfile } from '../../api/types'

export function ProgressIndicator({ employee }: { employee: EmployeeProfile }) {
  if (employee.progress === null || !employee.target) return null
  return <section className="progress-panel card"><div><div className="section-kicker">CAREER READINESS</div><div className="progress-number">{employee.progress}<span>%</span></div><p>Based on current skills against the target state</p></div><div className="progress-track-wrap"><div className="progress-track"><div className="progress-fill" style={{ width: `${employee.progress}%` }}><span className="progress-knob" /></div></div><div className="progress-labels"><span>{employee.grade}</span><span>{employee.target.grade}</span></div><div className="progress-delta">{employee.progress >= 75 ? 'Strong momentum' : 'Next step identified'}</div></div></section>
}
