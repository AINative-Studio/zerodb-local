/**
 * Guided "Add memory" form <-> the body of POST .../database/memory/store.
 */
import type { MemoryRole } from '@/types'

export interface MemoryFormState {
  role: MemoryRole
  content: string
  agentId: string
  sessionId: string
  tags: { key: string; value: string }[]
}

export interface StoreMemoryRequest {
  content: string
  role: MemoryRole
  agent_id: string
  session_id?: string
  metadata: Record<string, unknown>
}

export const ROLES: MemoryRole[] = ['user', 'assistant', 'system']

export function buildStoreRequest(form: MemoryFormState): StoreMemoryRequest {
  const metadata: Record<string, unknown> = {}
  for (const t of form.tags) {
    const k = t.key.trim()
    if (k) metadata[k] = t.value
  }
  const body: StoreMemoryRequest = {
    content: form.content,
    role: form.role,
    agent_id: form.agentId.trim() || 'default',
    metadata,
  }
  const sid = form.sessionId.trim()
  if (sid) body.session_id = sid
  return body
}

export type StoreParse = { ok: true; value: StoreMemoryRequest } | { ok: false; error: string }

export function parseStoreJson(text: string): StoreParse {
  let v: unknown
  try {
    v = JSON.parse(text)
  } catch (e) {
    return { ok: false, error: `Invalid JSON: ${(e as Error).message}` }
  }
  if (typeof v !== 'object' || v === null || Array.isArray(v)) return { ok: false, error: 'Body must be a JSON object.' }
  const o = v as Record<string, unknown>
  if (typeof o.content !== 'string' || !o.content.trim()) return { ok: false, error: '"content" is required.' }
  if (!ROLES.includes(o.role as MemoryRole)) return { ok: false, error: '"role" must be user, assistant or system.' }
  if (o.metadata !== undefined && (typeof o.metadata !== 'object' || o.metadata === null || Array.isArray(o.metadata))) {
    return { ok: false, error: '"metadata" must be an object.' }
  }
  const value: StoreMemoryRequest = {
    content: o.content,
    role: o.role as MemoryRole,
    agent_id: typeof o.agent_id === 'string' && o.agent_id.trim() ? o.agent_id : 'default',
    metadata: (o.metadata as Record<string, unknown>) ?? {},
  }
  if (typeof o.session_id === 'string' && o.session_id.trim()) value.session_id = o.session_id
  return { ok: true, value }
}

export function storeToForm(body: StoreMemoryRequest): MemoryFormState {
  const tags = Object.entries(body.metadata ?? {}).map(([key, value]) => ({
    key,
    value: typeof value === 'string' ? value : JSON.stringify(value),
  }))
  return {
    role: body.role,
    content: body.content,
    agentId: body.agent_id,
    sessionId: body.session_id ?? '',
    tags: tags.length ? tags : [{ key: '', value: '' }],
  }
}
