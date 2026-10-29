import { useSyncExternalStore } from 'react'

/** Light by default; the visitor can switch to dark with the navbar's button, and the choice is remembered in this browser.
 *  public/theme-init.js applies the same rule before the first paint. */
const KEY = 'caselens-landing-theme'
const listeners = new Set<() => void>()

const isDark = () => document.documentElement.classList.contains('dark')

export function setTheme(theme: 'light' | 'dark') {
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // Storage can be blocked (private mode); the choice just will not be remembered.
  }
  document.documentElement.classList.toggle('dark', theme === 'dark')
  listeners.forEach((listener) => listener())
}

function subscribe(onChange: () => void) {
  listeners.add(onChange)
  return () => listeners.delete(onChange)
}

export function useIsDark(): boolean {
  return useSyncExternalStore(subscribe, isDark, () => false)
}
