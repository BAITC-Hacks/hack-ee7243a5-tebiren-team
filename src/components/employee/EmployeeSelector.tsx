import { useEffect, useRef, useState } from 'react'
import type { EmployeeListItem } from '../../api/types'
import { api, errorMessage, getEmployeePage } from '../../api/client'
import { ChevronDown, Search } from '../common/Icons'

export function EmployeeSelector({selectedId, revision, onSelect}: {selectedId: string; revision: number; onSelect: (id: string)=>void}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<EmployeeListItem | null>(null)
  const [items, setItems] = useState<EmployeeListItem[]>([])
  const [total, setTotal] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const generation = useRef(0)
  useEffect(()=>{
    let active=true
    api.getEmployee(selectedId).then(e=>{if(active)setSelected(e)}).catch(()=>{if(active)setSelected(null)})
    return ()=>{active=false}
  }, [selectedId, revision])
  async function load(offset=0, token=generation.current) {
    setBusy(true); setError('')
    try {
      const page = await getEmployeePage(query, offset)
      if(token !== generation.current) return
      setItems(old=>offset ? [...old, ...page.employees] : page.employees); setTotal(page.total)
    } catch(e) {if(token===generation.current)setError(errorMessage(e))}
    finally {if(token===generation.current)setBusy(false)}
  }
  useEffect(()=>{
    const token=++generation.current
    setItems([]); setTotal(0)
    if(!open)return
    const timer=window.setTimeout(()=>void load(0,token),200)
    return ()=>{window.clearTimeout(timer); generation.current++}
  },[query,open,revision])
  return <div className="selector-wrap"><button className="selector-trigger" aria-expanded={open} onClick={()=>setOpen(!open)}>
    <div className="selector-avatar">{selected?.full_name.slice(0,1) || '?'}</div><div className="selector-copy"><strong>{selected?.full_name || selectedId}</strong><span>{selected ? selected.role + ' · ' + selected.grade : 'Choose employee'}</span></div><ChevronDown size={16}/>
  </button>{open && <div className="selector-menu"><div className="selector-search"><Search size={15}/><input autoFocus aria-label="Search employee or ID" placeholder="Search employee or ID" value={query} onChange={e=>setQuery(e.target.value)}/></div>
    <div className="selector-list">{items.map(e=><button key={e.employee_id} className={'selector-option ' + (e.employee_id===selectedId?'selected':'')} onClick={()=>{onSelect(e.employee_id);setSelected(e);setOpen(false);setQuery('')}}><div className="option-avatar">{e.full_name.slice(0,1)}</div><div><strong>{e.full_name}</strong><span>{e.role} · {e.grade}</span></div><code>{e.employee_id}</code></button>)}
      {error && <div role="alert" className="notice error-notice">{error}<button onClick={()=>void load()}>Retry</button></div>}
      {busy && <div className="selector-empty">Loading…</div>}
      {!busy && !error && !items.length && <div className="selector-empty">No employees found.</div>}
      {items.length<total && <button className="text-button full-button" disabled={busy} onClick={()=>void load(items.length)}>Load more ({items.length} of {total})</button>}
    </div></div>}</div>
}
