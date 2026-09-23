import { useState } from 'react'
import { api } from '../../api/client'
import { Upload, Check, X } from '../common/Icons'
import { Modal } from '../common/Modal'

export function ImportDialog({ onClose, onComplete }: { onClose: () => void; onComplete: () => void }) {
  const [employees, setEmployees] = useState<File | null>(null)
  const [history, setHistory] = useState<File | null>(null)
  const [state, setState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')
  async function submit() { if (!employees && !history) { setMessage('Choose at least one file to continue.'); setState('error'); return } setState('loading'); setMessage(''); try { const result = await api.importData({ employees, history }); setMessage(`${result.imported_employees || 0} employees and ${result.imported_history || 0} history rows ready.`); setState('success'); onComplete() } catch { setState('error'); setMessage('Import failed. Check the file format and try again.') } }
  return <Modal title="Import test data" onClose={onClose}><p className="modal-intro">Add jury data without changing the career logic in the frontend. Files are sent to the backend for validation.</p><div className="file-drop-grid"><FileDrop label="Employees JSON" hint="employees.json" accept=".json,application/json" file={employees} onChange={setEmployees} /><FileDrop label="Activity history CSV" hint="activity_history.csv" accept=".csv,text/csv" file={history} onChange={setHistory} /></div>{message && <div className={`import-message ${state === 'error' ? 'import-error' : state === 'success' ? 'import-success' : ''}`}>{state === 'success' && <Check size={16} />}{state === 'error' && <X size={16} />}{message}</div>}<div className="modal-footer"><button className="text-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={state === 'loading' || state === 'success'} onClick={submit}>{state === 'loading' ? 'Uploading…' : state === 'success' ? 'Imported' : 'Upload files'}<Upload size={15} /></button></div></Modal>
}

function FileDrop({ label, hint, accept, file, onChange }: { label: string; hint: string; accept: string; file: File | null; onChange: (file: File | null) => void }) { return <label className={`file-drop ${file ? 'has-file' : ''}`}><input type="file" accept={accept} onChange={(event) => onChange(event.target.files?.[0] || null)} /><div className="file-icon"><Upload size={17} /></div><strong>{file ? file.name : label}</strong><span>{file ? `${Math.round(file.size / 1024)} KB selected` : hint}</span></label> }
