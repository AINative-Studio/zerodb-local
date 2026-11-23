'use client'

import * as React from 'react'
import Link from 'next/link'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderKanban, Plus, Search, Trash2 } from 'lucide-react'
import { apiClient } from '@/services/api-client'
import { useProject } from '@/components/providers/project-provider'
import { PageHeader, PageShell } from '@/components/layout/page-header'
import { EmptyState, ErrorState, LoadingState } from '@/components/layout/states'
import { NewProjectDialog } from '@/components/projects/new-project-dialog'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatNumber } from '@/lib/utils'
import { useNewParam } from '@/lib/use-new-param'
import type { Project } from '@/types'

export default function ProjectsPage() {
  const { projects, isLoading, error, setProjectId } = useProject()
  const [open, setOpen] = useNewParam()
  const [query, setQuery] = React.useState('')
  const [toDelete, setToDelete] = React.useState<Project | null>(null)
  const qc = useQueryClient()

  const remove = useMutation({
    mutationFn: (id: string) => apiClient.deleteProject(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      setToDelete(null)
    },
  })

  const shown = projects.filter((p) =>
    `${p.name} ${p.description ?? ''}`.toLowerCase().includes(query.trim().toLowerCase())
  )

  return (
    <PageShell>
      <PageHeader
        title="Projects"
        description="A project holds its own vectors, tables, files and events."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus aria-hidden="true" className="h-4 w-4" strokeWidth={2.5} /> New project
          </Button>
        }
      />

      {isLoading && <LoadingState label="Loading projects" />}
      {error && <ErrorState error={error} what="projects" />}

      {!isLoading && !error && projects.length === 0 && (
        <EmptyState
          icon={FolderKanban}
          title="No projects yet"
          action={
            <Button onClick={() => setOpen(true)}>
              <Plus aria-hidden="true" className="h-4 w-4" /> Create your first project
            </Button>
          }
        >
          Start here. Everything else in ZeroDB Local lives inside a project.
        </EmptyState>
      )}

      {projects.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="relative w-full max-w-[420px]">
              <label htmlFor="project-search" className="sr-only">Search projects</label>
              <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input id="project-search" placeholder="Search projects" value={query} onChange={(e) => setQuery(e.target.value)} className="pl-9" />
            </div>
            <span className="text-[13px] text-muted-foreground">
              {shown.length} of {projects.length} {projects.length === 1 ? 'project' : 'projects'}
            </span>
          </div>

          <section aria-label="Project list" className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4">
            {shown.map((p) => (
              <article key={p.id} className="flex flex-col gap-3.5 rounded-xl border bg-card p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <h2 className="truncate font-display text-[17px] font-semibold">{p.name}</h2>
                    <p className="text-muted-foreground">{p.description || 'No description'}</p>
                  </div>
                  <Button variant="ghost" size="icon-sm" aria-label={`Delete ${p.name}`} onClick={() => setToDelete(p)}>
                    <Trash2 aria-hidden="true" className="h-4 w-4" />
                  </Button>
                </div>
                <dl className="grid grid-cols-4 gap-2">
                  {(['vectors', 'tables', 'files', 'events'] as const).map((k) => (
                    <div key={k} className="flex flex-col">
                      <dt className="text-xs capitalize text-muted-foreground">{k}</dt>
                      <dd className="font-mono font-medium">{formatNumber(p.usage?.[k] ?? 0)}</dd>
                    </div>
                  ))}
                </dl>
                <div className="flex items-center justify-between gap-3 border-t pt-3">
                  <span className="truncate font-mono text-xs text-muted-foreground">{p.id}</span>
                  <Link href="/vectors" onClick={() => setProjectId(p.id)} className="text-[13px] font-semibold">
                    Open
                  </Link>
                </div>
              </article>
            ))}
          </section>
        </>
      )}

      <NewProjectDialog open={open} onOpenChange={setOpen} />
      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title={`Delete ${toDelete?.name ?? 'project'}?`}
        confirmLabel="Delete project"
        onConfirm={() => toDelete && remove.mutate(toDelete.id)}
        pending={remove.isPending}
        error={remove.error}
      >
        This removes the project and everything in it: vectors, tables, files and events. It can’t be undone.
      </ConfirmDialog>
    </PageShell>
  )
}
