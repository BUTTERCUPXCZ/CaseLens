import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import type { ReactNode } from 'react'

import { trendsQuery } from '@/api/queries'
import { PageHeader } from '@/components/PageHeader'
import { ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { statuteLabel } from '@/features/cases/statutes'
import { dispositionLabel } from '@/lib/copy'
import { justiceName, plural } from '@/lib/format'

export const Route = createFileRoute('/patterns')({
  component: Patterns,
})

/** A row with a plain bar: how many of the saved cases it appears in. */
function BarRow({ label, count, max, total, showBar }: { label: ReactNode; count: number; max: number; total: number; showBar: boolean }) {
  return (
    <li className="py-2">
      <div className="flex items-baseline justify-between gap-4">
        <span className="min-w-0 text-base">{label}</span>
        <span className="tabular shrink-0 text-sm text-muted-foreground">
          {count} of {total}
        </span>
      </div>
      {showBar ? (
        <div className="mt-1.5 h-2 rounded-sm bg-muted" aria-hidden>
          <div className="h-2 rounded-sm bg-primary" style={{ width: `${(count / max) * 100}%` }} />
        </div>
      ) : null}
    </li>
  )
}

function Block({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <section className="border-t border-border py-8 first:border-t-0 first:pt-0">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 mb-3 text-sm text-muted-foreground">{hint}</p>
      {children}
    </section>
  )
}

function Patterns() {
  const { data, error, isPending, refetch } = useQuery(trendsQuery())

  if (isPending) return <div aria-busy="true" aria-label="Loading patterns" className="space-y-4"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-48 w-full" /></div>
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} title="Patterns didn't load" />

  const total = data.total_cases
  const years = [...new Set(data.dispositions_by_year.map((row) => row.year))].sort((a, b) => b - a)
  const maxStatute = Math.max(1, ...data.top_statutes.map((s) => s.cases))
  const maxCited = Math.max(1, ...data.most_cited_cases.map((c) => c.cases))
  const maxJustice = Math.max(1, ...data.cases_per_ponente.map((p) => p.cases))

  return (
    <>
      <PageHeader
        title="Patterns"
        description="What your saved cases have in common: the laws they lean on, how they were decided, and the cases they cite most."
      />

      {!data.enough_data ? (
        <div className="mb-10 max-w-xl rounded-lg bg-muted px-5 py-5">
          <h2 className="text-lg font-semibold">
            Save {data.minimum_cases} cases to see patterns{total > 0 ? ` (you have ${total})` : ''}
          </h2>
          <Progress value={(total / data.minimum_cases) * 100} className="mt-3" aria-label={`${total} of ${data.minimum_cases} cases saved`} />
          <p className="mt-3 text-base text-muted-foreground">
            With only a few cases, a count is just a coincidence. Check a reviewer or look up cases by G.R. number and
            they are saved here automatically.
          </p>
          <Button asChild className="mt-4">
            <Link to="/">Check a reviewer</Link>
          </Button>
        </div>
      ) : null}

      {total > 0 ? (
        <div>
          {!data.enough_data ? (
            <p className="mb-6 text-sm text-muted-foreground">
              Based on only {plural(total, 'case')}, so read these as examples, not patterns.
            </p>
          ) : null}

          <Block title="Laws cited most" hint="How many saved cases cite each law.">
            {data.top_statutes.length === 0 ? (
              <p className="text-base text-muted-foreground">No laws found yet.</p>
            ) : (
              <ul>
                {data.top_statutes.map((s) => (
                  <BarRow key={`${s.statute_type}-${s.number}`} label={statuteLabel(s.statute_type, s.number)} count={s.cases} max={maxStatute} total={total} showBar={data.enough_data} />
                ))}
              </ul>
            )}
          </Block>

          <Block title="How cases were decided" hint="The Court's ruling, by the year of the decision.">
            <dl className="space-y-4">
              {years.map((year) => (
                <div key={year}>
                  <dt className="tabular text-base font-semibold">{year}</dt>
                  <dd className="text-base text-muted-foreground">
                    {data.dispositions_by_year
                      .filter((row) => row.year === year)
                      .map((row) => `${dispositionLabel[row.disposition]}: ${row.cases}`)
                      .join(' · ')}
                  </dd>
                </div>
              ))}
            </dl>
          </Block>

          <Block title="Cases cited most" hint="Other cases that your saved cases rely on.">
            <ul>
              {data.most_cited_cases.map((c) => (
                <BarRow
                  key={c.title}
                  label={<><span className="font-serif">{c.title}</span>{c.gr_no ? <span className="tabular text-sm text-muted-foreground"> · G.R. No. {c.gr_no}</span> : null}</>}
                  count={c.cases}
                  max={maxCited}
                  total={total}
                  showBar={data.enough_data}
                />
              ))}
            </ul>
          </Block>

          <Block title="Justices who wrote the most" hint="Who wrote the decisions you've saved (the ponente).">
            <ul>
              {data.cases_per_ponente.map((p) => (
                <BarRow key={p.ponente} label={`Justice ${justiceName(p.ponente)}`} count={p.cases} max={maxJustice} total={total} showBar={data.enough_data} />
              ))}
            </ul>
          </Block>
        </div>
      ) : null}
    </>
  )
}
