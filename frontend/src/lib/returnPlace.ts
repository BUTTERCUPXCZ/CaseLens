/** The last page the student was on outside a case's own pages (the case, its digest, its full decision): the library with its search,
 *  My uploads, an upload, the search results. The case page's Back goes there, so moving between a case and its digest or decision never
 *  makes Back loop. Kept for this tab only; a blocked storage just means Back offers the Case library. */
const KEY = 'caselens:return-place'

export const isCasePage = (pathname: string) => /^\/cases\/\d+(\/|$)/.test(pathname)

export function rememberPlace(href: string): void {
  try {
    sessionStorage.setItem(KEY, href)
  } catch {
    /* private window or blocked storage: Back falls back to the Case library */
  }
}

export function returnPlace(): string | null {
  try {
    return sessionStorage.getItem(KEY)
  } catch {
    return null
  }
}
