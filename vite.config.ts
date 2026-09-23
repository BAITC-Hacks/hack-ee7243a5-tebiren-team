import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const port = Number(env.CQ_FRONTEND_PORT || 5173)
  const apiPort = Number(env.CQ_BACKEND_PORT || 8000)
  return {
    plugins: [react()],
    server: { host: '127.0.0.1', port, strictPort: true, proxy: { '/api': { target: 'http://127.0.0.1:' + apiPort } } },
    preview: { host: '127.0.0.1', port, strictPort: true, proxy: { '/api': { target: 'http://127.0.0.1:' + apiPort } } },
    build: { rolldownOptions: { output: { codeSplitting: { groups: [{ name: 'charts', test: /node_modules\/(recharts|d3-|victory)/ }] } } } },
  }
})
