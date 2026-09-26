import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../', import.meta.url))
const backend = path.join(root, 'backend')
const python = path.join(backend, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')

console.log('\n======================================================')
console.log('  AYUNEX / IP-SAKTI Sahayak — Development Server')
console.log('  Starting backend on http://127.0.0.1:8000')
console.log('  Starting frontend on http://localhost:5173')
console.log('  Press Ctrl+C to stop both.')
console.log('======================================================\n')

let backendChild = null
let frontendChild = null

function cleanup() {
  if (backendChild && backendChild.exitCode === null) {
    try { backendChild.kill('SIGTERM') } catch {}
  }
  if (frontendChild && frontendChild.exitCode === null) {
    try { frontendChild.kill('SIGTERM') } catch {}
  }
}

process.on('SIGINT', () => { cleanup(); process.exit(0) })
process.on('SIGTERM', () => { cleanup(); process.exit(0) })
process.on('exit', cleanup)

backendChild = spawn(existsSync(python) ? python : 'python3', ['-u', 'dev.py'], {
  cwd: backend,
  stdio: 'inherit',
  env: process.env
})

backendChild.on('error', err => {
  console.error(`Backend failed to start: ${err.message}`)
})

frontendChild = spawn('npm', ['--prefix', 'frontend', 'run', 'dev'], {
  cwd: root,
  stdio: 'inherit',
  env: process.env,
  shell: true
})

frontendChild.on('error', err => {
  console.error(`Frontend failed to start: ${err.message}`)
})
