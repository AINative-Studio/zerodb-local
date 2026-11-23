/**
 * Guided form state <-> the body of POST .../database/vectors/upsert.
 * The API embeds `document` server-side, so the guided form only needs text.
 */

export interface Tag {
  key: string
  value: string
}

export interface VectorFormState {
  document: string
  namespace: string
  vectorId: string
  tags: Tag[]
}

export interface UpsertVectorRequest {
  document: string
  namespace: string
  vector_id?: string
  metadata: Record<string, unknown>
}

export const EMPTY_VECTOR_FORM: VectorFormState = {
  document: '',
  namespace: 'default',
  vectorId: '',
  tags: [{ key: '', value: '' }],
}

export function buildUpsertRequest(form: VectorFormState): UpsertVectorRequest {
  const metadata: Record<string, unknown> = {}
  for (const t of form.tags) {
    const k = t.key.trim()
    if (k) metadata[k] = t.value
  }
  const req: UpsertVectorRequest = {
    document: form.document,
    namespace: form.namespace.trim() || 'default',
    metadata,
  }
  const id = form.vectorId.trim()
  if (id) req.vector_id = id
  return req
}

export type UpsertParse = { ok: true; value: UpsertVectorRequest } | { ok: false; error: string }

export function parseUpsertJson(text: string): UpsertParse {
  let v: unknown
  try {
    v = JSON.parse(text)
  } catch (e) {
    return { ok: false, error: `Invalid JSON: ${(e as Error).message}` }
  }
  if (typeof v !== 'object' || v === null || Array.isArray(v)) {
    return { ok: false, error: 'Body must be a JSON object.' }
  }
  const o = v as Record<string, unknown>
  if (typeof o.document !== 'string' || !o.document.trim()) {
    return { ok: false, error: '"document" is required and must be text.' }
  }
  if (o.metadata !== undefined && (typeof o.metadata !== 'object' || o.metadata === null || Array.isArray(o.metadata))) {
    return { ok: false, error: '"metadata" must be an object.' }
  }
  const value: UpsertVectorRequest = {
    document: o.document,
    namespace: typeof o.namespace === 'string' && o.namespace.trim() ? o.namespace : 'default',
    metadata: (o.metadata as Record<string, unknown>) ?? {},
  }
  if (typeof o.vector_id === 'string' && o.vector_id.trim()) value.vector_id = o.vector_id
  return { ok: true, value }
}

export function requestToForm(req: UpsertVectorRequest): VectorFormState {
  const tags = Object.entries(req.metadata ?? {}).map(([key, value]) => ({
    key,
    value: typeof value === 'string' ? value : JSON.stringify(value),
  }))
  return {
    document: req.document,
    namespace: req.namespace,
    vectorId: req.vector_id ?? '',
    tags: tags.length ? tags : [{ key: '', value: '' }],
  }
}
