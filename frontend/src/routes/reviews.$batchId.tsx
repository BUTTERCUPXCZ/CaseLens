import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, Link, notFound } from '@tanstack/react-router'
import { ChevronLeft, ChevronRight, FileQuestion, FileText, MessageCircleQuestion } from 'lucide-react'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { z } from 'zod'

import { orNotFound } from '@/api/orNotFound'
import { batchCasesQuery, bulkQuery, PAGE_SIZE } from '@/api/queries'
import type { BatchDigestFilter, Bulk, CaseSummary } from '@/api/types'
import { BackButton } from '@/components/BackButton'
import { Disclaimer } from '@/components/Disclaimer'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { AssistantPanel } from '@/features/assistant/AssistantPanel'
import { CaseDigestPanel } from '@/features/digest/CaseDigestPanel'
import { NotAdded } from '@/features/reviews/NotAdded'
import { reviewTitle } from '@/features/reviews/reviewTitle'
import { TONE_CLASS, uploadState } from '@/features/reviews/uploadState'
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from '@/components/ui/breadcrumb'
import { useWideScreen } from '@/hooks/useWideScreen'
import { assistantCopy, bulkCopy, decisionCopy, reviewsCopy } from '@/lib/copy'
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
  pendingComponent: () => <Skeleton className="h-96 w-full" aria-busy="true" aria-label="Opening the upload" />,
  errorComponent: ({ error, reset }) => <ErrorState error={error} onRetry={reset} title="The upload didn't open" />,
  notFoundComponent: () => (
    <EmptyState
      icon={FileQuestion}
      title="We can't find that upload"
      action={
        <Link to="/library" search={{ tab: 'uploads' }} className="underline">
          {reviewsCopy.tabUploads}
        </Link>
      }
    >
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

const FILTERS = ['all', 'ready', 'writing', 'failed'] as const
type Filter = (typeof FILTERS)[number]

/** "All · Ready · Being written": with many cases, the ready ones are one click away while the rest are still being written. */
function CaseFilter({ value, counts, total, onChange }: { value: Filter; counts: Record<string, number>; total: number; onChange: (next: Filter) => void }) {
  const count = (filter: Filter) => (filter === 'all' ? total : (counts[filter] ?? 0))
  return (
    <div role="group" aria-label={reviewsCopy.filterLabel} className="mb-3 flex flex-wrap gap-1.5">
      {FILTERS.filter((f) => f !== 'failed' || count(f) > 0 || value === f).map((filter) => {
        const on = value === filter
        return (
          <button
            key={filter}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(filter)}
            className={[
              'rounded-full border px-2.5 py-0.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-ring',
              on ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-muted',
            ].join(' ')}
          >
            {reviewsCopy.filters[filter]} <span className="tabular">{count(filter)}</span>
          </button>
        )
      })}
    </div>
  )
}

function Header({ bulk }: { bulk: Bulk }) {
  const c = bulk.counts
  const title = reviewTitle(bulk)
  const state = uploadState(bulk)
  return (
    <header className="mb-6">
      <BackButton fallback="uploads" />
      <Breadcrumb className="mb-3">
        <BreadcrumbList className="text-base">
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/library" search={{ tab: 'cases' }}>
                {reviewsCopy.crumbLibrary}
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/library" search={{ tab: 'uploads' }}>
                {reviewsCopy.tabUploads}
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem className="min-w-0">
            <BreadcrumbPage className="truncate">{title}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="font-serif text-2xl leading-tight font-semibold md:text-3xl">{title}</h1>
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
      <p role="status" className={`mt-3 flex items-center gap-2 text-base font-medium ${TONE_CLASS[state.tone]}`}>
        <state.icon className={`size-4 shrink-0 ${state.busy ? 'animate-spin' : ''}`} aria-hidden />
        {state.label}
      </p>
      <p className="mt-0.5 text-sm text-muted-foreground">
        {bulkCopy.total(c.total)} · {reviewsCopy.cases(c.found, c.digests_ready)}
      </p>
      {/* While digests are written: how far along, so the student knows they can start on the ready ones. */}
      {c.found > 1 && c.digests_ready < c.found && (c.digests_pending > 0 || !bulk.finished) ? (
        <div className="mt-4 max-w-md">
          <p className="tabular mb-1.5 text-sm font-medium">{reviewsCopy.progress(c.digests_ready, c.found)}</p>
          <Progress value={(100 * c.digests_ready) / c.found} aria-label={reviewsCopy.progress(c.digests_ready, c.found)} className="h-1.5" />
          <p className="mt-1.5 text-sm text-muted-foreground">{reviewsCopy.progressHelp}</p>
        </div>
      ) : null}
    </header>
  )
}

/** One upload: its cases on the left, the selected case's digest (for the upload's topic scope) in the middle,
 *  and the AI assistant on the right (docked on a wide screen, a sheet on a smaller one). */
function ReviewPage() {
  const batchId = Number(Route.useParams().batchId)
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const wide = useWideScreen()
  const [page, setPage] = useState(0)
  const [filter, setFilter] = useState<Filter>('all')
  const [sheetOpen, setSheetOpen] = useState(false)
  const { data: bulk } = useQuery(bulkQuery(batchId))
  const live = bulk ? !bulk.finished || bulk.counts.digests_pending > 0 : true
  const cases = useQuery(batchCasesQuery(batchId, page, live, filter === 'all' ? undefined : (filter as BatchDigestFilter)))
  const queryClient = useQueryClient()
  const found = bulk?.counts.found
  const ready = bulk?.counts.digests_ready

  // An upload can finish between two refreshes (a case already in the library, its digest already written): whenever the counts move,
  // read the list of cases again, so it never stops on an old, empty answer.
  useEffect(() => {
    if (found === undefined) return
    void queryClient.invalidateQueries({ queryKey: ['library', 'batch', batchId] })
  }, [found, ready, batchId, queryClient])

  if (!bulk) return null
  const items = cases.data?.items ?? []
  // The case the student picked; until they pick one, the first READY case (the first case may still be being written).
  const selected = items.find((c) => c.id === search.case) ?? items.find((c) => c.digest_state === 'ready') ?? items[0] ?? null
  const total = cases.data?.total ?? 0
  const last = Math.min((page + 1) * PAGE_SIZE, total)
  const assistant = <AssistantPanel caseId={selected?.id ?? null} caseName={selected ? shortCaseName(selected.title) : null} batchId={batchId} />
  const dock = typeof document !== 'undefined' ? document.getElementById(RIGHT_DOCK_ID) : null

  return (
    <>
      <Header bulk={bulk} />
      <div className="grid gap-8 xl:grid-cols-[15rem_minmax(0,1fr)]">
        <nav aria-label={reviewsCopy.casesTitle} className="space-y-6">
          <div>
            <h2 className="mb-2 text-sm font-semibold tracking-wide text-muted-foreground uppercase">{reviewsCopy.casesTitle}</h2>
            {cases.data?.state_counts && (bulk.counts.found > 1 || filter !== 'all') ? (
              <CaseFilter
                value={filter}
                counts={cases.data.state_counts}
                total={Object.values(cases.data.state_counts).reduce((sum, n) => sum + n, 0)}
                onChange={(next) => {
                  setFilter(next)
                  setPage(0)
                }}
              />
            ) : null}
            {!cases.data ? (
              <Skeleton className="h-24 w-full" aria-label="Loading the cases" />
            ) : total === 0 && filter !== 'all' ? (
              <p className="text-base text-muted-foreground">{reviewsCopy.filterEmpty[filter]}</p>
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
                {/* Individual is for reading the case: its full text comes first. */}
                <Button variant={bulk.kind === 'individual' ? 'default' : 'outline'} size={bulk.kind === 'individual' ? 'lg' : 'sm'} asChild>
                  <Link to="/cases/$caseId/decision" params={{ caseId: String(selected.id) }}>
                    <FileText data-icon="inline-start" aria-hidden />
                    {bulk.kind === 'individual' ? decisionCopy.read : reviewsCopy.fullText}
                  </Link>
                </Button>
              </div>
              <CaseDigestPanel key={`${selected.id}|${bulk.topic_scope}`} caseId={selected.id} scope={bulk.topic_scope} batchId={batchId} />
              <Disclaimer className={`mt-10 max-w-prose ${wide ? '' : 'mb-20'}`} />{/* room under it for the floating assistant button */}
            </>
          ) : (
            <p className="text-base text-muted-foreground">{total === 0 ? '' : reviewsCopy.pickCase}</p>
          )}
        </div>
      </div>

      {wide && dock ? createPortal(assistant, dock) : null}
      {/* In a smaller window the assistant is one tap away wherever the student has scrolled to: a button that floats in the corner. */}
      {!wide && selected && !sheetOpen ? (
        <Button size="lg" className="fixed right-6 bottom-6 z-40 rounded-full shadow-lg" onClick={() => setSheetOpen(true)}>
          <MessageCircleQuestion data-icon="inline-start" aria-hidden />
          {assistantCopy.open}
        </Button>
      ) : null}
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
