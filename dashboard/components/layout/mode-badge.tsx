'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api-client'
import { cn } from '@/lib/utils'

const STACK: Record<string, string> = {
  lite: 'SQLite · FAISS · files',
  full: 'Postgres · Qdrant · MinIO',
}

/**
 * States which backend is actually running, from /health, instead of
 * assuming full mode (the assumption behind the old home-page crash).
 */
export function ModeBadge({ className, compact }: { className?: string; compact?: boolean }) {
  const { data, isError } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 5000,
  })

  const backend = data?.backend ?? (data ? 'full' : undefined)
  const dot = isError
    ? 'bg-destructive'
    : data?.status === 'healthy'
      ? 'bg-emerald-500'
      : data
        ? 'bg-amber-500'
        : 'bg-muted-foreground'
  const label = isError ? 'API offline' : backend ? `${backend === 'lite' ? 'Lite' : 'Full'} mode` : 'Connecting'

  return (
    <span
      className={cn(
        'inline-flex h-8 items-center gap-2 rounded-full border bg-card px-3 text-[13px]',
        className
      )}
    >
      <span aria-hidden="true" className={cn('h-2 w-2 shrink-0 rounded-full', dot)} />
      <strong className="font-semibold">{label}</strong>
      {backend && !isError && !compact && (
        <span className="hidden font-mono text-xs text-muted-foreground sm:inline">{STACK[backend]}</span>
      )}
    </span>
  )
}
