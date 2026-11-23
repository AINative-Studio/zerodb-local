import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as React from 'react'
import { render, screen, act, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useQuery } from '@tanstack/react-query'
import MemoryPage from '@/app/memory/page'
import SyncPage from '@/app/sync/page'
import { QueryProvider } from '@/components/providers/query-provider'
import { AuthNotice } from '@/components/layout/auth-notice'
import { apiClient, ApiRequestError } from '@/services/api-client'
import { renderPage, PROJECT } from '../helpers'

vi.mock('@/services/api-client', async (orig) => {
  const real = await orig<typeof import('@/services/api-client')>()
  return {
    ApiRequestError: real.ApiRequestError,
    apiClient: {
      baseURL: 'http://localhost:8000',
      listProjects: vi.fn(),
      listMemorySessions: vi.fn(),
      getMemoryContext: vi.fn(),
      storeMemory: vi.fn(),
      searchMemory: vi.fn(),
      deleteMemorySession: vi.fn(),
      getSyncStatus: vi.fn(),
      getCloudSyncStatus: vi.fn(),
      listSyncHistory: vi.fn(),
      planSync: vi.fn(),
      executeSync: vi.fn(),
      listConflicts: vi.fn(),
      resolveConflict: vi.fn(),
    },
  }
})

const click = async (el: Element) => {
  await act(async () => {
    await userEvent.click(el)
  })
}

const SESSION = { session_id: 'chat-42', agent_id: 'support', message_count: 2, last_message_at: '2026-11-22T15:00:00Z' }

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  vi.mocked(apiClient.listProjects).mockResolvedValue([PROJECT])
  vi.mocked(apiClient.listMemorySessions).mockResolvedValue([SESSION])
  vi.mocked(apiClient.getMemoryContext).mockResolvedValue({
    session_id: 'chat-42',
    message_count: 2,
    estimated_tokens: 40,
    truncated: false,
    messages: [
      { id: 'm1', session_id: 'chat-42', agent_id: 'support', role: 'user', content: 'What does Pro cost?', metadata: {} },
      { id: 'm2', session_id: 'chat-42', agent_id: 'support', role: 'assistant', content: '$49 a month.', metadata: {} },
    ],
  })
  vi.mocked(apiClient.getSyncStatus).mockResolvedValue({ project_id: 'prj-1', sync_in_progress: false, pending_changes_count: 12, entity_sync_states: {} })
  vi.mocked(apiClient.getCloudSyncStatus).mockResolvedValue({ is_authenticated: true, pending_changes: 12, total_bundles: 0, storage_used_bytes: 0, sync_enabled: true })
  vi.mocked(apiClient.listSyncHistory).mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0, has_more: false })
  vi.mocked(apiClient.listConflicts).mockResolvedValue([])
})

describe('Memory page', () => {
  it('shows sessions and the selected conversation', async () => {
    renderPage(<MemoryPage />)
    expect(await screen.findByText('What does Pro cost?')).toBeInTheDocument()
    expect(screen.getByText('$49 a month.')).toBeInTheDocument()
    expect(apiClient.getMemoryContext).toHaveBeenCalledWith('prj-1', 'chat-42')
  })

  it('adds a memory to the open session', async () => {
    vi.mocked(apiClient.storeMemory).mockResolvedValue({ id: 'm3', session_id: 'chat-42', agent_id: 'support', role: 'user', content: 'x', metadata: {} })
    renderPage(<MemoryPage />)
    await screen.findByText('What does Pro cost?')
    await click(screen.getByRole('button', { name: /add to session/i }))
    const dialog = await screen.findByRole('dialog')
    await act(async () => {
      await userEvent.type(within(dialog).getByLabelText(/what to remember/i), 'Prefers annual billing')
    })
    await click(within(dialog).getByRole('button', { name: /^add memory$/i }))
    await waitFor(() =>
      expect(apiClient.storeMemory).toHaveBeenCalledWith('prj-1', {
        content: 'Prefers annual billing',
        role: 'user',
        agent_id: 'support',
        session_id: 'chat-42',
        metadata: {},
      })
    )
  })

  it('searches memory by meaning', async () => {
    vi.mocked(apiClient.searchMemory).mockResolvedValue([
      { id: 'm2', session_id: 'chat-42', agent_id: 'support', role: 'assistant', content: '$49 a month.', metadata: {}, score: 0.83 },
    ])
    renderPage(<MemoryPage />)
    await screen.findByText('What does Pro cost?')
    await act(async () => {
      await userEvent.type(screen.getByLabelText(/search memory by meaning/i), 'price{Enter}')
    })
    expect(await screen.findByText('0.83')).toBeInTheDocument()
    expect(apiClient.searchMemory).toHaveBeenCalledWith('prj-1', { query: 'price', limit: 20 })
  })
})

describe('Sync page', () => {
  it('previews a plan, then runs it only when asked', async () => {
    vi.mocked(apiClient.planSync).mockResolvedValue({
      plan_id: 'plan-1',
      project_id: 'prj-1',
      direction: 'push',
      created_at: '2026-11-22T15:00:00Z',
      steps: [],
      entity_counts: { tables: 1, table_rows: 10, vectors: 2, memory: 0, events: 0, files: 0 },
      estimated_duration_seconds: 3,
      estimated_data_size_bytes: 2048,
      schema_changes: { has_changes: false, is_breaking: false, changes: [], migration_required: false },
      conflicts: { has_conflicts: false, conflict_count: 0, conflicts: [] },
      warnings: [],
      requires_approval: false,
      can_rollback: true,
    })
    vi.mocked(apiClient.executeSync).mockResolvedValue({
      sync_id: 's1', plan_id: 'plan-1', direction: 'push', status: 'completed', started_at: '2026-11-22T15:00:00Z',
      total_steps: 3, successful_steps: 3, failed_steps: 0, records_synced: 13, bytes_transferred: 2048, errors: [],
    })

    renderPage(<SyncPage />)
    expect(await screen.findByText('12')).toBeInTheDocument()

    await click(screen.getByRole('button', { name: /preview sync/i }))
    expect(apiClient.planSync).toHaveBeenCalledWith('prj-1', { direction: 'push', conflict_strategy: 'newest_wins' })
    expect(apiClient.executeSync).not.toHaveBeenCalled()

    await click(await screen.findByRole('button', { name: /run sync/i }))
    await waitFor(() => expect(apiClient.executeSync).toHaveBeenCalledWith('prj-1', 'plan-1'))
    expect(await screen.findByText(/synced 13 records/i)).toBeInTheDocument()
  })

  it('resolves a conflict by keeping one side', async () => {
    vi.mocked(apiClient.listConflicts).mockResolvedValue([
      { id: 'c1', project_id: 'prj-1', entity_type: 'vector', entity_id: 'faq/1', local_version: { a: 1 }, cloud_version: { a: 2 }, detected_at: '2026-11-22T15:00:00Z' },
    ])
    vi.mocked(apiClient.resolveConflict).mockResolvedValue({})
    renderPage(<SyncPage />)
    await click(await screen.findByRole('button', { name: /keep the cloud's version/i }))
    expect(apiClient.resolveConflict).toHaveBeenCalledWith('prj-1', 'c1', 'cloud_wins')
  })
})

describe('Sign-in notice', () => {
  function Failing() {
    useQuery({
      queryKey: ['x'],
      queryFn: () => Promise.reject(new ApiRequestError('needs key', 401)),
    })
    return null
  }

  it('appears after the API refuses a request with 401', async () => {
    render(
      <QueryProvider>
        <AuthNotice />
        <Failing />
      </QueryProvider>
    )
    expect(await screen.findByText(/this server needs an api key/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /add your key in settings/i })).toHaveAttribute('href', '/settings#connection')
  })
})
