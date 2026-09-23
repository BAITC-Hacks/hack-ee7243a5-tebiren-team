import { Link } from 'react-router-dom'
import { Sparkle, Upload } from '../common/Icons'
import { EmployeeSelector } from '../employee/EmployeeSelector'
import type { EmployeeListItem } from '../../api/types'

export function Topbar({ employees, selectedId, onSelect, onImport }: { employees: EmployeeListItem[]; selectedId: string; onSelect: (id: string) => void; onImport: () => void }) {
  return <header className="topbar"><div className="mobile-brand"><Sparkle size={17} /> careerquest</div><div className="topbar-left"><div className="eyebrow">EMPLOYEE VIEW</div><EmployeeSelector employees={employees} selectedId={selectedId} onSelect={onSelect} /></div><div className="topbar-actions"><Link className="top-action" to="/hr">View HR overview <span>↗</span></Link><button className="outline-button" onClick={onImport}><Upload size={15} /> Import data</button><div className="avatar">HR</div></div></header>
}
