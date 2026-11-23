import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createApiClient, type HttpLike } from '@/services/api-client'

// The client takes its HTTP instance as a parameter, so tests never open a
// socket (the old suite re-mocked axios.create after the singleton had
// already been built, and hit localhost:8000 for real).
function fakeHttp(data: unknown = {}): HttpLike & { [k: string]: any } {
  return {
    defaults: { baseURL: 'http://localhost:8000' },
    get: vi.fn().mockResolvedValue({ data }),
    post: vi.fn().mockResolvedValue({ data }),
    patch: vi.fn().mockResolvedValue({ data }),
    put: vi.fn().mockResolvedValue({ data }),
    delete: vi.fn().mockResolvedValue({ data }),
  }
}

const P = 'prj-1'
const base = `/v1/projects/${P}/database`

describe('ApiClient', () => {
  let http: ReturnType<typeof fakeHttp>

  beforeEach(() => {
    http = fakeHttp({ ok: true })
  })

  it('exposes the configured base URL for Settings', () => {
    expect(createApiClient(http).baseURL).toBe('http://localhost:8000')
  })

  it('gets health', async () => {
    http = fakeHttp({ status: 'healthy', summary: { healthy: 3, total: 3 }, services: {} })
    const res = await createApiClient(http).getHealth()
    expect(http.get).toHaveBeenCalledWith('/health')
    expect(res.summary.healthy).toBe(3)
  })

  it('creates a project', async () => {
    await createApiClient(http).createProject({ name: 'support-bot', description: 'x' })
    expect(http.post).toHaveBeenCalledWith('/v1/projects', { name: 'support-bot', description: 'x' })
  })

  it('upserts a vector with the API body shape', async () => {
    const body = { document: 'hi', namespace: 'faq', metadata: { a: 1 } }
    await createApiClient(http).upsertVector(P, body)
    expect(http.post).toHaveBeenCalledWith(`${base}/vectors/upsert`, body)
  })

  it('searches vectors by namespace, not collection', async () => {
    await createApiClient(http).searchVectors(P, { query: 'refund', namespace: 'faq', limit: 5 })
    expect(http.post).toHaveBeenCalledWith(`${base}/vectors/search`, {
      query: 'refund',
      namespace: 'faq',
      limit: 5,
      threshold: 0,
    })
  })

  it('lists vectors in a namespace', async () => {
    await createApiClient(http).listVectors(P, 'faq')
    expect(http.get).toHaveBeenCalledWith(`${base}/vectors`, { params: { namespace: 'faq', limit: 100 } })
  })

  it('creates a table with table_name and schema', async () => {
    const schema = { fields: { a: { type: 'string', required: true } } }
    await createApiClient(http).createTable(P, { table_name: 't', schema })
    expect(http.post).toHaveBeenCalledWith(`${base}/tables`, { table_name: 't', schema })
  })

  it('queries table rows with filter/limit/offset', async () => {
    await createApiClient(http).queryTable(P, 'tickets', { limit: 50 })
    expect(http.post).toHaveBeenCalledWith(`${base}/tables/tickets/query`, { filter: undefined, limit: 50, offset: 0 })
  })

  it('inserts rows', async () => {
    await createApiClient(http).insertRows(P, 'tickets', [{ a: 1 }])
    expect(http.post).toHaveBeenCalledWith(`${base}/tables/tickets/insert`, { rows: [{ a: 1 }] })
  })

  it('encodes table names in URLs', async () => {
    await createApiClient(http).deleteTable(P, 'a/b')
    expect(http.delete).toHaveBeenCalledWith(`${base}/tables/a%2Fb`)
  })

  it('uploads a file as base64 JSON', async () => {
    await createApiClient(http).uploadFile(P, {
      file_name: 'a.txt',
      file_content: 'aGk=',
      content_type: 'text/plain',
    })
    expect(http.post).toHaveBeenCalledWith(`${base}/files/upload`, {
      file_name: 'a.txt',
      file_content: 'aGk=',
      content_type: 'text/plain',
    })
  })

  it('downloads and deletes files', async () => {
    const c = createApiClient(http)
    await c.downloadFile(P, 'f1')
    expect(http.get).toHaveBeenCalledWith(`${base}/files/f1`, { params: { return_base64: true } })
    await c.deleteFile(P, 'f1')
    expect(http.delete).toHaveBeenCalledWith(`${base}/files/f1`)
  })

  it('lists events with the API param names', async () => {
    await createApiClient(http).listEvents(P, { eventType: 'vector.upserted', limit: 20 })
    expect(http.get).toHaveBeenCalledWith(`${base}/events`, {
      params: { event_type: 'vector.upserted', limit: 20 },
    })
  })

  it('publishes an event', async () => {
    const ev = { event_type: 'agent.reply_sent', event_data: { t: 1 }, source: 'dashboard' }
    await createApiClient(http).createEvent(P, ev)
    expect(http.post).toHaveBeenCalledWith(`${base}/events`, ev)
  })

  it('gets event stats', async () => {
    await createApiClient(http).getEventStats(P, 'day')
    expect(http.get).toHaveBeenCalledWith(`${base}/events/stats/summary`, { params: { time_range: 'day' } })
  })
})
