import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, notFound } from '@tanstack/react-router'
import { ArrowLeft, ChevronLeft, ChevronRight, FileQuestion, Loader2, MessageCircleQuestion } from 'lucide-react'
import { useState } from 'react'
import { createPortal } from 'react-dom'
import { z } from 'zod'

import { orNotFound } from '@/api/orNotFound'
import { batchCasesQuery, bulkQuery, PAGE_SIZE } from '@/api/queries'
import type { Bulk, CaseSummary } from '@/api/types'
import { Disclaimer } from '@/components/Disclaimer'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { AssistantPanel } from '@/features/assistant/AssistantPanel'
import { CaseDigestPanel } from '@/features/digest/CaseDigestPanel'
import { NotAdded } from '@/features/reviews/NotAdded'
import { reviewTitle } from '@/features/reviews/reviewTitle'
import { useWideScreen } from '@/hooks/useWideScreen'
import { assistantCopy, bulkCopy, reviewsCopy } from '@/lib/copy'
import { RIGHT_DOCK_ID } from '@/lib/dock'
import { shortCaseName } from '@/lib/format'

const searchSchema = z.object({ case: z.coerce.number().int().optional().catch(undefined) })

export const Route = createFileRoute('/reviews/$batchId')({
  validateSearch: searchSchema,
  loader: async ({ context, params }) => {
    const id = Number(params.batchId)
    if (!Number.isInteger(id)) throw notFound()
    await orNotFound(context.queryClient.ensureQueryData(bulkQuery(id)))
  },
  pendingComponent: () => <Skeleton className="h-96 w-full" aria-busy="true" aria-label="Opening the review" />,
  errorComponent: ({ error, reset }) => <ErrorState error={error} onRetry={reset} title="The review didn't open" />,
  notFoundComponent: () => (
    <EmptyState icon={FileQuestion} title="We can't find that review" action={<Link to="/reviews" className="underline">{reviewsCopy.back}</Link>}>
      It may have been deleted.
    </EmptyState>
  ),
  component: ReviewPage,
})

function CaseList({ cases, selected, onSelect }: { cases: CaseSummary[]; selected: number | null; onSelect: (id: number) => void }) {
  return (
    <ul className="space-y-1">
      {cases.map((item) => {
        const on = item.id === selected
        return (
          <li key={item.id}>
            <button
              type="button"
              aria-current={on ? 'true' : undefined}
              onClick={() => onSelect(item.id)}
              className={[
                'w-full rounded-lg px-3 py-2.5 text-left transition-colors focus-visible:outline-2 focus-visible:outline-ring',
                on ? 'bg-accent' : 'hover:bg-muted',
              ].join(' ')}
            >
              <span className="block font-serif text-base leading-snug font-semibold">{shortCaseName(item.title)}</span>
              <span className="tabular block text-sm text-muted-foreground">G.R. No. {item.gr_no}</span>
              <span className={['mt-0.5 block text-xs font-medium', item.digest_state === 'ready' ? 'text-match' : item.digest_state === 'failed' ? 'text-problem' : 'text-muted-foreground'].join(' ')}>
                {reviewsCopy.digestStates[item.digest_state]}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

function Header({ bulk }: { bulk: Bulk }) {
  const c = bulk.counts
  return (
    <header className="mb-6">
      <Button variant="ghost" size="sm" asChild className="-ml-3 mb-3">
        <Link to="/reviews">
          <ArrowLeft data-icon="inline-start" aria-hidden />
          {reviewsCopy.back}
        </Link>
      </Button>
      <h1 className="font-serif text-2xl leading-tight font-semibold md:text-3xl">{reviewTitle(bulk)}</h1>
      <p className="mt-1 text-base text-muted-foreground">{bulk.topic_scope ? reviewsCopy.scope(bulk.topic_scope) : reviewsCopy.noScope}</p>
      {bulk.subjects.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Subject tags">
          {bulk.subjects.map((s) => (
            <li key={s.id} className="rounded-full border border-border px-2.5 py-0.5 text-sm">
              {s.name}
            </li>
          ))}
        </ul>
      ) : null}
      <p role="status" className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
        {!bulk.finished || c.digests_pending > 0 ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
        {bulkCopy.total(c.total)} · {reviewsCopy.cases(c.found, c.digests_ready)}
        {!bulk.finished ? ` · ${reviewsCopy.working}` : ''}
      </p>
    </header>
  )
}

/** One review: the cases of an upload on the left, the selected case's digest (for the upload's topic scope) in the middle,
 *  and the AI assistant on the right (docked on a wide screen, a sheet on a smaller one). */
function ReviewPage() {
  const batchId = Number(Route.useParams().batchId)
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const wide = useWideScreen()
  const [page, setPage] = useState(0)
  const [sheetOpen, setSheetOpen] = useState(false)
  const { data: bulk } = useQuery(bulkQuery(batchId))
  const live = bulk ? !bulk.finished || bulk.counts.digests_pending > 0 : true
  const cases = useQuery(batchCasesQuery(batchId, page, live))

  if (!bulk) return null
  const items = cases.data?.items ?? []
  const selected = items.find((c) => c.id === search.case) ?? items[0] ?? null
  const total = cases.data?.total ?? 0
  const last = Math.min((page + 1) * PAGE_SIZE, total)
  const assistant = <AssistantPanel caseId={selected?.id ?? null} caseName={selected ? shortCaseName(selected.title) : null} batchId={batchId} />
  const dock = typeof document !== 'undefined' ? document.getElementById(RIGHT_DOCK_ID) : null

  return (
    <>
      <Header bulk={bulk} />
      <div className="grid gap-8 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <nav aria-label={reviewsCopy.casesTitle} className="space-y-6">
          <div>
            <h2 className="mb-2 text-sm font-semibold tracking-wide text-muted-foreground uppercase">{reviewsCopy.casesTitle}</h2>
            {!cases.data ? (
              <Skeleton className="h-24 w-full" aria-label="Loading the cases" />
            ) : total === 0 ? (
              <p className="text-base text-muted-foreground">{bulk.finished ? reviewsCopy.nothingAdded : reviewsCopy.waitingFirst}</p>
            ) : (
              <CaseList cases={items} selected={selected?.id ?? null} onSelect={(id) => void navigate({ search: { case: id }, replace: true })} />
            )}
            {total > PAGE_SIZE ? (
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="tabular text-xs text-muted-foreground">{reviewsCopy.page(page * PAGE_SIZE + 1, last, total)}</span>
                <span className="flex gap-1">
                  <Button size="icon" variant="ghost" aria-label="Earlier cases" disabled={page === 0} onClick={() => setPage(page - 1)}>
                    <ChevronLeft aria-hidden />
                  </Button>
                  <Button size="icon" variant="ghost" aria-label="Later cases" disabled={last >= total} onClick={() => setPage(page + 1)}>
                    <ChevronRight aria-hidden />
                  </Button>
                </span>
              </div>
            ) : null}
          </div>
          <NotAdded bulk={bulk} />
        </nav>

        <div className="min-w-0">
          {selected ? (
            <>
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link to="/cases/$caseId/decision" params={{ caseId: String(selected.id) }}>
                    {reviewsCopy.fullText}
                  </Link>
                </Button>
                {!wide ? (
                  <Button size="sm" onClick={() => setSheetOpen(true)}>
                    <MessageCircleQuestion data-icon="inline-start" aria-hidden />
                    {assistantCopy.open}
                  </Button>
                ) : null}
              </div>
              <CaseDigestPanel key={`${selected.id}|${bulk.topic_scope}`} caseId={selected.id} scope={bulk.topic_scope} batchId={batchId} />
              <Disclaimer className="mt-10 max-w-prose" />
            </>
          ) : (
            <p className="text-base text-muted-foreground">{total === 0 ? '' : reviewsCopy.pickCase}</p>
          )}
        </div>
      </div>

      {wide && dock ? createPortal(assistant, dock) : null}
      {!wide ? (
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetContent side="right" className="w-full p-0 sm:max-w-md">
            <SheetTitle className="sr-only">{assistantCopy.title}</SheetTitle>
            {assistant}
          </SheetContent>
        </Sheet>
      ) : null}
    </>
  )
}
