import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { ChevronLeft, ChevronRight, FileStack, Loader2, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { useDeleteReview } from '@/api/mutations'
import { REVIEWS_PAGE_SIZE, reviewsQuery } from '@/api/queries'
import type { Bulk } from '@/api/types'
import { PageHeader } from '@/components/PageHeader'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { reviewTitle } from '@/features/reviews/reviewTitle'
import { friendlyError, reviewsCopy } from '@/lib/copy'
import { formatWhen } from '@/lib/format'

export const Route = createFileRoute('/reviews/')({ component: ReviewsPage })

function ReviewRow({ bulk, onDelete }: { bulk: Bulk; onDelete: () => void }) {
  const title = reviewTitle(bulk)
  const c = bulk.counts
  const working = !bulk.finished || c.digests_pending > 0
  return (
    <li className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 py-5">
      <div className="min-w-0 flex-1 basis-72">
        <Link to="/reviews/$batchId" params={{ batchId: String(bulk.id) }} className="font-serif text-lg leading-snug font-semibold text-primary underline-offset-4 hover:underline">
          {title}
        </Link>
        <p className="mt-1 text-sm text-muted-foreground">
          {formatWhen(bulk.created_at)} · {bulk.topic_scope ? reviewsCopy.scope(bulk.topic_scope) : reviewsCopy.noScope}
        </p>
        {bulk.subjects.length > 0 ? <p className="mt-0.5 text-sm">{bulk.subjects.map((s) => s.name).join(' · ')}</p> : null}
        <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
          {working ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : null}
          {reviewsCopy.cases(c.found, c.digests_ready)}
          {!bulk.finished ? ` · ${reviewsCopy.working}` : ''}
        </p>
      </div>
      <div className="flex shrink-0 gap-2">
        <Button asChild size="sm">
          <Link to="/reviews/$batchId" params={{ batchId: String(bulk.id) }}>
            {reviewsCopy.open}
            <span className="sr-only"> {title}</span>
          </Link>
        </Button>
        <Button size="sm" variant="ghost" onClick={onDelete} aria-label={reviewsCopy.delete(title)}>
          <Trash2 aria-hidden />
        </Button>
      </div>
    </li>
  )
}

/** "My reviews": every upload, newest first. */
function ReviewsPage() {
  const [page, setPage] = useState(0)
  const [toDelete, setToDelete] = useState<Bulk | null>(null)
  const { data, error, isPending, refetch } = useQuery(reviewsQuery(page))
  const remove = useDeleteReview()

  return (
    <>
      <PageHeader title={reviewsCopy.title} description={reviewsCopy.description} />
      {isPending ? (
        <div className="space-y-4" aria-busy="true" aria-label="Loading your reviews">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} title="Your reviews didn't load" />
      ) : data.length === 0 && page === 0 ? (
        <EmptyState icon={FileStack} title={reviewsCopy.emptyTitle} action={<Button asChild><Link to="/upload">{reviewsCopy.newDigest}</Link></Button>}>
          {reviewsCopy.emptyBody}
        </EmptyState>
      ) : (
        <>
          <ul className="divide-y divide-border border-y border-border" aria-label={reviewsCopy.title}>
            {data.map((bulk) => (
              <ReviewRow key={bulk.id} bulk={bulk} onDelete={() => setToDelete(bulk)} />
            ))}
          </ul>
          {page > 0 || data.length === REVIEWS_PAGE_SIZE ? (
            <nav aria-label="Pages" className="mt-6 flex justify-end gap-2">
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
                <ChevronLeft data-icon="inline-start" aria-hidden /> Newer
              </Button>
              <Button variant="outline" size="sm" disabled={data.length < REVIEWS_PAGE_SIZE} onClick={() => setPage(page + 1)}>
                Older <ChevronRight data-icon="inline-end" aria-hidden />
              </Button>
            </nav>
          ) : null}
        </>
      )}

      <Dialog open={toDelete !== null} onOpenChange={(open) => (open ? undefined : setToDelete(null))}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{reviewsCopy.deleteTitle}</DialogTitle>
            <DialogDescription>
              <span className="font-medium text-foreground">{toDelete ? reviewTitle(toDelete) : ''}</span>. {reviewsCopy.deleteBody}
            </DialogDescription>
          </DialogHeader>
          {remove.isError ? <p role="alert" className="text-sm text-problem">{friendlyError(remove.error)}</p> : null}
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">{reviewsCopy.keep}</Button>
            </DialogClose>
            <Button
              variant="destructive"
              disabled={remove.isPending}
              onClick={() => toDelete && remove.mutate(toDelete.id, { onSuccess: () => setToDelete(null) })}
            >
              {remove.isPending ? reviewsCopy.deleting : reviewsCopy.deleteConfirm}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
