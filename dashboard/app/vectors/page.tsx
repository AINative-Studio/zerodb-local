'use client'

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Trash2, Waypoints } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { useProject } from '@/components/providers/project-provider'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { EmptyState, ErrorState, LoadingState, RequireProject } from '@/components/layout/states'
import { UpsertVectorDialog } from '@/components/vectors/upsert-vector-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useNewParam } from '@/lib/use-new-param'
import type { Vector, VectorSearchResult } from '@/types'

type Row = (Vector | VectorSearchResult) & { score?: number }

export default function VectorsPage() {
  const { project } = useProject()
  const [open, setOpen] = useNewParam()

  return (
    <PageShell>
      <PageHeader
        scoped
        title="Vectors"
        actions={
          project && (
            <Button onClick={() => setOpen(true)}>
              <Plus aria-hidden="true" className="h-4 w-4" strokeWidth={2.5} /> Upsert vector
            </Button>
          )
        }
      />
      <RequireProject>
        {(projectId) => (
          <>
            <VectorBrowser projectId={projectId} onCreate={() => setOpen(true)} />
            <UpsertVectorDialog projectId={projectId} projectName={project?.name} open={open} onOpenChange={setOpen} />
          </>
        )}
      </RequireProject>
    </PageShell>
  )
}

function VectorBrowser({ projectId, onCreate }: { projectId: string; onCreate: () => void }) {
  const qc = useQueryClient()
  const [namespace, setNamespace] = React.useState('')
  const [draft, setDraft] = React.useState('')
  const [query, setQuery] = React.useState('')

  const ns = namespace.trim() || undefined

  const list = useQuery({
    queryKey: ['vectors', projectId, 'list', ns],
    queryFn: () => apiClient.listVectors(projectId, ns),
    enabled: !query,
  })
  const search = useQuery({
    queryKey: ['vectors', projectId, 'search', ns, query],
    queryFn: () => apiClient.searchVectors(projectId, { query, namespace: ns, limit: 20 }),
    enabled: !!query,
  })

  const remove = useMutation({
    mutationFn: (vectorId: string) => apiClient.deleteVector(projectId, vectorId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vectors', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  const active = query ? search : list
  const rows: Row[] = (active.data as Row[] | undefined) ?? []

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
          <label htmlFor="vq" className="sr-only">Search by meaning</label>
          <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input id="vq" placeholder="Search by meaning, e.g. how do I get a refund" value={draft} onChange={(e) => setDraft(e.target.value)} className="pl-9" />
        </div>
        <div className="w-44">
          <label htmlFor="vns" className="sr-only">Namespace</label>
          <Input id="vns" placeholder="All namespaces" value={namespace} onChange={(e) => setNamespace(e.target.value)} className="font-mono" />
        </div>
        <Button type="submit" variant="outline">Search</Button>
        {query && (
          <Button type="button" variant="ghost" onClick={() => { setQuery(''); setDraft('') }}>Clear</Button>
        )}
      </form>

      {active.isLoading && <LoadingState label={query ? 'Searching' : 'Loading vectors'} />}
      {active.error && <ErrorState error={active.error} what="vectors" />}

      {!active.isLoading && !active.error && rows.length === 0 && (
        query ? (
          <EmptyState icon={Search} title="No matches">Try different wording, or clear the namespace filter.</EmptyState>
        ) : (
          <EmptyState icon={Waypoints} title="No vectors yet" action={<Button onClick={onCreate}><Plus aria-hidden="true" className="h-4 w-4" /> Upsert your first vector</Button>}>
            Paste some text and we’ll turn it into a searchable vector.
          </EmptyState>
        )
      )}

      {rows.length > 0 && (
        <div className="relative overflow-x-auto rounded-xl border bg-card">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead>
              <tr className="bg-muted text-xs text-muted-foreground">
                {query && <th scope="col" className="px-4 py-3 font-semibold">Score</th>}
                <th scope="col" className="px-4 py-3 font-semibold">ID</th>
                <th scope="col" className="px-4 py-3 font-semibold">Document</th>
                <th scope="col" className="px-4 py-3 font-semibold">Namespace</th>
                <th scope="col" className="px-4 py-3 font-semibold">Metadata</th>
                <th scope="col" className="px-4 py-3"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t align-top">
                  {query && <td className="px-4 py-3.5 font-mono text-[13px] text-success">{r.score?.toFixed(2)}</td>}
                  <td className="whitespace-nowrap px-4 py-3.5 font-mono text-[13px]">{r.vector_id}</td>
                  <td className="max-w-[420px] px-4 py-3.5"><span className="line-clamp-2">{r.document}</span></td>
                  <td className="px-4 py-3.5 font-mono text-[13px] text-muted-foreground">{r.namespace}</td>
                  <td className="px-4 py-3.5">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(r.metadata ?? {}).slice(0, 3).map(([k, v]) => (
                        <Badge key={k} variant="muted" className="rounded font-mono font-normal">{k}: {String(v)}</Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button variant="ghost" size="icon-sm" aria-label={`Delete ${r.vector_id}`} onClick={() => remove.mutate(r.vector_id)} disabled={remove.isPending}>
                      <Trash2 aria-hidden="true" className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {remove.error && <p role="alert" className="text-sm text-destructive">{(remove.error as Error).message}</p>}
    </>
  )
}
