import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

function autoBackendPlugin() {
  let backendReady = false
  let backendChild = null

  async function isHealthy() {
    try {
      const res = await fetch('http://127.0.0.1:8000/health', { signal: AbortSignal.timeout(300) })
      return res.ok
    } catch {
      return false
    }
  }

  async function waitForBackend(maxWaitMs = 12000) {
    const start = Date.now()
    while (Date.now() - start < maxWaitMs) {
      if (await isHealthy()) {
        backendReady = true
        return true
      }
      await new Promise(r => setTimeout(r, 200))
    }
    return false
  }

  return {
    name: 'auto-backend',
    async configureServer(server) {
      if (await isHealthy()) {
        backendReady = true
        console.log('\n[ayunex] AYUNEX backend already running on http://127.0.0.1:8000\n')
      } else {
        const backendDir = path.resolve(__dirname, '../backend')
        const venvPython = path.join(backendDir, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
        const python = existsSync(venvPython) ? venvPython : 'python3'

        console.log('\n[ayunex] Auto-starting backend on http://127.0.0.1:8000...')
        backendChild = spawn(python, ['-u', 'dev.py'], {
          cwd: backendDir,
          stdio: 'inherit',
          env: process.env
        })

        backendChild.on('error', err => {
          console.error('[ayunex] Failed to auto-start backend:', err.message)
        })

        waitForBackend(12000).then(ready => {
          if (ready) {
            console.log('[ayunex] AYUNEX backend is ready on http://127.0.0.1:8000\n')
          }
        })
      }

      server.middlewares.use('/api', async (req, res, next) => {
        if (!backendReady) {
          await waitForBackend(6000)
        }
        next()
      })

      const cleanup = () => {
        if (backendChild && backendChild.exitCode === null) {
          try { backendChild.kill('SIGTERM') } catch {}
        }
      }
      process.on('SIGINT', cleanup)
      process.on('SIGTERM', cleanup)
      process.on('exit', cleanup)
      server.httpServer?.on('close', cleanup)
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), autoBackendPlugin()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            if (res && !res.headersSent) {
              res.writeHead(503, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({
                detail: 'Backend server is starting up or unreachable on http://127.0.0.1:8000. Please wait a moment and retry.'
              }))
            }
          })
        }
      }
    }
  },
})
