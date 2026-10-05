import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'

import { catalogSearchQuery } from '@/api/queries'
import { Skeleton } from '@/components/ui/skeleton'
import { ResultRow } from '@/features/search/ResultRow'
import { libraryCopy } from '@/lib/copy'

const SHOWN = 8

/** What the student typed, found on Lawphil's own list but not saved yet. The library keeps only the cases someone used;
 *  this is how any other decision is found and, with one press, saved. Saved ones are already in the table above. */
export function LawphilMatches({ q }: { q: string }) {
  const { data, isPending, error } = useQuery({ ...catalogSearchQuery(q, undefined, 0), enabled: q.trim().length >= 2 })
  if (error) return null // the saved cases above still work; the full search page explains a failure
  if (isPending) return <Skeleton className="mt-8 h-24 w-full" aria-busy="true" aria-label="Searching Lawphil's list" />

  const unsaved = data.items.filter((item) => !item.in_library)
  return (
    <section aria-label={libraryCopy.lawphilTitle} className="mt-10 border-t border-border pt-6">
      <h2 className="text-xl font-semibold">{libraryCopy.lawphilTitle}</h2>
      {unsaved.length === 0 ? (
        <p className="mt-2 text-base text-muted-foreground">{libraryCopy.lawphilNone}</p>
      ) : (
        <>
          <p className="mt-1 text-base text-muted-foreground">{libraryCopy.lawphilHelp}</p>
          <ul className="mt-2 divide-y divide-border">
            {unsaved.slice(0, SHOWN).map((item) => (
              <ResultRow key={item.source_url} item={item} />
            ))}
          </ul>
          {data.total > SHOWN ? (
            <p className="mt-3 text-base">
              <Link to="/search" search={{ q }} className="text-primary underline underline-offset-4">
                {libraryCopy.lawphilMore(data.total)}
              </Link>
            </p>
          ) : null}
        </>
      )}
    </section>
  )
}
