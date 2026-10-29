import { ExternalLink } from 'lucide-react'

import { libraryCopy } from '@/copy'
import { stagger } from '@/lib/useReveal'
import { Cell, Chapter, NoteRef, RuledGrid } from '@/sections/Chapter'

/** The Case library as the app draws it (a subject rail beside one row per main case), then how cases get into it. */
export function Library() {
  return (
    <Chapter id="library" title={libraryCopy.title} lead={libraryCopy.lead}>
      <div data-reveal className="overflow-hidden rounded-xl border border-border bg-card shadow-[0_24px_48px_-32px_color-mix(in_oklch,var(--foreground)_40%,transparent)]">
        <div className="grid grid-cols-[minmax(0,1fr)] md:grid-cols-[13rem_minmax(0,1fr)]">
          <div className="border-b border-border p-4 md:border-r md:border-b-0">
            <p className="text-sm font-semibold text-muted-foreground" id="library-subjects">
              {libraryCopy.subjectsLabel}
            </p>
            <ul aria-labelledby="library-subjects" className="mt-2 flex flex-wrap gap-1.5 md:flex-col md:gap-0.5">
              {libraryCopy.subjects.map((subject, i) => (
                <li
                  key={subject}
                  aria-current={i === 0 ? 'true' : undefined}
                  className={[
                    'rounded-md px-2.5 py-1.5 text-sm',
                    i === 0 ? 'bg-accent font-medium text-accent-foreground' : 'text-muted-foreground',
                  ].join(' ')}
                >
                  {subject}
                </li>
              ))}
            </ul>
          </div>
          <div tabIndex={0} role="region" aria-label={libraryCopy.region} className="relative overflow-x-auto p-4 md:p-5">
            <table className="w-full min-w-[32rem] border-collapse text-base">
              <caption className="sr-only">{libraryCopy.caption}</caption>
              <thead>
                <tr className="border-b border-border text-left text-sm text-muted-foreground">
                  {libraryCopy.columns.map((column) => (
                    <th key={column} scope="col" className="py-2 pr-4 font-medium">
                      {column}
                    </th>
                  ))}
                  <th scope="col" className="py-2 font-medium">
                    <span className="sr-only">{libraryCopy.actionsHeader}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {libraryCopy.rows.map((row) => (
                  <tr key={row.number} className="border-b border-border last:border-b-0">
                    <td className="py-3 pr-4 font-serif leading-snug font-medium">{row.name}</td>
                    <td className="tabular py-3 pr-4 text-sm">
                      <span className="block text-foreground">G.R. No. {row.number}</span>
                      <span className="block text-muted-foreground">
                        {row.date} · {row.ponente}
                      </span>
                    </td>
                    <td className="py-3 text-sm whitespace-nowrap text-primary">
                      {libraryCopy.actions}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <RuledGrid className="mt-14 md:grid-cols-2">
        <Cell data-reveal style={stagger(1)} className="md:border-r">
          <h3 className="text-lg font-semibold">{libraryCopy.bulkTitle}</h3>
          <p className="mt-2 max-w-[52ch] text-base leading-relaxed text-muted-foreground">{libraryCopy.bulk}</p>
        </Cell>
        <Cell data-reveal style={stagger(2)}>
          <h3 className="text-lg font-semibold">{libraryCopy.searchTitle}</h3>
          <p className="mt-2 max-w-[52ch] text-base leading-relaxed text-muted-foreground">
            {libraryCopy.search}
            <NoteRef n={3} />
          </p>
          <p className="mt-3 inline-flex items-center gap-1.5 text-sm text-muted-foreground">
            <ExternalLink className="size-3.5" aria-hidden />
            {libraryCopy.official}
          </p>
        </Cell>
      </RuledGrid>
    </Chapter>
  )
}
