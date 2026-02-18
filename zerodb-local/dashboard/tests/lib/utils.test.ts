import { describe, it, expect } from 'vitest'
import { cn, formatBytes, formatNumber, formatDate, formatRelativeTime } from '@/lib/utils'

describe('cn (class name merger)', () => {
    it('merges multiple class names', () => {
        expect(cn('foo', 'bar')).toBe('foo bar')
    })

    it('handles conditional classes', () => {
        expect(cn('base', false && 'hidden', 'visible')).toBe('base visible')
    })

    it('deduplicates tailwind classes', () => {
        expect(cn('px-2', 'px-4')).toBe('px-4')
    })

    it('returns empty string for no inputs', () => {
        expect(cn()).toBe('')
    })

    it('handles undefined and null inputs', () => {
        expect(cn('base', undefined, null, 'extra')).toBe('base extra')
    })
})

describe('formatNumber', () => {
    it('formats small numbers without separators', () => {
        expect(formatNumber(42)).toBe('42')
    })

    it('formats large numbers with locale separators', () => {
        const result = formatNumber(1234567)
        // Locale-dependent grouping; just verify digits and separator presence
        expect(result.replace(/\D/g, '')).toBe('1234567')
        expect(result.length).toBeGreaterThan(7) // has separator chars
    })

    it('formats zero', () => {
        expect(formatNumber(0)).toBe('0')
    })

    it('formats negative numbers', () => {
        const result = formatNumber(-1000)
        expect(result).toContain('1')
        expect(result).toContain('000')
    })
})

describe('formatBytes', () => {
    it('formats 0 bytes', () => {
        expect(formatBytes(0)).toBe('0 Bytes')
    })

    it('formats bytes', () => {
        expect(formatBytes(500)).toBe('500 Bytes')
    })

    it('formats kilobytes', () => {
        expect(formatBytes(1024)).toBe('1 KB')
    })

    it('formats megabytes', () => {
        expect(formatBytes(1048576)).toBe('1 MB')
    })

    it('formats gigabytes', () => {
        expect(formatBytes(1073741824)).toBe('1 GB')
    })

    it('respects decimal precision', () => {
        expect(formatBytes(1536, 1)).toBe('1.5 KB')
    })

    it('handles custom decimal places', () => {
        expect(formatBytes(1536, 0)).toBe('2 KB')
    })
})

describe('formatDate', () => {
    it('formats ISO date string', () => {
        const result = formatDate('2024-06-15T12:00:00Z')
        expect(result).toContain('Jun')
        expect(result).toContain('15')
        expect(result).toContain('2024')
    })

    it('formats Date object', () => {
        const result = formatDate(new Date('2024-01-01'))
        expect(result).toContain('2024')
    })
})

describe('formatRelativeTime', () => {
    it('returns a string with relative time', () => {
        const recent = new Date(Date.now() - 60000).toISOString()
        const result = formatRelativeTime(recent)
        expect(result).toContain('ago')
    })

    it('handles Date objects', () => {
        const recent = new Date(Date.now() - 3600000)
        const result = formatRelativeTime(recent)
        expect(result).toContain('ago')
    })
})
