/**
 * The ZeroDB block "Z" mark (blocks only -- the brand system drops the trace
 * below 48px). Path data copied from the brand's Logo board; don't hand-edit.
 */
export function ZeroDBMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 56 50" role="img" aria-label="ZeroDB" className={className}>
      <path
        fill="currentColor"
        shapeRendering="crispEdges"
        d="M0 0h56v10h-56zM24 10h24v10h-24zM16 20h24v10h-24zM8 30h24v10h-24zM0 40h56v10h-56z"
      />
    </svg>
  )
}

export function BrandLockup() {
  return (
    <span className="flex items-center gap-2.5">
      <ZeroDBMark className="h-auto w-[22px] text-foreground dark:text-primary" />
      <span className="font-display text-lg font-bold tracking-tight">ZeroDB</span>
      <span className="rounded bg-accent px-1.5 py-0.5 font-mono text-[11px] font-medium text-accent-foreground">
        LOCAL
      </span>
    </span>
  )
}
