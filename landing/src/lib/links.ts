/** Where the landing page sends people. The app's address is set per deploy (VITE_APP_URL); the rest are fixed. */
const fallbackApp = 'https://caselens.vercel.app'

export const APP_URL = (import.meta.env.VITE_APP_URL || fallbackApp).replace(/\/+$/, '')

export const REPO_URL = 'https://github.com/BUTTERCUPXCZ/CaseLens'
export const DESKTOP_URL = `${REPO_URL}/releases/latest`

/** A page of the app, with search values set (the app's /search reads `q`). */
export function appLink(path: string, search?: Record<string, string>): string {
  const url = new URL(path, `${APP_URL}/`)
  for (const [key, value] of Object.entries(search ?? {})) url.searchParams.set(key, value)
  return url.toString()
}
