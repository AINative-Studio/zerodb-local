import type { ZeroEvent } from '@/types'

/** "vector.upserted" -> "vector"; types without a dot are their own family. */
export function eventFamily(type: string): string {
  const i = type.indexOf('.')
  return i === -1 ? type : type.slice(0, i)
}

export interface FamilyCount {
  family: string
  count: number
}

export function countByFamily(events: ZeroEvent[]): FamilyCount[] {
  const counts = new Map<string, number>()
  for (const e of events) {
    const f = eventFamily(e.event_type)
    counts.set(f, (counts.get(f) ?? 0) + 1)
  }
  const families = Array.from(counts, ([family, count]) => ({ family, count })).sort(
    (a, b) => b.count - a.count || a.family.localeCompare(b.family)
  )
  return [{ family: 'all', count: events.length }, ...families]
}

export function filterByFamily(events: ZeroEvent[], family: string): ZeroEvent[] {
  if (family === 'all') return events
  return events.filter((e) => eventFamily(e.event_type) === family)
}

export type DataParse = { ok: true; value: Record<string, unknown> } | { ok: false; error: string }

export function parseEventData(text: string): DataParse {
  if (!text.trim()) return { ok: true, value: {} }
  try {
    const v = JSON.parse(text)
    if (typeof v !== 'object' || v === null || Array.isArray(v)) {
      return { ok: false, error: 'Event data must be a JSON object.' }
    }
    return { ok: true, value: v }
  } catch (e) {
    return { ok: false, error: `Invalid JSON: ${(e as Error).message}` }
  }
}

/** One-line preview of an event payload: the first few key/value pairs. */
export function summarizeEventData(data: Record<string, unknown>, max = 3): string {
  return Object.entries(data ?? {})
    .slice(0, max)
    .map(([k, v]) => `${k}: ${typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v)}`)
    .join(' · ')
}
