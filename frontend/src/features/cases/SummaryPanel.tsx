import { ExternalLink } from 'lucide-react'
import type { ReactNode } from 'react'

import type { CaseInsights } from '@/api/types'
import { justiceName } from '@/lib/format'

import { statuteLabel } from './statutes'

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="border-t border-border py-7 first:border-t-0 first:pt-0">
      <h2 className="text-lg font-semibold">{title}</h2>
      {hint ? <p className="mt-1 text-sm text-muted-foreground">{hint}</p> : null}
      <div className="mt-4">{children}</div>
    </section>
  )
}

const OPINION_KIND: Record<string, string> = {
  concurring: 'Concurring opinion',
  dissenting: 'Dissenting opinion',
  concurring_dissenting: 'Concurring and dissenting opinion',
  separate: 'Separate opinion',
}

/** The case at a glance. Every line is read from the Court's own text, never written by us. */
export function SummaryPanel({ insights }: { insights: CaseInsights }) {
  const concurring = insights.concurring_justices
  const ruling = insights.ruling
  return (
    <div className="max-w-3xl">
      <Section title="The ruling" hint="In the Court's own words.">
        {ruling ? (
          <blockquote className="border-l-0 font-serif text-[1.0625rem] leading-[1.75]">{ruling}</blockquote>
        ) : (
          <p className="text-base text-muted-foreground">We couldn’t find the ruling paragraph. Read the full decision.</p>
        )}
      </Section>

      <Section title="Who decided it">
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-base">
          {insights.ponente ? (
            <>
              <dt className="text-muted-foreground">Written by (ponente)</dt>
              <dd>Justice {justiceName(insights.ponente)}</dd>
            </>
          ) : null}
          {insights.division ? (
            <>
              <dt className="text-muted-foreground">Decided by</dt>
              <dd>{justiceName(insights.division)}</dd>
            </>
          ) : null}
          {concurring.length > 0 ? (
            <>
              <dt className="text-muted-foreground">Concurred</dt>
              <dd>{concurring.map(justiceName).join(', ')}</dd>
            </>
          ) : null}
          {insights.opinions.map((opinion, index) => (
            <div key={index} className="contents">
              <dt className="text-muted-foreground">{OPINION_KIND[opinion.kind] ?? 'Opinion'}</dt>
              <dd>{opinion.author ? `Justice ${justiceName(opinion.author)}` : 'See the full text'}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section
        title="Laws it cites"
        hint="Statutes and Constitution provisions named in the decision and its footnotes."
      >
        {insights.statutes.length === 0 ? (
          <p className="text-base text-muted-foreground">No statutes were found in this decision.</p>
        ) : (
          <ul className="grid gap-x-8 gap-y-1.5 text-base sm:grid-cols-2">
            {insights.statutes.map((statute) => (
              <li key={`${statute.type}-${statute.number}`}>{statuteLabel(statute.type, statute.number)}</li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Cases it cites" hint="Each one links to the footnote where the Court cites it.">
        {insights.cited_cases.length === 0 ? (
          <p className="text-base text-muted-foreground">No other cases were found in this decision.</p>
        ) : (
          <ul className="divide-y divide-border">
            {insights.cited_cases.map((cited) => (
              <li key={`${cited.title}-${cited.footnote_number ?? 'text'}`} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2.5">
                <span className="font-serif text-base">
                  {cited.title}
                  {cited.gr_no ? <span className="tabular font-sans text-sm text-muted-foreground"> &middot; G.R. No. {cited.gr_no}</span> : null}
                </span>
                {cited.source_url ? (
                  <a
                    href={cited.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-primary underline"
                  >
                    {cited.footnote_number ? `Footnote ${cited.footnote_number}` : 'In the text'}
                    <ExternalLink className="size-3" aria-hidden />
                    <span className="sr-only"> on Lawphil (opens in a new tab)</span>
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}
