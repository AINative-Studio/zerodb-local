'use client'

import * as React from 'react'

/**
 * False during the server render and the first client render, true after.
 * Use it for values only the browser knows (the client-side API URL,
 * localStorage choices) so server and client HTML match on hydration.
 */
export function useMounted(): boolean {
  const [mounted, setMounted] = React.useState(false)
  React.useEffect(() => setMounted(true), [])
  return mounted
}
