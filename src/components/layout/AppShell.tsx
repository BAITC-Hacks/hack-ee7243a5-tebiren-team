import { NavLink } from 'react-router-dom'
import { Chart, Compass, Upload, Briefcase } from '../common/Icons'

export function AppShell({ children, onImport }: { children: React.ReactNode; onImport: () => void }) {
  return <div className="app-frame"><aside className="sidebar"><div className="brand"><div className="brand-mark"><Compass size={21} /></div><span>career<span className="brand-accent">quest</span></span></div><div className="workspace-label">WORKSPACE</div><nav className="main-nav"><NavLink to="/" end className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}><Briefcase size={18} /><span>My journey</span></NavLink><NavLink to="/hr" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}><Chart size={18} /><span>HR overview</span></NavLink></nav><div className="sidebar-bottom"><button className="import-link" onClick={onImport}><Upload size={17} /><span>Import test data</span></button><div className="privacy-note"><span className="privacy-dot" />Private workspace</div></div></aside><main className="main-content">{children}</main></div>
}
