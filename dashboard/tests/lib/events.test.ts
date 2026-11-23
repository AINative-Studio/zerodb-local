import { describe, it, expect } from 'vitest'
import { eventFamily, countByFamily, filterByFamily, parseEventData, summarizeEventData } from '@/lib/events'
import type { ZeroEvent } from '@/types'

const ev = (event_type: string): ZeroEvent => ({
  id: event_type,
  event_type,
  event_data: {},
  source: null,
  correlation_id: null,
  timestamp: '2026-11-22T15:00:00Z',
})

const list = [ev('vector.upserted'), ev('vector.searched'), ev('table.created'), ev('heartbeat')]

describe('eventFamily', () => {
  it('uses the part before the first dot', () => {
    expect(eventFamily('vector.upserted')).toBe('vector')
  })

  it('uses the whole type when there is no dot', () => {
    expect(eventFamily('heartbeat')).toBe('heartbeat')
  })
})

describe('countByFamily', () => {
  it('counts each family, largest first, with an all total', () => {
    expect(countByFamily(list)).toEqual([
      { family: 'all', count: 4 },
      { family: 'vector', count: 2 },
      { family: 'heartbeat', count: 1 },
      { family: 'table', count: 1 },
    ])
  })
})

describe('filterByFamily', () => {
  it('returns everything for all', () => {
    expect(filterByFamily(list, 'all')).toHaveLength(4)
  })

  it('keeps one family', () => {
    expect(filterByFamily(list, 'vector').map((e) => e.event_type)).toEqual([
      'vector.upserted',
      'vector.searched',
    ])
  })
})

describe('parseEventData', () => {
  it('accepts an object', () => {
    expect(parseEventData('{"a":1}')).toEqual({ ok: true, value: { a: 1 } })
  })

  it('treats empty input as an empty object', () => {
    expect(parseEventData('  ')).toEqual({ ok: true, value: {} })
  })

  it('rejects arrays and bad JSON', () => {
    expect(parseEventData('[1]').ok).toBe(false)
    expect(parseEventData('{').ok).toBe(false)
  })
})

describe('summarizeEventData', () => {
  it('shows the first pairs, JSON for nested values', () => {
    expect(summarizeEventData({ a: 1, b: { c: 2 }, d: 'x', e: 4 })).toBe('a: 1 · b: {"c":2} · d: x')
  })
  it('handles empty data', () => {
    expect(summarizeEventData({})).toBe('')
  })
})
