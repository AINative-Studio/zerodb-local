import { describe, it, expect } from 'vitest'
import { arrayBufferToBase64, base64ToBytes, describeContentType } from '@/lib/files'

describe('base64 helpers', () => {
  it('round-trips bytes', () => {
    const bytes = new Uint8Array([0, 1, 2, 250, 255])
    const b64 = arrayBufferToBase64(bytes.buffer)
    expect(b64).toBe('AAEC+v8=')
    expect(Array.from(base64ToBytes(b64))).toEqual([0, 1, 2, 250, 255])
  })

  it('handles buffers larger than one chunk', () => {
    const big = new Uint8Array(100_000).map((_, i) => i % 256)
    const back = base64ToBytes(arrayBufferToBase64(big.buffer))
    expect(back.length).toBe(100_000)
    expect(back[99_999]).toBe(99_999 % 256)
  })
})

describe('describeContentType', () => {
  it('names common types in plain words', () => {
    expect(describeContentType('application/pdf')).toBe('PDF')
    expect(describeContentType('image/png')).toBe('PNG image')
    expect(describeContentType('text/csv')).toBe('CSV')
    expect(describeContentType('application/json')).toBe('JSON')
  })

  it('falls back to the raw type', () => {
    expect(describeContentType('application/x-thing')).toBe('application/x-thing')
  })
})
