'use client'

import * as React from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowDownToLine, ArrowUpFromLine, ArrowUpDown, Check, CloudOff, X } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { ErrorState, LoadingState, RequireProject } from '@/components/layout/states'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Field, Select } from '@/components/ui/form-controls'
import { Segmented } from '@/components/ui/segmented'
import { cn, formatBytes, formatNumber, formatRelativeTime } from '@/lib/utils'
import type { ConflictStrategy, SyncDirection, SyncPlanResult, SyncRunResult } from '@/types'

const STRATEGIES: { value: ConflictStrategy; label: string }[] = [
  { value: 'newest_wins', label: 'Newest change wins' },
  { value: 'local_wins', label: 'This machine wins' },
  { value: 'cloud_wins', label: 'Cloud wins' },
  { value: 'manual', label: 'Ask me for each conflict' },
]

const STATUS_BADGE: Record<string, 'success' | 'warning' | 'destructive' | 'muted'> = {
  completed: 'success',
  in_progress: 'warning',
  pending: 'muted',
  failed: 'destructive',
  rolled_back: 'warning',
}

export default function SyncPage() {
  return (
    <PageShell>
      <PageHeader scoped title="Sync" description="Push this project to ZeroDB Cloud, or pull cloud changes down. You review a plan before anything moves." />
      <RequireProject>{(projectId) => <SyncWorkspace projectId={projectId} />}</RequireProject>
    </PageShell>
  )
}

function SyncWorkspace({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const [direction, setDirection] = React.useState<SyncDirection>('push')
  const [strategy, setStrategy] = React.useState<ConflictStrategy>('newest_wins')
  const [plan, setPlan] = React.useState<SyncPlanResult | null>(null)
  const [result, setResult] = React.useState<SyncRunResult | null>(null)

  const status = useQuery({ queryKey: ['sync', projectId, 'status'], queryFn: () => apiClient.getSyncStatus(projectId), refetchInterval: 10000 })
  const cloud = useQuery({ queryKey: ['cloud-status', projectId], queryFn: () => apiClient.getCloudSyncStatus(projectId), retry: false })
  const history = useQuery({ queryKey: ['sync', projectId, 'history'], queryFn: () => apiClient.listSyncHistory(projectId), retry: false })

  const planMut = useMutation({
    mutationFn: () => apiClient.planSync(projectId, { direction, conflict_strategy: strategy }),
    onSuccess: (p) => {
      setPlan(p)
      setResult(null)
    },
  })

  const runMut = useMutation({
    mutationFn: (planId: string) => apiClient.executeSync(projectId, planId),
    onSuccess: (r) => {
      setResult(r)
      setPlan(null)
      qc.invalidateQueries({ queryKey: ['sync', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  const connected = cloud.data?.is_authenticated

  return (
    <>
      <section aria-label="Sync status" className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
        <StatusTile label="Waiting to sync" value={status.data ? formatNumber(status.data.pending_changes_count) : '–'} hint="local changes since the last sync" />
        <StatusTile
          label="Last sync"
          value={status.data?.last_sync_at ? formatRelativeTime(status.data.last_sync_at) : 'Never'}
          hint={status.data?.last_sync_direction ? `${status.data.last_sync_direction}` : 'no sync has run yet'}
        />
        <StatusTile
          label="ZeroDB Cloud"
          value={cloud.isLoading ? '…' : connected ? 'Connected' : 'Not connected'}
          hint={connected ? 'ready to push and pull' : <Link href="/settings">Connect in Settings</Link>}
        />
      </section>
      {status.error && <ErrorState error={status.error} what="sync status" />}
      {status.data?.sync_in_progress && (
        <p role="status" className="rounded-lg bg-warning-muted px-4 py-3 text-sm font-medium text-warning">A sync is running right now.</p>
      )}

      <section aria-labelledby="plan-h" className="flex flex-col gap-4 rounded-xl border bg-card p-5">
        <h2 id="plan-h" className="font-display text-base font-semibold">Plan a sync</h2>
        {!connected && !cloud.isLoading && (
          <div className="flex items-start gap-2.5 rounded-lg bg-muted px-4 py-3 text-sm">
            <CloudOff aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span>
              This project isn’t connected to ZeroDB Cloud yet, so pushing or pulling will fail. <Link href="/settings">Connect it in Settings</Link>. You can still preview a plan.
            </span>
          </div>
        )}
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold">Direction</span>
            <Segmented<SyncDirection>
              label="Direction"
              value={direction}
              onChange={(d) => {
                setDirection(d)
                setPlan(null)
              }}
              options={[
                { value: 'push', label: <><ArrowUpFromLine aria-hidden="true" className="h-[15px] w-[15px]" /> Push</> },
                { value: 'pull', label: <><ArrowDownToLine aria-hidden="true" className="h-[15px] w-[15px]" /> Pull</> },
                { value: 'bidirectional', label: <><ArrowUpDown aria-hidden="true" className="h-[15px] w-[15px]" /> Both</> },
              ]}
            />
          </div>
          <Field label="If the same thing changed in both places" htmlFor="sync-strategy" className="min-w-[240px]">
            <Select id="sync-strategy" value={strategy} onChange={(e) => { setStrategy(e.target.value as ConflictStrategy); setPlan(null) }}>
              {STRATEGIES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </Select>
          </Field>
          <Button onClick={() => planMut.mutate()} disabled={planMut.isPending}>
            {planMut.isPending ? 'Planning…' : 'Preview sync'}
          </Button>
        </div>
        {planMut.error && <p role="alert" className="text-sm text-destructive">{(planMut.error as Error).message}</p>}

        {plan && <PlanReview plan={plan} running={runMut.isPending} onRun={() => runMut.mutate(plan.plan_id)} onCancel={() => setPlan(null)} />}
        {runMut.error && <p role="alert" className="text-sm text-destructive">{(runMut.error as Error).message}</p>}
        {result && <RunResult result={result} />}
      </section>

      <Conflicts projectId={projectId} />

      <section aria-labelledby="hist-h" className="flex flex-col gap-3">
        <h2 id="hist-h" className="font-display text-base font-semibold">History</h2>
        {history.isLoading && <LoadingState label="Loading history" />}
        {history.error && <ErrorState error={history.error} what="sync history" />}
        {history.data && history.data.items.length === 0 && <p className="text-muted-foreground">No syncs yet.</p>}
        {history.data && history.data.items.length > 0 && (
          <div className="relative overflow-x-auto rounded-xl border bg-card">
            <table className="w-full min-w-[640px] border-collapse text-left">
              <thead>
                <tr className="bg-muted text-xs text-muted-foreground">
                  <th scope="col" className="px-4 py-3 font-semibold">When</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Direction</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Status</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Records</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Size</th>
                </tr>
              </thead>
              <tbody>
                {history.data.items.map((h) => (
                  <tr key={h.id} className="border-t align-top">
                    <td className="px-4 py-3 text-sm">{formatRelativeTime(h.started_at)}</td>
                    <td className="px-4 py-3 font-mono text-[13px]">{h.direction}</td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_BADGE[h.status] ?? 'muted'}>{h.status.replace('_', ' ')}</Badge>
                      {h.error_message && <p className="mt-1 text-xs text-destructive">{h.error_message}</p>}
                    </td>
                    <td className="px-4 py-3 font-mono text-[13px]">{formatNumber(Object.values(h.records_synced ?? {}).reduce((a, b) => a + b, 0))}</td>
                    <td className="px-4 py-3 font-mono text-[13px]">{formatBytes(h.bytes_transferred ?? 0, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}

function StatusTile({ label, value, hint }: { label: string; value: React.ReactNode; hint: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border bg-card p-[18px]">
      <span className="text-[13px] font-medium text-muted-foreground">{label}</span>
      <span className="font-display text-xl font-semibold">{value}</span>
      <span className="text-xs text-muted-foreground">{hint}</span>
    </div>
  )
}

function PlanReview({ plan, running, onRun, onCancel }: { plan: SyncPlanResult; running: boolean; onRun: () => void; onCancel: () => void }) {
  const counts = plan.entity_counts
  const rows: [string, number][] = [
    ['Tables', counts.tables],
    ['Table rows', counts.table_rows],
    ['Vectors', counts.vectors],
    ['Memories', counts.memory],
    ['Events', counts.events],
    ['Files', counts.files],
  ]
  const nothing = rows.every(([, n]) => n === 0) && !plan.schema_changes?.has_changes
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-primary/50 bg-accent/40 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-semibold">
          {plan.direction === 'push' ? 'Push to cloud' : plan.direction === 'pull' ? 'Pull from cloud' : 'Sync both ways'}
        </h3>
        <span className="text-xs text-muted-foreground">
          about {Math.max(1, Math.round(plan.estimated_duration_seconds))}s · {formatBytes(plan.estimated_data_size_bytes, 1)}
        </span>
      </div>
      <dl className="grid grid-cols-[repeat(auto-fit,minmax(110px,1fr))] gap-3">
        {rows.map(([label, n]) => (
          <div key={label} className="flex flex-col">
            <dt className="text-xs text-muted-foreground">{label}</dt>
            <dd className="font-mono font-medium">{formatNumber(n)}</dd>
          </div>
        ))}
      </dl>
      {plan.schema_changes?.has_changes && (
        <div className={cn('rounded-md px-3 py-2 text-sm', plan.schema_changes.is_breaking ? 'bg-destructive/10 text-destructive' : 'bg-muted')}>
          <strong>{plan.schema_changes.is_breaking ? 'Breaking schema changes' : 'Schema changes'}:</strong> {plan.schema_changes.changes.join('; ')}
        </div>
      )}
      {plan.conflicts?.has_conflicts && (
        <p className="text-sm"><strong>{plan.conflicts.conflict_count} conflicts</strong> will be handled as: {STRATEGIES.find((s) => s.value === plan.conflicts.resolution_strategy)?.label ?? plan.conflicts.resolution_strategy}.</p>
      )}
      {plan.warnings?.length > 0 && (
        <ul className="flex flex-col gap-1">
          {plan.warnings.map((w, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
              {w.message}
            </li>
          ))}
        </ul>
      )}
      {plan.steps?.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm font-semibold text-link">{plan.steps.length} steps</summary>
          <ol className="mt-2 flex list-decimal flex-col gap-1 pl-5 text-sm text-muted-foreground">
            {plan.steps.map((s) => <li key={s.step_number}>{s.description}{s.data_count ? ` (${formatNumber(s.data_count)})` : ''}</li>)}
          </ol>
        </details>
      )}
      <div className="flex flex-wrap justify-end gap-2.5">
        <Button variant="outline" onClick={onCancel}>Discard plan</Button>
        <Button onClick={onRun} disabled={running || nothing}>{running ? 'Syncing…' : nothing ? 'Nothing to sync' : 'Run sync'}</Button>
      </div>
    </div>
  )
}

function RunResult({ result }: { result: SyncRunResult }) {
  const ok = result.status === 'completed'
  return (
    <div role="status" className={cn('flex flex-col gap-1 rounded-lg px-4 py-3 text-sm', ok ? 'bg-success-muted text-success' : 'bg-destructive/10 text-destructive')}>
      <strong className="flex items-center gap-2">
        {ok ? <Check aria-hidden="true" className="h-4 w-4" /> : <X aria-hidden="true" className="h-4 w-4" />}
        {ok ? `Synced ${formatNumber(result.records_synced)} records` : `Sync ${result.status.replace('_', ' ')}`}
      </strong>
      <span>{result.successful_steps} of {result.total_steps} steps · {formatBytes(result.bytes_transferred, 1)}</span>
      {result.errors?.map((e, i) => <span key={i}>{e}</span>)}
    </div>
  )
}

function Conflicts({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const conflicts = useQuery({ queryKey: ['sync', projectId, 'conflicts'], queryFn: () => apiClient.listConflicts(projectId), retry: false })
  const resolve = useMutation({
    mutationFn: ({ id, choice }: { id: string; choice: 'local' | 'cloud' }) =>
      apiClient.resolveConflict(projectId, id, choice === 'local' ? 'local_wins' : 'cloud_wins'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sync', projectId, 'conflicts'] }),
  })

  const open = (conflicts.data ?? []).filter((c) => !c.resolved_at)
  if (conflicts.isLoading || conflicts.error || open.length === 0) return null

  return (
    <section aria-labelledby="conf-h" className="flex flex-col gap-3">
      <h2 id="conf-h" className="font-display text-base font-semibold">Conflicts to resolve <span className="font-mono text-sm font-normal text-muted-foreground">{open.length}</span></h2>
      {open.map((c) => (
        <article key={c.id} className="flex flex-col gap-3 rounded-xl border bg-card p-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant="warning">{c.entity_type}</Badge>
            <span className="font-mono text-[13px]">{c.entity_id}</span>
            {c.detected_at && <span className="text-xs text-muted-foreground">{formatRelativeTime(c.detected_at)}</span>}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {(['local', 'cloud'] as const).map((side) => (
              <div key={side} className="flex flex-col gap-2">
                <span className="text-xs font-semibold text-muted-foreground">{side === 'local' ? 'This machine' : 'Cloud'}</span>
                <pre className="max-h-48 overflow-auto rounded-lg bg-terminal p-3 font-mono text-xs text-terminal-foreground">
                  {JSON.stringify(side === 'local' ? c.local_version : c.cloud_version, null, 2)}
                </pre>
                <Button variant="outline" size="sm" className="self-start" onClick={() => resolve.mutate({ id: c.id, choice: side })} disabled={resolve.isPending}>
                  Keep {side === 'local' ? "this machine's" : "the cloud's"} version
                </Button>
              </div>
            ))}
          </div>
        </article>
      ))}
      {resolve.error && <p role="alert" className="text-sm text-destructive">{(resolve.error as Error).message}</p>}
    </section>
  )
}
