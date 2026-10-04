import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { ChevronLeft, ChevronRight, Library, SearchX } from 'lucide-react'
import { useEffect, useState } from 'react'
import { z } from 'zod'

import { libraryQuery, PAGE_SIZE } from '@/api/queries'
import { PageHeader } from '@/components/PageHeader'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { CasesTable } from '@/features/cases/CasesTable'

const searchSchema = z.object({
  q: z.string().optional().catch(undefined),
  page: z.coerce.number().int().min(0).optional().catch(undefined),
})

export const Route = createFileRoute('/cases/')({
  validateSearch: searchSchema,
  component: Library_,
})

function Library_() {
  const search = Route.useSearch()
  const q = search.q ?? ''
  const page = search.page ?? 0
  const navigate = Route.useNavigate()
  const [draft, setDraft] = useState(q)
  const { data, error, isPending, isPlaceholderData, refetch } = useQuery(libraryQuery(q, page))

  // Search as the student types, but only ask the server once they pause.
  useEffect(() => {
    if (draft === q) return
    const timer = setTimeout(() => void navigate({ search: { q: draft, page: 0 }, replace: true }), 300)
    return () => clearTimeout(timer)
  }, [draft, q, navigate])

  const total = data?.total ?? 0
  const first = total === 0 ? 0 : page * PAGE_SIZE + 1
  const last = Math.min((page + 1) * PAGE_SIZE, total)

  return (
    <>
      <PageHeader
        title="Case library"
        description="Every case you've looked up is saved here, so you can read it again without searching."
      />

      <div className="mb-6 max-w-md">
        <label htmlFor="library-search" className="mb-1.5 block text-sm font-medium">
          Search your saved cases
        </label>
        <Input
          id="library-search"
          type="search"
          placeholder="Part of the case name, or a G.R. number"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
      </div>

      {isPending ? (
        <div className="space-y-4" aria-busy="true" aria-label="Loading the library">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} title="The library didn't load" />
      ) : data.total === 0 && q === '' ? (
        <EmptyState icon={Library} title="Your library is empty" action={<Button asChild><Link to="/">Check a reviewer</Link></Button>}>
          Cases are saved here automatically when you check a reviewer or look one up by its G.R. number.
        </EmptyState>
      ) : data.total === 0 ? (
        <EmptyState icon={SearchX} title={`No saved case matches "${q}"`} action={<Button variant="outline" onClick={() => setDraft('')}>Clear the search</Button>}>
          Try part of the case name, or the first digits of the G.R. number. Cases you haven't looked up yet aren't in the library.
        </EmptyState>
      ) : (
        <div className={isPlaceholderData ? 'opacity-60 transition-opacity' : undefined} aria-busy={isPlaceholderData}>
          <CasesTable cases={data.items} />

          <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-4">
            <p className="tabular text-sm text-muted-foreground" aria-live="polite">
              Showing {first}&ndash;{last} of {total}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => void navigate({ search: (prev) => ({ ...prev, page: page - 1 }) })}>
                <ChevronLeft data-icon="inline-start" aria-hidden /> Earlier
              </Button>
              <Button variant="outline" size="sm" disabled={last >= total} onClick={() => void navigate({ search: (prev) => ({ ...prev, page: page + 1 }) })}>
                Later <ChevronRight data-icon="inline-end" aria-hidden />
              </Button>
            </div>
          </nav>
        </div>
      )}
    </>
  )
}
