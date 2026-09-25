import { existsSync } from 'node:fs'
import { spawn, execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../', import.meta.url))
const backend = path.join(root, 'backend')
const frontend = path.join(root, 'frontend')
const python = path.join(backend, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')

if (!existsSync(python)) {
  console.error('Backend Python environment is missing. Run backend setup first.')
  process.exit(1)
}

console.log('Building production frontend assets…')
try {
  execSync('npm --prefix frontend run build', { cwd: root, stdio: 'inherit' })
} catch (e) {
  console.error('Frontend build failed:', e.message)
  process.exit(1)
}

console.log('\n======================================================')
console.log('  AYUNEX / IP-SAKTI Sahayak — Production Server')
console.log('  Web App & API: http://127.0.0.1:8000')
console.log('  API Documentation: http://127.0.0.1:8000/docs')
console.log('  Liveness & Health: http://127.0.0.1:8000/healthz')
console.log('======================================================\n')

const child = spawn(python, ['-u', 'dev.py'], {
  cwd: backend,
  stdio: 'inherit',
  env: { ...process.env, APP_ENV: 'development', GUIDANCE_MODE: 'hosted' }
})

child.on('error', error => {
  console.error(`Could not start production server: ${error.message}`)
  process.exitCode = 1
})

child.on('exit', (code, signal) => {
  process.exitCode = signal === 'SIGINT' || signal === 'SIGTERM' ? 0 : (code ?? 1)
})

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => { if (child.exitCode === null) child.kill(signal) })
}
