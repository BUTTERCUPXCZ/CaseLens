import { Link, useRouter, useRouterState } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'

/** "Back to the case" from its decision or digest page. When the student came here from that case's page, it steps back in the history
 *  (so the case page's own Back still leads where the student came from, instead of looping to this page); opened straight from a
 *  link, it opens the case. */
export function BackToCase({ caseId, label, className = 'mb-3' }: { caseId: number; label: string; className?: string }) {
  const router = useRouter()
  const cameFromCase = useRouterState({ select: (state) => state.location.state.fromCase === caseId })
  if (cameFromCase) {
    return (
      <Button variant="ghost" size="sm" className={`-ml-3 ${className}`} onClick={() => router.history.back()}>
        <ArrowLeft data-icon="inline-start" aria-hidden />
        {label}
      </Button>
    )
  }
  return (
    <Button variant="ghost" size="sm" asChild className={`-ml-3 ${className}`}>
      <Link to="/cases/$caseId" params={{ caseId: String(caseId) }}>
        <ArrowLeft data-icon="inline-start" aria-hidden />
        {label}
      </Link>
    </Button>
  )
}
