import { createFileRoute } from '@tanstack/react-router'
import { z } from 'zod'

import { PageHeader } from '@/components/PageHeader'
import { EmptyState } from '@/components/States'
import { SearchResults } from '@/features/search/SearchResults'
import { searchCopy } from '@/lib/copy'
import { SearchX } from 'lucide-react'

// The router's URL parser turns "?q=14744" into the NUMBER 14744, so a G.R. number typed into the
// address bar would be dropped by a plain z.string(). Accept both and keep the text.
const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).transform(String).optional().catch(undefined),
  year: z.coerce.number().int().optional().catch(undefined),
  page: z.coerce.number().int().min(0).optional().catch(undefined),
})

export const Route = createFileRoute('/search')({
  validateSearch: searchSchema,
  component: Search,
})

function Search() {
  const { q = '', year, page = 0 } = Route.useSearch()
  const navigate = Route.useNavigate()

  if (q.trim() === '') {
    return (
      <EmptyState icon={SearchX} title={searchCopy.needSomething}>
        Searching covers every decision on Lawphil's list from 1987 on.
      </EmptyState>
    )
  }
  return (
    <>
      <PageHeader
        title={`Search: ${q}`}
        description="Decisions from Lawphil's own list. Open one to save the full case, with its footnotes, to your library."
      />
      <SearchResults
        q={q}
        year={year}
        page={page}
        onPage={(next) => void navigate({ search: (prev) => ({ ...prev, page: next || undefined }) })}
      />
    </>
  )
}
