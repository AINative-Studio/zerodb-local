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
  it('builds the store body, trimming ids and dropping blanks', () => {
    expect(buildStoreRequest(form)).toEqual({
      content: 'What does the Pro plan cost?',
      role: 'user',
      agent_id: 'support',
      metadata: { topic: 'pricing' },
    })
  })

  it('includes session_id when set and defaults the agent', () => {
    const r = buildStoreRequest({ ...form, agentId: '', sessionId: 's-1' })
    expect(r.agent_id).toBe('default')
    expect(r.session_id).toBe('s-1')
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
