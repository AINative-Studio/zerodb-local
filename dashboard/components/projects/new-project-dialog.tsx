'use client'

import * as React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronDown } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { useProject } from '@/components/providers/project-provider'
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
import { cn } from '@/lib/utils'

export function NewProjectDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const qc = useQueryClient()
  const { setProjectId } = useProject()
  const [name, setName] = React.useState('')
  const [description, setDescription] = React.useState('')
  const [showRequest, setShowRequest] = React.useState(false)
  const [touched, setTouched] = React.useState(false)

  const nameError = touched && !name.trim() ? 'Give the project a name.' : null
  const body = { name: name.trim(), ...(description.trim() ? { description: description.trim() } : {}) }

  const create = useMutation({
    mutationFn: () => apiClient.createProject(body),
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      setProjectId(project.id)
      setName('')
      setDescription('')
      setTouched(false)
      onOpenChange(false)
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (!name.trim()) return
    create.mutate()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>You’ll land in it straight away and can add data from there.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Field label="Name" htmlFor="np-name" required error={nameError} hint="Something short you'll recognise, like support-bot.">
              <Input
                id="np-name"
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                onBlur={() => setTouched(true)}
                aria-invalid={!!nameError}
                aria-describedby={nameError ? 'np-name-error' : 'np-name-hint'}
                className="font-mono"
              />
            </Field>
            <Field label="Description" htmlFor="np-desc" optional>
              <Textarea id="np-desc" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            <div className="flex flex-col gap-2.5">
              <button
                type="button"
                onClick={() => setShowRequest((s) => !s)}
                aria-expanded={showRequest}
                className="inline-flex min-h-9 items-center gap-1.5 self-start text-sm font-semibold text-link"
              >
                <ChevronDown aria-hidden="true" className={cn('h-4 w-4 transition-transform', showRequest && 'rotate-180')} />
                {showRequest ? 'Hide' : 'Show'} API request
              </button>
              {showRequest && (
                <pre className="overflow-x-auto rounded-lg bg-terminal px-4 py-3.5 font-mono text-[12.5px] leading-relaxed text-terminal-foreground">
                  {`POST /v1/projects\n${JSON.stringify(body, null, 2)}`}
                </pre>
              )}
            </div>
            {create.error && (
              <p role="alert" className="text-sm font-medium text-destructive">
                {(create.error as Error).message}
              </p>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? 'Creating…' : 'Create project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
