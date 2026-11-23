'use client'

import * as React from 'react'

/**
 * True when the page was opened with ?new=1 (links from Overview and empty
 * states open the create dialog directly). Reads window.location in an
 * effect so pages stay statically renderable without a Suspense boundary.
 */
export function useNewParam(): [boolean, (open: boolean) => void] {
  const [open, setOpen] = React.useState(false)
  React.useEffect(() => {
    if (new URLSearchParams(window.location.search).get('new') === '1') setOpen(true)
  }, [])
  return [open, setOpen]
}
