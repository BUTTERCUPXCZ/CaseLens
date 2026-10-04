import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ChevronLeft, ChevronRight, SearchX } from 'lucide-react'

import { CATALOG_PAGE_SIZE, catalogSearchQuery } from '@/api/queries'
import type { CatalogSearch } from '@/api/types'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { searchCopy } from '@/lib/copy'

import { parseGrNumber } from './grNumber'
import { ListProgress } from './ListProgress'
import { PasteLink } from './PasteLink'
import { ResultRow } from './ResultRow'

const quoted = (q: string, year: number | undefined) => `"${q}"${year ? ` in ${year}` : ''}`

/** Does any row carry exactly the number the student typed? ("1800" finds 180046 by prefix.) */
function hasExactNumber(data: CatalogSearch, typed: string): boolean {
  const wanted = parseGrNumber(typed)
  if (!wanted) return true
  const spellings = /^\d+$/.test(wanted) ? [wanted, `L-${wanted}`] : [wanted]
  return data.items.some((item) => item.numbers.some((number) => spellings.includes(number)))
}

export function SearchResults({
  q,
  year,
  page,
  onPage,
}: {
  q: string
  year: number | undefined
  page: number
  onPage: (next: number) => void
}) {
  const { data, error, isPending, isPlaceholderData, refetch } = useQuery(catalogSearchQuery(q, year, page))

  if (isPending) {
    return (
      <div className="space-y-5" aria-busy="true" aria-label="Searching Lawphil's list">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    )
  }
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} title="The search didn't work" />

  const typedNumber = parseGrNumber(q)
  const total = data.total
  const first = total === 0 ? 0 : page * CATALOG_PAGE_SIZE + 1
  const last = Math.min((page + 1) * CATALOG_PAGE_SIZE, total)
  const ready = data.catalog.state === 'ready'

  return (
    <>
      <ListProgress status={data.catalog} />

      {total === 0 ? (
        <NoResults data={data} q={q} year={year} typedNumber={typedNumber} ready={ready} />
      ) : (
        <div className={isPlaceholderData ? 'opacity-60 transition-opacity' : undefined} aria-busy={isPlaceholderData}>
          <p className="mb-2 text-base text-muted-foreground" aria-live="polite">
            {searchCopy.results(total, quoted(q, year))}
          </p>
          {typedNumber && !hasExactNumber(data, q) ? (
            <p className="mb-2 text-base font-medium">{searchCopy.noExactNumber(typedNumber.replace(/^L-/, ''))}</p>
          ) : null}
          <p className="mb-1 text-sm text-muted-foreground">{searchCopy.openHint}</p>

          <ul className="divide-y divide-border border-y border-border">
            {data.items.map((item) => (
              <ResultRow key={`${item.source_url}|${item.numbers.join(' ')}`} item={item} />
            ))}
          </ul>

          <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-4">
            <p className="tabular text-sm text-muted-foreground" aria-live="polite">
              Showing {first.toLocaleString('en-PH')}&ndash;{last.toLocaleString('en-PH')} of {total.toLocaleString('en-PH')}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => onPage(page - 1)}>
                <ChevronLeft data-icon="inline-start" aria-hidden /> Earlier
              </Button>
              <Button variant="outline" size="sm" disabled={last >= total} onClick={() => onPage(page + 1)}>
                Later <ChevronRight data-icon="inline-end" aria-hidden />
              </Button>
            </div>
          </nav>
        </div>
      )}
    </>
  )
}

function NoResults({
  data,
  q,
  year,
  typedNumber,
  ready,
}: {
  data: CatalogSearch
  q: string
  year: number | undefined
  typedNumber: string | null
  ready: boolean
}) {
  // The list is still being read: an empty answer may only mean "not read yet", so do not
  // claim the case does not exist.
  if (!ready && data.catalog.entries === 0) {
    return <EmptyState icon={SearchX} title={searchCopy.notReadyEmpty} />
  }

  if (typedNumber) {
    const shown = typedNumber.replace(/^L-/, '')
    return (
      <div className="max-w-2xl">
        <h2 className="text-lg font-semibold">{searchCopy.noMatchNumber(shown)}</h2>
        <p className="mt-2 text-base text-muted-foreground">{searchCopy.noMatchNumberHelp}</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button asChild variant="outline">
            <Link to="/lookup" search={{ gr_no: typedNumber, year }}>
              {searchCopy.lookUpWithYear}
              {year ? ` ${year}` : ''}
            </Link>
          </Button>
        </div>
        <PasteLink />
      </div>
    )
  }

  return (
    <EmptyState icon={SearchX} title={searchCopy.noMatchName(q)}>
      {searchCopy.noMatchNameHelp}
    </EmptyState>
  )
}
