'use client'

import * as React from 'react'
import {
  parseThemePreference,
  resolveTheme,
  THEME_STORAGE_KEY,
  type ResolvedTheme,
  type ThemePreference,
} from '@/lib/theme'

interface ThemeContextValue {
  preference: ThemePreference
  resolved: ResolvedTheme
  setPreference: (p: ThemePreference) => void
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null)

const DARK_QUERY = '(prefers-color-scheme: dark)'

function readStored(): ThemePreference {
  try {
    return parseThemePreference(window.localStorage.getItem(THEME_STORAGE_KEY))
  } catch {
    return 'system'
  }
}

function systemPrefersDark(): boolean {
  try {
    return typeof window.matchMedia === 'function' && window.matchMedia(DARK_QUERY).matches
  } catch {
    return false
  }
}

function apply(theme: ResolvedTheme) {
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
  root.style.colorScheme = theme
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Start from the same values the server rendered with, then read the
  // real ones after mount so hydration matches. The inline script in
  // <head> has already set the <html> class, so there's no flash.
  const [preference, setPref] = React.useState<ThemePreference>('system')
  const [systemDark, setSystemDark] = React.useState(false)
  const [ready, setReady] = React.useState(false)

  React.useEffect(() => {
    // One-shot hydration sync (see the comment above the state
    // declarations): reads browser-only values once on mount so server
    // and client HTML match, no cascading-render risk from the fixed,
    // empty dependency array.
    /* eslint-disable react-hooks/set-state-in-effect */
    setPref(readStored())
    setSystemDark(systemPrefersDark())
    setReady(true)
    /* eslint-enable react-hooks/set-state-in-effect */
    if (typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia(DARK_QUERY)
    const onChange = (e: MediaQueryListEvent) => setSystemDark(e.matches)
    mq.addEventListener?.('change', onChange)
    return () => mq.removeEventListener?.('change', onChange)
  }, [])

  const resolved = resolveTheme(preference, systemDark)

  React.useEffect(() => {
    // Before storage is read, leave the class the head script set alone.
    if (ready) apply(resolved)
  }, [resolved, ready])

  const setPreference = React.useCallback((p: ThemePreference) => {
    setPref(p)
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, p)
    } catch {
      // Private mode or blocked storage: the choice still applies for this visit.
    }
  }, [])

  const value = React.useMemo(() => ({ preference, resolved, setPreference }), [preference, resolved, setPreference])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const ctx = React.useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>')
  return ctx
}
