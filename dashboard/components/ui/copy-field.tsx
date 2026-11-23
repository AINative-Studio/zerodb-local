'use client'

import { Copy } from 'lucide-react'

export function CopyField({ value, label }: { value: string; label: string }) {
  const copy = () => {
    try {
      void navigator.clipboard?.writeText(value)
    } catch {
      // clipboard unavailable (insecure context); the value is still selectable
    }
  }
  return (
    <div className="flex h-11 items-center gap-2 rounded-lg bg-terminal pl-3 pr-1.5 font-mono text-[13px] text-terminal-foreground">
      <span className="flex-1 truncate">{value}</span>
      <button
        type="button"
        onClick={copy}
        aria-label={`Copy ${label}`}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md text-cyan-300 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Copy aria-hidden="true" className="h-4 w-4" />
      </button>
    </div>
  )
}
