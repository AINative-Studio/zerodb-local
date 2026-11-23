'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Check, Plus } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { useProject } from '@/components/providers/project-provider'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { ModeBadge } from '@/components/layout/mode-badge'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CopyField } from '@/components/ui/copy-field'
import { cn, formatNumber, formatRelativeTime } from '@/lib/utils'
import { useMounted } from '@/lib/use-mounted'
import { summarizeEventData } from '@/lib/events'
import type { ProjectUsage } from '@/types'

// Lite mode (SQLite + FAISS + filesystem, the zero-infrastructure default)
// and full mode (Docker stack) report different service keys in /health --
// render whichever set matches `backend` instead of assuming full mode.
const FULL_MODE_SERVICES = [
  { key: 'postgres', name: 'PostgreSQL', role: 'Projects, tables, events, memory' },
  { key: 'qdrant', name: 'Qdrant', role: 'Vector index and search' },
  { key: 'minio', name: 'MinIO', role: 'File storage' },
  { key: 'redpanda', name: 'RedPanda', role: 'Event streaming' },
  { key: 'embeddings', name: 'Embeddings', role: 'Local embeddings (BAAI BGE)' },
] as const

const LITE_MODE_SERVICES = [
  { key: 'sqlite', name: 'SQLite', role: 'Projects, tables, events, memory' },
  { key: 'faiss', name: 'FAISS', role: 'Vector index and search' },
  { key: 'filesystem', name: 'Filesystem', role: 'File storage' },
] as const

const EMPTY_USAGE: ProjectUsage = { vectors: 0, tables: 0, events: 0, memory: 0, files: 0 }

export default function OverviewPage() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 5000,
  })
  const { projects, projectId, project } = useProject()
  const mounted = useMounted()

  const totals = projects.reduce<ProjectUsage>((acc, p) => {
    const u = p.usage ?? EMPTY_USAGE
    return {
      vectors: acc.vectors + (u.vectors ?? 0),
      tables: acc.tables + (u.tables ?? 0),
      events: acc.events + (u.events ?? 0),
      memory: acc.memory + (u.memory ?? 0),
      files: acc.files + (u.files ?? 0),
    }
  }, EMPTY_USAGE)

  const recent = useQuery({
    queryKey: ['events', projectId, 'recent'],
    queryFn: () => apiClient.listEvents(projectId!, { limit: 5 }),
    enabled: !!projectId,
  })

  const services = health.data?.backend === 'lite' ? LITE_MODE_SERVICES : FULL_MODE_SERVICES
  const hasProject = projects.length > 0
  const hasData = totals.vectors + totals.tables > 0

  return (
    <PageShell>
      <PageHeader
        title="Overview"
        description="Your local ZeroDB, running on this machine."
        actions={<ModeBadge />}
      />

      {!(hasProject && hasData) && (
        <section
          aria-labelledby="first-steps"
          className="flex flex-wrap items-center justify-between gap-6 rounded-xl border bg-card p-6"
        >
          <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-3.5">
            <div className="flex flex-col gap-1">
              <h2 id="first-steps" className="font-display text-lg font-semibold">
                Your first five minutes
              </h2>
              <p className="text-muted-foreground">Everything here can be done from the dashboard. No API calls or CLI needed.</p>
            </div>
            <ol className="flex flex-wrap gap-2.5">
              <Step n={1} done={hasProject} label="Create a project" />
              <Step n={2} done={hasData} label="Add a table or vector" />
              <Step n={3} done={false} label="Search it" />
            </ol>
          </div>
          <div className="flex flex-wrap gap-2.5">
            {hasProject ? (
              <>
                <Button asChild>
                  <Link href="/vectors?new=1" className="text-primary-foreground no-underline">
                    <Plus className="h-4 w-4" /> Upsert a vector
                  </Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/tables?new=1" className="text-foreground no-underline">Create a table</Link>
                </Button>
              </>
            ) : (
              <Button asChild>
                <Link href="/projects?new=1" className="text-primary-foreground no-underline">
                  <Plus className="h-4 w-4" /> New project
                </Link>
              </Button>
            )}
          </div>
        </section>
      )}

      <section aria-label="Resource totals" className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-4">
        <Stat href="/projects" label="Projects" value={projects.length} />
        <Stat href="/vectors" label="Vectors" value={totals.vectors} />
        <Stat href="/tables" label="Tables" value={totals.tables} />
        <Stat href="/files" label="Files" value={totals.files} />
        <Stat href="/events" label="Events" value={totals.events} />
      </section>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-4">
        <section aria-labelledby="svc" className="flex flex-col gap-3.5 rounded-xl border bg-card p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 id="svc" className="font-display text-base font-semibold">Services</h2>
            {health.data && (
              <span className={cn('text-[13px] font-semibold', health.data.status === 'healthy' ? 'text-success' : 'text-warning')}>
                {health.data.summary.healthy} of {health.data.summary.total} healthy
              </span>
            )}
          </div>
          {health.isLoading && <p className="text-muted-foreground">Checking services…</p>}
          {health.error && (
            <div role="alert" className="flex items-start gap-2 text-sm">
              <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
              <span>
                Can’t reach the API at <span className="font-mono">{apiClient.baseURL}</span>. {(health.error as Error).message}
              </span>
            </div>
          )}
          {health.data &&
            services.map((svc) => {
              const s = health.data.services?.[svc.key]
              const ok = s?.status === 'healthy'
              return (
                <div key={svc.key} className="flex items-center gap-3 rounded-lg bg-muted px-3.5 py-3">
                  <span aria-hidden="true" className={cn('h-2 w-2 shrink-0 rounded-full', ok ? 'bg-emerald-500' : 'bg-destructive')} />
                  <div className="flex min-w-0 flex-1 flex-col">
                    <strong className="font-semibold">{svc.name}</strong>
                    <span className="text-xs text-muted-foreground">{s?.error ?? svc.role}</span>
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">
                    {s?.latency_ms != null ? `${Math.round(s.latency_ms)} ms` : ok ? 'healthy' : s ? 'unhealthy' : 'not reported'}
                  </span>
                </div>
              )
            })}
          {health.data?.backend === 'lite' && (
            <p className="text-[13px] text-muted-foreground">
              Postgres, Qdrant, MinIO and RedPanda only run in full mode. Lite mode doesn’t need them.
            </p>
          )}
        </section>

        <section aria-labelledby="conn" className="flex flex-col gap-3.5 rounded-xl border bg-card p-5">
          <h2 id="conn" className="font-display text-base font-semibold">Connect your app</h2>
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-muted-foreground">API endpoint</span>
            <CopyField value={mounted ? apiClient.baseURL : ''} label="API endpoint" />
          </div>
          <p className="text-[13px] text-muted-foreground">
            Read from your running config, not hardcoded. See <Link href="/settings">Settings</Link>.
          </p>
        </section>

        <section aria-labelledby="recent" className="flex flex-col gap-2.5 rounded-xl border bg-card p-5">
          <div className="flex items-baseline justify-between">
            <h2 id="recent" className="font-display text-base font-semibold">
              Recent activity {project && <span className="font-mono text-sm font-normal text-muted-foreground">· {project.name}</span>}
            </h2>
            <Link href="/events" className="text-[13px] font-medium">All events</Link>
          </div>
          {!projectId && <p className="text-muted-foreground">Nothing yet. Activity shows up here once you create a project.</p>}
          {recent.data?.length === 0 && <p className="text-muted-foreground">No events in this project yet.</p>}
          {recent.data?.map((e) => (
            <div key={e.id} className="flex items-center gap-2.5 border-b py-2 last:border-b-0">
              <Badge variant="accent" className="rounded">{e.event_type}</Badge>
              <span className="min-w-0 flex-1 truncate text-sm text-muted-foreground">{summarizeEventData(e.event_data, 2)}</span>
              {e.timestamp && <span className="whitespace-nowrap text-xs text-muted-foreground">{formatRelativeTime(e.timestamp)}</span>}
            </div>
          ))}
        </section>
      </div>
    </PageShell>
  )
}

function Step({ n, done, label }: { n: number; done: boolean; label: string }) {
  return (
    <li
      className={cn(
        'flex items-center gap-2 rounded-lg px-3 py-2 font-medium',
        done ? 'bg-success-muted text-success' : 'bg-muted'
      )}
    >
      {done ? (
        <Check aria-hidden="true" className="h-4 w-4" strokeWidth={2.5} />
      ) : (
        <span className="font-mono text-xs text-muted-foreground">{n}</span>
      )}
      {label}
      {done && <span className="sr-only">(done)</span>}
    </li>
  )
}

function Stat({ href, label, value }: { href: string; label: string; value: number }) {
  return (
    <Link
      href={href}
      className="flex flex-col gap-1.5 rounded-xl border bg-card p-[18px] text-foreground no-underline transition-colors hover:border-primary"
    >
      <span className="text-[13px] font-medium text-muted-foreground">{label}</span>
      <span className="font-mono text-[28px] font-medium tracking-tight">{formatNumber(value)}</span>
    </Link>
  )
}
