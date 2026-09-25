import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../', import.meta.url))
const backend = path.join(root, 'backend')
const python = path.join(backend, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
const check = process.argv.includes('--check')

if (!existsSync(python)) {
  console.error('Backend Python environment is missing. Run the one-time setup from backend/README.md first.')
  process.exit(1)
}

console.log(check ? 'Checking backend dependencies…' : 'Starting AYUNEX backend…\nAPI docs: http://127.0.0.1:8000/docs\nPress Ctrl+C to stop.\n')
const child = spawn(python, check
  ? ['-c', 'import fastapi, uvicorn, sqlalchemy, alembic, psycopg, httpx, pypdf, redis; print("Backend environment ready. Run npm run backend.")']
  : ['-u', 'dev.py'], { cwd: backend, stdio: 'inherit', env: process.env })

child.on('error', error => {
  console.error(`Could not start backend: ${error.message}`)
  process.exitCode = 1
})
child.on('exit', (code, signal) => {
  process.exitCode = signal === 'SIGINT' || signal === 'SIGTERM' ? 0 : (code ?? 1)
})
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => { if (child.exitCode === null) child.kill(signal) })
}
