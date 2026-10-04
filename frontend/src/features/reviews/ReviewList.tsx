import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { CheckCircle2, ChevronRight, CircleAlert, FileText, Loader2 } from 'lucide-react'

import { uploadsQuery } from '@/api/queries'
import type { UploadSummary } from '@/api/types'
import { ErrorState } from '@/components/States'
import { Skeleton } from '@/components/ui/skeleton'
import { formatWhen } from '@/lib/format'

import { headline, summaryText } from './summary'

const HEADLINE_ICON = {
  checking: { Icon: Loader2, className: 'animate-spin text-muted-foreground', label: 'Still checking' },
  'needs-attention': { Icon: CircleAlert, className: 'text-look', label: 'Needs a look' },
  'all-clear': { Icon: CheckCircle2, className: 'text-match', label: 'All match' },
  empty: { Icon: FileText, className: 'text-muted-foreground', label: 'No cases found' },
} as const

function ReviewRow({ review }: { review: UploadSummary }) {
  const state = headline(review)
  const { Icon, className, label } = HEADLINE_ICON[state]
  return (
    <li>
      <Link
        to="/reviews/$reviewId"
        params={{ reviewId: String(review.id) }}
        className="group flex items-center gap-4 px-1 py-4 hover:bg-accent/60 md:px-3"
      >
        <Icon className={`size-5 shrink-0 ${className}`} aria-label={label} role="img" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-medium">{review.filename}</p>
          <p className="text-sm text-muted-foreground">{summaryText(review)}</p>
        </div>
        <span className="hidden shrink-0 text-sm text-muted-foreground sm:block">{formatWhen(review.created_at)}</span>
        <ChevronRight className="size-4 shrink-0 text-muted-foreground group-hover:text-foreground" aria-hidden />
      </Link>
    </li>
  )
}

export function ReviewList({ limit, emptyMessage }: { limit: number; emptyMessage: string }) {
  const { data, error, isPending, refetch } = useQuery(uploadsQuery(limit))

  if (isPending) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading your reviews">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    )
  }
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} title="Your reviews didn't load" />
  if (data.length === 0) return <p className="text-base text-muted-foreground">{emptyMessage}</p>

  return (
    <ul className="divide-y divide-border border-y border-border">
      {data.map((review) => (
        <ReviewRow key={review.id} review={review} />
      ))}
    </ul>
  )
}
