'use client'

import * as React from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { Copy, Plus, Zap } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { useProject } from '@/components/providers/project-provider'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { EmptyState, ErrorState, LoadingState, RequireProject } from '@/components/layout/states'
import { PublishEventDialog } from '@/components/events/publish-event-dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { countByFamily, eventFamily, filterByFamily, summarizeEventData } from '@/lib/events'
import { cn } from '@/lib/utils'

const LINKS: Record<string, { href: string; label: string }> = {
  vector: { href: '/vectors', label: 'Open Vectors' },
  table: { href: '/tables', label: 'Open Tables' },
  file: { href: '/files', label: 'Open Files' },
  project: { href: '/projects', label: 'Open Projects' },
}

export default function EventsPage() {
  const { project } = useProject()
  const [publishing, setPublishing] = React.useState(false)
  const [live, setLive] = React.useState(true)

  return (
    <PageShell>
      <PageHeader
        scoped
        title="Events"
        description={<>What happened in this project, and events your app publishes. Raw server output is in <Link href="/logs">Logs</Link>.</>}
        actions={
          project && (
            <>
              <Button variant="outline" onClick={() => setLive((l) => !l)} aria-pressed={live}>
                <span aria-hidden="true" className={cn('h-2 w-2 rounded-full', live ? 'bg-emerald-500' : 'bg-muted-foreground')} />
                {live ? 'Live' : 'Paused'}
              </Button>
              <Button onClick={() => setPublishing(true)}>
                <Plus aria-hidden="true" className="h-4 w-4" strokeWidth={2.5} /> Publish event
              </Button>
            </>
          )
        }
      />
      <RequireProject>
        {(projectId) => (
          <>
            <EventFeed projectId={projectId} live={live} onPublish={() => setPublishing(true)} />
            <PublishEventDialog projectId={projectId} open={publishing} onOpenChange={setPublishing} />
          </>
        )}
      </RequireProject>
    </PageShell>
  )
}

function EventFeed({ projectId, live, onPublish }: { projectId: string; live: boolean; onPublish: () => void }) {
  const [family, setFamily] = React.useState('all')
  const [selectedId, setSelectedId] = React.useState<string | null>(null)

  const events = useQuery({
    queryKey: ['events', projectId, 'feed'],
    queryFn: () => apiClient.listEvents(projectId, { limit: 200 }),
    refetchInterval: live ? 3000 : false,
  })

  if (events.isLoading) return <LoadingState label="Loading events" />
  if (events.error) return <ErrorState error={events.error} what="events" />
  const all = events.data ?? []
  if (all.length === 0) {
    return (
      <EmptyState icon={Zap} title="No events yet" action={<Button variant="outline" onClick={onPublish}>Publish a test event</Button>}>
        Events show up here as your app publishes them.
      </EmptyState>
    )
  }

  const families = countByFamily(all)
  const shown = filterByFamily(all, family)
  const current = shown.find((e) => e.id === selectedId) ?? shown[0] ?? null
  const link = current ? LINKS[eventFamily(current.event_type)] : undefined

  return (
    <>
      <div role="group" aria-label="Filter by type" className="flex flex-wrap gap-2">
        {families.map((f) => {
          const on = f.family === family
          return (
            <button
              key={f.family}
              type="button"
              aria-pressed={on}
              onClick={() => setFamily(f.family)}
              className={cn(
                'inline-flex h-9 items-center gap-2 rounded-full border px-3 font-mono text-xs font-medium transition-colors',
                on ? 'border-primary bg-primary text-primary-foreground' : 'bg-card text-foreground hover:bg-muted'
              )}
            >
              {f.family === 'all' ? 'All' : `${f.family}.*`}
              <span className="opacity-80">{f.count}</span>
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap items-start gap-4">
        <section aria-label="Event feed" className="min-w-0 flex-[999_1_480px] overflow-hidden rounded-xl border bg-card">
          <ul>
            {shown.map((e) => {
              const on = current?.id === e.id
              return (
                <li key={e.id} className="border-b last:border-b-0">
                  <button
                    type="button"
                    onClick={() => setSelectedId(e.id)}
                    aria-pressed={on}
                    className={cn('flex w-full flex-wrap items-center gap-3 px-4 py-3 text-left transition-colors', on ? 'bg-accent' : 'hover:bg-muted')}
                  >
                    <span className="w-[72px] font-mono text-xs text-muted-foreground">
                      {e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour12: false }) : '–'}
                    </span>
                    <Badge variant="accent" className="min-w-[128px] rounded">{e.event_type}</Badge>
                    <span className="min-w-[160px] flex-1 truncate text-sm text-muted-foreground">{summarizeEventData(e.event_data)}</span>
                    <span className="text-xs text-muted-foreground">{e.source ?? ''}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>

        {current && (
          <aside aria-label="Event detail" className="flex w-full flex-col gap-3 rounded-xl border bg-card p-[18px] lg:max-w-[380px] lg:flex-[1_1_300px]">
            <div className="flex flex-col gap-0.5">
              <span className="truncate font-mono text-xs text-muted-foreground">{current.id}</span>
              <h2 className="font-mono text-[15px] font-medium">{current.event_type}</h2>
              <span className="text-[13px] text-muted-foreground">
                {current.timestamp ? new Date(current.timestamp).toLocaleString() : 'No timestamp'}
                {current.source && ` · ${current.source}`}
                {current.correlation_id && ` · ${current.correlation_id}`}
              </span>
            </div>
            <pre className="whitespace-pre-wrap break-words rounded-lg bg-terminal p-3.5 font-mono text-xs leading-relaxed text-terminal-foreground">
              {JSON.stringify(current.event_data, null, 2)}
            </pre>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  try {
                    void navigator.clipboard?.writeText(JSON.stringify(current, null, 2))
                  } catch {
                    // clipboard unavailable
                  }
                }}
              >
                <Copy aria-hidden="true" className="h-[15px] w-[15px]" /> Copy JSON
              </Button>
              {link && (
                <Button asChild variant="link" size="sm">
                  <Link href={link.href}>{link.label}</Link>
                </Button>
              )}
            </div>
          </aside>
        )}
      </div>
    </>
  )
}
