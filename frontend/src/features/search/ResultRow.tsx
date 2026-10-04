import { useNavigate } from '@tanstack/react-router'
import { ExternalLink } from 'lucide-react'
import { Link } from '@tanstack/react-router'

import { useFetchByLink } from '@/api/mutations'
import type { CatalogItem } from '@/api/types'
import { Button } from '@/components/ui/button'
import { friendlyError, searchCopy } from '@/lib/copy'
import { formatDate } from '@/lib/format'

/** One decision on Lawphil's list. The title is shown exactly as Lawphil prints it (typos and all),
 *  because this row is Lawphil's, not ours; the case page after opening has the full decision. */
export function ResultRow({ item }: { item: CatalogItem }) {
  const navigate = useNavigate()
  const open = useFetchByLink()

  return (
    <li className="py-5">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0 flex-1 basis-80">
          <p className="line-clamp-3 font-serif text-lg leading-snug font-semibold">{item.title}</p>
          <p className="tabular mt-1 text-base text-muted-foreground">
            G.R. No. {item.gr_no} &middot; {formatDate(item.decision_date)}
          </p>
          {item.also_decided_with.length > 0 ? (
            <p className="mt-0.5 text-sm text-muted-foreground">{searchCopy.alsoDecidedWith(item.also_decided_with)}</p>
          ) : null}
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {item.in_library && item.case_id !== null ? (
            <>
              <span className="text-sm font-medium text-match">{searchCopy.inLibrary}</span>
              <Button asChild>
                <Link to="/cases/$caseId" params={{ caseId: String(item.case_id) }}>
                  {searchCopy.readAction}
                </Link>
              </Button>
            </>
          ) : (
            <Button
              disabled={open.isPending}
              onClick={() =>
                open.mutate(item.source_url, {
                  onSuccess: (saved) => void navigate({ to: '/cases/$caseId', params: { caseId: String(saved.id) } }),
                })
              }
            >
              {open.isPending ? searchCopy.opening : searchCopy.openAction}
            </Button>
          )}
          <Button variant="outline" asChild>
            <a href={item.source_url} target="_blank" rel="noopener noreferrer">
              Lawphil
              <ExternalLink data-icon="inline-end" aria-hidden />
              <span className="sr-only"> (opens the decision on Lawphil in a new tab)</span>
            </a>
          </Button>
        </div>
      </div>
      {open.isError ? (
        <p role="alert" className="mt-2 text-sm text-problem">
          {friendlyError(open.error)}
        </p>
      ) : null}
    </li>
  )
}
