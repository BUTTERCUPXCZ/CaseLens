import { useForm } from '@tanstack/react-form'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, Link, Navigate, useNavigate } from '@tanstack/react-router'
import { Loader2, SearchX } from 'lucide-react'
import { z } from 'zod'

import { MAX_SEARCH_POLLS, searchQuery } from '@/api/queries'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PageHeader } from '@/components/PageHeader'
import { isValidYear } from '@/features/search/grNumber'
import { PasteLink } from '@/features/search/PasteLink'
import { shortCaseName } from '@/lib/format'

const searchSchema = z.object({
  // "?gr_no=180046" is parsed as a number by the router: accept it and keep the text.
  gr_no: z.union([z.string(), z.number()]).transform(String).catch(''),
  year: z.coerce.number().int().optional().catch(undefined),
})

export const Route = createFileRoute('/lookup')({
  validateSearch: searchSchema,
  component: Search,
})

function Search() {
  const { gr_no: grNo, year } = Route.useSearch()
  const queryClient = useQueryClient()
  const options = searchQuery(grNo, year)
  const { data, error, refetch } = useQuery({ ...options, enabled: grNo !== '' })
  // How many answers have come back so far: the search gives up after MAX_SEARCH_POLLS.
  const dataUpdateCount = queryClient.getQueryState(options.queryKey)?.dataUpdateCount ?? 0

  if (grNo === '') {
    return <EmptyState icon={SearchX} title="Type a G.R. number above" action={<Button asChild><Link to="/">Back to the start</Link></Button>}>For example 180046. Adding the year it was decided helps us find it.</EmptyState>
  }
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} title="The search didn't work" />
  if (!data) return <Waiting grNo={grNo} year={year} />

  if (data.status === 'found') {
    if (data.cases.length === 1) {
      return <Navigate to="/cases/$caseId" params={{ caseId: String(data.cases[0].id) }} replace />
    }
    return (
      <>
        <PageHeader title={`G.R. No. ${grNo}`} description="We have more than one document for this number. Pick the one you want." />
        <ul className="divide-y divide-border border-y border-border">
          {data.cases.map((found) => (
            <li key={found.id}>
              <Link to="/cases/$caseId" params={{ caseId: String(found.id) }} className="block px-1 py-4 hover:bg-accent/60 md:px-3">
                <span className="font-serif text-lg">{shortCaseName(found.title)}</span>
                <span className="block text-sm text-muted-foreground capitalize">{found.doc_type.replace('_', ' ')}</span>
              </Link>
            </li>
          ))}
        </ul>
      </>
    )
  }

  if (data.status === 'needs_year') return <NeedsYear grNo={grNo} />

  // pending: the backend is looking it up on Lawphil. After about two minutes, say so honestly.
  return dataUpdateCount >= MAX_SEARCH_POLLS ? <GaveUp grNo={grNo} year={year} /> : <Waiting grNo={grNo} year={year} />
}

function Waiting({ grNo, year }: { grNo: string; year: number | undefined }) {
  return (
    <div role="status" aria-live="polite" className="mx-auto max-w-xl py-16 text-center">
      <Loader2 className="mx-auto mb-5 size-10 animate-spin text-primary" aria-hidden />
      <h1 className="text-2xl font-semibold">Looking up G.R. No. {grNo} on Lawphil…</h1>
      <p className="mt-3 text-base text-muted-foreground">
        {year ? `We're searching around ${year}. ` : ''}The first time takes about a minute, and this page opens the case by
        itself as soon as it's ready.
      </p>
    </div>
  )
}

function NeedsYear({ grNo }: { grNo: string }) {
  const navigate = useNavigate()
  const form = useForm({
    defaultValues: { year: '' },
    validators: {
      onSubmit: z.object({ year: z.string().trim().refine(isValidYear, 'Use a four-digit year, for example 2009.') }),
    },
    onSubmit: ({ value }) => void navigate({ to: '/lookup', search: { gr_no: grNo, year: Number(value.year) } }),
  })

  return (
    <div className="max-w-xl">
      <PageHeader
        title={`We need the year for G.R. No. ${grNo}`}
        description="We don't have this case saved yet. Lawphil lists cases by the month they were decided, so we need to know roughly when. A year that's one or two off still works."
      />
      <form
        onSubmit={(event) => {
          event.preventDefault()
          void form.handleSubmit()
        }}
      >
        <label htmlFor="needs-year" className="mb-1.5 block text-sm font-medium">
          Year decided
        </label>
        <form.Field name="year">
          {(field) => {
            const problem = field.state.meta.errors[0]
            const message = typeof problem === 'string' ? problem : problem?.message
            return (
              <div className="flex flex-wrap items-start gap-2">
                <div>
                  <Input
                    id="needs-year"
                    className="w-32"
                    inputMode="numeric"
                    maxLength={4}
                    placeholder="e.g. 2009"
                    value={field.state.value}
                    onChange={(event) => field.handleChange(event.target.value)}
                    aria-invalid={message ? true : undefined}
                    aria-describedby={message ? 'needs-year-error' : undefined}
                  />
                  {message ? (
                    <p id="needs-year-error" role="alert" className="mt-1 text-sm text-problem">
                      {message}
                    </p>
                  ) : null}
                </div>
                <Button type="submit">Look it up</Button>
              </div>
            )
          }}
        </form.Field>
      </form>
      <PasteLink />
    </div>
  )
}

function GaveUp({ grNo, year }: { grNo: string; year: number | undefined }) {
  return (
    <div className="max-w-xl">
      <PageHeader
        title={`We couldn't find G.R. No. ${grNo}${year ? ` near ${year}` : ''}`}
        description="Check the number and the year. If you have the case's own Lawphil link, paste it below and we'll save the case from there."
      />
      <Button variant="outline" asChild>
        <Link to="/">Back to the start</Link>
      </Button>
      <PasteLink />
    </div>
  )
}
