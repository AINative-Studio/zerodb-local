'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { KeyRound } from 'lucide-react'
import { useAuthRequired } from '@/components/providers/query-provider'

/** Shown on every page once the API has refused a request for lack of a key. */
export function AuthNotice() {
  const { required } = useAuthRequired()
  const pathname = usePathname()
  if (!required) return null
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 border-b border-warning/40 bg-warning-muted px-4 py-3 text-sm text-warning sm:px-10">
      <KeyRound aria-hidden="true" className="h-4 w-4 shrink-0" />
      <span className="flex-1">
        <strong>This server needs an API key.</strong> It has a local access key (ZERODB_LOCAL_API_KEY) or cloud sign-in turned on.
      </span>
      {pathname !== '/settings' && (
        <Link href="/settings#connection" className="font-semibold text-warning underline">
          Add your key in Settings
        </Link>
      )}
    </div>
  )
}
