import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LogsPage from '@/app/logs/page'
import { apiClient } from '@/services/api-client'
import { renderPage } from '../../helpers'

vi.mock('@/services/api-client', () => ({
  apiClient: {
    listProjects: vi.fn().mockResolvedValue([]),
    getAvailableServices: vi.fn().mockResolvedValue(['api']),
    getLogs: vi.fn(),
  },
}))

describe('LogsPage', () => {
  beforeEach(() => {
    vi.mocked(apiClient.getLogs).mockResolvedValue({
      logs: [
        { timestamp: '2026-11-22T15:00:00Z', level: 'INFO', service: 'api', message: 'GET /health 200' },
        { timestamp: '2026-11-22T15:00:01Z', level: 'ERROR', service: 'api', message: 'POST /events 422' },
      ],
      total_count: 2,
      time_range_start: '2026-11-22T14:00:00Z',
      time_range_end: '2026-11-22T15:00:00Z',
    })
  })

  it('renders the heading and the stream', async () => {
    renderPage(<LogsPage />)
    expect(screen.getByRole('heading', { name: 'Logs' })).toBeInTheDocument()
    expect(await screen.findByText('GET /health 200')).toBeInTheDocument()
  })

  it('replaces the stat cards with level toggles that filter the stream', async () => {
    renderPage(<LogsPage />)
    await screen.findByText('POST /events 422')
    const info = screen.getByRole('button', { name: /^INFO/ })
    await act(async () => {
      await userEvent.click(info)
    })
    expect(info).toHaveAttribute('aria-pressed', 'false')
    expect(screen.queryByText('GET /health 200')).not.toBeInTheDocument()
    expect(screen.getByText('POST /events 422')).toBeInTheDocument()
  })
})
