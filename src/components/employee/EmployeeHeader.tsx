import type { EmployeeProfile } from '../../api/types'
import { Calendar, Briefcase } from '../common/Icons'
import { TinyTag } from '../common/Badge'

export function EmployeeHeader({ employee }: { employee: EmployeeProfile }) {
  const initials = employee.full_name.split(' ').map((name) => name[0]).join('').slice(0, 2)
  return <section className="profile-header"><div className="profile-avatar">{initials}</div><div className="profile-details"><div className="profile-title-row"><h1>{employee.full_name}</h1><TinyTag tone="green">{employee.employee_id}</TinyTag></div><p className="profile-role"><Briefcase size={15} /> {employee.role} <span>·</span> {employee.grade} {employee.department && <><span>·</span> {employee.department}</>}</p><div className="profile-meta">{employee.last_review_date && <span><Calendar size={14} /> Last review {formatDate(employee.last_review_date)}</span>}<span>{employee.tenure_months} months tenure</span>{employee.work_format && <span className="capitalize">{employee.work_format}</span>}</div></div></section>
}

function formatDate(value: string) { return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) }
