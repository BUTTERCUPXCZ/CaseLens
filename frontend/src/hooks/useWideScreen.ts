import { useSyncExternalStore } from 'react'

/** The width at which the AI assistant docks on the right of the page (the layout's `xl`); below it, it opens as a sheet. */
const WIDE = '(min-width: 1280px)'

function subscribe(onChange: () => void) {
  const query = window.matchMedia(WIDE)
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}

export function useWideScreen(): boolean {
  return useSyncExternalStore(subscribe, () => window.matchMedia(WIDE).matches, () => false)
}
