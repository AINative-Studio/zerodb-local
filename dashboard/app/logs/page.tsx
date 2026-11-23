'use client'

import { useEffect, useRef, useState, type JSX } from 'react';
import { useQuery } from '@tanstack/react-query'
import { Activity, Download, RefreshCw, Search } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/form-controls'
import { cn } from '@/lib/utils'
import type { LogEntry } from '@/types'

const LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const

// Colours are for the always-dark terminal surface, so they're fixed hues
// rather than theme tokens. Each passes AA on --terminal.
const LEVEL_TEXT: Record<string, string> = {
  DEBUG: 'text-slate-400',
  INFO: 'text-cyan-400',
  WARNING: 'text-amber-400',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-300 font-semibold',
}
const LEVEL_DOT: Record<string, string> = {
  DEBUG: 'bg-slate-400',
  INFO: 'bg-cyan-400',
  WARNING: 'bg-amber-400',
  ERROR: 'bg-red-400',
  CRITICAL: 'bg-red-500',
}
const ROW_TINT: Record<string, string> = {
  WARNING: 'bg-amber-400/[0.07]',
  ERROR: 'bg-red-400/10',
  CRITICAL: 'bg-red-400/15',
}

export default function LogsPage(): JSX.Element {
  const [service, setService] = useState('')
  const [hidden, setHidden] = useState<Record<string, boolean>>({})
  const [search, setSearch] = useState('')
  const [live, setLive] = useState(true)
  const [sinceMinutes, setSinceMinutes] = useState(60)
  const [limit, setLimit] = useState(500)
  const endRef = useRef<HTMLDivElement>(null)

  const { data: services } = useQuery({
    queryKey: ['log-services'],
    queryFn: () => apiClient.getAvailableServices(),
  })

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['logs', service, limit, sinceMinutes],
    queryFn: () => apiClient.getLogs(service || undefined, undefined, limit, sinceMinutes),
    refetchInterval: live ? 5000 : false,
  })

  const logs = data?.logs ?? []
  const counts = logs.reduce<Record<string, number>>((acc, l) => {
    acc[l.level] = (acc[l.level] ?? 0) + 1
    return acc
  }, {})
  const q = search.trim().toLowerCase()
  const shown = logs.filter(
    (l) => !hidden[l.level] && (!q || `${l.message} ${l.service} ${l.source ?? ''}`.toLowerCase().includes(q))
  )

  useEffect(() => {
    if (live) endRef.current?.scrollIntoView?.({ block: 'nearest' })
  }, [shown.length, live])

  const exportLogs = () => {
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `zerodb-logs-${new Date().toISOString()}.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <PageShell>
      <PageHeader
        title="Logs"
        description="Server output from the API, for debugging."
        actions={
          <>
            <Button variant="outline" onClick={() => setLive((l) => !l)} aria-pressed={live}>
              <span aria-hidden="true" className={cn('h-2 w-2 rounded-full', live ? 'bg-emerald-500' : 'bg-muted-foreground')} />
              {live ? 'Live' : 'Paused'}
            </Button>
            <Button variant="outline" size="icon" onClick={() => refetch()} disabled={isFetching} aria-label="Refresh logs">
              <RefreshCw aria-hidden="true" className={cn('h-4 w-4', isFetching && 'animate-spin')} />
            </Button>
            <Button variant="outline" onClick={exportLogs} disabled={!logs.length}>
              <Download aria-hidden="true" className="h-4 w-4" /> Export
            </Button>
          </>
        }
      />

      <section aria-label="Filters" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-[240px] flex-[1_1_300px] max-w-[460px]">
            <label htmlFor="log-search" className="sr-only">Search logs</label>
            <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input id="log-search" placeholder="Search message, service or source" value={search} onChange={(e) => setSearch(e.target.value)} className="h-10 pl-9" />
          </div>
          <label htmlFor="log-service" className="sr-only">Service</label>
          <Select id="log-service" value={service} onChange={(e) => setService(e.target.value)} className="h-10 w-auto">
            <option value="">All services</option>
            {services?.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
          <label htmlFor="log-range" className="sr-only">Time range</label>
          <Select id="log-range" value={sinceMinutes} onChange={(e) => setSinceMinutes(Number(e.target.value))} className="h-10 w-auto">
            <option value={5}>Last 5 minutes</option>
            <option value={15}>Last 15 minutes</option>
            <option value={60}>Last hour</option>
            <option value={360}>Last 6 hours</option>
            <option value={1440}>Last 24 hours</option>
          </Select>
          <label htmlFor="log-limit" className="sr-only">Max entries</label>
          <Select id="log-limit" value={limit} onChange={(e) => setLimit(Number(e.target.value))} className="h-10 w-auto">
            {[100, 250, 500, 1000].map((n) => <option key={n} value={n}>{n} lines</option>)}
          </Select>
        </div>

        {/* Replaces the six stat cards: one row of level toggles. Empty
            levels stay quiet instead of shouting a row of zeros. */}
        <div role="group" aria-label="Levels" className="flex flex-wrap gap-1.5">
          {LEVELS.map((lvl) => {
            const n = counts[lvl] ?? 0
            const on = !hidden[lvl]
            return (
              <button
                key={lvl}
                type="button"
                aria-pressed={on}
                onClick={() => setHidden((h) => ({ ...h, [lvl]: on }))}
                className={cn(
                  'inline-flex h-9 items-center gap-1.5 rounded-lg border px-2.5 font-mono text-xs font-medium transition-colors',
                  on && n > 0 ? 'border-border bg-card text-foreground' : 'border-transparent text-muted-foreground',
                  !on && 'line-through'
                )}
              >
                <span aria-hidden="true" className={cn('h-[7px] w-[7px] rounded-full', LEVEL_DOT[lvl])} />
                {lvl} <span className="opacity-75">{n}</span>
              </button>
            )
          })}
        </div>
      </section>

      <section aria-label="Log stream" className="overflow-hidden rounded-xl border bg-terminal">
        <div className="max-h-[640px] overflow-auto">
          {isLoading ? (
            <p className="px-4 py-10 text-center text-sm text-terminal-foreground">Loading logs…</p>
          ) : error ? (
            <p role="alert" className="px-4 py-10 text-center text-sm text-red-300">{(error as Error).message}</p>
          ) : shown.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-12 text-terminal-foreground">
              <Activity aria-hidden="true" className="h-10 w-10 opacity-50" />
              <p className="text-sm">{q || Object.values(hidden).some(Boolean) ? 'No lines match these filters.' : 'No log lines in this time range.'}</p>
            </div>
          ) : (
            <div className="min-w-[760px] py-1.5 font-mono text-[12.5px] leading-normal">
              {shown.map((l, i) => (
                <LogLine key={`${l.timestamp}-${i}`} log={l} />
              ))}
              <div ref={endRef} />
            </div>
          )}
        </div>
      </section>

      {data && (
        <p className="text-[13px] text-muted-foreground">
          {shown.length} of {data.total_count ?? logs.length} lines · {new Date(data.time_range_start).toLocaleTimeString()}–
          {new Date(data.time_range_end).toLocaleTimeString()}
          {live && ' · refreshing every 5 seconds'}
        </p>
      )}
    </PageShell>
  )
}

function LogLine({ log }: { log: LogEntry }) {
  return (
    <div className={cn('grid grid-cols-[96px_76px_120px_minmax(0,1fr)] gap-3.5 px-4 py-[5px]', ROW_TINT[log.level])}>
      <span className="text-slate-400">
        {new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </span>
      <span className={LEVEL_TEXT[log.level] ?? 'text-slate-300'}>{log.level}</span>
      <span className="truncate text-cyan-300">{log.service}</span>
      <span className="whitespace-pre-wrap break-words text-slate-300">{log.message}</span>
    </div>
  )
}
