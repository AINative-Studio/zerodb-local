'use client'

import * as React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Braces, Plus, X } from 'lucide-react'
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
import { Segmented } from '@/components/ui/segmented'
import {
  COLUMN_TYPE_LABELS,
  columnsToSchema,
  parseSchemaJson,
  validateColumns,
  validateTableName,
  type Column,
  type ColumnType,
} from '@/lib/schema-builder'
import { getFormMode, type FormMode } from '@/lib/preferences'

const STARTER: Column[] = [{ name: '', type: 'string', required: false }]

export function CreateTableDialog({
  projectId,
  open,
  onOpenChange,
  onCreated,
}: {
  projectId: string
  open: boolean
  onOpenChange: (o: boolean) => void
  onCreated?: (name: string) => void
}) {
  const qc = useQueryClient()
  const [mode, setMode] = React.useState<FormMode>('guided')
  const [name, setName] = React.useState('')
  const [description, setDescription] = React.useState('')
  const [columns, setColumns] = React.useState<Column[]>(STARTER)
  const [json, setJson] = React.useState('')
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!open) return
    // Resetting a controlled dialog's form state when it opens, keyed on
    // the `open` prop itself: a documented, intended use of this pattern,
    // not the derived-state anti-pattern the rule targets. getFormMode()
    // reads localStorage, an impure read render must not perform.
    /* eslint-disable react-hooks/set-state-in-effect */
    setMode(getFormMode())
    setName('')
    setDescription('')
    setColumns(STARTER)
    setJson(JSON.stringify(columnsToSchema(STARTER), null, 2))
    setError(null)
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [open])

  const switchMode = (next: FormMode) => {
    if (next === mode) return
    if (next === 'advanced') {
      setJson(JSON.stringify(columnsToSchema(columns), null, 2))
    } else {
      const parsed = parseSchemaJson(json)
      if (!parsed.ok) return setError(`${parsed.error} Fix it to switch back to the builder.`)
      setColumns(parsed.columns.length ? parsed.columns : STARTER)
    }
    setError(null)
    setMode(next)
  }

  const create = useMutation({
    mutationFn: (cols: Column[]) =>
      apiClient.createTable(projectId, {
        table_name: name.trim(),
        schema: columnsToSchema(cols),
        ...(description.trim() ? { description: description.trim() } : {}),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tables', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
      onCreated?.(name.trim())
      onOpenChange(false)
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const nameErr = validateTableName(name)
    if (nameErr) return setError(nameErr)
    let cols = columns
    if (mode === 'advanced') {
      const parsed = parseSchemaJson(json)
      if (!parsed.ok) return setError(parsed.error)
      cols = parsed.columns
    }
    const colErr = validateColumns(cols)
    if (colErr) return setError(colErr)
    setError(null)
    create.mutate(cols)
  }

  const update = (i: number, patch: Partial<Column>) =>
    setColumns((cs) => cs.map((c, j) => (j === i ? { ...c, ...patch } : c)))

  const jsonValid = mode === 'advanced' ? parseSchemaJson(json) : null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogHeader>
            <DialogTitle>Create table</DialogTitle>
            <DialogDescription>Describe your columns. Every row also gets an id and created_at automatically.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Segmented
              label="Input mode"
              value={mode}
              onChange={switchMode}
              options={[
                { value: 'guided', label: 'Column builder' },
                { value: 'advanced', label: <><Braces aria-hidden="true" className="h-[15px] w-[15px]" /> JSON schema</> },
              ]}
            />
            <div className="grid gap-3.5 sm:grid-cols-2">
              <Field label="Table name" htmlFor="ct-name" required hint="Letters, numbers and underscores.">
                <Input id="ct-name" autoFocus value={name} onChange={(e) => setName(e.target.value)} className="font-mono" aria-describedby="ct-name-hint" />
              </Field>
              <Field label="Description" htmlFor="ct-desc" optional>
                <Input id="ct-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
              </Field>
            </div>

            {mode === 'guided' ? (
              <fieldset className="flex flex-col gap-2">
                <legend className="mb-2 text-sm font-semibold">Columns</legend>
                <div aria-hidden="true" className="hidden grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_96px_36px] gap-2 text-xs font-semibold text-muted-foreground sm:grid">
                  <span>Name</span><span>Type</span><span /><span />
                </div>
                {columns.map((c, i) => (
                  <div key={i} className="flex flex-col gap-2 rounded-lg sm:grid sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_96px_36px] sm:items-center">
                    <Input aria-label={`Column ${i + 1} name`} placeholder="e.g. subject" value={c.name} onChange={(e) => update(i, { name: e.target.value })} className="h-10 font-mono text-[13px]" />
                    <Select aria-label={`Column ${i + 1} type`} value={c.type} onChange={(e) => update(i, { type: e.target.value as ColumnType })} className="h-10">
                      {(Object.keys(COLUMN_TYPE_LABELS) as ColumnType[]).map((t) => (
                        <option key={t} value={t}>{COLUMN_TYPE_LABELS[t]}</option>
                      ))}
                    </Select>
                    <label className="inline-flex min-h-10 items-center gap-2 text-sm">
                      <input type="checkbox" checked={c.required} onChange={(e) => update(i, { required: e.target.checked })} className="h-[18px] w-[18px] accent-cyan-600" />
                      Required
                    </label>
                    <Button type="button" variant="ghost" size="icon-sm" aria-label={`Remove column ${i + 1}`} onClick={() => setColumns((cs) => (cs.length > 1 ? cs.filter((_, j) => j !== i) : STARTER))}>
                      <X aria-hidden="true" className="h-4 w-4" />
                    </Button>
                    {c.type === 'enum' && (
                      <Input
                        aria-label={`Column ${i + 1} options`}
                        placeholder="Options, comma separated, e.g. open, pending, closed"
                        value={(c.options ?? []).join(', ')}
                        onChange={(e) => update(i, { options: e.target.value.split(',').map((o) => o.trim()) })}
                        className="h-10 text-[13px] sm:col-span-3"
                      />
                    )}
                  </div>
                ))}
                <Button type="button" variant="link" className="self-start" onClick={() => setColumns((cs) => [...cs, { name: '', type: 'string', required: false }])}>
                  <Plus aria-hidden="true" className="h-[15px] w-[15px]" strokeWidth={2.5} /> Add column
                </Button>
              </fieldset>
            ) : (
              <Field
                label="Schema"
                htmlFor="ct-json"
                hint={
                  jsonValid?.ok ? (
                    <span className="font-medium text-success">Valid schema · {jsonValid.columns.length} {jsonValid.columns.length === 1 ? 'column' : 'columns'}</span>
                  ) : (
                    'Shape: { "fields": { "name": { "type": "string", "required": true } } }'
                  )
                }
              >
                <Textarea id="ct-json" code rows={12} value={json} onChange={(e) => { setJson(e.target.value); setError(null) }} aria-describedby="ct-json-hint" />
              </Field>
            )}

            {(error || create.error) && (
              <p role="alert" className="text-sm font-medium text-destructive">{error ?? (create.error as Error).message}</p>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}>{create.isPending ? 'Creating…' : 'Create table'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
