import { Link, useCanGoBack, useRouter } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { navCopy } from '@/lib/copy'

/** "Back" to wherever the student came from in the app (an upload, a search, the library). A page opened straight from a link has nowhere
 *  to go back to, so it offers the Case library instead. */
export function BackButton({ fallback = 'cases' }: { fallback?: 'cases' | 'uploads' }) {
  const router = useRouter()
  const canGoBack = useCanGoBack()
  if (canGoBack) {
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
