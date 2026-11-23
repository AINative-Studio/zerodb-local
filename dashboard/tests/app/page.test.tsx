import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import OverviewPage from '@/app/page'
import { apiClient } from '@/services/api-client'
import { renderPage, PROJECT } from '../helpers'

vi.mock('@/services/api-client', () => ({
  apiClient: {
    baseURL: 'http://localhost:8000',
    getHealth: vi.fn(),
    listProjects: vi.fn(),
    listEvents: vi.fn(),
  },
}))

describe('OverviewPage', () => {
  beforeEach(() => {
    vi.mocked(apiClient.listProjects).mockResolvedValue([PROJECT])
    vi.mocked(apiClient.listEvents).mockResolvedValue([])
  })

  it('renders lite-mode services without crashing', async () => {
    // Real /health shape in lite mode: no postgres/qdrant/minio/redpanda/
    // embeddings keys exist at all -- this used to throw
    // "Cannot read properties of undefined (reading 'status')".
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'healthy',
      backend: 'lite',
      services: { sqlite: { status: 'healthy' }, faiss: { status: 'healthy' }, filesystem: { status: 'healthy' } },
      summary: { healthy: 3, total: 3 },
    })

    renderPage(<OverviewPage />)

    await waitFor(() => expect(screen.getByText('SQLite')).toBeInTheDocument())
    expect(screen.getByText('FAISS')).toBeInTheDocument()
    expect(screen.getByText('Filesystem')).toBeInTheDocument()
    expect(screen.queryByText('PostgreSQL')).not.toBeInTheDocument()
    expect(screen.getAllByText('Lite mode').length).toBeGreaterThan(0)
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

    renderPage(<OverviewPage />)

    await waitFor(() => expect(screen.getByText('PostgreSQL')).toBeInTheDocument())
    expect(screen.getByText('Qdrant')).toBeInTheDocument()
    expect(screen.getByText('MinIO')).toBeInTheDocument()
    expect(screen.getByText('RedPanda')).toBeInTheDocument()
    expect(screen.getByText('Embeddings')).toBeInTheDocument()
  })

  it('totals resources across projects from their usage', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({ status: 'healthy', backend: 'lite', services: {}, summary: { healthy: 0, total: 0 } })
    vi.mocked(apiClient.listProjects).mockResolvedValue([
      PROJECT,
      { ...PROJECT, id: 'prj-2', name: 'docs', usage: { vectors: 5, tables: 0, events: 0, memory: 0, files: 0 } },
    ])

    renderPage(<OverviewPage />)

    const vectors = await screen.findByRole('link', { name: /vectors/i })
    await waitFor(() => expect(vectors).toHaveTextContent('7'))
  })

  it('shows the first-steps guide when there are no projects', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({ status: 'healthy', backend: 'lite', services: {}, summary: { healthy: 0, total: 0 } })
    vi.mocked(apiClient.listProjects).mockResolvedValue([])

    renderPage(<OverviewPage />)

    expect(await screen.findByText('Your first five minutes')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /new project/i })).toHaveAttribute('href', '/projects?new=1')
  })
})
