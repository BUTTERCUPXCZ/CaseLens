import { useSyncExternalStore } from 'react'

/** Light for daytime reading; follows the device's dark setting for evening study until the
 *  student picks one by hand (then their choice is remembered). public/theme-init.js applies
 *  the same rule before the first paint. */
const KEY = 'caselens-theme'
const listeners = new Set<() => void>()

const isDark = () => document.documentElement.classList.contains('dark')

function apply(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark)
  listeners.forEach((listener) => listener())
}

export function setTheme(theme: 'light' | 'dark') {
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // Storage can be blocked (private mode); the choice just will not be remembered.
  }
  apply(theme === 'dark')
}

function subscribe(onChange: () => void) {
  listeners.add(onChange)
  const system = window.matchMedia('(prefers-color-scheme: dark)')
  const follow = () => {
    let chosen: string | null = null
    try {
      chosen = localStorage.getItem(KEY)
    } catch {
      // ignore
    }
    if (!chosen) apply(system.matches) // no hand-picked theme: keep following the device
  }
  system.addEventListener('change', follow)
  return () => {
    listeners.delete(onChange)
    system.removeEventListener('change', follow)
  }
}

export function useIsDark(): boolean {
  return useSyncExternalStore(subscribe, isDark, () => false)
}
