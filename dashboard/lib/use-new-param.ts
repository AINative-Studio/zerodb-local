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
    // One-shot read of a browser-only API on mount (see the docstring
    // above for why this can't just be the initial useState value), empty
    // deps, no cascading-render risk.
    /* eslint-disable-next-line react-hooks/set-state-in-effect */
    if (new URLSearchParams(window.location.search).get('new') === '1') setOpen(true)
  }, [])
  return [open, setOpen]
}
