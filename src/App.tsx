import { useEffect, useState } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { api } from './api/client'
import type { EmployeeListItem } from './api/types'
import { AppShell } from './components/layout/AppShell'
import { Topbar } from './components/layout/Topbar'
import { ImportDialog } from './components/import/ImportDialog'
import { EmployeePage } from './pages/EmployeePage'
import { HRPage } from './pages/HRPage'

export default function App() {
  const [employees, setEmployees] = useState<EmployeeListItem[]>([])
  const [selectedId, setSelectedId] = useState('E0002')
  const [showImport, setShowImport] = useState(false)
  const navigate = useNavigate()
  useEffect(() => { void api.getEmployees().then((items) => { setEmployees(items); if (!items.find((item) => item.employee_id === selectedId) && items[0]) setSelectedId(items[0].employee_id) }) }, [])
  function selectEmployee(id: string) { setSelectedId(id); navigate('/') }
  return <AppShell onImport={() => setShowImport(true)}><Topbar employees={employees} selectedId={selectedId} onSelect={selectEmployee} onImport={() => setShowImport(true)} /><Routes><Route path="/" element={<EmployeePage employees={employees} selectedId={selectedId} onSelect={selectEmployee} />} /><Route path="/hr" element={<HRPage />} /></Routes>{showImport && <ImportDialog onClose={() => setShowImport(false)} onComplete={() => { void api.getEmployees().then(setEmployees) }} />}</AppShell>
}
