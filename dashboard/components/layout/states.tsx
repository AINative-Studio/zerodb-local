'use client'

import * as React from 'react'
import Link from 'next/link'
import { AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useProject } from '@/components/providers/project-provider'

export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
      <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
      <span>{label}…</span>
    </div>
  )
}

export function ErrorState({ error, what }: { error: unknown; what: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-destructive/40 bg-card p-5">
      <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
      <div className="flex flex-col gap-1">
        <strong className="font-semibold">Couldn’t load {what}</strong>
        <p className="text-sm text-muted-foreground">{error instanceof Error ? error.message : String(error)}</p>
      </div>
    </div>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  children?: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed bg-card px-6 py-14 text-center">
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-accent-foreground">
        <Icon className="h-6 w-6" />
      </span>
      <h2 className="font-display text-lg font-semibold">{title}</h2>
      {children && <p className="max-w-md text-muted-foreground">{children}</p>}
      {action}
    </div>
  )
}

/** Renders children only once a project exists; otherwise points to Projects. */
export function RequireProject({ children }: { children: (projectId: string) => React.ReactNode }) {
  const { projectId, isLoading, error } = useProject()
  if (isLoading) return <LoadingState label="Loading projects" />
  if (error) return <ErrorState error={error} what="projects" />
  if (!projectId) {
    return (
      <EmptyState icon={AlertCircle} title="Create a project first" action={
        <Button asChild>
          <Link href="/projects?new=1" className="text-primary-foreground no-underline">New project</Link>
        </Button>
      }>
        Vectors, tables, files and events all live inside a project.
      </EmptyState>
    )
  }
  return <>{children(projectId)}</>
}
