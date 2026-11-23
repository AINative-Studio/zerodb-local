/**
 * Converts between the guided "column builder" rows and the table schema the
 * API expects: `{ fields: { <name>: { type, required, enum? } } }`.
 */

export type ColumnType = 'string' | 'integer' | 'number' | 'boolean' | 'datetime' | 'enum' | 'json'

export interface Column {
  name: string
  type: ColumnType
  required: boolean
  options?: string[]
}

export interface FieldDef {
  type: string
  required?: boolean
  enum?: string[]
}

export interface TableSchema {
  fields: Record<string, FieldDef>
}

/** Plain-language labels for people who don't think in JSON types. */
export const COLUMN_TYPE_LABELS: Record<ColumnType, string> = {
  string: 'Text',
  integer: 'Whole number',
  number: 'Decimal number',
  boolean: 'True / false',
  datetime: 'Date and time',
  enum: 'One of a list',
  json: 'JSON',
}

/** The API adds these to every row itself. */
const RESERVED = new Set(['id', 'created_at', 'updated_at'])
const KNOWN: ColumnType[] = ['string', 'integer', 'number', 'boolean', 'datetime', 'json']

export function columnsToSchema(columns: Column[]): TableSchema {
  const fields: Record<string, FieldDef> = {}
  for (const col of columns) {
    const name = col.name.trim()
    if (!name) continue
    if (col.type === 'enum') {
      fields[name] = { type: 'string', required: col.required, enum: col.options ?? [] }
    } else {
      fields[name] = { type: col.type, required: col.required }
    }
  }
  return { fields }
}

export function schemaToColumns(schema: Record<string, unknown>): Column[] {
  const raw = (isObject(schema.fields) ? schema.fields : schema) as Record<string, unknown>
  return Object.entries(raw).map(([name, def]) => {
    const d = (isObject(def) ? def : {}) as Record<string, unknown>
    const required = d.required === true
    if (Array.isArray(d.enum)) {
      return { name, type: 'enum', required, options: d.enum.map(String) }
    }
    const type = KNOWN.includes(d.type as ColumnType) ? (d.type as ColumnType) : 'json'
    return { name, type, required }
  })
}

export function validateTableName(name: string): string | null {
  const n = name.trim()
  if (!n) return 'Table name is required.'
  if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(n)) {
    return 'Use letters, numbers and underscores, starting with a letter.'
  }
  return null
}

export function validateColumns(columns: Column[]): string | null {
  const named = columns.filter((c) => c.name.trim())
  if (named.length === 0) return 'Add at least one column.'
  const seen = new Set<string>()
  for (const c of named) {
    const n = c.name.trim()
    if (RESERVED.has(n)) return `"${n}" is reserved; every row gets it automatically.`
    if (seen.has(n)) return `Duplicate column name "${n}".`
    seen.add(n)
    if (c.type === 'enum' && !(c.options ?? []).some((o) => o.trim())) {
      return `Give "${n}" at least one option.`
    }
  }
  return null
}

export type ParseResult = { ok: true; columns: Column[] } | { ok: false; error: string }

export function parseSchemaJson(text: string): ParseResult {
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch (e) {
    return { ok: false, error: `Invalid JSON: ${(e as Error).message}` }
  }
  if (!isObject(value)) return { ok: false, error: 'Schema must be a JSON object.' }
  return { ok: true, columns: schemaToColumns(value) }
}

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

export type RowResult = { ok: true; row: Record<string, unknown> } | { ok: false; error: string }

/** Turns the add-row form's string inputs into typed values for the API. */
export function coerceRow(columns: Column[], values: Record<string, string>): RowResult {
  const row: Record<string, unknown> = {}
  for (const c of columns) {
    const raw = (values[c.name] ?? '').trim()
    if (!raw) {
      if (c.required) return { ok: false, error: `"${c.name}" is required.` }
      continue
    }
    switch (c.type) {
      case 'integer':
        if (!/^-?\d+$/.test(raw)) return { ok: false, error: `"${c.name}" must be a whole number.` }
        row[c.name] = parseInt(raw, 10)
        break
      case 'number': {
        const n = Number(raw)
        if (!Number.isFinite(n)) return { ok: false, error: `"${c.name}" must be a number.` }
        row[c.name] = n
        break
      }
      case 'boolean':
        row[c.name] = raw === 'true'
        break
      case 'json':
        try {
          row[c.name] = JSON.parse(raw)
        } catch {
          return { ok: false, error: `"${c.name}" must be valid JSON.` }
        }
        break
      default:
        row[c.name] = raw
    }
  }
  return { ok: true, row }
}
