import { Link, useCanGoBack, useRouter } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { navCopy } from '@/lib/copy'
import { returnPlace } from '@/lib/returnPlace'

/** "Back" to wherever the student came from in the app (an upload, a search, the library). With `to="place"` (a case page) it goes to the
 *  last page outside the case, so a visit to the case's digest or decision in between never makes it loop. With nowhere to go back to,
 *  it offers the Case library (or My uploads). */
export function BackButton({ fallback = 'cases', to = 'history' }: { fallback?: 'cases' | 'uploads'; to?: 'history' | 'place' }) {
  const router = useRouter()
  const canGoBack = useCanGoBack()
  if (to === 'place') {
    // a case page: back to the last page outside the case (never to its own digest or decision page)
    const place = returnPlace()
    if (place) {
      return (
        <Button variant="ghost" size="sm" className="-ml-3 mb-3" onClick={() => void router.navigate({ href: place })}>
          <ArrowLeft data-icon="inline-start" aria-hidden />
          {navCopy.back}
        </Button>
      )
    }
  } else if (canGoBack) {
    return (
      <Button variant="ghost" size="sm" className="-ml-3 mb-3" onClick={() => router.history.back()}>
        <ArrowLeft data-icon="inline-start" aria-hidden />
        {navCopy.back}
      </Button>
    )
  }
  return (
    <Button variant="ghost" size="sm" asChild className="-ml-3 mb-3">
      <Link to="/library" search={{ tab: fallback }}>
        <ArrowLeft data-icon="inline-start" aria-hidden />
        {fallback === 'uploads' ? navCopy.toUploads : navCopy.toLibrary}
      </Link>
    </Button>
  )
}
