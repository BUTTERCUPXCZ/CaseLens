import { Link } from '@tanstack/react-router'
import { ExternalLink } from 'lucide-react'

import type { Citation } from '@/api/types'
import { Button } from '@/components/ui/button'
import { explainCitation } from '@/lib/copy'
import { formatDate, shortCaseName } from '@/lib/format'

import { AttachLinkForm } from './AttachLinkForm'
import { buildCompareRows } from './compareRows'
import { CompareTable } from './CompareTable'
import { StatusBadge } from './StatusBadge'

/** One cited case: its name, how it checked out, and what you wrote beside the Court's record. */
export function CitationSection({ citation, uploadId }: { citation: Citation; uploadId: number }) {
  const official = citation.case
  const title = official ? shortCaseName(official.title) : (citation.claimed.title ?? `G.R. No. ${citation.gr_no}`)
  const explanation = explainCitation(citation.status, citation.message)
  const rows = buildCompareRows(citation)

  return (
    <article className="border-b border-border py-8 first:pt-0 last:border-b-0" aria-labelledby={`citation-${citation.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={`citation-${citation.id}`} className="font-serif text-xl leading-snug font-semibold md:text-2xl">
            {title}
          </h2>
          {official ? (
            <p className="tabular mt-1 text-base text-muted-foreground">
              G.R. No. {official.gr_no} &middot; {formatDate(official.decision_date)}
              {official.division ? <> &middot; {toDivision(official.division)}</> : null}
            </p>
          ) : null}
        </div>
        <StatusBadge status={citation.status} />
      </div>

      {explanation ? <p className="mt-4 max-w-prose text-base">{explanation}</p> : null}

      <div className="mt-5">
        <CompareTable rows={rows} hasRecord={Boolean(official)} />
      </div>

      {citation.status === 'not_found' ? <AttachLinkForm uploadId={uploadId} citationId={citation.id} /> : null}

      {official ? (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button asChild>
            <Link to="/cases/$caseId" params={{ caseId: String(official.id) }}>
              Read the case
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <a href={official.source_url} target="_blank" rel="noopener noreferrer">
              Open on Lawphil
              <ExternalLink data-icon="inline-end" aria-hidden />
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          </Button>
        </div>
      ) : null}
    </article>
  )
}

/** "EN BANC" -> "En Banc", "SECOND DIVISION" -> "Second Division". */
function toDivision(division: string): string {
  return division.toLowerCase().replace(/\b[a-z]/g, (letter) => letter.toUpperCase())
}
