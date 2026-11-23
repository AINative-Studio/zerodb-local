import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider, useTheme } from '@/components/providers/theme-provider'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { THEME_STORAGE_KEY } from '@/lib/theme'

function mockMatchMedia(dark: boolean) {
  window.matchMedia = vi.fn().mockImplementation((q: string) => ({
    matches: dark && q.includes('dark'),
    media: q,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as any
}

function Probe() {
  const { preference, resolved, setPreference } = useTheme()
  return (
    <div>
      <span data-testid="pref">{preference}</span>
      <span data-testid="resolved">{resolved}</span>
      <button onClick={() => setPreference('dark')}>go dark</button>
    </div>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
    mockMatchMedia(false)
  })

  it('defaults to system and follows the OS', () => {
    mockMatchMedia(true)
    render(<ThemeProvider><Probe /></ThemeProvider>)
    expect(screen.getByTestId('pref').textContent).toBe('system')
    expect(screen.getByTestId('resolved').textContent).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('reads a stored preference', () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'dark')
    render(<ThemeProvider><Probe /></ThemeProvider>)
    expect(screen.getByTestId('resolved').textContent).toBe('dark')
  })

  it('applies and stores a new preference', async () => {
    render(<ThemeProvider><Probe /></ThemeProvider>)
    await act(async () => {
      await userEvent.click(screen.getByText('go dark'))
    })
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
  })

  it('survives storage that throws', () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    render(<ThemeProvider><Probe /></ThemeProvider>)
    expect(screen.getByTestId('pref').textContent).toBe('system')
    spy.mockRestore()
  })
})

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear()
    mockMatchMedia(false)
  })

  it('flips between light and dark', async () => {
    render(<ThemeProvider><ThemeToggle /><Probe /></ThemeProvider>)
    const btn = screen.getByRole('button', { name: /switch to dark mode/i })
    await act(async () => {
      await userEvent.click(btn)
    })
    expect(screen.getByTestId('resolved').textContent).toBe('dark')
    expect(screen.getByRole('button', { name: /switch to light mode/i })).toBeInTheDocument()
  })
})
