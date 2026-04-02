'use client'

import { useEffect, useState, useCallback } from 'react'

// Tauri v2: imports are tree-shaken — only available inside the Tauri webview.
// In plain browser / Next.js dev mode these will be undefined, so we guard all
// calls with the `isTauri` flag.
let invoke: ((cmd: string, args?: Record<string, unknown>) => Promise<unknown>) | undefined
let listen: ((event: string, cb: (e: { payload: unknown }) => void) => Promise<() => void>) | undefined

const isTauri =
  typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

if (isTauri) {
  // Dynamic import so Next.js static export doesn't bundle Tauri internals for
  // non-Tauri environments.
  import('@tauri-apps/api/core').then((m) => { invoke = m.invoke })
  import('@tauri-apps/api/event').then((m) => { listen = m.listen })
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ServerStatus {
  running: boolean
  url: string
  backend: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const DASHBOARD_ORIGIN = 'http://localhost:3000'
const API_URL = 'http://127.0.0.1:8000'

export default function Page() {
  const [status, setStatus] = useState<ServerStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [devMode] = useState(!isTauri)

  // Fetch status via Tauri command or direct HTTP in dev mode.
  const refreshStatus = useCallback(async () => {
    if (isTauri && invoke) {
      try {
        const s = (await invoke('get_server_status')) as ServerStatus
        setStatus(s)
      } catch {
        setStatus({ running: false, url: API_URL, backend: 'zerodb-server' })
      }
    } else {
      // Dev mode: ping the API directly.
      try {
        const res = await fetch(`${API_URL}/health`)
        setStatus({ running: res.ok, url: API_URL, backend: 'uvicorn (dev)' })
      } catch {
        setStatus({ running: false, url: API_URL, backend: 'uvicorn (dev)' })
      }
    }
  }, [])

  // Initial load + Tauri event subscription.
  useEffect(() => {
    refreshStatus()

    if (isTauri && listen) {
      let unlisten: (() => void) | undefined
      listen('server-status-changed', (e) => {
        setStatus((prev) =>
          prev ? { ...prev, running: e.payload as boolean } : prev
        )
      }).then((fn) => { unlisten = fn })

      return () => { unlisten?.() }
    }
  }, [refreshStatus])

  // Poll every 5 s so the UI stays in sync even without Tauri events.
  useEffect(() => {
    const id = setInterval(refreshStatus, 5000)
    return () => clearInterval(id)
  }, [refreshStatus])

  const handleStartServer = async () => {
    setLoading(true)
    try {
      if (isTauri && invoke) {
        await invoke('start_server')
      }
      await refreshStatus()
    } finally {
      setLoading(false)
    }
  }

  const handleStopServer = async () => {
    setLoading(true)
    try {
      if (isTauri && invoke) {
        await invoke('stop_server')
      }
      await refreshStatus()
    } finally {
      setLoading(false)
    }
  }

  const running = status?.running ?? false

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* ------------------------------------------------------------------ */}
      {/* Status bar                                                          */}
      {/* ------------------------------------------------------------------ */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '6px 16px',
          background: '#111',
          borderBottom: '1px solid #222',
          flexShrink: 0,
          fontSize: '13px',
          color: '#ccc',
        }}
      >
        {/* Status dot */}
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: running ? '#22c55e' : '#ef4444',
            flexShrink: 0,
            boxShadow: running
              ? '0 0 6px rgba(34,197,94,0.7)'
              : '0 0 4px rgba(239,68,68,0.5)',
          }}
        />
        <span style={{ fontWeight: 600, color: '#fff' }}>ZeroDB</span>
        <span style={{ color: running ? '#86efac' : '#fca5a5' }}>
          {running ? 'Server running' : 'Server stopped'}
        </span>
        {status && (
          <span style={{ color: '#555', marginLeft: 4 }}>
            {status.url} · {status.backend}
          </span>
        )}
        {devMode && (
          <span
            style={{
              marginLeft: 4,
              color: '#f59e0b',
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.05em',
            }}
          >
            DEV MODE
          </span>
        )}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Controls */}
        <button
          onClick={running ? handleStopServer : handleStartServer}
          disabled={loading}
          style={{
            padding: '4px 14px',
            borderRadius: 6,
            border: 'none',
            cursor: loading ? 'not-allowed' : 'pointer',
            background: running ? '#7f1d1d' : '#14532d',
            color: running ? '#fca5a5' : '#86efac',
            fontWeight: 600,
            fontSize: 12,
            opacity: loading ? 0.6 : 1,
            transition: 'opacity 0.15s',
          }}
        >
          {loading ? 'Working…' : running ? 'Stop Server' : 'Start Server'}
        </button>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Dashboard iframe                                                    */}
      {/* ------------------------------------------------------------------ */}
      {running ? (
        <iframe
          src={status?.url ?? API_URL}
          style={{ flex: 1, width: '100%' }}
          title="ZeroDB Dashboard"
          allow="clipboard-read; clipboard-write"
          // Note: the dashboard is a separate Next.js app served from the
          // API server or a static file server. In production Tauri builds
          // the static export is served by Tauri's asset protocol, and the
          // Python API is the JSON backend only.
        />
      ) : (
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 24,
            color: '#666',
          }}
        >
          <svg
            width={56}
            height={56}
            viewBox="0 0 24 24"
            fill="none"
            stroke="#333"
            strokeWidth={1.5}
          >
            <ellipse cx={12} cy={5} rx={9} ry={3} />
            <path d="M3 5v4c0 1.657 4.03 3 9 3s9-1.343 9-3V5" />
            <path d="M3 9v4c0 1.657 4.03 3 9 3s9-1.343 9-3V9" />
            <path d="M3 13v4c0 1.657 4.03 3 9 3s9-1.343 9-3v-4" />
          </svg>
          <p style={{ fontSize: 15 }}>ZeroDB server is not running</p>
          <button
            onClick={handleStartServer}
            disabled={loading || !isTauri}
            style={{
              padding: '10px 28px',
              borderRadius: 8,
              border: 'none',
              cursor: isTauri && !loading ? 'pointer' : 'not-allowed',
              background: '#14532d',
              color: '#86efac',
              fontWeight: 700,
              fontSize: 14,
              opacity: loading || !isTauri ? 0.5 : 1,
            }}
          >
            {loading ? 'Starting…' : 'Start Server'}
          </button>
          {!isTauri && (
            <p style={{ fontSize: 12, color: '#444' }}>
              Running outside Tauri — start the API manually on port 8000.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
