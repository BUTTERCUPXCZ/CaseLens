import { useQuery } from '@tanstack/react-query'
import { Loader2, Search, Sparkles } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { useStartBulk } from '@/api/mutations'
import { catalogSearchQuery } from '@/api/queries'
import type { CatalogItem } from '@/api/types'
import { ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { friendlyError, searchCopy, uploadCopy } from '@/lib/copy'
import { formatDate } from '@/lib/format'

import { SubjectTags } from './SubjectTags'
import { TopicScope } from './TopicScope'

/** "Search cases": find a decision on Lawphil's list, then generate its digest with the same tags and topic scope as an upload. */
export function SearchCasesPanel({ onStarted }: { onStarted: (batchId: number) => void }) {
  const [draft, setDraft] = useState('')
  const [q, setQ] = useState('')
  const [tags, setTags] = useState<number[]>([])
  const [scope, setScope] = useState('')
  const [picked, setPicked] = useState<string | null>(null)
  const results = useQuery({ ...catalogSearchQuery(q, undefined, 0), enabled: q.length >= 2 })
  const start = useStartBulk()

  const search = (event: FormEvent) => {
    event.preventDefault()
    setQ(draft.trim())
  }
  const generate = (item: CatalogItem) => {
    setPicked(item.source_url)
    const year = item.decision_date ? ` (${item.decision_date.slice(0, 4)})` : ''
    start.mutate({ text: `${item.gr_no}${year}`, subjectIds: tags, topicScope: scope.trim(), files: [] }, { onSuccess: (batch) => onStarted(batch.id) })
  }

  return (
    <div className="space-y-6">
      <form onSubmit={search} role="search" className="flex flex-wrap items-end gap-2">
        <div className="min-w-0 flex-1 basis-64">
          <label htmlFor="search-cases" className="mb-1 block text-sm font-medium">
            {searchCopy.boxLabel}
          </label>
          <Input id="search-cases" value={draft} placeholder={searchCopy.boxPlaceholder} onChange={(event) => setDraft(event.target.value)} />
        </div>
        <Button type="submit">
          <Search data-icon="inline-start" aria-hidden />
          Search
        </Button>
      </form>
      <p className="text-sm text-muted-foreground">{uploadCopy.searchHelp}</p>

      <div className="space-y-6 rounded-xl border border-border bg-card px-5 py-5">
        <SubjectTags id="search-tags" value={tags} onChange={setTags} disabled={start.isPending} />
        <TopicScope id="search-scope" value={scope} onChange={setScope} disabled={start.isPending} />
      </div>

      {q.length < 2 ? null : results.isPending ? (
        <Skeleton className="h-32 w-full" aria-busy="true" aria-label="Searching Lawphil's list" />
      ) : results.error ? (
        <ErrorState error={results.error} onRetry={() => void results.refetch()} title="The search didn't work" />
      ) : results.data.items.length === 0 ? (
        <p className="text-base text-muted-foreground">{searchCopy.noMatchName(q)} {searchCopy.noMatchNameHelp}</p>
      ) : (
        <ul className="divide-y divide-border border-y border-border" aria-label="Matching decisions">
          {results.data.items.map((item) => (
            <li key={item.source_url} className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 py-4">
              <div className="min-w-0 flex-1 basis-72">
                <p className="line-clamp-3 font-serif text-lg leading-snug font-semibold">{item.title}</p>
                <p className="tabular mt-1 text-base text-muted-foreground">
                  G.R. No. {item.gr_no} &middot; {formatDate(item.decision_date)}
                </p>
              </div>
              <Button disabled={start.isPending} onClick={() => generate(item)} aria-label={`${uploadCopy.generateOne}: ${item.title}`}>
                {start.isPending && picked === item.source_url ? <Loader2 data-icon="inline-start" className="animate-spin" aria-hidden /> : <Sparkles data-icon="inline-start" aria-hidden />}
                {start.isPending && picked === item.source_url ? uploadCopy.generating : uploadCopy.generateOne}
              </Button>
            </li>
          ))}
        </ul>
      )}
      {start.isError ? <p role="alert" className="text-base text-problem">{friendlyError(start.error)}</p> : null}
    </div>
  )
}
