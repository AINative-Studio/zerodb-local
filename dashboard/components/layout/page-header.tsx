'use client'

import * as React from 'react'
import Link from 'next/link'
import { ThemeToggle } from './theme-toggle'
import { useProject } from '@/components/providers/project-provider'
import { Select } from '@/components/ui/form-controls'

export function PageHeader({
  title,
  description,
  actions,
  scoped,
}: {
  title: string
  description?: React.ReactNode
  actions?: React.ReactNode
  /** Project-scoped pages show the shared project picker above the title. */
  scoped?: boolean
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex min-w-0 flex-col gap-1">
        {scoped && <ProjectCrumb />}
        <h1 className="font-display text-[28px] font-semibold leading-tight tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground">{description}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        <ThemeToggle />
        {actions}
      </div>
    </header>
  )
}

function ProjectCrumb() {
  const { projects, projectId, setProjectId } = useProject()
  return (
    <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
      <Link href="/projects" className="text-muted-foreground no-underline hover:text-foreground">
        Projects
      </Link>
      <span aria-hidden="true">/</span>
      {projects.length > 0 ? (
        <>
          <label htmlFor="project-picker" className="sr-only">
            Project
          </label>
          <Select
            id="project-picker"
            value={projectId ?? ''}
            onChange={(e) => setProjectId(e.target.value)}
            className="h-8 w-auto border-transparent bg-transparent px-1 font-mono text-[13px] text-foreground hover:border-border"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
        </>
      ) : (
        <span>none yet</span>
      )}
    </div>
  )
}

export function PageShell({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-6 px-4 pb-12 pt-7 sm:px-10">{children}</div>
}
