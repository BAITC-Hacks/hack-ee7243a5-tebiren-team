import { useMemo, useState } from 'react'
import type { EmployeeListItem } from '../../api/types'
import { ChevronDown, Search } from '../common/Icons'

export function EmployeeSelector({ employees, selectedId, onSelect }: { employees: EmployeeListItem[]; selectedId: string; onSelect: (id: string) => void }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const selected = employees.find((item) => item.employee_id === selectedId)
  const filtered = useMemo(() => employees.filter((item) => `${item.full_name} ${item.employee_id} ${item.role}`.toLowerCase().includes(query.toLowerCase())), [employees, query])
  return <div className="selector-wrap"><button className="selector-trigger" onClick={() => setOpen(!open)}><div className="selector-avatar">{selected?.full_name.split(' ').map((name) => name[0]).join('').slice(0, 2)}</div><div className="selector-copy"><strong>{selected?.full_name}</strong><span>{selected?.role} · {selected?.grade}</span></div><ChevronDown size={16} /></button>{open && <div className="selector-menu"><div className="selector-search"><Search size={15} /><input autoFocus placeholder="Search employee or ID" value={query} onChange={(event) => setQuery(event.target.value)} /></div><div className="selector-list">{filtered.map((employee) => <button key={employee.employee_id} className={`selector-option ${employee.employee_id === selectedId ? 'selected' : ''}`} onClick={() => { onSelect(employee.employee_id); setOpen(false); setQuery('') }}><div className="option-avatar">{employee.full_name.slice(0, 1)}</div><div><strong>{employee.full_name}</strong><span>{employee.role} · {employee.grade}</span><small>{employee.department}</small></div><code>{employee.employee_id}</code></button>)}{filtered.length === 0 && <div className="selector-empty">No employees found.</div>}</div></div>}</div>
}
