import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, Navigate, notFound } from '@tanstack/react-router'
import { BookOpenText, Download, ExternalLink, FileQuestion, FileText } from 'lucide-react'
import { z } from 'zod'

import { orNotFound } from '@/api/orNotFound'
import { caseDownloadUrl } from '@/api/endpoints'
import { useSetSubjects } from '@/api/mutations'
import { caseQuery, insightsQuery } from '@/api/queries'
import { Disclaimer } from '@/components/Disclaimer'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FootnoteList } from '@/features/cases/FootnoteList'
import { SubjectTags } from '@/features/upload/SubjectTags'
import { SummaryPanel } from '@/features/cases/SummaryPanel'
import { caseDownloadCopy, decisionCopy, dispositionLabel, libraryCopy } from '@/lib/copy'
import { divisionName, formatDate, justiceName, shortCaseName } from '@/lib/format'

const searchSchema = z.object({ tab: z.enum(['summary', 'text', 'footnotes']).optional().catch(undefined) })

export const Route = createFileRoute('/cases/$caseId')({
  validateSearch: searchSchema,
  loader: async ({ context, params }) => {
    const id = Number(params.caseId)
    if (!Number.isInteger(id)) throw notFound()
    await orNotFound(
      Promise.all([
        context.queryClient.ensureQueryData(caseQuery(id)),
        context.queryClient.ensureQueryData(insightsQuery(id)),
      ]),
    )
  },
  pendingComponent: CaseSkeleton,
  errorComponent: ({ error, reset }) => <ErrorState error={error} onRetry={reset} title="This case didn't open" />,
  notFoundComponent: () => (
    <EmptyState icon={FileQuestion} title="We can't find that case" action={<Link to="/library" search={{}} className="underline">Browse the case library</Link>}>
      The link may be old, or the case may not be saved yet.
    </EmptyState>
  ),
  component: CasePage,
})

function CaseSkeleton() {
  return (
    <div aria-busy="true" aria-label="Opening the case" className="space-y-4">
      <Skeleton className="h-10 w-3/4" />
      <Skeleton className="h-5 w-1/2" />
      <Skeleton className="h-96 w-full" />
    </div>
  )
}

function CasePage() {
  const caseId = Number(Route.useParams().caseId)
  const tab = Route.useSearch().tab ?? 'summary'
  const navigate = Route.useNavigate()
  const { data: detail } = useQuery(caseQuery(caseId))
  const { data: insights } = useQuery(insightsQuery(caseId))
  const setSubjects = useSetSubjects(caseId)
  if (tab === 'text') return <Navigate to="/cases/$caseId/decision" params={{ caseId: String(caseId) }} replace /> // an old link
  if (!detail || !insights) return <CaseSkeleton />

  const meta = [
    `G.R. No. ${detail.gr_no}`,
    formatDate(detail.decision_date),
    detail.division ? divisionName(detail.division) : null,
    detail.ponente ? `Written by Justice ${justiceName(detail.ponente)}` : null,
  ].filter(Boolean)

  return (
    <>
      <header className="mb-6">
        <h1 className="font-serif text-2xl leading-tight font-semibold md:text-3xl">{shortCaseName(detail.title)}</h1>
        <p className="tabular mt-3 text-base text-muted-foreground">{meta.join(' · ')}</p>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="rounded-md bg-secondary px-3 py-1 text-sm font-medium text-secondary-foreground">
            {dispositionLabel[detail.disposition]}
          </span>
          <Button size="sm" asChild>
            <Link to="/cases/$caseId/digest" params={{ caseId: String(caseId) }}>
              <BookOpenText data-icon="inline-start" aria-hidden />
              {libraryCopy.caseDigest}
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to="/cases/$caseId/decision" params={{ caseId: String(caseId) }}>
              <FileText data-icon="inline-start" aria-hidden />
              {decisionCopy.read}
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
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

        <div className="mt-5 max-w-3xl">
          <SubjectTags id="case-tags" value={detail.subjects.map((s) => s.id)} disabled={setSubjects.isPending} onChange={(ids) => setSubjects.mutate(ids)} />
          {setSubjects.isError ? <p role="alert" className="mt-1 text-sm text-problem">{libraryCopy.subjectFailed}</p> : null}
        </div>
      </header>

      <Tabs value={tab} onValueChange={(next) => void navigate({ search: { tab: next as typeof tab }, replace: true })}>
        <TabsList className="mb-6 h-auto flex-wrap justify-start gap-1 bg-transparent p-0">
          {[
            ['summary', 'Quick summary'],
            ['footnotes', `Footnotes (${detail.footnotes.length})`],
          ].map(([value, label]) => (
            <TabsTrigger
              key={value}
              value={value}
              className="rounded-md px-4 py-2 text-base data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              {label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="summary">
          <details className="mb-6 max-w-3xl text-sm text-muted-foreground">
            <summary className="cursor-pointer underline">The case title exactly as the Court wrote it</summary>
            <p className="mt-2 font-serif text-base">{detail.title}</p>
          </details>
          <SummaryPanel insights={insights} />
        </TabsContent>

        <TabsContent value="footnotes">
          <FootnoteList footnotes={detail.footnotes} />
        </TabsContent>
      </Tabs>

      <Disclaimer className="mt-14 max-w-prose" />
    </>
  )
}
