import { describe, it, expect } from 'vitest'
import { buildStoreRequest, parseStoreJson, storeToForm, type MemoryFormState } from '@/lib/memory-form'

const form: MemoryFormState = {
  role: 'user',
  content: 'What does the Pro plan cost?',
  agentId: ' support ',
  sessionId: '',
  tags: [{ key: 'topic', value: 'pricing' }, { key: '', value: 'x' }],
}

describe('buildStoreRequest', () => {
  it('builds the store body, trimming ids and dropping blank metadata', () => {
    const r = buildStoreRequest(form)
    expect(r).toEqual({
      content: 'What does the Pro plan cost?',
      role: 'user',
      agent_id: 'support',
      session_id: r.session_id,
      metadata: { topic: 'pricing' },
    })
  })

  it('includes session_id when set and defaults the agent', () => {
    const r = buildStoreRequest({ ...form, agentId: '', sessionId: 's-1' })
    expect(r.agent_id).toBe('default')
    expect(r.session_id).toBe('s-1')
  })

  it('generates a new session_id when the field is left blank, per its own "leave blank to start a new one" hint', () => {
    // Refs #77: api/services/memory_service.py's list_sessions() filters out
    // any memory whose session_id is null, so a request with no session_id
    // at all stored successfully but could never be found again through the
    // Memory page. Generating one client-side keeps the promise the field's
    // hint text makes and keeps every stored memory listed.
    const r1 = buildStoreRequest({ ...form, sessionId: '' })
    const r2 = buildStoreRequest({ ...form, sessionId: '' })
    expect(typeof r1.session_id).toBe('string')
    expect(r1.session_id!.length).toBeGreaterThan(0)
    // Each blank submission starts its own new session, not a shared one.
    expect(r1.session_id).not.toBe(r2.session_id)
  })
})

describe('parseStoreJson', () => {
  it('accepts a valid body', () => {
    const r = parseStoreJson('{"content":"hi","role":"assistant"}')
    expect(r).toEqual({ ok: true, value: { content: 'hi', role: 'assistant', agent_id: 'default', metadata: {} } })
  })

  it('requires content and a known role', () => {
    expect(parseStoreJson('{"role":"user"}').ok).toBe(false)
    expect(parseStoreJson('{"content":"a","role":"bot"}').ok).toBe(false)
  })

  it('reports bad JSON', () => {
    expect(parseStoreJson('{').ok).toBe(false)
  })
})

describe('storeToForm', () => {
  it('round-trips with buildStoreRequest', () => {
    const body = buildStoreRequest({ ...form, sessionId: 's-1' })
    expect(buildStoreRequest(storeToForm(body))).toEqual(body)
  })
})
