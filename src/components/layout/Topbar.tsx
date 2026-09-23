import { Link } from 'react-router-dom'
import { Upload } from '../common/Icons'
import { EmployeeSelector } from '../employee/EmployeeSelector'
import type { SessionUser } from '../../api/types'

export function Topbar({user, selectedId, revision, onSelect, onImport, onLogout}: {user: SessionUser; selectedId: string; revision: number; onSelect: (id: string)=>void; onImport: ()=>void; onLogout: ()=>void}) {
  return <header className="topbar"><div className="topbar-left"><div className="eyebrow">{user.role === 'hr' ? 'HR WORKSPACE' : 'MY WORKSPACE'}</div>
    {user.role === 'hr' ? <EmployeeSelector selectedId={selectedId} revision={revision} onSelect={onSelect}/> : <strong>{user.employee_id}</strong>}
  </div><div className="topbar-actions">{user.role === 'hr' && <><Link className="top-action" to="/hr">HR overview ↗</Link><button className="outline-button" onClick={onImport}><Upload size={15}/> Import data</button></>}<button className="text-button" onClick={onLogout}>Sign out</button><div className="avatar">{user.role === 'hr' ? 'HR' : 'ME'}</div></div></header>
}
