'use client'

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Brain, Plus, Search, Trash2 } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { useProject } from '@/components/providers/project-provider'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { EmptyState, ErrorState, LoadingState, RequireProject } from '@/components/layout/states'
import { AddMemoryDialog } from '@/components/memory/add-memory-dialog'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn, formatNumber, formatRelativeTime } from '@/lib/utils'
import { useNewParam } from '@/lib/use-new-param'
import type { MemoryRecord, MemorySession } from '@/types'

const ROLE_STYLE: Record<string, string> = {
  user: 'bg-muted',
  assistant: 'bg-accent',
  system: 'border border-dashed bg-card',
}

export default function MemoryPage() {
  const { project } = useProject()
  const [open, setOpen] = useNewParam()
  const [selected, setSelected] = React.useState<MemorySession | null>(null)

  return (
    <PageShell>
      <PageHeader
        scoped
        title="Memory"
        description="What your agents remember: conversations grouped by session, searchable by meaning."
        actions={
          project && (
            <Button onClick={() => setOpen(true)}>
              <Plus aria-hidden="true" className="h-4 w-4" strokeWidth={2.5} /> Add memory
            </Button>
          )
        }
      />
      <RequireProject>
        {(projectId) => (
          <>
            <MemoryBrowser projectId={projectId} selected={selected} onSelect={setSelected} onAdd={() => setOpen(true)} />
            <AddMemoryDialog
              projectId={projectId}
              open={open}
              onOpenChange={setOpen}
              defaults={selected ? { agentId: selected.agent_id, sessionId: selected.session_id } : undefined}
            />
          </>
        )}
      </RequireProject>
    </PageShell>
  )
}

function MemoryBrowser({
  projectId,
  selected,
  onSelect,
  onAdd,
}: {
  projectId: string
  selected: MemorySession | null
  onSelect: (s: MemorySession | null) => void
  onAdd: () => void
}) {
  const [agent, setAgent] = React.useState('')
  const [draft, setDraft] = React.useState('')
  const [query, setQuery] = React.useState('')

  const sessions = useQuery({
    queryKey: ['memory', projectId, 'sessions', agent.trim()],
    queryFn: () => apiClient.listMemorySessions(projectId, { agentId: agent.trim() || undefined }),
  })

  const search = useQuery({
    queryKey: ['memory', projectId, 'search', query],
    queryFn: () => apiClient.searchMemory(projectId, { query, limit: 20 }),
    enabled: !!query,
  })

  const list = sessions.data ?? []
  const current = list.find((s) => s.session_id === selected?.session_id) ?? list[0] ?? null

  // Keep the page's selection in step with what's on screen, so "Add to
  // session" targets the conversation the person is looking at.
  React.useEffect(() => {
    if (current && current.session_id !== selected?.session_id) onSelect(current)
  }, [current, selected, onSelect])

  return (
    <>
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault()
          setQuery(draft.trim())
        }}
        className="flex flex-wrap items-center gap-2.5"
      >
        <div className="relative min-w-[260px] flex-[1_1_360px]">
          <label htmlFor="mq" className="sr-only">Search memory by meaning</label>
          <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input id="mq" placeholder="Search memory by meaning, e.g. what did they say about pricing" value={draft} onChange={(e) => setDraft(e.target.value)} className="pl-9" />
        </div>
        <div className="w-44">
          <label htmlFor="magent" className="sr-only">Agent</label>
          <Input id="magent" placeholder="All agents" value={agent} onChange={(e) => setAgent(e.target.value)} className="font-mono" />
        </div>
        <Button type="submit" variant="outline">Search</Button>
        {query && <Button type="button" variant="ghost" onClick={() => { setQuery(''); setDraft('') }}>Clear</Button>}
      </form>

      {query ? (
        <section aria-label="Search results" className="flex flex-col gap-2">
          {search.isLoading && <LoadingState label="Searching" />}
          {search.error && <ErrorState error={search.error} what="search results" />}
          {search.data?.length === 0 && <EmptyState icon={Search} title="No matches">Try different wording.</EmptyState>}
          {search.data?.map((m) => (
            <article key={m.id} className="flex flex-col gap-1.5 rounded-xl border bg-card p-4">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="font-mono text-success">{m.score.toFixed(2)}</span>
                <Badge variant="muted" className="rounded font-mono font-normal">{m.role}</Badge>
                <span className="font-mono text-muted-foreground">{m.agent_id}</span>
                {m.session_id && (
                  <button
                    type="button"
                    className="font-mono text-link hover:underline"
                    onClick={() => {
                      onSelect({ session_id: m.session_id!, agent_id: m.agent_id, message_count: 0 })
                      setQuery('')
                      setDraft('')
                    }}
                  >
                    {m.session_id}
                  </button>
                )}
              </div>
              <p className="whitespace-pre-wrap text-sm">{m.content}</p>
            </article>
          ))}
        </section>
      ) : sessions.isLoading ? (
        <LoadingState label="Loading sessions" />
      ) : sessions.error ? (
        <ErrorState error={sessions.error} what="memory" />
      ) : list.length === 0 ? (
        <EmptyState icon={Brain} title="No memory yet" action={<Button onClick={onAdd}><Plus aria-hidden="true" className="h-4 w-4" /> Add the first memory</Button>}>
          Agents store messages here through the API or MCP. You can also add one by hand.
        </EmptyState>
      ) : (
        <div className="flex flex-wrap items-start gap-4">
          <nav aria-label="Sessions" className="flex w-full flex-col gap-1.5 sm:w-72">
            {list.map((s) => {
              const on = s.session_id === current?.session_id
              return (
                <button
                  key={s.session_id}
                  type="button"
                  onClick={() => onSelect(s)}
                  aria-current={on ? 'true' : undefined}
                  className={cn('flex flex-col gap-0.5 rounded-[10px] border px-3.5 py-3 text-left transition-colors', on ? 'border-primary bg-accent' : 'bg-card hover:bg-muted')}
                >
                  <span className="truncate font-mono text-[13px] font-medium">{s.session_id}</span>
                  <span className="text-xs text-muted-foreground">
                    {s.agent_id} · {formatNumber(s.message_count)} {s.message_count === 1 ? 'message' : 'messages'}
                    {s.last_message_at && ` · ${formatRelativeTime(s.last_message_at)}`}
                  </span>
                </button>
              )
            })}
          </nav>
          {current && <Conversation projectId={projectId} session={current} onAdd={onAdd} onDeleted={() => onSelect(null)} />}
        </div>
      )}
    </>
  )
}

function Conversation({
  projectId,
  session,
  onAdd,
  onDeleted,
}: {
  projectId: string
  session: MemorySession
  onAdd: () => void
  onDeleted: () => void
}) {
  const qc = useQueryClient()
  const [confirm, setConfirm] = React.useState(false)

  const ctx = useQuery({
    queryKey: ['memory', projectId, 'context', session.session_id],
    queryFn: () => apiClient.getMemoryContext(projectId, session.session_id),
  })

  const remove = useMutation({
    mutationFn: () => apiClient.deleteMemorySession(projectId, session.session_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memory', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
      setConfirm(false)
      onDeleted()
    },
  })

  return (
    <section aria-label={`Session ${session.session_id}`} className="flex min-w-0 flex-[999_1_480px] flex-col rounded-xl border bg-card">
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-b px-4 py-3.5">
        <div className="flex min-w-0 flex-col">
          <h2 className="truncate font-mono text-[15px] font-medium">{session.session_id}</h2>
          {ctx.data && (
            <p className="text-xs text-muted-foreground">
              {session.agent_id} · {formatNumber(ctx.data.message_count)} messages · about {formatNumber(ctx.data.estimated_tokens)} tokens
              {ctx.data.truncated && ' · showing the most recent'}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onAdd}>
            <Plus aria-hidden="true" className="h-[15px] w-[15px]" strokeWidth={2.5} /> Add to session
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label={`Delete session ${session.session_id}`} onClick={() => setConfirm(true)}>
            <Trash2 aria-hidden="true" className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {ctx.isLoading && <LoadingState label="Loading messages" />}
      {ctx.error && <div className="p-4"><ErrorState error={ctx.error} what="this session" /></div>}
      {ctx.data && (
        <ol className="flex flex-col gap-3 p-4">
          {ctx.data.messages.map((m: MemoryRecord) => (
            <li key={m.id} className={cn('flex flex-col gap-1 rounded-xl px-4 py-3', ROLE_STYLE[m.role] ?? 'bg-muted', m.role === 'assistant' && 'sm:ml-10', m.role === 'user' && 'sm:mr-10')}>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span className="font-semibold capitalize text-foreground">{m.role}</span>
                {m.created_at && <span>{formatRelativeTime(m.created_at)}</span>}
                {Object.entries(m.metadata ?? {}).slice(0, 3).map(([k, v]) => (
                  <span key={k} className="font-mono">{k}: {String(v)}</span>
                ))}
              </div>
              <p className="whitespace-pre-wrap text-sm">{m.content}</p>
            </li>
          ))}
        </ol>
      )}

      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title={`Delete session ${session.session_id}?`}
        confirmLabel="Delete session"
        onConfirm={() => remove.mutate()}
        pending={remove.isPending}
        error={remove.error}
      >
        Every message in this session is removed from the agent’s memory. This can’t be undone.
      </ConfirmDialog>
    </section>
  )
}
