import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardPage from '@/app/page'
import { apiClient } from '@/services/api-client'

vi.mock('@/services/api-client', () => ({
  apiClient: { getHealth: vi.fn() },
}))

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('DashboardPage', () => {
  it('renders lite-mode services without crashing', async () => {
    // Real /health shape in lite mode: no postgres/qdrant/minio/redpanda/
    // embeddings keys exist at all -- this used to throw
    // "Cannot read properties of undefined (reading 'status')".
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'healthy',
      backend: 'lite',
      services: {
        sqlite: { status: 'healthy' },
        faiss: { status: 'healthy' },
        filesystem: { status: 'healthy' },
      },
      summary: { healthy: 3, total: 3 },
    })

    renderWithQueryClient(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('SQLite')).toBeInTheDocument()
    })
    expect(screen.getByText('FAISS')).toBeInTheDocument()
    expect(screen.getByText('Filesystem')).toBeInTheDocument()
    expect(screen.queryByText('PostgreSQL')).not.toBeInTheDocument()
  })

  it('renders full-mode services without crashing', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'healthy',
      backend: 'full',
      services: {
        postgres: { status: 'healthy' },
        qdrant: { status: 'healthy' },
        minio: { status: 'healthy' },
        redpanda: { status: 'healthy' },
        embeddings: { status: 'healthy' },
      },
      summary: { healthy: 5, total: 5 },
    })

    renderWithQueryClient(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
    })
    expect(screen.getByText('Qdrant')).toBeInTheDocument()
    expect(screen.getByText('MinIO')).toBeInTheDocument()
    expect(screen.getByText('RedPanda')).toBeInTheDocument()
    expect(screen.getByText('Embeddings')).toBeInTheDocument()
  })
})
