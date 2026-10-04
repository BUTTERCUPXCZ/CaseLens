import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, notFound, useNavigate } from '@tanstack/react-router'
import { Loader2, RotateCw } from 'lucide-react'
import { z } from 'zod'

import { useRetryReview } from '@/api/mutations'
import { orNotFound } from '@/api/orNotFound'
import { uploadQuery } from '@/api/queries'
import { Disclaimer } from '@/components/Disclaimer'
import { PageHeader } from '@/components/PageHeader'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FinishedReviewer } from '@/features/digest/FinishedReviewer'
import { CitationSection } from '@/features/reviews/CitationSection'
import { summaryText } from '@/features/reviews/summary'
import { finishedCopy, friendlyError, summarizeReview } from '@/lib/copy'
import { formatWhen } from '@/lib/format'
import { FileQuestion } from 'lucide-react'

const searchSchema = z.object({ view: z.enum(['check', 'finished']).optional().catch(undefined) })

export const Route = createFileRoute('/reviews/$reviewId')({
  validateSearch: searchSchema,
  loader: ({ context, params }) => {
    const id = Number(params.reviewId)
    if (!Number.isInteger(id)) throw notFound()
    return orNotFound(context.queryClient.ensureQueryData(uploadQuery(id)))
  },
  pendingComponent: ResultsSkeleton,
  errorComponent: ({ error, reset }) => <ErrorState error={error} onRetry={reset} title="This review didn't open" />,
  notFoundComponent: () => (
    <EmptyState icon={FileQuestion} title="We can't find that review" action={<Link to="/reviews" className="underline">See your reviews</Link>}>
      The link may be old, or the review may have been removed.
    </EmptyState>
  ),
  component: ReviewResults,
})

function ResultsSkeleton() {
  return (
    <div aria-busy="true" aria-label="Opening your review" className="space-y-6">
      <Skeleton className="h-10 w-2/3" />
      <Skeleton className="h-6 w-1/2" />
      <Skeleton className="h-64 w-full" />
    </div>
  )
}

function ReviewResults() {
  const reviewId = Number(Route.useParams().reviewId)
  const view = Route.useSearch().view ?? 'check'
  const navigate = useNavigate({ from: Route.fullPath })
  const { data: review } = useQuery(uploadQuery(reviewId))
  const retry = useRetryReview()
  if (!review) return <ResultsSkeleton />

  const citations = review.citations
  const count = (status: string) => citations.filter((c) => c.status === status).length
  const counts = {
    total: citations.length,
    matched: count('match'),
    needs_look: count('mismatch'),
    not_found: count('not_found'),
    errors: count('error'),
    pending: count('pending'),
  }
  const checking = review.status === 'processing' || counts.pending > 0

  return (
    <>
      <PageHeader
        title={review.filename}
        description={`${summaryText(counts)} · ${formatWhen(review.created_at)}`}
        actions={
          <Button variant="outline" asChild>
            <Link to="/">Check another</Link>
          </Button>
        }
      />

      <Tabs value={view} onValueChange={(next) => void navigate({ search: { view: next === 'finished' ? 'finished' : undefined }, replace: true })}>
        <TabsList className="mb-6">
          <TabsTrigger value="check">{finishedCopy.tabCheck}</TabsTrigger>
          <TabsTrigger value="finished">{finishedCopy.tabFinished}</TabsTrigger>
        </TabsList>

        <TabsContent value="check">
      {/* Spoken to screen readers as it changes; seen by everyone while we wait. */}
      <div aria-live="polite" className="mb-6">
        {checking ? (
          <div className="flex items-start gap-3 rounded-lg bg-muted px-5 py-4">
            <Loader2 className="mt-0.5 size-5 shrink-0 animate-spin text-primary" aria-hidden />
            <div>
              <p className="font-medium">
                {summarizeReview.checking(counts.total - counts.pending, counts.total)}
              </p>
              <p className="text-base text-muted-foreground">
                The first time we look a case up it can take about a minute. You can leave this page open, or come back
                later from My reviews.
              </p>
            </div>
          </div>
        ) : null}

        {counts.errors > 0 && !checking ? (
          <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-problem-wash px-5 py-4 text-problem">
            <p className="font-medium">
              {counts.errors === 1 ? "One case couldn't be checked right now." : `${counts.errors} cases couldn't be checked right now.`}
            </p>
            <Button variant="outline" size="sm" disabled={retry.isPending} onClick={() => retry.mutate(reviewId)}>
              <RotateCw data-icon="inline-start" aria-hidden />
              {retry.isPending ? 'Trying again…' : 'Try again'}
            </Button>
          </div>
        ) : null}
        {retry.isError ? <p role="alert" className="mt-2 text-sm text-problem">{friendlyError(retry.error)}</p> : null}
      </div>

      {citations.length === 0 ? (
        <EmptyState icon={FileQuestion} title="No cases found in this file" action={<Button asChild><Link to="/">Try another file</Link></Button>}>
          {summarizeReview.empty} We look for a G.R. number such as &ldquo;G.R. No. 180046&rdquo;. If your reviewer
          cites cases another way, add the G.R. number next to each one.
        </EmptyState>
      ) : (
        <div>
          {citations.map((citation) => (
            <CitationSection key={citation.id} citation={citation} uploadId={review.id} />
          ))}
        </div>
      )}

        </TabsContent>

        <TabsContent value="finished">
          <FinishedReviewer uploadId={reviewId} checking={checking} />
        </TabsContent>
      </Tabs>

      <Disclaimer className="mt-10 max-w-prose" />
    </>
  )
}
