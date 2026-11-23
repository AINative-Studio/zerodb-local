import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createApiClient, withApiKey, ApiRequestError, toApiRequestError, type HttpLike } from '@/services/api-client'

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

  it('upserts a vector with the API body shape and a longer timeout for cold embedding loads', async () => {
    const body = { document: 'hi', namespace: 'faq', metadata: { a: 1 } }
    await createApiClient(http).upsertVector(P, body)
    expect(http.post).toHaveBeenCalledWith(`${base}/vectors/upsert`, body, { timeout: 90000 })
  })

  it('searches vectors by namespace, not collection, with a longer timeout for cold embedding loads', async () => {
    await createApiClient(http).searchVectors(P, { query: 'refund', namespace: 'faq', limit: 5 })
    expect(http.post).toHaveBeenCalledWith(
      `${base}/vectors/search`,
      {
        query: 'refund',
        namespace: 'faq',
        limit: 5,
        threshold: 0,
      },
      { timeout: 90000 }
    )
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

  // Memory -- routes from api/routers/memory.py
  it('lists memory sessions', async () => {
    await createApiClient(http).listMemorySessions(P, { agentId: 'support' })
    expect(http.get).toHaveBeenCalledWith(`${base}/memory/sessions`, { params: { agent_id: 'support', limit: 100 } })
  })

  it('loads a session context window', async () => {
    await createApiClient(http).getMemoryContext(P, 's/1')
    expect(http.get).toHaveBeenCalledWith(`${base}/memory/context/s%2F1`, { params: { limit: 200 } })
  })

  it('stores a memory', async () => {
    const body = { content: 'hi', role: 'user' as const, agent_id: 'support', session_id: 's1', metadata: {} }
    await createApiClient(http).storeMemory(P, body)
    expect(http.post).toHaveBeenCalledWith(`${base}/memory/store`, body)
  })

  it('searches memory with threshold 0 by default', async () => {
    await createApiClient(http).searchMemory(P, { query: 'pricing', sessionId: 's1' })
    expect(http.post).toHaveBeenCalledWith(`${base}/memory/search`, {
      query: 'pricing',
      limit: 20,
      threshold: 0,
      session_id: 's1',
    })
  })

  it('deletes a session', async () => {
    await createApiClient(http).deleteMemorySession(P, 's1')
    expect(http.delete).toHaveBeenCalledWith(`${base}/memory/sessions/s1`)
  })

  // Sync -- routes from api/routers/sync_orchestrator.py, conflict_resolution.py, sync_history.py
  it('gets sync status', async () => {
    await createApiClient(http).getSyncStatus(P)
    expect(http.get).toHaveBeenCalledWith(`/v1/projects/${P}/sync/status`)
  })

  it('plans a sync', async () => {
    await createApiClient(http).planSync(P, { direction: 'push', conflict_strategy: 'newest_wins' })
    expect(http.post).toHaveBeenCalledWith(`/v1/projects/${P}/sync/plan`, {
      direction: 'push',
      conflict_strategy: 'newest_wins',
    })
  })

  it('executes an approved plan', async () => {
    await createApiClient(http).executeSync(P, 'plan-1')
    expect(http.post).toHaveBeenCalledWith(`/v1/projects/${P}/sync/execute`, { plan_id: 'plan-1', approved: true })
  })

  it('lists and resolves conflicts', async () => {
    const c = createApiClient(http)
    await c.listConflicts(P)
    expect(http.get).toHaveBeenCalledWith(`/v1/projects/${P}/sync/conflicts/`, { params: { limit: 100 } })
    await c.resolveConflict(P, 'c1', 'local_wins')
    expect(http.post).toHaveBeenCalledWith(`/v1/projects/${P}/sync/conflicts/c1/resolve`, {
      conflict_id: 'c1',
      strategy: 'local_wins',
    })
  })

  it('lists sync history', async () => {
    await createApiClient(http).listSyncHistory(P)
    expect(http.get).toHaveBeenCalledWith(`/v1/projects/${P}/sync/history`, { params: { limit: 20, offset: 0 } })
  })
})

describe('withApiKey', () => {
  it('adds a bearer header when a key is set', () => {
    expect(withApiKey({ headers: {} }, 'sk_123').headers).toEqual({ Authorization: 'Bearer sk_123' })
  })

  it('leaves the request alone without a key', () => {
    expect(withApiKey({ headers: { a: '1' } }, null).headers).toEqual({ a: '1' })
  })

  it('never overrides an explicit Authorization header', () => {
    expect(withApiKey({ headers: { Authorization: 'Bearer other' } }, 'sk_123').headers).toEqual({ Authorization: 'Bearer other' })
  })
})

describe('ApiRequestError', () => {
  it('keeps the HTTP status so the UI can spot 401s', () => {
    const e = new ApiRequestError('nope', 401)
    expect(e).toBeInstanceOf(Error)
    expect(e.status).toBe(401)
    expect(e.isAuthError).toBe(true)
  })

  it('lets an explicit authOverride win over the status-based default', () => {
    // Refs #80: a 401/403 that is not evidence the local API needs a key
    // (e.g. a cloud-status check) needs to say so explicitly.
    expect(new ApiRequestError('nope', 401, false).isAuthError).toBe(false)
    expect(new ApiRequestError('nope', 200, true).isAuthError).toBe(true)
  })
})

describe('toApiRequestError', () => {
  it('treats a 401/403 as needing a local API key by default', () => {
    const e = toApiRequestError({ status: 401 })
    expect(e.isAuthError).toBe(true)
    expect(e.message).toContain('needs an API key')
  })

  it('does NOT treat a 401 from cloud/status as needing a local API key', () => {
    // Refs #80: GET .../cloud/status 401s by design whenever the project
    // isn't connected to ZeroDB Cloud -- a normal state, not evidence the
    // local server itself requires ZERODB_LOCAL_API_KEY. Before this fix,
    // any project with no cloud connection showed a false "This server
    // needs an API key" banner on every page, even with no local key set.
    const e = toApiRequestError({ status: 401, url: '/v1/projects/p1/cloud/status' })
    expect(e.isAuthError).toBe(false)
    expect(e.status).toBe(401)
  })

  it('still treats a 401 from a non-cloud-status endpoint as needing a key', () => {
    const e = toApiRequestError({ status: 401, url: '/v1/projects/p1/database/vectors' })
    expect(e.isAuthError).toBe(true)
  })

  it('passes through a plain detail message for non-auth errors', () => {
    const e = toApiRequestError({ status: 500, detail: 'boom' })
    expect(e.isAuthError).toBe(false)
    expect(e.message).toBe('boom')
  })
})
