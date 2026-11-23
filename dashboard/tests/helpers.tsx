import * as React from 'react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/components/providers/theme-provider'
import { ProjectProvider } from '@/components/providers/project-provider'

export const PROJECT = {
  id: 'prj-1',
  name: 'support-bot',
  description: 'Help-desk agent',
  user_id: 'u1',
  usage: { vectors: 2, tables: 1, events: 3, memory: 0, files: 1 },
  created_at: '2026-11-22T15:00:00Z',
  updated_at: '2026-11-22T15:00:00Z',
}

/** Renders a page inside the same providers the root layout uses. */
export function renderPage(ui: React.ReactElement<any>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <ProjectProvider>{ui}</ProjectProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
