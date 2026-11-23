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
  buildStoreRequest,
  parseStoreJson,
  ROLES,
  storeToForm,
  type MemoryFormState,
  type StoreMemoryRequest,
} from '@/lib/memory-form'
import { getFormMode, type FormMode } from '@/lib/preferences'
import type { MemoryRole } from '@/types'

const ROLE_LABELS: Record<MemoryRole, string> = {
  user: 'User (what a person said)',
  assistant: 'Assistant (what the agent said)',
  system: 'System (instructions or facts)',
}

export function AddMemoryDialog({
  projectId,
  open,
  onOpenChange,
  defaults,
  onStored,
}: {
  projectId: string
  open: boolean
  onOpenChange: (o: boolean) => void
  /** Pre-fills agent and session when adding to the conversation on screen. */
  defaults?: { agentId?: string; sessionId?: string }
  onStored?: (sessionId: string | null) => void
}) {
  const qc = useQueryClient()
  const [mode, setMode] = React.useState<FormMode>('guided')
  const [form, setForm] = React.useState<MemoryFormState>(blank(defaults))
  const [json, setJson] = React.useState('')
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!open) return
    const start = blank(defaults)
    setForm(start)
    setMode(getFormMode())
    setJson(JSON.stringify(buildStoreRequest(start), null, 2))
    setError(null)
    // defaults are read once per open
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const switchMode = (next: FormMode) => {
    if (next === mode) return
    if (next === 'advanced') {
      setJson(JSON.stringify(buildStoreRequest(form), null, 2))
    } else {
      const parsed = parseStoreJson(json)
      if (!parsed.ok) return setError(`${parsed.error} Fix it to switch back to Guided.`)
      setForm(storeToForm(parsed.value))
    }
    setError(null)
    setMode(next)
  }

  const store = useMutation({
    mutationFn: (body: StoreMemoryRequest) => apiClient.storeMemory(projectId, body),
    onSuccess: (rec) => {
      qc.invalidateQueries({ queryKey: ['memory', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
      onStored?.(rec?.session_id ?? null)
      onOpenChange(false)
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (mode === 'guided') {
      if (!form.content.trim()) return setError('Add what the agent should remember.')
      setError(null)
      store.mutate(buildStoreRequest(form))
    } else {
      const parsed = parseStoreJson(json)
      if (!parsed.ok) return setError(parsed.error)
      setError(null)
      store.mutate(parsed.value)
    }
  }

  const setTag = (i: number, patch: Partial<{ key: string; value: string }>) =>
    setForm((f) => ({ ...f, tags: f.tags.map((t, j) => (j === i ? { ...t, ...patch } : t)) }))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogHeader>
            <DialogTitle>Add memory</DialogTitle>
            <DialogDescription>
              Store a message or fact your agent can recall later. It’s embedded for search automatically.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Segmented
              label="Input mode"
              value={mode}
              onChange={switchMode}
              options={[
                { value: 'guided', label: 'Guided' },
                { value: 'advanced', label: <><Braces aria-hidden="true" className="h-[15px] w-[15px]" /> Advanced JSON</> },
              ]}
            />
            {mode === 'guided' ? (
              <>
                <Field label="What to remember" htmlFor="mem-content" required>
                  <Textarea id="mem-content" rows={4} autoFocus value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
                </Field>
                <Field label="Who said it" htmlFor="mem-role">
                  <Select id="mem-role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as MemoryRole })}>
                    {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                  </Select>
                </Field>
                <div className="grid gap-3.5 sm:grid-cols-2">
                  <Field label="Agent" htmlFor="mem-agent" hint="Which agent this memory belongs to.">
                    <Input id="mem-agent" value={form.agentId} onChange={(e) => setForm({ ...form, agentId: e.target.value })} className="font-mono" aria-describedby="mem-agent-hint" />
                  </Field>
                  <Field label="Session" htmlFor="mem-session" optional hint="Leave blank to start a new one.">
                    <Input id="mem-session" value={form.sessionId} onChange={(e) => setForm({ ...form, sessionId: e.target.value })} className="font-mono" aria-describedby="mem-session-hint" />
                  </Field>
                </div>
                <fieldset className="flex flex-col gap-2">
                  <legend className="mb-2 text-sm font-semibold">Tags <span className="font-normal text-muted-foreground">(optional)</span></legend>
                  {form.tags.map((t, i) => (
                    <div key={i} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_36px] items-center gap-2">
                      <Input aria-label={`Tag ${i + 1} name`} placeholder="e.g. topic" value={t.key} onChange={(e) => setTag(i, { key: e.target.value })} className="h-10 font-mono text-[13px]" />
                      <Input aria-label={`Tag ${i + 1} value`} placeholder="e.g. pricing" value={t.value} onChange={(e) => setTag(i, { value: e.target.value })} className="h-10 font-mono text-[13px]" />
                      <Button type="button" variant="ghost" size="icon-sm" aria-label={`Remove tag ${i + 1}`} onClick={() => setForm((f) => ({ ...f, tags: f.tags.length > 1 ? f.tags.filter((_, j) => j !== i) : [{ key: '', value: '' }] }))}>
                        <X aria-hidden="true" className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <Button type="button" variant="link" className="self-start" onClick={() => setForm((f) => ({ ...f, tags: [...f.tags, { key: '', value: '' }] }))}>
                    <Plus aria-hidden="true" className="h-[15px] w-[15px]" strokeWidth={2.5} /> Add tag
                  </Button>
                </fieldset>
              </>
            ) : (
              <Field label="Request body" htmlFor="mem-json" hint={<span className="font-mono">POST /v1/projects/{'{id}'}/database/memory/store</span>}>
                <Textarea id="mem-json" code rows={12} value={json} onChange={(e) => { setJson(e.target.value); setError(null) }} aria-describedby="mem-json-hint" />
              </Field>
            )}
            {(error || store.error) && (
              <p role="alert" className="text-sm font-medium text-destructive">{error ?? (store.error as Error).message}</p>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={store.isPending}>{store.isPending ? 'Saving…' : 'Add memory'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function blank(defaults?: { agentId?: string; sessionId?: string }): MemoryFormState {
  return {
    role: 'user',
    content: '',
    agentId: defaults?.agentId ?? 'default',
    sessionId: defaults?.sessionId ?? '',
    tags: [{ key: '', value: '' }],
  }
}
