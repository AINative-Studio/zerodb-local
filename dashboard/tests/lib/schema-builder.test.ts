import { describe, it, expect } from 'vitest'
import {
  columnsToSchema,
  schemaToColumns,
  validateColumns,
  validateTableName,
  parseSchemaJson,
  coerceRow,
  type Column,
} from '@/lib/schema-builder'

const cols: Column[] = [
  { name: 'subject', type: 'string', required: true },
  { name: 'status', type: 'enum', required: true, options: ['open', 'pending', 'closed'] },
  { name: 'priority', type: 'integer', required: false },
]

describe('columnsToSchema', () => {
  it('produces the API {fields: {...}} shape', () => {
    expect(columnsToSchema(cols)).toEqual({
      fields: {
        subject: { type: 'string', required: true },
        status: { type: 'string', required: true, enum: ['open', 'pending', 'closed'] },
        priority: { type: 'integer', required: false },
      },
    })
  })

  it('trims column names and skips blank rows', () => {
    const schema = columnsToSchema([
      { name: '  title ', type: 'string', required: false },
      { name: '', type: 'string', required: false },
    ])
    expect(Object.keys(schema.fields)).toEqual(['title'])
  })
})

describe('schemaToColumns', () => {
  it('round-trips with columnsToSchema', () => {
    expect(schemaToColumns(columnsToSchema(cols))).toEqual(cols)
  })

  it('treats a string field with enum as an enum column', () => {
    const out = schemaToColumns({ fields: { s: { type: 'string', enum: ['a'] } } })
    expect(out[0]).toEqual({ name: 's', type: 'enum', required: false, options: ['a'] })
  })

  it('accepts a flat schema without the fields wrapper', () => {
    const out = schemaToColumns({ age: { type: 'integer', required: true } })
    expect(out).toEqual([{ name: 'age', type: 'integer', required: true }])
  })

  it('maps unknown types to json', () => {
    const out = schemaToColumns({ fields: { blob: { type: 'object' } } })
    expect(out[0].type).toBe('json')
  })
})

describe('validateTableName', () => {
  it('requires a name', () => {
    expect(validateTableName('')).toMatch(/required/i)
  })

  it('allows letters, numbers and underscores starting with a letter', () => {
    expect(validateTableName('support_tickets2')).toBeNull()
  })

  it('rejects spaces, dashes and leading digits', () => {
    expect(validateTableName('my table')).not.toBeNull()
    expect(validateTableName('my-table')).not.toBeNull()
    expect(validateTableName('2tables')).not.toBeNull()
  })
})

describe('validateColumns', () => {
  it('needs at least one named column', () => {
    expect(validateColumns([{ name: '', type: 'string', required: false }])).toMatch(/at least one/i)
  })

  it('rejects duplicate names', () => {
    expect(
      validateColumns([
        { name: 'a', type: 'string', required: false },
        { name: 'a', type: 'integer', required: false },
      ])
    ).toMatch(/duplicate/i)
  })

  it('rejects reserved names the API adds itself', () => {
    expect(validateColumns([{ name: 'id', type: 'string', required: false }])).toMatch(/reserved/i)
  })

  it('needs options for an enum column', () => {
    expect(validateColumns([{ name: 's', type: 'enum', required: false, options: [] }])).toMatch(/option/i)
  })

  it('passes a valid set', () => {
    expect(validateColumns(cols)).toBeNull()
  })
})

describe('parseSchemaJson', () => {
  it('returns columns for valid JSON', () => {
    const r = parseSchemaJson(JSON.stringify(columnsToSchema(cols)))
    expect(r.ok).toBe(true)
    if (r.ok) expect(r.columns).toHaveLength(3)
  })

  it('returns a readable error for invalid JSON', () => {
    const r = parseSchemaJson('{ nope')
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.error).toMatch(/json/i)
  })

  it('rejects JSON that is not an object', () => {
    const r = parseSchemaJson('[1,2]')
    expect(r.ok).toBe(false)
  })
})

describe('coerceRow', () => {
  const columns: Column[] = [
    { name: 'title', type: 'string', required: true },
    { name: 'count', type: 'integer', required: false },
    { name: 'price', type: 'number', required: false },
    { name: 'done', type: 'boolean', required: false },
    { name: 'extra', type: 'json', required: false },
  ]

  it('converts form strings to typed values and skips blanks', () => {
    expect(coerceRow(columns, { title: 'a', count: '3', price: '2.5', done: 'true', extra: '{"x":1}' })).toEqual({
      ok: true,
      row: { title: 'a', count: 3, price: 2.5, done: true, extra: { x: 1 } },
    })
    expect(coerceRow(columns, { title: 'a', count: '' })).toEqual({ ok: true, row: { title: 'a' } })
  })

  it('reports missing required values', () => {
    const r = coerceRow(columns, { title: ' ' })
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.error).toMatch(/title/)
  })

  it('reports bad numbers and JSON', () => {
    expect(coerceRow(columns, { title: 'a', count: '1.5' }).ok).toBe(false)
    expect(coerceRow(columns, { title: 'a', price: 'abc' }).ok).toBe(false)
    expect(coerceRow(columns, { title: 'a', extra: '{' }).ok).toBe(false)
  })
})
