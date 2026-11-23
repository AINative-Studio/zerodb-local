'use client'

import * as React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, Select, Textarea } from '@/components/ui/form-controls'
import { COLUMN_TYPE_LABELS, coerceRow, type Column } from '@/lib/schema-builder'

export function AddRowDialog({
  projectId,
  table,
  columns,
  open,
  onOpenChange,
}: {
  projectId: string
  table: string
  columns: Column[]
  open: boolean
  onOpenChange: (o: boolean) => void
}) {
  const qc = useQueryClient()
  const [values, setValues] = React.useState<Record<string, string>>({})
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (open) {
      setValues({})
      setError(null)
    }
  }, [open])

  const insert = useMutation({
    mutationFn: (row: Record<string, unknown>) => apiClient.insertRows(projectId, table, [row]),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rows', projectId, table] })
      onOpenChange(false)
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const r = coerceRow(columns, values)
    if (!r.ok) return setError(r.error)
    setError(null)
    insert.mutate(r.row)
  }

  const set = (k: string, v: string) => setValues((s) => ({ ...s, [k]: v }))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogHeader>
            <DialogTitle>Add row</DialogTitle>
            <DialogDescription>To <span className="font-mono text-foreground">{table}</span>.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            {columns.map((c) => {
              const id = `row-${c.name}`
              const v = values[c.name] ?? ''
              return (
                <Field key={c.name} label={<span className="font-mono">{c.name}</span>} htmlFor={id} required={c.required} hint={COLUMN_TYPE_LABELS[c.type]}>
                  {c.type === 'enum' ? (
                    <Select id={id} value={v} onChange={(e) => set(c.name, e.target.value)}>
                      <option value="">Choose…</option>
                      {(c.options ?? []).filter(Boolean).map((o) => <option key={o}>{o}</option>)}
                    </Select>
                  ) : c.type === 'boolean' ? (
                    <Select id={id} value={v} onChange={(e) => set(c.name, e.target.value)}>
                      <option value="">Not set</option>
                      <option value="true">True</option>
                      <option value="false">False</option>
                    </Select>
                  ) : c.type === 'json' ? (
                    <Textarea id={id} code rows={3} value={v} onChange={(e) => set(c.name, e.target.value)} />
                  ) : (
                    <Input
                      id={id}
                      value={v}
                      onChange={(e) => set(c.name, e.target.value)}
                      type={c.type === 'datetime' ? 'datetime-local' : 'text'}
                      inputMode={c.type === 'integer' || c.type === 'number' ? 'decimal' : undefined}
                    />
                  )}
                </Field>
              )
            })}
            {(error || insert.error) && (
              <p role="alert" className="text-sm font-medium text-destructive">{error ?? (insert.error as Error).message}</p>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={insert.isPending}>{insert.isPending ? 'Adding…' : 'Add row'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
