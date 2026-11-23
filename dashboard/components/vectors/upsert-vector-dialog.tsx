'use client'

import * as React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Braces, Check, Plus, X } from 'lucide-react'
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
import { Field, Textarea } from '@/components/ui/form-controls'
import { Segmented } from '@/components/ui/segmented'
import {
  buildUpsertRequest,
  EMPTY_VECTOR_FORM,
  parseUpsertJson,
  requestToForm,
  type VectorFormState,
} from '@/lib/vector-form'
import { getDefaultNamespace, getFormMode, type FormMode } from '@/lib/preferences'

/**
 * Guided by default (just the text -- the API embeds it server-side, free),
 * with an Advanced JSON view of the exact request body. Switching views
 * carries edits across in both directions.
 */
export function UpsertVectorDialog({
  projectId,
  projectName,
  open,
  onOpenChange,
}: {
  projectId: string
  projectName?: string
  open: boolean
  onOpenChange: (o: boolean) => void
}) {
  const qc = useQueryClient()
  const [mode, setMode] = React.useState<FormMode>('guided')
  const [form, setForm] = React.useState<VectorFormState>(EMPTY_VECTOR_FORM)
  const [json, setJson] = React.useState('')
  const [jsonError, setJsonError] = React.useState<string | null>(null)
  const [touched, setTouched] = React.useState(false)

  React.useEffect(() => {
    if (!open) return
    const start = { ...EMPTY_VECTOR_FORM, namespace: getDefaultNamespace() }
    setForm(start)
    setMode(getFormMode())
    setJson(JSON.stringify(buildUpsertRequest(start), null, 2))
    setJsonError(null)
    setTouched(false)
  }, [open])

  const switchMode = (next: FormMode) => {
    if (next === mode) return
    if (next === 'advanced') {
      setJson(JSON.stringify(buildUpsertRequest(form), null, 2))
      setJsonError(null)
    } else {
      const parsed = parseUpsertJson(json)
      if (!parsed.ok) {
        setJsonError(`${parsed.error} Fix it to switch back to Guided.`)
        return
      }
      setForm(requestToForm(parsed.value))
    }
    setMode(next)
  }

  const upsert = useMutation({
    mutationFn: (body: ReturnType<typeof buildUpsertRequest>) => apiClient.upsertVector(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vectors', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
      onOpenChange(false)
    },
  })

  // The very first vector upsert in a lite-mode session lazily downloads
  // the embedding model server-side (BAAI/bge-small-en-v1.5), which can
  // take well over the usual sub-second response time -- surface that
  // instead of leaving "Embedding…" looking stuck. Every later call in the
  // same server process is fast.
  const [isSlow, setIsSlow] = React.useState(false)
  React.useEffect(() => {
    if (!upsert.isPending) {
      setIsSlow(false)
      return
    }
    const t = setTimeout(() => setIsSlow(true), 4000)
    return () => clearTimeout(t)
  }, [upsert.isPending])

  const docError = touched && mode === 'guided' && !form.document.trim() ? 'Add the text you want to store.' : null

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (mode === 'guided') {
      if (!form.document.trim()) return
      upsert.mutate(buildUpsertRequest(form))
    } else {
      const parsed = parseUpsertJson(json)
      if (!parsed.ok) return setJsonError(parsed.error)
      upsert.mutate(parsed.value)
    }
  }

  const setTag = (i: number, patch: Partial<{ key: string; value: string }>) =>
    setForm((f) => ({ ...f, tags: f.tags.map((t, j) => (j === i ? { ...t, ...patch } : t)) }))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogHeader>
            <DialogTitle>Upsert vector</DialogTitle>
            <DialogDescription>
              Into <span className="font-mono text-foreground">{projectName ?? 'this project'}</span>. Using an existing ID
              replaces that vector.
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
                <Field
                  label="Text to store"
                  htmlFor="uv-text"
                  required
                  error={docError}
                  hint={<span className="inline-flex items-center gap-1.5"><Check aria-hidden="true" className="h-3.5 w-3.5" />We’ll turn this into a vector for you. No API key, no cost.</span>}
                >
                  <Textarea
                    id="uv-text"
                    rows={4}
                    autoFocus
                    value={form.document}
                    onChange={(e) => setForm({ ...form, document: e.target.value })}
                    aria-invalid={!!docError}
                    aria-describedby={docError ? 'uv-text-error' : 'uv-text-hint'}
                  />
                </Field>
                <div className="grid gap-3.5 sm:grid-cols-2">
                  <Field label="Namespace" htmlFor="uv-ns" hint="Groups related vectors, like faq or tickets.">
                    <Input id="uv-ns" value={form.namespace} onChange={(e) => setForm({ ...form, namespace: e.target.value })} className="font-mono" aria-describedby="uv-ns-hint" />
                  </Field>
                  <Field label="ID" htmlFor="uv-id" optional hint="Leave blank to generate one.">
                    <Input id="uv-id" value={form.vectorId} onChange={(e) => setForm({ ...form, vectorId: e.target.value })} className="font-mono" aria-describedby="uv-id-hint" />
                  </Field>
                </div>
                <fieldset className="flex flex-col gap-2">
                  <legend className="mb-2 text-sm font-semibold">
                    Tags <span className="font-normal text-muted-foreground">(optional, helps filter later)</span>
                  </legend>
                  {form.tags.map((t, i) => (
                    <div key={i} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_36px] items-center gap-2">
                      <Input aria-label={`Tag ${i + 1} name`} placeholder="e.g. topic" value={t.key} onChange={(e) => setTag(i, { key: e.target.value })} className="h-10 font-mono text-[13px]" />
                      <Input aria-label={`Tag ${i + 1} value`} placeholder="e.g. billing" value={t.value} onChange={(e) => setTag(i, { value: e.target.value })} className="h-10 font-mono text-[13px]" />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Remove tag ${i + 1}`}
                        onClick={() => setForm((f) => ({ ...f, tags: f.tags.length > 1 ? f.tags.filter((_, j) => j !== i) : [{ key: '', value: '' }] }))}
                      >
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
              <Field
                label="Request body"
                htmlFor="uv-json"
                error={jsonError}
                hint={<span className="font-mono">POST /v1/projects/{'{id}'}/database/vectors/upsert</span>}
              >
                <Textarea
                  id="uv-json"
                  code
                  rows={12}
                  value={json}
                  onChange={(e) => {
                    setJson(e.target.value)
                    setJsonError(null)
                  }}
                  aria-invalid={!!jsonError}
                  aria-describedby={jsonError ? 'uv-json-error' : 'uv-json-hint'}
                />
              </Field>
            )}

            {isSlow && (
              <p className="text-sm text-muted-foreground">
                First time embedding text downloads a small model — this can take a minute. It only happens once.
              </p>
            )}

            {upsert.error && (
              <p role="alert" className="text-sm font-medium text-destructive">{(upsert.error as Error).message}</p>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={upsert.isPending}>{upsert.isPending ? 'Embedding…' : 'Upsert vector'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
