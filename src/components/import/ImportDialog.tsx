import { useState } from 'react'
import { api, errorMessage } from '../../api/client'
import type { ImportResult } from '../../api/types'
import { Upload } from '../common/Icons'
import { Modal } from '../common/Modal'

export function ImportDialog({onClose,onComplete,onOpenEmployee}: {onClose:()=>void;onComplete:()=>void;onOpenEmployee:(id:string)=>void}) {
  const [employees,setEmployees]=useState<File|null>(null)
  const [history,setHistory]=useState<File|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [result,setResult]=useState<ImportResult|null>(null)
  async function submit() {
    if(!employees&&!history){setError('Choose at least one file.');return}
    setBusy(true);setError('')
    try {setResult(await api.importData({employees,history}));onComplete()}
    catch(e){setError(errorMessage(e))}
    finally{setBusy(false)}
  }
  return <Modal title="Import test data" onClose={()=>{if(!busy)onClose()}}>
    <p className="modal-intro">Add employee profiles and participation history from the dataset. Both files are validated before any changes are saved.</p>
    <div className="file-drop-grid"><FileDrop label="Employees JSON" accept=".json" file={employees} disabled={busy||!!result} onChange={setEmployees}/><FileDrop label="Activity history CSV" accept=".csv" file={history} disabled={busy||!!result} onChange={setHistory}/></div>
    {error&&<p role="alert" className="notice error-notice">{error}</p>}
    {result&&<div className="notice success-notice"><p>{result.imported_employees||0} employees and {result.imported_history||0} history rows imported.</p>
      {result.warnings?.map(w=><p key={w}>{w}</p>)}
      {result.imported_employee_ids?.map(id=><button key={id} className="outline-button" onClick={()=>onOpenEmployee(id)}>Open profile {id} ↗</button>)}
    </div>}
    <div className="modal-footer"><button className="text-button" disabled={busy} onClick={onClose}>{result?'Done':'Cancel'}</button><button className="primary-button" disabled={busy||!!result} onClick={()=>void submit()}>{busy?'Uploading…':result?'Imported':'Upload files'}<Upload size={15}/></button></div>
  </Modal>
}
function FileDrop({label,accept,file,disabled,onChange}: {label:string;accept:string;file:File|null;disabled:boolean;onChange:(f:File|null)=>void}) {
  return <label className={'file-drop '+(file?'has-file':'')}><input aria-label={label} type="file" accept={accept} disabled={disabled} onChange={e=>onChange(e.target.files?.[0]||null)}/><Upload size={20}/><strong>{file?.name||label}</strong><span>{file?Math.ceil(file.size/1024)+' KB':'Choose file (up to 5 MB)'}</span></label>
}
