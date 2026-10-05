import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, redirect } from '@tanstack/react-router'
import { ChevronLeft, ChevronRight, Library, SearchX } from 'lucide-react'
import { useEffect, useState } from 'react'
import { z } from 'zod'

import { libraryQuery, PAGE_SIZE, subjectCountsQuery, type SubjectFilter } from '@/api/queries'
import { PageHeader } from '@/components/PageHeader'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { LawphilMatches } from '@/features/library/LawphilMatches'
import { LibraryTable } from '@/features/library/LibraryTable'
import { SubjectRail } from '@/features/library/SubjectRail'
import { libraryCopy, uploadCopy } from '@/lib/copy'

const searchSchema = z.object({
  q: z.string().optional().catch(undefined),
  subject: z.union([z.literal('none'), z.coerce.number().int()]).optional().catch(undefined),
  page: z.coerce.number().int().min(0).optional().catch(undefined),
  // old addresses from before "New digest" and "My reviews" existed: sent on to their new place
  mode: z.enum(['individual', 'bulk']).optional().catch(undefined),
  batch: z.coerce.number().int().optional().catch(undefined),
})

export const Route = createFileRoute('/library')({
  validateSearch: searchSchema,
  beforeLoad: ({ search }) => {
    if (search.batch !== undefined) throw redirect({ to: '/reviews/$batchId', params: { batchId: String(search.batch) } })
    if (search.mode === 'individual') throw redirect({ to: '/upload', search: { tab: 'search' } })
    if (search.mode === 'bulk') throw redirect({ to: '/upload', search: {} })
  },
  component: LibraryPage,
})

/** The client's drawing on one page: Individual and Bulk on top, the subject filter on the left, the table of cases on the right. */
function LibraryPage() {
  const search = Route.useSearch()
  const q = search.q ?? ''
  const page = search.page ?? 0
  const subject: SubjectFilter = search.subject
  const navigate = Route.useNavigate()
  const [draft, setDraft] = useState(q)
  const { data, error, isPending, isPlaceholderData, refetch } = useQuery(libraryQuery(q, page, subject))
  const counts = useQuery(subjectCountsQuery())

  // Search as the student types, but only ask the server once they pause.
  useEffect(() => {
    if (draft === q) return
    const timer = setTimeout(() => void navigate({ search: (prev) => ({ ...prev, q: draft || undefined, page: undefined }), replace: true }), 300)
    return () => clearTimeout(timer)
  }, [draft, q, navigate])

  const total = data?.total ?? 0
  const first = total === 0 ? 0 : page * PAGE_SIZE + 1
  const last = Math.min((page + 1) * PAGE_SIZE, total)
  const pick = (next: SubjectFilter) => void navigate({ search: (prev) => ({ ...prev, subject: next, page: undefined }) })

  return (
    <>
      <PageHeader title={libraryCopy.title} description={libraryCopy.description} />

      <div className="grid gap-8 md:grid-cols-[14rem_minmax(0,1fr)]">
        <aside>{counts.data ? <SubjectRail counts={counts.data} selected={subject} onSelect={pick} /> : <Skeleton className="h-40 w-full" aria-label="Loading the subjects" />}</aside>

        <div className="min-w-0">
          <div className="mb-6 max-w-md">
            <label htmlFor="library-search" className="mb-1.5 block text-sm font-medium">
              {libraryCopy.searchLabel}
            </label>
            <Input id="library-search" type="search" placeholder={libraryCopy.searchPlaceholder} value={draft} onChange={(event) => setDraft(event.target.value)} />
          </div>

          {isPending ? (
            <div className="space-y-4" aria-busy="true" aria-label="Loading the library">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : error ? (
            <ErrorState error={error} onRetry={() => void refetch()} title="The library didn't load" />
          ) : data.total === 0 && q === '' ? (
            <EmptyState icon={Library} title={subject === undefined ? libraryCopy.emptyTitle : libraryCopy.emptySubject} action={<Button asChild><Link to="/upload">{uploadCopy.title}</Link></Button>}>
              {libraryCopy.emptyBody}
            </EmptyState>
          ) : data.total === 0 ? (
            <EmptyState icon={SearchX} title={libraryCopy.noMatch(q)} action={<Button variant="outline" onClick={() => setDraft('')}>Clear the search</Button>}>
              Try part of the case name, or the first digits of the G.R. number.
            </EmptyState>
          ) : (
            <div className={isPlaceholderData ? 'opacity-60 transition-opacity' : undefined} aria-busy={isPlaceholderData}>
              <LibraryTable cases={data.items} />
              <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-4">
                <p className="tabular text-sm text-muted-foreground" aria-live="polite">
                  Showing {first}&ndash;{last} of {total}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" disabled={page === 0} onClick={() => void navigate({ search: (prev) => ({ ...prev, page: page - 1 || undefined }) })}>
                    <ChevronLeft data-icon="inline-start" aria-hidden /> Earlier
                  </Button>
                  <Button variant="outline" size="sm" disabled={last >= total} onClick={() => void navigate({ search: (prev) => ({ ...prev, page: page + 1 }) })}>
                    Later <ChevronRight data-icon="inline-end" aria-hidden />
                  </Button>
                </div>
              </nav>
            </div>
          )}
          {q.trim().length >= 2 && subject === undefined ? <LawphilMatches q={q} /> : null}
        </div>
      </div>
    </>
  )
}
