'use client'

import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/components/providers/theme-provider'

/** One-click light/dark flip for page headers. Settings offers System too. */
export function ThemeToggle() {
  const { resolved, setPreference } = useTheme()
  const next = resolved === 'dark' ? 'light' : 'dark'
  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setPreference(next)}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
    >
      {resolved === 'dark' ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
    </Button>
  )
}
