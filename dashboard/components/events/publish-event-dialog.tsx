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
import { Field, Textarea } from '@/components/ui/form-controls'
import { parseEventData } from '@/lib/events'

export function PublishEventDialog({
  projectId,
  open,
  onOpenChange,
}: {
  projectId: string
  open: boolean
  onOpenChange: (o: boolean) => void
}) {
  const qc = useQueryClient()
  const [type, setType] = React.useState('')
  const [source, setSource] = React.useState('dashboard')
  const [data, setData] = React.useState('{\n  \n}')
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (open) {
      // Resetting a controlled dialog's form state when it opens, keyed
      // on the `open` prop itself: a documented, intended use of this
      // pattern
      // (https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes),
      // not the derived-state anti-pattern the rule targets.
      /* eslint-disable react-hooks/set-state-in-effect */
      setType('')
      setSource('dashboard')
      setData('{\n  \n}')
      setError(null)
      /* eslint-enable react-hooks/set-state-in-effect */
    }
  }, [open])

  const publish = useMutation({
    mutationFn: (event_data: Record<string, unknown>) =>
      apiClient.createEvent(projectId, {
        event_type: type.trim(),
        event_data,
        ...(source.trim() ? { source: source.trim() } : {}),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['events', projectId] })
      qc.invalidateQueries({ queryKey: ['projects'] })
      onOpenChange(false)
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!type.trim()) return setError('Give the event a type, like order.shipped.')
    const parsed = parseEventData(data)
    if (!parsed.ok) return setError(parsed.error)
    setError(null)
    publish.mutate(parsed.value)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogHeader>
            <DialogTitle>Publish event</DialogTitle>
            <DialogDescription>Record something that happened. Useful for testing subscribers or seeding a feed.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <div className="grid gap-3.5 sm:grid-cols-2">
              <Field label="Type" htmlFor="ev-type" required hint="Use family.action, e.g. order.shipped.">
                <Input id="ev-type" autoFocus value={type} onChange={(e) => setType(e.target.value)} className="font-mono" aria-describedby="ev-type-hint" />
              </Field>
              <Field label="Source" htmlFor="ev-src" optional>
                <Input id="ev-src" value={source} onChange={(e) => setSource(e.target.value)} className="font-mono" />
              </Field>
            </div>
            <Field label="Data" htmlFor="ev-data" hint="A JSON object. Leave it empty if there's nothing to add.">
              <Textarea id="ev-data" code rows={7} value={data} onChange={(e) => setData(e.target.value)} aria-describedby="ev-data-hint" />
            </Field>
            {(error || publish.error) && (
              <p role="alert" className="text-sm font-medium text-destructive">{error ?? (publish.error as Error).message}</p>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={publish.isPending}>{publish.isPending ? 'Publishing…' : 'Publish event'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
