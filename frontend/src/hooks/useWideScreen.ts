import { useSyncExternalStore } from 'react'

/** The width at which the AI assistant docks on the right of the page (`min-[90rem]` in the layout): the menu, the page and the
 *  panel need about 1440px side by side. Below it, the assistant opens as a sheet. */
const WIDE = '(min-width: 1440px)'

function subscribe(onChange: () => void) {
  const query = window.matchMedia(WIDE)
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}

export function useWideScreen(): boolean {
  return useSyncExternalStore(subscribe, () => window.matchMedia(WIDE).matches, () => false)
}
