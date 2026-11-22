import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LogsPage from '@/app/logs/page'

// LogsPage calls useQuery, which requires a QueryClientProvider ancestor.
function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('LogsPage', () => {
  it('renders the page heading', () => {
    renderWithQueryClient(<LogsPage />)
    expect(screen.getByText('System Logs')).toBeInTheDocument()
  })

  it('renders the description text', () => {
    renderWithQueryClient(<LogsPage />)
    expect(
      screen.getByText('Real-time log streaming from all ZeroDB services')
    ).toBeInTheDocument()
  })

  it('renders the filters and controls section', () => {
    renderWithQueryClient(<LogsPage />)
    expect(screen.getByText('Filters & Controls')).toBeInTheDocument()
  })

  it('renders the log stream section', () => {
    renderWithQueryClient(<LogsPage />)
    expect(screen.getByText('Log Stream')).toBeInTheDocument()
  })
})
