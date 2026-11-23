import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, act, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProjectsPage from '@/app/projects/page'
import VectorsPage from '@/app/vectors/page'
import TablesPage from '@/app/tables/page'
import EventsPage from '@/app/events/page'
import { apiClient } from '@/services/api-client'
import { renderPage, PROJECT } from '../helpers'

vi.mock('@/services/api-client', () => ({
  apiClient: {
    baseURL: 'http://localhost:8000',
    listProjects: vi.fn(),
    createProject: vi.fn(),
    deleteProject: vi.fn(),
    listVectors: vi.fn(),
    searchVectors: vi.fn(),
    upsertVector: vi.fn(),
    deleteVector: vi.fn(),
    listTables: vi.fn(),
    createTable: vi.fn(),
    queryTable: vi.fn(),
    listEvents: vi.fn(),
    createEvent: vi.fn(),
  },
}))

const click = async (el: Element) => {
  await act(async () => {
    await userEvent.click(el)
  })
}
const type = async (el: Element, text: string) => {
  await act(async () => {
    await userEvent.type(el, text)
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  vi.mocked(apiClient.listProjects).mockResolvedValue([PROJECT])
  vi.mocked(apiClient.listVectors).mockResolvedValue([])
  vi.mocked(apiClient.listTables).mockResolvedValue([])
  vi.mocked(apiClient.listEvents).mockResolvedValue([])
})

describe('Projects: New project', () => {
  it('creates a project from the dialog', async () => {
    vi.mocked(apiClient.createProject).mockResolvedValue({ ...PROJECT, id: 'prj-9', name: 'docs-search' })
    renderPage(<ProjectsPage />)
    await screen.findByText('support-bot')

    await click(screen.getByRole('button', { name: /new project/i }))
    const dialog = await screen.findByRole('dialog')
    await type(within(dialog).getByLabelText(/name/i), 'docs-search')
    await click(within(dialog).getByRole('button', { name: /create project/i }))

    await waitFor(() => expect(apiClient.createProject).toHaveBeenCalledWith({ name: 'docs-search' }))
  })

  it('requires a name', async () => {
    renderPage(<ProjectsPage />)
    await screen.findByText('support-bot')
    await click(screen.getByRole('button', { name: /new project/i }))
    const dialog = await screen.findByRole('dialog')
    await click(within(dialog).getByRole('button', { name: /create project/i }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/name/i)
    expect(apiClient.createProject).not.toHaveBeenCalled()
  })
})

describe('Vectors: Upsert (guided / advanced)', () => {
  it('upserts from the guided form with tags as metadata', async () => {
    vi.mocked(apiClient.upsertVector).mockResolvedValue({} as any)
    renderPage(<VectorsPage />)
    await click(await screen.findByRole('button', { name: /upsert vector/i }))
    const dialog = await screen.findByRole('dialog')

    await type(within(dialog).getByLabelText(/text to store/i), 'Refunds take 5 days')
    await type(within(dialog).getByLabelText('Tag 1 name'), 'topic')
    await type(within(dialog).getByLabelText('Tag 1 value'), 'billing')
    await click(within(dialog).getByRole('button', { name: /^upsert vector$/i }))

    await waitFor(() =>
      expect(apiClient.upsertVector).toHaveBeenCalledWith('prj-1', {
        document: 'Refunds take 5 days',
        namespace: 'default',
        metadata: { topic: 'billing' },
      })
    )
  })

  it('carries guided input into the Advanced JSON view', async () => {
    renderPage(<VectorsPage />)
    await click(await screen.findByRole('button', { name: /upsert vector/i }))
    const dialog = await screen.findByRole('dialog')
    await type(within(dialog).getByLabelText(/text to store/i), 'hello')
    await click(within(dialog).getByRole('radio', { name: /advanced json/i }))

    const json = within(dialog).getByLabelText(/request body/i) as HTMLTextAreaElement
    expect(JSON.parse(json.value)).toMatchObject({ document: 'hello', namespace: 'default' })
  })
})

describe('Tables: Create table', () => {
  it('builds the schema from the column builder', async () => {
    vi.mocked(apiClient.createTable).mockResolvedValue({} as any)
    renderPage(<TablesPage />)
    await click(await screen.findByRole('button', { name: /create table/i }))
    const dialog = await screen.findByRole('dialog')

    await type(within(dialog).getByLabelText(/table name/i), 'tickets')
    await type(within(dialog).getByLabelText('Column 1 name'), 'subject')
    await click(within(dialog).getByLabelText('Required'))
    await click(within(dialog).getByRole('button', { name: /^create table$/i }))

    await waitFor(() =>
      expect(apiClient.createTable).toHaveBeenCalledWith('prj-1', {
        table_name: 'tickets',
        schema: { fields: { subject: { type: 'string', required: true } } },
      })
    )
  })

  it('rejects an invalid table name before calling the API', async () => {
    renderPage(<TablesPage />)
    await click(await screen.findByRole('button', { name: /create table/i }))
    const dialog = await screen.findByRole('dialog')
    await type(within(dialog).getByLabelText(/table name/i), 'my table')
    await click(within(dialog).getByRole('button', { name: /^create table$/i }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/letters, numbers and underscores/i)
    expect(apiClient.createTable).not.toHaveBeenCalled()
  })
})

describe('Events', () => {
  it('groups events by family and filters the feed', async () => {
    vi.mocked(apiClient.listEvents).mockResolvedValue([
      { id: 'e1', event_type: 'vector.upserted', event_data: { id: 'faq/1' }, source: 'dashboard', correlation_id: null, timestamp: '2026-11-22T15:00:00Z' },
      { id: 'e2', event_type: 'table.created', event_data: { table: 't' }, source: 'dashboard', correlation_id: null, timestamp: '2026-11-22T15:01:00Z' },
    ])
    renderPage(<EventsPage />)

    const chip = await screen.findByRole('button', { name: /table\.\*/ })
    const feed = screen.getByRole('region', { name: /event feed/i })
    expect(within(feed).getByText('vector.upserted')).toBeInTheDocument()
    await click(chip)
    expect(within(feed).queryByText('vector.upserted')).not.toBeInTheDocument()
    expect(within(feed).getByText('table.created')).toBeInTheDocument()
  })

  it('publishes an event with parsed JSON data', async () => {
    vi.mocked(apiClient.createEvent).mockResolvedValue({} as any)
    renderPage(<EventsPage />)
    await click(await screen.findByRole('button', { name: /publish event/i }))
    const dialog = await screen.findByRole('dialog')
    await type(within(dialog).getByLabelText(/^type/i), 'order.shipped')
    const data = within(dialog).getByLabelText(/^data/i)
    await act(async () => {
      await userEvent.clear(data)
      await userEvent.click(data)
      await userEvent.paste('{"order": 7}')
    })
    await click(within(dialog).getByRole('button', { name: /^publish event$/i }))

    await waitFor(() =>
      expect(apiClient.createEvent).toHaveBeenCalledWith('prj-1', {
        event_type: 'order.shipped',
        event_data: { order: 7 },
        source: 'dashboard',
      })
    )
  })
})
