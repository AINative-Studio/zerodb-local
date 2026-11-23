import { describe, it, expect } from 'vitest'
import { parseThemePreference, resolveTheme, THEME_STORAGE_KEY, themeInitScript } from '@/lib/theme'

describe('parseThemePreference', () => {
  it('accepts the three known preferences', () => {
    expect(parseThemePreference('light')).toBe('light')
    expect(parseThemePreference('dark')).toBe('dark')
    expect(parseThemePreference('system')).toBe('system')
  })

  it('falls back to system for missing or unknown values', () => {
    expect(parseThemePreference(null)).toBe('system')
    expect(parseThemePreference(undefined)).toBe('system')
    expect(parseThemePreference('purple')).toBe('system')
  })
})

describe('resolveTheme', () => {
  it('returns the explicit choice regardless of the OS', () => {
    expect(resolveTheme('light', true)).toBe('light')
    expect(resolveTheme('dark', false)).toBe('dark')
  })

  it('follows the OS when the preference is system', () => {
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
  })
})

describe('themeInitScript', () => {
  it('reads the same storage key the provider writes', () => {
    expect(themeInitScript).toContain(THEME_STORAGE_KEY)
  })

  it('never throws when storage is blocked', () => {
    expect(themeInitScript).toContain('try')
    expect(themeInitScript).toContain('catch')
  })
})
