import type { EmployeeProfile } from '../../api/types'
import { ArrowRight } from '../common/Icons'
import { EmptyState } from '../common/States'

export function CareerPath({ employee }: { employee: EmployeeProfile }) {
  return <section className="career-path card"><div className="section-kicker">YOUR CAREER PATH</div>{employee.target ? <div className="path-flow"><div className="path-node current"><span className="node-label">CURRENT ROLE</span><strong>{employee.role}</strong><span>{employee.grade}</span></div><div className="path-connector"><div className="connector-line" /><div className="connector-arrow"><ArrowRight size={20} /></div><small>DEVELOPMENT</small></div><div className="path-node target"><span className="node-label">TARGET STATE</span><strong>{employee.target.role}</strong><span>{employee.target.grade}</span></div></div> : <EmptyState title="No career target has been selected." detail="Once a target is added, your skill gaps and next steps will appear here." />}</section>
}
