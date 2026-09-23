import { useEffect, useState } from 'react'
import './readiness.css'
import { Navigate, Routes, Route, useNavigate } from 'react-router-dom'
import { ApiError, authApi, errorMessage, useMocks } from './api/client'
import type { SessionUser } from './api/types'
import { AppShell } from './components/layout/AppShell'
import { Topbar } from './components/layout/Topbar'
import { ImportDialog } from './components/import/ImportDialog'
import { EmployeePage } from './pages/EmployeePage'
import { HRPage } from './pages/HRPage'
import { LoadingState } from './components/common/States'

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [checking, setChecking] = useState(true)
  const [error, setError] = useState('')
  async function check() {
    setChecking(true); setError('')
    try { setUser(await authApi.me()) }
    catch (e) { if (!(e instanceof ApiError && e.status === 401)) setError(errorMessage(e)) }
    finally { setChecking(false) }
  }
  useEffect(() => {
    void check()
    const expired = () => { setUser(null); setError('Your session expired. Please sign in again.') }
    window.addEventListener('cq-session-expired', expired)
    return () => window.removeEventListener('cq-session-expired', expired)
  }, [])
  if (checking) return <LoadingState label="Opening your workspace…" />
  if (!user) return <Login onLogin={setUser} initialError={error} onRetry={check} />
  return <Workspace key={user.username} user={user} onLogout={() => setUser(null)} />
}

function Login({onLogin, initialError, onRetry}: {onLogin: (u: SessionUser) => void; initialError: string; onRetry: () => void}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  return <main className="login-page"><form className="card login-card" onSubmit={async e => {
    e.preventDefault(); setBusy(true); setError('')
    try { onLogin(await authApi.login(username, password)); setPassword('') }
    catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }}><div className="eyebrow dark">CAREER QUEST</div><h1>Your next chapter starts here.</h1><p>Sign in to your private development workspace.</p>
    <label>Username<input required autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} /></label>
    <label>Password<input required type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} /></label>
    {(error || initialError) && <p role="alert" className="notice error-notice">{error || initialError}</p>}
    <button className="primary-button full-button" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
    {initialError && <button type="button" className="text-button" onClick={onRetry}>Retry connection</button>}
    <small>Use the local account provided by your demo administrator.</small>
  </form></main>
}

function Workspace({user, onLogout}: {user: SessionUser; onLogout: () => void}) {
  const [selectedId, setSelectedId] = useState(user.employee_id || 'E0002')
  const [revision, setRevision] = useState(0)
  const [showImport, setShowImport] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const isHR = user.role === 'hr'
  function select(id: string) { setSelectedId(id); setShowImport(false); navigate('/') }
  async function logout() {
    try { await authApi.logout(); onLogout() } catch(e) { setError(errorMessage(e)) }
  }
  return <AppShell isHR={isHR} onImport={() => setShowImport(true)}>
    <Topbar user={user} selectedId={selectedId} revision={revision} onSelect={select} onImport={()=>setShowImport(true)} onLogout={logout} />
    {useMocks && <div className="notice">Mock preview — no real data is changed.</div>}
    {error && <div role="alert" className="notice error-notice">{error}</div>}
    <Routes>
      <Route path="/" element={<EmployeePage key={selectedId + ':' + revision} selectedId={selectedId} />} />
      <Route path="/hr" element={isHR ? <HRPage key={revision} onSelect={select} onReset={()=>{setSelectedId('E0002');setRevision(v=>v+1)}} /> : <Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    {isHR && showImport && <ImportDialog onClose={()=>setShowImport(false)} onComplete={()=>setRevision(v=>v+1)} onOpenEmployee={select} />}
  </AppShell>
}
