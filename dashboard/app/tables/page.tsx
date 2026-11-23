'use client'

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Table2, Trash2 } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { EmptyState, ErrorState, LoadingState, RequireProject } from '@/components/layout/states'
import { CreateTableDialog } from '@/components/tables/create-table-dialog'
import { AddRowDialog } from '@/components/tables/add-row-dialog'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Button } from '@/components/ui/button'
import { useProject } from '@/components/providers/project-provider'
import { schemaToColumns } from '@/lib/schema-builder'
import { cn } from '@/lib/utils'
import { useNewParam } from '@/lib/use-new-param'
import type { Table } from '@/types'

export default function TablesPage() {
  const { project } = useProject()
  const [open, setOpen] = useNewParam()
  const [selected, setSelected] = React.useState<string | null>(null)

  return (
    <PageShell>
      <PageHeader
        scoped
        title="Tables"
        actions={
          project && (
            <Button onClick={() => setOpen(true)}>
              <Plus aria-hidden="true" className="h-4 w-4" strokeWidth={2.5} /> Create table
            </Button>
          )
        }
      />
      <RequireProject>
        {(projectId) => (
          <>
            <TableBrowser projectId={projectId} selected={selected} onSelect={setSelected} onCreate={() => setOpen(true)} />
            <CreateTableDialog projectId={projectId} open={open} onOpenChange={setOpen} onCreated={setSelected} />
          </>
        )}
      </RequireProject>
    </PageShell>
  )
}

function TableBrowser({
  projectId,
  selected,
  onSelect,
  onCreate,
}: {
  projectId: string
  selected: string | null
  onSelect: (n: string | null) => void
  onCreate: () => void
}) {
  const tables = useQuery({
    queryKey: ['tables', projectId],
    queryFn: () => apiClient.listTables(projectId),
  })

  if (tables.isLoading) return <LoadingState label="Loading tables" />
  if (tables.error) return <ErrorState error={tables.error} what="tables" />
  const list = tables.data ?? []
  if (list.length === 0) {
    return (
      <EmptyState icon={Table2} title="No tables yet" action={<Button onClick={onCreate}><Plus aria-hidden="true" className="h-4 w-4" /> Create your first table</Button>}>
        Describe your columns in plain words, or paste a JSON schema.
      </EmptyState>
    )
  }

  const current = list.find((t) => t.name === selected) ?? list[0]

  return (
    <div className="flex flex-wrap items-start gap-4">
      <nav aria-label="Tables in this project" className="flex w-full flex-col gap-1.5 sm:w-64">
        {list.map((t) => {
          const on = t.name === current.name
          const count = Object.keys((t.schema?.fields ?? t.schema) || {}).length
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onSelect(t.name)}
              aria-current={on ? 'true' : undefined}
              className={cn(
                'flex flex-col gap-0.5 rounded-[10px] border px-3.5 py-3 text-left transition-colors',
                on ? 'border-primary bg-accent' : 'bg-card hover:bg-muted'
              )}
            >
              <span className="font-mono font-medium">{t.name}</span>
              <span className="text-xs text-muted-foreground">{count} {count === 1 ? 'column' : 'columns'}</span>
            </button>
          )
        })}
      </nav>
      <RowViewer projectId={projectId} table={current} onDeleted={() => onSelect(null)} />
    </div>
  )
}

function RowViewer({ projectId, table, onDeleted }: { projectId: string; table: Table; onDeleted: () => void }) {
  const qc = useQueryClient()
  const [adding, setAdding] = React.useState(false)
  const [confirm, setConfirm] = React.useState(false)
  const columns = schemaToColumns(table.schema ?? {})

  const rows = useQuery({
    queryKey: ['rows', projectId, table.name],
    queryFn: () => apiClient.queryTable(projectId, table.name, { limit: 100 }),
  })

  const drop = useMutation({
    mutationFn: () => apiClient.deleteTable(projectId, table.name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tables', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
      setConfirm(false)
      onDeleted()
    },
  })

  return (
    <section aria-label={`${table.name} rows`} className="flex min-w-0 flex-[999_1_480px] flex-col rounded-xl border bg-card">
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-b px-4 py-3.5">
        <div className="flex min-w-0 flex-col">
          <h2 className="font-mono text-[15px] font-medium">{table.name}</h2>
          {table.description && <p className="text-xs text-muted-foreground">{table.description}</p>}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setAdding(true)}>
            <Plus aria-hidden="true" className="h-[15px] w-[15px]" strokeWidth={2.5} /> Add row
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label={`Delete table ${table.name}`} onClick={() => setConfirm(true)}>
            <Trash2 aria-hidden="true" className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {rows.isLoading && <LoadingState label="Loading rows" />}
      {rows.error && <div className="p-4"><ErrorState error={rows.error} what="rows" /></div>}
      {rows.data && rows.data.length === 0 && (
        <p className="px-4 py-10 text-center text-muted-foreground">No rows yet. Add one to see it here.</p>
      )}
      {rows.data && rows.data.length > 0 && (
        <div className="relative overflow-x-auto">
          <table className="w-full min-w-[620px] border-collapse text-left">
            <thead>
              <tr className="bg-muted text-xs text-muted-foreground">
                <th scope="col" className="px-4 py-2.5 font-semibold">id</th>
                {columns.map((c) => (
                  <th key={c.name} scope="col" className="px-4 py-2.5 font-semibold">
                    {c.name} <span className="font-mono font-normal">{c.type}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.data.map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[13px] text-muted-foreground">{r.id.slice(0, 8)}</td>
                  {columns.map((c) => {
                    const v = r.data?.[c.name]
                    return (
                      <td key={c.name} className="px-4 py-3 text-sm">
                        {v === undefined || v === null ? <span className="text-muted-foreground">–</span> : typeof v === 'object' ? <code className="font-mono text-xs">{JSON.stringify(v)}</code> : String(v)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AddRowDialog projectId={projectId} table={table.name} columns={columns} open={adding} onOpenChange={setAdding} />
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title={`Delete ${table.name}?`}
        confirmLabel="Delete table"
        onConfirm={() => drop.mutate()}
        pending={drop.isPending}
        error={drop.error}
      >
        The table and all its rows are removed. This can’t be undone.
      </ConfirmDialog>
    </section>
  )
}
