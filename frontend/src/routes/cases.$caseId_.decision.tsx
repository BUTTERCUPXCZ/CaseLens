import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, notFound } from '@tanstack/react-router'
import { ArrowLeft, Download, ExternalLink, FileQuestion } from 'lucide-react'

import { orNotFound } from '@/api/orNotFound'
import { caseDownloadUrl } from '@/api/endpoints'
import { caseQuery } from '@/api/queries'
import { Disclaimer } from '@/components/Disclaimer'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { OfficialText } from '@/features/cases/OfficialText'
import { caseDownloadCopy, decisionCopy } from '@/lib/copy'
import { justiceName, shortCaseName } from '@/lib/format'

export const Route = createFileRoute('/cases/$caseId_/decision')({
  loader: async ({ context, params }) => {
    const id = Number(params.caseId)
    if (!Number.isInteger(id)) throw notFound()
    await orNotFound(context.queryClient.ensureQueryData(caseQuery(id)))
  },
  pendingComponent: () => (
    <div aria-busy="true" aria-label={decisionCopy.opening} className="space-y-4">
      <Skeleton className="h-10 w-3/4" />
      <Skeleton className="h-96 w-full" />
    </div>
  ),
  errorComponent: ({ error, reset }) => <ErrorState error={error} onRetry={reset} title={decisionCopy.failed} />,
  notFoundComponent: () => (
    <EmptyState icon={FileQuestion} title={decisionCopy.missing} action={<Link to="/library" search={{}} className="underline">Browse the case library</Link>}>
      The link may be old, or the case may not be saved yet.
    </EmptyState>
  ),
  component: DecisionPage,
})

/** The whole decision, as the Court printed it, on a page of its own: the case page keeps the summary and the facts. */
function DecisionPage() {
  const caseId = Number(Route.useParams().caseId)
  const { data: detail } = useQuery(caseQuery(caseId))
  if (!detail) return null

  return (
    <>
      <header className="mb-8">
        <Button variant="ghost" size="sm" asChild className="-ml-3 mb-3">
          <Link to="/cases/$caseId" params={{ caseId: String(caseId) }}>
            <ArrowLeft data-icon="inline-start" aria-hidden />
            {decisionCopy.back}
          </Link>
        </Button>
        <h1 className="font-serif text-2xl leading-tight font-semibold md:text-3xl">{shortCaseName(detail.title)}</h1>
        <p className="tabular mt-3 text-base text-muted-foreground">{`G.R. No. ${detail.gr_no}`}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button size="sm" asChild>
            <a href={caseDownloadUrl(caseId)} download>
              <Download data-icon="inline-start" aria-hidden />
              {caseDownloadCopy.one}
            </a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={detail.source_url} target="_blank" rel="noopener noreferrer">
              Open on Lawphil
              <ExternalLink data-icon="inline-end" aria-hidden />
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          </Button>
        </div>
      </header>

      <OfficialText text={detail.full_text} footnotes={detail.footnotes} />
      {detail.opinions.map((opinion, index) => (
        <section key={index} className="mx-auto mt-14 max-w-[62ch] border-t border-border pt-8">
          <h2 className="mb-4 text-center text-lg font-semibold">
            {opinion.kind === 'dissenting' ? 'Dissenting opinion' : opinion.kind === 'concurring' ? 'Concurring opinion' : 'Opinion'}
            {opinion.author ? `, Justice ${justiceName(opinion.author)}` : ''}
          </h2>
          <OfficialText text={opinion.text} footnotes={opinion.footnotes} />
        </section>
      ))}

      <Disclaimer className="mt-14 max-w-prose" />
    </>
  )
}
