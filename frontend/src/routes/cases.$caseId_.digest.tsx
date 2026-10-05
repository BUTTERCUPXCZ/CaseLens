import { createFileRoute, Link, notFound } from '@tanstack/react-router'
import { ArrowLeft, FileQuestion } from 'lucide-react'

import { orNotFound } from '@/api/orNotFound'
import { caseQuery } from '@/api/queries'
import { Disclaimer } from '@/components/Disclaimer'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { CaseDigestPanel } from '@/features/digest/CaseDigestPanel'
import { digestPageCopy } from '@/lib/copy'

export const Route = createFileRoute('/cases/$caseId_/digest')({
  loader: async ({ context, params }) => {
    const id = Number(params.caseId)
    if (!Number.isInteger(id)) throw notFound()
    await orNotFound(context.queryClient.ensureQueryData(caseQuery(id)))
  },
  pendingComponent: () => (
    <div aria-busy="true" aria-label="Opening the digest" className="space-y-4">
      <Skeleton className="h-10 w-3/4" />
      <Skeleton className="h-96 w-full" />
    </div>
  ),
  errorComponent: ({ error, reset }) => <ErrorState error={error} onRetry={reset} title="The digest didn't open" />,
  notFoundComponent: () => (
    <EmptyState icon={FileQuestion} title="We can't find that case" action={<Link to="/library" search={{}} className="underline">Browse the case library</Link>}>
      The link may be old, or the case may not be saved yet.
    </EmptyState>
  ),
  component: DigestPage,
})

/** The digest of one case. The first time it is opened it is written (a few minutes); after that it is kept. */
function DigestPage() {
  const caseId = Number(Route.useParams().caseId)
  return (
    <>
      <Button variant="ghost" size="sm" asChild className="-ml-3 mb-4">
        <Link to="/cases/$caseId" params={{ caseId: String(caseId) }}>
          <ArrowLeft data-icon="inline-start" aria-hidden />
          {digestPageCopy.back}
        </Link>
      </Button>
      <h1 className="sr-only">{digestPageCopy.pageTitle}</h1>
      <CaseDigestPanel caseId={caseId} />
      <Disclaimer className="mt-10 max-w-prose" />
    </>
  )
}
