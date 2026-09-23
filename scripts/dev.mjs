import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { createServer } from 'node:net'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { loadEnv } from 'vite'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
process.chdir(root)
const config = loadEnv('development', root, '')
const env = { ...process.env, ...config }
const backend = resolve(root, 'backend')
const python = env.CQ_PYTHON || resolve(backend, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
const mode = process.argv[2] || ''
if (mode !== '--mock' && !existsSync(python)) {
  console.error('Backend environment not found. Create backend/.venv and install backend/requirements.txt; see README.')
  process.exit(1)
}
if (mode === '--setup' || mode === '--test' || mode === '--check-ai') {
  const args = mode === '--setup' ? ['-m', 'app.setup_demo'] : mode === '--check-ai' ? ['check_openai.py'] : ['-m', 'pytest', '-q']
  const result = spawnSync(python, args, {cwd:backend, env, stdio:'inherit', windowsHide:true})
  process.exit(result.status ?? 1)
}
const frontPort = Number(env.CQ_FRONTEND_PORT || 5173)
const backPort = Number(env.CQ_BACKEND_PORT || 8000)
if (![frontPort,backPort].every(p=>Number.isInteger(p)&&p>0&&p<=65535) || frontPort===backPort) {
  console.error('Use two different valid CQ_FRONTEND_PORT / CQ_BACKEND_PORT values.')
  process.exit(1)
}
env.CQ_FRONTEND_PORT = String(frontPort)
env.CQ_BACKEND_PORT = String(backPort)
env.VITE_USE_MOCKS = mode === '--mock' ? 'true' : 'false'
env.VITE_API_URL = '' // Same-origin cookies and proxy: no cross-site cookie exceptions.
env.CQ_ALLOWED_ORIGINS = env.CQ_ALLOWED_ORIGINS || loadEnv('development', backend, 'CQ_').CQ_ALLOWED_ORIGINS || 'http://127.0.0.1:'+frontPort+',http://localhost:'+frontPort
function free(port) {
  return new Promise((yes,no)=>{
    const s=createServer()
    s.once('error',()=>no(new Error('Port '+port+' is in use. Stop the previous server yourself or choose CQ_FRONTEND_PORT / CQ_BACKEND_PORT.')))
    s.listen(port,'127.0.0.1',()=>s.close(yes))
  })
}
const children=[]
let stopping=false
function stop(code=0) {
  if(stopping)return
  stopping=true
  for(const child of children) {
    if(child.exitCode!==null || !child.pid)continue
    if(process.platform==='win32') spawnSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'})
    else child.kill('SIGTERM')
  }
  process.exit(code)
}
function launch(command,args,cwd) {
  const child=spawn(command,args,{cwd,env,stdio:'inherit',windowsHide:true})
  children.push(child)
  child.on('error',e=>{console.error(e.message);stop(1)})
  child.on('exit',code=>{if(!stopping)stop(code??1)})
  return child
}
process.on('SIGINT',()=>stop())
process.on('SIGTERM',()=>stop())
try {
  if(mode!=='--backend-only') await free(frontPort)
  if(mode!=='--mock') {
    await free(backPort)
    launch(python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port',String(backPort)],backend)
    let ready=false
    for(let i=0;i<50;i++) {
      try { const r=await fetch('http://127.0.0.1:'+backPort+'/api/health',{signal:AbortSignal.timeout(500)}); if(r.ok){ready=true;break} } catch {}
      await new Promise(r=>setTimeout(r,200))
    }
    if(!ready)throw new Error('Backend did not start. Check its output above.')
  }
  if(mode!=='--backend-only') {
    launch(process.execPath,[resolve(root,'node_modules/vite/bin/vite.js')],root)
    console.log('Career Quest: http://127.0.0.1:'+frontPort)
  }
} catch(e) { console.error(e.message); stop(1) }
