import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ChevronLeft, ChevronRight, FileSearch, FileStack, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { useDeleteReview } from '@/api/mutations'
import { REVIEWS_PAGE_SIZE, reviewsQuery } from '@/api/queries'
import type { Bulk } from '@/api/types'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { friendlyError, individualCopy, reviewsCopy } from '@/lib/copy'
import { formatWhen } from '@/lib/format'

import { reviewTitle, uploadedLabel } from './reviewTitle'
import { TONE_CLASS, uploadState } from './uploadState'

function UploadRow({ bulk, onDelete }: { bulk: Bulk; onDelete: () => void }) {
  const title = reviewTitle(bulk)
  const state = uploadState(bulk)
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-5">
      <div className="min-w-0 flex-1 basis-72">
        <Link
          to="/reviews/$batchId"
          params={{ batchId: String(bulk.id) }}
          className="font-serif text-lg leading-snug font-semibold text-primary underline-offset-4 hover:underline"
        >
          {title}
        </Link>
        <span className="ml-2 rounded-full border border-border px-2 py-0.5 align-middle text-xs font-medium">{reviewsCopy.kind[bulk.kind]}</span>
        {bulk.cases.length === 1 && bulk.case_total === 1 ? (
          <p className="tabular mt-0.5 text-base text-muted-foreground">G.R. No. {bulk.cases[0]!.gr_no}</p>
        ) : bulk.cases.length > 0 ? (
          <ul className="mt-1.5 space-y-0.5 text-base" aria-label={reviewsCopy.casesIn(title)}>
            {bulk.cases.map((c) => (
              <li key={c.gr_no}>
                <span className="font-medium">{c.name}</span> <span className="tabular text-muted-foreground">· G.R. No. {c.gr_no}</span>
              </li>
            ))}
            {bulk.case_total > bulk.cases.length ? <li className="text-sm text-muted-foreground">{reviewsCopy.moreCases(bulk.case_total - bulk.cases.length)}</li> : null}
          </ul>
        ) : null}
        <p className={`mt-1 flex items-center gap-1.5 text-base font-medium ${TONE_CLASS[state.tone]}`}>
          <state.icon className={`size-4 shrink-0 ${state.busy ? 'animate-spin' : ''}`} aria-hidden />
          {state.label}
        </p>
        <p className="mt-0.5 text-sm text-muted-foreground">
          {reviewsCopy.uploaded(uploadedLabel(bulk))} · {formatWhen(bulk.created_at)} · {bulk.topic_scope ? reviewsCopy.scope(bulk.topic_scope) : reviewsCopy.noScope}
          {bulk.subjects.length > 0 ? ` · ${bulk.subjects.map((s) => s.name).join(', ')}` : ''}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <Button asChild>
          <Link to="/reviews/$batchId" params={{ batchId: String(bulk.id) }}>
            {reviewsCopy.open}{' '}
            <span className="sr-only">{title}</span>
          </Link>
        </Button>
        <Button size="icon" variant="ghost" className="size-11" onClick={onDelete} aria-label={reviewsCopy.delete(title)}>
          <Trash2 aria-hidden />
        </Button>
      </div>
    </li>
  )
}

/** "My uploads": every upload, newest first, its state in words, one clear way in (Open), and delete with a confirm. */
export function UploadList() {
  const [page, setPage] = useState(0)
  const [toDelete, setToDelete] = useState<Bulk | null>(null)
  const { data, error, isPending, refetch } = useQuery(reviewsQuery(page))
  const remove = useDeleteReview()

  if (isPending) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading your uploads">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    )
  }
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} title="Your uploads didn't load" />
  if (data.length === 0 && page === 0) {
    return (
      <EmptyState
        icon={FileStack}
        title={reviewsCopy.emptyTitle}
        action={
          <Button asChild>
            <Link to="/individual">
              <FileSearch data-icon="inline-start" aria-hidden />
              {individualCopy.title}
            </Link>
          </Button>
        }
      >
        {reviewsCopy.emptyBody}
      </EmptyState>
    )
  }

  return (
    <>
      <p className="mb-2 max-w-prose text-base text-muted-foreground">{reviewsCopy.description}</p>
      <ul className="divide-y divide-border border-y border-border" aria-label={reviewsCopy.title}>
        {data.map((bulk) => (
          <UploadRow key={bulk.id} bulk={bulk} onDelete={() => setToDelete(bulk)} />
        ))}
      </ul>
      {page > 0 || data.length === REVIEWS_PAGE_SIZE ? (
        <nav aria-label="Pages of uploads" className="mt-6 flex justify-end gap-2">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
            <ChevronLeft data-icon="inline-start" aria-hidden /> Newer
          </Button>
          <Button variant="outline" size="sm" disabled={data.length < REVIEWS_PAGE_SIZE} onClick={() => setPage(page + 1)}>
            Older <ChevronRight data-icon="inline-end" aria-hidden />
          </Button>
        </nav>
      ) : null}

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
            <Button variant="destructive" disabled={remove.isPending} onClick={() => toDelete && remove.mutate(toDelete.id, { onSuccess: () => setToDelete(null) })}>
              {remove.isPending ? reviewsCopy.deleting : reviewsCopy.deleteConfirm}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
