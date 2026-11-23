'use client'

import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import type { Project } from '@/types'

const STORAGE_KEY = 'zerolocal-project'

interface ProjectContextValue {
  projects: Project[]
  project: Project | null
  projectId: string | null
  setProjectId: (id: string) => void
  isLoading: boolean
  error: Error | null
}

const ProjectContext = React.createContext<ProjectContextValue | null>(null)

/**
 * The selected project is shared by every project-scoped page, so moving
 * from Vectors to Tables keeps you in the same project. Remembered per
 * browser as a convenience; falls back to the first project.
 */
export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.listProjects(),
  })
  const projects = data ?? []

  // Read after mount so the server and first client render agree.
  const [chosen, setChosen] = React.useState<string | null>(null)
  React.useEffect(() => {
    try {
      // One-shot localStorage read on mount for hydration safety, empty
      // deps, no cascading-render risk.
      /* eslint-disable-next-line react-hooks/set-state-in-effect */
      setChosen(window.localStorage.getItem(STORAGE_KEY))
    } catch {
      // storage blocked: fall back to the first project
    }
  }, [])

  const project = projects.find((p) => p.id === chosen) ?? projects[0] ?? null

  const setProjectId = React.useCallback((id: string) => {
    setChosen(id)
    try {
      window.localStorage.setItem(STORAGE_KEY, id)
    } catch {
      // storage blocked: selection still works for this visit
    }
  }, [])

  const value: ProjectContextValue = {
    projects,
    project,
    projectId: project?.id ?? null,
    setProjectId,
    isLoading,
    error: (error as Error) ?? null,
  }

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
}

export function useProject(): ProjectContextValue {
  const ctx = React.useContext(ProjectContext)
  if (!ctx) throw new Error('useProject must be used inside <ProjectProvider>')
  return ctx
}
