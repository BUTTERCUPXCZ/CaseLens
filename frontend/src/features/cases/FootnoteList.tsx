import { ExternalLink } from 'lucide-react'

import type { Footnote } from '@/api/types'

/** All the footnotes in order, each with a link to the same footnote on Lawphil. */
export function FootnoteList({ footnotes }: { footnotes: Footnote[] }) {
  if (footnotes.length === 0) return <p className="text-base text-muted-foreground">This decision has no footnotes.</p>
  return (
    <ol className="mx-auto max-w-[62ch] space-y-4 font-serif text-base leading-relaxed">
      {footnotes.map((footnote) => (
        <li key={footnote.anchor} id={`footnote-${footnote.number}`} className="grid grid-cols-[2.5rem_1fr] gap-x-2">
          <span className="font-sans text-sm font-semibold text-muted-foreground tabular">{footnote.number}</span>
          <div>
            <p>{footnote.text || 'This footnote is empty on the Court’s page.'}</p>
            {footnote.source_url ? (
              <a
                href={footnote.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-flex items-center gap-1 font-sans text-sm text-primary underline"
              >
                On Lawphil
                <ExternalLink className="size-3" aria-hidden />
                <span className="sr-only"> (footnote {footnote.number}, opens in a new tab)</span>
              </a>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  )
}
