import { describe, it, expect } from 'vitest'
import {
  buildUpsertRequest,
  parseUpsertJson,
  requestToForm,
  type VectorFormState,
} from '@/lib/vector-form'

const form: VectorFormState = {
  document: 'Refunds arrive within 5 business days.',
  namespace: 'faq',
  vectorId: '',
  tags: [
    { key: 'topic', value: 'billing' },
    { key: '', value: 'ignored' },
  ],
}

describe('buildUpsertRequest', () => {
  it('builds the API body and drops blank tags and empty IDs', () => {
    expect(buildUpsertRequest(form)).toEqual({
      document: 'Refunds arrive within 5 business days.',
      namespace: 'faq',
      metadata: { topic: 'billing' },
    })
  })

  it('includes vector_id when one is given', () => {
    expect(buildUpsertRequest({ ...form, vectorId: ' faq/refunds ' }).vector_id).toBe('faq/refunds')
  })

  it('defaults the namespace', () => {
    expect(buildUpsertRequest({ ...form, namespace: ' ' }).namespace).toBe('default')
  })
})

describe('parseUpsertJson', () => {
  it('accepts a valid body', () => {
    const r = parseUpsertJson(JSON.stringify({ document: 'hi', namespace: 'x', metadata: { a: 1 } }))
    expect(r).toEqual({ ok: true, value: { document: 'hi', namespace: 'x', metadata: { a: 1 } } })
  })

  it('requires a document', () => {
    const r = parseUpsertJson(JSON.stringify({ namespace: 'x' }))
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.error).toMatch(/document/)
  })

  it('reports bad JSON', () => {
    const r = parseUpsertJson('{')
    expect(r.ok).toBe(false)
  })

  it('rejects non-object metadata', () => {
    const r = parseUpsertJson(JSON.stringify({ document: 'a', metadata: [1] }))
    expect(r.ok).toBe(false)
  })
})

describe('requestToForm', () => {
  it('turns a body back into guided-form state', () => {
    const f = requestToForm({ document: 'd', namespace: 'n', vector_id: 'v', metadata: { a: 1, b: 'x' } })
    expect(f).toEqual({
      document: 'd',
      namespace: 'n',
      vectorId: 'v',
      tags: [
        { key: 'a', value: '1' },
        { key: 'b', value: 'x' },
      ],
    })
  })
})
