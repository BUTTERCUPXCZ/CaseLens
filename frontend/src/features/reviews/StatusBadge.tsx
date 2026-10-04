import { CheckCircle2, CircleAlert, CircleX, Loader2, SearchX } from 'lucide-react'

import type { CitationStatus } from '@/api/types'
import { citationStatus, type Tone } from '@/lib/copy'

const TONE_CLASS: Record<Tone, string> = {
  match: 'bg-match-wash text-match',
  look: 'bg-look-wash text-look',
  notfound: 'bg-notfound-wash text-notfound',
  problem: 'bg-problem-wash text-problem',
  checking: 'bg-muted text-muted-foreground',
}

const ICON: Record<CitationStatus, typeof CheckCircle2> = {
  match: CheckCircle2,
  mismatch: CircleAlert,
  not_found: SearchX,
  error: CircleX,
  pending: Loader2,
}

/** Never colour alone: every status has its own icon and its own words. */
export function StatusBadge({ status }: { status: CitationStatus }) {
  const { label, tone } = citationStatus[status]
  const Icon = ICON[status]
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${TONE_CLASS[tone]}`}
    >
      <Icon className={`size-4 ${status === 'pending' ? 'animate-spin' : ''}`} aria-hidden />
      {label}
    </span>
  )
}
